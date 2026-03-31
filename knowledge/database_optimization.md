# 数据库索引与查询优化

> 来源: 训练知识结构化提取 | 用于: 考试execution题

## 1. 索引类型

### B-Tree索引（最常用）
```
结构: 平衡排序树，O(log n)查找
适用: 等值查询、范围查询、排序
MySQL InnoDB默认索引类型

CREATE INDEX idx ON orders(customer_id, status, created_at DESC);
```

### Hash索引
```
适用: 精确匹配（=, IN）
不适用: 范围查询（>, <, BETWEEN）、排序
Memory引擎默认
```

### 全文索引
```
适用: 文本搜索（LIKE '%keyword%' 无法用普通索引）
MySQL: FULLTEXT INDEX
PostgreSQL: tsvector + GIN索引
```

## 2. 复合索引设计

### 最左前缀原则
```sql
-- 索引: (a, b, c)
WHERE a = 1                -- ✅ 用到索引
WHERE a = 1 AND b = 2      -- ✅ 用到索引
WHERE a = 1 AND b = 2 AND c = 3  -- ✅ 全覆盖
WHERE b = 2                -- ❌ 无法用索引（跳过了a）
WHERE a = 1 AND c = 3      -- ⚠️ 只用到a（b被跳过）
WHERE a > 1 AND b = 2      -- ⚠️ 只用到a（范围查询后的列无法用）
```

### 覆盖索引（Covering Index）
```
查询只用到索引中的列，不需要回表（回表=根据索引找到行再查数据）

SELECT customer_id, status FROM orders WHERE customer_id = ? AND status = 'active';
-- 如果索引是 (customer_id, status)，则完全覆盖，不需要回表
```

### 考试高频: 选哪个索引？
```
查询: SELECT * FROM orders WHERE customer_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 20

A) idx(created_at)          -- ❌ 无过滤
B) idx(customer_id, status, created_at DESC)  -- ✅ 覆盖WHERE+ORDER BY
C) idx(status)              -- ❌ 选择性太低
D) idx(customer_id)         -- ⚠️ 部分覆盖，需filesort

答案: B
```

## 3. 查询优化

### EXPLAIN关键指标
```
type: ALL(全表扫描) < index < range < ref < const
      ❌                             ✅

rows: 预估扫描行数（越小越好）
Extra:
  Using filesort    → ORDER BY没有走索引
  Using temporary   → 用了临时表
  Using index       → 覆盖索引（好）
  Using where       → WHERE过滤
```

### 常见慢查询模式
| 模式 | 问题 | 优化 |
|------|------|------|
| SELECT * | 取了不需要的列 | 只取需要的列 |
| OFFSET 10000 | 深分页 | 改用cursor/seek pagination |
| LIKE '%xxx' | 前缀通配符无法用索引 | 全文索引或ElasticSearch |
| OR条件 | 可能不走索引 | 改用UNION |
| 函数包裹列 | WHERE YEAR(date)=2024 → 日期索引失效 | WHERE date >= '2024-01-01' AND date < '2025-01-01' |
| N+1查询 | 循环中执行查询 | JOIN或批量查询 |

### 分页优化
```sql
-- ❌ 深分页（OFFSET 100000扫描所有行）
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000;

-- ✅ 游标分页（O(1)复杂度）
SELECT * FROM orders WHERE id > 100000 ORDER BY id LIMIT 20;
```

## 4. 数据迁移模式

### 安全迁移三原则
1. **可回滚**: 每步都能反向操作
2. **幂等**: 重复运行不会出错
3. **有日志**: 每个操作都有记录

### 大表变更
```sql
-- ❌ 直接ALTER TABLE（锁表）
ALTER TABLE orders ADD COLUMN category VARCHAR(50);

-- ✅ pt-online-schema-change（无锁）或分批处理
-- 1. 创建新表
CREATE TABLE orders_new LIKE orders;
ALTER TABLE orders_new ADD COLUMN category VARCHAR(50);

-- 2. 复制数据（分批）
INSERT INTO orders_new SELECT *, NULL FROM orders WHERE id > ? LIMIT 1000;

-- 3. 双写期间同步增量
-- 4. 原子切换表名
RENAME TABLE orders TO orders_old, orders_new TO orders;
```

### 考试模板: 写迁移脚本
```
1. BEGIN事务
2. 创建临时表存储映射
3. 批量处理（避免长锁）
4. 记录日志（merge_log表）
5. 验证数据完整性
6. COMMIT
7. 提供验证查询
```
