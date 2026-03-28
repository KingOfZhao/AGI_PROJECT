"""
Module: auto_conceptualization_e58a4f
Description: To support 'human granting new concepts', this module enables the system to 
             possess 'anomaly detection' capabilities. It specifically addresses the 
             scenario where a SKILL execution fails (falsification) and cannot be 
             explained by existing 'real nodes' (known concepts). It automatically 
             extracts feature vectors from these failure cases, packs them into an 
             'unknown concept cluster', and pushes them to a human expert for definition.
Domain: Human-Computer Interaction / AGI Cognitive Architecture
"""

import logging
import numpy as np
import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillExecutionContext:
    """Represents the context in which a Skill was executed."""
    skill_id: str
    input_data: Dict[str, Any]
    expected_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    execution_success: bool
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class UnknownConceptCluster:
    """Data structure for an undefined concept cluster awaiting human definition."""
    cluster_id: str
    feature_vectors: np.ndarray
    centroid: np.ndarray
    anomaly_score: float
    creation_time: datetime.datetime
    status: str = "PENDING_DEFINITION"
    suggested_tags: List[str] = field(default_factory=list)

class ConceptAnomalyDetector:
    """
    Core class for detecting execution failures that defy current knowledge graphs
    and packaging them for human review.
    """

    def __init__(self, known_concept_centers: Dict[str, np.ndarray], epsilon: float = 0.5):
        """
        Initialize the detector.

        Args:
            known_concept_centers (Dict[str, np.ndarray]): A dictionary mapping existing 
                                                           concept IDs to their feature centroids.
            epsilon (float): The threshold distance for considering an anomaly 'unknown'.
        """
        self.known_concept_centers = known_concept_centers
        self.epsilon = epsilon
        self._buffer: List[Tuple[np.ndarray, SkillExecutionContext]] = []
        logger.info("ConceptAnomalyDetector initialized with %d known concepts.", len(known_concept_centers))

    def _validate_vector(self, vector: np.ndarray) -> bool:
        """
        Validate the feature vector format and integrity.
        
        Args:
            vector (np.ndarray): The vector to validate.
            
        Returns:
            bool: True if valid, raises ValueError otherwise.
        """
        if not isinstance(vector, np.ndarray):
            raise TypeError("Feature vector must be a numpy array.")
        if vector.ndim != 1:
            raise ValueError("Feature vector must be 1-dimensional.")
        if np.isnan(vector).any() or np.isinf(vector).any():
            raise ValueError("Feature vector contains NaN or Infinity values.")
        return True

    def _extract_features(self, context: SkillExecutionContext) -> np.ndarray:
        """
        [Helper Function] Extracts a feature vector from the execution context.
        
        In a real AGI system, this would involve encoding the state delta 
        (Expected vs Actual) into a semantic vector space.
        
        Args:
            context (SkillExecutionContext): The context of the failed skill.
            
        Returns:
            np.ndarray: A normalized feature vector representing the failure.
        """
        # Mock logic: In reality, use a pre-trained encoder (e.g., BERT for text, CNN for visual state)
        # Here we simulate a vector based on the hash of the state difference
        state_diff = str(context.expected_state) + str(context.actual_state)
        # Simulating a 128-dimension embedding
        np.random.seed(hash(state_diff) % (2**32))
        vector = np.random.rand(128)
        return vector

    def analyze_execution(self, context: SkillExecutionContext) -> bool:
        """
        [Core Function 1] Analyzes a failed skill execution to determine if it represents 
        an 'Unknown Concept'.
        
        Logic:
        1. Check if execution failed.
        2. Extract feature vector.
        3. Check if it matches any existing 'Real Node' (Known Concept).
        4. If unknown, buffer it for clustering.
        
        Args:
            context (SkillExecutionContext): The execution data.
            
        Returns:
            bool: True if an anomaly is detected and buffered, False otherwise.
        """
        if context.execution_success:
            return False

        logger.info(f"Analyzing failed execution for Skill: {context.skill_id}")
        
        try:
            vector = self._extract_features(context)
            self._validate_vector(vector)
            
            # Check against known concepts (Real Nodes)
            is_explainable = False
            for concept_id, center in self.known_concept_centers.items():
                distance = np.linalg.norm(vector - center)
                if distance < self.epsilon:
                    logger.info(f"Failure explained by known concept: {concept_id}")
                    is_explainable = True
                    break
            
            if not is_explainable:
                logger.warning("Unexplainable anomaly detected! Buffering for clustering.")
                self._buffer.append((vector, context))
                return True

        except (ValueError, TypeError) as e:
            logger.error(f"Feature extraction failed: {e}")
            return False
        
        return False

    def generate_concept_cluster(self, min_samples: int = 2) -> Optional[UnknownConceptCluster]:
        """
        [Core Function 2] Aggregates buffered anomalies into a concept cluster using DBSCAN.
        
        If a dense cluster of similar 'unknown' failures is found, it is packaged
        as a candidate for a new concept.
        
        Args:
            min_samples (int): Minimum number of samples to form a cluster.
            
        Returns:
            Optional[UnknownConceptCluster]: The packaged cluster, or None if no pattern found.
        """
        if len(self._buffer) < min_samples:
            logger.info("Insufficient data to form a concept cluster.")
            return None

        logger.info(f"Attempting to cluster {len(self._buffer)} anomalies...")
        
        # Prepare data
        vectors = np.array([item[0] for item in self._buffer])
        contexts = [item[1] for item in self._buffer]
        
        # Standardization
        scaler = StandardScaler()
        vectors_scaled = scaler.fit_transform(vectors)
        
        # Clustering (DBSCAN finds clusters without knowing K)
        db = DBSCAN(eps=0.5, min_samples=min_samples).fit(vectors_scaled)
        labels = db.labels_
        
        # Find the largest cluster (ignoring noise label -1)
        unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
        
        if len(unique_labels) == 0:
            logger.info("No significant clusters found in anomalies (all noise).")
            return None
            
        main_cluster_label = unique_labels[np.argmax(counts)]
        
        # Extract vectors belonging to the main cluster
        cluster_indices = np.where(labels == main_cluster_label)[0]
        cluster_vectors = vectors[cluster_indices]
        
        # Calculate centroid for the new concept
        centroid = np.mean(cluster_vectors, axis=0)
        
        # Calculate anomaly score (inverse of density or distance to known concepts)
        min_dist_to_known = float('inf')
        for center in self.known_concept_centers.values():
            dist = np.linalg.norm(centroid - center)
            if dist < min_dist_to_known:
                min_dist_to_known = dist
        anomaly_score = min_dist_to_known # Higher is better (more novel)

        # Package the cluster
        new_cluster = UnknownConceptCluster(
            cluster_id=f"unk_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            feature_vectors=cluster_vectors,
            centroid=centroid,
            anomaly_score=anomaly_score,
            creation_time=datetime.datetime.now(),
            suggested_tags=["auto-generated", "failure-analysis"]
        )
        
        # Clear processed items from buffer (simplified logic: clear all for demo)
        self._buffer.clear()
        
        logger.info(f"New Unknown Concept Cluster generated: {new_cluster.cluster_id}")
        return new_cluster

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Setup: Initialize with some existing 'Real Nodes' (Known Concepts)
    # Let's say we have concepts for "Object_Obstacle" and "Low_Battery"
    known_concepts = {
        "obj_obs": np.random.rand(128) * 0.2 + 0.1, # Clustered around 0.1-0.3
        "low_batt": np.random.rand(128) * 0.2 + 0.8 # Clustered around 0.8-1.0
    }

    detector = ConceptAnomalyDetector(known_concepts, epsilon=1.5)

    # 2. Simulate Failures
    # Case A: Failure explainable by "Object_Obstacle" (Vector close to center)
    explainable_context = SkillExecutionContext(
        skill_id="move_forward",
        input_data={"speed": 5},
        expected_state={"position": 10},
        actual_state={"position": 0, "error": "bumped"},
        execution_success=False
    )
    
    # Case B: Unexplainable Failure (Vector will be random, likely far from known centers)
    # We force the random seed in the helper to generate specific vectors, 
    # but in real flow, distinct inputs create distinct vectors.
    unexplainable_context_1 = SkillExecutionContext(
        skill_id="grasp_object",
        input_data={"target": "hammer"},
        expected_state={"gripped": True},
        actual_state={"gripped": False, "error": "slippery_surface"},
        execution_success=False
    )
    
    unexplainable_context_2 = SkillExecutionContext(
        skill_id="lift_object",
        input_data={"target": "hammer"},
        expected_state={"lifted": True},
        actual_state={"lifted": False, "error": "slippery_surface"},
        execution_success=False
    )

    # 3. Process Failures
    print("Processing known failure...")
    detector.analyze_execution(explainable_context)
    
    print("Processing unknown failures...")
    detector.analyze_execution(unexplainable_context_1)
    detector.analyze_execution(unexplainable_context_2)

    # 4. Trigger Clustering
    print("Checking for new concepts...")
    new_concept = detector.generate_concept_cluster(min_samples=2)

    if new_concept:
        print("\n>>> NEW CONCEPT DISCOVERED <<<")
        print(f"Cluster ID: {new_concept.cluster_id}")
        print(f"Samples Count: {len(new_concept.feature_vectors)}")
        print(f"Novelty Score: {new_concept.anomaly_score:.4f}")
        print("Action: Pushing to Human Expert Interface for naming...")
    else:
        print("No new concepts formed yet.")