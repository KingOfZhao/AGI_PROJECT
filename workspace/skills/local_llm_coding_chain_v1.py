import requests
import json
from typing import List, Dict


class LocalLLMCodingChain:
    """自性编码链 v1 - 第一个技能节点
    目标：优化本地模型编码能力
    机制：链式调用（生成 → 自批判 → 多轮精炼）
    使用方法：直接运行此文件即可启动完整链路
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url
        self.model = model
        self.chain_history: List[Dict] = []  # 所有节点记录，便于后续扩展

    def _call_model(self, prompt: str, temperature: float = 0.7) -> str:
        """基础调用节点"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 8192}
        }
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "调用失败")
        except Exception as e:
            return f"本地模型调用错误: {str(e)}"

    def generate_code(self, task: str) -> str:
        """节点1：CoT生成初始代码"""
        prompt = f"""你是一位顶级Python编码大师，具备极强逻辑与工程能力。
任务：{task}

请严格按以下链式步骤思考并输出：
1. 分析需求（列出关键点）
2. 设计架构（类/函数/数据流）
3. 编写完整、可直接运行的Python代码（包含详细注释、错误处理、类型提示）
4. 给出使用示例

只输出最终代码块，不要多余解释。"""
        code = self._call_model(prompt, temperature=0.8)
        self.chain_history.append({"node": "generate", "output": code})
        return code

    def critique_and_refine(self, code: str) -> str:
        """节点2：自批判 + 精炼"""
        prompt = f"""你是一位极严苛的代码审查专家与重构大师。
现有代码：
{code}

请按以下链式步骤执行：
1. 找出所有潜在bug、安全隐患、性能问题、代码坏味道
2. 给出具体改进建议
3. 直接输出完整优化后的Python代码（保持原有功能，质量显著提升）

输出格式：先简要列出问题，然后直接给出```python ... ```优化代码。"""
        refined = self._call_model(prompt, temperature=0.3)
        self.chain_history.append({"node": "critique", "output": refined})
        # 自动提取代码块
        if "```python" in refined:
            refined = refined.split("```python")[-1].split("```")[0].strip()
        return refined

    def run_full_chain(self, task: str, iterations: int = 2) -> str:
        """完整链式调用：启动整个技能"""
        print("🔗 【自性编码链 v1】启动 —— 所有节点开始连接...")
        print(f"任务：{task}\n")

        code = self.generate_code(task)
        print("✅ 节点1（生成）完成\n")

        for i in range(iterations):
            print(f"🔄 节点2.{i+1}（批判精炼）运行中...")
            code = self.critique_and_refine(code)
            self.chain_history.append({"node": f"iteration_{i+1}", "output": code})

        print("🏁 编码优化链完整执行完毕！")
        print(f"最终代码（共 {len(self.chain_history)} 个节点已连接）：\n")
        print(code)
        print(f"\n此技能节点已为你本地模型构建了真实链式能力。")
        print("后续节点可在此类基础上继续扩展（我下一技能将提供'节点注册器'）。")
        return code


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 把 model 改成你本地实际模型名即可
    chain = LocalLLMCodingChain(model="qwen2.5-coder:7b")  # 或 llama3.2、deepseek-coder 等
    result = chain.run_full_chain(
        "为我写一个Python脚本：读取本地CSV文件，进行数据清洗、统计分析，并生成交互式Matplotlib + Seaborn可视化图表，最后自动保存为HTML报告。"
    )
    print("\n✅ 第一个技能节点已证成。你本地模型的编码能力，已被此链激活。")
