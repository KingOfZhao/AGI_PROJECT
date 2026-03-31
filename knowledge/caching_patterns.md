# 缓存策略模式

> 来源: 训练知识结构化提取 | 用于: 考试execution题、系统设计

## 1. 缓存读写模式

### Cache-Aside（旁路缓存）⭐最常用
```
读: 先查缓存 → 命中则返回 → 未命中则查DB → 写入缓存 → 返回
写: 先写DB → 再删缓存（不是更新！）
```
- 优点: 简单、可靠、DB是唯一真相源
- 缺点: 首次请求延迟高（cache miss）
- 适用: 读多写少、一致性要求中等

### Read-Through（读穿透）
```
读: 查缓存 → miss → 缓存层自动查DB并填充 → 返回
写: 同Cache-Aside
```
- 与Cache-Aside区别: 缓存层封装了DB查询逻辑
- 适用: 需要统一缓存访问层的场景

### Write-Through（写穿透）
```
写: 写缓存 → 同步写DB → 两边都成功才返回
读: 直接读缓存
```
- 优点: 数据一致性强（缓存和DB同步更新）
- 缺点: 写延迟增加（要等DB写完）

### Write-Behind / Write-Back（写回）
```
写: 写缓存 → 立即返回 → 异步批量写DB
读: 直接读缓存
```
- 优点: 写性能极高
- 缺点: 缓存宕机=数据丢失

### Refresh-Ahead（预刷新）
```
TTL快过期时 → 异步刷新缓存 → 用户始终命中
```
- 优点: 零miss用户体验
- 缺点: 实现复杂

## 2. 缓存一致性

### 常见问题与解法

| 问题 | 原因 | 解法 |
|------|------|------|
| 缓存与DB不一致 | 写DB成功但删缓存失败 | 重试 + 消息队列保证 |
| 并发竞争 | 读写同时发生 | 加锁 or 延迟双删 |
| 缓存雪崩 | 大量key同时过期 | 随机TTL偏移 |
| 缓存穿透 | 查不存在的key | 布隆过滤器 + 空值缓存 |
| 缓存击穿 | 热点key过期 | 互斥锁 or 永不过期+异步刷新 |

### 延迟双删策略
```
1. 先删缓存
2. 更新DB
3. 延迟N毫秒再删一次缓存（防止并发读把旧数据写回缓存）
```

## 3. 缓存层级设计

### 典型多层缓存（从近到远）
```
CPU L1/L2/L3 → 进程内缓存(内存) → Redis/Memcached → CDN → DB
   (ns级)        (μs级)              (ms级)         (网络)    (磁盘)
```

### 多级缓存一致性
```
用户更新数据 → 写DB → 主动失效Redis → 主动失效CDN（purge API）→ 通知客户端 invalidateQuery
```
- 关键: CDN通常TTL最长（小时→天），必须主动purge
- React Query: mutation成功后调invalidateQueries

## 4. 缓存淘汰策略

| 策略 | 算法 | 适用场景 |
|------|------|---------|
| LRU | 最近最少使用 | 通用 |
| LFU | 最少使用频率 | 热点数据明确 |
| FIFO | 先进先出 | 简单场景 |
| TTL | 过期淘汰 | 时效性数据 |
| Random | 随机淘汰 | 均匀分布 |

### LRU实现要点
```python
# 正确的LRU: OrderedDict 或 双向链表+哈希
from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)  # O(1)
            return self.cache[key]
        return None
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # O(1) 删除最旧
```

## 5. 考试高频考点

### "实现缓存层"答题模板
1. 明确缓存模式（Cache-Aside最安全）
2. LRU淘汰 + TTL过期
3. 穿透/雪崩/击穿防护
4. 并发安全（锁或原子操作）
5. 降级策略（缓存故障时不拖垮DB）
6. 监控指标（命中率、延迟、大小）
