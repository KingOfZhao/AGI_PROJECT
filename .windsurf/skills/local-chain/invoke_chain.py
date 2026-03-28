#!/usr/bin/env python3
"""
本地调用链快速调用脚本 — 供Windsurf Skill使用
用法: python3 invoke_chain.py "问题" ["上下文"]
"""
import sys
import json

sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/scripts')
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/core')
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT')

from wechat_chain_processor import ChainProcessor, format_chain_result_for_wechat


def invoke(question: str, context: str = "") -> dict:
    """调用7步链并返回结构化结果"""
    chain = ChainProcessor()
    result = chain.process(question, context=context)
    return {
        "answer": result.final_answer,
        "route": result.route_decision,
        "duration": result.total_duration,
        "steps": [{"step": s["step"], "model": s.get("model", ""),
                    "success": s.get("success", False),
                    "duration": s.get("duration", 0)} for s in result.steps],
        "risks": result.risks,
        "hallucination_check": result.hallucination_check,
    }


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "测试调用链"
    context = sys.argv[2] if len(sys.argv) > 2 else ""
    result = invoke(question, context)
    print(json.dumps(result, ensure_ascii=False, indent=2))
