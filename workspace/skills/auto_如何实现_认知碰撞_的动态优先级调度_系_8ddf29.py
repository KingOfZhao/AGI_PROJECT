"""
Module: cognitive_collision_scheduler.py

Description:
    Implements a dynamic priority scheduling system for "Cognitive Collision" forces.
    This system manages computational resources for four types of cognitive forces:
    1. Top-Down (Decomposition)
    2. Bottom-Up (Synthesis)
    3. Cross-Domain (Lateral Thinking)
    4. Lateral (Associative)

    The allocation is dynamically adjusted based on the system's "Cognitive Health,"
    specifically focusing on Falsification Rate (stagnation indicator) and
    Node Growth Rate (chaos indicator).

Author: Senior Python Engineer (AGI System Core)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveScheduler")


class CognitiveForce(Enum):
    """Enumeration of cognitive forces acting on the system."""
    TOP_DOWN = "top_down"          # Decomposition, Analysis
    BOTTOM_UP = "bottom_up"        # Synthesis, Pattern Matching
    CROSS_DOMAIN = "cross_domain"  # Lateral Thinking, Innovation
    LATERAL = "lateral"            # Association, Memory Retrieval


class SystemState(Enum):
    """Enumeration of recognized high-level system states."""
    HEALTHY = "healthy"
    RIGID = "rigid"       # High stagnation, needs innovation
    CHAOTIC = "chaotic"   # High noise, needs structure
    STABLE = "stable"     # Balanced state


@dataclass
class HealthMetrics:
    """
    Container for system health metrics.
    
    Attributes:
        falsification_rate (float): Recent rate at which hypotheses are rejected (0.0 to 1.0).
                                    High value implies the system is learning or failing fast.
        node_growth_rate (float): Rate of new concept generation per cycle (0.0 to 10.0+).
                                  High value implies expansion or potential noise.
        entropy_level (float): Overall disorder in the knowledge graph (0.0 to 1.0).
    """
    falsification_rate: float = 0.0
    node_growth_rate: float = 0.0
    entropy_level: float = 0.5

    def validate(self) -> bool:
        """Validates that metrics are within logical bounds."""
        if not (0.0 <= self.falsification_rate <= 1.0):
            raise ValueError(f"Falsification rate out of bounds: {self.falsification_rate}")
        if self.node_growth_rate < 0.0:
            raise ValueError(f"Node growth rate cannot be negative: {self.node_growth_rate}")
        if not (0.0 <= self.entropy_level <= 1.0):
            raise ValueError(f"Entropy level out of bounds: {self.entropy_level}")
        return True


@dataclass
class SchedulingResult:
    """Result of the scheduling calculation."""
    allocations: Dict[CognitiveForce, float]
    current_state: SystemState
    confidence: float
    timestamp: str


def _normalize_weights(raw_weights: Dict[CognitiveForce, float]) -> Dict[CognitiveForce, float]:
    """
    [Helper Function] Normalizes raw weight scores into a probability distribution (sum=1.0).
    
    Args:
        raw_weights (Dict[CognitiveForce, float]): Unnormalized scores.
        
    Returns:
        Dict[CognitiveForce, float]: Normalized percentages for resource allocation.
    """
    total = sum(raw_weights.values())
    if total <= 1e-9:
        logger.warning("Total weights approx zero. Defaulting to uniform distribution.")
        count = len(CognitiveForce)
        return {force: 1.0/count for force in CognitiveForce}
    
    normalized = {k: v / total for k, v in raw_weights.items()}
    return normalized


def diagnose_system_state(metrics: HealthMetrics) -> Tuple[SystemState, Dict[str, float]]:
    """
    [Core Function 1] Analyzes health metrics to determine the current cognitive state.
    
    Logic:
    - Rigid: Low falsification, low growth. System is stuck.
    - Chaotic: High growth, high entropy. System is hallucinating or overwhelmed.
    - Healthy: Moderate levels.
    
    Args:
        metrics (HealthMetrics): Current system telemetry.
        
    Returns:
        Tuple[SystemState, Dict[str, float]]: The diagnosed state and severity scores.
    """
    logger.info("Diagnosing system state...")
    try:
        metrics.validate()
    except ValueError as e:
        logger.error(f"Invalid metrics received: {e}")
        # Default to safe mode
        return SystemState.STABLE, {"error": 1.0}

    # Calculate State Scores (0.0 to 1.0)
    # Rigidity Score: Inverse of activity
    rigidity_score = (1.0 - metrics.falsification_rate) * (1.0 / (1.0 + metrics.node_growth_rate))
    
    # Chaos Score: High growth + High Entropy
    chaos_score = math.tanh(metrics.node_growth_rate / 5.0) * metrics.entropy_level
    
    logger.debug(f"Rigidity Score: {rigidity_score:.3f}, Chaos Score: {chaos_score:.3f}")

    # Thresholds
    RIGID_THRESHOLD = 0.6
    CHAOS_THRESHOLD = 0.6

    if rigidity_score > RIGID_THRESHOLD:
        return SystemState.RIGID, {"rigidity": rigidity_score}
    elif chaos_score > CHAOS_THRESHOLD:
        return SystemState.CHAOTIC, {"chaos": chaos_score}
    else:
        return SystemState.HEALTHY, {"balance": 1.0 - max(rigidity_score, chaos_score)}


def calculate_dynamic_allocations(
    metrics: HealthMetrics, 
    base_weights: Optional[Dict[CognitiveForce, float]] = None
) -> SchedulingResult:
    """
    [Core Function 2] Calculates resource allocation percentages for each cognitive force.
    
    Strategy:
    - If RIGID: Boost CROSS_DOMAIN (to break patterns) and BOTTOM_UP (to find new connections).
    - If CHAOTIC: Boost TOP_DOWN (to impose structure/hierarchy) and suppress random growth.
    - If HEALTHY: Maintain base weights with slight entropy adjustments.
    
    Args:
        metrics (HealthMetrics): The current health metrics of the system.
        base_weights (Optional[Dict[CognitiveForce, float]]): Default distribution (default: uniform).
        
    Returns:
        SchedulingResult: Contains allocation map and metadata.
    """
    from datetime import datetime
    
    logger.info("Calculating dynamic priority schedule...")
    
    # 1. Setup Base Weights
    if base_weights is None:
        # Default uniform distribution
        w = 1.0 / len(CognitiveForce)
        current_weights = {force: w for force in CognitiveForce}
    else:
        # Ensure all forces are present
        current_weights = {force: base_weights.get(force, 0.1) for force in CognitiveForce}

    # 2. Diagnose State
    state, _ = diagnose_system_state(metrics)
    
    # 3. Apply Modifiers based on State
    # We use multiplicative factors to shift priority
    MODIFIER_STRONG = 2.5
    MODIFIER_MEDIUM = 1.5
    MODIFIER_WEAK = 0.5
    
    logger.info(f"Applying strategy for state: {state.value}")

    if state == SystemState.RIGID:
        # Need to break rigidity
        current_weights[CognitiveForce.CROSS_DOMAIN] *= MODIFIER_STRONG
        current_weights[CognitiveForce.BOTTOM_UP] *= MODIFIER_MEDIUM
        current_weights[CognitiveForce.TOP_DOWN] *= MODIFIER_WEAK # Reduce analysis paralysis
        
    elif state == SystemState.CHAOTIC:
        # Need structure
        current_weights[CognitiveForce.TOP_DOWN] *= MODIFIER_STRONG
        current_weights[CognitiveForce.LATERAL] *= MODIFIER_WEAK # Reduce noise
        current_weights[CognitiveForce.CROSS_DOMAIN] *= MODIFIER_WEAK
        
    elif state == SystemState.HEALTHY:
        # Balanced exploration/exploitation
        # Slight preference for top-down organization if entropy creeps up
        if metrics.entropy_level > 0.5:
            current_weights[CognitiveForce.TOP_DOWN] *= MODIFIER_MEDIUM

    # 4. Normalize and Package
    final_allocations = _normalize_weights(current_weights)
    
    result = SchedulingResult(
        allocations=final_allocations,
        current_state=state,
        confidence=0.0, # Placeholder for future ML confidence
        timestamp=datetime.utcnow().isoformat()
    )
    
    logger.info(f"Allocation complete. Top priority: {max(final_allocations, key=final_allocations.get).value}")
    return result


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Scenario 1: System is Stagnant (Rigid)
    # Low falsification, low growth
    rigid_metrics = HealthMetrics(
        falsification_rate=0.05,
        node_growth_rate=0.2,
        entropy_level=0.2
    )
    
    print("\n--- Scenario 1: Rigid System ---")
    result_rigid = calculate_dynamic_allocations(rigid_metrics)
    print(f"State: {result_rigid.current_state.value}")
    for force, alloc in result_rigid.allocations.items():
        print(f"{force.value:<15}: {alloc:.2%}")

    # Scenario 2: System is Spinning out of control (Chaotic)
    # High growth, high entropy
    chaotic_metrics = HealthMetrics(
        falsification_rate=0.4,
        node_growth_rate=9.5, # Very high growth
        entropy_level=0.95    # High disorder
    )
    
    print("\n--- Scenario 2: Chaotic System ---")
    result_chaotic = calculate_dynamic_allocations(chaotic_metrics)
    print(f"State: {result_chaotic.current_state.value}")
    for force, alloc in result_chaotic.allocations.items():
        print(f"{force.value:<15}: {alloc:.2%}")