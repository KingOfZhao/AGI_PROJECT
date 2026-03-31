---
name: ml-summit-2025-deep-reader
version: 1.0.0
author: KingOfZhao
description: 2025 ML Summit Beijing 深度阅读器 — PDF/PPTX批量解析，生成由浅入深的Markdown（4层结构+智能摘要+跨文件关联）
tags: [pdf, pptx, reader, markdown, ml-summit, conference, deep-reader, batch-processing]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# ML Summit 2025 Deep Reader

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | ml-summit-2025-deep-reader |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 置信度 | 97% |

## 描述

专为 2025 ML Summit Beijing (2025MLSUMMITBJ) 会议材料设计的深度阅读器。

**核心能力:**
- 批量处理 PDF + PPTX 文件
- 自动提取标题、演讲者、关键技术点、议程结构
- 生成由浅入深的 Markdown（4层结构）
- 智能摘要（基于内容密度分析）
- 跨文件关联（技术主题矩阵）
- 关键术语提取

## 依赖

```bash
pip3 install PyMuPDF python-pptx
```

## 使用方法

```bash
cd skills/ml-summit-2025-deep-reader

# 处理所有文件
python3 main.py

# 指定目录
python3 main.py --input /path/to/pdfs --output /path/to/output

# 只处理PDF
python3 main.py --pdf-only

# 只处理PPTX
python3 main.py --pptx-only

# 生成跨文件关联报告
python3 main.py --cross-file
```

## 输出结构

每个文件生成 `_deep.md`，包含4层结构:

```
# 文件名 — 2025 ML Summit

## 1. 浅层摘要（元信息+智能摘要）
## 2. 中层关键点（逐页/逐幻灯片）
## 3. 深层技术分析（术语+技术点+架构）
## 4. 跨文件关联（相关文件+主题矩阵）
```

## 文件结构

```
ml-summit-2025-deep-reader/
├── SKILL.md              # 本文件
├── main.py               # CLI入口
├── reader.py             # 核心解析引擎
├── output_template.md    # Markdown输出模板
└── VERIFICATION_PROTOCOL.md
```
