"""
standards_database.py — 国际标准公式数据库
基于 REAL_SUCCESS 节点确认的 FEFCO/ECMA/GB/ISO/JIS 标准

标准优先级（从严到松）：
  ECMA ±0.3mm > FEFCO ±0.5mm > GB/T ±1-2mm
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class StandardOrg(Enum):
    FEFCO = "FEFCO"        # 欧洲瓦楞纸箱联合会
    ECMA = "ECMA"          # 欧洲纸盒标准
    GB = "GB/T"            # 中国国家标准
    ISO = "ISO"            # 国际标准
    JIS = "JIS"            # 日本工业标准
    DIN = "DIN"            # 德国标准
    BRCGS = "BRCGS"        # 食品安全标准


class ToleranceGrade(Enum):
    PRECISION = "precision"    # 精密 ±0.254-0.3mm
    STANDARD = "standard"      # 标准 ±0.5mm
    COMMERCIAL = "commercial"  # 商业 ±1.0mm
    INDUSTRIAL = "industrial"  # 工业 ±1.5-2.0mm


@dataclass
class ToleranceSpec:
    """公差规格"""
    org: StandardOrg
    grade: ToleranceGrade
    tolerance_mm: float
    size_threshold_mm: float = 500  # 尺寸分界线
    tolerance_large_mm: float = 0   # >500mm时的公差
    dimension_basis: str = "inner"  # inner=内尺寸, outer=外尺寸
    note: str = ""


# ==================== 已确认标准公差 ====================

TOLERANCES = {
    # ECMA — 最严
    "ecma_precision": ToleranceSpec(
        org=StandardOrg.ECMA, grade=ToleranceGrade.PRECISION,
        tolerance_mm=0.30, dimension_basis="inner",
        note="欧洲高端包装要求，高档烟包/药盒",
    ),
    # FEFCO — 标准
    "fefco_small": ToleranceSpec(
        org=StandardOrg.FEFCO, grade=ToleranceGrade.STANDARD,
        tolerance_mm=0.50, size_threshold_mm=500,
        tolerance_large_mm=1.0, dimension_basis="inner",
        note="尺寸<500mm时±0.5mm，>500mm时±1.0mm",
    ),
    # GB/T — 宽松 (注意: GB/T 6543-2008运输包装优等品±3mm, 节点1838修正)
    "gb_commercial": ToleranceSpec(
        org=StandardOrg.GB, grade=ToleranceGrade.COMMERCIAL,
        tolerance_mm=1.0, size_threshold_mm=500,
        tolerance_large_mm=3.0, dimension_basis="outer",
        note="运输包装GB/T 6543-2008: 优等品±3mm(≤1000mm); 销售包装GB/T 27928.1: ±1mm",
    ),
    # ISO
    "iso_precision": ToleranceSpec(
        org=StandardOrg.ISO, grade=ToleranceGrade.PRECISION,
        tolerance_mm=0.254, dimension_basis="inner",
        note="IADD标准 ±0.254mm（±0.01英寸）",
    ),
}


@dataclass
class DesignRule:
    """设计规则"""
    name: str
    org: StandardOrg
    formula: str
    description: str
    source_node: str


# ==================== 已确认设计规则 ====================

DESIGN_RULES = {
    "fefco_001_tongue_depth": DesignRule(
        name="插舌最小深度",
        org=StandardOrg.FEFCO,
        formula="min_depth = max(15mm, 0.3 × W)",
        description="插舌深度不足导致盒盖弹开",
        source_node="0005",
    ),
    "fefco_002_dust_flap": DesignRule(
        name="防尘翼重叠",
        org=StandardOrg.FEFCO,
        formula="O_flap ≥ 0.5 × W_adjacent",
        description="重叠不足导致结构失稳",
        source_node="0006",
    ),
    "fefco_003_score_edge": DesignRule(
        name="压线到边缘距离",
        org=StandardOrg.FEFCO,
        formula="d_score_edge ≥ 2 × t_board",
        description="距离不足导致边缘撕裂",
        source_node="0007",
    ),
    "fefco_004_score_width": DesignRule(
        name="压痕宽度",
        org=StandardOrg.FEFCO,
        formula="W = t + k (k=0.5-1.0mm)",
        description="FEFCO强调三角槽形态",
        source_node="0004",
    ),
    "fefco_005_tongue_slot": DesignRule(
        name="插舌-插口配合",
        org=StandardOrg.FEFCO,
        formula="tongue = slot - 1.5×t - 0.5mm",
        description="锁底配合间隙",
        source_node="0056",
    ),
}


def get_tolerance(org: StandardOrg, size_mm: float, grade: ToleranceGrade = None) -> float:
    """
    获取指定标准的公差值
    
    Args:
        org: 标准组织
        size_mm: 产品尺寸
        grade: 公差等级（可选）
    
    Returns:
        公差值 (mm)
    """
    if org == StandardOrg.ECMA:
        return TOLERANCES["ecma_precision"].tolerance_mm
    elif org == StandardOrg.FEFCO:
        spec = TOLERANCES["fefco_small"]
        if size_mm > spec.size_threshold_mm:
            return spec.tolerance_large_mm
        return spec.tolerance_mm
    elif org == StandardOrg.GB:
        spec = TOLERANCES["gb_commercial"]
        if size_mm > spec.size_threshold_mm:
            return spec.tolerance_large_mm
        return spec.tolerance_mm
    elif org == StandardOrg.ISO:
        return TOLERANCES["iso_precision"].tolerance_mm
    else:
        return TOLERANCES["fefco_small"].tolerance_mm  # 默认FEFCO


def get_strictest_tolerance(size_mm: float) -> dict:
    """
    获取最严标准公差（出口订单用）
    
    已知：ECMA(±0.3) > FEFCO(±0.5) > GB(±1-2)
    
    Returns:
        dict with org, tolerance, note
    """
    candidates = []
    for org in [StandardOrg.ECMA, StandardOrg.FEFCO, StandardOrg.ISO]:
        tol = get_tolerance(org, size_mm)
        candidates.append({"org": org.value, "tolerance_mm": tol})
    
    candidates.sort(key=lambda x: x["tolerance_mm"])
    return candidates[0]


def check_design_rules(
    tongue_depth_mm: float = None,
    box_width_mm: float = None,
    dust_flap_mm: float = None,
    adjacent_width_mm: float = None,
    score_edge_dist_mm: float = None,
    board_thickness_mm: float = None,
    score_width_mm: float = None,
) -> List[dict]:
    """
    检查设计规则合规性
    
    Returns:
        list of check results
    """
    results = []
    
    if tongue_depth_mm and box_width_mm:
        min_depth = max(15, 0.3 * box_width_mm)
        results.append({
            "rule": "fefco_001_tongue_depth",
            "check": f"插舌深度 ≥ max(15, 0.3×{box_width_mm:.0f}) = {min_depth:.1f}mm",
            "actual": tongue_depth_mm,
            "passes": tongue_depth_mm >= min_depth,
        })
    
    if dust_flap_mm and adjacent_width_mm:
        min_overlap = 0.5 * adjacent_width_mm
        results.append({
            "rule": "fefco_002_dust_flap",
            "check": f"防尘翼 ≥ 0.5×{adjacent_width_mm:.0f} = {min_overlap:.1f}mm",
            "actual": dust_flap_mm,
            "passes": dust_flap_mm >= min_overlap,
        })
    
    if score_edge_dist_mm and board_thickness_mm:
        min_dist = 2 * board_thickness_mm
        results.append({
            "rule": "fefco_003_score_edge",
            "check": f"压线边缘 ≥ 2×{board_thickness_mm:.1f} = {min_dist:.1f}mm",
            "actual": score_edge_dist_mm,
            "passes": score_edge_dist_mm >= min_dist,
        })
    
    if score_width_mm and board_thickness_mm:
        min_w = board_thickness_mm + 0.5
        max_w = board_thickness_mm + 1.0
        results.append({
            "rule": "fefco_004_score_width",
            "check": f"压痕宽 {min_w:.1f}-{max_w:.1f}mm",
            "actual": score_width_mm,
            "passes": min_w <= score_width_mm <= max_w,
        })
    
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("国际标准公式数据库 v1.0")
    print("=" * 60)

    # 1. 公差对比
    print("\n--- 标准公差对比 ---")
    for size in [100, 300, 500, 800]:
        ecma = get_tolerance(StandardOrg.ECMA, size)
        fefco = get_tolerance(StandardOrg.FEFCO, size)
        gb = get_tolerance(StandardOrg.GB, size)
        iso = get_tolerance(StandardOrg.ISO, size)
        strictest = get_strictest_tolerance(size)
        print(f"  L={size}mm: ECMA=±{ecma}mm, FEFCO=±{fefco}mm, "
              f"GB=±{gb}mm, ISO=±{iso}mm, 最严={strictest['org']}")

    # 2. 设计规则检查
    print("\n--- 设计规则检查示例 ---")
    checks = check_design_rules(
        tongue_depth_mm=18, box_width_mm=50,
        dust_flap_mm=35, adjacent_width_mm=80,
        score_edge_dist_mm=1.0, board_thickness_mm=0.4,
        score_width_mm=1.2,
    )
    for c in checks:
        icon = "✅" if c["passes"] else "❌"
        print(f"  {icon} {c['rule']}: {c['check']} (实际={c['actual']}mm)")

    print("\n" + "=" * 60)
    print("✅ 完成")


# FEFCO 设计规则（从 confirmed_knowledge_base 提取）
FEFCO_DESIGN_RULES = {
    "FEFCO-001": {
        "name": "插舌最小深度",
        "formula": "t_min >= 15mm 或 t >= 0.3 × W",
        "risk": "盒盖弹开",
        "category": "结构安全",
    },
    "FEFCO-003": {
        "name": "压线到边缘距离",
        "formula": "d >= 2 × t_board",
        "risk": "边缘撕裂",
        "category": "结构安全",
    },
    "FEFCO-004": {
        "name": "摇盖折叠半径",
        "formula": "R_fold = t × (1 + E/G)",
        "risk": "纸板断裂",
        "category": "结构安全",
        "note": "E=弹性模量, G=剪切模量",
    },
    "FEFCO-005": {
        "name": "承重面最小宽度",
        "formula": "W >= F_max / (σ_crush × L)",
        "risk": "压溃失效",
        "category": "承重安全",
        "note": "F_max=最大载荷, σ_crush=边压强度, L=长度",
    },
    "FEFCO-0201_tolerance": {
        "name": "0201箱型公差(线性分段)",
        "rules": [
            {"max_L": 300, "tolerance_mm": 0.5},
            {"max_L": 600, "tolerance_mm": 1.0},
            {"max_L": 1000, "tolerance_mm": 1.5},
            {"max_L": float('inf'), "tolerance_mm": 2.0},
        ],
    },
    "FEFCO-0413_delta": {
        "name": "0413十字隔档槽宽修正",
        "formula": "Delta_jiangzhehu = Delta_europe + 0.2mm",
        "reason": "江浙沪纸张较软，需增加余量",
        "category": "区域修正",
    },
    "FEFCO-Grip": {
        "name": "咬口位",
        "premium": "8-10mm (进口机+FEFCO/DIN)",
        "domestic": ">=12mm (国产机+GB), 老旧机>=15mm",
        "category": "设备约束",
    },
    "JIS-Gflap": {
        "name": "摇盖盖合间隙",
        "formula": "G_flap <= 1mm",
        "standard": "JIS Z 1506",
        "category": "装配精度",
        "note": "要求2D展开精确到小数点后1位",
    },
    "FEFCO-MC": {
        "name": "含水率基准",
        "fefco": "7% ± 1%",
        "gb": "10% ± 2%",
        "impact": "BCT强度偏差15-25%",
        "category": "环境",
    },
}


# 尺寸基准差异
DIMENSION_BASIS_DIFF = {
    "FEFCO": "内尺寸(保护包装容积)",
    "JIS": "外尺寸(优化物流托盘适配)",
    "DIN": "特定场景外尺寸",
    "GB": "混合使用(无明确统一)",
}


def check_fefco_design_rules(length_mm: float = 0, box_width_mm: float = 0,
                              tongue_depth_mm: float = 0, board_thickness_mm: float = 0,
                              grip_type: str = "premium") -> list:
    """
    检查FEFCO设计规则合规性
    
    Args:
        grip_type: "premium" (进口机) 或 "domestic" (国产机)
    
    Returns:
        list of rule checks with pass/fail
    """
    checks = []
    
    # FEFCO-001: 插舌深度
    if tongue_depth_mm > 0:
        min_tongue = max(15, 0.3 * box_width_mm) if box_width_mm > 0 else 15
        checks.append({
            "rule": "FEFCO-001",
            "name": "插舌最小深度",
            "required": f">={min_tongue:.1f}mm",
            "actual": f"{tongue_depth_mm}mm",
            "passes": tongue_depth_mm >= min_tongue,
        })
    
    # FEFCO-003: 压线到边缘
    if board_thickness_mm > 0:
        min_edge = 2 * board_thickness_mm
        # 使用已有的score_edge_dist if available
        checks.append({
            "rule": "FEFCO-003",
            "name": "压线到边缘距离",
            "required": f">={min_edge:.1f}mm",
            "note": f"板厚{board_thickness_mm}mm → 最小{min_edge:.1f}mm",
        })
    
    # 咬口位
    grip_min = 12 if grip_type == "domestic" else 8
    checks.append({
        "rule": "FEFCO-Grip",
        "name": "咬口位",
        "required": f">={grip_min}mm",
        "type": grip_type,
    })
    
    return checks




# ═══════════════════════════════════════════════════════════════
# DiePre 已知事实参数化规则集 (从p_diepre推演涌现)
# ═══════════════════════════════════════════════════════════════

import math

DIEPRE_KNOWN_FACTS = {
    "F1_error_classification": {
        "name": "误差三分类",
        "description": "确定性(代数叠加) + 半确定性(RSS) + 随机(RSS)",
        "formula": "total = Σ(deterministic) + √(Σ(semi²)) + √(Σ(random²))",
    },
    "F2_rss_correction": {
        "name": "RSS修正系数",
        "description": "安全系数k=1.15-1.25, 方向因子K_dir, 环境因子K_env",
        "formula": "rss_corrected = k × K_dir × K_env × √(Σ(σᵢ²))",
        "params": {"k": (1.15, 1.25), "K_dir": 1.0, "K_env": 1.0},
    },
    "F3_bobst_vs_domestic": {
        "name": "Bobst vs 国产精度",
        "description": "Bobst ±0.15mm, 国产 ±0.30mm, 国产贡献率45%",
        "formula": "bobst_tol = 0.15mm, domestic_tol = 0.30mm",
    },
    "F4_moisture_hysteresis": {
        "name": "吸湿滞后效应",
        "description": "吸湿/脱湿路径收缩率不同 k_absorb ≠ k_desorb",
        "formula": "Δ_absorb = k_abs × ΔMC, Δ_desorb = k_desorb × ΔMC, k_absorb > k_desorb",
    },
    "F5_s_curve": {
        "name": "S型收缩曲线",
        "description": "Logistic模型, 收缩率在MC 8-16%区间渐变",
        "formula": "shrinkage(MC) = l_max / (1 + exp(-k × (MC - MC_mid)))",
        "params": {"k": 0.8, "MC_mid": 12.0, "l_max_pct": 1.2},
    },
    "F6_asia_collapse": {
        "name": "亚洲纸板塌陷补偿",
        "description": "亚洲纸板需额外+0.1-0.2mm, 欧洲0",
        "formula": "collapse_comp = 0.15mm (Asia) or 0mm (Europe)",
    },
    "F7_strip_angle": {
        "name": "清废临界角",
        "description": "θ ≈ 15° + 5° × ln(t), t=材料厚度mm",
        "formula": "θ = 15 + 5 × ln(t)",
    },
    "F8_mc_compatible": {
        "name": "MC兼容范围",
        "description": "±2% MC保守值",
        "formula": "ΔMC_max = 2%",
    },
    "F9_fan_error": {
        "name": "扇形误差",
        "description": "Δfan ≈ L²/(8R) + 热膨胀, 离心力可忽略",
        "formula": "Δfan = L²/(8R) + α×ΔT×L",
    },
    "F10_bobst_thermal": {
        "name": "Bobst圆压圆热膨胀",
        "description": "0.05-0.08mm/30min",
        "formula": "Δ_thermal = 0.065mm/30min (avg)",
    },
    "F11_heidelberg_tooth": {
        "name": "Heidelberg高刚性",
        "description": "允许0.8mm齿刀",
        "formula": "max_tooth = 0.8mm",
    },
    "F12_fefco_tuck": {
        "name": "FEFCO插舌公式",
        "description": "插舌 = 插口 - 1.5×t - 0.5mm",
        "formula": "tuck = slot - 1.5×t - 0.5",
    },
    "F13_export_md_risk": {
        "name": "出口纸箱MD方向风险",
        "description": "MD方向不一致→相对位移",
        "formula": "Δ_displacement ∝ |MD1 - MD2| × humidity_change",
    },
    "F14_roll_direction": {
        "name": "卷曲方向规则",
        "description": "卷筒→MD方向, 裱合板→刚性大侧",
        "formula": "MD = roll_direction, rigid_side = max(stiffness_A, stiffness_B)",
    },
    "F15_mc_is_enemy": {
        "name": "含水量=精度最大敌人",
        "description": "MC波动1%→尺寸变化0.1-0.3%",
        "formula": "Δ_size ≈ 0.2% × ΔMC% × L_mm",
    },
    "F16_s_shrinkage": {
        "name": "纸张收缩S型",
        "description": "同F5, 独立强调",
        "formula": "Logistic: k=40-60, MC_mid≈12%",
    },
    "F17_market_specific": {
        "name": "目标市场区分",
        "description": "亚洲/欧洲设计参数不同",
        "formula": "if Asia: collapse_comp=+0.15mm, else: 0",
    },
    "F18_mc_precision": {
        "name": "MC影响精度(重复)",
        "description": "精度最大敌人是MC",
        "formula": "Δ_precision ∝ MC_variance",
    },
}


def calc_strip_angle(thickness_mm: float) -> float:
    """F7: 清废临界角 θ = 15° + 5° × ln(t)"""
    return 15.0 + 5.0 * math.log(max(thickness_mm, 0.1))


def calc_fan_error(length_mm: float, radius_mm: float, delta_t: float = 0) -> float:
    """F9: 扇形误差 Δfan = L²/(8R) + α×ΔT×L"""
    geometric = (length_mm ** 2) / (8 * max(radius_mm, 1))
    thermal = 0.000012 * delta_t * length_mm  # α=12×10⁻⁶/°C (钢辊)
    return geometric + thermal


def calc_fefco_tuck(slot_mm: float, thickness_mm: float) -> float:
    """F12: FEFCO插舌 = 插口 - 1.5×t - 0.5mm"""
    return slot_mm - 1.5 * thickness_mm - 0.5


def calc_mc_expansion(length_mm: float, mc_delta_pct: float) -> float:
    """F15: MC引起的尺寸变化 Δ ≈ 0.2% × ΔMC% × L"""
    return 0.002 * mc_delta_pct * length_mm


def calc_s_shrinkage(mc_pct: float, k: float = 0.8, mc_mid: float = 12.0, l_max: float = 0.012) -> float:
    """F5: S型收缩 Logistic模型, 返回收缩率(0-1), 乘以长度得mm"""
    return l_max / (1.0 + math.exp(-k * (mc_pct - mc_mid)))
