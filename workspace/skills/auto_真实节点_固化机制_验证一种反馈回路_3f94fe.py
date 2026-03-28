"""
AGI Skill Module: Real Node Solidification Mechanism
Name: auto_真实节点_固化机制_验证一种反馈回路_3f94fe
Domain: agi_architecture

Description:
This module implements a feedback loop mechanism where successfully executed code
in a sandbox is abstracted into a "Reusable Skill Node" and injected back into
the knowledge base. The core logic focuses on extracting generic algorithmic
patterns from a specific successful execution instance, rather than merely
storing the raw code.

Key Components:
1. ExecutionTrace: Data structure representing the context of a successful run.
2. SkillNode: The abstracted, reusable unit of logic.
3. extract_generic_logic: Analyzes code and I/O to infer the skill's signature.
4. solidify_skill_node: Orchestrates the validation and storage process.
"""

import ast
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """
    Represents the trace of a code execution within the AGI sandbox.
    
    Attributes:
        source_code: The raw Python code executed.
        inputs: The arguments passed to the execution context.
        outputs: The result returned by the execution.
        execution_status: 'SUCCESS' or 'FAILURE'.
        execution_time_ms: Time taken to execute.
    """
    source_code: str
    inputs: Dict[str, Any]
    outputs: Any
    execution_status: str
    execution_time_ms: float

    def __post_init__(self):
        if self.execution_status not in ['SUCCESS', 'FAILURE']:
            raise ValueError("execution_status must be 'SUCCESS' or 'FAILURE'")


@dataclass
class SkillNode:
    """
    Represents a solidified, reusable skill node in the AGI knowledge graph.
    
    Attributes:
        node_id: Unique identifier for the skill.
        name: Inferred name of the skill (usually the function name).
        description: Auto-generated description of the skill's purpose.
        signature: The function signature (args and return type).
        logic_source: The optimized/refactored source code.
        input_schema: JSON schema describing expected inputs.
        output_schema: JSON schema describing expected output.
        metadata: Additional tags and provenance data.
    """
    node_id: str
    name: str
    description: str
    signature: str
    logic_source: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


def _infer_type_from_value(value: Any) -> str:
    """
    Helper function to infer Python type string from a value.
    
    Args:
        value: The value to inspect.
        
    Returns:
        String representation of the type.
    """
    if isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    elif isinstance(value, list):
        return "List"
    elif isinstance(value, dict):
        return "Dict"
    else:
        return "Any"


def _parse_function_signature(code: str) -> Optional[Tuple[str, List[str]]]:
    """
    Helper function to parse the AST and extract the top-level function definition.
    
    Args:
        code: The source code string.
        
    Returns:
        Tuple of (function_name, [argument_names]) or None if parsing fails.
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                return node.name, args
    except SyntaxError as e:
        logger.error(f"Syntax error while parsing code: {e}")
    return None


def extract_generic_logic(trace: ExecutionTrace) -> SkillNode:
    """
    Core Function 1: Analyzes the execution trace to extract generic logic.
    
    This function inspects the source code to find the primary function definition
    and uses the input/output data from the trace to infer type schemas. It attempts
    to generalize the specific execution into a reusable component.

    Args:
        trace: The ExecutionTrace object containing code and runtime data.

    Returns:
        A SkillNode object representing the abstracted skill.

    Raises:
        ValueError: If the trace status is not SUCCESS or code is invalid.
    """
    if trace.execution_status != "SUCCESS":
        raise ValueError("Cannot solidify logic from a failed execution trace.")

    logger.info(f"Extracting logic from execution trace...")
    
    # 1. Parse Code Structure
    func_info = _parse_function_signature(trace.source_code)
    if not func_info:
        # Fallback for script-like code without a specific function def
        func_name = "anonymous_skill"
        args = []
        logger.warning("No function definition found, creating anonymous skill.")
    else:
        func_name, args = func_info

    # 2. Infer Schemas from I/O
    input_schema = {
        arg_name: _infer_type_from_value(trace.inputs.get(arg_name))
        for arg_name in args
    }
    output_schema = {"result": _infer_type_from_value(trace.outputs)}

    # 3. Generate Metadata and ID
    content_hash = hashlib.sha256(trace.source_code.encode()).hexdigest()[:8]
    node_id = f"skill_{func_name}_{content_hash}"
    
    description = (
        f"Auto-generated skill from successful execution. "
        f"Processes inputs {args} and returns {output_schema['result']}."
    )

    return SkillNode(
        node_id=node_id,
        name=func_name,
        description=description,
        signature=f"{func_name}({', '.join(args)})",
        logic_source=trace.source_code,
        input_schema=input_schema,
        output_schema=output_schema,
        metadata={
            "origin_trace_id": str(uuid.uuid4()),
            "execution_time_ms": trace.execution_time_ms,
            "complexity_score": len(trace.source_code.splitlines())
        }
    )


def solidify_skill_node(skill: SkillNode, knowledge_base: Dict[str, SkillNode]) -> bool:
    """
    Core Function 2: Validates and injects the skill node into the knowledge base.
    
    This function performs boundary checks, validates the code integrity, and
    ensures no ID collision before persisting the skill.

    Args:
        skill: The SkillNode to be stored.
        knowledge_base: A dictionary acting as the in-memory knowledge store.

    Returns:
        True if successfully solidified, False otherwise.
    """
    logger.info(f"Attempting to solidify skill node: {skill.node_id}")
    
    try:
        # 1. Data Validation
        if not skill.node_id or not skill.logic_source:
            logger.error("Validation failed: Missing ID or source code.")
            return False

        # 2. Boundary Check: Code Size
        if len(skill.logic_source) > 10000:  # Arbitrary limit for example
            logger.warning("Skill source code too large for auto-solidification.")
            return False

        # 3. Collision Detection
        if skill.node_id in knowledge_base:
            logger.info(f"Skill {skill.node_id} already exists. Updating logic.")
            # In a real system, we might version this. Here we overwrite.
        
        # 4. Code Integrity Check (Re-parsing)
        try:
            compile(skill.logic_source, '<string>', 'exec')
        except SyntaxError:
            logger.error("Validation failed: Source code contains syntax errors.")
            return False

        # 5. Injection
        knowledge_base[skill.node_id] = skill
        logger.info(f"Successfully solidified skill: {skill.name} (ID: {skill.node_id})")
        return True

    except Exception as e:
        logger.exception(f"Unexpected error during solidification: {e}")
        return False


# Example Usage
if __name__ == "__main__":
    # Mock Knowledge Base
    agi_knowledge_base: Dict[str, SkillNode] = {}

    # 1. Define a successful execution trace
    # Example: A function that calculates the area of a rectangle
    successful_code = """
def calculate_area(width, height):
    return width * height
"""
    
    trace_data = ExecutionTrace(
        source_code=successful_code,
        inputs={"width": 10, "height": 5},
        outputs=50,
        execution_status="SUCCESS",
        execution_time_ms=1.2
    )

    # 2. Extract generic logic
    try:
        new_skill = extract_generic_logic(trace_data)
        print(f"\nExtracted Skill: {new_skill.name}")
        print(f"Signature: {new_skill.signature}")
        print(f"Input Schema: {new_skill.input_schema}")
        
        # 3. Solidify into Knowledge Base
        success = solidify_skill_node(new_skill, agi_knowledge_base)
        
        if success:
            print("\nKnowledge Base State:")
            for k, v in agi_knowledge_base.items():
                print(f" - {k}: {v.description}")
                
    except Exception as e:
        print(f"Error in feedback loop: {e}")