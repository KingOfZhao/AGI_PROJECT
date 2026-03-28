"""
Module: long_term_task_planner.py
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Description: 
    This module implements a robust engine for decomposing high-level, ambiguous 
    goals into structured, executable project plans (Gantt charts). It focuses on 
    top-down decomposition, dependency resolution, and Definition of Done (DoD) 
    verification.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Enumeration of possible task statuses."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class Priority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """
    Represents a single node in the project plan graph.
    
    Attributes:
        id: Unique identifier for the task.
        name: Short title of the task.
        description: Detailed description.
        duration_days: Estimated working days required.
        dependencies: List of Task IDs that must be completed before this task.
        dod: Definition of Done - specific verifiable criteria.
        status: Current state of the task.
        priority: Importance level of the task.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    duration_days: int = 1
    dependencies: List[str] = field(default_factory=list)
    dod: List[str] = field(default_factory=list)  # Definition of Done criteria
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def __post_init__(self):
        """Validate data after initialization."""
        if self.duration_days < 0:
            raise ValueError("Duration cannot be negative.")


class ProjectPlanningError(Exception):
    """Custom exception for planning logic errors."""
    pass


class LongTermTaskPlanner:
    """
    Core AGI Skill class for long-term task planning.
    
    This class handles the decomposition of fuzzy goals into structured plans,
    dependency graph construction, and schedule generation (Gantt logic).
    """

    def __init__(self, project_name: str, start_date: Optional[datetime] = None):
        """
        Initialize the planner.
        
        Args:
            project_name: The high-level name of the project.
            start_date: The start date for the project (defaults to today).
        """
        self.project_name = project_name
        self.tasks: Dict[str, Task] = {}
        self.start_date = start_date if start_date else datetime.now().replace(hour=0, minute=0, second=0)
        logger.info(f"Initialized planner for project: {project_name}")

    def _validate_task_structure(self, task_data: Dict) -> bool:
        """
        Validate the structure of task data before creation.
        
        Args:
            task_data: Dictionary containing task details.
            
        Returns:
            True if valid.
            
        Raises:
            ValueError: If required fields are missing or invalid.
        """
        required_keys = {"name", "duration_days", "dod"}
        if not required_keys.issubset(task_data.keys()):
            missing = required_keys - task_data.keys()
            raise ValueError(f"Missing required task keys: {missing}")
        
        if not isinstance(task_data['dod'], list) or len(task_data['dod']) < 1:
            raise ValueError(f"Task '{task_data.get('name')}' must have at least one DoD criterion.")
            
        return True

    def add_task(self, 
                 name: str, 
                 description: str, 
                 duration_days: int, 
                 dod: List[str], 
                 dependencies: Optional[List[str]] = None,
                 priority: Priority = Priority.MEDIUM) -> str:
        """
        Add a new task to the project plan.
        
        Args:
            name: Task name.
            description: Task details.
            duration_days: Estimated duration.
            dod: List of verifiable completion criteria.
            dependencies: IDs of prerequisite tasks.
            priority: Priority level.
            
        Returns:
            The ID of the created task.
        """
        try:
            task_data = {
                "name": name,
                "description": description,
                "duration_days": duration_days,
                "dod": dod,
                "dependencies": dependencies or []
            }
            self._validate_task_structure(task_data)

            task = Task(
                name=name,
                description=description,
                duration_days=duration_days,
                dependencies=dependencies or [],
                dod=dod,
                priority=priority
            )
            
            self.tasks[task.id] = task
            logger.debug(f"Added task: {name} (ID: {task.id})")
            return task.id
            
        except ValueError as ve:
            logger.error(f"Validation failed for task {name}: {ve}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error adding task: {e}")
            raise ProjectPlanningError(f"Could not add task {name}") from e

    def resolve_schedule(self) -> Dict[str, Dict]:
        """
        Calculate the schedule (Gantt chart) based on dependencies.
        
        This performs a topological sort to determine start and end dates.
        
        Returns:
            A dictionary representing the scheduled timeline.
            
        Raises:
            ProjectPlanningError: If circular dependencies are detected.
        """
        logger.info("Resolving project schedule...")
        visited: Set[str] = set()
        temp_marks: Set[str] = set()
        sorted_tasks: List[Task] = []

        def visit(task_id: str):
            if task_id in temp_marks:
                logger.error(f"Circular dependency detected at task {task_id}")
                raise ProjectPlanningError("Circular dependency detected")
            if task_id not in visited:
                temp_marks.add(task_id)
                task = self.tasks.get(task_id)
                if not task:
                    raise ProjectPlanningError(f"Unknown dependency ID: {task_id}")
                
                for dep_id in task.dependencies:
                    visit(dep_id)
                
                temp_marks.remove(task_id)
                visited.add(task_id)
                sorted_tasks.append(task)

        # Topological Sort
        for task_id in self.tasks:
            if task_id not in visited:
                visit(task_id)

        # Calculate Dates
        timeline = {}
        task_end_dates: Dict[str, datetime] = {}

        for task in sorted_tasks:
            # Determine earliest start date based on dependencies
            earliest_start = self.start_date
            for dep_id in task.dependencies:
                if dep_id in task_end_dates:
                    # Add 1 day buffer after dependency finishes
                    dep_finish = task_end_dates[dep_id] + timedelta(days=1)
                    if dep_finish > earliest_start:
                        earliest_start = dep_finish
            
            task.start_date = earliest_start
            task.end_date = earliest_start + timedelta(days=task.duration_days - 1) # Inclusive
            task_end_dates[task.id] = task.end_date
            
            timeline[task.id] = {
                "name": task.name,
                "start": task.start_date.strftime("%Y-%m-%d"),
                "end": task.end_date.strftime("%Y-%m-%d"),
                "duration": task.duration_days,
                "dod": task.dod,
                "dependencies": task.dependencies
            }

        logger.info(f"Schedule resolved. Total tasks: {len(sorted_tasks)}")
        return timeline

    def export_plan(self, format: str = "dict") -> str:
        """
        Export the plan to JSON or Dict.
        
        Args:
            format: 'dict' or 'json'.
        """
        schedule = self.resolve_schedule()
        if format == 'json':
            return json.dumps(schedule, indent=4)
        return schedule


# Helper Function for Demonstration
def generate_blog_project_plan() -> Dict:
    """
    Helper function to simulate the 'AGI' generation of a specific plan.
    
    Scenario: Building a Personal Blog with SEO Optimization.
    This demonstrates how the class is used to structure a complex request.
    """
    planner = LongTermTaskPlanner("Personal Blog & SEO Project")
    
    # Phase 1: Setup
    t1 = planner.add_task(
        name="Requirement Analysis",
        description="Define target audience, tech stack (e.g., Python/Django or WordPress), and hosting.",
        duration_days=2,
        dod=["Tech stack document signed off", "Domain name purchased"],
        priority=Priority.CRITICAL
    )

    # Phase 2: Infrastructure
    t2 = planner.add_task(
        name="Environment Setup",
        description="Setup CI/CD, servers, and database.",
        duration_days=3,
        dod=["Server accessible via SSH", "CI pipeline runs 'Hello World'"],
        dependencies=[t1]
    )

    # Phase 3: Content & Dev Parallel
    t3 = planner.add_task(
        name="SEO Keyword Research",
        description="Identify top 20 keywords for the niche.",
        duration_days=3,
        dod=["Spreadsheet of keywords with volume/difficulty"],
        dependencies=[t1]
    )

    t4 = planner.add_task(
        name="Backend Development",
        description="Develop API and Admin Panel.",
        duration_days=10,
        dod=["API endpoints documented", "Admin login functional"],
        dependencies=[t2]
    )

    t5 = planner.add_task(
        name="Frontend Development",
        description="UI implementation and responsiveness.",
        duration_days=10,
        dod=["Lighthouse score > 80", "Mobile responsive"],
        dependencies=[t2]
    )

    # Phase 4: Content Integration
    t6 = planner.add_task(
        name="Initial Content Creation",
        description="Write first 5 blog posts based on keywords.",
        duration_days=5,
        dod=["5 posts published", "Meta tags present"],
        dependencies=[t3, t4] # Needs keywords and Backend/Admin
    )

    t7 = planner.add_task(
        name="On-Page SEO Optimization",
        description="Optimize loading speed, structure data, sitemap.",
        duration_days=3,
        dod=["Sitemap.xml generated", "Schema markup validated"],
        dependencies=[t5, t6]
    )

    t8 = planner.add_task(
        name="Final Review & Launch",
        description="Security audit and DNS switch.",
        duration_days=2,
        dod=["SSL active", "Site live on domain"],
        dependencies=[t7]
    )

    return planner.export_plan()


if __name__ == "__main__":
    # Example Usage
    try:
        print("--- Generating Project Plan ---")
        project_timeline = generate_blog_project_plan()
        print(json.dumps(project_timeline, indent=2))
        
        print("\n--- Verification ---")
        print(f"Total Steps Generated: {len(project_timeline)}")
        
    except ProjectPlanningError as ppe:
        logger.error(f"Planning failed: {ppe}")
    except Exception as e:
        logger.error(f"System error: {e}")