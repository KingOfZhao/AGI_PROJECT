#!/usr/bin/env python3
"""测试 Coding Plan Pro 专属端点 vs 通用端点"""
import urllib.request, urllib.error, json, os, sys

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
API_KEY = ""
if os.path.exists(env_path):
    for line in open(env_path):
        if line.startswith("ZHIPU_API_KEY="):
            API_KEY = line.strip().split("=", 1)[1]

if not API_KEY:
    API_KEY = os.getenv("ZHIPU_API_KEY", "")
if not API_KEY:
    print("ERROR: no API key")
    sys.exit(1)

CODING_URL = "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"
GENERIC_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

models = ["glm-5", "glm-5-turbo", "glm-4-flash"]

for label, url in [("CODING (Pro)", CODING_URL), ("GENERIC", GENERIC_URL)]:
    print(f"\n=== {label} ===")
    print(f"URL: {url}")
    for m in models:
        try:
            payload = json.dumps({
                "model": m,
                "messages": [{"role": "user", "content": "say hi in 3 words"}],
                "max_tokens": 20,
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": "Bearer " + API_KEY,
                "Content-Type": "application/json"
            })
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read())
            tok = data.get("usage", {}).get("total_tokens", 0)
            txt = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:50]
            print(f"  OK   {m:20s} tok={tok:4d}  {txt}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            print(f"  FAIL {m:20s} HTTP {e.code}  {body[:100]}")
        except Exception as e:
            print(f"  FAIL {m:20s} {str(e)[:80]}")
