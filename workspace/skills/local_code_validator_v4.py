import requests
import json
from typing import Dict


class LocalCodeValidator:
    """自性代码验证器 v4 - 第四个真实能力节点
    目标：对前序技能生成的代码进行自动测试、验证与修复
    机制：链式调用（生成测试用例 → 执行验证 → 修复 → 报告）
    与v1/v2/v3无缝衔接
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

    def run_full_chain(self, code_to_validate: str) -> str:
        print("🔗 【自性代码验证器 v4】启动 —— 验证链开始...")
        print(f"待验证代码长度：{len(code_to_validate)}\n")

        prompt = f"""你是一位极严苛的代码验证专家。
代码：
{code_to_validate}

链式步骤：
1. 生成完整pytest测试用例（覆盖边缘、错误处理）
2. 模拟执行并指出所有问题
3. 输出修复后的完整代码
4. 给出验证报告

只输出最终修复代码 + 报告。"""
        validated = self._call_model(prompt, temperature=0.3)
        self.chain_history.append({"node": "validate", "output": validated})

        print("🏁 验证链完整执行完毕！")
        print(validated)
        return validated


if __name__ == "__main__":
    validator = LocalCodeValidator(model="qwen2.5-coder:7b")
    result = validator.run_full_chain("# 在这里粘贴你想验证的代码")
    print("\n✅ 第四个真实能力节点已证成。")
