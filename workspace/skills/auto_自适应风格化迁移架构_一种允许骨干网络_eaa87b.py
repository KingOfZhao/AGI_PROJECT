"""
自适应风格化迁移架构

一种允许骨干网络保持高泛化能力（结构安全），同时根据输入数据动态生成'表皮'网络参数的机制。
不同于传统的Fine-tuning，这里引入'参数表皮层'，根据上下文（如时间、地点、用户画像）像更换幕墙一样实时置换网络的前端处理逻辑，而无需重新训练核心骨干。实现'一处骨架，千面表皮'的动态部署。

核心组件:
1. BackboneNetwork: 骨干网络，保持高泛化能力
2. SkinGenerator: 表皮生成器，根据上下文动态生成参数
3. AdaptiveStyleTransfer: 主架构类，协调整个迁移过程
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContextType(Enum):
    """上下文类型枚举"""
    TEMPORAL = "temporal"       # 时间相关
    SPATIAL = "spatial"         # 地点相关
    USER_PROFILE = "user_profile"  # 用户画像
    ENVIRONMENT = "environment"    # 环境因素


@dataclass
class ContextFeature:
    """上下文特征数据结构"""
    feature_type: ContextType
    value: Union[str, float, Dict]
    weight: float = 1.0
    timestamp: float = time.time()


class BackboneNetwork:
    """
    骨干网络类
    
    保持核心处理逻辑和高泛化能力，不随上下文变化而改变
    
    Attributes:
        weights (np.ndarray): 网络权重
        bias (np.ndarray): 网络偏置
        architecture (str): 网络架构描述
    """
    
    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        """
        初始化骨干网络
        
        Args:
            input_size: 输入维度
            hidden_size: 隐藏层维度
            output_size: 输出维度
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # 初始化网络参数
        self.weights = {
            'W1': np.random.randn(input_size, hidden_size) * 0.01,
            'b1': np.zeros(hidden_size),
            'W2': np.random.randn(hidden_size, output_size) * 0.01,
            'b2': np.zeros(output_size)
        }
        
        self.architecture = f"Backbone({input_size}-{hidden_size}-{output_size})"
        logger.info(f"初始化骨干网络: {self.architecture}")
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        前向传播
        
        Args:
            x: 输入数据
            
        Returns:
            输出结果
        """
        # 第一层
        z1 = np.dot(x, self.weights['W1']) + self.weights['b1']
        a1 = np.maximum(0, z1)  # ReLU激活
        
        # 第二层
        z2 = np.dot(a1, self.weights['W2']) + self.weights['b2']
        
        return z2
    
    def get_core_parameters(self) -> Dict[str, np.ndarray]:
        """获取核心参数"""
        return self.weights.copy()


class SkinGenerator:
    """
    表皮生成器
    
    根据上下文动态生成表皮网络参数
    
    Attributes:
        context_embeddings (Dict): 上下文嵌入向量
        parameter_templates (Dict): 参数模板
    """
    
    def __init__(self, context_dim: int = 128):
        """
        初始化表皮生成器
        
        Args:
            context_dim: 上下文嵌入维度
        """
        self.context_dim = context_dim
        self.context_embeddings: Dict[str, np.ndarray] = {}
        self.parameter_templates: Dict[str, Dict] = {}
        
        logger.info(f"初始化表皮生成器，上下文维度: {context_dim}")
    
    def encode_context(self, context_features: List[ContextFeature]) -> np.ndarray:
        """
        编码上下文特征为向量
        
        Args:
            context_features: 上下文特征列表
            
        Returns:
            上下文嵌入向量
        """
        context_vector = np.zeros(self.context_dim)
        total_weight = 0.0
        
        for feature in context_features:
            # 为每个特征生成唯一标识
            feature_id = f"{feature.feature_type.value}_{feature.value}"
            
            # 如果没有缓存，则生成新的嵌入
            if feature_id not in self.context_embeddings:
                # 使用哈希函数生成伪随机但确定性的嵌入
                hash_obj = hashlib.md5(feature_id.encode())
                hash_int = int(hash_obj.hexdigest(), 16)
                np.random.seed(hash_int % (2**32))
                self.context_embeddings[feature_id] = np.random.randn(self.context_dim) * 0.1
            
            # 加权聚合
            context_vector += self.context_embeddings[feature_id] * feature.weight
            total_weight += feature.weight
        
        if total_weight > 0:
            context_vector /= total_weight
        
        return context_vector
    
    def generate_skin_parameters(
        self,
        context_vector: np.ndarray,
        backbone: BackboneNetwork
    ) -> Dict[str, np.ndarray]:
        """
        生成表皮参数
        
        Args:
            context_vector: 上下文向量
            backbone: 骨干网络
            
        Returns:
            表皮参数字典
        """
        # 生成表皮参数 (这里使用简单的线性变换作为示例)
        skin_params = {}
        
        # 为输入层生成变换矩阵
        skin_params['input_transform'] = np.random.randn(
            backbone.input_size, 
            backbone.input_size
        ) * 0.01 + np.eye(backbone.input_size) * 0.1
        
        # 为输出层生成缩放因子
        skin_params['output_scale'] = np.ones(backbone.output_size) + np.random.randn(
            backbone.output_size
        ) * 0.05
        
        # 生成风格化偏置
        skin_params['style_bias'] = np.random.randn(backbone.hidden_size) * 0.02
        
        logger.debug("生成表皮参数完成")
        return skin_params
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """获取参数模板"""
        return self.parameter_templates.get(template_name)


class AdaptiveStyleTransfer:
    """
    自适应风格化迁移架构主类
    
    整合骨干网络和表皮生成器，实现动态风格迁移
    
    Attributes:
        backbone (BackboneNetwork): 骨干网络
        skin_generator (SkinGenerator): 表皮生成器
        current_skin (Dict): 当前表皮参数
        context_history (List): 上下文历史记录
    """
    
    def __init__(
        self,
        input_size: int = 256,
        hidden_size: int = 512,
        output_size: int = 128,
        context_dim: int = 128
    ):
        """
        初始化自适应风格迁移架构
        
        Args:
            input_size: 输入维度
            hidden_size: 隐藏层维度
            output_size: 输出维度
            context_dim: 上下文维度
        """
        # 初始化骨干网络
        self.backbone = BackboneNetwork(input_size, hidden_size, output_size)
        
        # 初始化表皮生成器
        self.skin_generator = SkinGenerator(context_dim)
        
        # 当前表皮参数
        self.current_skin: Dict[str, np.ndarray] = {}
        
        # 上下文历史记录
        self.context_history: List[Tuple[datetime, np.ndarray]] = []
        
        logger.info("自适应风格化迁移架构初始化完成")
    
    def process(
        self,
        input_data: np.ndarray,
        context_features: List[ContextFeature],
        update_skin: bool = True
    ) -> np.ndarray:
        """
        处理输入数据，根据上下文动态应用风格
        
        Args:
            input_data: 输入数据
            context_features: 上下文特征列表
            update_skin: 是否更新表皮参数
            
        Returns:
            处理后的输出
            
        Raises:
            ValueError: 输入数据维度不匹配
        """
        # 数据验证
        if input_data.ndim == 1:
            input_data = input_data.reshape(1, -1)
        
        if input_data.shape[1] != self.backbone.input_size:
            error_msg = f"输入维度不匹配: 期望 {self.backbone.input_size}, 得到 {input_data.shape[1]}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 编码上下文
        context_vector = self.skin_generator.encode_context(context_features)
        
        # 记录上下文历史
        self.context_history.append((datetime.now(), context_vector))
        
        # 生成或更新表皮参数
        if update_skin or not self.current_skin:
            self.current_skin = self.skin_generator.generate_skin_parameters(
                context_vector,
                self.backbone
            )
            logger.info("表皮参数已更新")
        
        # 应用表皮变换
        transformed_input = self._apply_input_transform(input_data)
        
        # 骨干网络前向传播
        backbone_output = self.backbone.forward(transformed_input)
        
        # 应用输出变换
        final_output = self._apply_output_transform(backbone_output)
        
        return final_output
    
    def _apply_input_transform(self, x: np.ndarray) -> np.ndarray:
        """
        应用输入变换
        
        Args:
            x: 输入数据
            
        Returns:
            变换后的输入
        """
        if 'input_transform' in self.current_skin:
            return np.dot(x, self.current_skin['input_transform'])
        return x
    
    def _apply_output_transform(self, x: np.ndarray) -> np.ndarray:
        """
        应用输出变换
        
        Args:
            x: 骨干网络输出
            
        Returns:
            最终输出
        """
        if 'output_scale' in self.current_skin:
            return x * self.current_skin['output_scale']
        return x
    
    def get_current_skin_info(self) -> Dict:
        """获取当前表皮信息"""
        info = {
            'has_skin': bool(self.current_skin),
            'skin_keys': list(self.current_skin.keys()),
            'context_history_length': len(self.context_history)
        }
        
        if self.current_skin:
            info['parameter_shapes'] = {
                k: v.shape for k, v in self.current_skin.items()
            }
        
        return info
    
    def reset_skin(self) -> None:
        """重置表皮参数"""
        self.current_skin = {}
        logger.info("表皮参数已重置")
    
    def export_skin(self) -> Optional[Dict[str, List]]:
        """导出当前表皮参数"""
        if not self.current_skin:
            return None
        
        return {
            k: v.tolist() for k, v in self.current_skin.items()
        }
    
    def import_skin(self, skin_data: Dict[str, List]) -> None:
        """
        导入表皮参数
        
        Args:
            skin_data: 表皮参数字典
        """
        self.current_skin = {
            k: np.array(v) for k, v in skin_data.items()
        }
        logger.info("表皮参数已导入")


def create_context_features(
    temporal_info: Optional[str] = None,
    spatial_info: Optional[str] = None,
    user_profile: Optional[Dict] = None
) -> List[ContextFeature]:
    """
    辅助函数: 创建上下文特征列表
    
    Args:
        temporal_info: 时间信息 (如 "morning", "evening")
        spatial_info: 地点信息 (如 "office", "home")
        user_profile: 用户画像字典
        
    Returns:
        上下文特征列表
        
    Example:
        >>> features = create_context_features(
        ...     temporal_info="morning",
        ...     spatial_info="office",
        ...     user_profile={"age": 30, "preference": "tech"}
        ... )
    """
    features = []
    
    if temporal_info:
        features.append(ContextFeature(
            feature_type=ContextType.TEMPORAL,
            value=temporal_info,
            weight=1.0
        ))
    
    if spatial_info:
        features.append(ContextFeature(
            feature_type=ContextType.SPATIAL,
            value=spatial_info,
            weight=0.8
        ))
    
    if user_profile:
        features.append(ContextFeature(
            feature_type=ContextType.USER_PROFILE,
            value=user_profile,
            weight=1.2
        ))
    
    return features


# 使用示例
if __name__ == "__main__":
    # 创建自适应风格迁移架构
    model = AdaptiveStyleTransfer(
        input_size=64,
        hidden_size=128,
        output_size=32
    )
    
    # 创建示例输入数据
    sample_input = np.random.randn(10, 64)
    
    # 创建上下文特征
    context = create_context_features(
        temporal_info="morning",
        spatial_info="office",
        user_profile={"age": 30, "interest": "technology"}
    )
    
    # 处理数据
    output = model.process(sample_input, context)
    print(f"输出形状: {output.shape}")
    
    # 获取当前表皮信息
    skin_info = model.get_current_skin_info()
    print(f"表皮信息: {skin_info}")
    
    # 导出/导入表皮参数
    exported_skin = model.export_skin()
    print(f"导出的表皮参数键: {list(exported_skin.keys())}")