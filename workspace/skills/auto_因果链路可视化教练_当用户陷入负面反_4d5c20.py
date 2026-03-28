"""
Module: auto_causal_chain_visualization_coach
Description: A cross-domain AGI skill module designed to help users break negative rumination loops.
             It models cognitive processes as a Data Lineage Graph, detecting logical fallacies
             (Dirty Data) and rewriting attribution paths to restore mental flow.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CausalCoach")


class NodeType(Enum):
    """Enumeration of node types in the cognitive lineage."""
    EVENT = "Event"          # Objective occurrence
    EMOTION = "Emotion"      # Subjective feeling
    COGNITION = "Cognition"  # Interpretation/Attribution
    BEHAVIOR = "Behavior"    # Resulting action


class LogicState(Enum):
    """Status of the logical connection."""
    HEALTHY = "Healthy"
    BROKEN = "Broken"        # Logical Leap
    DIRTY = "Dirty Data"     # Cognitive Distortion (e.g., Overgeneralization)


@dataclass
class CognitiveNode:
    """Represents a single node in the cognitive graph."""
    id: str
    content: str
    type: NodeType
    is_distorted: bool = False


@dataclass
class CognitiveEdge:
    """Represents a link between nodes (Attribution Path)."""
    source_id: str
    target_id: str
    state: LogicState
    intervention: Optional[str] = None


class CausalChainCoach:
    """
    The core engine for visualizing and debugging cognitive causal chains.
    
    This class treats cognitive patterns as data pipelines, applying data governance
    rules to detect 'dirty data' (irrational thoughts) and 'broken links' (logical gaps).
    
    Attributes:
        nodes (Dict[str, CognitiveNode]): Repository of thought nodes.
        edges (List[CognitiveEdge]): Repository of connections.
    """

    def __init__(self) -> None:
        """Initialize the coach with empty graph data."""
        self.nodes: Dict[str, CognitiveNode] = {}
        self.edges: List[CognitiveEdge] = []
        logger.info("CausalChainCoach initialized successfully.")

    def add_thought_node(self, node_id: str, content: str, node_type: str) -> bool:
        """
        Add a node to the cognitive graph.
        
        Args:
            node_id (str): Unique identifier for the thought.
            content (str): The content of the thought/feeling.
            node_type (str): Type of node (Event, Emotion, Cognition, Behavior).
            
        Returns:
            bool: True if added successfully, False otherwise.
        """
        try:
            if not node_id or not content:
                raise ValueError("Node ID and content cannot be empty.")
            
            # Validate Enum
            type_map = {e.name: e for e in NodeType}
            if node_type.upper() not in type_map:
                logger.error(f"Invalid node type: {node_type}")
                return False
            
            node = CognitiveNode(
                id=node_id,
                content=content,
                type=type_map[node_type.upper()]
            )
            self.nodes[node_id] = node
            logger.debug(f"Added node: {node_id} ({node_type})")
            return True
        except Exception as e:
            logger.error(f"Error adding node {node_id}: {str(e)}")
            return False

    def create_causal_link(self, source_id: str, target_id: str) -> Optional[CognitiveEdge]:
        """
        Create a causal link between two nodes and immediately validate it.
        
        Args:
            source_id (str): ID of the cause node.
            target_id (str): ID of the effect node.
            
        Returns:
            Optional[CognitiveEdge]: The created edge with its initial state.
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.warning(f"Link creation failed: Node not found ({source_id} -> {target_id})")
            return None

        # Analyze the logic of this link
        state = self._analyze_link_logic(source_id, target_id)
        
        edge = CognitiveEdge(
            source_id=source_id,
            target_id=target_id,
            state=state
        )
        self.edges.append(edge)
        logger.info(f"Created link {source_id}->{target_id} with state: {state.value}")
        return edge

    def _analyze_link_logic(self, source_id: str, target_id: str) -> LogicState:
        """
        [Internal] Detect logical fallacies or 'dirty data' in the attribution.
        
        This is a simplified simulation of cognitive analysis.
        
        Args:
            source_id (str): Source node ID.
            target_id (str): Target node ID.
            
        Returns:
            LogicState: The determined state of the logic.
        """
        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]
        
        source_text = source_node.content.lower()
        target_text = target_node.content.lower()

        # Rule 1: Check for Absolute/Dirty Keywords in Cognition
        absolute_keywords = ["always", "never", "stupid", "failure", "impossible"]
        if any(kw in source_text for kw in absolute_keywords) and target_node.type == NodeType.EMOTION:
            source_node.is_distorted = True
            return LogicState.DIRTY

        # Rule 2: Check for Logical Leaps (Event -> Catastrophe directly)
        if source_node.type == NodeType.EVENT and target_node.type == NodeType.EMOTION:
            if "failure" in target_text:
                return LogicState.BROKEN # Missing intermediate cognition

        return LogicState.HEALTHY

    def visualize_lineage(self) -> str:
        """
        Generate a text-based representation of the cognitive lineage map.
        
        Returns:
            str: The formatted graph visualization.
        """
        output = ["\n=== COGNITIVE LINEAGE GRAPH ==="]
        for edge in self.edges:
            src = self.nodes.get(edge.source_id)
            tgt = self.nodes.get(edge.target_id)
            if not src or not tgt:
                continue
            
            status_icon = "✅" if edge.state == LogicState.HEALTHY else "❌"
            if edge.state == LogicState.DIRTY:
                status_icon = "⚠️ (Dirty Data)"
            elif edge.state == LogicState.BROKEN:
                status_icon = "断裂 (Logic Leap)"
                
            line = f"[{src.type.value}: {src.content}] --(Attribution)--> [{tgt.type.value}: {tgt.content}] {status_icon}"
            output.append(line)
        
        return "\n".join(output)

    def suggest_intervention(self) -> List[str]:
        """
        Analyze the graph for negative loops and suggest rewiring strategies.
        
        Returns:
            List[str]: List of actionable interventions.
        """
        suggestions = []
        for edge in self.edges:
            if edge.state != LogicState.HEALTHY:
                src = self.nodes[edge.source_id]
                tgt = self.nodes[edge.target_id]
                
                if edge.state == LogicState.DIRTY:
                    msg = (f"Detected Dirty Data at '{src.content}'. "
                           f"Suggestion: Is this an objective fact or an interpretation? "
                           f"Try replacing '{src.content}' with specific evidence.")
                    suggestions.append(msg)
                    
                elif edge.state == LogicState.BROKEN:
                    msg = (f"Logic Leap detected between '{src.content}' and '{tgt.content}'. "
                           f"Suggestion: What intermediate thought connects these? "
                           f"Are you ignoring external factors?")
                    suggestions.append(msg)
                    
        return suggestions


# --- Usage Example ---
if __name__ == "__main__":
    # Initialize the coach
    coach = CausalChainCoach()
    
    # 1. User Input: Negative Rumination Loop
    # "I failed the test (Event) -> I am stupid (Cognition) -> Depression (Emotion)"
    coach.add_thought_node("E1", "Failed the math test", "EVENT")
    coach.add_thought_node("C1", "I am stupid and always fail", "COGNITION")
    coach.add_thought_node("EM1", "Depression and Hopelessness", "EMOTION")
    
    # 2. Build the chain
    link1 = coach.create_causal_link("E1", "C1")  # Event to Cognition
    link2 = coach.create_causal_link("C1", "EM1") # Cognition to Emotion
    
    # 3. Visualize the 'Dirty' Data Lineage
    print(coach.visualize_lineage())
    
    # 4. Get Interventions (Data Governance)
    interventions = coach.suggest_intervention()
    print("\n=== SYSTEM INTERVENTIONS ===")
    for idx, advice in enumerate(interventions, 1):
        print(f"{idx}. {advice}")
        
    # 5. Simulated Rewiring (User updates thought)
    print("\n>>> Rewiring cognitive path...")
    coach.add_thought_node("C2", "I didn't study enough for this specific topic", "COGNITION")
    coach.create_causal_link("E1", "C2") # Rewire Event to Healthy Cognition
    
    print("\nUpdated Graph:")
    print(coach.visualize_lineage())