# migrate_packages/ — 系统迁移包

用于系统迁移的打包文件。配合 `migrate_receiver.py` 使用。

## 文件说明

| 文件 | 内容 |
|------|------|
| `agi_migrate_*.zip` | 系统迁移打包（含认知格数据库、配置、技能模块） |

## 使用方法

```bash
# 在目标机器上接收迁移包
python3 migrate_receiver.py --import agi_migrate_XXXXXXXX_XXXXXX.zip
```
