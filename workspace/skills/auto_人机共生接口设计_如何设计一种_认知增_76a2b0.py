"""
人机共生认知增益接口模块

该模块实现了一种基于认知科学原理的界面设计框架，通过可视化AI推理链条(CoT)，
使人类用户能够以最小认知负荷定位潜在错误环节，实现从"执行者"到"审核者"的角色转变。

核心功能：
1. 推理链可视化分析
2. 认知负荷评估
3. 高风险节点识别
4. 自适应界面生成

典型应用场景：
- AI决策系统审核
- 自动化流程验证
- 复杂系统诊断
- 知识工作增强

数据格式：
- 输入: JSON格式的推理链条数据
- 输出: 带认知增强标记的UI组件描述
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum
import math
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cognitive_enhancement.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """推理节点风险等级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ReasoningNode:
    """推理链条中的单个节点数据结构"""
    id: str
    content: str
    dependencies: List[str]
    confidence: float
    source: str
    timestamp: str
    metadata: Dict[str, Union[str, float, int]]


class CognitiveEnhancementInterface:
    """
    认知增益用户界面核心类
    
    该类封装了人机共生接口的核心逻辑，通过分析AI推理链条，
    生成适合人类认知特点的界面呈现方案。
    
    属性:
        nodes (List[ReasoningNode]): 推理节点集合
        risk_threshold (float): 风险判定阈值
        cognitive_load_limit (int): 认知负荷上限
    """
    
    def __init__(self, risk_threshold: float = 0.7, cognitive_load_limit: int = 5):
        """
        初始化认知增益接口
        
        参数:
            risk_threshold: 高风险节点置信度阈值
            cognitive_load_limit: 用户单次处理的最大节点数
        """
        self.nodes = []
        self.risk_threshold = risk_threshold
        self.cognitive_load_limit = cognitive_load_limit
        self._validate_parameters()
        logger.info("CognitiveEnhancementInterface initialized with risk_threshold=%.2f", risk_threshold)
    
    def _validate_parameters(self) -> None:
        """验证初始化参数有效性"""
        if not 0 < self.risk_threshold < 1:
            raise ValueError("Risk threshold must be between 0 and 1")
        if self.cognitive_load_limit < 1:
            raise ValueError("Cognitive load limit must be positive")
    
    def load_reasoning_chain(self, json_data: Union[str, Dict]) -> bool:
        """
        加载AI生成的推理链条数据
        
        参数:
            json_data: JSON字符串或已解析的字典对象
            
        返回:
            bool: 加载是否成功
            
        异常:
            ValueError: 当数据格式无效时
        """
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            if not isinstance(data, dict) or 'nodes' not in data:
                raise ValueError("Invalid reasoning chain format")
                
            self.nodes = [ReasoningNode(**node) for node in data['nodes']]
            logger.info("Successfully loaded %d reasoning nodes", len(self.nodes))
            return True
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Failed to parse reasoning chain data: %s", str(e))
            raise ValueError(f"Invalid JSON data: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error loading reasoning chain: %s", str(e))
            raise
    
    def analyze_cognitive_load(self) -> Dict[str, Union[float, List[str]]]:
        """
        分析当前推理链条的认知负荷特征
        
        返回:
            Dict: 包含以下键的字典:
                - 'total_nodes': 总节点数
                - 'avg_complexity': 平均复杂度
                - 'high_risk_nodes': 高风险节点ID列表
                - 'load_index': 认知负荷指数(0-1)
                
        示例:
            >>> interface = CognitiveEnhancementInterface()
            >>> interface.load_reasoning_chain(sample_data)
            >>> analysis = interface.analyze_cognitive_load()
        """
        if not self.nodes:
            logger.warning("Attempted to analyze empty reasoning chain")
            return {
                'total_nodes': 0,
                'avg_complexity': 0.0,
                'high_risk_nodes': [],
                'load_index': 0.0
            }
        
        try:
            # 计算基本指标
            total_nodes = len(self.nodes)
            avg_confidence = sum(node.confidence for node in self.nodes) / total_nodes
            high_risk_nodes = [
                node.id for node in self.nodes 
                if node.confidence < self.risk_threshold
            ]
            
            # 计算复杂度指标(考虑依赖关系)
            complexity_scores = [
                self._calculate_node_complexity(node)
                for node in self.nodes
            ]
            avg_complexity = sum(complexity_scores) / total_nodes
            
            # 计算认知负荷指数
            load_index = min(1.0, total_nodes / (self.cognitive_load_limit * 2))
            
            result = {
                'total_nodes': total_nodes,
                'avg_complexity': avg_complexity,
                'high_risk_nodes': high_risk_nodes,
                'load_index': load_index,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.debug("Cognitive load analysis completed: %s", result)
            return result
            
        except Exception as e:
            logger.error("Error during cognitive load analysis: %s", str(e))
            raise RuntimeError("Failed to analyze cognitive load") from e
    
    def generate_enhanced_ui(self) -> Dict[str, List[Dict]]:
        """
        生成认知增强型UI描述
        
        该方法根据认知负荷分析结果，生成适合人类审核的界面组件布局，
        突出显示需要重点关注的环节。
        
        返回:
            Dict: 包含以下键的字典:
                - 'focus_areas': 需要重点审核的区域
                - 'visualization_hints': 可视化建议
                - 'interaction_guidance': 交互指导
                
        示例:
            >>> ui_components = interface.generate_enhanced_ui()
            >>> print(ui_components['focus_areas'][0])
        """
        if not self.nodes:
            return {'focus_areas': [], 'visualization_hints': [], 'interaction_guidance': []}
        
        try:
            # 获取认知负荷分析
            analysis = self.analyze_cognitive_load()
            
            # 生成焦点区域
            focus_areas = [
                {
                    'node_id': node.id,
                    'priority': self._calculate_priority(node),
                    'visualization': self._recommend_visualization(node),
                    'verification_hints': self._generate_verification_hints(node)
                }
                for node in self.nodes
                if node.confidence < self.risk_threshold
            ]
            
            # 按优先级排序
            focus_areas.sort(key=lambda x: x['priority'], reverse=True)
            
            # 限制焦点区域数量以避免认知过载
            focus_areas = focus_areas[:self.cognitive_load_limit]
            
            # 生成可视化建议
            visualization_hints = [
                {
                    'type': 'confidence_heatmap',
                    'nodes': [node.id for node in self.nodes],
                    'values': [node.confidence for node in self.nodes]
                },
                {
                    'type': 'dependency_graph',
                    'highlight_nodes': [area['node_id'] for area in focus_areas]
                }
            ]
            
            # 生成交互指导
            interaction_guidance = [
                {
                    'action': 'verify_source',
                    'target_nodes': [node.id for node in self.nodes 
                                    if node.source == 'external'],
                    'guidance': '检查外部数据源的可信度'
                },
                {
                    'action': 'review_dependencies',
                    'target_nodes': list(set(
                        dep for node in self.nodes 
                        for dep in node.dependencies
                        if node.confidence < self.risk_threshold
                    )),
                    'guidance': '验证依赖关系的正确性'
                }
            ]
            
            result = {
                'focus_areas': focus_areas,
                'visualization_hints': visualization_hints,
                'interaction_guidance': interaction_guidance,
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("Generated enhanced UI with %d focus areas", len(focus_areas))
            return result
            
        except Exception as e:
            logger.error("Error generating enhanced UI: %s", str(e))
            raise RuntimeError("Failed to generate enhanced UI") from e
    
    def _calculate_node_complexity(self, node: ReasoningNode) -> float:
        """
        计算单个节点的复杂度分数(辅助方法)
        
        参数:
            node: 要分析的推理节点
            
        返回:
            float: 复杂度分数(0-1)
        """
        # 基于依赖数量、内容长度和元数据复杂度的加权计算
        dependency_factor = min(1.0, len(node.dependencies) / 3)
        content_factor = min(1.0, len(node.content.split()) / 20)
        metadata_factor = min(1.0, len(node.metadata) / 5)
        
        return 0.4 * dependency_factor + 0.3 * content_factor + 0.3 * metadata_factor
    
    def _calculate_priority(self, node: ReasoningNode) -> float:
        """
        计算节点的审核优先级(辅助方法)
        
        参数:
            node: 要分析的推理节点
            
        返回:
            float: 优先级分数(0-1)
        """
        # 风险因素(置信度越低风险越高)
        risk_factor = 1 - node.confidence
        
        # 复杂度因素
        complexity = self._calculate_node_complexity(node)
        
        # 依赖因素(被更多节点依赖的节点优先级更高)
        dependency_count = sum(
            1 for n in self.nodes 
            if node.id in n.dependencies
        )
        dependency_factor = min(1.0, dependency_count / 2)
        
        return 0.5 * risk_factor + 0.3 * complexity + 0.2 * dependency_factor
    
    def _recommend_visualization(self, node: ReasoningNode) -> Dict[str, str]:
        """
        为节点推荐最佳可视化方式(辅助方法)
        
        参数:
            node: 要分析的推理节点
            
        返回:
            Dict: 可视化建议
        """
        if node.confidence < 0.5:
            return {
                'type': 'warning_highlight',
                'style': 'red_background',
                'icon': 'alert_triangle'
            }
        elif node.confidence < self.risk_threshold:
            return {
                'type': 'attention_highlight',
                'style': 'yellow_background',
                'icon': 'info'
            }
        else:
            return {
                'type': 'standard_display',
                'style': 'default',
                'icon': 'check'
            }
    
    def _generate_verification_hints(self, node: ReasoningNode) -> List[str]:
        """
        生成节点验证提示(辅助方法)
        
        参数:
            node: 要分析的推理节点
            
        返回:
            List[str]: 验证提示列表
        """
        hints = []
        
        if node.confidence < 0.5:
            hints.append("该节点置信度极低，建议优先验证")
        
        if len(node.dependencies) > 2:
            hints.append("节点依赖较多，建议检查依赖链")
        
        if node.source == 'external':
            hints.append("基于外部数据，需验证数据源可靠性")
        
        if not hints:
            hints.append("常规检查节点内容")
        
        return hints


# 示例使用
if __name__ == "__main__":
    # 示例推理链条数据
    SAMPLE_DATA = {
        "nodes": [
            {
                "id": "node1",
                "content": "系统检测到异常登录尝试",
                "dependencies": [],
                "confidence": 0.92,
                "source": "internal",
                "timestamp": "2023-05-15T08:30:00",
                "metadata": {"count": 3, "location": "NY"}
            },
            {
                "id": "node2",
                "content": "IP地址来自高风险地区",
                "dependencies": ["node1"],
                "confidence": 0.65,
                "source": "external",
                "timestamp": "2023-05-15T08:31:00",
                "metadata": {"risk_score": 0.7, "country": "XX"}
            },
            {
                "id": "node3",
                "content": "账户存在数据泄露风险",
                "dependencies": ["node1", "node2"],
                "confidence": 0.45,
                "source": "inference",
                "timestamp": "2023-05-15T08:32:00",
                "metadata": {"affected_users": 120}
            }
        ]
    }
    
    try:
        # 初始化接口
        interface = CognitiveEnhancementInterface(risk_threshold=0.7)
        
        # 加载数据
        interface.load_reasoning_chain(SAMPLE_DATA)
        
        # 分析认知负荷
        analysis = interface.analyze_cognitive_load()
        print("认知负荷分析:", json.dumps(analysis, indent=2))
        
        # 生成增强UI
        ui_components = interface.generate_enhanced_ui()
        print("增强UI组件:", json.dumps(ui_components, indent=2))
        
    except Exception as e:
        logger.error("示例运行失败: %s", str(e))