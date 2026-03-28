"""
Module: implicit_dependency_miner.py
Description: [Human-Machine Symbiosis] Mines implicit contextual dependencies in skill execution
             to calculate the hidden prior probability of skill success.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    Represents a node in the skill graph.
    
    Attributes:
        id: Unique identifier for the skill
        name: Human-readable name of the skill
        explicit_deps: List of explicit dependency skill IDs
        success_rate: Base success rate without context
        metadata: Additional metadata about the skill
    """
    id: str
    name: str
    explicit_deps: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate input data after initialization."""
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Skill ID must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Skill name must be a non-empty string")
        if not 0 <= self.success_rate <= 1:
            raise ValueError("Success rate must be between 0 and 1")


class ImplicitDependencyMiner:
    """
    Analyzes skill execution logs to detect implicit contextual dependencies
    and calculates their impact on skill success probability.
    
    This module uses causal inference techniques to identify hidden factors
    that influence skill execution outcomes but are not explicitly recorded
    in the skill graph.
    """
    
    def __init__(self, significance_threshold: float = 0.15, min_samples: int = 30):
        """
        Initialize the dependency miner.
        
        Args:
            significance_threshold: Minimum probability difference to consider significant
            min_samples: Minimum number of samples required for reliable analysis
            
        Raises:
            ValueError: If parameters are outside valid ranges
        """
        if not 0 < significance_threshold < 1:
            raise ValueError("Significance threshold must be between 0 and 1")
        if min_samples < 10:
            raise ValueError("Minimum samples must be at least 10")
            
        self.significance_threshold = significance_threshold
        self.min_samples = min_samples
        self._context_db: Dict[str, Dict] = {}
        self._skill_db: Dict[str, SkillNode] = {}
        self._execution_history: List[Dict] = []
        
        logger.info("Initialized ImplicitDependencyMiner with threshold %.2f", significance_threshold)
    
    def register_skill(self, skill: SkillNode) -> None:
        """
        Register a skill in the knowledge base.
        
        Args:
            skill: SkillNode object to register
            
        Raises:
            TypeError: If input is not a SkillNode
            ValueError: If skill ID already exists
        """
        if not isinstance(skill, SkillNode):
            raise TypeError("Input must be a SkillNode object")
            
        if skill.id in self._skill_db:
            raise ValueError(f"Skill ID {skill.id} already exists")
            
        self._skill_db[skill.id] = skill
        logger.debug("Registered skill: %s (%s)", skill.name, skill.id)
    
    def record_execution(self, skill_id: str, context: Dict[str, Union[str, float, bool]], 
                         outcome: bool, timestamp: Optional[datetime] = None) -> None:
        """
        Record a skill execution instance with its context and outcome.
        
        Args:
            skill_id: ID of the executed skill
            context: Dictionary of contextual factors and their values
            outcome: Boolean indicating success (True) or failure (False)
            timestamp: Optional timestamp of execution (defaults to now)
            
        Raises:
            ValueError: If skill_id is not registered
        """
        if skill_id not in self._skill_db:
            raise ValueError(f"Unregistered skill ID: {skill_id}")
            
        if not isinstance(context, dict):
            raise TypeError("Context must be a dictionary")
            
        entry = {
            "skill_id": skill_id,
            "context": context.copy(),
            "outcome": outcome,
            "timestamp": timestamp or datetime.now()
        }
        
        self._execution_history.append(entry)
        logger.debug("Recorded execution for skill %s with outcome %s", skill_id, outcome)
    
    def _validate_context_data(self, skill_id: str) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Internal helper to validate and prepare context data for analysis.
        
        Args:
            skill_id: ID of the skill to analyze
            
        Returns:
            Tuple of (context_df, outcomes) where:
                context_df: DataFrame with one-hot encoded context factors
                outcomes: Array of boolean outcomes
                
        Raises:
            ValueError: If insufficient data for analysis
        """
        skill_executions = [e for e in self._execution_history if e["skill_id"] == skill_id]
        
        if len(skill_executions) < self.min_samples:
            raise ValueError(f"Insufficient data for skill {skill_id}. Need {self.min_samples}, have {len(skill_executions)}")
            
        # Extract all unique context keys
        all_context_keys = set()
        for entry in skill_executions:
            all_context_keys.update(entry["context"].keys())
            
        # Prepare data for DataFrame
        records = []
        outcomes = []
        
        for entry in skill_executions:
            record = {}
            for key in all_context_keys:
                val = entry["context"].get(key, None)
                # Convert to string for categorical handling
                record[key] = str(val) if val is not None else "missing"
            records.append(record)
            outcomes.append(entry["outcome"])
            
        df = pd.DataFrame(records)
        outcomes_arr = np.array(outcomes, dtype=bool)
        
        # One-hot encode categorical variables
        df = pd.get_dummies(df, dummy_na=True)
        
        return df, outcomes_arr
    
    def detect_implicit_dependencies(self, skill_id: str) -> Dict[str, Dict]:
        """
        Detect implicit contextual dependencies for a skill using statistical analysis.
        
        This method analyzes the recorded executions to identify context factors
        that significantly influence the success probability of the skill.
        
        Args:
            skill_id: ID of the skill to analyze
            
        Returns:
            Dictionary of detected implicit dependencies with their statistics:
            {
                "context_factor": {
                    "success_rate_when_present": float,
                    "success_rate_when_absent": float,
                    "impact": float,
                    "confidence": float
                },
                ...
            }
            
        Raises:
            ValueError: If skill_id is not registered or insufficient data
        """
        if skill_id not in self._skill_db:
            raise ValueError(f"Unregistered skill ID: {skill_id}")
            
        logger.info("Starting implicit dependency detection for skill: %s", skill_id)
        
        try:
            context_df, outcomes = self._validate_context_data(skill_id)
        except ValueError as e:
            logger.error("Data validation failed: %s", str(e))
            raise
            
        results = {}
        base_success_rate = self._skill_db[skill_id].success_rate
        
        for column in context_df.columns:
            # Skip columns with too many missing values
            if context_df[column].sum() < self.min_samples // 3:
                continue
                
            # Calculate success rates when factor is present/absent
            present_mask = context_df[column] == 1
            absent_mask = ~present_mask
            
            success_when_present = np.mean(outcomes[present_mask]) if present_mask.any() else 0
            success_when_absent = np.mean(outcomes[absent_mask]) if absent_mask.any() else 0
            
            impact = success_when_present - success_when_absent
            confidence = min(present_mask.sum(), absent_mask.sum()) / len(outcomes)
            
            # Only report if impact exceeds threshold
            if abs(impact) >= self.significance_threshold:
                results[column] = {
                    "success_rate_when_present": float(success_when_present),
                    "success_rate_when_absent": float(success_when_absent),
                    "impact": float(impact),
                    "confidence": float(confidence)
                }
                
                logger.debug("Detected implicit dependency: %s (impact: %.2f)", column, impact)
        
        logger.info("Found %d implicit dependencies for skill %s", len(results), skill_id)
        return results
    
    def calculate_adjusted_success_rate(self, skill_id: str, context: Dict[str, Union[str, float, bool]]) -> float:
        """
        Calculate the adjusted success probability considering implicit dependencies.
        
        Uses Bayesian updating to adjust the base success rate based on the presence
        of significant contextual factors.
        
        Args:
            skill_id: ID of the skill to evaluate
            context: Dictionary of current contextual factors
            
        Returns:
            Adjusted success probability (0.0 to 1.0)
            
        Raises:
            ValueError: If skill_id is not registered
        """
        if skill_id not in self._skill_db:
            raise ValueError(f"Unregistered skill ID: {skill_id}")
            
        base_rate = self._skill_db[skill_id].success_rate
        implicit_deps = self.detect_implicit_dependencies(skill_id)
        
        if not implicit_deps:
            logger.debug("No implicit dependencies found for skill %s", skill_id)
            return base_rate
            
        # Bayesian adjustment
        adjusted_rate = base_rate
        normalization = 1.0
        
        for factor, stats in implicit_deps.items():
            # Check if this factor is present in current context
            factor_parts = factor.split("_")
            is_present = False
            
            if len(factor_parts) > 1:
                orig_key = "_".join(factor_parts[:-1])
                orig_val = factor_parts[-1]
                
                if orig_key in context:
                    current_val = context[orig_key]
                    if isinstance(current_val, str):
                        is_present = (current_val == orig_val)
                    else:
                        try:
                            is_present = (str(current_val) == orig_val)
                        except:
                            pass
            
            # Update probability based on factor presence
            if is_present:
                likelihood = stats["success_rate_when_present"] / stats["success_rate_when_absent"]
                adjusted_rate *= likelihood
                normalization *= likelihood
            else:
                likelihood = (1 - stats["success_rate_when_present"]) / (1 - stats["success_rate_when_absent"])
                adjusted_rate *= likelihood
                normalization *= likelihood
        
        # Normalize to get proper probability
        if normalization > 0:
            adjusted_prob = adjusted_rate / (adjusted_rate + (1 - base_rate) * normalization)
        else:
            adjusted_prob = base_rate
            
        # Ensure probability is within bounds
        adjusted_prob = max(0.0, min(1.0, adjusted_prob))
        
        logger.info("Adjusted success rate for skill %s: %.2f (base: %.2f)", 
                   skill_id, adjusted_prob, base_rate)
        return adjusted_prob


# Example usage
if __name__ == "__main__":
    try:
        # Create some sample skills
        skill1 = SkillNode(
            id="street_vending",
            name="Street Vending",
            explicit_deps=["inventory_management"],
            success_rate=0.65
        )
        
        skill2 = SkillNode(
            id="outdoor_photography",
            name="Outdoor Photography",
            explicit_deps=["camera_operation"],
            success_rate=0.70
        )
        
        # Initialize the miner
        miner = ImplicitDependencyMiner(significance_threshold=0.1, min_samples=20)
        
        # Register skills
        miner.register_skill(skill1)
        miner.register_skill(skill2)
        
        # Record some sample executions with context
        sample_contexts = [
            {"weather": "sunny", "location": "park", "crowd_level": "high"},
            {"weather": "rainy", "location": "park", "crowd_level": "low"},
            {"weather": "sunny", "location": "downtown", "crowd_level": "high"},
            {"weather": "cloudy", "location": "park", "crowd_level": "medium"}
        ]
        
        # Simulate execution history
        for i in range(25):
            ctx = sample_contexts[i % len(sample_contexts)]
            # Success more likely in sunny weather
            outcome = (ctx["weather"] == "sunny" and np.random.random() < 0.8) or \
                     (ctx["weather"] != "sunny" and np.random.random() < 0.5)
            
            miner.record_execution("street_vending", ctx, outcome)
            
            # Photography succeeds more in good weather and interesting locations
            outcome2 = (ctx["weather"] in ["sunny", "cloudy"] and ctx["location"] == "park") and \
                      (np.random.random() < 0.85)
            miner.record_execution("outdoor_photography", ctx, outcome2)
        
        # Detect implicit dependencies
        print("\nDetecting implicit dependencies for street_vending:")
        deps = miner.detect_implicit_dependencies("street_vending")
        for factor, stats in deps.items():
            print(f"  {factor}: impact={stats['impact']:.2f}, confidence={stats['confidence']:.2f}")
        
        # Calculate adjusted success rate for a specific context
        test_context = {"weather": "sunny", "location": "park", "crowd_level": "high"}
        adjusted_prob = miner.calculate_adjusted_success_rate("street_vending", test_context)
        print(f"\nAdjusted success probability for street_vending in {test_context}: {adjusted_prob:.2f}")
        
    except Exception as e:
        logger.error("Error in example execution: %s", str(e))
        raise