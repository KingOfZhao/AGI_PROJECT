"""
Module: auto_skill_evolution_platform
A high-frequency skill evolution loop system for vertical domains.

This module implements a Lamarckian-style evolution platform where:
1. AI generates innovation task lists based on existing knowledge nodes
2. Human users execute tasks and provide feedback
3. System dynamically adjusts knowledge graph weights
4. Enables distributed skill evolution beyond individual experts
"""

import logging
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillEvolutionPlatform")


@dataclass
class KnowledgeNode:
    """Represents a knowledge node in the domain graph"""
    node_id: str
    name: str
    node_type: str  # 'ingredient', 'technique', 'tool', etc.
    attributes: Dict[str, float]  # e.g., {'spiciness': 0.8, 'umami': 0.6}
    connections: Dict[str, float]  # node_id -> connection_strength
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def validate(self) -> bool:
        """Validate node data integrity"""
        if not self.node_id or not self.name:
            return False
        if not isinstance(self.attributes, dict):
            return False
        if not isinstance(self.connections, dict):
            return False
        return True


@dataclass
class InnovationTask:
    """Represents an innovation task for human execution"""
    task_id: str
    description: str
    involved_nodes: List[str]
    hypothesis: str  # Expected outcome
    difficulty: float  # 0.1 (easy) to 1.0 (hard)
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def validate(self) -> bool:
        """Validate task data"""
        if not self.task_id or not self.description:
            return False
        if not 0 <= self.difficulty <= 1:
            return False
        return True


class SkillEvolutionPlatform:
    """
    Core platform for skill evolution through distributed human-AI collaboration.
    """

    def __init__(self, domain: str = "cooking"):
        """
        Initialize the platform for a specific domain.
        
        Args:
            domain: Target domain (cooking, programming, music, etc.)
        """
        self.domain = domain
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.task_queue: List[InnovationTask] = []
        self.feedback_history: List[Dict] = []
        self._initialize_base_knowledge()

    def _initialize_base_knowledge(self) -> None:
        """Initialize domain-specific base knowledge"""
        if self.domain == "cooking":
            base_nodes = [
                KnowledgeNode("ing_salt", "Salt", "ingredient",
                             {"salty": 1.0, "umami": 0.3}, {}),
                KnowledgeNode("ing_sugar", "Sugar", "ingredient",
                             {"sweet": 1.0, "umami": 0.1}, {}),
                KnowledgeNode("tech_roast", "Roasting", "technique",
                             {"temperature": 0.9, "dry_heat": 1.0}, {}),
                KnowledgeNode("tech_boil", "Boiling", "technique",
                             {"temperature": 0.7, "wet_heat": 1.0}, {}),
                KnowledgeNode("ing_chicken", "Chicken", "ingredient",
                             {"protein": 1.0, "neutral": 0.8}, {})
            ]
            
            # Add initial connections
            base_nodes[0].connections["ing_chicken"] = 0.8  # Salt goes with chicken
            base_nodes[4].connections["tech_roast"] = 0.9  # Chicken can be roasted
            
        elif self.domain == "programming":
            base_nodes = [
                KnowledgeNode("pattern_singleton", "Singleton Pattern", "pattern",
                             {"reusability": 0.7, "complexity": 0.3}, {}),
                KnowledgeNode("pattern_factory", "Factory Pattern", "pattern",
                             {"flexibility": 0.9, "complexity": 0.5}, {}),
                KnowledgeNode("lang_python", "Python", "language",
                             {"dynamic": 1.0, "readable": 0.9}, {}),
                KnowledgeNode("lang_rust", "Rust", "language",
                             {"safe": 1.0, "performance": 1.0}, {})
            ]
            
            # Add initial connections
            base_nodes[0].connections["lang_python"] = 0.6  # Singleton in Python
            base_nodes[1].connections["lang_rust"] = 0.7  # Factory in Rust
        else:
            logger.warning(f"No base knowledge for domain: {self.domain}")
            return
            
        for node in base_nodes:
            if node.validate():
                self.knowledge_graph[node.node_id] = node
            else:
                logger.error(f"Invalid node during initialization: {node.node_id}")
                
        logger.info(f"Initialized {len(self.knowledge_graph)} nodes for domain: {self.domain}")

    def generate_innovation_tasks(self, num_tasks: int = 5) -> List[InnovationTask]:
        """
        Generate innovation tasks based on current knowledge graph.
        
        Args:
            num_tasks: Number of tasks to generate
            
        Returns:
            List of InnovationTask objects
        """
        if num_tasks <= 0:
            raise ValueError("Number of tasks must be positive")
            
        if len(self.knowledge_graph) < 2:
            logger.warning("Not enough nodes to generate tasks")
            return []
            
        tasks = []
        node_list = list(self.knowledge_graph.values())
        
        for i in range(num_tasks):
            # Select random nodes to combine
            node_a, node_b = random.sample(node_list, 2)
            
            # Generate hypothesis based on node attributes
            common_attrs = set(node_a.attributes.keys()) & set(node_b.attributes.keys())
            
            if common_attrs:
                attr = random.choice(list(common_attrs))
                combined_score = (node_a.attributes[attr] + node_b.attributes[attr]) / 2
                
                if combined_score > 0.7:
                    hypothesis = f"High {attr} intensity expected"
                else:
                    hypothesis = f"Moderate {attr} combination"
            else:
                hypothesis = "Unknown interaction - experimental"
                
            # Calculate difficulty based on connection strength
            connection_strength = node_a.connections.get(node_b.node_id, 0)
            difficulty = 0.3 + (1 - connection_strength) * 0.5
            difficulty = min(1.0, max(0.1, difficulty))
            
            task = InnovationTask(
                task_id=f"task_{i}_{datetime.now().timestamp()}",
                description=f"Combine {node_a.name} with {node_b.name}",
                involved_nodes=[node_a.node_id, node_b.node_id],
                hypothesis=hypothesis,
                difficulty=difficulty
            )
            
            if task.validate():
                tasks.append(task)
                self.task_queue.append(task)
            else:
                logger.error(f"Generated invalid task: {task.task_id}")
                
        logger.info(f"Generated {len(tasks)} innovation tasks")
        return tasks

    def process_feedback(self, task_id: str, feedback: str, rating: float) -> bool:
        """
        Process human feedback and update knowledge graph.
        
        Args:
            task_id: ID of the completed task
            feedback: "positive" or "negative"
            rating: 0.0 (worst) to 1.0 (best)
            
        Returns:
            True if update successful, False otherwise
        """
        # Input validation
        if feedback not in ["positive", "negative"]:
            logger.error(f"Invalid feedback type: {feedback}")
            return False
            
        if not 0 <= rating <= 1:
            logger.error(f"Rating out of bounds: {rating}")
            return False
            
        # Find task
        task = next((t for t in self.task_queue if t.task_id == task_id), None)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
            
        # Update knowledge graph connections
        node_ids = task.involved_nodes
        if len(node_ids) != 2:
            logger.error(f"Task has invalid node count: {len(node_ids)}")
            return False
            
        node_a = self.knowledge_graph.get(node_ids[0])
        node_b = self.knowledge_graph.get(node_ids[1])
        
        if not node_a or not node_b:
            logger.error("Task references non-existent nodes")
            return False
            
        # Calculate weight adjustment
        adjustment = 0.2 if feedback == "positive" else -0.15
        adjustment *= rating  # Scale by rating intensity
        
        # Update bidirectional connections
        current_strength = node_a.connections.get(node_b.node_id, 0)
        new_strength = max(0, min(1, current_strength + adjustment))
        
        node_a.connections[node_b.node_id] = new_strength
        node_b.connections[node_a.node_id] = new_strength
        node_a.last_updated = datetime.now()
        node_b.last_updated = datetime.now()
        
        # Record feedback
        feedback_record = {
            "task_id": task_id,
            "feedback": feedback,
            "rating": rating,
            "nodes": node_ids,
            "adjustment": adjustment,
            "timestamp": datetime.now().isoformat()
        }
        self.feedback_history.append(feedback_record)
        
        # Remove task from queue
        self.task_queue.remove(task)
        
        logger.info(f"Processed feedback for task {task_id}: {feedback} ({rating})")
        return True

    def get_knowledge_stats(self) -> Dict:
        """
        Get statistics about the current knowledge graph.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self.knowledge_graph:
            return {"node_count": 0, "connection_count": 0}
            
        total_connections = sum(
            len(node.connections) for node in self.knowledge_graph.values()
        ) // 2  # Divide by 2 since connections are bidirectional
        
        avg_strength = 0
        if total_connections > 0:
            strength_sum = sum(
                sum(node.connections.values())
                for node in self.knowledge_graph.values()
            )
            avg_strength = strength_sum / (total_connections * 2)
            
        return {
            "domain": self.domain,
            "node_count": len(self.knowledge_graph),
            "connection_count": total_connections,
            "avg_connection_strength": round(avg_strength, 3),
            "pending_tasks": len(self.task_queue),
            "feedback_count": len(self.feedback_history)
        }

    def save_state(self, filepath: str) -> bool:
        """
        Save platform state to JSON file.
        
        Args:
            filepath: Path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = {
                "domain": self.domain,
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "name": node.name,
                        "type": node.node_type,
                        "attributes": node.attributes,
                        "connections": node.connections,
                        "last_updated": node.last_updated.isoformat()
                    }
                    for node in self.knowledge_graph.values()
                ],
                "feedback_history": self.feedback_history
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"Saved platform state to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
            return False

    def load_state(self, filepath: str) -> bool:
        """
        Load platform state from JSON file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
                
            self.domain = state["domain"]
            self.knowledge_graph = {}
            
            for node_data in state["nodes"]:
                node = KnowledgeNode(
                    node_id=node_data["node_id"],
                    name=node_data["name"],
                    node_type=node_data["type"],
                    attributes=node_data["attributes"],
                    connections=node_data["connections"],
                    last_updated=datetime.fromisoformat(node_data["last_updated"])
                )
                
                if node.validate():
                    self.knowledge_graph[node.node_id] = node
                    
            self.feedback_history = state.get("feedback_history", [])
            logger.info(f"Loaded {len(self.knowledge_graph)} nodes from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load state: {str(e)}")
            return False


def demonstrate_usage():
    """
    Demonstrate platform usage with a cooking domain example.
    """
    # Initialize platform
    platform = SkillEvolutionPlatform(domain="cooking")
    
    # Generate innovation tasks
    tasks = platform.generate_innovation_tasks(num_tasks=3)
    
    print("\nGenerated Innovation Tasks:")
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.description} (Difficulty: {task.difficulty:.2f})")
        print(f"   Hypothesis: {task.hypothesis}")
    
    # Simulate human feedback
    if tasks:
        first_task = tasks[0]
        
        # Positive feedback with high rating
        success = platform.process_feedback(
            first_task.task_id, 
            "positive", 
            0.9
        )
        
        if success:
            print(f"\nProcessed feedback for: {first_task.description}")
            stats = platform.get_knowledge_stats()
            print(f"Knowledge graph stats: {stats}")
    
    # Save state
    platform.save_state("skill_evolution_state.json")
    
    # Demonstrate loading
    new_platform = SkillEvolutionPlatform(domain="cooking")
    new_platform.load_state("skill_evolution_state.json")
    print(f"\nLoaded platform with {len(new_platform.knowledge_graph)} nodes")


if __name__ == "__main__":
    demonstrate_usage()