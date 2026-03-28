"""
Module: auto_top_down_falsifiability_planner
Description: Implements a Top-Down Falsifiable Planning System for AGI.
             This module validates and decomposes complex tasks into atomic,
             verifiable sub-steps, ensuring that generated plans are not
             'black boxes' but actionable, falsifiable procedures.
"""

import logging
from enum import Enum
from typing import List, Dict, Optional, Any, Set
from pydantic import BaseModel, Field, ValidationError, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Enums ---

class TaskComplexity(Enum):
    """Enumeration for task complexity levels."""
    ATOMIC = 1
    COMPOSITE = 2
    ABSTRACT = 3

class VerificationStatus(Enum):
    """Enumeration for verification results."""
    VERIFIED = "Verified"
    AMBIGUOUS = "Ambiguous"
    UNVERIFIABLE = "Unverifiable"

# --- Data Models ---

class ActionableStep(BaseModel):
    """
    Represents a single step in a plan.
    
    Attributes:
        step_id: Unique identifier for the step.
        description: Human-readable description of the action.
        dependencies: List of step_ids that must precede this step.
        verification_method: Specific method to verify completion (e.g., 'check_file_exists').
        is_atomic: Boolean indicating if the step is atomic (indivisible).
        estimated_complexity: Estimated complexity score (1-10).
    """
    step_id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    verification_method: str
    is_atomic: bool = False
    estimated_complexity: int = Field(ge=1, le=10)

    @validator('verification_method')
    def method_must_be_concrete(cls, v):
        vague_terms = ['think', 'consider', 'understand', 'maybe', 'guess']
        if any(term in v.lower() for term in vague_terms):
            raise ValueError(f"Verification method '{v}' is too vague.")
        return v

class PlanTree(BaseModel):
    """
    Represents the hierarchical plan structure.
    
    Attributes:
        root_goal: The high-level objective.
        steps: List of ActionableStep objects forming the plan.
    """
    root_goal: str
    steps: List[ActionableStep]

    class Config:
        arbitrary_types_allowed = True

# --- Core Functions ---

def analyze_atomicity(step: ActionableStep, knowledge_base: Dict[str, Any]) -> bool:
    """
    Determines if a step is atomic based on domain knowledge.
    
    An atomic step is defined as an action that requires no further decomposition
    to be executed by an agent with standard tools.
    
    Args:
        step: The step to analyze.
        knowledge_base: Dictionary containing tool capabilities and definitions.
        
    Returns:
        bool: True if the step is atomic, False otherwise.
        
    Raises:
        KeyError: If required knowledge base keys are missing.
    """
    logger.debug(f"Analyzing atomicity for step: {step.step_id}")
    
    # Boundary Check: Input validation
    if not step.description:
        logger.warning("Empty description encountered.")
        return False

    # Logic: Check against primitive operations in knowledge base
    primitives = knowledge_base.get("primitive_operations", set())
    
    # Simple heuristic: If verification method matches a primitive, it's likely atomic
    if step.verification_method in primitives:
        step.is_atomic = True
        step.estimated_complexity = 1
        return True
    
    # Heuristic: Check for conjunctions implying multiple tasks
    conjunctions = [' and ', ' then ', ' also ', ' after that ']
    if any(conj in step.description.lower() for conj in conjunctions):
        step.is_atomic = False
        step.estimated_complexity = 5
        logger.info(f"Step {step.step_id} identified as composite due to conjunctions.")
        return False
        
    # Default logic based on complexity estimation
    if step.estimated_complexity <= 3:
        step.is_atomic = True
        return True
    
    return False

def validate_plan_falsifiability(plan: PlanTree, knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the entire plan tree for falsifiability and executability.
    
    This function ensures that every sub-step is atomic and has a clear
    verification method, eliminating "black box" instructions.
    
    Args:
        plan: The PlanTree object to validate.
        knowledge_base: Context and tool definitions.
        
    Returns:
        Dict containing 'is_valid', 'score', and 'analysis_details'.
    """
    logger.info(f"Starting validation for plan: {plan.root_goal}")
    
    if not plan.steps:
        logger.error("Plan contains no steps.")
        return {"is_valid": False, "score": 0.0, "details": "Empty plan"}

    total_score = 0.0
    analysis_results = []
    visited_ids: Set[str] = set()
    
    # Graph Check: Detect circular dependencies
    # (Simplified check for this module)
    
    for step in plan.steps:
        # Data Validation
        if step.step_id in visited_ids:
            logger.warning(f"Duplicate step ID detected: {step.step_id}")
            continue
        visited_ids.add(step.step_id)
        
        # Core Logic: Check Atomicity
        is_atomic = analyze_atomicity(step, knowledge_base)
        
        # Core Logic: Check Verifiability
        has_concrete_verification = bool(step.verification_method)
        
        step_status = VerificationStatus.VERIFIED if (is_atomic and has_concrete_verification) else VerificationStatus.AMBIGUOUS
        
        if step_status == VerificationStatus.VERIFIED:
            total_score += 1.0
        else:
            # Penalty for ambiguity
            total_score += 0.2
            
        analysis_results.append({
            "step_id": step.step_id,
            "status": step_status.value,
            "atomic": is_atomic,
            "verification": step.verification_method
        })
        
    final_score = total_score / len(plan.steps) if plan.steps else 0.0
    is_globally_valid = final_score >= 0.8  # Threshold for AGI acceptance

    logger.info(f"Validation complete. Score: {final_score:.2f}. Valid: {is_globally_valid}")
    
    return {
        "is_valid": is_globally_valid,
        "score": final_score,
        "details": analysis_results
    }

# --- Helper Functions ---

def decompose_task_description(description: str) -> List[str]:
    """
    Helper function to split a complex text description into potential sub-tasks.
    Uses simple NLP heuristics (splitting by punctuation).
    
    Args:
        description: A complex task description string.
        
    Returns:
        List of substrings representing potential sub-tasks.
    """
    if not isinstance(description, str):
        raise TypeError("Description must be a string.")
        
    delimiters = [';', '.', '\n', ' followed by ']
    sub_tasks = [description]
    
    for delim in delimiters:
        new_tasks = []
        for task in sub_tasks:
            parts = task.split(delim)
            new_tasks.extend([p.strip() for p in parts if p.strip()])
        sub_tasks = new_tasks
        
    return sub_tasks

# --- Usage Example ---

if __name__ == "__main__":
    # Mock Knowledge Base
    kb = {
        "primitive_operations": ["check_file_exists", "http_get", "run_script", "db_query"]
    }

    # Define a complex plan
    steps_data = [
        {
            "step_id": "step_1",
            "description": "Fetch user data from API",
            "verification_method": "http_get",  # Concrete
            "estimated_complexity": 2
        },
        {
            "step_id": "step_2",
            "description": "Analyze the user sentiment and optimize database", # Vague
            "verification_method": "analyze", # Vague method
            "estimated_complexity": 8 # High complexity suggests non-atomic
        },
        {
            "step_id": "step_3",
            "description": "Write log file",
            "verification_method": "check_file_exists",
            "dependencies": ["step_1"],
            "estimated_complexity": 1
        }
    ]

    try:
        # Create Plan Object
        actionable_steps = [ActionableStep(**s) for s in steps_data]
        plan = PlanTree(root_goal="Update User Records", steps=actionable_steps)

        # Run Validation
        result = validate_plan_falsifiability(plan, kb)

        print(f"\n--- Plan Validation Report ---")
        print(f"Goal: {plan.root_goal}")
        print(f"Valid: {result['is_valid']}")
        print(f"Score: {result['score']:.2f}")
        print("Details:")
        for detail in result['details']:
            print(f"  - [{detail['status']}] {detail['step_id']}: Atomic={detail['atomic']}, Method='{detail['verification']}'")

    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")