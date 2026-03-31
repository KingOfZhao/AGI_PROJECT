#!/usr/bin/env python3
"""
网格叠加 + 图像扶正 + 精确比例还原
用于将普通照片转为带标准网格的校准图，辅助刀版还原

用法:
  python3 grid_calibrate.py input.jpg output_dir/ \
    --outer-w 123 --outer-l 135 --inner-w 107.9 --inner-l 116.7 \
    --wall-h 46.78
"""

import cv2
import numpy as np
import math
import argparse
import json
import os
import sys


def detect_document_edges(img):
    """检测文档/展开图的四个角点"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # 去噪 + 增强对比
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 自适应阈值二值化
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 10
    )
    
    # 形态学操作连接断裂线
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v, iterations=2)
    
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    
    # 按面积排序，取最大的
    contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)
    
    for c in contours[:5]:
        area = cv2.contourArea(c)
        img_area = img.shape[0] * img.shape[1]
        if area < img_area * 0.05:
            continue
        
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.01 * peri, True)
        
        if len(approx) == 4:
            corners = approx.reshape(4, 2)
            # 排序: 左上, 右上, 右下, 左下
            corners = order_corners(corners)
            return corners
    
    # 如果找不到四边形，用外接矩形
    c = contours[0]
    x, y, w, h = cv2.boundingRect(c)
    corners = np.array([
        [x, y], [x+w, y], [x+w, y+h], [x, y+h]
    ], dtype=np.float32)
    return corners


def order_corners(corners):
    """将4个角点排序为: 左上, 右上, 右下, 左下"""
    # 计算中心
    center = corners.mean(axis=0)
    
    # 按角度排序
    def angle(p):
        return math.atan2(p[1] - center[1], p[0] - center[0])
    
    sorted_pts = sorted(corners, key=angle)
    # 调整起始点为左上
    # 左上: x小, y小
    result = [None] * 4
    for pt in sorted_pts:
        x, y = pt
        if x < center[0] and y < center[1]:
            result[0] = pt  # 左上
        elif x >= center[0] and y < center[1]:
            result[1] = pt  # 右上
        elif x >= center[0] and y >= center[1]:
            result[2] = pt  # 右下
        else:
            result[3] = pt  # 左下
    
    return np.array(result, dtype=np.float32)


def perspective_correction(img, corners, target_w=None, target_h=None):
    """透视校正"""
    if corners is None:
        return img, None
    
    # 计算目标尺寸
    top_w = math.hypot(corners[1][0]-corners[0][0], corners[1][1]-corners[0][1])
    bot_w = math.hypot(corners[2][0]-corners[3][0], corners[2][1]-corners[3][1])
    left_h = math.hypot(corners[3][0]-corners[0][0], corners[3][1]-corners[0][1])
    right_h = math.hypot(corners[2][0]-corners[1][0], corners[2][1]-corners[1][1])
    
    w = max(int(max(top_w, bot_w)), 100)
    h = max(int(max(left_h, right_h)), 100)
    
    if target_w and target_h:
        w, h = target_w, target_h
    
    dst = np.array([
        [0, 0], [w-1, 0], [w-1, h-1], [0, h-1]
    ], dtype=np.float32)
    
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_LANCZOS4)
    
    return warped, M


def draw_grid(img, grid_mm=10, scale=1.0, color=(200, 200, 200), thick_color=(150, 150, 150)):
    """在图像上绘制标准网格
    
    Args:
        img: 图像
        grid_mm: 网格间距(mm)
        scale: mm/px 比例
        color: 普通网格线颜色
        thick_color: 50mm加粗网格线颜色
    """
    h, w = img.shape[:2]
    grid_px = int(grid_mm / scale)
    if grid_px < 3:
        grid_px = 3
    
    overlay = img.copy()
    
    # 普通网格线
    for x in range(0, w, grid_px):
        c = thick_color if (x * scale) % 50 < grid_mm else color
        cv2.line(overlay, (x, 0), (x, h), c, 1)
    
    for y in range(0, h, grid_px):
        c = thick_color if (y * scale) % 50 < grid_mm else color
        cv2.line(overlay, (0, y), (w, y), c, 1)
    
    # 50mm主网格线(加粗)
    grid50_px = int(50 / scale)
    for x in range(0, w, grid50_px):
        cv2.line(overlay, (x, 0), (x, h), thick_color, 2)
    for y in range(0, h, grid50_px):
        cv2.line(overlay, (0, y), (w, y), thick_color, 2)
    
    # 100mm标注
    grid100_px = int(100 / scale)
    for x in range(0, w, grid100_px):
        mm = int(x * scale)
        cv2.putText(overlay, f"{mm}", (x + 3, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    for y in range(0, h, grid100_px):
        mm = int(y * scale)
        cv2.putText(overlay, f"{mm}", (3, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    
    return overlay


def detect_edges_advanced(img):
    """增强边缘检测: 用于提取刀线"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # CLAHE增强
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 双边滤波保边去噪
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    
    # Canny边缘检测
    edges = cv2.Canny(denoised, 30, 100)
    
    # 形态学连接
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    return edges


def extract_contour_with_grid(edges, scale, origin=(0, 0)):
    """从边缘图提取轮廓并转换为mm坐标
    
    Args:
        edges: 边缘图
        scale: mm/px
        origin: 原点偏移(px)
    
    Returns:
        list of (mm_x, mm_y) tuples
    """
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
    if not contours:
        return []
    
    outer = max(contours, key=lambda c: cv2.contourArea(c))
    peri = cv2.arcLength(outer, True)
    approx = cv2.approxPolyDP(outer, 0.003 * peri, True)
    pts = approx.reshape(-1, 2)
    
    # 转mm坐标 (y翻转: 图像y向下 → mm y向上)
    h = edges.shape[0]
    pts_mm = []
    for x, y in pts:
        mm_x = (x - origin[0]) * scale
        mm_y = (h - 1 - y - origin[1]) * scale
        pts_mm.append((round(mm_x, 2), round(mm_y, 2)))
    
    return pts_mm


def compute_scale_from_dimensions(outer_w, outer_l, inner_w, inner_l, wall_h):
    """从已知尺寸计算展开图的理论尺寸"""
    # 纸厚
    t_w = (outer_w - inner_w) / 2
    t_l = (outer_l - inner_l) / 2
    
    # 展开图理论尺寸 (十字布局)
    unfold_w = 2 * wall_h + outer_w + 15  # 15mm糊边
    unfold_h = 2 * wall_h + outer_l
    
    return {
        't_w': round(t_w, 2),
        't_l': round(t_l, 2),
        'unfold_w': round(unfold_w, 2),
        'unfold_h': round(unfold_h, 2),
        'base_rect': {
            'x': wall_h,
            'y': wall_h,
            'w': outer_w,
            'h': outer_l
        }
    }


def main():
    parser = argparse.ArgumentParser(description='网格校准 + 图像扶正')
    parser.add_argument('input', help='输入图片路径')
    parser.add_argument('output_dir', help='输出目录')
    parser.add_argument('--outer-w', type=float, default=123.0)
    parser.add_argument('--outer-l', type=float, default=135.0)
    parser.add_argument('--inner-w', type=float, default=107.9)
    parser.add_argument('--inner-l', type=float, default=116.7)
    parser.add_argument('--wall-h', type=float, default=46.78)
    parser.add_argument('--grid-mm', type=float, default=10, help='网格间距(mm)')
    parser.add_argument('--no-straighten', action='store_true', help='跳过透视矫正')
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    img = cv2.imread(args.input)
    if img is None:
        print(f"Error: cannot read {args.input}")
        sys.exit(1)
    
    h, w = img.shape[:2]
    print(f"Input: {w}×{h}")
    
    # 计算理论展开图尺寸
    dims = compute_scale_from_dimensions(
        args.outer_w, args.outer_l, args.inner_w, args.inner_l, args.wall_h
    )
    print(f"理论展开图: {dims['unfold_w']}×{dims['unfold_h']} mm")
    print(f"纸厚: t_w={dims['t_w']}, t_l={dims['t_l']}")
    
    # Step 1: 透视矫正
    if not args.no_straighten:
        corners = detect_document_edges(img)
        if corners is not None:
            print(f"检测到四角: {corners.tolist()}")
            
            # 计算目标像素尺寸(保持宽高比)
            aspect = dims['unfold_w'] / dims['unfold_h']
            # 用较长边来设定像素大小
            if w > h:
                target_w = w
                target_h = int(w / aspect)
            else:
                target_h = h
                target_w = int(h * aspect)
            
            straightened, M = perspective_correction(img, corners, target_w, target_h)
            if straightened is not None:
                sh, sw = straightened.shape[:2]
                print(f"扶正后: {sw}×{sh}")
                cv2.imwrite(os.path.join(args.output_dir, '1_straightened.png'), straightened)
                img = straightened
                
                # 比例: 展开图mm / 像素
                scale = dims['unfold_w'] / sw
                # 同时检查垂直比例
                scale_v = dims['unfold_h'] / sh
                print(f"比例: H={scale:.4f} V={scale_v:.4f} mm/px")
            else:
                scale = dims['unfold_w'] / w
                scale_v = dims['unfold_h'] / h
                print(f"Warning: 透视矫正失败, 使用原始比例")
        else:
            scale = dims['unfold_w'] / w
            scale_v = dims['unfold_h'] / h
            print(f"Warning: 未检测到四角, 使用原始比例")
    else:
        scale = dims['unfold_w'] / w
        scale_v = dims['unfold_h'] / h
    
    # Step 2: 边缘检测
    edges = detect_edges_advanced(img)
    cv2.imwrite(os.path.join(args.output_dir, '2_edges.png'), edges)
    
    # Step 3: 网格叠加
    # 使用平均比例
    avg_scale = (scale + scale_v) / 2
    grid_img = draw_grid(img, args.grid_mm, avg_scale)
    cv2.imwrite(os.path.join(args.output_dir, '3_grid_overlay.png'), grid_img)
    
    # 网格叠加在边缘图上
    grid_edges = draw_grid(
        cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR),
        args.grid_mm, avg_scale,
        color=(0, 255, 0), thick_color=(0, 200, 0)
    )
    cv2.imwrite(os.path.join(args.output_dir, '4_grid_edges.png'), grid_edges)
    
    # Step 4: 提取轮廓
    pts_mm = extract_contour_with_grid(edges, avg_scale)
    print(f"\n提取轮廓: {len(pts_mm)} points")
    
    # 分析边
    print("\n=== 轮廓边 ===")
    for i in range(len(pts_mm)):
        p1 = pts_mm[i]
        p2 = pts_mm[(i+1) % len(pts_mm)]
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        length = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))
        if abs(angle) < 5 or abs(abs(angle)-180) < 5: kind = "H"
        elif abs(abs(angle)-90) < 5: kind = "V"
        else: kind = f"D{angle:.0f}"
        print(f"  {i:2d}: L={length:6.1f}mm {kind:5s} ({p1[0]:7.1f},{p1[1]:7.1f})->({p2[0]:7.1f},{p2[1]:7.1f})")
    
    # Step 5: 输出JSON
    result = {
        'dimensions': dims,
        'scale': {'h': round(scale, 4), 'v': round(scale_v, 4), 'avg': round(avg_scale, 4)},
        'contour_mm': pts_mm,
        'base_rect': dims['base_rect'],
        'grid_mm': args.grid_mm
    }
    
    json_path = os.path.join(args.output_dir, 'calibration.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\nOutput:")
    print(f"  1_straightened.png  - 扶正后图像")
    print(f"  2_edges.png         - 边缘检测")
    print(f"  3_grid_overlay.png  - 网格叠加原图")
    print(f"  4_grid_edges.png    - 网格叠加边缘")
    print(f"  calibration.json    - 校准数据(含轮廓mm坐标)")
    print(f"\n比例: {avg_scale:.4f} mm/px (平均)")
    print(f"理论尺寸: {dims['unfold_w']}×{dims['unfold_h']} mm")


if __name__ == '__main__':
    main()
