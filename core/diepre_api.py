"""
diepre_api.py — DiePre 刀模精度计算 API
将 error_budget 和 machine_database 的功能暴露为统一接口
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from error_budget import (
    calc_s_type_shrinkage, calc_fan_error, calc_total_budget,
    calc_crease_bridge_width, calc_critical_angle, calc_mc_compat_range,
    scenario_jiangzhehu_no_control, scenario_controlled_warehouse,
    scenario_seasonal_calibrated, ErrorSource, ErrorCategory,
    MATERIALS, Region,
)
from machine_database import (
    MACHINES, MachineSpec, MachineType,
    calc_machine_error_contribution, recommend_machine, calc_thermal_compensation,
)


def quick_tolerance_check(
    product_length_mm: float,
    product_width_mm: float,
    material_key: str,
    machine_key: str,
    target_tolerance_mm: float = 0.254,
    is_controlled_warehouse: bool = False,
    has_seasonal_calibration: bool = False,
    is_asia_market: bool = False,
) -> dict:
    """
    快速公差检查（一站式入口）
    
    从已知/未知框架出发，将所有已知参数输入，
    计算总误差并与目标公差对比。
    
    Args:
        product_length_mm: 产品长度 (MD方向)
        product_width_mm: 产品宽度 (CD方向)
        material_key: 材料键名 (如 "white_card_300")
        machine_key: 设备键名 (如 "bobst_sp104e")
        target_tolerance_mm: 目标公差 (默认 IADD ±0.254mm)
        is_controlled_warehouse: 是否受控仓储
        has_seasonal_calibration: 是否分季节标定刀模
        is_asia_market: 是否亚洲市场（触发塌陷补偿）
    
    Returns:
        dict with full analysis
    """
    material = MATERIALS.get(material_key)
    machine = MACHINES.get(machine_key)
    
    if not material:
        return {"error": f"未知材料: {material_key}", "available": list(MATERIALS.keys())}
    if not machine:
        return {"error": f"未知设备: {machine_key}", "available": list(MACHINES.keys())}
    
    # 构建误差源列表
    shrink_rate = 0.0008 if is_controlled_warehouse else 0.002
    if has_seasonal_calibration:
        shrink_rate *= 0.6
    errors = [
        ErrorSource("刀模制作偏差", ErrorCategory.DETERMINISTIC, 0.05),
        ErrorSource("机器固有偏移", ErrorCategory.DETERMINISTIC, machine.precision_mm * 0.2),
        ErrorSource("MD方向收缩", ErrorCategory.DETERMINISTIC,
                     product_length_mm * shrink_rate),
    ]
    
    if is_asia_market and material.collapse_compensation_mm > 0:
        errors.append(ErrorSource("亚洲塌陷补偿", ErrorCategory.DETERMINISTIC,
                                   material.collapse_compensation_mm))
    
    if has_seasonal_calibration:
        # 季节标定减少确定性误差
        pass  # 已在参数中体现
    
    # 第二类：半确定性误差
    if is_controlled_warehouse:
        errors.append(ErrorSource("吸湿滞后(受控)", ErrorCategory.SEMI_DETERMINISTIC, 0.05))
        errors.append(ErrorSource("S曲线不确定度", ErrorCategory.SEMI_DETERMINISTIC, 0.03))
    else:
        errors.append(ErrorSource("吸湿滞后(无控)", ErrorCategory.SEMI_DETERMINISTIC, 0.15))
        errors.append(ErrorSource("S曲线不确定度", ErrorCategory.SEMI_DETERMINISTIC, 0.08))
    
    # 第三类：随机误差
    errors.extend([
        ErrorSource("厚度波动", ErrorCategory.RANDOM, 0.02),
        ErrorSource("机器振动", ErrorCategory.RANDOM, 0.01),
        ErrorSource("热漂移", ErrorCategory.RANDOM, 0.03),
    ])
    
    # 计算总误差
    budget = calc_total_budget(errors, safety_k=1.2)
    
    # 设备误差贡献率
    contrib = calc_machine_error_contribution(machine.precision_mm, target_tolerance_mm)
    
    # 清废临界角
    crit_angle = calc_critical_angle(material.thickness_mm)
    
    # MC兼容范围
    mc_range = calc_mc_compat_range(12, product_length_mm, target_tolerance_mm)
    
    # 综合判定
    passes = budget["total_budget_mm"] <= target_tolerance_mm
    if passes:
        grade = "A"
        recommendation = "可直接投入生产"
    elif budget["total_budget_mm"] <= target_tolerance_mm * 1.3:
        grade = "B"
        recommendation = "需加强过程控制"
    elif budget["total_budget_mm"] <= target_tolerance_mm * 1.5:
        grade = "C"
        recommendation = "建议受控仓储+分季节标定"
    else:
        grade = "D"
        recommendation = "建议升级设备或放宽公差"
    
    return {
        "passes": passes,
        "grade": grade,
        "recommendation": recommendation,
        "product": {
            "length_mm": product_length_mm,
            "width_mm": product_width_mm,
            "material": material.name,
            "machine": f"{machine.brand} {machine.name}",
            "target_tolerance_mm": target_tolerance_mm,
        },
        "budget": budget,
        "machine_contribution": contrib,
        "critical_angle_deg": crit_angle,
        "mc_range": mc_range,
        "warnings": _generate_warnings(budget, contrib, crit_angle, is_asia_market),
    }


def _generate_warnings(budget, contrib, crit_angle, is_asia):
    """生成预警信息"""
    warnings = []
    
    if budget["total_budget_mm"] > budget.get("target_budget_mm", 999):
        warnings.append(f"总误差 ±{budget['total_budget_mm']}mm 超出目标公差")
    
    if contrib["risk"] == "high":
        warnings.append(f"设备误差贡献率 {contrib['contribution_pct']}%，建议升级")
    
    if is_asia:
        warnings.append("亚洲市场需额外塌陷补偿")
    
    return warnings


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("DiePre 快速公差检查工具")
    print("=" * 60)
    
    # 场景1: 高档烟包（Bobst + 受控 + 标定）
    print("\n--- 场景1: 高档烟包 ---")
    r1 = quick_tolerance_check(
        product_length_mm=200, product_width_mm=100,
        material_key="white_card_300", machine_key="bobst_sp104e",
        target_tolerance_mm=0.254,
        is_controlled_warehouse=True, has_seasonal_calibration=True,
    )
    print(f"  等级: {r1['grade']} | 通过: {'✅' if r1['passes'] else '❌'}")
    print(f"  总误差: ±{r1['budget']['total_budget_mm']}mm")
    print(f"  建议: {r1['recommendation']}")
    
    # 场景2: 普通瓦楞箱（国产 + 无温控）
    print("\n--- 场景2: 普通瓦楞箱 ---")
    r2 = quick_tolerance_check(
        product_length_mm=300, product_width_mm=200,
        material_key="corrugated_E", machine_key="changrong_mk1060",
        target_tolerance_mm=1.0,
        is_controlled_warehouse=False,
    )
    print(f"  等级: {r2['grade']} | 通过: {'✅' if r2['passes'] else '❌'}")
    print(f"  总误差: ±{r2['budget']['total_budget_mm']}mm")
    print(f"  建议: {r2['recommendation']}")
    
    # 场景3: 亚洲灰板裱合（国产 + 亚洲市场）
    print("\n--- 场景3: 亚洲灰板裱合 ---")
    r3 = quick_tolerance_check(
        product_length_mm=250, product_width_mm=150,
        material_key="greyboard_2.0", machine_key="changrong_mk1060",
        target_tolerance_mm=0.5,
        is_controlled_warehouse=False, is_asia_market=True,
    )
    print(f"  等级: {r3['grade']} | 通过: {'✅' if r3['passes'] else '❌'}")
    print(f"  总误差: ±{r3['budget']['total_budget_mm']}mm")
    print(f"  建议: {r3['recommendation']}")
    if r3['warnings']:
        print(f"  预警: {'; '.join(r3['warnings'])}")
    
    # 输出完整JSON（供API使用）
    print("\n--- 完整JSON输出（场景1）---")
    print(json.dumps(r1, ensure_ascii=False, indent=2))
