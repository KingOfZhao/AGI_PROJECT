"""
Name: auto_semantic_assembler_63508c
Description: This module implements a 'Semantic Architectural Assembler'.
             It treats natural language pronouns as 'Data Flow Ports' and verbs as 'API Probes'.
             It transforms fuzzy requirements (e.g., 'a space suitable for meditation') into
             structured intermediate logic and maps them to specific engineering parameters.
             This effectively processes natural language as an executable programming language.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentCategory(Enum):
    """Enumeration of recognized intent categories."""
    ATMOSPHERE = "atmosphere"
    CALCULATION = "calculation"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class SemanticPort:
    """
    Represents a 'Data Flow Port' derived from natural language pronouns or entities.
    """
    entity_id: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIProbe:
    """
    Represents an 'API Probe' derived from natural language verbs.
    """
    action_name: str
    requires_input: bool
    output_type: str


@dataclass
class EngineeringParameter:
    """
    Represents the final executable engineering parameter.
    """
    param_name: str
    param_value: Any
    unit: Optional[str] = None
    tolerance: Optional[float] = None


class SemanticArchitectureAssembler:
    """
    Translates natural language intents into executable engineering parameters.
    """

    def __init__(self):
        self._intent_map = self._initialize_intent_map()
        self._entity_registry: Dict[str, SemanticPort] = {}
        logger.info("Semantic Architecture Assembler initialized.")

    def _initialize_intent_map(self) -> Dict[str, Any]:
        """
        Helper function to initialize semantic mapping rules.
        """
        return {
            "create": {"category": IntentCategory.ATMOSPHERE, "base_logic": "GENERATE"},
            "meditation": {"attributes": {"lux_level": 50, "color_temp": 2700, "noise_threshold": 20}},
            "party": {"attributes": {"lux_level": 200, "color_temp": 4000, "noise_threshold": 80}},
            "calculate": {"category": IntentCategory.CALCULATION, "base_logic": "COMPUTE"},
            "send": {"category": IntentCategory.COMMUNICATION, "base_logic": "TRANSMIT"},
        }

    def _extract_data_ports(self, text: str) -> List[SemanticPort]:
        """
        Extracts entities (nouns/pronouns) acting as Data Flow Ports.
        This is a core function performing NLP-like extraction logic.
        """
        ports = []
        # Simple regex simulation for entities (nouns)
        # In a real AGI, this would interface with an NLP model
        noun_patterns = [
            (r'\b(space|room|area)\b', 'LOCATION'),
            (r'\b(light|lumination)\b', 'DEVICE'),
            (r'\b(message|email)\b', 'DATA_PACKET'),
            (r'\b(I|me|my)\b', 'USER_REF')
        ]

        for pattern, type_ in noun_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity_id = f"{type_}_{match.start()}"
                port = SemanticPort(entity_id=entity_id, entity_type=type_)
                ports.append(port)
                self._entity_registry[entity_id] = port
                logger.debug(f"Extracted Data Port: {port.entity_id} of type {port.entity_type}")

        return ports

    def _extract_api_probes(self, text: str) -> List[APIProbe]:
        """
        Extracts verbs acting as API Probes.
        This is a core function identifying executable actions.
        """
        probes = []
        verb_patterns = [
            (r'\b(make|create|generate|build)\b', 'CREATE_OBJECT', True, 'OBJECT_ID'),
            (r'\b(calculate|compute|derive)\b', 'EXEC_MATH', True, 'NUMBER'),
            (r'\b(send|transmit|email)\b', 'NETWORK_SEND', True, 'STATUS_CODE'),
        ]

        for pattern, action, req_input, out_type in verb_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                probe = APIProbe(
                    action_name=action,
                    requires_input=req_input,
                    output_type=out_type
                )
                probes.append(probe)
                logger.debug(f"Detected API Probe: {action}")

        return probes

    def _map_intent_to_parameters(self, intent_key: str, context: Dict[str, Any]) -> List[EngineeringParameter]:
        """
        Helper function to map high-level intents to specific engineering parameters.
        Performs data validation and boundary checks.
        """
        params = []
        intent_data = self._intent_map.get(intent_key.lower())

        if not intent_data:
            logger.warning(f"Intent key '{intent_key}' not found in mapping.")
            return params

        attributes = intent_data.get("attributes", {})
        
        for key, value in attributes.items():
            # Boundary checking for specific parameters
            if key == "lux_level":
                if not (0 <= value <= 1000):
                    logger.error(f"Lux level {value} out of bounds (0-1000). Clamping.")
                    value = max(0, min(1000, value))
            
            param = EngineeringParameter(
                param_name=key,
                param_value=value,
                unit="lux" if "lux" in key else "dB" if "noise" in key else None
            )
            params.append(param)

        return params

    def assemble(self, natural_language_input: str) -> Dict[str, Any]:
        """
        Main entry point. Transforms fuzzy NL input into structured execution logic.
        
        Args:
            natural_language_input (str): The user request string.
            
        Returns:
            Dict[str, Any]: A structured execution plan containing 'ports', 'logic', and 'parameters'.
        
        Raises:
            ValueError: If input is empty or invalid.
        """
        if not natural_language_input or not isinstance(natural_language_input, str):
            logger.error("Invalid input provided to assembler.")
            raise ValueError("Input must be a non-empty string.")

        logger.info(f"Processing input: '{natural_language_input}'")

        # 1. Identify Data Ports (Pronouns/Nouns)
        ports = self._extract_data_ports(natural_language_input)

        # 2. Identify API Probes (Verbs)
        probes = self._extract_api_probes(natural_language_input)

        # 3. Intermediate Logic Generation
        # Determining the core intent based on keywords
        logic_flow = "UNKNOWN"
        target_params = []

        if "meditation" in natural_language_input.lower():
            logic_flow = "SET_AMBIENT_ENVIRONMENT"
            target_params = self._map_intent_to_parameters("meditation", {})
        elif "party" in natural_language_input.lower():
            logic_flow = "SET_AMBIENT_ENVIRONMENT"
            target_params = self._map_intent_to_parameters("party", {})
        
        # 4. Construct Execution Plan
        execution_plan = {
            "status": "ANALYSIS_COMPLETE",
            "intermediate_logic": logic_flow,
            "identified_ports": [
                {"id": p.entity_id, "type": p.entity_type} for p in ports
            ],
            "api_probes": [
                {"action": p.action_name, "output": p.output_type} for p in probes
            ],
            "engineering_parameters": [
                {"param": p.param_name, "value": p.param_value, "unit": p.unit} 
                for p in target_params
            ]
        }

        logger.info(f"Assembly complete. Logic: {logic_flow}")
        return execution_plan


# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the assembler
    assembler = SemanticArchitectureAssembler()

    # Example 1: Fuzzy requirement for a space
    user_input_1 = "I want to create a space suitable for meditation."
    
    print(f"\n--- Processing Request ---\nInput: {user_input_1}")
    try:
        result = assembler.assemble(user_input_1)
        print("\n--- Execution Plan ---")
        import json
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"Error: {e}")

    # Example 2: Input validation test
    print("\n--- Testing Input Validation ---")
    try:
        assembler.assemble("")
    except ValueError as e:
        print(f"Caught expected error: {e}")