"""
Module: bio_ecosystem_manager
Description: A sophisticated AGI skill module that models system management based on 
             biological energy flow and metabolic mechanisms. It replaces static metrics 
             with a dynamic 'Value Trophic Network', calculating Mutualism Indices and 
             Functional Redundancy. Features 'Metabolic Flux Control' to trigger 
             'Anaerobic Respiration' (low-power/hibernation mode) during resource scarcity.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# --- Configuration & Setup ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BioEcosystemManager")


class MetabolicState(Enum):
    """Enumeration of system metabolic states."""
    AEROBIC = auto()      # Normal operation, abundant resources
    ANAEROBIC = auto()    # Survival mode, scarce resources
    HOMEOSTASIS = auto()  # Maintenance mode, equilibrium


@dataclass
class ResourcePacket:
    """Represents a unit of resources (Compute/Funds/Materials)."""
    energy_units: float  # Abstracted value (e.g., USD, TFLOPS)
    source_id: str
    entropy_factor: float = 0.0  # Degradation or risk factor

    def __post_init__(self):
        if self.energy_units < 0:
            raise ValueError("Energy units cannot be negative.")


@dataclass
class SystemNode:
    """Represents a node in the value network (e.g., supplier, process, agent)."""
    node_id: str
    metabolic_cost: float  # Base cost to keep this node alive
    efficiency: float = 1.0  # Output/Input ratio
    buffer: float = 0.0
    connections: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0 < self.efficiency <= 1.5:
            logger.warning(f"Node {self.node_id} efficiency {self.efficiency} is unusual.")


class BioEcosystemManager:
    """
    Manages a complex system using bio-mimetic principles.
    
    This class treats a business or computational network like an ecosystem,
    tracking energy flow, calculating symbiotic relationships, and managing
    metabolic states during resource scarcity.
    """

    def __init__(self, initial_nodes: Optional[List[SystemNode]] = None):
        """
        Initialize the ecosystem manager.
        
        Args:
            initial_nodes: List of SystemNode objects to seed the network.
        """
        self.nodes: Dict[str, SystemNode] = {}
        self.state: MetabolicState = MetabolicState.AEROBIC
        self.global_resource_pool: float = 1000.0
        self.mutation_rate: float = 0.05  # Randomness in flow
        
        if initial_nodes:
            for node in initial_nodes:
                self.add_node(node)

    def add_node(self, node: SystemNode) -> None:
        """Adds a node to the ecosystem network."""
        if node.node_id in self.nodes:
            logger.error(f"Duplicate node ID detected: {node.node_id}")
            raise ValueError(f"Node {node.node_id} already exists.")
        
        self.nodes[node.node_id] = node
        logger.info(f"Node {node.node_id} added to ecosystem.")

    def _calculate_trophic_efficiency(self, energy_in: float) -> float:
        """
        Helper function to calculate metabolic loss based on the Second Law of Thermodynamics.
        
        Args:
            energy_in: Input energy.
            
        Returns:
            Usable energy after entropy loss.
        """
        if energy_in <= 0:
            return 0.0
        
        # Simulate entropy: efficiency drops as energy scales up (complexity tax)
        entropy_loss = math.log1p(energy_in) * 0.1 * (1 + random.random() * self.mutation_rate)
        usable_energy = energy_in - entropy_loss
        return max(0, usable_energy)

    def calculate_network_mutualism(self) -> Tuple[float, float]:
        """
        Core Function 1: Analyzes the network for mutualism (win-win) and redundancy.
        
        Simulates a food web analysis. High redundancy means the system is resilient.
        High mutualism means nodes benefit from each other.
        
        Returns:
            Tuple[float, float]: (Mutualism Index, Functional Redundancy Score)
        """
        if not self.nodes:
            return 0.0, 0.0

        mutualism_score = 0.0
        redundancy_count = 0
        
        # Check connections
        node_list = list(self.nodes.values())
        for i, node_a in enumerate(node_list):
            # Redundancy check: Are there other nodes with similar costs/efficiency?
            for node_b in node_list[i+1:]:
                if abs(node_a.metabolic_cost - node_b.metabolic_cost) < 0.1 * node_a.metabolic_cost:
                    redundancy_count += 1
            
            # Mutualism check: Is node A connected to B, and B to A?
            for conn_id in node_a.connections:
                if conn_id in self.nodes:
                    target_node = self.nodes[conn_id]
                    if node_a.node_id in target_node.connections:
                        mutualism_score += (node_a.efficiency + target_node.efficiency) / 2

        # Normalize scores
        total_possible_links = len(self.nodes) * (len(self.nodes) - 1)
        norm_mutualism = mutualism_score / max(1, total_possible_links)
        norm_redundancy = redundancy_count / max(1, len(self.nodes))
        
        logger.debug(f"Network Analysis - Mutualism: {norm_mutualism:.4f}, Redundancy: {norm_redundancy:.4f}")
        return norm_mutualism, norm_redundancy

    def perform_metabolic_flux_control(self, available_resources: float) -> str:
        """
        Core Function 2: Manages resource distribution and switches metabolic states.
        
        If resources < total demand, triggers 'Anaerobic Respiration' (survival mode)
        instead of crashing. It rations resources to critical nodes only.
        
        Args:
            available_resources: Total energy available for the cycle.
            
        Returns:
            str: A status report of the metabolic cycle.
        """
        total_demand = sum(n.metabolic_cost for n in self.nodes.values())
        balance = available_resources - total_demand
        
        report_lines = []
        
        if balance >= 0:
            # Aerobic Mode: Abundant resources
            self.state = MetabolicState.AEROBIC
            self.global_resource_pool += balance # Store excess
            report_lines.append(f"Status: AEROBIC. Demand {total_demand:.2f} met. Surplus {balance:.2f} stored.")
            
            # Distribute full energy to nodes
            for node in self.nodes.values():
                intake = self._calculate_trophic_efficiency(node.metabolic_cost)
                node.buffer += intake
                
        else:
            # Anaerobic Mode: Scarcity
            self.state = MetabolicState.ANAEROBIC
            report_lines.append(f"Status: ANAEROBIC. Deficit of {-balance:.2f}. Initiating survival protocols.")
            
            # Rationing: Distribute what we have proportionally or by priority
            # Here we implement strict proportional rationing
            rationing_factor = available_resources / total_demand if total_demand > 0 else 0
            
            for node in self.nodes.values():
                allocated = node.metabolic_cost * rationing_factor
                # Anaerobic respiration is less efficient (generates lactate/toxins metaphorically)
                intake = self._calculate_trophic_efficiency(allocated) * 0.8 
                node.buffer += intake
                if node.buffer < node.metabolic_cost * 0.5:
                    report_lines.append(f"WARNING: Node {node.node_id} is starving!")

        return "\n".join(report_lines)

    def run_cycle(self, external_input: float) -> Dict[str, str]:
        """
        Executes a full biological cycle of the system.
        
        Args:
            external_input: Incoming resources from the environment.
            
        Returns:
            dict: A summary of the system state and health.
        """
        logger.info(f"Starting cycle with input: {external_input}")
        
        # 1. Ingest Resources
        total_resources = self.global_resource_pool + external_input
        
        # 2. Metabolic Control
        status_report = self.perform_metabolic_flux_control(total_resources)
        
        # 3. Network Analysis
        mutualism, redundancy = self.calculate_network_mutualism()
        
        # 4. Health Check
        health_status = "HEALTHY" if self.state == MetabolicState.AEROBIC else "STRESSED"
        
        return {
            "metabolic_status": self.state.name,
            "health": health_status,
            "details": status_report,
            "metrics": {
                "mutualism_index": round(mutualism, 4),
                "redundancy_score": round(redundancy, 4),
                "reservoir": round(self.global_resource_pool, 2)
            }
        }

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Nodes (Simulating a supply chain or process network)
    node_a = SystemNode("Raw_Materials", metabolic_cost=100, efficiency=1.2, connections=["Manufacturing"])
    node_b = SystemNode("Manufacturing", metabolic_cost=300, efficiency=1.0, connections=["Raw_Materials", "Logistics"])
    node_c = SystemNode("Logistics", metabolic_cost=150, efficiency=0.9, connections=["Manufacturing"])
    node_d = SystemNode("Backup_Logistics", metabolic_cost=140, efficiency=0.85, connections=["Manufacturing"])

    # 2. Initialize Manager
    ecosystem = BioEcosystemManager([node_a, node_b, node_c, node_d])

    print("--- Cycle 1: Abundant Resources ---")
    result1 = ecosystem.run_cycle(external_input=1000.0)
    print(result1['details'])
    print(f"Metrics: {result1['metrics']}\n")

    print("--- Cycle 2: Resource Drought (Anaerobic Test) ---")
    result2 = ecosystem.run_cycle(external_input=50.0) # Drastic drop
    print(result2['details'])
    print(f"Metrics: {result2['metrics']}")