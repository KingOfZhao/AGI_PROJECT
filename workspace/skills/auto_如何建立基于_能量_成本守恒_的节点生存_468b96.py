"""
Module: auto_如何建立基于_能量_成本守恒_的节点生存_468b96
Description: Implements a survival competition mechanism based on Energy/Cost Conservation.
             Manages the lifecycle of AGI cognitive nodes by enforcing an economic model
             of resource consumption (Survival Rent) versus value generation.

Domain: economic_computing
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Economic_Survival")


class NodeState(Enum):
    """Enumeration of possible states for a cognitive node."""
    ACTIVE = auto()
    DORMANT = auto()    # Low energy, paused
    ARCHIVED = auto()   # Long-term storage, inactive
    DEAD = auto()       # Removed from system


@dataclass
class EconomicProfile:
    """Represents the economic attributes of a node."""
    base_cost: float  # Base computational cost per cycle (Rent)
    complexity: float  # Dependency complexity multiplier
    value_score: float = 0.0  # Value generated in current cycle
    frequency: int = 0  # Times invoked in current cycle
    energy_balance: float = 100.0  # Current 'survival' points
    
    @property
    def total_maintenance_cost(self) -> float:
        """Calculates total rent including complexity overhead."""
        if self.base_cost < 0 or self.complexity < 0:
            raise ValueError("Cost and complexity must be non-negative")
        return self.base_cost * (1 + math.log1p(self.complexity))


@dataclass
class AGINode:
    """Represents a single node in the AGI system."""
    node_id: str
    state: NodeState
    profile: EconomicProfile
    history: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.node_id:
            raise ValueError("Node ID cannot be empty")


class SurvivalEcosystem:
    """
    Manages the economic lifecycle of AGI nodes.
    
    Implements a 'Survival of the Fittest' algorithm where nodes must pay rent
    to remain active. Rent is paid from energy gained by solving problems.
    """

    def __init__(self, global_energy_budget: float = 1000.0):
        """
        Initialize the ecosystem.
        
        Args:
            global_energy_budget: Total energy available for distribution per cycle.
        """
        self.nodes: Dict[str, AGINode] = {}
        self.global_energy_budget = global_energy_budget
        self._cycle_count = 0

    def register_node(self, node_id: str, base_cost: float, complexity: float) -> bool:
        """
        Register a new node into the ecosystem.
        
        Args:
            node_id: Unique identifier for the node.
            base_cost: Base resource consumption per cycle.
            complexity: Number of dependencies or complexity factor.
        
        Returns:
            True if registration successful, False otherwise.
        """
        try:
            if node_id in self.nodes:
                logger.warning(f"Node {node_id} already exists.")
                return False
            
            profile = EconomicProfile(
                base_cost=base_cost,
                complexity=complexity
            )
            new_node = AGINode(node_id=node_id, state=NodeState.ACTIVE, profile=profile)
            self.nodes[node_id] = new_node
            logger.info(f"Node {node_id} registered with cost {base_cost}.")
            return True
        except Exception as e:
            logger.error(f"Failed to register node {node_id}: {e}")
            return False

    def report_usage(self, node_id: str, value_generated: float, times_called: int) -> None:
        """
        Report the productivity of a node for the current cycle.
        
        Args:
            node_id: Target node ID.
            value_generated: Measured contribution to the main objective (0.0 to 1.0).
            times_called: Number of times the node was accessed.
        """
        if node_id not in self.nodes:
            logger.error(f"Usage report failed: Node {node_id} not found.")
            return

        node = self.nodes[node_id]
        if node.state != NodeState.ACTIVE:
            return # Ignore reports from inactive nodes for simplicity

        # Data validation
        value_generated = max(0.0, min(value_generated, 10.0)) # Cap value
        times_called = max(0, times_called)

        node.profile.value_score = value_generated
        node.profile.frequency = times_called
        logger.debug(f"Node {node_id} reported value: {value_generated}, calls: {times_called}.")

    def calculate_rewards(self) -> Dict[str, float]:
        """
        Core Logic: Distribute global energy budget based on value contribution.
        
        Returns:
            Dictionary of node_id to allocated energy.
        """
        active_nodes = [n for n in self.nodes.values() if n.state == NodeState.ACTIVE]
        total_value = sum(n.profile.value_score * n.profile.frequency for n in active_nodes)
        
        allocations = {}
        
        # Edge case: No value generated in system
        if total_value == 0:
            logger.warning("Total system value is zero. No energy distributed.")
            return {n.node_id: 0.0 for n in active_nodes}

        for node in active_nodes:
            contribution_weight = (node.profile.value_score * node.profile.frequency) / total_value
            reward = contribution_weight * self.global_energy_budget
            allocations[node.node_id] = reward
            
        return allocations

    def run_survival_cycle(self) -> None:
        """
        Execute one full survival cycle: Reward -> Charge Rent -> State Update.
        """
        self._cycle_count += 1
        logger.info(f"--- Starting Survival Cycle {self._cycle_count} ---")

        # 1. Distribute Rewards (Income)
        rewards = self.calculate_rewards()

        for node_id, reward in rewards.items():
            self.nodes[node_id].profile.energy_balance += reward

        # 2. Charge Rent (Expenses) & Update State
        nodes_to_archive = []
        
        for node in self.nodes.values():
            if node.state == NodeState.DEAD:
                continue

            cost = node.profile.total_maintenance_cost
            node.profile.energy_balance -= cost
            
            # Record history for analysis
            node.history.append(node.profile.energy_balance)
            if len(node.history) > 10: node.history.pop(0)

            # Check Survival Conditions
            if node.profile.energy_balance <= 0:
                self._handle_bankruptcy(node)
            elif node.profile.energy_balance < 20 and node.state == NodeState.ACTIVE:
                node.state = NodeState.DORMANT
                logger.warning(f"Node {node.node_id} is DORMANT (Low energy: {node.profile.energy_balance:.2f}).")
            elif node.profile.energy_balance > 50 and node.state == NodeState.DORMANT:
                node.state = NodeState.ACTIVE
                logger.info(f"Node {node.node_id} reactivated.")

    def _handle_bankruptcy(self, node: AGINode) -> None:
        """
        Helper function: Handles logic for nodes that run out of energy.
        """
        node_id = node.node_id
        if node.state == NodeState.DORMANT:
            node.state = NodeState.ARCHIVED
            logger.critical(f"Node {node_id} ARCHIVED (Bankrupt).")
        elif node.state == NodeState.ARCHIVED:
            # If it stays archived too long (simulated by checking history average)
            avg_energy = sum(node.history) / len(node.history) if node.history else 0
            if avg_energy < -50:
                node.state = NodeState.DEAD
                logger.critical(f"Node {node_id} PRUNED (Dead).")

    def get_ecosystem_stats(self) -> Dict:
        """Returns a summary of the current system status."""
        active = sum(1 for n in self.nodes.values() if n.state == NodeState.ACTIVE)
        dormant = sum(1 for n in self.nodes.values() if n.state == NodeState.DORMANT)
        return {
            "cycle": self._cycle_count,
            "active_nodes": active,
            "dormant_nodes": dormant,
            "total_nodes": len(self.nodes)
        }


# --- Usage Example ---
if __name__ == "__main__":
    # Initialize Ecosystem
    ecosystem = SurvivalEcosystem(global_energy_budget=500.0)

    # 1. Register Nodes (ID, Cost, Complexity)
    ecosystem.register_node("vision_encoder", base_cost=10.0, complexity=5.0) # High cost
    ecosystem.register_node("logic_core", base_cost=5.0, complexity=2.0)      # Medium cost
    ecosystem.register_node("legacy_api", base_cost=2.0, complexity=1.0)      # Low cost, rarely used

    # Simulate Cycle 1: Logic Core is very useful
    print("\n--- Cycle 1 Simulation ---")
    ecosystem.report_usage("vision_encoder", value_generated=0.5, times_called=2)
    ecosystem.report_usage("logic_core", value_generated=1.0, times_called=10) # High value
    ecosystem.report_usage("legacy_api", value_generated=0.0, times_called=0)  # Unused
    
    ecosystem.run_survival_cycle()
    
    # Check stats
    for nid, node in ecosystem.nodes.items():
        print(f"Node: {nid}, State: {node.state.name}, Energy: {node.profile.energy_balance:.2f}")

    # Simulate Cycle 2-5: Legacy API continues to be unused (Starvation test)
    print("\n--- Starvation Simulation (Cycles 2-5) ---")
    for _ in range(4):
        # Only Vision and Logic contribute
        ecosystem.report_usage("vision_encoder", 0.8, 5)
        ecosystem.report_usage("logic_core", 1.0, 5)
        ecosystem.report_usage("legacy_api", 0.0, 0) # Still unused
        
        ecosystem.run_survival_cycle()
        
        node = ecosystem.nodes["legacy_api"]
        print(f"Cycle {ecosystem._cycle_count}: Legacy API - State: {node.state.name}, Balance: {node.profile.energy_balance:.2f}")