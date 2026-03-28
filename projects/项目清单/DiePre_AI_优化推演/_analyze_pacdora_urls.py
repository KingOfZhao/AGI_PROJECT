#!/usr/bin/env python3
"""分析 pacdora_models_full.json 中所有URL字段和资源路径模式"""
import json, re
from collections import Counter, defaultdict

DATA_PATH = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

models = raw["data"]
print(f"=== 模型总数: {len(models)} ===\n")

# 1. 找出所有包含URL的字段
print("=" * 60)
print("1. 所有包含URL的字段")
print("=" * 60)
url_fields = defaultdict(list)
m0 = models[0]

def find_urls(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_urls(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_urls(item, f"{prefix}[{i}]")
    elif isinstance(obj, str) and ("http" in obj or "cloud.pacdora" in obj or ".json" in obj or ".png" in obj or ".jpg" in obj):
        url_fields[prefix.split("[")[0]].append(obj)

find_urls(m0)
for field, urls in sorted(url_fields.items()):
    print(f"\n  字段: {field}")
    for u in urls[:3]:
        print(f"    示例: {u[:150]}")

# 2. 分析 demoProjectDataUrl 模式
print("\n" + "=" * 60)
print("2. demoProjectDataUrl 模式分析")
print("=" * 60)
demo_urls = [m.get("demoProjectDataUrl", "") for m in models if m.get("demoProjectDataUrl")]
print(f"  有 demoProjectDataUrl 的模型数: {len(demo_urls)}")

# URL模式
url_patterns = Counter()
for url in demo_urls:
    # 提取域名+路径模式
    match = re.match(r'(https?://[^/]+)(/.+)', url)
    if match:
        domain = match.group(1)
        path = match.group(2)
        # 泛化路径(数字替换为{num})
        pattern = re.sub(r'/\d+\.json', '/{num}.json', path)
        url_patterns[f"{domain}{pattern}"] += 1

print(f"\n  URL模式:")
for pattern, count in url_patterns.most_common(10):
    print(f"    {pattern} → {count}个")

# 示例
print(f"\n  前5个 demoProjectDataUrl:")
for url in demo_urls[:5]:
    print(f"    {url}")

# 3. 分析 image 字段(2D预览图)
print("\n" + "=" * 60)
print("3. image 字段(2D刀线预览图) 模式分析")
print("=" * 60)
image_urls = [m.get("image", "") for m in models if m.get("image")]
print(f"  有 image 的模型数: {len(image_urls)}")

img_patterns = Counter()
for url in image_urls:
    match = re.match(r'(https?://[^/]+)(/.+)', url)
    if match:
        domain = match.group(1)
        path = match.group(2)
        # 泛化
        pattern = re.sub(r'/[a-f0-9]{20,}', '/{hash}', path)
        pattern = re.sub(r'/\d+', '/{num}', pattern)
        img_patterns[f"{domain}{pattern}"] += 1

print(f"\n  URL模式:")
for pattern, count in img_patterns.most_common(5):
    print(f"    {pattern} → {count}个")

print(f"\n  前3个 image URL:")
for url in image_urls[:3]:
    print(f"    {url}")

# 4. 分析 knife 字段(刀线SVG/图片)
print("\n" + "=" * 60)
print("4. knife 字段(刀线图) 模式分析")
print("=" * 60)
knife_urls = [m.get("knife", "") for m in models if m.get("knife")]
print(f"  有 knife 的模型数: {len(knife_urls)}")
if knife_urls:
    print(f"\n  前3个 knife URL:")
    for url in knife_urls[:3]:
        print(f"    {url[:200]}")

# 5. 分析 modeSetting 中的图片URL(材质预览)
print("\n" + "=" * 60)
print("5. modeSetting 材质预览图 模式分析")
print("=" * 60)
mode_img_urls = []
for m in models:
    for ms in m.get("modeSetting", []):
        img = ms.get("image", "")
        if img:
            mode_img_urls.append(img)

print(f"  材质预览图总数: {len(mode_img_urls)}")
if mode_img_urls:
    print(f"\n  前5个材质预览图:")
    for url in mode_img_urls[:5]:
        print(f"    {url[:200]}")

# 6. 分析 nameKey → 网页URL映射
print("\n" + "=" * 60)
print("6. nameKey → 详情页URL映射规则")
print("=" * 60)
for m in models[:10]:
    nk = m.get("nameKey", "")
    num = m.get("num", "")
    name = m.get("name", "")
    print(f"  num={num} | nameKey={nk}")
    print(f"    → https://www.pacdora.cn/dielines-detail/{nk}-dieline-{num}")
    print(f"    → name: {name}")

# 7. 分析完整模型数据结构中所有字段
print("\n" + "=" * 60)
print("7. 模型完整字段列表 (第一条)")
print("=" * 60)
for k, v in m0.items():
    vtype = type(v).__name__
    if isinstance(v, str):
        vshow = v[:100] + "..." if len(v) > 100 else v
    elif isinstance(v, list):
        vshow = f"[{len(v)} items]"
    elif isinstance(v, dict):
        vshow = f"{{keys: {list(v.keys())[:8]}}}"
    else:
        vshow = str(v)
    print(f"  {k} ({vtype}): {vshow}")

# 8. 分析 cate_info 子结构
print("\n" + "=" * 60)
print("8. cate_info 子结构分析")
print("=" * 60)
ci = m0.get("cate_info", {})
for k, v in ci.items():
    vtype = type(v).__name__
    if isinstance(v, str):
        vshow = v[:150] + "..." if len(v) > 150 else v
    elif isinstance(v, list):
        vshow = f"[{len(v)} items]"
        if v and len(v) <= 5:
            vshow = str(v)[:200]
    elif isinstance(v, dict):
        vshow = f"{{keys: {list(v.keys())[:10]}}}"
    else:
        vshow = str(v)
    print(f"  {k} ({vtype}): {vshow}")

# 9. 分析 displaySetting (3D展示配置)
print("\n" + "=" * 60)
print("9. displaySetting (3D展示配置)")
print("=" * 60)
ds_count = 0
ds_examples = []
for m in models[:50]:
    ci2 = m.get("cate_info", {})
    ds = ci2.get("displaySetting")
    if ds:
        ds_count += 1
        if len(ds_examples) < 3:
            ds_examples.append((m.get("num"), ds))
print(f"  有 displaySetting 的模型数 (前50中): {ds_count}")
for num, ds in ds_examples:
    print(f"\n  模型 {num}:")
    if isinstance(ds, str):
        print(f"    {ds[:300]}")
    else:
        print(f"    {json.dumps(ds, ensure_ascii=False)[:300]}")

# 10. 找120370模型的所有URL字段
print("\n" + "=" * 60)
print("10. 模型 120370 的所有URL字段")
print("=" * 60)
for m in models:
    if str(m.get("num", "")) == "120370":
        url_fields_120370 = {}
        find_urls(m)
        for k, v in m.items():
            if isinstance(v, str) and ("http" in v or ".json" in v or ".png" in v or ".svg" in v):
                url_fields_120370[k] = v
        for k, v in url_fields_120370.items():
            print(f"  {k}: {v[:200]}")
        # modeSetting中的URL
        for i, ms in enumerate(m.get("modeSetting", [])):
            for k2, v2 in ms.items():
                if isinstance(v2, str) and ("http" in v2 or ".png" in v2 or ".jpg" in v2):
                    print(f"  modeSetting[{i}].{k2}: {v2[:200]}")
        break

# 11. 统计哪些模型有3D数据
print("\n" + "=" * 60)
print("11. 3D数据可用性统计")
print("=" * 60)
has_demo = sum(1 for m in models if m.get("demoProjectDataUrl"))
has_knife = sum(1 for m in models if m.get("knife"))
has_image = sum(1 for m in models if m.get("image"))
has_mode = sum(1 for m in models if m.get("modeSetting"))

print(f"  demoProjectDataUrl (3D模型JSON): {has_demo}/{len(models)} ({100*has_demo/len(models):.1f}%)")
print(f"  knife (刀线图): {has_knife}/{len(models)} ({100*has_knife/len(models):.1f}%)")
print(f"  image (预览图): {has_image}/{len(models)} ({100*has_image/len(models):.1f}%)")
print(f"  modeSetting (材质选项): {has_mode}/{len(models)} ({100*has_mode/len(models):.1f}%)")

# 12. 提取所有唯一域名
print("\n" + "=" * 60)
print("12. 所有涉及的域名")
print("=" * 60)
all_domains = set()
for m in models[:200]:  # 采样200条
    for k, v in m.items():
        if isinstance(v, str) and "http" in v:
            match2 = re.match(r'https?://([^/]+)', v)
            if match2:
                all_domains.add(match2.group(1))
    for ms in m.get("modeSetting", []):
        for k2, v2 in ms.items():
            if isinstance(v2, str) and "http" in v2:
                match2 = re.match(r'https?://([^/]+)', v2)
                if match2:
                    all_domains.add(match2.group(1))

for d in sorted(all_domains):
    print(f"  {d}")
