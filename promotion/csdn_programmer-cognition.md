# 【开源】programmer-cognition：让 AI 用程序员的思维写代码

## 背景

AI 写代码的能力越来越强，但很多 Agent 存在这些问题：

- 不检查 import 是否完整就提交代码
- 裸 `except` 吞掉所有异常
- 硬编码密钥和 Token
- 写完不跑测试直接部署
- Debug 时猜→试→猜→试，没有方法论

`programmer-cognition` 把"程序员的思维方式"固化成一个可安装的 Skill。

## 核心能力

### 1. 四向代码碰撞

对每段代码从 4 个方向审查：

```
正面碰撞 → 这段代码正确实现了需求吗？有更简洁的写法吗？
反面碰撞 → 这段代码在什么情况下会崩溃？边缘 case？并发安全？
侧面碰撞 → 这段模式能复用到其他模块吗？违反 DRY 吗？
整体碰撞 → 符合项目整体架构吗？引入了不必要的耦合吗？
```

### 2. 调试方法论

```
禁止: 猜 → 试 → 猜 → 试
强制: 读日志 → 提出假设 → 验证假设 → 定位根因 → 修复 → 验证修复
```

### 3. 部署前 7 项强制检查

```
□ import 完整性    □ SQLite 安全    □ 参数校验
□ 错误处理         □ 本地验证       □ 部署顺序    □ 回滚方案
```

### 4. 6 条程序员红线（永不触碰）

```python
🔴 不硬编码密钥（用环境变量）
🔴 不裸 except（捕获具体异常）
🔴 不跳过测试（测试通过才能部署）
🔴 不直接操作生产数据库
🔴 不删除数据（trash > rm）
🔴 不在周五下午部署
```

## 基于 SOUL 哲学

这个 Skill 不是凭空设计的，它基于 SOUL 五律认知框架：

| SOUL 五律 | 程序员适配 |
|-----------|-----------|
| 已知 vs 未知 | 写代码前明确输入契约和边缘 case |
| 四向碰撞 | Code Review 四向碰撞 |
| 人机闭环 | CI 自动测试 → 人工 Review → 生产验证 |
| 文件即记忆 | docstring + CHANGELOG + debug 日志 |
| 置信度+红线 | 6 条程序员红线 |

## 快速安装

```bash
clawhub install programmer-cognition
```

## 使用示例

```python
from skills.programmer_cognition import ProgrammerCognition

dev = ProgrammerCognition(workspace=".")

# 四向代码审查
review = dev.review_code(code=snippet, context={"language": "python"})
print(review.collisions)    # 四向碰撞结果

# 调试辅助
debug = dev.debug(error_log="Traceback: ...")
print(debug.root_cause)     # 根因分析

# 部署前检查
checklist = dev.pre_deploy_check("./app/main.py", "production")
print(checklist.all_passed) # True/False
```

## 适合谁？

- OpenClaw 用户：让 Agent 写出生产级代码
- AI 编程助手开发者：给模型加入代码质量意识
- 团队 Lead：用四向碰撞做 Code Review 标准化

---

*开源认知 Skill by KingOfZhao*
*GitHub: https://github.com/KingOfZhao/AGI_PROJECT/tree/main/skills/programmer-cognition*
*安装: `clawhub install programmer-cognition`*
