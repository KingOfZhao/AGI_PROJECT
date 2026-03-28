"""
Module: cognitive_to_todo_scheduler
Description: AGI Skill - [Human-Computer Symbiosis Output]
Translates complex 'Cognitive Network' graph states into linear,
executable TODO-Lists based on real-time human state assessment.
"""

import logging
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveScheduler")

@dataclass(order=True)
class CognitiveNode:
    """
    Represents a node in the Cognitive Network (Graph).
    Sorted priority is handled by the scheduler logic, 
    but we can define default comparison behavior here if needed.
    """
    node_id: str
    content: str
    node_type: str  # e.g., 'hypothesis', 'data_gap', 'action_item'
    urgency: float = 0.0  # 0.0 to 1.0
    difficulty: float = 0.5  # 0.0 (easy) to 1.0 (hard)
    dependencies: List[str] = field(default_factory=list)
    is_completed: bool = False

    def __post_init__(self):
        if not 0.0 <= self.urgency <= 1.0:
            raise ValueError(f"Urgency must be between 0 and 1. Got: {self.urgency}")
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(f"Difficulty must be between 0 and 1. Got: {self.difficulty}")

@dataclass
class HumanState:
    """
    Represents the current state of the human operator.
    """
    user_id: str
    energy_level: float  # 0.0 (exhausted) to 1.0 (fully energized)
    skill_level: float   # 0.0 (novice) to 1.0 (expert)
    current_focus: Optional[str] = None

    def __post_init__(self):
        if not 0.0 <= self.energy_level <= 1.0:
            raise ValueError("Energy level out of bounds.")
        if not 0.0 <= self.skill_level <= 1.0:
            raise ValueError("Skill level out of bounds.")

@dataclass
class TODOItem:
    """
    The output structure for the human operator.
    """
    task_id: str
    instruction: str
    estimated_difficulty: str
    reason: str
    priority_score: float

class CognitiveScheduler:
    """
    A scheduling engine that bridges the gap between AGI graph states and human linear execution.
    
    Input Format:
        - cognitive_graph: Dict[str, CognitiveNode] representing the AGI's internal state.
        - human_state: HumanState object representing the operator's status.
    Output Format:
        - List[TODOItem]: A linear, prioritized list of instructions.
    """

    def __init__(self, cognitive_graph: Dict[str, CognitiveNode]):
        self.cognitive_graph = cognitive_graph
        logger.info(f"Scheduler initialized with {len(cognitive_graph)} nodes.")

    def _calculate_compatibility_score(self, node: CognitiveNode, human: HumanState) -> float:
        """
        [Helper] Calculates a fitness score between a Task Node and Human State.
        
        Formula Logic:
        - Base Score: Node Urgency.
        - Energy Filter: Penalize tasks requiring more energy than available.
        - Skill Match: Reward tasks matching skill level (Flow channel).
        
        Returns:
            float: Compatibility score (higher is better).
        """
        # Energy Check: If task difficulty > energy, heavy penalty, but allow low energy tasks.
        energy_factor = 1.0
        if node.difficulty > human.energy_level:
            # Penalize based on the deficit
            deficit = node.difficulty - human.energy_level
            energy_factor = max(0.1, 1.0 - deficit * 2) # Linear penalty

        # Skill Match: Best if skill matches difficulty +/- 0.2
        skill_delta = abs(node.difficulty - human.skill_level)
        skill_factor = 1.0 / (1.0 + skill_delta) # Inverse distance

        # Final Score Calculation
        score = (node.urgency * 0.5) + (energy_factor * 0.3) + (skill_factor * 0.2)
        
        logger.debug(f"Score calc for {node.node_id}: Urgency={node.urgency}, "
                     f"EnergyFactor={energy_factor:.2f}, SkillFactor={skill_factor:.2f} -> Total={score:.3f}")
        return score

    def _check_dependencies(self, node: CognitiveNode) -> bool:
        """
        [Helper] Verifies if all dependencies of a node are met.
        """
        for dep_id in node.dependencies:
            if dep_id in self.cognitive_graph:
                if not self.cognitive_graph[dep_id].is_completed:
                    return False
            else:
                logger.warning(f"Missing dependency {dep_id} for node {node.node_id}")
                return False
        return True

    def generate_linear_todo_list(self, human_state: HumanState, limit: int = 5) -> List[TODOItem]:
        """
        [Core] Generates a prioritized TODO list from the cognitive network.
        
        Args:
            human_state (HumanState): The current state of the human operator.
            limit (int): Maximum number of items to return.
            
        Returns:
            List[TODOItem]: Sorted list of executable tasks.
        """
        logger.info(f"Generating TODO list for user {human_state.user_id} "
                    f"(Energy: {human_state.energy_level}, Skill: {human_state.skill_level})")
        
        candidates = []

        for node_id, node in self.cognitive_graph.items():
            # Filter: Skip completed nodes
            if node.is_completed:
                continue
            
            # Filter: Check Dependencies (Graph Topology)
            if not self._check_dependencies(node):
                continue
            
            # Score the node
            score = self._calculate_compatibility_score(node, human_state)
            
            # Use a heap to keep top items (max-heap simulation by negating score)
            heapq.heappush(candidates, (-score, node))

        result_set = []
        for _ in range(min(limit, len(candidates))):
            neg_score, node = heapq.heappop(candidates)
            score = -neg_score
            
            # Map difficulty to human-readable string
            if node.difficulty < 0.3:
                diff_str = "Low"
            elif node.difficulty < 0.7:
                diff_str = "Medium"
            else:
                diff_str = "High"

            # Construct Instruction
            instruction = f"[{node.node_type.upper()}] {node.content}"
            reason = (f"Matched to your current profile (Score: {score:.2f}). "
                      f"System Urgency: {node.urgency:.2f}")

            todo = TODOItem(
                task_id=node.node_id,
                instruction=instruction,
                estimated_difficulty=diff_str,
                reason=reason,
                priority_score=score
            )
            result_set.append(todo)

        logger.info(f"Generated {len(result_set)} actionable tasks.")
        return result_set

    def execute_task_callback(self, task_id: str, success: bool) -> None:
        """
        [Core] Updates the cognitive network based on human feedback.
        
        Args:
            task_id: The ID of the executed task.
            success: Whether the human successfully completed the task.
        """
        if task_id not in self.cognitive_graph:
            logger.error(f"Callback failed: Task ID {task_id} not found.")
            return

        node = self.cognitive_graph[task_id]
        if success:
            node.is_completed = True
            # In a real AGI system, this would trigger graph propagation
            logger.info(f"Node {task_id} marked as COMPLETED. Graph state updated.")
        else:
            # If failed, maybe lower urgency or flag for review
            node.urgency *= 0.8
            logger.warning(f"Node {task_id} execution FAILED. Urgency degraded to {node.urgency}")

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Mock Data (Cognitive Network)
    graph_data = {
        "node_1": CognitiveNode("node_1", "Verify dataset integrity", "action", urgency=0.9, difficulty=0.2),
        "node_2": CognitiveNode("node_2", "Analyze anomaly in sector 7G", "analysis", urgency=0.8, difficulty=0.9, dependencies=["node_1"]),
        "node_3": CognitiveNode("node_3", "Draft report on findings", "reporting", urgency=0.5, difficulty=0.6, dependencies=["node_2"]),
        "node_4": CognitiveNode("node_4", "Respond to urgent query", "communication", urgency=0.99, difficulty=0.1),
    }

    # 2. Initialize Scheduler
    scheduler = CognitiveScheduler(graph_data)

    # 3. Define Human State (Tired Junior Engineer)
    tired_junior = HumanState("user_001", energy_level=0.3, skill_level=0.4)
    
    # 4. Generate TODO List
    print("\n--- SCENARIO 1: Tired Junior Operator ---")
    todos = scheduler.generate_linear_todo_list(tired_junior)
    for item in todos:
        print(f"[{item.estimated_difficulty}] {item.instruction} (Score: {item.priority_score:.2f})")

    # 5. Simulate Completion and Update
    print("\n--- SCENARIO 2: Completing Task & State Change ---")
    scheduler.execute_task_callback("node_1", success=True) # Complete the dependency
    
    # Operator rested a bit
    rested_mid_level = HumanState("user_001", energy_level=0.7, skill_level=0.6)
    
    todos_updated = scheduler.generate_linear_todo_list(rested_mid_level)
    for item in todos_updated:
        print(f"[{item.estimated_difficulty}] {item.instruction} (Score: {item.priority_score:.2f})")