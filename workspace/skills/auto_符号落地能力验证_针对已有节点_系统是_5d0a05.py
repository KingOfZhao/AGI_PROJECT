"""
Module: auto_符号落地能力验证_针对已有节点_系统是_5d0a05

Description:
    This module validates the AGI system's ability to perform 'Symbol Grounding' 
    (符号落地). It specifically tests whether the system can decompose a high-level 
    abstract concept (e.g., 'Compound Interest') into a sequence of atomic, 
    physically executable instructions (Atomic Operational Instructions).
    
    Unlike abstract planning, this verification demands that the output instructions
    map to specific, real-world digital or physical actions (e.g., 'Click button X', 
    'Open App Y') rather than vague goals.

Author: AGI System Core Engineering
Version: 1.0.0
Domain: cognitive_science
"""

import logging
import json
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstructionType(Enum):
    """Classification of the atomic instruction types."""
    DIGITAL_INTERACTION = "digital_interaction"  # e.g., click, type, swipe
    PHYSICAL_ACTION = "physical_action"        # e.g., pick up, move to
    COGNITIVE_ACTION = "cognitive_action"      # e.g., verify, read (boundary case)
    SYSTEM_COMMAND = "system_command"          # e.g., run script, api call


@dataclass
class AtomicInstruction:
    """
    Represents a single, grounded atomic instruction.
    
    Attributes:
        step_id: The sequence order of the instruction.
        description: The concrete action description.
        type: The classification of the instruction.
        target_entity: The specific object or software involved (grounding target).
        executability_score: A float (0.0-1.0) estimating how directly executable this is.
    """
    step_id: int
    description: str
    type: InstructionType
    target_entity: str
    executability_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the object to a dictionary."""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "type": self.type.value,
            "target_entity": self.target_entity,
            "executability_score": self.executability_score
        }


class SymbolGroundingValidator:
    """
    Core class for validating the symbol grounding capability.
    
    It simulates the process of fetching atomic instructions from a knowledge base
    and validates if they meet the criteria for physical/executable reality.
    """

    def __init__(self, min_instructions: int = 5, min_executability: float = 0.7):
        """
        Initializes the validator.
        
        Args:
            min_instructions: Minimum number of steps required for a valid decomposition.
            min_executability: Threshold for considering a sequence 'executable'.
        """
        self.min_instructions = min_instructions
        self.min_executability = min_executability
        self._concept_library = self._initialize_mock_concept_library()
        logger.info("SymbolGroundingValidator initialized with min_steps=%d", min_instructions)

    @staticmethod
    def _initialize_mock_concept_library() -> Dict[str, List[Dict]]:
        """
        Helper: Mock database representing the AGI's Concept Library.
        In a real AGI, this would query a vector database or knowledge graph.
        """
        return {
            "复利效应": [
                {"desc": "解锁手机屏幕", "type": InstructionType.DIGITAL_INTERACTION, "target": "Mobile OS", "score": 0.99},
                {"desc": "打开银行APP", "type": InstructionType.DIGITAL_INTERACTION, "target": "Bank App", "score": 0.98},
                {"desc": "点击'理财'标签页", "type": InstructionType.DIGITAL_INTERACTION, "target": "UI Button", "score": 0.95},
                {"desc": "选择'基金定投'产品", "type": InstructionType.DIGITAL_INTERACTION, "target": "List Item", "score": 0.92},
                {"desc": "设置扣款周期为'每周'", "type": InstructionType.DIGITAL_INTERACTION, "target": "Dropdown", "score": 0.90},
                {"desc": "开启'红利转投'开关", "type": InstructionType.DIGITAL_INTERACTION, "target": "Toggle Switch", "score": 0.95},
                {"desc": "输入交易密码", "type": InstructionType.DIGITAL_INTERACTION, "target": "Input Field", "score": 0.98},
                {"desc": "点击'确认'按钮", "type": InstructionType.DIGITAL_INTERACTION, "target": "Button", "score": 0.99},
            ],
            "番茄工作法": [
                {"desc": "拿起计时器", "type": InstructionType.PHYSICAL_ACTION, "target": "Timer", "score": 0.95},
                {"desc": "旋转至25分钟刻度", "type": InstructionType.PHYSICAL_ACTION, "target": "Timer Dial", "score": 0.90},
                {"desc": "坐下并打开笔记本", "type": InstructionType.PHYSICAL_ACTION, "target": "Notebook", "score": 0.94},
            ]
        }

    def _fetch_atomic_instructions(self, concept_name: str) -> Optional[List[AtomicInstruction]]:
        """
        Core Function 1: Retrieves and constructs atomic instructions from the concept library.
        
        Simulates the 'Extraction' phase of the AGI system.
        
        Args:
            concept_name: The high-level concept to query.
            
        Returns:
            A list of AtomicInstruction objects or None if concept not found.
        """
        logger.debug(f"Attempting to fetch instructions for concept: {concept_name}")
        raw_data = self._concept_library.get(concept_name)

        if not raw_data:
            logger.error(f"Concept '{concept_name}' not found in library.")
            return None

        instructions = []
        try:
            for idx, item in enumerate(raw_data):
                instruction = AtomicInstruction(
                    step_id=idx + 1,
                    description=item.get("desc"),
                    type=item.get("type"),
                    target_entity=item.get("target"),
                    executability_score=item.get("score", 0.0)
                )
                instructions.append(instruction)
        except Exception as e:
            logger.exception("Failed to parse raw instruction data.")
            return None

        return instructions

    def validate_grounding_quality(self, concept_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Core Function 2: Validates the grounding quality of the extracted instructions.
        
        It checks:
        1. Quantity: Are there enough steps?
        2. Specificity: Are the instructions concrete (validated via score)?
        3. Connectivity: Do they map to specific entities?
        
        Args:
            concept_name: The concept to validate.
            
        Returns:
            A tuple (is_valid: bool, report: dict).
        """
        logger.info(f"Starting validation for: {concept_name}")
        
        # Step 1: Extraction
        instructions = self._fetch_atomic_instructions(concept_name)
        
        if instructions is None:
            return False, {"error": "Concept extraction failed", "concept": concept_name}

        # Step 2: Validation Checks
        count = len(instructions)
        avg_score = sum(inst.executability_score for inst in instructions) / count if count > 0 else 0
        
        # Check constraints
        is_count_valid = count >= self.min_instructions
        is_score_valid = avg_score >= self.min_executability
        
        # Check for abstract terms (heuristic)
        abstract_keywords = ["consider", "understand", "think about", "strategy"]
        has_abstract = any(
            any(kw in inst.description.lower() for kw in abstract_keywords) 
            for inst in instructions
        )

        final_valid = is_count_valid and is_score_valid and not has_abstract

        # Construct Report
        report = {
            "concept": concept_name,
            "validation_passed": final_valid,
            "metrics": {
                "instruction_count": count,
                "min_required": self.min_instructions,
                "avg_executability": round(avg_score, 3),
                "contains_abstract_elements": has_abstract
            },
            "decomposed_steps": [inst.to_dict() for inst in instructions]
        }

        if not final_valid:
            logger.warning(f"Validation failed for '{concept_name}'. Count: {count}, Score: {avg_score}")
        else:
            logger.info(f"Validation succeeded for '{concept_name}'.")

        return final_valid, report


def format_report_output(report: Dict[str, Any]) -> str:
    """
    Auxiliary Function: Formats the validation report into a readable JSON string.
    
    Args:
        report: The dictionary report from the validator.
        
    Returns:
        A formatted JSON string.
    """
    try:
        return json.dumps(report, indent=4, ensure_ascii=False)
    except TypeError as e:
        logger.error(f"Serialization error: {e}")
        return "{}"


# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Initialize the system
    validator = SymbolGroundingValidator(min_instructions=5)
    
    # Case 1: Valid Concept (Compound Interest)
    concept_1 = "复利效应"
    is_valid_1, report_1 = validator.validate_grounding_quality(concept_1)
    print(f"Concept: {concept_1} | Valid: {is_valid_1}")
    print(format_report_output(report_1))
    
    print("-" * 60)

    # Case 2: Invalid Concept (Too few steps / Incomplete)
    concept_2 = "番茄工作法"
    is_valid_2, report_2 = validator.validate_grounding_quality(concept_2)
    print(f"Concept: {concept_2} | Valid: {is_valid_2}")
    print(format_report_output(report_2))

    print("-" * 60)

    # Case 3: Non-existent Concept
    concept_3 = "量子纠缠通讯" # Not in mock library
    is_valid_3, report_3 = validator.validate_grounding_quality(concept_3)
    print(f"Concept: {concept_3} | Valid: {is_valid_3}")
    print(format_report_output(report_3))