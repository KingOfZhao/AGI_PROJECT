"""
Module: auto_verify_causal_chain_vs_correlation.py

This module is designed for an AGI system to verify the capability of distinguishing
between causality and correlation. It provides tools to construct causal graphs from
observed data, identify confounding variables (spurious correlations), and validate
causal hypotheses through simulation of interventions (do-calculus logic).

The core logic is based on the principle that "Correlation does not imply Causation".
It uses the example of "Ice Cream Sales vs. Drowning Accidents" to demonstrate how
a confounding variable (Temperature) creates a spurious link.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
import itertools
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Enumeration of possible edge types in a causal graph."""
    CAUSAL = "causal"         # Direct cause A -> B
    SPURIOUS = "spurious"     # Correlation without direct cause (due to confounder)
    INDEPENDENT = "independent"


@dataclass
class Variable:
    """Represents a variable in the observation set."""
    name: str
    description: str
    observed_trend: str  # e.g., "rising", "falling", "stable"


@dataclass
class CausalLink:
    """Represents a relationship between two variables."""
    cause: Variable
    effect: Variable
    relation_type: RelationType
    confidence: float = 0.0  # 0.0 to 1.0
    confounders: List[Variable] = field(default_factory=list)

    def __str__(self) -> str:
        if self.relation_type == RelationType.CAUSAL:
            return f"{self.cause.name} -> {self.effect.name} (Direct Cause)"
        elif self.relation_type == RelationType.SPURIOUS:
            conf_names = [c.name for c in self.confounders]
            return f"{self.cause.name} -- {self.effect.name} (Spurious via {conf_names})"
        return f"{self.cause.name}  X  {self.effect.name} (Independent)"


@dataclass
class InterventionResult:
    """Result of a simulated intervention."""
    intervention: str
    is_effective: bool
    reasoning: str


class CausalVerificationSystem:
    """
    A system to verify if an AI correctly identifies causal structures and
    rejects spurious correlations based on observational data.
    """

    def __init__(self, variables: List[Variable], domain_knowledge: Optional[Dict] = None):
        """
        Initialize the verification system.

        Args:
            variables: A list of Variable objects representing the observed phenomena.
            domain_knowledge: Optional dictionary containing ground truth or physical laws
                              to assist in validation.
        """
        self.variables = variables
        self.variable_map = {v.name: v for v in variables}
        self.domain_knowledge = domain_knowledge or {}
        self.causal_graph: List[CausalLink] = []
        logger.info(f"CausalVerificationSystem initialized with {len(variables)} variables.")

    def _validate_inputs(self) -> bool:
        """Validates that input data is sufficient for analysis."""
        if len(self.variables) < 2:
            logger.error("Validation Error: At least two variables are required to check correlation.")
            raise ValueError("Insufficient data: At least two variables required.")
        
        names = [v.name for v in self.variables]
        if len(set(names)) != len(names):
            logger.error("Validation Error: Variable names must be unique.")
            raise ValueError("Duplicate variable names detected.")
            
        return True

    def analyze_correlations(self, correlation_data: List[Tuple[str, str, float]]) -> None:
        """
        Analyze pairs of variables that show statistical correlation.
        This function determines if a correlation is Causal or Spurious.

        Args:
            correlation_data: List of tuples (var_name_1, var_name_2, correlation_coeff).
                              Correlation coeff > 0.5 implies significant correlation.
        """
        self._validate_inputs()
        self.causal_graph = []
        
        logger.info("Starting causal analysis on correlated pairs...")
        
        for v1_name, v2_name, coeff in correlation_data:
            if v1_name not in self.variable_map or v2_name not in self.variable_map:
                logger.warning(f"Skipping unknown variable pair: {v1_name}, {v2_name}")
                continue
            
            if coeff < 0.6:  # Threshold for significance
                continue

            var1 = self.variable_map[v1_name]
            var2 = self.variable_map[v2_name]

            # Check for common causes (Confounders) using domain knowledge or heuristics
            # In a real AGI, this would query a knowledge base.
            # Here we simulate finding 'Temperature' as a common cause for 'Ice Cream' and 'Drowning'.
            
            potential_confounders = self._find_confounders(var1, var2)
            
            if potential_confounders:
                # If a confounder exists, the direct link is likely spurious
                link = CausalLink(
                    cause=var1,
                    effect=var2,
                    relation_type=RelationType.SPURIOUS,
                    confidence=0.9,
                    confounders=potential_confounders
                )
                logger.info(f"Detected SPURIOUS link between {var1.name} and {var2.name} due to {len(potential_confounders)} confounder(s).")
            else:
                # If no confounder and physical mechanism exists, assume causal
                link = CausalLink(
                    cause=var1,
                    effect=var2,
                    relation_type=RelationType.CAUSAL,
                    confidence=0.8
                )
                logger.info(f"Detected CAUSAL link: {var1.name} -> {var2.name}")
                
            self.causal_graph.append(link)

    def _find_confounders(self, var_a: Variable, var_b: Variable) -> List[Variable]:
        """
        [Internal Helper] Identifies if there is a common cause (confounder) in the
        variable set for the two provided variables.
        
        Logic:
        A confounder C affects both A and B.
        """
        confounders = []
        # Simple heuristic check: Is there a variable in our set that is NOT A or B
        # and is defined as an environmental factor?
        for potential_c in self.variables:
            if potential_c.name in [var_a.name, var_b.name]:
                continue
            
            # Simulation of Domain Knowledge check
            # In this specific scenario, we know Temperature causes Ice Cream sales
            # and Swimming frequency (leading to drowning).
            is_common_cause = False
            
            # Check if 'potential_c' is in the 'domain_knowledge' as a cause for 'var_a' and 'var_b'
            causes_of_a = self.domain_knowledge.get("causes", {}).get(var_a.name, [])
            causes_of_b = self.domain_knowledge.get("causes", {}).get(var_b.name, [])
            
            if potential_c.name in causes_of_a and potential_c.name in causes_of_b:
                is_common_cause = True
            
            if is_common_cause:
                confounders.append(potential_c)
                
        return confounders

    def propose_intervention(self, action_var_name: str, target_var_name: str) -> InterventionResult:
        """
        Proposes and validates an intervention (do-operator simulation).
        Checks if manipulating 'action_var' will change 'target_var' based on the
        constructed causal graph.

        Args:
            action_var_name: The variable we intend to change (e.g., 'Ice Cream Sales').
            target_var_name: The variable we want to affect (e.g., 'Drowning Accidents').

        Returns:
            InterventionResult object indicating success/failure and reasoning.
        """
        if action_var_name not in self.variable_map or target_var_name not in self.variable_map:
            raise ValueError("Invalid variable names for intervention.")

        logger.info(f"Evaluating intervention: DO({action_var_name}) to affect {target_var_name}")

        # Search for the link in the graph
        relevant_link = None
        for link in self.causal_graph:
            # Check both directions as correlation is symmetric initially
            if (link.cause.name == action_var_name and link.effect.name == target_var_name) or \
               (link.cause.name == target_var_name and link.effect.name == action_var_name):
                relevant_link = link
                break
        
        if relevant_link is None:
            return InterventionResult(
                intervention=f"Restrict/Modify {action_var_name}",
                is_effective=False,
                reasoning="No significant statistical relationship found."
            )

        if relevant_link.relation_type == RelationType.SPURIOUS:
            # The core of the skill: Rejecting intervention on spurious links
            confounder_names = [c.name for c in relevant_link.confounders]
            msg = (f"Intervention ineffective. The correlation between {action_var_name} and "
                   f"{target_var_name} is spurious. Both are driven by {confounder_names}. "
                   f"Changing {action_var_name} does not sever the link between {confounder_names} and {target_var_name}.")
            logger.warning(f"Intervention Failed: Spurious correlation detected. Common cause: {confounder_names}")
            return InterventionResult(
                intervention=f"Restrict {action_var_name}",
                is_effective=False,
                reasoning=msg
            )
        
        elif relevant_link.relation_type == RelationType.CAUSAL:
            msg = (f"Intervention likely effective. {action_var_name} is a direct cause of {target_var_name}.")
            logger.info("Intervention Validated: Causal path exists.")
            return InterventionResult(
                intervention=f"Restrict {action_var_name}",
                is_effective=True,
                reasoning=msg
            )
        
        # Default fallback
        return InterventionResult(
            intervention="Unknown",
            is_effective=False,
            reasoning="Could not determine relationship type."
        )

# ---------------------------------------------------------
# Usage Example and Demonstration
# ---------------------------------------------------------

def run_demonstration():
    """
    Demonstrates the verification of the 'Ice Cream vs Drowning' paradox.
    """
    print("-" * 60)
    print("AGI Skill Demonstration: Causal Chain vs Correlation")
    print("-" * 60)

    # 1. Define Observations (The input data)
    # We observe that Ice Cream sales and Drowning accidents are both rising.
    vars_data = [
        Variable(name="Ice_Cream_Sales", description="Sales volume of ice cream", observed_trend="rising"),
        Variable(name="Drowning_Accidents", description="Count of drowning incidents", observed_trend="rising"),
        Variable(name="Temperature", description="Ambient temperature", observed_trend="high")
    ]

    # 2. Define Ground Truth Knowledge (Simulating AGI's access to physical laws or history)
    # This helps the system identify confounders.
    knowledge = {
        "causes": {
            "Ice_Cream_Sales": ["Temperature"], # Heat causes people to buy ice cream
            "Drowning_Accidents": ["Temperature", "Swimming_Pool_Access"] # Heat causes people to swim
        }
    }

    # Initialize System
    try:
        system = CausalVerificationSystem(variables=vars_data, domain_knowledge=knowledge)
    except ValueError as e:
        print(f"Initialization Error: {e}")
        return

    # 3. Feed observed correlations (Simulated output from a statistical module)
    # We see a strong correlation (0.95) between Ice Cream and Drowning
    observed_correlations = [
        ("Ice_Cream_Sales", "Drowning_Accidents", 0.95),
        ("Temperature", "Ice_Cream_Sales", 0.90),
        ("Temperature", "Drowning_Accidents", 0.92)
    ]

    # 4. Run Analysis
    system.analyze_correlations(observed_correlations)

    # 5. Print Graph Structure
    print("\n[Generated Causal Graph]")
    for link in system.causal_graph:
        print(f" - {link}")

    # 6. Test Interventions (The Falsification Step)
    print("\n[Intervention Testing]")

    # Test Case 1: Banning Ice Cream to stop Drowning (The Fallacy)
    result_1 = system.propose_intervention("Ice_Cream_Sales", "Drowning_Accidents")
    print(f"\nHypothesis: Banning Ice Cream will reduce Drowning.")
    print(f"Result: {'EFFECTIVE' if result_1.is_effective else 'INEFFECTIVE'}")
    print(f"Reasoning: {result_1.reasoning}")

    # Test Case 2: Controlling Temperature (The Actual Cause - theoretically)
    # Note: In this graph, we analyzed the link between Ice Cream and Drowning.
    # To verify Temp -> Drowning, we would check that specific link.
    # Let's assume the system identified Temp -> Drowning as CAUSAL based on the 'knowledge' check logic
    # (Although in the current simplified logic, it checks pairs provided in correlation data).
    
    # Forcing a check on the causal pair explicitly
    # (Self-correction: The analyze function marked IceCream-Drowning as Spurious.
    # Let's check if the system can handle a valid causal pair if we add one.)
    
    # Adding a hypothetical causal link for contrast
    print("\n--- Contrast Test: Valid Causal Link ---")
    vars_simple = [
        Variable("Fire", "Combustion", "rising"),
        Variable("Smoke", "Visible particles", "rising")
    ]
    # Knowledge: Fire causes Smoke
    kb_simple = {"causes": {"Smoke": ["Fire"]}} 
    sys_simple = CausalVerificationSystem(vars_simple, kb_simple)
    # High correlation, no other confounders in this simple universe
    sys_simple.analyze_correlations([("Fire", "Smoke", 0.99)])
    
    res_smoke = sys_simple.propose_intervention("Fire", "Smoke")
    print(f"Hypothesis: Extinguishing Fire will stop Smoke.")
    print(f"Result: {'EFFECTIVE' if res_smoke.is_effective else 'INEFFECTIVE'}")
    print(f"Reasoning: {res_smoke.reasoning}")

if __name__ == "__main__":
    run_demonstration()