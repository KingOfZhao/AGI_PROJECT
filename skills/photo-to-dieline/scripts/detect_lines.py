#!/usr/bin/env python3
"""
Line Detection for Box Dielines
Detects cut lines, score lines, and panel structure from a clean scan-like image.

Usage:
    python3 detect_lines.py <clean_image> <output_data.json> [--min-length 30]

Output JSON contains:
  - contours: detected line segments with pixel coords and angles
  - panels: identified rectangular panels
  - scale: pixel-to-mm scale factor (if reference dimension provided)
"""

import sys, os, json, argparse, math
import cv2
import numpy as np

def detect_lines(image_path, min_length=30):
    """Detect all lines in the image."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read {image_path}")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Hough Lines - detect straight line segments
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, 
                            minLineLength=min_length, maxLineGap=10)
    
    if lines is None:
        return {"lines": [], "contours": [], "panels": []}
    
    # Classify lines
    classified = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))
        
        if abs(angle) < 10 or abs(abs(angle) - 180) < 10:
            kind = "H"
        elif abs(abs(angle) - 90) < 10:
            kind = "V"
        else:
            kind = f"D{angle:.0f}"
        
        classified.append({
            "p1": [int(x1), int(y1)],
            "p2": [int(x2), int(y2)],
            "length_px": round(length, 1),
            "angle": round(angle, 1),
            "kind": kind
        })
    
    # Sort by length descending
    classified.sort(key=lambda x: -x["length_px"])
    
    # Detect outer contour
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
    outer_contours = []
    for c in contours:
        area = cv2.contourArea(c)
        if area > 5000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.005 * peri, True)
            pts = approx.reshape(-1, 2).tolist()
            outer_contours.append({
                "area_px": round(area, 0),
                "points": pts,
                "num_points": len(pts)
            })
    
    return {
        "lines": classified[:100],  # top 100 by length
        "contours": outer_contours,
        "image_size": list(img.shape[:2]) if len(img.shape) == 3 else list(gray.shape)
    }

def calibrate_scale(lines_data, known_mm, known_desc=""):
    """Find scale factor from the longest line matching a known dimension."""
    best = None
    for line in lines_data["lines"]:
        if line["kind"] in ("H", "V"):
            ratio = known_mm / line["length_px"]
            if best is None or line["length_px"] > best["px"]:
                best = {"px": line["length_px"], "mm": known_mm, "scale": ratio, "desc": known_desc}
    return best

def identify_panels(lines_data, scale=None):
    """Identify rectangular panels from detected lines."""
    panels = []
    h_lines = sorted([l for l in lines_data["lines"] if l["kind"] == "H"], 
                     key=lambda l: (l["p1"][1], l["p1"][0]))
    v_lines = sorted([l for l in lines_data["lines"] if l["kind"] == "V"], 
                     key=lambda l: (l["p1"][0], l["p1"][1]))
    
    # Group parallel lines
    h_groups = []
    for line in h_lines:
        y = (line["p1"][1] + line["p2"][1]) / 2
        placed = False
        for g in h_groups:
            if abs(g["y"] - y) < 20:
                g["lines"].append(line)
                g["y"] = (g["y"] * (len(g["lines"]) - 1) + y) / len(g["lines"])
                placed = True
                break
        if not placed:
            h_groups.append({"y": y, "lines": [line]})
    
    v_groups = []
    for line in v_lines:
        x = (line["p1"][0] + line["p2"][0]) / 2
        placed = False
        for g in v_groups:
            if abs(g["x"] - x) < 20:
                g["lines"].append(line)
                g["x"] = (g["x"] * (len(g["lines"]) - 1) + x) / len(g["lines"])
                placed = True
                break
        if not placed:
            v_groups.append({"x": x, "lines": [line]})
    
    # Find rectangular intersections
    for i, hg in enumerate(h_groups):
        for j, hgp in enumerate(h_groups[i+1:], i+1):
            for k, vg in enumerate(v_groups):
                for l, vgp in enumerate(v_groups[k+1:], k+1):
                    # Check if these 4 groups form a rectangle
                    w_px = vgp["x"] - vg["x"]
                    h_px = hgp["y"] - hg["y"]
                    if w_px < 30 or h_px < 30:
                        continue
                    
                    w_mm = w_px * scale if scale else w_px
                    h_mm = h_px * scale if scale else h_px
                    
                    panels.append({
                        "bbox_px": [vg["x"], hg["y"], w_px, h_px],
                        "dims_mm": [round(w_mm, 1), round(h_mm, 1)] if scale else None,
                        "role": "unknown"
                    })
    
    return panels

def main():
    parser = argparse.ArgumentParser(description='Detect lines in dieline image')
    parser.add_argument('input', help='Input clean image path')
    parser.add_argument('output', help='Output JSON path')
    parser.add_argument('--min-length', type=int, default=30, help='Minimum line length in pixels')
    parser.add_argument('--calibrate', type=float, help='Known dimension in mm for scale calibration')
    parser.add_argument('--cal-desc', default='', help='Description of calibrated dimension')
    args = parser.parse_args()
    
    data = detect_lines(args.input, args.min_length)
    
    if args.calibrate:
        scale_info = calibrate_scale(data, args.calibrate, args.cal_desc)
        if scale_info:
            data["scale"] = scale_info
            data["panels"] = identify_panels(data, scale_info["scale"])
            print(f"Scale: {scale_info['scale']:.4f} mm/px ({scale_info['desc']})")
    
    # Summary
    h = sum(1 for l in data["lines"] if l["kind"] == "H")
    v = sum(1 for l in data["lines"] if l["kind"] == "V")
    d = sum(1 for l in data["lines"] if l["kind"].startswith("D"))
    print(f"Lines: {h}H + {v}V + {d}D = {len(data['lines'])} total")
    print(f"Contours: {len(data['contours'])}")
    
    with open(args.output, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Output: {args.output}")

if __name__ == '__main__':
    main()
