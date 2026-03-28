#!/usr/bin/env python3
"""
微信网关管理 API 服务器
为 CRM 系统提供网关管理接口: 创建/启动/停止/状态/二维码/名称管理

启动: python3 scripts/wechat_manager.py
端口: 8890 (API) + 8888 (CRM静态文件)
"""

import os, sys, json, time, base64, struct, signal, threading, subprocess
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict

import requests

# ── 路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 日志 ──
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger("wechat_mgr")

# ── 配置 ──
ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
GATEWAYS_FILE = PROJECT_ROOT / "data" / "wechat_gateways.json"
GATEWAYS_FILE.parent.mkdir(parents=True, exist_ok=True)
API_PORT = 8890

AGI_API_BASE = os.getenv("AGI_API_BASE", "http://localhost:5002")


# ════════════════════════════════════════════════════════════
# iLink 协议工具函数
# ════════════════════════════════════════════════════════════

def _random_uin() -> str:
    rand_bytes = os.urandom(4)
    uint32_val = struct.unpack('<I', rand_bytes)[0]
    return base64.b64encode(str(uint32_val).encode()).decode()

def _headers(bot_token: Optional[str] = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_uin(),
    }
    if bot_token:
        h["Authorization"] = f"Bearer {bot_token}"
    return h


# ════════════════════════════════════════════════════════════
# 网关实例管理
# ════════════════════════════════════════════════════════════

class GatewayInstance:
    """单个网关实例"""
    def __init__(self, gw_id: str, name: str):
        self.id = gw_id
        self.name = name
        self.status = "stopped"       # stopped / qrcode / running / error
        self.bot_token: Optional[str] = None
        self.base_url: str = ILINK_BASE_URL
        self.qrcode_url: Optional[str] = None
        self.qrcode_id: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self.created_at = datetime.now().isoformat()
        self.last_active: Optional[str] = None
        self.message_count = 0
        self.error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "has_token": bool(self.bot_token),
            "qrcode_url": self.qrcode_url,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "message_count": self.message_count,
            "error_msg": self.error_msg,
        }


class GatewayManager:
    """管理多个网关实例"""

    def __init__(self):
        self.gateways: Dict[str, GatewayInstance] = {}
        self._lock = threading.Lock()
        self._poll_threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}
        self._load()

    def _load(self):
        """从文件加载网关配置"""
        if GATEWAYS_FILE.exists():
            try:
                data = json.loads(GATEWAYS_FILE.read_text())
                for gw_data in data.get("gateways", []):
                    gw = GatewayInstance(gw_data["id"], gw_data["name"])
                    gw.created_at = gw_data.get("created_at", gw.created_at)
                    gw.bot_token = gw_data.get("bot_token")
                    gw.base_url = gw_data.get("base_url", ILINK_BASE_URL)
                    gw.message_count = gw_data.get("message_count", 0)
                    gw.last_active = gw_data.get("last_active")
                    gw.status = "stopped"
                    self.gateways[gw.id] = gw
                log.info(f"已加载 {len(self.gateways)} 个网关配置")
            except Exception as e:
                log.warning(f"加载网关配置失败: {e}")

    def _save(self):
        """保存网关配置到文件"""
        data = {"gateways": [], "saved_at": datetime.now().isoformat()}
        for gw in self.gateways.values():
            data["gateways"].append({
                "id": gw.id,
                "name": gw.name,
                "bot_token": gw.bot_token,
                "base_url": gw.base_url,
                "created_at": gw.created_at,
                "message_count": gw.message_count,
                "last_active": gw.last_active,
            })
        GATEWAYS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def create_gateway(self, name: str) -> GatewayInstance:
        """创建新网关"""
        gw_id = f"gw_{int(time.time())}_{os.urandom(2).hex()}"
        gw = GatewayInstance(gw_id, name)
        with self._lock:
            self.gateways[gw_id] = gw
            self._save()
        log.info(f"创建网关: {gw_id} ({name})")
        return gw

    def delete_gateway(self, gw_id: str) -> bool:
        """删除网关"""
        if gw_id in self.gateways:
            self.stop_gateway(gw_id)
            with self._lock:
                del self.gateways[gw_id]
                self._save()
            log.info(f"删除网关: {gw_id}")
            return True
        return False

    def rename_gateway(self, gw_id: str, new_name: str) -> bool:
        """重命名网关"""
        if gw_id in self.gateways:
            self.gateways[gw_id].name = new_name
            with self._lock:
                self._save()
            return True
        return False

    def get_qrcode(self, gw_id: str) -> dict:
        """为网关获取登录二维码"""
        gw = self.gateways.get(gw_id)
        if not gw:
            return {"error": "网关不存在"}

        try:
            url = f"{ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
            resp = requests.get(url, headers=_headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()

            gw.qrcode_id = data.get("qrcode", "")
            gw.qrcode_url = data.get("qrcode_img_content", "")
            gw.status = "qrcode"
            gw.error_msg = None

            # 启动后台轮询扫码状态
            self._start_qrcode_poll(gw_id)

            return {"qrcode_url": gw.qrcode_url, "qrcode_id": gw.qrcode_id}
        except Exception as e:
            gw.error_msg = str(e)
            gw.status = "error"
            return {"error": str(e)}

    def _start_qrcode_poll(self, gw_id: str):
        """后台线程轮询扫码状态"""
        def poll():
            gw = self.gateways.get(gw_id)
            if not gw or not gw.qrcode_id:
                return
            max_wait = 120
            start = time.time()
            while time.time() - start < max_wait:
                try:
                    url = f"{ILINK_BASE_URL}/ilink/bot/get_qrcode_status?qrcode={gw.qrcode_id}"
                    resp = requests.get(url, headers=_headers(), timeout=40)
                    data = resp.json()
                    s = data.get("status", data.get("state", ""))

                    if s == "confirmed":
                        gw.bot_token = data.get("bot_token", "")
                        new_base = data.get("baseurl", "")
                        if new_base:
                            gw.base_url = new_base
                        gw.status = "stopped"  # 有token但还没启动消息循环
                        gw.error_msg = None
                        with self._lock:
                            self._save()
                        log.info(f"网关 {gw_id} ({gw.name}) 扫码成功!")
                        return
                    elif s == "scanned":
                        log.info(f"网关 {gw_id} 已扫码，等待确认...")
                    elif s == "expired":
                        gw.status = "error"
                        gw.error_msg = "二维码已过期"
                        return
                except requests.exceptions.Timeout:
                    continue
                except Exception as e:
                    log.warning(f"轮询异常: {e}")
                time.sleep(2)

            gw.status = "error"
            gw.error_msg = "扫码超时(2分钟)"

        t = threading.Thread(target=poll, daemon=True, name=f"qr_poll_{gw_id}")
        t.start()

    def start_gateway(self, gw_id: str) -> dict:
        """启动网关消息循环"""
        gw = self.gateways.get(gw_id)
        if not gw:
            return {"error": "网关不存在"}
        if not gw.bot_token:
            return {"error": "未登录，请先扫码"}
        if gw.status == "running":
            return {"error": "网关已在运行"}

        # 启动消息循环线程
        stop_flag = threading.Event()
        self._stop_flags[gw_id] = stop_flag

        def message_loop():
            cursor = ""
            gw.status = "running"
            gw.error_msg = None
            consecutive_errors = 0
            empty_polls = 0
            log.info(f"网关 {gw_id} ({gw.name}) 消息循环启动")

            # 延迟导入handler
            from wechat_gateway import AGIMessageHandler, ILinkClient, TokenExpiredError
            handler = AGIMessageHandler()
            client = ILinkClient()
            client.bot_token = gw.bot_token
            client.base_url = gw.base_url

            def _process_msg(from_user, text, context_token):
                """在后台线程处理消息,不阻塞轮询循环"""
                try:
                    gw.message_count += 1
                    gw.last_active = datetime.now().isoformat()
                    log.info(f"[{gw.name}] 开始处理: {text[:60]}")

                    # 保存用户消息到 Redis
                    try:
                        from wechat_redis import save_message
                        save_message(gw_id, from_user, 'in', text)
                    except Exception:
                        pass

                    try:
                        client.send_typing(from_user, context_token)
                    except TokenExpiredError:
                        raise
                    except Exception as te:
                        log.warning(f"[{gw.name}] send_typing失败: {te}")

                    if handler.is_command(text):
                        reply = handler.handle(from_user, text)
                        if reply:
                            log.info(f"[{gw.name}] 命令回复({len(reply)}字): {reply[:60]}")
                            client.send_message(from_user, reply, context_token)
                            try:
                                from wechat_redis import save_message as _sm
                                _sm(gw_id, from_user, 'out', reply)
                            except Exception:
                                pass
                    else:
                        def make_send(u, c, gid):
                            def _s(part):
                                log.info(f"[{gw.name}] 发送片段({len(part)}字): {part[:60]}")
                                client.send_message(u, part, c)
                                try:
                                    from wechat_redis import save_message as _sm2
                                    _sm2(gid, u, 'out', part)
                                except Exception:
                                    pass
                            return _s
                        reply = handler.handle_streaming(
                            from_user, text,
                            make_send(from_user, context_token, gw_id)
                        )
                        log.info(f"[{gw.name}] 处理完成({len(reply) if reply else 0}字)")
                except TokenExpiredError as te:
                    log.warning(f"[{gw.name}] 发送时Token失效: {te}")
                    stop_flag.set()  # 通知轮询循环退出
                except Exception as e:
                    import traceback
                    log.warning(f"[{gw.name}] 消息处理异常: {e}\n{traceback.format_exc()}")

            poll_count = 0
            while not stop_flag.is_set():
                try:
                    result = client.get_updates(cursor)
                    poll_count += 1
                    ret_code = result.get("ret", 0)

                    # 心跳日志: 每5次轮询输出一次
                    if poll_count % 5 == 1:
                        log.info(f"[{gw.name}] 轮询#{poll_count} ret={ret_code} cursor={cursor[:20] if cursor else 'empty'}...")

                    # 检查返回码
                    if ret_code == -1:
                        raise TokenExpiredError("bot_token 已失效")
                    if ret_code != 0:
                        log.warning(f"[{gw.name}] get_updates ret={ret_code}: {json.dumps(result, ensure_ascii=False)[:200]}")

                    new_cursor = result.get("get_updates_buf", "")
                    if new_cursor:
                        cursor = new_cursor

                    msgs = result.get("msgs", [])
                    if msgs:
                        empty_polls = 0
                        log.info(f"[{gw.name}] 收到 {len(msgs)} 条消息")
                    else:
                        empty_polls += 1

                    for msg in msgs:
                        if msg.get("message_type") != 1:
                            continue
                        from_user = msg.get("from_user_id", "")
                        context_token = msg.get("context_token", "")
                        for item in msg.get("item_list", []):
                            if item.get("type") == 1:
                                text = item.get("text_item", {}).get("text", "")
                                if not text:
                                    continue
                                log.info(f"[{gw.name}] 📩 {text[:60]}")
                                # 在后台线程处理,避免阻塞轮询
                                t = threading.Thread(
                                    target=_process_msg,
                                    args=(from_user, text, context_token),
                                    daemon=True
                                )
                                t.start()

                    consecutive_errors = 0

                    # 每50次空轮询刷新session防止连接腐烂
                    if empty_polls > 0 and empty_polls % 50 == 0:
                        client.session.close()
                        client.session = requests.Session()
                        client.session.timeout = 40
                        log.info(f"[{gw.name}] Session已刷新 (空轮询{empty_polls}次)")

                except TokenExpiredError as te:
                    log.warning(f"[{gw.name}] Token 失效: {te}")
                    # 自动触发重新登录
                    gw.status = "relogin"
                    gw.error_msg = "Session过期,正在重新获取二维码..."
                    gw.bot_token = None
                    with self._lock:
                        self._save()
                    log.info(f"[{gw.name}] 自动重新获取登录二维码...")
                    try:
                        qr_result = self.get_qrcode(gw_id)
                        if "error" not in qr_result:
                            log.info(f"[{gw.name}] 新二维码已生成,请到 http://localhost:8890 扫码")
                            gw.error_msg = "请到管理页面重新扫码"
                        else:
                            log.warning(f"[{gw.name}] 获取二维码失败: {qr_result}")
                            gw.error_msg = f"重新登录失败: {qr_result.get('error','')}"
                    except Exception as qe:
                        log.warning(f"[{gw.name}] 自动重登失败: {qe}")
                        gw.error_msg = f"Token失效且重登失败: {qe}"
                    break
                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.ConnectionError as e:
                    consecutive_errors += 1
                    log.warning(f"[{gw.name}] 连接错误({consecutive_errors}): {e}")
                    # 刷新session重连
                    client.session.close()
                    client.session = requests.Session()
                    client.session.timeout = 40
                    if consecutive_errors >= 10:
                        gw.status = "error"
                        gw.error_msg = f"连续{consecutive_errors}次连接失败"
                        break
                    time.sleep(min(consecutive_errors * 2, 30))
                except Exception as e:
                    if stop_flag.is_set():
                        break
                    consecutive_errors += 1
                    import traceback
                    log.warning(f"[{gw.name}] 异常({consecutive_errors}): {e}\n{traceback.format_exc()}")
                    if consecutive_errors >= 10:
                        gw.status = "error"
                        gw.error_msg = f"连续异常: {str(e)[:80]}"
                        break
                    time.sleep(min(consecutive_errors * 2, 30))

            gw.status = "stopped" if not gw.error_msg else gw.status
            log.info(f"网关 {gw_id} ({gw.name}) 已停止")

        t = threading.Thread(target=message_loop, daemon=True, name=f"gw_{gw_id}")
        self._poll_threads[gw_id] = t
        t.start()
        return {"status": "started"}

    def stop_gateway(self, gw_id: str) -> dict:
        """停止网关"""
        gw = self.gateways.get(gw_id)
        if not gw:
            return {"error": "网关不存在"}

        flag = self._stop_flags.get(gw_id)
        if flag:
            flag.set()
            del self._stop_flags[gw_id]

        gw.status = "stopped"
        with self._lock:
            self._save()
        log.info(f"网关 {gw_id} ({gw.name}) 停止")
        return {"status": "stopped"}

    def list_gateways(self) -> list:
        """列出所有网关"""
        return [gw.to_dict() for gw in self.gateways.values()]


# ════════════════════════════════════════════════════════════
# HTTP API 服务器
# ════════════════════════════════════════════════════════════

manager = GatewayManager()

class APIHandler(SimpleHTTPRequestHandler):
    """API + 静态文件服务"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT / "web"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/api/chat_history",):
            return self._proxy_to_agi(method="GET")

        if path == "/api/gateways":
            self._json_response(manager.list_gateways())
        elif path.startswith("/api/gateways/") and path.endswith("/qrcode"):
            gw_id = path.split("/")[3]
            result = manager.get_qrcode(gw_id)
            self._json_response(result)
        elif path.startswith("/api/gateways/") and "/chats/" in path:
            # GET /api/gateways/{id}/chats/{user_id} — 单用户对话记录
            parts = path.split("/")
            gw_id = parts[3]
            user_id = "/".join(parts[5:])  # user_id 可能含特殊字符
            from urllib.parse import unquote
            user_id = unquote(user_id)
            from wechat_redis import get_chat_history
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["50"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            msgs = get_chat_history(gw_id, user_id, offset=offset, limit=limit)
            self._json_response(msgs)
        elif path.startswith("/api/gateways/") and path.endswith("/chats"):
            # GET /api/gateways/{id}/chats — 所有对话概览
            gw_id = path.split("/")[3]
            from wechat_redis import get_all_chats, get_chat_stats
            qs = parse_qs(parsed.query)
            if qs.get("stats"):
                self._json_response(get_chat_stats(gw_id))
            else:
                limit = int(qs.get("limit", ["30"])[0])
                chats = get_all_chats(gw_id, limit_per_user=limit)
                self._json_response(chats)
        elif path == "/api/gateways/health":
            self._json_response({"status": "ok", "count": len(manager.gateways)})
        elif path == "/api/problems":
            qs = parse_qs(parsed.query)
            pid = qs.get('project_id', [None])[0]
            status = qs.get('status', [None])[0]
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from deduction_db import DeductionDB
                db = DeductionDB()
                problems = db.get_problems(project_id=pid, status=status)
                db.close()
                self._json_response(problems)
            except Exception as e:
                self._json_response({'error': str(e)}, 500)
        elif path == "/api/projects":
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from deduction_db import DeductionDB
                db = DeductionDB()
                projects = db.get_projects()
                db.close()
                self._json_response(projects)
            except Exception as e:
                self._json_response({'error': str(e)}, 500)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/api/chat", "/api/chat/stop"):
            return self._proxy_to_agi(method="POST")

        body = self._read_body()

        if path == "/api/gateways":
            name = body.get("name", f"网关_{int(time.time()) % 10000}")
            gw = manager.create_gateway(name)
            self._json_response(gw.to_dict(), 201)

        elif path.startswith("/api/gateways/") and path.endswith("/start"):
            gw_id = path.split("/")[3]
            result = manager.start_gateway(gw_id)
            self._json_response(result)

        elif path.startswith("/api/gateways/") and path.endswith("/stop"):
            gw_id = path.split("/")[3]
            result = manager.stop_gateway(gw_id)
            self._json_response(result)

        elif path.startswith("/api/gateways/") and path.endswith("/rename"):
            gw_id = path.split("/")[3]
            new_name = body.get("name", "")
            if new_name:
                manager.rename_gateway(gw_id, new_name)
                self._json_response({"status": "renamed"})
            else:
                self._json_response({"error": "name required"}, 400)

        elif path == "/api/problems":
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from deduction_db import DeductionDB
                db = DeductionDB()
                prob_id = db.add_problem({
                    'project_id': body.get('project_id', 'p_rose'),
                    'title': body.get('title', ''),
                    'description': body.get('description', ''),
                    'severity': body.get('severity', 'medium'),
                })
                db.close()
                self._json_response({'id': prob_id, 'status': 'created'}, 201)
            except Exception as e:
                self._json_response({'error': str(e)}, 500)

        elif path.startswith("/api/problems/") and path.endswith("/resolve"):
            prob_id = int(path.split("/")[3])
            solution = body.get('solution', '已解决')
            try:
                sys.path.insert(0, str(PROJECT_ROOT))
                from deduction_db import DeductionDB
                db = DeductionDB()
                db.resolve_problem(prob_id, solution)
                db.close()
                self._json_response({'status': 'resolved'})
            except Exception as e:
                self._json_response({'error': str(e)}, 500)

        else:
            self._json_response({"error": "not found"}, 404)

    def _proxy_to_agi(self, method: str):
        try:
            url = f"{AGI_API_BASE}{self.path}"
            headers = {}
            content_type = self.headers.get("Content-Type")
            if content_type:
                headers["Content-Type"] = content_type

            if method.upper() == "GET":
                r = requests.get(url, headers=headers, timeout=300)
            elif method.upper() == "POST":
                raw = self.rfile.read(int(self.headers.get('Content-Length', 0) or 0))
                r = requests.post(url, headers=headers, data=raw, timeout=300)
            else:
                self._json_response({"error": "method not allowed"}, 405)
                return

            self.send_response(r.status_code)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(r.content)
        except Exception as e:
            self._json_response({"error": str(e)}, 502)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/gateways/"):
            gw_id = path.split("/")[3]
            if manager.delete_gateway(gw_id):
                self._json_response({"status": "deleted"})
            else:
                self._json_response({"error": "not found"}, 404)
        else:
            self._json_response({"error": "not found"}, 404)

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 0:
                return json.loads(self.rfile.read(length))
        except Exception:
            pass
        return {}

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if '/api/' in str(args[0]) if args else False:
            log.info(f"API: {args[0]}")


def main():
    print(f"""
    ╔══════════════════════════════════════════╗
    ║   AGI v13 微信网关管理器                  ║
    ║   API: http://localhost:{API_PORT}              ║
    ║   CRM: http://localhost:{API_PORT}/crm.html     ║
    ╚══════════════════════════════════════════╝
    """)

    server = HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    log.info(f"服务器启动在 http://localhost:{API_PORT}")
    log.info(f"CRM: http://localhost:{API_PORT}/crm.html")
    log.info(f"API: http://localhost:{API_PORT}/api/gateways")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("停止服务器...")
        # 停止所有网关
        for gw_id in list(manager._stop_flags.keys()):
            manager.stop_gateway(gw_id)
        server.shutdown()


if __name__ == "__main__":
    main()
