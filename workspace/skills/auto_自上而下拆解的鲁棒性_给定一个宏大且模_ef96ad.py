"""
Module: auto_robust_top_down_decomposition
Description: Implements an AGI skill for decomposing high-level goals into execution DAGs
             with dynamic adaptation to environmental resistances.

This system demonstrates robustness by detecting execution blocks (e.g., banned APIs)
and triggering a re-planning of the Directed Acyclic Graph (DAG) rather than retrying
failed operations indefinitely.
"""

import logging
import uuid
import time
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RobustPlanner")

class TaskStatus(Enum):
    """Enumeration of possible task states."""
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"  # Environmental resistance encountered
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskNode:
    """
    Represents a node in the execution DAG.
    
    Attributes:
        id: Unique identifier for the task.
        name: Human-readable name.
        action: The function to execute (simulated).
        dependencies: Set of TaskNode IDs that must complete before this runs.
        status: Current state of the task.
        retries: Number of attempts made.
        max_retries: Maximum allowed retries before marking as FAILED/BLOCKED.
    """
    id: str
    name: str
    action: Callable
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    max_retries: int = 1

    def __hash__(self):
        return hash(self.id)

@dataclass
class ExecutionDAG:
    """
    Container for the execution graph.
    """
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    goal: str = ""

    def add_task(self, task: TaskNode) -> None:
        """Adds a task to the DAG."""
        self.tasks[task.id] = task

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns tasks that are PENDING and have all dependencies COMPLETED."""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            all_deps_met = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if all_deps_met:
                ready.append(task)
        return ready

class RobustDecomposer:
    """
    Core class responsible for goal decomposition, execution, and re-planning.
    """

    def __init__(self):
        self.current_dag: Optional[ExecutionDAG] = None
        self.environment_state: Dict[str, Any] = {} # Simulates external world state

    def _generate_plan(self, goal: str, constraints: Dict[str, Any] = None) -> ExecutionDAG:
        """
        [Core Function 1]
        Decomposes a high-level goal into a specific DAG.
        
        In a real AGI system, this would use an LLM or a planning algorithm.
        Here, we simulate creating a standard e-commerce pipeline.
        
        Args:
            goal: The high-level objective string.
            constraints: Optional dictionary of constraints.
            
        Returns:
            ExecutionDAG: The initial plan.
        """
        logger.info(f"Generating plan for goal: '{goal}'")
        dag = ExecutionDAG(goal=goal)

        # Simulated Hierarchical Task Network (HTN) decomposition
        # Step 1: Market Research
        t1 = TaskNode(id="t1", name="Market Research", action=self._mock_action)
        
        # Step 2: Product Sourcing (Depends on Research)
        t2 = TaskNode(id="t2", name="Source Product", action=self._mock_action, dependencies={"t1"})
        
        # Step 3: Setup Payment Gateway (Depends on Research)
        # This is where we will inject the simulated 'environmental resistance'
        t3 = TaskNode(id="t3", name="Setup Payment API", action=self._mock_payment_setup, dependencies={"t1"})
        
        # Step 4: Launch Store (Depends on Sourcing & Payment)
        t4 = TaskNode(id="t4", name="Launch Store", action=self._mock_action, dependencies={"t2", "t3"})

        for t in [t1, t2, t3, t4]:
            dag.add_task(t)
            
        logger.info("Initial DAG generated with 4 nodes.")
        return dag

    def _detect_and_adapt(self, failed_task: TaskNode) -> ExecutionDAG:
        """
        [Core Function 2]
        Detects the root cause of failure and dynamically restructures the DAG.
        
        This function is triggered when a task hits a 'BLOCKED' state.
        It generates alternative pathways.
        """
        logger.warning(f"Adaptation triggered due to blocked task: {failed_task.name}")
        
        if "Payment" in failed_task.name:
            logger.info("Pivoting strategy: Switching from Payment API to Crypto/Manual Transfer...")
            
            # Create a new alternative task
            new_task_id = f"alt_{uuid.uuid4().hex[:4]}"
            new_task = TaskNode(
                id=new_task_id,
                name="Setup Manual Bank Transfer",
                action=self._mock_action, # This mock will succeed
                dependencies=failed_task.dependencies,
                status=TaskStatus.PENDING
            )
            
            # Update the DAG
            # 1. Add the new task
            self.current_dag.tasks[new_task.id] = new_task
            
            # 2. Update dependents of the old task to point to the new task
            for task in self.current_dag.tasks.values():
                if failed_task.id in task.dependencies:
                    task.dependencies.remove(failed_task.id)
                    task.dependencies.add(new_task.id)
                    logger.info(f"Rewired dependency: {task.name} now depends on {new_task.name}")
            
            # 3. Mark old task as failed (permanently)
            failed_task.status = TaskStatus.FAILED
            
            return self.current_dag
        
        raise RuntimeError("Unrecoverable strategy failure.")

    def execute_goal(self, goal: str, env_simulator: Dict[str, Any]) -> bool:
        """
        Main execution loop.
        
        Args:
            goal: The objective to achieve.
            env_simulator: Dictionary representing the 'World' (e.g., API status).
        
        Returns:
            bool: True if goal achieved, False otherwise.
        """
        self.environment_state = env_simulator
        self.current_dag = self._generate_plan(goal)
        
        while True:
            ready_tasks = self.current_dag.get_ready_tasks()
            
            if not ready_tasks:
                # Check termination conditions
                completed_count = sum(1 for t in self.current_dag.tasks.values() if t.status == TaskStatus.COMPLETED)
                if completed_count == len(self.current_dag.tasks):
                    logger.info(">>> GOAL ACHIEVED: All tasks completed successfully. <<<")
                    return True
                
                blocked_or_running = [t.status for t in self.current_dag.tasks.values() 
                                      if t.status in (TaskStatus.BLOCKED, TaskStatus.RUNNING)]
                if not blocked_or_running:
                    logger.error(">>> DEADLOCK DETECTED: No tasks ready, but goal not met. <<<")
                    return False
                time.sleep(0.1) # Simple wait simulation
                continue

            # Execute ready tasks
            for task in ready_tasks:
                task.status = TaskStatus.RUNNING
                logger.info(f"Executing Task: {task.name}")
                
                try:
                    result = task.action(task.name)
                    if result:
                        task.status = TaskStatus.COMPLETED
                    else:
                        # Action signaled failure
                        task.retries += 1
                        if task.retries >= task.max_retries:
                            task.status = TaskStatus.BLOCKED
                            # Trigger Adaptation
                            self.current_dag = self._detect_and_adapt(task)
                
                except Exception as e:
                    logger.error(f"Critical error in task {task.name}: {e}")
                    task.status = TaskStatus.FAILED
                    return False

    # --- Helper / Mock Functions ---

    def _mock_action(self, name: str) -> bool:
        """[Helper Function] Simulates a generic successful action."""
        logger.debug(f"Simulating success for: {name}")
        return True

    def _mock_payment_setup(self, name: str) -> bool:
        """Simulates an action that checks the environment state."""
        logger.debug(f"Attempting {name}...")
        if self.environment_state.get("payment_api_banned", False):
            logger.error(f"Environmental Resistance: {name} blocked by external firewall!")
            return False
        return True

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Define the Vague Goal
    vague_goal = "利用当前技能树在两周内通过电商赚取1000美元"
    
    # 2. Define a Hostile Environment (The 'Resistance')
    # Here, we simulate that the standard payment API is blocked.
    hostile_environment = {
        "payment_api_banned": True
    }
    
    # 3. Initialize System
    planner = RobustDecomposer()
    
    # 4. Run
    success = planner.execute_goal(vague_goal, hostile_environment)
    
    if success:
        print("\nResult: System successfully navigated around the blocked API.")
    else:
        print("\nResult: System failed.")