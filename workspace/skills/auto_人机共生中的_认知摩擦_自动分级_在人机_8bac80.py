"""
Module: auto_cognitive_friction_grader
Description: Human-Computer Interaction module for AGI systems.
             This module implements a classifier to automatically grade 'cognitive friction'
             in human-machine symbiotic loops. It identifies high-friction practice steps
             (difficult or error-prone for humans) to prioritize AI assistance or takeover.
"""

import logging
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FrictionLevel(Enum):
    """Enumeration representing the level of cognitive friction."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class PracticeNode:
    """
    Represents a single step in a human practice workflow.
    
    Attributes:
        node_id: Unique identifier for the step.
        complexity_score: Intrinsic complexity of the task (0.0 to 1.0).
        context_switches: Number of context switches required.
        required_precision: Level of precision required (0.0 to 1.0).
        historical_error_rate: Observed error rate in past executions (0.0 to 1.0).
        time_pressure_factor: Urgency of the task (0.0 to 1.0).
    """
    node_id: str
    complexity_score: float
    context_switches: int
    required_precision: float
    historical_error_rate: float
    time_pressure_factor: float

def _validate_input_data(node: PracticeNode) -> None:
    """
    Helper function to validate the input data boundaries.
    
    Args:
        node: The PracticeNode to validate.
        
    Raises:
        ValueError: If any numeric field is out of the [0, 1] range or negative.
        TypeError: If data types are incorrect.
    """
    logger.debug(f"Validating data for node {node.node_id}")
    
    # Check types implicitly via dataclass, but check boundaries
    fields_to_check = [
        ('complexity_score', node.complexity_score),
        ('required_precision', node.required_precision),
        ('historical_error_rate', node.historical_error_rate),
        ('time_pressure_factor', node.time_pressure_factor)
    ]
    
    for name, value in fields_to_check:
        if not (0.0 <= value <= 1.0):
            msg = f"Invalid value for {name}: {value}. Must be between 0.0 and 1.0."
            logger.error(msg)
            raise ValueError(msg)
            
    if node.context_switches < 0:
        msg = f"context_switches cannot be negative: {node.context_switches}"
        logger.error(msg)
        raise ValueError(msg)

def calculate_friction_score(node: PracticeNode, weight_profile: Optional[Dict[str, float]] = None) -> float:
    """
    Calculates a raw cognitive friction score based on node attributes.
    
    Uses a weighted heuristic model to combine complexity, error rate, and other factors
    into a single score representing the 'friction' experienced by a human operator.
    
    Args:
        node: The PracticeNode containing step attributes.
        weight_profile: Optional dictionary of weights for different factors.
                        Default weights prioritize historical error rate and complexity.
                        
    Returns:
        A float score between 0.0 and 1.0 representing friction intensity.
        
    Raises:
        ValueError: If input validation fails.
    """
    try:
        _validate_input_data(node)
    except ValueError as e:
        logger.error(f"Input validation failed for node {node.node_id}: {e}")
        raise

    # Default weights if none provided
    if weight_profile is None:
        weight_profile = {
            'complexity': 0.25,
            'error_rate': 0.35,
            'precision': 0.15,
            'time_pressure': 0.15,
            'context_switch': 0.10
        }
    
    # Normalize context switches (assuming > 5 switches is max friction for this factor)
    norm_context_switch = min(node.context_switches / 5.0, 1.0)
    
    # Weighted Sum Model
    score = (
        (node.complexity_score * weight_profile['complexity']) +
        (node.historical_error_rate * weight_profile['error_rate']) +
        (node.required_precision * weight_profile['precision']) +
        (node.time_pressure_factor * weight_profile['time_pressure']) +
        (norm_context_switch * weight_profile['context_switch'])
    )
    
    # Ensure result is capped at 1.0
    final_score = min(max(score, 0.0), 1.0)
    logger.info(f"Calculated raw friction score for {node.node_id}: {final_score:.4f}")
    
    return final_score

def classify_friction_level(score: float) -> FrictionLevel:
    """
    Maps a raw friction score to a discrete FrictionLevel enum.
    
    Args:
        score: A float between 0.0 and 1.0.
        
    Returns:
        FrictionLevel: The categorized level of friction.
        
    Raises:
        ValueError: If score is not between 0.0 and 1.0.
    """
    if not (0.0 <= score <= 1.0):
        logger.error(f"Invalid score input: {score}")
        raise ValueError("Score must be between 0.0 and 1.0")
        
    if score < 0.25:
        return FrictionLevel.LOW
    elif score < 0.50:
        return FrictionLevel.MEDIUM
    elif score < 0.75:
        return FrictionLevel.HIGH
    else:
        return FrictionLevel.CRITICAL

def analyze_workflow_friction(nodes: List[PracticeNode]) -> Dict[str, Any]:
    """
    Analyzes a list of practice nodes to identify high-friction steps.
    
    This is the main entry point for the AGI system to evaluate a workflow.
    It returns detailed analysis including which nodes should be prioritized for AI takeover.
    
    Args:
        nodes: A list of PracticeNode objects representing a workflow.
        
    Returns:
        A dictionary containing:
        - 'node_analysis': List of dicts with node ID, score, and level.
        - 'average_friction': Mean friction score of the workflow.
        - 'ai_intervention_candidates': List of node IDs with HIGH or CRITICAL friction.
    """
    if not nodes:
        logger.warning("Empty node list provided for analysis.")
        return {'node_analysis': [], 'average_friction': 0.0, 'ai_intervention_candidates': []}

    analysis_results = []
    raw_scores = []
    
    logger.info(f"Starting friction analysis for {len(nodes)} nodes...")
    
    for node in nodes:
        try:
            score = calculate_friction_score(node)
            level = classify_friction_level(score)
            
            raw_scores.append(score)
            
            analysis_results.append({
                'node_id': node.node_id,
                'friction_score': score,
                'level': level.name
            })
        except Exception as e:
            logger.error(f"Skipping node {node.node_id} due to error: {e}")
            continue

    # Calculate aggregate stats
    avg_friction = statistics.mean(raw_scores) if raw_scores else 0.0
    
    # Identify candidates for AI intervention (High or Critical friction)
    candidates = [
        res['node_id'] for res in analysis_results 
        if res['level'] in [FrictionLevel.HIGH.name, FrictionLevel.CRITICAL.name]
    ]
    
    report = {
        'node_analysis': analysis_results,
        'average_friction': avg_friction,
        'ai_intervention_candidates': candidates
    }
    
    logger.info(f"Analysis complete. Found {len(candidates)} intervention candidates.")
    return report

# --- Usage Example ---
if __name__ == "__main__":
    # Example Scenario: A complex data entry workflow
    # Step 1: Simple login (Low friction)
    # Step 2: Transcribing handwritten notes (High friction, high error rate)
    # Step 3: Submitting form under time pressure (Medium friction)
    
    workflow_steps = [
        PracticeNode(
            node_id="step_001_login",
            complexity_score=0.1,
            context_switches=0,
            required_precision=0.5,
            historical_error_rate=0.05,
            time_pressure_factor=0.1
        ),
        PracticeNode(
            node_id="step_002_transcribe_notes",
            complexity_score=0.8,
            context_switches=4,
            required_precision=0.95,
            historical_error_rate=0.65, # Humans struggle here
            time_pressure_factor=0.4
        ),
        PracticeNode(
            node_id="step_003_submit_report",
            complexity_score=0.3,
            context_switches=1,
            required_precision=0.5,
            historical_error_rate=0.1,
            time_pressure_factor=0.9 # High pressure
        )
    ]
    
    print("--- AGI Cognitive Friction Analysis ---")
    results = analyze_workflow_friction(workflow_steps)
    
    print(f"Workflow Average Friction: {results['average_friction']:.2f}")
    print("Detailed Analysis:")
    for item in results['node_analysis']:
        print(f"  Node: {item['node_id']} | Score: {item['friction_score']:.2f} | Level: {item['level']}")
    
    print(f"Recommended for AI Takeover: {results['ai_intervention_candidates']}")