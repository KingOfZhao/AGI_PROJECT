"""
Module: reputation_based_task_protocol
Description: Implements a reputation-based task allocation protocol for multi-agent systems.
             This module simulates authorization and accountability mechanisms found in
             human organizations, ensuring tasks are assigned to agents based on their
             historical performance and reliability.

Author: AGI System
Version: 1.0.0
License: MIT
"""

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Enumeration of task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Enumeration of possible task statuses."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """
    Represents an intelligent agent in the system.
    
    Attributes:
        id: Unique identifier for the agent.
        name: Human-readable name of the agent.
        specialization: The agent's area of expertise.
        reputation_score: Current reputation score (0.0 to 100.0).
        completed_tasks: Number of tasks successfully completed.
        failed_tasks: Number of tasks failed.
        current_load: Current number of active tasks.
        max_capacity: Maximum concurrent tasks the agent can handle.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Agent"
    specialization: str = "general"
    reputation_score: float = 50.0
    completed_tasks: int = 0
    failed_tasks: int = 0
    current_load: int = 0
    max_capacity: int = 5

    def __post_init__(self):
        """Validate data after initialization."""
        if not (0.0 <= self.reputation_score <= 100.0):
            raise ValueError("Reputation score must be between 0.0 and 100.0")
        if self.max_capacity < 1:
            raise ValueError("Max capacity must be at least 1")


@dataclass
class Task:
    """
    Represents a task to be allocated.
    
    Attributes:
        id: Unique identifier for the task.
        description: Description of the task.
        required_specialization: Required agent specialization.
        priority: Priority level of the task.
        difficulty: Estimated difficulty (1-10).
        status: Current status of the task.
        assigned_agent_id: ID of the assigned agent (if any).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = "Generic Task"
    required_specialization: str = "general"
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: int = 5
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None

    def __post_init__(self):
        """Validate data after initialization."""
        if not (1 <= self.difficulty <= 10):
            raise ValueError("Difficulty must be between 1 and 10")


class ReputationTaskProtocol:
    """
    Manages the allocation of tasks to agents based on reputation and capacity.
    
    This class implements the core logic for a reputation-based decentralized
    or centralized task allocation protocol.
    """

    def __init__(self, initial_agents: Optional[List[Agent]] = None):
        """
        Initialize the protocol manager.
        
        Args:
            initial_agents: A list of agents to register at startup.
        """
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.history: List[Dict] = []  # Audit trail
        
        if initial_agents:
            for agent in initial_agents:
                self.register_agent(agent)
                
        logger.info(f"ReputationTaskProtocol initialized with {len(self.agents)} agents.")

    def register_agent(self, agent: Agent) -> bool:
        """
        Register a new agent in the system.
        
        Args:
            agent: The Agent object to register.
            
        Returns:
            bool: True if registration successful, False otherwise.
            
        Raises:
            TypeError: If input is not an Agent instance.
        """
        if not isinstance(agent, Agent):
            logger.error("Invalid object type passed to register_agent.")
            raise TypeError("Input must be an instance of Agent")
        
        if agent.id in self.agents:
            logger.warning(f"Agent {agent.id} already exists.")
            return False
            
        self.agents[agent.id] = agent
        logger.info(f"Agent registered: {agent.name} (ID: {agent.id})")
        return True

    def submit_task(self, task: Task) -> str:
        """
        Submit a new task into the allocation queue.
        
        Args:
            task: The Task object to submit.
            
        Returns:
            str: The ID of the submitted task.
        """
        if not isinstance(task, Task):
            raise TypeError("Input must be an instance of Task")
            
        self.tasks[task.id] = task
        logger.info(f"Task submitted: {task.description} (Priority: {task.priority.name})")
        return task.id

    def _calculate_agent_score(self, agent: Agent, task: Task) -> float:
        """
        Helper function to calculate the suitability score of an agent for a specific task.
        
        Scoring Logic:
        - Base: Reputation Score (0-100)
        - Specialization Match Bonus: +20 points
        - Load Penalty: -10 points per current task
        - Difficulty Threshold: Agents with low reputation cannot take high difficulty tasks.
        
        Args:
            agent: The agent to evaluate.
            task: The task to be assigned.
            
        Returns:
            float: Suitability score. -1.0 if ineligible.
        """
        # Boundary Check: Capacity
        if agent.current_load >= agent.max_capacity:
            return -1.0

        # Boundary Check: Reputation vs Difficulty (Accountability mechanism)
        # High difficulty tasks require high reputation
        if task.difficulty > 8 and agent.reputation_score < 60.0:
            return -1.0
        if task.difficulty > 5 and agent.reputation_score < 30.0:
            return -1.0

        score = agent.reputation_score
        
        # Specialization Match
        if agent.specialization == task.required_specialization:
            score += 20.0
        elif task.required_specialization != "general":
            score -= 20.0 # Penalty for non-match if specific skill required

        # Load Balancing factor
        score -= (agent.current_load * 5.0)
        
        # Ensure score is not negative
        return max(0.0, score)

    def allocate_task(self, task_id: str) -> Tuple[bool, Optional[str]]:
        """
        Attempt to assign a specific task to the best available agent.
        
        This is the core 'Authorization' function.
        
        Args:
            task_id: The ID of the task to allocate.
            
        Returns:
            Tuple[bool, Optional[str]]: (Success status, Assigned Agent ID or Error message)
        """
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found.")
            return False, "Task not found"

        task = self.tasks[task_id]
        
        if task.status != TaskStatus.PENDING:
            logger.warning(f"Task {task_id} is not pending (Status: {task.status}).")
            return False, "Task is not pending"

        best_agent_id: Optional[str] = None
        highest_score: float = -1.0

        # Find best candidate
        for agent_id, agent in self.agents.items():
            current_score = self._calculate_agent_score(agent, task)
            if current_score > highest_score:
                highest_score = current_score
                best_agent_id = agent_id

        if best_agent_id and highest_score >= 0:
            # Authorization granted
            task.status = TaskStatus.ASSIGNED
            task.assigned_agent_id = best_agent_id
            self.agents[best_agent_id].current_load += 1
            
            record = {
                "event": "TASK_ASSIGNED",
                "task_id": task_id,
                "agent_id": best_agent_id,
                "score": highest_score
            }
            self.history.append(record)
            logger.info(f"Task {task_id} assigned to Agent {best_agent_id} (Score: {highest_score:.2f})")
            return True, best_agent_id
        
        logger.warning(f"No suitable agent found for task {task_id}")
        return False, "No suitable agent available"

    def report_task_outcome(self, task_id: str, success: bool, performance_delta: float = 0.0) -> None:
        """
        Report the outcome of a task and update agent reputation.
        
        This is the core 'Accountability' function.
        
        Args:
            task_id: The ID of the completed/failed task.
            success: True if task succeeded, False otherwise.
            performance_delta: Custom adjustment factor (-10 to 10).
        """
        if task_id not in self.tasks:
            raise ValueError("Task ID does not exist")
            
        task = self.tasks[task_id]
        agent_id = task.assigned_agent_id
        
        if not agent_id or agent_id not in self.agents:
            logger.error(f"Cannot report outcome: Task {task_id} has no valid assigned agent.")
            return

        agent = self.agents[agent_id]
        agent.current_load = max(0, agent.current_load - 1)
        
        # Base reputation adjustment
        base_change = 0.0
        if success:
            task.status = TaskStatus.COMPLETED
            agent.completed_tasks += 1
            # Reward based on difficulty
            base_change = 1.0 + (task.difficulty * 0.5) 
            logger.info(f"Task {task_id} COMPLETED by {agent.name}. Reputation increasing.")
        else:
            task.status = TaskStatus.FAILED
            agent.failed_tasks += 1
            # Penalty based on priority
            base_change = -5.0 - (task.priority.value * 2.0)
            logger.warning(f"Task {task_id} FAILED by {agent.name}. Reputation decreasing.")

        # Apply custom delta (e.g., partial success, minor errors)
        total_change = base_change + performance_delta
        
        # Update reputation with boundary checks
        new_score = agent.reputation_score + total_change
        agent.reputation_score = max(0.0, min(100.0, new_score))
        
        logger.info(f"Agent {agent.name} reputation updated: {agent.reputation_score:.2f}")


# ==============================================================================
# Usage Example
# ==============================================================================
if __name__ == "__main__":
    # 1. Setup the Protocol
    protocol = ReputationTaskProtocol()

    # 2. Create and Register Agents
    # Agent A: High reputation, specialized in data
    agent_a = Agent(
        name="Alpha",
        specialization="data_analysis",
        reputation_score=85.0,
        max_capacity=3
    )
    # Agent B: New agent, generalist
    agent_b = Agent(
        name="Beta",
        specialization="general",
        reputation_score=40.0,
        max_capacity=2
    )
    
    protocol.register_agent(agent_a)
    protocol.register_agent(agent_b)

    # 3. Create Tasks
    task_1 = Task(
        description="Analyze Q3 financial data",
        required_specialization="data_analysis",
        difficulty=8,
        priority=TaskPriority.HIGH
    )
    
    task_2 = Task(
        description="Clean up temporary logs",
        required_specialization="general",
        difficulty=2,
        priority=TaskPriority.LOW
    )

    # 4. Submit and Allocate Task 1 (High difficulty)
    protocol.submit_task(task_1)
    success, assigned_id = protocol.allocate_task(task_1.id)
    if success:
        print(f"\nTask 1 assigned to: {protocol.agents[assigned_id].name}")
        
        # 5. Simulate completion
        protocol.report_task_outcome(task_1.id, success=True)
        print(f"Agent Alpha Rep: {protocol.agents[agent_a.id].reputation_score:.2f}")

    # 6. Submit and Allocate Task 2 (Low difficulty)
    protocol.submit_task(task_2)
    success, assigned_id = protocol.allocate_task(task_2.id)
    if success:
        print(f"\nTask 2 assigned to: {protocol.agents[assigned_id].name}")
        # Simulate failure
        protocol.report_task_outcome(task_2.id, success=False)
        print(f"Agent Beta Rep: {protocol.agents[agent_b.id].reputation_score:.2f}")