"""
Cross-Domain Transfer Mechanism for Chatter Recognition.

This module implements a mechanism to abstract 'chatter recognition' skills
from the metal cutting domain and transfer them to the composite material
machining domain with minimal retraining. It utilizes feature abstraction
and domain adaptation techniques.

Key Concepts:
- Feature Abstraction: Extracting domain-invariant spectral features (FFT, statistical moments).
- Domain Adaptation: Aligning the statistical distribution of target domain features
  to the source domain using normalization techniques.
- Zero-Shot/Few-Shot Transfer: Using the adapted features directly with the source model.

Input Format:
    Raw sensor data (vibration/force) as numpy arrays.

Output Format:
    Predicted chatter probability and adapted feature vectors.

Example Usage:
    >>> import numpy as np
    >>> from auto_如何设计跨域迁移机制_将金属切削领域的_6b06b0 import (
    ...     abstract_features, adapt_domain, predict_chatter
    ... )
    >>> # Simulate source model parameters (mean and std of features in metal domain)
    >>> source_stats = {'mean': np.array([0.5, 1.0, 2.0]), 'std': np.array([0.1, 0.2, 0.5])}
    >>> # Simulate composite material signal
    >>> composite_signal = np.random.normal(0, 1, 1000)
    >>> features = abstract_features(composite_signal, sampling_rate=10000)
    >>> adapted_features = adapt_domain(features, source_stats)
    >>> prediction = predict_chatter(adapted_features)
    >>> print(f"Chatter Probability: {prediction:.4f}")
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TransferConfig:
    """Configuration for the transfer learning process."""
    sampling_rate: float = 10000.0  # Hz
    fft_bins: int = 512
    adaptation_strength: float = 0.8  # 0.0 to 1.0, how much to shift towards source dist
    threshold: float = 0.5  # Chatter detection threshold


def validate_input_data(signal: np.ndarray) -> None:
    """
    Validates the input sensor signal.

    Args:
        signal: 1D numpy array representing vibration or force data.

    Raises:
        ValueError: If the signal is empty, not 1D, or contains NaN/Inf.
    """
    if signal.size == 0:
        raise ValueError("Input signal cannot be empty.")
    if signal.ndim != 1:
        raise ValueError(f"Input signal must be 1D, got {signal.ndim} dimensions.")
    if not np.isfinite(signal).all():
        raise ValueError("Input signal contains NaN or Inf values.")
    logger.debug("Input data validation passed.")


def abstract_features(signal: np.ndarray, config: TransferConfig) -> np.ndarray:
    """
    Core Function 1: Abstracts raw signal into domain-invariant spectral features.
    
    This function mimics the feature extraction layer of a neural network trained
    on metal cutting. It focuses on frequency domain characteristics which are
    physically relevant to chatter in both metal and composite materials.

    Args:
        signal: 1D numpy array of sensor data.
        config: TransferConfig object containing processing parameters.

    Returns:
        A 1D numpy array of abstracted features [rms, peak_freq, spectral_centroid].
        
    Raises:
        RuntimeError: If FFT computation fails unexpectedly.
    """
    try:
        validate_input_data(signal)
        
        # 1. Time-Domain Feature: Root Mean Square (Energy)
        rms = np.sqrt(np.mean(signal ** 2))
        
        # 2. Frequency-Domain Features
        # Compute FFT
        n = len(signal)
        fft_vals = np.fft.rfft(signal[:config.fft_bins]) if n > config.fft_bins else np.fft.rfft(signal)
        fft_freq = np.fft.rfftfreq(len(fft_vals), 1 / config.sampling_rate)
        
        # Power Spectrum
        power_spectrum = np.abs(fft_vals) ** 2
        
        # Peak Frequency (Dominant frequency component)
        if len(power_spectrum) > 0:
            peak_freq_idx = np.argmax(power_spectrum)
            peak_freq = fft_freq[peak_freq_idx]
            
            # Spectral Centroid (Center of mass of the spectrum)
            spectral_centroid = np.sum(fft_freq * power_spectrum) / (np.sum(power_spectrum) + 1e-9)
        else:
            peak_freq = 0.0
            spectral_centroid = 0.0

        features = np.array([rms, peak_freq, spectral_centroid])
        logger.info(f"Abstracted features: {features}")
        return features

    except Exception as e:
        logger.error(f"Failed to abstract features: {e}")
        raise RuntimeError(f"Feature abstraction failed: {e}") from e


def adapt_domain(
    target_features: np.ndarray,
    source_domain_stats: Dict[str, np.ndarray],
    config: TransferConfig
) -> np.ndarray:
    """
    Core Function 2: Adapts target domain features to match source domain distribution.
    
    This function performs statistical normalization to bridge the gap between
    metal (source) and composite (target) data distributions without retraining
    the core model weights.

    Args:
        target_features: Features extracted from the composite material signal.
        source_domain_stats: Dictionary containing 'mean' and 'std' of the source domain features.
        config: TransferConfig object.

    Returns:
        Adapted feature vector aligned to source domain statistics.
        
    Raises:
        KeyError: If source_domain_stats is missing required keys.
    """
    try:
        if 'mean' not in source_domain_stats or 'std' not in source_domain_stats:
            raise KeyError("source_domain_stats must contain 'mean' and 'std'.")
            
        source_mean = source_domain_stats['mean']
        source_std = source_domain_stats['std']
        
        # Calculate target statistics (online estimation for single sample or batch)
        # Here we assume target_features is a single vector for simplicity of the skill
        # In a real batch scenario, we would calculate mean/std of the batch.
        
        # Z-score normalization relative to source domain
        # Formula: (x - target_mean) / target_std * source_std + source_mean
        # Simplified for single sample transfer: We map the feature vector directly
        # to the source manifold using linear scaling.
        
        # Avoid division by zero
        safe_source_std = np.where(source_std == 0, 1e-6, source_std)
        
        # This is a simplified adaptation: scaling based on source variance
        adapted_features = (target_features * config.adaptation_strength) + \
                           (source_mean * (1 - config.adaptation_strength))
                           
        # Alternatively, standardizing to source distribution:
        # adapted_features = (target_features - np.mean(target_features)) / (np.std(target_features) + 1e-9)
        # adapted_features = adapted_features * safe_source_std + source_mean

        logger.info(f"Domain adaptation applied. Adapted features: {adapted_features}")
        return adapted_features

    except Exception as e:
        logger.error(f"Domain adaptation failed: {e}")
        raise RuntimeError(f"Domain adaptation failed: {e}") from e


def predict_chatter(
    adapted_features: np.ndarray,
    model_weights: Optional[Dict[str, Any]] = None
) -> Tuple[float, bool]:
    """
    Helper Function: Performs inference using the adapted features.
    
    Simulates a pre-trained classifier (e.g., SVM or Neural Net head) that
    operates on the abstracted feature space.

    Args:
        adapted_features: The feature vector after domain adaptation.
        model_weights: Optional dictionary containing weights for a linear classifier.
                       If None, uses default heuristic weights.

    Returns:
        A tuple containing:
            - probability (float): Confidence score of chatter occurrence (0.0 to 1.0).
            - is_chatter (bool): Boolean decision based on threshold.
    """
    try:
        # Default heuristic weights if no model provided
        # [rms_weight, peak_freq_weight, centroid_weight]
        if model_weights is None:
            weights = np.array([0.4, 0.3, 0.3])
            bias = -0.5
        else:
            weights = model_weights.get('weights', np.array([0.4, 0.3, 0.3]))
            bias = model_weights.get('bias', -0.5)

        # Linear combination (Logit)
        logit = np.dot(adapted_features, weights) + bias
        
        # Sigmoid activation for probability
        probability = 1.0 / (1.0 + np.exp(-logit))
        
        # Decision boundary
        is_chatter = probability > 0.5
        
        logger.info(f"Prediction - Probability: {probability:.4f}, Is Chatter: {is_chatter}")
        return probability, is_chatter

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return 0.0, False


def execute_transfer_pipeline(
    raw_signal: np.ndarray,
    source_stats: Dict[str, np.ndarray],
    config: Optional[TransferConfig] = None
) -> Dict[str, Any]:
    """
    Executes the full cross-domain transfer pipeline.
    
    Orchestrates validation, abstraction, adaptation, and prediction.

    Args:
        raw_signal: Raw sensor data from composite machining.
        source_stats: Statistical profile of the metal cutting domain.
        config: Configuration object. Defaults to TransferConfig().

    Returns:
        Dictionary containing original features, adapted features, and prediction results.
    """
    if config is None:
        config = TransferConfig()
        
    logger.info("Starting cross-domain transfer pipeline...")
    
    # Step 1: Abstract
    features = abstract_features(raw_signal, config)
    
    # Step 2: Adapt
    adapted_features = adapt_domain(features, source_stats, config)
    
    # Step 3: Predict
    prob, is_chatter = predict_chatter(adapted_features)
    
    result = {
        "original_features": features,
        "adapted_features": adapted_features,
        "chatter_probability": float(prob),
        "is_chatter": is_chatter
    }
    
    logger.info("Pipeline execution completed successfully.")
    return result


if __name__ == "__main__":
    # Example execution block
    # 1. Define Source Domain Statistics (Metal Cutting)
    # These would typically be learned during the training phase on metal data
    metal_domain_stats = {
        'mean': np.array([0.8, 1200.0, 1500.0]), # High RMS, specific freqs
        'std': np.array([0.2, 300.0, 400.0])
    }
    
    # 2. Generate Synthetic Composite Material Signal
    # Composite signals often have lower amplitude and different damping
    np.random.seed(42)
    t = np.linspace(0, 0.1, 1000)
    # Simulate a signal with some noise and a specific frequency component
    composite_signal = 0.5 * np.sin(2 * np.pi * 1100 * t) + 0.1 * np.random.randn(len(t))
    
    # 3. Run Pipeline
    try:
        results = execute_transfer_pipeline(composite_signal, metal_domain_stats)
        print("\n--- Transfer Results ---")
        print(f"Original Features: {results['original_features']}")
        print(f"Adapted Features:  {results['adapted_features']}")
        print(f"Chatter Probability: {results['chatter_probability']:.2%}")
        print(f"Detection Status: {'CHATTER DETECTED' if results['is_chatter'] else 'STABLE'}")
    except Exception as e:
        print(f"Error in execution: {e}")