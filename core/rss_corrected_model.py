"""
RSS非正态分布修正模型
======================
已知(F1): 误差三分类 — 确定性(代数叠加) + 半确定性(RSS) + 随机(RSS)
问题: RSS假设正态分布, 但实际分布类型多样

从节点数据确认的分布类型:
  - 机器精度: 均匀分布 (物理极限)
  - 裱合滑移: 偏态分布 (方向性)
  - 圆压圆模切: 瑞利分布 (位置度)
  - 厚度波动: 正态分布 (大批量统计)
  - 热漂移: 线性趋势 + 正态噪声

修正策略:
  标准RSS: σ_total = √(Σσᵢ²)  [正态假设]
  修正RSS: σ_total = √(Σ(k_dist_i × σᵢ)²)  [分布修正]
  
  k_dist: 分布类型 → RSS权重修正系数
    正态分布:   k=1.00 (无修正)
    均匀分布:   k=1.15 (尾部更厚, 风险更高)
    偏态分布:   k=1.20 (方向性偏移)
    瑞利分布:   k=1.10 (单侧分布)
    线性趋势:   k=1.30 (系统性, 不可统计消除)
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import math


class DistributionType(Enum):
    """误差分布类型"""
    NORMAL = "正态分布"       # 厚度波动, 大批量统计
    UNIFORM = "均匀分布"      # 机器精度物理极限
    SKEWED = "偏态分布"       # 裱合滑移, 方向性偏移
    RAYLEIGH = "瑞利分布"     # 圆压圆模切位置度
    LINEAR_TREND = "线性趋势" # 设备磨损, 热漂移
    EXPONENTIAL = "指数分布"   # MC吸湿/脱湿初期


@dataclass
class ErrorSource:
    """误差源"""
    name: str
    value_mm: float         # 误差值 mm (±范围或σ)
    distribution: DistributionType
    category: str           # "deterministic" | "semi-deterministic" | "random"
    direction: Optional[str] = None  # "MD" | "CD" | None(各向同性)


@dataclass
class RSSResult:
    """RSS计算结果"""
    total_error_mm: float
    deterministic_sum: float
    rss_semi: float
    rss_random: float
    correction_factor: float    # 总修正系数
    naive_rss: float            # 未修正的RSS值
    improvement_pct: float      # vs 线性累加
    warnings: list


class RSSCorrectedModel:
    """
    修正RSS模型
    
    核心公式:
    Δ_total = ΣΔ_det + k_safety × √(Σ(k_dist_i × σ_semi)²) + √(Σ(k_dist_j × σ_rand)²)
    
    其中:
    - Δ_det: 确定性误差, 代数叠加
    - σ_semi: 半确定性误差, RSS叠加 + 分布修正
    - σ_rand: 随机误差, RSS叠加 + 分布修正
    - k_safety: 安全系数 (默认1.15-1.25)
    - k_dist_i: 分布修正系数
    """
    
    # === 分布修正系数 ===
    DIST_CORRECTION = {
        DistributionType.NORMAL:       1.00,
        DistributionType.UNIFORM:      1.15,  # 均匀分布6σ等价需要×√3
        DistributionType.SKEWED:       1.20,  # 偏态: 尾部更厚
        DistributionType.RAYLEIGH:     1.10,  # 瑞利: 单侧
        DistributionType.LINEAR_TREND: 1.30,  # 线性趋势: 不可统计消除
        DistributionType.EXPONENTIAL:  1.15,  # 指数: 初期变化剧烈
    }
    
    # === 安全系数 ===
    SAFETY_FACTORS = {
        'conservative': 1.25,  # 新产品/高风险
        'standard': 1.15,       # 常规产品
        'aggressive': 1.05,     # 大批量成熟产品
    }
    
    def calculate(
        self,
        errors: List[ErrorSource],
        safety: str = 'standard',
        n_sources_threshold: int = 4,
    ) -> RSSResult:
        """
        计算修正RSS总误差
        
        Args:
            errors: 误差源列表
            safety: 安全系数等级
            n_sources_threshold: 误差源数量阈值, 低于此值使用极值法校核
        """
        warnings = []
        
        # 分类
        det_errors = [e for e in errors if e.category == 'deterministic']
        semi_errors = [e for e in errors if e.category == 'semi-deterministic']
        rand_errors = [e for e in errors if e.category == 'random']
        
        # 1. 确定性误差: 代数叠加
        det_sum = sum(abs(e.value_mm) for e in det_errors)
        
        # 2. 半确定性误差: 修正RSS
        semi_rss = self._corrected_rss(semi_errors)
        
        # 3. 随机误差: 修正RSS
        rand_rss = self._corrected_rss(rand_errors)
        
        # 4. 安全系数
        k_safe = self.SAFETY_FACTORS.get(safety, 1.15)
        
        # 5. 总误差
        total = det_sum + k_safe * semi_rss + rand_rss
        
        # 6. 对比线性累加
        linear_sum = sum(abs(e.value_mm) for e in errors)
        naive_rss = math.sqrt(sum(e.value_mm ** 2 for e in errors))
        
        improvement = (1 - total / linear_sum) * 100 if linear_sum > 0 else 0
        
        # 7. 小样本校核 (n < 4 时RSS不可靠)
        if len(errors) < n_sources_threshold:
            extreme = linear_sum
            if total < extreme * 0.8:
                warnings.append(
                    f"⚠️ 误差源仅{len(errors)}个(<{n_sources_threshold}), "
                    f"极值法={extreme:.3f}mm > RSS={total:.3f}mm, 建议使用极值法"
                )
        
        # 8. 分布类型警告
        non_normal = [e for e in errors if e.distribution != DistributionType.NORMAL]
        if non_normal:
            warnings.append(
                f"ℹ️ {len(non_normal)}个非正态分布误差源, 已应用k_dist修正"
            )
        
        return RSSResult(
            total_error_mm=round(total, 3),
            deterministic_sum=round(det_sum, 3),
            rss_semi=round(semi_rss, 3),
            rss_random=round(rand_rss, 3),
            correction_factor=k_safe,
            naive_rss=round(naive_rss, 3),
            improvement_pct=round(improvement, 1),
            warnings=warnings,
        )
    
    def _corrected_rss(self, errors: List[ErrorSource]) -> float:
        """带分布修正的RSS计算"""
        if not errors:
            return 0.0
        sum_sq = sum(
            (self.DIST_CORRECTION.get(e.distribution, 1.0) * e.value_mm) ** 2
            for e in errors
        )
        return math.sqrt(sum_sq)
    
    def compare_safety_levels(self, errors: List[ErrorSource]) -> str:
        """对比不同安全系数等级"""
        lines = [f"{'='*60}"]
        lines.append(f"{'安全等级':<15} {'安全系数':<10} {'总误差(mm)':<12} {'vs线性累加':<12}")
        lines.append(f"{'-'*60}")
        
        linear = sum(abs(e.value_mm) for e in errors)
        for level in ['aggressive', 'standard', 'conservative']:
            r = self.calculate(errors, safety=level)
            pct = r.improvement_pct
            lines.append(
                f"{level:<15} {r.correction_factor:<10.2f} {r.total_error_mm:<12.3f} {pct:+.1f}%"
            )
        lines.append(f"{'-'*60}")
        lines.append(f"{'线性累加(参考)':<15} {'—':<10} {linear:<12.3f}")
        return "\n".join(lines)
    
    def get_dist_table(self) -> str:
        """分布修正系数表"""
        lines = ["分布类型          k_dist    说明"]
        lines.append("-" * 50)
        for dist, k in self.DIST_CORRECTION.items():
            descs = {
                DistributionType.NORMAL: "无修正, RSS标准假设",
                DistributionType.UNIFORM: "尾部更厚, 机器精度极限",
                DistributionType.SKEWED: "方向性偏移, 裱合滑移",
                DistributionType.RAYLEIGH: "单侧分布, 位置度误差",
                DistributionType.LINEAR_TREND: "系统性漂移, 不可统计消除",
                DistributionType.EXPONENTIAL: "初期变化剧烈, MC吸湿",
            }
            lines.append(f"{dist.value:<18} {k:<10.2f} {descs.get(dist, '')}")
        return "\n".join(lines)


# === 预置误差源工厂 ===
def bobst_diecut_errors(length_mm: float = 300) -> List[ErrorSource]:
    """Bobst模切机典型误差源"""
    return [
        ErrorSource("机器精度", 0.15, DistributionType.UNIFORM, "deterministic"),
        ErrorSource("纸张CD膨胀", length_mm * 0.0012, DistributionType.NORMAL, "random"),
        ErrorSource("裱合滑移", 0.08, DistributionType.SKEWED, "semi-deterministic", "CD"),
        ErrorSource("热漂移(30min)", 0.06, DistributionType.LINEAR_TREND, "semi-deterministic"),
        ErrorSource("刀具磨损", 0.03, DistributionType.LINEAR_TREND, "deterministic"),
        ErrorSource("厚度波动", 0.05, DistributionType.NORMAL, "random"),
        ErrorSource("扇形误差", length_mm**2 / (8 * 800) * 0.001, DistributionType.RAYLEIGH, "semi-deterministic"),
    ]

def domestic_diecut_errors(length_mm: float = 300) -> List[ErrorSource]:
    """国产模切机典型误差源"""
    return [
        ErrorSource("机器精度", 0.30, DistributionType.UNIFORM, "deterministic"),
        ErrorSource("纸张CD膨胀", length_mm * 0.0018, DistributionType.NORMAL, "random"),
        ErrorSource("裱合滑移", 0.15, DistributionType.SKEWED, "semi-deterministic", "CD"),
        ErrorSource("热漂移(30min)", 0.10, DistributionType.LINEAR_TREND, "semi-deterministic"),
        ErrorSource("刀具磨损", 0.05, DistributionType.LINEAR_TREND, "deterministic"),
        ErrorSource("厚度波动", 0.10, DistributionType.NORMAL, "random"),
        ErrorSource("扇形误差", length_mm**2 / (8 * 800) * 0.001, DistributionType.RAYLEIGH, "semi-deterministic"),
    ]


if __name__ == "__main__":
    model = RSSCorrectedModel()
    
    print(model.get_dist_table())
    print()
    
    # Bobst场景
    print("=" * 60)
    print("  Bobst SP106 — 300mm CD方向模切")
    print("=" * 60)
    bobst = bobst_diecut_errors(300)
    r = model.calculate(bobst)
    print(f"确定性(代数叠加): {r.deterministic_sum:.3f}mm")
    print(f"半确定性(修正RSS): {r.rss_semi:.3f}mm")
    print(f"随机(修正RSS):     {r.rss_random:.3f}mm")
    print(f"总误差(修正RSS):   {r.total_error_mm:.3f}mm (k_safe={r.correction_factor})")
    print(f"天真RSS:           {r.naive_rss:.3f}mm")
    print(f"vs线性累加:        {r.improvement_pct:+.1f}%")
    for w in r.warnings:
        print(f"  {w}")
    
    print("\n" + model.compare_safety_levels(bobst))
    
    # 国产机场景
    print("\n" + "=" * 60)
    print("  国产平压平 — 300mm CD方向模切")
    print("=" * 60)
    domestic = domestic_diecut_errors(300)
    r2 = model.calculate(domestic)
    print(f"总误差(修正RSS): {r2.total_error_mm:.3f}mm")
    print(f"vs线性累加:      {r2.improvement_pct:+.1f}%")
    print(f"Bobst vs 国产差异: {r2.total_error_mm - r.total_error_mm:.3f}mm")
    
    # 精度校核: ±0.5mm目标可达性
    print(f"\n--- 精度校核 ---")
    target = 0.5
    for name, errs, target in [("Bobst", bobst, 0.5), ("国产", domestic, 0.5)]:
        r = model.calculate(errs)
        status = "✅ 可达" if r.total_error_mm <= target else "❌ 不可达"
        print(f"{name} ±{target}mm: {status} (实际{r.total_error_mm:.3f}mm)")
