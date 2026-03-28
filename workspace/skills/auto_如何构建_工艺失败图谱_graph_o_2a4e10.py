"""
Module: auto_如何构建_工艺失败图谱_graph_o_2a4e10
Description: Implementation for constructing a 'Graph of Failure' (GoF).
             This module systemically records and structures erroneous operations
             and their specific consequences to form a reverse constraint graph.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FailureNode:
    """
    Represents a specific error operation node in the graph.
    
    Attributes:
        id: Unique identifier for the node.
        operation: The erroneous operation performed (e.g., "kneading dough").
        error_type: Classification of the error (e.g., "TimeExcess", "TempHigh").
        description: Detailed description of the wrong action.
        timestamp: Creation time.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""
    error_type: str = "GenericError"
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not self.operation:
            raise ValueError("FailureNode 'operation' cannot be empty.")

@dataclass
class ConsequenceNode:
    """
    Represents the specific negative outcome resulting from a failure.
    
    Attributes:
        id: Unique identifier.
        consequence: The specific result (e.g., "gluten breakdown").
        severity: Impact level (1-10).
        observable_symptoms: List of observable traits (e.g., "sour taste", "sticky texture").
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    consequence: str = ""
    severity: int = 1
    observable_symptoms: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not (1 <= self.severity <= 10):
            raise ValueError("Severity must be between 1 and 10.")

@dataclass
class FailureEdge:
    """
    Represents the causal link between an operation and a consequence.
    
    Attributes:
        source_id: ID of the FailureNode.
        target_id: ID of the ConsequenceNode.
        mechanism: The physical/chemical mechanism explaining the failure.
        constraints_generated: List of constraints derived to prevent this failure.
    """
    source_id: str = ""
    target_id: str = ""
    mechanism: str = ""
    constraints_generated: List[str] = field(default_factory=list)

class GraphOfFailureBuilder:
    """
    Core class for constructing the Graph of Failure.
    Acts as a knowledge engineering tool to map 'Wrong Actions' -> 'Bad Results'.
    """

    def __init__(self, graph_name: str = "DefaultProcessFailureGraph"):
        """
        Initialize the graph container.
        
        Args:
            graph_name: Name identifier for this specific failure graph.
        """
        self.graph_name = graph_name
        self._operations: Dict[str, FailureNode] = {}
        self._consequences: Dict[str, ConsequenceNode] = {}
        self._edges: List[FailureEdge] = []
        self._constraint_index: Dict[str, Set[str]] = {} # Quick lookup for constraints
        logger.info(f"Initialized GraphOfFailureBuilder for '{graph_name}'")

    def _validate_input_data(self, data: Dict[str, Any], required_keys: List[str]) -> bool:
        """
        Helper function to validate input dictionaries.
        
        Args:
            data: Input data dictionary.
            required_keys: List of keys that must exist in data.
            
        Returns:
            True if valid, False otherwise.
        """
        if not isinstance(data, dict):
            logger.error("Input data must be a dictionary.")
            return False
        
        missing = [key for key in required_keys if key not in data]
        if missing:
            logger.error(f"Missing required keys: {missing}")
            return False
        return True

    def add_failure_operation(self, op_data: Dict[str, str]) -> Optional[str]:
        """
        Adds a failure operation node to the graph.
        
        Args:
            op_data: Dictionary containing 'operation', 'error_type', 'description'.
            
        Returns:
            The ID of the created node, or None if failed.
        """
        try:
            if not self._validate_input_data(op_data, ['operation']):
                return None

            node = FailureNode(
                operation=op_data['operation'],
                error_type=op_data.get('error_type', 'Unknown'),
                description=op_data.get('description', '')
            )
            
            self._operations[node.id] = node
            logger.debug(f"Added Failure Operation: {node.operation} (ID: {node.id})")
            return node.id
            
        except Exception as e:
            logger.error(f"Failed to add failure operation: {str(e)}")
            return None

    def add_consequence(self, cons_data: Dict[str, Any]) -> Optional[str]:
        """
        Adds a consequence node to the graph.
        
        Args:
            cons_data: Dictionary containing 'consequence', 'severity', 'symptoms'.
            
        Returns:
            The ID of the created node, or None if failed.
        """
        try:
            if not self._validate_input_data(cons_data, ['consequence']):
                return None
                
            severity = int(cons_data.get('severity', 1))
            
            node = ConsequenceNode(
                consequence=cons_data['consequence'],
                severity=severity,
                observable_symptoms=cons_data.get('symptoms', [])
            )
            
            self._consequences[node.id] = node
            logger.debug(f"Added Consequence: {node.consequence} (Severity: {node.severity})")
            return node.id
            
        except ValueError as ve:
            logger.error(f"Validation error adding consequence: {ve}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error adding consequence: {e}")
            return None

    def link_failure_to_consequence(
        self, 
        op_id: str, 
        cons_id: str, 
        mechanism: str, 
        constraints: List[str]
    ) -> bool:
        """
        Creates a causal edge between an operation and a consequence.
        
        Args:
            op_id: ID of the source FailureNode.
            cons_id: ID of the target ConsequenceNode.
            mechanism: Explanation of why A caused B.
            constraints: List of preventative constraints.
            
        Returns:
            True if edge created successfully.
        """
        if op_id not in self._operations:
            logger.error(f"Operation ID {op_id} not found.")
            return False
        if cons_id not in self._consequences:
            logger.error(f"Consequence ID {cons_id} not found.")
            return False

        edge = FailureEdge(
            source_id=op_id,
            target_id=cons_id,
            mechanism=mechanism,
            constraints_generated=constraints
        )
        
        self._edges.append(edge)
        
        # Indexing constraints for reverse lookup
        for constraint in constraints:
            if constraint not in self._constraint_index:
                self._constraint_index[constraint] = set()
            self._constraint_index[constraint].add(op_id)
            
        logger.info(f"Linked Op:{op_id} -> Cons:{cons_id} with {len(constraints)} constraints.")
        return True

    def generate_reverse_constraint_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates a structured map useful for AGI decision making.
        Maps specific constraints to the failures they prevent.
        
        Returns:
            A dictionary mapping constraints to failure details.
        """
        constraint_map: Dict[str, List[Dict[str, Any]]] = {}
        
        for edge in self._edges:
            source_op = self._operations.get(edge.source_id)
            target_cons = self._consequences.get(edge.target_id)
            
            if not source_op or not target_cons:
                continue
                
            for constraint in edge.constraints_generated:
                entry = {
                    "prevented_operation": source_op.operation,
                    "avoided_consequence": target_cons.consequence,
                    "mechanism": edge.mechanism,
                    "severity": target_cons.severity
                }
                
                if constraint not in constraint_map:
                    constraint_map[constraint] = []
                constraint_map[constraint].append(entry)
                
        return constraint_map

    def export_graph(self, format: str = 'dict') -> Any:
        """
        Exports the graph structure.
        
        Args:
            format: 'dict' for Python dictionary, 'json' for JSON string.
        """
        data = {
            "metadata": {
                "name": self.graph_name,
                "nodes_count": len(self._operations) + len(self._consequences),
                "edges_count": len(self._edges),
                "generated_at": datetime.now().isoformat()
            },
            "operations": [asdict(op) for op in self._operations.values()],
            "consequences": [asdict(cons) for cons in self._consequences.values()],
            "edges": [asdict(edge) for edge in self._edges]
        }
        
        if format == 'json':
            return json.dumps(data, indent=2)
        return data

# Usage Example
if __name__ == "__main__":
    # 1. Initialize the Builder
    builder = GraphOfFailureBuilder(graph_name="Bakery_Process_Failures")
    
    # 2. Define a Failure Operation (The 'Wrong' Action)
    op_data_1 = {
        "operation": "Kneading Dough",
        "error_type": "TimeExcess",
        "description": "Mechanical kneading continued for 45 minutes instead of 15."
    }
    op_id_1 = builder.add_failure_operation(op_data_1)
    
    # 3. Define the Consequence (The 'Bad' Result)
    cons_data_1 = {
        "consequence": "Gluten Network Destruction",
        "severity": 9,
        "symptoms": ["Runny dough", "Inability to hold shape", "Sour smell"]
    }
    cons_id_1 = builder.add_consequence(cons_data_1)
    
    # 4. Link them with Mechanism and Constraints
    if op_id_1 and cons_id_1:
        builder.link_failure_to_consequence(
            op_id=op_id_1,
            cons_id=cons_id_1,
            mechanism="Excessive mechanical shear forces break down disulfide bonds in glutenin.",
            constraints=[
                "LIMIT_KNEADING_TIME_MAX_20_MIN", 
                "MONITOR_DOUGH_TEMP_LT_28C"
            ]
        )

    # 5. Generate knowledge for the AGI system
    knowledge_base = builder.generate_reverse_constraint_map()
    
    print("--- Reverse Constraint Map ---")
    print(f"Constraint: LIMIT_KNEADING_TIME_MAX_20_MIN")
    print(f"Prevents: {knowledge_base['LIMIT_KNEADING_TIME_MAX_20_MIN']}")
    
    # 6. Export full graph
    # print(builder.export_graph(format='json'))