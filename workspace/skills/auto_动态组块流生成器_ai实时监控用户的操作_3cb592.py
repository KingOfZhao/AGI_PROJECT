"""
Module: auto_dynamic_chunk_flow_generator
Description: AGI Skill for dynamic cognitive chunking. Monitors user interaction streams,
             identifies high-frequency atomic data clusters, and aggregates them into
             'Cognitive Chunks' (materialized views) to reduce cognitive load and induce flow.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DynamicChunkFlowGenerator")


class DataClusterType(Enum):
    """Enumeration of possible data cluster types for semantic chunking."""
    TASK_GROUP = "TASK_GROUP"
    CONTEXT_BLOCK = "CONTEXT_BLOCK"
    SPRINT_PHASE = "SPRINT_PHASE"
    UNKNOWN = "UNKNOWN"


@dataclass
class AtomicAction:
    """Represents a single atomic user action."""
    action_id: str
    timestamp: float
    target_entity: str  # e.g., "task_123", "file_readme.md"
    context: str        # e.g., "project_alpha", "debugging_session"
    frequency_weight: float = 1.0


@dataclass
class CognitiveChunk:
    """Represents an aggregated chunk of data presented to the user."""
    chunk_id: str
    semantic_label: str
    cluster_type: DataClusterType
    contained_entities: Set[str]
    priority_score: float
    created_at: float = field(default_factory=time.time)


class DynamicChunkFlowGenerator:
    """
    AI System that monitors user operations and dynamically generates cognitive chunks.
    
    This system analyzes streams of atomic actions to identify patterns. When a pattern
    (cluster) is identified as high-frequency, it is aggregated into a single semantic
    block to simplify the user interface and support focus.
    
    Attributes:
        window_size (int): The sliding window size for analyzing recent actions.
        action_buffer (deque): Buffer holding recent atomic actions.
        active_chunks (Dict[str, CognitiveChunk]): Currently active aggregated chunks.
        entity_graph (Dict[str, Set[str]]): Co-occurrence graph of entities.
    
    Usage Example:
        >>> generator = DynamicChunkFlowGenerator(window_size=50)
        >>> generator.ingest_action("a1", "task_1", "sprint_backend")
        >>> generator.ingest_action("a2", "task_2", "sprint_backend")
        >>> # ... ingest more actions ...
        >>> chunks = generator.analyze_and_chunk()
        >>> for chunk in chunks:
        ...     print(f"New Chunk: {chunk.semantic_label}")
    """

    def __init__(self, window_size: int = 100, cluster_threshold: int = 5):
        """
        Initialize the Dynamic Chunk Flow Generator.
        
        Args:
            window_size (int): Number of recent actions to keep in memory for analysis.
            cluster_threshold (int): Minimum co-occurrence count to form a cluster.
        """
        if window_size < 10:
            raise ValueError("Window size must be at least 10 to establish a pattern.")
        
        self.window_size = window_size
        self.cluster_threshold = cluster_threshold
        self.action_buffer: deque[AtomicAction] = deque(maxlen=window_size)
        self.active_chunks: Dict[str, CognitiveChunk] = {}
        self.entity_graph: Dict[str, Dict[str, int]] = {} # Adjacency list with weights
        
        logger.info(f"DynamicChunkFlowGenerator initialized with window {window_size}")

    def ingest_action(self, action_id: str, target_entity: str, context: str) -> bool:
        """
        Ingest a single atomic user action into the monitoring stream.
        
        Args:
            action_id (str): Unique identifier for the action.
            target_entity (str): The entity being manipulated.
            context (str): The current semantic context of the user.
        
        Returns:
            bool: True if ingestion was successful.
        
        Raises:
            ValueError: If required fields are empty.
        """
        if not all([action_id, target_entity, context]):
            logger.error("Ingestion failed: Empty fields detected.")
            raise ValueError("Action ID, Entity, and Context cannot be empty.")
            
        try:
            action = AtomicAction(
                action_id=action_id,
                timestamp=time.time(),
                target_entity=target_entity,
                context=context
            )
            self.action_buffer.append(action)
            self._update_co_occurrence(action)
            return True
        except Exception as e:
            logger.exception(f"Error ingesting action {action_id}: {e}")
            return False

    def _update_co_occurrence(self, new_action: AtomicAction) -> None:
        """
        Internal helper to update the entity relationship graph based on recent history.
        
        Analyzes the relationship between the new action and the immediate history
        to build a graph of related entities.
        """
        # Look at the last few actions to establish immediate context links
        depth = 5 
        recent_actions = list(self.action_buffer)[-depth:]
        
        target = new_action.target_entity
        if target not in self.entity_graph:
            self.entity_graph[target] = {}
            
        for past_action in recent_actions:
            neighbor = past_action.target_entity
            if neighbor != target:
                # Increment weight
                self.entity_graph[target][neighbor] = self.entity_graph[target].get(neighbor, 0) + 1

    def analyze_and_chunk(self) -> List[CognitiveChunk]:
        """
        Analyze the current stream to identify and generate cognitive chunks.
        
        This method finds cliques or dense clusters in the entity graph. If entities
        appear together frequently above the threshold, they are aggregated.
        
        Returns:
            List[CognitiveChunk]: A list of newly generated or updated chunks.
        """
        logger.info("Starting chunk analysis...")
        new_chunks: List[CognitiveChunk] = []
        
        # Identify clusters based on connection density
        visited: Set[str] = set()
        
        for entity, neighbors in self.entity_graph.items():
            if entity in visited:
                continue
                
            # Filter neighbors by threshold
            strong_neighbors = {
                n for n, w in neighbors.items() 
                if w >= self.cluster_threshold
            }
            
            if len(strong_neighbors) > 0:
                # Create a cluster candidate
                cluster_entities = strong_neighbors.union({entity})
                
                # Determine semantic type based on heuristics (placeholder for AI logic)
                cluster_type = self._determine_cluster_type(cluster_entities)
                
                # Generate a stable ID for this chunk
                chunk_id = f"chunk_{hash(frozenset(cluster_entities)) % 10000}"
                
                if chunk_id not in self.active_chunks:
                    chunk = CognitiveChunk(
                        chunk_id=chunk_id,
                        semantic_label=f"Aggregated Block ({cluster_type.value})",
                        cluster_type=cluster_type,
                        contained_entities=cluster_entities,
                        priority_score=len(cluster_entities) * 1.5
                    )
                    self.active_chunks[chunk_id] = chunk
                    new_chunks.append(chunk)
                    visited.update(cluster_entities)
                    logger.info(f"Generated new chunk: {chunk.chunk_id} with {len(cluster_entities)} entities")

        return new_chunks

    def _determine_cluster_type(self, entities: Set[str]) -> DataClusterType:
        """
        Auxiliary function to determine the semantic type of a data cluster.
        
        Args:
            entities (Set[str]): The set of entities in the cluster.
            
        Returns:
            DataClusterType: The predicted category of the data cluster.
        """
        # Simple heuristic logic for demonstration
        sample = next(iter(entities), "")
        if "task" in sample.lower():
            return DataClusterType.SPRINT_PHASE
        elif "doc" in sample.lower() or "file" in sample.lower():
            return DataClusterType.CONTEXT_BLOCK
        return DataClusterType.TASK_GROUP

    def get_materialized_view(self) -> Dict[str, List[str]]:
        """
        Returns the current 'Materialized View' of the user's world.
        Unchunked (atomic) data is hidden if it belongs to a chunk.
        
        Returns:
            Dict containing 'chunks' (aggregated views) and 'focus_points' (atomic outliers).
        """
        view = {
            "chunks": [c.semantic_label for c in self.active_chunks.values()],
            "atomic_focus": []
        }
        
        # Logic to determine what remains atomic (not yet chunked)
        all_chunked_entities = set()
        for c in self.active_chunks.values():
            all_chunked_entities.update(c.contained_entities)
            
        # Find recent entities that are not in chunks (requiring immediate attention)
        recent_entities = {a.target_entity for a in list(self.action_buffer)[-10:]}
        view["atomic_focus"] = list(recent_entities - all_chunked_entities)
        
        return view


if __name__ == "__main__":
    # Demonstration of usage
    generator = DynamicChunkFlowGenerator(window_size=50, cluster_threshold=3)
    
    # Simulate a stream of user operations (Project Management Scenario)
    print("Simulating user activity stream...")
    
    # Phase 1: Working on backend sprint (High frequency)
    for i in range(10):
        generator.ingest_action(f"act_{i}", f"backend_task_{i%3}", "sprint_1")
        
    # Phase 2: Switching context briefly (Low frequency)
    generator.ingest_action("act_20", "email_client", "communication")
    generator.ingest_action("act_21", "slack_bot", "communication")
    
    # Analyze
    chunks = generator.analyze_and_chunk()
    
    print("\n--- Cognitive Chunks Generated ---")
    for chunk in chunks:
        print(f"Chunk: {chunk.semantic_label}")
        print(f"  Type: {chunk.cluster_type.value}")
        print(f"  Entities: {chunk.contained_entities}")
        
    print("\n--- Materialized View for UI ---")
    view = generator.get_materialized_view()
    print(f"Aggregated Chunks: {view['chunks']}")
    print(f"Atomic Focus (Unchunked): {view['atomic_focus']}")