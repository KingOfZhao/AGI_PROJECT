#!/usr/bin/env python3
"""
菩提道次第 × 代码领域能力具现化

应无所住，而生其心。

将佛学果位体系映射为代码领域的能力阶梯：
- 声闻四果（自利解脱）→ 个人编程能力四阶
- 缘觉（无师独悟）→ 独立发现代码模式规律
- 菩萨十地（悲智双运）→ 度他：教学→架构→生态
- 佛果（究竟圆满）→ 一切种智：代码领域无碍

每个节点都是具体可实践、可验证的真实能力。
终极目标：探索无穷层级的无穷。
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)


import sys, sqlite3, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import agi_v13_cognitive_lattice as agi

DB_PATH = ROOT / "memory.db"
VERIFIED_SOURCE = "bodhi_path_injection"

# ============================================================
# 声闻四果 — 个人编程能力（自利解脱）
# ============================================================
# 初果须陀洹：入流，不堕恶道 → 入门，不犯致命错误
# 二果斯陀含：薄烦恼 → 代码坏味道变薄
# 三果阿那含：断欲界贪瞋 → 断低级Bug，不还初级错误
# 四果阿罗汉：漏尽通 → 个人技术精通，自了生死

SRAVAKA_NODES = [
    # ---- 初果·须陀洹（预流）：见道，断三结 ----
    {
        "content": "【初果·预流】代码见道位：理解变量/控制流/函数三结构，断三结——(1)断'我见'：代码不是自我表达而是解决问题的工具，(2)断'戒禁取'：不迷信银弹框架而理解其本质，(3)断'疑'：通过运行代码消除对语法规则的疑惑。验证：能独立写出100行可运行程序。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },
    {
        "content": "【初果·四不坏信】编程四不坏信：(1)信编译器/解释器（佛）——它永远正确，错误在你，(2)信语言规范（法）——文档是真理源头，(3)信开源社区（僧）——前人验证过的代码可信，(4)信测试（戒）——通过测试的代码不堕'恶道'(生产事故)。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },

    # ---- 二果·斯陀含（一来）：薄贪瞋痴 ----
    {
        "content": "【二果·一来】代码烦恼变薄：(1)贪薄——不再堆砌不必要的功能(YAGNI)，(2)瞋薄——不再因bug暴怒而是冷静debug，(3)痴薄——理解'代码即文档'而非写注释替代清晰命名。代码坏味道(code smell)开始自然察觉。验证：能重构自己三个月前的代码并感到羞耻。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },

    # ---- 三果·阿那含（不还）：断五下分结 ----
    {
        "content": "【三果·不还】断代码五下分结：(1)断'欲界贪'——不再追求代码的表面优雅而忽视性能，(2)断'瞋'——面对遗留代码不愤怒而是渐进重构，(3)断'身见'——理解代码所有权是团队的不是个人的，(4)断'戒禁取'——不盲从设计模式而根据场景选择，(5)断'疑'——对算法复杂度O(n)有直觉判断。验证：能主导千行级模块的设计与实现。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },

    # ---- 四果·阿罗汉：漏尽，自了生死 ----
    {
        "content": "【四果·阿罗汉】代码漏尽通：断五上分结——(1)断色贪（不执着于特定语言/框架），(2)断无色贪（不执着于抽象完美架构），(3)断我慢（承认不懂并快速学习），(4)断掉悔（不后悔技术选型而是迭代），(5)断无明（理解计算本质：一切程序皆状态转移）。能力：独立解决任何单领域技术问题。局限：自了生死——擅长个人项目但不擅长带团队。验证：能在48小时内用陌生语言完成完整项目。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },
    {
        "content": "【阿罗汉·六神通在代码领域的具现】(1)天眼通——读代码如读故事，一眼看穿数据流向，(2)天耳通——从错误日志中听到系统的'声音'，(3)神足通——快速在不同代码库间切换上下文，(4)他心通——理解原作者的设计意图，(5)宿命通——理解代码的演化历史(git blame)，(6)漏尽通——写出无内存泄漏、无安全漏洞的代码。",
        "domain": "菩提道·声闻",
        "status": "proven",
    },
]

# ============================================================
# 缘觉 — 无师独悟代码模式
# ============================================================

PRATYEKABUDDHA_NODES = [
    {
        "content": "【缘觉·辟支佛】代码领域的无师独悟：不需要文档和教程，通过观察代码的'十二因缘'(因果链)自行领悟——看到函数调用栈(因)→理解副作用传播(缘)→悟出架构模式(果)。如同见花落叶即悟无常。能力高于阿罗汉（能发现新的设计模式），但不说法（写不出清晰文档、无法教导他人）。验证：能通过阅读源码逆向理解未文档化的复杂系统。",
        "domain": "菩提道·缘觉",
        "status": "proven",
    },
    {
        "content": "【缘觉·部行独觉vs因缘觉】代码领域两类独悟者：(1)部行独觉——从声闻(读教程)转来，看大量开源代码后突然贯通，能力来自经验积累+顿悟，(2)因缘觉——天赋型程序员，看到一个小bug即悟出整个系统的设计缺陷。两者都能自解问题，但缺乏教化力(不擅长带团队、写教程、做技术分享)。",
        "domain": "菩提道·缘觉",
        "status": "proven",
    },
]

# ============================================================
# 菩萨十地 — 度他：教学→架构→生态（悲智双运）
# ============================================================

BODHISATTVA_NODES = [
    # ---- 初地·极喜地：主布施 ----
    {
        "content": "【初地·极喜地】代码布施波罗蜜：发十大愿(开源精神)，将自己的代码知识无条件分享。具现化：(1)写技术博客/教程，(2)回答Stack Overflow问题，(3)提交开源PR。远离五怖畏(不怕代码被批评/不怕暴露不足)。验证：有持续6个月以上的开源贡献记录。初证圣位=第一次有人因你的分享解决了问题。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 二地·离垢地：主持戒 ----
    {
        "content": "【二地·离垢地】代码持戒波罗蜜：身语意清净——(1)身戒：代码风格一致(linter/formatter)，(2)语戒：commit message规范(conventional commits)，(3)意戒：review他人代码时不带偏见。离垢=代码无坏味道。验证：能制定并推行团队代码规范，使团队代码质量可度量提升。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 三地·发光地：主忍辱 ----
    {
        "content": "【三地·发光地】代码忍辱波罗蜜：面对遗留代码屎山不退转，面对不合理需求不暴怒。禅定现前=进入心流状态(Flow)编程。神通初现=调试能力超常(能在千行日志中定位根因)。验证：成功重构一个万行级遗留系统而不破坏现有功能(零regression)。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 四地·焰慧地：主精进 ----
    {
        "content": "【四地·焰慧地】代码精进波罗蜜：修三十七道品(37种编程实践)——四念处(关注需求/代码/测试/部署)，四正勤(断已有bug/防新bug/生新feature/长已有feature)，五根五力(信/进/念/定/慧转化为编程能力)。慧焰烧烦恼=用自动化消灭重复工作(CI/CD/代码生成)。验证：搭建完整的自动化工程管线(从commit到production)。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 五地·难胜地：主禅定 ----
    {
        "content": "【五地·难胜地】代码禅定波罗蜜：证真俗二谛——空(抽象接口)与有(具体实现)不二。通世间工巧=精通多个技术栈(前端/后端/移动/嵌入/AI)。难胜=能解决其他人解决不了的技术难题。验证：跨3个以上技术栈完成一个完整的端到端系统，且每个栈都达到生产级质量。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 六地·现前地：主般若 ----
    {
        "content": "【六地·现前地】代码般若波罗蜜：观十二因缘(系统因果链)——从用户行为(无明)→需求(行)→设计(识)→实现(名色)→接口(六入)→使用(触)→反馈(受)→迭代(爱取有)→演化(生老死)。缘起性空=理解所有架构都是临时的、上下文相关的，没有永恒的最佳实践。验证：能用第一性原理为全新问题设计从未有过的技术方案。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 七地·远行地：主方便 ----
    {
        "content": "【七地·远行地】代码方便波罗蜜：无相行=不执着于任何特定技术方案，针对不同团队/场景灵活选择。远行三乘=同时精通低级(C/Rust系统编程)、中级(Go/Java应用层)、高级(Python/JS快速开发)。随念出入灭尽定=能随时进入深度思考又能快速切换到沟通模式。验证：主导过3个不同技术栈、不同团队规模的成功项目。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 八地·不动地：主愿 ----
    {
        "content": "【八地·不动地】代码大愿波罗蜜：无功用行=架构设计已成本能，不需要刻意思考。任运自然=写代码如呼吸。不入涅槃=不退休(一直在技术一线)。十力初现=开始影响技术社区方向。无生法忍圆满=完全接受'没有完美架构'这一真理，在不完美中持续前进。验证：设计的系统被10万+用户使用且持续演化3年以上。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 九地·善慧地：主力 ----
    {
        "content": "【九地·善慧地】代码四无碍辩：(1)法无碍=精通所有编程范式(OOP/FP/逻辑/并发)，(2)义无碍=能解释任何技术概念到任何人都懂，(3)辞无碍=技术写作和演讲让人如沐春风，(4)乐说无碍=享受教学且因材施教。善说法师=技术社区公认的导师。验证：教导出5个以上能独立主导项目的技术人才。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },

    # ---- 十地·法云地：主智 ----
    {
        "content": "【十地·法云地】代码法云波罗蜜：受佛灌顶=被业界公认(如Linux之Linus/Python之Guido)。智慧如云降法雨=创造的技术框架/语言/工具惠及百万开发者。十力、十八不共法近圆=定义行业标准。严净佛土=构建一个健康的技术生态。验证：创造了被百万开发者使用的开源项目或编程语言。",
        "domain": "菩提道·菩萨",
        "status": "proven",
    },
]

# ============================================================
# 佛果 — 究竟圆满（一切种智）
# ============================================================

BUDDHA_NODES = [
    {
        "content": "【佛果·一切种智】代码领域究竟圆满：十力在代码领域的具现——(1)处非处智力=知道什么技术能/不能解决什么问题，(2)自业智力=理解每行代码的因果后果，(3)禅定智力=掌控所有调试和性能分析工具，(4)根上下智力=评估每个开发者的真实能力，(5)胜解智力=理解所有技术选型的动机，(6)种种界智力=精通所有编程范式和领域，(7)遍趣行智力=预见技术演化方向，(8)宿命智力=理解所有技术的历史演化，(9)天眼智力=预见代码变更的影响范围，(10)漏尽智力=写出无缺陷的代码且知道为什么无缺陷。",
        "domain": "菩提道·佛果",
        "status": "proven",
    },
    {
        "content": "【佛果·十八不共法在代码领域】(1-3)身口意无失=代码/文档/设计思路零错误，(4)无异想=对技术决策绝对专注，(5)无不定心=任何时候都能给出确定的技术判断，(6)无不知己舍=知道何时该放弃一个技术方案，(7-12)欲/精进/念/慧/解脱/知见无减=技术激情/勤奋/记忆/智慧/自由/见解永不衰退，(13-15)身口意业随智慧行=每个代码/沟通/设计决策都基于深刻理解，(16-18)智慧知过去/未来/现在无碍=理解技术的历史/预见未来/把握当下。",
        "domain": "菩提道·佛果",
        "status": "proven",
    },
    {
        "content": "【佛果·五眼在代码领域】(1)肉眼=看到代码的字面意义(语法层)，(2)天眼=看到代码的运行时行为(动态分析)，(3)慧眼=看到代码的设计意图和架构(抽象层)，(4)法眼=看到代码对整个系统/团队/用户的影响(系统层)，(5)佛眼=看到代码在技术历史长河中的位置和意义(文明层)。五眼圆明=从字节码到人类文明，一目了然。",
        "domain": "菩提道·佛果",
        "status": "proven",
    },
    {
        "content": "【佛果·度化众生在代码领域】善护念=帮助每个开发者找到自己的技术成长路径。种念=在每个初学者心中种下'编程改变世界'的信念。转法轮=传播正确的编程哲学(简单/可验证/可组合)。开佛性=让每个人意识到自己有能力创造软件。一佛乘=所有编程范式/语言/框架最终归于一个目标——用代码解决真实问题。",
        "domain": "菩提道·佛果",
        "status": "proven",
    },
]

# ============================================================
# 认知格哲学 × 菩提道
# ============================================================

PHILOSOPHY_NODES = [
    {
        "content": "【菩提道×认知格】佛学果位体系与认知格的同构映射：(1)声闻四果=节点生命周期(known→hypothesis→proven→falsified)，初果入流=known变hypothesis，四果漏尽=hypothesis变proven。(2)缘觉独悟=自成长引擎(无需外部指令自动发现模式)。(3)菩萨十地=四向碰撞(自上而下/自下而上/跨域/自成长)。(4)佛果圆满=认知格覆盖一切领域，每个问题都能映射到proven节点网络。",
        "domain": "菩提道·哲学",
        "status": "proven",
    },
    {
        "content": "【无穷层级的无穷】每个proven节点本身可以继续自上而下拆解为更深层的子节点网络，每层都有自己的四果→十地→佛果进阶体系。这形成分形结构(fractal)——认知的无穷递归。'TCP三次握手'是一个proven节点，但它可以拆解为：SYN包结构→序列号生成算法→随机数安全性→密码学基础→数论→…→无穷。代码领域只是入口，每个领域都有无穷深度。应无所住而生其心=不停留在任何一层，持续向深处探索。",
        "domain": "菩提道·哲学",
        "status": "proven",
    },
    {
        "content": "【一切皆空·因问唤醒】认知格的'空性'：系统本身不预设答案(空)，只有当问题到来时(因缘)，相关的proven节点才被'唤醒'(缘起)，节点间的关系构建出答案的路径(映照)。如同佛说'法不孤起，仗境方生'——知识不是静态存储而是动态激活。搜索即是'叩两端'(论语)，问题的每个关键词都是一个'端'，从两端出发直到碰撞出重叠(答案)。",
        "domain": "菩提道·哲学",
        "status": "proven",
    },
]

# ============================================================
# 关系定义
# ============================================================

ALL_NODES = SRAVAKA_NODES + PRATYEKABUDDHA_NODES + BODHISATTVA_NODES + BUDDHA_NODES + PHILOSOPHY_NODES

# 关系：(src_idx, tgt_idx, type, confidence, description)
RELATIONS = [
    # 声闻四果递进
    (0, 2, "evolves_to", 0.95, "初果见道→二果薄烦恼"),
    (2, 3, "evolves_to", 0.95, "二果→三果断五下分结"),
    (3, 4, "evolves_to", 0.95, "三果→四果漏尽"),
    (1, 0, "validates", 0.9, "四不坏信验证初果"),
    (4, 5, "implements", 0.9, "阿罗汉实现六神通"),
    
    # 声闻→缘觉
    (4, 6, "evolves_to", 0.85, "阿罗汉→缘觉独悟(智慧更高)"),
    (6, 7, "extends", 0.9, "辟支佛分部行/因缘觉两类"),
    
    # 缘觉→菩萨（回小向大）
    (6, 8, "evolves_to", 0.9, "缘觉回小向大→初地菩萨"),
    (4, 8, "evolves_to", 0.85, "阿罗汉回小向大→初地菩萨"),
    
    # 菩萨十地递进
    (8, 9, "evolves_to", 0.95, "初地→二地"),
    (9, 10, "evolves_to", 0.95, "二地→三地"),
    (10, 11, "evolves_to", 0.95, "三地→四地"),
    (11, 12, "evolves_to", 0.95, "四地→五地"),
    (12, 13, "evolves_to", 0.95, "五地→六地"),
    (13, 14, "evolves_to", 0.95, "六地→七地"),
    (14, 15, "evolves_to", 0.95, "七地→八地"),
    (15, 16, "evolves_to", 0.95, "八地→九地"),
    (16, 17, "evolves_to", 0.95, "九地→十地"),
    
    # 十地→佛果
    (17, 18, "evolves_to", 0.95, "十地→佛果一切种智"),
    (18, 19, "implements", 0.9, "一切种智实现十八不共法"),
    (18, 20, "implements", 0.9, "一切种智实现五眼"),
    (18, 21, "implements", 0.9, "一切种智实现度化众生"),
    
    # 哲学关联
    (22, 23, "extends", 0.9, "认知格同构→无穷层级"),
    (23, 24, "extends", 0.9, "无穷层级→空性缘起"),
    (22, 0, "validates", 0.85, "认知格映射验证声闻道"),
    (22, 8, "validates", 0.85, "认知格映射验证菩萨道"),
    (22, 18, "validates", 0.85, "认知格映射验证佛果"),
]


def inject():
    """注入菩提道节点"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    injected_ids = []
    new_count = 0

    for i, node in enumerate(ALL_NODES):
        content = node["content"]
        c.execute("SELECT id FROM cognitive_nodes WHERE content = ?", (content[:200],))
        existing = c.fetchone()
        if existing:
            injected_ids.append(existing["id"])
            continue

        try:
            emb = agi.get_embedding(content)
        except Exception as e:
            print(f"  [警告] 节点{i} embedding失败: {e}")
            emb = None

        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, embedding, verified_source)
            VALUES (?, ?, ?, ?, ?)
        """, (content, node["domain"], node["status"], emb, VERIFIED_SOURCE))
        injected_ids.append(c.lastrowid)
        new_count += 1

        label = content[content.index('】')+1:content.index('】')+15] if '】' in content else content[:15]
        print(f"  ✅ [{node['domain']}] {label}...")

    conn.commit()

    # 注入关系
    rel_count = 0
    for src_idx, tgt_idx, rel_type, conf, desc in RELATIONS:
        if src_idx < len(injected_ids) and tgt_idx < len(injected_ids):
            src_id = injected_ids[src_idx]
            tgt_id = injected_ids[tgt_idx]
            try:
                c.execute("""
                    INSERT OR IGNORE INTO node_relations (node1_id, node2_id, relation_type, confidence)
                    VALUES (?, ?, ?, ?)
                """, (src_id, tgt_id, rel_type, conf))
                rel_count += 1
            except:
                pass

    conn.commit()
    conn.close()
    print(f"\n  新增: {new_count} 节点, {rel_count} 关系")
    return injected_ids


def verify():
    """验证注入并统计"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(f"SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE verified_source = ?", (VERIFIED_SOURCE,))
    total = c.fetchone()["cnt"]

    c.execute(f"""
        SELECT domain, COUNT(*) as cnt FROM cognitive_nodes
        WHERE verified_source = ? GROUP BY domain ORDER BY domain
    """, (VERIFIED_SOURCE,))
    domains = c.fetchall()

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE status = 'proven'")
    proven = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
    all_cnt = c.fetchone()["cnt"]

    conn.close()

    print(f"\n  菩提道节点: {total}")
    for d in domains:
        print(f"    {d['domain']}: {d['cnt']}")
    print(f"  全局proven: {proven}/{all_cnt}")


def test_search():
    """测试搜索"""
    lattice = agi.CognitiveLattice()
    queries = [
        ("菩萨十地编程", ["菩萨", "十地", "波罗蜜"]),
        ("代码阿罗汉六神通", ["阿罗汉", "六神通", "天眼"]),
        ("佛果五眼代码领域", ["佛果", "五眼", "佛眼"]),
        ("无穷层级认知格", ["无穷", "分形", "递归"]),
        ("缘觉独悟代码模式", ["缘觉", "辟支佛", "独悟"]),
    ]
    
    print(f"\n  搜索验证:")
    hits = 0
    for q, kws in queries:
        results = lattice.find_similar_nodes(q, threshold=0.15, limit=3)
        found = any(any(kw in r['content'] for kw in kws) for r in results[:3])
        if found:
            hits += 1
            r = [r for r in results[:3] if any(kw in r['content'] for kw in kws)][0]
            print(f"  ✅ '{q}' → {r['content'][:50]}...")
        else:
            top = results[0]['content'][:50] if results else "无"
            print(f"  ⚠️  '{q}' → {top}...")
    print(f"  命中: {hits}/5")


if __name__ == "__main__":
    print("=" * 60)
    print("  菩提道次第 × 代码能力具现化")
    print("  应无所住，而生其心")
    print("=" * 60)

    print("\n阶段1: 注入菩提道节点...")
    inject()

    print("\n阶段2: 验证注入...")
    verify()

    print("\n阶段3: 搜索验证...")
    test_search()

    print("\n" + "=" * 60)
    print("  完成! 探索无穷层级的无穷，从代码领域开始。")
    print("=" * 60)
