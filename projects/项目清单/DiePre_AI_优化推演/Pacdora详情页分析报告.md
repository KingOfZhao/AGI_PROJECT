# Pacdora 刀版详情页深度分析报告

> 分析对象: `https://www.pacdora.cn/dielines-detail/custom-dimensions-back-open-boxes-auto-bottome-snap-lock-dieline-103012`
> 数据来源: 完整渲染后的 HTML DOM + pacdora_models_full.json (5969模型) + demoProject JSON (Three.js 3D场景数据)
> 分析目的: 提取页面元素和呈现方式, 用于优化 DiePre AI 刀模设计项目

---

## 一、页面整体架构

```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo + 刀版生成器 │ 保存 │ 在线设计 │ 分享 │ 下载刀版  │
├──────────┬──────────────────────────────────────────────┤
│ 左侧面板  │              主内容区                         │
│          │  ┌────────────────────────────────────┐      │
│ [样机]    │  │                                    │      │
│ [基础] ◀  │  │      2D 刀版图 (D3.js SVG)         │      │
│ [高级]    │  │      + 图例(出血/割/折线)            │      │
│ [更多]    │  │      + 尺寸标注                     │      │
│          │  │                                    │      │
│ ─────── │  └────────────────────────────────────┘      │
│ 自定义尺寸 │  ┌────────────────────────────────────┐      │
│  长/宽/高  │  │                                    │      │
│ 自定义厚度 │  │      3D 预览 (Three.js WebGL)       │      │
│ 选择材质   │  │      可旋转/缩放交互                 │      │
│ 尺寸类型   │  │                                    │      │
│          │  └────────────────────────────────────┘      │
│ [ℹ️ 信息] │                                             │
└──────────┴──────────────────────────────────────────────┘
```

**技术栈**: Vue 3 SPA + Vue Router + Three.js + D3.js + OpenType.js + AWS SDK + Lottie

---

## 二、页面元素逐项分析

### 2.1 顶部导航栏 (Header)

| 元素 | 实现方式 | GTM埋点 | DiePre可借鉴 |
|------|---------|---------|-------------|
| Logo + "刀版生成器" | `p-icon-logo-icon` + 文字 | `ga-pacdora_home` | ✅ 品牌标识+功能定位 |
| 汉堡菜单(移动端) | `pac-popover-menu` 弹出 | `ga-dieline_dieline_menu_more` | ✅ 响应式设计 |
| 保存按钮 | Lottie SVG动画(云+勾) | `ga-dieline_dieline_save` | ✅ 微动画反馈 |
| 在线设计(跳转3D编辑器) | `<a>` 外链 + 箭头图标 | `ga-dieline_dieline_3Ddesign_choose` | ⭐ 核心转化入口 |
| 分享按钮 | `p-icon-scene-share2` | `ga-dieline_dieline_share` | ✅ 社交传播 |
| 导出历史 | Popover弹出 + Lottie | `ga-dieline_dieline_history_choose` | ✅ 版本管理 |
| 下载刀版 | 金色会员徽章 + 按钮 | `ga-dieline_dieline_generator_export` | ⭐ 付费转化核心 |

**关键发现**: 下载按钮旁有 `pac-member` 会员徽章(金色边框 `#E69833`), 暗示下载是付费功能。

### 2.2 左侧面板 — 四大功能Tab

```
┌──────────┐
│ 📦 样机   │ → 3D样机预览/选择
│ 📐 基础 ◀ │ → 尺寸/材质/厚度 (默认激活)
│ ⚙️ 高级   │ → 高级参数设置
│ ➕ 更多   │ → 扩展工具
│ ─分隔线─  │
│ ℹ️ 信息   │ → 盒型信息说明
└──────────┘
```

### 2.3 基础面板 — 核心参数控制 ⭐

#### A. 自定义尺寸 (Custom Dimensions)

```html
自定义尺寸 ℹ️  [mm | in]    ← 单位切换
├── 长度: [___] mm           ← 数值输入
├── 宽度: [___] mm           ← 数值输入
└── 高度: [___] mm           ← 数值输入
```

- **单位切换**: mm/in 双制式, 埋点 `ga-dieline_dieline_basic_mm` / `ga-dieline_dieline_basic_in`
- **输入框**: `p-input-box` 组件, autocomplete=new-password 防浏览器自动填充
- **信息提示**: 每个标题旁有 `p-icon-packaging-info` 帮助图标

#### B. 自定义厚度 (Custom Thickness)

```
自定义厚度
(0.2~3mm)              ← 明确的范围约束
[-] [___] [+]          ← 步进控制器
```

- **范围约束显示**: `thickness-range` 组件显示 (0.2~3mm)
- **步进器**: `number-control` 带 ± 按钮
- 埋点: `ga-dieline_dieline_basic_thickness_modify`

#### C. 选择材质 (Material Select)

```
选择材质 ℹ️
┌─────────────────────┐
│ 🖼️ 白卡纸          ▼ │  ← 图片+文字下拉选择
└─────────────────────┘
```

- **实现**: `tree-select-box` 树形下拉组件
- **材质图片**: `//cdn.baoxiaohe.com/...jpg?imageView2/2/w/128/h/128|imageslim` (七牛云图片处理)
- **已知材质** (来自JSON分析): `WHITE_BOARD`(白卡纸), `FLUTE`(瓦楞纸), `KRAFT`(牛皮纸) 等

#### D. 尺寸类型 (Size Mode)

```
尺寸类型 ℹ️
[制造尺寸 ✓] [内尺寸] [外尺寸]   ← 三选一切换
```

- **三种模式**: 制造尺寸(默认) / 内尺寸 / 外尺寸
- 每个模式有 loading 状态(切换时重新计算)
- 埋点: `ga-dieline_dieline_basic_manufacture` / `_inner` / `_outer`

### 2.4 主内容区 — 2D刀版图

#### A. 图例系统 (Legend)

```
━━ 出血线 (Bleed)    #46BA00 绿色
━━ 割线   (Cut)      #2028B0 蓝色
━━ 折线   (Fold)     #FA0000 红色
```

#### B. 尺寸信息展示

```
制造尺寸: 120.6 × 60.6 × 161.6 mm
```

- 使用 `size_diff` 组件同时显示不同尺寸类型的数值

#### C. 2D渲染技术

- **D3.js** (`UseD3-6794b65024.js`) 用于2D刀版SVG渲染
- **knifeEffect** (`knifeEffect-dd37f2ace3.js`) 刀版效果处理
- 渲染管线: `useRender` → `render` → `Dieline` → `Calc`

### 2.5 3D预览区 (从JS模块推断)

基于 `demoProjectDataUrl` (如 `https://cloud.pacdora.com/demoProject/103012.json`) 的Three.js场景:

#### 3D场景数据结构 (已分析):

```
totalX: 377.9mm    totalY: 282.75mm    ← 刀版总尺寸

Panel Hierarchy (面板层级):
F (正面)
├── F_FL (铰链) → FL (左侧面)
│   ├── FL_H (铰链) → H (背面)
│   │   ├── H_HL (铰链) → HL (背面左)
│   │   ├── H_HB → HB (背面底盖)
│   │   └── H_HT2 → HT2 → HT2_HT1 → HT1 (背面顶盖)
│   ├── FL_FLB → FLB (左侧底盖)
│   └── FL_FLT → FLT (左侧顶盖)
├── F_FR (铰链) → FR (右侧面)
│   ├── FR_FRB → FRB (右侧底盖)
│   └── FR_FRT → FRT (右侧顶盖)
├── F_FB → FB (正面底盖)
└── F_FT2 → FT2 → FT2_FT1 → FT1 (正面顶盖)
```

#### 面板命名规则:

| 缩写 | 含义 | 英文 |
|------|------|------|
| F | 正面 | Front |
| H | 背面 | Back (Hidden) |
| FL | 左前 | Front-Left |
| FR | 右前 | Front-Right |
| HL | 左后 | Hidden-Left |
| FB/HB | 底盖 | Front/Hidden Bottom |
| FT/HT | 顶盖 | Front/Hidden Top |
| FT1/FT2 | 顶盖嵌套层 | Top layer 1/2 |

#### 3D技术实现:

| 要素 | 实现 |
|------|------|
| 面板几何 | `ExtrudeGeometry` + 2D Shape (depth=0.5mm) |
| 折痕线 | `ExtrudeGeometry` + `LineCurve3` 路径挤压 (截面r=0.26mm EllipseCurve) |
| 2D曲线类型 | `LineCurve`, `QuadraticBezierCurve`, `EllipseCurve` |
| 材质 | `MeshPhysicalMaterial` (outside + inside 双面) |
| 贴图 | Canvas纹理 (outsideCanvasTexture / insideCanvasTexture) |
| 折叠动画 | 父子mesh层级旋转变换 |
| 灯光 | `useLight` 模块控制 |

### 2.6 导出/付费模块

| 模块 | JS文件 | 说明 |
|------|--------|------|
| 导出效果 | `exportEffect.js` | 文件导出流程 |
| 分辨率 | `resolutionEffect.js` | 输出分辨率控制 |
| 导出对话框 | `ExportDialog.js` | 导出设置弹窗 |
| 导出按钮组 | `ExportButtonGroup.js` | 导出选项(PDF/SVG/AI等) |
| 导出历史 | `ExportHistory.js` | 历史记录管理 |
| 付费模块 | `payEffect.js` / `pacdora-pay.js` | 支付集成 |
| 会员模块 | `Member.js` | 会员等级/权益 |

### 2.7 数据追踪体系

```
GTM (GTM-K44XR23)
├── Google Analytics (G-S00MVCP2JL)
├── Google Ads (AW-10837261960)
├── Facebook Pixel (1153990526532119)
├── Microsoft Clarity (lfd0xwuav7)
├── Zoho SalesIQ (客服系统)
└── Apollo (销售追踪)
```

**埋点命名规则**: `ga-dieline_dieline_{功能区}_{操作}`, 覆盖所有核心交互。

---

## 三、URL生成规则 (已验证)

```
详情页: https://www.pacdora.cn/dielines-detail/{nameKey}
样机页: https://www.pacdora.cn/mockup-detail/{mockupNameKey}
3D数据: https://cloud.pacdora.com/demoProject/{num}.json
刀版图: https://oss.pacdora.cn/preview/dieline-{num}.png
预览图: https://oss.pacdora.cn/preview/mockup-{num}.jpg
```

**nameKey 格式**: `custom-dimensions-{盒型英文描述}-dieline-{num}`
**mockupNameKey 格式**: `{盒型英文描述}-mockup-{num}`

---

## 四、DiePre AI 可借鉴的核心元素 ⭐

### 4.1 参数化设计系统 (Priority: P0)

**Pacdora做法**:
- 三维尺寸(长/宽/高) + 厚度 + 材质 = 自动生成刀版
- 三种尺寸模式(制造/内/外)自动换算
- 厚度范围约束 (0.2~3mm) 硬限制

**DiePre AI 优化方向**:
```
F→V→F 链式映射:
  F₀(物理约束: 0.2≤厚度≤3mm)
  → V₁(用户输入: 长/宽/高/材质)
  → F₁(材质→误差区间[εmin,εmax]锁定)
  → V₂(尺寸类型选择: 制造/内/外)
  → F₂(自动换算: 内尺寸 = 制造尺寸 - 2×厚度)
  → 生成刀版
```

**Pacdora缺失 → DiePre AI的护城河**:
- ❌ Pacdora无负载计算 → DiePre 有 [Fmin, Fmax] 承载区间
- ❌ Pacdora无误差传播 → DiePre 有全链路误差追踪
- ❌ Pacdora无工艺参数 → DiePre 有压痕/粘合/模切工艺约束

### 4.2 材质系统 (Priority: P0)

**Pacdora做法**:
- 图片+文字的树形下拉选择
- 材质图片托管在 CDN (七牛云 baoxiaohe.com)
- 材质类型: WHITE_BOARD / FLUTE / KRAFT 等
- `modeSetting` 为每种材质提供不同预览渲染

**DiePre AI 优化方向**:
```python
# Pacdora的材质仅影响外观, DiePre的材质直接影响工程约束
MATERIAL_CONSTRAINTS = {
    "WHITE_BOARD": {  # 白卡纸
        "thickness_range": (0.3, 1.5),     # mm
        "tolerance": (0.1, 0.3),           # mm 误差
        "load_factor": 0.6,                # 相对承载系数
        "crease_width": "1.5×thickness",   # 压痕宽度公式
        "grain_direction": "required",      # 需要纹理方向
    },
    "FLUTE": {  # 瓦楞纸
        "thickness_range": (1.0, 5.0),
        "tolerance": (0.5, 1.5),
        "load_factor": 1.0,
        "crease_width": "2.0×thickness",
        "grain_direction": "critical",
    },
}
```

### 4.3 2D刀版渲染 — 三线系统 (Priority: P1)

**Pacdora做法**:
| 线型 | 颜色 | 用途 |
|------|------|------|
| 出血线 | #46BA00 绿 | 印刷出血范围 |
| 割线 | #2028B0 蓝 | 模切切割线 |
| 折线 | #FA0000 红 | 压痕折叠线 |

**DiePre AI 扩展方向**:
```
DiePre应增加:
├── 粘合区域线 (Glue flap)    → 粘合工艺约束区域
├── 标注线 (Dimension)        → 关键尺寸标注
├── 纹理方向标记 (Grain)       → 纤维方向(影响折叠质量)
├── 危险区域高亮 (Risk zone)   → 误差累积超限区域
└── 负载路径线 (Load path)     → 结构承载路径可视化
```

### 4.4 3D面板层级与折叠系统 (Priority: P1)

**Pacdora做法**:
- 标准化面板命名: F/FL/FR/H/HL/HR/FB/HB/FT/HT
- 父→铰链(hinge)→子 的层级结构定义折叠顺序
- 折叠通过旋转矩阵变换实现

**DiePre AI 优化方向**:
```
DiePre 3D系统应包含:
1. 面板层级 (与Pacdora相同) → 可直接复用命名规则
2. 折叠顺序约束 → 某些面板必须先折(如底盖先于侧面)
3. 干涉检测 → 折叠过程中面板碰撞检测
4. 应力分析可视化 → 折痕处的应力分布
5. 动态折叠动画 → 用户可拖拽控制折叠角度
```

### 4.5 尺寸换算引擎 (Priority: P1)

**Pacdora做法**:
- 制造尺寸 / 内尺寸 / 外尺寸 三种模式
- 切换时有 loading 状态(实时重算)
- mm/in 双制式支持

**DiePre AI 优化方向**:
```
换算公式体系 (Pacdora只做简单换算, DiePre做全链路):
  外尺寸 = 内尺寸 + 2×材料厚度 + 2×误差
  制造尺寸 = 外尺寸 + 出血量 + 模切补偿
  刀版尺寸 = 制造尺寸 + 连接片 + 粘合片

DiePre独有:
  有效内容积 = 内尺寸 - 包装内衬厚度
  最大承载重量 = f(材质, 结构, 有效内容积)
  材料利用率 = 刀版面积 / 原材料板面积
```

### 4.6 交互设计模式 (Priority: P2)

**值得借鉴的UX模式**:

1. **参数→预览实时联动**: 修改任何参数 → 2D+3D同步更新
2. **渐进式披露**: 基础(默认) → 高级 → 更多, 避免信息过载
3. **微动画反馈**: 保存按钮用Lottie动画, 提升感知品质
4. **双视图对照**: 2D刀版 + 3D预览 同屏, 直观理解平面→立体映射
5. **约束可见性**: 厚度范围(0.2~3mm)直接显示, 用户不会输入无效值
6. **信息提示ℹ️**: 每个参数旁有帮助图标, 降低学习成本

### 4.7 数据资产 (Priority: P2)

**Pacdora数据规模** (来自JSON分析):
- **5969** 个盒型模型
- **覆盖材质**: WHITE_BOARD, FLUTE, KRAFT 等
- **尺寸范围**: L 20-1000mm, W 20-800mm, H 10-600mm
- **FEFCO编码覆盖**: 50+ 种国际标准盒型
- **3D数据**: 100% 覆盖率 (每个模型都有 demoProjectDataUrl)
- **刀版图**: 100% 覆盖率 (每个模型都有 knife PNG)

**DiePre AI 数据策略**:
```
可从Pacdora学习的数据维度:
1. 盒型分类体系 (class1/class2 编码)
2. 面板命名标准化 (F/FL/FR/H/HL等)
3. 3D形状定义规范 (Shape curves → dieline geometry)
4. 材质→渲染参数映射 (modeSetting)

DiePre独有数据维度:
1. 误差数据库 (每种材质×工艺的实测误差)
2. 负载数据库 (结构→承载能力映射)
3. 灾难知识库 (35种失败模式)
4. 工厂校准数据 (机器特定补偿值)
```

---

## 五、Pacdora vs DiePre AI 对比矩阵

| 维度 | Pacdora | DiePre AI (目标) | 差异化 |
|------|---------|-----------------|--------|
| **2D刀版** | ✅ D3.js SVG渲染 | ✅ 需实现 | 相同起点 |
| **3D预览** | ✅ Three.js WebGL | ✅ 需实现 | 相同起点 |
| **参数化设计** | ✅ 长/宽/高/厚/材质 | ✅ + 工艺参数 | DiePre更全 |
| **尺寸换算** | ✅ 制造/内/外 | ✅ + 误差传播 | DiePre更精 |
| **材质系统** | ✅ 外观切换 | ✅ + 工程约束 | **DiePre核心优势** |
| **误差计算** | ❌ | ✅ 全链路 | **DiePre独有** |
| **负载分析** | ❌ | ✅ F→V→F链 | **DiePre独有** |
| **工艺约束** | ❌ | ✅ 压痕/粘合/模切 | **DiePre独有** |
| **灾难预警** | ❌ | ✅ 35种失败模式 | **DiePre独有** |
| **数据量** | 5969盒型 | 起步阶段 | Pacdora领先 |
| **国际标准** | ✅ FEFCO覆盖 | ✅ 需对齐 | 需补齐 |
| **导出格式** | PDF/SVG/AI等 | 需实现 | 需对标 |
| **付费模式** | 下载付费+会员 | TBD | 需规划 |

---

## 六、优先实施路线图

### Phase 1: 基础对标 (与Pacdora功能对齐)
1. **参数化刀版生成器** — 长/宽/高/厚度/材质 → 2D刀版
2. **三线系统** — 出血线/割线/折线的标准渲染
3. **尺寸三模式** — 制造/内/外尺寸自动换算
4. **面板命名标准化** — 采用F/FL/FR/H/HL等国际通用命名

### Phase 2: 差异化超越 (DiePre护城河)
5. **F→V→F约束引擎** — 材质→误差区间→负载区间全链路
6. **扩展线型系统** — 粘合区/纹理方向/危险区域/负载路径
7. **工艺参数集成** — 压痕宽度公式/模切补偿/粘合工艺
8. **灾难预警系统** — 35种失败模式实时检测

### Phase 3: 3D可视化 (体验升级)
9. **Three.js 3D渲染** — 可参考Pacdora的面板层级+折叠动画
10. **应力分析可视化** — 折痕应力分布热力图
11. **干涉检测** — 折叠过程碰撞检测
12. **材料利用率优化** — 排版建议

---

## 七、从Pacdora 3D数据中可直接提取的技术资产

### 7.1 Shape曲线定义规范

Pacdora的每个面板由Shape曲线定义, 使用三种基本曲线:
- `LineCurve` — 直线段
- `QuadraticBezierCurve` — 二次贝塞尔曲线(圆角/弧形)
- `EllipseCurve` — 椭圆弧(折痕截面: r=0.26mm)

### 7.2 折痕线几何标准

```json
{
  "type": "ExtrudeGeometry",
  "shapes": ["EllipseCurve: aX=0, aY=0, xR=0.26, yR=0.26"],
  "options": {
    "extrudePath": "LineCurve3: 折痕长度",
    "bevelEnabled": false
  }
}
```
→ **折痕宽度标准: 直径0.52mm** (Pacdora默认值)

### 7.3 材质渲染参数

```json
{
  "outsideMaterial": {
    "type": "MeshPhysicalMaterial",
    "roughness": 1,    // 完全粗糙(纸质感)
    "metalness": 0,     // 无金属感
    "clearcoat": 0,     // 无清漆层
    "reflectivity": 0.5 // 中等反射
  }
}
```

---

## 八、总结

### Pacdora的核心价值: **2D→3D可视化 + 海量盒型库**
### DiePre AI的核心价值: **全链路F→V→F约束传播 + 工程精度 + 灾难预防**

Pacdora解决的是 "看到" 的问题(设计预览),
DiePre AI解决的是 "做到" 的问题(制造可行性 + 质量保证)。

**两者是互补关系**: DiePre AI可以在前端参考Pacdora的交互模式和可视化方式,
但在后端引擎上走完全不同的路径 — 从物理约束出发, 通过链式收敛保证每一步设计决策的工程有效性。
