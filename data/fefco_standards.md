# FEFCO标准模板库

> 用于DiePre Pipeline的结构化匹配和验证
> 2026-03-31 VLM分析发现: 4个样本均为FEFCO 0215/0216系列

## FEFCO国际运输包装标准

### 概述
FEFCO (European Federation of Corrugated Board Manufacturers) 定义了国际标准纸箱代码。

### DiePre项目相关的主要FEFCO代码

#### 0200系列: 管式纸箱 (Tube-style)

| FEFCO | 名称 | 特征 | 应用 |
|-------|------|------|------|
| **0200** | 半开槽箱 (Regular Slotted Case) | 四片式, 上下翼可折叠 | 最常见, 电商标准 |
| **0201** | RSC标准箱 | 0200的变体, 翼等长 | 快递箱 |
| **0203** | 全叠翼箱 | 上下翼完全覆盖 | 重物保护 |
| **0204** | 全叠翼+加固 | 额外加固耳 | 需加固场景 |
| **0205** | 半叠翼箱 | 翼部分重叠 | 中型物品 |
| **0209** | 嵌套箱 | 可堆叠嵌套 | 节省空间 |
| **0210** | 盖板箱 | 分离式盖板 | 大型物品 |
| **0211** | 内箱 | 容器内部 | 配合外箱 |
| **0212** | 外箱 | 容器外部 | 配合内箱 |
| **0214** | 拱形盖箱 | 拱形顶盖 | 特殊形状 |
| **0215** | 插入式箱 (Tuck-top) | 插舌封口 | **电子消费品** |
| **0216** | 带提手插入箱 | 插入式+提手 | **电子产品快递** |
| **0217** | 多层插入箱 | 多层折叠 | 高度可调 |

#### 0300系列: 盘式纸箱 (Tray-style)

| FEFCO | 名称 | 特征 |
|-------|------|------|
| 0300 | 标准托盘 | 四面低矮 |
| 0301 | 自锁托盘 | 翼互锁 |
| 0302 | 带盖托盘 | 分离盖板 |
| 0307 | 五面托盘 | 五面结构 |
| 0308 | 六面托盘 | 完全封闭 |

#### 0400系列: 折叠纸箱 (Foldable)

| FEFCO | 名称 | 特征 |
|-------|------|------|
| 0401 | 折叠纸箱 | 可平折存放 |
| 0402 | 自立式折叠 | 组装后自立 |
| 0409 | 折叠托盘 | 折叠式托盘 |

#### 0500系列: 滑入式 (Slide)

| FEFCO | 名称 | 特征 |
|-------|------|------|
| 0501 | 上下滑入 | 盖+体 |
| 0502 | 箱体+内衬 | 双层 |
| 0503 | 侧面滑入 | 侧面开口 |
| 0509 | 书型盒 | 书式翻盖 |
| 0510 | 钢琴翻盖 | 翻盖式 |
| 0511 | 底部折入式 | 底部折叠 |

#### 0600系列: 刚性箱 (Rigid)

| FEFCO | 名称 | 特征 |
|-------|------|------|
| 0601 | 天地盖 | 分体盖 |
| 0602 | 书型盒 | 翻盖 |
| 0607 | 三角盒 | 特殊形状 |

## VLM识别后的参数映射

基于VLM识别的FEFCO类型, 自动调整Pipeline参数:

```python
FEFCO_PARAMS = {
    "0200": {
        "flap_count": 4,           # 上下各2翼
        "cut_lines_ratio": 0.4,    # 刀线占比
        "crease_lines_ratio": 0.4, # 压痕占比
        "tuck_flap": False,
        "handle": False,
    },
    "0215": {
        "flap_count": 6,           # 上插舌+侧翼+底翼
        "cut_lines_ratio": 0.35,
        "crease_lines_ratio": 0.45,
        "tuck_flap": True,
        "tuck_length_ratio": 0.15, # 插舌长度/箱体宽度
        "handle": False,
    },
    "0216": {
        "flap_count": 7,           # +提手切割
        "cut_lines_ratio": 0.40,
        "crease_lines_ratio": 0.40,
        "tuck_flap": True,
        "handle": True,
        "handle_width_ratio": 0.10,
    },
    "0401": {
        "flap_count": 8,           # 折叠翼更多
        "cut_lines_ratio": 0.45,
        "crease_lines_ratio": 0.35,
        "tuck_flap": False,
        "fold_count": 6,
    },
    "0509": {
        "flap_count": 3,           # 书型盒
        "cut_lines_ratio": 0.30,
        "crease_lines_ratio": 0.50,
        "hinge_line": True,        # 铰接线
    },
}
```

## DiePre样本的FEFCO匹配

| 样本 | VLM识别 | 匹配FEFCO | 置信度 |
|------|---------|-----------|--------|
| 803fab | tuck-top mailer | 0215 | 0.85 |
| 6b119a | tuck-top with handle | 0216 | 0.90 |
| 92a52f | folding carton | 0215 | 0.85 |
| 185291 | tuck-top with slot | 0215 | 0.80 |

## 自动FEFCO识别规则

```python
def identify_fefco(vlm_analysis: dict) -> str:
    """基于VLM分析自动识别FEFCO类型"""
    
    # 检查tuck flap特征
    has_tuck = any(kw in str(vlm_analysis.get("flap_structure", "")) 
                   for kw in ["tuck", "插舌", "insert"])
    
    # 检查handle
    has_handle = any(kw in str(vlm_analysis.get("flap_structure", "")) 
                     for kw in ["handle", "提手"])
    
    # 检查closure type
    closure = vlm_analysis.get("closure_type", "").lower()
    
    if has_handle:
        return "0216"
    elif has_tuck:
        return "0215"
    elif "slide" in closure:
        return "0509"
    elif "tray" in str(vlm_analysis.get("box_type", "")).lower():
        return "0300"
    elif "fold" in str(vlm_analysis.get("box_type", "")).lower():
        return "0401"
    else:
        return "0201"  # 默认RSC
```

## 下一步

1. 用此模板库自动选择Pipeline参数
2. 预置FEFCO 0200-0600的DXF模板
3. 用模板匹配加速线条识别
4. 基于FEFCO类型自动生成CAD标注(尺寸标注/公差标注)
