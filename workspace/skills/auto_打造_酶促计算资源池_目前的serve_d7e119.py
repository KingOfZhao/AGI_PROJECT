"""
Module: auto_打造_酶促计算资源池_目前的serve_d7e119

Description:
    This module implements an 'Enzymatic Compute Resource Pool' to address Serverless cold-start 
    latency issues. It utilizes biological metaphors:
    1. Lock-and-Key Model: Maintaining a 'Substrate Pre-heat Pool' (warm containers) matched to 
       specific event types (substrates).
    2. Ribosome Activation: Rapidly activating 'semi-dormant' instances.
    3. Allosteric Regulation: Dynamically adjusting resource affinity based on substrate concentration.

Author: Advanced Python Engineer (AGI System Component)
Domain: Cross-Domain (Bio-inspired Computing)
"""

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Deque

# --- Configuration & Constants ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("EnzymaticPool")

# Allosteric threshold: If task backlog exceeds this, trigger affinity change
ALLOSTERIC_THRESHOLD = 5
ACTIVATION_DELAY_MS = 0.01  # Simulated delay for active instance (seconds)
COLD_START_DELAY_MS = 2.0   # Simulated delay for cold start (seconds)


class TaskType(Enum):
    """Enumerates supported task types (Substrates)."""
    IMAGE_PROCESSING = auto()
    DATA_ETL = auto()
    INFERENCE = auto()
    STREAM_PROCESSING = auto()


class InstanceState(Enum):
    """States of a compute instance."""
    DORMANT = auto()      # Semi-sleep, pre-warmed
    ACTIVE = auto()       # Currently processing
    TERMINATED = auto()   # Dead


@dataclass
class ComputeInstance:
    """Represents a single compute unit (Ribosome)."""
    instance_id: str
    affinity: TaskType
    state: InstanceState = InstanceState.DORMANT
    last_active: float = field(default_factory=time.time)

    def activate(self) -> float:
        """
        Activates the instance (Lock-and-Key match).
        Returns execution time.
        """
        if self.state != InstanceState.DORMANT:
            raise ValueError(f"Instance {self.instance_id} is not dormant.")

        logger.info(f"Activating instance {self.instance_id} for {self.affinity.name}")
        self.state = InstanceState.ACTIVE
        self.last_active = time.time()
        return ACTIVATION_DELAY_MS

    def terminate(self):
        """Terminates the instance."""
        self.state = InstanceState.TERMINATED
        logger.info(f"Instance {self.instance_id} terminated.")


@dataclass
class Task:
    """Incoming task definition (Substrate)."""
    task_id: str
    task_type: TaskType
    payload: Dict


class EnzymaticScheduler:
    """
    Manages the compute resource pool, mimicking enzymatic behavior.
    Handles pre-warming, matching, and allosteric regulation.
    """

    def __init__(self, initial_pool_size: int = 10):
        """
        Initializes the scheduler and the pre-heated pool.

        Args:
            initial_pool_size: Number of dormant instances to start with.
        """
        self._pool: Dict[TaskType, List[ComputeInstance]] = {t: [] for t in TaskType}
        self._task_queues: Dict[TaskType, Deque[Task]] = {t: deque() for t in TaskType}
        self._current_allosteric_affinity: Optional[TaskType] = None
        
        logger.info("Initializing Enzymatic Scheduler...")
        self._initialize_pool(initial_pool_size)

    def _initialize_pool(self, count: int):
        """
        Helper function to generate initial pool.
        Distributes instances evenly across known task types.
        """
        types = list(TaskType)
        for i in range(count):
            # Distribute evenly initially
            t_type = types[i % len(types)]
            instance = ComputeInstance(
                instance_id=f"ribosome-{i}",
                affinity=t_type
            )
            self._pool[t_type].append(instance)
        logger.info(f"Pool initialized with {count} instances.")

    def _check_allosteric_regulation(self) -> Optional[TaskType]:
        """
        Checks substrate concentration (queue depth) to determine if 
        allosteric regulation (affinity shift) is needed.
        
        Returns:
            TaskType requiring priority, or None.
        """
        max_concentration = 0
        critical_type = None

        for t_type, queue in self._task_queues.items():
            q_len = len(queue)
            if q_len > ALLOSTERIC_THRESHOLD and q_len > max_concentration:
                max_concentration = q_len
                critical_type = t_type
        
        if critical_type and critical_type != self._current_allosteric_affinity:
            logger.warning(f"ALLOSTERIC SHIFT: High concentration of {critical_type.name} detected. Adjusting affinity.")
            self._current_allosteric_affinity = critical_type
        elif not critical_type:
            self._current_allosteric_affinity = None
            
        return critical_type

    async def submit_task(self, task: Task):
        """
        Accepts a task (Substrate) into the system.
        
        Args:
            task: The task object containing type and payload.
        """
        if not isinstance(task.task_type, TaskType):
            logger.error(f"Invalid task type: {task.task_type}")
            raise ValueError("Invalid TaskType provided.")
            
        logger.debug(f"Task {task.task_id} submitted.")
        self._task_queues[task.task_type].append(task)
        # Trigger processing
        await self.process_cycle()

    async def process_cycle(self):
        """
        Core processing loop. Matches substrates to enzymes (instances).
        """
        priority_type = self._check_allosteric_regulation()
        
        # Determine processing order based on regulation
        types_to_process = list(TaskType)
        if priority_type:
            # Move priority type to front
            types_to_process.remove(priority_type)
            types_to_process.insert(0, priority_type)

        for t_type in types_to_process:
            queue = self._task_queues[t_type]
            available_instances = [i for i in self._pool[t_type] if i.state == InstanceState.DORMANT]

            while queue and available_instances:
                task = queue.popleft()
                instance = available_instances.pop()
                
                # Execute
                exec_time = instance.activate()
                logger.info(f"Task {task.task_id} matched with {instance.instance_id} | Latency: {exec_time*1000}ms")
                
                # Simulate async execution
                asyncio.create_task(self._simulate_processing(instance, task))

            if queue and not available_instances:
                logger.warning(f"Starvation for {t_type.name}: Cold start required or scaling needed.")
                # In a real system, this would trigger a scaling event

    async def _simulate_processing(self, instance: ComputeInstance, task: Task):
        """Simulates work and returns instance to dormant state."""
        # Simulate variable work time
        await asyncio.sleep(random.uniform(0.1, 0.5)) 
        instance.state = InstanceState.DORMANT
        logger.debug(f"Task {task.task_id} finished. Instance {instance.instance_id} returning to dormant.")

    def get_pool_status(self) -> Dict:
        """Returns current pool statistics."""
        status = {}
        for t_type, instances in self._pool.items():
            dormant = sum(1 for i in instances if i.state == InstanceState.DORMANT)
            active = sum(1 for i in instances if i.state == InstanceState.ACTIVE)
            status[t_type.name] = {"dormant": dormant, "active": active, "backlog": len(self._task_queues[t_type])}
        return status


# --- Usage Example & Demonstration ---
async def main():
    """
    Demonstrates the Enzymatic Scheduler capabilities.
    
    Scenario:
    1. Submits a normal flow of mixed tasks.
    2. Submits a spike of DATA_ETL tasks to trigger Allosteric Regulation.
    3. Observes the scheduler prioritizing DATA_ETL.
    """
    scheduler = EnzymaticScheduler(initial_pool_size=12)
    
    print("\n--- Phase 1: Normal Operation ---")
    # Submit mixed tasks
    tasks = [
        Task("img-001", TaskType.IMAGE_PROCESSING, {"url": "http://a.com/1"}),
        Task("etl-001", TaskType.DATA_ETL, {"csv": "data.csv"}),
        Task("inf-001", TaskType.INFERENCE, {"model": "v1"}),
    ]
    
    for t in tasks:
        await scheduler.submit_task(t)
        
    print("\nCurrent Status:", scheduler.get_pool_status())
    
    print("\n--- Phase 2: Allosteric Trigger (Spike) ---")
    # Simulate a spike in DATA_ETL
    spike_tasks = [Task(f"etl-burst-{i}", TaskType.DATA_ETL, {"batch": i}) for i in range(10)]
    
    for t in spike_tasks:
        await scheduler.submit_task(t)
        
    # Allow some processing time
    await asyncio.sleep(1)
    
    print("\nFinal Status:", scheduler.get_pool_status())


if __name__ == "__main__":
    # Run the async main loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System shutdown initiated by user.")