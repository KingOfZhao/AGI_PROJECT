# Feature Requests

Capabilities requested by the user.

---

## [FEAT-20260330-001] multi_agent_arena

**Logged**: 2026-03-30T17:42:00+08:00
**Priority**: high
**Status**: in_progress
**Area**: config

### Requested Capability
多个Agent角色互相审查、验证、督促，形成产出闭环

### User Context
用户批评"一个人自嗨"，需要多视角验证确保质量。执行者写代码→审查者验证→反思者提炼经验。

### Complexity Estimate
medium

### Suggested Implementation
- ARENA.md定义角色和流程
- 每次产出经过审查者独立验证
- 审查报告记录到CRM

### Metadata
- Frequency: recurring

---

## [FEAT-20260330-002] ssh_deploy_access

**Logged**: 2026-03-30T17:40:00+08:00
**Priority**: critical
**Status**: pending
**Area**: infra

### Requested Capability
SSH部署通道到120.55.65.39

### User Context
所有服务端代码改动无法部署，阻塞项目推进

### Complexity Estimate
simple

### Suggested Implementation
用户配置SSH密钥或提供密码

### Metadata
- Frequency: first_time

---

## [FEAT-20260330-003] admin_chart_export

**Logged**: 2026-03-30T17:38:00+08:00
**Priority**: medium
**Status**: pending
**Area**: backend

### Requested Capability
Admin后台数据趋势图表 + CSV导出

### Suggested Implementation
- /api/stats/trend API（已完成，待部署）
- Chart.js折线图（已完成，待部署）
- CSV导出按钮（已完成，待部署）

### Metadata
- Frequency: first_time
- Related Files: app.py, admin.html
