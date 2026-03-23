# data/ — 运行时数据

自成长引擎和系统运行产生的数据文件。

## 文件说明

| 文件 | 内容 |
|------|------|
| `zhipu_growth_log.jsonl` | 自成长引擎运行日志（每行一条JSON记录） |
| `zhipu_growth_problems.json` | 自成长引擎发现的待探索问题列表 |
| `zhipu_growth_progress.json` | 自成长引擎进度状态（已处理/已提升/已证伪计数） |
| `zhipu_quota.json` | 智谱API配额使用情况 |

## 注意

- `memory.db` 位于项目根目录，是SQLite认知格主数据库（~25MB）
- 数据文件在自成长引擎运行时自动更新，不要手动修改
