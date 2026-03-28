"""
模块: auto_intent_solidification
名称: auto_如何通过人机共生机制实现意图的结构化固化_e5b2fe
描述: 实现基于人机共生机制的意图固化系统。通过组合已验证的代码片段（真实节点），
     利用人类的二元或选择式反馈，将修正视为“实践证伪”，从而反向修正高维意图向量。
Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class RealNode:
    """
    真实节点：代表一个已验证的、可执行的代码片段或功能模块。
    """
    id: str
    name: str
    vector: np.ndarray  # 节点的功能向量表示
    code_snippet: str   # 关联的代码片段

@dataclass
class IntentVector:
    """
    意图向量：表示当前用户意图在高维空间中的映射。
    """
    current_vector: np.ndarray
    dimensions: int
    confidence: float = 0.0

@dataclass
class CompositeSolution:
    """
    组合方案：由多个真实节点组合而成的解决方案。
    """
    nodes: List[RealNode]
    combined_vector: np.ndarray
    solution_id: str

# --- 核心类 ---

class IntentSolidificationSystem:
    """
    人机共生意图固化系统。
    
    通过不断的提出方案-反馈-修正循环，将模糊的意图转化为确定的结构化代码。
    核心机制：
    1. 基于当前意图向量检索真实节点。
    2. 生成组合方案供人类审核。
    3. 接收二元（是/否）或选择式反馈。
    4. 使用贝叶斯更新或梯度反向传播思想修正意图向量。
    """

    def __init__(self, node_database: List[RealNode], dimensions: int = 128):
        """
        初始化系统。
        
        Args:
            node_database: 可用的真实节点库。
            dimensions: 意图向量的维度。
        """
        if not node_database:
            raise ValueError("节点数据库不能为空")
        
        self.node_database = node_database
        self.dimensions = dimensions
        # 初始化意图向量为零向量或随机向量，代表意图未知
        self.intent = IntentVector(
            current_vector=np.zeros(dimensions),
            dimensions=dimensions
        )
        logger.info("系统初始化完成，意图空间维度: %d", dimensions)

    def generate_solution(self) -> Optional[CompositeSolution]:
        """
        核心函数1: 生成基于真实节点的组合方案。
        
        根据当前的意图向量，在节点库中寻找最匹配的节点组合。
        此处使用简化的向量余弦相似度进行检索。
        
        Returns:
            CompositeSolution: 推荐的组合方案，如果无法生成则返回None。
        """
        logger.info("正在生成新的解决方案...")
        try:
            # 计算每个节点与当前意图的相似度
            scores = []
            norm_intent = np.linalg.norm(self.intent.current_vector)
            
            if norm_intent == 0:
                # 如果意图为零向量，随机推荐初始节点
                selected_nodes = np.random.choice(self.node_database, size=min(3, len(self.node_database)), replace=False)
            else:
                # 计算相似度
                for node in self.node_database:
                    norm_node = np.linalg.norm(node.vector)
                    if norm_node == 0: continue
                    similarity = np.dot(self.intent.current_vector, node.vector) / (norm_intent * norm_node)
                    scores.append((node, similarity))
                
                # 按相似度排序并选择Top K
                scores.sort(key=lambda x: x[1], reverse=True)
                selected_nodes = [item[0] for item in scores[:3]] # 取前3个节点

            if not selected_nodes:
                logger.warning("未找到合适的节点生成方案")
                return None

            # 生成组合向量（简单的向量加和作为示例）
            combined_vec = np.sum([n.vector for n in selected_nodes], axis=0)
            
            solution = CompositeSolution(
                nodes=selected_nodes,
                combined_vector=combined_vec,
                solution_id=f"sol_{np.random.randint(10000)}"
            )
            logger.info(f"生成方案 {solution.solution_id} 包含节点: {[n.name for n in selected_nodes]}")
            return solution

        except Exception as e:
            logger.error(f"生成方案时发生错误: {str(e)}")
            return None

    def update_intent_by_feedback(
        self, 
        solution: CompositeSolution, 
        feedback_type: str, 
        feedback_data: Any
    ) -> bool:
        """
        核心函数2: 根据反馈更新意图向量（意图固化）。
        
        将人类的修正视为'实践证伪'。如果反馈为负，则意图向量远离该方案向量；
        如果为正，则靠近。这实现了意图的结构化固化。
        
        Args:
            solution: 被评价的方案。
            feedback_type: 'binary' (二元) 或 'selection' (选择式)。
            feedback_data: 具体的反馈数据 (True/False 或 节点ID)。
            
        Returns:
            bool: 更新是否成功。
        """
        logger.info(f"收到反馈 - 类型: {feedback_type}, 数据: {feedback_data}")
        learning_rate = 0.1 # 学习率/步长
        
        try:
            if feedback_type == 'binary':
                is_positive = bool(feedback_data)
                # 意图修正逻辑：Intent_new = Intent_old +/- lr * (Solution_Vec - Intent_old)
                if is_positive:
                    # 正反馈：增强现有方向
                    delta = solution.combined_vector - self.intent.current_vector
                    self.intent.current_vector += learning_rate * delta
                    self.intent.confidence = min(1.0, self.intent.confidence + 0.1)
                    logger.info("正反馈：意图向量向方案方向微调。")
                else:
                    # 负反馈（证伪）：意图向量远离该方案
                    # 这里的"远离"意味着减少该方案特征在意图中的权重
                    delta = self.intent.current_vector - solution.combined_vector
                    # 这是一个简化的'远离'逻辑，实际上是寻找正交或相反方向的调整
                    self.intent.current_vector += learning_rate * delta 
                    self.intent.confidence = max(0.0, self.intent.confidence - 0.05)
                    logger.info("负反馈（证伪）：意图向量远离当前方案。")

            elif feedback_type == 'selection':
                # 用户选择了特定的节点，意味着意图高度聚焦于该节点
                target_node = next((n for n in solution.nodes if n.id == feedback_data), None)
                if target_node:
                    self.intent.current_vector += learning_rate * (target_node.vector - self.intent.current_vector)
                    logger.info(f"选择式反馈：意图聚焦于节点 {target_node.name}")
                else:
                    logger.error("无效的选择反馈：节点ID不存在")
                    return False
            
            # 边界检查：防止向量数值溢出或归零
            self._validate_vector()
            return True

        except Exception as e:
            logger.error(f"更新意图向量失败: {str(e)}")
            return False

    def _validate_vector(self) -> None:
        """
        辅助函数: 数据验证和边界检查。
        确保意图向量在合理的数值范围内。
        """
        if not isinstance(self.intent.current_vector, np.ndarray):
            raise TypeError("意图向量必须是numpy数组")
        
        # 处理NaN或Inf值
        if np.isnan(self.intent.current_vector).any() or np.isinf(self.intent.current_vector).any():
            logger.warning("检测到非法数值(NaN/Inf)，重置意图向量")
            self.intent.current_vector = np.zeros(self.dimensions)
            
        # 归一化处理（可选，防止向量过长）
        norm = np.linalg.norm(self.intent.current_vector)
        if norm > 1e6:
            self.intent.current_vector = self.intent.current_vector / norm * 100
            logger.debug("意图向量已重新缩放")

# --- 使用示例 ---
def setup_dummy_database() -> List[RealNode]:
    """创建模拟的真实节点数据库"""
    vec_size = 128
    return [
        RealNode("n1", "Data_Loading", np.random.randn(vec_size), "def load(): pass"),
        RealNode("n2", "Image_Preprocess", np.random.randn(vec_size), "def prep_img(): pass"),
        RealNode("n3", "Model_Train", np.random.randn(vec_size), "def train(): pass"),
    ]

if __name__ == "__main__":
    # 1. 初始化
    db = setup_dummy_database()
    system = IntentSolidificationSystem(node_database=db)
    
    # 2. 第一轮交互：AI生成方案
    print("\n--- Round 1 ---")
    sol_1 = system.generate_solution()
    
    if sol_1:
        # 3. 模拟人类反馈 (Binary: False - 证伪)
        # 假设用户不喜欢这个组合
        system.update_intent_by_feedback(sol_1, 'binary', False)
        
    # 4. 第二轮交互：基于修正后的意图再次生成
    print("\n--- Round 2 ---")
    sol_2 = system.generate_solution()
    
    if sol_2:
        # 5. 模拟人类反馈 (Selection: 选择特定节点)
        if sol_2.nodes:
            system.update_intent_by_feedback(sol_2, 'selection', sol_2.nodes[0].id)
            
    print(f"\n最终意图置信度: {system.intent.confidence:.2f}")