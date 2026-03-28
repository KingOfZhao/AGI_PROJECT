"""
Module: implicit_knowledge_vectorization
Description: This module transforms unstructured, hard-to-articulate human 'tacit knowledge'
             (such as craftsmanship touch, intuition, muscle memory) into machine-computable,
             replicable 'explicit vectors'.

             It constructs a 'Joint Embedding Space' fusing Electromyography (EMG), Force Sensing,
             Visual Streams, and Natural Language Fuzzy References. By aligning high-dimensional
             vectors, it translates a master's "feeling off" into specific feature vector deviations,
             enabling the digital preservation and reuse of tacit knowledge.

Domain: Cross-Domain (Biometrics, Robotics, NLP, Computer Vision)
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, Tuple, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SensorSample(BaseModel):
    """Represents a single timestamped multi-modal sensor reading."""
    timestamp: float = Field(..., description="Unix timestamp of the reading")
    emg_data: List[float] = Field(..., min_items=1, description="List of EMG voltage readings")
    force_vector: List[float] = Field(..., min_items=3, max_items=3, description="Force in x, y, z (Newtons)")
    visual_descriptor: Optional[List[float]] = Field(None, description="Latent visual vector from CNN")

class TacitKnowledgeConfig(BaseModel):
    """Configuration for the vectorization process."""
    emg_dim: int = Field(8, description="Number of EMG channels")
    vector_dim: int = Field(128, description="Dimension of the final unified vector")
    fusion_method: str = Field("concat_sigmoid", description="Method to fuse modalities")

# --- Core Class ---

class ImplicitKnowledgeVectorizer:
    """
    A system to convert implicit human physical skills into explicit vector representations.
    
    This class handles the fusion of disparate data sources (EMG, Force, Vision) into a
    unified latent space where 'intuition' can be measured as distance or deviation.
    """

    def __init__(self, config: TacitKnowledgeConfig):
        """
        Initialize the vectorizer with specific configurations.
        
        Args:
            config (TacitKnowledgeConfig): Configuration object defining dimensions and methods.
        """
        self.config = config
        self.is_calibrated = False
        # Initialize projection matrices (randomly for demo, would be trained in production)
        self._initialize_projection_matrices()
        logger.info("ImplicitKnowledgeVectorizer initialized with config: %s", config.dict())

    def _initialize_projection_matrices(self) -> None:
        """Initializes weights for mapping raw data to the joint embedding space."""
        np.random.seed(42)
        # Weights to map concatenated features to the unified vector space
        input_dim = (self.config.emg_dim * 2) + 3 + 64 # Assuming 64 visual dims
        self.projection_weights = np.random.randn(input_dim, self.config.vector_dim) * 0.01
        self.projection_bias = np.zeros(self.config.vector_dim)

    def _validate_input(self, data: Dict[str, Union[List[float], str]]) -> SensorSample:
        """
        Validates raw input dictionary and converts it to a SensorSample object.
        
        Args:
            data: Raw dictionary containing sensor readings.
            
        Returns:
            SensorSample: Validated data model instance.
            
        Raises:
            ValueError: If data format is invalid.
        """
        try:
            sample = SensorSample(**data)
            return sample
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise ValueError(f"Invalid sensor data format: {e}")

    def _extract_features(self, sample: SensorSample) -> np.ndarray:
        """
        Helper function to extract and normalize features from a single sample.
        
        Args:
            sample (SensorSample): Validated sensor data.
            
        Returns:
            np.ndarray: A concatenated array of raw features.
        """
        # 1. EMG Processing (Mockup: RMS calculation over window)
        emg_arr = np.array(sample.emg_data)
        emg_rms = np.sqrt(np.mean(emg_arr**2)) # Scalar
        # Replicate to match dimension expectation for demo purposes
        emg_features = np.full(self.config.emg_dim * 2, emg_rms) 

        # 2. Force Processing
        force_features = np.array(sample.force_vector)

        # 3. Visual Processing (Pad if missing)
        if sample.visual_descriptor:
            visual_features = np.array(sample.visual_descriptor)
        else:
            visual_features = np.zeros(64) # Default empty visual context
            
        # Ensure visual size matches expectation (pad/truncate)
        if len(visual_features) < 64:
            visual_features = np.pad(visual_features, (0, 64 - len(visual_features)))
        else:
            visual_features = visual_features[:64]

        return np.concatenate([emg_features, force_features, visual_features])

    def encode_tacit_state(self, sensor_data: Dict[str, Union[List[float], str]]) -> Tuple[np.ndarray, float]:
        """
        Core Function 1: Encodes the current multi-modal sensor state into a 'Skill Vector'.
        
        This represents the 'current feeling' or state of the operator.
        
        Args:
            sensor_data (Dict): Dictionary containing 'emg_data', 'force_vector', etc.
            
        Returns:
            Tuple[np.ndarray, float]: 
                - explicit_vector: The high-dimensional vector representing the skill state.
                - confidence_score: A metric indicating the reliability of the encoding (0.0 to 1.0).
                
        Raises:
            RuntimeError: If projection fails.
        """
        logger.info("Encoding tacit state...")
        
        # 1. Validate
        sample = self._validate_input(sensor_data)
        
        # 2. Feature Engineering
        try:
            raw_features = self._extract_features(sample)
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise RuntimeError("Feature extraction error")

        # 3. Projection to Joint Space
        # Simple linear projection followed by Tanh activation for bounded space
        unified_vector = np.tanh(np.dot(raw_features, self.projection_weights) + self.projection_bias)
        
        # 4. Calculate Confidence (Mockup: based on signal strength)
        signal_strength = np.linalg.norm(raw_features)
        confidence = min(1.0, signal_strength / 100.0) # Normalized heuristic
        
        logger.debug(f"Vector generated. Norm: {np.linalg.norm(unified_vector):.4f}")
        return unified_vector, confidence

    def compare_intuition(self, master_vector: np.ndarray, novice_vector: np.ndarray) -> Dict[str, float]:
        """
        Core Function 2: Quantifies the difference between a 'Master' state and a 'Novice' state.
        
        This function translates "It doesn't feel right" into specific vector deviations,
        identifying where the novice's muscle memory or intuition diverges from the master's.
        
        Args:
            master_vector (np.ndarray): The reference vector from the expert.
            novice_vector (np.ndarray): The vector from the learner/current attempt.
            
        Returns:
            Dict[str, float]: A dictionary containing:
                - 'cosine_distance': Semantic similarity of the skill state.
                - 'euclidean_deviation': Absolute magnitude of error.
                - 'skill_match_score': 0-100 score of how close the novice is to the master.
        """
        if master_vector.shape != novice_vector.shape:
            raise ValueError("Vector dimensions must match for comparison")

        logger.info("Comparing intuition vectors...")
        
        # Cosine Similarity
        dot_product = np.dot(master_vector, novice_vector)
        norm_master = np.linalg.norm(master_vector)
        norm_novice = np.linalg.norm(novice_vector)
        
        epsilon = 1e-8 # Prevent division by zero
        cosine_sim = dot_product / (norm_master * norm_novice + epsilon)
        cosine_dist = 1 - cosine_sim

        # Euclidean Distance
        euc_dist = np.linalg.norm(master_vector - novice_vector)

        # Skill Match Score (Heuristic: combination of cosine and magnitude)
        match_score = max(0, (1 - cosine_dist) * 100 - (euc_dist * 10))

        result = {
            "cosine_distance": float(cosine_dist),
            "euclidean_deviation": float(euc_dist),
            "skill_match_score": float(match_score)
        }
        
        logger.info(f"Comparison Result: Match Score {match_score:.2f}%")
        return result

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Configuration
    config = TacitKnowledgeConfig(emg_dim=4, vector_dim=64)
    
    # 2. Initialize Vectorizer
    vectorizer = ImplicitKnowledgeVectorizer(config)

    # 3. Simulate Master Data (The "Ideal" Feeling)
    master_raw_data = {
        "timestamp": datetime.now().timestamp(),
        "emg_data": [0.5, 0.6, 0.4, 0.5] * 10, # Simulated high tension
        "force_vector": [10.2, 0.1, 5.5],      # Specific force application
        "visual_descriptor": [0.1] * 64        # Ideal visual alignment
    }

    try:
        # Encode Master's Implicit Knowledge
        master_vec, _ = vectorizer.encode_tacit_state(master_raw_data)
        print(f"Master Vector Shape: {master_vec.shape}")

        # 4. Simulate Novice Data (The "Learning" Attempt)
        novice_raw_data = {
            "timestamp": datetime.now().timestamp(),
            "emg_data": [0.4, 0.5, 0.3, 0.4] * 10, # Slightly lower tension
            "force_vector": [9.8, 0.5, 5.1],      # Slightly off force
            "visual_descriptor": [0.1] * 64
        }

        # Encode Novice's State
        novice_vec, conf = vectorizer.encode_tacit_state(novice_raw_data)

        # 5. Compare and Quantify the "Gap"
        analysis = vectorizer.compare_intuition(master_vec, novice_vec)
        
        print("\n--- Tacit Knowledge Analysis ---")
        print(f"Novice Confidence: {conf:.2f}")
        print(f"Skill Match Score : {analysis['skill_match_score']:.2f}%")
        print(f"Intuition Gap (Cosine): {analysis['cosine_distance']:.4f}")
        print("-------------------------------")

    except (ValueError, RuntimeError) as e:
        print(f"Processing Error: {e}")