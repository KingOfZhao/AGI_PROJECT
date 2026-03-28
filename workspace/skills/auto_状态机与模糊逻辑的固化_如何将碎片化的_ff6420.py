"""
Module: auto_state_fuzzy_solidification_ff6420
Description: 【状态机与模糊逻辑的固化】
     Converts fragmented implicit knowledge (e.g., 'a pinch', 'a moment', 'hot')
     into executable probabilistic membership functions. This module handles
     'cognitive consistency' by managing fuzzy boundaries and constructing
     dynamically adjustable 'truth nodes' within a fuzzy state machine context.
"""

import logging
import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FuzzySolidification_FF6420")

# Type Aliases
FuzzyValue = Union[float, int]
MembershipFunction = Callable[[FuzzyValue], float]

class FuzzyLogicError(Exception):
    """Custom exception for fuzzy logic processing errors."""
    pass

@dataclass
class FuzzySet:
    """
    Represents a fuzzy set with a linguistic label and a membership function.
    
    Attributes:
        label (str): The linguistic term (e.g., 'hot', 'fast').
        membership_func (Callable): Function determining degree of membership [0, 1].
    """
    label: str
    membership_func: MembershipFunction

    def __call__(self, value: FuzzyValue) -> float:
        return self.membership_func(value)

class KnowledgeSolidifier:
    """
    Transforms implicit, fragmented knowledge definitions into structured
    fuzzy logic components (Membership Functions).
    """

    @staticmethod
    def _validate_parameters(a: float, b: float, c: float, d: Optional[float] = None) -> None:
        """
        Helper function to validate parameters for membership functions.
        
        Args:
            a, b, c, d: Parameters defining the shape boundaries.
        
        Raises:
            ValueError: If parameters are out of order or invalid.
        """
        if not (0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1):
             raise ValueError("Parameters must typically be normalized or logically ordered.")
        
        # For trapezoidal/triangular, a <= b <= c <= d (if d exists)
        if d is not None:
            if not (a <= b <= c <= d):
                raise ValueError(f"Invalid shape parameters: requires a <= b <= c <= d, got {a}, {b}, {c}, {d}")
        else:
            if not (a <= b <= c):
                raise ValueError(f"Invalid shape parameters: requires a <= b <= c, got {a}, {b}, {c}")

    @staticmethod
    def create_trapezoidal_mf(
        a: float, 
        b: float, 
        c: float, 
        d: float
    ) -> MembershipFunction:
        """
        Creates a Trapezoidal Membership Function.
        
        Args:
            a (float): Left foot (membership starts rising from 0).
            b (float): Left shoulder (membership reaches 1).
            c (float): Right shoulder (membership starts dropping from 1).
            d (float): Right foot (membership reaches 0).
            
        Returns:
            Callable[[float], float]: A function that accepts a crisp value and returns membership degree.
        
        Example:
            >>> func = KnowledgeSolidifier.create_trapezoidal_mf(0, 20, 30, 50)
            >>> func(25) # Returns 1.0
        """
        try:
            KnowledgeSolidifier._validate_parameters(a, b, c, d)
        except ValueError as e:
            logger.error(f"Parameter validation failed: {e}")
            raise

        def membership(x: FuzzyValue) -> float:
            if x <= a or x >= d:
                return 0.0
            elif a < x < b:
                return (x - a) / (b - a) if (b - a) != 0 else 0.0
            elif b <= x <= c:
                return 1.0
            elif c < x < d:
                return (d - x) / (d - c) if (d - c) != 0 else 0.0
            return 0.0
        
        logger.debug(f"Created Trapezoidal MF with params: {a}, {b}, {c}, {d}")
        return membership

    @staticmethod
    def solidify_implicit_knowledge(
        concept_name: str, 
        approx_range: Tuple[float, float, float, float]
    ) -> FuzzySet:
        """
        Core Function 1: Converts a linguistic concept into a FuzzySet (Probability Distribution).
        
        This simulates 'solidifying' vague human instructions into math.
        
        Args:
            concept_name (str): Name of the concept (e.g., 'momentarily').
            approx_range (Tuple): The rough boundaries (a, b, c, d) defining the concept.
            
        Returns:
            FuzzySet: The solidified knowledge node.
        """
        if not isinstance(approx_range, (list, tuple)) or len(approx_range) != 4:
            raise FuzzyLogicError("approx_range must be a tuple of 4 floats.")
            
        mf = KnowledgeSolidifier.create_trapezoidal_mf(*approx_range)
        logger.info(f"Solidified implicit concept '{concept_name}' into executable node.")
        
        return FuzzySet(label=concept_name, membership_func=mf)

class FuzzyStateEngine:
    """
    Core Function 2: A state engine that evaluates inputs against solidified fuzzy nodes
    to determine the current cognitive state.
    """
    
    def __init__(self):
        self.knowledge_base: Dict[str, FuzzySet] = {}
        logger.info("Initialized FuzzyStateEngine.")

    def add_knowledge_node(self, fuzzy_set: FuzzySet) -> None:
        """Registers a solidified knowledge node into the engine."""
        if not fuzzy_set.label:
            raise ValueError("FuzzySet must have a label.")
        self.knowledge_base[fuzzy_set.label] = fuzzy_set
        logger.debug(f"Added node: {fuzzy_set.label}")

    def evaluate_state(self, crisp_input: FuzzyValue) -> Dict[str, float]:
        """
        Evaluates a crisp input against all knowledge nodes to find truth degrees.
        
        Args:
            crisp_input (float): The real-world input value (e.g., temperature, time duration).
            
        Returns:
            Dict[str, float]: A dictionary mapping concept labels to their activation strength (0-1).
        
        Example:
            >>> engine = FuzzyStateEngine()
            >>> # Define "Hot" as roughly 30-50 degrees, fully 40-45
            >>> hot_node = KnowledgeSolidifier.solidify_implicit_knowledge("Hot", (30, 40, 45, 50))
            >>> engine.add_knowledge_node(hot_node)
            >>> engine.evaluate_state(42)
            {'Hot': 1.0}
        """
        if not isinstance(crisp_input, (int, float)):
            raise TypeError(f"Input must be numeric, got {type(crisp_input)}")

        results = {}
        logger.info(f"Evaluating state for input: {crisp_input}")
        
        for label, f_set in self.knowledge_base.items():
            try:
                degree = f_set(crisp_input)
                # Apply threshold to filter noise
                if degree > 0.01:
                    results[label] = degree
            except Exception as e:
                logger.error(f"Error evaluating set {label}: {e}")
        
        return results

    def get_dominant_state(self, crisp_input: FuzzyValue) -> Tuple[Optional[str], float]:
        """
        Helper Function: Determines the single most active state.
        """
        states = self.evaluate_state(crisp_input)
        if not states:
            return None, 0.0
        
        dominant = max(states.items(), key=lambda item: item[1])
        return dominant

# --- Usage Example and Demonstration ---

if __name__ == "__main__":
    # 1. Initialize the Solidifier
    solidifier = KnowledgeSolidifier()
    
    # 2. Define Implicit Knowledge (e.g., Time durations in seconds)
    # "A moment" (片刻) -> roughly 1s to 5s
    moment_node = solidifier.solidify_implicit_knowledge(
        concept_name="moment", 
        approx_range=(0.5, 1.0, 4.0, 6.0)
    )
    
    # "A while" (一会儿) -> roughly 10s to 60s
    while_node = solidifier.solidify_implicit_knowledge(
        concept_name="a_while", 
        approx_range=(5.0, 15.0, 50.0, 80.0)
    )

    # 3. Initialize Engine and Load Knowledge
    engine = FuzzyStateEngine()
    engine.add_knowledge_node(moment_node)
    engine.add_knowledge_node(while_node)

    # 4. Test Dynamic Evaluation (Cognitive Consistency Check)
    test_inputs = [0.8, 3.0, 12.0, 55.0, 100.0]

    print(f"{'Input (s)':<10} | {'Dominant State':<15} | {'Truth Value':<10} | {'All Active States'}")
    print("-" * 70)

    for t in test_inputs:
        dominant_label, dominant_val = engine.get_dominant_state(t)
        all_states = engine.evaluate_state(t)
        
        # Formatting output
        active_str = ", ".join([f"{k}:{v:.2f}" for k, v in all_states.items()])
        print(f"{t:<10} | {str(dominant_label):<15} | {dominant_val:<10.4f} | {active_str}")

    # 5. Error Handling Demo
    try:
        print("\nTesting invalid parameters...")
        bad_node = solidifier.solidify_implicit_knowledge("broken", (10, 5, 20, 30)) # a > b
    except ValueError as e:
        print(f"Caught expected error: {e}")