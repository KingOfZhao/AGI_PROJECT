"""
Module: auto_如何实现基于反事实推理的因果图谱构建_从_c3b576
Description: Implementation of Counterfactual Reasoning-based Causal Graph Construction
Author: AGI System
Version: 1.0.0
"""

import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
import pandas as pd
from collections import defaultdict
from itertools import combinations
from scipy.stats import pearsonr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CausalEdge:
    """Data class representing a causal edge in the graph."""
    source: str
    target: str
    correlation: float
    causal_effect: float
    counterfactual_score: float
    confidence: float


class CounterfactualCausalGraphBuilder:
    """
    A class to construct causal graphs based on counterfactual reasoning.
    
    This class implements algorithms to distinguish between correlational and 
    causal operations from industrial historical data, eliminating invalid 
    'empirical' interference through counterfactual analysis.
    
    Attributes:
        data (pd.DataFrame): Input industrial historical data
        variables (List[str]): List of variable names
        causal_graph (Dict[str, List[CausalEdge]]): Constructed causal graph
        alpha (float): Significance level for statistical tests
        min_samples (int): Minimum samples required for analysis
        
    Example:
        >>> data = pd.DataFrame({
        ...     'temperature': np.random.normal(25, 5, 1000),
        ...     'pressure': np.random.normal(1.2, 0.3, 1000),
        ...     'yield': np.random.normal(85, 10, 1000)
        ... })
        >>> builder = CounterfactualCausalGraphBuilder(data, alpha=0.05)
        >>> causal_graph = builder.build_causal_graph()
    """
    
    def __init__(
        self, 
        data: pd.DataFrame, 
        alpha: float = 0.05,
        min_samples: int = 100
    ) -> None:
        """
        Initialize the causal graph builder.
        
        Args:
            data: Input DataFrame containing industrial process variables
            alpha: Significance level for statistical tests (default: 0.05)
            min_samples: Minimum samples required for reliable analysis
            
        Raises:
            ValueError: If data is empty or contains insufficient samples
            TypeError: If input is not a pandas DataFrame
        """
        self._validate_input_data(data, min_samples)
        
        self.data = data.copy()
        self.variables = list(data.columns)
        self.causal_graph: Dict[str, List[CausalEdge]] = defaultdict(list)
        self.alpha = alpha
        self.min_samples = min_samples
        
        logger.info(f"Initialized causal graph builder with {len(self.variables)} variables")
    
    def _validate_input_data(
        self, 
        data: pd.DataFrame, 
        min_samples: int
    ) -> None:
        """
        Validate input data format and quality.
        
        Args:
            data: Input DataFrame to validate
            min_samples: Minimum required samples
            
        Raises:
            TypeError: If input is not a DataFrame
            ValueError: If data is empty or has insufficient samples
        """
        if not isinstance(data, pd.DataFrame):
            error_msg = "Input data must be a pandas DataFrame"
            logger.error(error_msg)
            raise TypeError(error_msg)
            
        if data.empty:
            error_msg = "Input DataFrame cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if len(data) < min_samples:
            error_msg = f"Insufficient samples: {len(data)} < {min_samples}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if data.isnull().any().any():
            logger.warning("Input data contains missing values, will be handled during processing")
    
    def _calculate_correlation(
        self, 
        x: pd.Series, 
        y: pd.Series
    ) -> Tuple[float, float]:
        """
        Calculate Pearson correlation coefficient and p-value between two series.
        
        Args:
            x: First data series
            y: Second data series
            
        Returns:
            Tuple of (correlation coefficient, p-value)
            
        Raises:
            ValueError: If series have different lengths or insufficient data
        """
        if len(x) != len(y):
            error_msg = "Series must have equal length"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Handle missing values by pairwise deletion
        valid_mask = x.notna() & y.notna()
        x_clean = x[valid_mask]
        y_clean = y[valid_mask]
        
        if len(x_clean) < 5:  # Minimum samples for correlation
            logger.warning("Insufficient valid samples for correlation")
            return 0.0, 1.0
            
        corr, p_value = pearsonr(x_clean, y_clean)
        return corr, p_value
    
    def _identify_potential_causes(
        self, 
        target: str, 
        threshold: float = 0.1
    ) -> List[str]:
        """
        Identify potential causal variables for a target variable.
        
        Args:
            target: Target variable name
            threshold: Minimum absolute correlation threshold
            
        Returns:
            List of potential causal variable names
        """
        potential_causes = []
        target_series = self.data[target]
        
        for var in self.variables:
            if var == target:
                continue
                
            corr, p_value = self._calculate_correlation(
                self.data[var], 
                target_series
            )
            
            if abs(corr) > threshold and p_value < self.alpha:
                potential_causes.append(var)
                
        logger.debug(f"Found {len(potential_causes)} potential causes for {target}")
        return potential_causes
    
    def _calculate_counterfactual_score(
        self, 
        cause: str, 
        effect: str, 
        confounders: List[str]
    ) -> float:
        """
        Calculate counterfactual score to distinguish correlation from causation.
        
        This method implements a simplified version of counterfactual reasoning:
        - Compare actual effect with counterfactual scenario
        - Adjust for confounding variables
        
        Args:
            cause: Potential causal variable
            effect: Effect variable
            confounders: List of potential confounding variables
            
        Returns:
            Counterfactual score (higher indicates stronger causal relationship)
        """
        if not confounders:
            # Simple case: no confounders
            corr, _ = self._calculate_correlation(
                self.data[cause], 
                self.data[effect]
            )
            return abs(corr)
        
        # Adjust for confounders using partial correlation
        # This is a simplified approach; more sophisticated methods exist
        residuals_cause = self._get_residuals(cause, confounders)
        residuals_effect = self._get_residuals(effect, confounders)
        
        # Calculate correlation between residuals
        partial_corr, _ = self._calculate_correlation(
            residuals_cause, 
            residuals_effect
        )
        
        return abs(partial_corr)
    
    def _get_residuals(
        self, 
        target: str, 
        predictors: List[str]
    ) -> pd.Series:
        """
        Calculate residuals from regressing target on predictors.
        
        Args:
            target: Target variable name
            predictors: List of predictor variable names
            
        Returns:
            Series of residuals
        """
        # Simple linear regression for residual calculation
        X = self.data[predictors].values
        y = self.data[target].values
        
        # Handle missing values
        valid_mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X_clean = X[valid_mask]
        y_clean = y[valid_mask]
        
        # Add intercept term
        X_with_intercept = np.column_stack([np.ones(len(X_clean)), X_clean])
        
        # Solve least squares
        try:
            beta = np.linalg.lstsq(X_with_intercept, y_clean, rcond=None)[0]
            residuals = y_clean - X_with_intercept @ beta
            
            # Return as Series with original index where valid
            result = pd.Series(index=self.data.index, dtype=float)
            result[valid_mask] = residuals
            return result
            
        except np.linalg.LinAlgError as e:
            logger.error(f"Linear algebra error in residual calculation: {e}")
            return pd.Series(0, index=self.data.index)
    
    def build_causal_graph(
        self, 
        corr_threshold: float = 0.3,
        cf_threshold: float = 0.2
    ) -> Dict[str, List[CausalEdge]]:
        """
        Build the causal graph using counterfactual reasoning.
        
        This method constructs a causal graph by:
        1. Identifying potential causal relationships based on correlation
        2. Applying counterfactual reasoning to distinguish causation from correlation
        3. Pruning edges that don't meet the counterfactual threshold
        
        Args:
            corr_threshold: Minimum absolute correlation to consider
            cf_threshold: Minimum counterfactual score for causal edge
            
        Returns:
            Dictionary mapping each variable to its list of causal effects
            
        Raises:
            RuntimeError: If graph construction fails
        """
        logger.info("Starting causal graph construction")
        
        try:
            # Step 1: Identify all potential causal relationships
            for target in self.variables:
                potential_causes = self._identify_potential_causes(
                    target, 
                    threshold=corr_threshold
                )
                
                for cause in potential_causes:
                    # Step 2: Identify potential confounders
                    confounders = [
                        v for v in self.variables 
                        if v != cause and v != target
                    ]
                    
                    # Step 3: Calculate counterfactual score
                    cf_score = self._calculate_counterfactual_score(
                        cause, 
                        target, 
                        confounders
                    )
                    
                    # Step 4: Calculate causal effect (simplified)
                    causal_effect = cf_score * np.sign(
                        self._calculate_correlation(
                            self.data[cause], 
                            self.data[target]
                        )[0]
                    )
                    
                    # Step 5: Create causal edge if meets threshold
                    if cf_score > cf_threshold:
                        edge = CausalEdge(
                            source=cause,
                            target=target,
                            correlation=self._calculate_correlation(
                                self.data[cause], 
                                self.data[target]
                            )[0],
                            causal_effect=causal_effect,
                            counterfactual_score=cf_score,
                            confidence=min(1.0, cf_score * 2)  # Simple confidence score
                        )
                        self.causal_graph[cause].append(edge)
                        
            logger.info(f"Causal graph constructed with {sum(len(v) for v in self.causal_graph.values())} edges")
            return dict(self.causal_graph)
            
        except Exception as e:
            error_msg = f"Failed to construct causal graph: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_causal_explanations(
        self, 
        variable: str, 
        top_n: int = 3
    ) -> List[Dict[str, Union[str, float]]]:
        """
        Get causal explanations for a variable's behavior.
        
        Args:
            variable: Variable to explain
            top_n: Number of top causes to return
            
        Returns:
            List of dictionaries with causal explanations
        """
        explanations = []
        
        for cause, edges in self.causal_graph.items():
            for edge in edges:
                if edge.target == variable:
                    explanations.append({
                        'cause': edge.source,
                        'effect': edge.target,
                        'correlation': edge.correlation,
                        'causal_effect': edge.causal_effect,
                        'counterfactual_score': edge.counterfactual_score,
                        'confidence': edge.confidence
                    })
        
        # Sort by counterfactual score
        explanations.sort(key=lambda x: x['counterfactual_score'], reverse=True)
        return explanations[:top_n]
    
    def export_graph_to_dict(self) -> Dict[str, List[Dict[str, Union[str, float]]]]:
        """
        Export the causal graph to a dictionary format.
        
        Returns:
            Dictionary representation of the causal graph
        """
        return {
            cause: [
                {
                    'target': edge.target,
                    'correlation': edge.correlation,
                    'causal_effect': edge.causal_effect,
                    'counterfactual_score': edge.counterfactual_score,
                    'confidence': edge.confidence
                }
                for edge in edges
            ]
            for cause, edges in self.causal_graph.items()
        }


# Example usage and demonstration
if __name__ == "__main__":
    # Create synthetic industrial process data
    np.random.seed(42)
    n_samples = 1000
    
    # Generate correlated variables with causal relationships
    temperature = np.random.normal(25, 5, n_samples)
    pressure = 0.7 * temperature + np.random.normal(0, 1, n_samples)
    catalyst = np.random.choice([0, 1], size=n_samples)
    
    # Target variable with causal relationships
    yield_rate = (
        0.5 * temperature + 
        0.3 * pressure + 
        5 * catalyst + 
        np.random.normal(0, 2, n_samples)
    )
    
    # Create DataFrame
    industrial_data = pd.DataFrame({
        'temperature': temperature,
        'pressure': pressure,
        'catalyst': catalyst,
        'yield': yield_rate
    })
    
    # Build causal graph
    builder = CounterfactualCausalGraphBuilder(
        data=industrial_data,
        alpha=0.05,
        min_samples=100
    )
    
    # Construct the causal graph
    causal_graph = builder.build_causal_graph(
        corr_threshold=0.2,
        cf_threshold=0.15
    )
    
    # Print results
    print("\nCausal Graph Edges:")
    for cause, edges in causal_graph.items():
        for edge in edges:
            print(f"{edge.source} -> {edge.target}")
            print(f"  Correlation: {edge.correlation:.3f}")
            print(f"  Causal Effect: {edge.causal_effect:.3f}")
            print(f"  Counterfactual Score: {edge.counterfactual_score:.3f}")
            print(f"  Confidence: {edge.confidence:.3f}\n")
    
    # Get explanations for yield
    explanations = builder.get_causal_explanations('yield', top_n=2)
    print("\nTop causes for yield:")
    for exp in explanations:
        print(f"{exp['cause']}: Effect = {exp['causal_effect']:.3f}")