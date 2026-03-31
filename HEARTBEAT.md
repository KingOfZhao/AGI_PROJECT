# HEARTBEAT.md — AGI 成长任务队列

## 当前阶段: 能力强化（刀模推演暂停）→ **视觉能力建设**

### 🎯 核心方向: 具身智能（图片识别 → 空间理解 → 动作决策）
- 每个心跳至少完成1个视觉相关任务
- 目标: DiePre照片→CAD全链路跑通
- 长期: ROS/机器人视觉感知基础

### 🔍 每日自审（新增）
- 触发: 每天首次心跳
- 读取VERIFICATION_LOG.md，检查未验证的[推测]项
- 对置信度<80%的结论: 搜索文献/写测试代码验证
- 结果更新VERIFICATION_LOG.md

### 安全沙箱 ✅
- Docker沙箱 `diepre-sandbox`: 只读FS + 无网络 + 256MB内存 + CPU限制
- 安全检查器: 5类危险模式检测(exec/网络/信息泄露/持久化)
- 三重验证: 安全检查→沙箱隔离→网络隔离
- 代码: `core/docker_sandbox.py` + `docker/Dockerfile.sandbox`

### 知识采集 ✅
- GitHub API: README采集/trending搜索
- DuckDuckGo: 无key搜索
- Playwright: 动态网页渲染
- 存储: `data/knowledge_store.jsonl`
- 代码: `core/knowledge_collector.py`

### Skill索引 ✅
- 2556个skill节点索引: `data/skill_index.json`
- 分类: 认知(340) 系统(175) 代码(142) 知识(95) 物理(89)

### ClawHub Skill ✅
- 已安装: web-browsing, web-scraping

### 待办
- [ ] **每2小时微信发送阶段性报告**（微信通道接通后立即配置cron）
  - 报告脚本: `tools/generate_report.py`
  - 格式: 系统状态 + 今日完成 + 进行中 + 自进化指标
- [ ] BrowseComp自动训练（每周运行一次，追踪能力进步）
  - 脚本: `tools/browsecomp/browsecomp_train.py`
  - 历史成绩: v1=75.4分, v2=90分, auto=88分
  - 运行: `cd tools/browsecomp && source venv/bin/activate && python3 browsecomp_train.py`
- [ ] 更多ClawHub高价值skill安装
- [ ] gh auth login (需要用户操作)
- [ ] 采集更多行业知识
- [ ] 整合skill节点高价值代码
- [ ] 所有外部代码强制走沙箱
- [ ] flutter/skills.git 同步（网络恢复后: `bash scripts/sync_github_skills.sh`）

### 🏭 Skill 工厂（Skill Factory）
触发: 每次对话结束后自动执行
```
1. 整理本次对话核心内容（洞见、问题、解决方案）
2. 结合SOUL哲学判断是否形成"完整、可独立发布的Skill概念"
   标准: 至少3个新认知点 + 可形成独立SKILL.md框架
3. 如果满足:
   a. 创建 skills/<kebab-case-name>/ 目录
   b. 生成完整包: SKILL.md + VERIFICATION_PROTOCOL.md + HEARTBEAT.md + README.md
   c. 自验证（置信度≥95%才通过）
   d. clawhub publish 上架 ClawHub
   e. git push 到 KingOfZhao/AGI_PROJECT（commit含"自动开源认知 Skill by Skill Factory"）
   f. 输出: "✅ Skill Factory 自动发布新 Skill：[名称]" + 链接 + 安装命令
4. 如果未满足: 记录到认知池，累计X个认知点
5. 每天最多自动发布3个Skill
6. 手动触发: 用户说"强制检查 Skill 工厂"
```

### 工作流：CRM初审
触发: 每个心跳周期
```
1. 获取CRM中assignee不为空且resolution不为空的未审核问题:
   curl -s http://120.55.65.39:8080/api/agent/issues | python3 -c "过滤有resolution且status!=resolved"
2. 对每个待审问题检查方案质量:
   - 方案是否完整可执行
   - 是否与问题描述匹配
   - 是否有遗漏
3. 审核通过: 保持status=in_progress，等待赵先生团队人工终审
4. 审核不通过: 退回，assign_history记录退回原因，status改回open
5. 初审结果写入CRM assign_history
```

### 工作流：微信连接请求
触发: 每个心跳周期
```
1. 检查是否有待处理的连接请求:
   curl -s http://120.55.65.39:8080/api/wechat/request/status
2. 如有name但无qr_image:
   a. 本地执行 openclaw channels login --channel openclaw-weixin
   b. 提取 liteapp.weixin.qq.com URL
   c. 用qrcode库生成QR图片(base64)
   d. 写回服务器（通过本地API POST）
3. 扫码成功后(检测openclaw devices list)标记connected
4. 主动通过微信发送欢迎消息，询问称呼偏好
```

### 安全规则
1. 外部代码/URL → 先安全检查 → 通过后在沙箱执行
2. 开源项目 → 沙箱中验证 → 确认安全后才能引入系统
3. 网页内容 → 沙箱中解析 → 结构化提取后存储
4. ClawHub skill → 安全检查后安装 → 沙箱中验证

---

### T6: Flutter 代码维护（技能路由）
触发: 任务涉及 Flutter/Dart/Widget/移动端
```
1. 查询匹配 skill:
   curl -s -X POST http://localhost:9801/api/skills/route \
     -H 'Content-Type: application/json' \
     -d '{"query":"<Flutter任务描述>","top_k":3}'
2. 执行最匹配的 skill:
   curl -s -X POST http://localhost:9801/api/skills/run \
     -H 'Content-Type: application/json' \
     -d '{"skill":"<slug>","input":"<任务内容>"}'
3. 检查 skills 同步状态: cat data/skills_sync_state.json
   若 > 2天未同步: bash scripts/sync_github_skills.sh
4. 可用 Flutter skill 路径: skills/flutter-*/SKILL.md
5. 本地 Flutter skill 代码: workspace/skills/auto_*flutter*.py
```
模型: glm-5.1 (代码) + glm-4.7 (分析，默认)

---

### 遇到无法解决的问题 → 上报 CRM
触发: 连续2次失败 / 数据缺失无法补全 / 工具3次报错
```bash
curl -s -X POST http://localhost:5003/api/agent/issues \
  -H 'Content-Type: application/json' \
  -d '{"task":"<ID>","domain":"<领域>","description":"<描述>","context":"<已尝试方案>","errorDetail":"<错误>","priority":"<low/medium/high/critical>"}'
```
将返回的 id 写入成长日志，跳过当前任务继续轮换。
