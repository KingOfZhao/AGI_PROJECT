"""
Module: auto_intent_to_directed_hypergraph_2fdace
Description:
    Transforms unstructured, long-form natural language intents into a Directed Hypergraph
    structure to serve as a modular Abstract Syntax Tree (AST) skeleton.
    
    This module addresses the challenge of interpreting 'Architectural Intent' by
    identifying implicit hierarchical relationships and cross-module dependencies,
    mapping fuzzy semantics into deterministic, structured nodes.

Domain: nlp_ast_mapping
"""

import logging
import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple, Any
from uuid import uuid4

# --- Configuration & Setup ---

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class NodeType(Enum):
    """Enumeration of possible node types in the architecture skeleton."""
    ROOT = "root"
    MODULE = "module"
    SERVICE = "service"
    FEATURE = "feature"
    DATA_MODEL = "data_model"
    UI_COMPONENT = "ui_component"

@dataclass
class Hyperedge:
    """
    Represents a directed hyperedge in the graph.
    A hyperedge connects a set of source nodes to a set of target nodes,
    modeling complex dependencies (e.g., multiple modules triggering one process).
    """
    sources: Set[str]
    targets: Set[str]
    label: str
    edge_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "label": self.label,
            "sources": list(self.sources),
            "targets": list(self.targets)
        }

@dataclass
class ASTNode:
    """Represents a node in the Abstract Syntax Tree skeleton."""
    node_id: str
    name: str
    node_type: NodeType
    description: str
    dependencies: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.node_type.value,
            "description": self.description,
            "dependencies": list(self.dependencies)
        }

@dataclass
class DirectedHypergraph:
    """Container for the generated architecture graph."""
    nodes: Dict[str, ASTNode] = field(default_factory=dict)
    edges: List[Hyperedge] = field(default_factory=list)

    def add_node(self, node: ASTNode):
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists. Overwriting.")
        self.nodes[node.node_id] = node

    def add_hyperedge(self, sources: List[str], targets: List[str], label: str):
        # Validation: Ensure source and target nodes exist
        all_ids = set(sources + targets)
        current_ids = set(self.nodes.keys())
        missing = all_ids - current_ids
        if missing:
            logger.error(f"Cannot create edge. Missing nodes: {missing}")
            raise ValueError(f"Missing nodes for edge: {missing}")
        
        edge = Hyperedge(sources=set(sources), targets=set(targets), label=label)
        self.edges.append(edge)

    def export_json(self) -> str:
        return json.dumps({
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges]
        }, indent=2)

# --- Intent Parsing & Extraction Logic ---

class IntentParser:
    """
    Parses unstructured text to extract architectural components.
    Uses keyword extraction and heuristic rules to identify modules and relationships.
    """

    def __init__(self):
        # In a real AGI system, this would load embeddings or LLM prompts.
        # Here we use heuristic patterns for demonstration.
        self.module_patterns = {
            NodeType.SERVICE: r'(service|backend|api|server)',
            NodeType.UI_COMPONENT: r'(ui|interface|screen|frontend|view)',
            NodeType.DATA_MODEL: r'(database|db|storage|model|schema)',
            NodeType.FEATURE: r'(feature|function|ability|capability|auth|login|chat)'
        }
        logger.info("IntentParser initialized with heuristic patterns.")

    def _clean_text(self, text: str) -> str:
        """Basic text normalization."""
        if not isinstance(text, str):
            raise TypeError("Input intent must be a string.")
        return text.lower().strip()

    def extract_entities(self, text: str) -> List[Tuple[str, NodeType]]:
        """
        Extracts potential architectural nodes from text.
        
        Args:
            text (str): Raw user intent text.
            
        Returns:
            List[Tuple[str, NodeType]]: List of (entity_name, type).
        """
        clean_text = self._clean_text(text)
        entities = []
        
        # Simple tokenization (split by non-alphanumeric)
        tokens = re.split(r'[^a-zA-Z0-9]+', clean_text)
        
        # Context window scanning (very simplified)
        # In production, use dependency parsing or transformer NER
        for token in tokens:
            if len(token) < 3: continue
            for n_type, pattern in self.module_patterns.items():
                if re.search(pattern, token):
                    # Generate a readable name
                    name = f"{token.capitalize()}{n_type.value.capitalize()}"
                    entities.append((name, n_type))
                    
        # Deduplication while preserving order
        seen = set()
        unique_entities = [x for x in entities if not (x[0] in seen or seen.add(x[0]))]
        
        logger.info(f"Extracted {len(unique_entities)} potential entities.")
        return unique_entities

# --- Graph Construction Logic ---

class ArchitectureMapper:
    """
    Maps extracted entities to a Directed Hypergraph AST.
    Responsible for resolving dependencies and creating structural links.
    """

    def __init__(self):
        self.graph = DirectedHypergraph()
        self.node_mapping: Dict[str, str] = {} # Maps name -> ID

    def _create_root_node(self, intent_summary: str) -> str:
        """Creates the root node of the AST."""
        root_id = "root_0"
        root = ASTNode(
            node_id=root_id,
            name="ProjectRoot",
            node_type=NodeType.ROOT,
            description=intent_summary
        )
        self.graph.add_node(root)
        self.node_mapping["root"] = root_id
        return root_id

    def build_graph(self, intent_text: str, entities: List[Tuple[str, NodeType]]) -> DirectedHypergraph:
        """
        Constructs the graph from entities.
        
        Args:
            intent_text (str): The original text for context.
            entities (List[Tuple[str, NodeType]]): Extracted components.
            
        Returns:
            DirectedHypergraph: The constructed architectural skeleton.
        """
        if not entities:
            logger.warning("No entities provided to build graph.")
            return self.graph

        root_id = self._create_root_node(intent_text)
        
        # Create nodes
        for idx, (name, n_type) in enumerate(entities):
            node_id = f"node_{idx}_{uuid4().hex[:6]}"
            node = ASTNode(
                node_id=node_id,
                name=name,
                node_type=n_type,
                description=f"Auto-generated {n_type.value} based on intent."
            )
            self.graph.add_node(node)
            self.node_mapping[name] = node_id

        # Create dependencies (Heuristic: UI -> Service -> DB)
        # This represents the "Architectural Intent" convergence
        ui_nodes = [nid for n, (name, nid) in self.node_mapping.items() if self.graph.nodes[nid].node_type == NodeType.UI_COMPONENT]
        service_nodes = [nid for n, (name, nid) in self.node_mapping.items() if self.graph.nodes[nid].node_type == NodeType.SERVICE]
        db_nodes = [nid for n, (name, nid) in self.node_mapping.items() if self.graph.nodes[nid].node_type == NodeType.DATA_MODEL]

        # Link all to Root
        all_children = list(self.node_mapping.values())
        all_children.remove(root_id)
        if all_children:
            self.graph.add_hyperedge([root_id], all_children, "composition")

        # Link logical flow
        if ui_nodes and service_nodes:
            self.graph.add_hyperedge(ui_nodes, service_nodes, "api_call")
        if service_nodes and db_nodes:
            self.graph.add_hyperedge(service_nodes, db_nodes, "data_persistence")
            
        return self.graph

# --- Facade / Main Function ---

def intent_to_hypergraph_ast(intent: str) -> Optional[DirectedHypergraph]:
    """
    Main entry point. Converts unstructured text intent into a Directed Hypergraph AST.
    
    Input Format:
        string: A long text describing software requirements (e.g., "Build a lightweight chat app with a React UI and Python backend").
    
    Output Format:
        DirectedHypergraph: An object containing nodes (ASTNode) and edges (Hyperedge).
        
    Example:
        >>> text = "I need a lightweight chat app with a React UI, Python backend service, and MongoDB storage."
        >>> graph = intent_to_hypergraph_ast(text)
        >>> print(graph.export_json())
    """
    if not intent or len(intent) < 10:
        logger.error("Input intent is too short or empty.")
        return None

    try:
        # Step 1: NLP Extraction
        parser = IntentParser()
        entities = parser.extract_entities(intent)
        
        # Step 2: Structure Mapping
        mapper = ArchitectureMapper()
        graph = mapper.build_graph(intent, entities)
        
        logger.info("Successfully generated Directed Hypergraph AST.")
        return graph

    except Exception as e:
        logger.exception(f"Critical failure during AST generation: {e}")
        return None

# --- Usage Example ---

if __name__ == "__main__":
    # Example Input: Unstructured intent
    sample_intent = """
    Create a lightweight social app similar to WeChat. 
    It needs a highly responsive UI, a backend service for message routing, 
    and a database for user storage. It should also support image processing features.
    """

    print(f"Processing intent: '{sample_intent[:50]}...'")
    
    # Execute
    result_graph = intent_to_hypergraph_ast(sample_intent)

    if result_graph:
        print("\n--- Generated Hypergraph AST (JSON) ---")
        print(result_graph.export_json())
    else:
        print("Failed to generate graph.")