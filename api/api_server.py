#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 Cognitive Lattice — Web API 服务
提供 REST API 供 HTML 前端调用

启动方式：
    ./venv/bin/python api_server.py

API 端点：
    GET  /api/stats          — 认知网络统计
    GET  /api/nodes          — 节点列表 (支持 ?domain=&status=&search=&page=&limit=)
    GET  /api/domains        — 领域列表
    GET  /api/relations      — 关联列表
    GET  /api/growth_log     — 成长日志
    POST /api/chat           — 对话（四向碰撞处理）
    GET  /api/chat_history   — 对话历史
    POST /api/ingest         — 录入人类真实节点
    POST /api/search         — 语义搜索
    POST /api/self_growth    — 触发一次自成长循环
    POST /api/imprint        — 执行认知烙印
    POST /api/practice_list  — 生成实践清单
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)



import os
import sys
import json
import uuid
import sqlite3
import threading
import time
import queue
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import re as _re
import math as _math
import requests as _requests

# 导入核心模块
import agi_v13_cognitive_lattice as agi
import cognitive_core
import action_engine
import cluster_manager
import tool_controller
import orchestrator as orch_module
from scripts.pcm_skill_router import route_skills, route_skills_formatted

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=os.path.join(PROJECT_ROOT, 'web'), static_url_path='')
CORS(app)

# 全局实例
lattice = None
growth_engine = None
task_orchestrator = None
chat_history_lock = threading.Lock()

# SSE 推送队列池
_sse_queues = []
_sse_lock = threading.Lock()

# 对话停止机制
_chat_abort = threading.Event()
_console_log = []  # 控制台日志缓冲
_console_lock = threading.Lock()
MAX_CONSOLE_LINES = 500

# API-3: 简易TTL缓存 — stats/domains等高频低变端点
_api_cache = {}
_api_cache_lock = threading.Lock()

def cached_response(key, ttl_seconds, fetch_fn):
    """TTL缓存: 在ttl_seconds内返回缓存结果, 过期则重新获取"""
    with _api_cache_lock:
        entry = _api_cache.get(key)
        if entry and (time.time() - entry['ts']) < ttl_seconds:
            return entry['data']
    data = fetch_fn()
    with _api_cache_lock:
        _api_cache[key] = {'data': data, 'ts': time.time()}
    return data

# INT-1: DiePre reasoning.db 桥接
DIEPRE_DB_PATH = Path.home() / "Desktop" / "DiePre AI" / "reasoning.db"

def _get_diepre_conn():
    """获取DiePre reasoning.db连接 (只读)"""
    if not DIEPRE_DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DIEPRE_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def console_log(msg):
    """Append to console log buffer for frontend"""
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with _console_lock:
        _console_log.append(entry)
        if len(_console_log) > MAX_CONSOLE_LINES:
            _console_log[:] = _console_log[-MAX_CONSOLE_LINES:]
    print(f"  {entry}")

def broadcast_step(step_type, detail, status="running"):
    """广播执行步骤到所有 SSE 客户端"""
    entry = action_engine._emit_step(step_type, detail, status)
    with _sse_lock:
        for q in _sse_queues:
            try:
                q.put_nowait(entry)
            except Exception:
                pass
    return entry

# 对话历史存储（追加到 DB）
def _ensure_chat_table():
    """确保对话历史表存在"""
    c = lattice.conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        metadata TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
    """)
    lattice.conn.commit()


def _save_chat(session_id, role, content, metadata=None):
    with chat_history_lock:
        lattice.conn.execute(
            "INSERT INTO chat_history (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(metadata or {}, ensure_ascii=False))
        )
        lattice.conn.commit()


# ==================== 静态文件 ====================
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# ==================== 后端切换 API ====================
@app.route('/api/backend')
def api_backend():
    """Get current backend info and available backends"""
    current = agi.Config.ACTIVE_BACKEND
    backends = {}
    for k, v in agi.BACKENDS.items():
        backends[k] = {"name": v["name"], "model": v["model"], "api_type": v.get("api_type", "openai")}
    return jsonify({"current": current, "backends": backends})


@app.route('/api/switch_backend', methods=['POST'])
def api_switch_backend():
    """Switch LLM backend"""
    data = request.json
    backend = data.get('backend', '')
    if not backend:
        return jsonify({"error": "need backend param"}), 400
    ok = agi.Config.switch_backend(backend)
    if ok:
        b = agi.BACKENDS[backend]
        console_log(f"\u540e\u7aef\u5207\u6362: {b['name']} ({b['model']})")
        return jsonify({"success": True, "backend": backend, "name": b['name'], "model": b['model']})
    return jsonify({"error": f"unknown backend: {backend}"}), 400


@app.route('/api/chat/stop', methods=['POST'])
def api_chat_stop():
    """Stop current chat processing"""
    _chat_abort.set()
    console_log("\u7528\u6237\u505c\u6b62\u4e86\u5f53\u524d\u5bf9\u8bdd")
    return jsonify({"success": True})


@app.route('/api/console')
def api_console():
    """Get console log lines"""
    since = int(request.args.get('since', 0))
    with _console_lock:
        lines = _console_log[since:]
    return jsonify({"lines": lines, "total": len(_console_log)})


# ==================== API 端点 ====================

@app.route('/api/stats')
def api_stats():
    # API-3: 30秒TTL缓存
    stats = cached_response('stats', 30, lambda: lattice.stats())
    return jsonify(stats)


@app.route('/api/domains')
def api_domains():
    # DB-3: 单条GROUP BY聚合查询替代N+1查询
    c = lattice.conn.cursor()
    c.execute("""
        SELECT domain, COUNT(*) as count
        FROM cognitive_nodes
        GROUP BY domain
        ORDER BY count DESC
    """)
    result = [{"domain": r['domain'], "count": r['count']} for r in c.fetchall()]
    return jsonify(result)


@app.route('/api/nodes')
def api_nodes():
    domain = request.args.get('domain', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    offset = (page - 1) * limit

    c = lattice.conn.cursor()
    conditions = []
    params = []

    if domain:
        conditions.append("domain = ?")
        params.append(domain)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if search:
        # API-4: 优先使用FTS5全文搜索, 回退到LIKE
        try:
            lattice.conn.cursor().execute("SELECT 1 FROM nodes_fts LIMIT 1")
            conditions.append("id IN (SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?)")
            params.append(f'"{search}"')
        except Exception:
            conditions.append("content LIKE ?")
            params.append(f"%{search}%")

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # 总数
    c.execute(f"SELECT COUNT(*) as cnt FROM cognitive_nodes{where}", params)
    total = c.fetchone()['cnt']

    # 分页数据
    c.execute(f"""
        SELECT id, content, domain, status, depth, access_count,
               created_at, last_verified_at, verified_source
        FROM cognitive_nodes{where}
        ORDER BY created_at DESC LIMIT ? OFFSET ?
    """, params + [limit, offset])
    nodes = [dict(r) for r in c.fetchall()]

    return jsonify({
        "nodes": nodes,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    })


@app.route('/api/relations')
def api_relations():
    limit = int(request.args.get('limit', 100))
    c = lattice.conn.cursor()
    c.execute("""
        SELECT r.id, r.node1_id, r.node2_id, r.relation_type, r.confidence,
               r.description, r.created_at,
               n1.content as node1_content, n1.domain as node1_domain,
               n2.content as node2_content, n2.domain as node2_domain
        FROM node_relations r
        JOIN cognitive_nodes n1 ON r.node1_id = n1.id
        JOIN cognitive_nodes n2 ON r.node2_id = n2.id
        ORDER BY r.created_at DESC LIMIT ?
    """, (limit,))
    return jsonify([dict(r) for r in c.fetchall()])


@app.route('/api/graph')
def api_graph():
    """返回图谱数据：节点+边，用于力导向图可视化
    API-2: 按连接度降序排列，优先返回核心节点"""
    limit = int(request.args.get('limit', 300))
    domain = request.args.get('domain', '')
    node_id = request.args.get('node_id', '')
    c = lattice.conn.cursor()

    if node_id:
        nid = int(node_id)
        c.execute("""
            SELECT DISTINCT n.id, n.content, n.domain, n.status
            FROM cognitive_nodes n
            WHERE n.id = ?
            UNION
            SELECT DISTINCT n.id, n.content, n.domain, n.status
            FROM cognitive_nodes n
            JOIN node_relations r ON (n.id = r.node1_id OR n.id = r.node2_id)
            WHERE r.node1_id = ? OR r.node2_id = ?
            LIMIT ?
        """, (nid, nid, nid, limit))
    elif domain:
        c.execute("""
            SELECT id, content, domain, status FROM cognitive_nodes
            WHERE domain = ? LIMIT ?
        """, (domain, limit))
    else:
        # API-2: 按连接度降序，优先返回核心高连接节点
        c.execute("""
            SELECT n.id, n.content, n.domain, n.status
            FROM cognitive_nodes n
            JOIN (
                SELECT nid, COUNT(*) as deg FROM (
                    SELECT node1_id as nid FROM node_relations
                    UNION ALL
                    SELECT node2_id as nid FROM node_relations
                ) GROUP BY nid ORDER BY deg DESC LIMIT ?
            ) ranked ON n.id = ranked.nid
        """, (limit,))

    nodes_raw = c.fetchall()
    node_ids = {r['id'] for r in nodes_raw}
    nodes = [{"id": r['id'], "label": r['content'][:40], "content": r['content'],
              "domain": r['domain'], "status": r['status']} for r in nodes_raw]

    if node_ids:
        placeholders = ','.join('?' * len(node_ids))
        c.execute(f"""
            SELECT node1_id as source, node2_id as target, relation_type as type,
                   confidence, description
            FROM node_relations
            WHERE node1_id IN ({placeholders}) AND node2_id IN ({placeholders})
        """, list(node_ids) + list(node_ids))
        edges = [dict(r) for r in c.fetchall()]
    else:
        edges = []

    return jsonify({"nodes": nodes, "edges": edges})


@app.route('/api/growth_log')
def api_growth_log():
    limit = int(request.args.get('limit', 20))
    history = lattice.get_growth_history(limit)
    return jsonify(history)


# ==================== INT-1: DiePre reasoning.db 桥接 API ====================

@app.route('/api/diepre/stats')
def api_diepre_stats():
    """DiePre推演数据库统计"""
    conn = _get_diepre_conn()
    if not conn:
        return jsonify({"error": "DiePre reasoning.db not found", "available": False})
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM nodes")
        total_nodes = c.fetchone()['cnt']
        c.execute("SELECT reality_level, COUNT(*) as cnt FROM nodes GROUP BY reality_level")
        reality_dist = {r['reality_level']: r['cnt'] for r in c.fetchall()}
        c.execute("SELECT node_type, COUNT(*) as cnt FROM nodes GROUP BY node_type ORDER BY cnt DESC LIMIT 20")
        type_dist = {r['node_type']: r['cnt'] for r in c.fetchall()}
        c.execute("SELECT COUNT(*) as cnt FROM reasoning_logs")
        total_logs = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM collision_results")
        total_collisions = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM node_relations")
        total_relations = c.fetchone()['cnt']
        conn.close()
        return jsonify({
            "available": True,
            "total_nodes": total_nodes,
            "reality_distribution": reality_dist,
            "type_distribution": type_dist,
            "total_logs": total_logs,
            "total_collisions": total_collisions,
            "total_relations": total_relations
        })
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "available": False})


@app.route('/api/diepre/nodes')
def api_diepre_nodes():
    """DiePre推演节点列表"""
    conn = _get_diepre_conn()
    if not conn:
        return jsonify({"error": "DiePre reasoning.db not found", "nodes": []})
    try:
        reality = request.args.get('reality', '')
        node_type = request.args.get('type', '')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        c = conn.cursor()
        conditions, params = [], []
        if reality:
            conditions.append("reality_level = ?")
            params.append(reality)
        if node_type:
            conditions.append("node_type = ?")
            params.append(node_type)
        if search:
            conditions.append("content LIKE ?")
            params.append(f"%{search}%")
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        c.execute(f"SELECT COUNT(*) as cnt FROM nodes{where}", params)
        total = c.fetchone()['cnt']
        c.execute(f"""
            SELECT id, content, node_type, reality_level, confidence, source, created_at
            FROM nodes{where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, params + [limit, offset])
        nodes = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify({"nodes": nodes, "total": total, "page": page, "pages": (total + limit - 1) // limit})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "nodes": []})


@app.route('/api/diepre/collisions')
def api_diepre_collisions():
    """DiePre碰撞结果"""
    conn = _get_diepre_conn()
    if not conn:
        return jsonify({"error": "DiePre reasoning.db not found", "collisions": []})
    try:
        limit = int(request.args.get('limit', 20))
        c = conn.cursor()
        c.execute("""
            SELECT id, round_number, collision_type, result_summary, 
                   consensus_count, disputed_count, new_count, failed_count, created_at
            FROM collision_results
            ORDER BY round_number DESC LIMIT ?
        """, (limit,))
        collisions = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify({"collisions": collisions})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "collisions": []})


@app.route('/api/diepre/import', methods=['POST'])
def api_diepre_import():
    """INT-2: 将DiePre real节点批量导入主知识库"""
    conn = _get_diepre_conn()
    if not conn:
        return jsonify({"error": "DiePre reasoning.db not found"})
    try:
        domain = request.json.get('domain', 'diepre') if request.json else 'diepre'
        c = conn.cursor()
        c.execute("SELECT content, node_type, confidence FROM nodes WHERE reality_level = 'real'")
        real_nodes = c.fetchall()
        conn.close()
        imported, skipped = 0, 0
        for rn in real_nodes:
            node_id = lattice.add_node(
                content=rn['content'],
                domain=f"{domain}_{rn['node_type']}" if rn['node_type'] else domain,
                status='known',
                source='diepre_import',
                silent=True
            )
            if node_id:
                imported += 1
            else:
                skipped += 1
        console_log(f"DiePre导入完成: {imported}个节点导入, {skipped}个跳过")
        return jsonify({"success": True, "imported": imported, "skipped": skipped, "total_real": len(real_nodes)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ==================== 盒型模板 API ====================

BOX_DB_PATH = os.path.join(PROJECT_ROOT, "api", "box_templates.db")
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "web", "templates")

def _get_box_conn():
    if not os.path.exists(BOX_DB_PATH):
        return None
    conn = sqlite3.connect(BOX_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/box/templates')
def api_box_templates():
    """盒型模板列表"""
    conn = _get_box_conn()
    if not conn:
        return jsonify({"error": "box_templates.db not found", "templates": []})
    try:
        box_type = request.args.get('type', '')
        fefco = request.args.get('fefco', '')
        search = request.args.get('search', '')
        c = conn.cursor()
        conditions, params = [], []
        if box_type:
            conditions.append("box_type = ?")
            params.append(box_type)
        if fefco:
            conditions.append("fefco_code = ?")
            params.append(fefco)
        if search:
            conditions.append("(filename LIKE ? OR box_type_cn LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        c.execute(f"""
            SELECT id, filename, fefco_code, box_type, box_type_cn,
                   dimension_l, dimension_w, dimension_h, flute_type,
                   entity_count, features_json, source, created_at
            FROM box_templates{where}
            ORDER BY created_at DESC
        """, params)
        templates = [dict(r) for r in c.fetchall()]
        for t in templates:
            if t.get('features_json'):
                try:
                    t['features'] = json.loads(t['features_json'])
                except Exception:
                    t['features'] = []
            del t['features_json']
        conn.close()
        return jsonify({"templates": templates})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "templates": []})


@app.route('/api/box/catalog')
def api_box_catalog():
    """盒型目录 (FEFCO标准)"""
    conn = _get_box_conn()
    if not conn:
        return jsonify({"error": "box_templates.db not found", "catalog": []})
    try:
        c = conn.cursor()
        c.execute("""
            SELECT id, fefco_code, type_key, type_cn, type_en, description, category,
                   template_count, common_dimensions_json, structure_features_json,
                   fold_sequence_json
            FROM box_type_catalog ORDER BY fefco_code
        """)
        catalog = []
        for r in c.fetchall():
            item = dict(r)
            for key in ['common_dimensions_json', 'structure_features_json', 'fold_sequence_json']:
                if item.get(key):
                    try:
                        item[key.replace('_json', '')] = json.loads(item[key])
                    except Exception:
                        pass
                if key in item:
                    del item[key]
            catalog.append(item)
        conn.close()
        return jsonify({"catalog": catalog})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "catalog": []})


@app.route('/api/box/modules')
def api_box_modules():
    """可拖拽模块库"""
    conn = _get_box_conn()
    if not conn:
        return jsonify({"error": "box_templates.db not found", "modules": []})
    try:
        c = conn.cursor()
        category = request.args.get('category', '')
        if category:
            c.execute("SELECT * FROM box_modules WHERE category = ? ORDER BY module_name", (category,))
        else:
            c.execute("SELECT * FROM box_modules ORDER BY category, module_name")
        modules = []
        for r in c.fetchall():
            item = dict(r)
            if item.get('parameters_json'):
                try:
                    item['parameters'] = json.loads(item['parameters_json'])
                except Exception:
                    item['parameters'] = {}
                del item['parameters_json']
            modules.append(item)
        conn.close()
        return jsonify({"modules": modules})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e), "modules": []})


@app.route('/api/box/template/<int:template_id>/dxf')
def api_box_template_dxf(template_id):
    """获取模板DXF文件"""
    conn = _get_box_conn()
    if not conn:
        return jsonify({"error": "not found"}), 404
    try:
        c = conn.cursor()
        c.execute("SELECT filepath, filename FROM box_templates WHERE id = ?", (template_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "template not found"}), 404
        filepath = row['filepath']
        if os.path.exists(filepath):
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            return send_from_directory(directory, filename, mimetype='application/dxf')
        return jsonify({"error": "file not found"}), 404
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/box/upload', methods=['POST'])
def api_box_upload():
    """上传DXF/DWG文件并自动识别盒型"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"})
    f = request.files['file']
    if not f.filename:
        return jsonify({"error": "Empty filename"})

    fname = f.filename
    ext = os.path.splitext(fname)[1].lower()
    if ext not in ('.dxf', '.dwg'):
        return jsonify({"error": f"Unsupported format: {ext}, only .dxf/.dwg"})

    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    save_path = os.path.join(TEMPLATE_DIR, fname)
    f.save(save_path)

    if ext == '.dwg':
        return jsonify({
            "success": True,
            "warning": "DWG文件已保存, 需转换为DXF后才能解析。请用AutoCAD另存为DXF格式。",
            "filepath": save_path,
            "needs_conversion": True
        })

    # 解析DXF并识别盒型
    try:
        import ezdxf
        from ezdxf import bbox as dxf_bbox
        from collections import Counter as Ctr

        doc = ezdxf.readfile(save_path)
        msp = doc.modelspace()
        entities = list(msp)
        type_counts = Ctr(e.dxftype() for e in entities)
        layers = [l.dxf.name for l in doc.layers]

        # 分析几何特征
        lines, arcs = [], []
        for e in entities:
            if e.dxftype() == "LINE":
                s, t = e.dxf.start, e.dxf.end
                angle = _math.degrees(_math.atan2(t[1]-s[1], t[0]-s[0])) % 180
                lines.append(angle)
            elif e.dxftype() == "ARC":
                arcs.append(e.dxf.radius)

        # 正交率
        ortho = sum(1 for a in lines if a < 5 or a > 175 or (85 < a < 95)) / max(len(lines), 1)

        # 盒型推断
        box_type = "general_carton"
        if ortho > 0.85 and not arcs:
            box_type = "standard_rsc" if len(entities) > 50 else "simple_tray"
        elif arcs and any(r < 10 for r in arcs):
            box_type = "lock_bottom_box"
        elif len(arcs) > 10:
            box_type = "die_cut_special"

        # 边界
        cache = dxf_bbox.Cache()
        box = dxf_bbox.extents(msp, cache=cache)
        width = round(box.extmax[0] - box.extmin[0], 1) if box.has_data else None
        height = round(box.extmax[1] - box.extmin[1], 1) if box.has_data else None

        type_names = {
            "standard_rsc": "标准开槽箱", "simple_tray": "简单托盘",
            "lock_bottom_box": "锁底盒", "die_cut_special": "异形模切",
            "general_carton": "通用纸箱"
        }

        # 存入DB
        conn = _get_box_conn()
        if conn:
            conn.execute("""
                INSERT OR REPLACE INTO box_templates (
                    filename, filepath, box_type, box_type_cn,
                    entity_count, line_count, arc_count,
                    total_width, total_height,
                    features_json, layers_json, source
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                fname, save_path, box_type, type_names.get(box_type, box_type),
                len(entities), type_counts.get("LINE", 0), type_counts.get("ARC", 0),
                width, height,
                json.dumps({"orthogonal_ratio": round(ortho, 3), "has_arcs": bool(arcs)}, ensure_ascii=False),
                json.dumps(layers, ensure_ascii=False),
                "uploaded"
            ))
            conn.commit()
            conn.close()

        console_log(f"DXF上传解析: {fname} → {type_names.get(box_type, box_type)}")
        return jsonify({
            "success": True,
            "filename": fname,
            "box_type": box_type,
            "box_type_cn": type_names.get(box_type, box_type),
            "entity_count": len(entities),
            "width": width,
            "height": height,
            "layers": layers,
            "orthogonal_ratio": round(ortho, 3),
        })
    except Exception as e:
        return jsonify({"error": f"DXF parse error: {str(e)}"})


@app.route('/api/box/generate', methods=['POST'])
def api_box_generate():
    """根据参数生成盒型DXF"""
    data = request.json or {}
    box_type = data.get('type', 'RSC')
    L = float(data.get('L', 300))
    W = float(data.get('W', 200))
    H = float(data.get('H', 200))
    name = data.get('name', f"{box_type}_{L:.0f}x{W:.0f}x{H:.0f}")

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
        from generate_box_templates import (
            fefco_0201_rsc, fefco_0421_lock_bottom,
            fefco_0711_telescope, fefco_0301_tube, display_stand,
            save_template, init_db
        )

        generators = {
            'RSC': lambda: fefco_0201_rsc(L, W, H),
            '0201': lambda: fefco_0201_rsc(L, W, H),
            'lock_bottom': lambda: fefco_0421_lock_bottom(L, W, H),
            '0421': lambda: fefco_0421_lock_bottom(L, W, H),
            'telescope': lambda: fefco_0711_telescope(L, W, H),
            '0711': lambda: fefco_0711_telescope(L, W, H),
            'tube': lambda: fefco_0301_tube(L, W, H),
            '0301': lambda: fefco_0301_tube(L, W, H),
            'display': lambda: display_stand(L, W, H, int(data.get('shelves', 3))),
        }

        gen_fn = generators.get(box_type)
        if not gen_fn:
            return jsonify({"error": f"Unknown box type: {box_type}. Options: {list(generators.keys())}"})

        doc, info = gen_fn()
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        filepath = os.path.join(TEMPLATE_DIR, f"{name}.dxf")
        doc.saveas(filepath)

        conn = _get_box_conn()
        if conn:
            save_template(conn, filepath, info, doc)
            conn.close()

        console_log(f"盒型生成: {name} ({info.get('type_cn', box_type)} {L}x{W}x{H})")
        return jsonify({
            "success": True,
            "filename": f"{name}.dxf",
            "filepath": filepath,
            "info": info,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    message = data.get('message', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4())[:8])
    mode = data.get('mode', 'code')  # code|ask|plan|nocollision|tool|heat|mobile|agi|cross
    enable_actions = data.get('enable_actions', True)
    if mode == 'ask':
        enable_actions = False
    elif mode == 'plan':
        enable_actions = 'plan'
    elif mode == 'nocollision':
        enable_actions = False
    elif mode == 'tool':
        enable_actions = False
    # 领域专属模式映射
    _domain_mode = None
    _DOMAIN_CONFIGS = {
        'heat': {
            'name': '热处理',
            'domains': ['热处理', '温度', '铁碳', '相变', '退火', '淬火', '回火', 'PID', '材料', '冶金', '扩散', '奥氏体', '马氏体'],
            'system': '你是热处理与材料科学专家。请在材料科学、热力学、相变理论、PID控温的概念框架内思考和回答。优先使用铁碳相图、扩散方程、TTT/CCT曲线等物理概念解释问题。如果问题涉及其他领域知识（如编程控制、机械加工），也要将答案锚定回热处理领域的实际应用。',
        },
        'mobile': {
            'name': '移动端',
            'domains': ['Flutter', 'Dart', 'Android', 'iOS', '蓝牙', 'BLE', '移动端', 'Widget', '状态管理', '路由', '动画', '跨平台'],
            'system': '你是移动端开发专家，精通Flutter/Dart生态。请在移动端开发的概念框架内思考：Widget树、状态管理(Riverpod/Bloc/Provider)、路由导航、平台通道、蓝牙BLE通信等。给出的代码示例应为Flutter/Dart。如果问题需要后端或算法知识，将答案锚定回移动端的实际集成场景。',
        },
        'agi': {
            'name': 'AGI/本地模型',
            'domains': ['AGI', 'LLM', '认知', '自成长', 'Ollama', '本地模型', 'embedding', '碰撞', 'Agent', 'MCP', '推理', '智谱'],
            'system': '你是AGI系统与本地模型能力专家。请在认知科学、知识图谱、LLM推理、Agent架构的概念框架内思考。重点关注：认知格四向碰撞、自成长引擎、embedding语义搜索、MCP工具协议、多模型协作。答案应聚焦于如何增强本地模型的认知能力和自主解决问题的能力。',
        },
        'cross': {
            'name': '跨域碰撞',
            'domains': [],  # 不限领域
            'system': '应无所住而生其心。你需要跨越领域边界来思考问题：\n1. 首先识别问题所属的核心概念域（如物理、材料、编程、认知科学等）\n2. 在该概念域内尝试解答\n3. 如果域内知识不足以完整解答，主动寻找其他概念域的类比、方法或工具来辅助\n4. 将跨域获得的洞察翻译回原始概念域，给出域内可理解的答案\n5. 明确标注哪些知识来自本域、哪些借鉴自其他域\n格式：先列出涉及的概念域，再分域分析，最后综合给出跨域碰撞后的答案。',
        },
    }
    if mode in _DOMAIN_CONFIGS:
        _domain_mode = _DOMAIN_CONFIGS[mode]
        if mode == 'cross':
            enable_actions = True  # 跨域模式允许执行
        else:
            enable_actions = True  # 领域模式也允许执行

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    _chat_abort.clear()  # 重置停止标志
    _save_chat(session_id, "user", message)
    _t0 = time.time()

    # ★★ OpenClaw 模式: 转发到 Bridge(9801)，走7步链+AGI上下文注入 ★★
    if agi.Config.ACTIVE_BACKEND == "openclaw":
        bridge_url = agi.BACKENDS["openclaw"]["base_url"]
        try:
            _bridge_resp = _requests.post(
                f"{bridge_url}/chat/completions",
                json={
                    "model": "agi-chain-v13",
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
                timeout=300,
            )
            _bridge_data = _bridge_resp.json()
            _reply = (_bridge_data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if not _reply:
                raise ValueError("bridge 返回空")
            _save_chat(session_id, "assistant", _reply)
            total_elapsed = time.time() - _t0
            return jsonify({
                "response": _reply,
                "session_id": session_id,
                "backend": "openclaw",
                "elapsed": round(total_elapsed, 2),
                "nodes_used": 0,
            })
        except Exception as _e:
            console_log(f"[OpenClaw] bridge 调用失败: {_e}，降级到本地编排器")

    # ★ Tool模式: LLM Controller + Real Python Runtime ★
    if mode == 'tool':
        console_log(f"🔧 Tool模式: {message[:80]}")
        broadcast_step("tool_start", f"🔧 Tool Controller启动: {message[:60]}...", "running")
        def _on_step(step_type, detail):
            broadcast_step(f"tool_{step_type}", str(detail)[:200], "running")
        try:
            tc_model = data.get('model', None)  # 允许前端指定模型
            result = tool_controller.solve(
                question=message,
                max_rounds=int(data.get('max_rounds', 15)),
                model=tc_model,
                on_step=_on_step,
            )
            answer = result.get('answer', '')
            broadcast_step("tool_done", f"🔧 完成: {result['rounds']}轮, {len(result['tool_calls'])}次工具调用, {result['duration']}s", "done")
            _save_chat(session_id, "assistant", answer)
            console_log(f"🔧 Tool完成: {result['rounds']}轮, {result['duration']}s")
            return jsonify({
                "response": answer,
                "session_id": session_id,
                "stats": lattice.stats(),
                "metadata": {
                    "mode": "tool",
                    "rounds": result['rounds'],
                    "tool_calls": result['tool_calls'],
                    "duration": result['duration'],
                    "runtime_stats": result.get('runtime_stats', {}),
                }
            })
        except Exception as e:
            console_log(f"🔧 Tool错误: {e}")
            broadcast_step("tool_error", str(e)[:200], "done")
            return jsonify({
                "response": f"Tool Controller错误: {e}",
                "session_id": session_id,
                "stats": lattice.stats(),
                "metadata": {"mode": "tool", "error": str(e)}
            }), 500
    def _step(stype, detail, status="running"):
        elapsed = time.time() - _t0
        broadcast_step(stype, f"{detail}  ({elapsed:.0f}s)", status)
    _step("chat_start", f"收到问题: {message[:60]}...", "running")
    console_log(f"\u5bf9\u8bdd\u5f00\u59cb: {message[:80]}")

    # 确定数据标注策略：本地后端产生的节点默认为 known（可本地验证）
    is_cloud_backend = agi.Config.ACTIVE_BACKEND not in ('ollama', 'ollama_7b')
    default_node_status = "hypothesis" if is_cloud_backend else "known"

    response_parts = []
    metadata = {"nodes_added": [], "collisions": 0, "actions": []}

    # 1. 查找相关已知节点
    if _chat_abort.is_set():
        return jsonify({"response": "✘ 已停止", "session_id": session_id, "stats": lattice.stats(), "metadata": metadata})
    _step("search", "搜索相关已知节点...", "running")
    console_log("搜索相关节点...")
    related = lattice.find_similar_nodes(message, threshold=0.4, limit=5)
    if related:
        _step("search", f"找到 {len(related)} 个相关节点", "done")
        response_parts.append(f"**找到 {len(related)} 个相关已知节点：**")
        for r in related:
            response_parts.append(f"- [{r['domain']}] {r['content'][:80]} (相似度:{r['similarity']:.3f})")
    else:
        _step("search", "未找到相关节点", "done")

    # 1b. 已验证方案复用 — 优先检索 proven 解决方案节点
    proven_solutions = []
    if related:
        proven_solutions = [r for r in related if r.get('status') == 'proven' and r.get('similarity', 0) > 0.7]
        if proven_solutions:
            response_parts.append(f"\n**♻ 找到 {len(proven_solutions)} 个已验证方案可复用：**")
            for ps in proven_solutions:
                response_parts.append(f"- ✅ [{ps['domain']}] {ps['content'][:100]}")

    # ★★★ Orchestrator 智能路由 ★★★
    orch_result = None
    if task_orchestrator and not _chat_abort.is_set():
        _step("orchestrator", "🧠 Orchestrator 分析问题...", "running")
        try:
            orch_result = task_orchestrator.process(
                message, context_nodes=related or [], enable_tracking=True)
            orch_model = orch_result.get('model_used', 'unknown')
            orch_complexity = orch_result.get('complexity', 0)
            metadata['orchestrator'] = {
                'model_used': orch_model,
                'complexity': orch_complexity,
                'task_type': orch_result.get('task_type', ''),
                'routing_reason': orch_result.get('routing', {}).get('reason', ''),
                'grounding_ratio': orch_result.get('grounding_ratio', 0),
                'problem_id': orch_result.get('problem_id'),
                'duration_ms': orch_result.get('duration_ms', 0),
            }
            metadata['thinking_steps'] = orch_result.get('thinking_steps', [])
            _step("orchestrator",
                   f"🧠 路由: {orch_model} (复杂度:{orch_complexity:.1f})",
                   "done")

            # 如果orchestrator已经通过GLM-5/GLM-4.7等获得了结果，直接使用
            if orch_result.get('text') and orch_model != 'fast_path':
                orch_text = orch_result['text']
                g_ratio = orch_result.get('grounding_ratio', 0)
                g_tag = f" (锚定率:{g_ratio:.0%})" if g_ratio > 0 else ""
                response_parts.append(
                    f"\n**🧠 {orch_model} 协同回答{g_tag}：**\n{orch_text}")

                # 执行动作（如果有动作意图）
                if enable_actions and action_engine._detect_action_intent(message):
                    _step("action_plan", "🔧 检测到执行意图...", "running")
                    try:
                        fp_actions = action_engine.plan_actions(
                            message, (related or [])[:10], lattice)
                        if fp_actions:
                            _step("action_plan",
                                  f"规划了 {len(fp_actions)} 个动作", "done")
                            if enable_actions != 'plan':
                                fp_results = action_engine.execute_action_plan(
                                    fp_actions, lattice=lattice)
                                new_nodes = action_engine.action_to_nodes(
                                    fp_results, lattice)
                                metadata["actions"] = [
                                    {"action": r["action"],
                                     "success": r["result"].get("success", False),
                                     "reasoning": r.get("reasoning", "")}
                                    for r in fp_results
                                ]
                                response_parts.append("\n**🔧 执行动作：**")
                                for r in fp_results:
                                    icon = "✓" if r["result"].get("success") else "✗"
                                    response_parts.append(
                                        f"- [{icon}] {r['action']}: {r['reasoning']}")
                    except Exception as e:
                        _step("action_plan", f"动作规划失败: {e}", "error")

                # 保存并返回
                stats = lattice.stats()
                response_parts.append(
                    f"\n---\n📊 认知网络：{stats['total_nodes']} 节点 / "
                    f"{stats['total_relations']} 关联 / "
                    f"{stats['total_domains']} 领域")
                full_response = "\n".join(response_parts)
                _save_chat(session_id, "assistant", full_response, metadata)
                total_elapsed = time.time() - _t0
                _step("chat_done",
                      f"Orchestrator完成，总耗时 {total_elapsed:.0f}秒", "done")
                return jsonify({
                    "response": full_response,
                    "session_id": session_id,
                    "stats": stats,
                    "metadata": metadata
                })
        except Exception as e:
            _step("orchestrator", f"Orchestrator异常: {e}，回退标准管线", "error")
            console_log(f"Orchestrator异常: {e}")
            orch_result = None

    # ★ 快速路径：proven节点充分命中时跳过重型管线 ★
    if len(proven_solutions) >= 2 and not _chat_abort.is_set():
        _step("fast_path", f"⚡ {len(proven_solutions)} 个proven节点命中，启用快速路径", "running")
        console_log(f"⚡ 快速路径：{len(proven_solutions)} proven命中，跳过拆解/碰撞")

        # 沿关系网络扩展更多相关proven节点
        related_via_rel = []
        try:
            conn = lattice.conn
            c = conn.cursor()
            proven_ids = [p['id'] for p in proven_solutions]
            for pid in proven_ids[:5]:
                c.execute("""
                    SELECT cn.content, cn.domain, cn.status, nr.relation_type
                    FROM node_relations nr
                    JOIN cognitive_nodes cn ON (cn.id = nr.node2_id OR cn.id = nr.node1_id)
                    WHERE (nr.node1_id = ? OR nr.node2_id = ?)
                    AND cn.id != ?
                    AND cn.status = 'proven'
                    AND nr.relation_type IN ('depends_on','extends','complements','implements','alternative','evolves_to')
                    LIMIT 5
                """, (pid, pid, pid))
                for row in c.fetchall():
                    related_via_rel.append({
                        "content": row[0], "domain": row[1],
                        "status": row[2], "relation": row[3]
                    })
        except Exception as e:
            console_log(f"关系扩展异常: {e}")

        if related_via_rel:
            _step("fast_path", f"⚡ 关系网络扩展 {len(related_via_rel)} 个关联节点", "running")
            response_parts.append(f"\n**🔗 关系网络扩展 {len(related_via_rel)} 个关联能力节点**")

        # 用proven节点直接生成结果（1次LLM调用）
        _step("fast_path", "⚡ 基于proven知识直接生成方案...", "running")
        fast_messages = cognitive_core.make_proven_fast_prompt(message, proven_solutions, related_via_rel)
        fast_result = agi.llm_call(fast_messages)
        fast_text = fast_result.get('raw', str(fast_result)) if isinstance(fast_result, dict) else str(fast_result)

        if fast_text and len(fast_text) > 30:
            response_parts.append(f"\n**⚡ 快速方案（基于 {len(proven_solutions)} 个proven节点）：**\n{fast_text}")
            _step("fast_path", "⚡ 快速路径完成", "done")

            # ★ 关键修复：fast_path也要检测动作意图并执行 ★
            if enable_actions and action_engine._detect_action_intent(message):
                _step("action_plan", "🔧 检测到执行意图，启动动作规划...", "running")
                try:
                    fp_actions = action_engine.plan_actions(message, related[:10], lattice)
                    if fp_actions:
                        _step("action_plan", f"规划了 {len(fp_actions)} 个动作", "done")
                        if enable_actions == 'plan':
                            response_parts.append("\n**📋 动作计划（未执行）：**")
                            for i, act in enumerate(fp_actions):
                                response_parts.append(f"- **{i+1}. {act.get('action','?')}**: {act.get('reasoning','')}")
                        else:
                            fp_results = action_engine.execute_action_plan(fp_actions, lattice=lattice)
                            new_nodes = action_engine.action_to_nodes(fp_results, lattice)
                            metadata["actions"] = [
                                {"action": r["action"], "success": r["result"].get("success", False),
                                 "reasoning": r.get("reasoning", "")}
                                for r in fp_results
                            ]
                            response_parts.append("\n**🔧 执行动作：**")
                            for r in fp_results:
                                icon = "✓" if r["result"].get("success") else "✗"
                                response_parts.append(f"- [{icon}] {r['action']}: {r['reasoning']}")
                                if r["result"].get("path"):
                                    response_parts.append(f"  文件: {r['result']['path']}")
                                if r["result"].get("full_path"):
                                    response_parts.append(f"  完整路径: {r['result']['full_path']}")
                                if r["result"].get("stdout"):
                                    response_parts.append(f"  输出: {r['result']['stdout'][:200]}")
                    else:
                        _step("action_plan", "动作规划未产出有效计划", "done")
                except Exception as e:
                    _step("action_plan", f"动作规划失败: {e}", "error")
                    console_log(f"fast_path动作规划失败: {e}")

            # 保存对话
            full_response = "\n".join(response_parts)
            _save_chat(session_id, "assistant", full_response, metadata)
            console_log(f"⚡ 快速路径完成，用时 {time.time()-_t0:.1f}s")
            return jsonify({
                "response": full_response,
                "session_id": session_id,
                "stats": lattice.stats(),
                "metadata": {**metadata, "fast_path": True,
                             "proven_used": len(proven_solutions),
                             "relations_expanded": len(related_via_rel)}
            })
        else:
            _step("fast_path", "快速路径结果不足，回退完整管线", "done")
            console_log("快速路径结果不足，回退完整管线")

    # ★ 无碰撞模式：最短路径，仅搜索proven+直接LLM回答 ★
    if mode == 'nocollision' and not _chat_abort.is_set():
        _step("nocollision", "⚡ 无碰撞模式：最短路径解答", "running")
        console_log("⚡ 无碰撞模式")
        # 收集所有proven上下文
        proven_ctx = [r for r in (related or []) if r.get('status') == 'proven']
        ctx_text = "\n".join([f"- [{p['domain']}] {p['content']}" for p in proven_ctx[:10]]) if proven_ctx else "无直接命中的proven节点"
        nc_messages = [
            {"role": "system", "content": f"你是一个高效的技术助手。基于以下已验证知识直接回答问题。如果已有知识不足以回答，明确说明'我无法解决此问题'并列出具体缺失的能力。\n\n已验证知识:\n{ctx_text}"},
            {"role": "user", "content": message}
        ]
        nc_result = agi.llm_call(nc_messages)
        nc_text = nc_result.get('raw', str(nc_result)) if isinstance(nc_result, dict) else str(nc_result)

        if nc_text:
            response_parts.append(f"\n**⚡ 无碰撞直达回答：**\n{nc_text}")
        _step("nocollision", "⚡ 无碰撞模式完成", "done")

        full_response = "\n".join(response_parts)
        _save_chat(session_id, "assistant", full_response)
        console_log(f"⚡ 无碰撞完成，用时 {time.time()-_t0:.1f}s")
        return jsonify({
            "response": full_response,
            "session_id": session_id,
            "stats": lattice.stats(),
            "metadata": {**metadata, "mode": "nocollision", "proven_used": len(proven_ctx)}
        })

    # ★ 领域专属模式：补充域内节点搜索 + 注入领域system prompt ★
    if _domain_mode and not _chat_abort.is_set():
        dm_name = _domain_mode['name']
        _step("domain_focus", f"🎯 {dm_name}模式: 搜索领域知识...", "running")
        console_log(f"🎯 领域模式: {dm_name}")
        # 搜索领域专属proven节点
        domain_nodes = []
        if _domain_mode['domains']:
            try:
                conn = lattice.conn
                c = conn.cursor()
                domain_likes = " OR ".join("domain LIKE ?" for _ in _domain_mode['domains'])
                params = [f"%{d}%" for d in _domain_mode['domains']]
                c.execute(f"""
                    SELECT id, content, domain, status FROM cognitive_nodes
                    WHERE status = 'proven' AND ({domain_likes})
                    ORDER BY access_count DESC LIMIT 15
                """, params)
                domain_nodes = [{"id": r[0], "content": r[1], "domain": r[2], "status": r[3]} for r in c.fetchall()]
            except Exception as e:
                console_log(f"领域节点搜索异常: {e}")
        if domain_nodes:
            response_parts.append(f"\n**🎯 {dm_name}领域知识({len(domain_nodes)}条proven)：**")
            for dn in domain_nodes[:5]:
                response_parts.append(f"- ✅ [{dn['domain']}] {dn['content'][:80]}")
            if len(domain_nodes) > 5:
                response_parts.append(f"- ...及另外 {len(domain_nodes)-5} 条")
        # 跨域碰撞模式：多领域搜索
        if mode == 'cross':
            _step("domain_focus", "🌐 跨域碰撞: 搜索多领域交叉知识...", "running")
            # 从不同领域各取几个proven节点
            try:
                c = lattice.conn.cursor()
                c.execute("""
                    SELECT DISTINCT domain FROM cognitive_nodes
                    WHERE status='proven' GROUP BY domain HAVING count(*)>2
                    ORDER BY count(*) DESC LIMIT 10
                """)
                top_domains = [r[0] for r in c.fetchall()]
                cross_nodes = []
                for td in top_domains[:6]:
                    c.execute("""
                        SELECT content, domain FROM cognitive_nodes
                        WHERE status='proven' AND domain=? ORDER BY RANDOM() LIMIT 2
                    """, (td,))
                    cross_nodes.extend([{"content": r[0], "domain": r[1]} for r in c.fetchall()])
                if cross_nodes:
                    response_parts.append(f"\n**🌐 跨域碰撞池({len(cross_nodes)}条，覆盖{len(top_domains)}领域)：**")
                    for cn in cross_nodes[:8]:
                        response_parts.append(f"- [{cn['domain']}] {cn['content'][:60]}")
                    # 注入跨域上下文到related
                    related = (related or []) + cross_nodes
            except Exception as e:
                console_log(f"跨域搜索异常: {e}")
        _step("domain_focus", f"🎯 {dm_name}模式知识准备完成", "done")

    # 2. 自上而下拆解
    if _chat_abort.is_set():
        return jsonify({"response": "\n".join(response_parts) + "\n\n✘ 已停止", "session_id": session_id, "stats": lattice.stats(), "metadata": metadata})
    _step("top_down", "↓ 自上而下拆解中...", "running")
    console_log("自上而下拆解...")
    response_parts.append("\n**↓ 自上而下拆解：**")
    top_result = agi.DualDirectionDecomposer.top_down(message, related, lattice=lattice)
    top_items = agi.extract_items(top_result)
    for item in top_items:
        content = item.get('content', '') if isinstance(item, dict) else str(item)
        can_v = item.get('can_verify', False) if isinstance(item, dict) else False
        domain = item.get('domain', 'general') if isinstance(item, dict) else 'general'
        if content:
            status = "known" if can_v else "hypothesis"
            nid = lattice.add_node(content, domain, status, source="top_down", silent=True)
            tag = "✅ 可验证" if can_v else "❓ 待拆解"
            response_parts.append(f"- [{tag}] [{domain}] {content}")
            if nid:
                metadata["nodes_added"].append({"id": nid, "content": content[:50]})
    _step("top_down", f"拆解出 {len(top_items)} 个节点", "done")

    # 3. 自下而上
    if _chat_abort.is_set():
        return jsonify({"response": "\n".join(response_parts) + "\n\n✘ 已停止", "session_id": session_id, "stats": lattice.stats(), "metadata": metadata})
    _step("bottom_up", "↑ 自下而上生成新问题...", "running")
    console_log("自下而上生成新问题...")
    response_parts.append("\n**↑ 自下而上生成新问题：**")
    known_for_bu = related[:1] if related else lattice.get_random_known_nodes(1)  # 仅用 1 个节点，加速响应
    all_domains = lattice.get_all_domains()
    all_bottom_items = []
    for idx_bu, kn in enumerate(known_for_bu):
        if _chat_abort.is_set():
            break
        kn_content = kn.get('content', '')
        kn_domain = kn.get('domain', 'general')
        if kn_content:
            _step("bottom_up", f"↑ ({idx_bu+1}/{len(known_for_bu)}) 从 [{kn_domain}] 生成新问题...", "running")
            bottom_result = agi.DualDirectionDecomposer.bottom_up(kn_content, kn_domain, all_domains)
            items = agi.extract_items(bottom_result)
            all_bottom_items.extend(items)
            for item in items:
                bq = item.get('question', '') if isinstance(item, dict) else str(item)
                bd = item.get('potential_domain', 'general') if isinstance(item, dict) else 'general'
                cross = item.get('cross_domain', False) if isinstance(item, dict) else False
                if bq:
                    nid = lattice.add_node(bq, bd, "hypothesis", source="bottom_up", silent=True)
                    tag = "🔗 跨域" if cross else "📌"
                    response_parts.append(f"- [{tag}] [{bd}] {bq}")
    _step("bottom_up", f"生成 {len(all_bottom_items)} 个新问题", "done")

    # 4. 碰撞
    _step("collision", "⚡ 四向碰撞检测中...", "running")
    v_added = agi.CollisionEngine.vertical_collide(lattice, top_items, all_bottom_items)
    h_added = agi.CollisionEngine.cross_domain_collide(lattice)
    total_collisions = v_added + h_added
    metadata["collisions"] = total_collisions
    if total_collisions > 0:
        response_parts.append(f"\n**⚡ 碰撞发现 {total_collisions} 个新关联** (上下:{v_added} 跨域:{h_added})")
    _step("collision", f"碰撞完成: {total_collisions} 个新关联", "done")

    # 5. 智能能力调用 + 动作执行（AGI 的双手+大脑）
    if _chat_abort.is_set():
        return jsonify({"response": "\n".join(response_parts) + "\n\n✘ 已停止", "session_id": session_id, "stats": lattice.stats(), "metadata": metadata})
    if enable_actions:
        _step("action_plan", "🧠 分析问题，匹配能力...", "running")
        try:
            # 将拆解结果注入动作规划上下文，让规划更精准
            enriched_context = list(related or [])
            for item in (top_items or []):
                if isinstance(item, dict) and item.get('content'):
                    enriched_context.append({
                        'domain': item.get('domain', 'decomposed'),
                        'content': f"[拆解] {item['content']}",
                        'status': 'known' if item.get('can_verify') else 'hypothesis'
                    })
            actions = action_engine.plan_actions(message, enriched_context[:15], lattice)
            if actions:
                _step("action_plan", f"规划了 {len(actions)} 个动作", "done")
                if enable_actions == 'plan':
                    # Plan 模式：仅展示计划，不执行
                    response_parts.append("\n**📋 动作计划（未执行，确认后可切换 Code 模式执行）：**")
                    metadata["plan"] = []
                    for i, act in enumerate(actions):
                        a_name = act.get("action", "?")
                        a_reason = act.get("reasoning", "")
                        a_params = act.get("params", {})
                        response_parts.append(f"- **{i+1}. {a_name}**: {a_reason}")
                        if a_params:
                            for k, v in a_params.items():
                                val = str(v)[:100]
                                response_parts.append(f"  `{k}`: {val}")
                        metadata["plan"].append({"action": a_name, "reasoning": a_reason, "params": a_params})
                    _step("action_plan", f"📋 Plan 模式: 展示 {len(actions)} 个动作（未执行）", "done")
                else:
                    # Code 模式：正常执行
                    action_results = action_engine.execute_action_plan(actions, lattice=lattice)
                    new_nodes = action_engine.action_to_nodes(action_results, lattice)
                    metadata["actions"] = [
                        {"action": r["action"], "success": r["result"].get("success", False),
                         "reasoning": r.get("reasoning", "")}
                        for r in action_results
                    ]
                    # 构建动作报告
                    response_parts.append("\n**🔧 执行动作：**")
                    failed_actions = []
                    for r in action_results:
                        icon = "✓" if r["result"].get("success") else "✗"
                        response_parts.append(f"- [{icon}] {r['action']}: {r['reasoning']}")
                        if r["result"].get("stdout"):
                            response_parts.append(f"  输出: {r['result']['stdout'][:150]}")
                        if r["result"].get("path"):
                            response_parts.append(f"  文件: {r['result']['path']}")
                        if not r["result"].get("success"):
                            failed_actions.append(r)

                    # 5b. 能力缺口检测 + 自我强化
                    if failed_actions and not _chat_abort.is_set():
                        _step("gap_detect", "🔍 检测能力缺口...", "running")
                        gap_desc = "; ".join(f"{f['action']}: {f['result'].get('error','?')[:80]}" for f in failed_actions[:3])
                        # 记录能力缺口为假设节点
                        gap_content = f"能力缺口: 执行'{message[:40]}'时 {gap_desc}"
                        gap_nid = lattice.add_node(gap_content, "能力缺口", "hypothesis",
                                                   source="gap_detection", silent=True)
                        if gap_nid:
                            metadata["nodes_added"].append({"id": gap_nid, "content": gap_content[:50]})
                        response_parts.append(f"\n**🔍 发现能力缺口：** {gap_desc[:120]}")
                        # 尝试根据相关真实节点锻造新能力
                        proven_nodes = [n for n in related if n.get('status') == 'proven']
                        if proven_nodes:
                            _step("self_strengthen", "💪 基于真实节点强化能力...", "running")
                            try:
                                forge_actions = action_engine.plan_actions(
                                    f"我需要解决'{message[:60]}'但缺乏能力。"
                                    f"已有真实知识: {'; '.join(n['content'][:50] for n in proven_nodes[:3])}。"
                                    f"缺口: {gap_desc[:100]}。"
                                    f"请用 forge_tool 或 build_skill 创建一个新能力来填补这个缺口。",
                                    proven_nodes, lattice
                                )
                                if forge_actions:
                                    forge_results = action_engine.execute_action_plan(forge_actions, lattice=lattice)
                                    for fr in forge_results:
                                        if fr["result"].get("success"):
                                            response_parts.append(f"- [💪 自强] {fr['action']}: {fr['reasoning']}")
                                            # 记录自强化为真实节点
                                            strengthen_content = f"自我强化: 通过{fr['action']}填补能力缺口 — {fr['reasoning']}"
                                            s_nid = lattice.add_node(strengthen_content, "自强化", "proven",
                                                                     source="self_strengthen", silent=True)
                                            if s_nid and gap_nid:
                                                lattice.add_relation(s_nid, gap_nid, "resolves_gap", 0.9,
                                                                     "自强化解决能力缺口")
                                _step("self_strengthen", "💪 自我强化完成", "done")
                            except Exception as e:
                                _step("self_strengthen", f"自我强化失败: {e}", "error")
                        else:
                            response_parts.append("  ⚠ 缺少相关真实(proven)节点，无法自动强化。请先通过实践验证相关假设节点。")
                            _step("gap_detect", "需要更多真实节点支撑自强化", "done")
            else:
                _step("action_plan", "无需执行动作", "done")
        except Exception as e:
            _step("action_plan", f"动作规划失败: {e}", "error")

    # 5c. 从问题拆解过程中提取真实洞察节点
    if not _chat_abort.is_set() and top_items:
        insight_count = 0
        for item in top_items:
            content = item.get('content', '') if isinstance(item, dict) else str(item)
            can_v = item.get('can_verify', False) if isinstance(item, dict) else False
            domain = item.get('domain', 'general') if isinstance(item, dict) else 'general'
            if can_v and content:
                # 可验证的拆解项 → 尝试发现与已有 proven 节点的关系
                try:
                    similar_proven = [s for s in lattice.find_similar_nodes(content, threshold=0.5, limit=5)
                                      if s.get('status') == 'proven']
                    for sp in similar_proven:
                        # 找到该拆解项对应的节点ID
                        c = lattice.conn.cursor()
                        c.execute("SELECT id FROM cognitive_nodes WHERE content=? LIMIT 1", (content,))
                        row = c.fetchone()
                        if row:
                            lattice.add_relation(row['id'], sp['id'], "decompose_linked",
                                                 sp['similarity'],
                                                 f"拆解发现关联 ({sp['similarity']:.3f})")
                            insight_count += 1
                except Exception:
                    pass
        if insight_count > 0:
            response_parts.append(f"\n**🔗 拆解过程发现 {insight_count} 个与真实节点的新关联**")

    # 5d. 解决方案合成 — 从「分析」到「执行」的桥梁
    if not _chat_abort.is_set():
        _step("synthesis", "🎯 合成解决方案...", "running")
        console_log("合成解决方案...")
        try:
            collision_info = f"上下碰撞:{v_added}, 跨域碰撞:{h_added}" if total_collisions > 0 else None
            # 将已验证方案和动作结果也注入合成上下文
            synth_related = list(related or [])
            if proven_solutions:
                for ps in proven_solutions:
                    if ps not in synth_related:
                        synth_related.insert(0, ps)
            if metadata.get("actions"):
                action_summary = "; ".join(
                    f"{a['action']}({'✓' if a['success'] else '✗'}): {a.get('reasoning','')[:40]}"
                    for a in metadata["actions"][:5]
                )
                collision_info = (collision_info or "") + f"\n## 动作执行结果\n{action_summary}"
            synth_messages = cognitive_core.make_solution_synthesis_prompt(
                message, synth_related, top_items, collision_info
            )
            # 领域模式：注入领域system prompt到合成上下文
            if _domain_mode:
                domain_prompt = f"\n\n【领域专属指令 - {_domain_mode['name']}模式】\n{_domain_mode['system']}"
                if synth_messages and synth_messages[0].get('role') == 'system':
                    synth_messages[0]['content'] += domain_prompt
                else:
                    synth_messages.insert(0, {"role": "system", "content": domain_prompt})
            synth_result = agi.verified_llm_call(synth_messages, lattice=lattice, question=message)
            synth_text = synth_result.get('raw', str(synth_result)) if isinstance(synth_result, dict) else str(synth_result)
            verification = synth_result.get('_verification', {}) if isinstance(synth_result, dict) else {}

            if synth_text and len(synth_text) > 20:
                vtag = verification.get('tag', '')
                header = f"\n**🎯 解决方案{'  ' + vtag if vtag else ''}：**"
                response_parts.append(f"{header}\n{synth_text}")
                # 将解决方案核心存为 proven 节点（它是综合分析的产出）
                synth_summary = synth_text[:200].replace('\n', ' ')
                synth_nid = lattice.add_node(
                    f"解决方案[{message[:40]}]: {synth_summary}",
                    "解决方案", "hypothesis", source="solution_synthesis", silent=True
                )
                if synth_nid:
                    metadata["nodes_added"].append({"id": synth_nid, "content": f"解决方案: {message[:40]}"})
                    # 关联到相关节点
                    for r in (related or [])[:3]:
                        lattice.add_relation(synth_nid, r['id'], "solution_uses",
                                             r.get('similarity', 0.6),
                                             "解决方案引用已知节点")
                metadata["solution"] = synth_text[:500]
                _step("synthesis", "🎯 解决方案合成完成", "done")
            else:
                _step("synthesis", "合成结果为空", "done")
        except Exception as e:
            _step("synthesis", f"合成失败: {e}", "error")
            console_log(f"解决方案合成失败: {e}")

    # 6. 当前状态
    stats = lattice.stats()
    response_parts.append(f"\n---\n📊 认知网络：{stats['total_nodes']} 节点 / {stats['total_relations']} 关联 / {stats['total_domains']} 领域")
    console_log(f"对话完成: {len(response_parts)}段, {metadata['collisions']}碰撞")
    total_elapsed = time.time() - _t0
    _step("chat_done", f"处理完成，总耗时 {total_elapsed:.0f}秒", "done")

    full_response = "\n".join(response_parts)
    _save_chat(session_id, "assistant", full_response, metadata)

    if _domain_mode:
        metadata["domain_mode"] = mode
        metadata["domain_name"] = _domain_mode['name']

    return jsonify({
        "response": full_response,
        "session_id": session_id,
        "stats": stats,
        "metadata": metadata
    })


@app.route('/api/chat_history')
def api_chat_history():
    session_id = request.args.get('session_id', '')
    limit = int(request.args.get('limit', 100))
    c = lattice.conn.cursor()

    if session_id:
        c.execute("""
            SELECT * FROM chat_history WHERE session_id = ?
            ORDER BY created_at ASC LIMIT ?
        """, (session_id, limit))
    else:
        # 返回所有会话的最近消息
        c.execute("""
            SELECT * FROM chat_history
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))

    return jsonify([dict(r) for r in c.fetchall()])


@app.route('/api/sessions')
def api_sessions():
    """获取所有对话会话列表"""
    c = lattice.conn.cursor()
    c.execute("""
        SELECT session_id,
               MIN(created_at) as started_at,
               MAX(created_at) as last_at,
               COUNT(*) as message_count,
               (SELECT content FROM chat_history ch2
                WHERE ch2.session_id = ch.session_id AND ch2.role='user'
                ORDER BY ch2.created_at ASC LIMIT 1) as first_message
        FROM chat_history ch
        GROUP BY session_id
        ORDER BY last_at DESC
    """)
    return jsonify([dict(r) for r in c.fetchall()])


@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    data = request.json
    content = data.get('content', '').strip()
    domain = data.get('domain', 'general').strip()

    if not content:
        return jsonify({"error": "内容不能为空"}), 400

    nid = lattice.add_node(content, domain, "known", source="human_practice")
    if nid:
        similar = lattice.find_similar_nodes(content, threshold=agi.Config.CROSS_DOMAIN_THRESHOLD)
        linked = []
        for s in similar:
            if s['id'] != nid:
                lattice.add_relation(nid, s['id'], "human_linked", s['similarity'],
                                     f"人类节点自动关联 ({s['similarity']:.3f})")
                linked.append({"id": s['id'], "content": s['content'][:50], "similarity": s['similarity']})

        return jsonify({"id": nid, "content": content, "domain": domain, "linked": linked})
    return jsonify({"error": "节点已存在或录入失败"}), 400


@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    keyword = data.get('keyword', '').strip()
    threshold = data.get('threshold', 0.4)
    limit = data.get('limit', 20)

    if not keyword:
        return jsonify({"error": "关键词不能为空"}), 400

    results = lattice.find_similar_nodes(keyword, threshold=threshold, limit=limit)
    return jsonify(results)


@app.route('/api/self_growth', methods=['POST'])
def api_self_growth():
    try:
        broadcast_step("growth_start", "⟳ 自成长循环启动...", "running")
        console_log("自成长循环启动")
        stats_before = lattice.stats()
        result = growth_engine.run_one_cycle()
        stats_after = lattice.stats()
        new_nodes = stats_after['total_nodes'] - stats_before['total_nodes']
        new_rels = stats_after['total_relations'] - stats_before['total_relations']
        broadcast_step("growth_done", f"✓ 自成长完成: +{new_nodes}节点 +{new_rels}关联", "done")
        console_log(f"自成长完成: +{new_nodes}节点 +{new_rels}关联")
        return jsonify({"success": True, "stats": result})
    except Exception as e:
        broadcast_step("growth_error", f"✗ 自成长失败: {e}", "error")
        console_log(f"自成长失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/offline_growth', methods=['POST'])
def api_offline_growth():
    """F7: 触发一次离线成长循环（纯proven embedding碰撞，无需LLM）"""
    try:
        broadcast_step("offline_growth_start", "⟳ 离线成长循环启动(纯embedding碰撞)...", "running")
        console_log("离线成长循环启动")
        result = growth_engine.run_offline_cycle()
        total = result.get("total_new_relations", 0)
        broadcast_step("offline_growth_done",
                       f"✓ 离线成长完成: 跨域{result.get('cross_domain',0)} "
                       f"孤立连接{result.get('orphan_connected',0)} "
                       f"聚类{result.get('clustered',0)} 共+{total}关联", "done")
        console_log(f"离线成长完成: +{total}关联")
        return jsonify({"success": True, **result})
    except Exception as e:
        broadcast_step("offline_growth_error", f"✗ 离线成长失败: {e}", "error")
        console_log(f"离线成长失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/offline_growth/start', methods=['POST'])
def api_offline_growth_start():
    """F7: 启动后台离线成长"""
    data = request.json or {}
    interval = int(data.get('interval', 300))
    result = growth_engine.start_offline_growth(interval=interval)
    console_log(f"离线后台成长已启动，间隔{interval}s")
    return jsonify({"success": True, **result})


@app.route('/api/turbo_growth', methods=['POST'])
def api_turbo_growth():
    """全速推演：GLM-5单次成长循环（聚焦热处理/移动端/本地模型）"""
    try:
        data = request.json or {}
        batch_size = int(data.get('batch_size', 5))
        broadcast_step("turbo_growth", "🚀 GLM-5全速推演启动...", "running")
        console_log(f"全速推演循环启动(GLM-5, batch={batch_size})")
        from workspace.skills.zhipu_growth import run_turbo_growth_cycle
        result = run_turbo_growth_cycle(batch_size=batch_size, deepen=True)
        p = result.get("promoted", 0)
        f = result.get("falsified", 0)
        d = result.get("deepened", 0)
        broadcast_step("turbo_growth_done", f"🚀 全速推演完成: ✅{p} ❌{f} 🌱{d}", "done")
        console_log(f"全速推演完成: promoted={p} falsified={f} deepened={d}")
        return jsonify({"success": True, **result})
    except Exception as e:
        broadcast_step("turbo_growth_error", f"✗ 全速推演失败: {e}", "error")
        return jsonify({"error": str(e)}), 500


@app.route('/api/turbo_growth/start', methods=['POST'])
def api_turbo_growth_start():
    """启动GLM-5全速推演后台成长"""
    data = request.json or {}
    interval = int(data.get('interval', 30))
    batch_size = int(data.get('batch_size', 5))
    from workspace.skills.zhipu_growth import start_turbo_growth
    result = start_turbo_growth(interval=interval, batch_size=batch_size)
    console_log(f"全速推演后台启动: GLM-5, interval={interval}s, batch={batch_size}")
    broadcast_step("turbo_start", f"🚀 GLM-5全速推演后台已启动(间隔{interval}s)", "done")
    return jsonify({"success": True, **result})


@app.route('/api/turbo_growth/stop', methods=['POST'])
def api_turbo_growth_stop():
    """停止GLM-5全速推演"""
    from workspace.skills.zhipu_growth import stop_turbo_growth
    result = stop_turbo_growth()
    console_log("全速推演已停止")
    broadcast_step("turbo_stop", "🛑 全速推演已停止", "done")
    return jsonify({"success": True, **result})


@app.route('/api/turbo_growth/status', methods=['GET'])
def api_turbo_growth_status():
    """获取全速推演状态"""
    from workspace.skills.zhipu_growth import is_turbo_running, get_growth_status
    status = get_growth_status()
    status["turbo_running"] = is_turbo_running()
    return jsonify(status)


@app.route('/api/growth/problems/batch_auto', methods=['POST'])
def api_batch_auto_problems():
    """批量自动处理所有pending问题节点"""
    try:
        from workspace.skills.zhipu_growth import batch_auto_process_problems
        result = batch_auto_process_problems()
        console_log(f"批量处理问题: {result['total']}个(resolved={result['resolved']}, dismissed={result['dismissed']})")
        broadcast_step("batch_problems", f"✓ 批量处理{result['total']}个问题(✅{result['resolved']} ✗{result['dismissed']})", "done")
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orchestrator/stats', methods=['GET'])
def api_orchestrator_stats():
    """Orchestrator 统计数据"""
    if not task_orchestrator:
        return jsonify({"error": "Orchestrator未初始化"}), 500
    try:
        stats = task_orchestrator.get_orchestrator_stats()
        return jsonify({"success": True, **stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orchestrator/unsolvable', methods=['GET'])
def api_unsolvable_problems():
    """获取无法处理的问题列表"""
    if not task_orchestrator:
        return jsonify({"error": "Orchestrator未初始化"}), 500
    try:
        limit = int(request.args.get('limit', 50))
        problems = task_orchestrator.get_unsolvable_problems(limit)
        return jsonify({"success": True, "problems": problems,
                        "count": len(problems)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orchestrator/problem/<int:problem_id>', methods=['GET'])
def api_problem_history(problem_id):
    """获取问题拆解历史"""
    if not task_orchestrator:
        return jsonify({"error": "Orchestrator未初始化"}), 500
    try:
        history = task_orchestrator.get_problem_history(problem_id)
        if not history:
            return jsonify({"error": "问题不存在"}), 404
        return jsonify({"success": True, **history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orchestrator/retry/<int:problem_id>', methods=['POST'])
def api_retry_problem(problem_id):
    """重试无法处理的问题"""
    if not task_orchestrator:
        return jsonify({"error": "Orchestrator未初始化"}), 500
    try:
        result = task_orchestrator.retry_problem(problem_id)
        if result and result.get('error'):
            return jsonify(result), 400
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/capability_gaps', methods=['POST'])
def api_capability_gaps():
    """F6: 检测能力缺口"""
    data = request.json
    question = data.get('question', '').strip()
    if not question:
        return jsonify({"error": "question不能为空"}), 400
    from action_engine import detect_capability_gaps
    gaps = detect_capability_gaps(question)
    return jsonify({"success": True, "gaps": gaps, "count": len(gaps)})


@app.route('/api/imprint', methods=['POST'])
def api_imprint():
    try:
        with lattice._lock:
            lattice.conn.execute("DELETE FROM growth_log WHERE action = 'cognitive_imprint'")
            lattice.conn.commit()

        result = agi.llm_call(cognitive_core.COGNITIVE_IMPRINT_PROMPT)
        raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)

        stats = lattice.stats()
        lattice.log_growth("imprint", "cognitive_imprint",
                           "认知格哲学植入完成", stats['total_nodes'], stats['total_nodes'],
                           stats['total_relations'], stats['total_relations'])

        return jsonify({"success": True, "response": raw})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/practice_list', methods=['POST'])
def api_practice_list():
    data = request.json
    node_content = data.get('content', '').strip()
    if not node_content:
        return jsonify({"error": "内容不能为空"}), 400

    related = lattice.find_similar_nodes(node_content, threshold=0.5, limit=3)
    domain = related[0].get('domain', 'general') if related else 'general'
    messages = cognitive_core.make_practice_list_prompt(node_content, domain, related)
    result = agi.llm_call(messages)
    items = agi.extract_items(result)

    return jsonify({"steps": items, "related": related})


# ==================== 批量导入 ====================
IMPORT_TEMPLATE = """# 认知格节点批量导入模板
# ============================================
# 支持两种格式，任选其一：
#
# ── 格式A：管道分隔（推荐，最快理解）──
# 每行一个节点: 领域 | 节点内容
# 以 # 开头的行为注释，自动跳过
#
# 示例：
Python核心 | 装饰器本质是闭包的语法糖，@decorator等价于func=decorator(func)
Python核心 | GIL确保同一时刻只有一个线程执行Python字节码，CPU密集任务用multiprocessing
软件架构 | 单一职责原则(SRP)：每个类/函数只做一件事，修改原因应唯一
软件架构 | 依赖倒置原则：高层模块不依赖低层模块，都依赖抽象接口
数据库 | SQL注入防御：使用参数化查询(?占位符)，绝不拼接用户输入到SQL语句
网络编程 | TCP三次握手：SYN→SYN-ACK→ACK，四次挥手：FIN→ACK→FIN→ACK
#
# ── 格式B：JSON 数组 ──
# [
#   {"domain": "Python核心", "content": "装饰器本质是闭包的语法糖"},
#   {"domain": "软件架构", "content": "单一职责原则：每个类只做一件事"}
# ]
#
# ============================================
# 导入规则：
# 1. 所有导入节点初始状态为「假设」(hypothesis)
# 2. 导入后自动发现与已有节点的关联关系
# 3. 经过真实实践验证后，手动转为「已证」(proven) 成为真实节点
# 4. 真实节点间的关系经验证后成为真实关系
# 5. 真实节点+真实关系 = 真实能力
# ============================================
"""

@app.route('/api/import_template')
def api_import_template():
    """返回批量导入模板"""
    return jsonify({"template": IMPORT_TEMPLATE})


@app.route('/api/batch_import', methods=['POST'])
def api_batch_import():
    """批量导入节点（支持管道分隔文本或JSON数组）"""
    data = request.json
    raw = data.get('data', '').strip()
    if not raw:
        return jsonify({"error": "数据不能为空"}), 400

    broadcast_step("batch_import", "📥 开始批量导入节点...", "running")
    console_log("批量导入开始")

    nodes_to_import = []

    # 尝试 JSON 格式
    if raw.lstrip().startswith('['):
        try:
            items = json.loads(raw)
            for item in items:
                if isinstance(item, dict) and item.get('content'):
                    nodes_to_import.append({
                        "domain": item.get('domain', 'general').strip(),
                        "content": item['content'].strip()
                    })
        except json.JSONDecodeError as e:
            return jsonify({"error": f"JSON 解析失败: {e}"}), 400
    else:
        # 管道分隔格式
        for line in raw.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                parts = line.split('|', 1)
                domain = parts[0].strip()
                content = parts[1].strip()
                if content:
                    nodes_to_import.append({"domain": domain or 'general', "content": content})
            elif len(line) > 5:
                # 无领域标记的纯内容行
                nodes_to_import.append({"domain": "general", "content": line})

    if not nodes_to_import:
        return jsonify({"error": "未解析到有效节点"}), 400

    imported = 0
    linked_total = 0
    skipped = 0
    results = []

    for i, nd in enumerate(nodes_to_import):
        nid = lattice.add_node(nd['content'], nd['domain'], "hypothesis",
                               source="batch_import", silent=True)
        if nid:
            imported += 1
            link_count = 0
            try:
                similar = lattice.find_similar_nodes(nd['content'], threshold=0.5, limit=5)
                for s in similar:
                    if s['id'] != nid:
                        lattice.add_relation(nid, s['id'], "import_linked",
                                             s['similarity'],
                                             f"批量导入自动关联 ({s['similarity']:.3f})")
                        link_count += 1
                        linked_total += 1
            except Exception:
                pass
            results.append({"id": nid, "content": nd['content'][:60], "domain": nd['domain'],
                            "linked": link_count})
        else:
            skipped += 1

        if (i + 1) % 10 == 0:
            broadcast_step("batch_import", f"已处理 {i+1}/{len(nodes_to_import)}...", "running")

    broadcast_step("batch_import",
                   f"✓ 导入完成: {imported}个假设节点, {linked_total}个关联, {skipped}个跳过",
                   "done")
    console_log(f"批量导入完成: {imported}节点, {linked_total}关联, {skipped}跳过")

    return jsonify({
        "success": True,
        "imported": imported,
        "linked": linked_total,
        "skipped": skipped,
        "results": results[:50],  # 最多返回50条详情
        "stats": lattice.stats()
    })


# ==================== NL 低幻觉重写 ====================

# 规则层：模糊词替换表
_VAGUE_WORDS = [
    ("很好的", ""), ("非常好的", ""), ("比较好的", ""), ("最好的", "最优的"),
    ("大量的", "（请指定数量的）"), ("大量", "（请指定数量的）"),
    ("一些", "（请指定数量的）"), ("很多", "（请指定数量的）"),
    ("非常", ""), ("特别", ""), ("相当", ""), ("极其", ""),
    ("可能", "[不确定] 可能"), ("也许", "[不确定] 也许"),
    ("应该是", "[不确定] 推测为"), ("大概", "[不确定] 大概"),
    ("帮我想想", "请列举具体方案："), ("帮我看看", "请分析："),
    ("帮我弄一下", "请执行以下操作："), ("帮我搞", "请实现："),
    ("差不多", "（请指定具体值）"), ("还行", "（请给出具体评价标准）"),
    ("那个东西", "（请明确指代对象）"), ("这种感觉", "（请用具体描述替代）"),
]

# 暗示性动词 → 指令性动词
_VAGUE_VERBS = [
    ("想一下", "列举"), ("想想", "列举"), ("看看", "分析"), ("试试", "执行"),
    ("搞一个", "创建一个"), ("弄一个", "创建一个"), ("整一个", "创建一个"),
]


def _rule_based_rewrite(text):
    """规则层：基于模式匹配的确定性重写"""
    changes = []
    result = text

    # 1. 替换模糊词
    for vague, replacement in _VAGUE_WORDS:
        if vague in result:
            result = result.replace(vague, replacement)
            changes.append(f"模糊词'{vague}' → '{replacement or '(删除)'}'")

    # 2. 替换暗示性动词
    for vague_v, precise_v in _VAGUE_VERBS:
        if vague_v in result:
            result = result.replace(vague_v, precise_v)
            changes.append(f"暗示性表达'{vague_v}' → 指令'{precise_v}'")

    # 3. 检测复合意图（多个"和"/"并且"/"同时"连接的子句）
    multi_intent_markers = ["，并且", "，同时", "，还要", "，另外", "，而且"]
    intent_count = 1
    for marker in multi_intent_markers:
        intent_count += result.count(marker)
    if intent_count > 1:
        changes.append(f"检测到{intent_count}个复合意图，建议拆分为独立指令")

    # 4. 计算歧义度
    ambiguity = 0.0
    # 无具体数量词
    if not _re.search(r'\d+', result):
        ambiguity += 0.15
    # 含不确定标记
    if '[不确定]' in result:
        ambiguity += 0.2
    # 含待指定占位
    placeholders = result.count('请指定') + result.count('请明确')
    ambiguity += min(placeholders * 0.1, 0.3)
    # 句子过短（可能省略上下文）
    if len(text) < 15:
        ambiguity += 0.2
        changes.append("原文较短，可能省略了上下文，建议补全")
    # 含指代不明
    if _re.search(r'[这那它][个种些]', text):
        ambiguity += 0.15
        changes.append("含模糊指代（这个/那种等），建议明确指代对象")

    ambiguity = min(ambiguity, 1.0)

    # 5. 清理多余空格
    result = _re.sub(r'\s+', ' ', result).strip()

    return result, changes, round(ambiguity, 2)


NL_REWRITE_PROMPT = """将下面的用户输入重写为更精确的表达，使AI不容易产生幻觉。

规则：
- 删除模糊修饰词（很好的、大量的、非常等）
- 补全省略的上下文和隐含前提
- 将暗示性表达改为明确指令
- 如有多个意图，拆为编号列表
- 添加具体约束（格式、范围、数量等）

参考NLP能力：
{proven_context}

用户原文：
{user_input}

规则层已处理为：
{rule_result}

请在规则层基础上进一步优化，输出最终的精确表达（只输出重写后的文字，不要解释）："""


@app.route('/api/nl_rewrite', methods=['POST'])
def api_nl_rewrite():
    """将自然语言重写为低幻觉表达（规则层+LLM层双重处理）"""
    data = request.json
    user_input = data.get('text', '').strip()
    if not user_input:
        return jsonify({"error": "输入不能为空"}), 400

    broadcast_step("nl_rewrite", f"🔄 NL重写: {user_input[:60]}...", "running")
    console_log(f"NL重写请求: {user_input[:80]}")

    try:
        # ---- 第1层：规则引擎（确定性，零幻觉）----
        rule_text, rule_changes, ambiguity = _rule_based_rewrite(user_input)
        broadcast_step("nl_rewrite", f"规则层完成: {len(rule_changes)}处改动", "running")

        # ---- 搜索相关NLP proven节点 ----
        nlp_nodes = lattice.find_similar_nodes(user_input, threshold=0.3, limit=10)
        nlp_proven = [n for n in nlp_nodes if n.get('status') == 'proven' and 'NLP' in n.get('domain', '')]
        if len(nlp_proven) < 3:
            with lattice._lock:
                c = lattice.conn.cursor()
                c.execute("""
                    SELECT content FROM cognitive_nodes
                    WHERE domain LIKE 'NLP-%' AND status = 'proven'
                    ORDER BY RANDOM() LIMIT 5
                """)
                extra = [row['content'] for row in c.fetchall()]
                nlp_proven.extend([{"content": e} for e in extra])

        proven_context = "\n".join([f"- {n['content'][:80]}" for n in nlp_proven[:8]])

        # ---- 第2层：LLM精修（在规则层基础上进一步优化）----
        llm_rewritten = rule_text  # 默认使用规则层结果
        llm_changes = []
        try:
            prompt_text = NL_REWRITE_PROMPT.format(
                proven_context=proven_context or "（无）",
                user_input=user_input,
                rule_result=rule_text
            )
            messages = [{"role": "user", "content": prompt_text}]
            result = agi.llm_call(messages)
            raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)

            # 提取LLM输出的纯文本重写结果
            cleaned = raw.strip()
            # 去掉可能的引号包裹
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            if cleaned.startswith('```') and cleaned.endswith('```'):
                cleaned = cleaned[3:-3].strip()

            # 只有当LLM输出合理长度时才采用
            if cleaned and 5 < len(cleaned) < len(user_input) * 5:
                llm_rewritten = cleaned
                llm_changes.append("LLM精修：补全上下文与约束")
                if llm_rewritten != rule_text:
                    llm_changes.append("LLM在规则层基础上进一步优化了表达")
        except Exception as e:
            console_log(f"NL重写LLM层失败(回退规则层): {e}")
            llm_changes.append(f"LLM层跳过(使用规则层结果): {str(e)[:50]}")

        # ---- 锚定校验 ----
        grounding_anchors = 0
        grounding_rate = 0.0
        if llm_rewritten:
            anchor_nodes = lattice.find_similar_nodes(llm_rewritten, threshold=0.4, limit=5)
            anchor_proven = [n for n in anchor_nodes if n.get('status') == 'proven']
            grounding_anchors = len(anchor_proven)
            grounding_rate = len(anchor_proven) / max(len(anchor_nodes), 1)

        # ---- 构建结果 ----
        all_changes = rule_changes + llm_changes
        tips = []
        if ambiguity > 0.5:
            tips.append("原文歧义度较高，建议添加更多具体约束")
        if grounding_anchors == 0:
            tips.append("重写结果未命中已知知识节点，建议核实表达准确性")
        if not tips:
            tips.append("表达已优化，可直接使用")

        rewrite_result = {
            "rewritten": llm_rewritten,
            "rule_rewritten": rule_text,
            "changes": all_changes,
            "ambiguity_score": ambiguity,
            "grounding_anchors": grounding_anchors,
            "grounding_rate": round(grounding_rate, 2),
            "tips": "；".join(tips)
        }

        broadcast_step("nl_rewrite",
                        f"✓ 重写完成 (歧义度: {ambiguity}, 锚定: {grounding_anchors})",
                        "done")
        console_log(f"NL重写完成: {llm_rewritten[:80]}")

        return jsonify({
            "success": True,
            "original": user_input,
            "result": rewrite_result,
            "proven_context_count": len(nlp_proven),
        })

    except Exception as e:
        broadcast_step("nl_rewrite", f"✗ 重写失败: {e}", "error")
        console_log(f"NL重写失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== 数学公式编码引擎 ====================
_math_engine = None

def _get_math_engine():
    global _math_engine
    if _math_engine is None:
        try:
            from workspace.skills.math_formula_engine import MathFormulaEngine
            _math_engine = MathFormulaEngine()
        except Exception as e:
            console_log(f"数学公式引擎加载失败: {e}")
    return _math_engine


@app.route('/api/math/formalize', methods=['POST'])
def api_math_formalize():
    """将自然语言问题形式化为数学表达"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    data = request.json
    problem = data.get('problem', '').strip()
    if not problem:
        return jsonify({"error": "问题不能为空"}), 400
    result = engine.formalize(problem)
    return jsonify({"success": True, "result": result})


@app.route('/api/math/execute', methods=['POST'])
def api_math_execute():
    """执行数学公式并返回结果"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    data = request.json
    formula_id = data.get('formula_id')
    formula_python = data.get('formula_python')
    variables = data.get('variables', {})
    result = engine.execute(formula_id=formula_id, formula_python=formula_python, variables=variables)
    return jsonify({"success": result.get("success", False), "result": result})


@app.route('/api/math/decompose', methods=['POST'])
def api_math_decompose():
    """将复杂问题拆解为公式树"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    data = request.json
    problem = data.get('problem', '').strip()
    if not problem:
        return jsonify({"error": "问题不能为空"}), 400
    from workspace.skills.math_formula_engine import decompose
    result = decompose(problem)
    return jsonify({"success": True, "result": result})


@app.route('/api/math/temperature', methods=['POST'])
def api_math_temperature():
    """温差推演分析"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    data = request.json
    T = data.get('temperature', 900)
    C = data.get('carbon', 0.5)
    delta_T = data.get('delta_t', 10.0)
    result = engine.temperature_differential_analysis(T, C, delta_T)
    return jsonify({"success": True, "result": result})


@app.route('/api/math/collision', methods=['POST'])
def api_math_collision():
    """四向碰撞推演：温度×碳含量网格"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    data = request.json
    result = engine.four_direction_collision(
        T_start=data.get('t_start', 25),
        T_end=data.get('t_end', 1600),
        T_step=data.get('t_step', 100),
        C_start=data.get('c_start', 0),
        C_end=data.get('c_end', 6.69),
        C_step=data.get('c_step', 0.5),
    )
    return jsonify({"success": True, "result": result})


@app.route('/api/math/formulas', methods=['GET'])
def api_math_formulas():
    """列出所有已知数学公式"""
    from workspace.skills.math_formula_engine import list_formulas
    return jsonify({"success": True, "formulas": list_formulas()})


@app.route('/api/math/inject', methods=['POST'])
def api_math_inject():
    """将proven公式节点注入认知晶格"""
    engine = _get_math_engine()
    if not engine:
        return jsonify({"error": "数学引擎未加载"}), 500
    result = engine.inject_proven_formulas(lattice)
    return jsonify({"success": True, **result})


@app.route('/api/node/verify', methods=['POST'])
def api_node_verify():
    """将假设节点转为已证(proven)真实节点，并强化关联"""
    data = request.json
    node_id = data.get('node_id')
    new_status = data.get('status', 'proven')  # proven | falsified
    if not node_id:
        return jsonify({"error": "需要 node_id"}), 400

    c = lattice.conn.cursor()
    c.execute("SELECT id, content, domain, status FROM cognitive_nodes WHERE id=?", (node_id,))
    row = c.fetchone()
    if not row:
        return jsonify({"error": "节点不存在"}), 404

    old_status = row['status']
    with lattice._lock:
        c.execute("UPDATE cognitive_nodes SET status=?, last_verified_at=datetime('now') WHERE id=?",
                  (new_status, node_id))
        lattice.conn.commit()

    # 如果转为 proven，尝试发现更多关联
    new_links = 0
    if new_status == 'proven':
        try:
            similar = lattice.find_similar_nodes(row['content'], threshold=0.45, limit=10)
            for s in similar:
                if s['id'] != node_id:
                    added = lattice.add_relation(node_id, s['id'], "verified_linked",
                                                 s['similarity'],
                                                 f"验证后强化关联 ({s['similarity']:.3f})")
                    if added:
                        new_links += 1
        except Exception:
            pass

    status_labels = {'proven': '已证✓', 'falsified': '已伪✗', 'known': '已知', 'hypothesis': '假设'}
    broadcast_step("verify",
                   f"节点#{node_id} {status_labels.get(old_status, old_status)}→{status_labels.get(new_status, new_status)}, +{new_links}关联",
                   "done")

    return jsonify({
        "success": True,
        "node_id": node_id,
        "old_status": old_status,
        "new_status": new_status,
        "new_links": new_links
    })


# ==================== SSE 实时推演流 ====================
@app.route('/api/stream')
def api_stream():
    """SSE 端点：前端订阅后实时接收执行步骤"""
    def event_stream():
        q = queue.Queue(maxsize=200)
        with _sse_lock:
            _sse_queues.append(q)
        try:
            yield f"data: {json.dumps({'type': 'connected', 'detail': 'SSE 已连接'}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    entry = q.get(timeout=30)
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield f": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if q in _sse_queues:
                    _sse_queues.remove(q)

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/execution_log')
def api_execution_log():
    """获取最近的执行日志"""
    n = int(request.args.get('limit', 50))
    return jsonify(action_engine.get_recent_log(n))


# ==================== 动作引擎 API ====================
@app.route('/api/workspace')
def api_workspace():
    """列出工作区文件"""
    files = action_engine.FileAction.list_workspace()
    return jsonify(files)


@app.route('/api/workspace/read', methods=['POST'])
def api_workspace_read():
    """读取工作区文件内容"""
    data = request.json
    filepath = data.get('path', '')
    result = action_engine.FileAction.read_file(filepath)
    return jsonify(result)


@app.route('/api/skills')
def api_skills():
    """列出所有技能"""
    return jsonify(action_engine.SkillBuilder.list_skills())


@app.route('/api/skills/run', methods=['POST'])
def api_skills_run():
    """执行技能"""
    data = request.json
    name = data.get('name', '')
    if not name:
        return jsonify({"error": "技能名不能为空"}), 400
    broadcast_step("skill_run", f"执行技能: {name}", "running")
    result = action_engine.SkillBuilder.run_skill(name)
    return jsonify(result)


@app.route('/api/skills/route', methods=['POST'])
def api_skills_route():
    """PCM 智能技能路由: 意图识别 + 精准推送最匹配的 Skill"""
    data = request.json or {}
    query = data.get('query', '').strip()
    top_k = int(data.get('top_k', 10))
    if not query:
        return jsonify({"error": "query 不能为空"}), 400
    try:
        results = route_skills(query, top_k=top_k)
        # 服务端格式化，避免二次路由计算
        lines = [f"[Skill Router] 匹配到 {len(results)} 个相关技能:"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r['name']} (score={r['score']}, {r['category']}): {r['description'][:80]}")
        return jsonify({
            "query": query,
            "total": len(results),
            "skills": results,
            "formatted": "\n".join(lines),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/seed_code_nodes', methods=['POST'])
def api_seed_code_nodes():
    """注入代码实现领域的细化真实节点"""
    broadcast_step("seed_code", "🔧 注入代码实现领域真实节点...", "running")
    console_log("开始注入代码实现领域真实节点")

    CODE_NODES = [
        # ===== Python 核心实践 =====
        ("Python列表推导式比for循环快2-3倍，因为字节码在C层执行避免了Python循环开销", "Python核心"),
        ("Python装饰器本质是高阶函数：接收函数返回函数，@语法糖等价于 func = decorator(func)", "Python核心"),
        ("Python的GIL使多线程无法并行CPU密集任务，IO密集用threading，CPU密集用multiprocessing", "Python核心"),
        ("Python上下文管理器__enter__/__exit__确保资源释放，with语句即使异常也会调用__exit__", "Python核心"),
        ("Python生成器yield实现惰性求值，处理大数据时内存占用O(1)而非O(n)", "Python核心"),
        ("Python dataclass装饰器自动生成__init__/__repr__/__eq__，减少样板代码", "Python核心"),
        ("Python类型注解+mypy静态检查可在运行前发现类型错误，大型项目必备", "Python核心"),
        ("Python asyncio事件循环单线程处理并发IO，await挂起协程不阻塞线程", "Python核心"),
        ("Python __slots__限制实例属性，减少内存占用约40%，适用于大量实例场景", "Python核心"),
        ("Python functools.lru_cache装饰器实现函数结果缓存，递归函数性能提升指数级", "Python核心"),

        # ===== 软件架构模式 =====
        ("单一职责原则(SRP)：每个类/函数只做一件事，修改原因应唯一", "软件架构"),
        ("依赖注入(DI)：高层模块不依赖低层模块，两者依赖抽象接口", "软件架构"),
        ("MVC模式将数据(Model)、展示(View)、控制逻辑(Controller)分离，降低耦合", "软件架构"),
        ("微服务架构每个服务独立部署，通过API通信，故障隔离但增加运维复杂度", "软件架构"),
        ("事件驱动架构通过消息队列解耦生产者消费者，实现异步处理和削峰填谷", "软件架构"),
        ("策略模式将算法封装为可互换的类，运行时动态选择，避免大量if-else", "软件架构"),
        ("观察者模式实现一对多依赖：当对象状态变化时自动通知所有订阅者", "软件架构"),
        ("工厂模式将对象创建逻辑集中管理，客户端无需知道具体类名", "软件架构"),
        ("SOLID原则中的开闭原则：对扩展开放对修改关闭，通过继承/组合添加功能", "软件架构"),
        ("领域驱动设计(DDD)用统一语言建模业务，聚合根保证事务一致性边界", "软件架构"),

        # ===== 数据库实践 =====
        ("SQL索引B+树结构使查询从O(n)降至O(log n)，但写入时需维护索引", "数据库"),
        ("数据库事务ACID：原子性/一致性/隔离性/持久性，保证数据完整", "数据库"),
        ("SQLite单文件数据库，WAL模式支持并发读+单写，适合嵌入式和小型应用", "数据库"),
        ("SQL JOIN操作：INNER只返回匹配行，LEFT保留左表全部行，RIGHT保留右表全部行", "数据库"),
        ("数据库连接池复用连接对象，避免频繁创建销毁连接的开销", "数据库"),
        ("ORM将数据库表映射为对象，SQLAlchemy支持两种模式：Core(SQL表达式)和ORM(对象映射)", "数据库"),
        ("数据库规范化(1NF-3NF)消除数据冗余，反规范化用空间换时间优化查询性能", "数据库"),
        ("SQL注入防御：永远使用参数化查询(占位符?)而非字符串拼接", "数据库"),

        # ===== Web开发实践 =====
        ("RESTful API设计：GET读取/POST创建/PUT更新/DELETE删除，无状态通信", "Web开发"),
        ("HTTP状态码语义：2xx成功/3xx重定向/4xx客户端错误/5xx服务器错误", "Web开发"),
        ("Flask路由装饰器@app.route将URL映射到处理函数，支持动态参数<param>", "Web开发"),
        ("CORS跨域资源共享：服务端设置Access-Control-Allow-Origin头允许跨域请求", "Web开发"),
        ("WebSocket实现全双工通信，适合实时推送场景，SSE适合服务端单向推送", "Web开发"),
        ("JWT(JSON Web Token)无状态认证：Header.Payload.Signature，服务端无需存session", "Web开发"),
        ("前端fetch API返回Promise，支持async/await，替代XMLHttpRequest", "Web开发"),
        ("CSS Flexbox一维布局：justify-content主轴对齐，align-items交叉轴对齐", "Web开发"),

        # ===== 测试工程 =====
        ("单元测试覆盖单个函数/方法，集成测试覆盖模块间交互，端到端测试覆盖完整流程", "测试工程"),
        ("pytest框架：assert直接断言，fixture管理测试依赖，parametrize参数化测试", "测试工程"),
        ("测试金字塔：大量单元测试(快)+适量集成测试(中)+少量E2E测试(慢)", "测试工程"),
        ("Mock/Stub替换外部依赖：unittest.mock.patch替换函数，MagicMock模拟对象", "测试工程"),
        ("TDD测试驱动开发：先写失败测试→写最少代码通过→重构，红绿重构循环", "测试工程"),
        ("代码覆盖率工具coverage.py测量哪些代码行被测试执行，80%覆盖率是合理目标", "测试工程"),

        # ===== Git版本控制 =====
        ("Git三区模型：工作区→暂存区(stage)→仓库，commit是不可变快照非差异", "版本控制"),
        ("Git分支是指向commit的可移动指针，创建分支O(1)开销，鼓励频繁分支", "版本控制"),
        ("Git rebase将分支变基到目标分支最新提交，保持线性历史但改写commit", "版本控制"),
        ("Git cherry-pick将指定commit应用到当前分支，用于跨分支移植修复", "版本控制"),
        (".gitignore文件排除不需要版本控制的文件，支持glob模式匹配", "版本控制"),

        # ===== 调试与性能 =====
        ("Python cProfile模块分析函数调用次数和耗时，找到性能瓶颈", "调试与性能"),
        ("断点调试pdb：import pdb; pdb.set_trace()在指定位置暂停，n下一步s进入", "调试与性能"),
        ("算法复杂度：哈希表O(1)查找，排序O(n log n)，暴力搜索O(n²)需避免", "调试与性能"),
        ("Python内存分析：objgraph追踪对象引用，tracemalloc追踪内存分配来源", "调试与性能"),
        ("缓存策略：LRU最近最少使用淘汰，TTL基于时间过期，适用于重复计算/请求", "调试与性能"),
        ("日志分级：DEBUG开发调试/INFO运行状态/WARNING潜在问题/ERROR错误/CRITICAL致命", "调试与性能"),

        # ===== 代码生成与AI辅助 =====
        ("LLM代码生成需要明确的需求描述+输入输出示例+约束条件才能产出高质量代码", "AI辅助编程"),
        ("AI生成代码必须经过人工审查和测试验证，不可直接部署到生产环境", "AI辅助编程"),
        ("Prompt工程：分步骤指令比一次性复杂指令效果好，Few-shot示例提升准确率", "AI辅助编程"),
        ("代码重构时保持测试通过是安全网，每次小改动后运行测试确认无回归", "AI辅助编程"),
        ("AST(抽象语法树)解析源代码为树形结构，实现代码分析/转换/生成", "AI辅助编程"),

        # ===== 错误处理模式 =====
        ("Python异常层次：BaseException→Exception→具体异常，只捕获预期的具体异常", "错误处理"),
        ("防御式编程：函数入口验证参数，早期失败(fail fast)比隐式错误更易调试", "错误处理"),
        ("重试模式：对临时性故障(网络超时)自动重试，指数退避避免雪崩效应", "错误处理"),
        ("Python logging模块替代print调试：结构化日志+级别过滤+多输出目标", "错误处理"),
        ("哨兵值模式：用特殊对象SENTINEL=object()替代None作为默认值，区分未传参和传None", "错误处理"),

        # ===== 并发编程 =====
        ("Python concurrent.futures提供线程池ThreadPoolExecutor和进程池ProcessPoolExecutor的统一高级接口", "并发编程"),
        ("死锁四条件：互斥+占有等待+不可抢占+循环等待，打破任意一条即可避免死锁", "并发编程"),
        ("Python threading.Lock保证互斥访问共享资源，with lock:自动获取释放，避免忘记释放", "并发编程"),
        ("Python queue.Queue线程安全队列，生产者消费者模式的标准实现", "并发编程"),
        ("asyncio.gather并发执行多个协程，asyncio.wait可设置超时和完成条件", "并发编程"),
        ("Python信号量Semaphore限制并发数量，用于限流和资源池管理", "并发编程"),

        # ===== 数据结构与算法 =====
        ("哈希表(dict)平均O(1)查找/插入/删除，是Python中最常用的数据结构", "数据结构"),
        ("collections.defaultdict避免KeyError，Counter统计频率，deque双端队列O(1)两端操作", "数据结构"),
        ("堆(heapq)实现优先队列：heappush/heappop保持最小堆，适用于Top-K和调度问题", "数据结构"),
        ("二分查找bisect模块：bisect_left/insort在有序列表中O(log n)查找和插入", "数据结构"),
        ("图的BFS用队列实现层序遍历求最短路径，DFS用栈/递归实现深度优先探索", "数据结构"),
        ("动态规划核心：定义状态+状态转移方程+边界条件，用空间换时间避免重复计算", "数据结构"),
        ("Python sorted()使用TimSort算法，稳定排序O(n log n)，key参数指定排序依据", "数据结构"),

        # ===== 网络编程 =====
        ("TCP三次握手建立连接(SYN→SYN-ACK→ACK)，四次挥手断开(FIN→ACK→FIN→ACK)", "网络编程"),
        ("HTTP/2多路复用在单个TCP连接上并发传输多个请求响应，消除队头阻塞", "网络编程"),
        ("Python requests库：Session对象复用TCP连接，自动处理Cookie和重定向", "网络编程"),
        ("gRPC基于HTTP/2和Protocol Buffers，比REST+JSON更高效，适合微服务间通信", "网络编程"),
        ("WebSocket握手后升级为全双工通信，心跳机制(ping/pong)检测连接存活", "网络编程"),

        # ===== DevOps实践 =====
        ("Docker容器封装应用及依赖，Dockerfile定义构建步骤，镜像分层缓存加速构建", "DevOps"),
        ("CI/CD持续集成持续部署：代码提交→自动测试→自动构建→自动部署，减少人工错误", "DevOps"),
        ("环境变量存储配置和密钥，python-dotenv从.env文件加载，绝不硬编码密钥", "DevOps"),
        ("Linux进程管理：systemd管理服务，supervisor守护进程，nohup后台运行", "DevOps"),
        ("Nginx反向代理：负载均衡+SSL终止+静态文件服务+请求缓存", "DevOps"),

        # ===== 安全编程 =====
        ("密码存储必须使用bcrypt/argon2等慢哈希算法+盐值，绝不存储明文或MD5/SHA", "安全编程"),
        ("XSS防御：对用户输入进行HTML转义，CSP策略限制脚本来源", "安全编程"),
        ("CSRF防御：使用随机Token验证请求来源，SameSite Cookie属性限制跨站发送", "安全编程"),
        ("最小权限原则：程序和用户只赋予完成任务所需的最小权限，降低攻击面", "安全编程"),

        # ===== 函数式编程 =====
        ("Python map/filter/reduce函数式操作：map变换每个元素，filter过滤，reduce聚合", "函数式编程"),
        ("纯函数无副作用：相同输入永远相同输出，不修改外部状态，易于测试和推理", "函数式编程"),
        ("Python itertools模块：chain连接迭代器，product笛卡尔积，groupby分组", "函数式编程"),
        ("闭包捕获外部变量：内部函数引用外部函数的局部变量，变量生命周期延长", "函数式编程"),
        ("Python partial偏函数：固定部分参数生成新函数，简化重复调用模式", "函数式编程"),
    ]

    count = 0
    linked_total = 0
    for content, domain in CODE_NODES:
        nid = lattice.add_node(content, domain, "proven", source="code_practice_seed")
        if nid:
            count += 1
            try:
                similar = lattice.find_similar_nodes(content, threshold=0.55, limit=5)
                for s in similar:
                    if s['id'] != nid:
                        lattice.add_relation(nid, s['id'], "practice_linked", s['similarity'],
                                             f"代码实践关联 ({s['similarity']:.3f})")
                        linked_total += 1
            except Exception:
                pass
        if count % 10 == 0:
            broadcast_step("seed_code", f"已注入 {count}/{len(CODE_NODES)} 节点...", "running")
            console_log(f"代码节点注入进度: {count}/{len(CODE_NODES)}")

    broadcast_step("seed_code", f"✓ 注入完成: {count}节点, {linked_total}关联", "done")
    console_log(f"代码实现领域注入完成: {count}节点, {linked_total}关联")
    return jsonify({"success": True, "injected": count, "linked": linked_total, "stats": lattice.stats()})


@app.route('/api/bootstrap', methods=['POST'])
def api_bootstrap():
    """引导注册所有技能为真实认知节点"""
    broadcast_step("bootstrap", "🚀 能力引导启动...", "running")
    try:
        import sys
        sys.path.insert(0, str(action_engine.WORKSPACE_DIR))
        from skills.capability_bootstrap import bootstrap_capabilities
        result = bootstrap_capabilities(lattice)
        broadcast_step("bootstrap", f"✓ 注册{result.get('registered',0)}项能力", "done")
        loadStats_after = lattice.stats()
        return jsonify({"success": True, **result, "stats": loadStats_after})
    except Exception as e:
        broadcast_step("bootstrap", f"引导失败: {e}", "error")
        return jsonify({"error": str(e)}), 500


@app.route('/api/advanced_action', methods=['POST'])
def api_advanced_action():
    """执行高级技能动作"""
    data = request.json
    act_type = data.get('action', '')
    params = data.get('params', {})
    if not act_type:
        return jsonify({"error": "需要 action 参数"}), 400
    broadcast_step(act_type, f"手动触发: {act_type}", "running")
    result = action_engine._dispatch_advanced_action(act_type, params, lattice)
    # 反馈到认知网络
    if result.get('success'):
        action_engine.action_to_nodes(
            [{"step": 1, "action": act_type, "reasoning": f"手动触发 {act_type}", "result": result}],
            lattice
        )
    return jsonify(result)


@app.route('/api/execute', methods=['POST'])
def api_execute():
    """直接执行 Python 代码"""
    data = request.json
    code = data.get('code', '')
    filepath = data.get('filepath', '')
    if not code and not filepath:
        return jsonify({"error": "需要 code 或 filepath"}), 400
    broadcast_step("execute", "手动执行代码", "running")
    result = action_engine.ExecuteAction.run_python(filepath=filepath or None, code=code or None)
    return jsonify(result)


# ==================== Shell Executor API ====================

@app.route('/api/shell/run', methods=['POST'])
def api_shell_run():
    """通过API执行shell命令"""
    from workspace.skills.shell_executor import run_shell
    data = request.json or {}
    cmd = data.get('cmd', '')
    if not cmd:
        return jsonify({"error": "需要 cmd 参数"}), 400
    result = run_shell(cmd, cwd=data.get('cwd'), timeout=data.get('timeout', 30))
    return jsonify(result)

@app.route('/api/shell/python', methods=['POST'])
def api_shell_python():
    """通过API执行Python代码片段"""
    from workspace.skills.shell_executor import run_python
    data = request.json or {}
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "需要 code 参数"}), 400
    result = run_python(code, timeout=data.get('timeout', 30))
    return jsonify(result)

@app.route('/api/shell/script', methods=['POST'])
def api_shell_script():
    """通过API执行Python脚本"""
    from workspace.skills.shell_executor import run_script
    data = request.json or {}
    path = data.get('path', '')
    if not path:
        return jsonify({"error": "需要 path 参数"}), 400
    result = run_script(path, args=data.get('args'), timeout=data.get('timeout', 60))
    return jsonify(result)

@app.route('/api/shell/port', methods=['POST'])
def api_shell_port():
    """检查端口状态"""
    from workspace.skills.shell_executor import check_port
    data = request.json or {}
    port = data.get('port')
    if not port:
        return jsonify({"error": "需要 port 参数"}), 400
    return jsonify(check_port(int(port), data.get('host', 'localhost')))

@app.route('/api/shell/info')
def api_shell_info():
    """获取系统信息"""
    from workspace.skills.shell_executor import system_info
    return jsonify(system_info())

@app.route('/api/shell/batch', methods=['POST'])
def api_shell_batch():
    """批量执行命令"""
    from workspace.skills.shell_executor import batch_run
    data = request.json or {}
    commands = data.get('commands', [])
    if not commands:
        return jsonify({"error": "需要 commands 列表"}), 400
    return jsonify(batch_run(commands))


# ==================== 智谱 AI 云端算力 API ====================

@app.route('/api/zhipu/models')
def api_zhipu_models():
    """获取可用智谱AI模型列表"""
    from workspace.skills.zhipu_ai_caller import get_available_models
    return jsonify(get_available_models())

@app.route('/api/zhipu/call', methods=['POST'])
def api_zhipu_call():
    """调用智谱AI完成任务"""
    from workspace.skills.zhipu_ai_caller import call_zhipu
    data = request.json or {}
    prompt = data.get('prompt', '')
    if not prompt:
        return jsonify({"error": "需要 prompt 参数"}), 400
    result = call_zhipu(
        prompt=prompt,
        task_type=data.get('task_type', 'chat'),
        model=data.get('model'),
        system_prompt=data.get('system_prompt'),
        temperature=data.get('temperature', 0.4),
        max_tokens=data.get('max_tokens'),
        session_id=data.get('session_id'),
        verify_locally=data.get('verify', False),
    )
    return jsonify(result)

@app.route('/api/zhipu/delegate', methods=['POST'])
def api_zhipu_delegate():
    """智能委托 — 自动分析任务并选择最优模型"""
    from workspace.skills.zhipu_ai_caller import smart_delegate
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    broadcast_step("zhipu", f"🌐 智谱AI委托: {task[:60]}", "running")
    # 收集相关节点作为上下文
    ctx = None
    if lattice:
        try:
            related = lattice.find_similar_nodes(task, threshold=0.4, limit=3)
            if related:
                ctx = [{"domain": n.get("domain",""), "content": n.get("content","")} for n in related]
        except Exception:
            pass
    result = smart_delegate(
        task=task,
        local_context=ctx,
        force_model=data.get('model'),
        verify=data.get('verify', True),
    )
    broadcast_step("zhipu", f"智谱AI完成: {result.get('model','?')} {result.get('duration',0):.1f}s", "done" if result.get("success") else "error")
    return jsonify(result)

@app.route('/api/zhipu/code', methods=['POST'])
def api_zhipu_code():
    """委托智谱AI生成代码"""
    from workspace.skills.zhipu_ai_caller import generate_code
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    result = generate_code(
        task=task,
        language=data.get('language', 'python'),
        model=data.get('model'),
        verify=data.get('verify', True),
    )
    return jsonify(result)

@app.route('/api/zhipu/reasoning', methods=['POST'])
def api_zhipu_reasoning():
    """委托智谱AI进行深度推理"""
    from workspace.skills.zhipu_ai_caller import deep_reasoning
    data = request.json or {}
    question = data.get('question', '')
    if not question:
        return jsonify({"error": "需要 question 参数"}), 400
    result = deep_reasoning(
        question=question,
        context=data.get('context'),
        model=data.get('model'),
    )
    return jsonify(result)

@app.route('/api/zhipu/chat', methods=['POST'])
def api_zhipu_chat():
    """智谱AI多轮对话"""
    from workspace.skills.zhipu_ai_caller import multi_turn_chat
    data = request.json or {}
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    if not message:
        return jsonify({"error": "需要 message 参数"}), 400
    result = multi_turn_chat(
        message=message,
        session_id=session_id,
        system_prompt=data.get('system_prompt'),
        model=data.get('model'),
    )
    return jsonify(result)

@app.route('/api/zhipu/stats')
def api_zhipu_stats():
    """获取智谱AI使用统计"""
    from workspace.skills.zhipu_ai_caller import get_usage_stats
    return jsonify(get_usage_stats())

@app.route('/api/zhipu/test', methods=['POST'])
def api_zhipu_test():
    """测试智谱AI连接"""
    from workspace.skills.zhipu_ai_caller import test_connection
    data = request.json or {}
    model = data.get('model', 'glm-4-flash')
    result = test_connection(model)
    return jsonify(result)

@app.route('/api/zhipu/sessions')
def api_zhipu_sessions():
    """列出活跃会话"""
    from workspace.skills.zhipu_ai_caller import list_sessions
    return jsonify({"sessions": list_sessions()})

@app.route('/api/zhipu/sessions/clear', methods=['POST'])
def api_zhipu_sessions_clear():
    """清除会话"""
    from workspace.skills.zhipu_ai_caller import clear_session, clear_all_sessions
    data = request.json or {}
    sid = data.get('session_id')
    if sid:
        ok = clear_session(sid)
        return jsonify({"success": ok})
    else:
        clear_all_sessions()
        return jsonify({"success": True, "cleared": "all"})


# ==================== OpenClaw能力增强 API ====================

@app.route('/api/openclaw/search', methods=['POST'])
def api_openclaw_enhanced_search():
    """增强搜索：查询扩展 + 时间衰减 + MMR多样性重排"""
    from workspace.skills.openclaw_abilities import enhanced_search
    data = request.json or {}
    query = data.get('query', '')
    if not query:
        return jsonify({"error": "query required"}), 400

    # 先用认知格搜索获取原始结果
    raw = agi.find_similar_nodes(query, threshold=data.get('threshold', 0.3), limit=data.get('limit', 20))
    result = enhanced_search(
        query, raw,
        mmr_lambda=data.get('mmr_lambda', 0.7),
        decay_half_life=data.get('decay_half_life', 30.0),
        apply_mmr=data.get('apply_mmr', True),
        apply_decay=data.get('apply_decay', False),
    )
    return jsonify(result)

@app.route('/api/openclaw/verify', methods=['POST'])
def api_openclaw_verify_content():
    """可验证性分类：判断内容是否可通过实践直接验证"""
    from workspace.skills.openclaw_abilities import classify_verifiability
    data = request.json or {}
    content = data.get('content', '')
    if not content:
        return jsonify({"error": "content required"}), 400
    result = classify_verifiability(content)
    return jsonify(result)

@app.route('/api/openclaw/expand', methods=['POST'])
def api_openclaw_expand_query():
    """查询扩展：将口语化查询转为结构化搜索关键词"""
    from workspace.skills.openclaw_abilities import expand_query
    data = request.json or {}
    query = data.get('query', '')
    if not query:
        return jsonify({"error": "query required"}), 400
    result = expand_query(query)
    return jsonify(result)

@app.route('/api/openclaw/mmr', methods=['POST'])
def api_openclaw_mmr():
    """MMR重排：对搜索结果应用多样性重排"""
    from workspace.skills.openclaw_abilities import mmr_rerank
    data = request.json or {}
    items = data.get('items', [])
    lam = data.get('lambda', 0.7)
    if not items:
        return jsonify({"error": "items required"}), 400
    result = mmr_rerank(items, lam=lam)
    return jsonify({"results": result, "count": len(result)})


# ==================== 超越引擎 API ====================

@app.route('/api/surpass', methods=['POST'])
def api_surpass():
    """超越引擎 — 自动分析任务复杂度并选择最优策略"""
    from workspace.skills.surpass_engine import surpass
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    broadcast_step("surpass", f"🚀 超越引擎: {task[:60]}", "running")
    result = surpass(
        task=task,
        lattice=lattice,
        force_strategy=data.get('strategy'),
        force_model=data.get('model'),
        verify=data.get('verify', True),
    )
    strat = result.get("strategy", "?")
    dur = result.get("total_duration", 0)
    broadcast_step("surpass", f"超越引擎({strat}) 完成 {dur:.1f}s", "done" if result.get("success") else "error")
    return jsonify(result)

@app.route('/api/surpass/code', methods=['POST'])
def api_surpass_code():
    """超越引擎 — 迭代精炼代码(生成→执行→修复→循环)"""
    from workspace.skills.surpass_engine import IterativeRefiner
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    result = IterativeRefiner.refine_code(
        task=task,
        language=data.get('language', 'python'),
        model=data.get('model', 'glm-4-plus'),
        lattice=lattice,
    )
    return jsonify(result)

@app.route('/api/surpass/reason', methods=['POST'])
def api_surpass_reason():
    """超越引擎 — 结构化思维链深度推理"""
    from workspace.skills.surpass_engine import StructuredCoT
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    result = StructuredCoT.solve(
        task=task,
        model=data.get('model', 'glm-4-plus'),
        lattice=lattice,
    )
    return jsonify(result)

@app.route('/api/surpass/vote', methods=['POST'])
def api_surpass_vote():
    """超越引擎 — 多模型投票(关键任务)"""
    from workspace.skills.surpass_engine import EnsembleVoter
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    models = data.get('models')  # 可自定义投票模型
    result = EnsembleVoter.vote(task=task, models=models, lattice=lattice)
    return jsonify(result)

@app.route('/api/surpass/analyze', methods=['POST'])
def api_surpass_analyze():
    """分析任务复杂度和推荐策略(不执行)"""
    from workspace.skills.surpass_engine import TaskAnalyzer
    data = request.json or {}
    task = data.get('task', '')
    if not task:
        return jsonify({"error": "需要 task 参数"}), 400
    ctx = []
    if lattice:
        try:
            ctx = lattice.find_similar_nodes(task, threshold=0.35, limit=5)
        except Exception:
            pass
    analysis = TaskAnalyzer.analyze(task, ctx)
    return jsonify(analysis)


# ==================== 集群管理 API ====================

@app.route('/api/cluster/local')
def api_cluster_local():
    """获取本机信息"""
    dm = cluster_manager.get_device_manager()
    return jsonify(dm.get_local_info())


@app.route('/api/cluster/devices')
def api_cluster_devices():
    """列出所有设备"""
    dm = cluster_manager.get_device_manager()
    return jsonify(dm.list_devices())


@app.route('/api/cluster/add_device', methods=['POST'])
def api_cluster_add_device():
    """手动添加设备"""
    data = request.json
    ip = data.get('ip', '').strip()
    name = data.get('name', '')
    os_type = data.get('os', 'auto')
    if not ip:
        return jsonify({"error": "需要IP地址"}), 400
    dm = cluster_manager.get_device_manager()
    device = dm.add_device(ip, name, os_type)
    console_log(f"添加设备: {ip} ({name})")
    broadcast_step("cluster", f"添加设备: {ip}", "done")
    return jsonify({"success": True, "device": device})


@app.route('/api/cluster/remove_device', methods=['POST'])
def api_cluster_remove_device():
    """移除设备"""
    data = request.json
    ip = data.get('ip', '')
    dm = cluster_manager.get_device_manager()
    ok = dm.remove_device(ip)
    if ok:
        console_log(f"移除设备: {ip}")
        return jsonify({"success": True})
    return jsonify({"error": "设备不存在"}), 404


@app.route('/api/cluster/probe', methods=['POST'])
def api_cluster_probe():
    """探测设备状态"""
    data = request.json
    ip = data.get('ip', '')
    if not ip:
        return jsonify({"error": "需要IP地址"}), 400
    dm = cluster_manager.get_device_manager()
    info = dm.probe_device(ip)
    return jsonify(info)


@app.route('/api/cluster/scan', methods=['POST'])
def api_cluster_scan():
    """扫描局域网"""
    dm = cluster_manager.get_device_manager()
    broadcast_step("cluster", "🔍 扫描局域网设备...", "running")
    console_log("开始局域网扫描")
    found = dm.scan_lan(callback=lambda msg: console_log(msg))
    broadcast_step("cluster", f"扫描完成: 发现 {len(found)} 个设备", "done")
    console_log(f"局域网扫描完成: 发现 {len(found)} 个设备")
    return jsonify({"success": True, "found": found, "devices": dm.list_devices()})


@app.route('/api/cluster/refresh', methods=['POST'])
def api_cluster_refresh():
    """刷新所有设备状态"""
    dm = cluster_manager.get_device_manager()
    results = dm.refresh_all()
    return jsonify({"success": True, "devices": dm.list_devices()})


# ==================== 一键迁移 API ====================

@app.route('/api/migrate/package', methods=['POST'])
def api_migrate_package():
    """创建迁移包"""
    mm = cluster_manager.get_migration_manager()
    task_id = str(uuid.uuid4())[:8]
    broadcast_step("migrate", "📦 创建迁移包...", "running")
    console_log("开始创建迁移包")

    def do_package():
        result = mm.create_package(task_id)
        if result.get("success"):
            broadcast_step("migrate", f"📦 迁移包就绪: {result['size']/1024/1024:.1f}MB", "done")
            console_log(f"迁移包创建完成: {result['size']/1024/1024:.1f}MB")
        else:
            broadcast_step("migrate", f"打包失败: {result.get('error')}", "error")

    thread = threading.Thread(target=do_package, daemon=True)
    thread.start()
    return jsonify({"success": True, "task_id": task_id})


@app.route('/api/migrate/progress')
def api_migrate_progress():
    """查询迁移进度"""
    task_id = request.args.get('task_id', '')
    mm = cluster_manager.get_migration_manager()
    return jsonify(mm.get_progress(task_id))


@app.route('/api/migrate/push', methods=['POST'])
def api_migrate_push():
    """推送迁移包到目标设备"""
    data = request.json
    task_id = data.get('task_id', '')
    target_ip = data.get('target_ip', '')
    if not task_id or not target_ip:
        return jsonify({"error": "需要 task_id 和 target_ip"}), 400

    mm = cluster_manager.get_migration_manager()
    broadcast_step("migrate", f"🚀 推送到 {target_ip}...", "running")
    console_log(f"开始推送迁移包到 {target_ip}")

    def do_push():
        result = mm.push_to_device(task_id, target_ip)
        if result.get("success"):
            broadcast_step("migrate", f"✓ 迁移到 {target_ip} 完成!", "done")
            console_log(f"迁移推送完成: {target_ip}")
        else:
            broadcast_step("migrate", f"推送失败: {result.get('error')}", "error")
            console_log(f"迁移推送失败: {result.get('error')}")

    thread = threading.Thread(target=do_push, daemon=True)
    thread.start()
    return jsonify({"success": True})


# ==================== 分布式通讯 API ====================

@app.route('/api/distributed/status')
def api_distributed_status():
    """获取分布式路由状态"""
    dr = cluster_manager.get_distributed_router()
    return jsonify(dr.get_routing())


@app.route('/api/distributed/routing', methods=['POST'])
def api_distributed_routing():
    """设置路由模式"""
    data = request.json
    mode = data.get('mode', 'local')
    device_ip = data.get('device_ip', None)
    dr = cluster_manager.get_distributed_router()
    result = dr.set_routing(mode, device_ip)
    console_log(f"分布式路由切换: {mode}" + (f" → {device_ip}" if device_ip else ""))
    return jsonify({"success": True, **result})


@app.route('/api/distributed/connect', methods=['POST'])
def api_distributed_connect():
    """连接设备用于分布式推理"""
    data = request.json
    ip = data.get('ip', '')
    if not ip:
        return jsonify({"error": "需要IP地址"}), 400
    dr = cluster_manager.get_distributed_router()
    result = dr.connect_device(ip)
    if result.get("success"):
        broadcast_step("cluster", f"🔗 已连接 {ip} 用于分布式推理", "done")
        console_log(f"分布式连接: {ip}")
    return jsonify(result)


@app.route('/api/distributed/disconnect', methods=['POST'])
def api_distributed_disconnect():
    """断开设备"""
    data = request.json
    ip = data.get('ip', '')
    dr = cluster_manager.get_distributed_router()
    ok = dr.disconnect_device(ip)
    if ok:
        console_log(f"分布式断开: {ip}")
    return jsonify({"success": ok})


# ==================== 飞书集成 API ====================

@app.route('/api/feishu/config', methods=['GET', 'POST'])
def api_feishu_config():
    """获取/设置飞书配置"""
    fs = cluster_manager.get_feishu_integration()
    if request.method == 'POST':
        data = request.json
        result = fs.configure(
            webhook_url=data.get('webhook_url', ''),
            app_id=data.get('app_id', ''),
            app_secret=data.get('app_secret', ''),
            openclaw_endpoint=data.get('openclaw_endpoint', '')
        )
        console_log("飞书配置已更新")
        return jsonify({"success": True, "config": result})
    return jsonify(fs.get_config())


@app.route('/api/feishu/test', methods=['POST'])
def api_feishu_test():
    """测试飞书连接"""
    data = request.json
    message = data.get('message', '🧠 AGI Cognitive Lattice 连接测试')
    fs = cluster_manager.get_feishu_integration()
    result = fs.send_message(message)
    if result.get("success"):
        console_log("飞书测试消息发送成功")
    else:
        console_log(f"飞书测试失败: {result.get('error')}")
    return jsonify(result)


@app.route('/api/feishu/send', methods=['POST'])
def api_feishu_send():
    """通过飞书发送消息"""
    data = request.json
    text = data.get('text', '')
    msg_type = data.get('msg_type', 'text')
    if not text:
        return jsonify({"error": "消息不能为空"}), 400
    fs = cluster_manager.get_feishu_integration()
    return jsonify(fs.send_message(text, msg_type))


@app.route('/api/feishu/webhook', methods=['POST'])
def api_feishu_webhook():
    """接收飞书事件回调"""
    data = request.json
    fs = cluster_manager.get_feishu_integration()
    parsed = fs.handle_incoming(data)

    # URL验证
    if "challenge" in parsed:
        return jsonify(parsed)

    # 处理消息 — 转发到AGI对话
    text = parsed.get("text", "")
    if text and lattice:
        console_log(f"飞书消息: {text[:60]}")
        # 可以在这里调用AGI对话处理
        # 然后将结果回复到飞书
        try:
            related = lattice.find_similar_nodes(text, threshold=0.4, limit=3)
            reply = f"收到消息: {text}\n找到 {len(related)} 个相关节点"
            fs.send_message(reply)
        except Exception:
            pass

    return jsonify({"success": True})


@app.route('/api/feishu/openclaw', methods=['POST'])
def api_feishu_openclaw():
    """通过OpenClaw转发消息"""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', '')
    if not message:
        return jsonify({"error": "消息不能为空"}), 400
    fs = cluster_manager.get_feishu_integration()
    return jsonify(fs.forward_to_openclaw(message, session_id))


# ==================== 菩提道次第 API ====================

@app.route('/api/bodhi/stages', methods=['GET'])
def api_bodhi_stages():
    """获取完整果位体系"""
    from workspace.skills.bodhi_path import get_all_stages
    return jsonify(get_all_stages())


@app.route('/api/bodhi/assess', methods=['POST'])
def api_bodhi_assess():
    """评估当前能力果位"""
    from workspace.skills.bodhi_path import assess_level
    data = request.json
    capabilities = data.get('capabilities', [])
    if not capabilities:
        return jsonify({"error": "请提供capabilities列表"}), 400
    result = assess_level(capabilities)
    console_log(f"菩提道评估: {result['current_stage']}")
    return jsonify(result)


@app.route('/api/bodhi/path', methods=['GET'])
def api_bodhi_path():
    """获取成长路径"""
    from workspace.skills.bodhi_path import get_growth_path
    level = request.args.get('level', 0, type=int)
    return jsonify(get_growth_path(level))


@app.route('/api/bodhi/activate', methods=['POST'])
def api_bodhi_activate():
    """因问唤醒：根据问题激活proven节点"""
    from workspace.skills.bodhi_path import activate_nodes
    data = request.json
    question = data.get('question', '')
    if not question:
        return jsonify({"error": "请提供question"}), 400
    limit = data.get('limit', 10)
    result = activate_nodes(question, limit)
    console_log(f"因问唤醒: {result['activated_count']}个节点")
    return jsonify(result)


@app.route('/api/bodhi/explore', methods=['POST'])
def api_bodhi_explore():
    """探索无穷层级的无穷"""
    from workspace.skills.bodhi_path import explore_depth
    data = request.json
    content = data.get('content', '')
    if not content:
        return jsonify({"error": "请提供content"}), 400
    depth = data.get('max_depth', 3)
    result = explore_depth(content, depth)
    console_log(f"深度探索: {content[:30]}...")
    return jsonify(result)


# ==================== 智谱API开关 ====================

@app.route('/api/zhipu/switches', methods=['GET', 'POST'])
def api_zhipu_switches():
    """获取/设置智谱API开关"""
    if request.method == 'POST':
        data = request.json or {}
        if 'auto_delegate' in data:
            agi.Config.ZHIPU_AUTO_DELEGATE = bool(data['auto_delegate'])
            console_log(f"智谱自动委托: {'开启' if agi.Config.ZHIPU_AUTO_DELEGATE else '关闭'}")
        if 'growth_enabled' in data:
            agi.Config.ZHIPU_GROWTH_ENABLED = bool(data['growth_enabled'])
            console_log(f"智谱自主成长: {'开启' if agi.Config.ZHIPU_GROWTH_ENABLED else '关闭'}")
            if not agi.Config.ZHIPU_GROWTH_ENABLED:
                try:
                    from workspace.skills.zhipu_growth import stop_background_growth
                    stop_background_growth()
                except Exception: pass
    return jsonify({
        "auto_delegate": agi.Config.ZHIPU_AUTO_DELEGATE,
        "growth_enabled": agi.Config.ZHIPU_GROWTH_ENABLED,
    })


# ==================== 智谱自主成长 API ====================

@app.route('/api/growth/start', methods=['POST'])
def api_growth_start():
    """启动智谱API后台自主成长"""
    if not agi.Config.ZHIPU_GROWTH_ENABLED:
        return jsonify({"error": "智谱自主成长已关闭，请先开启开关"}), 400
    from workspace.skills.zhipu_growth import start_background_growth, check_quota
    data = request.json or {}
    interval = data.get('interval', 120)
    batch_size = data.get('batch_size', 2)
    # 先检查配额
    quota = check_quota()
    if not quota['can_continue']:
        return jsonify({"error": quota['reason']}), 400
    result = start_background_growth(interval, batch_size)
    console_log(f"智谱自主成长启动: 间隔{interval}s, 批量{batch_size}")
    return jsonify(result)


@app.route('/api/growth/stop', methods=['POST'])
def api_growth_stop():
    """停止智谱API后台自主成长"""
    from workspace.skills.zhipu_growth import stop_background_growth
    result = stop_background_growth()
    console_log("智谱自主成长已停止")
    return jsonify(result)


@app.route('/api/growth/status', methods=['GET'])
def api_growth_status():
    """获取自主成长状态"""
    from workspace.skills.zhipu_growth import get_growth_status, is_running, is_turbo_running, check_memory, _load_quota
    status = get_growth_status()
    status["is_running"] = is_running()
    status["turbo_running"] = is_turbo_running()
    status["memory"] = check_memory()
    q = _load_quota()
    status["config"] = {
        "memory_ratio": q.get("memory_ratio", 0.15),
        "batch_size": q.get("batch_size", 2),
        "interval": q.get("interval", 120),
    }
    return jsonify(status)


@app.route('/api/growth/cycle', methods=['POST'])
def api_growth_cycle():
    """手动执行一次成长循环"""
    from workspace.skills.zhipu_growth import run_growth_cycle, check_quota
    data = request.json or {}
    batch_size = data.get('batch_size', 2)
    quota = check_quota()
    if not quota['can_continue']:
        return jsonify({"error": quota['reason']}), 400
    result = run_growth_cycle(batch_size=batch_size, deepen=True)
    console_log(f"成长循环: ✅{result.get('promoted',0)} ❌{result.get('falsified',0)} ❓{result.get('problems',0)}")
    return jsonify(result)


@app.route('/api/growth/quota', methods=['GET', 'POST'])
def api_growth_quota():
    """获取/设置配额"""
    from workspace.skills.zhipu_growth import check_quota, update_quota_limits
    if request.method == 'POST':
        data = request.json or {}
        update_quota_limits(
            daily_limit=data.get('daily_limit'),
            total_limit=data.get('total_limit'),
            max_ratio=data.get('max_ratio'),
            memory_ratio=data.get('memory_ratio'),
            batch_size=data.get('batch_size'),
            interval=data.get('interval'),
        )
        console_log(f"成长配置已更新")
    return jsonify(check_quota())


@app.route('/api/growth/problems', methods=['GET'])
def api_growth_problems():
    """获取无法处理的问题清单"""
    from workspace.skills.zhipu_growth import get_problems
    status = request.args.get('status', 'pending')
    return jsonify(get_problems(status if status != 'all' else None))


@app.route('/api/growth/problems/resolve', methods=['POST'])
def api_growth_problems_resolve():
    """解决/忽略问题"""
    from workspace.skills.zhipu_growth import resolve_problem, dismiss_problem
    data = request.json
    pid = data.get('id', '')
    action = data.get('action', 'resolve')  # resolve / dismiss
    resolution = data.get('resolution', '')
    if action == 'dismiss':
        dismiss_problem(pid)
    else:
        resolve_problem(pid, resolution)
    console_log(f"问题 {pid} 已{action}")
    return jsonify({"success": True})


@app.route('/api/growth/logs', methods=['GET'])
def api_growth_logs():
    """获取成长详细日志"""
    from workspace.skills.zhipu_growth import get_growth_logs
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    return jsonify(get_growth_logs(limit, offset))


@app.route('/api/tokens/usage', methods=['GET'])
def api_tokens_usage():
    """查询tokens消耗统计"""
    from workspace.skills.zhipu_growth import _load_quota, check_memory
    q = _load_quota()
    mem = check_memory()
    return jsonify({
        "daily": {
            "used": q.get("daily_used_tokens", 0),
            "limit": q.get("daily_limit_tokens", 100000000),
            "ratio": round(q.get("daily_used_tokens", 0) / max(q.get("daily_limit_tokens", 1), 1), 6),
            "calls": q.get("daily_calls", 0),
        },
        "total": {
            "used": q.get("total_used_tokens", 0),
            "limit": q.get("total_limit_tokens", 10000000000),
            "ratio": round(q.get("total_used_tokens", 0) / max(q.get("total_limit_tokens", 1), 1), 6),
            "calls": q.get("total_calls", 0),
        },
        "config": {
            "max_usage_ratio": q.get("max_usage_ratio", 0.7),
            "memory_ratio": q.get("memory_ratio", 0.15),
            "batch_size": q.get("batch_size", 2),
            "interval": q.get("interval", 120),
        },
        "memory": mem,
        "last_reset_date": q.get("last_reset_date", ""),
    })


# ==================== Tool Controller API ====================

@app.route('/api/tool/solve', methods=['POST'])
def api_tool_solve():
    """LLM Controller直接调用: 问题→工具调用循环→答案"""
    data = request.json
    question = data.get('question', '').strip()
    if not question:
        return jsonify({"error": "question不能为空"}), 400
    try:
        result = tool_controller.solve(
            question=question,
            max_rounds=int(data.get('max_rounds', 15)),
            model=data.get('model'),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tool/status', methods=['GET'])
def api_tool_status():
    """Tool Controller状态: 注册工具+统计+运行时"""
    return jsonify({
        "tools": tool_controller.get_tools_info(),
        "stats": tool_controller.get_stats(),
    })


@app.route('/api/tool/reset', methods=['POST'])
def api_tool_reset():
    """重置持久化Python运行时"""
    return jsonify(tool_controller.reset_runtime())


# ==================== 健康检查 & 可观测性 (维度40,95) ====================

@app.route('/api/health')
def api_health():
    """健康检查端点 — K8s liveness/readiness probe + Docker HEALTHCHECK"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "13.3",
        "checks": {}
    }
    # DB检查
    try:
        if lattice and lattice.conn:
            lattice.conn.execute("SELECT 1")
            checks["checks"]["database"] = "ok"
        else:
            checks["checks"]["database"] = "not_initialized"
    except Exception as e:
        checks["checks"]["database"] = f"error: {e}"
        checks["status"] = "degraded"

    # Ollama检查
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        checks["checks"]["ollama"] = "ok"
    except Exception:
        checks["checks"]["ollama"] = "unreachable"

    # ToolController检查
    checks["checks"]["tool_controller"] = "ok" if tool_controller._client or True else "not_ready"
    checks["checks"]["orchestrator"] = "ok" if task_orchestrator else "not_initialized"

    # 内存使用
    try:
        import resource
        mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
        checks["memory_mb"] = round(mem_mb, 1)
    except Exception:
        pass

    code = 200 if checks["status"] == "healthy" else 503
    return jsonify(checks), code


@app.route('/api/metrics')
def api_metrics():
    """Prometheus兼容指标端点 (维度95: 监控警报)"""
    try:
        from agi_logger import metrics
        # 更新实时指标
        if lattice:
            stats = lattice.stats()
            metrics.set_gauge("agi_nodes_total", stats.get("total_nodes", 0))
            metrics.set_gauge("agi_proven_nodes", stats.get("proven_nodes", 0))
            metrics.set_gauge("agi_relations_total", stats.get("total_relations", 0))
            metrics.set_gauge("agi_domains_total", stats.get("total_domains", 0))
        tc_stats = tool_controller.get_stats()
        metrics.set_gauge("agi_tool_calls_total", tc_stats.get("total_tool_calls", 0))
        metrics.set_gauge("agi_solve_count", tc_stats.get("total_solves", 0))
        metrics.set_gauge("agi_tool_errors", tc_stats.get("errors", 0))

        return Response(metrics.export_prometheus(), mimetype="text/plain")
    except Exception as e:
        return Response(f"# error: {e}", mimetype="text/plain"), 500


@app.route('/api/openapi.json')
def api_openapi():
    """OpenAPI 3.0 规范文档 (维度28: API设计)"""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "AGI v13.3 Cognitive Lattice API",
            "version": "13.3.0",
            "description": "多模型协同编码AGI系统 REST API",
            "contact": {"name": "AGI Cognitive Lattice"},
        },
        "servers": [{"url": "http://localhost:5002", "description": "Local dev"}],
        "paths": {
            "/api/health": {
                "get": {"summary": "健康检查", "tags": ["System"],
                        "responses": {"200": {"description": "系统健康"}, "503": {"description": "系统降级"}}}
            },
            "/api/stats": {
                "get": {"summary": "认知网络统计", "tags": ["Knowledge"],
                        "responses": {"200": {"description": "统计数据"}}}
            },
            "/api/nodes": {
                "get": {"summary": "节点列表", "tags": ["Knowledge"],
                        "parameters": [
                            {"name": "domain", "in": "query", "schema": {"type": "string"}},
                            {"name": "status", "in": "query", "schema": {"type": "string"}},
                            {"name": "search", "in": "query", "schema": {"type": "string"}},
                            {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                        ],
                        "responses": {"200": {"description": "分页节点列表"}}}
            },
            "/api/chat": {
                "post": {"summary": "对话", "tags": ["Chat"],
                         "requestBody": {"content": {"application/json": {"schema": {
                             "type": "object",
                             "properties": {
                                 "message": {"type": "string", "description": "用户消息"},
                                 "session_id": {"type": "string"},
                                 "mode": {"type": "string", "enum": ["code", "ask", "plan", "tool", "nocollision", "heat", "mobile", "agi", "cross"]},
                             },
                             "required": ["message"]
                         }}}},
                         "responses": {"200": {"description": "对话响应"}}}
            },
            "/api/metrics": {
                "get": {"summary": "Prometheus指标", "tags": ["System"],
                        "responses": {"200": {"description": "Prometheus文本格式指标"}}}
            },
            "/api/search": {
                "post": {"summary": "语义搜索", "tags": ["Knowledge"],
                         "requestBody": {"content": {"application/json": {"schema": {
                             "type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                             "required": ["query"]
                         }}}},
                         "responses": {"200": {"description": "搜索结果"}}}
            },
            "/api/tool/stats": {
                "get": {"summary": "工具控制器统计", "tags": ["Tools"],
                        "responses": {"200": {"description": "工具调用统计"}}}
            },
        },
        "tags": [
            {"name": "System", "description": "系统管理"},
            {"name": "Knowledge", "description": "认知网络"},
            {"name": "Chat", "description": "对话交互"},
            {"name": "Tools", "description": "工具管理"},
        ]
    }
    return jsonify(spec)


@app.route('/box-editor')
def box_editor_page():
    return send_from_directory(app.static_folder, 'box-editor.html')

@app.route('/templates/<path:filename>')
def serve_template(filename):
    return send_from_directory(TEMPLATE_DIR, filename)


# ==================== 启动 ====================
def init_app():
    global lattice, growth_engine, task_orchestrator
    lattice = agi.CognitiveLattice()
    agi.seed_database(lattice)
    _ensure_chat_table()
    growth_engine = agi.SelfGrowthEngine(lattice)
    # 注册步骤广播回调，让双模验证过程可以实时推送SSE到前端
    agi.set_step_callback(broadcast_step)
    # 注入认知格到ToolController，启用语义搜索
    tool_controller.set_lattice(lattice)
    # 初始化 Orchestrator
    task_orchestrator = orch_module.TaskOrchestrator(lattice)
    task_orchestrator.set_broadcast(broadcast_step)
    print("  [API] Orchestrator 已初始化")
    print("  [API] 认知格数据库已加载")
    print(f"  [API] 工作区: {action_engine.WORKSPACE_DIR}")


if __name__ == '__main__':
    init_app()
    # ★ 预热：在Flask启动前初始化所有懒加载模型，避免并发请求导致segfault ★
    print("  [预热] 初始化 Embedding 模型...")
    try:
        agi.Models.embed_model()
        agi.Models.embed_client()
        agi.Models.llm_client()
        # 做一次真实embedding调用来完全预热Ollama连接
        _ = agi.get_embedding("warmup test")
        print("  [预热] ✓ 所有模型已就绪")
    except Exception as e:
        print(f"  [预热] ⚠ 部分模型初始化失败(不影响启动): {e}")
    print("\n" + "=" * 50)
    print("  AGI v13.3 Web API + Action Engine")
    print("  http://localhost:5002")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
