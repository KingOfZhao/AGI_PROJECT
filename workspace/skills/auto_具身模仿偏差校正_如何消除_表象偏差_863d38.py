"""
Module: auto_具身模仿偏差校正_如何消除_表象偏差_863d38

This module implements a causal inference-based debiasing pipeline for Embodied Imitation Learning.
It aims to separate "Necessary Causal Chains" (Core Skills) from "Spurious Correlations" 
(Appearance Bias/Habitual Actions) in human demonstration data.

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.stats import pearsonr

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class DemonstrationStep:
    """Represents a single step in a demonstration sequence."""
    step_id: int
    state_vector: np.ndarray       # Environment state (e.g., joint angles, position)
    action_vector: np.ndarray      # Action taken (e.g., delta moves, gripper state)
    task_progress: float           # Ground truth progress (0.0 to 1.0)
    is_human_annotated_noise: Optional[bool] = None # Optional label for validation

@dataclass
class DemonstrationSequence:
    """Represents a full demonstration trajectory."""
    sequence_id: str
    steps: List[DemonstrationStep]
    success_label: bool

@dataclass
class CausalInterventionResult:
    """Result of the causal analysis."""
    core_skill_mask: np.ndarray    # Boolean mask of steps considered core skills
    noise_mask: np.ndarray         # Boolean mask of steps considered noise
    causal_score: np.ndarray       # Probability score of being causal
    explanation: str

# --- Helper Functions ---

def _validate_input_data(sequences: List[DemonstrationSequence]) -> bool:
    """
    Validates the structure and content of input demonstration data.
    
    Args:
        sequences: List of demonstration sequences.
        
    Returns:
        bool: True if valid.
        
    Raises:
        ValueError: If data is empty or vectors have inconsistent shapes.
    """
    if not sequences:
        raise ValueError("Input sequence list cannot be empty.")
    
    logger.info(f"Validating {len(sequences)} demonstration sequences...")
    
    ref_state_dim = None
    ref_action_dim = None
    
    for seq in sequences:
        if not seq.steps:
            logger.warning(f"Sequence {seq.sequence_id} is empty. Skipping validation for this specific seq.")
            continue
            
        for step in seq.steps:
            if ref_state_dim is None:
                ref_state_dim = len(step.state_vector)
                ref_action_dim = len(step.action_vector)
            else:
                if len(step.state_vector) != ref_state_dim or len(step.action_vector) != ref_action_dim:
                    raise ValueError("Inconsistent vector dimensions across steps.")
                    
            if not 0.0 <= step.task_progress <= 1.0:
                raise ValueError(f"Task progress must be between 0 and 1. Found: {step.task_progress}")
                
    return True

# --- Core Logic ---

def analyze_temporal_dynamics(sequences: List[DemonstrationSequence], window_size: int = 5) -> np.ndarray:
    """
    Analyzes the temporal dynamics to detect high-frequency jitter (common in habitual actions).
    
    Core Logic:
    Habitual actions (like scratching head) are often high-frequency, low-amplitude movements 
    superimposed on the task trajectory, or they break the flow of task progress.
    
    Args:
        sequences: List of demonstration sequences.
        window_size: Window for calculating moving variance.
        
    Returns:
        np.ndarray: A score array indicating the likelihood of a step being jitter/noise.
    """
    logger.info("Analyzing temporal dynamics for jitter detection...")
    
    jitter_scores = []
    
    for seq in sequences:
        actions = np.array([s.action_vector for s in seq.steps])
        
        # Calculate L2 norm of action changes
        action_norms = np.linalg.norm(actions, axis=1)
        
        # Moving average smoothing
        if len(action_norms) < window_size:
            jitter_scores.extend(np.zeros(len(action_norms)))
            continue
            
        # Calculate local variance (jitter indicator)
        df = pd.Series(action_norms)
        rolling_var = df.rolling(window=window_size).var().fillna(0)
        
        # Normalize scores
        if rolling_var.max() > 0:
            normalized_var = rolling_var / rolling_var.max()
        else:
            normalized_var = rolling_var
            
        jitter_scores.extend(normalized_var.values)
        
    return np.array(jitter_scores)

def infer_causal_relevance(sequences: List[DemonstrationSequence]) -> List[CausalInterventionResult]:
    """
    Main causal inference module. Distinguishes necessary causal chains from irrelevant noise.
    
    Methodology:
    1. **Correlation Analysis**: Calculate correlation between action magnitude and task progress.
    2. **Intervention Logic (Counterfactual)**: If an action is removed (or replaced with zero-action),
       does the predicted progress drop? Here approximated by analyzing if action aligns with 
       the gradient of progress.
    3. **PCA Projection**: Checks if actions lie in the principal subspace of successful demonstrations.
    
    Args:
        sequences: List of DemonstrationSequence objects.
        
    Returns:
        List of CausalInterventionResult for each sequence.
    """
    _validate_input_data(sequences)
    logger.info("Starting Causal Inference for Debiasing...")
    
    results = []
    
    # 1. Global Feature Extraction (PCA on Actions)
    all_actions = np.vstack([np.array([s.action_vector for s in seq.steps]) for seq in sequences])
    pca = PCA(n_components=min(0.95, all_actions.shape[1])) # Keep 95% variance
    pca.fit(all_actions)
    logger.info(f"PCA fitted with {pca.n_components_} components.")
    
    # 2. Process each sequence
    for seq in sequences:
        n_steps = len(seq.steps)
        states = np.array([s.state_vector for s in seq.steps])
        actions = np.array([s.action_vector for s in seq.steps])
        progress = np.array([s.task_progress for s in seq.steps])
        
        # Feature A: Progress Correlation
        # We want to see if the action magnitude correlates with progress change
        progress_delta = np.diff(progress, prepend=progress[0])
        action_magnitudes = np.linalg.norm(actions, axis=1)
        
        # Correlation coefficient per step (simplified: high action + high progress = good)
        # Normalize to 0-1
        causal_scores = np.zeros(n_steps)
        for i in range(n_steps):
            # Logic: If progress is increasing, the current action is likely causal.
            # If progress is flat but action is high, it's likely noise.
            if action_magnitudes[i] > 1e-3: # Avoid div by zero
                # Alignment score
                causal_scores[i] = max(0, progress_delta[i]) * action_magnitudes[i]
            else:
                causal_scores[i] = 0.0 # Zero action is rarely causal unless at goal
        
        # Feature B: PCA Reconstruction Error (Noise often lies outside main manifold)
        actions_proj = pca.transform(actions)
        actions_recon = pca.inverse_transform(actions_proj)
        recon_error = np.linalg.norm(actions - actions_recon, axis=1)
        
        # Normalize reconstruction error (High error = Potential Noise)
        if np.max(recon_error) > 0:
            noise_score_pca = recon_error / np.max(recon_error)
        else:
            noise_score_pca = np.zeros(n_steps)
            
        # Combine Scores
        # High Causal Score = Core Skill
        # High Noise Score (PCA) or Low Progress Correlation = Appearance Bias
        final_causal_prob = (causal_scores / (np.max(causal_scores) + 1e-6)) - 0.5 * noise_score_pca
        final_causal_prob = np.clip(final_causal_prob, 0, 1)
        
        # Generate Mask
        threshold = np.median(final_causal_prob) # Adaptive thresholding
        core_mask = final_causal_prob > threshold
        
        explanation = (
            f"Sequence {seq.sequence_id} analyzed. "
            f"Identified {np.sum(core_mask)} core steps out of {n_steps}. "
            f"Average Causal Probability: {np.mean(final_causal_prob):.4f}"
        )
        logger.info(explanation)
        
        result = CausalInterventionResult(
            core_skill_mask=core_mask,
            noise_mask=~core_mask,
            causal_score=final_causal_prob,
            explanation=explanation
        )
        results.append(result)
        
    return results

# --- Main Execution / Example ---

def run_debiasing_pipeline(sequences: List[DemonstrationSequence]) -> Dict[str, np.ndarray]:
    """
    Orchestrates the full pipeline to extract clean skills.
    
    Args:
        sequences: Input data.
        
    Returns:
        Dictionary containing cleaned trajectories and analysis metadata.
    """
    logger.info("=== Starting Auto-Embodied Imitation Debiasing Pipeline ===")
    
    # 1. Analyze Dynamics
    jitter_scores = analyze_temporal_dynamics(sequences)
    
    # 2. Causal Inference
    causal_results = infer_causal_relevance(sequences)
    
    # 3. Compile Results
    clean_data = {
        "cleaned_actions": [],
        "cleaned_states": [],
        "metadata": []
    }
    
    idx = 0
    for i, seq in enumerate(sequences):
        res = causal_results[i]
        
        # Filter data based on mask
        clean_actions = [s.action_vector for j, s in enumerate(seq.steps) if res.core_skill_mask[j]]
        clean_states = [s.state_vector for j, s in enumerate(seq.steps) if res.core_skill_mask[j]]
        
        clean_data["cleaned_actions"].append(np.array(clean_actions))
        clean_data["cleaned_states"].append(np.array(clean_states))
        clean_data["metadata"].append({
            "seq_id": seq.sequence_id,
            "noise_ratio": 1.0 - (len(clean_actions) / len(seq.steps))
        })
        
    logger.info("=== Pipeline Completed ===")
    return clean_data

# Example Usage
if __name__ == "__main__":
    # Create Mock Data
    def create_mock_data(n_samples=100):
        seqs = []
        for k in range(3):
            steps = []
            for i in range(n_samples):
                state = np.random.rand(10)
                
                # Simulate Causal Action (Progress increases)
                if 20 < i < 80:
                    action = np.random.normal(1.0, 0.1, 5) # Strong signal
                    progress = (i - 20) / 60.0
                # Simulate Noise (Habitual action at start/end)
                else:
                    action = np.random.normal(0.0, 0.8, 5) # Jitter/Noise
                    progress = 0.0 if i < 20 else 1.0
                    
                steps.append(DemonstrationStep(i, state, action, progress))
            seqs.append(DemonstrationSequence(f"demo_{k}", steps, True))
            
    mock_sequences = create_mock_data()
    
    # Run Pipeline
    try:
        results = run_debiasing_pipeline(mock_sequences)
        print(f"\nProcessed {len(results['cleaned_actions'])} sequences.")
        print(f"Average noise filtered: {np.mean([m['noise_ratio'] for m in results['metadata']]):.2%}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")