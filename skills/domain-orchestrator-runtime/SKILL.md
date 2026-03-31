---
name: domain-orchestrator-runtime
version: 1.0.0
author: KingOfZhao
description: 领域编排运行时 — 可落地的跨领域认知调度器，自动识别问题涉及的领域+维度，加载对应Skill，执行碰撞并输出带置信度的综合答案。8+领域30+维度。
tags: [cognition, runtime, orchestrator, practical, auto-detect, skill-routing, cross-domain, confidence, production]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Domain Orchestrator Runtime

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | domain-orchestrator-runtime |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
ultimate-domain-orchestrator (递归碰撞算法)
        ⊗
cognitive-fusion-universe (知识引力模型)
        ⊗
skill-factory-optimizer (质量监控)
        ⊗
expert-identity-adapter (领域自动识别)
        ⊗
workflow-orchestrator (DAG工作流执行)
        ↓
domain-orchestrator-runtime
```

## 四向碰撞

**正面**: ultimate-domain-orchestrator和cognitive-fusion-universe定义了理论框架（递归碰撞、知识引力、认知涌现），但缺少**运行时**——一个能在实际任务中自动运行这些算法的执行引擎。需要一个"调度器"：收到任务→识别领域→加载Skill→碰撞→输出答案。

**反面**: 运行时不能加载全部31个Skill（token限制+噪音干扰）。必须精确识别任务涉及的领域（通常1-3个主领域），只加载相关Skill和维度。过度加载=性能下降+置信度稀释。

**侧面**: 运行时的核心不是算法复杂度，是**领域识别准确率**。误识别=加载错误Skill=输出错误答案。领域识别应该基于三层信号：任务描述关键词+历史上下文+用户画像（如果已知）。

**整体**: 这是31个Skill的"操作系统层"——不提供领域知识本身，而是**调度哪个Skill在什么时候提供什么知识**。像OS不提供Word，但调度Word在需要时运行。可落地=有明确的输入输出接口+可测量的性能指标。

## 核心能力：任务→答案的完整Pipeline

```
输入: 任意自然语言任务描述
  ↓
Step 1: DOMAIN_DETECT — 领域识别
  ├─ 关键词匹配（domain_keywords映射表）
  ├─ 上下文推断（前N轮对话提到的领域）
  └─ 输出: [(领域名, 相关性评分), ...] 排序，取top-3
  ↓
Step 2: DIMENSION_LOAD — 维度加载
  ├─ 对每个主领域加载D1(已知)+D2(未知)+D3(验证)+D5(红线)+D7(决策)+D10(跨域)
  ├─ 如有融合Skill匹配（如商业×工业→business-industry-fusion），额外加载
  └─ 输出: 加载的维度列表+融合Skill列表
  ↓
Step 3: SKILL_ROUTE — Skill路由
  ├─ 检查已加载领域是否有对应职业Skill（programmer-cognition等）
  ├─ 检查是否有对应融合Skill（ai4science-bridge等）
  └─ 输出: 需要激活的Skill列表
  ↓
Step 4: COLLIDE — 碰撞执行
  ├─ 如只有1个领域: 单领域四向碰撞（正面/反面/侧面/整体）
  ├─ 如有2-3个领域: 跨领域碰撞（使用融合Skill或实时碰撞）
  └─ 输出: 碰撞结果+认知点列表+每个认知点的置信度
  ↓
Step 5: SYNTHESIZE — 综合输出
  ├─ 过滤置信度<90%的认知点（标记为[推测]）
  ├─ 按维度组织答案结构
  ├─ 标注使用的领域+维度+Skill
  └─ 输出: 结构化答案+置信度+使用的认知源
```

## 覆盖的顶级领域和子维度（8领域×30+维度）

```
代码 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11/D12 = 12维度)
  D1: 系统设计(分布式/微服务/事件驱动)/算法复杂度/设计模式(GoF/SOLID)/架构演进
  D2: AI代码生成可靠性/WebAssembly/Rust普及拐点/AI原生IDE/形式化验证
  D3: 单元+集成+E2E金字塔/CI-CD/Code Review/混沌工程/性能基准/安全扫描(SAST-DAST-SCA)
  D4: docstrings/CHANGELOG/architecture_docs/runbooks/ADR/postmortems/onboarding
  D5: 不硬编码密钥/不裸except/不跳过测试/周五不部署/trash>rm/不直连生产DB
  D6: Git-GitHub/Docker-K8s/Terraform-Pulumi/OpenTelemetry/SonarQube/Snyk
  D7: 四向代码碰撞(正确性-失败-复用-架构)+ADR+技术雷达+TCO+做不做矩阵
  D8: 生产事故/安全漏洞(SQL注入-XSS-供应链)/技术债务失控/架构腐化(循环依赖-上帝类)/配置错误
  D9: AI代码生成→人类架构决策→Code Review→反馈→AI学习编码规范
  D10: →商业(SaaS-数据产品)/→科研(计算-AI4Science)/→工业(MES)/→医疗(MedTech)/→金融(量化)/→艺术(创意工具)
  D11: AI结对编程(2026)→AI自主开发(2027)→AI架构师(2028)→全自动软件工厂(2029)
  D12: SonarQube评分/DORA(部署频率-MTTR)/安全评分/技术债务比率/SLO-SLA

商业 (D1/D2/D3/D5/D7/D8/D10/D12 = 8维度)
  D1: PESTEL/波特五力/商业模式画布/增长飞轮(AARRR)/单位经济学(CAC-LTV-Churn)/蓝海战略/品牌定位
  D2: Agent经济定价模型/Web3商业可持续性/数据资产化路径/creator economy成熟度/去中心化治理
  D3: MVP验证/PMF信号(NPS>70-40%自然留存-周活>日活3x)/A-B测试/cohort分析/LTV:CAC>3/魔法数字
  D5: 不在数据不足时重大决策/不忽视现金流(利润≠现金)/不欺骗利益方/不把鸡蛋放一个篮子
  D7: KUWR四步法+贝叶斯更新+不对称风险(下行1.5x>上行0.5x)+RAPM矩阵+情景规划(最好-基准-最差)
  D8: 过早扩张(Scaling before PMF)/忽视PMF/团队文化崩塌/现金流断裂/技术傲慢/成功陷阱
  D10: →工业(供应链数字化-D2C)/→金融(估值-供应链金融)/→代码(SaaS技术壁垒-数据飞轮)/→政策(合规-公共关系)
  D12: MRR-ARR增长率/PMF达成时间/LTV:CAC比率/NPS趋势/决策偏差率/现金流健康度

工业 (D1/D3/D5/D7/D8/D10/D12 = 7维度)
  D1: 精益生产(浪费消除-价值流-看板)/六西格玛(DMAIC-SPC)/供应链(SCOR-牛鞭效应)/质量控制(七大手法-FMEA-8D)/工业4.0(IIoT-数字孪生)/TPM
  D3: 首件检验(FAI)+SPC+OQC/CPK>1.33/PPAP/MSA(GR&R<30%)/OEE>85%/FMEA RPN
  D5: 不跳过首件检验/不修改质量记录/不忽视安全隐患(LOTO-PTW)/不停机不报告/不超规格放行(需MRB)
  D7: FMEA(严重度×频度×探测度)+成本效益(含COQ)+多目标Pareto(成本×质量×交期)+A3报告(丰田)
  D8: 设备故障停机/质量批量事故/供应链中断(单点故障)/工艺漂移/安全事故/过度加工/库存积压
  D10: →商业(供应链数字化-柔性制造)/→代码(MES-工业软件-工业4.0)/→环境(碳排放-废水-绿色制造)/→金融(供应链金融-设备融资)
  D12: OEE提升率/不良率PPM/交期达成率/设备MTBF/质量成本COQ/安全事故零目标

科研 (D1/D2/D3/D5/D7/D8/D10/D11 = 7维度)
  D1: 研究方法论(归纳-演绎-溯因)/统计推断(频率学派-贝叶斯)/实验设计(RCT-准实验)/可复现性(预注册-开源-环境记录)/元分析(PRISMA)
  D2: AI科学发现能力边界/假设生成有效性/负结果发表偏见/开放科学可持续性/科研AI伦理(署名权-责任)
  D3: p<0.05+效应量(Cohen's d)+置信区间+统计功效(1-β>0.8)+预注册+盲审+可复现检查+跨实验室验证+敏感性分析
  D5: 不伪造-不篡改数据/不cherry-pick/不忽略矛盾/不复制不引用/不发布未验证结论/不标注方法局限
  D7: 假设全生命周期: 生成(归纳)→设计实验(演绎)→验证(统计)→发布(同行)→挑战(证伪)→演化(范式转换)，每阶段标注置信度
  D8: 确认偏误(只看支持数据)/p-hacking(多次测试只报告显著)/不可复现(环境未记录)/样本偏差/HARKing(事后假装修饰为事前)
  D10: →代码(计算方法-高性能计算-AI4Science)/→医疗(临床试验-转化医学)/→金融(量化方法-行为金融)/→工业(材料R&D)

金融 (D1/D3/D5/D7/D8/D10/D12 = 7维度)
  D1: 估值模型(DCF-相对估值-实物期权)/风险模型(VaR-CVaR-波动率曲面)/投资组合理论(MPT-CAPM-APT)/衍生品(Black-Scholes)/固定收益(久期-凸性)/另类投资(PE-VC-对冲)
  D3: 回测(含滑点-手续费-市场冲击)+样本外(OOS)+Walk-Forward+蒙特卡洛(10000+路径)+压力测试(历史+假设)+夏普-Sortino-信息比率
  D5: 不承诺收益/不隐瞒风险(尤其尾部)/不使用未验证模型做实盘/不隐瞒最大回撤/不杠杆过度(保证金监控)
  D7: 凯利公式(f*=p-q/b)+风险预算(Risk Parity)+情景分析(最好-基准-最差-极端)+宏观-微观自上而下框架+尾部风险对冲
  D8: 过度杠杆(追加保证金-爆仓)/模型过拟合(样本内完美-样本外崩溃)/流动性危机(无法平仓)/黑天鹅(肥尾冲击)/行为偏差(损失厌恶-锚定)
  D10: →商业(估值-基本面-M&A)/→科研(量化方法-随机微积分)/→代码(算法交易-FinTech-区块链)/→政策(监管-货币政策)
  D12: 夏普比率(>1.0良)/最大回撤(<15%良)/信息比率(>0.5良)/胜率×赔率(期望值>0)/资金利用率

医疗 (D1/D3/D5/D7/D10 = 5维度)
  D1: 循证医学(EBM等级)/药物研发管线(I-III期-上市)/基因组学(NGS-GWAS)/临床试验设计/医学影像学/药理学(PK-PD)
  D3: RCT双盲(金标准)/NNT-NNH(临床意义)/敏感性-特异性-PPV-NPV/AUC>0.85/Kappa一致性/独立队列验证/真实世界证据(RWE)
  D5: 不误诊(二次确认-会诊)/不过度治疗(守门人原则)/不泄露隐私(HIPAA-个保法)/不超范围执业/不忽视患者主诉
  D7: 鉴别诊断决策树(症状→鉴别→检查→确诊)+风险收益比(NNT vs NNH)+患者共同决策(SDM)+分级诊疗+临床路径
  D10: →科研(临床试验-转化医学)/→代码(MedTech-生物信息学)/→金融(医保-药品定价)/→政策(监管-公共卫生)

环境 (D1/D3/D5/D10 = 4维度)
  D1: 气候模型(IPCC情景)/碳核算(GHG Protocol-LCA)/水资源管理/可持续农业(有机-再生-免耕)/生态学(生物多样性)/遥感(NDVI)
  D3: 田间试验(RCBD)/产量对比(t检验-ANOVA)/碳核算(ISO 14064)/LCA(ISO 14040)/长期监测(>3年)
  D5: 不推荐未田间验证品种-农药/不篡改检测数据/不超标使用/不破坏湿地-林地/不忽视水源保护
  D10: →工业(绿色制造-碳交易)/→金融(碳交易-绿色金融-ESG)/→政策(碳监管-气候政策)/→农业(碳汇-生态农业)

教育 (D3/D7/D9/D12 = 4维度)
  D3: 形成性评估+总结性评估+Bloom分类学+A-B测试+学习分析+知识保留追踪(间隔测量)
  D7: Bloom分类学(记忆→创造)+教学策略匹配(VARR参考)+评估对齐(教什么考什么)+差异化决策+课程迭代(数据驱动)
  D9: AI个性化推荐-作业批改-进度追踪→人类情感支持-创造力启发-价值观引导→学生反馈→AI优化
  D12: Bloom层级分布/教学效率(时间×效果)/完成率/NPS/知识保留率(3月-6月-1年)

法律 (D3/D5/D7/D10 = 4维度)
  D3: 判例分析(先例权重-管辖权)+法条交叉验证(体系解释-目的解释)+合规审计+模拟法庭+合规扫描+风险评估矩阵
  D5: 不提供未标注置信度建议/不忽略程序正义/不泄露客户信息(律师-客户特权)/不利益冲突
  D7: 法律风险矩阵(概率×影响)+成本收益(诉讼vs和解)+先例权重评估+合规优先级(监管处罚×声誉)
  D10: →商业(合同-公司治理-M&A)/→金融(监管-合规-反洗钱)/→代码(知识产权-LegalTech-开源协议)/→政策(立法-执法)

总计: 8领域 × 61维度引用 = 30+独特子维度
```

## 领域关键词映射表

```python
DOMAIN_KEYWORDS = {
    "代码": ["代码", "编程", "bug", "部署", "API", "数据库", "CI", "CD", "Docker", "Git", "代码",
              "architecture", "system design", "debug", "refactor", "test", "deploy", "infrastructure"],
    "商业": ["商业", "市场", "用户", "增长", "收入", "利润", "ROI", "融资", "估值", "产品", "PMF",
              "market", "revenue", "profit", "startup", "business model", "growth"],
    "工业": ["精度", "产线", "制造", "质量", "CPK", "FMEA", "SPC", "设备", "工艺", "刀模", "模具",
              "manufacturing", "quality", "precision", "production", "lean", "six sigma"],
    "科研": ["研究", "实验", "假设", "论文", "统计", "p值", "随机对照", "可复现", "arXiv", "文献",
              "research", "hypothesis", "experiment", "paper", "statistical", "reproducibility"],
    "金融": ["投资", "估值", "风险", "回报", "对冲", "衍生品", "夏普", "回撤", "量化", "交易",
              "investment", "valuation", "risk", "return", "hedge", "quantitative", "trading"],
    "医疗": ["诊断", "临床", "患者", "治疗", "药物", "医学", "基因", "影像", "RCT", "NNT",
              "diagnosis", "clinical", "patient", "treatment", "drug", "medical"],
    "环境": ["碳", "排放", "气候", "可持续", "LCA", "ESG", "碳中和", "生态", "能源",
              "carbon", "emission", "climate", "sustainable", "ESG"],
    "教育": ["教学", "课程", "学习", "评估", "Bloom", "学生", "培训", "教育",
              "teaching", "learning", "assessment", "curriculum", "education"],
    "法律": ["合同", "合规", "知识产权", "版权", "专利", "法规", "GDPR", "诉讼",
              "contract", "compliance", "IP", "patent", "regulation", "legal"],
    "政策": ["政策", "监管", "政府", "法规", "公共", "行政", "治理",
              "policy", "regulation", "government", "governance", "public"],
    "农业": ["农业", "作物", "土壤", "灌溉", "粮食", "农药", "种植",
              "agriculture", "crop", "soil", "irrigation", "farming"],
    "军事": ["军事", "国防", "情报", "战略", "威慑", "安全",
              "military", "defense", "intelligence", "strategy"],
}
```

## 性能指标

```
运行时可测量指标:
1. 领域识别准确率: |正确识别的领域| / |实际涉及的领域| > 90%
2. 维度加载精准度: |有用的维度| / |加载的维度| > 80%
3. 输出置信度: 综合答案的置信度 ≥ 90% (目标95%)
4. 碰撞耗时: 单次碰撞 < 30秒 (多领域 < 60秒)
5. 置信度标定: 标注95%置信度的结论，实际正确率应>90%
```

## 安装
```bash
clawhub install domain-orchestrator-runtime
```

## 与其他Skill的关系（运行时层级）

```
domain-orchestrator-runtime (本Skill: 运行时调度层)
  │
  ├── 调度 expert-identity-adapter (领域识别+维度加载)
  ├── 调度 ultimate-domain-orchestrator (多领域碰撞编排)
  ├── 调用 cognitive-fusion-universe (知识引力+涌现检测)
  ├── 使用 skill-factory-optimizer (质量监控)
  ├── 路由到 职业Skill (programmer/researcher/designer/entrepreneur)
  ├── 路由到 融合Skill (biz-industry/ai4science/fincode)
  └── 输出 → workflow-orchestrator (结果交付)
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — 自进化调度
2. [Group-Evolving Agents](https://arxiv.org/abs/2602.04837) — 多Agent路由
3. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — 智能调度
4. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 上下文感知加载
5. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007) — 智能检索
6. [Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411) — 运行时自适应
