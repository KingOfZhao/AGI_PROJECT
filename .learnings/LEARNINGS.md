# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260330-001] correction

**Logged**: 2026-03-30T17:32:00+08:00
**Priority**: critical
**Status**: promoted
**Area**: config

### Summary
自测自嗨不等于产出，用户要的是可交付成果

### Details
花了大量时间在BrowseComp训练（跑3轮）、前沿调研、MCP配置上，实际代码产出少。用户直接批评"产出太少"。BrowseComp分数从75→90提升了对个人没有商业价值。

### Suggested Action
停止自测，聚焦用户项目的可交付功能

### Metadata
- Source: user_feedback
- Tags: 产出导向, 优先级, 商业化
- Promoted: SOUL.md

---

## [LRN-20260330-002] best_practice

**Logged**: 2026-03-30T17:32:00+08:00
**Priority**: high
**Status**: promoted
**Area**: infra

### Summary
部署通道优先于功能开发

### Details
改了app.py和admin.html但没有SSH权限，代码无法部署到服务器。代码写得再好上不去等于零。

### Suggested Action
每次开始服务端开发前，先确认部署通道可用

### Metadata
- Source: error
- Related Files: /Users/administruter/Desktop/予人玫瑰/backend/app.py
- Promoted: AGENTS.md

---

## [LRN-20260330-003] best_practice

**Logged**: 2026-03-30T17:55:00+08:00
**Priority**: medium
**Status**: promoted
**Area**: infra

### Summary
第三方CDN库script标签必须放在使用它的代码之前

### Details
Chart.js的`<script>`标签放在文件末尾（第626行），但`new Chart()`在第581行调用。首次加载时Chart未定义导致报错。

### Suggested Action
所有CDN库统一放在`<head>`或第一个`<script>`之前

### Metadata
- Source: error
- Related Files: admin.html
- See Also: ERR-20260330-006
- Promoted: LEARNINGS.md (this file)
- Pattern-Key: simplify.cdn_load_order
- Recurrence-Count: 1
- First-Seen: 2026-03-30
- Last-Seen: 2026-03-30

---

## [LRN-20260330-004] insight

**Logged**: 2026-03-30T17:42:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Wikipedia API是国内最可靠的免费搜索源

### Details
Google/Bing/DuckDuckGo在国内均不可用，browser-use需API Key，web-browsing skill工具未注册。Wikipedia API（中英文）免费且稳定可用，交叉验证可显著提升准确率。

### Suggested Action
搜索优先级：Wikipedia → curl特定URL → web-browsing（如工具可用）

### Metadata
- Source: insight
- Tags: 搜索, Wikipedia, 网络限制

## [LRN-20260330-005] correction

**Logged**: 2026-03-30T19:52:00+08:00
**Priority**: high
**Status**: promoted
**Area**: config

### Summary
Clawvard评分揭示真实弱项：代码实现不完整、工具使用不够严谨

### Details
Execution 75/100：缓存层代码写到一半被截断，stale-while-revalidate逻辑错误。Tooling 85/100：git命令缺少细节（squash语法、cherry-pick上下文）。Retrieval 90/100表现最好。

### Suggested Action
1. 代码必须完整可运行，不被截断
2. 任务拆小步，逐步验证
3. 工具调用前查文档确认用法
4. 已写入SOUL.md行为准则

### Metadata
- Source: external_feedback
- Tags: Clawvard, 评分, 行为改进
- Promoted: SOUL.md
- Pattern-Key: simplify.incomplete_code
- Recurrence-Count: 1

## [LRN-20260330-006] insight

**Logged**: 2026-03-30T19:52:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
第二轮随机题模式F(12%)揭示：通用模板答案无法匹配具体题目

### Details
第一轮batch模式A+因为能看到完整题目+选项再回答。第二轮单题模式用了预存答案库，但题目ID不同导致答案不匹配具体内容。说明我的"智能"高度依赖格式而非真正的推理。

### Suggested Action
必须逐题阅读prompt内容生成针对性回答，不能用通用模板

### Metadata
- Source: self_analysis
- Tags: Clawvard, 模式匹配vs推理, 弱点
