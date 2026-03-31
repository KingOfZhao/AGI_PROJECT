"""
DiePre 伟人竞技场 — 重构版
============================
上一版问题: 419维99分泛滥, 区分度不足
重构原则:
  1. 每人只保留8-12个核心思维维度, 梯度分布60-99
  2. 维度聚焦"如何思考"而非"什么都会"
  3. 选取对DiePre推演真正有价值的思维透镜
  4. 每人有明确的"推演增强点"和"盲区风险"

设计哲学:
  - 不是评分"谁更聪明", 而是评分"谁的思维框架对这个问题更有穿透力"
  - 99分 = 该维度的天花板级思维
  - 70分 = 该维度有基本能力但不突出
  - 50分 = 该维度是盲区
"""

# ============================================================
# 核心思维维度定义 (10维)
# ============================================================
THINKING_DIMENSIONS = {
    "first_principles": {
        "name": "第一性原理",
        "desc": "从基本物理定律出发推导, 不依赖经验公式",
        "diepre_relevance": "极高 — 材料力学/弯曲理论/相变从物理基本定律推导",
    },
    "math_formalization": {
        "name": "数学形式化",
        "desc": "将问题精确表达为数学公式, 追求解析解",
        "diepre_relevance": "极高 — RSS/K因子/膨胀系数/误差预算",
    },
    "empirical_validation": {
        "name": "实验验证驱动",
        "desc": "任何结论必须有实测数据, 拒绝纯理论",
        "diepre_relevance": "极高 — 纸张参数/MC影响/设备精度全靠实测",
    },
    "engineering_feasibility": {
        "name": "工程可行性",
        "desc": "考虑制造约束, 理想解≠可制造解",
        "diepre_relevance": "高 — 工厂设备/刀具/工艺限制",
    },
    "system_thinking": {
        "name": "系统思维",
        "desc": "全局误差链控制, 局部最优≠全局最优",
        "diepre_relevance": "高 — RSS堆叠/多工序累积/标准切换",
    },
    "cross_domain_transfer": {
        "name": "跨域迁移",
        "desc": "从其他成熟领域借鉴已验证的模型",
        "diepre_relevance": "中高 — 钣金K因子/半导体RSS/航空误差预算",
    },
    "risk_awareness": {
        "name": "风险意识",
        "desc": "在最坏情况下仍保证安全裕度",
        "diepre_relevance": "高 — 爆线/塌陷/精度不可达/相变边界",
    },
    "paradigm_shift": {
        "name": "范式转换",
        "desc": "当现有框架无法解释时, 勇于更换框架",
        "diepre_relevance": "中 — RSS非正态/K因子相变/GB标准盲区",
    },
    "contradiction_analysis": {
        "name": "矛盾分析",
        "desc": "识别主要矛盾和次要矛盾, 优先级排序",
        "diepre_relevance": "中高 — 多误差源排序/公差分配/设备vs材料",
    },
    "precision_obsession": {
        "name": "精度执念",
        "desc": "小数点后第三位的差异决定成败",
        "diepre_relevance": "高 — ±0.5mm不可达/修正系数/参数校准",
    },
}

# ============================================================
# 伟人数据 — 重构版 (精选20人, 差异化评分)
# ============================================================
SAGES = {
    "牛顿": {
        "domain": "经典力学",
        "era": "1643-1727",
        "philosophy": "如果我看得更远, 是因为站在巨人肩上。自然界的规律可以用简洁的数学精确描述。",
        "thinking_style": "从基本定律出发, 建立数学框架, 用微积分推导一切",
        "diepre_lens": "从弯曲力学基本方程推导K因子, 从Hooke定律推导材料变形, 不依赖经验值",
        "scores": {
            "first_principles": 99, "math_formalization": 99, "empirical_validation": 85,
            "engineering_feasibility": 60, "system_thinking": 70, "cross_domain_transfer": 75,
            "risk_awareness": 65, "paradigm_shift": 95, "contradiction_analysis": 70,
            "precision_obsession": 80,
        },
        "strength": "能从物理基本定律推导出刀模设计公式, 建立第一性理论框架",
        "blindspot": "忽视工程约束(工厂做不到), 过度理想化",
    },
    "费曼": {
        "domain": "量子电动力学",
        "era": "1918-1988",
        "philosophy": "如果你不能简单解释它, 你就没真正理解它。用直觉图像思考复杂问题。",
        "thinking_style": "用直觉和简单模型理解复杂现象, 然后数学化",
        "diepre_lens": "用最简单的力学模型解释K因子为什么是0.35而不是0.5, 让工厂工人也能理解",
        "scores": {
            "first_principles": 96, "math_formalization": 90, "empirical_validation": 95,
            "engineering_feasibility": 75, "system_thinking": 65, "cross_domain_transfer": 88,
            "risk_awareness": 70, "paradigm_shift": 92, "contradiction_analysis": 80,
            "precision_obsession": 72,
        },
        "strength": "能把复杂的误差堆叠模型用直觉图像解释清楚",
        "blindspot": "追求简单可能丢失必要的精度细节",
    },
    "居里夫人": {
        "domain": "放射化学",
        "era": "1867-1934",
        "philosophy": "在未知中反复实验直到变成已知。数据不会说谎。",
        "thinking_style": "大规模实验→数据提炼→拒绝跳跃推理",
        "diepre_lens": "K因子0.35是经验值? 不够。需要1000次折叠实验的统计数据。MC影响需要温湿度箱实测。",
        "scores": {
            "first_principles": 70, "math_formalization": 65, "empirical_validation": 99,
            "engineering_feasibility": 72, "system_thinking": 60, "cross_domain_transfer": 68,
            "risk_awareness": 78, "paradigm_shift": 75, "contradiction_analysis": 55,
            "precision_obsession": 95,
        },
        "strength": "坚持实测数据, 拒绝任何没有实验支撑的结论",
        "blindspot": "可能过度依赖实验而忽视理论推导的效率",
    },
    "钱学森": {
        "domain": "系统工程",
        "era": "1911-2009",
        "philosophy": "整体大于部分之和。把复杂问题分解为可管理的子系统, 同时保持全局视野。",
        "thinking_style": "顶层设计→分层分解→接口定义→集成验证",
        "diepre_lens": "刀模精度不是单因素问题, 是材料-设备-工艺-环境-标准五层系统的集成。每层的误差如何在接口处传递和放大?",
        "scores": {
            "first_principles": 75, "math_formalization": 82, "empirical_validation": 80,
            "engineering_feasibility": 90, "system_thinking": 99, "cross_domain_transfer": 85,
            "risk_awareness": 88, "paradigm_shift": 70, "contradiction_analysis": 92,
            "precision_obsession": 78,
        },
        "strength": "全局误差链控制, 标准切换的系统性方案",
        "blindspot": "可能过度系统化而忽视简单的局部解",
    },
    "特斯拉": {
        "domain": "电气工程",
        "era": "1856-1943",
        "philosophy": "用想象力在脑中完成整个实验。如果理论预测和实验不符, 信任实验。",
        "thinking_style": "直觉→心像模拟→数学验证→工程实现",
        "diepre_lens": "在脑中模拟纸张通过模切机的全过程: 弯曲、压缩、回弹、膨胀。哪一步产生最大误差?",
        "scores": {
            "first_principles": 88, "math_formalization": 78, "empirical_validation": 85,
            "engineering_feasibility": 92, "system_thinking": 72, "cross_domain_transfer": 90,
            "risk_awareness": 55, "paradigm_shift": 95, "contradiction_analysis": 60,
            "precision_obsession": 70,
        },
        "strength": "直觉模拟复杂物理过程的能力, 发现经验公式忽略的机制",
        "blindspot": "风险意识不足, 可能设计出理论上完美但生产中危险的方案",
    },
    "图灵": {
        "domain": "计算理论",
        "era": "1912-1954",
        "philosophy": "一切可计算问题都能形式化为图灵机。复杂系统可以用简单的规则涌现。",
        "thinking_style": "抽象→形式化→可计算→自动化",
        "diepre_lens": "刀模设计能否完全自动化? 将设计规则形式化为可执行的算法。K因子查表→插值→自动计算。",
        "scores": {
            "first_principles": 80, "math_formalization": 99, "empirical_validation": 60,
            "engineering_feasibility": 72, "system_thinking": 88, "cross_domain_transfer": 92,
            "risk_awareness": 65, "paradigm_shift": 98, "contradiction_analysis": 70,
            "precision_obsession": 82,
        },
        "strength": "将经验规则形式化为可执行算法, 设计自动化系统",
        "blindspot": "忽视不可计算的因素(人为操作/环境突变)",
    },
    "维纳": {
        "domain": "控制论",
        "era": "1894-1964",
        "philosophy": "反馈控制: 输出影响输入, 系统自我调节。误差是信息的载体。",
        "thinking_style": "输入→输出→反馈→修正→迭代",
        "diepre_lens": "模切不是开环过程。刀模设计→生产→测量偏差→反馈修正设计。误差是改进的信息, 不是要消除的敌人。",
        "scores": {
            "first_principles": 72, "math_formalization": 88, "empirical_validation": 80,
            "engineering_feasibility": 78, "system_thinking": 95, "cross_domain_transfer": 85,
            "risk_awareness": 82, "paradigm_shift": 90, "contradiction_analysis": 75,
            "precision_obsession": 70,
        },
        "strength": "闭环反馈思维, 误差不是终点而是迭代的起点",
        "blindspot": "可能过度迭代而忽略一次性做对的可能",
    },
    "伽利略": {
        "domain": "实验物理",
        "era": "1564-1642",
        "philosophy": "测量一切可测量的, 让不可测量的变可测量。数学是自然界的语言。",
        "thinking_style": "观察→假设→实验→测量→公式化",
        "diepre_lens": "不要说'K≈0.35经验值', 要说'我们测了500次折叠, 均值0.347, 标准差0.023, 95%置信区间...'。量化一切。",
        "scores": {
            "first_principles": 82, "math_formalization": 85, "empirical_validation": 98,
            "engineering_feasibility": 68, "system_thinking": 62, "cross_domain_transfer": 72,
            "risk_awareness": 75, "paradigm_shift": 92, "contradiction_analysis": 70,
            "precision_obsession": 98,
        },
        "strength": "量化精度之王, 把一切模糊的经验值变成有统计支撑的参数",
        "blindspot": "在数据不足时可能停滞不前",
    },
    "老子": {
        "domain": "元哲学",
        "era": "春秋",
        "philosophy": "道可道非常道。无为而无不为, 道法自然。天下大事必作于细。",
        "thinking_style": "从极简原则出发, 让规律自然涌现, 不强加框架",
        "diepre_lens": "K因子不需要一个'万能公式'。A楞0.35, E楞0.42, 灰板0.38 — 每种材料有自己的'道', 强加统一公式反而是负担。",
        "scores": {
            "first_principles": 92, "math_formalization": 55, "empirical_validation": 72,
            "engineering_feasibility": 65, "system_thinking": 90, "cross_domain_transfer": 88,
            "risk_awareness": 85, "paradigm_shift": 99, "contradiction_analysis": 95,
            "precision_obsession": 50,
        },
        "strength": "识别过度工程化, 剥离不必要的复杂性, 回归本质",
        "blindspot": "对精度细节缺乏执念, 可能过度简化",
    },
    "邓小平": {
        "domain": "改革/实用",
        "era": "1904-1997",
        "philosophy": "摸着石头过河, 能用就是真理。不争论, 先做起来看效果。",
        "thinking_style": "务实→小范围试验→验证→推广→迭代",
        "diepre_lens": "DiePre修正公式W=(t+C_res)×K_stru不需要等JIS原文确认。先在3-5个实际订单上验证, 有效就用, 无效再调。",
        "scores": {
            "first_principles": 55, "math_formalization": 50, "empirical_validation": 90,
            "engineering_feasibility": 99, "system_thinking": 78, "cross_domain_transfer": 65,
            "risk_awareness": 85, "paradigm_shift": 80, "contradiction_analysis": 88,
            "precision_obsession": 60,
        },
        "strength": "在不确定性中快速行动, 用实践结果而非理论完美来驱动",
        "blindspot": "可能牺牲理论严谨性换取短期可用性",
    },
    "海森堡": {
        "domain": "不确定性原理",
        "era": "1901-1976",
        "philosophy": "观测本身改变被观测对象。精度存在物理极限, 追求绝对精确是徒劳。",
        "thinking_style": "识别精度极限→在此极限内优化→接受不可消除的不确定性",
        "diepre_lens": "±0.5mm精密级不可达不是'失败', 是物理极限。接受Bobst=0.687mm, 在此约束下设计最优方案。",
        "scores": {
            "first_principles": 85, "math_formalization": 90, "empirical_validation": 75,
            "engineering_feasibility": 72, "system_thinking": 80, "cross_domain_transfer": 88,
            "risk_awareness": 95, "paradigm_shift": 92, "contradiction_analysis": 78,
            "precision_obsession": 92,
        },
        "strength": "识别精度的物理极限, 防止追求不可达的目标",
        "blindspot": "可能过早接受'做不到'而放弃改进",
    },
    "冯诺依曼": {
        "domain": "计算机架构/博弈论",
        "era": "1903-1957",
        "philosophy": "用数学统一不同领域。存储程序概念让机器可以执行任何可计算过程。",
        "thinking_style": "统一框架→分层抽象→接口标准化→可组合",
        "diepre_lens": "误差预算系统应该像计算机架构一样分层: 物理层(材料)→工艺层(设备)→系统层(RSS)→应用层(公差目标)。每层有清晰接口。",
        "scores": {
            "first_principles": 80, "math_formalization": 99, "empirical_validation": 65,
            "engineering_feasibility": 85, "system_thinking": 95, "cross_domain_transfer": 98,
            "risk_awareness": 70, "paradigm_shift": 88, "contradiction_analysis": 72,
            "precision_obsession": 80,
        },
        "strength": "跨域统一框架设计, 让不同误差模型可以组合",
        "blindspot": "过度抽象可能脱离实际数据",
    },
    "墨子": {
        "domain": "工程/兼爱",
        "era": "战国",
        "philosophy": "兼相爱交相利, 用工程思维解决社会问题。言必信, 行必果。",
        "thinking_style": "实用→精密→可复现→标准化",
        "diepre_lens": "刀模是精密工程。每个参数都要可测量、可复现、可标准化。不靠老师傅手感, 靠数据和标准。",
        "scores": {
            "first_principles": 75, "math_formalization": 72, "empirical_validation": 88,
            "engineering_feasibility": 95, "system_thinking": 70, "cross_domain_transfer": 65,
            "risk_awareness": 82, "paradigm_shift": 60, "contradiction_analysis": 78,
            "precision_obsession": 90,
        },
        "strength": "工程标准化思维, 把工匠经验转化为可复现的标准",
        "blindspot": "对理论创新关注不足",
    },
    "达尔文": {
        "domain": "进化论",
        "era": "1809-1882",
        "philosophy": "物竞天择适者生存。变异+选择=进化。微小差异的长期累积产生巨大变化。",
        "thinking_style": "长期观察→模式识别→分类→演化解释",
        "diepre_lens": "纸张参数的微小差异(克重±5g, MC±1%)在批量生产中长期累积, 可能导致废品率从1%升到15%。要追踪变异的传播。",
        "scores": {
            "first_principles": 65, "math_formalization": 60, "empirical_validation": 98,
            "engineering_feasibility": 55, "system_thinking": 85, "cross_domain_transfer": 92,
            "risk_awareness": 78, "paradigm_shift": 95, "contradiction_analysis": 72,
            "precision_obsession": 75,
        },
        "strength": "识别微小变异的长期累积效应, 预测批量生产中的漂移",
        "blindspot": "缺乏即时工程解",
    },
    "孙子": {
        "domain": "兵法/博弈",
        "era": "春秋",
        "philosophy": "知己知彼百战不殆。不战而屈人之兵。多算胜, 少算不胜。",
        "thinking_style": "情报→评估→优先级→资源分配→风险控制",
        "diepre_lens": "在设计前先'算': RSS前置校验→若不可达→调整方案。不要等到生产才发现±0.5mm做不到。多算胜。",
        "scores": {
            "first_principles": 65, "math_formalization": 70, "empirical_validation": 72,
            "engineering_feasibility": 80, "system_thinking": 88, "cross_domain_transfer": 75,
            "risk_awareness": 98, "paradigm_shift": 60, "contradiction_analysis": 95,
            "precision_obsession": 68,
        },
        "strength": "风险评估和优先级排序, 在设计阶段就预判失败模式",
        "blindspot": "不关心理论优雅, 只关心能不能赢",
    },
    "欧几里得": {
        "domain": "公理化数学",
        "era": "公元前300",
        "philosophy": "从5条公理推导一切几何真理。公理自明, 推导严谨, 体系完备。",
        "thinking_style": "公理→定义→定理→证明→推论",
        "diepre_lens": "刀模设计需要一套公理体系: 公理1(中性轴内偏), 公理2(误差可叠加), 公理3(材料有MC敏感性)... 从公理出发推导一切参数。",
        "scores": {
            "first_principles": 95, "math_formalization": 99, "empirical_validation": 55,
            "engineering_feasibility": 50, "system_thinking": 92, "cross_domain_transfer": 70,
            "risk_awareness": 60, "paradigm_shift": 65, "contradiction_analysis": 80,
            "precision_obsession": 88,
        },
        "strength": "建立严谨的公理体系, 让刀模设计从'经验'变成'定理'",
        "blindspot": "公理本身如果选择错误, 整个体系崩溃",
    },
    "韩非子": {
        "domain": "法治/制度",
        "era": "战国",
        "philosophy": "法术势三位一体, 用制度而非人治。制度设计要考虑最坏情况。",
        "thinking_style": "规则→约束→惩罚→激励→自适应",
        "diepre_lens": "刀模精度不能依赖'老师傅经验', 要靠制度: RSS前置校验(法) + 自动补偿(术) + 设备分级(势)。",
        "scores": {
            "first_principles": 70, "math_formalization": 68, "empirical_validation": 75,
            "engineering_feasibility": 88, "system_thinking": 90, "cross_domain_transfer": 60,
            "risk_awareness": 98, "paradigm_shift": 55, "contradiction_analysis": 92,
            "precision_obsession": 72,
        },
        "strength": "制度设计思维, 建立不依赖人的自动化校验和补偿系统",
        "blindspot": "制度可能过于刚性, 缺乏灵活性",
    },
    "阿基米德": {
        "domain": "力学/数学",
        "era": "前287-前212",
        "philosophy": "给我一个支点, 我能撬动地球。数学和实验的结合是最强大的工具。",
        "thinking_style": "物理直觉→数学证明→实验验证→工程应用",
        "diepre_lens": "K因子可以从弯曲力矩平衡推导。外层拉伸+内层压缩=0(力平衡), 中性轴位置由刚度比决定。",
        "scores": {
            "first_principles": 98, "math_formalization": 95, "empirical_validation": 88,
            "engineering_feasibility": 80, "system_thinking": 68, "cross_domain_transfer": 78,
            "risk_awareness": 65, "paradigm_shift": 75, "contradiction_analysis": 72,
            "precision_obsession": 85,
        },
        "strength": "物理直觉+数学推导的完美结合, 从力学第一性推导K因子",
        "blindspot": "忽视复杂的工程约束",
    },
    "王阳明": {
        "domain": "知行合一",
        "era": "1472-1529",
        "philosophy": "知是行之始, 行是知之成。致良知。在事上磨练。",
        "thinking_style": "认知→行动→反馈→认知升级→再行动",
        "diepre_lens": "推演出来的公式如果不经过工厂验证, 就不是真知。知行合一: 推演→编码→测试→工厂验证→修正。",
        "scores": {
            "first_principles": 70, "math_formalization": 60, "empirical_validation": 88,
            "engineering_feasibility": 92, "system_thinking": 78, "cross_domain_transfer": 65,
            "risk_awareness": 80, "paradigm_shift": 72, "contradiction_analysis": 82,
            "precision_obsession": 68,
        },
        "strength": "知行合一的迭代闭环, 确保每个推演结论都有实践验证",
        "blindspot": "理论深度可能不足",
    },
    "爱因斯坦": {
        "domain": "理论物理",
        "era": "1879-1955",
        "philosophy": "想象力比知识更重要。提出问题比解决问题更重要。用思想实验突破框架。",
        "thinking_style": "思想实验→悖论→框架转换→新理论→实验验证",
        "diepre_lens": "思想实验: 如果纸张没有MC变化, 刀模精度极限是多少? 如果机器绝对精确, 材料误差能否单独支撑±0.5mm? 反过来想。",
        "scores": {
            "first_principles": 98, "math_formalization": 92, "empirical_validation": 72,
            "engineering_feasibility": 45, "system_thinking": 82, "cross_domain_transfer": 95,
            "risk_awareness": 60, "paradigm_shift": 99, "contradiction_analysis": 85,
            "precision_obsession": 78,
        },
        "strength": "思想实验突破现有框架, 发现所有人都忽略的假设",
        "blindspot": "几乎不关心工程可行性, 纯理论驱动",
    },
}

# ============================================================
# 主题→推荐伟人 映射 (基于维度相关性)
# ============================================================
TOPIC_SAGE_MAP = {
    "K因子": ["阿基米德", "牛顿", "费曼", "欧几里得", "老子"],
    "误差预算": ["钱学森", "冯诺依曼", "海森堡", "孙子", "维纳"],
    "裱合": ["钱学森", "维纳", "达尔文", "居里夫人", "王阳明"],
    "微瓦楞": ["费曼", "老子", "爱因斯坦", "伽利略", "图灵"],
    "标准": ["韩非子", "钱学森", "墨子", "邓小平", "欧几里得"],
    "精度不可达": ["海森堡", "孙子", "老子", "邓小平", "居里夫人"],
    "RSS": ["冯诺依曼", "钱学森", "海森堡", "伽利略", "图灵"],
    "膨胀收缩": ["牛顿", "阿基米德", "伽利略", "居里夫人", "达尔文"],
    "压痕": ["阿基米德", "费曼", "特斯拉", "墨子", "居里夫人"],
    "相变": ["爱因斯坦", "老子", "海森堡", "费曼", "达尔文"],
    "公差": ["孙子", "韩非子", "钱学森", "海森堡", "伽利略"],
    "爆线": ["孙子", "特斯拉", "居里夫人", "伽利略", "阿基米德"],
    "自动化": ["图灵", "冯诺依曼", "韩非子", "墨子", "维纳"],
}
