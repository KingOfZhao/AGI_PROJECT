"""
Module: auto_implicit_micro_error_correction_85eef3
Description: Advanced detection of 'micro-errors' in implicit operations and real-time correction.
             This module models expert tacit knowledge by distinguishing between 'nominal flow'
             and 'recovery maneuvers' in continuous data streams, converting them into
             actionable 'exception handling' nodes.
Domain: anomaly_detection
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of detected signal event types."""
    NOMINAL_OPERATION = "NOMINAL"
    MICRO_ERROR = "MICRO_ERROR"
    CORRECTION_MANEUVER = "CORRECTION"
    SYSTEMIC_FAILURE = "FAILURE"


@dataclass
class SignalPoint:
    """Represents a single point in the continuous data stream."""
    timestamp: float
    value: float
    velocity: float = 0.0
    acceleration: float = 0.0


@dataclass
class DetectedNode:
    """Represents a processed node in the skill graph."""
    start_time: float
    end_time: float
    event_type: EventType
    raw_data_segment: List[SignalPoint] = field(default_factory=list)
    correction_vector: Optional[Tuple[float, float]] = None
    severity_score: float = 0.0


def _calculate_derivatives(data: List[SignalPoint]) -> List[SignalPoint]:
    """
    Helper function: Calculate velocity and acceleration for the signal stream.
    
    Args:
        data: List of SignalPoint objects.
        
    Returns:
        List of SignalPoint objects populated with derivative attributes.
        
    Raises:
        ValueError: If data is empty.
    """
    if not data:
        raise ValueError("Input data cannot be empty for derivative calculation.")
    
    n = len(data)
    processed_data = []
    
    for i in range(n):
        point = data[i]
        
        # Calculate velocity (1st derivative)
        if i < n - 1:
            dt = data[i+1].timestamp - point.timestamp
            if dt == 0:
                vel = 0.0
            else:
                vel = (data[i+1].value - point.value) / dt
        else:
            # Use backward difference for the last point
            dt = point.timestamp - data[i-1].timestamp
            vel = (point.value - data[i-1].value) / dt if dt != 0 else 0.0
            
        point.velocity = vel
        
        # Calculate acceleration (2nd derivative) - simplified
        if i > 0:
            prev_vel = data[i-1].velocity if data[i-1].velocity != 0 else vel # Handle first step logic
            # Re-calculating prev_vel properly based on current context
            if i > 1:
                 dt_prev = data[i-1].timestamp - data[i-2].timestamp
                 prev_vel = (data[i-1].value - data[i-2].value) / dt_prev if dt_prev != 0 else 0.0
            
            dt_curr = point.timestamp - data[i-1].timestamp
            acc = (vel - prev_vel) / dt_curr if dt_curr != 0 else 0.0
            point.acceleration = acc
        else:
            point.acceleration = 0.0
            
        processed_data.append(point)
        
    return processed_data


def detect_implicit_errors(
    data_stream: List[Dict[str, float]],
    baseline: float,
    threshold_sigma: float = 2.5,
    window_size: int = 5,
    jerk_sensitivity: float = 0.8
) -> List[DetectedNode]:
    """
    Core Function 1: Analyzes continuous stream to detect micro-errors and correction maneuvers.
    
    This function identifies 'jerk' (rate of change of acceleration) as a primary indicator
    of a human operator reacting to a mistake (e.g., a chef adjusting a slipping knife).
    
    Args:
        data_stream (List[Dict]): Input data format [{'t': 0.1, 'v': 10.2}, ...].
        baseline (float): The expected nominal value of the signal.
        threshold_sigma (float): Std dev multiplier for anomaly detection.
        window_size (int): Rolling window size for local statistics.
        jerk_sensitivity (float): Threshold for acceleration changes to detect corrections.
        
    Returns:
        List[DetectedNode]: A list of classified operational nodes.
        
    Example:
        >>> stream = [{'t': i*0.1, 'v': 10 + np.random.normal(0, 0.1)} for i in range(100)]
        >>> # Inject error and correction
        >>> stream[50]['v'] = 15.0 # Sudden spike
        >>> stream[51]['v'] = 10.5 # Correction back
        >>> nodes = detect_implicit_errors(stream, baseline=10.0)
    """
    # Data Validation
    if not data_stream:
        logger.warning("Empty data stream received.")
        return []
    
    try:
        # Convert to internal object format
        raw_points = [SignalPoint(timestamp=d['t'], value=d['v']) for d in data_stream]
        points = _calculate_derivatives(raw_points)
        
        nodes: List[DetectedNode] = []
        current_node_buffer: List[SignalPoint] = []
        node_start_time = points[0].timestamp
        current_state = EventType.NOMINAL_OPERATION
        
        # Calculate global statistics for anomaly detection
        values = [p.value for p in points]
        std_dev = np.std(values)
        mean_val = np.mean(values)
        
        if std_dev == 0: std_dev = 1e-6 # Avoid division by zero
        
        logger.info(f"Processing stream. Mean: {mean_val:.2f}, StdDev: {std_dev:.2f}")
        
        for i, point in enumerate(points):
            deviation = abs(point.value - baseline)
            is_anomaly = deviation > (threshold_sigma * std_dev)
            
            # Detect 'Jerk' (correction force) -> High absolute acceleration change
            is_correction = abs(point.acceleration) > jerk_sensitivity
            
            # State Machine Logic
            if current_state == EventType.NOMINAL_OPERATION:
                if is_anomaly:
                    # Close nominal node
                    if current_node_buffer:
                        nodes.append(DetectedNode(
                            start_time=node_start_time,
                            end_time=point.timestamp,
                            event_type=EventType.NOMINAL_OPERATION,
                            raw_data_segment=current_node_buffer.copy()
                        ))
                    current_node_buffer = []
                    node_start_time = point.timestamp
                    current_state = EventType.MICRO_ERROR
                    logger.debug(f"Micro-error detected at {point.timestamp}")
                    
            elif current_state == EventType.MICRO_ERROR:
                if is_correction:
                    current_state = EventType.CORRECTION_MANEUVER
                    logger.debug(f"Correction maneuver started at {point.timestamp}")
                elif not is_anomaly:
                    # Returned to nominal without correction? (Noise)
                    current_state = EventType.NOMINAL_OPERATION
                    
            elif current_state == EventType.CORRECTION_MANEUVER:
                # Check if stabilized
                if not is_anomaly and not is_correction:
                    # Close the Error+Correction node
                    current_node_buffer.append(point)
                    nodes.append(DetectedNode(
                        start_time=node_start_time,
                        end_time=point.timestamp,
                        event_type=EventType.MICRO_ERROR, # Labelled as error containing correction
                        raw_data_segment=current_node_buffer.copy(),
                        correction_vector=(point.velocity, point.acceleration),
                        severity_score=deviation / std_dev
                    ))
                    current_node_buffer = []
                    node_start_time = point.timestamp
                    current_state = EventType.NOMINAL_OPERATION
                    logger.info(f"Correction successful. Node closed at {point.timestamp}")

            current_node_buffer.append(point)
            
        # Append remaining buffer
        if current_node_buffer:
             nodes.append(DetectedNode(
                start_time=node_start_time,
                end_time=points[-1].timestamp,
                event_type=current_state,
                raw_data_segment=current_node_buffer
            ))
            
        return nodes

    except KeyError as e:
        logger.error(f"Missing key in data stream: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during detection: {e}")
        raise


def analyze_correction_skill(nodes: List[DetectedNode]) -> Dict[str, Union[float, int]]:
    """
    Core Function 2: Evaluates the quality and characteristics of detected corrections.
    
    This transforms raw nodes into 'Skill Metrics', quantifying how 'masterful' the
    recovery was (e.g., speed of recovery, magnitude of correction).
    
    Args:
        nodes (List[DetectedNode]): The output from the detection phase.
        
    Returns:
        Dict: A summary of skill metrics.
    """
    if not nodes:
        return {"status": "no_data"}

    total_ops = len(nodes)
    corrections = [n for n in nodes if n.event_type == EventType.MICRO_ERROR and n.correction_vector]
    
    avg_severity = 0.0
    avg_recovery_time = 0.0
    
    if corrections:
        severities = [n.severity_score for n in corrections]
        avg_severity = sum(severities) / len(severities)
        
        durations = [n.end_time - n.start_time for n in corrections]
        avg_recovery_time = sum(durations) / len(durations)
        
    logger.info(f"Skill Analysis: {len(corrections)} recovery maneuvers detected.")
    
    return {
        "total_segments": total_ops,
        "recovery_count": len(corrections),
        "average_anomaly_severity": round(avg_severity, 4),
        "average_recovery_duration_ms": round(avg_recovery_time * 1000, 2),
        "resilience_score": round(1.0 / (1.0 + avg_recovery_time), 4) if avg_recovery_time > 0 else 1.0
    }


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate synthetic data representing a cutting motion
    # Nominal value is 5.0. We simulate a slip at t=1.0 and a recovery.
    np.random.seed(42)
    total_steps = 200
    time_steps = np.linspace(0, 2.0, total_steps)
    
    # Nominal signal + noise
    signal_values = [5.0 + np.random.normal(0, 0.05) for _ in range(total_steps)]
    
    # Inject Micro-Error (Slip) at step 100
    # Sudden increase in value (accident)
    for i in range(100, 105):
        signal_values[i] = 5.0 + (i - 100) * 0.5 # Linear drift away
        
    # Inject Correction (Forceful return) at step 105
    for i in range(105, 110):
        signal_values[i] = signal_values[104] - (i - 105) * 0.8 # High acceleration return
        
    # Prepare input data
    stream_data = [{'t': t, 'v': v} for t, v in zip(time_steps, signal_values)]
    
    print(f"Processing {len(stream_data)} data points...")
    
    # 2. Run Detection
    try:
        detected_nodes = detect_implicit_errors(
            data_stream=stream_data,
            baseline=5.0,
            threshold_sigma=3.0, # Looser threshold for synthetic data
            jerk_sensitivity=2.0 # High sensitivity for synthetic abrupt changes
        )
        
        # 3. Analyze Skill
        metrics = analyze_correction_skill(detected_nodes)
        
        print("\n--- Detection Results ---")
        print(f"Nodes found: {len(detected_nodes)}")
        for i, node in enumerate(detected_nodes):
            if node.event_type != EventType.NOMINAL_OPERATION:
                print(f"Node {i}: Type={node.event_type.value}, Duration={node.end_time - node.start_time:.4f}s, Severity={node.severity_score:.2f}")
        
        print("\n--- Skill Metrics ---")
        for k, v in metrics.items():
            print(f"{k}: {v}")
            
    except Exception as e:
        print(f"Execution failed: {e}")