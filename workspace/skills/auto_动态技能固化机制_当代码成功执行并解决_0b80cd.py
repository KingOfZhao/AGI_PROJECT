"""
Module: auto_dynamic_skill_consolidation.py
Description: Implements a dynamic skill consolidation mechanism for AGI systems.
             It extracts successfully executed code/intents into reusable 'Skill Nodes'
             and updates the skill library to prevent redundant problem-solving.
Author: Senior Python Engineer (AGI Agent)
Version: 1.0.0
"""

import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DynamicSkillConsolidation")


# --- Data Structures ---

@dataclass
class SkillNode:
    """
    Represents a reusable skill node in the AGI skill library.
    
    Attributes:
        id (str): Unique identifier (hash of core logic).
        name (str): Human-readable name of the skill.
        description (str): What problem this skill solves.
        source_intent (str): The original user intent or code trigger.
        code_snippet (str): The validated, executable Python code string.
        created_at (str): ISO format timestamp of creation.
        success_count (int): Number of times successfully reused.
        dependencies (List[str]): Required libraries or other skill IDs.
    """
    id: str
    name: str
    description: str
    source_intent: str
    code_snippet: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    success_count: int = 0
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTrace:
    """
    Tracks the context of a successful execution to be consolidated.
    
    Attributes:
        intent (str): The user input or system trigger.
        code_executed (str): The python code that ran successfully.
        inputs (Dict): The parameters passed to the code.
        outputs (Any): The result returned by the code.
        metadata (Dict): Additional context (environment, latency, etc.).
    """
    intent: str
    code_executed: str
    inputs: Dict[str, Any]
    outputs: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


# --- Core Class ---

class SkillConsolidator:
    """
    Manages the lifecycle of dynamic skills: extraction, validation, 
    deduplication, and storage.
    """

    def __init__(self, skill_library_path: str = "skill_library.json"):
        """
        Initialize the consolidator with a reference to the storage.
        
        Args:
            skill_library_path (str): Path to the persistent storage file.
        """
        self.skill_library_path = skill_library_path
        self._skill_cache: Dict[str, SkillNode] = {}
        self._load_library()
        logger.info(f"SkillConsolidator initialized with {len(self._skill_cache)} existing skills.")

    def _load_library(self) -> None:
        """Loads existing skills from storage into memory."""
        try:
            # In a real AGI system, this might be a database connection
            with open(self.skill_library_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get("skills", []):
                    node = SkillNode(**item)
                    self._skill_cache[node.id] = node
        except FileNotFoundError:
            logger.warning("Skill library file not found. Creating a new one.")
            self._save_library()
        except json.JSONDecodeError:
            logger.error("Skill library corruption detected. Starting fresh.")
            # Backup corrupted file logic would go here

    def _save_library(self) -> None:
        """Persists the current skill cache to storage."""
        try:
            data = {
                "meta": {"last_updated": datetime.now().isoformat(), "count": len(self._skill_cache)},
                "skills": [node.to_dict() for node in self._skill_cache.values()]
            }
            with open(self.skill_library_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("Skill library saved successfully.")
        except IOError as e:
            logger.critical(f"Failed to save skill library: {e}")

    def _generate_skill_id(self, code: str, intent: str) -> str:
        """
        Generates a unique ID based on code structure and intent semantics
        to identify duplicate functionality.
        """
        # Normalize code: remove extra whitespace and comments
        normalized_code = re.sub(r'\s+', '', code)
        raw_string = f"{normalized_code}::{intent}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16]

    def analyze_and_consolidate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        """
        Main entry point. Analyzes a successful execution trace to determine
        if it should be固化 (consolidated) into a new SkillNode.

        Args:
            trace (ExecutionTrace): The context of the successful run.

        Returns:
            Tuple[bool, str]: (Success status, Message/Skill ID).
        """
        logger.info(f"Analyzing trace for intent: {trace.intent[:50]}...")

        # 1. Validation: Check if code is substantial enough to be a skill
        if not self._validate_code_quality(trace.code_executed):
            return False, "Code complexity too low to be a skill."

        # 2. Deduplication: Check if skill already exists
        skill_id = self._generate_skill_id(trace.code_executed, trace.intent)
        if skill_id in self._skill_cache:
            # Update usage stats for existing skill
            self._skill_cache[skill_id].success_count += 1
            self._save_library()
            return True, f"Skill already exists. Updated stats: {skill_id}"

        # 3. Extraction: Create the new node
        new_skill = self._extract_skill(skill_id, trace)
        
        # 4. Verification: Final sanity check
        if not self._verify_skill_safety(new_skill):
            return False, "Safety check failed. Skill rejected."

        # 5. Storage
        self._skill_cache[new_skill.id] = new_skill
        self._save_library()
        
        logger.info(f"New skill consolidated: {new_skill.name} (ID: {new_skill.id})")
        return True, new_skill.id

    def _validate_code_quality(self, code: str) -> bool:
        """
        Checks if the code meets minimum complexity requirements.
        Avoids saving trivial one-liners like 'print(x)'.
        """
        # Remove comments and docstrings (simplified)
        clean_code = re.sub(r'#.*', '', code)
        clean_code = re.sub(r'""".*?"""', '', clean_code, flags=re.DOTALL)
        
        # Heuristic: Must have at least 3 lines or define a function/class
        lines = [line.strip() for line in clean_code.split('\n') if line.strip()]
        has_structure = 'def ' in clean_code or 'class ' in clean_code
        
        if len(lines) >= 3 or has_structure:
            return True
        return False

    def _extract_skill(self, skill_id: str, trace: ExecutionTrace) -> SkillNode:
        """
        Transforms an execution trace into a formal SkillNode.
        Includes logic to auto-generate descriptions and names.
        """
        # Auto-generate a generic name based on intent
        # e.g., "calculate bmi" -> "Auto_Skill_Calculate_Bmi"
        name_parts = trace.intent.split()[:3]
        skill_name = "Auto_" + "_".join([p.capitalize() for p in name_parts])
        
        # Extract potential dependencies (simple import scan)
        dependencies = []
        import_lines = re.findall(r'^(?:import|from)\s+([a-zA-Z0-9_]+)', trace.code_executed, re.MULTILINE)
        dependencies = list(set(import_lines))

        return SkillNode(
            id=skill_id,
            name=skill_name,
            description=f"Automatically generated skill for intent: '{trace.intent}'",
            source_intent=trace.intent,
            code_snippet=trace.code_executed,
            dependencies=dependencies
        )

    def _verify_skill_safety(self, skill: SkillNode) -> bool:
        """
        Basic safety boundary check. Ensures no forbidden operations.
        """
        forbidden_patterns = [
            r'os\.system',
            r'subprocess\.call',
            r'eval\(',
            r'exec\(',
            r'shutil\.rmtree',
            r'__import__'
        ]
        
        code = skill.code_snippet
        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                logger.warning(f"Safety violation: Pattern '{pattern}' found in skill {skill.id}")
                return False
        return True

    def get_reusable_skill(self, intent: str) -> Optional[SkillNode]:
        """
        Helper to retrieve a skill matching an intent.
        (Simulated semantic search via substring match for demo purposes).
        """
        for skill in self._skill_cache.values():
            # In a real system, use vector embedding similarity here
            if intent.lower() in skill.source_intent.lower() or skill.source_intent.lower() in intent.lower():
                return skill
        return None


# --- Usage Example ---

def example_usage():
    """
    Demonstrates the workflow of the Dynamic Skill Consolidation mechanism.
    """
    print("\n" + "="*50)
    print("Starting Dynamic Skill Consolidation Demo")
    print("="*50 + "\n")

    # 1. Initialize the system
    consolidator = SkillConsolidator(skill_library_path="demo_skill_lib.json")

    # 2. Simulate a successful execution of a new complex task (e.g., a specific data transform)
    code_that_worked = """
def calculate_bmi(weight_kg, height_m):
    '''Calculates Body Mass Index'''
    if height_m <= 0:
        raise ValueError("Height must be positive")
    return weight_kg / (height_m ** 2)

result = calculate_bmi(70, 1.75)
"""

    # 3. Create the trace object
    trace = ExecutionTrace(
        intent="calculate bmi metric",
        code_executed=code_that_worked,
        inputs={"weight": 70, "height": 1.75},
        outputs=22.857,
        metadata={"runtime_ms": 5}
    )

    # 4. Try to consolidate
    success, message = consolidator.analyze_and_consolidate(trace)
    print(f"Attempt 1 Result: Success={success}, Message={message}")

    # 5. Simulate trying to add the exact same skill again (Deduplication test)
    success_dup, message_dup = consolidator.analyze_and_consolidate(trace)
    print(f"Attempt 2 (Duplicate) Result: Success={success_dup}, Message={message_dup}")

    # 6. Test retrieval
    retrieved_skill = consolidator.get_reusable_skill("calculate bmi")
    if retrieved_skill:
        print(f"\nRetrieved Skill:\n  Name: {retrieved_skill.name}\n  Code Preview: {retrieved_skill.code_snippet[:50]}...")

if __name__ == "__main__":
    example_usage()