"""
Module: auto_symbiotic_entropy_core
A specialized cognitive component for processing "Human-Machine Symbiosis" interface entropy.
"""

import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SymbioticEntropyCore")


class FeedbackSentiment(Enum):
    """Enumeration of possible feedback sentiment types."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NOISY = "noisy"


class NodeStatus(Enum):
    """Status of a knowledge node in the cognitive graph."""
    ACTIVE = "active"
    DORMANT = "dormant"
    DEPRECATED = "deprecated"
    CANDIDATE = "candidate"


@dataclass
class FeedbackSignal:
    """
    Represents a raw feedback signal from the human operator.
    
    Attributes:
        content: The raw text or data payload of the feedback.
        biometric_data: Optional dictionary containing physiological signals (e.g., heart rate, skin conductance).
        timestamp: Time of feedback capture.
        context_id: Identifier for the operational context.
    """
    content: str
    biometric_data: Optional[Dict[str, float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    context_id: str = "default"

    def __post_init__(self):
        if not self.content:
            raise ValueError("Feedback content cannot be empty")


@dataclass
class KnowledgeNode:
    """
    Represents a unit of structured knowledge derived from feedback.
    
    Attributes:
        id: Unique identifier for the node.
        logical_kernel: The extracted logical core of the feedback.
        confidence: Current confidence score (0.0 to 1.0).
        status: Current status of the node.
        source_hash: Hash of the original feedback for traceability.
    """
    id: str
    logical_kernel: str
    confidence: float
    status: NodeStatus
    source_hash: str
    last_updated: datetime = field(default_factory=datetime.now)


class SymbioticEntropyCore:
    """
    Core cognitive component for handling high-entropy human feedback in a symbiotic system.
    
    This class processes noisy, unstructured, and emotional human feedback, extracts logical
    kernels via compression algorithms, and updates the system's knowledge graph.
    
    Attributes:
        knowledge_graph (Dict[str, KnowledgeNode]): The repository of validated knowledge nodes.
        noise_threshold (float): Threshold for biometric noise filtering.
        version (str): Version of the core logic.
    """

    def __init__(self, noise_threshold: float = 0.7, version: str = "1.0.0"):
        """
        Initialize the SymbioticEntropyCore.
        
        Args:
            noise_threshold: Threshold for filtering biometric noise (0.0-1.0).
            version: Version string of the core.
        """
        if not 0.0 <= noise_threshold <= 1.0:
            raise ValueError("Noise threshold must be between 0.0 and 1.0")
            
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.noise_threshold = noise_threshold
        self.version = version
        logger.info(f"SymbioticEntropyCore v{self.version} initialized with threshold {self.noise_threshold}")

    def _generate_id(self, content: str) -> str:
        """
        Generate a unique identifier based on content hash.
        
        Args:
            content: String content to hash.
            
        Returns:
            A unique hash string.
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

    def _analyze_sentiment(self, text: str) -> FeedbackSentiment:
        """
        Analyze the sentiment of the feedback text.
        
        Args:
            text: The feedback text.
            
        Returns:
            A FeedbackSentiment enum value.
        """
        text = text.lower()
        
        # Simple heuristic-based sentiment analysis
        negative_patterns = [
            r"根本没法用", r"垃圾", r"坏了", r"失败", r"错误", 
            r"terrible", r"broken", r"fail", r"error"
        ]
        positive_patterns = [
            r"很好", r"完美", r"解决", r"谢谢", r"优秀",
            r"good", r"great", r"perfect", r"thanks"
        ]
        
        for pattern in negative_patterns:
            if re.search(pattern, text):
                return FeedbackSentiment.NEGATIVE
                
        for pattern in positive_patterns:
            if re.search(pattern, text):
                return FeedbackSentiment.POSITIVE
                
        return FeedbackSentiment.NEUTRAL

    def _extract_logical_kernel(self, raw_text: str) -> str:
        """
        Extract the logical kernel from noisy feedback text.
        
        This function attempts to strip emotional language and extract the core issue.
        
        Args:
            raw_text: The raw feedback text.
            
        Returns:
            A cleaned string representing the logical core.
        """
        # Remove emotional intensifiers and noise
        noise_patterns = [
            r"该死[，。！]?", r"哎呀[，。！]?", r"天哪[，。！]?",
            r"damn[,.!]?", r"oh no[,.!]?", r"ugh[,.!]?"
        ]
        
        cleaned_text = raw_text
        for pattern in noise_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Extract action-object structures (simplified NLP)
        # Looking for patterns like "X is broken" or "Cannot do Y"
        logic_patterns = [
            r"([^，。！]+)不能工作",
            r"([^，。！]+)失败",
            r"无法([^，。！]+)",
            r"([^，。！]+)not working",
            r"cannot ([^,.!]+)"
        ]
        
        for pattern in logic_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                return f"ISSUE:{match.group(1).strip()}"
        
        # Fallback: return the cleaned text
        return cleaned_text.strip()

    def process_feedback(self, feedback: FeedbackSignal) -> Tuple[bool, Optional[KnowledgeNode]]:
        """
        Process a raw feedback signal and update the knowledge graph.
        
        This is the main entry point for handling human feedback. It performs:
        1. Biometric noise check
        2. Sentiment analysis
        3. Logical kernel extraction
        4. Knowledge graph update
        
        Args:
            feedback: A FeedbackSignal object containing the raw feedback.
            
        Returns:
            A tuple of (success: bool, node: Optional[KnowledgeNode]).
            
        Raises:
            ValueError: If feedback validation fails.
        """
        logger.info(f"Processing feedback from context: {feedback.context_id}")
        
        # Step 1: Biometric Noise Filter
        if feedback.biometric_data:
            stress_level = feedback.biometric_data.get('stress_level', 0.0)
            if stress_level > self.noise_threshold:
                logger.warning(f"Biometric noise detected (stress: {stress_level}). Flagging as NOISY.")
                # We still process but mark as noisy for lower confidence weighting
                sentiment = FeedbackSentiment.NOISY
            else:
                sentiment = self._analyze_sentiment(feedback.content)
        else:
            sentiment = self._analyze_sentiment(feedback.content)
        
        # Step 2: Extract Logical Kernel
        logical_kernel = self._extract_logical_kernel(feedback.content)
        if not logical_kernel:
            logger.error("Failed to extract logical kernel from feedback.")
            return False, None
            
        logger.info(f"Extracted kernel: '{logical_kernel}' with sentiment: {sentiment.value}")
        
        # Step 3: Create or Update Knowledge Node
        node_id = self._generate_id(logical_kernel)
        source_hash = self._generate_id(feedback.content)
        
        if node_id in self.knowledge_graph:
            # Update existing node
            node = self.knowledge_graph[node_id]
            adjustment = 0.1 if sentiment == FeedbackSentiment.POSITIVE else -0.1
            if sentiment == FeedbackSentiment.NOISY:
                adjustment *= 0.5  # Reduce impact of noisy feedback
                
            new_confidence = max(0.0, min(1.0, node.confidence + adjustment))
            node.confidence = new_confidence
            node.last_updated = datetime.now()
            logger.info(f"Updated node {node_id}. New confidence: {new_confidence:.2f}")
            return True, node
        else:
            # Create new node
            initial_confidence = 0.5
            if sentiment == FeedbackSentiment.POSITIVE:
                initial_confidence = 0.7
            elif sentiment == FeedbackSentiment.NEGATIVE:
                initial_confidence = 0.3
            elif sentiment == FeedbackSentiment.NOISY:
                initial_confidence = 0.2
                
            new_node = KnowledgeNode(
                id=node_id,
                logical_kernel=logical_kernel,
                confidence=initial_confidence,
                status=NodeStatus.CANDIDATE,
                source_hash=source_hash
            )
            self.knowledge_graph[node_id] = new_node
            logger.info(f"Created new node {node_id} with status CANDIDATE.")
            return True, new_node

    def consolidate_knowledge(self, confidence_threshold: float = 0.8) -> int:
        """
        Consolidate the knowledge graph by promoting high-confidence nodes.
        
        Nodes with confidence above the threshold are marked as ACTIVE.
        Nodes with very low confidence are marked as DEPRECATED.
        
        Args:
            confidence_threshold: The confidence level required to activate a node.
            
        Returns:
            The number of nodes modified.
        """
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
            
        modified_count = 0
        for node in self.knowledge_graph.values():
            if node.confidence >= confidence_threshold and node.status != NodeStatus.ACTIVE:
                node.status = NodeStatus.ACTIVE
                modified_count += 1
                logger.info(f"Node {node.id} promoted to ACTIVE.")
            elif node.confidence < 0.2 and node.status != NodeStatus.DEPRECATED:
                node.status = NodeStatus.DEPRECATED
                modified_count += 1
                logger.info(f"Node {node.id} demoted to DEPRECATED.")
                
        return modified_count

    def get_system_state(self) -> Dict[str, Any]:
        """
        Get the current state of the cognitive core.
        
        Returns:
            A dictionary containing system metrics.
        """
        active_count = sum(1 for n in self.knowledge_graph.values() if n.status == NodeStatus.ACTIVE)
        return {
            "version": self.version,
            "total_nodes": len(self.knowledge_graph),
            "active_nodes": active_count,
            "noise_threshold": self.noise_threshold,
            "last_update": max(
                (n.last_updated for n in self.knowledge_graph.values()),
                default=datetime.now()
            ).isoformat()
        }


# Usage Example
if __name__ == "__main__":
    # Initialize the core
    core = SymbioticEntropyCore(noise_threshold=0.75)
    
    # Simulate high-entropy feedback scenarios
    feedback_1 = FeedbackSignal(
        content="这该死的界面根本没法用！每次点击保存都会崩溃。",
        biometric_data={"heart_rate": 95, "stress_level": 0.8},
        context_id="ui_interaction_01"
    )
    
    feedback_2 = FeedbackSignal(
        content="Oh no, the export function is broken again.",
        biometric_data={"heart_rate": 70, "stress_level": 0.3},
        context_id="data_export_02"
    )
    
    feedback_3 = FeedbackSignal(
        content="自动保存功能很棒，帮我挽回了很多工作。",
        biometric_data={"heart_rate": 68, "stress_level": 0.1},
        context_id="ui_interaction_03"
    )

    # Process feedback
    print("\n--- Processing Feedback 1 ---")
    success, node_1 = core.process_feedback(feedback_1)
    if success and node_1:
        print(f"Processed Node: {node_1.logical_kernel}")
        print(f"Confidence: {node_1.confidence}")

    print("\n--- Processing Feedback 2 ---")
    success, node_2 = core.process_feedback(feedback_2)
    if success and node_2:
        print(f"Processed Node: {node_2.logical_kernel}")
        print(f"Confidence: {node_2.confidence}")
        
    print("\n--- Processing Feedback 3 ---")
    success, node_3 = core.process_feedback(feedback_3)
    if success and node_3:
        print(f"Processed Node: {node_3.logical_kernel}")
        print(f"Confidence: {node_3.confidence}")

    # Consolidate knowledge
    print("\n--- Consolidating Knowledge ---")
    changes = core.consolidate_knowledge(confidence_threshold=0.6)
    print(f"Total nodes modified: {changes}")
    
    # Display system state
    print("\n--- System State ---")
    print(core.get_system_state())