"""
Intuition-Structure Bidirectional Transformer Module

This module implements an intent engine capable of parsing natural language
by integrating 'Practical Context' (Best Practices) to generate executable
business workflows.

Module Name: auto_intuition_structure_transformer
Author: Senior Python Engineer
Version: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Enumeration of task execution statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ActionNode:
    """Represents a single node in the executable business flow."""
    id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the node to a dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "metadata": self.metadata
        }


@dataclass
class IntentSchema:
    """Structured representation of a parsed user intent."""
    raw_input: str
    domain: str
    goal: str
    confidence: float
    action_nodes: List[ActionNode]
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serializes the schema to a JSON string."""
        return json.dumps({
            "raw_input": self.raw_input,
            "domain": self.domain,
            "goal": self.goal,
            "confidence": self.confidence,
            "constraints": self.constraints,
            "action_nodes": [node.to_dict() for node in self.action_nodes]
        }, indent=2, ensure_ascii=False)


class BestPracticeRegistry:
    """
    Repository for domain-specific best practices.
    In a real AGI system, this would interface with a knowledge graph or RAG system.
    """

    def __init__(self):
        self._practices: Dict[str, Dict[str, Any]] = {
            "report_generation": {
                "keywords": ["报告", "总结", "汇总", "搞一下"],
                "standard_procedure": [
                    {"name": "Data Collection", "desc": "Gather necessary data sources"},
                    {"name": "Drafting", "desc": "Create initial content structure"},
                    {"name": "Formatting", "desc": "Apply standard typesetting and styles"},
                    {"name": "Proofreading", "desc": "Check for errors and consistency"},
                    {"name": "Final Submission", "desc": "Send to stakeholders"}
                ]
            },
            "code_deployment": {
                "keywords": ["上线", "发版", "部署"],
                "standard_procedure": [
                    {"name": "Unit Testing", "desc": "Run automated test suites"},
                    {"name": "Code Review", "desc": "Peer review process"},
                    {"name": "Staging Deployment", "desc": "Deploy to staging environment"},
                    {"name": "Production Rollout", "desc": "Deploy to production"}
                ]
            }
        }

    def get_domain_procedure(self, domain_key: str) -> Optional[List[Dict[str, str]]]:
        """Retrieves the standard procedure for a specific domain."""
        logger.debug(f"Fetching procedure for domain: {domain_key}")
        return self._practices.get(domain_key, {}).get("standard_procedure")

    def detect_domain(self, text: str) -> Optional[str]:
        """Detects the relevant domain based on input text."""
        for domain, data in self._practices.items():
            for keyword in data.get("keywords", []):
                if keyword in text:
                    logger.info(f"Domain detected: {domain} based on keyword: {keyword}")
                    return domain
        return None


class IntuitionStructureTransformer:
    """
    Core Engine: Transforms fuzzy natural language into structured,
    executable business flows based on validated best practices.
    """

    def __init__(self):
        self.registry = BestPracticeRegistry()
        logger.info("IntuitionStructureTransformer initialized.")

    def _clean_input(self, text: str) -> str:
        """
        Helper function to sanitize and normalize user input.
        
        Args:
            text (str): Raw user input.
            
        Returns:
            str: Cleaned text.
        """
        if not text:
            return ""
        # Remove extra whitespace and normalize punctuation
        cleaned = re.sub(r'\s+', ' ', text).strip()
        logger.debug(f"Input cleaned: '{text}' -> '{cleaned}'")
        return cleaned

    def _map_actions_to_nodes(self, procedures: List[Dict[str, str]]) -> List[ActionNode]:
        """
        Converts a list of procedure dictionaries into ActionNode objects.
        
        Args:
            procedures (List[Dict]): List of procedure steps.
            
        Returns:
            List[ActionNode]: List of actionable nodes with dependency logic.
        """
        nodes = []
        prev_id = "start_trigger"
        
        for idx, step in enumerate(procedures):
            node_id = f"node_{idx}_{step['name'].lower().replace(' ', '_')}"
            
            # Business logic: Inject standard constraints
            node = ActionNode(
                id=node_id,
                name=step['name'],
                description=step['desc'],
                dependencies=[prev_id] if idx > 0 else [],
                metadata={"source": "best_practice_registry"}
            )
            nodes.append(node)
            prev_id = node_id
            
        return nodes

    def parse_fuzzy_intent(self, user_input: str) -> IntentSchema:
        """
        Main entry point for parsing ambiguous user instructions.
        
        Args:
            user_input (str): The fuzzy instruction (e.g., "搞一下报告").
            
        Returns:
            IntentSchema: The fully constructed executable schema.
            
        Raises:
            ValueError: If input is empty or domain cannot be resolved.
        """
        logger.info(f"Received input: {user_input}")
        
        # 1. Input Validation
        clean_text = self._clean_input(user_input)
        if not clean_text:
            logger.error("Empty input provided.")
            raise ValueError("Input cannot be empty")

        # 2. Domain Detection (Intuition Phase)
        domain = self.registry.detect_domain(clean_text)
        if not domain:
            logger.warning(f"No specific domain detected for: {clean_text}")
            domain = "general"
            # Fallback logic could be inserted here
        
        # 3. Structure Retrieval (Constraint Application)
        procedures = self.registry.get_domain_procedure(domain)
        
        if not procedures:
            logger.error(f"No procedures found for domain: {domain}")
            raise RuntimeError(f"Configuration error: No procedures for domain {domain}")

        # 4. Construction (Executable Flow Generation)
        action_nodes = self._map_actions_to_nodes(procedures)
        
        # 5. Schema Assembly
        schema = IntentSchema(
            raw_input=user_input,
            domain=domain,
            goal=f"Execute standard {domain.replace('_', ' ')} flow",
            confidence=0.95 if domain != "general" else 0.60,
            action_nodes=action_nodes,
            constraints={"requires_human_review": False, "strict_ordering": True}
        )
        
        logger.info(f"Successfully generated IntentSchema with {len(action_nodes)} nodes.")
        return schema


# --- Usage Example and Demonstration ---

def run_demo():
    """Demonstrates the capabilities of the IntuitionStructureTransformer."""
    transformer = IntuitionStructureTransformer()
    
    # Example 1: Fuzzy Report Request
    fuzzy_input = "帮我搞一下报告"
    
    try:
        print(f"\n--- Processing User Input: '{fuzzy_input}' ---")
        intent_schema = transformer.parse_fuzzy_intent(fuzzy_input)
        
        print("\nGenerated Executable JSON Flow:")
        print(intent_schema.to_json())
        
        print("\n--- Node Details ---")
        for node in intent_schema.action_nodes:
            print(f"Node: {node.name} | Deps: {node.dependencies}")
            
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)

if __name__ == "__main__":
    run_demo()