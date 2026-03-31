# Errors

Command failures and integration errors.

---

## [ERR-20260330-001] clawhub_rate_limit

**Logged**: 2026-03-30T17:42:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
ClawHub API 429限流，无法安装self-improving-agent

### Error
```
ClawHub /api/v1/download failed (429): Rate limit exceeded
```

### Context
- Command: `openclaw skills install self-improving-agent`
- 3次重试均失败（间隔10s、15s、30s）
- 解决：直接git clone GitHub仓库

### Suggested Fix
限流时fallback到git clone

### Resolution
- **Resolved**: 2026-03-30T17:56:00+08:00
- **Notes**: `git clone https://github.com/peterskoett/self-improving-agent.git ~/.openclaw/skills/self-improving-agent`

---

## [ERR-20260330-002] scp_permission_denied

**Logged**: 2026-03-30T17:40:00+08:00
**Priority**: critical
**Status**: pending
**Area**: infra

### Summary
SSH到120.55.65.39失败，Permission denied publickey

### Error
```
Permission denied (publickey,gssapi-keyex,gssapi-with-mic)
```

### Context
- root和administruter用户均失败
- 阻塞所有服务端代码部署
- 需要赵先生配置SSH密钥

### Suggested Fix
用户配置SSH公钥到服务器authorized_keys

### Metadata
- Reproducible: yes
- Related Files: app.py, admin.html
- Recurrence-Count: 3+

---

## [ERR-20260330-003] auto-skill_not_found

**Logged**: 2026-03-30T17:42:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
auto-skill在ClawHub不存在（404）

### Error
```
ClawHub /api/v1/skills/auto-skill failed (404): Skill not found
```

### Resolution
- **Resolved**: 2026-03-30T17:42:00+08:00
- **Notes**: 该skill不存在，手动创建learnings文件替代

---

## [ERR-20260330-004] bash_json_loop_parse

**Logged**: 2026-03-30T10:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
bash for循环中变量展开导致CRM批量更新返回400

### Error
```
400 Bad Request - JSON parse error
```

### Context
- 用bash for循环批量curl更新CRM任务状态
- 变量在循环中展开不一致

### Suggested Fix
超过3次API调用用Python脚本

### Resolution
- **Resolved**: 2026-03-30
- **Promoted**: LEARNINGS

---

## [ERR-20260330-005] browser-use_api_key

**Logged**: 2026-03-30T12:00:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
browser-use本地模式需要BROWSER_USE_API_KEY

### Context
- 安装在独立venv中（Python 3.12）
- 本地模式启动后需要API Key才能运行

### Suggested Fix
获取API Key或使用免费搜索替代方案

---

## [ERR-20260330-006] chart_js_load_order

**Logged**: 2026-03-30T17:55:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
Chart.js script标签在自定义JS之后，导致运行时Chart未定义

### Error
```
ReferenceError: Chart is not defined
```

### Context
- `<script src="chart.js">` 在第626行
- `new Chart(ctx, ...)` 在第581行
- 伟人竞技场审查者发现

### Suggested Fix
1. CDN script移到自定义JS之前
2. 加 `typeof Chart === 'undefined'` 防护
3. 初始化时 `setTimeout(loadTrend, 500)` 确保库加载完成

### Resolution
- **Resolved**: 2026-03-30T17:55:00+08:00
- **Discoverer**: 伟人竞技场审查者
- See Also: LRN-20260330-003
