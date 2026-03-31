#!/usr/bin/env python3
"""
本地调用链 — 概念存档（已停用本地模型调用）

本地模型（Ollama/qwen2.5-coder）已停用。
请直接使用 GLM-5.1 (glm51) 完成所有编码和推理任务。
"""
import sys
import json


def invoke(question: str, context: str = "") -> dict:
    """本地链已停用，返回重定向提示"""
    return {
        "answer": "本地链已停用。请直接使用 GLM-5.1 处理此任务。",
        "route": "disabled",
        "duration": 0.0,
        "steps": [],
        "risks": [],
        "hallucination_check": None,
        "redirect": "glm51/glm-5.1",
    }


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else ""
    context = sys.argv[2] if len(sys.argv) > 2 else ""
    print(json.dumps(invoke(question, context), ensure_ascii=False, indent=2))
