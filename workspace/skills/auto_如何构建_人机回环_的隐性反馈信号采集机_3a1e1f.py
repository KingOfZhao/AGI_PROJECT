"""
Module: implicit_feedback_loop.py

This module implements a mechanism to collect implicit human feedback signals
within a Human-in-the-Loop (HITL) AGI system. It focuses on "silent rejections" —
scenarios where a human user does not explicitly reject an AI's suggestion but
bypasses it through subsequent actions.

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of possible user action types."""
    ACCEPT_SUGGESTION = 1
    BYPASS_SUGGESTION = 2
    IGNORE_SUGGESTION = 3
    EXPLICIT_REJECTION = 4


@dataclass
class SkillNode:
    """Represents a node in the AGI skill graph."""
    node_id: str
    name: str
    trust_score: float = 1.0  # Default score between 0.0 and 2.0
    invocation_count: int = 0
    bypass_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserAction:
    """Represents a single user action in the interaction log."""
    action_id: str
    timestamp: datetime
    action_type: ActionType
    target_node_id: Optional[str] = None  # The node being interacted with
    context_tags: List[str] = field(default_factory=list)


class ImplicitFeedbackCollector:
    """
    Core class for collecting and processing implicit feedback signals.
    
    This class maps user behavior sequences to node quality scores. It detects
    'passive resistance' (bypassing suggestions) and adjusts node trust scores
    accordingly.
    
    Attributes:
        nodes (Dict[str, SkillNode]): A registry of skill nodes.
        interaction_history (List[UserAction]): Log of user actions.
        decay_rate (float): How much past interactions weigh less over time.
        
    Usage Example:
        >>> collector = ImplicitFeedbackCollector()
        >>> collector.register_node("node_123", "DataFetcher")
        >>> collector.record_action(ActionType.BYPASS_SUGGESTION, "node_123")
        >>> score = collector.get_node_trust_score("node_123")
        >>> print(f"Updated Trust Score: {score}")
    """

    def __init__(self, decay_rate: float = 0.95):
        """
        Initialize the feedback collector.
        
        Args:
            decay_rate (float): Weight multiplier for historical data (0.0 to 1.0).
        """
        if not 0.0 <= decay_rate <= 1.0:
            raise ValueError("Decay rate must be between 0.0 and 1.0")
            
        self.nodes: Dict[str, SkillNode] = {}
        self.interaction_history: List[UserAction] = []
        self.decay_rate = decay_rate
        logger.info("ImplicitFeedbackCollector initialized with decay rate: %s", decay_rate)

    def register_node(self, node_id: str, name: str, metadata: Optional[Dict] = None) -> None:
        """
        Register a new skill node in the system.
        
        Args:
            node_id (str): Unique identifier for the node.
            name (str): Human-readable name of the skill.
            metadata (Optional[Dict]): Additional metadata.
        """
        if node_id in self.nodes:
            logger.warning("Node %s already exists. Overwriting.", node_id)
        
        self.nodes[node_id] = SkillNode(
            node_id=node_id,
            name=name,
            metadata=metadata or {}
        )
        logger.debug("Registered node: %s", node_id)

    def record_action(self, action_type: ActionType, target_node_id: Optional[str] = None, 
                      context: Optional[List[str]] = None) -> str:
        """
        Record a user action and trigger implicit feedback evaluation.
        
        This is the primary ingress for behavioral data.
        
        Args:
            action_type (ActionType): The type of action performed.
            target_node_id (Optional[str]): The ID of the node involved (if any).
            context (Optional[List[str]]): Contextual tags for the session.
            
        Returns:
            str: The unique ID of the recorded action.
            
        Raises:
            ValueError: If target_node_id is provided but does not exist.
        """
        if target_node_id and target_node_id not in self.nodes:
            logger.error("Attempted to record action for non-existent node: %s", target_node_id)
            raise ValueError(f"Node ID {target_node_id} not found in registry.")

        # Generate unique action ID
        ts_str = datetime.now().isoformat()
        action_hash = hashlib.md5(ts_str.encode()).hexdigest()[:8]
        action_id = f"act_{action_hash}"

        action = UserAction(
            action_id=action_id,
            timestamp=datetime.now(),
            action_type=action_type,
            target_node_id=target_node_id,
            context_tags=context or []
        )

        self.interaction_history.append(action)
        
        # Update node statistics immediately if a node is involved
        if target_node_id:
            self._update_node_stats(target_node_id, action_type)
            
        logger.info("Recorded action %s: %s on node %s", action_id, action_type.name, target_node_id)
        return action_id

    def _update_node_stats(self, node_id: str, action_type: ActionType) -> None:
        """
        Internal helper to update raw statistics on the node based on action.
        
        Args:
            node_id (str): The node to update.
            action_type (ActionType): The action that occurred.
        """
        node = self.nodes[node_id]
        node.invocation_count += 1

        if action_type in [ActionType.BYPASS_SUGGESTION, ActionType.EXPLICIT_REJECTION]:
            node.bypass_count += 1
            
        # Recalculate trust score
        self._calculate_trust_score(node)

    def _calculate_trust_score(self, node: SkillNode) -> None:
        """
        Calculate and update the trust score for a specific node.
        
        Logic:
        - Base score is 1.0.
        - 'Bypass' actions act as negative signals.
        - Formula uses a sigmoid-like dampening to prevent scores from hitting 0 too quickly.
        
        Args:
            node (SkillNode): The node object to update.
        """
        if node.invocation_count == 0:
            node.trust_score = 1.0
            return

        # Simple implicit feedback model:
        # Score = 1.0 - (Bypass_Rate * Penalty_Weight)
        # Bypass Rate = bypasses / invocations
        bypass_rate = node.bypass_count / node.invocation_count
        
        # Penalty weight increases as bypass rate increases (non-linear)
        # Using a simple exponential penalty for demonstration
        penalty = (bypass_rate ** 1.5) * 1.2  # 1.2 is a tuning hyperparameter
        
        new_score = max(0.1, 1.0 - penalty) # Floor at 0.1 to allow recovery
        
        node.trust_score = round(new_score, 3)
        logger.debug("Updated trust score for %s to %.3f", node.node_id, node.trust_score)

    def analyze_bypass_patterns(self, lookback_count: int = 100) -> Dict[str, float]:
        """
        Analyze recent history to map behavior sequences to node quality.
        
        This function looks for patterns where specific nodes are frequently
        bypassed in specific contexts (implicit negative feedback).
        
        Args:
            lookback_count (int): Number of recent actions to analyze.
            
        Returns:
            Dict[str, float]: A report of nodes with their current bypass rates.
        """
        if lookback_count <= 0:
            raise ValueError("Lookback count must be positive.")

        recent_actions = self.interaction_history[-lookback_count:]
        bypass_stats: Dict[str, Dict[str, int]] = {} # node_id -> {total, bypass}

        for action in recent_actions:
            if not action.target_node_id:
                continue
                
            node_id = action.target_node_id
            if node_id not in bypass_stats:
                bypass_stats[node_id] = {"total": 0, "bypass": 0}
            
            bypass_stats[node_id]["total"] += 1
            if action.action_type in [ActionType.BYPASS_SUGGESTION, ActionType.IGNORE_SUGGESTION]:
                bypass_stats[node_id]["bypass"] += 1

        report = {}
        for node_id, stats in bypass_stats.items():
            if stats["total"] > 0:
                rate = stats["bypass"] / stats["total"]
                report[node_id] = round(rate, 2)
        
        logger.info("Generated bypass pattern report for %d nodes.", len(report))
        return report

    def get_node_trust_score(self, node_id: str) -> float:
        """
        Retrieve the current trust score for a specific node.
        
        Args:
            node_id (str): The ID of the node.
            
        Returns:
            float: The trust score (0.1 to 2.0).
        """
        self._validate_node_exists(node_id)
        return self.nodes[node_id].trust_score

    def _validate_node_exists(self, node_id: str) -> None:
        """Helper to check if a node exists."""
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found.")


def run_simulation():
    """
    Simulation function to demonstrate the module capabilities.
    """
    print("--- Initializing Implicit Feedback System ---")
    system = ImplicitFeedbackCollector()
    
    # 1. Register Nodes
    system.register_node("skill_A", "WeatherAPI")
    system.register_node("skill_B", "DatabaseQuery")
    
    # 2. Simulate User Behavior: User accepts Skill A (Positive)
    print("\n[Sim] User accepts Skill A suggestion...")
    system.record_action(ActionType.ACCEPT_SUGGESTION, "skill_A")
    
    # 3. Simulate User Behavior: User bypasses Skill B (Implicit Negative)
    print("[Sim] User bypasses Skill B suggestion (passive resistance)...")
    system.record_action(ActionType.BYPASS_SUGGESTION, "skill_B")
    
    # 4. Simulate User Behavior: User bypasses Skill B again
    print("[Sim] User bypasses Skill B again...")
    system.record_action(ActionType.BYPASS_SUGGESTION, "skill_B")
    system.record_action(ActionType.BYPASS_SUGGESTION, "skill_B")
    
    # 5. Check Scores
    score_a = system.get_node_trust_score("skill_A")
    score_b = system.get_node_trust_score("skill_B")
    
    print(f"\n--- Results ---")
    print(f"Skill A Trust Score: {score_a} (High trust expected)")
    print(f"Skill B Trust Score: {score_b} (Low trust expected)")
    
    # 6. Analyze Patterns
    report = system.analyze_bypass_patterns()
    print(f"Bypass Analysis Report: {report}")

if __name__ == "__main__":
    run_simulation()