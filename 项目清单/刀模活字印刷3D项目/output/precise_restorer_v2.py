#!/usr/bin/env python3
"""
图像验证 + 对称性交叉验证
将理论精确DXF与图像轮廓叠加，识别不对称处
"""
import cv2, numpy as np, math, json, os

# 参数
W, L, H = 123.0, 135.0, 46.78
t_w, t_l = 7.55, 9.15
GLUE = 15.0
UNFOLD_W = 2*H + W + GLUE  # 231.56
UNFOLD_H = 2*H + L         # 228.56

X0, X1, X2, X3, X4 = 0, H, H+W, 2*H+W, 2*H+W+GLUE
Y0, Y1, Y2, Y3 = 0, H, H+L, 2*H+L

IMG_PATH = "/Users/administruter/Downloads/图像色彩增强结果/图像色彩增强结果.png"
OUT_DIR = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output"
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    img = cv2.imread(IMG_PATH)
    if img is None:
        print(f"Error: cannot read {IMG_PATH}")
        return
    h, w = img.shape[:2]
    print(f"图像: {w}×{h}")
    
    # 透视校正 — 手动四角（展开图外边界）
    # 增强图显示展开图大约占图像中下部
    # 先用CLAHE增强
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # 检测大矩形（展开图外边界）
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 21, 10)
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_v, iterations=2)
    
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)
    
    # 尝试找到展开图矩形
    target_corners = None
    for c in contours[:5]:
        area = cv2.contourArea(c)
        img_area = img.shape[0] * img.shape[1]
        if area < img_area * 0.05:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.01 * peri, True)
        if len(approx) == 4:
            corners = np.array(sorted([pt[0] for pt in approx.reshape(-1,2)],
                                      key=lambda p: (p[0]+p[1])), dtype=np.float32)
            # 检查宽高比
            cw = max(corners[1][0], corners[2][0]) - min(corners[0][0], corners[3][0])
            ch = max(corners[2][1], corners[3][1]) - min(corners[0][1], corners[1][1])
            ratio = cw/ch if ch > 0 else 0
            expected_ratio = UNFOLD_W / UNFOLD_H  # ~1.013
            if abs(ratio - expected_ratio) < 0.15:
                target_corners = corners
                print(f"检测到展开图矩形: {corners.tolist()}, 宽高比={ratio:.3f}(理论{expected_ratio:.3f})")
                break
    
    if target_corners is None:
        # 用最大轮廓的外接矩形
        c = contours[0]
        x, y, bw, bh = cv2.boundingRect(c)
        target_corners = np.array([
            [x, y], [x+bw, y], [x+bw, y+bh], [x, y+bh]
        ], dtype=np.float32)
        print(f"使用外接矩形: {target_corners.tolist()}")
    
    # 排序角点: 左上,右上,右下,左下
    cx = target_corners[:,0].mean()
    cy = target_corners[:,1].mean()
    ordered = []
    for pt in target_corners:
        if pt[0] < cx and pt[1] < cy: ordered.append(pt)
        elif pt[0] >= cx and pt[1] < cy: ordered.append(pt)
        elif pt[0] >= cx and pt[1] >= cy: ordered.append(pt)
        else: ordered.append(pt)
    target_corners = np.array(ordered, dtype=np.float32)
    
    # 目标像素尺寸
    target_w = int(UNFOLD_W / 0.18)  # ~0.18 mm/px → ~1286px
    target_h = int(UNFOLD_H / 0.18)  # ~1270px
    dst = np.array([
        [0, 0], [target_w-1, 0], [target_w-1, target_h-1], [0, target_h-1]
    ], dtype=np.float32)
    
    M = cv2.getPerspectiveTransform(target_corners, dst)
    warped = cv2.warpPerspective(img, M, (target_w, target_h), flags=cv2.INTER_LANCZOS4)
    
    scale_h = UNFOLD_W / target_w
    scale_v = UNFOLD_H / target_h
    scale = (scale_h + scale_v) / 2
    print(f"扶正后: {target_w}×{target_h}, 比例: {scale:.4f} mm/px")
    
    cv2.imwrite(os.path.join(OUT_DIR, "verify_straightened.png"), warped)
    
    # 边缘检测
    gray_w = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_w, 30, 100)
    cv2.imwrite(os.path.join(OUT_DIR, "verify_edges.png"), edges)
    
    # Hough线检测
    lines_raw = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=20, maxLineGap=8)
    
    def px2mm(x, y):
        return (x * scale, (target_h - y) * scale)
    
    segments = []
    for line in lines_raw:
        x1,y1,x2,y2 = line[0]
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        if length < 15: continue
        na = angle % 180
        if na > 90: na -= 180
        p1m = px2mm(x1, y1)
        p2m = px2mm(x2, y2)
        segments.append({'p1':p1m,'p2':p2m,'length':math.hypot(p2m[0]-p1m[0],p2m[1]-p1m[1]),
            'angle':na})
    
    # 分类
    H_s = [s for s in segments if abs(s['angle'])<8]
    V_s = [s for s in segments if abs(abs(s['angle'])-90)<8]
    D_s = [s for s in segments if 20<abs(s['angle'])<70]
    
    print(f"\n线段: {len(segments)} (H:{len(H_s)} V:{len(V_s)} D:{len(D_s)})")
    
    # === 对称性验证 ===
    # 将所有水平线关于 X_MID_BASE=X1+W/2=108.28 做镜像
    X_MID = X1 + W/2
    Y_MID = Y1 + L/2
    
    print(f"\n=== 左右对称性验证 (对称轴 x={X_MID:.2f}) ===")
    asym_h = []
    for s in H_s:
        mx = (s['p1'][0] + s['p2'][0]) / 2
        my = (s['p1'][1] + s['p2'][1]) / 2
        # 镜像x
        mirror_x = 2*X_MID - mx
        # 查找匹配线
        found = False
        for s2 in H_s:
            mx2 = (s2['p1'][0] + s2['p2'][0]) / 2
            my2 = (s2['p1'][1] + s2['p2'][1]) / 2
            if abs(mx2 - mirror_x) < 5 and abs(my2 - my) < 5:
                found = True
                break
        if not found and s['length'] > 20:
            # 检查是否在底板区域（应该对称的区域）
            if X1-10 < mx < X2+10:
                asym_h.append({'seg': s, 'mirror_x': mirror_x})
    
    if asym_h:
        print(f"  ⚠ 底板区域不对称: {len(asym_h)} 条")
        for a in asym_h[:10]:
            s = a['seg']
            mx = (s['p1'][0]+s['p2'][0])/2
            my = (s['p1'][1]+s['p2'][1])/2
            print(f"    y={my:.1f} x=[{s['p1'][0]:.0f},{s['p2'][0]:.0f}] L={s['length']:.1f} → 镜像应在x≈{a['mirror_x']:.1f}")
    else:
        print(f"  ✓ 底板区域水平线完全对称")
    
    print(f"\n=== 上下对称性验证 (对称轴 y={Y_MID:.2f}) ===")
    asym_v = []
    for s in V_s:
        mx = (s['p1'][0] + s['p2'][0]) / 2
        my = (s['p1'][1] + s['p2'][1]) / 2
        mirror_y = 2*Y_MID - my
        found = False
        for s2 in V_s:
            mx2 = (s2['p1'][0] + s2['p2'][0]) / 2
            my2 = (s2['p1'][1] + s2['p2'][1]) / 2
            if abs(my2 - mirror_y) < 5 and abs(mx2 - mx) < 5:
                found = True
                break
        if not found and s['length'] > 20:
            if Y1-10 < my < Y2+10:
                asym_v.append({'seg': s, 'mirror_y': mirror_y})
    
    if asym_v:
        print(f"  ⚠ 底板区域不对称: {len(asym_v)} 条")
        for a in asym_v[:10]:
            s = a['seg']
            mx = (s['p1'][0]+s['p2'][0])/2
            my = (s['p1'][1]+s['p2'][1])/2
            print(f"    x={mx:.1f} y=[{s['p1'][1]:.0f},{s['p2'][1]:.0f}] L={s['length']:.1f} → 镜像应在y≈{a['mirror_y']:.1f}")
    else:
        print(f"  ✓ 底板区域垂直线完全对称")
    
    # === 斜线 → 防撞翼片分析 ===
    print(f"\n=== 45°斜线分析 ===")
    flap_regions = {
        '前墙下方': lambda s: s['p1'][1]<Y1 and X1<s['p1'][0]<X2,
        '后墙上方': lambda s: s['p1'][1]>Y2 and X1<s['p1'][0]<X2,
        '左墙左方': lambda s: s['p1'][0]<X1 and Y1<s['p1'][1]<Y2,
        '右墙右方': lambda s: s['p1'][0]>X2 and Y1<s['p1'][1]<Y2,
    }
    for name, test in flap_regions.items():
        rs = [s for s in D_s if test(s)]
        if rs:
            angs = [s['angle'] for s in rs]
            lens = [s['length'] for s in rs]
            print(f"  {name}: {len(rs)}条, 角度{min(angs):.0f}°~{max(angs):.0f}°, 长{min(lens):.1f}~{max(lens):.1f}mm")
            
            # 对称验证：前后墙的斜线应镜像
            if name == '前墙下方':
                mirror_name = '后墙上方'
                mirror_test = flap_regions[mirror_name]
                rs_mirror = [s for s in D_s if mirror_test(s)]
                print(f"    对比{mirror_name}: {len(rs_mirror)}条 → {'对称✓' if abs(len(rs)-len(rs_mirror))<=1 else '不对称⚠'}")
    
    # === 理论 vs 图像压线对比 ===
    print(f"\n=== 压线理论 vs 图像 ===")
    theoretical_scores = {
        '底板底边 y=46.78': Y1,
        '底板顶边 y=181.78': Y2,
        '底板左边 x=46.78': X1,
        '底板右边 x=169.78': X2,
        '糊边线 x=216.56': X3,
    }
    
    for name, theo in theoretical_scores.items():
        if 'y=' in name:
            axis = 1
            pool = H_s
        else:
            axis = 0
            pool = V_s
        
        best = None
        best_diff = 999
        for s in pool:
            mid = (s['p1'][axis] + s['p2'][axis]) / 2
            diff = abs(mid - theo)
            if diff < best_diff and s['length'] > 30:
                best_diff = diff
                best = s
        
        if best:
            mid = (best['p1'][axis] + best['p2'][axis]) / 2
            status = "✓" if best_diff < 3 else "⚠"
            print(f"  {status} {name}: 理论{theo:.2f}, 图像{mid:.2f}, 偏差{best_diff:.2f}mm, 长度{best['length']:.1f}mm")
        else:
            print(f"  ✗ {name}: 未找到匹配线")
    
    # === 叠加可视化 ===
    overlay = warped.copy()
    wh, ww = warped.shape[:2]
    
    def mm2px(x, y):
        return (int(x/scale), int(wh - y/scale))
    
    # 画理论轮廓（红色）
    theory_cut = [
        ((X0,Y1),(X0,Y0)), ((X0,Y0),(X1,Y0)), ((X1,Y0),(X2,Y0)),
        ((X2,Y0),(X2,Y1)), ((X2,Y1),(X3,Y1)), ((X3,Y1),(X3,Y3)),
        ((X3,Y3),(X2,Y3)), ((X2,Y3),(X1,Y3)), ((X1,Y3),(X0,Y3)),
        ((X0,Y3),(X0,Y2)), ((X0,Y2),(X1,Y2)), ((X1,Y2),(X2,Y2)),
        ((X2,Y2),(X3,Y2)), ((X3,Y2),(X3,Y1)),
        ((X3,Y0),(X4,Y0)), ((X4,Y0),(X4,Y3)), ((X4,Y3),(X3,Y3)),
    ]
    for p1, p2 in theory_cut:
        px1 = mm2px(*p1)
        px2 = mm2px(*p2)
        cv2.line(overlay, px1, px2, (0, 0, 255), 2)
    
    # 画压线（绿色虚线）
    score_lines = [
        ((X1,Y1),(X2,Y1)), ((X1,Y2),(X2,Y2)),
        ((X1,Y0),(X1,Y3)), ((X2,Y0),(X2,Y3)),
        ((X3,Y0),(X3,Y3)),
    ]
    for p1, p2 in score_lines:
        px1 = mm2px(*p1)
        px2 = mm2px(*p2)
        # 画虚线
        cv2.line(overlay, px1, px2, (0, 255, 0), 1, cv2.LINE_AA)
    
    # 画对称轴（紫色）
    px_mid = mm2px(X_MID, Y_MID)
    cv2.line(overlay, mm2px(X_MID, -5), mm2px(X_MID, UNFOLD_H+5), (255, 0, 255), 1, cv2.LINE_AA)
    
    cv2.imwrite(os.path.join(OUT_DIR, "verify_overlay.png"), overlay)
    print(f"\n✓ 叠加图: {OUT_DIR}/verify_overlay.png")
    print(f"  红色=理论CUT轮廓, 绿色=理论压线, 紫色=对称轴")

if __name__ == '__main__':
    main()
