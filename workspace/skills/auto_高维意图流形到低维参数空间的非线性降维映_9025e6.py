"""
Module: auto_高维意图流形到低维参数空间的非线性降维映_9025e6
Description: 高维意图流形到低维参数空间的非线性降维映射
Author: AGI System Core
Version: 1.0.0
"""

import logging
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Tuple, Dict, Optional, Any, List
from dataclasses import dataclass
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ManifoldConfig:
    """Configuration for the Intent Manifold Mapper."""
    input_dim: int = 768  # Typical BERT embedding size
    latent_dim: int = 64  # Control parameter vector size
    hidden_dims: List[int] = None  # Encoder/Decoder hidden layers
    beta: float = 0.1  # KL divergence weight (for VAE)
    learning_rate: float = 1e-4
    batch_size: int = 32
    
    def __post_init__(self):
        if self.hidden_dims is None:
            self.hidden_dims = [512, 256, 128]
        
        # Boundary checks
        if self.input_dim <= 0 or self.latent_dim <= 0:
            raise ValueError("Dimensions must be positive integers")
        if not all(d > 0 for d in self.hidden_dims):
            raise ValueError("Hidden dimensions must be positive")
        if self.beta < 0:
            raise ValueError("Beta must be non-negative")


class Encoder(nn.Module):
    """Encodes high-dimensional intent vectors into latent space."""
    
    def __init__(self, config: ManifoldConfig):
        super(Encoder, self).__init__()
        self.config = config
        
        layers = []
        prev_dim = config.input_dim
        
        for hidden_dim in config.hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.1)
            ])
            prev_dim = hidden_dim
        
        self.encoder = nn.Sequential(*layers)
        
        # VAE parameters
        self.fc_mu = nn.Linear(prev_dim, config.latent_dim)
        self.fc_var = nn.Linear(prev_dim, config.latent_dim)
        
        logger.info(f"Encoder initialized: {config.input_dim} -> {config.latent_dim}")
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass through encoder.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
            
        Returns:
            Tuple of (mu, log_var) representing latent distribution
        """
        h = self.encoder(x)
        mu = self.fc_mu(h)
        log_var = self.fc_var(h)
        return mu, log_var


class Decoder(nn.Module):
    """Decodes latent vectors back to high-dimensional space for reconstruction."""
    
    def __init__(self, config: ManifoldConfig):
        super(Decoder, self).__init__()
        self.config = config
        
        layers = []
        prev_dim = config.latent_dim
        
        # Reverse hidden dimensions for decoder
        for hidden_dim in reversed(config.hidden_dims):
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.1)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, config.input_dim))
        self.decoder = nn.Sequential(*layers)
        
        logger.info(f"Decoder initialized: {config.latent_dim} -> {config.input_dim}")
    
    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Forward pass through decoder.
        
        Args:
            z: Latent tensor of shape (batch_size, latent_dim)
            
        Returns:
            Reconstructed tensor of shape (batch_size, input_dim)
        """
        return self.decoder(z)


class IntentManifoldMapper(nn.Module):
    """VAE-based mapper for intent manifold to parameter space.
    
    This network learns to compress high-dimensional, fuzzy natural language
    intent embeddings into low-dimensional, discrete control parameters while
    preserving semantic information.
    
    Example:
        >>> config = ManifoldConfig(input_dim=768, latent_dim=32)
        >>> mapper = IntentManifoldMapper(config)
        >>> intent_vec = torch.randn(1, 768)  # Simulated BERT embedding
        >>> params, recon_loss, kl_loss = mapper.encode_decode(intent_vec)
        >>> print(f"Control params shape: {params.shape}")
    """
    
    def __init__(self, config: ManifoldConfig):
        super(IntentManifoldMapper, self).__init__()
        self.config = config
        self.encoder = Encoder(config)
        self.decoder = Decoder(config)
        self.optimizer = optim.Adam(self.parameters(), lr=config.learning_rate)
        
        # Loss tracking
        self.recon_loss_fn = nn.MSELoss(reduction='sum')
        
        logger.info("IntentManifoldMapper initialized successfully")
    
    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick for VAE.
        
        Args:
            mu: Mean of latent distribution
            log_var: Log variance of latent distribution
            
        Returns:
            Sampled latent vector
        """
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def encode_decode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full encode-decode pass with loss computation.
        
        Args:
            x: Input intent tensor (batch_size, input_dim)
            
        Returns:
            Tuple of (latent_params, recon_loss, kl_loss)
        """
        # Validate input
        if x.dim() != 2 or x.size(1) != self.config.input_dim:
            raise ValueError(f"Expected input shape (batch, {self.config.input_dim}), got {x.shape}")
        
        # Encode
        mu, log_var = self.encoder(x)
        
        # Sample latent
        z = self.reparameterize(mu, log_var)
        
        # Decode
        x_recon = self.decoder(z)
        
        # Compute losses
        recon_loss = self.recon_loss_fn(x_recon, x)
        kl_loss = -0.5 * torch.sum(1 + log_var - mu.pow(2) - log_var.exp())
        
        return z, recon_loss, kl_loss
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass returning all outputs.
        
        Args:
            x: Input intent tensor
            
        Returns:
            Dictionary containing latent, reconstruction, and losses
        """
        z, recon_loss, kl_loss = self.encode_decode(x)
        
        return {
            'latent': z,
            'reconstruction': self.decoder(z),
            'recon_loss': recon_loss,
            'kl_loss': kl_loss,
            'total_loss': recon_loss + self.config.beta * kl_loss
        }
    
    def train_step(self, x: torch.Tensor) -> float:
        """Single training step.
        
        Args:
            x: Input batch
            
        Returns:
            Total loss value
        """
        self.optimizer.zero_grad()
        outputs = self.forward(x)
        loss = outputs['total_loss']
        loss.backward()
        self.optimizer.step()
        return loss.item()
    
    def map_intent_to_params(self, intent_vector: np.ndarray) -> np.ndarray:
        """Map high-dimensional intent to control parameters.
        
        Args:
            intent_vector: Numpy array of shape (input_dim,)
            
        Returns:
            Control parameter vector of shape (latent_dim,)
        """
        # Validate input
        if intent_vector.shape != (self.config.input_dim,):
            raise ValueError(f"Expected shape ({self.config.input_dim},), got {intent_vector.shape}")
        
        # Check for NaN/Inf
        if not np.all(np.isfinite(intent_vector)):
            raise ValueError("Intent vector contains NaN or Inf values")
        
        self.eval()
        with torch.no_grad():
            x = torch.FloatTensor(intent_vector).unsqueeze(0)
            mu, _ = self.encoder(x)
            params = mu.squeeze(0).numpy()
        
        logger.debug(f"Mapped intent to params: shape={params.shape}")
        return params
    
    def reconstruct_params_to_intent(self, params: np.ndarray) -> np.ndarray:
        """Reconstruct intent from control parameters (for verification).
        
        Args:
            params: Control parameters of shape (latent_dim,)
            
        Returns:
            Reconstructed intent vector of shape (input_dim,)
        """
        # Validate input
        if params.shape != (self.config.latent_dim,):
            raise ValueError(f"Expected shape ({self.config.latent_dim},), got {params.shape}")
        
        self.eval()
        with torch.no_grad():
            z = torch.FloatTensor(params).unsqueeze(0)
            recon = self.decoder(z).squeeze(0).numpy()
        
        return recon


def validate_intent_embedding(embedding: np.ndarray, expected_dim: int = 768) -> bool:
    """Validate intent embedding vector.
    
    Args:
        embedding: Numpy array to validate
        expected_dim: Expected dimensionality
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(embedding, np.ndarray):
        logger.error("Input must be numpy array")
        return False
    
    if embedding.shape != (expected_dim,):
        logger.error(f"Shape mismatch: expected ({expected_dim},), got {embedding.shape}")
        return False
    
    if not np.all(np.isfinite(embedding)):
        logger.error("Embedding contains NaN or Inf values")
        return False
    
    # Check for reasonable value range
    if np.abs(embedding).max() > 100:
        logger.warning("Embedding values seem unusually large")
    
    return True


def compute_semantic_preservation_score(
    original: np.ndarray, 
    reconstruction: np.ndarray
) -> float:
    """Compute semantic preservation score between original and reconstructed vectors.
    
    Uses cosine similarity to measure semantic alignment.
    
    Args:
        original: Original intent vector
        reconstruction: Reconstructed intent vector
        
    Returns:
        Cosine similarity score in range [-1, 1]
    """
    if original.shape != reconstruction.shape:
        raise ValueError("Vectors must have same shape")
    
    dot_product = np.dot(original, reconstruction)
    norm_product = np.linalg.norm(original) * np.linalg.norm(reconstruction)
    
    if norm_product == 0:
        return 0.0
    
    return dot_product / norm_product


# Usage Example
if __name__ == "__main__":
    # Initialize configuration
    config = ManifoldConfig(
        input_dim=768,
        latent_dim=32,
        hidden_dims=[512, 256, 128],
        beta=0.05
    )
    
    # Create mapper
    mapper = IntentManifoldMapper(config)
    
    # Simulate intent embeddings (e.g., from BERT)
    batch_size = 16
    intent_batch = torch.randn(batch_size, 768)
    
    # Training step example
    loss = mapper.train_step(intent_batch)
    print(f"Training loss: {loss:.4f}")
    
    # Map single intent to control parameters
    single_intent = np.random.randn(768)
    if validate_intent_embedding(single_intent):
        control_params = mapper.map_intent_to_params(single_intent)
        print(f"Control parameters shape: {control_params.shape}")
        
        # Reconstruct and verify
        reconstructed = mapper.reconstruct_params_to_intent(control_params)
        score = compute_semantic_preservation_score(single_intent, reconstructed)
        print(f"Semantic preservation score: {score:.4f}")