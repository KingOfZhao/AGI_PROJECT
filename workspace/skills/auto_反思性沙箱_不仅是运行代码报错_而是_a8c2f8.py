"""
Reflective Sandbox Module for AGI Systems.

This module implements a 'Cognitive-Code Dual Loop' system. It transcends
traditional try-except mechanisms by abstracting runtime errors into
cognitive 'Error Pattern Nodes'. This allows the system to learn from
failures, predicting and avoiding similar errors in future code generation
cycles.

Version: 1.0.0
Author: Senior Python Engineer
License: MIT
"""

import logging
import json
import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import inspect

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ReflectiveSandbox")


class ErrorCategory(Enum):
    """Enumeration of high-level cognitive error categories."""
    SCOPE_AMBIGUITY = "Variable Scope Ambiguity"
    TYPE_CONFLICT = "Type Logic Conflict"
    RESOURCE_CONTENTION = "Resource/Thread Contention"
    API_MISMATCH = "API Signature Mismatch"
    LOGIC_FLOW = "Control Flow Deadlock"
    UNKNOWN = "Unknown Pattern"


@dataclass
class ErrorPatternNode:
    """
    Represents an abstract 'cognitive' node derived from a concrete error.
    
    Attributes:
        id: Unique hash identifying the error pattern.
        category: The high-level cognitive classification of the error.
        abstract_cause: A human-readable abstract description of the failure mode.
        signature: Technical keywords or stack trace fragments used for matching.
        occurrence_count: How many times this pattern has been encountered.
        last_seen: Timestamp of the last occurrence.
        mitigation_strategy: Suggested logic to avoid this error in the future.
    """
    id: str
    category: ErrorCategory
    abstract_cause: str
    signature: List[str]
    occurrence_count: int = 1
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    mitigation_strategy: str = ""


class CognitiveMemory:
    """
    The long-term memory store for the AGI system.
    Persists and retrieves ErrorPatternNodes.
    """
    
    def __init__(self, storage_path: str = "agi_memory_store.json"):
        self.storage_path = storage_path
        self.patterns: Dict[str, ErrorPatternNode] = {}
        self._load_memory()
        logger.info(f"Cognitive Memory initialized with {len(self.patterns)} patterns.")

    def _load_memory(self) -> None:
        """Loads memory from disk if available."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for item in data.get("patterns", []):
                    node = ErrorPatternNode(**item)
                    # Convert string back to Enum
                    node.category = ErrorCategory(node.category)
                    self.patterns[node.id] = node
        except FileNotFoundError:
            logger.info("No existing memory found. Starting fresh.")
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")

    def save_memory(self) -> None:
        """Persists current memory state to disk."""
        try:
            serializable_data = {
                "patterns": [
                    {**asdict(p), "category": p.category.value} 
                    for p in self.patterns.values()
                ]
            }
            with open(self.storage_path, 'w') as f:
                json.dump(serializable_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def recall_similar(self, code_context: str) -> Optional[ErrorPatternNode]:
        """
        Searches memory for error patterns that match the current code context.
        
        Args:
            code_context: The source code or logic summary about to be executed.
            
        Returns:
            A matching ErrorPatternNode if vulnerability is detected, else None.
        """
        for node in self.patterns.values():
            # Simple matching heuristic: check if signature keywords appear in code
            matches = [sig for sig in node.signature if sig in code_context]
            if len(matches) / len(node.signature) > 0.8:  # Threshold for recall
                logger.warning(f"Cognitive Recall: Triggered pattern {node.id} ({node.category.value})")
                return node
        return None


class ReflectiveSandbox:
    """
    The core execution environment. It wraps code execution with a cognitive
    feedback loop.
    """

    def __init__(self):
        self.memory = CognitiveMemory()
        self.execution_history: List[Dict[str, Any]] = []

    def _generate_pattern_id(self, error_type: str, message: str) -> str:
        """Creates a deterministic ID for an error pattern."""
        unique_str = f"{error_type}:{message}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]

    def _abstract_error(self, exc: Exception, code: str) -> ErrorPatternNode:
        """
        Core Cognitive Function: Transforms a raw Exception into an abstract
        ErrorPatternNode.
        """
        error_type = type(exc).__name__
        message = str(exc)
        node_id = self._generate_pattern_id(error_type, message)
        
        # Check if we already know this specific raw error
        if node_id in self.memory.patterns:
            node = self.memory.patterns[node_id]
            node.occurrence_count += 1
            node.last_seen = datetime.now().isoformat()
            return node

        # Logic to categorize and abstract (Simulated AGI inference)
        category = ErrorCategory.UNKNOWN
        abstract_cause = "Generic execution failure."
        mitigation = "Review logs."
        signature = []

        if "UnboundLocalError" in error_type or "local variable" in message:
            category = ErrorCategory.SCOPE_AMBIGUITY
            abstract_cause = "Variable scope ambiguity in multi-threaded or closure contexts."
            mitigation = "Ensure variables are initialized in the local scope before assignment or use 'nonlocal/global' explicitly."
            # Extract variable names as signature
            signature = re.findall(r"local variable '(\w+)'", message)
            
        elif "TypeError" in error_type and "unsupported operand" in message:
            category = ErrorCategory.TYPE_CONFLICT
            abstract_cause = "Mismatched data types in arithmetic or logic operations."
            mitigation = "Implement strict type checking or casting before operations."
            signature = re.findall(r"'(\w+)'", message) # Capture types involved

        elif "Deadlock" in message or "Resource" in message:
            category = ErrorCategory.RESOURCE_CONTENTION
            abstract_cause = "Concurrency conflict over shared resources."
            mitigation = "Implement locking mechanisms or asynchronous queues."

        # Create the new node
        new_node = ErrorPatternNode(
            id=node_id,
            category=category,
            abstract_cause=abstract_cause,
            signature=signature if signature else [error_type],
            mitigation_strategy=mitigation
        )
        
        return new_node

    def pre_check(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Pre-execution cognitive interception.
        Checks if the code resembles a previously failed pattern.
        """
        risk_node = self.memory.recall_similar(code)
        if risk_node:
            return False, f"Pre-emptive Block: Pattern '{risk_node.category.value}' detected. Advice: {risk_node.mitigation_strategy}"
        return True, "Pre-check passed."

    def execute(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Executes the function within the sandbox.
        
        Args:
            func: The callable to execute.
            *args, **kwargs: Arguments for the callable.
            
        Returns:
            Tuple[success: bool, result: Any]
        """
        # 1. Source Inspection (Simplified for runtime callables)
        try:
            source_code = inspect.getsource(func)
        except (TypeError, OSError):
            source_code = "Dynamic code inspection failed"

        # 2. Cognitive Pre-check
        approved, msg = self.pre_check(source_code)
        if not approved:
            logger.warning(f"Execution aborted by cognitive pre-check: {msg}")
            return False, msg

        # 3. Execution
        try:
            logger.info(f"Executing function: {func.__name__}")
            result = func(*args, **kwargs)
            self._log_execution(func.__name__, success=True)
            return True, result
            
        except Exception as e:
            logger.error(f"Sandbox caught exception: {e}")
            
            # 4. Cognitive Abstraction Loop
            # In a real AGI, this would trigger a more complex analysis process
            pattern_node = self._abstract_error(e, source_code)
            
            # Update Memory
            if pattern_node.id not in self.memory.patterns:
                logger.info(f"Learning new error pattern: {pattern_node.category.value}")
                self.memory.patterns[pattern_node.id] = pattern_node
            
            self.memory.save_memory()
            
            self._log_execution(func.__name__, success=False, error=str(e), pattern=pattern_node.id)
            
            # Return structured failure
            return False, {
                "error": str(e),
                "cognitive_pattern": pattern_node.abstract_cause,
                "suggestion": pattern_node.mitigation_strategy
            }

    def _log_execution(self, func_name: str, success: bool, **extra) -> None:
        """Helper to log execution history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "function": func_name,
            "success": success,
            **extra
        }
        self.execution_history.append(entry)


# ==========================================
# Usage Example
# ==========================================

if __name__ == "__main__":
    # Initialize Sandbox
    sandbox = ReflectiveSandbox()

    # Example 1: A function with a subtle scope issue
    def faulty_scope_function():
        count = 10
        if count > 5:
            # This will cause UnboundLocalError because 'count' is referenced 
            # before assignment in the local scope due to the 'count = ' below
            # (Python treats 'count' as local if assigned anywhere in the function)
            print(f"Count is {count}")
            count = 20
        return count

    # First run: The system learns the error
    print("--- First Execution (Learning Phase) ---")
    success, result = sandbox.execute(faulty_scope_function)
    if not success:
        print(f"Result: {result}")

    # Example 2: A similar function that triggers the recall
    def similar_faulty_function():
        val = 5
        if val < 10:
            # Same pattern: print before local reassignment
            print(val)
            val = 15
        return val

    print("\n--- Second Execution (Predictive Phase) ---")
    # The sandbox should ideally warn or block this if the pre-check logic is strict,
    # or simply catch it again. Here we demonstrate the memory persistence.
    success, result = sandbox.execute(similar_faulty_function)
    if not success:
        print(f"Result: {result}")