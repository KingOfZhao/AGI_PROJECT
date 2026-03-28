"""
Module: auto_利用_认知固化的代码结晶_与_指令歧义性_3831e6
Description: AGI Skill for Code Crystallization and Ambiguity Detection.
             This module monitors code execution patterns, identifies high-frequency,
             unambiguous logic blocks, and refactors them into standardized skill functions.
Author: Senior Python Engineer (AGI System Core)
Version: 1.0.0
"""

import logging
import hashlib
import ast
import inspect
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class CodeFragment:
    """Represents a snippet of code identified for potential crystallization."""
    code_hash: str
    source_code: str
    frequency: int = 0
    ambiguity_score: float = 1.0  # Lower is better (0.0 = no ambiguity)
    last_invoked: datetime = field(default_factory=datetime.now)
    input_types: Optional[Tuple[type, ...]] = None
    output_type: Optional[type] = None

@dataclass
class CrystallizedSkill:
    """Represents a refined, reusable function stored in the Skill Library."""
    skill_id: str
    func: Callable
    description: str
    original_hashes: Set[str] = field(default_factory=set)

class AmbiguityDetectionError(Exception):
    """Custom exception for errors during ambiguity analysis."""
    pass

class SkillCrystallizationError(Exception):
    """Custom exception for errors during the refactoring process."""
    pass

# --- Core Components ---

class AmbiguityDetector:
    """
    Analyzes code snippets and execution contexts to determine semantic ambiguity.
    It ensures that only code with a single, clear interpretation is crystallized.
    """

    def analyze_structure(self, code_str: str) -> float:
        """
        Analyzes the AST structure for complexity and ambiguity.
        Returns a score between 0.0 (clear) and 1.0 (highly ambiguous/complex).
        """
        try:
            tree = ast.parse(code_str)
            
            # Heuristic: High cyclomatic complexity or dynamic attributes increase ambiguity
            # For this skill, we simulate ambiguity detection based on structural consistency
            
            # Check for dynamic lookups (getattr, setattr) which increase ambiguity
            dynamic_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
            
            # Check for 'eval' or 'exec' usage - strictly ambiguous
            calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
            for call in calls:
                if isinstance(call.func, ast.Name) and call.func.id in ('eval', 'exec', 'compile'):
                    logger.warning(f"High ambiguity detected: usage of {call.func.id}")
                    return 1.0

            # Calculate base ambiguity
            # Lower score if the code is purely functional (no side effects assumed here)
            score = 0.1 # Base low ambiguity
            if len(dynamic_nodes) > 2:
                score += 0.3 * len(dynamic_nodes) # Penalize heavy dynamism
            
            return min(score, 1.0)

        except SyntaxError as e:
            logger.error(f"Syntax error during ambiguity analysis: {e}")
            raise AmbiguityDetectionError("Invalid code syntax") from e

    def check_input_output_consistency(self, inputs: Tuple[Any, ...], output: Any) -> bool:
        """
        Validates if the input/output types are consistent with previous runs.
        In a real AGI system, this would check against a historical database.
        """
        if not inputs or output is None:
            return False
        
        # Basic validation: Ensure inputs are hashable or serializable for consistency checks
        try:
            hash(str(inputs))
            hash(str(output))
            return True
        except TypeError:
            return False


class CodeCrystallizer:
    """
    Monitors code usage, detects solidification patterns, and refactors
    high-frequency/low-ambiguity code into standard library functions.
    """

    def __init__(self, ambiguity_detector: AmbiguityDetector):
        self.detector = ambiguity_detector
        self.fragment_cache: Dict[str, CodeFragment] = {}
        self.skill_library: Dict[str, CrystallizedSkill] = {}
        self._crystallization_threshold = 5  # Frequency required
        self._ambiguity_tolerance = 0.3      # Max ambiguity score allowed

    def _hash_code(self, code_str: str) -> str:
        """Generates a SHA-256 hash for a code string."""
        return hashlib.sha256(code_str.encode('utf-8')).hexdigest()

    def monitor_execution(self, code_str: str, inputs: Tuple[Any, ...], output: Any):
        """
        Core entry point for monitoring. Records execution metadata and updates frequency.
        
        Args:
            code_str (str): The source code of the logic being executed.
            inputs (Tuple): The arguments passed to the logic.
            output (Any): The result of the logic.
        """
        if not isinstance(code_str, str) or not code_str.strip():
            return

        code_hash = self._hash_code(code_str)
        
        # Calculate Ambiguity
        try:
            current_ambiguity = self.detector.analyze_structure(code_str)
        except AmbiguityDetectionError:
            logger.info(f"Skipping monitoring for malformed code block.")
            return

        if code_hash in self.fragment_cache:
            fragment = self.fragment_cache[code_hash]
            fragment.frequency += 1
            fragment.last_invoked = datetime.now()
            
            # Update rolling average of ambiguity
            fragment.ambiguity_score = (fragment.ambiguity_score + current_ambiguity) / 2
        else:
            # Create new fragment record
            self.fragment_cache[code_hash] = CodeFragment(
                code_hash=code_hash,
                source_code=code_str,
                frequency=1,
                ambiguity_score=current_ambiguity,
                input_types=tuple(type(i) for i in inputs),
                output_type=type(output)
            )

        # Attempt crystallization
        self._try_crystallize(code_hash)

    def _try_crystallize(self, code_hash: str):
        """
        Checks if a fragment meets the criteria for crystallization.
        If successful, compiles it into a function and adds to library.
        """
        fragment = self.fragment_cache.get(code_hash)
        if not fragment:
            return

        # Validation Logic
        if (fragment.frequency >= self._crystallization_threshold and 
            fragment.ambiguity_score <= self._ambiguity_tolerance):
            
            logger.info(f"Crystallization threshold met for hash {code_hash[:8]}...")
            
            try:
                # Compile code into a reusable function object
                skill_func = self._refactor_to_skill(fragment)
                
                # Generate Skill ID
                skill_id = f"skill_{code_hash[:12]}"
                
                # Add to Library
                self.skill_library[skill_id] = CrystallizedSkill(
                    skill_id=skill_id,
                    func=skill_func,
                    description=f"Auto-crystallized skill from pattern {code_hash[:8]}",
                    original_hashes={code_hash}
                )
                
                logger.info(f"SUCCESS: New Skill added to Library: {skill_id}")
                
                # Optimization: Remove from cache to free memory
                del self.fragment_cache[code_hash]

            except Exception as e:
                logger.error(f"Failed to crystallize code {code_hash}: {e}")
                raise SkillCrystallizationError("Refactoring failed") from e

    def _refactor_to_skill(self, fragment: CodeFragment) -> Callable:
        """
        Internal helper to safely compile source code into a callable function.
        """
        # Sanitize and wrap code
        # In a real AGI, this involves sophisticated AST rewriting to handle arguments
        # Here we wrap it in a lambda or exec scope for demonstration
        
        sandbox = {}
        func_name = "crystallized_logic"
        
        # Basic boundary check: Ensure no forbidden keywords (Security)
        forbidden = ["import", "open", "os.", "sys."]
        if any(fw in fragment.source_code for fw in forbidden):
            raise SkillCrystallizationError("Security violation: Forbidden operations detected.")

        wrapped_code = f"def {func_name}(*args, **kwargs):\n    return {fragment.source_code}"
        
        try:
            exec(wrapped_code, sandbox)
            return sandbox[func_name]
        except Exception as e:
            logger.error(f"Compilation error: {e}\nCode:\n{wrapped_code}")
            raise

    def get_skill(self, skill_id: str) -> Optional[Callable]:
        """Retrieves a crystallized skill from the library."""
        if skill_id in self.skill_library:
            return self.skill_library[skill_id].func
        return None

# --- Usage Example ---

if __name__ == "__main__":
    # Initialize System
    detector = AmbiguityDetector()
    crystallizer = CodeCrystallizer(detector)

    # Simulation: Repeated execution of a simple, non-ambiguous logic
    # Logic: Calculate the square of a number plus a constant
    raw_logic = " (x * x) + 10 "
    
    print("--- Starting AGI Skill Evolution Simulation ---")
    
    # Feed the system multiple times
    for i in range(6):
        x_val = i + 1
        
        # Simulate monitoring
        # Note: In a real scenario, the system intercepts the execution flow
        print(f"Run {i+1}: Executing logic with input {x_val}")
        
        # The system monitors the raw string logic
        crystallizer.monitor_execution(
            code_str=raw_logic, 
            inputs=(x_val,), 
            output=(x_val * x_val) + 10
        )

    # Check if the skill was created
    print("\n--- Checking Skill Library ---")
    for skill_id, skill in crystallizer.skill_library.items():
        print(f"Skill Found: {skill_id}")
        print(f"Description: {skill.description}")
        
        # Test the new skill
        test_func = skill.func
        result = test_func(5) # Should return 5*5 + 10 = 35
        print(f"Testing Skill with input 5: Result = {result}")
        
        assert result == 35, "Skill execution failed validation"
        print("Validation Passed.")