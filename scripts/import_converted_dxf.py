#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入已转换的 DXF 文件到盒型模板数据库"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_dwg_templates import analyze_dwg, save_template, init_db

DXF_DIR = "/Users/administruter/Desktop/拉扯图形/dxf_output"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box_templates.db")

def main():
    dxf_files = [os.path.join(DXF_DIR, f) for f in os.listdir(DXF_DIR) if f.lower().endswith('.dxf')]
    print(f"找到 {len(dxf_files)} 个 DXF 文件")
    conn = init_db(DB_PATH)
    ok, err = 0, 0
    for i, fp in enumerate(dxf_files):
        fname = os.path.basename(fp)
        print(f"  [{i+1}/{len(dxf_files)}] {fname} ...", end=" ")
        data = analyze_dwg(fp)
        if data.get("error"):
            print(f"ERROR: {data['error'][:60]}")
            err += 1
        else:
            save_template(conn, data)
            ft = data.get("features", {})
            print(f"OK  type={ft.get('box_type','?')}")
            ok += 1
    print(f"\n完成: {ok} 成功, {err} 失败")
    conn.close()

if __name__ == "__main__":
    main()
