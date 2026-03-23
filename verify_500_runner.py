#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
500次复杂问题拆解验证 - 运行器
将每个复杂问题通过Orchestrator拆解为智谱AI可无幻觉执行的任务清单
结果存储到 verification_results/ 文件夹
"""
import json, time, os, sys, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agi_v13_cognitive_lattice as agi
import orchestrator as orch_module
from problems_500 import generate_problems

RESULTS_DIR = Path(__file__).parent / "verification_results"
RESULTS_DIR.mkdir(exist_ok=True)

def run_decomposition(orchestrator, problem_id, problem_text):
    """对单个问题执行拆解，返回结果字典"""
    t0 = time.time()
    result = {
        "id": problem_id,
        "problem": problem_text,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "task_list": [],
        "thinking_steps": [],
        "model_used": None,
        "complexity": 0,
        "task_type": None,
        "routing_reason": None,
        "grounding_ratio": 0,
        "duration_ms": 0,
        "error": None,
    }
    try:
        orch_result = orchestrator.process(
            problem_text, context_nodes=[], enable_tracking=True
        )
        result["status"] = "success"
        result["model_used"] = orch_result.get("model_used", "unknown")
        result["complexity"] = orch_result.get("complexity", 0)
        result["task_type"] = orch_result.get("task_type", "")
        result["routing_reason"] = orch_result.get("routing", {}).get("reason", "")
        result["grounding_ratio"] = orch_result.get("grounding_ratio", 0)
        result["thinking_steps"] = orch_result.get("thinking_steps", [])
        result["duration_ms"] = orch_result.get("duration_ms", 0)
        # 提取任务清单（从回答文本中解析）
        text = orch_result.get("text", "")
        result["response_text"] = text[:2000]  # 截断保存
        # 尝试从文本中提取任务列表
        tasks = []
        for line in text.split("\n"):
            line = line.strip()
            if line and (line.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.",
                                          "6.", "7.", "8.", "9.", "•", "→"))):
                tasks.append(line)
        result["task_list"] = tasks[:50]  # 最多保留50条
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        traceback.print_exc()

    result["duration_ms"] = result["duration_ms"] or int((time.time() - t0) * 1000)
    return result


def main():
    print("=" * 60)
    print("  500次复杂问题拆解验证")
    print("=" * 60)

    # 初始化
    print("\n[1/3] 初始化认知格和Orchestrator...")
    lattice = agi.CognitiveLattice()
    agi.seed_database(lattice)
    orchestrator = orch_module.TaskOrchestrator(lattice)
    print("  ✓ 初始化完成")

    # 生成问题
    print("[2/3] 生成500个复杂问题...")
    problems = generate_problems()
    print(f"  ✓ 已生成 {len(problems)} 个问题")

    # 执行拆解
    print("[3/3] 开始逐个拆解...\n")
    summary = {
        "total": len(problems),
        "success": 0,
        "error": 0,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "model_usage": {},
        "avg_complexity": 0,
        "avg_duration_ms": 0,
        "task_type_dist": {},
    }
    all_results = []
    complexities = []
    durations = []

    for i, problem in enumerate(problems, 1):
        print(f"  [{i:3d}/{len(problems)}] {problem[:50]}...", end="", flush=True)
        result = run_decomposition(orchestrator, i, problem)
        all_results.append(result)

        if result["status"] == "success":
            summary["success"] += 1
            model = result["model_used"] or "unknown"
            summary["model_usage"][model] = summary["model_usage"].get(model, 0) + 1
            tt = result["task_type"] or "unknown"
            summary["task_type_dist"][tt] = summary["task_type_dist"].get(tt, 0) + 1
            complexities.append(result["complexity"])
            durations.append(result["duration_ms"])
            task_count = len(result["task_list"])
            print(f" ✓ {result['model_used']} | 复杂度:{result['complexity']:.1f}"
                  f" | {task_count}条任务 | {result['duration_ms']}ms")
        else:
            summary["error"] += 1
            print(f" ✗ {result['error'][:40]}")

        # 每50个保存一次中间结果
        if i % 50 == 0:
            batch_file = RESULTS_DIR / f"batch_{i:03d}.json"
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump(all_results[i-50:i], f, ensure_ascii=False, indent=2)
            print(f"  >>> 已保存批次文件: {batch_file.name}")

    # 汇总
    summary["end_time"] = datetime.now().isoformat()
    summary["avg_complexity"] = sum(complexities) / len(complexities) if complexities else 0
    summary["avg_duration_ms"] = sum(durations) / len(durations) if durations else 0

    # 保存完整结果
    full_file = RESULTS_DIR / "full_results.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 打印总结
    print("\n" + "=" * 60)
    print("  验证完成!")
    print("=" * 60)
    print(f"  总计: {summary['total']} | 成功: {summary['success']} | 失败: {summary['error']}")
    print(f"  平均复杂度: {summary['avg_complexity']:.2f}")
    print(f"  平均耗时: {summary['avg_duration_ms']:.0f}ms")
    print(f"  模型使用分布: {json.dumps(summary['model_usage'], ensure_ascii=False)}")
    print(f"  任务类型分布: {json.dumps(summary['task_type_dist'], ensure_ascii=False)}")
    print(f"\n  结果目录: {RESULTS_DIR}")
    print(f"  完整结果: {full_file}")
    print(f"  汇总报告: {summary_file}")


if __name__ == "__main__":
    main()
