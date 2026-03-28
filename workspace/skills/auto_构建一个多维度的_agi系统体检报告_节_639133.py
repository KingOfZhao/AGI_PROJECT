"""
AGI System Health Check Module

This module provides functionality to generate multi-dimensional health reports for AGI systems.
It integrates topology health, semantic consistency, skill effectiveness, and temporal decay curves.

Key Features:
- Topology health assessment
- Semantic consistency validation
- Skill effectiveness measurement
- Temporal decay curve analysis

Example Usage:
    >>> from agi_health_check import AGIHealthChecker
    >>> checker = AGIHealthChecker()
    >>> report = checker.generate_health_report(system_data)
    >>> print(report.summary())
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthMetric(BaseModel):
    """Data model for individual health metrics"""
    name: str
    value: float = Field(..., ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict] = None

    @validator('value')
    def validate_value(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Metric value must be between 0 and 1")
        return v


class SystemData(BaseModel):
    """Input data model for AGI system health check"""
    topology_data: Dict[str, float]
    semantic_data: Dict[str, float]
    skill_data: Dict[str, float]
    temporal_data: Dict[str, List[float]]
    metadata: Optional[Dict] = None


@dataclass
class HealthReport:
    """Data class for storing health report results"""
    topology_health: float
    semantic_consistency: float
    skill_effectiveness: float
    temporal_decay: float
    overall_score: float
    timestamp: datetime
    metrics: Dict[str, HealthMetric]
    warnings: List[str]

    def summary(self) -> str:
        """Generate a summary string of the health report"""
        return (
            f"AGI System Health Report ({self.timestamp})\n"
            f"Overall Score: {self.overall_score:.2f}\n"
            f"Topology Health: {self.topology_health:.2f}\n"
            f"Semantic Consistency: {self.semantic_consistency:.2f}\n"
            f"Skill Effectiveness: {self.skill_effectiveness:.2f}\n"
            f"Temporal Decay: {self.temporal_decay:.2f}\n"
            f"Warnings: {len(self.warnings)}"
        )


def _validate_input_data(data: SystemData) -> None:
    """
    Validate input data structure and values.
    
    Args:
        data: SystemData object to validate
        
    Raises:
        ValueError: If data validation fails
    """
    if not all([data.topology_data, data.semantic_data, data.skill_data, data.temporal_data]):
        raise ValueError("All data categories must contain at least one metric")
    
    for category, metrics in [
        ("topology", data.topology_data),
        ("semantic", data.semantic_data),
        ("skill", data.skill_data)
    ]:
        for name, value in metrics.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{category} metric '{name}' value {value} out of range [0,1]")
    
    for name, values in data.temporal_data.items():
        if not values:
            raise ValueError(f"Temporal metric '{name}' contains empty data")
        if not all(0 <= v <= 1 for v in values):
            raise ValueError(f"Temporal metric '{name}' contains out of range values")


def calculate_temporal_decay_curve(values: List[float]) -> Tuple[float, float]:
    """
    Calculate temporal decay characteristics from a time series of values.
    
    Args:
        values: List of time-ordered metric values
        
    Returns:
        Tuple containing (decay_rate, current_value)
        
    Raises:
        ValueError: If input data is invalid
    """
    if not values:
        raise ValueError("Empty temporal data provided")
    
    try:
        values_arr = np.array(values)
        if len(values_arr) < 2:
            return 0.0, values_arr[0]
        
        # Calculate decay rate (slope of linear regression)
        x = np.arange(len(values_arr))
        y = values_arr
        slope, _ = np.polyfit(x, y, 1)
        
        # Current value is the last value in the series
        current_value = values_arr[-1]
        
        return float(slope), float(current_value)
    
    except Exception as e:
        logger.error(f"Error calculating temporal decay: {str(e)}")
        raise


def analyze_topology_health(topology_data: Dict[str, float]) -> HealthMetric:
    """
    Analyze topology health from provided metrics.
    
    Args:
        topology_data: Dictionary of topology metrics
        
    Returns:
        HealthMetric object with topology health assessment
        
    Raises:
        ValueError: If input data is invalid
    """
    if not topology_data:
        raise ValueError("Empty topology data provided")
    
    try:
        # Calculate weighted average with critical metrics having higher weight
        critical_metrics = ['node_connectivity', 'edge_stability']
        weights = {k: 2.0 if k in critical_metrics else 1.0 for k in topology_data}
        
        total_weight = sum(weights.values())
        weighted_sum = sum(v * weights[k] for k, v in topology_data.items())
        
        health_score = weighted_sum / total_weight
        
        return HealthMetric(
            name="topology_health",
            value=health_score,
            metadata={"metrics": topology_data, "weights": weights}
        )
    
    except Exception as e:
        logger.error(f"Error analyzing topology health: {str(e)}")
        raise


class AGIHealthChecker:
    """
    Main class for performing multi-dimensional health checks on AGI systems.
    
    Attributes:
        config: Configuration dictionary for health check parameters
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the health checker.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {
            'topology_weight': 0.3,
            'semantic_weight': 0.3,
            'skill_weight': 0.2,
            'temporal_weight': 0.2,
            'warning_threshold': 0.6
        }
        logger.info("AGIHealthChecker initialized with config: %s", self.config)
    
    def _analyze_semantic_consistency(self, semantic_data: Dict[str, float]) -> HealthMetric:
        """
        Analyze semantic consistency from provided metrics.
        
        Args:
            semantic_data: Dictionary of semantic metrics
            
        Returns:
            HealthMetric object with semantic consistency assessment
        """
        if not semantic_data:
            raise ValueError("Empty semantic data provided")
        
        try:
            # Calculate harmonic mean for semantic consistency
            values = list(semantic_data.values())
            harmonic_mean = len(values) / sum(1.0 / v for v in values if v > 0)
            
            return HealthMetric(
                name="semantic_consistency",
                value=harmonic_mean,
                metadata={"metrics": semantic_data}
            )
        
        except Exception as e:
            logger.error(f"Error analyzing semantic consistency: {str(e)}")
            raise
    
    def _analyze_skill_effectiveness(self, skill_data: Dict[str, float]) -> HealthMetric:
        """
        Analyze skill effectiveness from provided metrics.
        
        Args:
            skill_data: Dictionary of skill metrics
            
        Returns:
            HealthMetric object with skill effectiveness assessment
        """
        if not skill_data:
            raise ValueError("Empty skill data provided")
        
        try:
            # Calculate geometric mean for skill effectiveness
            values = list(skill_data.values())
            geometric_mean = np.exp(np.mean(np.log(values)))
            
            return HealthMetric(
                name="skill_effectiveness",
                value=geometric_mean,
                metadata={"metrics": skill_data}
            )
        
        except Exception as e:
            logger.error(f"Error analyzing skill effectiveness: {str(e)}")
            raise
    
    def _generate_warnings(self, metrics: Dict[str, HealthMetric]) -> List[str]:
        """
        Generate warning messages based on metric thresholds.
        
        Args:
            metrics: Dictionary of HealthMetric objects
            
        Returns:
            List of warning messages
        """
        warnings = []
        threshold = self.config['warning_threshold']
        
        for name, metric in metrics.items():
            if metric.value < threshold:
                warning_msg = (
                    f"Warning: {name.replace('_', ' ').title()} is low "
                    f"({metric.value:.2f} < {threshold})"
                )
                warnings.append(warning_msg)
                logger.warning(warning_msg)
        
        return warnings
    
    def generate_health_report(self, system_data: SystemData) -> HealthReport:
        """
        Generate a comprehensive health report for the AGI system.
        
        Args:
            system_data: SystemData object containing all health metrics
            
        Returns:
            HealthReport object with comprehensive health assessment
            
        Raises:
            ValueError: If input data validation fails
        """
        try:
            # Validate input data
            _validate_input_data(system_data)
            
            # Analyze each dimension
            topology_metric = analyze_topology_health(system_data.topology_data)
            semantic_metric = self._analyze_semantic_consistency(system_data.semantic_data)
            skill_metric = self._analyze_skill_effectiveness(system_data.skill_data)
            
            # Analyze temporal decay
            decay_rates = {}
            current_values = {}
            for name, values in system_data.temporal_data.items():
                rate, current = calculate_temporal_decay_curve(values)
                decay_rates[name] = rate
                current_values[name] = current
            
            # Calculate overall temporal decay score
            temporal_score = 1.0 - min(1.0, max(0.0, np.mean(list(decay_rates.values()))))
            
            temporal_metric = HealthMetric(
                name="temporal_decay",
                value=temporal_score,
                metadata={
                    "decay_rates": decay_rates,
                    "current_values": current_values
                }
            )
            
            # Combine all metrics
            metrics = {
                "topology_health": topology_metric,
                "semantic_consistency": semantic_metric,
                "skill_effectiveness": skill_metric,
                "temporal_decay": temporal_metric
            }
            
            # Calculate overall score
            overall_score = (
                topology_metric.value * self.config['topology_weight'] +
                semantic_metric.value * self.config['semantic_weight'] +
                skill_metric.value * self.config['skill_weight'] +
                temporal_metric.value * self.config['temporal_weight']
            )
            
            # Generate warnings
            warnings = self._generate_warnings(metrics)
            
            # Create and return report
            report = HealthReport(
                topology_health=topology_metric.value,
                semantic_consistency=semantic_metric.value,
                skill_effectiveness=skill_metric.value,
                temporal_decay=temporal_metric.value,
                overall_score=overall_score,
                timestamp=datetime.now(),
                metrics=metrics,
                warnings=warnings
            )
            
            logger.info("Health report generated successfully")
            return report
        
        except Exception as e:
            logger.error(f"Error generating health report: {str(e)}")
            raise


# Example usage
if __name__ == "__main__":
    # Sample input data
    sample_data = SystemData(
        topology_data={
            "node_connectivity": 0.85,
            "edge_stability": 0.78,
            "cluster_balance": 0.92
        },
        semantic_data={
            "concept_alignment": 0.88,
            "context_relevance": 0.79,
            "term_consistency": 0.91
        },
        skill_data={
            "reasoning": 0.82,
            "planning": 0.75,
            "execution": 0.89
        },
        temporal_data={
            "performance": [0.9, 0.85, 0.82, 0.78, 0.75],
            "accuracy": [0.95, 0.93, 0.91, 0.89, 0.87]
        },
        metadata={"system_id": "agi-prod-001"}
    )
    
    # Generate health report
    checker = AGIHealthChecker()
    try:
        report = checker.generate_health_report(sample_data)
        print("\n" + "="*50)
        print(report.summary())
        print("="*50 + "\n")
        
        # Print detailed warnings if any
        if report.warnings:
            print("System Warnings:")
            for warning in report.warnings:
                print(f"- {warning}")
    except Exception as e:
        print(f"Error generating health report: {str(e)}")