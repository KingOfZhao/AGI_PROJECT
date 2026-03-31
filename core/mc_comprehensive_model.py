"""
mc_comprehensive_model.py — 含水量(MC)综合影响模型
===============================================
MC是刀模精度的最大敌人。本模块建立MC从原材料到成品的全链路影响模型。

已知(F)基础:
- F15: 含水量是精度最大敌人
- F4: 吸湿滞后效应 (k_absorb ≠ k_desorb)
- F5: S型收缩曲线 (Logistic, k=40-60, MC_mid≈12%)
- F8: MC兼容范围 ±2%
- F27: MC≥16%触发湿态相变
- F12: Bobst热膨胀 0.05-0.08mm/30min
- F19: 裱合三耦合误差
- F26: K因子相变 d/T≥0.65
- F28: ±0.5mm精密级不可达
- F29: RSS非正态修正

推演任务: HEARTBEAT.md "MC含水量综合影响模型"
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import json


class MCZone(Enum):
    """MC影响分区"""
    SAFE = "safe"               # 8-12%: 正常工作区
    WARNING = "warning"         # 12-14%: 预警区
    DANGER = "danger"           # 14-16%: 危险区
    CRITICAL = "critical"       # 16%+: 湿态相变
    DEHYDRATED = "dehydrated"   # <8%: 过干脆化


class MCPath(Enum):
    """吸湿/脱湿路径"""
    ABSORB = "absorb"     # 吸湿路径(车间→高湿)
    DESORB = "desorb"     # 脱湿路径(烘干/低湿→平衡)
    EQUILIBRIUM = "equilibrium"  # 平衡态


class MoistureState(Enum):
    """材料水分状态"""
    OVEN_DRY = 0          # 烘干态 0%
    AMBIENT = 1           # 环境平衡态 ~10%
    PROCESS = 2           # 加工中
    PRODUCT = 3           # 成品
    SHIPPING = 4          # 运输中


@dataclass
class MCProfile:
    """MC状态剖面"""
    mc_pct: float                 # 当前含水量 %
    path: MCPath = MCPath.EQUILIBRIUM  # 吸湿/脱湿路径
    temperature_c: float = 23.0   # 温度
    humidity_rh: float = 50.0     # 相对湿度
    material_type: str = "single_wall"  # 材料类型
    thickness_mm: float = 3.0     # 厚度
    time_hours: float = 0.0       # 从上次MC变化经过的时间
    history: List[Dict] = field(default_factory=list)  # MC变化历史


@dataclass
class ShrinkageResult:
    """收缩计算结果"""
    linear_shrinkage_pct: float    # 线性收缩率 %
    md_shrinkage_mm: float         # MD方向收缩 mm
    cd_shrinkage_mm: float         # CD方向收缩 mm
    net_error_mm: float            # 净误差 mm
    zone: MCZone
    phase_change: bool             # 是否触发相变
    hysteresis_mm: float           # 滞后效应导致的额外误差
    confidence: float              # 置信度


@dataclass
class MCErrorBudget:
    """MC对总误差预算的贡献"""
    direct_shrinkage_mm: float = 0.0      # 直接收缩
    hysteresis_mm: float = 0.0            # 滞后效应
    lamination_coupling_mm: float = 0.0   # 裱合耦合放大
    k_factor_shift_mm: float = 0.0        # K因子偏移
    curl_warp_mm: float = 0.0            # 卷曲/翘曲
    phase_change_mm: float = 0.0         # 相变跳变
    rss_total_mm: float = 0.0            # RSS合成
    safety_factor: float = 1.0           # 安全系数


class MCComprehensiveModel:
    """
    含水量综合影响模型
    
    核心公式:
    1. S型收缩: S(MC) = S_max / (1 + exp(-k(MC - MC_mid)))
    2. 滞后效应: Δhyst = (k_absorb - k_desorb) × MC × L × 0.001
    3. 裱合耦合放大: Δlam = Δshrink × coupling_factor(MC)
    4. K因子偏移: ΔK = α_K × (MC - MC_ref)
    5. 相变阈值: MC ≥ 16% → K骤降, 收缩率跳变
    """

    # === 物理常数(基于已确认已知) ===
    
    # S型Logistic参数
    S_MAX_MD = 0.8       # MD方向最大收缩率 %
    S_MAX_CD = 0.3       # CD方向最大收缩率 % (CD < MD)
    LOGISTIC_K = 50      # Logistic陡度
    MC_MIDPOINT = 12.0   # 中点MC %
    MC_REFERENCE = 10.0  # 参考MC %
    
    # 滞后效应参数
    K_ABSORB = 0.042     # 吸湿路径系数
    K_DESORB = 0.028     # 脱湿路径系数 (比吸湿小33%)
    
    # 相变参数
    MC_PHASE_CHANGE = 16.0  # 湿态相变阈值
    K_NORMAL = 0.37         # 正常K因子
    K_PHASE_CHANGED = 0.25  # 相变后K因子
    D_T_CRITICAL = 0.65     # d/T临界比
    
    # MC安全范围
    MC_SAFE_MIN = 8.0
    MC_SAFE_MAX = 12.0
    MC_COMPATIBLE_DELTA = 2.0  # ±2%
    
    # 材料系数(不同材料的MC敏感度)
    MATERIAL_MC_SENSITIVITY = {
        "grayboard": 1.3,       # 灰板: 高敏感(密度大, 吸湿多)
        "single_wall": 1.0,     # 单瓦楞: 基准
        "double_wall": 0.9,     # 双瓦楞: 稍低(结构刚性)
        "micro_flute": 1.5,     # 微瓦楞: 最高敏感(薄, 快平衡)
        "plastic": 0.05,        # 塑料: 几乎不受MC影响
    }
    
    # 裱合耦合放大因子(随MC增大)
    LAMINATION_BASE_FACTOR = 0.3
    LAMINATION_MC_FACTOR = 0.08  # 每超过参考MC 1%, 耦合放大增加
    
    def __init__(self):
        self._cache = {}

    def classify_zone(self, mc_pct: float) -> MCZone:
        """MC分区"""
        if mc_pct < self.MC_SAFE_MIN:
            return MCZone.DEHYDRATED
        elif mc_pct <= self.MC_SAFE_MAX:
            return MCZone.SAFE
        elif mc_pct <= 14.0:
            return MCZone.WARNING
        elif mc_pct < self.MC_PHASE_CHANGE:
            return MCZone.DANGER
        else:
            return MCZone.CRITICAL

    def logistic_shrinkage(self, mc_pct: float, direction: str = "MD") -> float:
        """
        S型Logistic收缩曲线
        
        S(MC) = S_max / (1 + exp(-k × (MC - MC_mid)))
        
        direction: "MD"(纵向) 或 "CD"(横向)
        """
        s_max = self.S_MAX_MD if direction == "MD" else self.S_MAX_CD
        exponent = -self.LOGISTIC_K * (mc_pct - self.MC_MIDPOINT) / 100.0
        # 防溢出
        exponent = max(-20, min(20, exponent))
        return s_max / (1.0 + math.exp(exponent))

    def hysteresis_correction(self, mc_pct: float, path: MCPath, length_mm: float = 300) -> float:
        """
        吸湿滞后效应
        
        吸湿路径和脱湿路径的收缩率不同。
        滞后误差 = |k_absorb - k_desorb| × MC × L × 0.001
        """
        if path == MCPath.EQUILIBRIUM:
            return 0.0
        
        k_eff = self.K_ABSORB if path == MCPath.ABSORB else self.K_DESORB
        k_eq = (self.K_ABSORB + self.K_DESORB) / 2  # 平衡态等效系数
        # 滞后误差 = 实际路径收缩 - 平衡态收缩
        shrink_path = k_eff * mc_pct * length_mm * 0.001
        shrink_eq = k_eq * mc_pct * length_mm * 0.001
        return abs(shrink_path - shrink_eq)

    def lamination_coupling(self, mc_pct: float, base_shrinkage_mm: float) -> float:
        """
        裱合耦合放大
        
        MC越高, 裱合三耦合(胶水收缩+面纸膨胀+张力差异)效应越强。
        coupling_factor = base + mc_excess × rate
        """
        mc_excess = max(0, mc_pct - self.MC_REFERENCE)
        factor = self.LAMINATION_BASE_FACTOR + mc_excess * self.LAMINATION_MC_FACTOR
        return base_shrinkage_mm * factor

    def k_factor_shift(self, mc_pct: float, length_mm: float = 300) -> float:
        """
        K因子MC偏移
        
        正常范围(8-12%): K基本稳定
        12-16%: K缓慢下降
        ≥16%: K骤降(湿态相变)
        """
        if mc_pct <= self.MC_SAFE_MAX:
            return 0.0
        elif mc_pct < self.MC_PHASE_CHANGE:
            # 线性下降区: 每超1%MC, K下降约0.01
            delta_k = (mc_pct - self.MC_SAFE_MAX) * 0.01
            return delta_k * length_mm * 0.001  # K偏移对展开尺寸的影响
        else:
            # 相变跳变
            delta_k = self.K_NORMAL - self.K_PHASE_CHANGED  # 0.12
            # 加上渐变部分
            pre_delta = (self.MC_PHASE_CHANGE - self.MC_SAFE_MAX) * 0.01
            total_delta = delta_k + pre_delta
            return total_delta * length_mm * 0.001

    def curl_warp_estimate(self, mc_pct: float, thickness_mm: float) -> float:
        """
        卷曲/翘曲估算
        
        MC不均匀→内外层差异→卷曲
        """
        mc_deviation = abs(mc_pct - self.MC_REFERENCE)
        if mc_deviation < 1.0:
            return 0.0
        
        # 卷曲量与MC偏差和厚度相关
        # 简化: Δcurl ≈ α × ΔMC² × t (二次关系)
        alpha = 0.002  # 经验系数
        return alpha * mc_deviation ** 2 * thickness_mm

    def compute_full_error_budget(self, profile: MCProfile, length_mm: float = 300) -> MCErrorBudget:
        """
        计算MC对误差预算的完整贡献
        
        包含: 直接收缩 + 滞后 + 裱合耦合 + K偏移 + 卷曲 + 相变
        """
        mc = profile.mc_pct
        material_sens = self.MATERIAL_MC_SENSITIVITY.get(profile.material_type, 1.0)
        
        # 1. 直接收缩 (S型曲线)
        md_shrink_pct = self.logistic_shrinkage(mc, "MD") * material_sens
        cd_shrink_pct = self.logistic_shrinkage(mc, "CD") * material_sens
        direct_md = md_shrink_pct / 100.0 * length_mm
        direct_cd = cd_shrink_pct / 100.0 * length_mm
        direct_total = math.sqrt(direct_md**2 + direct_cd**2)  # 向量合成
        
        # 2. 滞后效应
        hysteresis = self.hysteresis_correction(mc, profile.path, length_mm)
        
        # 3. 裱合耦合放大
        lam_coupling = self.lamination_coupling(mc, direct_total)
        
        # 4. K因子偏移
        k_shift = self.k_factor_shift(mc, length_mm)
        
        # 5. 卷曲翘曲
        curl = self.curl_warp_estimate(mc, profile.thickness_mm)
        
        # 6. 相变跳变
        phase_change = 0.0
        if mc >= self.MC_PHASE_CHANGE:
            # 相变导致收缩率突变
            phase_change = 0.15 * length_mm * 0.001 * material_sens  # ~0.045mm/300mm
        
        # 7. RSS合成
        components = [direct_total, hysteresis, lam_coupling, k_shift, curl, phase_change]
        rss = math.sqrt(sum(c**2 for c in components))
        
        # 安全系数
        zone = self.classify_zone(mc)
        if zone == MCZone.SAFE:
            k_safety = 1.0
        elif zone == MCZone.WARNING:
            k_safety = 1.1
        elif zone == MCZone.DANGER:
            k_safety = 1.3
        elif zone == MCZone.CRITICAL:
            k_safety = 1.5  # 高不确定性
        else:
            k_safety = 1.2  # DEHYDRATED
        
        return MCErrorBudget(
            direct_shrinkage_mm=round(direct_total, 4),
            hysteresis_mm=round(hysteresis, 4),
            lamination_coupling_mm=round(lam_coupling, 4),
            k_factor_shift_mm=round(k_shift, 4),
            curl_warp_mm=round(curl, 4),
            phase_change_mm=round(phase_change, 4),
            rss_total_mm=round(rss * k_safety, 4),
            safety_factor=k_safety,
        )

    def compute_shrinkage(self, profile: MCProfile, length_mm: float = 300) -> ShrinkageResult:
        """
        计算收缩(简化接口)
        """
        mc = profile.mc_pct
        material_sens = self.MATERIAL_MC_SENSITIVITY.get(profile.material_type, 1.0)
        
        md_pct = self.logistic_shrinkage(mc, "MD") * material_sens
        cd_pct = self.logistic_shrinkage(mc, "CD") * material_sens
        
        md_mm = md_pct / 100.0 * length_mm
        cd_mm = cd_pct / 100.0 * length_mm
        net_mm = math.sqrt(md_mm**2 + cd_mm**2)
        
        hysteresis = self.hysteresis_correction(mc, profile.path, length_mm)
        
        zone = self.classify_zone(mc)
        phase_change = mc >= self.MC_PHASE_CHANGE
        
        # 置信度
        if zone == MCZone.SAFE:
            confidence = 0.95
        elif zone == MCZone.WARNING:
            confidence = 0.80
        elif zone == MCZone.DANGER:
            confidence = 0.60
        elif zone == MCZone.CRITICAL:
            confidence = 0.30
        else:
            confidence = 0.70
        
        return ShrinkageResult(
            linear_shrinkage_pct=round(md_pct, 3),
            md_shrinkage_mm=round(md_mm, 4),
            cd_shrinkage_mm=round(cd_mm, 4),
            net_error_mm=round(net_mm, 4),
            zone=zone,
            phase_change=phase_change,
            hysteresis_mm=round(hysteresis, 4),
            confidence=confidence,
        )

    def mc_equilibrium_time(self, target_mc: float, current_mc: float, 
                             thickness_mm: float, temperature_c: float = 23.0) -> float:
        """
        MC平衡时间估算
        
        τ = α × t² / (1 + β × T)
        α: 材料扩散系数
        t: 厚度
        T: 温度(加速因子)
        """
        alpha = 0.5  # 瓦楞纸板经验扩散系数 (hours/mm²)
        beta = 0.05  # 温度加速因子 (/°C)
        tau = alpha * thickness_mm**2 / (1 + beta * (temperature_c - 20))
        # 达到90%平衡需要 2.3τ
        return tau * 2.3

    def recommend_mc_control(self, profile: MCProfile, tolerance_target_mm: float = 0.5) -> Dict:
        """
        MC控制建议
        
        给定目标公差, 反推允许的MC范围
        """
        budget = self.compute_full_error_budget(profile)
        
        # 反推: RSS_total ≤ tolerance_target
        # 去掉安全系数: rss_raw ≤ tolerance / k
        # MC主要贡献来自direct_shrinkage + lamination_coupling
        # 简化: 允许的MC偏差 → 查表
        
        zone = self.classify_zone(profile.mc_pct)
        
        # MC对误差的贡献占总RSS的比例(经验值)
        mc_contribution_pct = 0.65  # MC约占65%的总误差
        
        # 允许MC误差 = tolerance × 0.65 (MC贡献部分)
        allowed_mc_error = tolerance_target_mm * mc_contribution_pct
        
        # 反推MC范围(使用S型曲线近似)
        # 在SAFE区(8-12%), 收缩率约0.1-0.4%/300mm
        # 直接搜索MC范围
        best_mc_range = self._find_mc_range(profile.material_type, allowed_mc_error, 300)
        
        recommendations = []
        
        if zone == MCZone.CRITICAL:
            recommendations.append("⚠️ MC≥16%触发湿态相变, 必须立即烘干或停止生产")
        elif zone == MCZone.DANGER:
            recommendations.append("🔴 MC在危险区, 强烈建议除湿至12%以下")
        elif zone == MCZone.WARNING:
            recommendations.append("🟡 MC偏高, 建议控制车间湿度(目标45-55%RH)")
        
        if best_mc_range:
            recommendations.append(
                f"目标公差±{tolerance_target_mm}mm时, 建议MC范围: "
                f"{best_mc_range[0]:.1f}-{best_mc_range[1]:.1f}%"
            )
            
            if profile.mc_pct > best_mc_range[1]:
                eq_time = self.mc_equilibrium_time(
                    best_mc_range[0],
                    profile.mc_pct, profile.thickness_mm, profile.temperature_c
                )
                recommendations.append(
                    f"预估平衡时间: {eq_time:.1f}小时 (厚度{profile.thickness_mm}mm, "
                    f"{profile.temperature_c}°C)"
                )
        else:
            recommendations.append(
                f"目标公差±{tolerance_target_mm}mm在当前MC({profile.mc_pct}%)下无法达成"
            )
        
        # 材料敏感度
        sens = self.MATERIAL_MC_SENSITIVITY.get(profile.material_type, 1.0)
        if sens > 1.2:
            recommendations.append(f"此材料MC敏感度高({sens}x), 需要更严格的MC控制")
        
        # 路径提示
        if profile.path == MCPath.ABSORB:
            recommendations.append("当前吸湿路径: 收缩率高于脱湿路径, 注意滞后效应")
        
        return {
            "current_mc": profile.mc_pct,
            "current_zone": zone.value,
            "mc_error_budget_mm": budget.rss_total_mm,
            "mc_contribution_pct": mc_contribution_pct,
            "recommended_mc_range": best_mc_range,
            "equilibrium_time_hours": self.mc_equilibrium_time(
                10, profile.mc_pct, profile.thickness_mm, profile.temperature_c
            ) if profile.mc_pct > 12 else 0,
            "recommendations": recommendations,
        }

    def _find_mc_range(self, material_type: str, allowed_error_mm: float, 
                        length_mm: float) -> Optional[Tuple[float, float]]:
        """反推允许MC范围"""
        sens = self.MATERIAL_MC_SENSITIVITY.get(material_type, 1.0)
        
        best_low = 6.0
        best_high = 14.0
        
        # 搜索下限
        for mc in [x * 0.5 for x in range(12, 40)]:  # 6-20%
            shrink = self.logistic_shrinkage(mc, "MD") * sens / 100.0 * length_mm
            lam = self.lamination_coupling(mc, shrink)
            total = math.sqrt(shrink**2 + lam**2)
            if total <= allowed_error_mm:
                best_low = mc
                break
        
        # 搜索上限
        for mc in [x * 0.5 for x in range(40, 12, -1)]:  # 20-6%
            shrink = self.logistic_shrinkage(mc, "MD") * sens / 100.0 * length_mm
            lam = self.lamination_coupling(mc, shrink)
            hyst = self.hysteresis_correction(mc, MCPath.ABSORB, length_mm)
            total = math.sqrt(shrink**2 + lam**2 + hyst**2)
            if total <= allowed_error_mm:
                best_high = mc
                break
        
        return (best_low, best_high)

    def simulate_mc_timeline(self, profile: MCProfile, 
                              target_mc: float, hours: float = 48,
                              steps: int = 24) -> List[Dict]:
        """
        模拟MC随时间的变化
        
        指数衰减模型: MC(t) = MC_target + (MC_0 - MC_target) × exp(-t/τ)
        """
        tau = self.mc_equilibrium_time(target_mc, profile.mc_pct, 
                                        profile.thickness_mm, profile.temperature_c)
        tau = max(tau, 0.5)  # 最小0.5小时
        
        timeline = []
        mc_0 = profile.mc_pct
        
        for i in range(steps + 1):
            t = hours * i / steps
            mc_t = target_mc + (mc_0 - target_mc) * math.exp(-t / tau)
            
            # 更新profile并计算误差
            temp_profile = MCProfile(
                mc_pct=mc_t,
                path=profile.path,
                temperature_c=profile.temperature_c,
                humidity_rh=profile.humidity_rh,
                material_type=profile.material_type,
                thickness_mm=profile.thickness_mm,
            )
            budget = self.compute_full_error_budget(temp_profile)
            zone = self.classify_zone(mc_t)
            
            timeline.append({
                "hour": round(t, 1),
                "mc_pct": round(mc_t, 2),
                "zone": zone.value,
                "error_budget_mm": budget.rss_total_mm,
                "phase_change": mc_t >= self.MC_PHASE_CHANGE,
            })
        
        return timeline

    def generate_report(self, profile: MCProfile, length_mm: float = 300) -> Dict:
        """生成MC综合影响报告"""
        budget = self.compute_full_error_budget(profile, length_mm)
        shrinkage = self.compute_shrinkage(profile, length_mm)
        control = self.recommend_mc_control(profile)
        
        # S型曲线采样
        curve = []
        for mc in [x * 0.5 for x in range(8, 40)]:  # 4-20%
            s = self.logistic_shrinkage(mc, "MD")
            curve.append({"mc": mc, "shrinkage_pct": round(s, 3)})
        
        return {
            "profile": {
                "mc_pct": profile.mc_pct,
                "material": profile.material_type,
                "thickness_mm": profile.thickness_mm,
                "path": profile.path.value,
                "temperature_c": profile.temperature_c,
                "humidity_rh": profile.humidity_rh,
            },
            "zone": shrinkage.zone.value,
            "phase_change_warning": shrinkage.phase_change,
            "shrinkage": {
                "md_mm": shrinkage.md_shrinkage_mm,
                "cd_mm": shrinkage.cd_shrinkage_mm,
                "net_mm": shrinkage.net_error_mm,
                "hysteresis_mm": shrinkage.hysteresis_mm,
            },
            "error_budget": {
                "direct_mm": budget.direct_shrinkage_mm,
                "hysteresis_mm": budget.hysteresis_mm,
                "lamination_mm": budget.lamination_coupling_mm,
                "k_shift_mm": budget.k_factor_shift_mm,
                "curl_mm": budget.curl_warp_mm,
                "phase_change_mm": budget.phase_change_mm,
                "rss_total_mm": budget.rss_total_mm,
                "safety_factor": budget.safety_factor,
            },
            "control_recommendations": control["recommendations"],
            "s_curve_sample": curve[:10],
        }


# === 测试 ===
if __name__ == "__main__":
    model = MCComprehensiveModel()
    
    print("=" * 60)
    print("  MC含水量综合影响模型")
    print("=" * 60)
    
    # 1. S型曲线验证
    print("\n--- S型Logistic收缩曲线 ---")
    print(f"{'MC%':>6} {'MD收缩%':>8} {'CD收缩%':>8} {'分区':>10}")
    for mc in [6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20]:
        md = model.logistic_shrinkage(mc, "MD")
        cd = model.logistic_shrinkage(mc, "CD")
        zone = model.classify_zone(mc).value
        print(f"{mc:>6.1f} {md:>8.3f} {cd:>8.3f} {zone:>10}")
    
    # 2. 滞后效应
    print("\n--- 吸湿滞后效应 ---")
    print(f"{'MC%':>6} {'吸湿路径':>10} {'脱湿路径':>10} {'差异mm':>8}")
    for mc in [8, 10, 12, 14, 16]:
        absorb = model.hysteresis_correction(mc, MCPath.ABSORB, 300)
        desorb = model.hysteresis_correction(mc, MCPath.DESORB, 300)
        diff = model.hysteresis_correction(mc, MCPath.ABSORB, 300) + model.hysteresis_correction(mc, MCPath.DESORB, 300)
        print(f"{mc:>6.1f} {absorb:>10.4f} {desorb:>10.4f} {diff:>8.4f}")
    
    # 3. 完整误差预算
    print("\n--- MC误差预算 (单瓦楞, 300mm) ---")
    print(f"{'MC%':>6} {'直接':>8} {'滞后':>8} {'裱合':>8} {'K偏移':>8} {'RSS':>8} {'k安全':>6}")
    for mc in [8, 10, 11, 12, 13, 14, 15, 16]:
        profile = MCProfile(mc_pct=mc, path=MCPath.ABSORB, material_type="single_wall", thickness_mm=3.0)
        budget = model.compute_full_error_budget(profile, 300)
        print(f"{mc:>6.1f} {budget.direct_shrinkage_mm:>8.4f} "
              f"{budget.hysteresis_mm:>8.4f} {budget.lamination_coupling_mm:>8.4f} "
              f"{budget.k_factor_shift_mm:>8.4f} {budget.rss_total_mm:>8.4f} "
              f"{budget.safety_factor:>6.1f}")
    
    # 4. 材料对比
    print("\n--- 材料MC敏感度对比 (MC=12%, 300mm) ---")
    for mat in ["grayboard", "single_wall", "double_wall", "micro_flute", "plastic"]:
        profile = MCProfile(mc_pct=12, material_type=mat, 
                           thickness_mm={"grayboard": 2.0, "single_wall": 3.0, 
                                        "double_wall": 7.0, "micro_flute": 1.5, 
                                        "plastic": 0.5}[mat])
        budget = model.compute_full_error_budget(profile, 300)
        sens = model.MATERIAL_MC_SENSITIVITY[mat]
        print(f"  {mat:>15}: RSS={budget.rss_total_mm:.4f}mm, 敏感度={sens}x")
    
    # 5. MC控制建议
    print("\n--- MC控制建议 ---")
    for mc in [10, 13, 16]:
        profile = MCProfile(mc_pct=mc, material_type="single_wall", thickness_mm=3.0)
        ctrl = model.recommend_mc_control(profile, 0.5)
        print(f"\n  MC={mc}%: {ctrl['current_zone']}")
        for rec in ctrl["recommendations"]:
            print(f"    {rec}")
    
    # 6. MC时间线模拟
    print("\n--- MC平衡时间线 (20%→10%, 3mm) ---")
    profile = MCProfile(mc_pct=20, material_type="single_wall", thickness_mm=3.0)
    timeline = model.simulate_mc_timeline(profile, 10.0, hours=48, steps=8)
    for t in timeline:
        phase_warn = " ⚠️相变" if t["phase_change"] else ""
        print(f"  {t['hour']:>5.1f}h: MC={t['mc_pct']:.1f}% "
              f"误差={t['error_budget_mm']:.4f}mm [{t['zone']}]{phase_warn}")
    
    # 7. 关键已知验证
    print("\n--- 已知验证 ---")
    # F28: ±0.5mm不可达(Bobst=0.687mm)
    profile_bobst = MCProfile(mc_pct=12, material_type="single_wall", thickness_mm=3.0)
    budget_bobst = model.compute_full_error_budget(profile_bobst, 300)
    print(f"F28验证: MC=12%时MC贡献={budget_bobst.rss_total_mm:.4f}mm "
          f"(Bobst总RSS=0.687mm, MC占比={budget_bobst.rss_total_mm/0.687*100:.1f}%)")
    
    # F4: 吸湿滞后
    hyst = model.hysteresis_correction(12, MCPath.ABSORB, 300)
    print(f"F4验证: 吸湿滞后@12%/300mm = {hyst:.4f}mm")
    
    # F27: 相变
    profile_wet = MCProfile(mc_pct=17, material_type="single_wall", thickness_mm=3.0)
    budget_wet = model.compute_full_error_budget(profile_wet, 300)
    print(f"F27验证: MC=17%相变, 误差从{budget_bobst.rss_total_mm:.4f}→{budget_wet.rss_total_mm:.4f}mm")
