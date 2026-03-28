"""
Module: intent_cognition_bridge.py

This module implements a 'Cognitive Middle Layer' designed to bridge the gap between
human fuzzy cognition and machine strict execution. It facilitates the translation of
ambiguous natural language instructions into structured code logic through a process
of intent clustering, context-aware inference, and progressive detail injection.

Core Features:
- Semantic Item Clustering: Extracts high-level intent skeletons.
- Code Context Awareness: Infers missing parameters based on environment.
- Progressive Detail Injection: Refines logic through iterative interaction.
- Cognitive Feedback Loop: Converts logic back to natural language for verification.

Author: Auto-Generated AGI Skill
Version: 1.0.0
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentConfidence(Enum):
    """Enumeration representing the confidence level of the parsed intent."""
    LOW = 1.0
    MEDIUM = 5.0
    HIGH = 10.0

@dataclass
class SemanticCluster:
    """Represents a cluster of related semantic items forming an intent skeleton."""
    cluster_id: str
    keywords: List[str]
    inferred_action: str
    required_params: List[str]
    optional_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CognitionState:
    """Maintains the state of the cognitive translation process."""
    raw_input: str
    intent_skeleton: Optional[SemanticCluster] = None
    current_logic_map: Dict[str, Any] = field(default_factory=dict)
    feedback_history: List[Dict[str, str]] = field(default_factory=list)
    iteration_count: int = 0
    is_locked: bool = False

class IntentCognitionBridge:
    """
    The core class implementing the Cognitive Middle Layer.
    
    This class manages the lifecycle of translating fuzzy human input into
    strict executable logic structures.
    """

    def __init__(self, context_profile: Dict[str, Any]):
        """
        Initialize the bridge with a specific context profile.
        
        Args:
            context_profile (Dict[str, Any]): Environmental variables and user preferences.
        """
        self._validate_context(context_profile)
        self.context = context_profile
        self._state_registry: Dict[str, CognitionState] = {}
        logger.info("IntentCognitionBridge initialized with context: %s", context_profile.get('env', 'default'))

    def _validate_context(self, context: Dict[str, Any]) -> None:
        """Validates the input context profile."""
        if not isinstance(context, dict):
            raise ValueError("Context profile must be a dictionary.")
        if 'env' not in context:
            logger.warning("No environment specified in context, defaulting to 'production'.")
            context['env'] = 'production'

    def _generate_intent_skeleton(self, text_input: str) -> SemanticCluster:
        """
        [Core Function 1]
        Parses natural language to generate an intent skeleton via semantic clustering.
        
        This function simulates the NLP process of identifying the core action and
        associated entities from fuzzy input.
        
        Args:
            text_input (str): The raw natural language input.
            
        Returns:
            SemanticCluster: A structured representation of the identified intent.
            
        Raises:
            ValueError: If the input text is empty or strictly invalid.
        """
        if not text_input or len(text_input.strip()) < 3:
            logger.error("Input text too short or empty: %s", text_input)
            raise ValueError("Input text must contain meaningful content.")
            
        logger.debug("Clustering semantics for: %s", text_input)
        
        # Simulated Semantic Extraction Logic
        # In a real AGI system, this would interface with an embedding space
        tokens = re.findall(r'\w+', text_input.lower())
        
        # Mock logic: Detect keywords
        action = "unknown"
        params = []
        
        if "create" in tokens or "make" in tokens:
            action = "generate_asset"
            params = ["asset_type", "name"]
        elif "analyze" in tokens or "check" in tokens:
            action = "run_diagnostics"
            params = ["target", "depth"]
        elif "deploy" in tokens:
            action = "deployment_sequence"
            params = ["module_name", "target_env"]
        else:
            action = "general_query"
            params = ["query_subject"]

        # Generate a unique cluster ID based on hash of content
        cluster_id = f"cluster_{hash(text_input) % 10000:04d}"
        
        skeleton = SemanticCluster(
            cluster_id=cluster_id,
            keywords=tokens[:5],  # Top 5 keywords
            inferred_action=action,
            required_params=params
        )
        
        logger.info("Skeleton generated: Action=%s, Params=%s", action, params)
        return skeleton

    def _context_aware_inference(self, skeleton: SemanticCluster) -> Dict[str, Any]:
        """
        [Core Function 2]
        Infers missing parameters based on the code context and intent skeleton.
        
        Args:
            skeleton (SemanticCluster): The extracted intent skeleton.
            
        Returns:
            Dict[str, Any]: A dictionary containing executable logic mapping.
        """
        logger.debug("Running context inference for cluster %s", skeleton.cluster_id)
        logic_map: Dict[str, Any] = {
            "action": skeleton.inferred_action,
            "params": {},
            "confidence_score": IntentConfidence.MEDIUM.value
        }
        
        # Infer values based on self.context
        for param in skeleton.required_params:
            if param in self.context:
                logic_map['params'][param] = self.context[param]
                logger.debug("Parameter '%s' inferred from context: %s", param, self.context[param])
            else:
                # Placeholder for missing data (Progressive Injection needed)
                logic_map['params'][param] = f"<MISSING:{param}>"
                logic_map['confidence_score'] = IntentConfidence.LOW.value
                
        return logic_map

    def _generate_feedback_loop(self, logic_map: Dict[str, Any]) -> str:
        """
        [Core Function 3 - Cognitive Friction]
        Translates the structured logic back into natural language for verification.
        This creates a 'Cognitive Friction' point to ensure alignment.
        
        Args:
            logic_map (Dict[str, Any]): The structured logic to verify.
            
        Returns:
            str: A natural language query asking for confirmation or clarification.
        """
        action = logic_map.get('action', 'unknown')
        params = logic_map.get('params', {})
        
        missing_keys = [k for k, v in params.items() if isinstance(v, str) and v.startswith("<MISSING")]
        
        if missing_keys:
            feedback = (
                f"I interpreted your intent as '{action}', but I am missing critical information "
                f"regarding: {', '.join(missing_keys)}. Could you clarify these points?"
            )
        else:
            param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            feedback = (
                f"I am preparing to execute '{action}' with the following parameters: [{param_str}]. "
                f"Does this match your intent? (Yes/No/Modify)"
            )
            
        logger.info("Generated cognitive feedback: %s", feedback)
        return feedback

    def process_input(self, session_id: str, text_input: str) -> Dict[str, Any]:
        """
        Main entry point for processing fuzzy input.
        
        Args:
            session_id (str): Unique identifier for the user session.
            text_input (str): The raw user input.
            
        Returns:
            Dict[str, Any]: A response containing the status, feedback, and partial logic.
        """
        if session_id in self._state_registry and self._state_registry[session_id].is_locked:
            return {"status": "error", "message": "Session is locked in execution state."}

        try:
            # Step 1: Semantic Clustering
            skeleton = self._generate_intent_skeleton(text_input)
            
            # Step 2: Context Inference
            logic_map = self._context_aware_inference(skeleton)
            
            # Step 3: Cognitive Feedback Generation
            feedback = self._generate_feedback_loop(logic_map)
            
            # Update State
            state = CognitionState(
                raw_input=text_input,
                intent_skeleton=skeleton,
                current_logic_map=logic_map,
                iteration_count=1
            )
            self._state_registry[session_id] = state
            
            return {
                "status": "clarification_needed" if "<MISSING" in str(logic_map) else "pending_confirmation",
                "feedback": feedback,
                "logic_preview": logic_map,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.exception("Error processing input for session %s", session_id)
            return {"status": "error", "message": str(e)}

    def inject_detail(self, session_id: str, detail_key: str, detail_value: Any) -> Dict[str, Any]:
        """
        [Auxiliary Function]
        Injects specific details into an existing intent skeleton (Progressive Detail Injection).
        
        Args:
            session_id (str): The active session ID.
            detail_key (str): The parameter name to update.
            detail_value (Any): The value to inject.
            
        Returns:
            Dict[str, Any]: Updated processing status.
        """
        if session_id not in self._state_registry:
            logger.warning("Inject detail called on non-existent session: %s", session_id)
            return {"status": "error", "message": "Session not found."}
            
        state = self._state_registry[session_id]
        if state.intent_skeleton is None:
            return {"status": "error", "message": "No intent skeleton found for session."}
            
        logger.info("Injecting detail: %s = %s", detail_key, detail_value)
        
        # Update logic map
        if detail_key in state.current_logic_map.get('params', {}):
            state.current_logic_map['params'][detail_key] = detail_value
            state.current_logic_map['confidence_score'] = min(
                state.current_logic_map['confidence_score'] + 2.0, 
                IntentConfidence.HIGH.value
            )
            
            # Re-generate feedback
            feedback = self._generate_feedback_loop(state.current_logic_map)
            return {
                "status": "updated",
                "feedback": feedback,
                "logic_preview": state.current_logic_map
            }
        else:
            logger.warning("Attempted to inject unknown parameter: %s", detail_key)
            return {"status": "warning", "message": f"Parameter {detail_key} not recognized."}

# Usage Example
if __name__ == "__main__":
    # Setup a mock context (e.g., user environment preferences)
    mock_context = {
        "env": "staging",
        "user_role": "admin",
        "asset_type": "report" # Default assumption
    }
    
    # Initialize the Bridge
    bridge = IntentCognitionBridge(context_profile=mock_context)
    
    # 1. Simulate fuzzy user input
    user_input = "Please create the quarterly analysis"
    session_id = "sess_12345"
    
    print(f"User Input: {user_input}")
    response = bridge.process_input(session_id, user_input)
    
    print("\n--- System Response ---")
    print(f"Status: {response['status']}")
    print(f"Feedback: {response['feedback']}")
    print(f"Logic: {json.dumps(response['logic_preview'], indent=2)}")
    
    # 2. Simulate progressive detail injection
    print("\n--- User Injects Detail ---")
    update_response = bridge.inject_detail(session_id, "name", "Q3_Financial_Report")
    print(f"Updated Logic: {json.dumps(update_response['logic_preview'], indent=2)}")