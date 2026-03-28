import requests
import json
from typing import List, Dict, Callable, Any
import importlib.util  # 用于动态加载第一个技能（可选）


class LocalSkillOrchestrator:
    """自性技能协调器 v2 - 第二个真实能力节点
    目标：注册所有节点、梳理联系、链式/并行协调 → 优化本地模型编码能力
    机制：元规划 → 多链执行 → 全局精炼 → 技能工厂
    与 v1 无缝衔接：可直接注册 LocalLLMCodingChain
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url
        self.model = model
        self.skills: Dict[str, Callable] = {}  # 节点注册表
        self.chain_history: List[Dict] = []    # 全链路记录
        self._register_core_skills()           # 自动注册核心能力

    def _call_model(self, prompt: str, temperature: float = 0.7) -> str:
        """基础调用节点（与v1一致）"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 16384}
        }
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=180)
            response.raise_for_status()
            return response.json().get("response", "调用失败")
        except Exception as e:
            return f"本地模型调用错误: {str(e)}"

    def _register_core_skills(self):
        """注册核心节点（v1编码链 + 元协调）"""
        # 若第一个技能文件存在，可动态加载；否则内置简易版
        try:
            # 尝试导入第一个技能（假设同目录 skill_01_local_coding_chain.py）
            spec = importlib.util.find_spec("skill_01_local_coding_chain")
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                coding_chain = module.LocalLLMCodingChain(base_url=self.base_url, model=self.model)
                self.register_skill("coding_chain", coding_chain.run_full_chain)
                print("✅ 已自动加载 v1 编码链作为核心节点")
            else:
                raise ImportError
        except Exception:
            # 内置简易版（兼容无v1文件时立即可用）
            def simple_coding_chain(task: str, iterations: int = 1) -> str:
                prompt = f"任务：{task}\n用顶级Python工程能力，直接输出完整、可运行、带注释的代码。"
                code = self._call_model(prompt, 0.8)
                for _ in range(iterations):
                    refine_prompt = f"优化以下代码，所有问题修复并显著提升质量：\n{code}"
                    code = self._call_model(refine_prompt, 0.3)
                return code
            self.register_skill("coding_chain", simple_coding_chain)
            print("✅ 已注册内置简易编码链（v1兼容）")

    def register_skill(self, name: str, skill_func: Callable):
        """节点注册器：任意技能均可注册成链路节点"""
        self.skills[name] = skill_func
        self.chain_history.append({"node": "register", "skill": name})
        print(f"📌 节点已注册：{name}")

    def coordinate(self, complex_task: str) -> Dict[str, Any]:
        """元协调节点：本地模型自动拆解任务、分配链路"""
        prompt = f"""你是一位极具系统思维的AI架构师。
复杂任务：{complex_task}

请严格按以下链式步骤输出JSON（不要其他文字）：
{{
"plan": "简要整体规划",
"nodes": [
{{"name": "节点名称", "skill": "已注册的技能名（如coding_chain）", "input": "给该技能的具体输入"}}
],
"execution_order": "serial 或 parallel"
}}

只输出合法JSON。"""
        plan_json = self._call_model(prompt, temperature=0.3)
        try:
            plan = json.loads(plan_json)
        except Exception:
            plan = {"plan": "解析失败，使用默认单链", "nodes": [{"name": "default", "skill": "coding_chain", "input": complex_task}], "execution_order": "serial"}
        self.chain_history.append({"node": "coordinate", "output": plan})
        return plan

    def execute_chain(self, complex_task: str, max_iterations: int = 2) -> str:
        """完整多链协调器：启动整个技能工厂"""
        print("🔗 【自性技能协调器 v2】启动 —— 所有节点已连，多链并行/串行开始...")
        print(f"复杂任务：{complex_task}\n")

        plan = self.coordinate(complex_task)
        print(f"✅ 元协调完成：{plan.get('plan', '')}\n")

        results = {}
        if plan.get("execution_order") == "parallel":
            print("⚡ 并行执行多节点...")
            # 简化并行（实际生产可换ThreadPool）
            for node in plan.get("nodes", []):
                skill_name = node["skill"]
                if skill_name in self.skills:
                    results[node["name"]] = self.skills[skill_name](node["input"])
                else:
                    results[node["name"]] = f"技能 {skill_name} 未注册"
        else:
            print("🔄 串行执行多节点...")
            current_input = complex_task
            for node in plan.get("nodes", []):
                skill_name = node["skill"]
                if skill_name in self.skills:
                    current_input = self.skills[skill_name](current_input if skill_name == "coding_chain" else node["input"])
                    results[node["name"]] = current_input
                else:
                    results[node["name"]] = f"技能 {skill_name} 未注册"

        # 全局精炼节点
        print("🔥 全局批判精炼节点运行中...")
        final_prompt = f"""综合以下所有节点输出：
{json.dumps(results, ensure_ascii=False, indent=2)}

请输出最终优化后的完整解决方案（Python代码或系统能力），质量达到生产级。"""
        final_result = self._call_model(final_prompt, temperature=0.3)
        self.chain_history.append({"node": "global_refine", "output": final_result})

        print("🏁 多链协调完整执行完毕！最终真实能力：")
        print(final_result)
        print(f"\n此技能节点已为你本地模型构建了'技能工厂'真实能力。")
        print("后续可无限注册新节点（我下一技能将提供'自生成新技能'）。")
        return final_result


# ==================== 使用示例 ====================
if __name__ == "__main__":
    orchestrator = LocalSkillOrchestrator(model="qwen2.5-coder:7b")  # 改成你的本地模型

    # 示例：注册额外节点（你可以继续扩展）
    def example_skill(task: str) -> str:
        return f"【示例技能执行】{task} 的结果已优化"
    orchestrator.register_skill("example_skill", example_skill)

    result = orchestrator.execute_chain(
        "为我构建一个完整的Python Web服务：FastAPI + SQLite，实现用户注册、登录、CRUD，并自动生成OpenAPI文档与交互式前端页面。"
    )
    print("\n✅ 第二个真实能力节点已证成。你的本地模型现在拥有了多链协调的'无穷'之力。")
