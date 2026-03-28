#!/usr/bin/env python3
"""
多租户计费系统 - OpenClaw 商业化基础设施

功能:
1. 租户管理 - 创建/管理/隔离租户
2. 用量计量 - API调用/Token消耗/存储用量
3. 计费账单 - 按量计费/订阅计费/账单生成
4. 配额控制 - 限流/配额/超限处理

用法:
    from tenant_billing import TenantManager, BillingEngine
    tm = TenantManager()
    tenant = tm.create_tenant("company_a", tier="pro")
    billing = BillingEngine(tenant.id)
    billing.record_usage("api_call", 1)
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "tenant_billing.db"
DB_PATH.parent.mkdir(exist_ok=True)


# ==================== 枚举和常量 ====================

class TenantTier(Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    INDUSTRIAL = "industrial"


class UsageType(Enum):
    API_CALL = "api_call"
    TOKEN_INPUT = "token_input"
    TOKEN_OUTPUT = "token_output"
    SKILL_EXECUTION = "skill_execution"
    CODE_EXECUTION = "code_execution"
    STORAGE_MB = "storage_mb"
    DEDUCTION_ROUND = "deduction_round"


# 套餐配置
TIER_CONFIG = {
    TenantTier.FREE: {
        "name": "免费版",
        "price_monthly": 0,
        "limits": {
            "api_calls_per_day": 100,
            "tokens_per_month": 100000,
            "skill_executions_per_day": 20,
            "code_executions_per_day": 10,
            "storage_mb": 100,
            "deduction_rounds_per_month": 10,
        },
        "features": ["basic_chat", "skill_search"]
    },
    TenantTier.STARTER: {
        "name": "入门版",
        "price_monthly": 99,
        "limits": {
            "api_calls_per_day": 1000,
            "tokens_per_month": 1000000,
            "skill_executions_per_day": 200,
            "code_executions_per_day": 100,
            "storage_mb": 1000,
            "deduction_rounds_per_month": 100,
        },
        "features": ["basic_chat", "skill_search", "code_agent", "crm_basic"]
    },
    TenantTier.PRO: {
        "name": "专业版",
        "price_monthly": 399,
        "limits": {
            "api_calls_per_day": 10000,
            "tokens_per_month": 10000000,
            "skill_executions_per_day": 2000,
            "code_executions_per_day": 1000,
            "storage_mb": 10000,
            "deduction_rounds_per_month": 1000,
        },
        "features": ["basic_chat", "skill_search", "code_agent", "crm_full", "workflow", "api_access"]
    },
    TenantTier.ENTERPRISE: {
        "name": "企业版",
        "price_monthly": 0,  # 按需定价
        "limits": {
            "api_calls_per_day": -1,  # 无限
            "tokens_per_month": -1,
            "skill_executions_per_day": -1,
            "code_executions_per_day": -1,
            "storage_mb": -1,
            "deduction_rounds_per_month": -1,
        },
        "features": ["all", "private_deployment", "sla", "dedicated_support"]
    },
    TenantTier.INDUSTRIAL: {
        "name": "工业版",
        "price_monthly": 0,  # 按件计费
        "price_per_piece": 5,  # 每件5元
        "limits": {
            "api_calls_per_day": -1,
            "tokens_per_month": -1,
            "skill_executions_per_day": -1,
            "code_executions_per_day": -1,
            "storage_mb": 50000,
            "deduction_rounds_per_month": -1,
        },
        "features": ["all", "deduction_engine", "cad_integration", "precision_guarantee"]
    },
}


# ==================== 数据模型 ====================

@dataclass
class Tenant:
    """租户"""
    id: str
    name: str
    tier: TenantTier
    api_key: str
    created_at: str
    status: str = "active"  # active, suspended, deleted
    contact_email: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Tenant':
        return cls(
            id=row[0],
            name=row[1],
            tier=TenantTier(row[2]),
            api_key=row[3],
            created_at=row[4],
            status=row[5],
            contact_email=row[6] or "",
            metadata=json.loads(row[7]) if row[7] else {}
        )


@dataclass
class UsageRecord:
    """用量记录"""
    tenant_id: str
    usage_type: UsageType
    amount: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["usage_type"] = self.usage_type.value
        return d


@dataclass
class Invoice:
    """账单"""
    id: str
    tenant_id: str
    period_start: str
    period_end: str
    total_amount: float
    items: List[Dict[str, Any]]
    status: str = "pending"  # pending, paid, overdue
    created_at: str = ""
    paid_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


# ==================== 数据库管理 ====================

class Database:
    """数据库管理"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    contact_email TEXT,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                );
                
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    items TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    paid_at TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_records(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp);
                CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id);
            """)
    
    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


# ==================== 租户管理 ====================

class TenantManager:
    """租户管理器"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def create_tenant(self, name: str, tier: TenantTier = TenantTier.FREE,
                      contact_email: str = "", metadata: Dict = None) -> Tenant:
        """创建租户"""
        tenant_id = f"tenant_{secrets.token_hex(8)}"
        api_key = f"sk_{secrets.token_hex(24)}"
        created_at = datetime.now().isoformat()
        
        tenant = Tenant(
            id=tenant_id,
            name=name,
            tier=tier,
            api_key=api_key,
            created_at=created_at,
            contact_email=contact_email,
            metadata=metadata or {}
        )
        
        with self.db._connect() as conn:
            conn.execute("""
                INSERT INTO tenants (id, name, tier, api_key, created_at, status, contact_email, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant.id, tenant.name, tenant.tier.value, tenant.api_key,
                tenant.created_at, tenant.status, tenant.contact_email,
                json.dumps(tenant.metadata)
            ))
        
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
            ).fetchone()
            
            if row:
                return Tenant.from_row(row)
        return None
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """通过API Key获取租户"""
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE api_key = ?", (api_key,)
            ).fetchone()
            
            if row:
                return Tenant.from_row(row)
        return None
    
    def list_tenants(self, status: str = None) -> List[Tenant]:
        """列出租户"""
        with self.db._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM tenants WHERE status = ?", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM tenants").fetchall()
            
            return [Tenant.from_row(row) for row in rows]
    
    def update_tier(self, tenant_id: str, new_tier: TenantTier) -> bool:
        """升级/降级套餐"""
        with self.db._connect() as conn:
            conn.execute(
                "UPDATE tenants SET tier = ? WHERE id = ?",
                (new_tier.value, tenant_id)
            )
            return conn.total_changes > 0
    
    def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户"""
        with self.db._connect() as conn:
            conn.execute(
                "UPDATE tenants SET status = 'suspended' WHERE id = ?",
                (tenant_id,)
            )
            return conn.total_changes > 0
    
    def activate_tenant(self, tenant_id: str) -> bool:
        """激活租户"""
        with self.db._connect() as conn:
            conn.execute(
                "UPDATE tenants SET status = 'active' WHERE id = ?",
                (tenant_id,)
            )
            return conn.total_changes > 0


# ==================== 计费引擎 ====================

class BillingEngine:
    """计费引擎"""
    
    def __init__(self, db: Database = None):
        self.db = db or Database()
        self.tenant_manager = TenantManager(self.db)
    
    def record_usage(self, tenant_id: str, usage_type: UsageType, 
                     amount: float, metadata: Dict = None) -> bool:
        """记录用量"""
        timestamp = datetime.now().isoformat()
        
        with self.db._connect() as conn:
            conn.execute("""
                INSERT INTO usage_records (tenant_id, usage_type, amount, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tenant_id, usage_type.value, amount, timestamp,
                json.dumps(metadata) if metadata else None
            ))
        
        return True
    
    def get_usage(self, tenant_id: str, usage_type: UsageType = None,
                  start_date: str = None, end_date: str = None) -> List[UsageRecord]:
        """获取用量记录"""
        query = "SELECT tenant_id, usage_type, amount, timestamp, metadata FROM usage_records WHERE tenant_id = ?"
        params = [tenant_id]
        
        if usage_type:
            query += " AND usage_type = ?"
            params.append(usage_type.value)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        with self.db._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            
            return [
                UsageRecord(
                    tenant_id=row[0],
                    usage_type=UsageType(row[1]),
                    amount=row[2],
                    timestamp=row[3],
                    metadata=json.loads(row[4]) if row[4] else {}
                )
                for row in rows
            ]
    
    def get_usage_summary(self, tenant_id: str, period: str = "month") -> Dict[str, float]:
        """获取用量汇总"""
        now = datetime.now()
        
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0).isoformat()
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
        else:
            start_date = None
        
        query = """
            SELECT usage_type, SUM(amount) as total
            FROM usage_records
            WHERE tenant_id = ?
        """
        params = [tenant_id]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        query += " GROUP BY usage_type"
        
        with self.db._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            
            return {row[0]: row[1] for row in rows}
    
    def check_quota(self, tenant_id: str, usage_type: UsageType, amount: float = 1) -> Dict[str, Any]:
        """检查配额"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return {"allowed": False, "reason": "租户不存在"}
        
        if tenant.status != "active":
            return {"allowed": False, "reason": f"租户状态: {tenant.status}"}
        
        config = TIER_CONFIG.get(tenant.tier, {})
        limits = config.get("limits", {})
        
        # 映射用量类型到配额键
        limit_map = {
            UsageType.API_CALL: "api_calls_per_day",
            UsageType.TOKEN_INPUT: "tokens_per_month",
            UsageType.TOKEN_OUTPUT: "tokens_per_month",
            UsageType.SKILL_EXECUTION: "skill_executions_per_day",
            UsageType.CODE_EXECUTION: "code_executions_per_day",
            UsageType.DEDUCTION_ROUND: "deduction_rounds_per_month",
        }
        
        limit_key = limit_map.get(usage_type)
        if not limit_key:
            return {"allowed": True, "reason": "无配额限制"}
        
        limit = limits.get(limit_key, -1)
        if limit == -1:
            return {"allowed": True, "reason": "无限额度"}
        
        # 获取当前用量
        period = "day" if "per_day" in limit_key else "month"
        summary = self.get_usage_summary(tenant_id, period)
        current = summary.get(usage_type.value, 0)
        
        if current + amount > limit:
            return {
                "allowed": False,
                "reason": f"超出配额限制 ({current}/{limit})",
                "current": current,
                "limit": limit,
                "remaining": max(0, limit - current)
            }
        
        return {
            "allowed": True,
            "current": current,
            "limit": limit,
            "remaining": limit - current - amount
        }
    
    def generate_invoice(self, tenant_id: str, period_start: str, 
                         period_end: str) -> Optional[Invoice]:
        """生成账单"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return None
        
        config = TIER_CONFIG.get(tenant.tier, {})
        items = []
        total = 0.0
        
        # 基础订阅费
        monthly_price = config.get("price_monthly", 0)
        if monthly_price > 0:
            items.append({
                "type": "subscription",
                "description": f"{config['name']} 月度订阅",
                "amount": monthly_price
            })
            total += monthly_price
        
        # 按量计费（工业版）
        if tenant.tier == TenantTier.INDUSTRIAL:
            summary = self.get_usage_summary(tenant_id, "month")
            pieces = summary.get("deduction_round", 0)
            price_per_piece = config.get("price_per_piece", 5)
            piece_cost = pieces * price_per_piece
            
            if piece_cost > 0:
                items.append({
                    "type": "usage",
                    "description": f"推演件数: {int(pieces)} × ¥{price_per_piece}",
                    "amount": piece_cost
                })
                total += piece_cost
        
        # 超额计费
        # TODO: 实现超额计费逻辑
        
        invoice_id = f"inv_{secrets.token_hex(8)}"
        invoice = Invoice(
            id=invoice_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            total_amount=total,
            items=items,
            created_at=datetime.now().isoformat()
        )
        
        with self.db._connect() as conn:
            conn.execute("""
                INSERT INTO invoices (id, tenant_id, period_start, period_end, total_amount, items, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice.id, invoice.tenant_id, invoice.period_start,
                invoice.period_end, invoice.total_amount,
                json.dumps(invoice.items), invoice.status, invoice.created_at
            ))
        
        return invoice
    
    def get_invoices(self, tenant_id: str) -> List[Invoice]:
        """获取账单列表"""
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM invoices WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,)
            ).fetchall()
            
            return [
                Invoice(
                    id=row[0],
                    tenant_id=row[1],
                    period_start=row[2],
                    period_end=row[3],
                    total_amount=row[4],
                    items=json.loads(row[5]),
                    status=row[6],
                    created_at=row[7],
                    paid_at=row[8] or ""
                )
                for row in rows
            ]


# ==================== 用量中间件 ====================

class UsageMiddleware:
    """用量计量中间件 - 供其他模块调用"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.billing = BillingEngine()
            cls._instance.enabled = True
        return cls._instance
    
    def track(self, tenant_id: str, usage_type: UsageType, amount: float = 1,
              metadata: Dict = None) -> Dict[str, Any]:
        """追踪用量并检查配额"""
        if not self.enabled:
            return {"allowed": True, "tracked": False}
        
        # 检查配额
        quota = self.billing.check_quota(tenant_id, usage_type, amount)
        
        if not quota["allowed"]:
            return quota
        
        # 记录用量
        self.billing.record_usage(tenant_id, usage_type, amount, metadata)
        
        return {
            "allowed": True,
            "tracked": True,
            "remaining": quota.get("remaining", -1)
        }
    
    def get_remaining(self, tenant_id: str, usage_type: UsageType) -> float:
        """获取剩余配额"""
        quota = self.billing.check_quota(tenant_id, usage_type, 0)
        return quota.get("remaining", -1)


# ==================== API 装饰器 ====================

def require_quota(usage_type: UsageType, amount: float = 1):
    """配额检查装饰器"""
    def decorator(func):
        def wrapper(*args, tenant_id: str = None, **kwargs):
            if tenant_id is None:
                # 尝试从参数中获取
                tenant_id = kwargs.get("tenant_id") or (args[0] if args else None)
            
            if tenant_id:
                middleware = UsageMiddleware()
                result = middleware.track(tenant_id, usage_type, amount)
                
                if not result["allowed"]:
                    raise PermissionError(f"配额不足: {result.get('reason', '未知原因')}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== CLI ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="多租户计费系统")
    subparsers = parser.add_subparsers(dest="command")
    
    # 创建租户
    create_parser = subparsers.add_parser("create", help="创建租户")
    create_parser.add_argument("name", help="租户名称")
    create_parser.add_argument("--tier", default="free", choices=["free", "starter", "pro", "enterprise", "industrial"])
    create_parser.add_argument("--email", default="", help="联系邮箱")
    
    # 列出租户
    list_parser = subparsers.add_parser("list", help="列出租户")
    
    # 查看用量
    usage_parser = subparsers.add_parser("usage", help="查看用量")
    usage_parser.add_argument("tenant_id", help="租户ID")
    
    # 生成账单
    invoice_parser = subparsers.add_parser("invoice", help="生成账单")
    invoice_parser.add_argument("tenant_id", help="租户ID")
    
    # 记录用量（测试）
    record_parser = subparsers.add_parser("record", help="记录用量")
    record_parser.add_argument("tenant_id", help="租户ID")
    record_parser.add_argument("--type", default="api_call", help="用量类型")
    record_parser.add_argument("--amount", type=float, default=1, help="数量")
    
    args = parser.parse_args()
    
    tm = TenantManager()
    billing = BillingEngine()
    
    if args.command == "create":
        tier = TenantTier(args.tier)
        tenant = tm.create_tenant(args.name, tier, args.email)
        print(f"✓ 租户创建成功")
        print(f"  ID: {tenant.id}")
        print(f"  API Key: {tenant.api_key}")
        print(f"  套餐: {TIER_CONFIG[tier]['name']}")
    
    elif args.command == "list":
        tenants = tm.list_tenants()
        print(f"\n{'ID':<25} {'名称':<15} {'套餐':<10} {'状态':<10}")
        print("-" * 60)
        for t in tenants:
            print(f"{t.id:<25} {t.name:<15} {t.tier.value:<10} {t.status:<10}")
    
    elif args.command == "usage":
        summary = billing.get_usage_summary(args.tenant_id)
        tenant = tm.get_tenant(args.tenant_id)
        
        if not tenant:
            print("租户不存在")
            return
        
        config = TIER_CONFIG.get(tenant.tier, {})
        limits = config.get("limits", {})
        
        print(f"\n租户: {tenant.name} ({tenant.tier.value})")
        print("-" * 40)
        print(f"{'用量类型':<20} {'已用':<10} {'限额':<10}")
        print("-" * 40)
        
        for usage_type, current in summary.items():
            limit = limits.get(f"{usage_type}s_per_day", limits.get(f"{usage_type}s_per_month", -1))
            limit_str = "无限" if limit == -1 else str(limit)
            print(f"{usage_type:<20} {current:<10.0f} {limit_str:<10}")
    
    elif args.command == "invoice":
        now = datetime.now()
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        
        invoice = billing.generate_invoice(args.tenant_id, start, end)
        if invoice:
            print(f"\n账单 ID: {invoice.id}")
            print(f"周期: {invoice.period_start} ~ {invoice.period_end}")
            print("-" * 40)
            for item in invoice.items:
                print(f"  {item['description']}: ¥{item['amount']:.2f}")
            print("-" * 40)
            print(f"总计: ¥{invoice.total_amount:.2f}")
        else:
            print("生成账单失败")
    
    elif args.command == "record":
        usage_type = UsageType(args.type)
        billing.record_usage(args.tenant_id, usage_type, args.amount)
        print(f"✓ 已记录用量: {args.type} × {args.amount}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
