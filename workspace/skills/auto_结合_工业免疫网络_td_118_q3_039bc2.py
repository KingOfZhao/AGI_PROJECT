"""
Module: auto_immune_homeostasis.py
Description: Implements an AGI 'Industrial Immune Network' combined with 'Epigenetic Configuration'
             and 'Cognitive Metabolic Homeostasis'. This system mimics biological self-repair
             by detecting external threats (antigens) or internal resource stress (metabolic pressure)
             and automatically adjusting configuration (gene expression) or activating backup
             pathways (immune response) to ensure systemic survival without human intervention.
Domain: Cross-Domain (Industrial AI / Bio-Inspired Computing)
"""

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AGI_Immune_Homeostasis")


class SystemState(Enum):
    """Enumeration of possible system health states."""
    HEALTHY = auto()
    STRESSED = auto()      # Metabolic pressure detected
    INFECTED = auto()      # External attack detected
    RECOVERING = auto()    # Active self-repair in progress
    CRITICAL = auto()      # System failure imminent


@dataclass
class MetabolicStatus:
    """Represents the internal resource state of the system."""
    cpu_load: float = 0.0      # 0.0 to 1.0
    memory_usage: float = 0.0  # 0.0 to 1.0
    energy_level: float = 1.0  # 1.0 is full, 0.0 is empty

    def is_stressed(self, threshold: float = 0.85) -> bool:
        """Check if system is under metabolic stress."""
        return self.cpu_load > threshold or self.memory_usage > threshold or self.energy_level < 0.2


@dataclass
class ExternalSignal:
    """Represents an incoming signal from the environment (potentially an antigen)."""
    source_id: str
    signal_type: str  # e.g., 'API_REQUEST', 'NETWORK_PACKET', 'UNKNOWN'
    payload: bytes
    threat_score: float = 0.0  # 0.0 (safe) to 1.0 (malicious)


@dataclass
class EpigeneticConfig:
    """
    Represents the 'Genetic Configuration' of the system.
    These parameters can be dynamically adjusted (mutated) to adapt to stress.
    """
    max_throughput: int = 1000
    redundancy_level: int = 1      # Number of backup active nodes
    defense_sensitivity: float = 0.5  # Threshold to trigger immune response
    repair_rate: float = 0.1       # Speed of self-repair

    def mutate_for_survival(self, stress_factor: float):
        """
        Adjusts configuration based on stress.
        Similar to gene expression changes in biology.
        """
        logger.info(f"Mutating epigenetic configuration due to stress factor: {stress_factor:.2f}")
        if stress_factor > 0.8:
            self.redundancy_level = min(5, self.redundancy_level + 1)
            self.defense_sensitivity = min(1.0, self.defense_sensitivity + 0.1)
            self.max_throughput = int(self.max_throughput * 0.8)  # Reduce load
            logger.warning("High stress: Increased redundancy, lowered throughput.")
        elif stress_factor < 0.3:
            # Relax if stress is low to save resources
            self.redundancy_level = max(1, self.redundancy_level - 1)
            self.max_throughput = int(self.max_throughput * 1.05)


class IndustrialImmuneSystem:
    """
    Core AGI Skill: Combines Immune Network, Epigenetics, and Metabolic Homeostasis.
    """

    def __init__(self, initial_config: Optional[EpigeneticConfig] = None):
        self.config = initial_config or EpigeneticConfig()
        self.state = SystemState.HEALTHY
        self.metabolism = MetabolicStatus()
        self.memory_b_cells: Dict[str, float] = {}  # Stores patterns of known threats
        self._startup_time = time.time()
        logger.info("Industrial Immune System initialized.")

    def _detect_antigen(self, signal: ExternalSignal) -> bool:
        """
        Core Function 1: Threat Detection (Innate and Adaptive Immunity).
        Analyzes input signals to determine if they are malicious (antigens).
        """
        # Adaptive immunity: Check memory cells for known threats
        if signal.source_id in self.memory_b_cells:
            if self.memory_b_cells[signal.source_id] > 0.8:
                logger.warning(f"Detected known threat from source: {signal.source_id}")
                return True

        # Innate immunity: Heuristic analysis of payload and type
        is_suspicious_type = signal.signal_type not in ["API_REQUEST", "SYSTEM_HEARTBEAT"]
        is_high_threat = signal.threat_score > self.config.defense_sensitivity
        
        # Simple anomaly detection logic
        if is_suspicious_type and is_high_threat:
            logger.warning(f"Detected novel antigen from {signal.source_id} (Score: {signal.threat_score})")
            # "Vaccinate" memory - learn the pattern
            self.memory_b_cells[signal.source_id] = signal.threat_score
            return True
        
        return False

    def _regulate_homeostasis(self, current_load: Dict[str, float]) -> Tuple[SystemState, float]:
        """
        Core Function 2: Cognitive Metabolic Homeostasis.
        Monitors internal resources and triggers stress responses.
        """
        # Update internal metabolic state
        self.metabolism.cpu_load = current_load.get('cpu', 0.0)
        self.metabolism.memory_usage = current_load.get('mem', 0.0)
        self.metabolism.energy_level = current_load.get('energy', 1.0)

        stress_val = 0.0
        new_state = SystemState.HEALTHY

        if self.metabolism.is_stressed():
            stress_val = max(self.metabolism.cpu_load, self.metabolism.memory_usage)
            new_state = SystemState.STRESSED
            logger.debug(f"Metabolic stress detected. CPU: {self.metabolism.cpu_load}, Mem: {self.metabolism.memory_usage}")
        
        # Update system state
        self.state = new_state
        return self.state, stress_val

    def activate_backup_pathways(self):
        """
        Auxiliary Function: Activates backup systems (immune response/repair).
        Represents the physical activation of standby nodes or redundant code paths.
        """
        logger.info(f"Activating {self.config.redundancy_level} redundant backup pathways...")
        # Simulate resource cost of activation
        self.metabolism.energy_level -= 0.05 
        
        # Simulate repair process
        repair_effect = self.config.repair_rate * random.uniform(0.8, 1.2)
        self.metabolism.cpu_load = max(0, self.metabolism.cpu_load - repair_effect)
        logger.info(f"System repair applied. Load reduced by {repair_effect:.3f}")

    def process_cycle(self, external_signals: List[ExternalSignal], system_load: Dict[str, float]) -> SystemState:
        """
        Main execution loop for the skill. Integrates all components.
        """
        logger.info("--- Starting AGI Cycle ---")

        # 1. Metabolic Check (Homeostasis)
        current_state, stress_level = self._regulate_homeostasis(system_load)

        # 2. Epigenetic Adjustment (Configure based on stress)
        if current_state == SystemState.STRESSED:
            self.config.mutate_for_survival(stress_level)

        # 3. Immune Surveillance (Scan inputs)
        threat_detected = False
        for signal in external_signals:
            if self._detect_antigen(signal):
                threat_detected = True
                self.state = SystemState.INFECTED
                break # Stop processing on first threat detection

        # 4. Response Execution
        if self.state == SystemState.INFECTED or self.state == SystemState.STRESSED:
            self.activate_backup_pathways()
            self.state = SystemState.RECOVERING
        elif self.state == SystemState.RECOVERING:
            # Logic to check if recovery is complete
            if not self.metabolism.is_stressed() and not threat_detected:
                self.state = SystemState.HEALTHY
                logger.info("System restored to healthy state.")

        logger.info(f"Cycle End State: {self.state.name}")
        return self.state

# Data Validation Helper
def validate_system_load(load_data: Dict[str, float]) -> bool:
    """Validates that load data is within logical bounds [0.0, 1.0]."""
    try:
        for key, val in load_data.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Invalid type for {key}")
            if not (0.0 <= val <= 1.0):
                logger.error(f"Out of bounds value for {key}: {val}")
                return False
        return True
    except Exception as e:
        logger.error(f"Load validation failed: {e}")
        return False

# Example Usage
if __name__ == "__main__":
    # Initialize System
    config = EpigeneticConfig(max_throughput=1200, defense_sensitivity=0.6)
    agi_system = IndustrialImmuneSystem(initial_config=config)

    # Simulation Data 1: Normal operation
    normal_signals = [
        ExternalSignal("client_1", "API_REQUEST", b"data", 0.1),
        ExternalSignal("sensor_5", "SYSTEM_HEARTBEAT", b"ping", 0.0)
    ]
    normal_load = {'cpu': 0.4, 'mem': 0.5, 'energy': 0.9}

    # Simulation Data 2: Under attack
    attack_signals = [
        ExternalSignal("unknown_ip", "UNKNOWN", b"malicious_payload", 0.95)
    ]
    
    # Simulation Data 3: Resource exhaustion
    stress_load = {'cpu': 0.95, 'mem': 0.98, 'energy': 0.15}

    # Run Cycles
    print("\n=== CYCLE 1: NORMAL ===")
    if validate_system_load(normal_load):
        agi_system.process_cycle(normal_signals, normal_load)

    print("\n=== CYCLE 2: ATTACK ===")
    if validate_system_load(normal_load): # Using normal load for this scenario
        agi_system.process_cycle(attack_signals, normal_load)

    print("\n=== CYCLE 3: STRESS & RECOVERY ===")
    if validate_system_load(stress_load):
        agi_system.process_cycle(normal_signals, stress_load)