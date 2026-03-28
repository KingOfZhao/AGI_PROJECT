"""
AGI Pattern Emergence Detection Module

This module implements a bottom-up inductive approach to detect meaningful patterns
from unstructured interaction logs. It identifies recurring structures and
'crystallizes' them into skills by distinguishing signal from noise using
statistical significance scoring.

Key Concepts:
- Bottom-Up Induction: Starting from raw data sequences to build higher-level abstractions.
- Pattern Emergence: Detecting structures that appear more frequently than random chance.
- Crystallization: Converting a validated pattern into a reusable skill object.

Input Format:
    List of interaction logs, where each log is a list of tokens (strings).
    Example: [["move", "grab", "lift"], ["scan", "move", "grab"]]

Output Format:
    A list of skill dictionaries, each containing the pattern sequence, frequency,
    and significance score.
"""

import logging
from typing import List, Dict, Tuple, Any
from collections import defaultdict
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternMiningError(Exception):
    """Custom exception for errors during pattern mining."""
    pass


def _calculate_significance_score(frequency: int, length: int, total_logs: int) -> float:
    """
    Calculate the significance score of a pattern to distinguish it from noise.

    This helper function uses a heuristic based on frequency and complexity (length).
    Longer patterns that appear frequently are considered more significant than
    short, common patterns or long, rare patterns.

    Args:
        frequency: How often the pattern appears.
        length: The number of tokens in the pattern.
        total_logs: Total number of logs processed (for normalization).

    Returns:
        A float representing the significance score.
    """
    if total_logs == 0:
        return 0.0

    # Normalize frequency
    norm_freq = frequency / total_logs

    # Complexity penalty: longer patterns are harder to occur by chance,
    # but we need enough data to support them.
    # Heuristic: Score = Frequency * Length * log(Length + 1)
    # This rewards patterns that are both frequent and structurally complex.
    score = norm_freq * length * math.log(length + 1)

    return score * 100  # Scale up for readability


def detect_emerging_patterns(
    interaction_logs: List[List[str]],
    min_support: int = 2,
    max_pattern_length: int = 5
) -> Dict[Tuple[str, ...], int]:
    """
    Scan interaction logs to find frequent subsequences (patterns).

    This is the core 'Bottom-Up' function. It iterates through raw data
    to extract all possible subsequences within the length constraints
    and counts their occurrences.

    Args:
        interaction_logs: A list of logs, where each log is a sequence of tokens.
        min_support: The minimum number of times a pattern must appear to be considered.
        max_pattern_length: The maximum length of a pattern to detect (cognitive limit).

    Returns:
        A dictionary mapping patterns (as tuples of strings) to their frequencies.

    Raises:
        PatternMiningError: If input data is invalid.
    """
    # Data Validation
    if not isinstance(interaction_logs, list):
        raise PatternMiningError("Input interaction_logs must be a list.")
    if not all(isinstance(log, list) for log in interaction_logs):
        raise PatternMiningError("Each log in interaction_logs must be a list of strings.")
    if min_support < 1:
        raise PatternMiningError("min_support must be at least 1.")
    if max_pattern_length < 1:
        raise PatternMiningError("max_pattern_length must be at least 1.")

    pattern_counts = defaultdict(int)
    total_logs = len(interaction_logs)

    logger.info(f"Starting pattern detection on {total_logs} logs...")

    for idx, log in enumerate(interaction_logs):
        if not log:
            continue

        # Generate all subsequences for the current log
        # This is a simplified approach. For production, consider PrefixSpan or FP-Growth.
        log_len = len(log)
        for i in range(log_len):
            # Limit j to create a sliding window of max_pattern_length
            for j in range(i + 1, min(i + max_pattern_length + 1, log_len + 1)):
                subsequence = tuple(log[i:j])
                pattern_counts[subsequence] += 1

    # Filter by min_support
    frequent_patterns = {
        k: v for k, v in pattern_counts.items() if v >= min_support
    }

    logger.info(f"Detected {len(frequent_patterns)} candidate patterns.")
    return frequent_patterns


def crystallize_skills(
    pattern_counts: Dict[Tuple[str, ...], int],
    total_logs: int,
    significance_threshold: float = 1.5
) -> List[Dict[str, Any]]:
    """
    Filter and 'crystallize' frequent patterns into formal AGI skills.

    This function applies the significance threshold to distinguish meaningful
    patterns (skills) from random noise. It structures the output into a
    standardized skill format.

    Args:
        pattern_counts: Dictionary of patterns and their frequencies from detect_emerging_patterns.
        total_logs: Total number of logs (used for score normalization).
        significance_threshold: Minimum score required for a pattern to become a skill.

    Returns:
        A list of skill dictionaries.
    """
    if not pattern_counts:
        logger.warning("No patterns provided for crystallization.")
        return []

    crystallized_skills = []

    for pattern, freq in pattern_counts.items():
        score = _calculate_significance_score(freq, len(pattern), total_logs)

        if score >= significance_threshold:
            skill = {
                "skill_id": f"skill_{hash(pattern)}",  # Simple ID generation
                "pattern_sequence": list(pattern),
                "frequency": freq,
                "complexity": len(pattern),
                "significance_score": round(score, 4),
                "description": f"Auto-generated skill from pattern: {' -> '.join(pattern)}"
            }
            crystallized_skills.append(skill)

    # Sort by significance score (descending)
    crystallized_skills.sort(key=lambda x: x["significance_score"], reverse=True)

    logger.info(f"Crystallized {len(crystallized_skills)} skills from patterns.")
    return crystallized_skills


# Example Usage
if __name__ == "__main__":
    # Mock Data: Unstructured interaction logs from an AGI agent
    # Imagine an agent navigating a grid and manipulating objects.
    raw_logs = [
        ["scan", "move_forward", "move_forward", "grab", "lift"],
        ["scan", "move_forward", "move_forward", "grab", "lift"],
        ["scan", "move_left", "grab", "lift"],
        ["scan", "move_forward", "move_forward", "grab", "lift", "drop"],
        ["rotate", "scan", "move_forward", "move_forward", "grab", "lift"],
        ["scan", "move_forward", "grab"],  # Noise/Incomplete
        ["scan", "move_forward", "move_forward", "grab", "lift"]
    ]

    try:
        # Step 1: Detect emerging patterns (Bottom-Up Induction)
        patterns = detect_emerging_patterns(
            interaction_logs=raw_logs,
            min_support=2,
            max_pattern_length=4
        )

        # Step 2: Crystallize into Skills (Filtering noise)
        skills = crystallize_skills(
            pattern_counts=patterns,
            total_logs=len(raw_logs),
            significance_threshold=2.0  # Adjust based on sensitivity needs
        )

        # Output Results
        print("\n=== Detected AGI Skills ===")
        for skill in skills:
            print(f"ID: {skill['skill_id']}")
            print(f"Pattern: {skill['pattern_sequence']}")
            print(f"Score: {skill['significance_score']} (Freq: {skill['frequency']})")
            print("-" * 30)

    except PatternMiningError as e:
        logger.error(f"Failed to process logs: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")