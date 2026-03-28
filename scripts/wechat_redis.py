#!/usr/bin/env python3
"""
微信对话记录 Redis 存储模块
- 每条消息存入 Redis List，key = wechat:chat:{gateway_id}:{user_id}
- 所有 user_id 存入 Redis Set，key = wechat:users:{gateway_id}
- TTL: 3天 (259200秒)
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

import redis

log = logging.getLogger("wechat_redis")

# Redis 配置
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
CHAT_TTL = 259200  # 3天 = 3 * 24 * 3600

_pool: Optional[redis.ConnectionPool] = None


def _get_conn() -> redis.Redis:
    """获取 Redis 连接(连接池复用)"""
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=True, max_connections=10
        )
    return redis.Redis(connection_pool=_pool)


def _chat_key(gateway_id: str, user_id: str) -> str:
    return f"wechat:chat:{gateway_id}:{user_id}"


def _users_key(gateway_id: str) -> str:
    return f"wechat:users:{gateway_id}"


def save_message(gateway_id: str, user_id: str, direction: str, text: str,
                 user_name: str = ""):
    """
    保存一条消息到 Redis
    direction: "in" (用户发送) 或 "out" (机器人回复)
    """
    try:
        r = _get_conn()
        entry = {
            "t": datetime.now().isoformat(),
            "d": direction,
            "text": text[:2000],
        }
        if user_name:
            entry["name"] = user_name

        chat_key = _chat_key(gateway_id, user_id)
        users_key = _users_key(gateway_id)

        pipe = r.pipeline()
        pipe.rpush(chat_key, json.dumps(entry, ensure_ascii=False))
        pipe.expire(chat_key, CHAT_TTL)
        pipe.sadd(users_key, user_id)
        pipe.expire(users_key, CHAT_TTL)
        pipe.execute()
    except Exception as e:
        log.warning(f"Redis 写入失败: {e}")


def get_chat_users(gateway_id: str) -> List[str]:
    """获取某网关的所有对话用户列表"""
    try:
        r = _get_conn()
        return list(r.smembers(_users_key(gateway_id)))
    except Exception as e:
        log.warning(f"Redis 读取失败: {e}")
        return []


def get_chat_history(gateway_id: str, user_id: str,
                     offset: int = 0, limit: int = 50) -> List[Dict]:
    """
    获取某用户的对话记录
    返回最新的 limit 条，offset 从最新往前偏移
    """
    try:
        r = _get_conn()
        chat_key = _chat_key(gateway_id, user_id)
        total = r.llen(chat_key)
        if total == 0:
            return []

        # 从尾部取(最新的在后面)
        start = max(0, total - offset - limit)
        end = total - offset - 1
        if end < 0:
            return []

        raw = r.lrange(chat_key, start, end)
        messages = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except Exception:
                pass
        return messages
    except Exception as e:
        log.warning(f"Redis 读取失败: {e}")
        return []


def get_all_chats(gateway_id: str, limit_per_user: int = 30) -> List[Dict]:
    """
    获取某网关所有对话(按用户分组)
    返回: [{user_id, messages: [...], last_time}]
    """
    users = get_chat_users(gateway_id)
    result = []
    for uid in users:
        msgs = get_chat_history(gateway_id, uid, limit=limit_per_user)
        if msgs:
            result.append({
                "user_id": uid,
                "messages": msgs,
                "count": len(msgs),
                "last_time": msgs[-1].get("t", "") if msgs else "",
            })
    # 按最后消息时间排序(最新的在前)
    result.sort(key=lambda x: x.get("last_time", ""), reverse=True)
    return result


def get_chat_stats(gateway_id: str) -> Dict:
    """获取网关对话统计"""
    try:
        r = _get_conn()
        users = get_chat_users(gateway_id)
        total_msgs = 0
        for uid in users:
            total_msgs += r.llen(_chat_key(gateway_id, uid))
        return {"users": len(users), "messages": total_msgs}
    except Exception as e:
        return {"users": 0, "messages": 0, "error": str(e)}
