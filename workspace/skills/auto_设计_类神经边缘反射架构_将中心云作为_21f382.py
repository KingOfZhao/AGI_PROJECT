"""
Module: auto_设计_类神经边缘反射架构_将中心云作为_21f382

Description:
    This module implements a 'Neuro-like Edge Reflex Architecture'.
    It simulates a system where the Central Cloud acts as the 'Brain' for complex
    training and global optimization, while Edge Nodes act as the 'Spinal Cord',
    capable of immediate reflex actions (e.g., shutting down circuits on overheating)
    without cloud latency.

    Key Features:
    - Central Cloud: Global Optimizer & Model Provider.
    - Edge Middleware: Executes 'Reflex Templates' (lite models) locally.
    - Reflex Action: Sub-millisecond response to specific patterns.
    - Pain Feedback: Escalates issues to the cloud if local handling fails.

Author: Advanced Python Engineer (AGI System)
Domain: Cross-Domain (IoT, Edge Computing, Distributed AI)
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# --- Configuration & Constants ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger("NeuroEdgeSystem")


class SystemState(Enum):
    """Enumeration for system status."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    PAIN_TRIGGERED = "PAIN_TRIGGERED"


@dataclass
class SensorData:
    """Represents input data from an edge sensor."""
    timestamp: float
    temperature: float  # Celsius
    pressure: float     # PSI
    error_rate: float   # 0.0 to 1.0

    def validate(self) -> bool:
        """Validates sensor data boundaries."""
        if not (0 <= self.error_rate <= 1):
            raise ValueError(f"Invalid error_rate: {self.error_rate}")
        if self.temperature < -273.15:
            raise ValueError(f"Invalid temperature: {self.temperature}")
        return True


@dataclass
class ReflexTemplate:
    """
    A 'Reflex Template' acts as a pre-programmed instinct.
    Downloaded from the 'Brain' (Cloud) to the 'Spinal Cord' (Edge).
    """
    rule_id: str
    trigger_condition: Callable[[SensorData], bool]
    action_code: str  # Code or instruction to execute
    version: float = 1.0


@dataclass
class PainSignal:
    """
    Data structure for the 'Pain Feedback' mechanism.
    Sent to the Cloud when the Edge cannot resolve an issue.
    """
    source_node: str
    severity: float
    context: SensorData
    failed_action: str


# --- Core Component: Central Cloud (The Brain) ---

class CentralCloudSystem:
    """
    The 'Brain'. Responsible for training, global optimization,
    and issuing reflex templates to edge nodes.
    """

    def __init__(self):
        self.global_knowledge_base: Dict[str, Any] = {}

    def generate_reflex_templates(self) -> List[ReflexTemplate]:
        """
        Simulates the training process where the cloud generates simplified models
        (reflexes) for edge deployment.
        """
        logger.info("[Brain] Generating global reflex templates...")
        
        # Rule 1: Temperature Reflex (Spinal Cord response to heat)
        def temp_trigger(data: SensorData) -> bool:
            return data.temperature > 85.0

        # Rule 2: Attack/Anomaly Reflex (High error rate)
        def attack_trigger(data: SensorData) -> bool:
            return data.error_rate > 0.8

        return [
            ReflexTemplate(
                rule_id="REFLEX_HEAT_001",
                trigger_condition=temp_trigger,
                action_code="EMERGENCY_SHUTDOWN_COOLING",
                version=2.1
            ),
            ReflexTemplate(
                rule_id="REFLEX_ATTACK_002",
                trigger_condition=attack_trigger,
                action_code="ISOLATE_NETWORK_PORT",
                version=1.5
            )
        ]

    def analyze_pain_signal(self, signal: PainSignal) -> str:
        """
        Receives 'Pain' signals from edge nodes for deep analysis.
        Returns a strategic decision.
        """
        logger.warning(f"[Brain] Received PAIN signal from {signal.source_node}. Analyzing context...")
        time.sleep(0.2)  # Simulate heavy processing latency
        
        if signal.severity > 0.9:
            decision = "GLOBAL_FAILOVER_INITIATED"
        else:
            decision = "RECONFIGURE_EDGE_PARAMS"
            
        logger.info(f"[Brain] Analysis complete. Decision: {decision}")
        return decision


# --- Core Component: Edge Middleware (The Spinal Cord) ---

class EdgeReflexMiddleware:
    """
    The 'Spinal Cord'. Deploys at the edge.
    Contains a Reflex Engine for immediate response and a Pain Mechanism
    for escalation.
    """

    def __init__(self, node_id: str, cloud_interface: CentralCloudSystem):
        self.node_id = node_id
        self.cloud_interface = cloud_interface
        self.reflex_memory: List[ReflexTemplate] = []
        self.state = SystemState.NORMAL
        self.latency_limit_ms = 5  # Max latency for reflexes

    def sync_templates(self) -> None:
        """Downloads the latest reflex models from the Cloud."""
        logger.info(f"[{self.node_id}] Syncing templates from Cloud...")
        self.reflex_memory = self.cloud_interface.generate_reflex_templates()
        logger.info(f"[{self.node_id}] Loaded {len(self.reflex_memory)} reflex templates.")

    def execute_local_reflex(self, data: SensorData) -> Tuple[bool, str]:
        """
        Core Reflex Loop. Checks data against local templates.
        Executes action if conditions are met, bypassing cloud latency.
        """
        start_time = time.perf_counter()
        
        for reflex in self.reflex_memory:
            if reflex.trigger_condition(data):
                self.state = SystemState.CRITICAL
                logger.critical(
                    f"[{self.node_id}] REFLEX TRIGGERED: {reflex.rule_id}. "
                    f"Action: {reflex.action_code}"
                )
                # Simulate hardware control action
                self._execute_hardware_action(reflex.action_code)
                
                # Check processing time
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if elapsed_ms > self.latency_limit_ms:
                    logger.warning(f"Reflex latency high: {elapsed_ms:.2f}ms")
                
                return True, reflex.action_code
        
        self.state = SystemState.NORMAL
        return False, "NO_ACTION"

    def _execute_hardware_action(self, action: str) -> None:
        """Helper to simulate hardware control."""
        logger.info(f"[{self.node_id}] >>> EXECUTING HARDWARE CMD: {action} <<<")

    def handle_pain_feedback(self, data: SensorData, failed_action: str) -> None:
        """
        Triggered when local reflex is insufficient or fails.
        Sends signal to Central Cloud.
        """
        self.state = SystemState.PAIN_TRIGGERED
        logger.error(f"[{self.node_id}] Local handling failed. Triggering PAIN FEEDBACK.")
        
        signal = PainSignal(
            source_node=self.node_id,
            severity=0.95,  # Example high severity
            context=data,
            failed_action=failed_action
        )
        
        # In a real async system, this would be a non-blocking call or queued
        decision = self.cloud_interface.analyze_pain_signal(signal)
        logger.info(f"[{self.node_id}] Cloud responded to pain with: {decision}")


# --- Helper Functions ---

def simulate_environment_data() -> SensorData:
    """Generates mock sensor data for testing."""
    return SensorData(
        timestamp=time.time(),
        temperature=random.uniform(20.0, 90.0),
        pressure=random.uniform(10.0, 50.0),
        error_rate=random.random()
    )


def run_architecture_demo():
    """
    Demonstrates the full flow: Cloud sync -> Edge processing -> Reflex/Pain.
    """
    logger.info("--- Initializing Neuro-Edge Architecture ---")
    
    # 1. Setup
    cloud = CentralCloudSystem()
    edge_node = EdgeReflexMiddleware("NODE_ALPHA_01", cloud)
    edge_node.sync_templates()
    
    # 2. Simulation Loop
    logger.info("\n--- Starting Simulation Loop ---")
    for cycle in range(1, 6):
        logger.info(f"\nCycle {cycle}...")
        data = simulate_environment_data()
        
        try:
            data.validate()
            logger.info(f"Input Data: Temp={data.temperature:.2f}C, ErrRate={data.error_rate:.2f}")
            
            # 3. Edge Processing (Reflex Check)
            handled, action = edge_node.execute_local_reflex(data)
            
            # 4. Pain Logic (Simulation: if temp > 95, even reflex might not be enough)
            if data.temperature > 95.0:
                edge_node.handle_pain_feedback(data, action)
            
            time.sleep(1)  # Cycle delay
            
        except ValueError as e:
            logger.error(f"Data Validation Error: {e}")
        except Exception as e:
            logger.exception("Unexpected system error")


# --- Main Execution ---

if __name__ == "__main__":
    run_architecture_demo()