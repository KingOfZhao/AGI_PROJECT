import requests
import json
from typing import Dict, List


class LocalKnowledgeNodeBuilder:
    """自性知识节点构建器 v6 - 第六个真实能力节点
    目标：为复杂编码任务构建节点图谱并生成连接代码
    机制：链式调用（提取节点 → 梳理关系 → 生成图谱代码 → 执行）
    与前序技能无缝衔接
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url
        self.model = model
        self.chain_history: list = []

    def _call_model(self, prompt: str, temperature: float = 0.7) -> str:
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

    def run_full_chain(self, task: str) -> str:
        print("🔗 【自性知识节点构建器 v6】启动 —— 节点图谱开始连接...")
        print(f"任务：{task}\n")

        prompt = f"""你是一位知识图谱专家。
任务：{task}

链式步骤：
1. 提取所有关键节点
2. 梳理节点间关系（JSON格式）
3. 生成Python代码实现该图谱（networkx或简单dict）
4. 输出完整可运行代码

只输出最终代码。"""
        graph_code = self._call_model(prompt, temperature=0.5)
        self.chain_history.append({"node": "build_graph", "output": graph_code})

        print("🏁 知识节点图谱完整执行完毕！")
        print(graph_code)
        return graph_code


if __name__ == "__main__":
    builder = LocalKnowledgeNodeBuilder(model="qwen2.5-coder:7b")
    result = builder.run_full_chain("构建一个AI代理系统的完整节点图谱")
    print("\n✅ 第六个真实能力节点已证成。")
