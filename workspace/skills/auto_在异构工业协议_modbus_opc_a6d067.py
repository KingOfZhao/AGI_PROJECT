"""
SKILL: auto_在异构工业协议_modbus_opc_a6d067
Description: Heterogeneous Industrial Protocol Semantic Adapter for AGI Systems.

This module provides a universal semantic adaptation layer for edge computing 
scenarios where heterogeneous industrial protocols (Modbus, OPC UA, Profinet, etc.) 
coexist. It converts raw, time-series data streams into standardized AGI 'State Nodes',
ensuring temporal synchronization and semantic consistency.

Domain: edge_computing
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_SemanticAdapter")

class ProtocolType(Enum):
    """Enumeration of supported industrial protocols."""
    MODBUS_TCP = "MODBUS_TCP"
    OPC_UA = "OPC_UA"
    PROFINET = "PROFINET"
    UNKNOWN = "UNKNOWN"

class SemanticType(Enum):
    """Target semantic types for AGI cognitive network."""
    TEMPERATURE = "TEMPERATURE"
    PRESSURE = "PRESSURE"
    VELOCITY = "VELOCITY"
    BOOLEAN_STATUS = "BOOLEAN_STATUS"
    GENERIC_METRIC = "GENERIC_METRIC"

@dataclass
class RawDataPayload:
    """Input data structure from edge devices."""
    source_id: str
    protocol: ProtocolType
    timestamp: float  # Unix timestamp
    raw_value: Union[int, float, bool, str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AGIStateNode:
    """
    Output data structure for AGI Cognitive Network.
    Represents a standardized state node.
    """
    node_id: str
    semantic_type: SemanticType
    timestamp: float
    normalized_value: float
    confidence_score: float  # 0.0 to 1.0
    context_tags: Dict[str, str] = field(default_factory=dict)

class SemanticMapper:
    """
    Handles the mapping logic from raw protocol values to semantic types.
    """
    def __init__(self):
        self._mapping_rules: Dict[str, Dict[str, Any]] = {}

    def add_rule(self, source_id: str, semantic_type: SemanticType, 
                 range_min: float, range_max: float, unit: str):
        """
        Adds a semantic mapping rule for a specific data source.
        """
        if range_min >= range_max:
            raise ValueError(f"Invalid range for {source_id}: min must be < max")
        
        self._mapping_rules[source_id] = {
            "type": semantic_type,
            "min": range_min,
            "max": range_max,
            "unit": unit
        }
        logger.info(f"Mapping rule added: {source_id} -> {semantic_type.value}")

    def get_rule(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self._mapping_rules.get(source_id)

class HeterogeneousProtocolAdapter:
    """
    Core adapter class to normalize heterogeneous industrial data into AGI State Nodes.
    """

    def __init__(self, time_sync_tolerance_ms: float = 100.0):
        """
        Initialize the adapter.

        Args:
            time_sync_tolerance_ms: Maximum allowed time delta for synchronization.
        """
        self.mapper = SemanticMapper()
        self.time_sync_tolerance = time_sync_tolerance_ms / 1000.0
        self._last_timestamps: Dict[str, float] = {}
        logger.info(f"Adapter initialized with sync tolerance: {time_sync_tolerance_ms}ms")

    def _validate_payload(self, payload: RawDataPayload) -> bool:
        """
        Validates the integrity of the incoming data payload.
        
        Args:
            payload: The raw data object to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not payload.source_id:
            logger.error("Validation failed: Missing source_id")
            return False
        
        if payload.timestamp <= 0:
            logger.error(f"Validation failed: Invalid timestamp {payload.timestamp}")
            return False
            
        if not isinstance(payload.raw_value, (int, float, bool)):
            logger.warning(f"Validation warning: Non-numeric value type {type(payload.raw_value)} for {payload.source_id}")
            # Depending on strictness, could return False here. 
            # We allow it for status flags but log warning.
            
        return True

    def _check_temporal_consistency(self, source_id: str, current_time: float) -> bool:
        """
        Checks if the data arrival time is consistent with the synchronization window.
        Prevents out-of-order or delayed data from corrupting the AGI state.
        """
        last_time = self._last_timestamps.get(source_id)
        
        if last_time:
            # Ensure time moves forward (simulating real-time check)
            if current_time < last_time - self.time_sync_tolerance:
                logger.warning(f"Temporal anomaly detected for {source_id}. Data delayed.")
                return False
                
        self._last_timestamps[source_id] = current_time
        return True

    def _normalize_value(self, raw_val: Any, rule: Dict[str, Any]) -> float:
        """
        Normalizes raw values to a [0, 1] range based on mapping rules.
        Handles type conversion and boundary checks.
        """
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            # Handle boolean mapping
            if isinstance(raw_val, bool):
                return 1.0 if raw_val else 0.0
            return 0.0

        min_v = rule['min']
        max_v = rule['max']
        
        # Clamp values to boundaries to prevent AGI saturation
        clamped_val = max(min_v, min(val, max_v))
        
        # Normalize
        if max_v == min_v:
            return 0.0
            
        return (clamped_val - min_v) / (max_v - min_v)

    def map_to_state_node(self, payload: RawDataPayload) -> Optional[AGIStateNode]:
        """
        Maps a raw industrial payload to an AGI State Node.
        
        Args:
            payload: The raw data from the protocol layer.
            
        Returns:
            An AGIStateNode object if successful, None otherwise.
            
        Raises:
            ValueError: If mapping rule is not found.
        """
        # 1. Validation
        if not self._validate_payload(payload):
            return None

        # 2. Temporal Check
        current_time = time.time()
        # Using system time for sync check, or payload timestamp depending on architecture
        if not self._check_temporal_consistency(payload.source_id, payload.timestamp):
            return None

        # 3. Semantic Lookup
        rule = self.mapper.get_rule(payload.source_id)
        if not rule:
            logger.error(f"No semantic mapping rule found for {payload.source_id}")
            raise ValueError(f"Unknown source: {payload.source_id}")

        # 4. Normalization
        normalized = self._normalize_value(payload.raw_value, rule)

        # 5. State Node Construction
        node = AGIStateNode(
            node_id=f"agi_node_{payload.source_id}",
            semantic_type=rule['type'],
            timestamp=payload.timestamp,
            normalized_value=normalized,
            confidence_score=1.0,  # Base confidence, could be adjusted by data quality
            context_tags={
                "source_protocol": payload.protocol.value,
                "original_unit": rule['unit'],
                "edge_id": "edge_gateway_01"
            }
        )
        
        logger.debug(f"Mapped {payload.source_id} to {node.node_id} (Val: {normalized:.3f})")
        return node

# Example Usage
if __name__ == "__main__":
    # Initialize Adapter
    adapter = HeterogeneousProtocolAdapter(time_sync_tolerance_ms=500)
    
    # Configure Semantic Rules (Usually loaded from a config file)
    # Sensor 'PLC01_TEMP' is a Modbus register returning 0-100 (Celsius)
    adapter.mapper.add_rule(
        source_id="PLC01_TEMP", 
        semantic_type=SemanticType.TEMPERATURE, 
        range_min=0.0, 
        range_max=100.0, 
        unit="Celsius"
    )
    
    # Sensor 'VALVE_STAT' is an OPC UA boolean
    adapter.mapper.add_rule(
        source_id="VALVE_STAT", 
        semantic_type=SemanticType.BOOLEAN_STATUS, 
        range_min=0.0, 
        range_max=1.0, 
        unit="Boolean"
    )

    # Simulate Incoming Modbus Data
    raw_modbus = RawDataPayload(
        source_id="PLC01_TEMP",
        protocol=ProtocolType.MODBUS_TCP,
        timestamp=time.time(),
        raw_value=42.5,
        metadata={"register": 40001}
    )

    # Simulate Incoming OPC UA Data
    raw_opcua = RawDataPayload(
        source_id="VALVE_STAT",
        protocol=ProtocolType.OPC_UA,
        timestamp=time.time(),
        raw_value=True,
        metadata={"node_id": "ns=2;s=V01"}
    )

    # Process Data
    try:
        node_temp = adapter.map_to_state_node(raw_modbus)
        node_valve = adapter.map_to_state_node(raw_opcua)

        if node_temp:
            print(f"\nProcessed Node: {node_temp.node_id}")
            print(f"Type: {node_temp.semantic_type.value}")
            print(f"Normalized Value: {node_temp.normalized_value:.4f}")
            
        if node_valve:
            print(f"\nProcessed Node: {node_valve.node_id}")
            print(f"Value: {node_valve.normalized_value}")

    except Exception as e:
        logger.error(f"Processing failed: {e}")