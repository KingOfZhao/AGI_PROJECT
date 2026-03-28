#!/usr/bin/env python3
"""
完整管线: DXF/DWG → 活字模块拆解 → STL生成 → 装配指南
"""
import os, json, sys
from datetime import datetime
from module_decomposer import ModuleDecomposer, parse_dxf_entities, generate_test_box, Segment
from stl_generator import ModuleSTLGenerator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_pipeline(dxf_path: str = None, blade_point: str = "2pt",
                 test_box: tuple = None) -> dict:
    """
    执行完整管线
    Args:
        dxf_path: DXF文件路径 (可选)
        blade_point: 刀片规格 2pt/3pt/4pt
        test_box: 测试盒尺寸 (L, W, H) (可选, 无DXF时使用)
    Returns:
        管线结果字典
    """
    print(f"\n{'='*60}")
    print(f"  刀模活字模块化管线")
    print(f"  刀片: {blade_point} | 源: {dxf_path or f'测试盒{test_box}'}")
    print(f"{'='*60}\n")

    result = {
        "timestamp": datetime.now().isoformat(),
        "blade_point": blade_point,
        "source": dxf_path or f"test_box_{test_box}",
    }

    # Step 1: 解析几何实体
    print("Step 1: 解析几何实体...")
    if dxf_path and os.path.exists(dxf_path):
        segments = parse_dxf_entities(dxf_path)
        result["source_type"] = "DXF"
    elif test_box:
        L, W, H = test_box
        segments = generate_test_box(L, W, H)
        result["source_type"] = "test_box"
        result["test_box"] = {"L": L, "W": W, "H": H}
    else:
        print("⚠ 无输入源, 使用默认300×200×150测试盒")
        segments = generate_test_box(300, 200, 150)
        result["source_type"] = "test_box"
        result["test_box"] = {"L": 300, "W": 200, "H": 150}

    result["total_segments"] = len(segments)
    cut_segs = [s for s in segments if s.layer == "CUT"]
    crease_segs = [s for s in segments if s.layer == "CREASE"]
    print(f"  → {len(segments)} 实体 (CUT:{len(cut_segs)} CREASE:{len(crease_segs)})")

    # Step 2: 模块拆解
    print("\nStep 2: 活字模块拆解...")
    decomposer = ModuleDecomposer(blade_point)
    decomposer.add_segments(segments)
    modules = decomposer.decompose()
    summary = decomposer.summary()
    result["decomposition"] = summary
    print(f"  → {summary['total_modules']} 模块 ({summary['unique_types']}种)")
    for t, c in sorted(summary["type_breakdown"].items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")

    # Step 3: 保存模块清单
    print("\nStep 3: 保存模块清单...")
    modules_path = os.path.join(OUTPUT_DIR, "module_list.json")
    with open(modules_path, "w", encoding="utf-8") as f:
        f.write(decomposer.to_json())
    result["module_list_path"] = modules_path
    print(f"  → {modules_path}")

    # Step 4: 生成STL文件
    print("\nStep 4: 生成标准模块STL...")
    stl_gen = ModuleSTLGenerator(blade_point)
    stl_files = stl_gen.generate_all_standard()
    result["stl_files"] = [os.path.basename(f) for f in stl_files]
    result["stl_count"] = len(stl_files)

    # Step 5: 生成BOM
    print("\nStep 5: 生成物料清单...")
    bom_path = os.path.join(OUTPUT_DIR, "BOM.md")
    with open(bom_path, "w", encoding="utf-8") as f:
        f.write(decomposer.to_bom())
    result["bom_path"] = bom_path
    print(f"  → {bom_path}")

    # Step 6: 生成装配指南
    print("\nStep 6: 生成装配指南...")
    guide = _generate_assembly_guide(decomposer, blade_point, summary)
    guide_path = os.path.join(OUTPUT_DIR, "assembly_guide.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(guide)
    result["guide_path"] = guide_path
    print(f"  → {guide_path}")

    # Step 7: 保存管线结果
    result_path = os.path.join(OUTPUT_DIR, "pipeline_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ 管线完成!")
    print(f"  模块: {summary['total_modules']} 个 ({summary['unique_types']}种)")
    print(f"  复用率: {summary['reuse_rate']*100:.1f}%")
    print(f"  打印时间: ~{summary['total_print_time_hours']:.1f} 小时")
    print(f"  材料成本: ~¥{summary['est_material_cost_yuan']:.1f}")
    print(f"  STL文件: {len(stl_files)} 个 → 模块库/")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    return result


def _generate_assembly_guide(decomposer, blade_point, summary) -> str:
    """生成装配指南Markdown"""
    bp_mm = IADD_STEEL_RULE_SPECS_LOCAL.get(blade_point, 0.71)
    lines = [
        "# 刀模活字模块装配指南",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 刀片规格: {blade_point}",
        "",
        "## 一、材料准备",
        "",
        f"| 物料 | 规格 | 数量 |",
        f"|------|------|------|",
        f"| 3D打印模块 | PETG-CF, 层高0.15mm | {summary['total_modules']}个 |",
        f"| 底板模块 | PLA, 层高0.20mm | {summary['type_breakdown'].get('BASE_TILE', 0)}块 |",
        f"| 钢规刀片 | {blade_point}, 高23.8mm | 按展开图周长裁剪 |",
        f"| 弹性橡胶 | 闭孔泡沫, 高25mm | 按需裁剪 |",
        "",
        "## 二、打印设置 (Bambu Studio)",
        "",
        "| 参数 | 模块 | 底板 |",
        "|------|------|------|",
        "| 材料 | PETG-CF | PLA |",
        "| 层高 | 0.15mm | 0.20mm |",
        "| 填充 | 80% 网格 | 20% 网格 |",
        "| 壁数 | 4 | 3 |",
        "| 速度 | 150mm/s | 200mm/s |",
        "| 温度 | 260°C/80°C | 220°C/60°C |",
        "| 打印方向 | 刀槽沿Z轴 | 平放 |",
        "",
        "## 三、装配步骤",
        "",
        "### 3.1 底板拼接",
        "1. 将底板模块平铺在工作台上",
        "2. 对齐边缘拼接榫和定位销",
        "3. 确认平面度 < 0.1mm (用直尺检查)",
        "",
        "### 3.2 模块安装",
        "1. **从中心向外**: 先安装最长的直线段模块",
        "2. 将模块的燕尾榫滑入相邻模块",
        "3. 安装转角模块, 确认角度锁定",
        "4. 安装T形/十字接头",
        "5. 安装端头模块封闭路径",
        "6. 安装桥接模块",
        "",
        "### 3.3 刀片安装",
        "1. 将钢规刀片按展开图裁剪到所需长度",
        "2. **刀片跨接**: 刀片长度应跨越模块接缝",
        "3. 将刀片压入模块刀槽 (过盈配合+0.03mm)",
        "4. 检查刀片高度一致性 (23.8mm ±0.25mm)",
        "",
        "### 3.4 弹料安装",
        "1. 裁剪闭孔泡沫至弹料座尺寸",
        "2. 粘贴到弹料座模块",
        "3. 弹料高出刀片约1.5mm",
        "",
        "## 四、质量检查",
        "",
        "| 检查项 | 标准 | 工具 |",
        "|--------|------|------|",
        "| 平面度 | < 0.1mm | 直尺+塞尺 |",
        "| 模块间隙 | < 0.3mm | 塞尺 |",
        "| 刀片高度 | 23.8 ±0.25mm | 卡尺 |",
        "| 刀片垂直度 | < 1° | 角尺 |",
        "| 弹料高度 | 刀片+1.5mm | 卡尺 |",
        "",
        "## 五、使用注意",
        "",
        "- 首次使用前在废纸上试切",
        "- PETG-CF耐温≤80°C, 避免高温环境",
        "- 模块可拆卸重组用于不同刀模",
        "- 刀片磨损后可单独更换",
        f"- 预估总打印时间: {summary['total_print_time_hours']:.1f} 小时",
        f"- 预估材料成本: ¥{summary['est_material_cost_yuan']:.1f}",
    ]
    return "\n".join(lines)


# 局部引用避免循环导入
IADD_STEEL_RULE_SPECS_LOCAL = {"2pt": 0.71, "3pt": 1.07, "4pt": 1.42}


if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        dxf = sys.argv[1]
        bp = sys.argv[2] if len(sys.argv) > 2 else "2pt"
        run_pipeline(dxf_path=dxf, blade_point=bp)
    else:
        L = int(sys.argv[1]) if len(sys.argv) > 1 else 300
        W = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        H = int(sys.argv[3]) if len(sys.argv) > 3 else 150
        bp = sys.argv[4] if len(sys.argv) > 4 else "2pt"
        run_pipeline(test_box=(L, W, H), blade_point=bp)
