"""
Module: intent_slicer_ecommerce.py
Description: Advanced AGI Skill for decomposing complex intents (e.g., 'Build an E-commerce System')
             into executable topological subsequences based on a repository of existing skills.
             It utilizes graph algorithms to identify dependencies and logic gaps.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import logging
import heapq
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass(order=True)
class SkillNode:
    """
    Represents a single Skill node in the knowledge graph.
    """
    node_id: str
    name: str
    description: str = field(compare=False)
    tags: Set[str] = field(default_factory=set, compare=False)
    dependencies: Set[str] = field(default_factory=set, compare=False) # IDs of prerequisite skills
    
    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if not isinstance(other, SkillNode):
            return NotImplemented
        return self.node_id == other.node_id

@dataclass
class TaskGraph:
    """
    Wrapper for the graph structure containing skills and their relationships.
    """
    skills: Dict[str, SkillNode] = field(default_factory=dict)
    adjacency_list: Dict[str, Set[str]] = field(default_factory=dict) # Directed edges: Dependent -> Provider

    def add_skill(self, skill: SkillNode):
        if skill.node_id in self.skills:
            logger.warning(f"Duplicate skill ID detected: {skill.node_id}")
            return
        
        self.skills[skill.node_id] = skill
        self.adjacency_list[skill.node_id] = set()
        logger.debug(f"Skill added: {skill.name}")

    def build_edges(self):
        """
        Construct graph edges based on skill dependencies.
        """
        for skill_id, skill in self.skills.items():
            for dep_id in skill.dependencies:
                if dep_id in self.skills:
                    self.adjacency_list[dep_id].add(skill_id)
                else:
                    logger.warning(f"Missing dependency {dep_id} for skill {skill_id}")

@dataclass
class ExecutionPlan:
    """
    The output object containing the execution sequence and identified gaps.
    """
    sequence: List[SkillNode]
    gaps: List[Tuple[SkillNode, str]] # (Preceding Skill, Missing Logic Description)
    coverage_score: float # 0.0 to 1.0

# --- Core Logic ---

class IntentSlicer:
    """
    Decomposes a high-level intent into a sequence of skills using graph algorithms.
    """

    def __init__(self, graph: TaskGraph):
        self.graph = graph
        self.graph.build_edges()
        logger.info(f"IntentSlicer initialized with {len(graph.skills)} skills.")

    def _match_intent_to_subgraphs(self, intent_keywords: Set[str]) -> List[SkillNode]:
        """
        Helper function to find relevant skill nodes based on keyword matching.
        """
        relevant_nodes = []
        for node in self.graph.skills.values():
            overlap = intent_keywords.intersection(node.tags)
            if overlap:
                relevant_nodes.append(node)
        
        if not relevant_nodes:
            logger.warning("No relevant skills found for the provided keywords.")
        return relevant_nodes

    def _calculate_relevance_weight(self, node: SkillNode, keywords: Set[str]) -> int:
        """
        Calculate a weight for pathfinding (lower is better).
        """
        overlap = len(keywords.intersection(node.tags))
        if overlap == 0:
            return 100 # High penalty for irrelevant nodes
        return 10 - overlap # Lower number means higher relevance

    def find_shortest_execution_path(self, start_node_id: str, end_node_id: str, keywords: Set[str]) -> Optional[List[SkillNode]]:
        """
        Dijkstra's algorithm adapted to find the most relevant path between two skill nodes.
        """
        if start_node_id not in self.graph.skills or end_node_id not in self.graph.skills:
            logger.error("Start or End node not found in graph.")
            return None

        distances = {node_id: float('inf') for node_id in self.graph.skills}
        previous = {node_id: None for node_id in self.graph.skills}
        distances[start_node_id] = 0
        
        pq = [(0, start_node_id)]
        
        while pq:
            current_dist, current_node_id = heapq.heappop(pq)
            
            if current_node_id == end_node_id:
                break
                
            if current_dist > distances[current_node_id]:
                continue
            
            # Iterate over neighbors (skills that depend on current OR current depends on - depending on graph direction logic)
            # Here we assume adjacency_list points to 'next possible steps' (dependencies resolved)
            # For this example, we treat adjacency as "can proceed to".
            neighbors = self.graph.adjacency_list.get(current_node_id, set())
            
            # Also consider reverse dependencies for building up a system (bottom-up)
            neighbors.update(self.graph.skills[current_node_id].dependencies)

            for neighbor_id in neighbors:
                weight = self._calculate_relevance_weight(self.graph.skills[neighbor_id], keywords)
                dist = current_dist + weight
                
                if dist < distances[neighbor_id]:
                    distances[neighbor_id] = dist
                    previous[neighbor_id] = current_node_id
                    heapq.heappush(pq, (dist, neighbor_id))
        
        # Reconstruct path
        path = []
        curr = end_node_id
        if distances[end_node_id] == float('inf'):
            return None # No path found
            
        while curr is not None:
            path.append(self.graph.skills[curr])
            curr = previous[curr]
        
        path.reverse()
        return path

    def analyze_logical_gaps(self, path: List[SkillNode]) -> List[Tuple[SkillNode, str]]:
        """
        Identifies logical breakpoints where manual code or new skills are needed.
        Heuristic: If two adjacent skills in the path share fewer than 1 tag or lack direct graph edge.
        """
        gaps = []
        for i in range(len(path) - 1):
            current = path[i]
            next_node = path[i+1]
            
            # Check graph connectivity
            is_connected = next_node.node_id in self.graph.adjacency_list.get(current.node_id, set())
            tag_overlap = len(current.tags.intersection(next_node.tags))
            
            if not is_connected and tag_overlap == 0:
                gap_desc = f"Logic Gap: Integration needed between '{current.name}' and '{next_node.name}'"
                gaps.append((current, gap_desc))
                logger.info(f"Gap detected: {gap_desc}")
                
        return gaps

    def generate_plan(self, intent: str, keywords: Set[str]) -> ExecutionPlan:
        """
        Main entry point. Generates the full execution plan.
        """
        logger.info(f"Generating plan for intent: {intent}")
        
        # 1. Identify Entry and Exit nodes based on intent
        candidates = self._match_intent_to_subgraphs(keywords)
        if not candidates:
            return ExecutionPlan(sequence=[], gaps=[], coverage_score=0.0)

        # Simplified logic: Sort by relevance (tag overlap)
        # In a real AGI, this would involve semantic vector search
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: len(x.tags.intersection(keywords)), 
            reverse=True
        )
        
        # 2. Construct a pseudo-path (Minimum Spanning Tree approach on subgraph is complex,
        # so we use a greedy path connection approach here for demonstration).
        # We try to link the most relevant 'infrastructure' skills.
        
        # Filter for 'Core' skills
        core_skills = [s for s in sorted_candidates if 'core' in s.tags or 'database' in s.tags or 'auth' in s.tags]
        
        # Build sequence using Topological Sort on the subgraph of candidates
        sequence = self._topological_sort_subgraph(core_skills)
        
        # 3. Analyze Gaps
        gaps = self.analyze_logical_gaps(sequence)
        
        # 4. Calculate Coverage
        total_steps = len(sequence) + len(gaps)
        coverage = len(sequence) / total_steps if total_steps > 0 else 0.0
        
        return ExecutionPlan(
            sequence=sequence,
            gaps=gaps,
            coverage_score=coverage
        )

    def _topological_sort_subgraph(self, nodes: List[SkillNode]) -> List[SkillNode]:
        """
        Performs topological sort on a subset of nodes to resolve dependencies.
        """
        in_degree = {n.node_id: 0 for n in nodes}
        node_map = {n.node_id: n for n in nodes}
        graph_subset = {n.node_id: [] for n in nodes}
        
        # Build subgraph edges
        node_ids = set(node_map.keys())
        for n in nodes:
            for dep_id in n.dependencies:
                if dep_id in node_ids:
                    graph_subset[dep_id].append(n.node_id)
                    in_degree[n.node_id] += 1
        
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []
        
        while queue:
            nid = queue.pop(0)
            sorted_nodes.append(node_map[nid])
            
            for neighbor in graph_subset[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(sorted_nodes) != len(nodes):
            logger.warning("Cycle detected in subgraph dependencies, returning partial result.")
            
        return sorted_nodes

# --- Example Usage ---

def setup_mock_ecommerce_graph() -> TaskGraph:
    """
    Creates a mock skill graph for demonstration purposes.
    """
    graph = TaskGraph()
    
    # Define skills
    skills = [
        SkillNode("sk_01", "Database Setup", "Initialize Postgres", {"database", "core", "infra"}, set()),
        SkillNode("sk_02", "User Auth API", "JWT Authentication System", {"auth", "api", "user"}, {"sk_01"}),
        SkillNode("sk_03", "Product Catalog DB", "Schema for products", {"database", "product"}, {"sk_01"}),
        SkillNode("sk_04", "Product API", "CRUD for products", {"api", "product"}, {"sk_03"}),
        SkillNode("sk_05", "Payment Gateway", "Stripe Integration", {"payment", "api"}, {"sk_02"}), # Depends on User Auth usually
        SkillNode("sk_06", "Frontend React App", "User Interface", {"frontend", "ui"}, set()),
        SkillNode("sk_07", "Docker Deployment", "Containerization", {"devops", "infra"}, set()),
    ]
    
    for s in skills:
        graph.add_skill(s)
        
    return graph

if __name__ == "__main__":
    # 1. Setup Data
    task_graph = setup_mock_ecommerce_graph()
    
    # 2. Initialize Slicer
    slicer = IntentSlicer(task_graph)
    
    # 3. Define Intent
    intent_desc = "构建一个电商系统"
    intent_keywords = {"ecommerce", "database", "auth", "api", "product", "payment"}
    
    # 4. Generate Plan
    plan = slicer.generate_plan(intent_desc, intent_keywords)
    
    # 5. Output Results
    print("\n=== AGI Task Decomposition Plan ===")
    print(f"Intent: {intent_desc}")
    print(f"Coverage Score: {plan.coverage_score:.2f}")
    print("\n--- Execution Sequence ---")
    for i, skill in enumerate(plan.sequence, 1):
        print(f"{i}. [{skill.node_id}] {skill.name}: {skill.description}")
        
    print("\n--- Identified Logic Gaps ---")
    if not plan.gaps:
        print("No critical gaps detected (Mock scenario).")
    for prev_skill, gap_desc in plan.gaps:
        print(f"! After '{prev_skill.name}': {gap_desc}")
