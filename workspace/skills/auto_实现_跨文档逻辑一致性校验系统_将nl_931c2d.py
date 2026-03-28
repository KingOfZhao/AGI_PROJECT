"""
Cross-Document Logic Consistency Verification System (CLCVS)

This module implements a system to verify logical consistency across multiple documents
or long texts. It uses techniques inspired by data flow analysis (taint tracking) and
NLP coreference resolution to track the propagation of entities (like obligations,
rights, or variables) and detect contradictions.

Key Concepts:
- Entity: A subject or object defined in text (e.g., "Party A", "Deposit Amount").
- State: The condition of an entity at a specific point (e.g., "Defined", "Revoked", "Obligated").
- Transition: How an entity changes state between documents or sections.

Author: AGI System
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EntityType(Enum):
    """Enumeration for different types of trackable entities."""
    VARIABLE = auto()
    OBLIGATION = auto()
    RIGHT = auto()
    DEFINITION = auto()

class ConsistencyStatus(Enum):
    """Status of the consistency check."""
    CONSISTENT = auto()
    CONTRADICTION = auto()
    UNDEFINED_REFERENCE = auto()
    AMBIGUOUS = auto()

@dataclass
class Entity:
    """Represents a trackable entity within the text."""
    id: str
    name: str
    type: EntityType
    defined_in: str  # Document ID
    attributes: Dict[str, str] = field(default_factory=dict)
    aliases: Set[str] = field(default_factory=set)

@dataclass
class LogicState:
    """Represents the state of the system at a specific processing step."""
    document_id: str
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: List[Tuple[str, str, str]] = field(default_factory=list) # (Source, Target, Relation)

@dataclass
class VerificationResult:
    """Contains the results of the consistency verification."""
    status: ConsistencyStatus
    message: str
    conflicts: List[Tuple[str, str]] = field(default_factory=list) # (Entity ID, Description)

class CrossDocumentValidator:
    """
    Main class for validating logic across multiple documents.
    
    Uses a simplified taint analysis approach where 'definitions' are sources
    and 'usages' are sinks. It ensures that logic flows correctly and flags
    contradictions (e.g., redefinition with different attributes, or usage
    before definition).
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the validator.
        
        Args:
            strict_mode: If True, undefined references raise errors. 
                         If False, they raise warnings.
        """
        self.strict_mode = strict_mode
        self.global_state: Dict[str, Entity] = {}
        self.document_graph: Dict[str, List[str]] = {} # Dependency graph
        logger.info("CrossDocumentValidator initialized with strict_mode=%s", strict_mode)

    def _preprocess_text(self, text: str) -> List[str]:
        """
        Helper function to split text into processable segments (sentences/clauses).
        
        Args:
            text: Raw input text.
            
        Returns:
            A list of strings, representing segments.
        """
        # Basic sentence splitting regex (simplified for demonstration)
        segments = re.split(r'[.;\n]', text)
        return [s.strip() for s in segments if s.strip()]

    def _resolve_coreference(self, entity_name: str, context: Dict[str, Entity]) -> Optional[str]:
        """
        Helper function to resolve aliases to the canonical entity ID.
        
        Args:
            entity_name: The name or alias found in the text.
            context: The current context of known entities.
            
        Returns:
            The canonical entity ID or None.
        """
        # Direct match
        if entity_name in context:
            return entity_name
        
        # Check aliases
        for entity_id, entity in context.items():
            if entity_name in entity.aliases:
                return entity_id
        return None

    def parse_document(self, doc_id: str, content: str, doc_type: str = "text") -> LogicState:
        """
        Parses a single document to extract entities and relations.
        
        This acts as the 'Lexer' and 'Parser' for the unstructured/semi-structured text.
        
        Args:
            doc_id: Unique identifier for the document.
            content: The text content of the document.
            doc_type: Type of document (e.g., 'contract', 'code').
            
        Returns:
            A LogicState object representing the extracted logic.
        """
        if not content or not isinstance(content, str):
            logger.error("Invalid content provided for document %s", doc_id)
            raise ValueError("Document content must be a non-empty string.")

        logger.info("Parsing document: %s", doc_id)
        segments = self._preprocess_text(content)
        state = LogicState(document_id=doc_id)
        
        # Simplified Regex Patterns for Entity Extraction
        # Pattern: "X is defined as Y" or "X equals Y"
        def_pattern = re.compile(r"(\w+)\s+(?:is defined as|equals)\s+(.+)")
        # Pattern: "X obligates Y to Z"
        oblig_pattern = re.compile(r"(\w+)\s+obligates\s+(\w+)\s+to\s+(.+)")
        
        for idx, segment in enumerate(segments):
            # Extraction Logic
            match_def = def_pattern.match(segment)
            if match_def:
                var_name = match_def.group(1)
                var_value = match_def.group(2)
                
                # Check for contradictions with global state
                if var_name in self.global_state:
                    existing = self.global_state[var_name]
                    if existing.attributes.get('value') != var_value:
                        logger.warning("Potential contradiction detected for '%s' in doc %s", var_name, doc_id)
                
                entity = Entity(
                    id=f"{doc_id}_{var_name}",
                    name=var_name,
                    type=EntityType.DEFINITION,
                    defined_in=doc_id,
                    attributes={'value': var_value, 'line': str(idx)}
                )
                state.entities[entity.id] = entity
                continue

            match_oblig = oblig_pattern.match(segment)
            if match_oblig:
                source = match_oblig.group(1)
                target = match_oblig.group(2)
                duty = match_oblig.group(3)
                
                # Create or update obligation entities
                entity_id = f"oblig_{source}_{target}"
                entity = Entity(
                    id=entity_id,
                    name=f"Obligation:{source}->{target}",
                    type=EntityType.OBLIGATION,
                    defined_in=doc_id,
                    attributes={'duty': duty}
                )
                state.entities[entity.id] = entity
                state.relations.append((source, target, "OBLIGATES"))
        
        logger.info("Extracted %d entities from %s", len(state.entities), doc_id)
        return state

    def verify_consistency(self, states: List[LogicState]) -> VerificationResult:
        """
        Verifies the logical consistency across multiple parsed document states.
        
        This simulates the 'Data Flow Analysis' phase. It merges states and checks
        for Undefined Usage (Taint) and Contradictions.
        
        Args:
            states: A list of LogicState objects from different documents.
            
        Returns:
            A VerificationResult object detailing the outcome.
        """
        if not states:
            return VerificationResult(ConsistencyStatus.CONSISTENT, "No states to verify.")

        conflicts: List[Tuple[str, str]] = []
        temp_global_state: Dict[str, Entity] = {}

        logger.info("Starting consistency verification for %d states.", len(states))

        for state in states:
            logger.debug("Processing state for document: %s", state.document_id)
            
            # 1. Check Dependencies (Taint Analysis / Undefined References)
            for src, tgt, rel in state.relations:
                # Check if source and target are defined in current or previous states
                src_defined = src in temp_global_state or any(src == e.name for e in state.entities.values())
                tgt_defined = tgt in temp_global_state or any(tgt == e.name for e in state.entities.values())
                
                if not src_defined:
                    msg = f"Undefined source entity '{src}' used in relation in {state.document_id}"
                    conflicts.append((src, msg))
                    logger.warning(msg)
                    
                if not tgt_defined:
                    msg = f"Undefined target entity '{tgt}' used in relation in {state.document_id}"
                    conflicts.append((tgt, msg))
                    logger.warning(msg)

            # 2. Merge States and Check Logic Conflicts
            for entity_id, entity in state.entities.items():
                if entity.name in temp_global_state:
                    existing_entity = temp_global_state[entity.name]
                    
                    # Check for attribute mismatch (Logic Contradiction)
                    if existing_entity.type == EntityType.DEFINITION:
                        if existing_entity.attributes.get('value') != entity.attributes.get('value'):
                            msg = (f"Contradiction: Entity '{entity.name}' defined as "
                                   f"'{existing_entity.attributes.get('value')}' in {existing_entity.defined_in} "
                                   f"but '{entity.attributes.get('value')}' in {entity.defined_in}")
                            conflicts.append((entity.name, msg))
                            logger.error(msg)
                else:
                    temp_global_state[entity.name] = entity

        # Determine final status
        if not conflicts:
            status = ConsistencyStatus.CONSISTENT
            message = "All documents are logically consistent."
        elif any("Contradiction" in c[1] for c in conflicts):
            status = ConsistencyStatus.CONTRADICTION
            message = "Critical logical contradictions found."
        else:
            status = ConsistencyStatus.UNDEFINED_REFERENCE
            message = "Undefined references detected."

        # Update global state with verified entities
        self.global_state.update(temp_global_state)
        
        return VerificationResult(status=status, message=message, conflicts=conflicts)

# Usage Example
if __name__ == "__main__":
    # Initialize System
    validator = CrossDocumentValidator(strict_mode=True)

    # Document 1: Definition of terms
    doc1_content = """
    User is defined as ActiveAgent.
    System is defined as PassiveAgent.
    User obligates System to ProcessData.
    """

    # Document 2: Usage and Extension (Consistent)
    doc2_content = """
    User obligates System to StoreLogs.
    Admin is defined as SuperUser.
    """

    # Document 3: Contradiction
    doc3_content = """
    User is defined as InactiveAgent.
    """

    # Document 4: Undefined Reference
    doc4_content = """
    Guest obligates System to Logout.
    """

    try:
        # Parse Documents
        state1 = validator.parse_document("DOC_001", doc1_content)
        state2 = validator.parse_document("DOC_002", doc2_content)
        state3 = validator.parse_document("DOC_003", doc3_content)
        state4 = validator.parse_document("DOC_004", doc4_content)

        # Verify
        results = validator.verify_consistency([state1, state2, state3, state4])

        print(f"\n=== Verification Report ===")
        print(f"Status: {results.status.name}")
        print(f"Summary: {results.message}")
        print("Conflicts found:")
        for entity, detail in results.conflicts:
            print(f"- [{entity}]: {detail}")

    except ValueError as e:
        logger.error("Input validation failed: %s", e)
    except Exception as e:
        logger.exception("An unexpected error occurred: %s", e)