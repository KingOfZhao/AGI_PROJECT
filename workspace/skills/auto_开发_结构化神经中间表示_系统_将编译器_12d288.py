"""
结构化神经中间表示系统 (Structured Neural Intermediate Representation - SNIR)

该模块实现了一个将编译器控制流图(CFG)与高维语义向量融合的系统。
通过将代码或文本的逻辑结构（如条件分支、循环、顺序执行）映射为特定的向量空间变换，
使得模型能够理解"结构逻辑性"，而不仅仅是语义相似性。

主要应用场景：
- 法律合同中的逻辑漏洞检测（例如：终止条款与续约条款的冲突）
- 医疗指南中的流程完整性校验
- 代码逻辑的语义一致性分析

依赖：
- numpy: 基础数值计算
- networkx: 图结构处理 (需安装)
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import networkx as nx
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SNIR_System")

class NodeType(Enum):
    """定义CFG中的节点类型枚举"""
    ENTRY = "entry"
    EXIT = "exit"
    ACTION = "action"       # 顺序执行
    CONDITION = "condition" # 条件分支
    LOOP = "loop"           # 循环结构
    MERGE = "merge"         # 汇聚点

@dataclass
class SemanticNode:
    """
    语义节点数据结构
    包含节点的文本内容、语义向量以及编译器属性。
    """
    node_id: str
    text_content: str
    embedding: Optional[np.ndarray] = None
    node_type: NodeType = NodeType.ACTION
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 数据验证：确保node_id不为空
        if not self.node_id:
            raise ValueError("Node ID cannot be empty")

class StructuredNeuralIRSystem:
    """
    结构化神经中间表示系统核心类。
    负责构建逻辑图、执行结构化编码以及检测逻辑异常。
    """

    def __init__(self, vector_dim: int = 128, anomaly_threshold: float = 0.85):
        """
        初始化系统。

        Args:
            vector_dim (int): 语义向量的维度。
            anomaly_threshold (float): 判断逻辑不一致的余弦相似度阈值。
        """
        if vector_dim <= 0:
            raise ValueError("Vector dimension must be positive.")
        
        self.vector_dim = vector_dim
        self.anomaly_threshold = anomaly_threshold
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, SemanticNode] = {}
        
        logger.info(f"SNIR System initialized with dim={vector_dim}, threshold={anomaly_threshold}")

    def _validate_vector(self, vector: np.ndarray) -> bool:
        """
        辅助函数：验证向量维度和类型。
        
        Args:
            vector (np.ndarray): 输入向量
            
        Returns:
            bool: 是否合法
        """
        if vector is None:
            return False
        if not isinstance(vector, np.ndarray):
            logger.error("Invalid type: Embedding must be a numpy array.")
            return False
        if vector.shape[0] != self.vector_dim:
            logger.error(f"Dimension mismatch: Expected {self.vector_dim}, got {vector.shape[0]}")
            return False
        return True

    def add_semantic_node(self, node: SemanticNode) -> bool:
        """
        向系统中添加语义节点。
        如果节点没有提供Embedding，则自动生成随机向量（模拟）。
        
        Args:
            node (SemanticNode): 语义节点对象
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if node.node_id in self.nodes:
                logger.warning(f"Node {node.node_id} already exists. Overwriting.")
            
            # 如果没有提供向量，生成模拟向量（实际场景应调用BERT等模型）
            if node.embedding is None:
                node.embedding = np.random.randn(self.vector_dim).astype(np.float32)
                node.embedding = node.embedding / np.linalg.norm(node.embedding) # L2 归一化
            
            if not self._validate_vector(node.embedding):
                return False

            self.nodes[node.node_id] = node
            self.graph.add_node(node.node_id, data=node)
            logger.debug(f"Added node: {node.node_id} ({node.node_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding node {node.node_id}: {str(e)}")
            return False

    def add_control_flow_edge(self, source_id: str, target_id: str, flow_type: str = "sequential"):
        """
        添加控制流边，构建逻辑结构。
        
        Args:
            source_id (str): 源节点ID
            target_id (str): 目标节点ID
            flow_type (str): 边的类型 (e.g., 'true_branch', 'false_branch', 'sequential')
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Source or Target node does not exist.")
        
        self.graph.add_edge(source_id, target_id, type=flow_type)
        logger.info(f"Added edge: {source_id} -> {target_id} ({flow_type})")

    def _get_structural_weight(self, source_type: NodeType, target_type: NodeType) -> float:
        """
        辅助函数：根据控制流类型计算结构化权重。
        用于调整向量在传播过程中的影响力。
        """
        # 简单的启发式规则：循环和条件分支具有更高的逻辑权重
        if source_type == NodeType.LOOP:
            return 1.5
        elif source_type == NodeType.CONDITION:
            return 1.2
        return 1.0

    def generate_structural_embeddings(self) -> Dict[str, np.ndarray]:
        """
        核心函数：生成结构化神经中间表示。
        
        将控制流图(CFG)的拓扑结构融入语义向量。
        算法：基于随机游走的聚合，将邻居节点的语义信息和边的逻辑权重合并到当前节点。
        
        Returns:
            Dict[str, np.ndarray]: 包含每个节点融合后向量的字典。
        """
        if not self.graph.nodes:
            logger.warning("Graph is empty. Cannot generate embeddings.")
            return {}

        structural_embeddings = {}
        alpha = 0.7 # 保留原始语义的比例

        logger.info("Starting structural embedding generation...")
        
        try:
            # 计算图的入度矩阵等（此处简化处理，逐节点聚合）
            for node_id in self.graph.nodes():
                node = self.nodes[node_id]
                original_vec = node.embedding
                
                # 聚合前驱节点信息（数据流/控制流来源）
                neighbors = list(self.graph.predecessors(node_id))
                if not neighbors:
                    structural_embeddings[node_id] = original_vec
                    continue
                
                aggregated_vec = np.zeros(self.vector_dim, dtype=np.float32)
                total_weight = 0.0
                
                for pred_id in neighbors:
                    pred_node = self.nodes[pred_id]
                    edge_data = self.graph.get_edge_data(pred_id, node_id)
                    
                    # 获取结构权重
                    weight = self._get_structural_weight(pred_node.node_type, node.node_type)
                    
                    # 这里简化了向量聚合：实际可能需要Attention机制或GNN
                    # 使用门控机制模拟：如果前驱是循环，强调重复出现的语义
                    aggregated_vec += pred_node.embedding * weight
                    total_weight += weight
                
                if total_weight > 0:
                    aggregated_vec /= total_weight
                    
                # 融合：原始向量 + 聚合的上下文向量
                fused_vec = (alpha * original_vec) + ((1 - alpha) * aggregated_vec)
                # 归一化
                norm = np.linalg.norm(fused_vec)
                if norm > 0:
                    fused_vec = fused_vec / norm
                    
                structural_embeddings[node_id] = fused_vec

            logger.info("Structural embedding generation complete.")
            return structural_embeddings

        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            raise

    def detect_logic_vulnerabilities(self, structural_embeddings: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        核心函数：基于结构化表示检测逻辑漏洞。
        
        逻辑：如果两个节点在控制流上是互斥或因果关系，但在语义向量空间中
        却高度相似（或方向冲突），则可能存在逻辑漏洞（如死代码、矛盾条款）。
        
        Args:
            structural_embeddings (Dict[str, np.ndarray]): generate_structural_embeddings的输出
            
        Returns:
            List[Dict]: 检测到的异常列表
        """
        vulnerabilities = []
        logger.info("Scanning for logical vulnerabilities...")

        # 示例逻辑：检测互斥分支的语义一致性
        # 寻找CONDITION节点，并检查其TRUE和FALSE分支的后续节点
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.CONDITION:
                successors = list(self.graph.successors(node_id))
                if len(successors) < 2:
                    continue
                
                # 假设前两个后继是True/False分支
                s1_id, s2_id = successors[0], successors[1]
                if s1_id in structural_embeddings and s2_id in structural_embeddings:
                    v1 = structural_embeddings[s1_id]
                    v2 = structural_embeddings[s2_id]
                    
                    # 计算余弦相似度
                    similarity = np.dot(v1, v2) # 已归一化，点积即余弦
                    
                    # 如果互斥分支的语义过于相似，可能意味着逻辑冗余或复制粘贴错误
                    if similarity > self.anomaly_threshold:
                        vuln = {
                            "type": "Redundant Logic in Mutually Exclusive Paths",
                            "location": f"Branches of Condition '{node_id}'",
                            "details": f"High semantic similarity ({similarity:.4f}) detected between supposedly divergent paths.",
                            "involved_nodes": [s1_id, s2_id]
                        }
                        vulnerabilities.append(vuln)
                        logger.warning(f"Vulnerability found: {vuln['type']} at {node_id}")

        return vulnerabilities

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化系统
    snir = StructuredNeuralIRSystem(vector_dim=64, anomaly_threshold=0.90)
    
    # 2. 模拟法律合同场景：构建节点
    # 节点A: 定义了"不可抗力"条款
    node_a = SemanticNode(
        node_id="clause_force_majeure", 
        text_content="If force majeure occurs, the contract is suspended.", 
        node_type=NodeType.CONDITION
    )
    
    # 节点B: 暂停执行逻辑
    node_b = SemanticNode(
        node_id="action_suspend", 
        text_content="Suspend all delivery obligations immediately.", 
        node_type=NodeType.ACTION
    )
    
    # 节点C: 正常执行逻辑
    node_c = SemanticNode(
        node_id="action_continue", 
        text_content="Continue standard delivery operations.", 
        node_type=NodeType.ACTION
    )
    
    # 节点D: 循环检查
    node_d = SemanticNode(
        node_id="loop_check_status", 
        text_content="Check if force majeure status has changed.", 
        node_type=NodeType.LOOP
    )

    # 添加节点
    snir.add_semantic_node(node_a)
    snir.add_semantic_node(node_b)
    snir.add_semantic_node(node_c)
    snir.add_semantic_node(node_d)

    # 3. 构建控制流
    # A -> B (True branch)
    snir.add_control_flow_edge("clause_force_majeure", "action_suspend", flow_type="true_branch")
    # A -> C (False branch)
    snir.add_control_flow_edge("clause_force_majeure", "action_continue", flow_type="false_branch")
    # B -> D (Loop back)
    snir.add_control_flow_edge("action_suspend", "loop_check_status")
    snir.add_control_flow_edge("loop_check_status", "clause_force_majeure")

    # 4. 生成结构化向量
    embeddings = snir.generate_structural_embeddings()
    
    # 5. 检测漏洞
    # 此处 B 和 C 是互斥的，如果它们文本太像，系统会报警
    # 为演示效果，我们假设 B 和 C 的随机向量相似度极高（或实际文本非常像）
    issues = snir.detect_logic_vulnerabilities(embeddings)
    
    print(f"\nDetected {len(issues)} potential logic issues.")
    for issue in issues:
        print(f"- {issue['type']}: {issue['details']}")