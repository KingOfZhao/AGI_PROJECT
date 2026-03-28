"""
Module: dynamic_skill_synthesis_engine
Description: This module implements a runtime architecture for dynamic skill synthesis.
             It breaks the limitations of fixed skill lists by treating atomic operations
             as instruction sets and compiling them into complex skill chains based on
             high-level abstract goals.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """Enumeration for skill execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SkillExecutionError(Exception):
    """Custom exception for errors during skill execution."""
    pass


class ValidationError(Exception):
    """Custom exception for input validation errors."""
    pass


@dataclass
class AtomicOperation:
    """
    Represents a basic, indivisible instruction.
    
    Attributes:
        name: The unique identifier of the operation.
        function: The callable function to execute.
        description: A brief description of what the operation does.
        cost: Estimated computational or resource cost.
    """
    name: str
    function: Any  # Callable
    description: str = ""
    cost: float = 1.0


@dataclass
class ExecutionResult:
    """
    Standardized output format for operation execution.
    
    Attributes:
        status: The completion status.
        output: The data returned by the operation.
        metrics: Performance metrics (duration, resource usage).
        error_message: Details if the execution failed.
    """
    status: SkillStatus
    output: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None


class AtomicSkillRegistry:
    """
    A registry holding all available atomic operations (the instruction set).
    """
    def __init__(self):
        self._operations: Dict[str, AtomicOperation] = {}
        self._load_default_operations()

    def _load_default_operations(self) -> None:
        """Load basic hard-coded atomic operations."""
        self.register(AtomicOperation(
            name="search_web",
            function=self._op_search,
            description="Search the web for information"
        ))
        self.register(AtomicOperation(
            name="filter_data",
            function=self._op_filter,
            description="Filter data based on criteria"
        ))
        self.register(AtomicOperation(
            name="analyze_sentiment",
            function=self._op_sentiment,
            description="Analyze sentiment of text"
        ))
        self.register(AtomicOperation(
            name="format_report",
            function=self._op_format,
            description="Compile data into a report format"
        ))

    def register(self, operation: AtomicOperation) -> None:
        """Register a new atomic operation."""
        if not callable(operation.function):
            raise ValidationError(f"Operation {operation.name} must have a callable function.")
        self._operations[operation.name] = operation
        logger.info(f"Registered atomic operation: {operation.name}")

    def get(self, name: str) -> Optional[AtomicOperation]:
        """Retrieve an operation by name."""
        return self._operations.get(name)

    # Mock implementations of atomic functions
    @staticmethod
    def _op_search(context: Dict) -> Dict:
        query = context.get("query", "N/A")
        logger.info(f"Executing Atomic: Searching for '{query}'...")
        time.sleep(0.2) # Simulate work
        return {"results": [f"Result for {query} - Item 1", f"Result for {query} - Item 2"]}

    @staticmethod
    def _op_filter(context: Dict) -> Dict:
        data = context.get("data", [])
        logger.info(f"Executing Atomic: Filtering {len(data)} items...")
        time.sleep(0.1)
        return {"filtered_data": [d for d in data if "Item 1" in d]}

    @staticmethod
    def _op_sentiment(context: Dict) -> Dict:
        text = context.get("text", "")
        logger.info("Executing Atomic: Analyzing sentiment...")
        time.sleep(0.1)
        return {"sentiment_score": 0.85}

    @staticmethod
    def _op_format(context: Dict) -> Dict:
        content = context.get("content", {})
        logger.info("Executing Atomic: Formatting report...")
        return {"report": f"FINAL REPORT: {json.dumps(content)}"}


class DynamicSkillEngine:
    """
    The core engine responsible for compiling and executing skill chains.
    """

    def __init__(self, registry: AtomicSkillRegistry):
        self.registry = registry
        self.context_memory: Dict[str, Any] = {}

    def _validate_goal(self, goal: str) -> None:
        """Validates the input goal string."""
        if not goal or not isinstance(goal, str):
            raise ValidationError("Goal must be a non-empty string.")
        if len(goal) > 1000:
            raise ValidationError("Goal description exceeds maximum length.")

    def plan_skill_chain(self, high_level_goal: str) -> List[str]:
        """
        Simulates the LLM's planning process to generate a skill chain.
        
        In a real AGI system, this function would call an LLM to analyze the goal
        and select atomic operations. Here we simulate logic mapping.
        
        Args:
            high_level_goal: The abstract objective (e.g., 'Market Research').
            
        Returns:
            A list of atomic operation names representing the execution flow.
        """
        self._validate_goal(high_level_goal)
        logger.info(f"Planning skill chain for goal: '{high_level_goal}'")

        # Simulated "Intelligence" logic
        chain = []
        if "research" in high_level_goal.lower() or "market" in high_level_goal.lower():
            chain = ["search_web", "filter_data", "analyze_sentiment", "format_report"]
        elif "quick check" in high_level_goal.lower():
            chain = ["search_web", "format_report"]
        else:
            # Default generic flow
            chain = ["search_web", "format_report"]
            
        logger.info(f"Compiled Chain: {' -> '.join(chain)}")
        return chain

    def execute_atomic(self, op_name: str, input_context: Dict[str, Any]) -> ExecutionResult:
        """
        Safely executes a single atomic operation.
        
        Args:
            op_name: Name of the operation to execute.
            input_context: Data dictionary passed to the operation.
            
        Returns:
            ExecutionResult object containing status and output.
        """
        operation = self.registry.get(op_name)
        if not operation:
            return ExecutionResult(
                status=SkillStatus.FAILED,
                error_message=f"Atomic operation '{op_name}' not found."
            )

        start_time = time.time()
        try:
            result_data = operation.function(input_context)
            duration = time.time() - start_time
            
            return ExecutionResult(
                status=SkillStatus.SUCCESS,
                output=result_data,
                metrics={"duration_sec": duration, "cost": operation.cost}
            )
        except Exception as e:
            logger.error(f"Error executing {op_name}: {str(e)}")
            return ExecutionResult(
                status=SkillStatus.FAILED,
                error_message=str(e),
                metrics={"duration_sec": time.time() - start_time}
            )

    def run_dynamic_skill(self, goal: str, initial_data: Optional[Dict] = None) -> Dict:
        """
        Main entry point. Generates and executes a temporary skill chain for the goal.
        
        Args:
            goal: The high-level abstract goal.
            initial_data: Optional starting data context.
            
        Returns:
            A dictionary containing the final result and execution trace.
            
        Example:
            >>> engine = DynamicSkillEngine(AtomicSkillRegistry())
            >>> result = engine.run_dynamic_skill("Market Research", {"query": "AI trends 2024"})
            >>> print(result["status"])
        """
        if initial_data is None:
            initial_data = {}
            
        self.context_memory = initial_data.copy()
        execution_trace = []
        
        # 1. Compile (Plan)
        try:
            skill_chain = self.plan_skill_chain(goal)
        except ValidationError as e:
            return {"status": "validation_error", "message": str(e)}

        # 2. Execute (Run)
        total_cost = 0.0
        for step_name in skill_chain:
            # Prepare context for the next step (chaining data)
            step_result = self.execute_atomic(step_name, self.context_memory)
            execution_trace.append({
                "step": step_name,
                "status": step_result.status.value,
                "metrics": step_result.metrics
            })
            
            if step_result.status == SkillStatus.FAILED:
                return {
                    "status": "failed",
                    "failed_at": step_name,
                    "error": step_result.error_message,
                    "trace": execution_trace
                }
            
            # Update memory with new outputs for the next step
            self.context_memory.update(step_result.output)
            total_cost += step_result.metrics.get("cost", 0)

        return {
            "status": "completed",
            "final_output": self.context_memory,
            "total_cost": total_cost,
            "trace": execution_trace
        }


def main():
    """
    Usage Example.
    """
    # Initialize System
    registry = AtomicSkillRegistry()
    engine = DynamicSkillEngine(registry)

    # Define High-Level Goal
    goal = "Conduct a market research analysis"
    inputs = {"query": "Latest Quantum Computing Breakthroughs"}

    print(f"--- Initiating Dynamic Skill for Goal: {goal} ---")
    
    # Execute
    result = engine.run_dynamic_skill(goal, inputs)
    
    # Output Results
    print("\n--- Execution Trace ---")
    for step in result.get("trace", []):
        print(f"Step: {step['step']:<20} | Status: {step['status']:<10} | Time: {step['metrics']['duration_sec']:.4f}s")
    
    print("\n--- Final Output ---")
    if result["status"] == "completed":
        print(json.dumps(result["final_output"], indent=2))
    else:
        print("Execution Failed:", result.get("error"))

if __name__ == "__main__":
    main()