"""
Module: anti_fragile_ecosystem_architect
Description: Implements the 'Anti-Fragile Organizational Ecosystem Architecture' skill.
This module models enterprise departments as biological species to calculate functional
redundancy and suggest resilience strategies.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Department:
    """
    Represents a department or asset within the enterprise ecosystem.
    
    Attributes:
        id: Unique identifier for the department.
        name: Name of the department.
        functions: Set of functional capabilities provided (e.g., 'logistics', 'ai_research').
        efficiency_score: Current profit/efficiency rating (0.0 to 1.0).
        uniqueness_score: How distinct/rare its capabilities are (0.0 to 1.0).
        dependencies: IDs of departments this unit relies upon.
    """
    id: str
    name: str
    functions: Set[str]
    efficiency_score: float = 0.5
    uniqueness_score: float = 0.5
    dependencies: Set[str] = field(default_factory=set)

class EcosystemAnalyzer:
    """Analyzes and builds the anti-fragile architecture of the organization."""

    def __init__(self, departments: List[Department]):
        self.departments = {d.id: d for d in departments}
        self.function_map: Dict[str, List[str]] = {} # function -> list of dept_ids
        self._build_function_map()
        logger.info(f"Ecosystem initialized with {len(departments)} entities.")

    def _build_function_map(self) -> None:
        """Indexes departments by their functions to calculate redundancy."""
        for d_id, dept in self.departments.items():
            for func in dept.functions:
                if func not in self.function_map:
                    self.function_map[func] = []
                self.function_map[func].append(d_id)

    def _validate_float_range(self, value: float, name: str) -> None:
        """Helper function to validate score ranges."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"{name} must be between 0.0 and 1.0. Got {value}.")

    def calculate_functional_redundancy(self) -> Dict[str, float]:
        """
        Calculates the redundancy index for every critical function.
        
        Redundancy Index (RI) = log(N + 1), where N is the number of departments 
        supporting a specific function. This rewards backup capabilities but 
        flattens the curve to avoid hoarding.
        
        Returns:
            Dict mapping function names to their Redundancy Index.
        """
        redundancy_report = {}
        logger.info("Calculating functional redundancy...")
        
        for func, dept_ids in self.function_map.items():
            count = len(dept_ids)
            # Using logarithmic scale to value redundancy but diminishing returns
            index = math.log10(count + 1)
            redundancy_report[func] = index
            
            if count == 1:
                logger.warning(f"CRITICAL RISK: Function '{func}' has single point of failure (Dept: {dept_ids[0]}).")
        
        return redundancy_report

    def evaluate_anti_fragility_potential(self, dept_id: str) -> float:
        """
        Calculates the 'Survival Value' of a department.
        
        Formula: 
        SV = (Uniqueness * 0.6) + (Redundancy_Contribution * 0.4) - (Efficiency_Penalty * 0.2)
        Note: In anti-fragile systems, high efficiency often means low redundancy (fragile).
        We value 'Uniqueness' (ancient genes) higher even if 'Efficiency' is low.
        
        Args:
            dept_id: The ID of the department to evaluate.
            
        Returns:
            A float score representing the resilience value (0.0 to 1.0+).
        """
        if dept_id not in self.departments:
            raise ValueError(f"Department ID {dept_id} not found.")
        
        dept = self.departments[dept_id]
        
        # 1. Base value from uniqueness
        uniqueness = dept.uniqueness_score
        
        # 2. Contribution to Redundancy (how many 'rare' functions it supports)
        rare_contribution = 0.0
        for func in dept.functions:
            # If this function is rare (only 1 or 2 providers), contribution is high
            providers = len(self.function_map.get(func, []))
            if providers <= 2:
                rare_contribution += 0.5 * (1.0 / providers) # Higher score for being the sole provider
        
        # 3. Efficiency Discount (High efficiency often implies over-optimization/fragility)
        # We penalize extreme efficiency if it lacks uniqueness
        efficiency_penalty = 0.0
        if dept.efficiency_score > 0.9 and uniqueness < 0.3:
            efficiency_penalty = 0.5 # Over-optimized commodity
        
        survival_value = (uniqueness * 0.6) + min(rare_contribution, 1.0) - efficiency_penalty
        
        logger.debug(f"Dept {dept.name}: SV={survival_value:.2f} (Uniq:{uniqueness}, RareCont:{rare_contribution})")
        return survival_value

    def generate_restructuring_advice(self) -> List[str]:
        """
        Generates actionable advice to improve ecosystem resilience.
        
        Returns:
            List of recommended actions.
        """
        advice = []
        redundancy_report = self.calculate_functional_redundancy()
        
        # 1. Identify functions with no redundancy (SPOF)
        for func, ri in redundancy_report.items():
            if ri < 0.5: # Approx log(2), meaning only 1 provider
                advice.append(f"CRITICAL: Create redundancy for function '{func}'. Consider splitting or duplicating resources.")

        # 2. Identify 'Living Fossils' (Low efficiency but High Uniqueness)
        for d_id, dept in self.departments.items():
            if dept.efficiency_score < 0.4 and dept.uniqueness_score > 0.7:
                advice.append(
                    f"PRESERVE: Protect department '{dept.name}'. "
                    f"Although efficiency is low ({dept.efficiency_score:.2f}), "
                    f"it holds unique genetic value ({dept.uniqueness_score:.2f}) critical for future shocks."
                )
            elif dept.efficiency_score > 0.95 and dept.uniqueness_score < 0.1:
                advice.append(
                    f"FRAGILITY WARNING: Department '{dept.name}' is highly optimized but generic. "
                    f"Vulnerable to market shifts. Consider diversifying its functions."
                )
                
        return advice

# Example Usage
if __name__ == "__main__":
    # Sample Data: Corporate Ecosystem
    dept_list = [
        Department(
            id="core_sales",
            name="Global Sales Force",
            functions={"revenue_generation", "client_relations"},
            efficiency_score=0.95,
            uniqueness_score=0.2
        ),
        Department(
            id="rnd_legacy",
            name="Legacy Basic Research Lab",
            functions={"fundamental_physics", "material_science"},
            efficiency_score=0.2, # Low immediate profit
            uniqueness_score=0.9, # High unique capability
            dependencies={"admin"}
        ),
        Department(
            id="it_ops",
            name="IT Infrastructure",
            functions={"server_maintenance", "cybersecurity"},
            efficiency_score=0.8,
            uniqueness_score=0.4
        ),
        Department(
            id="it_backup",
            name="Backup IT Facility",
            functions={"server_maintenance"}, # Provides redundancy
            efficiency_score=0.3, # Often idle, low efficiency usage
            uniqueness_score=0.1
        )
    ]

    try:
        analyzer = EcosystemAnalyzer(dept_list)
        
        # 1. Calculate Redundancy
        red_data = analyzer.calculate_functional_redundancy()
        print("\n--- Redundancy Report ---")
        print(red_data)
        
        # 2. Evaluate Survival Value of the 'Low Efficiency' Lab
        sv = analyzer.evaluate_anti_fragility_potential("rnd_legacy")
        print(f"\nSurvival Value of Legacy Lab: {sv:.2f}")
        
        # 3. Get Advice
        print("\n--- Architecture Advice ---")
        recommendations = analyzer.generate_restructuring_advice()
        for rec in recommendations:
            print(f"- {rec}")
            
    except ValueError as e:
        logger.error(f"Validation Error: {e}")
    except Exception as e:
        logger.critical(f"System Failure: {e}")