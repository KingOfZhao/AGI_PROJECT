#!/usr/bin/env python3
"""
菩提道次第 — 能力评估与成长路径引擎

应无所住，而生其心。
一切皆空，因问唤醒真实节点，构建关联映照答案，运用能力验证。

将佛学果位体系映射为代码领域能力阶梯：
- 声闻四果（初果→四果）：个人编程能力自利解脱
- 缘觉：无师独悟代码模式
- 菩萨十地（初地→十地）：度他，悲智双运
- 佛果：一切种智，究竟圆满

核心功能：
1. assess_level() — 评估当前能力果位
2. get_growth_path() — 获取下一步成长路径
3. activate_nodes() — 因问唤醒：根据问题激活相关proven节点
4. build_answer_path() — 构建关联映照答案路径
5. explore_depth() — 探索无穷层级的无穷
"""
import sys, sqlite3, json, re, time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "memory.db"

# ============================================================
# 果位定义（从低到高）
# ============================================================

STAGES = [
    # 声闻四果
    {"id": "srotapanna", "name": "初果·须陀洹", "alias": "预流果",
     "tier": "声闻", "level": 1,
     "essence": "见道位，断三结(我见/戒禁取/疑)，入圣流",
     "code_map": "理解变量/控制流/函数，能写100行可运行程序",
     "verify": "独立写出100行可运行程序"},

    {"id": "sakadagami", "name": "二果·斯陀含", "alias": "一来果",
     "tier": "声闻", "level": 2,
     "essence": "薄贪瞋痴，代码坏味道开始自然察觉",
     "code_map": "理解YAGNI/DRY，能重构自己的旧代码",
     "verify": "能重构自己三个月前的代码并发现改进点"},

    {"id": "anagami", "name": "三果·阿那含", "alias": "不还果",
     "tier": "声闻", "level": 3,
     "essence": "断五下分结，不还初级错误",
     "code_map": "主导千行级模块设计，对O(n)有直觉",
     "verify": "主导千行级模块的设计与实现"},

    {"id": "arhat", "name": "四果·阿罗汉", "alias": "漏尽",
     "tier": "声闻", "level": 4,
     "essence": "漏尽通，自了生死，个人技术精通",
     "code_map": "48小时内用陌生语言完成完整项目",
     "verify": "用陌生语言48小时内完成完整项目"},

    # 缘觉
    {"id": "pratyekabuddha", "name": "缘觉·辟支佛", "alias": "独觉",
     "tier": "缘觉", "level": 5,
     "essence": "无师独悟，观因缘而觉，智慧高于阿罗汉但不说法",
     "code_map": "通过阅读源码逆向理解未文档化的复杂系统",
     "verify": "逆向理解一个未文档化的复杂系统"},

    # 菩萨十地
    {"id": "bhumi_1", "name": "初地·极喜地", "alias": "欢喜地",
     "tier": "菩萨", "level": 6,
     "essence": "主布施，发十大愿(开源精神)",
     "code_map": "持续6个月以上开源贡献",
     "verify": "有持续6个月以上的开源贡献记录"},

    {"id": "bhumi_2", "name": "二地·离垢地", "alias": "持戒",
     "tier": "菩萨", "level": 7,
     "essence": "身语意清净，代码规范推行",
     "code_map": "制定并推行团队代码规范",
     "verify": "制定团队代码规范使质量可度量提升"},

    {"id": "bhumi_3", "name": "三地·发光地", "alias": "忍辱",
     "tier": "菩萨", "level": 8,
     "essence": "面对遗留屎山不退转，禅定现前(心流)",
     "code_map": "成功重构万行级遗留系统零regression",
     "verify": "重构万行级遗留系统不破坏现有功能"},

    {"id": "bhumi_4", "name": "四地·焰慧地", "alias": "精进",
     "tier": "菩萨", "level": 9,
     "essence": "慧焰烧烦恼(自动化消灭重复工作)",
     "code_map": "搭建完整CI/CD自动化管线",
     "verify": "搭建从commit到production的完整自动化管线"},

    {"id": "bhumi_5", "name": "五地·难胜地", "alias": "禅定",
     "tier": "菩萨", "level": 10,
     "essence": "真俗二谛不二(抽象与实现统一)",
     "code_map": "跨3个技术栈完成端到端生产级系统",
     "verify": "跨3个以上技术栈完成端到端系统"},

    {"id": "bhumi_6", "name": "六地·现前地", "alias": "般若",
     "tier": "菩萨", "level": 11,
     "essence": "观十二因缘(系统因果链)，缘起性空",
     "code_map": "用第一性原理设计全新技术方案",
     "verify": "为全新问题设计从未有过的技术方案"},

    {"id": "bhumi_7", "name": "七地·远行地", "alias": "方便",
     "tier": "菩萨", "level": 12,
     "essence": "无相行，三乘精通(低/中/高级语言)",
     "code_map": "主导3个不同技术栈不同团队的成功项目",
     "verify": "主导过3个不同栈不同团队规模的成功项目"},

    {"id": "bhumi_8", "name": "八地·不动地", "alias": "大愿",
     "tier": "菩萨", "level": 13,
     "essence": "无功用行(架构本能)，无生法忍圆满",
     "code_map": "设计的系统被10万+用户使用且演化3年+",
     "verify": "系统被10万+用户使用且持续演化3年以上"},

    {"id": "bhumi_9", "name": "九地·善慧地", "alias": "力",
     "tier": "菩萨", "level": 14,
     "essence": "四无碍辩(法/义/辞/乐说)",
     "code_map": "教导出5个以上能独立主导项目的技术人才",
     "verify": "教导出5个以上独立主导项目的技术人才"},

    {"id": "bhumi_10", "name": "十地·法云地", "alias": "智",
     "tier": "菩萨", "level": 15,
     "essence": "受佛灌顶，智慧如云降法雨",
     "code_map": "创造被百万开发者使用的开源项目或语言",
     "verify": "创造被百万开发者使用的开源项目或编程语言"},

    # 佛果
    {"id": "buddha", "name": "佛果·一切种智", "alias": "无上正等正觉",
     "tier": "佛果", "level": 16,
     "essence": "十力+十八不共法+五眼圆明，究竟圆满",
     "code_map": "代码领域无所不知无所不度，从字节码到文明一目了然",
     "verify": "一切种智——无需验证，因为已经超越验证本身"},
]


def assess_level(capabilities: list) -> dict:
    """
    评估当前能力对应的果位。

    Args:
        capabilities: 已具备的能力列表，如
            ["能写100行程序", "理解YAGNI", "主导过千行模块"]

    Returns:
        当前果位信息 + 下一步成长建议
    """
    current_level = 0
    matched = []
    unmatched = []

    for stage in STAGES:
        # 检查是否有任何能力匹配该果位的验证标准
        stage_matched = False
        for cap in capabilities:
            cap_lower = cap.lower()
            verify_lower = stage["verify"].lower()
            # 模糊匹配：能力描述中包含验证标准的关键词
            verify_keywords = re.findall(r'[\u4e00-\u9fff]{2,}', verify_lower)
            verify_keywords += re.findall(r'[a-zA-Z]{3,}', verify_lower)
            match_count = sum(1 for kw in verify_keywords if kw in cap_lower)
            if match_count >= 2 or cap_lower in verify_lower or verify_lower in cap_lower:
                stage_matched = True
                break

        if stage_matched:
            current_level = stage["level"]
            matched.append(stage["name"])
        else:
            unmatched.append(stage)

    current_stage = None
    next_stage = None
    for s in STAGES:
        if s["level"] == current_level:
            current_stage = s
        if s["level"] == current_level + 1:
            next_stage = s

    return {
        "current_level": current_level,
        "current_stage": current_stage["name"] if current_stage else "凡夫(未入流)",
        "current_tier": current_stage["tier"] if current_stage else "未入道",
        "matched_stages": matched,
        "next_stage": next_stage["name"] if next_stage else "已究竟",
        "next_verify": next_stage["verify"] if next_stage else "无需验证",
        "next_code_map": next_stage["code_map"] if next_stage else "一切圆满",
        "progress": f"{current_level}/{len(STAGES)}",
        "remaining": len(STAGES) - current_level,
    }


def get_growth_path(current_level: int = 0) -> list:
    """
    获取从当前果位开始的完整成长路径。

    Args:
        current_level: 当前果位等级(0=凡夫)

    Returns:
        剩余成长阶梯列表
    """
    path = []
    for stage in STAGES:
        if stage["level"] > current_level:
            path.append({
                "level": stage["level"],
                "name": stage["name"],
                "tier": stage["tier"],
                "essence": stage["essence"],
                "code_goal": stage["code_map"],
                "verify": stage["verify"],
            })
    return path


def activate_nodes(question: str, limit: int = 10) -> dict:
    """
    因问唤醒：根据问题激活相关proven节点。

    一切皆空——系统不预设答案。
    问题到来时，相关proven节点被唤醒(缘起)，
    节点间的关系构建答案路径(映照)。

    Args:
        question: 用户问题
        limit: 最大激活节点数

    Returns:
        被唤醒的节点 + 关系路径
    """
    import agi_v13_cognitive_lattice as agi
    lattice = agi.CognitiveLattice()

    # 唤醒：语义搜索激活相关节点
    activated = lattice.find_similar_nodes(question, threshold=0.15, limit=limit)

    # 只保留proven节点（真实节点才能映照答案）
    proven_nodes = [n for n in activated if n.get("status") == "proven"]

    # 构建关联：查找被唤醒节点之间的关系
    relations = []
    if len(proven_nodes) >= 2:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        node_ids = [n["id"] for n in proven_nodes]
        placeholders = ",".join("?" * len(node_ids))
        c.execute(f"""
            SELECT r.node1_id, r.node2_id, r.relation_type, r.confidence,
                   n1.content as src_content, n2.content as tgt_content
            FROM node_relations r
            JOIN cognitive_nodes n1 ON r.node1_id = n1.id
            JOIN cognitive_nodes n2 ON r.node2_id = n2.id
            WHERE r.node1_id IN ({placeholders}) AND r.node2_id IN ({placeholders})
        """, node_ids + node_ids)

        for row in c.fetchall():
            relations.append({
                "from": row["src_content"][:50],
                "to": row["tgt_content"][:50],
                "type": row["relation_type"],
                "confidence": row["confidence"],
            })
        conn.close()

    return {
        "question": question,
        "activated_count": len(proven_nodes),
        "total_searched": len(activated),
        "proven_nodes": [{
            "content": n["content"][:100],
            "domain": n["domain"],
            "similarity": n["similarity"],
        } for n in proven_nodes],
        "relations": relations,
        "philosophy": "一切皆空，因问唤醒，构建关联，映照答案",
    }


def explore_depth(node_content: str, max_depth: int = 3) -> dict:
    """
    探索无穷层级的无穷。

    每个proven节点可以继续拆解为更深层的子节点网络。
    这形成分形结构(fractal)——认知的无穷递归。

    Args:
        node_content: 要探索的节点内容
        max_depth: 最大递归深度

    Returns:
        多层级探索结果
    """
    import agi_v13_cognitive_lattice as agi
    lattice = agi.CognitiveLattice()

    def _explore(content, depth):
        if depth >= max_depth:
            return {"content": content[:80], "depth": depth, "status": "可继续深入(无穷)"}

        # 从当前内容提取关键概念作为子查询
        cn_terms = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
        en_terms = re.findall(r'[a-zA-Z]{3,}', content)
        sub_queries = (cn_terms + en_terms)[:3]  # 取前3个概念

        children = []
        for sq in sub_queries:
            results = lattice.find_similar_nodes(sq, threshold=0.3, limit=2)
            proven = [r for r in results if r.get("status") == "proven"
                      and r["content"][:30] != content[:30]]  # 排除自身
            if proven:
                child = proven[0]
                children.append(_explore(child["content"], depth + 1))

        return {
            "content": content[:80],
            "depth": depth,
            "children": children if children else [{"status": "叶节点(待实践具现化)"}],
        }

    result = _explore(node_content, 0)
    result["philosophy"] = "每层都有自己的四果→十地→佛果，认知的无穷递归"
    return result


def get_all_stages() -> list:
    """获取完整果位体系"""
    return STAGES


def get_stage_by_id(stage_id: str) -> dict:
    """按ID获取特定果位信息"""
    for s in STAGES:
        if s["id"] == stage_id:
            return s
    return None


# ============================================================
# 命令行测试
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  菩提道次第 · 能力评估引擎")
    print("=" * 60)

    # 测试1: 评估
    print("\n1. 能力评估测试:")
    result = assess_level([
        "能写100行程序",
        "理解YAGNI和DRY",
        "主导过千行模块设计",
    ])
    print(f"   当前: {result['current_stage']} ({result['current_tier']})")
    print(f"   进度: {result['progress']}")
    print(f"   下一步: {result['next_stage']}")
    print(f"   验证: {result['next_verify']}")

    # 测试2: 成长路径
    print(f"\n2. 成长路径 (从{result['current_level']}开始):")
    path = get_growth_path(result['current_level'])
    for p in path[:5]:
        print(f"   [{p['tier']}] {p['name']}: {p['code_goal']}")
    if len(path) > 5:
        print(f"   ... 还有 {len(path)-5} 个阶位")

    # 测试3: 因问唤醒
    print("\n3. 因问唤醒测试:")
    wake = activate_nodes("如何设计一个可扩展的分布式系统？")
    print(f"   问题: {wake['question']}")
    print(f"   唤醒: {wake['activated_count']}个proven节点")
    for n in wake['proven_nodes'][:3]:
        print(f"   → [{n['domain']}] {n['content'][:50]}...")
    if wake['relations']:
        print(f"   关系: {len(wake['relations'])}条")

    # 测试4: 深度探索
    print("\n4. 深度探索(无穷层级):")
    depth = explore_depth("TCP拥塞控制四个阶段", max_depth=2)
    def print_tree(node, indent=0):
        print("   " + "  " * indent + f"[深度{node.get('depth', '?')}] {node.get('content', node.get('status', ''))[:60]}")
        for child in node.get("children", []):
            print_tree(child, indent + 1)
    print_tree(depth)

    print(f"\n  完成!")
