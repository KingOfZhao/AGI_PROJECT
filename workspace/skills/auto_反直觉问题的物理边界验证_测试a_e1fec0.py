"""
Module: auto_counter_intuitive_physics_validation
Description: AGI Skill for verifying physical boundaries of counter-intuitive problems.
             This module simulates real-world physics to validate non-obvious outcomes,
             ensuring the system relies on modeling rather than statistical retrieval.
Author: Senior Python Engineer (AGI Division)
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhysicsDomain(Enum):
    """Enumeration of supported physics domains for simulation."""
    MECHANICS = "mechanics"
    THERMODYNAMICS = "thermodynamics"
    FLUID_DYNAMICS = "fluid_dynamics"

@dataclass
class SimulationResult:
    """Data class representing the outcome of a physics simulation."""
    scenario_name: str
    is_counter_intuitive: bool
    validation_passed: bool
    observed_value: float
    expected_intuition: float
    deviation_percent: float
    details: Dict[str, float]

def _validate_input_params(params: Dict[str, float], required_keys: List[str]) -> None:
    """
    Validates that all required parameters are present and physical values are non-negative.
    
    Args:
        params: Dictionary of input parameters.
        required_keys: List of keys that must exist in params.
        
    Raises:
        ValueError: If keys are missing or values are invalid.
    """
    missing = [key for key in required_keys if key not in params]
    if missing:
        error_msg = f"Missing required simulation parameters: {missing}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    for key, val in params.items():
        if not isinstance(val, (int, float)):
            raise TypeError(f"Parameter '{key}' must be numeric, got {type(val)}.")
        if val < 0 and key not in ['temperature_delta']:  # Example exception
            logger.warning(f"Parameter '{key}' has negative value {val}, checking physical plausibility.")

def calculate_chain_value_with_rust(
    base_mass: float,
    rust_percentage: float,
    market_price_steel: float,
    market_price_iron_ore: float,
    structural_integrity_factor: float = 0.8
) -> SimulationResult:
    """
    Simulates the value and structural integrity of a rusty chain to answer:
    'Does a rusty chain have more value?' (Counter-intuitive volume expansion vs. structural loss).
    
    Hypothesis: Rust (Fe2O3) has a larger volume than Fe (Pilling-Bedworth ratio ~2.1),
    seemingly adding 'material', but it reduces structural integrity and changes material value.
    
    Args:
        base_mass: Mass of the chain in kg before rusting.
        rust_percentage: Percentage of the surface area affected by rust (0.0 to 1.0).
        market_price_steel: Price per kg of functional steel.
        market_price_iron_ore: Price per kg of raw ore (rust equivalent).
        structural_integrity_factor: Multiplier for value based on remaining strength.
        
    Returns:
        SimulationResult: Detailed result of the simulation.
        
    Example:
        >>> result = calculate_chain_value_with_rust(10.0, 0.5, 5.0, 0.1)
        >>> print(result.validation_passed)
    """
    logger.info(f"Starting Rust Value Simulation for {base_mass}kg chain...")
    
    # Input Validation
    params = {
        'base_mass': base_mass, 
        'rust_percentage': rust_percentage,
        'market_price_steel': market_price_steel,
        'market_price_iron_ore': market_price_iron_ore
    }
    try:
        _validate_input_params(params, list(params.keys()))
        if not 0 <= rust_percentage <= 1:
            raise ValueError("Rust percentage must be between 0 and 1.")
    except (ValueError, TypeError) as e:
        logger.critical(f"Input validation failed: {e}")
        raise

    # Physical Constants
    # Pilling-Bedworth Ratio: Volume of oxide / Volume of metal
    # For Iron -> Iron Oxide (Fe2O3), ratio is approx 2.1
    PB_RATIO = 2.1
    DENSITY_STEEL = 7850  # kg/m^3
    
    # Simulation Logic
    # 1. Calculate effective mass distribution (simplified model)
    # Assume the rusted portion converts to oxide but keeps volume expansion
    rusted_mass = base_mass * rust_percentage
    intact_mass = base_mass * (1 - rust_percentage)
    
    # 2. Calculate Volume changes
    # Volume of the portion that became rust (originally metal)
    vol_metal_rusted = rusted_mass / DENSITY_STEEL
    # Volume of the rust created
    vol_rust = vol_metal_rusted * PB_RATIO
    
    # 3. Value Calculation
    # Functional value (intact steel)
    value_functional = intact_mass * market_price_steel * structural_integrity_factor
    
    # Scrap/Oxide value (rusted part)
    # Rust is effectively ore, heavily devalued compared to processed steel
    value_rust = (rusted_mass * 1.1) * market_price_iron_ore  # 1.1 accounts for oxygen mass gain
    
    total_value = value_functional + value_rust
    
    # Intuition Comparison
    # Intuition: "More material volume = more value"
    # Real: "Structural loss = massive value drop"
    intuition_value = base_mass * market_price_steel * (1 + (vol_rust - vol_metal_rusted) * 100) # Naive volume bonus
    
    deviation = ((total_value - intuition_value) / intuition_value) * 100 if intuition_value != 0 else 0
    
    logger.info(f"Sim Value: {total_value:.2f}, Intuition Value: {intuition_value:.2f}, Deviation: {deviation:.2f}%")
    
    return SimulationResult(
        scenario_name="Rusty Chain Value Paradox",
        is_counter_intuitive=True,
        validation_passed=(total_value < intuition_value),  # Validating physics usually lowers value
        observed_value=total_value,
        expected_intuition=intuition_value,
        deviation_percent=deviation,
        details={
            "oxide_volume_increase": vol_rust - vol_metal_rusted,
            "structural_loss_kg": rusted_mass
        }
    )

def simulate_bucket_water_rotation(
    rope_length: float,
    rotation_speed_rpm: float,
    water_mass: float,
    bucket_holes_area: float = 0.0
) -> SimulationResult:
    """
    Simulates the 'Spinning Bucket' problem.
    Counter-intuitive question: "If I spin a bucket of water upside down, why doesn't the water fall out?"
    
    Validates if Centrifugal Force > Gravitational Force.
    
    Args:
        rope_length: Length of the rope in meters (radius of rotation).
        rotation_speed_rpm: Rotations per minute.
        water_mass: Mass of water in kg.
        bucket_holes_area: Total area of holes in m^2 (for boundary checks).
        
    Returns:
        SimulationResult: indicating if water stays in the bucket.
    """
    logger.info("Simulating Spinning Bucket Physics...")
    
    required = ['rope_length', 'rotation_speed_rpm', 'water_mass']
    loc_vars = locals()
    params = {k: loc_vars[k] for k in required}
    params['bucket_holes_area'] = bucket_holes_area
    
    _validate_input_params(params, required)
    
    if rope_length <= 0:
        raise ValueError("Rope length must be positive.")

    # Physics Constants
    G = 9.81  # m/s^2
    
    # Conversion
    omega = (rotation_speed_rpm * 2 * math.pi) / 60  # rad/s
    
    # Forces
    # F_gravity = m * g
    # F_centrifugal = m * omega^2 * r
    
    # Accelerations (mass cancels out for checking condition, but we keep it for force calc)
    centripetal_acc = (omega ** 2) * rope_length
    
    # Boundary Check: Critical Velocity
    # Water stays if Centripetal Acc >= Gravity
    does_water_stay = centripetal_acc >= G
    
    # Boundary Check: Bucket Integrity (Holes)
    # If holes exist, water leaks due to pressure. 
    # Pressure at bottom P = rho * g * h (static) vs dynamic pressure.
    # Simplified: If holes exist, we lose water unless spinning extremely fast (spraying).
    # We assume 'staying in' means primarily 'not falling due to gravity'.
    
    leakage_factor = 0.0
    if bucket_holes_area > 0:
        # Simple heuristic: holes reduce effective water mass over time, 
        # but we check instantaneous state.
        leakage_factor = bucket_holes_area * 1000 # Arbitrary impact factor
    
    intuition_check = rotation_speed_rpm < 20 # Intuition might think "slow spin = fall"
    
    return SimulationResult(
        scenario_name="Spinning Bucket Paradox",
        is_counter_intuitive=intuition_check and does_water_stay,
        validation_passed=does_water_stay,
        observed_value=centripetal_acc,
        expected_intuition=G,
        deviation_percent=((centripetal_acc - G) / G) * 100,
        details={
            "angular_velocity_rad_s": omega,
            "tension_force": water_mass * (centripetal_acc + G) # At bottom of loop
        }
    )

if __name__ == "__main__":
    # Usage Example
    print("--- AGI Skill: Physics Boundary Verification ---")
    
    try:
        # Test 1: Rusty Chain
        res_chain = calculate_chain_value_with_rust(
            base_mass=50.0,
            rust_percentage=0.8, # Heavily rusted
            market_price_steel=0.8,
            market_price_iron_ore=0.05
        )
        print(f"Scenario: {res_chain.scenario_name}")
        print(f"Physics Validated: {res_chain.validation_passed}")
        print(f"Deviation from Intuition: {res_chain.deviation_percent:.2f}%")
        
        # Test 2: Spinning Bucket
        res_bucket = simulate_bucket_water_rotation(
            rope_length=1.0,
            rotation_speed_rpm=60, # 1 rev per sec
            water_mass=2.0
        )
        print(f"\nScenario: {res_bucket.scenario_name}")
        print(f"Water Stays (Physics): {res_bucket.validation_passed}")
        print(f"Centripetal Acc: {res_bucket.observed_value:.2f} m/s^2 vs Gravity {res_bucket.expected_intuition:.2f}")

    except Exception as e:
        logger.error(f"Simulation failed: {e}")