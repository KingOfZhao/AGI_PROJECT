"""
test_core.py — 核心模块统一测试套件 v3
运行: python3 tests/test_core.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} — {detail}")
        failed += 1


def test_cognitive_core():
    print("\n[cognitive_core.py]")
    from cognitive_core import make_top_down_prompt, make_bottom_up_prompt

    p1 = make_top_down_prompt("测试问题")
    test("top_down返回消息列表", isinstance(p1, list))
    test("top_down非空", len(p1) >= 2)

    p2 = make_bottom_up_prompt("测试观察", "diecut")
    test("bottom_up返回消息列表", isinstance(p2, list))
    test("bottom_up非空", len(p2) >= 2)


def test_error_budget():
    print("\n[error_budget.py]")
    from error_budget import (
        calc_s_type_shrinkage, calc_fan_error, calc_total_budget,
        calc_crease_bridge_width, calc_critical_angle, calc_mc_compat_range,
        scenario_jiangzhehu_no_control, scenario_seasonal_calibrated,
        ErrorSource, ErrorCategory, MATERIALS,
        calc_bct_box_crush_test, calc_score_line_params,
    )

    s = calc_s_type_shrinkage(0.12, MATERIALS["white_card_300"])
    test("S型收缩正数", s > 0)
    test("S型收缩<10%", s < 0.1)

    s_abs = calc_s_type_shrinkage(0.14, MATERIALS["white_card_300"], False)
    s_des = calc_s_type_shrinkage(0.14, MATERIALS["white_card_300"], True)
    test("吸湿/脱湿路径不同", s_abs != s_des)

    fan = calc_fan_error(300, 300)
    test("扇形误差>0", fan["fan_total_mm"] > 0)

    errors = [
        ErrorSource("t1", ErrorCategory.DETERMINISTIC, 0.1),
        ErrorSource("t2", ErrorCategory.SEMI_DETERMINISTIC, 0.1),
        ErrorSource("t3", ErrorCategory.RANDOM, 0.1),
    ]
    budget = calc_total_budget(errors)
    test("总误差>0", budget["total_budget_mm"] > 0)
    test("安全系数影响",
         calc_total_budget(errors, safety_k=1.5)["total_budget_mm"] > budget["total_budget_mm"])

    bw = calc_crease_bridge_width(1.0, 30)
    test("清废桥宽>0", bw > 0)

    ca = calc_critical_angle(1.0)
    test("临界角>0", ca > 0)
    test("厚材料临界角大", calc_critical_angle(2.0) > ca)

    mc = calc_mc_compat_range(12, 300)
    test("MC范围合理", 5 < mc["mc_min_pct"] < 10)

    r1 = scenario_jiangzhehu_no_control()
    r2 = scenario_seasonal_calibrated()
    test("受控误差更小", r2["total_budget_mm"] < r1["total_budget_mm"])

    bct = calc_bct_box_crush_test(6.5, 1200, 1.5)
    test("BCT>0", bct["bct_n"] > 0)

    score = calc_score_line_params(1.5, "fefco")
    test("压痕宽>0", score["width_mm"] > 0)


def test_machine_database():
    print("\n[machine_database.py]")
    from machine_database import (
        MACHINES, calc_machine_error_contribution,
        recommend_machine, calc_thermal_compensation,
    )

    test("设备非空", len(MACHINES) >= 6)
    test("Bobst优于国产",
         MACHINES["bobst_sp104e"].precision_mm < MACHINES["changrong_mk1060"].precision_mm)

    contrib = calc_machine_error_contribution(0.3, 0.5)
    test("国产贡献率~60%", 55 < contrib["contribution_pct"] < 65)

    recs = recommend_machine(0.5, 0.4)
    test("推荐非空", len(recs) > 0)

    comp0 = calc_thermal_compensation(MACHINES["bobst_spo20"], 0, 300)
    comp60 = calc_thermal_compensation(MACHINES["bobst_spo20"], 60, 300)
    test("热膨胀增大", comp60["current_drift_mm"] > comp0["current_drift_mm"])


def test_node_cleaner():
    print("\n[node_cleaner.py]")
    from node_cleaner import parse_node_file
    r = parse_node_file(
        "/Users/administruter/Desktop/DiePre AI/待存入节点/"
        "20260324_104245_0003_REAL_SUCCESS_standard_international.md"
    )
    test("解析返回dict", isinstance(r, dict))
    test("node_id=0003", r["node_id"] == "0003")


def test_diepre_api():
    print("\n[diepre_api.py]")
    from diepre_api import quick_tolerance_check

    r = quick_tolerance_check(200, 100, "white_card_300", "bobst_sp104e")
    test("返回dict", isinstance(r, dict))
    test("含grade", "grade" in r)
    test("含budget", "budget" in r)

    r_err = quick_tolerance_check(200, 100, "nonexistent", "bobst_sp104e")
    test("处理未知材料", "error" in r_err)


def test_standards_database():
    print("\n[standards_database.py]")
    from standards_database import get_tolerance, get_strictest_tolerance, check_design_rules, StandardOrg

    test("ECMA=±0.3", abs(get_tolerance(StandardOrg.ECMA, 300) - 0.3) < 0.01)
    test("FEFCO小=±0.5", abs(get_tolerance(StandardOrg.FEFCO, 300) - 0.5) < 0.01)
    test("FEFCO大=±1.0", abs(get_tolerance(StandardOrg.FEFCO, 800) - 1.0) < 0.01)

    strict = get_strictest_tolerance(300)
    test("最严=ISO", strict["org"] == "ISO")

    checks = check_design_rules(tongue_depth_mm=20, box_width_mm=60,
                                 score_edge_dist_mm=1.0, board_thickness_mm=0.4)
    test("规则非空", len(checks) > 0)


def test_production_expansion():
    print("\n[error_budget.py - production_expansion]")
    from error_budget import (
        calc_production_expansion, calc_env_pre_expansion,
        calc_humidity_expansion, MATERIAL_CATALOG,
        ALPHA_CORRECTION_FACTORS, STANDARD_ENVIRONMENTS,
    )

    # 节点0133验证
    r = calc_production_expansion("white_card_300", 500, 6, "cd", "production_typical")
    val = r["delta_l_mm"]
    test("节点0133验证1.8mm", abs(val - 1.8) < 0.01, "got " + str(val))

    r_single = calc_production_expansion("white_card_300", 300, 5, "cd", "single_sheet")
    r_prod = calc_production_expansion("white_card_300", 300, 5, "cd", "production_typical")
    test("生产膨胀>单张", r_prod["delta_l_mm"] > r_single["delta_l_mm"])

    r_env = calc_env_pre_expansion("white_card_300", 500, "GB_T462", "JIS_P8127")
    test("GB->JIS膨胀>0", r_env["delta_l_mm"] > 0)

    r_fefco = calc_env_pre_expansion("white_card_300", 500, "FEFCO_Code", "JIS_P8127")
    test("FEFCO->JIS>GB->JIS", r_fefco["delta_l_mm"] > r_env["delta_l_mm"])

    test("材料目录>=5种", len(MATERIAL_CATALOG) >= 5)
    test("含B瓦楞", "corrugated_B" in MATERIAL_CATALOG)
    test("修正因子4级", len(ALPHA_CORRECTION_FACTORS) >= 4)
    test("生产修正=7.5", ALPHA_CORRECTION_FACTORS["production_typical"] == 7.5)
    test("标准环境5种", len(STANDARD_ENVIRONMENTS) >= 5)


def test_fefco_rules():
    print("\n[standards_database.py - FEFCO rules]")
    from standards_database import FEFCO_DESIGN_RULES, check_fefco_design_rules, DIMENSION_BASIS_DIFF

    test("FEFCO规则>=9条", len(FEFCO_DESIGN_RULES) >= 9)
    test("含FEFCO-001", "FEFCO-001" in FEFCO_DESIGN_RULES)
    test("FEFCO=内尺寸", "内尺寸" in DIMENSION_BASIS_DIFF.get("FEFCO", ""))
    test("JIS=外尺寸", "外尺寸" in DIMENSION_BASIS_DIFF.get("JIS", ""))

    checks = check_fefco_design_rules(tongue_depth_mm=10, box_width_mm=60,
                                        board_thickness_mm=1.5, grip_type="premium")
    tongue_check = [c for c in checks if c.get("rule") == "FEFCO-001"]
    if tongue_check:
        test("插舌过浅检测", not tongue_check[0]["passes"])


if __name__ == "__main__":
    print("=" * 50)
    print("核心模块测试套件 v3")
    print("=" * 50)

    test_cognitive_core()
    test_error_budget()
    test_machine_database()
    test_node_cleaner()
    test_diepre_api()
    test_standards_database()
    test_production_expansion()
    test_fefco_rules()

    print("\n" + "=" * 50)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)
