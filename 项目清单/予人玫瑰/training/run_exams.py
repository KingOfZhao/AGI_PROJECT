#!/usr/bin/env python3
"""员工模拟考核 — 产出实际成果"""
import sys, json, os
from pathlib import Path
from datetime import datetime

OUT = Path(__file__).parent / "training" / "output"
OUT.mkdir(parents=True, exist_ok=True)

# ═══ 沈思语 — 写作考核 ═══
SHENSIYU_ARTICLE = """# 第一次独自搬家

凌晨两点，我蹲在空荡荡的客厅地板上，被三个纸箱包围。

最大的那个箱子装着我妈偷偷塞进来的棉被，她说"外面买的没有家里的暖和"。第二个箱子装了十二双鞋，但我平时只穿其中三双。最小的那个，只有一本书——《一间自己的房间》。

我没有哭。但也没有站起来。

---

搬家的原因说出来很俗：房东要涨租，每月多800块。

800块。够我吃一个月的早饭，或者交三个月的话费，或者买一束玫瑰放在那个永远见不到阳光的阳台上。

我算了一整天的账。算到最后发现，不是租不起，是不甘心。

不甘心什么呢？大概是不甘心二十六岁，还要为800块钱在深夜搬家，还要一个人把沙发扛上六楼，还要在搬完之后对着空白的墙壁发呆，然后假装这叫"独立生活"。

---

其实最难的不是搬家。

是搬家之后，你发现冰箱空了，要去超市采购。你买了两个人的量——番茄、鸡蛋、一把青菜——然后站在货架前愣住了。

你已经一个人了。一个人吃不完这些。

那天晚上我煮了一锅番茄蛋面，吃了一半，另一半倒掉了。

不是不好吃。是没有人问我"今天辛苦了吧"。

---

搬家第三天，我妈打电话来。

"到了吗？新房子暖和吗？"

"暖和。"我说，"棉被很厚。"

她不知道那床棉被我还没拆封。不是因为不冷，是因为拆开之后，整个房间都会变成家的味道，而我还不想承认——

这个陌生的房间，是我的家。

---

有人说，长大就是学会一个人做所有的事。

我觉得不是。

长大是学会一个人做完所有的事之后，还能对自己说一句：

**"辛苦了，但你可以的。"**

然后打开那床棉被，好好睡一觉。

明天早上醒来，冰箱里要有两个人的菜。一个给自己，一个给"值得被好好对待的自己"。

---

*你有过独自搬家的经历吗？那个晚上，你是怎么度过的？*

*评论区聊聊，你并不孤单。*

—— 我是思语，一个相信予人玫瑰的人。"""

with open(OUT / "shen_siyu_article_01.md", "w") as f:
    f.write(SHENSIYU_ARTICLE)

# ═══ 周知然 — 社群考核 ═══
ZHOU_ZHIRAN_PLAN = """# 玫瑰成长营 · 3天激活方案

## 背景
群内连续2天无人发言，处于"死亡沉默"状态。
根因分析：缺乏互动触发点 + 成员观望心态 + 内容同质化疲劳

## Day 1: 破冰行动 — "真心话接龙"

**08:00** 发早安+抛出轻话题：
> 🌹 早安姐妹们！今天玩个小游戏：
> 用一句话形容你此刻的心情，格式："我是[城市]的[昵称]，此刻我[状态]"
> 我先来：我是上海的婉清，此刻我在喝第三杯咖啡😂

**效果预期**：5~10人跟帖（低门槛参与）

**12:00** 追问+延伸：
> 看到好多姐妹都在忙工作/带娃/学习
> 那你们觉得，如果能有一整天完全属于自己，你最想做什么？
> 我会去花市买一束玫瑰，然后一个人看电影🍿

**效果预期**：激发讨论，10~15人参与

**21:00** 深度话题（与当日公众号文章联动）：
> 今天公众号发了篇文章《第一次独自搬家》
> 你们有没有那个"长大瞬间"？就是突然觉得自己变坚强的那一刻？
> 我的是：一个人去医院做全身体检的时候。

---

## Day 2: 价值回归 — "实用干货轰炸"

**08:00** 早安+实用分享：
> 🌹 早安！今天分享一个超实用的省钱小技巧：
> [干货内容：如"外卖怎么点最划算"/"平价好用的护肤品清单"]
> 觉得有用的话，分享给你身边需要的朋友吧～

**14:00** 限时福利：
> 🎁 姐妹们，我帮大家争取到一个福利：
> [某合作方的免费体验/折扣码/资料包]
> 只限群内姐妹，需要的私我领取，限量30份！

**效果预期**：创造"群内独享"感，提升群价值认知

**21:00** 话题讨论：
> 今天聊个扎心的话题：你有没有花过"后悔的钱"？
> 我先来：花2000块买的健身卡，去了3次😂
> 大家来"忏悔"一下？

---

## Day 3: 裂变重启 — "邀请有礼"

**08:00** 宣布活动：
> 🌹🌹🌹 好消息！
> 玫瑰成长营要升级了！
> 邀请1位闺蜜入群 = 获得品牌周边1份（玫瑰书签）
> 邀请3位 = 免费体验VIP会员1个月
> 活动仅限本周！

**效果预期**：现有活跃用户带动新用户，实现裂变

**21:00** 总结+预告：
> 本周群活跃度回升！感谢姐妹们的参与
> 下周预告：周三"匿名故事会" + 周末"线上电影之夜"
> 敬请期待～

---

## 关键数据追踪
| 指标 | Day 1前 | Day 1 | Day 2 | Day 3 |
|------|---------|-------|-------|-------|
| 发言人数 | 0 | 10~15 | 15~20 | 20~30 |
| 新增成员 | 0 | 0~2 | 2~5 | 5~10 |
| 群活跃率 | 0% | 20% | 35% | 50% |

## 注意事项
- 不要用机器人刷屏（用户能看出来）
- 每次发言间隔>30分钟（避免刷屏感）
- 私聊活跃用户，建立"核心圈子"（5~10人的KOC团队）
- 如果Day 1完全无人响应 → 私聊5个种子用户，请他们带头发言"""

with open(OUT / "zhou_zhiran_activation_plan.md", "w") as f:
    f.write(ZHOU_ZHIRAN_PLAN)

# ═══ 陈星辰 — 技术考核 ═══
CHEN_XINGCHEN_DB = """-- ═══ 予人玫瑰 CRM — P0 数据库扩展 ═══
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
"""

with open(OUT / "chen_xingchen_db_schema.sql", "w") as f:
    f.write(CHEN_XINGCHEN_DB)

# 陈星辰 — 裂变海报生成器
POSTER_GEN = '''#!/usr/bin/env python3
"""
裂变海报生成器 — 陈星辰
依赖: pip3 install Pillow
用法: python3 poster_gen.py "苏婉清" "送人玫瑰，手有余香" template_rose output.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

def create_poster(name, quote, template, output):
    W, H = 1080, 1920
    
    # 渐变背景
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(233 + (248 - 233) * y / H)
        g = int(30 + (187 - 30) * y / H)
        b = int(99 + (208 - 99) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # 装饰圆
    draw.ellipse([W-200, -100, W+100, 200], fill=(255, 255, 255, 30))
    draw.ellipse([-100, H-300, 200, H], fill=(255, 255, 255, 20))
    
    # 玫瑰emoji (用文字替代)
    try:
        font_rose = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 120)
        draw.text((W//2-60, 200), "🌹", font=font_rose, fill=(0,0,0))
    except:
        draw.text((W//2-30, 250), "🌹", fill=(255,255,255))
    
    # 引号
    try:
        font_quote = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 80)
        font_text = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 52)
        font_name = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 36)
        font_brand = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 28)
    except:
        font_quote = font_text = font_name = font_brand = ImageFont.load_default()
    
    draw.text((120, 500), """", font=font_quote, fill=(255, 255, 255, 200))
    
    # 金句 (自动换行)
    max_chars = 16
    lines = [quote[i:i+max_chars] for i in range(0, len(quote), max_chars)]
    y_start = 700
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_text)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x, y_start + i * 80), line, font=font_text, fill=(255, 255, 255))
    
    # 用户名
    name_text = f"—— {name}"
    bbox = draw.textbbox((0, 0), name_text, font=font_name)
    nw = bbox[2] - bbox[0]
    draw.text(((W - nw) // 2, y_start + len(lines) * 80 + 40), name_text, font=font_name, fill=(255, 215, 0))
    
    # 品牌
    brand = "予人玫瑰 · 让每个女性被看见"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) // 2, H - 200), brand, font=font_brand, fill=(255, 255, 255, 180))
    
    img.save(output)
    print(f"海报已生成: {output}")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "玫瑰女孩"
    quote = sys.argv[2] if len(sys.argv) > 2 else "送人玫瑰，手有余香"
    tpl = sys.argv[3] if len(sys.argv) > 3 else "template_rose"
    out = sys.argv[4] if len(sys.argv) > 4 else "poster.png"
    create_poster(name, quote, tpl, out)
'''

with open(OUT / "poster_generator.py", "w") as f:
    f.write(POSTER_GEN)

# ═══ 赵明远 — 财务考核 ═══
ZHAO_MINGYUAN_FINANCE = """# 予人玫瑰 · 3个月财务预测

## 三种场景对比

### 🟢 乐观场景（增长超预期）
| 月份 | 收入 | 支出 | 净利 | 累计 |
|------|------|------|------|------|
| M1 | ¥2,000 | ¥1,550 | +¥450 | +¥450 |
| M2 | ¥8,000 | ¥2,500 | +¥5,500 | +¥5,950 |
| M3 | ¥20,000 | ¥4,000 | +¥16,000 | +¥21,950 |

收入构成(M3):
- 付费社群: 300人 × ¥29.9 = ¥8,970
- 周边销售: 150件 × ¥29.9 = ¥4,485
- 公众号广告: ¥1,500
- 品牌合作: ¥3,000
- 打赏/其他: ¥2,045

### 🟡 中性场景（正常增长）
| 月份 | 收入 | 支出 | 净利 | 累计 |
|------|------|------|------|------|
| M1 | ¥500 | ¥1,550 | -¥1,050 | -¥1,050 |
| M2 | ¥3,000 | ¥2,000 | +¥1,000 | -¥50 |
| M3 | ¥8,000 | ¥3,000 | +¥5,000 | +¥4,950 |

收入构成(M3):
- 付费社群: 100人 × ¥29.9 = ¥2,990
- 周边销售: 50件 × ¥29.9 = ¥1,495
- 公众号广告: ¥800
- 品牌合作: ¥1,000
- 打赏/其他: ¥1,715

### 🔴 悲观场景（增长不及预期）
| 月份 | 收入 | 支出 | 净利 | 累计 |
|------|------|------|------|------|
| M1 | ¥100 | ¥1,550 | -¥1,450 | -¥1,450 |
| M2 | ¥500 | ¥1,800 | -¥1,300 | -¥2,750 |
| M3 | ¥2,000 | ¥2,000 | ¥0 | -¥2,750 |

**悲观场景应对**:
1. M2未达预期 → 暂停送花行动（省500/月）
2. M3仍未达预期 → 暂停周边制作（省200/月）
3. 3个月累计亏损 ¥2,750 → 在可承受范围内
4. 核心原则：**不借钱运营**

## 启动资金需求
**最低启动资金: ¥4,050**（3个月中性场景支出）
**建议准备: ¥5,000**（留15%缓冲）

## 盈亏平衡点
**付费社群 170人 = 月收入 ¥5,083 = 覆盖月支出**
预计达成时间：M2末~M3初

## 现金流红线
- 现金余额 < ¥2,000 → 黄色预警（缩减非必要支出）
- 现金余额 < ¥1,000 → 红色预警（暂停所有非核心支出）
- 现金余额 = ¥0 → 停止运营（但不借贷）"""

with open(OUT / "zhao_mingyuan_finance_forecast.md", "w") as f:
    f.write(ZHAO_MINGYUAN_FINANCE)

# ═══ 输出考核结果 ═══
results = [
    ("✍️ 沈思语", "写作考核", "shen_siyu_article_01.md", "800+字 / 2个金句 / 3秒钩子开头 / 零禁用词"),
    ("💬 周知然", "社群考核", "zhou_zhiran_activation_plan.md", "3天激活方案 / 数据追踪 / 注意事项"),
    ("💻 陈星辰", "技术考核", "chen_xingchen_db_schema.sql", "5张表 / 索引 / 外键 / 完整DDL"),
    ("💻 陈星辰", "海报生成器", "poster_generator.py", "Python Pillow / 渐变背景 / 金句排版 / 品牌水印"),
    ("📊 赵明远", "财务考核", "zhao_mingyuan_finance_forecast.md", "3种场景 / 盈亏平衡 / 现金流红线"),
]

print("═══════════════════════════════════════")
print("  🌹 予人玫瑰 · 员工考核结果")
print("═══════════════════════════════════════")
for name, exam, file, summary in results:
    print(f"\n{name} — {exam}")
    print(f"  📄 {file}")
    print(f"  ✓ {summary}")

print(f"\n📂 输出目录: {OUT}")
