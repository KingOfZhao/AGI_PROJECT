"""
Module: semantic_bubble_graph_generator.py

Description:
    Core module for the 'Semantic Bubble Graph Generator'.
    Utilizes a Variational Autoencoder (VAE) to map architectural logic (adjacency matrices)
    into a Latent Space, serving as a 'Digital Site'.
    
    Designers can manipulate vectors in this Latent Space (metaphorically 'moving walls'),
    while the system ensures real-time compliance with topological constraints and
    generates valid 3D functional bubble diagrams.

    This achieves a bidirectional mapping between abstract logic and concrete geometry.

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from pydantic import BaseModel, Field, validator, ValidationError
from scipy.spatial import Delaunay
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class ArchitecturalConstraint(BaseModel):
    """Defines the constraints for the architectural design."""
    min_area: float = Field(10.0, ge=1.0, description="Minimum functional area in square meters")
    max_area: float = Field(1000.0, description="Maximum functional area in square meters")
    adjacency_matrix: List[List[int]] = Field(..., description="Binary matrix defining connectivity")
    zones: List[str] = Field(..., description="List of zone names corresponding to matrix indices")

    @validator('adjacency_matrix')
    def check_square_matrix(cls, v):
        n_rows = len(v)
        for row in v:
            if len(row) != n_rows:
                raise ValueError("Adjacency matrix must be square")
        return v

    @validator('zones')
    def check_zone_length(cls, v, values):
        if 'adjacency_matrix' in values and len(v) != len(values['adjacency_matrix']):
            raise ValueError("Number of zones must match adjacency matrix dimensions")
        return v


class GeometricNode(BaseModel):
    """Represents a 3D bubble in the diagram."""
    id: str
    center: Tuple[float, float, float]
    radius: float
    zone_type: str


# --- Core Classes ---

class LatentSpaceVAE:
    """
    A simplified VAE interface simulation.
    In a real AGI scenario, this would load a trained PyTorch/TensorFlow model.
    Here, it uses mathematical transformations to simulate the Latent Space behavior.
    """
    def __init__(self, latent_dim: int = 16):
        self.latent_dim = latent_dim
        logger.info(f"Initializing Latent Space Interface with dimension {latent_dim}")

    def encode(self, adjacency_matrix: np.ndarray) -> np.ndarray:
        """
        Encodes topological logic into a latent vector.
        Simulates the compression of structural information.
        """
        logger.debug("Encoding adjacency matrix to latent vector...")
        # Simplified simulation: Eigenvalue projection + noise (reparameterization trick)
        matrix = np.array(adjacency_matrix, dtype=float)
        eigenvalues = np.linalg.eigvalsh(matrix)
        # Pad or truncate to match latent_dim
        if len(eigenvalues) < self.latent_dim:
            padding = np.zeros(self.latent_dim - len(eigenvalues))
            eigenvalues = np.concatenate([eigenvalues, padding])
        return eigenvalues[:self.latent_dim] + np.random.normal(0, 0.1, self.latent_dim)

    def decode(self, latent_vector: np.ndarray, constraints: ArchitecturalConstraint) -> List[GeometricNode]:
        """
        Decodes a latent vector into 3D geometric nodes (Bubbles).
        Simulates the generator part of the VAE.
        """
        logger.debug("Decoding latent vector to 3D geometry...")
        num_zones = len(constraints.zones)
        
        # Deterministic pseudo-random generation based on latent vector seed
        # This simulates the "Generation" process
        np.random.seed(int(abs(np.sum(latent_vector) * 1000)))
        
        nodes = []
        # Generate rough positions based on spectral layout simulation
        # (In reality, this would be a complex neural network output)
        base_positions = np.random.rand(num_zones, 3) * 10.0
        
        # Simple force simulation to respect adjacency constraints roughly
        # (The AI would implicitly learn this)
        for i in range(50): # Iteration for "relaxation"
            for r in range(num_zones):
                for c in range(num_zones):
                    if constraints.adjacency_matrix[r][c] == 1:
                        # Pull connected nodes closer
                        direction = base_positions[c] - base_positions[r]
                        base_positions[r] += direction * 0.05
        
        for i in range(num_zones):
            radius = np.random.uniform(constraints.min_area**0.5, constraints.max_area**0.5) / 2.0
            node = GeometricNode(
                id=f"zone_{i}",
                center=tuple(np.round(base_positions[i], 2)),
                radius=round(radius, 2),
                zone_type=constraints.zones[i]
            )
            nodes.append(node)
            
        return nodes


class SemanticBubbleGenerator:
    """
    Main Controller Class.
    Manages the interaction between the designer's logic and the AI's Latent Space.
    """

    def __init__(self, constraints: ArchitecturalConstraint):
        self.constraints = constraints
        self.vae = LatentSpaceVAE(latent_dim=32)
        self.current_latent_vector: Optional[np.ndarray] = None
        self.current_graph: Optional[List[GeometricNode]] = None
        logger.info("Semantic Bubble Generator initialized.")

    def initialize_from_logic(self) -> bool:
        """
        Core Function 1: Initialize the design space based on adjacency logic.
        Transforms the input adjacency matrix into the initial 3D diagram.
        """
        try:
            logger.info("Initializing design from adjacency logic...")
            matrix = np.array(self.constraints.adjacency_matrix)
            self.current_latent_vector = self.vae.encode(matrix)
            self.current_graph = self.vae.decode(self.current_latent_vector, self.constraints)
            logger.info(f"Generated {len(self.current_graph)} initial bubbles.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize from logic: {str(e)}")
            return False

    def manipulate_latent_vector(self, vector_shift: np.ndarray) -> bool:
        """
        Core Function 2: Apply a shift to the latent vector.
        This represents the designer 'moving walls' in the abstract space.
        The system regenerates the geometry while trying to maintain topology.
        """
        if self.current_latent_vector is None:
            logger.warning("Cannot manipulate: Latent space not initialized.")
            return False

        if vector_shift.shape != self.current_latent_vector.shape:
            logger.error(f"Shape mismatch: Shift {vector_shift.shape} vs Latent {self.current_latent_vector.shape}")
            raise ValueError("Latent vector shift must match dimensions.")

        try:
            logger.info("Applying latent space manipulation...")
            # Update vector
            self.current_latent_vector += vector_shift
            
            # Regenerate geometry
            self.current_graph = self.vae.decode(self.current_latent_vector, self.constraints)
            
            # Validate topology
            if not self._check_topological_integrity():
                logger.warning("Topological integrity compromised. Reverting shift.")
                # Basic rollback logic
                self.current_latent_vector -= vector_shift
                self.current_graph = self.vae.decode(self.current_latent_vector, self.constraints)
                return False
                
            return True
        except Exception as e:
            logger.critical(f"Error during manipulation: {e}")
            return False

    def _check_topological_integrity(self) -> bool:
        """
        Helper Function: Checks if the generated 3D geometry still respects the
        original adjacency requirements (within a tolerance).
        """
        if self.current_graph is None:
            return False

        # Calculate distances between nodes
        positions = np.array([n.center for n in self.current_graph])
        radii = np.array([n.radius for n in self.current_graph])
        
        # Simple check: Connected zones should overlap or be close
        adj_matrix = np.array(self.constraints.adjacency_matrix)
        
        for i in range(len(self.current_graph)):
            for j in range(i + 1, len(self.current_graph)):
                dist = np.linalg.norm(positions[i] - positions[j])
                touch_dist = radii[i] + radii[j]
                
                should_connect = adj_matrix[i][j] == 1
                
                # Heuristic: If connected in matrix, they must be within 1.5x sum of radii
                if should_connect:
                    if dist > touch_dist * 1.5:
                        return False
                        
        return True

    def export_graph_data(self) -> Dict[str, Any]:
        """Exports the current state for rendering."""
        if not self.current_graph:
            return {}
        
        return {
            "nodes": [node.dict() for node in self.current_graph],
            "latent_vector": self.current_latent_vector.tolist() if self.current_latent_vector is not None else []
        }


# --- Usage Example ---

def run_demo():
    """
    Demonstrates the workflow of the Semantic Bubble Graph Generator.
    """
    print("--- Starting Semantic Bubble Graph Demo ---")
    
    # 1. Define Input Logic
    # Zones: Living Room, Kitchen, Bedroom, Bathroom
    input_data = {
        "zones": ["Living", "Kitchen", "Bedroom", "Bathroom"],
        "adjacency_matrix": [
            [0, 1, 1, 0],  # Living connects to Kitchen, Bedroom
            [1, 0, 0, 1],  # Kitchen connects to Living, Bathroom
            [1, 0, 0, 1],  # Bedroom connects to Living, Bathroom
            [0, 1, 1, 0]   # Bathroom connects to Kitchen, Bedroom
        ],
        "min_area": 20.0,
        "max_area": 50.0
    }

    try:
        # 2. Validate and Initialize
        constraints = ArchitecturalConstraint(**input_data)
        generator = SemanticBubbleGenerator(constraints)
        
        # 3. Generate Initial Design
        success = generator.initialize_from_logic()
        if success:
            print("Initial Design Generated:")
            data = generator.export_graph_data()
            for node in data['nodes']:
                print(f"  - {node['zone_type']}: Pos {node['center']}, R {node['radius']}")
            
            # 4. Simulate "Moving a Wall" (Latent Space Shift)
            # We shift the vector slightly to see how the geometry morphs
            print("\nApplying Latent Shift (Morphing Design)...")
            shift_vector = np.random.normal(0, 0.5, 32) # Random walk in latent space
            generator.manipulate_latent_vector(shift_vector)
            
            print("Updated Design:")
            data = generator.export_graph_data()
            for node in data['nodes']:
                print(f"  - {node['zone_type']}: Pos {node['center']}, R {node['radius']}")
                
        else:
            print("Failed to generate design.")

    except ValidationError as e:
        print(f"Input Validation Error: {e}")
    except Exception as e:
        print(f"System Error: {e}")

if __name__ == "__main__":
    run_demo()