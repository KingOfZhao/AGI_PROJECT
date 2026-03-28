"""
Module: auto_implicit_craft_digitization.py

Description:
    This module implements the 'Implicit Craft Digitization' skill for an AGI system.
    It focuses on reverse-fitting human expert decision-making processes (the 'feel' or 'touch')
    from high-dimensional sensor data (vibration, current, thermal, acoustic).

    The core logic identifies key state vector shifts that correlate with human adjustments,
    transforming implicit tacit knowledge into explicit parameter nodes.

Domain: Cognitive Science / Industrial AI
Author: Senior Python Engineer (AGI System)
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ImplicitCraftDigitizer")

@dataclass
class SensorSnapshot:
    """
    Represents a single time-frame of high-dimensional machine state.
    """
    timestamp: float
    current_amps: float
    vibration_hz: float
    acoustic_db: float
    thermal_celsius: float
    pressure_mpa: float

@dataclass
class AdjustmentEvent:
    """
    Represents a human intervention point.
    """
    timestamp: float
    parameter_name: str
    delta_value: float  # The change made by the human

@dataclass
class ExplicitParameterNode:
    """
    The output structure: A digitized rule or parameter node derived from analysis.
    """
    node_id: str
    source_features: List[str]
    threshold_condition: str
    confidence_score: float
    suggested_adjustment: str

class ImplicitCraftDigitizer:
    """
    A system to reverse-engineer expert 'touch' from sensor data.
    
    Capabilities:
    - Ingests high-dimensional state space data.
    - Detects significant deviations (state shifts) around human adjustment events.
    - Uses dimensionality reduction to isolate critical features.
    - Solidifies these into explicit logic nodes.
    """

    def __init__(self, sensitivity: float = 0.05, min_samples: int = 5):
        """
        Initialize the digitizer.

        Args:
            sensitivity (float): Threshold for detecting significant change (0.0 to 1.0).
            min_samples (int): Minimum number of similar events to confirm a pattern.
        """
        if not 0.0 < sensitivity < 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0.")
        
        self.sensitivity = sensitivity
        self.min_samples = min_samples
        self._scaler = StandardScaler()
        self._pca = PCA(n_components=0.95) # Keep 95% variance
        logger.info("ImplicitCraftDigitizer initialized with sensitivity %.2f", sensitivity)

    def _validate_inputs(
        self, 
        state_history: List[SensorSnapshot], 
        adjustment_log: List[AdjustmentEvent]
    ) -> bool:
        """
        Validates input data integrity and alignment.
        
        Args:
            state_history: List of machine states.
            adjustment_log: List of human adjustments.

        Returns:
            bool: True if valid.

        Raises:
            ValueError: If data is empty or timestamps are misaligned.
        """
        if not state_history or not adjustment_log:
            raise ValueError("Input data streams cannot be empty.")
        
        # Check temporal logic
        last_state_time = state_history[-1].timestamp
        for adj in adjustment_log:
            if adj.timestamp > last_state_time:
                raise ValueError(f"Adjustment at {adj.timestamp} is beyond sensor history range.")
        
        logger.debug("Input validation passed. %d states, %d events.", len(state_history), len(adjustment_log))
        return True

    def extract_feature_vectors(
        self, 
        state_history: List[SensorSnapshot], 
        adjustment_log: List[AdjustmentEvent], 
        window_size: int = 10
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Core Function 1: Extracts and isolates feature deltas around adjustment events.
        
        This function creates a 'Difference Vector' representing the state of the machine
        immediately before a human intervention, compared to a baseline stable state.
        
        Args:
            state_history: The continuous stream of sensor data.
            adjustment_log: The specific moments human intervened.
            window_size: The number of time steps to average before/after an event.

        Returns:
            A numpy array of shape (N_events, M_features) representing the state shifts.
        """
        self._validate_inputs(state_history, adjustment_log)
        
        # Convert state history to matrix for easier processing
        feature_names = ['current', 'vibration', 'acoustic', 'thermal', 'pressure']
        state_matrix = np.array([
            [s.current_amps, s.vibration_hz, s.acoustic_db, s.thermal_celsius, s.pressure_mpa] 
            for s in state_history
        ])
        
        delta_vectors = []
        
        logger.info("Extracting feature vectors for %d adjustment events...", len(adjustment_log))
        
        for event in adjustment_log:
            # Find index closest to event timestamp
            # (In production, use binary search or pandas. Here we simulate logic)
            event_idx = -1
            for i, s in enumerate(state_history):
                if s.timestamp >= event.timestamp:
                    event_idx = i
                    break
            
            if event_idx == -1 or event_idx < window_size:
                logger.warning("Event at %.2f is too close to start or end of history, skipping.", event.timestamp)
                continue

            # Compare 'Pre-event' window vs 'Global Baseline' or 'Post-event' window
            # Here we calculate the derivative of state features relative to the immediate past
            pre_window = state_matrix[event_idx - window_size : event_idx]
            baseline = state_matrix[0 : window_size] # Using start of session as 'ideal' state
            
            # Calculate deviation from baseline
            current_state_mean = np.mean(pre_window, axis=0)
            baseline_mean = np.mean(baseline, axis=0)
            
            delta = current_state_mean - baseline_mean
            delta_vectors.append(delta)

        if not delta_vectors:
            return np.array([]), feature_names

        return np.array(delta_vectors), feature_names

    def analyze_decision_boundary(
        self, 
        delta_matrix: np.ndarray, 
        feature_names: List[str]
    ) -> List[ExplicitParameterNode]:
        """
        Core Function 2: Identifies critical dimensions and creates explicit nodes.
        
        Uses PCA and clustering to find patterns in how the machine state looks when 
        the human decides to intervene.
        
        Args:
            delta_matrix: The matrix of state shifts before interventions.
            feature_names: Labels for the columns.

        Returns:
            A list of digitized parameter nodes (rules).
        """
        if delta_matrix.shape[0] < self.min_samples:
            logger.warning("Insufficient data points for robust analysis.")
            return []

        # 1. Normalize data
        try:
            scaled_data = self._scaler.fit_transform(delta_matrix)
        except ValueError as e:
            logger.error("Scaling failed: %s", e)
            return []

        # 2. Dimensionality Reduction (Find the 'Latent Craft Features')
        # This tells us which sensor combinations matter most
        reduced_data = self._pca.fit_transform(scaled_data)
        logger.info("PCA reduced dimensions from %d to %d components.", 
                    delta_matrix.shape[1], reduced_data.shape[1])

        # 3. Cluster the 'Intent' (Group similar adjustment scenarios)
        # We assume similar machine states trigger similar human 'feelings'
        clusterer = DBSCAN(eps=0.5, min_samples=self.min_samples)
        labels = clusterer.fit_predict(reduced_data)
        
        nodes = []
        unique_clusters = set(labels) - {-1} # Remove noise points

        for cluster_id in unique_clusters:
            # Extract original features for this cluster
            cluster_indices = np.where(labels == cluster_id)[0]
            cluster_data_original = delta_matrix[cluster_indices]
            
            # Calculate mean feature importance for this cluster
            mean_feature_values = np.mean(cluster_data_original, axis=0)
            
            # Identify the dominant feature (The 'Key' to the implicit craft)
            dominant_feature_idx = np.argmax(np.abs(mean_feature_values))
            dominant_feature_name = feature_names[dominant_feature_idx]
            dominant_value = mean_feature_values[dominant_feature_idx]
            
            # Generate the 'Explicit Node'
            threshold = np.std(cluster_data_original[:, dominant_feature_idx])
            condition = f"{dominant_feature_name} deviation > {threshold:.4f}"
            
            node = ExplicitParameterNode(
                node_id=f"craft_node_{cluster_id}",
                source_features=[dominant_feature_name],
                threshold_condition=condition,
                confidence_score=len(cluster_indices) / len(labels), # Simplified confidence
                suggested_adjustment=f"Compensate for {dominant_feature_name} drift"
            )
            nodes.append(node)
            logger.info("Discovered Craft Node: %s (Trigger: %s)", node.node_id, condition)

        return nodes

# Helper function for usage
def run_craft_digitization_simulation():
    """
    Helper function to simulate the process.
    """
    # 1. Generate Synthetic Data
    # Baseline machine state
    history = []
    t = 0.0
    for _ in range(1000):
        # Normal noise
        snap = SensorSnapshot(
            timestamp=t,
            current_amps=10.0 + np.random.normal(0, 0.1),
            vibration_hz=50.0 + np.random.normal(0, 1.0),
            acoustic_db=80.0 + np.random.normal(0, 2.0),
            thermal_celsius=45.0 + np.random.normal(0, 0.5),
            pressure_mpa=5.0 + np.random.normal(0, 0.1)
        )
        history.append(snap)
        t += 0.1

    # Simulate 'Expert Adjustments' triggered by specific hidden states
    # e.g., Human hears 'rough' vibration (acoustic + vibration correlation) and adjusts
    adjustments = []
    for i in range(50, 1000, 100):
        # Artificially inject a pattern that the human 'reacts' to
        # Vibration rises slightly, Acoustic rises
        history[i].vibration_hz += 5.0 
        history[i].acoustic_db += 8.0
        
        # Human reacts 5 steps later
        adj = AdjustmentEvent(
            timestamp=history[i+5].timestamp,
            parameter_name="pressure_mpa",
            delta_value=0.2
        )
        adjustments.append(adj)

    # 2. Run the System
    digitizer = ImplicitCraftDigitizer(sensitivity=0.1)
    
    # Extract
    deltas, names = digitizer.extract_feature_vectors(history, adjustments)
    
    # Analyze
    if deltas.size > 0:
        nodes = digitizer.analyze_decision_boundary(deltas, names)
        
        print("\n--- Digitization Results ---")
        for node in nodes:
            print(f"Node ID: {node.node_id}")
            print(f"  Trigger Condition: {node.threshold_condition}")
            print(f"  Suggested Action: {node.suggested_adjustment}")
            print(f"  Confidence: {node.confidence_score:.2f}")
            print("-" * 30)

if __name__ == "__main__":
    run_craft_digitization_simulation()