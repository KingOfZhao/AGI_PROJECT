#!/usr/bin/env python3
"""
推演数据库引擎 — ULDS v2.1 极致推演计划管理
存储: 推演计划/过程/结果/报告/阻塞问题

Shell安全: 所有生成的命令经过安全检查, 禁止未闭合引号/括号/heredoc
模型: GLM-5 / GLM-5 Turbo / GLM-4.7 / Ollama 本地
"""

import sqlite3
import json
import os
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "deduction.db")

# ==================== Shell 安全检查 ====================

SHELL_DANGER_PATTERNS = [
    (r'(?<![\\])"([^"\\]|\\.)*$', 'dquote: 双引号未闭合'),
    (r"(?<![\\])'([^'\\]|\\.)*$", 'quote: 单引号未闭合'),
    (r'(?<![\\])`([^`\\]|\\.)*$', 'backtick: 反引号未闭合'),
    (r'\(\s*$', 'paren: 括号未闭合'),
    (r'\{\s*$', 'brace: 花括号未闭合'),
    (r'\|\s*$', 'pipe: 管道续行'),
    (r'<<\s*(\w+).*(?!\1)$', 'heredoc: Here-Document未结束'),
]

def check_shell_safety(cmd: str) -> Tuple[bool, str]:
    """检查shell命令安全性, 返回 (is_safe, reason)"""
    if not cmd or not cmd.strip():
        return True, "empty"
    for line in cmd.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        for pattern, reason in SHELL_DANGER_PATTERNS:
            if re.search(pattern, line):
                return False, f"SHELL_UNSAFE: {reason} in: {line[:80]}"
    return True, "safe"


# ==================== 数据库 Schema ====================

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#6366f1',
    status TEXT DEFAULT 'active',
    progress INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]',
    ultimate_goal TEXT,
    short_term_goal TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deduction_plans (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'queued',
    ulds_laws TEXT,
    surpass_strategies TEXT,
    target_metrics TEXT,
    estimated_rounds INTEGER DEFAULT 5,
    model_preference TEXT DEFAULT 'glm5',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS deduction_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    phase TEXT,
    prompt TEXT,
    response TEXT,
    model_used TEXT,
    tokens_used INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0,
    shell_cmd TEXT,
    shell_safe INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES deduction_plans(id)
);

CREATE TABLE IF NOT EXISTS deduction_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    result_type TEXT,
    content TEXT,
    code_generated TEXT,
    tests_passed INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    truth_level TEXT DEFAULT 'L0',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES deduction_plans(id)
);

CREATE TABLE IF NOT EXISTS deduction_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT,
    project_id TEXT,
    report_type TEXT DEFAULT 'round',
    title TEXT,
    content TEXT,
    metrics TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blocked_problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    suggested_solution TEXT,
    user_solution TEXT,
    alt_ai_used TEXT,
    spawned_plan_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS deduction_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    step_id INTEGER,
    node_type TEXT DEFAULT 'concept',
    name TEXT NOT NULL,
    content TEXT,
    ulds_laws TEXT,
    confidence REAL DEFAULT 0,
    truth_level TEXT DEFAULT 'L0',
    parent_node_id INTEGER,
    relations TEXT DEFAULT '[]',
    skill_generated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES deduction_plans(id)
);

CREATE TABLE IF NOT EXISTS queue_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    priority_project TEXT,
    new_problems_position TEXT DEFAULT 'append',
    auto_expand INTEGER DEFAULT 1,
    max_expand_per_plan INTEGER DEFAULT 3,
    deduction_order TEXT DEFAULT 'priority',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_url TEXT,
    model_id TEXT,
    role TEXT,
    max_tokens INTEGER DEFAULT 4096,
    temperature REAL DEFAULT 0.7,
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 5
);

CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_id TEXT,
    description TEXT,
    steps TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS task_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    user_id TEXT,
    content TEXT,
    rating INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

class DeductionDB:
    """推演数据库管理器"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- Projects ----
    def upsert_project(self, proj: dict):
        self.conn.execute("""
            INSERT INTO projects (id,name,description,color,status,progress,tags,ultimate_goal,short_term_goal)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, description=excluded.description,
                color=excluded.color, status=excluded.status,
                progress=excluded.progress, tags=excluded.tags,
                ultimate_goal=excluded.ultimate_goal,
                short_term_goal=excluded.short_term_goal,
                updated_at=CURRENT_TIMESTAMP
        """, (proj['id'], proj['name'], proj.get('description',''),
              proj.get('color','#6366f1'), proj.get('status','active'),
              proj.get('progress',0), json.dumps(proj.get('tags',[])),
              proj.get('ultimate_goal',''), proj.get('short_term_goal','')))
        self.conn.commit()

    def get_projects(self) -> List[dict]:
        rows = self.conn.execute("SELECT * FROM projects ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    # ---- Deduction Plans ----
    def add_plan(self, plan: dict) -> str:
        pid = plan.get('id', f"dp_{int(time.time()*1000)}_{hashlib.md5(plan['title'].encode()).hexdigest()[:6]}")
        self.conn.execute("""
            INSERT OR REPLACE INTO deduction_plans
            (id,project_id,title,description,priority,status,ulds_laws,surpass_strategies,target_metrics,estimated_rounds,model_preference)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (pid, plan['project_id'], plan['title'], plan.get('description',''),
              plan.get('priority','medium'), plan.get('status','queued'),
              plan.get('ulds_laws',''), plan.get('surpass_strategies',''),
              json.dumps(plan.get('target_metrics',{})),
              plan.get('estimated_rounds',5), plan.get('model_preference','glm5')))
        self.conn.commit()
        return pid

    def get_plans(self, project_id=None, status=None) -> List[dict]:
        sql = "SELECT * FROM deduction_plans WHERE 1=1"
        params = []
        if project_id:
            sql += " AND project_id=?"
            params.append(project_id)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def update_plan_status(self, plan_id: str, status: str):
        now = datetime.now().isoformat()
        extra = ""
        if status == 'running': extra = ", started_at=?"
        elif status in ('done','failed'): extra = ", completed_at=?"
        sql = f"UPDATE deduction_plans SET status=?, updated_at=CURRENT_TIMESTAMP{extra} WHERE id=?"
        params = [status]
        if extra: params.append(now)
        params.append(plan_id)
        self.conn.execute(sql, params)
        self.conn.commit()

    # ---- Steps ----
    def add_step(self, step: dict) -> int:
        safe, reason = check_shell_safety(step.get('shell_cmd',''))
        cur = self.conn.execute("""
            INSERT INTO deduction_steps (plan_id,step_number,phase,prompt,response,model_used,tokens_used,latency_ms,confidence,shell_cmd,shell_safe)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (step['plan_id'], step.get('step_number',0), step.get('phase',''),
              step.get('prompt',''), step.get('response',''),
              step.get('model_used',''), step.get('tokens_used',0),
              step.get('latency_ms',0), step.get('confidence',0),
              step.get('shell_cmd',''), 1 if safe else 0))
        self.conn.commit()
        return cur.lastrowid

    def get_steps(self, plan_id: str) -> List[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM deduction_steps WHERE plan_id=? ORDER BY step_number", (plan_id,)).fetchall()]

    # ---- Results ----
    def add_result(self, result: dict) -> int:
        cur = self.conn.execute("""
            INSERT INTO deduction_results (plan_id,result_type,content,code_generated,tests_passed,tests_total,truth_level)
            VALUES (?,?,?,?,?,?,?)
        """, (result['plan_id'], result.get('result_type',''),
              result.get('content',''), result.get('code_generated',''),
              result.get('tests_passed',0), result.get('tests_total',0),
              result.get('truth_level','L0')))
        self.conn.commit()
        return cur.lastrowid

    # ---- Reports ----
    def add_report(self, report: dict) -> int:
        cur = self.conn.execute("""
            INSERT INTO deduction_reports (plan_id,project_id,report_type,title,content,metrics)
            VALUES (?,?,?,?,?,?)
        """, (report.get('plan_id'), report.get('project_id'),
              report.get('report_type','round'), report.get('title',''),
              report.get('content',''), json.dumps(report.get('metrics',{}))))
        self.conn.commit()
        return cur.lastrowid

    # ---- Blocked Problems ----
    def add_problem(self, prob: dict) -> int:
        cur = self.conn.execute("""
            INSERT INTO blocked_problems (plan_id,project_id,title,description,severity,status,suggested_solution)
            VALUES (?,?,?,?,?,?,?)
        """, (prob.get('plan_id'), prob['project_id'], prob['title'],
              prob.get('description',''), prob.get('severity','medium'),
              'open', prob.get('suggested_solution','')))
        self.conn.commit()
        return cur.lastrowid

    def get_problems(self, project_id=None, status=None) -> List[dict]:
        sql = "SELECT * FROM blocked_problems WHERE 1=1"
        params = []
        if project_id: sql += " AND project_id=?"; params.append(project_id)
        if status: sql += " AND status=?"; params.append(status)
        sql += " ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, created_at DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def resolve_problem(self, prob_id: int, solution: str, alt_ai: str = ""):
        self.conn.execute("""
            UPDATE blocked_problems SET status='resolved', user_solution=?, alt_ai_used=?, resolved_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (solution, alt_ai, prob_id))
        self.conn.commit()

    def update_problem_status(self, prob_id: int, status: str, solution: str = None):
        """问题状态流转: open→pending_verify→pending_deduction→deduced→resolved"""
        params = [status]
        extra = ""
        if solution:
            extra = ", user_solution=?"
            params.append(solution)
        if status == 'resolved':
            extra += ", resolved_at=CURRENT_TIMESTAMP"
        params.append(prob_id)
        self.conn.execute(f"""
            UPDATE blocked_problems SET status=?, updated_at=CURRENT_TIMESTAMP{extra} WHERE id=?
        """, params)
        self.conn.commit()

    def spawn_plan_from_problem(self, prob_id: int, plan_data: dict) -> str:
        """从阻塞问题生成新推演计划"""
        pid = self.add_plan(plan_data)
        self.conn.execute(
            "UPDATE blocked_problems SET spawned_plan_id=?, status='pending_deduction', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (pid, prob_id))
        self.conn.commit()
        return pid

    # ---- Deduction Nodes ----
    def add_node(self, node: dict) -> int:
        cur = self.conn.execute("""
            INSERT INTO deduction_nodes (plan_id,step_id,node_type,name,content,ulds_laws,confidence,truth_level,parent_node_id,relations)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (node['plan_id'], node.get('step_id'), node.get('node_type','concept'),
              node['name'], node.get('content',''), node.get('ulds_laws',''),
              node.get('confidence',0), node.get('truth_level','L0'),
              node.get('parent_node_id'), json.dumps(node.get('relations',[]))))
        self.conn.commit()
        return cur.lastrowid

    def get_nodes(self, plan_id: str = None) -> List[dict]:
        sql = "SELECT * FROM deduction_nodes"
        params = []
        if plan_id:
            sql += " WHERE plan_id=?"
            params.append(plan_id)
        sql += " ORDER BY created_at"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ---- Queue Settings ----
    def get_queue_settings(self) -> dict:
        row = self.conn.execute("SELECT * FROM queue_settings WHERE id='default'").fetchone()
        if row:
            return dict(row)
        defaults = {'id':'default','priority_project':None,'new_problems_position':'append',
                    'auto_expand':1,'max_expand_per_plan':3,'deduction_order':'priority'}
        self.conn.execute("""
            INSERT OR IGNORE INTO queue_settings (id,priority_project,new_problems_position,auto_expand,max_expand_per_plan,deduction_order)
            VALUES (?,?,?,?,?,?)
        """, (defaults['id'],defaults['priority_project'],defaults['new_problems_position'],
              defaults['auto_expand'],defaults['max_expand_per_plan'],defaults['deduction_order']))
        self.conn.commit()
        return defaults

    def update_queue_settings(self, settings: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO queue_settings (id,priority_project,new_problems_position,auto_expand,max_expand_per_plan,deduction_order,updated_at)
            VALUES ('default',?,?,?,?,?,CURRENT_TIMESTAMP)
        """, (settings.get('priority_project'), settings.get('new_problems_position','append'),
              settings.get('auto_expand',1), settings.get('max_expand_per_plan',3),
              settings.get('deduction_order','priority')))
        self.conn.commit()

    # ---- Model Configs ----
    def upsert_model(self, model: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO model_configs (id,name,api_url,model_id,role,max_tokens,temperature,enabled,priority)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (model['id'], model['name'], model.get('api_url',''),
              model.get('model_id',''), model.get('role',''),
              model.get('max_tokens',4096), model.get('temperature',0.7),
              model.get('enabled',1), model.get('priority',5)))
        self.conn.commit()

    # ---- Workflows ----
    def upsert_workflow(self, wf: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO workflows (id,name,project_id,description,steps,status)
            VALUES (?,?,?,?,?,?)
        """, (wf['id'], wf['name'], wf.get('project_id'),
              wf.get('description',''), json.dumps(wf.get('steps',[])),
              wf.get('status','draft')))
        self.conn.commit()

    def get_workflows(self, project_id=None) -> List[dict]:
        sql = "SELECT * FROM workflows"
        params = []
        if project_id: sql += " WHERE project_id=?"; params.append(project_id)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ---- CRM Users ----
    def login_user(self, name: str) -> dict:
        uid = hashlib.md5(name.encode()).hexdigest()[:12]
        self.conn.execute("""
            INSERT OR IGNORE INTO crm_users (id,name) VALUES (?,?)
        """, (uid, name))
        self.conn.execute("UPDATE crm_users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (uid,))
        self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM crm_users WHERE id=?", (uid,)).fetchone())

    # ---- Stats ----
    def get_stats(self) -> dict:
        return {
            'total_plans': self.conn.execute("SELECT COUNT(*) FROM deduction_plans").fetchone()[0],
            'queued': self.conn.execute("SELECT COUNT(*) FROM deduction_plans WHERE status='queued'").fetchone()[0],
            'running': self.conn.execute("SELECT COUNT(*) FROM deduction_plans WHERE status='running'").fetchone()[0],
            'done': self.conn.execute("SELECT COUNT(*) FROM deduction_plans WHERE status='done'").fetchone()[0],
            'problems_open': self.conn.execute("SELECT COUNT(*) FROM blocked_problems WHERE status='open'").fetchone()[0],
            'problems_pending': self.conn.execute("SELECT COUNT(*) FROM blocked_problems WHERE status IN ('pending_verify','pending_deduction')").fetchone()[0],
            'total_steps': self.conn.execute("SELECT COUNT(*) FROM deduction_steps").fetchone()[0],
            'total_results': self.conn.execute("SELECT COUNT(*) FROM deduction_results").fetchone()[0],
            'total_nodes': self.conn.execute("SELECT COUNT(*) FROM deduction_nodes").fetchone()[0],
        }

    # ---- Export for CRM ----
    def export_for_crm(self) -> dict:
        """导出全部数据供CRM前端使用"""
        projects = self.get_projects()
        for p in projects:
            p['tags'] = json.loads(p.get('tags','[]')) if isinstance(p.get('tags'), str) else p.get('tags',[])
        plans = self.get_plans()
        problems = self.get_problems()
        stats = self.get_stats()
        workflows = self.get_workflows()
        nodes = self.get_nodes()
        queue_settings = self.get_queue_settings()
        return {
            'projects': projects,
            'deductions': plans,
            'problems': problems,
            'stats': stats,
            'workflows': workflows,
            'nodes': nodes,
            'queue_settings': queue_settings,
        }


# ==================== 初始化: 填充项目和模型 ====================

def init_projects(db: DeductionDB):
    """初始化8大项目"""
    projects = [
        {'id':'p_diepre','name':'刀模设计项目','description':'DiePre AI — 用户上传刀模图→ULDS推演→3D→2D制作图纸, F→V→F链式收敛',
         'color':'#ef4444','status':'active','progress':65,'tags':['AI','制造','刀模','DiePre'],
         'ultimate_goal':'用户免费使用现有刀模图, 经ULDS推演获取制作刀模的2D图纸, 持续优化精度',
         'short_term_goal':'Playwright自动验证+反馈→推演最佳实现'},
        {'id':'p_rose','name':'予人玫瑰','description':'予人玫瑰项目 — 上线运转+快速商业化',
         'color':'#ec4899','status':'active','progress':30,'tags':['创意','商业','CRM'],
         'ultimate_goal':'项目上线+商业化拓展+分成方案',
         'short_term_goal':'CRM用户登录+任务增删改查+反馈机制'},
        {'id':'p_huarong','name':'刀模活字印刷3D','description':'华容道×乐高×活字印刷→模块化卡刀→平整刀模, IADD标准',
         'color':'#f59e0b','status':'active','progress':20,'tags':['3D打印','乐高','华容道','IADD','拓竹P2S'],
         'ultimate_goal':'3D打印模块化刀模, 支持各种尺寸刀+卡纸, 可复用刀模模型',
         'short_term_goal':'IADD规格研究 + 拓竹P2S全模块2D图纸'},
        {'id':'p_model','name':'本地模型超越计划','description':'终极:突破世界前沿认知 | 短期:代码能力超Claude Opus 4.6',
         'color':'#6366f1','status':'active','progress':56,'tags':['AGI','代码','超越','自成长'],
         'ultimate_goal':'突破当下世界前沿认知',
         'short_term_goal':'代码能力超过Claude Opus 4.6, 强化自成长'},
        {'id':'p_mgmt','name':'最佳管理协作制度','description':'推演实践最佳管理协作制度, 圆桌决策借鉴历史人物高光',
         'color':'#10b981','status':'active','progress':15,'tags':['管理','协作','圆桌','历史人物'],
         'ultimate_goal':'构建AI圆桌决策系统, 汲取历史优秀人物能力',
         'short_term_goal':'最佳实践推演'},
        {'id':'p_operators','name':'三个算子推演','description':'三个核心算子极致推演, 目标算法第一',
         'color':'#8b5cf6','status':'active','progress':5,'tags':['算子','算法','推演'],
         'ultimate_goal':'拿下算法第一',
         'short_term_goal':'三算子形式化定义+代码实现'},
        {'id':'p_visual','name':'最佳视觉效果推演','description':'让AI理解人类觉得好看的视觉体验, 色彩/布局/动效/情感',
         'color':'#f472b6','status':'active','progress':0,'tags':['视觉','设计','美学','UX'],
         'ultimate_goal':'AI深度理解人类视觉审美, 自主生成最佳视觉方案',
         'short_term_goal':'视觉美学规则体系 + CRM美化实践'},
        {'id':'p_workflow','name':'工作流可视化项目','description':'可视化定义SKILL调用链路+能力编排',
         'color':'#0ea5e9','status':'active','progress':0,'tags':['工作流','可视化','SKILL','编排'],
         'ultimate_goal':'用户可视化拖拽定义AI工作流, 自动编排SKILL调用链',
         'short_term_goal':'工作流编辑器原型 + SKILL节点可视化'},
        {'id':'p_playwright','name':'Playwright可视化验证','description':'Playwright对所有可视化页面进行自动化测试验证+反馈推演',
         'color':'#16a34a','status':'active','progress':0,'tags':['Playwright','测试','自动化','验证'],
         'ultimate_goal':'所有可视化项目Playwright自动验证+反馈循环推演',
         'short_term_goal':'CRM系统全页面Playwright自动化测试'},
    ]
    for p in projects:
        db.upsert_project(p)

def init_models(db: DeductionDB):
    """初始化模型配置"""
    models = [
        {'id':'ollama_local','name':'Ollama 14B (君)','api_url':'http://localhost:11434','model_id':'qwen2.5-coder:14b','role':'emperor','max_tokens':4096,'temperature':0.3,'priority':1},
        {'id':'glm5','name':'GLM-5 (臣)','api_url':'https://open.bigmodel.cn/api/coding/paas/v4','model_id':'glm-5','role':'minister','max_tokens':8192,'temperature':0.7,'priority':2},
        {'id':'glm5_turbo','name':'GLM-5 Turbo (快臣)','api_url':'https://open.bigmodel.cn/api/coding/paas/v4','model_id':'glm-5-turbo','role':'fast_minister','max_tokens':8192,'temperature':0.5,'priority':3},
        {'id':'glm47','name':'GLM-4.7 (佐)','api_url':'https://open.bigmodel.cn/api/coding/paas/v4','model_id':'glm-4.7','role':'assistant','max_tokens':4096,'temperature':0.5,'priority':4},
        {'id':'glm45air','name':'GLM-4.5-Air (使)','api_url':'https://open.bigmodel.cn/api/coding/paas/v4','model_id':'glm-4.5-air','role':'messenger','max_tokens':2048,'temperature':0.3,'priority':5},
    ]
    for m in models:
        db.upsert_model(m)


# ==================== 生成全部推演计划 ====================

def generate_all_plans(db: DeductionDB):
    """为所有项目生成详尽的推演计划"""

    ALL_PLANS = [
        # ====== 刀模设计项目 (p_diepre) ======
        {'project_id':'p_diepre','title':'刀模图解析引擎','description':'用户上传DXF/PDF刀模图→自动解析几何元素(线/弧/压痕线/切割线)→结构化数据',
         'priority':'critical','ulds_laws':'L1数学+L4逻辑+L5信息','surpass_strategies':'S7零回避+S8链式收敛','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'三维需求→二维图纸推演','description':'用户输入3D盒型需求(长宽高+材料)→ULDS推演→自动生成制作刀模2D图纸',
         'priority':'critical','ulds_laws':'L1+L2+L3+L8对称','surpass_strategies':'S4碰撞+S8收敛','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'F→V→F约束传播求解器','description':'F₀(物理)→V₁(材料)→F₁(误差范围)→V₂(结构)→F₂(荷载)→V₃(工艺)→F₃(质量)',
         'priority':'high','ulds_laws':'L1+L2+L3+L6系统+L8','surpass_strategies':'S8链式收敛','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'材料特性数据库推演','description':'纸板/瓦楞/白卡/灰板各材料误差范围[εmin,εmax]和承载范围[Fmin,Fmax]',
         'priority':'high','ulds_laws':'L2物理+L3化学+L7概率','surpass_strategies':'S5真实性','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_diepre','title':'Playwright自动化验证','description':'运用Playwright对刀模设计Web界面全流程自动化测试+反馈循环',
         'priority':'high','ulds_laws':'L6系统+L10演化','surpass_strategies':'S7零回避','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_diepre','title':'精度优化反馈循环','description':'用户反馈→误差分析→参数调整→重新推演→精度提升',
         'priority':'medium','ulds_laws':'L7概率+L10演化+L11认识论','surpass_strategies':'S3王朝治理','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'刀模行业知识图谱','description':'构建刀模设计领域知识图谱:材料→工艺→设备→规格→成本',
         'priority':'medium','ulds_laws':'L5信息+L6系统','surpass_strategies':'S2技能锚定','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== 予人玫瑰 (p_rose) ======
        {'project_id':'p_rose','title':'上线不可回避问题推演','description':'推演项目上线运转所有不可回避的问题:法律/支付/运维/安全/用户增长',
         'priority':'critical','ulds_laws':'L4逻辑+L6系统+L11认识论','surpass_strategies':'S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_rose','title':'CRM用户系统实现','description':'用户输入名字登录(无密码), 任务增删改查, 完善反馈机制',
         'priority':'critical','ulds_laws':'L4逻辑+L5信息+L9可计算','surpass_strategies':'S7零回避+S8收敛','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_rose','title':'商业化方案推演','description':'推演商业模式:定价/分成/订阅/广告/增值服务, 竞争分析',
         'priority':'high','ulds_laws':'L1数学+L7概率+L10演化','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_rose','title':'分成方案推演','description':'创作者/平台/推广者分成比例, 阶梯分成, 激励机制推演',
         'priority':'high','ulds_laws':'L1+L7+L8对称','surpass_strategies':'S4碰撞+S3王朝','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_rose','title':'快速商业化拓展路径','description':'冷启动→种子用户→病毒传播→规模化, 各阶段策略推演',
         'priority':'high','ulds_laws':'L6系统+L10演化+L7概率','surpass_strategies':'S3王朝治理','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_rose','title':'支付与法律合规','description':'支付接入/用户协议/隐私政策/知识产权/税务处理',
         'priority':'medium','ulds_laws':'L4逻辑+L11认识论','surpass_strategies':'S7零回避','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 刀模活字印刷3D (p_huarong) ======
        {'project_id':'p_huarong','title':'IADD规格研究','description':'国际刀模协会(IADD)标准规格研究: 刀片厚度/高度/弯曲半径/压痕线规格',
         'priority':'critical','ulds_laws':'L1数学+L2物理+L3化学','surpass_strategies':'S5真实性+S7零回避','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_huarong','title':'活字印刷模块化设计','description':'参考活字印刷+华容道+乐高, 设计可拼接的刀模模块系统',
         'priority':'critical','ulds_laws':'L1+L8对称+L9可计算','surpass_strategies':'S4碰撞+S8收敛','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_huarong','title':'拓竹P2S全模块2D图纸','description':'为拓竹P2S 3D打印机设计全部可复用刀模模块的2D图纸',
         'priority':'high','ulds_laws':'L1+L2+L8+L9','surpass_strategies':'S8链式收敛','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_huarong','title':'卡刀固定机构推演','description':'模块化卡刀系统: 支持各种尺寸刀片+卡纸, 快速组装/拆卸',
         'priority':'high','ulds_laws':'L2物理+L3化学+L8对称','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5_turbo'},
        {'project_id':'p_huarong','title':'3D打印材料适配','description':'PLA/PETG/ABS/TPU各材料对刀模模块的适配性推演',
         'priority':'medium','ulds_laws':'L2+L3+L7概率','surpass_strategies':'S5真实性','estimated_rounds':4,'model_preference':'glm5_turbo'},
        {'project_id':'p_huarong','title':'组合优化算法','description':'华容道式的刀模拼接组合优化→最小间隙+最大利用率',
         'priority':'high','ulds_laws':'L1数学+L9可计算','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},

        # ====== 本地模型超越计划 (p_model) ======
        {'project_id':'p_model','title':'自成长引擎强化推演','description':'强化自成长能力: 自动发现弱点→生成训练数据→自我提升',
         'priority':'critical','ulds_laws':'L6系统+L10演化+L11认识论','surpass_strategies':'S3王朝+S7零回避','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_model','title':'见路不走:未知领域探索','description':'对未知领域执行"见路不走"策略, 走出独属于我们的道路',
         'priority':'critical','ulds_laws':'L10演化+L11认识论+L7概率','surpass_strategies':'S4碰撞+S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_model','title':'SWE-Bench 55%突破','description':'多文件编辑+AST差分+测试自动生成, 目标SWE-Bench 55%',
         'priority':'high','ulds_laws':'L1+L4+L5+L8','surpass_strategies':'S2锚定+S4碰撞','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_model','title':'多语言75分突破','description':'Rust/Go/Java/C# 专项提升到75分',
         'priority':'high','ulds_laws':'L8对称+L10演化','surpass_strategies':'S2锚定','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_model','title':'已知最佳实践推演','description':'对已知实现推演最佳实践, proven节点质量跃迁',
         'priority':'high','ulds_laws':'L4逻辑+L5信息+L7概率','surpass_strategies':'S5真实性','estimated_rounds':6,'model_preference':'glm5_turbo'},
        {'project_id':'p_model','title':'200K上下文稳定处理','description':'大上下文窗口注意力优化+记忆压缩+关键信息锚定',
         'priority':'medium','ulds_laws':'L5信息+L9可计算','surpass_strategies':'S8收敛','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_model','title':'Agent完全自治路径','description':'工具锻造+自主学习+自我修复闭环',
         'priority':'medium','ulds_laws':'L6系统+L10演化','surpass_strategies':'S3王朝','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_model','title':'GitHub开源项目学习','description':'自动发现+分析GitHub高星项目, 提取架构模式和最佳实践',
         'priority':'medium','ulds_laws':'L5信息+L10演化','surpass_strategies':'S2锚定','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== 最佳管理协作制度 (p_mgmt) ======
        {'project_id':'p_mgmt','title':'历史人物圆桌决策系统','description':'毛主席(学习/军事/政治)+释迦摩尼(护念/种念)+王阳明(心即理)+更多历史人物的独特能力融合',
         'priority':'critical','ulds_laws':'L4逻辑+L6系统+L10演化+L11认识论','surpass_strategies':'S4碰撞+S3王朝','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_mgmt','title':'管理协作最佳实践','description':'推演最佳管理协作制度: 扁平/层级/矩阵/敏捷, 各模式优劣分析',
         'priority':'high','ulds_laws':'L6系统+L7概率+L8对称','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_mgmt','title':'多Agent协作博弈推演','description':'多AI Agent协作的纳什均衡+帕累托最优+激励相容',
         'priority':'high','ulds_laws':'L1数学+L4逻辑+L7概率','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_mgmt','title':'毛主席高光能力提炼','description':'提炼毛主席在学习/军事/政治方面的核心方法论, 映射为AI决策模式',
         'priority':'medium','ulds_laws':'L4逻辑+L10演化+L11认识论','surpass_strategies':'S5真实性','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_mgmt','title':'释迦摩尼护念种念映射','description':'护念(保护正确认知不被干扰)+种念(种下新认知种子)→AI认知管理',
         'priority':'medium','ulds_laws':'L5信息+L6系统+L11认识论','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_mgmt','title':'王阳明心即理→AI推理','description':'心即理/知行合一/致良知 → AI推理架构:推理即行动, 知即行',
         'priority':'medium','ulds_laws':'L4逻辑+L11认识论','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== 三个算子推演 (p_operators) ======
        {'project_id':'p_operators','title':'三算子形式化定义','description':'三个核心算子数学形式化: 算子空间/运算规则/完备性证明',
         'priority':'critical','ulds_laws':'L1数学+L4逻辑+L9可计算','surpass_strategies':'S5真实性+S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_operators','title':'算子代码实现','description':'三算子的高效代码实现, benchmark对比, 复杂度分析',
         'priority':'high','ulds_laws':'L1+L9可计算+L10演化','surpass_strategies':'S2锚定+S4碰撞','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_operators','title':'算法竞赛第一路径','description':'分析算法竞赛评分维度, 针对性优化, 冲击第一',
         'priority':'high','ulds_laws':'L1+L7概率+L10演化','surpass_strategies':'S4碰撞','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_operators','title':'算子组合优化','description':'三算子组合使用的最优策略, 互补性分析',
         'priority':'medium','ulds_laws':'L1+L8对称+L9','surpass_strategies':'S8收敛','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== 最佳视觉效果推演 (p_visual) ======
        {'project_id':'p_visual','title':'人类视觉审美规则体系','description':'色彩理论/黄金比例/留白/对比/层次/动效 → 形式化规则',
         'priority':'critical','ulds_laws':'L1数学+L2物理(光学)+L8对称','surpass_strategies':'S5真实性+S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_visual','title':'CRM系统美化实践','description':'将视觉规则应用到CRM系统, A/B测试验证',
         'priority':'high','ulds_laws':'L8对称+L10演化','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_visual','title':'色彩情感映射','description':'色彩→情感→使用场景的映射关系推演',
         'priority':'medium','ulds_laws':'L2物理+L5信息+L7概率','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_visual','title':'动效与交互体验','description':'加载动画/过渡效果/微交互对用户体验的影响推演',
         'priority':'medium','ulds_laws':'L2物理+L6系统','surpass_strategies':'S8收敛','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 工作流可视化项目 (p_workflow) ======
        {'project_id':'p_workflow','title':'SKILL调用链编辑器','description':'可视化拖拽SKILL节点→定义调用链→自动执行',
         'priority':'critical','ulds_laws':'L1图论+L4逻辑+L6系统','surpass_strategies':'S2锚定+S8收敛','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_workflow','title':'能力编排引擎','description':'SKILL+模型+工具的自动编排, 智能路由+负载均衡',
         'priority':'high','ulds_laws':'L6系统+L9可计算+L10演化','surpass_strategies':'S3王朝+S8收敛','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_workflow','title':'工作流模板库','description':'预设常用工作流模板: 代码审查/文档生成/测试流水线',
         'priority':'medium','ulds_laws':'L5信息+L8对称','surpass_strategies':'S2锚定','estimated_rounds':4,'model_preference':'glm5_turbo'},
        {'project_id':'p_workflow','title':'模型调用链路可视化','description':'本地模型处理问题时的调用链路可视化+调节界面',
         'priority':'high','ulds_laws':'L5信息+L6系统','surpass_strategies':'S8收敛','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== AGI CRM完善性推演 ======
        {'project_id':'p_workflow','title':'Skill库完善推演','description':'完善Skill库标题/描述/功能性, 提升可搜索性和可用性',
         'priority':'high','ulds_laws':'L5信息+L8对称','surpass_strategies':'S2锚定+S5真实性','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== Playwright可视化验证 (p_playwright) ======
        {'project_id':'p_playwright','title':'CRM全页面自动化测试','description':'Playwright对CRM的仪表盘/项目/推演/任务/技能/模型/问题/工作流全8个页面自动化测试',
         'priority':'critical','ulds_laws':'L4逻辑+L6系统+L9可计算','surpass_strategies':'S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_playwright','title':'DiePre刀模Web界面验证','description':'Playwright对DiePre刀模设计Web全流程自动化测试: 上传→解析→推演→图纸输出',
         'priority':'critical','ulds_laws':'L4+L6+L10演化','surpass_strategies':'S7零回避+S8收敛','estimated_rounds':10,'model_preference':'glm5'},
        {'project_id':'p_playwright','title':'予人玫瑰CRM验证','description':'Playwright对予人玫瑰CRM用户登录/任务CRUD/反馈机制全流程验证',
         'priority':'high','ulds_laws':'L4+L6+L9','surpass_strategies':'S7零回避','estimated_rounds':6,'model_preference':'glm5_turbo'},
        {'project_id':'p_playwright','title':'可视化回归测试框架','description':'每次推演后自动运行Playwright回归测试, 结果写入推演数据库',
         'priority':'high','ulds_laws':'L6系统+L10演化','surpass_strategies':'S7+S8','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_playwright','title':'截图对比反馈推演','description':'Playwright截图前后对比→视觉差异分析→反馈给视觉推演项目',
         'priority':'medium','ulds_laws':'L2物理(光学)+L5信息+L8','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},

        # ====== 扩充: 刀模项目深度推演 ======
        {'project_id':'p_diepre','title':'Pacdora 5969模型分析推演','description':'分析Pacdora爬取的5969个刀模模型, 提取常见盒型参数/尺寸分布/结构计算',
         'priority':'high','ulds_laws':'L1数学+L5信息+L7概率','surpass_strategies':'S2锚定+S5真实性','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'刀模图→Three.js 3D渲染','description':'DXF解析后的刀模线条→Three.js 3D立体预览, 支持旋转/缩放/展开',
         'priority':'high','ulds_laws':'L1几何+L2物理+L8对称','surpass_strategies':'S4碰撞+S8收敛','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_diepre','title':'Pacdora竞品差异化推演','description':'DiePre vs Pacdora: F→V→F约束传播是核心护城河, Pacdora只做2D→3D可视化',
         'priority':'medium','ulds_laws':'L4逻辑+L10演化+L11','surpass_strategies':'S3王朝','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_diepre','title':'刀模图自动纠错推演','description':'用户上传不规范刀模图→自动检测错误(gap/overlap/未闭合)→推演修复方案',
         'priority':'high','ulds_laws':'L1+L4+L9可计算','surpass_strategies':'S7零回避','estimated_rounds':6,'model_preference':'glm5'},

        # ====== 扩充: 予人玫瑰深度推演 ======
        {'project_id':'p_rose','title':'用户增长飞轮推演','description':'获客→激活→留存→推荐→变现, 各环节转化率优化',
         'priority':'high','ulds_laws':'L6系统+L7概率+L10演化','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_rose','title':'社交裂变传播策略','description':'种子用户→社交分享→裂变传播, K因子优化',
         'priority':'medium','ulds_laws':'L6+L7+L10','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},
        {'project_id':'p_rose','title':'多端适配推演','description':'Web/小程序/APP多端适配策略, 优先级排序',
         'priority':'medium','ulds_laws':'L8对称+L9可计算','surpass_strategies':'S8收敛','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 扩充: 本地模型深度推演 ======
        {'project_id':'p_model','title':'多模型协同推理推演','description':'Ollama+GLM-5+GLM-5T+GLM-4.7协同推理, 动态路由+结果融合',
         'priority':'critical','ulds_laws':'L6系统+L7概率+L8对称','surpass_strategies':'S6并行+S3王朝','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_model','title':'幻觉检测与消除推演','description':'Ollama本地校验→GLM-5交叉验证→幻觉率<5%',
         'priority':'high','ulds_laws':'L4逻辑+L5信息+L11认识论','surpass_strategies':'S5真实性+S7零回避','estimated_rounds':8,'model_preference':'glm5'},
        {'project_id':'p_model','title':'Proven节点质量跃迁','description':'L1→2000+节点, L3→500+节点, 双轨分类促进',
         'priority':'high','ulds_laws':'L5+L7+L10','surpass_strategies':'S5真实性','estimated_rounds':6,'model_preference':'glm5_turbo'},
        {'project_id':'p_model','title':'SKILL自动生成质量提升','description':'零回避扫描→有效率从64%→85%, 自动测试通过率提升',
         'priority':'high','ulds_laws':'L9可计算+L10演化','surpass_strategies':'S7零回避+S2锚定','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_model','title':'视频/音频/图片理解能力推演','description':'借鉴SKILL多模态理解能力, 推演本地模型视觉/听觉推理路径',
         'priority':'medium','ulds_laws':'L2物理+L5信息+L8','surpass_strategies':'S4碰撞','estimated_rounds':6,'model_preference':'glm5'},

        # ====== 扩充: 管理协作深度推演 ======
        {'project_id':'p_mgmt','title':'孙子兵法→AI策略引擎','description':'孙子兵法核心原则映射为AI策略决策模块',
         'priority':'medium','ulds_laws':'L4逻辑+L6系统+L10','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5'},
        {'project_id':'p_mgmt','title':'团队激励机制推演','description':'内在/外在激励的最优组合, 包括反馈频率/成长感/自主性',
         'priority':'medium','ulds_laws':'L6+L7+L10','surpass_strategies':'S4碰撞','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 扩充: 三算子深度推演 ======
        {'project_id':'p_operators','title':'算子与现有算法融合','description':'三算子与DP/图算法/贪心/分治的融合应用',
         'priority':'high','ulds_laws':'L1+L4+L8对称','surpass_strategies':'S4碰撞+S2锚定','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_operators','title':'算子Benchmark全平台对比','description':'LeetCode/Codeforces/AtCoder全平台算子性能对比测试',
         'priority':'high','ulds_laws':'L1+L7概率+L9','surpass_strategies':'S5真实性','estimated_rounds':6,'model_preference':'glm5'},

        # ====== 扩充: 视觉效果深度推演 ======
        {'project_id':'p_visual','title':'设计系统构建','description':'Design Token/组件库/主题系统的规范化推演',
         'priority':'high','ulds_laws':'L8对称+L5信息','surpass_strategies':'S2锚定+S8收敛','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_visual','title':'无障碍视觉设计','description':'WCAG 2.1标准→对比度/字体/语义化颜色的可访问性推演',
         'priority':'medium','ulds_laws':'L2物理(光学)+L4+L8','surpass_strategies':'S7零回避','estimated_rounds':4,'model_preference':'glm5_turbo'},
        {'project_id':'p_visual','title':'字体排印体系推演','description':'字体选择/字号比例/行高/字间距的最佳实践推演',
         'priority':'medium','ulds_laws':'L1数学+L8对称','surpass_strategies':'S5真实性','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 扩充: 工作流深度推演 ======
        {'project_id':'p_workflow','title':'工作流条件分支推演','description':'if/else/switch条件分支节点, 支持复杂工作流逻辑',
         'priority':'high','ulds_laws':'L4逻辑+L9可计算','surpass_strategies':'S8收敛','estimated_rounds':5,'model_preference':'glm5'},
        {'project_id':'p_workflow','title':'工作流并行执行','description':'并行节点+同步屏障+结果合并的可视化编排',
         'priority':'medium','ulds_laws':'L6系统+L9','surpass_strategies':'S6并行','estimated_rounds':5,'model_preference':'glm5'},
        {'project_id':'p_workflow','title':'工作流历史记录与回放','description':'工作流执行历史可视化回放, 支持回滚/重试',
         'priority':'medium','ulds_laws':'L5信息+L6系统','surpass_strategies':'S7零回避','estimated_rounds':4,'model_preference':'glm5_turbo'},

        # ====== 扩充: 活字印刷3D深度推演 ======
        {'project_id':'p_huarong','title':'刀模模块库参数化','description':'建立参数化模块库: 刀刃宽度/高度/角度→自动生成STL',
         'priority':'high','ulds_laws':'L1数学+L2物理+L9','surpass_strategies':'S8收敛','estimated_rounds':6,'model_preference':'glm5'},
        {'project_id':'p_huarong','title':'多尺寸刀片兼容性推演','description':'各种尺寸刀片(2pt/3pt/4pt/定制)与模块库的兼容性推演',
         'priority':'high','ulds_laws':'L1+L2+L8对称','surpass_strategies':'S4碰撞','estimated_rounds':5,'model_preference':'glm5_turbo'},
    ]

    for plan in ALL_PLANS:
        db.add_plan(plan)
    return len(ALL_PLANS)


def init_blocked_problems(db: DeductionDB):
    """初始化已知阻塞问题"""
    problems = [
        {'project_id':'p_diepre','title':'DXF解析器对复杂曲线支持不足','description':'当前ezdxf只能解析基础几何, 贝塞尔曲线和样条曲线精度不够','severity':'high','suggested_solution':'研究libdxfrw或自实现贝塞尔解析'},
        {'project_id':'p_diepre','title':'材料物理参数缺乏实测数据','description':'各材料的误差范围和承载范围需要实际测试数据验证','severity':'medium','suggested_solution':'联系刀模厂商获取测试数据, 或用Instron万能试验机'},
        {'project_id':'p_rose','title':'支付牌照/合规问题','description':'商业化需要支付接入, 涉及支付牌照和金融合规','severity':'high','suggested_solution':'使用微信支付/支付宝API, 或接入第三方聚合支付'},
        {'project_id':'p_huarong','title':'拓竹P2S打印精度限制','description':'FDM打印精度约±0.2mm, 可能不满足刀模精度要求','severity':'medium','suggested_solution':'SLA树脂打印可达±0.05mm, 或混合方案'},
        {'project_id':'p_model','title':'本地Ollama推理速度受限','description':'14B模型本地推理较慢(约30-60s/轮), 已通过Coding Plan Pro接入GLM-5/5-Turbo缓解; 复杂任务用GLM-5, 普通任务用GLM-4-flash节省额度','severity':'low','suggested_solution':'已缓解: GLM-5(复杂)+GLM-5-Turbo(快速)+GLM-4-flash(普通), Ollama仅用于validate阶段幻觉检测'},
        {'project_id':'p_operators','title':'算子理论完备性证明难度','description':'形式化证明需要深度数学能力, 可能需要外部数学AI辅助','severity':'high','suggested_solution':'调用Claude/GPT进行数学证明辅助'},
    ]
    for p in problems:
        db.add_problem(p)


# ==================== 主入口 ====================

def init_all():
    """初始化全部数据"""
    db = DeductionDB()
    init_projects(db)
    init_models(db)
    count = generate_all_plans(db)
    init_blocked_problems(db)
    stats = db.get_stats()

    # 导出CRM数据
    crm_data = db.export_for_crm()
    crm_json_path = os.path.join(os.path.dirname(__file__), "web", "data", "deduction_export.json")
    with open(crm_json_path, 'w', encoding='utf-8') as f:
        json.dump(crm_data, f, ensure_ascii=False, indent=2, default=str)

    db.close()
    return count, stats

if __name__ == "__main__":
    print("=" * 60)
    print("AGI v13 推演数据库初始化")
    print("=" * 60)
    count, stats = init_all()
    print(f"\n初始化完成:")
    print(f"  推演计划: {count} 个")
    print(f"  统计: {json.dumps(stats, indent=2)}")
    print(f"\n数据库: {DB_PATH}")
    print(f"CRM导出: web/data/deduction_export.json")
    print("=" * 60)
