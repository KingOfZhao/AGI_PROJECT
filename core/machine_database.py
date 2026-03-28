"""
machine_database.py — 模切设备参数数据库
基于 REAL_SUCCESS 节点确认的设备参数构建

数据来源：DiePre 推演节点（Bobst/Heidelberg/国产设备）
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class MachineType(Enum):
    FLATBED = "flatbed"       # 平压平
    ROTARY = "rotary"         # 圆压圆
    FLATBED_ROTARY = "hybrid" # 平压圆


@dataclass
class MachineSpec:
    """设备规格"""
    name: str
    brand: str
    country: str
    machine_type: MachineType
    precision_mm: float          # 模切精度 (mm)
    pressure_tons: float         # 最大压力 (T)
    speed_sph: int               # 最高速度 (张/时)
    thickness_range_mm: tuple    # 支持材料厚度范围 (min, max)
    thermal_drift_mm: float = 0  # 30分钟热膨胀量 (mm)
    thermal_drift_rate: float = 0 # 热膨胀速率 (mm/min, 稳态)
    radial_compensation_pct: float = 0  # 圆压圆周向补偿率 (%)
    rigid_knife_min_mm: float = 1.0  # 最小齿刀宽度 (mm)
    min_bridge_mm: float = 0.8  # 最小连接桥宽 (mm)
    accuracy_class: str = "standard"  # standard/precision/ultra
    notes: str = ""


# ==================== 已确认设备数据库 ====================

MACHINES = {
    "bobst_sp104e": MachineSpec(
        name="SP 104 E",
        brand="Bobst",
        country="瑞士",
        machine_type=MachineType.FLATBED,
        precision_mm=0.15,  # 标称精度，最佳可达±0.05mm
        pressure_tons=250,
        speed_sph=7500,
        thickness_range_mm=(0.1, 4.0),
        rigid_knife_min_mm=0.8,
        min_bridge_mm=0.8,
        accuracy_class="ultra",
        notes="精度基准。标称±0.15mm，特定条件下最佳可达±0.05mm。适合微瓦楞/卡纸。",
    ),
    "bobst_sp106": MachineSpec(
        name="SP 106",
        brand="Bobst",
        country="瑞士",
        machine_type=MachineType.FLATBED,
        precision_mm=0.10,  # 比SP104E更精密
        pressure_tons=280,
        speed_sph=9000,
        thickness_range_mm=(0.1, 4.0),
        rigid_knife_min_mm=0.8,
        min_bridge_mm=0.8,
        accuracy_class="ultra",
        notes="新一代旗舰，标称±0.10mm，最佳可达±0.05mm。需实测扇形误差数据。",
    ),
    "bobst_spo20": MachineSpec(
        name="SPO 20",
        brand="Bobst",
        country="瑞士",
        machine_type=MachineType.ROTARY,
        precision_mm=0.20,
        pressure_tons=200,
        speed_sph=12000,
        thickness_range_mm=(0.2, 3.0),
        thermal_drift_mm=0.065,  # 30分钟热膨胀 0.05-0.08mm
        thermal_drift_rate=0.0022,  # 稳态 ~0.05mm/30min
        radial_compensation_pct=0.1,  # -0.1% 周向补偿
        accuracy_class="precision",
        notes="圆压圆，高速运行需增加-0.1%周向补偿。7000sph运行30分钟后滚筒热膨胀约0.05-0.08mm。",
    ),
    "heidelberg_dymatrix": MachineSpec(
        name="Dymatrix",
        brand="Heidelberg",
        country="德国",
        machine_type=MachineType.FLATBED,
        precision_mm=0.20,
        pressure_tons=300,
        speed_sph=9000,
        thickness_range_mm=(0.2, 4.0),
        rigid_knife_min_mm=0.8,  # 高刚性允许0.8mm齿刀
        min_bridge_mm=0.8,
        accuracy_class="precision",
        notes="高刚性机架，适合高克重卡纸，清废稳定性高。允许使用0.8mm齿刀而不跳刀。",
    ),
    "changrong_mk1060": MachineSpec(
        name="MK 1060",
        brand="长荣",
        country="中国",
        machine_type=MachineType.FLATBED,
        precision_mm=0.30,
        pressure_tons=200,
        speed_sph=6000,
        thickness_range_mm=(0.2, 3.0),
        rigid_knife_min_mm=1.0,  # 国产需加宽
        min_bridge_mm=1.0,
        accuracy_class="standard",
        notes="国产中端基准。机器误差在±0.5mm精密级公差中贡献率约45%。",
    ),
    "eastern_series": MachineSpec(
        name="东方系列",
        brand="东方",
        country="中国",
        machine_type=MachineType.FLATBED,
        precision_mm=0.30,
        pressure_tons=180,
        speed_sph=5500,
        thickness_range_mm=(0.2, 2.5),
        rigid_knife_min_mm=1.0,
        min_bridge_mm=1.0,
        accuracy_class="standard",
        notes="国产中端，±0.5mm精密级公差不可达成（RSS误差贡献45%）。",
    ),
    "iijima": MachineSpec(
        name="Iijima",
        brand="Iijima",
        country="日本",
        machine_type=MachineType.FLATBED,
        precision_mm=0.18,
        pressure_tons=220,
        speed_sph=7500,
        thickness_range_mm=(0.1, 3.5),
        rigid_knife_min_mm=0.9,
        min_bridge_mm=0.9,
        accuracy_class="precision",
        notes="日本品牌，精度介于Bobst和Heidelberg之间。<30°锐角清废时震动频率特性独特。",
    ),
}


def calc_machine_error_contribution(precision_mm: float,
                                     total_budget_mm: float) -> dict:
    """
    计算设备误差在总预算中的贡献率
    
    已知：国产设备在±0.5mm精密级公差中贡献率约45%
    
    Args:
        precision_mm: 设备精度 (mm)
        total_budget_mm: 目标总公差 (mm)
    
    Returns:
        dict with contribution rate and assessment
    """
    contribution = precision_mm / total_budget_mm if total_budget_mm > 0 else 0
    contribution_pct = contribution * 100
    
    # 基于已知的贡献率模型
    if contribution_pct > 40:
        assessment = "设备是主要误差源，建议升级设备或放宽公差"
        risk = "high"
    elif contribution_pct > 25:
        assessment = "设备误差贡献显著，需要其他工序高精度配合"
        risk = "medium"
    else:
        assessment = "设备精度充足，可支持精密级公差"
        risk = "low"
    
    return {
        "machine_precision_mm": precision_mm,
        "target_budget_mm": total_budget_mm,
        "contribution_pct": round(contribution_pct, 1),
        "assessment": assessment,
        "risk": risk,
    }


def recommend_machine(target_tolerance_mm: float,
                       material_thickness_mm: float,
                       budget_preference: str = "balanced") -> List[dict]:
    """
    根据目标公差和材料推荐设备
    
    Args:
        target_tolerance_mm: 目标公差
        material_thickness_mm: 材料厚度
        budget_preference: budget/premium/ultra
    
    Returns:
        推荐设备列表
    """
    recommendations = []
    
    for key, spec in MACHINES.items():
        # 检查材料厚度是否在范围内
        if not (spec.thickness_range_mm[0] <= material_thickness_mm <= spec.thickness_range_mm[1]):
            continue
        
        # 检查精度是否满足
        contrib = calc_machine_error_contribution(spec.precision_mm, target_tolerance_mm)
        
        # 计算综合评分
        score = 100
        score -= contrib["contribution_pct"] * 0.5  # 精度贡献率越高分越低
        
        # 预算偏好调整
        if budget_preference == "budget" and spec.country == "中国":
            score += 20  # 国产设备预算友好
        elif budget_preference == "ultra" and spec.accuracy_class == "ultra":
            score += 20
        
        recommendations.append({
            "machine_id": key,
            "name": f"{spec.brand} {spec.name}",
            "country": spec.country,
            "precision_mm": spec.precision_mm,
            "contribution_pct": contrib["contribution_pct"],
            "risk": contrib["risk"],
            "score": round(score, 1),
            "assessment": contrib["assessment"],
        })
    
    return sorted(recommendations, key=lambda x: x["score"], reverse=True)


def calc_thermal_compensation(machine: MachineSpec,
                               runtime_min: float,
                               line_length_mm: float) -> dict:
    """
    计算热膨胀补偿值
    
    已知：Bobst圆压圆7000sph运行30分钟后滚筒膨胀0.05-0.08mm
    
    Args:
        machine: 设备规格
        runtime_min: 运行时间
        line_length_mm: 切割线长度
    
    Returns:
        补偿值和运行状态
    """
    if machine.thermal_drift_mm <= 0:
        return {"compensation_mm": 0, "status": "无热膨胀数据"}
    
    # 简化热膨胀模型：指数趋近
    max_drift = machine.thermal_drift_mm
    tau = 15.0  # 时间常数 (分钟)
    current_drift = max_drift * (1 - 2.7182818 ** (-runtime_min / tau))
    
    # 周向补偿
    compensation = -line_length_mm * machine.radial_compensation_pct / 100
    
    # 热膨胀导致的尺寸变化
    thermal_change = current_drift * line_length_mm / 500  # 简化线性关系
    
    return {
        "current_drift_mm": round(current_drift, 4),
        "max_drift_mm": max_drift,
        "radial_compensation_mm": round(compensation, 4),
        "thermal_size_change_mm": round(thermal_change, 4),
        "total_compensation_mm": round(compensation + thermal_change, 4),
        "status": "稳态" if runtime_min > 45 else "预热中",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("模切设备参数数据库 v1.0")
    print("基于 REAL_SUCCESS 节点确认数据")
    print("=" * 60)

    # 1. 设备列表
    print("\n--- 已确认设备列表 ---")
    for key, spec in MACHINES.items():
        print(f"  {key:25} {spec.brand:12} {spec.country:6} "
              f"±{spec.precision_mm}mm {spec.speed_sph}s/h")

    # 2. 设备误差贡献率
    print("\n--- 设备误差贡献率（目标±0.5mm）---")
    for key, spec in MACHINES.items():
        contrib = calc_machine_error_contribution(spec.precision_mm, 0.5)
        icon = "🟢" if contrib["risk"] == "low" else ("🟡" if contrib["risk"] == "medium" else "🔴")
        print(f"  {icon} {spec.brand:12} {spec.name:10} "
              f"贡献率={contrib['contribution_pct']:5.1f}% | {contrib['assessment']}")

    # 3. 设备推荐
    print("\n--- 设备推荐（目标±0.5mm，白卡0.4mm）---")
    recs = recommend_machine(0.5, 0.4, "balanced")
    for r in recs[:3]:
        print(f"  #{1} {r['name']:25} 评分={r['score']} "
              f"贡献率={r['contribution_pct']}% {r['assessment']}")

    # 4. 热膨胀补偿
    print("\n--- 热膨胀补偿（Bobst SPO 20 圆压圆）---")
    bobst_rotary = MACHINES["bobst_spo20"]
    for t in [0, 10, 20, 30, 45, 60, 90]:
        comp = calc_thermal_compensation(bobst_rotary, t, 300)
        print(f"  运行{t:3d}分钟: 漂移={comp['current_drift_mm']:.3f}mm, "
              f"补偿={comp['total_compensation_mm']:.3f}mm ({comp['status']})")

    print("\n" + "=" * 60)
    print("✅ 完成")
