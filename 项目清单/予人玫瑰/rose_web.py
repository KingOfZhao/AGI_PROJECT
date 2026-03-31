#!/usr/bin/env python3
"""
予人玫瑰 CRM Web UI
技术栈: Flask + Jinja2 + 内嵌CSS (零外部依赖)
启动: python3 rose_web.py
访问: http://localhost:5010
"""
import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from rose_crm_v2 import RoseCRM
from staff import StaffManager

try:
    from flask import Flask, request, jsonify, redirect, url_for, render_template_string, abort
except ImportError:
    print("需要安装Flask: pip3 install flask")
    sys.exit(1)

app = Flask(__name__)
crm = RoseCRM()
sm = StaffManager()

# ═══ 内嵌HTML模板 ═══
LAYOUT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{%block title%}🌹 予人玫瑰{%endblock%}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--rose:#e91e63;--rose-light:#fce4ec;--rose-dark:#c2185b;--bg:#faf5f7;--card:#fff;--text:#333;--text2:#888;--border:#f0e0e5;--success:#4caf50;--warning:#ff9800;--danger:#f44336;--info:#2196f3}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
a{color:var(--rose);text-decoration:none}
a:hover{color:var(--rose-dark)}

/* 导航 */
.nav{background:linear-gradient(135deg,var(--rose),var(--rose-dark));color:#fff;padding:0 24px;display:flex;align-items:center;height:56px;box-shadow:0 2px 8px rgba(233,30,99,.3)}
.nav .logo{font-size:20px;font-weight:700;letter-spacing:1px}
.nav .logo span{opacity:.85;font-weight:400;font-size:14px;margin-left:8px}
.nav-links{display:flex;margin-left:40px;gap:4px}
.nav-links a{color:rgba(255,255,255,.85);padding:8px 16px;border-radius:20px;font-size:14px;transition:.2s}
.nav-links a:hover,.nav-links a.active{background:rgba(255,255,255,.2);color:#fff}

/* 布局 */
.container{max-width:1200px;margin:0 auto;padding:20px 24px}

/* 统计卡片 */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:var(--card);border-radius:12px;padding:20px;border:1px solid var(--border);box-shadow:0 1px 3px rgba(0,0,0,.04)}
.stat-card .num{font-size:32px;font-weight:700;color:var(--rose)}
.stat-card .label{font-size:13px;color:var(--text2);margin-top:4px}

/* 看板 */
.board{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.board-col{background:var(--card);border-radius:12px;padding:16px;border:1px solid var(--border);min-height:300px}
.board-col h3{font-size:14px;color:var(--text2);margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid var(--border)}
.board-col h3 .count{background:var(--rose-light);color:var(--rose);padding:2px 8px;border-radius:10px;font-size:12px;margin-left:8px}
.task-card{background:var(--bg);border-radius:8px;padding:12px;margin-bottom:8px;border-left:3px solid var(--border);cursor:pointer;transition:.2s}
.task-card:hover{border-left-color:var(--rose);box-shadow:0 2px 8px rgba(233,30,99,.1)}
.task-card .title{font-size:14px;font-weight:500;margin-bottom:6px}
.task-card .meta{font-size:12px;color:var(--text2)}
.task-card .subtask-bar{height:4px;background:#eee;border-radius:2px;margin-top:8px;overflow:hidden}
.task-card .subtask-fill{height:100%;background:var(--rose);border-radius:2px;transition:.3s}
.priority-critical{border-left-color:var(--danger)!important}
.priority-high{border-left-color:var(--warning)!important}

/* 表格 */
.table-wrap{background:var(--card);border-radius:12px;border:1px solid var(--border);overflow:hidden}
table{width:100%;border-collapse:collapse}
th{background:var(--rose-light);color:var(--rose-dark);font-size:13px;font-weight:600;padding:10px 16px;text-align:left}
td{padding:10px 16px;border-bottom:1px solid var(--border);font-size:14px}
tr:hover td{background:var(--bg)}
.badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500}
.badge-critical{background:#fce4ec;color:#c62828}
.badge-high{background:#fff3e0;color:#e65100}
.badge-medium{background:#e3f2fd;color:#1565c0}
.badge-draft{background:#f5f5f5;color:#666}
.badge-active{background:#e8f5e9;color:#2e7d32}
.badge-pending{background:#fff3e0;color:#e65100}
.badge-planning{background:#e3f2fd;color:#1565c0}
.badge-execution{background:#fce4ec;color:#c62828}

/* 表单 */
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:13px;font-weight:600;color:var(--text2);margin-bottom:4px}
input,select,textarea{width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px;font-family:inherit;transition:.2s}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--rose);box-shadow:0 0 0 3px rgba(233,30,99,.1)}
textarea{resize:vertical;min-height:80px}
.btn{display:inline-block;padding:10px 20px;border:none;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;transition:.2s}
.btn-primary{background:var(--rose);color:#fff}
.btn-primary:hover{background:var(--rose-dark)}
.btn-secondary{background:var(--bg);color:var(--text);border:1px solid var(--border)}
.btn-secondary:hover{border-color:var(--rose);color:var(--rose)}
.btn-sm{padding:6px 12px;font-size:12px}
.btn-danger{background:#ffebee;color:var(--danger)}

/* 模态框 */
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:100}
.modal{background:var(--card);border-radius:16px;padding:24px;width:90%;max-width:500px;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.2)}
.modal h2{font-size:18px;margin-bottom:16px;color:var(--rose)}
.modal .actions{display:flex;gap:8px;margin-top:16px;justify-content:flex-end}

/* 内容卡片 */
.content-card{background:var(--card);border-radius:12px;padding:16px;border:1px solid var(--border);margin-bottom:12px}
.content-card h3{font-size:16px;margin-bottom:6px}
.content-card .meta{font-size:12px;color:var(--text2);margin-bottom:8px}
.content-card .preview{font-size:14px;color:var(--text);line-height:1.7}

/* 项目卡片 */
.project-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.project-card{background:var(--card);border-radius:12px;padding:20px;border:1px solid var(--border);transition:.2s}
.project-card:hover{box-shadow:0 4px 12px rgba(233,30,99,.1)}
.project-card h3{font-size:16px;margin-bottom:8px}
.project-card .desc{font-size:13px;color:var(--text2);margin-bottom:12px}
.progress-bar{height:6px;background:#eee;border-radius:3px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--rose),var(--rose-dark));border-radius:3px;transition:.3s}
.milestones{margin-top:12px}
.milestone{display:flex;align-items:center;gap:8px;font-size:13px;padding:4px 0}
.milestone .icon{font-size:16px}

/* 快捷操作 */
.quick-actions{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}

/* 响应式 */
@media(max-width:768px){
  .board{grid-template-columns:1fr 1fr}
  .nav-links{display:none}
  .stats{grid-template-columns:1fr 1fr}
}
@media(max-width:480px){
  .board{grid-template-columns:1fr}
  .stats{grid-template-columns:1fr}
}

.empty{text-align:center;padding:40px;color:var(--text2);font-size:14px}
.empty .icon{font-size:40px;margin-bottom:12px}
.tag{display:inline-block;padding:2px 8px;background:var(--rose-light);color:var(--rose);border-radius:4px;font-size:11px;margin:0 2px}
</style>
</head>
<body>
<nav class="nav">
  <div class="logo">🌹 予人玫瑰<span>CRM</span></div>
  <div class="nav-links">
    <a href="/" class="{{'active' if page=='dashboard' else ''}}">仪表盘</a>
    <a href="/projects" class="{{'active' if page=='projects' else ''}}">项目</a>
    <a href="/board" class="{{'active' if page=='board' else ''}}">看板</a>
    <a href="/content" class="{{'active' if page=='content' else ''}}">内容</a>
    <a href="/assets" class="{{'active' if page=='assets' else ''}}">品牌</a>
    <a href="/suppliers" class="{{'active' if page=='suppliers' else ''}}">供应商</a>
    <a href="/campaigns" class="{{'active' if page=='campaigns' else ''}}">活动</a>
    <a href="/team" class="{{'active' if page=='team' else ''}}">👥 团队</a>
  </div>
</nav>
<div class="container">
{%block content%}{%endblock%}
</div>
</body>
</html>"""

DASHBOARD_TPL = """{%extends "layout"%}{%block title%}仪表盘 - 予人玫瑰{%endblock%}{%block content%}
<h2 style="margin-bottom:20px">🌹 欢迎回来</h2>

<div class="stats">
  <div class="stat-card"><div class="num">{{stats.projects.get('active',0)}}</div><div class="label">活跃项目</div></div>
  <div class="stat-card"><div class="num">{{stats.board.get('todo',0)}}</div><div class="label">待办任务</div></div>
  <div class="stat-card"><div class="num">{{stats.board.get('in_progress',0)}}</div><div class="label">进行中</div></div>
  <div class="stat-card"><div class="num">{{stats.board.get('done',0)}}</div><div class="label">已完成</div></div>
  <div class="stat-card"><div class="num">{{stats.content.get('draft',0)}}</div><div class="label">内容草稿</div></div>
  <div class="stat-card"><div class="num">{{stats.milestones.get('pending',0)}}</div><div class="label">待完成里程碑</div></div>
</div>

<div class="quick-actions">
  <a href="/task/new" class="btn btn-primary">+ 新任务</a>
  <a href="/article/new" class="btn btn-secondary">+ 新文章</a>
  <a href="/project/new" class="btn btn-secondary">+ 新项目</a>
</div>

<h3 style="margin-bottom:12px">🔥 最近任务</h3>
<div class="table-wrap">
<table>
<tr><th>ID</th><th>标题</th><th>状态</th><th>优先级</th><th>更新时间</th></tr>
{%for t in stats.recent_tasks[:10]%}
<tr>
  <td>#{{t.id}}</td>
  <td><a href="/task/{{t.id}}">{{t.title}}</a></td>
  <td><span class="badge badge-{{t.status}}">{{t.status}}</span></td>
  <td>{{t.priority}}</td>
  <td>{{(t.updated_at or '')[:16]}}</td>
</tr>
{%endfor%}
{%if not stats.recent_tasks%}<tr><td colspan="5" class="empty">暂无任务</td></tr>{%endif%}
</table>
</div>
{%endblock%}"""

BOARD_TPL = """{%extends "layout"%}{%block title%}看板 - 予人玫瑰{%endblock%}{%block content%}
<div class="quick-actions">
  <a href="/task/new" class="btn btn-primary">+ 新任务</a>
  <a href="/template/list" class="btn btn-secondary">📋 从模板创建</a>
</div>
<div class="board">
{%for col_key, col_name, col_icon in [('todo','待办','📋'),('in_progress','进行中','🔄'),('review','审核','👁'),('done','完成','✅')]%}
<div class="board-col">
  <h3>{{col_icon}} {{col_name}} <span class="count">{{board[col_key]|length}}</span></h3>
  {%for t in board[col_key]%}
  <div class="task-card priority-{{t.priority}}" onclick="location.href='/task/{{t.id}}'">
    <div class="title">#{{t.id}} {{t.title}}</div>
    <div class="meta">
      {%if t.customer_name%}👤 {{t.customer_name}}{%endif%}
      {%if t.subtasks%}{{t.subtasks|selectattr('status','equalto','completed')|list|length}}/{{t.subtasks|length}} 子任务{%endif%}
    </div>
    {%if t.subtasks%}
    {%set done = t.subtasks|selectattr('status','equalto','completed')|list|length%}
    {%set total = t.subtasks|length%}
    <div class="subtask-bar"><div class="subtask-fill" style="width:{{(done/total*100)|int}}%"></div></div>
    {%endif%}
  </div>
  {%endfor%}
</div>
{%endfor%}
</div>
{%endblock%}"""

PROJECTS_TPL = """{%extends "layout"%}{%block title%}项目 - 予人玫瑰{%endblock%}{%block content%}
<div class="quick-actions">
  <a href="/project/new" class="btn btn-primary">+ 新项目</a>
</div>
<div class="project-grid">
{%for p in projects%}
<div class="project-card">
  <h3>{{p.name}}</h3>
  <div class="desc">{{p.description or ''}}</div>
  <div style="display:flex;gap:8px;margin-bottom:8px">
    <span class="badge badge-{{p.phase}}">{{p.phase}}</span>
    <span class="badge badge-{{p.priority}}">{{p.priority}}</span>
  </div>
  <div style="font-size:13px;color:var(--text2);margin-bottom:8px">进度 {{p.progress_pct or 0}}%</div>
  <div class="progress-bar"><div class="progress-fill" style="width:{{p.progress_pct or 0}}%"></div></div>
  <div class="milestones">
  {%for m in p.milestones%}
    <div class="milestone">
      <span class="icon">{{'✅' if m.status=='completed' else '⬜'}}</span>
      <span>{{m.title}}</span>
    </div>
  {%endfor%}
  </div>
  <div style="margin-top:12px">
    <a href="/project/{{p.id}}" class="btn btn-sm btn-secondary">查看详情</a>
  </div>
</div>
{%endfor%}
</div>
{%endblock%}"""

TASK_TPL = """{%extends "layout"%}{%block title%}任务 #{{task.id}} - 予人玫瑰{%endblock%}{%block content%}
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
  <h2>#{{task.id}} {{task.title}}</h2>
  <span class="badge badge-{{task.priority}}">{{task.priority}}</span>
  <span class="badge badge-{{task.status}}">{{task.status}}</span>
</div>

<div style="display:grid;grid-template-columns:1fr 300px;gap:20px">
<div>
  <div class="content-card">
    <h3>📝 描述</h3>
    <p>{{task.description or '暂无描述'}}</p>
  </div>

  <h3 style="margin:16px 0 12px">📋 子任务 ({{subtasks|length}})</h3>
  {%for s in subtasks%}
  <div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--card);border-radius:8px;margin-bottom:4px;border:1px solid var(--border)">
    <form method="POST" action="/subtask/toggle" style="display:inline">
      <input type="hidden" name="task_id" value="{{task.id}}">
      <input type="hidden" name="subtask_id" value="{{s.id}}">
      <button type="submit" style="font-size:18px;cursor:pointer;border:none;background:none">{{'✅' if s.status=='completed' else '⬜'}}</button>
    </form>
    <span style="flex:1;{{'text-decoration:line-through;opacity:.5' if s.status=='completed' else ''}}">{{s.title}}</span>
    <form method="POST" action="/subtask/delete" style="display:inline">
      <input type="hidden" name="task_id" value="{{task.id}}">
      <input type="hidden" name="subtask_id" value="{{s.id}}">
      <button type="submit" class="btn btn-sm btn-danger">✕</button>
    </form>
  </div>
  {%endfor%}

  <form method="POST" action="/subtask/add" style="margin-top:8px;display:flex;gap:8px">
    <input type="hidden" name="task_id" value="{{task.id}}">
    <input type="text" name="title" placeholder="添加子任务..." required style="flex:1">
    <button type="submit" class="btn btn-primary btn-sm">添加</button>
  </form>
</div>

<div>
  <div class="content-card">
    <h3>📊 状态</h3>
    <form method="POST" action="/task/move">
      <input type="hidden" name="task_id" value="{{task.id}}">
      <select name="column" style="margin-bottom:8px">
        <option value="todo" {{'selected' if task.board_column=='todo'}}>📋 待办</option>
        <option value="in_progress" {{'selected' if task.board_column=='in_progress'}}>🔄 进行中</option>
        <option value="review" {{'selected' if task.board_column=='review'}}>👁 审核</option>
        <option value="done" {{'selected' if task.board_column=='done'}}>✅ 完成</option>
      </select>
      <button type="submit" class="btn btn-primary btn-sm" style="width:100%">移动</button>
    </form>
  </div>
</div>
</div>
{%endblock%}"""

CONTENT_TPL = """{%extends "layout"%}{%block title%}内容管理 - 予人玫瑰{%endblock%}{%block content%}
<div class="quick-actions">
  <a href="/article/new" class="btn btn-primary">+ 新文章</a>
</div>
<div class="table-wrap">
<table>
<tr><th>ID</th><th>标题</th><th>平台</th><th>状态</th><th>标签</th><th>创建时间</th></tr>
{%for a in articles%}
<tr>
  <td>#{{a.id}}</td>
  <td><a href="/article/{{a.id}}">{{a.title}}</a></td>
  <td>{{a.platform}}</td>
  <td><span class="badge badge-{{a.status}}">{{a.status}}</span></td>
  <td>{%if a.tags%}{%for tag in a.tags%}<span class="tag">{{tag}}</span>{%endfor%}{%endif%}</td>
  <td>{{(a.created_at or '')[:16]}}</td>
</tr>
{%endfor%}
{%if not articles%}<tr><td colspan="6" class="empty">暂无文章</td></tr>{%endif%}
</table>
</div>
{%endblock%}"""

FORM_TPL = """{%extends "layout"%}{%block title%}{{form_title}} - 予人玫瑰{%endblock%}{%block content%}
<h2>{{form_title}}</h2>
<div class="content-card" style="max-width:600px">
<form method="POST" action="{{form_action}}">
{%for field in form_fields%}
<div class="form-group">
  <label>{{field.label}}</label>
  {%if field.type=='textarea'%}
  <textarea name="{{field.name}}" rows="5" {{'required' if field.required}}>{{field.value or ''}}</textarea>
  {%elif field.type=='select'%}
  <select name="{{field.name}}">
  {%for opt in field.options%}
    <option value="{{opt[0]}}" {{'selected' if opt[0]==field.value}}>{{opt[1]}}</option>
  {%endfor%}
  </select>
  {%else%}
  <input type="{{field.type or 'text'}}" name="{{field.name}}" value="{{field.value or ''}}" {{'required' if field.required}}>
  {%endif%}
</div>
{%endfor%}
<div class="actions">
  <button type="submit" class="btn btn-primary">保存</button>
  <a href="{{cancel_url or '/'}}" class="btn btn-secondary">取消</a>
</div>
</form>
</div>
{%endblock%}"""

# ═══ 路由 ═══

def render_page(page_name, content_html, title=None, **context):
    """Render a full page - strips extends/block from child, injects into layout"""
    import re
    child = content_html
    m = re.search(r'\{%block title%\}(.*?)\{%endblock%\}', child, re.DOTALL)
    page_title = m.group(1).strip() if m else (title or '予人玫瑰')
    child = re.sub(r'\{%extends "layout"%\}', '', child)
    child = re.sub(r'\{%block title%\}.*?\{%endblock%\}', '', child, flags=re.DOTALL)
    child = re.sub(r'\{%block content%\}(.*?)\{%endblock%\}', r'\1', child, flags=re.DOTALL)
    full = LAYOUT.replace("{%block title%}🌹 予人玫瑰{%endblock%}", page_title)
    full = full.replace("{%block content%}{%endblock%}", child)
    context['page'] = page_name
    return render_template_string(full, **context)

@app.route("/")
def dashboard():
    stats = crm.dashboard()
    return render_page("dashboard", DASHBOARD_TPL, stats=stats)

@app.route("/board")
def board():
    b = crm.get_board()
    return render_page("board", BOARD_TPL, board=b)

@app.route("/projects")
def projects():
    projs = crm.list_projects()
    for p in projs:
        p['milestones'] = crm.list_milestones(p['id'])
    return render_page("projects", PROJECTS_TPL, projects=projs)

@app.route("/project/<int:pid>")
def project_detail(pid):
    p = crm.get_project(pid)
    if not p: abort(404)
    p['milestones'] = crm.list_milestones(pid)
    from rose_crm import CRMDatabase
    db = CRMDatabase()
    tasks = db.list_tasks(limit=100)
    p['tasks'] = [t for t in tasks if t.get('project_id') == pid]
    return render_page("projects", PROJECTS_TPL, projects=[p])

@app.route("/content")
def content():
    articles = crm.list_articles(limit=50)
    for a in articles:
        try: a['tags'] = json.loads(a.get('tags','[]'))
        except: a['tags'] = []
    return render_page("content", CONTENT_TPL, articles=articles)

@app.route("/assets")
def assets():
    assets = crm.list_assets()
    return render_page("assets", """
    {%extends "layout"%}{%block title%}品牌资产 - 予人玫瑰{%endblock%}{%block content%}
    <div class="quick-actions"><a href="/asset/new" class="btn btn-primary">+ 新资产</a></div>
    <div class="table-wrap"><table>
    <tr><th>ID</th><th>类型</th><th>名称</th><th>版本</th><th>状态</th></tr>
    {%for a in assets%}
    <tr><td>#{{a.id}}</td><td>{{a.type}}</td><td>{{a.name}}</td><td>{{a.version}}</td>
    <td><span class="badge badge-{{a.status}}">{{a.status}}</span></td></tr>
    {%endfor%}
    </table></div>
    {%endblock%}""")

@app.route("/suppliers")
def suppliers():
    sups = crm.list_suppliers()
    return render_page("suppliers", """
    {%extends "layout"%}{%block title%}供应商 - 予人玫瑰{%endblock%}{%block content%}
    <div class="quick-actions"><a href="/supplier/new" class="btn btn-primary">+ 新供应商</a></div>
    <div class="table-wrap"><table>
    <tr><th>ID</th><th>名称</th><th>分类</th><th>联系人</th><th>电话</th></tr>
    {%for s in sups%}
    <tr><td>#{{s.id}}</td><td>{{s.name}}</td><td>{{s.category or '-'}}</td><td>{{s.contact_person or '-'}}</td><td>{{s.phone or '-'}}</td></tr>
    {%endfor%}
    </table></div>
    {%endblock%}""")

@app.route("/campaigns")
def campaigns():
    camps = crm.list_campaigns()
    return render_page("campaigns", """
    {%extends "layout"%}{%block title%}传播活动 - 予人玫瑰{%endblock%}{%block content%}
    <div class="quick-actions"><a href="/campaign/new" class="btn btn-primary">+ 新活动</a></div>
    <div class="table-wrap"><table>
    <tr><th>ID</th><th>名称</th><th>类型</th><th>状态</th><th>预算</th></tr>
    {%for c in camps%}
    <tr><td>#{{c.id}}</td><td>{{c.name}}</td><td>{{c.type or '-'}}</td>
    <td><span class="badge badge-{{c.status}}">{{c.status}}</span></td><td>{{c.budget or '-'}}</td></tr>
    {%endfor%}
    </table></div>
    {%endblock%}""")

@app.route("/task/<int:tid>")
def task_detail(tid):
    from rose_crm import CRMDatabase
    db = CRMDatabase()
    task = db.get_task(tid)
    if not task: abort(404)
    task['subtasks'] = crm.list_subtasks(tid)
    task['board_column'] = task.get('board_column', 'todo')
    return render_page("board", TASK_TPL, task=task, subtasks=task['subtasks'])

# ═══ 通用表单路由 ═══

def render_form(title, action, fields, cancel_url="/"):
    return render_page("form", FORM_TPL,
        page="form", form_title=title, form_action=action, form_fields=fields, cancel_url=cancel_url)

@app.route("/task/new", methods=["GET","POST"])
def new_task():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('title',) and v}
        if 'project_id' in kw: kw['project_id'] = int(kw['project_id'])
        tid = crm.create_task(request.form['title'], **kw)
        return redirect(f"/task/{tid}")
    return render_form("新任务", "/task/new", [
        {"name":"title","label":"标题","required":True},
        {"name":"description","label":"描述","type":"textarea"},
        {"name":"priority","label":"优先级","type":"select","options":[("low","低"),("medium","中"),("high","高"),("critical","紧急")]},
        {"name":"project_id","label":"项目ID","type":"number"},
    ])

@app.route("/project/new", methods=["GET","POST"])
def new_project():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('name',) and v}
        if 'progress_pct' in kw: kw['progress_pct'] = int(kw['progress_pct'])
        pid = crm.create_project(request.form['name'], **kw)
        return redirect(f"/project/{pid}")
    return render_form("新项目", "/project/new", [
        {"name":"name","label":"项目名称","required":True},
        {"name":"description","label":"描述","type":"textarea"},
        {"name":"phase","label":"阶段","type":"select","options":[("planning","规划"),("execution","执行"),("review","审核"),("completed","完成")]},
        {"name":"priority","label":"优先级","type":"select","options":[("low","低"),("medium","中"),("high","高"),("critical","紧急")]},
    ])

@app.route("/article/new", methods=["GET","POST"])
def new_article():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('title',) and v}
        aid = crm.create_article(request.form['title'], **kw)
        return redirect(f"/content")
    return render_form("新文章", "/article/new", [
        {"name":"title","label":"标题","required":True},
        {"name":"content","label":"内容","type":"textarea"},
        {"name":"platform","label":"平台","type":"select","options":[("wechat","公众号"),("xiaohongshu","小红书"),("weibo","微博"),("douyin","抖音")]},
        {"name":"status","label":"状态","type":"select","options":[("draft","草稿"),("review","审核中"),("published","已发布")]},
        {"name":"tags","label":"标签(逗号分隔)","type":"text"},
    ])

@app.route("/article/<int:aid>")
def article_detail(aid):
    a = crm.list_articles(limit=1000)
    article = next((x for x in a if x['id'] == aid), None)
    if not article: abort(404)
    try: article['tags'] = json.loads(article.get('tags','[]'))
    except: article['tags'] = []
    return render_page("content", """
    {%extends "layout"%}{%block title%}{{article.title}} - 予人玫瑰{%endblock%}{%block content%}
    <div class="content-card">
      <h2>{{article.title}}</h2>
      <div class="meta">{{article.platform}} · {{article.status}} · {{(article.created_at or '')[:16]}}
      {%for tag in article.tags%}<span class="tag">{{tag}}</span>{%endfor%}
      </div>
      <div class="preview">{{(article.content or '暂无内容')|replace('\\n','<br>')}}</div>
    </div>
    <a href="/content" class="btn btn-secondary" style="margin-top:12px">← 返回列表</a>
    {%endblock%}""")

@app.route("/asset/new", methods=["GET","POST"])
def new_asset():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('name','type',) and v}
        crm.create_asset(request.form['type'], request.form['name'], **kw)
        return redirect("/assets")
    return render_form("新品牌资产", "/asset/new", [
        {"name":"name","label":"名称","required":True},
        {"name":"type","label":"类型","type":"select","options":[("logo","Logo"),("color","色板"),("font","字体"),("image","图片"),("template","模板"),("document","文档")]},
        {"name":"version","label":"版本"},
        {"name":"status","label":"状态","type":"select","options":[("draft","草稿"),("review","审核中"),("final","定稿")]},
        {"name":"notes","label":"备注","type":"textarea"},
    ])

@app.route("/supplier/new", methods=["GET","POST"])
def new_supplier():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('name',) and v}
        crm.create_supplier(request.form['name'], **kw)
        return redirect("/suppliers")
    return render_form("新供应商", "/supplier/new", [
        {"name":"name","label":"名称","required":True},
        {"name":"category","label":"分类","type":"select","options":[("设计","设计"),("印刷","印刷"),("包装","包装"),("开发","开发"),("物流","物流"),("广告","广告"),("法务","法务"),("财务","财务")]},
        {"name":"contact_person","label":"联系人"},
        {"name":"phone","label":"电话"},
        {"name":"email","label":"邮箱"},
        {"name":"notes","label":"备注","type":"textarea"},
    ])

@app.route("/campaign/new", methods=["GET","POST"])
def new_campaign():
    if request.method == "POST":
        kw = {k: v for k, v in request.form.items() if k not in ('name',) and v}
        crm.create_campaign(request.form['name'], **kw)
        return redirect("/campaigns")
    return render_form("新传播活动", "/campaign/new", [
        {"name":"name","label":"活动名称","required":True},
        {"name":"type","label":"类型","type":"select","options":[("viral","病毒传播"),("charity","公益活动"),("product","产品推广"),("brand","品牌宣传")]},
        {"name":"description","label":"描述","type":"textarea"},
        {"name":"budget","label":"预算","type":"number"},
        {"name":"start_date","label":"开始日期","type":"date"},
        {"name":"end_date","label":"结束日期","type":"date"},
    ])

@app.route("/template/list")
def template_list():
    ts = crm.list_templates()
    return render_page("board", """
    {%extends "layout"%}{%block title%}任务模板 - 予人玫瑰{%endblock%}{%block content%}
    <h2 style="margin-bottom:16px">📋 任务模板</h2>
    <div class="project-grid">
    {%for t in templates%}
    <div class="project-card">
      <h3>{{t.name}}</h3>
      <div class="desc">{{t.description or ''}} · {{t.category}}</div>
      <div class="milestones">
      {%for s in t.subtasks%}
        <div class="milestone"><span class="icon">⬜</span><span>{{s}}</span></div>
      {%endfor%}
      </div>
      <form method="POST" action="/template/apply" style="margin-top:12px">
        <input type="hidden" name="template_id" value="{{t.id}}">
        <button type="submit" class="btn btn-primary btn-sm">应用此模板</button>
      </form>
    </div>
    {%endfor%}
    </div>
    {%endblock%}""", templates=[{**t, "subtasks": json.loads(t.get("subtasks_json","[]"))} for t in ts])

# ═══ POST操作 ═══

@app.route("/task/move", methods=["POST"])
def task_move():
    crm.move_task(int(request.form['task_id']), request.form['column'])
    return redirect(f"/task/{request.form['task_id']}")

@app.route("/subtask/toggle", methods=["POST"])
def subtask_toggle():
    crm.toggle_subtask(int(request.form['subtask_id']))
    return redirect(f"/task/{request.form['task_id']}")

@app.route("/subtask/add", methods=["POST"])
def subtask_add():
    crm.add_subtask(int(request.form['task_id']), request.form['title'])
    return redirect(f"/task/{request.form['task_id']}")

@app.route("/subtask/delete", methods=["POST"])
def subtask_delete():
    c = crm._conn()
    c.execute("DELETE FROM subtasks WHERE id=?", (int(request.form['subtask_id']),))
    c.commit(); c.close()
    return redirect(f"/task/{request.form['task_id']}")

@app.route("/template/apply", methods=["POST"])
def template_apply():
    tid = crm.apply_template(int(request.form['template_id']))
    return redirect(f"/task/{tid}")

# ═══ 团队 ═══

@app.route("/team")
def team():
    staff_list = sm.list_staff()
    from rose_crm import CRMDatabase
    db = CRMDatabase()
    all_tasks = db.list_tasks(limit=200)
    for s in staff_list:
        s['tasks'] = [t for t in all_tasks if t.get('assigned_to') == s['name']]
        for t in s['tasks']:
            t['subtasks'] = crm.list_subtasks(t['id'])
            done = sum(1 for st in t['subtasks'] if st['status'] == 'completed')
            t['done'] = done
            t['total'] = len(t['subtasks'])
    return render_page("team", """
    <h2 style="margin-bottom:20px">👥 予人玫瑰团队</h2>
    <div class="project-grid">
    {%for s in staff%}
    <div class="project-card" style="border-top:3px solid var(--rose)">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <span style="font-size:36px">{{s.avatar}}</span>
        <div>
          <h3 style="margin:0">{{s.name}}</h3>
          <div style="font-size:13px;color:var(--text2)">{{s.role}} · {{s.department}}</div>
        </div>
      </div>
      <div style="font-size:13px;line-height:1.7;margin-bottom:12px;color:var(--text)">{{s.bio}}</div>
      <div style="margin-bottom:8px">
      {%for skill in s.skills[:6]%}
        <span class="tag">{{skill}}</span>
      {%endfor%}
      </div>
      {%if s.tasks%}
      <h4 style="font-size:13px;margin:12px 0 8px">📋 当前任务 ({{s.tasks|length}})</h4>
      {%for t in s.tasks%}
      <div style="background:var(--bg);border-radius:8px;padding:10px;margin-bottom:6px;border-left:3px solid {%if t.priority=='critical'%}var(--danger){%else%}var(--rose){%endif%}">
        <div style="font-size:13px;font-weight:500">{{t.title}}</div>
        <div style="font-size:11px;color:var(--text2)">
          {%if t.subtasks%}{{t.done}}/{{t.total}} 子任务{%else%}{{t.status}}{%endif%}
          · {{t.priority}}
        </div>
        {%if t.subtasks and t.total > 0%}
        <div class="subtask-bar" style="margin-top:6px"><div class="subtask-fill" style="width:{{(t.done/t.total*100)|int}}%"></div></div>
        {%endif%}
      </div>
      {%endfor%}
      {%else%}
      <div style="color:var(--text2);font-size:13px">暂无分配任务</div>
      {%endif%}
    </div>
    {%endfor%}
    </div>
    """, staff=staff_list)

# ═══ API (给AI调用) ═══

@app.route("/api/<path:path>")
def api(path):
    if path == "stats":
        return jsonify(crm.dashboard())
    elif path == "board":
        return jsonify(crm.get_board())
    return jsonify({"error":"not found"}), 404

if __name__ == "__main__":
    print("🌹 予人玫瑰 CRM Web UI")
    print("   http://localhost:5010")
    app.run(host="0.0.0.0", port=5010, debug=True)
