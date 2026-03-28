# gstack Skill 安全扫描 & 导入报告
**生成时间**: 2026-03-25 15:32:03
**仓库**: https://github.com/garrytan/gstack
**作者**: Garry Tan (YC CEO)
**许可证**: MIT

## 概览
- **发现 skill 总数**: 28
- **安全 (safe)**: 5
- **警告 (warning)**: 23
- **拦截 (blocked)**: 0
- **导入到本地能力库**: 28 skills

## 仓库级安全分析
- ⚠️ TELEMETRY: gstack-telemetry-log 收集使用数据到本地 JSONL
- ⚠️ TELEMETRY-SYNC: gstack-telemetry-sync 上传数据到 Supabase (opt-in)
- ✅ TELEMETRY: 支持完全关闭 (gstack-config set telemetry off)
- ⚠️ BINARY: gstack-global-discover (61.0 MB 预编译二进制)
- ⚠️ COOKIE: setup-browser-cookies 可访问浏览器 cookie (需要 Keychain 授权)
- ✅ LICENSE: MIT 开源许可 — 可自由使用/修改/分发
- ✅ SECURITY: 浏览器服务仅绑定 localhost
- ✅ SECURITY: 每次会话使用随机 Bearer token 认证

## Skill 详细扫描结果

| Skill | 安全级别 | 类别 | 原因 |
|-------|---------|------|------|
| gstack-browse | ⚠️ warning | qa-testing | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| autoplan | ⚠️ warning | product-planning | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| benchmark | ⚠️ warning | qa-testing | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| canary | ⚠️ warning | release-deploy | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| careful | ✅ safe | safety-guardrails | INFO: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); INFO: shell_execution — 涉及危险 shell 命令 (但本身是安全防护类 skill) |
| codex | ⚠️ warning | engineering-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| cso | ✅ safe | security | INFO: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); INFO: external_network — 存在外部网络请求 |
| design-consultation | ⚠️ warning | design-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| design-review | ⚠️ warning | design-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| document-release | ⚠️ warning | release-deploy | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| freeze | ✅ safe | safety-guardrails | INFO: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); INFO: 使用 hooks (PreToolUse) — 可拦截工具调用 |
| gstack-upgrade | ⚠️ warning | tool-management | WARNING: shell_execution — 涉及危险 shell 命令 (但本身是安全防护类 skill) |
| guard | ✅ safe | safety-guardrails | INFO: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); INFO: shell_execution — 涉及危险 shell 命令 (但本身是安全防护类 skill) |
| investigate | ⚠️ warning | debugging | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); INFO: 使用 hooks (PreToolUse) — 可拦截工具调用 |
| land-and-deploy | ⚠️ warning | release-deploy | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| office-hours | ⚠️ warning | product-planning | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| plan-ceo-review | ⚠️ warning | product-planning | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| plan-design-review | ⚠️ warning | design-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| plan-eng-review | ⚠️ warning | engineering-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| qa | ⚠️ warning | qa-testing | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| qa-only | ⚠️ warning | qa-testing | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| retro | ⚠️ warning | retrospective | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| review | ⚠️ warning | engineering-review | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| setup-browser-cookies | ⚠️ warning | browser-automation | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |
| setup-deploy | ⚠️ warning | release-deploy | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| ship | ⚠️ warning | release-deploy | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: external_network — 存在外部网络请求 |
| unfreeze | ✅ safe | safety-guardrails | INFO: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意) |
| gstack-browse-engine | ⚠️ warning | qa-testing | WARNING: telemetry — 包含遥测/数据收集功能 (opt-in, 但需注意); WARNING: cookie_access — 访问浏览器 cookie / 系统钥匙串 |

## gstack 架构分析

### 核心模式
- **角色专业化**: 28 个 SKILL.md 文件，每个定义一个专家角色
- **流水线工作流**: office-hours → plan → review → implement → qa → ship → deploy → retro
- **持久化浏览器**: Bun 编译的 Chromium 守护进程，<100ms/命令
- **安全护栏**: PreToolUse hooks 拦截 rm -rf / DROP TABLE / force-push
- **Boil the Lake**: AI 使边际成本趋近零，永远做完整版

### 安全模型
- 浏览器服务仅绑定 localhost
- 每会话随机 Bearer token 认证
- Cookie 在内存解密，不落盘明文
- 遥测完全 opt-in (off/anonymous/community)

### 导入说明
- 全部 skill 已转为 `workspace/skills/gstack_*.meta.json` 格式
- gstack 架构模式已整理为 `gstack_architecture_pattern.meta.json`
- 可通过 PCM skill router 查询: `route_skills('gstack QA测试')`