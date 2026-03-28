"""
Cross-Domain Knowledge Mapping Module: High Concurrency to Parallel Manufacturing

This module implements the 'Left-Right Cross-Domain Overlap' methodology to map 
high-concurrency solutions from the Internet domain to multi-station parallel 
processing problems in the industrial domain.

Core Concept:
    Internet Domain                      Industrial Domain
    ----------------                     -----------------
    High Concurrency       >>>           Multi-Station Parallel Processing
    Request Scheduling     >>>           Material/Task Scheduling
    Server Cluster         >>>           Workstation Cluster
    Queue Theory Model     >>>           Queue Theory Model (Isomorphism)
    
Mathematical Isomorphism:
    - λ (Arrival Rate): User requests/sec ≈ Material units/time_interval
    - μ (Service Rate): Requests handled/sec ≈ Workstation throughput/time_interval
    - W (Wait Time): Latency in queue ≈ Buffer wait time before processing
    - ρ (Utilization): Server load ≈ Machine utilization rate

Validation Logic:
    The module verifies if the mapped solution maintains stability 
    (Utilization < 1) and minimizes Wait Time (W).
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DomainMappingError(Exception):
    """Custom exception for errors during domain mapping."""
    pass


@dataclass
class InternetNode:
    """Represents a knowledge node from the Internet/Software domain.
    
    Attributes:
        arrival_rate: Request arrival rate (lambda, req/s).
        service_rate: Processing service rate (mu, req/s).
        num_servers: Number of parallel servers (threads/pods).
    """
    arrival_rate: float
    service_rate: float
    num_servers: int = 1

    def __post_init__(self):
        if self.arrival_rate <= 0 or self.service_rate <= 0:
            raise ValueError("Arrival and Service rates must be positive.")
        if self.num_servers < 1:
            raise ValueError("Number of servers must be at least 1.")


@dataclass
class IndustrialNode:
    """Represents a target node in the Industrial/Manufacturing domain.
    
    Attributes:
        material_input_rate: Rate of materials entering the buffer (units/min).
        processing_rate: Speed of the workstation (units/min).
        num_stations: Number of parallel workstations.
        buffer_size: Maximum capacity of the waiting buffer (0 for infinite).
    """
    material_input_rate: float = 0.0
    processing_rate: float = 0.0
    num_stations: int = 1
    buffer_size: int = 0  # 0 implies infinite buffer
    is_stable: bool = False
    avg_wait_time: float = 0.0


def calculate_mm1_metrics(lambda_rate: float, mu_rate: float) -> Dict[str, float]:
    """Helper: Calculate core metrics for an M/M/1 queue model.
    
    Args:
        lambda_rate: Arrival rate.
        mu_rate: Service rate.
        
    Returns:
        Dictionary containing utilization (rho) and average wait time (W).
    """
    if mu_rate <= 0:
        raise DomainMappingError("Service rate must be > 0 for calculation.")
    
    rho = lambda_rate / mu_rate
    
    # Stability check: System is stable only if arrival < service
    if rho >= 1:
        logger.warning(f"System unstable: Utilization {rho:.2f} >= 1.0. Infinite queue growth.")
        # Return inf for wait time if unstable
        return {"utilization": rho, "avg_wait_time": float('inf')}
    
    # Average time in system (Wait + Service) = 1 / (mu - lambda)
    # Average wait time in queue (W_q) = rho / (mu - lambda)
    avg_wait = rho / (mu_rate - lambda_rate)
    
    return {"utilization": rho, "avg_wait_time": avg_wait}


def map_concurrency_to_manufacturing(
    source_node: InternetNode, 
    target_capacity: int
) -> IndustrialNode:
    """
    Core Function 1: Structural Mapping.
    
    Transforms a High Concurrency model (Internet) into a Multi-Station 
    Processing model (Industrial) based on queue theory isomorphism.
    
    Args:
        source_node: The source internet node containing traffic parameters.
        target_capacity: The number of available industrial workstations.
        
    Returns:
        IndustrialNode: The initialized industrial node with mapped parameters.
        
    Raises:
        DomainMappingError: If data validation fails.
    """
    logger.info(f"Starting mapping from Internet Node to Industrial Node...")
    
    # 1. Extract Isomorphic Parameters
    # Internet Lambda -> Industrial Material Input Rate
    mat_rate = source_node.arrival_rate
    # Internet Mu -> Industrial Processing Rate per station
    proc_rate = source_node.service_rate
    # Server Count -> Station Count
    stations = target_capacity
    
    # 2. Boundary Checks
    if proc_rate * stations < mat_rate:
        logger.error("Mapped capacity insufficient for material input rate.")
        # In a real scenario, we might trigger a scaling event here
    
    # 3. Construct Target Node
    target_node = IndustrialNode(
        material_input_rate=mat_rate,
        processing_rate=proc_rate,
        num_stations=stations,
        buffer_size=0 # Default infinite buffer
    )
    
    logger.info(f"Mapping complete. Input: {mat_rate}, Process Rate: {proc_rate}, Stations: {stations}")
    return target_node


def validate_industrial_solution(node: IndustrialNode) -> Tuple[bool, Dict[str, float]]:
    """
    Core Function 2: Solution Verification.
    
    Validates the mapped industrial solution using Queuing Theory formulas 
    (approximating M/M/c model or simplified M/M/1 per station logic).
    
    Args:
        node: The industrial node to validate.
        
    Returns:
        A tuple containing:
        - bool: True if the system is stable and efficient, False otherwise.
        - Dict: Calculated performance metrics.
    """
    logger.info("Validating industrial solution effectiveness...")
    
    # Calculate effective service rate for the whole cluster
    total_processing_capacity = node.processing_rate * node.num_stations
    
    # Boundary Check: Prevent division by zero
    if total_processing_capacity == 0:
        raise DomainMappingError("Total processing capacity cannot be zero.")

    # Calculate metrics using helper
    # Note: This is a simplified aggregation. Strict M/M/c logic is more complex.
    metrics = calculate_mm1_metrics(node.material_input_rate, total_processing_capacity)
    
    # Update node status based on calculation
    node.is_stable = metrics["utilization"] < 1.0
    node.avg_wait_time = metrics["avg_wait_time"]
    
    # Validation Logic
    is_valid = True
    if not node.is_stable:
        is_valid = False
        logger.warning("Validation Failed: System is unstable (Bottleneck detected).")
    elif metrics["utilization"] > 0.85: # Heuristic: Safety margin
        logger.warning(f"Validation Warning: High utilization {metrics['utilization']:.2f}. Risk of jitter.")
    
    if is_valid:
        logger.info(f"Validation Passed. Utilization: {metrics['utilization']:.2f}, Avg Wait: {metrics['avg_wait_time']:.4f}")
        
    return is_valid, metrics


# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    try:
        # 1. Define the Internet Problem (High Concurrency)
        # Scenario: 1000 requests per second, single server handles 1200 req/s
        # We want to migrate this logic to a factory setting
        internet_scenario = InternetNode(
            arrival_rate=1000.0, 
            service_rate=1200.0, 
            num_servers=1
        )
        
        print("-" * 60)
        print("Source Domain: Internet (High Concurrency)")
        print(f"Traffic Intensity: {internet_scenario.arrival_rate} req/s")
        
        # 2. Perform Cross-Domain Mapping
        # Target: Factory with 1 workstation
        print("-" * 60)
        print("Mapping to Target Domain: Industrial (Parallel Processing)...")
        factory_scenario = map_concurrency_to_manufacturing(
            source_node=internet_scenario, 
            target_capacity=1
        )
        
        # 3. Validate the Migrated Solution
        print("-" * 60)
        print("Validating Mapped Solution...")
        is_success, performance = validate_industrial_solution(factory_scenario)
        
        print("-" * 60)
        print("RESULT:")
        print(f"System Stable: {is_success}")
        print(f"Machine Utilization: {performance['utilization']:.2%}")
        print(f"Average Queue Wait Time: {performance['avg_wait_time']:.4f} time units")
        
        # 4. Demonstrate Failure Case (Bottleneck)
        print("\n" + "=" * 60)
        print("Testing Edge Case: Overload Scenario")
        overload_scenario = InternetNode(arrival_rate=1500.0, service_rate=1000.0)
        factory_overload = map_concurrency_to_manufacturing(overload_scenario, 1)
        validate_industrial_solution(factory_overload)
        
    except DomainMappingError as dme:
        logger.error(f"Mapping failed: {dme}")
    except ValueError as ve:
        logger.error(f"Invalid input parameters: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)