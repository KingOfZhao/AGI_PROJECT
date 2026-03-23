#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 自主学习循环引擎
核心能力: 识别知识空白 → 制定学习计划 → 自主研究 → 代码验证 → 入库
这是 AGI 实现「无限自成长」的关键引擎。
LLM 只能回答被问到的问题，而此引擎主动发现未知并填补。

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def _call_llm(messages):
    import agi_v13_cognitive_lattice as agi
    return agi.llm_call(messages)


def identify_knowledge_gaps(lattice, domain=None, limit=5):
    """
    分析认知网络，识别知识空白区域
    返回 [{gap, domain, priority, suggested_action}]
    """
    stats = lattice.stats()
    
    # 收集各领域的 hypothesis 节点（未验证的假设 = 知识空白）
    c = lattice.conn.cursor()
    if domain:
        c.execute("""
            SELECT content, domain FROM cognitive_nodes 
            WHERE status = 'hypothesis' AND domain = ?
            ORDER BY created_at DESC LIMIT 20
        """, (domain,))
    else:
        c.execute("""
            SELECT content, domain FROM cognitive_nodes 
            WHERE status = 'hypothesis'
            ORDER BY access_count ASC, created_at DESC LIMIT 20
        """)
    hypotheses = [dict(r) for r in c.fetchall()]
    
    # 收集已知节点作为上下文
    c.execute("SELECT content, domain FROM cognitive_nodes WHERE status = 'known' ORDER BY RANDOM() LIMIT 10")
    known = [dict(r) for r in c.fetchall()]
    
    prompt = [
        {"role": "system", "content": """你是认知空白分析专家。
分析给定的假设节点（未验证的知识），识别最有价值的知识空白。

输出 JSON 数组：
[{
  "gap": "知识空白的描述",
  "domain": "所属领域",
  "priority": "high/medium/low",
  "suggested_action": "research（网络研究） | code_verify（编写代码验证） | decompose（进一步拆解）",
  "research_query": "如果需要研究，用什么关键词搜索"
}]

优先选择：
1. 与多个已知节点相关但尚未验证的假设
2. 能通过编写代码直接验证的假设
3. 跨领域的知识空白（碰撞潜力大）"""},
        {"role": "user", "content": f"""当前网络统计: {json.dumps(stats, ensure_ascii=False)}

未验证假设（知识空白）:
{json.dumps([h['content'][:100] + ' [' + h['domain'] + ']' for h in hypotheses], ensure_ascii=False)}

已知节点样本:
{json.dumps([k['content'][:80] + ' [' + k['domain'] + ']' for k in known], ensure_ascii=False)}

请识别 {limit} 个最有价值的知识空白："""}
    ]
    
    result = _call_llm(prompt)
    import agi_v13_cognitive_lattice as agi
    items = agi.extract_items(result)
    return items[:limit]


def execute_learning_plan(gaps, lattice):
    """
    对每个知识空白执行学习动作
    research → web_researcher
    code_verify → code_synthesizer
    decompose → 调用认知格拆解
    """
    results = []
    
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        
        action = gap.get("suggested_action", "research")
        gap_desc = gap.get("gap", "")
        domain = gap.get("domain", "general")
        query = gap.get("research_query", gap_desc)
        
        result = {"gap": gap_desc, "action": action, "success": False}
        
        if action == "research":
            try:
                from workspace.skills.web_researcher import research_and_ingest
                r = research_and_ingest(query, lattice)
                result["success"] = r.get("success", False)
                result["knowledge_count"] = r.get("total_points", 0)
                result["ingested"] = r.get("ingested_nodes", 0)
            except Exception as e:
                result["error"] = str(e)
        
        elif action == "code_verify":
            try:
                from workspace.skills.code_synthesizer import synthesize_and_verify
                task = f"验证以下概念是否正确，编写代码测试：{gap_desc}"
                r = synthesize_and_verify(task, save_path=f"verify_{len(results)}.py")
                result["success"] = r.get("success", False)
                result["output"] = r.get("output", "")[:300]
                result["iterations"] = r.get("iterations", 0)
                # 如果验证成功，将假设升级为已知
                if r["success"]:
                    nid = lattice.add_node(
                        f"[已验证] {gap_desc}: {r['output'][:100]}",
                        domain, "proven", source="code_verify", silent=True
                    )
                    result["proven_node_id"] = nid
            except Exception as e:
                result["error"] = str(e)
        
        elif action == "decompose":
            try:
                import agi_v13_cognitive_lattice as agi
                import cognitive_core
                related = lattice.find_similar_nodes(gap_desc, threshold=0.4, limit=3)
                td_result = agi.DualDirectionDecomposer.top_down(gap_desc, related)
                items = agi.extract_items(td_result)
                result["success"] = len(items) > 0
                result["decomposed_into"] = len(items)
                for item in items:
                    content = item.get('content', '') if isinstance(item, dict) else str(item)
                    can_v = item.get('can_verify', False) if isinstance(item, dict) else False
                    d = item.get('domain', domain) if isinstance(item, dict) else domain
                    if content:
                        status = "known" if can_v else "hypothesis"
                        lattice.add_node(content, d, status, source="auto_decompose", silent=True)
            except Exception as e:
                result["error"] = str(e)
        
        results.append(result)
    
    return results


def run_learning_cycle(lattice, domain=None):
    """
    完整的自主学习循环
    1. 识别知识空白
    2. 执行学习计划
    3. 跨域碰撞
    4. 返回学习报告
    """
    import agi_v13_cognitive_lattice as agi
    
    stats_before = lattice.stats()
    
    # 1. 识别空白
    gaps = identify_knowledge_gaps(lattice, domain, limit=3)
    if not gaps:
        return {"success": True, "message": "未发现关键知识空白", "learned": 0}
    
    # 2. 执行学习
    learn_results = execute_learning_plan(gaps, lattice)
    
    # 3. 跨域碰撞
    collisions = agi.CollisionEngine.cross_domain_collide(lattice)
    
    # 4. 统计
    stats_after = lattice.stats()
    new_nodes = stats_after['total_nodes'] - stats_before['total_nodes']
    new_rels = stats_after['total_relations'] - stats_before['total_relations']
    
    # 记录成长日志
    successful = sum(1 for r in learn_results if r.get('success'))
    lattice.log_growth(
        "autonomous_learning", "learn_cycle",
        f"自主学习: 识别{len(gaps)}个空白, 填补{successful}个, +{new_nodes}节点 +{new_rels}关联",
        stats_before['total_nodes'], stats_after['total_nodes'],
        stats_before['total_relations'], stats_after['total_relations']
    )
    
    return {
        "success": True,
        "gaps_identified": len(gaps),
        "gaps_filled": successful,
        "new_nodes": new_nodes,
        "new_relations": new_rels,
        "collisions": collisions,
        "details": learn_results
    }


# === 技能元数据 ===
SKILL_META = {
    "name": "自主学习循环引擎",
    "description": "主动识别知识空白→制定学习计划→Web研究/代码验证/拆解→注入认知网络。实现无限自成长。",
    "tags": ["自主学习", "知识空白", "自成长", "核心能力"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["identify_knowledge_gaps", "execute_learning_plan", "run_learning_cycle"]
}

if __name__ == "__main__":
    print("=== 自主学习引擎自测 ===")
    print("此技能需要认知网络实例运行")
    print("通过 API 调用: POST /api/skills/run {name: '自主学习循环引擎'}")
