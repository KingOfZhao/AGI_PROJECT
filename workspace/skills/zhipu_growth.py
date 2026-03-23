#!/usr/bin/env python3
"""
智谱API自主成长引擎 — 闲置时低内存后台运行

核心设计：
- 本地模型闲置时，用智谱API在代码实现领域自我成长
- 可随时打断并续接（进度持久化到JSON文件）
- 智谱API用量检测，不超过总量70%
- 无法处理的问题收集为清单，展示在可视化网页

架构：
  1. 从认知格取hypothesis节点 → 用智谱API验证/深化
  2. 验证通过 → 升级为proven
  3. 验证失败 → 标记为falsified
  4. 无法处理 → 加入问题清单等人工处理
  5. 每步完成后保存进度，可随时中断续接
"""
import sys, json, time, threading, sqlite3, uuid, re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "memory.db"
PROGRESS_FILE = ROOT / "data" / "zhipu_growth_progress.json"
PROBLEMS_FILE = ROOT / "data" / "zhipu_growth_problems.json"
GROWTH_LOG_FILE = ROOT / "data" / "zhipu_growth_log.jsonl"

# 确保data目录存在
(ROOT / "data").mkdir(exist_ok=True)

# ============================================================
# 用量追踪与限额
# ============================================================

QUOTA_FILE = ROOT / "data" / "zhipu_quota.json"
DEFAULT_QUOTA = {
    "daily_limit_tokens": 100000000,  # 每日token上限(1亿)
    "daily_used_tokens": 0,
    "total_limit_tokens": 10000000000, # 总token上限(100亿)
    "total_used_tokens": 0,
    "daily_calls": 0,
    "total_calls": 0,
    "last_reset_date": "",
    "max_usage_ratio": 0.70,          # 不超过70%
    "memory_ratio": 0.15,             # 内存占用上限(占系统总内存百分比)
    "batch_size": 2,                   # 每批处理节点数
    "interval": 120,                   # 成长间隔(秒)
    "consecutive_falsify_threshold": 5, # 连续falsified阈值→自动重置
}


def _load_quota() -> dict:
    if QUOTA_FILE.exists():
        try:
            q = json.loads(QUOTA_FILE.read_text())
            # 每日重置
            today = datetime.now().strftime("%Y-%m-%d")
            if q.get("last_reset_date") != today:
                q["daily_used_tokens"] = 0
                q["daily_calls"] = 0
                q["last_reset_date"] = today
                _save_quota(q)
            return q
        except:
            pass
    q = dict(DEFAULT_QUOTA)
    q["last_reset_date"] = datetime.now().strftime("%Y-%m-%d")
    _save_quota(q)
    return q


def _save_quota(q: dict):
    QUOTA_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2))


def check_quota() -> dict:
    """检查API用量是否超限"""
    q = _load_quota()
    daily_ratio = q["daily_used_tokens"] / max(q["daily_limit_tokens"], 1)
    total_ratio = q["total_used_tokens"] / max(q["total_limit_tokens"], 1)
    max_ratio = q["max_usage_ratio"]

    can_continue = daily_ratio < max_ratio and total_ratio < max_ratio
    return {
        "can_continue": can_continue,
        "daily_used": q["daily_used_tokens"],
        "daily_limit": q["daily_limit_tokens"],
        "daily_ratio": round(daily_ratio, 4),
        "total_used": q["total_used_tokens"],
        "total_limit": q["total_limit_tokens"],
        "total_ratio": round(total_ratio, 4),
        "max_ratio": max_ratio,
        "daily_calls": q["daily_calls"],
        "total_calls": q["total_calls"],
        "reason": "" if can_continue else
            f"已达用量上限({max_ratio:.0%}): 日用{daily_ratio:.1%}, 总用{total_ratio:.1%}",
    }


def record_usage(tokens: int):
    """记录一次API调用的token用量"""
    q = _load_quota()
    q["daily_used_tokens"] += tokens
    q["total_used_tokens"] += tokens
    q["daily_calls"] += 1
    q["total_calls"] += 1
    _save_quota(q)


def update_quota_limits(daily_limit: int = None, total_limit: int = None, max_ratio: float = None,
                        memory_ratio: float = None, batch_size: int = None, interval: int = None):
    """更新配额限制和成长参数"""
    q = _load_quota()
    if daily_limit is not None:
        q["daily_limit_tokens"] = daily_limit
    if total_limit is not None:
        q["total_limit_tokens"] = total_limit
    if max_ratio is not None:
        q["max_usage_ratio"] = max_ratio
    if memory_ratio is not None:
        q["memory_ratio"] = max(0.05, min(0.5, memory_ratio))
    if batch_size is not None:
        q["batch_size"] = max(1, min(10, batch_size))
    if interval is not None:
        q["interval"] = max(30, interval)
    _save_quota(q)


def check_memory() -> dict:
    """检查当前进程内存占用是否超限"""
    import os
    q = _load_quota()
    limit_ratio = q.get("memory_ratio", 0.15)
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        total_mem = psutil.virtual_memory().total
        used_ratio = mem_info.rss / total_mem
        return {
            "ok": used_ratio < limit_ratio,
            "used_mb": round(mem_info.rss / 1048576, 1),
            "total_mb": round(total_mem / 1048576, 1),
            "used_ratio": round(used_ratio, 4),
            "limit_ratio": limit_ratio,
        }
    except ImportError:
        # psutil不可用，返回宽松结果
        return {"ok": True, "used_mb": 0, "total_mb": 0, "used_ratio": 0, "limit_ratio": limit_ratio}


# ============================================================
# 问题清单
# ============================================================

def _load_problems() -> list:
    if PROBLEMS_FILE.exists():
        try:
            return json.loads(PROBLEMS_FILE.read_text())
        except:
            pass
    return []


def _save_problems(problems: list):
    PROBLEMS_FILE.write_text(json.dumps(problems, ensure_ascii=False, indent=2))


def _append_growth_log(entry: dict):
    """追加一条成长日志到JSONL文件"""
    entry["timestamp"] = datetime.now().isoformat()
    with open(GROWTH_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_growth_logs(limit: int = 50, offset: int = 0) -> list:
    """读取最近的成长日志（倒序）"""
    if not GROWTH_LOG_FILE.exists():
        return []
    lines = GROWTH_LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
    logs = []
    for line in reversed(lines):
        if line.strip():
            try:
                logs.append(json.loads(line))
            except:
                pass
            if len(logs) >= offset + limit:
                break
    return logs[offset:offset + limit]


def add_problem(content: str, domain: str, reason: str, node_id: int = None):
    """添加一个无法处理的问题"""
    problems = _load_problems()
    problems.append({
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "domain": domain,
        "reason": reason,
        "node_id": node_id,
        "created_at": datetime.now().isoformat(),
        "status": "pending",  # pending / resolved / dismissed
    })
    _save_problems(problems)


def get_problems(status: str = None) -> list:
    """获取问题清单"""
    problems = _load_problems()
    if status:
        problems = [p for p in problems if p.get("status") == status]
    return problems


def resolve_problem(problem_id: str, resolution: str = ""):
    """标记问题已解决"""
    problems = _load_problems()
    for p in problems:
        if p["id"] == problem_id:
            p["status"] = "resolved"
            p["resolved_at"] = datetime.now().isoformat()
            p["resolution"] = resolution
            break
    _save_problems(problems)


def dismiss_problem(problem_id: str):
    """忽略问题"""
    problems = _load_problems()
    for p in problems:
        if p["id"] == problem_id:
            p["status"] = "dismissed"
            break
    _save_problems(problems)


# ============================================================
# 进度管理（可打断+续接）
# ============================================================

def _load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except:
            pass
    return {
        "last_node_id": 0,
        "processed_ids": [],
        "total_processed": 0,
        "total_promoted": 0,
        "total_falsified": 0,
        "total_problems": 0,
        "cycles_completed": 0,
        "last_run_at": "",
        "status": "idle",  # idle / running / paused / quota_exceeded
    }


def _save_progress(p: dict):
    PROGRESS_FILE.write_text(json.dumps(p, ensure_ascii=False, indent=2))


def get_growth_status() -> dict:
    """获取当前自主成长状态"""
    progress = _load_progress()
    quota = check_quota()
    problems = get_problems("pending")
    return {
        "progress": progress,
        "quota": quota,
        "pending_problems": len(problems),
    }


# ============================================================
# 核心成长逻辑
# ============================================================

# 代码实现领域的hypothesis验证提示词
VERIFY_PROMPT = """你是一位资深软件工程师。请验证以下技术节点的准确性。

节点内容：{content}
领域：{domain}

请判断这个节点是否在代码实现领域是准确的、可验证的知识。

请用JSON格式回复：
{{
  "verdict": "proven" 或 "falsified" 或 "needs_human",
  "confidence": 0.0到1.0的置信度,
  "explanation": "简短解释为什么这样判断",
  "enriched_content": "如果是proven，提供更丰富准确的内容（保留核心要点，补充细节）。如果非proven则留空。",
  "related_topics": ["相关的代码领域话题1", "话题2"]
}}"""

DEEPEN_PROMPT = """你是一位资深软件工程师。请基于以下已验证的知识节点，生成3个在代码实现领域值得深入探索的子话题。

已验证节点：{content}
领域：{domain}

要求：
1. 必须是代码实现领域的具体、可验证的知识
2. 每个子话题应该比原节点更深入更具体
3. 必须是实际编程中有用的知识

请用JSON数组格式回复：
[
  {{"content": "具体的技术知识点", "domain": "具体子领域"}},
  {{"content": "具体的技术知识点", "domain": "具体子领域"}},
  {{"content": "具体的技术知识点", "domain": "具体子领域"}}
]"""

# 代码实现相关领域（精确列表，向后兼容）
CODE_DOMAINS = [
    'Python', 'Python核心', '编程基础', '数据结构', '算法', '软件工程', '架构设计',
    'DevOps', '数据库', '网络', '并发', '安全', 'Dart', 'Flutter', 'Android',
    'iOS', 'Web', '代码实现', '软件开发', '软件架构', '工程实践', '操作系统',
    '分布式系统', '机器学习', '网络协议', '安全工程', '数学基础', '并发编程',
    '技术比较', '跨域模式',
]

# 模糊匹配模式（LIKE %pattern%），覆盖所有技术相关领域
CODE_DOMAIN_PATTERNS = [
    '%Python%', '%编程%', '%数据%', '%算法%', '%软件%', '%架构%', '%DevOps%',
    '%数据库%', '%网络%', '%并发%', '%安全%', '%Dart%', '%Flutter%', '%Android%',
    '%iOS%', '%Web%', '%代码%', '%工程%', '%操作系统%', '%分布式%', '%机器学习%',
    '%AI%', '%测试%', '%部署%', '%设计%', '%优化%', '%前端%', '%后端%', '%API%',
    '%多模态%', '%认知%', '%系统%', '%功能%', '%UI%', '%项目%', '%模型%',
    '%Go%', '%Rust%', '%Java%', '%Swift%', '%MCP%', '%Agent%', '%LLM%',
    '%Transformer%', '%性能%', '%集成%', '%通用%', '%解决方案%', '%能力%',
    '%Engineering%', '%Design%', '%System%', '%Testing%', '%Security%',
    '%Visualization%', '%Concurrency%', '%Database%',
]

# 全速推演模式：聚焦领域（热处理/移动端/本地模型能力）
TURBO_DOMAIN_PATTERNS = [
    '%热处理%', '%温度%', '%控温%', '%PID%', '%材料%', '%铁碳%', '%奥氏体%',
    '%马氏体%', '%退火%', '%淬火%', '%回火%', '%扩散%', '%相变%', '%冶金%',
    '%Flutter%', '%Dart%', '%Android%', '%iOS%', '%蓝牙%', '%BLE%',
    '%移动端%', '%跨平台%', '%Widget%', '%状态管理%', '%路由%', '%动画%',
    '%Ollama%', '%本地模型%', '%认知%', '%自成长%', '%碰撞%', '%embedding%',
    '%AGI%', '%LLM%', '%推理%', '%Agent%', '%MCP%', '%智谱%',
    '%Python%', '%编程%', '%代码%', '%软件%',
]

_growth_thread = None
_growth_stop = threading.Event()


# 当前是否使用GLM-5全速模式
_turbo_mode = False

def set_turbo_mode(enabled: bool):
    global _turbo_mode
    _turbo_mode = enabled

def is_turbo_mode() -> bool:
    return _turbo_mode


def _call_zhipu_for_growth(prompt: str, task_type: str = "reasoning") -> Optional[dict]:
    """调用智谱API进行成长验证，带用量追踪。turbo模式下使用GLM-5。"""
    quota = check_quota()
    if not quota["can_continue"]:
        return {"_quota_exceeded": True, "reason": quota["reason"]}

    import agi_v13_cognitive_lattice as agi

    # turbo模式使用GLM-5 (Anthropic API)，否则用glm-4-flash
    if _turbo_mode:
        glm5_b = agi.BACKENDS.get("zhipu_glm5")
        if glm5_b and glm5_b.get("api_key"):
            return _call_glm5(prompt, glm5_b)

    zhipu_b = agi.BACKENDS.get("zhipu")
    if not zhipu_b or not zhipu_b.get("api_key"):
        return None

    try:
        from openai import OpenAI
        model_map = {"reasoning": "glm-4-flash", "code_gen": "glm-4-flash",
                     "chat": "glm-4-flash"}
        model = model_map.get(task_type, "glm-4-flash")
        client = OpenAI(api_key=zhipu_b["api_key"], base_url=zhipu_b["base_url"])
        resp = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        content = resp.choices[0].message.content.strip()
        tokens = len(prompt) // 2 + len(content) // 2
        record_usage(tokens)
        json_match = re.search(r'[\[{].*[}\]]', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {"raw": content}
    except Exception as e:
        return {"error": str(e)}


def _call_glm5(prompt: str, backend: dict) -> Optional[dict]:
    """使用GLM-5进行高速成长推演。优先Anthropic格式，失败则降级OpenAI格式。"""
    content = ""
    tokens = 0

    # 方式1: Anthropic API格式
    try:
        import httpx
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {backend['api_key']}",
        }
        body = {
            "model": backend.get("model", "glm-5"),
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{backend['base_url']}/v1/messages", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block["text"]
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
    except Exception as e1:
        print(f"  [GLM-5] Anthropic格式失败: {e1}, 尝试OpenAI格式...")
        # 方式2: OpenAI兼容格式（使用zhipu的base_url）
        try:
            import agi_v13_cognitive_lattice as agi
            zhipu_b = agi.BACKENDS.get("zhipu")
            if zhipu_b:
                from openai import OpenAI
                client = OpenAI(api_key=zhipu_b["api_key"], base_url=zhipu_b["base_url"])
                resp = client.chat.completions.create(
                    model="glm-5", max_tokens=4096, temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = resp.choices[0].message.content.strip()
                tokens = getattr(resp.usage, 'total_tokens', 0)
        except Exception as e2:
            print(f"  [GLM-5] OpenAI格式也失败: {e2}")
            return {"error": f"GLM-5双格式均失败: {e1} / {e2}"}

    if not content:
        return {"error": "GLM-5返回空内容"}

    if tokens == 0:
        tokens = len(prompt) // 2 + len(content) // 2
    record_usage(tokens)
    json_match = re.search(r'[\[{].*[}\]]', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    return {"raw": content}


def _get_code_hypothesis_nodes(limit: int = 5, skip_ids: list = None) -> list:
    """获取hypothesis节点 — 模糊匹配所有技术领域"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    skip_clause = ""
    params = []

    if skip_ids:
        skip_placeholders = ",".join("?" * len(skip_ids))
        skip_clause = f" AND id NOT IN ({skip_placeholders})"
        params.extend(skip_ids)

    # 用LIKE模糊匹配所有技术相关领域，而不是精确匹配
    domain_likes = " OR ".join(f"domain LIKE ?" for _ in CODE_DOMAIN_PATTERNS)
    params = list(CODE_DOMAIN_PATTERNS) + params

    c.execute(f"""
        SELECT id, content, domain, status
        FROM cognitive_nodes
        WHERE status = 'hypothesis'
        AND ({domain_likes})
        AND length(content) > 20
        {skip_clause}
        ORDER BY RANDOM()
        LIMIT ?
    """, params + [limit])

    nodes = [dict(r) for r in c.fetchall()]

    # 如果模糊匹配不够，回退到获取所有hypothesis节点
    if len(nodes) < limit:
        existing_ids = [n["id"] for n in nodes]
        all_skip = (skip_ids or []) + existing_ids
        skip_placeholders2 = ",".join("?" * len(all_skip)) if all_skip else "0"
        skip_params2 = all_skip if all_skip else []
        c.execute(f"""
            SELECT id, content, domain, status
            FROM cognitive_nodes
            WHERE status = 'hypothesis'
            AND length(content) > 20
            AND id NOT IN ({skip_placeholders2})
            ORDER BY RANDOM()
            LIMIT ?
        """, skip_params2 + [limit - len(nodes)])
        nodes.extend([dict(r) for r in c.fetchall()])

    conn.close()
    return nodes


def _process_one_node(node: dict) -> dict:
    """处理一个hypothesis节点：验证 → 升级/降级/标记"""
    content = node["content"]
    domain = node["domain"]
    node_id = node["id"]

    # 1. 调用智谱验证
    prompt = VERIFY_PROMPT.format(content=content, domain=domain)
    result = _call_zhipu_for_growth(prompt, "reasoning")

    if result is None:
        add_problem(content, domain, "智谱API不可用", node_id)
        return {"action": "problem", "reason": "API不可用"}

    if result.get("_quota_exceeded"):
        return {"action": "quota_exceeded", "reason": result["reason"]}

    if result.get("error"):
        add_problem(content, domain, f"API错误: {result['error']}", node_id)
        return {"action": "problem", "reason": result["error"]}

    # 2. 解析验证结果
    verdict = result.get("verdict", "needs_human")
    confidence = result.get("confidence", 0)
    explanation = result.get("explanation", "")
    enriched = result.get("enriched_content", "")

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    if verdict == "proven" and confidence >= 0.7:
        # 升级为proven
        final_content = enriched if enriched and len(enriched) > len(content) else content
        c.execute("UPDATE cognitive_nodes SET status = 'proven', content = ? WHERE id = ?",
                  (final_content, node_id))
        conn.commit()
        conn.close()

        # 生成embedding
        try:
            import agi_v13_cognitive_lattice as agi
            emb = agi.get_embedding(final_content)
            if emb:
                conn2 = sqlite3.connect(str(DB_PATH))
                conn2.execute("UPDATE cognitive_nodes SET embedding = ? WHERE id = ?", (emb, node_id))
                conn2.commit()
                conn2.close()
        except:
            pass

        _append_growth_log({"action": "promoted", "node_id": node_id, "domain": domain,
                            "content": final_content[:120], "confidence": confidence,
                            "explanation": explanation[:200]})
        print(f"  [成长✅] #{node_id} [{domain}] → proven ({confidence:.0%}) {content[:50]}")
        return {"action": "promoted", "verdict": verdict, "confidence": confidence,
                "explanation": explanation}

    elif verdict == "falsified" and confidence >= 0.6:
        # 降级为falsified
        c.execute("UPDATE cognitive_nodes SET status = 'falsified' WHERE id = ?", (node_id,))
        conn.commit()
        conn.close()
        _append_growth_log({"action": "falsified", "node_id": node_id, "domain": domain,
                            "content": content[:120], "confidence": confidence,
                            "explanation": explanation[:200]})
        print(f"  [成长❌] #{node_id} [{domain}] → falsified ({confidence:.0%}) {content[:50]}")
        return {"action": "falsified", "verdict": verdict, "confidence": confidence,
                "explanation": explanation}

    else:
        # 无法确定 → 加入问题清单
        conn.close()
        add_problem(content, domain, f"需要人工判断: {explanation}", node_id)
        _append_growth_log({"action": "problem", "node_id": node_id, "domain": domain,
                            "content": content[:120], "confidence": confidence,
                            "explanation": explanation[:200]})
        print(f"  [成长❓] #{node_id} [{domain}] → 待人工 ({confidence:.0%}) {content[:50]}")
        return {"action": "problem", "verdict": verdict, "confidence": confidence,
                "explanation": explanation}


def _deepen_proven_node(node_content: str, domain: str) -> list:
    """对已验证节点生成更深层的子话题"""
    prompt = DEEPEN_PROMPT.format(content=node_content, domain=domain)
    result = _call_zhipu_for_growth(prompt, "reasoning")

    if not result or not isinstance(result, list):
        return []

    new_nodes = []
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    for item in result:
        if isinstance(item, dict) and item.get("content"):
            sub_content = item["content"]
            sub_domain = item.get("domain", domain)
            # 检查是否已存在
            c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ?",
                      (sub_content[:50] + "%",))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO cognitive_nodes (content, domain, status, verified_source)
                    VALUES (?, ?, 'hypothesis', 'zhipu_growth')
                """, (sub_content, sub_domain))
                new_nodes.append({"content": sub_content, "domain": sub_domain})

    conn.commit()
    conn.close()
    return new_nodes


EXPLORE_PROMPT = """你是一位资深全栈工程师和AI系统架构师。请为认知系统生成{count}个新的、具体的、可验证的技术知识点。

当前系统已有的领域覆盖：{existing_domains}

要求：
1. 每个知识点必须是具体、可验证的技术事实（不是问句）
2. 覆盖不同技术领域，优先补充薄弱领域
3. 内容要深入（不少于30字），有实际编程价值
4. 避免重复已有领域中已覆盖的内容

请用JSON数组格式回复：
[
  {{"content": "具体的技术知识点描述", "domain": "所属技术领域"}},
  ...
]"""


def _explore_new_topics(count: int = 10) -> int:
    """用智谱API探索生成新的技术知识点作为hypothesis"""
    # 获取现有领域分布
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT domain, COUNT(*) FROM cognitive_nodes GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 30")
    domains = [f"{r[0]}({r[1]})" for r in c.fetchall()]
    conn.close()

    prompt = EXPLORE_PROMPT.format(count=count, existing_domains=", ".join(domains))
    result = _call_zhipu_for_growth(prompt, "reasoning")

    if not result or not isinstance(result, list):
        # 尝试从raw中提取
        if isinstance(result, dict) and "raw" in result:
            try:
                import re
                m = re.search(r'\[.*\]', result["raw"], re.DOTALL)
                if m:
                    result = json.loads(m.group())
            except:
                pass
        if not isinstance(result, list):
            print(f"  [智谱成长] 探索生成失败: {type(result)}")
            return 0

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    inserted = 0
    for item in result:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        content = item["content"].strip()
        domain = item.get("domain", "通用").strip()
        if len(content) < 20:
            continue
        # 检查重复
        c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ?", (content[:40] + "%",))
        if c.fetchone():
            continue
        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, verified_source)
            VALUES (?, ?, 'hypothesis', 'zhipu_explore')
        """, (content, domain))
        inserted += 1

    conn.commit()
    conn.close()
    _append_growth_log({"action": "explored", "generated": len(result), "inserted": inserted})
    return inserted


def run_growth_cycle(batch_size: int = 3, deepen: bool = True) -> dict:
    """执行一次成长循环

    1. 取batch_size个代码领域hypothesis节点
    2. 用智谱API验证每个节点
    3. 对升级为proven的节点生成子话题
    4. 保存进度

    Returns:
        循环结果统计
    """
    progress = _load_progress()
    skip_ids = progress.get("processed_ids", [])[-200:]  # 只保留最近200个避免无限增长

    nodes = _get_code_hypothesis_nodes(batch_size, skip_ids)
    if not nodes:
        # 无hypothesis节点时，用智谱API探索生成新节点
        print("  [智谱成长] 无hypothesis节点，启动探索生成...")
        _append_growth_log({"action": "explore_start", "reason": "no_hypothesis_nodes"})
        new_count = _explore_new_topics()
        if new_count > 0:
            _append_growth_log({"action": "explore_done", "new_nodes": new_count})
            print(f"  [智谱成长] 探索生成 {new_count} 个新hypothesis节点")
            # 重新获取节点
            nodes = _get_code_hypothesis_nodes(batch_size, skip_ids)
        if not nodes:
            return {"status": "no_nodes", "message": "探索后仍无可处理节点"}

    results = {"promoted": 0, "falsified": 0, "problems": 0, "deepened": 0,
               "quota_exceeded": False, "session_reset": False, "processed": []}

    # F8: 连续falsified计数器（防幻觉漂移）
    consecutive_falsified = progress.get("consecutive_falsified", 0)
    quota_cfg = _load_quota()
    falsify_threshold = quota_cfg.get("consecutive_falsify_threshold", 5)

    for node in nodes:
        if _growth_stop.is_set():
            break

        # 检查配额
        quota = check_quota()
        if not quota["can_continue"]:
            results["quota_exceeded"] = True
            progress["status"] = "quota_exceeded"
            _save_progress(progress)
            break

        # 处理节点
        r = _process_one_node(node)
        action = r.get("action", "unknown")

        if action == "quota_exceeded":
            results["quota_exceeded"] = True
            progress["status"] = "quota_exceeded"
            _save_progress(progress)
            break

        results["processed"].append({
            "node_id": node["id"],
            "content": node["content"][:60],
            "domain": node["domain"],
            "action": action,
            "explanation": r.get("explanation", ""),
        })

        if action == "promoted":
            results["promoted"] += 1
            consecutive_falsified = 0  # 重置连续falsified计数
            # 对新proven节点深化
            if deepen and not _growth_stop.is_set():
                new_nodes = _deepen_proven_node(node["content"], node["domain"])
                results["deepened"] += len(new_nodes)
        elif action == "falsified":
            results["falsified"] += 1
            consecutive_falsified += 1
            # F8: 连续falsified超阈值→自动重置会话（防幻觉漂移）
            if consecutive_falsified >= falsify_threshold:
                print(f"  [智谱成长⚠️] 连续{consecutive_falsified}次falsified，触发自动重置")
                _append_growth_log({"action": "auto_reset",
                                    "reason": f"consecutive_falsified={consecutive_falsified}",
                                    "threshold": falsify_threshold})
                consecutive_falsified = 0
                results["session_reset"] = True
                # 清除已处理ID缓存，允许重新评估
                progress["processed_ids"] = progress.get("processed_ids", [])[-50:]
                # 跳过剩余节点，下个循环重新开始
                break
        elif action == "problem":
            results["problems"] += 1

        # 更新进度
        progress["processed_ids"].append(node["id"])
        progress["total_processed"] += 1
        progress["last_node_id"] = node["id"]
        progress["last_run_at"] = datetime.now().isoformat()

        # 每处理一个节点就保存，确保可随时中断
        _save_progress(progress)

        # 小延迟避免API限流
        time.sleep(1.0)

    progress["total_promoted"] += results["promoted"]
    progress["total_falsified"] += results["falsified"]
    progress["total_problems"] += results["problems"]
    progress["consecutive_falsified"] = consecutive_falsified  # F8: 持久化连续计数
    progress["cycles_completed"] += 1
    _save_progress(progress)

    return results


def start_background_growth(interval: int = 120, batch_size: int = 2):
    """启动后台自主成长（守护线程，低内存）

    Args:
        interval: 每次循环间隔(秒)，默认120秒
        batch_size: 每次处理节点数，默认2个(低内存)
    """
    global _growth_thread
    _growth_stop.clear()

    if _growth_thread and _growth_thread.is_alive():
        return {"status": "already_running"}

    progress = _load_progress()
    progress["status"] = "running"
    _save_progress(progress)

    def _loop():
        # 从配置读取实际参数（支持运行时调整）
        q = _load_quota()
        _interval = q.get("interval", interval)
        _batch = q.get("batch_size", batch_size)
        print(f"  [智谱成长] 后台成长启动，间隔{_interval}s，批量{_batch}")
        while not _growth_stop.is_set():
            try:
                # 动态读取配置（支持运行时调整）
                q = _load_quota()
                _interval = q.get("interval", interval)
                _batch = q.get("batch_size", batch_size)

                # 检查内存占用
                mem = check_memory()
                if not mem["ok"]:
                    print(f"  [智谱成长] 内存超限({mem['used_ratio']:.1%}>{mem['limit_ratio']:.0%})，等待释放...")
                    _growth_stop.wait(60)
                    continue

                # 检查配额
                quota = check_quota()
                if not quota["can_continue"]:
                    print(f"  [智谱成长] 配额已达上限: {quota['reason']}")
                    p = _load_progress()
                    p["status"] = "quota_exceeded"
                    _save_progress(p)
                    break

                result = run_growth_cycle(batch_size=_batch, deepen=True)
                promoted = result.get("promoted", 0)
                falsified = result.get("falsified", 0)
                problems = result.get("problems", 0)
                deepened = result.get("deepened", 0)

                if result.get("status") == "no_nodes":
                    print("  [智谱成长] 无更多节点，暂停5分钟")
                    _growth_stop.wait(300)
                    continue

                if result.get("quota_exceeded"):
                    print(f"  [智谱成长] 配额超限，停止")
                    break

                print(f"  [智谱成长] 循环完成: ✅{promoted} ❌{falsified} ❓{problems} 🌱{deepened}")

            except Exception as e:
                print(f"  [智谱成长] 异常: {e}")

            # 等待间隔（可被中断，使用动态配置）
            _growth_stop.wait(_interval)

        p = _load_progress()
        if p["status"] == "running":
            p["status"] = "paused"
        _save_progress(p)
        print("  [智谱成长] 后台成长已停止")

    _growth_thread = threading.Thread(target=_loop, daemon=True, name="zhipu_growth")
    _growth_thread.start()
    return {"status": "started", "interval": interval, "batch_size": batch_size}


def stop_background_growth():
    """停止后台成长（可随时调用）"""
    _growth_stop.set()
    progress = _load_progress()
    progress["status"] = "paused"
    _save_progress(progress)
    return {"status": "stopped", "progress": progress}


def is_running() -> bool:
    """检查成长是否在运行"""
    return _growth_thread is not None and _growth_thread.is_alive()


# ============================================================
# 全速推演自成长（GLM-5 + 聚焦领域）
# ============================================================

_turbo_thread = None
_turbo_stop = threading.Event()

TURBO_EXPLORE_PROMPT = """你是一位资深工程师，精通热处理工艺控制、Flutter/Dart移动端开发、以及本地AI模型系统架构。
请为认知系统生成{count}个新的、具体的、可验证的技术知识点。

重点领域（必须覆盖）：
1. 热处理/材料科学：温度控制、PID调参、铁碳相图、退火/淬火/回火工艺、扩散系数
2. 移动端开发：Flutter/Dart状态管理、蓝牙BLE通信、跨平台架构、Widget生命周期
3. 本地模型能力：Ollama部署优化、认知格自成长、embedding碰撞、Agent架构、MCP工具

当前系统已有领域：{existing_domains}

要求：
1. 每个知识点必须是具体、可验证的技术事实（不是问句）
2. 三个重点领域各至少占{count}的30%
3. 内容深入（不少于30字），有实际工程价值
4. 避免重复已有内容

请用JSON数组格式回复：
[
  {{"content": "具体的技术知识点描述", "domain": "所属技术领域"}}
]"""


def _get_turbo_hypothesis_nodes(limit: int = 5, skip_ids: list = None) -> list:
    """获取聚焦领域的hypothesis节点（热处理/移动端/本地模型）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    skip_clause = ""
    params = []
    if skip_ids:
        skip_placeholders = ",".join("?" * len(skip_ids))
        skip_clause = f" AND id NOT IN ({skip_placeholders})"
        params.extend(skip_ids)

    domain_likes = " OR ".join(f"domain LIKE ?" for _ in TURBO_DOMAIN_PATTERNS)
    params = list(TURBO_DOMAIN_PATTERNS) + params

    c.execute(f"""
        SELECT id, content, domain, status
        FROM cognitive_nodes
        WHERE status = 'hypothesis'
        AND ({domain_likes})
        AND length(content) > 20
        {skip_clause}
        ORDER BY RANDOM()
        LIMIT ?
    """, params + [limit])

    nodes = [dict(r) for r in c.fetchall()]
    conn.close()
    return nodes


def _turbo_explore(count: int = 15) -> int:
    """用GLM-5探索生成聚焦领域的新hypothesis节点"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT domain, COUNT(*) FROM cognitive_nodes GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 30")
    domains = [f"{r[0]}({r[1]})" for r in c.fetchall()]
    conn.close()

    prompt = TURBO_EXPLORE_PROMPT.format(count=count, existing_domains=", ".join(domains))
    result = _call_zhipu_for_growth(prompt, "reasoning")

    if not result or not isinstance(result, list):
        if isinstance(result, dict) and "raw" in result:
            try:
                m = re.search(r'\[.*\]', result["raw"], re.DOTALL)
                if m:
                    result = json.loads(m.group())
            except:
                pass
        if not isinstance(result, list):
            print(f"  [全速推演] 探索生成失败: {type(result)}")
            return 0

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    inserted = 0
    for item in result:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        content = item["content"].strip()
        domain = item.get("domain", "通用").strip()
        if len(content) < 20:
            continue
        c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ?", (content[:40] + "%",))
        if c.fetchone():
            continue
        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, verified_source)
            VALUES (?, ?, 'hypothesis', 'glm5_turbo_explore')
        """, (content, domain))
        inserted += 1

    conn.commit()
    conn.close()
    _append_growth_log({"action": "turbo_explored", "generated": len(result), "inserted": inserted})
    return inserted


def run_turbo_growth_cycle(batch_size: int = 5, deepen: bool = True) -> dict:
    """执行一次全速推演成长循环（GLM-5 + 聚焦领域 + 大批量）"""
    old_turbo = _turbo_mode
    set_turbo_mode(True)

    try:
        progress = _load_progress()
        skip_ids = progress.get("processed_ids", [])[-200:]

        nodes = _get_turbo_hypothesis_nodes(batch_size, skip_ids)
        if not nodes:
            print("  [全速推演] 聚焦领域无hypothesis，启动GLM-5探索...")
            new_count = _turbo_explore(15)
            if new_count > 0:
                print(f"  [全速推演] 探索生成 {new_count} 个新hypothesis节点")
                nodes = _get_turbo_hypothesis_nodes(batch_size, skip_ids)
            if not nodes:
                # 回退到全领域
                nodes = _get_code_hypothesis_nodes(batch_size, skip_ids)
            if not nodes:
                return {"status": "no_nodes", "message": "探索后仍无可处理节点", "model": "glm-5"}

        results = {"promoted": 0, "falsified": 0, "problems": 0, "deepened": 0,
                   "quota_exceeded": False, "session_reset": False, "processed": [], "model": "glm-5"}

        consecutive_falsified = progress.get("consecutive_falsified", 0)
        quota_cfg = _load_quota()
        falsify_threshold = quota_cfg.get("consecutive_falsify_threshold", 5)

        for node in nodes:
            if _turbo_stop.is_set() or _growth_stop.is_set():
                break
            quota = check_quota()
            if not quota["can_continue"]:
                results["quota_exceeded"] = True
                break

            r = _process_one_node(node)
            action = r.get("action", "unknown")

            if action == "quota_exceeded":
                results["quota_exceeded"] = True
                break

            results["processed"].append({
                "node_id": node["id"],
                "content": node["content"][:60],
                "domain": node["domain"],
                "action": action,
            })

            if action == "promoted":
                results["promoted"] += 1
                consecutive_falsified = 0
                if deepen and not _turbo_stop.is_set():
                    new_nodes = _deepen_proven_node(node["content"], node["domain"])
                    results["deepened"] += len(new_nodes)
            elif action == "falsified":
                results["falsified"] += 1
                consecutive_falsified += 1
                if consecutive_falsified >= falsify_threshold:
                    consecutive_falsified = 0
                    results["session_reset"] = True
                    progress["processed_ids"] = progress.get("processed_ids", [])[-50:]
                    break
            elif action == "problem":
                results["problems"] += 1

            progress["processed_ids"].append(node["id"])
            progress["total_processed"] += 1
            progress["last_node_id"] = node["id"]
            progress["last_run_at"] = datetime.now().isoformat()
            _save_progress(progress)
            time.sleep(0.5)  # GLM-5更快，缩短间隔

        progress["total_promoted"] += results["promoted"]
        progress["total_falsified"] += results["falsified"]
        progress["total_problems"] += results["problems"]
        progress["consecutive_falsified"] = consecutive_falsified
        progress["cycles_completed"] += 1
        _save_progress(progress)
        return results
    finally:
        set_turbo_mode(old_turbo)


def start_turbo_growth(interval: int = 30, batch_size: int = 5):
    """启动全速推演后台成长（GLM-5 + 聚焦领域 + 短间隔 + 大批量）"""
    global _turbo_thread
    _turbo_stop.clear()

    if _turbo_thread and _turbo_thread.is_alive():
        return {"status": "already_running", "model": "glm-5"}

    # 同时停止普通成长避免冲突
    _growth_stop.set()

    progress = _load_progress()
    progress["status"] = "turbo_running"
    _save_progress(progress)

    def _loop():
        print(f"  [全速推演🚀] GLM-5全速模式启动，间隔{interval}s，批量{batch_size}")
        _append_growth_log({"action": "turbo_start", "model": "glm-5", "interval": interval, "batch_size": batch_size})
        cycle = 0
        while not _turbo_stop.is_set():
            try:
                mem = check_memory()
                if not mem["ok"]:
                    print(f"  [全速推演] 内存超限，等待60s...")
                    _turbo_stop.wait(60)
                    continue
                quota = check_quota()
                if not quota["can_continue"]:
                    print(f"  [全速推演] 配额超限，停止")
                    break

                result = run_turbo_growth_cycle(batch_size=batch_size, deepen=True)
                cycle += 1
                promoted = result.get("promoted", 0)
                falsified = result.get("falsified", 0)
                deepened = result.get("deepened", 0)
                problems = result.get("problems", 0)

                if result.get("status") == "no_nodes":
                    print("  [全速推演] 无更多节点，等2分钟后重试")
                    _turbo_stop.wait(120)
                    continue
                if result.get("quota_exceeded"):
                    break

                print(f"  [全速推演🚀] #{cycle}: ✅{promoted} ❌{falsified} ❓{problems} 🌱{deepened}")

            except Exception as e:
                print(f"  [全速推演] 异常: {e}")

            _turbo_stop.wait(interval)

        p = _load_progress()
        if p["status"] == "turbo_running":
            p["status"] = "paused"
        _save_progress(p)
        _append_growth_log({"action": "turbo_stop", "cycles": cycle})
        print(f"  [全速推演] 已停止，共完成{cycle}个循环")

    _turbo_thread = threading.Thread(target=_loop, daemon=True, name="zhipu_turbo_growth")
    _turbo_thread.start()
    return {"status": "started", "model": "glm-5", "interval": interval, "batch_size": batch_size,
            "focus_domains": ["热处理/材料科学", "Flutter/Dart移动端", "本地模型/AGI能力"]}


def stop_turbo_growth():
    """停止全速推演"""
    _turbo_stop.set()
    progress = _load_progress()
    if progress["status"] == "turbo_running":
        progress["status"] = "paused"
    _save_progress(progress)
    return {"status": "stopped"}


def is_turbo_running() -> bool:
    return _turbo_thread is not None and _turbo_thread.is_alive()


# ============================================================
# 批量问题自动处理能力
# ============================================================

def batch_auto_process_problems() -> dict:
    """自动分类并处理所有pending问题节点
    分类规则：
    - API超时/网络错误 → dismiss（瞬态错误）
    - 不存在的模型/版本（幻觉） → dismiss
    - 无意义内容 → dismiss
    - 有效技术问题（超时未验证） → resolve
    - 能力缺口报告 → resolve（已知限制）
    """
    problems = get_problems("pending")
    if not problems:
        return {"total": 0, "resolved": 0, "dismissed": 0}

    resolved = 0
    dismissed = 0

    for p in problems:
        pid = p['id']
        reason = p.get('reason', '')
        content = p.get('content', '')

        # 1. API瞬态错误 → dismiss
        if any(kw in reason for kw in ['timed out', 'Connection error', 'Connection reset']):
            dismiss_problem(pid)
            dismissed += 1
        # 2. 不存在的模型幻觉 → dismiss
        elif 'Claude Opus 4.6' in content:
            dismiss_problem(pid)
            dismissed += 1
        # 3. 无意义内容 → dismiss
        elif '龙虾' in content:
            dismiss_problem(pid)
            dismissed += 1
        # 4. 能力缺口报告 → resolve
        elif '能力缺口' in content:
            resolve_problem(pid, '已知能力缺口，已通过F6能力缺口检测器记录。')
            resolved += 1
        # 5. 有效技术问题 → resolve
        elif any(kw in content for kw in ['Flutter', 'Dart', 'Reflexion', 'Selenium', 'Nginx',
                                           'Java', 'C#', 'Go语言', 'Python', 'AES', 'LRU',
                                           '热处理', '温度', '蓝牙', 'BLE', 'Ollama',
                                           '机器学习', 'Pandas', 'Hive']):
            resolve_problem(pid, '有效技术问题，因API超时/限制未完成自动验证，内容已归档。')
            resolved += 1
        # 6. 其他 → dismiss
        else:
            dismiss_problem(pid)
            dismissed += 1

    _append_growth_log({
        "action": "batch_auto_process",
        "total": len(problems),
        "resolved": resolved,
        "dismissed": dismissed,
    })

    return {"total": len(problems), "resolved": resolved, "dismissed": dismissed, "remaining": len(get_problems("pending"))}


# ============================================================
# 命令行测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  智谱API自主成长引擎 · 测试")
    print("=" * 50)

    # 测试1: 配额检查
    print("\n1. 配额检查:")
    q = check_quota()
    print(f"  可继续: {q['can_continue']}")
    print(f"  日用: {q['daily_used']}/{q['daily_limit']} ({q['daily_ratio']:.1%})")
    print(f"  总用: {q['total_used']}/{q['total_limit']} ({q['total_ratio']:.1%})")

    # 测试2: 获取hypothesis节点
    print("\n2. 代码领域hypothesis节点:")
    nodes = _get_code_hypothesis_nodes(3)
    for n in nodes:
        print(f"  [{n['domain']}] {n['content'][:60]}...")
    print(f"  共 {len(nodes)} 个")

    # 测试3: 执行一次成长循环(1个节点)
    if nodes and q['can_continue']:
        print("\n3. 执行单节点成长循环:")
        result = run_growth_cycle(batch_size=1, deepen=False)
        for p in result.get("processed", []):
            icon = {"promoted": "✅", "falsified": "❌", "problem": "❓"}.get(p["action"], "?")
            print(f"  {icon} [{p['domain']}] {p['content'][:50]}...")
            print(f"     → {p['action']}: {p['explanation'][:60]}")

    # 测试4: 问题清单
    print("\n4. 问题清单:")
    problems = get_problems()
    print(f"  共 {len(problems)} 个待处理问题")
    for p in problems[:3]:
        print(f"  [{p['domain']}] {p['content'][:50]}... ({p['reason'][:30]})")

    # 测试5: 成长状态
    print("\n5. 成长状态:")
    status = get_growth_status()
    print(f"  状态: {status['progress']['status']}")
    print(f"  已处理: {status['progress']['total_processed']}")
    print(f"  已升级: {status['progress']['total_promoted']}")
    print(f"  已淘汰: {status['progress']['total_falsified']}")
    print(f"  待处理问题: {status['pending_problems']}")

    print("\n  完成!")
