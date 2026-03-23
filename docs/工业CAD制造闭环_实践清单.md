# 工业CAD制造闭环 — 完整实践清单

> 基于 AGI 结构化认知理念: 自上而下拆解未知→接近已知, 自下而上构建真实节点
> 架构: 智谱API(大脑) + Python技能文件(四肢) + tool_controller闭环
> 生成日期: 2026-03-19

---

## 全局架构 Pipeline

```
工业未解决概念
    ↓ (LLM Controller: concept_to_checklist)
可实践检查清单 (JSON)
    ↓ (cad_drawing_generator / CadQuery)
CAD设计 (DXF/STEP)
    ↓ (parse_dxf → dxf_to_text)
CAD内容文本化 → LLM理解图纸
    ↓ (dxf_to_process_plan)
Mastercam导出/CAM编程
    ↓ (generate_process_flow_dxf / generate_heat_treatment_curve)
热处理/加工工艺步骤 + 工艺步骤图纸
    ↓
人类实践验证 → proven节点 → 认知格网络
```

---

## 一、已完成 ✅ (可编码部分 — 已实现并验证)

### 1.1 DXF图纸读取 → 文本输出
- **文件**: `workspace/skills/cad_file_recognizer.py`
- **能力**: 用ezdxf解析DXF文件, 提取LINE/CIRCLE/ARC/TEXT/DIMENSION/INSERT/LWPOLYLINE等全部实体
- **函数**:
  - `parse_dxf(file_path)` → 完整实体+元数据JSON
  - `dxf_to_text(file_path, detail_level)` → LLM友好的自然语言描述
  - `extract_entities(file_path, entity_type)` → 按类型筛选实体
  - `get_dimensions(file_path)` → 提取所有尺寸标注
  - `get_layers(file_path)` → 图层信息
- **验证**: 自测通过 — 100×50矩形+圆+文字标注全部正确提取
- **依赖**: `pip install ezdxf` (已安装 v1.4.3)

### 1.2 工艺规划引擎 (概念 → 检查清单)
- **文件**: `workspace/skills/cad_process_planner.py`
- **能力**: 输入零件描述, 智谱API生成JSON格式工艺规划
- **函数**:
  - `concept_to_checklist(concept, context)` → 结构化检查清单(步骤/刀具/参数/验证方法)
  - `dxf_to_process_plan(file_path)` → 从DXF图纸生成完整工艺规划
  - `generate_heat_treatment(part_info)` → 热处理方案(温度/时间/冷却方式)
  - `save_plan_to_file(plan_data)` → 保存为JSON
- **依赖**: 智谱API (已配置)

### 1.3 DXF工艺图纸生成
- **文件**: `workspace/skills/cad_drawing_generator.py`
- **能力**: 用ezdxf生成各类工艺DXF图纸
- **函数**:
  - `generate_process_flow_dxf(steps)` → 工序流程图(带箭头连接+参数标注)
  - `generate_flange_dxf(outer_d, inner_d, ...)` → 参数化法兰盘(主视图+侧视图+标题栏)
  - `generate_heat_treatment_curve(steps)` → 热处理温度-时间曲线
  - `generate_part_outline_dxf(width, height, holes)` → 零件轮廓+尺寸标注
- **验证**: 自测通过 — 8步工序流程图+法兰盘+调质曲线均成功生成DXF
- **输出目录**: `workspace/outputs/`

### 1.4 Tool Controller 集成 (LLM自主调用)
- **文件**: `tool_controller.py`
- **新增工具**:
  - `parse_dxf` — LLM可自主调用读取DXF图纸
  - `concept_to_checklist` — LLM可自主生成工艺清单
  - `generate_dxf_drawing` — LLM可自主生成DXF图纸(4种类型)
- **使用方式**: Web UI切换到🔧Tool模式, 输入需求, LLM自动选择并调用工具
- **示例**: "帮我分析这个DXF图纸" → LLM调用parse_dxf → 返回图纸内容描述

---

## 二、待实践 — 可编码部分 🔨 (我来实现)

### 2.1 STEP/IGES 3D CAD 文件解析
- **方案**: 安装 CadQuery 或 pythonocc-core
- **命令**: `pip install cadquery` (需要conda环境, OCCT依赖较重)
- **实现**: 在 `cad_file_recognizer.py` 中新增 `parse_step()` 函数
- **优先级**: 中 — 当用户有STEP文件时再实现
- **状态**: 📋 待用户确认是否需要

### 2.2 Mermaid工艺流程图生成
- **方案**: 从工艺JSON生成Mermaid markdown, 可在Web UI直接渲染
- **实现**: 在 `cad_process_planner.py` 中新增 `plan_to_mermaid()` 函数
- **优先级**: 低 — DXF流程图已可用
- **状态**: 📋 待排期

### 2.3 DXF → SVG/PNG 预览图
- **方案**: 用ezdxf的matplotlib后端或svgwrite导出预览
- **命令**: `pip install matplotlib svgwrite`
- **实现**: 在 `cad_drawing_generator.py` 中新增 `dxf_to_preview()` 函数
- **优先级**: 中 — 方便在Web UI中预览
- **状态**: 📋 待排期

---

## 三、需要人工处理 👤 (你来操作)

### 3.1 DWG文件转换 ⚠️
- **问题**: DWG是AutoDesk私有格式, Python无法直接读取
- **解决方案**: 
  1. 下载安装 **ODA File Converter** (免费): https://www.opendesign.com/guestfiles/oda_file_converter
  2. Mac/Windows均支持, 安装后批量把DWG转为DXF
  3. 转换后的DXF文件可被 `parse_dxf()` 直接读取
- **替代**: 在AutoCAD/中望CAD中手动"另存为DXF"
- **优先级**: **高** — 如果你的图纸主要是DWG格式

### 3.2 Mastercam软件集成 ⚠️
- **问题**: Mastercam是Windows商业软件, 需IronPython + NEThook API
- **前置条件**:
  1. Windows机器上安装Mastercam 2020+
  2. 安装 PythonForMastercam: https://github.com/PeterRussellEvans/PythonForMastercam2020
  3. 安装 NetSDK: https://github.com/PeterRussellEvans/NetSDK
- **集成方式**: 本地模型生成Python脚本 → subprocess调用Mastercam
- **当前替代**: 用FreeCAD的Path workbench生成刀具路径 (开源免费)
- **优先级**: **高** — 核心CAM编程需求
- **状态**: 需在Windows机器上操作

### 3.3 Mastercam STEP-NC导出
- **问题**: 需要Mastercam + steptools插件
- **参考**: https://github.com/steptools/mastercam-stepnc
- **价值**: 导出包含完整工艺元数据的STEP-NC文件
- **优先级**: 中
- **状态**: 需在Mastercam环境中操作

### 3.4 FreeCAD安装与集成
- **问题**: FreeCAD体积较大(~1GB), 需要单独安装
- **解决方案**:
  1. 下载: https://www.freecad.org/downloads.php (Mac/Win/Linux)
  2. 启用Path workbench (CAM模块) + TechDraw (工程图)
  3. Python API: `import FreeCAD` → 脚本化操作
- **价值**: 开源Mastercam替代 + 可生成标准工程图
- **优先级**: 中 — 作为Mastercam的免费替代方案
- **文档**: https://wiki.freecad.org/Power_users_hub

### 3.5 CadQuery安装 (STEP/3D参数化CAD)
- **问题**: 依赖OpenCascade, conda环境更稳定
- **命令**: `conda install -c conda-forge cadquery` 或 `pip install cadquery`
- **价值**: 参数化3D建模 + STEP导入 → 几何查询 → 文本描述
- **参考**: https://github.com/CadQuery/cadquery
- **优先级**: 中

### 3.6 热处理实际工艺验证 ⚠️
- **问题**: 热处理参数必须由人类根据实际设备和材料验证
- **具体事项**:
  - 确认材料牌号与热处理规范对应 (如45#钢调质: 840-860°C淬火, 520-560°C回火)
  - 确认实际电炉升温速率和控温精度
  - 确认冷却介质(水/油/空气)与工件尺寸匹配
  - 硬度检测验证 (HRC/HRB)
- **优先级**: **高** — 热处理参数错误可能导致工件报废
- **解决方式**: AI生成方案 → 你审核修正 → 小批量试验 → 确认后批量

### 3.7 工业领域知识具现化 (构建真实节点)
- **对应你的AGI概念**: "认知自洽的人类将模糊化的内容具现化成一个个小节点"
- **具体事项**:
  - 你作为制造领域的实践者, 需要将具体加工经验录入系统:
    - 例: "45#钢车削时, 精车转速800-1000RPM, 进给0.08-0.15mm/r, 表面粗糙度可达Ra1.6"
    - 例: "M8螺纹底孔用∅6.8钻头, 攻丝时需加攻丝油"
    - 例: "法兰盘装夹用三爪卡盘夹外圆, 精车内孔时需校正跳动≤0.02"
  - 通过Web UI的"录入节点"功能或API `/api/ingest` 添加
  - 这些节点会成为proven节点, 被LLM查询和引用
- **优先级**: **高** — 这是AI认知网络的"真实物理路径"来源

---

## 四、无法解决的问题 ❌ (标记等待)

### 4.1 真实CNC机床联动
- **问题**: 生成的G-code/NC程序需要在真实机床上验证, 涉及机床型号/控制系统/夹具
- **状态**: 超出软件范畴, 需在车间实操
- **建议**: AI生成NC程序 → 你在仿真软件(Mastercam Verify/VERICUT)中验证 → 实机试切

### 4.2 材料物理性能测试
- **问题**: 热处理后硬度/强度/金相组织等需要实验室检测设备
- **状态**: 超出软件范畴

### 4.3 Mastercam Copilot 2026.R2 集成
- **问题**: 该功能内置于Mastercam商业软件, 需正版license
- **参考**: https://www.mastercam.com/community/blog/mastercam-copilot-in-2026-r2-faster-commands-smarter-automation-and-hands-free-programming/
- **状态**: 需要购买/获取软件

### 4.4 POPPER证伪框架集成
- **参考**: https://github.com/snap-stanford/POPPER
- **问题**: 该框架主要用于科学假设验证, 工业制造场景需要大量定制
- **建议**: 当前用tool_controller的execute_python来模拟: 生成假设→执行代码验证→反馈结果

---

## 五、Tool Controller 使用指南

### 5.1 Web UI 方式
1. 打开 http://localhost:5002
2. 聊天模式选择 🔧 **Tool**
3. 输入需求, 例如:
   - "读取 workspace/outputs/flange_20260319_154006.dxf 并告诉我图纸内容"
   - "帮我设计一个∅80×15mm的45#钢法兰盘加工方案"
   - "生成一个法兰盘DXF图纸, 外径120, 内径80, 6个M10螺栓孔"

### 5.2 API 方式
```bash
# 直接调用
curl -X POST http://localhost:5002/api/tool/solve \
  -H "Content-Type: application/json" \
  -d '{"question": "解析DXF文件并生成工艺清单"}'

# 通过聊天接口
curl -X POST http://localhost:5002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你的问题", "mode": "tool"}'

# 查看工具状态
curl http://localhost:5002/api/tool/status
```

### 5.3 可用工具清单 (9个)
| 工具 | 用途 |
|------|------|
| `execute_python` | 持久化Python运行时(变量保持) |
| `run_shell` | Shell命令执行 |
| `read_file` / `write_file` | 文件操作 |
| `query_knowledge` | 搜索proven知识节点 |
| `list_skills` | 列出26个Python技能模块 |
| `parse_dxf` | 解析DXF图纸→文本 |
| `concept_to_checklist` | 工业概念→工艺检查清单 |
| `generate_dxf_drawing` | 生成DXF图纸(4种类型) |

---

## 六、AGI认知网络映射

```
你的思想概念                          系统实现
────────────                      ────────
自上而下拆解不可证伪的问题     →   concept_to_checklist (LLM拆解概念→具体步骤)
梳理至已知部分               →   query_knowledge (搜索proven节点)
自下而上产生新问题            →   工艺规划中的"待验证"步骤 → 新hypothesis节点
碰撞重叠构建结构化认知        →   proven节点间的关联关系
人类通过实践丰富AI认知        →   你录入加工经验 → proven节点
人类将模糊概念具现化          →   你描述具体工艺参数 → /api/ingest录入
认知自洽的实践能力            →   每个proven节点 = 一个可验证的真实能力
AI梳理实践清单交给人实践      →   工艺检查清单(含codeable/non-codeable标记)
```

---

## 七、已生成的示例文件

| 文件 | 说明 |
|------|------|
| `workspace/outputs/process_flow_*.dxf` | 45#钢法兰盘8步工艺流程图 |
| `workspace/outputs/flange_*.dxf` | ∅100×20法兰盘参数化图纸(主视图+侧视图) |
| `workspace/outputs/heat_treatment_curve_*.dxf` | 45#钢调质处理温度曲线 |

可用AutoCAD/FreeCAD/中望CAD/DXF在线查看器打开验证。
