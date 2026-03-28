"""
Module: cognitive_roi_resource_allocator.py

This module implements a dynamic resource allocation mechanism based on 'Cognitive ROI'
(Return on Investment) for AGI systems. It is designed to optimize computational
resource usage by evaluating the potential value and uncertainty of reasoning paths.

The core philosophy is to prune paths with high uncertainty and low value (speculative
or unfalsifiable) and concentrate resources on paths with high value and high
actionability (falsifiable/practical).

Classes:
    CognitiveBudgetExceeded: Custom exception for budget limits.
    InferenceTask: Data class representing a reasoning sub-task.
    CognitiveROIManager: The core engine for resource allocation.
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveROI")


class CognitiveBudgetExceeded(Exception):
    """Raised when the allocated computational budget for a cycle is exceeded."""
    pass


class TaskCategory(Enum):
    """Enumeration of possible inference task categories."""
    CODE_OPTIMIZATION = 1
    LOGICAL_REASONING = 2
    CREATIVE_GENERATION = 3
    SPECULATIVE_METAPHYSICS = 4
    SYSTEM_MONITORING = 5


@dataclass
class InferenceTask:
    """
    Represents a single sub-problem or reasoning path in the AGI system.

    Attributes:
        id: Unique identifier for the task.
        description: Human-readable description of the task.
        category: The type of reasoning involved.
        base_value: Intrinsic value of solving this task (0.0 to 1.0).
        uncertainty: Estimated uncertainty level (0.0 to 1.0). High means hard to verify.
        estimated_cycles: Estimated computational cycles required.
        is_falsifiable: Whether the result can be empirically tested or verified.
        allocated_cycles: Actual cycles allocated by the manager (default 0).
    """
    id: str
    description: str
    category: TaskCategory
    base_value: float
    uncertainty: float
    estimated_cycles: int
    is_falsifiable: bool
    allocated_cycles: int = 0

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.base_value <= 1.0:
            raise ValueError(f"base_value must be between 0 and 1, got {self.base_value}")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError(f"uncertainty must be between 0 and 1, got {self.uncertainty}")
        if self.estimated_cycles < 0:
            raise ValueError("estimated_cycles cannot be negative")


class CognitiveROIManager:
    """
    Manages the dynamic allocation of compute resources based on Cognitive ROI.

    The manager evaluates tasks based on a utility function that penalizes
    high uncertainty (unless valuable and falsifiable) and rewards actionability.

    Usage Example:
        >>> manager = CognitiveROIManager(total_budget=10000)
        >>> tasks = [
        ...     InferenceTask("t1", "Optimize DB query", TaskCategory.CODE_OPTIMIZATION, 0.9, 0.1, 500, True),
        ...     InferenceTask("t2", "Ponder color of cosmos", TaskCategory.SPECULATIVE_METAPHYSICS, 0.1, 0.99, 2000, False)
        ... ]
        >>> allocated_tasks = manager.allocate_resources(tasks)
        >>> print(allocated_tasks[0].allocated_cycles > allocated_tasks[1].allocated_cycles)
        True
    """

    def __init__(self, total_budget: int, prune_threshold: float = 0.05):
        """
        Initialize the ROI Manager.

        Args:
            total_budget: Total available computational cycles per step.
            prune_threshold: Utility score below which tasks are completely dropped.
        """
        self.total_budget = total_budget
        self.prune_threshold = prune_threshold
        self._audit_log: List[Dict] = []

    def _calculate_utility(self, task: InferenceTask) -> float:
        """
        [Core Function 1]
        Calculate the 'Cognitive ROI' score for a given task.

        Formula logic:
        - Raw Value = base_value
        - Uncertainty Penalty: Reduces value if uncertainty is high AND falsifiability is low.
        - Actionability Bonus: Increases value if the task is falsifiable (testable).

        Args:
            task: The inference task to evaluate.

        Returns:
            A float score representing the priority/weight of the task.
        """
        # Validate inputs (redundant safety check)
        uncertainty = max(0.0, min(1.0, task.uncertainty))
        value = max(0.0, min(1.0, task.base_value))

        # Uncertainty penalty: If it's not falsifiable, high uncertainty is bad.
        # If it is falsifiable, we tolerate uncertainty (exploration).
        if not task.is_falsifiable:
            # Penalize speculative high uncertainty heavily
            utility = value * (1.0 - uncertainty)
        else:
            # For falsifiable tasks, uncertainty represents an opportunity to learn
            # (Information Gain), but we still value low uncertainty for efficiency
            utility = value * (0.5 + 0.5 * (1.0 - uncertainty))

        # Efficiency factor: Prefer tasks that require fewer cycles for the same value
        # We add a small epsilon to avoid division by zero
        cycles = max(1, task.estimated_cycles)
        efficiency_factor = 1000.0 / cycles  # Normalized around 1000 cycles

        final_score = utility * efficiency_factor
        
        logger.debug(f"Task {task.id} utility calc: {final_score:.4f} (Val:{value}, Unc:{uncertainty}, Fals:{task.is_falsifiable})")
        return final_score

    def allocate_resources(self, tasks: List[InferenceTask]) -> List[InferenceTask]:
        """
        [Core Function 2]
        Allocates computational cycles to tasks based on their calculated utility.

        This process involves:
        1. Calculating utility for all tasks.
        2. Pruning tasks with utility below the threshold.
        3. Distributing the total budget proportionally to utility scores.

        Args:
            tasks: A list of InferenceTask objects requesting resources.

        Returns:
            A list of tasks with updated `allocated_cycles`. Tasks that were
            pruned will have 0 allocated cycles.

        Raises:
            CognitiveBudgetExceeded: If internal logic fails to respect budget constraints.
        """
        if not tasks:
            return []

        logger.info(f"Starting allocation for {len(tasks)} tasks. Budget: {self.total_budget}")
        
        # Step 1: Evaluate and Filter
        valid_tasks = []
        for task in tasks:
            score = self._calculate_utility(task)
            if score >= self.prune_threshold:
                valid_tasks.append((task, score))
            else:
                task.allocated_cycles = 0
                logger.info(f"Pruned task '{task.id}': Score {score:.4f} < Threshold {self.prune_threshold}")
                self._log_decision(task, score, pruned=True)

        if not valid_tasks:
            logger.warning("All tasks pruned due to low utility.")
            return tasks

        # Step 2: Normalize Scores for Distribution
        total_score = sum(score for _, score in valid_tasks)
        if total_score <= 0:
            logger.warning("Total utility score is 0. Distributing budget equally.")
            total_score = len(valid_tasks) # Avoid division by zero, fallback to equal dist

        allocated_total = 0
        
        # Step 3: Resource Distribution
        # We iterate and allocate based on weight, ensuring we don't exceed budget
        final_tasks = []
        for task, score in valid_tasks:
            weight = score / total_score
            raw_allocation = int(self.total_budget * weight)
            
            # Boundary Check: Allocate at least 1 cycle if valid, but cap at estimated need
            # (We don't want to waste budget, but we also don't over-allocate beyond what was asked)
            allocation = min(raw_allocation, task.estimated_cycles)
            
            # Ensure we don't exceed remaining budget (safety check)
            if allocated_total + allocation > self.total_budget:
                allocation = self.total_budget - allocated_total

            if allocation < 0:
                allocation = 0

            task.allocated_cycles = allocation
            allocated_total += allocation
            final_tasks.append(task)
            self._log_decision(task, score, pruned=False, allocation=allocation)

        logger.info(f"Allocation complete. Distributed {allocated_total}/{self.total_budget} cycles.")
        return tasks

    def _log_decision(self, task: InferenceTask, score: float, pruned: bool, allocation: int = 0) -> None:
        """
        [Auxiliary Function]
        Records the allocation decision for audit and debugging purposes.
        """
        entry = {
            "task_id": task.id,
            "utility_score": round(score, 4),
            "pruned": pruned,
            "allocation": allocation,
            "category": task.category.name
        }
        self._audit_log.append(entry)


def run_simulation():
    """Demonstrates the Cognitive ROI system in action."""
    print("--- Initializing Cognitive ROI Simulation ---")
    
    # Initialize Manager with 5000 compute cycles budget
    manager = CognitiveROIManager(total_budget=5000, prune_threshold=0.1)
    
    # Define a mix of tasks
    tasks = [
        InferenceTask(
            id="T001",
            description="Optimize main loop latency",
            category=TaskCategory.CODE_OPTIMIZATION,
            base_value=0.9,      # High Value
            uncertainty=0.2,     # Low Uncertainty
            estimated_cycles=1500,
            is_falsifiable=True  # Can be benchmarked
        ),
        InferenceTask(
            id="T002",
            description="Analyze cosmic background color intent",
            category=TaskCategory.SPECULATIVE_METAPHYSICS,
            base_value=0.1,      # Low Value
            uncertainty=0.99,    # High Uncertainty
            estimated_cycles=3000,
            is_falsifiable=False # Not provable
        ),
        InferenceTask(
            id="T003",
            description="Fix critical memory leak in module X",
            category=TaskCategory.CODE_OPTIMIZATION,
            base_value=1.0,      # Critical Value
            uncertainty=0.1,     # Known solution exists
            estimated_cycles=800,
            is_falsifiable=True
        ),
        InferenceTask(
            id="T004",
            description="Generate creative name for variable",
            category=TaskCategory.CREATIVE_GENERATION,
            base_value=0.3,      # Low-Medium Value
            uncertainty=0.5,     # Subjective
            estimated_cycles=200,
            is_falsifiable=False # Subjective verification
        )
    ]

    # Run Allocation
    processed_tasks = manager.allocate_resources(tasks)

    # Display Results
    print("\n--- Allocation Results ---")
    for t in processed_tasks:
        status = "PRUNED" if t.allocated_cycles == 0 else "ACTIVE"
        print(f"ID: {t.id} | Status: {status} | Alloc: {t.allocated_cycles} / {t.estimated_cycles} | Desc: {t.description[:30]}...")
    
    print("\n--- Logic Summary ---")
    print("Task T001 (High Value/Low Unc): High allocation.")
    print("Task T002 (Low Value/High Unc): Pruned (Speculative).")
    print("Task T003 (Crit Value/Low Unc): Maximum priority.")
    print("Task T004 (Med Value/Med Unc):  Small residual allocation.")

if __name__ == "__main__":
    run_simulation()