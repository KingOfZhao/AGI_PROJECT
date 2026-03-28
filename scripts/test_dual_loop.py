#!/usr/bin/env python3
"""
双环态势网络体系 v2.0 — 集成测试
=================================
测试: COP + OODA内环 + 进化外环 + v1-v7技能链

用法:
  python3 scripts/test_dual_loop.py              # 框架自检 (不调LLM)
  python3 scripts/test_dual_loop.py --live        # 真实LLM调用测试
  python3 scripts/test_dual_loop.py --live --model qwen2.5-coder:7b
"""

import sys
import os
import json
import time
import tempfile
from pathlib import Path

AGI_DIR = Path("/Users/administruter/Desktop/AGI_PROJECT")
sys.path.insert(0, str(AGI_DIR / "workspace"))
sys.path.insert(0, str(AGI_DIR / "scripts"))

from cop_shared_awareness import COP, EventBus, TaskBoard, KnowledgeStore, PathCache
from ooda_controller import OODAController, SkillLoader, EvolutionLoop, DualLoopEngine

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def test_cop_components():
    """测试COP各组件"""
    print("\n" + "=" * 60)
    print("📋 Test 1: COP 组件测试")
    print("=" * 60)

    db_path = Path(tempfile.mktemp(suffix=".db"))
    cop = COP(db_path=db_path)

    # EventBus
    received = []
    cop.bus.subscribe("test.event", lambda e: received.append(e))
    cop.bus.publish("test.event", {"msg": "hello"})
    check("EventBus 发布/订阅", len(received) == 1 and received[0]["data"]["msg"] == "hello")

    # TaskBoard
    tid = cop.tasks.create_task("测试任务A", source="test")
    check("TaskBoard 创建任务", tid is not None and tid.startswith("task_"))
    cop.tasks.update_status(tid, "running", assigned_to="v1")
    task = cop.tasks.get_task(tid)
    check("TaskBoard 更新状态", task["status"] == "running" and task["assigned_to"] == "v1")
    summary = cop.tasks.summary()
    check("TaskBoard 统计", summary["running"] == 1)

    # KnowledgeStore 三层存储
    nid1 = cop.knowledge.add("原始日志数据", layer=1, importance=0.3)
    nid2 = cop.knowledge.add("结构化节点: Fibonacci", layer=2, importance=0.6)
    nid3 = cop.knowledge.add("精炼知识: 递归优化", layer=3, importance=0.9)
    check("KnowledgeStore 三层写入", nid1 > 0 and nid2 > 0 and nid3 > 0)

    results = cop.knowledge.search("Fibonacci", layer=2)
    check("KnowledgeStore 按层搜索", len(results) >= 1)

    cop.knowledge.reference(nid2)
    cop.knowledge.reference(nid2)
    updated = cop.knowledge.search("Fibonacci")[0]
    check("KnowledgeStore 引用计数", updated["ref_count"] >= 2)

    stats = cop.knowledge.stats()
    check("KnowledgeStore 统计",
          stats["layer_1"]["count"] == 1 and stats["layer_3"]["count"] == 1)

    # PathCache
    cop.cache.put("实现排序算法", ["v1_coding", "v4_validate"])
    cached = cop.cache.get("实现排序算法")
    check("PathCache 缓存命中", cached == ["v1_coding", "v4_validate"])
    miss = cop.cache.get("完全不同的任务")
    check("PathCache 缓存未命中", miss is None)
    check("PathCache 命中率", cop.cache.hit_rate > 0)

    # ConflictDetector
    tid2 = cop.tasks.create_task("测试任务B")
    cop.tasks.update_status(tid, "running")
    cop.tasks.update_status(tid2, "running")
    conflicts = cop.conflicts.check_task_conflicts()
    check("ConflictDetector 冲突检测", isinstance(conflicts, list))

    # OODA Log
    cop.log_ooda("test_cycle", "observe", "input", "output", 50, "v1")
    history = cop.get_ooda_history(limit=5)
    check("OODA日志 记录+查询", len(history) >= 1 and history[0]["cycle_id"] == "test_cycle")

    # Full status
    status = cop.full_status()
    check("全局态势 完整性", all(k in status for k in ["tasks", "knowledge", "cache"]))

    # Forgetting
    forgotten = cop.knowledge.run_forgetting()
    check("遗忘引擎 执行", forgotten >= 0)

    cop.close()
    os.unlink(str(db_path))


def test_ooda_framework():
    """测试OODA框架 (mock, 不调LLM)"""
    print("\n" + "=" * 60)
    print("📋 Test 2: OODA 框架测试 (mock)")
    print("=" * 60)

    db_path = Path(tempfile.mktemp(suffix=".db"))
    cop = COP(db_path=db_path)

    class MockSkills:
        def available(self): return ["v1_coding", "v4_validate", "v6_knowledge"]
        def get(self, k): return None
        def call(self, k, inp): return f"[mock_{k}] 输出: {inp[:30]}..."

    skills = MockSkills()
    ooda = OODAController(cop, skills)

    # 测试编码任务路由
    r1 = ooda.run_cycle("实现一个Fibonacci函数")
    check("OODA 编码任务完成", r1["status"] == "done")
    check("OODA 编码路径正确", "v1_coding" in r1["path"])

    # 测试知识图谱任务路由
    r2 = ooda.run_cycle("构建知识图谱")
    check("OODA 知识任务完成", r2["status"] == "done")
    check("OODA 知识路径正确", "v6_knowledge" in r2["path"],
          f"实际路径: {r2['path']}")

    # 测试缓存命中 (完全相同的意图应命中缓存)
    r3 = ooda.run_cycle("实现一个Fibonacci函数")
    check("OODA 缓存命中", cop.cache._hits > 0,
          f"hits={cop.cache._hits}, misses={cop.cache._misses}")

    # 测试进化外环触发
    evo = EvolutionLoop(cop, skills, trigger_every=2)
    evo.tick()  # 第1次, 不触发
    check("进化外环 未触发", evo._evolution_count == 0)
    evo.tick()  # 第2次, 触发
    check("进化外环 已触发", evo._evolution_count == 1)

    # 检查COP最终状态
    status = cop.full_status()
    check("COP 任务全部完成", status["tasks"]["done"] == 3)
    check("COP 知识沉淀", status["knowledge"]["layer_1"]["count"] > 0)

    cop.close()
    os.unlink(str(db_path))


def test_skill_loader():
    """测试技能加载器 (检查v1-v7文件存在性)"""
    print("\n" + "=" * 60)
    print("📋 Test 3: 技能文件完整性检查")
    print("=" * 60)

    skills_dir = AGI_DIR / "workspace" / "skills"
    expected = {
        "v1": "local_llm_coding_chain_v1.py",
        "v2": "local_skill_orchestrator_v2.py",
        "v3": "local_auto_skill_generator_v3.py",
        "v4": "local_code_validator_v4.py",
        "v5": "local_project_scaffolder_v5.py",
        "v6": "local_knowledge_node_builder_v6.py",
        "v7": "local_autonomous_evolver_v7.py",
    }
    for key, fname in expected.items():
        exists = (skills_dir / fname).exists()
        check(f"{key} 技能文件存在", exists, f"{fname}")
        meta = skills_dir / fname.replace(".py", ".meta.json")
        check(f"{key} meta.json存在", meta.exists(), f"{meta.name}")

    # COP + OODA meta
    check("COP meta.json", (skills_dir / "cop_shared_awareness.meta.json").exists())
    check("OODA meta.json", (skills_dir / "ooda_controller.meta.json").exists())


def test_live_ooda(model: str = "qwen2.5-coder:14b"):
    """真实LLM调用测试"""
    print("\n" + "=" * 60)
    print(f"📋 Test 4: 真实OODA循环 (model={model})")
    print("=" * 60)

    # 检测Ollama
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        model_ok = any(model in m for m in models)
    except Exception:
        models, model_ok = [], False

    if not model_ok:
        print(f"  ⚠️ Ollama未运行或模型 {model} 不可用, 跳过真实测试")
        print(f"     可用模型: {models}")
        return

    engine = DualLoopEngine(model=model, evolution_trigger=3)
    check("DualLoopEngine 初始化", len(engine.skills.available()) >= 4,
          f"可用技能: {engine.skills.available()}")

    # 执行一个简单编码任务
    print("\n  🔄 执行真实OODA: 写一个计算阶乘的Python函数...")
    t0 = time.time()
    result = engine.run("写一个计算阶乘的Python函数，要求支持大数和异常处理")
    elapsed = time.time() - t0

    check("真实OODA 执行成功", result["status"] == "done", f"status={result.get('status')}")
    check("真实OODA 有输出", result.get("duration_ms", 0) > 0, f"duration={result.get('duration_ms')}ms")
    check("真实OODA 路径合理", "v1_coding" in result.get("path", []), f"path={result.get('path')}")

    # 检查COP状态
    status = engine.status()
    check("COP 任务记录", status["cop"]["tasks"]["done"] >= 1)
    check("COP 知识沉淀", status["cop"]["knowledge"]["layer_1"]["count"] > 0 or
          status["cop"]["knowledge"]["layer_2"]["count"] > 0)

    print(f"\n  ⏱️ 总耗时: {elapsed:.1f}s")
    print(f"  📊 COP状态: {json.dumps(status['cop']['tasks'], ensure_ascii=False)}")
    print(f"  🧠 知识: {json.dumps(status['cop']['knowledge'], ensure_ascii=False)}")

    engine.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="双环引擎集成测试")
    parser.add_argument("--live", action="store_true", help="运行真实LLM测试")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Ollama模型")
    args = parser.parse_args()

    print("╔═══════════════════════════════════════════════════════╗")
    print("║  双环态势网络体系 v2.0 — 集成测试                     ║")
    print("╚═══════════════════════════════════════════════════════╝")

    test_cop_components()
    test_ooda_framework()
    test_skill_loader()

    if args.live:
        test_live_ooda(model=args.model)

    print("\n" + "=" * 60)
    print(f"📊 测试结果: ✅ {PASS} 通过  ❌ {FAIL} 失败")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
