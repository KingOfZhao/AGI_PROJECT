#!/usr/bin/env python3
"""
予人玫瑰 CRM v2 — 数据库扩展 + 任务系统升级
新增: projects, milestones, brand_assets, content_articles, suppliers, campaigns
增强: tasks支持子任务/模板/看板状态
"""
import sqlite3, json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

DB_PATH = Path(__file__).parent / "rose_crm.db"

class RoseCRM:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._migrate()

    def _conn(self):
        c = sqlite3.connect(str(self.db_path))
        c.row_factory = sqlite3.Row
        return c

    def _migrate(self):
        """V2迁移：新增表 + 扩展tasks"""
        c = self._conn()
        c.executescript("""
            -- 项目表
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                phase TEXT DEFAULT 'planning',
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                start_date TEXT,
                target_date TEXT,
                progress_pct INTEGER DEFAULT 0,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 里程碑
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                status TEXT DEFAULT 'pending',
                completed_at TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            -- 品牌资产
            CREATE TABLE IF NOT EXISTS brand_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT,
                version TEXT DEFAULT '1.0',
                tags TEXT,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 内容管理
            CREATE TABLE IF NOT EXISTS content_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                platform TEXT DEFAULT 'wechat',
                status TEXT DEFAULT 'draft',
                publish_date TEXT,
                author TEXT,
                tags TEXT,
                read_count INTEGER DEFAULT 0,
                share_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 供应商
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                rating INTEGER DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 传播活动
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                description TEXT,
                status TEXT DEFAULT 'planning',
                start_date TEXT,
                end_date TEXT,
                metrics TEXT,
                budget REAL,
                actual_cost REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 子任务 (扩展tasks)
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            -- 任务模板
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                subtasks_json TEXT,
                tags TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- 索引
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);
            CREATE INDEX IF NOT EXISTS idx_content_status ON content_articles(status);
            CREATE INDEX IF NOT EXISTS idx_subtasks_task ON subtasks(task_id);
            CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);

            -- 扩展tasks表：看板列（已存在则跳过）
        """)
        # ALTER TABLE if not exists workaround
        c2 = self._conn()
        cols = {r[1] for r in c2.execute("PRAGMA table_info(tasks)").fetchall()}
        if 'board_column' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN board_column TEXT DEFAULT 'todo'")
        if 'sort_order' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN sort_order INTEGER DEFAULT 0")
        if 'project_id' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects(id)")
        if 'tags' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN tags TEXT")
        if 'time_estimated' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN time_estimated INTEGER")
        if 'time_spent' not in cols:
            c2.execute("ALTER TABLE tasks ADD COLUMN time_spent INTEGER")
        c2.commit()
        c2.close()
        self._conn().execute("""
        """)
        c.commit()
        c.close()

    # ═══ 项目 ═══
    def create_project(self, name, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO projects (name,description,phase,status,priority,start_date,target_date,progress_pct,tags)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (name, kw.get('description'), kw.get('phase','planning'), kw.get('status','active'),
             kw.get('priority','medium'), kw.get('start_date'), kw.get('target_date'),
             kw.get('progress_pct',0), json.dumps(kw.get('tags',[]))))
        c.commit(); pid = cur.lastrowid; c.close(); return pid

    def get_project(self, pid) -> Optional[Dict]:
        c = self._conn()
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        c.close()
        return dict(r) if r else None

    def list_projects(self, status=None, phase=None, limit=50) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM projects WHERE 1=1"
        p = []
        if status: q += " AND status=?"; p.append(status)
        if phase: q += " AND phase=?"; p.append(phase)
        q += " ORDER BY created_at DESC LIMIT ?"; p.append(limit)
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    def update_project(self, pid, **kw) -> bool:
        if not kw: return False
        fields, vals = [], []
        for k in ['name','description','phase','status','priority','start_date','target_date','progress_pct']:
            if k in kw: fields.append(f"{k}=?"); vals.append(kw[k])
        if 'tags' in kw: fields.append("tags=?"); vals.append(json.dumps(kw['tags']))
        fields.append("updated_at=CURRENT_TIMESTAMP"); vals.append(pid)
        c = self._conn(); c.execute(f"UPDATE projects SET {','.join(fields)} WHERE id=?", vals)
        c.commit(); c.close(); return True

    # ═══ 里程碑 ═══
    def create_milestone(self, project_id, title, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO milestones (project_id,title,description,target_date,status,sort_order)
            VALUES (?,?,?,?,?,?)""",
            (project_id, title, kw.get('description'), kw.get('target_date'),
             kw.get('status','pending'), kw.get('sort_order',0)))
        c.commit(); mid = cur.lastrowid; c.close(); return mid

    def list_milestones(self, project_id) -> List[Dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM milestones WHERE project_id=? ORDER BY sort_order", (project_id,)).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def complete_milestone(self, mid):
        c = self._conn()
        c.execute("UPDATE milestones SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (mid,))
        c.commit(); c.close()

    # ═══ 子任务 ═══
    def add_subtask(self, task_id, title, **kw) -> int:
        c = self._conn()
        cur = c.execute("INSERT INTO subtasks (task_id,title,status,sort_order) VALUES (?,?,?,?)",
            (task_id, title, kw.get('status','pending'), kw.get('sort_order',0)))
        c.commit(); sid = cur.lastrowid; c.close(); return sid

    def list_subtasks(self, task_id) -> List[Dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM subtasks WHERE task_id=? ORDER BY sort_order", (task_id,)).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def toggle_subtask(self, sid):
        c = self._conn()
        r = c.execute("SELECT status FROM subtasks WHERE id=?", (sid,)).fetchone()
        if r:
            new = 'completed' if r['status']=='pending' else 'pending'
            at = "completed_at=CURRENT_TIMESTAMP" if new=='completed' else "completed_at=NULL"
            c.execute(f"UPDATE subtasks SET status='{new}', {at} WHERE id=?", (sid,))
        c.commit(); c.close()

    # ═══ 任务模板 ═══
    def create_template(self, name, subtasks, **kw) -> int:
        c = self._conn()
        cur = c.execute("INSERT INTO task_templates (name,description,category,subtasks_json,tags) VALUES (?,?,?,?,?)",
            (name, kw.get('description'), kw.get('category'), json.dumps(subtasks), json.dumps(kw.get('tags',[]))))
        c.commit(); tid = cur.lastrowid; c.close(); return tid

    def list_templates(self, category=None) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM task_templates WHERE 1=1"
        p = []
        if category: q += " AND category=?"; p.append(category)
        q += " ORDER BY created_at DESC"
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    def apply_template(self, template_id, project_id=None, due_date=None) -> int:
        """从模板创建任务+子任务"""
        c = self._conn()
        t = c.execute("SELECT * FROM task_templates WHERE id=?", (template_id,)).fetchone()
        if not t: c.close(); return 0
        cur = c.execute("INSERT INTO tasks (title,description,project_id,status,due_date) VALUES (?,?,?,?,?)",
            (t['name'], t['description'], project_id, 'pending', due_date))
        task_id = cur.lastrowid
        subs = json.loads(t['subtasks_json'])
        for i, s in enumerate(subs):
            c.execute("INSERT INTO subtasks (task_id,title,sort_order) VALUES (?,?,?)", (task_id, s, i))
        c.commit(); c.close(); return task_id

    # ═══ 看板 ═══
    def move_task(self, task_id, column):
        valid = ['todo','in_progress','review','done']
        if column not in valid: return False
        c = self._conn()
        status_map = {'todo':'pending','in_progress':'in_progress','review':'review','done':'completed'}
        c.execute("UPDATE tasks SET board_column=?, status=? WHERE id=?",
            (column, status_map[column], task_id))
        if column == 'done':
            c.execute("UPDATE tasks SET completed_at=CURRENT_TIMESTAMP WHERE id=?", (task_id,))
        c.commit(); c.close(); return True

    def get_board(self, project_id=None) -> Dict[str, List[Dict]]:
        """获取看板视图"""
        c = self._conn()
        q = "SELECT t.*, c.name as customer_name FROM tasks t LEFT JOIN customers c ON t.customer_id=c.id WHERE t.status!='deleted'"
        p = []
        if project_id: q += " AND t.project_id=?"; p.append(project_id)
        q += " ORDER BY t.sort_order"
        rows = c.execute(q, p).fetchall(); c.close()
        board = {'todo':[], 'in_progress':[], 'review':[], 'done':[]}
        for r in rows:
            d = dict(r)
            col = d.get('board_column','todo')
            if col not in board: col = 'todo'
            d['subtasks'] = self.list_subtasks(d['id'])
            board[col].append(d)
        return board

    # ═══ 品牌资产 ═══
    def create_asset(self, type, name, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO brand_assets (type,name,file_path,version,tags,status,notes)
            VALUES (?,?,?,?,?,?,?)""",
            (type, name, kw.get('file_path'), kw.get('version','1.0'),
             json.dumps(kw.get('tags',[])), kw.get('status','draft'), kw.get('notes')))
        c.commit(); aid = cur.lastrowid; c.close(); return aid

    def list_assets(self, type=None, status=None) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM brand_assets WHERE 1=1"
        p = []
        if type: q += " AND type=?"; p.append(type)
        if status: q += " AND status=?"; p.append(status)
        q += " ORDER BY updated_at DESC"
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    # ═══ 内容管理 ═══
    def create_article(self, title, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO content_articles (title,content,platform,status,publish_date,author,tags)
            VALUES (?,?,?,?,?,?,?)""",
            (title, kw.get('content'), kw.get('platform','wechat'), kw.get('status','draft'),
             kw.get('publish_date'), kw.get('author'), json.dumps(kw.get('tags',[]))))
        c.commit(); aid = cur.lastrowid; c.close(); return aid

    def list_articles(self, status=None, platform=None, limit=50) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM content_articles WHERE 1=1"
        p = []
        if status: q += " AND status=?"; p.append(status)
        if platform: q += " AND platform=?"; p.append(platform)
        q += " ORDER BY created_at DESC LIMIT ?"; p.append(limit)
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    def update_article(self, aid, **kw) -> bool:
        if not kw: return False
        fields, vals = [], []
        for k in ['title','content','platform','status','publish_date','author','read_count','share_count','like_count']:
            if k in kw: fields.append(f"{k}=?"); vals.append(kw[k])
        if 'tags' in kw: fields.append("tags=?"); vals.append(json.dumps(kw['tags']))
        fields.append("updated_at=CURRENT_TIMESTAMP"); vals.append(aid)
        c = self._conn(); c.execute(f"UPDATE content_articles SET {','.join(fields)} WHERE id=?", vals)
        c.commit(); c.close(); return True

    # ═══ 供应商 ═══
    def create_supplier(self, name, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO suppliers (name,category,contact_person,phone,email,address,rating,notes,status)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (name, kw.get('category'), kw.get('contact_person'), kw.get('phone'),
             kw.get('email'), kw.get('address'), kw.get('rating',0), kw.get('notes'), 'active'))
        c.commit(); sid = cur.lastrowid; c.close(); return sid

    def list_suppliers(self, category=None) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM suppliers WHERE status!='deleted'"
        p = []
        if category: q += " AND category=?"; p.append(category)
        q += " ORDER BY created_at DESC"
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    # ═══ 传播活动 ═══
    def create_campaign(self, name, **kw) -> int:
        c = self._conn()
        cur = c.execute("""INSERT INTO campaigns (name,type,description,status,start_date,end_date,metrics,budget,actual_cost,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (name, kw.get('type'), kw.get('description'), kw.get('status','planning'),
             kw.get('start_date'), kw.get('end_date'), json.dumps(kw.get('metrics',{})),
             kw.get('budget'), kw.get('actual_cost'), kw.get('notes')))
        c.commit(); cid = cur.lastrowid; c.close(); return cid

    def list_campaigns(self, status=None) -> List[Dict]:
        c = self._conn()
        q = "SELECT * FROM campaigns WHERE 1=1"
        p = []
        if status: q += " AND status=?"; p.append(status)
        q += " ORDER BY created_at DESC"
        rows = c.execute(q, p).fetchall(); c.close()
        return [dict(r) for r in rows]

    # ═══ 仪表盘 ═══
    def dashboard(self) -> Dict:
        c = self._conn()
        # 项目统计
        projs = c.execute("SELECT status, COUNT(*) as cnt FROM projects GROUP BY status").fetchall()
        proj_stats = {r['status']: r['cnt'] for r in projs}
        # 看板统计
        board = c.execute("SELECT board_column, COUNT(*) as cnt FROM tasks WHERE status!='deleted' GROUP BY board_column").fetchall()
        board_stats = {r['board_column']: r['cnt'] for r in board}
        # 内容统计
        articles = c.execute("SELECT status, COUNT(*) as cnt FROM content_articles GROUP BY status").fetchall()
        content_stats = {r['status']: r['cnt'] for r in articles}
        # 活动统计
        camps = c.execute("SELECT status, COUNT(*) as cnt FROM campaigns GROUP BY status").fetchall()
        camp_stats = {r['status']: r['cnt'] for r in camps}
        # 里程碑
        ms = c.execute("SELECT status, COUNT(*) as cnt FROM milestones GROUP BY status").fetchall()
        mile_stats = {r['status']: r['cnt'] for r in ms}
        # 近期任务
        recent = c.execute("""SELECT t.*, c.name as customer_name FROM tasks t
            LEFT JOIN customers c ON t.customer_id=c.id
            WHERE t.status NOT IN ('completed','deleted')
            ORDER BY t.updated_at DESC LIMIT 10""").fetchall()
        c.close()
        return {
            'projects': proj_stats,
            'board': board_stats,
            'content': content_stats,
            'campaigns': camp_stats,
            'milestones': mile_stats,
            'recent_tasks': [dict(r) for r in recent],
        }

    # ═══ 初始化种子数据 ═══
    def seed(self):
        """初始化予人玫瑰项目数据"""
        c = self._conn()
        existing = c.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if existing > 0:
            c.close(); return False
        c.close()

        # 创建项目
        p1 = self.create_project("公司注册", description="予人玫瑰公司注册全流程",
            phase="execution", priority="critical", tags=["P0","基础"])
        p2 = self.create_project("Logo设计", description="品牌Logo从概念到定稿",
            phase="execution", priority="critical", tags=["P0","品牌"])
        p3 = self.create_project("小程序开发", description="予人玫瑰小程序从设计到上线",
            phase="planning", priority="high", tags=["P0","产品"])
        p4 = self.create_project("公众号运营", description="公众号内容运营与粉丝增长",
            phase="planning", priority="high", tags=["P0","运营"])
        p5 = self.create_project("品牌VI体系", description="品牌视觉识别系统建设",
            phase="planning", priority="medium", tags=["P1","设计"])

        # 里程碑
        for pid, ms in [
            (p1, [("名称核准","3天"),("营业执照","7天"),("银行开户","5天"),("税务登记","3天")]),
            (p2, [("概念草图","5天"),("初稿设计","7天"),("内部评审","3天"),("定稿输出","3天")]),
            (p3, [("需求文档","7天"),("UI设计","14天"),("前端开发","21天"),("测试上线","7天")]),
            (p4, [("账号注册","1天"),("首批内容","7天"),("运营策略","5天"),("首批推广","14天")]),
        ]:
            for i,(title,days) in enumerate(ms):
                self.create_milestone(pid, title, sort_order=i)

        # 任务模板
        self.create_template("公司注册", ["工商查名","准备材料","提交申请","领取执照","刻章","银行开户","税务登记"], category="基础")
        self.create_template("Logo设计", ["品牌调研","概念发散","草图绘制","初稿设计","内部评审","客户反馈","修改定稿","多尺寸输出"], category="设计")
        self.create_template("小程序开发", ["需求分析","原型设计","UI设计","前端开发","后端开发","联调测试","内测","上线发布"], category="开发")
        self.create_template("公众号推文", ["选题策划","素材准备","内容撰写","配图设计","审核校对","定时发布","数据复盘"], category="运营")
        self.create_template("传播活动", ["活动策划","物料设计","渠道准备","活动上线","数据监控","活动总结"], category="营销")

        # 从模板创建任务
        self.apply_template(1, project_id=p1)  # 公司注册
        self.apply_template(2, project_id=p2)  # Logo设计

        # 内容
        self.create_article("予人玫瑰：让美好发生", content="品牌首发文章...",
            platform="wechat", status="draft", tags=["品牌","首发"])
        self.create_article("女性力量：做自己最美的样子", content="...",
            platform="wechat", status="draft", tags=["女性","成长"])
        self.create_article("公益进行时：每朵玫瑰都有意义", content="...",
            platform="wechat", status="draft", tags=["公益","传播"])

        # 供应商分类预设
        for cat in ["设计","印刷","包装","开发","物流","广告","法务","财务"]:
            self.create_supplier(f"[{cat}]待添加", category=cat)

        return True


# ═══ CLI v2 ═══
class RoseCLI:
    def __init__(self):
        self.crm = RoseCRM()

    def run(self, args):
        if not args: self.help(); return
        cmd = args[0]; p = args[1:]
        routes = {
            'project': self._project, 'milestone': self._milestone,
            'task': self._task, 'subtask': self._subtask,
            'template': self._template, 'board': self._board,
            'asset': self._asset, 'article': self._article,
            'supplier': self._supplier, 'campaign': self._campaign,
            'stats': self._stats, 'seed': self._seed, 'help': self.help,
        }
        h = routes.get(cmd)
        if h: h(p)
        else: print(f"未知: {cmd}"); self.help()

    def _project(self, p):
        if not p: print("project <add|list|get|update>"); return
        if p[0]=='add' and len(p)>=2:
            kw = {}
            for x in p[2:]:
                if x.startswith("--"): k,_,v = x[2:].partition("="); kw[k] = v
            pid = self.crm.create_project(p[1], **kw)
            print(f"✓ 项目 {pid}: {p[1]}")
        elif p[0]=='list':
            projs = self.crm.list_projects(p[1] if len(p)>1 else None)
            print(f"\n{'ID':<4} {'名称':<20} {'阶段':<12} {'优先级':<8} {'进度':<6}")
            print("-"*55)
            for pr in projs:
                print(f"{pr['id']:<4} {pr['name'][:18]:<20} {pr['phase']:<12} {pr['priority']:<8} {pr['progress_pct']}%")
        elif p[0]=='get' and len(p)>=2:
            pr = self.crm.get_project(int(p[1]))
            if pr:
                print(json.dumps(pr, indent=2, ensure_ascii=False, default=str))
                ms = self.crm.list_milestones(pr['id'])
                if ms:
                    print(f"\n里程碑({len(ms)}):")
                    for m in ms:
                        icon = "✓" if m['status']=='completed' else "○"
                        print(f"  {icon} {m['title']} ({m['target_date'] or '无期限'})")
        elif p[0]=='update' and len(p)>=3:
            kw = {}
            for x in p[2:]:
                if x.startswith("--"):
                    k,_,v = x[2:].partition("=")
                    if k in ('progress_pct',): v = int(v)
                    kw[k] = v
            self.crm.update_project(int(p[1]), **kw); print("✓")

    def _task(self, p):
        if not p: print("task <add|list|move>"); return
        if p[0]=='add' and len(p)>=2:
            kw = {}
            for x in p[2:]:
                if x.startswith("--"):
                    k,_,v = x[2:].partition("=")
                    if k in ('customer_id','project_id'): v = int(v)
                    kw[k] = v
            tid = self.crm.create_task(p[1], **kw)
            print(f"✓ 任务 {tid}: {p[1]}")
        elif p[0]=='list':
            from rose_crm import CRMDatabase
            db = CRMDatabase()
            tasks = db.list_tasks(p[1] if len(p)>1 else None, limit=20)
            print(f"\n{'ID':<4} {'标题':<25} {'状态':<12} {'看板':<14} {'优先级':<8}")
            print("-"*65)
            for t in tasks:
                col = t.get('board_column','todo')
                print(f"{t['id']:<4} {t['title'][:23]:<25} {t['status']:<12} {col:<14} {t['priority']:<8}")
        elif p[0]=='move' and len(p)>=3:
            self.crm.move_task(int(p[1]), p[2])
            print(f"✓ 任务{p[1]} → {p[2]}")

    def _subtask(self, p):
        if not p: print("subtask <add|list|toggle>"); return
        if p[0]=='add' and len(p)>=3:
            sid = self.crm.add_subtask(int(p[1]), p[2])
            print(f"✓ 子任务 {sid}")
        elif p[0]=='list' and len(p)>=2:
            subs = self.crm.list_subtasks(int(p[1]))
            for s in subs:
                icon = "✓" if s['status']=='completed' else "○"
                print(f"  {icon} [{s['id']}] {s['title']}")
        elif p[0]=='toggle' and len(p)>=2:
            self.crm.toggle_subtask(int(p[1])); print("✓")

    def _template(self, p):
        if not p or p[0]=='list':
            ts = self.crm.list_templates(p[1] if p and len(p)>1 else None)
            for t in ts:
                subs = json.loads(t['subtasks_json'])
                print(f"\n[{t['id']}] {t['name']} ({t['category']})")
                for i,s in enumerate(subs):
                    print(f"  {i+1}. {s}")

    def _board(self, p):
        pid = int(p[0]) if p else None
        board = self.crm.get_board(pid)
        columns = [('todo','📋 待办'),('in_progress','🔄 进行中'),('review','👁 审核'),('done','✅ 完成')]
        for col_key, col_name in columns:
            tasks = board.get(col_key, [])
            print(f"\n{col_name} ({len(tasks)})")
            print("-"*40)
            for t in tasks:
                subs = t.get('subtasks',[])
                done = sum(1 for s in subs if s['status']=='completed')
                sub_str = f" [{done}/{len(subs)}]" if subs else ""
                print(f"  #{t['id']} {t['title']}{sub_str}")

    def _milestone(self, p):
        if p[0]=='list' and len(p)>=2:
            ms = self.crm.list_milestones(int(p[1]))
            for m in ms:
                icon = "✓" if m['status']=='completed' else "○"
                print(f"  {icon} {m['title']} (截止: {m['target_date'] or '-'})")
        elif p[0]=='done' and len(p)>=2:
            self.crm.complete_milestone(int(p[1])); print("✓")

    def _article(self, p):
        if p[0]=='list':
            arts = self.crm.list_articles(p[1] if len(p)>1 else None)
            print(f"\n{'ID':<4} {'标题':<30} {'平台':<8} {'状态':<10}")
            print("-"*55)
            for a in arts:
                print(f"{a['id']:<4} {a['title'][:28]:<30} {a['platform']:<8} {a['status']:<10}")
        elif p[0]=='add' and len(p)>=2:
            kw = {}
            for x in p[2:]:
                if x.startswith("--"): k,_,v = x[2:].partition("="); kw[k] = v
            aid = self.crm.create_article(p[1], **kw)
            print(f"✓ 文章 {aid}")

    def _asset(self, p):
        if p[0]=='list':
            assets = self.crm.list_assets(p[1] if len(p)>1 else None)
            print(f"\n{'ID':<4} {'类型':<10} {'名称':<25} {'版本':<6} {'状态':<10}")
            print("-"*58)
            for a in assets:
                print(f"{a['id']:<4} {a['type']:<10} {a['name'][:23]:<25} {a['version']:<6} {a['status']:<10}")

    def _supplier(self, p):
        if p[0]=='list':
            sups = self.crm.list_suppliers(p[1] if len(p)>1 else None)
            print(f"\n{'ID':<4} {'名称':<20} {'分类':<10} {'联系人':<12} {'电话':<15}")
            print("-"*65)
            for s in sups:
                print(f"{s['id']:<4} {s['name'][:18]:<20} {s['category'] or '-':<10} {s['contact_person'] or '-':<12} {s['phone'] or '-':<15}")

    def _campaign(self, p):
        if p[0]=='list':
            camps = self.crm.list_campaigns(p[1] if len(p)>1 else None)
            print(f"\n{'ID':<4} {'名称':<25} {'类型':<10} {'状态':<12} {'预算':<8}")
            print("-"*62)
            for ca in camps:
                print(f"{ca['id']:<4} {ca['name'][:23]:<25} {ca['type'] or '-':<10} {ca['status']:<12} {ca['budget'] or '-':<8}")

    def _stats(self, p):
        d = self.crm.dashboard()
        print("\n═══════════════════════════════════")
        print("    🌹 予人玫瑰 CRM 仪表盘")
        print("═══════════════════════════════════")
        print(f"\n📁 项目: {d['projects']}")
        print(f"📋 看板: {d['board']}")
        print(f"📝 内容: {d['content']}")
        print(f"📢 活动: {d['campaigns']}")
        print(f"🏁 里程碑: {d['milestones']}")
        if d['recent_tasks']:
            print(f"\n🔥 最近任务:")
            for t in d['recent_tasks'][:5]:
                print(f"  #{t['id']} {t['title']} [{t.get('board_column','todo')}]")

    def _seed(self, p):
        if self.crm.seed():
            print("✓ 种子数据初始化完成")
        else:
            print("已存在数据，跳过")

    def help(self, p=None):
        print("""
🌹 予人玫瑰 CRM v2

命令:
  project    项目管理 (add/list/get/update)
  milestone  里程碑 (list/done)
  task       任务管理 (add/list/move)
  subtask    子任务 (add/list/toggle)
  template   任务模板 (list)
  board      看板视图 [project_id]
  asset      品牌资产 (list)
  article    内容管理 (add/list)
  supplier   供应商 (list)
  campaign   传播活动 (list)
  stats      仪表盘
  seed       初始化种子数据
  help       帮助

示例:
  python rose_crm_v2.py seed
  python rose_crm_v2.py stats
  python rose_crm_v2.py board
  python rose_crm_v2.py project list
  python rose_crm_v2.py task add "新任务" --project_id=1 --priority=high
  python rose_crm_v2.py task move 3 in_progress
  python rose_crm_v2.py subtask add 3 "子任务A"
  python rose_crm_v2.py subtask list 3
  python rose_crm_v2.py subtask toggle 5
        """)


if __name__ == "__main__":
    RoseCLI().run(__import__('sys').argv[1:])
