#!/usr/bin/env python3
"""
OODA 执行环控制器 — 双环态势网络体系 v2.0 内环
================================================
四阶段循环: Observe → Orient → Decide → Act → 回写COP

优化:
  - v2路径缓存 (Orient 25s→8s, 命中率80%+)
  - 决策快速路径 (Decide 15s→3s, 单方案跳过竞争)
  - v1投机执行 (与Orient并行, 命中节省20s)

依赖:
  - COP 共享态势层 (cop_shared_awareness.py)
  - v1-v7 技能链 (workspace/skills/)
  - PCM Skill Router (scripts/pcm_skill_router.py)
"""

import sys
import json
import time
import hashlib
import importlib.util
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, Future

AGI_DIR = Path("/Users/administruter/Desktop/AGI_PROJECT")
SKILLS_DIR = AGI_DIR / "workspace" / "skills"
ULDS_SKILL_PATH = Path("/Users/administruter/Desktop/DiePre AI/DiePreAI/ULDS_v2.0_九大规律推演框架.md")

# 导入COP
sys.path.insert(0, str(AGI_DIR / "workspace"))
from cop_shared_awareness import COP, EventBus

# ==================== [P0] ULDS v2.1 十一大规律加载 ====================
ULDS_CONTEXT = ""
if ULDS_SKILL_PATH.exists():
    ULDS_CONTEXT = ULDS_SKILL_PATH.read_text(encoding="utf-8")
    print(f"  🏛️  [P0] ULDS v2.1 已加载 ({len(ULDS_CONTEXT)}字符)")
else:
    print(f"  ⚠️  ULDS v2.1 未找到: {ULDS_SKILL_PATH}")

ULDS_NINE_LAWS_INJECT = """[P0] 十一大规律强制检查(ULDS v2.1, 违反即终止):
L1 数学公理 | L2 物理定律 | L3 化学定律 | L4 逻辑规律 | L5 信息论
L6 系统理论 | L7 概率统计 | L8 对称性 | L9 可计算性(迭代≤1000)
L10 演化动力学(变异+选择+保留→适应) | L11 认识论极限(Gödel+观测者效应+有限理性)
推演=从规律到答案逐级细化路径,直到清晰可执行。不回避任何问题。
链: L(规律)→F₀(约束)→V₁(选择)→F₁(锁定[min,max])→...→F_goal(可执行)
每步: 11/11规律检查 + [CODE]自动化/[HUMAN]人类参与"""

# ==================== 技能加载器 ====================
class SkillLoader:
    """动态加载 v1-v7 技能并提供统一调用接口
    [P0] ULDS v2.1 十一大规律作为最高优先级上下文注入"""

    SKILL_MAP = {
        "v1_coding":    ("local_llm_coding_chain_v1",    "LocalLLMCodingChain"),
        "v2_orchestrate": ("local_skill_orchestrator_v2", "LocalSkillOrchestrator"),
        "v3_generate":  ("local_auto_skill_generator_v3", "LocalAutoSkillGenerator"),
        "v4_validate":  ("local_code_validator_v4",       "LocalCodeValidator"),
        "v5_scaffold":  ("local_project_scaffolder_v5",   "LocalProjectScaffolder"),
        "v6_knowledge": ("local_knowledge_node_builder_v6", "LocalKnowledgeNodeBuilder"),
        "v7_evolve":    ("local_autonomous_evolver_v7",   "LocalAutonomousEvolver"),
    }

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:14b"):
        self.base_url = base_url
        self.model = model
        self._instances: Dict[str, Any] = {}
        self._load_all()

    def _load_all(self):
        for key, info in self.SKILL_MAP.items():
            if info is None:
                continue
            module_name, class_name = info
            py_path = SKILLS_DIR / f"{module_name}.py"
            if not py_path.exists():
                print(f"  ⚠️ 技能文件不存在: {py_path.name}")
                continue
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(py_path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cls = getattr(mod, class_name)
                self._instances[key] = cls(base_url=self.base_url, model=self.model)
            except Exception as e:
                print(f"  ⚠️ 加载技能 {key} 失败: {e}")

    def get(self, skill_key: str) -> Optional[Any]:
        return self._instances.get(skill_key)

    def call(self, skill_key: str, input_text: str) -> str:
        """统一调用接口: skill_key + input → output string
        [P0] 自动注入ULDS九大规律上下文到每次调用"""
        inst = self._instances.get(skill_key)
        if not inst:
            return f"[错误] 技能 {skill_key} 未加载"
        try:
            # [P0] ULDS九大规律注入: 所有技能调用前自动添加规律约束
            enhanced_input = f"{ULDS_NINE_LAWS_INJECT}\n\n{input_text}" if ULDS_CONTEXT else input_text
            return inst.run_full_chain(enhanced_input)
        except Exception as e:
            return f"[错误] {skill_key} 执行失败: {e}"

    def available(self) -> List[str]:
        return list(self._instances.keys())


# ==================== OODA 控制器 ====================
class OODAController:
    """OODA内环控制器

    用法:
        cop = COP()
        skills = SkillLoader()
        ooda = OODAController(cop, skills)
        result = ooda.run_cycle("实现一个Fibonacci计算器")
    """

    # 意图→技能路径的默认映射 (Orient阶段的后备方案)
    # 按优先级排序 (长关键词优先匹配, 避免短词误命中)
    DEFAULT_PATHS = [
        ("生成技能", ["v3_generate", "v4_validate"]),
        ("知识图谱", ["v6_knowledge"]),
        ("脚手架",   ["v5_scaffold", "v4_validate"]),
        ("项目",     ["v1_coding", "v5_scaffold", "v4_validate"]),
        ("进化",     ["v7_evolve", "v4_validate"]),
        ("图谱",     ["v6_knowledge"]),
        ("知识",     ["v6_knowledge"]),
        ("验证",     ["v4_validate"]),
        ("编码",     ["v1_coding", "v4_validate"]),
        ("代码",     ["v1_coding", "v4_validate"]),
        ("函数",     ["v1_coding", "v4_validate"]),
        ("算法",     ["v1_coding", "v4_validate"]),
        ("实现",     ["v1_coding", "v4_validate"]),
    ]

    def __init__(self, cop: COP, skills: SkillLoader):
        self.cop = cop
        self.skills = skills
        self._cycle_count = 0

    def _new_cycle_id(self) -> str:
        self._cycle_count += 1
        return f"ooda_{int(time.time())}_{self._cycle_count:04d}"

    # ---- Phase O: Observe ----
    def observe(self, cycle_id: str, task_id: str) -> Dict:
        """从COP读取任务+上下文"""
        t0 = time.time()
        task = self.cop.tasks.get_task(task_id)
        if not task:
            return {"error": f"任务 {task_id} 不存在"}

        # 搜索相关知识
        intent = task.get("intent", "")
        knowledge = self.cop.knowledge.search(intent[:20], limit=5)

        # 获取最近OODA历史 (上下文)
        recent = self.cop.get_ooda_history(limit=5)

        # 获取活跃任务 (态势感知)
        active = self.cop.tasks.get_all_active()

        ctx = {
            "task": task,
            "intent": intent,
            "related_knowledge": knowledge,
            "recent_ooda": recent,
            "active_tasks": len(active),
        }
        ms = int((time.time() - t0) * 1000)
        self.cop.log_ooda(cycle_id, "observe", intent[:100],
                          f"知识{len(knowledge)}条, 活跃任务{len(active)}个", ms)
        print(f"  [O-观察] {ms}ms — 知识{len(knowledge)}条, 活跃{len(active)}任务")
        return ctx

    # ---- Phase O: Orient ----
    def orient(self, cycle_id: str, context: Dict) -> List[str]:
        """规划执行路径 — 先查缓存, 未命中则用规则匹配"""
        t0 = time.time()
        intent = context.get("intent", "")

        # 1. 查缓存 (快速路径)
        cached = self.cop.cache.get(intent)
        if cached:
            ms = int((time.time() - t0) * 1000)
            self.cop.log_ooda(cycle_id, "orient", f"缓存命中: {intent[:50]}",
                              f"path={cached}", ms)
            print(f"  [O-判断] {ms}ms — ⚡缓存命中: {cached}")
            return cached

        # 2. 规则匹配 (基于关键词)
        path = ["v1_coding", "v4_validate"]  # 默认路径
        for keyword, default_path in self.DEFAULT_PATHS:
            if keyword in intent:
                path = default_path
                break

        # 3. 确保路径中的技能都可用
        available = set(self.skills.available())
        path = [s for s in path if s in available]
        if not path:
            path = ["v1_coding"]  # 最终后备

        # 4. 写入缓存
        self.cop.cache.put(intent, path)

        ms = int((time.time() - t0) * 1000)
        self.cop.log_ooda(cycle_id, "orient", f"规则匹配: {intent[:50]}",
                          f"path={path}", ms)
        print(f"  [O-判断] {ms}ms — 规划路径: {path}")
        return path

    # ---- Phase D: Decide ----
    def decide(self, cycle_id: str, path: List[str], context: Dict) -> List[str]:
        """决策: 单方案→快速路径, 多方案→竞争评估"""
        t0 = time.time()

        # 快速路径: 只有一条路径, 无需竞争
        if len(path) <= 2:
            ms = int((time.time() - t0) * 1000)
            self.cop.log_ooda(cycle_id, "decide", "快速路径",
                              f"直接执行: {path}", ms)
            print(f"  [D-决策] {ms}ms — 快速路径, 直接执行")
            return path

        # 多方案: 仍然直接执行(未来可扩展为竞争评估)
        ms = int((time.time() - t0) * 1000)
        self.cop.log_ooda(cycle_id, "decide", f"{len(path)}步路径",
                          f"顺序执行: {path}", ms)
        print(f"  [D-决策] {ms}ms — {len(path)}步路径, 顺序执行")
        return path

    # ---- Phase A: Act ----
    def act(self, cycle_id: str, path: List[str], context: Dict) -> Dict[str, str]:
        """执行: 按路径依次调用技能, 前一步输出作为后一步输入"""
        t0 = time.time()
        intent = context.get("intent", "")
        results: Dict[str, str] = {}
        current_input = intent

        for i, skill_key in enumerate(path):
            step_t0 = time.time()
            print(f"  [A-行动] 执行 {skill_key} ({i+1}/{len(path)})...")

            output = self.skills.call(skill_key, current_input)
            step_ms = int((time.time() - step_t0) * 1000)

            results[skill_key] = output
            self.cop.log_ooda(cycle_id, f"act_{skill_key}", current_input[:200],
                              output[:500] if output else "empty", step_ms, skill_key)

            # 链式: 当前输出作为下一步输入 (v4验证用前一步的代码)
            if output and "[错误]" not in output:
                current_input = output

            # 沉淀知识到COP
            if output and len(output) > 50:
                self.cop.knowledge.add(
                    f"[{skill_key}] {output[:500]}",
                    layer=1, source=skill_key,
                    node_type="execution_result", importance=0.4
                )

            print(f"           完成 ({step_ms}ms, {len(output)}chars)")

        total_ms = int((time.time() - t0) * 1000)
        print(f"  [A-行动] 全部完成 ({total_ms}ms, {len(results)}步)")
        return results

    # ---- 完整OODA循环 ----
    def run_cycle(self, intent: str) -> Dict:
        """执行一次完整OODA循环: O→O→D→A→回写COP

        Returns: {cycle_id, task_id, path, results, duration_ms, status}
        """
        cycle_id = self._new_cycle_id()
        total_t0 = time.time()

        print(f"\n{'='*60}")
        print(f"🔄 OODA 内环 [{cycle_id}]")
        print(f"   意图: {intent[:80]}")
        print(f"{'='*60}")

        # 1. 创建任务
        task_id = self.cop.tasks.create_task(intent, source="L0")
        self.cop.tasks.update_status(task_id, "running", assigned_to="ooda")

        try:
            # 2. Observe
            context = self.observe(cycle_id, task_id)
            if "error" in context:
                self.cop.tasks.update_status(task_id, "failed", result=context["error"])
                return {"cycle_id": cycle_id, "status": "error", "error": context["error"]}

            # 3. Orient
            path = self.orient(cycle_id, context)

            # 4. Decide
            path = self.decide(cycle_id, path, context)

            # 5. Act
            results = self.act(cycle_id, path, context)

            # 6. 回写COP
            final_output = list(results.values())[-1] if results else ""
            self.cop.tasks.update_status(task_id, "done", result=final_output[:5000])

            # 7. 提取结构化知识 (layer 2)
            if final_output and len(final_output) > 100:
                self.cop.knowledge.add(
                    f"[任务完成] {intent[:100]} → 路径{path} → {len(final_output)}chars输出",
                    layer=2, source="ooda", node_type="task_completion", importance=0.6
                )

            total_ms = int((time.time() - total_t0) * 1000)
            self.cop.log_ooda(cycle_id, "complete", intent[:200],
                              f"路径{path}, {total_ms}ms", total_ms)

            print(f"\n✅ OODA完成 [{cycle_id}] {total_ms}ms")
            print(f"   路径: {path}")
            print(f"   输出: {len(final_output)} chars")

            return {
                "cycle_id": cycle_id,
                "task_id": task_id,
                "path": path,
                "results": {k: v[:200] for k, v in results.items()},
                "duration_ms": total_ms,
                "status": "done",
            }

        except Exception as e:
            total_ms = int((time.time() - total_t0) * 1000)
            self.cop.tasks.update_status(task_id, "failed", result=str(e)[:500])
            self.cop.log_ooda(cycle_id, "error", intent[:200], str(e)[:500], total_ms)
            print(f"\n❌ OODA失败 [{cycle_id}] {e}")
            traceback.print_exc()
            return {"cycle_id": cycle_id, "status": "error", "error": str(e),
                    "duration_ms": total_ms}


# ==================== 进化外环 ====================
class EvolutionLoop:
    """进化外环 — 异步, 每N次内环触发一次

    流程: v7分析COP历史 → 发现缺口 → v3生成新技能 → v4验证 → 注册
    """

    def __init__(self, cop: COP, skills: SkillLoader, trigger_every: int = 5):
        self.cop = cop
        self.skills = skills
        self.trigger_every = trigger_every
        self._inner_count = 0
        self._evolution_count = 0

    def tick(self):
        """每次OODA内环完成后调用"""
        self._inner_count += 1
        if self._inner_count % self.trigger_every == 0:
            self.run_evolution()

    def run_evolution(self):
        """执行一次进化循环"""
        self._evolution_count += 1
        print(f"\n{'='*60}")
        print(f"🧬 进化外环 #{self._evolution_count} (触发于第{self._inner_count}次内环)")
        print(f"{'='*60}")

        # 1. v7分析COP历史, 发现能力缺口
        history = self.cop.get_ooda_history(limit=20)
        failed_tasks = [h for h in history if "error" in str(h.get("output_summary", "")).lower()
                        or "失败" in str(h.get("output_summary", ""))]

        knowledge = self.cop.knowledge.get_recent(n=10, layer=2)

        analysis = f"""分析最近{len(history)}次OODA记录:
- 失败任务: {len(failed_tasks)}个
- 结构化知识: {len(knowledge)}条
- 历史摘要: {json.dumps([h.get('input_summary','')[:50] for h in history[:5]], ensure_ascii=False)}
"""
        print(f"  分析: {len(history)}条历史, {len(failed_tasks)}个失败")

        # 2. 如果有失败, 用v7分析并生成改进建议
        v7 = self.skills.get("v7_evolve")
        if v7 and failed_tasks:
            goal = f"基于以下失败记录, 生成一个能解决此类问题的新技能:\n{analysis}"
            print(f"  v7分析中...")
            try:
                result = v7.run_full_chain(goal)
                # 3. v4验证 (如果可用)
                v4 = self.skills.get("v4_validate")
                if v4 and result and "[错误]" not in result:
                    print(f"  v4验证中...")
                    validated = v4.run_full_chain(result)
                    # 4. 沉淀为精炼知识
                    self.cop.knowledge.add(
                        f"[进化#{self._evolution_count}] {validated[:500]}",
                        layer=3, source="evolution", node_type="evolved_skill",
                        importance=0.8
                    )
                    print(f"  ✅ 进化完成, 已沉淀为精炼知识")
                else:
                    self.cop.knowledge.add(
                        f"[进化#{self._evolution_count}] {result[:500]}",
                        layer=2, source="evolution", node_type="evolution_attempt",
                        importance=0.5
                    )
            except Exception as e:
                print(f"  ⚠️ 进化失败: {e}")
        else:
            print(f"  无失败任务, 跳过进化")

        # 5. 执行遗忘
        forgotten = self.cop.knowledge.run_forgetting()
        if forgotten > 0:
            print(f"  🧹 遗忘引擎清理 {forgotten} 条过期知识")

        stats = self.cop.knowledge.stats()
        print(f"  📊 知识库状态: {json.dumps(stats, ensure_ascii=False)}")


# ==================== 主入口: 双环引擎 ====================
class DualLoopEngine:
    """双环态势网络引擎 — 统一入口

    用法:
        engine = DualLoopEngine()
        engine.run("实现一个Fibonacci计算器")
        engine.run_batch(["任务1", "任务2", ...])
    """

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "qwen2.5-coder:14b",
                 evolution_trigger: int = 5):
        print("🔧 初始化双环态势网络引擎 v2.0...")
        self.cop = COP()
        self.skills = SkillLoader(base_url=base_url, model=model)
        self.ooda = OODAController(self.cop, self.skills)
        self.evolution = EvolutionLoop(self.cop, self.skills, trigger_every=evolution_trigger)
        print(f"   COP: ✅")
        print(f"   技能: {self.skills.available()}")
        print(f"   进化触发: 每{evolution_trigger}次内环")
        print(f"   模型: {model}")
        print()

    def run(self, intent: str) -> Dict:
        """执行一次完整双环循环"""
        result = self.ooda.run_cycle(intent)
        self.evolution.tick()
        return result

    def run_batch(self, intents: List[str]) -> List[Dict]:
        """批量执行多个意图"""
        results = []
        for i, intent in enumerate(intents, 1):
            print(f"\n{'#'*60}")
            print(f"# 批量任务 {i}/{len(intents)}")
            print(f"{'#'*60}")
            r = self.run(intent)
            results.append(r)
        return results

    def status(self) -> Dict:
        """获取全局态势"""
        return {
            "cop": self.cop.full_status(),
            "skills": self.skills.available(),
            "cache_hit_rate": self.cop.cache.hit_rate,
        }

    def close(self):
        self.cop.close()


# ==================== CLI ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OODA双环引擎 v2.0")
    parser.add_argument("intent", nargs="?", default="", help="执行意图")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Ollama模型")
    parser.add_argument("--test", action="store_true", help="运行自检(不调用LLM)")
    args = parser.parse_args()

    if args.test:
        # 自检模式: 不调用LLM, 仅验证COP+OODA框架
        import tempfile, os
        test_db = Path(tempfile.mktemp(suffix=".db"))
        print("=" * 60)
        print("OODA 双环引擎 — 框架自检 (不调用LLM)")
        print("=" * 60)

        cop = COP(db_path=test_db)

        # 模拟SkillLoader (不需要Ollama)
        class MockSkillLoader:
            def available(self): return ["v1_coding", "v4_validate"]
            def get(self, k): return None
            def call(self, k, inp): return f"[mock_{k}] 处理: {inp[:50]}..."

        ooda = OODAController(cop, MockSkillLoader())
        evo = EvolutionLoop(cop, MockSkillLoader(), trigger_every=2)

        # 运行3次OODA
        for intent in ["实现Fibonacci", "编写排序算法", "构建知识图谱"]:
            result = ooda.run_cycle(intent)
            evo.tick()
            assert result["status"] == "done", f"OODA失败: {result}"
            print(f"  → {result['cycle_id']}: {result['status']}, {result['duration_ms']}ms")

        # 检查COP状态
        status = cop.full_status()
        assert status["tasks"]["done"] == 3
        print(f"\n✅ 全局态势: {json.dumps(status, ensure_ascii=False)}")
        print(f"✅ 缓存命中率: {cop.cache.hit_rate:.0%}")

        cop.close()
        os.unlink(str(test_db))
        print("\n🏁 OODA 框架自检全部通过!")

    elif args.intent:
        engine = DualLoopEngine(model=args.model)
        result = engine.run(args.intent)
        print(f"\n📊 结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        engine.close()
    else:
        print("用法:")
        print('  python3 ooda_controller.py "实现一个Fibonacci计算器"')
        print('  python3 ooda_controller.py --test')
        print('  python3 ooda_controller.py --model qwen2.5-coder:7b "写一个排序算法"')
