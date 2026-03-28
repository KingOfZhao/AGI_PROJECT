"""
Skill Module: Top-Down Decomposition and Falsification (TD-DF)
Domain: Cognitive Science / AGI Reasoning
Author: Senior Python Engineer
Version: 1.0.0

Description:
    This module implements a 'Critical Thinking' engine for complex logical reasoning tasks.
    It utilizes a 'Top-Down Decomposition' strategy to break down a hypothesis into sub-hypotheses,
    and then performs active 'Falsification' by generating counter-arguments (Red Teaming)
    against its own intermediate steps before committing to a final conclusion.

    This process mimics human scientific method and critical reasoning, ensuring robustness
    against linear bias.

Classes:
    - ReasoningState: Enum for tracking the status of reasoning steps.
    - ReasoningStep: Data model for individual reasoning nodes.
    - CriticalReasoningEngine: The core engine for decomposition and falsification.

Functions:
    - run_critical_reasoning_session: High-level API entry point.
"""

import logging
import json
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CriticalReasoningEngine")

class ReasoningState(Enum):
    """Enumeration of possible states for a reasoning step."""
    UNVERIFIED = "unverified"
    DECOMPOSED = "decomposed"
    FALSIFIED = "falsified"       # Proven wrong by counter-evidence
    SURVIVED = "survived"         # Withstood falsification attempts
    CONFIRMED = "confirmed"       # Finalized as true

@dataclass
class ReasoningStep:
    """
    Represents a single node in the reasoning tree.
    
    Attributes:
        id: Unique identifier for the step.
        content: The logical statement or hypothesis.
        parent_id: ID of the parent step (None for root).
        state: Current verification state.
        counter_arguments: List of generated arguments attempting to disprove this step.
        confidence: Calculated confidence score (0.0 to 1.0).
        metadata: Additional metadata (timestamps, etc.).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    parent_id: Optional[str] = None
    state: ReasoningState = ReasoningState.UNVERIFIED
    counter_arguments: List[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.metadata['created_at'] = datetime.utcnow().isoformat()

class ReasoningError(Exception):
    """Custom exception for reasoning engine errors."""
    pass

class CriticalReasoningEngine:
    """
    Engine that performs Top-Down Decomposition and Falsification.
    
    This engine attempts to prove a hypothesis by trying to disprove its components.
    If sub-hypotheses survive rigorous counter-argument generation, the main hypothesis
    is considered robust.
    """

    def __init__(self, max_depth: int = 3, falsification_threshold: int = 3):
        """
        Initialize the engine.
        
        Args:
            max_depth: Maximum recursion depth for decomposition.
            falsification_threshold: Minimum number of counter-arguments required per step.
        """
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        self.max_depth = max_depth
        self.falsification_threshold = falsification_threshold
        self.knowledge_base: List[ReasoningStep] = []
        logger.info("CriticalReasoningEngine initialized with depth %d and threshold %d",
                    max_depth, falsification_threshold)

    def _generate_sub_hypotheses(self, hypothesis: str) -> List[str]:
        """
        [Mock LLM/Logic Function]
        Decomposes a hypothesis into logical sub-components (Top-Down).
        
        In a real AGI system, this would query an LLM or a logic solver.
        """
        logger.debug("Decomposing hypothesis: %s", hypothesis)
        # Mock logic: simple splitting for demonstration
        if " and " in hypothesis:
            parts = hypothesis.split(" and ")
            return [p.strip() for p in parts]
        if " because " in hypothesis:
            parts = hypothesis.split(" because ")
            return [f"Precondition: {parts[1]}", f"Conclusion: {parts[0]}"]
        
        # If atomic or cannot decompose, return empty to signal leaf node
        return []

    def _generate_counter_arguments(self, statement: str) -> List[str]:
        """
        [Mock Critical Thinking Function]
        Generates potential counter-arguments or logical negations to falsify a statement.
        
        This represents the 'Red Teaming' phase.
        """
        logger.debug("Generating counter-arguments for: %s", statement)
        # Mock logic: generating generic doubt
        counters = []
        if "is" in statement:
            counters.append(f"What if '{statement.replace('is', 'is not')}'?")
        if "all" in statement.lower():
            counters.append("Is there an exception to 'all'? Have you checked edge cases?")
        
        # Ensure we meet the threshold for simulation purposes
        while len(counters) < self.falsification_threshold:
            counters.append(f"Logical Fallacy Check: Is '{statement}' circular reasoning?")
        
        return counters[:self.falsification_threshold]

    def _evaluate_resilience(self, step: ReasoningStep) -> bool:
        """
        [Mock Evaluation Function]
        Determines if a reasoning step survives the counter-arguments.
        Returns True if the step is robust, False if it is falsified.
        """
        # In a real system, an LLM would judge if the counters break the logic.
        # Here we use a simple heuristic: if the step contains "verify", it passes.
        is_robust = "verify" in step.content.lower() or "proven" in step.content.lower()
        
        if is_robust:
            logger.info("Step '%s' SURVIVED counter-arguments.", step.id)
            step.state = ReasoningState.SURVIVED
            step.confidence = 0.9
            return True
        else:
            logger.warning("Step '%s' was FALSIFIED by counter-evidence.", step.id)
            step.state = ReasoningState.FALSIFIED
            step.confidence = 0.1
            return False

    def decompose_and_falsify(self, hypothesis: str, current_depth: int = 0, parent_id: Optional[str] = None) -> ReasoningStep:
        """
        Core recursive function.
        
        1. Create a reasoning step.
        2. Generate Counter-Arguments (Falsification attempt).
        3. Evaluate Resilience.
        4. If survived, decompose further (Top-Down) until max_depth or atomic.
        
        Args:
            hypothesis: The current logical statement to process.
            current_depth: Current recursion depth.
            parent_id: ID of the parent node.
            
        Returns:
            The processed ReasoningStep.
        """
        if current_depth > self.max_depth:
            logger.info("Max recursion depth reached.")
            step = ReasoningStep(content=hypothesis, parent_id=parent_id, state=ReasoningState.UNVERIFIED)
            self.knowledge_base.append(step)
            return step

        # Step 1: Initialization
        step = ReasoningStep(content=hypothesis, parent_id=parent_id)
        self.knowledge_base.append(step)

        # Step 2: Falsification (The Critical Thinking Phase)
        try:
            counters = self._generate_counter_arguments(hypothesis)
            step.counter_arguments = counters
            
            # Step 3: Evaluation
            survived = self._evaluate_resilience(step)
            
            if not survived:
                # If falsified, we stop this branch
                return step

            # Step 4: Decomposition (Top-Down)
            sub_hypotheses = self._generate_sub_hypotheses(hypothesis)
            
            if not sub_hypotheses:
                # Leaf node
                step.state = ReasoningState.CONFIRMED
                return step
            
            step.state = ReasoningState.DECOMPOSED
            logger.info("Decomposing into %d sub-steps...", len(sub_hypotheses))
            
            valid_children = 0
            for sub_h in sub_hypotheses:
                # Recursive call
                child_step = self.decompose_and_falsify(sub_h, current_depth + 1, step.id)
                if child_step.state in [ReasoningState.SURVIVED, ReasoningState.CONFIRMED, ReasoningState.DECOMPOSED]:
                    valid_children += 1
            
            # If all children failed, parent logically fails too (or confidence drops)
            if valid_children < len(sub_hypotheses):
                step.confidence *= 0.5 
                logger.warning("Partial failure in sub-steps for %s", step.id)

        except Exception as e:
            logger.error("Error during reasoning step %s: %s", step.id, e)
            step.state = ReasoningState.FALSIFIED
            raise ReasoningError(f"Reasoning failed at step {step.id}") from e

        return step

def format_output(result_step: ReasoningStep) -> Dict[str, Any]:
    """
    Helper function to format the final result into a readable dictionary.
    """
    return {
        "final_conclusion": result_step.content,
        "status": result_step.state.value,
        "confidence": result_step.confidence,
        "last_counter_args": result_step.counter_arguments,
        "step_id": result_step.id
    }

def run_critical_reasoning_session(hypothesis: str, complexity_depth: int = 2) -> Dict[str, Any]:
    """
    High-level entry point for the skill.
    
    Args:
        hypothesis (str): The complex logical statement or problem to solve.
        complexity_depth (int): How deep the reasoning tree should go.
        
    Returns:
        Dict: A structured report of the reasoning process and final conclusion.
        
    Example:
        >>> result = run_critical_reasoning_session(
        ...     "The system is secure because the firewall is active and the code is verified", 
        ...     complexity_depth=2
        ... )
        >>> print(result['status'])
    """
    if not hypothesis or len(hypothesis) < 10:
        raise ValueError("Hypothesis is too short or empty.")
        
    engine = CriticalReasoningEngine(max_depth=complexity_depth)
    
    try:
        logger.info("Starting Critical Reasoning Session for: %s", hypothesis)
        final_step = engine.decompose_and_falsify(hypothesis)
        
        # In a real scenario, we might aggregate results from engine.knowledge_base
        # Here we return the root node status which aggregates the tree
        return format_output(final_step)
        
    except ReasoningError as re:
        logger.critical("Session failed: %s", re)
        return {"error": str(re), "status": "failed"}

if __name__ == "__main__":
    # Usage Example
    input_hypothesis = "The code is bug-free because it passed all unit tests and was reviewed by a senior dev."
    
    print(f"--- Starting Analysis for: '{input_hypothesis}' ---\n")
    
    result = run_critical_reasoning_session(input_hypothesis, complexity_depth=2)
    
    print("--- Analysis Complete ---")
    print(json.dumps(result, indent=2))