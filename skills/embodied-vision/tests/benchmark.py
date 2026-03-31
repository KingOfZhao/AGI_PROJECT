#!/usr/bin/env python3
"""
embodied-vision 端到端Benchmark
在多个样本上测试完整视觉能力
"""

import cv2
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 模块路径
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

exec(open(str(BASE / "primitives/__init__.py")).read())
exec(open(str(BASE / "spatial/__init__.py")).read())
exec(open(str(BASE / "action/__init__.py")).read())


def benchmark_single(image_path: str, label: str = "") -> dict:
    """对单张图像运行完整benchmark"""
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"无法读取: {image_path}"}
    
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = {"path": os.path.basename(image_path), "label": label, 
              "size": f"{w}x{h}"}
    
    # === P1: 感知原语 ===
    vp = VisualPrimitives()
    t0 = time.time()
    fast = vp.perceive_fast(img)
    result["p1_fast_ms"] = (time.time()-t0)*1000
    result["edge_pixels"] = fast["edge_count"]
    result["corners"] = fast["corner_count"]
    result["rectangles"] = fast.get("rectangles", 0)
    
    t0 = time.time()
    full = vp.perceive(img)
    result["p1_full_ms"] = (time.time()-t0)*1000
    result["contours"] = len(full["contours"])
    result["colors"] = len(full["color_regions"])
    result["texture_std"] = round(full["texture"].std, 1)
    result["texture_entropy"] = round(full["texture"].entropy, 2)
    result["texture_direction"] = round(full["texture"].dominant_direction, 0)
    
    # === P3: 空间理解 ===
    su = SpatialUnderstanding()
    t0 = time.time()
    spatial = su.understand(img)
    result["p3_spatial_ms"] = (time.time()-t0)*1000
    result["point_cloud"] = len(spatial["points"])
    result["depth_range"] = [round(float(spatial["depth_map"].min()), 0),
                              round(float(spatial["depth_map"].max()), 0)]
    result["ground_plane"] = "detected" if spatial["ground_plane"] else "none"
    
    stability = list(spatial["stability"].values())
    result["stable"] = stability[0].get("stable", None) if stability else None
    
    # === P4: 抓取规划 ===
    gp = GraspPlanner()
    t0 = time.time()
    grasps = gp.plan(img, (100, 200, w-200, h-400))
    result["p4_grasp_ms"] = (time.time()-t0)*1000
    result["grasp_points"] = len(grasps)
    result["best_grasp_quality"] = round(grasps[0].quality, 2) if grasps else 0
    
    # === 总计 ===
    result["total_ms"] = (result["p1_fast_ms"] + result["p1_full_ms"] + 
                           result["p3_spatial_ms"] + result["p4_grasp_ms"])
    
    return result


def run_benchmark(image_dir: str):
    """运行完整benchmark"""
    p = Path(image_dir)
    images = sorted(list(p.glob("*.jpg")) + list(p.glob("*.JPG")) + 
                    list(p.glob("*.png")) + list(p.glob("*.PNG")))
    
    print(f"{'='*80}")
    print(f"  EMBODIED VISION BENCHMARK")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  样本数: {len(images)}")
    print(f"{'='*80}")
    
    results = []
    for img_path in images:
        result = benchmark_single(str(img_path))
        results.append(result)
        print(f"  {os.path.basename(img_path):40s} | "
              f"P1={result.get('p1_fast_ms',0):5.0f}+{result.get('p1_full_ms',0):5.0f}ms | "
              f"P3={result.get('p3_spatial_ms',0):6.0f}ms | "
              f"边={result.get('edge_pixels',0):>6,} "
              f"角={result.get('corners',0):>4} "
              f"轮={result.get('contours',0):>4} "
              f"云={result.get('point_cloud',0):>6,} | "
              f"总={result.get('total_ms',0):6.0f}ms")
    
    # 汇总统计
    if results:
        print(f"\n{'='*80}")
        print(f"  汇总统计:")
        valid = [r for r in results if "error" not in r]
        if valid:
            print(f"    成功: {len(valid)}/{len(results)}")
            print(f"    平均快速感知: {sum(r['p1_fast_ms'] for r in valid)/len(valid):.0f}ms")
            print(f"    平均完整感知: {sum(r['p1_full_ms'] for r in valid)/len(valid):.0f}ms")
            print(f"    平均空间理解: {sum(r['p3_spatial_ms'] for r in valid)/len(valid):.0f}ms")
            print(f"    平均总耗时: {sum(r['total_ms'] for r in valid)/len(valid):.0f}ms")
            print(f"    平均点云: {sum(r['point_cloud'] for r in valid)/len(valid):,.0f} 点")
            print(f"    平均边缘: {sum(r['edge_pixels'] for r in valid)/len(valid):,.0f} px")
    
    # 保存JSON
    out = BASE / "benchmark_results.json"
    with open(str(out), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  结果保存: {out}")
    
    return results


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop"
    run_benchmark(target)
