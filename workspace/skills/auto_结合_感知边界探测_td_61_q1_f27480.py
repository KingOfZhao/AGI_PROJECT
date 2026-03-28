"""
Module: auto_结合_感知边界探测_td_61_q1_f27480
Description:
    Advanced AGI security module that combines Perceptual Boundary Detection,
    Structured Cognitive Network Anti-Jamming, and Dead-loop Detection.
    
    Unlike passive defense systems, this module actively generates 'adversarial nodes'
    (logic traps) to stress-test reasoning chains - similar to how immune systems
    produce antibodies. This provides immediate isolation capability against
    malicious prompts or logical fallacies.

Key Components:
    1. Perceptual Boundary Scanner (td_61_Q1_0_5246)
    2. Cognitive Network Defense (td_61_Q6_2_3033)
    3. Dead-loop Detection (td_61_Q4_2_3033)
    4. Adversarial Node Generator

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import random
import hashlib
import time
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum, auto

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enumeration of cognitive network node types"""
    NORMAL = auto()
    ADVERSARIAL = auto()
    ISOLATED = auto()
    IMMUNE = auto()


@dataclass
class CognitiveNode:
    """
    Represents a node in the structured cognitive network.
    
    Attributes:
        id: Unique identifier for the node
        content: The logical content or proposition
        node_type: Classification of the node type
        connections: Set of connected node IDs
        trust_score: Confidence score (0.0 to 1.0)
        created_at: Timestamp of creation
    """
    id: str
    content: str
    node_type: NodeType
    connections: Set[str]
    trust_score: float
    created_at: float


class PerceptualBoundaryScanner:
    """
    Implements td_61_Q1_0_5246: Perceptual Boundary Detection
    Scans input space for logical inconsistencies and boundary violations.
    """
    
    def __init__(self):
        self._boundary_patterns = self._load_boundary_patterns()
    
    def _load_boundary_patterns(self) -> Dict[str, List[str]]:
        """Load predefined boundary violation patterns"""
        return {
            'logical_fallacy': [
                'circular reasoning', 'false dichotomy', 
                'straw man', 'ad hominem'
            ],
            'semantic_violation': [
                'contradiction', 'ambiguity', 'category error'
            ],
            'structural_anomaly': [
                'infinite regress', 'ungrounded premise'
            ]
        }
    
    def scan_input(self, input_text: str) -> Tuple[bool, List[str]]:
        """
        Scan input for perceptual boundary violations.
        
        Args:
            input_text: The input text to analyze
            
        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        if not input_text or not isinstance(input_text, str):
            raise ValueError("Input must be a non-empty string")
            
        violations = []
        input_lower = input_text.lower()
        
        # Check for boundary violations
        for category, patterns in self._boundary_patterns.items():
            for pattern in patterns:
                if pattern in input_lower:
                    violations.append(f"{category}: {pattern}")
        
        is_safe = len(violations) == 0
        logger.debug(f"Input scan result: safe={is_safe}, violations={violations}")
        return is_safe, violations


class CognitiveNetwork:
    """
    Implements td_61_Q6_2_3033: Structured Cognitive Network Anti-Jamming
    Maintains a network of reasoning nodes with trust scoring and isolation.
    """
    
    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}
        self._adversarial_count = 0
    
    def add_node(self, content: str, node_type: NodeType = NodeType.NORMAL) -> str:
        """
        Add a new node to the cognitive network.
        
        Args:
            content: The logical content of the node
            node_type: Type classification (default: NORMAL)
            
        Returns:
            The ID of the newly created node
        """
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")
            
        node_id = self._generate_node_id(content)
        
        # Validate trust score bounds
        trust_score = 0.5 if node_type == NodeType.NORMAL else 0.1
        if node_type == NodeType.ADVERSARIAL:
            self._adversarial_count += 1
            trust_score = 0.0
        
        node = CognitiveNode(
            id=node_id,
            content=content,
            node_type=node_type,
            connections=set(),
            trust_score=trust_score,
            created_at=time.time()
        )
        
        self.nodes[node_id] = node
        logger.info(f"Added {node_type.name} node: {node_id[:8]}...")
        return node_id
    
    def _generate_node_id(self, content: str) -> str:
        """Generate unique node ID using content hash"""
        timestamp = str(time.time())
        hash_input = f"{content}-{timestamp}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()
    
    def connect_nodes(self, node1_id: str, node2_id: str) -> bool:
        """
        Create a connection between two nodes.
        
        Args:
            node1_id: First node ID
            node2_id: Second node ID
            
        Returns:
            True if connection was successful, False otherwise
        """
        if node1_id not in self.nodes or node2_id not in self.nodes:
            logger.warning("Connection failed: node not found")
            return False
            
        if node1_id == node2_id:
            logger.warning("Self-connection not allowed")
            return False
            
        self.nodes[node1_id].connections.add(node2_id)
        self.nodes[node2_id].connections.add(node1_id)
        return True
    
    def isolate_node(self, node_id: str) -> bool:
        """
        Isolate a node by removing all its connections.
        
        Args:
            node_id: ID of the node to isolate
            
        Returns:
            True if isolation was successful, False otherwise
        """
        if node_id not in self.nodes:
            return False
            
        node = self.nodes[node_id]
        
        # Remove all connections to this node
        for connected_id in node.connections.copy():
            if connected_id in self.nodes:
                self.nodes[connected_id].connections.discard(node_id)
        
        node.connections.clear()
        node.node_type = NodeType.ISOLATED
        logger.info(f"Node isolated: {node_id[:8]}...")
        return True


class DeadLoopDetector:
    """
    Implements td_61_Q4_2_3033: Dead-loop Detection
    Identifies circular reasoning patterns and infinite loops.
    """
    
    def __init__(self):
        self._visited_paths: Set[Tuple[str, ...]] = set()
    
    def detect_cycle(self, network: CognitiveNetwork, start_node_id: str) -> bool:
        """
        Detect if there's a cycle starting from a given node.
        
        Args:
            network: The cognitive network to analyze
            start_node_id: ID of the starting node
            
        Returns:
            True if a cycle is detected, False otherwise
        """
        if start_node_id not in network.nodes:
            return False
            
        visited = set()
        recursion_stack = set()
        
        return self._dfs_cycle_detection(
            network, start_node_id, visited, recursion_stack
        )
    
    def _dfs_cycle_detection(
        self,
        network: CognitiveNetwork,
        node_id: str,
        visited: Set[str],
        recursion_stack: Set[str]
    ) -> bool:
        """Depth-first search helper for cycle detection"""
        visited.add(node_id)
        recursion_stack.add(node_id)
        
        node = network.nodes[node_id]
        for neighbor_id in node.connections:
            if neighbor_id not in visited:
                if self._dfs_cycle_detection(network, neighbor_id, visited, recursion_stack):
                    return True
            elif neighbor_id in recursion_stack:
                logger.warning(f"Dead loop detected involving node: {node_id[:8]}...")
                return True
        
        recursion_stack.remove(node_id)
        return False


class AdversarialNodeGenerator:
    """
    Generates adversarial nodes to stress-test the cognitive network.
    Part of the active immune system approach.
    """
    
    def __init__(self, network: CognitiveNetwork):
        self.network = network
        self._trap_templates = self._load_trap_templates()
    
    def _load_trap_templates(self) -> List[str]:
        """Load logical trap templates for adversarial nodes"""
        return [
            "This statement is false.",
            "The following sentence is true. The previous sentence is false.",
            "If this is true, then it is false.",
            "This node contradicts itself.",
            "All generalizations are false, including this one."
        ]
    
    def generate_adversarial_node(self) -> str:
        """
        Generate a new adversarial node with a logical trap.
        
        Returns:
            The ID of the newly created adversarial node
        """
        trap_content = random.choice(self._trap_templates)
        return self.network.add_node(trap_content, NodeType.ADVERSARIAL)
    
    def test_network_resilience(self) -> float:
        """
        Test the network's resilience to adversarial attacks.
        
        Returns:
            Resilience score (0.0 to 1.0)
        """
        # Generate test adversarial nodes
        test_nodes = []
        for _ in range(3):
            node_id = self.generate_adversarial_node()
            test_nodes.append(node_id)
        
        # Check if any cycles were created
        detector = DeadLoopDetector()
        cycles_detected = 0
        
        for node_id in test_nodes:
            if detector.detect_cycle(self.network, node_id):
                cycles_detected += 1
                self.network.isolate_node(node_id)
        
        resilience = 1.0 - (cycles_detected / len(test_nodes))
        logger.info(f"Network resilience test: {resilience:.2f}")
        return resilience


class AGISecuritySystem:
    """
    Main security system combining all components for AGI protection.
    """
    
    def __init__(self):
        self.scanner = PerceptualBoundaryScanner()
        self.network = CognitiveNetwork()
        self.detector = DeadLoopDetector()
        self.adversarial_gen = AdversarialNodeGenerator(self.network)
    
    def process_input(self, input_text: str) -> Dict[str, any]:
        """
        Process input through the complete security pipeline.
        
        Args:
            input_text: The input text to analyze
            
        Returns:
            Dictionary containing processing results
        """
        results = {
            'input': input_text,
            'timestamp': time.time(),
            'status': 'processing',
            'violations': [],
            'is_safe': False,
            'nodes_created': []
        }
        
        try:
            # Step 1: Perceptual boundary scan
            is_safe, violations = self.scanner.scan_input(input_text)
            results['violations'] = violations
            
            if not is_safe:
                results['status'] = 'rejected'
                logger.warning(f"Input rejected due to violations: {violations}")
                return results
            
            # Step 2: Add to cognitive network
            node_id = self.network.add_node(input_text)
            results['nodes_created'].append(node_id)
            
            # Step 3: Dead-loop detection
            if self.detector.detect_cycle(self.network, node_id):
                self.network.isolate_node(node_id)
                results['status'] = 'isolated'
                logger.warning(f"Node isolated due to cycle detection: {node_id[:8]}...")
            else:
                results['status'] = 'accepted'
                results['is_safe'] = True
            
            # Step 4: Active immune response
            resilience = self.adversarial_gen.test_network_resilience()
            results['resilience_score'] = resilience
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error processing input: {e}")
        
        return results


# Example usage
if __name__ == "__main__":
    # Initialize the security system
    security_system = AGISecuritySystem()
    
    # Test with normal input
    test_cases = [
        "The sky is blue during clear days.",
        "This statement is false.",
        "All cats are mammals, and all mammals are animals.",
        "If this is true, then it is false."
    ]
    
    for test_input in test_cases:
        print(f"\nProcessing: {test_input}")
        result = security_system.process_input(test_input)
        print(f"Status: {result['status']}")
        print(f"Safe: {result.get('is_safe', False)}")
        if 'resilience_score' in result:
            print(f"Resilience: {result['resilience_score']:.2f}")