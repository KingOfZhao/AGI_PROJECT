#!/usr/bin/env python3
"""补充分析: 材质详情 + modeSetting 完整结构 + 120370可调节内容"""
import json
from collections import Counter

DATA_PATH = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

models = raw["data"]

# 找120370
m120370 = None
for m in models:
    if str(m.get("num", "")) == "120370":
        m120370 = m
        break

# 1. nameKey URL验证
print("=" * 60)
print("1. 详情页URL构造规则验证")
print("=" * 60)
print(f"  nameKey已包含num: {sum(1 for m in models if str(m.get('num','')) in str(m.get('nameKey','')))}/{len(models)}")
print(f"\n  构造规则: https://www.pacdora.cn/dielines-detail/{{nameKey}}")
print(f"  样机页:   https://www.pacdora.cn/mockup-detail/{{mockupNameKey}}")
print(f"\n  120370:")
print(f"    nameKey = {m120370['nameKey']}")
print(f"    → https://www.pacdora.cn/dielines-detail/{m120370['nameKey']}")

# 2. 120370 modeSetting 完整字段
print(f"\n{'='*60}")
print("2. 120370 modeSetting 完整字段")
print("=" * 60)
for i, ms in enumerate(m120370.get("modeSetting", [])):
    print(f"\n  modeSetting[{i}]:")
    for k, v in ms.items():
        if isinstance(v, str) and len(v) > 120:
            print(f"    {k}: {v[:120]}...")
        else:
            print(f"    {k}: {v}")

# 3. 所有材质的modeSetting字段结构对比
print(f"\n{'='*60}")
print("3. modeSetting 字段结构(统计)")
print("=" * 60)
all_ms_keys = Counter()
for m in models:
    for ms in m.get("modeSetting", []):
        for k in ms.keys():
            all_ms_keys[k] += 1
print(f"  modeSetting 中出现的所有字段:")
for k, cnt in all_ms_keys.most_common():
    print(f"    {k}: {cnt}次")

# 4. 不同材质的具体参数对比
print(f"\n{'='*60}")
print("4. 各材质参数对比 (采样)")
print("=" * 60)
seen_mats = set()
for m in models[:500]:
    for ms in m.get("modeSetting", []):
        mat = ms.get("material", "?")
        if mat not in seen_mats:
            seen_mats.add(mat)
            print(f"\n  材质: {mat}")
            for k, v in ms.items():
                if k == "image" and isinstance(v, str):
                    print(f"    {k}: {v[:80]}...")
                else:
                    print(f"    {k}: {v}")
        if len(seen_mats) >= 15:
            break
    if len(seen_mats) >= 15:
        break

# 5. tags分析(可能包含可调节属性标签)
print(f"\n{'='*60}")
print("5. 120370的tags")
print("=" * 60)
tags = m120370.get("tags", [])
print(f"  tag数量: {len(tags)}")
for t in tags[:20]:
    if isinstance(t, dict):
        print(f"    {json.dumps(t, ensure_ascii=False)[:100]}")
    else:
        print(f"    {t}")

# 6. 前5个模型的mockupNameKey
print(f"\n{'='*60}")
print("6. mockupNameKey 样机页URL")
print("=" * 60)
for m in models[:8]:
    num = m.get("num")
    mnk = m.get("mockupNameKey", "")
    name = m.get("name", "")
    if mnk:
        print(f"  [{num}] {name}")
        print(f"    样机: https://www.pacdora.cn/mockup-detail/{mnk}")
        print(f"    刀线: https://www.pacdora.cn/dielines-detail/{m.get('nameKey','')}")
        print()

# 7. 有无 editor URL 或编辑器入口
print(f"\n{'='*60}")
print("7. 编辑器入口分析")
print("=" * 60)
# 检查是否有 editor 相关字段
for k in m120370.keys():
    kl = k.lower()
    if "edit" in kl or "design" in kl or "custom" in kl or "config" in kl:
        print(f"  字段: {k} = {m120370[k]}")

# 推测编辑器URL
print(f"\n  推测编辑器入口:")
print(f"    刀线详情页点击'编辑'按钮 → 进入在线编辑器")
print(f"    可能URL: https://www.pacdora.cn/editor/{m120370.get('num')}")
print(f"    或: https://www.pacdora.cn/design/{m120370.get('num')}")
print(f"    或: 详情页内嵌编辑功能(SPA路由切换)")

# 8. description字段中的功能描述
print(f"\n{'='*60}")
print("8. description字段(功能描述)")
print("=" * 60)
desc = m120370.get("description", "")
print(f"  120370: {desc}")
print()
# 多看几个
for m in models[:5]:
    d = m.get("description", "")
    if d:
        print(f"  [{m.get('num')}]: {d[:200]}")
        print()
