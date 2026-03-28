"""
模块名称: neural_architectural_assembler
功能描述: 实现'神经常规建筑组合器'，通过预训练的模块化组件快速组装建筑方案。
版本: 1.0.0
作者: AGI System
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModuleCategory(Enum):
    """建筑模块分类枚举"""
    CORE = "core"               # 核心筒（电梯、楼梯）
    OFFICE = "office"           # 办公空间
    RESIDENTIAL = "residential" # 居住空间
    SANITARY = "sanitary"       # 卫生间/管道井
    LOBBY = "lobby"             # 大堂
    UTILITY = "utility"         # 设备间
    PARKING = "parking"         # 停车场

@dataclass
class GridPosition:
    """网格位置定义"""
    x: int
    y: int
    z: int  # 楼层
    
    def distance_to(self, other: 'GridPosition') -> float:
        """计算到另一个位置的欧几里得距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

@dataclass
class ModuleInterface:
    """模块接口定义：定义管线和动线连接点"""
    name: str
    position_offset: Tuple[float, float, float]  # 相对于模块原点的偏移
    interface_type: str  # 'water', 'electric', 'hvac', 'traffic'
    direction: str       # 'north', 'south', 'east', 'west', 'up', 'down'
    is_connected: bool = False

@dataclass
class NeuralModule:
    """
    神经建筑模块：预训练的建筑功能单元。
    类似于编程中的函数，具有明确的输入（入口）和输出（出口/管线）。
    """
    module_id: str
    category: ModuleCategory
    dimensions: Tuple[int, int, int]  # (width, depth, height) in grid units
    interfaces: List[ModuleInterface]
    performance_score: float = 0.0  # 预训练的性能评分 (0.0 - 1.0)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.performance_score <= 1.0:
            raise ValueError(f"Performance score must be between 0 and 1, got {self.performance_score}")
        if any(d <= 0 for d in self.dimensions):
            raise ValueError("Dimensions must be positive integers")

class NeuralModuleLibrary:
    """
    神经模块库：存储和管理预训练的建筑模块。
    """
    
    def __init__(self):
        self._library: Dict[str, NeuralModule] = {}
        self._load_default_modules()
        logger.info("Neural Module Library initialized with default modules.")
    
    def _load_default_modules(self) -> None:
        """加载基础模块库"""
        # 卫生间模块
        sanitary_module = NeuralModule(
            module_id="SANITARY_STD_V1",
            category=ModuleCategory.SANITARY,
            dimensions=(4, 6, 1),
            interfaces=[
                ModuleInterface("water_in", (0, 1, 0.5), "water", "west"),
                ModuleInterface("drain_out", (0, 4, 0.2), "water", "west"),
                ModuleInterface("door", (2, 0, 0.5), "traffic", "south")
            ],
            performance_score=0.92,
            metadata={"capacity": 20, "fixtures": ["wc", "sink", "urinal"]}
        )
        
        # 办公核心模块
        office_module = NeuralModule(
            module_id="OFFICE_OPEN_V1",
            category=ModuleCategory.OFFICE,
            dimensions=(12, 12, 1),
            interfaces=[
                ModuleInterface("main_entrance", (6, 0, 0.5), "traffic", "south"),
                ModuleInterface("fire_exit", (12, 6, 0.5), "traffic", "east"),
                ModuleInterface("hvac_intake", (0, 6, 0.8), "hvac", "west"),
                ModuleInterface("power_in", (0, 0, 0.3), "electric", "west")
            ],
            performance_score=0.88,
            metadata={"max_occupancy": 50, "area_sqm": 144}
        )
        
        # 核心筒模块
        core_module = NeuralModule(
            module_id="CORE_ELEVATOR_V1",
            category=ModuleCategory.CORE,
            dimensions=(8, 8, 1),
            interfaces=[
                ModuleInterface("lobby_access_n", (4, 0, 0.5), "traffic", "south"),
                ModuleInterface("lobby_access_s", (4, 8, 0.5), "traffic", "north"),
                ModuleInterface("lobby_access_e", (8, 4, 0.5), "traffic", "east"),
                ModuleInterface("lobby_access_w", (0, 4, 0.5), "traffic", "west"),
                ModuleInterface("power_main", (2, 2, 0.2), "electric", "down"),
                ModuleInterface("hvac_shaft", (6, 6, 0.9), "hvac", "up")
            ],
            performance_score=0.95,
            metadata={"elevator_count": 4, "stair_count": 2}
        )
        
        self.add_module(sanitary_module)
        self.add_module(office_module)
        self.add_module(core_module)

    def add_module(self, module: NeuralModule) -> None:
        """添加模块到库中"""
        if module.module_id in self._library:
            logger.warning(f"Overwriting existing module: {module.module_id}")
        self._library[module.module_id] = module
        logger.debug(f"Module {module.module_id} added to library.")

    def get_module(self, module_id: str) -> Optional[NeuralModule]:
        """获取模块"""
        return self._library.get(module_id)

class BuildingAssembler:
    """
    建筑组装器：负责将模块放置在网格中，并自动处理接口连接。
    核心功能：碰撞检测、自动对齐、管线自动连接。
    """
    
    def __init__(self, grid_size: Tuple[int, int, int] = (100, 100, 50)):
        """
        初始化组装器。
        
        Args:
            grid_size: 建筑网格的总大小 (X, Y, Z)
        """
        self.grid_size = grid_size
        self.occupied_grids: Dict[Tuple[int, int, int], str] = {} # 网格坐标 -> 模块ID
        self.placed_modules: Dict[str, Tuple[NeuralModule, GridPosition]] = {} # 模块ID -> (模块实例, 位置)
        self.module_library = NeuralModuleLibrary()
        logger.info(f"Building Assembler initialized with grid size {grid_size}")

    def _check_bounds(self, position: GridPosition, dimensions: Tuple[int, int, int]) -> bool:
        """检查模块是否在网格边界内"""
        if not (0 <= position.x < self.grid_size[0] and \
                0 <= position.y < self.grid_size[1] and \
                0 <= position.z < self.grid_size[2]):
            return False
        
        end_x = position.x + dimensions[0]
        end_y = position.y + dimensions[1]
        end_z = position.z + dimensions[2]
        
        return end_x <= self.grid_size[0] and end_y <= self.grid_size[1] and end_z <= self.grid_size[2]

    def _check_collision(self, position: GridPosition, dimensions: Tuple[int, int, int], exclude_module_id: Optional[str] = None) -> bool:
        """
        检查指定位置是否与现有模块碰撞。
        返回 True 表示发生碰撞，False 表示空间可用。
        """
        for x in range(position.x, position.x + dimensions[0]):
            for y in range(position.y, position.y + dimensions[1]):
                # 简化：假设模块高度占满一层，或者需要更精细的体素检查
                # 这里仅检查二维投影的占地面积，Z轴作为层级约束
                # 在实际AGI系统中，这里应该是三维体素碰撞检测
                coord = (x, y, position.z)
                if coord in self.occupied_grids:
                    if self.occupied_grids[coord] != exclude_module_id:
                        return True
        return False

    def place_module(self, module_id: str, position: GridPosition, auto_connect: bool = True) -> bool:
        """
        在指定位置放置模块。
        
        Args:
            module_id: 模块库中的ID
            position: 目标网格位置
            auto_connect: 是否自动尝试连接相邻接口
        
        Returns:
            bool: 放置是否成功
        """
        logger.info(f"Attempting to place module {module_id} at {position}")
        
        module = self.module_library.get_module(module_id)
        if not module:
            logger.error(f"Module {module_id} not found in library.")
            return False
            
        # 1. 边界检查
        if not self._check_bounds(position, module.dimensions):
            logger.error(f"Placement out of bounds for module {module_id} at {position}")
            return False
            
        # 2. 碰撞检查
        if self._check_collision(position, module.dimensions):
            logger.error(f"Collision detected for module {module_id} at {position}")
            return False
            
        # 3. 占用空间 (简化：标记二维区域)
        # 实际应记录三维体素
        for x in range(position.x, position.x + module.dimensions[0]):
            for y in range(position.y, position.y + module.dimensions[1]):
                self.occupied_grids[(x, y, position.z)] = module_id
        
        # 记录放置信息
        instance_id = f"{module_id}_{len(self.placed_modules)}"
        self.placed_modules[instance_id] = (module, position)
        
        # 4. 自动连接处理
        if auto_connect:
            self._resolve_interfaces(module, position)
            
        logger.info(f"Successfully placed {instance_id}")
        return True

    def _resolve_interfaces(self, current_module: NeuralModule, current_pos: GridPosition) -> None:
        """
        辅助函数：解析并尝试连接模块接口。
        检查相邻网格是否有兼容的接口（类型匹配、方向相对）。
        """
        logger.debug(f"Resolving interfaces for {current_module.module_id} at {current_pos}")
        
        for iface in current_module.interfaces:
            # 计算接口在全局网格中的绝对位置
            abs_x = current_pos.x + iface.position_offset[0]
            abs_y = current_pos.y + iface.position_offset[1]
            
            # 根据方向确定邻居检查坐标
            neighbor_coord = None
            required_dir = None
            
            if iface.direction == 'north':
                neighbor_coord = (abs_x, abs_y + 1, current_pos.z)
                required_dir = 'south'
            elif iface.direction == 'south':
                neighbor_coord = (abs_x, abs_y - 1, current_pos.z)
                required_dir = 'north'
            elif iface.direction == 'east':
                neighbor_coord = (abs_x + 1, abs_y, current_pos.z)
                required_dir = 'west'
            elif iface.direction == 'west':
                neighbor_coord = (abs_x - 1, abs_y, current_pos.z)
                required_dir = 'east'
            
            if neighbor_coord and neighbor_coord in self.occupied_grids:
                neighbor_mod_id = self.occupied_grids[neighbor_coord]
                # 查找邻居模块的具体实例（这里简化处理，直接取库定义）
                # 实际中需要通过 instance_id 获取 placed_modules 中的具体对象
                neighbor_mod = self.module_library.get_module(neighbor_mod_id.split('_')[0]) # 简化
                
                if neighbor_mod:
                    # 检查是否有匹配的接口
                    for n_iface in neighbor_mod.interfaces:
                        if n_iface.interface_type == iface.interface_type and n_iface.direction == required_dir:
                            # 连接成功
                            iface.is_connected = True
                            logger.info(f"Interface connected: {current_module.module_id}.{iface.name} <--> {neighbor_mod.module_id}.{n_iface.name} ({iface.interface_type})")
                            break

    def generate_blueprint_report(self) -> Dict:
        """
        生成当前组装状态的蓝图报告。
        
        Returns:
            Dict: 包含统计信息和布局数据的字典
        """
        total_score = 0.0
        module_counts = {}
        
        for instance_id, (module, pos) in self.placed_modules.items():
            total_score += module.performance_score
            cat = module.category.value
            module_counts[cat] = module_counts.get(cat, 0) + 1
            
        avg_score = total_score / len(self.placed_modules) if self.placed_modules else 0.0
        
        report = {
            "grid_size": self.grid_size,
            "total_modules": len(self.placed_modules),
            "category_breakdown": module_counts,
            "average_performance_score": round(avg_score, 3),
            "layout_coordinates": [
                {
                    "module_id": mod.module_id,
                    "position": (pos.x, pos.y, pos.z),
                    "dimensions": mod.dimensions
                } for mod, pos in self.placed_modules.values()
            ]
        }
        return report

# 使用示例
if __name__ == "__main__":
    # 1. 初始化组装器
    assembler = BuildingAssembler(grid_size=(50, 50, 10))
    
    # 2. 放置核心筒 (放在中心)
    core_pos = GridPosition(20, 20, 0)
    assembler.place_module("CORE_ELEVATOR_V1", core_pos)
    
    # 3. 放置办公模块 (围绕核心筒)
    # 南侧办公
    office_pos_south = GridPosition(20, 8, 0) # y < 20
    assembler.place_module("OFFICE_OPEN_V1", office_pos_south)
    
    # 4. 放置卫生间 (通常在核心筒附近或角落)
    sanitary_pos = GridPosition(28, 20, 0) # 紧邻核心筒东侧
    assembler.place_module("SANITARY_STD_V1", sanitary_pos)
    
    # 5. 尝试放置冲突模块 (应该失败)
    conflict_pos = GridPosition(20, 20, 0)
    print("\nAttempting collision test...")
    success = assembler.place_module("OFFICE_OPEN_V1", conflict_pos)
    assert not success, "Collision detection failed!"
    
    # 6. 生成报告
    print("\nGenerating Blueprint Report...")
    report = assembler.generate_blueprint_report()
    print(json.dumps(report, indent=2))