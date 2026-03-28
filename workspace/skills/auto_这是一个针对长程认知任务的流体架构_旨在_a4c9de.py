"""
Module: auto_cognitive_fluidity_a4c9de
A Fluid Architecture for Long-Range Cognitive Tasks.

This module implements a dynamic memory management system designed to mitigate 
'forgetting' and 'defocusing' issues in Large Language Models (LLMs) during 
complex, long-horizon tasks. It reimagines the static context window as a 
temporal 'Cognitive River', utilizing Ebbinghaus forgetting curves for context 
pruning and incremental generation protocols.
"""

import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveFluidity")


class ContextType(Enum):
    """Defines the type of cognitive content."""
    SYSTEM_CORE = 10        # Immutable core instructions (e.g., persona)
    CRITICAL_INTENT = 9     # High-priority goals (e.g., 'maintain code style')
    SYNTACTIC_ANCHOR = 7    # Structural markers (e.g., class definitions, TODOs)
    EPISODIC = 3            # Intermediate steps, historical data
    NOISE = 1               # Low-value filler content


@dataclass
class CognitiveFragment:
    """Represents a single unit of information in the cognitive stream."""
    content: str
    type: ContextType
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.5  # Lambda for exponential decay
    
    @property
    def salience(self) -> float:
        """
        Calculates current salience based on time elapsed and access frequency.
        Formula: Salience = (BaseWeight * (1 + log(Access + 1))) * e^(-DecayRate * TimeDelta)
        """
        time_elapsed = time.time() - self.timestamp
        base_weight = self.type.value
        frequency_boost = 1 + math.log(self.access_count + 1)
        retention = math.exp(-self.decay_rate * time_elapsed)
        return base_weight * frequency_boost * retention


class CognitiveManifold:
    """
    The core data structure representing the dynamic 'Cognitive Manifold'.
    Manages the insertion, decay, and retrieval of context segments.
    """

    def __init__(self, max_capacity: int = 100, retention_threshold: float = 0.1):
        """
        Initialize the Cognitive Manifold.

        Args:
            max_capacity (int): Maximum number of fragments before forced pruning.
            retention_threshold (float): Minimum salience score to remain in active memory.
        """
        if max_capacity <= 0:
            raise ValueError("max_capacity must be a positive integer")
        
        self._stream: List[CognitiveFragment] = []
        self._max_capacity = max_capacity
        self._retention_threshold = retention_threshold
        self._intent_graph: Dict[str, float] = {}  # Tracking core intents
        
        logger.info(f"CognitiveManifold initialized with capacity {max_capacity}")

    def _classify_content(self, content: str) -> ContextType:
        """
        Helper: Heuristically classify content type based on syntax/keywords.
        """
        content = content.strip()
        if not content:
            return ContextType.NOISE
        
        # Simple heuristics for demonstration
        if "CRITICAL:" in content or "OBJECTIVE:" in content:
            return ContextType.CRITICAL_INTENT
        if re.match(r"^(def |class |import |function |var )", content):
            return ContextType.SYNTACTIC_ANCHOR
        if len(content) < 5:
            return ContextType.NOISE
        
        return ContextType.EPISODIC

    def inject(self, content: str, explicit_type: Optional[ContextType] = None) -> None:
        """
        Injects new information into the cognitive stream.

        Args:
            content (str): The text/information to add.
            explicit_type (Optional[ContextType]): Override automatic classification.
        """
        if not isinstance(content, str):
            raise TypeError("Content must be a string")
        
        c_type = explicit_type if explicit_type else self._classify_content(content)
        
        fragment = CognitiveFragment(content=c_content, type=c_type)
        
        # If it's a critical intent, register it in the intent graph
        if c_type == ContextType.CRITICAL_INTENT:
            self._intent_graph[content] = 1.0
            logger.debug(f"Registered core intent: {content[:20]}...")

        self._stream.append(fragment)
        logger.debug(f"Injected fragment: Type={c_type.name}, Content='{content[:30]}...'")
        
        # Trigger flow regulation if capacity is reached
        if len(self._stream) > self._max_capacity:
            self.regulate_flow()

    def regulate_flow(self) -> None:
        """
        Core Mechanism: The 'Forgetting Curve' Pruning.
        Removes fragments with salience below the threshold, preserving core intents.
        """
        original_len = len(self._stream)
        
        # Filter stream based on salience and type
        surviving_fragments = []
        for frag in self._stream:
            # Always keep System Core
            if frag.type == ContextType.SYSTEM_CORE:
                surviving_fragments.append(frag)
                continue
            
            # Keep if salience is sufficient
            if frag.salience >= self._retention_threshold:
                surviving_fragments.append(frag)
            else:
                logger.verbose(f"Pruning forgotten fragment: {frag.content[:20]}...")
                
        self._stream = surviving_fragments
        
        # If still too full, force prune oldest episodic memory
        if len(self._stream) > self._max_capacity:
            self._stream = [f for f in self._stream if f.type != ContextType.EPISODIC][:self._max_capacity]

        logger.info(f"Flow Regulated: {original_len} -> {len(self._stream)} fragments.")

    def focus_attention(self, query: str) -> str:
        """
        Generates a 'Gaze Snapshot' - a compressed context window for the LLM.
        Prioritizes high-salience items and relevant intents.

        Args:
            query (str): The current input or task step to focus on.

        Returns:
            str: The constructed context string.
        """
        # Touch (access) fragments that match query keywords to boost their salience
        keywords = set(query.lower().split())
        for frag in self._stream:
            frag_words = set(frag.content.lower().split())
            if not keywords.isdisjoint(frag_words):
                frag.access_count += 1
        
        # Sort by salience (descending)
        sorted_stream = sorted(self._stream, key=lambda f: f.salience, reverse=True)
        
        # Reconstruct context (Simple truncation for demo, sophisticated summarization in prod)
        context_parts = ["[COGNITIVE CONTEXT START]"]
        
        # Add Core Intents first
        for frag in sorted_stream:
            if frag.type in [ContextType.SYSTEM_CORE, ContextType.CRITICAL_INTENT]:
                context_parts.append(f"!! {frag.content}")
        
        # Add Syntactic Anchors
        for frag in sorted_stream:
            if frag.type == ContextType.SYNTACTIC_ANCHOR:
                context_parts.append(f"# {frag.content}")
                
        # Add recent/salient Episodic memories
        for frag in sorted_stream:
            if frag.type == ContextType.EPISODIC:
                context_parts.append(f"> {frag.content}")
                
        context_parts.append("[COGNITIVE CONTEXT END]")
        
        return "\n".join(context_parts)


def run_cognitive_cycle(manifold: CognitiveManifold, task_steps: List[str]) -> str:
    """
    Simulates a long-range task execution loop using the fluid architecture.
    This acts as the 'Incremental Generation Protocol'.

    Args:
        manifold (CognitiveManifold): The memory instance.
        task_steps (List[str]): A list of steps/sub-tasks to process.

    Returns:
        str: The final state of the context manifold.
    """
    if not manifold or not task_steps:
        raise ValueError("Invalid manifold or empty task list provided")

    logger.info(f"Starting cognitive cycle with {len(task_steps)} steps.")
    
    final_output = []
    
    for i, step in enumerate(task_steps):
        logger.info(f"Processing Step {i+1}/{len(task_steps)}: {step[:30]}...")
        
        # 1. Retrieve Context (Focus)
        current_context = manifold.focus_attention(step)
        
        # 2. Simulate Processing (Here we just echo, but an LLM would generate)
        # In a real scenario: response = llm.generate(current_context, step)
        simulated_response = f"Result of '{step}'"
        final_output.append(simulated_response)
        
        # 3. Update Memory (Learning/Retaining)
        # Inject the result as new memory
        manifold.inject(f"Step {i} result: {simulated_response}", ContextType.EPISODIC)
        
        # Simulate time passing for the decay function
        time.sleep(0.1) 
        
        # 4. Regulate (Forgetting)
        if i % 5 == 0:  # Prune every 5 steps
            manifold.regulate_flow()
            
    return manifold.focus_attention("Final Summary")

# Example Usage (Commented out but structured for docstring)
"""
if __name__ == "__main__":
    # 1. Initialize
    memory = CognitiveManifold(max_capacity=50, retention_threshold=0.2)
    
    # 2. Set Core Intent (High retention)
    memory.inject("You are a Python Engineer.", ContextType.SYSTEM_CORE)
    memory.inject("CRITICAL: Ensure PEP 8 compliance.", ContextType.CRITICAL_INTENT)
    
    # 3. Define a long task
    tasks = [
        "Write a function to parse JSON",
        "Add error handling",
        "Refactor variable names",
        "Add docstrings",
        "Write tests",
        "Optimize imports",
        "Review logging levels"
    ]
    
    # 4. Run the cycle
    final_context = run_cognitive_cycle(memory, tasks)
    print("-" * 30)
    print("Final Context State:")
    print(final_context)
"""