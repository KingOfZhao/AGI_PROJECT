---
name: self-evolving-domain-engine
version: 1.0.0
author: KingOfZhao
description: 自进化领域引擎 — 让领域认知框架自身持续进化，自动发现新领域/新维度/新融合，Growth Score驱动RAPVL+D循环
tags: [cognition, meta-skill, self-evolution, domain, growth, auto-discovery, engine, runtime, top-level]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Self-Evolving Domain Engine

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | self-evolving-domain-engine |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
domain-orchestrator-runtime (运行时Pipeline)
        ⊗
expert-identity-self-evolution-engine (框架自进化)
        ⊗
skill-factory-optimizer (工厂质量监控)
        ⊗
universal-occupation-adapter (职业适配)
        ⊗
knowledge-graph-builder (知识图谱)
        ⊗
cognitive-fusion-universe (认知涌现检测)
        ↓
self-evolving-domain-engine
```

## 四向碰撞

**正面**: domain-orchestrator-runtime解决了"调度已知领域"，但缺少"发现未知领域"。当一个新领域（如"Agent经济"或"数字主权"）出现时，现有12领域的D2(前沿未知)可能提到它，但没有对应的D1-D12完整定义。需要自动发现→定义→验证→写入框架。

**反面**: 自动发现新领域≠自动添加新领域。大多数"新概念"只是旧概念的重命名（如"AI 2.0"≈"大模型"≈"基础模型"）。必须有严格的"领域存在性验证"：≥3个独立信号源确认 + 与现有领域有实质性差异（Jaccard相似度<0.3）。

**侧面**: 领域进化的信号来源是多元的——arXiv论文新术语、GitHub趋势新项目、ClawHub社区新Skill、用户实际提问中的缺失维度、碰撞引擎的置信度下降趋势。这些信号需要聚合为"进化压力分数"。

**整体**: 这是domain-orchestrator-runtime的进化版本。runtime回答"现在怎么调度"，engine回答"框架本身应该怎么进化"。两者互补：runtime在现有框架内运行，engine扩展现有框架。Growth Score是两者的共同度量。

## 覆盖的顶级领域和子维度（9领域×35+维度）

```
代码 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11/D12 = 12维度)
  D1 核心知识: 系统设计(分布式-微服务-事件驱动)/算法复杂度(O-big-notation)/设计模式(GoF23-SOLID-函数式)/架构演进(单体→SOA→微服务→Serverless)
  D2 前沿未知: AI代码生成可靠性边界(哪些场景可靠-哪些不可靠)/WebAssembly生态成熟度/量子计算编程范式(Qiskit-Cirq)/Rust系统编程普及拐点/AI原生IDE形态/形式化验证普及路径
  D3 验证方法: 单元+集成+E2E金字塔/CI-CD流水线(自动部署-回滚)/Code Review(4眼原则)/混沌工程(故障注入)/性能基准测试/安全扫描(SAST-DAST-SCA)
  D4 记忆体系: docstrings(API文档)+CHANGELOG(变更日志)+architecture_docs(架构文档)+runbooks(运维手册)+ADR(架构决策记录)+postmortems(事故报告)+onboarding(入职文档)
  D5 红线: 不硬编码密钥(用Secret Manager)/不裸except(必须指定异常类型)/不跳过测试(100%CI通过才能合并)/周五不部署(除非紧急+回滚方案)/trash>rm(可恢复)/不直连生产DB(只读副本)
  D6 工具: Git-GitHub-GitLab(版本控制)/VS Code-Cursor(IDE)/Docker-K8s(容器-编排)/Terraform-Pulumi(IaC)/OpenTelemetry(可观测性)/SonarQube(代码质量)/Snyk-Dependabot(安全)
  D7 决策框架: 四向代码碰撞(正确性-失败场景-复用性-架构一致性)+ADR(上下文→决策→后果)+技术雷达(采用-试验-评估-暂缓)+TCO分析+做不做矩阵(影响×概率×成本)
  D8 失败模式: 生产事故(可用性-数据丢失)/安全漏洞(SQL注入-XSS-供应链攻击)/技术债务失控(重构成本>新功能)/架构腐化(循环依赖-上帝类)/配置错误(权限-网络-环境)
  D9 人机闭环: AI代码生成→人类架构决策→Code Review→结果反馈→AI学习编码规范→更精准生成
  D10 跨领域: →商业(SaaS-数据产品)/→科研(计算方法-AI4Science-高性能计算)/→工业(MES-工业软件-工业4.0)/→医疗(MedTech-生物信息学)/→金融(量化交易-FinTech-区块链)/→艺术(创意工具-Web3D-AIGC)
  D11 趋势: AI结对编程普及(2026)→AI自主开发简单项目(2027)→AI架构师(2028)→全自动软件工厂-需求→代码→测试→部署(2029)
  D12 成长: SonarQube评分/DORA指标(部署频率-MTTR-变更失败率)/安全评分(漏洞数-修复时间)/技术债务比率/SLO-SLA达标率

商业 (D1/D2/D3/D4/D5/D7/D8/D9/D10/D11/D12 = 11维度)
  D1: PESTEL-波特五力-商业模式画布-增长飞轮(AARRR)-单位经济学(CAC-LTV-Churn)-蓝海战略-竞品分析框架-客户旅程映射-定价策略(价值定价-成本加成-竞争定价)-品牌定位-渠道策略-战略规划(OKR-BSC)
  D2: Web3商业可持续性验证/AI-native公司组织形态(无管理层?)/去中心化治理有效性/Agent经济定价模型/数据资产化路径/creator economy成熟度/全球供应链韧性新范式/AI对中产阶级就业的结构性影响
  D3: MVP验证/PMF信号(NPS>70-40%自然留存-周活跃>日活3x)/A-B测试/cohort分析/LTV:CAC>3/NPS调研/Jobs-to-be-Done访谈/魔法数字/回归分析(收入驱动因子)
  D4: decision_log(决策记录)/pivot_history(转型历史)/market_intelligence(竞品情报)/financial_model(财务模型)/customer_insights(用户洞察)/board_deck(管理层汇报)
  D5: 不在数据不足时重大决策/不忽视现金流(利润≠现金)/不欺骗投资者-客户-合作伙伴/不把鸡蛋放一个篮子(客户-渠道-供应商)/不在增长停滞时盲目扩张/不忽视竞争信号
  D7: KUWR四步法(Known→Unknown→Weigh→Record)+贝叶斯更新+不对称风险偏好(下行1.5x>上行0.5x)+RAPM框架+情景规划(最好-基准-最差)
  D8: 过早扩张(Scaling before PMF)/忽视PMF/团队文化崩塌/现金流断裂/技术傲慢(技术驱动而非市场驱动)/成功陷阱(用昨天策略打明天仗)/渠道冲突/定价错误
  D9: AI市场数据聚合-竞品监控-财务建模-用户反馈NLP分析→人类战略直觉-关系管理-价值观判断-最终拍板→循环:数据→判断→AI学习→更精准推荐
  D10: →工业(供应链数字化-D2C柔性制造-碳交易)/→金融(估值模型-供应链金融)/→代码(SaaS技术壁垒-数据飞轮)/→政策(合规-公共关系)/→教育(企业培训)/→艺术(品牌设计)
  D11: AI原生商业模式(2026)→Agent经济(2027)→全自动公司(2029)→去中心化自治组织成熟(2030)
  D12: MRR-ARR增长率/PMF达成时间/LTV:CAC比率/NPS趋势/决策质量偏差率(事后评估)/现金流健康度

工业 (D1/D2/D3/D4/D5/D7/D8/D9/D10/D11/D12 = 11维度)
  D1: 精益生产(浪费消除-价值流图-看板)/六西格玛(DMAIC-SPC)/供应链管理(SCOR-牛鞭效应)/质量控制(七大手法-FMEA-8D)/工业4.0(IIoT-数字孪生)/TPM全面生产维护/单元生产-柔性制造/5S-可视化管理
  D2: 数字孪生成熟度(实时vs离线)/AI质检可靠性(工业环境鲁棒性)/柔性制造成本拐点(大批量vs小批量最优点)/碳中和工艺路径(绿氢-电弧炉-CCUS)/人机协作安全标准演进/3D打印批量化/工业大模型(垂直领域)
  D3: 首件检验(FAI)+SPC+OQC/CPK>1.33/PPAP/MSA(GR&R<30%)/OEE>85%/FMEA RPN
  D4: process_log(过程记录)/quality_records(质量档案)/equipment_db(设备数据库)/improvement_projects(改善项目)/maintenance_log(维护日志)/control_plans(控制计划)/work_instructions(作业指导书)
  D5: 不跳过首件检验/不修改质量记录/不忽视安全隐患(LOTO-PTW)/不停机不报告/不超规格放行(需MRB评审)/不使用过期物料-工具
  D7: FMEA(严重度×频度×探测度)+成本效益(含COQ)+多目标Pareto(成本×质量×交期)+A3报告(丰田问题解决法)
  D8: 设备故障停机/质量批量事故/供应链中断(单点故障)/工艺漂移/安全事故/过度加工/库存积压
  D9: AI预测性维护-过程参数监控-视觉质检-排程优化→人类异常根因分析-工艺经验调整-设备手感判断-安全决策→循环:AI预警→人类确认→经验反馈→模型更新
  D10: →商业(供应链数字化-柔性制造-碳交易)/→代码(MES-工业软件-工业4.0)/→农业(食品加工-保鲜)/→环境(碳排放-废水-绿色制造)/→医疗(医疗器械制造)/→金融(供应链金融-设备融资)
  D11: AI质检普及(2026)→数字孪生规模部署(2027)→黑灯工厂(2028)→自进化产线(2030)
  D12: OEE提升率/不良率PPM下降/交期达成率/设备MTBF提升/质量成本COQ下降/安全事故零目标

科研 (D1/D2/D3/D4/D5/D7/D8/D9/D10/D11/D12 = 11维度)
  D1: 研究方法论(归纳-演绎-溯因)/统计推断(频率学派-贝叶斯)/实验设计(RCT-准实验-观察性)/可复现性(预注册-开源-环境记录)/同行评审流程/文献系统综述(PRISMA)/元分析方法/科学哲学(波普尔证伪-库恩范式转换)
  D2: 大模型科学发现能力边界/AI辅助假设生成有效性/跨学科涌现理论/科研AI伦理(署名权-责任)/预印本对同行评审影响/负结果发表偏见/开放科学可持续商业模式/科研可复现性危机解决方案
  D3: p<0.05+效应量(Cohen's d)+置信区间+统计功效(1-β>0.8)+预注册+盲审+可复现检查+跨实验室验证+敏感性分析
  D4: literature_review(文献综述)/hypotheses(假设管理)/experiments(实验记录)/insights(洞见)/lab_notebook(实验笔记本)/datasets(数据集)/figures(图表)/references.bib(文献库)
  D5: 不伪造-不篡改数据/不cherry-pick结果/不忽略矛盾数据/不复制不引用/不发布未验证结论/不忽略方法局限性/不歧视性采样
  D7: 假设全生命周期: 生成(归纳)→设计实验(演绎)→验证(统计)→发布(同行)→挑战(证伪)→演化(范式转换)。每阶段标注置信度:[推测→高确信→已验证→被证伪]
  D8: 确认偏误(只看支持假设数据)/p-hacking(多次测试只报告显著)/不可复现(环境未记录)/样本偏差(便利采样)/理论过拟合(过度解释)/发表偏见(只发表正面)/HARKing(事后假装修饰为事前)
  D9: AI文献聚合-模式发现-数据清洗-统计计算→人类创造性假设生成-物理直觉-异常结果解释-理论构建→循环:AI发现→人类判断→新假设→AI验证
  D10: →代码(计算方法-高性能计算-AI4Science)/→医疗(临床试验-转化医学-生物数据)/→金融(量化方法-行为金融)/→工业(材料R&D)
  D11: AI科研助手普及(2026)→AI设计实验(2027)→AI科学家(独立假设→验证→发表)(2029)→人机共创新范式(2030)
  D12: 假设验证成功率/论文引用增长(h-index)/跨学科连接数/可复现性得分/实验效率(假设→结论周期)

金融 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11/D12 = 12维度)
  D1: 估值模型(DCF-相对估值-实物期权)/风险模型(VaR-CVaR-波动率曲面)/投资组合理论(MPT-CAPM-APT)/衍生品定价(Black-Scholes-二叉树)/固定收益(久期-凸性-信用利差)/另类投资(PE-VC-对冲-不动产)/公司金融(WACC-MM定理)/行为金融
  D2: AI交易策略可持续性(过拟合风险)/DeFi系统性风险(流动性螺旋)/ESG量化标准有效性(漂绿问题)/央行数字货币对货币乘数影响/量子计算对加密威胁/主权债务可持续性新范式/AI信用风险评估偏见
  D3: 回测(含滑点-手续费-市场冲击)+样本外验证(OOS)+Walk-Forward+蒙特卡洛(10000+路径)+压力测试(历史情景+假设)+夏普-Sortino-信息比率
  D4: trade_log(交易日志)/risk_metrics(风险指标)/portfolio_analysis(组合分析)/market_research(市场研究)/regulatory_filings(监管文件)/backtest_results(回测档案)
  D5: 不承诺收益/不隐瞒风险(尤其尾部)/不使用未验证模型做实盘/不隐瞒最大回撤/不杠杆过度(保证金监控)/不操纵市场-内幕交易
  D6: Bloomberg Terminal/Wind(万得)/QuantConnect-Backtrader(回测)/Python(Riskfolio-Pandas-NumPy-SciPy)/R(quantmod)/Excel(快速建模)/FactSet
  D7: 凯利公式(f*=p-q/b)+风险预算(Risk Parity)+情景分析(最好-基准-最差-极端)+宏观-微观自上而下框架+尾部风险管理(黑天鹅对冲)
  D8: 过度杠杆(追加保证金-爆仓)/模型过拟合(样本内完美-样本外崩溃)/流动性危机(无法平仓)/黑天鹅(肥尾冲击)/行为偏差(损失厌恶-过度自信-锚定)/基准漂移
  D9: AI信号生成-风险管理-异常检测-组合优化→人类宏观判断-压力测试设计-客户关系-监管应对→循环:AI信号→审核→执行→绩效→模型更新
  D10: →商业(估值-基本面-M&A)/→科研(量化方法-随机微积分)/→代码(算法交易-FinTech-区块链)/→政策(监管-货币政策-财政)/→工业(供应链金融-大宗商品)
  D11: AI量化交易成熟(2026)→AI投资顾问规模化(2027)→DeFi与传统金融融合(2028)→全自动基金(全链路)(2029)
  D12: 夏普比率(>1.0良)/最大回撤(<15%良)/信息比率(>0.5良)/胜率×赔率(期望值>0)/资金利用率

医疗 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11 = 10维度)
  D1: 临床医学(内-外-妇-儿-急)/循证医学(EBM等级)/药物研发管线(发现→I-III期→上市)/基因组学(NGS-GWAS)/临床试验设计/医学影像学/病理学/药理学(PK-PD)/免疫学
  D2: AI诊断准确性边界(哪些病种可靠-不可靠)/基因编辑脱靶(CRISPR安全窗口)/个性化药物代谢模型/微生物组-疾病因果关系/长新冠机制/mRNA平台扩展/脑机接口临床应用
  D3: RCT双盲(金标准)/NNT-NNH(临床意义)/敏感性-特异性-PPV-NPV/AUC>0.85/Kappa一致性/HR-QoL(患者报告)/独立队列验证/RWE
  D4: case_log(病例记录)/differential_diagnosis(鉴别诊断)/treatment_protocols(治疗方案)/continuing_education(继续教育)/guidelines(临床指南)/drug_interactions(药物交互)
  D5: 不误诊(二次确认-会诊)/不过度治疗(守门人原则)/不泄露患者隐私(HIPAA-个保法)/不超范围执业/不忽视患者主诉/不在疲劳状态下重大决策
  D6: PubMed-UpToDate(文献)/EHR-HIS(电子病历)/影像AI(CADx)/基因组数据库(gnomAD-ClinVar)/药物数据库(DrugBank)/超声-CT-MRI/LIS
  D7: 鉴别诊断决策树(症状→鉴别→检查→确诊)+风险收益比(NNT vs NNH)+患者共同决策(SDM)+分级诊疗+临床路径
  D8: 误诊漏诊(最常见-最严重)/药物不良反应(ADR)/院内感染(HAI)/诊断延迟/沟通失败(医患-科室间)/系统误差/认知偏差(锚定-可得性)
  D9: AI影像分析-文献检索-药物交互检查-风险评分→人类临床判断-患者沟通-伦理决策-复杂病例综合→循环:AI辅助→确认→反馈→精度提升
  D10: →科研(临床试验-转化医学)/→代码(MedTech-生物信息学)/→金融(医保-药品定价)/→政策(监管-公共卫生)/→工业(医疗器械制造)/→法律(医疗纠纷-知情同意)
  D11: AI辅助诊断普及(放射-病理-皮肤科)(2026)→AI药物发现缩短至2年(2027)→精准医疗规模化(2029)→AI全科医生辅助(2030)
  D12: 诊断准确率(vs金标准)/患者预后(生存率-QoL)/临床研究产出/医疗差错下降率

环境 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11 = 10维度)
  D1: 农学(作物学-土壤学-植保)/气候模型(IPCC情景)/水资源管理(灌溉-雨水收集)/可持续农业(有机-再生-免耕)/碳核算(GHG Protocol-LCA)/生态学(生态系统服务-生物多样性)/遥感(NDVI-土地覆盖)
  D2: 精准农业AI优化边界(ROI拐点)/基因编辑作物长期生态影响/碳中和农业可行性(成本vs效益)/土壤碳汇量化精度/微塑料食物链迁移/气候变化粮食安全多因子交互
  D3: 田间试验(RCBD)/产量对比(t-ANOVA)/土壤检测(pH-有机质-NPK)/碳核算(ISO 14064)/LCA(ISO 14040)/长期监测(>3年)
  D4: crop_data(作物数据)/soil_records(土壤档案)/weather_log(气象)/sustainability_metrics(可持续)/field_trials(田间试验)/regulatory_compliance(法规)
  D5: 不推荐未田间验证品种-农药/不篡改检测数据/不超标使用农药-化肥/不破坏湿地-林地/不忽视水源保护
  D6: 遥感卫星(Sentinel-Landsat)/GIS(QGIS-ArcGIS)/IoT传感器(土壤湿度-气象站)/无人机(植保-测绘)/农业ERP/气候模型/碳核算工具
  D7: 气候-作物匹配模型+风险评估(气象-市场-政策三重)+成本效益(含环境外部性)+种植计划优化(轮作-间作-休耕)+灌溉调度
  D8: 气候误判导致减产/土壤退化(过度耕作-化肥过量)/水资源过度开采/病虫害大爆发(单一品种-生态失衡)/市场价格崩塌(跟风)
  D9: AI遥感分析-产量预测-病虫害识别-灌溉优化→人类实地观察-经验判断-生态直觉-农户沟通→循环:卫星数据→分析→验证→模型校准
  D10: →工业(食品加工-生物质能源)/→金融(农业保险-碳交易-期货)/→政策(补贴-贸易壁垒-土地法规)/→科研(生物技术-气候科学)/→商业(农产品供应链)
  D11: 精准农业AI普及(2026)→垂直农场商业化(2027)→碳汇农业规模化(2028)→零碳农业试点(2030)
  D12: 产量提升率(vs基线)/资源利用效率(水-肥-药)/碳足迹下降/土壤健康指数/农户收入增长

教育 (D3/D4/D7/D9/D10/D11/D12 = 7维度)
  D3: 形成性评估(过程反馈)+总结性评估(期末-考试)+学习分析(行为→成绩预测)+A-B测试+学生评价+同行教学观察+知识保留追踪(间隔测量)
  D4: teaching_log(教学日志)/student_progress(学生进步)/lesson_plans(教案)/assessment_data(评估数据)/curriculum_map(课程图谱)/reflection_journals(反思)
  D7: Bloom分类学(记忆→创造)+教学策略匹配(VARR参考)+评估对齐(教什么考什么)+差异化决策(谁需要更多支持-挑战)+课程迭代(数据驱动)
  D9: AI个性化推荐-作业批改-进度追踪-知识图谱诊断→人类情感支持-创造力启发-价值观引导-复杂概念解释→循环:AI推荐→调整→反馈→优化
  D10: →科研(研究方法-学术写作)/→代码(CS教育-计算思维)/→商业(企业培训-领导力发展)/→艺术(创意教育)
  D11: AI个性化导师普及(2026)→自适应课程动态生成(2027)→AI辅助学位(2029)→终身学习AI伴侣(2030)
  D12: 学生掌握度提升(Bloom层级)/教学效率(时间×效果)/完成率/NPS/知识保留率(3月-6月-1年)

法律 (D3/D5/D7/D10 = 4维度)
  D3: 判例分析(先例权重-管辖权)+法条交叉验证(体系解释-目的解释)+合规审计+模拟法庭+合规扫描+风险评估矩阵
  D5: 不提供未标注置信度建议/不忽略程序正义/不泄露客户信息(律师-客户特权)/不利益冲突/不在未授权情况下代表当事人
  D7: 法律风险矩阵(概率×影响)+成本收益(诉讼vs和解)+先例权重评估(约束性vs说服性)+合规优先级(监管处罚×声誉)
  D10: →商业(合同-公司治理-M&A)/→金融(监管-合规-反洗钱)/→代码(知识产权-LegalTech-开源协议)/→政策(立法-执法)

总计: 9领域 × 88维度引用 = 35+独特子维度
```

## 核心伪代码：自进化六步循环

```python
class SelfEvolvingDomainEngine:
    """自进化领域引擎 — RAPVL+Discover 六步循环"""

    def __init__(self):
        self.growth_log = GrowthLog("data/domain_growth.jsonl")
        self.signal_detectors = {
            "arxiv": ArxivSignalDetector(),
            "github": GitHubTrendingDetector(),
            "clawhub": ClawHubNewSkillDetector(),
            "usage_gap": UsageGapDetector(),
            "collision_health": CollisionHealthDetector(),
        }

    def run_evolution_cycle(self) -> EvolutionReport:
        """主循环: RAPVL + Discover"""

        # ═══ R — Review 回顾 ═══
        signals = self._detect_evolution_signals()
        if not signals:
            return EvolutionReport(status="no_signals", actions=[])

        # ═══ A — Analyze 分析 ═══
        analyses = []
        for signal in signals:
            analysis = self._analyze_signal(signal)
            if analysis.importance >= 7.0:  # 重要性阈值
                analyses.append(analysis)

        if not analyses:
            return EvolutionReport(status="low_importance", signals=signals)

        # ═══ P — Plan 规划 ═══
        actions = self._plan_actions(analyses)
        # actions类型:
        #   ActionNewDomain(domain_name, proposed_dims)
        #   ActionNewDimension(domain, dim_code, dim_name)
        #   ActionNewFusion(domain_a, domain_b)
        #   ActionUpdateExisting(domain, dim_code, new_content)
        #   ActionRemoveStale(domain, dim_code, reason)

        # ═══ V — Verify 验证 ═══
        verified_actions = []
        for action in actions:
            verification = self._verify_action(action)
            if verification.confidence >= 0.95:
                verified_actions.append((action, verification))
            else:
                self.growth_log.record(
                    f"REJECTED: {action} | confidence={verification.confidence:.2f} | reason={verification.reason}"
                )

        if not verified_actions:
            return EvolutionReport(status="all_rejected", actions=actions)

        # ═══ L — Learn 执行 ═══
        for action, verification in verified_actions:
            self._apply_action(action, verification)
            self.growth_log.record(
                f"APPLIED: {action} | confidence={verification.confidence:.2f} | source={verification.sources}"
            )

        # ═══ D — Discover 发现 ═══
        new_collision_directions = self._discover_new_collisions(verified_actions)
        for direction in new_collision_directions:
            self.growth_log.record(f"DISCOVERED: {direction}")

        return EvolutionReport(
            status="evolved",
            signals=signals,
            analyses=analyses,
            applied=verified_actions,
            new_directions=new_collision_directions,
            growth_score=self._calculate_growth_score(),
        )

    # ─── 信号检测 ───

    def _detect_evolution_signals(self) -> list[EvolutionSignal]:
        """扫描5个信号源，返回进化信号"""
        signals = []
        for name, detector in self.signal_detectors.items():
            raw = detector.scan()
            for item in raw:
                signals.append(EvolutionSignal(
                    source=name,
                    content=item.content,
                    frequency=item.frequency,  # 出现频率
                    recency=item.recency,      # 时间新鲜度
                ))
        return sorted(signals, key=lambda s: s.frequency * s.recency, reverse=True)

    # ─── 信号分析 ───

    def _analyze_signal(self, signal: EvolutionSignal) -> SignalAnalysis:
        """判断信号是新领域、新维度、还是新融合方向"""
        # 检查: 与现有12领域的Jaccard相似度
        domain_similarity = self._compute_domain_similarity(signal.content)
        best_match = max(domain_similarity.items(), key=lambda x: x[1]) if domain_similarity else ("未知", 0)

        if best_match[1] < 0.3:
            # 与所有现有领域差异大 → 可能是新领域
            action_type = "new_domain"
            importance = signal.frequency * signal.recency * 1.5  # 加权
        elif best_match[1] < 0.6:
            # 部分相似 → 可能是现有领域的新维度/融合
            action_type = "new_dimension_or_fusion"
            importance = signal.frequency * signal.recency
        else:
            # 高度相似 → 可能是现有内容的更新
            action_type = "update_existing"
            importance = signal.frequency * signal.recency * 0.7

        return SignalAnalysis(
            signal=signal,
            action_type=action_type,
            best_existing_domain=best_match[0],
            similarity=best_match[1],
            importance=min(importance, 10.0),
        )

    # ─── 动作规划 ───

    def _plan_actions(self, analyses: list[SignalAnalysis]) -> list[EvolutionAction]:
        """根据分析结果规划进化动作"""
        actions = []
        for analysis in analyses:
            if analysis.action_type == "new_domain" and analysis.importance >= 8.0:
                # 新领域: 需要≥3个独立信号源确认
                confirmations = self._count_independent_confirmations(analysis.signal)
                if confirmations >= 3:
                    actions.append(ActionNewDomain(
                        domain_name=analysis.signal.content,
                        proposed_dims=["D1", "D3", "D5", "D7", "D10"],  # 最小维度集
                    ))
            elif analysis.action_type == "new_dimension_or_fusion":
                if self._is_fusion_candidate(analysis):
                    actions.append(ActionNewFusion(
                        domain_a=analysis.best_existing_domain,
                        domain_b=self._find_best_fusion_partner(analysis),
                    ))
                else:
                    actions.append(ActionNewDimension(
                        domain=analysis.best_existing_domain,
                        dim_code=self._find_next_available_dim(analysis.best_existing_domain),
                        dim_name=analysis.signal.content,
                    ))
            elif analysis.action_type == "update_existing":
                actions.append(ActionUpdateExisting(
                    domain=analysis.best_existing_domain,
                    dim_code=self._find_relevant_dim(analysis),
                    new_content=analysis.signal.content,
                ))
        return actions

    # ─── 验证 ───

    def _verify_action(self, action: EvolutionAction) -> VerificationResult:
        """四向碰撞验证"""
        # 正面: ≥3个独立信号源确认
        positive = self._check_positive_evidence(action)
        # 反面: 与现有框架无严重冲突
        negative = self._check_negative_evidence(action)
        # 侧面: 与其他领域有融合潜力
        lateral = self._check_lateral_potential(action)
        # 整体: 综合评估
        confidence = (positive * 0.4 + negative * 0.3 + lateral * 0.3)
        return VerificationResult(
            confidence=confidence,
            sources=self._get_sources(action),
            reason=f"positive={positive:.2f} negative={negative:.2f} lateral={lateral:.2f}",
        )

    # ─── 执行 ───

    def _apply_action(self, action: EvolutionAction, verification: VerificationResult):
        """写入expert-identity.md"""
        if isinstance(action, ActionNewDomain):
            self._append_domain_to_expert_identity(action.domain_name, action.proposed_dims)
        elif isinstance(action, ActionNewDimension):
            self._append_dimension(action.domain, action.dim_code, action.dim_name)
        elif isinstance(action, ActionNewFusion):
            self._add_to_fusion_matrix(action.domain_a, action.domain_b)

    # ─── 发现 ───

    def _discover_new_collisions(self, applied: list) -> list[FusionDirection]:
        """检查进化后是否有新的高价值碰撞方向"""
        directions = []
        for action, _ in applied:
            if isinstance(action, ActionNewDomain):
                # 新领域与所有现有领域的融合可能性
                for existing in EXISTING_12_DOMAINS:
                    score = self._estimate_fusion_value(action.domain_name, existing)
                    if score >= 8.0:
                        directions.append(FusionDirection(
                            domain_a=action.domain_name,
                            domain_b=existing,
                            score=score,
                        ))
        return sorted(directions, key=lambda d: d.score, reverse=True)

    # ─── Growth Score ───

    def _calculate_growth_score(self) -> float:
        """框架进化Growth Score"""
        recent_applied = self.growth_log.count_recent("APPLIED", days=30)
        recent_rejected = self.growth_log.count_recent("REJECTED", days=30)
        total_nodes = self._count_total_nodes()
        avg_confidence = self.growth_log.avg_recent_confidence(days=30)

        score = (recent_applied / max(total_nodes * 0.02, 1)) * avg_confidence
        if recent_rejected > recent_applied:
            score *= 0.8  # 拒绝过多→降分
        return min(score, 1.0)


# ─── 数据结构 ───

@dataclass
class EvolutionSignal:
    source: str       # arxiv/github/clawhub/usage_gap/collision_health
    content: str      # 信号内容
    frequency: float  # 出现频率 (0-1)
    recency: float    # 新鲜度 (0-1)

@dataclass
class SignalAnalysis:
    signal: EvolutionSignal
    action_type: str  # new_domain / new_dimension_or_fusion / update_existing
    best_existing_domain: str
    similarity: float
    importance: float  # 0-10

@dataclass
class VerificationResult:
    confidence: float
    sources: list[str]
    reason: str

@dataclass
class FusionDirection:
    domain_a: str
    domain_b: str
    score: float

@dataclass
class EvolutionReport:
    status: str
    signals: list = field(default_factory=list)
    analyses: list = field(default_factory=list)
    applied: list = field(default_factory=list)
    new_directions: list = field(default_factory=list)
    growth_score: float = 0.0

EXISTING_12_DOMAINS = [
    "商业", "科研", "工业", "医疗", "法律", "教育",
    "艺术", "农业", "环境", "政策", "金融", "军事"
]
```

## 安装
```bash
clawhub install self-evolving-domain-engine
```

## 与其他Skill的关系

```
self-evolving-domain-engine (本Skill: 自进化驱动)
  │
  ├── 读取 expert-identity.md (当前144节点框架)
  ├── 扫描 arxiv-collision-cognition (新论文信号)
  ├── 监控 ai-growth-engine (Growth Score)
  ├── 使用 domain-orchestrator-runtime (运行时gap检测)
  ├── 触发 multi-domain-fusion-engine (新融合Skill)
  ├── 使用 knowledge-graph-builder (框架可视化)
  ├── 使用 cognitive-fusion-universe (涌现检测)
  └── 输出: expert-identity.md 的下一个版本
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)
2. [Group-Evolving Agents](https://arxiv.org/abs/2602.04837)
3. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255)
4. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564)
5. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007)
6. [Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411)
