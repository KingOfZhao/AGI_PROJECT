"""
Module: epigenetic_cognitive_layer.py
Description: Implements the Epigenetic Cognitive Layer (ECL) for AGI systems.
             This module provides a dynamic adaptation mechanism that allows
             operational context ("phenotype") to override system defaults ("genotype")
             without altering the underlying codebase. It mimics biological epigenetics
             by applying configuration overlays based on real-time environmental data.

Author: Senior Python Engineer (AGI Systems)
Version: 1.0.0
License: MIT
"""

import json
import logging
import hashlib
import copy
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, ValidationError, Field, confloat

# --- Configuration & Logging ---

# Setting up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EpigeneticCognitiveLayer")


# --- Data Models ---

class OperationalContext(BaseModel):
    """
    Represents the 'Environment' or 'Diet' of the system.
    Validates incoming real-time data from the field (e.g., sensor readings, operator habits).
    """
    node_id: str
    temperature: confloat(ge=-20.0, le=100.0)  # Celsius
    operator_skill_level: confloat(ge=0.0, le=1.0)  # 0.0 (Novice) to 1.0 (Expert)
    network_latency_ms: float = Field(ge=0.0)
    timestamp: int


class SystemConfiguration(BaseModel):
    """
    Represents the 'Genotype' or base configuration of the system.
    The immutable default settings defined in code.
    """
    processing_timeout: float = 5.0
    verbosity: str = "INFO"
    safety_mode: str = "STANDARD"
    max_concurrent_tasks: int = 4
    algorithm_aggressiveness: float = 0.5


class EpigeneticProfile(BaseModel):
    """
    Represents the 'Phenotype'.
    The resulting configuration after applying environmental adaptations.
    """
    config_hash: str
    settings: Dict[str, Any]
    adaptation_reason: str


# --- Custom Exceptions ---

class EpigeneticError(Exception):
    """Base exception for Epigenetic Layer errors."""
    pass


class EnvironmentSensingError(EpigeneticError):
    """Raised when environmental data is invalid or corrupted."""
    pass


class AdaptationConflictError(EpigeneticError):
    """Raised when adaptation rules conflict critically."""
    pass


# --- Core Functions ---

class EpigeneticCognitiveLayer:
    """
    The core class that manages the mapping between Environmental Context
    and System Configuration overlays.
    """

    def __init__(self, base_genome: SystemConfiguration):
        """
        Initializes the layer with a standard genetic code (base configuration).
        
        Args:
            base_genome (SystemConfiguration): The immutable default settings.
        """
        self._base_genome = base_genome.dict()
        self._cache: Dict[str, EpigeneticProfile] = {}
        logger.info("Epigenetic Cognitive Layer initialized with base genome.")

    def _generate_adaptation_rules(self, context: OperationalContext) -> Dict[str, Any]:
        """
        [Internal Logic] Translates environmental factors into configuration deltas.
        This acts as the 'Ribosome' of the system, translating RNA (Context)
        into Proteins (Config Changes).
        
        Args:
            context (OperationalContext): Validated environmental data.
            
        Returns:
            Dict[str, Any]: A dictionary of configuration patches.
        """
        patches: Dict[str, Any] = {}

        # Rule 1: Temperature Adaptation (Hardware Constraint)
        if context.temperature > 45.0:
            patches["safety_mode"] = "THERMAL_THROTTLE"
            patches["max_concurrent_tasks"] = 2
            logger.debug(f"Applying Thermal Throttle rules for {context.node_id}")
        
        # Rule 2: Operator Skill Adaptation (UX Personalization)
        if context.operator_skill_level < 0.4:
            patches["verbosity"] = "DEBUG"
            patches["algorithm_aggressiveness"] = 0.1  # Conservative behavior
            patches["safety_mode"] = "HIGH_VISIBILITY"
        elif context.operator_skill_level > 0.8:
            patches["verbosity"] = "ERROR"
            patches["algorithm_aggressiveness"] = 0.9  # Aggressive optimization

        # Rule 3: Network Condition Adaptation
        if context.network_latency_ms > 200.0:
            patches["processing_timeout"] = 15.0
            
        return patches

    def adapt(self, raw_context_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Main Entry Point. Processes environmental data and returns the adapted configuration.
        
        Args:
            raw_context_data (Dict[str, Any]): Raw input from the 'field'.
            
        Returns:
            Tuple[Dict[str, Any], str]: (The final adapted configuration, The profile ID)
            
        Raises:
            EnvironmentSensingError: If input data validation fails.
        """
        try:
            # 1. Sensing (Validation)
            context = OperationalContext(**raw_context_data)
            logger.info(f"Sensing environment for Node: {context.node_id}")
            
            # Check cache for efficiency
            cache_key = self._compute_context_hash(context)
            if cache_key in self._cache:
                logger.info(f"Retrieved cached Epigenetic Profile: {cache_key}")
                return self._cache[cache_key].settings, cache_key

            # 2. Transcription (Generating Rules)
            adaptation_patches = self._generate_adaptation_rules(context)
            
            # 3. Expression (Merging Configurations)
            # Deep copy to ensure base genome is never modified (Immutability)
            expressed_config = copy.deepcopy(self._base_genome)
            
            # Apply patches (Epigenetic markers)
            for key, value in adaptation_patches.items():
                if key in expressed_config:
                    expressed_config[key] = value
                    logger.debug(f"Overriding config '{key}': {self._base_genome[key]} -> {value}")
                else:
                    # Allow dynamic extension if needed, though strict validation is preferred
                    logger.warning(f"Attempted to modify non-genetic key: {key}")

            # 4. Validation of Result
            # Ensure the new configuration is still valid logic-wise
            if (expressed_config['algorithm_aggressiveness'] > 0.8 and 
                expressed_config['safety_mode'] == 'THERMAL_THROTTLE'):
                logger.warning("Conflict detected: High aggression in thermal throttle. Reverting to safe defaults.")
                expressed_config['algorithm_aggressiveness'] = 0.2

            # 5. Packaging and Caching
            profile = EpigeneticProfile(
                config_hash=cache_key,
                settings=expressed_config,
                adaptation_reason=f"Adapted to T:{context.temperature}, Skill:{context.operator_skill_level}"
            )
            self._cache[cache_key] = profile
            
            logger.info(f"New Epigenetic Profile generated: {cache_key}")
            return expressed_config, cache_key

        except ValidationError as e:
            logger.error(f"Environmental data validation failed: {e}")
            raise EnvironmentSensingError(f"Invalid sensor data: {e}") from e
        except Exception as e:
            logger.critical(f"Unexpected error during adaptation: {e}")
            raise EpigeneticError("System adaptation failed.") from e

    def _compute_context_hash(self, context: OperationalContext) -> str:
        """
        Helper function to create a unique hash for a specific environmental state.
        Allows for caching of configurations to avoid re-computation.
        """
        # Normalize data for hashing
        data_str = f"{context.node_id}-{context.temperature:.1f}-{context.operator_skill_level:.2f}"
        return hashlib.md5(data_str.encode()).hexdigest()


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Define the 'Genetic Code' (Base Code)
    default_config = SystemConfiguration()
    ecl = EpigeneticCognitiveLayer(default_config)

    # 2. Simulate 'Environmental Input' from a field node (e.g., a street vendor terminal)
    # Scenario: A hot day, novice operator, poor network
    field_data = {
        "node_id": "vendor_node_8849",
        "temperature": 48.5,
        "operator_skill_level": 0.2,
        "network_latency_ms": 350.0,
        "timestamp": 1678900000
    }

    print("\n--- Initiating Epigenetic Adaptation ---")
    print(f"Raw Field Data: {json.dumps(field_data, indent=2)}")

    try:
        # 3. Run Adaptation
        adapted_settings, profile_id = ecl.adapt(field_data)

        print(f"\nAdaptation Profile ID: {profile_id}")
        print("Final Active Configuration (Phenotype):")
        print(json.dumps(adapted_settings, indent=2))
        
        print("\n--- Comparison ---")
        print(f"Safety Mode changed: {default_config.safety_mode} -> {adapted_settings['safety_mode']}")
        print(f"Timeout changed: {default_config.processing_timeout} -> {adapted_settings['processing_timeout']}")

    except EpigeneticError as e:
        print(f"Critical Failure: {e}")