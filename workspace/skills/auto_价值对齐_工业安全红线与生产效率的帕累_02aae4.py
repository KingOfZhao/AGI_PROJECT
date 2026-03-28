"""
Module: industrial_safety_pareto_optimizer
Description: AGI Skill for resolving conflicts between industrial safety red lines
             and production efficiency using Pareto optimization logic.

This module implements a dynamic decision engine that translates abstract safety
regulations into calculatable 'stop-loss functions'. It aims to achieve Pareto
optimality where production efficiency is maximized subject to the constraint
that the probability of crossing a safety red line never exceeds a defined threshold.

Key Concepts:
- Safety Red Line: A boundary defined by probability of failure (PoF) > Threshold.
- Efficiency: Production throughput or speed.
- Rational Risk: Operating close to, but strictly under, the safety threshold.

Author: AGI System
Version: 2.0 (Refined for Industrial Standards)
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SafetyParetoOptimizer")

class SafetyStatus(Enum):
    """Status of the current operational state."""
    SAFE = "SAFE"                 # Operating well within limits
    WARNING = "WARNING"           # Nearing limits, efficiency optimized
    CRITICAL = "CRITICAL"         # Approaching red line, prepare to halt
    EMERGENCY_STOP = "E_STOP"     # Red line crossed or unavoidable

@dataclass
class SensorReading:
    """Represents a sensor input with noise handling."""
    sensor_id: str
    value: float
    unit: str
    timestamp: float
    confidence: float = 1.0  # 0.0 to 1.0 reliability of the sensor

@dataclass
class OperationalParameters:
    """Dynamic parameters for the AGI decision loop."""
    max_risk_tolerance: float = 0.05    # 5% max probability of failure
    efficiency_weight: float = 0.8      # Importance of efficiency (0-1)
    current_speed_ratio: float = 1.0    # 1.0 = 100% speed
    safety_decay_rate: float = 0.1      # How fast safety margin degrades with speed
    
@dataclass
class DecisionResult:
    """Output of the decision engine."""
    action: str
    target_speed: float
    risk_score: float
    status: SafetyStatus
    message: str

class IndustrialSafetyOptimizer:
    """
    Core class for balancing safety and efficiency.
    
    Includes methods for calculating risk based on sensor fusion and
    determining the optimal operational speed.
    """

    def __init__(self, params: OperationalParameters):
        self.params = params
        self._validate_params()
        logger.info("IndustrialSafetyOptimizer initialized with tolerance: %f", 
                    params.max_risk_tolerance)

    def _validate_params(self) -> None:
        """Validate input parameters to prevent configuration errors."""
        if not 0.0 <= self.params.max_risk_tolerance <= 1.0:
            raise ValueError("Risk tolerance must be between 0.0 and 1.0")
        if not 0.0 <= self.params.efficiency_weight <= 1.0:
            raise ValueError("Efficiency weight must be between 0.0 and 1.0")

    def _calculate_derived_risk_factor(self, sensor_data: List[SensorReading]) -> float:
        """
        [Helper] Aggregates sensor data into a unified risk factor.
        
        Uses a weighted geometric mean to simulate how multiple minor issues 
        can compound into a major risk.
        
        Args:
            sensor_data: List of sensor readings.
            
        Returns:
            A normalized risk score between 0.0 (Safe) and 1.0 (Failure).
        """
        if not sensor_data:
            return 0.0

        compounded_risk = 1.0
        total_weight = 0.0

        for reading in sensor_data:
            # Validate individual reading
            if reading.value < 0:
                logger.warning(f"Negative sensor value detected for {reading.sensor_id}, taking absolute.")
                reading.value = abs(reading.value)

            # Normalize value to 0-1 range based on hypothetical max limits
            # Here we assume value represents a % of max capacity for simplicity
            normalized_load = min(reading.value / 100.0, 1.5) # Cap at 150%
            
            # Adjust for sensor confidence (low confidence = higher risk assumption)
            adjusted_risk = normalized_load * (1.0 + (1.0 - reading.confidence))
            
            # Compounding risk
            weight = reading.confidence
            compounded_risk *= (1.0 + adjusted_risk) ** weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
            
        # Normalize the compounded result back to a 0-1 probability scale
        final_risk = (compounded_risk ** (1.0 / total_weight)) - 1.0
        return min(max(final_risk, 0.0), 1.0)

    def evaluate_stop_loss_function(self, risk_score: float, speed: float) -> Tuple[bool, float]:
        """
        [Core 1] Determines if operations should halt based on dynamic stop-loss.
        
        Logic:
        - If current risk > tolerance, STOP.
        - If predicted risk (risk * speed_factor) > tolerance * 1.1, WARN.
        
        Args:
            risk_score: Current calculated risk from sensors.
            speed: Current operational speed (0.0 to 2.0 ratio).
            
        Returns:
            Tuple (should_stop, urgency_score)
        """
        # Project risk based on current speed (higher speed = exponentially higher risk)
        # This is the "Stop Loss Function"
        projected_risk = risk_score * (speed ** 2) 
        
        threshold = self.params.max_risk_tolerance
        
        if projected_risk > threshold * 1.5:
            logger.critical(f"EMERGENCY STOP triggered. Projected risk: {projected_risk:.4f}")
            return True, 1.0
        elif projected_risk > threshold:
            logger.warning(f"Approaching Safety Red Line. Projected risk: {projected_risk:.4f}")
            return False, 0.8
        
        return False, projected_risk / threshold if threshold > 0 else 0.0

    def optimize_pareto_efficiency(self, sensor_data: List[SensorReading]) -> DecisionResult:
        """
        [Core 2] Main loop to find the Pareto Optimal operational point.
        
        Tries to maximize speed while keeping the 'Stop Loss' function < Threshold.
        
        Args:
            sensor_data: Real-time data from industrial sensors.
            
        Returns:
            DecisionResult object containing the AGI's decision.
        """
        # 1. Data Validation & Risk Calculation
        base_risk = self._calculate_derived_risk_factor(sensor_data)
        
        # 2. Check Immediate Stop Condition
        should_stop, urgency = self.evaluate_stop_loss_function(base_risk, self.params.current_speed_ratio)
        
        if should_stop:
            return DecisionResult(
                action="EMERGENCY_BRAKE",
                target_speed=0.0,
                risk_score=base_risk,
                status=SafetyStatus.EMERGENCY_STOP,
                message="Safety red line breached. Initiating emergency protocols."
            )

        # 3. Pareto Optimization Logic
        # Calculate the maximum speed that keeps risk just under the threshold
        # Formula: base_risk * speed^2 <= threshold
        # speed = sqrt(threshold / base_risk)
        
        max_safe_speed = 0.0
        if base_risk > 0.0001: # Avoid division by zero
            max_safe_speed = math.sqrt(self.params.max_risk_tolerance / base_risk)
        else:
            max_safe_speed = 2.0 # If risk is negligible, allow max hardware speed

        # Apply conservative buffer based on urgency
        # If urgency is high (close to 1.0), reduce speed more aggressively
        buffer_factor = 1.0 - (urgency * 0.3) 
        recommended_speed = max_safe_speed * buffer_factor
        
        # Clamp speed to physical limits (e.g., 0 to 1.5 standard rate)
        recommended_speed = max(0.0, min(recommended_speed, 1.5))
        
        # 4. Determine Status
        if urgency > 0.8:
            status = SafetyStatus.CRITICAL
            msg = "Operating near safety limits. Speed reduced to maintain containment."
        elif urgency > 0.5:
            status = SafetyStatus.WARNING
            msg = "High efficiency mode engaged with active risk monitoring."
        else:
            status = SafetyStatus.SAFE
            msg = "Optimal operating conditions. Efficiency maximized."

        logger.info(f"Decision: {status.value} | Risk: {base_risk:.4f} | Target Speed: {recommended_speed:.2f}")
        
        return DecisionResult(
            action="ADJUST_SPEED",
            target_speed=recommended_speed,
            risk_score=base_risk,
            status=status,
            message=msg
        )

# --- Usage Example & Demonstration ---
if __name__ == "__main__":
    # 1. Setup Parameters
    params = OperationalParameters(
        max_risk_tolerance=0.05, # 5% risk threshold
        current_speed_ratio=1.0  # Currently at 100% speed
    )
    
    optimizer = IndustrialSafetyOptimizer(params)
    
    # 2. Simulate Sensor Data (Scenario: Machine overheating and vibration rising)
    print("\n--- Scenario A: Normal Operations ---")
    sensors_normal = [
        SensorReading("TEMP_01", 45.0, "C", 1678900000, 0.99),
        SensorReading("VIB_01", 0.02, "mm/s", 1678900000, 0.95)
    ]
    result_a = optimizer.optimize_pareto_efficiency(sensors_normal)
    print(f"Result: {result_a.status.value}, Speed: {result_a.target_speed:.2f}x")
    
    print("\n--- Scenario B: High Load (Approaching Red Line) ---")
    # Risk calculation will increase. Optimizer should reduce speed to maintain safety.
    sensors_danger = [
        SensorReading("TEMP_01", 92.0, "C", 1678900100, 0.99), # High temp
        SensorReading("VIB_01", 0.08, "mm/s", 1678900100, 0.90) # High vibration
    ]
    result_b = optimizer.optimize_pareto_efficiency(sensors_danger)
    print(f"Result: {result_b.status.value}, Speed: {result_b.target_speed:.2f}x")
    print(f"Message: {result_b.message}")
    
    print("\n--- Scenario C: Critical Failure Imminent ---")
    # Risk exceeds threshold even at low speeds
    sensors_critical = [
        SensorReading("TEMP_01", 110.0, "C", 1678900200, 0.99),
        SensorReading("VIB_01", 0.15, "mm/s", 1678900200, 0.80)
    ]
    result_c = optimizer.optimize_pareto_efficiency(sensors_critical)
    print(f"Result: {result_c.status.value}, Action: {result_c.action}")