"""
Module: multimodal_intent_fusion.py

This module provides a robust framework for unifying multimodal user inputs
(text, sketches, voice, and mouse trajectories) into a single, structured
"Intent Tensor". It serves as a standardized input source for downstream
AGI code generation or task planning modules.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ValidationError, field_validator
from enum import Enum

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants and Configuration
# -----------------------------------------------------------------------------
EMBEDDING_DIM = 768  # Standard transformer dimension (e.g., BERT-base)
TEMPORAL_DIM = 128   # Standardized time steps for sequential data

class ModalityType(str, Enum):
    """Enumeration of supported input modalities."""
    TEXT = "text"
    SKETCH = "sketch"
    AUDIO = "audio"
    TRAJECTORY = "trajectory"

# -----------------------------------------------------------------------------
# Data Models (Validation)
# -----------------------------------------------------------------------------

class ModalityInput(BaseModel):
    """Base model for validating raw modality inputs."""
    modality_type: ModalityType
    data: Union[str, List[float], List[Tuple[float, float, float]]]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: float = Field(default=0.0, ge=0.0)

    @field_validator('data')
    @classmethod
    def validate_data_structure(cls, v, info):
        """Ensure data matches the modality type requirements."""
        m_type = info.data['modality_type']
        
        if m_type == ModalityType.TEXT:
            if not isinstance(v, str) or len(v) == 0:
                raise ValueError("Text modality requires non-empty string data.")
        elif m_type in [ModalityType.AUDIO, ModalityType.SKETCH]:
            if not isinstance(v, list):
                raise ValueError(f"{m_type} modality requires list data.")
        elif m_type == ModalityType.TRAJECTORY:
            if not isinstance(v, list) or (len(v) > 0 and not isinstance(v[0], (list, tuple))):
                raise ValueError("Trajectory modality requires list of coordinates.")
        return v

class IntentTensor(BaseModel):
    """Structured output representing the unified intent."""
    fused_embedding: np.ndarray
    modality_weights: Dict[str, float]
    attention_mask: np.ndarray
    
    class Config:
        arbitrary_types_allowed = True

# -----------------------------------------------------------------------------
# Core Functions
# -----------------------------------------------------------------------------

def _normalize_vector(vector: np.ndarray, target_dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Helper function to normalize vectors to a consistent dimension and magnitude.
    
    Args:
        vector (np.ndarray): Input vector (1D or 2D).
        target_dim (int): Target dimension for projection.
        
    Returns:
        np.ndarray: Normalized and projected vector.
    """
    if vector is None or vector.size == 0:
        logger.warning("Received empty vector for normalization, returning zero vector.")
        return np.zeros(target_dim)
    
    # Basic L2 normalization
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    vector = vector / norm
    
    # Simple projection/padding to match target dimension
    current_dim = vector.shape[-1]
    if current_dim < target_dim:
        # Pad with zeros
        padding = np.zeros(target_dim - current_dim)
        return np.concatenate([vector, padding])
    elif current_dim > target_dim:
        # Truncate or apply linear projection (truncation used here for simplicity)
        return vector[:target_dim]
    return vector

def encode_text_modality(text: str) -> np.ndarray:
    """
    Encodes text input into a semantic vector.
    
    Note: This mock simulates a Transformer encoder (e.g., BERT/CLIP).
    
    Args:
        text (str): The user's text query.
        
    Returns:
        np.ndarray: Semantic embedding vector.
    """
    logger.info(f"Encoding text modality: '{text[:50]}...'")
    # Mock encoding: Deterministic random vector based on string hash
    np.random.seed(hash(text) % (2**32))
    embedding = np.random.rand(EMBEDDING_DIM).astype(np.float32)
    return _normalize_vector(embedding)

def encode_visual_modality(sketch_data: List[float]) -> np.ndarray:
    """
    Encodes visual data (sketch/image) into a semantic vector.
    
    Note: This mock simulates a Visual Transformer (ViT) or Sketch-RNN output.
    
    Args:
        sketch_data (List[float]): Flattened sketch data or image features.
        
    Returns:
        np.ndarray: Visual embedding vector.
    """
    logger.info("Encoding visual/sketch modality...")
    if not sketch_data:
        return np.zeros(EMBEDDING_DIM)
    
    # Convert to numpy and normalize
    raw_vec = np.array(sketch_data, dtype=np.float32)
    # Simple projection simulation
    projection_weights = np.random.rand(len(raw_vec), EMBEDDING_DIM).astype(np.float32)
    embedding = np.mean(projection_weights * raw_vec[:, np.newaxis], axis=0)
    
    return _normalize_vector(embedding)

def encode_temporal_modality(sequence_data: List[Tuple], modality_type: str) -> np.ndarray:
    """
    Encodes temporal sequences (Audio or Mouse Trajectory) into a fixed vector.
    
    Uses a simulated RNN/LSTM processing approach.
    
    Args:
        sequence_data (List[Tuple]): Time-series data points.
        modality_type (str): 'audio' or 'trajectory'.
        
    Returns:
        np.ndarray: Temporal embedding vector.
    """
    logger.info(f"Encoding {modality_type} modality...")
    if not sequence_data:
        return np.zeros(EMBEDDING_DIM)
    
    try:
        # Convert variable length sequence to numpy
        # Handle (x, y, t) or (frequency, amplitude) tuples
        arr = np.array(sequence_data, dtype=np.float32)
        
        # Basic simulation of temporal aggregation (e.g., mean pooling over time)
        # In a real system, this would be an LSTM/GRU hidden state
        aggregated_feature = np.mean(arr, axis=0)
        
        # Project to embedding dimension
        # Use a deterministic seed based on content for reproducibility in mock
        np.random.seed(int(np.sum(aggregated_feature) * 1000) % (2**32))
        projection = np.random.rand(aggregated_feature.shape[0], EMBEDDING_DIM).astype(np.float32)
        embedding = np.dot(aggregated_feature, projection)
        
        return _normalize_vector(embedding)
        
    except Exception as e:
        logger.error(f"Error processing temporal data: {e}")
        return np.zeros(EMBEDDING_DIM)

def fuse_multimodal_intents(inputs: List[ModalityInput]) -> Optional[IntentTensor]:
    """
    Main Fusion Function.
    
    Aggregates heterogeneous input modalities into a single 'Intent Tensor'.
    Implements an attention-like weighting mechanism based on input confidence
    and calculated information entropy.
    
    Args:
        inputs (List[ModalityInput]): List of validated modality inputs.
        
    Returns:
        Optional[IntentTensor]: The unified data structure, or None if fusion fails.
        
    Input Format Example:
        [
            {"modality_type": "text", "data": "Create a red button", "confidence": 0.9},
            {"modality_type": "trajectory", "data": [[0,0,0], [10,10,100]], "confidence": 0.8}
        ]
        
    Output Format:
        IntentTensor(
            fused_embedding: np.ndarray [1, 768],
            modality_weights: Dict,
            attention_mask: np.ndarray
        )
    """
    if not inputs:
        logger.warning("No inputs provided for fusion.")
        return None

    embeddings = []
    weights = []
    modality_keys = []

    logger.info(f"Starting fusion process for {len(inputs)} modalities...")

    for item in inputs:
        try:
            # 1. Encode
            if item.modality_type == ModalityType.TEXT:
                emb = encode_text_modality(item.data)
            elif item.modality_type == ModalityType.SKETCH:
                emb = encode_visual_modality(item.data)
            elif item.modality_type == ModalityType.AUDIO:
                emb = encode_temporal_modality(item.data, "audio")
            elif item.modality_type == ModalityType.TRAJECTORY:
                emb = encode_temporal_modality(item.data, "trajectory")
            else:
                continue
            
            embeddings.append(emb)
            
            # 2. Calculate Weight (Mock Attention Score)
            # Real system would calculate similarity between modalities here.
            # We combine user-provided confidence with a mock 'feature density' score.
            density_score = np.linalg.norm(emb) # L2 norm as proxy for info density
            final_weight = item.confidence * (0.5 + density_score)
            
            weights.append(final_weight)
            modality_keys.append(item.modality_type.value)
            
        except Exception as e:
            logger.error(f"Failed to process modality {item.modality_type}: {e}")

    if not embeddings:
        logger.error("No valid embeddings were generated.")
        return None

    # 3. Weighted Fusion
    embeddings_stack = np.stack(embeddings, axis=0) # Shape: [N, EMBEDDING_DIM]
    weights_arr = np.array(weights).reshape(-1, 1)  # Shape: [N, 1]
    
    # Softmax normalization of weights
    exp_weights = np.exp(weights_arr - np.max(weights_arr))
    softmax_weights = exp_weights / np.sum(exp_weights)
    
    # Weighted sum
    fused_embedding = np.sum(embeddings_stack * softmax_weights, axis=0)
    
    # Post-fusion normalization
    fused_embedding = _normalize_vector(fused_embedding)
    
    logger.info("Fusion complete. Generated Intent Tensor.")

    # 4. Construct Output Structure
    weight_distribution = {k: float(v) for k, v in zip(modality_keys, softmax_weights.flatten())}
    
    return IntentTensor(
        fused_embedding=fused_embedding,
        modality_weights=weight_distribution,
        attention_mask=np.ones(EMBEDDING_DIM) # Mock mask indicating active intent space
    )

# -----------------------------------------------------------------------------
# Usage Example
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Simulate a multimodal input scenario
    raw_input_data = [
        {
            "modality_type": "text",
            "data": "Draw a circle here and make it red",
            "confidence": 0.95
        },
        {
            "modality_type": "trajectory",
            "data": [(0,0,0), (10, 5, 10), (20, 20, 20), (10, 40, 30)], # x, y, t
            "confidence": 0.85
        },
        {
            "modality_type": "sketch",
            "data": [0.1, 0.5, 0.2, 0.9, 0.3], # Mock sketch features
            "confidence": 0.6
        }
    ]

    try:
        # 1. Validate Inputs
        validated_inputs = [ModalityInput(**item) for item in raw_input_data]
        
        # 2. Fuse Intents
        unified_intent = fuse_multimodal_intents(validated_inputs)
        
        # 3. Display Results
        if unified_intent:
            print("\n--- Fusion Result ---")
            print(f"Shape: {unified_intent.fused_embedding.shape}")
            print(f"Modality Contribution Weights: {unified_intent.modality_weights}")
            print(f"First 5 values of Intent Tensor: {unified_intent.fused_embedding[:5]}")
        else:
            print("Fusion failed.")
            
    except ValidationError as e:
        logger.error(f"Input validation failed: {e}")
    except Exception as e:
        logger.error(f"System error: {e}")