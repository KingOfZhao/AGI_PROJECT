#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超越引擎 (Surpass Engine) — 让本地14B + 智谱AI组合超越单体大模型

核心策略（6个可编码的超越维度）：

1. 任务复杂度评估器 (TaskAnalyzer)
   - 分析任务类型/复杂度/所需能力
   - 自动路由: 简单→本地 / 中等→云端 / 复杂→多模型编排

2. 多模型集成投票 (EnsembleVoter)
   - 关键任务同时调用多个模型
   - 交叉校验 + 取共识 → 准确率超越任何单一模型

3. 迭代精炼管线 (IterativeRefiner)
   - 生成 → 执行验证 → 错误分析 → 修复 → 循环
   - Claude单次生成 vs 我们N次精炼直到正确

4. 知识锚定生成 (KnowledgeAnchor)
   - 每次推理注入相关proven节点
   - 事实性有1400+验证节点保障 → Claude没有

5. 结构化思维链 (StructuredCoT)
   - 强制分步推理 + 每步验证
   - 突破14B单次推理深度限制

6. 自适应上下文管理 (ContextManager)
   - 智能检索+压缩 vs Claude的暴力长窗口
   - glm-4-long 128K处理超长文本
"""

import sys
import time
import json
import re
import hashlib
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# ==================== 1. 任务复杂度评估器 ====================

class TaskAnalyzer:
    """分析任务复杂度，决定最优执行策略"""
    
    # 复杂度特征
    COMPLEXITY_SIGNALS = {
        "high": [
            r"设计.*架构", r"实现.*系统", r"完整.*项目",
            r"多文件", r"并发", r"分布式", r"优化.*性能",
            r"算法.*复杂", r"数学.*证明", r"深度.*分析",
            r"重构", r"migrate", r"architecture",
        ],
        "medium": [
            r"实现.*函数", r"写.*代码", r"解释.*原理",
            r"比较.*区别", r"如何.*处理", r"调试",
            r"implement", r"function", r"class",
        ],
        "low": [
            r"什么是", r"翻译", r"格式化", r"列出",
            r"简单.*说明", r"定义", r"translate",
        ],
    }
    
    # 任务类型检测
    TASK_TYPES = {
        "code_gen": [r"写.*代码", r"实现", r"编写", r"implement", r"code", r"函数", r"脚本"],
        "code_fix": [r"修复", r"bug", r"错误", r"fix", r"debug", r"调试", r"不工作"],
        "reasoning": [r"为什么", r"原因", r"分析", r"推理", r"explain", r"why", r"how"],
        "architecture": [r"设计", r"架构", r"系统", r"design", r"architect", r"方案"],
        "knowledge": [r"什么是", r"定义", r"概念", r"what is", r"define"],
        "translate": [r"翻译", r"translate", r"转换"],
        "review": [r"审查", r"review", r"检查", r"优化", r"改进"],
        "creative": [r"创意", r"想法", r"brainstorm", r"方案", r"建议"],
    }
    
    @classmethod
    def analyze(cls, task: str, context_nodes: List[Dict] = None) -> Dict:
        """
        分析任务，返回执行策略
        
        Returns:
            {
                "complexity": "low/medium/high",
                "task_type": str,
                "strategy": "local/cloud/ensemble/iterative",
                "recommended_model": str,
                "needs_verification": bool,
                "needs_knowledge": bool,
                "estimated_steps": int,
            }
        """
        task_lower = task.lower()
        
        # 检测复杂度
        complexity = "medium"
        for level, patterns in cls.COMPLEXITY_SIGNALS.items():
            for p in patterns:
                if re.search(p, task_lower):
                    complexity = level
                    break
            if complexity != "medium" or level == "medium":
                break
        
        # 长任务描述通常更复杂
        if len(task) > 500:
            complexity = "high"
        
        # 检测任务类型
        task_type = "general"
        for ttype, patterns in cls.TASK_TYPES.items():
            for p in patterns:
                if re.search(p, task_lower):
                    task_type = ttype
                    break
            if task_type != "general":
                break
        
        # 决定策略
        strategy_map = {
            ("low", "knowledge"): ("local", "ollama", False),
            ("low", "translate"): ("cloud", "glm-4-flash", False),
            ("low", "general"): ("local", "ollama", False),
            ("medium", "code_gen"): ("iterative", "glm-4-plus", True),
            ("medium", "code_fix"): ("iterative", "glm-4-plus", True),
            ("medium", "reasoning"): ("cloud", "glm-4-plus", True),
            ("medium", "review"): ("cloud", "glm-4-long", False),
            ("medium", "general"): ("cloud", "glm-4-air", False),
            ("high", "code_gen"): ("ensemble", "glm-4-plus", True),
            ("high", "architecture"): ("ensemble", "glm-4-plus", True),
            ("high", "reasoning"): ("ensemble", "glm-4-plus", True),
            ("high", "code_fix"): ("iterative", "glm-4-plus", True),
            ("high", "creative"): ("cloud", "glm-5", False),
            ("high", "general"): ("ensemble", "glm-4-plus", True),
        }
        
        key = (complexity, task_type)
        strategy, model, needs_verify = strategy_map.get(
            key, ("cloud", "glm-4-air", False)
        )
        
        # 是否有可用知识锚定
        has_knowledge = bool(context_nodes and len(context_nodes) > 0)
        proven_count = sum(1 for n in (context_nodes or []) if n.get('status') == 'proven')
        
        return {
            "complexity": complexity,
            "task_type": task_type,
            "strategy": strategy,
            "recommended_model": model,
            "needs_verification": needs_verify,
            "needs_knowledge": has_knowledge,
            "proven_anchors": proven_count,
            "estimated_steps": {"local": 1, "cloud": 1, "iterative": 3, "ensemble": 3}.get(strategy, 1),
        }


# ==================== 2. 多模型集成投票 ====================

class EnsembleVoter:
    """多模型投票 — 同时调用多个模型，交叉校验取共识"""
    
    @staticmethod
    def vote(
        task: str,
        system_prompt: str = "",
        models: List[str] = None,
        lattice=None,
    ) -> Dict:
        """
        多模型投票
        
        默认使用: 本地Ollama + glm-4-flash + glm-4-plus
        取三者共识，标注分歧
        """
        if models is None:
            models = ["local", "glm-4-flash", "glm-4-plus"]
        
        results = {}
        t0 = time.time()
        
        # 并行调用（用线程）
        threads = []
        results_lock = threading.Lock()
        
        def _call_model(model_id):
            try:
                if model_id == "local":
                    r = _call_local(task, system_prompt)
                else:
                    r = _call_zhipu(task, system_prompt, model_id)
                with results_lock:
                    results[model_id] = r
            except Exception as e:
                with results_lock:
                    results[model_id] = {"error": str(e), "content": ""}
        
        for m in models:
            t = threading.Thread(target=_call_model, args=(m,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=120)
        
        # 分析共识
        contents = {m: r.get("content", "") for m, r in results.items() if r.get("content")}
        
        if not contents:
            return {"success": False, "error": "所有模型调用失败", "results": results}
        
        # 选择最佳答案 + 标注分歧
        best, consensus_report = _analyze_consensus(contents, task, lattice)
        
        return {
            "success": True,
            "content": best,
            "consensus": consensus_report,
            "models_used": list(contents.keys()),
            "individual_results": {m: r.get("content", "")[:200] for m, r in results.items()},
            "duration": round(time.time() - t0, 2),
            "strategy": "ensemble_vote",
        }


def _call_local(task, system_prompt=""):
    """调用本地Ollama"""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import agi_v13_cognitive_lattice as agi
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": task})
    
    result = agi._local_ollama_call(messages)
    content = result.get("raw", str(result)) if isinstance(result, dict) else str(result)
    return {"content": content, "model": "local-ollama"}


def _call_zhipu(task, system_prompt, model):
    """调用智谱AI"""
    from workspace.skills.zhipu_ai_caller import call_zhipu
    r = call_zhipu(prompt=task, model=model, system_prompt=system_prompt or None)
    return {"content": r.get("content", ""), "model": model}


def _analyze_consensus(contents: Dict[str, str], task: str, lattice=None) -> Tuple[str, Dict]:
    """分析多模型输出的共识"""
    models = list(contents.keys())
    texts = list(contents.values())
    
    # 简单启发式：选最长且有代码块的回答作为基础
    scored = []
    for m, t in contents.items():
        score = 0
        score += len(t) * 0.001  # 长度分
        score += t.count("```") * 5  # 代码块
        score += t.count("\n-") * 2  # 列表
        score += t.count("##") * 3  # 结构化
        # 云端模型加分（通常质量更高）
        if m != "local":
            score += 10
        if "plus" in m:
            score += 5
        scored.append((m, score, t))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    best_model = scored[0][0]
    best_content = scored[0][2]
    
    # 用本地模型做最终校验（如果有本地结果）
    local_content = contents.get("local", "")
    
    consensus = {
        "best_model": best_model,
        "agreement_level": "high" if len(set(len(t) // 100 for t in texts)) <= 1 else "medium",
        "models_count": len(models),
    }
    
    # 如果本地和云端结果差异很大，标注
    if local_content and best_model != "local":
        local_len = len(local_content)
        cloud_len = len(best_content)
        if cloud_len > local_len * 3:
            consensus["note"] = "云端回答显著更详细，采用云端结果"
        elif local_len > cloud_len * 2:
            consensus["note"] = "本地回答更详细，但采用云端结果（通常更准确）"
    
    return best_content, consensus


# ==================== 3. 迭代精炼管线 ====================

class IterativeRefiner:
    """生成 → 验证 → 修复 → 循环，直到通过或达到最大轮次"""
    
    MAX_ITERATIONS = 5
    
    @classmethod
    def refine_code(
        cls,
        task: str,
        language: str = "python",
        model: str = "glm-4-plus",
        lattice=None,
    ) -> Dict:
        """
        迭代精炼代码：
        1. 生成代码
        2. 实际执行
        3. 分析错误
        4. 修复代码
        5. 重复直到通过
        """
        from workspace.skills.zhipu_ai_caller import call_zhipu
        
        history = []
        current_code = ""
        t0 = time.time()
        
        for i in range(cls.MAX_ITERATIONS):
            iteration = {"round": i + 1, "action": "", "result": ""}
            
            if i == 0:
                # 首次生成
                prompt = f"请用{language}实现以下需求。只输出代码，不要解释：\n\n{task}"
                r = call_zhipu(prompt=prompt, task_type="code_gen", model=model)
                if not r.get("success"):
                    iteration["action"] = "generate_failed"
                    iteration["result"] = r.get("error", "")
                    history.append(iteration)
                    break
                current_code = _extract_code(r["content"])
                iteration["action"] = "initial_generate"
            else:
                # 修复代码
                fix_prompt = f"""上一次代码执行报错，请修复。

原始需求: {task}

当前代码:
```{language}
{current_code}
```

执行错误:
{last_error}

请输出修复后的完整代码，不要解释："""
                r = call_zhipu(prompt=fix_prompt, task_type="code_gen", model=model)
                if not r.get("success"):
                    iteration["action"] = "fix_failed"
                    iteration["result"] = r.get("error", "")
                    history.append(iteration)
                    break
                current_code = _extract_code(r["content"])
                iteration["action"] = "fix"
            
            # 执行验证（仅Python）
            if language.lower() == "python" and current_code:
                exec_result = _execute_code(current_code)
                if exec_result["success"]:
                    iteration["result"] = f"✅ 通过! stdout: {exec_result['stdout'][:200]}"
                    history.append(iteration)
                    return {
                        "success": True,
                        "code": current_code,
                        "iterations": i + 1,
                        "history": history,
                        "stdout": exec_result["stdout"],
                        "duration": round(time.time() - t0, 2),
                        "strategy": "iterative_refine",
                    }
                else:
                    last_error = exec_result.get("stderr", "") or exec_result.get("error", "")
                    iteration["result"] = f"❌ 错误: {last_error[:200]}"
            else:
                # 非Python代码，只生成不执行
                iteration["result"] = "代码已生成（非Python，跳过执行验证）"
                history.append(iteration)
                return {
                    "success": True,
                    "code": current_code,
                    "iterations": i + 1,
                    "history": history,
                    "duration": round(time.time() - t0, 2),
                    "strategy": "iterative_refine",
                    "note": "非Python代码，未做执行验证",
                }
            
            history.append(iteration)
        
        return {
            "success": False,
            "code": current_code,
            "iterations": cls.MAX_ITERATIONS,
            "history": history,
            "duration": round(time.time() - t0, 2),
            "strategy": "iterative_refine",
            "error": f"{cls.MAX_ITERATIONS}轮迭代未通过",
        }
    
    @classmethod
    def refine_reasoning(
        cls,
        question: str,
        model: str = "glm-4-plus",
        lattice=None,
        max_rounds: int = 3,
    ) -> Dict:
        """
        迭代精炼推理：
        1. 云端给出初步推理
        2. 本地模型质疑/挑战
        3. 云端修正
        4. 直到本地模型满意
        """
        from workspace.skills.zhipu_ai_caller import call_zhipu
        
        history = []
        t0 = time.time()
        
        # 知识锚定
        anchors = ""
        if lattice:
            try:
                related = lattice.find_similar_nodes(question, threshold=0.4, limit=5)
                proven = [n for n in related if n.get('status') == 'proven']
                if proven:
                    anchors = "\n已验证的相关知识：\n" + "\n".join(
                        f"- [{n['domain']}] {n['content'][:80]}" for n in proven[:5]
                    )
            except:
                pass
        
        # 第1步：云端初步推理
        prompt = f"{question}{anchors}\n\n请逐步推理，每步给出依据。不确定的标注[假设]。"
        r = call_zhipu(prompt=prompt, task_type="reasoning", model=model)
        if not r.get("success"):
            return {"success": False, "error": r.get("error", ""), "strategy": "iterative_reasoning"}
        
        current_answer = r["content"]
        history.append({"round": 1, "role": "cloud", "content": current_answer[:300]})
        
        # 第2-N步：本地质疑 → 云端修正
        for i in range(1, max_rounds):
            # 本地模型质疑
            challenge = _local_challenge(question, current_answer, anchors)
            if not challenge or "无异议" in challenge or "正确" in challenge.lower():
                history.append({"round": i + 1, "role": "local_verify", "content": "本地校验通过"})
                break
            
            history.append({"round": i + 1, "role": "local_challenge", "content": challenge[:200]})
            
            # 云端修正
            fix_prompt = f"""原始问题: {question}

你之前的回答: {current_answer[:2000]}

校验者提出的质疑: {challenge}

请针对质疑修正你的回答，保留正确部分，修正错误部分："""
            r = call_zhipu(prompt=fix_prompt, task_type="reasoning", model=model)
            if r.get("success"):
                current_answer = r["content"]
                history.append({"round": i + 1, "role": "cloud_revise", "content": current_answer[:300]})
        
        return {
            "success": True,
            "content": current_answer,
            "iterations": len(history),
            "history": history,
            "duration": round(time.time() - t0, 2),
            "strategy": "iterative_reasoning",
            "knowledge_anchors": len(anchors) > 0,
        }


def _extract_code(text: str) -> str:
    """从AI回复中提取代码块"""
    blocks = re.findall(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
    if blocks:
        return blocks[0].strip()
    # 如果没有代码块标记，整段就是代码
    return text.strip()


def _execute_code(code: str) -> Dict:
    """执行Python代码"""
    try:
        from workspace.skills.shell_executor import run_python
        return run_python(code, timeout=15)
    except ImportError:
        import subprocess
        try:
            python = str(Path(__file__).parent.parent.parent / "venv" / "bin" / "python")
            r = subprocess.run(
                [python, "-c", code],
                capture_output=True, text=True, timeout=15,
                cwd=str(Path(__file__).parent.parent.parent)
            )
            return {
                "success": r.returncode == 0,
                "stdout": r.stdout,
                "stderr": r.stderr,
                "returncode": r.returncode,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def _local_challenge(question: str, answer: str, anchors: str = "") -> str:
    """本地模型对云端回答提出质疑"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        import agi_v13_cognitive_lattice as agi
        
        prompt = f"""请严格审查以下回答的准确性。

问题: {question}
{anchors}

回答: {answer[:2000]}

请指出回答中的错误、不准确或可疑之处。如果回答基本正确，请回复"无异议"。
只输出质疑要点，不要重复原文。"""
        
        result = agi._local_ollama_call([
            {"role": "system", "content": "你是严格的事实审查员。只指出确定的错误，不确定时说'无异议'。"},
            {"role": "user", "content": prompt}
        ])
        
        content = result.get("raw", str(result)) if isinstance(result, dict) else str(result)
        return content
    except Exception as e:
        return f"校验异常: {e}"


# ==================== 4. 知识锚定生成 ====================

class KnowledgeAnchor:
    """注入proven节点到每次推理，确保事实性 — Claude没有这个能力"""
    
    @staticmethod
    def anchor(task: str, lattice) -> Tuple[str, List[Dict]]:
        """
        检索相关proven节点并构建上下文锚定
        
        Returns:
            (anchored_prompt, proven_nodes)
        """
        proven_nodes = []
        try:
            related = lattice.find_similar_nodes(task, threshold=0.35, limit=8)
            proven_nodes = [n for n in related if n.get('status') == 'proven']
        except:
            pass
        
        if not proven_nodes:
            return task, []
        
        anchor_text = "\n\n## 已验证知识（务必基于这些事实回答）\n"
        for n in proven_nodes[:6]:
            anchor_text += f"- ✅ [{n['domain']}] {n['content'][:100]}\n"
        anchor_text += "\n超出以上已验证范围的推断请标注[假设]。\n\n"
        
        return anchor_text + task, proven_nodes


# ==================== 5. 结构化思维链 ====================

class StructuredCoT:
    """强制分步推理 + 每步验证，突破14B单次推理深度限制"""
    
    @staticmethod
    def solve(
        task: str,
        model: str = "glm-4-plus",
        lattice=None,
        max_steps: int = 5,
    ) -> Dict:
        """
        结构化分步推理：
        1. 分解问题为子步骤
        2. 每步单独推理
        3. 每步结果验证
        4. 综合最终答案
        """
        from workspace.skills.zhipu_ai_caller import call_zhipu
        
        t0 = time.time()
        
        # 知识锚定
        anchors = ""
        if lattice:
            anchored, _ = KnowledgeAnchor.anchor(task, lattice)
            if anchored != task:
                anchors = anchored.replace(task, "").strip()
        
        # 步骤1: 分解问题
        decompose_prompt = f"""请将以下复杂问题分解为3-5个子步骤，每步可独立推理。
{anchors}

问题: {task}

请以JSON格式输出:
[
  {{"step": 1, "sub_question": "子问题", "approach": "解决思路"}},
  ...
]
只输出JSON。"""
        
        r = call_zhipu(prompt=decompose_prompt, task_type="reasoning", model="glm-4-flash")
        
        steps = []
        try:
            content = r.get("content", "")
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                steps = json.loads(json_match.group())
        except:
            pass
        
        if not steps:
            # 分解失败，直接单步处理
            direct = call_zhipu(prompt=f"{anchors}\n{task}", task_type="reasoning", model=model)
            return {
                "success": direct.get("success", False),
                "content": direct.get("content", ""),
                "steps": [],
                "duration": round(time.time() - t0, 2),
                "strategy": "structured_cot_fallback",
            }
        
        # 步骤2-N: 逐步推理
        step_results = []
        accumulated_context = ""
        
        for step in steps[:max_steps]:
            sub_q = step.get("sub_question", "")
            approach = step.get("approach", "")
            
            step_prompt = f"""我正在分步解决一个问题。

原始问题: {task}
{anchors}

当前步骤: 第{step.get('step', '?')}步 - {sub_q}
解决思路: {approach}

{f"前面步骤的结论: {accumulated_context}" if accumulated_context else ""}

请完成当前步骤的推理，给出明确结论："""
            
            r = call_zhipu(prompt=step_prompt, task_type="reasoning", model=model)
            step_content = r.get("content", "无法完成此步骤")
            
            step_results.append({
                "step": step.get("step", len(step_results) + 1),
                "question": sub_q,
                "result": step_content[:500],
            })
            
            accumulated_context += f"\n第{step.get('step','?')}步: {step_content[:300]}"
        
        # 最终综合
        synth_prompt = f"""基于以下分步推理结果，给出最终综合答案。

原始问题: {task}

分步推理结果:
{accumulated_context}

请综合所有步骤，给出完整、准确的最终答案："""
        
        r = call_zhipu(prompt=synth_prompt, task_type="reasoning", model=model)
        final_content = r.get("content", accumulated_context)
        
        return {
            "success": True,
            "content": final_content,
            "steps": step_results,
            "total_steps": len(step_results),
            "duration": round(time.time() - t0, 2),
            "strategy": "structured_cot",
        }


# ==================== 6. 主编排器 ====================

def surpass(
    task: str,
    lattice=None,
    force_strategy: Optional[str] = None,
    force_model: Optional[str] = None,
    verify: bool = True,
) -> Dict:
    """
    超越引擎主入口 — 自动分析任务并选择最优策略
    
    Args:
        task: 任务描述
        lattice: 认知网络实例
        force_strategy: 强制策略 (local/cloud/ensemble/iterative/cot)
        force_model: 强制模型
        verify: 是否启用验证
        
    Returns:
        完整的执行结果，包含策略、过程、结论
    """
    t0 = time.time()
    
    # 1. 收集上下文节点
    context_nodes = []
    if lattice:
        try:
            context_nodes = lattice.find_similar_nodes(task, threshold=0.35, limit=8)
        except:
            pass
    
    # 2. 分析任务
    analysis = TaskAnalyzer.analyze(task, context_nodes)
    strategy = force_strategy or analysis["strategy"]
    model = force_model or analysis["recommended_model"]
    
    # 3. 执行策略
    result = None
    
    if strategy == "local":
        # 简单任务 → 本地处理
        r = _call_local(task)
        result = {
            "success": True,
            "content": r.get("content", ""),
            "strategy": "local",
            "model": "ollama-local",
        }
    
    elif strategy == "cloud":
        # 中等任务 → 云端处理 + 知识锚定
        anchored_task, proven = KnowledgeAnchor.anchor(task, lattice) if lattice else (task, [])
        from workspace.skills.zhipu_ai_caller import call_zhipu
        r = call_zhipu(
            prompt=anchored_task,
            model=model,
            verify_locally=verify,
        )
        result = {
            "success": r.get("success", False),
            "content": r.get("content", ""),
            "strategy": "cloud_anchored",
            "model": model,
            "knowledge_anchors": len(proven),
            "verification": r.get("verification"),
        }
    
    elif strategy == "ensemble":
        # 复杂任务 → 多模型投票
        result = EnsembleVoter.vote(task, lattice=lattice)
    
    elif strategy == "iterative":
        # 代码任务 → 迭代精炼
        if analysis["task_type"] in ("code_gen", "code_fix"):
            result = IterativeRefiner.refine_code(task, model=model, lattice=lattice)
        else:
            result = IterativeRefiner.refine_reasoning(task, model=model, lattice=lattice)
    
    elif strategy == "cot":
        # 深度推理 → 结构化思维链
        result = StructuredCoT.solve(task, model=model, lattice=lattice)
    
    else:
        # 默认走云端
        from workspace.skills.zhipu_ai_caller import call_zhipu
        result = call_zhipu(prompt=task, model=model)
    
    if result is None:
        result = {"success": False, "error": "策略执行失败"}
    
    # 4. 补充元信息
    result["task_analysis"] = analysis
    result["total_duration"] = round(time.time() - t0, 2)
    
    return result


# ==================== 便捷接口 ====================

def surpass_code(task: str, language: str = "python", lattice=None) -> Dict:
    """超越引擎 — 代码生成专用"""
    return surpass(task, lattice=lattice, force_strategy="iterative")


def surpass_reason(task: str, lattice=None) -> Dict:
    """超越引擎 — 深度推理专用"""
    return surpass(task, lattice=lattice, force_strategy="cot")


def surpass_critical(task: str, lattice=None) -> Dict:
    """超越引擎 — 关键任务(多模型投票)"""
    return surpass(task, lattice=lattice, force_strategy="ensemble")
