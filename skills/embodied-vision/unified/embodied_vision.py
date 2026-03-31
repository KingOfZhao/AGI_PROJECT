#!/usr/bin/env python3
"""
embodied-vision unified API — 单文件版
将所有模块合并为一个独立可运行的文件
"""

import cv2
import numpy as np
import math
import json
import time
import sys
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from pathlib import Path

# ═══════════════════════════════════════════
# PRIMITIVES
# ═══════════════════════════════════════════

class EdgeDetector:
    def detect_single(self, gray):
        v = np.median(gray)
        return cv2.Canny(gray, max(0, 0.7*v), min(255, 1.3*v))
    
    def detect(self, gray):
        v = np.median(gray)
        edges = [cv2.Canny(gray, max(0, 0.7*v), min(255, 1.3*v))]
        fused = edges[0]
        for scale in [1.5, 2.0]:
            h, w = gray.shape
            scaled = cv2.resize(gray, (int(w/scale), int(h/scale)))
            e = cv2.Canny(scaled, max(0, 0.7*v/scale), min(255, 1.3*v/scale))
            e = cv2.resize(e, (w, h))
            fused = cv2.bitwise_or(fused, e)
            edges.append(e)
        edges.append(fused)
        return edges


class CornerDetector:
    def detect(self, gray, method="orb", max_points=500):
        if method == "orb":
            orb = cv2.ORB_create(nfeatures=max_points)
            kp = orb.detect(gray)
            return [(p.pt[0], p.pt[1], p.response, p.size) for p in kp[:max_points]]
        elif method == "fast":
            fast = cv2.FastFeatureDetector_create()
            kp = fast.detect(gray)
            return [(p.pt[0], p.pt[1], p.response, p.size) for p in kp[:max_points]]
        return []


class TextureAnalyzer:
    def analyze(self, gray):
        mean = float(np.mean(gray))
        std = float(np.std(gray))
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist / hist.sum()
        entropy = -float(np.sum(hist * np.log2(hist + 1e-10)))
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        angles = np.arctan2(gy, gx) * 180 / np.pi % 180
        hist_a, bins = np.histogram(angles.ravel(), bins=36, range=(0, 180))
        direction = float(bins[np.argmax(hist_a)])
        return {"mean": mean, "std": std, "entropy": entropy, "direction": direction}


class ColorSegmenter:
    RANGES = {
        "red": [(0,100,50),(10,255,255),(160,100,50),(180,255,255)],
        "orange": [(10,100,50),(25,255,255)],
        "yellow": [(25,100,50),(35,255,255)],
        "green": [(35,100,50),(85,255,255)],
        "blue": [(85,100,50),(135,255,255)],
        "white": [(0,0,200),(180,30,255)],
        "gray": [(0,0,50),(180,30,200)],
        "black": [(0,0,0),(180,255,50)],
    }
    
    def segment(self, bgr):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        regions = []
        for name, ranges in self.RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for i in range(0, len(ranges), 2):
                m = cv2.inRange(hsv, np.array(ranges[i]), np.array(ranges[i+1]))
                mask = cv2.bitwise_or(mask, m)
            area = cv2.countNonZero(mask)
            if area > 500:
                regions.append({"name": name, "area": area})
        return sorted(regions, key=lambda r: -r["area"])


class VisualPrimitives:
    def __init__(self):
        self.edge = EdgeDetector()
        self.corner = CornerDetector()
        self.texture = TextureAnalyzer()
        self.color = ColorSegmenter()
    
    def perceive_fast(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
        edge = self.edge.detect_single(gray)
        corners = self.corner.detect(gray, "fast", 100)
        return {"edge_count": int(cv2.countNonZero(edge)), "corners": len(corners), "edges": edge}
    
    def perceive(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
        edge = self.edge.detect_single(gray)
        corners = self.corner.detect(gray, "orb")
        contours, _ = cv2.findContours(edge, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        texture = self.texture.analyze(gray)
        color_regions = self.color.segment(img) if len(img.shape)==3 else []
        
        contour_list = []
        for cnt in contours[:50]:
            area = cv2.contourArea(cnt)
            if area < 30: continue
            peri = cv2.arcLength(cnt, True)
            circ = 4*np.pi*area/(peri**2) if peri>0 else 0
            M = cv2.moments(cnt)
            if M["m00"]==0: continue
            cx, cy = M["m10"]/M["m00"], M["m01"]/M["m00"]
            x,y,w,h = cv2.boundingRect(cnt)
            contour_list.append({"points": cnt, "area": area, "circularity": circ,
                               "centroid": (cx,cy), "bbox": (x,y,w,h),
                               "aspect_ratio": w/max(h,1)})
        
        return {"edges": edge, "corners": corners, "contours": contour_list,
                "texture": texture, "color_regions": color_regions}


# ═══════════════════════════════════════════
# SPATIAL
# ═══════════════════════════════════════════

class MonocularDepthEstimator:
    def estimate(self, bgr, camera_height_mm=500.0, fov_deg=60.0):
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape)==3 else bgr
        h, w = gray.shape
        y_coords = np.arange(h, dtype=np.float32).reshape(-1, 1)
        depth_pos = 1.0 - y_coords / h
        
        blur = cv2.GaussianBlur(gray, (31,31), 0)
        detail = np.abs(gray.astype(float) - blur.astype(float))
        blur_det = cv2.GaussianBlur(detail, (21,21), 0)
        depth_tex = 1.0 - blur_det / max(blur_det.max(), 1)
        
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        sharp = cv2.GaussianBlur(np.abs(lap), (21,21), 0)
        depth_sharp = 1.0 - sharp / max(sharp.max(), 1)
        
        depth = 0.35*depth_pos + 0.30*depth_tex + 0.35*depth_sharp
        depth = cv2.GaussianBlur(depth, (31,31), 0)
        return (200 + depth * 4800).astype(np.float32)


class PointCloudGenerator:
    def __init__(self, fx=800, fy=800):
        self.fx, self.fy = fx, fy
    
    def generate(self, depth_map, max_points=50000):
        h, w = depth_map.shape
        cx, cy = w/2, h/2
        points = []
        step = max(1, int(math.sqrt(h*w/max_points)))
        for y in range(0, h, step):
            for x in range(0, w, step):
                z = float(depth_map[y, x])
                if z <= 0: continue
                x3 = (x - cx) * z / self.fx
                y3 = (y - cy) * z / self.fy
                points.append((x3, y3, z))
        return points
    
    def get_plane(self, points):
        if len(points) < 10: return None
        arr = np.array(points)
        best_inliers = 0
        best_plane = None
        for _ in range(100):
            idx = np.random.choice(len(arr), 3, replace=False)
            p1, p2, p3 = arr[idx]
            normal = np.cross(p2-p1, p3-p1)
            norm = np.linalg.norm(normal)
            if norm < 1e-10: continue
            normal /= norm
            d = -np.dot(normal, p1)
            dists = np.abs(arr @ normal + d)
            inliers = np.sum(dists < 5.0)
            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = tuple(normal.tolist()) + (float(d),)
        return best_plane


class SpatialUnderstanding:
    def __init__(self):
        self.depth = MonocularDepthEstimator()
        self.pc = PointCloudGenerator()
    
    def understand(self, bgr):
        t0 = time.time()
        dm = self.depth.estimate(bgr)
        pts = self.pc.generate(dm, 50000)
        plane = self.pc.get_plane(pts[:5000])
        return {
            "depth_map": dm, "points": pts, "ground_plane": plane,
            "depth_range": (float(dm.min()), float(dm.max())),
            "duration": time.time()-t0
        }


# ═══════════════════════════════════════════
# ACTION
# ═══════════════════════════════════════════

class GraspPlanner:
    def plan(self, img, bbox):
        x, y, w, h = bbox
        cx, cy = x+w//2, y+h//2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape)==3 else img
        r = 20
        x1, x2 = max(0, cx-r), min(gray.shape[1], cx+r)
        y1, y2 = max(0, cy-r), min(gray.shape[0], cy+r)
        if x2<=x1 or y2<=y1: return []
        roi = gray[y1:y2, x1:x2]
        edge = cv2.Canny(roi, 50, 150)
        quality = np.sum(edge>0)/edge.size
        grasps = [{"x": cx, "y": cy, "angle": 0, "width": min(w,h), 
                  "quality": round(float(quality), 2), "method": "top"}]
        # 侧面抓取
        if h > w * 1.5:
            grasps.append({"x": x, "y": cy, "angle": 90, "width": h, 
                          "quality": round(float(quality)*0.8, 2), "method": "side"})
        return sorted(grasps, key=lambda g: -g["quality"])


class TrajectoryPlanner:
    @staticmethod
    def plan_pick_place(start, end, height=100, n=20):
        sx,sy,sz = start; ex,ey,ez = end
        def lerp(a,b,n):
            return [tuple(a[j]+(b[j]-a[j])*i/n for j in range(3)) for i in range(n+1)]
        above_s = (sx, sy, sz+height)
        above_e = (ex, ey, ez+height)
        return lerp(start, above_s, n//4) + lerp(above_s, above_e, n//2) + lerp(above_e, end, n//4)


# ═══════════════════════════════════════════
# UNIFIED API
# ═══════════════════════════════════════════

class EmbodiedVision:
    """统一具身视觉API — 一行代码获取完整视觉理解"""
    
    def __init__(self):
        self.prim = VisualPrimitives()
        self.spatial = SpatialUnderstanding()
        self.grasp = GraspPlanner()
        self.traj = TrajectoryPlanner()
    
    def perceive(self, image_path: str, mode: str = "full") -> dict:
        """
        感知图像
        mode: fast(30ms) / standard(200ms) / full(500ms)
        """
        t0 = time.time()
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": f"无法读取: {image_path}"}
        
        h, w = img.shape[:2]
        result = {"path": image_path, "size": (w, h), "success": True}
        
        # P1: 感知
        fast = self.prim.perceive_fast(img)
        result["edge_pixels"] = fast["edge_count"]
        result["corners"] = fast["corners"]
        
        if mode in ("standard", "full"):
            full = self.prim.perceive(img)
            result["contours"] = len(full["contours"])
            result["texture"] = full["texture"]
            result["colors"] = len(full["color_regions"])
            result["contour_details"] = [
                {"area": round(c["area"],0), "circ": round(c["circularity"],2),
                 "ar": round(c["aspect_ratio"],2)}
                for c in full["contours"][:5]
            ]
        
        # P3: 空间
        if mode == "full":
            sp = self.spatial.understand(img)
            result["point_cloud"] = len(sp["points"])
            result["depth_range"] = sp["depth_range"]
            result["ground_plane"] = sp["ground_plane"]
            
            # P4: 抓取
            grasps = self.grasp.plan(img, (w//4, h//4, w//2, h//2))
            result["grasps"] = grasps
        
        result["duration_ms"] = (time.time()-t0)*1000
        return result


# ═══════════════════════════════════════════
# BENCHMARK
# ═══════════════════════════════════════════

def benchmark(image_dir: str):
    p = Path(image_dir)
    exts = ["*.jpg","*.JPG","*.png","*.PNG"]
    files = sorted(set(f for ext in exts for f in p.glob(ext)))
    
    ev = EmbodiedVision()
    
    print(f"{'='*80}")
    print(f"  EMBODIED VISION BENCHMARK v2")
    print(f"  样本: {len(files)}")
    print(f"{'='*80}")
    
    results = []
    for f in files:
        r = ev.perceive(str(f), "full")
        results.append(r)
        name = f.name[:40].ljust(40)
        edge = f"{r.get('edge_pixels',0):>6,}"
        corners = f"{r.get('corners',0):>4}"
        contours = f"{r.get('contours',0):>4}"
        pc = f"{r.get('point_cloud',0):>6,}"
        ms = f"{r.get('duration_ms',0):6.0f}"
        tex = f"std={r.get('texture',{}).get('std',0):.0f}" if 'texture' in r else ""
        print(f"  {name} | 边={edge} 角={corners} 轮={contours} 云={pc} {tex} | {ms}ms")
    
    if results:
        ok = [r for r in results if r.get("success")]
        print(f"\n{'='*80}")
        print(f"  {len(ok)}/{len(results)} 成功")
        print(f"  平均: {sum(r['duration_ms'] for r in ok)/len(ok):.0f}ms")
        print(f"  平均点云: {sum(r.get('point_cloud',0) for r in ok)/len(ok):,.0f}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop"
    benchmark(target)
