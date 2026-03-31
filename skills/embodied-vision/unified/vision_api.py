#!/usr/bin/env python3
"""
embodied-vision — 统一视觉API
所有模块的单一入口点

用法:
  python unified/vision_api.py <image_path>
  python unified/vision_api.py --demo
"""

import cv2
import numpy as np
import sys
import os
import time
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

# 确保可以找到模块
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

# 直接加载模块 (避免包导入问题)
exec(open(str(SCRIPT_DIR / "primitives/__init__.py")).read())
exec(open(str(SCRIPT_DIR / "detection/__init__.py")).read())
exec(open(str(SCRIPT_DIR / "spatial/__init__.py")).read())


@dataclass
class VisionResult:
    """统一视觉结果"""
    # 基础
    image_path: str = ""
    image_size: Tuple[int, int] = (0, 0)
    duration_ms: float = 0.0
    
    # P1: 感知原语
    edge_pixel_count: int = 0
    corner_count: int = 0
    rectangle_count: int = 0
    texture_std: float = 0.0
    texture_entropy: float = 0.0
    texture_direction: float = 0.0
    color_regions: int = 0
    contours_total: int = 0
    contours_top5: List[Dict] = field(default_factory=list)
    
    # P2: 检测
    detected_objects: int = 0
    object_details: List[Dict] = field(default_factory=list)
    
    # P3: 空间
    point_cloud_size: int = 0
    ground_plane: Optional[List[float]] = None
    depth_range: Tuple[float, float] = (0.0, 0.0)
    scene_relations: List[Dict] = field(default_factory=list)
    affordances: Dict[str, List[str]] = field(default_factory=dict)
    stability: Dict[str, Dict] = field(default_factory=dict)
    scene_text: str = ""
    
    # 元信息
    timestamp: str = ""
    success: bool = True
    error: str = ""


class EmbodiedVisionAPI:
    """
    具身智能统一视觉API
    
    一行代码获取完整视觉理解:
        api = EmbodiedVisionAPI()
        result = api.perceive("photo.jpg")
        print(result.scene_text)
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.primitives = VisualPrimitives()
        self.detector = ObjectDetector()
        self.spatial = SpatialUnderstanding()
    
    def perceive(self, image_path: str, 
                 mode: str = "full") -> VisionResult:
        """
        感知一张图像
        
        mode:
          "fast" — 仅边缘+角点+矩形 (<0.1s)
          "standard" — +轮廓+纹理+颜色+检测 (<1s)
          "full" — +深度+点云+场景图+可供性+物理推理 (<5s)
          "complete" — full + 中间可视化图片
        """
        t0 = time.time()
        result = VisionResult(
            image_path=image_path,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                result.success = False
                result.error = f"无法读取: {image_path}"
                return result
            
            result.image_size = (img.shape[1], img.shape[0])
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            
            # === P1: 感知原语 ===
            fast = self.primitives.perceive_fast(img)
            result.edge_pixel_count = fast["edge_count"]
            result.corner_count = fast["corner_count"]
            result.rectangle_count = fast["rectangles"]
            
            if mode in ("standard", "full", "complete"):
                full_percept = self.primitives.perceive(img)
                result.texture_std = full_percept["texture"].std
                result.texture_entropy = full_percept["texture"].entropy
                result.texture_direction = full_percept["texture"].dominant_direction
                result.color_regions = len(full_percept["color_regions"])
                result.contours_total = len(full_percept["contours"])
                
                result.contours_top5 = [
                    {"shape": c.shape_type, "area": round(c.area, 0),
                     "circularity": round(c.circularity, 2),
                     "aspect_ratio": round(c.aspect_ratio, 2),
                     "solidity": round(c.solidity, 2)}
                    for c in full_percept["contours"][:5]
                ]
            
            # === P2: 检测 ===
            if mode in ("standard", "full", "complete"):
                objects = self.detector.detect_and_classify(img)
                result.detected_objects = len(objects)
                result.object_details = [
                    {"id": o.id, "category": o.category, "score": round(o.score, 2),
                     "bbox": list(o.bbox)}
                    for o in objects[:10]
                ]
            
            # === P3: 空间 ===
            if mode in ("full", "complete"):
                spatial_result = self.spatial.understand(img)
                result.point_cloud_size = len(spatial_result["points"])
                result.ground_plane = (list(spatial_result["ground_plane"]) 
                                       if spatial_result["ground_plane"] else None)
                
                dm = spatial_result["depth_map"]
                result.depth_range = (float(dm.min()), float(dm.max()))
                
                result.scene_relations = [
                    {"subject": r.subject, "object": r.object_id,
                     "relation": r.relation, "confidence": round(r.confidence, 2)}
                    for r in spatial_result["relations"][:10]
                ]
                
                result.affordances = {
                    str(k): v for k, v in spatial_result["affordances"].items()
                }
                result.stability = {
                    str(k): v for k, v in spatial_result["stability"].items()
                }
                result.scene_text = spatial_result["scene_text"]
            
            result.duration_ms = (time.time() - t0) * 1000
        
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.duration_ms = (time.time() - t0) * 1000
        
        return result
    
    def perceive_array(self, image_array: np.ndarray, mode: str = "standard") -> VisionResult:
        """直接从numpy数组感知"""
        tmp_path = "/tmp/embodied_vision_tmp.jpg"
        cv2.imwrite(tmp_path, image_array)
        result = self.perceive(tmp_path, mode)
        os.remove(tmp_path)
        result.image_path = "array_input"
        return result


def print_result(r: VisionResult):
    """打印视觉结果摘要"""
    print(f"{'='*60}")
    print(f"  具身智能视觉API结果")
    print(f"{'='*60}")
    print(f"  图像: {r.image_path}")
    print(f"  尺寸: {r.image_size[0]}x{r.image_size[1]}")
    print(f"  耗时: {r.duration_ms:.0f}ms")
    print(f"{'─'*60}")
    print(f"  感知原语:")
    print(f"    边缘像素: {r.edge_pixel_count:,}")
    print(f"    角点数:   {r.corner_count}")
    print(f"    矩形数:   {r.rectangle_count}")
    print(f"    纹理:     std={r.texture_std:.1f} entropy={r.texture_entropy:.2f} 方向={r.texture_direction:.0f}°")
    print(f"    颜色区域: {r.color_regions}")
    print(f"    轮廓总数: {r.contours_total}")
    if r.contours_top5:
        print(f"    TOP5轮廓:")
        for c in r.contours_top5:
            print(f"      {c['shape']}: area={c['area']:.0f} circ={c['circularity']:.2f} ar={c['aspect_ratio']:.2f}")
    print(f"{'─'*60}")
    print(f"  目标检测: {r.detected_objects} 个物体")
    for obj in r.object_details[:5]:
        print(f"    #{obj['id']} {obj['category']} (置信={obj['score']:.2f}) {obj['bbox']}")
    if r.point_cloud_size > 0:
        print(f"{'─'*60}")
        print(f"  空间理解:")
        print(f"    点云: {r.point_cloud_size:,} 点")
        print(f"    深度范围: {r.depth_range[0]:.0f} - {r.depth_range[1]:.0f} mm")
        print(f"    地面: {r.ground_plane}")
        print(f"    可供性: {r.affordances}")
        print(f"    稳定性: {r.stability}")
    if r.scene_text:
        print(f"{'─'*60}")
        print(f"  场景描述:")
        for line in r.scene_text.split('\n'):
            print(f"    {line}")
    print(f"{'='*60}")
    
    if not r.success:
        print(f"  ❌ 错误: {r.error}")


def demo():
    """演示: 对所有DiePre样本运行感知"""
    samples = [
        "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg",
        "/Users/administruter/Desktop/6b119ad2dc8b0f107979dc11a0fa3515.jpg",
        "/Users/administruter/Desktop/92a52f66546d6b97e887320e2dc06443.jpg",
    ]
    
    api = EmbodiedVisionAPI()
    
    for mode in ["fast", "standard", "full"]:
        print(f"\n{'#'*60}")
        print(f"#  Mode: {mode}")
        print(f"{'#'*60}")
        
        for path in samples:
            if not os.path.exists(path):
                continue
            result = api.perceive(path, mode=mode)
            print(f"\n{os.path.basename(path)}:")
            print(f"  耗时={result.duration_ms:.0f}ms "
                  f"边缘={result.edge_pixel_count} "
                  f"角点={result.corner_count} "
                  f"轮廓={result.contours_total} "
                  f"物体={result.detected_objects} "
                  f"点云={result.point_cloud_size}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            demo()
        else:
            api = EmbodiedVisionAPI()
            result = api.perceive(sys.argv[1], mode="full")
            print_result(result)
    else:
        demo()
