"""
高级Python模块：实现所见即所得(WYSIWYG)的物理材质编辑器
用途：桥接Flutter前端与CAD/渲染后端，实时同步PBR材质参数
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wysiwyg_material_editor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PBRMaterial:
    """
    基于物理的渲染(PBR)材质数据结构
    
    Attributes:
        albedo (Tuple[float, float, float]): 漫反射颜色 (RGB, 0.0-1.0)
        metallic (float): 金属度 (0.0-1.0)
        roughness (float): 粗糙度 (0.0-1.0)
        normal_intensity (float): 法线强度 (0.0-2.0)
        rust_level (float): 生锈程度 (0.0-1.0)
        emissive (Tuple[float, float, float]): 自发光颜色 (RGB, 0.0-1.0)
        ao (float): 环境光遮蔽强度 (0.0-1.0)
        material_id (str): 材质唯一标识符
    """
    albedo: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    metallic: float = 0.0
    roughness: float = 0.5
    normal_intensity: float = 1.0
    rust_level: float = 0.0
    emissive: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ao: float = 1.0
    material_id: str = "default_material"


class MaterialValidator:
    """PBR材质参数验证器"""
    
    @staticmethod
    def validate_color(color: Tuple[float, float, float]) -> bool:
        """验证RGB颜色值是否在0.0-1.0范围内"""
        return all(0.0 <= c <= 1.0 for c in color)
    
    @staticmethod
    def validate_factor(value: float, min_val: float = 0.0, max_val: float = 1.0) -> bool:
        """验证标量参数是否在指定范围内"""
        return min_val <= value <= max_val
    
    @classmethod
    def validate_material(cls, material: PBRMaterial) -> bool:
        """验证整个材质对象的参数有效性"""
        try:
            if not cls.validate_color(material.albedo):
                raise ValueError(f"Invalid albedo color: {material.albedo}")
            if not cls.validate_color(material.emissive):
                raise ValueError(f"Invalid emissive color: {material.emissive}")
            if not cls.validate_factor(material.metallic):
                raise ValueError(f"Invalid metallic value: {material.metallic}")
            if not cls.validate_factor(material.roughness):
                raise ValueError(f"Invalid roughness value: {material.roughness}")
            if not cls.validate_factor(material.normal_intensity, 0.0, 2.0):
                raise ValueError(f"Invalid normal intensity: {material.normal_intensity}")
            if not cls.validate_factor(material.rust_level):
                raise ValueError(f"Invalid rust level: {material.rust_level}")
            if not cls.validate_factor(material.ao):
                raise ValueError(f"Invalid ambient occlusion value: {material.ao}")
            return True
        except ValueError as e:
            logger.error(f"Material validation failed: {str(e)}")
            return False


class FlutterShaderBridge:
    """
    Flutter着色器桥接器
    处理Flutter界面与GLSL着色器之间的参数传递
    """
    
    @staticmethod
    def generate_shader_uniforms(material: PBRMaterial) -> Dict[str, Any]:
        """
        将材质参数转换为GLSL着色器uniform变量格式
        
        Args:
            material: PBR材质对象
            
        Returns:
            Dict[str, Any]: 可直接传递给Flutter Shader的uniform字典
        """
        if not MaterialValidator.validate_material(material):
            logger.warning("Generating shader uniforms with potentially invalid material")
        
        uniforms = {
            "u_albedo": list(material.albedo),
            "u_metallic": material.metallic,
            "u_roughness": material.roughness,
            "u_normal_intensity": material.normal_intensity,
            "u_rust_level": material.rust_level,
            "u_emissive": list(material.emissive),
            "u_ao": material.ao,
        }
        
        logger.debug(f"Generated shader uniforms: {uniforms}")
        return uniforms
    
    @staticmethod
    def apply_rust_effect(material: PBRMaterial, rust_map: Optional[np.ndarray] = None) -> PBRMaterial:
        """
        应用生锈效果到材质
        
        Args:
            material: 原始PBR材质
            rust_map: 可选的生锈纹理贴图 (H x W x 1)
            
        Returns:
            PBRMaterial: 应用生锈效果后的新材质对象
        """
        if rust_map is not None and not isinstance(rust_map, np.ndarray):
            raise TypeError("Rust map must be a numpy array")
            
        new_material = PBRMaterial(**asdict(material))
        
        # 根据生锈程度调整材质参数
        rust_factor = material.rust_level
        new_material.roughness = min(1.0, material.roughness + rust_factor * 0.4)
        new_material.metallic = max(0.0, material.metallic - rust_factor * 0.7)
        
        # 调整颜色向橙红色偏移（生锈效果）
        rust_color = np.array([0.6, 0.3, 0.1])
        original_albedo = np.array(material.albedo)
        new_albedo = original_albedo * (1 - rust_factor) + rust_color * rust_factor
        new_material.albedo = tuple(np.clip(new_albedo, 0.0, 1.0))
        
        logger.info(f"Applied rust effect with level {rust_factor:.2f}")
        return new_material


class CADMaterialSynchronizer:
    """
    CAD材质同步器
    处理与CAD系统材质库的同步操作
    """
    
    def __init__(self, library_path: Union[str, Path]):
        """
        初始化同步器
        
        Args:
            library_path: CAD材质库文件路径
        """
        self.library_path = Path(library_path)
        self._ensure_library_exists()
        
    def _ensure_library_exists(self) -> None:
        """确保材质库文件存在"""
        if not self.library_path.exists():
            self.library_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.library_path, 'w') as f:
                json.dump({"materials": []}, f)
            logger.info(f"Created new material library at {self.library_path}")
    
    def load_material(self, material_id: str) -> Optional[PBRMaterial]:
        """
        从CAD材质库加载指定材质
        
        Args:
            material_id: 材质唯一标识符
            
        Returns:
            Optional[PBRMaterial]: 找到的材质对象，或None
        """
        try:
            with open(self.library_path, 'r') as f:
                data = json.load(f)
                
            for mat_data in data.get("materials", []):
                if mat_data.get("material_id") == material_id:
                    logger.info(f"Loaded material {material_id} from CAD library")
                    return PBRMaterial(**mat_data)
                    
            logger.warning(f"Material {material_id} not found in CAD library")
            return None
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load material {material_id}: {str(e)}")
            return None
    
    def sync_material(self, material: PBRMaterial) -> bool:
        """
        将材质同步到CAD材质库
        
        Args:
            material: 要同步的PBR材质对象
            
        Returns:
            bool: 同步是否成功
        """
        if not MaterialValidator.validate_material(material):
            logger.error("Attempted to sync invalid material")
            return False
            
        try:
            # 读取现有库
            with open(self.library_path, 'r') as f:
                data = json.load(f) if self.library_path.exists() else {"materials": []}
            
            # 更新或添加材质
            materials = data.get("materials", [])
            updated = False
            
            for i, mat in enumerate(materials):
                if mat.get("material_id") == material.material_id:
                    materials[i] = asdict(material)
                    updated = True
                    break
                    
            if not updated:
                materials.append(asdict(material))
            
            # 保存更新后的库
            data["materials"] = materials
            with open(self.library_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Successfully synced material {material.material_id} to CAD library")
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to sync material {material.material_id}: {str(e)}")
            return False


# 使用示例
if __name__ == "__main__":
    # 示例1: 创建材质并生成着色器uniforms
    material = PBRMaterial(
        albedo=(0.7, 0.2, 0.1),
        metallic=0.8,
        roughness=0.3,
        rust_level=0.2
    )
    
    shader_uniforms = FlutterShaderBridge.generate_shader_uniforms(material)
    print("Shader Uniforms:", shader_uniforms)
    
    # 示例2: 应用生锈效果
    rusted_material = FlutterShaderBridge.apply_rust_effect(material)
    print("Rusted Material:", asdict(rusted_material))
    
    # 示例3: 与CAD材质库同步
    try:
        synchronizer = CADMaterialSynchronizer("./cad_material_library.json")
        synchronizer.sync_material(rusted_material)
        
        loaded_material = synchronizer.load_material(rusted_material.material_id)
        if loaded_material:
            print("Material loaded from CAD:", asdict(loaded_material))
    except Exception as e:
        logger.error(f"CAD synchronization failed: {str(e)}")