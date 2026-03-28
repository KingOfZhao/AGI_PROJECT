"""
Module: generational_memory_system.py

This module implements a hierarchical storage mechanism simulating human civilization's
inheritance to address the limitations of lifespan-induced narrowness in AGI systems.
It manages 'Generational Forgetting' (short-term, high-frequency changes) and
'Core Memory' (long-term, immutable underlying logic) via a tiered storage architecture.

Design Philosophy:
1. Short-Term Memory (Ephemeral): High entropy, frequent updates (e.g., daily prices).
   Automatically decays if not reinforced.
2. Core Memory (Genetic/Immutable): Low entropy, structural logic (e.g., laws of physics/supply-demand).
   Persists across sessions and creates checkpoints.

Author: Senior Python Engineer (AGI Systems)
Date: 2023-10
"""

import logging
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("memory_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemoryTier(Enum):
    """Defines the hierarchy levels of memory."""
    EPHEMERAL = 0  # Short-term, high volatility
    STABLE = 1     # Mid-term, consolidated
    GENETIC = 2    # Core, immutable logic

@dataclass
class MemoryNode:
    """
    Represents a single unit of memory.
    
    Attributes:
        key: Unique identifier for the memory.
        content: The data payload (JSON serializable).
        created_at: Timestamp of creation.
        last_accessed: Timestamp of last retrieval.
        importance: A score (0.0-1.0) determining survival chances.
        tier: Current storage tier.
    """
    key: str
    content: Any
    created_at: str
    last_accessed: str
    importance: float
    tier: MemoryTier

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "content": self.content,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "importance": self.importance,
            "tier": self.tier.name
        }

class GenerationalMemorySystem:
    """
    A hierarchical database architecture mimicking cultural and biological inheritance.
    
    Handles the lifecycle of data from volatile observation to crystallized logic.
    """

    def __init__(self, decay_threshold_hours: int = 24, core_storage_path: str = "core_memory_store.json"):
        """
        Initialize the memory system.
        
        Args:
            decay_threshold_hours: Time before unchecked ephemeral data decays.
            core_storage_path: File path for persistent genetic memory.
        """
        self._decay_threshold = timedelta(hours=decay_threshold_hours)
        self._core_storage_path = core_storage_path
        
        # In-memory storage buffers
        self._ephemeral_buffer: Dict[str, MemoryNode] = {}  # Short-term
        self._genetic_core: Dict[str, MemoryNode] = {}      # Long-term
        
        logger.info("Initializing Generational Memory System...")
        self._load_genetic_core()

    def _load_genetic_core(self) -> None:
        """Loads persistent genetic memory from disk."""
        if os.path.exists(self._core_storage_path):
            try:
                with open(self._core_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, val in data.items():
                        val['tier'] = MemoryTier.GENETIC # Ensure tier is correct
                        self._genetic_core[key] = MemoryNode(**val)
                logger.info(f"Loaded {len(self._genetic_core)} genetic core memories.")
            except Exception as e:
                logger.error(f"Failed to load genetic core: {e}")
        else:
            logger.info("No existing genetic core found. Starting fresh.")

    def _save_genetic_core(self) -> None:
        """Persists genetic memory to disk."""
        try:
            data = {k: v.to_dict() for k, v in self._genetic_core.items()}
            with open(self._core_storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info("Genetic core persisted to disk.")
        except Exception as e:
            logger.error(f"Failed to save genetic core: {e}")

    def _validate_content(self, content: Any) -> bool:
        """
        Helper: Validates input data.
        Ensures content is not empty and is JSON serializable.
        """
        if content is None:
            return False
        try:
            json.dumps(content)
            return True
        except TypeError:
            logger.warning("Content validation failed: Not JSON serializable.")
            return False

    def _generate_key(self, content: Any) -> str:
        """
        Helper: Generates a unique deterministic key for logic nodes,
        or a random key for transient events.
        """
        # For logic/core data, we want deterministic keys to prevent duplication
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def observe(self, data_point: Dict[str, Any], is_logic: bool = False) -> str:
        """
        Input new data into the system.
        
        Args:
            data_point: The data to store.
            is_logic: If True, treats data as structural logic (Candidate for Core).
                      If False, treats as transient detail (Ephemeral).
        
        Returns:
            The memory key.
        """
        if not self._validate_content(data_point):
            raise ValueError("Invalid data format: Content must be JSON serializable.")

        now = datetime.utcnow().isoformat()
        key = self._generate_key(data_point)
        
        # Determine Tier
        tier = MemoryTier.GENETIC if is_logic else MemoryTier.EPHEMERAL
        importance = 1.0 if is_logic else 0.1
        
        node = MemoryNode(
            key=key,
            content=data_point,
            created_at=now,
            last_accessed=now,
            importance=importance,
            tier=tier
        )

        if is_logic:
            if key not in self._genetic_core:
                self._genetic_core[key] = node
                self._save_genetic_core()
                logger.info(f"New CORE MEMORY encoded: {key}")
            else:
                logger.info(f"CORE MEMORY already exists: {key}")
        else:
            self._ephemeral_buffer[key] = node
            logger.debug(f"Ephemeral observation stored: {key}")
            
        return key

    def recall(self, query_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve memory. Updates 'last_accessed' to prevent decay for ephemeral data.
        """
        # Check Core first (High Priority)
        if query_key in self._genetic_core:
            node = self._genetic_core[query_key]
            logger.info(f"Recalled from GENETIC CORE: {query_key}")
            return node.content
            
        # Check Ephemeral buffer
        if query_key in self._ephemeral_buffer:
            node = self._ephemeral_buffer[query_key]
            node.last_accessed = datetime.utcnow().isoformat()
            # Boost importance if accessed
            node.importance = min(1.0, node.importance + 0.2)
            logger.info(f"Recalled from EPHEMERAL BUFFER: {query_key}")
            return node.content
            
        logger.warning(f"Memory not found: {query_key}")
        return None

    def run_decay_cycle(self) -> int:
        """
        Executes the 'Forgetting' process.
        Removes ephemeral data that hasn't been accessed recently or has low importance.
        
        Returns:
            Number of forgotten items.
        """
        now = datetime.utcnow()
        keys_to_forget = []
        
        logger.info("Starting memory decay cycle...")
        
        for key, node in self._ephemeral_buffer.items():
            last_access = datetime.fromisoformat(node.last_accessed)
            age = now - last_access
            
            # Logic: Forget if older than threshold AND importance is low
            if age > self._decay_threshold and node.importance < 0.5:
                keys_to_forget.append(key)
                
        for key in keys_to_forget:
            del self._ephemeral_buffer[key]
            
        if keys_to_forget:
            logger.info(f"Generation遗忘
        return len(keys_to_forget)

    def consolidate_memories(self) -> None:
        """
        Promotes high-importance ephemeral memories to stable/core memory if necessary.
        (Simplified implementation of sleep-cycle consolidation).
        """
        logger.info("Analyzing buffer for consolidation...")
        for key, node in list(self._ephemeral_buffer.items()):
            if node.importance >= 0.8:
                logger.info(f"Consolidating high-value memory to core: {key}")
                node.tier = MemoryTier.GENETIC
                self._genetic_core[key] = node
                del self._ephemeral_buffer[key]
        
        self._save_genetic_core()

# --- Usage Example ---
if __name__ == "__main__":
    # Initialize System
    agi_memory = GenerationalMemorySystem(decay_threshold_hours=1)
    
    print("\n--- Phase 1: Observation ---")
    
    # 1. Observe transient details (Today's vegetable price)
    ephemeral_data = {"type": "market_price", "item": "cabbage", "price": 3.5, "date": "2023-10-27"}
    key_ephemeral = agi_memory.observe(ephemeral_data, is_logic=False)
    
    # 2. Observe core logic (Supply and Demand Principle)
    core_logic = {"principle": "supply_demand", "law": "Price increases when supply < demand", "immutable": True}
    key_core = agi_memory.observe(core_logic, is_logic=True)
    
    print(f"Stored Ephemeral Key: {key_ephemeral}")
    print(f"Stored Core Key: {key_core}")
    
    print("\n--- Phase 2: Recall & Decay ---")
    
    # Recall logic
    retrieved_logic = agi_memory.recall(key_core)
    print(f"Retrieved Logic: {retrieved_logic}")
    
    # Simulate time passing and run decay (In real scenario, this happens periodically)
    forgotten_count = agi_memory.run_decay_cycle()
    print(f"Items forgotten in this cycle: {forgotten_count}")
    
    # Verify ephemeral data is gone (assuming it wasn't accessed enough to boost importance)
    # Note: In this simple run, it might survive if the threshold isn't met,
    # but the logic demonstrates the mechanism.
    retrieved_price = agi_memory.recall(key_ephemeral)
    print(f"Retrieved Price (after potential decay): {retrieved_price}")