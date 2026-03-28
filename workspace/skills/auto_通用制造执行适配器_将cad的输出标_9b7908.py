"""
通用制造执行适配器

该模块实现了将CAD系统的输出标准化为Platform Channel消息协议的功能。
支持将Flutter App设计的模型转换为设备可执行的指令序列。

典型使用流程:
1. Flutter App通过Manufacturing Channel发送设计模型
2. 适配器将模型转换为标准化的指令格式
3. 指令通过云端或边缘设备发送到具体制造设备
4. 设备驱动程序执行实际制造操作

输入格式:
- JSON格式的CAD模型数据
- 包含几何参数、材料属性、制造约束等信息

输出格式:
- 标准化的Platform Channel消息协议
- 包含操作码、参数、元数据等字段
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ManufacturingAdapter")


class ManufacturingOperation(Enum):
    """支持的制造操作类型枚举"""
    PRINT_3D = "print_3d"
    MILL_CNC = "mill_cnc"
    LASER_CUT = "laser_cut"
    DRILL = "drill"
    ASSEMBLE = "assemble"


@dataclass
class PlatformChannelMessage:
    """标准化的Platform Channel消息格式"""
    operation_id: str
    operation_type: ManufacturingOperation
    parameters: Dict[str, Union[float, str, List[float]]]
    metadata: Dict[str, str]
    timestamp: float


class CADModelValidator:
    """CAD模型验证器"""
    
    @staticmethod
    def validate_geometry(geometry: Dict) -> bool:
        """验证几何参数的有效性"""
        required_fields = ['dimensions', 'coordinates']
        for field in required_fields:
            if field not in geometry:
                logger.error(f"缺少必要几何字段: {field}")
                return False
                
        # 检查尺寸是否为正数
        for dim in ['x', 'y', 'z']:
            if dim in geometry['dimensions']:
                if geometry['dimensions'][dim] <= 0:
                    logger.error(f"无效尺寸值: {dim} = {geometry['dimensions'][dim]}")
                    return False
                    
        return True
    
    @staticmethod
    def validate_material(material: Dict) -> bool:
        """验证材料属性的有效性"""
        if 'type' not in material:
            logger.error("缺少材料类型字段")
            return False
            
        if material['type'] not in ['PLA', 'ABS', 'Metal', 'Wood']:
            logger.error(f"不支持的材料类型: {material['type']}")
            return False
            
        return True


class ManufacturingAdapter:
    """通用制造执行适配器主类"""
    
    def __init__(self):
        self.operation_counter = 0
        self._init_device_profiles()
        
    def _init_device_profiles(self):
        """初始化设备配置文件"""
        self.device_profiles = {
            '3d_printer': {
                'max_volume': [200, 200, 200],  # mm
                'supported_materials': ['PLA', 'ABS'],
                'resolution': 0.1
            },
            'cnc_machine': {
                'max_volume': [500, 500, 300],
                'supported_materials': ['Metal', 'Wood'],
                'resolution': 0.05
            }
        }
    
    def _generate_operation_id(self) -> str:
        """生成唯一操作ID"""
        self.operation_counter += 1
        return f"MFG-{int(time.time())}-{self.operation_counter}"
    
    def convert_cad_to_operations(
        self, 
        cad_data: Dict,
        device_type: str = '3d_printer'
    ) -> List[PlatformChannelMessage]:
        """
        将CAD模型数据转换为制造操作指令
        
        Args:
            cad_data: 包含CAD模型数据的字典
            device_type: 目标设备类型
            
        Returns:
            标准化制造操作指令列表
            
        Raises:
            ValueError: 如果输入数据无效或设备不支持
        """
        try:
            # 验证输入数据
            if not CADModelValidator.validate_geometry(cad_data.get('geometry', {})):
                raise ValueError("无效的几何参数")
                
            if not CADModelValidator.validate_material(cad_data.get('material', {})):
                raise ValueError("无效的材料参数")
                
            # 检查设备兼容性
            if device_type not in self.device_profiles:
                raise ValueError(f"不支持的设备类型: {device_type}")
                
            profile = self.device_profiles[device_type]
            
            # 检查材料兼容性
            if cad_data['material']['type'] not in profile['supported_materials']:
                raise ValueError(
                    f"材料 {cad_data['material']['type']} 不被设备 {device_type} 支持"
                )
                
            # 生成操作序列
            operations = []
            
            # 主制造操作
            main_op = self._create_main_operation(cad_data, device_type)
            operations.append(main_op)
            
            # 后处理操作
            if 'post_processing' in cad_data:
                post_ops = self._create_post_processing_operations(
                    cad_data['post_processing'],
                    device_type
                )
                operations.extend(post_ops)
                
            logger.info(f"成功转换CAD模型为 {len(operations)} 个操作指令")
            return operations
            
        except Exception as e:
            logger.error(f"转换CAD模型失败: {str(e)}")
            raise
    
    def _create_main_operation(
        self, 
        cad_data: Dict,
        device_type: str
    ) -> PlatformChannelMessage:
        """创建主制造操作"""
        operation_type = ManufacturingOperation.PRINT_3D
        if device_type == 'cnc_machine':
            operation_type = ManufacturingOperation.MILL_CNC
            
        params = {
            'geometry': cad_data['geometry'],
            'material': cad_data['material']['type'],
            'resolution': self.device_profiles[device_type]['resolution'],
            'speed': cad_data.get('manufacturing_params', {}).get('speed', 50)
        }
        
        metadata = {
            'source': 'flutter_app',
            'designer': cad_data.get('metadata', {}).get('designer', 'unknown'),
            'version': '1.0'
        }
        
        return PlatformChannelMessage(
            operation_id=self._generate_operation_id(),
            operation_type=operation_type,
            parameters=params,
            metadata=metadata,
            timestamp=time.time()
        )
    
    def _create_post_processing_operations(
        self,
        post_processing: List[Dict],
        device_type: str
    ) -> List[PlatformChannelMessage]:
        """创建后处理操作"""
        ops = []
        for step in post_processing:
            op_type = None
            params = {}
            
            if step['type'] == 'sanding':
                op_type = ManufacturingOperation.MILL_CNC
                params = {
                    'intensity': step.get('intensity', 0.5),
                    'area': step.get('area', 'all')
                }
            elif step['type'] == 'coating':
                op_type = ManufacturingOperation.PRINT_3D
                params = {
                    'material': step.get('coating_material', 'clear'),
                    'thickness': step.get('thickness', 0.1)
                }
                
            if op_type:
                ops.append(PlatformChannelMessage(
                    operation_id=self._generate_operation_id(),
                    operation_type=op_type,
                    parameters=params,
                    metadata={'stage': 'post_processing'},
                    timestamp=time.time()
                ))
                
        return ops
    
    def serialize_to_channel_format(
        self, 
        operations: List[PlatformChannelMessage]
    ) -> str:
        """
        将操作序列化为Platform Channel协议格式
        
        Args:
            operations: 制造操作列表
            
        Returns:
            JSON格式的标准化消息
        """
        try:
            serialized = []
            for op in operations:
                serialized.append({
                    'op_id': op.operation_id,
                    'op_type': op.operation_type.value,
                    'params': op.parameters,
                    'meta': op.metadata,
                    'ts': op.timestamp
                })
                
            channel_message = {
                'protocol_version': '1.0',
                'message_type': 'manufacturing_commands',
                'payload': serialized
            }
            
            logger.debug(f"序列化 {len(operations)} 个操作为Channel格式")
            return json.dumps(channel_message, indent=2)
            
        except Exception as e:
            logger.error(f"序列化操作失败: {str(e)}")
            raise


# 示例用法
if __name__ == "__main__":
    # 示例CAD数据
    sample_cad_data = {
        "geometry": {
            "dimensions": {"x": 100, "y": 100, "z": 50},
            "coordinates": [0, 0, 0],
            "shape": "cuboid"
        },
        "material": {
            "type": "PLA",
            "color": "blue",
            "density": 1.24
        },
        "manufacturing_params": {
            "speed": 60,
            "infill": 20
        },
        "post_processing": [
            {
                "type": "sanding",
                "intensity": 0.7,
                "area": "top"
            }
        ],
        "metadata": {
            "designer": "user_123",
            "project": "prototype_v1"
        }
    }
    
    # 创建适配器实例
    adapter = ManufacturingAdapter()
    
    try:
        # 转换CAD模型为操作指令
        operations = adapter.convert_cad_to_operations(
            sample_cad_data,
            device_type='3d_printer'
        )
        
        # 序列化为Channel协议格式
        channel_message = adapter.serialize_to_channel_format(operations)
        
        print("转换成功! Platform Channel消息:")
        print(channel_message)
        
    except ValueError as e:
        print(f"转换失败: {str(e)}")