#!/usr/bin/env python3
"""
COP 共享态势层 — 双环态势网络体系 v2.0 核心基础设施
=====================================================
四大组件:
  1. TaskBoard    — 任务态势板 (实时状态)
  2. KnowledgeStore — 三层知识存储 (原始→结构化→精炼) + 重要度遗忘
  3. SkillRegistry — 技能注册表 (对接 PCM Skill Router)
  4. ConflictDetector — 冲突检测广播
  + EventBus     — 发布-订阅事件总线
  + PathCache    — v2路径缓存 (OODA加速)

非Agent, 纯基础设施。所有节点可读写。
"""

import json
import time
import hashlib
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any

# ==================== 配置 ====================
COP_DIR = Path(__file__).parent
COP_DB_PATH = COP_DIR / "cop_awareness.db"

# ==================== EventBus ====================
class EventBus:
    """发布-订阅事件总线 — 所有COP组件通过此通信"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._history: List[Dict] = []

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type: str, data: Any = None):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            self._history.append(event)
            if len(self._history) > 1000:
                self._history = self._history[-500:]
            listeners = list(self._subscribers.get(event_type, []))
        for cb in listeners:
            try:
                cb(event)
            except Exception as e:
                print(f"  ⚠️ EventBus callback error [{event_type}]: {e}")

    def recent(self, n: int = 20) -> List[Dict]:
        with self._lock:
            return list(self._history[-n:])


# ==================== TaskBoard ====================
class TaskBoard:
    """任务态势板 — 实时展示谁在做什么"""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    def __init__(self, db: "COPDB", bus: EventBus):
        self.db = db
        self.bus = bus

    def create_task(self, intent: str, source: str = "L0") -> str:
        task_id = f"task_{int(time.time()*1000)}_{hashlib.md5(intent.encode()).hexdigest()[:6]}"
        self.db.exec(
            "INSERT INTO cop_tasks (task_id, intent, source, status, created_at) VALUES (?,?,?,?,?)",
            (task_id, intent, source, self.STATUS_PENDING, datetime.now().isoformat())
        )
        self.bus.publish("task.created", {"task_id": task_id, "intent": intent})
        return task_id

    def update_status(self, task_id: str, status: str, result: str = "", assigned_to: str = ""):
        updates = ["status=?", "updated_at=?"]
        params = [status, datetime.now().isoformat()]
        if result:
            updates.append("result=?")
            params.append(result[:50000])
        if assigned_to:
            updates.append("assigned_to=?")
            params.append(assigned_to)
        params.append(task_id)
        self.db.exec(f"UPDATE cop_tasks SET {','.join(updates)} WHERE task_id=?", tuple(params))
        self.bus.publish(f"task.{status}", {"task_id": task_id})

    def get_pending(self) -> List[Dict]:
        rows = self.db.query("SELECT * FROM cop_tasks WHERE status=? ORDER BY created_at", (self.STATUS_PENDING,))
        return [dict(r) for r in rows]

    def get_task(self, task_id: str) -> Optional[Dict]:
        row = self.db.query_one("SELECT * FROM cop_tasks WHERE task_id=?", (task_id,))
        return dict(row) if row else None

    def get_all_active(self) -> List[Dict]:
        rows = self.db.query(
            "SELECT * FROM cop_tasks WHERE status IN (?,?) ORDER BY created_at DESC LIMIT 50",
            (self.STATUS_PENDING, self.STATUS_RUNNING)
        )
        return [dict(r) for r in rows]

    def summary(self) -> Dict:
        counts = {}
        for st in [self.STATUS_PENDING, self.STATUS_RUNNING, self.STATUS_DONE, self.STATUS_FAILED]:
            row = self.db.query_one("SELECT COUNT(*) as c FROM cop_tasks WHERE status=?", (st,))
            counts[st] = row["c"] if row else 0
        return counts


# ==================== KnowledgeStore ====================
class KnowledgeStore:
    """三层知识存储 + 重要度加权遗忘
    Layer 1: 原始日志 (TTL 7天)
    Layer 2: 结构化节点 (TTL 30天)
    Layer 3: 精炼知识 (永久, 需人工或v7确认)
    """

    LAYER_RAW = 1
    LAYER_STRUCTURED = 2
    LAYER_REFINED = 3

    def __init__(self, db: "COPDB", bus: EventBus):
        self.db = db
        self.bus = bus

    def add(self, content: str, layer: int = 1, source: str = "",
            node_type: str = "general", importance: float = 0.5) -> int:
        ttl_days = {1: 7, 2: 30, 3: 99999}.get(layer, 30)
        expires = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        nid = self.db.exec_lastid(
            """INSERT INTO cop_knowledge
               (content, layer, source, node_type, importance, ref_count, expires_at, created_at)
               VALUES (?,?,?,?,?,0,?,?)""",
            (content[:50000], layer, source, node_type, importance, expires, datetime.now().isoformat())
        )
        self.bus.publish("knowledge.added", {"id": nid, "layer": layer, "type": node_type})
        return nid

    def promote(self, node_id: int, to_layer: int):
        """提升节点层级 (如 raw→structured, structured→refined)"""
        ttl_days = {2: 30, 3: 99999}.get(to_layer, 30)
        expires = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        self.db.exec("UPDATE cop_knowledge SET layer=?, expires_at=? WHERE id=?",
                     (to_layer, expires, node_id))

    def reference(self, node_id: int):
        """被引用时增加 ref_count, 提升重要度"""
        self.db.exec(
            "UPDATE cop_knowledge SET ref_count=ref_count+1, importance=MIN(1.0, importance+0.05) WHERE id=?",
            (node_id,)
        )

    def search(self, keyword: str, layer: Optional[int] = None, limit: int = 10) -> List[Dict]:
        sql = "SELECT * FROM cop_knowledge WHERE content LIKE ? AND expires_at > ?"
        params: list = [f"%{keyword}%", datetime.now().isoformat()]
        if layer:
            sql += " AND layer=?"
            params.append(layer)
        sql += " ORDER BY importance DESC, ref_count DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.db.query(sql, tuple(params))]

    def get_recent(self, n: int = 20, layer: Optional[int] = None) -> List[Dict]:
        sql = "SELECT * FROM cop_knowledge WHERE expires_at > ?"
        params: list = [datetime.now().isoformat()]
        if layer:
            sql += " AND layer=?"
            params.append(layer)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(n)
        return [dict(r) for r in self.db.query(sql, tuple(params))]

    def run_forgetting(self) -> int:
        """执行遗忘: 删除过期+低重要度节点"""
        now = datetime.now().isoformat()
        # 删除已过期的非精炼节点
        cur = self.db.exec("DELETE FROM cop_knowledge WHERE expires_at < ? AND layer < 3", (now,))
        expired = cur.rowcount if hasattr(cur, 'rowcount') else 0
        # 加速衰减: 低重要度(<0.3)且无引用的非精炼节点, TTL减半
        self.db.exec(
            """UPDATE cop_knowledge SET expires_at=datetime(expires_at, '-3 days')
               WHERE importance < 0.3 AND ref_count = 0 AND layer < 3"""
        )
        if expired > 0:
            self.bus.publish("knowledge.forgotten", {"expired": expired})
        return expired

    def stats(self) -> Dict:
        result = {}
        for layer in [1, 2, 3]:
            row = self.db.query_one(
                "SELECT COUNT(*) as c, AVG(importance) as avg_imp FROM cop_knowledge WHERE layer=? AND expires_at>?",
                (layer, datetime.now().isoformat())
            )
            result[f"layer_{layer}"] = {"count": row["c"] if row else 0,
                                         "avg_importance": round(row["avg_imp"] or 0, 3)}
        return result


# ==================== ConflictDetector ====================
class ConflictDetector:
    """冲突检测 — 广播预警, 不仲裁"""

    def __init__(self, db: "COPDB", bus: EventBus):
        self.db = db
        self.bus = bus

    def check_task_conflicts(self) -> List[Dict]:
        """检测正在执行的任务中是否有依赖冲突"""
        active = self.db.query(
            "SELECT * FROM cop_tasks WHERE status=? ORDER BY created_at",
            (TaskBoard.STATUS_RUNNING,)
        )
        conflicts = []
        active_list = [dict(r) for r in active]
        # 简易冲突检测: 两个running任务的intent包含相同关键词
        for i, t1 in enumerate(active_list):
            for t2 in active_list[i+1:]:
                overlap = set(t1.get("intent", "").split()) & set(t2.get("intent", "").split())
                if len(overlap) >= 2:
                    conflict = {
                        "task_a": t1["task_id"], "task_b": t2["task_id"],
                        "overlap_keywords": list(overlap),
                        "detected_at": datetime.now().isoformat()
                    }
                    conflicts.append(conflict)
                    self.bus.publish("conflict.detected", conflict)
        return conflicts


# ==================== PathCache ====================
class PathCache:
    """v2路径缓存 — 加速OODA Orient阶段
    缓存 task_pattern → execution_path 映射
    命中率目标: 第5轮60%, 第10轮80%+
    """

    def __init__(self, db: "COPDB", bus: EventBus):
        self.db = db
        self.bus = bus
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _pattern_hash(intent: str) -> str:
        """提取意图模式哈希 (去掉具体名词, 保留动词+结构)"""
        # 简化: 按长度分桶 + 关键词排序哈希
        words = sorted(set(intent.replace("，", " ").replace(",", " ").split()))
        pattern = " ".join(w for w in words if len(w) >= 2)[:200]
        return hashlib.md5(pattern.encode()).hexdigest()[:12]

    def get(self, intent: str) -> Optional[List[str]]:
        """查缓存, 返回 [skill_name, ...] 或 None"""
        ph = self._pattern_hash(intent)
        row = self.db.query_one(
            "SELECT path_json, hit_count FROM cop_path_cache WHERE pattern_hash=?", (ph,)
        )
        if row:
            self._hits += 1
            self.db.exec("UPDATE cop_path_cache SET hit_count=hit_count+1, last_used=? WHERE pattern_hash=?",
                         (datetime.now().isoformat(), ph))
            self.bus.publish("cache.hit", {"pattern": ph})
            return json.loads(row["path_json"])
        self._misses += 1
        return None

    def put(self, intent: str, path: List[str]):
        ph = self._pattern_hash(intent)
        self.db.exec(
            """INSERT OR REPLACE INTO cop_path_cache
               (pattern_hash, intent_sample, path_json, hit_count, last_used, created_at)
               VALUES (?,?,?,0,?,?)""",
            (ph, intent[:200], json.dumps(path), datetime.now().isoformat(), datetime.now().isoformat())
        )

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict:
        return {"hits": self._hits, "misses": self._misses,
                "hit_rate": f"{self.hit_rate:.1%}",
                "cached_paths": self.db.query_one("SELECT COUNT(*) as c FROM cop_path_cache")["c"]}


# ==================== COPDB ====================
class COPDB:
    """COP数据库封装"""

    def __init__(self, db_path=COP_DB_PATH):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS cop_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE,
                intent TEXT,
                source TEXT DEFAULT 'L0',
                status TEXT DEFAULT 'pending',
                assigned_to TEXT DEFAULT '',
                result TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS cop_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                layer INTEGER DEFAULT 1,
                source TEXT DEFAULT '',
                node_type TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                ref_count INTEGER DEFAULT 0,
                expires_at TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS cop_path_cache (
                pattern_hash TEXT PRIMARY KEY,
                intent_sample TEXT,
                path_json TEXT,
                hit_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS cop_ooda_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                phase TEXT,
                input_summary TEXT,
                output_summary TEXT,
                duration_ms INTEGER DEFAULT 0,
                skill_used TEXT DEFAULT '',
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON cop_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_knowledge_layer ON cop_knowledge(layer);
            CREATE INDEX IF NOT EXISTS idx_knowledge_importance ON cop_knowledge(importance);
            CREATE INDEX IF NOT EXISTS idx_ooda_cycle ON cop_ooda_log(cycle_id);
        """)
        self.conn.commit()

    def exec(self, sql, params=()):
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def exec_lastid(self, sql, params=()) -> int:
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.lastrowid

    def query(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def close(self):
        self.conn.close()


# ==================== COP 主类 ====================
class COP:
    """共享态势感知层 — 统一入口

    用法:
        cop = COP()
        task_id = cop.tasks.create_task("实现Fibonacci函数")
        cop.knowledge.add("Fibonacci递归+备忘录", layer=2, source="v1")
        cached = cop.cache.get("实现算法函数")
        cop.conflicts.check_task_conflicts()
    """

    def __init__(self, db_path=COP_DB_PATH):
        self.db = COPDB(db_path)
        self.bus = EventBus()
        self.tasks = TaskBoard(self.db, self.bus)
        self.knowledge = KnowledgeStore(self.db, self.bus)
        self.conflicts = ConflictDetector(self.db, self.bus)
        self.cache = PathCache(self.db, self.bus)

    def log_ooda(self, cycle_id: str, phase: str, input_summary: str,
                 output_summary: str, duration_ms: int = 0, skill_used: str = ""):
        self.db.exec(
            """INSERT INTO cop_ooda_log
               (cycle_id, phase, input_summary, output_summary, duration_ms, skill_used, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (cycle_id, phase, input_summary[:2000], output_summary[:2000],
             duration_ms, skill_used, datetime.now().isoformat())
        )

    def get_ooda_history(self, limit: int = 20) -> List[Dict]:
        rows = self.db.query("SELECT * FROM cop_ooda_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def full_status(self) -> Dict:
        return {
            "tasks": self.tasks.summary(),
            "knowledge": self.knowledge.stats(),
            "cache": self.cache.stats(),
            "recent_events": len(self.bus.recent(50)),
        }

    def close(self):
        self.db.close()


# ==================== 测试 ====================
if __name__ == "__main__":
    import tempfile, os
    test_db = Path(tempfile.mktemp(suffix=".db"))
    print("=" * 60)
    print("COP 共享态势层 — 自检")
    print("=" * 60)

    cop = COP(db_path=test_db)

    # 1. TaskBoard
    tid = cop.tasks.create_task("实现一个Fibonacci计算器", source="L0")
    cop.tasks.update_status(tid, "running", assigned_to="v1_coding")
    assert cop.tasks.get_task(tid)["status"] == "running"
    print(f"✅ TaskBoard: 创建+更新任务 {tid}")

    # 2. KnowledgeStore
    nid = cop.knowledge.add("Fibonacci可用递归+备忘录实现", layer=2, source="v1", importance=0.7)
    cop.knowledge.reference(nid)
    results = cop.knowledge.search("Fibonacci")
    assert len(results) >= 1
    print(f"✅ KnowledgeStore: 添加+搜索知识 (layer2, id={nid})")

    # 3. PathCache
    cop.cache.put("实现算法函数", ["v1_coding", "v4_validate"])
    cached = cop.cache.get("实现算法函数")
    assert cached == ["v1_coding", "v4_validate"]
    print(f"✅ PathCache: 缓存命中 {cached}, hit_rate={cop.cache.hit_rate:.0%}")

    # 4. ConflictDetector
    tid2 = cop.tasks.create_task("实现一个排序算法", source="L0")
    cop.tasks.update_status(tid, "running")
    cop.tasks.update_status(tid2, "running")
    conflicts = cop.conflicts.check_task_conflicts()
    print(f"✅ ConflictDetector: 检测冲突 {len(conflicts)}个")

    # 5. OODA Log
    cop.log_ooda("cycle_001", "observe", "读取任务", "发现Fibonacci任务", 50, "")
    history = cop.get_ooda_history()
    assert len(history) >= 1
    print(f"✅ OODA Log: 记录{len(history)}条")

    # 6. EventBus
    events = cop.bus.recent(10)
    print(f"✅ EventBus: {len(events)}条事件")

    # 7. Full status
    status = cop.full_status()
    print(f"✅ 全局态势: {json.dumps(status, ensure_ascii=False)}")

    # 8. Forgetting
    forgotten = cop.knowledge.run_forgetting()
    print(f"✅ 遗忘引擎: 清理{forgotten}条过期知识")

    cop.close()
    os.unlink(str(test_db))
    print("\n🏁 COP 全部自检通过!")
