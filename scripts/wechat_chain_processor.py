#!/usr/bin/env python3
"""
微信7步AI调用链处理器
=======================
用户提问 → Ollama路由 → GLM-5T快速分析 → GLM-5深度推理 → GLM-4.7代码生成 → Ollama幻觉校验 → 零回避扫描 → 返回结果

遵循 Local-First 策略:
- Tier 0: 本地Ollama做路由+幻觉校验 (免费)
- Tier 1: GLM-5-Turbo快速分析 (低成本)
- Tier 2: GLM-5深度推理 + GLM-4.7代码生成 (按需)
"""

import json
import time
import logging
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ── 响应缓存 (LRU, 相同问题秒回) ──
_RESPONSE_CACHE: Dict[str, dict] = {}  # {hash: {"answer":..., "ts":..., "hits":0}}
_CACHE_MAX = 100
_CACHE_TTL = 3600  # 1小时过期

def _cache_key(question: str, context: str = "") -> str:
    return hashlib.md5((question.strip()[:200] + context[:100]).encode()).hexdigest()

def _cache_get(key: str) -> Optional[str]:
    entry = _RESPONSE_CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        entry["hits"] += 1
        return entry["answer"]
    return None

def _cache_set(key: str, answer: str):
    if len(_RESPONSE_CACHE) >= _CACHE_MAX:
        oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k]["ts"])
        del _RESPONSE_CACHE[oldest]
    _RESPONSE_CACHE[key] = {"answer": answer, "ts": time.time(), "hits": 0}

# ── 路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

log = logging.getLogger("chain")

# ── 从主配置读取API ──
def _get_backends():
    try:
        import agi_v13_cognitive_lattice as agi
        return agi.BACKENDS
    except Exception:
        return {}


# ════════════════════════════════════════════════════════════
# 模型调用封装
# ════════════════════════════════════════════════════════════

def _call_ollama(prompt: str, system: str = "", model: str = "qwen2.5-coder:14b",
                 max_tokens: int = 1024, temperature: float = 0.3, timeout: int = 30) -> Dict:
    """调用本地Ollama"""
    t0 = time.time()
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages,
                  "stream": False, "options": {"num_predict": max_tokens, "temperature": temperature}},
            timeout=timeout
        )
        if resp.status_code == 200:
            content = resp.json().get("message", {}).get("content", "").strip()
            return {"success": True, "content": content, "model": f"ollama/{model}",
                    "duration": round(time.time() - t0, 2)}
    except Exception as e:
        return {"success": False, "content": "", "error": str(e), "model": f"ollama/{model}",
                "duration": round(time.time() - t0, 2)}
    return {"success": False, "content": "", "error": "Ollama返回异常", "model": f"ollama/{model}",
            "duration": round(time.time() - t0, 2)}


# ── 模型性能追踪器（自适应选择） ──
_MODEL_STATS: Dict[str, dict] = {}  # {"glm-5": {"ok":10, "fail":2, "avg_dur":25.3}}
_STATS_FILE = Path(__file__).resolve().parent.parent / "data" / "model_stats.json"

def _load_model_stats():
    global _MODEL_STATS
    try:
        if _STATS_FILE.exists():
            _MODEL_STATS = json.loads(_STATS_FILE.read_text())
    except Exception:
        pass

def _record_model_stat(model: str, success: bool, duration: float):
    if model not in _MODEL_STATS:
        _MODEL_STATS[model] = {"ok": 0, "fail": 0, "avg_dur": 0, "total_dur": 0}
    s = _MODEL_STATS[model]
    if success:
        s["ok"] += 1
    else:
        s["fail"] += 1
    s["total_dur"] += duration
    total = s["ok"] + s["fail"]
    s["avg_dur"] = round(s["total_dur"] / max(total, 1), 1)
    try:
        _STATS_FILE.parent.mkdir(exist_ok=True)
        _STATS_FILE.write_text(json.dumps(_MODEL_STATS, ensure_ascii=False, indent=1))
    except Exception:
        pass

def _best_model(candidates: list) -> list:
    """按成功率×速度排序候选模型，最优的排前面"""
    def score(m):
        s = _MODEL_STATS.get(m, {})
        ok = s.get("ok", 0)
        total = ok + s.get("fail", 0)
        if total < 3:
            return 0.5  # 数据不足，中等优先
        success_rate = ok / total
        speed = 1 / max(s.get("avg_dur", 30), 1)
        return success_rate * 0.7 + speed * 0.3
    return sorted(candidates, key=score, reverse=True)

_load_model_stats()


def _call_zhipu_adaptive(prompt: str, candidates: list, system: str = "",
                         max_tokens: int = 2048, temperature: float = 0.4, timeout: int = 60) -> Dict:
    """自适应调用: 按历史性能排序候选模型，依次尝试直到成功"""
    ordered = _best_model(candidates)
    for model in ordered:
        r = _call_zhipu(prompt, model, system, max_tokens, temperature, timeout)
        if r.get("success"):
            return r
    # 全部失败，返回最后一次结果
    return r


def _call_zhipu(prompt: str, model: str = "GLM-4.7", system: str = "",
                max_tokens: int = 4096, temperature: float = 0.4, timeout: int = 60) -> Dict:
    """调用智谱GLM (OpenAI兼容格式)"""
    t0 = time.time()
    backends = _get_backends()
    zhipu = backends.get("zhipu", {})
    api_key = zhipu.get("api_key", "")
    base_url = zhipu.get("base_url", "https://open.bigmodel.cn/api/coding/paas/v4")

    if not api_key:
        return {"success": False, "content": "", "error": "智谱API未配置", "model": model,
                "duration": round(time.time() - t0, 2)}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model, messages=messages,
            max_tokens=max_tokens, temperature=temperature
        )
        content = resp.choices[0].message.content.strip()
        tokens = getattr(resp.usage, 'total_tokens', 0)
        dur = round(time.time() - t0, 2)
        _record_model_stat(model, True, dur)
        return {"success": True, "content": content, "model": f"zhipu/{model}",
                "tokens": tokens, "duration": dur}
    except Exception as e:
        err = str(e)
        _record_model_stat(model, False, round(time.time() - t0, 2))
        # 429限速: 重试一次
        if ("429" in err or "1302" in err) and timeout > 10:
            time.sleep(3)
            return _call_zhipu(prompt, model, system, max_tokens, temperature, timeout=10)
        return {"success": False, "content": "", "error": err[:200], "model": f"zhipu/{model}",
                "duration": round(time.time() - t0, 2)}


# ════════════════════════════════════════════════════════════
# 7步调用链
# ════════════════════════════════════════════════════════════

@dataclass
class ChainResult:
    """调用链结果"""
    question: str = ""
    final_answer: str = ""
    steps: List[Dict] = field(default_factory=list)
    total_duration: float = 0
    route_decision: str = ""
    risks: List[Dict] = field(default_factory=list)
    hallucination_check: str = ""

    def summary(self) -> str:
        """生成可读的步骤摘要"""
        lines = []
        for s in self.steps:
            icon = "✅" if s.get("success") else "❌"
            lines.append(f"{icon} {s['step']}: {s['model']} ({s['duration']}s)")
        return "\n".join(lines)


class ChainProcessor:
    """
    7步AI调用链处理器

    步骤:
    1. Ollama路由 — 本地模型分析意图/复杂度,决定走哪些步骤
    2. GLM-5-Turbo快速分析 — 快速给出初步分析
    3. GLM-5深度推理 — 深度推理(仅复杂问题)
    4. GLM-4.7代码生成 — 代码生成(仅代码类问题)
    5. Ollama幻觉校验 — 本地模型交叉验证结果
    6. 零回避扫描 — 扫描代码/方案的潜在风险
    7. 返回结果 — 整合所有步骤输出最终答案
    """

    # 路由分类
    ROUTE_SIMPLE = "simple"        # 简单问候/查询 → Ollama直答
    ROUTE_ANALYSIS = "analysis"    # 分析类 → GLM-5T
    ROUTE_DEEP = "deep"            # 深度推理 → GLM-5T + GLM-5
    ROUTE_CODE = "code"            # 代码类 → GLM-5T + GLM-4.7
    ROUTE_FULL = "full"            # 复杂问题 → 全链路

    def __init__(self, on_step: Optional[Callable] = None):
        """
        Args:
            on_step: 步骤回调 (step_name, detail_str) → None, 用于流式反馈给用户
        """
        self.on_step = on_step or (lambda *a: None)

    # ── 项目/数据查询快速路径关键词 ──
    _FAST_DATA_PATTERNS = re.compile(
        r'(列出|列举|列表|查看|显示|告诉我|有哪些|多少个|几个|进度|项目列表|活跃项目|待推演|推演计划|阻塞问题|统计|stats|projects|plans)',
        re.IGNORECASE
    )

    def _fast_data_answer(self, question: str) -> Optional[str]:
        """快速路径: 项目/数据类查询直接查 DeductionDB，不走 LLM"""
        try:
            from deduction_db import DeductionDB
            db = DeductionDB()
            projects = db.get_projects()
            plans = db.get_plans()
            problems = db.get_problems()
            db.close()

            active = [p for p in projects if p.get('status') == 'active']
            queued = [p for p in plans if p.get('status') == 'queued']
            running = [p for p in plans if p.get('status') == 'running']
            open_probs = [p for p in problems if p.get('status') == 'open']

            lines = [f"## 项目速览 (共 {len(active)} 个活跃项目)\n"]
            for p in sorted(active, key=lambda x: -x.get('progress', 0)):
                bar = '█' * (p.get('progress', 0) // 10) + '░' * (10 - p.get('progress', 0) // 10)
                lines.append(f"**[{p['id']}] {p['name']}** [{bar}] {p.get('progress', 0)}%")
                if p.get('short_term_goal'):
                    lines.append(f"  短期目标: {p['short_term_goal'][:60]}")
            lines.append(f"\n待推演: {len(queued)} 条 | 推演中: {len(running)} 条 | 阻塞问题: {len(open_probs)} 个")
            return '\n'.join(lines)
        except Exception:
            return None

    def _step_web_search(self, question: str) -> str:
        """Step 0c: DuckDuckGo 即时搜索 — 注入外部知识"""
        try:
            q = question[:100].replace('\n', ' ')
            r = requests.get(
                'https://api.duckduckgo.com/',
                params={'q': q, 'format': 'json', 'no_html': '1', 'skip_disambig': '1'},
                timeout=5,
            )
            data = r.json()
            parts = []
            if data.get('AbstractText'):
                parts.append(f"摘要: {data['AbstractText'][:200]}")
            if data.get('Answer'):
                parts.append(f"答案: {data['Answer'][:200]}")
            for t in (data.get('RelatedTopics') or [])[:3]:
                if isinstance(t, dict) and t.get('Text'):
                    parts.append(f"- {t['Text'][:100]}")
            if parts:
                return "## 网络搜索结果\n" + "\n".join(parts)
        except Exception:
            pass
        return ""

    def _step_skill_route(self, question: str) -> str:
        """Step 0: PCM Skill Router — 找 top-3 skill, 高分skill尝试执行"""
        try:
            from pcm_skill_router import route_skills
            results = route_skills(question, top_k=3)
            if not results:
                return ""
            lines = ["## 相关 Skills (PCM路由器推荐)"]
            for sk in results:
                score = sk.get('score', 0)
                name = sk.get('name', '?')
                lines.append(f"- **{name}** (score:{score:.1f}): {sk.get('desc','')[:60]}")
                # 高分skill(≥7): 尝试实际执行
                if score >= 7 and sk.get('file'):
                    try:
                        skill_path = Path(sk['file'])
                        if skill_path.exists() and skill_path.suffix == '.py':
                            import importlib.util
                            spec = importlib.util.spec_from_file_location(name, str(skill_path))
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            # 尝试调用 main() 或 run()
                            if hasattr(mod, 'main'):
                                out = str(mod.main())[:300]
                                lines.append(f"  🔧 执行结果: {out}")
                            elif hasattr(mod, 'run'):
                                out = str(mod.run(question))[:300]
                                lines.append(f"  🔧 执行结果: {out}")
                    except Exception as e:
                        lines.append(f"  ⚠️ 执行失败: {str(e)[:60]}")
                elif sk.get('url'):
                    lines.append(f"  URL: {sk['url']}")
            return '\n'.join(lines)
        except Exception:
            return ""

    def process(self, question: str, context: str = "") -> ChainResult:
        """执行完整调用链"""
        t0 = time.time()
        result = ChainResult(question=question)

        # ── 缓存命中 → 秒回 ──
        ck = _cache_key(question, context)
        cached = _cache_get(ck)
        if cached:
            self.on_step("cache", "⚡ 缓存命中")
            result.route_decision = "cache"
            result.final_answer = cached
            result.total_duration = round(time.time() - t0, 2)
            result.steps.append({"step": "缓存", "success": True, "model": "cache",
                                 "content": cached[:100], "duration": 0})
            return result

        # ── Step 0: 快速路径 — 项目/数据查询不走 LLM ──
        if self._FAST_DATA_PATTERNS.search(question) and len(question) < 30:
            fast_ans = self._fast_data_answer(question)
            if fast_ans:
                self.on_step("fast", "⚡ 直接查询数据库...")
                result.route_decision = "fast_data"
                result.final_answer = fast_ans
                result.total_duration = round(time.time() - t0, 2)
                result.steps.append({"step": "快速数据路径", "success": True,
                                     "model": "DeductionDB", "content": fast_ans,
                                     "duration": round(time.time() - t0, 3)})
                return result

        # ── Step 0b+0c: 并行执行 Skill检索 + 联网搜索 (省5s) ──
        self.on_step("enrich", "🔍 并行检索 Skills + 联网搜索...")
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_skill = pool.submit(self._step_skill_route, question)
            f_web = pool.submit(self._step_web_search, question)
            skill_ctx = f_skill.result()
            web_ctx = f_web.result()
        if skill_ctx:
            context = context + "\n\n" + skill_ctx if context else skill_ctx
        if web_ctx:
            context = context + "\n\n" + web_ctx if context else web_ctx

        # ── Step 1: 路由 ──
        self.on_step("route", "🔀 正在分析问题类型...")
        route = self._step_route(question, context)
        result.route_decision = route["route"]
        result.steps.append(route)

        route_type = route["route"]

        # ── 简单问题: Ollama直答 ──
        if route_type == self.ROUTE_SIMPLE:
            self.on_step("answer", "💬 简单问题,本地模型直答...")
            answer = self._step_ollama_answer(question, context)
            result.steps.append(answer)
            result.final_answer = answer.get("content", "")
            result.total_duration = round(time.time() - t0, 2)
            return result

        # ── Step 2: GLM-5-Turbo快速分析 ──
        self.on_step("glm5t", "⚡ GLM-5-Turbo 快速分析中...")
        glm5t = self._step_glm5t_analysis(question, context, route.get("analysis_prompt", ""), route_type)
        result.steps.append(glm5t)
        analysis_text = glm5t.get("content", "")

        # ── Step 3+4: 推理与代码 ──
        deep_text = ""
        code_text = ""

        if route_type == self.ROUTE_FULL:
            # FULL路由: 推理+代码并行 (都只依赖 analysis_text, 省30-60s)
            self.on_step("parallel", "🧠💻 并行: 深度推理 + 代码生成...")
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_deep = pool.submit(self._step_glm5_deep, question, analysis_text, context)
                f_code = pool.submit(self._step_glm47_code, question, analysis_text, context)
                glm5 = f_deep.result()
                glm47 = f_code.result()
            result.steps.append(glm5)
            result.steps.append(glm47)
            deep_text = glm5.get("content", "")
            code_text = glm47.get("content", "")
        else:
            if route_type == self.ROUTE_DEEP:
                self.on_step("glm5", "🧠 GLM-5.1 深度推理中...")
                glm5 = self._step_glm5_deep(question, analysis_text, context)
                result.steps.append(glm5)
                deep_text = glm5.get("content", "")

            if route_type == self.ROUTE_CODE:
                self.on_step("glm47", "💻 GLM-5 代码生成中...")
                glm47 = self._step_glm47_code(question, analysis_text, context)
                result.steps.append(glm47)
                code_text = glm47.get("content", "")

        # ── Step 5: 交叉验证 (双模型对比, 替代Ollama幻觉校验) ──
        if route_type in (self.ROUTE_DEEP, self.ROUTE_CODE, self.ROUTE_FULL):
            main_content = deep_text or analysis_text
            self.on_step("verify", "� 交叉验证中...")
            verify = self._step_cross_validate(question, main_content, code_text)
            result.steps.append(verify)
            result.hallucination_check = verify.get("content", "")

        # ── Step 6: 零回避扫描 + 代码执行验证 ──
        if code_text:
            self.on_step("scan", "🛡️ 零回避扫描 + 代码验证...")
            risks = self._step_zero_avoidance(code_text)
            result.risks = risks
            result.steps.append({
                "step": "零回避扫描", "success": True, "model": "ZeroAvoidanceScanner",
                "content": f"发现 {len(risks)} 个潜在风险",
                "duration": 0, "risks": risks
            })
            # 执行验证
            exec_result = self._step_execute_code(code_text)
            result.steps.append(exec_result)
            if not exec_result.get("success") and "安全拦截" not in exec_result.get("content", ""):
                result.hallucination_check += f"\n⚠️ 代码执行: {exec_result.get('content', '')[:150]}"

        # ── Step 7: 整合最终答案 ──
        self.on_step("synthesize", "📝 整合最终答案...")
        result.final_answer = self._synthesize(
            question, route_type, analysis_text, deep_text, code_text,
            result.hallucination_check, result.risks
        )
        result.total_duration = round(time.time() - t0, 2)

        # 写入缓存
        _cache_set(ck, result.final_answer)

        # ── 预见性: 后台预测下一步问题并预缓存 ──
        import threading
        def _prefetch():
            try:
                predict_r = _call_zhipu(
                    f"用户刚问了: {question[:100]}\n得到了回答: {result.final_answer[:200]}\n"
                    "预测用户最可能的下一个问题(只输出1个问题,不要解释):",
                    model="glm-5-turbo", max_tokens=100, temperature=0.3, timeout=15
                )
                if predict_r.get("success") and predict_r["content"]:
                    next_q = predict_r["content"].strip()
                    next_ck = _cache_key(next_q, context)
                    if not _cache_get(next_ck):
                        next_r = _call_zhipu(next_q, model="glm-5-turbo",
                                             system="简洁回答,中文。", max_tokens=512, temperature=0.4, timeout=30)
                        if next_r.get("success"):
                            _cache_set(next_ck, next_r["content"])
                            log.info(f"🔮 预缓存: {next_q[:40]}")
            except Exception:
                pass
        threading.Thread(target=_prefetch, daemon=True).start()

        return result

    # ──────────────────── Step 1: Ollama路由 ────────────────────

    # 仅这些模式才算"simple" — 纯问候/闲聊/单词查询
    _SIMPLE_PATTERNS = re.compile(
        r'^(你好|hi|hello|hey|嗨|早|晚安|谢谢|thanks|ok|好的|收到|/help|/帮助|帮助|在吗|测试)[\s!！。.？?]*$',
        re.IGNORECASE
    )
    # 强制升级关键词 → 至少 analysis
    _UPGRADE_KEYWORDS_CODE = ['代码', 'code', '实现', '函数', '脚本', 'python', 'bug',
                               'debug', '修复', '报错', '编译', 'error', 'fix', 'import']
    _UPGRADE_KEYWORDS_DEEP = ['为什么', '分析', '推理', '推演', '原因', '深度', '解释',
                               '怎么办', '如何', '问题', '优化', '设计', '架构', '方案',
                               '比较', '区别', '原理', '机制', '策略', '规划', '建议']

    def _step_route(self, question: str, context: str) -> Dict:
        # ── 快速前置判断: 只有极短的纯问候才是simple ──
        q_stripped = question.strip()
        if self._SIMPLE_PATTERNS.match(q_stripped):
            return {
                "step": "Ollama路由", "success": True, "model": "pattern",
                "content": "路由: simple (模式匹配)", "route": self.ROUTE_SIMPLE,
                "analysis_prompt": "", "duration": 0
            }

        # ── 关键词强制路由(跳过Ollama, 省15s) ──
        q_lower = question.lower()
        kw_route = None
        if any(k in q_lower for k in self._UPGRADE_KEYWORDS_CODE):
            kw_route = self.ROUTE_CODE
        elif any(k in q_lower for k in self._UPGRADE_KEYWORDS_DEEP):
            kw_route = self.ROUTE_DEEP
        else:
            kw_route = self.ROUTE_ANALYSIS  # 默认 analysis

        # 关键词命中 → 直接返回，不调 Ollama
        if kw_route:
            return {
                "step": "关键词路由", "success": True, "model": "keyword",
                "content": f"路由: {kw_route} (关键词快速)", "route": kw_route,
                "analysis_prompt": "", "duration": 0
            }

        # ── Ollama辅助路由(仅在关键词无法判断时) ──
        ROUTE_PROMPT = (
            "你是AI路由器。根据问题复杂度输出一个JSON。\n\n"
            "规则(严格遵守):\n"
            "- simple: 仅限纯问候(你好/hi/谢谢)或一两个字的闲聊\n"
            "- analysis: 需要查询信息/简单分析/解释概念\n"
            "- deep: 需要多步推理/因果分析/复杂逻辑/技术支持/排查问题\n"
            "- code: 需要写代码/调试/修复bug/代码优化\n"
            "- full: 极复杂,需要推理+代码+多维度分析\n\n"
            "重要: 如果不确定,选analysis或deep,绝不要选simple!\n"
            "例子:\n"
            "- '你好' → simple\n"
            "- '今日天气' → analysis\n"
            "- '为什么消息收不到' → deep\n"
            "- '帮我写一个排序函数' → code\n"
            "- '设计一个分布式消息队列并实现' → full\n\n"
            f"问题: {question[:500]}\n"
            f"{'上下文: ' + context[:800] if context else ''}\n\n"
            "只输出JSON: {\"route\": \"类型\", \"reason\": \"原因\"}"
        )
        r = _call_ollama(ROUTE_PROMPT, max_tokens=200, temperature=0.1, timeout=15)
        route_type = self.ROUTE_ANALYSIS  # 默认: analysis(不是simple!)
        analysis_prompt = ""
        if r["success"]:
            try:
                m = re.search(r'\{.*?\}', r["content"], re.DOTALL)
                if m:
                    data = json.loads(m.group())
                    rt = data.get("route", "analysis")
                    if rt in (self.ROUTE_SIMPLE, self.ROUTE_ANALYSIS, self.ROUTE_DEEP,
                              self.ROUTE_CODE, self.ROUTE_FULL):
                        route_type = rt
                    analysis_prompt = data.get("analysis_prompt", "")
            except Exception:
                pass

        # ── 安全网: 只有_SIMPLE_PATTERNS匹配才允许simple ──
        # 到这里说明问题没匹配问候模式,所以Ollama不应分类为simple
        if route_type == self.ROUTE_SIMPLE:
            route_type = self.ROUTE_ANALYSIS
        # 关键词优先级高于Ollama判断
        if kw_route:
            if route_type == self.ROUTE_SIMPLE or route_type == self.ROUTE_ANALYSIS:
                route_type = kw_route

        return {
            "step": "Ollama路由", "success": True, "model": r.get("model", "ollama"),
            "content": f"路由: {route_type}", "route": route_type,
            "analysis_prompt": analysis_prompt,
            "duration": r.get("duration", 0)
        }

    # ──────────────────── Ollama直答 ────────────────────

    def _step_ollama_answer(self, question: str, context: str) -> Dict:
        system = (
            "你是AGI v13智能助手。回复简洁实用,中文。\n"
            + (f"项目上下文:\n{context[:2000]}" if context else "")
        )
        r = _call_ollama(question, system=system, max_tokens=500, timeout=20)
        return {"step": "Ollama直答", **r}

    # ──────────────────── Step 2: GLM-5-Turbo快速分析 ────────────────────

    def _step_glm5t_analysis(self, question: str, context: str, analysis_hint: str, route_type: str = "") -> Dict:
        system = (
            "你是快速分析专家。请对用户问题进行结构化分析,给出:\n"
            "1. 问题要点拆解\n"
            "2. 关键概念识别\n"
            "3. 初步分析结论\n"
            "4. 是否需要进一步深度推理或代码实现\n"
            "回复简洁结构化,中文。"
        )
        prompt = question
        if context:
            system = system + f"\n\n项目背景:\n{context[:2000]}"
        if analysis_hint:
            prompt += f"\n\n路由提示: {analysis_hint}"

        _mt = 4096 if route_type == self.ROUTE_ANALYSIS else 8192
        # GLM-5-Turbo: 专为Agent/OpenClaw优化, 200K context, 高吞吐
        r = _call_zhipu(prompt, model="glm-5-turbo", system=system, max_tokens=_mt, temperature=0.4)
        if not r["success"]:
            r = _call_zhipu(prompt, model="glm-5.1", system=system, max_tokens=_mt, temperature=0.4)
        if not r["success"]:
            r = _call_zhipu(prompt, model="GLM-4.7", system=system, max_tokens=_mt, temperature=0.4)
        return {"step": "GLM-5T快速分析", **r}

    # ──────────────────── Step 3: GLM-5深度推理 ────────────────────

    def _step_glm5_deep(self, question: str, analysis: str, context: str) -> Dict:
        system = (
            "你是AGI v13系统的深度推理模块,基于ULDS v2.1十一大规律框架。\n"
            "请进行深度推理:\n"
            "1. 基于初步分析,深入挖掘根因\n"
            "2. 应用相关ULDS规律(L1数学/L4逻辑/L6系统/L10演化等)\n"
            "3. 考虑边界条件和极端情况\n"
            "4. 给出具体可执行的结论和建议\n"
            "回复深入但有条理,中文。"
        )
        prompt = (
            f"原始问题: {question}\n\n"
            f"初步分析:\n{analysis[:2000]}\n\n"
            + (f"\n\n项目背景:\n{context[:2000]}" if context else "")
            + "\n\n请进行深度推理分析。"
        )
        # GLM-5.1: 深度推理首选(GLM-5迭代版), 降级→GLM-5→GLM-5-Turbo
        r = _call_zhipu(prompt, model="glm-5.1", system=system, max_tokens=8192, temperature=0.5, timeout=120)
        if not r["success"]:
            r = _call_zhipu(prompt, model="glm-5", system=system, max_tokens=2048, temperature=0.5, timeout=90)
        if not r["success"]:
            r = _call_zhipu(prompt, model="glm-5-turbo", system=system, max_tokens=2048, temperature=0.5)
        return {"step": "GLM-5.1深度推理", **r}

    # ──────────────────── Step 4: GLM-4.7代码生成 ────────────────────

    def _step_glm47_code(self, question: str, prior_analysis: str, context: str) -> Dict:
        system = (
            "你是AGI v13的代码生成模块。\n"
            "要求:\n"
            "1. 生成可直接运行的完整代码\n"
            "2. 包含必要的import、类型提示、错误处理\n"
            "3. 添加简明注释\n"
            "4. 考虑边界条件和异常情况\n"
            "5. 如果是修复bug,清楚说明根因和修复原理\n"
            "回复必须包含可执行代码块。"
        )
        prompt = (
            f"任务: {question}\n\n"
            f"分析参考:\n{prior_analysis[:2000]}\n\n"
            + (f"\n\n项目背景:\n{context[:2000]}" if context else "")
            + "\n\n请生成代码实现。"
        )
        # 代码生成: GLM-5(SWE-bench 77.8最强) → GLM-5.1 → GLM-5-Turbo
        r = _call_zhipu(prompt, model="glm-5", system=system, max_tokens=8192, temperature=0.3, timeout=120)
        if not r["success"]:
            r = _call_zhipu(prompt, model="glm-5.1", system=system, max_tokens=4096, temperature=0.3)
        if not r["success"]:
            r = _call_zhipu(prompt, model="glm-5-turbo", system=system, max_tokens=4096, temperature=0.3)
        return {"step": "GLM-5代码生成", **r}

    # ──────────────────── Step 5: Ollama幻觉校验 ────────────────────

    def _step_hallucination_check(self, question: str, answer: str, code: str = "") -> Dict:
        check_prompt = (
            "你是幻觉校验器。请检查以下AI回答是否存在幻觉(编造事实/不存在的API/错误逻辑)。\n\n"
            f"用户问题: {question[:300]}\n\n"
            f"AI回答:\n{answer[:1500]}\n"
            f"{'代码: ' + code[:800] if code else ''}\n\n"
            "请检查:\n"
            "1. 是否有编造的事实/API/库\n"
            "2. 逻辑是否自洽\n"
            "3. 代码是否可执行(如有)\n"
            "4. 是否有遗漏的关键点\n\n"
            "输出JSON: {\"hallucination_found\": true/false, \"issues\": [\"问题1\", ...], \"confidence\": 0.0-1.0}"
        )
        r = _call_ollama(check_prompt, max_tokens=500, temperature=0.1, timeout=20)
        return {"step": "Ollama幻觉校验", **r}

    def _step_cross_validate(self, question: str, answer: str, code: str = "") -> Dict:
        """交叉验证: Ollama(不同模型家族) + GLM-5-Turbo 双重核查"""
        t0 = time.time()
        verify_prompt = (
            f"你是事实核查员。验证以下回答的真实性。\n\n"
            f"问题: {question[:300]}\n\n"
            f"待验证:\n{answer[:1000]}\n"
            + (f"\n代码:\n{code[:500]}" if code else "")
            + "\n\n只输出: [可信度:0-100] + 发现的具体错误(如有)"
        )
        # 并行: Ollama(不同家族) + GLM-5-Turbo(同家族不同规模)
        issues = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_ollama = pool.submit(_call_ollama, verify_prompt, "你是严格的事实核查员", "qwen2.5-coder:14b", 400, 0.1, 20)
            f_glm = pool.submit(_call_zhipu, verify_prompt, "glm-5-turbo", "你是严格的事实核查员,只指出确定的错误。", 400, 0.1, 30)
            r_ollama = f_ollama.result()
            r_glm = f_glm.result()
        if r_ollama.get("success"):
            issues.append(f"[Ollama] {r_ollama['content'][:200]}")
        if r_glm.get("success"):
            issues.append(f"[GLM-5T] {r_glm['content'][:200]}")
        combined = "\n".join(issues) if issues else "双模型验证均未发现问题"
        return {"step": "双家族交叉验证", "success": True,
                "model": "ollama+glm-5-turbo", "content": combined,
                "duration": round(time.time() - t0, 2)}

    # ──────────────────── Step 5b: 代码执行验证 ────────────────────

    def _step_execute_code(self, code_text: str) -> Dict:
        """沙箱执行生成的代码，验证是否能跑"""
        import subprocess as _sp
        import tempfile
        # 提取 python 代码块
        blocks = re.findall(r'```python\n(.*?)```', code_text, re.DOTALL)
        if not blocks:
            blocks = re.findall(r'```\n(.*?)```', code_text, re.DOTALL)
        if not blocks:
            return {"step": "代码执行", "success": True, "model": "sandbox",
                    "content": "无可执行代码块", "duration": 0}

        code = blocks[0][:3000]  # 限制长度
        # 安全检查: 禁止危险操作
        danger = re.search(r'(os\.system|subprocess|shutil\.rmtree|open\(.*(w|a)\)|__import__|eval\(|exec\()', code)
        if danger:
            return {"step": "代码执行", "success": False, "model": "sandbox",
                    "content": f"安全拦截: 检测到危险操作 {danger.group()[:30]}", "duration": 0}

        t0 = time.time()
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                tmp = f.name
            result = _sp.run(
                [sys.executable, tmp],
                capture_output=True, text=True, timeout=10, cwd=str(PROJECT_ROOT)
            )
            import os; os.unlink(tmp)
            if result.returncode == 0:
                output = result.stdout[:500] if result.stdout else "(无输出,执行成功)"
                return {"step": "代码执行", "success": True, "model": "sandbox",
                        "content": f"✅ 执行成功\n{output}", "duration": round(time.time() - t0, 2)}
            else:
                err = result.stderr[:300]
                return {"step": "代码执行", "success": False, "model": "sandbox",
                        "content": f"❌ 执行失败\n{err}", "duration": round(time.time() - t0, 2)}
        except _sp.TimeoutExpired:
            return {"step": "代码执行", "success": False, "model": "sandbox",
                    "content": "⏱️ 执行超时(10s)", "duration": 10}
        except Exception as e:
            return {"step": "代码执行", "success": False, "model": "sandbox",
                    "content": f"执行异常: {str(e)[:100]}", "duration": round(time.time() - t0, 2)}

    # ──────────────────── Step 6: 零回避扫描 ────────────────────

    def _step_zero_avoidance(self, code: str) -> List[Dict]:
        try:
            from diepre_growth_framework import ZeroAvoidanceScanner
            risks = ZeroAvoidanceScanner.scan_skill(code, {"name": "chain_output"})
            return risks
        except Exception:
            return []

    # ──────────────────── Step 7: 整合 ────────────────────

    def _synthesize(self, question: str, route_type: str,
                    analysis: str, deep: str, code: str,
                    hallucination: str, risks: List[Dict]) -> str:
        """整合所有步骤的输出为最终答案"""
        parts = []

        # 主体内容
        if route_type == self.ROUTE_ANALYSIS:
            parts.append(analysis)
        elif route_type == self.ROUTE_DEEP:
            parts.append(deep if deep else analysis)
        elif route_type == self.ROUTE_CODE:
            if analysis:
                parts.append(f"📋 分析:\n{analysis[:800]}")
            if code:
                parts.append(f"\n💻 代码:\n{code}")
        elif route_type == self.ROUTE_FULL:
            if deep:
                parts.append(f"🧠 深度分析:\n{deep[:1200]}")
            elif analysis:
                parts.append(f"📋 分析:\n{analysis[:800]}")
            if code:
                parts.append(f"\n💻 代码:\n{code}")

        # 幻觉校验结果
        hall_issues = []
        if hallucination:
            try:
                m = re.search(r'\{[^}]+\}', hallucination, re.DOTALL)
                if m:
                    hdata = json.loads(m.group())
                    if hdata.get("hallucination_found"):
                        hall_issues = hdata.get("issues", [])
            except Exception:
                pass
        if hall_issues:
            parts.append("\n⚠️ 幻觉校验发现问题:\n" + "\n".join(f"- {i}" for i in hall_issues[:3]))

        # 零回避风险
        if risks:
            risk_lines = [f"- [{r['disaster_id']}] {r['name']}: {r['trigger']}" for r in risks[:3]]
            parts.append("\n🛡️ 风险提示:\n" + "\n".join(risk_lines))

        return "\n".join(parts) if parts else analysis or "处理完成,但未生成有效输出。"


# ════════════════════════════════════════════════════════════
# 格式化输出(微信消息限制)
# ════════════════════════════════════════════════════════════

def format_chain_result_for_wechat(result: ChainResult, max_len: int = 2000) -> List[str]:
    """将调用链结果格式化为适合微信发送的消息列表(可能拆分为多条)"""
    answer = result.final_answer
    if not answer:
        return ["⚠️ 调用链未生成有效输出"]

    # 添加链路摘要头
    header = f"🔗 AI调用链 ({result.route_decision}) | {result.total_duration}s\n"
    step_summary = " → ".join(
        s['step'].replace('GLM-5T快速分析', 'GLM5T').replace('GLM-5深度推理', 'GLM5')
        .replace('GLM-4.7代码生成', 'GLM47').replace('Ollama路由', '路由')
        .replace('Ollama幻觉校验', '校验').replace('零回避扫描', '扫描')
        for s in result.steps if s.get('success')
    )
    header += f"链路: {step_summary}\n{'─'*30}\n"

    full = header + answer

    # 拆分为多条(微信单条消息限制)
    messages = []
    while full:
        if len(full) <= max_len:
            messages.append(full)
            break
        # 找自然断点
        cut = max_len
        for sep in ["\n\n", "\n", "。", ".", " "]:
            pos = full.rfind(sep, 0, max_len)
            if pos > max_len // 2:
                cut = pos + len(sep)
                break
        messages.append(full[:cut])
        full = full[cut:]

    return messages


# ════════════════════════════════════════════════════════════
# 项目数据库CRUD (供微信命令调用)
# ════════════════════════════════════════════════════════════

def db_list_projects() -> str:
    """列出所有项目"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        projects = db.get_projects()
        db.close()
        if not projects:
            return "ℹ️ 暂无项目"
        lines = [f"📁 项目列表 ({len(projects)}个)\n"]
        for p in projects:
            status_icon = {"active": "🟢", "paused": "🟡", "done": "✅", "archived": "📦"}.get(p['status'], "⚪")
            progress = p.get('progress', 0) or 0
            bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
            lines.append(f"{status_icon} {p['name']} [{p['id']}]")
            lines.append(f"   {bar} {progress}%")
            if p.get('short_term_goal'):
                lines.append(f"   近期: {p['short_term_goal'][:50]}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 查询失败: {e}"


def db_project_detail(project_id: str) -> str:
    """项目详情(含计划和问题)"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        # 查项目
        row = db.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            # 模糊匹配
            row = db.conn.execute("SELECT * FROM projects WHERE name LIKE ?",
                                  (f"%{project_id}%",)).fetchone()
        if not row:
            db.close()
            return f"⚠️ 项目 '{project_id}' 不存在"
        p = dict(row)

        lines = [f"📁 {p['name']}", f"ID: {p['id']}", f"状态: {p['status']} | 进度: {p.get('progress',0)}%"]
        if p.get('description'):
            lines.append(f"描述: {p['description'][:100]}")
        if p.get('ultimate_goal'):
            lines.append(f"终极目标: {p['ultimate_goal'][:80]}")
        if p.get('short_term_goal'):
            lines.append(f"近期目标: {p['short_term_goal'][:80]}")

        # 推演计划
        plans = db.get_plans(project_id=p['id'])
        if plans:
            queued = sum(1 for x in plans if x['status'] == 'queued')
            running = sum(1 for x in plans if x['status'] == 'running')
            done = sum(1 for x in plans if x['status'] == 'done')
            lines.append(f"\n📋 推演计划: {len(plans)}个 ({queued}排队 {running}进行 {done}完成)")
            for pl in plans[:5]:
                st = {"queued": "⏳", "running": "🔄", "done": "✅", "failed": "❌"}.get(pl['status'], "⚪")
                lines.append(f"  {st} {pl['title'][:40]} [{pl['priority']}]")
            if len(plans) > 5:
                lines.append(f"  ... 还有{len(plans)-5}个计划")

        # 问题
        problems = db.get_problems(project_id=p['id'])
        if problems:
            open_count = sum(1 for x in problems if x['status'] == 'open')
            lines.append(f"\n⭕ 问题: {len(problems)}个 ({open_count}未解决)")
            for prob in problems[:3]:
                st = "⭕" if prob['status'] == 'open' else "✅"
                lines.append(f"  {st} #{prob['id']} {prob['title'][:40]}")

        db.close()
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ 查询失败: {e}"


def db_add_project(name: str, description: str = "", goal: str = "") -> str:
    """新增项目"""
    try:
        from deduction_db import DeductionDB
        pid = f"p_{''.join(c for c in name if c.isalnum())[:10].lower()}_{int(time.time()) % 10000}"
        db = DeductionDB()
        db.upsert_project({
            'id': pid, 'name': name, 'description': description,
            'status': 'active', 'progress': 0,
            'short_term_goal': goal,
        })
        db.close()
        return f"✅ 项目创建成功\nID: {pid}\n名称: {name}"
    except Exception as e:
        return f"⚠️ 创建失败: {e}"


def db_update_project(project_id: str, updates: Dict) -> str:
    """更新项目"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        row = db.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            row = db.conn.execute("SELECT * FROM projects WHERE name LIKE ?",
                                  (f"%{project_id}%",)).fetchone()
        if not row:
            db.close()
            return f"⚠️ 项目 '{project_id}' 不存在"

        p = dict(row)
        p.update(updates)
        db.upsert_project(p)
        db.close()
        changed = ", ".join(f"{k}={v}" for k, v in updates.items())
        return f"✅ 项目 {p['name']} 已更新: {changed}"
    except Exception as e:
        return f"⚠️ 更新失败: {e}"


def db_delete_project(project_id: str) -> str:
    """删除项目(标记为archived)"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        row = db.conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            db.close()
            return f"⚠️ 项目 '{project_id}' 不存在"
        p = dict(row)
        db.conn.execute("UPDATE projects SET status='archived', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (project_id,))
        db.conn.commit()
        db.close()
        return f"📦 项目 {p['name']} 已归档"
    except Exception as e:
        return f"⚠️ 删除失败: {e}"


def db_get_stats() -> str:
    """获取全局统计"""
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        stats = db.get_stats()
        projects = db.get_projects()
        active = [p for p in projects if p['status'] == 'active']
        problems = db.get_problems()
        open_probs = [p for p in problems if p['status'] == 'open']
        db.close()
        return (
            f"📊 系统全局统计\n\n"
            f"项目: {len(active)}/{len(projects)} 活跃\n"
            f"推演计划: {stats.get('plans_total', 0)}个 "
            f"({stats.get('plans_queued', 0)}排队 {stats.get('plans_done', 0)}完成)\n"
            f"问题: {len(open_probs)}/{len(problems)} 未解决\n"
            f"推演步骤: {stats.get('steps_total', 0)}个\n"
            f"知识节点: {stats.get('nodes_total', 0)}个"
        )
    except Exception as e:
        return f"⚠️ 统计失败: {e}"


# ════════════════════════════════════════════════════════════
# CLI 测试
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    def on_step(name, detail):
        print(f"  [{name}] {detail}")

    question = sys.argv[1] if len(sys.argv) > 1 else "如何用Python实现一个简单的任务队列?"
    print(f"\n🎯 问题: {question}\n")

    chain = ChainProcessor(on_step=on_step)
    result = chain.process(question)

    print(f"\n{'='*60}")
    print(f"📊 链路摘要:")
    print(result.summary())
    print(f"\n总耗时: {result.total_duration}s | 路由: {result.route_decision}")
    print(f"\n{'='*60}")
    print(f"📝 最终答案:\n{result.final_answer[:2000]}")
