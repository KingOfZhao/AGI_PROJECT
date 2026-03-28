"""
Module: auto_针对现有1481个skill_如何构建一_3a22ff
Description: Implements a 'Skill Composition Evolution' algorithm using Graph Neural Networks (GNN).
             When a single skill fails to solve a given task, this system explores the existing
             skill graph to find optimal combination paths and generates new 'composite skill' nodes.

Domain: Evolutionary Computation / AGI Architecture
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Data Structures ---

@dataclass
class Skill:
    """
    Represents a primitive skill node in the graph.
    
    Attributes:
        id (str): Unique identifier for the skill.
        description (str): Human-readable description of the skill.
        embedding (np.ndarray): Feature vector representing the skill's semantic capability.
    """
    id: str
    description: str
    embedding: np.ndarray = field(default_factory=lambda: np.random.rand(64))

    def __post_init__(self):
        if not isinstance(self.embedding, np.ndarray):
            raise TypeError("Embedding must be a numpy array.")
        if self.embedding.shape != (64,):
            # Auto-correct or raise error for consistency in GNN input
            self.embedding = np.random.rand(64)
            logger.warning(f"Skill {self.id} embedding reshaped/reinitialized to (64,).")


@dataclass
class Task:
    """
    Represents a target problem to be solved.
    
    Attributes:
        id (str): Task identifier.
        requirement_vector (np.ndarray): The vectorized representation of the task requirements.
    """
    id: str
    requirement_vector: np.ndarray


class SkillGraphGNN(nn.Module):
    """
    A Graph Convolutional Network model for learning skill node embeddings
    and predicting compatibility scores for composition.
    """
    def __init__(self, input_dim: int = 64, hidden_dim: int = 128, output_dim: int = 64):
        super(SkillGraphGNN, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)
        logger.info("SkillGraphGNN initialized with GCN layers.")

    def forward(self, data: Data) -> torch.Tensor:
        """
        Forward pass through the GNN.
        
        Args:
            data (Data): PyTorch Geometric Data object containing x (features) and edge_index.
            
        Returns:
            torch.Tensor: Updated node embeddings.
        """
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, training=self.training)
        x = self.conv2(x, edge_index)
        return x


class SkillEvolutionSystem:
    """
    Main system class for managing skills, running the GNN, and evolving new composite skills.
    """

    def __init__(self, initial_skills: List[Skill]):
        """
        Initializes the system with a list of primitive skills.
        
        Args:
            initial_skills (List[Skill]): List of 1481 existing skills.
        """
        if not initial_skills:
            raise ValueError("Initial skill list cannot be empty.")
        
        self.skills: Dict[str, Skill] = {s.id: s for s in initial_skills}
        self.skill_counter = len(initial_skills)
        
        # Initialize GNN components
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.gnn_model = SkillGraphGNN().to(self.device)
        self.graph_data: Optional[Data] = None
        
        logger.info(f"System initialized with {len(self.skills)} skills on device: {self.device}")

    def _validate_task(self, task: Task) -> None:
        """Validates the task input data."""
        if not isinstance(task, Task):
            raise TypeError("Input must be a Task object.")
        if task.requirement_vector is None or len(task.requirement_vector) == 0:
            raise ValueError("Task requirement vector cannot be empty.")

    def build_skill_graph(self) -> None:
        """
        Constructs the graph data structure from the current skill database.
        Nodes are skills, edges represent functional proximity (mocked for this example).
        In a real scenario, edges would be based on semantic similarity or historical co-usage.
        """
        logger.info("Building skill graph structure...")
        node_features = []
        node_ids = []
        
        for skill_id, skill in self.skills.items():
            node_features.append(skill.embedding)
            node_ids.append(skill_id)
            
        x = torch.tensor(np.array(node_features), dtype=torch.float32)
        
        # Generate mock edges based on random proximity for demonstration
        # In production, use k-NN on embeddings
        num_nodes = len(self.skills)
        edges = []
        for i in range(num_nodes):
            # Connect to random 3 neighbors
            targets = random.sample(range(num_nodes), min(3, num_nodes - 1))
            for t in targets:
                edges.append([i, t])
        
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        
        self.graph_data = Data(x=x, edge_index=edge_index).to(self.device)
        logger.info(f"Graph built: {num_nodes} nodes, {edge_index.size(1)} edges.")

    def evolve_composite_skill(self, task: Task, top_k: int = 3) -> Optional[Tuple[Skill, float]]:
        """
        Core Algorithm: Uses GNN to explore the graph and find the best combination of skills
        to satisfy the task requirements. If successful, creates and registers a new composite skill.
        
        Args:
            task (Task): The problem to solve.
            top_k (int): Number of candidate skills to combine.
            
        Returns:
            Optional[Tuple[Skill, float]]: The new composite skill and its confidence score, or None if failed.
        """
        self._validate_task(task)
        if self.graph_data is None:
            self.build_skill_graph()

        logger.info(f"Evolving solution for task {task.id}...")

        # 1. Update embeddings via GNN
        self.gnn_model.eval()
        with torch.no_grad():
            refined_embeddings = self.gnn_model(self.graph_data)
        
        # 2. Find candidates using GNN-refined embeddings
        task_tensor = torch.tensor(task.requirement_vector, dtype=torch.float32).to(self.device)
        
        # Calculate cosine similarity between task and all skills
        # Normalize vectors
        task_norm = F.normalize(task_tensor.unsqueeze(0), p=2, dim=1)
        skill_norms = F.normalize(refined_embeddings, p=2, dim=1)
        
        similarities = torch.mm(task_norm, skill_norms.t()).squeeze(0)
        
        # Get top K indices
        top_indices = torch.topk(similarities, k=top_k).indices.cpu().numpy()
        
        # 3. Check if the top skill alone is sufficient (threshold check)
        best_score = similarities[top_indices[0]].item()
        if best_score > 0.95:
            logger.info(f"Single skill match found with score {best_score:.4f}. No evolution needed.")
            skill_list = list(self.skills.values())
            return skill_list[top_indices[0]], best_score

        logger.info(f"Single skill insufficient (Score: {best_score:.4f}). Combining top {top_k} skills...")
        
        # 4. Generate Composite Skill
        # Heuristic: Average the embeddings of top_k skills and add noise for mutation
        selected_embeddings = refined_embeddings[top_indices]
        new_embedding_tensor = torch.mean(selected_embeddings, dim=0)
        
        # Mutation step (Evolutionary logic)
        mutation_noise = torch.randn(new_embedding_tensor.shape).to(self.device) * 0.05
        new_embedding_tensor += mutation_noise
        
        # Create new Skill object
        skill_list = list(self.skills.values())
        parent_ids = [skill_list[i].id for i in top_indices]
        
        self.skill_counter += 1
        new_skill_id = f"composite_{self.skill_counter}"
        new_skill_desc = f"Composite of: {', '.join(parent_ids)}"
        
        new_skill = Skill(
            id=new_skill_id,
            description=new_skill_desc,
            embedding=new_embedding_tensor.cpu().numpy()
        )
        
        # 5. Register new skill into the graph
        self.skills[new_skill_id] = new_skill
        logger.info(f"Generated new composite skill: {new_skill_id}")
        
        # Rebuild graph to include new node (In production, use dynamic graph updates)
        self.build_skill_graph()
        
        # Calculate confidence score (simple heuristic: mean similarity of parents)
        confidence_score = torch.mean(similarities[top_indices]).item()
        
        return new_skill, confidence_score

    def get_skill_count(self) -> int:
        """Helper function to return current number of skills."""
        return len(self.skills)


# --- Usage Example ---

def initialize_mock_skills(num_skills: int = 1481) -> List[Skill]:
    """Generates mock data for testing."""
    skills = []
    for i in range(num_skills):
        skills.append(Skill(
            id=f"skill_{i}",
            description=f"Capability vector {i}",
            embedding=np.random.rand(64)
        ))
    return skills

if __name__ == "__main__":
    try:
        # 1. Setup
        logger.info("Starting Skill Evolution System Demo")
        mock_skills = initialize_mock_skills(1481)
        system = SkillEvolutionSystem(mock_skills)
        
        # 2. Build Graph
        system.build_skill_graph()
        
        # 3. Define a complex task
        # Let's create a task vector that is somewhat similar to a random existing skill but not exact
        target_skill_idx = 50
        noise = np.random.normal(0, 0.5, 64)
        task_vector = mock_skills[target_skill_idx].embedding + noise
        
        difficult_task = Task(id="task_001_complex", requirement_vector=task_vector)
        
        # 4. Run Evolution
        result = system.evolve_composite_skill(difficult_task, top_k=3)
        
        if result:
            new_skill, score = result
            print(f"\n--- Result ---")
            print(f"Solution found for Task {difficult_task.id}")
            print(f"Generated Skill ID: {new_skill.id}")
            print(f"Description: {new_skill.description}")
            print(f"Confidence Score: {score:.4f}")
            print(f"Total Skills in System: {system.get_skill_count()}")
        else:
            print("Failed to generate a solution.")

    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}", exc_info=True)