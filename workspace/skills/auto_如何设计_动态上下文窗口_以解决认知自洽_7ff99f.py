"""
Module: dynamic_context_window.py

This module implements a Dynamic Context Window (DCW) mechanism to address 
cognitive consistency issues in long-horizon AGI tasks. 

It introduces a 'Core Intent Anchoring' mechanism where high-level directives 
(e.g., 'Maintain Code Style') are treated as immutable constraints, while 
short-term operational contexts are allowed to evolve. The system continuously 
validates generated outputs against these core intents to prevent 'intention drift' 
during complex, multi-step operations like large-scale code refactoring.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentPriority(Enum):
    """Enumeration for context intent priority levels."""
    CORE = 0      # Immutable, strict constraints (e.g., Safety, Style Guide)
    STRATEGIC = 1 # High-level goals (e.g., Refactor Module A)
    TACTICAL = 2  # Immediate steps (e.g., Rename variable x)


@dataclass
class ContextBlock:
    """
    Represents a discrete unit of context within the sliding window.
    
    Attributes:
        id: Unique identifier for the context block.
        content: The actual content/data of the context.
        priority: The priority level determining retention behavior.
        timestamp: Creation time for decay calculation.
        relevance_score: A score (0.0-1.0) indicating current relevance.
    """
    id: str
    content: Any
    priority: IntentPriority
    timestamp: float = field(default_factory=time.time)
    relevance_score: float = 1.0

    def decay(self, factor: float) -> None:
        """Reduces relevance over time or operations."""
        if self.priority != IntentPriority.CORE:
            self.relevance_score *= factor


class ContextWindowError(Exception):
    """Custom exception for context window operations."""
    pass


class DynamicContextWindow:
    """
    Manages the active context for an AGI agent, ensuring cognitive consistency
    by anchoring core intents and validating outputs against them.
    
    The window consists of:
    1. Anchors: High-priority, non-decaying context blocks.
    2. Active Buffer: Short-term memory that slides/decays.
    
    Methods:
        register_intent: Add a new intent to the window.
        update_window: Slide the window and apply decay.
        validate_action: Check if a proposed action violates core intents.
    """

    def __init__(self, max_tokens: int = 4096, decay_factor: float = 0.95):
        """
        Initialize the Dynamic Context Window.
        
        Args:
            max_tokens: Maximum capacity of the context window (abstract representation).
            decay_factor: The factor by which tactical context relevance decays per step.
        """
        if max_tokens <= 0:
            raise ValueError("Max tokens must be positive.")
        
        self._max_tokens = max_tokens
        self._decay_factor = decay_factor
        self._registry: Dict[str, ContextBlock] = {}
        self._current_load = 0
        logger.info(f"DynamicContextWindow initialized with capacity {max_tokens}.")

    def register_intent(
        self, 
        content: Any, 
        priority: IntentPriority, 
        block_id: Optional[str] = None
    ) -> str:
        """
        Registers a new context block into the window.
        
        Args:
            content: The context data (e.g., a rule, a code snippet).
            priority: The priority level (CORE intents are protected).
            block_id: Optional ID, auto-generated if None.
            
        Returns:
            The ID of the registered block.
        """
        try:
            # Estimate 'size' of the content for simulation
            size = len(str(content)) 
            if size > self._max_tokens:
                raise ContextWindowError("Single block exceeds window capacity.")

            bid = block_id or f"ctx_{int(time.time() * 1000)}"
            
            # If it's a CORE intent, we make space if needed (simulated eviction)
            if priority == IntentPriority.CORE:
                self._ensure_space(size)
            
            block = ContextBlock(id=bid, content=content, priority=priority)
            self._registry[bid] = block
            self._current_load += size
            logger.debug(f"Registered intent [{priority.name}]: {bid}")
            return bid
            
        except Exception as e:
            logger.error(f"Failed to register intent: {e}")
            raise ContextWindowError(f"Registration failed: {e}")

    def _ensure_space(self, required: int) -> None:
        """
        Internal helper to evict lowest-priority items if capacity is exceeded.
        CORE items are never evicted.
        """
        if self._current_load + required <= self._max_tokens:
            return

        # Sort by priority (descending) then relevance (ascending) for eviction
        # Tactical (2) > Strategic (1) > Core (0) - We want to evict Tactical first
        candidates = [
            b for b in self._registry.values() 
            if b.priority != IntentPriority.CORE
        ]
        
        # Sort: Lowest relevance first
        candidates.sort(key=lambda x: x.relevance_score)
        
        for block in candidates:
            if self._current_load + required <= self._max_tokens:
                break
            
            self._evict_block(block.id)

    def _evict_block(self, block_id: str) -> None:
        """Removes a block from the registry."""
        if block_id in self._registry:
            block = self._registry.pop(block_id)
            size = len(str(block.content))
            self._current_load -= size
            logger.info(f"Evicted block {block_id} to free space.")

    def validate_action(self, action_payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates a proposed action against CORE intents.
        
        This is the key function for 'Cognitive Self-Consistency'. It simulates
        a check (e.g., using an external LLM or rule engine) to ensure the action
        doesn't conflict with anchored values.
        
        Args:
            action_payload: Dictionary containing the proposed action or code.
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        # 1. Extract Core Anchors
        core_intents = [
            block.content for block in self._registry.values() 
            if block.priority == IntentPriority.CORE
        ]
        
        if not core_intents:
            return True, "No core constraints defined."

        # 2. Simulation of Consistency Check
        # In a real AGI system, this would involve an embedding space check or 
        # a logical inference call.
        action_desc = action_payload.get('description', '')
        action_code = action_payload.get('code', '')
        
        logger.info(f"Validating action against {len(core_intents)} core intents...")
        
        # Mock Logic: Check if action explicitly violates a keyword rule
        # Example: Core intent says "No global variables", action introduces one.
        for intent in core_intents:
            if isinstance(intent, dict):
                rule = intent.get('rule', '')
                # Naive contradiction check for demonstration
                if "No Obfuscation" in rule and "lambda:" in action_code and ":" in action_code:
                    return False, f"Violation of Core Intent: '{rule}'. Code appears obfuscated."
                if "Consistent Style" in rule and "camelCase" in action_code:
                     # Imagine we expect snake_case based on context
                     return False, f"Style Inconsistency: Expected snake_case, found camelCase."

        return True, "Action is consistent with core intents."

    def update_window(self) -> None:
        """
        Advances the window state. 
        Applies decay to non-core contexts and cleans up obsolete data.
        """
        logger.debug("Updating context window state...")
        obsolete_ids = []
        
        for bid, block in self._registry.items():
            if block.priority != IntentPriority.CORE:
                block.decay(self._decay_factor)
                if block.relevance_score < 0.1:
                    obsolete_ids.append(bid)
        
        for bid in obsolete_ids:
            self._evict_block(bid)
            logger.info(f"Context block {bid} decayed and removed.")

    def get_active_context(self) -> List[ContextBlock]:
        """Returns the current active context blocks."""
        return list(self._registry.values())


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup the Dynamic Context Window
    dcw = DynamicContextWindow(max_tokens=5000)
    
    # 2. Define Core Intents (The 'Anchors')
    # These should theoretically never be forgotten.
    core_style_rule = {
        "rule": "Consistent Style", 
        "details": "Use snake_case for variables."
    }
    core_safety_rule = {
        "rule": "No Obfuscation", 
        "details": "Do not generate unreadable lambda logic."
    }
    
    dcw.register_intent(core_style_rule, IntentPriority.CORE, "anchor_style")
    dcw.register_intent(core_safety_rule, IntentPriority.CORE, "anchor_safety")
    
    # 3. Add Tactical Context (Short-term memory)
    # This might be the immediate task or recent variable names.
    dcw.register_intent("Refactor function calculate_speed", IntentPriority.TACTICAL, "task_1")
    
    # 4. Simulate a long chain of tasks
    # We perform some updates, causing tactical context to decay
    dcw.update_window()
    dcw.update_window() # task_1 relevance drops
    
    # 5. Validate a generated code block (The Consistency Check)
    
    # Case A: Violation of Style
    bad_action_style = {
        "description": "Optimized loop",
        "code": "def run_fast(): speedValue = 10"  # camelCase violation
    }
    
    is_valid, reason = dcw.validate_action(bad_action_style)
    print(f"Action A Valid: {is_valid} | Reason: {reason}")
    
    # Case B: Valid Action
    good_action = {
        "description": "Optimized loop",
        "code": "def run_fast(): speed_value = 10"
    }
    
    is_valid, reason = dcw.validate_action(good_action)
    print(f"Action B Valid: {is_valid} | Reason: {reason}")