#!/usr/bin/env python3
"""
OpenClaw Bridge — OpenAI-compatible API 桥接本地 Chain Processor

OpenClaw (微信中转) → POST /v1/chat/completions → 本地7步链 → 返回结果

内容注入: AGI 项目上下文 (projects / skills / identity) 自动注入 system prompt
所有 llm_call() 经由此 bridge 统一处理，不再直接调 Ollama/GLM。
"""
import json
import os
import sys
import time
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("openclaw_bridge")

# ── 代码代理能力 ──────────────────────────────────────────
try:
    from code_agent import CodeAgent, parse_code_actions, execute_ai_actions
    _CODE_AGENT = CodeAgent(workspace=PROJECT_ROOT)
    log.info("[代码代理] 已加载，支持文件读写/终端执行/项目分析")
except ImportError as e:
    _CODE_AGENT = None
    log.warning(f"[代码代理] 未加载: {e}")

# ── 闲置推演集成 ──────────────────────────────────────────
_LAST_REQUEST_FILE = PROJECT_ROOT / ".last_request_time"

def _update_last_request():
    """更新最后请求时间，供闲置推演引擎检测"""
    try:
        _LAST_REQUEST_FILE.write_text(str(time.time()))
    except:
        pass

# ── AGI 上下文注入 ──────────────────────────────────────────
_AGI_CONTEXT: str = ""
_CONTEXT_LOADED: bool = False
KNOWLEDGE_FEED = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"

def _load_agi_context() -> str:
    """
    加载 AGI 项目上下文作为 system prompt。
    优先加载完整知识库文件 data/agi_knowledge_feed.md，
    如不存在则回退到内联生成简洁版本。
    """
    global _AGI_CONTEXT, _CONTEXT_LOADED
    if _CONTEXT_LOADED:
        return _AGI_CONTEXT

    # ① 优先: 加载全量知识库文件
    if KNOWLEDGE_FEED.exists():
        try:
            _AGI_CONTEXT = KNOWLEDGE_FEED.read_text(encoding="utf-8")
            _CONTEXT_LOADED = True
            log.info(f"[知识库] 已加载 {len(_AGI_CONTEXT):,} 字符 ← {KNOWLEDGE_FEED.name}")
            return _AGI_CONTEXT
        except Exception as e:
            log.warning(f"[知识库] 加载失败: {e}，回退到内联生成")

    # ② 回退: 内联生成简洁版
    log.info("[上下文] agi_knowledge_feed.md 不存在，生成内联简洁版..")
    lines = []
    lines.append("# AGI PROJECT — 上下文注入")
    lines.append("你是 AGI 项目的核心助手，具备以下完整上下文：\n")

    # 项目列表 (from DeductionDB)
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        projects = db.get_projects()
        plans = db.get_plans()
        db.close()
        active = [p for p in projects if p.get("status") == "active"]
        lines.append("## 当前活跃项目")
        for p in active:
            lines.append(f"- [{p['id']}] {p['name']}: {p.get('description','')[:80]}")
            if p.get("ultimate_goal"):
                lines.append(f"  终极目标: {p['ultimate_goal'][:60]}")
        queued = [pl for pl in plans if pl.get("status") == "queued"]
        lines.append(f"\n## 待推演计划: 共 {len(queued)} 条")
        for pl in queued[:8]:
            lines.append(f"- [{pl['priority']}] {pl['title']}")
        if len(queued) > 8:
            lines.append(f"  … 还有 {len(queued)-8} 条")
    except Exception as e:
        log.warning(f"DeductionDB 加载失败: {e}")

    # Skill 库摘要
    try:
        import json as _j
        from collections import defaultdict
        skills_dir = PROJECT_ROOT / "workspace" / "skills"
        cat_count: dict = defaultdict(int)
        for mf in skills_dir.glob("*.meta.json"):
            try:
                m = _j.loads(mf.read_text(encoding="utf-8"))
                tag = (m.get("tags") or ["通用"])[0]
                cat_count[tag] += 1
            except:
                pass
        lines.append(f"\n## Skill库: {sum(cat_count.values())} 个 / {len(cat_count)} 类")
        for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1])[:12]:
            lines.append(f"  {cat}: {cnt}")
    except Exception as e:
        log.warning(f"Skill库加载失败: {e}")

    lines.append("\n## 能力: 7步链+ULDS+6000+Skill+自成长+DeductionDB")
    lines.append("请根据上下文精准理解用户意图。")
    lines.append(f"\n提示: 运行 `python3 scripts/feed_openclaw.py --push` 可生成全量知识库并刷新此上下文")

    _AGI_CONTEXT = "\n".join(lines)
    _CONTEXT_LOADED = True
    log.info(f"[上下文] 内联简洁版 {len(_AGI_CONTEXT)} 字符")
    return _AGI_CONTEXT


def _refresh_context():
    """强制刷新上下文（项目/计划更新后调用）"""
    global _CONTEXT_LOADED
    _CONTEXT_LOADED = False
    _load_agi_context()


_last_question: str = ""  # 用于主题感知的context裁剪

def _get_compact_context(max_chars: int = 5000) -> str:
    """
    智能上下文裁剪: 根据问题主题动态选择知识库片段。
    固定部分(元框架) + 动态部分(匹配问题关键词的章节)。
    """
    full = _load_agi_context()
    if len(full) <= max_chars:
        return full

    # 固定部分: 元框架(始终注入, ≤1200字)
    fixed = []
    for marker in ["# 元框架：知与不知"]:
        idx = full.find(marker)
        if idx != -1:
            end = full.find("\n# ", idx + len(marker))
            fixed.append(full[idx:min(end if end != -1 else idx + 1200, idx + 1200)])

    # 动态部分: 根据问题关键词匹配章节
    q = _last_question.lower()
    topic_sections = {
        "项目": ["# 项目与推演计划", "## 当前活跃项目"],
        "玫瑰": ["p_rose", "予人玫瑰"],
        "刀模": ["p_diepre", "刀模", "p_huarong", "活字印刷"],
        "架构": ["# 系统架构总览", "调用链路"],
        "skill": ["# Skill库", "PCM"],
        "ulds": ["ULDS", "十一大规律"],
        "碰撞": ["四向碰撞", "认知自洽"],
        "推演": ["推演结论", "自评估"],
    }

    dynamic = []
    matched_any = False
    for keyword, markers in topic_sections.items():
        if keyword in q:
            for m in markers:
                idx = full.find(m)
                if idx != -1:
                    # 取该位置前后800字
                    start = max(0, full.rfind("\n#", 0, idx))
                    end = full.find("\n# ", idx + len(m))
                    chunk = full[start:min(end if end != -1 else start + 800, start + 800)]
                    dynamic.append(chunk)
                    matched_any = True
                    break

    # 无匹配 → 默认项目列表
    if not matched_any:
        for marker in ["# 项目与推演计划", "## 当前活跃项目"]:
            idx = full.find(marker)
            if idx != -1:
                dynamic.append(full[idx:idx + 1200])
                break

    header = full[:200]
    combined = header + "\n\n" + "\n\n".join(fixed) + "\n\n" + "\n\n".join(dynamic)
    return combined[:max_chars]


# ── 延迟加载 Chain Processor ──
_chain = None

def get_chain():
    global _chain
    if _chain is None:
        try:
            from wechat_chain_processor import ChainProcessor
            _chain = ChainProcessor()
            log.info("ChainProcessor 已加载")
        except Exception as e:
            log.warning(f"ChainProcessor 加载失败: {e}, 将使用 Ollama 直答")
    return _chain


# ── 持久化对话记忆 ──
import threading
_MEMORY_FILE = PROJECT_ROOT / "data" / "conversation_memory.jsonl"
_MEMORY_LOCK = threading.Lock()
_RECENT_MEMORY: list = []  # [{"q":...,"a":...,"ts":...}]
_MAX_MEMORY = 50  # 保留最近50轮

def _load_memory():
    global _RECENT_MEMORY
    try:
        if _MEMORY_FILE.exists():
            lines = _MEMORY_FILE.read_text(encoding="utf-8").strip().split("\n")
            _RECENT_MEMORY = [json.loads(l) for l in lines[-_MAX_MEMORY:] if l.strip()]
            log.info(f"[记忆] 加载 {len(_RECENT_MEMORY)} 条历史对话")
    except Exception as e:
        log.warning(f"[记忆] 加载失败: {e}")

def _save_memory(question: str, answer: str):
    with _MEMORY_LOCK:
        entry = {"q": question[:200], "a": answer[:300], "ts": datetime.now().strftime("%m-%d %H:%M")}
        _RECENT_MEMORY.append(entry)
        if len(_RECENT_MEMORY) > _MAX_MEMORY:
            _RECENT_MEMORY[:] = _RECENT_MEMORY[-_MAX_MEMORY:]
        try:
            _MEMORY_FILE.parent.mkdir(exist_ok=True)
            with open(_MEMORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

def _get_memory_context(max_chars: int = 800) -> str:
    """将近期对话记忆格式化为上下文"""
    if not _RECENT_MEMORY:
        return ""
    lines = ["## 近期对话记忆"]
    for m in _RECENT_MEMORY[-8:]:
        lines.append(f"[{m.get('ts','')}] 问: {m['q'][:60]}")
        lines.append(f"  答: {m['a'][:80]}")
    result = "\n".join(lines)
    return result[:max_chars]


def process_message(user_msg: str, user_id: str = "openclaw", context: str = "") -> str:
    """调用本地7步链处理消息，自动注入 AGI 项目上下文 + 对话记忆"""
    # HEARTBEAT过滤: OpenClaw内部心跳不进入推演链
    if "HEARTBEAT" in user_msg or "heartbeat" in user_msg.lower():
        log.info("💓 心跳消息，跳过推演")
        return "heartbeat acknowledged"

    # 通知透传: 不走AI链，直接返回原文
    if "[系统通知" in user_msg:
        # 提取标记行之后的内容
        idx = user_msg.find("[系统通知")
        after_tag = user_msg[idx:]
        raw = after_tag.split("\n", 1)[-1].strip() if "\n" in after_tag else after_tag
        log.info(f"📢 通知透传: {raw[:50]}")
        return raw

    # 主题感知: 让 context 裁剪知道当前问题
    global _last_question
    _last_question = user_msg
    # 大context注入(≤20K) 充分利用200M token配额
    agi_ctx = _get_compact_context(max_chars=20000)
    # 注入对话记忆
    mem_ctx = _get_memory_context()
    full_ctx = agi_ctx
    if mem_ctx:
        full_ctx += "\n\n" + mem_ctx
    if context:
        full_ctx += "\n\n## 当前对话历史\n" + context[-1000:]

    chain = get_chain()
    if chain:
        try:
            result = chain.process(user_msg, context=full_ctx)
            if result and result.final_answer:
                _save_memory(user_msg, result.final_answer)
                return result.final_answer
        except Exception as e:
            log.warning(f"Chain 处理失败: {e}")

    # 降级: 直接调用 Ollama
    try:
        from wechat_chain_processor import _call_ollama
        r = _call_ollama(f"请回答用户问题:\n{user_msg}", max_tokens=2000, temperature=0.7)
        if r.get("success"):
            return r["content"]
    except Exception as e:
        log.warning(f"Ollama 降级也失败: {e}")

    return f"处理失败，请稍后重试。(msg: {user_msg[:30]})"


# ── 安全: 敏感信息过滤 ──
import re as _re

_SENSITIVE_PATTERNS = []

def _build_sensitive_patterns():
    """收集所有可能的 API key 片段用于输出过滤"""
    global _SENSITIVE_PATTERNS
    patterns = []
    # 从环境变量收集
    for k, v in os.environ.items():
        if any(w in k.upper() for w in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'AUTH']) and len(v) > 8:
            patterns.append(v)
    # 从 BACKENDS 配置收集
    try:
        import agi_v13_cognitive_lattice as _agi
        for bk, bv in _agi.BACKENDS.items():
            ak = bv.get('api_key', '')
            if ak and len(ak) > 8 and ak != 'ollama':
                patterns.append(ak)
    except Exception:
        pass
    _SENSITIVE_PATTERNS = [p for p in patterns if p]
    log.info(f"[安全] 已注册 {len(_SENSITIVE_PATTERNS)} 个敏感模式")

def _sanitize_output(text: str) -> str:
    """从输出中移除所有 API key / token 片段"""
    for pat in _SENSITIVE_PATTERNS:
        if pat in text:
            text = text.replace(pat, '***REDACTED***')
        # 也检查部分匹配（key的前16字符）
        if len(pat) > 16 and pat[:16] in text:
            text = text.replace(pat[:16], '***REDACTED***')
    return text

_INJECTION_KEYWORDS = _re.compile(
    r'(忽略.*指令|ignore.*instruction|system.*prompt|api.?key|密钥|token.*secret|'
    r'repeat.*system|打印.*配置|print.*config|输出.*环境变量|show.*env|'
    r'reveal.*password|泄露|dump.*context)',
    _re.IGNORECASE
)

def _is_injection_attempt(msg: str) -> bool:
    """检测 prompt injection 尝试"""
    return bool(_INJECTION_KEYWORDS.search(msg))


class OpenAICompatHandler(BaseHTTPRequestHandler):
    """模拟 OpenAI /v1/chat/completions 接口"""

    def log_message(self, format, *args):
        log.info(f"HTTP {args[0] if args else ''}")

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            self._handle_chat_completion()
        elif self.path == "/v1/context/refresh":
            _refresh_context()
            self._send_json({"status": "ok", "chars": len(_AGI_CONTEXT)})
        elif self.path == "/v1/feedback":
            body = self._read_body()
            problem = body.get("problem", "")
            solution = body.get("solution", "")
            if problem and solution:
                _save_memory(f"[已解决] {problem}", f"[方案] {solution}")
                log.info(f"📚 学习反馈: {problem[:40]} → {solution[:40]}")
                self._send_json({"status": "learned", "memory_size": len(_RECENT_MEMORY)})
            else:
                self._send_json({"error": "need problem and solution"}, 400)
        elif self.path == "/v1/code/execute":
            # 直接执行代码操作
            if not _CODE_AGENT:
                self._send_json({"error": "code agent not loaded"}, 500)
                return
            body = self._read_body()
            actions = body.get("actions", [])
            if not actions:
                # 尝试解析单个action
                if body.get("type"):
                    actions = [body]
            results = []
            for action in actions:
                result = _CODE_AGENT.execute_action(action)
                results.append(result.to_dict())
            self._send_json({"results": results})
        # ── 自主成长 API ──
        elif self.path == "/v1/growth/trigger":
            body = self._read_body()
            try:
                from autonomous_growth import api_trigger_growth
                result = api_trigger_growth(
                    task_type=body.get("type"),
                    title=body.get("title"),
                    priority=body.get("priority", "medium")
                )
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/v1/growth/batch":
            body = self._read_body()
            try:
                from autonomous_growth import api_run_batch
                result = api_run_batch(body.get("max_tasks", 5))
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/v1/growth/pause":
            try:
                from autonomous_growth import api_pause
                self._send_json(api_pause())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/v1/growth/resume":
            try:
                from autonomous_growth import api_resume
                self._send_json(api_resume())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_GET(self):
        if self.path == "/v1/models":
            self._send_json({
                "object": "list",
                "data": [{
                    "id": "agi-chain-v13",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "local",
                }]
            })
        elif self.path == "/health":
            self._send_json({
                "status": "ok",
                "chain": get_chain() is not None,
                "context_chars": len(_AGI_CONTEXT),
                "context_loaded": _CONTEXT_LOADED,
            })
        elif self.path == "/v1/context":
            ctx = _load_agi_context()
            self._send_json({"chars": len(ctx), "context": ctx[:500] + '... (已截断，完整内容仅供内部使用)'})
        elif self.path == "/v1/growth/status":
            try:
                from autonomous_growth import api_get_status
                self._send_json(api_get_status())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)

    def _handle_chat_completion(self):
        body = self._read_body()
        messages = body.get("messages", [])
        stream = body.get("stream", False)

        # 提取用户最后一条消息 + 构建对话历史上下文
        user_msg = ""
        history_lines = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        content = part.get("text", "")
                        break
            if role == "system":
                continue  # system 由 bridge 自己注入
            if role == "user":
                user_msg = content  # 取最后一条 user
                history_lines.append(f"User: {content}")
            elif role == "assistant":
                history_lines.append(f"Assistant: {content}")

        if not user_msg:
            self._send_json({"error": "no user message"}, 400)
            return

        # 对话历史（去掉最后一条，它是当前 user_msg）
        ctx_history = "\n".join(history_lines[:-1]) if len(history_lines) > 1 else ""

        log.info(f"📩 收到: {user_msg[:60]}...")
        _update_last_request()  # 更新最后请求时间，供闲置推演引擎检测

        # 安全检查: prompt injection 检测
        if _is_injection_attempt(user_msg):
            log.warning(f"⚠️ 检测到可疑注入: {user_msg[:40]}")
            reply = "检测到可疑请求，已拦截。如有正当需求请用其他方式表述。"
            self._send_json({
                "id": f"chatcmpl-blocked",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}}]
            })
            return

        # 调用本地链处理
        start = time.time()
        reply = process_message(user_msg, context=ctx_history)
        
        # 代码代理: 检测并执行 AI 响应中的代码操作
        if _CODE_AGENT:
            try:
                actions = parse_code_actions(reply)
                if actions:
                    log.info(f"🔧 检测到 {len(actions)} 个代码操作，执行中...")
                    exec_results = []
                    for action in actions:
                        result = _CODE_AGENT.execute_action(action)
                        exec_results.append(result.to_markdown())
                        log.info(f"  → {action.get('type')}: {'✅' if result.success else '❌'}")
                    # 将执行结果附加到回复
                    reply += "\n\n## 代码执行结果\n" + "\n\n".join(exec_results)
            except Exception as e:
                log.warning(f"代码执行失败: {e}")
        
        reply = _sanitize_output(reply)  # 安全: 过滤密钥
        duration = time.time() - start
        log.info(f"📤 回复({len(reply)}字, {duration:.1f}s): {reply[:60]}...")

        resp_id = f"chatcmpl-{int(time.time())}"

        if stream:
            # SSE 流式响应
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            # 单次发送完整内容
            chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "agi-chain-v13",
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": reply},
                    "finish_reason": None,
                }]
            }
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())

            # 结束标记
            done_chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "agi-chain-v13",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            self.wfile.write(f"data: {json.dumps(done_chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            # 非流式响应
            self._send_json({
                "id": resp_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "agi-chain-v13",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": len(user_msg),
                    "completion_tokens": len(reply),
                    "total_tokens": len(user_msg) + len(reply),
                }
            })


def main():
    port = 9801
    # 启动时预加载 AGI 上下文 + 安全模式 + 对话记忆
    _load_agi_context()
    _build_sensitive_patterns()
    _load_memory()
    server = HTTPServer(("127.0.0.1", port), OpenAICompatHandler)
    log.info(f"OpenClaw Bridge 启动: http://127.0.0.1:{port}")
    log.info(f"  /v1/chat/completions → 本地7步链 + AGI上下文")
    log.info(f"  /v1/models           → 模型列表")
    log.info(f"  /v1/context          → 查看当前注入上下文")
    log.info(f"  /v1/context/refresh  → 刷新上下文")
    log.info(f"  /health              → 健康检查")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Bridge 停止")
        server.server_close()


if __name__ == "__main__":
    main()
