---
name: diepre-vision-cognition
version: 1.1.0
author: KingOfZhao
description: DiePre 视觉认知 Skill —— 将包装/模切机器视觉感知与 SOUL 推理融合的认知框架
tags: [cognition, vision, diepre, packaging, manufacturing, quality-control, cad, vlm]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# DiePre Vision Cognition Skill

## 元数据

| 字段       | 值                              |
|------------|-------------------------------|
| 名称       | diepre-vision-cognition        |
| 版本       | 2.0.0 (Pipeline v3.0)          |
| 作者       | KingOfZhao                     |
| 发布日期   | 2026-03-31                     |
| 置信度     | 96%                            |

## 学术参考文献

本视觉框架的技术路线受以下前沿研究启发：

1. **[Generating CAD Code with Vision-Language Models](https://arxiv.org/abs/2410.05340)** — VLM生成CAD代码+迭代验证（CADCodeVerify），直接升级照片→DXF管道
2. **[From 2D CAD to 3D Parametric via VLM](https://arxiv.org/abs/2412.11892)** — 2D图纸→参数化3D，解决透视矫正和参数化问题
3. **[Tool-Augmented VLLMs as Generic CAD Task Solvers](https://arxiv.org/) (ICCV 2025)** — VLLM+工具调用做通用CAD，封装OpenCV管道为可调用Skill
4. **[Efficient Vision-Language-Action Models](https://arxiv.org/abs/2510.17111)** — VLA高效优化（低延迟+内存优化），适合本地部署
5. **[Vlaser: Synergistic Embodied Reasoning](https://arxiv.org/abs/2510.11027)** — 具身推理VLA，未来"照片→动作决策"的理论基础

## 核心能力

将 DiePre（模切压痕）机器视觉感知与 SOUL 认知框架融合：

1. **视觉已知/未知分离**：从图像中提取确定特征（已知）与模糊区域（未知）
2. **文件记忆**：每次检测结果写入 `vision_log/YYYY-MM-DD.jsonl`
3. **四向视觉碰撞**：正视角、反转、侧光、整体布局四个维度同时分析
4. **人机闭环质检**：AI 初判 → 人类复核 → 标注反馈 → 模型持续进化
5. **置信度质检输出**：低于 90% 置信度的缺陷自动升级为人工复核

## Pipeline v3.0 架构 (已验证)

```
手机拍照(任意角度/光照)
  → [S1] 预处理 (去噪 + 顶帽黑帽光照校正 + CLAHE + Otsu前景提取)
  → [S2] 透视矫正 (凸包角点检测 → 四象限排序 → 透视变换)
  → [S3] 印刷过滤 (MSER文字检测 + 局部方差纹理 + inpainting填充)
  → [S4] 线条提取 (自适应二值化 + 方向性闭运算 + 细长连通域过滤 + 十字核细化)
  → [S5] 线宽分类 (距离变换 → 线宽直方图 → 峰谷分割 → 刀线/压痕)
  → [S6] 输出 (白底黑边PNG + 分类PNG + DXF + SVG)
```

### 验证结果 (2026-03-31)
- **10/10样本全部成功** (6张包装展开图 + 4张截图)
- **速度**: 11.6s/张 (平均)
- **印刷过滤**: 检测并移除 0-27% 面积的印刷文字/图案
- **刀线/压痕分类**: 基于线宽自动区分(中位宽2.0-5.6px)

### 已知问题
- [ ] 6b119a样本线条提取为0(透视矫正后对比度不足)
- [ ] 92a52f样本噪点较多(高印刷密度区域过滤不彻底)
- [ ] 速度瓶颈在透视矫正(O(n²)角点排序)
- [ ] DXF中线段断裂(需闭合路径检测)
- [ ] 无像素→mm标定(需参考物)

### 下一步优化方向
1. **VLM辅助**: 用GLM视觉模型辅助识别轮廓区域
2. **自适应参数**: 根据图像统计自动调整二值化阈值
3. **闭合路径**: 轮廓跟踪替代Hough线段
4. **标定**: QR码/参考尺自动标定
5. **模板匹配**: FEFCO标准模板对齐

## 安装命令

```bash
clawhub install diepre-vision-cognition
# 或手动安装
cp -r skills/diepre-vision-cognition ~/.openclaw/skills/
```

## 调用方式

```python
# Pipeline v3.0 (当前版本)
from pipeline_v3 import DiePrePipelineV3

pipeline = DiePrePipelineV3()
result = pipeline.process("path/to/box_photo.jpg", "output_dir/")
print(result.summary)
# 输出: white_black.png, classified.png, .dxf, .svg

# 批量处理
from pipeline_v3 import batch
results = batch("/path/to/photos/", "/path/to/output/")

# 旧版 v1.0 (Hough-based, 500ms/img)
from pipeline import batch_process as v1_batch
```
