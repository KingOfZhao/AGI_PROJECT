#!/usr/bin/env python3
"""
予人玫瑰 CRM系统 - 完整实现
基于OpenClaw对话生成

模块:
- M01 客户管理
- M02 任务管理
- M03 跟进记录
- M04 统计分析
- M05 反馈收集
- M06 数据导出
- M07 系统设置
"""

import os
import sys
import json
import sqlite3
import csv
import io
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any

# Flask (可选依赖)
try:
    from flask import Flask, request, jsonify, send_file, g
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    Flask = None

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "rose_crm.db"


# ═══════════════════════════════════════════════════════════════
# 数据库层
# ═══════════════════════════════════════════════════════════════

class CRMDatabase:
    """CRM数据库"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库"""
        conn = self._get_conn()
        conn.executescript("""
            -- 客户表
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                source TEXT DEFAULT 'direct',
                status TEXT DEFAULT 'active',
                notes TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 任务表
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                customer_id INTEGER,
                assigned_to TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                due_date DATE,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            
            -- 跟进记录表
            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                task_id INTEGER,
                type TEXT DEFAULT 'call',
                content TEXT,
                result TEXT,
                next_action TEXT,
                next_date DATE,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            
            -- 反馈表
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                customer_id INTEGER,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            
            -- 用户表
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                api_key TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 系统配置表
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 索引
            CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_customer ON tasks(customer_id);
            CREATE INDEX IF NOT EXISTS idx_followups_customer ON followups(customer_id);
        """)
        conn.commit()
        conn.close()
    
    # ==================== 客户操作 ====================
    
    def create_customer(self, name: str, **kwargs) -> int:
        """创建客户"""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO customers (name, company, phone, email, address, source, status, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            kwargs.get("company"),
            kwargs.get("phone"),
            kwargs.get("email"),
            kwargs.get("address"),
            kwargs.get("source", "direct"),
            kwargs.get("status", "active"),
            kwargs.get("notes"),
            json.dumps(kwargs.get("tags", []))
        ))
        conn.commit()
        customer_id = cursor.lastrowid
        conn.close()
        return customer_id
    
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """获取客户"""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
    
    def list_customers(self, status: str = None, search: str = None, 
                       limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出客户"""
        conn = self._get_conn()
        query = "SELECT * FROM customers WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if search:
            query += " AND (name LIKE ? OR company LIKE ? OR phone LIKE ?)"
            params.extend([f"%{search}%"] * 3)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_customer(self, customer_id: int, **kwargs) -> bool:
        """更新客户"""
        if not kwargs:
            return False
        
        conn = self._get_conn()
        fields = []
        values = []
        
        for key in ["name", "company", "phone", "email", "address", "source", "status", "notes"]:
            if key in kwargs:
                fields.append(f"{key} = ?")
                values.append(kwargs[key])
        
        if "tags" in kwargs:
            fields.append("tags = ?")
            values.append(json.dumps(kwargs["tags"]))
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(customer_id)
        
        conn.execute(f"UPDATE customers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0
    
    def delete_customer(self, customer_id: int) -> bool:
        """删除客户（软删除）"""
        return self.update_customer(customer_id, status="deleted")
    
    # ==================== 任务操作 ====================
    
    def create_task(self, title: str, customer_id: int = None, **kwargs) -> int:
        """创建任务"""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO tasks (title, description, customer_id, assigned_to, priority, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            kwargs.get("description"),
            customer_id,
            kwargs.get("assigned_to"),
            kwargs.get("priority", "medium"),
            kwargs.get("status", "pending"),
            kwargs.get("due_date")
        ))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return task_id
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务"""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT t.*, c.name as customer_name
            FROM tasks t
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE t.id = ?
        """, (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
    
    def list_tasks(self, status: str = None, customer_id: int = None,
                   priority: str = None, limit: int = 100) -> List[Dict]:
        """列出任务"""
        conn = self._get_conn()
        query = """
            SELECT t.*, c.name as customer_name
            FROM tasks t
            LEFT JOIN customers c ON t.customer_id = c.id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND t.status = ?"
            params.append(status)
        
        if customer_id:
            query += " AND t.customer_id = ?"
            params.append(customer_id)
        
        if priority:
            query += " AND t.priority = ?"
            params.append(priority)
        
        query += " ORDER BY t.due_date ASC, t.priority DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """更新任务"""
        if not kwargs:
            return False
        
        conn = self._get_conn()
        fields = []
        values = []
        
        for key in ["title", "description", "assigned_to", "priority", "status", "due_date"]:
            if key in kwargs:
                fields.append(f"{key} = ?")
                values.append(kwargs[key])
        
        if kwargs.get("status") == "completed":
            fields.append("completed_at = CURRENT_TIMESTAMP")
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0
    
    def complete_task(self, task_id: int) -> bool:
        """完成任务"""
        return self.update_task(task_id, status="completed")
    
    # ==================== 跟进记录 ====================
    
    def create_followup(self, customer_id: int, content: str, **kwargs) -> int:
        """创建跟进记录"""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO followups (customer_id, task_id, type, content, result, next_action, next_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            kwargs.get("task_id"),
            kwargs.get("type", "call"),
            content,
            kwargs.get("result"),
            kwargs.get("next_action"),
            kwargs.get("next_date"),
            kwargs.get("created_by")
        ))
        conn.commit()
        followup_id = cursor.lastrowid
        conn.close()
        return followup_id
    
    def list_followups(self, customer_id: int = None, task_id: int = None,
                       limit: int = 50) -> List[Dict]:
        """列出跟进记录"""
        conn = self._get_conn()
        query = """
            SELECT f.*, c.name as customer_name
            FROM followups f
            LEFT JOIN customers c ON f.customer_id = c.id
            WHERE 1=1
        """
        params = []
        
        if customer_id:
            query += " AND f.customer_id = ?"
            params.append(customer_id)
        
        if task_id:
            query += " AND f.task_id = ?"
            params.append(task_id)
        
        query += " ORDER BY f.created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ==================== 反馈 ====================
    
    def create_feedback(self, task_id: int, rating: int, comment: str = None,
                        customer_id: int = None) -> int:
        """创建反馈"""
        conn = self._get_conn()
        cursor = conn.execute("""
            INSERT INTO feedbacks (task_id, customer_id, rating, comment)
            VALUES (?, ?, ?, ?)
        """, (task_id, customer_id, rating, comment))
        conn.commit()
        feedback_id = cursor.lastrowid
        conn.close()
        return feedback_id
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """获取反馈统计"""
        conn = self._get_conn()
        
        rating_dist = conn.execute("""
            SELECT rating, COUNT(*) as count
            FROM feedbacks
            WHERE rating IS NOT NULL
            GROUP BY rating
            ORDER BY rating
        """).fetchall()
        
        avg = conn.execute(
            "SELECT AVG(rating) as avg FROM feedbacks WHERE rating IS NOT NULL"
        ).fetchone()["avg"] or 0
        
        total = conn.execute("SELECT COUNT(*) as cnt FROM feedbacks").fetchone()["cnt"]
        
        conn.close()
        
        return {
            "total": total,
            "average_rating": round(avg, 2),
            "rating_distribution": {r["rating"]: r["count"] for r in rating_dist}
        }
    
    # ==================== 统计分析 ====================
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表盘统计"""
        conn = self._get_conn()
        
        stats = {
            "customers": {
                "total": conn.execute("SELECT COUNT(*) FROM customers WHERE status != 'deleted'").fetchone()[0],
                "active": conn.execute("SELECT COUNT(*) FROM customers WHERE status = 'active'").fetchone()[0],
                "new_this_month": conn.execute("""
                    SELECT COUNT(*) FROM customers 
                    WHERE created_at >= date('now', 'start of month')
                """).fetchone()[0]
            },
            "tasks": {
                "total": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                "pending": conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'").fetchone()[0],
                "in_progress": conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'").fetchone()[0],
                "completed": conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'").fetchone()[0],
                "overdue": conn.execute("""
                    SELECT COUNT(*) FROM tasks 
                    WHERE status != 'completed' AND due_date < date('now')
                """).fetchone()[0]
            },
            "followups": {
                "total": conn.execute("SELECT COUNT(*) FROM followups").fetchone()[0],
                "this_week": conn.execute("""
                    SELECT COUNT(*) FROM followups 
                    WHERE created_at >= date('now', '-7 days')
                """).fetchone()[0]
            },
            "feedbacks": self.get_feedback_stats()
        }
        
        conn.close()
        return stats
    
    # ==================== 数据导出 ====================
    
    def export_customers_csv(self) -> str:
        """导出客户CSV"""
        customers = self.list_customers(limit=10000)
        
        output = io.StringIO()
        if customers:
            writer = csv.DictWriter(output, fieldnames=customers[0].keys())
            writer.writeheader()
            writer.writerows(customers)
        
        return output.getvalue()
    
    def export_tasks_csv(self, status: str = None) -> str:
        """导出任务CSV"""
        tasks = self.list_tasks(status=status, limit=10000)
        
        output = io.StringIO()
        if tasks:
            writer = csv.DictWriter(output, fieldnames=tasks[0].keys())
            writer.writeheader()
            writer.writerows(tasks)
        
        return output.getvalue()


# ═══════════════════════════════════════════════════════════════
# CLI 接口
# ═══════════════════════════════════════════════════════════════

class CRMCLI:
    """CRM命令行接口"""
    
    def __init__(self):
        self.db = CRMDatabase()
    
    def run(self, args: List[str]):
        """运行CLI命令"""
        if not args:
            self.show_help()
            return
        
        cmd = args[0]
        params = args[1:]
        
        commands = {
            "customer": self.handle_customer,
            "task": self.handle_task,
            "followup": self.handle_followup,
            "stats": self.handle_stats,
            "export": self.handle_export,
            "help": self.show_help,
        }
        
        handler = commands.get(cmd)
        if handler:
            handler(params)
        else:
            print(f"未知命令: {cmd}")
            self.show_help()
    
    def handle_customer(self, params: List[str]):
        """处理客户命令"""
        if not params:
            print("用法: customer <add|list|get|update|delete> [参数]")
            return
        
        action = params[0]
        
        if action == "add":
            if len(params) < 2:
                print("用法: customer add <名称> [--company=] [--phone=] [--email=]")
                return
            
            name = params[1]
            kwargs = {}
            for p in params[2:]:
                if p.startswith("--"):
                    key, _, value = p[2:].partition("=")
                    kwargs[key] = value
            
            customer_id = self.db.create_customer(name, **kwargs)
            print(f"✓ 客户创建成功 (ID: {customer_id})")
        
        elif action == "list":
            status = None
            search = None
            for p in params[1:]:
                if p.startswith("--status="):
                    status = p[9:]
                elif p.startswith("--search="):
                    search = p[9:]
            
            customers = self.db.list_customers(status=status, search=search, limit=20)
            print(f"\n{'ID':<5} {'名称':<15} {'公司':<20} {'电话':<15} {'状态':<10}")
            print("-" * 70)
            for c in customers:
                print(f"{c['id']:<5} {c['name']:<15} {c['company'] or '-':<20} {c['phone'] or '-':<15} {c['status']:<10}")
        
        elif action == "get":
            if len(params) < 2:
                print("用法: customer get <ID>")
                return
            
            customer = self.db.get_customer(int(params[1]))
            if customer:
                print(json.dumps(customer, indent=2, ensure_ascii=False, default=str))
            else:
                print("客户不存在")
        
        elif action == "update":
            if len(params) < 3:
                print("用法: customer update <ID> --field=value ...")
                return
            
            customer_id = int(params[1])
            kwargs = {}
            for p in params[2:]:
                if p.startswith("--"):
                    key, _, value = p[2:].partition("=")
                    kwargs[key] = value
            
            if self.db.update_customer(customer_id, **kwargs):
                print("✓ 客户更新成功")
            else:
                print("更新失败")
        
        elif action == "delete":
            if len(params) < 2:
                print("用法: customer delete <ID>")
                return
            
            if self.db.delete_customer(int(params[1])):
                print("✓ 客户已删除")
            else:
                print("删除失败")
    
    def handle_task(self, params: List[str]):
        """处理任务命令"""
        if not params:
            print("用法: task <add|list|get|update|complete> [参数]")
            return
        
        action = params[0]
        
        if action == "add":
            if len(params) < 2:
                print("用法: task add <标题> [--customer_id=] [--priority=] [--due_date=]")
                return
            
            title = params[1]
            kwargs = {}
            customer_id = None
            for p in params[2:]:
                if p.startswith("--customer_id="):
                    customer_id = int(p[14:])
                elif p.startswith("--"):
                    key, _, value = p[2:].partition("=")
                    kwargs[key] = value
            
            task_id = self.db.create_task(title, customer_id, **kwargs)
            print(f"✓ 任务创建成功 (ID: {task_id})")
        
        elif action == "list":
            status = None
            for p in params[1:]:
                if p.startswith("--status="):
                    status = p[9:]
            
            tasks = self.db.list_tasks(status=status, limit=20)
            print(f"\n{'ID':<5} {'标题':<25} {'客户':<15} {'优先级':<8} {'状态':<10} {'截止日期':<12}")
            print("-" * 80)
            for t in tasks:
                print(f"{t['id']:<5} {t['title'][:23]:<25} {(t['customer_name'] or '-')[:13]:<15} {t['priority']:<8} {t['status']:<10} {t['due_date'] or '-':<12}")
        
        elif action == "complete":
            if len(params) < 2:
                print("用法: task complete <ID>")
                return
            
            if self.db.complete_task(int(params[1])):
                print("✓ 任务已完成")
            else:
                print("操作失败")
    
    def handle_followup(self, params: List[str]):
        """处理跟进记录命令"""
        if not params:
            print("用法: followup <add|list> [参数]")
            return
        
        action = params[0]
        
        if action == "add":
            if len(params) < 3:
                print("用法: followup add <客户ID> <内容> [--type=call|visit|email]")
                return
            
            customer_id = int(params[1])
            content = params[2]
            kwargs = {}
            for p in params[3:]:
                if p.startswith("--"):
                    key, _, value = p[2:].partition("=")
                    kwargs[key] = value
            
            followup_id = self.db.create_followup(customer_id, content, **kwargs)
            print(f"✓ 跟进记录创建成功 (ID: {followup_id})")
        
        elif action == "list":
            customer_id = None
            for p in params[1:]:
                if p.startswith("--customer_id="):
                    customer_id = int(p[14:])
            
            followups = self.db.list_followups(customer_id=customer_id, limit=20)
            print(f"\n{'ID':<5} {'客户':<15} {'类型':<8} {'内容':<40} {'时间':<20}")
            print("-" * 90)
            for f in followups:
                print(f"{f['id']:<5} {f['customer_name'] or '-':<15} {f['type']:<8} {f['content'][:38]:<40} {f['created_at'][:19]:<20}")
    
    def handle_stats(self, params: List[str]):
        """处理统计命令"""
        stats = self.db.get_dashboard_stats()
        
        print("\n═══════════════════════════════════════")
        print("           予人玫瑰 CRM 统计")
        print("═══════════════════════════════════════")
        
        print("\n📊 客户统计:")
        print(f"  总客户数: {stats['customers']['total']}")
        print(f"  活跃客户: {stats['customers']['active']}")
        print(f"  本月新增: {stats['customers']['new_this_month']}")
        
        print("\n📋 任务统计:")
        print(f"  总任务数: {stats['tasks']['total']}")
        print(f"  待处理: {stats['tasks']['pending']}")
        print(f"  进行中: {stats['tasks']['in_progress']}")
        print(f"  已完成: {stats['tasks']['completed']}")
        print(f"  已逾期: {stats['tasks']['overdue']}")
        
        print("\n📝 跟进统计:")
        print(f"  总记录数: {stats['followups']['total']}")
        print(f"  本周跟进: {stats['followups']['this_week']}")
        
        print("\n⭐ 反馈统计:")
        print(f"  总反馈数: {stats['feedbacks']['total']}")
        print(f"  平均评分: {stats['feedbacks']['average_rating']}")
    
    def handle_export(self, params: List[str]):
        """处理导出命令"""
        if not params:
            print("用法: export <customers|tasks> [--output=文件名]")
            return
        
        target = params[0]
        output_file = None
        for p in params[1:]:
            if p.startswith("--output="):
                output_file = p[9:]
        
        if target == "customers":
            csv_content = self.db.export_customers_csv()
            output_file = output_file or f"customers_{datetime.now().strftime('%Y%m%d')}.csv"
        elif target == "tasks":
            csv_content = self.db.export_tasks_csv()
            output_file = output_file or f"tasks_{datetime.now().strftime('%Y%m%d')}.csv"
        else:
            print(f"未知导出目标: {target}")
            return
        
        Path(output_file).write_text(csv_content, encoding="utf-8-sig")
        print(f"✓ 已导出到: {output_file}")
    
    def show_help(self, params=None):
        """显示帮助"""
        print("""
予人玫瑰 CRM系统

用法: python rose_crm.py <命令> [参数]

命令:
  customer   客户管理 (add|list|get|update|delete)
  task       任务管理 (add|list|get|update|complete)
  followup   跟进记录 (add|list)
  stats      查看统计
  export     导出数据 (customers|tasks)
  help       显示帮助

示例:
  python rose_crm.py customer add "张三" --company="ABC公司" --phone="13800138000"
  python rose_crm.py customer list --status=active
  python rose_crm.py task add "跟进客户需求" --customer_id=1 --priority=high
  python rose_crm.py task list --status=pending
  python rose_crm.py followup add 1 "电话沟通，客户有意向" --type=call
  python rose_crm.py stats
  python rose_crm.py export customers --output=my_customers.csv
        """)


# ═══════════════════════════════════════════════════════════════
# Flask API (可选)
# ═══════════════════════════════════════════════════════════════

def create_app() -> Optional[Flask]:
    """创建Flask应用"""
    if not HAS_FLASK:
        return None
    
    app = Flask(__name__)
    db = CRMDatabase()
    
    @app.route("/api/customers", methods=["GET"])
    def list_customers():
        customers = db.list_customers(
            status=request.args.get("status"),
            search=request.args.get("search"),
            limit=int(request.args.get("limit", 100))
        )
        return jsonify({"customers": customers})
    
    @app.route("/api/customers", methods=["POST"])
    def create_customer():
        data = request.get_json() or {}
        if not data.get("name"):
            return jsonify({"error": "名称必填"}), 400
        
        customer_id = db.create_customer(**data)
        return jsonify({"id": customer_id}), 201
    
    @app.route("/api/customers/<int:customer_id>", methods=["GET"])
    def get_customer(customer_id):
        customer = db.get_customer(customer_id)
        if not customer:
            return jsonify({"error": "客户不存在"}), 404
        return jsonify(customer)
    
    @app.route("/api/tasks", methods=["GET"])
    def list_tasks():
        tasks = db.list_tasks(
            status=request.args.get("status"),
            customer_id=request.args.get("customer_id", type=int),
            limit=int(request.args.get("limit", 100))
        )
        return jsonify({"tasks": tasks})
    
    @app.route("/api/tasks", methods=["POST"])
    def create_task():
        data = request.get_json() or {}
        if not data.get("title"):
            return jsonify({"error": "标题必填"}), 400
        
        task_id = db.create_task(**data)
        return jsonify({"id": task_id}), 201
    
    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        return jsonify(db.get_dashboard_stats())
    
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "rose_crm"})
    
    return app


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        app = create_app()
        if app:
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 5010
            print(f"启动 予人玫瑰 CRM 服务器: http://localhost:{port}")
            app.run(host="0.0.0.0", port=port, debug=True)
        else:
            print("Flask未安装，无法启动服务器")
    else:
        cli = CRMCLI()
        cli.run(sys.argv[1:])
