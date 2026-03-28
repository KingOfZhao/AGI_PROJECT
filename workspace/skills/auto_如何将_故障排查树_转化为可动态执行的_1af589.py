"""
Module: bayesian_troubleshooter
Description: Converts static troubleshooting trees into a dynamic Bayesian Action Network (BAN)
             to optimize repair paths based on real-time feedback, balancing information gain
             and execution cost.

Author: AGI System Core
Version: 1.0.0
License: MIT
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration for node types in the network."""
    FAULT = "FAULT"
    ACTION = "ACTION"
    OBSERVATION = "OBSERVATION"

@dataclass
class Node:
    """
    Represents a node in the Bayesian Action Network.
    
    Attributes:
        id: Unique identifier for the node.
        name: Human-readable name.
        type: Type of the node (Fault, Action, Observation).
        prior_prob: Prior probability of a fault being present (only for FAULT type).
        cost: Cost associated with executing an action (only for ACTION type).
        children: List of child node IDs.
        cpt: Conditional Probability Table (simplified as dict for this example).
             Maps (Parent State) -> Probability.
    """
    id: str
    name: str
    type: NodeType
    prior_prob: float = 0.0
    cost: float = 0.0
    children: List[str] = field(default_factory=list)
    parents: List[str] = field(default_factory=list)
    # Simplified CPT: Key = outcome/observation, Value = probability of this outcome given action
    cpt: Dict[str, float] = field(default_factory=dict)

class DynamicTroubleshooter:
    """
    A system to transform static troubleshooting trees into a dynamic, executable 
    Bayesian Action Network. It selects the next optimal action based on 
    Information Gain (IG) normalized by Cost.
    """

    def __init__(self, nodes: List[Node], prior_beliefs: Dict[str, float]):
        """
        Initialize the network with nodes and initial beliefs.
        
        Args:
            nodes: List of Node objects defining the network structure.
            prior_beliefs: Initial probability distribution over potential root faults.
        """
        self.nodes: Dict[str, Node] = {n.id: n for n in nodes}
        self.beliefs: Dict[str, float] = prior_beliefs.copy()
        self.history: List[Tuple[str, str]] = [] # (Action ID, Outcome)
        
        # Validation
        self._validate_network()
        logger.info("DynamicTroubleshooter initialized with %d nodes.", len(self.nodes))

    def _validate_network(self) -> None:
        """Validates the integrity of the network data."""
        if not self.nodes:
            raise ValueError("Network cannot be empty.")
            
        for node in self.nodes.values():
            if node.type == NodeType.ACTION and node.cost < 0:
                raise ValueError(f"Cost cannot be negative for action {node.id}")
            if node.type == NodeType.FAULT:
                if not (0.0 <= node.prior_prob <= 1.0):
                    raise ValueError(f"Invalid prior probability for fault {node.id}")

    def update_beliefs(self, action_id: str, observation: str) -> None:
        """
        Update the belief state based on the action taken and observation received.
        Uses a simplified Bayesian update mechanism.
        
        Args:
            action_id: The ID of the action performed.
            observation: The result of the action (e.g., 'success', 'pressure_low').
        """
        if action_id not in self.nodes:
            logger.error("Action %s not found in network.", action_id)
            return

        action_node = self.nodes[action_id]
        likelihood = action_node.cpt.get(observation, 0.0)
        
        if likelihood == 0.0:
            logger.warning("Observation %s has 0 likelihood in CPT for action %s", observation, action_id)
            return

        # Simplified Bayesian Update:
        # We update the probability of the *causes* (faults) that this action investigates.
        # In a full BAN, this involves message passing. Here we update connected faults.
        # P(Fault | Obs) = P(Obs | Fault) * P(Fault) / P(Obs)
        # We assume this action is relevant to specific faults (connected via logic).
        
        connected_faults = [p_id for p_id in action_node.parents if self.nodes[p_id].type == NodeType.FAULT]
        
        for fault_id in connected_faults:
            current_belief = self.beliefs.get(fault_id, 0.0)
            # Naive update: Increase belief if observation matches expected outcome for this fault
            # In a real scenario, we'd look up P(Obs | Fault) specifically.
            # Here we simply scale belief by the likelihood provided in the action node.
            new_belief = current_belief * likelihood
            
            # Normalize (rough approximation to keep sum=1, though strictly speaking requires marginalization)
            # For this demo, we just update the specific value and re-normalize later.
            self.beliefs[fault_id] = new_belief
            
        self._normalize_beliefs()
        self.history.append((action_id, observation))
        logger.info(f"Updated beliefs after {action_id}: {self.beliefs}")

    def _normalize_beliefs(self) -> None:
        """Normalizes belief probabilities to sum to 1."""
        total = sum(self.beliefs.values())
        if total > 0:
            self.beliefs = {k: v / total for k, v in self.beliefs.items()}
        else:
            # Uniform distribution if everything is zero
            count = len(self.beliefs)
            self.beliefs = {k: 1.0/count for k in self.beliefs}

    def calculate_eoi(self, action_id: str) -> float:
        """
        Calculates the Expected Output Information (EOI) / Information Gain 
        for a specific action.
        
        EOI = Sum(P(outcome) * EntropyReduction(outcome))
        
        Simplified Formula used here:
        EOI = Entropy(CurrentBeliefs) - Expected_Entropy(FutureBeliefs)
        
        Args:
            action_id: The ID of the action to evaluate.
            
        Returns:
            float: The expected information gain.
        """
        if action_id not in self.nodes:
            return 0.0
            
        action_node = self.nodes[action_id]
        if action_node.type != NodeType.ACTION:
            return 0.0

        current_entropy = self._calculate_entropy(self.beliefs)
        expected_future_entropy = 0.0
        
        # Calculate weighted average of entropies after possible observations
        for outcome, prob_outcome in action_node.cpt.items():
            # Simulate belief update
            temp_beliefs = self.beliefs.copy()
            
            # Heuristic update for simulation: 
            # If outcome is likely, shift probability mass.
            # This is a proxy for full inference simulation.
            for fault_id in self.beliefs:
                # P(Obs|Fault) approximation
                # Let's assume high prob_outcome implies strong evidence
                relevance = 0.0
                if fault_id in action_node.parents:
                    relevance = prob_outcome # Simplification
                
                # Adjust temporary beliefs
                if relevance > 0:
                    temp_beliefs[fault_id] *= (1 + relevance) # Boost likely faults
                else:
                    temp_beliefs[fault_id] *= (1 - (prob_outcome * 0.5)) # Penalize unlikely

            # Normalize temp
            total = sum(temp_beliefs.values())
            if total > 0:
                temp_beliefs = {k: v/total for k, v in temp_beliefs.items()}
            
            outcome_entropy = self._calculate_entropy(temp_beliefs)
            expected_future_entropy += prob_outcome * outcome_entropy
            
        info_gain = current_entropy - expected_future_entropy
        return max(0.0, info_gain)

    def _calculate_entropy(self, distribution: Dict[str, float]) -> float:
        """Calculates Shannon entropy of a probability distribution."""
        entropy = 0.0
        for p in distribution.values():
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    def get_next_best_action(self) -> Optional[str]:
        """
        Determines the next best action by maximizing the ratio of 
        Information Gain to Cost (IG/Cost).
        
        Returns:
            str: The ID of the selected action node, or None if no actions remain.
        """
        best_action_id = None
        max_value = -1.0
        
        logger.info("Evaluating candidate actions...")
        
        candidate_actions = [
            n.id for n in self.nodes.values() 
            if n.type == NodeType.ACTION and n.id not in [h[0] for h in self.history]
        ]

        if not candidate_actions:
            logger.info("No remaining actions to execute.")
            return None

        for action_id in candidate_actions:
            node = self.nodes[action_id]
            
            # Safety check for cost
            if node.cost <= 0:
                logger.warning(f"Action {action_id} has zero or negative cost, defaulting to epsilon.")
                cost = 1e-6
            else:
                cost = node.cost
                
            ig = self.calculate_eoi(action_id)
            value_ratio = ig / cost
            
            logger.debug(f"Action: {action_id} | IG: {ig:.4f} | Cost: {cost} | Ratio: {value_ratio:.4f}")
            
            if value_ratio > max_value:
                max_value = value_ratio
                best_action_id = action_id
                
        logger.info(f"Selected Best Action: {best_action_id} with Value Ratio: {max_value:.4f}")
        return best_action_id

# Helper Functions

def build_standard_tree() -> List[Node]:
    """
    Helper function to construct a sample troubleshooting tree.
    
    Structure:
    Faults: F1 (Leak), F2 (Clog)
    Actions: A1 (Tighten), A2 (Flush)
    """
    return [
        Node(id="F1", name="Pipe Leak", type=NodeType.FAULT, prior_prob=0.6),
        Node(id="F2", name="Valve Clog", type=NodeType.FAULT, prior_prob=0.4),
        
        # Action 1: Tighten screws. High cost, good for detecting Leak.
        Node(
            id="A1", 
            name="Tighten Screws", 
            type=NodeType.ACTION, 
            cost=50.0,
            parents=["F1"],
            cpt={"tightened_ok": 0.8, "still_loose": 0.2} # Probabilities of outcomes given F1 is likely
        ),
        
        # Action 2: Flush valve. Low cost, good for detecting Clog.
        Node(
            id="A2", 
            name="Flush Valve", 
            type=NodeType.ACTION, 
            cost=10.0,
            parents=["F2"],
            cpt={"flow_restored": 0.9, "blocked": 0.1}
        )
    ]

def run_diagnosis_demo():
    """
    Demonstrates the full workflow of the dynamic troubleshooter.
    """
    print("--- Starting AGI Dynamic Troubleshooting Demo ---")
    
    # 1. Build Network
    nodes = build_standard_tree()
    
    # 2. Initialize System
    # Initial beliefs based on priors
    priors = {"F1": 0.6, "F2": 0.4}
    troubleshooter = DynamicTroubleshooter(nodes, priors)
    
    # 3. First Cycle: Determine best action
    print("\n[Step 1] Calculating optimal first action...")
    action_1 = troubleshooter.get_next_best_action()
    
    if action_1:
        print(f"--> System chooses: {action_1} ({troubleshooter.nodes[action_1].name})")
        
        # 4. Simulate Execution & Feedback
        # Imagine we perform A2 (Flush Valve) and observe 'flow_restored'
        # (This matches F2)
        print(f"--> Executing {action_1}... (Simulating real-world execution)")
        simulated_observation = "flow_restored" 
        
        # 5. Update Beliefs
        print(f"--> Observation received: '{simulated_observation}'")
        troubleshooter.update_beliefs(action_1, simulated_observation)
        
        # 6. Re-evaluate
        print("\n[Step 2] Re-evaluating beliefs...")
        print(f"New Beliefs: {troubleshooter.beliefs}")
        
        # Check if solved (simplistic check: if belief > 0.9)
        top_fault = max(troubleshooter.beliefs, key=troubleshooter.beliefs.get)
        if troubleshooter.beliefs[top_fault] > 0.85:
            print(f"--> FAULT IDENTIFIED: {top_fault} with high confidence.")
        else:
            action_2 = troubleshooter.get_next_best_action()
            if action_2:
                print(f"--> Next recommended action: {action_2}")

if __name__ == "__main__":
    run_diagnosis_demo()