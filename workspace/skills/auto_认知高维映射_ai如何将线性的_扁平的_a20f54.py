"""
Module: auto_cognitive_high_dim_mapping_ai
Description: 【认知高维映射】Transforms linear, flat knowledge (e.g., textbook text)
             into a topological 'Cognitive Network' (DAG).
             
             Core features:
             1. Automatic extraction of knowledge atoms.
             2. Inference of explicit dependencies.
             3. Prediction of implicit dependencies using heuristics (concept inclusion).
             4. Validation to ensure Directed Acyclic Graph (DAG) properties.
             
Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
import networkx as nx  # Assuming networkx is available for graph validation/structure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeAtom:
    """
    Represents a single node in the cognitive network.
    
    Attributes:
        id (str): Unique identifier for the knowledge point.
        content (str): The raw text content.
        context (str): Surrounding context or section header.
        keywords (Set[str]): Extracted keywords for heuristic analysis.
    """
    id: str
    content: str
    context: str = "general"
    keywords: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.id or not self.content:
            raise ValueError("KnowledgeAtom must have an ID and content.")
        # Auto-extract basic keywords if not provided
        if not self.keywords:
            self.keywords = _extract_keywords_heuristic(self.content)


class CognitiveMappingError(Exception):
    """Custom exception for cognitive mapping failures."""
    pass


def _extract_keywords_heuristic(text: str) -> Set[str]:
    """
    [Helper] Extracts potential conceptual keywords from text.
    
    In a real AGI system, this would use NLP/NER. Here we use regex heuristics
    to simulate the identification of 'concepts' (Capitalized words or specific patterns).
    
    Args:
        text (str): Input text.
        
    Returns:
        Set[str]: Set of extracted keywords.
    """
    # Simple heuristic: Find words starting with a capital letter (excluding sentence starts)
    # or specific technical patterns.
    matches = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)\b', text)  # CamelCase
    matches += re.findall(r'\b[A-Z]{2,}\b', text)  # Acronyms
    return set(matches)


def analyze_implicit_dependencies(
    atoms: List[KnowledgeAtom], 
    existing_edges: Set[Tuple[str, str]]
) -> Set[Tuple[str, str]]:
    """
    [Core Function 2] Infers 'implicit' dependencies based on conceptual inclusion.
    
    Logic:
    If Concept B uses terminology that was formally introduced or defined in Concept A,
    and A appears "earlier" in the linear flow, we infer an implicit dependency A -> B.
    
    Args:
        atoms (List[KnowledgeAtom]): List of knowledge atoms in linear order.
        existing_edges (Set[Tuple[str, str]]): Explicit dependencies already identified.
        
    Returns:
        Set[Tuple[str, str]]: A set of inferred implicit edges (source_id, target_id).
        
    Raises:
        CognitiveMappingError: If analysis fails.
    """
    if not atoms:
        return set()

    try:
        implicit_edges = set()
        # Map concepts to the first atom ID where they appear significantly
        concept_origin_map: Dict[str, str] = {}
        
        # Sorted by linear order (assumed list order)
        sorted_atoms = sorted(atoms, key=lambda x: x.id) 

        for atom in sorted_atoms:
            # Check if current atom references concepts defined earlier
            for concept in atom.keywords:
                if concept in concept_origin_map:
                    origin_id = concept_origin_map[concept]
                    # Avoid self-loops and duplicates
                    if origin_id != atom.id and (origin_id, atom.id) not in existing_edges:
                        implicit_edges.add((origin_id, atom.id))
            
            # Register current atom's keywords as 'origin' for future nodes
            # (Simulating the 'Introduction' of a concept)
            for concept in atom.keywords:
                if concept not in concept_origin_map:
                    concept_origin_map[concept] = atom.id

        logger.info(f"Identified {len(implicit_edges)} implicit dependencies.")
        return implicit_edges
        
    except Exception as e:
        logger.error(f"Error during implicit dependency analysis: {e}")
        raise CognitiveMappingError(f"Analysis failed: {e}")


def build_cognitive_dag(
    atoms: List[KnowledgeAtom],
    explicit_relations: Optional[List[Tuple[str, str]]] = None
) -> nx.DiGraph:
    """
    [Core Function 1] Constructs the topological Cognitive Network (DAG).
    
    This function orchestrates the mapping process:
    1. Validates input atoms.
    2. Builds explicit connections.
    3. Augments with implicit connections.
    4. Validates the final structure to ensure it is a DAG.
    
    Args:
        atoms (List[KnowledgeAtom]): The linear list of knowledge points.
        explicit_relations (Optional[List[Tuple[str, str]]]): Known dependencies 
            (e.g., "Chapter 1" -> "Chapter 2").
            
    Returns:
        nx.DiGraph: A directed acyclic graph representing the knowledge topology.
        
    Raises:
        ValueError: If input data is invalid.
        CognitiveMappingError: If the resulting graph contains cycles (not a DAG).
        
    Example:
        >>> atoms = [
        ...     KnowledgeAtom(id="k1", content="Introduction to Python variables."),
        ...     KnowledgeAtom(id="k2", content="Python Data Structures rely on variables.")
        ... ]
        >>> graph = build_cognitive_dag(atoms)
        >>> print(graph.nodes)
    """
    logger.info(f"Starting Cognitive DAG construction with {len(atoms)} atoms.")
    
    # 1. Data Validation
    if not atoms:
        logger.warning("Empty atom list provided. Returning empty graph.")
        return nx.DiGraph()
        
    if explicit_relations is None:
        explicit_relations = []
        
    # Validate atom IDs are unique
    ids = [a.id for a in atoms]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate KnowledgeAtom IDs detected.")
        
    # 2. Initialize Graph
    G = nx.DiGraph()
    for atom in atoms:
        G.add_node(atom.id, content=atom.content, keywords=atom.keywords)
    
    # Add Explicit Edges
    G.add_edges_from(explicit_relations)
    logger.info(f"Added {len(explicit_relations)} explicit edges.")
    
    # 3. Analyze Implicit Dependencies
    implicit_edges = analyze_implicit_dependencies(atoms, set(explicit_relations))
    G.add_edges_from(implicit_edges)
    
    # 4. Topological Validation (Cycle Check)
    # The challenge: Handling implied dependencies might create logical loops.
    # We must ensure the result is a DAG.
    try:
        # Perform check
        if not nx.is_directed_acyclic_graph(G):
            # Attempt to fix or report
            cycles = list(nx.simple_cycles(G))
            logger.error(f"Generated graph contains cycles: {cycles}")
            raise CognitiveMappingError(
                f"Cognitive mapping failed: Detected {len(cycles)} cycles in the graph. "
                "Implicit inferences contradict structure."
            )
            
        logger.info("Graph validation successful: Structure is a DAG.")
        
        # Calculate topological generations (Layers)
        topological_sort = list(nx.topological_sort(G))
        logger.info(f"Topological order established with {len(topological_sort)} nodes.")
        
        return G
        
    except nx.NetworkXError as e:
        logger.critical(f"Graph processing error: {e}")
        raise CognitiveMappingError(f"Graph construction error: {e}")


def generate_dag_report(graph: nx.DiGraph) -> Dict:
    """
    Generates a statistical report of the Cognitive DAG.
    
    Args:
        graph (nx.DiGraph): The constructed knowledge graph.
        
    Returns:
        Dict: Statistics including depth, density, and hub nodes.
    """
    if graph.number_of_nodes() == 0:
        return {"status": "empty"}

    report = {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(graph),
        "density": nx.density(graph),
        "root_nodes": [n for n, d in graph.in_degree() if d == 0],
        "leaf_nodes": [n for n, d in graph.out_degree() if d == 0],
    }
    
    # Calculate longest path (DAG depth)
    if report["is_dag"]:
        report["max_depth"] = nx.dag_longest_path_length(graph)
    
    return report


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Prepare sample linear data (Simulating a textbook excerpt)
    raw_knowledge = [
        KnowledgeAtom(
            id="math_01", 
            content="Variables are symbols that hold values.", 
            context="Basics"
        ),
        KnowledgeAtom(
            id="math_02", 
            content="Functions map input Variables to output values.", 
            context="Intermediate"
        ),
        KnowledgeAtom(
            id="math_03", 
            content="Derivatives measure the rate of change of Functions.", 
            context="Advanced"
        ),
         KnowledgeAtom(
            id="math_04", 
            content="Integrals are the inverse of Derivatives.", 
            context="Advanced"
        )
    ]

    print("-" * 50)
    print("Initializing Cognitive High-Dimensional Mapping...")
    
    try:
        # 2. Build the Cognitive Network
        # Note: We pass an empty list for explicit relations to test implicit inference
        cognitive_graph = build_cognitive_dag(raw_knowledge)
        
        # 3. Generate Report
        stats = generate_dag_report(cognitive_graph)
        
        print("\nMapping Complete.")
        print(f"Nodes: {stats['node_count']}")
        print(f"Edges (Connections): {stats['edge_count']}")
        print(f"Max Depth (Learning Path Length): {stats.get('max_depth', 'N/A')}")
        print(f"Root Nodes (Starting Points): {stats['root_nodes']}")
        
        print("\nEdges (Source -> Target):")
        for u, v in cognitive_graph.edges():
            print(f"  {u} -> {v}")
            
    except CognitiveMappingError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")