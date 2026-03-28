"""
高级Python模块：语义驱动的API反向探索代理

该模块实现了一个能够理解模糊用户意图（如'温和一点'、'激进一点'）
并将其映射到未知API具体参数值的智能代理。通过构建API语义向量空间，
代理能够像人类一样"阅读说明书并联想应用"。

核心功能：
1. 解析API文档并构建功能向量空间
2. 将自然语言用户意图投影到向量空间
3. 提取最近的参数节点并智能赋值

作者: AGI系统
版本: 1.0.0
"""

import logging
import json
import math
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """API参数类型枚举"""
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"


@dataclass
class APIParameter:
    """API参数数据结构"""
    name: str
    description: str
    param_type: ParameterType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[List[str]] = None
    default_value: Optional[Union[float, bool, str]] = None
    semantic_tags: List[str] = None  # 语义标签（如'gentle', 'aggressive'）

    def __post_init__(self):
        if self.semantic_tags is None:
            self.semantic_tags = []


@dataclass
class APIEndpoint:
    """API端点数据结构"""
    name: str
    description: str
    parameters: Dict[str, APIParameter]
    category: str


class SemanticSpace:
    """语义向量空间模型"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.parameter_vectors = {}
        self.parameter_metadata = {}
        self._is_fitted = False
    
    def build_space(self, endpoints: Dict[str, APIEndpoint]) -> None:
        """
        构建API参数的语义向量空间
        
        参数:
            endpoints: API端点字典，key为端点名，value为APIEndpoint对象
            
        异常:
            ValueError: 当输入数据为空或无效时抛出
        """
        if not endpoints:
            raise ValueError("API端点数据不能为空")
        
        logger.info("开始构建语义向量空间...")
        
        # 收集所有参数的描述文本用于训练
        corpus = []
        param_info = []
        
        for endpoint_name, endpoint in endpoints.items():
            for param_name, param in endpoint.parameters.items():
                # 构建参数的完整描述文本
                full_desc = f"{param.description} {' '.join(param.semantic_tags)}"
                corpus.append(full_desc)
                param_info.append({
                    'endpoint': endpoint_name,
                    'param': param_name,
                    'metadata': param
                })
        
        if not corpus:
            raise ValueError("没有有效的参数描述可用于构建向量空间")
        
        # 训练TF-IDF向量化器
        try:
            self.vectorizer.fit(corpus)
            vectors = self.vectorizer.transform(corpus)
            
            # 存储参数向量和元数据
            for i, info in enumerate(param_info):
                key = f"{info['endpoint']}.{info['param']}"
                self.parameter_vectors[key] = vectors[i]
                self.parameter_metadata[key] = info['metadata']
            
            self._is_fitted = True
            logger.info(f"语义向量空间构建完成，包含{len(self.parameter_vectors)}个参数")
            
        except Exception as e:
            logger.error(f"构建向量空间失败: {str(e)}")
            raise RuntimeError(f"向量空间构建失败: {str(e)}")
    
    def project_intent(self, intent_text: str, top_n: int = 3) -> List[Tuple[str, float, APIParameter]]:
        """
        将用户意图投影到语义空间并找到最相关的参数
        
        参数:
            intent_text: 用户的自然语言意图描述
            top_n: 返回的最相关参数数量
            
        返回:
            包含(参数key, 相似度分数, 参数元数据)的元组列表
            
        异常:
            RuntimeError: 当向量空间未构建时抛出
        """
        if not self._is_fitted:
            raise RuntimeError("语义空间未构建，请先调用build_space方法")
        
        if not intent_text or not isinstance(intent_text, str):
            raise ValueError("意图文本必须是非空字符串")
        
        logger.info(f"投影用户意图: '{intent_text}'")
        
        try:
            # 将用户意图转换为向量
            intent_vector = self.vectorizer.transform([intent_text])
            
            # 计算与所有参数的相似度
            similarities = {}
            for key, param_vector in self.parameter_vectors.items():
                similarity = cosine_similarity(intent_vector, param_vector)[0][0]
                similarities[key] = similarity
            
            # 按相似度排序并返回top_n个结果
            sorted_params = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            results = []
            for key, score in sorted_params:
                results.append((key, score, self.parameter_metadata[key]))
            
            logger.info(f"找到{len(results)}个相关参数")
            return results
            
        except Exception as e:
            logger.error(f"意图投影失败: {str(e)}")
            raise RuntimeError(f"意图投影失败: {str(e)}")


class SemanticDrivenAPIAgent:
    """语义驱动的API反向探索代理"""
    
    def __init__(self):
        self.semantic_space = SemanticSpace()
        self.api_endpoints: Dict[str, APIEndpoint] = {}
        self._is_initialized = False
    
    def load_api_documentation(self, api_docs: Dict[str, Dict]) -> None:
        """
        加载并解析API文档
        
        参数:
            api_docs: API文档字典，格式见示例
            
        示例输入格式:
        {
            "image_processing": {
                "name": "ImageProcessor",
                "description": "图像处理API",
                "category": "media",
                "parameters": {
                    "blur_radius": {
                        "description": "模糊半径，值越大越模糊",
                        "type": "numeric",
                        "min": 0.0,
                        "max": 10.0,
                        "default": 1.0,
                        "semantic_tags": ["gentle", "soft", "smooth"]
                    },
                    "intensity": {
                        "description": "处理强度",
                        "type": "numeric",
                        "min": 0.0,
                        "max": 1.0,
                        "default": 0.5,
                        "semantic_tags": ["strong", "aggressive", "intense"]
                    }
                }
            }
        }
        """
        if not api_docs or not isinstance(api_docs, dict):
            raise ValueError("API文档必须是非空字典")
        
        logger.info("开始加载API文档...")
        
        try:
            for endpoint_name, endpoint_data in api_docs.items():
                # 验证端点数据
                required_fields = ['name', 'description', 'parameters']
                if not all(field in endpoint_data for field in required_fields):
                    logger.warning(f"端点 '{endpoint_name}' 缺少必要字段，跳过")
                    continue
                
                # 解析参数
                parameters = {}
                for param_name, param_data in endpoint_data['parameters'].items():
                    try:
                        param_type = ParameterType(param_data.get('type', 'numeric'))
                        
                        param = APIParameter(
                            name=param_name,
                            description=param_data.get('description', ''),
                            param_type=param_type,
                            min_value=param_data.get('min'),
                            max_value=param_data.get('max'),
                            enum_values=param_data.get('enum_values'),
                            default_value=param_data.get('default'),
                            semantic_tags=param_data.get('semantic_tags', [])
                        )
                        parameters[param_name] = param
                        
                    except ValueError as e:
                        logger.warning(f"参数 '{param_name}' 类型无效: {str(e)}")
                        continue
                
                # 创建API端点对象
                endpoint = APIEndpoint(
                    name=endpoint_data['name'],
                    description=endpoint_data['description'],
                    parameters=parameters,
                    category=endpoint_data.get('category', 'general')
                )
                
                self.api_endpoints[endpoint_name] = endpoint
            
            # 构建语义空间
            self.semantic_space.build_space(self.api_endpoints)
            self._is_initialized = True
            logger.info(f"API文档加载完成，共{len(self.api_endpoints)}个端点")
            
        except Exception as e:
            logger.error(f"API文档加载失败: {str(e)}")
            raise RuntimeError(f"API文档加载失败: {str(e)}")
    
    def map_intent_to_parameters(
        self,
        intent_text: str,
        endpoint_name: Optional[str] = None,
        threshold: float = 0.3
    ) -> Dict[str, Dict[str, Union[float, bool, str]]]:
        """
        将用户意图映射到具体的API参数值
        
        参数:
            intent_text: 用户的自然语言意图描述
            endpoint_name: 可选，指定API端点名称
            threshold: 相似度阈值，低于此值的结果将被过滤
            
        返回:
            参数映射字典，格式为:
            {
                "endpoint_name": {
                    "param_name": value,
                    ...
                },
                ...
            }
            
        异常:
            RuntimeError: 当代理未初始化时抛出
            ValueError: 当输入参数无效时抛出
        """
        if not self._is_initialized:
            raise RuntimeError("代理未初始化，请先调用load_api_documentation")
        
        if not intent_text or not isinstance(intent_text, str):
            raise ValueError("意图文本必须是非空字符串")
        
        if threshold < 0 or threshold > 1:
            raise ValueError("阈值必须在0到1之间")
        
        logger.info(f"开始映射意图: '{intent_text}'")
        
        result = {}
        
        try:
            # 获取最相关的参数
            relevant_params = self.semantic_space.project_intent(intent_text, top_n=10)
            
            # 按端点分组
            endpoint_params = {}
            for key, score, param in relevant_params:
                if score < threshold:
                    continue
                
                endpoint, param_name = key.split('.')
                
                if endpoint_name and endpoint != endpoint_name:
                    continue
                
                if endpoint not in endpoint_params:
                    endpoint_params[endpoint] = []
                
                endpoint_params[endpoint].append((param_name, score, param))
            
            # 为每个端点生成参数值
            for endpoint, params in endpoint_params.items():
                if endpoint not in result:
                    result[endpoint] = {}
                
                for param_name, score, param in params:
                    value = self._infer_parameter_value(intent_text, param, score)
                    if value is not None:
                        result[endpoint][param_name] = value
            
            logger.info(f"意图映射完成，生成{len(result)}个端点的参数配置")
            return result
            
        except Exception as e:
            logger.error(f"意图映射失败: {str(e)}")
            raise RuntimeError(f"意图映射失败: {str(e)}")
    
    def _infer_parameter_value(
        self,
        intent_text: str,
        param: APIParameter,
        relevance_score: float
    ) -> Optional[Union[float, bool, str]]:
        """
        根据意图和参数信息推断参数值
        
        参数:
            intent_text: 用户意图文本
            param: API参数对象
            relevance_score: 相关性得分
            
        返回:
            推断的参数值，如果无法推断则返回None
        """
        # 定义意图关键词与参数调整方向的映射
        intensity_keywords = {
            'increase': ['更多', '更强', '激进', '加大', '提高', 'more', 'stronger', 'aggressive', 'increase'],
            'decrease': ['更少', '更弱', '温和', '减轻', '降低', 'less', 'weaker', 'gentle', 'decrease', 'smooth']
        }
        
        # 判断意图方向
        direction = None
        for keyword_group in intensity_keywords['increase']:
            if keyword_group in intent_text.lower():
                direction = 'increase'
                break
        
        if not direction:
            for keyword_group in intensity_keywords['decrease']:
                if keyword_group in intent_text.lower():
                    direction = 'decrease'
                    break
        
        # 根据参数类型推断值
        if param.param_type == ParameterType.NUMERIC:
            if direction == 'increase':
                # 对于"增加"意图，取参数范围的上限部分
                if param.max_value is not None and param.min_value is not None:
                    return param.min_value + (param.max_value - param.min_value) * (0.7 + 0.3 * relevance_score)
                elif param.default_value is not None:
                    return param.default_value * 1.5
            
            elif direction == 'decrease':
                # 对于"减少"意图，取参数范围的下限部分
                if param.max_value is not None and param.min_value is not None:
                    return param.min_value + (param.max_value - param.min_value) * (0.3 * relevance_score)
                elif param.default_value is not None:
                    return param.default_value * 0.5
            
            else:
                # 无明确方向，使用默认值或相关性调整
                if param.default_value is not None:
                    return param.default_value
                elif param.max_value is not None and param.min_value is not None:
                    return param.min_value + (param.max_value - param.min_value) * 0.5
        
        elif param.param_type == ParameterType.BOOLEAN:
            # 布尔类型根据相关性决定
            return relevance_score > 0.6
        
        elif param.param_type == ParameterType.ENUM:
            if param.enum_values:
                # 枚举类型选择最相关的值
                return param.enum_values[0]  # 简化处理，实际可扩展为更复杂的匹配
        
        # 默认返回默认值
        return param.default_value
    
    def explain_parameter_mapping(
        self,
        intent_text: str,
        endpoint_name: Optional[str] = None
    ) -> List[Dict[str, Union[str, float]]]:
        """
        解释参数映射的推理过程
        
        参数:
            intent_text: 用户意图文本
            endpoint_name: 可选，指定API端点名称
            
        返回:
            解释信息列表，每个元素包含参数名、推理路径和相关性得分
        """
        if not self._is_initialized:
            raise RuntimeError("代理未初始化，请先调用load_api_documentation")
        
        try:
            relevant_params = self.semantic_space.project_intent(intent_text, top_n=5)
            explanations = []
            
            for key, score, param in relevant_params:
                if endpoint_name and not key.startswith(f"{endpoint_name}."):
                    continue
                
                # 构建推理路径
                tags_str = ', '.join(param.semantic_tags) if param.semantic_tags else '无'
                reasoning = (
                    f"参数 '{param.name}' 的描述 '{param.description}' "
                    f"与语义标签 [{tags_str}] 和您的意图 '{intent_text}' "
                    f"在语义空间中具有较高的相似度({score:.2f})"
                )
                
                explanations.append({
                    'parameter': key,
                    'reasoning': reasoning,
                    'relevance_score': score,
                    'description': param.description
                })
            
            return explanations
            
        except Exception as e:
            logger.error(f"生成解释失败: {str(e)}")
            raise RuntimeError(f"生成解释失败: {str(e)}")


def demonstrate_usage():
    """使用示例演示"""
    
    # 示例API文档
    sample_api_docs = {
        "image_processing": {
            "name": "ImageProcessor",
            "description": "图像处理API",
            "category": "media",
            "parameters": {
                "blur_radius": {
                    "description": "模糊半径，值越大越模糊",
                    "type": "numeric",
                    "min": 0.0,
                    "max": 10.0,
                    "default": 1.0,
                    "semantic_tags": ["gentle", "soft", "smooth", "温和", "柔化"]
                },
                "intensity": {
                    "description": "处理强度，控制效果的明显程度",
                    "type": "numeric",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.5,
                    "semantic_tags": ["strong", "aggressive", "intense", "激进", "强烈"]
                },
                "denoise": {
                    "description": "是否启用降噪处理",
                    "type": "boolean",
                    "default": False,
                    "semantic_tags": ["clean", "smooth", "纯净"]
                }
            }
        },
        "data_processing": {
            "name": "DataTransformer",
            "description": "数据处理API",
            "category": "data",
            "parameters": {
                "sample_rate": {
                    "description": "采样率，控制数据点的密度",
                    "type": "numeric",
                    "min": 0.1,
                    "max": 1.0,
                    "default": 0.5,
                    "semantic_tags": ["dense", "sparse", "密集", "稀疏"]
                },
                "smoothing_factor": {
                    "description": "平滑因子，使数据曲线更平滑",
                    "type": "numeric",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.3,
                    "semantic_tags": ["smooth", "gentle", "平滑", "温和"]
                }
            }
        }
    }
    
    print("=" * 60)
    print("语义驱动的API反向探索代理 - 使用示例")
    print("=" * 60)
    
    try:
        # 创建代理实例
        agent = SemanticDrivenAPIAgent()
        
        # 加载API文档
        print("\n[1] 加载API文档...")
        agent.load_api_documentation(sample_api_docs)
        print("API文档加载成功!")
        
        # 示例1: 温和处理
        print("\n[2] 示例1: 用户意图 '处理得温和一点'")
        result1 = agent.map_intent_to_parameters("处理得温和一点")
        print("生成的参数配置:")
        print(json.dumps(result1, indent=2, ensure_ascii=False))
        
        # 示例2: 激进处理
        print("\n[3] 示例2: 用户意图 'make it more aggressive'")
        result2 = agent.map_intent_to_parameters("make it more aggressive")
        print("生成的参数配置:")
        print(json.dumps(result2, indent=2, ensure_ascii=False))
        
        # 获取推理解释
        print("\n[4] 推理过程解释:")
        explanations = agent.explain_parameter_mapping("处理得温和一点")
        for exp in explanations:
            print(f"\n参数: {exp['parameter']}")
            print(f"相关性得分: {exp['relevance_score']:.3f}")
            print(f"推理路径: {exp['reasoning']}")
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")


if __name__ == "__main__":
    demonstrate_usage()