#!/usr/bin/env python3
"""
Path B v3: 基于精确轮廓角点的透视校正 + 完整结构识别
用17角轮廓定义展开图边界，透视校正后提取所有内部元素
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
X0,X1,X2,X3,X4 = 0, H, H+W, 2*H+W, 2*H+W+GLUE
Y0,Y1,Y2,Y3 = 0, H, H+L, 2*H+L

img = cv2.imread(IMG)
h, w = img.shape[:2]

# ============================================================
# Step 1: 提取精确轮廓角点
# ============================================================
print("=== Step 1: 轮廓提取 ===")

roi = img[700:1500, 100:1200].copy()
gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray_roi)

binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 15, 5)
kh = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kh, iterations=3)
binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kv, iterations=3)

contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=lambda c: cv2.contourArea(c), reverse=True)

peri = cv2.arcLength(contours[0], True)
approx = cv2.approxPolyDP(contours[0], 0.01*peri, True)
pts = approx.reshape(-1, 2).astype(np.float32)
print(f"轮廓角点: {len(pts)}")

# 转原图坐标
pts_orig = pts.copy()
pts_orig[:,0] += 100
pts_orig[:,1] += 700

# ============================================================
# Step 2: 理论角点映射
# ============================================================
print("\n=== Step 2: 角点-理论映射 ===")

# 理论展开图外轮廓（简化版，不含防撞翼片锯齿）
# 顺时针从(X0,Y0)开始
theory_simple = np.array([
    [X0, Y0], [X1, Y0], [X2, Y0],           # 前墙底边
    [X2, Y1],                                  # 右前角
    [X3, Y1],                                  # 右墙底
    [X3, Y3],                                  # 右后角
    [X2, Y3], [X1, Y3], [X0, Y3],            # 后墙顶边
    [X0, Y2],                                  # 左后角
    [X1, Y2], [X2, Y2],                       # 底板顶边
    [X3, Y2],                                  # 右墙顶/底板右上
    [X3, Y0],                                  # 糊边底
    [X4, Y0], [X4, Y3], [X3, Y3],            # 糊边
], dtype=np.float32)

# 分析角点间距离找"锯齿区域"
n = len(pts)
print(f"角点间距离:")
edge_types = []
for i in range(n):
    j = (i+1) % n
    d = math.hypot(pts[j][0]-pts[i][0], pts[j][1]-pts[i][1])
    if d > 200: 
        t = "PANEL"
    elif d > 80:
        t = "FLAP"
    else:
        t = "DETAIL"
    edge_types.append(t)
    print(f"  {i:2d}→{j:2d}: {d:6.0f}px {t}")

# 面板边界角 = PANEL边的端点
panel_corners_img = []
panel_corners_theory = []
# 长边端点是面板角
long_edge_indices = set()
for i in range(n):
    j = (i+1) % n
    d = math.hypot(pts[j][0]-pts[i][0], pts[j][1]-pts[i][1])
    if d > 200:
        long_edge_indices.add(i)
        long_edge_indices.add(j)

panel_pts = [(i, pts[i]) for i in sorted(long_edge_indices)]
print(f"\n面板角点: {len(panel_pts)}")
for idx, p in panel_pts:
    print(f"  #{idx}: ({p[0]+100:.0f}, {p[1]+700:.0f})")

# ============================================================
# Step 3: 用面板角做透视校正
# ============================================================
print("\n=== Step 3: 透视校正 ===")

# 用外接矩形做校正（最简单可靠）
all_x = [p[0] for _, p in panel_pts]
all_y = [p[1] for _, p in panel_pts]
bbox_tl = (min(all_x), min(all_y))
bbox_br = (max(all_x), max(all_y))

# 加一些padding
pad = 30
src_corners = np.array([
    [bbox_tl[0]-pad, bbox_tl[1]-pad],
    [bbox_br[0]+pad, bbox_tl[1]-pad],
    [bbox_br[0]+pad, bbox_br[1]+pad],
    [bbox_tl[0]-pad, bbox_br[1]+pad],
], dtype=np.float32)

target_w = 1500
target_h = int(target_w * UH / UW)
dst = np.array([[0,0],[target_w-1,0],[target_w-1,target_h-1],[0,target_h-1]], dtype=np.float32)

M = cv2.getPerspectiveTransform(src_corners, dst)
warped = cv2.warpPerspective(img, M, (target_w, target_h), flags=cv2.INTER_LANCZOS4)

scale = UW / target_w
print(f"校正: {target_w}×{target_h}, scale={scale:.4f} mm/px")
print(f"bbox: ({bbox_tl[0]:.0f},{bbox_tl[1]:.0f})->({bbox_br[0]:.0f},{bbox_br[1]:.0f})")

cv2.imwrite(f"{OUT}/f1_warped.png", warped)

# ============================================================
# Step 4: 在校正图上提取所有结构
# ============================================================
print("\n=== Step 4: 结构提取 ===")

def px2mm(x, y):
    return (x * scale, (target_h - y) * scale)

gray_w = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
denoised = cv2.bilateralFilter(gray_w, 9, 75, 75)

# 多源边缘
edges = cv2.Canny(denoised, 15, 60)
tophat_h = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (21,3)))
tophat_v = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3,21)))

combined = cv2.bitwise_or(edges, cv2.threshold(tophat_h, 25, 255, cv2.THRESH_BINARY)[1])
combined = cv2.bitwise_or(combined, cv2.threshold(tophat_v, 25, 255, cv2.THRESH_BINARY)[1])
kernel = np.ones((2,2), np.uint8)
combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=1)

cv2.imwrite(f"{OUT}/f2_edges.png", combined)

# Hough线段
lines_raw = cv2.HoughLinesP(combined, 1, np.pi/180, threshold=20, minLineLength=10, maxLineGap=6)
segments = []
if lines_raw is not None:
    for line in lines_raw:
        x1,y1,x2,y2 = line[0]
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        if length < 5: continue
        na = angle % 180
        if na > 90: na -= 180
        p1m = px2mm(x1, y1)
        p2m = px2mm(x2, y2)
        mm_len = math.hypot(p2m[0]-p1m[0], p2m[1]-p1m[1])
        segments.append({
            'p1': p1m, 'p2': p2m,
            'mid': ((p1m[0]+p2m[0])/2, (p1m[1]+p2m[1])/2),
            'length_mm': mm_len, 'angle': na,
        })

H_s = [s for s in segments if abs(s['angle'])<8]
V_s = [s for s in segments if abs(abs(s['angle'])-90)<8]
D_s = [s for s in segments if 20<abs(s['angle'])<70]

print(f"线段: 总{len(segments)} H:{len(H_s)} V:{len(V_s)} D:{len(D_s)}")

# ============================================================
# Step 5: 理论匹配
# ============================================================
print("\n=== Step 5: 理论匹配 ===")

def merge_lines(segs, axis, tol=3.0):
    groups = []
    for s in segs:
        val = s['mid'][axis]
        placed = False
        for g in groups:
            if abs(g['val'] - val) < tol:
                g['segs'].append(s)
                g['val'] = sum(s2['mid'][axis] for s2 in g['segs']) / len(g['segs'])
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

theory_h = [(Y0,"前墙底"),(Y1,"底板底"),(Y2,"底板顶"),(Y3,"后墙顶")]
theory_v = [(X0,"左墙外"),(X1,"底板左"),(X2,"底板右"),(X3,"右墙外"),(X4,"糊边右")]

matched = 0
total_diff = 0
print("  H线:")
for theo_y, name in theory_h:
    best = None
    best_d = 999
    for g in HG:
        if g['length'] > 20:
            d = abs(g['val'] - theo_y)
            if d < best_d:
                best_d = d
                best = g
    if best:
        status = "✓" if best_d < 3 else ("≈" if best_d < 8 else "✗")
        print(f"  {status} {name}: 理论{theo_y:.1f} 图像{best['val']:.1f} Δ={best_d:.1f}mm L={best['length']:.0f}")
        if best_d < 10:
            matched += 1
            total_diff += best_d

print("  V线:")
for theo_x, name in theory_v:
    best = None
    best_d = 999
    for g in VG:
        if g['length'] > 20:
            d = abs(g['val'] - theo_x)
            if d < best_d:
                best_d = d
                best = g
    if best:
        status = "✓" if best_d < 3 else ("≈" if best_d < 8 else "✗")
        print(f"  {status} {name}: 理论{theo_x:.1f} 图像{best['val']:.1f} Δ={best_d:.1f}mm L={best['length']:.0f}")
        if best_d < 10:
            matched += 1
            total_diff += best_d

if matched > 0:
    print(f"\n  平均偏差: {total_diff/matched:.1f}mm ({matched}条匹配)")

# ============================================================
# Step 6: 对称性验证
# ============================================================
print("\n=== Step 6: 对称性 ===")

X_MID = X1 + W/2
Y_MID = Y1 + L/2

# 底板区域 H线 左右对称
asym_count = 0
for g in HG:
    my = g['val']
    if not (Y1-5 < my < Y2+5): continue
    if g['length'] < 15: continue
    g_cx = (g['xr'][0]+g['xr'][1])/2
    mirror_cx = 2*X_MID - g_cx
    found = any(
        abs((g2['xr'][0]+g2['xr'][1])/2 - mirror_cx) < 5 and abs(g2['val'] - my) < 3
        for g2 in HG if g2 is not g
    )
    if not found:
        asym_count += 1

# 底板区域 V线 上下对称
for g in VG:
    mx = g['val']
    if not (X1-5 < mx < X2+5): continue
    if g['length'] < 15: continue
    g_cy = (g['yr'][0]+g['yr'][1])/2
    mirror_cy = 2*Y_MID - g_cy
    found = any(
        abs((g2['yr'][0]+g2['yr'][1])/2 - mirror_cy) < 5 and abs(g2['val'] - mx) < 3
        for g2 in VG if g2 is not g
    )
    if not found:
        asym_count += 1

if asym_count == 0:
    print("  ✓ 底板区域完全对称")
else:
    print(f"  ⚠ {asym_count}处不对称（可能是设计特征或物理遮挡）")

# ============================================================
# Step 7: 特征识别
# ============================================================
print("\n=== Step 7: 特征识别 ===")

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
        mirror_name = {'前墙下方':'后墙上方','后墙上方':'前墙下方',
                       '左墙左方':'右墙右方','右墙右方':'左墙左方'}[name]
        mirror_fs = [s for s in D_s if flap_zones[mirror_name](s)]
        sym = "✓" if abs(len(fs)-len(mirror_fs)) <= 2 else f"⚠"
        print(f"  {name}: {len(fs)}条 θ={min(angs):.0f}°~{max(angs):.0f}° L={min(lens):.1f}~{max(lens):.1f}mm vs {mirror_name}:{len(mirror_fs)}条 {sym}")

# 锁扣候选
print(f"\n  角落附近短线(锁扣):")
corners_mm = [(X1,Y1),(X2,Y1),(X1,Y2),(X2,Y2)]
total_locks = 0
for cx, cy in corners_mm:
    near = [s for s in segments if math.hypot(s['mid'][0]-cx, s['mid'][1]-cy) < 25 and 5 < s['length_mm'] < 25]
    if near:
        total_locks += len(near)
        print(f"  ({cx:.0f},{cy:.0f}): {len(near)}条", end="")
        if len(near) > 0:
            avg_l = sum(s['length_mm'] for s in near)/len(near)
            print(f" avg_L={avg_l:.1f}mm", end="")
        print()

# 弧度
print(f"\n  弧度:")
contours_ext, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
for ci, contour in enumerate(sorted(contours_ext, key=lambda c: -cv2.contourArea(c))[:3]):
    pts_c = contour.reshape(-1, 2)
    nc = len(pts_c)
    if nc < 100: continue
    win = 15
    curvs = []
    for i in range(nc):
        pp, pc, pn = pts_c[(i-win)%nc], pts_c[i], pts_c[(i+win)%nc]
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
                    ap = pts_c[start:hc[i-1]+1]
                    p1m = px2mm(*ap[0])
                    p2m = px2mm(*ap[-1])
                    ak = np.mean(np.abs(curvs[start:hc[i-1]+1]))
                    R = 1.0/(ak*scale) if ak > 0 else 999
                    arcs.append((p1m, p2m, R, len(ap)))
                start = hc[i]
        real_arcs = [a for a in arcs if 3 < a[3] and 2 < a[2] < 100]
        if real_arcs:
            print(f"  轮廓#{ci}: {len(real_arcs)}处弧")
            for p1, p2, R, cnt in real_arcs[:5]:
                print(f"    R≈{R:.1f}mm ({p1[0]:.0f},{p1[1]:.0f})→({p2[0]:.0f},{p2[1]:.0f})")

# ============================================================
# Step 8: 叠加可视化
# ============================================================
print("\n=== Step 8: 可视化 ===")

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

# 对称轴
cv2.line(overlay, mm2px(X_MID,-5), mm2px(X_MID,UH+5), (255,0,255), 1)

# 图像线段
for s in H_s:
    if s['length_mm'] > 10:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (0,255,255), 1)
for s in V_s:
    if s['length_mm'] > 10:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,255,0), 1)
for s in D_s:
    if s['length_mm'] > 5:
        cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,165,0), 1)

cv2.imwrite(f"{OUT}/f3_overlay.png", overlay)

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
cv2.imwrite(f"{OUT}/f3_lines.png", line_bg)

print(f"  ✓ 叠加: f3_overlay.png")
print(f"  ✓ 纯线: f3_lines.png")
print(f"\n=== 完成 ===")
