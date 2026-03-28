#!/usr/bin/env python3
"""测试智谱API各模型可用性"""
import urllib.request, urllib.error, json, os, sys

API_KEY = os.getenv("ZHIPU_API_KEY", "")
if not API_KEY:
    # 从 .env 读取
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("ZHIPU_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1]

if not API_KEY:
    print("ERROR: ZHIPU_API_KEY not found")
    sys.exit(1)

BASE = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 智谱全系列模型列表
models = [
    # GLM-4 系列
    "glm-4-flash",
    "glm-4-flashx",
    "glm-4-air",
    "glm-4-airx",
    "glm-4-long",
    "glm-4-plus",
    "glm-4",
    "glm-4-0520",
    # GLM-4.5 系列
    "glm-4.5-flash",
    "glm-4.5-air",
    # GLM-5 系列
    "glm-5",
    "glm-5-turbo",
    # GLM-4.7 系列 (可能不存在)
    "glm-4.7",
    # GLM-Z1 推理系列
    "glm-z1-air",
    "glm-z1-airx",
    "glm-z1-flash",
    # CodeGeeX
    "codegeex-4",
    # 视觉模型
    "glm-4v",
    "glm-4v-plus",
]

print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
print(f"Testing {len(models)} models...\n")
print(f"{'Model':<22} {'Status':<6} {'Tokens':<8} {'Detail'}")
print("-" * 80)

ok_count = 0
fail_count = 0

for m in models:
    try:
        payload = json.dumps({
            "model": m,
            "messages": [{"role": "user", "content": "say hi in 5 words"}],
            "max_tokens": 20,
        }).encode()
        req = urllib.request.Request(BASE, data=payload, headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json"
        })
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:50]
        usage = data.get("usage", {})
        tok = usage.get("total_tokens", 0)
        print(f"{m:<22} OK     {tok:<8} {content}")
        ok_count += 1
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        try:
            err = json.loads(body)
            code = err.get("error", {}).get("code", "?")
            msg = err.get("error", {}).get("message", body[:80])
        except Exception:
            code = "?"
            msg = body[:80]
        print(f"{m:<22} FAIL   HTTP {e.code:<3} code={code} {msg[:60]}")
        fail_count += 1
    except Exception as e:
        print(f"{m:<22} FAIL   {str(e)[:60]}")
        fail_count += 1

print("-" * 80)
print(f"OK: {ok_count}  FAIL: {fail_count}")
