"""
Skeptical Causal Inverter Module.

This module implements a 'Skeptical Causal Inverter' designed for AGI systems.
Unlike traditional inverse dynamics models that output a single deterministic
solution, this module acknowledges the inherent uncertainty in inferring causes
from effects (Humean skepticism). It outputs a 'Causal Confidence Distribution'
over a set of 'Hidden Variable Hypotheses'.

This approach prevents the AGI from overfitting to a single explanation and
enhances robustness in scenarios with missing data or ambiguous causality.

Classes:
    CausalHypothesis: Represents a potential cause with its associated confidence.
    SkepticalCausalInverter: Main engine for performing skeptical causal inversion.

Functions:
    normalize_distribution: Helper function to normalize probability vectors.
    generate_hypothesis_pool: Core logic to generate potential causes.
    compute_skeptical_distribution: Core logic to apply skepticism and calculate confidence.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkepticalCausalInverter")


@dataclass
class CausalHypothesis:
    """
    Represents a single hypothesis regarding the cause of an observed effect.

    Attributes:
        name (str): Identifier for the hypothesis (e.g., 'Applied_Force', 'Wind_Gust').
        raw_score (float): The initial likelihood score based on physical models.
        confidence (float): The final confidence score after applying skepticism.
        metadata (Dict[str, Any]): Additional context or parameters for the hypothesis.
    """
    name: str
    raw_score: float
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.raw_score < 0:
            logger.warning(f"Hypothesis {self.name} has negative raw_score. Clamping to 0.")
            self.raw_score = 0.0


class SkepticalCausalInverter:
    """
    A class that performs inverse dynamics with a layer of epistemological skepticism.

    Instead of returning a single 'true' cause, it returns a distribution of
    probabilities across multiple plausible causes, weighted by evidence but
    dampened by a 'skeptical factor' to account for unknown unknowns.

    Attributes:
        skepticism_level (float): A value between 0.0 (deterministic) and 1.0 (total uncertainty).
                                  Higher values increase the entropy of the output distribution.
        entropy_threshold (float): Minimum entropy required to accept a distribution.
    """

    def __init__(self, skepticism_level: float = 0.3, entropy_threshold: float = 0.5):
        """
        Initialize the inverter.

        Args:
            skepticism_level (float): Degree of uncertainty to inject (0.0 to 1.0).
            entropy_threshold (float): Minimum entropy for a valid distribution.

        Raises:
            ValueError: If skepticism_level is not between 0 and 1.
        """
        self._validate_params(skepticism_level, entropy_threshold)
        self.skepticism_level = skepticism_level
        self.entropy_threshold = entropy_threshold
        logger.info(f"SkepticalCausalInverter initialized with skepticism={skepticism_level}")

    def _validate_params(self, skepticism: float, threshold: float) -> None:
        """Validate initialization parameters."""
        if not (0.0 <= skepticism <= 1.0):
            raise ValueError("skepticism_level must be between 0.0 and 1.0")
        if threshold < 0:
            raise ValueError("entropy_threshold cannot be negative")

    def _validate_input(self, observation_vector: List[float]) -> None:
        """
        Validate the input observation vector.

        Args:
            observation_vector (List[float]): The observed state changes.

        Raises:
            ValueError: If input is empty or contains non-finite values.
        """
        if not observation_vector:
            raise ValueError("Observation vector cannot be empty.")
        if any(not math.isfinite(x) for x in observation_vector):
            raise ValueError("Observation vector contains non-finite values (NaN or Inf).")

    def _normalize_distribution(self, scores: List[float]) -> List[float]:
        """
        Helper function to normalize a list of scores to sum to 1.0.

        Args:
            scores (List[float]): List of raw scores.

        Returns:
            List[float]: Normalized probabilities.
        """
        total = sum(scores)
        if total == 0:
            # Uniform distribution if total score is zero
            return [1.0 / len(scores)] * len(scores)
        return [s / total for s in scores]

    def _generate_hypothesis_pool(
        self,
        observation: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[CausalHypothesis]:
        """
        Core Function 1: Generate a pool of potential causal hypotheses.

        Based on the magnitude and direction of the observation vector, it proposes
        various physical or abstract causes (e.g., Direct Force, Friction, Noise).

        Args:
            observation (List[float]): The observed effect (e.g., change in velocity).
            context (Optional[Dict[str, Any]]): Environmental context (e.g., 'windy').

        Returns:
            List[CausalHypothesis]: A list of generated hypotheses with raw scores.
        """
        context = context or {}
        magnitude = math.sqrt(sum(x**2 for x in observation))
        hypotheses = []

        # Hypothesis 1: Direct Action (The most obvious cause)
        # Score correlates with magnitude
        h1_score = min(magnitude, 1.0)
        hypotheses.append(CausalHypothesis(
            name="Direct_Applied_Force",
            raw_score=h1_score,
            metadata={"type": "intentional", "vector": observation}
        ))

        # Hypothesis 2: Environmental Factors (e.g., Wind, Gravity)
        # Score boosted if context suggests it
        env_score = 0.1
        if context.get("weather") == "windy":
            env_score += 0.4
        if magnitude > 0.5:
            env_score += 0.2
        hypotheses.append(CausalHypothesis(
            name="Environmental_Drift",
            raw_score=env_score,
            metadata={"type": "external", "factors": context.get("weather", "calm")}
        ))

        # Hypothesis 3: Measurement Noise / Sensor Error
        # Higher if magnitude is very small (likely noise)
        noise_score = 1.0 - min(magnitude * 2, 0.9)
        hypotheses.append(CausalHypothesis(
            name="Sensor_Noise",
            raw_score=noise_score,
            metadata={"type": "error", "variance": 0.05}
        ))

        # Hypothesis 4: Hidden Systemic Lag (Delayed reaction)
        # Randomized slightly to simulate uncertainty about hidden states
        lag_score = random.uniform(0.1, 0.3)
        hypotheses.append(CausalHypothesis(
            name="Hidden_State_Lag",
            raw_score=lag_score,
            metadata={"type": "latent", "delay": "unknown"}
        ))

        logger.debug(f"Generated {len(hypotheses)} raw hypotheses.")
        return hypotheses

    def _compute_skeptical_distribution(
        self,
        hypotheses: List[CausalHypothesis]
    ) -> List[CausalHypothesis]:
        """
        Core Function 2: Apply skepticism to raw scores to generate final confidence.

        This function implements the 'Humean' aspect. It takes the raw likelihoods
        and blends them with a uniform distribution based on the skepticism_level.
        This ensures that even if one cause seems dominant, we reserve some
        probability mass for 'unknown' or 'other' causes.

        Args:
            hypotheses (List[CausalHypothesis]): The list of hypotheses with raw scores.

        Returns:
            List[CausalHypothesis]: Updated hypotheses with final confidence scores.
        """
        raw_scores = [h.raw_score for h in hypotheses]
        normalized_probs = self._normalize_distribution(raw_scores)
        n = len(hypotheses)

        # Apply skepticism: Blend the calculated probability with a uniform distribution
        # P_final = (1 - alpha) * P_calc + alpha * (1/n)
        # Where alpha is skepticism_level
        final_confidences = []
        for p in normalized_probs:
            skeptical_p = (1 - self.skepticism_level) * p + (self.skepticism_level / n)
            final_confidences.append(skeptical_p)

        # Update hypothesis objects
        for i, h in enumerate(hypotheses):
            h.confidence = final_confidences[i]

        # Calculate Shannon Entropy of the resulting distribution
        entropy = -sum([p * math.log(p) for p in final_confidences if p > 0])
        logger.info(f"Distribution Entropy: {entropy:.4f} (Threshold: {self.entropy_threshold})")

        if entropy < self.entropy_threshold:
            logger.warning("Low entropy detected. The system might be overfitting to a single cause.")

        return hypotheses

    def invert(
        self,
        observation_vector: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[CausalHypothesis]:
        """
        Main entry point for the inversion process.

        Input Format:
            observation_vector: List[float] (e.g., [dx, dy, dz] representing change in state).
            context: Dict[str, Any] (e.g., {'surface': 'ice', 'weather': 'windy'}).

        Output Format:
            List[CausalHypothesis]: Sorted list of hypotheses, highest confidence first.

        Example:
            >>> inverter = SkepticalCausalInverter(skepticism_level=0.4)
            >>> result = inverter.invert([0.8, 0.2, 0.0], context={'weather': 'windy'})
            >>> for h in result:
            ...     print(f"{h.name}: {h.confidence:.2f}")
        """
        try:
            self._validate_input(observation_vector)
            logger.info(f"Processing observation: {observation_vector}")

            # Step 1: Generate potential causes
            raw_hypotheses = self._generate_hypothesis_pool(observation_vector, context)

            # Step 2: Apply skeptical reasoning
            final_hypotheses = self._compute_skeptical_distribution(raw_hypotheses)

            # Sort by confidence descending
            final_hypotheses.sort(key=lambda x: x.confidence, reverse=True)

            return final_hypotheses

        except Exception as e:
            logger.error(f"Error during causal inversion: {e}")
            raise


# Example Usage
if __name__ == "__main__":
    # Setup
    inverter = SkepticalCausalInverter(skepticism_level=0.3)

    # Scenario 1: Strong movement in calm conditions
    print("--- Scenario 1: Strong Push ---")
    obs1 = [0.9, 0.1, 0.0]
    ctx1 = {"weather": "calm"}
    results1 = inverter.invert(obs1, ctx1)
    for h in results1:
        print(f"{h.name:<20} | Confidence: {h.confidence:.4f} | Raw: {h.raw_score:.4f}")

    # Scenario 2: Slight movement in windy conditions (Ambiguous)
    print("\n--- Scenario 2: Ambiguous Drift ---")
    obs2 = [0.2, 0.05, 0.0]
    ctx2 = {"weather": "windy"}
    results2 = inverter.invert(obs2, ctx2)
    for h in results2:
        print(f"{h.name:<20} | Confidence: {h.confidence:.4f} | Raw: {h.raw_score:.4f}")

    # Scenario 3: Near zero movement (Likely noise)
    print("\n--- Scenario 3: Noise ---")
    obs3 = [0.01, 0.0, 0.0]
    results3 = inverter.invert(obs3)
    for h in results3:
        print(f"{h.name:<20} | Confidence: {h.confidence:.4f} | Raw: {h.raw_score:.4f}")