#!/usr/bin/env python3
"""
wechat_notify.py — 通过 OpenClaw 向微信推送通知
================================================
用法:
    python3 scripts/wechat_notify.py "推演完成，发现3个阻塞问题"
    
    # 在代码中:
    from wechat_notify import notify
    notify("🦞 P1 予人玫瑰推演完成")
"""
import json
import subprocess
import sys
import logging
from pathlib import Path

log = logging.getLogger("wx_notify")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_FILE = Path.home() / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"
OPENCLAW_BIN = "/opt/homebrew/opt/node@22/bin/openclaw"


def _get_session_id() -> str:
    """从 OpenClaw session 文件获取微信 session ID"""
    try:
        data = json.loads(SESSION_FILE.read_text())
        for key, sess in data.items():
            if sess.get("lastChannel") == "openclaw-weixin":
                return sess["sessionId"]
    except Exception:
        pass
    return ""


def notify(message: str, max_len: int = 500) -> bool:
    """
    发送微信通知。
    通过 openclaw agent --deliver 发送，会经过 AI 处理后推送。
    为了让 AI 直接转发而不过度加工，在消息前加转发指令。
    """
    sid = _get_session_id()
    if not sid:
        log.warning("未找到微信 session，通知未发送")
        return False

    # 截断过长消息
    if len(message) > max_len:
        message = message[:max_len] + "…(已截断)"

    # 包装为转发指令，减少 AI 加工
    wrapped = (
        f"[系统通知-请直接转发原文不要分析]\n{message}"
    )

    try:
        import os as _os
        env = _os.environ.copy()
        env["PATH"] = "/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:" + env.get("PATH", "")
        result = subprocess.run(
            ["/opt/homebrew/bin/openclaw", "agent", "-m", wrapped,
             "--session-id", sid, "--deliver"],
            capture_output=True, text=True, timeout=180, env=env,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            log.info(f"✅ 微信通知已发送: {message[:50]}")
            return True
        else:
            log.warning(f"微信通知失败: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        log.warning("微信通知超时")
        return False
    except Exception as e:
        log.warning(f"微信通知异常: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "🦞 龙虾推演通知测试"
    ok = notify(msg)
    print(f"发送{'成功' if ok else '失败'}")
