"""
Module: agi_conflict_resolution_node_generator
Description: Implements the 'Overlap Solidification as Real Node' skill for AGI systems.
             It handles conflicts between multi-modal sensor data (Objective) and 
             expert experience rules (Subjective) by generating weighted 'Falsifiable Nodes'.
             
Author: Senior Python Engineer
Version: 1.0.0
Domain: decision_theory
"""

import logging
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
CONFLICT_THRESHOLD = 0.25  # Minimum divergence to trigger conflict resolution
MODALITY_WEIGHTS = {
    "vibration_spectrum": 0.4,
    "acoustic_signature": 0.3,
    "thermal_profile": 0.3
}

@dataclass
class SensorReading:
    """Represents normalized input from multi-modal sensors."""
    vibration_score: float  # 0.0 (Healthy) to 1.0 (Critical)
    acoustic_score: float   # 0.0 (Quiet) to 1.0 (Loud/Anomalous)
    thermal_score: float    # 0.0 (Cool) to 1.0 (Overheat)
    timestamp: str

    def __post_init__(self):
        self._validate_scores()

    def _validate_scores(self):
        for attr in ['vibration_score', 'acoustic_score', 'thermal_score']:
            val = getattr(self, attr)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{attr} must be between 0.0 and 1.0. Got {val}")

@dataclass
class ExpertHypothesis:
    """Represents the human expert's intuition or rule-based prediction."""
    risk_level: float  # 0.0 (Safe) to 1.0 (Imminent Failure)
    source_id: str
    reasoning: str
    credibility_factor: float = 1.0  # Historical accuracy of the expert

class ConflictResolver:
    """
    Core engine for resolving discrepancies between data and expert expectations.
    Generates a 'Falsifiable Node' when a significant conflict is detected.
    """

    def __init__(self, system_trust_bias: float = 0.6):
        """
        Initialize the resolver.
        
        Args:
            system_trust_bias (float): How much the system trusts raw data over experts 
                                       (0.5 = balanced, >0.5 favors data).
        """
        if not (0.0 <= system_trust_bias <= 1.0):
            raise ValueError("System trust bias must be between 0.0 and 1.0")
        self.system_trust_bias = system_trust_bias
        logger.info(f"ConflictResolver initialized with trust bias: {system_trust_bias}")

    def _calculate_weighted_risk(self, data: SensorReading) -> float:
        """
        Helper: Calculate aggregated risk score from multi-modal data.
        Weighted average based on modality importance.
        """
        weighted_sum = (
            data.vibration_score * MODALITY_WEIGHTS["vibration_spectrum"] +
            data.acoustic_score * MODALITY_WEIGHTS["acoustic_signature"] +
            data.thermal_score * MODALITY_WEIGHTS["thermal_profile"]
        )
        total_weight = sum(MODALITY_WEIGHTS.values())
        return weighted_sum / total_weight

    def _determine_conflict_nature(self, data_risk: float, expert_risk: float) -> str:
        """
        Helper: Categorize the type of conflict for the knowledge graph.
        """
        if data_risk < 0.3 and expert_risk > 0.7:
            return "Latent_Risk_Overlooked"  # Expert sees what data doesn't
        elif data_risk > 0.7 and expert_risk < 0.3:
            return "False_Positive_Suspected" # Data sees what expert denies
        else:
            return "Ambiguity_Detected"

    def analyze_and_generate_node(
        self, 
        sensor_input: SensorReading, 
        expert_input: ExpertHypothesis
    ) -> Optional[Dict[str, Any]]:
        """
        Main function to process inputs and generate a 'Falsifiable Node' if conflict exists.
        
        Args:
            sensor_input (SensorReading): Validated multi-modal data object.
            expert_input (ExpertHypothesis): Expert's prediction object.
            
        Returns:
            Optional[Dict]: A dictionary representing the new node to be added to the KG,
                            or None if no significant conflict is found.
                            
        Example:
            >>> sensor = SensorReading(0.1, 0.2, 0.15, datetime.now().isoformat())
            >>> expert = ExpertHypothesis(0.9, "Expert_01", "Bearing wear sounds different")
            >>> resolver = ConflictResolver()
            >>> node = resolver.analyze_and_generate_node(sensor, expert)
            >>> print(node['type'])
            'Pending_Falsification'
        """
        try:
            # 1. Quantify Objective vs Subjective Risk
            data_risk = self._calculate_weighted_risk(sensor_input)
            expert_risk = expert_input.risk_level * expert_input.credibility_factor
            
            divergence = abs(data_risk - expert_risk)
            logger.info(f"Analysis | Data Risk: {data_risk:.2f} | Expert Risk: {expert_risk:.2f} | Divergence: {divergence:.2f}")

            # 2. Check if conflict exceeds threshold
            if divergence < CONFLICT_THRESHOLD:
                logger.info("Divergence within acceptable limits. Reinforcing existing node.")
                return None

            # 3. Generate Falsifiable Node Logic
            # Conflict Logic: If data says "Safe" (low) and Expert says "Danger" (high),
            # and we trust the expert, the new node risk should be higher than raw data suggests.
            
            # Dynamic Weighting:
            # If bias is 0.6 (trust data), result leans to data.
            # If expert credibility is high, result pulls towards expert.
            effective_weight = (1 - self.system_trust_bias) * expert_input.credibility_factor
            
            # Calculate new probability score (Bayesian-inspired update approximation)
            # New_Risk = (Data_Risk * (1 - effective_weight)) + (Expert_Risk * effective_weight)
            new_risk_score = (
                (data_risk * (1 - effective_weight)) + 
                (expert_risk * effective_weight)
            )
            
            conflict_type = self._determine_conflict_nature(data_risk, expert_risk)

            # 4. Construct the Node Object
            new_node = {
                "node_id": f"node_{str(uuid4())[:8]}",
                "timestamp": datetime.now().isoformat(),
                "type": "Pending_Falsification",
                "attributes": {
                    "conflict_category": conflict_type,
                    "integrated_risk_score": round(new_risk_score, 3),
                    "source_data_score": round(data_risk, 3),
                    "source_expert_score": round(expert_risk, 3),
                    "expert_reasoning": expert_input.reasoning,
                    "resolution_strategy": "Schedule targeted maintenance / Increase sensor sampling rate"
                },
                "status": "Unverified"
            }
            
            logger.warning(f"CONFLICT DETECTED [{conflict_type}]: Generating new node {new_node['node_id']}")
            return new_node

        except Exception as e:
            logger.error(f"Error during conflict analysis: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to process conflict resolution logic") from e

def run_diagnostic_check(sensor_dict: Dict, expert_dict: Dict) -> Dict:
    """
    Convenience wrapper function to run the skill logic from raw dictionaries.
    
    Args:
        sensor_dict (Dict): Contains 'vibration', 'acoustic', 'temp' keys.
        expert_dict (Dict): Contains 'risk', 'source', 'reason' keys.
        
    Returns:
        Dict: The generated node or a 'stable' status message.
    """
    try:
        # Data Validation and Object Mapping
        reading = SensorReading(
            vibration_score=sensor_dict.get('vibration', 0.0),
            acoustic_score=sensor_dict.get('acoustic', 0.0),
            thermal_score=sensor_dict.get('temp', 0.0),
            timestamp=datetime.now().isoformat()
        )
        
        hypothesis = ExpertHypothesis(
            risk_level=expert_dict.get('risk', 0.0),
            source_id=expert_dict.get('source', 'Unknown'),
            reasoning=expert_dict.get('reason', 'No reason provided')
        )
        
        # Initialize Resolver (Assuming balanced trust for this instance)
        resolver = ConflictResolver(system_trust_bias=0.5)
        
        # Execute
        result = resolver.analyze_and_generate_node(reading, hypothesis)
        
        if result:
            return result
        else:
            return {"status": "Stable", "message": "No conflict detected"}
            
    except ValueError as ve:
        logger.error(f"Input Validation Failed: {ve}")
        return {"error": str(ve)}
    except Exception as e:
        logger.critical(f"System Failure: {e}")
        return {"error": "Internal system error"}

if __name__ == "__main__":
    # Example Usage: Scenario where data looks normal, but expert predicts failure
    mock_sensor_data = {
        "vibration": 0.15,  # Low vibration
        "acoustic": 0.1,    # Quiet
        "temp": 0.2         # Normal temp
    }
    
    mock_expert_data = {
        "risk": 0.95,       # High risk predicted
        "source": "Senior_Engineer_01",
        "reason": "Detected subtle harmonic dissonance indicative of bearing micro-cracks"
    }
    
    print("--- Running AGI Conflict Resolution Skill ---")
    node_result = run_diagnostic_check(mock_sensor_data, mock_expert_data)
    print(json.dumps(node_result, indent=4))