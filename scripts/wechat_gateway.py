#!/usr/bin/env python3
"""
AGI Project 微信网关 — 基于腾讯 iLink 协议直连微信
无需 OpenClaw，纯 Python 实现。

用法:
  python3 scripts/wechat_gateway.py              # 启动网关(扫码登录)
  python3 scripts/wechat_gateway.py --resume      # 使用已保存的token恢复连接

协议来源: 腾讯 iLink Bot API (https://ilinkai.weixin.qq.com)
许可: 基于微信ClawBot插件官方开放协议，合法使用
"""

import os, sys, json, time, base64, struct, signal, logging, hashlib, re
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("wechat_gw")


class TokenExpiredError(Exception):
    """bot_token 已失效"""
    pass

# ── 项目路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 配置 ──
ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
CHANNEL_VERSION = "1.0.2"
TOKEN_FILE = PROJECT_ROOT / ".wechat_bot_token.json"
LOG_DIR = PROJECT_ROOT / "logs" / "wechat"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════
# iLink 协议实现
# ════════════════════════════════════════════════════════════

def _random_uin() -> str:
    """生成随机 X-WECHAT-UIN (防重放): random uint32 → 十进制字符串 → base64"""
    rand_bytes = os.urandom(4)
    uint32_val = struct.unpack('<I', rand_bytes)[0]
    return base64.b64encode(str(uint32_val).encode()).decode()


def _headers(bot_token: Optional[str] = None) -> dict:
    """构造 iLink 请求头"""
    h = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_uin(),
    }
    if bot_token:
        h["Authorization"] = f"Bearer {bot_token}"
    return h


class ILinkClient:
    """腾讯 iLink Bot API 客户端"""

    def __init__(self):
        self.bot_token: Optional[str] = None
        self.base_url: str = ILINK_BASE_URL
        self.session = requests.Session()
        self.session.timeout = 40  # 长轮询需要 > 35s

    def get_qrcode(self) -> dict:
        """获取登录二维码"""
        url = f"{self.base_url}/ilink/bot/get_bot_qrcode?bot_type=3"
        resp = self.session.get(url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        if data.get("ret") != 0 and "qrcode" not in data:
            raise RuntimeError(f"获取二维码失败: {data}")
        return data

    def poll_qrcode_status(self, qrcode: str) -> dict:
        """轮询扫码状态(服务端可能hold住连接等待扫码)"""
        url = f"{self.base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}"
        resp = self.session.get(url, headers=_headers(), timeout=40)
        resp.raise_for_status()
        return resp.json()

    def get_updates(self, cursor: str = "") -> dict:
        """长轮询收消息 (最长35秒hold)"""
        url = f"{self.base_url}/ilink/bot/getupdates"
        payload = {
            "get_updates_buf": cursor,
            "base_info": {"channel_version": CHANNEL_VERSION}
        }
        resp = self.session.post(url, json=payload,
                                 headers=_headers(self.bot_token), timeout=40)
        resp.raise_for_status()
        data = resp.json()
        # 检查两种错误格式: ret=-1 或 errcode<0
        if data.get("ret") == -1:
            raise TokenExpiredError("bot_token 已失效, 需要重新扫码登录")
        errcode = data.get("errcode", 0)
        if errcode and errcode < 0:
            errmsg = data.get("errmsg", "unknown")
            if errcode == -14 or "session" in errmsg.lower() or "token" in errmsg.lower():
                raise TokenExpiredError(f"session过期(errcode={errcode}): {errmsg}")
            log.warning(f"get_updates errcode={errcode}: {errmsg}")
        return data

    def send_message(self, to_user_id: str, text: str, context_token: str) -> dict:
        """发送文本消息"""
        url = f"{self.base_url}/ilink/bot/sendmessage"
        payload = {
            "msg": {
                "to_user_id": to_user_id,
                "message_type": 2,      # BOT 发出
                "message_state": 2,     # FINISH (完整消息)
                "context_token": context_token,
                "item_list": [
                    {"type": 1, "text_item": {"text": text}}
                ]
            }
        }
        hdrs = _headers(self.bot_token)
        resp = self.session.post(url, json=payload, headers=hdrs, timeout=10)
        resp.raise_for_status()
        data = resp.json() if resp.text.strip() else {}
        # 检查两种错误格式
        errcode = data.get("errcode", 0)
        if errcode and errcode < 0:
            errmsg = data.get("errmsg", "unknown")
            if errcode == -14 or "session" in errmsg.lower():
                raise TokenExpiredError(f"send失败(errcode={errcode}): {errmsg}")
            log.warning(f"send_message errcode={errcode}: {errmsg}")
        else:
            log.info(f"📤 已发送: {text[:60]}...")
        return data

    def send_typing(self, to_user_id: str, context_token: str,
                    typing_ticket: str = "") -> dict:
        """发送"正在输入"状态"""
        url = f"{self.base_url}/ilink/bot/sendtyping"
        payload = {
            "to_user_id": to_user_id,
            "context_token": context_token,
        }
        if typing_ticket:
            payload["typing_ticket"] = typing_ticket
        try:
            resp = self.session.post(url, json=payload,
                                     headers=_headers(self.bot_token), timeout=5)
            return resp.json()
        except Exception:
            return {}

    def get_config(self) -> dict:
        """获取配置(typing_ticket等)"""
        url = f"{self.base_url}/ilink/bot/getconfig"
        try:
            resp = self.session.post(url, json={},
                                     headers=_headers(self.bot_token), timeout=5)
            return resp.json()
        except Exception:
            return {}


# ════════════════════════════════════════════════════════════
# Token 持久化
# ════════════════════════════════════════════════════════════

def save_token(bot_token: str, base_url: str):
    """保存token到文件(下次可恢复连接)"""
    data = {
        "bot_token": bot_token,
        "base_url": base_url,
        "saved_at": datetime.now().isoformat(),
    }
    TOKEN_FILE.write_text(json.dumps(data, indent=2))
    log.info(f"Token 已保存到 {TOKEN_FILE}")


def load_token() -> Optional[dict]:
    """从文件加载已保存的token"""
    if TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text())
            if data.get("bot_token"):
                return data
        except Exception:
            pass
    return None


# ════════════════════════════════════════════════════════════
# AGI 消息处理器
# ════════════════════════════════════════════════════════════

class AGIMessageHandler:
    """AGI 项目消息处理器 — 接收微信消息，调用AGI能力，返回结果"""

    def __init__(self):
        self.conversation_history: dict = {}  # user_id → list of messages
        self._load_handlers()

    def _load_handlers(self):
        """加载命令处理器"""
        self.commands = {
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/projects": self._cmd_projects,
            "/deduction": self._cmd_deduction,
            "/problems": self._cmd_problems,
            "/skills": self._cmd_skills,
            "/crm": self._cmd_crm,
            "/问题": self._cmd_issues_open,
            "/已解决": self._cmd_issues_resolved,
            "/新问题": self._cmd_issue_add,
            "/解决": self._cmd_issue_resolve,
            "/所有问题": self._cmd_issues_all,
            "/skill": self._cmd_skill_search,
            "/技能": self._cmd_skill_search,
            "/处理": self._cmd_skill_solve,
            "/chain": self._cmd_chain,
            "/调用链": self._cmd_chain,
            "/项目列表": self._cmd_project_list,
            "/项目详情": self._cmd_project_detail,
            "/新项目": self._cmd_project_add,
            "/更新项目": self._cmd_project_update,
            "/删除项目": self._cmd_project_delete,
            "/项目进度": self._cmd_project_progress,
            "/统计": self._cmd_global_stats,
        }

    def is_command(self, text: str) -> bool:
        """判断是否为命令消息"""
        if not text.strip():
            return False
        return text.strip().split()[0].lower() in self.commands

    def handle(self, user_id: str, text: str) -> str:
        """处理命令消息，返回回复文本(非流式)"""
        text = text.strip()
        if not text:
            return ""

        # 记录对话历史
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({
            "role": "user", "content": text,
            "time": datetime.now().isoformat()
        })

        # 命令匹配
        cmd = text.split()[0].lower()
        if cmd in self.commands:
            reply = self.commands[cmd](text)
        else:
            reply = self._smart_reply(user_id, text)

        self._record_reply(user_id, reply)
        return reply

    def handle_streaming(self, user_id: str, text: str,
                         send_fn: Callable[[str], None]) -> str:
        """处理普通消息，通过7步调用链处理并逐步反馈"""
        text = text.strip()
        if not text:
            return ""

        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({
            "role": "user", "content": text,
            "time": datetime.now().isoformat()
        })

        # 使用7步调用链处理
        try:
            from wechat_chain_processor import ChainProcessor, format_chain_result_for_wechat

            def on_step(step_name, detail):
                """链路步骤回调: 给用户发送进度提示"""
                try:
                    send_fn(detail)
                except Exception:
                    pass

            chain = ChainProcessor(on_step=on_step)
            # 构建上下文(对话历史)
            history = self.conversation_history.get(user_id, [])
            ctx_parts = []
            for msg in history[-6:]:
                if msg["role"] == "user":
                    ctx_parts.append(f"用户: {msg['content'][:100]}")
                elif msg["role"] == "assistant":
                    ctx_parts.append(f"助手: {msg['content'][:100]}")
            context = "\n".join(ctx_parts[-4:]) if ctx_parts else ""

            result = chain.process(text, context=context)
            msgs = format_chain_result_for_wechat(result)

            # 发送最终结果(可能多条)
            full_reply = ""
            for msg in msgs:
                send_fn(msg)
                full_reply += msg + "\n"
                if len(msgs) > 1:
                    time.sleep(0.5)

            reply = full_reply.strip() or result.final_answer
            self._record_reply(user_id, reply)
            return reply
        except Exception as e:
            log.warning(f"调用链异常: {e}, 降级到流式回复")
            # 降级: 使用原有的Ollama流式回复
            reply = self.smart_reply_streaming(user_id, text, send_fn)
            self._record_reply(user_id, reply)
            return reply

    def _record_reply(self, user_id: str, reply: str):
        """记录回复到对话历史"""
        self.conversation_history[user_id].append({
            "role": "assistant", "content": reply,
            "time": datetime.now().isoformat()
        })

    def _cmd_help(self, text: str) -> str:
        return (
            "🤖 AGI v13 微信助手\n\n"
            "系统命令:\n"
            "/help — 显示帮助\n"
            "/status — 系统状态\n"
            "/projects — 项目列表\n"
            "/deduction — 推演状态\n"
            "/problems — 所有阻塞问题\n"
            "/skills — 技能库统计\n"
            "/crm — CRM 链接\n\n"
            "问题管理:\n"
            "/问题 [项目名] — 查看未处理问题\n"
            "/已解决 [项目名] — 查看已解决问题\n"
            "/所有问题 [项目名] — 查看全部问题\n"
            "/新问题 标题 — 添加新问题\n"
            "/解决 #ID 解决方案 — 标记问题已解决\n\n"
            "Skill 调用:\n"
            "/skill 查询词 — 搜索相关技能\n"
            "/技能 查询词 — 同上(中文)\n"
            "/处理 #ID — 用Skill+本地模型分析问题并给出方案\n\n"
            "AI调用链:\n"
            "/chain 问题 — 7步调用链(路由→GLM5T→GLM5→GLM47→校验→扫描)\n"
            "/调用链 问题 — 同上(中文)\n\n"
            "项目管理:\n"
            "/项目列表 — 查看所有项目\n"
            "/项目详情 ID — 项目详细信息\n"
            "/新项目 名称|描述|目标 — 创建项目\n"
            "/更新项目 ID 字段=值 — 更新项目\n"
            "/项目进度 ID 百分比 — 更新进度\n"
            "/删除项目 ID — 归档项目\n"
            "/统计 — 全局统计\n\n"
            "直接发消息即可与 AGI 对话(自动走7步调用链) 💬"
        )

    def _cmd_status(self, text: str) -> str:
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            stats = db.get_stats()
            db.close()
            return (
                f"📊 AGI v13 系统状态\n\n"
                f"推演计划: {stats.get('total_plans', 0)} 个\n"
                f"  ✅ 完成: {stats.get('done', 0)}\n"
                f"  ⏳ 队列: {stats.get('queued', 0)}\n"
                f"  🔄 运行中: {stats.get('running', 0)}\n\n"
                f"知识节点: {stats.get('total_nodes', 0)} 个\n"
                f"推演步骤: {stats.get('total_steps', 0)} 步\n"
                f"阻塞问题: {stats.get('problems_open', 0)} 个 (open)\n"
            )
        except Exception as e:
            return f"⚠️ 无法获取状态: {e}"

    def _cmd_projects(self, text: str) -> str:
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            projects = db.get_projects()
            db.close()
            if not projects:
                return "暂无项目"
            lines = ["📁 项目列表\n"]
            for p in projects:
                lines.append(f"• {p['name']}\n  {p.get('description', '')[:50]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _cmd_deduction(self, text: str) -> str:
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            stats = db.get_stats()
            plans = db.get_plans(status='queued')
            db.close()
            lines = [
                f"🔬 推演状态\n",
                f"总计: {stats.get('total_plans', 0)} | "
                f"完成: {stats.get('done', 0)} | "
                f"队列: {stats.get('queued', 0)}\n",
            ]
            if plans:
                lines.append("待推演 (前5个):")
                for p in plans[:5]:
                    lines.append(f"  • [{p.get('priority','?')}] {p['title']}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _cmd_problems(self, text: str) -> str:
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            problems = db.conn.execute(
                "SELECT id, title, severity, status, project_id FROM blocked_problems "
                "ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, created_at DESC LIMIT 10"
            ).fetchall()
            db.close()
            if not problems:
                return "✅ 当前无阻塞问题"
            lines = ["⚠️ 全部阻塞问题 (前10个)\n"]
            for p in problems:
                st = '⭕' if p[3] == 'open' else '✅'
                lines.append(f"  {st} #{p[0]} [{p[2]}] {p[1][:50]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _find_project_id(self, text_args: str) -> tuple:
        """从命令参数中查找项目ID,返回 (project_id, project_name)"""
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            projects = db.get_projects()
            db.close()
        except Exception:
            return ('p_rose', '予人玫瑰')

        if not text_args.strip():
            return ('p_rose', '予人玫瑰')

        keyword = text_args.strip()
        for p in projects:
            if keyword in p['name'] or keyword == p['id']:
                return (p['id'], p['name'])
        return ('p_rose', '予人玫瑰')

    def _cmd_issues_open(self, text: str) -> str:
        """/问题 [项目名] — 查看未处理问题"""
        try:
            args = text.strip()[len('/问题'):].strip()
            pid, pname = self._find_project_id(args)
            from deduction_db import DeductionDB
            db = DeductionDB()
            problems = db.get_problems(project_id=pid, status='open')
            db.close()
            if not problems:
                return f"✅ {pname}项目无未处理问题"
            lines = [f"⭕ {pname} — 未处理问题 ({len(problems)}个)\n"]
            for p in problems:
                lines.append(f"  #{p['id']} [{p['severity']}] {p['title'][:55]}")
                if p.get('description'):
                    lines.append(f"    {p['description'][:60]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _cmd_issues_resolved(self, text: str) -> str:
        """/已解决 [项目名] — 查看已解决问题"""
        try:
            args = text.strip()[len('/已解决'):].strip()
            pid, pname = self._find_project_id(args)
            from deduction_db import DeductionDB
            db = DeductionDB()
            problems = db.get_problems(project_id=pid, status='resolved')
            db.close()
            if not problems:
                return f"ℹ️ {pname}项目无已解决问题"
            lines = [f"✅ {pname} — 已解决问题 ({len(problems)}个)\n"]
            for p in problems:
                sol = p.get('user_solution', '') or ''
                lines.append(f"  #{p['id']} {p['title'][:50]}")
                if sol:
                    lines.append(f"    解决: {sol[:60]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _cmd_issues_all(self, text: str) -> str:
        """/所有问题 [项目名] — 查看全部问题"""
        try:
            args = text.strip()[len('/所有问题'):].strip()
            pid, pname = self._find_project_id(args)
            from deduction_db import DeductionDB
            db = DeductionDB()
            problems = db.get_problems(project_id=pid)
            db.close()
            if not problems:
                return f"ℹ️ {pname}项目无问题记录"
            open_count = sum(1 for p in problems if p['status'] == 'open')
            resolved_count = sum(1 for p in problems if p['status'] == 'resolved')
            lines = [f"📊 {pname} — 全部问题 ({len(problems)}个: {open_count}未处理 {resolved_count}已解决)\n"]
            for p in problems:
                st = '⭕' if p['status'] == 'open' else '✅'
                lines.append(f"  {st} #{p['id']} [{p['severity']}] {p['title'][:50]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ {e}"

    def _cmd_issue_add(self, text: str) -> str:
        """/新问题 标题内容"""
        try:
            args = text.strip()[len('/新问题'):].strip()
            if not args:
                return "用法: /新问题 问题标题\n例: /新问题 支付接口对接未完成"

            # 支持 "/新问题 [项目名] 标题" 格式
            pid, pname = 'p_rose', '予人玫瑰'
            if args.startswith('[') and ']' in args:
                proj_name = args[1:args.index(']')]
                args = args[args.index(']')+1:].strip()
                pid, pname = self._find_project_id(proj_name)

            if not args:
                return "⚠️ 请提供问题标题"

            # 支持 "标题|描述" 格式
            if '|' in args:
                title, desc = args.split('|', 1)
            else:
                title, desc = args, ''

            from deduction_db import DeductionDB
            db = DeductionDB()
            prob_id = db.add_problem({
                'project_id': pid,
                'title': title.strip(),
                'description': desc.strip(),
                'severity': 'medium',
            })
            db.close()
            return f"✅ 已添加问题 #{prob_id}\n项目: {pname}\n标题: {title.strip()}\n状态: open"
        except Exception as e:
            return f"⚠️ 添加失败: {e}"

    def _cmd_issue_resolve(self, text: str) -> str:
        """/解决 #ID 解决方案"""
        try:
            args = text.strip()[len('/解决'):].strip()
            if not args:
                return "用法: /解决 #ID 解决方案描述\n例: /解决 #3 已对接微信支付"

            # 解析 ID
            import re as _re
            m = _re.match(r'#?(\d+)\s*(.*)', args)
            if not m:
                return "⚠️ 格式错误，用法: /解决 #ID 解决方案"
            prob_id = int(m.group(1))
            solution = m.group(2).strip() or '已解决'

            from deduction_db import DeductionDB
            db = DeductionDB()
            # 检查问题是否存在
            row = db.conn.execute("SELECT id, title, status FROM blocked_problems WHERE id=?", (prob_id,)).fetchone()
            if not row:
                db.close()
                return f"⚠️ 问题 #{prob_id} 不存在"
            if row[2] == 'resolved':
                db.close()
                return f"ℹ️ 问题 #{prob_id} 已经是已解决状态"

            db.resolve_problem(prob_id, solution)
            db.close()
            return f"✅ 问题 #{prob_id} 已标记为已解决\n标题: {row[1][:50]}\n方案: {solution[:60]}"
        except Exception as e:
            return f"⚠️ 解决失败: {e}"

    def _cmd_skills(self, text: str) -> str:
        try:
            from pcm_skill_router import get_router
            router = get_router()
            count = len(router.library.skills)
            cats = len(router.library.by_category)
            return (
                f"🧪 Skill 技能库统计\n\n"
                f"已加载技能: {count} 个\n"
                f"类别数: {cats} 个\n"
                f"关键词索引: {len(router.library.keyword_index)} 个\n\n"
                "发 /skill <关键词> 搜索相关技能\n"
                "发 /处理 #ID 用Skill链分析问题"
            )
        except Exception:
            return (
                "🧪 Skill 技能库\n\n"
                "自有技能 + OpenClaw + gstack\n"
                "总计: ~7,000+ 个\n\n"
                "发 /skill <关键词> 搜索相关技能"
            )

    def _cmd_skill_search(self, text: str) -> str:
        """/skill <query> — 搜索相关技能"""
        try:
            cmd = text.strip().split()[0]
            query = text.strip()[len(cmd):].strip()
            if not query:
                return "用法: /skill 查询关键词\n例: /skill 部署\n例: /skill 支付接口\n例: /skill 数据分析"

            from pcm_skill_router import route_skills
            results = route_skills(query, top_k=8)
            if not results:
                return f"未找到与 '{query}' 相关的技能"

            lines = [f"🔍 为 '{query}' 匹配到 {len(results)} 个技能:\n"]
            for i, r in enumerate(results, 1):
                src = f"[{r['source']}]" if r.get('source') else ''
                lines.append(f"{i}. {r['name']} (score={r['score']}) {src}")
                if r.get('description'):
                    lines.append(f"   {r['description'][:60]}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ Skill搜索失败: {e}"

    def _cmd_skill_solve(self, text: str) -> str:
        """/处理 #ID — 用Skill链+本地模型分析问题并给出方案"""
        try:
            args = text.strip()[len('/处理'):].strip()
            if not args:
                return "用法: /处理 #ID\n例: /处理 #3\n会用本地模型+相关Skill分析问题并给出解决方案"

            import re as _re
            m = _re.match(r'#?(\d+)', args)
            if not m:
                return "⚠️ 格式错误，用法: /处理 #ID"
            prob_id = int(m.group(1))

            # 获取问题详情
            from deduction_db import DeductionDB
            db = DeductionDB()
            row = db.conn.execute(
                "SELECT id, title, description, severity, project_id, suggested_solution "
                "FROM blocked_problems WHERE id=?", (prob_id,)
            ).fetchone()
            if not row:
                db.close()
                return f"⚠️ 问题 #{prob_id} 不存在"

            prob_title = row[1]
            prob_desc = row[2] or ''
            prob_severity = row[3]
            proj_row = db.conn.execute("SELECT name FROM projects WHERE id=?", (row[4],)).fetchone()
            proj_name = proj_row[0] if proj_row else row[4]
            suggested = row[5] or ''
            db.close()

            # 搜索相关Skill
            skill_context = ""
            try:
                from pcm_skill_router import route_skills
                search_query = f"{prob_title} {prob_desc[:100]}"
                skills = route_skills(search_query, top_k=5)
                if skills:
                    skill_lines = []
                    for s in skills:
                        skill_lines.append(f"- {s['name']}: {s['description'][:80]}")
                    skill_context = "\n相关技能:\n" + "\n".join(skill_lines)
            except Exception:
                pass

            # 用本地模型分析
            prompt = (
                f"你是AGI v13系统的问题分析器。请分析以下阻塞问题并给出具体可执行的解决方案。\n\n"
                f"项目: {proj_name}\n"
                f"问题 #{prob_id}: {prob_title}\n"
                f"描述: {prob_desc[:300]}\n"
                f"严重程度: {prob_severity}\n"
                f"{'建议: ' + suggested if suggested else ''}\n"
                f"{skill_context}\n\n"
                "请给出:\n"
                "1. 问题根因分析(简洁)\n"
                "2. 具体解决步骤(3-5步)\n"
                "3. 需要用到的技能/工具\n"
                "4. 预计工作量\n"
                "回复简洁实用，中文。"
            )

            try:
                resp = requests.post(
                    "http://localhost:11434/api/chat",
                    json={"model": "qwen2.5-coder:14b",
                          "messages": [{"role": "user", "content": prompt}],
                          "stream": False, "options": {"num_predict": 800}},
                    timeout=60
                )
                if resp.status_code == 200:
                    analysis = resp.json().get("message", {}).get("content", "").strip()
                    if analysis:
                        header = f"🔧 问题 #{prob_id} 分析\n{prob_title}\n{'='*30}\n"
                        return (header + analysis)[:2000]
            except Exception:
                pass

            # Ollama不可用时的降级方案
            lines = [f"🔧 问题 #{prob_id} 分析\n"]
            lines.append(f"项目: {proj_name}")
            lines.append(f"标题: {prob_title}")
            lines.append(f"严重程度: {prob_severity}")
            if prob_desc:
                lines.append(f"描述: {prob_desc[:100]}")
            if suggested:
                lines.append(f"建议: {suggested[:100]}")
            if skill_context:
                lines.append(skill_context)
            lines.append("\n⚠️ 本地模型(Ollama)未运行，无法生成智能分析")
            lines.append("请启动 Ollama 后重试")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ 分析失败: {e}"

    def _cmd_chain(self, text: str) -> str:
        """/chain 问题 — 7步AI调用链"""
        try:
            cmd = text.strip().split()[0]
            question = text.strip()[len(cmd):].strip()
            if not question:
                return (
                    "🔗 AI调用链用法\n\n"
                    "/chain 你的问题\n"
                    "/调用链 你的问题\n\n"
                    "链路: Ollama路由 → GLM-5T快速分析 → GLM-5深度推理 "
                    "→ GLM-4.7代码生成 → Ollama幻觉校验 → 零回避扫描\n\n"
                    "简单问题Ollama直答, 复杂问题自动走完整链路"
                )
            from wechat_chain_processor import ChainProcessor, format_chain_result_for_wechat
            chain = ChainProcessor()
            result = chain.process(question)
            msgs = format_chain_result_for_wechat(result)
            return msgs[0] if msgs else "⚠️ 调用链未生成有效输出"
        except Exception as e:
            return f"⚠️ 调用链失败: {e}"

    def _cmd_project_list(self, text: str) -> str:
        """/项目列表 — 查看所有项目"""
        from wechat_chain_processor import db_list_projects
        return db_list_projects()

    def _cmd_project_detail(self, text: str) -> str:
        """/项目详情 ID — 项目详细信息"""
        args = text.strip().split(maxsplit=1)
        if len(args) < 2:
            return "用法: /项目详情 项目ID或名称\n例: /项目详情 p_rose\n例: /项目详情 予人玫瑰"
        from wechat_chain_processor import db_project_detail
        return db_project_detail(args[1].strip())

    def _cmd_project_add(self, text: str) -> str:
        """/新项目 名称|描述|目标"""
        content = text.strip()[len('/新项目'):].strip()
        if not content:
            return "用法: /新项目 名称|描述|目标\n例: /新项目 测试项目|这是一个测试|完成测试"
        parts = content.split('|')
        name = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ''
        goal = parts[2].strip() if len(parts) > 2 else ''
        from wechat_chain_processor import db_add_project
        return db_add_project(name, desc, goal)

    def _cmd_project_update(self, text: str) -> str:
        """/更新项目 ID 字段=值"""
        content = text.strip()[len('/更新项目'):].strip()
        if not content:
            return (
                "用法: /更新项目 ID 字段=值\n"
                "可更新字段: name, description, status, short_term_goal, ultimate_goal\n"
                "例: /更新项目 p_rose status=paused\n"
                "例: /更新项目 p_rose short_term_goal=完成支付接入"
            )
        parts = content.split(maxsplit=1)
        if len(parts) < 2:
            return "⚠️ 缺少更新内容，用法: /更新项目 ID 字段=值"
        pid = parts[0]
        updates = {}
        allowed = {'name', 'description', 'status', 'short_term_goal', 'ultimate_goal', 'color', 'tags'}
        for item in parts[1].split():
            if '=' in item:
                k, v = item.split('=', 1)
                if k in allowed:
                    updates[k] = v
        if not updates:
            return "⚠️ 未识别到有效更新字段"
        from wechat_chain_processor import db_update_project
        return db_update_project(pid, updates)

    def _cmd_project_progress(self, text: str) -> str:
        """/项目进度 ID 百分比"""
        content = text.strip()[len('/项目进度'):].strip()
        if not content:
            return "用法: /项目进度 ID 百分比\n例: /项目进度 p_rose 45"
        parts = content.split()
        if len(parts) < 2:
            return "⚠️ 缺少进度值，用法: /项目进度 ID 百分比"
        import re as _re
        m = _re.match(r'(\d+)', parts[1])
        if not m:
            return "⚠️ 进度必须是数字(0-100)"
        progress = min(100, max(0, int(m.group(1))))
        from wechat_chain_processor import db_update_project
        return db_update_project(parts[0], {'progress': progress})

    def _cmd_project_delete(self, text: str) -> str:
        """/删除项目 ID"""
        content = text.strip()[len('/删除项目'):].strip()
        if not content:
            return "用法: /删项目 项目ID\n例: /删项目 p_test"
        from wechat_chain_processor import db_delete_project
        return db_delete_project(content.strip())

    def _cmd_global_stats(self, text: str) -> str:
        """/统计 — 全局统计"""
        from wechat_chain_processor import db_get_stats
        return db_get_stats()

    def _cmd_crm(self, text: str) -> str:
        return (
            "🖥️ CRM 系统\n\n"
            "本地访问: http://localhost:8888/crm.html\n"
            "功能: 项目管理/推演列表/任务/技能库/模型能力/问题追踪/工作流\n\n"
            "请确保 CRM 服务已启动:\n"
            "cd web && python3 -m http.server 8888"
        )

    SYSTEM_PROMPT = (
        "你是 AGI v13 智能助手，由用户自主开发的本地AGI系统驱动，运行在用户自己的电脑上。"
        "你不是任何商业公司的产品，不是阿里云、OpenAI或任何第三方开发的。"
        "你的核心能力来自本地部署的模型和ULDS v2.1推演框架。"
        "你拥有7000+技能库(Skill)支撑，涵盖编码/部署/搜索/安全/数据分析等领域。"
        "当用户提问时，你会自动匹配相关Skill上下文来增强回答。"
        "你可以查询项目状态、推演任务、技能库、阻塞问题等(用户可发 /help 查看命令)。"
        "回复简洁、有用、友好。使用中文回复。"
    )

    def _get_skill_context(self, text: str) -> str:
        """根据用户输入获取相关Skill上下文注入到LLM"""
        try:
            from pcm_skill_router import route_skills
            results = route_skills(text, top_k=3)
            if not results or results[0]['score'] < 3.0:
                return ""
            lines = ["\n[相关技能参考]:"]
            for r in results:
                lines.append(f"- {r['name']}: {r['description'][:80]}")
            return "\n".join(lines)
        except Exception:
            return ""

    def _build_chat_messages(self, user_id: str, text: str) -> list:
        """构建带历史的chat消息列表，自动注入Skill上下文"""
        skill_ctx = self._get_skill_context(text)
        system = self.SYSTEM_PROMPT
        if skill_ctx:
            system += skill_ctx

        messages = [{"role": "system", "content": system}]
        history = self.conversation_history.get(user_id, [])
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": text})
        return messages

    def _smart_reply(self, user_id: str, text: str) -> str:
        """非流式智能回复(命令等场景的降级方案)"""
        messages = self._build_chat_messages(user_id, text)
        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={"model": "qwen2.5-coder:14b", "messages": messages,
                      "stream": False, "options": {"num_predict": 500}},
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json().get("message", {}).get("content", "").strip()
                if result:
                    return result[:2000]
        except Exception:
            pass
        return self._fallback_reply(text)

    def smart_reply_streaming(self, user_id: str, text: str,
                              send_fn: Callable[[str], None]) -> str:
        """流式智能回复: 边生成边按段落发送到微信
        
        Args:
            user_id: 用户ID
            text: 用户消息
            send_fn: 发送一段文本的回调函数
        Returns:
            完整回复文本(用于记录)
        """
        messages = self._build_chat_messages(user_id, text)

        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={"model": "qwen2.5-coder:14b", "messages": messages,
                      "stream": True, "options": {"num_predict": 800}},
                stream=True, timeout=60
            )
            if resp.status_code != 200:
                fallback = self._fallback_reply(text)
                send_fn(fallback)
                return fallback
        except Exception:
            fallback = self._fallback_reply(text)
            send_fn(fallback)
            return fallback

        # 流式读取，按段落分批发送
        full_text = ""
        buffer = ""
        sent_parts = []
        CHUNK_MIN = 80   # 最少积累80字符再发
        CHUNK_MAX = 400  # 最多400字符强制发一次

        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                done = chunk.get("done", False)
            except Exception:
                continue

            full_text += token
            buffer += token

            # 判断是否该发送当前buffer
            should_send = False
            if done and buffer.strip():
                should_send = True
            elif len(buffer) >= CHUNK_MAX:
                should_send = True
            elif len(buffer) >= CHUNK_MIN:
                # 在自然断点处发送: 双换行、句号+换行、段落结束
                if buffer.endswith("\n\n"):
                    should_send = True
                elif any(buffer.rstrip().endswith(p) for p in ["。", "！", "？", ".", "!", "?"]):
                    if "\n" in buffer[-5:]:
                        should_send = True
                # 遇到列表项开头也分段
                elif re.search(r'\n\d+\.\s', buffer[-10:]):
                    should_send = True
                elif re.search(r'\n[-*•]\s', buffer[-10:]):
                    should_send = True

            if should_send and buffer.strip():
                part = buffer.strip()[:2000]
                send_fn(part)
                sent_parts.append(part)
                log.info(f"  📤 流式段落 [{len(sent_parts)}]: {part[:50]}...")
                buffer = ""
                time.sleep(0.3)  # 短暂间隔,避免刷屏

        # 如果buffer还有剩余(不太可能但保险起见)
        if buffer.strip():
            part = buffer.strip()[:2000]
            send_fn(part)
            sent_parts.append(part)

        if not full_text.strip():
            fallback = self._fallback_reply(text)
            send_fn(fallback)
            return fallback

        return full_text.strip()

    @staticmethod
    def _fallback_reply(text: str) -> str:
        """降级规则匹配回复"""
        if any(w in text for w in ["你好", "hello", "hi", "嗨"]):
            return "你好！我是 AGI v13 微信助手 🤖\n发 /help 查看可用命令"
        if any(w in text for w in ["谢谢", "感谢", "thanks"]):
            return "不客气！有问题随时问我 😊"
        return (
            f"收到消息: {text[:100]}\n\n"
            "⚠️ 本地模型(Ollama)未运行，无法智能回复。\n"
            "发 /help 查看可用命令，或启动 Ollama 后重试。"
        )


# ════════════════════════════════════════════════════════════
# 消息日志
# ════════════════════════════════════════════════════════════

def log_message(direction: str, user_id: str, text: str, gateway_id: str = "default"):
    """记录消息到日志文件 + Redis"""
    log_file = LOG_DIR / f"messages_{datetime.now().strftime('%Y%m%d')}.jsonl"
    entry = {
        "time": datetime.now().isoformat(),
        "direction": direction,  # "in" or "out"
        "user_id": user_id,
        "text": text[:500],
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 同步写入 Redis (3天TTL)
    try:
        from wechat_redis import save_message
        save_message(gateway_id, user_id, direction, text)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
# 二维码终端显示
# ════════════════════════════════════════════════════════════

def display_qrcode_terminal(qr_url: str):
    """在终端显示二维码(使用 qrcode 库或提示 URL)"""
    try:
        import qrcode as qr_lib
        qr = qr_lib.QRCode(version=1, box_size=1, border=1)
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        log.info("提示: pip install qrcode[pil] 可在终端显示二维码")
    print(f"\n📱 请用微信扫描上方二维码，或在浏览器打开此链接:\n{qr_url}\n")


# ════════════════════════════════════════════════════════════
# 主循环
# ════════════════════════════════════════════════════════════

def login(client: ILinkClient) -> bool:
    """登录流程: 获取二维码 → 等待扫码 → 获取 token"""
    log.info("正在获取登录二维码...")
    try:
        qr_data = client.get_qrcode()
    except Exception as e:
        log.error(f"获取二维码失败: {e}")
        return False

    qrcode_id = qr_data.get("qrcode", "")
    # qrcode_img_content 是扫码URL(不是base64图片)
    qr_url = qr_data.get("qrcode_img_content", "") or qr_data.get("url", "")

    if not qrcode_id:
        log.error(f"二维码数据异常: {qr_data}")
        return False

    # 显示二维码
    print("\n" + "=" * 50)
    print("🔐 微信扫码登录")
    print("=" * 50)

    if qr_url:
        display_qrcode_terminal(qr_url)

    # 轮询扫码状态
    log.info("等待微信扫码...")
    max_wait = 120  # 最多等2分钟
    start = time.time()
    while time.time() - start < max_wait:
        try:
            status = client.poll_qrcode_status(qrcode_id)
            s = status.get("status", status.get("state", ""))

            if s == "confirmed":
                client.bot_token = status.get("bot_token", "")
                new_base = status.get("baseurl", "")
                if new_base:
                    client.base_url = new_base

                save_token(client.bot_token, client.base_url)
                log.info("✅ 登录成功!")
                return True

            elif s == "scanned":
                log.info("📱 已扫码，请在手机上确认...")

            elif s == "expired":
                log.error("❌ 二维码已过期")
                return False

        except Exception as e:
            log.warning(f"轮询异常: {e}")

        time.sleep(2)

    log.error("❌ 登录超时")
    return False


def message_loop(client: ILinkClient, handler: AGIMessageHandler):
    """消息收发主循环 — 消息处理在后台线程,不阻塞轮询"""
    import threading
    cursor = ""
    error_count = 0
    max_errors = 10
    empty_polls = 0

    def _process_msg(from_user, text, context_token):
        """在后台线程处理消息,不阻塞轮询循环"""
        try:
            client.send_typing(from_user, context_token)

            def _send(part):
                try:
                    client.send_message(from_user, part, context_token)
                except Exception as se:
                    log.warning(f"发送失败: {se}")

            if handler.is_command(text):
                reply = handler.handle(from_user, text)
                if reply:
                    _send(reply)
                    log.info(f"� 回复: {reply[:80]}...")
                    log_message("out", from_user, reply)
            else:
                reply = handler.handle_streaming(from_user, text, _send)
                log.info(f"📤 流式回复完成: {reply[:80]}...")
                log_message("out", from_user, reply)
        except Exception as e:
            log.warning(f"消息处理异常: {e}")

    log.info("�🚀 消息循环启动，等待微信消息...")
    print("\n" + "=" * 50)
    print("AGI v13 微信网关已启动 (非阻塞模式)")
    print("按 Ctrl+C 停止")
    print("=" * 50 + "\n")

    while True:
        try:
            # 长轮询收消息 (最长35秒)
            result = client.get_updates(cursor)
            error_count = 0  # 重置错误计数

            # 更新游标
            new_cursor = result.get("get_updates_buf", "")
            if new_cursor:
                cursor = new_cursor

            # 处理消息
            msgs = result.get("msgs", [])
            if msgs:
                empty_polls = 0
            else:
                empty_polls += 1

            for msg in msgs:
                msg_type = msg.get("message_type", 0)
                if msg_type != 1:  # 只处理用户发来的消息
                    continue

                from_user = msg.get("from_user_id", "")
                context_token = msg.get("context_token", "")
                items = msg.get("item_list", [])

                for item in items:
                    item_type = item.get("type", 0)
                    text = ""

                    if item_type == 1:  # 文本消息
                        text = item.get("text_item", {}).get("text", "")
                    elif item_type == 3:  # 语音(转文字)
                        text = item.get("voice_item", {}).get("text", "")
                        if text:
                            log.info(f"🎤 收到语音(转文字): {text[:80]}")
                    elif item_type == 2:  # 图片
                        log.info(f"📷 收到图片消息 (暂不支持)")
                        try:
                            client.send_message(
                                from_user,
                                "收到图片 📷 当前版本暂不支持图片处理，请发送文字消息。",
                                context_token
                            )
                        except Exception:
                            pass
                        continue

                    if not text:
                        continue

                    log.info(f"� 收到: {from_user[:20]}... → {text[:80]}")
                    log_message("in", from_user, text)

                    # 在后台线程处理,不阻塞轮询
                    t = threading.Thread(
                        target=_process_msg,
                        args=(from_user, text, context_token),
                        daemon=True
                    )
                    t.start()

            # 每50次空轮询刷新session防止连接腐烂
            if empty_polls > 0 and empty_polls % 50 == 0:
                client.session.close()
                client.session = requests.Session()
                client.session.timeout = 40
                log.info(f"Session已刷新 (空轮询{empty_polls}次)")

        except KeyboardInterrupt:
            log.info("用户中断，正在退出...")
            break

        except TokenExpiredError:
            log.warning("⚠️ Token 已失效，尝试重新登录...")
            if login(client):
                cursor = ""  # 重置游标
                error_count = 0
                log.info("✅ 重新登录成功，继续消息循环")
            else:
                log.error("❌ 重新登录失败，退出")
                break

        except requests.exceptions.Timeout:
            # 长轮询超时是正常的
            continue

        except requests.exceptions.ConnectionError as e:
            error_count += 1
            log.warning(f"连接错误 ({error_count}/{max_errors}): {e}")
            if error_count >= max_errors:
                log.error("连续错误过多，退出")
                break
            # 刷新session重连
            client.session.close()
            client.session = requests.Session()
            client.session.timeout = 40
            time.sleep(min(error_count * 2, 30))

        except Exception as e:
            error_count += 1
            log.error(f"异常 ({error_count}/{max_errors}): {e}")
            if error_count >= max_errors:
                log.error("连续错误过多，退出")
                break
            time.sleep(5)


# ════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AGI v13 微信网关 (iLink 协议直连)")
    parser.add_argument("--resume", action="store_true", help="使用已保存的token恢复连接")
    args = parser.parse_args()

    print("""
    ╔══════════════════════════════════════════╗
    ║   AGI v13 微信网关                       ║
    ║   基于腾讯 iLink 协议直连                 ║
    ║   无需 OpenClaw                          ║
    ╚══════════════════════════════════════════╝
    """)

    client = ILinkClient()
    handler = AGIMessageHandler()

    # 尝试恢复 token
    if args.resume:
        saved = load_token()
        if saved:
            client.bot_token = saved["bot_token"]
            client.base_url = saved.get("base_url", ILINK_BASE_URL)
            log.info(f"已加载保存的 token (保存于 {saved.get('saved_at', '?')})")
        else:
            log.warning("未找到保存的 token，需要重新登录")
            if not login(client):
                sys.exit(1)
    else:
        if not login(client):
            sys.exit(1)

    # 启动消息循环
    message_loop(client, handler)

    log.info("微信网关已停止")


if __name__ == "__main__":
    main()
