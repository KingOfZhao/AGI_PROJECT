#!/usr/bin/env python3
"""查询 120370 tray box 模型详情 + 下载 demoProjectData"""
import json, sys

DATA_PATH = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

models = raw["data"]

# 1. 找 120370
print("=== 搜索 120370 ===")
found = None
for m in models:
    if str(m.get("num", "")) == "120370":
        found = m
        break
    # also check nameKey
    nk = str(m.get("nameKey", ""))
    if "120370" in nk:
        found = m
        break

if found:
    print(json.dumps(found, ensure_ascii=False, indent=2))
else:
    print("num=120370 未找到，尝试全文搜索...")
    for m in models:
        if "120370" in json.dumps(m):
            found = m
            print(json.dumps(m, ensure_ascii=False, indent=2))
            break

if not found:
    print("\n120370 不在 pacdora_models_full.json 中")
    # 找 tray boxes four folds
    print("\n=== 搜索 tray boxes / four folds ===")
    for m in models:
        kw = str(m.get("keywords", "")).lower()
        nk = str(m.get("nameKey", "")).lower()
        name = str(m.get("name", "")).lower()
        if "tray" in nk or "托盘" in name or "纸盘" in name or "盘式" in name:
            print(f"\n--- {m.get('num')} | {m.get('name')} ---")
            print(f"  nameKey: {m.get('nameKey')}")
            print(f"  class2Bymodel: {m.get('class2Bymodel')}")
            print(f"  L×W×H: {m.get('length')}×{m.get('width')}×{m.get('height')}")
            print(f"  demoProjectDataUrl: {m.get('demoProjectDataUrl')}")
            print(f"  image: {m.get('image')}")
            print(f"  knife: {m.get('knife')}")
            kw_short = str(m.get('keywords', ''))[:200]
            print(f"  keywords: {kw_short}")
            ms = m.get('modeSetting', [])
            if ms:
                for s in ms:
                    print(f"  material: {s.get('material')} | img: {s.get('image','')[:80]}")
            desc = str(m.get('description', ''))[:300]
            print(f"  description: {desc}")

# 2. 统计 tray 相关模型数量
tray_count = 0
tray_nums = []
for m in models:
    nk = str(m.get("nameKey", "")).lower()
    name = str(m.get("name", "")).lower()
    kw = str(m.get("keywords", "")).lower()
    if "tray" in nk or "tray" in kw or "托盘" in name or "纸盘" in name:
        tray_count += 1
        tray_nums.append(m.get("num"))

print(f"\n=== Tray 类模型总数: {tray_count} ===")
print(f"编号: {tray_nums[:20]}")

# 3. 模型字段中哪些包含可自定义内容
print("\n=== 自定义相关字段分析 ===")
m0 = models[0]
print(f"cate_info.size_options: {m0.get('cate_info',{}).get('size_options','N/A')}")
print(f"modeSetting (材质选项): {len(m0.get('modeSetting',[]))} 种")
for s in m0.get('modeSetting', []):
    print(f"  material={s.get('material')}, coverType={s.get('coverType','')}")
print(f"def_science_id: {m0.get('def_science_id')}")
print(f"cate_info.complex_type: {m0.get('cate_info',{}).get('complex_type')}")
print(f"cate_info.elaborate: {m0.get('cate_info',{}).get('elaborate')}")
print(f"cate_info.displaySetting: {m0.get('cate_info',{}).get('displaySetting')}")

# 4. 所有不同的 material 类型
materials = set()
for m in models:
    for s in m.get("modeSetting", []):
        materials.add(s.get("material", "unknown"))
print(f"\n=== 所有材质类型 ({len(materials)}) ===")
for mat in sorted(materials):
    print(f"  {mat}")

# 5. 尺寸范围统计
lens = [m.get("length",0) for m in models if m.get("length")]
wids = [m.get("width",0) for m in models if m.get("width")]
hgts = [m.get("height",0) for m in models if m.get("height")]
print(f"\n=== 尺寸范围 ===")
print(f"  length: {min(lens)}-{max(lens)}mm (avg={sum(lens)/len(lens):.0f})")
print(f"  width:  {min(wids)}-{max(wids)}mm (avg={sum(wids)/len(wids):.0f})")
print(f"  height: {min(hgts)}-{max(hgts)}mm (avg={sum(hgts)/len(hgts):.0f})")
