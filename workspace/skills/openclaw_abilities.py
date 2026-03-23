"""
OpenClaw 可复用能力集成模块

从OpenClaw项目中提取的4个核心算法，移植为Python实现：
1. MMR (Maximal Marginal Relevance) — 多样性重排
2. Temporal Decay — 时间衰减评分
3. Query Expansion — 查询扩展
4. Verifiability Classification — 可验证性分类

这些能力直接增强本地模型的搜索、记忆和推理质量。
"""
import re, math, time
from typing import List, Dict, Any, Optional, Set, Tuple


# ============================================================
# 1. MMR (Maximal Marginal Relevance) 多样性重排
# 来源: OpenClaw src/memory/mmr.ts
# 用途: 搜索结果去重，确保覆盖不同角度
# ============================================================

def tokenize(text: str) -> Set[str]:
    """提取文本中的有意义token（支持中英文）
    
    中文使用2-gram切分（因为中文没有空格分词），
    英文使用空格/标点分词。
    """
    en_tokens = set(re.findall(r'[a-z0-9_]+', text.lower()))
    # 中文2-gram切分
    cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
    cn_tokens = set()
    for i in range(len(cn_chars)):
        cn_tokens.add(cn_chars[i])  # 单字
        if i + 1 < len(cn_chars):
            cn_tokens.add(cn_chars[i] + cn_chars[i + 1])  # 二字词
    return en_tokens | cn_tokens


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard相似度：交集/并集"""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def text_similarity(content_a: str, content_b: str) -> float:
    """文本相似度（基于Jaccard token匹配）"""
    return jaccard_similarity(tokenize(content_a), tokenize(content_b))


def mmr_rerank(items: List[Dict[str, Any]], lam: float = 0.7,
               score_key: str = 'similarity', content_key: str = 'content') -> List[Dict[str, Any]]:
    """
    MMR多样性重排算法
    
    平衡相关性与多样性：
    MMR = λ * relevance - (1-λ) * max_similarity_to_selected
    
    Args:
        items: 待重排列表，每项必须有score_key和content_key
        lam: λ参数，0=最大多样性，1=最大相关性，推荐0.7
        score_key: 分数字段名
        content_key: 内容字段名
    Returns:
        重排后的列表
    
    来源: Carbonell & Goldstein 1998
    """
    if len(items) <= 1:
        return list(items)
    
    lam = max(0.0, min(1.0, lam))
    
    # 预计算token
    token_cache = {}
    for i, item in enumerate(items):
        token_cache[i] = tokenize(item.get(content_key, ''))
    
    # 归一化分数到[0,1]
    # 当分数范围很窄时(如0.8-0.9)，标准归一化会放大微小差异
    # 使用 max-normalization 保持比例关系
    scores = [item.get(score_key, 0) for item in items]
    max_score = max(scores) if scores else 1
    min_score = min(scores) if scores else 0
    score_range = max_score - min_score
    
    def normalize(s):
        if score_range > 0 and score_range / max_score > 0.3:
            return (s - min_score) / score_range
        # 窄范围：用 max-normalization 保持比例
        return s / max_score if max_score > 0 else 1.0
    
    selected = []
    selected_indices = []
    remaining = set(range(len(items)))
    
    while remaining:
        best_idx = None
        best_mmr = float('-inf')
        
        for idx in remaining:
            relevance = normalize(items[idx].get(score_key, 0))
            
            # 计算与已选项的最大相似度
            max_sim = 0.0
            for sel_idx in selected_indices:
                sim = jaccard_similarity(token_cache[idx], token_cache[sel_idx])
                max_sim = max(max_sim, sim)
            
            mmr_score = lam * relevance - (1 - lam) * max_sim
            
            if mmr_score > best_mmr or (mmr_score == best_mmr and 
                    items[idx].get(score_key, 0) > (items[best_idx].get(score_key, 0) if best_idx is not None else float('-inf'))):
                best_mmr = mmr_score
                best_idx = idx
        
        if best_idx is not None:
            selected.append(items[best_idx])
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
        else:
            break
    
    return selected


# ============================================================
# 2. Temporal Decay 时间衰减
# 来源: OpenClaw src/memory/temporal-decay.ts
# 用途: 让新信息权重高于旧信息
# ============================================================

def temporal_decay_multiplier(age_days: float, half_life_days: float = 30.0) -> float:
    """
    计算时间衰减乘数
    
    使用指数衰减模拟人类记忆遗忘曲线：
    multiplier = exp(-λ * age_days)，其中 λ = ln2 / half_life_days
    
    Args:
        age_days: 内容年龄（天数）
        half_life_days: 半衰期（天数），默认30天
    Returns:
        衰减乘数 [0, 1]，1=最新，→0=越老
    """
    if half_life_days <= 0 or not math.isfinite(age_days):
        return 1.0
    lam = math.log(2) / half_life_days
    return math.exp(-lam * max(0, age_days))


def apply_temporal_decay(items: List[Dict[str, Any]], 
                          score_key: str = 'similarity',
                          time_key: str = 'created_at',
                          half_life_days: float = 30.0,
                          now: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    对搜索结果应用时间衰减
    
    Args:
        items: 搜索结果列表
        score_key: 分数字段
        time_key: 时间字段（epoch秒 或 ISO字符串）
        half_life_days: 半衰期
        now: 当前时间（epoch秒），默认time.time()
    Returns:
        应用衰减后的结果（按新分数排序）
    """
    if now is None:
        now = time.time()
    
    results = []
    for item in items:
        item_copy = dict(item)
        
        # 解析时间
        t = item.get(time_key)
        if t is None:
            age_days = 0
        elif isinstance(t, (int, float)):
            age_days = (now - t) / 86400
        elif isinstance(t, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                age_days = (now - dt.timestamp()) / 86400
            except:
                age_days = 0
        else:
            age_days = 0
        
        decay = temporal_decay_multiplier(age_days, half_life_days)
        original_score = item.get(score_key, 0)
        item_copy['_original_score'] = original_score
        item_copy['_decay'] = round(decay, 4)
        item_copy[score_key] = original_score * decay
        results.append(item_copy)
    
    results.sort(key=lambda x: x.get(score_key, 0), reverse=True)
    return results


# ============================================================
# 3. Query Expansion 查询扩展
# 来源: OpenClaw src/memory/query-expansion.ts
# 用途: 将口语化查询转为搜索关键词
# ============================================================

STOP_WORDS_EN = {
    'a', 'an', 'the', 'this', 'that', 'these', 'those',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they', 'them',
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'can', 'may', 'might',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
    'about', 'into', 'through', 'during', 'before', 'after',
    'and', 'or', 'but', 'if', 'not', 'no', 'so', 'just', 'also',
    'what', 'when', 'where', 'how', 'why', 'who', 'which',
    'very', 'really', 'quite', 'much', 'more', 'most',
    'some', 'any', 'all', 'each', 'every', 'both',
}

STOP_WORDS_CN = {
    '的', '了', '在', '是', '我', '有', '和', '就',
    '不', '人', '都', '一', '个', '上', '也', '很',
    '到', '说', '要', '去', '你', '会', '着', '没有',
    '看', '好', '自己', '这', '他', '么', '把', '那',
    '她', '它', '吗', '什么', '怎么', '如何', '为什么',
    '能', '可以', '还', '吧', '呢', '啊', '请', '帮',
}


def expand_query(raw: str) -> Dict[str, Any]:
    """
    查询扩展：将口语化查询转为结构化搜索

    Returns:
        {
            'original': 原始查询,
            'keywords_en': 英文关键词列表,
            'keywords_cn': 中文关键词列表,
            'fts_query': FTS搜索语句(AND连接),
            'domain_hints': 检测到的领域提示,
        }
    """
    # 提取英文词
    en_words = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*', raw)
    en_keywords = [w.lower() for w in en_words if w.lower() not in STOP_WORDS_EN and len(w) > 1]
    
    # 提取中文词
    cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', raw)
    cn_keywords = [w for w in cn_words if w not in STOP_WORDS_CN]
    
    # 构建FTS查询
    all_keywords = en_keywords + cn_keywords
    fts_query = ' AND '.join(f'"{kw}"' for kw in all_keywords) if all_keywords else None
    
    # 领域提示检测（不用\b，因为中英混合文本中\b无法正确匹配）
    domain_hints = []
    domain_keywords_map = {
        'python': ['python', 'django', 'flask', 'fastapi', 'pip', 'pytest'],
        'dart': ['dart', 'flutter', 'widget', 'pubspec'],
        'web': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'nodejs'],
        'database': ['sql', 'sqlite', 'mysql', 'postgres', 'mongodb', 'redis'],
        'devops': ['docker', 'k8s', 'kubernetes', 'nginx', 'deploy'],
        'ai': ['llm', 'gpt', 'embedding', 'neural', '训练', '推理', '模型'],
        'agi': ['认知格', 'cognitive', 'lattice', '碰撞', '拆解', 'proven'],
    }
    raw_lower = raw.lower()
    for domain, kws in domain_keywords_map.items():
        if any(kw in raw_lower for kw in kws):
            domain_hints.append(domain)
    
    return {
        'original': raw,
        'keywords_en': en_keywords,
        'keywords_cn': cn_keywords,
        'fts_query': fts_query,
        'domain_hints': domain_hints,
    }


# ============================================================
# 4. Verifiability Classification 可验证性分类
# 来源: OpenClaw src/agents/cognitive-lattice.ts
# 用途: 自动判断节点是否可通过实践直接验证
# ============================================================

CONCRETE_PATTERNS = [
    # 动作动词（表示可直接执行）
    re.compile(r'^(run|execute|create|write|build|test|measure|count|install|configure|deploy|check|verify|record|open|send|call)\b', re.I),
    re.compile(r'^(运行|执行|创建|编写|构建|测试|测量|计数|安装|配置|部署|检查|验证|记录|打开|发送|调用)', re.I),
    # 包含具体数量或时间
    re.compile(r'\d+\s*(人|次|个|天|小时|分钟|秒|minutes?|hours?|days?|times?|items?|people)', re.I),
    # 包含文件路径、命令或URL
    re.compile(r'[/\\][\w.-]+\.\w+|`[^`]+`|https?://'),
]

ABSTRACT_PATTERNS = [
    # 疑问形式
    re.compile(r'^(如何|怎[么样]|为什么|是否|how|why|whether|should|could|would)\b', re.I),
    # 抽象目标
    re.compile(r'\b(成功|最佳|完美|优化|提升|理想|achieve|optimize|perfect|ideal|best)\b', re.I),
]


def classify_verifiability(content: str) -> Dict[str, Any]:
    """
    判断内容是否可通过实践直接验证
    
    可验证 = 具体动作，人类可以直接做并验证结果
    不可验证 = 抽象概念，需要进一步拆解才能验证
    
    Returns:
        {
            'can_verify': True/False,
            'concrete_score': 具体性得分,
            'abstract_score': 抽象性得分,
            'classification': 'verifiable' | 'needs_decomposition',
            'reason': 分类原因
        }
    """
    concrete_score = sum(1 for p in CONCRETE_PATTERNS if p.search(content))
    abstract_score = sum(1 for p in ABSTRACT_PATTERNS if p.search(content))
    
    can_verify = concrete_score > abstract_score
    
    if can_verify:
        reason = "包含具体动作/数量/路径，可直接实践验证"
    elif abstract_score > 0:
        reason = "包含抽象目标/疑问，需要自上而下拆解"
    else:
        reason = "内容中性，默认为需要拆解"
    
    return {
        'can_verify': can_verify,
        'concrete_score': concrete_score,
        'abstract_score': abstract_score,
        'classification': 'verifiable' if can_verify else 'needs_decomposition',
        'reason': reason,
    }


# ============================================================
# 5. 增强版搜索：组合以上所有能力
# ============================================================

def enhanced_search(query: str, raw_results: List[Dict[str, Any]],
                     mmr_lambda: float = 0.7,
                     decay_half_life: float = 30.0,
                     apply_mmr: bool = True,
                     apply_decay: bool = False) -> Dict[str, Any]:
    """
    增强版搜索管道：查询扩展 → 时间衰减 → MMR重排
    
    组合OpenClaw的4个核心算法提供最佳搜索体验。
    
    Args:
        query: 原始查询
        raw_results: 原始搜索结果
        mmr_lambda: MMR多样性参数
        decay_half_life: 时间衰减半衰期（天）
        apply_mmr: 是否启用MMR
        apply_decay: 是否启用时间衰减
    Returns:
        {
            'query_analysis': 查询分析结果,
            'results': 重排后的结果,
            'stats': 统计信息
        }
    """
    # 1. 查询扩展
    query_analysis = expand_query(query)
    
    results = list(raw_results)
    
    # 2. 时间衰减
    if apply_decay and results:
        results = apply_temporal_decay(results, half_life_days=decay_half_life)
    
    # 3. MMR重排
    if apply_mmr and len(results) > 1:
        results = mmr_rerank(results, lam=mmr_lambda)
    
    return {
        'query_analysis': query_analysis,
        'results': results,
        'stats': {
            'total_results': len(results),
            'keywords': query_analysis['keywords_en'] + query_analysis['keywords_cn'],
            'domains': query_analysis['domain_hints'],
            'mmr_applied': apply_mmr,
            'decay_applied': apply_decay,
        }
    }
