"""
Module: Semantic Incremental Inference Engine
Description: Implements a semantic incremental reasoning engine inspired by compiler theory.
             It mimics "incremental compilation" to optimize long-context LLM interactions.
             Instead of recalculating the full context attention, it identifies impacted
             "logic branches" (semantic nodes) and only re-reasoning those parts.
             
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticIncrementalEngine")

class NodeStatus(Enum):
    """Status of a semantic node in the reasoning graph."""
    CLEAN = "clean"         # Compiled and valid
    DIRTY = "dirty"         # Needs re-compilation
    DETACHED = "detached"   # Orphaned node

@dataclass
class SemanticNode:
    """
    Represents a unit of reasoning (similar to a compiled object file or AST node).
    
    Attributes:
        id: Unique identifier (hash of content).
        content: The text content of this reasoning step.
        dependencies: Set of Node IDs this node depends on.
        compiled_result: The output/reasoning result (simulated LLM response).
        checksum: Hash of the content to detect changes.
        token_cost: Estimated tokens used for this step.
    """
    id: str
    content: str
    dependencies: Set[str] = field(default_factory=set)
    compiled_result: str = ""
    checksum: str = field(init=False)
    token_cost: int = 0
    status: NodeStatus = NodeStatus.DIRTY

    def __post_init__(self):
        """Calculate checksum after initialization."""
        self.checksum = self._generate_checksum(self.content)

    @staticmethod
    def _generate_checksum(content: str) -> str:
        """Generates a SHA256 checksum for the content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def update_content(self, new_content: str) -> bool:
        """
        Updates content and invalidates status if changed.
        Returns True if content changed, False otherwise.
        """
        new_check = self._generate_checksum(new_content)
        if new_check != self.checksum:
            logger.debug(f"Node {self.id} content changed. Marking DIRTY.")
            self.content = new_content
            self.checksum = new_check
            self.status = NodeStatus.DIRTY
            self.compiled_result = ""  # Clear cache
            return True
        return False

class IncrementalReasoningEngine:
    """
    The core engine managing the dependency graph and incremental reasoning.
    
    Input Format:
        - User inputs are strings.
        - System context is a structured graph of SemanticNodes.
    Output Format:
        - Final reasoned response (string).
        - Metrics regarding token savings.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initializes the engine.
        
        Args:
            similarity_threshold: Threshold for semantic diff (mocked in this logic).
        """
        self.nodes: Dict[str, SemanticNode] = {}
        self.root_id: Optional[str] = None
        self.similarity_threshold = similarity_threshold
        logger.info("Semantic Incremental Reasoning Engine initialized.")

    def _find_impacted_set(self, changed_node_ids: Set[str]) -> Set[str]:
        """
        [Helper Function] Traverses the graph to find all dependent nodes 
        that need re-compilation (propagation of dirty status).
        
        Args:
            changed_node_ids: Set of node IDs that were modified.
            
        Returns:
            Set of all node IDs that need updating (transitive closure).
        """
        impacted = set(changed_node_ids)
        queue = list(changed_node_ids)
        
        # BFS to find dependents
        while queue:
            current_id = queue.pop(0)
            for node_id, node in self.nodes.items():
                if current_id in node.dependencies:
                    if node_id not in impacted:
                        impacted.add(node_id)
                        queue.append(node_id)
                        logger.info(f"Propagation: Node {node_id} marked impacted by {current_id}")
        
        return impacted

    def add_or_update_node(self, node_id: str, content: str, dependencies: List[str] = None) -> bool:
        """
        [Core Function 1] Adds a new reasoning node or updates an existing one.
        Acts as the 'Lexer/Parser' stage.
        
        Args:
            node_id: Logical ID for the node.
            content: The text/prompt segment.
            dependencies: List of node IDs this logic depends on.
            
        Returns:
            True if the graph structure changed significantly.
        """
        if dependencies is None:
            dependencies = []
            
        # Validate dependencies exist
        for dep in dependencies:
            if dep not in self.nodes:
                logger.error(f"Dependency {dep} not found for node {node_id}")
                raise ValueError(f"Missing dependency: {dep}")

        is_new = node_id not in self.nodes
        changed = False

        if is_new:
            node = SemanticNode(
                id=node_id, 
                content=content, 
                dependencies=set(dependencies)
            )
            self.nodes[node_id] = node
            logger.info(f"Created new node: {node_id}")
            changed = True
        else:
            node = self.nodes[node_id]
            # Check content change
            content_changed = node.update_content(content)
            # Check dependency change
            new_deps = set(dependencies)
            if new_deps != node.dependencies:
                logger.info(f"Dependencies changed for {node_id}")
                node.dependencies = new_deps
                node.status = NodeStatus.DIRTY
                changed = True
            elif content_changed:
                changed = True

        if not self.root_id and not dependencies:
            self.root_id = node_id

        return changed

    def incremental_compile(self) -> Dict[str, Any]:
        """
        [Core Function 2] Executes the incremental reasoning process.
        Only re-runs the LLM inference (simulated) for dirty nodes.
        
        Returns:
            A report containing the final result and performance metrics.
        """
        start_time = time.time()
        
        # 1. Identify dirty nodes
        dirty_nodes = {nid for nid, node in self.nodes.items() if node.status == NodeStatus.DIRTY}
        
        if not dirty_nodes:
            logger.info("No changes detected. Serving from cache.")
            return {
                "status": "cached",
                "result": self.nodes[self.root_id].compiled_result if self.root_id else "",
                "tokens_saved": sum(n.token_cost for n in self.nodes.values()),
                "processing_time_ms": 0
            }

        # 2. Calculate impact scope
        impacted_ids = self._find_impacted_set(dirty_nodes)
        logger.info(f"Incremental compilation required for {len(impacted_ids)} nodes.")

        total_tokens_used = 0
        full_graph_tokens = 0

        # 3. Re-compile (Mock LLM Call)
        # In a real scenario, this would involve constructing specific prompts
        # with context from clean dependencies.
        for nid in impacted_ids:
            node = self.nodes[nid]
            
            # Simulation: Token cost is approx word count
            input_len = len(node.content.split())
            dep_context_len = sum(len(self.nodes[d].content.split()) for d in node.dependencies)
            
            current_cost = input_len + dep_context_len
            full_cost = sum(len(n.content.split()) for n in self.nodes.values()) # Simulate full context cost
            
            # Mock Inference
            node.compiled_result = f"[Processed({nid})]: {node.content[:20]}..."
            node.status = NodeStatus.CLEAN
            node.token_cost = current_cost
            
            total_tokens_used += current_cost
            full_graph_tokens += full_cost # Simplified accumulation for demo
            
            logger.debug(f"Re-compiled node {nid}. Cost: {current_cost} tokens.")

        # 4. Finalize
        processing_time = (time.time() - start_time) * 1000
        savings = full_graph_tokens - total_tokens_used
        
        final_result = "Aggregated Result: " + " -> ".join(
            [self.nodes[nid].compiled_result for nid in self.nodes if not self.nodes[nid].dependencies]
        )

        return {
            "status": "success",
            "result": final_result,
            "nodes_recompiled": len(impacted_ids),
            "total_nodes": len(self.nodes),
            "tokens_used_incremental": total_tokens_used,
            "estimated_tokens_full": full_graph_tokens,
            "efficiency_gain": f"{(savings / full_graph_tokens) * 100:.2f}%" if full_graph_tokens > 0 else "0%",
            "processing_time_ms": round(processing_time, 2)
        }

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Initialize Engine
    engine = IncrementalReasoningEngine()

    print("--- Step 1: Initial Reasoning Graph Construction ---")
    # Building the logic branches
    engine.add_or_update_node("concept_A", "Define User Authentication Logic", [])
    engine.add_or_update_node("concept_B", "Define Database Schema for Users", [])
    # Concept C depends on A and B
    engine.add_or_update_node(
        "concept_C", 
        "Implement Login API using Auth and DB Schema", 
        ["concept_A", "concept_B"]
    )

    # First run (Full compilation)
    report_1 = engine.incremental_compile()
    print(f"Report 1: {report_1}")

    print("\n--- Step 2: Incremental Update (Hot Reload) ---")
    # Modify only Concept A (Authentication Logic)
    # Concept B remains clean. Concept C depends on A, so it must be invalidated.
    engine.add_or_update_node(
        "concept_A", 
        "Define OAuth 2.0 Authentication Logic (Updated)", 
        []
    )

    # Second run (Incremental compilation)
    report_2 = engine.incremental_compile()
    print(f"Report 2: {report_2}")
    
    # Verify that only A and C were processed
    assert report_2['nodes_recompiled'] == 2
    print("\nTest Passed: Incremental logic correctly identified dependencies.")

    print("\n--- Step 3: No Changes (Cache Hit) ---")
    report_3 = engine.incremental_compile()
    print(f"Report 3: {report_3}")
    assert report_3['status'] == 'cached'