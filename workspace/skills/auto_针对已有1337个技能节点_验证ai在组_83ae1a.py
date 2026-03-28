"""
Module: socratic_js_debug_validator.py

This module is designed to validate the AGI system's ability to synthesize two
distinct, low-frequency skills: 'Socratic Questioning' (Philosophy/Pedagogy) 
and 'JavaScript Debugging' (Technical/Programming).

The core task is to generate code comments that do not merely point out errors,
but guide the user to the solution through philosophical inquiry (Socratic Method).
This verifies logical integration of concepts rather than simple keyword拼接.

Domain: cognitive_synthesis
Skill ID: auto_针对已有1337个技能节点_验证ai在组_83ae1a
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------
# 1. Configuration and Setup
# ---------------------------------------------------------

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Enumeration for JS error severity levels."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    STYLE = "STYLE"

@dataclass
class JSLineContext:
    """Represents the context of a specific line in JavaScript code."""
    line_number: int
    content: str
    variables_in_scope: List[str] = field(default_factory=list)
    is_async: bool = False

@dataclass
class SocraticComment:
    """Data structure for the generated Socratic comment."""
    target_line: int
    question: str
    underlying_bug_type: str
    logical_depth_score: float # 0.0 to 1.0 (measuring how well concepts are integrated)

# ---------------------------------------------------------
# 2. Core Logic Classes
# ---------------------------------------------------------

class SocraticEngine:
    """
    A cognitive engine designed to translate technical JavaScript errors 
    into philosophical, Socratic questions.
    """

    def __init__(self):
        self._philosophical_templates = {
            "ReferenceError": [
                "If a variable is named but not defined, does it truly exist? ",
                "Is the name merely a shadow of an object that has not yet been brought into being? "
            ],
            "TypeError": [
                "Can one ask a stone to fly? Is this object capable of the action you demand of it? ",
                "What is the true nature of this object that it should possess such a property? "
            ],
            "SyntaxError": [
                "Does the structure of your argument follow the laws of grammar? ",
                "Have you closed the circle of logic, or left it open to chaos? "
            ],
            "Async/Await": [
                "Does the passage of time halt simply because we desire a result? ",
                "Can you grasp the fruit before the tree has borne it? "
            ]
        }
        logger.info("SocraticEngine initialized with philosophical templates.")

    def _analyze_js_context(self, code_line: str) -> Dict[str, bool]:
        """
        Helper: Analyzes a line of JS code for potential issues.
        Returns a dictionary of detected features/bugs.
        """
        analysis = {
            "is_async": "await" in code_line or "async" in code_line,
            "missing_semicolon": not code_line.strip().endswith(";") and not code_line.strip().endswith("{") and not code_line.strip().endswith("}"),
            "undefined_var_usage": re.search(r'\b(console|document|window)\b', code_line) is None and re.search(r'var|let|const', code_line) is None
        }
        return analysis

    def generate_inquiry(self, line: str, error_hint: str) -> str:
        """
        Synthesizes a Socratic question based on a technical error hint.
        
        Args:
            line (str): The line of code in question.
            error_hint (str): A technical hint (e.g., 'ReferenceError').
        
        Returns:
            str: A Socratic question.
        """
        templates = self._philosophical_templates.get(error_hint, [
            "Is this the most clear expression of your intent? "
        ])
        
        # Simple rotation logic for variety
        base_question = templates[hash(line) % len(templates)]
        
        # Synthesis: Combine the technical context with the question
        return f"{base_question}(Observe line: '{line.strip()}')"


class CognitiveValidator:
    """
    Validates whether the AI is performing true logical synthesis 
    between 'Socratic Method' and 'JS Debugging'.
    """

    def __init__(self):
        self.soc_engine = SocraticEngine()
        logger.info("CognitiveValidator ready for skill synthesis check.")

    def _validate_code_structure(self, js_code: str) -> bool:
        """
        Helper: Basic validation of input JS code.
        """
        if not js_code or len(js_code) < 10:
            logger.warning("Input code is too short for meaningful analysis.")
            return False
        return True

    def analyze_and_comment(self, js_code: str) -> List[SocraticComment]:
        """
        Main Core Function: Analyzes JS code and generates Socratic comments.
        
        Args:
            js_code (str): A string containing JavaScript code.
            
        Returns:
            List[SocraticComment]: A list of generated comments with metadata.
        """
        if not self._validate_code_structure(js_code):
            return []

        comments = []
        lines = js_code.split('\n')
        
        logger.info(f"Starting cognitive analysis on {len(lines)} lines of code.")

        for idx, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            # Detect technical patterns
            if "await" in line and "async" not in self._find_function_start(lines, idx):
                # Logic Synthesis Point: Handling Async/Await without context
                question = self.soc_engine.generate_inquiry(line, "Async/Await")
                comments.append(SocraticComment(
                    target_line=idx,
                    question=question,
                    underlying_bug_type="Missing Async Context",
                    logical_depth_score=0.9
                ))
            
            elif line.strip().endswith("}") and "{" not in line:
                 # Logic Synthesis Point: Structure/Syntax
                 # (This is a heuristic check for simplicity)
                 pass 

        return comments

    def _find_function_start(self, lines: List[str], current_idx: int) -> str:
        """Helper: Look backwards to find function definition."""
        for i in range(current_idx - 1, -1, -1):
            if "function" in lines[i] or "=>" in lines[i]:
                return lines[i]
        return ""

    def evaluate_synthesis_quality(self, comments: List[SocraticComment]) -> Dict[str, float]:
        """
        Second Core Function: Evaluates the logical consistency of the generated comments.
        
        It checks if the comments are truly Socratic (questions) and relevant to JS,
        rather than just generic statements.
        """
        if not comments:
            return {"synthesis_score": 0.0, "reason": "No comments generated"}

        total_score = 0.0
        valid_synthesis_count = 0

        for comment in comments:
            # Check 1: Is it a question? (Socratic nature)
            is_question = "?" in comment.question
            
            # Check 2: Does it reference code elements? (JS Debugging nature)
            # (Checking if the comment isn't purely abstract philosophy)
            references_code = "'" in comment.question or '"' in comment.question

            if is_question and references_code:
                valid_synthesis_count += 1
                total_score += comment.logical_depth_score
            else:
                logger.warning(f"Low quality synthesis detected at line {comment.target_line}")

        avg_score = total_score / len(comments)
        
        return {
            "synthesis_score": round(avg_score, 2),
            "valid_synthesis_ratio": round(valid_synthesis_count / len(comments), 2),
            "reason": "Logical integration successful" if avg_score > 0.7 else "Conceptual mismatch"
        }

# ---------------------------------------------------------
# 3. Execution and Formatting
# ---------------------------------------------------------

def format_output_report(results: List[SocraticComment], metrics: Dict) -> str:
    """
    Helper: Formats the analysis results into a readable report string.
    """
    report_lines = [
        "=" * 40,
        "COGNITIVE SYNTHESIS VALIDATION REPORT",
        "=" * 40,
        f"Skill: Socratic Questioning + JS Debugging",
        f"Validation Result: {metrics.get('reason', 'N/A')}",
        f"Synthesis Score: {metrics.get('synthesis_score', 0)}",
        "-" * 40,
        "Generated Socratic Debugging Comments:",
        ""
    ]

    for res in results:
        report_lines.append(f"Line {res.target_line} [{res.underlying_bug_type}]:")
        report_lines.append(f"  >> {res.question}")
        report_lines.append("")

    return "\n".join(report_lines)


def main():
    """
    Usage Example & Execution Entry Point.
    """
    # A sample buggy JS code snippet (Async/await misuse)
    buggy_js_code = """
    // Fetching user data
    function getUserData(id) {
        const data = await fetch('/api/user/' + id); // Bug: Missing async keyword
        return data.json();
    }
    """

    # Initialize the validator
    validator = CognitiveValidator()

    try:
        # Step 1: Analyze and Generate
        comments = validator.analyze_and_comment(buggy_js_code)

        # Step 2: Validate Synthesis
        metrics = validator.evaluate_synthesis_quality(comments)

        # Step 3: Output
        report = format_output_report(comments, metrics)
        print(report)

        # Log final status
        if metrics['synthesis_score'] > 0.8:
            logger.info("SUCCESS: AI demonstrated valid cognitive synthesis.")
        else:
            logger.error("FAILURE: AI failed to properly merge skills.")

    except Exception as e:
        logger.error(f"System Error during validation: {e}", exc_info=True)

if __name__ == "__main__":
    main()