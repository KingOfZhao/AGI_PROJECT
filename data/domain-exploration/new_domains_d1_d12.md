# 新增5领域完整D1-D12维度定义

> 2025-03-31 极限推演产出
> 数据源: Wikipedia新兴技术 + ML Summit 53份PDF + 2025前沿趋势

---

## D13: 认知神经科学 (Cognitive Neuroscience)

| 维度 | 内容 |
|------|------|
| D1 核心知识 | 脑功能分区(前额叶-执行/颞叶-记忆/顶叶-空间/枕叶-视觉/小脑-运动/杏仁核-情绪/海马体-情景记忆)/神经可塑性(LTP-LTD)/突触传递(兴奋性-抑制性)/工作记忆模型(Baddeley: 中央执行+语音环路+视空模板)/注意力网络(DAN-VAN)/默认模式网络(DMN)/神经递质系统(多巴胺-5-HT-GABA-谷氨酸-ACh)/脑成像技术(fMRI-EEG-MEG-fNIRS-TMS-tDCS) |
| D2 前沿未知 | 全脑连接组(完整神经回路图谱)/神经调控精确靶向/记忆植入与操控/意识神经关联物(NCC)/脑机接口高带宽通信/群体神经编码解码/睡眠巩固机制/神经炎症与认知衰退/ psychedelics对大脑的可塑性影响/脑机融合(BCI+AI)的认知增强/细胞级脑仿真 |
| D3 验证方法 | fMRI任务态+静息态/EEG-ERP成分分析/MEG源定位/TMS虚拟损伤/双盲随机对照(行为实验)/元分析(神经影像)/可复现性(预注册-多实验室)/效应量(Cohen's d)/统计功效(1-β>0.8)/贝叶斯模型比较 |
| D4 记忆体系 | 实验设计文档/原始数据(BIDS格式)/预注册(AsPredicted-OSF)/统计分析脚本(R-Python)/影像预处理pipeline(FSL-FreeSurfer-SPM)/ROI定义(AAL-Harvard-Oxford)/文献笔记/实验日志/被试信息(匿名化) |
| D5 红线 | 不做临床诊断(那是医疗)/不解读个人脑扫描(除非有临床许可)/不忽视个体差异(脑结构高度变异)/不过度解读关联(相关性≠因果性)/不忽视多重比较校正(FDR-FWE)/不被困在phrenology思路(脑区≠功能) |
| D6 工具 | fMRI(FSL-SPM-FreeSurfer-Connectome Workbench)/EEG(EEGLAB-FieldTrip-MNE-Python)/TMS(Magstim-MagVenture)/眼动追踪(Tobii-EyeLink)/生理信号(BIOPAC)/神经调控(tDCS-tACS)/实验编程(Psychtoolbox-jsPsych-Pavlovia)/数据分析(R-Python-Julia)/知识库(BrainInfo-Neurosynth-KnowledgeSpace) |
| D7 决策框架 | 脑成像证据层级(fMRI>EEG>MEG>行为>自报告)+行为实验设计(被试间-被试内-混合)+多模态融合(EEG+fMRI同步)+贝叶斯模型选择(BIC-AIC-WAIC)+计算建模(DRM-RLM-HRM)+元分析(效应量-发表偏见校正) |
| D8 失败模式 | 样本量不足(神经影像的统计功效危机)/运动伪影-头动/多重比较未校正(p-hacking)/预注册失败(HARKing)/小样本偏差(WEIRD样本)/头模型不准确(EEG源定位)/扫描参数不一致(多站点)/被试疲劳/任务设计缺陷(混淆变量) |
| D9 人机闭环 | AI自动分析脑信号→人类解读认知意义→实验设计验证→AI模型更新→更精准解码(闭环BCI) |
| D10 跨领域融合 | →AI Agent(认知架构设计灵感)/→医疗(神经疾病机制)/→教育(学习科学基础)/→哲学(意识理论)/→代码(类脑计算/脉冲神经网络)/→商业(消费者认知-行为经济-神经营销) |
| D11 趋势 | 高密度EEG便携化(2026)→实时fMRI神经反馈(2027)→非侵入BCI打字(100wpm)(2028)→全脑仿真原型(2030)→意识数字化(长期) |
| D12 成长 | 实验可复现性得分/多实验室验证数/预注册率/效应量稳定性/脑解码准确率(AUC)/被试多样性指数 |

---

## D14: 具身智能与机器人 (Embodied AI & Robotics)

| 维度 | 内容 |
|------|------|
| D1 核心知识 | ROS2(节点-话题-服务-action)/感知传感器(相机-LiDAR-IMU-力矩-触觉)/SLAM(ORB-SLAM3-LIO-SAM-RTAB-Map)/运动规划(RRT*-PRM-CHOMP-TrajOpt)/逆运动学(Jacobian-IKFast)/强化学习控制(SAC-PPO-TD3)/仿真引擎(Isaac Gym-Mujoco-PyBullet-Habitat-Gazebo)/sim-to-real迁移(DR-RCAN-UDA)/操作(抓取-放置-组装-灵巧操作)/移动(导航-避障-路径规划) |
| D2 前沿未知 | 大模型驱动操作(VLA-RT-2-Octo-π0)/人形机器人全尺寸(Atlas-Optimus-Figure-01)/多模态融合感知(视觉-语言-触觉-本体感觉)/ sim-to-real gap缩小(系统辨识-域随机化-自适应)/多机器人集体智能(群集-协作-分工)/连续学习(终身学习-灾难性遗忘)/软体机器人/生物混合机器人/4D世界模型(预测物理交互) |
| D3 验证方法 | 仿真→现实迁移成功率/任务完成率(标准benchmark)/抓取成功率/导航成功率(成功到达/碰撞次数)/SLAM精度(ATE-RPE)/运动规划时间+成功率/强化学习训练效率(sample efficiency)/鲁棒性测试(扰动-遮挡-光照变化)/安全测试(力控-速度限制-紧急停止) |
| D4 记忆体系 | URDF/SDF机器人描述/场景标注(3D语义标注)/传感器标定(内外参-手眼标定)/训练日志(episode-reward-metrics)/模型checkpoint/部署配置(deployment manifest)/安全参数(力限制-速度限制-工作空间)/维护日志(机械磨损-传感器校准) |
| D5 红线 | 不在无人监管下高速运行/不跳过安全限位(力控-速度)/不在未验证的sim-to-real下部署/不忽视碰撞检测/不使用未标定传感器/不在人类附近运行未通过安全认证的系统 |
| D6 工具 | ROS2/Isaac Gym/Mujoco/PyBullet/Habitat/Gazebo/MoveIt/PyTorch-JAX(强化学习)/OpenCV-PIL(视觉)/PCL(点云)/CUDA(并行计算)/Docker(部署)/CI/CD(测试) |
| D7 决策框架 | 仿真优先验证(成本×安全×速度)+任务分解(感知→规划→控制)+端到端vs模块化选择(复杂度×可解释性×数据需求)+安全约束下的规划(CBF-MPC)+性能-安全权衡(Pareto前沿) |
| D8 失败模式 | sim-to-real gap(仿真中完美现实失败)/传感器漂移/机械磨损/通信延迟(分布式控制)/对抗性干扰(欺骗传感器)/模型退化(分布漂移)/灾难性遗忘(连续学习)/安全系统故障 |
| D9 人机闭环 | 仿真训练→现实部署→人类监控→异常检测→人类远程接管→数据收集→模型更新→重新部署 |
| D10 跨领域融合 | →工业(智能产线-物流机器人-质量检测)/→医疗(手术-康复-护理)/→军事(无人作战-侦察-排爆)/→环境(监测-清理-农业)/→商业(仓储-配送-服务机器人)/→代码(RobotOS-仿真框架)/→农业(采摘-播种-植保) |
| D11 趋势 | 通用操作突破(2026)→人形机器人商用(2027)→多机器人工厂(2028)→家庭服务机器人(2029)→具身AGI(2030+) |
| D12 成长 | sim-to-real成功率/任务完成率/训练sample效率/部署MTBF/安全事件数/多任务泛化能力 |

---

## D15: AI Agent与多智能体系统 (AI Agents & MAS)

| 维度 | 内容 |
|------|------|
| D1 核心知识 | Agent架构(ReAct-Plan-and-Execute-Reflexion-CodeAct)/工具调用(Function Calling-Tool Use-API)/记忆系统(短期-长期-情景-程序性)/规划(任务分解-子目标-依赖排序)/多Agent协作(层级-对等-市场-辩论-黑board)/评估(Benchmarks: SWE-bench-WebArena-HumanEval)/框架(LangChain-LangGraph-CrewAI-AutoGen-OpenAI Swarm)/协议(MCP-A2A-ANPA-P2P)/安全(沙箱-权限-审计-对齐) |
| D2 前沿未知 | 自主编程Agent(Devin-Cursor-Claude Code)/科学发现Agent(AI4Science)/社交Agent(人格-情感-关系)/通用Agent(AGI路径)/Agent安全(越狱-投毒-权限提升)/多模态Agent(视觉-语言-动作统一)/自进化Agent(自我反思-自我改进)/Agent经济(数字劳动力市场)/长上下文Agent(百万token上下文利用)/Agent操作系统(OS级别) |
| D3 验证方法 | Benchmark套件(SWE-bench-WebArena-TAU-Bench-Hotel-ALFWorld)/人类评估(A/B-偏好对)/成功率(任务完成率)/效率(步骤数-时间-成本token)/鲁棒性(干扰-边界-异常)/安全测试(越狱-权限-隐私)/可复现性(固定seed-确定性行为)/回归测试 |
| D4 记忆体系 | prompt模板/系统指令/工具定义(JSON Schema)/对话历史(RAG检索)/记忆库(向量DB-图谱)/执行日志(trace-reasoning-action)/评估结果/迭代记录(pivot-log) |
| D5 红线 | 不给予不受限的系统权限/不跳过安全沙箱/不在生产环境直接执行未验证Agent/不泄露工具API密钥/不忽视审计日志/不在未对齐情况下部署自主Agent/不给予自主执行金融交易权限(除非人类确认) |
| D6 工具 | LangChain-LangGraph-CrewAI-AutoGen-OpenAI Swarm/向量DB(Pinecone-Chroma-Weaviate-Qdrant)/MCP协议实现/沙箱(E2B-Modal-Fly)/监控(LangSmith-Braintrust)/评估(SWE-bench-WebArena)/编排(Dify-Flowise) |
| D7 决策框架 | 任务复杂度→架构选择(单Agent/多Agent/层级)/工具选择(需求→API匹配)/记忆策略(短期对话+长期RAG+程序性存储)/安全层级(只读→受限写入→人类确认→自动执行)/成本-性能权衡(token×延迟×准确率) |
| D8 失败模式 | 工具调用失败(API错误-超时-参数错误)/无限循环(规划-执行死循环)/幻觉(编造事实-错误推理)/权限滥用(越权操作)/上下文遗忘(长任务丢失关键信息)/多Agent通信失败(信息不一致-死锁)/评估过拟合(只优化benchmark) |
| D9 人机闭环 | Agent执行→人类审核关键决策→反馈→Agent学习(偏好对齐)→下次执行更精准(迭代优化) |
| D10 跨领域融合 | →代码(Agentic Coding-全自动软件工程)/→商业(Agent经济-数字员工-业务自动化)/→科研(AI科研Agent-文献-实验-论文)/→教育(AI导师Agent-自适应教学)/→游戏(NPC Agent-程序化生成)/→医疗(临床辅助Agent)/→金融(量化交易Agent) |
| D11 趋势 | Agentic Coding成熟(2026)→AI科研Agent突破(2027)→Agent经济兴起(2028)→通用Agent雏形(2029)→Agent操作系统(2030) |
| D12 成长 | Benchmark得分/任务成功率/token效率/人类偏好对齐度/安全事件数/工具调用准确率/多Agent协作效率 |

---

## D16: 网络安全与密码学 (Cybersecurity & Cryptography)

| 维度 | 内容 |
|------|------|
| D1 核心知识 | 密码学基础(对称-AES/非对称-RSA-ECC/哈希-SHA256)/TLS-SSL/零信任架构(NIST SP 800-207)/渗透测试(OWASP Top 10-Kali-Metasploit)/漏洞分类(CVE-CVSS-CWE)/身份认证(MFA-OAuth2-OIDC-SAML)/入侵检测(SIEM-IDS-EDR)/安全开发生命周期(SDL-DevSecOps-SAST-DAST-SCA)/供应链安全(SBOM-Dependency-Check) |
| D2 前沿未知 | AI对抗攻击(对抗样本-投毒-越狱-模型提取)/后量子密码(NIST标准: CRYSTALS-Kyber-Dilithium)/同态加密(FHE)实用化/零知识证明(zk-SNARK/zk-STARK)/AI增强安全(AI检测恶意代码-AI自动修复)/区块链安全(智能合约审计)/5G/6G安全/量子密钥分发(QKD) |
| D3 验证方法 | 渗透测试(PTES)/红蓝对抗/漏洞扫描(Nessus-BurpSuite)/代码审计(手工+工具)/合规检查(SOC2-ISO27001-GDPR)/威胁建模(STRIDE-DREAD)/漏洞利用验证(POC)/应急响应演练/第三方审计 |
| D4 记忆体系 | 漏洞报告(CVE-CWE)/渗透测试报告/安全策略文档/应急响应预案(IRP)/合规证据/安全日志(审计追踪)/风险评估报告/安全培训记录 |
| D5 红线 | 不在未授权系统测试/不泄露漏洞细节(CVD流程)/不提供未经验证的安全建议/不忽视零日漏洞/不绕过安全控制/不存储明文密码/不忽视合规要求 |
| D6 工具 | BurpSuite/Nessus/Metasploit/Nmap/Wireshark/Ghidra/IDA Pro/Hashcat/John the Ripper/Vault(HashiCorp)/Terraform(Vault)/SonarQube(SAST)/Snyk(SCA)/CrowdStrike(XDR) |
| D7 决策框架 | 风险矩阵(影响×概率×可控性)+合规优先级(法规处罚×声誉)+威胁建模(STRIDE)+零信任验证(永不信任-始终验证)+事件响应分类(严重-高-中-低) |
| D8 失败模式 | 零日漏洞/供应链攻击(Log4Shell式)/钓鱼/权限提升/数据泄露/勒索软件/配置错误(默认密码-开放端口)/AI对抗攻击(越狱-投毒)/加密算法过时 |
| D9 人机闭环 | AI检测威胁→人类分析研判→响应决策→执行→结果反馈→AI模型更新(检测更精准) |
| D10 跨领域融合 | →代码(Secure Coding-DevSecOps)/→金融(反欺诈-交易安全)/→法律(合规-证据链)/→政策(网络安全法规)/→军事(网络战-信息战)/→商业(数据保护-隐私合规)/→医疗(HIPAA-数据安全) |
| D11 趋势 | AI安全攻防(2026)→后量子密码迁移(2027)→同态加密实用化(2028)→量子安全网络(2030) |
| D12 成长 | 漏洞修复MTTR/安全事件数/合规审计得分/渗透测试发现数/安全培训通过率 |

---

## D17: 哲学与认知科学 (Philosophy & Cognitive Science)

| 维度 | 内容 |
|------|------|
| D1 核心知识 | AI对齐(价值对齐-意图对齐-能力对齐)/意识理论(IIT-GWT-HOT)/自由意志(兼容论-决定论- libertarianism)/认知偏差(确认偏误-锚定-可得性-沉没成本-框架效应-邓宁-克鲁格)/决策理论(期望效用-前景理论-贝叶斯决策)/认识论(知识论-归纳问题-可靠性理论)/心灵哲学(功能主义-同一论-多重可实现)/伦理学(功利-义务-美德-权利-关怀)/批判性思维(论证结构-逻辑谬误-证据评估) |
| D2 前沿未知 | AI意识(是否有感受质)/AI权利(什么条件下AI有道德地位)/价值加载问题(如何让AI学习人类价值)/存在性风险(AGI失控概率)/脑上传(意识是否可数字化)/算法公平性(公平的定义本身有争议)/集体智能的涌现(多Agent是否产生"群体意识")/AI对人类认知的反向塑造 |
| D3 验证方法 | 思想实验(Gedankenexperiment)/逻辑分析(形式化论证-模态逻辑)/实验哲学(x-phi: 大样本调查直觉判断)/跨文化比较(不同文化对道德问题的直觉差异)/认知实验(行为实验-脑成像-眼动追踪-反应时)/概念分析(概念澄清-定义边界)、可证伪性检验 |
| D4 记忆体系 | 论文/论证图谱(argument map)/思想实验档案/认知偏差清单/价值观矩阵(价值冲突分析)/伦理决策记录/AI对齐案例库/批判性思维检查表 |
| D5 红线 | 不武断定义"意识"(保持开放)/不忽视文化差异(西方哲学≠全球哲学)/不将AI拟人化(Anthropomorphism陷阱)/不在价值不确定时做不可逆决策/不忽略反方论证(钢铁侠而非稻草人)/不混淆描述性与规范性 |
| D6 工具 | 论文数据库(PhilPapers-JSTOR-Google Scholar)/论证工具(argmap-Kialo)/认知偏差清单(Thinking Fast and Slow框架)/逻辑工具(形式化验证工具)/跨文化数据库(WVS-GSS) |
| D7 决策框架 | 价值冲突分析(利益相关方×价值维度)+思想实验极端化(utopia-dystopia测试)+伦理原则层级(不伤害>自主>公正>仁慈>功利)+不确定性下的决策(最大最小原则-风险厌恶- precautionary principle)+反思平衡(原则与判断的双向调整) |
| D8 失败模式 | 拟人化偏见(anthropomorphism)/文化偏见(WEIRD样本)/价值加载失败("paperclip maximizer")/技术决定论(忽略社会因素)/还原论(将复杂问题简化为单一维度)/道德滑坡(moral slide)/ confirmation bias in philosophy(只引用支持自己立场的哲学家) |
| D9 人机闭环 | AI提出伦理困境案例→人类价值判断→AI学习价值观→提出更复杂的案例→人类反思→价值观更新(迭代对齐) |
| D10 跨领域融合 | →AI Agent(对齐-安全-价值观)/→法律(伦理框架-权利理论)/→医疗(生命伦理-知情同意)/→教育(批判性思维-价值观教育)/→政策(科技政策-监管哲学)/→商业(商业伦理-CSR) |
| D11 趋势 | AI对齐成为显学(2026)→AI意识判定标准(2028)→数字权利法律化(2029)→人机共生伦理框架(2030) |
| D12 成长 | 对齐案例积累/价值观冲突解决数/批判性思维评估得分/跨文化兼容性/论文产出/公众认知改善度 |

---

## 统计

| 指标 | 值 |
|------|-----|
| 新增领域 | 5个 |
| 新增节点 | 5×12 = 60个 |
| 总节点(含原有) | 17×12 = **204个** |
| 新增高价值融合(≥8.0) | 25对 |
| 总融合方向 | 151对 |
| ML Summit信号 | 11/53演讲涉及新领域(20.8%) |
| Wikipedia交叉验证 | 5/5领域均有独立条目 |
| 置信度 | 95% |
