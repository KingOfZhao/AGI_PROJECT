"""
Module Name: embodied_compute_cost_model
Description: Implements an 'Embodied Computational Cost Model' (ECCM) for AGI systems.
             This module allows an AI system to dynamically adjust its inference depth
             (and thus computational load) based on real-time hardware states such as
             temperature, battery level, and CPU/GPU load.

Author: Senior Python Engineer
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InferenceDepth(Enum):
    """Enumeration for standardized inference depth levels."""
    MINIMAL = 1
    STANDARD = 2
    DEEP = 3
    MAXIMUM = 4

@dataclass
class HardwareState:
    """
    Represents the current state of the hardware environment.
    
    Attributes:
        temperature (float): Current chip temperature in Celsius.
        battery_level (float): Current battery percentage (0-100). None if plugged in.
        cpu_load (float): Current CPU utilization percentage (0-100).
        gpu_load (float): Current GPU utilization percentage (0-100).
        is_charging (bool): Whether the device is connected to power.
    """
    temperature: float
    battery_level: Optional[float]
    cpu_load: float
    gpu_load: float
    is_charging: bool = False

    def __post_init__(self):
        """Validate data ranges after initialization."""
        if not (0 <= self.cpu_load <= 100):
            raise ValueError(f"CPU load must be between 0 and 100, got {self.cpu_load}")
        if not (0 <= self.gpu_load <= 100):
            raise ValueError(f"GPU load must be between 0 and 100, got {self.gpu_load}")
        if self.battery_level is not None and not (0 <= self.battery_level <= 100):
            raise ValueError(f"Battery level must be between 0 and 100, got {self.battery_level}")

class EmbodiedCostModel:
    """
    Core class for calculating computational costs and determining optimal inference depth.
    
    This model uses a utility function to balance performance requirements against
    hardware constraints to prevent overheating or battery drain.
    """

    def __init__(self, 
                 temp_threshold: float = 80.0, 
                 low_battery_threshold: float = 20.0,
                 load_threshold: float = 90.0):
        """
        Initialize the cost model with hardware constraints.

        Args:
            temp_threshold (float): Maximum safe temperature in Celsius.
            low_battery_threshold (float): Battery % considered critical.
            load_threshold (float): System load % considered max capacity.
        """
        self.temp_threshold = temp_threshold
        self.low_battery_threshold = low_battery_threshold
        self.load_threshold = load_threshold
        logger.info("EmbodiedCostModel initialized with thresholds: Temp=%s, Batt=%s, Load=%s",
                    temp_threshold, low_battery_threshold, load_threshold)

    def _normalize_metric(self, value: float, max_value: float, is_critical: bool = False) -> float:
        """
        Helper function to normalize a metric to a 0.0-1.0 scale cost.
        
        Args:
            value (float): The current value.
            max_value (float): The maximum/reference value.
            is_critical (bool): If True, cost scales exponentially near the limit.
        
        Returns:
            float: A normalized cost factor (0.0 to 1.0+).
        """
        if max_value == 0:
            return 0.0
        
        ratio = value / max_value
        
        if is_critical:
            # Exponential penalty as we approach the limit
            return math.pow(ratio, 2)
        return min(ratio, 1.0)

    def calculate_embodied_cost(self, state: HardwareState) -> float:
        """
        Calculates a composite 'Embodied Cost' score representing system stress.
        
        The score ranges from 0.0 (Low stress, plenty of resources) to 1.0+ (High stress).
        
        Args:
            state (HardwareState): The current hardware telemetry.
            
        Returns:
            float: The calculated cost score.
        
        Raises:
            TypeError: If state is not a HardwareState instance.
        """
        if not isinstance(state, HardwareState):
            logger.error("Invalid input type for calculate_embodied_cost")
            raise TypeError("Input must be a HardwareState instance")

        logger.debug("Calculating cost for state: %s", state)

        # 1. Thermal Cost (High priority)
        thermal_cost = self._normalize_metric(state.temperature, self.temp_threshold, is_critical=True)

        # 2. Energy Cost (Context dependent)
        energy_cost = 0.0
        if not state.is_charging and state.battery_level is not None:
            # Invert battery level: lower battery = higher cost
            # Map 100% -> 0.0, 0% -> 1.0
            energy_cost = self._normalize_metric(100 - state.battery_level, 100)
            if state.battery_level < self.low_battery_threshold:
                energy_cost *= 1.5  # Penalty for critical battery

        # 3. Load Cost
        avg_load = (state.cpu_load + state.gpu_load) / 2
        load_cost = self._normalize_metric(avg_load, self.load_threshold)

        # Weighted sum (Thermal is usually most critical for embodied agents to prevent burns/shutdown)
        total_cost = (thermal_cost * 0.5) + (energy_cost * 0.3) + (load_cost * 0.2)
        
        logger.info(f"Calculated Embodied Cost: {total_cost:.4f} (Therm: {thermal_cost:.2f}, Ener: {energy_cost:.2f}, Load: {load_cost:.2f})")
        return total_cost

    def determine_inference_depth(self, state: HardwareState) -> InferenceDepth:
        """
        Determines the optimal inference depth based on current hardware state.
        
        Args:
            state (HardwareState): Current hardware telemetry.
            
        Returns:
            InferenceDepth: The recommended operational depth level.
        """
        try:
            cost = self.calculate_embodied_cost(state)
        except Exception as e:
            logger.exception("Failed to calculate cost, defaulting to STANDARD depth.")
            return InferenceDepth.STANDARD

        # Decision Logic based on Cost Score
        if cost > 0.9:
            # System is heavily constrained
            recommended_depth = InferenceDepth.MINIMAL
            reason = "High system stress"
        elif cost > 0.6:
            recommended_depth = InferenceDepth.STANDARD
            reason = "Moderate system stress"
        elif cost > 0.3:
            recommended_depth = InferenceDepth.DEEP
            reason = "Low system stress"
        else:
            recommended_depth = InferenceDepth.MAXIMUM
            reason = "Optimal system conditions"

        logger.info(f"Recommended Depth: {recommended_depth.name}. Reason: {reason} (Cost: {cost:.2f})")
        return recommended_depth

def run_simulation():
    """
    Simulation function demonstrating the module's usage.
    """
    print("--- Starting Embodied Compute Cost Model Simulation ---")
    
    # Initialize Model
    model = EmbodiedCostModel(temp_threshold=85.0, low_battery_threshold=15.0)

    # Scenario 1: Ideal conditions
    state_ideal = HardwareState(temperature=40.0, battery_level=95.0, cpu_load=10.0, gpu_load=5.0, is_charging=True)
    depth_1 = model.determine_inference_depth(state_ideal)
    print(f"Scenario 1 (Ideal): {depth_1.name}")

    # Scenario 2: High Temperature
    state_hot = HardwareState(temperature=82.0, battery_level=80.0, cpu_load=60.0, gpu_load=50.0, is_charging=True)
    depth_2 = model.determine_inference_depth(state_hot)
    print(f"Scenario 2 (Hot): {depth_2.name}")

    # Scenario 3: Low Battery & High Load
    state_stressed = HardwareState(temperature=65.0, battery_level=10.0, cpu_load=95.0, gpu_load=90.0, is_charging=False)
    depth_3 = model.determine_inference_depth(state_stressed)
    print(f"Scenario 3 (Stressed): {depth_3.name}")

if __name__ == "__main__":
    run_simulation()