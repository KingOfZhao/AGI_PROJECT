"""
Auto-Top-Down Decomposition Skill Module.

This module provides an AGI-oriented skill for decomposing high-level, ambiguous 
macro goals into a structured, executable tree of specific actions. It emphasizes 
the transformation of abstract concepts into concrete parameters (location, cost, time).

Author: AGI System
Version: 1.0.0
Domain: Cognitive Science / Automated Planning
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enumeration of node types in the decomposition tree."""
    ROOT = "Root Goal"
    STRATEGY = "Strategy Layer"
    TACTIC = "Tactic Layer"
    ACTION = "Executable Action"


@dataclass
class ActionParameter:
    """Represents specific parameters for an executable action."""
    location: str
    estimated_cost: float  # In local currency
    time_window: str       # e.g., "Day 1 08:00-10:00"
    duration_minutes: int
    notes: str = ""


@dataclass
class DecompositionNode:
    """A node in the decomposition tree."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    node_type: NodeType = NodeType.ROOT
    depth: int = 0
    parameters: Optional[ActionParameter] = None
    children: List['DecompositionNode'] = field(default_factory=list)

    def add_child(self, child: 'DecompositionNode') -> None:
        """Adds a child node to the current node."""
        self.children.append(child)

    def is_leaf(self) -> bool:
        """Checks if the node is a leaf node."""
        return len(self.children) == 0


def validate_macro_goal(goal: str, constraints: Dict[str, Any]) -> bool:
    """
    Validates the input macro goal and constraints.
    
    Args:
        goal (str): The macro goal string.
        constraints (Dict[str, Any]): Dictionary containing constraints like budget, time.
        
    Returns:
        bool: True if valid, raises ValueError otherwise.
        
    Raises:
        ValueError: If goal is empty or constraints are missing critical keys.
    """
    if not goal or len(goal.strip()) < 5:
        logger.error("Validation failed: Goal description is too short or empty.")
        raise ValueError("Goal must be a descriptive string of at least 5 characters.")
    
    required_keys = ['budget', 'location', 'duration_days']
    for key in required_keys:
        if key not in constraints:
            logger.error(f"Validation failed: Missing constraint key '{key}'")
            raise ValueError(f"Missing required constraint: {key}")
            
    logger.info("Input validation passed.")
    return True


def _create_action_node(content: str, loc: str, cost: float, time: str, dur: int, depth: int) -> DecompositionNode:
    """
    Helper function to create a leaf node with specific parameters.
    
    Args:
        content: Description of the action.
        loc: Specific location.
        cost: Cost estimate.
        time: Time string.
        dur: Duration in minutes.
        depth: Current depth level.
        
    Returns:
        DecompositionNode: A fully parameterized action node.
    """
    params = ActionParameter(
        location=loc,
        estimated_cost=cost,
        time_window=time,
        duration_minutes=dur
    )
    return DecompositionNode(
        content=content,
        node_type=NodeType.ACTION,
        depth=depth,
        parameters=params
    )


def decompose_goal_recursive(
    current_node: DecompositionNode, 
    constraints: Dict[str, Any],
    max_depth: int = 3
) -> None:
    """
    Recursively decomposes a node into sub-nodes based on cognitive heuristics.
    
    This function simulates the 'thinking' process of breaking down a problem.
    
    Args:
        current_node: The node to decompose.
        constraints: Global constraints (budget, location).
        max_depth: Maximum depth of the tree (minimum 3 for this skill).
    """
    if current_node.depth >= max_depth:
        return

    current_depth = current_node.depth
    next_depth = current_depth + 1
    
    # Heuristic decomposition logic based on content type
    content_lower = current_node.content.lower()
    
    # Level 0 -> Level 1: High-level Strategies
    if "生存" in content_lower or "survival" in content_lower:
        strategies = [
            "解决住宿问题 (Accommodation)",
            "解决饮食问题 (Food)",
            "解决交通与移动 (Transport)"
        ]
        for strat in strategies:
            child = DecompositionNode(content=strat, node_type=NodeType.STRATEGY, depth=next_depth)
            current_node.add_child(child)
            decompose_goal_recursive(child, constraints, max_depth)
            
    # Level 1 -> Level 2: Tactics
    elif "住宿" in content_lower:
        tactics = [
            "寻找24小时营业场所 (24h Venues)",
            "寻找廉价青旅或澡堂 (Budget Hostels/Baths)"
        ]
        for tac in tactics:
            child = DecompositionNode(content=tac, node_type=NodeType.TACTIC, depth=next_depth)
            current_node.add_child(child)
            decompose_goal_recursive(child, constraints, max_depth)
            
    elif "饮食" in content_lower:
        tactics = [
            "寻找特价超市打折食品 (Discount Supermarkets)",
            "寻找提供免费水的公共场所 (Free Water Access)"
        ]
        for tac in tactics:
            child = DecompositionNode(content=tac, node_type=NodeType.TACTIC, depth=next_depth)
            current_node.add_child(child)
            decompose_goal_recursive(child, constraints, max_depth)

    # Level 2 -> Level 3: Concrete Actions (Leaf Nodes)
    elif "24小时营业场所" in content_lower:
        # Simulating retrieval of specific knowledge
        action = _create_action_node(
            content="前往麦当劳(火车站店)过夜",
            loc=f"{constraints['location']}火车站二层",
            cost=0.0, # Just sitting there
            time=f"Day 1 23:00 - Day 2 06:00",
            dur=420,
            depth=next_depth
        )
        current_node.add_child(action)
        
    elif "廉价青旅" in content_lower:
        budget_remaining = constraints.get('budget', 50)
        # Only suggest if budget allows (Logic check)
        cost = 30.0
        if budget_remaining >= cost:
            action = _create_action_node(
                content="入住'行者胶囊'青年旅舍床位",
                loc=f"{constraints['location']}老城区解放路45号",
                cost=cost,
                time=f"Day 2 14:00 - Day 3 12:00",
                dur=1320,
                depth=next_depth
            )
            current_node.add_child(action)
        else:
            # Fallback action if budget is tight
            action = _create_action_node(
                content="寻找公园长椅睡觉(备选)",
                loc=f"{constraints['location']}中心公园",
                cost=0.0,
                time=f"Day 2 00:00 - 05:00",
                dur=300,
                depth=next_depth
            )
            current_node.add_child(action)

    elif "特价超市" in content_lower:
        action = _create_action_node(
            content="购买打折便当和矿泉水",
            loc=f"{constraints['location']}沃尔玛超市(负一层)",
            cost=15.0,
            time=f"Day 1 20:30 (超市关门打折时段)",
            dur=30,
            depth=next_depth
        )
        current_node.add_child(action)

    elif "免费水" in content_lower:
        action = _create_action_node(
            content="在火车站候车室接取免费饮用水",
            loc=f"{constraints['location']}火车站候车大厅",
            cost=0.0,
            time=f"Day 1 10:00",
            dur=10,
            depth=next_depth
        )
        current_node.add_child(action)


def generate_execution_tree(goal: str, constraints: Dict[str, Any]) -> DecompositionNode:
    """
    Main entry point for generating the decomposition tree.
    
    Input Format:
        goal: "用50元本金在城市A生存3天"
        constraints: {
            'budget': 50.0, 
            'location': 'City A', 
            'duration_days': 3
        }
    
    Output Format:
        DecompositionNode (Root of the tree)
    
    Args:
        goal (str): The fuzzy macro goal.
        constraints (Dict[str, Any]): Dictionary of environmental constraints.
        
    Returns:
        DecompositionNode: The root node of the generated tree.
    """
    try:
        logger.info(f"Starting decomposition for goal: {goal}")
        validate_macro_goal(goal, constraints)
        
        root = DecompositionNode(content=goal, node_type=NodeType.ROOT, depth=0)
        
        # Start recursive decomposition
        decompose_goal_recursive(root, constraints, max_depth=3)
        
        logger.info("Tree generation completed successfully.")
        return root
        
    except Exception as e:
        logger.exception("Failed to generate execution tree.")
        raise RuntimeError(f"Decomposition failed: {e}")


def print_tree(node: DecompositionNode, indent: str = "") -> None:
    """Utility to visualize the tree structure."""
    prefix = f"{indent}[{node.node_type.value}] "
    cost_info = f" | Cost: {node.parameters.estimated_cost}" if node.parameters else ""
    loc_info = f" | Loc: {node.parameters.location}" if node.parameters else ""
    
    print(f"{prefix}{node.content}{cost_info}{loc_info}")
    
    for child in node.children:
        print_tree(child, indent + "  ")


# Example Usage
if __name__ == "__main__":
    macro_goal = "用50元本金在城市A生存3天"
    env_constraints = {
        'budget': 50.0,
        'location': 'City A',
        'duration_days': 3
    }
    
    try:
        execution_tree = generate_execution_tree(macro_goal, env_constraints)
        print("\n=== Generated Execution Tree ===")
        print_tree(execution_tree)
    except RuntimeError as e:
        print(f"Error: {e}")