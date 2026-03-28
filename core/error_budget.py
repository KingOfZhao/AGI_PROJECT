"""
error_budget.py — 刀模误差预算计算引擎
基于 p_diepre 已知/未知推演的已知事实构建

核心原理（从推演中涌现，非预设）：
  误差按"可预测性"分为三类：
    第一类：确定性误差 → 代数叠加
    第二类：半确定性误差 → RSS叠加
    第三类：随机误差 → RSS叠加
  总误差 = Σ(第一类) + √[Σ(第二类²)] + √[Σ(第三类²)]
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum
import math
import json


class ErrorCategory(Enum):
    """误差可预测性分类"""
    DETERMINISTIC = "deterministic"    # 第一类：确定性，可一次性标定
    SEMI_DETERMINISTIC = "semi"        # 第二类：半确定性，需查表
    RANDOM = "random"                   # 第三类：随机，RSS处理


class PulpType(Enum):
    """纸浆类型"""
    SOFTWOOD = "softwood"    # 针叶木（北方/俄罗斯）- 纤维长，磨损线性
    HARDWOOD = "hardwood"    # 阔叶木（南方/东南亚）- 纤维短，磨损指数级


class Region(Enum):
    """目标市场（纸板特性差异）"""
    ASIA = "asia"
    EUROPE = "europe"


@dataclass
class ErrorSource:
    """单个误差源"""
    name: str
    category: ErrorCategory
    value_mm: float          # 误差值（mm）
    direction_known: bool = True  # 是否已知方向（确定性误差代数叠加用）
    notes: str = ""


@dataclass
class MaterialParams:
    """材料参数"""
    name: str
    thickness_mm: float
    gsm: float
    region: Region = Region.ASIA
    # S型收缩曲线参数（Logistic模型）
    shrink_s_max: float = 0.005    # 最大收缩率（0.5%）
    shrink_k: float = 0.5          # 曲线陡度
    shrink_mc_mid: float = 0.11    # 拐点含水量
    # 吸湿/脱湿路径差异
    k_absorb: float = 0.4          # 吸湿路径陡度
    k_desorb: float = 0.6          # 脱湿路径陡度
    # 亚洲塌陷补偿
    collapse_compensation_mm: float = 0.0  # 亚洲纸板额外补偿


# ==================== 预定义材料库 ====================

MATERIALS = {
    "white_card_300": MaterialParams(
        name="白卡300gsm", thickness_mm=0.4, gsm=300,
        shrink_s_max=0.008, shrink_k=50.0, shrink_mc_mid=0.12,
        # 注意: k值较大因为MC范围(0.06-0.18)需要陡峭的S型过渡
        k_absorb=40.0, k_desorb=60.0,
    ),
    "greyboard_1.0": MaterialParams(
        name="灰板1.0mm", thickness_mm=1.0, gsm=900,
        region=Region.ASIA, collapse_compensation_mm=0.1,
        shrink_s_max=0.003, shrink_k=0.4, shrink_mc_mid=0.12,
    ),
    "greyboard_2.0": MaterialParams(
        name="灰板2.0mm", thickness_mm=2.0, gsm=1800,
        region=Region.ASIA, collapse_compensation_mm=0.15,
        shrink_s_max=0.002, shrink_k=0.3, shrink_mc_mid=0.12,
    ),
    "corrugated_E": MaterialParams(
        name="E瓦楞", thickness_mm=1.8, gsm=450,
        shrink_s_max=0.006, shrink_k=0.6, shrink_mc_mid=0.13,
    ),
}


# ==================== 核心计算函数 ====================

def calc_s_type_shrinkage(mc: float, material: MaterialParams,
                          is_desorbing: bool = False) -> float:
    """
    S型收缩率计算（Logistic模型）
    
    基于已知事实：
    - 纸张收缩呈S型曲线（非线性）
    - 吸湿路径和脱湿路径不同（吸湿滞后效应）
    
    Args:
        mc: 当前含水量 (0.0-1.0, 如0.12表示12%)
        material: 材料参数
        is_desorbing: 是否为脱湿路径（从高MC降到当前MC）
    
    Returns:
        收缩率 (如0.003表示0.3%)
    """
    k = material.k_desorb if is_desorbing else material.k_absorb
    # Logistic: S(MC) = S_max / (1 + exp(-k * (MC - MC_mid)))
    exponent = -k * (mc - material.shrink_mc_mid)
    # 防溢出
    exponent = max(-20, min(20, exponent))
    shrinkage = material.shrink_s_max / (1 + math.exp(exponent))
    return shrinkage


def calc_fan_error(length_mm: float, roller_radius_mm: float,
                   speed_spm: float = 100, runtime_min: float = 0) -> dict:
    """
    扇形误差计算（三因子分解）
    
    基于已知事实：
    Δfan = 几何扇形扩散 + 热膨胀漂移 + 离心力变形
    
    Args:
        length_mm: 切割线长度
        roller_radius_mm: 刀辊半径
        speed_spm: 运行速度（张/分钟）
        runtime_min: 累计运行时间（影响热漂移）
    
    Returns:
        dict with components and total
    """
    # 1. 几何扇形扩散（主要项）
    # 物理含义：刀辊圆弧展开为平面时的扇形偏移
    # Δfan_geo ≈ L × θ / 2，其中 θ ≈ L / R（小角度近似）
    # 实际上扇形展开误差是关于中心线的对称偏移
    # 正确公式：Δfan = L² / (8R)（弦高近似）
    if roller_radius_mm > 0:
        fan_geo = (length_mm ** 2) / (8 * roller_radius_mm)
    else:
        fan_geo = 0
    
    # 2. 热膨胀漂移（次要项）
    alpha_steel = 12e-6  # 钢的热膨胀系数 /°C
    delta_t = min(runtime_min * 0.5, 30)  # 简化：每分钟升温0.5°C，最高30°C
    fan_thermal = alpha_steel * delta_t * length_mm
    
    # 3. 离心力变形（微项，通常可忽略）
    # 典型值 < 0.01mm，直接设为0
    fan_centrifugal = 0.0
    
    total = fan_geo + fan_thermal + fan_centrifugal
    
    return {
        "fan_geo_mm": round(fan_geo, 4),
        "fan_thermal_mm": round(fan_thermal, 4),
        "fan_centrifugal_mm": round(fan_centrifugal, 4),
        "fan_total_mm": round(total, 4),
    }


def calc_total_budget(errors: List[ErrorSource],
                      safety_k: float = 1.2,
                      k_dir: float = 1.0,
                      k_env: float = 1.0) -> dict:
    """
    总误差预算计算（已确认修正版）
    
    公式：T_total = k × K_dir × K_env × [Σ(第一类) + √(Σ(第二类²)) + √(Σ(第三类²))]
    
    修正系数来源（从 REAL_SUCCESS 节点确认）：
    - k (安全系数): 1.15-1.25，因模切误差呈瑞利分布而非正态分布
    - K_dir (方向因子): 垂直于瓦楞方向误差比平行方向大20%-30%
    - K_env (环境因子): 温湿度波动导致 RSS 低估
    
    Args:
        errors: 误差源列表
        safety_k: 安全系数（默认1.2，节点0430确认）
        k_dir: 方向修正因子（默认1.0，瓦楞垂直方向取1.25）
        k_env: 环境修正因子（默认1.0，无温控取1.15）
    
    Returns:
        dict with breakdown and total
    """
    cat1_sum = 0.0
    cat2_sq_sum = 0.0
    cat3_sq_sum = 0.0
    cat1_items = []
    cat2_items = []
    cat3_items = []

    for e in errors:
        if e.category == ErrorCategory.DETERMINISTIC:
            cat1_sum += e.value_mm
            cat1_items.append(e)
        elif e.category == ErrorCategory.SEMI_DETERMINISTIC:
            cat2_sq_sum += e.value_mm ** 2
            cat2_items.append(e)
        else:
            cat3_sq_sum += e.value_mm ** 2
            cat3_items.append(e)

    cat1_total = cat1_sum
    cat2_total = math.sqrt(cat2_sq_sum) if cat2_sq_sum > 0 else 0
    cat3_total = math.sqrt(cat3_sq_sum) if cat3_sq_sum > 0 else 0
    total = (cat1_total + cat2_total + cat3_total) * safety_k * k_dir * k_env

    return {
        "category1_deterministic_mm": round(cat1_total, 4),
        "category1_items": [{"name": e.name, "value": e.value_mm} for e in cat1_items],
        "category2_semi_mm": round(cat2_total, 4),
        "category2_items": [{"name": e.name, "value": e.value_mm} for e in cat2_items],
        "category3_random_mm": round(cat3_total, 4),
        "category3_items": [{"name": e.name, "value": e.value_mm} for e in cat3_items],
        "raw_budget_mm": round(cat1_total + cat2_total + cat3_total, 4),
        "safety_k": safety_k,
        "k_dir": k_dir,
        "k_env": k_env,
        "total_budget_mm": round(total, 4),
        "meets_iadd": total <= 0.254,  # IADD标准 ±0.254mm
    }


# ==================== 场景预设 ====================

def scenario_jiangzhehu_no_control(length_md: float = 300,
                                    length_cd: float = 200) -> dict:
    """场景：江浙沪，无温控仓库，白卡300gsm"""
    errors = [
        ErrorSource("刀模制作偏差", ErrorCategory.DETERMINISTIC, 0.05),
        ErrorSource("机器固有偏移", ErrorCategory.DETERMINISTIC, 0.03),
        ErrorSource("MD方向收缩(年均)", ErrorCategory.DETERMINISTIC, 0.10),
        ErrorSource("吸湿滞后效应", ErrorCategory.SEMI_DETERMINISTIC, 0.15),
        ErrorSource("S型曲线不确定度", ErrorCategory.SEMI_DETERMINISTIC, 0.08),
        ErrorSource("同批次厚度波动", ErrorCategory.RANDOM, 0.02),
        ErrorSource("机器振动", ErrorCategory.RANDOM, 0.01),
        ErrorSource("热漂移", ErrorCategory.RANDOM, 0.03),
    ]
    return calc_total_budget(errors)


def scenario_controlled_warehouse(length_md: float = 300,
                                   length_cd: float = 200) -> dict:
    """场景：受控仓储 RH=55±5%"""
    errors = [
        ErrorSource("刀模制作偏差", ErrorCategory.DETERMINISTIC, 0.05),
        ErrorSource("机器固有偏移", ErrorCategory.DETERMINISTIC, 0.03),
        ErrorSource("MD方向收缩(受控)", ErrorCategory.DETERMINISTIC, 0.05),
        ErrorSource("吸湿滞后(受控)", ErrorCategory.SEMI_DETERMINISTIC, 0.05),
        ErrorSource("S型曲线不确定度", ErrorCategory.SEMI_DETERMINISTIC, 0.03),
        ErrorSource("裱合胶水收缩", ErrorCategory.SEMI_DETERMINISTIC, 0.05),
        ErrorSource("同批次厚度波动", ErrorCategory.RANDOM, 0.02),
        ErrorSource("机器振动", ErrorCategory.RANDOM, 0.01),
        ErrorSource("热漂移", ErrorCategory.RANDOM, 0.03),
    ]
    return calc_total_budget(errors)


def scenario_seasonal_calibrated(length_md: float = 300,
                                  length_cd: float = 200) -> dict:
    """场景：受控仓储 + 分季节标定刀模"""
    errors = [
        ErrorSource("刀模制作偏差(季节标定)", ErrorCategory.DETERMINISTIC, 0.03),
        ErrorSource("机器固有偏移", ErrorCategory.DETERMINISTIC, 0.03),
        ErrorSource("MD方向收缩(受控+标定)", ErrorCategory.DETERMINISTIC, 0.04),
        ErrorSource("吸湿滞后(受控)", ErrorCategory.SEMI_DETERMINISTIC, 0.03),
        ErrorSource("S型曲线不确定度", ErrorCategory.SEMI_DETERMINISTIC, 0.02),
        ErrorSource("同批次厚度波动", ErrorCategory.RANDOM, 0.02),
        ErrorSource("机器振动", ErrorCategory.RANDOM, 0.01),
        ErrorSource("热漂移", ErrorCategory.RANDOM, 0.03),
    ]
    return calc_total_budget(errors)


def calc_crease_bridge_width(thickness_mm: float, angle_deg: float) -> float:
    """
    计算清废桥宽度（锐角处）
    
    已知：桥宽 b = 2 × t × tan(θ/2) + clearance
    临界条件：b < t × 1.5 时断裂概率急剧上升
    
    Args:
        thickness_mm: 材料厚度
        angle_deg: 锐角角度（度）
    
    Returns:
        桥宽（mm）
    """
    import math
    clearance = 0.3  # 最小清废间隙 0.3mm
    bridge = 2 * thickness_mm * math.tan(math.radians(angle_deg / 2)) + clearance
    return round(bridge, 3)


def calc_critical_angle(thickness_mm: float) -> float:
    """
    计算清废断裂临界角度
    
    已知：θ_crit ≈ 15° + 5° × ln(t)
    来源：从节点0314推演，基于应力集中系数推导
    
    Args:
        thickness_mm: 材料厚度
    
    Returns:
        临界角度（度）
    """
    return round(15 + 5 * math.log(thickness_mm), 1)


def calc_mc_compat_range(design_mc_pct: float, product_length_mm: float,
                          iadd_tolerance_mm: float = 0.254,
                          shrinkage_coeff: float = 0.0002) -> dict:
    """
    计算MC兼容范围（临界兼容阈值）
    
    已知：ΔMC_max = tolerance / (L × coefficient)
    超出此范围应报警而非继续补偿
    
    Args:
        design_mc_pct: 设计含水量（%）
        product_length_mm: 产品长度（mm）
        iadd_tolerance_mm: IADD公差（mm）
        shrinkage_coeff: 收缩系数（/1%MC/mm）
    
    Returns:
        dict with mc_min, mc_max, range
    """
    delta_mc = iadd_tolerance_mm / (product_length_mm * shrinkage_coeff)
    mc_min = design_mc_pct - delta_mc / 2
    mc_max = design_mc_pct + delta_mc / 2
    return {
        "design_mc_pct": design_mc_pct,
        "mc_min_pct": round(mc_min, 1),
        "mc_max_pct": round(mc_max, 1),
        "mc_range_pct": round(delta_mc, 1),
        "alarm_threshold_pct": round(delta_mc * 0.8, 1),  # 80%时预报警
    }


def calc_knife_wear_factor(pulp_type: PulpType, runtime_hours: float) -> dict:
    """
    计算刀刃磨损因子 K_wear
    
    已知（节点0594确认）：
    - 针叶木(softwood)：磨损呈线性
    - 阔叶木(hardwood)：磨损呈指数级，衰减系数需上调30%
    
    Args:
        pulp_type: 纸浆类型
        runtime_hours: 累计运行时间
    
    Returns:
        dict with wear factor and knife life estimate
    """
    if pulp_type == PulpType.SOFTWOOD:
        # 线性磨损
        k_wear = 1.0 + runtime_hours * 0.002  # 每小时增加0.2%
        wear_type = "线性"
        life_hours = 500  # 预估寿命
    else:
        # 指数磨损 + 30%上调
        k_wear = 1.3 * (1.028 ** runtime_hours)  # 指数因子 1.028/h
        wear_type = "指数级"
        life_hours = 300  # 阔叶木寿命更短
    
    return {
        "k_wear": round(k_wear, 4),
        "wear_type": wear_type,
        "runtime_hours": runtime_hours,
        "life_hours": life_hours,
        "remaining_pct": max(0, round((1 - runtime_hours/life_hours) * 100, 1)),
    }


# ==================== 测试入口 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("刀模误差预算计算引擎 v1.0")
    print("基于 p_diepre 已知/未知推演的已知事实构建")
    print("=" * 60)

    # 1. S型收缩曲线演示
    print("\n--- S型收缩曲线 ---")
    mat = MATERIALS["white_card_300"]
    for mc_pct in [6, 8, 10, 11, 12, 14, 16, 18]:
        mc = mc_pct / 100
        s_abs = calc_s_type_shrinkage(mc, mat, is_desorbing=False)
        s_des = calc_s_type_shrinkage(mc, mat, is_desorbing=True)
        print(f"  MC={mc_pct:2d}%: 吸湿路径={s_abs:.4f} ({s_abs*100:.2f}%), "
              f"脱湿路径={s_des:.4f} ({s_des*100:.2f}%), "
              f"差={abs(s_abs-s_des)*100:.3f}%")

    # 2. 扇形误差演示
    print("\n--- 扇形误差（不同刀线长度）---")
    for L in [50, 100, 200, 300, 500]:
        fan = calc_fan_error(L, roller_radius_mm=300, speed_spm=100, runtime_min=30)
        print(f"  L={L:3d}mm: Δfan_geo={fan['fan_geo_mm']:.3f}mm, "
              f"Δfan_thermal={fan['fan_thermal_mm']:.3f}mm, "
              f"total={fan['fan_total_mm']:.3f}mm")

    # 3. 误差预算对比
    print("\n--- 误差预算对比 ---")
    scenarios = [
        ("无温控仓库", scenario_jiangzhehu_no_control),
        ("受控仓储", scenario_controlled_warehouse),
        ("受控+季节标定", scenario_seasonal_calibrated),
    ]
    for name, fn in scenarios:
        result = fn()
        iadd = "✅ 满足IADD" if result["meets_iadd"] else "❌ 超出IADD"
        print(f"\n  场景: {name}")
        print(f"    第一类(确定性): ±{result['category1_deterministic_mm']:.3f}mm")
        print(f"    第二类(半确定性): ±{result['category2_semi_mm']:.3f}mm")
        print(f"    第三类(随机):     ±{result['category3_random_mm']:.3f}mm")
        print(f"    总误差预算:       ±{result['total_budget_mm']:.3f}mm")
        print(f"    {iadd} (标准: ±0.254mm)")

    # 4. 亚洲塌陷补偿演示
    print("\n--- 亚洲塌陷补偿 ---")
    mat_asia = MATERIALS["greyboard_2.0"]
    mat_europe = MaterialParams(
        name="欧洲灰板2.0mm", thickness_mm=2.0, gsm=1800,
        region=Region.EUROPE, collapse_compensation_mm=0.0,
        shrink_s_max=0.002, shrink_k=0.3, shrink_mc_mid=0.12,
    )
    print(f"  亚洲灰板2.0mm: 塌陷补偿 = {mat_asia.collapse_compensation_mm}mm")
    print(f"  欧洲灰板2.0mm: 塌陷补偿 = {mat_europe.collapse_compensation_mm}mm")
    print(f"  差异: {mat_asia.collapse_compensation_mm - mat_europe.collapse_compensation_mm}mm")

    # 5. 清废断裂临界角度
    print("\n--- 清废断裂临界角度 ---")
    for t in [0.4, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
        crit = calc_critical_angle(t)
        bridge_20 = calc_crease_bridge_width(t, 20)
        bridge_30 = calc_crease_bridge_width(t, 30)
        print(f"  t={t:.1f}mm: 临界角={crit}°, "
              f"20°桥宽={bridge_20}mm, 30°桥宽={bridge_30}mm")

    # 6. MC兼容范围
    print("\n--- MC兼容范围计算 ---")
    for L in [100, 200, 300, 500]:
        mc_range = calc_mc_compat_range(design_mc_pct=12, product_length_mm=L)
        print(f"  L={L}mm: MC兼容范围 {mc_range['mc_min_pct']:.1f}%-{mc_range['mc_max_pct']:.1f}% "
              f"(±{mc_range['mc_range_pct']/2:.1f}%), 报警阈值: ±{mc_range['alarm_threshold_pct']/2:.1f}%")

    print("\n" + "=" * 60)
    print("✅ 计算完成")


def calc_bct_box_crush_test(ect_kn_m: float, perimeter_mm: float,
                             thickness_mm: float) -> dict:
    """
    计算箱体抗压强度 BCT (Box Compression Test)
    
    马基公式（McKee Formula，已确认）：
    BCT = 5.87 × ECT × √(S × t)
    
    Args:
        ect_kn_m: 边压强度 (kN/m)
        perimeter_mm: 箱体周长 (mm)
        thickness_mm: 纸板厚度 (mm)
    
    Returns:
        dict with BCT value and assessment
    """
    # S = perimeter / 1000 (转换为m)
    s_m = perimeter_mm / 1000
    bct = 5.87 * ect_kn_m * (s_m * thickness_mm) ** 0.5
    
    return {
        "bct_n": round(bct, 1),
        "ect_kn_m": ect_kn_m,
        "perimeter_mm": perimeter_mm,
        "thickness_mm": thickness_mm,
    }


def calc_score_line_params(thickness_mm: float,
                            standard: str = "fefco") -> dict:
    """
    计算压痕线设计参数
    
    已确认标准：
    - FEFCO: W = t + 0.8mm, D = t × 0.3, S = W × 2
    - ECMA: W = t × 1.5, D = t × 0.25, S = W × 2.2
    
    Args:
        thickness_mm: 纸板厚度
        standard: "fefco" 或 "ecma"
    
    Returns:
        dict with score line parameters
    """
    if standard == "ecma":
        w = thickness_mm * 1.5
        d = thickness_mm * 0.25
        s = w * 2.2
    else:  # FEFCO
        w = thickness_mm + 0.8
        d = thickness_mm * 0.3
        s = w * 2
    
    return {
        "width_mm": round(w, 2),
        "depth_mm": round(d, 2),
        "shoulder_mm": round(s, 2),
        "standard": standard,
    }




# 从 confirmed_knowledge_base 节点0179-0183提取的材料数据库
MATERIAL_CATALOG = {
    "white_card_300": {
        "name": "白卡300gsm",
        "gsm": 300, "thickness_mm": 0.38,
        "mc_std_pct": 5.0, "mc_range": 1.0,
        "alpha_md": 3.0e-5, "alpha_cd": 8.0e-5,  # 1%RH
        "fiber": "紧密", "note": "精品盒常用面料"
    },
    "white_card_450": {
        "name": "白卡450gsm",
        "gsm": 450, "thickness_mm": 0.60,
        "mc_std_pct": 5.5, "mc_range": 1.0,
        "alpha_md": 3.5e-5, "alpha_cd": 9.0e-5,
        "fiber": "紧密", "note": "精装盒面料"
    },
    "corrugated_B": {
        "name": "B瓦楞",
        "gsm": 0, "thickness_mm": 3.0,
        "mc_std_pct": 7.0, "mc_range": 2.0,
        "alpha_md": 1.2e-4, "alpha_cd": 3.5e-4,
        "fiber": "多层", "note": "需考虑压实效应"
    },
    "corrugated_E": {
        "name": "E瓦楞",
        "gsm": 0, "thickness_mm": 1.25,
        "mc_std_pct": 7.0, "mc_range": 2.0,
        "alpha_md": 1.0e-4, "alpha_cd": 3.0e-4,
        "fiber": "多层", "note": "易压溃,K因子敏感"
    },
    "corrugated_F": {
        "name": "F瓦楞(微)",
        "gsm": 0, "thickness_mm": 0.75,
        "mc_std_pct": 6.5, "mc_range": 1.0,
        "alpha_md": 9.0e-5, "alpha_cd": 2.8e-4,
        "fiber": "多层", "note": "极薄,模切精度要求极高"
    },
    "greyboard_1.5": {
        "name": "灰板1.5mm",
        "gsm": 0, "thickness_mm": 1.5,
        "mc_std_pct": 8.0, "mc_range": 2.0,
        "alpha_md": 4.0e-5, "alpha_cd": 1.0e-4,
        "fiber": "回收废纸", "note": "书脊/礼盒盖板"
    },
}


def calc_humidity_expansion(material_key: str, length_mm: float,
                            delta_rh_pct: float, direction: str = "cd") -> dict:
    """
    计算湿度引起的尺寸变化
    
    公式: ΔL = L × alpha × ΔRH
    
    Args:
        material_key: 材料键名
        length_mm: 尺寸(mm)
        delta_rh_pct: 含水率变化百分比(如6%→12%则为6)
        direction: "md"(机器方向) 或 "cd"(横向)
    
    Returns:
        dict with expansion details
    """
    mat = MATERIAL_CATALOG.get(material_key)
    if not mat:
        return {"error": f"未知材料: {material_key}"}
    
    alpha = mat["alpha_md"] if direction == "md" else mat["alpha_cd"]
    delta_l = length_mm * alpha * delta_rh_pct
    
    return {
        "material": mat["name"],
        "length_mm": length_mm,
        "direction": direction,
        "delta_rh_pct": delta_rh_pct,
        "alpha_per_rh": alpha,
        "delta_l_mm": round(delta_l, 3),
        "delta_l_pct": round(delta_l / length_mm * 100, 4),
    }


def calc_jiangzhehu_delta_jiangsu(
    length_mm: float, mc_from: float = 7.0, mc_to: float = 12.0,
    material_key: str = "white_card_300"
) -> dict:
    """
    计算江浙沪全年MC波动对具体尺寸的影响
    
    场景: 江浙沪MC范围约7%-17%, 以年均12%为基准
    """
    md = calc_humidity_expansion(material_key, length_mm, mc_to - mc_from, "md")
    cd = calc_humidity_expansion(material_key, length_mm, mc_to - mc_from, "cd")
    
    return {
        "length_mm": length_mm,
        "mc_range_pct": f"{mc_from}-{mc_to}%",
        "md_expansion_mm": md["delta_l_mm"],
        "cd_expansion_mm": cd["delta_l_mm"],
        "cd_larger_by": round(cd["delta_l_mm"] / md["delta_l_mm"], 2),
        "warning": "CD方向膨胀约为MD的2-3倍" if cd["delta_l_mm"] > md["delta_l_mm"] * 2 else None,
    }




# 膨胀系数修正因子
# 纯材料alpha vs 实际生产alpha 的差距来源:
# 1. 裱合胶水吸湿 → 二次膨胀
# 2. 纸板压实后松弛 → 回弹
# 3. 多层结构应力释放
# 节点0133实测: 白卡500mm盒身, MC 6→12%, CD膨胀≈1.8mm
# 反推alpha_effective ≈ 6e-4/1%MC (vs 纯材料8e-5)
# 修正系数 K_lam ≈ 7.5

ALPHA_CORRECTION_FACTORS = {
    "single_sheet": 1.0,        # 单张纸, 纯材料系数
    "laminated_2ply": 3.0,      # 两层裱纸
    "laminated_3ply": 5.0,      # 三层(面+瓦楞+里)
    "production_typical": 7.5,  # 实际生产(含裱合+压实+松弛)
}


def calc_production_expansion(material_key: str, length_mm: float,
                               delta_mc_pct: float, direction: str = "cd",
                               correction: str = "production_typical") -> dict:
    """
    计算实际生产环境下的膨胀（含裱合/压实修正）
    
    纯材料系数 × 修正因子 = 生产环境有效系数
    """
    mat = MATERIAL_CATALOG.get(material_key)
    if not mat:
        return {"error": f"未知材料: {material_key}"}
    
    alpha_base = mat["alpha_md"] if direction == "md" else mat["alpha_cd"]
    k = ALPHA_CORRECTION_FACTORS.get(correction, 1.0)
    alpha_eff = alpha_base * k
    
    delta_l = length_mm * alpha_eff * delta_mc_pct
    
    return {
        "material": mat["name"],
        "length_mm": length_mm,
        "direction": direction,
        "delta_mc_pct": delta_mc_pct,
        "alpha_base": alpha_base,
        "correction_factor": k,
        "alpha_effective": alpha_eff,
        "delta_l_mm": round(delta_l, 3),
        "correction_type": correction,
    }




# 标准测试/交付环境条件（节点0364确认）
STANDARD_ENVIRONMENTS = {
    "ISO_287": {
        "name": "ISO 287 标准测试条件",
        "temp_c": 23, "rh_pct": 50,
        "mc_target_pct": None,  # 不规定MC，只规定环境
        "use": "实验室测试",
    },
    "DIN_54302": {
        "name": "DIN 54302 标准条件",
        "temp_c": 23, "rh_pct": 50,
        "mc_target_pct": None,
        "use": "欧洲标准测试",
    },
    "JIS_P8127": {
        "name": "JIS P 8127 交付平衡",
        "temp_c": 20, "rh_pct": 65,
        "mc_target_pct": None,
        "use": "日本交付后平衡环境",
    },
    "GB_T462": {
        "name": "GB/T 462 出厂条件",
        "temp_c": None, "rh_pct": None,
        "mc_target_pct": 10.0,  # MC 10% ± 2%
        "mc_range_pct": 2.0,
        "use": "中国出厂含水率",
    },
    "FEFCO_Code": {
        "name": "FEFCO Code MC基准",
        "temp_c": None, "rh_pct": None,
        "mc_target_pct": 7.0,  # MC 7% ± 1%
        "mc_range_pct": 1.0,
        "use": "FEFCO含水率基准",
    },
}


def calc_env_pre_expansion(material_key: str, length_mm: float,
                            from_standard: str, to_standard: str,
                            direction: str = "cd") -> dict:
    """
    计算跨标准环境的预膨胀量
    
    出口订单需引入环境预膨胀系数 K_env
    例如: GB出厂(10%MC) → JIS交付(20℃/65%RH ≈ 12%MC)
    """
    env_from = STANDARD_ENVIRONMENTS.get(from_standard)
    env_to = STANDARD_ENVIRONMENTS.get(to_standard)
    mat = MATERIAL_CATALOG.get(material_key)
    
    if not env_from or not env_to or not mat:
        return {"error": "未知标准或材料"}
    
    # 从MC出发
    mc_from = env_from.get("mc_target_pct", 8.0)
    mc_to = env_to.get("mc_target_pct", 12.0)
    
    # 如果目标只有环境条件，估算MC
    if mc_to is None and env_to["rh_pct"]:
        # 粗略估算: MC ≈ RH * 0.18 (经验公式)
        mc_to = env_to["rh_pct"] * 0.18
    
    if mc_from is None and env_from["rh_pct"]:
        mc_from = env_from["rh_pct"] * 0.18
    
    delta_mc = mc_to - mc_from
    
    # 使用生产环境膨胀系数
    alpha = mat["alpha_md"] if direction == "md" else mat["alpha_cd"]
    alpha_eff = alpha * ALPHA_CORRECTION_FACTORS["production_typical"]
    delta_l = length_mm * alpha_eff * delta_mc
    
    return {
        "from": env_from["name"],
        "to": env_to["name"],
        "mc_from_pct": round(mc_from, 1),
        "mc_to_pct": round(mc_to, 1),
        "delta_mc_pct": round(delta_mc, 1),
        "length_mm": length_mm,
        "direction": direction,
        "delta_l_mm": round(delta_l, 3),
        "recommendation": "需要在2D展开图上预留此膨胀量" if delta_l > 0.1 else "膨胀量可忽略",
    }


