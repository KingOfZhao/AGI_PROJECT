"""
Cross-Domain Deep Structural Mapping Engine

This module implements a cognitive component capable of identifying deep structural
similarities across different domains and performing safe knowledge mapping.
It focuses on extracting 'structural solutions' rather than surface-level analogies.

Key Features:
- Deep isomorphism detection
- False isomorphism filtering
- Safe operator extraction and injection
- Cross-domain knowledge transfer

Author: AGI System
Version: 1.0.0
"""

import logging
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from scipy.spatial.distance import cosine
from scipy.stats import pearsonr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MappingSafetyLevel(Enum):
    """Safety levels for cross-domain mappings."""
    SAFE = "safe"
    CONDITIONAL = "conditional"
    UNSAFE = "unsafe"
    INVALID = "invalid"


class IsomorphismType(Enum):
    """Types of detected isomorphism."""
    DEEP = "deep"
    SURFACE = "surface"
    NONE = "none"


@dataclass
class DomainFeature:
    """Represents a feature in a domain with its properties."""
    name: str
    value: Union[float, int, str]
    weight: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate feature data after initialization."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Feature name must be a non-empty string")
        if not 0 <= self.weight <= 1:
            raise ValueError("Weight must be between 0 and 1")


@dataclass
class StructuralMapping:
    """Represents a mapping between two domains."""
    source_domain: str
    target_domain: str
    isomorphism_type: IsomorphismType
    safety_level: MappingSafetyLevel
    confidence_score: float
    mapped_features: Dict[str, str]
    operator_transferability: float
    warnings: List[str]
    
    def is_transfer_safe(self) -> bool:
        """Check if the mapping is safe for knowledge transfer."""
        return (
            self.safety_level == MappingSafetyLevel.SAFE and
            self.isomorphism_type == IsomorphismType.DEEP and
            self.confidence_score >= 0.7
        )


class CrossDomainMapper:
    """
    Advanced cognitive component for identifying deep structural similarities
    between different domains and performing safe knowledge mapping.
    
    This class implements:
    - Feature extraction and normalization
    - Deep vs surface isomorphism detection
    - False isomorphism filtering
    - Safe operator transfer validation
    
    Example:
        >>> mapper = CrossDomainMapper()
        >>> medical_features = [DomainFeature("pulse_rate", 72, 0.8)]
        >>> industrial_features = [DomainFeature("vibration_freq", 50, 0.8)]
        >>> mapping = mapper.analyze_structural_similarity(
        ...     "medical", medical_features,
        ...     "industrial", industrial_features
        ... )
        >>> print(mapping.isomorphism_type)
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.75,
        safety_threshold: float = 0.6,
        deep_feature_weight: float = 0.7
    ):
        """
        Initialize the CrossDomainMapper.
        
        Args:
            similarity_threshold: Minimum similarity for mapping consideration
            safety_threshold: Minimum safety score for transfer
            deep_feature_weight: Weight given to deep features vs surface
        """
        self.similarity_threshold = similarity_threshold
        self.safety_threshold = safety_threshold
        self.deep_feature_weight = deep_feature_weight
        self._feature_cache: Dict[str, np.ndarray] = {}
        
        # Validate parameters
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        if not 0 <= safety_threshold <= 1:
            raise ValueError("Safety threshold must be between 0 and 1")
        if not 0 <= deep_feature_weight <= 1:
            raise ValueError("Deep feature weight must be between 0 and 1")
            
        logger.info(
            f"CrossDomainMapper initialized with thresholds: "
            f"similarity={similarity_threshold}, safety={safety_threshold}"
        )
    
    def _normalize_features(
        self,
        features: List[DomainFeature]
    ) -> np.ndarray:
        """
        Normalize domain features to a comparable vector representation.
        
        Args:
            features: List of domain features to normalize
            
        Returns:
            Normalized feature vector as numpy array
        """
        if not features:
            raise ValueError("Feature list cannot be empty")
            
        # Extract numeric values and weights
        values = []
        weights = []
        
        for feature in features:
            if isinstance(feature.value, (int, float)):
                values.append(float(feature.value))
                weights.append(feature.weight)
            else:
                # Handle non-numeric features by hashing
                hash_val = float(hash(str(feature.value)) % 10000) / 10000
                values.append(hash_val)
                weights.append(feature.weight * 0.5)  # Lower weight for non-numeric
        
        values_array = np.array(values)
        weights_array = np.array(weights)
        
        # Normalize values
        if values_array.max() > values_array.min():
            normalized = (values_array - values_array.min()) / (values_array.max() - values_array.min())
        else:
            normalized = np.zeros_like(values_array)
        
        # Apply weights
        weighted = normalized * weights_array
        
        return weighted
    
    def _calculate_structural_similarity(
        self,
        vector_a: np.ndarray,
        vector_b: np.ndarray
    ) -> Tuple[float, float]:
        """
        Calculate structural similarity between two feature vectors.
        
        Computes both cosine similarity and correlation-based similarity.
        
        Args:
            vector_a: First feature vector
            vector_b: Second feature vector
            
        Returns:
            Tuple of (cosine_similarity, correlation_similarity)
        """
        if len(vector_a) != len(vector_b):
            # Pad shorter vector with zeros
            max_len = max(len(vector_a), len(vector_b))
            vector_a = np.pad(vector_a, (0, max_len - len(vector_a)))
            vector_b = np.pad(vector_b, (0, max_len - len(vector_b)))
        
        # Cosine similarity
        if np.all(vector_a == 0) or np.all(vector_b == 0):
            cosine_sim = 0.0
        else:
            cosine_sim = 1 - cosine(vector_a, vector_b)
        
        # Correlation similarity
        if len(vector_a) > 2:
            corr_sim, _ = pearsonr(vector_a, vector_b)
            if np.isnan(corr_sim):
                corr_sim = 0.0
        else:
            corr_sim = cosine_sim
        
        return cosine_sim, corr_sim
    
    def _detect_false_isomorphism(
        self,
        source_features: List[DomainFeature],
        target_features: List[DomainFeature],
        similarity_scores: Tuple[float, float]
    ) -> Tuple[bool, List[str]]:
        """
        Detect false isomorphisms between domains.
        
        False isomorphisms occur when surface features appear similar but
        underlying causal structures differ significantly.
        
        Args:
            source_features: Features from source domain
            target_features: Features from target domain
            similarity_scores: Tuple of similarity scores
            
        Returns:
            Tuple of (is_false_isomorphism, list_of_warnings)
        """
        warnings = []
        is_false = False
        cosine_sim, corr_sim = similarity_scores
        
        # Check for large discrepancy between similarity measures
        if abs(cosine_sim - corr_sim) > 0.3:
            warnings.append(
                f"Large discrepancy between similarity measures: "
                f"cosine={cosine_sim:.3f}, correlation={corr_sim:.3f}"
            )
            is_false = True
        
        # Check for scale differences in numeric features
        source_numeric = [f.value for f in source_features if isinstance(f.value, (int, float))]
        target_numeric = [f.value for f in target_features if isinstance(f.value, (int, float))]
        
        if source_numeric and target_numeric:
            source_range = max(source_numeric) - min(source_numeric)
            target_range = max(target_numeric) - min(target_numeric)
            
            if source_range > 0 and target_range > 0:
                range_ratio = max(source_range, target_range) / min(source_range, target_range)
                if range_ratio > 10:
                    warnings.append(
                        f"Significant scale difference detected: ratio={range_ratio:.2f}"
                    )
                    is_false = True
        
        # Check for metadata inconsistencies
        source_meta = [f.metadata for f in source_features if f.metadata]
        target_meta = [f.metadata for f in target_features if f.metadata]
        
        if source_meta and target_meta:
            source_keys = set()
            target_keys = set()
            for meta in source_meta:
                source_keys.update(meta.keys())
            for meta in target_meta:
                target_keys.update(meta.keys())
            
            if len(source_keys.symmetric_difference(target_keys)) > len(source_keys) * 0.5:
                warnings.append("Metadata structures are significantly different")
                is_false = True
        
        return is_false, warnings
    
    def _determine_isomorphism_type(
        self,
        similarity_scores: Tuple[float, float],
        is_false: bool
    ) -> IsomorphismType:
        """
        Determine the type of isomorphism based on analysis results.
        
        Args:
            similarity_scores: Tuple of (cosine_similarity, correlation_similarity)
            is_false: Whether a false isomorphism was detected
            
        Returns:
            IsomorphismType enum value
        """
        if is_false:
            return IsomorphismType.NONE
        
        cosine_sim, corr_sim = similarity_scores
        avg_sim = (cosine_sim + corr_sim) / 2
        
        if avg_sim >= self.similarity_threshold:
            return IsomorphismType.DEEP
        elif avg_sim >= self.similarity_threshold * 0.6:
            return IsomorphismType.SURFACE
        else:
            return IsomorphismType.NONE
    
    def _calculate_safety_level(
        self,
        isomorphism_type: IsomorphismType,
        confidence: float,
        warnings: List[str]
    ) -> MappingSafetyLevel:
        """
        Calculate the safety level for knowledge transfer.
        
        Args:
            isomorphism_type: Type of detected isomorphism
            confidence: Confidence score of the mapping
            warnings: List of detected warnings
            
        Returns:
            MappingSafetyLevel enum value
        """
        if isomorphism_type == IsomorphismType.NONE:
            return MappingSafetyLevel.INVALID
        
        if isomorphism_type == IsomorphismType.SURFACE:
            return MappingSafetyLevel.UNSAFE
        
        # Deep isomorphism - check confidence and warnings
        if confidence >= 0.8 and len(warnings) == 0:
            return MappingSafetyLevel.SAFE
        elif confidence >= self.safety_threshold and len(warnings) <= 1:
            return MappingSafetyLevel.CONDITIONAL
        else:
            return MappingSafetyLevel.UNSAFE
    
    def extract_operator(
        self,
        domain_name: str,
        features: List[DomainFeature],
        operator_name: str
    ) -> Dict[str, Any]:
        """
        Extract an abstract operator from a domain for transfer.
        
        This function extracts the core logic/algorithm from a domain
        in a domain-agnostic format suitable for injection into another domain.
        
        Args:
            domain_name: Name of the source domain
            features: Domain features to analyze
            operator_name: Name/identifier of the operator to extract
            
        Returns:
            Dictionary containing the abstracted operator
            
        Raises:
            ValueError: If features are invalid or operator cannot be extracted
        """
        if not features:
            raise ValueError("Features list cannot be empty")
        
        if not operator_name or not isinstance(operator_name, str):
            raise ValueError("Operator name must be a non-empty string")
        
        logger.info(f"Extracting operator '{operator_name}' from domain '{domain_name}'")
        
        # Extract numeric patterns
        numeric_features = [
            f for f in features 
            if isinstance(f.value, (int, float))
        ]
        
        if not numeric_features:
            raise ValueError("No numeric features available for operator extraction")
        
        values = np.array([f.value for f in numeric_features])
        weights = np.array([f.weight for f in numeric_features])
        
        # Calculate operator parameters
        operator = {
            "name": operator_name,
            "source_domain": domain_name,
            "parameters": {
                "mean": float(np.average(values, weights=weights)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "trend": "increasing" if values[-1] > values[0] else "decreasing",
                "weighted_center": float(np.sum(values * weights) / np.sum(weights))
            },
            "feature_count": len(features),
            "extraction_confidence": float(np.mean(weights))
        }
        
        logger.info(f"Operator extracted successfully: {operator['parameters']}")
        return operator
    
    def inject_operator(
        self,
        operator: Dict[str, Any],
        target_domain: str,
        target_features: List[DomainFeature],
        scaling_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Inject an abstract operator into a target domain.
        
        This function safely transfers an extracted operator to a new domain,
        applying necessary transformations and safety checks.
        
        Args:
            operator: Previously extracted operator dictionary
            target_domain: Name of the target domain
            target_features: Features of the target domain
            scaling_factor: Optional manual scaling factor (auto-calculated if None)
            
        Returns:
            Dictionary containing injection results and transformed parameters
            
        Raises:
            ValueError: If operator or target features are invalid
            RuntimeError: If injection fails safety checks
        """
        if not operator or "parameters" not in operator:
            raise ValueError("Invalid operator: missing parameters")
        
        if not target_features:
            raise ValueError("Target features list cannot be empty")
        
        logger.info(
            f"Injecting operator '{operator.get('name', 'unknown')}' "
            f"into domain '{target_domain}'"
        )
        
        # Get target domain statistics
        target_numeric = [
            f.value for f in target_features 
            if isinstance(f.value, (int, float))
        ]
        
        if not target_numeric:
            raise ValueError("No numeric features in target domain")
        
        target_values = np.array(target_numeric)
        target_min = np.min(target_values)
        target_max = np.max(target_values)
        target_range = target_max - target_min
        
        # Calculate scaling factor if not provided
        if scaling_factor is None:
            source_range = operator["parameters"]["max"] - operator["parameters"]["min"]
            if source_range > 0 and target_range > 0:
                scaling_factor = target_range / source_range
            else:
                scaling_factor = 1.0
        
        # Transform operator parameters
        transformed_params = {}
        source_params = operator["parameters"]
        
        for key, value in source_params.items():
            if isinstance(value, (int, float)):
                # Scale and shift to target domain
                transformed = value * scaling_factor
                transformed = max(target_min, min(target_max, transformed))
                transformed_params[key] = float(transformed)
            else:
                transformed_params[key] = value
        
        # Calculate injection confidence
        source_confidence = operator.get("extraction_confidence", 0.5)
        injection_confidence = source_confidence * (1 - abs(1 - scaling_factor) * 0.5)
        
        result = {
            "operator_name": operator.get("name", "unknown"),
            "source_domain": operator.get("source_domain", "unknown"),
            "target_domain": target_domain,
            "scaling_factor": scaling_factor,
            "original_parameters": source_params,
            "transformed_parameters": transformed_params,
            "injection_confidence": injection_confidence,
            "warnings": []
        }
        
        # Add warnings for potential issues
        if scaling_factor > 5 or scaling_factor < 0.2:
            result["warnings"].append(
                f"Extreme scaling factor ({scaling_factor:.2f}) may affect accuracy"
            )
        
        if injection_confidence < 0.5:
            result["warnings"].append(
                f"Low injection confidence ({injection_confidence:.3f})"
            )
        
        logger.info(f"Operator injection complete with confidence {injection_confidence:.3f}")
        return result
    
    def analyze_structural_similarity(
        self,
        source_domain: str,
        source_features: List[DomainFeature],
        target_domain: str,
        target_features: List[DomainFeature]
    ) -> StructuralMapping:
        """
        Analyze structural similarity between two domains.
        
        This is the main entry point for cross-domain analysis, performing
        deep isomorphism detection and safety assessment.
        
        Args:
            source_domain: Name of the source domain
            source_features: List of features from source domain
            target_domain: Name of the target domain
            target_features: List of features from target domain
            
        Returns:
            StructuralMapping object containing complete analysis results
            
        Raises:
            ValueError: If input validation fails
        """
        # Input validation
        if not source_domain or not isinstance(source_domain, str):
            raise ValueError("Source domain must be a non-empty string")
        if not target_domain or not isinstance(target_domain, str):
            raise ValueError("Target domain must be a non-empty string")
        if not source_features:
            raise ValueError("Source features cannot be empty")
        if not target_features:
            raise ValueError("Target features cannot be empty")
        
        logger.info(
            f"Analyzing structural similarity: "
            f"'{source_domain}' -> '{target_domain}'"
        )
        
        try:
            # Normalize features
            source_vector = self._normalize_features(source_features)
            target_vector = self._normalize_features(target_features)
            
            # Calculate similarity scores
            similarity_scores = self._calculate_structural_similarity(
                source_vector, target_vector
            )
            
            # Detect false isomorphisms
            is_false, warnings = self._detect_false_isomorphism(
                source_features, target_features, similarity_scores
            )
            
            # Determine isomorphism type
            isomorphism_type = self._determine_isomorphism_type(
                similarity_scores, is_false
            )
            
            # Calculate confidence score
            confidence = (similarity_scores[0] + similarity_scores[1]) / 2
            if isomorphism_type == IsomorphismType.DEEP:
                confidence *= 1.2  # Boost for deep isomorphism
            confidence = min(1.0, confidence)
            
            # Determine safety level
            safety_level = self._calculate_safety_level(
                isomorphism_type, confidence, warnings
            )
            
            # Create feature mapping
            mapped_features = {}
            for i, sf in enumerate(source_features):
                if i < len(target_features):
                    mapped_features[sf.name] = target_features[i].name
            
            # Calculate operator transferability
            transferability = confidence if safety_level == MappingSafetyLevel.SAFE else 0.0
            
            mapping = StructuralMapping(
                source_domain=source_domain,
                target_domain=target_domain,
                isomorphism_type=isomorphism_type,
                safety_level=safety_level,
                confidence_score=confidence,
                mapped_features=mapped_features,
                operator_transferability=transferability,
                warnings=warnings
            )
            
            logger.info(
                f"Analysis complete: isomorphism={isomorphism_type.value}, "
                f"safety={safety_level.value}, confidence={confidence:.3f}"
            )
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error during structural analysis: {str(e)}")
            raise RuntimeError(f"Structural analysis failed: {str(e)}")


# Example usage and demonstration
if __name__ == "__main__":
    """
    Example demonstrating the Cross-Domain Mapping Engine.
    
    This example shows how medical pulse diagnosis concepts can be
    mapped to industrial equipment vibration analysis.
    """
    
    print("=" * 60)
    print("Cross-Domain Structural Mapping Engine - Demo")
    print("=" * 60)
    
    # Initialize the mapper
    mapper = CrossDomainMapper(
        similarity_threshold=0.7,
        safety_threshold=0.6
    )
    
    # Define medical domain features (pulse diagnosis)
    medical_features = [
        DomainFeature("resting_rate", 72, 0.9, {"unit": "bpm", "type": "frequency"}),
        DomainFeature("variability", 0.15, 0.8, {"unit": "ratio", "type": "variance"}),
        DomainFeature("peak_amplitude", 1.2, 0.7, {"unit": "normalized", "type": "amplitude"}),
        DomainFeature("recovery_time", 2.5, 0.6, {"unit": "seconds", "type": "temporal"}),
        DomainFeature("pattern_regularity", 0.85, 0.85, {"unit": "ratio", "type": "structure"})
    ]
    
    # Define industrial domain features (vibration analysis)
    industrial_features = [
        DomainFeature("baseline_frequency", 50, 0.9, {"unit": "Hz", "type": "frequency"}),
        DomainFeature("amplitude_variance", 0.12, 0.8, {"unit": "ratio", "type": "variance"}),
        DomainFeature("peak_magnitude", 1.5, 0.7, {"unit": "normalized", "type": "amplitude"}),
        DomainFeature("damping_time", 3.0, 0.6, {"unit": "seconds", "type": "temporal"}),
        DomainFeature("pattern_consistency", 0.82, 0.85, {"unit": "ratio", "type": "structure"})
    ]
    
    # Analyze structural similarity
    print("\n1. Analyzing Structural Similarity...")
    print("-" * 40)
    
    mapping = mapper.analyze_structural_similarity(
        source_domain="medical_pulse_diagnosis",
        source_features=medical_features,
        target_domain="industrial_vibration_analysis",
        target_features=industrial_features
    )
    
    print(f"Source Domain: {mapping.source_domain}")
    print(f"Target Domain: {mapping.target_domain}")
    print(f"Isomorphism Type: {mapping.isomorphism_type.value}")
    print(f"Safety Level: {mapping.safety_level.value}")
    print(f"Confidence Score: {mapping.confidence_score:.3f}")
    print(f"Operator Transferability: {mapping.operator_transferability:.3f}")
    print(f"Mapped Features: {mapping.mapped_features}")
    
    if mapping.warnings:
        print(f"Warnings: {mapping.warnings}")
    
    # Extract operator from medical domain
    print("\n2. Extracting Operator from Medical Domain...")
    print("-" * 40)
    
    operator = mapper.extract_operator(
        domain_name="medical_pulse_diagnosis",
        features=medical_features,
        operator_name="pulse_pattern_analyzer"
    )
    
    print(f"Operator Name: {operator['name']}")
    print(f"Source Domain: {operator['source_domain']}")
    print(f"Parameters: {operator['parameters']}")
    print(f"Extraction Confidence: {operator['extraction_confidence']:.3f}")
    
    # Inject operator into industrial domain
    print("\n3. Injecting Operator into Industrial Domain...")
    print("-" * 40)
    
    injection_result = mapper.inject_operator(
        operator=operator,
        target_domain="industrial_vibration_analysis",
        target_features=industrial_features
    )
    
    print(f"Target Domain: {injection_result['target_domain']}")
    print(f"Scaling Factor: {injection_result['scaling_factor']:.3f}")
    print(f"Original Parameters: {injection_result['original_parameters']}")
    print(f"Transformed Parameters: {injection_result['transformed_parameters']}")
    print(f"Injection Confidence: {injection_result['injection_confidence']:.3f}")
    
    if injection_result['warnings']:
        print(f"Warnings: {injection_result['warnings']}")
    
    # Test transfer safety
    print("\n4. Transfer Safety Check...")
    print("-" * 40)
    
    if mapping.is_transfer_safe():
        print("✓ Mapping is SAFE for knowledge transfer")
        print("  Operator can be safely injected into target domain")
    else:
        print("✗ Mapping is NOT safe for direct transfer")
        print(f"  Reason: Safety level is '{mapping.safety_level.value}'")
        if mapping.warnings:
            print(f"  Issues: {', '.join(mapping.warnings)}")
    
    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)