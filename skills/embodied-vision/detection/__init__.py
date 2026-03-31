"""
embodied-vision/detection — 2D目标检测与分割

不依赖深度学习框架，基于传统CV方法:
- 显著性检测 (物体突出度)
- 轮廓层次分割 (物体级别分割)
- 特征匹配 (模板/特征点匹配)
- 简单物体分类 (形状+纹理+颜色)
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from primitives import (
    EdgeDetector, CornerDetector, ContourAnalyzer, 
    TextureAnalyzer, ColorSegmenter, VisualPrimitives,
    ContourInfo, TextureFeatures, ColorRegion
)


@dataclass
class DetectedObject:
    """检测到的物体"""
    id: int
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    mask: np.ndarray
    contour: Optional[ContourInfo] = None
    texture: Optional[TextureFeatures] = None
    color: Optional[ColorRegion] = None
    score: float = 0.0  # 检测置信度
    category: str = "unknown"
    sub_objects: List = field(default_factory=list)  # 层次关系


@dataclass
class MatchResult:
    """特征匹配结果"""
    matches: int
    inliers: int
    homography: Optional[np.ndarray]
    score: float
    src_points: List
    dst_points: List


# ═══════════════════════════════════════════
# 1. 显著性检测
# ═══════════════════════════════════════════

class SaliencyDetector:
    """基于频率调谐的显著性检测"""
    
    def __init__(self):
        self.primitives = VisualPrimitives()
    
    def detect(self, bgr: np.ndarray) -> np.ndarray:
        """
        频率调谐显著性 (Achanta et al., 2009)
        返回: 显著性图 (0-255)
        """
        h, w = bgr.shape[:2]
        
        # 在Lab颜色空间计算
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
        
        # 高斯模糊作为"背景"特征
        blur_size = max(3, min(h, w) // 4) | 1  # 确保奇数
        blurred = cv2.GaussianBlur(lab, (blur_size, blur_size), 0)
        
        # 显著性 = 与模糊版本的差异
        saliency = np.zeros((h, w), dtype=np.float32)
        for c in range(3):
            diff = lab[:, :, c].astype(np.float32) - blurred[:, :, c].astype(np.float32)
            saliency += diff ** 2
        
        saliency = np.sqrt(saliency)
        # 归一化到0-255
        saliency = (saliency / saliency.max() * 255).astype(np.uint8)
        
        return saliency
    
    def get_salient_regions(self, bgr: np.ndarray, 
                            threshold_ratio: float = 0.7) -> List[DetectedObject]:
        """从显著性图提取显著区域"""
        sal = self.detect(bgr)
        
        # 二值化
        thresh = int(sal.max() * threshold_ratio)
        _, binary = cv2.threshold(sal, thresh, 255, cv2.THRESH_BINARY)
        
        # 形态学清理
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k, iterations=2)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, iterations=1)
        
        # 提取连通域
        n, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        
        objects = []
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < 500:
                continue
            
            x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], \
                         stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            
            mask = (labels == i).astype(np.uint8) * 255
            score = float(np.mean(sal[labels == i]))
            
            objects.append(DetectedObject(
                id=i, bbox=(x, y, w, h), mask=mask, score=score
            ))
        
        return sorted(objects, key=lambda o: -o.score)


# ═══════════════════════════════════════════
# 2. 层次分割
# ═══════════════════════════════════════════

class HierarchicalSegmenter:
    """基于轮廓层次的物体分割"""
    
    def __init__(self):
        self.edge = EdgeDetector()
        self.contour = ContourAnalyzer()
        self.texture = TextureAnalyzer()
        self.color = ColorSegmenter()
    
    def segment(self, bgr: np.ndarray,
                min_area_ratio: float = 0.01,
                max_objects: int = 20) -> List[DetectedObject]:
        """
        层次分割: 外轮廓=物体, 内轮廓=子物体/孔洞
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape) == 3 else bgr
        
        h, w = gray.shape
        min_area = h * w * min_area_ratio
        
        # 边缘检测
        edge = self.edge.detect_single(gray)
        
        # 形态学闭运算连接断裂边缘
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, k, iterations=2)
        
        # 层次轮廓
        contours_info = self.contour.analyze(closed, min_area=int(min_area))
        
        # 构建物体层次
        objects = []
        for i, ci in enumerate(contours_info[:max_objects]):
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [ci.points], -1, 255, -1)  # 填充
            
            # 如果是内轮廓，从父mask中减去
            if ci.hierarchy_level > 0:
                # 找到父轮廓
                parent = None
                for pj, cj in enumerate(contours_info):
                    if cj.hierarchy_level == ci.hierarchy_level - 1:
                        parent = cj
                        break
                if parent:
                    parent_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(parent_mask, [parent.points], -1, 255, -1)
                    # 这个物体是parent减去自己=孔洞
                    continue  # 跳过孔洞
            
            # 纹理分析
            texture = self.texture.analyze(gray, ci.bbox)
            
            # 颜色分析
            if len(bgr.shape) == 3:
                roi = bgr[ci.bbox[1]:ci.bbox[1]+ci.bbox[3], 
                          ci.bbox[0]:ci.bbox[0]+ci.bbox[2]]
                color_regions = self.color.segment(roi, method="hsv_range")
                dominant_color = color_regions[0] if color_regions else None
            else:
                dominant_color = None
            
            # 简单分类
            category = self._simple_classify(ci, texture)
            
            obj = DetectedObject(
                id=i, bbox=ci.bbox, mask=mask,
                contour=ci, texture=texture,
                color=dominant_color, score=ci.area,
                category=category
            )
            objects.append(obj)
        
        return sorted(objects, key=lambda o: -o.score)
    
    def _simple_classify(self, ci: ContourInfo, tex: TextureFeatures) -> str:
        """基于形状+纹理的简单分类"""
        if ci.shape_type == "circle" and ci.circularity > 0.8:
            return "circle_object"
        elif ci.shape_type == "rect" and 0.8 < ci.aspect_ratio < 1.2:
            return "square_object"
        elif ci.shape_type == "rect":
            return "rect_object"
        elif ci.solidity > 0.8 and tex.entropy < 5.0:
            return "uniform_object"
        else:
            return "complex_object"


# ═══════════════════════════════════════════
# 3. 特征匹配
# ═══════════════════════════════════════════

class FeatureMatcher:
    """基于ORB特征点的模板匹配"""
    
    def __init__(self):
        self.detector = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    def match(self, image: np.ndarray, template: np.ndarray,
              min_matches: int = 10) -> Optional[MatchResult]:
        """匹配图像中的模板"""
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray_tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        
        kp1, des1 = self.detector.detectAndCompute(gray_img, None)
        kp2, des2 = self.detector.detectAndCompute(gray_tpl, None)
        
        if des1 is None or des2 is None:
            return None
        
        matches = self.matcher.match(des1, des2)
        matches = sorted(matches, key=lambda m: m.distance)
        
        if len(matches) < min_matches:
            return None
        
        # RANSAC + 单应性
        good = matches[:min(len(matches), 50)]
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        inliers = int(mask.sum()) if mask is not None else len(good)
        
        return MatchResult(
            matches=len(matches),
            inliers=inliers,
            homography=H,
            score=inliers / max(len(good), 1),
            src_points=[kp1[m.queryIdx].pt for m in good],
            dst_points=[kp2[m.trainIdx].pt for m in good]
        )
    
    def locate_in_image(self, image: np.ndarray, template: np.ndarray,
                        min_score: float = 0.3) -> Optional[Tuple[int, int, int, int]]:
        """在图像中定位模板, 返回bbox"""
        result = self.match(image, template)
        if result is None or result.score < min_score:
            return None
        
        if result.homography is not None:
            h, w = template.shape[:2]
            corners = np.float32([[0,0],[w,0],[w,h],[0,h]]).reshape(-1,1,2)
            warped = cv2.perspectiveTransform(corners, result.homography)
            x_coords = warped[:, 0, 0]
            y_coords = warped[:, 0, 1]
            x, y = int(x_coords.min()), int(y_coords.min())
            w_box = int(x_coords.max() - x)
            h_box = int(y_coords.max() - y)
            return (x, y, w_box, h_box)
        
        return None


# ═══════════════════════════════════════════
# 4. 物体分类器 (形状+纹理+颜色)
# ═══════════════════════════════════════════

class SimpleClassifier:
    """不依赖深度学习的简单物体分类"""
    
    CATEGORIES = {
        "packaging_box": {
            "shape": ["rect"], "circularity": (0.0, 0.3),
            "aspect_ratio": (0.3, 3.0), "solidity": (0.5, 1.0),
            "texture_entropy": (3.0, 8.0)
        },
        "cylinder": {
            "shape": ["circle"], "circularity": (0.6, 1.0),
            "aspect_ratio": (0.5, 2.0), "solidity": (0.7, 1.0),
            "texture_entropy": (2.0, 7.0)
        },
        "flat_panel": {
            "shape": ["rect"], "circularity": (0.0, 0.2),
            "aspect_ratio": (1.5, 10.0), "solidity": (0.8, 1.0),
            "texture_entropy": (2.0, 6.0)
        },
        "irregular": {
            "shape": ["irregular", "polygon"],
            "circularity": (0.0, 0.5), "aspect_ratio": (0.0, 10.0),
            "solidity": (0.3, 1.0), "texture_entropy": (0.0, 10.0)
        }
    }
    
    def classify(self, obj: DetectedObject) -> Tuple[str, float]:
        """分类单个物体, 返回(类别, 置信度)"""
        if obj.contour is None or obj.texture is None:
            return "unknown", 0.0
        
        ci = obj.contour
        tex = obj.texture
        
        best_cat = "unknown"
        best_score = 0.0
        
        for cat, spec in self.CATEGORIES.items():
            score = 0.0
            total = 0
            
            # 形状匹配
            if ci.shape_type in spec["shape"]:
                score += 1.0
            total += 1
            
            # 圆度范围
            lo, hi = spec["circularity"]
            if lo <= ci.circularity <= hi:
                score += 1.0
            total += 1
            
            # 长宽比
            lo, hi = spec["aspect_ratio"]
            if lo <= ci.aspect_ratio <= hi:
                score += 1.0
            total += 1
            
            # 实心度
            lo, hi = spec["solidity"]
            if lo <= ci.solidity <= hi:
                score += 1.0
            total += 1
            
            # 纹理熵
            lo, hi = spec["texture_entropy"]
            if lo <= tex.entropy <= hi:
                score += 1.0
            total += 1
            
            normalized = score / total
            if normalized > best_score:
                best_score = normalized
                best_cat = cat
        
        return best_cat, best_score


# ═══════════════════════════════════════════
# 统一检测接口
# ═══════════════════════════════════════════

class ObjectDetector:
    """统一2D目标检测"""
    
    def __init__(self):
        self.saliency = SaliencyDetector()
        self.segmenter = HierarchicalSegmenter()
        self.matcher = FeatureMatcher()
        self.classifier = SimpleClassifier()
    
    def detect(self, image: np.ndarray,
               method: str = "hierarchical") -> List[DetectedObject]:
        """检测图像中的物体"""
        if method == "saliency":
            return self.saliency.get_salient_regions(image)
        elif method == "hierarchical":
            objects = self.segmenter.segment(image)
            # 分类
            for obj in objects:
                obj.category, obj.score = self.classifier.classify(obj)
            return objects
        else:
            return self.segmenter.segment(image)
    
    def detect_and_classify(self, image: np.ndarray) -> List[DetectedObject]:
        """检测并分类所有物体"""
        objects = self.segmenter.segment(image)
        for obj in objects:
            obj.category, obj.score = self.classifier.classify(obj)
        return objects
    
    def find_template(self, image: np.ndarray, template: np.ndarray,
                      min_score: float = 0.3) -> Optional[Tuple[int, int, int, int]]:
        """在图像中查找模板"""
        return self.matcher.locate_in_image(image, template, min_score)


if __name__ == "__main__":
    import sys
    import time
    
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
    img = cv2.imread(path)
    if img is None:
        print(f"无法读取: {path}"); sys.exit(1)
    
    print(f"目标检测: {path}")
    
    det = ObjectDetector()
    
    # 层次分割
    t0 = time.time()
    objects = det.detect_and_classify(img)
    print(f"检测到 {len(objects)} 个物体 ({time.time()-t0:.2f}s)")
    
    for obj in objects[:10]:
        print(f"  #{obj.id}: {obj.category} (置信度={obj.score:.2f}) "
              f"bbox={obj.bbox} 面积={obj.score}")
        if obj.contour:
            print(f"    形状={obj.contour.shape_type} 圆度={obj.contour.circularity:.2f}")
        if obj.texture:
            print(f"    纹理: std={obj.texture.std:.1f} entropy={obj.texture.entropy:.2f}")
