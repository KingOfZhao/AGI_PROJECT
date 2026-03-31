#!/usr/bin/env python3
"""
刀版图识别推演 v1
从成品盒照片反推展开刀版结构

策略：成品盒是展开图的折叠态，折痕=展开图的压线(SCORE)
      通过识别面之间的折线关系，反推2D展开图布局

图像：成品包装盒照片（非展开图）
目标：识别折痕→反推面板布局→还原展开刀版图
"""
import cv2
import numpy as np
import math
import json
import os

IMG_PATH = "/Users/administruter/Downloads/图像色彩增强结果/图像色彩增强结果.png"
OUT_DIR = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output/verify"
os.makedirs(OUT_DIR, exist_ok=True)

# 已知参数
W, L, H = 123.0, 135.0, 46.78
t_w, t_l = 7.55, 9.15

def analyze(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    results = {}
    
    # ============================================================
    # Stage 1: 多尺度折痕增强
    # 折痕特征：局部亮度突变（亮线或暗线），方向性强
    # ============================================================
    print("=== Stage 1: 折痕增强 ===")
    
    # 1a. CLAHE对比度增强
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    eq = clahe.apply(gray)
    
    # 1b. 双边滤波保边去噪
    denoised = cv2.bilateralFilter(eq, 9, 75, 75)
    
    # 1c. 形态学Top-Hat（检测亮折痕）和Black-Hat（检测暗折痕）
    # 用不同尺度的结构元素
    for ksize in [15, 25, 40]:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
        tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT, kernel)
        blackhat = cv2.morphologyEx(denoised, cv2.MORPH_BLACKHAT, kernel)
        cv2.imwrite(f"{OUT_DIR}/1a_tophat_{ksize}.png", tophat)
        cv2.imwrite(f"{OUT_DIR}/1b_blackhat_{ksize}.png", blackhat)
    
    # 1d. 方向性折痕检测：分别检测0°/45°/90°/135°方向的线
    kernels_dir = {
        'H': cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1)),
        'V': cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25)),
        'D45': cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7)),
        'D135': cv2.getStructuringElement(cv2.MORPH_RECT, (7, 21)),
    }
    
    # 对去噪图做自适应阈值
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 15, 8)
    
    dir_results = {}
    for name, kernel in kernels_dir.items():
        # 用morph open/close增强特定方向
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)
        dir_results[name] = closed
        cv2.imwrite(f"{OUT_DIR}/2_dir_{name}.png", closed)
    
    # 合并所有方向
    combined = np.zeros_like(binary)
    for name, img_dir in dir_results.items():
        combined = cv2.bitwise_or(combined, img_dir)
    cv2.imwrite(f"{OUT_DIR}/2_combined_dirs.png", combined)
    
    # ============================================================
    # Stage 2: 折痕线段提取
    # ============================================================
    print("\n=== Stage 2: 折痕线段提取 ===")
    
    edges = cv2.Canny(denoised, 20, 80)
    cv2.imwrite(f"{OUT_DIR}/3_canny.png", edges)
    
    # Hough线检测
    lines_raw = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=25, 
                                 minLineLength=15, maxLineGap=10)
    
    segments = []
    if lines_raw is not None:
        for line in lines_raw:
            x1,y1,x2,y2 = line[0]
            length = math.hypot(x2-x1, y2-y1)
            angle = math.degrees(math.atan2(y2-y1, x2-x1))
            if length < 10: continue
            na = angle % 180
            if na > 90: na -= 180
            segments.append({
                'p1': (x1,y1), 'p2': (x2,y2),
                'length_px': length, 'length_mm': length,  # 需要scale
                'angle': na, 'angle_raw': angle
            })
    
    # 分类
    H_s = [s for s in segments if abs(s['angle'])<10]
    V_s = [s for s in segments if abs(abs(s['angle'])-90)<10]
    D45 = [s for s in segments if 30<abs(s['angle'])<60]
    D135 = [s for s in segments if -60<abs(s['angle'])<-30]
    
    print(f"  总线段: {len(segments)}")
    print(f"  水平: {len(H_s)}, 垂直: {len(V_s)}")
    print(f"  45°斜: {len(D45)}, 135°斜: {len(D135)}")
    
    # ============================================================
    # Stage 3: 线段合并与聚类
    # ============================================================
    print("\n=== Stage 3: 线段聚类 ===")
    
    def merge_parallel(segs, angle_tol=10, dist_tol=15):
        """合并近似平行且距离相近的线段"""
        if not segs: return []
        # 按角度排序
        sorted_segs = sorted(segs, key=lambda s: s['angle'])
        groups = []
        for s in sorted_segs:
            placed = False
            for g in groups:
                if abs(g['angle'] - s['angle']) < angle_tol:
                    # 检查是否共线（投影距离）
                    dx = s['p2'][0] - s['p1'][0]
                    dy = s['p2'][1] - s['p1'][1]
                    L = math.hypot(dx, dy)
                    if L < 1: continue
                    nx, ny = -dy/L, dx/L  # 法向量
                    
                    # 两线段中点到参考线的距离
                    gmx = (g['p1'][0]+g['p2'][0])/2
                    gmy = (g['p1'][1]+g['p2'][1])/2
                    smx = (s['p1'][0]+s['p2'][0])/2
                    smy = (s['p1'][1]+s['p2'][1])/2
                    
                    dist = abs((smx-gmx)*nx + (smy-gmy)*ny)
                    if dist < dist_tol:
                        # 合并
                        g['segments'].append(s)
                        g['length_px'] = max(g['length_px'], s['length_px'])
                        # 更新包围盒
                        all_pts = [(g['p1'][0],g['p1'][1]),(g['p2'][0],g['p2'][1]),
                                   (s['p1'][0],s['p1'][1]),(s['p2'][0],s['p2'][1])]
                        xs = [p[0] for p in all_pts]
                        ys = [p[1] for p in all_pts]
                        g['p1'] = (min(xs), min(ys))
                        g['p2'] = (max(xs), max(ys))
                        g['angle'] = (g['angle'] * (len(g['segments'])-1) + s['angle']) / len(g['segments'])
                        placed = True
                        break
            if not placed:
                groups.append({
                    'p1': s['p1'], 'p2': s['p2'],
                    'angle': s['angle'],
                    'length_px': s['length_px'],
                    'segments': [s]
                })
        return groups
    
    h_groups = merge_parallel(H_s)
    v_groups = merge_parallel(V_s)
    d45_groups = merge_parallel(D45)
    d135_groups = merge_parallel(D135)
    
    print(f"  H聚类: {len(h_groups)} 组")
    for i, g in enumerate(sorted(h_groups, key=lambda x: -x['length_px'])[:10]):
        my = (g['p1'][1]+g['p2'][1])/2
        print(f"    H#{i}: y≈{my:.0f} L={g['length_px']:.0f}px θ={g['angle']:.1f}° n={len(g['segments'])}")
    
    print(f"  V聚类: {len(v_groups)} 组")
    for i, g in enumerate(sorted(v_groups, key=lambda x: -x['length_px'])[:10]):
        mx = (g['p1'][0]+g['p2'][0])/2
        print(f"    V#{i}: x≈{mx:.0f} L={g['length_px']:.0f}px θ={g['angle']:.1f}° n={len(g['segments'])}")
    
    print(f"  45°聚类: {len(d45_groups)} 组")
    print(f"  135°聚类: {len(d135_groups)} 组")
    
    # ============================================================
    # Stage 4: 面板识别（矩形检测）
    # ============================================================
    print("\n=== Stage 4: 面板识别 ===")
    
    # 在二值图上找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 500: continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) >= 4:
            x, y, bw, bh = cv2.boundingRect(c)
            aspect = bw / bh if bh > 0 else 0
            rects.append({
                'contour': approx,
                'bbox': (x, y, bw, bh),
                'area': area,
                'n_corners': len(approx),
                'aspect': aspect,
                'center': (x + bw/2, y + bh/2)
            })
    
    rects = sorted(rects, key=lambda r: -r['area'])
    print(f"  检测到 {len(rects)} 个矩形区域")
    for i, r in enumerate(rects[:8]):
        x, y, bw, bh = r['bbox']
        print(f"    #{i}: {bw}×{bh}px area={r['area']:.0f} aspect={r['aspect']:.2f} center=({r['center'][0]:.0f},{r['center'][1]:.0f}) corners={r['n_corners']}")
    
    # 在图像上标注面板
    panel_img = img.copy()
    colors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255)]
    for i, r in enumerate(rects[:6]):
        x, y, bw, bh = r['bbox']
        color = colors[i % len(colors)]
        cv2.rectangle(panel_img, (x, y), (x+bw, y+bh), color, 2)
        cv2.putText(panel_img, f"P{i}", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.imwrite(f"{OUT_DIR}/4_panels.png", panel_img)
    
    # ============================================================
    # Stage 5: 折痕线可视化
    # ============================================================
    print("\n=== Stage 5: 折痕可视化 ===")
    
    fold_vis = img.copy()
    # 画聚类后的长线
    for g in h_groups:
        if g['length_px'] > 50:
            cv2.line(fold_vis, g['p1'], g['p2'], (0, 255, 0), 2)
    for g in v_groups:
        if g['length_px'] > 50:
            cv2.line(fold_vis, g['p1'], g['p2'], (0, 255, 0), 2)
    for g in d45_groups:
        if g['length_px'] > 20:
            cv2.line(fold_vis, g['p1'], g['p2'], (255, 165, 0), 2)
    for g in d135_groups:
        if g['length_px'] > 20:
            cv2.line(fold_vis, g['p1'], g['p2'], (255, 165, 0), 2)
    
    cv2.imwrite(f"{OUT_DIR}/5_fold_lines.png", fold_vis)
    
    # 短线（可能是锁扣/小特征）
    short_h = [s for s in H_s if s['length_px'] < 50 and s['length_px'] > 10]
    short_v = [s for s in V_s if s['length_px'] < 50 and s['length_px'] > 10]
    
    feature_vis = img.copy()
    for s in short_h:
        cv2.line(feature_vis, s['p1'], s['p2'], (0, 0, 255), 1)
    for s in short_v:
        cv2.line(feature_vis, s['p1'], s['p2'], (255, 0, 255), 1)
    cv2.imwrite(f"{OUT_DIR}/5b_short_features.png", feature_vis)
    
    print(f"  短水平线(特征): {len(short_h)}")
    print(f"  短垂直线(特征): {len(short_v)}")
    
    # ============================================================
    # Stage 6: 弧度检测
    # ============================================================
    print("\n=== Stage 6: 弧度检测 ===")
    
    contours_ext, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for ci, contour in enumerate(sorted(contours_ext, key=lambda c: -cv2.contourArea(c))[:3]):
        pts = contour.reshape(-1, 2)
        n = len(pts)
        if n < 50: continue
        
        win = 15
        curvatures = []
        for i in range(n):
            pp = pts[(i - win) % n]
            pc = pts[i]
            pn = pts[(i + win) % n]
            
            a1 = math.atan2(pp[1]-pc[1], pp[0]-pc[0])
            a2 = math.atan2(pn[1]-pc[1], pn[0]-pc[0])
            da = a2 - a1
            while da > math.pi: da -= 2*math.pi
            while da < -math.pi: da += 2*math.pi
            ds = math.hypot(pn[0]-pc[0], pn[1]-pc[1])
            curvatures.append(da / ds if ds > 0 else 0)
        
        curvatures = np.array(curvatures)
        threshold = np.percentile(np.abs(curvatures), 95)
        high_curv = np.where(np.abs(curvatures) > threshold)[0]
        
        if len(high_curv) > 5:
            # 聚类连续高曲率区域
            arcs = []
            start = high_curv[0]
            for i in range(1, len(high_curv)):
                if high_curv[i] - high_curv[i-1] > 20:
                    if high_curv[i-1] - start > 5:
                        arc_pts = pts[start:high_curv[i-1]+1]
                        if len(arc_pts) > 5:
                            p1 = tuple(arc_pts[0])
                            p2 = tuple(arc_pts[-1])
                            mean_curv = np.mean(np.abs(curvatures[start:high_curv[i-1]+1]))
                            R = 1.0/mean_curv if mean_curv > 0 else 999
                            arcs.append((p1, p2, R, len(arc_pts)))
                    start = high_curv[i]
            
            if arcs:
                print(f"  轮廓#{ci}: {len(arcs)} 处弧度")
                arc_vis = img.copy()
                for j, (p1, p2, R, cnt) in enumerate(arcs):
                    if cnt > 3 and R < 500:
                        print(f"    弧{j}: R≈{R:.1f}px ({p1[0]},{p1[1]})→({p2[0]},{p2[1]}) pts={cnt}")
                        cv2.circle(arc_vis, p1, 5, (0, 255, 255), -1)
                        cv2.circle(arc_vis, p2, 5, (255, 0, 255), -1)
                cv2.imwrite(f"{OUT_DIR}/6_arcs_{ci}.png", arc_vis)
    
    # ============================================================
    # Stage 7: 对称性分析
    # ============================================================
    print("\n=== Stage 7: 对称性分析 ===")
    
    # 图像中心对称
    cx, cy = w/2, h/2
    
    # 检查水平对称（左右镜像）
    # 取图像左半部分，水平翻转后与右半部分比较
    left = denoised[:, :w//2]
    right_flip = cv2.flip(denoised[:, w//2:], 1)
    
    # 对齐尺寸
    min_w = min(left.shape[1], right_flip.shape[1])
    left_crop = left[:, :min_w]
    right_crop = right_flip[:, :min_w]
    
    # 计算相似度
    diff = cv2.absdiff(left_crop, right_crop)
    similarity = 1.0 - np.mean(diff) / 255.0
    print(f"  左右对称相似度: {similarity:.3f}")
    
    # 检查垂直对称（上下镜像）
    top = denoised[:h//2, :]
    bottom_flip = cv2.flip(denoised[h//2:, :], 0)
    min_h = min(top.shape[0], bottom_flip.shape[0])
    top_crop = top[:min_h, :]
    bottom_crop = bottom_flip[:min_h, :]
    diff_v = cv2.absdiff(top_crop, bottom_crop)
    similarity_v = 1.0 - np.mean(diff_v) / 255.0
    print(f"  上下对称相似度: {similarity_v:.3f}")
    
    # 对称差异图
    sym_h = np.hstack([left_crop, right_crop])
    sym_h_vis = cv2.cvtColor(sym_h, cv2.COLOR_GRAY2BGR)
    cv2.imwrite(f"{OUT_DIR}/7_symmetry_h.png", sym_h_vis)
    
    # ============================================================
    # Stage 8: 识别结果汇总
    # ============================================================
    print("\n=== Stage 8: 识别汇总 ===")
    
    # 尝试识别盒子的可见面板
    # 通过长线段的交点来确定面板边界
    
    # 找长水平线（可能是面板的上下边）
    long_h = sorted([g for g in h_groups if g['length_px'] > w*0.3], 
                    key=lambda g: (g['p1'][1]+g['p2'][1])/2)
    
    print(f"\n  主要水平线(>{w*0.3:.0f}px):")
    for i, g in enumerate(long_h):
        my = (g['p1'][1]+g['p2'][1])/2
        mx = (g['p1'][0]+g['p2'][0])/2
        ratio = g['length_px'] / w
        print(f"    H{i}: y={my:.0f} x=[{g['p1'][0]},{g['p2'][0]}] L={g['length_px']:.0f}px ({ratio:.1%}宽) @({mx:.0f},{my:.0f})")
    
    long_v = sorted([g for g in v_groups if g['length_px'] > h*0.2],
                    key=lambda g: (g['p1'][0]+g['p2'][0])/2)
    
    print(f"\n  主要垂直线(>{h*0.2:.0f}px):")
    for i, g in enumerate(long_v):
        mx = (g['p1'][0]+g['p2'][0])/2
        my = (g['p1'][1]+g['p2'][1])/2
        ratio = g['length_px'] / h
        print(f"    V{i}: x={mx:.0f} y=[{g['p1'][1]},{g['p2'][1]}] L={g['length_px']:.0f}px ({ratio:.1%}高) @({mx:.0f},{my:.0f})")
    
    # ============================================================
    # 输出标注图
    # ============================================================
    final = img.copy()
    
    # 画主要面板线
    for g in long_h[:6]:
        cv2.line(final, g['p1'], g['p2'], (0, 255, 0), 2)
    for g in long_v[:6]:
        cv2.line(final, g['p1'], g['p2'], (255, 0, 0), 2)
    
    # 画短线特征
    for s in short_h[:20]:
        cv2.line(final, s['p1'], s['p2'], (255, 255, 0), 1)
    for s in short_v[:20]:
        cv2.line(final, s['p1'], s['p2'], (0, 255, 255), 1)
    
    # 画斜线（防撞翼片）
    for s in D45[:20]:
        cv2.line(final, s['p1'], s['p2'], (255, 165, 0), 1)
    for s in D135[:20]:
        cv2.line(final, s['p1'], s['p2'], (255, 165, 0), 1)
    
    cv2.imwrite(f"{OUT_DIR}/8_final_analysis.png", final)
    
    # 保存数据
    analysis = {
        'image_size': [w, h],
        'segments': {'total': len(segments), 'H': len(H_s), 'V': len(V_s), 'D45': len(D45), 'D135': len(D135)},
        'clusters': {'H': len(h_groups), 'V': len(v_groups), 'D45': len(d45_groups), 'D135': len(d135_groups)},
        'symmetry': {'horizontal': round(similarity, 3), 'vertical': round(similarity_v, 3)},
        'long_h_lines': [{'y': round((g['p1'][1]+g['p2'][1])/2), 'length': round(g['length_px']), 'n': len(g['segments'])} for g in long_h],
        'long_v_lines': [{'x': round((g['p1'][0]+g['p2'][0])/2), 'length': round(g['length_px']), 'n': len(g['segments'])} for g in long_v],
        'rects': [{'bbox': list(r['bbox']), 'area': round(r['area']), 'aspect': round(r['aspect'], 2)} for r in rects[:8]],
    }
    
    with open(f"{OUT_DIR}/analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== 完成 ===")
    print(f"输出目录: {OUT_DIR}")
    return analysis

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    img = cv2.imread(IMG_PATH)
    if img is None:
        print(f"Error: cannot read {IMG_PATH}")
        exit(1)
    
    print(f"输入: {IMG_PATH}")
    print(f"图像: {img.shape[1]}×{img.shape[0]}")
    print(f"已知盒子: {W}×{L}×{H} mm")
    print()
    
    analysis = analyze(img)
