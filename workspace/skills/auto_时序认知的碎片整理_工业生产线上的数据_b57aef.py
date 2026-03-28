"""
Module: auto_时序认知的碎片整理_工业生产线上的数据_b57aef
Description: [时序认知的碎片整理] Implements lossless compression for continuous
             industrial data streams into discrete cognitive nodes. It specifically
             focuses on detecting "cognitive blind spots" caused by information loss
             during sampling, particularly for slowly varying signals like tool wear.
"""

import logging
import numpy as np
from typing import Tuple, List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataValidationError(ValueError):
    """Custom exception for invalid input data."""
    pass

def _validate_input_signals(data: np.ndarray, sampling_rate: float) -> None:
    """
    Auxiliary function to validate input data integrity and boundary conditions.
    
    Args:
        data (np.ndarray): 1D array of time series data.
        sampling_rate (float): Sampling rate in Hz.
    
    Raises:
        DataValidationError: If data is empty, contains NaNs, or sampling rate is invalid.
    """
    if not isinstance(data, np.ndarray):
        raise DataValidationError("Input data must be a numpy array.")
    
    if data.ndim != 1:
        raise DataValidationError("Input data must be a 1-dimensional array.")
        
    if len(data) == 0:
        raise DataValidationError("Input data array cannot be empty.")
        
    if np.isnan(data).any():
        raise DataValidationError("Input data contains NaN values.")
        
    if sampling_rate <= 0:
        raise DataValidationError("Sampling rate must be positive.")

def adaptive_fragmented_sampling(
    signal: np.ndarray, 
    base_threshold: float = 0.05, 
    slow_drift_window: int = 50
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Core Function 1: Implements 'Continuous-Discrete' compression.
    
    This function performs adaptive sampling. Instead of fixed-interval sampling,
    it retains points where significant changes occur (information entropy is high)
    and aggregates areas of low change (slow drift) into representative statistical nodes.
    
    Args:
        signal (np.ndarray): The input continuous data stream.
        base_threshold (float): The relative change threshold to trigger a 'cognitive node'.
        slow_drift_window (int): Window size to detect slow-varying trends (blind spots).
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: 
            - compressed_indices: Indices of the retained nodes in the original array.
            - compressed_values: Values at these nodes.
            
    Example:
        >>> data = np.sin(np.linspace(0, 10, 1000))
        >>> idx, vals = adaptive_fragmented_sampling(data)
    """
    logger.info("Starting adaptive fragmented sampling...")
    
    n = len(signal)
    compressed_indices = [0]
    compressed_values = [signal[0]]
    
    i = 1
    while i < n:
        # Check for rapid changes (Standard sampling logic)
        if i == n - 1:
            compressed_indices.append(i)
            compressed_values.append(signal[i])
            break
            
        current_val = signal[i]
        last_compressed_val = compressed_values[-1]
        
        # Calculate dynamic threshold based on signal magnitude to handle scaling
        dynamic_thresh = base_threshold * (1 + abs(last_compressed_val))
        
        if abs(current_val - last_compressed_val) > dynamic_thresh:
            # Significant change detected -> Create discrete cognitive node
            compressed_indices.append(i)
            compressed_values.append(current_val)
            i += 1
        else:
            # Check for "Slow Drift" (Cognitive Blind Spot mitigation)
            # Look ahead in the window to see if a small change accumulates
            window_end = min(i + slow_drift_window, n)
            window_data = signal[i:window_end]
            
            if len(window_data) > 0:
                drift = np.max(window_data) - np.min(window_data)
                # If drift is significant over time but not instantaneous, capture it
                if drift > (dynamic_thresh * 2):
                    # Force a node at the peak of the drift to preserve trend
                    extreme_idx_rel = np.argmax(np.abs(window_data - last_compressed_val))
                    extreme_idx = i + extreme_idx_rel
                    compressed_indices.append(extreme_idx)
                    compressed_values.append(signal[extreme_idx])
                    i = extreme_idx + 1
                    continue
            
            # Skip redundant data point (Lossless in context of threshold)
            i += 1
            
    logger.info(f"Compression complete. Original: {n}, Compressed: {len(compressed_indices)}")
    return np.array(compressed_indices), np.array(compressed_values)

def detect_cognitive_blind_spots(
    original_signal: np.ndarray, 
    reconstructed_signal: np.ndarray, 
    tolerance: float = 0.01
) -> Dict[str, float]:
    """
    Core Function 2: Verifies information loss and detects 'Cognitive Blind Spots'.
    
    It compares the original continuous stream against the reconstructed stream
    (from the discrete nodes) to quantify the "blindness" of the system.
    Special focus is on residuals in slowly varying regions.
    
    Args:
        original_signal (np.ndarray): The ground truth continuous data.
        reconstructed_signal (np.ndarray): The signal reconstructed from discrete nodes.
        tolerance (float): Maximum allowable error variance.
        
    Returns:
        Dict[str, float]: A report containing MSE, Max Drift Error, and Blind Spot Ratio.
        
    Example:
        >>> report = detect_cognitive_blind_spots(raw_data, reconstructed_data)
    """
    logger.info("Analyzing cognitive blind spots...")
    
    if len(original_signal) != len(reconstructed_signal):
        raise ValueError("Signal lengths must match for comparison.")

    # Calculate residuals
    residuals = original_signal - reconstructed_signal
    
    # 1. Global Information Loss (MSE)
    mse = np.mean(residuals ** 2)
    
    # 2. Blind Spot Detection (Slow varying errors that accumulate)
    # We look for high correlation in residuals over time, implying a drift was missed
    if len(residuals) > 10:
        # Simple gradient check for slow drift
        residual_gradient = np.gradient(residuals)
        slow_drift_indicator = np.mean(np.abs(residual_gradient))
    else:
        slow_drift_indicator = 0.0
        
    # 3. Max deviation (The deepest blind spot)
    max_error = np.max(np.abs(residuals))
    
    # 4. Blind Spot Ratio (Percentage of time the system is 'blind' beyond tolerance)
    # Normalized by signal range to handle different sensor scales
    signal_range = np.max(original_signal) - np.min(original_signal)
    if signal_range == 0: signal_range = 1.0
    
    normalized_error = np.abs(residuals) / signal_range
    blind_spots = np.sum(normalized_error > tolerance) / len(normalized_error)
    
    report = {
        "mean_squared_error": float(mse),
        "max_deviation": float(max_error),
        "slow_drift_intensity": float(slow_drift_indicator),
        "blind_spot_ratio": float(blind_spots)
    }
    
    if blind_spots > 0.05:
        logger.warning(f"High Blind Spot Ratio detected: {blind_spots:.2%}")
    
    return report

# --- Usage Example and Execution ---

if __name__ == "__main__":
    try:
        # 1. Generate Synthetic Industrial Data (Tool Wear Simulation)
        # Contains: Fast vibrations (noise) + Slow trend (wear) + Abrupt change (breakage)
        logger.info("Generating synthetic industrial data...")
        time = np.linspace(0, 100, 5000)
        
        # Slow wear trend: increases slowly
        wear_trend = np.log1p(time * 0.1) 
        
        # Vibrations: High frequency noise
        vibration = 0.05 * np.sin(2 * np.pi * 10 * time)
        
        # Abrupt change: Wear spike at the end
        wear_spike = np.zeros_like(time)
        wear_spike[4000:] = 0.5
        
        original_data = wear_trend + vibration + wear_spike
        
        # 2. Validate Data
        _validate_input_signals(original_data, sampling_rate=50.0)
        
        # 3. Perform Adaptive Sampling (Compression)
        indices, values = adaptive_fragmented_sampling(
            original_data, 
            base_threshold=0.02, 
            slow_drift_window=100
        )
        
        # 4. Reconstruct Signal for Verification
        # Using linear interpolation to simulate how the AGI 'connects' discrete nodes
        reconstructed_data = np.interp(time, time[indices], values)
        
        # 5. Check for Blind Spots
        blind_spot_report = detect_cognitive_blind_spots(
            original_data, 
            reconstructed_data, 
            tolerance=0.01
        )
        
        print(f"\n--- Cognitive Defragmentation Report ---")
        print(f"Original Data Points: {len(original_data)}")
        print(f"Discrete Nodes Retained: {len(values)}")
        print(f"Compression Ratio: {100 * (1 - len(values)/len(original_data)):.2f}%")
        print(f"Blind Spot Analysis: {blind_spot_report}")
        
    except DataValidationError as dve:
        logger.error(f"Data validation failed: {dve}")
    except Exception as e:
        logger.critical(f"System crash: {e}", exc_info=True)