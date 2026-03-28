"""
Module: intermediate_representation_design.py

This module defines a robust framework for an Intermediate Representation (IR)
designed to bridge the gap between ambiguous natural language intents and
deterministic Abstract Syntax Trees (AST).

The IR design philosophy is hybrid:
1. It uses a structured, S-expression (Lisp-like) syntax for representing
   logic and control flow, ensuring unambiguous parsing.
2. It incorporates a probabilistic distribution layer to handle the
   uncertainty inherent in natural language inputs.
3. It is compiled deterministically into executable Python code.

Author: AGI System
Version: 1.0.0
"""

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class ProbabilisticSymbol:
    """
    Represents a symbol in the IR that carries a probability distribution.
    
    Attributes:
        values: A dictionary mapping possible values to their confidence scores.
        resolved_value: The final resolved value after sampling or selection.
    """
    values: Dict[Union[str, int, float], float]
    resolved_value: Optional[Union[str, int, float]] = None

    def resolve(self, strategy: str = "max") -> Union[str, int, float]:
        """
        Resolves the symbol to a single value based on the chosen strategy.
        
        Args:
            strategy: Resolution strategy ('max' for highest probability).
        
        Returns:
            The resolved value.
        
        Raises:
            ValueError: If no values are present or strategy is unknown.
        """
        if not self.values:
            raise ValueError("Cannot resolve an empty ProbabilisticSymbol.")
        
        if strategy == "max":
            self.resolved_value = max(self.values, key=self.values.get)
            logger.debug(f"Resolved symbol to '{self.resolved_value}' using max strategy.")
            return self.resolved_value
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")

@dataclass
class IRNode:
    """
    A node in the Intermediate Representation tree.
    
    This acts similarly to an S-Expression: (Operator * Operands).
    It supports both deterministic symbols and probabilistic symbols.
    """
    operator: str
    operands: List[Union['IRNode', ProbabilisticSymbol, str, int, float]] = field(default_factory=list)

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """Validates the structure of the IR Node."""
        if not isinstance(self.operator, str) or not self.operator:
            raise ValueError("Operator must be a non-empty string.")
        if not isinstance(self.operands, list):
            raise ValueError("Operands must be a list.")

# --- Core Functions ---

def create_ir_from_intent(intent: Dict) -> IRNode:
    """
    Constructs the IR tree from a structured intent dictionary.
    This function handles the mapping of high-level concepts to logical IR nodes.
    
    Args:
        intent: A dictionary containing 'action', 'target', and 'params' with confidence scores.
    
    Returns:
        The root IRNode of the constructed Intermediate Representation.
    
    Example Input:
        {
            "action": {"value": "compute", "confidence": 0.9},
            "target": {"value": "matrix_mult", "confidence": 0.8},
            "params": [
                {"value": "A", "confidence": 0.99},
                {"value": "B", "confidence": 0.95}
            ]
        }
    """
    logger.info("Constructing IR from intent...")
    
    # Extract and validate action
    action_data = intent.get("action")
    if not action_data:
        raise ValueError("Intent must contain an 'action' field.")
    
    # Create probabilistic symbol for the operation type
    # Here we map natural language 'action' to IR 'operator'
    # For simplicity, we assume direct mapping, but in AGI this would be a learned mapping.
    op_symbol = ProbabilisticSymbol(
        values={action_data["value"]: action_data["confidence"]}
    )
    
    # Construct operands
    operands = []
    params = intent.get("params", [])
    targets = intent.get("target", [])
    
    # Add targets
    if isinstance(targets, dict):
        targets = [targets]
        
    for t in targets:
        operands.append(ProbabilisticSymbol(values={t["value"]: t["confidence"]}))
        
    # Add params
    for p in params:
        operands.append(ProbabilisticSymbol(values={p["value"]: p["confidence"]}))

    # Create the root node
    # Structure: (CALL <target> <param1> <param2> ...)
    root_node = IRNode(operator="CALL", operands=operands)
    
    logger.info(f"IR constructed successfully with operator: {root_node.operator}")
    return root_node

def compile_ir_to_python(ir_node: IRNode, context: Optional[Dict] = None) -> str:
    """
    Deterministically compiles the IR tree into executable Python code.
    
    This function traverses the IR tree, resolves any probabilistic symbols,
    and generates syntactically correct Python source code.
    
    Args:
        ir_node: The root node of the IR tree.
        context: A dictionary for variable context (unused in this simple example but needed for scope).
    
    Returns:
        A string containing the generated Python code.
    """
    logger.info("Compiling IR to Python...")
    
    def _traverse(node: Union[IRNode, ProbabilisticSymbol, any]) -> str:
        if isinstance(node, ProbabilisticSymbol):
            # Resolve probability to concrete value
            val = node.resolve(strategy="max")
            # Add casting or validation if necessary
            return repr(val) if isinstance(val, str) else str(val)
        
        elif isinstance(node, IRNode):
            if node.operator == "CALL":
                if len(node.operands) < 1:
                    raise ValueError("CALL operation requires at least one operand (function name).")
                
                # Resolve function name
                func_name_node = node.operands[0]
                if isinstance(func_name_node, ProbabilisticSymbol):
                    func_name = func_name_node.resolve(strategy="max")
                else:
                    func_name = str(func_name_node)

                # Process arguments
                args_nodes = node.operands[1:]
                args_str = ", ".join([_traverse(arg) for arg in args_nodes])
                
                # Map IR function names to Python functions (Stub for demonstration)
                # In a real system, this would import specific libraries (e.g., numpy)
                python_func_name = _map_ir_func_to_python(func_name)
                
                return f"{python_func_name}({args_str})"
            else:
                # Handle generic operators (e.g., ADD, SUB)
                args_str = ", ".join([_traverse(arg) for arg in node.operands])
                return f"{node.operator}({args_str})"
        
        elif isinstance(node, (str, int, float)):
            return repr(node) if isinstance(node, str) else str(node)
        
        else:
            raise TypeError(f"Unsupported node type in traversal: {type(node)}")

    code = _traverse(ir_node)
    logger.info("Compilation complete.")
    return code

# --- Helper Functions ---

def _map_ir_func_to_python(ir_func: str) -> str:
    """
    Maps an IR function identifier to a concrete Python function name.
    Includes validation and security checks (e.g., preventing arbitrary execution).
    """
    # Whitelist approach for security
    allowed_funcs = {
        "matrix_mult": "numpy.matmul",
        "add": "operator.add",
        "print": "print",
        "compute": "process_data" # Hypothetical function
    }
    
    sanitized_func = allowed_funcs.get(ir_func)
    if sanitized_func:
        return sanitized_func
    else:
        logger.warning(f"Attempted to map unauthorized or unknown function: {ir_func}")
        raise ValueError(f"Function '{ir_func}' is not allowed or recognized.")

# --- Usage Example ---

if __name__ == "__main__":
    # Example: Simulating an AGI output where the user asked:
    # "Calculate the matrix multiplication of A and B" with some ambiguity
    
    ambiguous_intent = {
        "action": {"value": "compute", "confidence": 0.98},
        "target": {
            # The system is 90% sure it's matrix_mult, but maybe 10% dot product
            "value": "matrix_mult", 
            "confidence": 0.90
        },
        "params": [
            {"value": "matrix_A", "confidence": 0.99},
            {"value": "matrix_B", "confidence": 0.95}
        ]
    }

    try:
        # 1. Create IR
        ir_tree = create_ir_from_intent(ambiguous_intent)
        
        # 2. Compile to Python
        # This will resolve probabilities (matrix_mult selected) and map to numpy
        python_code = compile_ir_to_python(ir_tree)
        
        print("-" * 40)
        print("Generated Python Code:")
        print(python_code)
        print("-" * 40)
        
    except ValueError as e:
        logger.error(f"Processing failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)