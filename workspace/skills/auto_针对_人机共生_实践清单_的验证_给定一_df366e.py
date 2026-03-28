"""
Module: symbiosis_action_validator.py
Description: Validates AI-generated action plans against "Human-Computer Symbiosis" standards.
             Specifically checks if actionable items contain "falsifiable boundary conditions"
             and executable granularity (e.g., specific thresholds and logical triggers).

Author: AGI System
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """Data structure for individual action validation results."""
    action_id: int
    original_text: str
    is_valid: bool
    severity: ValidationSeverity
    score: float  # 0.0 to 1.0
    feedback: str
    detected_conditions: List[str]
    detected_metrics: List[str]


@dataclass
class PlanAuditReport:
    """Aggregate report for the entire action plan."""
    total_actions: int
    valid_actions: int
    average_score: float
    details: List[ValidationResult]
    summary_feedback: str


# --- Configuration Constants ---
# Regex patterns to identify metrics (numbers with units/percentages)
METRIC_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?%?)'  # Number/Percentage
    r'\s*(?:人|元|小时|天|次|单|件|个|客户|流量|损耗|利润|点击|转化)?'  # Contextual units (Chinese)
    r'(?:\/|\s*(?:per|每天|每小时))?', 
    re.IGNORECASE
)

# Logic keywords indicating boundary conditions
BOUNDARY_KEYWORDS = [
    "如果", "若", "当", "一旦", "假设",  # Chinese
    "if", "when", "given", "assuming", "once"  # English
]

# Action keywords indicating specific execution
ACTION_KEYWORDS = [
    "则", "尝试", "执行", "启动", "调整", "降低", "提高", # Chinese
    "then", "try", "execute", "adjust", "reduce", "increase" # English
]


def _extract_structured_components(text: str) -> Dict[str, Any]:
    """
    Helper function: Extracts logical triggers, metrics, and action verbs from text.
    
    Args:
        text (str): The action item description.
        
    Returns:
        Dict[str, Any]: Dictionary containing 'triggers', 'metrics', and 'actions'.
    """
    logger.debug(f"Extracting components from: {text}")
    
    # Normalize text
    clean_text = text.strip()
    
    # Find metrics
    metrics = METRIC_PATTERN.findall(clean_text)
    
    # Find boundary keywords
    triggers = [kw for kw in BOUNDARY_KEYWORDS if kw in clean_text]
    
    # Find action keywords
    actions = [kw for kw in ACTION_KEYWORDS if kw in clean_text]
    
    return {
        "triggers": triggers,
        "metrics": metrics,
        "actions": actions
    }


def validate_single_action(action_text: str, action_id: int = 0) -> ValidationResult:
    """
    Core Function 1: Validates a single action item for falsifiable boundary conditions.
    
    Criteria for validity:
    1. Must contain at least one quantifiable metric (e.g., "10%", "100元").
    2. Must contain a logical trigger/condition (e.g., "If X happens").
    3. Must imply a specific execution (checked via action verbs).
    
    Args:
        action_text (str): The text description of the action.
        action_id (int): Identifier for the action.
        
    Returns:
        ValidationResult: Detailed validation object.
    """
    if not action_text or not isinstance(action_text, str):
        logger.error(f"Action ID {action_id}: Invalid input type or empty.")
        return ValidationResult(
            action_id=action_id,
            original_text=str(action_text),
            is_valid=False,
            severity=ValidationSeverity.FAIL,
            score=0.0,
            feedback="Input is empty or not a string.",
            detected_conditions=[],
            detected_metrics=[]
        )

    components = _extract_structured_components(action_text)
    score = 0.0
    feedback_msgs = []
    
    # Check 1: Quantifiable Metrics (Weight: 40%)
    if components["metrics"]:
        score += 0.4
        feedback_msgs.append(f"Contains metrics: {components['metrics']}")
    else:
        feedback_msgs.append("Missing quantifiable metrics (e.g., '<10%', '100 units').")

    # Check 2: Boundary Conditions (Weight: 40%)
    if components["triggers"]:
        score += 0.4
        feedback_msgs.append(f"Contains logic triggers: {components['triggers']}")
    else:
        feedback_msgs.append("Missing conditional logic (e.g., 'If...', 'When...').")

    # Check 3: Actionability (Weight: 20%)
    if components["actions"]:
        score += 0.2
    else:
        feedback_msgs.append("Action verb is implicit or missing.")

    # Determine overall validity
    # A "Symbiotic" action usually needs both metrics and conditions (Score >= 0.8)
    is_valid = score >= 0.8
    severity = ValidationSeverity.PASS if is_valid else (ValidationSeverity.WARNING if score >= 0.5 else ValidationSeverity.FAIL)
    
    final_feedback = " | ".join(feedback_msgs)
    logger.info(f"Action {action_id} validated. Score: {score}. Valid: {is_valid}")

    return ValidationResult(
        action_id=action_id,
        original_text=action_text,
        is_valid=is_valid,
        severity=severity,
        score=score,
        feedback=final_feedback,
        detected_conditions=components["triggers"],
        detected_metrics=components["metrics"]
    )


def generate_audit_report(action_list: List[str]) -> PlanAuditReport:
    """
    Core Function 2: Generates a comprehensive audit report for a list of actions.
    
    This function iterates through a list of proposed actions, validates each one,
    and aggregates the results into a strategic report.
    
    Args:
        action_list (List[str]): A list of action item strings.
        
    Returns:
        PlanAuditReport: The aggregated report.
        
    Raises:
        ValueError: If the input list is empty.
    """
    if not action_list:
        logger.error("Input action list is empty.")
        raise ValueError("Action list cannot be empty.")
    
    logger.info(f"Starting audit for {len(action_list)} actions...")
    
    results: List[ValidationResult] = []
    total_score = 0.0
    valid_count = 0
    
    for idx, action in enumerate(action_list):
        result = validate_single_action(action, action_id=idx)
        results.append(result)
        total_score += result.score
        if result.is_valid:
            valid_count += 1
            
    avg_score = total_score / len(action_list) if action_list else 0.0
    
    # Generate Summary Feedback
    if avg_score >= 0.8:
        summary = "Excellent granularity. The plan demonstrates high Human-Machine Symbiosis potential with clear falsifiable conditions."
    elif avg_score >= 0.5:
        summary = "Partial compliance. Some actions are too vague for automated verification. Recommend adding specific thresholds."
    else:
        summary = "Poor granularity. The plan is primarily composed of vague suggestions. Fails the 'Falsifiable Boundary' check."

    logger.info(f"Audit complete. Average Score: {avg_score:.2f}. Valid Actions: {valid_count}/{len(action_list)}")
    
    return PlanAuditReport(
        total_actions=len(action_list),
        valid_actions=valid_count,
        average_score=avg_score,
        details=results,
        summary_feedback=summary
    )


# --- Usage Example ---
if __name__ == "__main__":
    # Sample Input: A mix of good (symbiotic) and bad (vague) actions
    sample_actions = [
        "若客流<100人/天且损耗率>10%，则尝试降价5%",  # Good: Conditional + Metrics
        "If conversion rate drops below 2%, increase ad spend by $50", # Good: Conditional + Metrics
        "提升服务质量",  # Bad: Vague, no metrics
        "Try to reduce waste", # Bad: No condition, no specific amount
        "当库存超过500件时，启动买一送一活动" # Good: Conditional + Metric
    ]

    print(f"--- Starting Validation for Goal: 'Improve Street Vendor Profit' ---\n")
    
    try:
        report = generate_audit_report(sample_actions)
        
        print(f"SUMMARY: {report.summary_feedback}")
        print(f"TOTAL ACTIONS: {report.total_actions}")
        print(f"SYMBIOTIC ACTIONS: {report.valid_actions} ({(report.valid_actions/report.total_actions)*100:.1f}%)")
        print("-" * 60)
        
        for detail in report.details:
            status = "✅ VALID" if detail.is_valid else "❌ INVALID"
            print(f"[{status}] ID {detail.action_id}: {detail.original_text}")
            print(f"    Score: {detail.score:.2f} | Feedback: {detail.feedback}")
            print(f"    Metrics: {detail.detected_metrics}")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")