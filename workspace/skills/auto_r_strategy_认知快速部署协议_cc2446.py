"""
Module: auto_r_strategy_认知快速部署协议_cc2446
Description: Implementation of the r-Strategy Cognitive Rapid Deployment Protocol.
             This module facilitates AGI cold starts in unfamiliar domains by
             generating massive amounts of low-cost, high-variability cognitive
             scripts ('hawker-level') and rapidly iterating through a
             generate-validate-discard cycle.
Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
"""

import random
import logging
import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("R_Strategy_Protocol")

# --- Constants and Configuration ---
MAX_GENERATION_COST: float = 0.05  # Maximum cost allowed per script generation
DEFAULT_POPULATION_SIZE: int = 100
SURVIVAL_RATE: float = 0.1  # Top 10% survive to influence the next batch
MUTATION_FACTOR: float = 0.8  # High variability


class RStrategyError(Exception):
    """Custom exception for R-Strategy protocol failures."""
    pass


@dataclass
class CognitiveScript:
    """
    Represents a lightweight cognitive script (a 'variant').
    
    Attributes:
        script_id: Unique identifier for the script.
        logic_vector: A list of floats representing the 'logic' or weights of the script.
        source_domain: The domain this script was originally derived from (if any).
        fitness_score: The score assigned by the environment during validation.
        generation: The generation cycle this script belongs to.
        is_viable: Whether the script passed the minimal viability check.
    """
    script_id: str
    logic_vector: List[float]
    source_domain: str = "unknown"
    fitness_score: float = 0.0
    generation: int = 0
    is_viable: bool = False

    def __post_init__(self):
        if not isinstance(self.logic_vector, list):
            raise ValueError("logic_vector must be a list")
        if not all(isinstance(x, (float, int)) for x in self.logic_vector):
            raise ValueError("logic_vector must contain only numbers")


class RStrategyOrchestrator:
    """
    Orchestrates the R-Strategy protocol: Generate -> Validate -> Select.
    
    This class manages the population of cognitive scripts and drives the
    rapid evolutionary cycle to find a working solution for a target domain.
    """

    def __init__(self, target_domain: str, complexity_dim: int = 10):
        """
        Initialize the Orchestrator.
        
        Args:
            target_domain: The name of the new domain the AGI is trying to adapt to.
            complexity_dim: The dimensionality of the problem space (length of the logic vector).
        """
        self.target_domain = target_domain
        self.complexity_dim = complexity_dim
        self.current_generation = 0
        self.population: List[CognitiveScript] = []
        self.history: List[Dict[str, Any]] = []
        logger.info(f"R-Strategy Orchestrator initialized for domain: {target_domain}")

    def _generate_random_logic(self) -> List[float]:
        """Generates a random logic vector with high variance."""
        return [random.uniform(-1.0, 1.0) * random.choice([1, 10, 100]) 
                for _ in range(self.complexity_dim)]

    def _hash_script(self, logic: List[float]) -> str:
        """Creates a unique hash for a logic vector."""
        return hashlib.md5(json.dumps(logic).encode()).hexdigest()[:12]

    def generate_initial_batch(self, batch_size: int = DEFAULT_POPULATION_SIZE) -> List[CognitiveScript]:
        """
        Generates the initial population of 'hawker-level' scripts.
        
        These scripts are low-cost, mostly random, and designed for volume
        rather than precision.
        
        Args:
            batch_size: Number of scripts to generate.
        
        Returns:
            A list of unvalidated CognitiveScript objects.
        """
        if batch_size <= 0:
            raise RStrategyError("Batch size must be positive.")

        batch = []
        for _ in range(batch_size):
            logic = self._generate_random_logic()
            script = CognitiveScript(
                script_id=self._hash_script(logic),
                logic_vector=logic,
                source_domain="genesis_random",
                generation=self.current_generation
            )
            batch.append(script)
        
        logger.info(f"Generated {len(batch)} initial scripts for Gen {self.current_generation}")
        return batch

    def validate_batch(self, 
                       batch: List[CognitiveScript], 
                       environment_feedback: Callable[[List[float]], Tuple[bool, float]]
                       ) -> List[CognitiveScript]:
        """
        Validates a batch of scripts against the environment.
        
        This simulates the 'Try' phase of Try-Error. It uses an external
        feedback function to determine fitness.
        
        Args:
            batch: The list of scripts to test.
            environment_feedback: A callback function that takes a logic vector
                                 and returns (is_viable, fitness_score).
        
        Returns:
            A list of scripts that passed validation, sorted by fitness.
        """
        validated = []
        for script in batch:
            try:
                # Simulate resource check
                if random.random() < MAX_GENERATION_COST:
                    is_viable, score = environment_feedback(script.logic_vector)
                    script.is_viable = is_viable
                    script.fitness_score = score
                    if is_viable:
                        validated.append(script)
            except Exception as e:
                logger.warning(f"Script {script.script_id} crashed during validation: {e}")
                script.is_viable = False
        
        # Sort by score descending
        validated.sort(key=lambda s: s.fitness_score, reverse=True)
        logger.info(f"Validation complete. {len(validated)}/{len(batch)} scripts viable.")
        return validated

    def mutate_and_replicate(self, parents: List[CognitiveScript], count: int) -> List[CognitiveScript]:
        """
        Creates a new generation by mutating high-performing scripts.
        
        This implements the 'high variability' aspect of r-Strategy.
        
        Args:
            parents: The surviving scripts from the previous generation.
            count: How many new scripts to generate.
        
        Returns:
            A new batch of mutant scripts.
        """
        if not parents:
            logger.warning("No parents available for replication, reverting to random genesis.")
            return self.generate_initial_batch(count)

        new_batch = []
        self.current_generation += 1
        
        for _ in range(count):
            parent = random.choice(parents)
            
            # Deep copy logic
            new_logic = parent.logic_vector[:]
            
            # Apply high variability mutation
            mutation_idx = random.randint(0, len(new_logic) - 1)
            mutation_val = random.uniform(-1.0, 1.0) * MUTATION_FACTOR
            
            # Sometimes apply a massive shift (Punctuated Equilibrium)
            if random.random() < 0.1:
                mutation_val *= 10
            
            new_logic[mutation_idx] += mutation_val
            
            script = CognitiveScript(
                script_id=self._hash_script(new_logic),
                logic_vector=new_logic,
                source_domain=f"mutant_gen_{self.current_generation-1}",
                generation=self.current_generation
            )
            new_batch.append(script)
            
        return new_batch


# --- Helper Functions ---

def analyze_convergence(history: List[Dict[str, Any]], threshold: float = 0.9) -> bool:
    """
    Analyzes the history log to determine if the system has converged.
    
    Args:
        history: List of generation summary dictionaries.
        threshold: The target fitness score to consider the problem 'solved'.
    
    Returns:
        True if convergence is achieved, False otherwise.
    """
    if not history:
        return False
    
    latest = history[-1]
    if latest.get('best_score', 0) >= threshold:
        logger.info(f"Convergence achieved with score {latest['best_score']:.4f}")
        return True
    return False

def format_script_output(script: CognitiveScript) -> str:
    """
    Formats a successful cognitive script for display or storage.
    
    Args:
        script: The script to format.
    
    Returns:
        A JSON formatted string representation.
    """
    output = {
        "id": script.script_id,
        "score": script.fitness_score,
        "generation": script.generation,
        "logic_summary": [round(x, 3) for x in script.logic_vector]
    }
    return json.dumps(output, indent=2)


# --- Example Usage & Demonstration ---

if __name__ == "__main__":
    # 1. Define a mock environment (The "Problem")
    # Let's say the target domain requires a logic vector summing to approx 50.0
    # and the first element must be positive.
    def mock_environment_feedback(logic: List[float]) -> Tuple[bool, float]:
        total = sum(logic)
        score = 0.0
        viable = False
        
        # Criterion 1: Sum is close to 50
        diff = abs(total - 50.0)
        if diff < 10.0: # Loose constraint initially
            score += (10.0 - diff)
        
        # Criterion 2: First element positive
        if logic[0] > 0:
            score += 20.0
            viable = True
        
        return viable, score

    # 2. Initialize Protocol
    orchestrator = RStrategyOrchestrator(target_domain="td_66_finance_simulation", complexity_dim=5)
    
    # 3. Run Loop
    MAX_CYCLES = 20
    best_script = None
    
    logger.info("--- Starting R-Strategy Rapid Deployment ---")
    
    # Initial Gen
    population = orchestrator.generate_initial_batch(200)
    
    for cycle in range(MAX_CYCLES):
        logger.info(f"Cycle {cycle + 1} starting...")
        
        # Validate
        survivors = orchestrator.validate_batch(population, mock_environment_feedback)
        
        if survivors:
            current_best = survivors[0]
            logger.info(f"Current Best Score: {current_best.fitness_score:.2f}")
            
            # Check Convergence
            gen_stats = {"generation": cycle, "best_score": current_best.fitness_score}
            orchestrator.history.append(gen_stats)
            
            if analyze_convergence(orchestrator.history, threshold=25.0):
                best_script = current_best
                break
            
            # Select top 10% to be parents
            parents = survivors[:int(len(survivors) * SURVIVAL_RATE) + 1]
            
            # Reproduce
            population = orchestrator.mutate_and_replicate(parents, 200)
        else:
            # Total failure, restart
            logger.warning("Total extinction event. Re-seeding.")
            population = orchestrator.generate_initial_batch(200)

    # 4. Results
    print("\n" + "="*30)
    print("PROTOCOL EXECUTION FINISHED")
    print("="*30)
    
    if best_script:
        print("Successful 'Mutant' Found:")
        print(format_script_output(best_script))
    else:
        print("Protocol failed to find a viable solution within cycle limit.")