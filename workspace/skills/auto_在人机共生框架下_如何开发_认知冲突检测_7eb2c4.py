"""
Module: cognitive_conflict_resolver.py

This module implements a 'Cognitive Conflict Detection & Fusion Mechanism' within
a Human-AI Symbiosis framework. It is designed to handle scenarios where an AI's
structured network prediction (Logical/Optimal Path) conflicts with human
intuition or behavior.

Instead of defaulting to compliance or override, the system generates an
'Inquiry Node' to resolve ambiguity. Crucially, it validates whether a
'Human Violation' is actually the discovery of an AI Model Blind Spot (Edge Case).

Key Components:
- CognitiveState: Represents the context of the decision.
- ConflictDetector: Identifies discrepancies between AI and Human actions.
- InquiryGenerator: Formulates clarification requests.
- BlindSpotValidator: Determines if the human action reveals a model gap.
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ValidationError, confloat

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("CognitiveConflictResolver")

class ConflictLevel(Enum):
    """Enumeration for the severity of cognitive conflict."""
    NONE = 0
    LOW = 1      # Minor deviation, likely noise
    MEDIUM = 2   # Significant deviation, requires logging
    HIGH = 3     # Critical divergence, requires immediate Inquiry Node

class SystemAction(Enum):
    """Possible outcomes of the conflict resolution process."""
    AI_OVERRIDE = "AI logic prevails (High Confidence)"
    HUMAN_COMPLIANCE = "Follow Human lead (Trust/Authority)"
    INQUIRY_NODE = "Pause and Ask for Clarification"
    MODEL_ADAPTATION = "Human action identified as Edge Case (Blind Spot)"

class CognitiveState(BaseModel):
    """
    Represents a snapshot of the decision-making environment.
    Uses Pydantic for data validation.
    """
    state_vector: List[float] = Field(..., min_items=3, description="Numerical representation of environment")
    ai_confidence: confloat(ge=0.0, le=1.0) = Field(..., description="AI's prediction confidence")
    human_deviation_score: confloat(ge=0.0, le=1.0) = Field(..., description="Distance between AI optimal and Human action")

class ConflictAnalyzer:
    """
    Core class for detecting cognitive conflicts and managing the symbiotic relationship.
    """

    def __init__(self, blind_spot_threshold: float = 0.85, conflict_threshold: float = 0.4):
        """
        Initialize the analyzer with thresholds.

        Args:
            blind_spot_threshold (float): If AI confidence is below this, human action is likely a blind spot.
            conflict_threshold (float): Deviation score above which a conflict is flagged.
        """
        self.blind_spot_threshold = blind_spot_threshold
        self.conflict_threshold = conflict_threshold
        self._inquiry_count = 0
        logger.info("ConflictAnalyzer initialized with thresholds: BlindSpot=%s, Conflict=%s",
                    blind_spot_threshold, conflict_threshold)

    def _calculate_conflict_level(self, state: CognitiveState) -> ConflictLevel:
        """
        Helper function to determine the level of conflict based on deviation and confidence.
        
        Args:
            state (CognitiveState): The current cognitive state.
            
        Returns:
            ConflictLevel: The calculated severity level.
        """
        if state.human_deviation_score < self.conflict_threshold:
            return ConflictLevel.NONE
        
        if state.ai_confidence > 0.9:
            return ConflictLevel.HIGH
        elif state.ai_confidence > 0.7:
            return ConflictLevel.MEDIUM
        else:
            return ConflictLevel.LOW

    def detect_cognitive_dissonance(self, state: CognitiveState) -> Tuple[ConflictLevel, SystemAction]:
        """
        Analyzes the dissonance between AI prediction and Human action.
        
        Logic Flow:
        1. Check for conflict existence.
        2. If conflict exists, determine if it's an AI Blind Spot (Low Confidence + High Deviation).
        3. If High Confidence + High Deviation, generate Inquiry Node.
        4. Otherwise, default to standard conflict resolution.
        
        Args:
            state (CognitiveState): Validated input state.
            
        Returns:
            Tuple[ConflictLevel, SystemAction]: The diagnosis and the prescribed system action.
        """
        try:
            conflict_level = self._calculate_conflict_level(state)
            
            if conflict_level == ConflictLevel.NONE:
                return conflict_level, SystemAction.AI_OVERRIDE

            logger.warning(f"Cognitive Dissonance Detected: Level {conflict_level.name}")
            
            # Check for Blind Spot (The "Human Violation" vs "Model Gap" check)
            # If AI is not confident, but Human deviates strongly, Human likely sees something AI misses.
            if state.ai_confidence < self.blind_spot_threshold and state.human_deviation_score > 0.6:
                logger.info("Identified potential AI Blind Spot (Edge Case).")
                return conflict_level, SystemAction.MODEL_ADAPTATION
            
            # High Confidence Conflict -> Generate Inquiry Node
            if conflict_level == ConflictLevel.HIGH:
                return conflict_level, SystemAction.INQUIRY_NODE
            
            # Medium/Low conflict with decent confidence -> Log and follow Human or Ask
            return conflict_level, SystemAction.HUMAN_COMPLIANCE

        except Exception as e:
            logger.error(f"Error during dissonance detection: {e}")
            # Fallback to safety
            return ConflictLevel.HIGH, SystemAction.INQUIRY_NODE

    def generate_inquiry_node(self, conflict_level: ConflictLevel, context: str = "Unspecified Context") -> Dict:
        """
        Constructs a structured query object (Inquiry Node) to be sent to the human interface.
        
        Args:
            conflict_level (ConflictLevel): Severity of the conflict.
            context (str): Description of the situation.
            
        Returns:
            Dict: A structured JSON-like object representing the query.
        """
        self._inquiry_count += 1
        node_id = f"INQ_{self._inquiry_count:04d}"
        
        inquiry = {
            "node_id": node_id,
            "type": "COGNITIVE_CONFLICT_RESOLUTION",
            "priority": conflict_level.value,
            "message": f"AI prediction conflicts with operator input ({context}). Please verify intent.",
            "options": [
                {"label": "Maintain AI Path", "action": "REVERT_TO_AI"},
                {"label": "Force Human Path", "action": "OVERRIDE_AI"},
                {"label": "Pause & Re-evaluate", "action": "SYSTEM_HALT"}
            ],
            "metadata": {
                "timestamp": logging.time.time() if hasattr(logging, 'time') else 'N/A',
                "requires_immediate_response": conflict_level == ConflictLevel.HIGH
            }
        }
        
        logger.debug(f"Generated Inquiry Node: {node_id}")
        return inquiry

def run_symbiosis_cycle(state_data: Dict) -> None:
    """
    Orchestrates a single cycle of the Human-AI symbiosis decision process.
    This function demonstrates the full workflow.
    
    Args:
        state_data (Dict): Raw dictionary data to be validated into CognitiveState.
    """
    logger.info("--- Starting Symbiosis Cycle ---")
    
    # 1. Data Validation
    try:
        state = CognitiveState(**state_data)
    except ValidationError as e:
        logger.error(f"Input validation failed: {e}")
        return

    # 2. Initialize Analyzer
    analyzer = ConflictAnalyzer(blind_spot_threshold=0.75, conflict_threshold=0.3)
    
    # 3. Detect Conflict
    level, action = analyzer.detect_cognitive_dissonance(state)
    
    # 4. Act based on decision
    logger.info(f"Decision Result: Level={level.name}, Action={action.value}")
    
    if action == SystemAction.INQUIRY_NODE:
        inquiry = analyzer.generate_inquiry_node(level, context="Navigation Decision")
        print(f"SYSTEM OUTPUT: {inquiry['message']}")
        # Here the system would pause and wait for user input
    elif action == SystemAction.MODEL_ADAPTATION:
        logger.info("Triggering online learning module to update model based on Edge Case.")
        print("SYSTEM OUTPUT: Human action accepted as correction. Adapting model...")
    else:
        print(f"SYSTEM OUTPUT: Proceeding with {action.value}")

if __name__ == "__main__":
    # Example 1: High Confidence Conflict (AI thinks it's right, Human deviates) -> Inquiry Node
    print("\n--- Scenario A: High Confidence Conflict ---")
    scenario_a_data = {
        "state_vector": [0.5, 1.2, 3.3],
        "ai_confidence": 0.95,
        "human_deviation_score": 0.8
    }
    run_symbiosis_cycle(scenario_a_data)

    # Example 2: Low Confidence + Deviation (AI unsure, Human acts) -> Blind Spot Detection
    print("\n--- Scenario B: Low Confidence (Blind Spot) ---")
    scenario_b_data = {
        "state_vector": [0.1, 0.2, 0.1],
        "ai_confidence": 0.60,
        "human_deviation_score": 0.9
    }
    run_symbiosis_cycle(scenario_b_data)

    # Example 3: Alignment (No conflict)
    print("\n--- Scenario C: Alignment ---")
    scenario_c_data = {
        "state_vector": [1.0, 1.0, 1.0],
        "ai_confidence": 0.98,
        "human_deviation_score": 0.1
    }
    run_symbiosis_cycle(scenario_c_data)