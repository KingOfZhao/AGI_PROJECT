"""
Module: innovation_combination_engine.py
Description: AGI Skill for generating "Combinatorial Innovation" by analyzing
             skill node distances and complementarity.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    Represents a single skill node in the innovation graph.
    
    Attributes:
        id: Unique identifier for the skill.
        name: Human-readable name of the skill.
        vector: Multi-dimensional vector representing skill attributes 
                (e.g., domain, cognitive load, tool dependency).
        industry: The primary industry the skill belongs to.
    """
    id: str
    name: str
    vector: List[float]
    industry: str

@dataclass
class InnovationCombination:
    """
    Represents a recommended combination of skills.
    """
    skills: Tuple[SkillNode, SkillNode]
    distance_score: float
    complementarity_score: float
    innovation_probability: float
    description: str

class CombinatorialInnovationEngine:
    """
    Engine to process skill nodes and generate high-potential innovation combinations.
    
    This engine calculates the 'distance' (novelty) and 'complementarity' (synergy)
    between distinct skills to predict the probability of generating new value.
    
    Usage Example:
        >>> skills = [SkillNode("1", "Python", [0.9, 0.1], "Tech"), 
        ...           SkillNode("2", "Culinary", [0.1, 0.9], "Food")]
        >>> engine = CombinatorialInnovationEngine(skills)
        >>> recommendations = engine.generate_recommendations(top_k=5)
        >>> for rec in recommendations:
        ...     print(f"Combine {rec.skills[0].name} + {rec.skills[1].name}: {rec.innovation_probability}")
    """

    def __init__(self, skill_nodes: List[SkillNode]):
        """
        Initialize the engine with a list of skill nodes.
        
        Args:
            skill_nodes: A list of SkillNode objects.
        
        Raises:
            ValueError: If skill_nodes is empty or invalid.
        """
        if not skill_nodes:
            logger.error("Initialization failed: Skill node list is empty.")
            raise ValueError("Skill node list cannot be empty.")
        
        self.skill_nodes = skill_nodes
        self._node_index = {node.id: node for node in skill_nodes}
        logger.info(f"Engine initialized with {len(skill_nodes)} skill nodes.")

    def _validate_vector(self, vector: List[float]) -> bool:
        """Helper function to validate skill vectors."""
        if not isinstance(vector, list):
            return False
        if not all(isinstance(x, (float, int)) for x in vector):
            return False
        return True

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two non-zero vectors.
        
        Args:
            vec1: First vector.
            vec2: Second vector.
            
        Returns:
            Similarity score between -1 and 1.
        """
        if len(vec1) != len(vec2):
            logger.warning("Vector dimension mismatch in similarity calculation.")
            return 0.0
            
        dot_product = sum(p * q for p, q in zip(vec1, vec2))
        magnitude = math.sqrt(sum(p**2 for p in vec1)) * math.sqrt(sum(q**2 for q in vec2))
        
        if magnitude == 0:
            return 0.0
            
        return dot_product / magnitude

    def calculate_skill_distance(self, node_a: SkillNode, node_b: SkillNode) -> float:
        """
        Calculate the semantic distance between two skills.
        Distance is defined here as (1 - Cosine Similarity).
        Higher distance implies higher novelty (cross-domain).
        
        Args:
            node_a: First skill node.
            node_b: Second skill node.
            
        Returns:
            float: Distance score between 0.0 and 2.0.
        """
        if not (self._validate_vector(node_a.vector) and self._validate_vector(node_b.vector)):
            return 0.0
            
        similarity = self._cosine_similarity(node_a.vector, node_b.vector)
        return 1.0 - similarity

    def calculate_complementarity(self, node_a: SkillNode, node_b: SkillNode) -> float:
        """
        Calculate the complementarity (synergy potential) between two skills.
        
        Logic:
        Skills from different industries but serving similar high-level goals 
        (abstracted here) have high complementarity.
        For this simulation, we use a heuristic: 
        High distance + Different Industry = High Complementarity potential,
        but penalize total lack of correlation.
        
        Args:
            node_a: First skill node.
            node_b: Second skill node.
            
        Returns:
            float: Complementarity score between 0.0 and 1.0.
        """
        # Heuristic: Skills from different industries have higher synergy potential
        industry_bonus = 0.0
        if node_a.industry != node_b.industry:
            industry_bonus = 0.4
            
        # Check for orthogonal dimensions in the vector
        # (Simplified logic: identify if they have non-overlapping strong points)
        overlap = sum(1 for a, b in zip(node_a.vector, node_b.vector) if a > 0.5 and b > 0.5)
        
        # Penalize if they overlap too much (competition) or too little (irrelevance)
        synergy_factor = 1.0 / (1.0 + abs(2.0 - overlap)) # Arbitrary scaling
        
        score = min(1.0, industry_bonus + synergy_factor)
        return score

    def predict_innovation_probability(self, distance: float, complementarity: float) -> float:
        """
        Predict the probability of generating new value based on metrics.
        
        Formula (Sigmoid based):
        P = 1 / (1 + e^(-(Distance * Weight + Complementarity * Weight - Bias)))
        
        Args:
            distance: The distance score between skills.
            complementarity: The complementarity score.
            
        Returns:
            float: Probability between 0.0 and 1.0.
        """
        # Weights can be tuned based on historical data
        w_dist = 0.6
        w_comp = 1.2
        bias = 1.0
        
        z = (distance * w_dist) + (complementarity * w_comp) - bias
        probability = 1 / (1 + math.exp(-z))
        
        return probability

    def generate_recommendations(self, top_k: int = 10) -> List[InnovationCombination]:
        """
        Main Generator Function: Scans the node graph and generates top innovation combinations.
        
        Process:
        1. Iterate through unique pairs of nodes.
        2. Calculate Distance and Complementarity.
        3. Predict Innovation Probability.
        4. Sort and return top K results.
        
        Args:
            top_k: Number of top recommendations to return.
            
        Returns:
            List[InnovationCombination]: Sorted list of recommendations.
        """
        logger.info(f"Starting combinatorial analysis on {len(self.skill_nodes)} nodes...")
        candidates = []
        
        # Brute-force pair analysis (O(N^2))
        # Note: For 1680 nodes, this is ~1.4M pairs, acceptable for batch processing.
        # Optimization: Vectorized matrix multiplication could be used for production.
        
        count = 0
        for i in range(len(self.skill_nodes)):
            for j in range(i + 1, len(self.skill_nodes)):
                node_a = self.skill_nodes[i]
                node_b = self.skill_nodes[j]
                
                try:
                    dist = self.calculate_skill_distance(node_a, node_b)
                    comp = self.calculate_complementarity(node_a, node_b)
                    prob = self.predict_innovation_probability(dist, comp)
                    
                    # Filter low probability combinations early to save memory
                    if prob > 0.1:
                        desc = f"Combining {node_a.industry}('{node_a.name}') with {node_b.industry}('{node_b.name}')"
                        combo = InnovationCombination(
                            skills=(node_a, node_b),
                            distance_score=dist,
                            complementarity_score=comp,
                            innovation_probability=prob,
                            description=desc
                        )
                        candidates.append(combo)
                        count += 1
                except Exception as e:
                    logger.error(f"Error processing pair {node_a.id}-{node_b.id}: {e}")
                    continue

        logger.info(f"Analysis complete. Found {count} potential combinations.")
        
        # Sort by probability descending
        candidates.sort(key=lambda x: x.innovation_probability, reverse=True)
        
        return candidates[:top_k]

# --- Data Generation Helper (For Demonstration) ---
def generate_mock_data(num_nodes: int = 1680) -> List[SkillNode]:
    """
    Generates mock skill nodes for testing the engine.
    """
    industries = ["Tech", "Health", "Art", "Finance", "Education", "Engineering", "Culinary"]
    skills = []
    
    for i in range(num_nodes):
        # Create a random 5-dimensional feature vector
        vector = [random.uniform(0, 1) for _ in range(5)]
        industry = random.choice(industries)
        
        skills.append(SkillNode(
            id=f"skill_{i}",
            name=f"Skill_{i}_{industry}",
            vector=vector,
            industry=industry
        ))
    return skills

if __name__ == "__main__":
    # Main execution block
    print("Initializing Combinatorial Innovation Engine...")
    
    # 1. Generate mock data
    mock_skills = generate_mock_data(100) # Using 100 for quick demo, set to 1680 for full test
    
    # 2. Initialize Engine
    engine = CombinatorialInnovationEngine(mock_skills)
    
    # 3. Generate Recommendations
    top_innovations = engine.generate_recommendations(top_k=5)
    
    print("\n--- Top Innovation Recommendations ---")
    for idx, innovation in enumerate(top_innovations):
        print(f"Rank {idx+1}: {innovation.description}")
        print(f"   - Probability: {innovation.innovation_probability:.4f}")
        print(f"   - Novelty (Distance): {innovation.distance_score:.4f}")
        print(f"   - Synergy (Complementarity): {innovation.complementarity_score:.4f}")
        print("-" * 40)