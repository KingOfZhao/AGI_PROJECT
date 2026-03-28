"""
Industrial SOP to Skill Tree Parser Module.

This module converts rigorous Standard Operating Procedure (SOP) text into a
structured, executable Skill Tree topology. It identifies logical dependencies
(sequential, conditional, parallel) within the SOP and maps them to existing
AGI skill nodes.

Domain: nlp_process_mining
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import re
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, field, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkillNodeType(Enum):
    """Enumeration of possible node types in the Skill Tree."""
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ACTION = "action"
    LOOP = "loop"


class SOPParsingError(Exception):
    """Custom exception for errors during SOP parsing."""
    pass


@dataclass
class SkillNode:
    """
    Represents a node in the executable Skill Tree.
    
    Attributes:
        id: Unique identifier for the node.
        name: Human-readable name derived from SOP.
        node_type: Type of logic (Sequence, Action, etc.).
        context: Dictionary containing parameters (e.g., torque, angle).
        dependencies: List of IDs of nodes that must complete before this one.
        children: Sub-nodes for complex types (Sequence/Parallel).
        mapped_skill_id: ID of the existing AGI skill this node maps to (if any).
    """
    id: str
    name: str
    node_type: SkillNodeType
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    children: List['SkillNode'] = field(default_factory=list)
    mapped_skill_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize the node to a dictionary."""
        return asdict(self)


class SOPParser:
    """
    Parses industrial SOP text into a structured Skill Tree.
    
    Handles logical extraction, context inference, and topology mapping.
    """

    def __init__(self, existing_skill_nodes: Dict[str, Dict]):
        """
        Initialize the parser with a knowledge base of existing skills.
        
        Args:
            existing_skill_nodes: Dictionary mapping skill IDs to their metadata.
        """
        if not existing_skill_nodes:
            logger.warning("Initializing parser with empty skill knowledge base.")
        self.existing_skill_nodes = existing_skill_nodes
        self._node_counter = 0
        logger.info("SOPParser initialized with %d existing skills.", len(existing_skill_nodes))

    def _generate_node_id(self) -> str:
        """Generate a unique ID for a new skill node."""
        self._node_counter += 1
        return f"sop_node_{self._node_counter}"

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """
        Extract implicit context parameters from text.
        
        Example: "Tighten screw to 10Nm" -> {'torque': '10Nm'}
        """
        params = {}
        # Regex for Torque (e.g., 10Nm, 5 N·m)
        torque_match = re.search(r'(\d+(\.\d+)?)\s*(Nm|N·m|Newton)', text, re.IGNORECASE)
        if torque_match:
            params['torque'] = f"{torque_match.group(1)} {torque_match.group(3)}"
            
        # Regex for Angle (e.g., 90 degrees)
        angle_match = re.search(r'(\d+)\s*(degrees|°)', text, re.IGNORECASE)
        if angle_match:
            params['angle'] = int(angle_match.group(1))
            
        # Regex for Time (e.g., 5 seconds)
        time_match = re.search(r'(\d+)\s*(s|sec|seconds)', text, re.IGNORECASE)
        if time_match:
            params['duration'] = int(time_match.group(1))
            
        return params

    def _find_similar_skill(self, node_name: str, node_context: Dict) -> Optional[str]:
        """
        Map a parsed SOP node to an existing AGI skill node based on semantics.
        
        This is a simplified heuristic mapping. In production, this would use
        vector embeddings or a knowledge graph.
        """
        # Heuristic: Keyword matching against existing skills
        target_keywords = set(node_name.lower().split())
        
        best_match = None
        highest_score = 0
        
        for skill_id, skill_meta in self.existing_skill_nodes.items():
            skill_name = skill_meta.get('name', '')
            meta_keywords = set(skill_name.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(target_keywords & meta_keywords)
            union = len(target_keywords | meta_keywords)
            score = intersection / union if union > 0 else 0
            
            # Boost score if context matches (e.g. both have 'torque')
            if any(k in skill_meta.get('context', {}) for k in node_context.keys()):
                score += 0.1
            
            if score > highest_score and score > 0.5:  # Threshold
                highest_score = score
                best_match = skill_id
                
        return best_match

    def parse_sop_segment(self, sop_text: str) -> SkillNode:
        """
        Core function to parse a block of SOP text into a Skill Node structure.
        
        Args:
            sop_text: The raw text of the Standard Operating Procedure.
            
        Returns:
            A SkillNode object representing the root of the parsed tree.
            
        Raises:
            SOPParsingError: If text is empty or unparseable.
        """
        if not sop_text or not sop_text.strip():
            raise SOPParsingError("Input SOP text cannot be empty.")

        logger.info("Parsing SOP segment...")
        
        # Normalize line endings and split
        lines = [line.strip() for line in sop_text.split('\n') if line.strip()]
        
        root_node = SkillNode(
            id=self._generate_node_id(),
            name="SOP_Root_Sequence",
            node_type=SkillNodeType.SEQUENCE
        )
        
        # State tracking for logical flow
        # This simplified logic handles sequential steps and simple "If/Then" branching
        last_node_id = None
        
        for line in lines:
            # Detect Logic Type
            if line.lower().startswith("if "):
                # Handle Conditional Branch
                condition_text = line[3:].strip()
                node = SkillNode(
                    id=self._generate_node_id(),
                    name=f"Condition: {condition_text}",
                    node_type=SkillNodeType.CONDITIONAL,
                    dependencies=[last_node_id] if last_node_id else []
                )
                logger.debug(f"Created conditional node: {node.id}")
                
            elif line.lower().startswith("while "):
                # Handle Loop
                loop_text = line[6:].strip()
                node = SkillNode(
                    id=self._generate_node_id(),
                    name=f"Loop: {loop_text}",
                    node_type=SkillNodeType.LOOP,
                    dependencies=[last_node_id] if last_node_id else []
                )
                
            else:
                # Handle Action (Default)
                context = self._extract_parameters(line)
                node = SkillNode(
                    id=self._generate_node_id(),
                    name=line,
                    node_type=SkillNodeType.ACTION,
                    context=context,
                    dependencies=[last_node_id] if last_node_id else []
                )
                
                # Map to existing topology
                mapped_id = self._find_similar_skill(line, context)
                if mapped_id:
                    node.mapped_skill_id = mapped_id
                    logger.info(f"Mapped '{line}' to existing skill {mapped_id}")

            root_node.children.append(node)
            last_node_id = node.id

        return root_node


# Example Usage
if __name__ == "__main__":
    # Mock existing AGI skills database
    existing_skills = {
        "skill_001": {"name": "tighten bolt", "context": {"torque": "float"}},
        "skill_002": {"name": "visual inspection", "context": {}},
        "skill_042": {"name": "apply lubricant", "context": {"volume": "ml"}}
    }

    sample_sop = """
    Clean the surface area thoroughly
    Apply lubricant to the bolt threads
    Tighten bolt to 15Nm
    If bolt is stripped
    Replace bolt assembly
    Perform final visual inspection
    """

    try:
        parser = SOPParser(existing_skill_nodes=existing_skills)
        skill_tree = parser.parse_sop_segment(sample_sop)
        
        # Output the result structure
        print(json.dumps(skill_tree.to_dict(), indent=2, default=str))
        
    except SOPParsingError as e:
        logger.error(f"Failed to parse SOP: {e}")