# DiePre VLM标注数据 — 视觉语言模型分析结果

> 生成时间: 2026-03-31 23:45
> 方法: 对每个样本使用VLM分析，提取结构化信息

## 样本1: 803fab — 手持风扇包装盒

```json
{
  "file": "803fab503407aa9fd58885c30ec832ff.jpg",
  "box_type": "mailer/产品盒(tuck-top)",
  "material": "牛皮纸卡板(棕色)",
  "colors": ["棕色(牛皮纸)", "黑色(印刷)", "白色(背景)"],
  "printed_text": [
    "Battery Insertion",
    "Belt Clip Rotation", 
    "Battery Release",
    "PRESS",
    "Adjustable Air Outlet"
  ],
  "brand": "未知(手绘风格)",
  "product": "手持风扇(Handheld Fan)",
  "flap_structure": "tuck-top封口 + 侧翼 + 底翼",
  "closure_type": "tuck-in",
  "quality": "良好",
  "dimensions": "中小型(电子设备)",
  "estimated_fefco": "0215/0216",
  "vlm_confidence": 0.85
}
```

## 样本2: 6b119a — Swalon风扇包装盒

```json
{
  "file": "6b119ad2dc8b0f107979dc11a0fa3515.jpg",
  "box_type": "带提手快递盒(mailer with handle)",
  "material": "牛皮纸卡板(棕色)",
  "colors": ["棕色(牛皮纸)", "黑色(印刷)", "白色(背景)"],
  "printed_text": [
    "swalon",
    "INOKRAFT",
    "HANDS FREE FAN",
    "Hope you love it, too.",
    "Swap on. Stay Unbound.",
    "MADE IN CHINA"
  ],
  "brand": "Swalon / INOKRAFT",
  "product": "手持免持风扇(Hands Free Fan)",
  "flap_structure": "tuck-top + 侧封翼 + 提手切割",
  "closure_type": "tuck-in + handle",
  "quality": "良好",
  "certifications": ["CE"],
  "dimensions": "中小型快递盒",
  "estimated_fefco": "0410(带提手)",
  "vlm_confidence": 0.90
}
```

## 样本3: 92a52f — Shake Break风扇包装盒

```json
{
  "file": "92a52f66546d6b97e887320e2dc06443.jpg",
  "box_type": "折叠纸盒(folding carton)",
  "material": "牛皮纸卡板(棕色)",
  "colors": ["棕色(牛皮纸)", "黑色(印刷)", "白色(背景)"],
  "printed_text": [
    "Shake Break!",
    "I'm not trying to be crispy",
    "天车",
    "Battery Insertion",
    "Belt Clip Rotation",
    "Battery Release",
    "PRESS",
    "Press & Pull",
    "Adjustable Air Outlet",
    "Only use with Infrared Swap-On Battery"
  ],
  "brand": "Shake Break / Swap-On",
  "product": "手持风扇(类似产品, 不同品牌)",
  "flap_structure": "tuck-top + 侧翼 + 底翼",
  "closure_type": "tuck-in",
  "quality": "良好",
  "special_features": ["中英混合印刷", "手绘风格"],
  "dimensions": "中小型",
  "estimated_fefco": "0215",
  "vlm_confidence": 0.85
}
```

## 样本4: 185291 — 风扇包装盒(同类)

```json
{
  "file": "1852915213047bdfaa689d458a69bb0a.jpg",
  "box_type": "tuck-top mailer",
  "material": "牛皮纸卡板(棕色)",
  "colors": ["棕色(牛皮纸)", "黑色(印刷)", "白色(背景)", "绿色(手持)"],
  "printed_text": [
    "Adjustable Air Outlet",
    "Press",
    "Battery Insertion",
    "Battery Clip Rotation",
    "1/24",
    "95+6"
  ],
  "brand": "未明确",
  "product": "手持风扇(可调速)",
  "flap_structure": "对称设计, tuck-top三片式顶盖",
  "closure_type": "tuck-in with slot",
  "quality": "良好",
  "dimensions": "中小型(电子设备)",
  "estimated_fefco": "0215/0216",
  "vlm_confidence": 0.80
}
```

## 分析总结

### 共性发现
1. **所有样本都是手持风扇包装盒** — 同类产品, 不同品牌
2. **材料统一**: 牛皮纸(kraft)卡板
3. **印刷统一**: 黑色油墨, 手绘/示意图风格
4. **结构统一**: tuck-top封口, FEFCO 0215/0216系列
5. **尺寸统一**: 中小型电子设备包装

### 对DiePre Pipeline的指导
1. **印刷过滤效果应很好** — 所有样本都是牛皮纸+黑色印刷, 对比度高
2. **刀线检测应关注tuck-flap区域** — 封口翼和侧翼的切割线
3. **压痕线在折叠处** — tuck-top有明显的折叠压痕
4. **FEFCO 0215可作为模板** — 用于结构化匹配和验证

### VLM增强Pipeline的下一步
1. 用VLM识别: 品牌名 → 自动标注
2. 用VLM识别: FEFCO类型 → 加载对应模板
3. 用VLM识别: 产品类别 → 选择最优处理参数
4. 用VLM检测: 印刷区域 → 增强过滤精度
