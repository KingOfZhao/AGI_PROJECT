#!/usr/bin/env python3
"""
DiePre Vision Pipeline v1.0 — 手机拍照→白底黑边→CAD
完整的计算机视觉处理链路

Pipeline:
  1. 图像预处理 (去噪+白平衡+增强)
  2. 透视矫正 (自动检测四角+透视变换)
  3. 前景提取 (分离纸板 vs 背景)
  4. 线条检测 (Canny+Hough+形态学)
  5. 线条分类 (刀线/压痕/折线/桥接)
  6. 矢量化 + DXF输出
"""

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DiePreVision")


# ═══════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════

@dataclass
class PipelineConfig:
    """Pipeline参数配置"""
    # 预处理
    denoise_h: int = 10           # 非局部均值去噪
    clahe_clip: float = 2.0       # CLAHE对比度限制
    clahe_grid: int = 8           # CLAHE网格大小
    
    # 前景提取
    background_thresh_low: int = 100
    background_thresh_high: int = 255
    
    # 线条检测
    canny_low: int = 50
    canny_high: int = 150
    hough_rho: int = 1
    hough_theta: float = np.pi / 180
    hough_threshold: int = 80
    hough_min_line_len: int = 30
    hough_max_line_gap: int = 10
    
    # 分类
    cut_line_thickness: Tuple[float, float] = (0.5, 2.0)
    crease_thickness: Tuple[float, float] = (2.0, 5.0)
    
    # 输出
    output_scale_mm: float = 1.0  # 像素→毫米转换比例
    dxf_line_width: float = 0.5   # DXF线条宽度


@dataclass
class LineSegment:
    """检测到的线段"""
    x1: float; y1: float; x2: float; y2: float
    length: float
    angle: float  # 弧度
    thickness: float
    line_type: str = "unknown"  # cut/crease/fold/bridge
    confidence: float = 0.0


@dataclass
class PipelineResult:
    """Pipeline处理结果"""
    input_path: str
    output_dir: str
    success: bool
    stages: dict = field(default_factory=dict)
    lines: List[LineSegment] = field(default_factory=list)
    summary: str = ""
    duration_ms: float = 0.0
    error: str = ""


# ═══════════════════════════════════════════════════════
# Stage 1: 图像预处理
# ═══════════════════════════════════════════════════════

def preprocess(img: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """
    图像预处理: 去噪 + 白平衡 + 对比度增强
    """
    # 转RGB (如果是BGR)
    if len(img.shape) == 3 and img.shape[2] == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        rgb = img
    
    # 1. 去噪 (非局部均值)
    denoised = cv2.fastNlMeansDenoisingColored(rgb, None, h=config.denoise_h, 
                                                 hColor=config.denoise_h,
                                                 templateWindowSize=7, searchWindowSize=21)
    
    # 2. 转灰度
    gray = cv2.cvtColor(denoised, cv2.COLOR_RGB2GRAY)
    
    # 3. CLAHE 对比度增强
    clahe = cv2.createCLAHE(clipLimit=config.clahe_clip, 
                             tileGridSize=(config.clahe_grid, config.clahe_grid))
    enhanced = clahe.apply(gray)
    
    # 4. 自适应直方图均衡 (处理不均匀光照)
    equalized = cv2.equalizeHist(enhanced)
    
    return equalized


# ═══════════════════════════════════════════════════════
# Stage 2: 前景提取 (分离纸板 vs 背景)
# ═══════════════════════════════════════════════════════

def extract_foreground(gray: np.ndarray, config: PipelineConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    前景提取: 将纸板从背景中分离
    返回: (binary_mask, foreground)
    """
    # Otsu自动阈值
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 形态学操作: 去除小噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # 找到最大连通域 (纸板)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    if num_labels <= 1:
        return binary, gray
    
    # 找最大非背景区域
    max_area = 0
    max_label = 1  # 跳过背景(0)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > max_area:
            max_area = area
            max_label = i
    
    # 创建纸板mask
    mask = np.zeros_like(binary)
    mask[labels == max_label] = 255
    
    # 提取前景
    foreground = cv2.bitwise_and(gray, gray, mask=mask)
    
    return mask, foreground


# ═══════════════════════════════════════════════════════
# Stage 3: 透视矫正
# ═══════════════════════════════════════════════════════

def correct_perspective(gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    透视矫正: 检测纸板四角 → 透视变换为俯视图
    """
    # 在mask上找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        logger.warning("未检测到轮廓，跳过透视矫正")
        return gray
    
    # 取最大轮廓
    contour = max(contours, key=cv2.contourArea)
    
    # 多边形逼近
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    
    # 需要4个角点
    if len(approx) < 4:
        logger.warning(f"检测到{len(approx)}个角点(需要4)，跳过透视矫正")
        return gray
    
    # 取最外面的4个点
    if len(approx) > 4:
        # 凸包
        hull = cv2.convexHull(approx)
        approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
        if len(approx) < 4:
            return gray
    
    # 排序角点: 左上-右上-右下-左下
    points = approx.reshape(-1, 2).astype(np.float32)
    center = points.mean(axis=0)
    
    # 按角度排序
    def angle_from_center(p):
        return np.arctan2(p[1] - center[1], p[0] - center[0])
    
    sorted_points = sorted(points, key=angle_from_center)
    
    # 重新排序为: 左上-右上-右下-左下
    corners = np.array([
        sorted_points[3],  # 左上(y小x小)
        sorted_points[2],  # 右上(y小x大)
        sorted_points[1],  # 右下(y大x大)
        sorted_points[0],  # 左下(y大x小)
    ], dtype=np.float32)
    
    # 计算目标尺寸
    width_top = np.linalg.norm(corners[1] - corners[0])
    width_bottom = np.linalg.norm(corners[2] - corners[3])
    max_width = max(int(width_top), int(width_bottom))
    
    height_left = np.linalg.norm(corners[3] - corners[0])
    height_right = np.linalg.norm(corners[2] - corners[1])
    max_height = max(int(height_left), int(height_right))
    
    if max_width < 100 or max_height < 100:
        logger.warning(f"检测尺寸过小({max_width}x{max_height})，跳过矫正")
        return gray
    
    # 目标点
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype=np.float32)
    
    # 透视变换
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(gray, M, (max_width, max_height), 
                                  flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    
    logger.info(f"透视矫正: {gray.shape} → {warped.shape}")
    return warped


# ═══════════════════════════════════════════════════════
# Stage 4: 线条检测
# ═══════════════════════════════════════════════════════

def detect_lines(gray: np.ndarray, config: PipelineConfig) -> List[LineSegment]:
    """
    线条检测: Canny边缘 + Hough变换 + 线段合并
    """
    # 1. Canny边缘检测
    edges = cv2.Canny(gray, config.canny_low, config.canny_high)
    
    # 2. 形态学增强边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    
    # 3. Hough变换检测直线
    lines_raw = cv2.HoughLinesP(edges,
                                 rho=config.hough_rho,
                                 theta=config.hough_theta,
                                 threshold=config.hough_threshold,
                                 minLineLength=config.hough_min_line_len,
                                 maxLineGap=config.hough_max_line_gap)
    
    if lines_raw is None:
        logger.warning("未检测到任何线段")
        return []
    
    # 4. 转换为LineSegment
    segments = []
    for l in lines_raw:
        x1, y1, x2, y2 = l[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = np.arctan2(y2-y1, x2-x1)
        segments.append(LineSegment(
            x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
            length=length, angle=angle, thickness=1.0
        ))
    
    logger.info(f"检测到 {len(segments)} 条线段")
    return segments


# ═══════════════════════════════════════════════════════
# Stage 5: 线条分类 (刀线/压痕/折线/桥接)
# ═══════════════════════════════════════════════════════

def classify_lines(segments: List[LineSegment], config: PipelineConfig) -> List[LineSegment]:
    """
    线条分类: 基于长度、角度、邻域特征分类
    """
    if not segments:
        return segments
    
    # 统计特征
    lengths = [s.length for s in segments]
    if not lengths:
        return segments
    
    median_len = np.median(lengths)
    
    for seg in segments:
        # 基于长度的初步分类
        if seg.length < median_len * 0.3:
            seg.line_type = "bridge"  # 桥接(短线)
            seg.confidence = 0.6
        elif seg.length > median_len * 1.5:
            seg.line_type = "cut"  # 刀线(长线)
            seg.confidence = 0.8
        else:
            # 中等长度: 基于角度判断
            # 压痕通常沿纸板边缘(0°/90°方向)
            angle_deg = abs(np.degrees(seg.angle) % 180)
            if angle_deg < 15 or angle_deg > 165:
                seg.line_type = "cut"
                seg.confidence = 0.7
            elif 75 < angle_deg < 105:
                seg.line_type = "crease"
                seg.confidence = 0.65
            else:
                seg.line_type = "fold"
                seg.confidence = 0.55
    
    return segments


# ═══════════════════════════════════════════════════════
# Stage 6: 白底黑边可视化
# ═══════════════════════════════════════════════════════

def generate_white_black_vis(gray: np.ndarray, segments: List[LineSegment]) -> np.ndarray:
    """
    生成白底黑边图
    """
    # 白底
    h, w = gray.shape
    result = np.ones((h, w), dtype=np.uint8) * 255
    
    # 画黑色线条
    type_colors = {
        "cut": 0,        # 黑色=刀线
        "crease": 100,   # 深灰=压痕
        "fold": 150,     # 灰色=折线
        "bridge": 200,   # 浅灰=桥接
        "unknown": 128,  # 中灰=未知
    }
    
    for seg in segments:
        color = type_colors.get(seg.line_type, 128)
        thickness = 2 if seg.line_type == "cut" else 1
        cv2.line(result, (int(seg.x1), int(seg.y1)), (int(seg.x2), int(seg.y2)),
                 color, thickness)
    
    return result


# ═══════════════════════════════════════════════════════
# Stage 7: DXF输出
# ═══════════════════════════════════════════════════════

def generate_dxf(segments: List[LineSegment], config: PipelineConfig) -> str:
    """
    生成DXF格式CAD文件 (最小有效DXF)
    """
    lines = [
        "0",
        "SECTION",
        "2",
        "ENTITIES",
    ]
    
    type_layers = {
        "cut": "DIE_LINE",
        "crease": "CREASE_LINE",
        "fold": "FOLD_LINE",
        "bridge": "BRIDGE",
        "unknown": "UNKNOWN",
    }
    
    for seg in segments:
        layer = type_layers.get(seg.line_type, "UNKNOWN")
        # LINE entity
        lines.extend([
            "0", "LINE",
            "8", layer,  # Layer
            "10", f"{seg.x1 / config.output_scale_mm:.2f}",
            "20", f"{seg.y1 / config.output_scale_mm:.2f}",
            "11", f"{seg.x2 / config.output_scale_mm:.2f}",
            "21", f"{seg.y2 / config.output_scale_mm:.2f}",
        ])
    
    lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 主Pipeline
# ═══════════════════════════════════════════════════════

def run_pipeline(input_path: str, output_dir: str = None, 
                 config: PipelineConfig = None) -> PipelineResult:
    """
    完整Pipeline: 照片 → 白底黑边 + DXF
    """
    t0 = time.time()
    
    input_path = Path(input_path)
    if not input_path.exists():
        return PipelineResult(input_path=str(input_path), output_dir="", 
                             success=False, error="文件不存在")
    
    if config is None:
        config = PipelineConfig()
    
    if output_dir is None:
        output_dir = input_path.parent / "output"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = PipelineResult(
        input_path=str(input_path),
        output_dir=str(output_dir),
        success=False,
    )
    
    try:
        # 读取图像
        logger.info(f"读取: {input_path.name}")
        img = cv2.imread(str(input_path))
        if img is None:
            result.error = "无法读取图像"
            return result
        result.stages["original_size"] = f"{img.shape[1]}x{img.shape[0]}"
        
        # Stage 1: 预处理
        logger.info("Stage 1: 图像预处理...")
        gray = preprocess(img, config)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_1_preprocessed.png"), gray)
        
        # Stage 2: 前景提取
        logger.info("Stage 2: 前景提取...")
        mask, foreground = extract_foreground(gray, config)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_2_mask.png"), mask)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_2_foreground.png"), foreground)
        
        # Stage 3: 透视矫正
        logger.info("Stage 3: 透视矫正...")
        warped = correct_perspective(foreground, mask)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_3_corrected.png"), warped)
        
        # Stage 4: 线条检测
        logger.info("Stage 4: 线条检测...")
        segments = detect_lines(warped, config)
        
        # Stage 5: 线条分类
        logger.info("Stage 5: 线条分类...")
        segments = classify_lines(segments, config)
        
        # 统计
        type_counts = {}
        for s in segments:
            type_counts[s.line_type] = type_counts.get(s.line_type, 0) + 1
        logger.info(f"线条分类: {type_counts}")
        
        # Stage 6: 白底黑边
        logger.info("Stage 6: 生成白底黑边...")
        white_black = generate_white_black_vis(warped, segments)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_4_white_black.png"), white_black)
        
        # Stage 7: DXF
        logger.info("Stage 7: 生成DXF...")
        dxf_content = generate_dxf(segments, config)
        dxf_path = output_dir / f"{input_path.stem}.dxf"
        dxf_path.write_text(dxf_content)
        
        # 可视化(彩色分类)
        vis = cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)
        colors = {"cut": (0, 0, 255), "crease": (0, 255, 0), 
                  "fold": (255, 0, 0), "bridge": (0, 255, 255)}
        for seg in segments:
            color = colors.get(seg.line_type, (128, 128, 128))
            cv2.line(vis, (int(seg.x1), int(seg.y1)), (int(seg.x2), int(seg.y2)),
                     color, 2)
        cv2.imwrite(str(output_dir / f"{input_path.stem}_5_visualized.png"), vis)
        
        result.success = True
        result.lines = segments
        result.duration_ms = (time.time() - t0) * 1000
        
        # 摘要
        cut_count = type_counts.get("cut", 0)
        crease_count = type_counts.get("crease", 0)
        result.summary = (
            f"✅ {input_path.name}: "
            f"总{len(segments)}线(刀{cut_count}/压{crease_count}/桥{type_counts.get('bridge',0)}/折{type_counts.get('fold',0)}) "
            f"| {result.duration_ms:.0f}ms"
        )
        
    except Exception as e:
        logger.error(f"Pipeline失败: {e}")
        result.error = str(e)
        result.duration_ms = (time.time() - t0) * 1000
    
    return result


def batch_process(input_dir: str, output_dir: str = None, 
                  extensions: list = None) -> list:
    """批量处理"""
    input_dir = Path(input_dir)
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG"]
    
    files = sorted([f for f in input_dir.iterdir() if f.suffix in extensions])
    logger.info(f"发现 {len(files)} 个图片文件")
    
    results = []
    for f in files:
        result = run_pipeline(str(f), output_dir)
        print(result.summary if result.success else f"❌ {result.error}")
        results.append(result)
    
    # 汇总
    ok = sum(1 for r in results if r.success)
    print(f"\n{'='*50}")
    print(f"✅ 成功: {ok}/{len(results)}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 单文件
        result = run_pipeline(sys.argv[1])
        print(result.summary)
    else:
        # 批量处理桌面样本
        results = batch_process("/Users/administruter/Desktop",
                                "/Users/administruter/Desktop/DiePre AI/vision_pipeline/output")
