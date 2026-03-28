"""
Module: multimodal_perception_mapping.py

This module provides a framework for establishing quantitative mapping models between
multimodal sensor data (Vision, Force, Audio) and fuzzy natural language descriptions
(e.g., 'sticky手感', 'crisp声音'). It aims to digitize implicit human perceptions.

Domain: Multimodal Learning / Cognitive Robotics
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pydantic import BaseModel, Field, ValidationError, validator
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class SensorSample(BaseModel):
    """Represents a single timestamp of synchronized sensor data."""
    vision_vector: List[float] = Field(..., description="Feature vector from vision sensor (e.g., color, texture histogram).")
    force_vector: List[float] = Field(..., description="Feature vector from haptic/force sensor (e.g., friction, vibration).")
    audio_vector: List[float] = Field(..., description="Feature vector from audio sensor (e.g., MFCCs, spectral centroid).")

    @validator('vision_vector', 'force_vector', 'audio_vector')
    def check_vector_non_empty(cls, v):
        if not v:
            raise ValueError("Sensor vectors cannot be empty")
        return v

class FuzzyLabel(BaseModel):
    """Represents a human annotation."""
    description: str
    intensity: float = Field(..., ge=0.0, le=1.0, description="Subjective intensity score [0, 1].")

class PerceptionDataset(BaseModel):
    """Collection of data samples paired with fuzzy labels."""
    samples: List[SensorSample]
    labels: List[FuzzyLabel]

# --- Core Functions ---

def extract_crossmodal_features(dataset: PerceptionDataset) -> Tuple[np.ndarray, np.ndarray]:
    """
    Processes raw sensor data into a unified latent feature vector and prepares targets.
    
    This function handles normalization and dimensionality reduction (mocked via PCA)
    to align different modalities into a shared space.

    Args:
        dataset (PerceptionDataset): Validated dataset containing sensor readings and labels.

    Returns:
        Tuple[np.ndarray, np.ndarray]: 
            - X: Matrix of shape (N, M) representing fused sensor features.
            - Y: Vector of shape (N,) representing quantitative intensity scores.
    
    Raises:
        ValueError: If dataset is empty or inconsistent.
    """
    if not dataset.samples:
        logger.error("Dataset is empty.")
        raise ValueError("Dataset must contain at least one sample.")

    logger.info(f"Processing {len(dataset.samples)} samples...")
    
    # Extract and concatenate raw vectors
    raw_features = []
    for sample in dataset.samples:
        # Simple concatenation represents early fusion
        combined = sample.vision_vector + sample.force_vector + sample.audio_vector
        raw_features.append(combined)
    
    X_raw = np.array(raw_features)
    Y = np.array([label.intensity for label in dataset.labels])

    # 1. Normalization (Min-Max Scaling)
    try:
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X_raw)
    except Exception as e:
        logger.error(f"Scaling failed: {e}")
        raise

    # 2. Dimensionality Reduction (Mock alignment)
    # In a real scenario, this might be a Variational Autoencoder (VAE) or Contrastive Learning
    n_components = min(5, X_scaled.shape[1], X_scaled.shape[0])
    if n_components < 1:
        logger.warning("Not enough features or samples for PCA reduction.")
        return X_scaled, Y

    try:
        reducer = PCA(n_components=n_components)
        X_fused = reducer.fit_transform(X_scaled)
        logger.info(f"Feature fusion complete. Explained variance ratio sum: {sum(reducer.explained_variance_ratio_):.2f}")
        return X_fused, Y
    except Exception as e:
        logger.error(f"Dimensionality reduction failed: {e}")
        raise

def train_perception_mapping_model(X: np.ndarray, Y: np.ndarray) -> Dict[str, float]:
    """
    Trains a regression model to map fused sensor features to quantitative perception scores.
    
    This acts as the 'digitization' of the fuzzy logic. We simulate a simple linear 
    regression behavior here for demonstration without heavy dependencies like PyTorch.

    Args:
        X (np.ndarray): Feature matrix (N, M).
        Y (np.ndarray): Target values (N,).

    Returns:
        Dict[str, float]: A dictionary containing model weights and bias (mock model).
    
    Raises:
        RuntimeError: If mathematical stability issues occur.
    """
    logger.info("Training quantitative mapping model...")
    
    # Input validation
    if X.shape[0] != Y.shape[0]:
        msg = f"Shape mismatch: X has {X.shape[0]} samples, Y has {Y.shape[0]}."
        logger.error(msg)
        raise ValueError(msg)
    
    # Add bias term (intercept)
    X_b = np.c_[np.ones((X.shape[0], 1)), X]
    
    # Normal Equation: theta = (X^T * X)^-1 * X^T * y
    try:
        # Using SVD pseudo-inverse for stability
        theta_best = np.linalg.pinv(X_b.T.dot(X_b)).dot(X_b.T).dot(Y)
    except np.linalg.LinAlgError as e:
        logger.critical(f"Linear algebra error during model training: {e}")
        raise RuntimeError("Failed to converge on a solution for perception mapping.") from e

    bias = theta_best[0]
    weights = theta_best[1:]

    logger.info(f"Model trained. Bias: {bias:.4f}, Weights norm: {np.linalg.norm(weights):.4f}")

    return {
        "weights": weights.tolist(),
        "bias": float(bias),
        "mse": float(np.mean((X_b.dot(theta_best) - Y) ** 2))
    }

# --- Auxiliary Functions ---

def map_fuzzy_description_to_vector(description: str) -> List[float]:
    """
    Auxiliary function to convert text descriptions to preliminary anchor vectors.
    In a full AGI system, this would use an LLM embedding.
    
    Args:
        description (str): Natural language input like 'sticky' or 'smooth'.
        
    Returns:
        List[float]: A dummy semantic vector.
    """
    # Simple hash-based embedding simulation
    base_vector = np.zeros(5)
    for char in description:
        idx = ord(char) % 5
        val = (ord(char) % 10) / 10.0
        base_vector[idx] += val
    
    # Normalize
    norm = np.linalg.norm(base_vector)
    return (base_vector / norm if norm > 0 else base_vector).tolist()

# --- Usage Example ---

if __name__ == "__main__":
    try:
        # 1. Generate Mock Data
        # Simulating 10 samples of multimodal data
        mock_samples = [
            SensorSample(
                vision_vector=[0.1, 0.8], 
                force_vector=[0.9, 0.2, 0.1], # High friction -> sticky
                audio_vector=[0.1, 0.1]       # Dull sound
            ) for _ in range(5)
        ]
        mock_samples.extend([
            SensorSample(
                vision_vector=[0.9, 0.1], 
                force_vector=[0.1, 0.1, 0.9], # Low friction -> smooth
                audio_vector=[0.9, 0.9]       # Crisp sound
            ) for _ in range(5)
        ])

        mock_labels = [FuzzyLabel(description="sticky", intensity=0.9) for _ in range(5)]
        mock_labels.extend([FuzzyLabel(description="smooth", intensity=0.1) for _ in range(5)])

        dataset = PerceptionDataset(samples=mock_samples, labels=mock_labels)
        
        # 2. Feature Engineering
        X_features, y_targets = extract_crossmodal_features(dataset)
        
        # 3. Model Training
        model_params = train_perception_mapping_model(X_features, y_targets)
        
        print("-" * 30)
        print("Training Complete.")
        print(f"Model MSE: {model_params['mse']:.6f}")
        print(f"Bias: {model_params['bias']:.4f}")
        print("-" * 30)

    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")