"""
Module: cognitive_friction_feedback_loop.py

This module implements a 'Cognitive Friction' feedback loop mechanism for AGI systems.
The core concept is to prevent immediate execution of structured code derived from
ambiguous natural language intents. Instead, it forces a 'Back-Translation' process
where the structured logic is converted back into a human-readable natural language
description for verification.

This process creates a necessary 'friction' to ensure Human-AI intent alignment,
acting as a critical safety and clarification layer in Human-Computer Interaction.

Author: Senior Python Engineer (AGI System Core)
Domain: Human-Computer Interaction
"""

import logging
import json
from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveFeedbackLoop")


class IntentCategory(Enum):
    """Enumeration of possible intent categories."""
    DATA_PROCESSING = "data_processing"
    SYSTEM_CONTROL = "system_control"
    INFORMATION_RETRIEVAL = "information_retrieval"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk assessment levels for the proposed action."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class StructuredIntent:
    """
    Represents the AI's interpretation of user intent in a structured format.
    
    Attributes:
        action: The primary action to be taken (e.g., 'delete', 'modify', 'query').
        target: The object or entity the action is performed upon.
        parameters: Specific constraints or modifiers for the action.
        category: Classification of the intent.
        confidence: AI's confidence score (0.0 to 1.0).
    """
    action: str
    target: str
    parameters: Dict[str, Any]
    category: IntentCategory
    confidence: float

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class FeedbackResult:
    """
    Result of the cognitive friction loop analysis.
    
    Attributes:
        human_readable_description: The back-translated natural language description.
        requires_confirmation: Whether the action needs explicit user approval.
        risk_level: Estimated risk of the action.
        ambiguity_detected: Flags if the intent was ambiguous.
    """
    human_readable_description: str
    requires_confirmation: bool
    risk_level: RiskLevel
    ambiguity_detected: bool


def _assess_action_risk(structured_intent: StructuredIntent) -> RiskLevel:
    """
    Helper function: Analyzes the structured intent to determine potential risk.
    
    This acts as a safeguard to force confirmation for sensitive operations even if
    confidence is high, or to allow low-risk operations to proceed automatically.
    
    Args:
        structured_intent: The structured data representing the intent.
        
    Returns:
        RiskLevel: The calculated risk level enum.
    """
    logger.debug(f"Assessing risk for action: {structured_intent.action}")
    
    # Heuristic risk assessment logic
    high_risk_keywords = ['delete', 'remove', 'drop', 'execute', 'shutdown']
    medium_risk_keywords = ['modify', 'update', 'write', 'send']
    
    action_lower = structured_intent.action.lower()
    
    if action_lower in high_risk_keywords:
        return RiskLevel.CRITICAL
    if action_lower in medium_risk_keywords:
        return RiskLevel.MEDIUM
    if structured_intent.category == IntentCategory.UNKNOWN:
        return RiskLevel.HIGH
        
    return RiskLevel.LOW


def translate_code_to_natural_language(structured_intent: StructuredIntent) -> str:
    """
    Core Function 1: Back-Translation Engine.
    
    Converts a StructuredIntent object (the 'code' representation) back into a
    polite, querying natural language string. This creates 'Cognitive Friction'
    by forcing the system to articulate its understanding.
    
    Args:
        structured_intent: The internal representation of the parsed intent.
        
    Returns:
        A string representing the AI's understanding to be presented to the user.
        
    Raises:
        ValueError: If the structured intent is incomplete.
    """
    if not structured_intent.action or not structured_intent.target:
        logger.error("Translation failed: Missing action or target.")
        raise ValueError("Cannot translate incomplete intent.")
    
    logger.info("Translating structured code to natural language...")
    
    # Template-based Natural Language Generation (NLG)
    # In a real AGI, this would use an LLM. Here we use structured templates.
    
    base_templates = {
        "delete": "Are you sure you want to permanently remove {target}?",
        "update": "I understand that you want to update {target} with parameters {params}. Is this correct?",
        "query": "I will search for {target} based on your criteria. Shall I proceed?",
        "default": "I interpreted your command as: {action} on {target}. Do you mean to do this?"
    }
    
    template = base_templates.get(
        structured_intent.action.lower(), 
        base_templates["default"]
    )
    
    # Format parameters for readability
    params_str = ", ".join([f"{k}={v}" for k, v in structured_intent.parameters.items()])
    if not params_str:
        params_str = "none"
        
    description = template.format(
        action=structured_intent.action,
        target=structured_intent.target,
        params=params_str
    )
    
    # Add ambiguity warning if confidence is low
    if structured_intent.confidence < 0.75:
        description += " (Note: I am not very confident about this interpretation, please verify carefully.)"
        
    return description


def evaluate_alignment_quality(structured_intent: StructuredIntent) -> FeedbackResult:
    """
    Core Function 2: Feedback Loop Evaluator.
    
    Evaluates the structured intent to decide if the system should proceed
    automatically or if it must pause and ask for human confirmation (Cognitive Friction).
    
    It combines confidence scores and risk assessment to make this decision.
    
    Args:
        structured_intent: The internal representation of the parsed intent.
        
    Returns:
        FeedbackResult: An object containing the human-readable description and decision flags.
    """
    logger.info("Evaluating alignment quality...")
    
    # Step 1: Back-translate to natural language
    try:
        description = translate_code_to_natural_language(structured_intent)
    except ValueError as e:
        logger.critical(f"Alignment failed due to translation error: {e}")
        # Return a safe default requiring intervention
        return FeedbackResult(
            human_readable_description="I encountered an error understanding the context. Please clarify.",
            requires_confirmation=True,
            risk_level=RiskLevel.CRITICAL,
            ambiguity_detected=True
        )
    
    # Step 2: Assess Risk
    risk = _assess_action_risk(structured_intent)
    
    # Step 3: Determine if confirmation is needed
    # Logic: If Risk > LOW or Confidence < 0.9, we need confirmation.
    needs_confirmation = False
    if risk.value > RiskLevel.LOW.value:
        needs_confirmation = True
        logger.info(f"Confirmation required due to risk level: {risk.name}")
    elif structured_intent.confidence < 0.90:
        needs_confirmation = True
        logger.info("Confirmation required due to lower confidence score.")
    
    # Step 4: Check for ambiguity
    is_ambiguous = structured_intent.confidence < 0.80 or structured_intent.category == IntentCategory.UNKNOWN
    
    return FeedbackResult(
        human_readable_description=description,
        requires_confirmation=needs_confirmation,
        risk_level=risk,
        ambiguity_detected=is_ambiguous
    )


def execute_cognitive_loop(user_input: str, mock_ai_parser: callable) -> None:
    """
    Orchestrator function demonstrating the full workflow.
    
    Args:
        user_input: The raw natural language string from the user.
        mock_ai_parser: A callable that simulates the NLU parsing (Intent -> Code).
    """
    print(f"\n>>> User Input: {user_input}")
    
    try:
        # Phase 1: Intent Parsing (NLU)
        # In a real system, this converts text to StructuredIntent
        intent_data = mock_ai_parser(user_input)
        structured_intent = StructuredIntent(**intent_data)
        
        # Phase 2: Cognitive Friction Generation
        # We analyze the code and generate feedback
        feedback = evaluate_alignment_quality(structured_intent)
        
        # Phase 3: System Response
        print(f"System Analysis [Risk: {feedback.risk_level.name}]:")
        print(f"\"{feedback.human_readable_description}\"")
        
        if feedback.requires_confirmation:
            print("[ACTION REQUIRED] Waiting for user confirmation...")
        else:
            print("[AUTO-EXECUTE] Proceeding with low-risk action.")
            
    except Exception as e:
        logger.error(f"Critical failure in cognitive loop: {e}")
        print("System Error: Unable to process intent safely.")


# --- Usage Examples and Mocks ---

def mock_nlu_parser_high_risk(text: str) -> Dict:
    """Simulates an AI parsing a dangerous command."""
    return {
        "action": "DELETE",
        "target": "production_database",
        "parameters": {"rows": "all", "backup": False},
        "category": IntentCategory.SYSTEM_CONTROL,
        "confidence": 0.92
    }

def mock_nlu_parser_ambiguous(text: str) -> Dict:
    """Simulates an AI parsing a vague command."""
    return {
        "action": "process",
        "target": "files",
        "parameters": {},
        "category": IntentCategory.UNKNOWN,
        "confidence": 0.55
    }

if __name__ == "__main__":
    print("--- Initializing Cognitive Friction Feedback Loop Demo ---")
    
    # Example 1: High Risk Action (Should trigger friction)
    execute_cognitive_loop(
        "Remove all data from the production database", 
        mock_nlu_parser_high_risk
    )
    
    # Example 2: Ambiguous Intent (Should trigger friction)
    execute_cognitive_loop(
        "Handle the files", 
        mock_nlu_parser_ambiguous
    )