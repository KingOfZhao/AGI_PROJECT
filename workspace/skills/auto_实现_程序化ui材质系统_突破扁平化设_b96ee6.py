"""
高级程序化UI材质系统

该模块实现了一个程序化UI材质系统，将CAD领域的PBR(基于物理的渲染)材质概念引入Flutter UI组件。
允许开发者定义组件的物理属性（粗糙度、金属度等），使UI元素具备真实物理材质的光影表现。

核心功能:
- 材质属性定义和验证
- 光照交互模拟
- 表面散射效果计算
- 材质预设管理

示例用法:
>>> material_system = ProceduralUIMaterialSystem()
>>> glass_material = material_system.create_material(
...     name="frosted_glass",
...     base_color=(0.95, 0.95, 0.98),
...     roughness=0.85,
...     metalness=0.1,
...     subsurface_scattering=0.4
... )
>>> render_result = material_system.render_material(glass_material, lighting_conditions=(1.0, 0.8))
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional, List, Union
from enum import Enum, auto
from functools import lru_cache

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MaterialType(Enum):
    """支持的材质类型枚举"""
    GLASS = auto()
    METAL = auto()
    PLASTIC = auto()
    FABRIC = auto()
    LIQUID = auto()
    CUSTOM = auto()


@dataclass
class MaterialProperties:
    """材质属性数据类，包含所有物理材质参数"""
    name: str
    base_color: Tuple[float, float, float]  # RGB值 (0.0-1.0)
    roughness: float = 0.5  # 表面粗糙度 (0.0-1.0)
    metalness: float = 0.0  # 金属度 (0.0-1.0)
    subsurface_scattering: float = 0.0  # 次表面散射强度 (0.0-1.0)
    opacity: float = 1.0  # 不透明度 (0.0-1.0)
    refractive_index: float = 1.5  # 折射率 (玻璃≈1.5, 水≈1.33)
    material_type: MaterialType = MaterialType.CUSTOM
    
    def __post_init__(self):
        """初始化后验证数据"""
        self._validate_properties()
    
    def _validate_properties(self) -> None:
        """验证材质属性的有效性"""
        if not (0.0 <= self.roughness <= 1.0):
            raise ValueError(f"粗糙度必须在0.0到1.0之间，当前值: {self.roughness}")
        if not (0.0 <= self.metalness <= 1.0):
            raise ValueError(f"金属度必须在0.0到1.0之间，当前值: {self.metalness}")
        if not (0.0 <= self.subsurface_scattering <= 1.0):
            raise ValueError(f"次表面散射强度必须在0.0到1.0之间，当前值: {self.subsurface_scattering}")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"不透明度必须在0.0到1.0之间，当前值: {self.opacity}")
        if not (1.0 <= self.refractive_index <= 3.0):
            raise ValueError(f"折射率必须在1.0到3.0之间，当前值: {self.refractive_index}")
        if not all(0.0 <= c <= 1.0 for c in self.base_color):
            raise ValueError(f"基础颜色RGB值必须在0.0到1.0之间，当前值: {self.base_color}")


class ProceduralUIMaterialSystem:
    """
    程序化UI材质系统核心类
    
    实现基于物理的渲染材质系统，为UI组件提供真实感的材质表现。
    """
    
    def __init__(self, max_cached_materials: int = 100):
        """
        初始化材质系统
        
        Args:
            max_cached_materials: 缓存的最大材质数量
        """
        self.materials_library: Dict[str, MaterialProperties] = {}
        self.max_cached_materials = max_cached_materials
        self._initialize_presets()
        logger.info("Procedural UI Material System initialized")
    
    def _initialize_presets(self) -> None:
        """初始化内置材质预设"""
        presets = [
            MaterialProperties(
                name="frosted_glass",
                base_color=(0.95, 0.95, 0.98),
                roughness=0.85,
                metalness=0.1,
                subsurface_scattering=0.4,
                opacity=0.7,
                refractive_index=1.5,
                material_type=MaterialType.GLASS
            ),
            MaterialProperties(
                name="brushed_metal",
                base_color=(0.8, 0.8, 0.85),
                roughness=0.4,
                metalness=0.9,
                subsurface_scattering=0.0,
                opacity=1.0,
                refractive_index=1.0,
                material_type=MaterialType.METAL
            ),
            MaterialProperties(
                name="matte_plastic",
                base_color=(0.2, 0.2, 0.2),
                roughness=0.95,
                metalness=0.0,
                subsurface_scattering=0.1,
                opacity=1.0,
                refractive_index=1.0,
                material_type=MaterialType.PLASTIC
            )
        ]
        
        for preset in presets:
            self.materials_library[preset.name] = preset
        logger.info(f"Loaded {len(presets)} material presets")
    
    def create_material(
        self,
        name: str,
        base_color: Tuple[float, float, float],
        roughness: float = 0.5,
        metalness: float = 0.0,
        subsurface_scattering: float = 0.0,
        opacity: float = 1.0,
        refractive_index: float = 1.5,
        material_type: MaterialType = MaterialType.CUSTOM
    ) -> MaterialProperties:
        """
        创建新的材质
        
        Args:
            name: 材质名称
            base_color: 基础颜色RGB值 (0.0-1.0)
            roughness: 表面粗糙度 (0.0-1.0)
            metalness: 金属度 (0.0-1.0)
            subsurface_scattering: 次表面散射强度 (0.0-1.0)
            opacity: 不透明度 (0.0-1.0)
            refractive_index: 折射率 (1.0-3.0)
            material_type: 材质类型
            
        Returns:
            创建的材质属性对象
            
        Raises:
            ValueError: 如果材质参数无效
        """
        if name in self.materials_library:
            logger.warning(f"Material '{name}' already exists, will be overwritten")
        
        try:
            material = MaterialProperties(
                name=name,
                base_color=base_color,
                roughness=roughness,
                metalness=metalness,
                subsurface_scattering=subsurface_scattering,
                opacity=opacity,
                refractive_index=refractive_index,
                material_type=material_type
            )
            
            if len(self.materials_library) >= self.max_cached_materials:
                self._clean_cache()
                
            self.materials_library[name] = material
            logger.info(f"Created new material: {name}")
            return material
            
        except ValueError as e:
            logger.error(f"Failed to create material '{name}': {str(e)}")
            raise
    
    def render_material(
        self,
        material: Union[str, MaterialProperties],
        lighting_conditions: Tuple[float, float] = (1.0, 1.0),
        view_angle: float = 0.0
    ) -> Dict[str, Union[Tuple[float, float, float], float]]:
        """
        渲染材质效果
        
        Args:
            material: 材质对象或材质名称
            lighting_conditions: 光照条件 (强度, 环境光)
            view_angle: 观察角度 (弧度)
            
        Returns:
            包含渲染结果的字典:
            {
                'final_color': RGB元组,
                'specular_intensity': 高光强度,
                'diffuse_intensity': 漫反射强度,
                'scattering_effect': 散射效果强度
            }
            
        Raises:
            ValueError: 如果材质不存在或参数无效
        """
        if isinstance(material, str):
            if material not in self.materials_library:
                raise ValueError(f"Material '{material}' not found in library")
            material = self.materials_library[material]
        
        if not isinstance(material, MaterialProperties):
            raise ValueError("Invalid material type")
        
        if not (0.0 <= lighting_conditions[0] <= 2.0) or not (0.0 <= lighting_conditions[1] <= 1.0):
            raise ValueError("Lighting conditions must be in range (0.0-2.0, 0.0-1.0)")
        
        try:
            # 计算基础光照效果
            light_intensity, ambient_light = lighting_conditions
            diffuse = self._calculate_diffuse(material, light_intensity)
            specular = self._calculate_specular(material, light_intensity, view_angle)
            scattering = self._calculate_scattering(material, light_intensity)
            
            # 合成最终颜色
            final_color = tuple(
                min(1.0, c * diffuse * (1.0 - material.metalness) + 
                    specular * material.metalness + 
                    scattering * material.subsurface_scattering)
                for c in material.base_color
            )
            
            result = {
                'final_color': final_color,
                'specular_intensity': specular,
                'diffuse_intensity': diffuse,
                'scattering_effect': scattering
            }
            
            logger.debug(f"Rendered material '{material.name}' with lighting {lighting_conditions}")
            return result
            
        except Exception as e:
            logger.error(f"Error rendering material '{material.name}': {str(e)}")
            raise
    
    @lru_cache(maxsize=128)
    def _calculate_diffuse(self, material: MaterialProperties, light_intensity: float) -> float:
        """
        计算漫反射强度 (辅助函数)
        
        Args:
            material: 材质属性
            light_intensity: 光照强度
            
        Returns:
            漫反射强度 (0.0-1.0)
        """
        # 漫反射强度受粗糙度和金属度影响
        diffuse = (1.0 - material.roughness) * (1.0 - material.metalness) * light_intensity
        return max(0.1, min(1.0, diffuse))  # 确保在合理范围内
    
    def _calculate_specular(
        self, 
        material: MaterialProperties, 
        light_intensity: float, 
        view_angle: float
    ) -> float:
        """
        计算高光反射强度 (核心函数)
        
        Args:
            material: 材质属性
            light_intensity: 光照强度
            view_angle: 观察角度 (弧度)
            
        Returns:
            高光反射强度 (0.0-1.0)
        """
        # 高光强度基于金属度和粗糙度
        base_specular = material.metalness * (1.0 - material.roughness)
        
        # 根据观察角度调整高光强度
        angle_factor = math.cos(view_angle) ** 2
        
        # 组合计算最终高光强度
        specular = base_specular * light_intensity * angle_factor
        return max(0.0, min(1.0, specular))
    
    def _calculate_scattering(
        self, 
        material: MaterialProperties, 
        light_intensity: float
    ) -> float:
        """
        计算次表面散射效果 (核心函数)
        
        Args:
            material: 材质属性
            light_intensity: 光照强度
            
        Returns:
            散射效果强度 (0.0-1.0)
        """
        if material.subsurface_scattering <= 0.0:
            return 0.0
        
        # 散射效果受材质类型和折射率影响
        type_factor = {
            MaterialType.GLASS: 1.2,
            MaterialType.LIQUID: 1.1,
            MaterialType.FABRIC: 0.8,
            MaterialType.PLASTIC: 0.6,
            MaterialType.METAL: 0.0,
            MaterialType.CUSTOM: 1.0
        }.get(material.material_type, 1.0)
        
        # 计算散射强度
        scattering = material.subsurface_scattering * type_factor * light_intensity
        
        # 考虑折射率的影响
        refraction_factor = 1.0 / material.refractive_index if material.refractive_index > 0 else 1.0
        scattering *= refraction_factor
        
        return max(0.0, min(1.0, scattering))
    
    def _clean_cache(self) -> None:
        """清理材质缓存"""
        # 简单的清理策略：保留内置预设
        materials_to_remove = [
            name for name in self.materials_library 
            if name not in ["frosted_glass", "brushed_metal", "matte_plastic"]
        ]
        
        for name in materials_to_remove:
            del self.materials_library[name]
        
        logger.info(f"Cleaned material cache, removed {len(materials_to_remove)} materials")
    
    def get_material(self, name: str) -> Optional[MaterialProperties]:
        """
        获取材质属性
        
        Args:
            name: 材质名称
            
        Returns:
            材质属性对象，如果不存在则返回None
        """
        return self.materials_library.get(name)
    
    def list_materials(self) -> List[str]:
        """获取所有可用材质名称列表"""
        return list(self.materials_library.keys())


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化材质系统
        material_system = ProceduralUIMaterialSystem()
        
        # 创建自定义材质
        custom_material = material_system.create_material(
            name="custom_glass",
            base_color=(0.8, 0.9, 0.95),
            roughness=0.75,
            metalness=0.2,
            subsurface_scattering=0.5,
            opacity=0.6,
            material_type=MaterialType.GLASS
        )
        
        # 渲染材质效果
        render_result = material_system.render_material(
            material=custom_material,
            lighting_conditions=(1.2, 0.7),
            view_angle=math.pi/4
        )
        
        print("\n渲染结果:")
        print(f"最终颜色: {render_result['final_color']}")
        print(f"高光强度: {render_result['specular_intensity']:.2f}")
        print(f"漫反射强度: {render_result['diffuse_intensity']:.2f}")
        print(f"散射效果: {render_result['scattering_effect']:.2f}")
        
        # 列出所有可用材质
        print("\n可用材质:", material_system.list_materials())
        
    except Exception as e:
        logger.error(f"Error in material system demo: {str(e)}")