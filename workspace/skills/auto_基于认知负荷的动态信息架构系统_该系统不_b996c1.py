"""
Module: cognitive_adaptive_architecture.py

This module implements a dynamic information architecture system based on cognitive load theory.
It dynamically adjusts data structures between normalized (detail-oriented) and denormalized
(performance-oriented) states based on real-time user cognitive state monitoring.

Classes:
    CognitiveState: Data class representing user's current cognitive metrics.
    DataRecord: Represents a unit of information with dual storage modes.
    CognitiveArchitectureSystem: The core controller for the adaptive system.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataSchemaMode(Enum):
    """Enumeration for data schema states."""
    HIGH_NORMALIZATION = auto()  # Exploration mode: Detailed, normalized, space-efficient
    DENORMALIZED = auto()        # Cognitive Overload mode: Redundant, speed-efficient


@dataclass
class CognitiveState:
    """
    Represents the real-time cognitive state of the user.
    
    Attributes:
        eye_movement_frequency (float): Hz, frequency of saccades.
        interaction_latency (float): Seconds, delay in user response.
        pupil_dilation (float): Relative change in pupil size.
        is_overloaded (bool): Calculated flag indicating cognitive overload.
    """
    eye_movement_frequency: float
    interaction_latency: float
    pupil_dilation: float
    is_overloaded: bool = field(init=False)

    def __post_init__(self):
        """Validate inputs and calculate overload status."""
        if self.eye_movement_frequency < 0:
            raise ValueError("Eye movement frequency cannot be negative")
        if self.interaction_latency < 0:
            raise ValueError("Interaction latency cannot be negative")
            
        # Heuristic: High latency + High saccades + High dilation = Overload
        # Thresholds are hypothetical for simulation
        score = (self.interaction_latency * 10) + (self.eye_movement_frequency * 0.5) + (self.pupil_dilation * 2)
        self.is_overloaded = score > 15.0
        logger.debug(f"Cognitive score: {score}, Overload: {self.is_overloaded}")


@dataclass
class DataRecord:
    """
    Represents a data entity capable of switching between Normalized and Denormalized states.
    
    Normalized State: Stores references (IDs) requiring joins to understand context.
    Denormalized State: Stores pre-calculated summaries and embedded values.
    """
    record_id: str
    raw_data: Dict[str, Any]
    schema_mode: DataSchemaMode = DataSchemaMode.HIGH_NORMALIZATION
    cached_denormalized_view: Optional[str] = None
    
    def switch_mode(self, target_mode: DataSchemaMode, context_data: Optional[Dict] = None) -> None:
        """
        Switch the active schema mode of the data.
        Performs 'Denormalization' by creating a cached view if moving to overload mode.
        """
        if self.schema_mode == target_mode:
            return

        logger.info(f"Switching record {self.record_id} from {self.schema_mode.name} to {target_mode.name}")
        
        if target_mode == DataSchemaMode.DENORMALIZED:
            # Simulate expensive computation/pre-joining (The "Redundancy" cost)
            # In a real DB, this might involve creating a Materialized View
            time.sleep(0.01) # Simulate processing cost
            
            # Create a readable summary (Redundant data generation)
            details = context_data or {}
            summary = (
                f"Summary for {self.record_id}: "
                f"Status={self.raw_data.get('status', 'N/A')}, "
                f"Owner={details.get('owner_name', 'System')}, "
                f"Value={self.raw_data.get('value', 0) * 1.15}" # Pre-calculated adjustment
            )
            self.cached_denormalized_view = summary
            
        else:
            # Returning to Normalized mode: discard redundancy to save space/focus on details
            self.cached_denormalized_view = None
            
        self.schema_mode = target_mode

    def get_display_data(self) -> Dict[str, Any]:
        """Returns data appropriate for the current mode."""
        if self.schema_mode == DataSchemaMode.DENORMALIZED and self.cached_denormalized_view:
            return {
                "id": self.record_id,
                "quick_view": self.cached_denormalized_view,
                "type": "optimized_for_speed"
            }
        else:
            return {
                "id": self.record_id,
                "details": self.raw_data,
                "type": "source_of_truth"
            }


class CognitiveArchitectureSystem:
    """
    The core system that monitors user state and adjusts the information architecture.
    
    It acts as a mediator between the user's biological limitations and the system's
    data storage logic.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.data_store: List[DataRecord] = []
        self.external_context: Dict[str, Dict] = {} # Simulating a foreign key lookup table
        self.current_system_mode: DataSchemaMode = DataSchemaMode.HIGH_NORMALIZATION
        logger.info(f"System initialized for user {user_id}")

    def ingest_data(self, raw_records: List[Dict[str, Any]]) -> None:
        """Ingests raw data into the system in normalized format."""
        for rec in raw_records:
            if not isinstance(rec, dict):
                logger.warning("Invalid record format skipped")
                continue
            
            record_id = rec.get("id", str(uuid.uuid4()))
            new_record = DataRecord(record_id=record_id, raw_data=rec)
            self.data_store.append(new_record)
        
        logger.info(f"Ingested {len(raw_records)} records.")

    def monitor_and_adapt(self, cognitive_state: CognitiveState) -> None:
        """
        Core Function 1: Analyzes cognitive state and triggers architecture adaptation.
        
        Args:
            cognitive_state (CognitiveState): The current state of the user.
        """
        target_mode = DataSchemaMode.HIGH_NORMALIZATION
        
        if cognitive_state.is_overloaded:
            logger.warning("Cognitive Overload Detected! Switching to Denormalized Architecture.")
            target_mode = DataSchemaMode.DENORMALIZED
        else:
            logger.info("User in Exploration Mode. Maintaining Normalized Architecture.")
            target_mode = DataSchemaMode.HIGH_NORMALIZATION

        if self.current_system_mode != target_mode:
            self._execute_architecture_shift(target_mode)
            self.current_system_mode = target_mode

    def _execute_architecture_shift(self, target_mode: DataSchemaMode) -> None:
        """
        Helper Function: Iterates through data store and updates schemas.
        Handles the actual data transformation logic.
        """
        logger.info(f"--- Beginning Architecture Shift to {target_mode.name} ---")
        start_time = time.time()
        
        for record in self.data_store:
            # Look up context if needed for denormalization
            context = self.external_context.get(record.record_id, {})
            record.switch_mode(target_mode, context)
            
        end_time = time.time()
        logger.info(f"--- Shift Completed in {end_time - start_time:.4f}s ---")

    def get_user_interface_payload(self) -> List[Dict]:
        """
        Core Function 2: Retrieves the data formatted for the current UI state.
        """
        return [rec.get_display_data() for rec in self.data_store]

    def update_external_context(self, context_map: Dict[str, Dict]) -> None:
        """Updates context used for denormalization (e.g., User names for IDs)."""
        self.external_context.update(context_map)


def simulate_system_usage():
    """Example usage of the Cognitive Architecture System."""
    
    # 1. Setup System
    system = CognitiveArchitectureSystem(user_id="user_123")
    
    # 2. Load Data (Normalized state initially)
    raw_data = [
        {"id": "order_1", "status": "pending", "value": 100, "owner_id": "u_55"},
        {"id": "order_2", "status": "shipped", "value": 200, "owner_id": "u_99"},
    ]
    system.ingest_data(raw_data)
    
    # Context for potential joins (e.g., User names)
    system.update_external_context({
        "order_1": {"owner_name": "Alice"},
        "order_2": {"owner_name": "Bob"}
    })

    print("\n--- SCENARIO A: Relaxed User (Exploration) ---")
    # Low latency, low stress
    state_relaxed = CognitiveState(
        eye_movement_frequency=2.0, interaction_latency=0.1, pupil_dilation=0.1
    )
    
    system.monitor_and_adapt(state_relaxed)
    payload = system.get_user_interface_payload()
    print("UI Data (Detailed):", payload[0]) # Shows raw data structure

    print("\n--- SCENARIO B: Stressed User (Overload) ---")
    # High latency, erratic eyes
    state_stressed = CognitiveState(
        eye_movement_frequency=15.0, interaction_latency=2.5, pupil_dilation=1.5
    )
    
    system.monitor_and_adapt(state_stressed)
    payload = system.get_user_interface_payload()
    print("UI Data (Simplified):", payload[0]) # Shows pre-calculated summary

if __name__ == "__main__":
    simulate_system_usage()