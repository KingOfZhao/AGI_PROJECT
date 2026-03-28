"""
Module: dynamic_context_router
A robust dynamic routing system that switches between aggressive association
and conservative isolation based on real-time context risk assessment.
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RoutingStrategy(Enum):
    """Enumeration of available routing strategies."""
    AGGRESSIVE_ASSOCIATION = auto()
    CONSERVATIVE_ISOLATION = auto()
    NEUTRAL = auto()

@dataclass
class ContextSnapshot:
    """
    Represents a snapshot of the current execution context.
    
    Attributes:
        trust_score: A float between 0.0 and 1.0 representing context trustworthiness.
        complexity_index: An integer representing the complexity of the current task.
        entropy_level: A float representing the unpredictability of the environment.
        sensitive_data_flags: List of flags indicating presence of sensitive data types.
    """
    trust_score: float
    complexity_index: int
    entropy_level: float
    sensitive_data_flags: List[str]

class ContextRiskAnalyzer:
    """
    Analyzes context snapshots to determine a risk level score.
    """
    
    @staticmethod
    def validate_input(context: ContextSnapshot) -> None:
        """Validate the context snapshot data."""
        if not (0.0 <= context.trust_score <= 1.0):
            raise ValueError(f"Trust score {context.trust_score} out of range [0.0, 1.0]")
        if context.complexity_index < 0:
            raise ValueError("Complexity index cannot be negative")
        if context.entropy_level < 0:
            raise ValueError("Entropy level cannot be negative")
            
    @staticmethod
    def _normalize_entropy(entropy: float) -> float:
        """Helper function to normalize entropy values to a 0.0-1.0 scale."""
        # Assuming entropy might be unbounded, we apply a sigmoid-like normalization
        if entropy < 0:
            return 0.0
        return 1 / (1 + math.exp(-0.5 * (entropy - 5)))

    def calculate_risk_score(self, context: ContextSnapshot) -> float:
        """
        Calculates a composite risk score based on context parameters.
        
        Args:
            context: The context snapshot to analyze.
            
        Returns:
            A float representing the risk level (0.0 = Safe, 1.0 = Critical).
            
        Raises:
            ValueError: If input validation fails.
        """
        try:
            self.validate_input(context)
            
            # Base risk is inverse of trust
            base_risk = 1.0 - context.trust_score
            
            # Complexity contribution (normalized)
            complexity_factor = min(context.complexity_index / 10.0, 1.0) * 0.3
            
            # Entropy contribution
            normalized_entropy = self._normalize_entropy(context.entropy_level)
            entropy_factor = normalized_entropy * 0.3
            
            # Sensitivity contribution
            sensitivity_weight = 0.2 if "PII" in context.sensitive_data_flags else 0.0
            sensitivity_weight += 0.2 if "CLASSIFIED" in context.sensitive_data_flags else 0.0
            
            total_risk = min(base_risk + complexity_factor + entropy_factor + sensitivity_weight, 1.0)
            
            logger.debug(f"Calculated risk score: {total_risk:.4f} for context.")
            return round(total_risk, 4)
            
        except Exception as e:
            logger.error(f"Risk calculation failed: {str(e)}")
            # Fail-safe: return maximum risk on error
            return 1.0

class DynamicRouter:
    """
    Routes execution flow based on calculated risk levels.
    """
    
    def __init__(self, low_risk_threshold: float = 0.3, high_risk_threshold: float = 0.7):
        """
        Initialize the router with risk thresholds.
        
        Args:
            low_risk_threshold: Below this, strategy is Aggressive.
            high_risk_threshold: Above this, strategy is Conservative.
        """
        if not (0 <= low_risk_threshold < high_risk_threshold <= 1.0):
            raise ValueError("Invalid threshold configuration.")
            
        self.low_threshold = low_risk_threshold
        self.high_threshold = high_risk_threshold
        self.analyzer = ContextRiskAnalyzer()
        logger.info(f"Router initialized with thresholds: Low={low_risk_threshold}, High={high_risk_threshold}")

    def determine_strategy(self, context: ContextSnapshot) -> RoutingStrategy:
        """
        Determines the routing strategy based on context risk.
        
        Args:
            context: The current context snapshot.
            
        Returns:
            The selected RoutingStrategy enum member.
        """
        risk_score = self.analyzer.calculate_risk_score(context)
        
        if risk_score < self.low_threshold:
            logger.info(f"Risk {risk_score} is low. Switching to AGGRESSIVE_ASSOCIATION.")
            return RoutingStrategy.AGGRESSIVE_ASSOCIATION
        elif risk_score > self.high_threshold:
            logger.warning(f"Risk {risk_score} is high. Switching to CONSERVATIVE_ISOLATION.")
            return RoutingStrategy.CONSERVATIVE_ISOLATION
        else:
            logger.info(f"Risk {risk_score} is moderate. Maintaining NEUTRAL strategy.")
            return RoutingStrategy.NEUTRAL

    def apply_routing_logic(self, strategy: RoutingStrategy, data_payload: Dict) -> Dict:
        """
        Applies the specific logic associated with the routing strategy.
        (Simulated for demonstration)
        
        Args:
            strategy: The chosen routing strategy.
            data_payload: The data to be processed.
            
        Returns:
            A dictionary containing the processing result and metadata.
        """
        result = {
            "original_payload_size": len(str(data_payload)),
            "strategy_used": strategy.name,
            "processed": False
        }
        
        if strategy == RoutingStrategy.AGGRESSIVE_ASSOCIATION:
            # In aggressive mode, we might link data to external graphs
            result["processed"] = True
            result["mode"] = "linked_external_context"
            
        elif strategy == RoutingStrategy.CONSERVATIVE_ISOLATION:
            # In conservative mode, we sandbox the execution
            result["processed"] = True
            result["mode"] = "sandboxed_isolated"
            
        else:
            # Neutral mode - standard processing
            result["processed"] = True
            result["mode"] = "standard_pipeline"
            
        return result

# --- Usage Example ---
if __name__ == "__main__":
    # Setup sample contexts
    safe_context = ContextSnapshot(
        trust_score=0.95,
        complexity_index=2,
        entropy_level=0.1,
        sensitive_data_flags=[]
    )
    
    risky_context = ContextSnapshot(
        trust_score=0.15,
        complexity_index=8,
        entropy_level=7.5,
        sensitive_data_flags=["PII", "FINANCIAL"]
    )

    # Initialize Router
    router = DynamicRouter()

    # Process Safe Context
    print("\n--- Processing Safe Context ---")
    strategy_safe = router.determine_strategy(safe_context)
    output_safe = router.apply_routing_logic(strategy_safe, {"query": "open_weather_data"})
    print(f"Result: {output_safe}")

    # Process Risky Context
    print("\n--- Processing Risky Context ---")
    strategy_risky = router.determine_strategy(risky_context)
    output_risky = router.apply_routing_logic(strategy_risky, {"query": "user_ssn_lookup"})
    print(f"Result: {output_risky}")