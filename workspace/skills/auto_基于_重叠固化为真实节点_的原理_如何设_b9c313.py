"""
Module: skill_craft_skeleton_extractor.py

This module implements an algorithm to extract the Common Structural Skeleton (CSS)
from heterogeneous video streams of artisan operations. It is based on the principle
of "Overlapping Solidifies Reality" (重叠固化为真实节点).

The core logic involves:
1. Parsing temporal data from multiple sources (simulating video analysis).
2. Detecting 'Candidate Nodes' based on frequency and temporal density.
3. Filtering out 'Noise' (personal habits) that do not appear across different artisans.
4. Constructing a standardized Directed Acyclic Graph (DAG) representing the core craft.

Author: AGI System
Version: 1.0.0
"""

import logging
import heapq
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OperationNode:
    """
    Represents a distinct operation detected in a video stream.
    
    Attributes:
        name (str): The label of the operation (e.g., 'hammer_strike', 'heating').
        timestamp (float): The time in seconds when the operation occurred.
        confidence (float): Detection confidence score (0.0 to 1.0).
        features (np.ndarray): Vector features representing the visual characteristics.
    """
    name: str
    timestamp: float
    confidence: float
    features: np.ndarray = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp cannot be negative, got {self.timestamp}")


@dataclass
class ArtisanStream:
    """
    Represents a processed video stream from a single artisan session.
    
    Attributes:
        artisan_id (str): Unique identifier for the artisan.
        operations (List[OperationNode]): List of detected operations in chronological order.
    """
    artisan_id: str
    operations: List[OperationNode] = field(default_factory=list)


class StructuralSkeletonExtractor:
    """
    Extracts the common structural skeleton from multiple artisan streams based on
    the principle of 'Overlapping Solidifies Reality'.
    
    The algorithm assumes that true core techniques appear as clusters in time
    across multiple artisans, while personal habits appear as sparse outliers.
    """

    def __init__(self, 
                 time_threshold: float = 2.0, 
                 min_overlap_count: int = 3,
                 feature_similarity_threshold: float = 0.85):
        """
        Initialize the extractor.
        
        Args:
            time_threshold (float): The maximum time difference (seconds) to consider 
                                    two operations as temporally overlapping.
            min_overlap_count (int): The minimum number of artisans who must perform 
                                     an action for it to be considered a 'Real Node'.
            feature_similarity_threshold (float): Cosine similarity threshold for 
                                                  matching operations.
        """
        self.time_threshold = time_threshold
        self.min_overlap_count = min_overlap_count
        self.feature_similarity_threshold = feature_similarity_threshold
        logger.info("StructuralSkeletonExtractor initialized with threshold=%.2f, min_overlap=%d",
                    time_threshold, min_overlap_count)

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Helper function to calculate cosine similarity between two vectors.
        
        Args:
            vec_a: First vector.
            vec_b: Second vector.
            
        Returns:
            float: Similarity score between -1 and 1.
        """
        if vec_a.size == 0 or vec_b.size == 0:
            return 0.0
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(vec_a, vec_b) / (norm_a * norm_b)

    def _align_and_merge_nodes(self, 
                               node: OperationNode, 
                               candidate_clusters: Dict[str, List[Tuple[float, int, np.ndarray]]]) -> None:
        """
        Attempts to merge a node into existing candidate clusters or creates a new cluster.
        
        This is an auxiliary function implementing the 'Overlap' logic. It checks if the
        current node overlaps significantly with existing candidates.
        
        Args:
            node: The operation node to classify.
            candidate_clusters: Dictionary mapping node names to lists of 
                                (center_time, count, mean_feature_vector).
        """
        name = node.name
        time = node.timestamp
        feat = node.features
        
        if name not in candidate_clusters:
            candidate_clusters[name] = [(time, 1, feat)]
            return

        merged = False
        # Check against existing clusters of the same name
        for i, (center, count, mean_feat) in enumerate(candidate_clusters[name]):
            # Check temporal overlap and feature similarity
            sim = self._cosine_similarity(feat, mean_feat)
            if abs(time - center) < self.time_threshold and sim > self.feature_similarity_threshold:
                # Update cluster: move center slightly, increment count, update mean feature
                new_count = count + 1
                new_center = (center * count + time) / new_count
                # Incremental mean update for features (simplified)
                new_mean_feat = mean_feat + (feat - mean_feat) / new_count
                candidate_clusters[name][i] = (new_center, new_count, new_mean_feat)
                merged = True
                break
        
        if not merged:
            # Start a new potential cluster (could be noise)
            candidate_clusters[name].append((time, 1, feat))

    def extract_skeleton(self, streams: List[ArtisanStream]) -> Dict[str, Tuple[float, float]]:
        """
        Main function to extract the Common Structural Skeleton.
        
        Algorithm Steps:
        1. Aggregate all operations from all streams into a time-sorted global timeline.
        2. Iterate through the timeline to find overlapping nodes.
        3. Filter nodes based on the `min_overlap_count`.
        
        Args:
            streams: List of ArtisanStream objects containing operation data.
            
        Returns:
            Dict[str, Tuple[float, float]]: A dictionary where keys are the names of 
            the 'Real Nodes' and values are (mean_start_time, duration_estimate).
            
        Raises:
            ValueError: If input streams list is empty.
        """
        if not streams:
            logger.error("Input streams cannot be empty.")
            raise ValueError("Input streams cannot be empty.")

        logger.info("Processing %d artisan streams...", len(streams))
        
        # 1. Consolidate all nodes with source tracking
        # Format: (time, name, features, source_id)
        global_timeline = []
        for stream in streams:
            for op in stream.operations:
                # Only consider high confidence operations
                if op.confidence > 0.5:
                    global_timeline.append((op.timestamp, op.name, op.features, stream.artisan_id))
        
        # Sort by time
        global_timeline.sort(key=lambda x: x[0])
        
        # 2. Cluster detection logic
        # Stores: {node_name: [(center_time, overlap_count, mean_features), ...]}
        candidate_clusters: Dict[str, List[Tuple[float, int, np.ndarray]]] = {}
        
        # Sliding window or density-based approach (simplified here for clarity)
        # We treat the timeline sequentially
        for time, name, feat, src_id in global_timeline:
            # Create a dummy node to use the helper
            node = OperationNode(name, time, 1.0, feat)
            self._align_and_merge_nodes(node, candidate_clusters)
            
        # 3. Filtering: Solidification
        # Only keep clusters where overlap_count >= min_overlap_count
        real_nodes: Dict[str, Tuple[float, float]] = {}
        
        for name, clusters in candidate_clusters.items():
            for center, count, _ in clusters:
                if count >= self.min_overlap_count:
                    # In a real scenario, duration would be calculated from cluster width
                    # Here we estimate duration based on time_threshold
                    duration = self.time_threshold 
                    node_id = f"{name}_{len(real_nodes)}" # Unique ID
                    real_nodes[node_id] = (center, duration)
                    logger.debug(f"Solidified Real Node: {name} at {center:.2f}s (Count: {count})")

        logger.info("Extraction complete. Found %d real nodes.", len(real_nodes))
        
        # Sort output by time
        sorted_skeleton = dict(sorted(real_nodes.items(), key=lambda item: item[1][0]))
        return sorted_skeleton


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Generate synthetic data representing 3 artisans performing a similar task
    # Task structure: Prepare -> Process -> Finish
    
    def generate_mock_stream(artisan_id: str, noise_level: float = 0.0) -> ArtisanStream:
        ops = []
        # Common nodes (Skeleton)
        ops.append(OperationNode("prepare_material", 1.0 + noise_level, 0.9, np.random.rand(128)))
        ops.append(OperationNode("heat_source", 5.0 + noise_level, 0.95, np.random.rand(128)))
        ops.append(OperationNode("main_forge", 10.0 + noise_level, 0.88, np.random.rand(128)))
        ops.append(OperationNode("quench", 15.0 + noise_level, 0.92, np.random.rand(128)))
        
        # Noise nodes (Personal habits)
        if artisan_id == "artisan_1":
            ops.append(OperationNode("wipe_sweat", 7.0, 0.8, np.random.rand(128))) # Noise
        if artisan_id == "artisan_2":
            ops.append(OperationNode("adjust_apron", 3.0, 0.7, np.random.rand(128))) # Noise
            ops.append(OperationNode("check_phone", 20.0, 0.6, np.random.rand(128))) # Noise
        if artisan_id == "artisan_3":
            pass # No noise
        
        # Sort by timestamp just in case
        ops.sort(key=lambda x: x.timestamp)
        return ArtisanStream(artisan_id=artisan_id, operations=ops)

    try:
        # Create mock streams
        stream1 = generate_mock_stream("artisan_1", noise_level=0.2)
        stream2 = generate_mock_stream("artisan_2", noise_level=-0.1)
        stream3 = generate_mock_stream("artisan_3", noise_level=0.0)
        
        # Initialize Extractor
        extractor = StructuralSkeletonExtractor(
            time_threshold=2.0,
            min_overlap_count=2, # Require at least 2 artisans to agree
            feature_similarity_threshold=0.5 # Lowered for random vectors
        )
        
        # Extract Skeleton
        skeleton = extractor.extract_skeleton([stream1, stream2, stream3])
        
        print("\n=== Extracted Structural Skeleton ===")
        print(f"{'Node ID':<20} | {'Start Time (s)':<15} | {'Duration (s)':<15}")
        print("-" * 55)
        for node_id, (start, dur) in skeleton.items():
            print(f"{node_id:<20} | {start:<15.2f} | {dur:<15.2f}")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)