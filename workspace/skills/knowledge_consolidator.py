#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 知识整合引擎
核心能力:
  1. 跨域模式挖掘 — 发现不同领域之间的深层结构相似性
  2. 知识压缩 — 将大量碎片节点合并为高密度认知结晶
  3. 自动推理链 — 从已知节点推导未知结论
  4. 知识图谱分析 — 发现孤立节点、关键枢纽、知识断层

LLM 的知识是平面的，此引擎将知识编织为立体网络。

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def _call_llm(messages):
    import agi_v13_cognitive_lattice as agi
    return agi.llm_call(messages)


def mine_cross_domain_patterns(lattice, min_domains=2):
    """
    跨域模式挖掘：找到在多个领域中反复出现的相同模式
    例：「递归分解」在编程/数学/管理/学习中都适用 → 这是一个深层模式
    """
    c = lattice.conn.cursor()
    # 获取所有领域及其节点
    c.execute("SELECT DISTINCT domain FROM cognitive_nodes WHERE status IN ('known', 'proven')")
    domains = [r['domain'] for r in c.fetchall()]
    
    if len(domains) < min_domains:
        return {"success": False, "error": f"需要至少{min_domains}个领域", "patterns": []}
    
    # 从每个领域采样节点
    domain_samples = {}
    for d in domains:
        c.execute("""
            SELECT content FROM cognitive_nodes 
            WHERE domain = ? AND status IN ('known', 'proven')
            ORDER BY access_count DESC LIMIT 10
        """, (d,))
        domain_samples[d] = [r['content'] for r in c.fetchall()]
    
    prompt = [
        {"role": "system", "content": """你是跨域模式挖掘专家。分析不同领域的知识节点，发现深层结构相似性。

寻找的模式类型：
1. 通用原则 — 在多个领域都成立的抽象规律
2. 同构关系 — 不同领域中结构相似的概念对
3. 可迁移方法 — 一个领域的方法可以移植到另一个领域

输出 JSON 数组：
[{
  "pattern": "模式描述",
  "domains_involved": ["领域1", "领域2"],
  "evidence": ["支撑证据1", "支撑证据2"],
  "insight": "这个模式的深层含义",
  "application": "如何利用这个模式"
}]"""},
        {"role": "user", "content": f"各领域知识节点：\n{json.dumps(domain_samples, ensure_ascii=False, indent=2)}\n\n请挖掘跨域模式："}
    ]
    
    result = _call_llm(prompt)
    import agi_v13_cognitive_lattice as agi
    patterns = agi.extract_items(result)
    
    # 将发现的模式注入认知网络
    for p in patterns:
        if isinstance(p, dict) and p.get('pattern'):
            content = f"[跨域模式] {p['pattern']}"
            domains = p.get('domains_involved', [])
            nid = lattice.add_node(content, '跨域模式', 'hypothesis', source='pattern_mining', silent=True)
            if nid and p.get('insight'):
                insight_nid = lattice.add_node(
                    f"[模式洞察] {p['insight']}", '跨域模式', 'hypothesis',
                    source='pattern_mining', silent=True
                )
                if insight_nid:
                    lattice.add_relation(nid, insight_nid, 'pattern_insight', 0.8, '模式与洞察')
    
    return {"success": True, "patterns": patterns, "count": len(patterns)}


def compress_knowledge(lattice, domain=None, threshold=0.85):
    """
    知识压缩：将高度相似的节点合并为一个高密度认知结晶
    相似度 > threshold 的节点被视为冗余，合并为一个更精准的表述
    """
    c = lattice.conn.cursor()
    if domain:
        c.execute("SELECT id, content, domain FROM cognitive_nodes WHERE domain = ? AND status IN ('known', 'proven')", (domain,))
    else:
        c.execute("SELECT id, content, domain FROM cognitive_nodes WHERE status IN ('known', 'proven')")
    
    nodes = [dict(r) for r in c.fetchall()]
    if len(nodes) < 3:
        return {"success": True, "message": "节点太少，无需压缩", "compressed": 0}
    
    # 找相似组
    groups = []
    used = set()
    
    for i, n1 in enumerate(nodes):
        if n1['id'] in used:
            continue
        group = [n1]
        for j, n2 in enumerate(nodes[i+1:], i+1):
            if n2['id'] in used:
                continue
            similar = lattice.find_similar_nodes(n1['content'], threshold=threshold, limit=5)
            for s in similar:
                if s['id'] == n2['id']:
                    group.append(n2)
                    used.add(n2['id'])
                    break
        if len(group) >= 2:
            used.add(n1['id'])
            groups.append(group)
    
    if not groups:
        return {"success": True, "message": "未发现冗余节点", "compressed": 0}
    
    # 让 LLM 为每组生成压缩后的表述
    compressed_count = 0
    for group in groups[:5]:  # 每次最多压缩5组
        contents = [g['content'] for g in group]
        domain = group[0]['domain']
        
        prompt = [
            {"role": "system", "content": "将以下高度相似的知识点合并为一个更精准、更完整的表述。只输出合并后的一句话。"},
            {"role": "user", "content": "\n".join(f"- {c}" for c in contents)}
        ]
        result = _call_llm(prompt)
        raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
        
        if raw and len(raw) > 5:
            nid = lattice.add_node(
                f"[结晶] {raw.strip()}", domain, 'proven',
                source='knowledge_compression', silent=True
            )
            compressed_count += 1
    
    return {"success": True, "groups_found": len(groups), "compressed": compressed_count}


def build_reasoning_chain(lattice, question, max_steps=5):
    """
    自动推理链：从已知节点出发，逐步推导到回答目标问题
    每一步推理都锚定在认知网络的真实节点上
    """
    # 收集相关节点
    related = lattice.find_similar_nodes(question, threshold=0.3, limit=10)
    
    if not related:
        return {"success": False, "error": "认知网络中没有相关节点", "chain": []}
    
    known_facts = [f"[{r['domain']}] {r['content']}" for r in related if r.get('status') in ('known', 'proven')]
    hypotheses = [f"[{r['domain']}] {r['content']}" for r in related if r.get('status') == 'hypothesis']
    
    prompt = [
        {"role": "system", "content": f"""你是逻辑推理引擎。基于给定的已知事实，构建一条推理链来回答问题。

规则：
1. 每步推理必须基于已知事实或前一步的结论
2. 明确标注每步使用的依据
3. 如果推理链中有不确定的环节，标注为「需验证」
4. 最多 {max_steps} 步

输出 JSON 数组：
[{{
  "step": 1,
  "reasoning": "推理内容",
  "based_on": "基于哪个已知事实",
  "confidence": 0.0-1.0,
  "needs_verification": true/false
}}]"""},
        {"role": "user", "content": f"""问题：{question}

已知事实：
{chr(10).join(known_facts[:8]) if known_facts else '（无直接相关已知）'}

相关假设：
{chr(10).join(hypotheses[:5]) if hypotheses else '（无）'}

请构建推理链："""}
    ]
    
    result = _call_llm(prompt)
    import agi_v13_cognitive_lattice as agi
    chain = agi.extract_items(result)
    
    # 将推理链中的结论注入认知网络
    for step in chain:
        if isinstance(step, dict) and step.get('reasoning'):
            confidence = step.get('confidence', 0.5)
            needs_v = step.get('needs_verification', True)
            status = 'hypothesis' if needs_v else ('known' if confidence > 0.8 else 'hypothesis')
            lattice.add_node(
                f"[推理] {step['reasoning']}", '推理链', status,
                source='reasoning_chain', silent=True
            )
    
    return {"success": True, "question": question, "chain": chain, "steps": len(chain)}


def analyze_network_topology(lattice):
    """
    分析认知网络拓扑结构
    发现：孤立节点、关键枢纽、知识断层、领域桥梁
    """
    c = lattice.conn.cursor()
    
    # 节点连接度
    c.execute("""
        SELECT n.id, n.content, n.domain, n.status,
               COUNT(DISTINCT r.id) as connections
        FROM cognitive_nodes n
        LEFT JOIN node_relations r ON (r.node1_id = n.id OR r.node2_id = n.id)
        GROUP BY n.id
        ORDER BY connections DESC
    """)
    all_nodes = [dict(r) for r in c.fetchall()]
    
    # 孤立节点（0连接）
    isolated = [n for n in all_nodes if n['connections'] == 0]
    
    # 枢纽节点（连接数 top 10）
    hubs = all_nodes[:10]
    
    # 跨域桥梁（连接不同领域的节点）
    c.execute("""
        SELECT n.id, n.content, n.domain,
               COUNT(DISTINCT n2.domain) as bridge_domains
        FROM cognitive_nodes n
        JOIN node_relations r ON (r.node1_id = n.id OR r.node2_id = n.id)
        JOIN cognitive_nodes n2 ON (n2.id = CASE WHEN r.node1_id = n.id THEN r.node2_id ELSE r.node1_id END)
        WHERE n2.domain != n.domain
        GROUP BY n.id
        HAVING bridge_domains >= 2
        ORDER BY bridge_domains DESC LIMIT 10
    """)
    bridges = [dict(r) for r in c.fetchall()]
    
    # 领域统计
    c.execute("""
        SELECT domain, COUNT(*) as node_count,
               SUM(CASE WHEN status = 'known' THEN 1 ELSE 0 END) as known_count,
               SUM(CASE WHEN status = 'hypothesis' THEN 1 ELSE 0 END) as hyp_count
        FROM cognitive_nodes GROUP BY domain ORDER BY node_count DESC
    """)
    domain_stats = [dict(r) for r in c.fetchall()]
    
    return {
        "total_nodes": len(all_nodes),
        "isolated_count": len(isolated),
        "isolated_samples": [{"content": n['content'][:60], "domain": n['domain']} for n in isolated[:5]],
        "hub_nodes": [{"content": n['content'][:60], "domain": n['domain'], "connections": n['connections']} for n in hubs],
        "bridge_nodes": [{"content": n['content'][:60], "domain": n['domain'], "bridge_domains": n['bridge_domains']} for n in bridges],
        "domain_stats": domain_stats,
        "health_score": round(1.0 - (len(isolated) / max(len(all_nodes), 1)), 3)
    }


# === 技能元数据 ===
SKILL_META = {
    "name": "知识整合引擎",
    "description": "跨域模式挖掘+知识压缩+自动推理链+网络拓扑分析。将碎片知识编织为立体认知网络。",
    "tags": ["知识整合", "模式挖掘", "推理链", "网络分析"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["mine_cross_domain_patterns", "compress_knowledge", "build_reasoning_chain", "analyze_network_topology"]
}

if __name__ == "__main__":
    print("=== 知识整合引擎 ===")
    print("需要认知网络实例运行")
    print("通过 API 调用各项能力")
