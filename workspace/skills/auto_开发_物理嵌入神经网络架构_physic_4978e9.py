"""
Module: auto_开发_物理嵌入神经网络架构_physic_4978e9
Description: Engineering implementation of Physics-informed Neural Architectures (PINN).
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, List, Optional, Dict, Union, Callable
from pydantic import BaseModel, Field, ValidationError, confloat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# Data Models and Validation
# ==========================================

class PhysicsConfig(BaseModel):
    """
    Configuration model for the Physics-Informed Neural Network.
    Validates network architecture and physics hyperparameters.
    """
    input_dim: int = Field(..., gt=0, description="Dimensionality of the input space (e.g., spatial coordinates)")
    output_dim: int = Field(..., gt=0, description="Dimensionality of the output space (e.g., physical fields)")
    hidden_layers: List[int] = Field(default=[64, 64, 64], description="List of neurons per hidden layer")
    learning_rate: confloat(gt=0, le=1) = Field(default=1e-3, description="Optimizer learning rate")
    lambda_pde: float = Field(default=1.0, description="Weight for the PDE residual loss")
    lambda_bc: float = Field(default=1.0, description="Weight for the boundary condition loss")
    activation: str = Field(default="tanh", description="Activation function name")

# ==========================================
# Core Components
# ==========================================

class FCBlock(nn.Module):
    """
    Fully Connected Neural Network Block.
    A flexible feed-forward network architecture.
    """
    def __init__(self, layers: List[int], activation: str = 'tanh'):
        super(FCBlock, self).__init__()
        self.layers = nn.ModuleList()
        self.activation = self._get_activation(activation)
        
        # Construct layers
        for i in range(len(layers) - 1):
            self.layers.append(nn.Linear(layers[i], layers[i+1]))
            # Apply weight initialization
            nn.init.xavier_normal_(self.layers[-1].weight)
            nn.init.zeros_(self.layers[-1].bias)

    def _get_activation(self, name: str) -> nn.Module:
        """Helper to select activation function."""
        activations = {
            'tanh': nn.Tanh(),
            'relu': nn.ReLU(),
            'silu': nn.SiLU(),
            'gelu': nn.GELU()
        }
        if name not in activations:
            logger.warning(f"Activation {name} not found, defaulting to Tanh.")
            return nn.Tanh()
        return activations[name]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for i, layer in enumerate(self.layers[:-1]):
            x = layer(x)
            x = self.activation(x)
        # No activation on the final layer usually for regression
        x = self.layers[-1](x)
        return x

class PhysicsInformedNN:
    """
    High-level API for training and evaluating Physics-Informed Neural Networks.
    
    Attributes:
        config (PhysicsConfig): Validated configuration object.
        model (nn.Module): The PyTorch neural network model.
        optimizer (torch.optim.Optimizer): The optimizer instance.
    """

    def __init__(self, config: Dict):
        """
        Initialize the PINN system.
        
        Args:
            config (Dict): Dictionary containing configuration parameters.
        
        Raises:
            ValidationError: If configuration parameters are invalid.
            ValueError: If tensor dimensions mismatch during setup.
        """
        try:
            self.config = PhysicsConfig(**config)
            logger.info("Configuration validated successfully.")
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise

        # Setup Network Architecture
        layers = [self.config.input_dim] + self.config.hidden_layers + [self.config.output_dim]
        self.model = FCBlock(layers, self.config.activation)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        
        logger.info(f"Model initialized with architecture: {layers}")

    def compute_pde_residual(self, inputs: torch.Tensor, physics_fn: Callable) -> torch.Tensor:
        """
        Computes the Physics Differential Equation residual.
        
        This is the core of PINN: calculating the deviation from the known physical law.
        
        Args:
            inputs (torch.Tensor): Input coordinates requiring gradients.
            physics_fn (Callable): A function defining the PDE (f(u, x, t) = 0).
        
        Returns:
            torch.Tensor: The calculated residual loss.
        """
        if not inputs.requires_grad:
            inputs.requires_grad_(True)
        
        # Forward pass to get predictions
        u_pred = self.model(inputs)
        
        # Calculate physics loss via the provided closure
        # This closure typically uses torch.autograd.grad to compute derivatives
        try:
            residual = physics_fn(inputs, u_pred)
        except Exception as e:
            logger.error(f"Error computing physics residual: {e}")
            raise RuntimeError("Failed to compute PDE residual.") from e
            
        return torch.mean(residual ** 2)

    def train_step(
        self, 
        collocation_points: torch.Tensor,
        boundary_points: torch.Tensor,
        boundary_values: torch.Tensor,
        physics_fn: Callable
    ) -> Tuple[float, float, float]:
        """
        Performs a single training step (forward + backward pass).
        
        Args:
            collocation_points (torch.Tensor): Points inside the domain to enforce PDE.
            boundary_points (torch.Tensor): Points on the boundary.
            boundary_values (torch.Tensor): Ground truth values at boundaries.
            physics_fn (Callable): Function defining the differential equation.
        
        Returns:
            Tuple[float, float, float]: Total loss, PDE loss, Boundary loss.
        """
        self.model.train()
        self.optimizer.zero_grad()

        # 1. Compute Boundary Condition Loss (Data Loss)
        pred_boundary = self.model(boundary_points)
        loss_bc = torch.mean((pred_boundary - boundary_values) ** 2)

        # 2. Compute PDE Loss (Physics Loss)
        loss_pde = self.compute_pde_residual(collocation_points, physics_fn)

        # 3. Aggregate Loss
        total_loss = (self.config.lambda_bc * loss_bc) + (self.config.lambda_pde * loss_pde)

        # Backpropagation
        total_loss.backward()
        self.optimizer.step()

        return total_loss.item(), loss_pde.item(), loss_bc.item()

    def predict(self, inputs: torch.Tensor) -> np.ndarray:
        """
        Generates predictions for the given inputs.
        
        Args:
            inputs (torch.Tensor): Input coordinates.
            
        Returns:
            np.ndarray: Predicted physical field values.
        """
        self.model.eval()
        with torch.no_grad():
            # Ensure input is tensor
            if isinstance(inputs, np.ndarray):
                inputs = torch.from_numpy(inputs).float()
            
            # Basic boundary check
            if inputs.dim() != 2 or inputs.shape[1] != self.config.input_dim:
                raise ValueError(f"Input dimension mismatch. Expected (N, {self.config.input_dim}), got {inputs.shape}")

            predictions = self.model(inputs)
        return predictions.numpy()

# ==========================================
# Helper Functions
# ==========================================

def generate_training_data_1d(n_points: int = 1000, domain: Tuple[float, float] = (0, 1)) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Helper function to generate synthetic data for a simple 1D problem (e.g., diffusion).
    
    Args:
        n_points (int): Number of internal collocation points.
        domain (Tuple[float, float]): Spatial domain boundaries.
    
    Returns:
        Tuple containing collocation points, boundary points, and boundary values.
    """
    # Internal points (Collocation)
    x_internal = np.random.uniform(domain[0], domain[1], (n_points, 1))
    
    # Boundary points (0.0 and 1.0)
    x_boundary = np.array([[domain[0]], [domain[1]]])
    
    # Example Boundary Condition: u(0)=0, u(1)=0
    u_boundary = np.zeros_like(x_boundary)
    
    # Convert to tensors
    x_internal_t = torch.from_numpy(x_internal).float()
    x_boundary_t = torch.from_numpy(x_boundary).float()
    u_boundary_t = torch.from_numpy(u_boundary).float()
    
    return x_internal_t, x_boundary_t, u_boundary_t

def visualize_results(model: PhysicsInformedNN, domain: Tuple[float, float] = (0, 1)):
    """
    Helper to visualize 1D results using matplotlib (if available).
    Included for completeness of the engineering specification.
    """
    try:
        import matplotlib.pyplot as plt
        
        x_test = np.linspace(domain[0], domain[1], 100).reshape(-1, 1)
        x_test_t = torch.from_numpy(x_test).float()
        
        u_pred = model.predict(x_test_t)
        
        plt.figure(figsize=(8, 5))
        plt.plot(x_test, u_pred, label='PINN Prediction', color='blue')
        plt.scatter([domain[0], domain[1]], [0, 0], color='red', label='Boundary Conditions', zorder=5)
        plt.title('Physics-Informed Neural Network Result')
        plt.xlabel('Spatial Coordinate x')
        plt.ylabel('Physical Quantity u')
        plt.legend()
        plt.grid(True)
        plt.show()
        logger.info("Visualization rendered successfully.")
    except ImportError:
        logger.warning("Matplotlib not found. Skipping visualization.")

# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # 1. Define Configuration
    config = {
        "input_dim": 1, 
        "output_dim": 1, 
        "hidden_layers": [20, 20, 20],
        "learning_rate": 0.001,
        "lambda_pde": 1.0,
        "lambda_bc": 100.0, # Higher weight for BC usually helps convergence
        "activation": "tanh"
    }

    # 2. Initialize PINN
    pinn = PhysicsInformedNN(config)

    # 3. Generate Data
    x_colloc, x_bc, u_bc = generate_training_data_1d(n_points=500)

    # 4. Define a Physics Function (Example: Simple Laplacian u_xx = 0)
    # For a source term solution like u = x^2, PDE is u_xx - 2 = 0
    def simple_pde(x, u):
        # compute u_x
        u_x = torch.autograd.grad(u, x, torch.ones_like(u), create_graph=True)[0]
        # compute u_xx
        u_xx = torch.autograd.grad(u_x, x, torch.ones_like(u_x), create_graph=True)[0]
        
        # For simple harmonic (u_xx = 0) or decay
        # Here we solve u_xx = 0 (Linear solution)
        return u_xx 

    # 5. Training Loop
    logger.info("Starting training...")
    epochs = 1000
    for epoch in range(epochs):
        loss, l_pde, l_bc = pinn.train_step(x_colloc, x_bc, u_bc, simple_pde)
        if epoch % 100 == 0:
            logger.info(f"Epoch {epoch}: Total Loss={loss:.4e}, PDE={l_pde:.4e}, BC={l_bc:.4e}")

    # 6. Prediction and Validation
    test_x = torch.tensor([[0.5]]) # Midpoint
    prediction = pinn.predict(test_x)
    logger.info(f"Prediction at x=0.5: {prediction[0,0]:.4f} (Expected approx 0 for linear BCs)")