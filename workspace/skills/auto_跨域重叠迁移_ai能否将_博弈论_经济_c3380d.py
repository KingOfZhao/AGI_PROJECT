"""
跨域重叠迁移技能模块：博弈论至分布式系统的映射

本模块实现了从博弈论（纳什均衡）概念到分布式系统（拜占庭容错）参数配置的跨域映射。
通过建立两个领域间的数学同构关系，将经济博弈中的稳定性概念转化为分布式系统的可靠性参数。

核心映射逻辑：
1. 纳什均衡中的"策略稳定性" <-> BFT中的"共识稳定性"
2. 参与者理性选择 <-> 节点诚实行为概率
3. 混合策略概率分布 <-> 节点投票权重分配
4. 收益矩阵特征 <-> 系统容错阈值

作者: AGI Architecture Team
版本: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameTheoryConcept(Enum):
    """博弈论概念枚举"""
    NASH_EQUILIBRIUM = "纳什均衡"
    PARETO_OPTIMALITY = "帕累托最优"
    DOMINANT_STRATEGY = "优势策略"
    MIXED_STRATEGY = "混合策略"


class BFTParameter(Enum):
    """拜占庭容错参数枚举"""
    FAULT_TOLERANCE = "容错节点数"
    MESSAGE_THRESHOLD = "消息阈值"
    VOTING_WEIGHT = "投票权重"
    TIMEOUT_FACTOR = "超时因子"


@dataclass
class GameTheoryInput:
    """博弈论输入数据结构"""
    player_count: int
    payoff_matrix: Dict[Tuple[int, int], float]
    strategy_probabilities: Dict[int, float]
    rationality_factor: float  # 0.0-1.0, 参与者理性程度
    
    def __post_init__(self):
        """数据验证"""
        if self.player_count < 2:
            raise ValueError("玩家数量必须≥2")
        if not 0 <= self.rationality_factor <= 1:
            raise ValueError("理性因子必须在0.0到1.0之间")
        if len(self.strategy_probabilities) != self.player_count:
            raise ValueError("策略概率数量必须与玩家数量匹配")


@dataclass
class BFTConfiguration:
    """BFT配置输出数据结构"""
    total_nodes: int
    max_faulty_nodes: int
    message_threshold: int
    voting_weights: Dict[int, float]
    timeout_factor: float
    stability_score: float  # 系统稳定性评分 (0-1)


def calculate_nash_stability(payoff_matrix: Dict[Tuple[int, int], float], 
                            player_count: int) -> float:
    """
    计算纳什均衡稳定性指数
    
    基于收益矩阵计算系统的纳什均衡稳定性，返回0.0到1.0之间的稳定性评分。
    该指数反映系统在理性参与者行为下的可预测性和稳定性。
    
    参数:
        payoff_matrix: 收益矩阵，键为(玩家1策略, 玩家2策略)，值为收益
        player_count: 参与者数量
        
    返回:
        float: 稳定性指数 (0.0-1.0)
        
    示例:
        >>> matrix = {(0, 0): 3.0, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 2.0}
        >>> stability = calculate_nash_stability(matrix, 2)
        # 输出: 0.85 (表示高稳定性)
    """
    if not payoff_matrix:
        logger.error("收益矩阵为空")
        raise ValueError("收益矩阵不能为空")
    
    logger.info("计算纳什均衡稳定性...")
    
    # 计算收益标准差 (稳定性指标)
    payoffs = list(payoff_matrix.values())
    mean_payoff = sum(payoffs) / len(payoffs)
    variance = sum((p - mean_payoff) ** 2 for p in payoffs) / len(payoffs)
    std_dev = math.sqrt(variance)
    
    # 归一化稳定性 (标准差越小，稳定性越高)
    max_possible_std = max(abs(max(payoffs) - mean_payoff), abs(min(payoffs) - mean_payoff))
    if max_possible_std == 0:
        stability = 1.0  # 完全稳定
    else:
        stability = 1.0 - min(std_dev / max_possible_std, 1.0)
    
    # 考虑玩家数量对稳定性的影响
    player_factor = 1.0 / math.log2(player_count + 1)
    final_stability = stability * player_factor
    
    logger.debug(f"收益标准差: {std_dev:.4f}, 玩家因子: {player_factor:.4f}")
    logger.info(f"计算完成，稳定性指数: {final_stability:.4f}")
    
    return final_stability


def map_rationality_to_fault_tolerance(rationality_factor: float, 
                                      node_count: int) -> Tuple[int, int]:
    """
    将理性因子映射为拜占庭容错参数
    
    核心映射逻辑：
    - 高理性因子 (接近1.0) → 低故障节点比例 → 更严格的BFT要求
    - 低理性因子 (接近0.0) → 高故障节点比例 → 更宽松的BFT要求
    
    参数:
        rationality_factor: 理性因子 (0.0-1.0)
        node_count: 系统节点总数
        
    返回:
        Tuple[int, int]: (最大故障节点数, 消息阈值)
        
    示例:
        >>> faulty, threshold = map_rationality_to_fault_tolerance(0.8, 10)
        # 输出: (2, 7) 表示最多2个故障节点，需要7个消息确认
    """
    if not 0 <= rationality_factor <= 1:
        raise ValueError("理性因子必须在0.0到1.0之间")
    if node_count < 4:
        raise ValueError("BFT系统至少需要4个节点")
    
    logger.info(f"映射理性因子 {rationality_factor:.2f} 到BFT参数...")
    
    # BFT理论: 需要 n > 3f (n=总节点数, f=故障节点数)
    max_possible_faulty = (node_count - 1) // 3
    
    # 理性因子越高，系统越可预测，允许更少的故障节点
    if rationality_factor >= 0.7:
        fault_ratio = 0.2  # 保守策略
    elif rationality_factor >= 0.4:
        fault_ratio = 0.3  # 中等策略
    else:
        fault_ratio = 0.33  # 激进策略 (接近BFT理论上限)
    
    max_faulty = max(1, int(node_count * fault_ratio))
    max_faulty = min(max_faulty, max_possible_faulty)
    
    # 消息阈值 = n - f (需要超过2/3节点同意)
    message_threshold = node_count - max_faulty
    
    logger.info(f"映射完成: 最大故障节点={max_faulty}, 消息阈值={message_threshold}")
    return max_faulty, message_threshold


def convert_strategy_to_voting_weights(
    strategy_probabilities: Dict[int, float],
    node_ids: List[int]
) -> Dict[int, float]:
    """
    将博弈论策略概率转换为BFT投票权重
    
    混合策略中的概率分布映射为节点投票权重，反映不同节点在共识过程中的影响力。
    
    参数:
        strategy_probabilities: 策略概率字典 {玩家ID: 概率}
        node_ids: 目标系统节点ID列表
        
    返回:
        Dict[int, float]: 投票权重字典 {节点ID: 权重}
        
    示例:
        >>> probs = {0: 0.6, 1: 0.4}
        >>> weights = convert_strategy_to_voting_weights(probs, [10, 20])
        # 输出: {10: 0.6, 20: 0.4}
    """
    if not strategy_probabilities:
        raise ValueError("策略概率不能为空")
    if len(strategy_probabilities) != len(node_ids):
        raise ValueError("策略数量必须与节点数量匹配")
    
    logger.info("转换策略概率为投票权重...")
    
    # 验证概率总和为1 (允许小误差)
    total_prob = sum(strategy_probabilities.values())
    if not math.isclose(total_prob, 1.0, rel_tol=1e-3):
        logger.warning(f"策略概率总和 {total_prob:.4f} 不等于1.0，将进行归一化")
        # 归一化
        strategy_probabilities = {
            k: v/total_prob for k, v in strategy_probabilities.items()
        }
    
    # 直接映射策略概率到投票权重
    voting_weights = {}
    for i, (player_id, prob) in enumerate(strategy_probabilities.items()):
        node_id = node_ids[i]
        voting_weights[node_id] = prob
        logger.debug(f"玩家{player_id}(策略概率{prob:.3f}) -> 节点{node_id}(投票权重{prob:.3f})")
    
    logger.info(f"投票权重转换完成: {voting_weights}")
    return voting_weights


def cross_domain_mapping(game_input: GameTheoryInput) -> BFTConfiguration:
    """
    执行跨域映射：博弈论概念 → BFT系统配置
    
    这是核心映射函数，整合所有转换逻辑，生成完整的BFT配置建议。
    
    参数:
        game_input: 包含博弈论参数的输入数据结构
        
    返回:
        BFTConfiguration: 完整的BFT系统配置
        
    异常:
        ValueError: 输入数据验证失败
        RuntimeError: 映射过程失败
        
    示例:
        >>> game_data = GameTheoryInput(
        ...     player_count=4,
        ...     payoff_matrix={(0,0): 3.0, (0,1): 0.0, (1,0): 0.0, (1,1): 2.0},
        ...     strategy_probabilities={0: 0.5, 1: 0.3, 2: 0.1, 3: 0.1},
        ...     rationality_factor=0.75
        ... )
        >>> config = cross_domain_mapping(game_data)
        # 输出完整的BFT配置
    """
    logger.info("=" * 60)
    logger.info("开始跨域映射: 博弈论 → 分布式系统")
    logger.info("=" * 60)
    
    try:
        # 1. 计算纳什均衡稳定性
        stability_score = calculate_nash_stability(
            game_input.payoff_matrix, 
            game_input.player_count
        )
        
        # 2. 映射理性因子到容错参数
        node_count = game_input.player_count  # 玩家映射为节点
        max_faulty, msg_threshold = map_rationality_to_fault_tolerance(
            game_input.rationality_factor,
            node_count
        )
        
        # 3. 转换策略概率为投票权重
        node_ids = list(range(node_count))
        voting_weights = convert_strategy_to_voting_weights(
            game_input.strategy_probabilities,
            node_ids
        )
        
        # 4. 计算超时因子 (基于稳定性)
        # 稳定性越高，超时时间可以越短
        timeout_factor = 1.0 - (stability_score * 0.5)  # 范围: 0.5-1.0
        
        # 5. 构建BFT配置
        bft_config = BFTConfiguration(
            total_nodes=node_count,
            max_faulty_nodes=max_faulty,
            message_threshold=msg_threshold,
            voting_weights=voting_weights,
            timeout_factor=timeout_factor,
            stability_score=stability_score
        )
        
        logger.info("跨域映射成功完成")
        logger.info(f"BFT配置: 总节点={bft_config.total_nodes}, "
                   f"最大故障={bft_config.max_faulty_nodes}, "
                   f"消息阈值={bft_config.message_threshold}")
        logger.info(f"系统稳定性评分: {bft_config.stability_score:.4f}")
        
        return bft_config
        
    except Exception as e:
        logger.error(f"跨域映射失败: {str(e)}")
        raise RuntimeError(f"映射过程失败: {str(e)}")


def validate_bft_configuration(config: BFTConfiguration) -> bool:
    """
    验证生成的BFT配置是否满足拜占庭容错理论约束
    
    参数:
        config: BFT配置对象
        
    返回:
        bool: 配置是否有效
        
    验证规则:
        1. n > 3f (总节点数 > 3 × 最大故障节点数)
        2. 消息阈值 ≥ 2f + 1
        3. 投票权重总和 = 1.0
    """
    logger.info("验证BFT配置...")
    
    # 规则1: n > 3f
    if config.total_nodes <= 3 * config.max_faulty_nodes:
        logger.error(f"BFT约束失败: {config.total_nodes} ≤ 3×{config.max_faulty_nodes}")
        return False
    
    # 规则2: 消息阈值 ≥ 2f + 1
    min_threshold = 2 * config.max_faulty_nodes + 1
    if config.message_threshold < min_threshold:
        logger.error(f"消息阈值不足: {config.message_threshold} < {min_threshold}")
        return False
    
    # 规则3: 投票权重总和 = 1.0
    weight_sum = sum(config.voting_weights.values())
    if not math.isclose(weight_sum, 1.0, rel_tol=1e-3):
        logger.error(f"投票权重总和不等于1.0: {weight_sum:.4f}")
        return False
    
    logger.info("BFT配置验证通过 ✓")
    return True


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    """
    完整使用示例：演示从博弈论到BFT系统的跨域映射
    """
    print("\n" + "="*70)
    print("跨域重叠迁移演示：博弈论 → 分布式系统")
    print("="*70)
    
    # 示例1: 囚徒困境映射
    print("\n【示例1：囚徒困境场景】")
    print("-" * 50)
    
    prisoner_game = GameTheoryInput(
        player_count=2,
        payoff_matrix={
            (0, 0): 3.0,   # 双方合作
            (0, 1): 0.0,   # 玩家1合作，玩家2背叛
            (1, 0): 5.0,   # 玩家1背叛，玩家2合作
            (1, 1): 1.0    # 双方背叛
        },
        strategy_probabilities={0: 0.6, 1: 0.4},  # 混合策略
        rationality_factor=0.8  # 高理性
    )
    
    try:
        bft_config = cross_domain_mapping(prisoner_game)
        is_valid = validate_bft_configuration(bft_config)
        print(f"\n配置有效性: {'✓ 有效' if is_valid else '✗ 无效'}")
        print(f"建议: 使用{bft_config.total_nodes}个节点，"
              f"容忍{bft_config.max_faulty_nodes}个故障")
    except Exception as e:
        print(f"错误: {e}")
    
    # 示例2: 多人博弈映射
    print("\n\n【示例2：4节点分布式系统】")
    print("-" * 50)
    
    multi_player_game = GameTheoryInput(
        player_count=4,
        payoff_matrix={
            (0, 0): 4.0, (0, 1): 1.0, (0, 2): 2.0, (0, 3): 1.0,
            (1, 0): 1.0, (1, 1): 3.0, (1, 2): 1.0, (1, 3): 2.0,
            (2, 0): 2.0, (2, 1): 1.0, (2, 2): 4.0, (2, 3): 1.0,
            (3, 0): 1.0, (3, 1): 2.0, (3, 2): 1.0, (3, 3): 3.0,
        },
        strategy_probabilities={0: 0.3, 1: 0.25, 2: 0.25, 3: 0.2},
        rationality_factor=0.65  # 中等理性
    )
    
    try:
        bft_config = cross_domain_mapping(multi_player_game)
        is_valid = validate_bft_configuration(bft_config)
        print(f"\n配置有效性: {'✓ 有效' if is_valid else '✗ 无效'}")
        print(f"投票权重分配: {bft_config.voting_weights}")
        print(f"超时因子: {bft_config.timeout_factor:.3f}")
        print(f"系统稳定性: {bft_config.stability_score:.3f}")
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "="*70)
    print("跨域映射演示完成")
    print("="*70)