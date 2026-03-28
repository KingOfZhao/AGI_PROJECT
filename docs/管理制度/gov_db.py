#!/usr/bin/env python3
"""治理推演引擎 v2.0 — 数据库 + 搜索模块"""

import json
import re
import time
import hashlib
import threading
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "governance_reasoning.db"
CACHE_PATH = SCRIPT_DIR / ".gov_search_cache.json"

# ==================== 数据库 ====================
class GovernanceDB:
    """治理推演数据库: sessions/nodes/hierarchies/rebels/factions/dynasties"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_tables()
        self._migrate_v2()

    def _migrate_v2(self):
        """Migrate v1 DB schema to v2: add missing columns to existing tables"""
        migrations = [
            ("gov_sessions", "dynasty_num", "INTEGER DEFAULT 1"),
            ("gov_nodes", "phase", "TEXT DEFAULT ''"),
            ("gov_hierarchies", "faction_id", "TEXT DEFAULT 'main'"),
            ("gov_reasoning_logs", "phase", "TEXT DEFAULT ''"),
        ]
        for table, col, coltype in migrations:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                self.conn.commit()
            except Exception:
                pass  # column already exists

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS gov_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                dynasty_num INTEGER DEFAULT 1,
                started_at TEXT,
                ended_at TEXT,
                status TEXT DEFAULT 'running',
                summary TEXT
            );
            CREATE TABLE IF NOT EXISTS gov_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, content TEXT, node_type TEXT, source TEXT,
                confidence REAL DEFAULT 0.5, reality TEXT DEFAULT 'inferred',
                collision_round INTEGER, phase TEXT DEFAULT '',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS gov_hierarchies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, round_num INTEGER, hierarchy_json TEXT,
                overthrow_reason TEXT, score REAL DEFAULT 0,
                faction_id TEXT DEFAULT 'main',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS gov_reasoning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, round_num INTEGER, direction TEXT,
                role TEXT, content TEXT, phase TEXT DEFAULT '',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS gov_node_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, from_node_id INTEGER, to_node_id INTEGER,
                relation_type TEXT, description TEXT, round_num INTEGER,
                created_at TEXT
            );
            -- v2.0 反贼表
            CREATE TABLE IF NOT EXISTS gov_rebels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                rebel_name TEXT,
                rebel_type TEXT,
                description TEXT,
                severity TEXT DEFAULT 'medium',
                target_level INTEGER DEFAULT -1,
                suppression_count INTEGER DEFAULT 0,
                max_suppression INTEGER DEFAULT 3,
                status TEXT DEFAULT 'active',
                suppression_log TEXT DEFAULT '[]',
                source_round INTEGER,
                created_at TEXT,
                resolved_at TEXT
            );
            -- v2.0 派系表 (群雄割据)
            CREATE TABLE IF NOT EXISTS gov_factions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                faction_id TEXT,
                faction_name TEXT,
                hierarchy_json TEXT,
                origin TEXT,
                score REAL DEFAULT 0,
                rebel_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'competing',
                created_at TEXT
            );
            -- v2.0 王朝表 (一统记录)
            CREATE TABLE IF NOT EXISTS gov_dynasties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                dynasty_num INTEGER,
                dynasty_name TEXT,
                hierarchy_json TEXT,
                total_rebels INTEGER DEFAULT 0,
                suppressed_rebels INTEGER DEFAULT 0,
                unsuppressed_rebels INTEGER DEFAULT 0,
                final_score REAL DEFAULT 0,
                overthrown_by TEXT,
                status TEXT DEFAULT 'ruling',
                created_at TEXT,
                ended_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_rebels_session ON gov_rebels(session_id);
            CREATE INDEX IF NOT EXISTS idx_rebels_status ON gov_rebels(status);
            CREATE INDEX IF NOT EXISTS idx_factions_session ON gov_factions(session_id);
            CREATE INDEX IF NOT EXISTS idx_dynasties_session ON gov_dynasties(session_id);
            CREATE INDEX IF NOT EXISTS idx_gov_nodes_session ON gov_nodes(session_id);
            CREATE INDEX IF NOT EXISTS idx_gov_hier_session ON gov_hierarchies(session_id);
            CREATE INDEX IF NOT EXISTS idx_gov_logs_session ON gov_reasoning_logs(session_id);
        """)
        self.conn.commit()

    def _exec(self, sql, params=()):
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def create_session(self, dynasty_num=1):
        sid = f"gov_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        self._exec("INSERT INTO gov_sessions (session_id, dynasty_num, started_at, status) VALUES (?,?,?,?)",
                    (sid, dynasty_num, datetime.now().isoformat(), "running"))
        return sid

    def save_node(self, session_id, content, node_type, source, confidence=0.5,
                  reality="inferred", collision_round=0, phase=""):
        cur = self._exec("""INSERT INTO gov_nodes
            (session_id, content, node_type, source, confidence, reality, collision_round, phase, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (session_id, content, node_type, source, confidence, reality,
             collision_round, phase, datetime.now().isoformat()))
        return cur.lastrowid

    def save_hierarchy(self, session_id, round_num, hierarchy, overthrow_reason, score=0, faction_id="main"):
        self._exec("""INSERT INTO gov_hierarchies
            (session_id, round_num, hierarchy_json, overthrow_reason, score, faction_id, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (session_id, round_num, json.dumps(hierarchy, ensure_ascii=False),
             overthrow_reason, score, faction_id, datetime.now().isoformat()))

    def save_log(self, session_id, round_num, direction, role, content, phase=""):
        self._exec("""INSERT INTO gov_reasoning_logs
            (session_id, round_num, direction, role, content, phase, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (session_id, round_num, direction, role,
             content[:50000] if content else "", phase, datetime.now().isoformat()))

    def save_relation(self, session_id, from_id, to_id, rel_type, description="", round_num=0):
        self._exec("""INSERT INTO gov_node_relations
            (session_id, from_node_id, to_node_id, relation_type, description, round_num, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (session_id, from_id, to_id, rel_type, description, round_num, datetime.now().isoformat()))

    # ---- 反贼 CRUD ----
    def create_rebel(self, session_id, name, rebel_type, description, severity="medium",
                     target_level=-1, source_round=0):
        cur = self._exec("""INSERT INTO gov_rebels
            (session_id, rebel_name, rebel_type, description, severity, target_level,
             source_round, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (session_id, name, rebel_type, description, severity, target_level,
             source_round, "active", datetime.now().isoformat()))
        return cur.lastrowid

    def update_rebel_suppression(self, rebel_id, attempt_log, new_status="active"):
        row = self.conn.execute("SELECT suppression_log, suppression_count FROM gov_rebels WHERE id=?",
                                (rebel_id,)).fetchone()
        if not row:
            return
        logs = json.loads(row["suppression_log"] or "[]")
        logs.append(attempt_log)
        count = (row["suppression_count"] or 0) + 1
        resolved_at = datetime.now().isoformat() if new_status == "suppressed" else None
        self._exec("""UPDATE gov_rebels SET suppression_log=?, suppression_count=?, status=?, resolved_at=?
                      WHERE id=?""",
                   (json.dumps(logs, ensure_ascii=False), count, new_status, resolved_at, rebel_id))

    def get_active_rebels(self, session_id):
        rows = self.conn.execute(
            "SELECT * FROM gov_rebels WHERE session_id=? AND status='active' ORDER BY severity DESC",
            (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_all_rebels(self, session_id):
        rows = self.conn.execute("SELECT * FROM gov_rebels WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_unsuppressed_rebels(self, session_id):
        rows = self.conn.execute(
            "SELECT * FROM gov_rebels WHERE session_id=? AND status IN ('active','unsuppressable')",
            (session_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- 派系 CRUD ----
    def create_faction(self, session_id, faction_id, name, hierarchy, origin="split"):
        self._exec("""INSERT INTO gov_factions
            (session_id, faction_id, faction_name, hierarchy_json, origin, status, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (session_id, faction_id, name,
             json.dumps(hierarchy, ensure_ascii=False), origin, "competing", datetime.now().isoformat()))

    def update_faction_score(self, session_id, faction_id, score, rebel_count=0):
        self._exec("UPDATE gov_factions SET score=?, rebel_count=? WHERE session_id=? AND faction_id=?",
                   (score, rebel_count, session_id, faction_id))

    def get_factions(self, session_id):
        rows = self.conn.execute("SELECT * FROM gov_factions WHERE session_id=? AND status='competing'",
                                 (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def crown_faction(self, session_id, winner_id):
        self._exec("UPDATE gov_factions SET status='defeated' WHERE session_id=? AND faction_id!=?",
                   (session_id, winner_id))
        self._exec("UPDATE gov_factions SET status='unified' WHERE session_id=? AND faction_id=?",
                   (session_id, winner_id))

    # ---- 王朝 CRUD ----
    def create_dynasty(self, session_id, dynasty_num, name, hierarchy, total_rebels=0,
                       suppressed=0, unsuppressed=0, score=0):
        self._exec("""INSERT INTO gov_dynasties
            (session_id, dynasty_num, dynasty_name, hierarchy_json, total_rebels,
             suppressed_rebels, unsuppressed_rebels, final_score, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session_id, dynasty_num, name,
             json.dumps(hierarchy, ensure_ascii=False), total_rebels,
             suppressed, unsuppressed, score, "ruling", datetime.now().isoformat()))

    def overthrow_dynasty(self, session_id, dynasty_num, reason):
        self._exec("""UPDATE gov_dynasties SET status='overthrown', overthrown_by=?, ended_at=?
                      WHERE session_id=? AND dynasty_num=?""",
                   (reason, datetime.now().isoformat(), session_id, dynasty_num))

    def get_dynasties(self, session_id):
        rows = self.conn.execute("SELECT * FROM gov_dynasties WHERE session_id=? ORDER BY dynasty_num",
                                 (session_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- 通用查询 ----
    def get_all_nodes(self, session_id):
        rows = self.conn.execute("SELECT * FROM gov_nodes WHERE session_id=? ORDER BY collision_round",
                                 (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_logs(self, session_id, round_num=None):
        if round_num is not None:
            rows = self.conn.execute("SELECT * FROM gov_reasoning_logs WHERE session_id=? AND round_num=?",
                                     (session_id, round_num)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM gov_reasoning_logs WHERE session_id=? ORDER BY round_num",
                                     (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_relations(self, session_id):
        rows = self.conn.execute("SELECT * FROM gov_node_relations WHERE session_id=? ORDER BY round_num",
                                 (session_id,)).fetchall()
        return [dict(r) for r in rows]

    def end_session(self, session_id, summary):
        self._exec("UPDATE gov_sessions SET ended_at=?, status=?, summary=? WHERE session_id=?",
                    (datetime.now().isoformat(), "completed", summary, session_id))

    def close(self):
        self.conn.close()


# ==================== 搜索引擎 ====================
class GovernanceSearcher:
    """搜索各国治理体系、军事编制、文明兴亡、开源最佳实践、前沿论文"""

    SEARCH_TOPICS = [
        # 中国历史治理
        {"query": "中国历代官制演变 秦汉三公九卿 唐三省六部", "category": "china_gov"},
        {"query": "中国古代军事编制 卫所制 八旗 绿营", "category": "china_military"},
        {"query": "PLA军改 集团军旅营 合成化扁平化", "category": "china_modern_military"},
        # 罗马帝国
        {"query": "Roman Empire governance provincial administration hierarchy", "category": "rome_gov"},
        {"query": "Roman legion organization centurion cohort maniple", "category": "rome_military"},
        # 蒙古帝国
        {"query": "Mongol Empire decimal system tumen mingghan", "category": "mongol"},
        # 欧洲近现代
        {"query": "Prussian military staff system Auftragstaktik mission command", "category": "prussia"},
        {"query": "Napoleon Grande Armee corps division organization", "category": "napoleon"},
        {"query": "British civil service reform Northcote Trevelyan", "category": "britain_gov"},
        # 美军
        {"query": "US Army modular brigade combat team organization structure", "category": "us_military"},
        {"query": "US military joint operations command structure", "category": "us_joint"},
        # 日本
        {"query": "日本明治维新官制改革 废藩置县 内阁制", "category": "japan_gov"},
        {"query": "Toyota production system lean management hierarchy", "category": "japan_mgmt"},
        # 科技公司治理
        {"query": "Google engineering management structure flat organization", "category": "tech_flat"},
        {"query": "Amazon two pizza team organizational structure", "category": "tech_amazon"},
        {"query": "Valve flat hierarchy no managers game company", "category": "tech_valve"},
        {"query": "ByteDance OKR organizational management structure", "category": "tech_bytedance"},
        # 开源治理
        {"query": "Linux kernel development governance BDFL maintainer", "category": "opensource"},
        {"query": "Apache Software Foundation governance model meritocracy", "category": "opensource"},
        # AI Agent编排 (v2.0新增)
        {"query": "multi-agent orchestration framework LangGraph CrewAI AutoGen", "category": "ai_agent"},
        {"query": "LLM chain of thought tree of thought reasoning architecture", "category": "ai_reasoning"},
        {"query": "AI agent hierarchy supervisor worker pattern best practice", "category": "ai_hierarchy"},
        # 文明失败
        {"query": "why empires fall bureaucracy corruption overextension", "category": "failure"},
        {"query": "organizational failure too many management layers", "category": "failure"},
        # 管辖幅度理论
        {"query": "span of control optimal management layers research", "category": "theory"},
        {"query": "information loss hierarchy levels communication research", "category": "theory"},
    ]

    ACADEMIC_TOPICS = [
        {"query": "optimal span of control organizational hierarchy", "category": "academic"},
        {"query": "military command structure effectiveness combat", "category": "academic"},
        {"query": "flat vs hierarchical organization performance", "category": "academic"},
        {"query": "multi-agent system coordination hierarchy efficiency", "category": "academic"},
        {"query": "LLM agent orchestration scalability", "category": "academic"},
    ]

    CACHE_TTL_DAYS = 7

    def __init__(self):
        self.results = []
        self._cache = self._load_cache()

    @staticmethod
    def _load_cache():
        if CACHE_PATH.exists():
            try:
                data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                cached_at = data.get("cached_at", "")
                if cached_at:
                    age = (datetime.now() - datetime.fromisoformat(cached_at)).days
                    if age <= GovernanceSearcher.CACHE_TTL_DAYS:
                        return data
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def _has_valid_cache(self):
        return bool(self._cache.get("results")) and bool(self._cache.get("flat"))

    def _save_cache(self, all_results):
        cache = {"cached_at": datetime.now().isoformat(), "results": all_results, "flat": self.results}
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _search_ddg_html(self, query, max_results=5):
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            results = []
            title_matches = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', html)
            snippet_matches = re.findall(r'class="result__snippet"[^>]*>(.+?)</a>', html, re.DOTALL)
            for i, (href, title) in enumerate(title_matches[:max_results]):
                snippet = re.sub(r'<[^>]+>', '', snippet_matches[i]).strip() if i < len(snippet_matches) else ""
                if "uddg=" in href:
                    m = re.search(r'uddg=([^&]+)', href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                results.append({"title": title.strip()[:100], "snippet": snippet[:300], "url": href, "source": "ddg_html"})
            return results
        except Exception as e:
            return [{"title": f"搜索失败: {query[:30]}", "snippet": str(e)[:80], "url": "", "source": "error"}]

    def _search_github(self, query, max_results=5):
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&per_page={max_results}"
            headers = {"User-Agent": "Gov-Engine/2.0", "Accept": "application/vnd.github.v3+json"}
            github_token = ""
            env_path = Path("/Users/administruter/Desktop/DiePre AI/.env")
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    l = line.strip()
                    if l and not l.startswith("#") and "GITHUB_TOKEN=" in l:
                        github_token = l.split("=", 1)[1].strip().strip('"').strip("'")
            if not github_token:
                import os
                github_token = os.environ.get("GITHUB_TOKEN", "")
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [{"title": it["full_name"], "snippet": it.get("description", "") or "",
                      "url": it["html_url"], "source": "github"} for it in data.get("items", [])[:max_results]]
        except Exception:
            return []

    def _search_semantic_scholar(self, query, max_results=5):
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded}&limit={max_results}&fields=title,abstract,url,year,citationCount"
            req = urllib.request.Request(url, headers={"User-Agent": "Gov-Engine/2.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            for p in data.get("data", [])[:max_results]:
                abstract = (p.get("abstract") or "")[:250]
                yr = p.get("year", "")
                cites = p.get("citationCount", 0)
                results.append({"title": f"[{yr}] {p.get('title','')}", "snippet": f"(引用{cites}) {abstract}",
                                "url": p.get("url", ""), "source": "semantic_scholar"})
            return results
        except Exception:
            return []

    def run_all(self):
        if self._has_valid_cache():
            self.results = self._cache["flat"]
            valid = sum(1 for r in self.results if r.get("source") != "error")
            print(f"  ⚡ 使用搜索缓存 ({valid}条有效)")
            return self._cache["results"]

        all_results = {}
        total = len(self.SEARCH_TOPICS)
        for i, t in enumerate(self.SEARCH_TOPICS, 1):
            q, cat = t["query"], t["category"]
            print(f"  🔍 [{i}/{total}] {q[:55]}...")
            res = self._search_ddg_html(q)
            valid = [r for r in res if r.get("source") != "error" and (r.get("snippet") or r.get("url"))]
            all_results.setdefault(cat, []).extend(valid)
            self.results.extend(valid)
            time.sleep(0.5)

        gh_queries = ["multi-agent orchestration framework", "LLM hierarchy management",
                      "AI agent supervisor worker pattern"]
        print(f"\n  🐙 GitHub搜索 ({len(gh_queries)}个)...")
        for q in gh_queries:
            res = self._search_github(q)
            valid = [r for r in res if r.get("source") != "error"]
            all_results.setdefault("github_project", []).extend(valid)
            self.results.extend(valid)
            time.sleep(0.5)

        print(f"  📚 学术搜索 ({len(self.ACADEMIC_TOPICS)}个)...")
        for t in self.ACADEMIC_TOPICS:
            res = self._search_semantic_scholar(t["query"])
            valid = [r for r in res if r.get("source") != "error" and r.get("snippet")]
            all_results.setdefault(t["category"], []).extend(valid)
            self.results.extend(valid)
            time.sleep(0.3)

        self._save_cache(all_results)
        valid_total = sum(1 for r in self.results if r.get("source") != "error")
        print(f"\n  📊 搜索完成: {valid_total}条有效, {len(all_results)}个分类")
        return all_results

    def build_context(self, max_chars=10000):
        ctx = "## 搜索结果摘要\n\n"
        for r in self.results[:50]:
            snippet = r.get("snippet", "")
            if not snippet or r.get("source") == "error":
                continue
            line = f"- [{r['source']}] {r['title'][:60]}: {snippet[:150]}\n"
            if len(ctx) + len(line) > max_chars:
                break
            ctx += line
        return ctx
