"""
Module: auto_融合能力_功能冗余型组织抗毁伤架构_将投_de0a48
Description: Implements a framework for assessing and designing anti-fragile systems
             by introducing financial portfolio concepts (Sharpe Ratio) into organizational
             and AI architecture design. It focuses on functional redundancy and robustness.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    Represents a unit in the organization or system architecture.
    
    Attributes:
        id (str): Unique identifier for the node.
        function (str): The primary function this node performs (e.g., 'compute', 'decision_making').
        performance (float): The efficiency or output quality of the node (0.0 to 1.0).
        is_backup (bool): Whether this node is a redundant backup.
        failure_prob (float): Probability of failure or unavailability (0.0 to 1.0).
        heterogeneity_factor (float): Degree of difference from primary nodes (0.0 to 1.0).
    """
    id: str
    function: str
    performance: float = 0.8
    is_backup: bool = False
    failure_prob: float = 0.1
    heterogeneity_factor: float = 0.0

    def __post_init__(self):
        self._validate_attributes()

    def _validate_attributes(self):
        if not 0.0 <= self.performance <= 1.0:
            raise ValueError(f"Performance must be between 0 and 1 for node {self.id}")
        if not 0.0 <= self.failure_prob <= 1.0:
            raise ValueError(f"Failure probability must be between 0 and 1 for node {self.id}")
        if not 0.0 <= self.heterogeneity_factor <= 1.0:
            raise ValueError(f"Heterogeneity factor must be between 0 and 1 for node {self.id}")

@dataclass
class SystemArchitecture:
    """
    Represents the collection of nodes forming the system.
    """
    nodes: List[Node] = field(default_factory=list)

    def add_node(self, node: Node):
        if not isinstance(node, Node):
            raise TypeError("Only Node objects can be added.")
        self.nodes.append(node)
        logger.info(f"Node {node.id} added to architecture.")

    def get_functional_groups(self) -> Dict[str, List[Node]]:
        """Groups nodes by their primary function."""
        groups: Dict[str, List[Node]] = {}
        for node in self.nodes:
            if node.function not in groups:
                groups[node.function] = []
            groups[node.function].append(node)
        return groups

def calculate_system_sharpe_ratio(
    architecture: SystemArchitecture, 
    risk_free_rate: float = 0.02
) -> float:
    """
    Calculates the 'System Sharpe Ratio' analogous to finance.
    (System Efficiency - Risk-Free Efficiency) / System Volatility (Risk).
    
    High efficiency is desired, but high volatility (caused by single points of failure) lowers the score.
    
    Args:
        architecture (SystemArchitecture): The system to evaluate.
        risk_free_rate (float): A baseline efficiency expectation.
        
    Returns:
        float: The calculated pseudo-Sharpe ratio.
    """
    logger.info("Calculating System Sharpe Ratio...")
    
    if not architecture.nodes:
        return 0.0

    # Calculate Average Efficiency (Return)
    total_performance = sum(n.performance for n in architecture.nodes if not n.is_backup)
    active_nodes = [n for n in architecture.nodes if not n.is_backup]
    
    if not active_nodes:
        return 0.0
        
    avg_efficiency = total_performance / len(active_nodes)
    
    # Calculate Systemic Risk (Volatility) based on failure probability clustering
    # We treat 'risk' as the variance of expected output.
    # If a critical function relies on one node with high failure prob, variance is high.
    
    groups = architecture.get_functional_groups()
    system_risk = 0.0
    
    for func, nodes in groups.items():
        primary_nodes = [n for n in nodes if not n.is_backup]
        backup_nodes = [n for n in nodes if n.is_backup]
        
        # Probability that ALL primary nodes fail simultaneously
        # P(Fail) = Product(p_fail)
        p_primary_fail = 1.0
        for n in primary_nodes:
            p_primary_fail *= n.failure_prob
            
        # Backups mitigate risk. 
        # Effectiveness of backup depends on heterogeneity (diversity).
        # High heterogeneity = less likely to fail from the same cause as primary.
        mitigation_factor = 0.0
        if backup_nodes:
            # Simple model: Average heterogeneity reduces the impact of primary failure
            avg_hetero = sum(n.heterogeneity_factor for n in backup_nodes) / len(backup_nodes)
            mitigation_factor = avg_hetero * (1 - p_primary_fail) # Diverse backups absorb shock
            
        # Risk contribution: Probability of total failure * Impact (1.0 is total loss)
        # Mitigation reduces the effective probability
        effective_failure_prob = p_primary_fail * (1 - mitigation_factor)
        system_risk += effective_failure_prob

    # Normalize risk relative to number of functions
    if groups:
        system_risk /= len(groups)
        
    # Avoid division by zero
    if system_risk == 0:
        system_risk = 1e-4

    # Sharpe Ratio Formula adaptation
    ratio = (avg_efficiency - risk_free_rate) / math.sqrt(system_risk)
    
    logger.info(f"Avg Efficiency: {avg_efficiency:.4f}, System Risk: {system_risk:.4f}, Ratio: {ratio:.4f}")
    return round(ratio, 4)

def recommend_redundancy_strategy(
    architecture: SystemArchitecture, 
    budget_constraint: int = 3
) -> List[Dict[str, Union[str, float]]]:
    """
    Analyzes the architecture and suggests where to add redundancy (insurance).
    
    Args:
        architecture (SystemArchitecture): The current system.
        budget_constraint (int): Max number of new nodes suggested.
        
    Returns:
        List[Dict]: Recommendations for backup nodes.
    """
    logger.info("Analyzing redundancy requirements...")
    recommendations = []
    
    groups = architecture.get_functional_groups()
    
    # Calculate risk score for each function
    function_risks = []
    for func, nodes in groups.items():
        primary_nodes = [n for n in nodes if not n.is_backup]
        backup_nodes = [n for n in nodes if n.is_backup]
        
        # Criticality: How important is this function? 
        # Here simplified as number of primary nodes (critical path dependency)
        # and their average performance.
        
        # Risk: High failure prob + Low backup + High importance
        current_failure_prob = 1.0
        for n in primary_nodes:
            current_failure_prob *= n.failure_prob
            
        # If backups exist, risk is lower
        if backup_nodes:
            # Simple reduction logic for demo
            current_failure_prob *= 0.5 ** len(backup_nodes)
            
        # Calculate "Insurance Value": 
        # How much value would a backup add? (High risk + High Performance nodes)
        insurance_value = current_failure_prob * sum(n.performance for n in primary_nodes)
        
        function_risks.append({
            "function": func,
            "risk": current_failure_prob,
            "insurance_value": insurance_value,
            "has_backup": len(backup_nodes) > 0
        })
    
    # Sort by highest insurance value (best place to add insurance)
    function_risks.sort(key=lambda x: x['insurance_value'], reverse=True)
    
    for item in function_risks:
        if len(recommendations) >= budget_constraint:
            break
            
        if item['risk'] > 0.05: # Threshold for action
            rec = {
                "target_function": item['function'],
                "suggested_action": "ADD_HETEROGENEOUS_BACKUP",
                "reason": f"High vulnerability (Risk: {item['risk']:.2f}) detected. Adding a backup increases system robustness.",
                "expected_sharpe_improvement": item['insurance_value'] * 0.5 # Heuristic
            }
            recommendations.append(rec)
            logger.warning(f"Vulnerability found in function '{item['function']}'. Recommendation generated.")
            
    return recommendations

def _simulate_shock(architecture: SystemArchitecture, shock_magnitude: float = 0.5) -> float:
    """
    Helper function to simulate a shock and measure resilience.
    
    Args:
        architecture: The system.
        shock_magnitude: Probability that a node fails during the shock (0-1).
        
    Returns:
        float: The percentage of functionality retained.
    """
    import random
    retained_functions = 0
    total_functions = 0
    
    groups = architecture.get_functional_groups()
    
    for func, nodes in groups.items():
        total_functions += 1
        is_function_alive = False
        # Check if at least one node survives
        for node in nodes:
            # Probability of survival = 1 - (failure_prob + shock_effect)
            # Ensure probability doesn't exceed 1
            p_fail = min(1.0, node.failure_prob + shock_magnitude)
            if random.random() > p_fail:
                is_function_alive = True
                break
        if is_function_alive:
            retained_functions += 1
            
    resilience = retained_functions / total_functions if total_functions > 0 else 0.0
    logger.debug(f"Shock simulation complete. Resilience: {resilience:.2f}")
    return resilience

# Example Usage
if __name__ == "__main__":
    # 1. Define the system architecture
    print("--- Initializing System Architecture ---")
    sys_arch = SystemArchitecture()
    
    # Core Team (High Efficiency, but Single Points of Failure)
    sys_arch.add_node(Node(id="lead_dev", function="coding", performance=0.95, failure_prob=0.1))
    sys_arch.add_node(Node(id="lead_design", function="design", performance=0.90, failure_prob=0.15))
    sys_arch.add_node(Node(id="db_admin", function="database", performance=0.85, failure_prob=0.2))
    
    # Calculate Initial State
    print("\n--- Initial Analysis ---")
    initial_sharpe = calculate_system_sharpe_ratio(sys_arch)
    print(f"Initial System Sharpe Ratio: {initial_sharpe}")
    
    # Get Recommendations
    print("\n--- Generating Redundancy Recommendations ---")
    recs = recommend_redundancy_strategy(sys_arch, budget_constraint=2)
    for r in recs:
        print(f"Action: {r['suggested_action']} for {r['target_function']}")
        print(f"Reason: {r['reason']}")
        
    # Apply Recommendations (Simulated)
    print("\n--- Applying 'Anti-Fragile' Patches ---")
    # Adding a heterogeneous backup for coding (e.g., an external consultant or different AI model)
    sys_arch.add_node(Node(
        id="backup_ai_coder", 
        function="coding", 
        performance=0.7, # Lower efficiency
        is_backup=True, 
        heterogeneity_factor=0.8, # High diversity
        failure_prob=0.05 # Very reliable
    ))
    
    # Adding a backup for database
    sys_arch.add_node(Node(
        id="backup_db_replica", 
        function="database", 
        performance=0.8, 
        is_backup=True,
        heterogeneity_factor=0.2, # Low diversity (same tech stack)
        failure_prob=0.2
    ))
    
    # Calculate New State
    print("\n--- Final Analysis ---")
    final_sharpe = calculate_system_sharpe_ratio(sys_arch)
    print(f"Final System Sharpe Ratio: {final_sharpe}")
    print(f"Improvement: {final_sharpe - initial_sharpe:.4f}")
    
    # Simulate Shock
    print("\n--- Simulating Catastrophic Shock ---")
    resilience = _simulate_shock(sys_arch, shock_magnitude=0.6)
    print(f"System Functionality Retained: {resilience * 100}%")