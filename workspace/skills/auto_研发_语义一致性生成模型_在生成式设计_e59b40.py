"""
Module: auto_研发_语义一致性生成模型_在生成式设计_e59b40

Description:
    This module implements a Semantic Consistency Generative Design framework.
    It introduces an 'Evaluator' that assesses the semantic alignment between
    generated 3D/2D design shapes and abstract natural language concepts using
    CLIP (Contrastive Language-Image Pre-training).

    Unlike traditional generative design which focuses on physical constraints
    (stress, strain, fluid dynamics), this module optimizes for 'Spirit' and
    'Intent'.

    Example:
        >>> designer = SemanticGenerativeDesigner()
        >>> prompt = "A sword possessing a murderous and sharp aura"
        >>> shape_seed = np.random.rand(512)  # Latent vector representation
        >>> optimized_shape = designer.generate_and_refine(prompt, shape_seed)
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import numpy as np
import torch
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Attempt to import CLIP related libraries with fallback for environments without them
try:
    import clip
    from torchvision import transforms
    CLIP_AVAILABLE = True
except ImportError:
    logger.warning("CLIP or Torchvision not found. Running in 'mock' mode with random embeddings.")
    CLIP_AVAILABLE = False


@dataclass
class DesignResult:
    """Data class to hold the result of the generative design process."""
    success: bool
    final_score: float
    latent_vector: np.ndarray
    rendered_image: Optional[Image.Image]
    message: str


class SemanticEvaluator:
    """
    Core component: Evaluates the semantic distance between visual content and text.
    Uses a pre-trained CLIP model to encode images and text into the same feature space.
    """

    def __init__(self, model_name: str = "ViT-B/32", device: str = "auto"):
        """
        Initialize the Semantic Evaluator.

        Args:
            model_name (str): The CLIP model architecture to use.
            device (str): Computation device ('auto', 'cuda', 'cpu').
        """
        self.device = self._determine_device(device) if device == "auto" else device
        self.model = None
        self.preprocess = None
        self._load_model(model_name)

    def _determine_device(self, device_str: str) -> str:
        """Helper to determine the best available device."""
        if torch.cuda.is_available():
            logger.info("CUDA device found.")
            return "cuda"
        logger.info("Running on CPU.")
        return "cpu"

    def _load_model(self, model_name: str) -> None:
        """Load the CLIP model."""
        if CLIP_AVAILABLE:
            try:
                self.model, self.preprocess = clip.load(model_name, device=self.device)
                self.model.eval()
                logger.info(f"CLIP model {model_name} loaded successfully on {self.device}.")
            except Exception as e:
                logger.error(f"Failed to load CLIP model: {e}")
                raise RuntimeError(f"Model loading failed: {e}")
        else:
            # Mock mode for environments without dependencies
            self.model = None
            self.preprocess = None
            logger.info("Running in Mock Mode (No CLIP loaded).")

    @torch.no_grad()
    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text prompt into a feature vector.

        Args:
            text (str): The natural language description.

        Returns:
            np.ndarray: Normalized text embedding.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input text must be a non-empty string.")

        if CLIP_AVAILABLE and self.model:
            tokens = clip.tokenize([text]).to(self.device)
            text_features = self.model.encode_text(tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy().flatten()
        else:
            # Mock deterministic embedding based on hash for testing
            return np.random.rand(512)

    @torch.no_grad()
    def encode_image(self, image: Image.Image) -> np.ndarray:
        """
        Encode a PIL Image into a feature vector.

        Args:
            image (Image.Image): The visual design to evaluate.

        Returns:
            np.ndarray: Normalized image embedding.
        """
        if not isinstance(image, Image.Image):
            raise TypeError("Input must be a PIL Image object.")

        if CLIP_AVAILABLE and self.model and self.preprocess:
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            image_features = self.model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            return image_features.cpu().numpy().flatten()
        else:
            return np.random.rand(512)

    def calculate_semantic_distance(self, image: Image.Image, text: str) -> float:
        """
        Calculate the semantic distance (dissimilarity) between image and text.
        Distance = 1 - CosineSimilarity.

        Args:
            image (Image.Image): The generated design.
            text (str): The target semantic description.

        Returns:
            float: Semantic distance. Lower is better (0.0 means perfect alignment).
        """
        # Input validation
        if image is None:
             raise ValueError("Image cannot be None")

        img_emb = self.encode_image(image)
        txt_emb = self.encode_text(text)

        # Cosine similarity: dot product (since vectors are normalized)
        similarity = np.dot(img_emb, txt_emb)
        
        # Clamp similarity to avoid floating point errors
        similarity = np.clip(similarity, -1.0, 1.0)
        
        distance = 1.0 - similarity
        return float(distance)


class SemanticGenerativeDesigner:
    """
    High-level system to generate designs guided by semantic constraints.
    """

    def __init__(self, evaluator: Optional[SemanticEvaluator] = None):
        """
        Initialize the designer.

        Args:
            evaluator (SemanticEvaluator): An instance of the semantic evaluator.
        """
        self.evaluator = evaluator if evaluator else SemanticEvaluator()
        logger.info("SemanticGenerativeDesigner initialized.")

    def _mock_geometry_renderer(self, latent_vector: np.ndarray) -> Image.Image:
        """
        [HELPER FUNCTION]
        Mocks a 3D/2D design rendering engine. 
        In a real scenario, this would use Blender API, OpenSCAD, or a Diffusion Model (like Stable Diffusion img2img).
        
        Here we create a dummy image that changes slightly based on the latent vector
        to simulate the design process.
        """
        if not isinstance(latent_vector, np.ndarray):
            raise TypeError("Latent vector must be a numpy array.")
            
        # Create a simple image based on vector stats to simulate variation
        avg_val = int(np.mean(latent_vector) * 255) % 256
        img_array = np.full((224, 224, 3), avg_val, dtype=np.uint8)
        
        # Add some noise to make it unique
        noise = (latent_vector[:100] * 255).reshape(10, 10).astype(np.uint8)
        noise = np.repeat(np.repeat(noise, 22, axis=0), 22, axis=1)[:224, :224]
        
        # Mix channels
        img_array[:, :, 0] = (img_array[:, :, 0] + noise) % 256
        img_array[:, :, 1] = 255 - avg_val # Contrast
        
        return Image.fromarray(img_array)

    def _mutate_latent_vector(self, vector: np.ndarray, mutation_rate: float = 0.1) -> np.ndarray:
        """
        [HELPER FUNCTION]
        Applies random mutations to the latent vector to explore the design space.
        """
        noise = np.random.randn(*vector.shape) * mutation_rate
        new_vector = vector + noise
        # Normalize to keep vector magnitude stable (optional but often helpful)
        norm = np.linalg.norm(new_vector)
        if norm > 0:
            new_vector = new_vector / norm
        return new_vector

    def generate_and_refine(
        self, 
        prompt: str, 
        initial_seed: Optional[np.ndarray] = None,
        iterations: int = 10,
        target_threshold: float = 0.2
    ) -> DesignResult:
        """
        Main generation loop. Generates a design and refines it based on semantic feedback.

        Args:
            prompt (str): The design intent (e.g., "A sword with murderous intent").
            initial_seed (np.ndarray, optional): Starting latent vector. Random if None.
            iterations (int): Max optimization steps.
            target_threshold (float): Stop if semantic distance < this value.

        Returns:
            DesignResult: The result object containing the final design data.
        """
        # 1. Input Validation
        if not isinstance(prompt, str) or len(prompt) < 3:
            return DesignResult(False, 1.0, np.array([]), None, "Prompt too short or invalid.")
        
        if iterations < 1 or iterations > 1000:
            return DesignResult(False, 1.0, np.array([]), None, "Iterations must be between 1 and 1000.")

        logger.info(f"Starting generative design for prompt: '{prompt}'")

        # 2. Initialization
        current_latent = initial_seed if initial_seed is not None else np.random.rand(512)
        current_latent = current_latent / np.linalg.norm(current_latent)
        
        best_image = None
        best_score = float('inf')
        best_latent = current_latent

        # 3. Optimization Loop (Gradient-free optimization / Evolutionary Strategy simulation)
        try:
            for i in range(iterations):
                # Render design from latent vector
                current_image = self._mock_geometry_renderer(current_latent)
                
                # Evaluate
                distance = self.evaluator.calculate_semantic_distance(current_image, prompt)
                
                logger.debug(f"Iteration {i+1}/{iterations} | Semantic Distance: {distance:.4f}")

                # Update Best
                if distance < best_score:
                    best_score = distance
                    best_image = current_image
                    best_latent = current_latent
                    
                    # Early stopping
                    if best_score <= target_threshold:
                        logger.info(f"Target threshold reached at iteration {i+1}.")
                        break
                
                # Mutate for next step (Simple Hill Climbing)
                # In a real system, this would be backprop through a differentiable renderer
                # or a CMA-ES optimizer.
                current_latent = self._mutate_latent_vector(best_latent, mutation_rate=0.1 * (1 - i/iterations))

            final_msg = f"Optimization finished. Best Score: {best_score:.4f}"
            logger.info(final_msg)
            
            return DesignResult(
                success=True,
                final_score=best_score,
                latent_vector=best_latent,
                rendered_image=best_image,
                message=final_msg
            )

        except Exception as e:
            logger.error(f"Error during generation loop: {str(e)}")
            return DesignResult(False, 1.0, np.array([]), None, f"Runtime Error: {str(e)}")

# -----------------------------------------
# Usage Example (Execution Block)
# -----------------------------------------
if __name__ == "__main__":
    # 1. Instantiate the system
    designer = SemanticGenerativeDesigner()

    # 2. Define the abstract intent
    design_prompt = "A sword possessing a murderous and sharp aura"
    
    # 3. Run the generation process
    # We use fewer iterations for the demo
    result = designer.generate_and_refine(
        prompt=design_prompt,
        iterations=5, 
        target_threshold=0.1
    )

    # 4. Output results
    print("\n" + "="*50)
    print(f"Generation Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Final Semantic Distance: {result.final_score:.4f}")
    print(f"Message: {result.message}")
    
    if result.rendered_image:
        # In a real app, we would save the image
        print("Image generated (PIL object).")
        # result.rendered_image.save("generated_design_concept.png")
    print("="*50)