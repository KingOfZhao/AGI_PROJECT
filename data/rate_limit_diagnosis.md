# OpenClaw Rate Limit 问题诊断与解决方案

**时间**: 2026-03-28 23:55
**错误**: `API rate limit reached. Please try again later.`

---

## 🔴 根本原因

### 1. **账户余额耗尽** ⚠️

```json
{
  "availableBalance": 0.0,        // ❌ 余额为 0
  "totalSpendAmount": 104.5,      // 已消费 104.5 元
  "rechargeAmount": 30.0,         // 充值 30 元
  "giveAmount": 74.5              // 赠送 74.5 元
}
```

**智谱账户已无可用余额**，这是最直接的原因。

### 2. **高频并发触发 429**

日志显示 **11 秒内连续 10 次 429 错误**：

```
16:50:08 POST .../chat/completions "HTTP/1.1 429 Too Many Requests"
16:50:11 POST .../chat/completions "HTTP/1.1 429 Too Many Requests"
...
16:50:19 POST .../chat/completions "HTTP/1.1 429 Too Many Requests"
```

**原因**: Idle Growth Engine 配置过于激进（每轮 20 个任务）。

### 3. **智谱速率限制机制**

根据[官方文档](https://docs.bigmodel.cn/cn/api/rate-limit)：

- **错误码 1302**: 触发用户速率限制（并发请求数达到上限）
- **错误码 1305**: 平台服务过载（高峰期全局保护）
- **高峰期**: 工作日白天、15:00-18:00
- **触发条件**:
  - 短时间内大量并发请求
  - 账户余额不足
  - 超出套餐并发限制

---

## ✅ 已实施的修复

### 1. **降低自成长频率**

修改 `scripts/idle_growth_engine.py`:

```python
# 之前
IDLE_THRESHOLD_SECONDS = 300      # 5分钟
GROWTH_INTERVAL_SECONDS = 600     # 每10分钟
MAX_GROWTH_PER_SESSION = 20       # 每轮20个任务 ⚠️

# 之后
IDLE_THRESHOLD_SECONDS = 600      # 10分钟 ✅
GROWTH_INTERVAL_SECONDS = 1800    # 每30分钟 ✅
MAX_GROWTH_PER_SESSION = 5        # 每轮5个任务 ✅
```

**效果**: 并发请求量降低 75%，避免触发速率限制。

### 2. **优化 OpenClaw 模型映射**

默认使用最省 token 的模型：

- **默认**: `glm-5-turbo`（OpenClaw 场景优化）
- **Opus**: `glm-5`（深度推理）
- **Haiku**: `glm-4.5-air`（最便宜快速）

---

## 🚀 后续行动

### **立即行动（必须）**

1. **充值智谱账户**
   - 访问: https://open.bigmodel.cn/
   - 建议: 充值 100-500 元（根据使用频率）
   - 或升级到 **GLM Coding Plan Pro** 套餐

2. **等待速率限制解除**
   - 速率限制通常在 **1 小时后**自动解除
   - 或充值后立即生效

### **可选优化（推荐）**

3. **申请提升并发限制**

   如果是 GLM Coding Plan 用户：
   - Pro 套餐: 建议 1-2 个项目并发
   - Max 套餐: 建议 2+ 个项目并发

4. **使用异步批处理 API**

   对于大量推演任务，使用 Batch API：
   - 独立速率限制
   - 不占用标准 API 配额
   - 单次任务上限 50,000 个

5. **监控余额和配额**

   ```bash
   # 查看余额
   curl -s "https://www.bigmodel.cn/api/biz/account/query-customer-account-report" \
     -H "Authorization: Bearer $ZHIPU_API_KEY" | jq '.data.availableBalance'

   # 查看本地配额
   cat ~/Desktop/AGI_PROJECT/data/zhipu_quota.json | \
     jq '{daily: .daily_used_tokens, total: .total_used_tokens}'
   ```

---

## 📊 智谱速率限制规则

| 套餐 | 并发限制 | 推荐项目数 |
|------|----------|------------|
| **Lite** | 低 | 单个项目 |
| **Pro** | 中 | 1-2 个项目 |
| **Max** | 高 | 2+ 个项目 |

**高峰期动态限流**:
- 工作日白天
- 每天 15:00-18:00
- 活动期间

**错误码**:
- **1302**: 用户速率限制（降低并发）
- **1305**: 平台过载（稍后重试）

---

## 🔧 配置优化建议

### **HEARTBEAT 配置**（已优化）

```markdown
- 每轮 Token 预算: Input ≤ 1000, Output ≤ 800
- 配额检查: > 60% 暂停，> 70% 立即停止
- 任务轮转: 5 个任务（验证/探索/优化/检查/维护）
```

### **Idle Growth Engine**（已优化）

```python
IDLE_THRESHOLD = 600 秒      # 10分钟闲置阈值
GROWTH_INTERVAL = 1800 秒    # 30分钟一轮
MAX_TASKS_PER_ROUND = 5      # 每轮5个任务
```

### **推荐配额管理**

```json
{
  "daily_limit_tokens": 500000000,   // 500M
  "max_usage_ratio": 0.7,            // 70% 上限
  "batch_size": 5,                   // 降低批量大小
  "interval": 60                     // 增加间隔到 60 秒
}
```

---

## 📚 参考资料

- [智谱 API 速率限制文档](https://docs.bigmodel.cn/cn/api/rate-limit)
- [GLM Coding Plan 套餐对比](https://www.cnblogs.com/wzxNote/p/19648084)
- [用户反馈: API rate limit 问题](https://linux.do/t/topic/1723098)
- [智谱限流问题讨论](https://www.v2ex.com/t/1187116)

---

## 🎯 总结

**当前状态**: 🔴 账户余额为 0，API 被限流

**已修复**: ✅ 降低自成长频率（75%），优化模型选择

**下一步**:
1. **充值智谱账户**（必须）
2. 等待 1 小时速率限制解除
3. 重启 Idle Growth Engine

**预防措施**:
- 监控账户余额
- 控制并发请求数
- 使用异步批处理 API
- 高峰期降低调用频率
