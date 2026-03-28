"""
模块名称: intelligent_metabolic_pipeline
版本: 1.0.0
描述: 实现'智能代谢流管道'，模拟生物酶促反应的去中心化工业调控系统。
      该系统利用边缘计算节点（模拟酶）实时压缩环境数据熵，
      实现基于局部最优的变构调节，无需中心化指令。
作者: AGI System
"""

import logging
import time
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态枚举"""
    IDLE = "idle"
    ACTIVE = "active"
    CATALYZING = "catalyzing"
    ERROR = "error"

@dataclass
class EnvironmentalContext:
    """环境上下文数据结构"""
    temperature: float  # 温度 (摄氏度)
    humidity: float     # 湿度 (%)
    worker_fatigue: float  # 工人疲劳度 (0.0-1.0)
    material_quality: float  # 物料质量系数 (0.0-1.0)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """数据验证"""
        if not (0 <= self.humidity <= 100):
            raise ValueError("湿度必须在0-100之间")
        if not (0 <= self.worker_fatigue <= 1.0):
            raise ValueError("工人疲劳度必须在0.0-1.0之间")
        if not (-50 <= self.temperature <= 200):
            raise ValueError("温度超出合理范围")

@dataclass
class NodeParameter:
    """节点参数数据结构"""
    speed: float = 1.0       # 运转速度系数
    intensity: float = 1.0   # 强度系数
    cooling: float = 0.5     # 冷却系数

class AllostericModel:
    """
    小型边缘计算模型（模拟酶的变构调节能力）
    用于实时处理环境数据并生成调控参数
    """
    
    @staticmethod
    def _sigmoid(x: float, k: float = 1.0, center: float = 0.5) -> float:
        """Sigmoid激活函数，用于平滑过渡"""
        try:
            return 1 / (1 + pow(2.71828, -k * (x - center)))
        except OverflowError:
            return 0.0 if x < center else 1.0

    def catalyze_entropy(self, context: EnvironmentalContext) -> NodeParameter:
        """
        核心功能：压缩信息熵，计算局部最优参数
        输入: 高维环境上下文
        输出: 低维控制参数
        """
        logger.debug(f"开始催化环境数据: Temp={context.temperature}, Hum={context.humidity}")
        
        # 模拟信息熵压缩：将多个环境因子映射为少量的控制参数
        # 这里使用简化的启发式算法模拟小型神经网络的推理过程
        
        # 温度影响：温度过高需要降速并增强冷却
        temp_factor = self._sigmoid(context.temperature, k=0.1, center=35)
        speed_adj = 1.0 - (temp_factor * 0.5)
        cooling_adj = 0.5 + (temp_factor * 0.5)
        
        # 工人状态影响：疲劳度高时降低强度
        fatigue_penalty = 1.0 - context.worker_fatigue * 0.7
        
        # 物料质量影响：质量差时需要降速保良品率
        quality_factor = 0.5 + (context.material_quality * 0.5)
        
        final_speed = max(0.1, speed_adj * fatigue_penalty * quality_factor)
        final_intensity = max(0.1, fatigue_penalty)
        
        return NodeParameter(
            speed=round(final_speed, 3),
            intensity=round(final_intensity, 3),
            cooling=round(min(1.0, cooling_adj), 3)
        )

class EnzymeNode:
    """
    智能节点类（模拟生物酶）
    具备状态感知、数据处理和动作执行能力
    """
    
    def __init__(self, node_id: str, capability: str):
        self.node_id = node_id
        self.capability = capability
        self.status = NodeStatus.IDLE
        self.model = AllostericModel()
        self.current_params = NodeParameter()
        self.error_count = 0
        
    def _validate_input(self, raw_data: Dict[str, Any]) -> EnvironmentalContext:
        """辅助函数：验证并转换输入数据"""
        required_fields = ['temperature', 'humidity', 'worker_fatigue', 'material_quality']
        
        if not isinstance(raw_data, dict):
            raise TypeError("输入数据必须是字典类型")
            
        missing = [field for field in required_fields if field not in raw_data]
        if missing:
            raise ValueError(f"缺少必要字段: {missing}")
            
        return EnvironmentalContext(
            temperature=float(raw_data['temperature']),
            humidity=float(raw_data['humidity']),
            worker_fatigue=float(raw_data['worker_fatigue']),
            material_quality=float(raw_data['material_quality'])
        )

    def execute_catalysis(self, sensor_data: Dict[str, Any]) -> Optional[NodeParameter]:
        """
        核心功能：执行催化工作流
        1. 感知环境
        2. 催化处理 (Model)
        3. 变构调节
        """
        self.status = NodeStatus.ACTIVE
        logger.info(f"节点 {self.node_id} 开始处理流转...")
        
        try:
            # 1. 数据验证与转换
            context = self._validate_input(sensor_data)
            
            # 2. 智能催化 (降低认知负荷/熵)
            self.status = NodeStatus.CATALYZING
            new_params = self.model.catalyze_entropy(context)
            
            # 3. 应用变构调节
            self._apply_allosteric_change(new_params)
            
            self.status = NodeStatus.IDLE
            self.error_count = 0
            return self.current_params
            
        except Exception as e:
            self.status = NodeStatus.ERROR
            self.error_count += 1
            logger.error(f"节点 {self.node_id} 催化失败: {str(e)}")
            return None

    def _apply_allosteric_change(self, new_params: NodeParameter):
        """应用新的参数配置（模拟蛋白质构象改变）"""
        # 边界检查
        if not (0 < new_params.speed <= 2.0):
            logger.warning(f"异常速度参数检测: {new_params.speed}，已限制")
            new_params.speed = max(0.1, min(1.5, new_params.speed))
            
        self.current_params = new_params
        logger.info(f"节点 {self.node_id} 变构调节完成: Speed={new_params.speed}, Intensity={new_params.intensity}")

class MetabolicPipeline:
    """
    代谢流管道管理器
    模拟去中心化的生物代谢网络
    """
    
    def __init__(self):
        self.nodes: Dict[str, EnzymeNode] = {}
        logger.info("智能代谢流管道初始化完成")
        
    def register_node(self, node: EnzymeNode):
        """注册节点到代谢网络"""
        if node.node_id in self.nodes:
            logger.warning(f"节点 {node.node_id} 已存在，将被覆盖")
        self.nodes[node.node_id] = node
        
    def flow(self, data_stream: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理完整的数据流转
        数据依次流经各个节点进行代谢处理
        """
        results = []
        logger.info(f"开始处理数据流，共 {len(data_stream)} 个包")
        
        for data_packet in data_stream:
            # 在真实场景中，数据会根据路由流向特定节点
            # 这里模拟所有节点对环境做出的群体反应
            packet_result = {
                'timestamp': time.time(),
                'node_adjustments': {}
            }
            
            for node_id, node in self.nodes.items():
                params = node.execute_catalysis(data_packet)
                if params:
                    packet_result['node_adjustments'][node_id] = params.__dict__
            
            results.append(packet_result)
            
        return results

# 使用示例
if __name__ == "__main__":
    # 1. 初始化管道
    pipeline = MetabolicPipeline()
    
    # 2. 创建酶节点（工作单元）
    node_assembly = EnzymeNode(node_id="ASM-01", capability="assembly")
    node_qc = EnzymeNode(node_id="QC-02", capability="quality_check")
    
    # 3. 注册节点
    pipeline.register_node(node_assembly)
    pipeline.register_node(node_qc)
    
    # 4. 模拟实时环境数据流
    # 模拟工厂环境：温度波动，湿度正常，工人疲劳度上升
    mock_stream = []
    for i in range(3):
        mock_stream.append({
            'temperature': 25 + random.uniform(-2, 5) + i, # 温度逐渐升高
            'humidity': 45.0,
            'worker_fatigue': 0.1 + (i * 0.3), # 疲劳度增加
            'material_quality': 0.9
        })
    
    # 5. 运行管道
    print("\n--- 开始智能代谢流处理 ---")
    flow_results = pipeline.flow(mock_stream)
    
    for idx, res in enumerate(flow_results):
        print(f"\nTime Step {idx+1}:")
        for node_id, params in res['node_adjustments'].items():
            print(f"  Node {node_id} adjusted -> Speed: {params['speed']}, Cooling: {params['cooling']}")