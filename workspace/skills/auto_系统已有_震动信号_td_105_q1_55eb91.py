"""
Module: cross_modal_semantic_alignment.py

Description:
    This module implements a 'Cross-Modal Semantic Alignment Matrix' mechanism.
    It bridges the gap between independent processing nodes—specifically
    'Vibration Signals' (td_105) and 'Text Logs' (td_106)—by mapping them
    into a unified 'Fault Cause' vector space.

    It addresses the lack of semantic correlation in multi-modal AGI systems
    by projecting disparate data types (visual/audio waveforms, text) into
    a shared latent space for reasoning.

Author: AGI System Core Engineering
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
VECTOR_DIMENSION = 128  # Dimension of the shared semantic space
DEFAULT_ALIGNMENT_THRESHOLD = 0.85
MAX_INPUT_VECTOR_NORM = 1000.0  # Boundary check for sanity


class SemanticVector(BaseModel):
    """Data model for a semantic vector derived from a sensor or log."""
    source_id: str = Field(..., description="ID of the source node (e.g., td_105_Q1_3_4162)")
    modality: str = Field(..., description="Type of data: 'vibration', 'text', or 'visual'")
    timestamp: datetime = Field(default_factory=datetime.now)
    vector: List[float] = Field(..., description="The embedding vector")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('vector')
    def check_vector_dimension(cls, v):
        if len(v) != VECTOR_DIMENSION:
            raise ValueError(f"Vector dimension must be {VECTOR_DIMENSION}, got {len(v)}")
        return v


class FaultHypothesis(BaseModel):
    """Represents a potential fault cause in the vector space."""
    fault_id: str
    description: str
    reference_vector: List[float]


class AlignmentMatrix:
    """
    Core class for managing the cross-modal alignment matrix.
    Handles the projection and alignment of different modalities into a shared space.
    """

    def __init__(self, vector_dim: int = VECTOR_DIMENSION):
        self.vector_dim = vector_dim
        self.projection_weights: Dict[str, np.ndarray] = {}
        self.fault_space: Dict[str, np.ndarray] = {}
        logger.info(f"AlignmentMatrix initialized with dimension {vector_dim}")

    def register_modality(self, modality_name: str, projection_matrix: Optional[np.ndarray] = None):
        """
        Registers a new modality and its projection weights to the shared space.
        If no matrix is provided, an identity matrix (no-op) is used.
        """
        if modality_name in self.projection_weights:
            logger.warning(f"Modality {modality_name} already registered. Overwriting.")

        if projection_matrix is None:
            # Identity transformation for testing or pre-aligned vectors
            self.projection_weights[modality_name] = np.eye(self.vector_dim)
        else:
            if projection_matrix.shape != (self.vector_dim, self.vector_dim):
                raise ValueError(f"Projection matrix must be square {self.vector_dim}x{self.vector_dim}")
            self.projection_weights[modality_name] = projection_matrix
        
        logger.info(f"Modality '{modality_name}' registered successfully.")

    def _validate_vector(self, raw_vector: List[float]) -> np.ndarray:
        """
        Helper function to validate and sanitize input vectors.
        Ensures numerical stability and boundary compliance.
        """
        vec = np.array(raw_vector, dtype=np.float32)
        
        # Check for NaN or Infinity
        if not np.all(np.isfinite(vec)):
            raise ValueError("Input vector contains NaN or Infinity values.")
            
        # Boundary Check: Prevent overflow in subsequent calculations
        norm = np.linalg.norm(vec)
        if norm > MAX_INPUT_VECTOR_NORM:
            logger.warning(f"Vector norm {norm} exceeds max limit. Normalizing.")
            vec = vec / norm
            
        return vec

    def project_to_shared_space(self, semantic_vec: SemanticVector) -> np.ndarray:
        """
        Projects a specific modality vector into the shared 'Fault Cause' space.
        
        Args:
            semantic_vec (SemanticVector): Validated input vector object.
            
        Returns:
            np.ndarray: The projected vector in the shared space.
        """
        if semantic_vec.modality not in self.projection_weights:
            raise KeyError(f"Modality '{semantic_vec.modality}' is not registered in the alignment matrix.")
            
        try:
            raw_vec = self._validate_vector(semantic_vec.vector)
            weights = self.projection_weights[semantic_vec.modality]
            
            # Matrix multiplication for projection
            projected_vec = np.dot(weights, raw_vec)
            
            # L2 Normalization for cosine similarity search later
            norm = np.linalg.norm(projected_vec)
            if norm == 0:
                return projected_vec
            return projected_vec / norm
            
        except Exception as e:
            logger.error(f"Projection failed for {semantic_vec.source_id}: {e}")
            raise

    def calculate_alignment_score(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Calculates the semantic similarity (alignment) between two vectors in the shared space.
        Uses Cosine Similarity.
        """
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(dot_product / (norm_a * norm_b))

    def diagnose_fault(self, 
                       vibration_input: SemanticVector, 
                       log_input: SemanticVector) -> Dict[str, Any]:
        """
        Core Skill Function: Performs cross-modal reasoning to identify fault causes.
        
        It aligns the 'Vibration Signal' and 'Text Log' into the shared space,
        calculates their coherence, and outputs a unified diagnostic result.
        
        Args:
            vibration_input: Data from node td_105 (震动信号).
            log_input: Data from node td_106 (文本日志).
            
        Returns:
            A dictionary containing alignment status and diagnosis confidence.
        """
        logger.info(f"Starting diagnosis for Vibration:{vibration_input.source_id} and Log:{log_input.source_id}")
        
        try:
            # 1. Project both modalities
            vib_proj = self.project_to_shared_space(vibration_input)
            log_proj = self.project_to_shared_space(log_input)
            
            # 2. Calculate Cross-Modal Alignment (Are the sensors telling the same story?)
            cross_modal_score = self.calculate_alignment_score(vib_proj, log_proj)
            
            # 3. Generate Unified Fault Vector (Fusion)
            unified_vector = (vib_proj + log_proj) / 2.0
            unified_vector = unified_vector / np.linalg.norm(unified_vector)
            
            # 4. Check against known fault hypotheses (Mock implementation)
            # In a real system, this would query a vector database
            fault_confidence = np.max(unified_vector)  # Simplified logic
            
            result = {
                "status": "ALIGNED" if cross_modal_score > DEFAULT_ALIGNMENT_THRESHOLD else "CONFLICT",
                "cross_modal_similarity": cross_modal_score,
                "diagnosis_confidence": float(fault_confidence),
                "timestamp": datetime.now().isoformat(),
                "fusion_vector_sample": unified_vector[:5].tolist() # Sample for visualization
            }
            
            logger.info(f"Diagnosis complete. Status: {result['status']}, Score: {cross_modal_score:.4f}")
            return result

        except ValidationError as ve:
            logger.error(f"Input validation error: {ve}")
            return {"status": "ERROR", "message": str(ve)}
        except Exception as e:
            logger.error(f"Critical failure in diagnosis pipeline: {e}")
            return {"status": "ERROR", "message": "Internal processing error"}


# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the Matrix System
    matrix_system = AlignmentMatrix(vector_dim=128)
    
    # Register Modalities (Simulating learned projection weights)
    # In reality, these would be trained neural network projection heads
    matrix_system.register_modality("vibration", projection_matrix=np.eye(128) * 0.9) 
    matrix_system.register_modality("text", projection_matrix=np.eye(128) * 1.1)

    # Create Mock Inputs
    # Simulating a frequency spike in vibration
    vib_data = [0.0] * 128
    vib_data[10] = 5.0  # High energy at index 10
    
    # Simulating a text log embedding that correlates (semantically similar direction)
    log_data = [0.0] * 128
    log_data[10] = 4.8  # Similar pattern in latent space
    
    try:
        input_vib = SemanticVector(
            source_id="td_105_Q1_3_4162",
            modality="vibration",
            vector=vib_data
        )
        
        input_log = SemanticVector(
            source_id="td_106_Q4_0_3672",
            modality="text",
            vector=log_data
        )
        
        # Execute Diagnosis
        diagnosis = matrix_system.diagnose_fault(input_vib, input_log)
        
        print("\n--- Diagnosis Result ---")
        print(f"Status: {diagnosis.get('status')}")
        print(f"Cross-Modal Similarity: {diagnosis.get('cross_modal_similarity'):.4f}")
        print(f"Confidence: {diagnosis.get('diagnosis_confidence'):.4f}")
        
    except Exception as e:
        print(f"System Error: {e}")