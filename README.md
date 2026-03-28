# AGI v13 — 认知格自成长智能体

> 应无所住而生其心 · 域内思考→跨域求助→域内获答
> 95维编码均分 **84.2** (超越 Claude Opus 4 的 84.1)

## 项目简介

基于「认知格」（Cognitive Lattice）架构的AGI系统，通过四向碰撞（上↔下 × 左↔右）实现知识的自动发现、验证和成长。融合26部人类经典智慧 + ULDS v2.1 十一大规律 + 君臣佐使多模型协同。

## 核心架构

```
用户问题 → 君(14B)路由 → 语义搜索proven → 四向碰撞 → 臣(GLM-5)推理 → 解决方案
               ↓              ↓                ↓              ↓
          复杂度评估      proven锚定      ULDS约束校验     5级真实性验证
```

**君臣佐使**: 本地14B(君) + GLM-5(臣) + GLM-4.7(佐) + GLM-4.5-Air(使)

## 目录结构

```
AGI_PROJECT/
├── README.md                  # 本文档
├── RANKING.md                 # 🏆 世界排名仪表盘
├── ROADMAP.md                 # 🗺️ 发展路线图+进度追踪
├── PROJECT_REORG.md           # 📐 项目重组方案
├── start.sh / stop.sh         # 启停脚本
├── _paths.py                  # Python路径引导模块
│
├── core/                      # 🧠 核心引擎
│   ├── cognitive_core.py      #   认知哲学(四向碰撞+5级真实性)
│   ├── agi_v13_cognitive_lattice.py  #   认知格主引擎
│   ├── growth_engine.py       #   自成长引擎v7.0(100x并行)
│   ├── orchestrator.py        #   君臣佐使路由器
│   ├── extreme_deduction_engine.py  #   极致推演引擎v1.0
│   ├── diepre_growth_framework.py   #   DiePre六模式框架
│   ├── action_engine.py       #   动作执行引擎
│   ├── coding_enhancer.py     #   代码增强器
│   ├── cluster_manager.py     #   集群管理器
│   └── ...                    #   (14个核心模块)
│
├── api/                       # 🌐 API与服务
│   ├── api_server.py          #   Flask REST + SSE (85+端点)
│   ├── mcp_server.py          #   MCP认知格工具(9工具)
│   ├── tool_controller.py     #   工具控制器
│   └── env_config.py          #   环境配置
│
├── workspace/skills/          # 🔧 技能库 (2,624个)
│   ├── README.md              #   技能索引+统计
│   ├── auto_*.py/json         #   自成长生成(2,556)
│   ├── gstack_*.json          #   gstack导入(29)
│   └── *.py                   #   手工核心技能(39)
│
├── docs/                      # 📚 文档中心
│   ├── capabilities/          #   能力清单+排名对比
│   ├── architecture/          #   架构设计文档
│   ├── optimization/          #   优化记录
│   ├── guides/                #   使用指南
│   ├── research/              #   研究与分析
│   └── pending/               #   待处理文档
│
├── classic/                   # 📜 26部经典智慧(440+条)
├── data/                      # 💾 运行时数据+进度追踪
├── scripts/                   # 🔨 工具脚本+验证脚本
├── tests/                     # ✅ 测试套件(324/325 pass)
├── deploy/                    # 🚀 部署配置(Docker+K8s)
├── projects/                  # 📁 子项目(DiePre AI等)
├── web/                       # 🖥️ Web前端
└── readme/                    # 使用指南(旧版)
```

## 核心能力 (108项, 81% ≥ 4星)

| 类别 | 数量 | 代表能力 |
|------|------|----------|
| 认知格核心 | 16 | 四向碰撞、节点管理、GLM-5全速推演 |
| 对话推理 | 10 | 5模式对话、双向拆解、幻觉校验 |
| 动作引擎 | 13 | 代码合成、软件工程管线、代码库分析 |
| 云端算力 | 10 | GLM-5推理、智能委托、自成长循环 |
| 超越引擎 | 6 | 多模型投票、迭代精炼、知识锚定 |
| 数学引擎 | 9 | 公式执行、铁碳相图、PID控制 |
| 工业制造 | 8 | 谐波减速器、DXF生成、工艺规划 |
| 前端API | 5 | 85+端点、Web可视化、SSE推送 |

## 数据资产

| 资产 | 规模 |
|------|------|
| proven 知识节点 | 1,200+ |
| 认知领域 | 920+ |
| 关联关系 | 108,000+ |
| 技能模块 | 2,624 |
| 经典智慧节点 | 175条 |

## 快速启动

```bash
# 启动服务 (自动设置PYTHONPATH)
./start.sh

# 访问
open http://localhost:5002

# 极致推演 (需ZHIPU_API_KEY)
PYTHONPATH=core:api:. python3 core/extreme_deduction_engine.py --problem "你的问题" --rounds 5

# 自成长引擎
PYTHONPATH=core:api:. python3 core/growth_engine.py --parallel --workers 8 --rounds 20
```

## 技术栈

- **后端**: Python + Flask + SQLite
- **前端**: 原生HTML/JS + TailwindCSS
- **LLM**: Ollama(本地14B) + 智谱GLM-4/5(云端)
- **嵌入**: nomic-embed-text (Ollama本地向量化)
- **框架**: ULDS v2.1 (11大规律) + DiePre六模式 + 5级真实性
