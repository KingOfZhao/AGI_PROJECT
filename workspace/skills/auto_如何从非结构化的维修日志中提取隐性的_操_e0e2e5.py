"""
Module: implicit_operator_extractor.py
Description: Extracts implicit operational 'verbs' from unstructured maintenance logs
             and maps them to standardized, executable Python functions (skills).
Author: AGI System Core
Version: 1.0.0
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class ActionIntent:
    """
    Represents a parsed action from the log.
    
    Attributes:
        action_type: The standardized action verb (e.g., 'calibrate', 'tap').
        parameters: Extracted parameters (e.g., force level, target component).
        confidence: Confidence score of the extraction (0.0 to 1.0).
        raw_text: The original text segment.
    """
    action_type: str
    parameters: Dict[str, Any]
    confidence: float
    raw_text: str

class OperationalContext:
    """
    Context class holding the state of the equipment or robot.
    """
    def __init__(self, equipment_id: str, current_state: Dict[str, Any]):
        self.equipment_id = equipment_id
        self.state = current_state
        self.history: List[str] = []

    def update_state(self, key: str, value: Any):
        self.state[key] = value
        self.history.append(f"Updated {key} to {value}")

# --- Abstract Skill Definition ---

class OperationalSkill(ABC):
    """Abstract base class for executable skills."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self, context: OperationalContext, **kwargs) -> bool:
        pass

# --- Concrete Skill Implementations ---

class CalibrationSkill(OperationalSkill):
    @property
    def name(self) -> str:
        return "calibrate"

    def execute(self, context: OperationalContext, target: str = "default", level: str = "fine") -> bool:
        logger.info(f"Executing CALIBRATION on {context.equipment_id} | Target: {target}, Level: {level}")
        # Simulate hardware interaction
        if level == "rough":
            logger.warning("Performing rough calibration.")
        context.update_state("calibration_status", "calibrated")
        return True

class PercussiveMaintenanceSkill(OperationalSkill):
    @property
    def name(self) -> str:
        return "tap"

    def execute(self, context: OperationalContext, force: str = "medium", location: str = "chassis") -> bool:
        logger.info(f"Executing TAP (Percussive Maintenance) | Force: {force}, Location: {location}")
        
        force_map = {"light": 0.2, "medium": 0.5, "heavy": 0.9}
        val = force_map.get(force, 0.5)
        
        # Boundary check
        if val > 0.8:
            logger.error("Force too high, risking damage. Aborting.")
            return False
            
        # Simulate action
        logger.info(f"Actuator striking with {val} Newtons.")
        return True

class InspectionSkill(OperationalSkill):
    @property
    def name(self) -> str:
        return "inspect"

    def execute(self, context: OperationalContext, component: str = "general") -> bool:
        logger.info(f"Executing INSPECTION on component: {component}")
        # Mock logic to detect anomalies
        found_anomaly = False # random check
        context.update_state(f"{component}_status", "checked")
        return True

# --- Core Logic Components ---

class OperatorExtractor:
    """
    NLP Component responsible for parsing unstructured text and identifying intents.
    Uses a heuristic/regex-based approach for this specific implementation.
    """

    def __init__(self):
        # Define patterns for implicit verbs
        # Format: StandardizedName: [(regex_pattern, parameter_extractors)]
        self._patterns = {
            "calibrate": [
                re.compile(r"re-?calibrat(e|ing)", re.I),
                re.compile(r"reset (the )?baseline", re.I),
                re.compile(r"zero (out )?the sensors", re.I)
            ],
            "tap": [
                re.compile(r"(gentle|light|slight)\s*(tap|hit|knock|strike)", re.I),
                re.compile(r"percussive maintenance", re.I),
                re.compile(r"tap (it )?lightly", re.I)
            ],
            "inspect": [
                re.compile(r"check(ing)? (the )?status", re.I),
                re.compile(r"visual inspection", re.I),
                re.compile(r"look(ed)? into", re.I)
            ]
        }
        logger.info("OperatorExtractor initialized with predefined patterns.")

    def parse_log_entry(self, log_text: str) -> List[ActionIntent]:
        """
        Parses a single log entry to extract action intents.
        
        Args:
            log_text: The raw string from the maintenance log.
            
        Returns:
            A list of ActionIntent objects.
        """
        if not log_text or not isinstance(log_text, str):
            logger.warning("Invalid log input received.")
            return []

        detected_intents = []
        
        for action_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(log_text)
                if match:
                    # Extract parameters heuristically
                    params = self._extract_parameters(log_text, action_type)
                    
                    intent = ActionIntent(
                        action_type=action_type,
                        parameters=params,
                        confidence=0.85, # Fixed confidence for rule-based
                        raw_text=match.group(0)
                    )
                    detected_intents.append(intent)
                    logger.debug(f"Detected intent '{action_type}' in text: '{log_text}'")
        
        return detected_intents

    def _extract_parameters(self, text: str, action_type: str) -> Dict[str, Any]:
        """
        Helper function to extract specific parameters based on the action type.
        """
        params = {}
        if action_type == "tap":
            if "heavy" in text.lower() or "hard" in text.lower():
                params["force"] = "heavy"
            elif "light" in text.lower() or "gentle" in text.lower() or "slight" in text.lower():
                params["force"] = "light"
            else:
                params["force"] = "medium"
                
        if action_type == "calibrate":
            if "rough" in text.lower():
                params["level"] = "rough"
            else:
                params["level"] = "fine"
                
        return params


class SkillRegistry:
    """
    Manages the mapping between extracted intents and executable skill objects.
    """
    
    def __init__(self):
        self._skills: Dict[str, OperationalSkill] = {}
        self._load_skills()

    def _load_skills(self):
        """Initializes available skills."""
        self.register_skill(CalibrationSkill())
        self.register_skill(PercussiveMaintenanceSkill())
        self.register_skill(InspectionSkill())

    def register_skill(self, skill: OperationalSkill):
        if skill.name in self._skills:
            logger.warning(f"Overwriting existing skill: {skill.name}")
        self._skills[skill.name] = skill
        logger.info(f"Skill registered: {skill.name}")

    def get_skill(self, name: str) -> Optional[OperationalSkill]:
        return self._skills.get(name)


class MaintenanceSkillOrchestrator:
    """
    Main controller class. It takes raw logs, extracts intents, 
    validates data, and orchestrates execution.
    """
    
    def __init__(self):
        self.extractor = OperatorExtractor()
        self.registry = SkillRegistry()

    def process_log_to_action(self, log_entry: str, context: OperationalContext) -> Dict[str, Any]:
        """
        The primary workflow function.
        
        Args:
            log_entry: The unstructured text log.
            context: The current operational context of the machine.
            
        Returns:
            A report dictionary detailing what was parsed and executed.
        """
        report = {
            "input": log_entry,
            "success": False,
            "actions_suggested": [],
            "errors": []
        }

        # 1. Validation
        if len(log_entry) > 1000:
            report["errors"].append("Log entry exceeds character limit.")
            return report

        # 2. Extraction
        intents = self.extractor.parse_log_entry(log_entry)
        
        if not intents:
            report["errors"].append("No actionable intents found.")
            logger.info(f"No intents found for: {log_entry}")
            return report

        # 3. Execution Loop
        execution_results = []
        for intent in intents:
            skill = self.registry.get_skill(intent.action_type)
            
            if skill:
                try:
                    logger.info(f"Mapping intent '{intent.action_type}' to skill execution.")
                    # Data validation before execution
                    if not self._validate_safety_constraints(intent, context):
                        msg = f"Safety check failed for action {intent.action_type}"
                        logger.error(msg)
                        report["errors"].append(msg)
                        continue

                    # Execute
                    result = skill.execute(context, **intent.parameters)
                    execution_results.append({
                        "action": intent.action_type,
                        "params": intent.parameters,
                        "executed": result
                    })
                except Exception as e:
                    logger.exception("Error during skill execution")
                    report["errors"].append(str(e))
            else:
                logger.warning(f"No skill mapping found for action: {intent.action_type}")

        report["actions_suggested"] = execution_results
        report["success"] = len(execution_results) > 0
        return report

    def _validate_safety_constraints(self, intent: ActionIntent, context: OperationalContext) -> bool:
        """
        Auxiliary function to check if the action is safe to perform given the context.
        """
        # Example: Do not calibrate if the machine is moving
        if intent.action_type == "calibrate":
            if context.state.get("motion_status") == "active":
                return False
        
        return True


# --- Usage Example ---

if __name__ == "__main__":
    # Initialize System
    orchestrator = MaintenanceSkillOrchestrator()
    
    # Define Context
    robot_state = {
        "equipment_id": "ARM-Unit-01",
        "motion_status": "idle",
        "calibration_status": "drift_detected"
    }
    ctx = OperationalContext(equipment_id="ARM-Unit-01", current_state=robot_state)

    # Sample Unstructured Logs
    logs = [
        "System noticed a drift in sensor readings. Please recalibrate the base sensors.",
        "The arm is stuck. Give it a slight tap to unjam it.",
        "Just a visual inspection of the chassis.",
        "The system is overheating, reset everything." # This won't match current skills
    ]

    print("-" * 50)
    print("Processing Maintenance Logs...")
    print("-" * 50)

    for log in logs:
        print(f"\nInput Log: {log}")
        result_report = orchestrator.process_log_to_action(log, ctx)
        print(f"Outcome: {'SUCCESS' if result_report['success'] else 'FAILED'}")
        if result_report['actions_suggested']:
            for action in result_report['actions_suggested']:
                print(f"  > Executed: {action['action']} with {action['params']}")
        if result_report['errors']:
            print(f"  > Errors: {result_report['errors']}")
    
    print("\nFinal Context State:", ctx.state)