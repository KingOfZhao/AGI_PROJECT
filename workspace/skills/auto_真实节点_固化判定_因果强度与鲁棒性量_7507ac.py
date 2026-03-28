"""
模块: auto_真实节点_固化判定_因果强度与鲁棒性量化
描述: 实现AGI系统中"真实节点"的自动化固化判定。通过量化因果强度和工况鲁棒性，
      决定一个知识单元是否从"假设"升级为"真实节点"。
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """知识节点的当前状态枚举"""
    HYPOTHETICAL = "hypothetical"  # 假设性节点
    CANDIDATE = "candidate"        # 候选节点
    SOLIDIFIED = "solidified"      # 已固化真实节点
    REJECTED = "rejected"          # 被拒绝的节点

@dataclass
class ValidationScenario:
    """单一验证工况的数据结构"""
    scenario_id: str
    temperature: float      # 温度（摄氏度）
    load: float             # 负载（百分比 0.0-1.0）
    noise_level: float      # 环境噪声水平 (0.0-1.0)
    input_val: float        # 输入变量
    output_val: float       # 输出变量
    expected_output: float  # 期望输出（用于误差计算）

@dataclass
class KnowledgeNode:
    """知识节点数据结构"""
    node_id: str
    description: str
    history: List[ValidationScenario] = field(default_factory=list)
    status: NodeStatus = NodeStatus.HYPOTHETICAL
    causal_strength: float = 0.0
    robustness_score: float = 0.0

def calculate_causal_strength(
    input_data: np.ndarray, 
    output_data: np.ndarray
) -> float:
    """
    计算输入对输出的因果强度（基于简单的相关性/回归系数简化模型）。
    
    在实际AGI场景中，此处应替换为结构因果模型或Do-calculus计算。
    这里使用Pearson相关系数的绝对值作为因果强度的代理指标。
    
    Args:
        input_data (np.ndarray): 输入变量数组
        output_data (np.ndarray): 输出变量数组
        
    Returns:
        float: 因果强度值 [0, 1]
        
    Raises:
        ValueError: 如果输入数据长度不匹配或为空
    """
    if len(input_data) == 0 or len(output_data) == 0:
        raise ValueError("输入数据不能为空")
    if len(input_data) != len(output_data):
        raise ValueError("输入输出数据长度必须一致")
        
    # 数据标准化处理
    x = input_data.astype(float)
    y = output_data.astype(float)
    
    # 计算相关系数矩阵
    corr_matrix = np.corrcoef(x, y)
    # 相关系数范围是 -1 到 1，取绝对值代表强度
    strength = abs(corr_matrix[0, 1])
    
    return strength if not np.isnan(strength) else 0.0

def calculate_robustness(
    scenarios: List[ValidationScenario], 
    error_tolerance: float = 0.1
) -> float:
    """
    计算节点在不同工况下的鲁棒性分数。
    
    通过分析不同温度、负载下的输出误差方差来量化鲁棒性。
    误差波动越小，环境因子对结果影响越小，鲁棒性越高。
    
    Args:
        scenarios (List[ValidationScenario]): 验证工况列表
        error_tolerance (float): 允许的误差标准差阈值
        
    Returns:
        float: 鲁棒性分数 [0, 1]
    """
    if not scenarios:
        return 0.0
    
    # 计算相对误差
    errors = []
    for s in scenarios:
        if abs(s.expected_output) < 1e-6:
            continue # 避免除零
        relative_error = abs(s.output_val - s.expected_output) / abs(s.expected_output)
        errors.append(relative_error)
    
    if not errors:
        return 0.0
    
    # 计算误差的标准差，波动越小鲁棒性越高
    std_dev = np.std(errors)
    
    # 将标准差映射到 0-1 分数 (这里使用简单的指数衰减映射)
    # 标准差越小，分数越接近 1
    score = np.exp(-std_dev / error_tolerance)
    
    return float(np.clip(score, 0.0, 1.0))

def check_environment_diversity(
    scenarios: List[ValidationScenario], 
    min_unique_conditions: int = 3
) -> bool:
    """
    辅助函数：检查验证工况是否满足环境多样性要求。
    
    要求工况在温度、负载或噪声水平上存在显著差异，防止过拟合特定环境。
    
    Args:
        scenarios (List[ValidationScenario]): 验证工况列表
        min_unique_conditions (int): 最少需要的不同工况数量
        
    Returns:
        bool: 是否满足多样性标准
    """
    unique_conditions = set()
    
    for s in scenarios:
        # 将连续变量离散化为桶，以判断是否为不同工况
        # 温度按10度分桶，负载按20%分桶
        temp_bucket = int(s.temperature // 10)
        load_bucket = int(s.load // 0.2)
        noise_bucket = int(s.noise_level // 0.2)
        
        condition_key = (temp_bucket, load_bucket, noise_bucket)
        unique_conditions.add(condition_key)
        
    return len(unique_conditions) >= min_unique_conditions

def evaluate_node_solidification(
    node: KnowledgeNode,
    causal_threshold: float = 0.85,
    robustness_threshold: float = 0.75,
    min_samples: int = 5
) -> Tuple[NodeStatus, Dict[str, float]]:
    """
    核心函数：评估节点是否满足固化条件。
    
    综合计算因果强度、鲁棒性分数，并结合工况多样性进行最终判定。
    
    Args:
        node (KnowledgeNode): 待评估的知识节点
        causal_threshold (float): 因果强度阈值
        robustness_threshold (float): 鲁棒性阈值
        min_samples (int): 最少验证样本数
        
    Returns:
        Tuple[NodeStatus, Dict[str, float]]: 
            返回更新后的状态以及包含各项指标的字典。
            
    Raises:
        TypeError: 输入节点类型错误
    """
    if not isinstance(node, KnowledgeNode):
        raise TypeError("输入必须是 KnowledgeNode 类型")
        
    metrics = {
        "causal_strength": 0.0,
        "robustness_score": 0.0,
        "sample_count": len(node.history),
        "diversity_pass": False
    }
    
    logger.info(f"开始评估节点: {node.node_id} - {node.description}")
    
    # 1. 边界检查：样本数量是否足够
    if len(node.history) < min_samples:
        logger.warning(f"样本数量不足 ({len(node.history)} < {min_samples})，保持假设状态。")
        return NodeStatus.HYPOTHETICAL, metrics
    
    # 2. 检查工况多样性
    if not check_environment_diversity(node.history):
        logger.warning("工况多样性不足，无法证明通用性。")
        return NodeStatus.CANDIDATE, metrics # 标记为候选，但暂不固化
    
    metrics["diversity_pass"] = True
    
    # 3. 准备数据
    inputs = np.array([s.input_val for s in node.history])
    outputs = np.array([s.output_val for s in node.history])
    
    try:
        # 4. 计算因果强度
        causal_score = calculate_causal_strength(inputs, outputs)
        metrics["causal_strength"] = causal_score
        
        # 5. 计算鲁棒性
        robust_score = calculate_robustness(node.history)
        metrics["robustness_score"] = robust_score
        
        logger.info(f"计算结果 -> 因果强度: {causal_score:.4f}, 鲁棒性: {robust_score:.4f}")
        
        # 6. 判定逻辑
        if (causal_score >= causal_threshold and 
            robust_score >= robustness_threshold):
            logger.info(f"节点 {node.node_id} 判定为 '真实节点' (已固化)。")
            return NodeStatus.SOLIDIFIED, metrics
        else:
            logger.info("节点指标未达到固化阈值。")
            return NodeStatus.CANDIDATE, metrics
            
    except Exception as e:
        logger.error(f"计算过程中发生错误: {str(e)}")
        return NodeStatus.REJECTED, metrics

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟生成测试数据
    mock_history = [
        ValidationScenario("s1", 25.0, 0.5, 0.1, 10.0, 20.1, 20.0),
        ValidationScenario("s2", 40.0, 0.8, 0.3, 15.0, 30.2, 30.0), # 高温高负载
        ValidationScenario("s3", 10.0, 0.2, 0.0, 5.0,  10.05, 10.0), # 低温低负载
        ValidationScenario("s4", 60.0, 0.9, 0.5, 20.0, 40.5, 40.0), # 极端工况
        ValidationScenario("s5", 25.0, 0.5, 0.2, 12.0, 24.1, 24.0), # 重复工况验证
    ]
    
    # 创建一个待评估的节点
    test_node = KnowledgeNode(
        node_id="KN_7507ac_01",
        description="工业电机转速与扭矩的线性关系假设",
        history=mock_history
    )
    
    # 执行评估
    final_status, metrics = evaluate_node_solidification(
        test_node,
        causal_threshold=0.90, # 设定较高阈值
        robustness_threshold=0.80
    )
    
    # 输出结果
    print("-" * 30)
    print(f"最终状态: {final_status.value}")
    print(f"详细指标: {metrics}")
    print("-" * 30)