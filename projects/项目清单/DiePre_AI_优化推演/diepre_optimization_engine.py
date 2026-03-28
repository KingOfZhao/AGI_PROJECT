#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiePre AI 优化推演引擎 v1.0 — 王朝循环制
==========================================
基于管理制度推演方法论(六向碰撞+反贼检测+收敛验证), 对DiePre AI项目进行
架构优化推演。

五阶段循环: 【推演】→【构建】→【反贼】→【分裂】→【一统】
六向碰撞:
  1. 物理定律方向 — 15条不可违背的数学/物理约束
  2. 行业标准方向 — FEFCO/ECMA/ISO/TAPPI/IADD 合规
  3. 工艺链方向   — 裱纸→模切→压痕→糊盒 工序优化
  4. 3D⇄2D引擎方向 — Three.js/Konva渲染管线+误差可视化
  5. 系统架构方向 — 前后端+数据库+API架构
  6. 推翻重建方向 — 质疑当前架构, 找致命缺陷, 提出替代方案

作者: Zhao Dylan
日期: 2026-03-26
"""

import sys
import os
import json
import re
import time
import hashlib
import threading
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests as _requests
except ImportError:
    print("需要 requests 库: pip install requests")
    sys.exit(1)

try:
    sys.path.insert(0, str(Path("/Users/administruter/Desktop/AGI_PROJECT")))
    import agi_v13_cognitive_lattice as _agi
    _HAS_LATTICE_OLLAMA = True
except Exception:
    _agi = None
    _HAS_LATTICE_OLLAMA = False

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
AGI_DIR = Path("/Users/administruter/Desktop/AGI_PROJECT")
OUTPUT_DIR = SCRIPT_DIR
DYNASTY_LOG_DIR = SCRIPT_DIR / "王朝记录"
CHECKPOINT_PATH = SCRIPT_DIR / ".diepre_checkpoint.json"
PREV_ARCH_PATH = SCRIPT_DIR / "上一次架构.json"
SEARCH_CACHE_PATH = SCRIPT_DIR / ".diepre_search_cache.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DYNASTY_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 导入技能路由
sys.path.insert(0, str(AGI_DIR / "scripts"))
try:
    from pcm_skill_router import route_skills_formatted
    SKILL_ROUTER_AVAILABLE = True
except ImportError:
    SKILL_ROUTER_AVAILABLE = False
    def route_skills_formatted(q, top_k=5): return ""

# ==================== 本地模型配置 ====================
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")

_call_count = 0
_call_lock = threading.Lock()


def _call_ollama(prompt: str, system: str = "", max_tokens: int = 8192) -> str:
    global _call_count
    with _call_lock:
        _call_count += 1
        n = _call_count
    # 优先走项目内“本地模型调用链路”: agi_v13_cognitive_lattice._local_ollama_call
    # 这样不依赖外部脚本/命令行拼接，也避免 heredoc/quote 等shell问题。
    if _HAS_LATTICE_OLLAMA and _agi is not None:
        try:
            # 临时覆盖 MAX_TOKENS (仅本次调用有效)
            old_max = getattr(_agi.Config, "MAX_TOKENS", None)
            if old_max is not None:
                _agi.Config.MAX_TOKENS = max_tokens
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            result = _agi._local_ollama_call(messages)
            if old_max is not None:
                _agi.Config.MAX_TOKENS = old_max
            if isinstance(result, dict):
                text = result.get("raw", "") if "raw" in result else json.dumps(result, ensure_ascii=False)
            else:
                text = str(result)
            if n <= 3 or n % 10 == 0:
                print(f"      [OllamaChain #{n}] {len(text)} chars")
            return text
        except Exception as e:
            print(f"      ⚠️ [OllamaChain #{n}] 调用失败, fallback到HTTP: {e}")

    # fallback: 直接走 Ollama HTTP /api/generate
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_ctx": 16384, "num_predict": max_tokens}
    }
    try:
        resp = _requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        text = resp.json().get("response", "")
        if n <= 3 or n % 10 == 0:
            print(f"      [OllamaHTTP #{n}] {len(text)} chars")
        return text
    except Exception as e:
        print(f"      ⚠️ [OllamaHTTP #{n}] 调用失败: {e}")
        return ""


def call_llm(prompt, system="", max_tokens=8192):
    return _call_ollama(prompt, system=system, max_tokens=max_tokens)


def _get_skill_context(topic: str) -> str:
    if not SKILL_ROUTER_AVAILABLE:
        return ""
    try:
        ctx = route_skills_formatted(topic, top_k=5)
        if ctx and "未找到" not in ctx:
            return f"\n## 可用技能参考\n{ctx}\n"
    except Exception:
        pass
    return ""


# ==================== DiePre AI 系统提示 ====================
SYSTEM_PROMPT = """你是包装工程与AI系统架构双领域专家, 精通:
- 包装物理: Gaussian曲率K=0展开约束, RSS误差堆叠, Euler柱屈曲, Kelvin-Voigt蠕变
- 行业标准: FEFCO 12th盒型编码, ECMA折叠纸盒, IADD钢规公差, ISO 12048运输测试, TAPPI T804/T825
- 材料科学: 10大类包装材料(纸板8种/瓦楞6楞型/塑料9种/箔5种/木5种/泡沫6种/织物4种/金属3种/特种纸5种/胶粘剂6种)
- 工艺链: 裱纸(CR压实率)→印刷(套准)→模切(IADD公差)→压痕(槽宽公式)→糊盒(胶收缩)
- 前端: Vue3+Element Plus+Pinia+TailwindCSS+Three.js+Konva.js+GSAP
- 后端: FastAPI+SQLAlchemy+SQLite/PostgreSQL
- 3D引擎: Three.js ExtrudeGeometry/折叠动画/误差带可视化/OrbitControls

核心原则:
- 固定部分=骨架: 物理定律+行业标准+工序规则 不可违背
- 可变部分=穷举选择: 材料/盒型/胶种/机器参数 只能从有限集选择
- 误差反推: 3D成品偏差→RSS拆解→Top contributor→反推2D图纸补偿
- 反贼检测: 任何架构都有内生缺陷, 必须主动发现并修复"""


# ==================== 反贼类型(DiePre专用) ====================
REBEL_TYPES = {
    "bottleneck": {"label": "性能瓶颈", "desc": "计算/渲染瓶颈, 响应>100ms"},
    "data_silo": {"label": "数据孤岛", "desc": "材料/参数数据散落多处, 不一致"},
    "precision_loss": {"label": "精度丢失", "desc": "计算链中误差传递/丢失"},
    "unmapped": {"label": "功能缺失", "desc": "设计了但未实现的功能"},
    "ux_friction": {"label": "交互摩擦", "desc": "用户操作路径过长/不直观"},
    "tech_debt": {"label": "技术债务", "desc": "代码质量/架构耦合问题"},
    "standard_gap": {"label": "标准缺口", "desc": "缺少行业标准合规检查"},
    "integration_gap": {"label": "集成断裂", "desc": "模块间数据不同步/接口不匹配"},
    "render_gap": {"label": "渲染缺陷", "desc": "3D/2D渲染精度或效果不足"},
    "scalability": {"label": "扩展瓶颈", "desc": "架构无法适应新需求/多用户"},
}

# ==================== 六向碰撞方向(DiePre专用) ====================
SIX_DIRECTIONS = [
    {
        "name": "physics_laws",
        "label": "物理定律",
        "topic": """15条不可违背的数学/物理约束在系统中的实现状态:
F1 Gaussian曲率K=0(展开约束), F2面积守恒, F3 Haga折叠, F4 RSS误差堆叠,
F5 Kelvin-Voigt蠕变, F6 Euler柱屈曲, F7复合梁理论, F8 Hooke弹性,
F9 Fick扩散, F10 Kirsch应力集中, F11 Coffin-Manson疲劳, F12 WLF时温等效,
F13弹性回弹, F14热力学第二定律, F15弯曲补偿BA公式。
哪些已实现? 哪些缺失? 实现精度如何?""",
    },
    {
        "name": "industry_standards",
        "label": "行业标准",
        "topic": """20条行业标准的系统合规状态:
S1 FEFCO Code 12th(盒型编号), S2 ECMA(卡纸盒型), S3 IADD(钢规公差±0.254mm),
S4 ISO 12048(运输测试), S5 ISO 3035(纸板测试), S6 TAPPI T804(BCT),
S7 TAPPI T825(ECT), S8 BRCGS(过程控制), S9 FEFCO可回收性, S10 ISPM-15,
S11 GB/T 6543(中国标准), S12 FDA/EU食品接触, S13 McKee公式, S14折痕槽宽公式,
S15 CPK≥1.33, S16印刷色差ΔE<2.0, S17模切毛边≤0.3mm, S18热封温度, S19 ISTA, S20 DIN。
哪些已集成验证? 哪些缺失?""",
    },
    {
        "name": "process_chain",
        "label": "工艺链优化",
        "topic": """5大工序(裱纸→印刷→模切→压痕→糊盒)的系统实现:
- 12条工序固定规则(P1-P12)是否全部编码?
- 压实率CR计算是否区分材料组合?
- 模切刀寿命衰减是否纳入误差预算?
- 工序链是否可视化(每步误差贡献)?
- 机器参数是否动态(工厂profile vs 硬编码)?
- MC膨胀等待时间是否纳入排产?""",
    },
    {
        "name": "render_engine",
        "label": "3D⇄2D引擎",
        "topic": """Three.js+Konva渲染管线的优化:
- 3D面板是否有材料厚度(ExtrudeGeometry)还是0厚度面片?
- 折叠动画是否基于折痕线旋转轴+GSAP补间?
- 误差带是否实时可视化(半透明红色Box)?
- 2D⇄3D是否双向同步(编辑2D→3D更新, 拖3D→2D跟随)?
- 内结构装配是否有碰撞检测+间隙可视化?
- 材料纹理是否根据选择动态加载?
- 误差滑块拖动是否<100ms响应(60fps)?""",
    },
    {
        "name": "system_architecture",
        "label": "系统架构",
        "topic": """前端+后端+数据库架构评估:
- 前端: Vue3+Element Plus+Pinia状态管理 是否最优?
- 2D引擎: Fabric.js+Konva.js双引擎是否应统一?
- 后端API: FastAPI端点是否完整(展开/折叠/RSS/风险/嵌套)?
- 数据库: SQLite 803MB→并发瓶颈? 需PostgreSQL?
- 材料数据: 是否统一为单一数据源(vs 散落3处)?
- 缓存: Redis计算缓存是否必要?
- 离线能力: 前端WASM误差计算器?
- 迁移系统: Alembic是否已集成?""",
    },
    {
        "name": "overthrow_rebuild",
        "label": "推翻重建",
        "topic": """质疑当前DiePre AI架构, 找出致命缺陷:
- 2D/3D引擎是否割裂(Fabric+Konva+Three三套独立)?
- 误差计算是否非实时(需手动触发API)?
- 是否存在'上帝对象'(某个模块承担过多职责)?
- 内结构设计是否完全缺失?
- 装配模拟是否缺失?
- 工厂profile是否缺失(机器参数硬编码)?
- 数据模型是否过度耦合?
提出替代方案: 如何用最小改动解决最大问题?""",
    },
]

# ==================== 节点提取模式(DiePre专用) ====================
NODE_PATTERNS = [
    (r"(?:F\d+|物理定律|公式|约束|守恒|曲率)[:\s：]*([^\n]{10,200})", "physics_law", 0.90),
    (r"(?:S\d+|FEFCO|ECMA|ISO|TAPPI|IADD|BRCGS|DIN|GB/T)[^\n]{5,200}", "standard_ref", 0.90),
    (r"(?:P\d+|工序|裱纸|模切|压痕|糊盒|印刷|覆膜)[:\s：]*([^\n]{10,200})", "process_rule", 0.85),
    (r"(?:Three\.js|Konva|Fabric|GSAP|ExtrudeGeometry|OrbitControls)[^\n]{5,200}", "render_tech", 0.85),
    (r"(?:Vue|Pinia|FastAPI|SQLAlchemy|SQLite|PostgreSQL|Redis|Alembic)[^\n]{5,200}", "arch_tech", 0.80),
    (r"(?:误差|RSS|公差|精度|偏差|σ|tolerance)[:\s：]*([^\n]{10,200})", "error_analysis", 0.85),
    (r"(?:材料|纸板|瓦楞|SBS|FBB|CRB|GRB|楞型)[:\s：]*([^\n]{10,200})", "material_spec", 0.80),
    (r"(?:反贼|缺陷|瓶颈|缺失|问题|debt|gap)[:\s：]*([^\n]{10,200})", "rebel_indicator", 0.70),
    (r"(?:优化|改进|方案|建议|替代|重构)[:\s：]*([^\n]{10,200})", "optimization", 0.70),
    (r"(?:API|端点|路由|/api/)[^\n]{5,200}", "api_endpoint", 0.75),
    (r"(?:\.vue|\.py|engine|service|module)[^\n]{5,200}", "code_module", 0.75),
    (r"(?:动画|渲染|可视化|交互|面板|滑块)[:\s：]*([^\n]{10,200})", "ux_feature", 0.70),
]


# ==================== 搜索器(DiePre专用) ====================
class DiePreSearcher:
    """搜索包装工程、3D渲染、前端架构最佳实践"""

    SEARCH_TOPICS = [
        # 包装工程
        {"query": "FEFCO box code standard corrugated carton design", "category": "packaging_std"},
        {"query": "die cutting tolerance precision packaging IADD", "category": "packaging_precision"},
        {"query": "corrugated board flute types A B C E F specifications", "category": "material_flute"},
        {"query": "paperboard moisture content expansion coefficient CD MD", "category": "material_mc"},
        {"query": "RSS error propagation tolerance stack-up packaging", "category": "error_analysis"},
        {"query": "McKee BCT box compression test formula", "category": "packaging_test"},
        {"query": "crease width formula paperboard thickness", "category": "process_crease"},
        {"query": "lamination compaction rate corrugated board", "category": "process_laminate"},
        # 3D/CAD
        {"query": "Three.js ExtrudeGeometry folding animation box packaging", "category": "threejs"},
        {"query": "3D box folding simulation Three.js GSAP animation", "category": "threejs_fold"},
        {"query": "parametric box design CAD 2D 3D conversion", "category": "cad_3d"},
        {"query": "Konva.js 2D canvas editor performance optimization", "category": "konva"},
        # 前端架构
        {"query": "Vue 3 Pinia state management large application best practice", "category": "vue_arch"},
        {"query": "real-time slider WebSocket debounce 60fps interaction", "category": "realtime_ux"},
        {"query": "WASM WebAssembly calculation offline browser", "category": "wasm"},
        # 后端
        {"query": "FastAPI SQLAlchemy PostgreSQL migration Alembic best practice", "category": "backend"},
        {"query": "DXF SVG parser Python packaging die line", "category": "dxf_parser"},
        # 开源项目
        {"query": "github box template generator FEFCO SVG", "category": "github_box"},
        {"query": "github three.js packaging box 3D folding", "category": "github_3d"},
        {"query": "github corrugated box design calculator", "category": "github_calc"},
    ]

    CACHE_TTL_DAYS = 7

    def __init__(self):
        self.results = []
        self._cache = self._load_cache()

    @staticmethod
    def _load_cache():
        if SEARCH_CACHE_PATH.exists():
            try:
                data = json.loads(SEARCH_CACHE_PATH.read_text(encoding="utf-8"))
                cached_at = data.get("cached_at", "")
                if cached_at:
                    age = (datetime.now() - datetime.fromisoformat(cached_at)).days
                    if age <= DiePreSearcher.CACHE_TTL_DAYS:
                        return data
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def _save_cache(self):
        self._cache["cached_at"] = datetime.now().isoformat()
        SEARCH_CACHE_PATH.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _search_ddg(self, query: str) -> List[str]:
        cache_key = f"ddg:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            resp = _requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = resp.json()
            snippets = []
            if data.get("Abstract"):
                snippets.append(data["Abstract"][:500])
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    snippets.append(topic["Text"][:300])
            self._cache[cache_key] = snippets
            return snippets
        except Exception:
            return []

    def _search_github(self, query: str) -> List[str]:
        cache_key = f"gh:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            resp = _requests.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "per_page": 3},
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            items = resp.json().get("items", [])
            snippets = []
            for item in items:
                desc = item.get("description", "") or ""
                snippets.append(f"[{item['full_name']}★{item.get('stargazers_count',0)}] {desc[:200]}")
            self._cache[cache_key] = snippets
            return snippets
        except Exception:
            return []

    def run_all(self):
        print("  搜索包装工程/3D渲染/前端架构知识...")
        for topic in self.SEARCH_TOPICS:
            q = topic["query"]
            cat = topic["category"]
            snippets = self._search_ddg(q)
            if cat.startswith("github_"):
                snippets += self._search_github(q)
            for s in snippets:
                self.results.append({"category": cat, "content": s})
            time.sleep(0.3)
        self._save_cache()
        print(f"  ✅ 搜索完成: {len(self.results)} 条结果, {len(self.SEARCH_TOPICS)} 个主题")

    def build_context(self) -> str:
        if not self.results:
            return ""
        parts = []
        by_cat = {}
        for r in self.results:
            by_cat.setdefault(r["category"], []).append(r["content"])
        for cat, snippets in by_cat.items():
            parts.append(f"### {cat}")
            for s in snippets[:3]:
                parts.append(f"- {s[:300]}")
        return "\n".join(parts)[:8000]


# ==================== DiePre AI 当前能力清单 ====================
CURRENT_CAPABILITIES = """
## DiePre AI 当前能力清单 (已实现)

### 核心引擎
- rss_engine.py: RSS误差堆叠计算 (F4公式)
- impact_engine.py: McKee箱压计算 (S13公式)
- process_chain_engine.py: 工序链推演 (5大工序)
- risk_scanner.py: 35类灾难风险扫描
- standard_params.py: FEFCO盒型数据 + 材料属性

### 前端
- ParametricDesign.vue: 2D/3D切换 (Three.js v0.183 + Konva.js)
- BoxEditor: 2D编辑器 (Fabric.js)
- 材料选择: 基础下拉
- 状态管理: Pinia

### 后端API
- /api/reasoning/rss: RSS计算
- /api/reasoning/risk-scan: 风险扫描
- /api/reasoning/nesting: 嵌套公差
- /api/reasoning/process-chain: 工序链

### 数据库
- SQLite (803MB单文件)
- 无迁移系统

### 已知缺口 (v1.0推演发现的8个反贼)
- R1: 2D/3D引擎割裂 (Fabric+Konva+Three三套)
- R2: 误差计算非实时 (需手动触发)
- R3: 材料属性散落3处
- R4: 无工厂profile (机器参数硬编码)
- R5: 3D无厚度 (0厚度面片)
- R6: 无装配模拟 (内结构完全缺失)
- R7: DB单点 (SQLite并发锁)
- R8: 无离线计算
"""


# ==================== 推演引擎 ====================
class DiePreOptimizationEngine:
    """DiePre AI 优化推演引擎 — 王朝循环制"""

    SPLIT_THRESHOLD = 5
    MAX_SUPPRESSION = 3

    def __init__(self):
        self.session_id = f"diepre_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._global_seen = set()
        self._round_new_counts = []
        self._all_nodes = []
        self._all_rebels = []
        self._all_logs = []
        self._dynasty_records = []

    @staticmethod
    def _fingerprint(content):
        cleaned = re.sub(r'[\s\*\#\-\|：:。，,、\(\)\[\]（）【】""\'\"\\/$]', '', content)
        if len(cleaned) < 12:
            return hashlib.md5(cleaned.encode()).hexdigest()
        ngrams = set(cleaned[i:i+4] for i in range(len(cleaned) - 3))
        return hashlib.md5("".join(sorted(ngrams)).encode()).hexdigest()

    def _is_dup(self, content, ntype):
        fp = self._fingerprint(content)
        key = f"{ntype}:{fp}"
        if key in self._global_seen:
            return True
        self._global_seen.add(key)
        return False

    def extract_nodes(self, text, source, round_num=0):
        nodes = []
        seen_local = set()
        for pat, ntype, conf in NODE_PATTERNS:
            for m in re.findall(pat, text)[:8]:
                content = m.strip() if isinstance(m, str) else str(m).strip()
                if len(content) < 10 or content in seen_local:
                    continue
                seen_local.add(content)
                if self._is_dup(content, ntype):
                    continue
                node = {"content": content, "type": ntype, "confidence": conf,
                        "source": source, "round": round_num}
                self._all_nodes.append(node)
                nodes.append(node)
        return nodes

    @staticmethod
    def _extract_json(text):
        json_match = re.search(r'```json\s*(\{.+?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        candidates = []
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                start = i
                in_str = False
                escape = False
                for j in range(i, len(text)):
                    c = text[j]
                    if escape:
                        escape = False
                        continue
                    if c == '\\':
                        escape = True
                        continue
                    if c == '"' and not escape:
                        in_str = not in_str
                        continue
                    if in_str:
                        continue
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start:j+1])
                            i = j
                            break
            i += 1
        candidates.sort(key=len, reverse=True)
        for cand in candidates:
            try:
                obj = json.loads(cand)
                if isinstance(obj, dict) and ("模块" in obj or "架构名称" in obj or "modules" in obj
                                              or "优化方案" in obj or "引擎" in obj or "components" in obj):
                    return obj
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _extract_score(text):
        score_match = re.search(r'(?:总分|评分|得分|score)[:\s：]*(\d{1,3})', text, re.IGNORECASE)
        if score_match:
            return min(int(score_match.group(1)), 100)
        return 50

    # ==================== Phase 1: 六向碰撞推演 ====================
    def phase1_reasoning(self, search_ctx, prev_arch, round_num):
        prev_text = json.dumps(prev_arch, ensure_ascii=False, indent=2)[:3000] if prev_arch else ""
        skill_ctx = _get_skill_context("包装设计 刀模 Three.js 误差计算 RSS 盒型 FEFCO")
        direction_results = {}

        for d in SIX_DIRECTIONS:
            prompt = f"""基于以下搜索结果和DiePre AI当前能力, 进行【{d['label']}】方向推演。

## 搜索知识
{search_ctx[:3000]}
{skill_ctx}
{CURRENT_CAPABILITIES}

{"## 上一次架构 (需质疑/推翻)" + chr(10) + prev_text if prev_text else ""}

## 推演方向: {d['topic']}

要求:
1. 列出该方向下发现的所有优化点, 标注优先级(P0/P1/P2)和预估工作量(天)
2. 给出核心结论 (当前实现是否合格, 缺口在哪)
3. 主动发现"反贼": 当前系统中哪些实现暴露了结构性缺陷?
4. 映射到具体代码: 每个优化点对应哪个文件/模块/API
5. 如果是推翻重建方向, 必须给出推翻理由和替代方案

格式: markdown, 关键数据用**加粗**, 反贼用🔴标记"""
            result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
            self._all_logs.append({"round": round_num, "direction": d["name"], "result": result or ""})
            if result:
                self.extract_nodes(result, f"dir_{d['name']}", round_num)
                direction_results[d["name"]] = result
                print(f"    ✅ {d['label']}")
            else:
                print(f"    ⚠️ {d['label']}: 无结果")
            time.sleep(0.5)

        return direction_results

    # ==================== Phase 2: 构建优化架构 ====================
    def phase2_build(self, direction_results, prev_arch, round_num):
        parts = []
        for d in SIX_DIRECTIONS:
            res = direction_results.get(d["name"], "")
            if res:
                parts.append(f"### {d['label']}结论\n{res[:2000]}\n")
        collision_input = "\n".join(parts)

        prev_text = json.dumps(prev_arch, ensure_ascii=False, indent=2)[:2000] if prev_arch else "无"

        prompt = f"""基于六向碰撞推演结果, 构建DiePre AI的**优化架构方案**。

## 碰撞综合
{collision_input[:8000]}

## 上一次架构
{prev_text}

请输出一个完整的JSON架构方案:
```json
{{
  "架构名称": "方案名称",
  "核心改进": "一句话概括",
  "推翻理由": "为什么推翻上一次架构",
  "模块": [
    {{
      "名称": "模块名",
      "文件": "xxx.py / xxx.vue",
      "当前状态": "已有/缺失/需重构",
      "优化方案": "具体改进",
      "优先级": "P0/P1/P2",
      "工作量": "N天",
      "依赖": ["其他模块名"]
    }}
  ],
  "新增API": ["/api/xxx"],
  "新增页面": ["XxxPage.vue"],
  "数据库变更": ["新增表xxx / 字段xxx"],
  "风险": ["风险描述"],
  "评分": {{
    "物理合规": 0-100,
    "标准覆盖": 0-100,
    "工艺完整": 0-100,
    "渲染质量": 0-100,
    "架构健康": 0-100,
    "用户体验": 0-100,
    "总分": 0-100
  }}
}}
```

要求:
1. 必须覆盖六向碰撞中发现的所有问题
2. 每个模块必须映射到具体文件
3. 总分必须合理(不能全100), 反映真实水平
4. 标注哪些是P0(立即)、P1(1-2周)、P2(后续)"""

        result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
        self._all_logs.append({"round": round_num, "phase": "build", "result": result or ""})

        arch = self._extract_json(result) if result else None
        score = arch.get("评分", {}).get("总分", 50) if arch and isinstance(arch.get("评分"), dict) else self._extract_score(result or "")

        if result:
            self.extract_nodes(result, "phase2_build", round_num)

        return result or "", arch, score

    # ==================== Phase 3: 反贼检测与镇压 ====================
    def phase3_rebels(self, current_arch, collision_text, round_num):
        arch_text = json.dumps(current_arch, ensure_ascii=False, indent=2)[:3000] if current_arch else "未生成"

        prompt = f"""作为DiePre AI的"反贼检测官", 分析当前架构中的结构性缺陷。

## 当前架构
{arch_text}

## 碰撞推演发现
{collision_text[:4000]}

请找出所有"反贼"(结构性缺陷), 输出JSON数组:
```json
[
  {{
    "rebel_name": "缺陷名称",
    "rebel_type": "bottleneck/data_silo/precision_loss/unmapped/ux_friction/tech_debt/standard_gap/integration_gap/render_gap/scalability",
    "description": "详细描述, 包含具体代码/模块引用",
    "severity": "critical/high/medium/low",
    "affected_module": "受影响的模块/文件",
    "fix_proposal": "修复方案"
  }}
]
```

要求:
1. 至少找出5个反贼, 不回避任何问题
2. severity必须根据对用户的实际影响判定
3. 每个反贼必须引用具体的模块/文件/API
4. fix_proposal必须具体可执行"""

        result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=4096)
        self._all_logs.append({"round": round_num, "phase": "rebels", "result": result or ""})

        rebels = []
        rebel_list = None

        # 多策略提取
        json_match = re.search(r'```json\s*(\[.+?\])\s*```', result or "", re.DOTALL)
        if json_match:
            try:
                rebel_list = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        if not rebel_list and result:
            arr_start = result.find('[')
            arr_end = result.rfind(']')
            if arr_start >= 0 and arr_end > arr_start:
                try:
                    rebel_list = json.loads(result[arr_start:arr_end+1])
                except json.JSONDecodeError:
                    pass

        if not rebel_list and result:
            rebel_list = []
            for m in re.finditer(r'\{[^{}]*"rebel_name"[^{}]*\}', result):
                try:
                    obj = json.loads(m.group())
                    rebel_list.append(obj)
                except json.JSONDecodeError:
                    pass

        if rebel_list:
            for r in rebel_list:
                if isinstance(r, dict) and r.get("rebel_name"):
                    rebel = {
                        "name": r.get("rebel_name", ""),
                        "type": r.get("rebel_type", "tech_debt"),
                        "description": r.get("description", ""),
                        "severity": r.get("severity", "medium"),
                        "affected_module": r.get("affected_module", ""),
                        "fix_proposal": r.get("fix_proposal", ""),
                        "round": round_num,
                        "status": "active",
                    }
                    rebels.append(rebel)

        if rebels:
            print(f"    🔴 检测到 {len(rebels)} 个反贼!")
            for r in rebels:
                print(f"      [{r['severity']}] {r['name']}: {r['description'][:80]}")
                self._all_rebels.append(r)

            # 镇压
            for rebel in rebels:
                self._suppress_rebel(rebel, current_arch, round_num)
        else:
            print("    ✅ 未检测到反贼")

        active = [r for r in self._all_rebels if r.get("status") == "active"]
        return active

    def _suppress_rebel(self, rebel, current_arch, round_num):
        print(f"      ⚔️ 镇压反贼: {rebel['name']}...")
        prompt = f"""针对DiePre AI中发现的反贼"{rebel['name']}", 提出具体镇压方案。

反贼详情:
- 类型: {rebel['type']}
- 严重度: {rebel['severity']}
- 描述: {rebel['description']}
- 影响模块: {rebel['affected_module']}

要求:
1. 给出**具体的代码级修复方案** (涉及哪些文件/函数/API)
2. 引用行业最佳实践或开源方案
3. 估算修复工作量
4. 说明修复后的预期效果(量化)"""

        result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=2048)
        if result and len(result) > 50:
            rebel["status"] = "suppressed"
            rebel["suppression_log"] = result[:500]
            print(f"      ✅ 镇压成功: {rebel['name']}")
        else:
            rebel["status"] = "active"
            print(f"      ⚠️ 镇压失败: {rebel['name']}")
        time.sleep(0.3)

    # ==================== Phase 4: 分裂(多方案竞争) ====================
    def phase4_split(self, current_arch, active_rebels, round_num):
        if len(active_rebels) < self.SPLIT_THRESHOLD:
            print(f"    ℹ️ 活跃反贼({len(active_rebels)})<阈值({self.SPLIT_THRESHOLD}), 无需分裂")
            return None

        print(f"    ⚔️ 群雄割据! {len(active_rebels)}个反贼未镇压, 产生竞争方案...")
        rebel_text = "\n".join(f"- [{r['severity']}] {r['name']}: {r['description'][:100]}" for r in active_rebels)

        prompt = f"""DiePre AI当前架构有{len(active_rebels)}个未解决的结构性缺陷, 需要产生竞争方案。

未镇压反贼:
{rebel_text}

请生成2-3个竞争架构方案, 每个方案用不同策略解决这些反贼。
每个方案输出JSON(同Phase 2格式), 用---分隔。"""

        result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=8192)
        # 简单实现: 返回整段文本作为factions
        if result:
            return {"text": result, "rebel_count": len(active_rebels)}
        return None

    # ==================== Phase 5: 一统(评选最优) ====================
    def phase5_unify(self, factions, current_arch, round_num):
        if not factions:
            return current_arch

        prompt = f"""从以下竞争方案中选出最优架构:

{factions.get('text', '')[:6000]}

评选标准: 物理合规×标准覆盖×工艺完整×渲染质量×架构健康×用户体验
输出胜者的完整JSON(同Phase 2格式)。"""

        result = call_llm(prompt, system=SYSTEM_PROMPT, max_tokens=4096)
        unified = self._extract_json(result) if result else None
        return unified or current_arch

    # ==================== 报告生成 ====================
    def generate_report(self, dynasty_records, num_cycles, rounds_per_cycle):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 节点统计
        type_counts = {}
        for n in self._all_nodes:
            type_counts[n["type"]] = type_counts.get(n["type"], 0) + 1

        # 反贼统计
        rebel_type_counts = {}
        for r in self._all_rebels:
            rebel_type_counts[r["type"]] = rebel_type_counts.get(r["type"], 0) + 1
        suppressed = sum(1 for r in self._all_rebels if r["status"] == "suppressed")
        unsuppressed = sum(1 for r in self._all_rebels if r["status"] != "suppressed")

        lines = [
            f"# DiePre AI 优化推演报告",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> Session: {self.session_id}",
            f"> 循环: {num_cycles} | 每循环: {rounds_per_cycle}轮",
            f"> 方法论: 六向碰撞 + 反贼检测 + 王朝循环制",
            "",
            "## 一、推演概要",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 王朝循环数 | {num_cycles} |",
            f"| 提取节点 | {len(self._all_nodes)} |",
            f"| 反贼总数 | {len(self._all_rebels)} |",
            f"| 已镇压 | {suppressed} |",
            f"| 未镇压 | {unsuppressed} |",
            "",
            "## 二、节点类型分布",
            "",
            "| 类型 | 数量 |",
            "|------|------|",
        ]
        for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {ntype} | {count} |")

        lines += ["", "## 三、反贼统计", "", "| 反贼类型 | 数量 |", "|----------|------|"]
        for rtype, count in sorted(rebel_type_counts.items(), key=lambda x: -x[1]):
            label = REBEL_TYPES.get(rtype, {}).get("label", rtype)
            lines.append(f"| {label} ({rtype}) | {count} |")

        lines += ["", "### 反贼详情", ""]
        for r in self._all_rebels:
            status = "✅" if r["status"] == "suppressed" else "❌"
            lines.append(f"- {status} **{r['name']}** [{r['severity']}] — {r['description'][:150]}")
            lines.append(f"  模块: {r.get('affected_module', '?')} | 状态: {r['status']}")

        lines += ["", "## 四、王朝更替记录", ""]
        for dr in dynasty_records:
            lines.append(f"### 王朝 {dr['dynasty_num']}: {dr.get('name', '?')}")
            lines.append(f"- 评分: {dr['score']}")
            lines.append(f"- 反贼: 总{dr['total_rebels']} / 镇压{dr['suppressed']} / 未镇压{dr['unsuppressed']}")
            if dr.get("arch"):
                lines.append(f"- 核心改进: {dr['arch'].get('核心改进', '?')}")
            lines.append("")

        # 最终架构
        final_arch = dynasty_records[-1].get("arch") if dynasty_records else None
        if final_arch:
            lines += ["## 五、最终优化架构", "", "```json",
                       json.dumps(final_arch, ensure_ascii=False, indent=2), "```"]

        feedback_template_path = OUTPUT_DIR / "人类反馈注入模板.md"
        feedback_hint = str(feedback_template_path)
        lines += [
            "",
            "## 六、人类反馈注入（让系统越用越准）",
            "",
            "如果你希望下一轮推演更贴近真实业务/生产线/材料库，请优先提供结构化反馈。",
            "",
            f"- 模板文件: `{feedback_hint}`",
            "- 建议方式: 复制下面的 JSON，3 分钟填完关键字段即可",
            "",
            "```json",
            json.dumps({
                "meta": {
                    "author": "",
                    "date": "",
                    "context": "你在做什么场景的包装/刀模设计？（电商邮寄/奢侈品/食品/医药/工业件等）",
                    "priority": "P0/P1/P2"
                },
                "overall": {
                    "what_is_correct": [],
                    "what_is_wrong": [],
                    "missing": [],
                    "should_delete": [],
                    "should_add": [],
                    "must_keep_invariants": []
                },
                "dimension_feedback": {
                    "box_types": {"recommended_count": "", "why": ""},
                    "materials": {"recommended_count": "", "why": ""},
                    "fefco_coverage": {"phase0_codes": [], "phase1_goal": "", "why": ""},
                    "error_sources": {"top_sources": [], "missing_sources": [], "why": ""},
                    "frontend_pages": {"must_have": [], "can_wait": [], "why": ""},
                    "apis": {"must_have": [], "can_wait": [], "why": ""}
                },
                "module_level": [
                    {
                        "module": "",
                        "rating": 1,
                        "issues": [],
                        "suggested_change": "",
                        "acceptance_test": ""
                    }
                ],
                "rebel_level": [
                    {
                        "rebel_name": "",
                        "severity": "critical/high/medium/low",
                        "agree": True,
                        "why": "",
                        "better_fix": ""
                    }
                ]
            }, ensure_ascii=False, indent=2),
            "```",
            "",
            "反馈写完后你只要贴回给我（或保存成文件），我会把它自动注入下一轮推演的提示词与优先级排序里。",
        ]

        lines += ["", "---",
                   f"> DiePre AI 优化推演引擎 v1.0 | 循环: {num_cycles} | 轮次: {rounds_per_cycle}"]

        report_text = "\n".join(lines)
        report_path = OUTPUT_DIR / f"推演报告_{ts}.md"
        report_path.write_text(report_text, encoding="utf-8")
        print(f"\n📄 报告已保存: {report_path}")

        # 保存最终架构JSON
        if final_arch:
            arch_path = OUTPUT_DIR / f"最优架构_{ts}.json"
            arch_path.write_text(json.dumps(final_arch, ensure_ascii=False, indent=2), encoding="utf-8")
            PREV_ARCH_PATH.write_text(json.dumps(final_arch, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"📄 架构已保存: {arch_path}")

        # 保存反贼记录
        rebel_path = DYNASTY_LOG_DIR / f"反贼记录_{ts}.json"
        rebel_path.write_text(json.dumps(self._all_rebels, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 反贼记录已保存: {rebel_path}")

        return report_path

    # ==================== 主循环 ====================
    def run(self, num_cycles=2, rounds_per_cycle=5):
        # 本地模型可用性检测：优先走调用链路，失败再检查HTTP tags
        model_ok = False
        models = []
        if _HAS_LATTICE_OLLAMA and _agi is not None:
            try:
                probe = _call_ollama("返回OK", system="只输出OK", max_tokens=32)
                if "OK" in (probe or ""):
                    model_ok = True
            except Exception:
                model_ok = False

        if not model_ok:
            try:
                resp = _requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
                models = [m["name"] for m in resp.json().get("models", [])]
                model_ok = any(OLLAMA_MODEL in m for m in models)
            except Exception:
                models, model_ok = [], False

        if not model_ok:
            print(f"  ❌ 本地Ollama不可用或模型 {OLLAMA_MODEL} 不可用!")
            if models:
                print(f"     可用模型: {models}")
            print(f"     请先确保 Ollama 运行，并安装模型: ollama pull {OLLAMA_MODEL}")
            sys.exit(1)

        skill_status = "✅ 已加载" if SKILL_ROUTER_AVAILABLE else "❌ 未加载"

        print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║  DiePre AI 优化推演引擎 v1.0 — 王朝循环制                            ║
║  五阶段: 【推演】→【构建】→【反贼】→【分裂】→【一统】                 ║
║  六向碰撞: 物理定律/行业标准/工艺链/3D引擎/系统架构/推翻重建          ║
║  模型: {OLLAMA_MODEL:<20s} | Skill Router: {skill_status}              ║
║  循环: {num_cycles} | 每循环: {rounds_per_cycle}轮 | Session: {self.session_id}
╚═══════════════════════════════════════════════════════════════════════╝
""")

        # Phase 0: 搜索
        print("=" * 70)
        print("🔍 Phase 0: 搜索包装工程/3D渲染/前端架构知识")
        print("=" * 70)
        searcher = DiePreSearcher()
        searcher.run_all()
        search_ctx = searcher.build_context()

        # 加载上一次架构
        prev_arch = None
        if PREV_ARCH_PATH.exists():
            try:
                prev_arch = json.loads(PREV_ARCH_PATH.read_text(encoding="utf-8"))
                print(f"\n📜 上一次架构: {prev_arch.get('架构名称', '未命名')} — 本次将推翻它!")
            except (json.JSONDecodeError, KeyError):
                pass

        dynasty_records = []
        try:
            for cycle in range(num_cycles):
                dynasty_num = cycle + 1
                print(f"\n{'#' * 70}")
                print(f"# 🏛️ 第 {dynasty_num} 个王朝循环")
                print(f"{'#' * 70}")

                current_arch = prev_arch
                best_arch = None
                best_score = 0
                cycle_factions = None

                last_rnd = 0
                for rnd in range(1, rounds_per_cycle + 1):
                    last_rnd = rnd
                    pre_count = len(self._global_seen)

                    print(f"\n{'=' * 70}")
                    print(f"🔄 王朝{dynasty_num} — Round {rnd}/{rounds_per_cycle}")
                    print("=" * 70)

                    # Phase 1: 推演
                    print(f"\n  📐 Phase 1: 六向碰撞推演 (Round {rnd})")
                    direction_results = self.phase1_reasoning(search_ctx, current_arch, rnd)

                    # Phase 2: 构建
                    print(f"\n  🏗️ Phase 2: 构建优化架构")
                    collision_text, new_arch, score = self.phase2_build(direction_results, current_arch, rnd)

                    if new_arch:
                        print(f"    ✅ 新架构: {new_arch.get('架构名称', '?')} (评分: {score})")
                        if score >= best_score:
                            best_arch = new_arch
                            best_score = score
                        current_arch = new_arch
                    else:
                        print("    ⚠️ 未能提取架构JSON")

                    # Phase 3: 反贼
                    print(f"\n  🔴 Phase 3: 反贼检测与镇压")
                    active_rebels = self.phase3_rebels(current_arch, collision_text, rnd)

                    # Phase 4: 分裂
                    print(f"\n  ⚔️ Phase 4: 分裂检测")
                    factions = self.phase4_split(current_arch, active_rebels, rnd)
                    if factions:
                        cycle_factions = factions

                    # Phase 5: 一统
                    if cycle_factions:
                        print(f"\n  👑 Phase 5: 一统天下")
                        unified = self.phase5_unify(cycle_factions, current_arch, rnd)
                        if unified and unified != current_arch:
                            current_arch = unified
                            best_arch = unified
                            cycle_factions = None
                            print("    🎉 新架构一统天下!")
                    else:
                        print(f"\n  👑 Phase 5: 无需一统, 当前架构稳固")

                    new_nodes = len(self._global_seen) - pre_count
                    self._round_new_counts.append(new_nodes)
                    print(f"\n  📈 本轮新增节点: {new_nodes}")

                    # 收敛检测
                    if len(self._round_new_counts) >= 3:
                        if all(c < 2 for c in self._round_new_counts[-3:]):
                            print(f"\n  🔔 收敛: 连续3轮新增<2节点, 结束本王朝")
                            break

                    time.sleep(0.5)

                # 王朝结束
                final_arch = best_arch or current_arch
                cycle_rebels = [r for r in self._all_rebels if r.get("round", 0) <= last_rnd]
                suppressed = sum(1 for r in cycle_rebels if r["status"] == "suppressed")
                unsuppressed = sum(1 for r in cycle_rebels if r["status"] != "suppressed")

                dynasty_record = {
                    "dynasty_num": dynasty_num,
                    "arch": final_arch,
                    "name": (final_arch or {}).get("架构名称", f"王朝{dynasty_num}"),
                    "score": best_score,
                    "total_rebels": len(cycle_rebels),
                    "suppressed": suppressed,
                    "unsuppressed": unsuppressed,
                }
                dynasty_records.append(dynasty_record)

                if final_arch:
                    PREV_ARCH_PATH.write_text(
                        json.dumps(final_arch, ensure_ascii=False, indent=2), encoding="utf-8")

                prev_arch = final_arch

                print(f"\n{'=' * 70}")
                print(f"🏛️ 王朝{dynasty_num}结束")
                print(f"  架构: {(final_arch or {}).get('架构名称', '?')}")
                print(f"  评分: {best_score}")
                print(f"  反贼: 总{len(cycle_rebels)} / 镇压{suppressed} / 未镇压{unsuppressed}")
                print("=" * 70)
        except Exception as e:
            print(f"\n⚠️ 推演中断: {e}")
            traceback.print_exc()
        finally:
            # 无论成功/失败，都落盘当前已有结果
            if dynasty_records:
                print(f"\n{'#' * 70}")
                print("# 📊 生成报告(保证落盘)")
                print(f"{'#' * 70}")
                report_path = self.generate_report(dynasty_records, num_cycles, rounds_per_cycle)
                print(f"\n📌 已落盘: {report_path}")
            else:
                print("\n⚠️ 无可用王朝记录，未生成报告")


# ==================== 主函数 ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="DiePre AI 优化推演引擎 v1.0")
    parser.add_argument("--cycles", type=int, default=2, help="王朝循环数 (默认2)")
    parser.add_argument("--rounds", type=int, default=5, help="每循环轮数 (默认5)")
    parser.add_argument("--split-threshold", type=int, default=5, help="触发分裂的反贼数阈值")
    args = parser.parse_args()

    engine = DiePreOptimizationEngine()
    engine.SPLIT_THRESHOLD = args.split_threshold
    engine.run(num_cycles=args.cycles, rounds_per_cycle=args.rounds)


if __name__ == "__main__":
    main()
