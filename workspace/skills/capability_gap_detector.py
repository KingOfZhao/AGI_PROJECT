#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 能力缺口检测与自修复引擎
描述: F6实现 — 基于规则+模式匹配检测系统能力缺口，提供修复建议，
      支持自动触发forge_tool锻造缺失能力。
标签: 能力检测, 缺口分析, 自修复, 规则引擎
创建: 2026-03-20
由 AGI v13.3 Cognitive Lattice 自主构建
"""

import sys
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

SKILL_META = {
    "name": "capability_gap_detector",
    "display_name": "能力缺口检测与自修复引擎",
    "description": "基于规则+模式匹配检测系统能力缺口，分析执行失败原因，提供修复建议并可触发自动锻造",
    "tags": ["能力检测", "缺口分析", "自修复", "规则引擎"],
    "created_at": "2026-03-20",
    "version": "1.0",
    "capabilities": [
        "detect_gaps: 关键词+模式匹配检测能力缺口",
        "analyze_failures: 执行失败原因分析(ImportError/Timeout等)",
        "suggest_fixes: 根据缺口类型生成修复建议",
        "auto_forge: 可编码修复的缺口自动触发forge_tool",
        "gap_report: 生成能力缺口报告",
    ],
    "api_endpoints": [
        "POST /api/capability_gaps  → 检测问题中的能力缺口",
    ],
}


def detect_and_report(question: str, action_results: list = None) -> dict:
    """检测能力缺口并生成报告"""
    from action_engine import detect_capability_gaps, CAPABILITY_RULES
    
    gaps = detect_capability_gaps(question, action_results)
    
    # 分类统计
    code_fixable = [g for g in gaps if g.get("fixable_by_code")]
    human_needed = [g for g in gaps if not g.get("fixable_by_code")]
    
    report = {
        "total_gaps": len(gaps),
        "code_fixable": len(code_fixable),
        "human_needed": len(human_needed),
        "gaps": gaps,
        "summary": "",
        "total_rules": len(CAPABILITY_RULES),
    }
    
    if gaps:
        lines = [f"检测到 {len(gaps)} 个能力缺口:"]
        for g in gaps:
            icon = "🔧" if g.get("fixable_by_code") else "👤"
            lines.append(f"  {icon} {g['capability']} ({g['status']}) → {g['fix']}")
        report["summary"] = "\n".join(lines)
    else:
        report["summary"] = "✅ 未检测到能力缺口，当前系统能力覆盖该任务"
    
    return report


if __name__ == "__main__":
    print("=" * 50)
    print("能力缺口检测器 · 自测")
    print("=" * 50)
    
    tests = [
        "帮我搜索最新的Python框架",
        "生成一个PDF报告并用语音播报",
        "写一个PLC梯形图控制温度",
        "用Python计算碳扩散系数",
    ]
    
    for q in tests:
        print(f"\n问: {q}")
        r = detect_and_report(q)
        print(f"  缺口: {r['total_gaps']} (可编码:{r['code_fixable']}, 需人工:{r['human_needed']})")
        if r['gaps']:
            for g in r['gaps']:
                print(f"    - {g['capability']}: {g['fix']}")
