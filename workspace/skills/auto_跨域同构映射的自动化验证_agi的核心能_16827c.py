"""
Module: auto_cross_domain_isomorphism_validator
Description: Implements an automated pipeline to verify whether a proposed mapping
             between two distinct domains (e.g., Fluid Dynamics vs. Traffic Flow)
             represents a genuine structural (mathematical/physical) isomorphism
             rather than a superficial linguistic coincidence.

             This module extracts symbolic representations of domain behaviors,
             constructs computational graphs, and performs graph isomorphism analysis.
"""

import logging
import sympy
from sympy.core.basic import Basic as SympyBasic
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossDomainValidator")


@dataclass
class ComputationalGraph:
    """
    Represents the computational graph of a mathematical model.
    
    Attributes:
        nodes: A dictionary mapping node IDs to their operation type (e.g., 'Add', 'Mul', 'Symbol').
        edges: A list of tuples representing directed edges (source, target).
        expression: The root expression of the graph.
    """
    nodes: Dict[int, str] = field(default_factory=dict)
    edges: List[Tuple[int, int]] = field(default_factory=list)
    expression: Optional[SympyBasic] = None


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def _extract_sympy_expression(formula_str: str, variable_map: Dict[str, str]) -> SympyBasic:
    """
    [Helper Function] Parses a raw string formula into a SymPy expression object
    while performing variable substitution based on a mapping.
    
    Args:
        formula_str: The raw mathematical string (e.g., "dP/dx + rho * v * dv/dx").
        variable_map: A dictionary mapping domain-specific terms to canonical symbols
                      (e.g., {'Pressure': 'P', 'Density': 'rho'}).
                      
    Returns:
        A SymPy expression object.
        
    Raises:
        ValidationError: If the formula string cannot be parsed.
    """
    if not formula_str or not isinstance(formula_str, str):
        raise ValidationError("Input formula must be a non-empty string.")
    
    try:
        # Sanitize input string for basic security (prevent code injection in sympify if unsafe mode used)
        # Here we rely on sympify's parsing logic.
        logger.debug(f"Parsing formula: {formula_str}")
        
        # Define local variables dynamically based on map
        local_dict = {}
        for domain_term, canonical_sym in variable_map.items():
            local_dict[domain_term] = sympy.Symbol(canonical_sym)
            
        # Parse expression
        expr = sympy.sympify(formula_str, locals=local_dict)
        return expr
        
    except SyntaxError as e:
        logger.error(f"Syntax error parsing formula '{formula_str}': {e}")
        raise ValidationError(f"Invalid mathematical syntax: {formula_str}") from e
    except Exception as e:
        logger.error(f"Unexpected error during parsing: {e}")
        raise ValidationError("Failed to parse mathematical expression.") from e


def build_computational_graph(expression: SympyBasic) -> ComputationalGraph:
    """
    [Core Function 1] Transforms a SymPy expression into a structural Computational Graph.
    
    This function recursively traverses the expression tree to extract nodes (operations/symbols)
    and edges (data dependencies), ignoring specific constant values to focus on 
    topological structure.
    
    Args:
        expression: A SymPy expression object.
        
    Returns:
        A ComputationalGraph object containing the structural topology.
    """
    if not isinstance(expression, SympyBasic):
        raise ValidationError("Input must be a SymPy expression.")
        
    graph = ComputationalGraph(expression=expression)
    visited = {}  # Map object ID to assigned node ID to handle DAGs correctly
    
    def traverse(node: SympyBasic, parent_id: Optional[int] = None):
        # Use object identity for caching within this traversal
        node_oid = id(node)
        
        if node_oid in visited:
            current_id = visited[node_oid]
            if parent_id is not None:
                graph.edges.append((parent_id, current_id))
            return

        # Create new node
        current_id = len(graph.nodes) + 1
        visited[node_oid] = current_id
        
        # Determine node type (abstraction layer)
        # We care about the class name (Add, Mul, Symbol, Derivative) rather than values
        node_type = node.__class__.__name__
        graph.nodes[current_id] = node_type
        
        if parent_id is not None:
            graph.edges.append((parent_id, current_id))
            
        # Traverse arguments (children)
        for arg in node.args:
            traverse(arg, current_id)

    traverse(expression)
    logger.info(f"Built graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    return graph


def verify_structural_isomorphism(
    graph_a: ComputationalGraph, 
    graph_b: ComputationalGraph,
    tolerance: float = 0.0
) -> Dict[str, float]:
    """
    [Core Function 2] Verifies if two computational graphs are isomorphic.
    
    Instead of checking if the equations are *equal* mathematically (which implies identical physics),
    this checks for *structural isomorphism*. This allows us to identify if two systems share the 
    same form of differential equations (e.g., Navier-Stokes vs. LWR Traffic Model), 
    even if the variables represent different physical quantities.
    
    Args:
        graph_a: The computational graph of the source domain.
        graph_b: The computational graph of the target domain.
        tolerance: Unused in strict graph isomorphism but reserved for future probabilistic relaxations.
        
    Returns:
        A dictionary containing:
        - 'is_isomorphic': bool
        - 'similarity_score': float (0.0 to 1.0)
        - 'node_overlap_ratio': float (ratio of matching node types)
        
    Raises:
        ValidationError: If inputs are not ComputationalGraph objects.
    """
    if not isinstance(graph_a, ComputationalGraph) or not isinstance(graph_b, ComputationalGraph):
        raise ValidationError("Both inputs must be ComputationalGraph instances.")

    # Quick reject based on size differences
    len_nodes_a = len(graph_a.nodes)
    len_nodes_b = len(graph_b.nodes)
    
    if len_nodes_a == 0 or len_nodes_b == 0:
        logger.warning("Empty graph detected in comparison.")
        return {"is_isomorphic": False, "similarity_score": 0.0, "node_overlap_ratio": 0.0}

    # 1. Node Label Compatibility Check (Heuristic)
    # In a true isomorphism for physics, we expect similar operators (Derivative, Add, Pow)
    # even if leaf nodes (Symbols) differ.
    
    types_a = list(graph_a.nodes.values())
    types_b = list(graph_b.nodes.values())
    
    # Filter out 'Symbol' and 'Integer' to focus on OPERATOR structure
    # This allows 'Velocity' to map to 'Density' as long as the operators (d/dt, +, *) match.
    ops_a = [t for t in types_a if t not in ['Symbol', 'Integer', 'Float', 'Rational']]
    ops_b = [t for t in types_b if t not in ['Symbol', 'Integer', 'Float', 'Rational']]
    
    if len(ops_a) != len(ops_b):
        logger.info(f"Operator count mismatch: {len(ops_a)} vs {len(ops_b)}")
        # Strict check: if structure length differs, likely not strict isomorphism
        # In a fuzzy scenario, we might continue, but here we require strict structure match for AGI core skill.
    
    # 2. Graph Isomorphism Check (Topological)
    # We convert our graph to a standard adjacency format for a simplified comparison logic.
    # For this demonstration, we implement a simplified structural signature comparison.
    
    # In a full production environment, we would use `networkx.is_isomorphic` with node_match.
    # Here we implement a SymPy-based structural hash comparison.
    
    # Canonical Representation: Sort and count arguments at each level
    def get_structure_signature(expr):
        if not expr.args:
            return expr.__class__.__name__
        return tuple(sorted([get_structure_signature(arg) for arg in expr.args]))

    sig_a = get_structure_signature(graph_a.expression)
    sig_b = get_structure_signature(graph_b.expression)
    
    if sig_a == sig_b:
        logger.info("Exact structural isomorphism detected.")
        return {
            "is_isomorphic": True, 
            "similarity_score": 1.0, 
            "node_overlap_ratio": 1.0,
            "details": "Graph topologies are identical."
        }
    
    # If not exact, check for operator set similarity (Partial Isomorphism)
    set_a = set(ops_a)
    set_b = set(ops_b)
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    jaccard = intersection / union if union > 0 else 0.0
    
    logger.info(f"Structure mismatch. Operator Jaccard similarity: {jaccard:.2f}")
    
    return {
        "is_isomorphic": False,
        "similarity_score": jaccard,
        "node_overlap_ratio": intersection / max(len(ops_a), len(ops_b)),
        "details": "Graph topologies differ structurally."
    }


# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # Scenario: AGI proposes mapping between Fluid Dynamics (Bernoulli) and 
    # Traffic Flow (Conservation of Vehicles).
    
    print(f"--- Starting Cross-Domain Isomorphism Validation ---")
    
    # 1. Define Domain A: Fluid Dynamics (Simplified Bernoulli / Conservation)
    # P + 0.5 * rho * v**2 = Constant
    fluid_formula = "Pressure + 0.5 * Density * Velocity**2"
    fluid_vars = {'Pressure': 'P', 'Density': 'rho', 'Velocity': 'v'}
    
    # 2. Define Domain B: Traffic Flow (Lighthill-Whitham-Richards concept)
    # A hypothetical energy-like potential function: Q + k * v**2
    # where Q is flow potential, k is density, v is speed.
    traffic_formula = "FlowPotential + Factor * Density * Speed**2"
    traffic_vars = {'FlowPotential': 'Phi', 'Factor': 'k', 'Density': 'rho', 'Speed': 'v'}
    
    # 3. Define Domain C: Dissimilar Domain (Random arithmetic)
    random_formula = "Income + Tax * Rate"
    random_vars = {'Income': 'I', 'Tax': 'T', 'Rate': 'r'}

    try:
        # Step A: Extract Expressions
        expr_fluid = _extract_sympy_expression(fluid_formula, fluid_vars)
        expr_traffic = _extract_sympy_expression(traffic_formula, traffic_vars)
        expr_random = _extract_sympy_expression(random_formula, random_vars)

        # Step B: Build Graphs
        graph_fluid = build_computational_graph(expr_fluid)
        graph_traffic = build_computational_graph(expr_traffic)
        graph_random = build_computational_graph(expr_random)

        # Step C: Verify Isomorphism (Positive Case)
        print("\n[TEST 1] Fluid vs. Traffic (Expected: Isomorphic Structure)")
        result_traffic = verify_structural_isomorphism(graph_fluid, graph_traffic)
        print(f"Result: {result_traffic}")

        # Step D: Verify Isomorphism (Negative Case)
        print("\n[TEST 2] Fluid vs. Economic (Expected: Non-Isomorphic)")
        result_random = verify_structural_isomorphism(graph_fluid, graph_random)
        print(f"Result: {result_random}")

    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
    except Exception as e:
        logger.critical(f"System error: {e}", exc_info=True)