#!/usr/bin/env python3
"""Pacdora模型数据维度分析 — 使用safe_code_executor避免heredoc/quote问题"""
import json, re
from collections import Counter

data = json.loads(open("/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json").read())
models = data["data"]
print(f"总模型数: {len(models)}")

cate_ids = set()
class1_all = set()
class2_all = set()
materials = set()
names = Counter()
fefco_codes = set()
size_L, size_W, size_H = [], [], []
has_knife = 0
has_3d = 0

for m in models:
    cate_ids.add(m.get("cate_id"))
    c1 = str(m.get("class1", "") or "")
    c2 = str(m.get("class2", "") or "")
    for c in re.findall(r"\((\d+)\)", c1):
        class1_all.add(c)
    for c in re.findall(r"\((\d+)\)", c2):
        class2_all.add(c)
    for ms in (m.get("modeSetting") or []):
        mat = ms.get("material", "") or ""
        if mat:
            materials.add(mat)
    name = m.get("name", "") or ""
    if name:
        names[name] += 1
    kw = str(m.get("keywords", "") or "")
    for fc in re.findall(r"fefco\s*(\d{4})", kw, re.IGNORECASE):
        fefco_codes.add(fc)
    for fc in re.findall(r"\b(0\d{3})\b", kw):
        fefco_codes.add(fc)
    L = m.get("length", 0) or 0
    W = m.get("width", 0) or 0
    H = m.get("height", 0) or 0
    if L:
        size_L.append(L)
    if W:
        size_W.append(W)
    if H:
        size_H.append(H)
    if m.get("knife"):
        has_knife += 1
    if m.get("demoProjectDataUrl"):
        has_3d += 1

print(f"\n=== 分类维度 ===")
print(f"cate_id: {sorted(cate_ids)} ({len(cate_ids)}种)")
print(f"class1编码: {len(class1_all)}种")
print(f"class2编码: {len(class2_all)}种")
print(f"材料: {sorted(materials)} ({len(materials)}种)")
print(f"FEFCO编码: {sorted(fefco_codes)[:30]}... 共{len(fefco_codes)}种")
print(f"盒型名称: {len(names)}种")
print(f"\nTop25盒型:")
for n, c in names.most_common(25):
    print(f"  {c:4d} | {n}")
print(f"\n=== 尺寸范围 ===")
if size_L:
    print(f"L: {min(size_L)}-{max(size_L)}mm, avg={sum(size_L)/len(size_L):.0f}, n={len(size_L)}")
if size_W:
    print(f"W: {min(size_W)}-{max(size_W)}mm, avg={sum(size_W)/len(size_W):.0f}, n={len(size_W)}")
if size_H:
    print(f"H: {min(size_H)}-{max(size_H)}mm, avg={sum(size_H)/len(size_H):.0f}, n={len(size_H)}")
print(f"\n=== 资产覆盖 ===")
print(f"刀模图: {has_knife}/{len(models)} ({has_knife*100//len(models)}%)")
print(f"3D数据: {has_3d}/{len(models)} ({has_3d*100//len(models)}%)")

# 额外维度分析
print(f"\n=== 额外维度 ===")
enterprise = sum(1 for m in models if m.get("is_enterprise"))
print(f"企业版模型: {enterprise}")
cate_names = Counter()
for m in models:
    ci = m.get("cate_info") or {}
    ct = ci.get("complex_type", 0)
    cate_names[ct] += 1
print(f"complex_type分布: {dict(cate_names)}")
def_sci = Counter(m.get("def_science_id") for m in models)
print(f"def_science_id分布: {dict(def_sci.most_common(10))}")
