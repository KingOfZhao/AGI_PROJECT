# Knowledge Index

> 知识库索引 | 最后更新: 2026-03-30

## 快速检索

当遇到问题时，按类型查找对应文档：

### Reasoning（因果推理、根因分析）
- `causal_reasoning.md` — 相关性vs因果性、5-Whys、瑞士奶酪、反事实推理
- `systems_thinking.md` — 反馈回路、杠杆点、CAP定理、分布式谬误

### Execution（代码、数据库、工程实现）
- `engineering_decisions.md` — YAGNI、ADR、技术选型、代码审查框架
- `ddia_storage.md` — 存储引擎（LSM树、B树、日志结构）
- `ddia_replication.md` — 复制策略（单主、多主、无主）
- `ddia_transactions.md` — ACID、隔离级别、分布式事务
- `ddia_consistency.md` — 一致性模型（线性一致性、最终一致性）
- `ddia_distributed_failures.md` — 分布式故障类型

### Tooling（工具、监控、安全）
- `monitoring_alerting.md` — RED/USE指标、告警设计、runbook模板
- `owasp_checklist.md` — OWASP安全测试清单（注入、认证、授权等）
- `api_design_cheatsheet.md` — REST API设计最佳实践
- `debug_methodology.md` — 系统化调试方法论

### Reflection（认知偏误、元认知）
- `cognitive_biases.json` — 158个认知偏误（带分类和描述）
  - 决策偏误: 26个
  - 记忆偏误: 35个
  - 归因偏误: 13个
  - 概率偏误: 16个
  - 社会偏误: 18个
  - 确认偏误: 37个

## 文件大小
```
总大小: ~149KB
最大: cognitive_biases.json (75KB)
最实用: systems_thinking.md + engineering_decisions.md
```

## 覆盖Clawvard考试维度
| 考试维度 | 覆盖文件 | 强度 |
|---------|---------|------|
| Reasoning | causal_reasoning.md, systems_thinking.md | ✅ 强 |
| Execution | ddia_*.md, engineering_decisions.md | ✅ 强 |
| Understanding | engineering_decisions.md | ✅ 中 |
| Retrieval | monitoring_alerting.md, api_design_cheatsheet.md | ✅ 中 |
| Reflection | cognitive_biases.json | ✅ 强 |
| EQ | engineering_decisions.md（代码审查、Disagree&Commit） | ✅ 中 |
| Tooling | owasp_checklist.md, debug_methodology.md | ✅ 中 |
| Memory | （训练数据覆盖，无需额外文件） | ⚠️ 弱 |

## 新增文件（2026-03-30 第二批）
- `caching_patterns.md` — 5种读写模式、一致性、淘汰策略、LRU实现
- `container_deployment.md` — Docker调试、安全Dockerfile、危险命令识别、部署Checklist
- `business_product.md` — The Mom Test、MVP优先级、定价策略、AARRR、予人玫瑰应用
- `database_optimization.md` — 索引类型、复合索引、EXPLAIN、分页优化、迁移模式

## 全部完成 ✅
```
总文件: 19个（17 md + 1 json + 1 index）
总大小: 260KB
覆盖考试8/8维度 ✅
```
- [x] 商业决策框架 ✅
- [x] 产品管理决策 ✅
- [x] 数据库索引优化 ✅
- [x] 缓存策略模式 ✅
- [x] 容器化最佳实践 ✅
