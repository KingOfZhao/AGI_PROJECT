# AGI 高速自成长 — 后台运行说明

> 启动时间: 2026-03-24 07:10  
> 进程ID: 85953  
> 日志文件: logs/growth_overnight_20260324_071024.log

---

## 运行配置

```bash
命令: python3 growth_engine.py --parallel --workers 4 --rounds 150
模式: DiePre增强并行模式
并发数: 4 workers (降低以避免429限速)
目标轮次: 150轮
预计耗时: ~25小时
```

---

## 预期成果

### 节点与SKILL增长

```
基于3轮测试数据推算:
- 真实节点: 3150个 (150轮 × 21节点/轮)
- 有效SKILL: 2350个 (150轮 × 15.7 SKILL/轮)
- 总Tokens: 23M+ (150轮 × 153K/轮)
- 总API调用: 23,100次 (150轮 × 154次/轮)
```

### DiePre框架效果

```
- 固定规则节点: 预计50+ (收敛后自动升级)
- 可变参数节点: 预计3000+
- 零回避风险扫描: 预计4150项
- 收敛域: 预计20%+ (σ<0.05)
- 灾难知识完全量化: 预计10类
```

---

## 监控命令

### 查看进程状态

```bash
# 检查进程是否运行
ps aux | grep 85953

# 查看资源占用
top -pid 85953
```

### 实时监控日志

```bash
# 实时查看最新输出
tail -f logs/growth_overnight_20260324_071024.log

# 查看最近100行
tail -100 logs/growth_overnight_20260324_071024.log

# 搜索关键信息
grep "轮.*DiePre增强" logs/growth_overnight_20260324_071024.log
grep "✅ 报告" logs/growth_overnight_20260324_071024.log
```

### 查看中间结果

```bash
# 查看已生成SKILL数量
ls -1 workspace/skills/*.py | wc -l

# 查看数据库节点数
sqlite3 memory.db "SELECT COUNT(*) FROM proven_nodes;"

# 查看最新报告
cat docs/321自成长待处理/growth_execution_report_v6.md
```

---

## 异常处理

### 如果进程意外退出

```bash
# 检查日志最后错误
tail -200 logs/growth_overnight_20260324_071024.log | grep -i error

# 重新启动（会从checkpoint恢复）
nohup python3 growth_engine.py --parallel --workers 4 --rounds 150 > logs/growth_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### 如果429限速严重

```bash
# 降低并发数到2
kill 85953
nohup python3 growth_engine.py --parallel --workers 2 --rounds 150 > logs/growth_slow_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### 手动停止

```bash
# 优雅停止（会保存checkpoint）
kill -INT 85953

# 强制停止
kill -9 85953
```

---

## 明早检查清单

### 1. 进程状态

```bash
ps aux | grep growth_engine
```

### 2. 完成轮次

```bash
grep "轮.*DiePre增强" logs/growth_overnight_20260324_071024.log | tail -5
```

### 3. 节点统计

```bash
sqlite3 memory.db "SELECT COUNT(*) FROM proven_nodes WHERE domain='software_engineering';"
```

### 4. SKILL数量

```bash
ls -1 workspace/skills/*.py | wc -l
```

### 5. 最终报告

```bash
cat docs/321自成长待处理/growth_execution_report_v6.md
```

### 6. 收敛分析

查看报告末尾的"收敛分析"部分，确认:
- 已收敛域数量
- 灾难知识完全量化类别
- 平均RSS置信度

---

## 成功标准

✅ **最低目标**: 3000+代码领域真实节点  
✅ **理想目标**: 3150+节点 + 2350+ SKILL  
✅ **质量目标**: 20%+域收敛 + 10类灾难完全量化  

---

> 祝您睡个好觉！明早见证AGI的高速成长 🚀
