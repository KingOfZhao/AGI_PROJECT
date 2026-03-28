"""
Causal Inference based Credit Allocation Path Tracker

This module provides a mechanism to trace execution paths in a skill tree,
monitoring each node to allocate credit based on causal inference principles.
It implements a simplified counterfactual analysis to determine the contribution
of each node to the final global outcome.

Classes:
    TraceNode: Data class representing a single node in the execution trace.
    CausalPathTracer: Main class for managing traces and calculating credit.

Functions:
    start_node: Records the entry point of a skill execution.
    end_node: Records the exit point and calculates causal credit.
    validate_payload: Helper function to validate input/output data structures.

Example Usage:
    >>> tracer = CausalPathTracer()
    >>> root_id = tracer.start_node("Root_Skill", None, {"query": "test"})
    >>> # ... perform logic ...
    >>> credit = tracer.end_node(root_id, {"result": "success"}, global_reward=1.0)
    >>> print(f"Node Credit: {credit}")
"""

import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TraceNode:
    """
    Represents a single node in the skill execution tree.
    
    Attributes:
        node_id (str): Unique identifier for the node.
        parent_id (Optional[str]): ID of the parent node.
        name (str): Name of the skill/function.
        start_time (float): Timestamp of execution start.
        end_time (Optional[float]): Timestamp of execution end.
        input_data (Optional[Dict]): Input payload.
        output_data (Optional[Dict]): Output payload.
        causal_credit (float): Calculated credit based on causal inference.
        status (str): Execution status (RUNNING, SUCCESS, FAILED).
    """
    node_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    causal_credit: float = 0.0
    status: str = "RUNNING"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the node to a dictionary."""
        return asdict(self)


class CausalPathTracer:
    """
    Manages the execution tree and performs causal credit allocation.
    
    The credit allocation uses a simplified counterfactual approach:
    If a node's output is valid and the global reward is high, the node
    receives positive credit. If the node fails, it receives negative credit,
    propagating causality upwards.
    """
    
    def __init__(self):
        """Initialize the tracer with an empty node registry."""
        self._nodes: Dict[str, TraceNode] = {}
        self._root_id: Optional[str] = None

    def _validate_payload(self, data: Any) -> bool:
        """
        Helper function to validate data payloads.
        
        Args:
            data: The data to validate.
            
        Returns:
            bool: True if data is a dictionary or None, False otherwise.
        """
        if data is None:
            return True
        if not isinstance(data, dict):
            logger.warning(f"Invalid payload type: {type(data)}. Expected dict or None.")
            return False
        return True

    def start_node(self, name: str, parent_id: Optional[str], 
                   input_data: Optional[Dict[str, Any]]) -> str:
        """
        Records the start of a skill execution (Core Function 1).
        
        Args:
            name: Name of the skill being executed.
            parent_id: ID of the parent skill. None for root.
            input_data: Input arguments for the skill.
            
        Returns:
            str: The unique ID generated for this node.
            
        Raises:
            ValueError: If parent_id is provided but not found in registry.
        """
        if not self._validate_payload(input_data):
            raise ValueError("Input data validation failed.")

        node_id = str(uuid.uuid4())
        current_time = time.time()

        if parent_id and parent_id not in self._nodes:
            logger.error(f"Parent node {parent_id} not found.")
            raise ValueError(f"Parent node {parent_id} does not exist.")

        if self._root_id is None:
            self._root_id = node_id

        new_node = TraceNode(
            node_id=node_id,
            parent_id=parent_id,
            name=name,
            start_time=current_time,
            input_data=input_data,
            status="RUNNING"
        )
        
        self._nodes[node_id] = new_node
        logger.info(f"Started node: {name} (ID: {node_id})")
        return node_id

    def end_node(self, node_id: str, output_data: Optional[Dict[str, Any]], 
                 global_reward: float) -> float:
        """
        Records the end of a skill execution and calculates causal credit (Core Function 2).
        
        Args:
            node_id: ID of the node ending execution.
            output_data: Result produced by the skill.
            global_reward: The overall reward/success signal of the AGI task (0.0 to 1.0).
            
        Returns:
            float: The calculated causal credit for this node.
            
        Raises:
            ValueError: If node_id is not found or global_reward is out of bounds.
        """
        if node_id not in self._nodes:
            logger.error(f"Node {node_id} not found for termination.")
            raise ValueError(f"Node {node_id} does not exist.")
            
        if not 0.0 <= global_reward <= 1.0:
            logger.error(f"Global reward {global_reward} out of bounds [0.0, 1.0].")
            raise ValueError("Global reward must be between 0.0 and 1.0.")

        if not self._validate_payload(output_data):
            raise ValueError("Output data validation failed.")

        node = self._nodes[node_id]
        node.end_time = time.time()
        node.output_data = output_data
        
        # Causal Inference Logic:
        # Credit is proportional to global reward and output validity.
        # We simulate a counterfactual: if this node failed, how much would reward drop?
        # Simplified: Credit = Global Reward * (Output Validity Factor)
        
        output_validity = 1.0 if output_data is not None else 0.0
        duration = node.end_time - node.start_time
        
        # Penalize extremely long executions slightly (efficiency penalty)
        efficiency_penalty = min(0.1, duration / 100.0) 
        
        node.causal_credit = (global_reward * output_validity) - efficiency_penalty
        
        if output_data is None:
            node.status = "FAILED"
            node.causal_credit = -1.0 * global_reward # Strong negative causality for failure
        else:
            node.status = "SUCCESS"

        logger.info(
            f"Ended node: {node.name} (ID: {node_id}) | "
            f"Credit: {node.causal_credit:.4f} | Status: {node.status}"
        )
        
        return node.causal_credit

    def get_execution_tree(self) -> List[Dict[str, Any]]:
        """
        Helper function to reconstruct the tree structure from the flat node map.
        
        Returns:
            List[Dict]: A list of root nodes (usually one) with nested children.
        """
        if not self._nodes:
            return []

        node_map = {nid: node.to_dict() for nid, node in self._nodes.items()}
        roots = []
        
        # Build hierarchy
        for nid, node in node_map.items():
            parent_id = node.get('parent_id')
            if parent_id is None:
                roots.append(node)
            else:
                if parent_id in node_map:
                    if 'children' not in node_map[parent_id]:
                        node_map[parent_id]['children'] = []
                    node_map[parent_id]['children'].append(node)
                else:
                    logger.warning(f"Orphan node found: {nid} pointing to missing parent {parent_id}")
                    
        return roots

    def get_node_statistics(self) -> Dict[str, Any]:
        """
        Aggregates statistics across all traced nodes.
        
        Returns:
            Dict: Summary statistics including total nodes, avg credit, and failure rate.
        """
        total_nodes = len(self._nodes)
        if total_nodes == 0:
            return {"total_nodes": 0}

        credits = [n.causal_credit for n in self._nodes.values()]
        failures = sum(1 for n in self._nodes.values() if n.status == "FAILED")
        
        return {
            "total_nodes": total_nodes,
            "average_credit": sum(credits) / total_nodes,
            "total_failures": failures,
            "failure_rate": failures / total_nodes
        }


if __name__ == "__main__":
    # Example Usage Demonstration
    tracer = CausalPathTracer()
    
    try:
        # 1. Start Root Node
        root_id = tracer.start_node("AGI_Main_Task", None, {"task": "optimize_portfolio"})
        
        # 2. Start Child Node A
        child_a_id = tracer.start_node("Data_Fetcher", root_id, {"source": "api"})
        
        # 3. End Child Node A (Success)
        tracer.end_node(child_a_id, {"data_points": 500}, global_reward=0.8)
        
        # 4. Start Child Node B
        child_b_id = tracer.start_node("Strategy_Model", root_id, {"model": "transformer"})
        
        # 5. End Child Node B (Partial Success)
        tracer.end_node(child_b_id, {"confidence": 0.6}, global_reward=0.8)
        
        # 6. End Root Node
        tracer.end_node(root_id, {"final_allocation": "optimal"}, global_reward=0.8)
        
        # 7. Output Results
        tree = tracer.get_execution_tree()
        stats = tracer.get_node_statistics()
        
        import json
        print("\n--- Execution Tree ---")
        print(json.dumps(tree, indent=2))
        print("\n--- Statistics ---")
        print(json.dumps(stats, indent=2))
        
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")