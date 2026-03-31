#!/usr/bin/env python3
"""
予人玫瑰 — 员工档案系统
每个员工有独立职责、KPI、工作流
"""
import sqlite3, json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "rose_crm.db"

class StaffManager:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT,
                avatar TEXT,
                bio TEXT,
                skills TEXT,
                kpi TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS staff_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER,
                action TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES staff(id)
            );
        """)
        self.conn.commit()

    def add_staff(self, name, role, **kw):
        cur = self.conn.execute("""
            INSERT INTO staff (name,role,department,avatar,bio,skills,kpi)
            VALUES (?,?,?,?,?,?,?)
        """, (name, role, kw.get('department'), kw.get('avatar'),
              kw.get('bio'), json.dumps(kw.get('skills',[]), ensure_ascii=False),
              json.dumps(kw.get('kpi',{}), ensure_ascii=False)))
        self.conn.commit()
        sid = cur.lastrowid
        return sid

    def log(self, staff_id, action, detail):
        self.conn.execute("INSERT INTO staff_log (staff_id,action,detail) VALUES (?,?,?)",
            (staff_id, action, detail))
        self.conn.commit()

    def list_staff(self):
        rows = self.conn.execute("SELECT * FROM staff WHERE status='active'").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['skills'] = json.loads(d.get('skills','[]'))
            d['kpi'] = json.loads(d.get('kpi','{}'))
            result.append(d)
        return result

    def get_staff(self, sid):
        r = self.conn.execute("SELECT * FROM staff WHERE id=?", (sid,)).fetchone()
        if not r: return None
        d = dict(r)
        d['skills'] = json.loads(d.get('skills','[]'))
        d['kpi'] = json.loads(d.get('kpi','{}'))
        return d

    def get_logs(self, staff_id, limit=20):
        rows = self.conn.execute("SELECT * FROM staff_log WHERE staff_id=? ORDER BY created_at DESC LIMIT ?",
            (staff_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()

# ═══ 员工定义 ═══
STAFF_DEFS = [
    {
        "name": "苏婉清",
        "role": "品牌运营总监",
        "department": "品牌宣传部",
        "avatar": "👩‍💼",
        "bio": "8年品牌运营经验，擅长内容策划与社群裂变。坚信'好内容是最好的营销'。负责予人玫瑰的整体品牌调性、公众号/小红书/抖音全渠道运营，以及公益IP打造。",
        "skills": ["内容策划", "社群运营", "KOL合作", "数据分析", "活动策划", "文案撰写", "短视频策划", "危机公关"],
        "kpi": {"月涨粉目标": 2000, "月发文量": 30, "社群活跃率": 0.6, "爆款文章率": 0.2, "品牌认知度": "问卷追踪"},
    },
    {
        "name": "林小棠",
        "role": "视觉设计师",
        "department": "设计部",
        "avatar": "🎨",
        "bio": "4年平面/UI设计经验，专注女性审美。负责予人玫瑰全品牌视觉：Logo、VI体系、公众号排版、小红书封面、品牌周边设计、3D打印产品外观。",
        "skills": ["平面设计", "UI/UX", "品牌VI", "插画", "动效设计", "3D建模", "包装设计", "字体设计"],
        "kpi": {"月产出设计稿": 40, "品牌统一度": "视觉规范100%遵循", "周边产品上架": "3款/月"},
    },
    {
        "name": "陈星辰",
        "role": "全栈工程师",
        "department": "技术部",
        "avatar": "💻",
        "bio": "6年全栈开发经验，Flask/React/Flutter全栈。负责予人玫瑰技术基础设施：CRM系统开发维护、小程序开发、3D打印自动化流程、数据看板。",
        "skills": ["Python", "Flask", "React", "Flutter", "SQLite", "3D建模(OpenSCAD)", "自动化脚本", "API设计"],
        "kpi": {"系统可用率": 0.999, "月功能交付": 8, "Bug修复时效": "4小时内", "自动化覆盖率": 0.8},
    },
    {
        "name": "赵明远",
        "role": "财务经理",
        "department": "财务部",
        "avatar": "📊",
        "bio": "CPA持证，5年创业公司财务管理经验。负责予人玫瑰全盘财务：预算编制、收支管理、税务合规、成本控制、变现模型优化。",
        "skills": ["财务规划", "税务合规", "成本控制", "预算管理", "数据分析", "融资对接", "记账报税", "变现模型"],
        "kpi": {"月度预算偏差": "<10%", "现金流健康": "始终>3个月运营成本", "税务合规": "零违规"},
    },
    {
        "name": "沈思语",
        "role": "内容创作者",
        "department": "品牌宣传部",
        "avatar": "✍️",
        "bio": "自由撰稿人，3年情感类内容创作经验，文章累计阅读量500万+。负责予人玫瑰公众号/小红书/抖音的日常内容创作，擅长将品牌价值观融入故事。",
        "skills": ["情感写作", "故事叙述", "爆款标题", "SEO优化", "短视频脚本", "用户心理", "互动话术", "热点追踪"],
        "kpi": {"月产出文章": 25, "平均阅读量": ">500", "爆款率": ">15%", "互动率": ">5%"},
    },
    {
        "name": "周知然",
        "role": "社群运营专员",
        "department": "品牌宣传部",
        "avatar": "💬",
        "bio": "2年社群运营经验，曾管理5个万人社群。负责予人玫瑰微信群的日常运营、用户关系维护、付费社群转化、用户反馈收集。",
        "skills": ["社群管理", "用户运营", "转化话术", "活动策划", "用户画像", "裂变增长", "危机处理", "数据分析"],
        "kpi": {"月新增群成员": 200, "群活跃率": ">40%", "付费转化率": ">20%", "用户满意度": ">4.5/5"},
    },
]

if __name__ == "__main__":
    sm = StaffManager()
    existing = sm.conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
    if existing == 0:
        for s in STAFF_DEFS:
            sid = sm.add_staff(**s)
            sm.log(sid, "入职", f"{s['role']}加入予人玫瑰团队")
        print(f"✓ {len(STAFF_DEFS)}名员工已入职")
    else:
        print(f"已有{existing}名员工")

    for s in sm.list_staff():
        print(f"\n{s['avatar']} {s['name']} — {s['role']} ({s['department']})")
        print(f"   {s['bio'][:60]}...")
        print(f"   技能: {', '.join(s['skills'][:5])}...")
