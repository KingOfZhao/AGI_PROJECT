# AGI v13.3 Cognitive Lattice — 待实现能力清单

> 生成时间：2026-03-20
> 标记说明：🔧=可通过编码实现 | 👤=需人工处理 | ⭐=最高优先级

---

## ⭐ 最高优先级 — 本地模型+proven节点+智谱API协同强化

### 🔧 F1. Tool Controller query_knowledge 升级为语义搜索
- **现状**: 仅做SQL LIKE关键词匹配，无法利用1200+ proven节点的语义关系
- **目标**: 调用 lattice.find_similar_nodes() 进行embedding语义搜索
- **实现**: 修改 tool_controller.py 的 _query_knowledge 函数
- **优先级**: P0

### 🔧 F2. 幻觉校验增强 — Chain-of-Verification + proven节点强比对
- **现状**: verified_llm_call 仅做一次本地校验，校验粒度粗
- **目标**: 
  - 逐句与proven节点相似度比对
  - 置信度评分(0-1)
  - 低置信度部分标记为hypothesis而非直接采纳
  - 参考Zep的Chain-of-Verification模式
- **实现**: 增强 agi_v13_cognitive_lattice.py 的 verified_llm_call
- **优先级**: P0

### 🔧 F3. 智谱API会话自动重置（防幻觉累积）
- **现状**: 多轮对话无上下文阈值重置机制
- **目标**:
  - 会话token超过阈值(如8000)时自动重置messages
  - 连续验证失败超过N次时强制新建会话
  - 重置时保留关键proven节点上下文
  - 参考LangGraph state reset最佳实践
- **实现**: 修改 zhipu_ai_caller.py + tool_controller.py
- **优先级**: P0

### 🔧 F4. 拆解结果Schema校验与容错增强
- **现状**: extract_items对LLM输出的JSON解析仅做基础容错
- **目标**: 添加JSON Schema验证 + 字段默认值 + 格式自修复
- **实现**: 修改 agi_v13_cognitive_lattice.py 的 extract_items
- **优先级**: P1

---

## 高优先级 — 能力增强

### 🔧 F5. 本地模型Supervisor + 智谱Worker LangGraph图结构
- **现状**: 本地模型与智谱API的协同是硬编码的if-else逻辑
- **目标**:
  - 构建LangGraph风格的Supervisor/Worker节点图
  - Supervisor(本地Ollama)负责: 规划、验证、记忆管理、最终合成
  - Worker(智谱API)负责: 重计算(代码生成、长上下文、agentic coding)
  - 重叠节点验证通过后固化为proven，不再重复调用
- **实现**: 新建 workspace/skills/supervisor_graph.py
- **优先级**: P1
- **依赖**: 安装 langgraph (pip install langgraph)

### 🔧 F6. 能力缺口规则检测器
- **现状**: 仅依赖LLM判断能力缺口
- **目标**: 增加关键词+模式匹配+错误类型分析的规则检测
- **实现**: 在 action_engine.py 增加 detect_capability_gap() 函数
- **优先级**: P1

### 🔧 F7. 自成长离线模式
- **现状**: 自成长依赖LLM在线
- **目标**: 纯proven节点embedding碰撞的离线成长路径
- **实现**: 在 agi_v13_cognitive_lattice.py 的 SelfGrowthEngine 增加 offline_cycle()
- **优先级**: P1

### 🔧 F8. zhipu_growth幻觉阈值自动重置
- **现状**: 成长循环中连续falsify无自动重置
- **目标**: 连续falsified>3次时自动清除会话上下文
- **实现**: 修改 workspace/skills/zhipu_growth.py
- **优先级**: P1

### 🔧 F9. 问题清单管理+自动处理按钮
- **现状**: 成长过程发现的问题有记录但缺少自动处理判断
- **目标**:
  - 前端增加"🤖 自动处理"按钮
  - 判断当前哪些问题可被模型处理(有对应proven节点覆盖)
  - 可处理的自动执行，不可处理的标记给用户
- **实现**: 修改 api_server.py + web/index.html
- **优先级**: P1

---

## 中优先级 — 新增能力

### 🔧 F10. LangChain智谱集成(ChatZhipuAI)
- **现状**: 直接使用OpenAI兼容接口调用智谱
- **目标**: 集成langchain_community.chat_models.ChatZhipuAI，支持streaming/async/tool_calling
- **实现**: 新建技能模块或修改现有调用方式
- **优先级**: P2
- **依赖**: pip install langchain-community httpx httpx-sse PyJWT

### 🔧 F11. 时间知识图谱（Temporal Knowledge Graph）
- **现状**: 节点有created_at/last_verified_at但无时间衰减查询
- **目标**:
  - 查询时考虑节点新鲜度(时间衰减权重)
  - 冲突检测(同一领域的新旧节点矛盾)
  - 参考Zep的Temporal Knowledge Graph模式
- **实现**: 增强 find_similar_nodes 加入时间权重
- **优先级**: P2

### 🔧 F12. 自一致性验证(Self-Consistency)
- **现状**: 单次LLM调用取结果
- **目标**: 关键任务多次采样→取共识(参考Zep推荐)
- **实现**: 在 surpass_engine.py 的 EnsembleVoter 基础上增加同模型多次采样
- **优先级**: P2

### 🔧 F13. 结构化错误恢复
- **现状**: 工具执行失败仅记录错误
- **目标**: 错误自动分类→选择恢复策略→重试/降级/报告
- **实现**: 在 action_engine.py 增加 ErrorRecoveryEngine
- **优先级**: P2

### 🔧 F14. proven节点质量分层
- **现状**: 所有proven节点权重相同
- **目标**: 根据验证来源/访问频次/关联数量计算quality_score
- **实现**: 修改数据库schema + find_similar_nodes加权
- **优先级**: P2

---

## 低优先级 — 扩展能力

### 🔧 F15. 流式对话响应(Streaming Chat)
- **现状**: 对话完成后一次性返回
- **目标**: SSE流式输出每个步骤的文本
- **优先级**: P3

### 🔧 F16. 多语言代码生成扩展
- **现状**: 主要支持Python
- **目标**: 扩展Dart/Kotlin/Swift代码生成+验证
- **优先级**: P3

### 🔧 F17. API鉴权
- **现状**: 所有API无鉴权
- **目标**: 添加简单Token鉴权保护关键API
- **优先级**: P3

---

## 👤 需人工处理项

| # | 项目 | 所需操作 | 优先级 |
|---|------|----------|--------|
| H1 | Web研究搜索API | 申请并配置Google Custom Search或Bing Search API Key | P1 |
| H2 | 飞书集成配置 | 创建飞书应用→获取Webhook URL + App ID/Secret→通过前端配置 | P2 |
| H3 | 多设备分布式部署 | 在其他设备安装Ollama+运行migrate_receiver.py | P2 |
| H4 | ODA File Converter | 下载安装用于DWG→DXF转换(Windows/Mac) | P3 |
| H5 | 工业领域知识录入 | 领域专家将热处理/加工参数等验证后录入为proven节点 | P3 |
| H6 | LangGraph依赖安装 | pip install langgraph langchain-community (F5/F10依赖) | P1 |

---

## 实施路线图

```
Phase 1 (立即) — P0修复
  F1: query_knowledge语义搜索升级
  F3: 智谱会话自动重置
  F2: 幻觉校验增强
  F4: 拆解结果Schema校验

Phase 2 (本周) — P1增强  
  F5: Supervisor/Worker图结构
  F6: 能力缺口规则检测
  F7: 自成长离线模式
  F8: 成长幻觉重置
  F9: 问题清单自动处理

Phase 3 (下周) — P2新增
  F10: LangChain集成
  F11: 时间知识图谱
  F12: 自一致性验证
  F13: 结构化错误恢复
  F14: proven质量分层
```
