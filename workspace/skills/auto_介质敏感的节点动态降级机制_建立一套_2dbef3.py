"""
Module: auto_context_friction_degradation.py

This module implements a 'Medium-Sensitive Node Dynamic Degradation Mechanism'.
It provides a system to evaluate 'Context Friction' when attempting to migrate
high-level AI Skills (nodes) from one domain (e.g., Python algorithms) to another
(e.g., Java or Embedded C).

When the friction (environmental constraints, library differences) is too high,
the system automatically degrades 'High-Level Reality Nodes' into 'Basic Atomic Nodes'
for recombination in the target medium.
"""

import logging
import enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContextFrictionSystem")

class DomainType(enum.Enum):
    """Enumeration of possible operational domains."""
    PYTHON = "python"
    JAVA = "java"
    EMBEDDED_C = "embedded_c"
    UNSUPPORTED = "unsupported"

class NodeType(enum.Enum):
    """Classification of the node complexity."""
    HIGH_LEVEL_REALITY = "high_level_reality"  # Complex, context-dependent
    ATOMIC = "atomic"                          # Basic, fundamental logic
    FAILED = "failed"                          # Cannot be processed

@dataclass
class SkillNode:
    """
    Represents a unit of skill or logic to be transferred.
    
    Attributes:
        id: Unique identifier for the node.
        content: The logic or code snippet.
        source_domain: The domain this node originates from.
        dependencies: List of external libraries or hardware features required.
        complexity_score: A float representing how complex the node is (0.0 to 1.0).
    """
    id: str
    content: str
    source_domain: DomainType
    dependencies: List[str] = field(default_factory=list)
    complexity_score: float = 0.5

    def __post_init__(self):
        """Validate data after initialization."""
        if not 0.0 <= self.complexity_score <= 1.0:
            raise ValueError(f"Complexity score must be between 0.0 and 1.0 for node {self.id}")

@dataclass
class EnvironmentProfile:
    """
    Represents the target environment constraints.
    
    Attributes:
        domain: The target domain type.
        available_libs: Set of available libraries/features.
        max_complexity: The maximum complexity score the environment can handle for direct ports.
        memory_kb: Available memory in KB (optional, for embedded contexts).
    """
    domain: DomainType
    available_libs: set = field(default_factory=set)
    max_complexity: float = 0.8
    memory_kb: Optional[int] = None

def _calculate_medium_hardness(source: DomainType, target: DomainType) -> float:
    """
    [Helper Function] Calculates the base hardness of the target medium relative to the source.
    
    Hardness represents the resistance to direct porting. 
    0.0 = Identical environments (Fluid).
    1.0 = Completely incompatible environments (Solid).
    
    Args:
        source: The source domain.
        target: The target domain.
        
    Returns:
        float: A hardness coefficient between 0.0 and 1.0.
    """
    if source == target:
        return 0.0
    
    # Define inherent friction between distinct ecosystems
    friction_map = {
        (DomainType.PYTHON, DomainType.JAVA): 0.4,
        (DomainType.PYTHON, DomainType.EMBEDDED_C): 0.9, # High friction
        (DomainType.JAVA, DomainType.PYTHON): 0.3,
    }
    
    hardness = friction_map.get((source, target), 0.7) # Default to high friction
    logger.debug(f"Base hardness from {source.value} to {target.value}: {hardness}")
    return hardness

def evaluate_context_friction(node: SkillNode, target_env: EnvironmentProfile) -> float:
    """
    [Core Function 1] Evaluates the total 'Context Friction' for migrating a node.
    
    Friction is calculated based on:
    1. Base Medium Hardness (Language barrier).
    2. Dependency mismatch (Missing libraries).
    3. Complexity overhead.
    
    Args:
        node: The skill node to be migrated.
        target_env: The target environment profile.
        
    Returns:
        float: A friction score from 0.0 (no friction) to >1.0 (extreme friction).
    
    Raises:
        ValueError: If inputs are invalid.
    """
    if not node.content:
        raise ValueError("Node content cannot be empty")

    logger.info(f"Evaluating friction for Node '{node.id}' targeting '{target_env.domain.value}'")
    
    # 1. Base Medium Hardness
    base_hardness = _calculate_medium_hardness(node.source_domain, target_env.domain)
    
    # 2. Dependency Friction
    missing_deps = set(node.dependencies) - target_env.available_libs
    # Each missing dependency adds 0.15 friction points
    dep_friction = len(missing_deps) * 0.15
    
    # 3. Complexity Penalty (Higher complexity nodes are harder to port to constrained systems)
    complexity_penalty = 0.0
    if node.complexity_score > target_env.max_complexity:
        complexity_penalty = (node.complexity_score - target_env.max_complexity) * 0.5

    total_friction = base_hardness + dep_friction + complexity_penalty
    
    logger.info(f"Friction Analysis: Base={base_hardness:.2f}, Deps={dep_friction:.2f}, Complexity={complexity_penalty:.2f} -> Total={total_friction:.2f}")
    return total_friction

def degrade_node(node: SkillNode, target_env: EnvironmentProfile, friction_threshold: float = 1.0) -> Tuple[List[SkillNode], NodeType]:
    """
    [Core Function 2] Attempts to port a node, or degrades it into atomic components if friction is too high.
    
    If friction < threshold: 
        Returns the node marked as HIGH_LEVEL_REALITY (direct port).
    If friction >= threshold:
        Simulates decomposition into ATOMIC nodes (simplified logic units).
        
    Args:
        node: The original skill node.
        target_env: The target environment.
        friction_threshold: The limit above which degradation is triggered.
        
    Returns:
        Tuple[List[SkillNode], NodeType]: A list of resulting nodes (either the original or decomposed) 
                                          and the determined node type.
    """
    if friction_threshold < 0:
        raise ValueError("Friction threshold cannot be negative")

    current_friction = evaluate_context_friction(node, target_env)
    
    if current_friction < friction_threshold:
        logger.info(f"Friction {current_friction:.2f} below threshold. Passing through High-Level Node.")
        return [node], NodeType.HIGH_LEVEL_REALITY
    
    logger.warning(f"High Context Friction detected ({current_friction:.2f}). Initiating Degradation Protocol.")
    
    # Simulation of Decomposition Logic
    # In a real AGI system, this would use an LLM to break 'Sort Algorithm' into 
    # 'Loop', 'Compare', 'Swap' logic blocks.
    # Here we simulate splitting by creating generic atomic nodes.
    
    atomic_nodes = []
    
    # Create an atomic node for the core logic concept
    atomic_nodes.append(
        SkillNode(
            id=f"{node.id}_atomic_core",
            content=f"ATOMIC_LOGIC_CORE({node.id})",
            source_domain=target_env.domain, # Adapted to target
            dependencies=[], # Atomics should ideally have no external deps
            complexity_score=0.1
        )
    )
    
    # If the original node was highly complex, split off a control structure node
    if node.complexity_score > 0.6:
        atomic_nodes.append(
            SkillNode(
                id=f"{node.id}_atomic_ctrl",
                content=f"ATOMIC_CONTROL_FLOW({node.id})",
                source_domain=target_env.domain,
                dependencies=[],
                complexity_score=0.1
            )
        )
        
    return atomic_nodes, NodeType.ATOMIC

# ==========================================================
# Usage Example
# ==========================================================

if __name__ == "__main__":
    # 1. Define a High-Level Python Skill Node (e.g., a complex Pandas operation)
    python_node = SkillNode(
        id="data_cleaner_01",
        content="df.dropna(subset=['price']).groupby('category').mean()",
        source_domain=DomainType.PYTHON,
        dependencies=["pandas", "numpy"],
        complexity_score=0.7
    )

    # 2. Define a constrained Target Environment (Embedded C on a microcontroller)
    embedded_env = EnvironmentProfile(
        domain=DomainType.EMBEDDED_C,
        available_libs={"stdio", "stdlib"}, # No pandas here!
        max_complexity=0.3,
        memory_kb=64
    )

    print("-" * 50)
    print(f"Attempting to transfer Node: {python_node.id}")
    print(f"Source: {python_node.source_domain.value} -> Target: {embedded_env.domain.value}")
    print("-" * 50)

    # 3. Execute Degradation Mechanism
    try:
        resulting_nodes, op_type = degrade_node(python_node, embedded_env, friction_threshold=0.8)
        
        print(f"Operation Result: {op_type.value}")
        print("Generated Nodes:")
        for n in resulting_nodes:
            print(f" - ID: {n.id} | Content: {n.content} | Deps: {n.dependencies}")
            
    except ValueError as e:
        logger.error(f"Processing failed: {e}")