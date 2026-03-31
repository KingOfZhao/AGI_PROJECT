# Markdown 输出模板

> 此模板定义了 `_deep.md` 的标准结构

```markdown
# {filename} — 2025 ML Summit 北京

> 📅 解析时间: {timestamp}
> 📄 类型: {type} | 总页数: {total_pages}
> 👤 演讲者: {speaker}（自动提取）
> 🏷️ 关键术语: {top_terms}

---

## 1. 浅层摘要

### 元信息
- **文件**: {filename}
- **类型**: {pdf/pptx}
- **页/幻灯片数**: {total}
- **图片数**: {images}
- **总字符数**: {chars}
- **平均密度**: {chars_per_page} 字符/页

### 智能摘要
{auto_summary: 基于前3页和最后1页的自动摘要，约100-200字}

### 演讲者/主题（自动提取）
- **演讲者**: {speaker_name}
- **所属机构**: {org}（如有）
- **主题**: {main_topic}

---

## 2. 中层关键点

### Page/Slide 1 — {page_title}
{content_preview_300字}

> 🔑 关键点: {bullet_points}

### Page/Slide 2 — {page_title}
...

---

## 3. 深层技术分析

### 关键术语
| 术语 | 出现频率 | 相关页 |
|------|---------|--------|
| {term} | {count} | {pages} |

### 技术架构（如有）
{architecture_description}

### 核心论点
1. {argument_1}
2. {argument_2}
3. {argument_3}

---

## 4. 跨文件关联

### 相关文件
- [{related_file_1}]({path}) — 关联原因: {reason}
- [{related_file_2}]({path}) — 关联原因: {reason}

### 技术主题矩阵
{cross_file_topic_matrix}
```
