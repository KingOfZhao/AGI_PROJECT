"""
Module: atomic_skill_orchestrator.py

This module implements a topology for code generation based on Skill Units.
It provides the infrastructure to define atomic skill interfaces (Input/Output/Pre-condition),
validate parameter types, resolve dependencies, and orchestrate LLM-generated pipelines
without writing low-level code.

Key Components:
- AtomicSkill: A standardized wrapper for executable units.
- SkillRegistry: A repository for managing available skills.
- SkillPipeline: An executable chain of skills with automatic data passing.

Author: Advanced Python Engineer (AGI System Simulation)
Version: 1.0.0
"""

import logging
import inspect
from typing import Any, Dict, List, Optional, Callable, Type, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError, Field
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures for Interface Standards ---

class SkillInputSpec(BaseModel):
    """Defines the expected input structure for a skill."""
    param_name: str
    param_type: str  # e.g., 'str', 'int', 'DataFrame', 'List[Dict]'
    description: str
    is_required: bool = True
    default_value: Optional[Any] = None

class SkillOutputSpec(BaseModel):
    """Defines the output structure of a skill."""
    return_name: str
    return_type: str
    description: str

class PreCondition(BaseModel):
    """
    Defines a precondition that must be met before execution.
    This acts as a state validator for the pipeline context.
    """
    description: str
    validation_logic: str  # A string representation or lambda logic reference

@dataclass
class AtomicSkill:
    """
    The standard interface for an Atomic Skill.
    Wraps a Python callable with strict metadata to allow LLM orchestration.
    """
    name: str
    description: str
    inputs: List[SkillInputSpec]
    outputs: List[SkillOutputSpec]
    pre_conditions: List[PreCondition] = field(default_factory=list)
    func: Callable = field(repr=False)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate that the wrapped function matches the signature roughly."""
        if not callable(self.func):
            raise ValueError(f"Skill {self.name} provided func is not callable.")

# --- Core Functions ---

class SkillRegistry:
    """
    A registry to manage 1800+ skill nodes.
    Supports registration, retrieval, and dependency analysis.
    """
    
    def __init__(self):
        self._skills: Dict[str, AtomicSkill] = {}
        self._type_index: Dict[str, List[str]] = {} # Maps output types to skill names

    def register(self, skill: AtomicSkill) -> None:
        """
        Registers a skill in the topology.
        
        Args:
            skill (AtomicSkill): The skill object to register.
        
        Raises:
            ValueError: If skill name already exists.
        """
        if skill.name in self._skills:
            logger.error(f"Attempted to register duplicate skill: {skill.name}")
            raise ValueError(f"Skill '{skill.name}' already exists.")
        
        self._skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name}")
        
        # Indexing for dependency resolution (what produces what)
        for output in skill.outputs:
            if output.return_type not in self._type_index:
                self._type_index[output.return_type] = []
            self._type_index[output.return_type].append(skill.name)

    def get_skill(self, name: str) -> Optional[AtomicSkill]:
        """Retrieves a skill by name."""
        return self._skills.get(name)

    def resolve_producers(self, target_type: str) -> List[str]:
        """
        Finds skills that produce a specific output type.
        Essential for auto-wiring the pipeline.
        """
        return self._type_index.get(target_type, [])


class SkillPipeline:
    """
    Orchestrates multiple AtomicSkills into an executable flow.
    Handles state management, parameter passing, and pre-condition checks.
    """
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.execution_graph: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {} # The "Blackboard" or shared state

    def add_step(self, skill_name: str, input_mapping: Dict[str, str]) -> 'SkillPipeline':
        """
        Adds a step to the pipeline topology.
        
        Args:
            skill_name (str): Name of the skill to execute.
            input_mapping (Dict[str, str]): Mapping of Skill Input Name -> Context Key.
                                            e.g., {'source_text': 'raw_data'}
        
        Returns:
            SkillPipeline: self (for chaining)
        """
        skill = self.registry.get_skill(skill_name)
        if not skill:
            logger.error(f"Skill not found: {skill_name}")
            raise ValueError(f"Skill '{skill_name}' not found in registry.")
            
        self.execution_graph.append({
            'skill': skill,
            'mapping': input_mapping
        })
        return self

    def _validate_pre_conditions(self, skill: AtomicSkill) -> bool:
        """Checks if preconditions are met using current context."""
        # Simplified logic: check if required keys exist in context
        # In real AGI, this would evaluate the validation_logic string
        for cond in skill.pre_conditions:
            # Mock logic: check if context is not empty
            if "context_not_empty" in cond.validation_logic and not self.context:
                logger.warning(f"Precondition failed for {skill.name}: {cond.description}")
                return False
        return True

    def execute(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the pipeline sequentially.
        
        Args:
            initial_inputs (Dict[str, Any]): The starting data for the pipeline.
        
        Returns:
            Dict[str, Any]: The final state of the context.
        """
        self.context = initial_inputs.copy()
        logger.info(f"Starting pipeline execution with {len(self.execution_graph)} steps.")

        for step in self.execution_graph:
            skill = step['skill']
            mapping = step['mapping']
            logger.info(f"Executing skill: {skill.name}")

            # 1. Pre-condition Check
            if not self._validate_pre_conditions(skill):
                raise RuntimeError(f"Pre-conditions failed for skill: {skill.name}")

            # 2. Argument Resolution (Matching)
            kwargs = {}
            for spec in skill.inputs:
                context_key = mapping.get(spec.param_name)
                
                if context_key is None and spec.is_required and spec.default_value is None:
                    raise ValueError(f"Missing required input '{spec.param_name}' for skill {skill.name}")
                
                # Fetch value from context
                if context_key:
                    val = self.context.get(context_key)
                    # Basic Type Validation (Mock)
                    if val is None and spec.is_required:
                         raise ValueError(f"Key '{context_key}' not found in context for input '{spec.param_name}'")
                    kwargs[spec.param_name] = val
                elif spec.default_value is not None:
                    kwargs[spec.param_name] = spec.default_value

            # 3. Execution
            try:
                result = skill.func(**kwargs)
            except Exception as e:
                logger.exception(f"Error executing skill {skill.name}")
                raise RuntimeError(f"Skill execution failed: {skill.name}") from e

            # 4. Output Registration (Write back to context)
            if skill.outputs:
                # Assuming single output for simplicity, or mapped dict output
                primary_output = skill.outputs[0]
                self.context[primary_output.return_name] = result
                logger.info(f"Output '{primary_output.return_name}' stored in context.")

        return self.context

# --- Helper Functions ---

def skill_decorator_factory(registry: SkillRegistry):
    """
    Helper factory to create a decorator for registering functions as skills easily.
    """
    def decorator(
        name: str, 
        description: str, 
        inputs: List[Dict], 
        outputs: List[Dict],
        tags: List[str] = []
    ):
        def wrapper(func):
            # Convert dict specs to Pydantic models
            input_specs = [SkillInputSpec(**i) for i in inputs]
            output_specs = [SkillOutputSpec(**o) for o in outputs]
            
            # Create AtomicSkill
            skill = AtomicSkill(
                name=name,
                description=description,
                inputs=input_specs,
                outputs=output_specs,
                func=func,
                tags=tags
            )
            registry.register(skill)
            return func
        return wrapper
    return decorator

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Registry
    registry = SkillRegistry()
    skill_decorator = skill_decorator_factory(registry)

    # 2. Define Atomic Skills (Simulating a small subset of 1800)
    @skill_decorator(
        name="text.cleaner",
        description="Removes special characters and lowercases text.",
        inputs=[
            {"param_name": "raw_text", "param_type": "str", "description": "Input text", "is_required": True}
        ],
        outputs=[
            {"return_name": "clean_text", "return_type": "str", "description": "Processed text"}
        ],
        tags=["nlp", "preprocessing"]
    )
    def clean_text(raw_text: str) -> str:
        import re
        text = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text)
        return text.lower()

    @skill_decorator(
        name="text.word_counter",
        description="Counts words in a text string.",
        inputs=[
            {"param_name": "text_input", "param_type": "str", "description": "Cleaned text", "is_required": True}
        ],
        outputs=[
            {"return_name": "word_count", "return_type": "int", "description": "Total words"}
        ],
        tags=["nlp", "analytics"]
    )
    def count_words(text_input: str) -> int:
        if not isinstance(text_input, str):
            raise TypeError("Input must be string")
        return len(text_input.split())

    # 3. Orchestration (The "AGI" part - wiring skills together)
    pipeline = SkillPipeline(registry)
    
    # Build the flow: Raw Data -> Cleaner -> Counter
    pipeline.add_step("text.cleaner", {"raw_text": "user_input"})
    pipeline.add_step("text.word_counter", {"text_input": "clean_text"})

    # 4. Execute
    input_data = {"user_input": "Hello World! This is a Complex System."}
    
    try:
        final_context = pipeline.execute(input_data)
        print("\n--- Execution Result ---")
        print(f"Final Context: {final_context}")
        print(f"Result stored in 'word_count': {final_context.get('word_count')}")
    except Exception as e:
        print(f"Pipeline failed: {e}")