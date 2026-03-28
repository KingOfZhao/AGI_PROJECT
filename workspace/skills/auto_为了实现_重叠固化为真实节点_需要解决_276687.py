"""
Module: auto_causality_node_consolidator
Description: Implements a Causal Extraction Algorithm to identify 'Necessary Conditions'
             in time-series interaction logs and compress them into 'Cognitive Skill Nodes'.
             This facilitates the transition from overlapping interaction patterns to
             consolidated, reusable skill primitives in an AGI system.
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class InteractionEvent:
    """Represents a single atomic interaction in the log."""
    timestamp: datetime.datetime
    action_type: str  # e.g., 'copy', 'paste', 'edit', 'open'
    target_object: str # e.g., 'file_v1', 'clipboard_buffer'
    metadata: Dict[str, any] = field(default_factory=dict)

    def __str__(self):
        return f"{self.action_type}:{self.target_object}"

@dataclass
class CognitiveSkillNode:
    """Represents a consolidated skill node derived from interactions."""
    node_id: str
    pattern_sequence: List[str] # The action sequence defining this skill
    frequency: int
    compression_ratio: float
    last_updated: datetime.datetime

# --- Helper Functions ---

def validate_interaction_stream(events: List[InteractionEvent]) -> bool:
    """
    Validates the integrity of the input time-series data.
    Ensures chronological order and data completeness.
    
    Args:
        events (List[InteractionEvent]): Raw interaction logs.
        
    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if not events:
        logger.warning("Empty event stream provided.")
        return False
    
    # Check chronological order
    for i in range(1, len(events)):
        if events[i].timestamp < events[i-1].timestamp:
            logger.error(f"Timestamp violation at index {i}: Time travel detected.")
            raise ValueError("Interaction events must be sorted chronologically.")
        
        # Check for nulls in critical fields
        if not events[i].action_type or not events[i].target_object:
            raise ValueError(f"Missing critical data at index {i}")
            
    logger.info(f"Validated {len(events)} interaction events successfully.")
    return True

def calculate_frequency_threshold(event_count: int) -> int:
    """
    Determines the minimum frequency required for a pattern to be considered 'Causal'.
    Simple heuristic: 1% of total events or min 3 occurrences.
    """
    return max(3, int(event_count * 0.01))

# --- Core Functions ---

def extract_causal_sequences(
    events: List[InteractionEvent], 
    window_size: int = 5
) -> Dict[Tuple[str, ...], int]:
    """
    Extracts frequent action sequences (potential causal chains) from logs.
    This identifies 'Necessary Conditions' by finding patterns that consistently
    precede a specific outcome or appear together.
    
    Args:
        events (List[InteractionEvent]): The stream of interaction events.
        window_size (int): The max length of the sequence to analyze.
        
    Returns:
        Dict[Tuple[str, ...], int]: A map of sequence tuples to their occurrence count.
    """
    if window_size < 2:
        raise ValueError("Window size must be at least 2 to form a sequence.")

    sequence_counts: Dict[Tuple[str, ...], int] = defaultdict(int)
    total_events = len(events)
    
    # Sliding window to capture sequences
    for i in range(total_events - window_size + 1):
        # Extract the 'Action' signature for the window
        window = events[i : i + window_size]
        sequence = tuple(e.action_type for e in window)
        
        # Basic redundancy filtering: ignore sequences of identical actions
        if len(set(sequence)) == 1:
            continue
            
        sequence_counts[sequence] += 1

    logger.info(f"Found {len(sequence_counts)} raw sequence patterns.")
    return sequence_counts

def consolidate_to_skill_nodes(
    sequence_counts: Dict[Tuple[str, ...], int],
    frequency_threshold: int,
    original_event_count: int
) -> List[CognitiveSkillNode]:
    """
    Compresses identified frequent sequences into 'Cognitive Skill Nodes'.
    It filters out noise and calculates compression metrics.
    
    Args:
        sequence_counts (Dict[Tuple, int]): Patterns found in logs.
        frequency_threshold (int): Minimum occurrences to be considered a skill.
        original_event_count (int): Total original events for ratio calculation.
        
    Returns:
        List[CognitiveSkillNode]: List of consolidated,固化.
    """
    skill_nodes: List[CognitiveSkillNode] = []
    
    for seq, count in sequence_counts.items():
        if count >= frequency_threshold:
            # Generate a representative ID for the node
            node_id = f"skill_{'_'.join(seq)}"
            
            # Calculate compression: (Original Steps * Frequency) vs (1 Skill Node * Frequency)
            # Simplified metric: How much space we save by replacing the sequence with one pointer
            steps_saved = (len(seq) - 1) * count
            compression_ratio = steps_saved / original_event_count if original_event_count > 0 else 0.0
            
            node = CognitiveSkillNode(
                node_id=node_id,
                pattern_sequence=list(seq),
                frequency=count,
                compression_ratio=compression_ratio,
                last_updated=datetime.datetime.now()
            )
            skill_nodes.append(node)
            
    # Sort by impact (frequency * compression)
    skill_nodes.sort(key=lambda x: x.frequency * x.compression_ratio, reverse=True)
    
    logger.info(f"Consolidated {len(skill_nodes)} nodes from overlapping sequences.")
    return skill_nodes

# --- Main Execution ---

def run_skill_consolidation_pipeline(log_data: List[InteractionEvent]) -> Optional[List[CognitiveSkillNode]]:
    """
    Orchestrator function to process logs into skill nodes.
    
    Example Input:
        [
            InteractionEvent(t1, 'copy', 'text_A'),
            InteractionEvent(t2, 'paste', 'doc_B'),
            InteractionEvent(t3, 'edit', 'doc_B'),
            InteractionEvent(t4, 'copy', 'text_C'),
            InteractionEvent(t5, 'paste', 'doc_D'),
            InteractionEvent(t6, 'edit', 'doc_D'),
        ]
    
    Expected Result:
        A CognitiveSkillNode representing ('copy', 'paste', 'edit') pattern.
    """
    try:
        logger.info("Starting Skill Consolidation Pipeline...")
        
        # 1. Validation
        if not validate_interaction_stream(log_data):
            return None
            
        # 2. Determine Thresholds
        threshold = calculate_frequency_threshold(len(log_data))
        
        # 3. Causal Extraction (Pattern Mining)
        # Looking for sequences of length 3 (e.g., Copy -> Paste -> Edit)
        patterns = extract_causal_sequences(log_data, window_size=3)
        
        # 4. Consolidation
        nodes = consolidate_to_skill_nodes(patterns, threshold, len(log_data))
        
        return nodes

    except Exception as e:
        logger.error(f"Critical failure in consolidation pipeline: {e}")
        return None

# --- Usage Example ---
if __name__ == "__main__":
    # Generate dummy data representing 'Copy-Paste-Edit' repetitions
    base_time = datetime.datetime.now()
    dummy_logs = []
    
    # Creating a repetitive pattern to ensure it's detected
    for i in range(5):
        dummy_logs.append(InteractionEvent(base_time + datetime.timedelta(seconds=i*3), "copy", f"src_{i}"))
        dummy_logs.append(InteractionEvent(base_time + datetime.timedelta(seconds=i*3+1), "paste", f"dest_{i}"))
        dummy_logs.append(InteractionEvent(base_time + datetime.timedelta(seconds=i*3+2), "edit", f"dest_{i}"))
        
    # Add some noise
    dummy_logs.append(InteractionEvent(base_time + datetime.timedelta(seconds=20), "save", "final_doc"))
    dummy_logs.append(InteractionEvent(base_time + datetime.timedelta(seconds=21), "exit", "system"))

    # Run pipeline
    skills = run_skill_consolidation_pipeline(dummy_logs)
    
    if skills:
        print("\n--- Discovered Cognitive Skills ---")
        for skill in skills:
            print(f"ID: {skill.node_id}")
            print(f"Pattern: {skill.pattern_sequence}")
            print(f"Frequency: {skill.frequency}")
            print(f"Compression Ratio: {skill.compression_ratio:.4f}")
            print("-" * 30)