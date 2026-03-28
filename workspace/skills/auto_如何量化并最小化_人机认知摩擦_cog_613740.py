"""
Module: auto_how_to_quantify_and_minimize_cognitive_friction_cog_613740

This module provides a computational model to quantify and minimize 'Cognitive Friction'
in Human-Computer Interaction (HCI), specifically focusing on AI-generated actionable lists.
It calculates the cognitive load of a task list and applies dimensionality reduction
(simplification and splitting) to ensure the output fits within a single human attention unit.

Author: Senior Python Engineer (AGI System)
Domain: Cognitive Science / HCI
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
DEFAULT_ATTENTION_SPAN_UNITS = 120.0  # Represents "N" cognitive units (abstract scale)
MAX_ITEM_LENGTH_CHARS = 80
PENALTY_ABSTRACT_CONCEPT = 1.5  # Multiplier for vague terms
PENALTY_DEPENDENCY = 0.5  # Additive cost per dependency

@dataclass
class ActionItem:
    """
    Represents a single node in an actionable list.
    
    Attributes:
        id: Unique identifier for the action.
        content: The textual description of the action.
        complexity: A base complexity score (1-10).
        dependencies: List of IDs that this action depends on.
        is_abstract: Flag indicating if the concept requires deep domain knowledge.
    """
    id: str
    content: str
    complexity: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    is_abstract: bool = False

    def __post_init__(self):
        """Validate data after initialization."""
        if not self.id:
            raise ValueError("ActionItem must have an ID.")
        if self.complexity < 0:
            logger.warning(f"Negative complexity for {self.id}, resetting to 0.")
            self.complexity = 0.0

@dataclass
class CognitiveLoadReport:
    """
    Contains the results of the cognitive load analysis.
    """
    total_load: float
    load_per_item: Dict[str, float]
    is_within_attention_span: bool
    reduction_applied: bool
    suggestions: List[str]

class CognitiveFrictionMinimizer:
    """
    A class to model, predict, and minimize cognitive friction in human-AI symbiosis.
    """
    
    def __init__(self, attention_span_threshold: float = DEFAULT_ATTENTION_SPAN_UNITS):
        """
        Initialize the minimizer with a specific attention span threshold.
        
        Args:
            attention_span_threshold: The maximum cognitive load a user can handle 
                                      in one 'unit' of attention.
        """
        self.threshold = attention_span_threshold
        logger.info(f"CognitiveFrictionMinimizer initialized with threshold: {self.threshold}")

    def _calculate_item_load(self, item: ActionItem) -> float:
        """
        [Helper] Calculate the cognitive load of a single ActionItem.
        
        Logic:
        Load = BaseComplexity * LengthFactor * AbstractionPenalty + DependencyCost
        
        Args:
            item: The ActionItem to evaluate.
            
        Returns:
            float: The calculated cognitive load score.
        """
        # 1. Length Factor: Logarithmic scaling of text length
        len_factor = 1.0 + math.log10(max(len(item.content), 1) / 10.0)
        
        # 2. Complexity Base
        base_load = item.complexity
        
        # 3. Abstraction Penalty
        if item.is_abstract:
            base_load *= PENALTY_ABSTRACT_CONCEPT
            
        # 4. Dependency Cost (Linear)
        dep_cost = len(item.dependencies) * PENALTY_DEPENDENCY
        
        total_item_load = (base_load * len_factor) + dep_cost
        
        # Boundary check
        return max(0.0, total_item_load)

    def predict_cognitive_load(self, items: List[ActionItem]) -> CognitiveLoadReport:
        """
        [Core 1] Predicts the total cognitive load of a list of actions.
        
        Args:
            items: List of ActionItem objects.
            
        Returns:
            CognitiveLoadReport: Detailed analysis of the load.
        """
        if not items:
            return CognitiveLoadReport(0.0, {}, True, False, ["List is empty."])

        load_map: Dict[str, float] = {}
        total_load = 0.0
        
        logger.debug(f"Analyzing load for {len(items)} items...")
        
        for item in items:
            try:
                load = self._calculate_item_load(item)
                load_map[item.id] = load
                total_load += load
            except Exception as e:
                logger.error(f"Error calculating load for item {item.id}: {e}")
                load_map[item.id] = -1.0 # Error marker

        is_ok = total_load <= self.threshold
        suggestions = [] if is_ok else ["Consider reducing list complexity."]
        
        return CognitiveLoadReport(
            total_load=round(total_load, 2),
            load_per_item=load_map,
            is_within_attention_span=is_ok,
            reduction_applied=False,
            suggestions=suggestions
        )

    def minimize_friction(self, items: List[ActionItem], strategy: str = "truncate") -> Tuple[List[ActionItem], CognitiveLoadReport]:
        """
        [Core 2] Attempts to minimize cognitive friction by reducing the list complexity
        or splitting it, ensuring it fits within the attention span.
        
        Args:
            items: The original list of ActionItems.
            strategy: Reduction strategy ('truncate', 'simplify', 'essential').
            
        Returns:
            Tuple[List[ActionItem], CognitiveLoadReport]: The optimized list and the report.
        """
        logger.info(f"Starting friction minimization using strategy: {strategy}")
        
        # 1. Initial Assessment
        report = self.predict_cognitive_load(items)
        
        if report.is_within_attention_span:
            logger.info("List already within acceptable cognitive limits.")
            return items, report

        # 2. Apply Reduction Strategy
        optimized_items: List[ActionItem] = []
        
        if strategy == "truncate":
            # Simple truncation based on load accumulation
            current_load = 0.0
            for item in items:
                item_load = self._calculate_item_load(item)
                if current_load + item_load <= self.threshold:
                    optimized_items.append(item)
                    current_load += item_load
                else:
                    # Stop adding items once threshold is reached
                    logger.debug(f"Threshold reached at item {item.id}. Truncating.")
                    break
                    
        elif strategy == "simplify":
            # Try to reduce complexity and abstractness while keeping all items
            # (If possible within a hard limit, otherwise fall back to truncation)
            for item in items:
                if item.is_abstract:
                    # Simulate de-abstraction
                    new_item = ActionItem(
                        id=item.id, 
                        content=item.content, 
                        complexity=item.complexity * 0.8, # Reduce complexity assumption
                        is_abstract=False
                    )
                    optimized_items.append(new_item)
                else:
                    optimized_items.append(item)
            
            # Check if simplification was enough
            new_report = self.predict_cognitive_load(optimized_items)
            if not new_report.is_within_attention_span:
                # Recurse with truncate if simplification failed
                return self.minimize_friction(optimized_items, strategy="truncate")
                
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # 3. Final Report
        final_report = self.predict_cognitive_load(optimized_items)
        final_report.reduction_applied = True
        final_report.suggestions.append(f"Original list reduced using '{strategy}' strategy.")
        
        logger.info(f"Minimization complete. Load reduced from {report.total_load} to {final_report.total_load}")
        
        return optimized_items, final_report

# --- Usage Example ---
if __name__ == "__main__":
    # Example Scenario: AI generates a checklist for a human to verify a system deployment
    
    # 1. Define raw tasks (High friction)
    raw_tasks = [
        ActionItem("task_1", "Verify the integrity of the core database schema migrations.", complexity=5.0, is_abstract=True),
        ActionItem("task_2", "Check logs.", complexity=2.0, dependencies=["task_1"]),
        ActionItem("task_3", "Ensure all microservices are running and health checks return 200 OK status codes.", complexity=8.0, dependencies=["task_1", "task_2"]),
        ActionItem("task_4", "Review security group settings on the cloud provider console.", complexity=6.0, is_abstract=True),
        ActionItem("task_5", "Validate user feedback loop.", complexity=4.0, is_abstract=True)
    ]

    # 2. Initialize Minimizer
    # Setting a low threshold to force reduction
    minimizer = CognitiveFrictionMinimizer(attention_span_threshold=15.0)

    # 3. Analyze
    print("--- Initial Analysis ---")
    initial_report = minimizer.predict_cognitive_load(raw_tasks)
    print(f"Total Load: {initial_report.total_load}")
    print(f"Within Limit: {initial_report.is_within_attention_span}")

    # 4. Minimize
    print("\n--- Minimizing Friction ---")
    optimized_tasks, final_report = minimizer.minimize_friction(raw_tasks, strategy="simplify")

    print(f"Final Load: {final_report.total_load}")
    print(f"Tasks Retained: {len(optimized_tasks)}")
    print("Suggestions:", final_report.suggestions)
    
    # Output the optimized list
    for t in optimized_tasks:
        print(f"- [{t.id}] {t.content}")