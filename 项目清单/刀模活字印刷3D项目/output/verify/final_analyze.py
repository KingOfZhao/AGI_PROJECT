#!/usr/bin/env python3
"""Path B v3 final: 完整结构识别+对称性验证"""
import cv2, numpy as np, math

OUT = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/output/verify"
IMG = "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
img = cv2.imread(IMG)

W, L, H = 123.0, 135.0, 46.78
GLUE = 15.0
UW = 2*H + W + GLUE; UH = 2*H + L
X0,X1,X2,X3,X4 = 0, H, H+W, 2*H+W, 2*H+W+GLUE
Y0,Y1,Y2,Y3 = 0, H, H+L, 2*H+L

# 最佳homography (从f5步骤获得)
outline_pts = np.array([
    [144, 0], [184, 371], [191, 603], [447, 592], [512, 799], [855, 799],
    [964, 595], [1056, 604], [983, 669], [1111, 707], [1199, 284],
    [1095, 0], [235, 0], [176, 379], [272, 622], [512, 592],
], dtype=np.float32)

theory_simple = np.array([
    [X0, Y0], [X1, Y0], [X2, Y0], [X2, Y1], [X3, Y1], [X3, Y3],
    [X2, Y3], [X1, Y3], [X0, Y3], [X0, Y2], [X1, Y2], [X2, Y2],
    [X3, Y2], [X3, Y0], [X4, Y0], [X4, Y3],
], dtype=np.float32)

img_top4 = [0, 11, 12, 10]
th_top4 = [0, 8, 14, 1]
perm = (2, 0, 1, 3)
src_4 = outline_pts[np.array([img_top4[perm[i]] for i in range(4)])].reshape(-1,1,2)
dst_4 = theory_simple[th_top4].reshape(-1,1,2)
M, _ = cv2.findHomography(src_4, dst_4)

target_w = 1500
target_h = int(target_w * UH / UW)
warped = cv2.warpPerspective(img, M, (target_w, target_h), flags=cv2.INTER_LANCZOS4)
scale = UW / target_w

def px2mm(x, y):
    return (x * scale, (target_h - y) * scale)

def mm2px(x, y):
    return (int(x/scale), int(target_h - y/scale))

# 边缘提取
gray_w = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
denoised = cv2.bilateralFilter(gray_w, 9, 75, 75)
edges = cv2.Canny(denoised, 15, 60)
tophat_h = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (21,3)))
tophat_v = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3,21)))
combined = cv2.bitwise_or(edges, cv2.threshold(tophat_h, 25, 255, cv2.THRESH_BINARY)[1])
combined = cv2.bitwise_or(combined, cv2.threshold(tophat_v, 25, 255, cv2.THRESH_BINARY)[1])
kernel = np.ones((2,2), np.uint8)
combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=1)

# Hough线段
lines_raw = cv2.HoughLinesP(combined, 1, np.pi/180, threshold=20, minLineLength=8, maxLineGap=6)
segments = []
if lines_raw is not None:
    for line in lines_raw:
        x1,y1,x2,y2 = line[0]
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        if length < 3: continue
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

# 合并
def merge_lines(segs, axis, tol=2.0):
    groups = []
    for s in segs:
        val = s['mid'][axis]
        placed = False
        for g in groups:
            if abs(g['val'] - val) < tol:
                g['segs'].append(s)
                g['val'] = sum(s2['mid'][axis] for s2 in g['segs']) / len(g['segs'])
                g['length'] = max(g['length'], s['length_mm'])
                ax = [x for s2 in g['segs'] for x in (s2['p1'][0], s2['p2'][0])]
                ay = [y for s2 in g['segs'] for y in (s2['p1'][1], s2['p2'][1])]
                g['xr'] = (min(ax), max(ax))
                g['yr'] = (min(ay), max(ay))
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

# 理论匹配
theory_h = [(Y0,"前墙底"),(Y1,"底板底"),(Y2,"底板顶"),(Y3,"后墙顶")]
theory_v = [(X0,"左墙外"),(X1,"底板左"),(X2,"底板右"),(X3,"右墙外"),(X4,"糊边右")]

print("\n=== H线匹配 ===")
h_matched = {}
for theo_y, name in theory_h:
    best = None; best_d = 999
    for g in HG:
        if g['length'] > 15:
            d = abs(g['val'] - theo_y)
            if d < best_d: best_d = d; best = g
    if best:
        st = "✓" if best_d < 2 else ("≈" if best_d < 5 else "✗")
        print(f"  {st} {name}: 理论{theo_y:.1f} 图像{best['val']:.1f} Δ={best_d:.1f}mm L={best['length']:.0f}")
        h_matched[name] = best_d

print("\n=== V线匹配 ===")
v_matched = {}
for theo_x, name in theory_v:
    best = None; best_d = 999
    for g in VG:
        if g['length'] > 15:
            d = abs(g['val'] - theo_x)
            if d < best_d: best_d = d; best = g
    if best:
        st = "✓" if best_d < 2 else ("≈" if best_d < 5 else "✗")
        print(f"  {st} {name}: 理论{theo_x:.1f} 图像{best['val']:.1f} Δ={best_d:.1f}mm L={best['length']:.0f}")
        v_matched[name] = best_d

# 对称性
print("\n=== 对称性验证 ===")
X_MID = X1 + W/2
Y_MID = Y1 + L/2

asym_lr = 0
for g in HG:
    my = g['val']
    if not (Y1-3 < my < Y2+3): continue
    if g['length'] < 10: continue
    g_cx = (g['xr'][0]+g['xr'][1])/2
    mcx = 2*X_MID - g_cx
    found = any(abs((g2['xr'][0]+g2['xr'][1])/2 - mcx) < 4 and abs(g2['val'] - my) < 2
               for g2 in HG if g2 is not g)
    if not found:
        asym_lr += 1
        print(f"  ⚠ H不对称: y={my:.1f} cx={g_cx:.0f} L={g['length']:.1f}")

asym_tb = 0
for g in VG:
    mx = g['val']
    if not (X1-3 < mx < X2+3): continue
    if g['length'] < 10: continue
    g_cy = (g['yr'][0]+g['yr'][1])/2
    mcy = 2*Y_MID - g_cy
    found = any(abs((g2['yr'][0]+g2['yr'][1])/2 - mcy) < 4 and abs(g2['val'] - mx) < 2
               for g2 in VG if g2 is not g)
    if not found:
        asym_tb += 1
        print(f"  ⚠ V不对称: x={mx:.1f} cy={g_cy:.0f} L={g['length']:.1f}")

if asym_lr == 0 and asym_tb == 0:
    print("  ✓ 底板区域完全对称")
else:
    print(f"  不对称: H={asym_lr} V={asym_tb}")

# 防撞翼片
print("\n=== 防撞翼片 ===")
flap_zones = {
    '前墙下方': lambda s: s['mid'][1] < Y1-2 and X1-3 < s['mid'][0] < X2+3,
    '后墙上方': lambda s: s['mid'][1] > Y2+2 and X1-3 < s['mid'][0] < X2+3,
    '左墙左方': lambda s: s['mid'][0] < X1-2 and Y1-3 < s['mid'][1] < Y2+3,
    '右墙右方': lambda s: s['mid'][0] > X2+2 and Y1-3 < s['mid'][1] < Y2+3,
}
mirror_map = {'前墙下方':'后墙上方','后墙上方':'前墙下方','左墙左方':'右墙右方','右墙右方':'左墙左方'}
for name, test in flap_zones.items():
    fs = [s for s in D_s if test(s)]
    if fs:
        angs = [s['angle'] for s in fs]
        lens = [s['length_mm'] for s in fs]
        mirror_fs = [s for s in D_s if flap_zones[mirror_map[name]](s)]
        diff = abs(len(fs) - len(mirror_fs))
        sym = "✓" if diff <= 2 else f"⚠ 差{diff}条"
        print(f"  {name}: {len(fs)}条 θ={min(angs):.0f}°~{max(angs):.0f}° L={min(lens):.1f}~{max(lens):.1f}mm vs {mirror_map[name]}:{len(mirror_fs)}条 {sym}")
        if len(fs) >= 3:
            avg_depth = sum(s['length_mm'] for s in fs) / len(fs)
            ys = sorted(set(round(s['mid'][1], 0) for s in fs))
            if len(ys) > 1:
                spacings = [ys[i+1]-ys[i] for i in range(len(ys)-1)]
                avg_sp = sum(spacings) / len(spacings)
                print(f"    齿: n≈{len(ys)}, 平均深度={avg_depth:.1f}mm, 间距={avg_sp:.1f}mm")

# 锁扣
print("\n=== 锁扣候选 ===")
corners_mm = [(X1,Y1),(X2,Y1),(X1,Y2),(X2,Y2)]
cn = ["底板左下","底板右下","底板左上","底板右上"]
for (cx,cy), name in zip(corners_mm, cn):
    near = [s for s in segments if math.hypot(s['mid'][0]-cx, s['mid'][1]-cy) < 20 and 3 < s['length_mm'] < 20]
    if near:
        print(f"  {name}: {len(near)}条")

# 可视化
overlay = warped.copy()
for p1, p2 in [
    ((X0,Y1),(X0,Y0)), ((X0,Y0),(X1,Y0)), ((X1,Y0),(X2,Y0)),
    ((X2,Y0),(X2,Y1)), ((X2,Y1),(X3,Y1)), ((X3,Y1),(X3,Y3)),
    ((X3,Y3),(X2,Y3)), ((X2,Y3),(X1,Y3)), ((X1,Y3),(X0,Y3)),
    ((X0,Y3),(X0,Y2)), ((X0,Y2),(X1,Y2)), ((X1,Y2),(X2,Y2)),
    ((X2,Y2),(X3,Y2)),
    ((X3,Y0),(X4,Y0)), ((X4,Y0),(X4,Y3)), ((X4,Y3),(X3,Y3)),
]:
    cv2.line(overlay, mm2px(*p1), mm2px(*p2), (0,0,255), 2)
for p1, p2 in [((X1,Y1),(X2,Y1)),((X1,Y2),(X2,Y2)),((X1,Y0),(X1,Y3)),((X2,Y0),(X2,Y3)),((X3,Y0),(X3,Y3))]:
    cv2.line(overlay, mm2px(*p1), mm2px(*p2), (0,255,0), 1)
cv2.line(overlay, mm2px(X_MID,-5), mm2px(X_MID,UH+5), (255,0,255), 1)
for s in H_s:
    if s['length_mm'] > 8: cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (0,255,255), 1)
for s in V_s:
    if s['length_mm'] > 8: cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,255,0), 1)
for s in D_s:
    if s['length_mm'] > 3: cv2.line(overlay, mm2px(*s['p1']), mm2px(*s['p2']), (255,165,0), 1)
cv2.imwrite(f"{OUT}/f6_overlay.png", overlay)

line_bg = np.ones_like(warped) * 255
for s in segments:
    if s['length_mm'] > 2:
        p1 = mm2px(*s['p1']); p2 = mm2px(*s['p2'])
        c = (0,0,0) if (abs(s['angle'])<8 or abs(abs(s['angle'])-90)<8) else (100,100,100)
        cv2.line(line_bg, p1, p2, c, 1)
cv2.imwrite(f"{OUT}/f6_lines.png", line_bg)

all_diffs = list(h_matched.values()) + list(v_matched.values())
avg_d = sum(all_diffs)/len(all_diffs) if all_diffs else 0
max_d = max(all_diffs) if all_diffs else 0
matched_good = sum(1 for d in all_diffs if d < 3)
print(f"\n=== 总结 ===")
print(f"匹配: {matched_good}/{len(all_diffs)}条 Δ<3mm")
print(f"平均偏差: {avg_d:.1f}mm, 最大: {max_d:.1f}mm")
print(f"对称: H不对称={asym_lr}, V不对称={asym_tb}")
print(f"✓ f6_overlay.png, f6_lines.png")
