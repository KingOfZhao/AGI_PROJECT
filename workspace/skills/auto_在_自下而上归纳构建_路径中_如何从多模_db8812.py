"""
Module: prototype_extractor.py
Description: Advanced pattern recognition module for extracting cognitive prototypes
             from multimodal data (vision, text) using bottom-up induction.
Author: AGI System Core Team
Version: 1.0.0
"""

import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModalityData:
    """Dataclass for storing multimodal perception data."""
    visual_features: Optional[NDArray[np.float64]] = None
    text_embeddings: Optional[NDArray[np.float64]] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PrototypeNode:
    """
    Represents a cognitive prototype node extracted from data.
    
    Attributes:
        node_id: Unique identifier for the prototype
        centroid: The central feature vector of the prototype
        variance: Variance within the cluster (signal vs noise indicator)
        member_count: Number of instances contributing to this prototype
        modality_weights: Weights assigned to different modalities
        feature_importance: Importance scores for individual features
    """
    node_id: str
    centroid: NDArray[np.float64]
    variance: float
    member_count: int
    modality_weights: Dict[str, float] = field(default_factory=dict)
    feature_importance: Dict[int, float] = field(default_factory=dict)


def validate_input_data(
    data_samples: List[ModalityData],
    min_samples: int = 3
) -> Tuple[bool, str]:
    """
    Validate input data structure and quality.
    
    Args:
        data_samples: List of multimodal data samples
        min_samples: Minimum required samples for clustering
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not isinstance(data_samples, list):
        return False, "Input must be a list of ModalityData objects"
    
    if len(data_samples) < min_samples:
        return False, f"Insufficient samples: {len(data_samples)} < {min_samples}"
    
    # Check for empty data
    for i, sample in enumerate(data_samples):
        if not isinstance(sample, ModalityData):
            return False, f"Sample {i} is not a ModalityData instance"
        if sample.visual_features is None and sample.text_embeddings is None:
            return False, f"Sample {i} has no feature data"
    
    return True, "Validation successful"


def extract_prototypes(
    data_samples: List[ModalityData],
    eps: float = 0.5,
    min_cluster_size: int = 3,
    noise_threshold: float = 0.3,
    modality_balance: Optional[Dict[str, float]] = None
) -> List[PrototypeNode]:
    """
    Extract cognitive prototypes from multimodal data using bottom-up clustering.
    
    This function implements the core AGI pattern recognition capability:
    1. Fuses multimodal features with configurable weights
    2. Applies density-based clustering (DBSCAN) to find natural groupings
    3. Computes prototype centroids and variance (signal vs noise separation)
    4. Returns reusable cognitive nodes
    
    Args:
        data_samples: List of multimodal perception data
        eps: DBSCAN epsilon parameter (neighborhood radius)
        min_cluster_size: Minimum samples to form a cluster
        noise_threshold: Variance threshold to distinguish signal from noise
        modality_balance: Weights for different modalities (e.g., {'visual': 0.6, 'text': 0.4})
        
    Returns:
        List of PrototypeNode objects representing extracted cognitive patterns
        
    Raises:
        ValueError: If input validation fails
        RuntimeError: If clustering process fails
        
    Example:
        >>> samples = [
        ...     ModalityData(visual_features=np.random.rand(128), 
        ...                  text_embeddings=np.random.rand(768))
        ...     for _ in range(50)
        ... ]
        >>> prototypes = extract_prototypes(samples, eps=0.3)
        >>> print(f"Found {len(prototypes)} prototypes")
    """
    # Input validation
    is_valid, msg = validate_input_data(data_samples)
    if not is_valid:
        logger.error(f"Input validation failed: {msg}")
        raise ValueError(msg)
    
    logger.info(f"Starting prototype extraction from {len(data_samples)} samples")
    
    try:
        # Step 1: Feature fusion and normalization
        fused_features, modality_info = _fuse_multimodal_features(
            data_samples, 
            modality_balance
        )
        
        if fused_features.shape[0] < min_cluster_size:
            logger.warning("Not enough samples for clustering after fusion")
            return []
        
        # Step 2: Dimensionality reduction for better clustering
        n_components = min(50, fused_features.shape[1], fused_features.shape[0] - 1)
        pca = PCA(n_components=n_components)
        reduced_features = pca.fit_transform(fused_features)
        
        logger.info(f"Reduced features from {fused_features.shape[1]} to {n_components} dimensions")
        
        # Step 3: Density-based clustering
        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(reduced_features)
        
        dbscan = DBSCAN(eps=eps, min_samples=min_cluster_size, metric='euclidean')
        labels = dbscan.fit_predict(normalized_features)
        
        # Step 4: Extract prototypes from clusters
        prototypes = []
        unique_labels = set(labels) - {-1}  # Remove noise label
        
        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_features = fused_features[cluster_indices]
            
            # Compute centroid and variance
            centroid = np.mean(cluster_features, axis=0)
            variance = np.mean(np.var(cluster_features, axis=0))
            
            # Signal vs Noise distinction
            if variance > noise_threshold:
                logger.debug(f"Cluster {label} has high variance ({variance:.4f}), may contain noise")
                continue
            
            # Generate unique node ID
            node_id = _generate_node_id(centroid, label)
            
            # Compute feature importance based on variance contribution
            feature_variance = np.var(cluster_features, axis=0)
            feature_importance = {
                idx: float(1.0 / (var + 1e-8)) 
                for idx, var in enumerate(feature_variance) 
                if var < noise_threshold
            }
            
            prototype = PrototypeNode(
                node_id=node_id,
                centroid=centroid,
                variance=float(variance),
                member_count=len(cluster_indices),
                modality_weights=modality_info['weights'],
                feature_importance=feature_importance
            )
            
            prototypes.append(prototype)
            logger.info(f"Created prototype {node_id} with {len(cluster_indices)} members")
        
        logger.info(f"Extraction complete: {len(prototypes)} prototypes from {len(unique_labels)} clusters")
        return prototypes
        
    except Exception as e:
        logger.error(f"Prototype extraction failed: {str(e)}")
        raise RuntimeError(f"Clustering process failed: {str(e)}")


def _fuse_multimodal_features(
    data_samples: List[ModalityData],
    modality_balance: Optional[Dict[str, float]] = None
) -> Tuple[NDArray[np.float64], Dict]:
    """
    Fuse visual and text features into a unified representation.
    
    Args:
        data_samples: List of multimodal data
        modality_balance: Optional weights for modalities
        
    Returns:
        Tuple of (fused_features_array, modality_info_dict)
    """
    # Default balance
    if modality_balance is None:
        modality_balance = {'visual': 0.5, 'text': 0.5}
    
    features_list = []
    visual_dim = 0
    text_dim = 0
    
    for sample in data_samples:
        combined = []
        
        if sample.visual_features is not None:
            visual_features = np.asarray(sample.visual_features, dtype=np.float64)
            visual_dim = max(visual_dim, len(visual_features))
            combined.append(visual_features * modality_balance.get('visual', 0.5))
        
        if sample.text_embeddings is not None:
            text_features = np.asarray(sample.text_embeddings, dtype=np.float64)
            text_dim = max(text_dim, len(text_features))
            combined.append(text_features * modality_balance.get('text', 0.5))
        
        if combined:
            features_list.append(np.concatenate(combined))
    
    # Pad to consistent length
    max_len = max(len(f) for f in features_list)
    padded_features = np.zeros((len(features_list), max_len), dtype=np.float64)
    
    for i, feat in enumerate(features_list):
        padded_features[i, :len(feat)] = feat
    
    modality_info = {
        'weights': modality_balance,
        'visual_dim': visual_dim,
        'text_dim': text_dim,
        'total_dim': max_len
    }
    
    return padded_features, modality_info


def _generate_node_id(centroid: NDArray[np.float64], cluster_label: int) -> str:
    """
    Generate a unique identifier for a prototype node.
    
    Args:
        centroid: The centroid vector of the cluster
        cluster_label: The cluster label from DBSCAN
        
    Returns:
        Unique string identifier
    """
    hash_input = centroid.tobytes() + str(cluster_label).encode()
    hash_digest = hashlib.md5(hash_input).hexdigest()[:12]
    return f"proto_{hash_digest}"


def compute_prototype_similarity(
    prototype: PrototypeNode,
    query_features: NDArray[np.float64]
) -> float:
    """
    Compute similarity between a prototype and query features.
    
    Args:
        prototype: A PrototypeNode object
        query_features: Feature vector to compare against
        
    Returns:
        Similarity score between 0 and 1
        
    Example:
        >>> similarity = compute_prototype_similarity(prototypes[0], test_features)
        >>> print(f"Similarity: {similarity:.4f}")
    """
    if len(query_features) != len(prototype.centroid):
        # Adjust dimensions if needed
        if len(query_features) < len(prototype.centroid):
            query_features = np.pad(query_features, (0, len(prototype.centroid) - len(query_features)))
        else:
            query_features = query_features[:len(prototype.centroid)]
    
    # Cosine similarity
    dot_product = np.dot(prototype.centroid, query_features)
    norm_product = np.linalg.norm(prototype.centroid) * np.linalg.norm(query_features)
    
    if norm_product < 1e-10:
        return 0.0
    
    similarity = dot_product / norm_product
    
    # Adjust by variance (lower variance = more reliable prototype)
    confidence_weight = 1.0 / (1.0 + prototype.variance)
    
    return float(similarity * confidence_weight)


# Usage Example
if __name__ == "__main__":
    # Generate synthetic multimodal data
    np.random.seed(42)
    
    # Create 3 distinct clusters of data
    samples = []
    for cluster_id in range(3):
        base_visual = np.random.rand(128) * (cluster_id + 1)
        base_text = np.random.rand(768) * (cluster_id + 1)
        
        for _ in range(20):  # 20 samples per cluster
            noise_v = np.random.normal(0, 0.05, 128)
            noise_t = np.random.normal(0, 0.05, 768)
            
            sample = ModalityData(
                visual_features=base_visual + noise_v,
                text_embeddings=base_text + noise_t,
                metadata={'cluster': str(cluster_id)}
            )
            samples.append(sample)
    
    # Extract prototypes
    try:
        prototypes = extract_prototypes(
            samples,
            eps=0.5,
            min_cluster_size=5,
            noise_threshold=0.2,
            modality_balance={'visual': 0.4, 'text': 0.6}
        )
        
        print(f"\n=== Extraction Results ===")
        print(f"Total prototypes extracted: {len(prototypes)}")
        
        for proto in prototypes:
            print(f"\nPrototype ID: {proto.node_id}")
            print(f"  Members: {proto.member_count}")
            print(f"  Variance: {proto.variance:.6f}")
            print(f"  Modality weights: {proto.modality_weights}")
        
        # Test similarity computation
        if prototypes:
            test_features = np.random.rand(896)  # 128 + 768
            sim = compute_prototype_similarity(prototypes[0], test_features)
            print(f"\nTest similarity: {sim:.4f}")
            
    except Exception as e:
        print(f"Error: {e}")