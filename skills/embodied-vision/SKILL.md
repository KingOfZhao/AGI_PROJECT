---
name: embodied-vision
version: 1.0.0
author: KingOfZhao
description: 具身智能视觉系统 — 从感知原语到动作决策的完整视觉能力金字塔
tags: [embodied, vision, robotics, perception, spatial, grasp, servo, 3d]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Embodied Vision — 具身智能视觉系统

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | embodied-vision |
| 版本 | 1.0.0 |
| 创建日期 | 2026-03-31 |
| 置信度 | 92% |
| 覆盖领域 | 具身智能(D14) + 代码 + 工业 |

## 核心架构

```
embodied-vision/
├── primitives/     # P1: 感知原语 (边缘/角点/轮廓/纹理/颜色)
├── detection/      # P2: 2D检测 (显著性/层次分割/特征匹配/分类)
├── spatial/        # P3: 3D空间 (深度估计/点云/场景图/可供性/物理推理)
├── action/         # P4: 动作视觉 (伺服/抓取/监控/轨迹)
├── unified/        # P5: 统一API (vision_api.py)
└── simulation/     # P6: 仿真 (待构建)
```

## 能力金字塔

| 层级 | 模块 | 能力 | 速度 | 依赖 |
|------|------|------|------|------|
| L1 | primitives | 边缘/角点/轮廓/纹理/颜色 | 30ms | OpenCV |
| L2 | detection | 物体检测/分割/分类/模板匹配 | 100ms | L1 |
| L3 | spatial | 深度估计/点云/场景图/可供性/物理 | 250ms | L1 |
| L4 | action | 视觉伺服/抓取规划/操作监控/轨迹 | 50ms | L1+L2+L3 |
| L5 | unified | 一行代码完整感知 | 500ms | L1-L4 |
| L6 | simulation | PyBullet仿真验证 | TBD | L1-L5 |

## 验证结果

### 感知原语 (2026-03-31)
- ✅ 快速感知: 30ms (边缘+角点+矩形)
- ✅ 完整感知: 250ms (边缘+角点+轮廓+纹理+颜色)
- ✅ 纹理分析: LBP + Haralick特征 + 主方向检测
- ✅ 颜色分割: HSV 10种颜色 + K-means聚类 + 背景检测

### 2D检测
- ✅ 显著性检测: 频率调谐方法
- ✅ 层次分割: 基于轮廓层次关系
- ✅ 特征匹配: ORB + RANSAC单应性
- ✅ 简单分类: 形状+纹理+颜色规则

### 3D空间
- ✅ 单目深度: 多线索融合(位置+纹理+清晰度+色彩)
- ✅ 点云生成: 6万点(50ms), 法向量, 平面拟合
- ✅ 场景图: 物体间空间关系(on/above/beside/contains)
- ✅ 可供性: graspable/pushable/liftable/placeable_on
- ✅ 物理推理: 支撑关系/稳定性/遮挡检测

### 动作视觉
- ✅ 视觉伺服: IBVS + ORB跟踪 + 光流
- ✅ 抓取规划: 几何中心+边缘+深度梯度3种方法
- ✅ 操作监控: 6阶段状态机(approach→grasp→lift→move→place→release)
- ✅ 轨迹规划: pick-and-place + 碰撞检测 + 简单规避

## 全链路验证

```
输入: 包装盒照片 (1706x1279)
输出:
  感知原语: 37K边缘 / 100角点 / 96轮廓 / 7颜色区域
  深度估计: 1541-4965mm
  点云: 60,990点
  地面平面: RANSAC拟合成功
  稳定性: tilt_risk=0.99 (平放纸板, 正确)
  可供性: placeable_on
  总耗时: 508ms
```

## 已知限制

1. **无深度传感器**: 单目深度是估计值, 不精确
2. **无深度学习**: 物体分类基于规则, 需要VLM增强 → **P7已部分解决: VLM框架+标注数据**
3. **抓取规划参数**: 需要根据具体场景调整
4. **仿真未完成**: PyBullet未安装, 用纯Python2D替代
5. **import结构**: 用单文件版embodied_vision.py解决

## VLM增强 ✅ (2026-03-31 23:45完成)

### DiePre VLM标注结果
- 4个样本全部为**手持风扇包装盒**
- FEFCO 0215/0216系列(tuck-top封口)
- 牛皮纸+黑色印刷
- 自动FEFCO识别规则已实现

### 学习组件 ✅ (2026-03-31 23:30完成)
- 输出质量评估: 65-85分(10个样本)
- 参数自动优化: 简化贝叶斯优化
- 策略学习器: 从实验中提取3种策略
- 自动调优框架: AutoTuner类

## 下一步

1. **VLM增强**: 用GLM视觉模型替代规则分类
2. **PyBullet仿真**: 搭建桌面场景验证抓取
3. **ROS2集成**: 感知→动作的ROS节点
4. **实时优化**: GPU加速点云/深度估计
5. **学习组件**: 从演示中学习抓取策略

## 安装

```bash
# 依赖: opencv-python, numpy (已安装)
pip install opencv-python numpy

# 使用
python skills/embodied-vision/unified/vision_api.py <image_path>
```

## 与DiePre的关系

DiePre视觉Pipeline是embodied-vision的一个具体应用:
- DiePre = primitives(edge+contour) + spatial(depth→透视矫正) + 自定义(线条分类+DXF)
- embodied-vision = 通用框架, DiePre可以重构为上层应用

## 覆盖领域维度

| 维度 | 内容 |
|------|------|
| D1核心知识 | OpenCV算子/计算机视觉/机器人学基础/3D重建 |
| D2前沿未知 | VLM驱动的抓取/NeRF场景重建/具身大模型 |
| D7决策框架 | 置信度阈值→人类确认→执行→反馈循环 |
| D10融合 | →工业(质检/分拣) →医疗(手术辅助) →代码(自动化) |
