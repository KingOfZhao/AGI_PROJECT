"""
DiePre 补偿引擎 v2.0
基于30分钟深度推演产出的核心算法
整合: MC自适应RSS + K因子响应面 + 压痕弹性回复 + 裱合非对称补偿 + K深度依赖

作者: AGI Agent (Zhipu GLM) | 日期: 2026-03-31
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class MaterialType(Enum):
    GREYBOARD = "greyboard"
    SINGLE_WALL = "single_wall"
    MICRO_FLUTE = "micro_flute"
    DOUBLE_WALL = "double_wall"
    PLASTIC = "plastic"
    WHITE_CARD = "white_card"


class MachineType(Enum):
    BOBST_SP104 = "bobst_sp104"      # ±0.15mm
    BOBST_SP106 = "bobst_sp106"      # ±0.15mm (newer)
    BOBST_SPO20 = "bobst_spo20"      # ±0.20mm (rotary)
    HEIDELBERG_DYMA = "heidelberg_dymatrix"  # ±0.20mm
    MK_1060 = "mk_1060"             # ±0.30mm
    DOMESTIC = "domestic"           # ±0.30mm
    JAPAN_MITSUBISHI = "mitsubishi"  # ±0.10mm


# ===== 机器精度数据库 =====
MACHINE_DB = {
    MachineType.BOBST_SP104: {"precision": 0.15, "pressure_ton": 250, "speed_sph": 7500, "best": 0.05},
    MachineType.BOBST_SP106: {"precision": 0.15, "pressure_ton": 280, "speed_sph": 9000, "best": 0.05},
    MachineType.BOBST_SPO20: {"precision": 0.20, "pressure_ton": 0, "speed_sph": 0, "best": 0.10},
    MachineType.HEIDELBERG_DYMA: {"precision": 0.20, "pressure_ton": 300, "speed_sph": 0, "best": 0.10},
    MachineType.MK_1060: {"precision": 0.30, "pressure_ton": 0, "speed_sph": 0, "best": 0.15},
    MachineType.DOMESTIC: {"precision": 0.30, "pressure_ton": 0, "speed_sph": 0, "best": 0.15},
    MachineType.JAPAN_MITSUBISHI: {"precision": 0.10, "pressure_ton": 0, "speed_sph": 0, "best": 0.05},
}

# ===== K因子基线数据库 =====
K_BASE = {
    MaterialType.GREYBOARD: 0.375,
    MaterialType.SINGLE_WALL: 0.350,
    MaterialType.MICRO_FLUTE: 0.425,
    MaterialType.DOUBLE_WALL: 0.400,
    MaterialType.PLASTIC: 0.500,
    MaterialType.WHITE_CARD: 0.380,
}

# ===== K因子响应面参数 =====
K_PARAMS = {
    # (alpha_mc, beta_thickness, gamma_cross)
    MaterialType.GREYBOARD: (0.005, -0.010, 0.001),
    MaterialType.SINGLE_WALL: (0.008, -0.005, 0.001),
    MaterialType.MICRO_FLUTE: (0.006, -0.008, 0.001),
    MaterialType.DOUBLE_WALL: (0.004, -0.003, 0.001),
    MaterialType.PLASTIC: (0.000, 0.000, 0.000),  # 不受MC影响
    MaterialType.WHITE_CARD: (0.006, -0.008, 0.001),
}


@dataclass
class CompensationResult:
    """补偿结果"""
    L2d: float           # MD方向展开长度
    W2d: float           # CD方向展开宽度
    k_factor: float      # 使用的K因子
    h_score: float       # 压痕深度
    h_score_ratio: float # 压痕深度比(d/t)
    error_budget: float  # 误差预算(mm)
    k_dist: float        # RSS分布修正系数
    warnings: List[str]  # 警告列表


def k_response_surface(mc: float, t: float, material: MaterialType) -> float:
    """K因子响应面: K = K_base + α×(MC-12) + β×(t-1.0) + γ×(MC-12)×(t-1.0)"""
    k_base = K_BASE[material]
    alpha, beta, gamma = K_PARAMS[material]
    k = k_base + alpha * (mc - 12) + beta * (t - 1.0) + gamma * (mc - 12) * (t - 1.0)
    return max(k, 0.20)  # 下限保护


def k_depth_factor(d_over_t: float) -> float:
    """K因子深度依赖: K_depth = (d/t)^0.15 (d/t < 0.65)"""
    if d_over_t >= 0.65:
        return 0.25 / K_BASE[MaterialType.GREYBOARD]  # 相变归一化
    return d_over_t ** 0.15


def mc_distribution_selector(mc: float) -> float:
    """MC自适应误差分布修正系数 k_dist"""
    if mc < 12:
        return 1.0   # 正态RSS
    elif mc < 16:
        return 1.0 + 0.15 * (mc - 12) / 4  # 1.0 → 1.15 (线性过渡)
    else:
        return 1.25 + 0.10 * (mc - 16) / 2  # 1.25 → 1.35


def recovery_rate(mc: float) -> float:
    """弹性回复率: 4% + 2% × (MC-10)/6 (MC 7-16%)"""
    return 0.04 + 0.02 * max(0, mc - 10) / 6


def mc_shrinkage(mc: float, direction: str) -> float:
    """MC收缩系数 (每1%MC的尺寸变化百分比)"""
    if direction == "MD":
        return 0.0002  # 0.02%/1%MC
    else:  # CD
        return 0.0004  # 0.04%/1%MC


def diepre_compensate(
    L: float, W: float, H: float,
    t: float, material: MaterialType,
    mc: float, machine: MachineType,
    is_laminated: bool = False,
    score_ratio: float = 0.55,  # 压痕深度比(默认0.55)
) -> CompensationResult:
    """
    DiePre核心补偿引擎 v2.0
    
    参数:
        L, W, H: 成品尺寸(mm)
        t: 板厚(mm)
        material: 材料类型
        mc: 含水率(%)
        machine: 机器型号
        is_laminated: 是否裱合
        score_ratio: 压痕深度比(默认0.55)
    
    返回:
        CompensationResult
    """
    warnings = []
    
    # 1. K因子(响应面)
    k_base = k_response_surface(mc, t, material)
    
    # 2. K因子深度修正
    k_depth = k_depth_factor(score_ratio)
    k_effective = k_base * k_depth
    
    # 3. MC自适应分布修正
    k_dist = mc_distribution_selector(mc)
    
    # 4. 展开尺寸补偿
    shrink_md = mc_shrinkage(mc, "MD") * mc  # 总MD收缩率
    shrink_cd = mc_shrinkage(mc, "CD") * mc  # 总CD收缩率
    
    L2d = L + 2 * H * k_effective * (1 + shrink_md * L)
    W2d = W + 2 * H * k_effective * (1 + shrink_cd * W)
    
    # 5. 压痕深度(含弹性回复)
    recovery = recovery_rate(mc)
    if mc < 16:
        h_score = t * score_ratio / (1 - recovery)
        h_ratio = h_score / t
    else:
        h_score = t * 0.45  # 湿态安全值
        h_ratio = 0.45
        warnings.append(f"MC={mc}%≥16%, 使用安全压痕深度(湿态相变风险)")
    
    # 6. 误差预算
    machine_precision = MACHINE_DB[machine]["precision"]
    # 误差预算(三分类模型)
    # 第一类(确定性，直接叠加)
    e_machine_systematic = 0.03  # 机器固有偏移(标定后)
    e_die_making = 0.05  # 刀模制作偏差
    
    # 第二类(半确定性，RSS)
    e_mc_hysteresis = 0.15  # 吸湿滞后
    e_s_curve = 0.08 if mc < 14 else 0.12  # S曲线不确定度
    e_laminate = 0.05 if is_laminated else 0.0  # 裱合胶水
    
    # 第三类(随机，RSS)
    e_thickness = 0.02  # 同批次厚度波动
    e_vibration = 0.01  # 机器振动
    e_thermal = 0.03 if "bobst" in machine.value and "spo" not in machine.value else 0.01  # 热漂移
    
    # 总误差 = Σ(第一类) + k_dist × √(Σ第二类²) + √(Σ第三类²)
    e_class1 = e_machine_systematic + e_die_making
    e_class2 = math.sqrt(e_mc_hysteresis**2 + e_s_curve**2 + e_laminate**2)
    e_class3 = math.sqrt(e_thickness**2 + e_vibration**2 + e_thermal**2)
    error_budget = e_class1 + k_dist * e_class2 + e_class3
    
    # 7. 裱合补偿
    if is_laminated:
        # 假设裱合MC差异为mc_delta
        mc_delta = 3  # 默认3%差异
        laminate_md = 0.0002 * mc_delta * L * 0.5
        laminate_cd = 0.0004 * mc_delta * W * 0.5
        L2d += laminate_md
        W2d += laminate_cd
        
        # 喇叭口检查
        flare = 0.006 * mc_delta * min(L, W)
        if flare > 0.3:
            warnings.append(f"喇叭口风险: {flare:.2f}mm (MC差异{mc_delta}%)")
    
    # 8. 爆线检查
    if score_ratio >= 0.65:
        warnings.append(f"压痕比{score_ratio:.2f}≥0.65, 爆线风险!")
        k_effective = 0.25  # 相变K值
    
    # 9. MC警告
    if mc > 14 and mc < 16:
        warnings.append(f"MC={mc}%>14%, RSS正态假设可能失效(k_dist={k_dist:.2f})")
    
    # 10. 精度可行性
    iadd = 0.254
    if error_budget > iadd:
        warnings.append(f"误差预算±{error_budget:.3f}mm超出IADD(±{iadd}mm)")
    
    return CompensationResult(
        L2d=round(L2d, 3),
        W2d=round(W2d, 3),
        k_factor=round(k_effective, 4),
        h_score=round(h_score, 3),
        h_score_ratio=round(h_ratio, 3),
        error_budget=round(error_budget, 3),
        k_dist=round(k_dist, 3),
        warnings=warnings,
    )


def demo():
    """演示计算"""
    print("=" * 60)
    print("DiePre v2.0 补偿引擎 — 演示")
    print("=" * 60)
    
    scenarios = [
        {"name": "白卡盒(MC=10%, Bobst)", "L": 300, "W": 200, "H": 100,
         "t": 0.4, "mat": MaterialType.WHITE_CARD, "mc": 10, "mach": MachineType.BOBST_SP104},
        {"name": "灰板礼盒(MC=15%, 国产)", "L": 250, "W": 150, "H": 60,
         "t": 2.0, "mat": MaterialType.GREYBOARD, "mc": 15, "mach": MachineType.MK_1060},
        {"name": "双瓦楞运输箱(MC=12%, Bobst)", "L": 400, "W": 300, "H": 250,
         "t": 7.0, "mat": MaterialType.DOUBLE_WALL, "mc": 12, "mach": MachineType.BOBST_SP104},
        {"name": "微瓦楞精品盒(MC=14%, Mitsubishi)", "L": 180, "W": 120, "H": 50,
         "t": 1.2, "mat": MaterialType.MICRO_FLUTE, "mc": 14, "mach": MachineType.JAPAN_MITSUBISHI},
        {"name": "裱合灰板(MC=16%, Heidelberg)", "L": 300, "W": 200, "H": 80,
         "t": 2.5, "mat": MaterialType.GREYBOARD, "mc": 16, "mach": MachineType.HEIDELBERG_DYMA,
         "laminated": True},
    ]
    
    for s in scenarios:
        result = diepre_compensate(
            L=s["L"], W=s["W"], H=s["H"], t=s["t"],
            material=s["mat"], mc=s["mc"], machine=s["mach"],
            is_laminated=s.get("laminated", False),
        )
        print(f"\n📊 {s['name']}")
        print(f"   成品: {s['L']}×{s['W']}×{s['H']}mm, t={s['t']}mm, MC={s['mc']}%")
        print(f"   展开: {result.L2d}×{result.W2d}mm")
        print(f"   K因子: {result.k_factor} (k_dist={result.k_dist})")
        print(f"   压痕: h={result.h_score}mm (d/t={result.h_score_ratio})")
        print(f"   误差预算: ±{result.error_budget}mm")
        if result.warnings:
            for w in result.warnings:
                print(f"   ⚠️  {w}")


if __name__ == "__main__":
    demo()
