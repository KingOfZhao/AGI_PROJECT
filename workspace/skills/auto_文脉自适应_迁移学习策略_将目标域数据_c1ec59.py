"""
AGI Skill: Context-Adaptive Transfer Learning Strategy (auto_文脉自适应_迁移学习策略)

This module implements a sophisticated transfer learning approach that treats target domain data
as 'terrain' and pre-trained models as 'universal building blocks'. Unlike traditional fine-tuning,
this strategy performs 'terrain survey' (data distribution analysis) to identify 'geological faults'
(data sparse regions), then generates specific 'foundations' (Adapter modules) to ensure the model
'grows' along the data's context rather than being forcefully implanted.

Core Components:
- TerrainSurveyor: Analyzes target domain data distribution and identifies sparse regions
- FoundationArchitect: Generates and optimizes adapter modules for the pre-trained model
- ContextAdaptiveLearner: Main orchestrator that manages the adaptive learning process

Input Format:
- Pre-trained model (torch.nn.Module)
- Target domain dataset (torch.utils.data.Dataset or numpy arrays)
- Configuration dictionary with adaptation parameters

Output Format:
- Adapted model with context-specific adapters
- Training metrics and adaptation report
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Tuple, Optional, Union, List, Any
from dataclasses import dataclass
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import GridSearchCV
from scipy.stats import entropy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AdaptationConfig:
    """Configuration for context-adaptive transfer learning"""
    adapter_dim: int = 64  # Dimension of adapter bottleneck
    survey_bins: int = 50  # Number of bins for density estimation
    fault_threshold: float = 0.1  # Threshold for identifying sparse regions
    adaptation_lr: float = 1e-4  # Learning rate for adapter training
    max_epochs: int = 20  # Maximum training epochs
    early_stop_patience: int = 3  # Early stopping patience
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'


class TerrainSurveyor:
    """
    Analyzes target domain data distribution to identify 'geological faults'
    (sparse regions that require special handling during adaptation).
    """
    
    def __init__(self, config: AdaptationConfig):
        """Initialize with adaptation configuration."""
        self.config = config
        self.density_estimator = None
        self.fault_regions = []
        logger.info("TerrainSurveyor initialized with config: %s", config)
    
    def survey_terrain(self, data: Union[np.ndarray, torch.Tensor]) -> Dict[str, Any]:
        """
        Perform terrain survey on target domain data.
        
        Args:
            data: Input data array of shape (n_samples, n_features)
            
        Returns:
            Dictionary containing terrain analysis results including:
            - 'density': Estimated density for each data point
            - 'faults': List of identified sparse regions
            - 'stats': Basic statistics of the terrain
            
        Raises:
            ValueError: If input data is empty or has invalid shape
        """
        if isinstance(data, torch.Tensor):
            data = data.cpu().numpy()
            
        if data.size == 0:
            raise ValueError("Input data cannot be empty")
            
        if len(data.shape) != 2:
            raise ValueError(f"Expected 2D array, got shape {data.shape}")
            
        logger.info("Starting terrain survey on data with shape %s", data.shape)
        
        # Data validation
        if np.any(np.isnan(data)):
            raise ValueError("Input data contains NaN values")
            
        # Basic terrain statistics
        stats = {
            'n_samples': data.shape[0],
            'n_features': data.shape[1],
            'mean': np.mean(data, axis=0),
            'std': np.std(data, axis=0),
            'min': np.min(data, axis=0),
            'max': np.max(data, axis=0)
        }
        
        # Kernel density estimation
        params = {'bandwidth': np.logspace(-1, 1, 20)}
        grid = GridSearchCV(KernelDensity(), params, cv=5)
        grid.fit(data)
        
        self.density_estimator = grid.best_estimator_
        log_density = self.density_estimator.score_samples(data)
        density = np.exp(log_density)
        
        # Identify geological faults (sparse regions)
        density_threshold = np.percentile(density, self.config.fault_threshold * 100)
        fault_mask = density < density_threshold
        fault_points = data[fault_mask]
        
        self.fault_regions = self._cluster_fault_regions(fault_points)
        
        logger.info("Survey complete. Identified %d fault regions", len(self.fault_regions))
        
        return {
            'density': density,
            'faults': self.fault_regions,
            'stats': stats
        }
    
    def _cluster_fault_regions(self, fault_points: np.ndarray) -> List[Dict[str, Any]]:
        """Cluster fault points into distinct regions using simple distance-based clustering."""
        if len(fault_points) == 0:
            return []
            
        regions = []
        visited = np.zeros(len(fault_points), dtype=bool)
        
        for i in range(len(fault_points)):
            if visited[i]:
                continue
                
            # Simple clustering based on distance threshold
            distances = np.linalg.norm(fault_points - fault_points[i], axis=1)
            cluster_mask = distances < np.mean(distances)  # Adaptive threshold
            cluster_points = fault_points[cluster_mask]
            visited[cluster_mask] = True
            
            regions.append({
                'center': np.mean(cluster_points, axis=0),
                'radius': np.max(np.linalg.norm(cluster_points - np.mean(cluster_points, axis=0), axis=1)),
                'density': np.mean(self.density_estimator.score_samples(cluster_points))
            })
            
        return regions


class FoundationArchitect:
    """
    Generates and optimizes adapter modules ('foundations') for the pre-trained model
    based on terrain survey results.
    """
    
    def __init__(self, config: AdaptationConfig):
        """Initialize with adaptation configuration."""
        self.config = config
        logger.info("FoundationArchitect initialized with adapter_dim=%d", config.adapter_dim)
    
    def design_foundation(self, model: nn.Module, survey_results: Dict[str, Any]) -> nn.Module:
        """
        Design adapter modules based on terrain survey results.
        
        Args:
            model: Pre-trained model to adapt
            survey_results: Results from TerrainSurveyor.survey_terrain()
            
        Returns:
            Model with added adapter modules
            
        Raises:
            RuntimeError: If model architecture is incompatible
        """
        if not hasattr(model, 'forward'):
            raise RuntimeError("Model must have a forward method")
            
        logger.info("Designing foundation for model with %d parameters", sum(p.numel() for p in model.parameters()))
        
        # Identify insertion points for adapters
        insertion_points = self._find_adapter_insertion_points(model)
        
        if not insertion_points:
            raise RuntimeError("Could not find suitable insertion points for adapters")
            
        # Create adapter modules for each insertion point
        adapters = nn.ModuleDict()
        
        for name, module in insertion_points:
            # Get module dimensions
            if hasattr(module, 'in_features') and hasattr(module, 'out_features'):
                in_dim = module.in_features
                out_dim = module.out_features
            else:
                logger.warning("Skipping adapter for %s - could not determine dimensions", name)
                continue
                
            # Create adapter with fault-aware initialization
            adapter = self._create_fault_aware_adapter(
                in_dim, 
                out_dim, 
                survey_results['faults']
            )
            
            adapters[name] = adapter
            logger.debug("Created adapter for %s with shape (%d, %d)", name, in_dim, out_dim)
        
        # Wrap the original model with adapters
        adapted_model = self._wrap_model_with_adapters(model, adapters)
        
        logger.info("Foundation design complete with %d adapters", len(adapters))
        return adapted_model
    
    def _find_adapter_insertion_points(self, model: nn.Module) -> List[Tuple[str, nn.Module]]:
        """Find suitable insertion points for adapters in the model."""
        insertion_points = []
        
        for name, module in model.named_modules():
            # Skip container modules and only consider linear layers
            if isinstance(module, nn.Linear) and not any(
                isinstance(child, nn.Linear) for child in module.children()
            ):
                insertion_points.append((name, module))
                
        return insertion_points
    
    def _create_fault_aware_adapter(self, in_dim: int, out_dim: int, fault_regions: List[Dict]) -> nn.Module:
        """Create adapter module with fault-aware initialization."""
        adapter = nn.Sequential(
            nn.Linear(in_dim, self.config.adapter_dim),
            nn.GELU(),
            nn.Linear(self.config.adapter_dim, out_dim)
        )
        
        # Custom initialization based on fault regions
        if fault_regions:
            fault_centers = np.array([r['center'] for r in fault_regions])
            fault_weights = np.array([1.0 / (r['density'] + 1e-6) for r in fault_regions])
            fault_weights = fault_weights / fault_weights.sum()
            
            # Initialize adapter weights to emphasize fault regions
            with torch.no_grad():
                weighted_center = np.average(fault_centers, weights=fault_weights, axis=0)
                if len(weighted_center) == in_dim:
                    adapter[0].weight.data = torch.tensor(
                        np.outer(weighted_center, np.ones(self.config.adapter_dim)),
                        dtype=torch.float32
                    )
        
        return adapter
    
    def _wrap_model_with_adapters(self, model: nn.Module, adapters: nn.ModuleDict) -> nn.Module:
        """Wrap the original model with adapter modules."""
        class AdaptedModel(nn.Module):
            def __init__(self, base_model, adapters):
                super().__init__()
                self.base_model = base_model
                self.adapters = adapters
                
            def forward(self, x):
                # Store intermediate outputs for adapter insertion
                intermediates = {}
                hooks = []
                
                def make_hook(name):
                    def hook(module, input, output):
                        intermediates[name] = output
                    return hook
                
                # Register hooks to capture intermediate outputs
                for name, module in self.base_model.named_modules():
                    if name in self.adapters:
                        hooks.append(module.register_forward_hook(make_hook(name)))
                
                # Forward pass through base model
                output = self.base_model(x)
                
                # Apply adapters to captured outputs
                for name, adapter in self.adapters.items():
                    if name in intermediates:
                        adapted = adapter(intermediates[name])
                        # Add adapted output to final output
                        if isinstance(output, tuple):
                            output = tuple(o + a for o, a in zip(output, adapted))
                        else:
                            output = output + adapted
                
                # Remove hooks
                for hook in hooks:
                    hook.remove()
                    
                return output
                
        return AdaptedModel(model, adapters)


class ContextAdaptiveLearner:
    """
    Main orchestrator for the context-adaptive transfer learning process.
    Coordinates terrain surveying, foundation design, and model adaptation.
    """
    
    def __init__(self, config: Optional[AdaptationConfig] = None):
        """
        Initialize the context-adaptive learner.
        
        Args:
            config: Adaptation configuration. If None, uses default values.
        """
        self.config = config or AdaptationConfig()
        self.surveyor = TerrainSurveyor(self.config)
        self.architect = FoundationArchitect(self.config)
        self.device = torch.device(self.config.device)
        logger.info("ContextAdaptiveLearner initialized on device: %s", self.device)
    
    def adapt(
        self,
        model: nn.Module,
        target_data: Union[np.ndarray, torch.Tensor, torch.utils.data.Dataset],
        val_data: Optional[Union[np.ndarray, torch.Tensor, torch.utils.data.Dataset]] = None
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        Perform context-adaptive transfer learning.
        
        Args:
            model: Pre-trained model to adapt
            target_data: Target domain data for adaptation
            val_data: Optional validation data
            
        Returns:
            Tuple of (adapted_model, adaptation_report)
            
        Raises:
            RuntimeError: If adaptation fails
        """
        logger.info("Starting context-adaptive transfer learning")
        
        try:
            # Step 1: Terrain survey
            if isinstance(target_data, torch.utils.data.Dataset):
                # Convert dataset to array for survey
                data_list = [x for x, _ in target_data]
                survey_data = torch.stack(data_list).numpy()
            else:
                survey_data = target_data
                
            survey_results = self.surveyor.survey_terrain(survey_data)
            
            # Step 2: Foundation design
            adapted_model = self.architect.design_foundation(model, survey_results)
            adapted_model = adapted_model.to(self.device)
            
            # Step 3: Fine-tune adapters
            if val_data is not None:
                adaptation_report = self._fine_tune_adapters(
                    adapted_model, target_data, val_data
                )
            else:
                adaptation_report = {
                    'status': 'adapters_designed',
                    'survey_results': survey_results
                }
            
            logger.info("Context-adaptive transfer learning completed successfully")
            return adapted_model, adaptation_report
            
        except Exception as e:
            logger.error("Adaptation failed: %s", str(e))
            raise RuntimeError(f"Adaptation failed: {str(e)}") from e
    
    def _fine_tune_adapters(
        self,
        model: nn.Module,
        train_data: Union[np.ndarray, torch.Tensor, torch.utils.data.Dataset],
        val_data: Union[np.ndarray, torch.Tensor, torch.utils.data.Dataset]
    ) -> Dict[str, Any]:
        """Fine-tune adapter modules on target data."""
        logger.info("Starting adapter fine-tuning")
        
        # Prepare data loaders
        if isinstance(train_data, torch.utils.data.Dataset):
            train_loader = torch.utils.data.DataLoader(
                train_data, batch_size=32, shuffle=True
            )
        else:
            if isinstance(train_data, np.ndarray):
                train_data = torch.tensor(train_data, dtype=torch.float32)
            train_loader = torch.utils.data.DataLoader(
                torch.utils.data.TensorDataset(train_data),
                batch_size=32, shuffle=True
            )
            
        if isinstance(val_data, torch.utils.data.Dataset):
            val_loader = torch.utils.data.DataLoader(
                val_data, batch_size=32, shuffle=False
            )
        else:
            if isinstance(val_data, np.ndarray):
                val_data = torch.tensor(val_data, dtype=torch.float32)
            val_loader = torch.utils.data.DataLoader(
                torch.utils.data.TensorDataset(val_data),
                batch_size=32, shuffle=False
            )
        
        # Only optimize adapter parameters
        optimizer = torch.optim.Adam(
            [p for n, p in model.named_parameters() if 'adapter' in n],
            lr=self.config.adaptation_lr
        )
        
        criterion = nn.MSELoss()  # Suitable for feature adaptation
        
        best_loss = float('inf')
        patience_counter = 0
        history = {'train_loss': [], 'val_loss': []}
        
        for epoch in range(self.config.max_epochs):
            model.train()
            train_loss = 0.0
            
            for batch in train_loader:
                if isinstance(batch, (list, tuple)):
                    x = batch[0].to(self.device)
                else:
                    x = batch.to(self.device)
                
                optimizer.zero_grad()
                
                try:
                    output = model(x)
                    
                    # Simple reconstruction loss for demonstration
                    if isinstance(output, tuple):
                        loss = sum(criterion(o, x) for o in output)
                    else:
                        loss = criterion(output, x)
                    
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()
                    
                except RuntimeError as e:
                    logger.warning("Batch processing failed: %s", str(e))
                    continue
            
            # Validation
            model.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for batch in val_loader:
                    if isinstance(batch, (list, tuple)):
                        x = batch[0].to(self.device)
                    else:
                        x = batch.to(self.device)
                    
                    output = model(x)
                    
                    if isinstance(output, tuple):
                        loss = sum(criterion(o, x) for o in output)
                    else:
                        loss = criterion(output, x)
                    
                    val_loss += loss.item()
            
            # Record metrics
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            
            logger.info(
                "Epoch %d/%d - Train Loss: %.4f, Val Loss: %.4f",
                epoch + 1, self.config.max_epochs, train_loss, val_loss
            )
            
            # Early stopping
            if val_loss < best_loss:
                best_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stop_patience:
                    logger.info("Early stopping triggered")
                    break
        
        return {
            'status': 'adaptation_complete',
            'history': history,
            'best_val_loss': best_loss,
            'epochs_completed': epoch + 1
        }


# Example usage
if __name__ == "__main__":
    # Create a simple pre-trained model
    class PretrainedModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(10, 20)
            self.fc2 = nn.Linear(20, 10)
            
        def forward(self, x):
            x = torch.relu(self.fc1(x))
            return self.fc2(x)
    
    # Generate some target domain data with sparse regions
    np.random.seed(42)
    target_data = np.random.randn(1000, 10).astype(np.float32)
    # Create sparse regions
    target_data[::10] *= 0.1  # Low density region
    target_data[50:70] *= 5.0  # High density region
    
    # Split into train and validation
    train_data = target_data[:800]
    val_data = target_data[800:]
    
    # Initialize learner with custom config
    config = AdaptationConfig(
        adapter_dim=32,
        survey_bins=30,
        fault_threshold=0.15,
        max_epochs=10
    )
    learner = ContextAdaptiveLearner(config)
    
    # Perform adaptation
    model = PretrainedModel()
    adapted_model, report = learner.adapt(model, train_data, val_data)
    
    print("\nAdaptation Report:")
    print(f"Status: {report['status']}")
    print(f"Best Validation Loss: {report['best_val_loss']:.4f}")
    print(f"Epochs Completed: {report['epochs_completed']}")