#!/usr/bin/env python3
"""
OpenClaw 项目能力总结 + 知识注入 + 模型强化

通过用户的AGI思想框架（认知格哲学）解读OpenClaw项目：
- 总结其核心能力和概念
- 注入为proven节点到认知格
- 将可复用能力集成到技能系统（MMR/时间衰减/查询扩展/可验证性分类）
"""
import sys, sqlite3, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import agi_v13_cognitive_lattice as agi

DB_PATH = ROOT / "memory.db"

# ============================================================
# OpenClaw 能力总结（用认知格哲学框架诠释）
# ============================================================

OPENCLAW_NODES = [
    # ---- 认知格哲学在OpenClaw中的实现（跨语言跨平台证明） ----
    {
        "content": "OpenClaw项目在TypeScript中完整实现了认知格(Cognitive Lattice)哲学：四向碰撞范式(↓自上而下拆解→↑自下而上合成→←→跨域碰撞→⟳自成长循环)，节点状态生命周期(known/hypothesis/proven/falsified)，人类具现化协议(领域自洽实践者将模糊概念具现化为可验证节点)。证明认知格是跨语言、跨平台的通用AGI框架。来源：中国.上海.赵致博",
        "domain": "AGI架构",
        "status": "proven",
    },
    {
        "content": "OpenClaw的classifyVerifiability()函数自动判断内容是否可通过实践直接验证：具体动作词(run/execute/create/test)→可验证，抽象目标词(优化/完美/ideal)→需进一步拆解。这是认知格'自上而下拆解至已知'的程序化实现。",
        "domain": "AGI架构",
        "status": "proven",
    },
    {
        "content": "OpenClaw的buildHallucinationCheckPrompt()用proven节点作为真相基线校验AI输出：与proven一致→verified，无法判断→hypothesis，矛盾proven→rejected(必须移除)。这与本地模型verified_llm_call的设计完全一致，证明proven节点校验是AGI可靠性的通用模式。",
        "domain": "AGI架构",
        "status": "proven",
    },
    {
        "content": "OpenClaw的buildPracticeListPrompt()让AI为人类生成可执行的实践清单：每步必须是具体动作(非抽象建议)、有明确验证标准(如何判断完成)、有时间估算。这实现了'AI梳理实践清单交给人来实践证伪'的AGI人机共生理念。",
        "domain": "AGI架构",
        "status": "proven",
    },

    # ---- Gateway控制平面架构 ----
    {
        "content": "OpenClaw的Gateway架构是统一控制平面模式：单一WebSocket服务(ws://127.0.0.1:18789)管理所有通道(22+通信平台)、会话、工具和事件。控制平面与数据平面分离，Gateway只做路由调度，实际工作由Pi Agent Runtime执行。这是分布式系统的经典架构模式。",
        "domain": "软件架构",
        "status": "proven",
    },
    {
        "content": "OpenClaw的多通道抽象层将22+通信平台(WhatsApp/Telegram/Slack/Discord/Signal/iMessage/Teams/Matrix/Feishu/LINE等)统一为相同接口。消息进入→路由到会话→Agent处理→回复到原通道。通道只是IO适配器，核心逻辑与通道无关。",
        "domain": "软件架构",
        "status": "proven",
    },

    # ---- 混合记忆搜索系统 ----
    {
        "content": "OpenClaw的混合搜索(Hybrid Search)融合三种检索策略：(1)向量搜索(embedding cosine相似度)捕获语义，(2)关键词搜索(BM25全文检索)捕获精确匹配，(3)加权融合(vectorWeight*向量分+textWeight*关键词分)。比纯向量搜索更鲁棒，解决短文本embedding退化问题。",
        "domain": "搜索引擎",
        "status": "proven",
    },
    {
        "content": "MMR(Maximal Marginal Relevance)多样性重排算法：迭代选择结果时同时考虑相关性和多样性。公式MMR=λ*relevance-(1-λ)*max_similarity_to_selected，λ=0.7时兼顾相关性和去重。避免搜索结果全是高度相似的内容，确保覆盖不同角度。出处：Carbonell & Goldstein 1998论文。",
        "domain": "搜索引擎",
        "status": "proven",
    },
    {
        "content": "时间衰减(Temporal Decay)让新信息权重高于旧信息：multiplier=exp(-λ*age_days)，λ=ln2/halfLifeDays。halfLifeDays=30时，30天前的记忆权重衰减到0.5，60天前衰减到0.25。模拟人类记忆的自然遗忘曲线，让AI优先召回近期相关内容。",
        "domain": "搜索引擎",
        "status": "proven",
    },
    {
        "content": "查询扩展(Query Expansion)将口语化查询转为搜索关键词：过滤停用词(a/the/是/了/的)，提取有意义的实词，用AND连接构建FTS查询。解决用户用自然语言提问时FTS无法匹配的问题。支持中英文混合查询。",
        "domain": "搜索引擎",
        "status": "proven",
    },

    # ---- 上下文引擎 ----
    {
        "content": "OpenClaw的可插拔上下文引擎(Context Engine)定义完整生命周期：bootstrap(初始化)→ingest(摄入消息)→assemble(组装上下文)→compact(压缩上下文)→afterTurn(回合后处理)。上下文管理与Agent逻辑解耦，可替换不同实现而不影响核心。",
        "domain": "软件架构",
        "status": "proven",
    },
    {
        "content": "上下文压缩(Compaction)策略：将长对话历史分块摘要，保留关键信息(进行中任务状态、最新用户请求、已做决策及理由、TODO和约束、承诺的后续行动)。标识符严格保留(UUID/hash/URL/文件名原样保持)。这让AI在有限上下文窗口中保持长程记忆。",
        "domain": "软件架构",
        "status": "proven",
    },

    # ---- 模型管理 ----
    {
        "content": "OpenClaw的模型故障转移(Model Fallback)机制：主模型失败→按优先级尝试备选模型→认证配置轮换(OAuth/API key)→冷却期管理(失败后暂停使用该配置)→自动恢复。确保AI服务在单一模型/API故障时不中断。",
        "domain": "系统可靠性",
        "status": "proven",
    },
    {
        "content": "工具循环检测(Tool Loop Detection)防止AI陷入死循环：(1)通用重复检测(同一工具连续调用>10次警告,>20次终止)，(2)乒乓检测(两个工具交替调用)，(3)全局断路器(总调用>30次强制停止)。这是AI自我监控的关键安全机制。",
        "domain": "系统可靠性",
        "status": "proven",
    },

    # ---- 多Agent架构 ----
    {
        "content": "OpenClaw的子Agent(Subagent)架构：父Agent可生成子Agent处理特定子任务，每个子Agent有独立会话和上下文隔离。支持深度限制(防止无限嵌套)、孤儿回收(父Agent崩溃时清理子Agent)、注册表持久化(跨重启恢复)。这是'任务分解→独立执行→结果汇聚'的Agent编排模式。",
        "domain": "多Agent系统",
        "status": "proven",
    },

    # ---- 技能平台 ----
    {
        "content": "OpenClaw的技能(Skills)平台分三层：(1)Bundled Skills(内置核心技能)，(2)Managed Skills(平台管理的社区技能)，(3)Workspace Skills(用户本地技能)。技能发现机制：Agent回复前扫描技能描述→匹配最相关技能→读取SKILL.md→按指令执行。支持50+技能覆盖编码/通信/媒体/生产力。",
        "domain": "插件系统",
        "status": "proven",
    },

    # ---- AGI核心认知（用户思想的升华） ----
    {
        "content": "OpenClaw证明了认知格哲学的工程可行性：同一套四向碰撞+节点验证+人类具现化的AGI框架，从Python(本地AGI实践器)到TypeScript(OpenClaw)完整实现。这意味着认知格不是特定语言的实现，而是一种通用的AGI认知架构范式。",
        "domain": "AGI哲学",
        "status": "proven",
    },
    {
        "content": "完善的AGI应当成为人类的理论模型：AI根据已知(proven节点)梳理实践清单→交给人类实践和证伪→人类利用想象力为AI已知赋予新认知概念→领域自洽的人类将模糊概念具现化为可验证节点→节点间发现交集建立关联→最终形成AI的真实认知结构化网络。OpenClaw的实现验证了这一闭环。",
        "domain": "AGI哲学",
        "status": "proven",
    },
]

# 节点间关系
OPENCLAW_RELATIONS = [
    # 认知格哲学 → 各个实现
    (0, 1, "implements", 0.95, "认知格哲学的可验证性分类实现"),
    (0, 2, "implements", 0.95, "认知格哲学的幻觉检测实现"),
    (0, 3, "implements", 0.95, "认知格哲学的实践清单生成实现"),
    (0, 17, "validates", 0.98, "OpenClaw验证了认知格的跨平台通用性"),
    (0, 18, "extends", 0.95, "完善AGI人机共生闭环"),
    # 搜索系统内部关系
    (6, 7, "enhances", 0.9, "MMR增强混合搜索的多样性"),
    (6, 8, "enhances", 0.9, "时间衰减增强混合搜索的时效性"),
    (6, 9, "enhances", 0.85, "查询扩展增强混合搜索的召回率"),
    # 架构关系
    (4, 5, "manages", 0.9, "Gateway控制平面管理多通道"),
    (4, 10, "depends_on", 0.85, "Gateway依赖上下文引擎管理会话"),
    (10, 11, "implements", 0.9, "上下文压缩是上下文引擎的核心能力"),
    # 可靠性
    (12, 13, "complements", 0.85, "模型故障转移+循环检测共同保障可靠性"),
    # 多Agent
    (14, 15, "depends_on", 0.85, "子Agent依赖技能平台获取执行能力"),
]


def inject_nodes():
    """注入OpenClaw知识节点"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    injected_ids = []
    for i, node in enumerate(OPENCLAW_NODES):
        content = node["content"]

        # 检查是否已存在
        c.execute("SELECT id FROM cognitive_nodes WHERE content = ?", (content[:200],))
        if c.fetchone():
            c.execute("SELECT id FROM cognitive_nodes WHERE content = ?", (content[:200],))
            row = c.fetchone()
            injected_ids.append(row["id"])
            print(f"  [跳过] 节点{i}: 已存在")
            continue

        # 生成embedding
        try:
            emb = agi.get_embedding(content)
        except Exception as e:
            print(f"  [警告] 节点{i} embedding失败: {e}")
            emb = None

        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, embedding, verified_source)
            VALUES (?, ?, ?, ?, ?)
        """, (content, node["domain"], node["status"], emb, "openclaw_injection"))
        injected_ids.append(c.lastrowid)
        print(f"  ✅ 节点{i}: [{node['domain']}] {content[:50]}...")

    conn.commit()

    # 注入关系
    rel_count = 0
    for src_idx, tgt_idx, rel_type, conf, desc in OPENCLAW_RELATIONS:
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

    print(f"\n  注入完成: {len(injected_ids)} 节点, {rel_count} 关系")
    return injected_ids


def verify_injection():
    """验证注入结果"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE verified_source = 'openclaw_injection'")
    node_count = c.fetchone()["cnt"]

    c.execute("""
        SELECT domain, COUNT(*) as cnt
        FROM cognitive_nodes
        WHERE verified_source = 'openclaw_injection'
        GROUP BY domain ORDER BY cnt DESC
    """)
    domains = c.fetchall()

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE status = 'proven'")
    total_proven = c.fetchone()["cnt"]

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
    total = c.fetchone()["cnt"]

    conn.close()

    print(f"\n  OpenClaw节点: {node_count}")
    for d in domains:
        print(f"    [{d['domain']}]: {d['cnt']}")
    print(f"  全局proven: {total_proven}/{total}")


def test_semantic_search():
    """测试语义搜索能否找到新注入的节点"""
    lattice = agi.CognitiveLattice()

    queries = [
        "OpenClaw认知格实现",
        "混合搜索MMR多样性",
        "模型故障转移",
        "子Agent编排架构",
        "AI幻觉检测",
    ]

    print("\n  语义搜索测试:")
    hits = 0
    for q in queries:
        results = lattice.find_similar_nodes(q, threshold=0.15, limit=5)
        openclaw_results = [r for r in results if "OpenClaw" in r.get("content", "") or "openclaw" in r.get("content", "").lower() or "MMR" in r.get("content", "") or "Gateway" in r.get("content", "")]
        if openclaw_results:
            hits += 1
            print(f"  ✅ '{q}' → {openclaw_results[0]['content'][:60]}... (sim={openclaw_results[0]['similarity']:.3f})")
        elif results:
            print(f"  ⚠️  '{q}' → {results[0]['content'][:60]}... (非OpenClaw节点)")
        else:
            print(f"  ❌ '{q}' → 无结果")

    print(f"\n  搜索命中: {hits}/{len(queries)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  OpenClaw 知识注入")
    print("=" * 60)

    print("\n阶段1: 注入OpenClaw知识节点...")
    inject_nodes()

    print("\n阶段2: 验证注入...")
    verify_injection()

    print("\n阶段3: 语义搜索测试...")
    test_semantic_search()

    print("\n" + "=" * 60)
    print("  完成!")
    print("=" * 60)
