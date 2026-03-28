"""
Module: intent_parameterization_middleware.py

This module implements an 'Intent Parameterization Middleware' designed to convert
vague natural language inputs into structured JSON objects with constraint logic.
It leverages a simulated knowledge base of 2978 cognitive nodes (semantic anchors)
to ground the interpretation and identify missing parameters.

The middleware avoids hallucination by explicitly flagging missing information
and generating targeted clarification questions.

Author: Senior Python Engineer
Version: 1.0.0
Domain: nlp_interface
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Data Structures ---

COGNITIVE_NODES_COUNT = 2978

@dataclass
class CognitiveNode:
    """
    Represents a semantic anchor in the AGI knowledge graph.
    """
    node_id: str
    name: str
    category: str  # e.g., 'game', 'ui_component', 'logic'
    required_params: List[str]  # Parameters required to fulfill this intent
    constraints: Dict[str, Any]  # Validation rules for params

@dataclass
class ParameterizedIntent:
    """
    Structured output of the middleware.
    """
    raw_input: str
    detected_domain: Optional[str] = None
    confidence: float = 0.0
    extracted_parameters: Dict[str, Any] = field(default_factory=dict)
    missing_parameters: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    is_complete: bool = False
    error: Optional[str] = None

# --- Mock Knowledge Base (Simulation of 2978 Nodes) ---

class SemanticAnchorDB:
    """
    Simulates the interface to the AGI's 2978 cognitive nodes.
    In a real scenario, this would connect to a vector database or graph DB.
    """
    
    def __init__(self):
        # Hardcoding a few representative nodes for demonstration
        # Imagine these are selected from 2978 total nodes
        self._nodes: Dict[str, CognitiveNode] = {
            "node_game_snake": CognitiveNode(
                node_id="node_game_snake",
                name="Snake Game",
                category="arcade_game",
                required_params=["grid_size", "speed", "visual_theme"],
                constraints={"grid_size": {"min": 5, "max": 50}, "speed": {"min": 1, "max": 10}}
            ),
            "node_ui_dashboard": CognitiveNode(
                node_id="node_ui_dashboard",
                name="Admin Dashboard",
                category="web_interface",
                required_params=["color_scheme", "modules", "auth_level"],
                constraints={}
            )
        }
        logger.info(f"SemanticAnchorDB initialized with {COGNITIVE_NODES_COUNT} nodes (Simulated).")

    def semantic_search(self, query: str) -> Tuple[Optional[CognitiveNode], float]:
        """
        Finds the best matching cognitive node for a given query.
        """
        # Simplified NLP logic: keyword matching
        query = query.lower()
        
        if "贪吃蛇" in query or "snake" in query:
            return self._nodes["node_game_snake"], 0.95
        elif "仪表盘" in query or "dashboard" in query:
            return self._nodes["node_ui_dashboard"], 0.92
        else:
            return None, 0.0

# --- Core Middleware Class ---

class IntentParameterizer:
    """
    The core middleware class responsible for transforming unstructured text
    into structured intent using semantic anchors.
    """

    def __init__(self):
        self.db = SemanticAnchorDB()
        logger.info("IntentParameterizer Middleware initialized.")

    def _extract_known_params(self, text: str, anchor: CognitiveNode) -> Dict[str, Any]:
        """
        Helper function to extract explicit parameters from text based on the anchor context.
        """
        params = {}
        text = text.lower()

        # Regex or NLP extraction logic would go here
        if "grid_size" in anchor.required_params:
            match = re.search(r'(\d+)\s*(?:x|乘|by)\s*(\d+)', text)
            if match:
                params["grid_size"] = (int(match.group(1)), int(match.group(2)))
            elif "大" in text:
                params["grid_size"] = 20 # Default 'large'
            elif "小" in text:
                params["grid_size"] = 10 # Default 'small'

        if "visual_theme" in anchor.required_params:
            if "好玩" in text or "卡通" in text:
                params["visual_theme"] = "cartoon"
            elif "赛博" in text:
                params["visual_theme"] = "cyberpunk"
            elif "经典" in text:
                params["visual_theme"] = "classic"

        return params

    def _validate_constraints(self, params: Dict[str, Any], anchor: CognitiveNode) -> bool:
        """
        Validates extracted parameters against anchor constraints.
        """
        for key, value in params.items():
            if key in anchor.constraints:
                rules = anchor.constraints[key]
                if isinstance(value, tuple): # Handle tuple like grid size
                     if not (rules['min'] <= value[0] <= rules['max'] and rules['min'] <= value[1] <= rules['max']):
                         logger.warning(f"Parameter {key} value {value} out of bounds {rules}.")
                         return False
        return True

    def process_intent(self, natural_language_input: str) -> ParameterizedIntent:
        """
        Main entry point. Processes natural language and returns a structured object.
        
        Args:
            natural_language_input (str): The raw user input (e.g., "做一个好玩的贪吃蛇")
            
        Returns:
            ParameterizedIntent: The structured data object.
        """
        if not natural_language_input or not isinstance(natural_language_input, str):
            logger.error("Invalid input: Input must be a non-empty string.")
            return ParameterizedIntent(
                raw_input=str(natural_language_input),
                error="Invalid input type"
            )

        logger.info(f"Processing intent: {natural_language_input}")

        # 1. Semantic Anchoring
        best_anchor, confidence = self.db.semantic_search(natural_language_input)
        
        if not best_anchor:
            logger.warning("No semantic anchor found for input.")
            return ParameterizedIntent(
                raw_input=natural_language_input,
                confidence=0.0,
                missing_parameters=["*"], # Wildcard indicating total confusion
                clarification_questions=["抱歉，我不确定您想构建什么类型的应用。您能具体描述一下吗？"]
            )

        # 2. Parameter Extraction
        extracted = self._extract_known_params(natural_language_input, best_anchor)
        
        # 3. Gap Analysis (Identifying missing parameters)
        missing = [p for p in best_anchor.required_params if p not in extracted]
        
        # 4. Validation
        is_valid = self._validate_constraints(extracted, best_anchor)
        if not is_valid:
            # In a real system, we might try to correct the value or ask for re-input
            pass

        # 5. Generating Clarification Questions
        questions = []
        for param in missing:
            if param == "speed":
                questions.append("游戏速度应该多快？请选择 1 (慢) 到 10 (快)。")
            elif param == "grid_size":
                questions.append("地图网格需要多大？例如 10x10 或 20x20？")
            elif param == "visual_theme":
                questions.append("您偏好什么视觉风格？例如：经典、卡通或赛博朋克？")
            else:
                questions.append(f"请提供关于 '{param}' 的信息。")

        result = ParameterizedIntent(
            raw_input=natural_language_input,
            detected_domain=best_anchor.category,
            confidence=confidence,
            extracted_parameters=extracted,
            missing_parameters=missing,
            clarification_questions=questions,
            is_complete=(len(missing) == 0)
        )

        logger.info(f"Intent processed. Complete: {result.is_complete}. Missing: {missing}")
        return result

    def to_structured_json(self, intent: ParameterizedIntent) -> str:
        """
        Converts the ParameterizedIntent object into a JSON string suitable for downstream systems.
        """
        # Using dataclasses asdict recursively
        from dataclasses import asdict
        return json.dumps(asdict(intent), indent=2, ensure_ascii=False)

# --- Usage Example ---

def main():
    """
    Example usage of the IntentParameterizer middleware.
    """
    middleware = IntentParameterizer()
    
    # Example 1: Vague input (Missing params)
    input_text_1 = "做一个好玩的贪吃蛇"
    print(f"\n--- User Input: {input_text_1} ---")
    result_1 = middleware.process_intent(input_text_1)
    print(middleware.to_structured_json(result_1))
    
    # Example 2: Specific input
    input_text_2 = "做一个 15x15 的经典贪吃蛇，速度要快"
    print(f"\n--- User Input: {input_text_2} ---")
    result_2 = middleware.process_intent(input_text_2)
    print(middleware.to_structured_json(result_2))

    # Example 3: Unknown input
    input_text_3 = "帮我修一下自行车"
    print(f"\n--- User Input: {input_text_3} ---")
    result_3 = middleware.process_intent(input_text_3)
    print(middleware.to_structured_json(result_3))

if __name__ == "__main__":
    main()