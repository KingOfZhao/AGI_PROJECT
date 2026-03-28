"""
Module: auto_perceptual_boundary_probe_909750
Description: 自动感知边界探测模块。

该模块用于在现有的SKILL节点空间中进行主动学习。
它不仅仅是生成随机噪声，而是试图构建“对抗性输入”或“边界用例”，
目的是最大化系统的不确定性（熵），从而识别出感知模型中的盲区。

This module is designed for Active Learning pipelines within an AGI context.
It generates adversarial inputs to probe the decision boundaries of skill nodes.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    技能节点的数据结构表示。
    
    Attributes:
        id (str): 节点的唯一标识符。
        embedding (np.ndarray): 节点的语义嵌入向量 (e.g., 768-dim vector).
        metadata (Dict[str, Any]): 包含节点描述或标签的元数据。
    """
    id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证：确保嵌入向量是numpy数组且非空。"""
        if not isinstance(self.embedding, np.ndarray):
            raise TypeError(f"Node {self.id}: embedding must be a numpy array.")
        if self.embedding.size == 0:
            raise ValueError(f"Node {self.id}: embedding cannot be empty.")

class PerceptualBoundaryProber:
    """
    自动感知边界探测器。
    
    该类封装了基于现有SKILL节点生成高熵值输入的逻辑。
    核心思想是在向量空间中寻找“无人区”或“模糊地带”，
    并生成能够触发这些区域的对抗性输入。
    """

    def __init__(self, skill_nodes: List[SkillNode], embedding_dim: int = 768):
        """
        初始化探测器。
        
        Args:
            skill_nodes (List[SkillNode]): 现有的SKILL节点列表。
            embedding_dim (int): 向量空间的维度。
        """
        if not skill_nodes:
            raise ValueError("Input skill_nodes list cannot be empty.")
        
        self.skill_nodes = skill_nodes
        self.embedding_dim = embedding_dim
        self.node_matrix = self._build_node_matrix()
        logger.info(f"Initialized Prober with {len(skill_nodes)} nodes.")

    def _build_node_matrix(self) -> np.ndarray:
        """
        辅助函数：构建节点向量矩阵以便于批量计算。
        
        Returns:
            np.ndarray: 形状为 (N, D) 的矩阵，N为节点数，D为维度。
        """
        try:
            matrix = np.stack([node.embedding for node in self.skill_nodes])
            return matrix
        except ValueError as e:
            logger.error(f"Failed to stack embeddings. Ensure all have same dimension: {e}")
            raise

    def _calculate_entropy_score(self, distances: np.ndarray) -> float:
        """
        辅助函数：基于距离分布计算不确定性分数（伪熵）。
        
        如果一个点到所有SKILL节点的距离都非常相似（即处于中心等距位置），
        则系统很难将其归类为某一特定技能，此时熵值最高。
        
        Args:
            distances (np.ndarray): 输入点到所有节点的距离数组。
            
        Returns:
            float: 归一化的不确定性分数 [0, 1]。
        """
        # 使用距离的倒数作为相似度
        sim = 1 / (distances + 1e-8)
        # 归一化为概率分布
        prob = sim / np.sum(sim)
        # 计算信息熵
        entropy = -np.sum(prob * np.log(prob + 1e-10))
        # 归一化 (粗略估计最大熵为 log(N))
        max_entropy = np.log(len(self.skill_nodes))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def generate_adversarial_input(
        self, 
        num_samples: int = 1, 
        temperature: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        核心函数：生成对抗性输入向量。
        
        策略：
        1. 随机选择两个或多个在语义空间中距离较近但属于不同簇的节点。
        2. 在它们的连线上或混合区域生成扰动点。
        3. 或者生成处于整个系统“质心”附近的点（最大模糊区）。
        
        Args:
            num_samples (int): 需要生成的样本数量。
            temperature (float): 控制生成样本的边界激进程度 (0.0 - 1.0)。
            
        Returns:
            List[Dict[str, Any]]: 包含生成向量及其元数据的字典列表。
        """
        if not 0.0 <= temperature <= 1.0:
            logger.warning("Temperature should be between 0 and 1. Clamping.")
            temperature = np.clip(temperature, 0.0, 1.0)

        generated_samples = []
        
        for _ in range(num_samples):
            # 策略A: 寻找高熵区域 (随机游走寻找最小置信度点)
            # 初始化一个随机向量作为起点
            current_vector = np.random.randn(self.embedding_dim)
            current_vector = current_vector / np.linalg.norm(current_vector)
            
            # 简单的模拟退火/梯度上升寻找高熵区
            # 在实际AGI场景中，这里应使用生成模型或优化器
            best_vector = current_vector
            best_score = 0.0
            
            for _ in range(10): # 迭代优化
                # 计算到所有节点的距离
                dists = np.linalg.norm(self.node_matrix - current_vector, axis=1)
                score = self._calculate_entropy_score(dists)
                
                if score > best_score:
                    best_score = score
                    best_vector = current_vector
                
                # 随机扰动
                perturbation = np.random.randn(self.embedding_dim) * 0.1 * temperature
                current_vector = best_vector + perturbation
                # 保持模长一致（假设在单位球面上）
                current_vector = current_vector / (np.linalg.norm(current_vector) + 1e-9)

            sample = {
                "id": str(uuid.uuid4()),
                "vector": best_vector,
                "uncertainty_score": best_score,
                "generation_timestamp": datetime.utcnow().isoformat(),
                "type": "adversarial_probe"
            }
            generated_samples.append(sample)
            
        logger.info(f"Generated {num_samples} adversarial samples. Avg Score: {np.mean([s['uncertainty_score'] for s in generated_samples]):.4f}")
        return generated_samples

    def evaluate_blind_spots(
        self, 
        test_inputs: List[np.ndarray], 
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        核心函数：评估给定输入集合并识别感知盲区。
        
        分析输入向量，如果它们在现有节点空间中产生高熵值，
        则将其标记为潜在的“盲区”或“未覆盖区域”。
        
        Args:
            test_inputs (List[np.ndarray]): 待测试的输入向量列表。
            threshold (float): 判定为盲区的不确定性阈值。
            
        Returns:
            Dict[str, Any]: 包含盲区分析报告的字典。
        """
        if not test_inputs:
            raise ValueError("Test inputs list cannot be empty.")

        blind_spots = []
        
        for idx, vec in enumerate(test_inputs):
            if vec.shape[0] != self.embedding_dim:
                logger.warning(f"Input vector at index {idx} has wrong dimension. Skipping.")
                continue

            # 计算距离
            dists = np.linalg.norm(self.node_matrix - vec, axis=1)
            min_dist = np.min(dists)
            entropy = self._calculate_entropy_score(dists)
            
            if entropy > threshold:
                blind_spots.append({
                    "input_index": idx,
                    "uncertainty": entropy,
                    "nearest_node_distance": min_dist,
                    "status": "BLIND_SPOT_DETECTED"
                })

        report = {
            "total_inputs_analyzed": len(test_inputs),
            "blind_spot_count": len(blind_spots),
            "threshold_used": threshold,
            "details": blind_spots
        }
        
        logger.info(f"Evaluated {len(test_inputs)} inputs. Found {len(blind_spots)} potential blind spots.")
        return report

# Usage Example
if __name__ == "__main__":
    # 1. 模拟生成1047个SKILL节点数据
    NUM_NODES = 1047
    DIM = 128 # 使用较小的维度进行演示
    
    # 创建一些模拟的聚类中心
    centers = np.random.rand(10, DIM) * 10
    mock_nodes = []
    
    for i in range(NUM_NODES):
        # 随机选择一个中心并添加噪声，模拟真实的技能聚类
        center_idx = i % 10
        noise = np.random.randn(DIM) * 0.5
        vec = centers[center_idx] + noise
        
        node = SkillNode(
            id=f"skill_{i}",
            embedding=vec,
            metadata={"category": f"cluster_{center_idx}"}
        )
        mock_nodes.append(node)

    # 2. 初始化探测器
    try:
        prober = PerceptualBoundaryProber(skill_nodes=mock_nodes, embedding_dim=DIM)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        exit(1)

    # 3. 生成对抗性输入（探测盲区）
    # 目标：生成5个系统最“困惑”的输入向量
    adversarial_inputs_data = prober.generate_adversarial_input(num_samples=5, temperature=0.8)
    
    print("\n--- Generated Adversarial Inputs ---")
    for item in adversarial_inputs_data:
        print(f"ID: {item['id']}, Uncertainty: {item['uncertainty_score']:.4f}")

    # 4. 验证：手动创建一些已知区域内的点和未知区域的点进行测试
    test_vectors = [item['vector'] for item in adversarial_inputs_data]
    
    # 添加一些已知点（在现有节点附近）
    test_vectors.append(mock_nodes[0].embedding) # 确定性应该很高（熵低）
    test_vectors.append(mock_nodes[100].embedding + np.random.randn(DIM) * 0.1) # 确定性较高

    # 5. 评估盲区
    analysis_report = prober.evaluate_blind_spots(test_vectors, threshold=0.7)
    
    print("\n--- Blind Spot Analysis Report ---")
    print(f"Total Analyzed: {analysis_report['total_inputs_analyzed']}")
    print(f"Blind Spots Found: {analysis_report['blind_spot_count']}")