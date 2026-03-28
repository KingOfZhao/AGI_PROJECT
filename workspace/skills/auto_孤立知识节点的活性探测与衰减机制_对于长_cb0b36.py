"""
Module: dormant_knowledge_prober.py

This module implements a mechanism to detect dormant (isolated) knowledge nodes,
generate probing questions for human verification, and handle the decay or
archival of outdated information.

It addresses the "knowledge corruption" problem where static knowledge becomes
obsolete over time if not reinforced by interaction or reasoning.

Key Components:
- DormancyDetector: Identifies nodes based on inactivity timestamps.
- ProbingEngine: Generates natural language questions based on node context.
- FeedbackProcessor: Handles user responses to trigger validation or deletion.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeStatus(Enum):
    """Enumeration of possible states for a knowledge node."""
    ACTIVE = "active"
    DORMANT = "dormant"
    ARCHIVED = "archived"
    DISPROVED = "disproved"


@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the graph.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge text or data.
        category: Domain of the knowledge (e.g., 'python', 'cooking').
        last_accessed: Timestamp of the last interaction or inference usage.
        creation_date: Timestamp of creation.
        status: Current lifecycle status of the node.
        access_count: Number of times accessed.
    """
    id: str
    content: str
    category: str
    last_accessed: datetime.datetime
    creation_date: datetime.datetime = field(default_factory=datetime.datetime.now)
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    access_count: int = 0


class KnowledgeBaseEmulator:
    """
    A mock class to simulate a Knowledge Graph database.
    In a real AGI system, this would interface with Vector DBs or Graph DBs.
    """
    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}

    def add_node(self, node: KnowledgeNode):
        self._nodes[node.id] = node

    def get_all_nodes(self) -> List[KnowledgeNode]:
        return list(self._nodes.values())


def calculate_dormancy_score(
    node: KnowledgeNode, 
    current_time: datetime.datetime,
    decay_factor: float = 0.1
) -> float:
    """
    Auxiliary Function: Calculates a dormancy score based on time decay.
    
    The score increases as the time since last access grows.
    
    Args:
        node: The knowledge node to evaluate.
        current_time: The reference current time.
        decay_factor: Rate at which knowledge 'rots'.
        
    Returns:
        float: A score representing the likelihood of being obsolete.
    """
    delta = current_time - node.last_accessed
    days_inactive = delta.total_seconds() / 86400
    
    # Simple exponential decay model for score calculation
    # Higher score = more likely to be dormant
    score = 1 - (1 / (1 + (days_inactive * decay_factor)))
    return score


def detect_dormant_nodes(
    knowledge_base: KnowledgeBaseEmulator,
    threshold_days: int = 90,
    min_access_count: int = 1
) -> List[KnowledgeNode]:
    """
    Core Function 1: Scans the knowledge base to find isolated or inactive nodes.
    
    It filters nodes that haven't been accessed recently and have low interaction counts.
    
    Args:
        knowledge_base: The database interface containing nodes.
        threshold_days: Number of days of inactivity to consider a node dormant.
        min_access_count: Minimum interactions to consider a node 'established' 
                          (low count + old = likely irrelevant).
        
    Returns:
        List[KnowledgeNode]: A list of nodes suspected to be obsolete.
    """
    logger.info(f"Starting dormancy scan with threshold {threshold_days} days...")
    dormant_nodes = []
    current_time = datetime.datetime.now()
    
    try:
        nodes = knowledge_base.get_all_nodes()
        if not nodes:
            logger.warning("Knowledge base is empty.")
            return []

        for node in nodes:
            # Skip already archived or disproved nodes
            if node.status in [KnowledgeStatus.ARCHIVED, KnowledgeStatus.DISPROVED]:
                continue

            delta = current_time - node.last_accessed
            days_inactive = delta.days
            
            # Logic: Old and rarely used, or very old regardless of use
            if days_inactive > threshold_days:
                logger.debug(f"Node {node.id} identified as dormant (Inactive: {days_inactive} days).")
                node.status = KnowledgeStatus.DORMANT
                dormant_nodes.append(node)
                
    except Exception as e:
        logger.error(f"Error during dormancy detection: {str(e)}", exc_info=True)
        raise

    logger.info(f"Detection complete. Found {len(dormant_nodes)} dormant nodes.")
    return dormant_nodes


def generate_probing_questions(dormant_nodes: List[KnowledgeNode]) -> Dict[str, str]:
    """
    Core Function 2: Generates questions for human verification.
    
    Creates contextual questions based on the content of the dormant nodes.
    
    Args:
        dormant_nodes: List of nodes targeted for verification.
        
    Returns:
        Dict[str, str]: A mapping of Node ID to the generated Question string.
    """
    logger.info("Generating probing questions for dormant nodes...")
    questions_map = {}
    
    if not dormant_nodes:
        return questions_map

    for node in dormant_nodes:
        try:
            # Input Validation
            if not node.content or not isinstance(node.content, str):
                logger.warning(f"Node {node.id} has invalid content. Skipping.")
                continue

            # Template-based Question Generation
            # In a real AGI system, an LLM would generate this contextually.
            if "config" in node.category.lower():
                question = (
                    f"The system holds configuration knowledge: '{node.content}'. "
                    f"This hasn't been used in { (datetime.datetime.now() - node.last_accessed).days } days. "
                    f"Is this configuration still valid?"
                )
            else:
                question = (
                    f"Do you still consider the following knowledge relevant? "
                    f"'{node.content}' (Category: {node.category})"
                )
            
            questions_map[node.id] = question
            logger.debug(f"Generated question for Node {node.id}")
            
        except Exception as e:
            logger.error(f"Failed to generate question for node {node.id}: {e}")
            continue

    return questions_map


def handle_user_feedback(
    node: KnowledgeNode, 
    is_valid: bool, 
    reason: Optional[str] = None
) -> None:
    """
    Core Function 3 (Extension): Updates the node status based on user feedback.
    
    Implements the 'Falsification' logic.
    
    Args:
        node: The node being evaluated.
        is_valid: Boolean indicating if the user confirmed the knowledge is correct.
        reason: Optional reason for invalidation.
    """
    try:
        if is_valid:
            # Reinforce knowledge: Reset timer and status
            node.last_accessed = datetime.datetime.now()
            node.status = KnowledgeStatus.ACTIVE
            node.access_count += 1
            logger.info(f"Node {node.id} reinforced. Status set to ACTIVE.")
        else:
            # Trigger Falsification
            node.status = KnowledgeStatus.DISPROVED
            logger.info(f"Node {node.id} falsified by user. Reason: {reason or 'N/A'}. Marked for deletion/archiving.")
            
    except Exception as e:
        logger.error(f"Failed to update node {node.id} status: {e}")


# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    # 1. Setup Mock Knowledge Base
    kb = KnowledgeBaseEmulator()
    
    # 2. Create Sample Data
    # Node 1: Active knowledge (recently accessed)
    kb.add_node(KnowledgeNode(
        id="k_001", 
        content="The capital of France is Paris.", 
        category="geography",
        last_accessed=datetime.datetime.now() - datetime.timedelta(days=1)
    ))
    
    # Node 2: Dormant knowledge (Config info, 100 days old)
    kb.add_node(KnowledgeNode(
        id="k_002", 
        content="API Endpoint is http://old-service.example.com/v1", 
        category="config",
        last_accessed=datetime.datetime.now() - datetime.timedelta(days=100)
    ))
    
    # Node 3: Dormant knowledge (General info, 200 days old)
    kb.add_node(KnowledgeNode(
        id="k_003", 
        content="Python 3.8 is the latest version.", # Outdated fact
        category="tech",
        last_accessed=datetime.datetime.now() - datetime.timedelta(days=200)
    ))

    # 3. Run Detection
    print("--- Step 1: Detecting Dormant Nodes ---")
    dormant_list = detect_dormant_nodes(kb, threshold_days=90)
    
    # 4. Generate Probing Questions
    print("\n--- Step 2: Generating Probing Questions ---")
    questions = generate_probing_questions(dormant_list)
    
    for nid, q in questions.items():
        print(f"[ASK HUMAN] Node {nid}: {q}")

    # 5. Simulate Feedback Handling
    print("\n--- Step 3: Simulating Feedback Loop ---")
    # Simulate user saying 'k_002' is still valid
    node_k2 = next(n for n in kb.get_all_nodes() if n.id == "k_002")
    handle_user_feedback(node_k2, is_valid=True)
    
    # Simulate user saying 'k_003' is outdated
    node_k3 = next(n for n in kb.get_all_nodes() if n.id == "k_003")
    handle_user_feedback(node_k3, is_valid=False, reason="Python 3.12 is out")
    
    print("\nFinal State of Nodes:")
    for n in kb.get_all_nodes():
        print(f"ID: {n.id} | Status: {n.status.value} | Last Used: {n.last_accessed.strftime('%Y-%m-%d')}")