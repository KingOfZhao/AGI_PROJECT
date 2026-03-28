"""
Module: auto_causal_attribution_analysis
Description: Implements top-down decomposition and falsification for skill execution failures.
             Uses causal reasoning to attribute failure to Environment, Skill Defect, or Execution Error.
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
Domain: causal_inference
"""

import logging
import typing
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class FailureCategory(Enum):
    """
    Enumeration of possible failure root causes derived from causal analysis.
    """
    ENVIRONMENT_NOISE = "Environment Noise (Uncontrollable)"
    SKILL_DEFECT = "Skill Defect (Logic/Model Error)"
    EXECUTION_BIAS = "Execution Bias (Human/Operator Error)"
    UNKNOWN = "Insufficient Data for Causal Link"

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class SkillContext:
    """
    Represents the state context of a skill execution.
    """
    skill_name: str
    expected_params: dict
    actual_params: dict
    environment_state: dict  # e.g., weather, market activity
    internal_state: dict     # e.g., agent health, inventory
    outcome: bool            # True if Success, False if Failure
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AttributionResult:
    """
    Result of the causal attribution analysis.
    """
    category: FailureCategory
    confidence: float  # 0.0 to 1.0
    root_cause_hypothesis: str
    recommended_action: str
    debug_data: dict = field(default_factory=dict)

# --- Core Functions ---

def decompose_failure_factors(context: SkillContext) -> typing.Dict[str, float]:
    """
    Decomposes the failure into potential contributing factors using a simulated 
    causal graph weight adjustment.
    
    Args:
        context (SkillContext): The data object containing execution details.
        
    Returns:
        typing.Dict[str, float]: A dictionary mapping factor names to their 
                                 calculated impact scores (0.0-1.0).
    
    Raises:
        ValueError: If input data is malformed or missing critical keys.
    """
    logger.info(f"Starting decomposition for Skill: {context.skill_name}")
    
    # Data Validation
    if not isinstance(context.expected_params, dict) or not isinstance(context.actual_params, dict):
        logger.error("Invalid parameter format in context.")
        raise ValueError("Parameters must be dictionaries.")
    
    factors = {
        "environment_impact": 0.0,
        "skill_logic_gap": 0.0,
        "execution_deviation": 0.0
    }
    
    try:
        # 1. Check Execution Deviation (Human/Actuator Error)
        # Compare expected vs actual params (e.g., price set vs price input)
        param_diff = _calculate_param_divergence(context.expected_params, context.actual_params)
        factors["execution_deviation"] = param_diff
        
        # 2. Check Environment Noise
        # Heuristic: If environment 'hostility' metric is high
        env_hostility = context.environment_state.get("hostility_level", 0.0)
        factors["environment_impact"] = min(max(env_hostility, 0.0), 1.0)
        
        # 3. Check Skill Defect
        # Heuristic: If execution was perfect and environment was benign, 
        # but still failed, the skill logic (model) is likely wrong.
        # This is a "Falsification" step: Proving it wasn't env or execution.
        if factors["execution_deviation"] < 0.1 and factors["environment_impact"] < 0.2:
            factors["skill_logic_gap"] = 0.8  # High probability of skill defect
        else:
            factors["skill_logic_gap"] = 0.1  # Low probability

        logger.debug(f"Decomposed factors: {factors}")
        return factors
        
    except Exception as e:
        logger.exception("Error during factor decomposition.")
        raise RuntimeError(f"Decomposition failed: {str(e)}")

def perform_causal_attribution(context: SkillContext, factors: typing.Dict[str, float]) -> AttributionResult:
    """
    Performs the final causal inference to determine the primary root cause.
    
    Args:
        context (SkillContext): The execution context.
        factors (typing.Dict[str, float]): Impact scores from decomposition.
        
    Returns:
        AttributionResult: The structured conclusion of the analysis.
    """
    logger.info("Performing causal attribution...")
    
    if context.outcome:
        logger.warning("Analysis called on a successful execution. Returning default success.")
        return AttributionResult(
            category=FailureCategory.UNKNOWN,
            confidence=1.0,
            root_cause_hypothesis="Success",
            recommended_action="None"
        )

    # Thresholds for decision making
    EXECUTION_THRESHOLD = 0.4
    ENV_THRESHOLD = 0.5
    
    max_factor = max(factors, key=factors.get)
    
    # Causal Logic Chain
    if factors["execution_deviation"] > EXECUTION_THRESHOLD:
        # Falsification: The failure is most likely caused by the operator not following the skill parameters.
        return AttributionResult(
            category=FailureCategory.EXECUTION_BIAS,
            confidence=factors["execution_deviation"],
            root_cause_hypothesis="Significant deviation between expected and actual parameters.",
            recommended_action="Retrain operator or check actuator calibration.",
            debug_data={"raw_scores": factors}
        )
    
    elif factors["environment_impact"] > ENV_THRESHOLD:
        # Falsification: External conditions violated the skill's preconditions.
        return AttributionResult(
            category=FailureCategory.ENVIRONMENT_NOISE,
            confidence=factors["environment_impact"],
            root_cause_hypothesis="Uncontrollable environmental variables exceeded tolerance.",
            recommended_action="Retry skill when environment stabilizes or switch to robust skill variant.",
            debug_data={"raw_scores": factors}
        )
    
    elif factors["skill_logic_gap"] > 0.5:
        # Falsification: Execution and Environment were fine. The Skill itself is the variable.
        return AttributionResult(
            category=FailureCategory.SKILL_DEFECT,
            confidence=0.85, # Confidence derived from elimination
            root_cause_hypothesis="Skill logic failed to map state to successful outcome.",
            recommended_action="Update skill model or decision tree logic.",
            debug_data={"raw_scores": factors}
        )
    
    else:
        return AttributionResult(
            category=FailureCategory.UNKNOWN,
            confidence=0.1,
            root_cause_hypothesis="Ambiguous causality.",
            recommended_action="Gather more data points.",
            debug_data={"raw_scores": factors}
        )

# --- Helper Functions ---

def _calculate_param_divergence(expected: dict, actual: dict) -> float:
    """
    Helper: Calculates a normalized divergence score between two parameter sets.
    Uses a simple key-matching heuristic for demonstration.
    
    Args:
        expected (dict): The ideal parameters.
        actual (dict): The actual parameters used.
        
    Returns:
        float: Divergence score between 0.0 (identical) and 1.0 (completely different).
    """
    if not expected:
        return 0.0
    
    total_keys = set(expected.keys()) | set(actual.keys())
    if not total_keys:
        return 0.0
        
    errors = 0
    for key in total_keys:
        exp_val = expected.get(key)
        act_val = actual.get(key)
        
        if exp_val != act_val:
            # Simple mismatch count (could be extended to value difference for numerics)
            errors += 1
            
    divergence = errors / len(total_keys)
    logger.debug(f"Param divergence calculated: {divergence}")
    return divergence

# --- Main Execution Block ---

def run_analysis_pipeline(context: SkillContext) -> AttributionResult:
    """
    Main pipeline wrapper.
    """
    try:
        factors = decompose_failure_factors(context)
        result = perform_causal_attribution(context, factors)
        return result
    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
        return AttributionResult(
            category=FailureCategory.UNKNOWN,
            confidence=0.0,
            root_cause_hypothesis="System Error",
            recommended_action="Check logs"
        )

if __name__ == "__main__":
    # Example Usage: Street Vending Failure Analysis
    
    # Scenario 1: Execution Bias (Human Error)
    # The skill said 'price = 5', but the human set 'price = 50'
    vending_context_bias = SkillContext(
        skill_name="street_vending_basic",
        expected_params={"price": 5.0, "location": "downtown"},
        actual_params={"price": 50.0, "location": "downtown"}, # Error here
        environment_state={"hostility_level": 0.1, "foot_traffic": "high"},
        internal_state={"inventory": 100},
        outcome=False
    )
    
    print("--- Analyzing Scenario 1: Execution Bias ---")
    result_1 = run_analysis_pipeline(vending_context_bias)
    print(f"Category: {result_1.category.value}")
    print(f"Hypothesis: {result_1.root_cause_hypothesis}")
    
    # Scenario 2: Skill Defect (Logic Error)
    # Everything looks good, but the skill logic is flawed (Simulated by low noise + low deviation + failure)
    vending_context_skill = SkillContext(
        skill_name="street_vending_advanced",
        expected_params={"approach": "friendly"},
        actual_params={"approach": "friendly"},
        environment_state={"hostility_level": 0.1}, # Good env
        internal_state={"inventory": 100},
        outcome=False # Still failed
    )
    
    print("\n--- Analyzing Scenario 2: Skill Defect ---")
    result_2 = run_analysis_pipeline(vending_context_skill)
    print(f"Category: {result_2.category.value}")
    print(f"Hypothesis: {result_2.root_cause_hypothesis}")

    # Scenario 3: Environment Noise
    vending_context_env = SkillContext(
        skill_name="street_vending_basic",
        expected_params={"price": 10},
        actual_params={"price": 10},
        environment_state={"hostility_level": 0.9, "event": "rain"}, # Heavy rain
        internal_state={"inventory": 100},
        outcome=False
    )

    print("\n--- Analyzing Scenario 3: Environment Noise ---")
    result_3 = run_analysis_pipeline(vending_context_env)
    print(f"Category: {result_3.category.value}")
    print(f"Hypothesis: {result_3.root_cause_hypothesis}")