"""
Module: goal_skill_alignment.py
Description: Implements 'Top-Down' Goal Decomposition Trees and 'Bottom-Up' Skill Discovery Trees
             with a dynamic alignment algorithm for AGI systems.
             
Author: Senior Python Engineer (AGI System Core)
Version: 1.0.0
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """Enumeration of node statuses in the AGI cognitive tree."""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCESS = "success"
    FAILED = "failed"
    INFEASIBLE = "infeasible"

@dataclass
class CognitiveNode:
    """
    Represents a node in either the Goal Tree or Skill Tree.
    
    Attributes:
        id: Unique identifier for the node.
        description: Human-readable description (e.g., 'Make Money', 'Set up Stall').
        level: Abstract level (0 = Macro Goal/Root, 10 = Micro Action).
        parent_id: ID of the parent node.
        children: List of child node IDs.
        status: Current status of the node.
        metadata: Additional properties (e.g., cost, time_required).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    level: int = 0
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.status, NodeStatus):
            raise ValueError(f"Invalid status: {self.status}")

class AlignmentSystem:
    """
    Manages the dynamic alignment between Goal Decomposition (Top-Down) 
    and Skill Discovery (Bottom-Up).
    """
    
    def __init__(self):
        self.goal_tree: Dict[str, CognitiveNode] = {}
        self.skill_tree: Dict[str, CognitiveNode] = {}
        self.alignment_map: Dict[str, str] = {} # Maps Goal Node ID -> Skill Node ID
        
    def add_node(self, node: CognitiveNode, tree_type: str = 'goal') -> str:
        """
        Helper function to add a node to a specific tree.
        
        Args:
            node: The CognitiveNode to add.
            tree_type: 'goal' or 'skill'.
            
        Returns:
            The ID of the added node.
        """
        try:
            if tree_type == 'goal':
                self.goal_tree[node.id] = node
            elif tree_type == 'skill':
                self.skill_tree[node.id] = node
            else:
                raise ValueError(f"Unknown tree type: {tree_type}")
            
            # Link to parent if exists
            if node.parent_id:
                parent_tree = self.goal_tree if tree_type == 'goal' else self.skill_tree
                if node.parent_id in parent_tree:
                    parent_tree[node.parent_id].children.append(node.id)
            
            logger.info(f"Added {tree_type} node: {node.description} (ID: {node.id})")
            return node.id
        except Exception as e:
            logger.error(f"Error adding node: {e}")
            raise

    def decompose_goal(self, parent_goal_id: str, sub_goals: List[str]) -> List[str]:
        """
        [Top-Down] Decompose a high-level goal into executable sub-goals.
        
        Args:
            parent_goal_id: ID of the goal to decompose.
            sub_goals: List of descriptions for sub-goals.
            
        Returns:
            List of new Goal Node IDs.
        """
        if parent_goal_id not in self.goal_tree:
            raise ValueError(f"Parent goal {parent_goal_id} not found.")
            
        parent = self.goal_tree[parent_goal_id]
        new_ids = []
        
        logger.info(f"Decomposing Goal '{parent.description}' into {len(sub_goals)} sub-goals.")
        
        for desc in sub_goals:
            # Create new goal node
            new_node = CognitiveNode(
                description=desc,
                level=parent.level + 1,
                parent_id=parent.id,
                status=NodeStatus.PENDING
            )
            self.goal_tree[new_node.id] = new_node
            parent.children.append(new_node.id)
            new_ids.append(new_node.id)
            
            # Automatic Alignment: Try to find an existing skill
            self._align_node(new_node.id)
            
        return new_ids

    def report_skill_failure(self, skill_node_id: str, reason: str = "Execution failed") -> None:
        """
        [Bottom-Up] Report a skill failure and propagate the impact up the hierarchy.
        
        This is the core of the feedback loop. If a micro-action fails, it checks
        if the parent Goal is still achievable. If not, it marks the parent as
        INFEASIBLE, triggering a re-planning or higher-level strategy shift.
        
        Args:
            skill_node_id: ID of the skill node that failed.
            reason: Description of the failure.
        """
        if skill_node_id not in self.skill_tree:
            raise ValueError(f"Skill node {skill_node_id} not found.")
            
        skill_node = self.skill_tree[skill_node_id]
        skill_node.status = NodeStatus.FAILED
        skill_node.metadata['failure_reason'] = reason
        logger.warning(f"Skill '{skill_node.description}' reported FAILURE: {reason}")
        
        # 1. Propagate up Skill Tree
        if skill_node.parent_id:
            parent_skill = self.skill_tree.get(skill_node.parent_id)
            if parent_skill:
                # Check if all siblings failed (simplified logic)
                self._evaluate_parent_status(parent_skill)

        # 2. Cross-Tree Alignment Impact
        # If this skill maps to a Goal, update that Goal's status
        # Reverse lookup in alignment_map
        aligned_goal_id = self._get_goal_id_by_skill(skill_node_id)
        
        if aligned_goal_id:
            logger.info(f"Propagating failure to aligned Goal ID: {aligned_goal_id}")
            self._mark_goal_infeasible(aligned_goal_id, reason)

    def _align_node(self, goal_node_id: str) -> Optional[str]:
        """
        [Internal] Aligns a specific Goal Node with a Skill Node.
        If no skill exists, it creates a placeholder.
        
        Args:
            goal_node_id: The ID of the goal node to align.
            
        Returns:
            The ID of the aligned skill node.
        """
        goal_node = self.goal_tree[goal_node_id]
        
        # Simple heuristic: Check if a skill with same description exists
        # In real AGI, this would use vector embeddings for semantic matching
        matched_skill_id = None
        
        for s_id, s_node in self.skill_tree.items():
            if s_node.description == goal_node.description and s_node.level == goal_node.level:
                matched_skill_id = s_id
                break
        
        if matched_skill_id:
            logger.debug(f"Aligned Goal '{goal_node.description}' with existing Skill.")
            self.alignment_map[goal_node_id] = matched_skill_id
            return matched_skill_id
        else:
            # Create a corresponding skill node (Discovery)
            new_skill = CognitiveNode(
                description=goal_node.description,
                level=goal_node.level,
                status=NodeStatus.PENDING
            )
            self.skill_tree[new_skill.id] = new_skill
            self.alignment_map[goal_node_id] = new_skill.id
            logger.debug(f"Created new Skill '{new_skill.description}' to align with Goal.")
            return new_skill.id

    def _evaluate_parent_status(self, parent_node: CognitiveNode) -> None:
        """
        [Internal] Evaluate if a parent node should fail based on children status.
        """
        children = [self.skill_tree[cid] for cid in parent_node.children if cid in self.skill_tree]
        if not children:
            return

        # Example Logic: If ALL children failed, parent fails
        all_failed = all(c.status == NodeStatus.FAILED for c in children)
        
        if all_failed:
            parent_node.status = NodeStatus.FAILED
            logger.warning(f"Parent Skill '{parent_node.description}' marked as FAILED due to total child failure.")

    def _mark_goal_infeasible(self, goal_id: str, reason: str) -> None:
        """
        [Internal] Mark a goal as infeasible and handle logic.
        """
        if goal_id not in self.goal_tree:
            return
            
        goal = self.goal_tree[goal_id]
        if goal.status == NodeStatus.INFEASIBLE:
            return
            
        goal.status = NodeStatus.INFEASIBLE
        goal.metadata['infeasibility_reason'] = reason
        logger.error(f"GOAL INFEASIBLE: '{goal.description}' (Level {goal.level}). Reason: {reason}")
        
        # In a real system, this would trigger a re-planning event

    def _get_goal_id_by_skill(self, skill_id: str) -> Optional[str]:
        """Helper to find goal ID from skill ID using the map."""
        for g_id, s_id in self.alignment_map.items():
            if s_id == skill_id:
                return g_id
        return None

# Usage Example
if __name__ == "__main__":
    system = AlignmentSystem()
    
    # 1. Define Macro Goal
    root_goal = CognitiveNode(description="Make Money", level=0, status=NodeStatus.ACTIVE)
    system.add_node(root_goal, tree_type='goal')
    
    # 2. Top-Down Decomposition
    # "Make Money" -> "Start Business", "Invest Stocks"
    sub_goal_ids = system.decompose_goal(root_goal.id, ["Start Business", "Invest Stocks"])
    
    # Further decompose "Start Business"
    start_biz_id = sub_goal_ids[0]
    system.decompose_goal(start_biz_id, ["Open Lemonade Stand", "Develop App"])
    
    # 3. Simulate Execution & Bottom-Up Feedback
    # Assume "Open Lemonade Stand" aligns with a specific skill
    # We retrieve the aligned skill for "Open Lemonade Stand"
    lemon_goal_id = None
    for gid in system.goal_tree:
        if system.goal_tree[gid].description == "Open Lemonade Stand":
            lemon_goal_id = gid
            break
            
    if lemon_goal_id:
        aligned_skill_id = system.alignment_map.get(lemon_goal_id)
        if aligned_skill_id:
            print("\n--- Simulating Failure Propagation ---")
            print(f"Micro-action '{system.skill_tree[aligned_skill_id].description}' failed due to bad location.")
            # Report failure
            system.report_skill_failure(aligned_skill_id, reason="Bad location, no customers")
            
            # Check status of parent goal "Start Business"
            parent_goal = system.goal_tree.get(start_biz_id)
            print(f"Parent Goal '{parent_goal.description}' status: {parent_goal.status}")