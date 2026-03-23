#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 自我评估与反思引擎
核心能力:
  1. 评估自身输出质量 — 对 LLM 回复进行多维度打分
  2. 对比验证 — 将推理结论与代码执行结果对比
  3. 知识一致性检查 — 检测认知网络中的矛盾
  4. 能力边界探测 — 主动发现自己不擅长的领域

LLM 无法自我反思，此引擎赋予 AGI 元认知能力。

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


def evaluate_response(question, response, context_nodes=None):
    """
    多维度评估 LLM 输出质量
    维度：准确性、完整性、逻辑性、可操作性、创新性
    """
    context = ""
    if context_nodes:
        context = "\n相关已知节点：\n" + "\n".join(
            f"- [{n.get('domain','')}] {n.get('content','')[:80]}"
            for n in context_nodes[:5]
        )

    prompt = [
        {"role": "system", "content": """你是严格的输出质量评审官。对 AI 的回复进行多维度评估。

评分标准（每项0-10分）：
1. accuracy（准确性）— 是否包含事实错误
2. completeness（完整性）— 是否覆盖了问题的所有方面
3. logic（逻辑性）— 推理链是否自洽
4. actionability（可操作性）— 是否给出了可执行的建议
5. novelty（创新性）— 是否有超出常规的洞察

输出 JSON：
{
  "scores": {"accuracy": 8, "completeness": 7, "logic": 9, "actionability": 6, "novelty": 5},
  "overall": 7.0,
  "strengths": ["优势1"],
  "weaknesses": ["不足1"],
  "improvement": "如何改进",
  "contradictions": ["发现的矛盾（如果有）"]
}

要严格！不要给虚高分数。"""},
        {"role": "user", "content": f"问题：{question}\n\nAI回复：\n{response[:3000]}{context}"}
    ]

    result = _call_llm(prompt)
    if isinstance(result, dict) and 'scores' in result:
        return result
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    try:
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {"scores": {}, "overall": 0, "error": "评估解析失败"}


def verify_by_execution(claim, lattice=None):
    """
    通过代码执行验证一个声明是否正确
    例：「Python 的 sorted 是稳定排序」→ 写代码验证
    """
    from workspace.skills.code_synthesizer import synthesize_and_verify

    task = f"""验证以下声明是否正确，编写代码进行实验验证：
声明：{claim}

要求：
1. 设计一个测试来验证或反驳这个声明
2. 输出明确的结论：VERIFIED（已验证）或 FALSIFIED（已反驳）
3. 给出实验证据"""

    result = synthesize_and_verify(task, save_path="verification_test.py")

    verified = False
    if result.get("success"):
        output = result.get("output", "").lower()
        verified = "verified" in output or "true" in output or "正确" in output

    verdict = {
        "claim": claim,
        "verified": verified,
        "execution_success": result.get("success", False),
        "evidence": result.get("output", "")[:500],
        "iterations": result.get("iterations", 0)
    }

    # 更新认知网络
    if lattice and result.get("success"):
        status = "proven" if verified else "falsified"
        lattice.add_node(
            f"[{'已验证' if verified else '已反驳'}] {claim}",
            "验证结果", status, source="self_evaluation", silent=True
        )

    return verdict


def check_consistency(lattice, domain=None, sample_size=20):
    """
    检测认知网络中的矛盾
    找出互相矛盾的已知节点对
    """
    c = lattice.conn.cursor()
    if domain:
        c.execute("""
            SELECT content, domain, status FROM cognitive_nodes
            WHERE status IN ('known', 'proven') AND domain = ?
            ORDER BY RANDOM() LIMIT ?
        """, (domain, sample_size))
    else:
        c.execute("""
            SELECT content, domain, status FROM cognitive_nodes
            WHERE status IN ('known', 'proven')
            ORDER BY RANDOM() LIMIT ?
        """, (sample_size,))

    nodes = [dict(r) for r in c.fetchall()]
    if len(nodes) < 3:
        return {"success": True, "contradictions": [], "checked": 0}

    prompt = [
        {"role": "system", "content": """你是逻辑一致性检查器。检查以下知识节点中是否存在互相矛盾的对。

输出 JSON 数组（如果没有矛盾则输出空数组 []）：
[{
  "node_a": "节点A内容",
  "node_b": "节点B内容",
  "contradiction": "矛盾描述",
  "severity": "high/medium/low",
  "resolution": "建议的解决方式"
}]

只报告真正的逻辑矛盾，不要报告只是不同角度的描述。"""},
        {"role": "user", "content": "知识节点：\n" + "\n".join(
            f"[{n['domain']}] {n['content']}" for n in nodes
        )}
    ]

    result = _call_llm(prompt)
    import agi_v13_cognitive_lattice as agi
    contradictions = agi.extract_items(result)

    # 标记矛盾节点
    for c_item in contradictions:
        if isinstance(c_item, dict) and c_item.get("contradiction"):
            lattice.add_node(
                f"[矛盾] {c_item['contradiction']}", "自我评估",
                "hypothesis", source="consistency_check", silent=True
            )

    return {
        "success": True,
        "contradictions": contradictions,
        "checked": len(nodes),
        "contradiction_count": len(contradictions)
    }


def probe_capability_boundaries(lattice):
    """
    探测 AGI 的能力边界
    通过一系列测试问题，发现哪些领域回答质量低
    """
    # 从每个领域取一个问题
    c = lattice.conn.cursor()
    c.execute("""
        SELECT DISTINCT domain FROM cognitive_nodes
        WHERE status = 'hypothesis'
        GROUP BY domain HAVING COUNT(*) >= 2
    """)
    domains = [r['domain'] for r in c.fetchall()]

    test_results = []
    for d in domains[:8]:
        c.execute("""
            SELECT content FROM cognitive_nodes
            WHERE domain = ? AND status = 'hypothesis'
            ORDER BY RANDOM() LIMIT 1
        """, (d,))
        row = c.fetchone()
        if not row:
            continue

        question = row['content']
        # 生成回答
        prompt = [
            {"role": "user", "content": question}
        ]
        answer = _call_llm(prompt)
        raw_answer = answer.get('raw', str(answer)) if isinstance(answer, dict) else str(answer)

        # 评估回答
        eval_result = evaluate_response(question, raw_answer)
        overall = eval_result.get('overall', 0)

        test_results.append({
            "domain": d,
            "question": question[:80],
            "score": overall,
            "weaknesses": eval_result.get("weaknesses", [])
        })

    # 排序找出薄弱领域
    test_results.sort(key=lambda x: x.get('score', 0))

    weak_domains = [r for r in test_results if r.get('score', 10) < 6]
    strong_domains = [r for r in test_results if r.get('score', 0) >= 7]

    return {
        "success": True,
        "total_tested": len(test_results),
        "weak_domains": weak_domains,
        "strong_domains": strong_domains,
        "all_results": test_results,
        "recommendation": f"建议优先学习: {', '.join(r['domain'] for r in weak_domains[:3])}" if weak_domains else "各领域表现均衡"
    }


# === 技能元数据 ===
SKILL_META = {
    "name": "自我评估与反思引擎",
    "description": "输出质量评估+代码验证声明+知识一致性检查+能力边界探测。赋予AGI元认知能力。",
    "tags": ["自我评估", "元认知", "一致性检查", "质量控制"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["evaluate_response", "verify_by_execution", "check_consistency", "probe_capability_boundaries"]
}

if __name__ == "__main__":
    print("=== 自我评估引擎自测 ===")
    # 简单自测：评估一个示例回答
    test_eval = evaluate_response(
        "什么是递归？",
        "递归是函数调用自身的编程技术。它需要基准条件防止无限循环。常用于树遍历、分治算法等。"
    )
    print(f"评估分数: {test_eval.get('overall', '?')}")
    print(f"优势: {test_eval.get('strengths', [])}")
    print(f"不足: {test_eval.get('weaknesses', [])}")
