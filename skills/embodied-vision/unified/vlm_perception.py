"""
embodied-vision/unified/vlm_perception.py — VLM增强感知

用视觉语言模型(GLM-4V)替代规则分类, 实现零样本物体识别和场景理解。

核心思想:
  传统CV提供低层特征(边缘/轮廓/纹理) → VLM提供高层语义(物体名称/关系/可供性)
  两者融合 → 更准确的感知

注意: 此模块通过OpenClaw调用VLM, 不直接调用API
"""

import cv2
import numpy as np
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class VLMObject:
    """VLM检测到的物体"""
    name: str
    description: str
    bbox: Tuple[int, int, int, int]  # 估算bbox
    confidence: float
    attributes: Dict[str, str] = field(default_factory=dict)
    affordances: List[str] = field(default_factory=list)
    spatial_relations: List[str] = field(default_factory=list)


@dataclass
class VLMScene:
    """VLM场景理解"""
    description: str  # 自然语言场景描述
    objects: List[VLMObject]
    room_type: str = "unknown"  # 客厅/厨房/办公室/桌面/工厂
    layout: str = ""  # 空间布局描述
    interactions: List[str] = field(default_factory=list)  # 可执行的交互


class VLMPerception:
    """
    VLM增强感知
    
    使用方式:
      vlm = VLMPerception()
      scene = vlm.analyze_scene(image_path)
      print(scene.description)
      
    设计原则:
      1. 先用传统CV提取特征(快速)
      2. 将特征+图像一起发给VLM(准确)
      3. VLM返回自然语言, 解析为结构化数据
      4. 传统CV提供bbox, VLM提供语义
    """
    
    # VLM提示词模板
    SCENE_PROMPT = """你是一个具身智能机器人的视觉系统。分析这张图片, 返回JSON:

{
  "room_type": "房间类型(desktop/kitchen/office/factory/outdoor/other)",
  "description": "一句话场景描述",
  "objects": [
    {
      "name": "物体名称",
      "description": "简短描述",
      "attributes": {"color": "颜色", "material": "材质", "shape": "形状"},
      "affordances": ["可抓取", "可推开", "可放置在上面"],
      "position": "位置描述(左上/右上/中央/左下/右下)"
    }
  ],
  "spatial_relations": ["物体A在物体B上面", ...],
  "interactions": ["可以执行的操作", ...]
}

只返回JSON, 不要其他文字。"""
    
    OBJECT_PROMPT = """分析图片中的{position}区域(约{x},{y},{w},{h}像素):

返回JSON:
{{
  "name": "物体名称",
  "description": "简短描述(中文)",
  "material": "材质",
  "graspable": true/false,
  "grasp_method": "最佳抓取方式(top/side/pinch)",
  "weight_estimate": "重/中/轻",
  "fragile": true/false
}}

只返回JSON。"""
    
    def __init__(self):
        self.cache: Dict[str, VLMScene] = {}
        self.call_count = 0
    
    def analyze_scene(self, image_path: str, 
                      cv_features: Dict = None) -> VLMScene:
        """
        分析场景 (通过OpenClaw VLM)
        
        注意: 此方法需要被Agent调用时传入VLM的响应
        Agent应该: 看图→用SCENE_PROMPT→解析JSON→调用此方法
        """
        # 如果有缓存, 直接返回
        if image_path in self.cache:
            return self.cache[image_path]
        
        # 构建待VLM填充的结果(占位)
        scene = VLMScene(
            description="[待VLM分析]",
            objects=[],
            room_type="unknown"
        )
        
        self.cache[image_path] = scene
        return scene
    
    def parse_vlm_response(self, json_str: str) -> VLMScene:
        """解析VLM返回的JSON为结构化数据"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试提取JSON块
            import re
            match = re.search(r'\{[\s\S]*\}', json_str)
            if match:
                data = json.loads(match.group())
            else:
                return VLMScene(description="VLM解析失败", objects=[])
        
        scene = VLMScene(
            description=data.get("description", ""),
            room_type=data.get("room_type", "unknown"),
            layout=data.get("layout", ""),
            interactions=data.get("interactions", []),
            spatial_relations=data.get("spatial_relations", [])
        )
        
        for obj_data in data.get("objects", []):
            obj = VLMObject(
                name=obj_data.get("name", "unknown"),
                description=obj_data.get("description", ""),
                bbox=(0, 0, 0, 0),  # 需要传统CV填充
                confidence=0.8,
                attributes=obj_data.get("attributes", {}),
                affordances=obj_data.get("affordances", []),
            )
            scene.objects.append(obj)
        
        return scene
    
    def merge_with_cv(self, vlm_scene: VLMScene,
                      cv_objects: list, image: np.ndarray) -> VLMScene:
        """
        融合VLM语义和CV检测结果
        """
        h, w = image.shape[:2]
        
        # 位置映射: VLM的"左上"等 → 像素bbox
        position_map = {
            "左上": (0, 0, w//2, h//2),
            "右上": (w//2, 0, w//2, h//2),
            "中央": (w//4, h//4, w//2, h//2),
            "左下": (0, h//2, w//2, h//2),
            "右下": (w//2, h//2, w//2, h//2),
            "顶部": (w//4, 0, w//2, h//3),
            "底部": (w//4, 2*h//3, w//2, h//3),
            "左侧": (0, h//4, w//3, h//2),
            "右侧": (2*w//3, h//4, w//3, h//2),
        }
        
        for vlm_obj in vlm_scene.objects:
            # 尝试从传统CV找匹配
            best_match = None
            best_score = 0
            
            for cv_obj in cv_objects:
                score = self._match_score(vlm_obj, cv_obj, image)
                if score > best_score:
                    best_score = score
                    best_match = cv_obj
            
            if best_match and best_score > 0.3:
                vlm_obj.bbox = best_match.get("bbox", (0,0,0,0))
                vlm_obj.confidence = best_score
            else:
                # 用VLM位置描述估算bbox
                for pos_key, bbox in position_map.items():
                    if pos_key in vlm_obj.description or pos_key in vlm_obj.name:
                        vlm_obj.bbox = bbox
                        break
        
        return vlm_scene
    
    def _match_score(self, vlm_obj: VLMObject, cv_obj: Dict,
                     image: np.ndarray) -> float:
        """计算VLM物体和CV物体的匹配分数"""
        score = 0.0
        
        # 颜色匹配
        vlm_color = vlm_obj.attributes.get("color", "")
        if vlm_color and "color" in cv_obj:
            if vlm_color in cv_obj["color"]:
                score += 0.4
        
        # 形状匹配
        vlm_shape = vlm_obj.attributes.get("shape", "")
        cv_category = cv_obj.get("category", "")
        shape_map = {
            "box": ["rect", "square"],
            "circular": ["circle", "cylinder"],
            "flat": ["flat_panel"],
        }
        for vlm_s, cv_cats in shape_map.items():
            if vlm_s in vlm_shape and any(c in cv_category for c in cv_cats):
                score += 0.3
                break
        
        # 面积比例匹配 (VLM描述"大/小" vs CV面积)
        # 简化: 中等分
        score += 0.3
        
        return score


class EmbodiedVisionV2:
    """
    具身视觉V2: 传统CV + VLM融合
    
    使用方式:
      ev = EmbodiedVisionV2()
      result = ev.perceive("photo.jpg", use_vlm=True)
    """
    
    def __init__(self, use_vlm: bool = True):
        self.use_vlm = use_vlm
        self.vlm = VLMPerception()
        
        # 延迟加载传统CV模块
        self._cv_loaded = False
        self._primitives = None
        self._spatial = None
    
    def _ensure_cv(self):
        if self._cv_loaded:
            return
        BASE = Path(__file__).parent.parent
        import sys
        sys.path.insert(0, str(BASE))
        exec(open(str(BASE / "primitives/__init__.py")).read())
        exec(open(str(BASE / "spatial/__init__.py")).read())
        self._primitives = VisualPrimitives()
        self._spatial = SpatialUnderstanding()
        self._cv_loaded = True
    
    def perceive(self, image_path: str, 
                 use_vlm: bool = None) -> Dict:
        """
        完整感知 (CV + VLM)
        返回与传统vision_api兼容的结果 + VLM增强字段
        """
        if use_vlm is None:
            use_vlm = self.use_vlm
        
        self._ensure_cv()
        
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": f"无法读取: {image_path}"}
        
        t0 = time.time()
        result = {}
        
        # === 传统CV部分 ===
        fast = self._primitives.perceive_fast(img)
        result.update({
            "image_size": (img.shape[1], img.shape[0]),
            "edge_pixels": fast["edge_count"],
            "corners": fast["corner_count"],
            "rectangles": fast.get("rectangles", 0),
        })
        
        full = self._primitives.perceive(img)
        result.update({
            "contours": len(full["contours"]),
            "texture_std": full["texture"].std,
            "texture_entropy": full["texture"].entropy,
            "color_regions": len(full["color_regions"]),
            "cv_objects": [
                {"bbox": c.bbox, "shape": c.shape_type, "area": c.area}
                for c in full["contours"][:10]
            ]
        })
        
        spatial = self._spatial.understand(img)
        result.update({
            "point_cloud": len(spatial["points"]),
            "depth_range": [float(spatial["depth_map"].min()), 
                           float(spatial["depth_map"].max())],
            "ground_plane": list(spatial["ground_plane"]) if spatial["ground_plane"] else None,
            "affordances": {str(k): v for k, v in spatial["affordances"].items()},
        })
        
        # === VLM部分 ===
        if use_vlm:
            # VLM分析结果(需要Agent调用VLM填充)
            vlm_result = self.vlm.analyze_scene(image_path)
            result["vlm"] = {
                "description": vlm_result.description,
                "room_type": vlm_result.room_type,
                "objects": [{"name": o.name, "description": o.description,
                            "affordances": o.affordances} 
                           for o in vlm_result.objects],
                "note": "VLM结果为占位, 需要Agent实际调用VLM API填充"
            }
        
        result["duration_ms"] = (time.time() - t0) * 1000
        result["success"] = True
        
        return result
    
    def get_vlm_prompt(self, image_path: str) -> str:
        """获取用于VLM分析的prompt(供Agent使用)"""
        return VLMPerception.SCENE_PROMPT


if __name__ == "__main__":
    import sys
    
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
    
    ev = EmbodiedVisionV2(use_vlm=False)
    result = ev.perceive(path)
    
    print(f"感知结果 ({result['duration_ms']:.0f}ms):")
    print(f"  边缘: {result['edge_pixels']:,}")
    print(f"  角点: {result['corners']}")
    print(f"  轮廓: {result['contours']}")
    print(f"  点云: {result['point_cloud']:,}")
    print(f"  深度: {result['depth_range']}")
    
    # VLM prompt
    print(f"\nVLM Prompt (供Agent调用):")
    print(f"  {ev.get_vlm_prompt(path)[:100]}...")
