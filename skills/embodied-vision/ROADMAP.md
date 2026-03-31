# 具身智能视觉能力 — 全速推演路线图

> 开始: 2026-03-31 21:36
> 目标: 从零构建具身智能视觉算法体系
> 原则: 不问不解释，直接执行，每步验证后commit

## 核心认知

DiePre只是视觉能力的一个微小应用场景。真正目标是：

**视觉感知 → 空间理解 → 动作决策 → 物理交互**

这不是一个Skill，是一个完整的能力金字塔。

## 今晚推演计划

### Phase 1: 视觉基础原语 (21:36-23:00)
- [x] P0: 当前状态评估 + 路线图
- [ ] P1: 感知原语Skill — 边缘/角点/轮廓/纹理/颜色基础算子
- [ ] P2: 2D目标检测 — 物体定位+边界框+分割
- [ ] P3: 基础3D重建 — 单目深度估计 + 点云生成

### Phase 2: 空间理解 (23:00-01:00)
- [ ] P4: 场景理解 — 房间布局+物体关系图
- [ ] P5: 可供性检测 — 可抓取/可推/可开
- [ ] P6: 物理推理 — 支撑关系/稳定性/遮挡

### Phase 3: 动作视觉桥 (01:00-03:00)
- [ ] P7: 视觉伺服 — 相机-目标对齐
- [ ] P8: 抓取规划 — 抓取点+方向+力度
- [ ] P9: 操作反馈 — 工具/物体交互监控

### Phase 4: 框架整合 (03:00-06:00)
- [ ] P10: 统一视觉API — 所有原语统一接口
- [ ] P11:仿真环境 — PyBullet/Isaac场景搭建
- [ ] P12: 端到端demo — 桌面物体识别→抓取规划→执行

### Phase 5: DiePre回接 (06:00-08:00)
- [ ] P13: 用统一框架重构DiePre pipeline
- [ ] P14: 用3D理解改进透视矫正
- [ ] P15: 用物理推理改进纸板结构分析

## 执行规则

1. 每个Phase产出: Skill定义 + 可运行代码 + 验证结果
2. 依赖检查: 需要安装的包立即安装
3. 失败不停: 遇到阻碍绕过或降级，不停顿
4. 每步commit: 保证进度可追溯
5. 写log: 每个Phase结束写入推演日志

## 架构原则

```
embodied-vision/           # 根目录
├── primitives/            # 感知原语(P1)
│   ├── edge_detector.py
│   ├── corner_detector.py
│   ├── contour_analyzer.py
│   ├── texture_analyzer.py
│   └── color_segmenter.py
├── detection/             # 2D检测(P2)
│   ├── object_detector.py
│   ├── instance_segmenter.py
│   └── pose_estimator.py
├── spatial/               # 3D空间(P3-P6)
│   ├── depth_estimator.py
│   ├── point_cloud.py
│   ├── scene_graph.py
│   ├── affordance.py
│   └── physics_reasoner.py
├── action/                # 动作视觉(P7-P9)
│   ├── visual_servo.py
│   ├── grasp_planner.py
│   └── manipulation_monitor.py
├── simulation/            # 仿真(P11)
│   ├── pybullet_env.py
│   └── scenes/
└── unified/               # 统一API(P10)
    ├── vision_api.py
    └── embodied_agent.py
```

---
_开始执行。不解释，不问，不停。_
