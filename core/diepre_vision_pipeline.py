"""
diepre_vision_pipeline.py — DiePre 视觉处理管道
照片 → 白底黑边技术图纸 → CAD(DXF/SVG)

阶段1: 图像预处理 (photo → binary technical drawing)
阶段2: 线条提取 (binary → vector lines)
阶段3: CAD生成 (vector lines → DXF/SVG)

HEARTBEAT阶段: 视觉能力建设
样本路径: /Users/administruter/Desktop/*.jpg (6张)
"""

import os
import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class PipelineStage(Enum):
    RAW = "raw"                    # 原始照片
    PREPROCESSED = "preprocessed"  # 预处理(去噪/增强)
    BINARIZED = "binarized"        # 二值化(白底黑边)
    CONTOURS = "contours"          # 轮廓提取
    VECTORIZED = "vectorized"      # 矢量化
    CAD = "cad"                    # CAD输出


class LineType(Enum):
    CUT = "cut"          # 切割线(实线)
    FOLD = "fold"        # 折叠线(虚线)
    CREASE = "crease"    # 压痕线(点划线)
    SLOT = "slot"        # 插槽
    UNKNOWN = "unknown"  # 未分类


@dataclass
class VectorLine:
    """矢量化线条"""
    points: List[Tuple[float, float]]  # [(x1,y1), (x2,y2), ...]
    line_type: LineType = LineType.UNKNOWN
    length_px: float = 0
    angle_deg: float = 0
    confidence: float = 0.0

    def __post_init__(self):
        if len(self.points) >= 2:
            p1, p2 = self.points[0], self.points[-1]
            self.length_px = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            self.angle_deg = math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0]))


@dataclass
class ProcessingResult:
    """处理结果"""
    stage: PipelineStage
    success: bool
    output_path: str = ""
    error: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class ImageDimensions:
    """检测到的尺寸标注"""
    value_mm: float
    start_px: Tuple[int, int]
    end_px: Tuple[int, int]
    orientation: str  # "H" or "V"
    label: str = ""


class DiePreVisionPipeline:
    """
    DiePre 视觉处理管道
    
    输入: 手机拍摄的二维包装盒展开图照片
    输出: 白底黑边技术图纸 + DXF/SVG CAD文件
    """

    # 图像预处理参数
    TARGET_DPI = 150            # 目标DPI
    MIN_LINE_LENGTH_PX = 20     # 最小线段长度(像素)
    CANNY_LOW = 50              # Canny边缘检测低阈值
    CANNY_HIGH = 150            # Canny边缘检测高阈值
    BLUR_KERNEL = 5             # 高斯模糊核大小
    MORPH_KERNEL = 3            # 形态学操作核大小

    # 文件扩展名
    INPUT_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    OUTPUT_DIR = "data/vision_output"

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or self.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.results: List[ProcessingResult] = []
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖库"""
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            self._cv2_available = False

        try:
            import numpy as np
            self._numpy_available = True
        except ImportError:
            self._numpy_available = False

        try:
            from PIL import Image
            self._pil_available = True
        except ImportError:
            self._pil_available = False

    @property
    def status(self) -> Dict:
        """管道状态"""
        return {
            "cv2": self._cv2_available,
            "numpy": self._numpy_available,
            "pil": self._pil_available,
            "output_dir": self.output_dir,
            "results_count": len(self.results),
        }

    def quality_check(self, binary_path: str) -> Dict:
        """
        管道输出质量评估
        
        返回: {line_ratio, components, noise_ratio, density, rating, issues}
        """
        import cv2, numpy as np
        
        img = cv2.imread(binary_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"error": f"Cannot read: {binary_path}"}
        
        h, w = img.shape
        line_ratio = np.sum(img == 0) / img.size * 100
        
        _, labels = cv2.connectedComponents(img)
        n_components = labels.max()
        density = n_components / (h * w) * 10000
        
        unique, counts = np.unique(labels, return_counts=True)
        small_components = np.sum(counts[1:] < 20)
        noise_ratio = small_components / max(n_components, 1) * 100
        
        issues = []
        if line_ratio > 15: issues.append('too_much_noise')
        if line_ratio < 1: issues.append('too_few_lines')
        if noise_ratio > 50: issues.append('high_noise')
        if density > 5: issues.append('fragmented')
        
        rating = 'clean' if not issues else ('acceptable' if len(issues) <= 1 else 'poor')
        
        return {
            "line_pixel_ratio": round(line_ratio, 1),
            "connected_components": int(n_components),
            "noise_ratio": round(noise_ratio, 1),
            "fragmentation_density": round(density, 2),
            "rating": rating,
            "issues": issues,
        }

    def _estimate_skew(self, gray: 'np.ndarray') -> float:
        """
        估计图像倾斜角度(仅对小角度准确, ±10°以内)
        返回需要旋转的度数(正值=逆时针)
        """
        import cv2, numpy as np
        
        edges = cv2.Canny(gray, 30, 100)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        if lines is None:
            return 0.0
        
        angles = np.array([l[0][1] for l in lines])
        
        # 10° bins, find strongest peak
        bins = np.arange(0, np.pi, np.pi/36)  # 5° resolution
        hist, _ = np.histogram(angles, bins=bins)
        
        # The dominant peak should be near 0° (horizontal) or 90° (vertical)
        top2 = np.argsort(hist)[-2:]
        for idx in top2:
            theta = (bins[idx] + np.pi/72) * 180 / np.pi
            # Normalize to -45..45 range
            skew = theta
            while skew > 45: skew -= 90
            while skew < -45: skew += 90
            
            # Only trust if the peak is significantly dominant (>30% of total)
            if hist[idx] / len(lines) > 0.3 and abs(skew) < 10:
                return skew
        
        return 0.0

    def preprocess(self, input_path: str) -> ProcessingResult:
        """
        阶段1: 图像预处理
        
        - 读取并缩放到目标DPI
        - 转灰度
        - 高斯模糊去噪
        - 自适应直方图均衡化(CLAHE)
        - 透视校正(如果检测到明显倾斜)
        """
        if not self._pil_available:
            return ProcessingResult(PipelineStage.PREPROCESSED, False, 
                                   error="PIL not available")

        try:
            from PIL import Image, ImageFilter, ImageEnhance
            import numpy as np
            
            img = Image.open(input_path).convert('RGB')
            original_size = img.size
            
            # CLAHE增强(用numpy模拟)
            import cv2
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            
            # Auto-deskew (small rotation correction, ±10°)
            skew_angle = self._estimate_skew(gray)
            if abs(skew_angle) > 0.5:  # Only correct if skew > 0.5°
                (h_rot, w_rot) = gray.shape[:2]
                center = (w_rot // 2, h_rot // 2)
                M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w_rot, h_rot), 
                                       borderMode=cv2.BORDER_REPLICATE)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)

            # Auto-crop: 检测内容边界, 去除多余白边
            # 先做粗略二值化找边界
            temp_binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                 cv2.THRESH_BINARY_INV, 31, 10)
            coords = cv2.findNonZero(temp_binary)
            cropped = gray
            crop_info = "none"
            if coords is not None:
                x, y, bw, bh = cv2.boundingRect(coords)
                margin = 30
                x1, y1 = max(0, x - margin), max(0, y - margin)
                x2, y2 = min(gray.shape[1], x + bw + margin), min(gray.shape[0], y + bh + margin)
                # 只在裁剪面积减少>10%时才裁剪(避免过度裁剪)
                if bw * bh < gray.shape[0] * gray.shape[1] * 0.90:
                    cropped = gray[y1:y2, x1:x2]
                    crop_info = f"({x1},{y1},{x2},{y2})"
            
            # 高斯模糊去噪
            blurred = cv2.GaussianBlur(cropped, (self.BLUR_KERNEL, self.BLUR_KERNEL), 0)
            
            # 保存预处理结果
            output_path = self._output_path(input_path, "preprocessed", ".png")
            cv2.imwrite(output_path, blurred)
            
            return ProcessingResult(
                PipelineStage.PREPROCESSED, True, output_path,
                metadata={
                    "original_size": original_size,
                    "output_size": (blurred.shape[1], blurred.shape[0]),
                    "format": "grayscale",
                    "auto_crop": crop_info,
                    "deskew_angle": round(skew_angle, 2),
                }
            )
        except Exception as e:
            return ProcessingResult(PipelineStage.PREPROCESSED, False, error=str(e))

    def binarize(self, input_path: str, 
                 method: str = "adaptive",
                 block_size: int = 15,
                 c_offset: int = 5) -> ProcessingResult:
        """
        阶段2: 二值化(白底黑边)
        
        方法:
        - adaptive: 自适应阈值(适合光照不均匀的照片)
        - otsu: Otsu全局阈值(适合光照均匀的照片)
        - manual: 固定阈值
        
        后处理:
        - 形态学开运算(去小噪点)
        - 形态学闭运算(连接断裂线条)
        - 反色(确保白底黑边)
        """
        if not self._cv2_available:
            return ProcessingResult(PipelineStage.BINARIZED, False,
                                   error="OpenCV not available")

        try:
            import cv2
            import numpy as np
            
            # 读取(可能是彩色或灰度)
            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return ProcessingResult(PipelineStage.BINARIZED, False,
                                       error=f"Cannot read: {input_path}")

            # 自适应阈值二值化
            if method == "adaptive":
                binary = cv2.adaptiveThreshold(
                    img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV, block_size, c_offset
                )
            elif method == "otsu":
                _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)

            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.MORPH_KERNEL, self.MORPH_KERNEL))
            # 开运算: 去噪点
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
            # 闭运算: 连接断裂线
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

            # 确保白底黑边
            # THRESH_BINARY_INV 产生: 线条=白(255), 背景=黑(0)
            # 我们需要: 白底(255) + 黑线条(0), 所以始终反转
            black_ratio = np.sum(binary == 255) / binary.size
            binary = cv2.bitwise_not(binary)  # 白底黑边

            output_path = self._output_path(input_path, "binary", ".png")
            cv2.imwrite(output_path, binary)

            return ProcessingResult(
                PipelineStage.BINARIZED, True, output_path,
                metadata={
                    "method": method,
                    "block_size": block_size,
                    "line_pixel_ratio": round(black_ratio, 4),
                }
            )
        except Exception as e:
            return ProcessingResult(PipelineStage.BINARIZED, False, error=str(e))

    def extract_contours(self, input_path: str,
                         min_length: Optional[int] = None) -> ProcessingResult:
        """
        阶段3: 轮廓/线条提取
        
        - Canny边缘检测
        - Hough直线检测
        - 轮廓查找(用于复杂曲线)
        - 合并为统一的线条列表
        """
        if not self._cv2_available:
            return ProcessingResult(PipelineStage.CONTOURS, False,
                                   error="OpenCV not available")

        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return ProcessingResult(PipelineStage.CONTOURS, False,
                                       error=f"Cannot read: {input_path}")

            min_len = min_length or self.MIN_LINE_LENGTH_PX

            # Canny边缘检测
            edges = cv2.Canny(img, self.CANNY_LOW, self.CANNY_HIGH)

            # Hough直线检测
            lines_p = cv2.HoughLinesP(
                edges, rho=1, theta=np.pi/180,
                threshold=50, minLineLength=min_len, maxLineGap=10
            )

            vector_lines = []
            if lines_p is not None:
                for line in lines_p:
                    x1, y1, x2, y2 = line[0]
                    vl = VectorLine(
                        points=[(float(x1), float(y1)), (float(x2), float(y2))]
                    )
                    if vl.length_px >= min_len:
                        vector_lines.append(vl)

            # 轮廓查找(用于封闭图形)
            contours, hierarchy = cv2.findContours(
                img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )

            # 可视化
            vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            for vl in vector_lines:
                p1 = (int(vl.points[0][0]), int(vl.points[0][1]))
                p2 = (int(vl.points[-1][0]), int(vl.points[-1][1]))
                color = (0, 255, 0)  # 绿色=检测到的线
                cv2.line(vis, p1, p2, color, 1)

            # 绘制轮廓(蓝色)
            cv2.drawContours(vis, contours, -1, (255, 0, 0), 1)

            output_path = self._output_path(input_path, "contours", ".png")
            cv2.imwrite(output_path, vis)

            return ProcessingResult(
                PipelineStage.CONTOURS, True, output_path,
                metadata={
                    "lines_detected": len(vector_lines),
                    "contours_detected": len(contours),
                    "canny_low": self.CANNY_LOW,
                    "canny_high": self.CANNY_HIGH,
                }
            )
        except Exception as e:
            return ProcessingResult(PipelineStage.CONTOURS, False, error=str(e))

    def generate_svg(self, input_path: str) -> ProcessingResult:
        """
        阶段4: 生成SVG (with cut/fold classification)
        """
        if not self._cv2_available:
            return ProcessingResult(PipelineStage.CAD, False,
                                   error="OpenCV not available")

        try:
            import cv2
            import numpy as np
            
            # 获取图像尺寸
            img_gray = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img_gray is None:
                return ProcessingResult(PipelineStage.CAD, False, error="Cannot read image")
            h, w = img_gray.shape[:2]

            # Canny + Hough for line detection
            edges = cv2.Canny(img_gray, self.CANNY_LOW, self.CANNY_HIGH)
            lines_p = cv2.HoughLinesP(
                edges, rho=1, theta=np.pi/180,
                threshold=50, minLineLength=self.MIN_LINE_LENGTH_PX, maxLineGap=10
            )

            # 线条分类
            cut_mask, fold_mask = self.classify_lines(input_path)
            h_mask, w_mask = cut_mask.shape

            # 生成SVG
            svg_lines = [
                f'<?xml version="1.0" encoding="UTF-8"?>',
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                f'  <rect width="100%" height="100%" fill="white"/>',
            ]

            # 按mask分类线条
            cut_lines = []
            fold_lines = []
            if lines_p is not None:
                for line in lines_p:
                    x1, y1, x2, y2 = line[0]
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    vl = VectorLine(points=[(float(x1), float(y1)), (float(x2), float(y2))])
                    if vl.length_px >= self.MIN_LINE_LENGTH_PX:
                        if 0 <= my < h_mask and 0 <= mx < w_mask and fold_mask[my, mx]:
                            fold_lines.append(vl)
                        else:
                            cut_lines.append(vl)

            # 切割线(实线, 黑色)
            for vl in cut_lines:
                p1 = vl.points[0]
                p2 = vl.points[-1]
                svg_lines.append(
                    f'  <line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" '
                    f'x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                    f'stroke="black" stroke-width="0.5"/>'
                )

            # 折叠线(虚线, 红色)
            for vl in fold_lines:
                p1 = vl.points[0]
                p2 = vl.points[-1]
                svg_lines.append(
                    f'  <line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" '
                    f'x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                    f'stroke="red" stroke-width="0.5" stroke-dasharray="5,3"/>'
                )

            svg_lines.append('</svg>')

            output_path = self._output_path(input_path, "cad", ".svg")
            with open(output_path, 'w') as f:
                f.write('\n'.join(svg_lines))

            return ProcessingResult(
                PipelineStage.CAD, True, output_path,
                metadata={
                    "format": "SVG",
                    "cut_lines": len(cut_lines),
                    "fold_lines": len(fold_lines),
                    "width_px": w,
                    "height_px": h,
                }
            )
        except Exception as e:
            return ProcessingResult(PipelineStage.CAD, False, error=str(e))

    def classify_lines(self, binary_path: str) -> Tuple['np.ndarray', 'np.ndarray']:
        """
        线条分类: 切割线 vs 折叠线
        
        基于形态学侵蚀: 粗线条(≥2px)=切割线, 细线条(1px)=折叠线
        返回: (cut_mask, fold_mask) 布尔数组
        """
        import cv2, numpy as np
        
        img = cv2.imread(binary_path, cv2.IMREAD_GRAYSCALE)
        inverted = cv2.bitwise_not(img)  # lines=white
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        eroded = cv2.erode(inverted, kernel, iterations=1)
        
        cut_mask = eroded > 0
        fold_mask = (inverted > 0) & (~cut_mask)
        
        return cut_mask, fold_mask

    def generate_dxf(self, input_path: str,
                     pixel_to_mm: float = 0.25) -> ProcessingResult:
        """
        阶段5: 生成DXF CAD文件
        
        使用ezdxf库生成AutoCAD兼容的DXF文件。
        图层: CUT(切割线), FOLD(折叠线), OUTLINE(轮廓)
        像素坐标转换为毫米(默认0.25mm/px, 约100DPI)
        """
        try:
            import cv2
            import numpy as np
            import ezdxf
            
            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return ProcessingResult(PipelineStage.CAD, False,
                                       error=f"Cannot read: {input_path}")

            h, w = img.shape[:2]

            # Canny + Hough
            edges = cv2.Canny(img, self.CANNY_LOW, self.CANNY_HIGH)
            lines_p = cv2.HoughLinesP(
                edges, rho=1, theta=np.pi/180,
                threshold=50, minLineLength=self.MIN_LINE_LENGTH_PX, maxLineGap=10
            )

            # 轮廓
            contours, _ = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # 创建DXF
            doc = ezdxf.new(dxfversion='R2010')
            msp = doc.modelspace()

            # 设置图层
            for layer_name, color in [('CUT', 7), ('FOLD', 1), ('OUTLINE', 3)]:
                doc.layers.add(layer_name, color=color)

            # 线条分类
            cut_mask, fold_mask = self.classify_lines(input_path)

            # 绘制直线 — 根据中点位置分类到CUT或FOLD层
            cut_count = 0
            fold_count = 0
            if lines_p is not None:
                for line in lines_p:
                    x1, y1, x2, y2 = line[0]
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    # 检查线段中点在哪个mask上
                    if 0 <= my < h and 0 <= mx < w:
                        layer = 'CUT' if cut_mask[my, mx] else 'FOLD'
                    else:
                        layer = 'CUT'
                    # 像素转毫米 + Y轴翻转
                    msp.add_line(
                        (x1 * pixel_to_mm, (h - y1) * pixel_to_mm),
                        (x2 * pixel_to_mm, (h - y2) * pixel_to_mm),
                        dxfattribs={'layer': layer, 'lineweight': 18 if layer == 'FOLD' else 25}
                    )
                    if layer == 'CUT':
                        cut_count += 1
                    else:
                        fold_count += 1

            # 绘制轮廓到OUTLINE层(仅大型封闭轮廓)
            contour_count = 0
            min_contour_area = 500  # 过滤小噪点
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_contour_area:
                    continue
                points = []
                for pt in contour:
                    px, py = pt[0]
                    points.append((px * pixel_to_mm, (h - py) * pixel_to_mm))
                if len(points) >= 3:
                    msp.add_lwpolyline(points, dxfattribs={'layer': 'OUTLINE'})
                    contour_count += 1

            output_path = self._output_path(input_path, "cad", ".dxf")
            doc.saveas(output_path)

            return ProcessingResult(
                PipelineStage.CAD, True, output_path,
                metadata={
                    "format": "DXF",
                    "version": "R2010",
                    "layers": ["CUT", "FOLD", "OUTLINE"],
                    "cut_lines": cut_count,
                    "fold_lines": fold_count,
                    "outlines": contour_count,
                    "width_mm": round(w * pixel_to_mm, 1),
                    "height_mm": round(h * pixel_to_mm, 1),
                    "pixel_to_mm": pixel_to_mm,
                }
            )
        except ImportError:
            return ProcessingResult(PipelineStage.CAD, False,
                                   error="ezdxf not installed. pip install ezdxf")
        except Exception as e:
            return ProcessingResult(PipelineStage.CAD, False, error=str(e))

    def process_full(self, input_path: str) -> Dict:
        """执行完整管道"""
        results = {}
        
        # Stage 1: Preprocess
        r1 = self.preprocess(input_path)
        results["preprocess"] = r1
        if not r1.success:
            return {"error": f"Preprocess failed: {r1.error}", "results": results}

        # Stage 2: Binarize (from preprocessed)
        r2 = self.binarize(r1.output_path)
        results["binarize"] = r2
        if not r2.success:
            return {"error": f"Binarize failed: {r2.error}", "results": results}

        # Quality check
        quality = self.quality_check(r2.output_path)
        results["quality"] = quality

        # Stage 3: Extract contours (from binary)
        r3 = self.extract_contours(r2.output_path)
        results["contours"] = r3
        if not r3.success:
            return {"error": f"Contour extraction failed: {r3.error}", "results": results}

        # Stage 4: Generate SVG (from binary)
        r4 = self.generate_svg(r2.output_path)
        results["svg"] = r4

        # Stage 5: Generate DXF (from binary)
        r5 = self.generate_dxf(r2.output_path)
        results["dxf"] = r5

        self.results.extend([r1, r2, r3, r4, r5])

        return {
            "success": all(r.success for r in [r1, r2, r3, r4]),
            "results": results,
            "output_files": {
                "preprocessed": r1.output_path if r1.success else None,
                "binary": r2.output_path if r2.success else None,
                "contours": r3.output_path if r3.success else None,
                "svg": r4.output_path if r4.success else None,
                "dxf": r5.output_path if r5.success else None,
            }
        }

    def batch_process(self, input_dir: str, pattern: str = "*.jpg") -> List[Dict]:
        """批量处理"""
        results = []
        input_path = Path(input_dir)
        for f in sorted(input_path.glob(pattern)):
            if f.suffix.lower() in self.INPUT_EXTS:
                print(f"Processing: {f.name}")
                result = self.process_full(str(f))
                result["input"] = f.name
                results.append(result)
        return results

    def _output_path(self, input_path: str, stage: str, ext: str = ".png") -> str:
        """生成输出路径"""
        stem = Path(input_path).stem
        return os.path.join(self.output_dir, f"{stem}_{stage}{ext}")


# === 测试 ===
if __name__ == "__main__":
    pipeline = DiePreVisionPipeline()
    
    print("=" * 60)
    print("  DiePre 视觉处理管道")
    print("=" * 60)
    
    # 状态检查
    print(f"\n依赖检查: {pipeline.status}")
    
    if not pipeline._cv2_available:
        print("\n❌ OpenCV未安装, 无法运行视觉管道")
        print("安装: pip install opencv-python numpy Pillow")
        exit(1)
    
    # 单张测试
    sample = "/Users/administruter/Desktop/2ac029a2eefc8a31313269317fe870a8.jpg"
    if os.path.exists(sample):
        print(f"\n--- 处理样本: {os.path.basename(sample)} ---")
        result = pipeline.process_full(sample)
        
        if result.get("success"):
            print("✅ 管道执行成功")
            for stage, r in result["results"].items():
                if r.success:
                    print(f"  {stage}: {r.output_path}")
                    for k, v in r.metadata.items():
                        print(f"    {k}: {v}")
        else:
            print(f"❌ 管道失败: {result.get('error')}")
    else:
        print(f"\n⚠️ 样本文件不存在: {sample}")
    
    # 批量处理所有样本
    desktop = "/Users/administruter/Desktop"
    samples = [f for f in os.listdir(desktop) 
               if f.endswith('.jpg') and len(f) == 40]  # 40字符hash名
    if len(samples) > 1:
        print(f"\n--- 批量处理: {len(samples)}个样本 ---")
        batch_results = pipeline.batch_process(desktop)
        success = sum(1 for r in batch_results if r.get("success"))
        print(f"结果: {success}/{len(batch_results)} 成功")
