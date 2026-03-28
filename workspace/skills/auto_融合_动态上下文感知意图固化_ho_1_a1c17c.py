"""
Module: auto_融合_动态上下文感知意图固化_ho_1_a1c17c
Domain: cross_domain
Description: 
    This module implements a fusion of 'Dynamic Context-Aware Intent Solidification' 
    and 'Instruction Compliance & Anti-Interference'. 
    
    It resolves ambiguous user instructions (e.g., "that file") by analyzing the 
    execution context and history. Furthermore, it evaluates the potential risk 
    of instructions (e.g., deleting a database) to determine if the action aligns 
    with safety protocols, requiring secondary confirmation or automatically 
    intercepting destructive commands based on context.

Key Features:
    - Context-aware resolution of ambiguous pronouns/references.
    - Risk assessment engine for command evaluation.
    - Automatic interception or confirmation request for high-risk operations.
    - Comprehensive logging and error handling.

Input/Output Formats:
    - Input: User command (str), Current Context (SystemContext).
    - Output: ExecutionResult (status, message, data).

Example Usage:
    See the `if __name__ == "__main__":` block at the end of the file.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentFusionSkill")


class RiskLevel(Enum):
    """Enumeration of risk levels for user commands."""
    SAFE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ActionStatus(Enum):
    """Enumeration of action execution statuses."""
    SUCCESS = auto()
    BLOCKED = auto()
    REQUIRES_CONFIRMATION = auto()
    FAILED = auto()


@dataclass
class SystemContext:
    """
    Represents the dynamic context of the system.
    
    Attributes:
        active_files: List of files currently in focus.
        last_command: The last command executed.
        environment_variables: Current system environment state.
        recent_entities: A stack of recently accessed entities for ambiguity resolution.
    """
    active_files: List[str] = field(default_factory=list)
    last_command: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    recent_entities: List[str] = field(default_factory=list)

    def get_last_entity(self) -> Optional[str]:
        """Retrieves the most recently accessed entity."""
        return self.recent_entities[-1] if self.recent_entities else None


@dataclass
class ExecutionResult:
    """
    Represents the result of an intent processing attempt.
    
    Attributes:
        status: The outcome status of the operation.
        message: Human-readable description of the result.
        resolved_intent: The fully resolved command string.
        risk_score: The calculated risk score (0.0 to 1.0).
    """
    status: ActionStatus
    message: str
    resolved_intent: str
    risk_score: float = 0.0


def _validate_input(command: str, context: SystemContext) -> None:
    """
    Validates the input parameters for the core functions.
    
    Args:
        command: The user input string.
        context: The system context object.
        
    Raises:
        ValueError: If command is empty or context is invalid.
        TypeError: If input types are incorrect.
    """
    if not isinstance(command, str):
        raise TypeError(f"Command must be a string, got {type(command)}")
    if not command.strip():
        raise ValueError("Command cannot be empty or whitespace only.")
    if not isinstance(context, SystemContext):
        raise TypeError(f"Context must be a SystemContext object, got {type(context)}")


def _assess_risk(command: str, context: SystemContext) -> Tuple[RiskLevel, float]:
    """
    (Auxiliary Function) Evaluates the risk level of a given command.
    
    Uses keyword matching and context analysis to determine risk.
    
    Args:
        command: The resolved command string.
        context: The system context.
        
    Returns:
        A tuple containing the RiskLevel enum and a float score (0.0-1.0).
    """
    risk_keywords = {
        'delete': 0.6,
        'remove': 0.5,
        'drop': 0.8,
        'format': 0.9,
        'shutdown': 0.7,
        'database': 0.4, # Modifier
        'system': 0.4    # Modifier
    }
    
    score = 0.0
    cmd_lower = command.lower()
    
    # Base keyword scoring
    for word, weight in risk_keywords.items():
        if word in cmd_lower:
            score += weight
            
    # Contextual amplification (e.g., deleting a database is worse than a file)
    if 'database' in cmd_lower and 'delete' in cmd_lower:
        score += 0.3
    if 'system' in cmd_lower and 'delete' in cmd_lower:
        score += 0.4
        
    # Cap score at 1.0
    score = min(score, 1.0)
    
    # Determine Enum
    if score >= 0.9:
        return RiskLevel.CRITICAL, score
    elif score >= 0.7:
        return RiskLevel.HIGH, score
    elif score >= 0.4:
        return RiskLevel.MEDIUM, score
    elif score > 0:
        return RiskLevel.LOW, score
    else:
        return RiskLevel.SAFE, score


def resolve_ambiguous_intent(command: str, context: SystemContext) -> str:
    """
    (Core Function 1) Resolves ambiguous references in the user command using context.
    
    Identifies pronouns or vague references (e.g., "it", "that", "the file") 
    and replaces them with specific entities from the system context.
    
    Args:
        command: The raw user command.
        context: The current system context.
        
    Returns:
        The resolved command string with specific entities.
        
    Raises:
        ValueError: If ambiguity cannot be resolved.
    """
    logger.info(f"Resolving intent for command: '{command}'")
    
    # Pattern to find vague references
    # Matches "that [noun]", "the [noun]", or standalone pronouns like "it"
    vague_patterns = [
        r"\b(that|this)\s+(file|document|table|database)\b",
        r"\b(the)\s+(file|document|table|database)\b",
        r"\b(it)\b"
    ]
    
    resolved_cmd = command
    entity_found = False
    
    for pattern in vague_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            target_entity = context.get_last_entity()
            if not target_entity:
                # Try to infer from active files if recent entities is empty
                if context.active_files:
                    target_entity = context.active_files[0]
                    logger.warning(f"Recent entities empty, defaulting to active file: {target_entity}")
                else:
                    raise ValueError(
                        f"Ambiguity detected ('{match.group()}') but no context available to resolve it."
                    )
            
            # Replace the vague phrase with the specific entity
            # We replace the whole match to be safe
            replacement = f"'{target_entity}'"
            resolved_cmd = re.sub(pattern, replacement, command, flags=re.IGNORECASE)
            entity_found = True
            logger.info(f"Resolved '{match.group()}' to {replacement}")
            break
            
    return resolved_cmd if entity_found else command


def evaluate_and_execute_intent(command: str, context: SystemContext, auto_confirm: bool = False) -> ExecutionResult:
    """
    (Core Function 2) Evaluates the risk of the resolved intent and decides execution flow.
    
    This function acts as the safety gate. It calculates the risk score. 
    If the risk is too high, it blocks the action. If it is moderate, 
    it requests confirmation (simulated here). Otherwise, it proceeds.
    
    Args:
        command: The raw user command.
        context: The system context.
        auto_confirm: If True, bypasses confirmation prompts (for automation).
        
    Returns:
        An ExecutionResult object containing the status and details.
    """
    try:
        _validate_input(command, context)
        
        # Step 1: Resolve Ambiguity
        resolved_cmd = resolve_ambiguous_intent(command, context)
        
        # Step 2: Assess Risk
        risk_level, risk_score = _assess_risk(resolved_cmd, context)
        logger.info(f"Risk Assessment: Level={risk_level.name}, Score={risk_score:.2f}")
        
        # Step 3: Decision Logic
        if risk_level == RiskLevel.CRITICAL:
            logger.critical(f"Command blocked due to CRITICAL risk level: {resolved_cmd}")
            return ExecutionResult(
                status=ActionStatus.BLOCKED,
                message="Action blocked: Critical risk detected. Manual override required.",
                resolved_intent=resolved_cmd,
                risk_score=risk_score
            )
            
        elif risk_level == RiskLevel.HIGH:
            if not auto_confirm:
                logger.warning(f"High risk action requires confirmation: {resolved_cmd}")
                # In a real system, this would trigger a UI prompt. 
                # Here we return a status indicating confirmation is needed.
                return ExecutionResult(
                    status=ActionStatus.REQUIRES_CONFIRMATION,
                    message=f"High risk action '{resolved_cmd}' requires confirmation.",
                    resolved_intent=resolved_cmd,
                    risk_score=risk_score
                )
            else:
                logger.warning(f"Auto-confirming HIGH risk action: {resolved_cmd}")
        
        # Step 4: Simulate Execution
        logger.info(f"Executing command: {resolved_cmd}")
        # Update context (simulation)
        context.last_command = resolved_cmd
        if "open" in resolved_cmd.lower() or "select" in resolved_cmd.lower():
            # Extract entity name crudely for context update
            match = re.search(r"'([^']+)'", resolved_cmd)
            if match:
                entity = match.group(1)
                if entity not in context.recent_entities:
                    context.recent_entities.append(entity)
        
        return ExecutionResult(
            status=ActionStatus.SUCCESS,
            message="Command executed successfully.",
            resolved_intent=resolved_cmd,
            risk_score=risk_score
        )
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
        return ExecutionResult(
            status=ActionStatus.FAILED,
            message=str(ve),
            resolved_intent=command,
            risk_score=0.0
        )
    except Exception as e:
        logger.exception("Unexpected error during intent evaluation")
        return ExecutionResult(
            status=ActionStatus.FAILED,
            message=f"Internal system error: {str(e)}",
            resolved_intent=command,
            risk_score=0.0
        )


if __name__ == "__main__":
    # Example Usage Demonstration
    
    # 1. Setup Context
    # Simulating a system where 'customer_db.sql' was just accessed
    current_context = SystemContext(
        active_files=["report.pdf", "data.csv"],
        recent_entities=["customer_db.sql"],
        environment_variables={"MODE": "PRODUCTION"}
    )
    
    print("--- Scenario 1: Ambiguous Intent Resolution ---")
    # User says "delete that file" referring to 'customer_db.sql'
    user_cmd_1 = "delete that file"
    result_1 = evaluate_and_execute_intent(user_cmd_1, current_context)
    print(f"Input: {user_cmd_1}")
    print(f"Resolved: {result_1.resolved_intent}")
    print(f"Status: {result_1.status.name}")
    print(f"Message: {result_1.message}\n")
    
    print("--- Scenario 2: High Risk Interception ---")
    # User tries to drop the database explicitly
    user_cmd_2 = "drop database customer_db"
    result_2 = evaluate_and_execute_intent(user_cmd_2, current_context)
    print(f"Input: {user_cmd_2}")
    print(f"Status: {result_2.status.name}")
    print(f"Risk Score: {result_2.risk_score}")
    print(f"Message: {result_2.message}\n")
    
    print("--- Scenario 3: Safe Execution ---")
    # User reads a file
    user_cmd_3 = "read report.pdf"
    result_3 = evaluate_and_execute_intent(user_cmd_3, current_context)
    print(f"Input: {user_cmd_3}")
    print(f"Status: {result_3.status.name}")
    print(f"Message: {result_3.message}\n")