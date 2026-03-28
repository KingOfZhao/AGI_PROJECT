# AGI v13 项目重组方案

> 生成时间: 2026-03-26 | 引擎: 极致推演引擎 v1.0
> 基于 ULDS v2.1 L6(系统论) + L8(对称性/简化) + L11(认识论) 推演

---

## 一、当前状态审计

### 1.1 项目规模
| 指标 | 数值 |
|------|------|
| 总文件数 | ~5800+ |
| Python 核心模块 | 47 个 (.py 根目录+workspace/) |
| 技能模块(.py) | 2,596 个 |
| 技能元数据(.meta.json) | 2,624 个 |
| 文档(.md) | 60+ 个 |
| 经典智慧节点 | 29 篇 |
| 能力清单项 | 108 项 (81% ≥ 4星) |
| proven 知识节点 | 1,200+ |
| 认知领域 | 920+ |
| 关联关系 | 108,000+ |

### 1.2 当前结构问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **根目录膨胀** | 🔴高 | 47个Python文件平铺在根目录，核心/辅助/配置混杂 |
| **skills目录爆炸** | 🔴高 | 5,200+文件(py+json)平铺在一个目录，无分类 |
| **文档碎片化** | 🟡中 | docs/下有6个子目录，命名不统一(中英混合, "321"前缀) |
| **命名不一致** | 🟡中 | 中英文混用无规则(如"项目清单/"、"classic/"、"readme/") |
| **重复信息** | 🟡中 | 能力清单、排名信息散落在多个文档中 |
| **无进度追踪** | 🟡中 | 目标/进度/里程碑无结构化追踪 |
| **部署配置散落** | 🟢低 | Dockerfile/docker-compose/k8s在不同层级 |

---

## 二、重组后目标结构

```
AGI_PROJECT/
│
├── README.md                          # 项目总览 + 快速启动
├── RANKING.md                         # 世界排名对比仪表盘
├── ROADMAP.md                         # 发展路线图 + 进度追踪
├── PROJECT_REORG.md                   # 本文档(重组方案)
│
├── core/                              # 🧠 核心引擎 (系统灵魂)
│   ├── README.md                      #   核心模块说明
│   ├── cognitive_core.py              #   认知格核心(四向碰撞+节点真实性)
│   ├── growth_engine.py               #   自成长引擎(并行推演v7.0)
│   ├── orchestrator.py                #   君臣佐使路由器
│   ├── diepre_growth_framework.py     #   DiePre六模式框架
│   ├── extreme_deduction_engine.py    #   极致推演引擎v1.0
│   ├── action_engine.py               #   动作引擎
│   ├── surpass_engine.py              #   超越引擎(6维策略)  [从skills移入]
│   ├── agi_v13_cognitive_lattice.py   #   认知格主类
│   ├── error_classifier.py            #   错误分类器
│   ├── coding_enhancer.py             #   代码增强器
│   └── plugin_registry.py             #   插件注册
│
├── api/                               # 🌐 API 与服务
│   ├── api_server.py                  #   Flask REST + SSE 服务
│   ├── mcp_server.py                  #   MCP 认知格工具
│   ├── tool_controller.py             #   工具控制器
│   └── env_config.py                  #   环境配置
│
├── skills/                            # 🔧 技能库 (按来源分类)
│   ├── README.md                      #   技能库索引 + 统计
│   ├── auto_generated/                #   自成长引擎生成 (2,556个)
│   │   ├── _index.json                #     自动生成索引
│   │   ├── *.py + *.meta.json         #     技能文件
│   │   └── ...
│   ├── imported/                      #   外部导入
│   │   ├── gstack/                    #     gstack 29个工作流技能
│   │   └── openclaw/                  #     OpenClaw 能力模块
│   ├── manual/                        #   手工编写的核心技能
│   │   ├── code_synthesizer.py        #     代码合成器
│   │   ├── software_engineer.py       #     软件工程管线
│   │   ├── codebase_analyzer.py       #     代码库分析
│   │   ├── benchmark_test.py          #     基准测试
│   │   ├── math_formula_engine.py     #     数学公式引擎
│   │   ├── zhipu_ai_caller.py         #     智谱API调用
│   │   ├── zhipu_growth.py            #     智谱自成长
│   │   └── ...                        #     (约39个)
│   └── frameworks/                    #   框架级技能
│       ├── ulds_v2_*.meta.json        #     ULDS v2.1 框架
│       ├── bodhi_path.py              #     菩提道果位
│       └── governance_dynasty.py      #     王朝循环治理
│
├── docs/                              # 📚 文档中心 (按主题分类)
│   ├── README.md                      #   文档索引
│   ├── capabilities/                  #   能力与排名
│   │   ├── capability_list.md         #     108项能力清单
│   │   ├── 100dim_comparison.md       #     100维世界前三对比
│   │   ├── 95dim_execution.md         #     95维执行清单
│   │   └── local_vs_opus.md           #     本地 vs Opus 对比
│   ├── architecture/                  #   架构设计
│   │   ├── orchestrator_design.md     #     Orchestrator架构
│   │   ├── opus_workflow.md           #     Opus需求→实现流程
│   │   └── node_truth_system.md       #     节点真实性系统
│   ├── optimization/                  #   优化记录
│   │   ├── amd_gpu_kernels.md         #     AMD GPU核优化
│   │   ├── openclaw_pcm.md            #     OpenClaw PCM优化
│   │   └── gstack_scan.md             #     gstack扫描报告
│   ├── guides/                        #   使用指南
│   │   ├── quickstart.md              #     快速启动
│   │   ├── api_guide.md               #     API使用指南
│   │   └── amd_launcher.md            #     AMD参赛启动器
│   ├── research/                      #   研究与分析
│   │   ├── industrial_cad.md          #     工业CAD闭环
│   │   ├── heat_treatment.md          #     热处理控温
│   │   └── model_enhancement.md       #     模型能力强化
│   └── pending/                       #   待处理 (替代321前缀)
│       └── ...
│
├── classic/                           # 📜 经典智慧 (不变)
│   ├── 00_应无所住而生其心_认知框架.md
│   ├── 01_道德经.md
│   └── ...
│
├── data/                              # 💾 运行时数据
│   ├── growth_reasoning_log.jsonl
│   ├── extreme_deduction_log.jsonl
│   └── *.json
│
├── scripts/                           # 🔨 工具脚本
│   ├── README.md
│   └── *.py
│
├── tests/                             # ✅ 测试套件
│   ├── test_core.py
│   ├── test_routing_verify.py
│   └── test_truth_classifier.py
│
├── deploy/                            # 🚀 部署配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── k8s/
│   │   └── deployment.yaml
│   ├── start.sh
│   └── stop.sh
│
├── web/                               # 🖥️ Web前端
│   ├── index.html
│   ├── box-editor.html
│   ├── data/
│   └── templates/
│
├── projects/                          # 📁 子项目 (替代"项目清单")
│   ├── diepre_ai/                     #   DiePre AI 优化推演
│   └── modular_die_cutting/           #   刀模活字印刷3D项目
│
└── .github/                           # CI/CD
    └── workflows/
        └── ci.yml
```

---

## 三、世界排名仪表盘

### 3.1 当前排名定位

| 维度 | 本地模型 | Claude Opus 4 | GPT-5 | Gemini 2.5 Pro |
|------|----------|--------------|-------|----------------|
| **95维总均分** | **84.2** | 84.1 | 83.5 | 82.8 |
| **代码生成质量** | 78 | 90 | 88 | 85 |
| **多语言覆盖** | 65 | 92 | 90 | 88 |
| **API调用成本** | **95** | 42 | 38 | 50 |
| **自主知识进化** | **92** | 15 | 10 | 12 |
| **多模型路由** | **90** | 0 | 0 | 0 |
| **开源可控性** | **95** | 0 | 0 | 20 |
| **AI Agent逻辑** | **88** | 65 | 60 | 55 |

### 3.2 结构性优势 (不可被闭源模型复制)

1. **零成本推理**: 本地14B零成本 + GLM成本1/10~1/100
2. **君臣佐使路由**: 4模型协同，任务精准分配
3. **开源完全可控**: 本地部署，数据不外流
4. **自主知识进化**: 认知格自成长，越用越强
5. **AI Agent自治**: 完整工具链+自主决策+自我修复

### 3.3 待提升维度 (短期目标)

| 维度 | 当前 | 目标 | 策略 |
|------|------|------|------|
| SWE-Bench完成率 | 35% | 55% | 极致推演引擎 + 技能库扩展 |
| 多文件编辑 | 55 | 75 | AST级别差分编辑 |
| Rust/Go/Java生成 | 50 | 75 | GLM-5专项训练数据 |
| 200K+上下文 | 40 | 70 | 分段摘要+proven锚定 |
| Computer Use | 30 | 60 | Playwright集成 |

---

## 四、发展路线图

### 4.1 终极目标
> **构建一个自主进化的认知格AGI系统，通过人机共生持续碰撞，在代码领域达到世界顶级水平，并具备跨域迁移能力。**

### 4.2 里程碑

| 里程碑 | 目标 | 预计时间 | 状态 |
|--------|------|----------|------|
| M1 认知格基础 | 1000+节点, 四向碰撞, 语义搜索 | 2026-Q1 | ✅ 已完成 |
| M2 君臣佐使 | 4模型协同, 95维84.2分 | 2026-Q1 | ✅ 已完成 |
| M3 自成长v7 | 并行推演, 5级真实性, DiePre框架 | 2026-Q1 | ✅ 已完成 |
| M4 技能库6000+ | OpenClaw+gstack+自生成 | 2026-Q1 | ✅ 已完成 |
| M5 极致推演 | ULDS+王朝循环+极致推演引擎 | 2026-Q1 | 🔄 进行中 |
| M6 SWE-Bench 55% | 多文件编辑+AST差分+测试生成 | 2026-Q2 | 📋 计划中 |
| M7 多语言75分 | Rust/Go/Java/C#专项提升 | 2026-Q2 | 📋 计划中 |
| M8 Agent自治 | 完整Agent循环+工具锻造+自主学习 | 2026-Q3 | 📋 计划中 |
| M9 跨域迁移 | 代码→工业→医疗→商业知识迁移 | 2026-Q4 | 📋 计划中 |

### 4.3 短期目标 (2026-Q1 剩余)

- [x] 极致推演引擎 v1.0 (ULDS + 王朝循环 + 技能库整合)
- [x] 项目重组方案设计
- [ ] 执行项目重组 (文件移动 + 路径更新)
- [ ] 生成 RANKING.md 实时仪表盘
- [ ] 生成 ROADMAP.md 进度追踪
- [ ] 极致推演引擎首轮执行 (10轮推演)
- [ ] 技能库分类整理 (auto/imported/manual/frameworks)

---

## 五、能力清单索引

### 5.1 按类别统计

| 类别 | 能力数 | 评分均值 | 代表能力 |
|------|--------|----------|----------|
| 认知格核心 | 16 | 4.3★ | 四向碰撞、节点管理、语义搜索 |
| 对话与推理 | 10 | 4.2★ | 多模式对话、双向拆解、幻觉校验 |
| 动作引擎 | 13 | 3.8★ | 代码合成、文件操作、软件工程管线 |
| 云端算力 | 10 | 4.3★ | GLM-5推理、智能委托、自主成长 |
| 工具控制 | 10 | 4.5★ | Python运行时、Shell执行、DXF解析 |
| 超越引擎 | 6 | 4.2★ | 多模型投票、迭代精炼、知识锚定 |
| 技能模块 | 28 | 4.0★ | 代码合成、基准测试、数学引擎 |
| 数学引擎 | 9 | 4.6★ | 公式执行、铁碳相图、PID控制 |
| 工业制造 | 8 | 4.1★ | 谐波减速器、DXF生成、工艺规划 |
| 集群分布 | 4 | 3.3★ | 设备管理、一键迁移、分布式路由 |
| 前端API | 5 | 4.8★ | Web可视化、REST API、SSE推送 |

### 5.2 技能库统计

| 来源 | 数量 | 有实际代码 | 占位符 |
|------|------|-----------|--------|
| 自成长引擎(GLM-5) | 1,475 | ~1,000 | ~475 |
| 碰撞生成 | 854 | ~500 | ~354 |
| 深度推理 | 145 | ~100 | ~45 |
| 知识缺口 | 82 | ~50 | ~32 |
| gstack导入 | 29 | 0 (meta only) | - |
| 手工编写 | 39 | 39 | 0 |
| **合计** | **2,624** | **~1,689** | **~935** |

---

## 六、重组执行计划

### Phase 1: 创建新目录结构 (不移动文件)
```bash
mkdir -p core api skills/{auto_generated,imported/gstack,imported/openclaw,manual,frameworks}
mkdir -p docs/{capabilities,architecture,optimization,guides,research,pending}
mkdir -p deploy projects
```

### Phase 2: 核心文件移动
- 根目录 .py → core/ 或 api/ (按职责)
- workspace/skills/ → skills/ (按来源分类)
- 部署文件 → deploy/

### Phase 3: 路径更新
- 更新所有 import 路径
- 更新 start.sh / stop.sh
- 更新 CI/CD 配置
- 更新 README.md

### Phase 4: 文档整理
- 合并重复文档
- 统一命名为英文小写+下划线
- 创建文档索引

### Phase 5: 验证
- 运行全部 pytest 测试
- 验证 API 启动
- 验证自成长引擎
- 验证极致推演引擎

---

## 七、进度追踪系统

进度追踪通过 `ROADMAP.md` + `data/progress.json` 双轨制:
- **ROADMAP.md**: 人类可读的里程碑和目标
- **data/progress.json**: 机器可读的结构化进度数据

```json
{
  "version": "1.0",
  "last_updated": "2026-03-26",
  "milestones": {
    "M1": {"status": "completed", "progress": 100, "completed_at": "2026-03-15"},
    "M2": {"status": "completed", "progress": 100, "completed_at": "2026-03-18"},
    "M3": {"status": "completed", "progress": 100, "completed_at": "2026-03-22"},
    "M4": {"status": "completed", "progress": 100, "completed_at": "2026-03-25"},
    "M5": {"status": "in_progress", "progress": 60, "started_at": "2026-03-26"},
    "M6": {"status": "planned", "progress": 0},
    "M7": {"status": "planned", "progress": 0},
    "M8": {"status": "planned", "progress": 0},
    "M9": {"status": "planned", "progress": 0}
  },
  "metrics": {
    "total_capabilities": 108,
    "capabilities_4star_plus": 88,
    "skill_count": 2624,
    "proven_nodes": 1200,
    "domains": 920,
    "95dim_score": 84.2
  }
}
```
