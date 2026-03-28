"""
Module: auto_bottom_up_tolerance_chain
Description: Implements a probabilistic tolerance stack-up node for multi-level assemblies.
             It generates synthetic data via Monte Carlo Simulation (MCS) and trains a
             surrogate neural network to enable real-time 'assemblability' inference.
Domain: precision_engineering
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

# In a production environment, ensure TensorFlow is installed.
# For this standalone skill, we handle import gracefully.
try:
    import tensorflow as tf
    from tensorflow.keras import layers, models, optimizers
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    # Mocking for environments without TF just to allow parsing, though run will fail.
    class layers:
        Dense = None
        Input = None
    class models:
        Sequential = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class PartTolerance:
    """
    Represents a 3D geometric tolerance for a single part.
    
    Attributes:
        name: Identifier for the part.
        dim_x, dim_y, dim_z: Nominal dimensions.
        tol_x, tol_y, tol_z: Geometric tolerances (usually symmetric +/-).
        distribution: Assumed statistical distribution ('normal' or 'uniform').
    """
    name: str
    dim_x: float
    dim_y: float
    dim_z: float
    tol_x: float
    tol_y: float
    tol_z: float
    distribution: str = 'normal'

    def __post_init__(self):
        if self.distribution not in ['normal', 'uniform']:
            raise ValueError(f"Unsupported distribution: {self.distribution}")

class ToleranceNode:
    """
    The 'Node' in the AGI system representing the assembly.
    """
    def __init__(self, assembly_name: str):
        self.assembly_name = assembly_name
        self.parts: List[PartTolerance] = []
        self.nn_model: Optional[models.Sequential] = None
        self.scaler_input = StandardScaler()
        self.scaler_output = StandardScaler()
        logger.info(f"Initialized ToleranceNode for assembly: {assembly_name}")

    def add_part(self, part: PartTolerance) -> None:
        """Adds a part definition to the assembly chain."""
        if not isinstance(part, PartTolerance):
            raise TypeError("Must add PartTolerance objects.")
        self.parts.append(part)
        logger.debug(f"Added part {part.name} to assembly.")

# --- Core Functions ---

def run_monte_carlo_simulation(
    node: ToleranceNode, 
    n_samples: int = 10000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Performs a Bottom-Up Monte Carlo Simulation to generate training data.
    
    Converts individual part tolerances into assembly-level functional gaps.
    Assumes a linear stack-up for demonstration (1D chain vector projection).
    
    Args:
        node: The ToleranceNode containing part definitions.
        n_samples: Number of Monte Carlo iterations.
        
    Returns:
        X: Input features (Individual part deviations) shape (n_samples, n_features).
        y: Target label (Total Assembly Gap/Interference) shape (n_samples, 1).
    """
    if not node.parts:
        raise ValueError("Cannot simulate an empty assembly.")
    
    logger.info(f"Starting Monte Carlo Simulation with {n_samples} samples...")
    
    n_parts = len(node.parts)
    # Features: Flattened deviations (dx, dy, dz) for each part
    X_data = np.zeros((n_samples, n_parts * 3))
    # Target: Total accumulation vector magnitude (simplified to 1D stack logic here)
    # In a real 3D scenario, this would be a kinematic constraint solver result.
    y_data = np.zeros((n_samples, 1))
    
    for i in range(n_samples):
        current_gap = 0.0
        features_row = []
        
        for p_idx, part in enumerate(node.parts):
            # Generate deviations based on distribution
            # Assuming 3-Sigma process capability for normal dist
            if part.distribution == 'normal':
                dx = np.random.normal(0, part.tol_x / 3)
                dy = np.random.normal(0, part.tol_y / 3)
                dz = np.random.normal(0, part.tol_z / 3)
            else: # Uniform
                dx = np.random.uniform(-part.tol_x, part.tol_x)
                dy = np.random.uniform(-part.tol_y, part.tol_y)
                dz = np.random.uniform(-part.tol_z, part.tol_z)
            
            features_row.extend([dx, dy, dz])
            
            # Simplified Accumulation Logic:
            # Real AGI would use Homogeneous Transformation Matrices (HTM) here.
            # We project 3D tolerance onto the assembly axis (Z-axis) for this demo.
            current_gap += dz
            
        X_data[i, :] = np.array(features_row)
        y_data[i, 0] = current_gap
        
    logger.info("Monte Carlo Simulation complete.")
    return X_data, y_data

def build_and_train_surrogate_model(
    node: ToleranceNode,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 50,
    validation_split: float = 0.2
) -> Dict[str, float]:
    """
    Trains a neural network to approximate the MCS function.
    
    This enables real-time inference (microseconds vs minutes/seconds).
    
    Args:
        node: The ToleranceNode to attach the model to.
        X: Input data (part deviations).
        y: Target data (assembly gaps).
        epochs: Training epochs.
        validation_split: Fraction of data for validation.
        
    Returns:
        metrics: Dictionary containing final loss and validation metrics.
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required for this functionality.")
        
    logger.info("Preprocessing data and building model...")
    
    # Data Scaling
    X_scaled = node.scaler_input.fit_transform(X)
    y_scaled = node.scaler_output.fit_transform(y)
    
    # Model Architecture
    input_dim = X_scaled.shape[1]
    model = models.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(64, activation='relu', name='hidden_1'),
        layers.Dense(32, activation='relu', name='hidden_2'),
        layers.Dense(16, activation='relu', name='hidden_3'),
        layers.Dense(1, name='gap_prediction') # Linear output for regression
    ])
    
    model.compile(optimizer=optimizers.Adam(learning_rate=0.001), loss='mse')
    
    logger.info("Starting training...")
    history = model.fit(
        X_scaled, y_scaled,
        epochs=epochs,
        batch_size=32,
        validation_split=validation_split,
        verbose=0
    )
    
    node.nn_model = model
    final_loss = history.history['loss'][-1]
    final_val_loss = history.history['val_loss'][-1]
    
    logger.info(f"Training complete. Final MSE: {final_loss:.6f}")
    
    return {"loss": final_loss, "val_loss": final_val_loss}

# --- Auxiliary Functions ---

def real_time_assemblability_check(
    node: ToleranceNode,
    part_deviations: Dict[str, Tuple[float, float, float]]
) -> Dict[str, Union[float, str]]:
    """
    Uses the trained surrogate model to evaluate assemblability instantly.
    
    Args:
        node: ToleranceNode with a loaded model.
        part_deviations: Dict mapping part name to (dx, dy, dz).
        
    Returns:
        result: Dictionary containing predicted gap and status.
    """
    if node.nn_model is None:
        raise RuntimeError("Model not trained. Call build_and_train_surrogate_model first.")
    
    # Validate input structure
    if len(part_deviations) != len(node.parts):
        raise ValueError(f"Expected deviations for {len(node.parts)} parts, got {len(part_deviations)}.")
        
    # Flatten input vector in the order parts were added
    input_vector = []
    for part in node.parts:
        if part.name not in part_deviations:
            raise KeyError(f"Missing deviation data for part: {part.name}")
        
        dev = part_deviations[part.name]
        if len(dev) != 3:
            raise ValueError(f"Deviations for {part.name} must be (dx, dy, dz).")
        input_vector.extend(dev)
        
    # Inference
    input_array = np.array([input_vector])
    input_scaled = node.scaler_input.transform(input_array)
    
    pred_scaled = node.nn_model.predict(input_scaled, verbose=0)
    pred_gap = node.scaler_output.inverse_transform(pred_scaled)[0][0]
    
    # Determine Status (Example threshold: +/- 0.05mm critical gap)
    if pred_gap > 0.05:
        status = "LOOSE"
    elif pred_gap < -0.05:
        status = "INTERFERENCE"
    else:
        status = "OPTIMAL"
        
    return {
        "predicted_gap_mm": float(pred_gap),
        "assembly_status": status
    }

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Assembly Node
    assembly_node = ToleranceNode(assembly_name="Gearbox_Housing_Unit")
    
    # 2. Define Parts (Bottom-Up)
    # Part A: Cylinder, tight tolerance
    part_a = PartTolerance("Cylinder", 10, 10, 50, 0.01, 0.01, 0.02, distribution='normal')
    # Part B: Sleeve, looser tolerance
    part_b = PartTolerance("Sleeve", 12, 12, 20, 0.05, 0.05, 0.10, distribution='normal')
    # Part C: Base plate
    part_c = PartTolerance("Plate", 50, 50, 5, 0.1, 0.1, 0.01, distribution='uniform')
    
    assembly_node.add_part(part_a)
    assembly_node.add_part(part_b)
    assembly_node.add_part(part_c)
    
    # 3. Generate Data (Monte Carlo)
    try:
        X_train, y_train = run_monte_carlo_simulation(assembly_node, n_samples=5000)
        
        # 4. Train Surrogate Model
        if TF_AVAILABLE:
            metrics = build_and_train_surrogate_model(assembly_node, X_train, y_train, epochs=20)
            print(f"\nTraining Metrics: {metrics}")
            
            # 5. Real-time Inference (The AGI Skill)
            # Scenario: Incoming inspection measurements
            live_deviations = {
                "Cylinder": (0.005, -0.002, 0.015),
                "Sleeve": (0.02, 0.01, -0.08),
                "Plate": (-0.05, 0.05, 0.005)
            }
            
            result = real_time_assemblability_check(assembly_node, live_deviations)
            print(f"\nReal-time Inference Result: {result}")
            
        else:
            print("\nTensorFlow not found. Skipping training and inference steps.")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")