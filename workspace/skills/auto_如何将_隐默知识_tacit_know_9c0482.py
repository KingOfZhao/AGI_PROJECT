"""
Module: auto_如何将_隐默知识_tacit_know_9c0482
Description: Mechanism for decomposing tacit knowledge into atomic, verifiable skills.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeNodeType(Enum):
    """Enumeration of knowledge node types."""
    ATOMIC = "atomic"          # Fully decomposed, testable skill
    COMPOSITE = "composite"    # Decomposable into sub-skills
    BLACKBOX = "blackbox"      # Cannot be decomposed with current methods


class ModalityType(Enum):
    """Types of input modalities for analysis."""
    VIDEO = "video"
    AUDIO = "audio"
    SENSOR = "sensor"
    TEXT = "text"
    TACTILE = "tactile"


@dataclass
class AtomicSkill:
    """Represents a verifiable atomic skill extracted from tacit knowledge."""
    skill_id: str
    name: str
    modality: ModalityType
    test_procedure: str
    success_criteria: str
    confidence_score: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Confidence score must be between 0 and 1, got {self.confidence_score}")


@dataclass
class KnowledgeNode:
    """Represents a node in the tacit knowledge decomposition graph."""
    node_id: str
    description: str
    node_type: KnowledgeNodeType
    modalities: List[ModalityType]
    atomic_skills: List[AtomicSkill] = field(default_factory=list)
    children: List['KnowledgeNode'] = field(default_factory=list)
    parent_id: Optional[str] = None
    decomposition_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TacitKnowledgeDecomposer:
    """
    Core engine for decomposing tacit knowledge into verifiable atomic skills.
    
    This class implements a recursive decomposition algorithm that attempts to
    break down implicit knowledge into testable components based on available
    modalities and decomposition strategies.
    
    Example:
        >>> decomposer = TacitKnowledgeDecomposer()
        >>> node = decomposer.create_root_node(
        ...     "Street vendor customer assessment intuition",
        ...     [ModalityType.VIDEO, ModalityType.AUDIO]
        ... )
        >>> result = decomposer.decompose_node(node)
    """
    
    MAX_DECOMPOSITION_DEPTH = 5
    MIN_CONFIDENCE_THRESHOLD = 0.3
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize the decomposer.
        
        Args:
            confidence_threshold: Minimum confidence to consider a skill as atomic.
        """
        self.confidence_threshold = confidence_threshold
        self._node_registry: Dict[str, KnowledgeNode] = {}
        self._decomposition_strategies = self._initialize_strategies()
        logger.info(f"TacitKnowledgeDecomposer initialized with threshold {confidence_threshold}")
    
    def _initialize_strategies(self) -> Dict[str, Any]:
        """Initialize decomposition strategies for different modalities."""
        return {
            "video": self._decompose_video_input,
            "audio": self._decompose_audio_input,
            "sensor": self._decompose_sensor_input,
            "text": self._decompose_text_input,
            "tactile": self._decompose_tactile_input
        }
    
    def create_root_node(
        self,
        description: str,
        modalities: List[ModalityType],
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeNode:
        """
        Create a root knowledge node from a tacit knowledge description.
        
        Args:
            description: Human-readable description of the tacit knowledge.
            modalities: List of available input modalities for analysis.
            metadata: Optional additional metadata.
            
        Returns:
            KnowledgeNode: The created root node.
            
        Raises:
            ValueError: If description is empty or modalities list is empty.
        """
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")
        if not modalities:
            raise ValueError("At least one modality must be specified")
        
        node_id = str(uuid.uuid4())
        node = KnowledgeNode(
            node_id=node_id,
            description=description.strip(),
            node_type=KnowledgeNodeType.COMPOSITE,
            modalities=modalities,
            metadata=metadata or {}
        )
        
        self._node_registry[node_id] = node
        logger.info(f"Created root node {node_id}: {description[:50]}...")
        return node
    
    def decompose_node(
        self,
        node: KnowledgeNode,
        depth: int = 0
    ) -> Tuple[KnowledgeNodeType, List[AtomicSkill]]:
        """
        Attempt to decompose a knowledge node into atomic skills.
        
        This is the core decomposition function that recursively tries to break
        down tacit knowledge into verifiable components.
        
        Args:
            node: The knowledge node to decompose.
            depth: Current recursion depth (used internally).
            
        Returns:
            Tuple containing the final node type and list of extracted atomic skills.
            
        Raises:
            RuntimeError: If maximum decomposition depth is exceeded.
        """
        if depth > self.MAX_DECOMPOSITION_DEPTH:
            logger.warning(f"Max decomposition depth reached for node {node.node_id}")
            node.node_type = KnowledgeNodeType.BLACKBOX
            return (KnowledgeNodeType.BLACKBOX, [])
        
        node.decomposition_attempts += 1
        logger.info(f"Decomposing node {node.node_id} (attempt {node.decomposition_attempts}, depth {depth})")
        
        extracted_skills: List[AtomicSkill] = []
        total_confidence = 0.0
        
        # Try each available modality
        for modality in node.modalities:
            strategy_name = modality.value
            if strategy_name in self._decomposition_strategies:
                try:
                    skills = self._decomposition_strategies[strategy_name](node)
                    extracted_skills.extend(skills)
                    total_confidence += sum(s.confidence_score for s in skills) / max(len(skills), 1)
                except Exception as e:
                    logger.error(f"Decomposition failed for modality {strategy_name}: {e}")
                    continue
        
        # Evaluate decomposition success
        if not extracted_skills:
            node.node_type = KnowledgeNodeType.BLACKBOX
            logger.warning(f"Node {node.node_id} marked as BLACKBOX - no skills extracted")
            return (KnowledgeNodeType.BLACKBOX, [])
        
        avg_confidence = total_confidence / len(node.modalities)
        
        if avg_confidence >= self.confidence_threshold:
            node.atomic_skills = extracted_skills
            node.node_type = KnowledgeNodeType.ATOMIC
            logger.info(f"Node {node.node_id} decomposed to ATOMIC with {len(extracted_skills)} skills")
            return (KnowledgeNodeType.ATOMIC, extracted_skills)
        else:
            # Try further decomposition
            node.node_type = KnowledgeNodeType.COMPOSITE
            return self._attempt_recursive_decomposition(node, depth)
    
    def _decompose_video_input(self, node: KnowledgeNode) -> List[AtomicSkill]:
        """
        Decompose knowledge based on video input modality.
        
        Analyzes visual patterns and attempts to identify atomic visual skills.
        """
        skills = []
        
        # Micro-expression recognition
        skills.append(AtomicSkill(
            skill_id=f"{node.node_id}_video_microexp",
            name="Micro-expression Recognition",
            modality=ModalityType.VIDEO,
            test_procedure="Present video frames with known expressions; measure recognition accuracy",
            success_criteria=">=85% accuracy on test set within 200ms per frame",
            confidence_score=0.78,
            dependencies=[]
        ))
        
        # Body language analysis
        skills.append(AtomicSkill(
            skill_id=f"{node.node_id}_video_bodylang",
            name="Body Language Pattern Analysis",
            modality=ModalityType.VIDEO,
            test_procedure="Analyze posture sequences; classify engagement levels",
            success_criteria="Correlation >= 0.7 with expert assessments",
            confidence_score=0.65,
            dependencies=[f"{node.node_id}_video_microexp"]
        ))
        
        logger.debug(f"Extracted {len(skills)} video-based skills for node {node.node_id}")
        return skills
    
    def _decompose_audio_input(self, node: KnowledgeNode) -> List[AtomicSkill]:
        """
        Decompose knowledge based on audio input modality.
        
        Analyzes vocal patterns and speech characteristics.
        """
        skills = []
        
        # Tone analysis
        skills.append(AtomicSkill(
            skill_id=f"{node.node_id}_audio_tone",
            name="Vocal Tone Analysis",
            modality=ModalityType.AUDIO,
            test_procedure="Process audio samples; classify emotional tone",
            success_criteria="F1 score >= 0.8 on emotion classification",
            confidence_score=0.72,
            dependencies=[]
        ))
        
        # Speech pace analysis
        skills.append(AtomicSkill(
            skill_id=f"{node.node_id}_audio_pace",
            name="Speech Pace Pattern Recognition",
            modality=ModalityType.AUDIO,
            test_procedure="Measure speech rate variations; correlate with urgency",
            success_criteria="Pearson correlation >= 0.6 with labeled urgency",
            confidence_score=0.58,
            dependencies=[]
        ))
        
        logger.debug(f"Extracted {len(skills)} audio-based skills for node {node.node_id}")
        return skills
    
    def _decompose_sensor_input(self, node: KnowledgeNode) -> List[AtomicSkill]:
        """Decompose knowledge based on sensor data input."""
        # Placeholder for sensor-based decomposition
        logger.debug(f"Sensor decomposition not yet implemented for node {node.node_id}")
        return []
    
    def _decompose_text_input(self, node: KnowledgeNode) -> List[AtomicSkill]:
        """Decompose knowledge based on text input modality."""
        skills = []
        
        skills.append(AtomicSkill(
            skill_id=f"{node.node_id}_text_sentiment",
            name="Text Sentiment Analysis",
            modality=ModalityType.TEXT,
            test_procedure="Analyze text samples; classify sentiment polarity",
            success_criteria="Accuracy >= 90% on benchmark dataset",
            confidence_score=0.85,
            dependencies=[]
        ))
        
        return skills
    
    def _decompose_tactile_input(self, node: KnowledgeNode) -> List[AtomicSkill]:
        """Decompose knowledge based on tactile/haptic input."""
        logger.debug(f"Tactile decomposition not yet implemented for node {node.node_id}")
        return []
    
    def _attempt_recursive_decomposition(
        self,
        node: KnowledgeNode,
        current_depth: int
    ) -> Tuple[KnowledgeNodeType, List[AtomicSkill]]:
        """
        Attempt to recursively decompose a composite node.
        
        Args:
            node: The composite node to further decompose.
            current_depth: Current recursion depth.
            
        Returns:
            Tuple of final node type and extracted skills.
        """
        # Create sub-nodes based on identified skill clusters
        sub_descriptions = self._identify_sub_clusters(node)
        
        if not sub_descriptions:
            node.node_type = KnowledgeNodeType.BLACKBOX
            return (KnowledgeNodeType.BLACKBOX, [])
        
        all_skills: List[AtomicSkill] = []
        all_atomic = True
        
        for desc, modalities in sub_descriptions:
            sub_node = KnowledgeNode(
                node_id=str(uuid.uuid4()),
                description=desc,
                node_type=KnowledgeNodeType.COMPOSITE,
                modalities=modalities,
                parent_id=node.node_id
            )
            self._node_registry[sub_node.node_id] = sub_node
            node.children.append(sub_node)
            
            sub_type, sub_skills = self.decompose_node(sub_node, current_depth + 1)
            all_skills.extend(sub_skills)
            
            if sub_type != KnowledgeNodeType.ATOMIC:
                all_atomic = False
        
        if all_atomic and all_skills:
            node.atomic_skills = all_skills
            node.node_type = KnowledgeNodeType.ATOMIC
            return (KnowledgeNodeType.ATOMIC, all_skills)
        
        return (node.node_type, all_skills)
    
    def _identify_sub_clusters(
        self,
        node: KnowledgeNode
    ) -> List[Tuple[str, List[ModalityType]]]:
        """
        Identify potential sub-clusters for recursive decomposition.
        
        Uses heuristics to suggest how a complex skill might be broken down.
        """
        # Simple heuristic-based clustering
        clusters = []
        
        if "customer" in node.description.lower() or "人" in node.description:
            clusters.append((
                "Customer demographic assessment",
                [ModalityType.VIDEO, ModalityType.SENSOR]
            ))
            clusters.append((
                "Customer intent recognition",
                [ModalityType.VIDEO, ModalityType.AUDIO]
            ))
        
        if "price" in node.description.lower() or "菜" in node.description:
            clusters.append((
                "Price sensitivity estimation",
                [ModalityType.VIDEO, ModalityType.AUDIO]
            ))
        
        if not clusters:
            clusters.append((
                f"Sub-component of: {node.description[:30]}",
                node.modalities[:1] if node.modalities else [ModalityType.VIDEO]
            ))
        
        return clusters
    
    def export_decomposition_graph(self, format: str = "dict") -> Union[Dict[str, Any], str]:
        """
        Export the decomposition graph for external use.
        
        Args:
            format: Output format - 'dict' or 'json'.
            
        Returns:
            Serialized representation of the decomposition graph.
        """
        graph_data = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "total_nodes": len(self._node_registry),
                "export_timestamp": str(uuid.uuid1())
            }
        }
        
        for node_id, node in self._node_registry.items():
            node_data = {
                "id": node.node_id,
                "description": node.description,
                "type": node.node_type.value,
                "modalities": [m.value for m in node.modalities],
                "skills_count": len(node.atomic_skills),
                "parent_id": node.parent_id
            }
            graph_data["nodes"].append(node_data)
            
            if node.parent_id:
                graph_data["edges"].append({
                    "source": node.parent_id,
                    "target": node.node_id,
                    "type": "decomposes_to"
                })
        
        if format == "json":
            return json.dumps(graph_data, indent=2, ensure_ascii=False)
        return graph_data
    
    def get_node_by_id(self, node_id: str) -> Optional[KnowledgeNode]:
        """Retrieve a node from the registry by its ID."""
        return self._node_registry.get(node_id)


def validate_input_data(data: Dict[str, Any]) -> bool:
    """
    Validate input data structure for knowledge decomposition.
    
    Args:
        data: Dictionary containing input specification.
        
    Returns:
        bool: True if valid, raises exception otherwise.
        
    Raises:
        KeyError: If required fields are missing.
        ValueError: If field values are invalid.
    """
    required_fields = ["description", "modalities"]
    
    for field in required_fields:
        if field not in data:
            raise KeyError(f"Required field '{field}' missing from input data")
    
    if not isinstance(data["description"], str) or len(data["description"]) < 10:
        raise ValueError("Description must be a string with at least 10 characters")
    
    if not isinstance(data["modalities"], list) or len(data["modalities"]) == 0:
        raise ValueError("Modalities must be a non-empty list")
    
    valid_modalities = {m.value for m in ModalityType}
    for mod in data["modalities"]:
        if mod not in valid_modalities:
            raise ValueError(f"Invalid modality '{mod}'. Valid options: {valid_modalities}")
    
    logger.debug("Input data validation passed")
    return True


# Example usage and demonstration
if __name__ == "__main__":
    """
    Example: Decomposing a street vendor's tacit knowledge about customer assessment.
    
    Input format:
    {
        "description": "Detailed description of the tacit knowledge",
        "modalities": ["video", "audio", "sensor"],
        "metadata": {"context": "street vending", "expertise_level": "master"}
    }
    
    Output format:
    {
        "node_type": "atomic|composite|blackbox",
        "atomic_skills": [
            {
                "skill_id": "...",
                "name": "...",
                "test_procedure": "...",
                "success_criteria": "..."
            }
        ]
    }
    """
    
    # Initialize the decomposer
    decomposer = TacitKnowledgeDecomposer(confidence_threshold=0.6)
    
    # Example input: Street vendor's intuition about customers
    input_data = {
        "description": "Street vendor's ability to assess customer purchasing intent and adjust pricing strategy based on subtle behavioral cues",
        "modalities": ["video", "audio"],
        "metadata": {
            "domain": "retail",
            "cultural_context": "Asian market",
            "expertise_years": 15
        }
    }
    
    # Validate input
    try:
        validate_input_data(input_data)
    except (KeyError, ValueError) as e:
        logger.error(f"Input validation failed: {e}")
        exit(1)
    
    # Convert modality strings to enums
    modality_enums = [ModalityType(m) for m in input_data["modalities"]]
    
    # Create and decompose the root node
    root_node = decomposer.create_root_node(
        description=input_data["description"],
        modalities=modality_enums,
        metadata=input_data.get("metadata")
    )
    
    # Perform decomposition
    final_type, skills = decomposer.decompose_node(root_node)
    
    # Output results
    print("\n" + "="*60)
    print("DECOMPOSITION RESULTS")
    print("="*60)
    print(f"Root Node ID: {root_node.node_id}")
    print(f"Final Type: {final_type.value}")
    print(f"Total Atomic Skills Extracted: {len(skills)}")
    print("\nExtracted Skills:")
    print("-"*60)
    
    for skill in skills:
        print(f"\n  Skill: {skill.name}")
        print(f"  ID: {skill.skill_id}")
        print(f"  Modality: {skill.modality.value}")
        print(f"  Confidence: {skill.confidence_score:.2f}")
        print(f"  Test: {skill.test_procedure}")
        print(f"  Criteria: {skill.success_criteria}")
        if skill.dependencies:
            print(f"  Dependencies: {skill.dependencies}")
    
    # Export graph
    print("\n" + "="*60)
    print("GRAPH EXPORT (JSON)")
    print("="*60)
    graph_json = decomposer.export_decomposition_graph(format="json")
    print(graph_json[:500] + "..." if len(graph_json) > 500 else graph_json)