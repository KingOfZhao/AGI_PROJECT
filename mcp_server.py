#!/usr/bin/env python3
"""
AGI 认知格 MCP Server

让 Claude for VSCode / Windsurf 可以直接调用本地AGI模型的认知格能力：
- 搜索认知格proven节点
- 按领域获取知识
- 查询认知格统计
- 可验证性分类
- 增强搜索（MMR + 时间衰减）

启动方式: python mcp_server.py
配置方式: 在 Windsurf/VSCode 的 MCP settings 中添加此 server
"""
import sys, sqlite3, json, os
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # 确保工作目录正确，MCP进程可能从任意目录启动

from mcp.server.fastmcp import FastMCP

# ============================================================
# MCP Server 实例
# ============================================================

mcp = FastMCP(
    "AGI-CognitiveLattice",
    instructions="""你正在连接一个本地AGI认知格系统。
该系统包含1000+个经过验证的proven知识节点，覆盖操作系统、网络、数据库、算法、
机器学习、工程实践、分布式系统、安全工程等领域。
使用 search_knowledge 搜索相关知识，使用 get_proven_by_domain 按领域获取知识。
所有proven节点都是经过实践验证的真实知识，可以直接引用。"""
)

DB_PATH = str(ROOT / "memory.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# Tools
# ============================================================

@mcp.tool()
def search_knowledge(query: str, limit: int = 10) -> str:
    """搜索认知格知识节点。
    
    在1000+个proven知识节点中进行语义搜索，返回最相关的结果。
    支持中英文查询。
    
    Args:
        query: 搜索查询（自然语言）
        limit: 返回结果数量（默认10）
    """
    try:
        import agi_v13_cognitive_lattice as agi
        lattice = agi.CognitiveLattice()
        results = lattice.find_similar_nodes(query, threshold=0.2, limit=limit)
        
        if not results:
            return json.dumps({"message": f"未找到与'{query}'相关的知识节点", "results": []}, ensure_ascii=False)
        
        output = []
        for r in results:
            output.append({
                "content": r.get("content", ""),
                "domain": r.get("domain", ""),
                "status": r.get("status", ""),
                "similarity": r.get("similarity", 0),
            })
        
        return json.dumps({"query": query, "count": len(output), "results": output}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def get_proven_by_domain(domain: str, limit: int = 20) -> str:
    """获取指定领域的所有proven（已验证）知识节点。
    
    可用领域包括：操作系统、网络协议、数据库、分布式系统、安全工程、算法、
    机器学习、工程实践、数学基础、并发编程、Python核心、编程基础、
    软件工程、架构设计、DevOps、AGI架构、搜索引擎等。
    
    Args:
        domain: 领域名称（支持模糊匹配）
        limit: 返回数量（默认20）
    """
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT content, domain, status, verified_source
            FROM cognitive_nodes
            WHERE status = 'proven' AND domain LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (f"%{domain}%", limit))
        
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        
        if not rows:
            return json.dumps({"message": f"未找到领域'{domain}'的proven节点", "results": []}, ensure_ascii=False)
        
        return json.dumps({"domain": domain, "count": len(rows), "results": rows}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def get_lattice_stats() -> str:
    """获取认知格统计信息：节点总数、各状态数量、领域分布、关系数量。"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        
        # 状态统计
        c.execute("SELECT status, COUNT(*) as cnt FROM cognitive_nodes GROUP BY status")
        status_counts = {r["status"]: r["cnt"] for r in c.fetchall()}
        
        # 总数
        c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
        total = c.fetchone()["cnt"]
        
        # 关系数
        c.execute("SELECT COUNT(*) as cnt FROM node_relations")
        relations = c.fetchone()["cnt"]
        
        # 领域分布 top 20
        c.execute("""
            SELECT domain, COUNT(*) as cnt FROM cognitive_nodes
            WHERE status = 'proven'
            GROUP BY domain ORDER BY cnt DESC LIMIT 20
        """)
        top_domains = {r["domain"]: r["cnt"] for r in c.fetchall()}
        
        conn.close()
        
        return json.dumps({
            "total_nodes": total,
            "status_distribution": status_counts,
            "total_relations": relations,
            "top_proven_domains": top_domains,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def classify_content(content: str) -> str:
    """判断内容是否可通过实践直接验证。
    
    可验证 = 具体动作，人类可以直接做并验证结果（如"运行pytest"）
    不可验证 = 抽象概念，需要进一步拆解才能验证（如"如何实现完美架构"）
    
    Args:
        content: 要分类的内容
    """
    try:
        from workspace.skills.openclaw_abilities import classify_verifiability
        result = classify_verifiability(content)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def enhanced_search(query: str, limit: int = 10, apply_mmr: bool = True) -> str:
    """增强搜索：查询扩展 + MMR多样性重排。
    
    比普通搜索更智能：自动提取关键词、检测领域、
    用MMR算法去重保证结果覆盖不同角度。
    
    Args:
        query: 搜索查询
        limit: 返回数量
        apply_mmr: 是否启用MMR多样性重排
    """
    try:
        import agi_v13_cognitive_lattice as agi
        from workspace.skills.openclaw_abilities import enhanced_search as es
        
        lattice = agi.CognitiveLattice()
        raw = lattice.find_similar_nodes(query, threshold=0.2, limit=limit * 2)
        result = es(query, raw, apply_mmr=apply_mmr)
        
        # 截取到limit
        result["results"] = result["results"][:limit]
        result["stats"]["total_results"] = len(result["results"])
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def list_domains() -> str:
    """列出认知格中所有领域及其proven节点数量。"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT domain, COUNT(*) as total,
                   SUM(CASE WHEN status='proven' THEN 1 ELSE 0 END) as proven_cnt
            FROM cognitive_nodes
            GROUP BY domain ORDER BY total DESC
        """)
        domains = [{"domain": r["domain"], "total": r["total"], "proven": r["proven_cnt"]} for r in c.fetchall()]
        conn.close()
        return json.dumps({"count": len(domains), "domains": domains}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def bodhi_assess(capabilities: str) -> str:
    """评估当前能力对应的菩提道果位。
    
    将佛学果位映射为代码能力阶梯：
    声闻四果(个人编程)→缘觉(独悟)→菩萨十地(度他)→佛果(圆满)。
    
    Args:
        capabilities: 逗号分隔的能力列表，如 "能写100行程序,理解YAGNI,主导过千行模块"
    """
    try:
        from workspace.skills.bodhi_path import assess_level
        caps = [c.strip() for c in capabilities.split(",") if c.strip()]
        result = assess_level(caps)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def bodhi_activate(question: str) -> str:
    """因问唤醒：根据问题激活相关proven节点，构建关联映照答案。
    
    一切皆空——系统不预设答案。问题到来时，相关proven节点被唤醒(缘起)，
    节点间的关系构建答案路径(映照)。
    
    Args:
        question: 要探索的问题
    """
    try:
        from workspace.skills.bodhi_path import activate_nodes
        result = activate_nodes(question, limit=10)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def bodhi_explore(content: str, max_depth: int = 3) -> str:
    """探索无穷层级的无穷。每个proven节点可继续拆解为更深层子节点网络。
    
    Args:
        content: 要深入探索的知识内容
        max_depth: 最大递归深度(默认3)
    """
    try:
        from workspace.skills.bodhi_path import explore_depth
        result = explore_depth(content, max_depth)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# Resources
# ============================================================

@mcp.resource("lattice://stats")
def resource_stats() -> str:
    """认知格实时统计"""
    return get_lattice_stats()


@mcp.resource("lattice://philosophy")
def resource_philosophy() -> str:
    """认知格核心哲学"""
    return json.dumps({
        "name": "认知格 (Cognitive Lattice)",
        "version": "v13.3",
        "core_philosophy": [
            "自上而下拆解未知到已知（真实物理路径）",
            "自下而上从已知合成新问题",
            "四向碰撞发现重叠构建结构化认知网络",
            "人类领域自洽实践者具现化节点",
            "无限自成长",
        ],
        "node_lifecycle": ["known", "hypothesis", "proven", "falsified"],
        "key_principles": [
            "真正的智能不是参数量而是知识的可验证性",
            "小模型+proven节点轨道 > 大模型自由幻觉",
            "慢而真实 > 快而幻觉",
            "本地模型是真实性守门人，不是推理引擎",
        ],
    }, ensure_ascii=False, indent=2)


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("🧠 AGI Cognitive Lattice MCP Server 启动中...")
    print(f"   数据库: {DB_PATH}")
    print(f"   工具: search_knowledge, get_proven_by_domain, get_lattice_stats,")
    print(f"         classify_content, enhanced_search, list_domains,")
    print(f"         bodhi_assess, bodhi_activate, bodhi_explore")
    print(f"   资源: lattice://stats, lattice://philosophy")
    print()
    mcp.run()
