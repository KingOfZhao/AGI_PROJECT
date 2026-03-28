"""
Cross-Domain Skill Transfer Microscope Module.

This module provides tools to analyze and map isomorphic structures between
a source skill (already mastered) and a target skill (to be learned).
By identifying deep topological similarities, it generates "Metaphorical Tutorials"
to accelerate the learning process using cognitive scaffolding.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkillDomain(Enum):
    """Enumeration of possible skill domains."""
    PHYSICAL = "physical"
    COGNITIVE = "cognitive"
    ARTISTIC = "artistic"
    SOCIAL = "social"
    TECHNICAL = "technical"


@dataclass
class SkillNode:
    """Represents a fundamental component of a skill."""
    node_id: str
    name: str
    attributes: Dict[str, float]  # e.g., {"rhythm": 0.9, "force": 0.4}
    domain: SkillDomain
    
    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())


@dataclass
class IsomorphicPair:
    """Represents a mapped pair between source and target skills."""
    source_node: str
    target_node: str
    similarity_score: float
    mapping_rationale: str


@dataclass
class MetaphoricalTutorial:
    """The generated output containing the learning scaffolding."""
    source_skill: str
    target_skill: str
    transfer_map: List[IsomorphicPair]
    narrative: str
    difficulty_alignment: float


class SkillGraph:
    """
    Represents a skill as a topological graph of nodes.
    """
    def __init__(self, skill_name: str, domain: SkillDomain):
        self.skill_name = skill_name
        self.domain = domain
        self.nodes: List[SkillNode] = []
        
    def add_node(self, name: str, attributes: Dict[str, float]) -> None:
        """Adds a node to the skill graph."""
        if not attributes:
            raise ValueError("Attributes dictionary cannot be empty.")
        node = SkillNode(
            node_id=str(uuid.uuid4()),
            name=name,
            attributes=attributes,
            domain=self.domain
        )
        self.nodes.append(node)
        logger.debug(f"Added node '{name}' to skill '{self.skill_name}'")

    def get_node_by_name(self, name: str) -> Optional[SkillNode]:
        """Retrieves a node by its name."""
        for node in self.nodes:
            if node.name == name:
                return node
        return None


def _calculate_semantic_overlap(attr_a: Dict[str, float], attr_b: Dict[str, float]) -> float:
    """
    Helper function: Calculates the cosine similarity-like overlap between two attribute sets.
    
    Args:
        attr_a: Attributes of node A
        attr_b: Attributes of node B
        
    Returns:
        A float score between 0.0 and 1.0 representing similarity.
    """
    common_keys = set(attr_a.keys()) & set(attr_b.keys())
    if not common_keys:
        return 0.0
    
    dot_product = sum(attr_a[k] * attr_b[k] for k in common_keys)
    magnitude_a = sum(v**2 for v in attr_a.values())**0.5
    magnitude_b = sum(v**2 for v in attr_b.values())**0.5
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
        
    return dot_product / (magnitude_a * magnitude_b)


class CrossDomainMicroscope:
    """
    The core engine for analyzing skill transferability.
    
    This class compares a Source Skill Graph with a Target Skill Graph to find
    isomorphic structures and generate learning metaphors.
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize the Microscope.
        
        Args:
            similarity_threshold: Minimum score to consider two nodes isomorphic.
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
            
        self.similarity_threshold = similarity_threshold
        logger.info(f"CrossDomainMicroscope initialized with threshold {similarity_threshold}")

    def analyze_isomorphism(self, source: SkillGraph, target: SkillGraph) -> List[IsomorphicPair]:
        """
        Core Function 1: Analyzes two skill graphs to find structural overlaps.
        
        Args:
            source: The mastered skill graph.
            target: The new skill to learn.
            
        Returns:
            A list of IsomorphicPair objects representing the mappings.
        """
        if not source.nodes or not target.nodes:
            logger.warning("One or both skill graphs are empty.")
            return []
            
        mappings: List[IsomorphicPair] = []
        
        logger.info(f"Analyzing {source.skill_name} -> {target.skill_name}")
        
        for t_node in target.nodes:
            best_match: Optional[Tuple[SkillNode, float]] = None
            
            for s_node in source.nodes:
                # Only compare if there is some attribute overlap potential
                score = _calculate_semantic_overlap(s_node.attributes, t_node.attributes)
                
                if score >= self.similarity_threshold:
                    if best_match is None or score > best_match[1]:
                        best_match = (s_node, score)
            
            if best_match:
                s_node, score = best_match
                pair = IsomorphicPair(
                    source_node=s_node.name,
                    target_node=t_node.name,
                    similarity_score=round(score, 3),
                    mapping_rationale=f"Shared attribute structure (Score: {score:.2f})"
                )
                mappings.append(pair)
                logger.debug(f"Mapped: {s_node.name} <-> {t_node.name}")
                
        return mappings

    def generate_metaphor_tutorial(self, source: SkillGraph, target: SkillGraph, mappings: List[IsomorphicPair]) -> MetaphoricalTutorial:
        """
        Core Function 2: Generates a tutorial narrative based on the mappings.
        
        Uses the 'source' concepts to explain 'target' concepts.
        
        Args:
            source: Source skill graph.
            target: Target skill graph.
            mappings: The list of detected isomorphic pairs.
            
        Returns:
            A MetaphoricalTutorial object containing the learning guide.
        """
        if not mappings:
            narrative = f"No direct cognitive bridge found between {source.skill_name} and {target.skill_name}. Learning must proceed from first principles."
            return MetaphoricalTutorial(
                source_skill=source.skill_name,
                target_skill=target.skill_name,
                transfer_map=[],
                narrative=narrative,
                difficulty_alignment=1.0 # High difficulty (no help)
            )
        
        narrative_parts = [f"To learn {target.skill_name}, leverage your mastery of {source.skill_name}:\n"]
        
        for pair in mappings:
            # Constructing the metaphor
            part = (f"1. Understanding '{pair.target_node}':\n"
                    f"   Think of this like '{pair.source_node}' in {source.skill_name}.\n"
                    f"   (Structural Similarity: {pair.similarity_score * 100:.1f}%)\n")
            narrative_parts.append(part)
            
        full_narrative = "\n".join(narrative_parts)
        
        # Calculate how much the source 'covers' the target
        coverage = len(mappings) / len(target.nodes) if target.nodes else 0
        
        logger.info(f"Generated tutorial with {len(mappings)} bridges.")
        
        return MetaphoricalTutorial(
            source_skill=source.skill_name,
            target_skill=target.skill_name,
            transfer_map=mappings,
            narrative=full_narrative,
            difficulty_alignment=1.0 - coverage
        )


# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # 1. Define Source Skill (Swimming)
    swimming = SkillGraph("Swimming", SkillDomain.PHYSICAL)
    swimming.add_node("Breath Control", {"rhythm": 0.9, "pressure_management": 0.8, "endurance": 0.7})
    swimming.add_node("Streamlining", {"aerodynamics": 0.9, "body_control": 0.8})
    
    # 2. Define Target Skill (Weight Lifting)
    lifting = SkillGraph("Weight Lifting", SkillDomain.PHYSICAL)
    lifting.add_node("Valsalva Maneuver", {"rhythm": 0.8, "pressure_management": 0.9, "force": 0.8})
    lifting.add_node("Stance Stability", {"balance": 0.8, "body_control": 0.9})
    
    # 3. Initialize Microscope
    microscope = CrossDomainMicroscope(similarity_threshold=0.5)
    
    # 4. Analyze
    iso_pairs = microscope.analyze_isomorphism(swimming, lifting)
    
    # 5. Generate Tutorial
    tutorial = microscope.generate_metaphor_tutorial(swimming, lifting, iso_pairs)
    
    # Output results
    print("\n=== Generated Metaphorical Tutorial ===")
    print(f"Source: {tutorial.source_skill}")
    print(f"Target: {tutorial.target_skill}")
    print(f"Difficulty Reduction: {tutorial.difficulty_alignment:.2f}")
    print("\nNarrative:")
    print(tutorial.narrative)
    
    # JSON Output format demonstration
    print("\n=== Transfer Map (JSON) ===")
    print(json.dumps([asdict(p) for p in tutorial.transfer_map], indent=2))