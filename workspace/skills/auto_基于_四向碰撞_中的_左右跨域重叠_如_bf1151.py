"""
Module: auto_analogical_mapping.py

Description:
    Implements an automated skill for 'Analogical Mapping' based on the
    'Left-Right Cross-Domain Overlap' concept derived from 'Four-Direction Collision'
    theory in cognitive science.

    This module enables the system to identify structural isomorphisms between a
    Source Domain (e.g., Fluid Dynamics) and a Target Domain (e.g., Traffic Flow),
    and transfer solution models to generate novel hypotheses.

Key Concepts:
    - Structural Isomorphism: Matching relationships (R1) rather than just attributes (A1).
    - Cross-Domain Mapping: Bridging distinct knowledge domains.
    - Hypothesis Generation: Creating new inferences in the target domain based on
      source domain logic.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DomainType(Enum):
    """Enumeration for supported domain types for validation."""
    PHYSICS = "physics"
    FLUID_DYNAMICS = "fluid_dynamics"
    TRAFFIC_FLOW = "traffic_flow"
    ELECTRONICS = "electronics"
    ABSTRACT = "abstract"


@dataclass
class Entity:
    """Represents an object or concept within a domain."""
    uid: str
    name: str
    attributes: Dict[str, float] = field(default_factory=dict)
    domain_type: DomainType = DomainType.ABSTRACT


@dataclass
class Relation:
    """Represents a relationship between two entities."""
    uid: str
    name: str  # e.g., "causes", "increases", "flows_through"
    source_uid: str
    target_uid: str
    weight: float = 1.0


@dataclass
class DomainKnowledge:
    """Container for a specific domain's knowledge graph."""
    name: str
    domain_type: DomainType
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)


class AnalogicalMappingError(Exception):
    """Custom exception for errors during analogical reasoning."""
    pass


def _validate_structural_integrity(domain: DomainKnowledge) -> bool:
    """
    Helper function: Validates that all relations in a domain refer to existing entities.
    
    Args:
        domain: The domain knowledge base to validate.
        
    Returns:
        True if valid, raises ValueError if invalid.
    """
    logger.debug(f"Validating structural integrity for domain: {domain.name}")
    entity_uids = {e.uid for e in domain.entities}
    
    for rel in domain.relations:
        if rel.source_uid not in entity_uids:
            msg = f"Relation {rel.uid} has invalid source entity {rel.source_uid}"
            logger.error(msg)
            raise ValueError(msg)
        if rel.target_uid not in entity_uids:
            msg = f"Relation {rel.uid} has invalid target entity {rel.target_uid}"
            logger.error(msg)
            raise ValueError(msg)
            
    return True


def calculate_structural_overlap(
    source: DomainKnowledge, 
    target: DomainKnowledge
) -> Tuple[Dict[str, str], float]:
    """
    Core Function 1: Identifies structural isomorphism between two domains.
    
    This function implements the 'Left-Right Cross-Domain Overlap' logic. It ignores
    surface attributes (what things *look* like) and focuses on how things *relate*
    to each other (topological structure).
    
    Args:
        source: The source domain knowledge base (e.g., Fluid Dynamics).
        target: The target domain knowledge base (e.g., Traffic Flow).
        
    Returns:
        A tuple containing:
        - mapping_dict: A dictionary mapping Source Entity UIDs to Target Entity UIDs.
        - confidence_score: A float (0.0-1.0) indicating the quality of the isomorphism.
        
    Raises:
        AnalogicalMappingError: If domains are empty or validation fails.
    """
    logger.info(f"Starting structural overlap analysis: {source.name} -> {target.name}")
    
    # Data Validation
    if not source.relations or not target.relations:
        logger.warning("One or both domains lack relational data.")
        return {}, 0.0
        
    try:
        _validate_structural_integrity(source)
        _validate_structural_integrity(target)
    except ValueError as e:
        raise AnalogicalMappingError(f"Domain validation failed: {e}")

    # Create lookup maps for relations by name (structure)
    # Grouping relations by their predicate name
    source_rel_groups: Dict[str, List[Relation]] = {}
    for r in source.relations:
        source_rel_groups.setdefault(r.name, []).append(r)
        
    target_rel_groups: Dict[str, List[Relation]] = {}
    for r in target.relations:
        target_rel_groups.setdefault(r.name, []).append(r)
        
    # Find candidate mappings based on shared relational structure
    # Map Structure: Source UID -> Target UID -> Count of shared relational contexts
    candidate_votes: Dict[str, Dict[str, int]] = {}
    
    # Look for relation names that exist in both domains
    common_predicates = set(source_rel_groups.keys()) & set(target_rel_groups.keys())
    
    if not common_predicates:
        logger.info("No common relational predicates found. Isomorphism unlikely.")
        return {}, 0.0
        
    logger.debug(f"Found {len(common_predicates)} common relational structures.")
    
    for predicate in common_predicates:
        s_rels = source_rel_groups[predicate]
        t_rels = target_rel_groups[predicate]
        
        # Simple heuristic: If relation types match, vote for the entities involved
        for s_rel in s_rels:
            for t_rel in t_rels:
                # Vote for Source mapping
                if s_rel.source_uid not in candidate_votes:
                    candidate_votes[s_rel.source_uid] = {}
                candidate_votes[s_rel.source_uid][t_rel.source_uid] = \
                    candidate_votes[s_rel.source_uid].get(t_rel.source_uid, 0) + 1
                    
                # Vote for Target mapping
                if s_rel.target_uid not in candidate_votes:
                    candidate_votes[s_rel.target_uid] = {}
                candidate_votes[s_rel.target_uid][t_rel.target_uid] = \
                    candidate_votes[s_rel.target_uid].get(t_rel.target_uid, 0) + 1

    # Finalize mapping by taking the highest voted target for each source
    final_mapping: Dict[str, str] = {}
    total_votes = 0
    max_possible_votes = len(source.relations)
    
    for s_uid, targets in candidate_votes.items():
        best_t_uid = max(targets, key=targets.get)
        final_mapping[s_uid] = best_t_uid
        total_votes += targets[best_t_uid]
        
    # Confidence Score: Ratio of aligned structural votes to total source relations
    confidence = min(total_votes / max(len(source.relations), 1), 1.0)
    
    logger.info(f"Mapping complete. Confidence: {confidence:.2f}")
    return final_mapping, confidence


def generate_hypotheses(
    source: DomainKnowledge,
    target: DomainKnowledge,
    mapping: Dict[str, str],
    threshold: float = 0.5
) -> List[Dict[str, str]]:
    """
    Core Function 2: Transfers unmapped source knowledge to the target domain as hypotheses.
    
    This function uses the established mapping to project source-domain causalities
    or properties onto the target domain where they were previously unknown.
    
    Args:
        source: Source domain.
        target: Target domain.
        mapping: The dictionary mapping Source UIDs to Target UIDs.
        threshold: Minimum confidence required to generate a hypothesis.
        
    Returns:
        A list of hypothesis dictionaries, describing inferred relations or properties.
    """
    hypotheses = []
    
    if not mapping:
        logger.warning("Empty mapping provided. No hypotheses generated.")
        return hypotheses
        
    logger.info("Generating hypotheses based on cross-domain mapping...")
    
    # Invert mapping for reverse lookup if needed
    # target_to_source = {v: k for k, v in mapping.items()}
    
    # Get existing relations in target to avoid duplicating known facts
    target_rel_signatures = {
        (r.name, r.source_uid, r.target_uid) for r in target.relations
    }
    
    for s_rel in source.relations:
        # Check if the source relation's entities are mapped to the target domain
        s_source_mapped = mapping.get(s_rel.source_uid)
        s_target_mapped = mapping.get(s_rel.target_uid)
        
        if s_source_mapped and s_target_mapped:
            # Construct hypothetical relation in target domain
            hyp_signature = (s_rel.name, s_source_mapped, s_target_mapped)
            
            # If this relation does NOT exist in target, it is a Novel Hypothesis
            if hyp_signature not in target_rel_signatures:
                hypothesis = {
                    "type": "INFERRED_RELATION",
                    "predicate": s_rel.name,
                    "subject": s_source_mapped,
                    "object": s_target_mapped,
                    "source_evidence": f"Derived from {source.name} relation '{s_rel.name}'",
                    "certainty": "Tentative"
                }
                hypotheses.append(hypothesis)
                logger.debug(f"New hypothesis found: {hypothesis['predicate']} "
                             f"between {hypothesis['subject']} and {hypothesis['object']}")

    return hypotheses


class AnalogicalEngine:
    """
    Main engine wrapper to handle the full lifecycle of the analogical reasoning process.
    """
    
    def __init__(self):
        self.source_domain: Optional[DomainKnowledge] = None
        self.target_domain: Optional[DomainKnowledge] = None
        self.mapping: Dict[str, str] = {}
        self.hypotheses: List[Dict] = []
        
    def load_domains(self, source: DomainKnowledge, target: DomainKnowledge):
        """Loads and validates source and target domains."""
        logger.info("Loading domains into engine...")
        _validate_structural_integrity(source)
        _validate_structural_integrity(target)
        self.source_domain = source
        self.target_domain = target
        
    def execute_reasoning(self):
        """Runs the full analogical mapping and hypothesis generation pipeline."""
        if not self.source_domain or not self.target_domain:
            raise AnalogicalMappingError("Domains not loaded.")
            
        self.mapping, confidence = calculate_structural_overlap(
            self.source_domain, self.target_domain
        )
        
        if confidence > 0.1:  # Arbitrary low threshold to proceed
            self.hypotheses = generate_hypotheses(
                self.source_domain, 
                self.target_domain, 
                self.mapping
            )
        else:
            logger.warning("Confidence too low to generate reliable hypotheses.")
            
        return {
            "mapping": self.mapping,
            "confidence": confidence,
            "hypotheses": self.hypotheses
        }

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define Source Domain: Fluid Dynamics (Water in Pipe)
    # Entities
    e_pipe = Entity(uid="s1", name="Pipe", domain_type=DomainType.FLUID_DYNAMICS)
    e_water = Entity(uid="s2", name="Water", domain_type=DomainType.FLUID_DYNAMICS)
    e_pressure = Entity(uid="s3", name="Pressure", domain_type=DomainType.FLUID_DYNAMICS)
    e_flow_rate = Entity(uid="s4", name="Flow_Rate", domain_type=DomainType.FLUID_DYNAMICS)
    
    # Relations (The Structure)
    r1 = Relation(uid="sr1", name="contains", source_uid="s1", target_uid="s2")
    r2 = Relation(uid="sr2", name="causes_increase", source_uid="s3", target_uid="s4")
    r3 = Relation(uid="sr3", name="constrained_by", source_uid="s2", target_uid="s1")
    
    source_domain = DomainKnowledge(
        name="Fluid Dynamics",
        domain_type=DomainType.FLUID_DYNAMICS,
        entities=[e_pipe, e_water, e_pressure, e_flow_rate],
        relations=[r1, r2, r3]
    )
    
    # 2. Define Target Domain: Traffic Flow (Cars on Highway)
    # Entities
    e_highway = Entity(uid="t1", name="Highway", domain_type=DomainType.TRAFFIC_FLOW)
    e_cars = Entity(uid="t2", name="Cars", domain_type=DomainType.TRAFFIC_FLOW)
    # Note: We intentionally leave out 'Congestion' or 'Speed' to see if the system
    # can map 'Pressure' and 'Flow_Rate' concepts if partial structure exists.
    # Let's say we only know Highway contains Cars.
    
    # Relations
    tr1 = Relation(uid="tr1", name="contains", source_uid="t1", target_uid="t2")
    # We do NOT have the relation "Pressure causes Flow" here explicitly, 
    # but we might have similar structure if we define it.
    
    target_domain = DomainKnowledge(
        name="Traffic Flow",
        domain_type=DomainType.TRAFFIC_FLOW,
        entities=[e_highway, e_cars],
        relations=[tr1]
    )
    
    # 3. Run Engine
    engine = AnalogicalEngine()
    engine.load_domains(source_domain, target_domain)
    result = engine.execute_reasoning()
    
    # 4. Output Results
    print("\n--- Analogical Mapping Result ---")
    print(f"Mapping Identified: {result['mapping']}")
    print(f"Confidence Score: {result['confidence']:.2f}")
    print(f"Generated Hypotheses: {len(result['hypotheses'])}")
    for hyp in result['hypotheses']:
        print(f"- {hyp}")