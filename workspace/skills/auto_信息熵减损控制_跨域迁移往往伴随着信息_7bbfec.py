"""
Module: auto_信息熵减损控制_跨域迁移往往伴随着信息_7bbfec

Description:
    This module implements an Information Entropy Loss Control system for 
    Cross-Domain Knowledge Transfer. It quantifies and controls "Semantic Entropy Loss" 
    when migrating knowledge units from a source domain to a target domain.
    
    It provides tools to calculate the Information Retention Rate (IRR) by comparing
    the structural and semantic embeddings of knowledge units before and after migration.

Key Concepts:
    - Source Knowledge Unit (SKU): The original concept (e.g., "Glaucoma Treatment").
    - Target Knowledge Unit (TKU): The mapped concept (e.g., "Pipeline Unclogging").
    - Core Structure Vector: The abstract logical skeleton (e.g., "Blockage -> Pressure -> Damage").
    - Semantic Entropy: A measure of uncertainty or information content.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("EntropyLossController")


class EntropyCalculationError(Exception):
    """Custom exception for errors during entropy calculation."""
    pass


class VectorDimensionMismatchError(Exception):
    """Custom exception for vector shape mismatches."""
    pass


@dataclass
class KnowledgeUnit:
    """
    Represents a unit of knowledge in a specific domain.
    
    Attributes:
        domain: The source domain (e.g., 'medical', 'engineering').
        concept_name: The name of the concept.
        features: A dictionary mapping feature names to their weights or values.
        embedding: A vector representation of the concept's semantics.
        timestamp: Creation time.
    """
    domain: str
    concept_name: str
    features: Dict[str, float]
    embedding: Optional[np.ndarray] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Validate data after initialization."""
        if not self.features:
            raise ValueError("Features dictionary cannot be empty.")
        if self.embedding is not None and not isinstance(self.embedding, np.ndarray):
            raise TypeError("Embedding must be a numpy ndarray.")


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculate the Cosine Similarity between two vectors.
    
    Args:
        vec_a: First vector.
        vec_b: Second vector.
        
    Returns:
        float: Cosine similarity score between -1 and 1.
    """
    if vec_a.shape != vec_b.shape:
        raise VectorDimensionMismatchError(
            f"Vector shapes mismatch: {vec_a.shape} vs {vec_b.shape}"
        )
    
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def _validate_inputs(source: KnowledgeUnit, target: KnowledgeUnit) -> None:
    """
    Helper function to validate input data before processing.
    
    Args:
        source: Source KnowledgeUnit.
        target: Target KnowledgeUnit.
        
    Raises:
        ValueError: If inputs are invalid.
    """
    if not isinstance(source, KnowledgeUnit) or not isinstance(target, KnowledgeUnit):
        raise TypeError("Inputs must be instances of KnowledgeUnit")
    
    if source.embedding is None or target.embedding is None:
        raise EntropyCalculationError("Both units must have embeddings for semantic analysis.")
        
    logger.debug(f"Input validation passed for {source.concept_name} -> {target.concept_name}")


def calculate_structural_retention(
    source: KnowledgeUnit, 
    target: KnowledgeUnit, 
    core_structure_keys: List[str]
) -> float:
    """
    Calculates the retention rate of specific structural features.
    
    This function checks if the keys defined in 'core_structure_keys' exist in both
    domains and calculates a weighted retention score.
    
    Args:
        source: The source domain KnowledgeUnit.
        target: The target domain KnowledgeUnit.
        core_structure_keys: List of keys representing the 'core structure' (e.g., ['pressure', 'blockage']).
        
    Returns:
        float: Structural retention rate (0.0 to 1.0).
        
    Example:
        >>> src = KnowledgeUnit("med", "glaucoma", {"pressure": 0.9, "nerve_damage": 0.8})
        >>> tgt = KnowledgeUnit("eng", "pipe", {"pressure": 0.8, "burst_risk": 0.7})
        >>> rate = calculate_structural_retention(src, tgt, ["pressure"])
    """
    if not core_structure_keys:
        logger.warning("Core structure keys list is empty. Returning 1.0 (neutral).")
        return 1.0

    retained_weight = 0.0
    total_weight = 0.0

    for key in core_structure_keys:
        # In a real scenario, this would involve semantic matching of keys.
        # Here we simulate exact key matching for structural logic.
        source_val = source.features.get(key, 0.0)
        target_val = target.features.get(key, 0.0)
        
        # Weight is determined by presence and magnitude
        weight = abs(source_val) 
        total_weight += weight
        
        if key in target.features:
            # Calculate similarity of the feature value (normalized difference)
            diff = abs(source_val - target_val)
            retention = max(0.0, 1.0 - diff)
            retained_weight += (retention * weight)
            
    if total_weight == 0:
        return 0.0
        
    return retained_weight / total_weight


def calculate_semantic_entropy_loss(
    source: KnowledgeUnit, 
    target: KnowledgeUnit
) -> Tuple[float, Dict[str, Any]]:
    """
    Quantifies the semantic entropy loss during transfer.
    
    Uses vector embeddings to calculate Information Retention Rate (IRR).
    IRR = Similarity(Source_Embedding, Target_Embedding).
    Entropy Loss = 1 - IRR.
    
    Args:
        source: Source KnowledgeUnit.
        target: Target KnowledgeUnit.
        
    Returns:
        Tuple[float, Dict]: 
            - Entropy loss value (0.0 to 2.0 theoretically, usually 0.0-1.0).
            - Metadata dictionary containing IRR and raw scores.
            
    Raises:
        EntropyCalculationError: If embeddings are missing or invalid.
    """
    try:
        _validate_inputs(source, target)
        
        # Calculate Semantic Similarity
        similarity = _cosine_similarity(source.embedding, target.embedding)
        
        # Information Retention Rate (IRR)
        irr = (similarity + 1) / 2  # Scale [-1, 1] to [0, 1]
        
        # Calculate Entropy Loss
        # Here we define loss as the reduction in information fidelity
        entropy_loss = 1.0 - irr
        
        metadata = {
            "source_concept": source.concept_name,
            "target_concept": target.concept_name,
            "source_domain": source.domain,
            "target_domain": target.domain,
            "cosine_similarity": round(similarity, 4),
            "retention_rate": round(irr, 4),
            "loss_value": round(entropy_loss, 4)
        }
        
        logger.info(
            f"Transfer {source.domain}->{target.domain}: "
            f"IRR={irr:.2%}, Loss={entropy_loss:.4f}"
        )
        
        return entropy_loss, metadata

    except Exception as e:
        logger.error(f"Failed to calculate entropy loss: {str(e)}")
        raise EntropyCalculationError(f"Calculation failed: {e}")


class CrossDomainMonitor:
    """
    A monitoring class to manage and log cross-domain transfer sessions.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: List[Dict] = []
        logger.info(f"Initialized Monitor Session: {session_id}")

    def monitor_transfer(
        self, 
        source_ku: KnowledgeUnit, 
        target_ku: KnowledgeUnit, 
        core_keys: List[str]
    ) -> Dict[str, Any]:
        """
        Monitors a single transfer event and generates a report.
        """
        try:
            struct_rate = calculate_structural_retention(source_ku, target_ku, core_keys)
            entropy_loss, sem_meta = calculate_semantic_entropy_loss(source_ku, target_ku)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "structural_retention": struct_rate,
                "semantic_entropy_loss": entropy_loss,
                "details": sem_meta,
                "status": "SUCCESS" if entropy_loss < 0.5 else "HIGH_LOSS_WARNING"
            }
            
            self.history.append(report)
            return report
            
        except Exception as e:
            logger.error(f"Transfer monitoring failed: {e}")
            return {"status": "ERROR", "message": str(e)}

# Usage Example (in docstring or main block)
if __name__ == "__main__":
    # 1. Define Source Knowledge (Medical: Glaucoma)
    # Semantic vector (abstract representation)
    medical_embedding = np.array([0.8, 0.2, 0.9, 0.1]) 
    source_knowledge = KnowledgeUnit(
        domain="medical",
        concept_name="Glaucoma Treatment",
        features={"pressure": 0.95, "blockage": 0.90, "biological_damage": 0.85},
        embedding=medical_embedding
    )

    # 2. Define Target Knowledge (Engineering: Pipeline Unclogging)
    # Note the vector similarity to medical_embedding
    engineering_embedding = np.array([0.75, 0.3, 0.85, 0.2]) 
    target_knowledge = KnowledgeUnit(
        domain="engineering",
        concept_name="Pipeline Unclogging",
        features={"pressure": 0.80, "blockage": 0.95, "mechanical_damage": 0.70},
        embedding=engineering_embedding
    )

    # 3. Initialize Monitor
    monitor = CrossDomainMonitor(session_id="AGI_TRANSFER_001")

    # 4. Monitor the transfer
    # We care about preserving the "pressure" and "blockage" logic
    core_logic = ["pressure", "blockage"]
    
    report = monitor.monitor_transfer(source_knowledge, target_knowledge, core_logic)

    print(f"\n--- Transfer Report ({source_knowledge.concept_name} -> {target_knowledge.concept_name}) ---")
    print(f"Structural Retention: {report['structural_retention']:.2%}")
    print(f"Semantic Entropy Loss: {report['semantic_entropy_loss']:.4f}")
    print(f"Status: {report['status']}")
    print(f"Details: {report['details']}")