"""
Module: qualitative_to_quantitative_constraint_translator
This module is designed to convert qualitative software requirements (fuzzy intent)
into quantitative, machine-executable constraints (performance indicators).

It serves as a translation layer in an AGI system, bridging the gap between
human-centric descriptions (e.g., "make it robust") and machine-centric
metrics (e.g., "unit test coverage > 90%").
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class QuantitativeConstraint:
    """
    Represents a specific, measurable constraint.
    
    Attributes:
        metric_name: The name of the metric (e.g., 'latency_p99').
        operator: Comparison operator (e.g., '<', '>=').
        value: The target numerical value.
        unit: The unit of measurement (e.g., 'ms', '%', 'score').
        confidence: Confidence level of the translation (0.0 to 1.0).
    """
    metric_name: str
    operator: str
    value: float
    unit: str
    confidence: float = 1.0
    description: str = ""

    def to_dict(self) -> Dict:
        return self.__dict__

@dataclass
class QualitativeIntent:
    """
    Represents the user's fuzzy input.
    
    Attributes:
        text: The raw natural language text.
        category: Estimated category (e.g., 'performance', 'maintainability').
    """
    text: str
    category: Optional[str] = None

# --- Knowledge Base (Heuristics) ---
# Mapping fuzzy keywords to specific metric templates
KNOWLEDGE_BASE = {
    "maintainability": {
        "patterns": [r"优雅", r"clean code", r"好读", r"可维护", r"elegant", r"readable"],
        "metrics": [
            {"name": "linter_score", "op": ">=", "val": 90, "unit": "score", "desc": "Static analysis score"},
            {"name": "cyclomatic_complexity", "op": "<=", "val": 10, "unit": "count", "desc": "Max complexity per function"},
            {"name": "docstring_coverage", "op": ">=", "val": 80, "unit": "%", "desc": "Documentation coverage"}
        ]
    },
    "stability": {
        "patterns": [r"稳定", r"不崩", r"robust", r"reliable", r"高可用"],
        "metrics": [
            {"name": "error_rate", "op": "<", "val": 0.1, "unit": "%", "desc": "System error rate"},
            {"name": "uptime", "op": ">=", "val": 99.9, "unit": "%", "desc": "System availability"},
            {"name": "crash_count", "op": "==", "val": 0, "unit": "count", "desc": "Fatal errors per deployment"}
        ]
    },
    "performance": {
        "patterns": [r"快", r"高性能", r"响应迅速", r"low latency", r"fast"],
        "metrics": [
            {"name": "latency_p99", "op": "<", "val": 200, "unit": "ms", "desc": "99th percentile latency"},
            {"name": "throughput", "op": ">=", "val": 1000, "unit": "req/s", "desc": "Requests handled per second"}
        ]
    },
    "security": {
        "patterns": [r"安全", r"secure", r"privacy", r"hacking"],
        "metrics": [
            {"name": "vulnerability_count", "op": "==", "val": 0, "unit": "count", "desc": "Critical vulnerabilities"},
            {"name": "dependency_freshness", "op": "<", "val": 30, "unit": "days", "desc": "Days since last dependency update"}
        ]
    }
}

class ConstraintTranslator:
    """
    Translates Qualitative Intents into Quantitative Constraints.
    
    Uses a knowledge base of patterns and heuristics to map natural language
    to specific system metrics.
    """

    def __init__(self, knowledge_base: Dict = None):
        """
        Initialize the translator.
        
        Args:
            knowledge_base: Custom mapping rules. Defaults to the built-in KNOWLEDGE_BASE.
        """
        self.kb = knowledge_base if knowledge_base else KNOWLEDGE_BASE
        logger.info("ConstraintTranslator initialized with %d categories.", len(self.kb))

    def _classify_intent(self, text: str) -> Optional[str]:
        """
        Helper function to classify the text into a domain category.
        
        Args:
            text: Input natural language string.
            
        Returns:
            The matching category key or None.
        """
        text_lower = text.lower()
        for category, data in self.kb.items():
            for pattern in data["patterns"]:
                if re.search(pattern, text_lower):
                    logger.debug(f"Pattern '{pattern}' matched for category '{category}'")
                    return category
        return None

    def _validate_constraints(self, constraints: List[QuantitativeConstraint]) -> List[QuantitativeConstraint]:
        """
        Validates and filters generated constraints.
        
        Ensures values are within logical bounds (e.g., percentage <= 100).
        
        Args:
            constraints: List of generated constraints.
            
        Returns:
            Filtered list of valid constraints.
        """
        valid_constraints = []
        for c in constraints:
            # Boundary Checks
            if c.unit == "%" and c.value > 100:
                logger.warning(f"Invalid percentage value {c.value} for {c.metric_name}. Capping at 100.")
                c.value = 100.0
            
            if c.value < 0 and c.metric_name not in ['temperature', 'debt']:
                logger.warning(f"Negative value found for {c.metric_name}. Taking absolute.")
                c.value = abs(c.value)
                
            valid_constraints.append(c)
        
        return valid_constraints

    def translate(self, intent: QualitativeIntent) -> List[QuantitativeConstraint]:
        """
        Core Function 1: Translates a fuzzy intent into a list of specific constraints.
        
        Args:
            intent: A QualitativeIntent object containing the user's requirement.
            
        Returns:
            A list of QuantitativeConstraint objects.
            
        Raises:
            ValueError: If the intent text is empty.
        """
        if not intent.text or not intent.text.strip():
            logger.error("Empty intent text provided.")
            raise ValueError("Intent text cannot be empty.")

        logger.info(f"Translating intent: '{intent.text}'")
        
        # 1. Classify the intent
        category = self._classify_intent(intent.text)
        if not category:
            logger.warning(f"No specific category found for intent: '{intent.text}'. Defaulting to generic metrics.")
            # Fallback logic could go here; for now, return empty
            return []

        intent.category = category
        kb_entry = self.kb[category]
        
        # 2. Generate Constraints based on templates
        generated_constraints = []
        for template in kb_entry["metrics"]:
            constraint = QuantitativeConstraint(
                metric_name=template["name"],
                operator=template["op"],
                value=float(template["val"]),
                unit=template["unit"],
                description=template.get("desc", ""),
                confidence=0.85 # Heuristic confidence
            )
            generated_constraints.append(constraint)
        
        # 3. Validate Data
        valid_constraints = self._validate_constraints(generated_constraints)
        
        logger.info(f"Generated {len(valid_constraints)} constraints for category '{category}'.")
        return valid_constraints

    def generate_performance_profile(self, intents: List[QualitativeIntent]) -> Dict[str, Dict]:
        """
        Core Function 2: Aggregates multiple intents into a system performance profile.
        
        This function creates a unified view of constraints, handling potential conflicts.
        
        Args:
            intents: List of QualitativeIntent objects.
            
        Returns:
            A dictionary representing the System Performance Profile (SPP).
        """
        if not intents:
            logger.warning("No intents provided for profile generation.")
            return {}

        profile = {}
        logger.info(f"Generating performance profile for {len(intents)} intents.")

        for intent in intents:
            try:
                constraints = self.translate(intent)
                for c in constraints:
                    key = c.metric_name
                    if key in profile:
                        # Conflict resolution: Keep the strictest constraint
                        # Simple heuristic: if operator is <, take min; if >, take max
                        existing_val = profile[key]["value"]
                        if c.operator == "<" and c.value < existing_val:
                            profile[key] = c.to_dict()
                        elif c.operator == ">" or c.operator == ">=":
                            if c.value > existing_val:
                                profile[key] = c.to_dict()
                        else:
                            pass # Keep existing
                    else:
                        profile[key] = c.to_dict()
            except ValueError as e:
                logger.error(f"Skipping invalid intent: {e}")
                continue

        return profile

# --- Usage Example ---

if __name__ == "__main__":
    # Initialize the translator
    translator = ConstraintTranslator()

    # Example 1: Single Intent Translation
    intent_1 = QualitativeIntent(text="The payment system must be extremely robust and stable.")
    constraints_1 = translator.translate(intent_1)
    
    print(f"\n--- Translation for: '{intent_1.text}' ---")
    for c in constraints_1:
        print(f"[{c.metric_name}] {c.operator} {c.value} {c.unit} (Confidence: {c.confidence})")

    # Example 2: Multi-Intent Profile Generation
    intent_list = [
        QualitativeIntent(text="Code needs to be very elegant and clean."),
        QualitativeIntent(text="Make the API response very fast."),
        QualitativeIntent(text="Ensure security is high.") 
    ]

    performance_profile = translator.generate_performance_profile(intent_list)
    
    print("\n--- Generated System Performance Profile ---")
    import json
    print(json.dumps(performance_profile, indent=2))