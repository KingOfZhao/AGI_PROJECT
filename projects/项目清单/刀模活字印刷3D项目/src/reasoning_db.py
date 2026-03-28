"""
刀模活字印刷3D项目 — 推演数据库
"""
import json
import os
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "推演数据")
DB_PATH = os.path.join(DATA_DIR, "reasoning.db")
os.makedirs(DATA_DIR, exist_ok=True)


class ReasoningDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS reasoning_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_num INTEGER NOT NULL,
            phase TEXT NOT NULL,
            direction TEXT,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            findings TEXT DEFAULT '[]',
            score REAL DEFAULT 0,
            sigma REAL DEFAULT 1.0,
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            confidence REAL DEFAULT 0.5,
            truth_level INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            round_num INTEGER,
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS module_designs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_type TEXT NOT NULL,
            variant TEXT,
            params_json TEXT NOT NULL,
            dims_json TEXT NOT NULL,
            connector_json TEXT NOT NULL,
            print_json TEXT,
            verified INTEGER DEFAULT 0,
            round_num INTEGER,
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS decomposition_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            total_entities INTEGER DEFAULT 0,
            total_modules INTEGER DEFAULT 0,
            modules_json TEXT NOT NULL,
            assembly_json TEXT,
            print_time_min REAL,
            cost_estimate REAL,
            round_num INTEGER,
            ts TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS convergence_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_num INTEGER,
            metric TEXT,
            value REAL,
            sigma REAL,
            converged INTEGER DEFAULT 0,
            ts TEXT DEFAULT (datetime('now'))
        );
        """)
        self.conn.commit()

    def save_round(self, rn, phase, direction, topic, content, findings=None, score=0, sigma=1.0):
        self.conn.execute(
            "INSERT INTO reasoning_rounds (round_num,phase,direction,topic,content,findings,score,sigma) VALUES (?,?,?,?,?,?,?,?)",
            (rn, phase, direction, topic, content, json.dumps(findings or [], ensure_ascii=False), score, sigma))
        self.conn.commit()

    def save_node(self, ntype, title, content, source="", conf=0.5, truth=0, rn=0):
        self.conn.execute(
            "INSERT INTO knowledge_nodes (node_type,title,content,source,confidence,truth_level,round_num) VALUES (?,?,?,?,?,?,?)",
            (ntype, title, content, source, conf, truth, rn))
        self.conn.commit()

    def save_module(self, mtype, variant, params, dims, connector, print_s=None, rn=0):
        self.conn.execute(
            "INSERT INTO module_designs (module_type,variant,params_json,dims_json,connector_json,print_json,round_num) VALUES (?,?,?,?,?,?,?)",
            (mtype, variant, json.dumps(params), json.dumps(dims), json.dumps(connector), json.dumps(print_s or {}), rn))
        self.conn.commit()

    def save_decomp(self, src, entities, modules, mlist, assembly=None, ptime=0, cost=0, rn=0):
        self.conn.execute(
            "INSERT INTO decomposition_results (source_file,total_entities,total_modules,modules_json,assembly_json,print_time_min,cost_estimate,round_num) VALUES (?,?,?,?,?,?,?,?)",
            (src, entities, modules, json.dumps(mlist, ensure_ascii=False), json.dumps(assembly or {}), ptime, cost, rn))
        self.conn.commit()

    def log_conv(self, rn, metric, value, sigma, converged=False):
        self.conn.execute(
            "INSERT INTO convergence_log (round_num,metric,value,sigma,converged) VALUES (?,?,?,?,?)",
            (rn, metric, value, sigma, int(converged)))
        self.conn.commit()

    def get_round_count(self):
        r = self.conn.execute("SELECT MAX(round_num) FROM reasoning_rounds").fetchone()
        return r[0] if r[0] else 0

    def get_nodes(self, ntype=None):
        if ntype:
            return [dict(r) for r in self.conn.execute("SELECT * FROM knowledge_nodes WHERE node_type=? ORDER BY confidence DESC", (ntype,))]
        return [dict(r) for r in self.conn.execute("SELECT * FROM knowledge_nodes ORDER BY confidence DESC")]

    def get_modules(self, mtype=None):
        if mtype:
            return [dict(r) for r in self.conn.execute("SELECT * FROM module_designs WHERE module_type=?", (mtype,))]
        return [dict(r) for r in self.conn.execute("SELECT * FROM module_designs")]

    def get_convergence(self, metric):
        return [dict(r) for r in self.conn.execute("SELECT * FROM convergence_log WHERE metric=? ORDER BY round_num", (metric,))]

    def close(self):
        self.conn.close()
