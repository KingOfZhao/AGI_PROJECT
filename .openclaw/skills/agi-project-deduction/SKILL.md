---
name: agi-project-deduction
description: 自动扫描 AGI_PROJECT 所有子项目，调用伟人竞技场进行全面推演，生成报告并记录
version: 1.0
---

# AGI_PROJECT 自动推演

## 触发条件
- 每 2 小时自动执行（cron 调度）
- 手动触发：「开始 AGI 项目推演」

## 执行步骤

### Phase 1: 项目扫描
扫描以下路径，收集项目状态：
- `/Users/administruter/Desktop/AGI_PROJECT/` — 主项目
- `/Users/administruter/Desktop/AGI_PROJECT/项目清单/` — 子项目清单
- `/Users/administruter/Desktop/AGI_PROJECT/data/growth_results/` — 成长结果
- `/Users/administruter/Desktop/AGI_PROJECT/scripts/` — 核心脚本状态

重点读取：
- `ROADMAP.md` — 当前路线图
- `data/conversation_memory.jsonl` — 最近对话记忆（最新10条）
- `.autonomous_growth_state.json` — 自主成长引擎状态

### Phase 2: 伟人竞技场推演
对每个活跃项目调用 `greatman-arena-deduction` skill，输出：
- 当前状态评估
- 阻塞点分析
- 多视角洞见
- 优先级建议

### Phase 3: 报告生成
将推演结果写入：
```
/Users/administruter/Desktop/AGI_PROJECT/data/growth_results/growth_p_deduction_YYYYMMDD_HHMMSS.md
```

报告格式：
```markdown
# AGI_PROJECT 推演报告 [时间戳]

## 扫描结果
- 活跃项目数: N
- 阻塞问题数: N
- 成长任务队列: N

## 各项目推演
[伟人竞技场输出]

## 优先行动建议（TOP 5）
1. ...
```

### Phase 4: 通知
通过微信发送推演摘要（如微信已连接）
