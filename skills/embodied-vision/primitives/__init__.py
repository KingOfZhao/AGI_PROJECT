"""
embodied-vision/primitives — 视觉感知原语

从零构建具身智能视觉系统的最底层:
- 边缘检测 (多尺度Canny)
- 角点检测 (Harris/FAST/ORB)
- 轮廓分析 (层次轮廓+形状描述)
- 纹理分析 (LBP/GLCM/灰度统计)
- 颜色分割 (HSV空间+K-means)
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from pathlib import Path


# ═══════════════════════════════════════════
# 通用数据结构
# ═══════════════════════════════════════════

@dataclass
class KeyPoint:
    x: float; y: float
    response: float
    size: float = 0.0
    angle: float = 0.0
    octave: int = 0
    class_id: int = -1
    descriptor: Optional[np.ndarray] = None


@dataclass
class ContourInfo:
    points: np.ndarray
    area: float
    perimeter: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    centroid: Tuple[float, float]
    shape_type: str = "unknown"  # circle/rect/triangle/polygon/irregular
    circularity: float = 0.0
    aspect_ratio: float = 0.0
    solidity: float = 0.0
    hierarchy_level: int = 0


@dataclass
class TextureFeatures:
    mean: float
    std: float
    smoothness: float
    third_moment: float
    uniformity: float
    entropy: float
    lbp_hist: np.ndarray
    dominant_direction: float  # 0-180度


@dataclass
class ColorRegion:
    mask: np.ndarray
    bbox: Tuple[int, int, int, int]
    centroid: Tuple[float, float]
    area: int
    dominant_color: Tuple[int, int, int]  # HSV
    label: int


# ═══════════════════════════════════════════
# 1. 边缘检测
# ═══════════════════════════════════════════

class EdgeDetector:
    """多尺度边缘检测"""
    
    def __init__(self):
        self.scales = [1.0, 1.5, 2.0]
    
    def detect(self, gray: np.ndarray, 
               method: str = "canny",
               low_ratio: float = 0.3,
               high_ratio: float = 0.7) -> List[np.ndarray]:
        """
        多尺度边缘检测
        返回: 每个尺度的边缘图列表
        """
        edges = []
        
        if method == "canny":
            # 自动阈值基于中值
            v = np.median(gray)
            low = max(0, (1.0 - low_ratio) * v)
            high = min(255, (1.0 + high_ratio) * v)
            
            for scale in self.scales:
                if scale != 1.0:
                    h, w = gray.shape
                    scaled = cv2.resize(gray, (int(w / scale), int(h / scale)))
                    e = cv2.Canny(scaled, low / scale, high / scale)
                    e = cv2.resize(e, (w, h))
                else:
                    e = cv2.Canny(gray, low, high)
                edges.append(e)
            
            # 融合多尺度
            fused = np.zeros_like(gray)
            for e in edges:
                fused = cv2.bitwise_or(fused, e)
            edges.append(fused)
        
        elif method == "laplacian":
            for ksize in [3, 5, 7]:
                lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
                abs_lap = np.uint8(np.clip(np.abs(lap), 0, 255))
                edges.append(abs_lap)
        
        elif method == "sobel":
            for ksize in [3, 5]:
                sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
                sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
                mag = np.uint8(np.clip(np.sqrt(sx**2 + sy**2), 0, 255))
                edges.append(mag)
                # 方向
                direction = np.arctan2(sy, sx) * 180 / np.pi
                edges.append(direction)
        
        return edges
    
    def detect_single(self, gray: np.ndarray) -> np.ndarray:
        """最快单尺度Canny"""
        v = np.median(gray)
        return cv2.Canny(gray, max(0, 0.7 * v), min(255, 1.3 * v))


# ═══════════════════════════════════════════
# 2. 角点检测
# ═══════════════════════════════════════════

class CornerDetector:
    """多方法角点检测"""
    
    def detect(self, gray: np.ndarray, 
               method: str = "orb",
               max_points: int = 500) -> List[KeyPoint]:
        """
        检测角点并返回KeyPoint列表
        method: harris/fast/orb/shi_tomasi
        """
        if method == "harris":
            dst = cv2.cornerHarris(gray, 2, 3, 0.04)
            dst = cv2.dilate(dst, None)
            thresh = 0.01 * dst.max()
            pts = np.argwhere(dst > thresh)
            kps = []
            for y, x in pts:
                kps.append(KeyPoint(x=float(x), y=float(y), 
                                     response=float(dst[y, x])))
            return sorted(kps, key=lambda k: -k.response)[:max_points]
        
        elif method == "shi_tomasi":
            corners = cv2.goodFeaturesToTrack(gray, max_points, 0.01, 10)
            if corners is None:
                return []
            return [KeyPoint(x=float(c[0][0]), y=float(c[0][1]), response=0.0)
                    for c in corners]
        
        elif method == "fast":
            fast = cv2.FastFeatureDetector_create()
            kp = fast.detect(gray)
            return [KeyPoint(x=p.pt[0], y=p.pt[1], response=p.response,
                            size=p.size, angle=p.angle) for p in kp[:max_points]]
        
        elif method == "orb":
            orb = cv2.ORB_create(nfeatures=max_points)
            kp, des = orb.detectAndCompute(gray, None)
            result = []
            for i, p in enumerate(kp):
                k = KeyPoint(x=p.pt[0], y=p.pt[1], response=p.response,
                            size=p.size, angle=p.angle, class_id=p.class_id)
                if des is not None:
                    k.descriptor = des[i]
                result.append(k)
            return result
        
        return []


# ═══════════════════════════════════════════
# 3. 轮廓分析
# ═══════════════════════════════════════════

class ContourAnalyzer:
    """层次轮廓分析"""
    
    def analyze(self, binary: np.ndarray,
                min_area: int = 100,
                max_depth: int = 3) -> List[ContourInfo]:
        """提取并分析层次轮廓"""
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        if hierarchy is None:
            return results
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            
            peri = cv2.arcLength(cnt, True)
            M = cv2.moments(cnt)
            
            if M["m00"] == 0:
                continue
            
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            x, y, w, h = cv2.boundingRect(cnt)
            
            # 形状特征
            circularity = 4 * np.pi * area / (peri ** 2) if peri > 0 else 0
            aspect_ratio = w / max(h, 1)
            
            # 凸性
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            # 形状分类
            shape = self._classify_shape(cnt, circularity, aspect_ratio, w, h)
            
            # 层次深度
            depth = 0
            idx = i
            while hierarchy[0][idx][3] != -1 and depth < max_depth:
                idx = hierarchy[0][idx][3]
                depth += 1
            
            results.append(ContourInfo(
                points=cnt, area=area, perimeter=peri,
                bbox=(x, y, w, h), centroid=(cx, cy),
                shape_type=shape, circularity=circularity,
                aspect_ratio=aspect_ratio, solidity=solidity,
                hierarchy_level=depth
            ))
        
        return sorted(results, key=lambda c: -c.area)
    
    def _classify_shape(self, cnt, circularity, ar, w, h) -> str:
        eps = 0.04 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps, True)
        n = len(approx)
        
        if circularity > 0.85:
            return "circle"
        elif n == 3:
            return "triangle"
        elif n == 4:
            return "rect" if 0.8 < ar < 1.2 else "rect"
        elif n == 5:
            return "pentagon"
        elif n <= 8:
            return "polygon"
        else:
            return "irregular"
    
    def find_rectangles(self, gray: np.ndarray, 
                        min_area: int = 500) -> List[ContourInfo]:
        """专门检测矩形(适合包装盒)"""
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        rects = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            
            if len(approx) == 4:
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    x, y, w, h = cv2.boundingRect(cnt)
                    rects.append(ContourInfo(
                        points=approx, area=area, perimeter=peri,
                        bbox=(x, y, w, h),
                        centroid=(M["m10"]/M["m00"], M["m01"]/M["m00"]),
                        shape_type="rect", circularity=4*np.pi*area/(peri**2),
                        aspect_ratio=w/max(h,1), solidity=1.0
                    ))
        
        return sorted(rects, key=lambda c: -c.area)


# ═══════════════════════════════════════════
# 4. 纹理分析
# ═══════════════════════════════════════════

class TextureAnalyzer:
    """纹理特征提取"""
    
    def analyze(self, gray: np.ndarray, 
                roi: Optional[Tuple[int, int, int, int]] = None) -> TextureFeatures:
        """提取纹理特征"""
        if roi:
            x, y, w, h = roi
            region = gray[y:y+h, x:x+w]
        else:
            region = gray
        
        # 基础统计
        mean = float(np.mean(region))
        std = float(np.std(region))
        
        # 归一化灰度直方图
        hist = cv2.calcHist([region], [0], None, [256], [0, 256]).flatten()
        hist = hist / hist.sum()
        
        # Haralick纹理特征 (简化版)
        smoothness = 1 - 1 / (1 + std ** 2)
        third_moment = float(np.mean((region - mean) ** 3))
        uniformity = float(np.sum(hist ** 2))
        entropy = -float(np.sum(hist * np.log2(hist + 1e-10)))
        
        # LBP (Local Binary Pattern)
        lbp = self._lbp(region)
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=59, range=(0, 59))
        lbp_hist = lbp_hist.astype(float) / lbp_hist.sum()
        
        # 主方向 (通过梯度直方图)
        gx = cv2.Sobel(region, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(region, cv2.CV_64F, 0, 1, ksize=3)
        angles = np.arctan2(gy, gx) * 180 / np.pi % 180
        hist_ang, bins = np.histogram(angles.ravel(), bins=36, range=(0, 180))
        dominant_direction = bins[np.argmax(hist_ang)]
        
        return TextureFeatures(
            mean=mean, std=std, smoothness=smoothness,
            third_moment=third_moment, uniformity=uniformity,
            entropy=entropy, lbp_hist=lbp_hist,
            dominant_direction=float(dominant_direction)
        )
    
    def _lbp(self, gray: np.ndarray, radius: int = 1) -> np.ndarray:
        """Local Binary Pattern"""
        h, w = gray.shape
        lbp = np.zeros((h, w), dtype=np.uint8)
        
        # 8邻域
        offsets = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
        for i, (dy, dx) in enumerate(offsets):
            shifted = np.zeros_like(gray)
            y_slice_src = slice(max(0, dy), min(h, h+dy))
            x_slice_src = slice(max(0, dx), min(w, w+dx))
            y_slice_dst = slice(max(0, -dy), min(h, h-dy))
            x_slice_dst = slice(max(0, -dx), min(w, w-dx))
            shifted[y_slice_dst, x_slice_dst] = gray[y_slice_src, x_slice_src]
            lbp += ((shifted >= gray) << i).astype(np.uint8)
        
        return lbp
    
    def compute_homogeneity(self, gray: np.ndarray, 
                           block_size: int = 32) -> np.ndarray:
        """计算局部纹理均匀度图 (用于分割)"""
        h, w = gray.shape
        result = np.zeros((h, w), dtype=np.float32)
        
        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = gray[y:y+block_size, x:x+block_size]
                std = np.std(block)
                # 均匀区域std低, 纹理区域std高
                score = 1.0 / (1.0 + std)
                result[y:y+block_size, x:x+block_size] = score
        
        return result


# ═══════════════════════════════════════════
# 5. 颜色分割
# ═══════════════════════════════════════════

class ColorSegmenter:
    """HSV颜色空间分割"""
    
    # 预定义颜色范围 (HSV)
    COLOR_RANGES = {
        "red":      [(0, 100, 50), (10, 255, 255), (160, 100, 50), (180, 255, 255)],
        "orange":   [(10, 100, 50), (25, 255, 255)],
        "yellow":   [(25, 100, 50), (35, 255, 255)],
        "green":    [(35, 100, 50), (85, 255, 255)],
        "blue":     [(85, 100, 50), (135, 255, 255)],
        "purple":   [(135, 100, 50), (160, 255, 255)],
        "brown":    [(10, 50, 30), (25, 200, 150)],
        "white":    [(0, 0, 200), (180, 30, 255)],
        "gray":     [(0, 0, 50), (180, 30, 200)],
        "black":    [(0, 0, 0), (180, 255, 50)],
    }
    
    def segment(self, bgr: np.ndarray, 
                n_colors: int = 5,
                method: str = "kmeans") -> List[ColorRegion]:
        """
        颜色分割
        method: kmeans / hsv_range / both
        """
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        
        if method == "hsv_range":
            return self._hsv_range_segment(hsv)
        elif method == "kmeans":
            return self._kmeans_segment(bgr, n_colors)
        else:
            return self._hsv_range_segment(hsv)
    
    def _hsv_range_segment(self, hsv: np.ndarray) -> List[ColorRegion]:
        regions = []
        for color_name, ranges in self.COLOR_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            # 处理red的两组范围
            for i in range(0, len(ranges), 2):
                low, high = ranges[i], ranges[i+1]
                m = cv2.inRange(hsv, np.array(low), np.array(high))
                mask = cv2.bitwise_or(mask, m)
            
            area = cv2.countNonZero(mask)
            if area < 100:
                continue
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(cnt)
                M = cv2.moments(cnt)
                cx = M["m10"]/M["m00"] if M["m00"] > 0 else x + w/2
                cy = M["m01"]/M["m00"] if M["m00"] > 0 else y + h/2
                
                # 计算该区域的平均HSV
                mean_hsv = cv2.mean(hsv, mask=mask)[:3]
                
                regions.append(ColorRegion(
                    mask=mask, bbox=(x, y, w, h),
                    centroid=(cx, cy), area=area,
                    dominant_color=tuple(int(v) for v in mean_hsv),
                    label=list(self.COLOR_RANGES.keys()).index(color_name)
                ))
        
        return sorted(regions, key=lambda r: -r.area)
    
    def _kmeans_segment(self, bgr: np.ndarray, k: int) -> List[ColorRegion]:
        """K-means颜色聚类"""
        pixels = bgr.reshape(-1, 3).astype(np.float32)
        
        # subsample加速
        if len(pixels) > 10000:
            idx = np.random.choice(len(pixels), 10000, replace=False)
            pixels_sub = pixels[idx]
        else:
            pixels_sub = pixels
        
        _, labels, centers = cv2.kmeans(
            pixels_sub, k, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
            3, cv2.KMEANS_PP_CENTERS
        )
        
        regions = []
        for i in range(k):
            mask_full = np.zeros(bgr.shape[:2], dtype=np.uint8)
            full_labels = np.zeros(len(pixels), dtype=np.int32)
            if len(pixels) > 10000:
                # 对所有像素分配最近cluster
                dists = np.linalg.norm(pixels - centers[i], axis=1)
                full_labels = (dists == np.min(dists.reshape(-1, k), axis=1)).astype(np.uint8) * (i + 1)
            else:
                full_labels = (labels.flatten() == i).astype(np.uint8) * (i + 1)
            
            mask_full = full_labels.reshape(bgr.shape[:2]).astype(np.uint8) * 255
            area = cv2.countNonZero(mask_full)
            
            if area < 100:
                continue
            
            contours, _ = cv2.findContours(mask_full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(cnt)
                M = cv2.moments(cnt)
                cx = M["m10"]/M["m00"] if M["m00"] > 0 else x + w/2
                cy = M["m01"]/M["m00"] if M["m00"] > 0 else y + h/2
                
                regions.append(ColorRegion(
                    mask=mask_full, bbox=(x, y, w, h),
                    centroid=(cx, cy), area=area,
                    dominant_color=tuple(int(v) for v in centers[i]),
                    label=i
                ))
        
        return sorted(regions, key=lambda r: -r.area)
    
    def detect_background(self, bgr: np.ndarray) -> np.ndarray:
        """检测并返回背景mask (取边缘区域颜色)"""
        h, w = bgr.shape[:2]
        border_size = min(h, w) // 10
        
        # 从四边采样颜色
        samples = np.vstack([
            bgr[:border_size, :].reshape(-1, 3),
            bgr[-border_size:, :].reshape(-1, 3),
            bgr[:, :border_size].reshape(-1, 3),
            bgr[:, -border_size:].reshape(-1, 3),
        ])
        
        # K=1找背景色
        _, _, center = cv2.kmeans(
            samples.astype(np.float32), 1, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
            3, cv2.KMEANS_PP_CENTERS
        )
        
        bg_color = center[0]
        # 在HSV空间中找相近颜色
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        bg_hsv = cv2.cvtColor(bg_color.reshape(1,1,3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0][0]
        
        lower = np.array([max(0, bg_hsv[0]-15), max(0, bg_hsv[1]-40), max(0, bg_hsv[2]-40)])
        upper = np.array([min(180, bg_hsv[0]+15), min(255, bg_hsv[1]+40), min(255, bg_hsv[2]+40)])
        
        mask = cv2.inRange(hsv, lower, upper)
        return mask


# ═══════════════════════════════════════════
# 统一感知接口
# ═══════════════════════════════════════════

class VisualPrimitives:
    """统一视觉原语接口"""
    
    def __init__(self):
        self.edge = EdgeDetector()
        self.corner = CornerDetector()
        self.contour = ContourAnalyzer()
        self.texture = TextureAnalyzer()
        self.color = ColorSegmenter()
    
    def perceive(self, image: np.ndarray) -> Dict:
        """
        完整感知: 对一张图像执行所有原语分析
        返回: 包含所有分析结果的字典
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. 边缘
        edges = self.edge.detect(gray)
        
        # 2. 角点
        corners = self.corner.detect(gray, method="orb")
        
        # 3. 轮廓
        binary = self.edge.detect_single(gray)
        contours = self.contour.analyze(binary)
        rectangles = self.contour.find_rectangles(gray)
        
        # 4. 纹理
        texture = self.texture.analyze(gray)
        
        # 5. 颜色
        if len(image.shape) == 3:
            color_regions = self.color.segment(image, method="hsv_range")
            bg_mask = self.color.detect_background(image)
        else:
            color_regions = []
            bg_mask = np.zeros_like(gray)
        
        return {
            "image_size": gray.shape,
            "edges": edges[-1] if edges else None,  # 融合边缘
            "corners": corners,
            "contours": contours,
            "rectangles": rectangles,
            "texture": texture,
            "color_regions": color_regions,
            "background_mask": bg_mask,
        }
    
    def perceive_fast(self, image: np.ndarray) -> Dict:
        """快速感知 (仅关键特征)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        edge = self.edge.detect_single(gray)
        corners = self.corner.detect(gray, method="fast", max_points=100)
        rects = self.contour.find_rectangles(gray)
        
        return {
            "edge_count": int(cv2.countNonZero(edge)),
            "corner_count": len(corners),
            "rectangles": len(rects),
            "largest_rect_area": rects[0].area if rects else 0,
        }


# ═══════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import time
    
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        # 默认用DiePre样本
        img_path = "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"无法读取: {img_path}")
        sys.exit(1)
    
    print(f"感知原语测试: {img_path}")
    print(f"图像尺寸: {img.shape}")
    
    vp = VisualPrimitives()
    
    # 快速感知
    t0 = time.time()
    fast = vp.perceive_fast(img)
    print(f"\n快速感知 ({time.time()-t0:.2f}s):")
    print(f"  边缘像素: {fast['edge_count']}")
    print(f"  角点数: {fast['corner_count']}")
    print(f"  矩形数: {fast['rectangles']}")
    print(f"  最大矩形面积: {fast['largest_rect_area']}")
    
    # 完整感知
    t0 = time.time()
    result = vp.perceive(img)
    print(f"\n完整感知 ({time.time()-t0:.2f}s):")
    print(f"  轮廓数: {len(result['contours'])}")
    print(f"  颜色区域: {len(result['color_regions'])}")
    print(f"  纹理: std={result['texture'].std:.1f}, entropy={result['texture'].entropy:.2f}")
    print(f"  纹理主方向: {result['texture'].dominant_direction:.0f}°")
    
    if result['contours']:
        top5 = result['contours'][:5]
        print(f"\n  TOP5轮廓:")
        for c in top5:
            print(f"    {c.shape_type}: 面积={c.area:.0f}, 圆度={c.circularity:.2f}, "
                  f"长宽比={c.aspect_ratio:.2f}, 实心度={c.solidity:.2f}")
    
    if result['color_regions']:
        print(f"\n  颜色区域:")
        for r in result['color_regions'][:5]:
            print(f"    面积={r.area}, HSV={r.dominant_color}")
    
    print(f"\n✅ 感知原语测试完成")
