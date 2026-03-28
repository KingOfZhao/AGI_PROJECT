"""
Attention-Anchored Task Decomposer Module

This module implements a cognitive-science-based task decomposition strategy.
It utilizes a 'Dynamic Granularity Adjustment' algorithm to break down complex
programming tasks into manageable steps. Crucially, it identifies 'High-Risk
Inference Nodes' (HRINs)—similar to distractors in logic puzzles—where LLMs
often hallucinate or fail. At these nodes, it automatically inserts 'Anchors'
(intermediate verification steps), simulating the human 'scratchpad' mechanism.

Version: 1.0.0
Author: Senior Python Engineer (AGI Systems)
License: MIT
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Enumeration of risk levels for inference nodes."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskNode:
    """
    Represents a single node in the task decomposition graph.
    
    Attributes:
        id: Unique identifier for the node.
        description: The natural language description of the task step.
        code_snippet: Optional Python code associated with the step.
        risk_level: Estimated risk of reasoning failure.
        dependencies: List of node IDs that must complete before this one.
        is_anchor: Boolean indicating if this is an auto-inserted verification step.
    """
    id: str
    description: str
    code_snippet: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    dependencies: List[str] = field(default_factory=list)
    is_anchor: bool = False


class AttentionAnchoredDecomposer:
    """
    Decomposes complex tasks into graphs of nodes with attention anchors.
    
    This class analyzes task descriptions and logical structures to determine
    where reasoning is most likely to fail (High-Risk Inference Nodes) and
    inserts verification steps (Anchors) to ensure correctness.
    """

    # Heuristics for detecting high-risk reasoning patterns
    _RISK_PATTERNS = {
        # Complex logic often involving nested quantifiers
        r'\b(if|else|elif|switch|case)\b.*\b(and|or|not)\b': RiskLevel.HIGH,
        # State mutation and side effects
        r'\b(update|delete|modify|mutate|global)\b': RiskLevel.HIGH,
        # Iteration logic (off-by-one errors, infinite loops)
        r'\b(for|while|loop|iterate|recursion)\b': RiskLevel.MEDIUM,
        # Resource handling (memory leaks, file locks)
        r'\b(open|close|alloc|free|socket|connect)\b': RiskLevel.CRITICAL,
        # Mathematical precision
        r'\b(float|double|precision|round|sqrt|power)\b': RiskLevel.MEDIUM,
        # External API calls
        r'\b(api|http|request|fetch|external)\b': RiskLevel.HIGH,
    }

    def __init__(self, max_decomposition_depth: int = 5):
        """
        Initialize the decomposer.
        
        Args:
            max_decomposition_depth: Maximum recursion depth for task splitting.
        """
        if not isinstance(max_decomposition_depth, int) or max_decomposition_depth < 1:
            raise ValueError("max_decomposition_depth must be a positive integer")
        self.max_depth = max_decomposition_depth
        logger.info(f"AttentionAnchoredDecomposer initialized with max_depth={max_decomposition_depth}")

    def _assess_node_risk(self, text: str) -> RiskLevel:
        """
        Internal helper to assess the risk level of a specific text segment.
        
        Args:
            text: The task description or logic snippet.
            
        Returns:
            The calculated RiskLevel.
        """
        if not text or not isinstance(text, str):
            return RiskLevel.LOW
            
        max_risk = RiskLevel.LOW
        for pattern, level in self._RISK_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                if level.value > max_risk.value:
                    max_risk = level
        return max_risk

    def _create_anchor_node(self, target_node: TaskNode) -> TaskNode:
        """
        Creates a verification anchor node for a given high-risk target.
        
        Args:
            target_node: The node that requires verification.
            
        Returns:
            A new TaskNode acting as the anchor.
        """
        anchor_desc = (
            f"VERIFY ANCHOR: Validate logic for '{target_node.description}'. "
            f"Ensure pre-conditions and post-conditions are met."
        )
        
        # Simple assertion-based verification snippet generation
        anchor_code = (
            f"# Verification Anchor for {target_node.id}\n"
            f"assert result is not None, 'Result should not be None'\n"
            f"print(f'[ANCHOR CHECK] {target_node.id} passed')\n"
        )
        
        return TaskNode(
            id=f"{target_node.id}_anchor",
            description=anchor_desc,
            code_snippet=anchor_code,
            risk_level=RiskLevel.LOW,
            dependencies=[target_node.id],
            is_anchor=True
        )

    def analyze_complexity(self, task_description: str) -> Dict[str, float]:
        """
        Analyzes the cognitive complexity of a task description.
        
        Args:
            task_description: The raw task text.
            
        Returns:
            A dictionary containing complexity metrics.
        """
        if not task_description:
            raise ValueError("Task description cannot be empty")
            
        # Count logical operators and distinct verbs as proxy for complexity
        logic_count = len(re.findall(r'\b(if|else|for|while|and|or)\b', task_description, re.I))
        length_factor = len(task_description.split()) / 10.0
        
        return {
            "logic_density": logic_count,
            "length_factor": length_factor,
            "overall_score": logic_count * 0.5 + length_factor
        }

    def decompose_task(self, task_description: str) -> List[TaskNode]:
        """
        Main entry point. Decomposes a task into steps with anchors.
        
        Args:
            task_description: The high-level description of the task.
            
        Returns:
            A list of TaskNodes representing the execution plan.
            
        Raises:
            ValueError: If input is invalid.
            RuntimeError: If decomposition fails unexpectedly.
        """
        try:
            logger.info(f"Starting decomposition for task: {task_description[:50]}...")
            
            # 1. Input Validation
            if not isinstance(task_description, str):
                raise TypeError("Task description must be a string")
            
            # 2. Initial Split (Simulation of semantic parsing)
            # In a real AGI system, this would use an LLM or semantic parser.
            # Here we simulate splitting by sentences or logical delimiters.
            raw_steps = re.split(r'[.;]\s*', task_description.strip())
            raw_steps = [s for s in raw_steps if len(s) > 5] # Filter noise
            
            if not raw_steps:
                return []

            nodes: List[TaskNode] = []
            node_map: Dict[str, TaskNode] = {}
            
            # 3. Node Generation and Risk Assessment
            for i, step_text in enumerate(raw_steps):
                node_id = f"step_{i:02d}"
                risk = self._assess_node_risk(step_text)
                
                node = TaskNode(
                    id=node_id,
                    description=step_text.strip(),
                    risk_level=risk,
                    dependencies=[f"step_{i-1:02d}"] if i > 0 else []
                )
                nodes.append(node)
                node_map[node_id] = node
                logger.debug(f"Generated node {node_id} with risk {risk.name}")

            # 4. Anchor Insertion Strategy (Attention Mechanism)
            # We insert anchors after CRITICAL or HIGH risk nodes to verify state.
            final_plan: List[TaskNode] = []
            
            for node in nodes:
                final_plan.append(node)
                
                # Dynamic Granularity Adjustment: Insert anchor if risk is high
                if node.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    anchor = self._create_anchor_node(node)
                    final_plan.append(anchor)
                    logger.info(f"Inserted Anchor {anchor.id} after {node.id}")

            return final_plan

        except Exception as e:
            logger.error(f"Decomposition failed: {str(e)}")
            raise RuntimeError(f"Decomposition failed: {str(e)}") from e


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Example complex task involving logic and iteration
    complex_task = (
        "Connect to the database API. "
        "Iterate over the user list. "
        "If the user is active and has a valid subscription, update their role. "
        "Finally, close the connection and log the results."
    )

    print(f"{'='*60}\nProcessing Task:\n{complex_task}\n{'='*60}")

    decomposer = AttentionAnchoredDecomposer()
    
    try:
        # Analyze complexity first
        metrics = decomposer.analyze_complexity(complex_task)
        print(f"Complexity Metrics: {metrics}\n")

        # Perform decomposition
        plan = decomposer.decompose_task(complex_task)

        print(f"Generated Plan ({len(plan)} steps):")
        print("-" * 40)
        
        for step in plan:
            prefix = "[ANCHOR]" if step.is_anchor else "[TASK]"
            risk_tag = f"({step.risk_level.name})"
            deps = f"deps: {step.dependencies}" if step.dependencies else "root"
            print(f"{prefix} {step.id} {risk_tag}: {step.description[:40]}...")
            print(f"       -> {deps}")
            
    except Exception as e:
        print(f"Error: {e}")