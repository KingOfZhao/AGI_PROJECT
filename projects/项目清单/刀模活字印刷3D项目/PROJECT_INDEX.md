# 项目索引 — 刀模活字印刷3D打印模块化系统

> 项目地址: `/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/`
> 创建日期: 2026-03-25
> 推演轮次: 30轮 (已全部完成)
> 状态: ✅ 推演完成 + 代码构建完成 + STL生成完成

---

## 项目描述

将传统钢规刀模制作理念与**活字印刷**模块化思想结合，利用**拓竹P1S/P2S 3D打印机**
制造可复用的模块化刀模组件。系统能将CAD二维图纸(DXF/DWG)自动拆解为标准化小模块，
像华容道一样拼接成完整刀模，实现刀模的低成本、快速、可复用制造。

---

## 文件结构

| 路径 | 说明 |
|------|------|
| `README.md` | 项目详细说明 (概念/标准/模块/算法) |
| `PROJECT_INDEX.md` | 本文件 — 项目索引 |

### 源代码 (`src/`)

| 文件 | 功能 | 运行方式 |
|------|------|----------|
| `knowledge_base.py` | 知识库: IADD标准/P1S P2S参数/物理定律/模块类型 | 被其他模块import |
| `reasoning_db.py` | 推演数据库: SQLite ORM (6张表) | 被引擎import |
| `die_reasoning_engine.py` | **30轮推演引擎** (基础→设计→算法→验证→优化→集成) | `python3 die_reasoning_engine.py 30` |
| `module_decomposer.py` | **活字模块拆解器**: CAD→连接图→路径→模块序列 | `python3 module_decomposer.py [L W H]` 或 `python3 module_decomposer.py file.dxf` |
| `stl_generator.py` | **STL生成器**: 参数化生成3D打印模型 (纯Python) | `python3 stl_generator.py [2pt\|3pt]` |
| `dieline_to_modules.py` | **完整管线**: DXF→拆解→STL→BOM→装配指南 | `python3 dieline_to_modules.py [file.dxf] [2pt]` |

### 推演数据 (`推演数据/`)

| 文件 | 说明 |
|------|------|
| `reasoning.db` | SQLite数据库 (65KB): 30轮推演记录/70知识节点/84模块设计/收敛日志 |
| `round_01.md` ~ `round_30.md` | 每轮推演简报 |
| `推演最终报告.md` | 30轮推演最终报告: 结论/统计/技术栈推荐 |

### 模块库 (`模块库/`) — 18个STL文件

| 模块 | 文件数 | 说明 |
|------|--------|------|
| STRAIGHT (直线段) | 5 | 20/50/100/150/200mm, 2pt刀片 |
| CORNER (转角) | 4 | 45°/90° × R1.4/R3.0mm |
| T_JOINT (T形接头) | 1 | 三向交汇 |
| CROSS_JOINT (十字接头) | 1 | 四向交汇 |
| END_CAP (端头) | 2 | 平头/圆头 |
| BASE_TILE (底板) | 3 | 100²/150²/200²mm |
| BRIDGE (桥接) | 2 | 5/10mm |

### 输出 (`output/`)

| 文件 | 说明 |
|------|------|
| `module_list.json` | 测试盒(300×200×150)拆解后的25个模块清单 |

---

## 推演核心数据

### 数据库表结构 (reasoning.db)

| 表 | 记录数 | 内容 |
|----|--------|------|
| `reasoning_rounds` | 30 | 每轮推演记录 (轮次/阶段/方向/内容/分数/σ) |
| `knowledge_nodes` | 70 | 知识节点 (固定规则26/公式20/优化10/平台5/变量5/发现4) |
| `module_designs` | 84 | 模块设计参数 (11种类型的详细规格) |
| `decomposition_results` | 2 | 拆解验证结果 |
| `convergence_log` | 9 | 收敛追踪 (σ均<0.065, 全部收敛) |

### 推演6阶段收敛

| 阶段 | 轮次 | σ值 | 状态 |
|------|------|-----|------|
| 基础研究 | R1-R5 | 0.064 | ✓收敛 |
| 模块设计 | R6-R10 | 0.064 | ✓收敛 |
| 拆解算法 | R11-R15 | 0.061 | ✓收敛 |
| 约束验证 | R16-R20 | 0.056 | ✓收敛 |
| 拼接优化 | R21-R25 | 0.060 | ✓收敛 |
| 系统集成 | R26-R30 | 0.061 | ✓收敛 |

### 关键验证结果

| 指标 | 值 | 标准 | 结果 |
|------|-----|------|------|
| 3D打印精度 | ±0.15mm | IADD ±0.254mm | ✅ PASS |
| RSS公差链 | 0.219mm | < 0.254mm | ✅ PASS |
| 模切力承载 | 4760N | > 2380N (安全系数2.0) | ✅ PASS |
| 燕尾榫剪切力 | 3600N | > 2380N | ✅ PASS |
| 模块复用率 | 91.2% | > 60% | ✅ PASS |
| 成本对比 | ¥186 | 传统 ¥500 | ✅ 节省63% |

---

## 源图纸

- **主图纸**: `/Users/administruter/Desktop/拉扯图形/苑艺.dwg` (2333KB)
- **图纸目录**: `/Users/administruter/Desktop/拉扯图形/` (70+个DWG客户刀模文件)
- **格式**: AutoCAD DWG → 需 ezdxf 或 ODA转DXF后解析

---

## 依赖

```
Python 3.8+
ezdxf         # DXF解析 (pip install ezdxf)
              # STL生成为纯Python实现,无额外依赖
```

## 快速开始

```bash
cd "/Users/administruter/Desktop/AGI_PROJECT/项目清单/刀模活字印刷3D项目/src"

# 1. 运行推演 (已完成,可跳过)
python3 die_reasoning_engine.py 30

# 2. 生成标准模块STL
python3 stl_generator.py 2pt

# 3. 拆解测试盒
python3 module_decomposer.py 300 200 150

# 4. 拆解DXF文件 (需ezdxf)
python3 module_decomposer.py /path/to/file.dxf 2pt

# 5. 完整管线
python3 dieline_to_modules.py 300 200 150 2pt
```
