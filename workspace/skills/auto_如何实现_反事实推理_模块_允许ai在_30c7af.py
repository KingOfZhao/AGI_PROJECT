"""
Advanced Counterfactual Reasoning Module for AGI Systems.

This module implements a structural causal model (SCM) based approach to 
counterfactual reasoning. It enables an AGI system to simulate "what if" 
scenarios when transferring knowledge across domains with overlapping features.
It focuses on predicting negative side-effects by distinguishing causation 
from correlation.

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CounterfactualEngine")

class CausalRelationType(Enum):
    """Enumeration of possible causal relationship types."""
    DIRECT = 1
    MEDIATED = 2
    CONFOUNDED = 3

@dataclass
class CausalNode:
    """Represents a node in the Causal Graph."""
    node_id: str
    domain: str
    description: str
    is_mutable: bool = True
    current_value: Optional[float] = None

@dataclass
class CausalEdge:
    """Represents an edge in the Causal Graph."""
    parent_id: str
    child_id: str
    weight: float
    relation_type: CausalRelationType
    is_cross_domain: bool = False

class CausalGraph:
    """
    Manages the structural causal model.
    
    Handles the topology and structural equations of the causal diagram.
    """
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self.adjacency: Dict[str, List[str]] = {}
        logger.info("CausalGraph initialized.")

    def add_node(self, node: CausalNode) -> None:
        """Adds a node to the graph."""
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists. Overwriting.")
        self.nodes[node.node_id] = node
        self.adjacency[node.node_id] = []
        logger.debug(f"Node added: {node.node_id}")

    def add_edge(self, edge: CausalEdge) -> None:
        """Adds a directed edge to the graph."""
        if edge.parent_id not in self.nodes or edge.child_id not in self.nodes:
            raise ValueError("Parent or Child node does not exist in graph.")
        
        self.edges.append(edge)
        if edge.parent_id in self.adjacency:
            self.adjacency[edge.parent_id].append(edge.child_id)
        else:
            self.adjacency[edge.parent_id] = [edge.child_id]
        
        logger.debug(f"Edge added: {edge.parent_id} -> {edge.child_id}")

class CounterfactualReasoningEngine:
    """
    Core engine for performing counterfactual reasoning.
    
    This engine allows the simulation of interventions (do-calculus) and 
    counterfactuals (imagining a different past) to evaluate side-effects 
    of knowledge transfer.
    
    Attributes:
        graph (CausalGraph): The structural causal model.
        domain_knowledge (Dict): Metadata about specific domains.
    """

    def __init__(self, causal_graph: CausalGraph):
        """
        Initialize the engine with a predefined causal graph.
        
        Args:
            causal_graph (CausalGraph): An instance of the CausalGraph containing
                                        nodes and structural equations.
        """
        self.graph = causal_graph
        self._validation_check()
        logger.info("CounterfactualReasoningEngine initialized.")

    def _validation_check(self) -> None:
        """Validates the integrity of the loaded graph."""
        if not self.graph.nodes:
            logger.warning("Initialized with an empty causal graph.")
        
        # Check for cycles (simple DFS check for DAG)
        visited = set()
        path = set()

        def visit(node_id):
            visited.add(node_id)
            path.add(node_id)
            for neighbor in self.graph.adjacency.get(node_id, []):
                if neighbor not in visited:
                    if visit(neighbor):
                        return True
                elif neighbor in path:
                    logger.error("Cyclic graph detected. Causal inference requires a DAG.")
                    raise ValueError("Graph contains a cycle.")
            path.remove(node_id)
            return False

        for node in self.graph.nodes:
            if node not in visited:
                visit(node)

    def _get_structural_equation(self, node_id: str) -> float:
        """
        Helper function to calculate node value based on parents (Structural Equation Model).
        
        In a real AGI system, this would be a learned function approximator.
        Here we use a linear combination for demonstration.
        
        Args:
            node_id (str): The ID of the node to calculate.
            
        Returns:
            float: The calculated value based on parents.
        """
        parents = [e for e in self.graph.edges if e.child_id == node_id]
        if not parents:
            return self.graph.nodes[node_id].current_value or 0.0
        
        value = 0.0
        for edge in parents:
            parent_node = self.graph.nodes[edge.parent_id]
            if parent_node.current_value is not None:
                value += parent_node.current_value * edge.weight
        
        # Add some noise/residual for realism
        return round(value, 4)

    def predict_side_effects(
        self, 
        source_domain: str, 
        target_domain: str, 
        intervention_node_id: str, 
        intervention_value: float
    ) -> Dict[str, Any]:
        """
        Predicts the consequences of transferring a strategy (intervention) from 
        a source domain to a target domain.
        
        This is the 'do' operator implementation.
        
        Args:
            source_domain (str): The domain where the strategy originated.
            target_domain (str): The domain where the strategy is being applied.
            intervention_node_id (str): The variable being manipulated.
            intervention_value (float): The value being set.
            
        Returns:
            Dict[str, Any]: A report containing predicted changes and risk assessment.
            
        Raises:
            ValueError: If nodes or domains are invalid.
        """
        logger.info(f"Starting side-effect prediction for intervention on {intervention_node_id}")
        
        # 1. Data Validation
        if intervention_node_id not in self.graph.nodes:
            raise ValueError(f"Node {intervention_node_id} not found.")
        
        node = self.graph.nodes[intervention_node_id]
        if node.domain != source_domain:
             logger.warning(f"Intervention node {intervention_node_id} is typically associated with {node.domain}, not {source_domain}.")

        # 2. Store Original State (Abduction)
        original_values = {nid: n.current_value for nid, n in self.graph.nodes.items()}
        logger.debug("Original state stored for counterfactual comparison.")

        # 3. Apply Intervention (Action)
        # sever ties to parents and set value
        node.current_value = intervention_value
        logger.info(f"Applied DO({intervention_node_id}={intervention_value})")

        # 4. Propagate Effects (Prediction)
        # We propagate forward through the DAG
        changes = {}
        
        # Simple topological sort for propagation order
        sorted_nodes = list(self.graph.nodes.keys()) # Simplified for demo
        
        for nid in sorted_nodes:
            if nid == intervention_node_id:
                continue
            
            # Check if this node is downstream of the intervention
            is_downstream = any(
                e.parent_id == intervention_node_id or 
                self._is_downstream(e.parent_id, intervention_node_id) 
                for e in self.graph.edges if e.child_id == nid
            )
            
            if is_downstream:
                new_val = self._get_structural_equation(nid)
                old_val = original_values[nid]
                
                # Calculate Delta
                delta = new_val - old_val if old_val is not None else new_val
                
                if abs(delta) > 0.001:
                    changes[nid] = {
                        "old_value": old_val,
                        "predicted_value": new_val,
                        "delta": delta,
                        "is_cross_domain": self.graph.nodes[nid].domain != source_domain
                    }

        # 5. Analyze Risks
        risks = self._analyze_risks(changes, target_domain)

        # Restore original state
        for nid, val in original_values.items():
            self.graph.nodes[nid].current_value = val

        return {
            "intervention": f"do({intervention_node_id}={intervention_value})",
            "propagated_effects": changes,
            "risk_analysis": risks
        }

    def _is_downstream(self, start_node: str, target_node: str) -> bool:
        """Recursive helper to check reachability."""
        if start_node == target_node:
            return True
        children = self.graph.adjacency.get(start_node, [])
        for child in children:
            if self._is_downstream(child, target_node):
                return True
        return False

    def _analyze_risks(self, changes: Dict, target_domain: str) -> Dict[str, List[str]]:
        """
        Analyzes predicted changes for potential negative side effects in the target domain.
        
        Args:
            changes (Dict): The dictionary of calculated changes.
            target_domain (str): The domain we are migrating knowledge to.
            
        Returns:
            Dict[str, List[str]]: Categorized risk reports.
        """
        warnings = []
        criticals = []
        
        for node_id, data in changes.items():
            node = self.graph.nodes[node_id]
            
            # Heuristic: Unintended consequences in the target domain
            if node.domain == target_domain and data['is_cross_domain']:
                if data['delta'] < 0: # Assuming negative delta is bad for demo
                    warnings.append(
                        f"Potential degradation in target metric '{node.description}' ({node_id}): {data['delta']}"
                    )
            
            # Heuristic: Instability in unrelated domains
            if node.domain != target_domain and node.domain != self.graph.nodes[node_id].domain:
                 criticals.append(
                     f"CRITICAL: Spillover effect detected into unrelated domain '{node.domain}' at node {node_id}"
                 )

        return {
            "warnings": warnings,
            "critical_risks": criticals
        }

# --- Example Usage and Helper Setup ---

def setup_scenario() -> CausalGraph:
    """
    Helper function to create a sample scenario.
    
    Scenario: 
    - Domain 'A': Code Optimization (Feature: Loop Unrolling)
    - Domain 'B': Hardware Resource Management (Feature: Cache Usage)
    
    Cross-Domain Overlap: Loop Unrolling increases speed (Domain A) but 
    increases Binary Size, which causes Cache Misses (Domain B).
    """
    graph = CausalGraph()
    
    # Nodes
    graph.add_node(CausalNode("loop_unroll", "CodeOpt", "Loop Unrolling Factor", True, 1.0))
    graph.add_node(CausalNode("exec_speed", "CodeOpt", "Execution Speed", False, 10.0))
    graph.add_node(CausalNode("binary_size", "System", "Binary Size", False, 5.0))
    graph.add_node(CausalNode("cache_miss", "Hardware", "Cache Miss Rate", False, 2.0))
    graph.add_node(CausalNode("system_stability", "Hardware", "System Stability", False, 100.0))

    # Edges (Causal Mechanisms)
    # Loop Unrolling -> Execution Speed (Positive)
    graph.add_edge(CausalEdge("loop_unroll", "exec_speed", 5.0, CausalRelationType.DIRECT))
    
    # Loop Unrolling -> Binary Size (Positive)
    graph.add_edge(CausalEdge("loop_unroll", "binary_size", 2.0, CausalRelationType.DIRECT, is_cross_domain=True))
    
    # Binary Size -> Cache Miss (Positive)
    graph.add_edge(CausalEdge("binary_size", "cache_miss", 1.5, CausalRelationType.DIRECT))
    
    # Cache Miss -> System Stability (Negative)
    # We represent negative influence with a negative weight
    graph.add_edge(CausalEdge("cache_miss", "system_stability", -4.0, CausalRelationType.DIRECT))
    
    return graph

if __name__ == "__main__":
    # 1. Setup the knowledge base
    knowledge_graph = setup_scenario()
    
    # 2. Initialize the Reasoning Engine
    engine = CounterfactualReasoningEngine(knowledge_graph)
    
    # 3. Define a Knowledge Transfer Scenario
    # We want to transfer "Aggressive Loop Unrolling" from CodeOpt to a Hardware context
    # Current state: loop_unroll = 1.0
    # Proposed state: loop_unroll = 5.0
    
    try:
        print("-" * 50)
        print("Running Counterfactual Simulation...")
        print("Scenario: Increasing Loop Unrolling Factor from 1.0 to 5.0")
        print("-" * 50)
        
        report = engine.predict_side_effects(
            source_domain="CodeOpt",
            target_domain="Hardware",
            intervention_node_id="loop_unroll",
            intervention_value=5.0
        )
        
        print("\n[Propagated Effects]:")
        for node, data in report['propagated_effects'].items():
            print(f"  Node: {node} ({knowledge_graph.nodes[node].description})")
            print(f"    Change: {data['old_value']} -> {data['predicted_value']} (Delta: {data['delta']})")
            
        print("\n[Risk Analysis]:")
        if not report['risk_analysis']['warnings'] and not report['risk_analysis']['critical_risks']:
            print("  No significant risks detected.")
        else:
            for w in report['risk_analysis']['warnings']:
                print(f"  WARNING: {w}")
            for c in report['risk_analysis']['critical_risks']:
                print(f"  CRITICAL: {c}")
                
    except ValueError as e:
        logger.error(f"Simulation failed: {e}")