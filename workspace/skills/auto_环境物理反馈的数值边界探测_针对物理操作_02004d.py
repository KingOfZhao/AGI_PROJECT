"""
SKILL: auto_环境物理反馈的数值边界探测_针对物理操作_02004d

Description:
    This module implements an automated boundary detection system for robotic skills 
    in physics simulations. It automatically generates 'edge test cases' to determine 
    the operational limits (confidence intervals) of physics-based skills like grasping, 
    pushing, or lifting objects.

    For example, given a 'grasp' skill, it generates a gradient of object weights 
    (1kg, 5kg, 10kg...) or friction coefficients and uses the simulation environment's 
    feedback to determine the skill's success rate and boundaries.

Domain: robotics_simulation
Author: AGI System Core
Version: 2.0.4d
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BoundaryDetector")

class BoundaryDirection(Enum):
    """Enumeration for boundary search direction."""
    INCREMENTAL = 1
    DECREMENTAL = -1

@dataclass
class PhysicsParameter:
    """
    Represents a physics parameter to be tested.
    
    Attributes:
        name: Name of the parameter (e.g., 'mass', 'friction').
        min_val: Minimum allowable value (physical limit).
        max_val: Maximum allowable value (physical limit).
        step: Step size for gradient generation.
        unit: Unit of measurement (optional).
        current_val: Current value during testing.
    """
    name: str
    min_val: float
    max_val: float
    step: float
    unit: str = ""
    current_val: float = 0.0

    def __post_init__(self):
        """Validate data after initialization."""
        if self.min_val >= self.max_val:
            raise ValueError(f"min_val ({self.min_val}) must be less than max_val ({self.max_val})")
        if self.step <= 0:
            raise ValueError(f"Step ({self.step}) must be positive")
        self.current_val = self.min_val

@dataclass
class ExperimentResult:
    """
    Represents the result of a single simulation experiment.
    
    Attributes:
        parameter_name: Name of the tested parameter.
        value: The value tested.
        success: Whether the skill execution was successful.
        feedback_data: Raw data dictionary returned from the environment.
        execution_time: Time taken to execute the simulation.
        error_msg: Error message if any occurred.
    """
    parameter_name: str
    value: float
    success: bool
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_msg: Optional[str] = None

class PhysicsSkillTestbed:
    """
    A mock simulation environment interface for demonstration purposes.
    In a real scenario, this would interface with engines like PyBullet, MuJoCo, or Gazebo.
    """
    
    def execute_skill(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates the execution of a skill with specific physics properties.
        
        Args:
            config: Dictionary containing 'target_param' and 'value'.
            
        Returns:
            Dictionary containing 'success' (bool) and 'metrics' (dict).
        """
        # Simulate processing time
        time.sleep(0.01)
        
        param = config.get('target_param')
        val = config.get('value')
        
        # Mock physics logic: Success probability decreases as value increases
        # Let's assume a "Grasping" scenario where weight affects success.
        # Base success rate is 100%, drops as mass increases.
        # Adding some noise to simulate real-world stochasticity.
        
        if param == 'mass':
            # Simulating a gripper with a strength limit around 12kg
            limit = 12.0
            noise = random.uniform(-0.5, 0.5)
            effective_limit = limit + noise
            
            if val < 5.0:
                success = True
            elif val < effective_limit:
                # Probabilistic failure zone
                success = random.random() > ((val - 5.0) / (effective_limit - 5.0))
            else:
                success = False
                
            return {
                'success': success,
                'metrics': {'grip_force_required': val * 9.8 * 0.8}
            }
            
        elif param == 'friction':
            # High friction usually helps grasping, low friction causes slipping
            # Assume failure below 0.2
            success = val >= 0.25 or (val >= 0.15 and random.random() > 0.5)
            return {'success': success, 'metrics': {'slip_detected': not success}}
            
        return {'success': False, 'metrics': {}}

class BoundaryExplorer:
    """
    Core class for exploring numerical boundaries of physics-based skills.
    """
    
    def __init__(self, env_interface: PhysicsSkillTestbed):
        """
        Initialize the explorer.
        
        Args:
            env_interface: An instance of the simulation environment interface.
        """
        self.env = env_interface
        logger.info("BoundaryExplorer initialized.")

    def _validate_parameter_scope(self, param: PhysicsParameter) -> bool:
        """
        Helper: Validate if the parameter configuration is valid for testing.
        
        Args:
            param: PhysicsParameter object.
            
        Returns:
            bool: True if valid.
        """
        if param.step > (param.max_val - param.min_val):
            logger.error("Step size is larger than the parameter range.")
            return False
        return True

    def _log_experiment(self, result: ExperimentResult) -> None:
        """
        Helper: Log the result of an experiment.
        """
        status = "SUCCESS" if result.success else "FAILURE"
        logger.debug(f"Test [{result.parameter_name}={result.value:.2f}]: {status}")

    def probe_parameter_boundary(
        self,
        skill_func: Callable[[Dict], Dict],
        target_param: PhysicsParameter,
        success_threshold: float = 0.95,
        sample_size: int = 3
    ) -> Dict[str, Any]:
        """
        Core Function 1: Probes a specific parameter dimension to find the success boundary.
        
        This function performs a sweep or binary-search-like approach to find where
        the skill transitions from mostly successful to mostly failing.
        
        Args:
            skill_func: The function representing the skill logic (passed by controller).
            target_param: The PhysicsParameter object defining the search space.
            success_threshold: The probability threshold (0.0 to 1.0) to consider a point 'stable'.
            sample_size: Number of times to repeat a test to account for stochasticity.
            
        Returns:
            A dictionary containing:
            - 'confidence_interval': Tuple (lower_bound, upper_bound)
            - 'failure_point': Approximate value where success drops below threshold
            - 'raw_data': List of ExperimentResult objects
            
        Example:
            >>> testbed = PhysicsSkillTestbed()
            >>> explorer = BoundaryExplorer(testbed)
            >>> mass_param = PhysicsParameter("mass", 1.0, 20.0, 1.0)
            >>> results = explorer.probe_parameter_boundary(testbed.execute_skill, mass_param)
        """
        if not self._validate_parameter_scope(target_param):
            return {"error": "Invalid parameter scope"}

        logger.info(f"Starting boundary probe for: {target_param.name} "
                    f"Range: [{target_param.min_val}, {target_param.max_val}]")

        results: List[ExperimentResult] = []
        current_val = target_param.min_val
        
        # 1. Coarse Sweep
        while current_val <= target_param.max_val:
            successes = 0
            
            # Monte Carlo sampling for stochastic environments
            for _ in range(sample_size):
                start_time = time.time()
                
                # Prepare configuration
                config = {
                    'target_param': target_param.name,
                    'value': current_val
                }
                
                try:
                    # Execute skill in simulation
                    sim_feedback = skill_func(config)
                    is_success = sim_feedback.get('success', False)
                    
                    res = ExperimentResult(
                        parameter_name=target_param.name,
                        value=current_val,
                        success=is_success,
                        feedback_data=sim_feedback,
                        execution_time=time.time() - start_time
                    )
                    results.append(res)
                    if is_success:
                        successes += 1
                        
                except Exception as e:
                    logger.error(f"Simulation crash at {target_param.name}={current_val}: {e}")
                    results.append(ExperimentResult(
                        parameter_name=target_param.name,
                        value=current_val,
                        success=False,
                        error_msg=str(e)
                    ))
                    
                self._log_experiment(results[-1])

            # Check if we have crossed the confidence threshold
            success_rate = successes / sample_size
            if success_rate < success_threshold:
                # Found a potential boundary region
                logger.info(f"Boundary detected near {current_val}. Success rate: {success_rate:.2f}")
                break
                
            current_val += target_param.step
            
        # 2. Analyze Results to find the 'Safe Operating Limit'
        # For simplicity, we find the highest value with 100% success rate
        stable_max = target_param.min_val
        for res in results:
            if res.success:
                stable_max = max(stable_max, res.value)
            else:
                # Stop at first failure for conservative estimation
                break
                
        return {
            "parameter": target_param.name,
            "safe_upper_limit": stable_max,
            "tested_upper_limit": current_val,
            "data_points": len(results),
            "details": results
        }

    def analyze_skill_sensitivity(
        self,
        skill_func: Callable[[Dict], Dict],
        params_list: List[PhysicsParameter]
    ) -> Dict[str, Dict]:
        """
        Core Function 2: Analyzes sensitivity of a skill across multiple physics dimensions.
        
        It iterates over a list of parameters and compiles a 'Skill Fingerprint' 
        showing which dimensions are bottlenecks.
        
        Args:
            skill_func: The skill execution function.
            params_list: List of PhysicsParameter objects to test.
            
        Returns:
            A dictionary mapping parameter names to their boundary analysis results.
            
        Example:
            >>> params = [
            ...     PhysicsParameter("mass", 1.0, 15.0, 1.0),
            ...     PhysicsParameter("friction", 0.1, 1.0, 0.1)
            ... ]
            >>> sensitivity = explorer.analyze_skill_sensitivity(testbed.execute_skill, params)
        """
        logger.info(f"Starting multi-dimensional sensitivity analysis for {len(params_list)} parameters.")
        full_report = {}
        
        for param in params_list:
            logger.info(f"Testing dimension: {param.name}")
            try:
                boundary_data = self.probe_parameter_boundary(
                    skill_func=skill_func,
                    target_param=param
                )
                full_report[param.name] = boundary_data
            except Exception as e:
                logger.critical(f"Failed to analyze parameter {param.name}: {e}")
                full_report[param.name] = {"error": str(e)}
                
        return full_report

# ================= Usage Example =================
if __name__ == "__main__":
    # 1. Setup the environment and explorer
    simulation_env = PhysicsSkillTestbed()
    explorer = BoundaryExplorer(simulation_env)
    
    # 2. Define parameters to test
    # We want to find the limit of the 'grasp' skill regarding object mass
    mass_param = PhysicsParameter(
        name="mass",
        min_val=1.0,
        max_val=15.0,
        step=1.0,
        unit="kg"
    )
    
    print(f"--- Testing Single Parameter: {mass_param.name} ---")
    
    # 3. Run the boundary probe
    report = explorer.probe_parameter_boundary(
        skill_func=simulation_env.execute_skill,
        target_param=mass_param,
        sample_size=2 # Low sample size for speed in this example
    )
    
    print(f"Analysis Complete.")
    print(f"Safe Upper Limit: {report['safe_upper_limit']} kg")
    print(f"First Failure Detected at: {report['tested_upper_limit']} kg")
    
    # 4. Multi-parameter sensitivity analysis
    print("\n--- Multi-Dimensional Analysis ---")
    friction_param = PhysicsParameter("friction", 0.1, 1.0, 0.1)
    
    sensitivity_report = explorer.analyze_skill_sensitivity(
        skill_func=simulation_env.execute_skill,
        params_list=[mass_param, friction_param]
    )
    
    for param_name, result in sensitivity_report.items():
        safe_limit = result.get('safe_upper_limit', 'N/A')
        print(f"Parameter: {param_name} | Safe Limit: {safe_limit}")