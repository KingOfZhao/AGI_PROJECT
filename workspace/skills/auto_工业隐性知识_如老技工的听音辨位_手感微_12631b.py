"""
SKILL: Industrial Tacit Knowledge Encoder (Human-Machine Symbiosis Encoder)
ID: auto_工业隐性知识_如老技工的听音辨位_手感微_12631b
Domain: Cognitive Science / Industrial AI

Description:
    This module implements a 'Human-Machine Symbiosis Encoder' designed to translate
    unstructured, tacit industrial knowledge (e.g., a senior technician's verbal
    descriptions like "a bit tight", "sounds scratchy") into structured, digitized
    vectors with explicit physical boundaries (e.g., Torque Nm range).
    
    It bridges the gap between 'Subjective Perception' (Fuzzy) and 'Objective Physics' (Precise)
    using a Fuzzy Logic Mapping Layer and aligns the output with existing concept nodes.
"""

import logging
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Data Structures ---

class KnowledgeDomain(Enum):
    MECHANICAL = "mechanical"
    ACOUSTIC = "acoustic"
    TACTILE = "tactile"
    VISUAL = "visual"

@dataclass
class PhysicalConstraint:
    """Represents the objective physical boundaries."""
    unit: str
    min_val: float
    max_val: float
    safety_tolerance: float = 0.05  # 5% safety buffer

@dataclass
class SubjectiveInput:
    """Represents the raw human input."""
    description: str
    intensity: float  # 0.0 to 1.0 (e.g., "slightly"=0.3, "very"=0.9)
    domain: KnowledgeDomain
    context_tags: List[str] = field(default_factory=list)

@dataclass
class KnowledgeVector:
    """The final structured output."""
    vector_id: str
    semantic_embedding: np.ndarray
    physical_range: Tuple[float, float]
    unit: str
    aligned_nodes: List[str]
    confidence: float

# --- Helper Functions ---

def validate_intensity(intensity: float) -> bool:
    """
    Validate if the intensity value is within the standard [0.0, 1.0] range.
    
    Args:
        intensity (float): The subjective intensity score.
        
    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if not (0.0 <= intensity <= 1.0):
        logger.error(f"Intensity out of bounds: {intensity}")
        raise ValueError(f"Intensity must be between 0.0 and 1.0, got {intensity}")
    return True

def load_semantic_alignment_matrix(nodes_count: int = 2852) -> np.ndarray:
    """
    Simulates loading a pre-trained semantic alignment matrix.
    In a real scenario, this would load an embedding model (e.g., SentenceTransformers).
    
    Args:
        nodes_count (int): Number of concept nodes in the knowledge graph.
        
    Returns:
        np.ndarray: A random normalized vector representing the semantic alignment.
    """
    logger.debug(f"Generating semantic alignment vector for {nodes_count} nodes.")
    # Generate a random vector for simulation purposes
    vec = np.random.rand(nodes_count)
    return vec / np.linalg.norm(vec)

# --- Core Logic Classes ---

class FuzzyLogicMapper:
    """
    Handles the translation from subjective descriptions to physical value adjustments.
    Implements the 'Intermediate Layer' of the encoder.
    """
    
    def __init__(self):
        # Heuristic mapping: How much a "subjective unit" changes a "physical unit"
        # In reality, this would be a trained model.
        self.modifier_mapping = {
            "tight": 1.2,
            "loose": 0.8,
            "smooth": 1.0,
            "rough": 1.1,
            "hot": 1.3,
            "noisy": 1.1
        }
        
    def map_to_physical_range(
        self, 
        subjective_input: SubjectiveInput, 
        base_constraint: PhysicalConstraint
    ) -> Tuple[float, float]:
        """
        Maps subjective description to a specific physical range.
        
        Args:
            subjective_input (SubjectiveInput): The human input.
            base_constraint (PhysicalConstraint): The standard operating physical limits.
            
        Returns:
            Tuple[float, float]: The calculated [min, max] physical range.
        """
        try:
            # Determine modifier based on description
            modifier = 1.0
            desc_lower = subjective_input.description.lower()
            
            for key, val in self.modifier_mapping.items():
                if key in desc_lower:
                    modifier = val
                    break
            
            # Calculate the target value based on intensity
            # Higher intensity pushes the value further from the median
            range_span = base_constraint.max_val - base_constraint.min_val
            median_val = (base_constraint.max_val + base_constraint.min_val) / 2
            
            # Calculate delta: intensity * range_span * (modifier - 1.0 normalization)
            # This is a simplified fuzzy logic formula for demonstration
            delta = (subjective_input.intensity - 0.5) * 2 * range_span * (modifier - 1.0) * 2
            target_val = median_val + delta
            
            # Calculate bounds around the target (uncertainty decreases with confidence)
            uncertainty = 0.1 * (1.1 - subjective_input.intensity) # Higher intensity = more specific
            bound_span = range_span * uncertainty
            
            min_res = max(base_constraint.min_val, target_val - bound_span)
            max_res = min(base_constraint.max_val, target_val + bound_span)
            
            logger.info(f"Mapped '{desc_lower}' (Int: {subjective_input.intensity}) to range [{min_res:.2f}, {max_res:.2f}]")
            return (min_res, max_res)
            
        except Exception as e:
            logger.error(f"Error in fuzzy mapping: {e}")
            # Fallback to safe default
            return (base_constraint.min_val, base_constraint.max_val)

class KnowledgeEncoder:
    """
    Main class for the Human-Machine Symbiosis Encoder.
    """
    
    def __init__(self, knowledge_graph_nodes: List[str]):
        """
        Initialize the encoder.
        
        Args:
            knowledge_graph_nodes (List[str]): List of concept IDs for semantic alignment.
        """
        self.nodes = knowledge_graph_nodes
        self.node_count = len(knowledge_graph_nodes)
        self.mapper = FuzzyLogicMapper()
        logger.info(f"KnowledgeEncoder initialized with {self.node_count} concept nodes.")
        
    def encode(
        self, 
        raw_input: Dict[str, Any], 
        constraints: Dict[str, Any]
    ) -> Optional[KnowledgeVector]:
        """
        Main entry point. Encodes raw human input into a structured knowledge vector.
        
        Args:
            raw_input (Dict): Contains 'desc', 'intensity', 'domain'.
            constraints (Dict): Contains 'unit', 'min', 'max'.
            
        Returns:
            KnowledgeVector: The structured digital vector.
        """
        try:
            # 1. Data Validation and Parsing
            domain = KnowledgeDomain(raw_input.get('domain', 'mechanical'))
            subj_input = SubjectiveInput(
                description=raw_input['desc'],
                intensity=raw_input['intensity'],
                domain=domain,
                context_tags=raw_input.get('tags', [])
            )
            validate_intensity(subj_input.intensity)
            
            phys_const = PhysicalConstraint(
                unit=constraints['unit'],
                min_val=constraints['min'],
                max_val=constraints['max']
            )
            
            # 2. Fuzzy Mapping (Subjective -> Objective)
            phys_range = self.mapper.map_to_physical_range(subj_input, phys_const)
            
            # 3. Semantic Alignment (Text -> Vector)
            # Simulating the alignment with concept nodes
            semantic_vec = self._generate_aligned_vector(subj_input.description)
            
            # 4. Find relevant aligned nodes
            aligned_indices = self._find_top_k_nodes(semantic_vec, k=3)
            
            return KnowledgeVector(
                vector_id=f"vec_{hash(raw_input['desc']) % 10000}",
                semantic_embedding=semantic_vec,
                physical_range=phys_range,
                unit=phys_const.unit,
                aligned_nodes=[self.nodes[i] for i in aligned_indices],
                confidence=0.85 # Simulated confidence
            )
            
        except ValueError as ve:
            logger.warning(f"Validation failed: {ve}")
            return None
        except KeyError as ke:
            logger.error(f"Missing required key in input: {ke}")
            return None
        except Exception as e:
            logger.exception("Unexpected error during encoding.")
            return None
            
    def _generate_aligned_vector(self, text: str) -> np.ndarray:
        """
        Internal helper to generate vector aligned with the 2852 concept nodes.
        """
        # In a real implementation, use BERT/Word2Vec here.
        # We simulate by hashing the text to seed the random generator for reproducibility
        seed = sum(ord(c) for c in text)
        rng = np.random.default_rng(seed)
        vec = rng.random(self.node_count)
        return vec / np.linalg.norm(vec)
        
    def _find_top_k_nodes(self, vector: np.ndarray, k: int) -> List[int]:
        """
        Find the top K nodes that semantically align with the vector.
        """
        # Simulation: return random indices representing alignment
        return list(range(k))

# --- Usage Example ---

if __name__ == "__main__":
    # Mock Data: Existing Concept Nodes in the AGI System
    CONCEPT_NODES = [f"concept_node_{i}" for i in range(2852)]
    
    # Initialize Encoder
    encoder = KnowledgeEncoder(CONCEPT_NODES)
    
    # Example 1: Old technician feeling "a bit tight"
    tech_input = {
        "desc": "感觉轴承稍微有点紧，声音发闷",  # "Bearing feels a bit tight, sound is muffled"
        "intensity": 0.7,  # Strong sensation but not extreme
        "domain": "mechanical",
        "tags": ["bearing", "assembly"]
    }
    
    physical_limits = {
        "unit": "Nm",
        "min": 5.0,
        "max": 10.0
    }
    
    print("-" * 30)
    print("Processing Technician Input...")
    result = encoder.encode(tech_input, physical_limits)
    
    if result:
        print(f"Input Description: {tech_input['desc']}")
        print(f"Output Physical Range: {result.physical_range[0]:.2f} - {result.physical_range[1]:.2f} {result.unit}")
        print(f"Aligned Concepts: {result.aligned_nodes}")
        print(f"Vector Shape: {result.semantic_embedding.shape}")
        print(f"Confidence: {result.confidence}")
        
    # Example 2: Invalid Input handling
    print("-" * 30)
    print("Processing Invalid Input...")
    bad_input = {
        "desc": "Something wrong",
        "intensity": 1.5,  # Invalid intensity
        "domain": "mechanical"
    }
    encoder.encode(bad_input, physical_limits)