# AGI 可视化项目优化清单

> 基于 DiePre AI 推演输出 (3180节点, 4轮碰撞) + 代码审计生成
> 生成时间: 2026-03-24
> 目标: 前端性能/后端效率/数据库查询/DiePre数据集成

---

## 一、数据库层优化 (DB)

### DB-1: 启用 WAL 模式 + PRAGMA 优化
- **现状**: `CognitiveLattice.__init__` 仅 `connect()`, 无 PRAGMA 配置
- **问题**: 默认 journal_mode=delete, 读写互斥; 无 mmap 加速
- **优化**: 在 `_init_db()` 开头添加 PRAGMA 配置
- **影响**: 并发读写性能提升 3-5x
- **文件**: `agi_v13_cognitive_lattice.py`

### DB-2: 添加 FTS5 全文搜索索引
- **现状**: `/api/nodes?search=xxx` 使用 `LIKE '%xxx%'` 全表扫描
- **问题**: 3180+ 节点时 LIKE 扫描慢, 且不支持中文分词
- **优化**: 创建 FTS5 虚拟表, 用 trigram tokenizer 支持中文
- **影响**: 搜索响应 < 10ms (当前 ~200ms+)
- **文件**: `agi_v13_cognitive_lattice.py`

### DB-3: 优化 `/api/domains` 的 COUNT 查询
- **现状**: 对每个 domain 调用 `get_nodes_by_domain(d, limit=1000)` 再 `len()`
- **问题**: N+1 查询, 每个 domain 一次 SELECT, 大量冗余数据传输
- **优化**: 改为单条 `GROUP BY domain` 聚合查询
- **影响**: 从 N+1 次查询降为 1 次
- **文件**: `api_server.py` + `agi_v13_cognitive_lattice.py`

### DB-4: 添加复合索引优化分页查询
- **现状**: 仅有 `idx_content`, `idx_status`, `idx_domain` 单列索引
- **问题**: `/api/nodes` 的 domain+status+created_at 联合过滤无法使用索引
- **优化**: 添加 `(domain, status, created_at DESC)` 复合索引
- **文件**: `agi_v13_cognitive_lattice.py`

### DB-5: embedding 搜索优化 — 避免全表加载
- **现状**: `find_similar_nodes()` 每次 `SELECT * WHERE embedding IS NOT NULL` 全表扫描
- **问题**: 所有 embedding 加载到内存, 29MB DB 内有大量 BLOB
- **优化**: 添加 domain 预过滤 + 分批加载 + 缓存热点 embedding
- **文件**: `agi_v13_cognitive_lattice.py`

---

## 二、后端 API 优化 (API)

### API-1: `/api/domains` 改为聚合查询 (对应 DB-3)
- **现状**: 逐 domain 查询再计数
- **优化**: `SELECT domain, COUNT(*) as count FROM cognitive_nodes GROUP BY domain ORDER BY count DESC`
- **文件**: `api_server.py`

### API-2: `/api/graph` 添加连接度排序
- **现状**: 无序 LIMIT, 可能漏掉高连接度核心节点
- **优化**: 按连接度降序排列, 优先返回核心节点
- **文件**: `api_server.py`

### API-3: 添加 API 响应缓存
- **现状**: 每次请求都查询数据库
- **优化**: 对 `/api/stats`, `/api/domains` 添加 TTL 缓存 (30s)
- **文件**: `api_server.py`

### API-4: `/api/nodes` 搜索使用 FTS5 (对应 DB-2)
- **现状**: `content LIKE '%search%'`
- **优化**: 使用 FTS5 match 查询
- **文件**: `api_server.py`

---

## 三、前端性能优化 (FE)

### FE-1: 图谱力导向算法 — Barnes-Hut 加速
- **现状**: O(n²) 暴力斥力计算 (`simStep` 双重 for 循环)
- **问题**: 200+ 节点时帧率下降, 300+ 节点明显卡顿
- **优化**: 实现四叉树 Barnes-Hut 近似, 复杂度降至 O(n log n)
- **影响**: 支持 500+ 节点流畅渲染
- **文件**: `web/index.html` (simStep 函数)

### FE-2: 节点列表虚拟滚动
- **现状**: 一次渲染所有节点 DOM (最多 50 个)
- **问题**: 分组展开后 DOM 节点过多
- **优化**: 对分组展开的节点添加懒加载, 折叠组默认不渲染内部节点
- **文件**: `web/index.html` (renderNodeCard/loadNodes)

### FE-3: 防抖搜索
- **现状**: 搜索需按 Enter 触发
- **优化**: 添加 300ms debounce 实时搜索
- **文件**: `web/index.html` (searchND)

### FE-4: DiePre 报告面板增强 — 接入 reasoning.db
- **现状**: 从 `data/growth_report.json` 静态文件加载
- **问题**: 无法展示 DiePre AI 推演的实时数据 (碰撞结果/节点关系/搜索结果)
- **优化**: 添加 `/api/diepre/report` 接口从 reasoning.db 读取, 前端动态渲染
- **文件**: `api_server.py` + `web/index.html`

### FE-5: 图谱 Canvas 高 DPI 适配
- **现状**: `canvas.width = wrap.clientWidth` 未考虑 devicePixelRatio
- **问题**: Retina 屏幕模糊
- **优化**: 乘以 devicePixelRatio, CSS 尺寸不变
- **文件**: `web/index.html` (drawGraph)

### FE-6: SSE 断线重连指数退避
- **现状**: 固定 3 秒重连 `setTimeout(connectSSE, 3000)`
- **优化**: 指数退避 (3s → 6s → 12s → 30s max)
- **文件**: `web/index.html` (connectSSE)

---

## 四、DiePre 数据集成 (INT)

### INT-1: DiePre reasoning.db 数据桥接 API
- **现状**: DiePre 的 9 张 DB 表与主系统完全隔离
- **优化**: 添加 `/api/diepre/stats`, `/api/diepre/nodes`, `/api/diepre/collisions` 接口
- **影响**: 前端可展示 DiePre 推演的 3180 节点和 4 轮碰撞数据
- **文件**: `api_server.py`

### INT-2: DiePre 节点导入主知识库
- **现状**: DiePre 的 real 节点 (1573个) 未进入主 cognitive_nodes 表
- **优化**: 添加批量导入接口, 将 DiePre real 节点映射为 known 状态导入
- **文件**: `api_server.py`

---

## 优先级排序

| 优先级 | 编号 | 预估收益 |
|--------|------|---------|
| P0 | DB-1, DB-3, API-1 | 立即可见的性能提升 |
| P1 | FE-1, FE-5, FE-6 | 前端体验显著改善 |
| P2 | DB-2, DB-4, API-4, FE-3 | 搜索体验提升 |
| P3 | DB-5, API-2, API-3 | 大数据量下的性能保障 |
| P4 | FE-4, INT-1, INT-2 | DiePre 数据集成 |
| P5 | FE-2 | 极端场景下的 DOM 优化 |
