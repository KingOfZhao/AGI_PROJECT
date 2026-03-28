"""
Module: auto_自下而上归纳中的_噪声滤波器_有效性_当_3db549

Description:
    Implements a statistical filter for bottom-up induction in AGI systems.
    It distinguishes between 'accidental success' (noise) and 'reproducible patterns'
    (signal) when inducting new nodes from massive practical data.

    Core Logic:
    A candidate node is considered valid only if:
    1. It appears in at least 3 independent contexts.
    2. The statistical confidence of its success rate being significant is p < 0.05.

Author: Senior Python Engineer (AGI Division)
Date: 2023-10-27
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NodeObservation:
    """
    Represents a single observation of a candidate node's performance.

    Attributes:
        context_id (str): Unique identifier for the independent context (e.g., session, environment).
        successes (int): Number of successful outcomes in this context.
        trials (int): Total number of trials in this context.
    """
    context_id: str
    successes: int
    trials: int


class InductionFilter:
    """
    Filters candidate nodes based on reproducibility and statistical significance.

    Logic:
    1. Reproducibility: Checks if the node appears in >= 3 distinct contexts.
    2. Significance: Aggregates data and performs a Binomial Test (normal approximation)
       to ensure success rate is significantly better than a baseline (noise threshold).
    """

    def __init__(self, noise_threshold: float = 0.5, alpha: float = 0.05, min_contexts: int = 3):
        """
        Initialize the filter.

        Args:
            noise_threshold (float): The baseline random probability of success (H0).
            alpha (float): Significance level (default 0.05).
            min_contexts (int): Minimum number of independent contexts required (default 3).
        """
        if not 0.0 <= noise_threshold <= 1.0:
            raise ValueError("Noise threshold must be between 0 and 1.")
        if not 0.0 < alpha < 1.0:
            raise ValueError("Alpha must be between 0 and 1.")
        if min_contexts < 1:
            raise ValueError("Minimum contexts must be at least 1.")

        self.noise_threshold = noise_threshold
        self.alpha = alpha
        self.min_contexts = min_contexts
        logger.info(
            f"InductionFilter initialized: baseline={noise_threshold}, "
            f"alpha={alpha}, min_contexts={min_contexts}"
        )

    def _calculate_z_score(self, total_successes: int, total_trials: int) -> Optional[float]:
        """
        Helper function to calculate Z-score for one-sided binomial test.

        H0: p <= noise_threshold (The observed success is just noise/luck)
        H1: p > noise_threshold (The observed success is a real pattern)

        Args:
            total_successes (int): Sum of successes across contexts.
            total_trials (int): Sum of trials across contexts.

        Returns:
            Optional[float]: Z-score, or None if division by zero occurs.
        """
        if total_trials == 0:
            return None

        p_observed = total_successes / total_trials
        p_null = self.noise_threshold

        # Standard error under null hypothesis
        # SE = sqrt( p * (1-p) / n )
        variance = p_null * (1 - p_null)
        if variance == 0 or total_trials == 0:
            return None
        
        std_error = math.sqrt(variance / total_trials)
        
        if std_error == 0:
            return 0.0

        z_score = (p_observed - p_null) / std_error
        return z_score

    def _z_to_p_value(self, z_score: float) -> float:
        """
        Approximate one-tailed p-value from Z-score using error function (erf).
        Standard normal CDF approximation.

        Args:
            z_score (float): The calculated Z-score.

        Returns:
            float: p-value.
        """
        # Approximation constants
        # Using Abramowitz and Stegun approximation for Normal CDF
        # P(Z < z) ~= 1 - phi(z) * (b1*t + b2*t^2 + b3*t^3 + b4*t^4 + b5*t^5)
        # Here we use Python's math.erf for higher precision
        # CDF = 0.5 * (1 + erf(z / sqrt(2)))
        # We want P(Z > z_score) for one-sided test
        cdf = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        p_value = 1 - cdf
        return p_value

    def validate_node(self, observations: List[NodeObservation]) -> Tuple[bool, dict]:
        """
        Validates a candidate node based on observations.

        Args:
            observations (List[NodeObservation]): List of observations from different contexts.

        Returns:
            Tuple[bool, dict]: (is_valid, metadata_dict)
                               metadata contains stats like z_score, p_value, distinct_contexts.
        """
        if not observations:
            logger.warning("Empty observation list provided.")
            return False, {"reason": "No data provided"}

        # 1. Data Validation & Aggregation
        unique_contexts = set()
        total_successes = 0
        total_trials = 0

        for obs in observations:
            if obs.trials < 0 or obs.successes < 0:
                logger.error(f"Invalid data counts in context {obs.context_id}")
                raise ValueError("Trials and successes must be non-negative.")
            if obs.successes > obs.trials:
                logger.error(f"Successes exceed trials in context {obs.context_id}")
                raise ValueError("Successes cannot exceed trials.")
            
            unique_contexts.add(obs.context_id)
            total_successes += obs.successes
            total_trials += obs.trials

        num_contexts = len(unique_contexts)
        
        meta = {
            "total_successes": total_successes,
            "total_trials": total_trials,
            "distinct_contexts": num_contexts,
            "reason": ""
        }

        # 2. Reproducibility Check (Context Threshold)
        if num_contexts < self.min_contexts:
            meta["reason"] = f"Insufficient contexts: {num_contexts} < {self.min_contexts}"
            logger.info(f"Node rejected: {meta['reason']}")
            return False, meta

        # 3. Statistical Significance Check (Z-test)
        # Avoid testing on zero trials
        if total_trials == 0:
            meta["reason"] = "Zero total trials"
            return False, meta

        z_score = self._calculate_z_score(total_successes, total_trials)
        if z_score is None:
            meta["reason"] = "Statistical calculation error (zero variance)"
            return False, meta

        p_value = self._z_to_p_value(z_score)
        
        meta["z_score"] = z_score
        meta["p_value"] = p_value

        logger.debug(f"Stats: Z={z_score:.4f}, p={p_value:.4f}")

        if p_value < self.alpha:
            meta["reason"] = "Valid pattern"
            logger.info(f"Node ACCEPTED: p={p_value:.6f} < {self.alpha}")
            return True, meta
        else:
            meta["reason"] = f"Not significant: p={p_value:.6f} >= {self.alpha}"
            logger.info(f"Node rejected: {meta['reason']}")
            return False, meta


# --- Usage Example ---
if __name__ == "__main__":
    # Scenario: We are testing a new 'Skill' (node) found by the AGI system.
    # Hypothesis: This skill succeeds 60% of the time, while random noise succeeds 50% of the time.
    
    # Create dummy data
    # Case 1: A valid pattern (appears in 3 contexts, high success rate)
    valid_observations = [
        NodeObservation(context_id="env_A", successes=15, trials=20),
        NodeObservation(context_id="env_B", successes=16, trials=20),
        NodeObservation(context_id="env_C", successes=14, trials=20),
    ]

    # Case 2: Noise / Coincidence (appears in only 1 context, even if success is high)
    noise_observations = [
        NodeObservation(context_id="env_X", successes=100, trials=100),
    ]
    
    # Case 3: Frequent but not significant (3 contexts, but success rate is near baseline)
    fluke_observations = [
        NodeObservation(context_id="env_1", successes=5, trials=10),
        NodeObservation(context_id="env_2", successes=6, trials=10),
        NodeObservation(context_id="env_3", successes=4, trials=10),
    ]

    # Initialize Filter (Baseline 50%, Alpha 0.05, Min 3 contexts)
    try:
        filter_engine = InductionFilter(noise_threshold=0.5, alpha=0.05, min_contexts=3)
        
        print("\n--- Testing Valid Pattern ---")
        is_valid, stats = filter_engine.validate_node(valid_observations)
        print(f"Result: {is_valid}")
        print(f"Stats: {stats}")

        print("\n--- Testing Noise (Insufficient Contexts) ---")
        is_valid, stats = filter_engine.validate_node(noise_observations)
        print(f"Result: {is_valid}")
        print(f"Reason: {stats['reason']}")

        print("\n--- Testing Fluke (Statistically Insignificant) ---")
        is_valid, stats = filter_engine.validate_node(fluke_observations)
        print(f"Result: {is_valid}")
        print(f"Reason: {stats['reason']}")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.critical(f"Unexpected runtime error: {e}", exc_info=True)