# AGI v13 — 认知格自成长智能体

> 应无所住而生其心 · 域内思考→跨域求助→域内获答

## 项目简介

基于「认知格」（Cognitive Lattice）架构的AGI系统，通过四向碰撞（上↔下 × 左↔右）实现知识的自动发现、验证和成长。融合26部人类经典智慧作为操作原则。

## 核心架构

```
用户问题 → 语义搜索已知节点 → 四向碰撞拆解 → LLM推理 → 解决方案合成
                ↓                      ↓                    ↓
           proven节点复用        新hypothesis生成       认知格自成长
```

## 目录结构

```
AGI_PROJECT/
├── api_server.py          # Flask API服务器（主入口）
├── agi_v13_cognitive_lattice.py  # 认知格核心引擎
├── cognitive_core.py      # 认知哲学引擎（系统提示词/思维范式）
├── action_engine.py       # 动作执行引擎
├── tool_controller.py     # 工具控制器
├── cluster_manager.py     # 集群管理器
├── mcp_server.py          # MCP协议服务器
├── deploy_and_verify.py   # 部署与验证
├── start.sh / stop.sh     # 启停脚本
├── setup_agi_v13_mac.py   # Mac安装脚本
├── memory.db              # SQLite认知格数据库
│
├── web/                   # 前端可视化界面
│   └── index.html         # 单页面应用（认知格可视化+对话+成长控制）
│
├── classic/               # 26部经典智慧认知体系（440+条微言大义）
│   ├── 00_应无所住而生其心_认知框架.md  # 元框架
│   ├── 01_道德经.md ~ 26_哈瓦玛尔.md   # 26部经典
│   ├── 能力清单_经典智慧.md             # 50项能力清单（39已实现/3可实现/8需人类）
│   └── 验证清单_经典智慧.md             # 50项验证清单（39已验证/3待验证/8不可验证）
│
├── scripts/               # 知识注入脚本与测试工具
│   ├── _inject_classic_wisdom.py  # 经典智慧注入（175条proven节点）
│   ├── _inject_*.py               # 各领域知识注入
│   └── _test_*.py                 # 测试脚本
│
├── docs/                  # 项目文档与知识资料
│   ├── 能力清单.md / 验证清单.md  # 系统能力文档
│   ├── 热处理控温方法_室温到1600度.md
│   ├── 工业CAD制造闭环_实践清单.md
│   └── 待完成清单/
│
├── readme/                # 使用指南
│   ├── README.md
│   ├── 启动脚本说明.md
│   └── 调用方式与提问指南.md
│
├── workspace/             # 工作区（技能/数据/日志）
│   └── skills/            # 技能模块（zhipu_growth.py等）
│
├── data/                  # 数据文件
├── migrate_packages/      # 迁移工具
└── venv/                  # Python虚拟环境
```

## 核心功能

### 对话模式
| 模式 | 描述 |
|------|------|
| Code | 标准代码模式，带动作执行 |
| Ask | 纯问答模式 |
| Plan | 规划模式 |
| 🔥 热处理 | 热处理/材料科学领域专家 |
| 📱 移动端 | Flutter/Dart/移动开发专家 |
| 🧠 AGI | AGI/本地模型/认知架构专家 |
| 🌐 跨域碰撞 | 应无所住而生其心·多域交叉解题 |

### 自成长引擎
- **普通成长**: GLM-4-flash验证hypothesis节点
- **全速推演**: GLM-5高性能批量验证
- **自主探索**: falsified节点触发新方向探索

### 认知格数据
- 3100+ 知识节点
- 108000+ 关联关系
- 920+ 认知领域
- 175条经典智慧proven节点（50项能力清单，39项已实现）

## 快速启动

```bash
# 启动服务
./start.sh

# 或直接运行
python3 api_server.py

# 访问
open http://localhost:5002
```

## 技术栈

- **后端**: Python + Flask + SQLite
- **前端**: 原生HTML/JS + TailwindCSS
- **LLM**: Ollama（本地）+ 智谱GLM-4/5（云端）
- **嵌入**: nomic-embed-text（Ollama本地向量化）
