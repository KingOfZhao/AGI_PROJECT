"""
Module: auto_认知自洽验证_黑盒测试用例生成器
Description: Automatic generation of black-box test cases to verify the closed-loop
             consistency of cognitive nodes (e.g., Street Vendor Economy).
Author: AGI System Core
Version: 1.0.0
"""

import logging
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StressLevel(Enum):
    """Enumeration for simulation stress levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SimulationScenario:
    """Data structure representing a single test scenario."""
    scenario_id: str
    description: str
    input_factors: Dict[str, Any]
    expected_behavior_keywords: List[str]
    stress_level: StressLevel

    def to_dict(self) -> Dict[str, Any]:
        """Convert the scenario to a dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "input_factors": self.input_factors,
            "expected_behavior_keywords": self.expected_behavior_keywords,
            "stress_level": self.stress_level.name
        }


@dataclass
class CognitiveDomain:
    """Represents the cognitive domain node to be tested."""
    name: str
    attributes: Dict[str, Any]
    constraints: List[str] = field(default_factory=list)


class BlackBoxTestGenerator:
    """
    Core class for generating black-box test cases for cognitive consistency verification.
    """

    def __init__(self, domain_config: Dict[str, Any]):
        """
        Initialize the generator with domain configuration.

        Args:
            domain_config (Dict[str, Any]): Configuration containing variables and rules.
        """
        self.domain = self._parse_domain_config(domain_config)
        self.generated_scenarios: List[SimulationScenario] = []
        logger.info(f"BlackBoxTestGenerator initialized for domain: {self.domain.name}")

    def _parse_domain_config(self, config: Dict[str, Any]) -> CognitiveDomain:
        """Helper function to parse and validate input config."""
        if not config or "name" not in config:
            logger.error("Invalid domain configuration provided.")
            raise ValueError("Domain configuration must contain a 'name' field.")
        
        return CognitiveDomain(
            name=config.get("name"),
            attributes=config.get("attributes", {}),
            constraints=config.get("constraints", [])
        )

    def _generate_environmental_noise(self, intensity: StressLevel) -> Dict[str, Any]:
        """
        Helper function to generate random environmental variables based on stress level.
        
        Args:
            intensity (StressLevel): The intensity of the noise to generate.
        
        Returns:
            Dict[str, Any]: A dictionary of environmental factors.
        """
        base_noise = {
            "weather_condition": "normal",
            "regulatory_pressure": 0.0,
            "market_volatility": 0.0
        }

        if intensity == StressLevel.LOW:
            base_noise["weather_condition"] = random.choice(["sunny", "cloudy"])
            base_noise["regulatory_pressure"] = round(random.uniform(0, 0.2), 2)
        
        elif intensity == StressLevel.MEDIUM:
            base_noise["weather_condition"] = random.choice(["rainy", "windy"])
            base_noise["regulatory_pressure"] = round(random.uniform(0.2, 0.5), 2)
            base_noise["market_volatility"] = round(random.uniform(0.1, 0.3), 2)

        elif intensity == StressLevel.HIGH:
            base_noise["weather_condition"] = random.choice(["storm", "heatwave"])
            base_noise["regulatory_pressure"] = round(random.uniform(0.5, 0.8), 2)
            base_noise["market_volatility"] = round(random.uniform(0.3, 0.6), 2)
            base_noise["supply_chain_disruption"] = True

        elif intensity == StressLevel.CRITICAL:
            base_noise["weather_condition"] = "severe_hazard"
            base_noise["regulatory_pressure"] = 1.0  # Max enforcement
            base_noise["market_volatility"] = round(random.uniform(0.8, 1.0), 2)
            base_noise["emergency_event"] = random.choice(["pandemic", "curfew"])

        return base_noise

    def generate_scenarios(
        self, 
        count: int = 5, 
        stress_mix: Optional[List[StressLevel]] = None
    ) -> List[SimulationScenario]:
        """
        Generates a list of simulation scenarios based on the domain context.

        Args:
            count (int): Number of scenarios to generate.
            stress_mix (Optional[List[StressLevel]]): A list of stress levels to cycle through.
                                                      If None, selects randomly.

        Returns:
            List[SimulationScenario]: List of generated test case objects.
        """
        if count < 1:
            logger.warning("Requested count < 1, returning empty list.")
            return []

        logger.info(f"Generating {count} scenarios for {self.domain.name}...")
        scenarios = []

        for i in range(count):
            # Determine stress level for this iteration
            if stress_mix and len(stress_mix) > 0:
                current_stress = stress_mix[i % len(stress_mix)]
            else:
                current_stress = random.choice(list(StressLevel))

            # Generate factors
            env_factors = self._generate_environmental_noise(current_stress)
            
            # Construct Scenario
            scenario_id = f"{self.domain.name}_TEST_{i+1:03d}"
            description = (
                f"Simulating {current_stress.name} stress environment for {self.domain.name}. "
                f"Conditions: {env_factors}"
            )
            
            # Define expected cognitive outcomes (Blackbox Oracle)
            # In a real AGI system, these would be checked against the system's output
            expected_keywords = self._derive_expected_keywords(env_factors, current_stress)

            scenario = SimulationScenario(
                scenario_id=scenario_id,
                description=description,
                input_factors=env_factors,
                expected_behavior_keywords=expected_keywords,
                stress_level=current_stress
            )
            scenarios.append(scenario)
            logger.debug(f"Generated scenario: {scenario_id}")

        self.generated_scenarios.extend(scenarios)
        return scenarios

    def _derive_expected_keywords(
        self, 
        factors: Dict[str, Any], 
        stress: StressLevel
    ) -> List[str]:
        """
        Internal logic to determine what constitutes a 'consistent' response.
        """
        keywords = []
        
        if factors.get("regulatory_pressure", 0) > 0.7:
            keywords.append("evasive_action")
            keywords.append("inventory_concealment")
        
        if factors.get("weather_condition") in ["rainy", "storm"]:
            keywords.append("seek_shelter")
            keywords.append("protect_merchandise")
            
        if factors.get("supply_chain_disruption"):
            keywords.append("price_adjustment")
            keywords.append("alternative_sourcing")
            
        if not keywords:
            keywords.append("maintain_operations")
            keywords.append("routine_optimization")
            
        return keywords

    def export_test_suite(self, format_type: str = "json") -> str:
        """
        Exports the generated scenarios to a specific format.

        Args:
            format_type (str): 'json' or 'dict'.

        Returns:
            str: Serialized test suite.
        """
        if not self.generated_scenarios:
            logger.warning("No scenarios generated to export.")
            return "{}"

        data = {
            "domain": self.domain.name,
            "test_suite_size": len(self.generated_scenarios),
            "test_cases": [s.to_dict() for s in self.generated_scenarios]
        }

        if format_type == "json":
            return json.dumps(data, indent=4)
        else:
            return str(data)


# Usage Example
if __name__ == "__main__":
    # Define the cognitive domain configuration (e.g., Street Vendor Economy)
    vendor_config = {
        "name": "Street_Vendor_Economy_Node",
        "attributes": {
            "capital": 500,
            "inventory": ["food", "utensils"],
            "location_type": "mobile"
        },
        "constraints": ["max_profit", "risk_avoidance"]
    }

    try:
        # Initialize Generator
        generator = BlackBoxTestGenerator(vendor_config)

        # Generate 5 specific scenarios mixing Medium and Critical stress
        target_stresses = [StressLevel.MEDIUM, StressLevel.CRITICAL, StressLevel.LOW]
        test_cases = generator.generate_scenarios(count=3, stress_mix=target_stresses)

        print(f"\n--- Generated {len(test_cases)} Black-Box Test Cases ---")
        for case in test_cases:
            print(f"ID: {case.scenario_id}")
            print(f"Stress: {case.stress_level.name}")
            print(f"Factors: {case.input_factors}")
            print(f"Expecting behavior involving: {case.expected_behavior_keywords}")
            print("-" * 40)

        # Export to JSON
        # json_output = generator.export_test_suite()
        # print(json_output)

    except ValueError as ve:
        logger.error(f"Configuration Error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected System Failure: {e}", exc_info=True)