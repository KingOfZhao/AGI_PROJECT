"""
Module: auto_sequential_skill_miner
Description: A high-level module for mining sequential patterns from human activity logs
             to automatically generate executable Skill Nodes for AGI systems.

Author: Senior Python Engineer (AGI Division)
Version: 1.0.0
License: MIT
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class ActionLog:
    """Represents a single atomic action performed by a human operator."""
    timestamp: datetime.datetime
    action_type: str  # e.g., 'IDE_INSERT', 'MENU_CLICK', 'SHORTCUT'
    tool_name: str    # e.g., 'VSCode', 'Chrome', 'Terminal'
    details: Dict[str, Any]  # Context-specific data (e.g., key pressed, file path)
    session_id: str

    def __post_init__(self):
        if not isinstance(self.timestamp, datetime.datetime):
            raise ValueError("Invalid timestamp format")
        if not self.action_type or not self.tool_name:
            raise ValueError("Action type and tool name cannot be empty")

@dataclass
class SkillNode:
    """Represents a discovered executable skill/workflow node."""
    skill_id: str
    pattern_sequence: List[str]  # Sequence of action signatures
    description: str
    frequency: int
    source_logs: List[ActionLog] = field(repr=False)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_code_stub(self) -> str:
        """Generates a Python code skeleton for this skill."""
        args = ["context: Dict"]
        func_name = self.skill_id.lower().replace(" ", "_")
        body = "\n".join([f"    # TODO: Implement logic for step: {step}" for step in self.pattern_sequence])
        return f"def {func_name}({', '.join(args)}):\n{body}\n    pass"

# --- Core Functions ---

def preprocess_logs(raw_logs: List[Dict[str, Any]]) -> List[ActionLog]:
    """
    Validates and converts raw dictionary logs into structured ActionLog objects.
    
    Args:
        raw_logs: List of dictionaries containing log data.
        
    Returns:
        List of validated ActionLog objects.
        
    Raises:
        ValueError: If data validation fails.
    """
    if not raw_logs:
        logger.warning("Empty log list provided for preprocessing.")
        return []

    processed_logs = []
    for i, entry in enumerate(raw_logs):
        try:
            # Data validation logic
            if 'timestamp' not in entry:
                raise ValueError(f"Missing timestamp in entry {i}")
            
            # Handle string timestamps
            ts = entry['timestamp']
            if isinstance(ts, str):
                ts = datetime.datetime.fromisoformat(ts)
            
            log = ActionLog(
                timestamp=ts,
                action_type=entry.get('action_type', 'UNKNOWN'),
                tool_name=entry.get('tool_name', 'UNKNOWN'),
                details=entry.get('details', {}),
                session_id=entry.get('session_id', 'default')
            )
            processed_logs.append(log)
        except Exception as e:
            logger.error(f"Failed to process log entry {i}: {e}")
            continue
            
    logger.info(f"Successfully preprocessed {len(processed_logs)} logs.")
    return processed_logs

def mine_sequential_patterns(
    logs: List[ActionLog],
    min_support: int = 3,
    window_size_seconds: int = 300
) -> List[SkillNode]:
    """
    Mines frequent sequences of actions to identify potential skills.
    
    This implementation uses a simplified sliding window approach to find
    contiguous sequences of actions that occur frequently.
    
    Args:
        logs: List of preprocessed ActionLog objects.
        min_support: Minimum frequency for a pattern to be considered a skill.
        window_size_seconds: Time window to group actions into a session sequence.
        
    Returns:
        A list of SkillNode objects representing discovered patterns.
    """
    if min_support < 2:
        raise ValueError("min_support must be at least 2")
    
    logger.info(f"Starting pattern mining with support={min_support}")
    
    # 1. Convert logs to sequences of action signatures
    # Group by session
    sessions: Dict[str, List[ActionLog]] = {}
    for log in logs:
        sessions.setdefault(log.session_id, []).append(log)
    
    # Sort sessions by time and create sequences
    # Signature: "TOOL_NAME:ACTION_TYPE" (simplified for mining)
    sequences: List[List[Tuple[str, ActionLog]]] = []
    
    for session_id, session_logs in sessions.items():
        session_logs.sort(key=lambda x: x.timestamp)
        sequences.append([(f"{l.tool_name}:{l.action_type}", l) for l in session_logs])
    
    # 2. Frequent Pattern Mining (Simplified PrefixSpan approach approximation)
    # Here we look for frequent pairs and triplets for demonstration
    # In production, use a library like 'prefixspan' or 'pymining'
    
    pattern_registry: Dict[str, List[ActionLog]] = Counter()
    pattern_sources: Dict[str, List[ActionLog]] = {} # Store representative logs
    
    # Extract subsequences
    # Note: This is a naive implementation focusing on contiguous sequences
    # A real AGI system would use a specialized library for gap-tolerant mining
    
    for seq in sequences:
        sigs = [x[0] for x in seq]
        logs_in_seq = [x[1] for x in seq]
        
        # Generate n-grams (size 2 to 4)
        for n in range(2, 5):
            for i in range(len(sigs) - n + 1):
                # Create a tuple signature for the pattern
                sub_pattern = tuple(sigs[i:i+n])
                pattern_registry[sub_pattern] += 1
                
                # Store the first occurrence as the representative source
                if sub_pattern not in pattern_sources:
                    pattern_sources[sub_pattern] = logs_in_seq[i:i+n]

    # 3. Filter by support and create SkillNodes
    discovered_skills = []
    skill_counter = 1
    
    for pattern, count in pattern_registry.items():
        if count >= min_support:
            skill_id = f"AUTO_SKILL_{skill_counter:04d}"
            skill_counter += 1
            
            description = f"Detected workflow: {' -> '.join(pattern)}"
            
            node = SkillNode(
                skill_id=skill_id,
                pattern_sequence=list(pattern),
                description=description,
                frequency=count,
                source_logs=pattern_sources[pattern]
            )
            discovered_skills.append(node)
            logger.info(f"Discovered Skill: {skill_id} (Freq: {count}) Pattern: {pattern}")

    return discovered_skills

# --- Helper Functions ---

def export_skills_to_registry(skills: List[SkillNode], output_format: str = "dict") -> Any:
    """
    Exports discovered skills to a specific format for the AGI system.
    
    Args:
        skills: List of SkillNodes to export.
        output_format: 'dict' for JSON-compatible dict, 'code' for python stubs.
        
    Returns:
        Serialized data or code string.
    """
    if not skills:
        return {} if output_format == 'dict' else ""

    if output_format == 'code':
        return "\n\n".join([s.to_code_stub() for s in skills])
    
    # Default to dict
    return [
        {
            "id": s.skill_id,
            "pattern": s.pattern_sequence,
            "description": s.description,
            "frequency": s.frequency,
            "generated_code_stub": s.to_code_stub()
        }
        for s in skills
    ]

# --- Usage Example ---

if __name__ == "__main__":
    # Mock Data (Simulating IDE logs)
    mock_raw_logs = [
        {"timestamp": "2023-10-27T10:00:00", "action_type": "OPEN_FILE", "tool_name": "IDE", "details": {"file": "main.py"}, "session_id": "s1"},
        {"timestamp": "2023-10-27T10:00:05", "action_type": "INSERT_TEXT", "tool_name": "IDE", "details": {"text": "def hello():"}, "session_id": "s1"},
        {"timestamp": "2023-10-27T10:00:10", "action_type": "RUN_COMMAND", "tool_name": "Terminal", "details": {"cmd": "python main.py"}, "session_id": "s1"},
        
        # Similar pattern in a different session
        {"timestamp": "2023-10-27T11:00:00", "action_type": "OPEN_FILE", "tool_name": "IDE", "details": {"file": "utils.py"}, "session_id": "s2"},
        {"timestamp": "2023-10-27T11:00:05", "action_type": "INSERT_TEXT", "tool_name": "IDE", "details": {"text": "import os"}, "session_id": "s2"},
        {"timestamp": "2023-10-27T11:00:10", "action_type": "RUN_COMMAND", "tool_name": "Terminal", "details": {"cmd": "python utils.py"}, "session_id": "s2"},
        
        # Noise
        {"timestamp": "2023-10-27T12:00:00", "action_type": "CLICK", "tool_name": "Browser", "details": {}, "session_id": "s3"},
    ]

    print("--- Starting Auto Skill Mining Process ---")
    
    # 1. Preprocess
    clean_logs = preprocess_logs(mock_raw_logs)
    
    # 2. Mine Patterns
    # Looking for patterns that appear at least 2 times
    discovered_skills = mine_sequential_patterns(clean_logs, min_support=2)
    
    # 3. Export
    skill_registry = export_skills_to_registry(discovered_skills)
    
    print("\n--- Generated Skill Nodes ---")
    for skill in skill_registry:
        print(f"ID: {skill['id']}")
        print(f"Pattern: {skill['pattern']}")
        print(f"Description: {skill['description']}")
        print(f"Generated Code:\n{skill['generated_code_stub']}")
        print("-" * 30)