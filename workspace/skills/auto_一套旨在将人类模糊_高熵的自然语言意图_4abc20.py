"""
Module: intent_collapse_protocol.py

This module implements the 'Intent Collapse Protocol', a cognitive subsystem designed
to translate high-entropy, ambiguous human natural language intents into low-entropy,
formalized, machine-executable logic.

Core Concepts:
- Cognitive Friction: Detection of semantic loss during domain transfer (e.g., Management -> Code).
- Explanatory Bridge Nodes: Intermediate data structures that map abstract concepts to concrete parameters.
- Binary Teaching Interaction: A mechanism to guide the user through choices to collapse ambiguity.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentCollapseProtocol")

class EntropyLevel(Enum):
    """Enumeration representing the semantic entropy level of the intent."""
    HIGH = "high"       # Ambiguous, requires disambiguation
    MEDIUM = "medium"   # Partially structured
    LOW = "low"         # Ready for execution

@dataclass
class SemanticBridge:
    """
    Represents an 'Explanatory Bridge Node'.
    Used to map a vague concept to a set of concrete, selectable options.
    """
    concept_id: str
    description: str
    options: List[Dict[str, str]]  # List of {'id': 'val', 'desc': 'desc'}
    selected_value: Optional[str] = None

@dataclass
class FormalizedIntent:
    """
    The final low-entropy output structure.
    """
    raw_input: str
    action_type: str
    parameters: Dict[str, Any]
    confidence_score: float
    is_executable: bool = False

class IntentCollapseEngine:
    """
    A cognitive protocol engine that transforms fuzzy human intents into
    precise machine logic through interactive entropy reduction.
    """

    def __init__(self, domain_constraints: Dict[str, List[str]]):
        """
        Initialize the engine with domain-specific constraints.
        
        Args:
            domain_constraints (Dict[str, List[str]]): Defines valid parameters for specific domains.
        """
        self.domain_constraints = domain_constraints
        self._validation_cache = {}
        logger.info("IntentCollapseEngine initialized with domain constraints.")

    def _calculate_entropy(self, text: str) -> EntropyLevel:
        """
        [Helper] Estimates the entropy of the input text based on heuristic length and keyword density.
        
        Args:
            text (str): The natural language input.
            
        Returns:
            EntropyLevel: The estimated entropy level.
        """
        if not text or len(text) < 5:
            return EntropyLevel.LOW  # Empty or very short input is treated as specific (or error)
        
        # Heuristic: Check for ambiguity markers
        ambiguity_markers = ["maybe", "sort of", "fast", "good", "nice", "change", "it"]
        
        # Simple intersection check
        words = set(text.lower().split())
        markers_found = sum(1 for marker in ambiguity_markers if marker in words)
        
        if markers_found > 2 or len(words) < 3:
            return EntropyLevel.HIGH
        
        if markers_found > 0:
            return EntropyLevel.MEDIUM
            
        return EntropyLevel.LOW

    def detect_cognitive_friction(self, raw_intent: str, target_domain: str) -> Tuple[bool, List[SemanticBridge]]:
        """
        Analyzes the intent for 'Cognitive Friction' - gaps between the intent and the target domain.
        Generates 'Explanatory Bridge Nodes' (SemanticBridges) to fill these gaps.
        
        Args:
            raw_intent (str): The user's natural language input.
            target_domain (str): The target execution domain (e.g., 'database', 'ui').
            
        Returns:
            Tuple[bool, List[SemanticBridge]]: 
                - bool: True if friction is detected (bridges needed).
                - List[SemanticBridge]: The required bridges to collapse the wave function.
        """
        logger.info(f"Analyzing cognitive friction for intent: '{raw_intent}'")
        entropy = self._calculate_entropy(raw_intent)
        
        if entropy == EntropyLevel.LOW:
            logger.info("Low entropy detected. No friction.")
            return False, []

        bridges = []
        
        # Simulation of mapping fuzzy logic to domain constraints
        # In a real AGI, this would involve vector space mapping.
        # Here we simulate detecting missing parameters based on the domain.
        
        if "fast" in raw_intent.lower():
            # The concept of "fast" is high-entropy in execution terms.
            bridge = SemanticBridge(
                concept_id="speed_profile",
                description="The term 'fast' is ambiguous in the execution domain. Please specify a performance profile.",
                options=[
                    {"id": "low_latency", "desc": "Optimize for speed, ignore cost (Low Latency)."},
                    {"id": "balanced", "desc": "Standard execution speed."},
                    {"id": "batch", "desc": "Background processing (Slow but efficient)."}
                ]
            )
            bridges.append(bridge)
            
        if target_domain in self.domain_constraints:
            required_params = self.domain_constraints[target_domain]
            # Check if raw intent seems to lack specific required params (simulated)
            if len(raw_intent.split()) < 10: 
                bridge = SemanticBridge(
                    concept_id="scope_definition",
                    description="Intent lacks specific scope boundaries.",
                    options=[{"id": p, "desc": f"Apply to {p}"} for p in required_params]
                )
                bridges.append(bridge)

        has_friction = len(bridges) > 0
        logger.info(f"Friction detected: {has_friction}. Bridges generated: {len(bridges)}")
        return has_friction, bridges

    def collapse_intent(
        self, 
        raw_intent: str, 
        bridges: List[SemanticBridge], 
        user_choices: Dict[str, str]
    ) -> FormalizedIntent:
        """
        Collapses the fuzzy intent into a formalized state by applying user choices
        to the bridge nodes.
        
        Args:
            raw_intent (str): Original input.
            bridges (List[SemanticBridge]): The generated bridges.
            user_choices (Dict[str, str]): Map of bridge_id -> selected_option_id.
            
        Returns:
            FormalizedIntent: The low-entropy, executable object.
            
        Raises:
            ValueError: If required choices are missing.
        """
        logger.info("Initiating intent collapse sequence...")
        
        resolved_params = {}
        
        # Process Bridges
        for bridge in bridges:
            choice = user_choices.get(bridge.concept_id)
            if not choice:
                logger.error(f"Missing choice for bridge: {bridge.concept_id}")
                raise ValueError(f"Disambiguation required for '{bridge.concept_id}'")
            
            # Validate choice against options
            valid_ids = [opt['id'] for opt in bridge.options]
            if choice not in valid_ids:
                logger.error(f"Invalid choice '{choice}' for bridge {bridge.concept_id}")
                raise ValueError(f"Invalid option selected for {bridge.concept_id}")
                
            resolved_params[bridge.concept_id] = choice
            logger.info(f"Bridge '{bridge.concept_id}' collapsed to: {choice}")

        # Construct Final Logic
        # Simulate conversion to JSON logic or similar formal representation
        formal_logic = {
            "action": "execute_task",
            "target": raw_intent, # In real scenario, this would be parsed entities
            "config": resolved_params,
            "timestamp": "2023-10-27T10:00:00Z" 
        }
        
        result = FormalizedIntent(
            raw_input=raw_intent,
            action_type="DOMAIN_EXECUTION",
            parameters=formal_logic,
            confidence_score=0.98, # High confidence post-collapse
            is_executable=True
        )
        
        logger.info("Intent successfully collapsed to low-entropy state.")
        return result

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup Domain Constraints
    constraints = {
        "database": ["read_replica", "master", "backup"],
        "ui": ["mobile", "desktop", "tablet"]
    }
    
    # 2. Initialize Engine
    engine = IntentCollapseEngine(constraints)
    
    # 3. Simulate User Input (High Entropy)
    user_input = "Make the database run fast"
    
    try:
        # 4. Detect Friction
        needs_guidance, semantic_bridges = engine.detect_cognitive_friction(user_input, "database")
        
        if needs_guidance:
            print(f"System: Detected ambiguity in intent: '{user_input}'")
            simulated_choices = {}
            
            # 5. Binary Teaching Interaction (Simulated UI Loop)
            for bridge in semantic_bridges:
                print(f"\nBridge Needed: {bridge.description}")
                print("Options:")
                for opt in bridge.options:
                    print(f"  [{opt['id']}]: {opt['desc']}")
                
                # Simulate user selecting the first option for automation purposes
                selected = bridge.options[0]['id']
                print(f"User Selects: {selected}")
                simulated_choices[bridge.concept_id] = selected
                
            # 6. Collapse Intent
            final_intent = engine.collapse_intent(user_input, semantic_bridges, simulated_choices)
            print("\n--- Formalized Output ---")
            print(json.dumps(final_intent.parameters, indent=2))
        else:
            print("Intent is already precise. Executing directly...")
            
    except ValueError as e:
        logger.error(f"Protocol Failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected System Error: {e}")