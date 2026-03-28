"""
Module: urban_context_gan.py
Description: Implements the 'Urban Context Generative Adversarial Network' (UC-GAN).
             This system generates architectural designs by distilling historical styles,
             using Cross-Attention to retrieve and fuse typological features from a
             knowledge base, ensuring historical continuity without superficial pastiche.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SketchVector(BaseModel):
    """Represents the input architectural sketch as a latent vector."""
    vector_data: List[float] = Field(..., description="Latent vector representation of the sketch")
    dimensions: int = Field(..., gt=0, description="Dimensions of the vector")

    @validator('vector_data')
    def check_dimension_match(cls, v, values):
        if 'dimensions' in values and len(v) != values['dimensions']:
            raise ValueError("Vector data length does not match declared dimensions")
        return v

class TypologicalFeature(BaseModel):
    """Represents a single feature from the historical knowledge base."""
    feature_id: str
    style_epoch: str
    feature_vector: List[float]
    description: str

class DesignOutput(BaseModel):
    """Represents the generated design proposal."""
    generated_vector: List[float]
    matched_styles: List[str]
    confidence_score: float

# --- Core Components ---

class StyleDistiller:
    """
    Encapsulates the logic for 'Style Distillation' and feature fusion.
    Acts as the interface to the Historical Knowledge Base.
    """
    def __init__(self, knowledge_base_path: str = "mock_db"):
        self.knowledge_base = self._load_mock_knowledge_base()
        logger.info("StyleDistiller initialized with %d features.", len(self.knowledge_base))

    def _load_mock_knowledge_base(self) -> List[TypologicalFeature]:
        """Helper: Generates mock historical data for demonstration."""
        logger.debug("Loading mock knowledge base...")
        # Mocking distinct architectural features
        return [
            TypologicalFeature(
                feature_id="col_001", style_epoch="Classical",
                feature_vector=[0.8, 0.1, 0.5], description="Doric Column"
            ),
            TypologicalFeature(
                feature_id="mod_002", style_epoch="Modernism",
                feature_vector=[0.1, 0.9, 0.2], description="Ribbon Window"
            ),
            TypologicalFeature(
                feature_id="got_003", style_epoch="Gothic",
                feature_vector=[0.4, 0.4, 0.8], description="Pointed Arch"
            )
        ]

    def retrieve_similar_features(
        self, 
        query_vector: np.ndarray, 
        top_k: int = 2
    ) -> List[Tuple[TypologicalFeature, float]]:
        """
        Retrieves the most relevant historical features based on cosine similarity.
        
        Args:
            query_vector: The input sketch's latent vector.
            top_k: Number of features to retrieve.
            
        Returns:
            List of tuples containing (Feature, Similarity_Score).
        """
        if not isinstance(query_vector, np.ndarray):
            raise TypeError("Query vector must be a numpy array.")
            
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return []
            
        scores = []
        for feature in self.knowledge_base:
            f_vec = np.array(feature.feature_vector)
            # Ensure shapes match for demo purposes
            min_len = min(len(query_vector), len(f_vec))
            similarity = np.dot(query_vector[:min_len], f_vec[:min_len]) / (query_norm * np.linalg.norm(f_vec[:min_len]) + 1e-9)
            scores.append((feature, similarity))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

class CrossAttentionFusion:
    """
    Implements the Cross-Attention mechanism to fuse modern sketch intent
    with historical typological features.
    """
    def __init__(self, embed_dim: int = 64):
        self.embed_dim = embed_dim
        logger.info("CrossAttentionFusion initialized with embed_dim=%d", embed_dim)

    def _validate_inputs(
        self, 
        sketch_emb: np.ndarray, 
        context_embs: List[np.ndarray]
    ) -> None:
        """Data validation and boundary checks."""
        if sketch_emb.ndim != 1:
            raise ValueError("Sketch embedding must be a 1D array.")
        if not context_embs:
            raise ValueError("Context embeddings list cannot be empty.")
        # In a real scenario, we'd check embedding dimensions match model expectations

    def fuse_features(
        self, 
        sketch_embedding: np.ndarray, 
        retrieved_features: List[TypologicalFeature]
    ) -> np.ndarray:
        """
        Fuses the sketch embedding with retrieved historical features.
        
        Mechanism:
        1. Calculate attention weights based on sketch-query interaction.
        2. Weighted sum of historical features (Value).
        3. Residual connection to original sketch to preserve functionality.
        """
        if not retrieved_features:
            logger.warning("No features provided for fusion. Returning original sketch.")
            return sketch_embedding

        # Convert features to numpy array (Context)
        context_matrix = np.array([f.feature_vector for f in retrieved_features])
        
        # Pad/truncate to match dimensions for mock calculation
        target_dim = sketch_embedding.shape[0]
        padded_context = np.zeros((context_matrix.shape[0], target_dim))
        for i, row in enumerate(context_matrix):
            length = min(len(row), target_dim)
            padded_context[i, :length] = row[:length]

        try:
            # Mock Cross-Attention Calculation
            # Query (Q) = sketch, Key (K) = context, Value (V) = context
            # Attention(Q, K, V) = softmax(Q * K^T) * V
            
            # 1. Energy scores (Dot product)
            energy = np.dot(padded_context, sketch_embedding) # (Batch, Seq)
            
            # 2. Attention Weights (Softmax)
            exp_energy = np.exp(energy - np.max(energy))
            attention_weights = exp_energy / np.sum(exp_energy) + 1e-9
            
            # 3. Apply weights to Values
            # Reshape weights for broadcasting
            weights_reshaped = attention_weights[:, np.newaxis]
            weighted_context = np.sum(weights_reshaped * padded_context, axis=0)
            
            # 4. Fusion (Residual Connection + Alpha Blend)
            # Avoid superficial pastiche by keeping strong residual connection
            alpha = 0.3 # Strength of historical influence
            fused_vector = (1 - alpha) * sketch_embedding + alpha * weighted_context
            
            return fused_vector

        except Exception as e:
            logger.error("Error during feature fusion: %s", e)
            raise RuntimeError("Fusion process failed.") from e

# --- Main AGI Skill Function ---

def generate_contextual_design(
    sketch_input: SketchVector, 
    style_distiller: StyleDistiller, 
    fusion_engine: CrossAttentionFusion
) -> DesignOutput:
    """
    High-level function to generate a design based on urban context.
    
    Workflow:
    1. Convert sketch to latent vector.
    2. Retrieve historical references via Style Distiller.
    3. Fuse features via Cross-Attention.
    
    Args:
        sketch_input: Validated input sketch data.
        style_distiller: Instance of the historical knowledge engine.
        fusion_engine: Instance of the fusion mechanism.
        
    Returns:
        DesignOutput object containing the result.
    """
    logger.info("Starting design generation for sketch ID: %s", "current_request")
    
    # 1. Vector Preparation
    try:
        sketch_vec = np.array(sketch_input.vector_data)
    except Exception as e:
        logger.error("Failed to process input vector: %s", e)
        raise

    # 2. Knowledge Retrieval
    retrieved = style_distiller.retrieve_similar_features(sketch_vec, top_k=2)
    if not retrieved:
        logger.warning("No relevant historical context found.")
    
    matched_styles = [feat[0].style_epoch for feat in retrieved]
    feature_objs = [feat[0] for feat in retrieved]
    
    # 3. Feature Fusion
    generated_vec = fusion_engine.fuse_features(sketch_vec, feature_objs)
    
    # 4. Output Packaging
    result = DesignOutput(
        generated_vector=generated_vec.tolist(),
        matched_styles=matched_styles,
        confidence_score=float(np.mean([s for _, s in retrieved]))
    )
    
    logger.info("Design generation complete. Matched styles: %s", matched_styles)
    return result

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize systems
    distiller = StyleDistiller()
    fusion = CrossAttentionFusion()
    
    # Create a dummy sketch (e.g., leaning towards modernism but needing context)
    # Vector [0.1, 0.8, ...] suggests modern structure
    dummy_data = [0.1, 0.85, 0.2, 0.5, 0.9]
    input_sketch = SketchVector(vector_data=dummy_data, dimensions=len(dummy_data))
    
    try:
        # Run the AGI Skill
        design = generate_contextual_design(input_sketch, distiller, fusion)
        
        print("\n--- Generation Result ---")
        print(f"Matched Styles: {design.matched_styles}")
        print(f"Confidence: {design.confidence_score:.4f}")
        print(f"Output Vector (first 5): {design.generated_vector[:5]}")
        
    except Exception as e:
        logger.critical("System failed: %s", e)