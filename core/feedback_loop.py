"""
feedback_loop.py — 精度优化反馈循环引擎
测量数据→误差分解→参数校准→公差重算→迭代收敛

推演任务: dp_1774574718408_ab77e5
基于已知(F): RSS合成/热膨胀/MC影响/裱合耦合/K因子相变
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import json
import time


class FeedbackStatus(Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    CALIBRATING = "calibrating"
    CONVERGED = "converged"
    DIVERGED = "diverged"
    NEEDS_HUMAN = "needs_human"


class ErrorCategory(Enum):
    SYSTEMATIC = "systematic"       # 系统性偏差(可校准)
    RANDOM = "random"               # 随机误差(RSS处理)
    ENVIRONMENTAL = "environmental" # 环境(MC/温度)
    MATERIAL = "material"           # 材料批次差异
    PROCESS = "process"             # 工艺参数漂移


@dataclass
class Measurement:
    """单次测量数据"""
    timestamp: float
    nominal_mm: float          # 标称值
    actual_mm: float           # 实测值
    error_mm: float            # 偏差(=actual-nominal)
    temperature_c: float = 23.0
    humidity_pct: float = 50.0
    machine_id: str = "unknown"
    material_id: str = "unknown"
    operator: str = "auto"
    notes: str = ""


@dataclass
class ErrorDecomposition:
    """误差分解结果"""
    systematic_mm: float = 0.0        # 系统偏差(均值)
    random_std_mm: float = 0.0        # 随机标准差
    thermal_component_mm: float = 0.0 # 温度贡献
    mc_component_mm: float = 0.0      # 含水量贡献
    material_component_mm: float = 0.0
    process_component_mm: float = 0.0
    residual_mm: float = 0.0          # 残差
    confidence: float = 0.0           # 分解置信度 0-1


@dataclass
class CalibrationResult:
    """校准结果"""
    parameter: str
    old_value: float
    new_value: float
    delta_pct: float
    category: ErrorCategory
    justification: str


@dataclass
class FeedbackCycle:
    """一次完整反馈循环"""
    cycle_id: int
    measurements: List[Measurement]
    decomposition: ErrorDecomposition
    calibrations: List[CalibrationResult]
    predicted_improvement_mm: float
    status: FeedbackStatus
    convergence_ratio: float = 0.0  # improvement/cycle, <0.01视为收敛


class FeedbackLoopEngine:
    """精度优化反馈循环引擎"""

    # 物理常数(基于已确认已知)
    THERMAL_EXPANSION_COEFF = 1.2e-4   # 纸板热膨胀系数 /°C
    MC_SENSITIVITY = 0.015              # MC每1%收缩率变化
    REFERENCE_TEMP_C = 23.0
    REFERENCE_MC_PCT = 10.0

    # 设备基准精度
    MACHINE_PRECISION = {
        "bobst": 0.15,
        "heidelberg": 0.20,
        "domestic": 0.30,
        "rotary_bobst": 0.25,
    }

    def __init__(self):
        self.measurements: List[Measurement] = []
        self.cycles: List[FeedbackCycle] = []
        self.current_params: Dict[str, float] = {
            "safety_factor_k": 1.20,
            "thermal_drift_coeff": 1.0,
            "mc_sensitivity": 1.0,
            "material_variability": 1.0,
            "k_factor_base": 0.37,
        }
        self.history: List[Dict] = []
        self._cycle_counter = 0

    def add_measurement(self, m: Measurement):
        """添加测量数据"""
        if m.error_mm == 0 and hasattr(m, 'nominal_mm'):
            m.error_mm = m.actual_mm - m.nominal_mm
        self.measurements.append(m)

    def add_batch(self, data: List[Dict]) -> int:
        """批量添加测量(从JSON/CSV导入)"""
        count = 0
        for d in data:
            m = Measurement(
                timestamp=d.get("timestamp", time.time()),
                nominal_mm=d["nominal"],
                actual_mm=d["actual"],
                error_mm=d.get("actual", 0) - d.get("nominal", 0),
                temperature_c=d.get("temperature", 23.0),
                humidity_pct=d.get("humidity", 50.0),
                machine_id=d.get("machine", "unknown"),
                material_id=d.get("material", "unknown"),
                notes=d.get("notes", ""),
            )
            self.add_measurement(m)
            count += 1
        return count

    def decompose_errors(self, measurements: Optional[List[Measurement]] = None) -> ErrorDecomposition:
        """误差分解: 将总偏差分解为各分量"""
        data = measurements or self.measurements
        if len(data) < 3:
            return ErrorDecomposition(confidence=0.0)

        errors = [m.error_mm for m in data]
        n = len(errors)
        mean_err = sum(errors) / n
        std_err = math.sqrt(sum((e - mean_err)**2 for e in errors) / (n - 1)) if n > 1 else 0

        result = ErrorDecomposition(
            systematic_mm=round(mean_err, 4),
            random_std_mm=round(std_err, 4),
        )

        # 温度分量估算
        temps = [m.temperature_c for m in data]
        mean_temp = sum(temps) / n
        temp_deviation = mean_temp - self.REFERENCE_TEMP_C
        # 假设典型尺寸300mm
        result.thermal_component_mm = round(abs(temp_deviation) * self.THERMAL_EXPANSION_COEFF * 300, 4)

        # MC分量估算
        humidities = [m.humidity_pct for m in data]
        mean_humidity = sum(humidities) / n
        # 近似MC ≈ humidity_pct / 10 (经验关系: 50%RH ≈ 10%MC)
        mc_estimate = mean_humidity / 10.0
        mc_deviation = mc_estimate - self.REFERENCE_MC_PCT
        # MC影响: 偏差×敏感度×尺寸系数(归一化到100mm)
        result.mc_component_mm = round(abs(mc_deviation) * self.MC_SENSITIVITY * 0.3, 4)

        # 材料分量(按设备精度估算)
        machine_ids = set(m.machine_id for m in data)
        mat_component = 0
        for mid in machine_ids:
            base = self.MACHINE_PRECISION.get(mid, 0.30)
            mat_component = max(mat_component, base * 0.3)  # 材料约占设备精度的30%
        result.material_component_mm = round(mat_component, 4)

        # 工艺分量(裱合/压痕)
        result.process_component_mm = round(std_err * 0.2, 4)  # 工艺约占随机分量的20%

        # 残差
        rss_components = [
            result.thermal_component_mm ** 2,
            result.mc_component_mm ** 2,
            result.material_component_mm ** 2,
            result.process_component_mm ** 2,
        ]
        rss_sum = math.sqrt(sum(rss_components))
        result.residual_mm = round(max(0, abs(mean_err) - rss_sum), 4)

        # 置信度(基于样本量和残差比)
        sample_factor = min(1.0, n / 30)  # 30样本达到满置信
        residual_ratio = result.residual_mm / max(abs(mean_err), 0.001)
        result.confidence = round(sample_factor * max(0.1, 1 - residual_ratio), 2)

        return result

    def suggest_calibrations(self, decomp: ErrorDecomposition) -> List[CalibrationResult]:
        """基于误差分解建议校准"""
        calibrations = []

        # 系统偏差→安全系数调整
        if abs(decomp.systematic_mm) > 0.02:
            old_k = self.current_params["safety_factor_k"]
            # 如果系统偏差为正(实测>标称), 需要增大安全系数
            adjustment = decomp.systematic_mm * 0.5 / max(old_k, 0.1)
            new_k = max(1.0, min(1.5, old_k + adjustment))
            calibrations.append(CalibrationResult(
                parameter="safety_factor_k",
                old_value=old_k,
                new_value=round(new_k, 4),
                delta_pct=round((new_k - old_k) / old_k * 100, 1),
                category=ErrorCategory.SYSTEMATIC,
                justification=f"系统偏差{decomp.systematic_mm:+.3f}mm, 调整安全系数"
            ))

        # MC敏感度
        if decomp.mc_component_mm > 0.05:
            old_sens = self.current_params["mc_sensitivity"]
            mc_ratio = decomp.mc_component_mm / max(decomp.random_std_mm, 0.001)
            new_sens = min(2.0, old_sens * (1 + mc_ratio * 0.3))
            calibrations.append(CalibrationResult(
                parameter="mc_sensitivity",
                old_value=old_sens,
                new_value=round(new_sens, 4),
                delta_pct=round((new_sens - old_sens) / old_sens * 100, 1),
                category=ErrorCategory.ENVIRONMENTAL,
                justification=f"MC贡献{decomp.mc_component_mm:.3f}mm, 提升敏感度权重"
            ))

        # 热膨胀系数
        if decomp.thermal_component_mm > 0.03:
            old_tc = self.current_params["thermal_drift_coeff"]
            new_tc = old_tc * (1 + decomp.thermal_component_mm * 2)
            calibrations.append(CalibrationResult(
                parameter="thermal_drift_coeff",
                old_value=old_tc,
                new_value=round(new_tc, 4),
                delta_pct=round((new_tc - old_tc) / old_tc * 100, 1),
                category=ErrorCategory.ENVIRONMENTAL,
                justification=f"热膨胀贡献{decomp.thermal_component_mm:.3f}mm, 修正漂移系数"
            ))

        # 材料变异
        if decomp.material_component_mm > 0.04:
            old_mv = self.current_params["material_variability"]
            new_mv = old_mv * (1 + decomp.material_component_mm)
            calibrations.append(CalibrationResult(
                parameter="material_variability",
                old_value=old_mv,
                new_value=round(new_mv, 4),
                delta_pct=round((new_mv - old_mv) / old_mv * 100, 1),
                category=ErrorCategory.MATERIAL,
                justification=f"材料变异{decomp.material_component_mm:.3f}mm, 提升变异系数"
            ))

        return calibrations

    def apply_calibrations(self, calibrations: List[CalibrationResult]):
        """应用校准结果"""
        for cal in calibrations:
            if cal.parameter in self.current_params:
                self.current_params[cal.parameter] = cal.new_value

    def predict_tolerance(self, machine_id: str = "bobst", size_mm: float = 300) -> Dict:
        """基于当前参数预测公差"""
        base_prec = self.MACHINE_PRECISION.get(machine_id, 0.30)

        k = self.current_params["safety_factor_k"]
        tc = self.current_params["thermal_drift_coeff"]
        mc = self.current_params["mc_sensitivity"]
        mv = self.current_params["material_variability"]

        # 各分量
        machine_var = base_prec
        thermal_var = 0.065 * tc
        mc_var = 0.08 * mc
        material_var = 0.05 * mv
        process_var = 0.03

        # RSS合成
        rss = math.sqrt(sum(v**2 for v in [machine_var, thermal_var, mc_var, material_var, process_var]))
        budget = rss * k

        # 缩放到目标尺寸
        scale = size_mm / 300.0
        budget_scaled = budget * math.sqrt(scale)  # 误差与√L成正比

        return {
            "machine": machine_id,
            "size_mm": size_mm,
            "base_precision_mm": base_prec,
            "rss_components": {
                "machine": machine_var,
                "thermal": thermal_var,
                "mc": mc_var,
                "material": material_var,
                "process": process_var,
            },
            "rss_total_mm": round(rss, 4),
            "safety_factor": k,
            "tolerance_budget_mm": round(budget_scaled, 3),
            "tolerance_±_mm": round(budget_scaled / 2, 3),
        }

    def run_cycle(self, new_measurements: Optional[List[Dict]] = None) -> FeedbackCycle:
        """执行一次完整反馈循环"""
        self._cycle_counter += 1

        if new_measurements:
            self.add_batch(new_measurements)

        if len(self.measurements) < 3:
            return FeedbackCycle(
                cycle_id=self._cycle_counter,
                measurements=[],
                decomposition=ErrorDecomposition(confidence=0.0),
                calibrations=[],
                predicted_improvement_mm=0,
                status=FeedbackStatus.NEEDS_HUMAN,
            )

        # 1. 误差分解
        decomp = self.decompose_errors()

        # 2. 校准建议
        calibrations = self.suggest_calibrations(decomp)

        # 3. 应用校准
        self.apply_calibrations(calibrations)

        # 4. 预测改善
        old_pred = self.predict_tolerance()
        predicted_improvement = 0
        if self.cycles:
            prev_pred = self.cycles[-1]
            if hasattr(prev_pred, 'predicted_improvement_mm'):
                # 用系统偏差减少量估算改善
                predicted_improvement = abs(decomp.systematic_mm) * 0.5

        # 5. 收敛判断
        convergence = abs(predicted_improvement) if self.cycles else 1.0
        status = FeedbackStatus.CALIBRATING
        if convergence < 0.005:
            status = FeedbackStatus.CONVERGED
        elif convergence > 0.5:
            status = FeedbackStatus.DIVERGED

        cycle = FeedbackCycle(
            cycle_id=self._cycle_counter,
            measurements=self.measurements[-50:],  # 最近50条
            decomposition=decomp,
            calibrations=calibrations,
            predicted_improvement_mm=round(predicted_improvement, 4),
            status=status,
            convergence_ratio=round(convergence, 4),
        )
        self.cycles.append(cycle)

        # 记录历史
        self.history.append({
            "cycle": self._cycle_counter,
            "timestamp": time.time(),
            "n_measurements": len(self.measurements),
            "decomp": {
                "systematic": decomp.systematic_mm,
                "random_std": decomp.random_std_mm,
                "thermal": decomp.thermal_component_mm,
                "mc": decomp.mc_component_mm,
                "confidence": decomp.confidence,
            },
            "params": dict(self.current_params),
            "status": status.value,
        })

        return cycle

    def get_report(self) -> Dict:
        """生成反馈循环报告"""
        if not self.cycles:
            return {"status": "no_cycles", "recommendation": "需要至少3条测量数据"}

        latest = self.cycles[-1]
        decomp = latest.decomposition
        pred = self.predict_tolerance()

        # 趋势分析
        systematic_trend = "stable"
        if len(self.history) >= 2:
            prev_sys = self.history[-2]["decomp"]["systematic"]
            curr_sys = decomp.systematic_mm
            diff = abs(curr_sys) - abs(prev_sys)
            if diff < -0.005:
                systematic_trend = "improving"
            elif diff > 0.005:
                systematic_trend = "worsening"

        return {
            "total_cycles": len(self.cycles),
            "total_measurements": len(self.measurements),
            "latest_status": latest.status.value,
            "systematic_bias_mm": decomp.systematic_mm,
            "random_variation_mm": decomp.random_std_mm,
            "decomposition_confidence": decomp.confidence,
            "systematic_trend": systematic_trend,
            "current_tolerance_±_mm": pred["tolerance_±_mm"],
            "current_params": self.current_params,
            "calibrations_applied": [
                {"param": c.parameter, f"{c.old_value}→{c.new_value}": f"({c.delta_pct:+.1f}%)", "reason": c.justification}
                for c in latest.calibrations
            ],
            "recommendation": self._generate_recommendation(latest, pred),
        }

    def _generate_recommendation(self, cycle: FeedbackCycle, pred: Dict) -> str:
        """生成改善建议"""
        parts = []
        decomp = cycle.decomposition

        if abs(decomp.systematic_mm) > 0.1:
            parts.append(f"系统偏差{decomp.systematic_mm:+.3f}mm较大, 检查设备校准和图纸基准")

        if decomp.mc_component_mm > 0.05:
            parts.append("MC影响显著, 建议控制车间湿度(目标45-55%RH)")

        if decomp.thermal_component_mm > 0.03:
            parts.append("温度漂移可检测, 建议预热设备30min后再生产")

        if decomp.material_component_mm > 0.04:
            parts.append("材料批次差异大, 建议加强来料检验")

        if cycle.status == FeedbackStatus.CONVERGED:
            parts.append(f"已收敛, 当前最优公差±{pred['tolerance_±_mm']}mm")

        if cycle.status == FeedbackStatus.DIVERGED:
            parts.append("⚠️ 发散趋势, 需要人工检查测量数据质量")

        if not parts:
            parts.append("各项指标正常, 继续积累数据")

        return "; ".join(parts)

    def export_history(self) -> str:
        """导出历史为JSON"""
        return json.dumps(self.history, indent=2, ensure_ascii=False)


# === 测试 ===
if __name__ == "__main__":
    import random

    engine = FeedbackLoopEngine()

    # 模拟Bobst设备测量数据(30条)
    print("=== 精度优化反馈循环引擎 ===\n")
    random.seed(42)
    measurements = []
    for i in range(30):
        # 模拟: 系统偏差+0.05mm, 随机±0.12mm, 温度波动
        sys_bias = 0.05
        rand_err = random.gauss(0, 0.12)
        temp_effect = random.gauss(0, 0.02)
        measurements.append({
            "nominal": 100.0,
            "actual": 100.0 + sys_bias + rand_err + temp_effect,
            "temperature": 23 + random.gauss(0, 1.5),
            "humidity": 50 + random.gauss(0, 5),
            "machine": "bobst",
        })

    # Cycle 1
    print("--- Cycle 1 ---")
    cycle1 = engine.run_cycle(measurements)
    decomp1 = cycle1.decomposition
    print(f"系统偏差: {decomp1.systematic_mm:+.4f}mm")
    print(f"随机标准差: {decomp1.random_std_mm:.4f}mm")
    print(f"温度分量: {decomp1.thermal_component_mm:.4f}mm")
    print(f"MC分量: {decomp1.mc_component_mm:.4f}mm")
    print(f"置信度: {decomp1.confidence}")
    print(f"校准建议: {len(cycle1.calibrations)}条")
    for cal in cycle1.calibrations:
        print(f"  {cal.parameter}: {cal.old_value:.4f} → {cal.new_value:.4f} ({cal.delta_pct:+.1f}%)")
    print(f"状态: {cycle1.status.value}")

    # Cycle 2: 模拟改善后的数据
    print("\n--- Cycle 2 (改善后数据) ---")
    improved = []
    for i in range(20):
        rand_err = random.gauss(0, 0.10)  # 随机误差减小
        improved.append({
            "nominal": 100.0,
            "actual": 100.0 + 0.02 + rand_err,  # 系统偏差减小
            "temperature": 23 + random.gauss(0, 0.5),
            "humidity": 50 + random.gauss(0, 2),
            "machine": "bobst",
        })
    cycle2 = engine.run_cycle(improved)
    decomp2 = cycle2.decomposition
    print(f"系统偏差: {decomp2.systematic_mm:+.4f}mm (从{decomp1.systematic_mm:+.4f}改善)")
    print(f"随机标准差: {decomp2.random_std_mm:.4f}mm")
    print(f"状态: {cycle2.status.value}")

    # 公差预测
    print("\n--- 公差预测 ---")
    for machine in ["bobst", "domestic"]:
        for size in [100, 300, 500]:
            pred = engine.predict_tolerance(machine, size)
            print(f"  {machine:>12} L={size}mm: ±{pred['tolerance_±_mm']:.3f}mm (RSS={pred['rss_total_mm']:.4f}, k={pred['safety_factor']})")

    # 完整报告
    print("\n--- 反馈报告 ---")
    report = engine.get_report()
    for k, v in report.items():
        print(f"  {k}: {v}")
