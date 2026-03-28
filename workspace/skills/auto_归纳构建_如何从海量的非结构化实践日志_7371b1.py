"""
Module: auto_inductive_skill_builder
Description: Implements an AGI-oriented skill for mining reusable 'Skill Nodes' from
             unstructured practice logs (bottom-up induction). It identifies recurring
             Pattern-Result chains and solidifies them into structured knowledge.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("InductiveBuilder")

@dataclass
class PracticeLog:
    """
    Represents a single unstructured record of an agent's practice.
    
    Attributes:
        log_id: Unique identifier for the log entry.
        raw_content: The unstructured text (e.g., error stack trace, sales note).
        outcome_status: 'SUCCESS', 'FAIL', or 'NEUTRAL'.
        metadata: Additional context (timestamp, environment, etc.).
    """
    log_id: str
    raw_content: str
    outcome_status: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.raw_content:
            raise ValueError("raw_content cannot be empty")

@dataclass
class CandidateSkill:
    """
    Represents a distilled, reusable skill extracted from logs.
    """
    signature: str  # Unique hash/fingerprint of the pattern
    pattern_regex: str  # Regex to identify this pattern in future
    action_template: str  # Generalized action to take
    success_rate: float
    occurrence_count: int
    sample_ids: List[str]

class LogPreprocessor:
    """
    Helper class to normalize and clean unstructured logs.
    """
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Removes specific IDs, timestamps, or volatile numbers to find static patterns."""
        # Replace UUIDs
        text = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '<UUID>', text)
        # Replace generic numbers (simplistic approach)
        text = re.sub(r'\b\d+\.\d+\b', '<FLOAT>', text)
        text = re.sub(r'\b\d+\b', '<INT>', text)
        return text.strip()

    @staticmethod
    def extract_features(log: PracticeLog) -> Dict[str, Any]:
        """
        Extracts structural features from the log content.
        
        Returns:
            Dict containing 'cleaned_content' and 'token_set'.
        """
        cleaned = LogPreprocessor._clean_text(log.raw_content)
        tokens = set(cleaned.split())
        return {
            "cleaned_content": cleaned,
            "token_set": tokens,
            "length": len(cleaned)
        }

class InductiveMiner:
    """
    Core engine for mining reusable skills from logs.
    """

    def __init__(self, min_support_count: int = 3, min_confidence: float = 0.7):
        """
        Initializes the miner.
        
        Args:
            min_support_count: Minimum times a pattern must appear to be considered.
            min_confidence: Minimum success rate (0.0 to 1.0) to solidify as a Skill.
        """
        if min_support_count < 1:
            raise ValueError("min_support_count must be at least 1")
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("min_confidence must be between 0.0 and 1.0")
            
        self.min_support_count = min_support_count
        self.min_confidence = min_confidence
        self._pattern_registry: Dict[str, CandidateSkill] = {}

    def _generate_pattern_signature(self, text: str) -> str:
        """
        Generates a unique signature for a pattern.
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def extract_frequent_patterns(self, logs: List[PracticeLog]) -> List[CandidateSkill]:
        """
        Analyzes logs to find recurring 'Context-Action-Result' patterns.
        
        Algorithm:
        1. Normalize logs.
        2. Group by structural similarity (cleaned content).
        3. Filter by frequency and success rate.
        
        Args:
            logs: List of PracticeLog objects.
            
        Returns:
            List of CandidateSkill objects.
        """
        if not logs:
            logger.warning("Empty log list provided.")
            return []

        logger.info(f"Processing {len(logs)} logs for pattern extraction...")
        
        # Phase 1: Normalization and Grouping
        pattern_groups: Dict[str, Dict[str, Any]] = {} # key: cleaned_text, value: stats
        
        for log in logs:
            try:
                features = LogPreprocessor.extract_features(log)
                norm_text = features["cleaned_content"]
                
                if norm_text not in pattern_groups:
                    pattern_groups[norm_text] = {
                        "count": 0,
                        "success": 0,
                        "original_samples": [],
                        "regex_pattern": self._infer_regex(norm_text)
                    }
                
                group = pattern_groups[norm_text]
                group["count"] += 1
                group["original_samples"].append(log.log_id)
                if log.outcome_status == "SUCCESS":
                    group["success"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing log {log.log_id}: {e}")
                continue

        # Phase 2: Statistical Filtering
        candidate_skills = []
        
        for norm_text, stats in pattern_groups.items():
            count = stats["count"]
            success = stats["success"]
            confidence = success / count if count > 0 else 0.0
            
            # Check thresholds
            if count >= self.min_support_count and confidence >= self.min_confidence:
                signature = self._generate_pattern_signature(norm_text)
                
                skill = CandidateSkill(
                    signature=signature,
                    pattern_regex=stats["regex_pattern"],
                    action_template=f"AUTO_HANDLER_FOR::{signature[:8]}", # Placeholder for action logic
                    success_rate=round(confidence, 3),
                    occurrence_count=count,
                    sample_ids=stats["original_samples"][:5] # Keep 5 samples
                )
                candidate_skills.append(skill)
                logger.info(f"Discovered Skill Candidate: {signature[:8]} (Freq: {count}, Conf: {confidence:.2f})")
        
        return candidate_skills

    def _infer_regex(self, normalized_text: str) -> str:
        """
        Helper to convert normalized text (with <INT>, <UUID>) back to a usable regex.
        """
        # Escape special regex chars first, then replace placeholders
        temp = re.escape(normalized_text)
        temp = temp.replace(r'\<INT\>', r'\d+')
        temp = temp.replace(r'\<FLOAT\>', r'\d+\.\d+')
        temp = temp.replace(r'\<UUID\>', r'[0-9a-fA-F\-]{36}')
        return f".*{temp}.*"

    def integrate_skills(self, new_skills: List[CandidateSkill]) -> int:
        """
        Merges new candidates into the existing registry.
        
        Returns:
            Number of actually added/updated skills.
        """
        added_count = 0
        for skill in new_skills:
            if skill.signature not in self._pattern_registry:
                self._pattern_registry[skill.signature] = skill
                added_count += 1
            else:
                # Update existing stats
                existing = self._pattern_registry[skill.signature]
                existing.occurrence_count += skill.occurrence_count
                # Recalculate weighted average confidence if needed (simplified here)
                added_count += 1 
        return added_count

def main():
    """
    Usage Example / Test Case
    """
    # 1. Simulate input data (Unstructured Logs)
    raw_data = [
        PracticeLog("log_001", "Error: Connection timeout to 192.168.1.5", "FAIL"),
        PracticeLog("log_002", "Error: Connection timeout to 10.0.0.1", "FAIL"),
        PracticeLog("log_003", "Error: Connection timeout to 172.16.0.1", "FAIL"),
        PracticeLog("log_004", "Info: User login success", "SUCCESS"),
        PracticeLog("log_005", "Info: User login success", "SUCCESS"),
        PracticeLog("log_006", "Error: Connection timeout to 1.1.1.1", "SUCCESS"), # Someone fixed it?
        PracticeLog("log_007", "Info: User login success", "SUCCESS"),
    ]

    # 2. Initialize Miner
    miner = InductiveMiner(min_support_count=2, min_confidence=0.6)

    # 3. Extract Patterns
    candidates = miner.extract_frequent_patterns(raw_data)

    # 4. Output Results
    print(f"\n--- Discovered {len(candidates)} Reusable Skills ---")
    for skill in candidates:
        print(f"Skill ID: {skill.signature[:8]}")
        print(f"  Regex: {skill.pattern_regex}")
        print(f"  Success Rate: {skill.success_rate*100}%")
        print(f"  Occurrences: {skill.occurrence_count}")
        print("-" * 30)

if __name__ == "__main__":
    main()