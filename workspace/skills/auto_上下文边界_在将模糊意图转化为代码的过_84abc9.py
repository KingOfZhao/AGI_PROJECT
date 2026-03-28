"""
Module: auto_context_boundary_pruner
Description: Implements "Variable Scope Context Pruning" for AGI systems.
             This module is designed to filter long code sequences generated
             in multi-turn dialogues, identifying and retaining only the "Real Nodes"
             (execution-relevant variables and logic) required for the current step,
             while removing redundant noise to optimize LLM attention mechanisms.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CodeNode:
    """
    Represents a node in the abstract code sequence.
    
    Attributes:
        id: Unique identifier for the node.
        code_snippet: The actual code string.
        dependencies: List of variable names this node reads/uses.
        definitions: List of variable names this node defines/writes.
        is_active: Whether this node is part of the current logical execution path.
    """
    id: str
    code_snippet: str
    dependencies: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    is_active: bool = False

    def __repr__(self) -> str:
        return f"Node({self.id}, defs={self.definitions}, deps={self.dependencies})"


class ContextBoundaryPruner:
    """
    Analyzes a sequence of code nodes to perform Context Scope Pruning.
    
    This class implements a reverse dependency graph traversal to determine
    which variables and code blocks are strictly necessary to fulfill a 
    specific target intent (represented by required output variables).
    """

    def __init__(self, node_sequence: List[CodeNode]):
        """
        Initialize the pruner with a sequence of code nodes.
        
        Args:
            node_sequence: A list of CodeNode objects representing the conversation history.
        """
        if not isinstance(node_sequence, list):
            raise ValueError("Input must be a list of CodeNode objects.")
        
        self.node_sequence = node_sequence
        self.scope_state: Dict[str, str] = {}  # Maps variable name to defining Node ID
        logger.info(f"Initialized ContextBoundaryPruner with {len(node_sequence)} nodes.")

    def _build_scope_map(self) -> None:
        """
        Helper function to map variables to their defining nodes.
        Simulates the top-down execution scope.
        """
        self.scope_state.clear()
        for node in self.node_sequence:
            for var in node.definitions:
                self.scope_state[var] = node.id
        logger.debug(f"Scope map built: {len(self.scope_state)} variables tracked.")

    def _get_transitive_dependencies(self, target_vars: Set[str]) -> Set[str]:
        """
        Recursively finds all variables required to produce the target_vars.
        
        Args:
            target_vars: The set of variables needed for the current intent.
            
        Returns:
            A set of all variable names required (transitive closure).
        """
        required_vars: Set[str] = set(target_vars)
        queue = list(target_vars)
        
        while queue:
            current_var = queue.pop(0)
            # Find the node that defines this variable
            defining_node_id = self.scope_state.get(current_var)
            
            if defining_node_id:
                # Find the node object
                node = next((n for n in self.node_sequence if n.id == defining_node_id), None)
                if node:
                    for dep in node.dependencies:
                        if dep not in required_vars:
                            required_vars.add(dep)
                            queue.append(dep)
                            
        return required_vars

    def identify_real_nodes(self, target_variables: List[str]) -> List[CodeNode]:
        """
        Core Function 1: Identifies and returns the "Real Nodes" required for execution.
        
        This method determines the minimal set of code nodes needed to provide
        the context for the specified target variables, effectively pruning
        the irrelevant conversation history.
        
        Args:
            target_variables: List of variable names relevant to the current user intent.
            
        Returns:
            A list of CodeNode objects representing the pruned, relevant context.
            
        Raises:
            ValueError: If target_variables is empty.
        """
        if not target_variables:
            raise ValueError("Target variables list cannot be empty for pruning.")

        logger.info(f"Starting context pruning for targets: {target_variables}")
        
        # 1. Build the variable scope map
        self._build_scope_map()
        
        # 2. Calculate transitive dependencies
        required_vars = self._get_transitive_dependencies(set(target_variables))
        logger.info(f"Transitive dependency resolution complete. Required vars: {required_vars}")
        
        # 3. Identify Node IDs involved in these definitions
        relevant_node_ids: Set[str] = set()
        for var in required_vars:
            if var in self.scope_state:
                relevant_node_ids.add(self.scope_state[var])
        
        # 4. Filter the sequence
        real_nodes = [
            node for node in self.node_sequence 
            if node.id in relevant_node_ids
        ]
        
        logger.info(f"Pruning complete. Retained {len(real_nodes)}/{len(self.node_sequence)} nodes.")
        return real_nodes

    def get_pruned_context_state(self, target_variables: List[str]) -> Dict[str, Any]:
        """
        Core Function 2: Extracts the clean variable state for the context window.
        
        Instead of returning code blocks, this function returns the actual data
        state (simulation) required for the LLM to proceed, eliminating code history.
        
        Args:
            target_variables: List of variable names needed.
            
        Returns:
            A dictionary containing the 'state' (variable names) and 'metadata'
            about the pruning process.
        """
        try:
            real_nodes = self.identify_real_nodes(target_variables)
            
            # In a real AGI system, this would extract actual values.
            # Here we return the structural representation.
            active_state = {
                "required_variables": list(self._get_transitive_dependencies(set(target_variables))),
                "source_nodes": [node.id for node in real_nodes],
                "pruning_ratio": len(real_nodes) / len(self.node_sequence) if self.node_sequence else 0
            }
            
            return {
                "status": "success",
                "context_payload": active_state,
                "message": "Context boundary successfully pruned."
            }
            
        except Exception as e:
            logger.error(f"Error during context state extraction: {str(e)}")
            return {
                "status": "error",
                "context_payload": {},
                "message": str(e)
            }

# --- Usage Example ---

def run_demo():
    """
    Demonstrates the usage of the ContextBoundaryPruner.
    """
    # 1. Simulate a long conversation history generating code nodes
    history_nodes = [
        CodeNode(
            id="node_1", 
            code_snippet="config = load_config()", 
            definitions=["config"], 
            dependencies=[]
        ),
        CodeNode(
            id="node_2", 
            code_snippet="raw_data = fetch_data(config)", 
            definitions=["raw_data"], 
            dependencies=["config"]
        ),
        CodeNode(
            id="node_3", 
            code_snippet="noise_var = debug_log('checking stuff')", 
            definitions=["noise_var"], 
            dependencies=[]
        ),
        CodeNode(
            id="node_4", 
            code_snippet="processed_df = clean(raw_data)", 
            definitions=["processed_df"], 
            dependencies=["raw_data"]
        ),
        CodeNode(
            id="node_5", 
            code_snippet="model = train(processed_df)", 
            definitions=["model"], 
            dependencies=["processed_df"]
        ),
        CodeNode( # Imagine the user asks about the model training result, ignoring the debug noise
            id="node_6", 
            code_snippet="result = evaluate(model)", 
            definitions=["result"], 
            dependencies=["model"]
        )
    ]

    try:
        pruner = ContextBoundaryPruner(history_nodes)
        
        # Scenario: User asks "Why did the result variable fail?"
        # We only need variables leading to 'result'.
        # 'noise_var' (node_3) should be pruned out.
        
        print("--- Starting Pruning Demo ---")
        targets = ["result"]
        real_nodes = pruner.identify_real_nodes(targets)
        
        print(f"\nTarget Intent requires: {targets}")
        print(f"Identified Real Nodes ({len(real_nodes)}):")
        for node in real_nodes:
            print(f" - {node.id}: {node.code_snippet}")
            
        print("\nFull State Extraction:")
        state = pruner.get_pruned_context_state(targets)
        print(state)
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")

if __name__ == "__main__":
    run_demo()