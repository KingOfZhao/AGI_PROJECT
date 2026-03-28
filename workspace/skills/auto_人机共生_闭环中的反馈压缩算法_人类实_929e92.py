"""
Module: auto_人机共生_闭环中的反馈压缩算法_人类实_929e92
Description: Implements a noise-resilient feedback compression algorithm for AGI-Human Symbiosis.
             Transforms high-entropy, unstructured human feedback into structured, low-entropy
             'Truth Nodes' (e.g., Anti-patterns) and integrates them into the system's knowledge
             graph without disrupting existing weight balances (catastrophic forgetting prevention).
Author: Senior Python Engineer
License: MIT
"""

import logging
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class FeedbackEntry:
    """Represents raw, potentially noisy feedback from a human user."""
    user_id: str
    raw_content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context_tags: List[str] = field(default_factory=list)

@dataclass
class TruthNode:
    """Represents a compressed, structured concept derived from feedback."""
    node_id: str
    canonical_name: str  # e.g., 'UI_交互_反模式_001'
    compressed_data: Dict[str, Any]  # The distilled insight
    weight: float = 1.0
    source_hash: str = ""
    connections: Dict[str, float] = field(default_factory=dict) # node_id -> weight

@dataclass
class KnowledgeGraph:
    """Simulates the AGI's existing knowledge network."""
    nodes: Dict[str, TruthNode] = field(default_factory=dict)
    stability_threshold: float = 0.05

# --- Core Algorithm Class ---

class SymbioticFeedbackCompression:
    """
    Implements the 'Human-in-the-loop' Feedback Compression Algorithm.
    
    Workflow:
    1. Ingest high-noise feedback.
    2. Semantic Cleaning & Feature Extraction (Compression).
    3. Crystallization into a TruthNode.
    4. Conservative Integration (Inverse Node Patching) to maintain weight balance.
    """

    def __init__(self, knowledge_graph: KnowledgeGraph, compression_rate: float = 0.3):
        """
        Initialize the algorithm.
        
        Args:
            knowledge_graph: The existing network of concepts.
            compression_rate: Aggressiveness of semantic compression (0.0 to 1.0).
        """
        if not (0.0 <= compression_rate <= 1.0):
            raise ValueError("Compression rate must be between 0.0 and 1.0.")
        
        self.graph = knowledge_graph
        self.compression_rate = compression_rate
        logger.info("SymbioticFeedbackCompression initialized with graph size: %d", len(self.graph.nodes))

    def _clean_noise(self, text: str) -> Tuple[str, List[str]]:
        """
        [Helper] Removes stop words, profanity, and normalizes text to extract core signals.
        
        Args:
            text: Raw input string.
            
        Returns:
            A tuple of (cleaned_text, extracted_keywords).
        """
        if not isinstance(text, str):
            raise TypeError("Input text must be a string.")
            
        # Basic noise filtering (simulated)
        noise_patterns = [
            r'\b(stupid|damn|useless|garbage|crap|idiot)\b', # Profanity/Frustration
            r'\b(really|very|extremely|basically|literally)\b', # Intensifiers
            r'[^\w\s]' # Punctuation
        ]
        
        cleaned = text.lower()
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Keyword extraction (Mock logic: take nouns/verbs or specific terms)
        # In production, this would use an NLP model (e.g., spaCy/BERT)
        keywords = [w for w in cleaned.split() if len(w) > 3]
        
        logger.debug("Cleaned '%s' to '%s' with keywords %s", text[:20], cleaned[:20], keywords)
        return cleaned, keywords

    def compress_feedback(self, feedback: FeedbackEntry) -> Optional[TruthNode]:
        """
        [Core 1] Compresses raw feedback into a structured TruthNode.
        
        This function acts as the 'semantic black hole', collapsing high-entropy
        information into a dense state.
        
        Args:
            feedback: The raw FeedbackEntry object.
            
        Returns:
            A crystallized TruthNode or None if feedback is empty.
        """
        try:
            if not feedback.raw_content:
                logger.warning("Empty feedback content received.")
                return None

            # 1. Denoise
            cleaned_text, keywords = self._clean_noise(feedback.raw_content)
            
            if not keywords:
                return None

            # 2. Generate Identity (Crystallization)
            # Create a deterministic ID based on content to avoid duplicates
            content_hash = hashlib.md5(cleaned_text.encode()).hexdigest()[:8]
            
            # 3. Canonical Naming
            # Map keywords to a system-readable category (Mock logic)
            category = "General_Issue"
            if "ui" in keywords or "interface" in keywords:
                category = "UI_Interaction_Antipattern"
            elif "logic" in keywords or "result" in keywords:
                category = "Logic_Error"
            
            node_name = f"{category}_{content_hash}"
            
            # 4. Structure the Data
            compressed_data = {
                "original_sentiment": feedback.raw_content,
                "core_issues": keywords,
                "frequency": 1,
                "first_seen": feedback.timestamp
            }
            
            new_node = TruthNode(
                node_id=f"node_{content_hash}",
                canonical_name=node_name,
                compressed_data=compressed_data,
                source_hash=content_hash,
                weight=0.1 # Initial weak weight
            )
            
            logger.info("Compressed feedback into node: %s", node_name)
            return new_node

        except Exception as e:
            logger.error("Error during compression: %s", e, exc_info=True)
            return None

    def integrate_node_safely(self, new_node: TruthNode, target_connections: List[str]) -> bool:
        """
        [Core 2] Integrates the new node into the network without disrupting weight balance.
        
        Implements 'Inverse Node Patching' or 'Elastic Weight Consolidation' concept:
        - If a connection exists, dampen the update.
        - If new, initialize with low weight.
        - Renormalize local subgraph to prevent explosion.
        
        Args:
            new_node: The TruthNode to integrate.
            target_connections: List of existing node IDs to connect this new node to.
            
        Returns:
            True if integration successful, False otherwise.
        """
        if new_node.node_id in self.graph.nodes:
            logger.warning("Node %s already exists. Updating frequency.", new_node.node_id)
            self.graph.nodes[new_node.node_id].compressed_data["frequency"] += 1
            return True

        try:
            # 1. Add Node to Graph
            self.graph.nodes[new_node.node_id] = new_node
            
            # 2. Establish Connections with Weight Balancing
            valid_connections = 0
            for t_id in target_connections:
                if t_id not in self.graph.nodes:
                    logger.warning("Target node %s not found. Skipping connection.", t_id)
                    continue
                
                valid_connections += 1
                
                # Calculate new edge weight (Inverse scaling)
                # If existing node has high degree, we contribute less weight to avoid dilution
                target_node = self.graph.nodes[t_id]
                existing_degree = len(target_node.connections)
                
                # Damping factor based on existing connectivity
                dampener = 1.0 / (1.0 + existing_degree * self.compression_rate)
                edge_weight = new_node.weight * dampener
                
                # Bidirectional connection
                new_node.connections[t_id] = edge_weight
                target_node.connections[new_node.node_id] = edge_weight
                
                logger.debug("Connected %s <-> %s with weight %.4f", 
                             new_node.canonical_name, t_id, edge_weight)

            if valid_connections == 0:
                logger.error("Integration failed: No valid targets found for node %s", new_node.node_id)
                # Rollback
                del self.graph.nodes[new_node.node_id]
                return False

            # 3. Local Renormalization (Prevent weight explosion)
            self._local_renormalize(new_node.node_id)
            
            logger.info("Successfully integrated node %s into network.", new_node.canonical_name)
            return True

        except Exception as e:
            logger.error("Critical error during node integration: %s", e, exc_info=True)
            return False

    def _local_renormalize(self, node_id: str):
        """
        [Helper] Renormalizes the weights of the connected component to sum to 1.0 (or avg const).
        """
        if node_id not in self.graph.nodes:
            return
            
        node = self.graph.nodes[node_id]
        total_weight = sum(node.connections.values())
        
        if total_weight > 1.0: # Threshold check
            scale = 1.0 / total_weight
            for k in node.connections:
                node.connections[k] *= scale
                # Update reverse link proportionally? 
                # For this skill, we keep it simple to demonstrate the concept.
                
            logger.debug("Renormalized weights for node %s", node_id)

# --- Usage Example ---

def main():
    """
    Example Usage of the Symbiotic Feedback Compression Algorithm.
    """
    print("--- Initializing System ---")
    
    # 1. Setup existing Knowledge Graph
    graph = KnowledgeGraph()
    # Add some dummy existing nodes
    node_ui = TruthNode(node_id="ui_base", canonical_name="UI_Core_Component", weight=1.0)
    node_logic = TruthNode(node_id="logic_base", canonical_name="Logic_Core_Component", weight=1.0)
    graph.nodes = {node_ui.node_id: node_ui, node_logic.node_id: node_logic}
    
    # 2. Initialize Algorithm
    compressor = SymbioticFeedbackCompression(graph, compression_rate=0.5)
    
    # 3. Simulate Human Feedback (High Noise)
    raw_feedback_1 = "This damn UI button is useless! It just doesn't work when I click it."
    feedback_entry = FeedbackEntry(
        user_id="user_123",
        raw_content=raw_feedback_1,
        context_tags=["interface", "button_click"]
    )
    
    print(f"\n[Input] Raw Feedback: '{raw_feedback_1}'")
    
    # 4. Compress Feedback
    compressed_node = compressor.compress_feedback(feedback_entry)
    
    if compressed_node:
        print(f"[Process] Compressed to Node: {compressed_node.canonical_name}")
        print(f"[Process] Extracted Keywords: {compressed_node.compressed_data['core_issues']}")
        
        # 5. Integrate into Network
        # We assume the context tags hint at where to connect, or we use the 'ui_base' key
        success = compressor.integrate_node_safely(compressed_node, target_connections=["ui_base"])
        
        if success:
            print(f"[Result] Node integrated. Total nodes: {len(graph.nodes)}")
            print(f"[Result] New connections for 'UI_Core_Component': {graph.nodes['ui_base'].connections}")
        else:
            print("[Result] Integration failed.")
            
    # 6. Simulate Logic Error
    raw_feedback_2 = "The result is completely stupid logic error garbage."
    feedback_entry_2 = FeedbackEntry(user_id="user_456", raw_content=raw_feedback_2)
    print(f"\n[Input] Raw Feedback: '{raw_feedback_2}'")
    
    node_2 = compressor.compress_feedback(feedback_entry_2)
    if node_2:
        print(f"[Process] Compressed to Node: {node_2.canonical_name}")
        compressor.integrate_node_safely(node_2, target_connections=["logic_base"])

if __name__ == "__main__":
    main()