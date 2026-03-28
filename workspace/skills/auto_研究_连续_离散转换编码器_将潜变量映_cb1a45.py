"""
Module: auto_research_continuous_discrete_encoder_cb1a45
Description: Implements research-grade Continuous-to-Discrete Transition Encoders
             capable of mapping high-dimensional continuous latent variables
             into a finite set of executable action primitives.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Data Models ---

class LatentVector(BaseModel):
    """Represents a continuous latent vector input."""
    data: List[float] = Field(..., min_items=1, description="The continuous vector data.")
    source: str = Field("unknown", description="Origin of the latent vector.")

    class Config:
        arbitrary_types_allowed = True

class ActionPrimitive(BaseModel):
    """Represents a discrete action primitive output."""
    id: int
    label: str
    confidence: float
    embedding_hash: int


# --- Core Classes ---

class ContinuousDiscreteEncoder:
    """
    A sophisticated encoder that transforms continuous latent spaces into discrete action tokens.
    
    This implementation utilizes a nearest-neighbor lookup approach against a codebook
    of pre-defined action embeddings (VQ-VAE style concept).
    
    Attributes:
        embedding_dim (int): Dimensionality of the latent space.
        codebook_size (int): Number of discrete action primitives available.
        codebook (np.ndarray): The matrix of learnable embeddings representing actions.
    """

    def __init__(self, embedding_dim: int = 64, codebook_size: int = 128, seed: int = 42):
        """
        Initialize the Encoder with random codebook weights.
        
        Args:
            embedding_dim (int): Size of the input vectors.
            codebook_size (int): Number of discrete actions.
            seed (int): Random seed for reproducibility.
        """
        self.embedding_dim = embedding_dim
        self.codebook_size = codebook_size
        self._rng = np.random.default_rng(seed)
        
        # Initialize codebook with random vectors (simulating untrained weights)
        self.codebook = self._rng.normal(0, 1, size=(codebook_size, embedding_dim))
        logger.info(f"Encoder initialized with codebook shape: {self.codebook.shape}")

    def _validate_input_shape(self, vector: np.ndarray) -> None:
        """Validates that the input vector matches the embedding dimension."""
        if vector.shape != (self.embedding_dim,):
            error_msg = f"Input vector dim mismatch. Expected {(self.embedding_dim,)}, got {vector.shape}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def quantize(self, continuous_vector: np.ndarray) -> Tuple[int, np.ndarray]:
        """
        Core Function 1: Maps a single continuous vector to the nearest discrete code.
        
        Args:
            continuous_vector (np.ndarray): The input latent vector.
            
        Returns:
            Tuple[int, np.ndarray]: The index of the best match and the discrete embedding vector.
        
        Raises:
            ValueError: If input dimensions do not match model configuration.
        """
        logger.debug("Starting quantization process...")
        
        if not isinstance(continuous_vector, np.ndarray):
            continuous_vector = np.array(continuous_vector, dtype=np.float32)
            
        try:
            self._validate_input_shape(continuous_vector)
        except ValueError as e:
            logger.error(f"Input validation failed: {e}")
            raise

        # Calculate Euclidean distances to all codebook entries
        # Using broadcasting: (K, D) - (D,) -> (K, D) -> sum over D -> (K,)
        distances = np.sum((self.codebook - continuous_vector) ** 2, axis=1)
        
        # Find index of minimum distance
        best_idx = np.argmin(distances)
        best_embedding = self.codebook[best_idx]
        
        logger.info(f"Vector mapped to action primitive index: {best_idx}")
        return int(best_idx), best_embedding

    def batch_encode(self, vectors: List[np.ndarray]) -> List[ActionPrimitive]:
        """
        Core Function 2: Processes a batch of continuous vectors into Action Primitives.
        
        Args:
            vectors (List[np.ndarray]): A list of numpy arrays.
            
        Returns:
            List[ActionPrimitive]: List of structured action objects.
        """
        if not vectors:
            logger.warning("Batch encode called with empty list.")
            return []

        results = []
        for i, vec in enumerate(vectors):
            try:
                idx, embedding = self.quantize(vec)
                primitive = ActionPrimitive(
                    id=idx,
                    label=f"ACTION_{idx:03d}",
                    confidence=float(1.0 / (1.0 + np.linalg.norm(vec - embedding))), # Proxy confidence
                    embedding_hash=hash(embedding.tobytes())
                )
                results.append(primitive)
            except Exception as e:
                logger.error(f"Failed to encode vector at index {i}: {e}")
                # Optionally append a null primitive or skip
                continue
                
        return results

    def decode_primitive(self, primitive_id: int) -> np.ndarray:
        """
        Helper Function: Retrieves the continuous embedding for a given primitive ID.
        """
        if not 0 <= primitive_id < self.codebook_size:
            raise IndexError(f"Primitive ID {primitive_id} out of bounds for codebook size {self.codebook_size}.")
        return self.codebook[primitive_id]


# --- Utility / Helper Functions ---

def generate_synthetic_latent_stream(count: int, dim: int, noise_level: float = 0.1) -> List[LatentVector]:
    """
    Helper Function: Generates synthetic data to simulate AGI latent outputs.
    
    Args:
        count (int): Number of vectors to generate.
        dim (int): Dimension of each vector.
        noise_level (float): Standard deviation of noise.
        
    Returns:
        List[LatentVector]: Validated list of data objects.
    """
    logger.info(f"Generating {count} synthetic latent vectors...")
    data_stream = []
    rng = np.random.default_rng(0)
    
    # Create a "True" signal that we want to encode
    base_signal = rng.normal(0, 1, dim)
    
    for i in range(count):
        # Add noise to base signal
        noisy_vector = base_signal + rng.normal(0, noise_level, dim)
        
        # Create Pydantic model for validation
        vec_obj = LatentVector(
            data=noisy_vector.tolist(),
            source=f"synthetic_node_{i%5}"
        )
        data_stream.append(vec_obj)
        
    return data_stream


# --- Main Execution Block ---

def main():
    """
    Usage Example:
    Demonstrates the full pipeline from synthetic data generation to discrete encoding.
    """
    CONFIG = {
        "embedding_dim": 32,
        "codebook_size": 64
    }
    
    try:
        # 1. Initialize System
        logger.info("Initializing Continuous-Discrete Encoder System...")
        encoder = ContinuousDiscreteEncoder(**CONFIG)
        
        # 2. Generate Input Data (Simulating AGI Thought Process)
        raw_data = generate_synthetic_latent_stream(count=5, dim=CONFIG["embedding_dim"])
        
        # 3. Convert to Numpy for Processing
        input_vectors = [np.array(d.data) for d in raw_data]
        
        # 4. Perform Batch Encoding
        logger.info("Processing batch encoding...")
        action_primitives = encoder.batch_encode(input_vectors)
        
        # 5. Output Results
        print("\n--- Encoding Results ---")
        for i, primitive in enumerate(action_primitives):
            print(f"Input {i}: Mapped to {primitive.label} (ID: {primitive.id})")
            print(f"  Confidence: {primitive.confidence:.4f}")
            
            # Verify reconstruction
            reconstructed = encoder.decode_primitive(primitive.id)
            print(f"  Reconstruction Norm: {np.linalg.norm(reconstructed):.4f}\n")

        # 6. Boundary Check Example
        logger.info("Testing boundary checks...")
        try:
            bad_vector = np.random.rand(CONFIG["embedding_dim"] + 10)
            encoder.quantize(bad_vector)
        except ValueError as e:
            logger.info(f"Caught expected error: {e}")

    except ValidationError as ve:
        logger.critical(f"Data validation failed during execution: {ve}")
    except Exception as e:
        logger.critical(f"System crash: {e}", exc_info=True)

if __name__ == "__main__":
    main()