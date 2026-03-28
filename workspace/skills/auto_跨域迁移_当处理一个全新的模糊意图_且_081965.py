"""
Module: auto_cross_domain_transfer_fuzzy_intent_081965
Description: 实现【跨域迁移】核心逻辑。利用'重叠固化'（Overlapping Solidification）原理，
             当处理一个全新的、模糊的意图（在现有节点库中无直接匹配）时，通过计算不同领域
             （如'烹饪'与'化学实验'）节点间的结构相似性，复用旧领域的成熟流程模板来解决新问题。
Author: Senior Python Engineer (AGI System Component)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义异常类
class TransferLearningError(Exception):
    """Base exception for transfer learning errors."""
    pass

class NodeValidationError(TransferLearningError):
    """Raised when node structure is invalid."""
    pass

class NoMatchingTemplateError(TransferLearningError):
    """Raised when no suitable template is found."""
    pass

@dataclass
class Node:
    """
    表示知识图谱中的一个节点（意图或流程）。
    
    Attributes:
        id (str): 节点唯一标识符。
        domain (str): 节点所属领域 (e.g., 'chemistry', 'cooking')。
        raw_intent (str): 原始意图描述。
        features (Dict[str, float]): 节点的特征向量，用于相似度计算。
        process_template (Dict): 该节点关联的执行流程模板。
    """
    id: str
    domain: str
    raw_intent: str
    features: Dict[str, float]
    process_template: Dict

class StructuralSimilarityEngine:
    """
    核心引擎：基于'重叠固化'原理计算结构相似性并执行迁移。
    """
    
    def __init__(self, existing_nodes: List[Node], similarity_threshold: float = 0.75):
        """
        初始化引擎。
        
        Args:
            existing_nodes (List[Node]): 现有的1841个（或其他数量）节点库。
            similarity_threshold (float): 触发迁移的相似度阈值。
        """
        self.node_database = existing_nodes
        self.similarity_threshold = similarity_threshold
        logger.info(f"Engine initialized with {len(existing_nodes)} nodes and threshold {similarity_threshold}")

    def _validate_node(self, node_data: Dict[str, Any]) -> Node:
        """
        [Helper Function] 验证并转换字典数据为Node对象。
        
        Args:
            node_data: 原始节点数据。
            
        Returns:
            Node: 验证后的Node对象。
            
        Raises:
            NodeValidationError: 如果数据缺失或格式错误。
        """
        required_keys = ['id', 'domain', 'raw_intent', 'features', 'process_template']
        if not all(key in node_data for key in required_keys):
            raise NodeValidationError(f"Missing required keys in node data: {required_keys}")
        
        if not isinstance(node_data['features'], dict):
            raise NodeValidationError("Features must be a dictionary.")
            
        return Node(**node_data)

    def _calculate_overlap_coefficient(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """
        [Helper Function] 计算两个特征向量的重叠系数（模拟重叠固化原理）。
        这里使用加权Jaccard相似度作为结构相似性的代理指标。
        
        Args:
            vec_a: 特征向量A。
            vec_b: 特征向量B。
            
        Returns:
            float: 相似度分数 (0.0 to 1.0)。
        """
        intersection_weight = 0.0
        union_weight = 0.0
        
        keys_a = set(vec_a.keys())
        keys_b = set(vec_b.keys())
        
        # 计算交集特征的权重和
        common_keys = keys_a & keys_b
        for key in common_keys:
            # 固化权重：如果特征相同，权重更高
            intersection_weight += min(vec_a[key], vec_b[key]) * 1.5 
            
        # 计算并集特征的权重和
        all_keys = keys_a | keys_b
        for key in all_keys:
            if key in vec_a:
                union_weight += vec_a[key]
            if key in vec_b:
                # 避免重复计算交集部分的简单逻辑（简化版）
                if key not in common_keys:
                    union_weight += vec_b[key]
        
        if union_weight == 0:
            return 0.0
            
        return intersection_weight / union_weight

    def find_best_match_and_transfer(self, fuzzy_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心功能：处理模糊意图，寻找最佳跨域匹配并返回复用后的流程。
        
        流程:
        1. 验证输入的模糊意图。
        2. 遍历现有节点库，计算结构相似度。
        3. 如果相似度超过阈值，复用该节点的模板。
        4. 对模板进行变量替换/适配（模拟）。
        
        Args:
            fuzzy_intent_data: 包含新意图信息的字典，需包含 'features' 和 'context'。
            
        Returns:
            Dict: 包含匹配结果、相似度分数和适配后的流程模板。
            
        Raises:
            NoMatchingTemplateError: 如果没有找到合适的模板。
        """
        try:
            # 1. 数据验证
            if 'features' not in fuzzy_intent_data:
                raise ValueError("Input must contain 'features' for similarity calculation.")
                
            input_features = fuzzy_intent_data['features']
            input_domain = fuzzy_intent_data.get('domain', 'unknown')
            
            best_match: Optional[Node] = None
            highest_score = 0.0
            
            logger.info(f"Processing fuzzy intent from domain: {input_domain}")
            
            # 2. 遍历与计算 (在AGI场景下，此处应优化为向量检索)
            for candidate in self.node_database:
                # 跳过完全相同的领域，强制寻找跨域迁移机会
                if candidate.domain == input_domain:
                    continue
                    
                score = self._calculate_overlap_coefficient(input_features, candidate.features)
                
                if score > highest_score:
                    highest_score = score
                    best_match = candidate
                    
            # 3. 检查阈值与固化
            if best_match and highest_score >= self.similarity_threshold:
                logger.info(f"Cross-domain match found! Domain: {best_match.domain}, Score: {highest_score:.4f}")
                
                # 执行模板复用逻辑
                adapted_template = self._adapt_template(
                    source_template=best_match.process_template,
                    target_context=fuzzy_intent_data.get('context', {})
                )
                
                return {
                    "status": "success",
                    "matched_node_id": best_match.id,
                    "source_domain": best_match.domain,
                    "similarity_score": highest_score,
                    "adapted_process": adapted_template,
                    "strategy": "Cross-Domain Structural Reuse"
                }
            else:
                logger.warning(f"No suitable cross-domain template found. Max score: {highest_score}")
                raise NoMatchingTemplateError("Intent too ambiguous or no structural equivalent in other domains.")

        except Exception as e:
            logger.error(f"Error during transfer learning process: {str(e)}")
            raise TransferLearningError(f"Failed to process intent: {str(e)}")

    def _adapt_template(self, source_template: Dict, target_context: Dict) -> Dict:
        """
        [Core Function] 模板适配器。
        将源领域的流程模板根据新问题的上下文进行参数映射。
        
        Args:
            source_template: 源领域的原始模板。
            target_context: 新问题的上下文变量。
            
        Returns:
            Dict: 适配后的模板。
        """
        # 这里模拟深拷贝和变量注入
        # 在实际AGI系统中，这涉及复杂的图神经网络重写或规则替换
        adapted = json.loads(json.dumps(source_template)) # Deep copy hack for demo
        
        # 注入迁移标记
        adapted['_meta'] = {
            "is_transferred": True,
            "timestamp": "2023-10-27T10:00:00Z",
            "modification_log": [
                "Mapped 'heating_element' to 'stove'",
                "Mapped 'reaction_chamber' to 'pot'"
            ]
        }
        
        # 简单的键值替换逻辑示例
        if 'steps' in adapted:
            for step in adapted['steps']:
                if 'action' in step:
                    # 示例：化学实验 -> 烹饪 的动词映射
                    mapping = {
                        "dissolve": "mix",
                        "heat_gently": "simmer",
                        "precipitate": "thicken"
                    }
                    step['action'] = mapping.get(step['action'], step['action'])
                    
        return adapted

# ==========================================
# Usage Example (Simulated Execution)
# ==========================================
if __name__ == "__main__":
    # 模拟现有的节点数据库
    mock_db = [
        Node(
            id="node_001",
            domain="chemistry",
            raw_intent="Mix two reagents and apply heat",
            features={"mix": 0.8, "heat": 0.9, "container": 0.5, "time_sensitive": 0.3},
            process_template={
                "steps": [
                    {"step_id": 1, "action": "dissolve", "params": {"reagent": "A", "solvent": "water"}},
                    {"step_id": 2, "action": "heat_gently", "params": {"temp": 60, "duration": 300}}
                ]
            }
        ),
        Node(
            id="node_099",
            domain="construction",
            raw_intent="Mix cement and water",
            features={"mix": 0.9, "solidify": 0.8, "container": 0.2},
            process_template={"steps": [{"step_id": 1, "action": "blend", "params": {}}]}
        )
    ]

    # 初始化引擎
    engine = StructuralSimilarityEngine(existing_nodes=mock_db, similarity_threshold=0.7)

    # 模拟全新的模糊意图：来自 'cooking' 领域，意图类似于化学实验（混合加热）
    new_fuzzy_intent = {
        "domain": "cooking",
        "features": {"mix": 0.75, "heat": 0.85, "container": 0.6, "edible": 0.9},
        "context": {
            "ingredients": ["flour", "water"],
            "goal": "make_sauce"
        }
    }

    print(f"{'='*15} Running Cross-Domain Transfer {'='*15}")
    
    try:
        result = engine.find_best_match_and_transfer(new_fuzzy_intent)
        print(f"Match Status: {result['status']}")
        print(f"Source Domain: {result['source_domain']} (ID: {result['matched_node_id']})")
        print(f"Similarity Score: {result['similarity_score']:.2f}")
        print("Adapted Process Steps:")
        for step in result['adapted_process'].get('steps', []):
            print(f"  - {step}")
    except TransferLearningError as e:
        print(f"Execution failed: {e}")

    print(f"{'='*15} Execution Finished {'='*15}")