"""
Auto-Counterfactual Data Augmentation Verification Module

This module implements an automated system for generating counterfactual samples
to test the robustness of AI classification skills, particularly focusing on
long-tail distribution scenarios.
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerturbationType(Enum):
    """Types of perturbations for counterfactual generation"""
    COLOR_SHIFT = "color_shift"
    GEOMETRIC = "geometric"
    TEXTURE = "texture"
    CONTEXTUAL = "contextual"
    SEMANTIC = "semantic"


@dataclass
class CounterfactualSample:
    """Container for counterfactual samples"""
    original_label: str
    perturbed_label: Optional[str]
    perturbation_type: PerturbationType
    perturbation_magnitude: float
    latent_vector: np.ndarray
    confidence_score: float
    boundary_distance: float
    timestamp: str = datetime.now().isoformat()


class LatentSpacePerturber:
    """
    Handles latent space perturbations for counterfactual generation.
    Simulates potential vulnerabilities in classification boundaries.
    """
    
    def __init__(
        self,
        latent_dim: int = 128,
        perturbation_range: Tuple[float, float] = (-2.0, 2.0),
        random_seed: Optional[int] = None
    ):
        """
        Initialize the latent space perturber.
        
        Args:
            latent_dim: Dimension of the latent space
            perturbation_range: Range of perturbation values
            random_seed: Random seed for reproducibility
        """
        self.latent_dim = latent_dim
        self.perturbation_range = perturbation_range
        self.rng = np.random.RandomState(random_seed)
        
        # Validate parameters
        if latent_dim <= 0:
            raise ValueError("Latent dimension must be positive")
        if perturbation_range[0] >= perturbation_range[1]:
            raise ValueError("Invalid perturbation range")
            
        logger.info(f"Initialized LatentSpacePerturber with dim={latent_dim}")
    
    def generate_base_latent(self, class_label: str) -> np.ndarray:
        """
        Generate a base latent vector representing a class prototype.
        
        Args:
            class_label: Class label for prototype generation
            
        Returns:
            Normalized latent vector
        """
        # Simulate class-conditional latent distribution
        class_hash = hash(class_label) % (2**32)
        self.rng.seed(class_hash)
        
        base_vector = self.rng.randn(self.latent_dim)
        normalized = base_vector / np.linalg.norm(base_vector)
        
        logger.debug(f"Generated base latent for class '{class_label}'")
        return normalized
    
    def apply_perturbation(
        self,
        latent_vector: np.ndarray,
        perturbation_type: PerturbationType,
        magnitude: float
    ) -> np.ndarray:
        """
        Apply a specific type of perturbation to a latent vector.
        
        Args:
            latent_vector: Original latent vector
            perturbation_type: Type of perturbation to apply
            magnitude: Strength of perturbation
            
        Returns:
            Perturbed latent vector
        """
        # Validate inputs
        if not isinstance(latent_vector, np.ndarray):
            raise TypeError("latent_vector must be numpy array")
        if latent_vector.shape[0] != self.latent_dim:
            raise ValueError(f"Expected latent dim {self.latent_dim}, got {latent_vector.shape[0]}")
        if not 0 <= magnitude <= 1:
            raise ValueError("Magnitude must be between 0 and 1")
        
        # Generate perturbation based on type
        perturbation = self._generate_perturbation_vector(perturbation_type, magnitude)
        perturbed = latent_vector + perturbation
        
        # Normalize to unit sphere
        perturbed = perturbed / np.linalg.norm(perturbed)
        
        return perturbed
    
    def _generate_perturbation_vector(
        self,
        perturbation_type: PerturbationType,
        magnitude: float
    ) -> np.ndarray:
        """
        Generate a perturbation vector based on the specified type.
        
        Args:
            perturbation_type: Type of perturbation
            magnitude: Perturbation magnitude
            
        Returns:
            Perturbation vector
        """
        scale = magnitude * (self.perturbation_range[1] - self.perturbation_range[0])
        
        if perturbation_type == PerturbationType.COLOR_SHIFT:
            # Affects specific dimensions (simulating color channels)
            perturbation = np.zeros(self.latent_dim)
            color_dims = self.rng.choice(
                self.latent_dim, 
                size=max(1, self.latent_dim // 10),
                replace=False
            )
            perturbation[color_dims] = self.rng.uniform(-scale, scale, len(color_dims))
            
        elif perturbation_type == PerturbationType.GEOMETRIC:
            # Affects spatial dimensions
            perturbation = np.zeros(self.latent_dim)
            spatial_dims = self.rng.choice(
                self.latent_dim,
                size=max(1, self.latent_dim // 5),
                replace=False
            )
            perturbation[spatial_dims] = self.rng.normal(0, scale/2, len(spatial_dims))
            
        else:
            # General semantic perturbation
            perturbation = self.rng.randn(self.latent_dim) * scale
            
        return perturbation


class CounterfactualValidator:
    """
    Validates counterfactual samples and evaluates classifier robustness.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        boundary_threshold: float = 0.3
    ):
        """
        Initialize the validator.
        
        Args:
            confidence_threshold: Threshold for confidence score validation
            boundary_threshold: Threshold for boundary distance validation
        """
        self.confidence_threshold = confidence_threshold
        self.boundary_threshold = boundary_threshold
        self.validation_history: List[Dict] = []
        
        logger.info("Initialized CounterfactualValidator")
    
    def simulate_classifier(
        self,
        latent_vector: np.ndarray,
        true_class: str,
        class_list: List[str]
    ) -> Tuple[str, float]:
        """
        Simulate classifier prediction on a latent vector.
        
        Args:
            latent_vector: Input latent vector
            true_class: True class label
            class_list: List of possible class labels
            
        Returns:
            Tuple of (predicted_class, confidence_score)
        """
        # Simulate decision boundary proximity
        class_prototypes = {
            cls: LatentSpacePerturber(latent_dim=latent_vector.shape[0]).generate_base_latent(cls)
            for cls in class_list
        }
        
        # Calculate similarities
        similarities = {
            cls: np.dot(latent_vector, proto)
            for cls, proto in class_prototypes.items()
        }
        
        # Softmax normalization
        exp_sims = {cls: np.exp(sim) for cls, sim in similarities.items()}
        total = sum(exp_sims.values())
        probs = {cls: exp_sim/total for cls, exp_sim in exp_sims.items()}
        
        predicted_class = max(probs.keys(), key=lambda x: probs[x])
        confidence = probs[predicted_class]
        
        return predicted_class, confidence
    
    def validate_counterfactual(
        self,
        sample: CounterfactualSample,
        class_list: List[str]
    ) -> Dict[str, Union[bool, str, float]]:
        """
        Validate a counterfactual sample.
        
        Args:
            sample: Counterfactual sample to validate
            class_list: List of possible class labels
            
        Returns:
            Validation results dictionary
        """
        # Input validation
        if not isinstance(sample, CounterfactualSample):
            raise TypeError("sample must be CounterfactualSample instance")
        if not class_list:
            raise ValueError("class_list cannot be empty")
        
        # Simulate classification
        predicted, confidence = self.simulate_classifier(
            sample.latent_vector,
            sample.original_label,
            class_list
        )
        
        # Determine if prediction changed
        prediction_changed = predicted != sample.original_label
        
        # Check if confidence dropped significantly
        confidence_drop = confidence < self.confidence_threshold
        
        # Check boundary proximity
        boundary_violation = sample.boundary_distance < self.boundary_threshold
        
        # Overall vulnerability assessment
        is_vulnerable = prediction_changed or confidence_drop or boundary_violation
        
        result = {
            "sample_id": id(sample),
            "original_class": sample.original_label,
            "predicted_class": predicted,
            "prediction_changed": prediction_changed,
            "confidence_score": confidence,
            "confidence_drop": confidence_drop,
            "boundary_violation": boundary_violation,
            "is_vulnerable": is_vulnerable,
            "perturbation_type": sample.perturbation_type.value,
            "perturbation_magnitude": sample.perturbation_magnitude
        }
        
        self.validation_history.append(result)
        logger.info(f"Validated counterfactual: vulnerable={is_vulnerable}")
        
        return result
    
    def generate_robustness_report(self) -> Dict:
        """
        Generate a summary report of robustness testing.
        
        Returns:
            Dictionary containing robustness metrics
        """
        if not self.validation_history:
            logger.warning("No validation history available")
            return {}
        
        total_samples = len(self.validation_history)
        vulnerable_count = sum(1 for r in self.validation_history if r["is_vulnerable"])
        
        # Per-perturbation analysis
        perturbation_stats = {}
        for record in self.validation_history:
            ptype = record["perturbation_type"]
            if ptype not in perturbation_stats:
                perturbation_stats[ptype] = {"total": 0, "vulnerable": 0}
            perturbation_stats[ptype]["total"] += 1
            if record["is_vulnerable"]:
                perturbation_stats[ptype]["vulnerable"] += 1
        
        # Calculate vulnerability rates
        for ptype in perturbation_stats:
            stats = perturbation_stats[ptype]
            stats["vulnerability_rate"] = stats["vulnerable"] / stats["total"]
        
        report = {
            "total_samples_tested": total_samples,
            "vulnerable_samples": vulnerable_count,
            "overall_vulnerability_rate": vulnerable_count / total_samples,
            "perturbation_analysis": perturbation_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Generated robustness report: {vulnerable_count}/{total_samples} vulnerable")
        return report


def run_counterfactual_verification(
    target_skill: str,
    related_classes: List[str],
    num_samples: int = 20,
    latent_dim: int = 64
) -> Dict:
    """
    Main function to run counterfactual verification for a skill.
    
    Args:
        target_skill: The skill/class to verify
        related_classes: Related classes for confusion testing
        num_samples: Number of counterfactual samples to generate
        latent_dim: Dimension of latent space
        
    Returns:
        Verification results dictionary
        
    Example:
        >>> results = run_counterfactual_verification(
        ...     target_skill="apple",
        ...     related_classes=["orange", "banana", "blue_apple", "square_apple"],
        ...     num_samples=10
        ... )
        >>> print(results["robustness_report"]["overall_vulnerability_rate"])
    """
    logger.info(f"Starting counterfactual verification for skill: {target_skill}")
    
    # Initialize components
    perturber = LatentSpacePerturber(latent_dim=latent_dim, random_seed=42)
    validator = CounterfactualValidator()
    
    # Generate base latent for target skill
    base_latent = perturber.generate_base_latent(target_skill)
    
    # Generate counterfactual samples
    samples = []
    perturbation_types = list(PerturbationType)
    
    for i in range(num_samples):
        # Select random perturbation type and magnitude
        ptype = perturbation_types[i % len(perturbation_types)]
        magnitude = np.random.uniform(0.1, 0.9)
        
        # Apply perturbation
        perturbed_latent = perturber.apply_perturbation(
            base_latent, ptype, magnitude
        )
        
        # Create counterfactual sample
        sample = CounterfactualSample(
            original_label=target_skill,
            perturbed_label=None,  # Will be determined by classifier
            perturbation_type=ptype,
            perturbation_magnitude=magnitude,
            latent_vector=perturbed_latent,
            confidence_score=0.0,  # Will be updated
            boundary_distance=np.random.uniform(0.1, 0.5)  # Simulated
        )
        
        samples.append(sample)
    
    # Validate all samples
    all_classes = [target_skill] + related_classes
    validation_results = []
    
    for sample in samples:
        result = validator.validate_counterfactual(sample, all_classes)
        validation_results.append(result)
    
    # Generate robustness report
    robustness_report = validator.generate_robustness_report()
    
    # Compile final results
    final_results = {
        "target_skill": target_skill,
        "related_classes": related_classes,
        "samples_generated": num_samples,
        "validation_results": validation_results,
        "robustness_report": robustness_report,
        "recommendations": _generate_recommendations(robustness_report)
    }
    
    logger.info("Counterfactual verification completed")
    return final_results


def _generate_recommendations(report: Dict) -> List[str]:
    """
    Generate improvement recommendations based on robustness report.
    
    Args:
        report: Robustness report dictionary
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if not report:
        return ["Insufficient data for recommendations"]
    
    vuln_rate = report.get("overall_vulnerability_rate", 0)
    
    if vuln_rate > 0.5:
        recommendations.append(
            "CRITICAL: High vulnerability rate detected. "
            "Consider retraining with adversarial examples."
        )
    elif vuln_rate > 0.3:
        recommendations.append(
            "WARNING: Moderate vulnerability rate. "
            "Augment training data with boundary samples."
        )
    
    # Analyze perturbation-specific vulnerabilities
    pert_analysis = report.get("perturbation_analysis", {})
    for ptype, stats in pert_analysis.items():
        if stats.get("vulnerability_rate", 0) > 0.4:
            recommendations.append(
                f"High vulnerability to {ptype} perturbations. "
                f"Focus data augmentation on this aspect."
            )
    
    if not recommendations:
        recommendations.append(
            "Model shows good robustness. "
            "Continue monitoring with diverse test cases."
        )
    
    return recommendations


if __name__ == "__main__":
    # Example usage
    print("Running Counterfactual Verification Demo")
    print("=" * 50)
    
    results = run_counterfactual_verification(
        target_skill="apple_recognition",
        related_classes=["orange", "pear", "blue_apple", "square_apple"],
        num_samples=15,
        latent_dim=32
    )
    
    print(f"\nTarget Skill: {results['target_skill']}")
    print(f"Samples Generated: {results['samples_generated']}")
    print(f"Vulnerability Rate: {results['robustness_report']['overall_vulnerability_rate']:.2%}")
    print("\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  - {rec}")