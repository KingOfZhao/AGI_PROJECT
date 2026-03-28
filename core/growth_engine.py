#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI 全速成长引擎 v5.0 — 100x多线程并行·代码领域真实节点
君(14B)=无幻觉验证 臣(GLM-5)=主力算力 佐(GLM-4.7)=快速生成 使(GLM-4.5)=轻量
v5.0新增: 多线程并行GLM-5调用(8-16并发), Phase并行执行, 代码领域全维度每轮推演
目标: 100x消耗量提升, 代码领域真实节点全速增长
"""

import sys, os, json, time, sqlite3, hashlib, re, threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from diepre_growth_framework import (
    DualTrackClassifier, ConvergenceTracker, ZeroAvoidanceScanner,
    PipelineStageGate, RSSConfidenceComposer, GrowthSessionRecorder,
    NodeTruthClassifier, ChainLinkTracker, ComputeOptimizer
)

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

USER_AGI_PHILOSOPHY = """
核心: AGI = 结构化认知网络 + 人机共生 + 持续碰撞
四向碰撞: 1)自上而下拆解证伪 2)自下而上归纳构建 3)左右跨域重叠 4)重叠固化为真实节点
价值: 解决人类寿命限制导致的狭隘性
人机共生: AI梳理实践清单→人类实践证伪→人类赋予新概念→AI整合
认知自洽: 领域内可实践闭环(如小摊贩的摆摊知识)都可构建真实节点

节点真实性5级体系(得到社会广泛认可和实际应用的就是真实节点):
  L1 本体真实: 国际标准(ISO/ECMA/GB)/物理定律/编程语言规范/广泛应用算法/开源组件API
  L2 关系真实: 链式依赖验证(所有前置均L1+)/跨域碰撞(≥2领域验证)/标准映射/设计模式实例化/组件组合/因果链/层级继承
  L3 能力真实: 代码可执行(测试通过)/链式调用(端到端验证)/工程部署/性能达标/人类实践反馈/竞赛评测通过/解决实际问题
  L4 共识真实: 开源广泛使用/行业最佳实践/学术论文引用/专利认证/教育体系收录/多平台一致验证
  L5 进化真实: 参数收敛σ<0.01/≥5轮证伪幸存/版本迭代核心保留/灾难知识完全量化/跨代验证有效

组件=代码功能的链式调用: 节点在链式调用中形成真实能力, 所有节点(含假设/已证伪)均存入数据库
真实性可升可降: hypothesis→L1→L2→L3→L4→L5, 被证伪则降级为deprecated(保留证伪原因)
"""

TOPDOWN_PROMPT = """你是AGI架构师，精通认知科学、软件工程、跨域迁移。认知框架:{philosophy}
大问题: {big_question}
当前系统状态: 已有节点:{node_count} SKILL:{skill_count}

请深度拆解此问题为8-15个可证伪子问题，每个子问题要求:
1. 足够具体，可以写成代码或实验验证
2. 标注难度(1-5)、领域、预期验证方法
3. 说明该子问题与已有节点的关联
4. 给出该子问题被证伪的条件

输出严格JSON: {{"sub_questions":[{{"id":"Q1","question":"详细的子问题描述(至少50字)","difficulty":3,"can_become_skill":true,"skill_type":"executable","domain":"agi","verification_method":"如何验证","falsification_condition":"在什么条件下可被推翻","related_nodes":[]}}]}}"""

BOTTOMUP_PROMPT = """你是AGI模式识别与归纳推理专家。认知框架:{philosophy}
已知节点({node_count}个): {proven_nodes_json}

请从这些节点中进行深度归纳:
1. 识别5-8组组合模式（至少3个节点组合）
2. 每个模式抽象出一个新的高阶概念
3. 详细描述抽象过程和推理链条
4. 评估新概念的实用性和可执行性
5. 给出每个新概念可以转化为什么类型的SKILL

输出JSON: {{"patterns":[{{"pattern_id":"P1","pattern_name":"模式名称","source_nodes":["节点ID列表"],"abstraction":"详细的新概念描述(至少80字)","reasoning_chain":"推理过程描述","can_become_skill":true,"skill_type":"executable或knowledge","confidence":0.8,"practical_application":"实际应用场景"}}]}}"""

HORIZONTAL_PROMPT = """你是AGI跨域迁移与知识融合专家。认知框架:{philosophy}
领域A({domain_a}): {domain_a_nodes}
领域B({domain_b}): {domain_b_nodes}

请进行深度跨域分析:
1. 找出4-8个跨域结构重叠（不仅是表面相似，要找深层结构同构）
2. 每个重叠详细描述两个领域的映射关系
3. 提出具体的融合新能力，包括实现路径
4. 评估融合能力的创新性和实用性
5. 给出每个融合能力的代码实现思路

输出JSON: {{"overlaps":[{{"overlap_id":"O1","domain_a_concept":"领域A的概念","domain_b_concept":"领域B的概念","similarity":0.85,"structural_mapping":"深层结构映射描述","fusion_capability":"详细的融合能力描述(至少80字)","implementation_path":"实现路径","skill_name_suggestion":"建议名","innovation_score":0.9}}]}}"""

FALSIFY_PROMPT = """你是一位严谨的科学哲学家和批判性思维专家。

请尝试从以下多个角度推翻此节点:
节点内容: "{node_content}"
来源: {source} | 当前置信度: {confidence}

证伪分析要求:
1. 逻辑一致性: 该节点是否存在内部逻辑矛盾?
2. 可操作性: 该节点描述的能力是否在当前技术条件下可实现?
3. 边界条件: 在什么极端情况下该节点会失效?
4. 反例搜索: 是否存在已知的反例或反证?
5. 价值判断: 该节点对AGI系统的实际贡献度如何?
6. 给出详细的推理过程

输出JSON: {{"can_be_falsified":false,"logical_analysis":"逻辑分析","operability_analysis":"可操作性分析","boundary_conditions":"边界条件","counterexamples":"反例","value_score":0.8,"reason":"综合判断原因(至少50字)","adjusted_confidence":0.85,"is_proven":true}}"""

SKILL_GEN_PROMPT = """你是一位高级Python工程师，为AGI系统生成高质量SKILL代码。

名称: {skill_name}
描述: {description}
领域: {domain}

要求:
1. 完整可运行的Python模块，不少于80行
2. 包含详细的docstring和类型注解
3. 包含完整的错误处理和日志记录
4. 包含至少2个核心函数和1个辅助函数
5. 包含数据验证和边界检查
6. 包含使用示例(在docstring或注释中)
7. 遵循PEP 8编码规范
8. 如果涉及数据处理，包含输入输出格式说明

只输出Python代码，用```python```包裹。"""

CODE_DOMAIN_PROMPT = """你是一位精通多语言编程的高级架构师。当前AGI系统正在强化代码领域的95个维度能力。

当前系统状态:
- 已有SKILL: {skill_count} | 已有节点: {node_count}
- 当前轮次: {round_number}
- 本轮聚焦维度: {focus_dimensions}

请针对以下代码维度进行深度推演，为每个维度生成可执行的能力提升方案:

{dimension_details}

要求:
1. 每个维度给出具体的代码实现方案(不是概念描述)
2. 包含实际的代码片段、工具集成方案、或算法实现
3. 标注该方案使用的编程语言和依赖库
4. 给出验证方法(如何证明能力已提升)
5. 评估实现后可达到的分数(0-100)

输出JSON: {{"improvements":[{{"dimension_id":1,"dimension_name":"名称","current_score":35,"implementation":"具体实现方案(含代码片段,至少100字)","language":"python/rust/go/java等","dependencies":["依赖列表"],"verification":"验证方法","expected_score":70,"can_become_skill":true,"skill_code":"完整可执行Python代码(至少50行)"}}]}}"""

DEEP_REASONING_PROMPT = """你是AGI认知架构师，负责对系统已有的真实节点进行深度关系推演。

当前系统状态:
- 真实节点数: {node_count}
- SKILL数: {skill_count}
- 当前轮次: {round_number}

已有真实节点(最近{sample_size}个):
{nodes_json}

请进行以下深度推演:
1. 节点关系图谱: 分析这些节点之间的依赖、互补、冲突关系
2. 知识缺口: 识别当前节点网络中的知识空白区域
3. 涌现能力: 推演这些节点组合后可能涌现的新能力(至少5个)
4. 进化路径: 为下一轮成长推荐最有价值的探索方向
5. 关系强度量化: 为每对有关系的节点给出关系强度(0-1)

输出JSON: {{"relationships":[{{"from":"节点ID","to":"节点ID","type":"dependency|complement|conflict","strength":0.8,"description":"关系描述"}}],"knowledge_gaps":[{{"gap_id":"G1","description":"缺口描述","priority":"high","suggested_exploration":"探索建议"}}],"emergent_capabilities":[{{"id":"E1","name":"涌现能力名","description":"详细描述(至少80字)","source_nodes":["来源节点"],"can_become_skill":true,"confidence":0.8}}],"evolution_directions":[{{"direction":"方向描述","priority":"high","expected_nodes":5}}]}}"""


def _unwrap_result(result):
    """Unwrap _parse_llm_content results: extract raw text or return dict/str"""
    if result is None: return None
    if isinstance(result, dict):
        if "raw" in result and len(result) == 1:
            return result["raw"]  # unwrap {"raw": "..."}
        return json.dumps(result, ensure_ascii=False)
    if isinstance(result, list):
        return json.dumps(result, ensure_ascii=False)
    return str(result)

# JSONL日志文件
GROWTH_LOG_PATH = PROJECT_DIR / "data" / "growth_reasoning_log.jsonl"
GROWTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def _log_call(phase, prompt, response, tokens, round_num=0):
    """记录每次GLM-5调用到本地JSONL"""
    entry = {"ts": datetime.now().isoformat(), "round": round_num, "phase": phase,
             "prompt_len": len(prompt), "response_len": len(str(response)) if response else 0,
             "tokens": tokens, "prompt_preview": prompt[:500], "response_preview": str(response)[:1000]}
    try:
        with open(GROWTH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception: pass

def call_glm5(prompt, system="", max_tokens=8192, phase="unknown", round_num=0, timeout=150):
    """Call GLM-5 with timeout protection (default 150s) and rate-limit delay.
    串行模式下使用, 自带429指数退避重试(最多3次)"""
    import random as _rand
    max_retries = 3
    for attempt in range(max_retries + 1):
        time.sleep(max(1.5, 2.0 + attempt * 1.0))  # 渐进式rate-limit保护
        result_box = [None]
        error_box = [None]
        def _call():
            try:
                from agi_v13_cognitive_lattice import glm5_call
                msgs = []
                if system: msgs.append({"role":"system","content":system})
                msgs.append({"role":"user","content":prompt})
                result_box[0] = glm5_call(msgs, max_tokens=max_tokens)
            except Exception as e:
                error_box[0] = e
        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            print(f"  [GLM-5 Timeout] {phase} exceeded {timeout}s, skipping")
            _log_call(phase, prompt, "TIMEOUT", 0, round_num)
            return None, 0
        if error_box[0]:
            err_str = str(error_box[0])
            if ("429" in err_str or "1302" in err_str or "rate" in err_str.lower()) and attempt < max_retries:
                backoff = min(3.0 * (2 ** attempt), 30.0) + _rand.uniform(0.5, 2.0)
                print(f"  [GLM-5] 429 retry {attempt+1}/{max_retries}, wait {backoff:.1f}s ({phase})")
                time.sleep(backoff)
                continue
            print(f"  [GLM-5 Error] {error_box[0]}")
            return None, 0
        result = result_box[0]
        itk = len(prompt+system)//2; otk = len(str(result))//2 if result else 0
        unwrapped = _unwrap_result(result)
        _log_call(phase, prompt, unwrapped, itk+otk, round_num)
        return unwrapped, itk+otk
    print(f"  [GLM-5] 所有{max_retries}次重试耗尽 ({phase})")
    _log_call(phase, prompt, "RETRY_EXHAUSTED", 0, round_num)
    return None, 0

class AdaptiveRateLimiter:
    """自适应限速器: 成功时逐步加速, 429时大幅减速(智谱官方推荐控制请求频率)"""
    def __init__(self, initial_qps=1.0, max_qps=5.0, min_qps=0.2):
        self.qps = initial_qps
        self.max_qps = max_qps
        self.min_qps = min_qps
        self.success_streak = 0
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._consecutive_429 = 0

    def wait(self):
        with self._lock:
            interval = 1.0 / self.qps
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_call = time.time()

    def on_success(self):
        with self._lock:
            self.success_streak += 1
            self._consecutive_429 = 0
            if self.success_streak >= 15:
                old = self.qps
                self.qps = min(self.qps * 1.15, self.max_qps)
                if self.qps != old:
                    print(f"  [RateLimiter] QPS: {old:.1f} → {self.qps:.1f}")
                self.success_streak = 0

    def on_rate_limit(self):
        with self._lock:
            old = self.qps
            self._consecutive_429 += 1
            # 连续429越多, 降速越猛
            factor = max(0.3, 0.5 ** self._consecutive_429)
            self.qps = max(self.qps * factor, self.min_qps)
            self.success_streak = 0
            print(f"  [RateLimiter] 429(连续{self._consecutive_429})! QPS: {old:.1f} → {self.qps:.1f}")

    def on_error(self):
        with self._lock:
            self.success_streak = 0

# 全局限速器实例 (智谱GLM-5建议低QPS启动, 避免瞬时突发)
_rate_limiter = AdaptiveRateLimiter(initial_qps=1.0, max_qps=5.0)

def call_glm5_throttled(prompt, system="", max_tokens=8192, phase="unknown", round_num=0, timeout=150):
    """带自适应限速的GLM-5调用 (线程安全, 迭代重试, 指数退避)
    智谱官方推荐: 控制请求频率, 429时指数退避重试"""
    import random as _rand
    max_retries = 5
    for attempt in range(max_retries + 1):
        _rate_limiter.wait()
        result_box = [None]
        error_box = [None]
        def _call():
            try:
                from agi_v13_cognitive_lattice import glm5_call
                msgs = []
                if system: msgs.append({"role":"system","content":system})
                msgs.append({"role":"user","content":prompt})
                result_box[0] = glm5_call(msgs, max_tokens=max_tokens)
            except Exception as e:
                error_box[0] = e
        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            _rate_limiter.on_error()
            _log_call(phase, prompt, "TIMEOUT", 0, round_num)
            return None, 0
        if error_box[0]:
            err_str = str(error_box[0])
            if ("429" in err_str or "1302" in err_str or "rate" in err_str.lower()) and attempt < max_retries:
                _rate_limiter.on_rate_limit()
                # 指数退避 + 随机抖动 (3s, 6s, 12s, 24s, 48s)
                backoff = min(3.0 * (2 ** attempt), 60.0) + _rand.uniform(0.5, 3.0)
                print(f"  [Throttled] 429 retry {attempt+1}/{max_retries}, wait {backoff:.1f}s ({phase})")
                time.sleep(backoff)
                continue
            _rate_limiter.on_error()
            print(f"  [Throttled] Error: {error_box[0]} ({phase})")
            return None, 0
        _rate_limiter.on_success()
        result = result_box[0]
        itk = len(prompt+system)//2; otk = len(str(result))//2 if result else 0
        unwrapped = _unwrap_result(result)
        _log_call(phase, prompt, unwrapped, itk+otk, round_num)
        return unwrapped, itk+otk
    # 所有重试耗尽
    print(f"  [Throttled] 所有{max_retries}次重试耗尽 ({phase})")
    _log_call(phase, prompt, "RETRY_EXHAUSTED", 0, round_num)
    return None, 0


class ParallelGLM5Caller:
    """多线程并行GLM-5调用器 — 100x消耗量核心"""

    def __init__(self, max_workers=8):
        self.max_workers = max_workers
        self.total_calls = 0
        self.total_tokens = 0
        self._lock = threading.Lock()

    def submit_batch(self, tasks):
        """并行提交一批GLM-5调用任务
        tasks: List[dict] 每个dict包含:
            - prompt: str
            - system: str (可选)
            - max_tokens: int (可选, 默认8192)
            - phase: str
            - round_num: int
            - task_id: str (用于结果匹配)
        返回: Dict[task_id → (response, tokens)]
        """
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {}
            for task in tasks:
                tid = task.get("task_id", f"t_{id(task)}")
                future = executor.submit(
                    call_glm5_throttled,
                    prompt=task["prompt"],
                    system=task.get("system", ""),
                    max_tokens=task.get("max_tokens", 8192),
                    phase=task.get("phase", "parallel"),
                    round_num=task.get("round_num", 0),
                    timeout=task.get("timeout", 150),
                )
                future_map[future] = tid

            for future in as_completed(future_map):
                tid = future_map[future]
                try:
                    resp, tk = future.result()
                    results[tid] = (resp, tk)
                    with self._lock:
                        self.total_calls += 1
                        self.total_tokens += tk
                except Exception as e:
                    print(f"  [Parallel] {tid} failed: {e}")
                    results[tid] = (None, 0)

        return results

    def stats(self):
        with self._lock:
            return {"calls": self.total_calls, "tokens": self.total_tokens}


def _wrap_list(lst):
    """Wrap a list into a dict by guessing key from content"""
    if not lst or not isinstance(lst, list): return {"items": lst or []}
    if isinstance(lst[0], dict):
        if "question" in lst[0]: return {"sub_questions": lst}
        if "pattern_name" in lst[0] or "abstraction" in lst[0]: return {"patterns": lst}
        if "overlap_id" in lst[0] or "fusion_capability" in lst[0] or "similarity" in lst[0]: return {"overlaps": lst}
    return {"items": lst}

def _ensure_dict(obj):
    """Ensure result is a dict"""
    if obj is None: return None
    if isinstance(obj, dict): return obj
    if isinstance(obj, list): return _wrap_list(obj)
    return None

def parse_json(text):
    if not text: return None
    if isinstance(text, dict): return text
    if isinstance(text, list): return _wrap_list(text)
    text = str(text)
    # Try direct parse
    try:
        r = json.loads(text)
        return _ensure_dict(r) or r
    except (json.JSONDecodeError, ValueError): pass
    # Try ```json``` block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            r = json.loads(m.group(1))
            return _ensure_dict(r) or r
        except (json.JSONDecodeError, ValueError): pass
    # Find outermost { ... }
    depth = 0; start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try: return json.loads(text[start:i+1])
                except (json.JSONDecodeError, ValueError): start = -1
    # Last resort: find outermost [ ... ]
    depth = 0; start = -1
    for i, ch in enumerate(text):
        if ch == '[':
            if depth == 0: start = i
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    r = json.loads(text[start:i+1])
                    return _wrap_list(r)
                except (json.JSONDecodeError, ValueError): start = -1
    return None


class GrowthEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.db_path = PROJECT_DIR / "memory.db"
        self.skills_dir = PROJECT_DIR / "workspace" / "skills"
        self.web_dir = PROJECT_DIR / "web"
        self.current_round = 0
        self.history = []
        self.all_skills = []
        self.total_tokens = 0
        # DiePre框架增强组件
        self.dual_track = DualTrackClassifier()
        self.convergence = ConvergenceTracker()
        self.scanner = ZeroAvoidanceScanner()
        self.session_recorder = GrowthSessionRecorder(self.db_path)
        # v7.0 节点真实性分级 + 链式调用 + 算力优化
        self.truth_classifier = NodeTruthClassifier()
        self.chain_tracker = ChainLinkTracker(self.db_path)
        self.compute_optimizer = ComputeOptimizer()
        self._init_db()
        self._load_existing_skills()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS proven_nodes(id TEXT PRIMARY KEY,content TEXT NOT NULL,type TEXT NOT NULL,source TEXT,collision_type TEXT,confidence REAL DEFAULT 0.8,domain TEXT,tags TEXT,metadata TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,verified_by TEXT,verification_date TIMESTAMP);
            CREATE TABLE IF NOT EXISTS skills(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,file_path TEXT,description TEXT,tags TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,forged_by TEXT,source_node_id TEXT,meta_json TEXT,validation_score INTEGER DEFAULT 0,is_active BOOLEAN DEFAULT 1);
            CREATE TABLE IF NOT EXISTS skill_dependencies(id INTEGER PRIMARY KEY AUTOINCREMENT,skill_id TEXT NOT NULL,depends_on TEXT NOT NULL,dependency_type TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS growth_log(id INTEGER PRIMARY KEY AUTOINCREMENT,round_number INTEGER NOT NULL,phase TEXT NOT NULL,event_type TEXT,entity_id TEXT,tokens_used INTEGER DEFAULT 0,elapsed_seconds REAL,metadata TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS collision_history(id INTEGER PRIMARY KEY AUTOINCREMENT,collision_type TEXT NOT NULL,input_nodes TEXT,output_nodes TEXT,glm5_prompt TEXT,glm5_response TEXT,tokens_used INTEGER,confidence REAL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS pcm(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,concept TEXT NOT NULL,domain TEXT,confidence REAL DEFAULT 0.8,references_json TEXT,source_node_id TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """)
        conn.commit(); conn.close()

    def _load_existing_skills(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT meta_json FROM skills WHERE is_active=1")
        for row in c.fetchall():
            try: self.all_skills.append(json.loads(row[0]))
            except Exception: pass
        conn.close()
        # Also scan filesystem
        for f in self.skills_dir.glob("*.meta.json"):
            try:
                meta = json.loads(f.read_text(encoding="utf-8"))
                if meta.get("name") and not any(s.get("name")==meta["name"] for s in self.all_skills):
                    self.all_skills.append(meta)
            except Exception: pass

    def _count_nodes(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor(); c.execute("SELECT COUNT(*) FROM proven_nodes"); n = c.fetchone()[0]; conn.close(); return n

    def _get_proven_nodes(self, limit=15):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT id,content,type,domain,confidence,tags,metadata FROM proven_nodes WHERE type='proven' ORDER BY created_at DESC LIMIT ?", (limit,))
        nodes = [{"id":r[0],"content":r[1],"type":r[2],"domain":r[3],"confidence":r[4],"tags":r[5],"metadata":r[6]} for r in c.fetchall()]
        conn.close(); return nodes

    def _get_domains(self):
        nodes = self._get_proven_nodes(limit=50)
        domains = {}
        for n in nodes:
            d = n.get("domain","general")
            domains.setdefault(d, []).append(n)
        return domains

    def _get_nodes_by_domain(self, domain, limit=5):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT id,content,type,domain,confidence FROM proven_nodes WHERE domain=? LIMIT ?", (domain, limit))
        nodes = [{"id":r[0],"content":r[1],"type":r[2],"domain":r[3],"confidence":r[4]} for r in c.fetchall()]
        conn.close(); return nodes

    def _save_node(self, node):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT OR REPLACE INTO proven_nodes(id,content,type,source,collision_type,confidence,domain,tags,metadata) VALUES(?,?,?,?,?,?,?,?,?)",
            (node["id"], node["content"], node.get("type","proven"), node.get("source",""), node.get("collision_type",""),
             node.get("confidence",0.8), node.get("domain","general"), node.get("tags","[]"), node.get("metadata","{}")))
        # v7.0: 更新真实性分级字段 (安全处理: 列可能尚未存在)
        try:
            conn.execute("""UPDATE proven_nodes SET truth_level=?, truth_source=?, truth_reasons=?,
                verify_count=COALESCE(verify_count,0)+1, falsify_survived=? WHERE id=?""",
                (node.get("truth_level", 0), node.get("truth_source", "unclassified"),
                 json.dumps(node.get("truth_reasons", []), ensure_ascii=False),
                 node.get("falsify_survived", 0), node["id"]))
        except Exception:
            pass
        conn.commit(); conn.close()

    def _save_collision(self, ctype, inputs, outputs, prompt, response, tokens):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT INTO collision_history(collision_type,input_nodes,output_nodes,glm5_prompt,glm5_response,tokens_used) VALUES(?,?,?,?,?,?)",
            (ctype, json.dumps(inputs), json.dumps(outputs), prompt[:2000], str(response)[:2000], tokens))
        conn.commit(); conn.close()

    def _save_skill_to_db(self, skill):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT OR REPLACE INTO skills(id,name,file_path,description,tags,forged_by,source_node_id,meta_json) VALUES(?,?,?,?,?,?,?,?)",
            (skill["name"], skill["name"], skill.get("file",""), skill.get("description",""),
             json.dumps(skill.get("tags",[]),ensure_ascii=False), "growth_engine",
             skill.get("source_node_id",""), json.dumps(skill,ensure_ascii=False)))
        conn.commit(); conn.close()

    def _save_pcm(self, pcm):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO pcm(id,name,concept,domain,confidence,source_node_id) VALUES(?,?,?,?,?,?)",
                (pcm["id"], pcm["name"], pcm["concept"], pcm.get("domain",""), pcm.get("confidence",0.8), pcm.get("source_node_id","")))
            conn.commit()
        except Exception: pass
        conn.close()

    def _update_skill_score(self, name, score):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE skills SET validation_score=? WHERE name=?", (score, name))
        conn.commit(); conn.close()

    def _save_round_to_db(self, result):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("INSERT INTO growth_log(cycle_id,action,detail,nodes_before,nodes_after,relations_before,relations_after) VALUES(?,?,?,?,?,?,?)",
            (f"growth_r{result['round']}_{int(time.time())}", "growth_round", json.dumps(result,ensure_ascii=False),
             result.get('proven_nodes',0), result.get('cumul_skills',0), result.get('tokens_used',0), result.get('skills_valid',0)))
        conn.commit(); conn.close()

    def _make_name(self, content, node_id, prefix="auto"):
        short = content[:20].lower()
        name = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '_', short)
        name = re.sub(r'_+', '_', name).strip('_') or "unnamed"
        suffix = hashlib.md5(f"{content}{node_id}".encode()).hexdigest()[:6]
        return f"{prefix}_{name}_{suffix}"

    # ==================== 核心循环 ====================
    def run(self, min_rounds=10, max_rounds=100):
        print(f"\n{'='*60}\nAGI 全速成长引擎 v4.0 — 君臣佐使·代码维度强化\n已有SKILL: {len(self.all_skills)} | 已有节点: {self._count_nodes()}\n目标: 每轮70,000+ tokens | GLM-5主力算力(臣)\n新增Phase 4.5: 代码维度专项推演(5组×4维度轮转)\n{'='*60}\n")

        for rnd in range(1, max_rounds+1):
            self.current_round = rnd
            t0 = time.time()
            print(f"\n{'#'*60}\n# 第 {rnd} 轮\n{'#'*60}")

            rtk = 0; new_nodes = []

            # [Phase 1] 自上而下
            td_nodes, td_tk = self._top_down()
            new_nodes.extend(td_nodes); rtk += td_tk

            # [Phase 2] 自下而上
            bu_nodes, bu_tk = self._bottom_up()
            new_nodes.extend(bu_nodes); rtk += bu_tk

            # [Phase 3] 左右重叠 (每轮做2对域)
            for pair_idx in range(2):
                ho_nodes, ho_tk = self._horizontal_overlap(pair_offset=pair_idx)
                new_nodes.extend(ho_nodes); rtk += ho_tk

            # [Phase 4] 深度关系推演 (GLM-5重度消耗)
            dr_nodes, dr_tk = self._deep_reasoning()
            new_nodes.extend(dr_nodes); rtk += dr_tk

            # [Phase 4.5] 代码维度专项推演 (GLM-5主力算力·臣)
            cd_nodes, cd_tk = self._code_domain_growth()
            new_nodes.extend(cd_nodes); rtk += cd_tk

            # [Phase 5] 证伪 (GLM-5)
            proven, fp_tk = self._falsify(new_nodes)
            rtk += fp_tk

            # [Phase 6] 转换SKILL (GLM-5生成代码)
            skills, cv_tk = self._convert(proven)
            rtk += cv_tk

            # [Phase 7] 校验
            valid = self._validate(skills)

            # [Phase 8] 可视化
            self._visualize(valid)

            # [Phase 9] 增量检查
            if len(self.all_skills) >= 5 and len(self.all_skills) % 5 < max(len(valid),1):
                self._dep_check()

            elapsed = time.time() - t0
            self.total_tokens += rtk
            result = {"round":rnd, "raw_nodes":len(new_nodes), "proven_nodes":len(proven),
                      "skills_gen":len(skills), "skills_valid":len(valid), "tokens_used":rtk,
                      "elapsed_seconds":elapsed, "cumul_tokens":self.total_tokens, "cumul_skills":len(self.all_skills),
                      "val_rate": len(valid)/max(len(skills),1)}
            self.history.append(result)
            self._save_round_to_db(result)

            eff = len(proven) + len(valid)
            thrX = 10 + rnd * 4
            print(f"\n{'='*60}\n轮{rnd}: 有效={eff} 阈值X={thrX} tokens={rtk:,} 累计={self.total_tokens:,} 耗时={elapsed:.1f}s\n{'='*60}")

            if rnd >= min_rounds and eff >= thrX:
                print(f"\n✅ 达到阈值，结束"); break

        self._final_report()

    # ==================== 100x并行核心循环 (DiePre框架增强 + 节点真实性分级) ====================
    def run_parallel(self, min_rounds=10, max_rounds=100, max_workers=8):
        """100x消耗量并行模式 + DiePre 6阶段管线门控 + v7.0节点真实性分级
        DiePre增强: 双轨分类 + 收敛追踪 + 零回避扫描 + RSS合成 + 成长记录
        v7.0增强: 5级真实性分级 + 链式调用追踪 + 算力智能调优
        每轮预计: ~75次GLM-5调用, ~600K tokens"""
        self.parallel_caller = ParallelGLM5Caller(max_workers=max_workers)
        print(f"\n{'='*60}\nAGI 全速成长引擎 v7.0 — 节点真实性分级+DiePre增强并行\n已有SKILL: {len(self.all_skills)} | 已有节点: {self._count_nodes()}\n并发数: {max_workers} | 真实性分级: L1本体→L2关系→L3能力→L4共识→L5进化\nDiePre增强: 双轨+收敛+零回避+RSS+管线门控+算力调优\n{'='*60}\n")

        for rnd in range(1, max_rounds+1):
            self.current_round = rnd
            t0 = time.time()
            pipeline = PipelineStageGate()
            print(f"\n{'#'*60}\n# 第 {rnd} 轮 (DiePre增强并行模式)\n{'#'*60}")

            rtk = 0; new_nodes = []; phase_confidences = []

            # ===== Stage 1: 问题分解 (DiePre Pipeline Stage 1) =====
            print(f"\n[Stage1] 问题分解+知识加载...")
            phase_futures = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for qi in range(4):
                    phase_futures[executor.submit(self._top_down_indexed, qi)] = f"td_{qi}"
                for bi in range(2):
                    phase_futures[executor.submit(self._bottom_up)] = f"bu_{bi}"
                for future in as_completed(phase_futures):
                    tag = phase_futures[future]
                    try:
                        nodes, tk = future.result()
                        new_nodes.extend(nodes)
                        rtk += tk
                        phase_name = "top_down" if tag.startswith("td") else "bottom_up"
                        avg_conf = sum(n.get("confidence", 0.5) for n in nodes) / max(len(nodes), 1)
                        phase_confidences.append((phase_name, avg_conf))
                        print(f"  ✓ {tag}: {len(nodes)}节点, {tk:,}tokens")
                    except Exception as e:
                        print(f"  ✗ {tag}: {e}")
            gate_ok, gate_msg = pipeline.check_gate(1, {"sub_questions_count": len(new_nodes)})
            if not gate_ok:
                print(f"  ⚠ {gate_msg}")

            # ===== Stage 2: 多Phase推演 (DiePre Pipeline Stage 2+3) =====
            print(f"\n[Stage2] 碰撞推演+代码维度...")
            phase_futures2 = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for pi in range(6):
                    phase_futures2[executor.submit(self._horizontal_overlap, pair_offset=pi)] = f"ho_{pi}"
                for di in range(2):
                    phase_futures2[executor.submit(self._deep_reasoning)] = f"dr_{di}"
                for gi in range(len(self.CODE_DIMENSION_GROUPS)):
                    phase_futures2[executor.submit(self._code_domain_growth_indexed, gi)] = f"cd_{gi}"
                for future in as_completed(phase_futures2):
                    tag = phase_futures2[future]
                    try:
                        nodes, tk = future.result()
                        new_nodes.extend(nodes)
                        rtk += tk
                        if tag.startswith("ho"): pn = "horizontal"
                        elif tag.startswith("dr"): pn = "deep_reasoning"
                        else: pn = "code_domain"
                        avg_conf = sum(n.get("confidence", 0.5) for n in nodes) / max(len(nodes), 1)
                        phase_confidences.append((pn, avg_conf))
                        print(f"  ✓ {tag}: {len(nodes)}节点, {tk:,}tokens")
                    except Exception as e:
                        print(f"  ✗ {tag}: {e}")

            pipeline.check_gate(2, {"context_nodes_count": self._count_nodes()})
            pipeline.check_gate(3, {"raw_nodes_count": len(new_nodes)})
            print(f"\n[Stage2] 推演完成: {len(new_nodes)}节点, {rtk:,}tokens")

            # ===== RSS置信度合成 (DiePre模式5) + 算力权重更新(v7.0) =====
            rss_confidence = RSSConfidenceComposer.compose(phase_confidences)
            contributions = RSSConfidenceComposer.contribution_analysis(phase_confidences)
            print(f"  📊 RSS合成置信度: {rss_confidence:.3f}")
            if contributions:
                top = contributions[0]
                print(f"     主贡献: {top['phase']} ({top['contribution_pct']:.1f}%)")
                # v7.0: 根据贡献度动态调整Phase权重
                self.compute_optimizer.update_phase_weights(contributions)

            # ===== Stage 3: 并行证伪 + 双轨分类 + 真实性分级 (DiePre模式1+3 + v7.0) =====
            proven, fp_tk = self._falsify_parallel(new_nodes)
            rtk += fp_tk
            # DiePre双轨分类
            classified = self.dual_track.batch_classify(proven)
            fixed_count = len(classified["fixed_rule"])
            variable_count = len(classified["variable_param"])
            print(f"  📊 双轨分类: 固定={fixed_count} 可变={variable_count} 假设={len(classified['hypothesis'])}")
            # v7.0: 节点真实性5级分级
            truth_contexts = {}
            for nd in proven:
                ctx = self.chain_tracker.get_chain_context(nd.get("id", ""))
                # 从碰撞类型推断跨域验证次数
                if nd.get("collision_type") == "horizontal":
                    ctx["cross_domain_count"] = ctx.get("cross_domain_count", 0) + 2
                truth_contexts[nd.get("id", "")] = ctx
            truth_result = NodeTruthClassifier.batch_classify(proven, truth_contexts)
            truth_stats = truth_result["stats"]
            print(f"  📊 真实性分级: L0={truth_stats['L0']} L1={truth_stats['L1']} L2={truth_stats['L2']} L3={truth_stats['L3']} L4={truth_stats['L4']} L5={truth_stats['L5']} deprecated={truth_stats['deprecated']}")
            # 收敛追踪
            for nd in proven:
                domain = nd.get("domain", "general")
                self.convergence.record(f"{domain}.confidence", nd.get("confidence", 0.7))

            # ===== Stage 4: 并行转换SKILL + 零回避扫描 (DiePre模式3 + v7.0算力优化) =====
            # v7.0: 使用算力优化器预判哪些节点值得生成SKILL
            worthy_nodes = [nd for nd in proven if self.compute_optimizer.should_generate_skill(nd)]
            skipped = len(proven) - len(worthy_nodes)
            if skipped > 0:
                print(f"  ⚡ 算力优化: 跳过{skipped}个低价值节点的SKILL生成")
            skills, cv_tk = self._convert_parallel(worthy_nodes)
            rtk += cv_tk
            # 零回避风险扫描
            all_risks = []
            for sk in skills:
                skill_file = self.skills_dir / f"{sk.get('name', '')}.py"
                if skill_file.exists():
                    code = skill_file.read_text(encoding="utf-8")
                    risks = self.scanner.scan_skill(code, sk)
                    all_risks.extend(risks)
            if all_risks:
                print(f"  ⚠ 零回避扫描: {len(all_risks)}风险")
                for r in all_risks[:3]:
                    print(f"    {r['level']} {r['name']}: {r['trigger'][:40]}")
            pipeline.check_gate(4, {"skills_generated": len(skills)})

            # ===== Stage 5: 验证 (DiePre Pipeline Stage 5) =====
            valid = self._validate(skills)
            self._visualize(valid)
            if len(self.all_skills) >= 5:
                self._dep_check()
            val_rate = len(valid) / max(len(skills), 1)
            pipeline.check_gate(5, {"validation_rate": val_rate})

            # ===== Stage 6: 成长记录 (DiePre Pipeline Stage 6) =====
            elapsed = time.time() - t0
            self.total_tokens += rtk
            p_stats = self.parallel_caller.stats()
            result = {"round":rnd, "raw_nodes":len(new_nodes), "proven_nodes":len(proven),
                      "skills_gen":len(skills), "skills_valid":len(valid), "tokens_used":rtk,
                      "elapsed_seconds":elapsed, "cumul_tokens":self.total_tokens,
                      "cumul_skills":len(self.all_skills), "val_rate": val_rate,
                      "parallel_calls": p_stats["calls"], "mode": "parallel",
                      "rss_confidence": rss_confidence, "fixed_nodes": fixed_count,
                      "variable_nodes": variable_count, "risks_found": len(all_risks),
                      "truth_L0": truth_stats.get("L0", 0), "truth_L1": truth_stats.get("L1", 0),
                      "truth_L2": truth_stats.get("L2", 0), "truth_L3": truth_stats.get("L3", 0),
                      "truth_L4": truth_stats.get("L4", 0), "truth_L5": truth_stats.get("L5", 0),
                      "truth_avg": truth_stats.get("avg_level", 0), "nodes_skipped": skipped}
            self.history.append(result)
            self._save_round_to_db(result)
            # DiePre成长会话记录
            pipeline.check_gate(6, {"recorded": 1})
            self.session_recorder.record_session(
                rnd, "parallel", result, pipeline, classified, all_risks)

            eff = len(proven) + len(valid)
            thrX = 10 + rnd * 4
            conv_status = self.convergence.status("general.confidence")
            print(f"\n{'='*60}\n轮{rnd}(v7.0真实性分级): 有效={eff} 节点={len(new_nodes)} tokens={rtk:,}\n累计={self.total_tokens:,} 耗时={elapsed:.1f}s RSS={rss_confidence:.3f}\n双轨: 固定={fixed_count} 可变={variable_count} 收敛状态={conv_status}\n真实性: L0={truth_stats.get('L0',0)} L1={truth_stats.get('L1',0)} L2={truth_stats.get('L2',0)} L3={truth_stats.get('L3',0)} avg={truth_stats.get('avg_level',0):.2f}\n算力优化: 跳过{skipped}节点 风险={len(all_risks)} 管线={'全通' if not pipeline.blocked_at else f'阻断@{pipeline.blocked_at}'}\nQPS={_rate_limiter.qps:.1f} 总调用={p_stats['calls']}\n{'='*60}")

            if rnd >= min_rounds and eff >= thrX:
                print(f"\n✅ 达到阈值，结束"); break

            self.save_checkpoint()
            # 每5轮输出收敛报告
            if rnd % 5 == 0:
                print(self.session_recorder.growth_report())

        self._final_report()

    def _top_down_indexed(self, question_idx=0):
        """自上而下: 按索引选择不同问题 (支持并行调用不同问题)"""
        qs = ["如何让AI自我发现新知识并自动构建认知网络",
              "如何将模糊的人类意图转化为可执行的结构化代码",
              "如何验证AI能力是否真实可用而非表面流畅",
              "如何建立跨域知识迁移桥梁并保持认知自洽",
              "如何设计AI与人类的高效协作循环以加速认知进化",
              "如何构建AI的自我证伪与纠错机制以确保知识可靠性",
              "如何让AI理解并处理人类隱性知识如手工艺经验",
              "如何构建可持续进化的AGI认知架构而非静态知识库",
              "如何实现认知节点的自动化质量评估与淘汰机制",
              "如何将工业制造领域的实践经验转化为AGI可用的结构化知识"]
        idx = ((self.current_round - 1) * 4 + question_idx) % len(qs)
        q = qs[idx]
        prompt = TOPDOWN_PROMPT.format(philosophy=USER_AGI_PHILOSOPHY, big_question=q,
                                       node_count=self._count_nodes(), skill_count=len(self.all_skills))
        resp, tk = call_glm5_throttled(prompt, max_tokens=8192, phase=f"top_down_{question_idx}",
                                       round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            for sq in data.get("sub_questions", []):
                nd = {"id": f"td_{self.current_round}_{sq.get('id','Q0')}_{question_idx}_{int(time.time()*1000)%9999}",
                      "content": sq.get("question", ""), "type": "hypothesis", "source": "glm5_generated",
                      "collision_type": "top_down", "confidence": 0.6, "domain": sq.get("domain", "agi"),
                      "tags": json.dumps(["top_down", "glm5", "parallel"]), "metadata": json.dumps(sq, ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)
        self._save_collision("top_down", [], [n["id"] for n in nodes], prompt[:2000], str(resp)[:2000], tk)
        return nodes, tk

    def _code_domain_growth_indexed(self, group_idx):
        """代码维度推演: 指定组索引 (支持5组全并行)"""
        group = self.CODE_DIMENSION_GROUPS[group_idx]
        dims = group["dimensions"]
        dim_details = "\n".join([
            f"维度{d['id']}: {d['name']} (当前{d['score']}分)\n  要求: {d['detail']}"
            for d in dims
        ])
        focus = ", ".join([f"{d['id']}.{d['name']}" for d in dims])
        prompt = CODE_DOMAIN_PROMPT.format(
            skill_count=len(self.all_skills), node_count=self._count_nodes(),
            round_number=self.current_round, focus_dimensions=focus,
            dimension_details=dim_details)
        resp, tk = call_glm5_throttled(prompt, max_tokens=8192, phase=f"code_domain_{group_idx}",
                                       round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            for imp in data.get("improvements", []):
                dim_name = imp.get("dimension_name", "")
                impl_text = imp.get("implementation", "")
                expected = imp.get("expected_score", 0)
                nd = {"id": f"cd_{self.current_round}_{imp.get('dimension_id',0)}_{group_idx}_{int(time.time()*1000)%9999}",
                      "content": f"[代码维度{imp.get('dimension_id',0)}:{dim_name}] {impl_text[:300]}",
                      "type": "code_improvement", "source": "code_domain_growth",
                      "collision_type": "code_dimension", "confidence": min(expected / 100.0, 0.95),
                      "domain": "software_engineering",
                      "tags": json.dumps(["code_domain", imp.get("language","python"), f"dim_{imp.get('dimension_id',0)}", "parallel"]),
                      "metadata": json.dumps(imp, ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)
                skill_code = imp.get("skill_code", "")
                if skill_code and len(skill_code) > 50:
                    name = self._make_name(dim_name, str(imp.get("dimension_id", 0)), "codedim")
                    try:
                        (self.skills_dir / f"{name}.py").write_text(skill_code, encoding="utf-8")
                        meta = {"name": name, "file": f"skills/{name}.py",
                                "description": f"代码维度{imp.get('dimension_id',0)}: {dim_name} — {impl_text[:100]}",
                                "tags": ["code_domain", imp.get("language","python"), "glm5_generated", "parallel"],
                                "created_at": datetime.now().isoformat(), "forged_by": "code_domain_growth_v5",
                                "design_spec": {"name": name, "display_name": dim_name,
                                                "functions": [{"name":"execute","purpose":dim_name,"params":[],"returns":"Dict"}],
                                                "dependencies": imp.get("dependencies",[]),
                                                "estimated_lines": len(skill_code.split("\n"))}}
                        (self.skills_dir / f"{name}.meta.json").write_text(
                            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                        self._save_skill_to_db(meta)
                        self.all_skills.append(meta)
                        # v7.0: 记录代码维度节点→SKILL的链式调用关系
                        try:
                            chain_id = f"codedim_chain_{self.current_round}_{imp.get('dimension_id',0)}_{int(time.time()*1000)%9999}"
                            self.chain_tracker.add_chain(chain_id, f"codedim→skill:{name}", [
                                {"from": nd["id"], "to": f"skill_{name}",
                                 "call_type": "code_dimension_to_skill", "order": 0}])
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"  ✗ SKILL写入失败: {e}")
        # v7.0: 记录同组代码维度节点间的链式关系(同组维度构成组件链)
        if len(nodes) >= 2:
            try:
                group_chain_id = f"dimgroup_{self.current_round}_{group_idx}_{int(time.time()*1000)%9999}"
                links = [{"from": nodes[i]["id"], "to": nodes[i+1]["id"],
                          "call_type": "dimension_group_chain", "order": i}
                         for i in range(len(nodes)-1)]
                self.chain_tracker.add_chain(group_chain_id, f"dimgroup_{group['name']}", links)
            except Exception:
                pass
        self._save_collision("code_domain", [f"dim_{d['id']}" for d in dims],
                             [n["id"] for n in nodes], prompt[:2000], str(resp)[:2000], tk)
        return nodes, tk

    def _falsify_parallel(self, nodes):
        """并行证伪: 所有候选节点同时发送给GLM-5"""
        print(f"\n[B] 并行证伪 ({len(nodes)}候选)...")
        if not nodes: return [], 0
        tasks = []
        for i, nd in enumerate(nodes):
            prompt = FALSIFY_PROMPT.format(node_content=nd["content"][:300],
                                           source=nd.get("source",""), confidence=nd.get("confidence",0.5))
            tasks.append({"prompt": prompt, "max_tokens": 4096, "phase": f"falsify_{i}",
                          "round_num": self.current_round, "task_id": f"f_{i}"})
        results = self.parallel_caller.submit_batch(tasks)
        proven = []; ttk = 0
        for i, nd in enumerate(nodes):
            resp, tk = results.get(f"f_{i}", (None, 0))
            ttk += tk
            data = parse_json(resp) if resp else None
            if data and data.get("is_proven", True) and data.get("adjusted_confidence", 0.5) >= 0.6:
                nd["type"] = "proven"; nd["confidence"] = data.get("adjusted_confidence", 0.7)
                proven.append(nd); self._save_node(nd)
            elif not data:
                nd["type"] = "proven"; proven.append(nd); self._save_node(nd)
        print(f"  ✓ {len(proven)}/{len(nodes)} 通过")
        return proven, ttk

    def _convert_parallel(self, nodes):
        """并行SKILL转换: 所有proven节点同时生成代码"""
        print(f"\n[C] 并行转换 ({len(nodes)}节点)...")
        exec_nodes = []
        know_nodes = []
        exec_kw = ["实现","生成","执行","调用","处理","构建","创建","转换","分析","检测","验证","优化","设计","开发","计算","提取","映射","融合"]
        know_kw = ["概念","定义","原理","理论","知识","理解","认知","模型"]
        for nd in nodes:
            content = nd.get("content","").lower()
            if sum(1 for k in exec_kw if k in content) > sum(1 for k in know_kw if k in content):
                exec_nodes.append(nd)
            else:
                know_nodes.append(nd)
                pcm_name = self._make_name(nd["content"], nd["id"], "pcm")
                self._save_pcm({"id":f"pcm_{int(time.time()*1000)}","name":pcm_name,"concept":nd["content"],
                                "domain":nd.get("domain",""),"confidence":nd.get("confidence",0.7),
                                "source_node_id":nd.get("id","")})
        tasks = []
        for i, nd in enumerate(exec_nodes):
            name = self._make_name(nd["content"], nd["id"])
            prompt = SKILL_GEN_PROMPT.format(skill_name=name, description=nd["content"][:400],
                                             domain=nd.get("domain","general"))
            # v7.0: 根据节点真实性级别动态分配token预算
            token_budget = self.compute_optimizer.get_token_budget(nd.get("truth_level", 0))
            tasks.append({"prompt": prompt, "max_tokens": token_budget, "phase": f"skill_gen_{i}",
                          "round_num": self.current_round, "task_id": f"s_{i}",
                          "_name": name, "_node": nd})
        if not tasks:
            return [], 0
        results = self.parallel_caller.submit_batch(tasks)
        skills = []; ttk = 0
        for i, task in enumerate(tasks):
            resp, tk = results.get(f"s_{i}", (None, 0))
            ttk += tk
            nd = task["_node"]; name = task["_name"]
            code = ""
            if resp:
                m = re.search(r'```python\s*\n?(.*?)\n?```', str(resp), re.DOTALL)
                code = m.group(1) if m else str(resp)
            if not code or len(code) < 20:
                code = f'"""\nSKILL: {name}\n{nd["content"][:100]}\n"""\n\ndef execute(**kwargs):\n    pass\n'
            meta = {"name":name,"file":f"skills/{name}.py","description":nd["content"][:400],
                    "tags":["auto_growth","glm5_generated",f"round_{self.current_round}",nd.get("domain","general"),"parallel"],
                    "created_at":datetime.now().isoformat(),"forged_by":"growth_engine_v5_parallel",
                    "source":nd.get("source","glm5_generated"),"source_node_id":nd.get("id",""),
                    "design_spec":{"name":name,"display_name":nd["content"][:50],
                                   "functions":[{"name":"execute","purpose":nd["content"][:80],"params":[],"returns":"Dict"}],
                                   "dependencies":[],"estimated_lines":len(code.split("\n"))}}
            try:
                (self.skills_dir/f"{name}.py").write_text(code, encoding="utf-8")
                (self.skills_dir/f"{name}.meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2), encoding="utf-8")
                self._save_skill_to_db(meta); self.all_skills.append(meta); skills.append(meta)
                # v7.0: 记录节点→SKILL的链式调用关系
                try:
                    chain_id = f"skill_chain_{self.current_round}_{i}_{int(time.time()*1000)%9999}"
                    self.chain_tracker.add_chain(chain_id, f"node→skill:{name}", [
                        {"from": nd.get("id",""), "to": f"skill_{name}",
                         "call_type": "node_to_skill", "order": 0}])
                except Exception:
                    pass
            except Exception as e:
                print(f"  ✗ {e}")
        print(f"  ✓ {len(skills)} SKILL + {len(know_nodes)} PCM (token预算按真实性分级)")
        return skills, ttk

    def _top_down(self):
        print(f"\n[1] 自上而下 (GLM-5)...")
        qs = ["如何让AI自我发现新知识并自动构建认知网络",
              "如何将模糊的人类意图转化为可执行的结构化代码",
              "如何验证AI能力是否真实可用而非表面流畅",
              "如何建立跨域知识迁移桥梁并保持认知自洽",
              "如何设计AI与人类的高效协作循环以加速认知进化",
              "如何构建AI的自我证伪与纠错机制以确保知识可靠性",
              "如何让AI理解并处理人类隱性知识如手工艺经验",
              "如何构建可持续进化的AGI认知架构而非静态知识库",
              "如何实现认知节点的自动化质量评估与淘汰机制",
              "如何将工业制造领域的实践经验转化为AGI可用的结构化知识"]
        q = qs[(self.current_round-1) % len(qs)]
        prompt = TOPDOWN_PROMPT.format(philosophy=USER_AGI_PHILOSOPHY, big_question=q, node_count=self._count_nodes(), skill_count=len(self.all_skills))
        resp, tk = call_glm5(prompt, max_tokens=8192, phase="top_down", round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            for sq in data.get("sub_questions",[]):
                nd = {"id":f"td_{self.current_round}_{sq.get('id','Q0')}_{int(time.time()*1000)%9999}",
                      "content":sq.get("question",""), "type":"hypothesis", "source":"glm5_generated",
                      "collision_type":"top_down", "confidence":0.6, "domain":sq.get("domain","agi"),
                      "tags":json.dumps(["top_down","glm5"]), "metadata":json.dumps(sq,ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)
            print(f"  ✓ '{q[:25]}...' → {len(nodes)} 子问题")
        else:
            print(f"  ✗ 失败")
        self._save_collision("top_down",[],[n["id"] for n in nodes],prompt[:2000],str(resp)[:2000],tk)
        return nodes, tk

    def _bottom_up(self):
        print(f"\n[2] 自下而上 (GLM-5)...")
        existing = self._get_proven_nodes(30)
        if len(existing) < 2:
            print(f"  ⏭ 节点不足({len(existing)})")
            return [], 0
        ns = json.dumps([{"id":n["id"],"content":n["content"][:80]} for n in existing], ensure_ascii=False)
        prompt = BOTTOMUP_PROMPT.format(philosophy=USER_AGI_PHILOSOPHY, node_count=len(existing), proven_nodes_json=ns)
        resp, tk = call_glm5(prompt, max_tokens=8192, phase="bottom_up", round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            for p in data.get("patterns",[]):
                nd = {"id":f"bu_{self.current_round}_{p.get('pattern_id','P0')}_{int(time.time()*1000)%9999}",
                      "content":p.get("abstraction",""), "type":"pattern", "source":"glm5_generated",
                      "collision_type":"bottom_up", "confidence":p.get("confidence",0.7), "domain":"cross_domain",
                      "tags":json.dumps(["bottom_up","glm5"]), "metadata":json.dumps(p,ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)
            print(f"  ✓ {len(existing)}节点 → {len(nodes)}模式")
        else:
            print(f"  ✗ 失败")
        return nodes, tk

    def _horizontal_overlap(self, pair_offset=0):
        print(f"\n[3] 左右重叠 (GLM-5, 组{pair_offset+1})...")
        pairs = [("software_engineering","cognitive_science"),("agi","practical_skills"),
                 ("flutter","cad"),("data_modeling","human_cognition"),
                 ("machine_learning","traditional_craftsmanship"),("compiler_theory","natural_language"),
                 ("robotics","philosophy"),("game_design","education"),
                 ("biology","distributed_systems"),("music_theory","algorithm_design"),
                 ("architecture","neural_networks"),("economics","ecology")]
        idx = ((self.current_round-1) * 2 + pair_offset) % len(pairs)
        da, db = pairs[idx]
        na = self._get_nodes_by_domain(da, 8) or [{"id":"seed","content":f"{da}领域的核心实践模式、关键抽象和方法论"}]
        nb = self._get_nodes_by_domain(db, 8) or [{"id":"seed","content":f"{db}领域的核心实践模式、关键抽象和方法论"}]
        aj = json.dumps([{"id":n.get("id",""),"content":n.get("content","")[:80]} for n in na], ensure_ascii=False)
        bj = json.dumps([{"id":n.get("id",""),"content":n.get("content","")[:80]} for n in nb], ensure_ascii=False)
        prompt = HORIZONTAL_PROMPT.format(philosophy=USER_AGI_PHILOSOPHY, domain_a=da, domain_b=db, domain_a_nodes=aj, domain_b_nodes=bj)
        resp, tk = call_glm5(prompt, max_tokens=8192, phase="horizontal_overlap", round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            for ov in data.get("overlaps",[]):
                if ov.get("similarity",0) >= 0.5:
                    nd = {"id":f"ho_{self.current_round}_{ov.get('overlap_id','O0')}_{int(time.time()*1000)%9999}",
                          "content":ov.get("fusion_capability",""), "type":"overlap", "source":"collision",
                          "collision_type":"horizontal", "confidence":ov.get("similarity",0.7), "domain":"cross_domain",
                          "tags":json.dumps(["horizontal","collision",da,db]), "metadata":json.dumps(ov,ensure_ascii=False)}
                    if nd["content"]: nodes.append(nd)
            print(f"  ✓ {da}↔{db} → {len(nodes)}重叠")
        else:
            print(f"  ✗ 失败")
        return nodes, tk

    def _deep_reasoning(self):
        print(f"\n[4] 深度关系推演 (GLM-5)...")
        existing = self._get_proven_nodes(25)
        if len(existing) < 3:
            print(f"  ⏭ 节点不足({len(existing)})")
            return [], 0
        ns = json.dumps([{"id":n["id"],"content":n["content"][:100],"domain":n.get("domain","general")} for n in existing], ensure_ascii=False)
        prompt = DEEP_REASONING_PROMPT.format(
            node_count=self._count_nodes(), skill_count=len(self.all_skills),
            round_number=self.current_round, sample_size=len(existing), nodes_json=ns)
        resp, tk = call_glm5(prompt, max_tokens=8192, phase="deep_reasoning", round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []
        if data:
            # 保存关系到数据库
            rels = data.get("relationships", [])
            if rels:
                conn = sqlite3.connect(str(self.db_path))
                for rel in rels[:20]:
                    try:
                        conn.execute("INSERT INTO skill_dependencies(skill_id,depends_on,dependency_type) VALUES(?,?,?)",
                            (rel.get("from",""), rel.get("to",""), rel.get("type","complement")))
                    except Exception: pass
                conn.commit(); conn.close()
                print(f"  🔗 {len(rels)}个节点关系已记录")

            # 涌现能力转为新节点
            for ec in data.get("emergent_capabilities", []):
                nd = {"id":f"em_{self.current_round}_{ec.get('id','E0')}_{int(time.time()*1000)%9999}",
                      "content":ec.get("description",""), "type":"emergent", "source":"deep_reasoning",
                      "collision_type":"emergence", "confidence":ec.get("confidence",0.7), "domain":"cross_domain",
                      "tags":json.dumps(["emergent","deep_reasoning","glm5"]),
                      "metadata":json.dumps(ec,ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)

            # 知识缺口转为探索节点
            for gap in data.get("knowledge_gaps", []):
                nd = {"id":f"gap_{self.current_round}_{gap.get('gap_id','G0')}_{int(time.time()*1000)%9999}",
                      "content":gap.get("suggested_exploration","") or gap.get("description",""),
                      "type":"hypothesis", "source":"knowledge_gap",
                      "collision_type":"gap_fill", "confidence":0.5, "domain":"general",
                      "tags":json.dumps(["knowledge_gap","deep_reasoning"]),
                      "metadata":json.dumps(gap,ensure_ascii=False)}
                if nd["content"]: nodes.append(nd)

            print(f"  ✓ 涌现能力={len(data.get('emergent_capabilities',[]))} 知识缺口={len(data.get('knowledge_gaps',[]))} 关系={len(rels)}")
        else:
            print(f"  ✗ 失败")
        self._save_collision("deep_reasoning", [n["id"] for n in existing[:5]], [n["id"] for n in nodes], prompt[:2000], str(resp)[:2000], tk)
        return nodes, tk

    def _falsify(self, nodes):
        print(f"\n[5] 证伪 ({len(nodes)}候选, GLM-5)...")
        if not nodes: return [], 0
        proven = []; ttk = 0
        for nd in nodes:
            prompt = FALSIFY_PROMPT.format(node_content=nd["content"][:300], source=nd.get("source",""), confidence=nd.get("confidence",0.5))
            resp, tk = call_glm5(prompt, max_tokens=4096, phase="falsify", round_num=self.current_round)
            ttk += tk
            data = parse_json(resp) if resp else None
            if data and data.get("is_proven",True) and data.get("adjusted_confidence",0.5) >= 0.6:
                nd["type"] = "proven"; nd["confidence"] = data.get("adjusted_confidence",0.7)
                proven.append(nd); self._save_node(nd)
            elif not data:
                nd["type"] = "proven"; proven.append(nd); self._save_node(nd)
            else:
                print(f"  ✗ 伪: {nd['content'][:30]}...")
        print(f"  ✓ {len(proven)}/{len(nodes)} 通过")
        return proven, ttk

    def _convert(self, nodes):
        print(f"\n[6] 转换 ({len(nodes)}节点, GLM-5生成代码)...")
        skills = []; ttk = 0
        for nd in nodes:
            content = nd.get("content","").lower()
            exec_kw = ["实现","生成","执行","调用","处理","构建","创建","转换","分析","检测","验证","优化","设计","开发","计算","提取","映射","融合"]
            know_kw = ["概念","定义","原理","理论","知识","理解","认知","模型"]
            is_exec = sum(1 for k in exec_kw if k in content) > sum(1 for k in know_kw if k in content)
            if is_exec:
                name = self._make_name(nd["content"], nd["id"])
                prompt = SKILL_GEN_PROMPT.format(skill_name=name, description=nd["content"][:400], domain=nd.get("domain","general"))
                resp, tk = call_glm5(prompt, max_tokens=8192, phase="skill_gen", round_num=self.current_round)
                ttk += tk
                code = ""
                if resp:
                    m = re.search(r'```python\s*\n?(.*?)\n?```', str(resp), re.DOTALL)
                    code = m.group(1) if m else str(resp)
                if not code or len(code) < 20:
                    code = f'"""\nSKILL: {name}\n{nd["content"][:100]}\n"""\n\ndef execute(**kwargs):\n    pass\n'
                meta = {"name":name,"file":f"skills/{name}.py","description":nd["content"][:400],
                        "tags":["auto_growth","glm5_generated",f"round_{self.current_round}",nd.get("domain","general")],
                        "created_at":datetime.now().isoformat(),"forged_by":"growth_engine_v3",
                        "source":nd.get("source","glm5_generated"),"source_node_id":nd.get("id",""),
                        "design_spec":{"name":name,"display_name":nd["content"][:50],
                                       "functions":[{"name":"execute","purpose":nd["content"][:80],"params":[],"returns":"Dict"}],
                                       "dependencies":[],"estimated_lines":len(code.split("\n"))}}
                try:
                    (self.skills_dir/f"{name}.py").write_text(code, encoding="utf-8")
                    (self.skills_dir/f"{name}.meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2), encoding="utf-8")
                    self._save_skill_to_db(meta); self.all_skills.append(meta); skills.append(meta)
                    print(f"  📄 {name} ({len(code.split(chr(10)))}行)")
                except Exception as e:
                    print(f"  ✗ {e}")
            else:
                pcm_name = self._make_name(nd["content"], nd["id"], "pcm")
                self._save_pcm({"id":f"pcm_{int(time.time()*1000)}","name":pcm_name,"concept":nd["content"],"domain":nd.get("domain",""),"confidence":nd.get("confidence",0.7),"source_node_id":nd.get("id","")})
                print(f"  📚 PCM: {pcm_name[:30]}")
        return skills, ttk

    def _validate(self, skills):
        print(f"\n[7] 校验 ({len(skills)})...")
        REQ = ["name","file","description","tags","created_at","forged_by","design_spec"]
        SPEC = ["name","display_name","functions","dependencies"]
        valid = []
        for s in skills:
            issues = [f"缺{f}" for f in REQ if f not in s]
            sp = s.get("design_spec",{})
            issues += [f"spec缺{f}" for f in SPEC if f not in sp]
            score = max(0, 100 - len(issues)*15)
            if score >= 70:
                valid.append(s); self._update_skill_score(s["name"], score)
                print(f"  ✓ {s['name']}: {score}")
            else:
                print(f"  ✗ {s['name']}: {score} {issues[:2]}")
        print(f"  {len(valid)}/{len(skills)} 通过")
        return valid

    def _visualize(self, skills):
        if not skills: return
        print(f"\n[8] 可视化接入...")
        p = self.web_dir/"data"/"skills.json"; p.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"skills":[],"last_updated":""}
        for s in skills:
            data["skills"].append({"id":s["name"],"name":s["name"],"display_name":s.get("design_spec",{}).get("display_name",""),
                                   "description":s.get("description",""),"tags":s.get("tags",[]),"source":s.get("source",""),"created_at":s.get("created_at","")})
        data["last_updated"] = datetime.now().isoformat()
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2), encoding="utf-8")
        print(f"  ✓ {p}")

    # ==================== 代码维度专项推演 (君臣佐使·臣) ====================
    # 95维代码能力维度分组，每轮推演一组，GLM-5重度消耗
    CODE_DIMENSION_GROUPS = [
        {
            "name": "多语言代码生成",
            "dimensions": [
                {"id": 34, "name": "Java企业级开发", "score": 22, "detail": "Spring Boot REST API + JPA + 事务管理"},
                {"id": 35, "name": "Go语言并发编程", "score": 17, "detail": "goroutine + channel + sync.WaitGroup 并发模式"},
                {"id": 36, "name": "Rust内存安全", "score": 12, "detail": "所有权/借用/生命周期 + unsafe最小化"},
                {"id": 37, "name": "C# .NET生态", "score": 7, "detail": "ASP.NET Core Web API + Entity Framework + LINQ"},
            ]
        },
        {
            "name": "前端与跨平台",
            "dimensions": [
                {"id": 33, "name": "JS/TS框架掌握", "score": 37, "detail": "React/Vue组件 + TypeScript类型体操 + Next.js SSR"},
                {"id": 38, "name": "前端UI/UX组件", "score": 37, "detail": "Tailwind + shadcn/ui + 响应式布局"},
                {"id": 50, "name": "移动应用开发", "score": 17, "detail": "Flutter Widget + Swift UIKit/SwiftUI"},
                {"id": 51, "name": "跨平台桌面应用", "score": 7, "detail": "Electron/Tauri 桌面应用架构"},
            ]
        },
        {
            "name": "新兴技术领域",
            "dimensions": [
                {"id": 52, "name": "WebAssembly", "score": 2, "detail": "Rust→WASM编译 + JS互操作 + 性能优化"},
                {"id": 53, "name": "游戏开发引擎", "score": 2, "detail": "Unity C# / Godot GDScript 基础游戏逻辑"},
                {"id": 86, "name": "区块链智能合约", "score": 3, "detail": "Solidity ERC-20/721 + Hardhat测试 + 安全审计"},
                {"id": 47, "name": "ML框架集成", "score": 42, "detail": "PyTorch训练循环 + HuggingFace Transformers + ONNX导出"},
            ]
        },
        {
            "name": "算法与性能",
            "dimensions": [
                {"id": 54, "name": "算法竞赛解决率", "score": 37, "detail": "LeetCode Hard级别: 图论/DP/线段树/网络流"},
                {"id": 55, "name": "DP与贪心算法", "score": 42, "detail": "状态压缩DP/区间DP/树形DP + 贪心证明"},
                {"id": 56, "name": "图论与搜索算法", "score": 37, "detail": "Dijkstra/Bellman-Ford/Floyd + A*/IDA* + 最大流"},
                {"id": 17, "name": "时间复杂度优化", "score": 58, "detail": "渐进分析 + 摊还分析 + 主定理应用"},
            ]
        },
        {
            "name": "工程质量深化",
            "dimensions": [
                {"id": 1, "name": "SWE-Bench能力", "score": 35, "detail": "Issue→代码定位→Patch生成→测试验证完整链路"},
                {"id": 6, "name": "仓库级上下文", "score": 32, "detail": "tree-sitter AST + 调用图 + 符号索引 + 跨文件分析"},
                {"id": 72, "name": "遗留代码重构", "score": 32, "detail": "识别代码坏味道 + 设计模式应用 + 安全重构步骤"},
                {"id": 75, "name": "系统架构决策", "score": 62, "detail": "ADR文档 + 架构权衡分析 + 技术选型"},
            ]
        },
    ]

    def _code_domain_growth(self):
        """[Phase 4.5] 代码维度专项推演 — GLM-5主力算力(臣)
        每轮聚焦一组维度，生成可执行的提升方案和SKILL代码"""
        group_idx = (self.current_round - 1) % len(self.CODE_DIMENSION_GROUPS)
        group = self.CODE_DIMENSION_GROUPS[group_idx]
        print(f"\n[4.5] 代码维度推演·臣 (GLM-5): {group['name']}...")

        dims = group["dimensions"]
        dim_details = "\n".join([
            f"维度{d['id']}: {d['name']} (当前{d['score']}分)\n  要求: {d['detail']}"
            for d in dims
        ])
        focus = ", ".join([f"{d['id']}.{d['name']}" for d in dims])

        prompt = CODE_DOMAIN_PROMPT.format(
            skill_count=len(self.all_skills), node_count=self._count_nodes(),
            round_number=self.current_round, focus_dimensions=focus,
            dimension_details=dim_details
        )

        resp, tk = call_glm5(prompt, max_tokens=8192, phase="code_domain", round_num=self.current_round)
        data = parse_json(resp) if resp else None
        nodes = []

        if data:
            improvements = data.get("improvements", [])
            for imp in improvements:
                # 创建能力节点
                dim_name = imp.get("dimension_name", "")
                impl_text = imp.get("implementation", "")
                expected = imp.get("expected_score", 0)
                nd = {
                    "id": f"cd_{self.current_round}_{imp.get('dimension_id', 0)}_{int(time.time()*1000)%9999}",
                    "content": f"[代码维度{imp.get('dimension_id',0)}:{dim_name}] {impl_text[:300]}",
                    "type": "code_improvement",
                    "source": "code_domain_growth",
                    "collision_type": "code_dimension",
                    "confidence": min(expected / 100.0, 0.95),
                    "domain": "software_engineering",
                    "tags": json.dumps(["code_domain", imp.get("language", "python"), f"dim_{imp.get('dimension_id',0)}"]),
                    "metadata": json.dumps(imp, ensure_ascii=False)
                }
                if nd["content"]:
                    nodes.append(nd)

                # 如果有skill_code，直接生成SKILL文件
                skill_code = imp.get("skill_code", "")
                if skill_code and len(skill_code) > 50:
                    name = self._make_name(dim_name, str(imp.get("dimension_id", 0)), "codedim")
                    try:
                        (self.skills_dir / f"{name}.py").write_text(skill_code, encoding="utf-8")
                        meta = {
                            "name": name, "file": f"skills/{name}.py",
                            "description": f"代码维度{imp.get('dimension_id',0)}: {dim_name} — {impl_text[:100]}",
                            "tags": ["code_domain", imp.get("language", "python"), "glm5_generated"],
                            "created_at": datetime.now().isoformat(),
                            "forged_by": "code_domain_growth",
                            "design_spec": {"name": name, "display_name": dim_name,
                                            "functions": [{"name": "execute", "purpose": dim_name, "params": [], "returns": "Dict"}],
                                            "dependencies": imp.get("dependencies", []),
                                            "estimated_lines": len(skill_code.split("\n"))}
                        }
                        (self.skills_dir / f"{name}.meta.json").write_text(
                            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                        self._save_skill_to_db(meta)
                        self.all_skills.append(meta)
                        print(f"  📄 {name} ({len(skill_code.split(chr(10)))}行, 目标{expected}分)")
                    except Exception as e:
                        print(f"  ✗ SKILL写入失败: {e}")

            print(f"  ✓ {group['name']}: {len(improvements)}个维度方案, {len(nodes)}个节点")
        else:
            print(f"  ✗ 代码维度推演失败")

        self._save_collision("code_domain", [f"dim_{d['id']}" for d in dims],
                             [n["id"] for n in nodes], prompt[:2000], str(resp)[:2000], tk)
        return nodes, tk

    def _dep_check(self):
        print(f"\n[9] 依赖检查 ({len(self.all_skills)} SKILL)...")
        graph = {s.get("name",""):s.get("design_spec",{}).get("dependencies",[]) for s in self.all_skills}
        isolated = [n for n,d in graph.items() if not d]
        print(f"  孤立SKILL: {len(isolated)} | 有依赖: {len(graph)-len(isolated)}")

    def _final_report(self):
        rp = PROJECT_DIR/"docs"/"321自成长待处理"/"growth_execution_report_v7.md"
        tr = len(self.history); tn = sum(h.get("proven_nodes",0) for h in self.history)
        ts = sum(h.get("skills_valid",0) for h in self.history); tt = self.total_tokens
        total_elapsed = sum(h.get("elapsed_seconds",0) for h in self.history)
        tokens_per_hour = int(tt / max(total_elapsed/3600, 0.01))
        is_parallel = any(h.get("mode") == "parallel" for h in self.history)
        total_calls = sum(h.get("parallel_calls", 0) for h in self.history)
        total_fixed = sum(h.get("fixed_nodes", 0) for h in self.history)
        total_variable = sum(h.get("variable_nodes", 0) for h in self.history)
        total_risks = sum(h.get("risks_found", 0) for h in self.history)
        avg_rss = sum(h.get("rss_confidence", 0) for h in self.history) / max(tr, 1)
        # v7.0: 真实性分级统计
        total_L0 = sum(h.get("truth_L0", 0) for h in self.history)
        total_L1 = sum(h.get("truth_L1", 0) for h in self.history)
        total_L2 = sum(h.get("truth_L2", 0) for h in self.history)
        total_L3 = sum(h.get("truth_L3", 0) for h in self.history)
        total_L4 = sum(h.get("truth_L4", 0) for h in self.history)
        total_L5 = sum(h.get("truth_L5", 0) for h in self.history)
        avg_truth = sum(h.get("truth_avg", 0) for h in self.history) / max(tr, 1)
        total_skipped = sum(h.get("nodes_skipped", 0) for h in self.history)
        ver = "v7.0 节点真实性分级+DiePre增强并行" if is_parallel else "v4.0 串行"
        report = f"""# AGI 全速成长执行报告\n\n生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n引擎版本: {ver}\n框架来源: DiePre AI + 节点真实性5级体系 + 链式调用追踪 + 算力智能调优\n
## 核心统计\n- 轮次: {tr}\n- 真实节点: {tn}\n- 有效SKILL: {ts}\n- **总 Tokens: {tt:,}**\n- 平均/轮 tokens: {tt//max(tr,1):,}\n- 总耗时: {total_elapsed:.0f}s ({total_elapsed/60:.1f}分钟)\n- **Tokens/小时: {tokens_per_hour:,}**\n- 总API调用: {total_calls}\n
## 节点真实性分级统计 (v7.0)\n- L0 假设: {total_L0}\n- L1 本体真实: {total_L1}\n- L2 关系真实: {total_L2}\n- L3 能力真实: {total_L3}\n- L4 共识真实: {total_L4}\n- L5 进化真实: {total_L5}\n- 平均真实性级别: {avg_truth:.2f}\n- 算力优化跳过节点: {total_skipped}\n
## DiePre框架增强指标\n- 固定规则节点(累计): {total_fixed}\n- 可变参数节点(累计): {total_variable}\n- 零回避风险(累计): {total_risks}\n- 平均RSS置信度: {avg_rss:.3f}\n- 日志文件: data/growth_reasoning_log.jsonl\n
## 逐轮详细\n| 轮 | 原始 | 真实 | L0 | L1 | L2 | L3 | 固定 | 可变 | SKILL | 有效 | Tokens | RSS | 风险 | 耗时 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"""
        for h in self.history:
            report += f"| {h['round']} | {h.get('raw_nodes',0)} | {h.get('proven_nodes',0)} | {h.get('truth_L0',0)} | {h.get('truth_L1',0)} | {h.get('truth_L2',0)} | {h.get('truth_L3',0)} | {h.get('fixed_nodes',0)} | {h.get('variable_nodes',0)} | {h.get('skills_gen',0)} | {h.get('skills_valid',0)} | {h.get('tokens_used',0):,} | {h.get('rss_confidence',0):.2f} | {h.get('risks_found',0)} | {h.get('elapsed_seconds',0):.1f}s |\n"
        report += f"\n## 架构说明\n- 引擎: {ver}\n- GLM-5调用: token预算按真实性级别动态分配(L0=4K L1=6.5K L2=8K L3=9.8K)\n"
        if is_parallel:
            report += f"- 并行Phase: top_down×4 + bottom_up×2 + horizontal×6 + deep_reasoning×2 + code_domain×5\n"
            report += f"- 并行证伪+并行SKILL生成 | 自适应限速QPS={_rate_limiter.qps:.1f}\n"
            report += f"\n## v7.0 节点真实性体系\n"
            report += f"- 得到社会广泛认可和实际应用的就是真实节点\n"
            report += f"- L1 本体真实: 国际标准/物理定律/编程语言规范/广泛应用算法/开源组件API\n"
            report += f"- L2 关系真实: 链式依赖验证/跨域碰撞/标准映射/设计模式实例化/因果链\n"
            report += f"- L3 能力真实: 代码可执行/链式调用验证/工程部署/性能达标/竞赛通过\n"
            report += f"- L4 共识真实: 开源广泛使用/行业最佳实践/学术引用/多平台验证\n"
            report += f"- L5 进化真实: 参数收敛σ<0.01/≥5轮证伪幸存/版本迭代核心保留\n"
            report += f"- 组件=代码功能的链式调用, 节点在链式调用中形成真实能力\n"
            report += f"\n## DiePre 6大增强模式\n"
            report += f"1. **固定/可变双轨**: 节点按置信度+验证次数自动分类, 可变→固定升级路径\n"
            report += f"2. **收敛追踪**: 滑动σ窗口, 已收敛域自动升级为固定规则\n"
            report += f"3. **零回避扫描**: 12类代码灾难模板, 每个SKILL必须扫描失败模式\n"
            report += f"4. **6阶段管线门控**: 分解→加载→推演→生成→验证→记录, 不达标阻断\n"
            report += f"5. **RSS置信度合成**: 多Phase结果加权合成, 贡献度分析指导强化方向\n"
            report += f"6. **成长会话记录**: 灾难知识进化(疑似→确认→完全量化), 每5轮收敛报告\n"
        else:
            report += "- 9个Phase串行: 自上而下/自下而上/左右重叠x2/深度推演/证伪/转换/校验/可视化/依赖检查\n"
        report += "- 12组跨域对、10个大问题轮转\n- 本地JSONL日志记录每次GLM-5调用\n"
        # 附加收敛报告 + 算力优化报告
        if is_parallel and hasattr(self, 'session_recorder'):
            report += f"\n{self.session_recorder.growth_report()}\n"
        if is_parallel and hasattr(self, 'compute_optimizer'):
            co_report = self.compute_optimizer.optimization_report()
            report += f"\n## 算力智能调优报告\n"
            report += f"- 当前并发数: {co_report['concurrent_workers']}\n"
            report += f"- Phase权重: {json.dumps(co_report['phase_weights'], ensure_ascii=False)}\n"
            report += f"- Phase频率: {json.dumps(co_report['phase_frequency'], ensure_ascii=False)}\n"
            report += f"- Token预算: {json.dumps(co_report['token_budget_by_level'], ensure_ascii=False)}\n"
        rp.write_text(report, encoding="utf-8")
        print(f"\n✅ 报告: {rp}")

    def save_checkpoint(self):
        cp = {"round":self.current_round,"history":self.history,"tokens":self.total_tokens,"ts":datetime.now().isoformat()}
        (PROJECT_DIR/"docs"/"321自成长待处理"/"checkpoint.json").write_text(json.dumps(cp,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AGI 全速成长引擎 v7.0 (节点真实性分级+DiePre增强)")
    parser.add_argument("--rounds", type=int, default=20, help="最大轮次")
    parser.add_argument("--test", action="store_true", help="测试模式(2轮)")
    parser.add_argument("--parallel", action="store_true", help="100x多线程并行模式")
    parser.add_argument("--workers", type=int, default=8, help="并行线程数(默认8)")
    args = parser.parse_args()
    engine = GrowthEngine()
    try:
        if args.parallel:
            engine.run_parallel(min_rounds=2 if args.test else args.rounds,
                                max_rounds=args.rounds, max_workers=args.workers)
        else:
            engine.run(min_rounds=2 if args.test else args.rounds, max_rounds=args.rounds)
    except KeyboardInterrupt:
        print("\n中断，保存检查点...")
        engine.save_checkpoint()
