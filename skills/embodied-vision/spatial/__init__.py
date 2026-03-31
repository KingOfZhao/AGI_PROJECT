"""
embodied-vision/spatial — 3D空间理解

从2D图像构建3D理解:
- 单目深度估计 (无深度传感器)
- 点云生成与处理
- 场景图 (物体空间关系)
- 可供性检测 (可抓取/可推/可开)
- 物理推理 (支撑/稳定性/遮挡)
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
from pathlib import Path
import math


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class Point3D:
    x: float; y: float; z: float
    r: int = 128; g: int = 128; b: int = 128
    
    def to_array(self):
        return np.array([self.x, self.y, self.z])
    
    def distance_to(self, other):
        return math.sqrt((self.x-other.x)**2 + (self.y-other.y)**2 + (self.z-other.z)**2)


@dataclass
class BBox3D:
    """3D轴对齐包围盒"""
    x_min: float; y_min: float; z_min: float
    x_max: float; y_max: float; z_max: float
    
    @property
    def center(self) -> Tuple[float, float, float]:
        return ((self.x_min+self.x_max)/2, (self.y_min+self.y_max)/2, (self.z_min+self.z_max)/2)
    
    @property
    def size(self) -> Tuple[float, float, float]:
        return (self.x_max-self.x_min, self.y_max-self.y_min, self.z_max-self.z_min)
    
    def volume(self) -> float:
        w, h, d = self.size
        return w * h * d
    
    def iou(self, other) -> float:
        ix = max(0, min(self.x_max, other.x_max) - max(self.x_min, other.x_min))
        iy = max(0, min(self.y_max, other.y_max) - max(self.y_min, other.y_min))
        iz = max(0, min(self.z_max, other.z_max) - max(self.z_min, other.z_min))
        inter = ix * iy * iz
        union = self.volume() + other.volume() - inter
        return inter / max(union, 1e-10)


@dataclass
class SceneObject:
    """场景中的物体"""
    id: int
    name: str
    bbox_2d: Tuple[int, int, int, int]  # image bbox
    bbox_3d: Optional[BBox3D] = None
    depth: float = 0.0  # 估计深度
    points: List[Point3D] = field(default_factory=list)
    affordances: List[str] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)


@dataclass
class SpatialRelation:
    """两个物体间的空间关系"""
    subject: int  # 物体ID
    object_id: int  # 物体ID
    relation: str  # on/in/beside/behind/in_front_of/above/below/inside/adjacent
    confidence: float = 0.0
    distance: float = 0.0


# ═══════════════════════════════════════════
# 1. 单目深度估计
# ═══════════════════════════════════════════

class MonocularDepthEstimator:
    """
    基于多线索的单目深度估计 (不需要深度传感器/深度学习)
    
    线索:
    - 尺寸透视 (远处物体小)
    - 纹理梯度 (远处纹理密)
    - 大气透视 (远处模糊/灰)
    - 遮挡关系 (被遮挡=更远)
    - 地面接触 (物体底部=地面)
    """
    
    def estimate(self, bgr: np.ndarray, 
                 camera_height_mm: float = 500.0,
                 fov_deg: float = 60.0) -> np.ndarray:
        """
        估计深度图
        返回: depth_map (float32, 单位: mm), 近=小值, 远=大值
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape) == 3 else bgr
        h, w = gray.shape
        
        # === 线索1: 纵向位置 (假设地面平面) ===
        # 图像底部=近, 顶部=远
        y_coords = np.arange(h, dtype=np.float32).reshape(-1, 1)
        depth_positional = (1.0 - y_coords / h)  # 0(近)→1(远)
        
        # === 线索2: 纹理梯度 (远处纹理密→高频) ===
        blur_far = cv2.GaussianBlur(gray, (31, 31), 0)
        blur_near = cv2.GaussianBlur(gray, (5, 5), 0)
        texture_detail = np.abs(gray.astype(float) - blur_near.astype(float)).astype(np.float32)
        blur_detail = cv2.GaussianBlur(texture_detail, (21, 21), 0)
        texture_depth = 1.0 - blur_detail / max(blur_detail.max(), 1)
        
        # === 线索3: 对比度/清晰度 (远处模糊) ===
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = np.abs(laplacian)
        sharpness = cv2.GaussianBlur(sharpness, (21, 21), 0)
        sharpness_depth = 1.0 - sharpness / max(sharpness.max(), 1)
        
        # === 线索4: 色彩饱和度 (远处灰/蓝) ===
        if len(bgr.shape) == 3:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            saturation = hsv[:, :, 1].astype(np.float32) / 255
            color_depth = 1.0 - saturation
        else:
            color_depth = np.full((h, w), 0.5, dtype=np.float32)
        
        # === 融合多线索 ===
        weights = {
            'position': 0.35,
            'texture': 0.25,
            'sharpness': 0.25,
            'color': 0.15,
        }
        
        depth = (weights['position'] * depth_positional +
                 weights['texture'] * texture_depth +
                 weights['sharpness'] * sharpness_depth +
                 weights['color'] * color_depth)
        
        # 平滑
        depth = cv2.GaussianBlur(depth, (31, 31), 0)
        
        # 转换为mm (使用简单针孔模型)
        # 假设地面在图像底部, 最近距离=camera_height * tan(fov/2 - angle)
        fov_rad = math.radians(fov_deg)
        focal_length_px = h / (2 * math.tan(fov_rad / 2))
        
        # 近似: depth_mm = camera_height * focal / (y_pixel * pixel_size)
        # 简化为: 近=200mm, 远=5000mm
        depth_mm = 200 + depth * 4800
        
        return depth_mm.astype(np.float32)
    
    def get_depth_at(self, depth_map: np.ndarray, 
                     x: int, y: int, 
                     radius: int = 5) -> float:
        """获取某点的平均深度"""
        h, w = depth_map.shape
        x1 = max(0, x - radius)
        x2 = min(w, x + radius)
        y1 = max(0, y - radius)
        y2 = min(h, y + radius)
        return float(np.mean(depth_map[y1:y2, x1:x2]))


# ═══════════════════════════════════════════
# 2. 点云生成
# ═══════════════════════════════════════════

class PointCloudGenerator:
    """从深度图生成3D点云"""
    
    def __init__(self, fx: float = 800.0, fy: float = 800.0,
                 cx: float = 0.0, cy: float = 0.0):
        """
        相机内参 (像素→3D)
        fx, fy: 焦距(px)
        cx, cy: 主点(通常为图像中心)
        """
        self.fx = fx
        self.fy = fy
        self.cx = cx  # 0表示自动取中心
        self.cy = cy
    
    def generate(self, depth_map: np.ndarray, 
                 bgr: Optional[np.ndarray] = None,
                 max_points: int = 100000,
                 depth_scale: float = 1.0) -> List[Point3D]:
        """
        从深度图生成点云
        depth_map: 深度图(mm)
        bgr: 颜色图(可选, 用于给点云着色)
        """
        h, w = depth_map.shape
        cx = self.cx if self.cx != 0 else w / 2
        cy = self.cy if self.cy != 0 else h / 2
        
        points = []
        # 降采样
        step = max(1, int(math.sqrt(h * w / max_points)))
        
        for y in range(0, h, step):
            for x in range(0, w, step):
                z = float(depth_map[y, x]) * depth_scale
                if z <= 0:
                    continue
                
                # 反投影: 像素→相机坐标
                x3d = (x - cx) * z / self.fx
                y3d = (y - cy) * z / self.fy
                
                r, g, b = 128, 128, 128
                if bgr is not None:
                    pixel = bgr[y, x]
                    r, g, b = int(pixel[2]), int(pixel[1]), int(pixel[0])
                
                points.append(Point3D(x3d, y3d, z, r, g, b))
        
        return points
    
    def to_array(self, points: List[Point3D]) -> np.ndarray:
        """转为Nx3 numpy数组"""
        return np.array([[p.x, p.y, p.z] for p in points])
    
    def estimate_normals(self, points: List[Point3D], 
                         k: int = 10) -> List[Tuple[float, float, float]]:
        """估计每个点的法向量"""
        if not points:
            return []
        
        arr = self.to_array(points)
        n = len(arr)
        normals = []
        
        for i in range(n):
            dists = np.linalg.norm(arr - arr[i], axis=1)
            neighbors = np.argsort(dists)[1:k+1]
            
            if len(neighbors) < 3:
                normals.append((0, 0, 1))
                continue
            
            # PCA估计法向量
            centered = arr[neighbors] - arr[i]
            cov = centered.T @ centered
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            normal = eigenvectors[:, 0]  # 最小特征值对应法向量
            normals.append(tuple(normal))
        
        return normals
    
    def get_plane(self, points: List[Point3D]) -> Optional[Tuple[float, float, float, float]]:
        """RANSAC平面拟合 (ax+by+cz+d=0)"""
        if len(points) < 10:
            return None
        
        arr = self.to_array(points)
        best_inliers = 0
        best_plane = None
        
        for _ in range(100):
            idx = np.random.choice(len(arr), 3, replace=False)
            p1, p2, p3 = arr[idx]
            
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm < 1e-10:
                continue
            normal = normal / norm
            d = -np.dot(normal, p1)
            
            # 计算内点
            distances = np.abs(arr @ normal + d)
            inliers = np.sum(distances < 5.0)  # 5mm阈值
            
            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = (float(normal[0]), float(normal[1]), float(normal[2]), float(d))
        
        return best_plane


# ═══════════════════════════════════════════
# 3. 场景图
# ═══════════════════════════════════════════

class SceneGraphBuilder:
    """构建场景关系图"""
    
    def __init__(self):
        self.relation_thresholds = {
            "on": 0.3,        # 重叠度高
            "in": 0.8,        # 包含
            "beside": 0.5,    # 水平相邻
            "above": 0.3,     # 垂直上方
            "below": 0.3,     # 垂直下方
            "behind": 0.2,    # z方向远
            "in_front_of": 0.2,  # z方向近
        }
    
    def build(self, objects: List[SceneObject]) -> List[SpatialRelation]:
        """构建物体间的空间关系"""
        relations = []
        
        for i, obj_i in enumerate(objects):
            for j, obj_j in enumerate(objects):
                if i >= j:
                    continue
                
                rel = self._compute_relation(obj_i, obj_j)
                if rel:
                    relations.append(rel)
        
        return relations
    
    def _compute_relation(self, a: SceneObject, b: SceneObject) -> Optional[SpatialRelation]:
        """计算两个物体间的空间关系"""
        ax, ay, aw, ah = a.bbox_2d
        bx, by, bw, bh = b.bbox_2d
        
        # 2D位置关系
        acx, acy = ax + aw/2, ay + ah/2
        bcx, bcy = bx + bw/2, by + bh/2
        
        dx = bcx - acx
        dy = bcy - acy
        distance = math.sqrt(dx**2 + dy**2)
        
        # 重叠度
        ix = max(0, min(ax+aw, bx+bw) - max(ax, bx))
        iy = max(0, min(ay+ah, by+bh) - max(ay, by))
        inter_area = ix * iy
        union_area = aw*ah + bw*bh - inter_area
        iou = inter_area / max(union_area, 1)
        
        # 深度关系
        if a.depth > 0 and b.depth > 0:
            depth_diff = a.depth - b.depth
        else:
            depth_diff = ay - by  # 用y位置近似
        
        # 判断关系
        relation = None
        confidence = 0.0
        
        if iou > 0.5:
            # 大量重叠: 包含关系
            if aw * ah > bw * bh:
                relation = "contains"
                confidence = iou
            else:
                relation = "in"
                confidence = iou
        elif iou > 0.1:
            # 部分重叠: on/above
            if ay + ah < by:  # a在b上方
                relation = "on"
                confidence = iou * 2
        else:
            # 不重叠
            if abs(dx) > abs(dy) * 2:
                relation = "beside"
                confidence = 1 - min(abs(dx) / max(aw, bw), 3) / 3
            elif abs(dy) > abs(dx) * 2:
                if dy < 0:
                    relation = "above"
                else:
                    relation = "below"
                confidence = 1 - min(abs(dy) / max(ah, bh), 3) / 3
            else:
                relation = "beside"
                confidence = 0.3
        
        if confidence < 0.15:
            return None
        
        return SpatialRelation(
            subject=a.id, object_id=b.id,
            relation=relation, confidence=confidence,
            distance=distance
        )
    
    def to_text(self, objects: List[SceneObject], 
                relations: List[SpatialRelation]) -> str:
        """生成场景的文字描述"""
        obj_map = {o.id: o for o in objects}
        lines = []
        
        for o in objects[:5]:
            lines.append(f"物体{o.id}({o.name}): 位置{o.bbox_2d} 深度{o.depth:.0f}mm")
        
        lines.append("\n空间关系:")
        for r in relations[:10]:
            sub = obj_map.get(r.subject, type('o', (), {'name': '?'}))
            obj = obj_map.get(r.object_id, type('o', (), {'name': '?'}))
            lines.append(f"  物体{r.subject}({sub.name}) {r.relation} 物体{r.object_id}({obj.name}) "
                        f"置信度={r.confidence:.2f}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════
# 4. 可供性检测
# ═══════════════════════════════════════════

class AffordanceDetector:
    """
    可供性检测: 判断物体可以被如何操作
    
    基于形状+物理属性的推理(非深度学习)
    """
    
    AFFORDANCE_RULES = {
        "graspable": {  # 可抓取
            "max_size": (300, 300),  # 最大可抓取尺寸(mm)
            "min_solidity": 0.5,
            "min_depth_range": 50,  # 需要一定的深度变化
        },
        "pushable": {  # 可推
            "max_height": 200,  # 低矮物体
            "min_solidity": 0.7,  # 需要平坦底面
            "shape": ["rect"],
        },
        "liftable": {  # 可抬起
            "max_weight_estimate": 5000,  # g (基于尺寸估计)
            "min_solidity": 0.6,
        },
        "openable": {  # 可打开
            "shape": ["rect"],  # 有面板
            "min_aspect_ratio": 0.3,
            "max_aspect_ratio": 3.0,
            "has_handle": True,  # 需要检测把手
        },
        "placeable_on": {  # 可放置在上面
            "is_flat_top": True,
            "min_area": 2000,  # mm²
        },
        "insertable": {  # 可插入
            "shape": ["rect"],
            "max_aspect_ratio": 5.0,
            "min_solidity": 0.9,
        },
    }
    
    def detect(self, objects: List[SceneObject],
               depth_map: Optional[np.ndarray] = None) -> Dict[int, List[str]]:
        """检测每个物体的可供性"""
        result = {}
        
        for obj in objects:
            affordances = []
            
            if obj.bbox_3d is None:
                # 从2D bbox粗略估计3D
                x, y, w, h = obj.bbox_2d
                est_depth = obj.depth if obj.depth > 0 else 500
                # 假设宽高为像素尺寸的一定比例(经验值)
                scale = est_depth / 800  # 像素→mm近似
                obj.bbox_3d = BBox3D(0, 0, est_depth - 50,
                                     w * scale, h * scale, est_depth + 50)
            
            size = obj.bbox_3d.size
            
            # 可抓取: 不太大的物体
            if size[0] < 300 and size[1] < 300:
                affordances.append("graspable")
            
            # 可推: 低矮且宽
            if size[1] < 200 and size[0] > 100:
                affordances.append("pushable")
            
            # 可抬起: 估计不太重
            vol = obj.bbox_3d.volume()
            if vol < 5000000:  # ~5L
                affordances.append("liftable")
            
            # 可放置在上面: 有平坦顶部
            if size[0] > 50 and size[2] > 50 and vol > 50000:
                affordances.append("placeable_on")
            
            obj.affordances = affordances
            result[obj.id] = affordances
        
        return result
    
    def get_grasp_points(self, obj: SceneObject,
                         depth_map: np.ndarray) -> List[Tuple[int, int, float]]:
        """
        计算抓取点
        返回: [(x, y, approach_angle), ...]
        """
        x, y, w, h = obj.bbox_2d
        cx, cy = x + w // 2, y + h // 2
        
        points = []
        
        # 中心抓取(默认)
        points.append((cx, cy, 0.0))  # 从上方抓取
        
        # 侧边抓取(如果物体窄高)
        if h > w * 1.5:
            points.append((x, cy, 90.0))   # 从左侧
            points.append((x + w, cy, -90.0))  # 从右侧
        
        # 如果物体宽矮
        if w > h * 1.5:
            points.append((cx, y, 180.0))  # 从上方前方
            points.append((cx, y + h, 0.0))  # 从上方后方
        
        return points


# ═══════════════════════════════════════════
# 5. 物理推理
# ═══════════════════════════════════════════

class PhysicsReasoner:
    """
    简单物理推理:
    - 支撑关系 (什么在什么上面)
    - 稳定性 (是否会倒)
    - 遮挡 (什么挡住了什么)
    - 跌落风险
    """
    
    def analyze_support(self, objects: List[SceneObject],
                        relations: List[SpatialRelation]) -> Dict[int, int]:
        """
        分析支撑关系
        返回: {物体ID: 被哪个物体支撑}
        """
        support_map = {}
        obj_map = {o.id: o for o in objects}
        
        for rel in relations:
            if rel.relation == "on":
                support_map[rel.subject] = rel.object_id
        
        return support_map
    
    def check_stability(self, obj: SceneObject, 
                        support_obj: Optional[SceneObject] = None) -> Dict:
        """
        检查物体稳定性
        返回: {stable: bool, tilt_risk: float, tipping_direction: str}
        """
        if obj.bbox_3d is None:
            return {"stable": True, "tilt_risk": 0.0, "tipping_direction": "none"}
        
        w, h, d = obj.bbox_3d.size
        base_w = min(w, d)  # 最窄基边
        height = h
        
        # 重心高度(假设均匀密度)
        cg_height = height / 2
        
        # 稳定性 = 基宽/(2*重心高), >1稳定
        stability_ratio = base_w / (2 * cg_height) if cg_height > 0 else 999
        stable = stability_ratio > 1.0
        
        # 倾倒方向: 最窄边方向
        tipping = "side" if w < d else "front"
        
        return {
            "stable": stable,
            "stability_ratio": stability_ratio,
            "tilt_risk": max(0, 1 - stability_ratio),
            "tipping_direction": tipping
        }
    
    def check_occlusion(self, objects: List[SceneObject],
                        depth_map: np.ndarray) -> List[Tuple[int, int]]:
        """
        检查遮挡关系
        返回: [(前方物体ID, 被遮挡物体ID), ...]
        """
        occlusions = []
        
        for i, a in enumerate(objects):
            for j, b in enumerate(objects):
                if i >= j:
                    continue
                
                ax, ay, aw, ah = a.bbox_2d
                bx, by, bw, bh = b.bbox_2d
                
                # 检查2D重叠
                ix = max(0, min(ax+aw, bx+bw) - max(ax, bx))
                iy = max(0, min(ay+ah, by+bh) - max(ay, by))
                if ix * iy < 100:
                    continue
                
                # 比较深度: 深度小=近=前方
                da = self._get_depth_at_center(depth_map, a.bbox_2d)
                db = self._get_depth_at_center(depth_map, b.bbox_2d)
                
                if da > 0 and db > 0:
                    if da < db:
                        occlusions.append((a.id, b.id))
                    else:
                        occlusions.append((b.id, a.id))
        
        return occlusions
    
    def _get_depth_at_center(self, depth_map: np.ndarray, 
                              bbox: Tuple[int, int, int, int], radius: int = 10) -> float:
        x, y, w, h = bbox
        cx, cy = x + w // 2, y + h // 2
        h_d, w_d = depth_map.shape
        x1 = max(0, cx - radius)
        x2 = min(w_d, cx + radius)
        y1 = max(0, cy - radius)
        y2 = min(h_d, cy + radius)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        return float(np.median(depth_map[y1:y2, x1:x2]))


# ═══════════════════════════════════════════
# 统一空间理解接口
# ═══════════════════════════════════════════

class SpatialUnderstanding:
    """统一3D空间理解"""
    
    def __init__(self):
        self.depth = MonocularDepthEstimator()
        self.pointcloud = PointCloudGenerator()
        self.scene_graph = SceneGraphBuilder()
        self.affordance = AffordanceDetector()
        self.physics = PhysicsReasoner()
    
    def understand(self, bgr: np.ndarray,
                   objects_2d: list = None) -> Dict:
        """
        完整3D空间理解
        objects_2d: 2D检测结果列表 [{bbox, name}, ...]
        """
        t0 = time.time()
        h, w = bgr.shape[:2]
        
        # 1. 深度估计
        depth_map = self.depth.estimate(bgr)
        
        # 2. 点云
        points = self.pointcloud.generate(depth_map, bgr, max_points=50000)
        
        # 3. 地面平面
        ground_plane = self.pointcloud.get_plane(points[:min(5000, len(points))])
        
        # 4. 物体深度分配
        scene_objects = []
        if objects_2d:
            for i, obj_2d in enumerate(objects_2d):
                bbox = obj_2d.get("bbox") or obj_2d.get("bbox_2d") or (0,0,0,0)
                name = obj_2d.get("name", f"object_{i}")
                cx, cy = bbox[0]+bbox[2]//2, bbox[1]+bbox[3]//2
                d = self.depth.get_depth_at(depth_map, cx, cy)
                
                so = SceneObject(
                    id=i, name=name, bbox_2d=bbox,
                    depth=d, points=[]
                )
                
                # 收集物体区域的3D点
                for p in points:
                    # 简化: 基于深度范围筛选
                    if abs(p.z - d) < d * 0.3:
                        so.points.append(p)
                
                scene_objects.append(so)
        else:
            # 无2D检测, 使用显著性分区
            fast = {'edge_count': 0, 'corner_count': 0, 'rectangles': 0, 'largest_rect_area': 0}  # placeholder
            scene_objects.append(SceneObject(
                id=0, name="scene", 
                bbox_2d=(0, 0, w, h),
                depth=float(np.median(depth_map)),
                points=points[:10000]
            ))
        
        # 5. 场景图
        relations = self.scene_graph.build(scene_objects)
        
        # 6. 可供性
        affordances = self.affordance.detect(scene_objects, depth_map)
        
        # 7. 物理推理
        support = self.physics.analyze_support(scene_objects, relations)
        occlusions = self.physics.check_occlusion(scene_objects, depth_map)
        
        stability = {}
        for obj in scene_objects:
            supporter = support.get(obj.id)
            sup_obj = next((o for o in scene_objects if o.id == supporter), None)
            stability[obj.id] = self.physics.check_stability(obj, sup_obj)
        
        duration = time.time() - t0
        
        return {
            "depth_map": depth_map,
            "points": points,
            "ground_plane": ground_plane,
            "objects": scene_objects,
            "relations": relations,
            "affordances": affordances,
            "stability": stability,
            "occlusions": occlusions,
            "scene_text": self.scene_graph.to_text(scene_objects, relations),
            "duration": duration,
        }


import time  # needed by understand()
