"""
Human-AI Interaction Protocol for Hypothesis Validation

This module implements a protocol that enables human experts to efficiently
validate or falsify AI-generated operational hypotheses through minimal
feedback mechanisms (corrections/confirmations).

The protocol is designed to:
1. Present AI hypotheses to human experts
2. Collect minimal feedback (confirm/correct/reject)
3. Track confidence scores and learning progression
4. Solidify validated knowledge as new nodes

Author: AGI System
Version: 1.0.0
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hci_protocol.log')
    ]
)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Enumeration of possible feedback types from human experts."""
    CONFIRM = auto()      # Expert confirms the hypothesis
    CORRECT = auto()      # Expert provides a correction
    REJECT = auto()       # Expert rejects the hypothesis
    UNCERTAIN = auto()    # Expert is uncertain, needs more info


class HypothesisStatus(Enum):
    """Enumeration of hypothesis validation states."""
    PENDING = auto()      # Awaiting expert feedback
    VALIDATED = auto()    # Confirmed by expert
    CORRECTED = auto()    # Modified by expert
    REJECTED = auto()     # Rejected by expert
    CONSOLIDATED = auto() # Converted to knowledge node


@dataclass
class Hypothesis:
    """
    Represents an AI-generated operational hypothesis.
    
    Attributes:
        hypothesis_id: Unique identifier for the hypothesis
        content: The actual hypothesis content/description
        confidence: AI's confidence score (0.0 to 1.0)
        domain: Knowledge domain the hypothesis belongs to
        context: Additional context information
        created_at: Timestamp of hypothesis creation
        status: Current validation status
        feedback_count: Number of feedback rounds received
    """
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    confidence: float = 0.5
    domain: str = "general"
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: HypothesisStatus = HypothesisStatus.PENDING
    feedback_count: int = 0
    
    def __post_init__(self):
        """Validate data after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate hypothesis data integrity."""
        if not isinstance(self.content, str) or len(self.content.strip()) == 0:
            raise ValueError("Hypothesis content must be a non-empty string")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if not isinstance(self.domain, str) or len(self.domain.strip()) == 0:
            raise ValueError("Domain must be a non-empty string")


@dataclass
class ExpertFeedback:
    """
    Represents feedback from a human expert.
    
    Attributes:
        feedback_id: Unique identifier for the feedback
        hypothesis_id: ID of the hypothesis being evaluated
        feedback_type: Type of feedback (confirm/correct/reject)
        correction_content: Corrected content if feedback_type is CORRECT
        expert_confidence: Expert's confidence in their feedback
        rationale: Optional explanation for the feedback
        timestamp: When the feedback was given
        expert_id: Identifier for the expert (anonymized)
    """
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str = ""
    feedback_type: FeedbackType = FeedbackType.UNCERTAIN
    correction_content: Optional[str] = None
    expert_confidence: float = 0.5
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    expert_id: str = "anonymous"
    
    def __post_init__(self):
        """Validate feedback data."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate feedback data integrity."""
        if self.feedback_type == FeedbackType.CORRECT:
            if not self.correction_content or len(self.correction_content.strip()) == 0:
                raise ValueError("Correction content required when feedback type is CORRECT")
        
        if not 0.0 <= self.expert_confidence <= 1.0:
            raise ValueError(f"Expert confidence must be between 0.0 and 1.0")


@dataclass
class KnowledgeNode:
    """
    Represents a consolidated knowledge node created from validated hypotheses.
    
    Attributes:
        node_id: Unique identifier for the knowledge node
        content: The validated knowledge content
        source_hypothesis_id: ID of the original hypothesis
        validation_rounds: Number of feedback rounds before consolidation
        confidence_score: Final confidence score after validation
        created_at: Timestamp of node creation
        domain: Knowledge domain
        metadata: Additional metadata
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    source_hypothesis_id: str = ""
    validation_rounds: int = 0
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    domain: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)


class HCIProtocol:
    """
    Main protocol class for Human-Computer Interaction in hypothesis validation.
    
    This class manages the entire lifecycle of hypothesis validation:
    - Hypothesis submission and tracking
    - Expert feedback collection and processing
    - Knowledge consolidation from validated hypotheses
    - Protocol state management and persistence
    
    Example:
        >>> protocol = HCIProtocol()
        >>> hypothesis = protocol.submit_hypothesis(
        ...     content="The optimal temperature for this reaction is 75°C",
        ...     confidence=0.72,
        ...     domain="chemistry"
        ... )
        >>> feedback = ExpertFeedback(
        ...     hypothesis_id=hypothesis.hypothesis_id,
        ...     feedback_type=FeedbackType.CORRECT,
        ...     correction_content="The optimal temperature is actually 82°C",
        ...     expert_confidence=0.95
        ... )
        >>> result = protocol.process_feedback(feedback)
        >>> print(result.status)
        HypothesisStatus.CORRECTED
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the HCI Protocol.
        
        Args:
            storage_path: Optional path for persistent storage
        """
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.feedback_history: Dict[str, List[ExpertFeedback]] = {}
        self.knowledge_nodes: Dict[str, KnowledgeNode] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        
        # Statistics tracking
        self.stats = {
            'total_hypotheses': 0,
            'validated': 0,
            'corrected': 0,
            'rejected': 0,
            'consolidated': 0,
            'avg_feedback_rounds': 0.0
        }
        
        logger.info("HCI Protocol initialized successfully")
        
        if self.storage_path and self.storage_path.exists():
            self._load_state()
    
    def submit_hypothesis(
        self,
        content: str,
        confidence: float,
        domain: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Hypothesis:
        """
        Submit a new AI-generated hypothesis for validation.
        
        Args:
            content: The hypothesis content/description
            confidence: AI's confidence score (0.0 to 1.0)
            domain: Knowledge domain
            context: Optional additional context
            
        Returns:
            The created Hypothesis object
            
        Raises:
            ValueError: If input validation fails
        """
        try:
            hypothesis = Hypothesis(
                content=content,
                confidence=confidence,
                domain=domain,
                context=context or {}
            )
            
            self.hypotheses[hypothesis.hypothesis_id] = hypothesis
            self.feedback_history[hypothesis.hypothesis_id] = []
            
            self.stats['total_hypotheses'] += 1
            
            logger.info(
                f"Submitted hypothesis {hypothesis.hypothesis_id[:8]}... "
                f"in domain '{domain}' with confidence {confidence:.2f}"
            )
            
            return hypothesis
            
        except Exception as e:
            logger.error(f"Failed to submit hypothesis: {e}")
            raise
    
    def process_feedback(
        self,
        feedback: ExpertFeedback,
        auto_consolidate: bool = True,
        consolidation_threshold: float = 0.85
    ) -> Union[Hypothesis, KnowledgeNode]:
        """
        Process expert feedback and update hypothesis status.
        
        This is a core function that handles the minimal feedback loop:
        1. Validates the feedback
        2. Updates hypothesis status based on feedback type
        3. Recalculates confidence scores
        4. Optionally consolidates validated hypotheses into knowledge nodes
        
        Args:
            feedback: The expert feedback to process
            auto_consolidate: Whether to automatically create knowledge nodes
            consolidation_threshold: Confidence threshold for auto-consolidation
            
        Returns:
            Updated Hypothesis or newly created KnowledgeNode
            
        Raises:
            ValueError: If hypothesis_id is invalid
            KeyError: If hypothesis doesn't exist
        """
        if feedback.hypothesis_id not in self.hypotheses:
            error_msg = f"Hypothesis {feedback.hypothesis_id} not found"
            logger.error(error_msg)
            raise KeyError(error_msg)
        
        hypothesis = self.hypotheses[feedback.hypothesis_id]
        
        try:
            # Store feedback
            self.feedback_history[feedback.hypothesis_id].append(feedback)
            hypothesis.feedback_count += 1
            
            # Update hypothesis based on feedback type
            if feedback.feedback_type == FeedbackType.CONFIRM:
                hypothesis.status = HypothesisStatus.VALIDATED
                hypothesis.confidence = self._calculate_updated_confidence(
                    hypothesis.confidence,
                    feedback.expert_confidence,
                    positive=True
                )
                self.stats['validated'] += 1
                logger.info(
                    f"Hypothesis {feedback.hypothesis_id[:8]}... CONFIRMED "
                    f"(new confidence: {hypothesis.confidence:.2f})"
                )
                
            elif feedback.feedback_type == FeedbackType.CORRECT:
                hypothesis.status = HypothesisStatus.CORRECTED
                original_content = hypothesis.content
                hypothesis.content = feedback.correction_content
                hypothesis.confidence = self._calculate_updated_confidence(
                    hypothesis.confidence,
                    feedback.expert_confidence,
                    positive=True
                )
                self.stats['corrected'] += 1
                logger.info(
                    f"Hypothesis {feedback.hypothesis_id[:8]}... CORRECTED "
                    f"(from '{original_content[:30]}...' to '{feedback.correction_content[:30]}...')"
                )
                
            elif feedback.feedback_type == FeedbackType.REJECT:
                hypothesis.status = HypothesisStatus.REJECTED
                hypothesis.confidence = 0.0
                self.stats['rejected'] += 1
                logger.info(f"Hypothesis {feedback.hypothesis_id[:8]}... REJECTED")
                
            elif feedback.feedback_type == FeedbackType.UNCERTAIN:
                # Keep pending but log the uncertainty
                logger.info(
                    f"Hypothesis {feedback.hypothesis_id[:8]}... received UNCERTAIN feedback"
                )
            
            # Check for consolidation
            if auto_consolidate and hypothesis.confidence >= consolidation_threshold:
                if hypothesis.status in [HypothesisStatus.VALIDATED, HypothesisStatus.CORRECTED]:
                    return self._consolidate_to_knowledge_node(hypothesis)
            
            self._update_stats()
            
            if self.storage_path:
                self._save_state()
            
            return hypothesis
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            raise
    
    def _calculate_updated_confidence(
        self,
        current_confidence: float,
        expert_confidence: float,
        positive: bool = True
    ) -> float:
        """
        Calculate updated confidence score using Bayesian-like update.
        
        This helper function combines AI confidence with expert confidence
        to produce an updated confidence score.
        
        Args:
            current_confidence: Current hypothesis confidence
            expert_confidence: Expert's confidence in their feedback
            positive: Whether the feedback was positive (confirm/correct)
            
        Returns:
            Updated confidence score (0.0 to 1.0)
        """
        if positive:
            # Weighted combination favoring expert input
            alpha = 0.6  # Expert weight
            updated = (alpha * expert_confidence) + ((1 - alpha) * current_confidence)
            # Apply slight boost for positive feedback
            updated = min(1.0, updated * 1.05)
        else:
            # Significant reduction for negative feedback
            updated = current_confidence * 0.3
        
        return round(max(0.0, min(1.0, updated)), 3)
    
    def _consolidate_to_knowledge_node(self, hypothesis: Hypothesis) -> KnowledgeNode:
        """
        Convert a validated hypothesis into a permanent knowledge node.
        
        Args:
            hypothesis: The hypothesis to consolidate
            
        Returns:
            The created KnowledgeNode
        """
        knowledge_node = KnowledgeNode(
            content=hypothesis.content,
            source_hypothesis_id=hypothesis.hypothesis_id,
            validation_rounds=hypothesis.feedback_count,
            confidence_score=hypothesis.confidence,
            domain=hypothesis.domain,
            metadata={
                'original_context': hypothesis.context,
                'consolidation_time': datetime.now().isoformat()
            }
        )
        
        self.knowledge_nodes[knowledge_node.node_id] = knowledge_node
        hypothesis.status = HypothesisStatus.CONSOLIDATED
        self.stats['consolidated'] += 1
        
        logger.info(
            f"Consolidated hypothesis {hypothesis.hypothesis_id[:8]}... "
            f"to knowledge node {knowledge_node.node_id[:8]}..."
        )
        
        return knowledge_node
    
    def _update_stats(self) -> None:
        """Update protocol statistics."""
        if self.stats['total_hypotheses'] > 0:
            total_rounds = sum(
                h.feedback_count for h in self.hypotheses.values()
            )
            self.stats['avg_feedback_rounds'] = round(
                total_rounds / self.stats['total_hypotheses'], 2
            )
    
    def get_pending_hypotheses(self, domain: Optional[str] = None) -> List[Hypothesis]:
        """
        Retrieve all hypotheses pending validation.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of pending hypotheses
        """
        pending = [
            h for h in self.hypotheses.values()
            if h.status == HypothesisStatus.PENDING
        ]
        
        if domain:
            pending = [h for h in pending if h.domain == domain]
        
        return pending
    
    def get_knowledge_base(self, domain: Optional[str] = None) -> List[KnowledgeNode]:
        """
        Retrieve consolidated knowledge nodes.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of knowledge nodes
        """
        nodes = list(self.knowledge_nodes.values())
        
        if domain:
            nodes = [n for n in nodes if n.domain == domain]
        
        return nodes
    
    def export_protocol_state(self) -> Dict[str, Any]:
        """
        Export the current protocol state as a dictionary.
        
        Returns:
            Dictionary containing all protocol data
        """
        return {
            'hypotheses': {
                hid: {
                    'hypothesis_id': h.hypothesis_id,
                    'content': h.content,
                    'confidence': h.confidence,
                    'domain': h.domain,
                    'context': h.context,
                    'created_at': h.created_at.isoformat(),
                    'status': h.status.name,
                    'feedback_count': h.feedback_count
                }
                for hid, h in self.hypotheses.items()
            },
            'knowledge_nodes': {
                nid: {
                    'node_id': n.node_id,
                    'content': n.content,
                    'source_hypothesis_id': n.source_hypothesis_id,
                    'validation_rounds': n.validation_rounds,
                    'confidence_score': n.confidence_score,
                    'domain': n.domain,
                    'created_at': n.created_at.isoformat()
                }
                for nid, n in self.knowledge_nodes.items()
            },
            'statistics': self.stats,
            'export_timestamp': datetime.now().isoformat()
        }
    
    def _save_state(self) -> None:
        """Save protocol state to storage."""
        if not self.storage_path:
            return
        
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.export_protocol_state(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _load_state(self) -> None:
        """Load protocol state from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Restore hypotheses
            for hid, h_data in data.get('hypotheses', {}).items():
                hypothesis = Hypothesis(
                    hypothesis_id=h_data['hypothesis_id'],
                    content=h_data['content'],
                    confidence=h_data['confidence'],
                    domain=h_data['domain'],
                    context=h_data.get('context', {}),
                    created_at=datetime.fromisoformat(h_data['created_at']),
                    status=HypothesisStatus[h_data['status']],
                    feedback_count=h_data['feedback_count']
                )
                self.hypotheses[hid] = hypothesis
                self.feedback_history[hid] = []
            
            # Restore knowledge nodes
            for nid, n_data in data.get('knowledge_nodes', {}).items():
                node = KnowledgeNode(
                    node_id=n_data['node_id'],
                    content=n_data['content'],
                    source_hypothesis_id=n_data['source_hypothesis_id'],
                    validation_rounds=n_data['validation_rounds'],
                    confidence_score=n_data['confidence_score'],
                    domain=n_data['domain'],
                    created_at=datetime.fromisoformat(n_data['created_at'])
                )
                self.knowledge_nodes[nid] = node
            
            # Restore stats
            self.stats = data.get('statistics', self.stats)
            
            logger.info(f"Loaded state from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")


def demo_protocol():
    """
    Demonstration of the HCI Protocol usage.
    
    This function shows a complete workflow:
    1. Creating the protocol instance
    2. Submitting AI hypotheses
    3. Processing expert feedback
    4. Consolidating knowledge
    """
    print("=" * 60)
    print("HCI Protocol Demonstration")
    print("=" * 60)
    
    # Initialize protocol
    protocol = HCIProtocol()
    
    # Submit AI hypotheses
    h1 = protocol.submit_hypothesis(
        content="The system should use caching for database queries",
        confidence=0.75,
        domain="software_architecture",
        context={"module": "data_access", "performance_tier": "critical"}
    )
    print(f"\n[1] Submitted Hypothesis: {h1.hypothesis_id[:8]}...")
    print(f"    Content: {h1.content}")
    print(f"    Confidence: {h1.confidence}")
    
    h2 = protocol.submit_hypothesis(
        content="API rate limiting should be set to 1000 req/min",
        confidence=0.65,
        domain="api_design"
    )
    print(f"\n[2] Submitted Hypothesis: {h2.hypothesis_id[:8]}...")
    print(f"    Content: {h2.content}")
    print(f"    Confidence: {h2.confidence}")
    
    # Process confirm feedback
    feedback1 = ExpertFeedback(
        hypothesis_id=h1.hypothesis_id,
        feedback_type=FeedbackType.CONFIRM,
        expert_confidence=0.95,
        rationale="Confirmed through load testing"
    )
    result1 = protocol.process_feedback(feedback1)
    print(f"\n[3] Processed CONFIRM feedback for {h1.hypothesis_id[:8]}...")
    print(f"    New Status: {result1.status.name}")
    print(f"    New Confidence: {result1.confidence}")
    
    # Process correction feedback
    feedback2 = ExpertFeedback(
        hypothesis_id=h2.hypothesis_id,
        feedback_type=FeedbackType.CORRECT,
        correction_content="API rate limiting should be set to 500 req/min for stability",
        expert_confidence=0.90
    )
    result2 = protocol.process_feedback(feedback2)
    print(f"\n[4] Processed CORRECT feedback for {h2.hypothesis_id[:8]}...")
    print(f"    New Status: {result2.status.name}")
    print(f"    Corrected Content: {result2.content}")
    print(f"    New Confidence: {result2.confidence}")
    
    # Display final statistics
    print("\n" + "=" * 60)
    print("Protocol Statistics:")
    print("=" * 60)
    for key, value in protocol.stats.items():
        print(f"  {key}: {value}")
    
    # Show knowledge base
    print("\n" + "=" * 60)
    print("Consolidated Knowledge Nodes:")
    print("=" * 60)
    for node in protocol.get_knowledge_base():
        print(f"  [{node.domain}] {node.content}")
        print(f"    Confidence: {node.confidence_score}")
        print(f"    Validation Rounds: {node.validation_rounds}")
        print()


if __name__ == "__main__":
    demo_protocol()