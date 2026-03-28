"""
Module: adaptive_metabolic_flow_middleware
Description: Implements an 'Adaptive Metabolic Flow Control Middleware'.
This system mimics biological metabolic switching (e.g., anaerobic respiration under hypoxia).
Unlike traditional 'all-or-nothing' rate limiters, this middleware allows the system to
survive extreme loads by degrading Quality of Service (QoS) and returning approximate results,
akin to muscle cells producing lactate to maintain function. It tracks 'oxygen debt' for
eventual consistency recovery once the load subsides.

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import time
import random
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MetabolicMiddleware")


class MetabolicState(Enum):
    """Enumeration of system metabolic states."""
    AEROBIC = 1      # Normal operation, full resources available
    HYPOXIC = 2      # Resources are scarce, switching to survival mode
    ANAEROBIC = 3    # Extreme load, calculating approximate results, accumulating debt


@dataclass
class SystemProfile:
    """Monitors the 'physiological' state of the system."""
    max_capacity: int = 1000
    current_load: int = 0
    oxygen_debt: int = 0  # Represents unprocessed or approximated data backlog
    history: deque = field(default_factory=lambda: deque(maxlen=10))

    def update_load(self, current_requests: int) -> None:
        """Updates current load and history."""
        self.current_load = current_requests
        self.history.append(current_requests)

    def get_stress_level(self) -> float:
        """Calculates stress level (0.0 to 1.0+)."""
        if self.max_capacity == 0:
            return 1.0
        return self.current_load / self.max_capacity


def _generate_approximate_signature(data: Any) -> str:
    """
    Helper function to generate a unique signature for the 'oxygen debt'.
    Used to track the specific request that was handled approximately.
    """
    raw_str = str(data) + str(time.time())
    return hashlib.md5(raw_str.encode()).hexdigest()


def _repay_debt_logic(debt_id: str, approximate_result: Any) -> bool:
    """
    Helper function to simulate the background process of fixing consistency.
    In a real scenario, this would re-run heavy computations or update databases.
    """
    # Simulate processing time
    time.sleep(0.01)
    # Simulate success
    logger.info(f"[Recovery] Repaying oxygen debt for ID: {debt_id}")
    return True


class MetabolicMiddleware:
    """
    Middleware that regulates data flow based on system stress levels.
    It switches between precise calculation and approximate survival modes.
    """

    def __init__(self, profile: SystemProfile, thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize the middleware.

        Args:
            profile (SystemProfile): The system resource profile.
            thresholds (dict): Configuration for state transitions.
                               Keys: 'hypoxic', 'anaerobic'. Values: 0.0-1.0.
        """
        self.profile = profile
        self.thresholds = thresholds or {'hypoxic': 0.7, 'anaerobic': 0.9}
        self.state = MetabolicState.AEROBIC
        logger.info("Metabolic Middleware initialized with state: AEROBIC")

    def _evaluate_state(self) -> MetabolicState:
        """
        Core Logic 1: Evaluates current system load and determines the metabolic state.
        Mimics the cell detecting oxygen levels.
        """
        stress = self.profile.get_stress_level()
        
        if stress >= self.thresholds['anaerobic']:
            new_state = MetabolicState.ANAEROBIC
        elif stress >= self.thresholds['hypoxic']:
            new_state = MetabolicState.HYPOXIC
        else:
            new_state = MetabolicState.AEROBIC

        if new_state != self.state:
            logger.warning(f"Metabolic State Change: {self.state.name} -> {new_state.name} (Stress: {stress:.2f})")
            self.state = new_state
        
        return self.state

    def process_request(self, data: Dict[str, Any], precise_processor: Callable, fast_processor: Callable) -> Tuple[Any, str]:
        """
        Core Logic 2: Intercepts requests and routes them based on metabolic state.
        
        Args:
            data (dict): Input data payload.
            precise_processor (Callable): Function for high-quality, resource-heavy processing.
            fast_processor (Callable): Function for low-quality, resource-light processing.
            
        Returns:
            Tuple[Any, str]: The result and the status ('precise', 'approximate', 'rejected').
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")

        current_state = self._evaluate_state()

        if current_state == MetabolicState.AEROBIC:
            # Normal operation: Full precision
            return precise_processor(data), "precise"

        elif current_state == MetabolicState.HYPOXIC:
            # Warning state: Try to process precisely, but prioritize speed
            # If the data is complex, we might switch to fast processing selectively
            if len(str(data)) > 100:  # Heuristic for complexity
                logger.info("Hypoxic state: Handling complex data with fast processor.")
                result = fast_processor(data)
                return result, "approximate"
            else:
                return precise_processor(data), "precise"

        elif current_state == MetabolicState.ANAEROBIC:
            # Survival state: Approximate results only, accumulate debt
            logger.warning("Anaerobic state: Generating approximate result to survive.")
            
            # Generate a 'survival' result
            result = fast_processor(data)
            
            # Record the 'Oxygen Debt'
            debt_id = _generate_approximate_signature(data)
            self.profile.oxygen_debt += 1
            
            # In a real system, we would push (debt_id, data) to a queue for later processing
            return result, "approximate"
        
        return None, "error"

    def repay_all_debts(self) -> int:
        """
        Initiates the recovery process to clear oxygen debt.
        Should be called when system load is low.
        """
        count = 0
        while self.profile.oxygen_debt > 0:
            self.profile.oxygen_debt -= 1
            # Simulate repayment
            _repay_debt_logic(f"debt_{random.randint(1000, 9999)}", None)
            count += 1
        logger.info(f"Recovery complete. Repaid {count} debts.")
        return count


def precise_processing_engine(data: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates a heavy computation (e.g., complex SQL joins, ML inference)."""
    time.sleep(0.1)  # Simulate CPU usage
    return {"result": f"High Precision Analysis of {data.get('id')}", "accuracy": 0.99}

def survival_processing_engine(data: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates a fast, approximate computation (e.g., cache lookup, heuristic)."""
    time.sleep(0.01)  # Very fast
    return {"result": f"Quick Estimate for {data.get('id')}", "accuracy": 0.75}


if __name__ == "__main__":
    # Example Usage
    system_profile = SystemProfile(max_capacity=100)
    middleware = MetabolicMiddleware(system_profile)

    print("\n--- Simulating Load Scenarios ---")
    
    # 1. Normal Load
    print("\n[Scenario 1: Normal Load]")
    system_profile.update_load(50) # 50% load
    payload = {"id": "req_001", "value": 100}
    res, status = middleware.process_request(payload, precise_processing_engine, survival_processing_engine)
    print(f"Result: {res}, Status: {status}")

    # 2. High Load (Hypoxic)
    print("\n[Scenario 2: High Load (Hypoxic)]")
    system_profile.update_load(75) # 75% load
    payload = {"id": "req_002", "value": "x" * 150} # Large payload triggers fast path
    res, status = middleware.process_request(payload, precise_processing_engine, survival_processing_engine)
    print(f"Result: {res}, Status: {status}")

    # 3. Extreme Load (Anaerobic)
    print("\n[Scenario 3: Extreme Load (Anaerobic)]")
    system_profile.update_load(95) # 95% load
    payload = {"id": "req_003", "value": 500}
    res, status = middleware.process_request(payload, precise_processing_engine, survival_processing_engine)
    print(f"Result: {res}, Status: {status}")
    print(f"Current Oxygen Debt: {system_profile.oxygen_debt}")

    # 4. Recovery
    print("\n[Scenario 4: Recovery]")
    system_profile.update_load(10) # Load drops
    middleware.repay_all_debts()