"""
Module: dynamic_ecological_economic_monitor.py

Description:
    Constructs a 'Dynamic Ecological Niche Economy Monitoring System'.
    This system integrates the spatiotemporal dynamics of ecological niches 
    with economic marginal analysis. It predicts enterprise (species) survival 
    rates in specific markets (habitats) and calculates the optimal 
    'investment density' to prevent market involution caused by excessive 
    competition (competitive exclusion). The system simulates critical points 
    of system collapse when external resources (e.g., capital/rainfall) change 
    abruptly.

    Key Features:
    - Ecological Niche Modeling (Tilman's Resource Competition).
    - Economic Marginal Analysis (ROI vs. Competition Cost).
    - System Stability Analysis (Critical slowing down indicators).

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SystemParameters:
    """Defines the parameters for the ecological economic model."""
    growth_rate: float  # Intrinsic growth rate of the enterprise/species
    competition_coeff: float  # Alpha: Intraspecific competition intensity
    resource_efficiency: float  # Ability to convert resources to growth
    carrying_capacity_factor: float  # K factor relative to base resources
    mortality_rate: float  # Base exit rate of enterprises

class EcologicalEconomicMonitor:
    """
    A monitoring system combining ecological dynamics with economic constraints.
    """

    def __init__(self, initial_resources: float, params: SystemParameters, time_steps: int = 100):
        """
        Initialize the monitoring system.

        Args:
            initial_resources (float): Starting level of market resources/capital.
            params (SystemParameters): Biological and economic parameters.
            time_steps (int): Number of iterations for simulation.
        """
        self.resources = initial_resources
        self.params = params
        self.time_steps = time_steps
        self.history: Dict[str, List[float]] = {
            "population": [],
            "resources": [],
            "marginal_benefit": [],
            "stress_index": []
        }
        logger.info("System initialized with resources: %.2f", initial_resources)

    def _validate_inputs(self, current_population: float) -> None:
        """
        Validate input parameters and state variables.
        
        Args:
            current_population (float): Current number of enterprises.
            
        Raises:
            ValueError: If inputs are non-physical or negative.
        """
        if current_population < 0:
            raise ValueError("Population cannot be negative.")
        if self.resources < 0:
            raise ValueError("Resources cannot be negative.")
        if self.params.competition_coeff <= 0:
            raise ValueError("Competition coefficient must be positive.")
        logger.debug("Input validation passed.")

    def calculate_optimal_density(self, current_population: float) -> Tuple[float, float]:
        """
        Core Function 1: Calculate the optimal investment density and survival rate.
        
        Models the 'Competitive Exclusion Principle' to find the point where 
        marginal revenue equals marginal cost of competition.
        
        Args:
            current_population (float): Current number of competitors.
            
        Returns:
            Tuple[float, float]: 
                - optimal_density (float): The ideal number of enterprises the market can sustain.
                - survival_prob (float): Probability of system stability (0.0 to 1.0).
        """
        try:
            self._validate_inputs(current_population)
            
            # Logistic growth model derivative combined with resource consumption
            # dN/dt = rN(1 - N/K) - mN
            # Equilibrium N* = K(1 - m/r)
            
            K = self.resources * self.params.carrying_capacity_factor
            r = self.params.growth_rate
            m = self.params.mortality_rate
            
            if r <= m:
                logger.warning("Growth rate <= Mortality rate. System heading for extinction.")
                return 0.0, 0.0

            optimal_n = K * (1 - m / r)
            
            # Calculate stress based on how far current pop is from optimal
            # Using a Gaussian decay for survival probability
            sigma = K * 0.2  # Allowable variance
            stress = np.exp(-((current_population - optimal_n) ** 2) / (2 * sigma ** 2))
            
            survival_prob = max(0.0, min(1.0, stress))
            
            logger.info(f"Calculated Optimal Density: {optimal_n:.2f}, Survival Prob: {survival_prob:.2f}")
            return optimal_n, survival_prob

        except ValueError as ve:
            logger.error(f"Validation Error in density calculation: {ve}")
            return 0.0, 0.0
        except Exception as e:
            logger.critical(f"Unexpected error in density calculation: {e}", exc_info=True)
            raise

    def simulate_shock(self, shock_magnitude: float, shock_time: int) -> pd.DataFrame:
        """
        Core Function 2: Simulate system evolution under external resource shocks.
        
        Simulates the time evolution of the market ecosystem. Introduces a sudden
        change in resources (positive or negative) at a specific time step to 
        observe resilience and critical transitions.
        
        Args:
            shock_magnitude (float): Amount to add/subtract from resources (delta R).
            shock_time (int): Time step at which the shock occurs.
            
        Returns:
            pd.DataFrame: Time series data of Population, Resources, and Stability Metrics.
        """
        logger.info(f"Starting simulation for {self.time_steps} steps. Shock at t={shock_time}.")
        
        # Initialize state
        N = 10.0  # Initial population
        R = self.resources
        
        for t in range(self.time_steps):
            # Apply Shock
            if t == shock_time:
                logger.warning(f"RESOURCE SHOCK TRIGGERED at t={t}: {shock_magnitude}")
                R += shock_magnitude
                R = max(0, R) # Floor at 0

            # Calculate Dynamics
            try:
                # Resource regeneration (logistic) and consumption
                dR = 0.1 * R * (1 - R / 1000) - N * self.params.resource_efficiency * 0.1
                R += dR
                
                # Population dynamics
                K = R * self.params.carrying_capacity_factor
                dN = self.params.growth_rate * N * (1 - N / (K + 1e-9)) - self.params.mortality_rate * N
                
                # Prevent negative population
                N = max(0, N + dN)
                
                # Record history
                self.history["population"].append(N)
                self.history["resources"].append(R)
                
                # Calculate Marginal Benefit (derivative of growth approx)
                marginal = (dN / (N + 1e-9)) if N > 0 else 0
                self.history["marginal_benefit"].append(marginal)
                
                # Stress Index (Autocorrelation of recent population changes - indicator of critical slowing down)
                # Simplified: Variance of recent window
                if len(self.history["population"]) > 10:
                    window = np.diff(self.history["population"][-10:])
                    stress = np.std(window)
                    self.history["stress_index"].append(stress)
                else:
                    self.history["stress_index"].append(0.0)

            except Exception as e:
                logger.error(f"Simulation failed at step {t}: {e}")
                break

        return pd.DataFrame(self.history)

def analyze_critical_transitions(df: pd.DataFrame, threshold: float = 0.8) -> Dict[str, Union[bool, float]]:
    """
    Auxiliary Function: Analyze simulation results for signs of collapse.
    
    Monitors the 'Stress Index' (variance/autocorrelation) to detect 
    'Critical Slowing Down' (CSD), a hallmark of approaching a tipping point.
    
    Args:
        df (pd.DataFrame): Output from the simulation.
        threshold (float): Variance threshold to flag as 'Critical'.
        
    Returns:
        Dict containing status and max stress.
    """
    if df.empty or 'stress_index' not in df.columns:
        return {"status": "Error", "message": "Invalid data"}

    max_stress = df['stress_index'].max()
    is_critical = max_stress > threshold
    
    result = {
        "is_critical_state": bool(is_critical),
        "max_variance_stress": float(max_stress),
        "final_population": float(df['population'].iloc[-1]),
        "recommendation": ""
    }
    
    if is_critical:
        result["recommendation"] = "Warning: High variance detected. Market is losing resilience. Reduce exposure."
    else:
        result["recommendation"] = "System stable. Monitor resource levels."
        
    logger.info(f"Analysis Complete: Critical={is_critical}, MaxStress={max_stress:.4f}")
    return result

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. Setup Parameters
    # High growth, high competition
    params = SystemParameters(
        growth_rate=0.5,
        competition_coeff=0.2,
        resource_efficiency=0.8,
        carrying_capacity_factor=2.5,
        mortality_rate=0.1
    )
    
    # 2. Initialize Monitor
    monitor = EcologicalEconomicMonitor(initial_resources=100.0, params=params, time_steps=150)
    
    # 3. Check Optimal Density
    current_competitors = 50.0
    opt_density, surv_prob = monitor.calculate_optimal_density(current_competitors)
    print(f"Optimal Density for current state: {opt_density:.2f}")
    
    # 4. Run Simulation with a Negative Shock (Capital Drought)
    # Shock at t=50, removing 80% of resources
    sim_df = monitor.simulate_shock(shock_magnitude=-80.0, shock_time=50)
    
    # 5. Analyze Results
    analysis = analyze_critical_transitions(sim_df)
    
    print("\n--- Simulation Summary ---")
    print(f"Final Population: {analysis['final_population']:.2f}")
    print(f"System Criticality: {analysis['is_critical_state']}")
    print(f"Recommendation: {analysis['recommendation']}")