"""
Module: semantic_drift_resolver.py

This module provides a mechanism to detect and handle 'Semantic Drift' during
Cross-Domain Migration of AI skills.

Specifically, it addresses the scenario where a text processing skill (designed
for Web Crawlers) is applied to a new domain (Bioinformatics/Gene Sequences).
It implements a 'Semantic Boundary Detection' layer to validate assumptions
before execution, preventing the generation of garbage data.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DriftStatus(Enum):
    """Enumeration for semantic drift check results."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    FALSIFIED = "FALSIFIED"

@dataclass
class SkillMetadata:
    """Metadata describing the skill's original domain and requirements."""
    name: str
    source_domain: str
    target_domain: str
    required_pattern: str  # Regex pattern expected by the skill
    description: str = ""

@dataclass
class DataProfile:
    """Statistical profile of the input data."""
    avg_token_length: float
    whitespace_ratio: float
    non_alnum_ratio: float
    matches_required_pattern: bool
    sample_tokens: List[str] = field(default_factory=list)

class SemanticBoundaryDetector:
    """
    Detects semantic drift by validating input data against a skill's
    pre-condition assumptions.
    """

    def __init__(self, skill_meta: SkillMetadata, strict_mode: bool = True):
        """
        Initialize the detector.

        Args:
            skill_meta (SkillMetadata): The metadata of the skill being migrated.
            strict_mode (bool): If True, mismatches raise exceptions. If False, logs warnings.
        """
        self.skill_meta = skill_meta
        self.strict_mode = strict_mode
        logger.info(f"Initialized Boundary Detector for skill: {skill_meta.name}")

    def _calculate_whitespace_ratio(self, text: str) -> float:
        """
        Helper: Calculate the ratio of whitespace characters to total length.
        
        Args:
            text (str): Input text string.
            
        Returns:
            float: Ratio between 0.0 and 1.0.
        """
        if not text:
            return 0.0
        ws_count = len(re.findall(r'\s', text))
        return ws_count / len(text)

    def _analyze_data_statistics(self, data: List[str]) -> DataProfile:
        """
        Core Function 1: Analyzes the statistical properties of the input data.
        
        This creates a fingerprint of the data to compare against expected semantic boundaries.
        
        Args:
            data (List[str]): A list of text strings to analyze.
            
        Returns:
            DataProfile: An object containing statistical metrics.
        """
        logger.debug(f"Analyzing statistics for {len(data)} data points.")
        
        total_len = 0
        total_ws = 0
        total_non_alnum = 0
        token_lengths = []
        matches = 0
        sample_tokens = []
        
        pattern = re.compile(self.skill_meta.required_pattern)

        for item in data:
            total_len += len(item)
            total_ws += len(re.findall(r'\s', item))
            total_non_alnum += len(re.findall(r'[^a-zA-Z0-9\s]', item))
            
            tokens = item.split()
            if tokens:
                token_lengths.extend([len(t) for t in tokens])
                if not sample_tokens and len(tokens) < 10:
                    sample_tokens = tokens
            
            if pattern.search(item):
                matches += 1

        avg_token_len = sum(token_lengths) / len(token_lengths) if token_lengths else 0
        ws_ratio = total_ws / total_len if total_len > 0 else 0
        non_alnum_ratio = total_non_alnum / total_len if total_len > 0 else 0
        pattern_match_ratio = matches / len(data) if data else 0

        return DataProfile(
            avg_token_length=avg_token_len,
            whitespace_ratio=ws_ratio,
            non_alnum_ratio=non_alnum_ratio,
            matches_required_pattern=(pattern_match_ratio > 0.8),  # Threshold for pattern match
            sample_tokens=sample_tokens[:5]
        )

    def validate_semantic_boundaries(self, profile: DataProfile) -> Tuple[DriftStatus, str]:
        """
        Core Function 2: Validates the data profile against semantic assumptions.
        
        It checks for specific heuristics that indicate the skill is being applied
        to the wrong type of data (e.g., applying NLP text cleaning to Gene Sequences).
        
        Args:
            profile (DataProfile): The statistical profile of the dataset.
            
        Returns:
            Tuple[DriftStatus, str]: Status of the validation and a reason message.
        """
        reasons = []
        status = DriftStatus.SAFE
        
        # Heuristic 1: Whitespace Density
        # NLP Text usually has significant whitespace. Gene sequences usually do not.
        if profile.whitespace_ratio < 0.05:
            msg = f"Low whitespace ratio ({profile.whitespace_ratio:.2f}). Expected structured text."
            reasons.append(msg)
            status = DriftStatus.FALSIFIED
        
        # Heuristic 2: Token Length Variance (simplified check via average)
        # Words are usually 3-10 chars. Gene tokens (codons/proteins) often differ significantly.
        if profile.avg_token_length > 20 or profile.avg_token_length < 1:
            msg = f"Abnormal average token length ({profile.avg_token_length:.2f})."
            reasons.append(msg)
            status = DriftStatus.WARNING

        # Heuristic 3: Pattern Matching
        if not profile.matches_required_pattern:
            msg = "Input data does not match the required regex pattern of the skill."
            reasons.append(msg)
            status = DriftStatus.FALSIFIED

        if status != DriftStatus.SAFE:
            full_reason = "; ".join(reasons)
            logger.warning(f"Semantic Drift Detected: {full_reason}")
            return status, full_reason

        logger.info("Semantic boundaries validated successfully.")
        return DriftStatus.SAFE, "Data fits semantic profile."

    def run_skill_with_protection(self, data: List[str], skill_logic_func: callable) -> Any:
        """
        Auxiliary Function: Wrapper that executes the skill logic only if validation passes.
        
        Args:
            data (List[str]): Input data.
            skill_logic_func (callable): The function containing the actual skill logic.
            
        Returns:
            Any: Result of the skill logic or None if validation fails.
            
        Raises:
            ValueError: If strict_mode is True and validation fails.
        """
        logger.info("Starting Skill Execution Pipeline with Boundary Protection...")
        
        if not data:
            logger.error("Input data is empty.")
            return None

        # Step 1: Analyze
        profile = self._analyze_data_statistics(data)
        
        # Step 2: Validate
        status, reason = self.validate_semantic_boundaries(profile)
        
        # Step 3: Execute or Reject
        if status == DriftStatus.FALSIFIED:
            msg = f"Execution Halted: Semantic Drift detected. Reason: {reason}"
            if self.strict_mode:
                raise ValueError(msg)
            else:
                logger.error(msg)
                return None
        
        if status == DriftStatus.WARNING:
            logger.warning(f"Proceeding with warnings: {reason}")
            
        logger.info("Executing Skill Logic...")
        try:
            result = skill_logic_func(data)
            logger.info("Skill Execution Completed Successfully.")
            return result
        except Exception as e:
            logger.exception("Error during skill execution logic.")
            raise

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Define the Skill Metadata (Web Crawler Context)
    web_text_skill_meta = SkillMetadata(
        name="web_text_cleaner",
        source_domain="web_crawler",
        target_domain="bioinformatics",
        required_pattern=r'[a-zA-Z0-9\s\.,]', # Expects mostly standard text
        description="Cleans HTML artifacts and normalizes whitespace."
    )

    # 2. Define a Dummy Skill Logic
    def simple_text_cleaner(data: List[str]) -> List[str]:
        """A dummy skill that expects space-separated text."""
        return [item.strip().lower() for item in data]

    # 3. Initialize Detector
    detector = SemanticBoundaryDetector(web_text_skill_meta, strict_mode=True)

    # 4. Test with Valid Data (Web Text)
    web_data = ["This is a valid sentence.", "Another piece of text content."]
    print("\n--- Testing with Valid Web Data ---")
    try:
        # Should pass
        result = detector.run_skill_with_protection(web_data, simple_text_cleaner)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Blocked: {e}")

    # 5. Test with Drifted Data (Gene Sequence)
    # Simulating a FASTA-like sequence without headers, continuous strings.
    gene_data = [
        "ATGCGTACGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
        "TACGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA"
    ]
    
    print("\n--- Testing with Drifted Gene Data ---")
    try:
        # Should fail (raise ValueError) because whitespace ratio is too low
        # and pattern might not match expectations of standard text
        result = detector.run_skill_with_protection(gene_data, simple_text_cleaner)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Expected Failure Triggered: {e}")