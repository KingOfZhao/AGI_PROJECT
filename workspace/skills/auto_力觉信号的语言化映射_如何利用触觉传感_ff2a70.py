"""
Module: auto_力觉信号的语言化映射_如何利用触觉传感_ff2a70
Description: Mapping High-Dimensional Tactile Signals to Natural Language Semantics.
Author: Senior Python Engineer (AGI System Component)
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Enums ---

class TactileMetric(Enum):
    """Enumeration of quantifiable tactile metrics."""
    NORMAL_FORCE = "normal_force"
    VIBRATION_INTENSITY = "vibration_intensity"
    VIBRATION_FREQUENCY = "vibration_frequency"
    SHEAR_FORCE = "shear_force"
    TEMPERATURE_DELTA = "temperature_delta"

class SemanticLabel(Enum):
    """Pre-defined semantic labels for haptic sensations."""
    SMOOTH = "手感顺滑"
    ROUGH = "表面粗糙"
    STICKY = "粘滞感强"
    SLIPPERY = "过于湿滑"
    RESISTANT = "阻力适中"
    HARD = "触感坚硬"
    SOFT = "触感柔软"

@dataclass
class TactileSample:
    """
    Represents a single timestamped sample of tactile sensor data.
    
    Attributes:
        timestamp (float): Time of capture in seconds.
        sensor_data (Dict[TactileMetric, float]): Multi-dimensional sensor readings.
    """
    timestamp: float
    sensor_data: Dict[TactileMetric, float] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validates the sensor data boundaries."""
        for metric, value in self.sensor_data.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid type for {metric}: {type(value)}")
            if metric == TactileMetric.NORMAL_FORCE and value < 0:
                logger.warning("Negative normal force detected, setting to 0.")
                self.sensor_data[metric] = 0.0
        return True

@dataclass
class SemanticMapping:
    """
    Defines a rule to map a metric range to a semantic concept.
    
    Attributes:
        metric (TactileMetric): The metric to evaluate.
        range_val (Tuple[float, float]): The (min, max) inclusive range.
        label (SemanticLabel): The semantic label to apply.
        confidence (float): Base confidence weight for this rule.
    """
    metric: TactileMetric
    range_val: Tuple[float, float]
    label: SemanticLabel
    confidence: float = 1.0

class HapticSemanticMapper:
    """
    Core Class: HapticSemanticMapper
    
    Maps high-dimensional tactile data to natural language descriptions.
    It implements a weighted decision logic based on semantic rules.
    """

    def __init__(self, mapping_rules: Optional[List[SemanticMapping]] = None):
        """
        Initialize the mapper with optional custom rules.
        
        Args:
            mapping_rules (Optional[List[SemanticMapping]]): Custom mapping rules.
        """
        self._rules = mapping_rules if mapping_rules else self._default_rules()
        logger.info(f"HapticSemanticMapper initialized with {len(self._rules)} rules.")

    def _default_rules(self) -> List[SemanticMapping]:
        """Generates default heuristics for common industrial scenarios."""
        return [
            # Smoothness: Low vibration intensity
            SemanticMapping(TactileMetric.VIBRATION_INTENSITY, (0.0, 0.3), SemanticLabel.SMOOTH, 0.9),
            # Roughness: High vibration intensity
            SemanticMapping(TactileMetric.VIBRATION_INTENSITY, (0.7, 1.5), SemanticLabel.ROUGH, 0.9),
            # Resistance: Moderate Normal Force
            SemanticMapping(TactileMetric.NORMAL_FORCE, (5.0, 15.0), SemanticLabel.RESISTANT, 0.8),
            # Stickiness: High Shear Force relative to Normal Force (Simplified)
            SemanticMapping(TactileMetric.SHEAR_FORCE, (10.0, 50.0), SemanticLabel.STICKY, 0.7),
            # Softness: Low Normal Force
            SemanticMapping(TactileMetric.NORMAL_FORCE, (0.1, 3.0), SemanticLabel.SOFT, 0.6)
        ]

    def _normalize_data(self, sample: TactileSample) -> Dict[TactileMetric, float]:
        """
        Helper: Normalizes raw sensor data into a standard range [0, 1] or similar.
        
        Args:
            sample (TactileSample): Raw tactile data.
            
        Returns:
            Dict[TactileMetric, float]: Normalized feature vector.
        """
        normalized = {}
        # Example normalization logic (can be expanded with MinMaxScaler etc.)
        # Assuming sensors return raw voltage or newtons, here we abstract it.
        for metric, value in sample.sensor_data.items():
            # Clipping extreme values for safety
            normalized[metric] = np.clip(value, -100.0, 100.0)
        return normalized

    def map_to_semantics(self, sample: TactileSample) -> Dict[str, Union[str, float]]:
        """
        Core Function: map_to_semantics
        
        Transforms a TactileSample into a semantic description.
        
        Args:
            sample (TactileSample): Input tactile data object.
            
        Returns:
            Dict[str, Union[str, float]]: Contains 'description', 'primary_label', and 'confidence'.
        
        Raises:
            ValueError: If sample validation fails.
        """
        try:
            sample.validate()
        except ValueError as ve:
            logger.error(f"Data validation failed: {ve}")
            return {"description": "Invalid Data", "confidence": 0.0}

        features = self._normalize_data(sample)
        candidates: List[Tuple[SemanticLabel, float]] = []

        # Rule Matching
        for rule in self._rules:
            metric_val = features.get(rule.metric)
            
            if metric_val is not None:
                min_val, max_val = rule.range_val
                if min_val <= metric_val <= max_val:
                    # Calculate dynamic confidence based on distance from center
                    center = (min_val + max_val) / 2
                    dist = abs(metric_val - center) / (max_val - min_val + 1e-6)
                    dynamic_conf = rule.confidence * (1 - dist * 0.2) # Slight adjustment
                    candidates.append((rule.label, dynamic_conf))
                    logger.debug(f"Rule matched: {rule.label.value} for {rule.metric.value}={metric_val}")

        if not candidates:
            logger.info("No semantic rules matched the current tactile input.")
            return {
                "description": "感觉模糊/未识别",
                "primary_label": "UNKNOWN",
                "confidence": 0.0
            }

        # Aggregation: Sort by confidence
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_label, best_conf = candidates[0]
        
        # Construct Natural Language Description
        description = self._generate_sentence(best_label, candidates)

        return {
            "description": description,
            "primary_label": best_label.value,
            "confidence": round(best_conf, 4)
        }

    def _generate_sentence(self, primary: SemanticLabel, candidates: List[Tuple[SemanticLabel, float]]) -> str:
        """
        Helper: Generates a natural language sentence from matched labels.
        
        Args:
            primary (SemanticLabel): The dominant sensation.
            candidates (List): Other matched sensations.
            
        Returns:
            str: Natural language description.
        """
        base_desc = f"当前触觉反馈: {primary.value}"
        
        # Add secondary nuances
        secondary = [label for label, conf in candidates[1:3] if conf > 0.5]
        if secondary:
            nuance = "，同时伴随".join([l.value for l in secondary])
            base_desc += f"，同时伴随{nuance}"
            
        base_desc += "。"
        return base_desc

# --- Main Execution Block (Usage Example) ---

if __name__ == "__main__":
    # 1. Setup Mock Sensor Data
    # Scenario: A craftsman polishing a surface, feeling smooth but with some resistance
    mock_data_point = TactileSample(
        timestamp=1678900000.123,
        sensor_data={
            TactileMetric.NORMAL_FORCE: 12.5,      # Moderate pressure
            TactileMetric.VIBRATION_INTENSITY: 0.15, # Very low vibration (smooth)
            TactileMetric.SHEAR_FORCE: 2.0,         # Low shear
            TactileMetric.TEMPERATURE_DELTA: 0.5    # Slight warmth
        }
    )

    # 2. Initialize Mapper
    mapper = HapticSemanticMapper()

    # 3. Perform Mapping
    try:
        result = mapper.map_to_semantics(mock_data_point)
        
        print("-" * 40)
        print("Haptic Semantic Analysis Result:")
        print(f"Description : {result['description']}")
        print(f"Label       : {result['primary_label']}")
        print(f"Confidence  : {result['confidence']}")
        print("-" * 40)

        # Scenario 2: Rough grinding
        rough_data = TactileSample(
            timestamp=1678900001.500,
            sensor_data={
                TactileMetric.NORMAL_FORCE: 5.0,
                TactileMetric.VIBRATION_INTENSITY: 1.2 # High vibration
            }
        )
        result_rough = mapper.map_to_semantics(rough_data)
        print(f"Description : {result_rough['description']}")

    except Exception as e:
        logger.exception("An error occurred during semantic mapping execution.")