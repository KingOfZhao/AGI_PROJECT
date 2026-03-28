"""
Module: neuro_symbolic_middleware.py

A high-level Python module implementing a Neuro-Symbolic Middleware for LLM reasoning.
This module introduces compiler optimization concepts—specifically Constant Propagation
and Dead Code Elimination—into the context generation process.

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReasoningError(Exception):
    """Custom exception for reasoning failures."""
    pass

class SymbolicState(Enum):
    """Enumeration for the state of a symbolic fact."""
    CONCRETE = 1    # Constant/Fact
    ABSTRACT = 2    # Variable/Unknown
    PRUNED = 3      # Ignored/Dead Code

@dataclass
class ThoughtRegister:
    """
    Represents the 'Working Memory' or Thought Register.
    Acts as a scratchpad for the reasoning process.
    """
    register_id: str
    facts: Dict[str, str] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    max_capacity: int = 5

    def update(self, key: str, value: str):
        """Updates a fact in the register."""
        if len(self.facts) >= self.max_capacity and key not in self.facts:
            # Simple FIFO eviction policy for demo
            oldest_key = next(iter(self.facts))
            del self.facts[oldest_key]
            logger.debug(f"Register {self.register_id}: Evicted {oldest_key}")
        
        self.facts[key] = value
        self.history.append(f"Updated {key}")

class NeuroSymbolicMiddleware:
    """
    Middleware that sits between the User/Agent and the LLM.
    It optimizes the prompt context using symbolic logic rules.
    
    Attributes:
        constants (Dict): Known facts (Constant Propagation).
        dead_patterns (List[re.Pattern]): Regex patterns for irrelevant context (Dead Code Elimination).
        register (ThoughtRegister): The active working memory.
    """

    def __init__(self, initial_facts: Optional[Dict[str, str]] = None):
        """
        Initialize the middleware.
        
        Args:
            initial_facts (Optional[Dict]): Pre-existing knowledge base.
        """
        self.constants = initial_facts if initial_facts else {}
        self.dead_patterns = [
            re.compile(r"(Disclaimer:.*?(\n|$))", re.IGNORECASE),
            re.compile(r"(As an AI language model.*?(\n|$))", re.IGNORECASE),
            re.compile(r"(\[IRR\].*?(\n|$))", re.IGNORECASE) # Custom tag for irrelevant info
        ]
        self.register = ThoughtRegister(register_id="main_logic_window")
        logger.info("Neuro-Symbolic Middleware Initialized.")

    def _validate_input(self, context: str) -> bool:
        """
        Helper function to validate input context.
        
        Args:
            context (str): The raw input text.
            
        Returns:
            bool: True if valid.
            
        Raises:
            ReasoningError: If input is empty or invalid type.
        """
        if not isinstance(context, str):
            raise ReasoningError(f"Input context must be str, got {type(context)}")
        if not context.strip():
            logger.warning("Empty context received.")
            return False
        return True

    def apply_constant_propagation(self, context: str) -> str:
        """
        Core Function 1: Constant Propagation.
        Replaces symbolic variables in the context with known concrete values
        from the 'constants' store. This solidifies facts before inference.
        
        Args:
            context (str): The raw reasoning trace or prompt.
            
        Returns:
            str: The context with variables substituted by facts.
        """
        if not self._validate_input(context):
            return context

        logger.debug("Applying Constant Propagation...")
        modified_context = context
        
        # Iterate over known facts and replace placeholders or references
        for var, val in self.constants.items():
            # Pattern looks for {{var}} or [var]
            pattern = re.compile(rf"(\{{{{{var}\}}}}|\[{var}\])", re.IGNORECASE)
            if pattern.search(modified_context):
                modified_context = pattern.sub(val, modified_context)
                self.register.update(var, val)
                logger.info(f"Propagated constant: {var} -> {val}")
                
        return modified_context

    def apply_dead_code_elimination(self, context: str) -> str:
        """
        Core Function 2: Dead Code Elimination.
        Removes segments of text that match 'dead' patterns (hallucinations,
        boilerplate, or explicitly tagged irrelevant data) to reduce token noise.
        
        Args:
            context (str): The context string.
            
        Returns:
            str: The pruned context string.
        """
        if not self._validate_input(context):
            return context

        logger.debug("Applying Dead Code Elimination (Pruning)...")
        lines = context.split('\n')
        pruned_lines = []
        
        removed_count = 0
        for line in lines:
            is_dead = False
            for pattern in self.dead_patterns:
                if pattern.search(line):
                    is_dead = True
                    removed_count += 1
                    break
            
            if not is_dead:
                pruned_lines.append(line)
        
        if removed_count > 0:
            logger.info(f"Pruned {removed_count} irrelevant lines (Dead Code).")
            
        return "\n".join(pruned_lines)

    def process_reasoning_trace(self, raw_trace: str) -> Tuple[str, Dict]:
        """
        Main pipeline function. Chains optimization steps.
        
        Args:
            raw_trace (str): The input prompt or reasoning chain.
            
        Returns:
            Tuple[str, Dict]: The optimized context and metadata about the operation.
        """
        try:
            # Step 1: Validate
            if not self._validate_input(raw_trace):
                return raw_trace, {"status": "skipped"}

            # Step 2: Constant Propagation (Facts Injection)
            propagated_context = self.apply_constant_propagation(raw_trace)

            # Step 3: Dead Code Elimination (Context Pruning)
            clean_context = self.apply_dead_code_elimination(propagated_context)

            # Metadata generation
            stats = {
                "original_length": len(raw_trace),
                "optimized_length": len(clean_context),
                "compression_ratio": round(len(clean_context) / len(raw_trace), 2) if len(raw_trace) > 0 else 0,
                "register_state": self.register.facts
            }
            
            return clean_context, stats

        except Exception as e:
            logger.error(f"Critical error in reasoning trace processing: {e}")
            raise ReasoningError(f"Processing failed: {e}") from e

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Setup initial knowledge base (The 'Compiler' Knowledge)
    known_facts = {
        "user_name": "Alice",
        "target_city": "Tokyo",
        "date": "2023-10-27"
    }

    # 2. Initialize Middleware
    middleware = NeuroSymbolicMiddleware(initial_facts=known_facts)

    # 3. Simulate a raw LLM input/Chain of Thought containing placeholders and noise
    raw_input_prompt = """
    [SYSTEM] Please assist the user.
    User: Hi, I am {{user_name}}. I need travel help.
    Assistant: Sure, [target_city] is great. 
    [IRR] Ignore this internal debug text.
    Disclaimer: I am an AI language model and cannot book real flights.
    Date: [date].
    Please generate an itinerary for {{target_city}}.
    """

    print("--- Raw Input ---")
    print(raw_input_prompt)

    # 4. Process through the Neuro-Symbolic Middleware
    optimized_prompt, stats = middleware.process_reasoning_trace(raw_input_prompt)

    print("\n--- Optimized Context (Sent to LLM) ---")
    print(optimized_prompt)

    print("\n--- Execution Stats ---")
    print(f"Compression Ratio: {stats['compression_ratio']}")
    print(f"Working Memory: {stats['register_state']}")