# OpenClaw + PCM 集成优化清单

## 🔴 BUG（必修）

### B1. 黑名单 "dex" 子串误杀
- **文件**: `scripts/openclaw_skill_scanner.py` L38
- **问题**: `"dex"` 作为子串匹配，误杀 `index-cards`、`yandex-tracker-cli`、`ag-model-usage`(含CodexBar) 等合法skill
- **影响**: 至少 4 个合法 skill 被错误拦截
- **修复**: 改用 `\bdex\b` 正则词边界匹配，或替换为更精确的 `"dex "`, `" dex"` 等

### B2. 防御性安全工具被误杀
- **文件**: `scripts/openclaw_skill_scanner.py` L46
- **问题**: `"prompt injection"` 匹配到了 `anti-injection-skill`（防注入工具）和 `pipelock`（安全防护工具），这些是**防御方**而非攻击方
- **影响**: 2 个安全防护 skill 被错误拦截
- **修复**: 黑名单检查前增加白名单例外 (`anti-`, `defense`, `guard`, `protect`, `detect`)

### B3. api_server.py 双重路由计算
- **文件**: `api_server.py` L2313-2314
- **问题**: `/api/skills/route` 同时调用 `route_skills()` 和 `route_skills_formatted()`，路由逻辑执行两次
- **修复**: 只调 `route()` 一次，格式化在服务端完成

### B4. Tag 索引分词器与主索引不一致
- **文件**: `scripts/pcm_skill_router.py` L287
- **问题**: tag 索引用 `[a-z0-9]+` (允许单字母)，主索引用 `[a-z][a-z0-9]{1,}` (要求2+字符)
- **修复**: 统一为同一正则

## 🟡 性能优化

### P1. 类别候选集过大导致结果噪声
- **文件**: `scripts/pcm_skill_router.py` L322-328
- **问题**: 类别匹配对整个类别所有 skill 平均 +3.0 分。`coding-agents-and-ides` 有 1085 个 skill，全部得到相同基础分，Top-K 结果几乎随机
- **修复**: 类别匹配仅作为候选池，不直接加分；改为：类别匹配 + 关键词命中才加分

### P2. _bigrams() 在全部候选上运行
- **文件**: `scripts/pcm_skill_router.py` L348-355
- **问题**: 对全部 candidates（可能数千个）逐一做 bigram 子串匹配
- **修复**: 先按初始分数排序取 Top-100，再对这 100 个做精细化 bigram 匹配

### P3. 未使用的 import
- **文件**: `scripts/pcm_skill_router.py` L17-18 (`os`, `math`)
- **文件**: `scripts/openclaw_skill_scanner.py` L12 (`os`)
- **修复**: 删除未使用的 import

## 🟢 质量改进

### Q1. PCM watched 索引文件过大
- **问题**: `skill_library_index.md` 包含 4842 个 skill 的完整描述，文件过大
- **修复**: 只保留类别摘要 + 每类 Top-10 代表性 skill，总量控制在 500 行内

### Q2. 路由结果缺少与用户查询的相关性解释
- **修复**: 在返回结果中增加 `relevance_summary` 字段，用一句话说明为什么推荐此 skill
