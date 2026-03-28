"""
类型学生成式设计代理

利用LLM理解建筑规范与功能类型，构建一个'语义-空间'对齐的流形空间。
在这个空间中，'厨房'到'餐厅'的测地线距离应极短，而到'厕所'的距离受规范约束。
AI不仅能生成图纸，还能在潜在空间中进行'类型变异'（如将教堂的空间感融合到住宅中），
创造出既符合功能逻辑又具备陌生化美感的建筑方案。

Author: AGI System
Version: 1.0.0
Domain: cross_domain (Architecture + AI + NLP)
"""

import logging
import json
import math
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BuildingCodeError(Exception):
    """自定义异常：违反建筑规范"""
    pass

class SpaceSemantic(Enum):
    """空间语义枚举，定义建筑功能类型"""
    LIVING = "living"
    KITCHEN = "kitchen"
    DINING = "dining"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    SANCTUARY = "sanctuary" # 教堂圣殿
    NAVE = "nave"           # 教堂中殿
    FOYER = "foyer"

@dataclass
class SemanticNode:
    """
    语义-空间节点。
    
    Attributes:
        id: 节点唯一标识
        semantic_type: 空间语义类型
        vector: 在潜在流形空间中的向量表示
        properties: 额外的物理属性 (如面积, 高度)
    """
    id: str
    semantic_type: SpaceSemantic
    vector: List[float]
    properties: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.vector, list) or len(self.vector) == 0:
            raise ValueError("Vector must be a non-empty list.")
        if not all(isinstance(v, (float, int)) for v in self.vector):
            raise ValueError("Vector elements must be numeric.")

class SemanticManifold:
    """
    语义-空间对齐的流形空间。
    管理空间节点及其拓扑关系。
    """
    
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
        self.nodes: Dict[str, SemanticNode] = {}
        self.adjacency_cache: Dict[Tuple[str, str], float] = {}
        logger.info(f"Initialized SemanticManifold with {dimensions} dimensions.")

    def add_node(self, node: SemanticNode) -> None:
        """添加节点到流形空间"""
        if len(node.vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch. Expected {self.dimensions}, got {len(node.vector)}")
        self.nodes[node.id] = node
        logger.debug(f"Node {node.id} added to manifold.")

    def euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """计算欧几里得距离"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def geodesic_distance(self, id1: str, id2: str) -> float:
        """
        计算测地线距离。
        在此简化实现中，我们假设流形足够平滑，测地线距离近似于向量空间中的加权距离。
        """
        if id1 not in self.nodes or id2 not in self.nodes:
            raise KeyError("Node ID not found in manifold.")
        
        node1 = self.nodes[id1]
        node2 = self.nodes[id2]
        
        # 基础距离
        dist = self.euclidean_distance(node1.vector, node2.vector)
        
        # 语义约束加权 (模拟LLM理解的规范约束)
        # 示例：厨房到餐厅应该很近
        if {node1.semantic_type, node2.semantic_type} == {SpaceSemantic.KITCHEN, SpaceSemantic.DINING}:
            dist *= 0.1 # 强吸引
        # 示例：厕所到厨房/餐厅应该较远 (卫生规范)
        elif {node1.semantic_type, node2.semantic_type} == {SpaceSemantic.BATHROOM, SpaceSemantic.KITCHEN}:
            dist *= 10.0 # 强排斥
            
        return dist

class GenerativeDesignAgent:
    """
    核心代理类。
    利用LLM理解逻辑并生成/变异设计方案。
    """
    
    def __init__(self, llm_model_name: str = "claude-3-opus"):
        self.llm_model = llm_model_name
        self.manifold = SemanticManifold(dimensions=128)
        logger.info(f"Agent initialized with model: {llm_model_name}")

    def _validate_program(self, requirements: Dict[str, Any]) -> bool:
        """
        辅助函数：验证输入需求是否符合基本逻辑。
        
        Args:
            requirements: 包含 'functions', 'style', 'constraints' 的字典
            
        Returns:
            bool: 验证通过返回True
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not requirements.get("functions"):
            raise ValueError("Input requirements must contain 'functions' list.")
        
        if not isinstance(requirements["functions"], list):
            raise ValueError("'functions' must be a list of strings.")
            
        logger.info("Input requirements validated successfully.")
        return True

    def construct_semantic_space(self, design_brief: Dict[str, Any]) -> SemanticManifold:
        """
        核心函数1：构建语义-空间流形。
        
        根据设计任务书，利用LLM解析功能关系，在流形空间中生成初始节点布局。
        
        Args:
            design_brief: 建筑设计任务书
                Format: {
                    "functions": ["kitchen", "living", "bathroom"],
                    "style": "modern",
                    "constraints": {"max_area": 100}
                }
        
        Returns:
            SemanticManifold: 填充了初始节点的流形空间
        """
        try:
            self._validate_program(design_brief)
            
            # 模拟LLM解析过程：将自然语言功能映射为语义枚举和向量
            functions = design_brief["functions"]
            
            for i, func_name in enumerate(functions):
                try:
                    sem_type = SpaceSemantic[func_name.upper()]
                except KeyError:
                    sem_type = SpaceSemantic.LIVING # Default fallback
                    logger.warning(f"Unknown function '{func_name}', defaulting to LIVING.")
                
                # 生成随机向量模拟LLM生成的语义嵌入
                # 在真实场景中，这里会调用 sentence-transformers 或 LLM embedding API
                vector = [random.gauss(0, 1) for _ in range(self.manifold.dimensions)]
                
                # 根据类型调整向量特定维度 (模拟语义聚类)
                # 例如：所有服务空间（厨卫）在第0维为负，生活空间为正
                if sem_type in [SpaceSemantic.KITCHEN, SpaceSemantic.BATHROOM]:
                    vector[0] = -abs(vector[0]) 
                else:
                    vector[0] = abs(vector[0])
                    
                node = SemanticNode(
                    id=f"node_{i}_{func_name}",
                    semantic_type=sem_type,
                    vector=vector,
                    properties={"area": random.uniform(10, 50)}
                )
                self.manifold.add_node(node)
                
            logger.info(f"Semantic space constructed with {len(self.manifold.nodes)} nodes.")
            return self.manifold
            
        except Exception as e:
            logger.error(f"Error constructing semantic space: {e}")
            raise

    def morphological_mutation(
        self, 
        target_node_id: str, 
        style_reference: SpaceSemantic, 
        intensity: float = 0.5
    ) -> SemanticNode:
        """
        核心函数2：类型变异。
        
        将一种建筑类型的特征（如教堂的高耸感）融合到目标节点（如住宅客厅）。
        
        Args:
            target_node_id: 需要变异的目标节点ID
            style_reference: 提供风格特征的参考语义类型 (e.g., SpaceSemantic.NAVE)
            intensity: 变异强度 [0.0, 1.0]
            
        Returns:
            SemanticNode: 变异后的新节点
        """
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("Intensity must be between 0.0 and 1.0")
            
        if target_node_id not in self.manifold.nodes:
            raise KeyError(f"Target node {target_node_id} not found.")
            
        logger.info(f"Starting morphological mutation: blending {style_reference.value} into {target_node_id}")
        
        target_node = self.manifold.nodes[target_node_id]
        
        # 1. 获取参考类型的原型向量
        # 这里为了演示，动态生成一个模拟的原型向量
        # 教堂特征：垂直性强 (假设在维度1上体现)
        ref_vector = [0.0] * self.manifold.dimensions
        if style_reference == SpaceSemantic.NAVE or style_reference == SpaceSemantic.SANCTUARY:
            ref_vector[1] = 10.0  # 强垂直感
            ref_vector[2] = 5.0   # 神圣光感
        else:
            ref_vector = [random.gauss(0, 0.5) for _ in range(self.manifold.dimensions)]
            
        # 2. 向量插值
        # new_vec = (1-a)*orig + a*ref
        new_vector = []
        for orig_val, ref_val in zip(target_node.vector, ref_vector):
            new_val = (1 - intensity) * orig_val + intensity * ref_val
            new_vector.append(new_val)
            
        # 3. 创建变异节点
        mutated_node = SemanticNode(
            id=f"{target_node_id}_mutated_{style_reference.value}",
            semantic_type=target_node.semantic_type, # 功能类型保持不变（仍是住宅）
            vector=new_vector,
            properties=target_node.properties.copy()
        )
        
        # 更新属性：例如融合教堂风格后层高增加
        mutated_node.properties["height"] = mutated_node.properties.get("height", 3.0) * (1 + intensity * 2)
        
        logger.info(f"Mutation complete. New node ID: {mutated_node.id}")
        return mutated_node

    def check_compliance(self, node1: SemanticNode, node2: SemanticNode) -> bool:
        """
        检查两个空间节点的布局是否符合建筑规范。
        """
        dist = self.manifold.geodesic_distance(node1.id, node2.id)
        
        # 规范检查：厨房与卫生间不能直接相邻（模拟规范）
        if {node1.semantic_type, node2.semantic_type} == {SpaceSemantic.KITCHEN, SpaceSemantic.BATHROOM}:
            if dist < 50.0: # 阈值
                logger.warning(f"Compliance Check Failed: {node1.semantic_type.value} too close to {node2.semantic_type.value}")
                return False
        
        logger.info("Compliance check passed.")
        return True

# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 初始化代理
    agent = GenerativeDesignAgent(llm_model_name="arch-llm-v1")
    
    # 2. 定义设计任务书
    brief = {
        "functions": ["kitchen", "dining", "bathroom", "living"],
        "style": "contemporary",
        "constraints": {"max_area": 120}
    }
    
    try:
        # 3. 构建流形空间
        manifold = agent.construct_semantic_space(brief)
        
        # 4. 检查初始空间关系
        node_ids = list(manifold.nodes.keys())
        if len(node_ids) >= 2:
            n1 = manifold.nodes[node_ids[0]]
            n2 = manifold.nodes[node_ids[1]]
            dist = manifold.geodesic_distance(n1.id, n2.id)
            print(f"Distance between {n1.semantic_type.value} and {n2.semantic_type.value}: {dist:.4f}")
            
        # 5. 执行类型变异 - 将教堂(Sanctuary)的空间感融合到客厅
        living_node_id = next(id for id, node in manifold.nodes.items() if node.semantic_type == SpaceSemantic.LIVING)
        
        mutated_living = agent.morphological_mutation(
            target_node_id=living_node_id,
            style_reference=SpaceSemantic.SANCTUARY,
            intensity=0.7
        )
        
        # 6. 输出结果
        print(f"\nMutated Node Properties: {json.dumps(mutated_living.properties, indent=2)}")
        print(f"Mutated Node Vector (first 5 dims): {mutated_living.vector[:5]}")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")