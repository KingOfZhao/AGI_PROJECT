"""
自上而下的好奇心驱动探索策略模块

该模块实现了一个基于信息熵的好奇心驱动探索系统，AI能够自主识别知识网络中的
高不确定性区域（稀疏区），并生成内部奖励信号驱动探索行为，而非依赖外部输入。

核心功能：
1. 评估知识网络的信息熵分布
2. 识别高不确定性区域（稀疏区）
3. 生成探索性内部奖励信号
4. 动态调整探索策略

输入数据格式：
    - knowledge_network: Dict[str, np.ndarray] 知识节点的特征表示
    - exploration_history: List[str] 已探索节点的历史记录

输出数据格式：
    - exploration_report: Dict 包含目标区域、奖励值和熵值分析
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from collections import defaultdict
import time
from dataclasses import dataclass

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CuriosityDrivenExplorer")


@dataclass
class ExplorationTarget:
    """探索目标数据结构"""
    region_id: str
    uncertainty_score: float
    novelty_score: float
    exploration_priority: float


class KnowledgeNetworkAnalyzer:
    """知识网络分析器，计算网络中的信息熵分布"""
    
    def __init__(self, entropy_threshold: float = 0.7):
        """
        初始化分析器
        
        Args:
            entropy_threshold: 熵值阈值，超过此值认为区域是稀疏的
        """
        self.entropy_threshold = entropy_threshold
        self.region_entropy_cache = {}
        logger.info("KnowledgeNetworkAnalyzer initialized with threshold %.2f", entropy_threshold)
    
    def compute_region_entropy(self, region_features: np.ndarray) -> float:
        """
        计算特定知识区域的熵值（不确定性度量）
        
        使用基于概率分布的信息熵计算方法，归一化到[0,1]范围
        
        Args:
            region_features: 区域特征矩阵，shape=(n_samples, n_features)
            
        Returns:
            float: 归一化后的熵值 [0, 1]
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not isinstance(region_features, np.ndarray):
            raise ValueError("Input must be numpy array")
            
        if region_features.size == 0:
            logger.warning("Empty region features provided")
            return 0.0
            
        try:
            # 计算特征维度上的标准差作为稀疏性指标
            std_dev = np.std(region_features, axis=0)
            mean_std = np.mean(std_dev)
            
            # 使用sigmoid函数归一化到[0,1]
            entropy = 1 / (1 + np.exp(-mean_std))
            
            # 缓存结果
            cache_key = hash(region_features.tobytes())
            self.region_entropy_cache[cache_key] = entropy
            
            return float(entropy)
            
        except Exception as e:
            logger.error("Entropy computation failed: %s", str(e))
            raise RuntimeError(f"Entropy computation error: {e}") from e
    
    def identify_sparse_regions(
        self, 
        knowledge_network: Dict[str, np.ndarray]
    ) -> List[Tuple[str, float]]:
        """
        识别知识网络中的稀疏区域（高熵区域）
        
        Args:
            knowledge_network: 知识网络字典 {区域ID: 特征矩阵}
            
        Returns:
            List[Tuple[str, float]]: 稀疏区域列表，按熵值降序排列 [(区域ID, 熵值)]
        """
        if not knowledge_network:
            logger.warning("Empty knowledge network provided")
            return []
            
        sparse_regions = []
        
        for region_id, features in knowledge_network.items():
            try:
                entropy = self.compute_region_entropy(features)
                if entropy >= self.entropy_threshold:
                    sparse_regions.append((region_id, entropy))
                    logger.debug(
                        "Sparse region detected: %s (entropy=%.3f)", 
                        region_id, entropy
                    )
            except Exception as e:
                logger.warning(
                    "Skipping region %s due to error: %s", 
                    region_id, str(e)
                )
                continue
                
        # 按熵值降序排序
        sparse_regions.sort(key=lambda x: x[1], reverse=True)
        return sparse_regions


class CuriosityDrivenExplorer:
    """好奇心驱动的探索代理，生成内部奖励指导探索"""
    
    def __init__(
        self, 
        base_reward: float = 1.0,
        novelty_weight: float = 0.6,
        uncertainty_weight: float = 0.4
    ):
        """
        初始化探索代理
        
        Args:
            base_reward: 基础奖励值
            novelty_weight: 新颖性奖励的权重
            uncertainty_weight: 不确定性奖励的权重
        """
        self.analyzer = KnowledgeNetworkAnalyzer()
        self.exploration_history = defaultdict(int)
        self.base_reward = base_reward
        self.novelty_weight = novelty_weight
        self.uncertainty_weight = uncertainty_weight
        
        # 验证权重参数
        if not (0 <= novelty_weight <= 1) or not (0 <= uncertainty_weight <= 1):
            raise ValueError("Weights must be in range [0, 1]")
            
        logger.info(
            "CuriosityDrivenExplorer initialized with weights (novelty=%.2f, uncertainty=%.2f)",
            novelty_weight, uncertainty_weight
        )
    
    def compute_novelty_score(self, region_id: str) -> float:
        """
        计算区域的新颖性分数（探索频率的反比）
        
        Args:
            region_id: 区域标识符
            
        Returns:
            float: 新颖性分数 [0, 1]，1表示完全未探索
        """
        visit_count = self.exploration_history[region_id]
        # 使用指数衰减函数
        novelty = np.exp(-0.1 * visit_count)
        return float(novelty)
    
    def generate_internal_reward(
        self, 
        region_id: str, 
        uncertainty_score: float
    ) -> float:
        """
        生成内部奖励信号，结合不确定性和新颖性
        
        Args:
            region_id: 目标区域ID
            uncertainty_score: 区域的不确定性分数
            
        Returns:
            float: 内部奖励值
        """
        # 数据验证
        if not isinstance(uncertainty_score, (int, float)):
            raise TypeError("Uncertainty score must be numeric")
        if not 0 <= uncertainty_score <= 1:
            logger.warning(
                "Uncertainty score %.2f out of range, clamping to [0,1]",
                uncertainty_score
            )
            uncertainty_score = np.clip(uncertainty_score, 0, 1)
            
        novelty = self.compute_novelty_score(region_id)
        reward = self.base_reward * (
            self.novelty_weight * novelty + 
            self.uncertainty_weight * uncertainty_score
        )
        
        logger.debug(
            "Reward generated for %s: %.3f (novelty=%.2f, uncertainty=%.2f)",
            region_id, reward, novelty, uncertainty_score
        )
        return float(reward)
    
    def select_exploration_target(
        self, 
        knowledge_network: Dict[str, np.ndarray]
    ) -> Optional[ExplorationTarget]:
        """
        选择下一个探索目标，基于好奇心驱动策略
        
        Args:
            knowledge_network: 知识网络字典
            
        Returns:
            ExplorationTarget: 选中的探索目标，如果无合适目标则返回None
        """
        # 识别稀疏区域
        sparse_regions = self.analyzer.identify_sparse_regions(knowledge_network)
        
        if not sparse_regions:
            logger.info("No sparse regions found for exploration")
            return None
            
        # 评估所有候选区域
        candidates = []
        for region_id, uncertainty in sparse_regions:
            novelty = self.compute_novelty_score(region_id)
            priority = (
                self.novelty_weight * novelty + 
                self.uncertainty_weight * uncertainty
            )
            candidates.append(ExplorationTarget(
                region_id=region_id,
                uncertainty_score=uncertainty,
                novelty_score=novelty,
                exploration_priority=priority
            ))
            
        # 选择优先级最高的目标
        target = max(candidates, key=lambda x: x.exploration_priority)
        
        # 更新探索历史
        self.exploration_history[target.region_id] += 1
        
        logger.info(
            "Selected exploration target: %s (priority=%.3f)",
            target.region_id, target.exploration_priority
        )
        return target
    
    def explore_and_learn(
        self, 
        knowledge_network: Dict[str, np.ndarray],
        max_iterations: int = 5
    ) -> Dict[str, float]:
        """
        执行好奇心驱动的探索循环
        
        Args:
            knowledge_network: 知识网络
            max_iterations: 最大探索迭代次数
            
        Returns:
            Dict[str, float]: 探索报告 {区域ID: 获得的奖励}
        """
        if max_iterations < 1:
            raise ValueError("Max iterations must be positive")
            
        exploration_report = {}
        
        for i in range(max_iterations):
            target = self.select_exploration_target(knowledge_network)
            if target is None:
                logger.info("Exploration completed: no more targets")
                break
                
            # 生成内部奖励
            reward = self.generate_internal_reward(
                target.region_id, 
                target.uncertainty_score
            )
            
            exploration_report[target.region_id] = reward
            
            # 模拟探索后知识更新（实际应用中这里会获取新数据）
            # 这里我们简化为增加区域数据的多样性
            if target.region_id in knowledge_network:
                current_data = knowledge_network[target.region_id]
                noise = np.random.normal(0, 0.1, current_data.shape)
                knowledge_network[target.region_id] = current_data + noise
                
            logger.info(
                "Exploration iteration %d/%d: %s (reward=%.3f)",
                i+1, max_iterations, target.region_id, reward
            )
            
        return exploration_report


def create_sample_knowledge_network(
    num_regions: int = 10, 
    samples_per_region: int = 50
) -> Dict[str, np.ndarray]:
    """
    辅助函数：创建模拟知识网络用于测试
    
    Args:
        num_regions: 区域数量
        samples_per_region: 每个区域的样本数
        
    Returns:
        Dict[str, np.ndarray]: 模拟知识网络
    """
    network = {}
    for i in range(num_regions):
        # 随机生成不同稀疏度的区域
        if i < num_regions // 3:
            # 稀疏区域（高熵）
            data = np.random.randn(samples_per_region, 10) * 2.0
        else:
            # 稠密区域（低熵）
            data = np.random.randn(samples_per_region, 10) * 0.2
            
        network[f"region_{i}"] = data
    return network


if __name__ == "__main__":
    # 使用示例
    print("=== 自上而下的好奇心驱动探索策略演示 ===")
    
    # 1. 创建知识网络和探索代理
    knowledge_net = create_sample_knowledge_network()
    explorer = CuriosityDrivenExplorer(
        novelty_weight=0.7,
        uncertainty_weight=0.3
    )
    
    # 2. 执行探索循环
    print("\n开始探索循环...")
    report = explorer.explore_and_learn(knowledge_net, max_iterations=3)
    
    # 3. 输出探索报告
    print("\n探索报告:")
    for region, reward in report.items():
        print(f"{region}: 内部奖励 = {reward:.3f}")
    
    # 4. 分析熵分布
    print("\n知识网络熵分布分析:")
    analyzer = KnowledgeNetworkAnalyzer()
    for region_id, features in knowledge_net.items():
        entropy = analyzer.compute_region_entropy(features)
        print(f"{region_id}: 熵值 = {entropy:.3f}")