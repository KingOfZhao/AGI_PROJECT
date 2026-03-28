#!/usr/bin/env python3
"""查询 pacdora_models_full.json 中的 tray box 模型"""
import json, sys

DATA_PATH = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

models = raw["data"] if isinstance(raw, dict) else raw

# 1. 找 120370
found_120370 = None
for m in models:
    if "120370" in str(m):
        found_120370 = m
        break

if found_120370:
    print("=== 找到 120370 ===")
    print(json.dumps(found_120370, ensure_ascii=False, indent=2))
else:
    print("=== 未找到 120370，搜索 tray 类模型 ===")

# 2. 找所有 tray box 模型
tray_models = []
for m in models:
    s = json.dumps(m, ensure_ascii=False).lower()
    if "tray" in s or "托盘" in s or "纸盘" in s or "盘式" in s:
        tray_models.append(m)

print(f"\n=== Tray 类模型总数: {len(tray_models)} ===")
for m in tray_models[:8]:
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print("---")

# 3. 统计所有 class1/class2 分类
class1_set = {}
class2_set = {}
for m in models:
    c1 = m.get("class1", "unknown")
    c2 = m.get("class2", "unknown")
    class1_set[c1] = class1_set.get(c1, 0) + 1
    class2_set[c2] = class2_set.get(c2, 0) + 1

print("\n=== class1 分类统计 ===")
for k, v in sorted(class1_set.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\n=== class2 分类统计 (前30) ===")
for k, v in sorted(class2_set.items(), key=lambda x: -x[1])[:30]:
    print(f"  {k}: {v}")

# 4. 查看模型的字段结构
print("\n=== 模型字段结构 (第一条) ===")
if models:
    print(json.dumps(list(models[0].keys()), ensure_ascii=False))
    # 看有没有 demoProjectDataUrl 类字段
    for k in models[0].keys():
        val = models[0][k]
        if isinstance(val, str) and len(val) > 100:
            print(f"  {k}: {val[:200]}...")
        else:
            print(f"  {k}: {val}")
