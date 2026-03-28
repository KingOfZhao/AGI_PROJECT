# 可视化 CRM 系统 — AI 可读文档

> **生成时间**: 2026-03  
> **用途**: 供 AI 系统快速理解本项目的 CRM 前端系统全貌  
> **源文件索引**: 见文末「源文件清单」

---

## 1. 系统概述

**AGI v13 CRM** 是一个单页面可视化管理系统，用于管理 AGI 系统的项目、推演任务、SKILL技能库、模型能力、阻塞问题和工作流编排。

- **技术栈**: 纯前端 (HTML + Vanilla JS)，无后端框架
- **UI框架**: TailwindCSS (CDN) + Chart.js 4
- **设计风格**: 暗色主题 (Glassmorphism)，Inter 字体
- **数据持久化**: localStorage + 从 `deduction_export.json` 动态加载
- **入口文件**: `web/crm.html`

---

## 2. 页面结构 (9个页面)

### 导航分组与页面

| 分组 | 页面ID | 页面名称 | 功能 |
|------|--------|---------|------|
| 主面板 | `dashboard` | 总览仪表盘 | KPI指标 + 策略柱状图 + 项目进度饼图 + 推演成果 + 里程碑 |
| 主面板 | `projects` | 项目管理 | 项目卡片 (CRUD) + 进度条 + 标签 |
| 推演任务 | `deduction` | 待推演列表 | 推演计划列表 + 优先级筛选 + 项目筛选 + 队列设定 + 状态切换 |
| 推演任务 | `todos` | 待完成列表 | 看板视图 (待处理/进行中/已完成) |
| 资源 | `skills` | Skill 技能库 | 分类展示 + 搜索 + 统计 (自有/OpenClaw/gstack) |
| 资源 | `model` | 本地模型能力 | 模型卡片 + 调用链路可视化 + 雷达图 + vs世界前三对比 + 95维详情表 |
| 资源 | `progress` | 进度追踪 | 短期/长期目标 + 季度规划 + 8大策略进度 |
| 协作 | `problems` | 阻塞问题 | 问题报告 + 5阶段状态流转 + 解决方案插入 + 替代AI记录 |
| 协作 | `workflows` | 工作流编排 | 可视化SKILL调用链路 + 步骤连线展示 |

### 导航徽章 (Badge)

- `deduction`: 显示未完成推演数量
- `todos`: 显示未完成任务数量
- `problems`: 显示 open 状态问题数量

---

## 3. 数据模型 (DATA 对象)

### 3.1 数据加载流程

```
initApp()
  → loadSaved()        // 从 localStorage 加载 ('agi_crm_v2')
  → loadFromDB()        // 从 data/deduction_export.json 异步加载
  → 缺失数组回退到 DEFAULTS
  → buildNav() + go('dashboard')
```

### 3.2 核心数据结构

```javascript
DATA = {
  currentUser: { name, id } | null,
  
  projects: [{
    id, name, description, status: 'active'|'planning',
    progress: 0-100, color: '#hex',
    tags: [...], ultimate_goal, short_term_goal
  }],
  
  deductions: [{
    id, title, desc, priority: 'critical'|'high'|'medium',
    status: 'queued'|'running'|'done',
    laws: 'L1+L4', strategies: 'S4+S7',
    model: 'glm5'|'glm5_turbo'|'glm47'|'ollama_local',
    project: 'project_id', rounds: 5
  }],
  
  todos: [{
    id, title, status: 'pending'|'progress'|'done',
    priority: 'high'|'medium'|'low', project: 'project_id'
  }],
  
  skills: [{
    category, count, source: '自有'|'OpenClaw'|'gstack',
    color, items: [...], desc
  }],
  
  capabilities: [{
    dim: '维度名', local: 0-100, opus: 0-100, gpt5: 0-100, target: 0-100
  }],
  
  strategies: [{ name: 'S1 规律约束注入', pct: 85 }],
  
  problems: [{
    id, title, description,
    severity: 'critical'|'high'|'medium',
    status: 'open'|'pending_verify'|'pending_deduction'|'deduced'|'resolved',
    project_id, suggested_solution, user_solution, alt_ai_used,
    spawned_plan_id, resolved_at, updated_at
  }],
  
  workflows: [{
    id, name, project: 'project_id',
    steps: [{ id, skill: 'SKILL名', type: 'system'|'glm5'|'glm5_turbo'|'ollama' }],
    status: 'active'|'draft'
  }],
  
  models: [{
    id, name, role: '君 Emperor'|'臣 Minister'|...',
    desc, color, enabled: boolean
  }],
  
  codeGoals: [{ name, current, target }],
  sysGoals: [{ name, current, target, invert?: boolean }],
  milestones: [{ name, pct: 0-100 }],
  deductionResults: [{ round, name, laws, test: '6/6' }],
  
  queue_settings: {
    priority_project, new_problems_position: 'append'|'prepend',
    auto_expand: 0|1, max_expand_per_plan: 3,
    deduction_order: 'priority'|'project'|'created'
  }
}
```

---

## 4. 默认预置项目 (8个)

| ID | 名称 | 说明 | 进度 |
|----|------|------|------|
| `p_diepre` | 刀模设计项目 | DiePre AI — 刀模图→ULDS推演→3D→2D图纸 | 65% |
| `p_rose` | 予人玫瑰 | 上线运转+快速商业化 | 30% |
| `p_huarong` | 刀模活字印刷3D | 华容道×乐高×活字印刷→模块化卡刀 | 20% |
| `p_model` | 本地模型超越计划 | 代码能力超 Claude Opus 4.6 | 56% |
| `p_mgmt` | 最佳管理协作制度 | AI圆桌决策+历史人物高光 | 15% |
| `p_operators` | 三个算子推演 | 算法第一 | 5% |
| `p_visual` | 最佳视觉效果推演 | AI理解人类视觉审美 | 0% |
| `p_workflow` | 工作流可视化项目 | 拖拽定义AI工作流 | 0% |

---

## 5. 模型配置 (君臣佐使)

| ID | 名称 | 角色 | 职责 |
|----|------|------|------|
| `ollama_local` | Ollama 14B | 君 Emperor | 幻觉校验/路由决策/节点锚定 |
| `glm5` | GLM-5 | 臣 Minister | 复杂推理/深度分析/创新 |
| `glm5_turbo` | GLM-5 Turbo | 快臣 Fast | 快速推演/批量处理/高吞吐 |
| `glm47` | GLM-4.7 | 佐 Assistant | 快速编码/代码补全/重构 |
| `glm45air` | GLM-4.5-Air | 使 Messenger | 轻量响应/分类路由/摘要 |

调用链路可视化:
```
用户提问 → Ollama路由 → GLM-5 Turbo快速分析 → GLM-5深度推理
→ GLM-4.7代码生成 → Ollama幻觉校验 → 零回避扫描 → 返回结果
```

---

## 6. 阻塞问题 5 阶段状态流转

```
open (待解决)
  → pending_verify (待验证)
    → pending_deduction (待推演)
      → deduced (已推演)
        → resolved (已解决)
```

每个阶段支持:
- **插入解决方案**: `user_solution` 字段
- **记录替代AI**: `alt_ai_used` 字段
- **生成推演计划**: `spawned_plan_id` 关联

---

## 7. 推演队列设定

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `priority_project` | 优先推演的项目 | 无 |
| `new_problems_position` | 问题生成的计划排序 | `append` (追加末尾) |
| `auto_expand` | 是否自动拓展推演方向 | 1 (开启) |
| `max_expand_per_plan` | 每计划最大拓展数 | 3 |
| `deduction_order` | 推演排序方式 | `priority` |

---

## 8. 图表可视化 (Chart.js)

| 图表 | 页面 | 类型 | 数据源 |
|------|------|------|--------|
| 8大超越策略 | dashboard | bar | `DATA.strategies` |
| 项目进度分布 | dashboard | doughnut | `DATA.projects` |
| 能力雷达图 | model | radar | 8维: 代码生成/系统设计/算法/自治/多语言/成本/自成长/幻觉控制 |
| vs世界前三 | model | horizontal bar | `DATA.capabilities` (本地 vs Opus 4 vs GPT-5) |

---

## 9. 预置工作流 (3个)

| 工作流 | 项目 | 步骤 | 状态 |
|--------|------|------|------|
| 代码推演流水线 | p_model | ULDS注入→问题分解→代码生成→测试验证→零回避→记录 | active |
| 刀模设计推演链 | p_diepre | DXF解析→F→V→F约束→2D图纸→Playwright验证→精度反馈 | draft |
| 商业化推演链 | p_rose | 市场分析→竞品对比→定价推演→分成方案→法律合规 | draft |

---

## 10. 预置技能库统计

| 分类 | 数量 | 来源 | 关键能力 |
|------|------|------|---------|
| 代码生成 | 420 | 自有 | Python/Dart/TS/AST分析 |
| 算法数据结构 | 380 | 自有 | 图算法/DP/并发LRU |
| 系统设计 | 310 | 自有 | 分布式/微服务/容错 |
| 工业制造 | 250 | 自有 | CAD/DXF/刀模/3D |
| NLP/认知 | 751 | 自有 | 语义搜索/幻觉检测/知识图谱 |
| 数学/公式 | 180 | 自有 | 公式引擎/铁碳相图/优化 |
| DevOps | 333 | 自有+gstack | CI/CD/Docker/K8s |
| 自愈/可靠性 | 45 | 自有 | 断路器/混沌工程/自愈运行时 |
| 多语言生成 | 35 | 自有 | 跨语言Schema/类型映射 |
| OpenClaw开源 | 4717 | 社区 | Web/移动/数据库/安全/测试 |

**总计**: ~7,421 技能

---

## 11. 95维能力矩阵 (vs 世界前三)

CRM 中展示 14 个关键维度的对比:

| 维度 | 本地 | Opus 4 | GPT-5 | 目标 | 本地优势? |
|------|------|--------|-------|------|----------|
| SWE-Bench | 35 | 49 | 55 | 55 | ✗ |
| Python生成 | 82 | 92 | 90 | 88 | ✗ |
| API成本 | 95 | 40 | 35 | 95 | ✓ (绝对优势) |
| 自成长 | 92 | 10 | 5 | 95 | ✓ (绝对优势) |
| 多模型路由 | 88 | 20 | 15 | 92 | ✓ (绝对优势) |
| 知识演化 | 90 | 15 | 10 | 95 | ✓ (绝对优势) |
| 幻觉控制 | 80 | 85 | 82 | 88 | ✗ (接近) |

---

## 12. UI 交互功能

### CRUD 操作

| 实体 | 创建 | 编辑 | 删除 | 状态切换 |
|------|------|------|------|---------|
| 项目 | `addProject()` | `editProject(id)` | - | 进行中/规划中 |
| 推演计划 | `addDeduction()` | - | `removeDed(id)` | queued→running→done |
| 待办任务 | `addTodo()` | - | - | pending→progress→done |
| 阻塞问题 | `addProblem()` | `solveProblem(id)` | - | 5阶段流转 |
| 工作流 | `addWorkflow()` | - | - | active/draft |

### 模态框系统

```javascript
openModal(title, body, callback)  // 打开
closeModal()                       // 关闭
saveModal()                        // 执行回调 + 关闭 + 重渲染
```

### 筛选功能

- 推演列表: 按优先级 (`filterDed`) + 按项目 (`filterDedProj`)
- 阻塞问题: 按状态 (`filterProblems`)
- 技能库: 搜索关键词 (`filterSkills`)

### 用户登录

简单本地登录，存入 `DATA.currentUser`，无鉴权后端。

---

## 13. 数据与后端集成

### 数据来源

1. **localStorage** (`agi_crm_v2`): 用户操作后 `saveData()` 写入
2. **deduction_export.json**: 由 `deduction_runner.py --export` 生成
   - 包含: projects, deductions (plans), problems
   - 字段映射: `description→desc`, `project_id→project`, `ulds_laws→laws`

### 与推演引擎的关系

```
deduction_runner.py --export
  → 写入 web/data/deduction_export.json
    → crm.html loadFromDB() 读取
      → 与 localStorage 合并
        → 渲染页面
```

---

## 13. 关联性标签

```yaml
system_id: crm_visual
category: visualization
priority: P1
relates_to:
  - system: ULDS v2.1 推演框架
    relation: CRM的deduction页面直接管理ULDS推演计划; 每条推演标注laws(L1-L11)和strategies(S1-S8); deduction_runner.py --export将推演结果导出为CRM可读JSON
    shared_concepts: [推演计划CRUD, ULDS规律标注, 超越策略, 阻塞问题5阶段流转, 自动拓展]
  - system: 本地模型自成长框架
    relation: CRM的model页面展示君臣佐使模型矩阵和95维能力对比; skills页面展示growth_engine生成的SKILL库(2624自有+4717OpenClaw+29gstack); dashboard的KPI来自growth_engine的累计数据
    shared_concepts: [SKILL技能库统计, 95维能力矩阵, 模型启停控制, 进度追踪(codeGoals/sysGoals), 里程碑]
  - system: 推演引擎(deduction_runner)
    relation: CRM通过loadFromDB()加载deduction_export.json(由deduction_runner生成); 推演中产生的problems同步到CRM的阻塞问题页面
    shared_concepts: [deduction_export.json数据格式, problems状态流转, queue_settings队列配置]
  - system: DiePre推演引擎
    relation: CRM预置了刀模设计推演链工作流(wf2); p_diepre项目是CRM中进度最高的项目(65%)
    shared_concepts: [DXF解析→F→V→F→2D图纸工作流, Playwright验证]
tags:
  - visualization
  - crm
  - single-page-app
  - tailwindcss
  - chartjs
  - dark-theme
  - glassmorphism
  - localstorage
  - project-management
  - deduction-queue
  - skill-library
  - model-comparison
  - problem-tracking
  - workflow-editor
```

---

## 14. 成长方向

| 方向 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| **后端API集成** | 纯前端 localStorage | 接入 api_server.py REST API, 实现多端同步 | 高 |
| **实时数据刷新** | 手动刷新/页面重载 | WebSocket/SSE 推送推演进度和SKILL生成事件 | 高 |
| **工作流可视化编辑器** | 文本输入步骤名称 | 拖拽式DAG编辑器, 可视化定义SKILL调用链 | 高 |
| **95维能力矩阵动态更新** | 硬编码在 DEFAULTS | 从 growth_engine 实时读取最新维度分数 | 中 |
| **用户认证与权限** | 无鉴权本地登录 | 接入 crm_users 表, 角色权限控制 | 中 |
| **推演过程实时监控** | 仅展示最终结果 | 推演中实时显示Phase进度、tokens消耗、节点提取 | 高 |
| **SKILL详情与代码预览** | 仅分类统计 | 点击SKILL查看代码、元数据、依赖图、验证状态 | 中 |
| **移动端适配** | 桌面优先 | 响应式布局, 移动端导航抽屉 | 低 |
| **收敛可视化** | 无 | 集成 DiePre 收敛追踪器数据, 显示参数收敛曲线 | 中 |
| **节点真实性分布图** | 无 | 展示 L0-L5 节点数量分布 + 升降趋势 | 中 |

---

## 源文件清单

| 文件 | 说明 |
|------|------|
| `web/crm.html` (469行) | CRM 单页应用: 导航+9页面+图表+CRUD+模态框 |
| `web/data/crm_data.js` (108行) | 数据层: DATA对象+DEFAULTS+localStorage+DB加载 |
| `web/data/deduction_export.json` | 推演引擎导出数据 (由 deduction_runner.py 生成) |
| `deduction_runner.py` | 推演引擎 (提供 --export 导出 CRM 数据) |
| `deduction_db.py` | 数据库层 (crm_users, task_feedback 等表) |
