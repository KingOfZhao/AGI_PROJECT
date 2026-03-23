# AGI v13.3 Cognitive Lattice

> 四向碰撞认知格 — 本地 AI 模型 + 可视化前端 + 自成长引擎

## 项目概览

基于认知格(Cognitive Lattice)架构的本地 AGI 系统，支持：

- **四向碰撞思维**：自上而下拆解 + 自下而上合成 + 左右跨域碰撞 + 循环自成长
- **多后端支持**：Ollama 本地模型 / 智谱AI / OpenAI / DeepSeek / xAI
- **动作引擎**：代码生成、文件操作、技能构建、工具锻造
- **数学公式引擎**：18个 proven 公式 + 铁碳相图 + 温差推演
- **自成长引擎**：在线(LLM驱动) + 离线(纯embedding碰撞)两种模式
- **Web 可视化**：节点图谱、对话、控制台、成长监控

## 快速启动

```bash
./start.sh
```

浏览器自动打开 → http://localhost:5002

停止服务：
```bash
./stop.sh
```

## 目录结构

```
AGI_PROJECT/
├── start.sh                  # 一键启动脚本
├── stop.sh                   # 停止脚本
├── api_server.py             # 后端服务(Flask, 端口5002)
├── agi_v13_cognitive_lattice.py  # 认知格核心(节点/碰撞/自成长)
├── action_engine.py          # 动作引擎(代码合成/文件操作/技能构建)
├── cognitive_core.py         # 认知核心(Prompt/对话管线)
├── tool_controller.py        # 工具控制器(LLM+Python运行时)
├── cluster_manager.py        # 集群管理(多设备分布式)
├── mcp_server.py             # MCP Server(IDE集成)
├── memory.db                 # SQLite 认知数据库
├── web/
│   └── index.html            # 前端可视化页面
├── classic/                  # 26部经典智慧认知体系(440+条微言大义)
│   ├── 00_应无所住而生其心_认知框架.md
│   ├── 01_道德经.md ~ 26_哈瓦玛尔.md
│   ├── 能力清单_经典智慧.md   # 50项能力(39已实现)
│   └── 验证清单_经典智慧.md   # 50项验证(39已验证)
├── scripts/                  # 知识注入脚本(175条proven节点)
├── workspace/
│   ├── skills/               # 技能模块目录(28+个)
│   ├── outputs/              # 工具执行输出(DXF/STEP等)
│   └── logs/                 # 运行日志
├── data/                     # 运行时数据(成长进度/日志/配额)
├── docs/                     # 项目文档与领域知识
├── migrate_packages/         # 系统迁移打包
├── readme/                   # 使用指南
│   ├── README.md             # 本文件
│   ├── 启动脚本说明.md        # 启动方式详解
│   └── 调用方式与提问指南.md   # API调用 + 提问示例
└── web/                      # 前端可视化界面
```

## 系统要求

- **macOS / Linux**
- **Python 3.9+**（项目使用 venv 虚拟环境）
- **Ollama**（本地模型推理，可选）
- 磁盘空间：~500MB（含模型和数据库）

## 详细文档

- [启动脚本说明](启动脚本说明.md) — 启动/停止方式详解
- [调用方式与提问指南](调用方式与提问指南.md) — API 端点 + 对话模式 + 提问示例

## 当前状态

- **节点数**：3100+（proven 2200+）
- **领域数**：920+
- **关联数**：108000+
- **技能模块**：28+
- **经典智慧**：175条proven节点，50项能力清单（39已实现）
- **经典文本**：26部经典，440+条微言大义
