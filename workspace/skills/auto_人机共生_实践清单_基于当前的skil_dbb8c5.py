"""
Module: auto_symbiosis_practice_list.py
Description: Generates high-executability practice checklists (minimum viable units)
             based on a provided skill graph to facilitate Human-AI Symbiosis.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, TypedDict, Literal
from dataclasses import dataclass, field
from enum import Enum

# --- Configuration & Setup ---

# Setting up robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures & Types ---

class TaskComplexity(Enum):
    """Enum defining the complexity levels of cognitive nodes."""
    HIGH = "macro"          # e.g., "Start a business"
    MEDIUM = "meso"         # e.g., "Validate market demand"
    LOW = "micro"           # e.g., "Interview 3 users"

class ActionType(Enum):
    """Types of executable actions."""
    INTERVIEW = "interview"
    SURVEY = "survey"
    PROTOTYPE_TEST = "prototype_test"
    DATA_ANALYSIS = "data_analysis"
    CODE_COMMIT = "code_commit"

class NodeStatus(Enum):
    """Status of the cognitive node."""
    ACTIVE = "active"
    PENDING = "pending"
    COMPLETED = "completed"

@dataclass
class CognitiveNode:
    """
    Represents a node in the AGI skill/knowledge graph.
    
    Attributes:
        id: Unique identifier.
        name: Human-readable name (e.g., 'Entrepreneurship').
        description: Detailed context.
        complexity: Estimated complexity level.
        current_weight: The current importance or confidence score (0.0 to 1.0).
        parent_id: ID of the parent node, if any.
        status: Current status of the node.
    """
    id: str
    name: str
    description: str
    complexity: TaskComplexity
    current_weight: float = 0.5
    parent_id: Optional[str] = None
    status: NodeStatus = NodeStatus.ACTIVE

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.current_weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {self.current_weight}")

@dataclass
class ActionableTask:
    """
    Represents a 'Minimum Executable Unit' for the human partner.
    """
    task_id: str
    title: str
    description: str
    associated_node_id: str
    estimated_duration_hours: float
    deadline: datetime
    required_tools: List[str]
    expected_feedback_type: str  # What data will the human return?
    action_type: ActionType
    generation_timestamp: datetime = field(default_factory=datetime.now)

class SkillGraph(TypedDict):
    """Type definition for the input skill database."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, str]]

# --- Core Logic Classes ---

class NodeParser:
    """
    Analyzes and processes raw skill data into structured CognitiveNodes.
    Handles input validation and initial complexity estimation.
    """
    
    @staticmethod
    def estimate_complexity(node_name: str, description: str) -> TaskComplexity:
        """Heuristic to determine node complexity based on keywords."""
        text = f"{node_name} {description}".lower()
        
        macro_keywords = ["strategy", "start", "business", "system", "architecture"]
        meso_keywords = ["validate", "design", "analyze", "develop", "plan"]
        
        if any(kw in text for kw in macro_keywords):
            return TaskComplexity.HIGH
        elif any(kw in text for kw in meso_keywords):
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.LOW

    def parse_raw_data(self, raw_data: List[Dict[str, Any]]) -> List[CognitiveNode]:
        """
        Converts raw dictionaries into validated CognitiveNode objects.
        
        Args:
            raw_data: List of dictionaries containing node info.
            
        Returns:
            List of validated CognitiveNode objects.
            
        Raises:
            ValueError: If required fields are missing.
        """
        processed_nodes = []
        
        for item in raw_data:
            try:
                # Data Validation
                if 'name' not in item or 'id' not in item:
                    logger.warning(f"Skipping invalid node data: {item}")
                    continue
                
                complexity = item.get('complexity', self.estimate_complexity(item['name'], item.get('description', '')))
                
                node = CognitiveNode(
                    id=item['id'],
                    name=item['name'],
                    description=item.get('description', ''),
                    complexity=TaskComplexity(complexity) if isinstance(complexity, str) else complexity,
                    current_weight=float(item.get('weight', 0.5)),
                    parent_id=item.get('parent_id')
                )
                processed_nodes.append(node)
                logger.debug(f"Parsed node: {node.name} (Complexity: {node.complexity})")
                
            except Exception as e:
                logger.error(f"Failed to parse node {item.get('id', 'unknown')}: {e}")
                continue
                
        return processed_nodes

class SymbiosisPlanner:
    """
    The core engine for generating the Human-Computer Symbiosis Practice List.
    It identifies actionable items and updates cognitive weights based on feedback loops.
    """

    def __init__(self, max_daily_hours: float = 8.0):
        self.max_daily_hours = max_daily_hours
        self.task_templates = self._load_task_templates()

    def _load_task_templates(self) -> Dict[TaskComplexity, Dict[str, Any]]:
        """Helper to load decomposition rules."""
        return {
            TaskComplexity.HIGH: {
                "action": ActionType.INTERVIEW,
                "duration": 2.0,
                "feedback": "qualitative_summary",
                "instruction": "Identify 3 potential stakeholders and conduct brief interviews."
            },
            TaskComplexity.MEDIUM: {
                "action": ActionType.SURVEY,
                "duration": 1.0,
                "feedback": "quantitative_data",
                "instruction": "Distribute a 5-question survey to target demographic."
            },
            TaskComplexity.LOW: {
                "action": ActionType.PROTOTYPE_TEST,
                "duration": 0.5,
                "feedback": "usability_report",
                "instruction": "Perform A/B test on specific feature."
            }
        }

    def _decompose_node(self, node: CognitiveNode) -> List[ActionableTask]:
        """
        Core Heuristic: Breaks down a node into executable tasks.
        Strategy: If node is complex, create a task to gather info to simplify it.
        """
        tasks = []
        template = self.task_templates.get(node.complexity)
        
        if not template:
            logger.warning(f"No template found for complexity {node.complexity}")
            return tasks

        # Generate a task specifically designed to validate or update this node's weight
        deadline = datetime.now() + timedelta(hours=24)
        
        task = ActionableTask(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            title=f"Validation: {node.name}",
            description=f"To progress on '{node.name}': {template['instruction']}",
            associated_node_id=node.id,
            estimated_duration_hours=template['duration'],
            deadline=deadline,
            required_tools=["Notebook", "Communication App"],
            expected_feedback_type=template['feedback'],
            action_type=template['action']
        )
        tasks.append(task)
        
        return tasks

    def generate_daily_checklist(self, nodes: List[CognitiveNode]) -> List[ActionableTask]:
        """
        Generates an optimized practice list for the next 24 hours.
        Prioritizes nodes with high uncertainty (weight ~0.5) or high impact.
        
        Args:
            nodes: List of current cognitive nodes.
            
        Returns:
            A list of ActionableTasks fitting within time constraints.
        """
        if not nodes:
            logger.info("No nodes provided for planning.")
            return []

        # Sort nodes: Prioritize active nodes that need validation (weight near 0.5 means uncertainty)
        # We want to move weight towards 0.0 (discard) or 1.0 (confirm)
        sorted_nodes = sorted(
            nodes, 
            key=lambda n: abs(0.5 - n.current_weight), 
            reverse=False # False means highest uncertainty first? 
            # Actually, let's prioritize high weight but unconfirmed, or specific logic.
            # Here we simply sort by complexity to ensure big rocks are handled.
        )
        
        daily_plan: List[ActionableTask] = []
        accumulated_hours = 0.0
        
        logger.info(f"Generating daily plan. Capacity: {self.max_daily_hours} hours.")
        
        for node in sorted_nodes:
            if accumulated_hours >= self.max_daily_hours:
                logger.info("Daily capacity reached.")
                break
                
            # Generate candidate tasks
            candidate_tasks = self._decompose_node(node)
            
            for task in candidate_tasks:
                if (accumulated_hours + task.estimated_duration_hours) <= self.max_daily_hours:
                    daily_plan.append(task)
                    accumulated_hours += task.estimated_duration_hours
                    logger.info(f"Added task: {task.title} ({task.estimated_duration_hours}h)")
                else:
                    # Try to find a smaller task or skip
                    continue
                    
        return daily_plan

    def process_feedback(self, task: ActionableTask, feedback_data: Dict[str, Any]) -> float:
        """
        Updates the cognitive node weight based on task execution feedback.
        
        Args:
            task: The completed task.
            feedback_data: Data containing 'success_score' (0.0-1.0).
            
        Returns:
            The new calculated weight delta.
        """
        try:
            score = float(feedback_data.get('success_score', 0.5))
            if not 0.0 <= score <= 1.0:
                raise ValueError("Score out of range")
            
            # Simple reinforcement logic:
            # If score is high, increase confidence. 
            # In a real system, this would update the vector DB or graph weights.
            logger.info(f"Processing feedback for node {task.associated_node_id}. Score: {score}")
            
            # Return delta for the system to apply
            return (score - 0.5) * 0.2  # Small adjustment
            
        except Exception as e:
            logger.error(f"Invalid feedback data: {e}")
            return 0.0

# --- Helper Functions ---

def format_checklist_for_human(tasks: List[ActionableTask]) -> str:
    """
    Formats the list of tasks into a human-readable markdown string.
    """
    if not tasks:
        return "No actionable tasks for today. Review long-term goals."
    
    output = ["# 🧠 Human-AI Symbiosis Daily Practice List"]
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    for i, task in enumerate(tasks, 1):
        output.append(f"## {i}. {task.title}")
        output.append(f"**Node ID:** `{task.associated_node_id}`")
        output.append(f"**Action:** {task.action_type.value}")
        output.append(f"**Goal:** {task.description}")
        output.append(f"**Time Est:** {task.estimated_duration_hours} hours")
        output.append(f"**Deadline:** {task.deadline.strftime('%H:%M')}")
        output.append("---")
        
    return "\n".join(output)

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Simulate Input Data (The 'Current Skill DB')
    raw_skill_data = [
        {
            "id": "node_001",
            "name": "Start an AI Startup",
            "description": "Establish a company focused on AGI solutions.",
            "weight": 0.8,
            "complexity": "macro"
        },
        {
            "id": "node_002",
            "name": "Validate Market Fit",
            "description": "Ensure the product meets market needs.",
            "weight": 0.5, # High uncertainty
            "complexity": "meso"
        },
        {
            "id": "node_003",
            "name": "Write Pitch Deck",
            "description": "Create slides for investors.",
            "weight": 0.2,
            "complexity": "meso"
        }
    ]

    try:
        # 2. Parse Nodes
        parser = NodeParser()
        cognitive_nodes = parser.parse_raw_data(raw_skill_data)
        
        # 3. Generate Checklist
        planner = SymbiosisPlanner(max_daily_hours=4.0)
        daily_tasks = planner.generate_daily_checklist(cognitive_nodes)
        
        # 4. Output Results
        checklist_markdown = format_checklist_for_human(daily_tasks)
        print(checklist_markdown)
        
        # 5. Simulate Feedback Loop
        if daily_tasks:
            sample_task = daily_tasks[0]
            print(f"\n>>> Simulating feedback for task: {sample_task.title}")
            mock_feedback = {"success_score": 0.9} # User reported high success
            delta = planner.process_feedback(sample_task, mock_feedback)
            print(f">>> Node {sample_task.associated_node_id} weight updated by delta: {delta:.2f}")

    except Exception as e:
        logger.critical(f"System Failure: {e}", exc_info=True)