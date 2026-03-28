"""
Module: auto_cross_domain_isomorphism_lens.py
Description: Implements the 'Cross-Domain Isomorphism Lens' for AGI systems.
             This module serves as a 'Meta-Structure Extractor', identifying
             dynamic structural similarities between disparate domains rather than
             mere semantic resemblance.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Callable
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IsomorphismLens")

@dataclass
class DynamicStructure:
    """
    Represents the extracted 'skeleton' or dynamic structure of a problem/solution.
    
    Attributes:
        domain (str): The domain the structure belongs to (e.g., 'thermodynamics', 'economics').
        inputs (List[str]): Key input variables or stimuli.
        outputs (List[str]): Key output variables or results.
        feedback_loops (List[str]): Description of regulatory or reinforcing loops.
        entropy_trend (str): Direction of entropy ('increasing', 'decreasing', 'stable').
        core_dynamics (str): Abstract description of the mechanism (e.g., 'gradient descent').
        solution_blueprint (Dict): The actionable part of the solution to be migrated.
    """
    domain: str
    inputs: List[str]
    outputs: List[str]
    feedback_loops: List[str]
    entropy_trend: str
    core_dynamics: str
    solution_blueprint: Dict[str, Any]

@dataclass
class IsomorphismMatch:
    """
    Represents a match between a source problem and a target historical structure.
    """
    source_id: str
    target_structure: DynamicStructure
    similarity_score: float
    mapping_suggestions: Dict[str, str]

class IsomorphismLensError(Exception):
    """Custom exception for errors in the isomorphism mapping process."""
    pass

def _calculate_vector_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Helper function: Calculates Cosine Similarity between two vectors.
    
    Args:
        vec_a (List[float]): First vector.
        vec_b (List[float]): Second vector.
        
    Returns:
        float: Similarity score between 0.0 and 1.0.
        
    Raises:
        ValueError: If vectors are empty or of different lengths.
    """
    if not vec_a or not vec_b:
        raise ValueError("Vectors cannot be empty")
    if len(vec_a) != len(vec_b):
        # In a real AGI system, we might use embedding padding or projection here.
        # For this skill, we enforce strict dimension matching or return 0.
        logger.warning(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

def extract_dynamic_structure(problem_context: Dict[str, Any]) -> DynamicStructure:
    """
    Core Function 1: Meta-Structure Extractor.
    
    Analyzes a raw problem description to extract its 'Dynamic Structure' 
    (kinematics, constraints, entropy).
    
    Args:
        problem_context (Dict): Raw data describing the problem. 
                                Expected keys: 'domain', 'description', 
                                'observed_inputs', 'observed_outputs', 'behavior'.
                                
    Returns:
        DynamicStructure: The abstracted skeleton of the problem.
        
    Example:
        >>> ctx = {
        ...     "domain": "traffic_flow",
        ...     "description": "Cars moving through a bottleneck, speed drops as density increases.",
        ...     "observed_inputs": ["cars_in", "time"],
        ...     "observed_outputs": ["cars_out", "avg_speed"],
        ...     "behavior": "negative_feedback"
        ... }
        >>> structure = extract_dynamic_structure(ctx)
    """
    logger.info(f"Extracting dynamic structure from domain: {problem_context.get('domain')}")
    
    # Validation
    required_keys = ['domain', 'observed_inputs', 'observed_outputs']
    for key in required_keys:
        if key not in problem_context:
            raise IsomorphismLensError(f"Missing required key in context: {key}")

    # Abstracting Entropy/Chaos Direction
    # Heuristic: If behavior mentions 'decay', 'friction', or 'dissipation', entropy increases.
    desc = str(problem_context.get('description', '')).lower()
    if any(k in desc for k in ['decay', 'heat', 'random', 'chaos', 'expand']):
        entropy = 'increasing'
    elif any(k in desc for k in ['organize', 'build', 'structure', 'converge']):
        entropy = 'decreasing'
    else:
        entropy = 'stable'

    # Abstracting Feedback Loops
    feedback = []
    behavior = problem_context.get('behavior', '')
    if 'oscillate' in behavior:
        feedback.append('delayed_negative_feedback')
    elif 'stable' in behavior:
        feedback.append('immediate_negative_feedback')
    elif 'explode' in behavior or 'viral' in behavior:
        feedback.append('positive_feedback')

    # Identify Core Dynamics (The "Physics" of the problem)
    # In a full AGI system, this would use an LLM or a physics engine simulation.
    # Here we use a rule-based proxy for the "Analogy" cognitive step.
    core_dynamics = "unknown_interaction"
    if 'bottleneck' in desc or 'limit' in desc:
        core_dynamics = "saturation_dynamics"
    elif 'gradient' in desc or 'flow' in desc:
        core_dynamics = "potential_flow"
    
    return DynamicStructure(
        domain=problem_context['domain'],
        inputs=problem_context['observed_inputs'],
        outputs=problem_context['observed_outputs'],
        feedback_loops=feedback if feedback else ['none_identified'],
        entropy_trend=entropy,
        core_dynamics=core_dynamics,
        solution_blueprint=problem_context.get('proposed_solution', {})
    )

def find_isomorphic_solution(
    source_structure: DynamicStructure, 
    historical_db: List[DynamicStructure],
    threshold: float = 0.7
) -> Optional[IsomorphismMatch]:
    """
    Core Function 2: Cross-Domain Mapper.
    
    Searches the historical database for a structure that shares the same 
    'kinematics' (dynamics) as the source problem, ignoring the specific content.
    
    Args:
        source_structure (DynamicStructure): The problem we need to solve.
        historical_db (List[DynamicStructure]): Library of previously solved problems.
        threshold (float): Minimum similarity score to accept a match (0.0 to 1.0).
        
    Returns:
        Optional[IsomorphismMatch]: The best matching structure and migration map, or None.
        
    Example:
        >>> match = find_isomorphic_solution(current_problem_structure, knowledge_base)
        >>> if match:
        ...     print(f"Found solution in domain: {match.target_structure.domain}")
    """
    if not historical_db:
        logger.warning("Historical database is empty.")
        return None

    logger.info(f"Scanning {len(historical_db)} historical structures for isomorphism...")
    
    best_match: Optional[IsomorphismMatch] = None
    highest_score = 0.0

    # Feature Vectorization for Comparison
    # We convert qualitative properties into comparable features.
    # Features: [Entropy Match (0/1), Feedback Match (0-1), Dynamics Match (0/1), IO Count Similarity]
    
    for candidate in historical_db:
        # 1. Structural Entropy Check
        entropy_sim = 1.0 if source_structure.entropy_trend == candidate.entropy_trend else 0.0
        
        # 2. Dynamics Check (The most critical part of 'Analogy')
        dynamics_sim = 1.0 if source_structure.core_dynamics == candidate.core_dynamics else 0.0
        
        # 3. Feedback Loop Similarity
        # Simple Jaccard index of loop descriptions
        s_loops = set(source_structure.feedback_loops)
        c_loops = set(candidate.feedback_loops)
        if not s_loops and not c_loops:
            loop_sim = 1.0
        elif not s_loops or not c_loops:
            loop_sim = 0.0
        else:
            loop_sim = len(s_loops.intersection(c_loops)) / len(s_loops.union(c_loops))
            
        # 4. I/O Complexity Similarity (Topological similarity)
        # We compare the complexity (number of nodes) rather than the content
        io_diff = abs(len(source_structure.inputs) - len(candidate.inputs)) + \
                  abs(len(source_structure.outputs) - len(candidate.outputs))
        io_sim = 1.0 / (1.0 + io_diff) # Dampened similarity
        
        # Weighted Total Score
        # We prioritize Core Dynamics and Feedback loops for functional mapping
        # Weights: Dynamics(0.4), Feedback(0.3), Entropy(0.2), IO(0.1)
        vector_a = [dynamics_sim, loop_sim, entropy_sim, io_sim]
        # Ideal vector is [1, 1, 1, 1], so we can use dot product or simple weighted sum
        score = (vector_a[0] * 0.4 + vector_a[1] * 0.3 + vector_a[2] * 0.2 + vector_a[3] * 0.1)
        
        if score > highest_score:
            highest_score = score
            # Create variable mapping suggestions based on I/O position
            mapping = {}
            for i, inp in enumerate(source_structure.inputs):
                if i < len(candidate.inputs):
                    mapping[inp] = candidate.inputs[i]
            
            best_match = IsomorphismMatch(
                source_id=source_structure.domain,
                target_structure=candidate,
                similarity_score=score,
                mapping_suggestions=mapping
            )

    if highest_score >= threshold:
        logger.info(f"Isomorphism found with score {highest_score:.2f} in domain '{best_match.target_structure.domain}'")
        return best_match
    else:
        logger.info("No sufficient isomorphic structure found.")
        return None

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Simulate a Knowledge Base (History)
    knowledge_base = [
        DynamicStructure(
            domain="Hydraulics",
            inputs=["water_in", "pipe_width"],
            outputs=["water_out", "pressure"],
            feedback_loops=["immediate_negative_feedback"],
            entropy_trend="stable",
            core_dynamics="saturation_dynamics",
            solution_blueprint={"strategy": "Widen the bottleneck or reduce input flow"}
        ),
        DynamicStructure(
            domain="Economics",
            inputs=["capital", "labor"],
            outputs=["gdp"],
            feedback_loops=["positive_feedback"],
            entropy_trend="increasing",
            core_dynamics="potential_flow",
            solution_blueprint={"strategy": "Invest in high multiplier areas"}
        )
    ]

    # 2. Define a New Problem (Source)
    # Problem: A server is getting overloaded requests (Input), causing latency (Output).
    # Analysis: As load increases, performance drops until crash.
    current_problem_ctx = {
        "domain": "Server_Mgmt",
        "description": "Handling high request volume causing a bottleneck in the CPU queue.",
        "observed_inputs": ["requests", "cpu_cores"],
        "observed_outputs": ["latency", "throughput"],
        "behavior": "stable_oscillation", # System tries to stabilize but lags
        "proposed_solution": {} # Unknown initially
    }

    try:
        print("--- Starting Cross-Domain Isomorphism Search ---")
        
        # Step A: Extract Structure
        source_struct = extract_dynamic_structure(current_problem_ctx)
        print(f"Extracted Structure: {source_struct.core_dynamics}")
        
        # Step B: Find Match
        match_result = find_isomorphic_solution(source_struct, knowledge_base, threshold=0.5)
        
        if match_result:
            print("\n>>> SOLUTION MIGRATION SUCCESSFUL <<<")
            print(f"Matched Domain: {match_result.target_structure.domain}")
            print(f"Similarity: {match_result.similarity_score:.2f}")
            print(f"Variable Mapping: {match_result.mapping_suggestions}")
            print(f"Solution Skeleton: {match_result.target_structure.solution_blueprint}")
            
            # Translate solution back
            strategy = match_result.target_structure.solution_blueprint['strategy']
            print(f"\nTranslated Advice: '{strategy}'")
            print("(Interpret 'Widen bottleneck' as 'Scale vertically' or 'Load Balance')")
        else:
            print("\nNo suitable historical model found for migration.")

    except IsomorphismLensError as e:
        logger.error(f"System Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")