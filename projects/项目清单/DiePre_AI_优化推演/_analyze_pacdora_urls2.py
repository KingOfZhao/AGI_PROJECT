#!/usr/bin/env python3
"""深入分析 Pacdora URL模式 + 可调节内容 + 页面访问路径"""
import json, re
from collections import Counter, defaultdict

DATA_PATH = "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/推演数据/pacdora_models_full.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

models = raw["data"]

# ====== 1. 详情页URL构造规则验证 ======
print("=" * 70)
print("1. 详情页URL构造规则 (nameKey → 页面地址)")
print("=" * 70)

# 检查 nameKey 是否已经包含 num
namekey_has_num = 0
namekey_no_num = 0
for m in models:
    nk = str(m.get("nameKey", ""))
    num = str(m.get("num", ""))
    if num in nk:
        namekey_has_num += 1
    else:
        namekey_no_num += 1

print(f"  nameKey 包含 num 的模型数: {namekey_has_num}")
print(f"  nameKey 不含 num 的模型数: {namekey_no_num}")

# 验证: 120370的URL
m120370 = None
for m in models:
    if str(m.get("num", "")) == "120370":
        m120370 = m
        break

if m120370:
    nk = m120370["nameKey"]
    num = str(m120370["num"])
    print(f"\n  120370 验证:")
    print(f"    nameKey = {nk}")
    print(f"    用户提供URL = https://www.pacdora.cn/dielines-detail/{nk}")
    print(f"    → 规则: https://www.pacdora.cn/dielines-detail/{{nameKey}}")

# 验证前10个
print(f"\n  前10个模型的详情页URL:")
for m in models[:10]:
    nk = m.get("nameKey", "")
    num = str(m.get("num", ""))
    mnk = m.get("mockupNameKey", "")
    name = m.get("name", "")
    print(f"    刀线页: https://www.pacdora.cn/dielines-detail/{nk}")
    print(f"    样机页: https://www.pacdora.cn/mockup-detail/{mnk}")
    print(f"      [{num}] {name}")
    print()

# ====== 2. 所有可访问的资源URL模板 ======
print("=" * 70)
print("2. Pacdora 完整资源URL模板")
print("=" * 70)
if m120370:
    num = str(m120370["num"])
    nk = m120370["nameKey"]
    mnk = m120370.get("mockupNameKey", "")
    
    print(f"\n  以 120370 为例:")
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │ 资源类型        │ URL模板                         │")
    print(f"  ├─────────────────┼─────────────────────────────────┤")
    print(f"  │ 刀线详情页(SPA) │ https://www.pacdora.cn/dielines-detail/{{nameKey}}")
    print(f"  │                 │ = https://www.pacdora.cn/dielines-detail/{nk}")
    print(f"  │ 样机详情页(SPA) │ https://www.pacdora.cn/mockup-detail/{{mockupNameKey}}")
    print(f"  │                 │ = https://www.pacdora.cn/mockup-detail/{mnk}")
    print(f"  │ 3D模型JSON      │ https://cloud.pacdora.com/demoProject/{{num}}.json")
    print(f"  │                 │ = {m120370.get('demoProjectDataUrl', 'N/A')}")
    print(f"  │ 2D刀线图(PNG)   │ https://oss.pacdora.cn/preview/dieline-{{num}}.png")
    print(f"  │                 │ = {m120370.get('knife', 'N/A')}")
    print(f"  │ 预览图(JPG/PNG) │ https://oss.pacdora.cn/render/{{timestamp}}/{{id}}.png")
    print(f"  │                 │ = {m120370.get('image', 'N/A')}")
    print(f"  │ 材质预览图      │ (modeSetting[i].image)")
    for i, ms in enumerate(m120370.get("modeSetting", [])):
        mat = ms.get("material", "?")
        img = ms.get("image", "N/A")
        print(f"  │   {mat:16s}│ = {img}")
    print(f"  │ 分类渲染图      │ https://oss.pacdora.cn/render/{{date}}/{{num}}.jpg")
    ci = m120370.get("cate_info", {})
    print(f"  │                 │ = {ci.get('image', 'N/A')}")
    print(f"  └─────────────────┴─────────────────────────────────┘")

# ====== 3. 可调节内容分析 ======
print("\n" + "=" * 70)
print("3. 页面可调节内容分析")
print("=" * 70)

# 3a. 尺寸调节
print("\n  3a. 尺寸调节")
print(f"    默认尺寸: L={m120370.get('length')} × W={m120370.get('width')} × H={m120370.get('height')} mm")
size_opts = m120370.get("cate_info", {}).get("size_options", [])
print(f"    size_options: {size_opts if size_opts else '空(自由输入)'}")

# 检查其他模型的size_options
has_size_opts = 0
for m in models:
    so = m.get("cate_info", {}).get("size_options", [])
    if so:
        has_size_opts += 1
print(f"    有预设尺寸选项的模型: {has_size_opts}/{len(models)}")
# 找一个有size_options的
for m in models:
    so = m.get("cate_info", {}).get("size_options", [])
    if so and len(so) > 0:
        print(f"    示例 (模型{m.get('num')}): {json.dumps(so[:3], ensure_ascii=False)[:200]}")
        break

# 3b. 材质调节
print("\n  3b. 材质调节")
# 统计每个模型的材质数量
mat_counts = Counter()
for m in models:
    ms = m.get("modeSetting", [])
    mat_counts[len(ms)] += 1
print(f"    材质选项数量分布:")
for cnt, num in sorted(mat_counts.items()):
    print(f"      {cnt}种材质: {num}个模型")

# 120370的材质详情
print(f"\n    120370的材质选项:")
for ms in m120370.get("modeSetting", []):
    print(f"      material: {ms.get('material')}")
    print(f"      coverType: {ms.get('coverType', 'N/A')}")
    print(f"      suggestColor: {ms.get('suggestColor', 'N/A')}")
    print(f"      image: {ms.get('image', 'N/A')[:100]}")
    # 打印所有其他字段
    for k, v in ms.items():
        if k not in ('material', 'coverType', 'suggestColor', 'image'):
            print(f"      {k}: {v}")
    print()

# 3c. def_science_id (工艺/科学ID)
print("\n  3c. def_science_id (工艺配置)")
sci_ids = Counter()
for m in models:
    sid = m.get("def_science_id", "N/A")
    sci_ids[sid] += 1
print(f"    def_science_id 分布:")
for sid, cnt in sci_ids.most_common(10):
    print(f"      {sid}: {cnt}个模型")

# 3d. complex_type
print("\n  3d. complex_type (复杂度类型)")
ct_counts = Counter()
for m in models:
    ct = m.get("cate_info", {}).get("complex_type", "N/A")
    ct_counts[ct] += 1
for ct, cnt in ct_counts.most_common(10):
    print(f"      {ct}: {cnt}个模型")

# 3e. elaborate
print("\n  3e. elaborate (精细度)")
elab_counts = Counter()
for m in models:
    el = m.get("cate_info", {}).get("elaborate", "N/A")
    elab_counts[el] += 1
for el, cnt in elab_counts.most_common(10):
    print(f"      {el}: {cnt}个模型")

# 3f. edition
print("\n  3f. edition (版本)")
ed_counts = Counter()
for m in models:
    ed = m.get("cate_info", {}).get("edition", "N/A")
    ed_counts[ed] += 1
for ed, cnt in ed_counts.most_common(10):
    print(f"      {ed}: {cnt}个模型")

# ====== 4. 批量访问策略 ======
print("\n" + "=" * 70)
print("4. 批量访问策略")
print("=" * 70)

# 有3D数据的模型
models_with_3d = [m for m in models if m.get("demoProjectDataUrl")]
print(f"\n  有3D模型JSON的: {len(models_with_3d)}/5969")

# 按 use_count 排序
models_with_3d_sorted = sorted(models_with_3d, key=lambda x: x.get("use_count", 0), reverse=True)
print(f"\n  热门3D模型 TOP 20 (按use_count):")
for i, m in enumerate(models_with_3d_sorted[:20]):
    num = m.get("num")
    name = m.get("name", "")
    uc = m.get("use_count", 0)
    nk = m.get("nameKey", "")
    demo = m.get("demoProjectDataUrl", "")
    ms_count = len(m.get("modeSetting", []))
    print(f"    {i+1:2d}. [{num}] {name}")
    print(f"        use_count={uc}, 材质={ms_count}种")
    print(f"        刀线页: /dielines-detail/{nk}")
    print(f"        3D JSON: {demo}")
    print()

# 没有3D但有刀线的模型数
no_3d = [m for m in models if not m.get("demoProjectDataUrl") and m.get("knife")]
print(f"\n  无3D但有2D刀线的: {len(no_3d)}")
print(f"  完全无3D无刀线的: {len(models) - len(models_with_3d) - len(no_3d)}")

# ====== 5. 3D JSON 内容结构 (从已下载的120370分析) ======
print("\n" + "=" * 70)
print("5. demoProjectDataUrl 返回的3D JSON结构要点")
print("=" * 70)
print("""
  每个 {num}.json 返回 Three.js Object3D.toJSON() 格式:
  {
    "metadata": {"version": 4.5, "type": "Object", "generator": "Object3D.toJSON"},
    "geometries": [
      // ExtrudeGeometry 数组 - 每个面板一个
      {"uuid": "...", "type": "ExtrudeGeometry", 
       "shapes": ["Shape UUID"],
       "options": {"depth": 0.5, "bevelEnabled": false}}
    ],
    "materials": [
      // MeshPhysicalMaterial - 外面/内面各一个
      {"uuid": "...", "type": "MeshPhysicalMaterial",
       "roughness": 1, "metalness": 0, "clearcoat": 0,
       "map": "outsideCanvasTexture UUID"}
    ],
    "textures": [
      // CanvasTexture - outside + inside
      {"uuid": "...", "name": "outsideCanvasTexture"},
      {"uuid": "...", "name": "insideCanvasTexture"}
    ],
    "shapes": [
      // Shape 定义 2D轮廓
      {"uuid": "...", "type": "Shape",
       "curves": [
         {"type": "LineCurve", "v1": [x1,y1], "v2": [x2,y2]},
         {"type": "EllipseCurve", "aX": cx, "aY": cy, ...}
       ]}
    ],
    "object": {
      // 场景树 - 包含所有面板的层级关系
      "type": "Scene",
      "children": [
        {"type": "AmbientLight", "intensity": 0.7},
        {"type": "DirectionalLight", "intensity": 0.35},
        {"type": "Mesh", "name": "B", // 底板
         "geometry": "ExtrudeGeometry UUID",
         "material": ["outsideMat", "insideMat", "outsideMat"],
         "children": [
           {"type": "Mesh", "name": "B_BL", // 铰链
            "children": [
              {"type": "Mesh", "name": "BL", // 左侧壁
               "children": [...]} // 递归子面板
            ]}
         ]}
      ]
    },
    "totalX": 442, // 2D展开总宽(mm)
    "totalY": 443  // 2D展开总高(mm)
  }
""")

# ====== 6. 页面SPA加载流程推测 ======
print("=" * 70)
print("6. 页面SPA加载流程推测 (从数据结构逆向)")
print("=" * 70)
print("""
  用户访问: https://www.pacdora.cn/dielines-detail/{nameKey}
  
  SPA加载流程:
  1. 前端路由解析 nameKey → 提取 num (末尾数字)
  2. API请求 → 获取模型元数据 (等同 pacdora_models_full.json 中的单条)
     - 包含: name, L/W/H, modeSetting, cate_info, keywords等
  3. 加载 demoProjectDataUrl → fetch('https://cloud.pacdora.com/demoProject/{num}.json')
     - 获取完整 Three.js 场景JSON
  4. 加载 knife → <img src="https://oss.pacdora.cn/preview/dieline-{num}.png">
     - 2D刀线图静态预览
  5. 渲染 3D 场景:
     - THREE.ObjectLoader.parse(json) → 还原整个场景树
     - 添加 OrbitControls 交互
     - 绑定材质切换 (modeSetting[i].material)
  6. 用户可调节:
     - L/W/H 尺寸 → 重新生成 Shape 路径 → 重建 ExtrudeGeometry
     - 材质切换 → 替换 MeshPhysicalMaterial 参数
     - 颜色修改 → 更新 CanvasTexture
     - 印刷设计 → 编辑 outsideCanvasTexture → 实时映射到3D面
  
  关键API端点(推测):
  - GET /api/model/{num}              → 模型元数据
  - GET /demoProject/{num}.json       → 3D场景JSON (cloud.pacdora.com)
  - GET /preview/dieline-{num}.png    → 2D刀线图 (oss.pacdora.cn)
  - GET /preview/mockup-{num}.jpg     → 预览图 (oss.pacdora.cn)
  - GET /render/{ts}/{id}.png         → 材质渲染图 (oss.pacdora.cn)
""")
