# MEMORY.md - OpenClaw 长期记忆

> 首次创建: 2026-03-29
> 最后更新: 2026-03-29 01:36
> 维护策略: 每次有意义的心跳执行后更新

## 项目概况

- **工作空间**: `/Users/administruter/Desktop/AGI_PROJECT`
- **DiePre 数据**: `/Users/administruter/Desktop/DiePre AI/`
- **核心引擎**: `core/cognitive_core.py` (认知格哲学引擎, 568行)
- **成长引擎**: `core/growth_engine.py`, `core/diepre_growth_framework.py`
- **误差引擎**: `core/error_budget.py` (刀模误差预算, 380+行)
- **设备数据库**: `core/machine_database.py` (7台设备)
- **节点清洗**: `core/node_cleaner.py` (节点分析工具)
- **测试套件**: `tests/test_core.py` (29 tests, 27 pass)
- **数据库**: `deduction.db`, `memory.db`, `box_templates.db`

## 核心认知框架

1. **唯一不动点**: 一切可分为已知(F)和未知(V)
2. **框架可变性**: ULDS规律本身是阶段性产物，推演中发现新模式应主动推翻
3. **禁止过早收敛**: 不从预设结构出发验证，从具体问题中让模式自然涌现
4. **人机闭环**: AI需要人类通过实践反馈引入负熵

## DiePre 项目关键已知（18条）

1. 误差三分类：确定性(代数叠加) + 半确定性(RSS) + 随机(RSS)
2. RSS修正系数：安全系数k=1.15-1.25，方向因子K_dir，环境因子K_env
3. Bobst ±0.15mm vs 国产 ±0.30mm，国产贡献率45%
4. 吸湿滞后效应：吸湿/脱湿路径收缩率不同（k_absorb≠k_desorb）
5. S型收缩曲线：Logistic模型，k=40-60，MC_mid≈12%
6. 亚洲纸板塌陷补偿 +0.1-0.2mm vs 欧洲0
7. 清废临界角：θ ≈ 15° + 5° × ln(t)
8. MC兼容范围：±2% MC（保守值）
9. 扇形误差：Δfan ≈ L²/(8R) + 热膨胀 + 离心力(可忽略)
10. Bobst圆压圆热膨胀：0.05-0.08mm/30min
11. Heidelberg高刚性允许0.8mm齿刀
12. FEFCO插舌公式 = 插口 - 1.5×t - 0.5mm
13. 出口纸箱风险：MD方向不一致→相对位移
14. 卷曲方向：卷筒→MD方向，裱合板→刚性大侧
15. 含水量是精度最大敌人
16. 精度的最大敌人是含水量(MC)，非刀模图纸
17. 纸张收缩呈S型曲线
18. 刀模设计需区分目标市场（亚洲/欧洲）

## DiePre 节点数据库状态（截至2026-03-29）

- 总节点: 3746
- 已确认: 2237 (REAL_SUCCESS + INFER_SUCCESS)
- 争议: 1439 (DISPUTED + INFER_DISPUTED)
- 已清除: 70 (UNKNOWN)
- 待处理: 0 (PENDING)
- 碎片率: 22%
- 确认知识库: confirmed_knowledge_base.md (3126行)

## 成长任务队列（HEARTBEAT.md）

T1: DiePre节点处理 | T2: p_diepre深度推演 | T3: 知识合成
T4: 记忆维护 | T5: 代码任务推进

## 额度信息

- 配额每5小时重置
- 重置时间: 00:52, 05:52, 10:52, 15:52, 20:52

## 关键日期

- 2026-03-29: 首次高速成长会话（61分钟，处理3746节点，产出4个代码模块，获得18条新已知）
