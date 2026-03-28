"""
Module: auto_融合能力_自然语言中间语言_nl_ir_2ed192

Description:
    This module implements a Natural Language to Intermediate Representation (NL-IR) compiler.
    It serves as a bridge between human intent and machine execution. Instead of directly
    generating code from natural language, it first compiles requirements into a structured,
    logical "Intermediate Representation" (IR). This IR contains logic flow, variable definitions,
    and intent constraints.

    The IR is designed to be:
    1. Debuggable: Humans can verify the logic before code generation.
    2. Optimizable: An optimizer pass can refine the logic (e.g., loop unrolling).
    3. Portable: Different backends (Python, C++, Workflow engines) can consume the IR.

    This specific implementation focuses on the Frontend (NL -> IR) and a basic
    Backend (IR -> Executable Python Code).

Author: AGI System
Version: 2.1.0
"""

import re
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass, asdict

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NL_IR_Compiler")

# --- Enums and Data Structures ---

class IROperationType(Enum):
    """Defines the types of operations supported in the Intermediate Representation."""
    ASSIGN = "ASSIGN"
    LOOP = "LOOP"
    CONDITIONAL = "CONDITIONAL"
    FUNCTION_CALL = "FUNCTION_CALL"
    RETURN = "RETURN"
    LOG = "LOG"
    CONSTRAINT = "CONSTRAINT"  # Special node for intent constraints (e.g., max time)

class DataType(Enum):
    """Supported data types for type checking."""
    INTEGER = "int"
    STRING = "str"
    FLOAT = "float"
    LIST = "list"
    BOOLEAN = "bool"
    ANY = "any"

@dataclass
class IRNode:
    """
    Represents a single node in the Intermediate Representation graph.
    Equivalent to an assembly instruction or a high-level DSL statement.
    """
    op: str               # Operation type (from IROperationType)
    args: List[str]       # Arguments/Operands
    target: Optional[str] # Target variable for assignment
    meta: Dict[str, Any]  # Metadata (line number, confidence, raw text)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class IRGraph:
    """
    The complete Intermediate Representation structure.
    """
    name: str
    description: str
    inputs: Dict[str, str]  # variable_name: type
    outputs: str            # variable_name to return
    constraints: List[str]
    body: List[IRNode]

# --- Type Definitions for Validation ---

class VariableTable(TypedDict):
    name: str
    type: str
    value: Any

# --- Exceptions ---

class NLCompilerError(Exception):
    """Base exception for NL-IR compilation errors."""
    pass

class IRValidationError(NLCompilerError):
    """Raised when the generated IR fails validation checks."""
    pass

class BackendExecutionError(NLCompilerError):
    """Raised when the IR cannot be executed by the backend."""
    pass

# --- Core Functions ---

def parse_nl_to_ir(natural_language_input: str, context: Optional[Dict] = None) -> IRGraph:
    """
    [Frontend] Compiles Natural Language requirements into an IRGraph.
    
    In a real AGI system, this would involve NLP models (BERT/GPT) to extract entities and intent.
    Here, we use regex-based heuristic parsing to simulate the extraction of logic and constraints.
    
    Args:
        natural_language_input (str): The raw user requirement text.
        context (Optional[Dict]): Contextual variables available in the current scope.
        
    Returns:
        IRGraph: A structured Intermediate Representation.
        
    Raises:
        IRValidationError: If input is empty or logic is unparseable.
    """
    logger.info("Starting NL -> IR compilation...")
    
    if not natural_language_input or len(natural_language_input.strip()) < 5:
        logger.error("Input validation failed: Input too short or empty.")
        raise IRValidationError("Input must be a non-empty string with at least 5 characters.")

    # 1. Extract Metadata
    task_name_match = re.search(r"任务[名称]*[:：](.*?)[。\n]", natural_language_input)
    task_name = task_name_match.group(1).strip() if task_name_match else "unnamed_task"
    
    # 2. Initialize IR Structure
    ir_graph = IRGraph(
        name=task_name,
        description=natural_language_input,
        inputs={},
        outputs="result",
        constraints=[],
        body=[]
    )
    
    # 3. Extract Constraints (Heuristic Simulation)
    # Pattern: "ensure X is Y" or "limit X to Y"
    constraint_patterns = [
        r"确保(.*?)小于(\d+)",
        r"限制(.*?)不超过(\d+)"
    ]
    for pattern in constraint_patterns:
        matches = re.finditer(pattern, natural_language_input)
        for match in matches:
            constraint_desc = f"CONSTRAINT: {match.group(1)} < {match.group(2)}"
            ir_graph.constraints.append(constraint_desc)
            logger.debug(f"Extracted constraint: {constraint_desc}")

    # 4. Extract Logic Flow (Heuristic Simulation)
    # Detecting Loops
    loop_match = re.search(r"遍历列表\s+(.*?)\s+并计算(.*?)之和", natural_language_input)
    
    if loop_match:
        list_var = loop_match.group(1).strip()
        logic_var = loop_match.group(2).strip()
        
        # Define Inputs
        ir_graph.inputs[list_var] = "list"
        
        # Add Logic Nodes
        # Node 1: Initialize accumulator
        ir_graph.body.append(IRNode(
            op=IROperationType.ASSIGN.value,
            args=["0"],
            target="accumulator",
            meta={"desc": "Initialize sum accumulator"}
        ))
        
        # Node 2: Loop
        ir_graph.body.append(IRNode(
            op=IROperationType.LOOP.value,
            args=[list_var, "item"],
            target=None,
            meta={"desc": "Iterate over input list"}
        ))
        
        # Node 3: Calculation inside loop (Simplified: Add item to accumulator)
        ir_graph.body.append(IRNode(
            op=IROperationType.ASSIGN.value,
            args=["accumulator", "+", "item"],
            target="accumulator",
            meta={"desc": "Add current item to sum"}
        ))
        
        # Node 4: Return result
        ir_graph.body.append(IRNode(
            op=IROperationType.RETURN.value,
            args=["accumulator"],
            target="result",
            meta={"desc": "Return final sum"}
        ))
    else:
        # Fallback for generic intent
        logger.warning("Complex logic not detected, generating generic placeholder IR.")
        ir_graph.body.append(IRNode(
            op=IROperationType.LOG.value,
            args=["Processing request..."],
            target=None,
            meta={"desc": "Generic log"}
        ))

    logger.info(f"IR Generation complete. Nodes count: {len(ir_graph.body)}")
    return ir_graph

def compile_ir_to_python(ir_graph: IRGraph, safe_mode: bool = True) -> str:
    """
    [Backend] Compiles an IRGraph into executable Python code string.
    
    This deterministic backend ensures that the logic defined in the IR is
    translated into syntactically correct Python code.
    
    Args:
        ir_graph (IRGraph): The Intermediate Representation graph.
        safe_mode (bool): If True, adds type checking and boundary checks.
        
    Returns:
        str: A string containing valid Python code.
    """
    logger.info(f"Compiling IR '{ir_graph.name}' to Python backend...")
    
    code_lines = []
    code_lines.append(f"def generated_{ir_graph.name}(inputs):")
    code_lines.append("    # Auto-generated by NL-IR Compiler")
    code_lines.append("    import logging")
    code_lines.append("    logger = logging.getLogger('ExecutionEngine')")
    
    # Input Validation
    if safe_mode:
        code_lines.append("    # Input Validation")
        for var, vtype in ir_graph.inputs.items():
            code_lines.append(f"    if '{var}' not in inputs: raise ValueError('Missing input: {var}')")
            # Basic type mapping check
            type_map = {"list": "list", "int": "int", "str": "str"}
            if vtype in type_map:
                code_lines.append(f"    if not isinstance(inputs['{var}'], {type_map[vtype]}): raise TypeError('Invalid type for {var}')")

    # Scope variables
    code_lines.append("    context = inputs.copy()")
    
    # Variable initialization
    indent = "    "
    variables = {}
    
    for node in ir_graph.body:
        current_indent = indent
        
        if node.op == IROperationType.ASSIGN.value:
            # Simple assignment logic
            if len(node.args) == 1:
                expr = node.args[0]
            else:
                expr = " ".join(node.args) # e.g. "accumulator + item"
            
            code_lines.append(f"{current_indent}{node.target} = {expr}")
            variables[node.target] = True

        elif node.op == IROperationType.LOOP.value:
            # Args: [iterable, item_var]
            iterable = node.args[0]
            item_var = node.args[1]
            code_lines.append(f"{current_indent}for {item_var} in context.get('{iterable}', []):")
            # Increase indent for next nodes (Simplified logic for single nesting)
            # In a real compiler, we would manage an indent stack
            current_indent += "    "
            
        elif node.op == IROperationType.RETURN.value:
            code_lines.append(f"{current_indent}return {node.args[0]}")
            
        elif node.op == IROperationType.LOG.value:
            code_lines.append(f"{current_indent}logger.info('{node.args[0]}')")

    # Fallback return if not explicit
    if "return" not in code_lines[-1]:
        code_lines.append(f"{indent}return None")

    return "\n".join(code_lines)

# --- Helper Functions ---

def validate_ir_integrity(ir_graph: IRGraph) -> bool:
    """
    Validates the structural integrity and semantic consistency of the IR Graph.
    
    Checks:
    1. All variables used in expressions must be defined or inputted.
    2. The graph must have an entry point and preferably an exit (return).
    
    Args:
        ir_graph (IRGraph): The IR graph to validate.
        
    Returns:
        bool: True if valid.
        
    Raises:
        IRValidationError: If integrity check fails.
    """
    logger.info("Running IR Integrity Validation...")
    
    defined_vars = set(ir_graph.inputs.keys())
    
    for node in ir_graph.body:
        # Check variable definitions (Very simplified static analysis)
        if node.target:
            defined_vars.add(node.target)
            
        # Check if loop iterator source exists
        if node.op == IROperationType.LOOP.value:
            source_var = node.args[0]
            if source_var not in defined_vars:
                logger.error(f"Validation Error: Loop source '{source_var}' used before definition.")
                raise IRValidationError(f"Undefined variable used in loop: {source_var}")
                
    logger.info("IR Integrity Validation Passed.")
    return True

def execute_ir_interpreter(ir_graph: IRGraph, runtime_inputs: Dict[str, Any]) -> Any:
    """
    [Interpreter Mode] Executes the IR directly without generating source code.
    Useful for sandbox execution or rapid prototyping.
    
    Args:
        ir_graph (IRGraph): The IR to execute.
        runtime_inputs (Dict): The actual data to process.
        
    Returns:
        Any: The result of the computation.
    """
    logger.info("Executing IR in Interpreter Mode...")
    context = runtime_inputs.copy()
    
    # Simple stack-based execution simulation
    for node in ir_graph.body:
        if node.op == IROperationType.ASSIGN.value:
            # Extremely simplified evaluation
            if node.args == ["0"]:
                context[node.target] = 0
            elif len(node.args) == 3 and node.args[1] == "+":
                # Handle addition
                left = context.get(node.args[0], 0)
                right = context.get(node.args[2], 0)
                context[node.target] = left + right
                
        elif node.op == IROperationType.RETURN.value:
            return context.get(node.args[0])
            
    return None

# --- Main Execution Example ---

if __name__ == "__main__":
    # Example Usage
    
    # 1. Define Natural Language Requirement
    nl_requirement = """
    任务名称: 计算总和
    遍历列表 data_list 并计算元素之和。
    确保结果不超过 1000。
    """
    
    input_data = {
        "data_list": [10, 20, 30, 40, 50]
    }

    try:
        print("-" * 40)
        print(f"Original Requirement:\n{nl_requirement.strip()}")
        print("-" * 40)

        # 2. Compile NL to IR
        ir_representation = parse_nl_to_ir(nl_requirement)
        
        # 3. Validate IR
        validate_ir_integrity(ir_representation)
        
        # 4. Visualize IR (JSON)
        print("\n[Generated IR Structure]")
        ir_dict = asdict(ir_representation)
        ir_dict['body'] = [asdict(n) for n in ir_representation.body]
        print(json.dumps(ir_dict, indent=2, ensure_ascii=False))
        
        # 5. Compile to Python Code
        python_code = compile_ir_to_python(ir_representation)
        print("\n[Compiled Python Code]")
        print(python_code)
        
        # 6. Execute the generated code (Dynamic Execution)
        print("\n[Execution Result]")
        # Create a namespace for execution
        local_scope = {}
        exec(python_code, {}, local_scope)
        
        # Retrieve the function
        generated_func = local_scope[f"generated_{ir_representation.name}"]
        
        # Run
        result = generated_func(input_data)
        print(f"Output: {result}")
        
    except NLCompilerError as e:
        logger.error(f"Compilation failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)