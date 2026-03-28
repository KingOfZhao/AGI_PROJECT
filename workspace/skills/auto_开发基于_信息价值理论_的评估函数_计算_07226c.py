"""
Module: auto_开发基于_信息价值理论_的评估函数_计算_07226c

This module implements evaluation functions based on Information Value Theory (IVT)
to calculate the Expected Utility (EU) of exploring new nodes in a search or decision tree.
It balances the potential value of information against the exploration costs
(time and computational resources).

The core logic estimates the value of a node by combining the probability of
reaching a high-value state with the cost required to verify it.
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeState:
    """
    Represents the state of a node in the search space.
    
    Attributes:
        node_id (str): Unique identifier for the node.
        current_value (float): The heuristic value or reward obtained at this node.
        probability_success (float): Estimated probability (0.0 to 1.0) that this path leads to a solution.
        time_cost (float): Estimated time (in seconds) to explore this node.
        compute_cost (float): Estimated computational cycles (FLOPS or abstract units) required.
        depth (int): Current depth in the search tree.
    """
    node_id: str
    current_value: float
    probability_success: float
    time_cost: float
    compute_cost: float
    depth: int = 0

@dataclass
class ExplorationParams:
    """
    Configuration parameters for the evaluation function.
    
    Attributes:
        time_weight (float): Weight factor for time cost in the utility function.
        compute_weight (float): Weight factor for compute cost.
        discount_factor (float): Gamma, discount for future rewards (0 to 1).
        exploration_bonus (float): Constant bonus added to encourage exploration of unknowns.
    """
    time_weight: float = 0.5
    compute_weight: float = 0.5
    discount_factor: float = 0.95
    exploration_bonus: float = 0.1


def _validate_inputs(node: NodeState, params: ExplorationParams) -> None:
    """
    Helper function to validate data integrity and boundary conditions.
    
    Args:
        node (NodeState): The node to validate.
        params (ExplorationParams): The parameters to validate.
    
    Raises:
        ValueError: If any numerical inputs are out of bounds or invalid.
        TypeError: If input types are incorrect.
    """
    if not isinstance(node, NodeState) or not isinstance(params, ExplorationParams):
        raise TypeError("Invalid input types provided.")
    
    if not (0.0 <= node.probability_success <= 1.0):
        raise ValueError(f"Probability must be between 0 and 1, got {node.probability_success}")
    
    if node.time_cost < 0 or node.compute_cost < 0:
        raise ValueError("Costs cannot be negative.")
    
    if params.discount_factor < 0 or params.discount_factor > 1:
        logger.warning(f"Unusual discount factor: {params.discount_factor}")

def calculate_expected_utility(
    node: NodeState, 
    params: ExplorationParams, 
    potential_reward: float = 100.0
) -> float:
    """
    Calculates the Expected Utility (EU) of a node based on Information Value Theory.
    
    The formula used is:
    EU = (Probability_Success * Potential_Reward * Discount_Factor^Depth) - 
         (Time_Weight * Time_Cost + Compute_Weight * Compute_Cost)
    
    Args:
        node (NodeState): The node to evaluate.
        params (ExplorationParams): Configuration for weights and discounts.
        potential_reward (float): The estimated value of the target goal.
    
    Returns:
        float: The calculated expected utility value.
    
    Example:
        >>> state = NodeState("n1", 10.0, 0.8, 2.0, 50.0, depth=1)
        >>> config = ExplorationParams()
        >>> utility = calculate_expected_utility(state, config)
        >>> print(f"Utility: {utility}")
    """
    try:
        _validate_inputs(node, params)
        
        # Calculate discounted future reward
        discounted_reward = potential_reward * (params.discount_factor ** node.depth)
        
        # Expected Value of Information (VOI)
        voi = node.probability_success * discounted_reward
        
        # Total weighted cost
        total_cost = (params.time_weight * node.time_cost) + (params.compute_weight * node.compute_cost)
        
        utility = voi - total_cost
        logger.debug(f"Calculated EU for {node.node_id}: {utility}")
        
        return utility
        
    except Exception as e:
        logger.error(f"Error calculating utility for node {node.node_id}: {e}")
        return -float('inf') # Return negative infinity to discourage invalid nodes

def calculate_exploration_ratio(
    node: NodeState, 
    params: ExplorationParams,
    potential_reward: float = 100.0,
    epsilon: float = 1e-6
) -> float:
    """
    Calculates the Value/Cost ratio for exploration prioritization.
    
    This function computes the efficiency of exploring a node by dividing
    the expected utility by the exploration cost. It handles division by zero
    using a small epsilon.
    
    Formula:
    Ratio = Expected_Utility / (Time_Cost + Compute_Cost + Epsilon)
    
    Args:
        node (NodeState): The node to evaluate.
        params (ExplorationParams): Configuration parameters.
        potential_reward (float): Estimated target reward.
        epsilon (float): Small value to prevent division by zero.
    
    Returns:
        float: The exploration efficiency ratio.
    
    Example:
        >>> state = NodeState("n2", 5.0, 0.5, 10.0, 100.0)
        >>> config = ExplorationParams()
        >>> ratio = calculate_exploration_ratio(state, config)
        >>> print(f"Efficiency Ratio: {ratio}")
    """
    try:
        eu = calculate_expected_utility(node, params, potential_reward)
        
        total_raw_cost = node.time_cost + node.compute_cost
        
        if total_raw_cost < 0:
            raise ValueError("Total cost calculation resulted in negative value.")
            
        # Avoid division by zero
        ratio = eu / (total_raw_cost + epsilon)
        
        return ratio
        
    except Exception as e:
        logger.error(f"Failed to calculate ratio for {node.node_id}: {e}")
        return 0.0

def select_best_node(
    candidates: List[NodeState], 
    params: ExplorationParams
) -> Tuple[Optional[NodeState], float]:
    """
    Selects the best node to explore next based on the highest exploration ratio.
    
    Args:
        candidates (List[NodeState]): List of candidate nodes.
        params (ExplorationParams): Evaluation parameters.
    
    Returns:
        Tuple[Optional[NodeState], float]: The best node and its score. 
                                           Returns (None, -1.0) if list is empty.
    
    Example:
        >>> nodes = [NodeState("a", 10, 0.5, 1, 10), NodeState("b", 20, 0.8, 5, 50)]
        >>> p = ExplorationParams()
        >>> best, score = select_best_node(nodes, p)
    """
    if not candidates:
        logger.warning("Candidate list is empty.")
        return None, -1.0

    best_node = None
    max_ratio = -float('inf')

    for node in candidates:
        try:
            ratio = calculate_exploration_ratio(node, params)
            if ratio > max_ratio:
                max_ratio = ratio
                best_node = node
        except Exception as e:
            logger.warning(f"Skipping node {node.node_id} due to error: {e}")
            continue

    if best_node:
        logger.info(f"Selected Node: {best_node.node_id} with Value/Cost Ratio: {max_ratio:.4f}")
    
    return best_node, max_ratio

# Main execution block for usage demonstration
if __name__ == "__main__":
    # Create sample nodes
    node_A = NodeState(
        node_id="explore_path_A",
        current_value=50.0,
        probability_success=0.8,
        time_cost=2.0,
        compute_cost=100.0,
        depth=2
    )
    
    node_B = NodeState(
        node_id="explore_path_B",
        current_value=10.0,
        probability_success=0.2,
        time_cost=0.5,
        compute_cost=10.0,
        depth=1
    )
    
    # Define parameters
    search_params = ExplorationParams(
        time_weight=0.1,
        compute_weight=0.9,
        discount_factor=0.9
    )
    
    # Evaluate nodes
    candidates = [node_A, node_B]
    best_choice, score = select_best_node(candidates, search_params)
    
    if best_choice:
        print(f"\n--- Decision Result ---")
        print(f"Best Node ID: {best_choice.node_id}")
        print(f"Calculated Efficiency Ratio: {score:.4f}")
        
        # Detailed breakdown
        eu = calculate_expected_utility(best_choice, search_params)
        print(f"Expected Utility: {eu:.2f}")