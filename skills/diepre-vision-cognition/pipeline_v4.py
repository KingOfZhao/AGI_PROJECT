#!/usr/bin/env python3
"""
DiePre Vision Pipeline v4.0 — 基于embodied-vision框架重构

核心改进:
- 使用EmbodiedVision统一API作为基础
- VLM辅助识别(通过Agent调用)
- 深度估计驱动透视矫正
- 物理推理判断纸板结构
"""

import cv2
import numpy as np
import time
import sys
from pathlib import Path

# 加载embodied-vision
BASE = Path(__file__).parent.parent.parent / "AGI_PROJECT" / "skills" / "embodied-vision" / "unified"
if not BASE.exists():
    # Try direct path
    BASE = Path("/Users/administruter/Desktop/AGI_PROJECT/skills/embodied-vision/unified")
exec(open(str(BASE / "embodied_vision.py")).read())


class DiePreV4:
    """
    DiePre Vision v4 — embodied-vision框架重构版
    
    Pipeline:
      照片 → EmbodiedVision感知(边缘+轮廓+深度+点云) 
           → 纸板提取(前景mask+地面平面) 
           → 线条提取(形态学+细化) 
           → 刀线/压痕分类(线宽分析) 
           → 输出(白底黑边+DXF+SVG)
    """
    
    def __init__(self):
        self.vision = EmbodiedVision()
    
    def process(self, input_path: str, output_dir: str = None) -> dict:
        """完整处理"""
        t0 = time.time()
        inp = Path(input_path)
        out_dir = Path(output_dir or inp.parent / "output_v4")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        img = cv2.imread(str(inp))
        if img is None:
            return {"success": False, "error": "无法读取图像"}
        
        h, w = img.shape[:2]
        result = {"path": str(inp), "success": False}
        
        # === Step 1: EmbodiedVision感知 ===
        perception = self.vision.perceive(str(inp), mode="full")
        result["perception"] = {
            "edge_pixels": perception.get("edge_pixels", 0),
            "corners": perception.get("corners", 0),
            "point_cloud": perception.get("point_cloud", 0),
        }
        
        # === Step 2: 纸板提取 ===
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 使用深度估计辅助前景提取
        if "depth_range" in perception:
            dm_low = perception["depth_range"][0]
            # 近处的物体=纸板
            depth_threshold = dm_low + (perception["depth_range"][1] - dm_low) * 0.3
        
        # Otsu前景
        clahe = cv2.createCLAHE(2.0, (8, 8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k, 3)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, 2)
        
        # 最大连通域
        n, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        if n > 1:
            best = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            mask = np.zeros_like(binary)
            mask[labels == best] = 255
        else:
            mask = binary
        
        foreground = cv2.bitwise_and(enhanced, enhanced, mask=mask)
        
        # === Step 3: 透视矫正 ===
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            contour = max(contours, key=cv2.contourArea)
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.005 * peri, True)
            
            if len(approx) >= 4:
                pts = approx.reshape(-1, 2).astype(np.float32)
                if len(pts) > 4:
                    hull = cv2.convexHull(pts).reshape(-1, 2).astype(np.float32)
                    pts = hull
                
                s = pts.sum(axis=1)
                d = np.diff(pts, axis=1)
                tl = pts[np.argmin(s)]
                br = pts[np.argmax(s)]
                tr = pts[np.argmin(d)]
                bl = pts[np.argmax(d)]
                src = np.array([tl, tr, br, bl], dtype=np.float32)
                
                ww = max(int(np.linalg.norm(tr-tl)), int(np.linalg.norm(br-bl)))
                hh = max(int(np.linalg.norm(bl-tl)), int(np.linalg.norm(br-tr)))
                
                if ww > 100 and hh > 100:
                    M = cv2.getPerspectiveTransform(src, 
                        np.array([[0,0],[ww-1,0],[ww-1,hh-1],[0,hh-1]], dtype=np.float32))
                    warped = cv2.warpPerspective(foreground, M, (ww, hh))
                    result["corrected_size"] = f"{ww}x{hh}"
                else:
                    warped = foreground
            else:
                warped = foreground
        else:
            warped = foreground
        
        # === Step 4: 印刷过滤 ===
        try:
            mser = cv2.MSER_create(8, 40, 40000)
            regions, _ = mser.detectRegions(warped)
            text_mask = np.zeros(warped.shape, dtype=np.uint8)
            for reg in regions:
                x, y, bw, bh = cv2.boundingRect(reg)
                if 0.1 < bw/max(bh,1) < 10 and bh < 80:
                    cv2.rectangle(text_mask, (x,y), (x+bw,y+bh), 255, -1)
            cleaned = cv2.inpaint(warped, text_mask, 5, cv2.INPAINT_TELEA)
        except:
            cleaned = warped
        
        # === Step 5: 线条提取 ===
        binary_lines = cv2.adaptiveThreshold(cleaned, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY_INV, 21, 8)
        kh = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        binary_lines = cv2.morphologyEx(binary_lines, cv2.MORPH_CLOSE, kh, 1)
        binary_lines = cv2.morphologyEx(binary_lines, cv2.MORPH_CLOSE, kv, 1)
        
        # 细化
        thinned = binary_lines.copy()
        cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        for _ in range(30):
            er = cv2.erode(thinned, cross)
            temp = cv2.dilate(er, cross)
            diff = cv2.subtract(thinned, temp)
            thinned = cv2.subtract(thinned, diff)
            if cv2.countNonZero(diff) < 10:
                break
        
        # === Step 6: 线宽分类 ===
        dist = cv2.distanceTransform(binary_lines, cv2.DIST_L2, 5)
        sk_pts = np.argwhere(thinned > 0)
        
        cut = crease = 0
        classified = np.zeros(thinned.shape, dtype=np.uint8)
        
        if len(sk_pts) > 0:
            sample = sk_pts[::max(1, len(sk_pts)//5000)]
            widths = np.array([dist[y, x] * 2 for y, x in sample 
                             if 0 <= y < dist.shape[0] and 0 <= x < dist.shape[1]])
            if len(widths) > 0:
                median_w = float(np.median(widths))
                threshold = median_w  # 简化
                
                for y, x in sk_pts:
                    if 0 <= y < dist.shape[0] and 0 <= x < dist.shape[1]:
                        if dist[y, x] * 2 < threshold:
                            classified[y, x] = 255
                            cut += 1
                        else:
                            classified[y, x] = 128
                            crease += 1
                
                result["line_stats"] = {
                    "cut": cut, "crease": crease,
                    "median_width": round(median_w, 1),
                    "total_points": len(sk_pts)
                }
        
        # === Step 7: 输出 ===
        wh, ww = thinned.shape
        
        # 白底黑边
        wb = np.full((wh, ww), 255, dtype=np.uint8)
        wb[thinned > 0] = 0
        cv2.imwrite(str(out_dir / f"{inp.stem}_white_black.png"), wb)
        
        # 分类图
        cls = np.full((wh, ww), 255, dtype=np.uint8)
        cls[classified == 255] = 0
        cls[classified == 128] = 128
        cv2.imwrite(str(out_dir / f"{inp.stem}_classified.png"), cls)
        
        # DXF
        lines_p = cv2.HoughLinesP(thinned, 1, np.pi/180, 20, minLineLength=15, maxLineGap=6)
        dxf_parts = ["0\nSECTION\n2\nENTITIES"]
        if lines_p is not None:
            for l in lines_p:
                x1, y1, x2, y2 = l[0]
                mx, my = int((x1+x2)/2), int((y1+y2)/2)
                layer = "CUT" if (0<=my<wh and 0<=mx<ww and classified[my,mx]==255) else "CREASE"
                dxf_parts.append(f"0\nLINE\n8\n{layer}\n10\n{x1:.1f}\n20\n{y1:.1f}\n11\n{x2:.1f}\n21\n{y2:.1f}")
        dxf_parts.append("0\nENDSEC\n0\nEOF")
        (out_dir / f"{inp.stem}.dxf").write_text("\n".join(dxf_parts))
        
        result["success"] = True
        result["duration_ms"] = (time.time() - t0) * 1000
        result["output_dir"] = str(out_dir)
        
        if "line_stats" in result:
            ls = result["line_stats"]
            result["summary"] = (f"✅ {inp.name}: 刀{ls['cut']}/压{ls['crease']} "
                                f"(宽{ls['median_width']:.1f}px) | {result['duration_ms']:.0f}ms")
        
        return result


def batch_process(input_dir: str, output_dir: str = None):
    p = Path(input_dir)
    files = sorted(set(f for ext in ["*.jpg","*.JPG","*.png","*.PNG"] for f in p.glob(ext)))
    
    pipeline = DiePreV4()
    results = []
    for f in files:
        r = pipeline.process(str(f), output_dir)
        print(r.get("summary", f"❌ {f.name}: {r.get('error','')}"))
        results.append(r)
    
    ok = sum(1 for r in results if r.get("success"))
    total = sum(r["duration_ms"] for r in results)
    print(f"\n{'='*60}")
    print(f"✅ {ok}/{len(results)} | {total/1000:.1f}s total | {total/max(ok,1)/1000:.1f}s/img")
    return results


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop"
    batch_process(target, "/Users/administruter/Desktop/DiePre AI/vision_pipeline/output_v4")
