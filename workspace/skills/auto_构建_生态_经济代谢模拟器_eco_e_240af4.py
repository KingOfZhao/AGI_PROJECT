"""
Module: eco_economic_metabolic_simulator
Description: Builds an 'Eco-Economic Metabolic Simulator'.
This module simulates the interaction between economic activities and ecological systems
by introducing physical constraints (Energy, Entropy) and biological dynamics (Trophic Cascades).
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TrophicLevel(Enum):
    """Enumeration of ecological trophic levels."""
    PRODUCER = 1      # Plants, Photosynthesis
    PRIMARY_CONSUMER = 2  # Herbivores
    SECONDARY_CONSUMER = 3 # Carnivores
    DECOMPOSER = 4    # Fungi, Bacteria

@dataclass
class EconomicAgent:
    """Represents an economic entity acting within the ecosystem."""
    agent_id: str
    trophic_level: TrophicLevel
    monetary_capital: float  # In standard currency units
    energy_requirement: float  # In Joules per cycle
    efficiency: float = 0.20  # Energy conversion efficiency (default 20%)
    waste_generation_rate: float = 0.1  # Entropy generation factor

@dataclass
class EcoEcoState:
    """Snapshot of the combined system state."""
    cycle: int
    total_biomass_energy: float  # Available ecological energy (Joules)
    entropy_accumulated: float
    energy_monetary_exchange_rate: float  # Currency per Joule
    agents: List[EconomicAgent] = field(default_factory=list)

class EcoEconomicMetabolicSimulator:
    """
    A simulator that models economic activities as metabolic processes within an ecosystem.
    
    It replaces purely monetary metrics with bio-physical constraints, calculating the
    'real' cost of economic growth via entropy and energy dissipation.
    
    Attributes:
        initial_energy (float): Total initial energy budget of the ecosystem.
        max_entropy (float): The entropy limit beyond which the system collapses.
        decay_rate (float): Natural energy decay/dissipation rate.
    """

    def __init__(self, initial_energy: float, max_entropy: float, decay_rate: float = 0.02):
        """
        Initialize the simulator.
        
        Args:
            initial_energy (float): The starting energy budget (e.g., solar input * biomass).
            max_entropy (float): Carrying capacity limit in terms of disorder.
            decay_rate (float): Rate at which unused energy is lost to the environment.
        """
        if initial_energy <= 0:
            raise ValueError("Initial energy must be positive.")
        if max_entropy <= 0:
            raise ValueError("Max entropy must be positive.")
            
        self.state = EcoEcoState(
            cycle=0,
            total_biomass_energy=initial_energy,
            entropy_accumulated=0.0,
            energy_monetary_exchange_rate=0.0, # Calculated dynamically
            agents=[]
        )
        self.max_entropy = max_entropy
        self.decay_rate = decay_rate
        logger.info(f"Simulator initialized with Energy: {initial_energy}J, Max Entropy: {max_entropy}")

    def add_agent(self, agent: EconomicAgent) -> None:
        """Register an economic agent in the simulation."""
        if not isinstance(agent, EconomicAgent):
            raise TypeError("Invalid agent type.")
        self.state.agents.append(agent)
        logger.debug(f"Agent {agent.agent_id} added at level {agent.trophic_level.name}")

    def _calculate_exchange_rate(self) -> float:
        """
        Core Logic: Calculate the Energy-Money Exchange Rate.
        
        Formula:
        Rate = (Total Economic Demand) / (Available Biological Capacity)
        
        As energy becomes scarce relative to money, the 'price' of energy rises,
        representing inflation in physical terms.
        """
        total_monetary_demand = sum(a.monetary_capital for a in self.state.agents)
        available_energy = self.state.total_biomass_energy

        if available_energy <= 0:
            logger.warning("System Collapse: Energy depleted.")
            return float('inf') # Infinite cost

        # Scarcity factor: High money chasing low energy creates high 'physical' inflation
        base_rate = 1.0
        scarcity_multiplier = (total_monetary_demand / available_energy) * 0.001
        return base_rate + scarcity_multiplier

    def _apply_trophic_cascade(self) -> Dict[str, float]:
        """
        Core Logic: Simulate Trophic Cascade effects.
        
        If primary producers (Level 1) are over-consumed, higher levels suffer
        non-linear decline. This models the 'tragedy of the commons' physically.
        
        Returns:
            Dict mapping agent_id to energy harvested.
        """
        harvested_energy_log = {}
        
        # Group agents by level
        levels: Dict[int, List[EconomicAgent]] = {1: [], 2: [], 3: [], 4: []}
        for agent in self.state.agents:
            levels[agent.trophic_level.value].append(agent)

        # 1. Producers consume solar/abiotic energy
        producer_consumption = 0.0
        for producer in levels.get(1, []):
            # Producers 'eat' from the main pool
            consumption = min(producer.energy_requirement, self.state.total_biomass_energy)
            producer_consumption += consumption
            harvested_energy_log[producer.agent_id] = consumption
        
        self.state.total_biomass_energy -= producer_consumption

        # 2. Consumers eat producers or lower consumers
        # Simplified cascade: Level N consumes remaining energy from Level N-1's waste/biomass
        # Transfer efficiency is typically 10% (Lindeman's law), modified by agent efficiency
        
        current_biomass_pool = producer_consumption # Energy fixed by producers
        
        for level_val in [2, 3, 4]:
            consumers = levels.get(level_val, [])
            if not consumers:
                continue
                
            pool_for_this_level = current_biomass_pool * 0.2 # Approximate trophic transfer loss
            
            for consumer in consumers:
                # Predation pressure
                needed = consumer.energy_requirement
                harvested = min(needed, pool_for_this_level * consumer.efficiency)
                
                pool_for_this_level -= harvested
                harvested_energy_log[consumer.agent_id] = harvested
                
                # Check for collapse conditions
                if harvested < needed * 0.5:
                    logger.warning(f"Trophic Stress: Agent {consumer.agent_id} is energy starved.")
            
            # Pass remaining biomass up the chain (with heavy losses)
            current_biomass_pool = pool_for_this_level

        return harvested_energy_log

    def step(self) -> bool:
        """
        Execute one simulation cycle (Metabolic Step).
        
        Returns:
            bool: True if system survives, False if collapsed.
        """
        self.state.cycle += 1
        logger.info(f"--- Cycle {self.state.cycle} ---")

        # 1. Update Exchange Rate
        rate = self._calculate_exchange_rate()
        self.state.energy_monetary_exchange_rate = rate

        # 2. Metabolism & Trophic Dynamics
        harvested = self._apply_trophic_cascade()

        # 3. Entropy Generation (Waste)
        # Economic activity generates entropy. 
        # Entropy = (Energy Used) * (1 - Efficiency) + BaseMetabolism
        cycle_entropy = 0.0
        for agent in self.state.agents:
            e_harvested = harvested.get(agent.agent_id, 0.0)
            waste = e_harvested * (1 - agent.efficiency) * agent.waste_generation_rate
            cycle_entropy += waste
            
            # Economic Growth logic (simplified): If energy needs met, capital grows
            if e_harvested >= agent.energy_requirement * 0.8:
                agent.monetary_capital *= 1.05 # 5% growth
            else:
                agent.monetary_capital *= 0.95 # Recession

        self.state.entropy_accumulated += cycle_entropy

        # 4. Natural Decay and Regeneration
        self.state.total_biomass_energy *= (1 - self.decay_rate)
        # Producers regenerate energy (e.g., photosynthesis) - fixed influx
        # Assuming closed system for this model or limited influx
        self.state.total_biomass_energy += 5000.0 # Solar injection constant

        # 5. Boundary Check
        if self.state.entropy_accumulated > self.max_entropy:
            logger.critical("ECO-ECONOMIC COLLAPSE: Entropy limit exceeded.")
            return False
        
        if self.state.total_biomass_energy < 100:
            logger.critical("ECO-ECONOMIC COLLAPSE: Resource depletion.")
            return False

        logger.info(f"Status - Energy: {self.state.total_biomass_energy:.2f}J, "
                    f"Entropy: {self.state.entropy_accumulated:.2f}, "
                    f"Rate: {rate:.4f}")
        
        return True

    def forecast_limits(self, steps: int = 10) -> Optional[Tuple[float, float]]:
        """
        Forecast the optimal boundary of economic activity based on current trends.
        
        Args:
            steps (int): Number of cycles to project.
            
        Returns:
            Tuple[float, float]: Projected (Energy, Entropy) at the horizon.
        """
        if steps <= 0:
            return None
            
        # Simple linear projection (for complex systems, use Kalman filters inside)
        # Calculate average entropy growth per step
        if self.state.cycle == 0:
            return (self.state.total_biomass_energy, 0.0)
            
        avg_entropy_rate = self.state.entropy_accumulated / self.state.cycle
        
        projected_entropy = self.state.entropy_accumulated + (avg_entropy_rate * steps)
        
        # Warning check
        if projected_entropy > self.max_entropy * 0.8:
            logger.warning(f"Forecast Warning: Entropy approaching critical threshold in {steps} cycles.")
            
        return (self.state.total_biomass_energy, projected_entropy)

# Usage Example
if __name__ == "__main__":
    # 1. Setup Environment
    simulator = EcoEconomicMetabolicSimulator(
        initial_energy=100_000.0,  # 100 kJ equivalent
        max_entropy=50_000.0,
        decay_rate=0.01
    )

    # 2. Define Economic Agents (Sectors)
    # Agriculture (Primary Producer)
    ag_sector = EconomicAgent(
        agent_id="Agri_Corp", 
        trophic_level=TrophicLevel.PRODUCER,
        monetary_capital=10_000,
        energy_requirement=5_000,
        efficiency=0.4 # High efficiency
    )

    # Manufacturing (Secondary Consumer - eats raw materials)
    mfg_sector = EconomicAgent(
        agent_id="Manuf_Inc",
        trophic_level=TrophicLevel.SECONDARY_CONSUMER,
        monetary_capital=50_000,
        energy_requirement=8_000,
        efficiency=0.15 # Lower efficiency, high waste
    )

    simulator.add_agent(ag_sector)
    simulator.add_agent(mfg_sector)

    # 3. Run Simulation
    is_alive = True
    cycle_count = 0
    while is_alive and cycle_count < 20:
        is_alive = simulator.step()
        cycle_count += 1
        
        # Check forecast
        if cycle_count % 5 == 0:
            forecast = simulator.forecast_limits(5)
            if forecast:
                logger.info(f"Forecast -> Entropy: {forecast[1]:.2f} / {simulator.max_entropy}")

    # 4. Output Final State
    print("\n--- Final State ---")
    print(f"Survived: {is_alive}")
    print(f"Final Energy Reserves: {simulator.state.total_biomass_energy:.2f}")
    print(f"Final Entropy Level: {simulator.state.entropy_accumulated:.2f}")
    print(f"Final Exchange Rate: {simulator.state.energy_monetary_exchange_rate:.4f}")