"""
Module: zero_shot_building_adaptation
Description: 实现跨气候区的建筑零样本适应设计。
             利用迁移学习原理，建立一个通用建筑核心模型，并根据特定气候数据
             自动调整建筑表皮参数。
Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClimateZone(Enum):
    """定义主要气候区枚举"""
    TROPICAL = "tropical"
    ARID = "arid"
    TEMPERATE = "temperate"
    CONTINENTAL = "continental"
    POLAR = "polar"


@dataclass
class ClimateData:
    """
    输入气候数据结构。
    
    Attributes:
        avg_summer_temp (float): 夏季平均温度 (摄氏度)
        avg_winter_temp (float): 冬季平均温度 (摄氏度)
        humidity_avg (float): 平均湿度 (%)
        solar_radiation (float): 太阳辐射强度 (W/m^2)
        latitude (float): 纬度 (用于计算太阳高度角)
    """
    avg_summer_temp: float
    avg_winter_temp: float
    humidity_avg: float
    solar_radiation: float
    latitude: float

    def __post_init__(self):
        """数据验证"""
        if not (-60 <= self.avg_winter_temp <= 50):
            raise ValueError(f"无效的冬季温度: {self.avg_winter_temp}")
        if not (-30 <= self.avg_summer_temp <= 60):
            raise ValueError(f"无效的夏季温度: {self.avg_summer_temp}")
        if not (0 <= self.humidity_avg <= 100):
            raise ValueError(f"无效的湿度值: {self.humidity_avg}")
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"无效的纬度: {self.latitude}")


@dataclass
class BuildingCoreModel:
    """
    通用建筑核心模型（基础骨架）。
    包含不变的内部逻辑（如功能分区比例、结构逻辑）。
    """
    total_floor_area: float  # 总建筑面积 (平方米)
    window_to_wall_ratio_base: float = 0.4  # 基础窗墙比
    structural_grid: Tuple[float, float] = (8.0, 8.0)  # 结构柱网 (米)


@dataclass
class AdaptiveSkinParameters:
    """
    输出的自适应表皮参数。
    
    Attributes:
        shading_type (str): 遮阳类型
        shading_angle (float): 遮阳构件角度 (度)
        u_value (float): 外墙传热系数 (W/m^2K) - 越低保温越好
        shgc (float): 太阳得热系数 - 越低隔热越好
        material_recommendation (str): 推荐表皮材料
        window_ratio_adjusted (float): 调整后的窗墙比
    """
    shading_type: str
    shading_angle: float
    u_value: float
    shgc: float
    material_recommendation: str
    window_ratio_adjusted: float


def _map_climate_zone(climate_data: ClimateData) -> ClimateZone:
    """
    [辅助函数] 根据气温数据简单映射气候区。
    
    这是一个简化的逻辑，实际应用中会使用更复杂的Köppen分类。
    
    Args:
        climate_data (ClimateData): 输入的气候数据对象
        
    Returns:
        ClimateZone: 预测的气候区枚举值
    """
    logger.debug(f"Mapping climate zone for data: {climate_data}")
    
    avg_annual_temp = (climate_data.avg_summer_temp + climate_data.avg_winter_temp) / 2
    
    if climate_data.avg_summer_temp > 35 and climate_data.humidity_avg < 50:
        return ClimateZone.ARID
    elif climate_data.avg_summer_temp > 30 and climate_data.humidity_avg > 70:
        return ClimateZone.TROPICAL
    elif avg_annual_temp < 0:
        return ClimateZone.POLAR
    elif climate_data.avg_winter_temp < -5:
        return ClimateZone.CONTINENTAL
    else:
        return ClimateZone.TEMPERATE


def calculate_solar_geometry_params(latitude: float, hour: int = 12) -> float:
    """
    [核心函数1] 计算特定纬度的太阳高度角参数（简化版）。
    
    用于决定遮阳构件的最佳倾角。
    
    Args:
        latitude (float): 建筑地点纬度
        hour (int): 计算的时间点（默认正午）
        
    Returns:
        float: 正午太阳高度角的近似值（度）
    """
    if not (-90 <= latitude <= 90):
        logger.error("纬度超出范围")
        raise ValueError("Latitude must be between -90 and 90")
        
    # 简化的正午太阳高度角计算 (假设夏至日最大辐射需求)
    # 太阳高度角 = 90 - (纬度 - 赤纬度)
    # 夏至日赤纬度约为 23.5
    declination = 23.5
    solar_altitude = 90 - abs(latitude - declination)
    
    logger.info(f"Calculated Solar Altitude: {solar_altitude:.2f} degrees")
    return solar_altitude


def generate_adaptive_skin(
    core_model: BuildingCoreModel, 
    climate_data: ClimateData
) -> AdaptiveSkinParameters:
    """
    [核心函数2] 实现零样本适应逻辑。
    
    该函数是迁移学习的“适配器”部分。它不改变Core Model，
    而是根据Climate Data生成表皮参数。
    
    Args:
        core_model (BuildingCoreModel): 通用建筑模型配置
        climate_data (ClimateData): 目标地点的气候数据
        
    Returns:
        AdaptiveSkinParameters: 计算出的具体设计参数
        
    Raises:
        ValueError: 如果输入数据不符合物理逻辑
    """
    logger.info(f"Starting adaptation for region with Summer Temp: {climate_data.avg_summer_temp}")
    
    # 1. 识别气候特征
    zone = _map_climate_zone(climate_data)
    logger.info(f"Detected Climate Zone: {zone.value}")
    
    # 2. 初始化默认参数
    shading_type = "Fixed Overhangs"
    u_value = 0.25  # 默认保温性能
    shgc = 0.4      # 默认遮阳性能
    material = "Concrete/Glass Composite"
    adjusted_wwr = core_model.window_to_wall_ratio_base
    
    # 3. 基于气候区的参数调整逻辑
    if zone == ClimateZone.ARID:
        # 高温干燥：需要极强遮阳，防止过热，保留热量在冬季（如果有）
        shading_type = "Deep Horizontal Louvers"
        u_value = 0.20  # 需要良好隔热
        shgc = 0.15     # 极低得热
        material = "High-Performance Glazing with Ceramic Frit"
        adjusted_wwr = min(0.3, core_model.window_to_wall_ratio_base) # 减少开窗面积
        
    elif zone == ClimateZone.TROPICAL:
        # 高温高湿：需要遮阳和通风
        shading_type = "Perforated Metal Screens"
        u_value = 2.0   # 保温要求低，重点在散热
        shgc = 0.20
        material = "Bamboo-Composite / Breathable Cladding"
        
    elif zone == ClimateZone.POLAR or zone == ClimateZone.CONTINENTAL:
        # 寒冷：最大化得热，最小化热损失
        shading_type = "Minimal / Removable"
        u_value = 0.10  # 超级保温
        shgc = 0.60     # 允许太阳辐射进入
        material = "Triple Glazing / Insulated Metal Panels"
        adjusted_wwr = 0.5 # 增加开窗以获取光线和热量

    # 4. 动态计算遮阳角度 (基于太阳高度角)
    # 遮阳角度通常应阻挡正午高角度阳光（夏季）
    solar_altitude = calculate_solar_geometry_params(climate_data.latitude)
    
    # 简单几何逻辑：遮阳板倾角应能阻挡高度角为 solar_altitude 的光线
    # 这里使用经验公式：角度 = 90 - Solar Altitude + 修正值
    shading_angle = max(15, min(75, 90 - solar_altitude + 10))

    # 5. 边界检查
    if not (0 < u_value <= 5.0):
        logger.warning(f"Calculated U-Value {u_value} seems off, clamping.")
        u_value = max(0.05, min(5.0, u_value))

    return AdaptiveSkinParameters(
        shading_type=shading_type,
        shading_angle=round(shading_angle, 2),
        u_value=u_value,
        shgc=shgc,
        material_recommendation=material,
        window_ratio_adjusted=adjusted_wwr
    )


def run_design_simulation(climate_input: Dict) -> Dict:
    """
    主运行函数，模拟整个设计流程。
    
    Args:
        climate_input (Dict): 包含气候数据的字典
        
    Returns:
        Dict: 包含完整设计参数的字典
    """
    try:
        # 输入数据解析
        location = climate_input.get("location_name", "Unknown")
        c_data = ClimateData(
            avg_summer_temp=climate_input["summer_temp"],
            avg_winter_temp=climate_input["winter_temp"],
            humidity_avg=climate_input["humidity"],
            solar_radiation=climate_input.get("solar_rad", 800),
            latitude=climate_input["latitude"]
        )
        
        # 定义核心模型（假设这是一个标准化的办公楼产品）
        core = BuildingCoreModel(total_floor_area=5000)
        
        # 执行零样本适应
        skin_params = generate_adaptive_skin(core, c_data)
        
        # 格式化输出
        result = {
            "status": "success",
            "location": location,
            "detected_zone": _map_climate_zone(c_data).value,
            "design_parameters": vars(skin_params),
            "core_model_specs": vars(core)
        }
        return result

    except KeyError as e:
        logger.error(f"Missing input data: {e}")
        return {"status": "error", "message": f"Missing key: {e}"}
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        return {"status": "error", "message": "Internal simulation error"}


if __name__ == "__main__":
    # 使用示例
    
    # 场景1：迪拜（高温，干旱，低纬度）
    dubai_data = {
        "location_name": "Dubai",
        "summer_temp": 42.0,
        "winter_temp": 15.0,
        "humidity": 45.0,
        "solar_rad": 950.0,
        "latitude": 25.2
    }
    
    # 场景2：莫斯科（寒冷，大陆性，高纬度）
    moscow_data = {
        "location_name": "Moscow",
        "summer_temp": 23.0,
        "winter_temp": -10.0,
        "humidity": 70.0,
        "solar_rad": 400.0,
        "latitude": 55.7
    }
    
    print("--- 测试迪拜项目 ---")
    dubai_result = run_design_simulation(dubai_data)
    for k, v in dubai_result.items():
        print(f"{k}: {v}")
        
    print("\n--- 测试莫斯科项目 ---")
    moscow_result = run_design_simulation(moscow_data)
    for k, v in moscow_result.items():
        print(f"{k}: {v}")