#!/usr/bin/env python3
"""
Path B v2: 精确角点定位 + 透视校正 + 结构识别
修正v1的问题：四角检测框住了整个图像而非刀版图区域
"""
import cv2, numpy as np, math, json, os

IMG = "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
OUT = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output/verify"
os.makedirs(OUT, exist_ok=True)

W, L, H = 123.0, 135.0, 46.78
t_w, t_l = 7.55, 9.15
GLUE = 15.0
UW = 2*H + W + GLUE  # 231.56
UH = 2*H + L         # 228.56

img = cv2.imread(IMG)
h, w = img.shape[:2]
print(f"图像: {w}×{h}")

# ============================================================
# Step 1: 定位刀版图区域（图像下半部分）
# ============================================================
print("\n=== Step 1: 刀版图区域定位 ===")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 刀版图区域的特征：大量直线，规则网格状
# 用边缘密度来定位
edges_full = cv2.Canny(gray, 30, 100)

# 计算每行的边缘密度
row_density = np.sum(edges_full, axis=1) / 255.0
col_density = np.sum(edges_full, axis=0) / 255.0

# 找刀版图区域的上下边界（边缘密度突然增大的位置）
# 刀版图从大约 y=700 开始
threshold = np.max(row_density) * 0.3
active_rows = np.where(row_density > threshold)[0]
if len(active_rows) > 0:
    y_top = max(0, active_rows[0] - 20)
    y_bot = min(h-1, active_rows[-1] + 20)
else:
    y_top, y_bot = h//2, h-1

# 左右边界
threshold_x = np.max(col_density) * 0.3
active_cols = np.where(col_density > threshold)[0]
if len(active_cols) > 0:
    x_left = max(0, active_cols[0] - 20)
    x_right = min(w-1, active_cols[-1] + 20)
else:
    x_left, x_right = 0, w-1

print(f"  刀版图区域: x=[{x_left},{x_right}], y=[{y_top},{y_bot}]")
print(f"  区域尺寸: {x_right-x_left}×{y_bot-y_top}")

# 裁剪到刀版图区域
roi = img[y_top:y_bot, x_left:x_right].copy()
roi_gray = gray[y_top:y_bot, x_left:x_right].copy()
roi_h, roi_w = roi.shape[:2]
print(f"  ROI: {roi_w}×{roi_h}")

# 宽高比检查
roi_ratio = roi_w / roi_h
theory_ratio = UW / UH
print(f"  ROI宽高比: {roi_ratio:.3f} (理论: {theory_ratio:.3f})")

cv2.imwrite(f"{OUT}/c1_roi.png", roi)

# ============================================================
# Step 2: 在ROI内检测精确四角
# ============================================================
print("\n=== Step 2: 精确四角检测 ===")

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
enhanced = clahe.apply(roi_gray)

binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 21, 10)
kh = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kh, iterations=2)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kv, iterations=2)

contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)

best_corners = None
best_score = 999
for c in contours[:10]:
    area = cv2.contourArea(c)
    roi_area = roi_w * roi_h
    if area < roi_area * 0.3: continue
    peri = cv2.arcLength(c, True)
    
    # 用不同精度尝试
    for epsilon_factor in [0.005, 0.008, 0.01, 0.015, 0.02]:
        approx = cv2.approxPolyDP(c, epsilon_factor * peri, True)
        if len(approx) != 4: continue
        
        pts = sorted([pt[0] for pt in approx.reshape(-1,2)], key=lambda p: p[0]+p[1])
        cw = max(pts[:,0]) - min(pts[:,0])
        ch = max(pts[:,1]) - min(pts[:,1])
        ratio = cw/ch if ch > 0 else 0
        score = abs(ratio - theory_ratio)
        
        if score < best_score:
            best_score = score
            best_corners = np.array(pts, dtype=np.float32)
            print(f"  ε={epsilon_factor}: corners={pts.tolist()}, ratio={ratio:.3f}, score={score:.4f}")

if best_corners is None:
    # fallback: 外接矩形
    c = contours[0]
    x, y, bw, bh = cv2.boundingRect(c)
    best_corners = np.array([[x,y],[x+bw,y],[x+bw,y+bh],[x,y+bh]], dtype=np.float32)
    print(f"  Fallback: bounding rect")

# 排序: 左上, 右上, 右下, 左下
cx_c = best_corners[:,0].mean()
cy_c = best_corners[:,1].mean()
ordered = []
for pt in best_corners:
    if pt[0]<cx_c and pt[1]<cy_c: ordered.append(pt)
    elif pt[0]>=cx_c and pt[1]<cy_c: ordered.append(pt)
    elif pt[0]>=cx_c and pt[1]>=cy_c: ordered.append(pt)
    else: ordered.append(pt)
corners = np.array(ordered, dtype=np.float32)
print(f"  排序后: {corners.tolist()}")

# 在ROI图上标注角点
corner_vis = roi.copy()
for i, pt in enumerate(corners):
    cv2.circle(corner_vis, (int(pt[0]), int(pt[1])), 10, (0,255,0), -1)
    cv2.putText(corner_vis, str(i), (int(pt[0])+12, int(pt[1])+5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
cv2.imwrite(f"{OUT}/c2_corners.png", corner_vis)

# ============================================================
# Step 3: 透视校正
# ============================================================
print("\n=== Step 3: 透视校正 ===")

# 目标尺寸：保持理论宽高比
target_w = 1400
target_h = int(target_w / theory_ratio)
dst = np.array([[0,0],[target_w-1,0],[target_w-1,target_h-1],[0,target_h-1]], dtype=np.float32)

M = cv2.getPerspectiveTransform(corners, dst)
warped = cv2.warpPerspective(roi, M, (target_w, target_h), flags=cv2.INTER_LANCZOS4)

scale = UW / target_w
print(f"  目标: {target_w}×{target_h}")
print(f"  比例: {scale:.4f} mm/px")
cv2.imwrite(f"{OUT}/c3_warped.png", warped)

# ============================================================
# Step 4: 多层次边缘提取
# ============================================================
print("\n=== Step 4: 边缘提取 ===")

gray_w = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
denoised = cv2.bilateralFilter(gray_w, 9, 75, 75)

# Canny
edges = cv2.Canny(denoised, 20, 80)

# TopHat提取亮线（刀线通常是红色/亮色线条）
tophat_h = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (21,3)))
tophat_v = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3,21)))

# HSV提取红色刀线
hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
# 红色在HSV中有两个范围
mask_r1 = cv2.inRange(hsv, np.array([0,50,50]), np.array([10,255,255]))
mask_r2 = cv2.inRange(hsv, np.array([170,50,50]), np.array([180,255,255]))
red_mask = cv2.bitwise_or(mask_r1, mask_r2)
cv2.imwrite(f"{OUT}/c4_red_mask.png", red_mask)

# 合并所有边缘源
combined = cv2.bitwise_or(edges, cv2.threshold(tophat_h, 25, 255, cv2.THRESH_BINARY)[1])
combined = cv2.bitwise_or(combined, cv2.threshold(tophat_v, 25, 255, cv2.THRESH_BINARY)[1])
combined = cv2.bitwise_or(combined, red_mask)
# 形态学清理
kernel = np.ones((2,2), np.uint8)
combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=1)
cv2.imwrite(f"{OUT}/c4_combined.png", combined)
cv2.imwrite(f"{OUT}/c4_edges.png", edges)

# ============================================================
# Step 5: Hough线段 + 分类
# ============================================================
print("\n=== Step 5: 线段检测 ===")

def px2mm(x, y):
    return (x * scale, (target_h - y) * scale)

lines_raw = cv2.HoughLinesP(combined, 1, np.pi/180, threshold=25, minLineLength=15, maxLineGap=8)
segments = []
if lines_raw is not None:
    for line in lines_raw:
        x1,y1,x2,y2 = line[0]
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        if length < 8: continue
        na = angle % 180
        if na > 90: na -= 180
        p1m = px2mm(x1, y1)
        p2m = px2mm(x2, y2)
        mm_len = math.hypot(p2m[0]-p1m[0], p2m[1]-p1m[1])
        segments.append({
            'p1': p1m, 'p2': p2m, 
            'mid': ((p1m[0]+p2m[0])/2, (p1m[1]+p2m[1])/2),
            'length_mm': mm_len, 'length_px': length, 'angle': na,
            'px': (x1,y1,x2,y2)
        })

H_s = [s for s in segments if abs(s['angle'])<8]
V_s = [s for s in segments if abs(abs(s['angle'])-90)<8]
D_s = [s for s in segments if 20<abs(s['angle'])<70]

print(f"  总: {len(segments)}, H:{len(H_s)}, V:{len(V_s)}, D:{len(D_s)}")

# ============================================================
# Step 6: 合并 + 理论匹配
# ============================================================
print("\n=== Step 6: 理论匹配 ===")

def merge_lines(segs, axis, tol=3.0):
    groups = []
    for s in segs:
        val = s['mid'][axis]
        placed = False
        for g in groups:
            if abs(g['val'] - val) < tol:
                g['segs'].append(s)
                g['val'] = sum(s2['mid'][axis] for s2 in g['segs'])/len(g['segs'])
                g['length'] = max(g['length'], s['length_mm'])
                all_x = [x for s2 in g['segs'] for x in (s2['p1'][0], s2['p2'][0])]
                all_y = [y for s2 in g['segs'] for y in (s2['p1'][1], s2['p2'][1])]
                g['xr'] = (min(all_x), max(all_x))
                g['yr'] = (min(all_y), max(all_y))
                placed = True
                break
        if not placed:
            groups.append({
                'val': val, 'segs': [s], 'length': s['length_mm'],
                'xr': (min(s['p1'][0],s['p2'][0]), max(s['p1'][0],s['p2'][0])),
                'yr': (min(s['p1'][1],s['p2'][1]), max(s['p1'][1],s['p2'][1]))
            })
    return groups

HG = merge_lines(H_s, 1)
VG = merge_lines(V_s, 0)

X0,X1,X2,X3,X4 = 0, H, H+W, 2*H+W, 2*H+W+GLUE
Y0,Y1,Y2,Y3 = 0, H, H+L, 2*H+L

theory_h = [(Y0,"前墙底"),(Y1,"底板底/前墙顶"),(Y2,"底板顶/后墙底"),(Y3,"后墙顶")]
theory_v = [(X0,"左墙外"),(X1,"底板左"),(X2,"底板右"),(X3,"右墙外"),(X4,"糊边右")]

h_matched = {}
print("  水平线:")
for theo_y, name in theory_h:
    best = None
    best_d = 999
    for g in HG:
        if g['length'] > 30:
            d = abs(g['val'] - theo_y)
            if d < best_d:
                best_d = d
                best = g
    if best:
        status = "✓" if best_d < 3 else ("≈" if best_d < 8 else "✗")
        print(f"  {status} {name}: 理论{theo_y:.2f} 图像{best['val']:.2f} Δ={best_d:.2f} L={best['length']:.1f}")
        h_matched[name] = {'theory': theo_y, 'image': best['val'], 'diff': best_d}
    else:
        print(f"  ✗ {name}: 未找到")

v_matched = {}
print("  垂直线:")
for theo_x, name in theory_v:
    best = None
    best_d = 999
    for g in VG:
        if g['length'] > 30:
            d = abs(g['val'] - theo_x)
            if d < best_d:
                best_d = d
                best = g
    if best:
        status = "✓" if best_d < 3 else ("≈" if best_d < 8 else "✗")
        print(f"  {status} {name}: 理论{theo_x:.2f} 图像{best['val']:.2f} Δ={best_d:.2f} L={best['length']:.1f}")
        v_matched[name] = {'theory': theo_x, 'image': best['val'], 'diff': best_d}
    else:
        print(f"  ✗ {name}: 未找到")

# ============================================================
# Step 7: 对称性
# ============================================================
print("\n=== Step 7: 对称性 ===")
X_MID = X1 + W/2
Y_MID = Y1 + L/2

# 底板区域水平线对称
asym = 0
for g in HG:
    my = g['val']
    if not (Y1-3 < my < Y2+3): continue
    if g['length'] < 15: continue
    g_cx = (g['xr'][0]+g['xr'][1])/2
    mirror_cx = 2*X_MID - g_cx
    found = any(abs((g2['xr'][0]+g2['xr'][1])/2 - mirror_cx) < 5 and 
                abs(g2['val'] - my) < 3 for g2 in HG if g2 is not g)
    if not found:
        asym += 1
        print(f"  ⚠ H不对称: y={my:.1f} cx={g_cx:.0f} L={g['length']:.1f} 镜像应在cx≈{mirror_cx:.0f}")

if asym == 0:
    print(f"  ✓ 底板区域H线完全对称")

# 底板区域垂直线对称
asym_v = 0
for g in VG:
    mx = g['val']
    if not (X1-3 < mx < X2+3): continue
    if g['length'] < 15: continue
    g_cy = (g['yr'][0]+g['yr'][1])/2
    mirror_cy = 2*Y_MID - g_cy
    found = any(abs((g2['yr'][0]+g2['yr'][1])/2 - mirror_cy) < 5 and 
                abs(g2['val'] - mx) < 3 for g2 in VG if g2 is not g)
    if not found:
        asym_v += 1
        print(f"  ⚠ V不对称: x={mx:.1f} cy={g_cy:.0f} L={g['length']:.1f} 镜像应在cy≈{mirror_cy:.0f}")

if asym_v == 0:
    print(f"  ✓ 底板区域V线完全对称")

# ============================================================
# Step 8: 特征识别
# ============================================================
print("\n=== Step 8: 特征识别 ===")

# 防撞翼片斜线
flap_zones = {
    '前墙下方': lambda s: s['mid'][1] < Y1-2 and X1-5 < s['mid'][0] < X2+5,
    '后墙上方': lambda s: s['mid'][1] > Y2+2 and X1-5 < s['mid'][0] < X2+5,
    '左墙左方': lambda s: s['mid'][0] < X1-2 and Y1-5 < s['mid'][1] < Y2+5,
    '右墙右方': lambda s: s['mid'][0] > X2+2 and Y1-5 < s['mid'][1] < Y2+5,
}
for name, test in flap_zones.items():
    fs = [s for s in D_s if test(s)]
    if fs:
        angs = [s['angle'] for s in fs]
        lens = [s['length_mm'] for s in fs]
        print(f"  {name}: {len(fs)}条 θ={min(angs):.0f}°~{max(angs):.0f}° L={min(lens):.1f}~{max(lens):.1f}mm")
        
        # 对称验证
        mirror_name = {'前墙下方':'后墙上方','后墙上方':'前墙下方',
                       '左墙左方':'右墙右方','右墙右方':'左墙左方'}[name]
        mirror_fs = [s for s in D_s if flap_zones[mirror_name](s)]
        diff_count = abs(len(fs) - len(mirror_fs))
        sym_status = "✓" if diff_count <= 2 else f"⚠ 差{diff_count}条"
        print(f"    vs {mirror_name}: {len(mirror_fs)}条 {sym_status}")

# 锁扣候选（角落附近的短线）
corners_mm = [(X1,Y1),(X2,Y1),(X1,Y2),(X2,Y2)]
print(f"\n  角落附近短线:")
for cx, cy in corners_mm:
    name = f"({cx:.0f},{cy:.0f})"
    near = [s for s in segments if math.hypot(s['mid'][0]-cx, s['mid'][1]-cy) < 25 
            and 5 < s['length_mm'] < 30]
    if near:
        print(f"  {name}: {len(near)}条")
        for s in near[:5]:
            print(f"    L={s['length_mm']:.1f} θ={s['angle']:.1f}° @({s['mid'][0]:.0f},{s['mid'][1]:.0f})")

# 弧度
print(f"\n  弧度检测:")
contours_ext, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
for ci, contour in enumerate(sorted(contours_ext, key=lambda c: -cv2.contourArea(c))[:5]):
    pts = contour.reshape(-1, 2)
    n = len(pts)
    if n < 100: continue
    win = 15
    curvs = []
    for i in range(n):
        pp, pc, pn = pts[(i-win)%n], pts[i], pts[(i+win)%n]
        a1 = math.atan2(pp[1]-pc[1], pp[0]-pc[0])
        a2 = math.atan2(pn[1]-pc[1], pn[0]-pc[0])
        da = a2-a1
        while da>math.pi: da-=2*math.pi
        while da<-math.pi: da+=2*math.pi
        ds = math.hypot(pn[0]-pc[0], pn[1]-pc[1])
        curvs.append(da/ds if ds>0 else 0)
    curvs = np.array(curvs)
    thresh = np.percentile(np.abs(curvs), 97)
    hc = np.where(np.abs(curvs) > thresh)[0]
    if len(hc) > 10:
        arcs = []
        start = hc[0]
        for i in range(1, len(hc)):
            if hc[i] - hc[i-1] > 15:
                if hc[i-1] - start > 8:
                    ap = pts[start:hc[i-1]+1]
                    p1m = px2mm(*ap[0])
                    p2m = px2mm(*ap[-1])
                    ak = np.mean(np.abs(curvs[start:hc[i-1]+1]))
                    R = 1.0/(ak*scale) if ak > 0 else 999
                    arcs.append((p1m, p2m, R, len(ap)))
                start = hc[i]
        if arcs:
            print(f"  轮廓#{ci}: {len(arcs)}处弧")
            for j, (p1, p2, R, cnt) in enumerate(arcs):
                if cnt > 5 and R < 100:
                    print(f"    弧{j}: R≈{R:.1f}mm ({p1[0]:.0f},{p1[1]:.0f})→({p2[0]:.0f},{p2[1]:.0f}) pts={cnt}")

# ============================================================
# Step 9: 叠加可视化
# ============================================================
print("\n=== Step 9: 可视化 ===")

def mm2px(x, y):
    return (int(x/scale), int(target_h - y/scale))

overlay = warped.copy()

# 理论外轮廓（红色）
theory_cut = [
    ((X0,Y1),(X0,Y0)), ((X0,Y0),(X1,Y0)), ((X1,Y0),(X2,Y0)),
    ((X2,Y0),(X2,Y1)), ((X2,Y1),(X3,Y1)), ((X3,Y1),(X3,Y3)),
    ((X3,Y3),(X2,Y3)), ((X2,Y3),(X1,Y3)), ((X1,Y3),(X0,Y3)),
    ((X0,Y3),(X0,Y2)), ((X0,Y2),(X1,Y2)), ((X1,Y2),(X2,Y2)),
    ((X2,Y2),(X3,Y2)),
    ((X3,Y0),(X4,Y0)), ((X4,Y0),(X4,Y3)), ((X4,Y3),(X3,Y3)),
]
for p1, p2 in theory_cut:
    cv2.line(overlay, mm2px(*p1), mm2px(*p2), (0,0,255), 2)

# 理论压线（绿色）
scores = [((X1,Y1),(X2,Y1)), ((X1,Y2),(X2,Y2)),
          ((X1,Y0),(X1,Y3)), ((X2,Y0),(X2,Y3)),
          ((X3,Y0),(X3,Y3))]
for p1, p2 in scores:
    cv2.line(overlay, mm2px(*p1), mm2px(*p2), (0,255,0), 1)

# 对称轴（紫色）
cv2.line(overlay, mm2px(X_MID,-5), mm2px(X_MID,UH+5), (255,0,255), 1)

# 图像检测到的线
for s in H_s:
    if s['length_mm'] > 15:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (0,255,255), 1)
for s in V_s:
    if s['length_mm'] > 15:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,255,0), 1)
for s in D_s:
    if s['length_mm'] > 8:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,165,0), 1)

cv2.imwrite(f"{OUT}/c9_overlay.png", overlay)

# 纯线图
line_bg = np.ones_like(warped) * 255
for s in segments:
    if s['length_mm'] > 3:
        p1 = mm2px(*s['p1'])
        p2 = mm2px(*s['p2'])
        if abs(s['angle']) < 8 or abs(abs(s['angle'])-90) < 8:
            cv2.line(line_bg, p1, p2, (0,0,0), 1)
        else:
            cv2.line(line_bg, p1, p2, (100,100,100), 1)
cv2.imwrite(f"{OUT}/c9_lines.png", line_bg)

print(f"  ✓ 叠加: c9_overlay.png")
print(f"  ✓ 纯线: c9_lines.png")
print(f"  红=理论CUT 绿=理论SCORE 紫=对称轴 青=检测H 黄=检测V 橙=检测斜线")

# ============================================================
# Step 10: 总结
# ============================================================
print("\n=== 总结 ===")
all_diffs = [m['diff'] for m in list(h_matched.values()) + list(v_matched.values())]
avg_d = sum(all_diffs)/len(all_diffs) if all_diffs else 0
max_d = max(all_diffs) if all_diffs else 0
print(f"  匹配线: {len(all_diffs)}条")
print(f"  平均偏差: {avg_d:.2f}mm")
print(f"  最大偏差: {max_d:.2f}mm")
if max_d < 3:
    print(f"  ✓ 比例精确，可进行像素级验证")
elif max_d < 8:
    print(f"  ≈ 比例可用，建议微调")
else:
    print(f"  ⚠ 偏差较大，需要手动校准角点")
