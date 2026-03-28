"""
最小描述长度(MDL)原则下的知识节点熵减验证模块

该模块实现了基于MDL原则的知识节点验证系统，用于在AGI架构中评估新知识节点的有效性。
核心逻辑是计算新节点加入后的系统整体复杂度变化，通过权衡描述长度和预测误差来判断
节点是否为'过拟合噪音'。

输入格式:
    - 现有知识图谱 (Dict[str, KnowledgeNode])
    - 新候选节点 (KnowledgeNode)
    - 观测数据集

输出格式:
    - 验证结果
    - 系统指标变化
    - 决策日志

作者: AGI Systems Architect
版本: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MDL_Knowledge_Entropy')


class NodeDecision(Enum):
    """节点验证决策枚举"""
    ACCEPT = "accept"
    REJECT_NOISE = "reject_noise"
    REJECT_REDUNDANT = "reject_redundant"


@dataclass
class KnowledgeNode:
    """
    知识节点数据结构
    
    属性:
        node_id: 节点唯一标识符
        description: 节点描述文本
        connections: 连接的其他节点ID及权重
        complexity: 节点自身复杂度(描述长度)
        prediction_error: 节点预测误差
    """
    node_id: str
    description: str
    connections: Dict[str, float] = field(default_factory=dict)
    complexity: float = 0.0
    prediction_error: float = 1.0
    
    def __post_init__(self):
        """初始化后验证数据"""
        if not self.node_id:
            raise ValueError("节点ID不能为空")
        if self.complexity < 0:
            raise ValueError("复杂度不能为负")
        if not 0 <= self.prediction_error <= 1:
            raise ValueError("预测误差必须在[0, 1]范围内")


@dataclass
class MDLMetrics:
    """
    MDL评估指标数据结构
    
    属性:
        total_description_length: 系统总描述长度
        total_prediction_error: 系统总预测误差
        normalized_mdl: 归一化MDL值
        entropy_reduction: 熵减值
    """
    total_description_length: float
    total_prediction_error: float
    normalized_mdl: float
    entropy_reduction: float = 0.0
    
    def __post_init__(self):
        """初始化后验证数据"""
        if self.total_description_length < 0:
            raise ValueError("描述长度不能为负")
        if not 0 <= self.total_prediction_error <= 1:
            raise ValueError("预测误差必须在[0, 1]范围内")


@dataclass
class ValidationResult:
    """
    验证结果数据结构
    
    属性:
        decision: 决策结果
        metrics_before: 验证前系统指标
        metrics_after: 验证后系统指标(预测)
        message: 决策说明消息
    """
    decision: NodeDecision
    metrics_before: MDLMetrics
    metrics_after: MDLMetrics
    message: str


def calculate_node_complexity(node: KnowledgeNode) -> float:
    """
    计算单个知识节点的描述长度(复杂度)
    
    基于节点描述长度和连接权重分布计算信息量。
    使用香农熵公式: H(X) = -Σ p(x) * log2(p(x))
    
    参数:
        node: 知识节点对象
        
    返回:
        节点的描述长度(以比特为单位)
        
    示例:
        >>> node = KnowledgeNode("n1", "example", {"n2": 0.5, "n3": 0.5})
        >>> complexity = calculate_node_complexity(node)
        >>> print(f"节点复杂度: {complexity:.2f} bits")
    """
    if not node.connections:
        # 无连接节点复杂度为描述长度
        return len(node.description) * 8  # 假设每个字符8比特
    
    # 计算连接权重熵
    total_weight = sum(node.connections.values())
    if total_weight <= 0:
        logger.warning(f"节点 {node.node_id} 权重总和为0，使用默认复杂度")
        return len(node.description) * 8
    
    entropy = 0.0
    for weight in node.connections.values():
        if weight > 0:
            prob = weight / total_weight
            entropy -= prob * math.log2(prob)
    
    # 复杂度 = 描述长度 + 连接熵
    return len(node.description) * 8 + entropy * 10  # 熵加权因子


def calculate_system_mdl(
    nodes: Dict[str, KnowledgeNode],
    new_node: Optional[KnowledgeNode] = None
) -> MDLMetrics:
    """
    计算系统的MDL指标
    
    参数:
        nodes: 现有知识节点字典
        new_node: 可选的新候选节点
        
    返回:
        MDLMetrics对象包含所有评估指标
        
    示例:
        >>> nodes = {"n1": KnowledgeNode("n1", "test")}
        >>> metrics = calculate_system_mdl(nodes)
        >>> print(f"系统MDL: {metrics.normalized_mdl:.3f}")
    """
    if not nodes and new_node is None:
        return MDLMetrics(0.0, 1.0, 0.0)
    
    # 计算总描述长度
    total_dl = 0.0
    total_pe = 0.0
    node_count = 0
    
    # 处理现有节点
    for node in nodes.values():
        node.complexity = calculate_node_complexity(node)
        total_dl += node.complexity
        total_pe += node.prediction_error
        node_count += 1
    
    # 处理新节点
    if new_node is not None:
        new_node.complexity = calculate_node_complexity(new_node)
        total_dl += new_node.complexity
        total_pe += new_node.prediction_error
        node_count += 1
    
    # 计算归一化MDL
    avg_pe = total_pe / node_count if node_count > 0 else 1.0
    normalized_mdl = total_dl * (1 + avg_pe)  # 惩罚高预测误差
    
    return MDLMetrics(
        total_description_length=total_dl,
        total_prediction_error=avg_pe,
        normalized_mdl=normalized_mdl
    )


def validate_knowledge_node(
    existing_nodes: Dict[str, KnowledgeNode],
    candidate_node: KnowledgeNode,
    mdl_threshold: float = 0.1,
    error_tolerance: float = 0.05
) -> ValidationResult:
    """
    验证新知识节点是否应被接受
    
    基于MDL原则，如果新节点的加入:
    1. 显著降低预测误差(>error_tolerance) → 接受
    2. 增加描述长度但未降低误差 → 拒绝(过拟合噪音)
    3. 描述长度增加超过阈值 → 拒绝(冗余)
    
    参数:
        existing_nodes: 现有知识节点字典
        candidate_node: 候选新节点
        mdl_threshold: MDL增加容忍阈值
        error_tolerance: 误差降低的显著阈值
        
    返回:
        ValidationResult对象包含决策和指标
        
    示例:
        >>> nodes = {"n1": KnowledgeNode("n1", "cat", prediction_error=0.2)}
        >>> new_node = KnowledgeNode("n2", "feline", {"n1": 0.8}, prediction_error=0.1)
        >>> result = validate_knowledge_node(nodes, new_node)
        >>> print(f"决策: {result.decision.value}")
    """
    # 数据验证
    if not candidate_node.node_id:
        raise ValueError("候选节点必须有有效ID")
    
    if candidate_node.node_id in existing_nodes:
        logger.warning(f"节点 {candidate_node.node_id} 已存在，检查更新")
    
    # 计算当前系统指标
    metrics_before = calculate_system_mdl(existing_nodes)
    
    # 计算加入新节点后的系统指标(预测)
    metrics_after = calculate_system_mdl(existing_nodes, candidate_node)
    
    # 计算变化量
    dl_change = metrics_after.total_description_length - metrics_before.total_description_length
    pe_change = metrics_before.total_prediction_error - metrics_after.total_prediction_error
    mdl_change = metrics_after.normalized_mdl - metrics_before.normalized_mdl
    
    logger.info(f"验证节点 {candidate_node.node_id}: "
                f"DL变化={dl_change:.2f}, PE变化={pe_change:.4f}, MDL变化={mdl_change:.2f}")
    
    # 决策逻辑
    if pe_change > error_tolerance:
        # 显著降低预测误差 → 接受
        message = (f"接受节点 {candidate_node.node_id}: 预测误差降低 {pe_change:.4f} "
                   f"(超过阈值 {error_tolerance})")
        decision = NodeDecision.ACCEPT
        metrics_after.entropy_reduction = pe_change * 100  # 估算熵减
        
    elif dl_change > 0 and pe_change <= 0:
        # 增加复杂度但未降低误差 → 过拟合噪音
        message = (f"拒绝节点 {candidate_node.node_id}: 过拟合噪音 - "
                   f"描述长度增加 {dl_change:.2f} 但预测误差未改善")
        decision = NodeDecision.REJECT_NOISE
        
    elif mdl_change > mdl_threshold:
        # MDL增加超过阈值 → 冗余节点
        message = (f"拒绝节点 {candidate_node.node_id}: 冗余节点 - "
                   f"MDL增加 {mdl_change:.2f} 超过阈值 {mdl_threshold}")
        decision = NodeDecision.REJECT_REDUNDANT
        
    else:
        # 边缘情况：略微改善，接受
        message = f"接受节点 {candidate_node.node_id}: 边缘改善"
        decision = NodeDecision.ACCEPT
        metrics_after.entropy_reduction = pe_change * 50
    
    logger.info(f"决策: {decision.value} - {message}")
    
    return ValidationResult(
        decision=decision,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
        message=message
    )


def optimize_knowledge_graph(
    nodes: Dict[str, KnowledgeNode],
    candidate_nodes: List[KnowledgeNode],
    max_iterations: int = 100
) -> Tuple[Dict[str, KnowledgeNode], List[ValidationResult]]:
    """
    优化知识图谱，批量验证候选节点
    
    参数:
        nodes: 初始知识节点字典
        candidate_nodes: 候选节点列表
        max_iterations: 最大迭代次数
        
    返回:
        Tuple[优化后的节点字典, 验证结果列表]
        
    示例:
        >>> initial_nodes = {"n1": KnowledgeNode("n1", "root")}
        >>> candidates = [KnowledgeNode(f"n{i}", f"node{i}") for i in range(5)]
        >>> optimized, results = optimize_knowledge_graph(initial_nodes, candidates)
        >>> print(f"接受节点数: {sum(1 for r in results if r.decision == NodeDecision.ACCEPT)}")
    """
    results = []
    current_nodes = nodes.copy()
    
    for i, candidate in enumerate(candidate_nodes[:max_iterations]):
        logger.info(f"处理候选节点 {i+1}/{len(candidate_nodes)}: {candidate.node_id}")
        
        try:
            result = validate_knowledge_node(current_nodes, candidate)
            results.append(result)
            
            if result.decision == NodeDecision.ACCEPT:
                current_nodes[candidate.node_id] = candidate
                logger.info(f"节点 {candidate.node_id} 已添加到知识图谱")
            else:
                logger.info(f"节点 {candidate.node_id} 被拒绝: {result.decision.value}")
                
        except Exception as e:
            logger.error(f"验证节点 {candidate.node_id} 时出错: {str(e)}")
            continue
    
    # 计算最终指标
    final_metrics = calculate_system_mdl(current_nodes)
    logger.info(f"优化完成 - 最终节点数: {len(current_nodes)}, "
                f"MDL: {final_metrics.normalized_mdl:.2f}, "
                f"平均误差: {final_metrics.total_prediction_error:.4f}")
    
    return current_nodes, results


# 使用示例
if __name__ == "__main__":
    print("=== MDL知识节点熵减验证示例 ===")
    
    # 创建初始知识图谱
    initial_nodes = {
        "animal": KnowledgeNode(
            node_id="animal",
            description="living being that can move and eat",
            prediction_error=0.3
        ),
        "mammal": KnowledgeNode(
            node_id="mammal",
            description="warm-blooded animal with hair",
            connections={"animal": 0.9},
            prediction_error=0.2
        )
    }
    
    # 创建候选节点
    candidates = [
        KnowledgeNode(
            node_id="cat",
            description="small domestic feline",
            connections={"mammal": 0.8, "animal": 0.2},
            prediction_error=0.1  # 显著改善
        ),
        KnowledgeNode(
            node_id="noise_node",
            description="xyzabc12345",  # 高复杂度
            connections={"unknown": 1.0},
            prediction_error=0.35  # 未改善
        ),
        KnowledgeNode(
            node_id="dog",
            description="domestic canine",
            connections={"mammal": 0.9},
            prediction_error=0.15
        )
    ]
    
    # 执行优化
    optimized_graph, validation_results = optimize_knowledge_graph(
        initial_nodes, candidates
    )
    
    # 输出结果
    print("\n=== 验证结果 ===")
    for result in validation_results:
        print(f"节点: {result.metrics_after.total_description_length:.1f} -> "
              f"{result.decision.value}: {result.message}")
    
    print(f"\n最终知识图谱节点数: {len(optimized_graph)}")
    print("节点ID列表:", list(optimized_graph.keys()))