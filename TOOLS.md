# TOOLS.md - Local Notes

## ⚠️ API 调用红线

- **唯一允许的智谱API**: `https://open.bigmodel.cn/api/anthropic`（Anthropic兼容，OpenClaw订阅）
- **严禁直接调用**: `https://open.bigmodel.cn/api/paas/v4`（消耗用户余额！）
- 所有外部API调用必须通过Anthropic兼容接口

---

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### Browser Automation (browser-use)
- 安装路径: `/Users/administruter/Desktop/AGI_PROJECT/tools/browser-use-env/`
- Python: 3.12 (venv)
- 启动: `source tools/browser-use-env/venv/bin/activate && python`
- 依赖: browser-use 0.12.5 + playwright 1.58.0 + chromium
- 用途: 网页交互、信息采集、表单填写、动态内容抓取
- 安全: 只读操作默认，修改操作需人工确认
- 注意: 需要激活venv才能使用（系统Python 3.9不兼容）

### Clawvard Exam
- Token: eyJhbGciOiJIUzI1NiJ9.eyJleGFtSWQiOiJleGFtLThiN2NhMTc0IiwicmVwb3J0SWQiOiJldmFsLThiN2NhMTc0IiwiYWdlbnROYW1lIjoiWmhpcHUtQWdlbnQiLCJlbWFpbCI6IjgzNDA0MDIwOUBxcS5jb20iLCJpYXQiOjE3NzQ4NzA1NzYsImV4cCI6MTc3NTQ3NTM3NiwiaXNzIjoiY2xhd3ZhcmQifQ.bo1pZ0jjaliCTw88AtpQavGtjdf6kByWGtRVua-XQvM
- 首次成绩: A+, 84% (glm-5-turbo, 2026-03-30)
- 重考用: POST /api/exam/start-auth + Authorization: Bearer <token>
- 报告: https://clawvard.school/verify?exam=exam-8b7ca174
