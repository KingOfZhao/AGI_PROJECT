#!/usr/bin/env python3
"""
Path B: 展开刀版图照片 → 精确DXF
完整识别pipeline
"""
import cv2, numpy as np, math, json, os

IMG = "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
OUT = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output/verify"
os.makedirs(OUT, exist_ok=True)

# 已知参数
W, L, H = 123.0, 135.0, 46.78
t_w, t_l = 7.55, 9.15
GLUE = 15.0
UW = 2*H + W + GLUE  # 231.56
UH = 2*H + L         # 228.56

X0,X1,X2,X3,X4 = 0, H, H+W, 2*H+W, 2*H+W+GLUE
Y0,Y1,Y2,Y3 = 0, H, H+L, 2*H+L

img = cv2.imread(IMG)
h, w = img.shape[:2]
print(f"图像: {w}×{h}")

# ============================================================
# Stage 1: 透视校正
# ============================================================
print("\n=== Stage 1: 透视校正 ===")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)

binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 21, 10)
kh = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kh, iterations=2)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kv, iterations=2)

contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)

corners = None
for c in contours[:5]:
    area = cv2.contourArea(c)
    if area < img.shape[0] * img.shape[1] * 0.05: continue
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.008 * peri, True)
    if len(approx) == 4:
        corners = np.array(sorted([pt[0] for pt in approx.reshape(-1,2)],
                                  key=lambda p: p[0]+p[1]), dtype=np.float32)
        cw = max(corners[:,0]) - min(corners[:,0])
        ch = max(corners[:,1]) - min(corners[:,1])
        ratio = cw/ch if ch > 0 else 0
        print(f"  四角: {corners.tolist()}, ratio={ratio:.3f} (理论{UW/UH:.3f})")
        break

if corners is None:
    c = contours[0]
    x,y,bw,bh = cv2.boundingRect(c)
    corners = np.array([[x,y],[x+bw,y],[x+bw,y+bh],[x,y+bh]], dtype=np.float32)
    print(f"  外接矩形: {corners.tolist()}")

# 排序: 左上,右上,右下,左下
cx, cy = corners[:,0].mean(), corners[:,1].mean()
ordered = []
for pt in corners:
    if pt[0]<cx and pt[1]<cy: ordered.append(pt)
    elif pt[0]>=cx and pt[1]<cy: ordered.append(pt)
    elif pt[0]>=cx and pt[1]>=cy: ordered.append(pt)
    else: ordered.append(pt)
corners = np.array(ordered, dtype=np.float32)

# 目标: 保持宽高比
target_w = int(UW / 0.18)
target_h = int(UH / 0.18)
dst = np.array([[0,0],[target_w-1,0],[target_w-1,target_h-1],[0,target_h-1]], dtype=np.float32)
M = cv2.getPerspectiveTransform(corners, dst)
warped = cv2.warpPerspective(img, M, (target_w, target_h), flags=cv2.INTER_LANCZOS4)

scale_h = UW / target_w
scale_v = UH / target_h
scale = (scale_h + scale_v) / 2
print(f"  扶正: {target_w}×{target_h}, scale={scale:.4f} mm/px")

cv2.imwrite(f"{OUT}/b1_straightened.png", warped)

# ============================================================
# Stage 2: 多层次边缘提取
# ============================================================
print("\n=== Stage 2: 边缘提取 ===")

gray_w = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
denoised = cv2.bilateralFilter(gray_w, 9, 75, 75)

# Canny多阈值
edges_fine = cv2.Canny(denoised, 20, 60)
edges_med = cv2.Canny(denoised, 30, 100)
edges_coarse = cv2.Canny(denoised, 50, 150)
cv2.imwrite(f"{OUT}/b2_edges_fine.png", edges_fine)

# TopHat提取亮线（刀线通常是亮色/白色）
tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (15,3)))
cv2.imwrite(f"{OUT}/b2_tophat_h.png", tophat)
tophat_v = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3,15)))
cv2.imwrite(f"{OUT}/b2_tophat_v.png", tophat_v)

# 合并: Canny + TopHat
combined = cv2.bitwise_or(edges_fine, cv2.threshold(tophat, 30, 255, cv2.THRESH_BINARY)[1])
combined = cv2.bitwise_or(combined, cv2.threshold(tophat_v, 30, 255, cv2.THRESH_BINARY)[1])
# 形态学连接
kernel = np.ones((2,2), np.uint8)
combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=1)
cv2.imwrite(f"{OUT}/b2_combined.png", combined)

# ============================================================
# Stage 3: Hough线段检测 + 分类
# ============================================================
print("\n=== Stage 3: 线段检测 ===")

def px2mm(x, y):
    return (x * scale, (target_h - y) * scale)

lines_raw = cv2.HoughLinesP(combined, 1, np.pi/180, threshold=25, minLineLength=15, maxLineGap=8)
segments = []
if lines_raw is not None:
    for line in lines_raw:
        x1,y1,x2,y2 = line[0]
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        if length < 10: continue
        na = angle % 180
        if na > 90: na -= 180
        p1m = px2mm(x1, y1)
        p2m = px2mm(x2, y2)
        mm_len = math.hypot(p2m[0]-p1m[0], p2m[1]-p1m[1])
        segments.append({
            'p1': p1m, 'p2': p2m, 'mid': ((p1m[0]+p2m[0])/2, (p1m[1]+p2m[1])/2),
            'length_mm': mm_len, 'length_px': length, 'angle': na,
            'px': (x1,y1,x2,y2)
        })

H_s = [s for s in segments if abs(s['angle'])<8]
V_s = [s for s in segments if abs(abs(s['angle'])-90)<8]
D_s = [s for s in segments if 20<abs(s['angle'])<70]

print(f"  总: {len(segments)}, H:{len(H_s)}, V:{len(V_s)}, D:{len(D_s)}")

# ============================================================
# Stage 4: 合并平行线 + 理论匹配
# ============================================================
print("\n=== Stage 4: 理论匹配 ===")

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

# 理论位置
theory_h = [
    (Y0, "前墙底边"), (Y1, "底板底边/前墙顶"),
    (Y2, "底板顶边/后墙底"), (Y3, "后墙顶边"),
]
theory_v = [
    (X0, "左墙外边"), (X1, "底板左边/前墙右"),
    (X2, "底板右边/右墙左"), (X3, "右墙外边/糊边左"),
    (X4, "糊边右边"),
]

print("  --- 水平线匹配 ---")
h_matched = {}
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
        status = "✓" if best_d < 5 else "≈"
        print(f"  {status} {name}: 理论{theo_y:.2f}, 图像{best['val']:.2f}, Δ={best_d:.2f}mm, L={best['length']:.1f}")
        h_matched[name] = {'theory': theo_y, 'image': best['val'], 'diff': best_d, 'group': best}
    else:
        print(f"  ✗ {name}: 未找到")

print("  --- 垂直线匹配 ---")
v_matched = {}
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
        status = "✓" if best_d < 5 else "≈"
        print(f"  {status} {name}: 理论{theo_x:.2f}, 图像{best['val']:.2f}, Δ={best_d:.2f}mm, L={best['length']:.1f}")
        v_matched[name] = {'theory': theo_x, 'image': best['val'], 'diff': best_d, 'group': best}
    else:
        print(f"  ✗ {name}: 未找到")

# ============================================================
# Stage 5: 对称性分析
# ============================================================
print("\n=== Stage 5: 对称性 ===")

X_MID = X1 + W/2  # 底板中心
Y_MID = Y1 + L/2

# 左右对称（底板区域）
print(f"  对称轴: x={X_MID:.2f}")
asym_lr = []
for g in HG:
    my = g['val']
    if not (Y1-5 < my < Y2+5): continue  # 只检查底板区域
    if g['length'] < 20: continue
    mirror_x = 2*X_MID - (g['xr'][0]+g['xr'][1])/2
    found = False
    for g2 in HG:
        if g2 is g: continue
        g2_cx = (g2['xr'][0]+g2['xr'][1])/2
        if abs(g2_cx - mirror_x) < 5 and abs(g2['val'] - my) < 3:
            found = True
            break
    if not found:
        asym_lr.append(g)
        print(f"  ⚠ H不对称: y={my:.1f} x=[{g['xr'][0]:.0f},{g['xr'][1]:.0f}] L={g['length']:.1f}")

# 上下对称
print(f"  对称轴: y={Y_MID:.2f}")
asym_tb = []
for g in VG:
    mx = g['val']
    if not (X1-5 < mx < X2+5): continue
    if g['length'] < 20: continue
    mirror_y = 2*Y_MID - (g['yr'][0]+g['yr'][1])/2
    found = False
    for g2 in VG:
        if g2 is g: continue
        g2_cy = (g2['yr'][0]+g2['yr'][1])/2
        if abs(g2_cy - mirror_y) < 5 and abs(g2['val'] - mx) < 3:
            found = True
            break
    if not found:
        asym_tb.append(g)
        print(f"  ⚠ V不对称: x={mx:.1f} y=[{g['yr'][0]:.0f},{g['yr'][1]:.0f}] L={g['length']:.1f}")

if not asym_lr: print(f"  ✓ 底板区域左右完全对称")
if not asym_tb: print(f"  ✓ 底板区域上下完全对称")

# ============================================================
# Stage 6: 特征识别（锁扣/防撞翼片/弧度）
# ============================================================
print("\n=== Stage 6: 特征识别 ===")

# 短线 → 锁扣候选
short_h = sorted([s for s in H_s if 5 < s['length_mm'] < 25], key=lambda s: -s['length_mm'])
short_v = sorted([s for s in V_s if 5 < s['length_mm'] < 25], key=lambda s: -s['length_mm'])

print(f"  短H线(锁扣候选): {len(short_h)}")
# 在面板角落附近的短线
corners_mm = [(X1,Y1),(X2,Y1),(X1,Y2),(X2,Y2)]
near_corner_h = []
for s in short_h:
    mx, my = s['mid']
    for cx, cy in corners_mm:
        if math.hypot(mx-cx, my-cy) < 30:
            near_corner_h.append((s, cx, cy))
            break
print(f"  角落附近: {len(near_corner_h)}")
for s, cx, cy in near_corner_h[:15]:
    print(f"    ({s['mid'][0]:.1f},{s['mid'][1]:.1f}) L={s['length_mm']:.1f} θ={s['angle']:.1f}°")

print(f"  短V线(锁扣候选): {len(short_v)}")
near_corner_v = []
for s in short_v:
    mx, my = s['mid']
    for cx, cy in corners_mm:
        if math.hypot(mx-cx, my-cy) < 30:
            near_corner_v.append((s, cx, cy))
            break
print(f"  角落附近: {len(near_corner_v)}")
for s, cx, cy in near_corner_v[:15]:
    print(f"    ({s['mid'][0]:.1f},{s['mid'][1]:.1f}) L={s['length_mm']:.1f} θ={s['angle']:.1f}°")

# 斜线 → 防撞翼片
print(f"\n  45°斜线(防撞翼片): {len(D_s)}")
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
        print(f"  {name}: {len(fs)}条, θ={min(angs):.0f}°~{max(angs):.0f}°, L={min(lens):.1f}~{max(lens):.1f}mm")

# 弧度检测
print(f"\n  弧度检测:")
contours_ext, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
for ci, contour in enumerate(sorted(contours_ext, key=lambda c: -cv2.contourArea(c))[:3]):
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
                    R = min(1/ak*scale, 999) if ak > 0 else 999
                    arcs.append((p1m, p2m, R, len(ap)))
                start = hc[i]
        if arcs:
            print(f"  轮廓#{ci}: {len(arcs)}处弧")
            for j, (p1, p2, R, cnt) in enumerate(arcs):
                if cnt > 5 and R < 200:
                    print(f"    弧{j}: R≈{R:.1f}mm ({p1[0]:.0f},{p1[1]:.0f})→({p2[0]:.0f},{p2[1]:.0f}) pts={cnt}")

# ============================================================
# Stage 7: 叠加可视化
# ============================================================
print("\n=== Stage 7: 可视化 ===")

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

# 理论压线（绿色虚线）
scores = [((X1,Y1),(X2,Y1)), ((X1,Y2),(X2,Y2)),
          ((X1,Y0),(X1,Y3)), ((X2,Y0),(X2,Y3)),
          ((X3,Y0),(X3,Y3))]
for p1, p2 in scores:
    cv2.line(overlay, mm2px(*p1), mm2px(*p2), (0,255,0), 1)

# 对称轴（紫色）
cv2.line(overlay, mm2px(X_MID,-5), mm2px(X_MID,UH+5), (255,0,255), 1)

# 图像检测到的线（黄色半透明）
for s in H_s:
    if s['length_mm'] > 20:
        p1 = mm2px(s['p1'][0], s['p1'][1])
        p2 = mm2px(s['p2'][0], s['p2'][1])
        cv2.line(overlay, p1, p2, (0,255,255), 1)
for s in V_s:
    if s['length_mm'] > 20:
        p1 = mm2px(s['p1'][0], s['p1'][1])
        p2 = mm2px(s['p2'][0], s['p2'][1])
        cv2.line(overlay, p1, p2, (255,255,0), 1)

cv2.imwrite(f"{OUT}/b7_overlay.png", overlay)

# 纯线图（去背景）
line_bg = np.ones_like(warped) * 255
for s in segments:
    if s['length_mm'] > 5:
        p1 = mm2px(s['p1'][0], s['p1'][1])
        p2 = mm2px(s['p2'][0], s['p2'][1])
        if abs(s['angle']) < 8:
            cv2.line(line_bg, p1, p2, (0,0,0), 1)
        elif abs(abs(s['angle'])-90) < 8:
            cv2.line(line_bg, p1, p2, (0,0,0), 1)
        else:
            cv2.line(line_bg, p1, p2, (128,128,128), 1)
cv2.imwrite(f"{OUT}/b7_line_only.png", line_bg)

print(f"  ✓ 叠加图: b7_overlay.png")
print(f"  ✓ 纯线图: b7_line_only.png")
print(f"  红=理论CUT, 绿=理论SCORE, 紫=对称轴, 黄/青=图像检测线")

# ============================================================
# Stage 8: 尺寸校准
# ============================================================
print("\n=== Stage 8: 尺寸校准 ===")

# 用匹配到的线段位置计算实际比例
calib_pairs = []
for name, m in h_matched.items():
    if m['diff'] < 10:
        calib_pairs.append(m)
for name, m in v_matched.items():
    if m['diff'] < 10:
        calib_pairs.append(m)

if calib_pairs:
    avg_diff = sum(c['diff'] for c in calib_pairs) / len(calib_pairs)
    max_diff = max(c['diff'] for c in calib_pairs)
    print(f"  校准点: {len(calib_pairs)}")
    print(f"  平均偏差: {avg_diff:.2f}mm")
    print(f"  最大偏差: {max_diff:.2f}mm")
    
    if max_diff > 3:
        # 尝试重新计算比例
        print(f"  ⚠ 偏差较大，尝试比例修正...")
        # 用实际匹配位置反推比例
        for name, m in h_matched.items():
            if '底板' in name and m['diff'] < 10:
                new_scale_h = (m['image'] - Y0) / (m['theory'] - Y0) * scale if m['theory'] != Y0 else scale
                print(f"    {name}: 比例修正因子 = {new_scale_h/scale:.4f}")

print(f"\n=== 完成 ===")
print(f"所有输出: {OUT}/")
