"""
Module: auto_environment_boundary_detector.py

Description:
    This module implements an 'Environment Context Boundary Detector' designed to evaluate the 
    robustness of AGI Skill Nodes. It addresses the narrowness problem by performing parameter 
    sweeps on environmental variables (e.g., law enforcement intensity, market volatility).
    
    It simulates how a Skill's success rate changes as environmental parameters shift. If a Skill 
    is highly sensitive (lacks robustness) and contains no adaptive logic, its quality score is 
    penalized.

Domain: Complex Systems / AGI Safety & Evaluation

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Callable, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class SkillNode:
    """
    Represents a SKILL node in the AGI system.
    
    Attributes:
        id: Unique identifier for the skill.
        name: Human-readable name.
        success_rate: The nominal success rate (0.0 to 1.0) under ideal conditions.
        environmental_sensitivity: A dictionary defining sensitivity to parameters.
            Format: {'param_name': {'sensitivity_factor': float, 'threshold': float}}
            Higher sensitivity_factor means the skill fails faster as param changes.
        has_adaptive_logic: Boolean indicating if the skill can adjust to changes.
    """
    id: str
    name: str
    success_rate: float
    environmental_sensitivity: Dict[str, Dict[str, float]] = field(default_factory=dict)
    has_adaptive_logic: bool = False

    def __post_init__(self):
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError(f"Success rate for {self.id} must be between 0.0 and 1.0.")

@dataclass
class EnvironmentContext:
    """
    Represents the state of the environment.
    
    Attributes:
        parameters: A dictionary of environmental parameters (normalized 0.0 to 1.0).
                   e.g., {'enforcement_intensity': 0.8, 'market_volatility': 0.3}
    """
    parameters: Dict[str, float]

    def validate(self):
        for k, v in self.parameters.items():
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"Parameter {k} value {v} is out of bounds [0, 1].")

@dataclass
class ScanResult:
    """Holds the result of the boundary scan."""
    skill_id: str
    is_robust: bool
    sensitivity_score: float  # 0.0 (Robust) to 1.0 (Extremely Sensitive)
    adjusted_quality_score: float
    details: Dict[str, Any]

# --- Core Functions ---

def simulate_skill_performance(
    skill: SkillNode, 
    env_context: EnvironmentContext
) -> float:
    """
    Simulates the execution of a skill within a specific environment context.
    
    This acts as a mock executor or a sandbox interface. It calculates the projected
    success rate based on the distance between the skill's ideal context and the 
    current environment context.
    
    Args:
        skill: The SkillNode to test.
        env_context: The environment context to test against.
        
    Returns:
        float: The calculated success rate (0.0 to 1.0) for this context.
    """
    current_success = skill.success_rate
    
    # If skill has adaptive logic, it resists environmental pressure to a degree
    # but consumes more resources (conceptually). Here we just model robustness.
    if skill.has_adaptive_logic:
        # Adaptive logic flattens the sensitivity curve
        resistance_factor = 0.2 
    else:
        resistance_factor = 1.0

    for param_name, param_value in env_context.parameters.items():
        if param_name in skill.environmental_sensitivity:
            config = skill.environmental_sensitivity[param_name]
            threshold = config.get('threshold', 0.5)
            sensitivity = config.get('sensitivity_factor', 1.0)
            
            # Calculate deviation from threshold (simple linear model for simulation)
            # If param value > threshold, success rate drops
            if param_value > threshold:
                deviation = param_value - threshold
                # Apply sensitivity
                penalty = deviation * sensitivity * current_success * resistance_factor
                current_success = max(0.0, current_success - penalty)
                
    logger.debug(f"Simulated {skill.name} at {env_context.parameters}: {current_success:.3f}")
    return current_success

def perform_boundary_scan(
    skill: SkillNode,
    param_ranges: Dict[str, List[float]],
    stability_threshold: float = 0.7,
    penalty_weight: float = 1.5
) -> ScanResult:
    """
    Performs an 'Environment Parameter Scan' to detect context boundary fragility.
    
    It sweeps through defined parameter ranges and calculates the variance and 
    minimum performance of the skill.
    
    Args:
        skill: The SkillNode to evaluate.
        param_ranges: Dict defining the sweep range for parameters.
                      e.g., {'enforcement_intensity': [0.1, 0.5, 0.9]}
        stability_threshold: The minimum success rate required to consider the skill 'stable'.
        penalty_weight: Multiplier for reducing quality score if the skill is fragile.
        
    Returns:
        ScanResult: An object containing robustness analysis and adjusted scores.
    """
    logger.info(f"Starting Boundary Scan for Skill: {skill.name} (ID: {skill.id})")
    
    if not param_ranges:
        logger.warning("No parameter ranges defined for scan.")
        return ScanResult(
            skill_id=skill.id,
            is_robust=True,
            sensitivity_score=0.0,
            adjusted_quality_score=skill.success_rate,
            details={"message": "No scan performed"}
        )

    performance_history: List[float] = []
    failure_count = 0
    total_steps = 0
    
    # Generate scenarios (simple iteration for 1-2 params, complex systems might need grid search)
    # Here we assume independent parameter scans for simplicity
    for param_name, values in param_ranges.items():
        for val in values:
            # Create temporary context
            ctx = EnvironmentContext(parameters={param_name: val})
            try:
                ctx.validate()
                performance = simulate_skill_performance(skill, ctx)
                performance_history.append(performance)
                total_steps += 1
                
                if performance < stability_threshold:
                    failure_count += 1
            except ValueError as ve:
                logger.error(f"Validation error during scan: {ve}")
                continue

    if total_steps == 0:
        avg_perf = skill.success_rate
        variance = 0.0
    else:
        avg_perf = np.mean(performance_history)
        variance = np.std(performance_history)

    # Calculate Sensitivity Score (0 to 1)
    # Higher variance and lower average performance increase sensitivity
    normalized_variance = min(1.0, variance * 5) # Scale variance for significance
    sensitivity_score = (normalized_variance + (1.0 - avg_perf)) / 2.0
    
    # Determine Robustness
    is_robust = (failure_count == 0) and (sensitivity_score < 0.3)
    
    # Adjust Quality Score
    # If robust or adaptive, keep score high. If sensitive, penalize.
    if skill.has_adaptive_logic:
        logger.info(f"Skill {skill.id} contains adaptive logic. Mitigating sensitivity penalty.")
        adjusted_score = skill.success_rate # Assume logic handles the context
    else:
        if not is_robust:
            # Heavy penalty for narrow skills
            adjusted_score = skill.success_rate * (1.0 - (sensitivity_score * penalty_weight))
            adjusted_score = max(0.0, adjusted_score)
            logger.warning(f"Skill {skill.id} is FRAGILE. Score reduced from {skill.success_rate:.2f} to {adjusted_score:.2f}")
        else:
            adjusted_score = skill.success_rate

    return ScanResult(
        skill_id=skill.id,
        is_robust=is_robust,
        sensitivity_score=round(sensitivity_score, 4),
        adjusted_quality_score=round(adjusted_score, 4),
        details={
            "average_performance": round(avg_perf, 4),
            "std_deviation": round(variance, 4),
            "failure_count": failure_count,
            "total_scenarios": total_steps
        }
    )

# --- Helper Functions ---

def format_scan_report(result: ScanResult) -> str:
    """
    Formats the scan result into a human-readable string report.
    
    Args:
        result: The ScanResult object.
        
    Returns:
        str: Formatted report string.
    """
    status = "ROBUST" if result.is_robust else "FRAGILE"
    header = f"=== Evaluation Report: {result.skill_id} ==="
    separator = "-" * 40
    
    report_lines = [
        header,
        separator,
        f"Status: {status}",
        f"Sensitivity Index: {result.sensitivity_score:.2f}",
        f"Original Quality Score: {result.details.get('original_score', 'N/A')}",
        f"Adjusted Quality Score: {result.adjusted_quality_score:.2f}",
        separator,
        "Statistics:",
        f"  - Scenarios Tested: {result.details.get('total_scenarios', 0)}",
        f"  - Failures (Below Threshold): {result.details.get('failure_count', 0)}",
        f"  - Avg Performance: {result.details.get('average_performance', 0):.3f}",
        separator
    ]
    
    return "\n".join(report_lines)

# --- Main Execution / Example Usage ---

if __name__ == "__main__":
    # Setup Example Data
    
    # 1. Define a Skill that relies on loose regulation (The "Street Vendor" example)
    street_vendor_skill = SkillNode(
        id="skill_street_vendor_01",
        name="Street Vendor Tactics",
        success_rate=0.95, # High success in ideal conditions
        environmental_sensitivity={
            "enforcement_intensity": {
                "threshold": 0.3, # Fails if enforcement goes above 0.3
                "sensitivity_factor": 1.5 # Very sensitive
            }
        },
        has_adaptive_logic=False # Narrow skill, no adaptation
    )
    
    # 2. Define a Robust Skill (e.g., Online Trading)
    online_trading_skill = SkillNode(
        id="skill_trade_02",
        name="Algorithmic Trading",
        success_rate=0.60, # Moderate baseline
        environmental_sensitivity={
            "market_volatility": {
                "threshold": 0.8, # Handles high volatility
                "sensitivity_factor": 0.2 # Low sensitivity
            }
        },
        has_adaptive_logic=True
    )

    # 3. Define the Scan Range
    # We want to scan 'enforcement_intensity' from 0.1 (loose) to 0.9 (strict)
    scan_params = {
        "enforcement_intensity": np.linspace(0.1, 0.9, 9).tolist() # [0.1, 0.2, ..., 0.9]
    }
    
    # Execute Scan for Fragile Skill
    logger.info("Testing Fragile Skill...")
    result_fragile = perform_boundary_scan(
        skill=street_vendor_skill, 
        param_ranges=scan_params
    )
    
    # Execute Scan for Robust Skill (using different param name just for logic demo, 
    # though in real system param keys must match. Let's use a generic 'load' param)
    scan_params_robust = {
        "market_volatility": np.linspace(0.1, 0.9, 9).tolist()
    }
    logger.info("Testing Robust Skill...")
    result_robust = perform_boundary_scan(
        skill=online_trading_skill, 
        param_ranges=scan_params_robust
    )
    
    # Output Results
    print("\n" + format_scan_report(result_fragile))
    print("\n" + format_scan_report(result_robust))