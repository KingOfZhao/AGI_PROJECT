"""
Module: auto_state_machine_validator_e47ab2
Description: Advanced static analysis and formal verification module for AGI systems.
             This module validates structured logic (like state machines or workflow DAGs)
             without code execution to ensure 'Cognitive Self-Consistency'.
             It detects deadlocks, unreachable states, and infinite loops (cycles).
Author: Senior Python Engineer (AGI Division)
Version: 1.0.0
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass

class StateMachineValidator:
    """
    Performs static analysis on a state machine definition to verify logic closure.
    
    Input Format:
        states: List[str] - List of state names.
        initial_state: str - The entry point state.
        transitions: Dict[str, List[str]] - Mapping of source state to list of destination states.
        
    Output Format:
        Dict containing 'is_valid', 'unreachable_states', 'potential_loops', 'deadlocks'.
    """
    
    def __init__(self, states: List[str], initial_state: str, transitions: Dict[str, List[str]]):
        """
        Initialize the validator with state machine data.
        
        Args:
            states: List of all defined states.
            initial_state: The starting state of the machine.
            transitions: A dictionary representing the graph edges.
        """
        self.states = set(states)
        self.initial_state = initial_state
        self.transitions = transitions
        self.graph: Dict[str, Set[str]] = {}
        self._build_graph()
        
    def _build_graph(self) -> None:
        """
        Helper function to build an adjacency set representation of the graph.
        Validates data types during construction.
        """
        logger.info("Building graph representation...")
        if not isinstance(self.states, set) or not self.states:
            raise ValidationError("States must be a non-empty list.")
        
        if self.initial_state not in self.states:
            raise ValidationError(f"Initial state '{self.initial_state}' not in defined states.")
            
        for state, neighbors in self.transitions.items():
            if state not in self.states:
                logger.warning(f"Transition defined for undefined state '{state}'. Ignoring.")
                continue
                
            self.graph[state] = set()
            for neighbor in neighbors:
                if neighbor in self.states:
                    self.graph[state].add(neighbor)
                else:
                    logger.warning(f"Transition to undefined state '{neighbor}' from '{state}'. Ignoring.")
    
    def _get_all_nodes(self) -> Set[str]:
        """Returns the set of all valid nodes."""
        return self.states

    def detect_unreachable_states(self) -> Tuple[bool, Set[str]]:
        """
        Core Function 1: Detects states that cannot be reached from the initial state.
        Uses Breadth-First Search (BFS) for traversal.
        
        Returns:
            Tuple[bool, Set[str]]: (True if unreachable states exist, set of those states)
        """
        logger.info("Running Reachability Analysis (BFS)...")
        visited: Set[str] = set()
        queue: deque[str] = deque([self.initial_state])
        
        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                # Add neighbors that are defined in the graph
                neighbors = self.graph.get(current, set())
                for neighbor in neighbors:
                    if neighbor not in visited:
                        queue.append(neighbor)
        
        unreachable = self._get_all_nodes() - visited
        
        if unreachable:
            logger.warning(f"Found {len(unreachable)} unreachable states.")
            return True, unreachable
            
        logger.info("All states are reachable.")
        return False, set()

    def detect_logic_anomalies(self) -> Dict[str, Any]:
        """
        Core Function 2: Detects deadlocks (sink nodes) and potential infinite loops (cycles).
        Uses iterative Deepening / DFS for cycle detection and out-degree analysis for deadlocks.
        
        Returns:
            Dict containing details about loops and deadlocks.
        """
        logger.info("Running Logic Anomaly Detection...")
        results = {
            "deadlocks": [],  # States with no exit (sink nodes)
            "potential_loops": [] # Cycles detected
        }
        
        # 1. Deadlock Detection (Simple Out-degree check)
        for state in self.states:
            neighbors = self.graph.get(state, set())
            if not neighbors:
                # If it's not a designated terminal state, it's a logic error
                results["deadlocks"].append(state)
                logger.warning(f"Deadlock detected: State '{state}' has no outgoing transitions.")
                
        # 2. Loop Detection (Depth First Search)
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        
        def dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in recursion_stack:
                    # Cycle found
                    loop_path = path + [neighbor]
                    results["potential_loops"].append(loop_path)
                    logger.warning(f"Infinite Loop detected: {' -> '.join(loop_path)}")
                    return True # Found a cycle
            
            recursion_stack.remove(node)
            return False

        for node in self.states:
            if node not in visited:
                dfs(node, [node])
                
        return results

def validate_cognitive_closure(machine_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    High-level wrapper to validate a structured logic block.
    
    Args:
        machine_def: Dictionary containing 'states', 'initial_state', 'transitions'.
        
    Returns:
        Comprehensive validation report.
        
    Example Usage:
    >>> definition = {
    ...     "states": ["A", "B", "C"],
    ...     "initial_state": "A",
    ...     "transitions": {
    ...         "A": ["B"],
    ...         "B": ["C", "A"], # Loop A->B->A possible
    ...         "C": []          # Deadlock
    ...     }
    ... }
    >>> report = validate_cognitive_closure(definition)
    >>> print(report["is_valid"])
    False
    """
    logger.info("Starting Cognitive Closure Validation...")
    
    try:
        # Data Validation
        if not isinstance(machine_def, dict):
            raise ValidationError("Input must be a dictionary.")
        if "states" not in machine_def or "transitions" not in machine_def:
            raise ValidationError("Missing 'states' or 'transitions' keys.")
            
        validator = StateMachineValidator(
            states=machine_def["states"],
            initial_state=machine_def.get("initial_state", machine_def["states"][0]),
            transitions=machine_def["transitions"]
        )
        
        # Run Analysis
        has_unreachable, unreachable_set = validator.detect_unreachable_states()
        anomalies = validator.detect_logic_anomalies()
        
        is_valid = not has_unreachable and not anomalies["deadlocks"] and not anomalies["potential_loops"]
        
        report = {
            "is_valid": is_valid,
            "unreachable_states": list(unreachable_set),
            "logic_anomalies": anomalies,
            "message": "Validation complete. Logic is consistent." if is_valid else "Inconsistencies detected."
        }
        
    except ValidationError as ve:
        logger.error(f"Validation Error: {ve}")
        return {"is_valid": False, "error": str(ve)}
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)
        return {"is_valid": False, "error": "Internal System Error"}
        
    return report

if __name__ == "__main__":
    # Example Usage for demonstration
    sample_agi_logic = {
        "states": ["Init", "Process", "Verify", "Success", "Fail"],
        "initial_state": "Init",
        "transitions": {
            "Init": ["Process"],
            "Process": ["Verify", "Fail"],
            "Verify": ["Success", "Process"], # Potential Loop: Process <-> Verify
            "Success": [], # Intentional End
            "Fail": []     # Intentional End
        }
    }
    
    # Introduce an error for demonstration: Isolated state 'Ghost'
    sample_agi_logic["states"].append("Ghost")
    
    # Introduce an error for demonstration: Deadlock without exit
    sample_agi_logic["states"].append("Stuck")
    sample_agi_logic["transitions"]["Stuck"] = []
    
    print("--- Running Static Analysis ---")
    result = validate_cognitive_closure(sample_agi_logic)
    
    import json
    print(json.dumps(result, indent=2))