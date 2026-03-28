# AGI v13.3 Cognitive Lattice — 验证清单

> 生成时间：2026-03-20 (更新：2026-03-20)
> 标记说明：🔧=可编码修复/优化 | 👤=需人工处理 | ✅=已验证通过 | ⚠️=需注意

---

## 一、认知格核心 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 1.1 | 四向碰撞 | POST /api/chat 发送问题→检查response中是否包含拆解/合成/碰撞步骤 | 已验证 | — |
| 1.2 | 节点管理 | POST /api/ingest 录入→GET /api/nodes 查询→POST /api/node/verify 验证转化 | 已验证 | — |
| 1.3 | 语义搜索 | POST /api/search 搜索→检查返回相似度分数是否合理(>0.4有效) | 已验证 | — |
| 1.4 | 关系网络 | GET /api/relations→GET /api/graph→检查节点间关联是否正确 | 已验证 | — |
| 1.5 | 自成长引擎 | POST /api/self_growth→检查stats节点/关联数是否增长 | 依赖LLM在线 | 可添加离线模式 |
| 1.12 | 离线成长模式(F7) | POST /api/offline_growth→检查cross_domain/orphan_connected/clustered计数 | 已验证(+90关联) | — |
| 1.13 | 幻觉阈值重置(F8) | 检查zhipu_growth_progress.json中consecutive_falsified字段+growth_log中auto_reset事件 | 已实现 | — |
| 1.14 | GLM-5全速推演(F19) | POST /api/turbo_growth→检查promoted/falsified/deepened计数+model="glm-5"；POST /api/turbo_growth/start→检查status="started"；GET /api/turbo_growth/status→检查turbo_running=true | 已实现 | — |
| 1.15 | 批量问题自动处理(F20) | POST /api/growth/problems/batch_auto→检查total/resolved/dismissed/remaining计数；前端"⚡一键清理"按钮点击→检查问题列表清空 | 已验证(57个问题全部处理) | — |
| 1.11 | 消息自动压缩 | POST /api/tool/solve 发长对话→检查控制台“消息压缩”日志→确认保留最近8条 | 已验证 | — |
| 1.6 | 认知烙印 | POST /api/imprint→检查返回的哲学理解文本 | 已验证 | — |
| 1.7 | 实践清单 | POST /api/practice_list→检查返回steps是否具体可执行 | 已验证 | — |
| 1.8 | 批量导入 | POST /api/batch_import 发送管道格式数据→检查imported/linked计数 | 已验证 | — |
| 1.9 | 节点验证 | POST /api/node/verify {node_id, status:"proven"}→检查new_links数 | 已验证 | — |
| 1.10 | proven快速路径 | 发送与proven节点高度相关的问题→检查metadata.fast_path=true | 已验证 | — |

## 二、对话推理 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 2.1 | 多模式对话 | 分别用mode=code/ask/plan/nocollision/tool测试→检查不同行为 | 已验证 | — |
| 2.2 | 自上而下拆解 | 检查response中“↓ 自上而下拆解”部分→至少3个can_verify=true节点+Schema校验 | F4已修复 | — |
| 2.3 | 自下而上合成 | 检查response中“↑ 自下而上”部分→至少1个跨域问题+Schema校验 | F4已修复 | — |
| 2.4 | 方案合成 | 检查response中“ 解决方案”部分→包含具体步骤/代码 | 取决于LLM | — |
| 2.5 | 双模验证 | 切换到云端后端→检查_verification标签是否出现 | 已验证 | — |
| 2.6 | 幻觉校验 | 云端生成明显错误→检查proven句级锚定+置信度评分→低置信度标记hypothesis | F2已增强 | — |
| 2.7 | 对话停止 | POST /api/chat/stop→检查返回“✘ 已停止” | 已验证 | — |
| 2.8 | 对话历史 | GET /api/chat_history?session_id=xxx→检查记录完整性 | 已验证 | — |
| 2.9 | SSE推送 | GET /api/stream→监听data事件→检查步骤实时到达 | 已验证 | — |
| 2.10 | 能力缺口规则检测(F6) | POST /api/capability_gaps {question:"搜索+PDF+语音"}→检查gaps数组含3条规则匹配 | 已验证(12规则) | — |

## 三、动作引擎 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 3.1 | 文件操作 | POST /api/workspace/read {path:"skills/shell_executor.py"}→检查content | 已验证 | — |
| 3.2 | Python执行 | POST /api/execute {code:"print(1+1)"}→检查stdout="2" | 已验证 | — |
| 3.3 | 技能构建 | POST /api/advanced_action {action:"build_skill",params:{name,code}}→检查文件 | 已验证 | — |
| 3.4 | LLM动作规划 | POST /api/chat mode=code→检查metadata.actions是否合理 | LLM可能输出非法JSON | 已有extract_items容错 |
| 3.5 | 代码合成 | POST /api/advanced_action {action:"code_synthesize",params:{task:"计算斐波那契"}} | 已验证 | — |
| 3.6 | Web研究 | POST /api/advanced_action {action:"web_research",params:{topic:"Python GIL"}} | 需外网+搜索API配置 | 需用户配置搜索API |
| 3.7 | 推理链 | POST /api/advanced_action {action:"reasoning_chain",params:{question:"..."}} | 取决于proven节点覆盖 | 可增强节点覆盖 |
| 3.8 | 声明验证 | POST /api/advanced_action {action:"verify_claim",params:{claim:"..."}} | 已验证 | — |
| 3.9 | 工具锻造 | POST /api/advanced_action {action:"forge_tool",params:{need:"..."}} | 依赖LLM代码生成质量 | 可加代码验证循环 |
| 3.10 | 自主学习 | POST /api/advanced_action {action:"learn_topic",params:{domain:"Python"}} | 依赖Web研究 | 需搜索API |
| 3.11 | 软件工程管线 | POST /api/advanced_action {action:"implement_requirement",params:{requirement:"..."}} | 已验证 | — |
| 3.12 | 增量编辑 | POST /api/advanced_action {action:"edit_existing_code",params:{filepath,requirement}} | 已验证 | — |
| 3.13 | 代码库分析 | POST /api/advanced_action {action:"analyze_codebase",params:{project_dir:"."}} | 已验证 | — |

## 四、智谱AI — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 4.1 | 多模型支持 | GET /api/zhipu/models→检查5个模型全部返回 | ✅ 已验证 | — |
| 4.2 | 智能委托 | POST /api/zhipu/delegate {task:"解释GIL"}→检查model自动选择 | ✅ 已验证(7.1s) | — |
| 4.3 | 代码生成 | POST /api/zhipu/code {task:"斐波那契"}→检查生成代码可运行 | ✅ 已验证(22s) | — |
| 4.4 | 深度推理 | POST /api/zhipu/reasoning {question:"..."}→检查推理链条 | ✅ 已验证 | — |
| 4.5 | 多轮对话 | POST /api/zhipu/chat 连续发送→检查上下文连贯 | ✅ 已验证 | — |
| 4.6 | 自动委托+会话重置 | 用Ollama后端发送复杂问题→检查控制台"自动委托"日志+多轮后检查"会话重置"日志 | ✅ F3已修复 | — |
| 4.7 | 本地校验 | POST /api/zhipu/call {verify:true}→检查verification字段 | ⚠️ 校验粒度粗 | 🔧 可强化:逐句校验+proven比对 |
| 4.8 | 会话管理 | GET /api/zhipu/sessions→POST /api/zhipu/sessions/clear | ✅ 已验证 | — |
| 4.9 | 使用统计 | GET /api/zhipu/stats→检查调用次数/token/费用 | ✅ 已验证 | — |
| 4.10 | 自主成长 | POST /api/growth/start→GET /api/growth/status→检查promoted/falsified | ✅ 已验证 | — |

## 五、Tool Controller — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 5.1 | 持久化运行时 | POST /api/tool/solve "定义x=42然后打印x"→第二次"打印x"检查变量保持 | ✅ 已验证 | — |
| 5.2 | 工具自主调用 | POST /api/tool/solve "偶数平方和"→检查tool_calls有execute_python | ✅ 已验证(2轮49.8s) | — |
| 5.3 | query_knowledge | POST /api/tool/solve "查询Python知识"→检查工具调用→确认返回语义相似度分数 | ✅ F1已升级语义搜索 | — |
| 5.4 | 运行时重置 | POST /api/tool/reset→检查变量清空 | ✅ 已验证 | — |

## 六、超越引擎 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 6.1 | 任务分析 | POST /api/surpass/analyze {task:"设计分布式系统"}→检查complexity/strategy | ✅ 已验证 | — |
| 6.2 | 多模型投票 | POST /api/surpass/vote {task:"..."}→检查共识结果 | ✅ 已验证 | — |
| 6.3 | 迭代精炼 | POST /api/surpass/code {task:"排序算法"}→检查迭代次数+可执行 | ✅ 已验证 | — |
| 6.4 | 结构化CoT | POST /api/surpass/reason {task:"..."}→检查分步推理 | ✅ 已验证 | — |

## 七、集群/分布式 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 7.1 | 本机信息 | GET /api/cluster/local→检查IP/hostname/OS | ✅ 已验证 | — |
| 7.2 | 局域网扫描 | POST /api/cluster/scan→检查found设备列表 | ⚠️ 需局域网环境 | 👤 需多设备 |
| 7.3 | 迁移包 | POST /api/migrate/package→检查size>0 | ⚠️ 需目标设备 | 👤 需目标机运行接收端 |
| 7.4 | 飞书集成 | POST /api/feishu/test→检查消息发送成功 | ⚠️ 需飞书配置 | 👤 需用户配置Webhook |

---

## 八、数学公式引擎 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 8A.1 | 问题形式化 | POST /api/math/formalize {problem:"求解x²+3x-4=0"}→检查返回公式ID+LaTeX表达 | ✅ 已验证 | — |
| 8A.2 | 公式执行 | POST /api/math/execute {formula_id:"quadratic",variables:{a:1,b:3,c:-4}}→检查x1=1,x2=-4 | ✅ 已验证 | — |
| 8A.3 | 公式拆解 | POST /api/math/decompose {problem:"复杂热处理问题"}→检查子公式树节点数>1 | ✅ 已验证 | — |
| 8A.4 | 温差推演 | POST /api/math/temperature {temperature:900,carbon:0.5,delta_t:10}→检查相区+扩散系数+PID建议 | ✅ 已验证 | — |
| 8A.5 | 四向碰撞推演 | POST /api/math/collision {t_start:25,t_end:1600,t_step:100}→检查相变点检测 | ✅ 已验证 | — |
| 8A.6 | 公式列表 | GET /api/math/formulas→检查返回18个公式 | ✅ 已验证 | — |
| 8A.7 | proven公式注入 | POST /api/math/inject→检查injected节点数>0 | ✅ 已验证 | — |
| 8A.8 | PID参数建议 | 温差推演结果中检查pid_suggestion字段含Kp/Ki/Kd | ✅ 已验证 | — |
| 8A.9 | 控制方法推荐 | 温差推演检查control_method_recommendation字段 | ✅ 已验证 | — |

## 九、工业制造扩展 — 验证方式

| # | 能力 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 9A.1 | 谐波减速器3D | 运行harmonic_flexspline_generator.py→检查生成STEP文件>1MB | ✅ 已验证(1.8MB) | — |
| 9A.2 | 谐波减速器2D | 检查flexspline_2d_*.dxf生成→检查实体数>50 | ✅ 已验证(81实体) | — |
| 9A.3 | 法兰盘DXF | 检查workspace/outputs/flange_*.dxf生成+可用AutoCAD打开 | ✅ 已验证 | — |
| 9A.4 | 热处理曲线DXF | 检查heat_treatment_curve_*.dxf生成+温度-时间轴 | ✅ 已验证 | — |
| 9A.5 | 工艺流程图DXF | 检查process_flow_*.dxf生成+步骤连接箭头 | ✅ 已验证 | — |
| 9A.6 | 工业概念→工艺清单 | POST /api/tool/solve "设计法兰盘加工工艺"→检查返回JSON步骤 | ⚠️ 依赖LLM | 🔧 可加模板兆底 |
| 9A.7 | DXF→工艺规划 | dxf_to_process_plan(法兰盘.dxf)→检查包含材料/刀具/参数 | ⚠️ 依赖LLM | 🔧 可加模板兆底 |
| 9A.8 | 热处理方案生成 | generate_heat_treatment({material:"45钢"})→检查温度/时间/冷却方式字段 | ✅ 已验证 | — |

## 十、新增技能模块 — 验证方式

| # | 技能 | 验证方式 | 当前状态 | 处理方 |
|---|------|----------|----------|--------|
| 7.21 | 数学公式引擎 | GET /api/math/formulas→返回18公式+POST /api/math/execute测试计算 | ✅ 已验证 | — |
| 7.22 | 谐波减速器生成 | python harmonic_flexspline_generator.py→检查STEP+DXF输出 | ✅ 已验证 | — |
| 7.23 | 基准测试 | from benchmark_test import run_benchmark; run_benchmark()→检查5维度得分 | ✅ 可用 | — |
| 7.24 | 架构缺陷修复 | from architecture_defect_repair_tool import analyze_architecture→检查success=True | ⚠️ 框架级 | 🔧 需完善检测逻辑 |
| 7.25 | 架构监控 | from system_architecture_monitor import monitor_system→检查报告字段 | ⚠️ 框架级 | 🔧 需完善监控逻辑 |
| 7.26 | 文件计数器 | from file_counter import count_total_files; count_total_files(".")→检查total_files>0 | ✅ 已验证 | — |
| 7.27 | 数据结构管理 | import测试→检查函数可调用 | ⚠️ 未深度验证 | 🔧 需测试用例 |

---

## 关键可编码修复项 (🔧 优先级排序)

### P0 — 最高优先级（✅ 全部已完成）

| # | 问题 | 修复方案 | 状态 |
|---|------|----------|------|
| F1 | Tool Controller query_knowledge仅关键词匹配 | 升级为调用lattice.find_similar_nodes语义搜索 | ✅ 已完成 |
| F2 | 幻觉校验深度不足 | 增强verified_llm_call:proven句级锚定+置信度评分+多轮校验 | ✅ 已完成 |
| F3 | 自动委托缺少上下文重置 | 累积对话超阈值时自动重置messages列表 | ✅ 已完成 |
| F4 | 拆解结果缺少格式校验 | 对extract_items结果增加schema验证和容错 | ✅ 已完成 |

### P1 — 高优先级（下一步实施）

| # | 问题 | 修复方案 | 影响范围 |
|---|------|----------|----------|
| F5 | Supervisor/Worker图结构 | 本地Ollama监督+智谱Worker执行 | 全局架构 |
| F6 | 能力缺口无规则兆底 | 增加关键词+模式匹配的能力缺口规则检测器 | 2.10 |
| F7 | 自成长无离线模式 | 添加纯proven节点碰撞的离线成长路径 | 1.5 |
| F8 | zhipu_growth缺少幻觉阈值自动重置 | 连续falsified超阈值时自动清除会话 | 4.10 |
| F9 | 问题清单自动处理 | 前端"自动处理"按钮+判断能力覆盖 | 前端+后端 |
| F18 | proven公式节点注入DB | 将18个数学公式+12个铁碳数据点注入晶格 | 数据资产 |

### P2 — 需人工处理项 (👤)

| # | 问题 | 需要 |
|---|------|------|
| H1 | Web研究需搜索API | 用户配置Google/Bing搜索API Key |
| H2 | 飞书集成需配置 | 用户提供Webhook URL + App ID/Secret |
| H3 | 分布式推理需多设备 | 用户部署多台Ollama节点 |
| H4 | DWG→DXF转换 | 用户安装ODA File Converter |
| H5 | 工业参数实际验证 | 需领域专家人工校验 |
| H7 | 真实炉温数据采集 | 需热处理炉温度记录仪数据(毫秒级) |
| H8 | 工业PLC/DCS编程 | 机器语言控制温度需工控编程(梯形图/ST) |
| H11 | PID参数实际调试 | 建议参数需在实际控制器上调试 |
| H12 | 高精度传感器选型 | 零温差目标需±0.1°C热电偶采购 |
