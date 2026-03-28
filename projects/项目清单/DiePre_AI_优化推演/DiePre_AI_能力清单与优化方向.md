# DiePre AI 能力清单·优化方向·最终目标

> 生成时间: 2026-03-26
> 方法论: 管理制度推演·六向碰撞+反贼检测+王朝循环制
> 推演配置: 2循环 × 5轮

---

## 一、项目概述

**DiePre AI** — 智能包装刀模设计系统
- 路径: `/Users/administruter/Desktop/DiePre AI`
- 核心能力: 从2D刀模图→3D成品预览, 含误差预测、材料选择、工序推演
- 技术栈: Vue3 + Three.js + FastAPI + SQLAlchemy + SQLite

---

## 二、当前能力清单 (已实现)

### 2.1 核心引擎 (后端Python)

| # | 模块 | 文件 | 能力 | 成熟度 |
|---|------|------|------|--------|
| E1 | RSS误差引擎 | rss_engine.py | RSS误差堆叠计算(F4公式), 9大误差源 | ★★★★☆ |
| E2 | 箱压引擎 | impact_engine.py | McKee BCT计算(S13), 堆码预测 | ★★★★☆ |
| E3 | 工序链引擎 | process_chain_engine.py | 5大工序推演, 12条固定规则 | ★★★☆☆ |
| E4 | 风险扫描器 | risk_scanner.py | 35类灾难风险检测 | ★★★★☆ |
| E5 | 标准参数库 | standard_params.py | FEFCO盒型 + 材料属性 | ★★★☆☆ |

### 2.2 前端 (Vue3)

| # | 模块 | 文件 | 能力 | 成熟度 |
|---|------|------|------|--------|
| F1 | 参数化设计 | ParametricDesign.vue | 2D/3D视图切换 (Three.js+Konva) | ★★★☆☆ |
| F2 | 2D编辑器 | BoxEditor | Fabric.js 2D编辑 | ★★★☆☆ |
| F3 | 材料选择 | 基础下拉 | 简单材料选择 | ★★☆☆☆ |
| F4 | 状态管理 | Pinia | 全局状态 | ★★★★☆ |

### 2.3 后端API (FastAPI)

| # | 端点 | 能力 | 成熟度 |
|---|------|------|--------|
| A1 | /api/reasoning/rss | RSS误差计算 | ★★★★☆ |
| A2 | /api/reasoning/risk-scan | 35类风险扫描 | ★★★★☆ |
| A3 | /api/reasoning/nesting | 嵌套公差计算 | ★★★☆☆ |
| A4 | /api/reasoning/process-chain | 工序链推演 | ★★★☆☆ |

### 2.4 数据层

| # | 组件 | 状态 |
|---|------|------|
| D1 | SQLite | 803MB单文件, 无迁移系统 |
| D2 | 材料数据 | 散落3处(standard_params/seed_data/impact_engine) |
| D3 | FEFCO盒型 | 仅6种(0201/0203/0401/0409/0421/0713), 缺完整编码 |

---

## 三、固定框架 (不可违背)

### 3.1 物理定律 (15条)
- F1 Gaussian曲率K=0 (3D→2D展开约束)
- F2 面积守恒
- F3 Haga折叠定理
- F4 RSS误差堆叠 e=√(Σeᵢ²) **[已实现]**
- F5 Kelvin-Voigt蠕变
- F6 Euler柱屈曲 **[已实现: impact_engine]**
- F7 复合梁理论
- F8 Hooke弹性定律
- F9 Fick扩散
- F10 Kirsch应力集中
- F11 Coffin-Manson疲劳
- F12 WLF时温等效
- F13 弹性回弹 Δθ=3σyR/(Et)
- F14 热力学第二定律
- F15 弯曲补偿 BA=π(R+kt)θ/180

### 3.2 行业标准 (20条)
- S1 FEFCO Code 12th **[部分实现: 仅6种]**
- S2 ECMA折叠纸盒
- S3 IADD钢规公差±0.254mm
- S4-S20 (详见推演报告)

### 3.3 工序固定规则 (12条)
- P1-P12 (详见推演报告)

---

## 四、优化方向 (六向碰撞)

### 方向1: 物理定律合规 → 补全缺失公式
| 优化项 | 当前 | 目标 | 优先级 |
|--------|------|------|--------|
| 15条物理定律编码 | 3/15已实现 | 15/15全部编码到引擎 | P1 |
| 3D展开K=0校验 | 缺失 | unfold_engine.py实现 | P1 |
| 蠕变/疲劳预测 | 缺失 | 堆码+反复折叠寿命预测 | P2 |

### 方向2: 行业标准覆盖 → 完整FEFCO+合规检查
| 优化项 | 当前 | 目标 | 优先级 |
|--------|------|------|--------|
| FEFCO盒型扩展 | 6种 | ~80种完整编码 | P0 |
| 标准合规检查器 | 缺失 | 自动校验20条标准 | P1 |
| McKee BCT增强 | 基础 | 含MC衰减+老化系数 | P1 |

### 方向3: 工艺链优化 → 动态工厂参数
| 优化项 | 当前 | 目标 | 优先级 |
|--------|------|------|--------|
| 工厂profile | 硬编码 | machines表+动态参数 | P0 |
| 工序可视化 | 缺失 | ProcessChain.vue | P1 |
| 刀模磨损追踪 | 缺失 | machine_wear_logs表 | P2 |

### 方向4: 3D⇄2D引擎 → 真实厚度+双向同步
| 优化项 | 当前 | 目标 | 优先级 |
|--------|------|------|--------|
| 3D面板厚度 | 0厚度面片 | ExtrudeGeometry真实厚度 | P0 |
| 误差带可视化 | 缺失 | 半透明红色Box实时显示 | P0 |
| 折叠动画 | 缺失 | GSAP补间+折痕旋转轴 | P1 |
| 2D⇄3D双向同步 | 缺失 | 编辑2D→3D更新, 拖3D→2D跟随 | P1 |
| 装配模拟 | 完全缺失 | 碰撞检测+间隙可视化 | P1 |

### 方向5: 系统架构 → 统一数据源+实时计算
| 优化项 | 当前 | 目标 | 优先级 |
|--------|------|------|--------|
| 材料数据统一 | 散落3处 | material_db_service.py单一源 | P0 |
| 2D引擎统一 | Fabric+Konva | 统一Konva | P1 |
| 误差实时计算 | 手动触发 | WebSocket+debounce 60fps | P0 |
| DB迁移系统 | 无 | Alembic初始化 | P0 |
| PostgreSQL | SQLite 803MB | 并发+JSONB+全文搜索 | P2 |

### 方向6: 推翻重建 → 消灭8个已知反贼
| 反贼 | 类型 | 严重度 | 修复方案 |
|------|------|--------|---------|
| R1 2D/3D引擎割裂 | info_loss | 🔴高 | Konva(2D)+Three(3D)+Pinia共享 |
| R2 误差非实时 | latency | 🔴高 | WebSocket+debounce |
| R3 材料散落 | data_silo | 🟡中 | 统一material_db |
| R4 无工厂profile | unmapped | 🟡中 | machines表 |
| R5 3D无厚度 | render_gap | 🔴高 | ExtrudeGeometry |
| R6 无装配模拟 | unmapped | 🟡中 | Assembly模块 |
| R7 DB单点 | scalability | 🟠低 | PostgreSQL |
| R8 无离线计算 | rigidity | 🟠低 | WASM |

---

## 五、最终目标

### 5.1 短期目标 (P0, 1-2周)
- [ ] 材料数据统一为 `material_db_service.py`
- [ ] `ErrorBudgetPanel.vue` — RSS滑块 + 3D实时联动
- [ ] `MaterialCascader.vue` — 级联材料选择器
- [ ] 3D面板厚度渲染 (ExtrudeGeometry)
- [ ] Alembic迁移系统初始化
- [ ] FEFCO盒型扩展至完整编码 (~80种)
- [ ] WebSocket误差实时推送

### 5.2 中期目标 (P1, 3-4周)
- [ ] `ProcessChain.vue` — 工序链可视化
- [ ] `InternalStructure.vue` — 内结构设计器
- [ ] `AssemblyValidator.vue` — 装配碰撞检测+间隙动画
- [ ] unfold_engine.py — 3D→2D展开 (K=0约束)
- [ ] fold_engine.py — 2D→3D折叠 (材料厚度+补偿)
- [ ] GSAP折叠动画
- [ ] 2D⇄3D双向同步编辑
- [ ] machines表 + 工厂profile API
- [ ] 标准合规检查器 (20条)

### 5.3 长期目标 (P2, 5-8周)
- [ ] `RiskHeatmap.vue` — 35类灾难热力图
- [ ] PostgreSQL迁移
- [ ] MC变化间隙动态模拟
- [ ] WASM前端离线计算
- [ ] 蠕变/疲劳寿命预测引擎
- [ ] 多用户协作
- [ ] 国际化 (中/英/日/德)

### 5.4 终极目标
> **用户选择材料+盒型+工艺 → 自动生成2D刀模图 → 实时3D折叠预览 → RSS误差带可视化 → 滑块调节参数 → 一键导出生产DXF**
>
> 覆盖: 15条物理定律 + 20条行业标准 + 12条工序规则 = **47条硬约束全部编码**
> 材料: 10大类51种 + FEFCO ~80种盒型 = **穷举选择, 不允许自由输入**
> 精度: RSS误差<1mm (3σ置信度99.73%)
> 响应: 滑块→3D更新 <100ms (60fps)

---

## 六、推演执行记录

本文件由 `diepre_optimization_engine.py` 生成的推演报告补充。
推演命令: `python3 diepre_optimization_engine.py --cycles 2 --rounds 5`
