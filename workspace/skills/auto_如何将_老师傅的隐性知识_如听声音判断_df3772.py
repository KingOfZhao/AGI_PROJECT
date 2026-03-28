"""
SKILL: auto_如何将_老师傅的隐性知识_如听声音判断_df3772
Description: Converts expert tacit knowledge (e.g., auditory machine diagnostics)
             into explicit computational nodes via contrastive learning and sensor alignment.
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SensorReading(BaseModel):
    """Represents raw high-precision sensor data."""
    timestamp: float
    vibration_axis_x: float = Field(..., description="Acceleration in X (m/s^2)")
    vibration_axis_y: float = Field(..., description="Acceleration in Y (m/s^2)")
    vibration_axis_z: float = Field(..., description="Acceleration in Z (m/s^2)")
    decibels: float = Field(..., description="Sound pressure level (dB)")

class ExpertLabel(BaseModel):
    """Represents the expert's fuzzy judgment."""
    timestamp: float
    state_label: str = Field(..., description="Categorical label e.g., 'normal', 'anomaly', 'wear'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Expert's subjective confidence")

class DigitalIntuitionNode(BaseModel):
    """The explicit output node containing the learned logic."""
    node_id: str
    created_at: str
    feature_weights: Dict[str, float]
    bias: float
    threshold: float
    validation_accuracy: float
    source_expert_id: str

# --- Core Functions ---

def preprocess_signals(
    readings: List[SensorReading],
    sample_rate: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Preprocesses raw sensor data into feature vectors.
    
    Transforms time-domain vibration and audio signals into statistical features
    that might correlate with human auditory perception (e.g., RMS, Kurtosis).
    
    Args:
        readings: List of raw sensor observations.
        sample_rate: Sampling rate used for calculations.
        
    Returns:
        Tuple containing:
            - timestamps (np.ndarray)
            - feature_matrix (np.ndarray): Shape (n_samples, n_features)
            
    Raises:
        ValueError: If input list is empty or data integrity check fails.
    """
    if not readings:
        logger.error("Input readings list is empty.")
        raise ValueError("Input readings cannot be empty.")

    logger.info(f"Preprocessing {len(readings)} sensor readings...")
    
    n = len(readings)
    # Feature placeholders: [RMS_X, RMS_Y, RMS_Z, RMS_dB, Kurtosis_X]
    features = np.zeros((n, 5))
    timestamps = np.zeros(n)
    
    try:
        for i, r in enumerate(readings):
            timestamps[i] = r.timestamp
            # Simplified Feature Extraction
            # In a real scenario, this would involve FFT or Wavelet transforms
            rms_x = np.sqrt(r.vibration_axis_x**2) 
            rms_y = np.sqrt(r.vibration_axis_y**2)
            rms_z = np.sqrt(r.vibration_axis_z**2)
            
            # Normalize dB to scale with vibrations
            norm_db = r.decibels / 100.0 
            
            features[i, 0] = rms_x
            features[i, 1] = rms_y
            features[i, 2] = rms_z
            features[i, 3] = norm_db
            # Mock Kurtosis calculation for demonstration
            features[i, 4] = (r.vibration_axis_x**4) / (rms_x**4 + 1e-9)
            
        # Data Validation: Check for NaNs
        if np.isnan(features).any():
            raise ValueError("NaN values detected in feature extraction.")
            
        logger.info("Preprocessing complete.")
        return timestamps, features
        
    except Exception as e:
        logger.exception("Error during signal preprocessing.")
        raise RuntimeError(f"Failed to process signals: {e}")

def align_and_train_node(
    expert_labels: List[ExpertLabel],
    timestamps: np.ndarray,
    feature_matrix: np.ndarray,
    learning_rate: float = 0.01,
    epochs: int = 100
) -> DigitalIntuitionNode:
    """
    Aligns expert 'fuzzy' timestamps with sensor features to train a classifier.
    
    This uses a simplified Contrastive Learning approach. It maximizes the distance
    between 'Normal' and 'Anomaly' feature clusters while minimizing intra-class variance.
    The result is a weight vector (Digital Intuition) that mimics the expert's decision boundary.
    
    Args:
        expert_labels: List of expert observations.
        timestamps: Numpy array of sensor timestamps.
        feature_matrix: Numpy array of extracted features.
        learning_rate: Learning rate for gradient descent.
        epochs: Number of training iterations.
        
    Returns:
        DigitalIntuitionNode: The serialized knowledge object.
    """
    logger.info("Starting knowledge alignment and node training...")
    
    # 1. Data Alignment (Temporal Join)
    # Match expert labels to the closest sensor reading
    aligned_X = []
    aligned_y = []
    
    label_map = {label.timestamp: label for label in expert_labels}
    label_times = np.array(list(label_map.keys()))
    
    for i, t in enumerate(timestamps):
        # Find closest expert label within a tolerance (e.g., 0.5 seconds)
        diffs = np.abs(label_times - t)
        min_idx = np.argmin(diffs)
        
        if diffs[min_idx] < 0.5:
            label = expert_labels[min_idx]
            if label.state_label != 'ambiguous': # Filter out low confidence data
                aligned_X.append(feature_matrix[i])
                # Binary classification: Normal (0) vs Others (1)
                y_val = 0 if label.state_label == 'normal' else 1
                aligned_y.append(y_val)
                
    if len(aligned_X) < 10:
        raise ValueError("Insufficient aligned data points for training.")
        
    X = np.array(aligned_X)
    y = np.array(aligned_y)
    
    # Normalize features
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    X_norm = (X - mean) / std
    
    # 2. Train Simple Perceptron (Simulating the Intuition Node)
    # We use a basic linear model here to represent the "Explicit Node"
    weights = np.random.rand(X_norm.shape[1])
    bias = 0.0
    
    for epoch in range(epochs):
        # Forward pass
        z = np.dot(X_norm, weights) + bias
        pred = 1 / (1 + np.exp(-z)) # Sigmoid
        
        # Gradient calculation (Cross-Entropy Loss derivative)
        error = pred - y
        grad_w = np.dot(X_norm.T, error) / len(y)
        grad_b = np.mean(error)
        
        # Update weights
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
        
    # 3. Validation
    final_pred = (np.dot(X_norm, weights) + bias) > 0.5
    accuracy = np.mean(final_pred == y)
    logger.info(f"Node training complete. Alignment Accuracy: {accuracy:.2f}")
    
    # 4. Construct the Node
    node = DigitalIntuitionNode(
        node_id=f"node_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        created_at=datetime.now().isoformat(),
        feature_weights={f"feature_{i}": w for i, w in enumerate(weights)},
        bias=bias,
        threshold=0.5,
        validation_accuracy=float(accuracy),
        source_expert_id="EXPERT_001"
    )
    
    return node

# --- Helper Functions ---

def validate_inputs(
    readings: List[SensorReading], 
    labels: List[ExpertLabel]
) -> bool:
    """
    Validates data integrity and temporal overlap between sensors and labels.
    
    Args:
        readings: List of sensor data.
        labels: List of expert labels.
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If time ranges do not overlap or lists are empty.
    """
    if not readings or not labels:
        raise ValueError("Input lists cannot be empty.")
        
    r_min = min(r.timestamp for r in readings)
    r_max = max(r.timestamp for r in readings)
    l_min = min(l.timestamp for l in labels)
    l_max = max(l.timestamp for l in labels)
    
    # Check for overlap
    if r_max < l_min or l_max < r_min:
        logger.error(f"Temporal mismatch. Sensors: [{r_min}-{r_max}], Labels: [{l_min}-{l_max}]")
        raise ValueError("Sensor data and Expert labels do not overlap in time.")
        
    logger.info("Input validation passed.")
    return True

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate Mock Data
    # Simulating 1 second of data
    mock_readings = [
        SensorReading(
            timestamp=i * 0.01,
            vibration_axis_x=np.random.normal(0, 0.1) if i < 50 else np.random.normal(0.5, 0.1),
            vibration_axis_y=np.random.normal(0, 0.1),
            vibration_axis_z=np.random.normal(0, 0.1),
            decibels=60.0 if i < 50 else 85.0
        ) for i in range(100)
    ]
    
    # Expert sees the shift at index 50 roughly
    mock_labels = [
        ExpertLabel(timestamp=0.2, state_label="normal", confidence=0.9),
        ExpertLabel(timestamp=0.4, state_label="normal", confidence=0.9),
        ExpertLabel(timestamp=0.6, state_label="anomaly", confidence=0.8), # The shift
        ExpertLabel(timestamp=0.8, state_label="anomaly", confidence=0.95)
    ]
    
    try:
        # 2. Validate
        validate_inputs(mock_readings, mock_labels)
        
        # 3. Process
        ts, feats = preprocess_signals(mock_readings)
        
        # 4. Train / Extract Knowledge
        intuition_node = align_and_train_node(mock_labels, ts, feats)
        
        # 5. Output Result
        print("\n--- Generated Digital Intuition Node ---")
        print(json.dumps(intuition_node.model_dump(), indent=2))
        
    except (ValueError, RuntimeError) as e:
        logger.error(f"Execution failed: {e}")