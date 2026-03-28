# 🔧 AGI v13 技能库索引

> 最后更新: 2026-03-26 | 总计: 2,624 技能

---

## 统计概览

| 指标 | 数值 |
|------|------|
| 总 .py 文件 | 2,596 |
| 总 .meta.json 文件 | 2,624 |
| 有实际代码 (>500B) | 1,661 (64%) |
| 占位符/桩 (<500B) | 935 (36%) |

## 按来源分类

| 来源 | 数量 | 说明 |
|------|------|------|
| **GLM-5 自生成** (`glm5_generated`) | 1,475 | 自成长引擎并行推演产出 |
| **碰撞生成** (`collision`) | 854 | 四向碰撞+跨域推演产出 |
| **深度推理** (`deep_reasoning`) | 145 | GLM-5深度推理产出 |
| **知识缺口** (`knowledge_gap`) | 82 | 能力缺口检测→自动填补 |
| **gstack 导入** (`gstack`) | 29 | Garry Tan gstack 工作流技能 |
| **手工编写** (`local`) | 39 | 核心手工技能模块 |

## 核心技能 (手工编写)

| 技能文件 | 功能 | 评分 |
|----------|------|------|
| `code_synthesizer.py` | 迭代式代码合成+自动纠错 | ★★★★☆ |
| `software_engineer.py` | 完整软件工程管线 | ★★★★☆ |
| `codebase_analyzer.py` | AST解析+依赖图+模式识别 | ★★★★☆ |
| `benchmark_test.py` | 5维度15题标准基准测试 | ★★★★☆ |
| `math_formula_engine.py` | 18公式+铁碳相图+形式化 | ★★★★★ |
| `zhipu_ai_caller.py` | 智谱AI多模型调用+校验 | ★★★★☆ |
| `zhipu_growth.py` | 智谱后台自成长+全速推演 | ★★★★★ |
| `openclaw_abilities.py` | MMR重排+时间衰减+查询扩展 | ★★★★★ |
| `bodhi_path.py` | 菩提道果位体系 | ★★★★★ |
| `surpass_engine.py` | 超越引擎6维策略 | ★★★★☆ |
| `harmonic_flexspline_generator.py` | 谐波减速器3D/2D生成 | ★★★★★ |
| `capability_gap_detector.py` | 12规则能力缺口检测 | ★★★★☆ |

## gstack 工作流技能

| 类别 | 技能 |
|------|------|
| **产品** | office-hours, plan-ceo-review, autoplan |
| **工程** | plan-eng-review, review, codex, investigate |
| **设计** | plan-design-review, design-consultation, design-review |
| **QA** | qa, qa-only, benchmark, browse |
| **发布** | ship, land-and-deploy, canary, document-release, setup-deploy |
| **安全** | cso, careful, freeze, guard, unfreeze |

## 框架级技能

| 技能 | 说明 | 优先级 |
|------|------|--------|
| `ulds_v2_九大规律推演框架.meta.json` | ULDS v2.1 十一大规律框架 | P0 (最高) |

## 文件命名规则

- `auto_*.py` / `auto_*.meta.json` — 自成长引擎自动生成
- `gstack_*.meta.json` — gstack 导入 (仅元数据)
- 其他 — 手工编写核心技能
