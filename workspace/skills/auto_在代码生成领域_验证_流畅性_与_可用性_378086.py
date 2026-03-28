"""
Module: auto_code_fluency_usability_verification

This module is designed to demonstrate the separation between 'Fluency' (generating
syntactically correct code) and 'Usability' (generating functionally correct logic)
in code generation contexts.

It introduces the concept of 'Assumption Boundaries' (AssumptionBoundaries),
allowing an AI system to explicitly tag parts of the code that are deterministic
versus parts that are probabilistic or based on heuristics.

Core Concepts:
- Fluent Code: Code that compiles/runs without syntax errors.
- Usable Code: Code that produces the expected logical result.
- Assumption Boundary: A marker distinguishing verified logic from inferred logic.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    """Enumeration for code block confidence levels."""
    DETERMINISTIC = 1.0  # Verified logic, math, or explicit instructions
    HIGH_PROBABILITY = 0.85  # Strong inference based on context
    PROBABILISTIC_GUESS = 0.5  # Fill-in-the-blank or hallucination risk
    PLACEHOLDER = 0.0  # Dummy code for structure

@dataclass
class CodeSegment:
    """Represents a slice of generated code with associated metadata."""
    content: str
    confidence: ConfidenceLevel
    start_line: int
    end_line: int
    description: str = ""
    assumption_note: str = ""

@dataclass
class GeneratedArtifact:
    """A container for a complete generated code artifact."""
    filename: str
    raw_source: str
    segments: List[CodeSegment] = field(default_factory=list)

    def get_overall_usability_score(self) -> float:
        """Calculates a weighted usability score based on segment confidence."""
        if not self.segments:
            return 0.0
        
        total_lines = sum(seg.end_line - seg.start_line + 1 for seg in self.segments)
        if total_lines == 0:
            return 0.0

        weighted_score = 0.0
        for seg in self.segments:
            weight = (seg.end_line - seg.start_line + 1)
            weighted_score += seg.confidence.value * weight
        
        return round(weighted_score / total_lines, 3)

def validate_syntax_safety(source_code: str) -> bool:
    """
    Validates that the code is syntactically correct (Fluency Check).
    This is a heuristic check using compile().
    """
    try:
        compile(source_code, '<string>', 'exec')
        logger.info("Fluency Check: Syntax is valid.")
        return True
    except SyntaxError as e:
        logger.error(f"Fluency Check Failed: Syntax Error at line {e.lineno}")
        return False

def extract_assumption_boundaries(raw_source: str) -> GeneratedArtifact:
    """
    Parses raw source code to identify Assumption Boundaries based on special comments.
    
    Expected Format in code:
        # ASSUMPTION: <description> (Confidence: <LEVEL>)
        <code block>
        # END_ASSUMPTION
    
    Levels: DETERMINISTIC, HIGH_PROBABILITY, PROBABILISTIC_GUESS, PLACEHOLDER
    """
    logger.info("Parsing source code for Assumption Boundaries...")
    artifact = GeneratedArtifact(filename="generated_module.py", raw_source=raw_source)
    
    lines = raw_source.split('\n')
    
    # Regex to capture boundary markers
    start_pattern = re.compile(r'#\s*ASSUMPTION:\s*(.*?)\s*\(Confidence:\s*(\w+)\)')
    
    current_segment_lines = []
    segment_start_idx = 0
    current_meta = None
    
    for i, line in enumerate(lines):
        start_match = start_pattern.match(line.strip())
        
        if start_match:
            # Start of a new explicit boundary
            current_meta = {
                "desc": start_match.group(1),
                "level_str": start_match.group(2)
            }
            segment_start_idx = i + 1 # Code starts next line
            continue

        if "END_ASSUMPTION" in line and current_meta:
            # End of boundary
            try:
                level = ConfidenceLevel[current_meta['level_str'].upper()]
            except KeyError:
                level = ConfidenceLevel.PROBABILISTIC_GUESS
            
            seg = CodeSegment(
                content="\n".join(current_segment_lines),
                confidence=level,
                start_line=segment_start_idx + 1, # 1-based indexing
                end_line=i, # Current line is the end marker, code is before it
                description=current_meta['desc'],
                assumption_note=f"Inferred logic: {current_meta['desc']}"
            )
            artifact.segments.append(seg)
            
            # Reset buffers
            current_segment_lines = []
            current_meta = None
            continue
            
        if current_meta:
            # We are inside an assumption block
            current_segment_lines.append(line)
        else:
            # Code outside markers is treated as Deterministic by default
            # In this parser, we treat unmarked code as implicit deterministic segments
            # For simplicity in this demo, we only explicitly track marked blocks.
            pass
            
    return artifact

def verify_fluency_vs_usability(source_code: str) -> Tuple[bool, float, Dict]:
    """
    Main orchestrator function.
    1. Checks Fluency (Can it run?).
    2. Parses Assumption Boundaries (What is guessed?).
    3. Calculates Usability Score (How much is verified?).
    
    Args:
        source_code (str): The complete Python source code string.
        
    Returns:
        Tuple[bool, float, Dict]: 
            - is_fluent (bool)
            - usability_score (float)
            - report (Dict)
    """
    logger.info("Starting Verification Process...")
    
    # 1. Fluency Validation
    is_fluent = validate_syntax_safety(source_code)
    
    if not is_fluent:
        return False, 0.0, {"error": "Syntax validation failed"}
    
    # 2. Boundary Extraction
    artifact = extract_assumption_boundaries(source_code)
    
    # 3. Logic Analysis (Simulated)
    # In a real AGI system, this would involve running unit tests or formal verification.
    # Here we rely on the metadata extracted.
    
    usability_score = artifact.get_overall_usability_score()
    
    report = {
        "total_segments": len(artifact.segments),
        "segments_detail": [
            {
                "line_range": f"{s.start_line}-{s.end_line}",
                "confidence": s.confidence.name,
                "note": s.assumption_note
            } for s in artifact.segments
        ],
        "summary": "Code is fluent. Usability depends on the validity of probabilistic assumptions."
    }
    
    logger.info(f"Verification Complete. Fluency: {is_fluent}, Usability Score: {usability_score}")
    
    return is_fluent, usability_score, report

# --- Data Processing Helper ---

def format_verification_report(report: Dict) -> str:
    """
    Formats the verification dictionary into a readable string for UI or Logs.
    """
    if "error" in report:
        return f"VERIFICATION FAILED: {report['error']}"
    
    header = "=== CODE VERIFICATION REPORT ===\n"
    body = f"Total Assumption Blocks Detected: {report['total_segments']}\n"
    body += "Details:\n"
    
    for item in report['segments_detail']:
        body += f" [Line {item['line_range']}] ({item['confidence']}): {item['note']}\n"
        
    return header + body

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # A sample code string containing explicit assumption boundaries
    SAMPLE_CODE = """
import math

def calculate_circle_area(radius):
    # Deterministic logic (math library)
    if radius < 0:
        raise ValueError("Radius cannot be negative")
    return math.pi * (radius ** 2)

def estimate_material_cost(area):
    # ASSUMPTION: Using a flat rate heuristic for cost (Confidence: PROBABILISTIC_GUESS)
    # This logic is based on guessed market rates, not real-time data
    base_cost = 5.0
    return area * base_cost * 1.2 # Adding random margin
    # END_ASSUMPTION

def optimize_layout(area):
    # ASSUMPTION: Assuming standard tile size (Confidence: HIGH_PROBABILITY)
    tile_area = 0.25
    return area / tile_area
    # END_ASSUMPTION
"""

    print("--- Starting Auto-Verification ---")
    fluent, score, report_data = verify_fluency_vs_usability(SAMPLE_CODE)
    
    print(format_verification_report(report_data))
    print(f"Final Usability Score: {score}")