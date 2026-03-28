#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG → DXF 批量转换工具

macOS 上 AutoCAD 没有 accoreconsole，需要通过 AppleScript 控制 AutoCAD 2026
逐个打开 DWG 并另存为 DXF。

用法:
  python3 scripts/convert_dwg_to_dxf.py [--input DIR] [--output DIR] [--method METHOD]

方法:
  autocad   - 通过 AppleScript 控制 AutoCAD 2026 (推荐，需 AutoCAD 运行)
  manual    - 生成 AutoCAD .scr 批处理脚本文件，手动在 AutoCAD 中运行
"""

import os
import sys
import glob
import subprocess
import argparse
import time

DWG_DIR = "/Users/administruter/Desktop/拉扯图形"
DXF_OUTPUT_DIR = "/Users/administruter/Desktop/拉扯图形/dxf_output"


def find_dwg_files(root_dir):
    """递归查找所有 DWG 文件"""
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.lower().endswith('.dwg') and not f.startswith('.'):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def convert_via_autocad_applescript(dwg_files, output_dir):
    """通过 AppleScript 控制 AutoCAD 2026 批量转换"""
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n将通过 AppleScript 控制 AutoCAD 2026 转换 {len(dwg_files)} 个文件")
    print(f"输出目录: {output_dir}")
    print("请确保 AutoCAD 2026 已启动!\n")

    success, fail = 0, 0
    for i, dwg_path in enumerate(dwg_files):
        fname = os.path.basename(dwg_path)
        dxf_name = os.path.splitext(fname)[0] + ".dxf"
        dxf_path = os.path.join(output_dir, dxf_name)

        if os.path.exists(dxf_path):
            print(f"  [{i+1}/{len(dwg_files)}] 跳过(已存在): {fname}")
            success += 1
            continue

        print(f"  [{i+1}/{len(dwg_files)}] 转换: {fname} ...", end=" ", flush=True)

        # AppleScript: 让 AutoCAD 打开文件，SAVEAS DXF，然后关闭
        script = f'''
tell application "AutoCAD 2026"
    activate
    open POSIX file "{dwg_path}"
    delay 3
    do script "DXFOUT\\n{dxf_path}\\n16\\n"
    delay 2
    do script "CLOSE\\nN\\n"
    delay 1
end tell
'''
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and os.path.exists(dxf_path):
                print("OK")
                success += 1
            else:
                print(f"FAIL ({result.stderr.strip()[:50]})")
                fail += 1
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            fail += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail += 1

        time.sleep(1)  # 给 AutoCAD 喘息时间

    return success, fail


def generate_scr_script(dwg_files, output_dir):
    """生成 AutoCAD .scr 批处理脚本"""
    os.makedirs(output_dir, exist_ok=True)
    scr_path = os.path.join(output_dir, "_batch_convert.scr")

    lines = []
    for dwg_path in dwg_files:
        fname = os.path.basename(dwg_path)
        dxf_name = os.path.splitext(fname)[0] + ".dxf"
        dxf_path = os.path.join(output_dir, dxf_name)
        lines.append(f'OPEN "{dwg_path}"')
        lines.append(f'DXFOUT "{dxf_path}" 16')
        lines.append('CLOSE N')

    with open(scr_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"\n已生成 AutoCAD 批处理脚本: {scr_path}")
    print(f"包含 {len(dwg_files)} 个文件的转换命令")
    print(f"\n使用方法:")
    print(f"  1. 打开 AutoCAD 2026")
    print(f"  2. 命令行输入: SCRIPT")
    print(f'  3. 选择文件: {scr_path}')
    print(f"  4. 等待自动转换完成")
    print(f"  5. DXF 文件将保存到: {output_dir}")
    return scr_path


def generate_import_after_convert_script(output_dir):
    """生成转换后的导入脚本"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "import_converted_dxf.py")

    content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入已转换的 DXF 文件到盒型模板数据库"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_dwg_templates import analyze_dwg, save_template, init_db

DXF_DIR = "{output_dir}"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box_templates.db")

def main():
    dxf_files = [os.path.join(DXF_DIR, f) for f in os.listdir(DXF_DIR) if f.lower().endswith('.dxf')]
    print(f"找到 {{len(dxf_files)}} 个 DXF 文件")
    conn = init_db(DB_PATH)
    ok, err = 0, 0
    for i, fp in enumerate(dxf_files):
        fname = os.path.basename(fp)
        print(f"  [{{i+1}}/{{len(dxf_files)}}] {{fname}} ...", end=" ")
        data = analyze_dwg(fp)
        if data.get("error"):
            print(f"ERROR: {{data['error'][:60]}}")
            err += 1
        else:
            save_template(conn, data)
            ft = data.get("features", {{}})
            print(f"OK  type={{ft.get('box_type','?')}}")
            ok += 1
    print(f"\\n完成: {{ok}} 成功, {{err}} 失败")
    conn.close()

if __name__ == "__main__":
    main()
'''
    with open(script_path, 'w') as f:
        f.write(content)
    print(f"\n转换后导入脚本已生成: {script_path}")
    print(f"转换完 DWG→DXF 后运行: python3 {script_path}")


def main():
    parser = argparse.ArgumentParser(description="DWG → DXF 批量转换")
    parser.add_argument('--input', default=DWG_DIR, help='DWG文件目录')
    parser.add_argument('--output', default=DXF_OUTPUT_DIR, help='DXF输出目录')
    parser.add_argument('--method', choices=['autocad', 'manual'], default='manual',
                       help='转换方法: autocad(AppleScript自动) / manual(生成.scr脚本)')
    args = parser.parse_args()

    print("=" * 60)
    print("  DWG → DXF 批量转换工具")
    print("=" * 60)

    dwg_files = find_dwg_files(args.input)
    print(f"\n扫描目录: {args.input}")
    print(f"找到 {len(dwg_files)} 个 DWG 文件")

    if not dwg_files:
        print("无文件需要转换")
        return

    if args.method == 'autocad':
        success, fail = convert_via_autocad_applescript(dwg_files, args.output)
        print(f"\n转换完成: {success} 成功, {fail} 失败")
    else:
        generate_scr_script(dwg_files, args.output)

    generate_import_after_convert_script(args.output)

    print(f"\n{'='*60}")
    print(f"  完整流程:")
    print(f"  1. 运行此脚本生成 .scr 批处理文件")
    print(f"  2. 在 AutoCAD 2026 中执行 SCRIPT 命令加载 .scr")
    print(f"  3. 运行 import_converted_dxf.py 将 DXF 导入数据库")
    print(f"  4. 在 Web 盒型编辑器中查看和使用模板")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
