#!/usr/bin/env python3
"""微信发送测试 - 调试消息是否能送达"""
import requests, json, os, struct, base64, sys

TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          '.wechat_bot_token.json')
with open(TOKEN_FILE) as f:
    token_data = json.load(f)
bot_token = token_data['bot_token']
base_url = token_data.get('base_url', 'https://ilinkai.weixin.qq.com')
print(f"Token: {bot_token[:20]}...")
print(f"Base URL: {base_url}")

def uin():
    r = os.urandom(4)
    v = struct.unpack('<I', r)[0]
    return base64.b64encode(str(v).encode()).decode()

def headers():
    return {
        'Content-Type': 'application/json',
        'AuthorizationType': 'ilink_bot_token',
        'X-WECHAT-UIN': uin(),
        'Authorization': f'Bearer {bot_token}'
    }

# Step 1: 长轮询等待消息
print("\n等待微信消息(请在微信发一条消息, 40s超时)...")
try:
    r = requests.post(
        f'{base_url}/ilink/bot/getupdates',
        json={'get_updates_buf': '', 'base_info': {'channel_version': '1.0.2'}},
        headers=headers(), timeout=40
    )
    data = r.json()
    ret = data.get('ret', -1)
    msgs = data.get('msgs', [])
    print(f"ret={ret} msgs_count={len(msgs)}")

    if not msgs:
        print("无新消息, 退出")
        sys.exit(0)

    msg = msgs[-1]
    from_user = msg.get('from_user_id', '')
    ctx = msg.get('context_token', '')
    text = ''
    for item in msg.get('item_list', []):
        if item.get('type') == 1:
            text = item.get('text_item', {}).get('text', '')
    print(f"收到: {from_user[:30]} -> {text}")
    print(f"context_token: {ctx[:60]}...")
    print(f"message_type: {msg.get('message_type')}")
    print(f"message_state: {msg.get('message_state')}")

    # Step 2: 发送回复
    payload = {
        'msg': {
            'to_user_id': from_user,
            'message_type': 2,
            'message_state': 2,
            'context_token': ctx,
            'item_list': [
                {'type': 1, 'text_item': {'text': 'AGI v13 连通性测试成功!'}}
            ]
        }
    }
    print("\n=== 发送回复 ===")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    sr = requests.post(
        f'{base_url}/ilink/bot/sendmessage',
        json=payload, headers=headers(), timeout=10
    )
    print(f"HTTP Status: {sr.status_code}")
    print(f"Response: {sr.text}")

except requests.exceptions.Timeout:
    print("超时(40s内没收到消息)")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
