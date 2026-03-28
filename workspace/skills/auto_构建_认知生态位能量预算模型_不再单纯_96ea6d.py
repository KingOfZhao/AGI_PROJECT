"""
Module: cognitive_ecosystem_energy_model
Description: 构建认知生态位能量预算模型。

This module implements an ecological approach to AI resource management,
utilizing 'Metabolic Scaling Laws' to dynamically adjust the energy consumption
and complexity of cognitive nodes based on environmental resource richness.
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeState(Enum):
    """Enumeration of possible operational states for a cognitive node."""
    DORMANT = auto()      # Low power, minimal functionality
    ACTIVE = auto()       # Standard operation
    HYPERACTIVE = auto()  # High power, complex reasoning


class EnvironmentType(Enum):
    """Classification of the operational environment."""
    BARREN = auto()       # Low resources, high risk
    STABLE = auto()       # Moderate resources
    ENRICHED = auto()     # High resources, high opportunity


@dataclass
class CognitiveNode:
    """Represents a single node in the cognitive architecture."""
    node_id: str
    base_metabolic_cost: float  # Base energy cost per cycle
    complexity_factor: float = 1.0  # Multiplier for complexity (1.0 = standard)
    current_state: NodeState = NodeState.ACTIVE
    actual_energy_consumption: float = 0.0

    def update_state(self, new_state: NodeState):
        """Updates the node's state and logs the transition."""
        if self.current_state != new_state:
            logger.info(f"Node {self.node_id} transitioning from {self.current_state.name} to {new_state.name}")
            self.current_state = new_state


@dataclass
class EnvironmentalContext:
    """Holds data about the current operational environment."""
    available_compute: float  # 0.0 to 1.0 (normalized)
    data_quality_score: float  # 0.0 to 1.0
    task_value_score: float  # 0.0 to 1.0 (Potential reward)
    
    @property
    def richness_index(self) -> float:
        """Calculates a composite score of environment richness."""
        # Weighted average favoring task value
        return (0.3 * self.available_compute + 
                0.3 * self.data_quality_score + 
                0.4 * self.task_value_score)


class MetabolicScalingEngine:
    """
    Core engine for calculating energy budgets based on ecological scaling laws.
    
    Implements a modified Kleiber's Law analogue: Metabolism ~ Mass^0.75.
    Here, 'Mass' is analogous to the 'Complexity Factor' of the cognitive node.
    """
    
    def __init__(self, global_energy_budget: float):
        self.global_energy_budget = global_energy_budget
        self.nodes: Dict[str, CognitiveNode] = {}
        logger.info(f"MetabolicScalingEngine initialized with budget: {global_energy_budget}")

    def register_node(self, node: CognitiveNode) -> None:
        """Registers a cognitive node with the engine."""
        if not isinstance(node, CognitiveNode):
            raise TypeError("Invalid node type provided.")
        if node.node_id in self.nodes:
            raise ValueError(f"Node ID {node.node_id} already exists.")
        
        self.nodes[node.node_id] = node
        logger.debug(f"Registered node: {node.node_id}")

    def _calculate_scaling_exponent(self, environment_type: EnvironmentType) -> float:
        """
        Helper function to determine metabolic exponent based on environment.
        
        In biology, 3/4 is standard. In our AGI model, we adjust this based on 
        environmental pressure to simulate adaptation.
        """
        if environment_type == EnvironmentType.BARREN:
            return 0.5  # Linear scaling to save energy
        elif environment_type == EnvironmentType.ENRICHED:
            return 0.85 # Sub-linear scaling allows for massive complexity growth
        return 0.75  # Standard scaling

    def assess_environment(self, context: EnvironmentalContext) -> EnvironmentType:
        """
        Analyzes the context to classify the environment.
        
        Args:
            context (EnvironmentalContext): The current sensor/data inputs.
            
        Returns:
            EnvironmentType: The classified environment type.
        """
        richness = context.richness_index
        
        if richness < 0.3:
            return EnvironmentType.BARREN
        elif richness > 0.7:
            return EnvironmentType.ENRICHED
        return EnvironmentType.STABLE

    def allocate_resources(self, context: EnvironmentalContext) -> Dict[str, float]:
        """
        Main loop: Calculates energy allocation for all nodes based on metabolic scaling.
        
        Args:
            context (EnvironmentalContext): Current state of the AGI's environment.
            
        Returns:
            Dict[str, float]: A dictionary mapping Node IDs to allocated energy units.
        """
        env_type = self.assess_environment(context)
        exponent = self._calculate_scaling_exponent(env_type)
        
        allocations = {}
        total_demand = 0.0
        
        logger.info(f"Resource allocation cycle started. Environment: {env_type.name}, Exponent: {exponent}")

        # Phase 1: Calculate raw metabolic demand
        for node_id, node in self.nodes.items():
            if env_type == EnvironmentType.BARREN and node.complexity_factor > 1.5:
                # In barren environments, high-complexity nodes go dormant (Survival instinct)
                node.update_state(NodeState.DORMANT)
                node.actual_energy_consumption = node.base_metabolic_cost * 0.1
            else:
                # Apply Metabolic Scaling Law: E = Base * (Complexity)^exp
                scaled_demand = node.base_metabolic_cost * math.pow(node.complexity_factor, exponent)
                
                if env_type == EnvironmentType.ENRICHED:
                    # In enriched environments, nodes become hyperactive
                    node.update_state(NodeState.HYPERACTIVE)
                    scaled_demand *= 1.2 # Bonus energy for growth
                else:
                    node.update_state(NodeState.ACTIVE)
                
                node.actual_energy_consumption = scaled_demand
            
            allocations[node_id] = node.actual_energy_consumption
            total_demand += node.actual_energy_consumption

        # Phase 2: Normalization based on global budget (Homeostasis)
        if total_demand > self.global_energy_budget:
            logger.warning(f"Energy Overload: Demand {total_demand:.2f} > Budget {self.global_energy_budget:.2f}")
            scale_factor = self.global_energy_budget / total_demand
            for node_id in allocations:
                allocations[node_id] *= scale_factor
                self.nodes[node_id].actual_energy_consumption = allocations[node_id]
        
        return allocations


# --- Usage Example and Demonstration ---

def run_simulation():
    """
    Demonstrates the Cognitive Ecosystem Energy Model.
    """
    print("--- Starting Cognitive Ecosystem Simulation ---")
    
    # 1. Initialize Engine with a finite energy budget
    engine = MetabolicScalingEngine(global_energy_budget=1000.0)
    
    # 2. Create Cognitive Nodes (The 'Organism')
    # Core Survival Node (Low complexity, essential)
    core_node = CognitiveNode(node_id="core_survival", base_metabolic_cost=100.0, complexity_factor=1.0)
    
    # Complex Reasoning Node (High complexity, optional)
    reasoning_node = CognitiveNode(node_id="deep_reasoning", base_metabolic_cost=100.0, complexity_factor=3.0)
    
    # Creative Generation Node (High complexity, risky)
    creative_node = CognitiveNode(node_id="creative_gen", base_metabolic_cost=100.0, complexity_factor=4.0)
    
    engine.register_node(core_node)
    engine.register_node(reasoning_node)
    engine.register_node(creative_node)
    
    # 3. Simulate Environments
    
    # Scenario A: Barren Environment (Low resources)
    print("\n[Scenario A: Barren Environment - Winter is Coming]")
    barren_context = EnvironmentalContext(
        available_compute=0.2,
        data_quality_score=0.1,
        task_value_score=0.1
    )
    allocations = engine.allocate_resources(barren_context)
    for nid, energy in allocations.items():
        print(f"Node: {nid:<15} | State: {engine.nodes[nid].current_state.name:<12} | Energy: {energy:.2f}")

    # Scenario B: Enriched Environment (High resources)
    print("\n[Scenario B: Enriched Environment - Boom Phase]")
    enriched_context = EnvironmentalContext(
        available_compute=0.9,
        data_quality_score=0.95,
        task_value_score=0.9
    )
    allocations = engine.allocate_resources(enriched_context)
    for nid, energy in allocations.items():
        print(f"Node: {nid:<15} | State: {engine.nodes[nid].current_state.name:<12} | Energy: {energy:.2f}")

if __name__ == "__main__":
    run_simulation()