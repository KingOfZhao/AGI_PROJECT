"""
Module: auto_static_intent_refinement
Description: Implements Static Analysis Guided Intent Refinement.
This module utilizes a simulated 'Prior Knowledge Base' of existing skill nodes
to perform static analysis on user intents. It identifies missing parameters
by referencing skill signatures and generates prompts to guide the user for
completion (Bottom-Up Inductive Completion).
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentRefiner")

@dataclass
class SkillNode:
    """
    Represents a single node in the Skill Knowledge Base.
    
    Attributes:
        id: Unique identifier for the skill.
        name: Human-readable name of the skill.
        keywords: List of keywords associated with this skill for retrieval.
        required_params: Dictionary of required parameters and their expected types/formats.
        description: Detailed description of what the skill does.
    """
    id: str
    name: str
    keywords: List[str]
    required_params: Dict[str, str]
    description: str = ""

@dataclass
class UserIntent:
    """
    Represents the user's input intent.
    
    Attributes:
        query: The raw natural language input.
        provided_params: Parameters currently provided by the user.
        confidence: Confidence score of the intent parsing (0.0 to 1.0).
    """
    query: str
    provided_params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

class StaticIntentRefiner:
    """
    Core class for refining user intents using a static knowledge base.
    
    This class loads existing skill nodes (simulating the 1575 skill nodes)
    and uses them to validate user requests. If a request maps to a skill
    but lacks necessary parameters, it statically determines what is missing
    and prompts the user.
    """

    def __init__(self, skill_knowledge_base: List[SkillNode]):
        """
        Initialize the refiner with a knowledge base.
        
        Args:
            skill_knowledge_base: A list of SkillNode objects acting as prior knowledge.
        """
        if not skill_knowledge_base:
            logger.warning("Initialized with empty knowledge base.")
        self.knowledge_base = skill_knowledge_base
        logger.info(f"StaticIntentRefiner initialized with {len(skill_knowledge_base)} skills.")

    def _preprocess_query(self, text: str) -> Set[str]:
        """
        [Helper] Normalizes and tokenizes the input query.
        
        Args:
            text: Raw input string.
            
        Returns:
            A set of normalized tokens.
        """
        # Basic cleaning: lowercase and remove non-alphanumeric
        clean_text = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff\s]', '', text.lower())
        tokens = set(clean_text.split())
        logger.debug(f"Query '{text}' tokenized to {tokens}")
        return tokens

    def retrieve_relevant_skills(self, intent: UserIntent) -> List[Tuple[SkillNode, float]]:
        """
        Core Function 1: Retrieves and ranks skills based on static keyword matching.
        
        This acts as the retrieval mechanism against the 'Prior Knowledge Base'.
        
        Args:
            intent: The UserIntent object containing the query.
            
        Returns:
            A list of tuples (SkillNode, relevance_score), sorted by relevance.
        """
        query_tokens = self._preprocess_query(intent.query)
        if not query_tokens:
            return []

        scored_skills = []
        
        for skill in self.knowledge_base:
            skill_keywords = set(k.lower() for k in skill.keywords)
            # Calculate Jaccard similarity / Intersection score
            intersection = query_tokens.intersection(skill_keywords)
            if intersection:
                score = len(intersection) / len(skill_keywords) # Simple relevance metric
                scored_skills.append((skill, score))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        
        if scored_skills:
            logger.info(f"Retrieved {len(scored_skills)} potential skills. Top: {scored_skills[0][0].name}")
        
        return scored_skills

    def refine_intent_parameters(self, intent: UserIntent, top_n: int = 1) -> Dict[str, Any]:
        """
        Core Function 2: Analyzes missing parameters and generates refinement prompts.
        
        This function performs the 'Static Analysis'. It compares the user's
        provided parameters with the requirements of the most likely skill.
        
        Args:
            intent: The current UserIntent state.
            top_n: Number of top candidate skills to consider for analysis.
            
        Returns:
            A dictionary containing:
            - 'status': 'complete' or 'needs_info'
            - 'target_skill': The SkillNode identified.
            - 'missing_params': List of missing parameter keys.
            - 'prompt': Generated question for the user.
            - 'analysis_details': Debug info.
        """
        candidates = self.retrieve_relevant_skills(intent)
        
        if not candidates:
            return {
                "status": "error",
                "message": "No matching skills found in knowledge base."
            }

        # Analyze the best candidate
        best_skill, score = candidates[0]
        
        logger.info(f"Analyzing intent against Skill: '{best_skill.name}' (Score: {score:.2f})")

        # Static Analysis: Find missing keys
        required_keys = set(best_skill.required_params.keys())
        provided_keys = set(intent.provided_params.keys())
        
        missing_keys = required_keys - provided_keys
        
        if not missing_keys:
            logger.info("Intent fully refined. All parameters present.")
            return {
                "status": "complete",
                "target_skill": best_skill.name,
                "prompt": None,
                "missing_params": []
            }
        
        # Generate Prompt (Bottom-Up Inductive Completion)
        missing_key = list(missing_keys)[0] # Prioritize the first missing param for simplicity
        expected_type = best_skill.required_params[missing_key]
        
        prompt = (
            f"To perform '{best_skill.name}', I need more specific information. "
            f"Could you please provide the '{missing_key}' (expected: {expected_type})?"
        )
        
        logger.warning(f"Intent incomplete. Missing: {missing_keys}")
        
        return {
            "status": "needs_info",
            "target_skill": best_skill.name,
            "missing_params": list(missing_keys),
            "prompt": prompt,
            "analysis_details": {
                "matched_score": score,
                "skill_id": best_skill.id
            }
        }

# --- Data Setup and Usage Example ---

def load_mock_knowledge_base() -> List[SkillNode]:
    """
    Helper to generate a mock knowledge base simulating the '1575 skill nodes'.
    """
    return [
        SkillNode(
            id="sk_101",
            name="Data Visualization",
            keywords=["data", "chart", "plot", "visualization", "graph"],
            required_params={"data_source": "csv/database", "chart_type": "string"},
            description="Generates charts from data sources."
        ),
        SkillNode(
            id="sk_205",
            name="System Health Check",
            keywords=["system", "status", "health", "check", "diagnostics"],
            required_params={"target_ip": "ip_address", "depth": "integer"},
            description="Checks the health of a remote system."
        ),
        SkillNode(
            id="sk_310",
            name="Text Summarization",
            keywords=["text", "summarize", "summary", "nlp", "condense"],
            required_params={"text_body": "string", "max_length": "integer"},
            description="Summarizes long text."
        )
    ]

if __name__ == "__main__":
    # 1. Initialize System
    mock_skills = load_mock_knowledge_base()
    refiner = StaticIntentRefiner(mock_skills)

    # 2. Simulate User Input (Intent with missing params)
    # User wants to do something with data, implies 'Data Visualization'
    raw_intent = UserIntent(
        query="Please visualize the sales data",
        provided_params={"chart_type": "bar"} # User specified chart, but not source
    )

    # 3. Run Refinement Loop
    print(f"\n> User Query: {raw_intent.query}")
    print(f"> Provided Params: {raw_intent.provided_params}")

    result = refiner.refine_intent_parameters(raw_intent)

    # 4. Output Results
    print("\n--- Refinement Result ---")
    print(f"Status: {result['status']}")
    print(f"Matched Skill: {result.get('target_skill', 'N/A')}")
    
    if result['status'] == 'needs_info':
        print(f"Missing Parameters: {result['missing_params']}")
        print(f"System Prompt: {result['prompt']}")