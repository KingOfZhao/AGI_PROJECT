"""
Auto-Executable Knowledge Node Wrapper Protocol (SKILL Generator)

This module provides a framework to transform static, theoretical knowledge nodes
(e.g., natural language text, structured data) into executable Python SKILLs
(Callable APIs/Scripts). It leverages a standardized interface to parse inputs,
generate code stubs, and validate the output.

Version: 1.0.0
Author: AGI System Core
License: MIT
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import uuid

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class KnowledgeNode:
    """
    Represents the input 'Real Node' containing theoretical knowledge.
    
    Attributes:
        node_id: Unique identifier for the knowledge node.
        content: The raw content (e.g., text description of "Tomato Scrambled Eggs").
        metadata: Additional metadata (tags, source, timestamp).
        input_schema: Expected input parameters definition (optional).
        output_schema: Expected output definition (optional).
    """
    node_id: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)
    input_schema: Optional[Dict[str, str]] = None
    output_schema: Optional[Dict[str, str]] = None

@dataclass
class ExecutableSkill:
    """
    Represents the generated executable SKILL object.
    
    Attributes:
        skill_id: Unique ID for the generated skill.
        source_node_id: ID of the parent KnowledgeNode.
        func_name: The name of the generated function.
        code_body: The actual Python source code string.
        executor: The compiled callable function (if compilation successful).
        parameters: List of parameter names extracted/inferred.
        status: 'DRAFT', 'COMPILED', or 'FAILED'.
    """
    skill_id: str
    source_node_id: str
    func_name: str
    code_body: str
    executor: Optional[Callable] = None
    parameters: List[str] = field(default_factory=list)
    status: str = "DRAFT"

# --- Custom Exceptions ---

class SkillGenerationError(Exception):
    """Base exception for errors during skill generation."""
    pass

class CodeCompilationError(SkillGenerationError):
    """Raised when the generated code fails to compile."""
    pass

class SchemaValidationError(SkillGenerationError):
    """Raised when input data does not match the skill schema."""
    pass

# --- Core Logic ---

class SkillWrapperProtocol:
    """
    Handles the transformation of KnowledgeNodes into ExecutableSkills.
    """
    
    def __init__(self, default_timeout: int = 30):
        """
        Initialize the protocol wrapper.
        
        Args:
            default_timeout: Execution timeout for generated skills.
        """
        self.default_timeout = default_timeout
        self._registry: Dict[str, ExecutableSkill] = {}
        logger.info("SkillWrapperProtocol initialized.")

    def _sanitize_identifier(self, name: str) -> str:
        """
        Helper function to convert a string into a valid Python function identifier.
        
        Args:
            name: The raw name string (e.g., "Tomato Scrambled Eggs").
            
        Returns:
            A valid snake_case identifier string (e.g., "tomato_scrambled_eggs").
        """
        # Remove special characters, replace spaces with underscores
        clean_name = re.sub(r'[^a-zA-Z0-9_\s]', '', name).strip().lower()
        clean_name = re.sub(r'\s+', '_', clean_name)
        
        if not clean_name:
            return f"skill_{uuid.uuid4().hex[:8]}"
        
        # Ensure it doesn't start with a number
        if clean_name[0].isdigit():
            clean_name = f"func_{clean_name}"
            
        return clean_name

    def _extract_parameters_from_text(self, text: str) -> List[str]:
        """
        Advanced helper to extract potential parameters from unstructured text.
        (Simulated logic for AGI context understanding).
        
        Args:
            text: The knowledge content.
            
        Returns:
            A list of parameter names.
        """
        # In a real AGI system, this would use NLP/NER.
        # Here we use simple regex simulation.
        keywords = ["eggs", "tomatoes", "oil", "salt", "water", "time", "temperature"]
        found = []
        for kw in keywords:
            if kw in text.lower():
                found.append(kw)
        return sorted(list(set(found)))

    def generate_skill_code(self, node: KnowledgeNode) -> ExecutableSkill:
        """
        Core Function 1: Generates and wraps a knowledge node into an executable structure.
        
        This process involves:
        1. Analyzing the node content.
        2. Defining a function signature.
        3. Constructing the Python code string.
        
        Args:
            node: The KnowledgeNode to process.
            
        Returns:
            An ExecutableSkill object containing the source code.
            
        Raises:
            SkillGenerationError: If node content is empty or invalid.
        """
        if not node.content or len(node.content.strip()) < 5:
            raise SkillGenerationError(f"Node {node.node_id} content is too short or empty.")

        logger.info(f"Generating SKILL for Node: {node.node_id}")
        
        # Determine function name
        func_name = self._sanitize_identifier(node.metadata.get('title', f"skill_{node.node_id}"))
        
        # Determine parameters
        if node.input_schema:
            params = list(node.input_schema.keys())
        else:
            params = self._extract_parameters_from_text(node.content)
            # Add standard context parameter
            params.append("context")
            
        params_str = ", ".join([f"{p}: Any = None" for p in params])
        
        # Generate Code Body (Template)
        # In a real scenario, an LLM would generate the logic inside the function.
        # Here we create a structured wrapper that logs the execution.
        
        code_body = f'''
def {func_name}({params_str}) -> Dict[str, Any]:
    """
    Auto-generated SKILL from Knowledge Node: {node.node_id}
    Original Content Summary: {node.content[:50]}...
    """
    import logging
    logging.info("Executing SKILL: {func_name}")
    
    # --- Input Validation ---
    # (Placeholder for specific logic validation)
    
    # --- Core Logic Simulation ---
    # This represents the 'knowledge' being executed.
    # For 'Tomato Scrambled Eggs', this would contain cooking steps.
    
    execution_log = []
    execution_log.append("Starting process...")
    
    # Accessing parameters safely
    args_local = locals()
    
    # Simulating logic based on parameters
    if "eggs" in args_local and args_local["eggs"]:
        execution_log.append(f"Using {{args_local['eggs']}} eggs.")
    else:
        execution_log.append("No eggs specified, using default 2.")
        
    # --- Return Result ---
    result = {{
        "status": "SUCCESS",
        "action": "{func_name}",
        "logs": execution_log,
        "input_received": {{k: v for k, v in args_local.items() if v is not None}}
    }}
    return result
'''
        
        skill = ExecutableSkill(
            skill_id=f"sk_{uuid.uuid4().hex[:12]}",
            source_node_id=node.node_id,
            func_name=func_name,
            code_body=code_body,
            parameters=params,
            status="DRAFT"
        )
        
        return skill

    def compile_and_register(self, skill: ExecutableSkill) -> ExecutableSkill:
        """
        Core Function 2: Compiles the generated code and registers the callable.
        
        Args:
            skill: The ExecutableSkill (usually in DRAFT state).
            
        Returns:
            The updated ExecutableSkill with the 'executor' populated.
            
        Raises:
            CodeCompilationError: If the code syntax is invalid.
        """
        logger.info(f"Compiling SKILL: {skill.skill_id}")
        try:
            # Compile the code in a restricted local scope
            local_scope: Dict[str, Any] = {}
            compiled_code = compile(skill.code_body, filename="<string>", mode="exec")
            exec(compiled_code, globals(), local_scope)
            
            if skill.func_name not in local_scope:
                raise CodeCompilationError(f"Function {skill.func_name} not found in generated code.")
                
            skill.executor = local_scope[skill.func_name]
            skill.status = "COMPILED"
            self._registry[skill.skill_id] = skill
            logger.info(f"SKILL {skill.skill_id} compiled and registered successfully.")
            
        except SyntaxError as se:
            skill.status = "FAILED"
            logger.error(f"Syntax Error in skill {skill.skill_id}: {se}")
            raise CodeCompilationError(f"Syntax error: {se}")
        except Exception as e:
            skill.status = "FAILED"
            logger.error(f"Error compiling skill {skill.skill_id}: {e}")
            raise CodeCompilationError(f"Compilation failed: {e}")
            
        return skill

    def execute_skill(self, skill_id: str, **kwargs) -> Dict[str, Any]:
        """
        Helper: Executes a registered skill by ID with provided arguments.
        
        Args:
            skill_id: The ID of the compiled skill.
            **kwargs: Arguments to pass to the skill function.
            
        Returns:
            The execution result dictionary.
        """
        if skill_id not in self._registry:
            raise ValueError(f"Skill ID {skill_id} not found in registry.")
            
        skill = self._registry[skill_id]
        
        if not skill.executor or skill.status != "COMPILED":
            raise SkillGenerationError("Skill is not compiled or invalid.")
            
        logger.info(f"Executing skill {skill_id} with args: {kwargs.keys()}")
        
        # Basic validation
        missing_params = []
        for p in skill.parameters:
            if p != "context" and p not in kwargs:
                # In strict mode, we might raise error. Here we allow defaults.
                logger.warning(f"Missing parameter '{p}' for skill {skill_id}")
        
        try:
            result = skill.executor(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Runtime error in skill {skill_id}: {e}")
            return {"status": "ERROR", "message": str(e)}

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define a Knowledge Node (Theoretical Knowledge)
    node_content = """
    How to make Tomato Scrambled Eggs:
    1. Prepare 2 eggs and 1 tomato.
    2. Beat the eggs with a pinch of salt.
    3. Heat oil in a pan.
    4. Pour in eggs, scramble, then add chopped tomato.
    5. Cook for 3 minutes.
    """
    
    knowledge_node = KnowledgeNode(
        node_id="kn_98231",
        content=node_content,
        metadata={"title": "Tomato Scrambled Eggs Recipe"},
        input_schema={"eggs": "int", "tomatoes": "float"} # Optional hint
    )

    # 2. Initialize Protocol
    protocol = SkillWrapperProtocol()

    try:
        # 3. Generate Code
        draft_skill = protocol.generate_skill_code(knowledge_node)
        print(f"--- Generated Code for {draft_skill.func_name} ---")
        print(draft_skill.code_body)
        print("-" * 40)

        # 4. Compile
        compiled_skill = protocol.compile_and_register(draft_skill)
        
        # 5. Execute
        result = protocol.execute_skill(
            compiled_skill.skill_id, 
            eggs=3, 
            tomatoes=1.5
        )
        
        print("--- Execution Result ---")
        print(json.dumps(result, indent=2))
        
    except SkillGenerationError as e:
        print(f"Failed to process knowledge node: {e}")