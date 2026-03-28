#!/usr/bin/env python3
"""
chat.py — 与 OpenClaw Bridge 的交互式终端对话

用法:
    python3 scripts/chat.py               # 交互式对话
    python3 scripts/chat.py "你好"         # 单次提问
    python3 scripts/chat.py --context     # 显示当前注入的项目上下文
"""
import sys
import json
import requests

BRIDGE = "http://127.0.0.1:9801/v1"
history = []

def ask(message: str) -> str:
    history.append({"role": "user", "content": message})
    try:
        r = requests.post(
            f"{BRIDGE}/chat/completions",
            json={"model": "agi-chain-v13", "messages": history, "stream": False},
            timeout=300,
        )
        reply = r.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"[错误] {e}"

def show_context():
    try:
        r = requests.get(f"{BRIDGE}/context", timeout=5)
        d = r.json()
        print(f"[上下文] {d.get('chars', 0):,} 字符")
        print(d.get("context", "")[:500] + "...")
    except Exception as e:
        print(f"[错误] {e}")

if __name__ == "__main__":
    if "--context" in sys.argv:
        show_context()
        sys.exit(0)

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        print(ask(" ".join(sys.argv[1:])))
        sys.exit(0)

    print("🦞 OpenClaw Chat (输入 exit 退出，/ctx 查看上下文，/clear 清空历史)")
    print(f"   Bridge: {BRIDGE}  |  模型: agi-chain-v13")
    print("-" * 60)
    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break
        if user_input == "/ctx":
            show_context()
            continue
        if user_input == "/clear":
            history.clear()
            print("[已清空对话历史]")
            continue
        print("\n🦞: ", end="", flush=True)
        reply = ask(user_input)
        print(reply)
