-- ═══ 予人玫瑰 CRM — P0 数据库扩展 ═══
-- 陈星辰 · 技术考核产出

-- 1. 统一用户系统
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    union_id TEXT UNIQUE,          -- 微信UnionID(未来多端打通)
    openid TEXT UNIQUE,            -- 公众号openid
    nickname TEXT,
    avatar_url TEXT,
    phone TEXT,                     -- 脱敏: 138****1234
    gender TEXT DEFAULT 'female',
    birthday TEXT,                  -- 用于生日关怀
    city TEXT,
    tags TEXT DEFAULT '[]',         -- JSON: ["高频互动","潜在付费"]
    source TEXT,                    -- 来源: 公众号搜索/朋友圈转发/小红书/社群邀请
    level TEXT DEFAULT 'free',     -- free/vip/svip
    referrer_id INTEGER,            -- 谁邀请来的(裂变追踪)
    total_spend REAL DEFAULT 0,     -- 累计消费
    points INTEGER DEFAULT 0,       -- 积分
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_active_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(id)
);

-- 2. 数据埋点
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    event TEXT NOT NULL,            -- 事件: page_view/article_read/like/share/join_group/purchase
    page TEXT,                      -- 页面: /article/1 /board /team
    source TEXT,                    -- 来源渠道
    value REAL DEFAULT 0,           -- 数值(如阅读时长)
    extra TEXT,                     -- JSON扩展字段
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(created_at);

-- 3. 分销系统
CREATE TABLE IF NOT EXISTS distributors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    parent_id INTEGER,              -- 上级分销员(支持2级)
    level INTEGER DEFAULT 1,        -- 分销等级: 1=普通 2=高级
    commission_rate REAL DEFAULT 0.10, -- 佣金比例: 10%
    total_earnings REAL DEFAULT 0,
    withdrawable REAL DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (parent_id) REFERENCES distributors(id)
);

-- 4. 佣金流水
CREATE TABLE IF NOT EXISTS commissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    distributor_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    rate REAL NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/settled/withdrawn
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    settled_at TEXT,
    FOREIGN KEY (distributor_id) REFERENCES distributors(id)
);

-- 5. 财务记录
CREATE TABLE IF NOT EXISTS finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,             -- income/expense
    category TEXT NOT NULL,         -- 社群会员/周边销售/送花公益/设计制作/工具订阅
    amount REAL NOT NULL,
    description TEXT,
    order_id INTEGER,
    operator TEXT,                  -- 谁操作的
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_finance_type ON finance(type);
CREATE INDEX IF NOT EXISTS idx_finance_date ON finance(created_at);
