"""
Industrial Long-Term Memory System for AGI

This module implements a specialized storage architecture designed to address the 
limitations of human lifespan in industrial settings. It enables AGI systems to 
maintain "long-cycle memory" across decades of industrial equipment lifecycle, 
preserving sparse but critical expert knowledge about rare equipment failures and 
specialized solutions that occurred many years ago.

Key Features:
- Anti-forgetting mechanism for long-tail industrial data
- Sparse node preservation for rare but critical maintenance scenarios
- Temporal decay-resistant storage for legacy equipment knowledge
- Expert knowledge emulation for 20+ year old equipment troubleshooting
"""

import logging
import sqlite3
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialLongTermMemory")

# Constants
MEMORY_DB_PATH = "industrial_memory.db"
FORGETTING_THRESHOLD = 0.2  # Minimum importance score to retain memory
DECAY_RATE = 0.01  # Memory decay rate per year
REINFORCEMENT_FACTOR = 1.5  # Importance increase when memory is accessed

@dataclass
class EquipmentMemory:
    """Represents a single memory entry for industrial equipment."""
    memory_id: str
    equipment_id: str
    timestamp: float  # Unix timestamp when memory was created
    description: str
    solution: str
    importance_score: float  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: float = 0.0
    tags: List[str] = None
    is_rare_case: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

class IndustrialLongTermMemory:
    """
    A specialized memory system that preserves critical industrial knowledge over 
    extended time periods, emulating how experienced engineers recall rare but 
    important equipment issues from decades ago.
    """
    
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        """Initialize the industrial long-term memory system."""
        self.db_path = db_path
        self._initialize_database()
        self.memory_graph = defaultdict(list)  # Equipment ID to memory IDs mapping
        self.temporal_index = {}  # Time-based index for quick access
        self._load_memory_graph()
        
    def _initialize_database(self) -> None:
        """Create necessary database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment_memories (
                    memory_id TEXT PRIMARY KEY,
                    equipment_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    description TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    importance_score REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    tags TEXT,  # Stored as JSON array
                    is_rare_case INTEGER DEFAULT 0,
                    metadata TEXT,  # Stored as JSON object
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
                """)
                
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_reinforcements (
                    memory_id TEXT NOT NULL,
                    reinforcement_factor REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES equipment_memories(memory_id)
                )
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_equipment_id ON equipment_memories(equipment_id)
                """)
                
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON equipment_memories(timestamp)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise RuntimeError(f"Failed to initialize memory database: {str(e)}")
    
    def _load_memory_graph(self) -> None:
        """Load existing memory graph from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT equipment_id, memory_id FROM equipment_memories")
                for equip_id, mem_id in cursor.fetchall():
                    self.memory_graph[equip_id].append(mem_id)
                    
                logger.info(f"Loaded memory graph with {sum(len(v) for v in self.memory_graph.values())} nodes")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to load memory graph: {str(e)}")
    
    def store_memory(
        self,
        equipment_id: str,
        description: str,
        solution: str,
        importance_score: float = 0.5,
        is_rare_case: bool = False,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Store a new memory for industrial equipment.
        
        Args:
            equipment_id: Unique identifier for the equipment
            description: Description of the equipment issue
            solution: The solution applied to fix the issue
            importance_score: Initial importance score (0.0 to 1.0)
            is_rare_case: Whether this is a rare/special case
            tags: List of tags for categorization
            metadata: Additional metadata about the memory
            
        Returns:
            The generated memory ID
            
        Raises:
            ValueError: If input validation fails
        """
        # Input validation
        if not equipment_id or not description or not solution:
            raise ValueError("Equipment ID, description, and solution are required")
            
        if not 0 <= importance_score <= 1:
            raise ValueError("Importance score must be between 0 and 1")
            
        if tags is None:
            tags = []
            
        if metadata is None:
            metadata = {}
            
        # Generate memory ID
        memory_id = self._generate_memory_id(equipment_id, description, solution)
        
        # Create memory object
        memory = EquipmentMemory(
            memory_id=memory_id,
            equipment_id=equipment_id,
            timestamp=time.time(),
            description=description,
            solution=solution,
            importance_score=importance_score,
            is_rare_case=is_rare_case,
            tags=tags,
            metadata=metadata
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if memory already exists
                cursor.execute("SELECT 1 FROM equipment_memories WHERE memory_id = ?", (memory_id,))
                if cursor.fetchone():
                    logger.warning(f"Memory {memory_id} already exists, updating instead")
                    return self._update_memory(memory)
                
                # Insert new memory
                cursor.execute("""
                INSERT INTO equipment_memories (
                    memory_id, equipment_id, timestamp, description, solution,
                    importance_score, access_count, last_accessed, tags,
                    is_rare_case, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id,
                    memory.equipment_id,
                    memory.timestamp,
                    memory.description,
                    memory.solution,
                    memory.importance_score,
                    memory.access_count,
                    memory.last_accessed,
                    json.dumps(memory.tags),
                    int(memory.is_rare_case),
                    json.dumps(memory.metadata)
                ))
                
                conn.commit()
                
                # Update memory graph
                self.memory_graph[equipment_id].append(memory_id)
                
                logger.info(f"Stored new memory {memory_id} for equipment {equipment_id}")
                return memory_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to store memory: {str(e)}")
            raise RuntimeError(f"Memory storage failed: {str(e)}")
    
    def retrieve_memory(
        self,
        equipment_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_importance: float = 0.0,
        include_rare_cases: bool = True,
        tags: List[str] = None
    ) -> List[EquipmentMemory]:
        """
        Retrieve memories for a specific piece of equipment with filtering options.
        
        Args:
            equipment_id: Equipment ID to retrieve memories for
            time_range: Optional time range (start, end) to filter memories
            min_importance: Minimum importance score to include
            include_rare_cases: Whether to include rare cases regardless of importance
            tags: List of tags to filter by (any tag matches)
            
        Returns:
            List of EquipmentMemory objects matching the criteria
        """
        if not equipment_id:
            raise ValueError("Equipment ID is required")
            
        if equipment_id not in self.memory_graph:
            logger.info(f"No memories found for equipment {equipment_id}")
            return []
            
        memories = []
        memory_ids = self.memory_graph[equipment_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                for mem_id in memory_ids:
                    cursor.execute("SELECT * FROM equipment_memories WHERE memory_id = ?", (mem_id,))
                    row = cursor.fetchone()
                    
                    if not row:
                        continue
                        
                    # Apply filters
                    if min_importance > 0 and row['importance_score'] < min_importance:
                        if not (include_rare_cases and row['is_rare_case']):
                            continue
                            
                    if time_range:
                        start, end = time_range
                        mem_time = datetime.fromtimestamp(row['timestamp'])
                        if not (start <= mem_time <= end):
                            continue
                            
                    if tags and not any(tag in json.loads(row['tags']) for tag in tags):
                        continue
                        
                    # Convert to EquipmentMemory object
                    memory = EquipmentMemory(
                        memory_id=row['memory_id'],
                        equipment_id=row['equipment_id'],
                        timestamp=row['timestamp'],
                        description=row['description'],
                        solution=row['solution'],
                        importance_score=row['importance_score'],
                        access_count=row['access_count'],
                        last_accessed=row['last_accessed'],
                        tags=json.loads(row['tags']),
                        is_rare_case=bool(row['is_rare_case']),
                        metadata=json.loads(row['metadata'])
                    )
                    
                    memories.append(memory)
                    
                    # Update access statistics
                    self._record_memory_access(memory.memory_id)
                    
                logger.info(f"Retrieved {len(memories)} memories for equipment {equipment_id}")
                return memories
                
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve memories: {str(e)}")
            raise RuntimeError(f"Memory retrieval failed: {str(e)}")
    
    def _record_memory_access(self, memory_id: str) -> None:
        """Record that a memory was accessed and reinforce its importance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update access statistics
                cursor.execute("""
                UPDATE equipment_memories 
                SET access_count = access_count + 1,
                    last_accessed = ?,
                    importance_score = MIN(1.0, importance_score * ?)
                WHERE memory_id = ?
                """, (time.time(), REINFORCEMENT_FACTOR, memory_id))
                
                # Record reinforcement
                cursor.execute("""
                INSERT INTO memory_reinforcements (memory_id, reinforcement_factor, timestamp)
                VALUES (?, ?, ?)
                """, (memory_id, REINFORCEMENT_FACTOR, time.time()))
                
                conn.commit()
                
        except sqlite3.Error as e:
            logger.warning(f"Failed to record memory access: {str(e)}")
    
    def _update_memory(self, memory: EquipmentMemory) -> str:
        """Update an existing memory in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                UPDATE equipment_memories 
                SET 
                    description = ?,
                    solution = ?,
                    importance_score = ?,
                    tags = ?,
                    is_rare_case = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE memory_id = ?
                """, (
                    memory.description,
                    memory.solution,
                    memory.importance_score,
                    json.dumps(memory.tags),
                    int(memory.is_rare_case),
                    json.dumps(memory.metadata),
                    time.time(),
                    memory.memory_id
                ))
                
                conn.commit()
                logger.info(f"Updated memory {memory.memory_id}")
                return memory.memory_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update memory: {str(e)}")
            raise RuntimeError(f"Memory update failed: {str(e)}")
    
    def apply_forgetting_mechanism(self, force: bool = False) -> int:
        """
        Apply the forgetting mechanism to remove low-importance memories that 
        haven't been accessed recently.
        
        Args:
            force: If True, apply even if recently applied
            
        Returns:
            Number of memories removed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all memories that might be candidates for forgetting
                cursor.execute("""
                SELECT memory_id, importance_score, timestamp, last_accessed, is_rare_case
                FROM equipment_memories
                WHERE importance_score < ? AND is_rare_case = 0
                """, (FORGETTING_THRESHOLD,))
                
                candidates = cursor.fetchall()
                removed_count = 0
                
                for mem_id, importance, timestamp, last_accessed, _ in candidates:
                    # Calculate time-based decay
                    current_time = time.time()
                    age_years = (current_time - timestamp) / (365 * 24 * 3600)
                    
                    # Adjust importance based on age and access frequency
                    if last_accessed:
                        time_since_access = (current_time - last_accessed) / (365 * 24 * 3600)
                        decayed_importance = importance * np.exp(-DECAY_RATE * time_since_access)
                    else:
                        decayed_importance = importance * np.exp(-DECAY_RATE * age_years)
                    
                    # Remove if below threshold after decay
                    if decayed_importance < FORGETTING_THRESHOLD:
                        cursor.execute("DELETE FROM equipment_memories WHERE memory_id = ?", (mem_id,))
                        cursor.execute("DELETE FROM memory_reinforcements WHERE memory_id = ?", (mem_id,))
                        removed_count += 1
                        
                        # Update memory graph
                        for equip_id, mem_list in self.memory_graph.items():
                            if mem_id in mem_list:
                                mem_list.remove(mem_id)
                                break
                
                conn.commit()
                logger.info(f"Forgetting mechanism removed {removed_count} memories")
                return removed_count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to apply forgetting mechanism: {str(e)}")
            raise RuntimeError(f"Forgetting mechanism failed: {str(e)}")
    
    def find_similar_issues(
        self,
        description: str,
        equipment_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Tuple[EquipmentMemory, float]]:
        """
        Find similar issues based on description using a simple text similarity approach.
        
        Args:
            description: Description of the current issue
            equipment_id: Optional equipment ID to filter results
            limit: Maximum number of results to return
            
        Returns:
            List of tuples containing (memory, similarity_score)
        """
        # Simple Jaccard similarity for demonstration
        # In a real system, this would use more sophisticated NLP techniques
        
        def preprocess(text: str) -> set:
            """Simple text preprocessing."""
            return set(text.lower().split())
            
        query_words = preprocess(description)
        if not query_words:
            return []
            
        similar_memories = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if equipment_id:
                    cursor.execute("SELECT * FROM equipment_memories WHERE equipment_id = ?", (equipment_id,))
                else:
                    cursor.execute("SELECT * FROM equipment_memories")
                    
                for row in cursor:
                    memory_words = preprocess(row['description'])
                    intersection = len(query_words & memory_words)
                    union = len(query_words | memory_words)
                    similarity = intersection / union if union > 0 else 0.0
                    
                    if similarity > 0.1:  # Threshold for relevance
                        memory = EquipmentMemory(
                            memory_id=row['memory_id'],
                            equipment_id=row['equipment_id'],
                            timestamp=row['timestamp'],
                            description=row['description'],
                            solution=row['solution'],
                            importance_score=row['importance_score'],
                            access_count=row['access_count'],
                            last_accessed=row['last_accessed'],
                            tags=json.loads(row['tags']),
                            is_rare_case=bool(row['is_rare_case']),
                            metadata=json.loads(row['metadata'])
                        )
                        similar_memories.append((memory, similarity))
                        
                # Sort by similarity and importance
                similar_memories.sort(key=lambda x: (-x[1], -x[0].importance_score))
                return similar_memories[:limit]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to find similar issues: {str(e)}")
            return []
    
    def _generate_memory_id(self, equipment_id: str, description: str, solution: str) -> str:
        """Generate a unique memory ID based on content."""
        hash_input = f"{equipment_id}|{description}|{solution}".encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get basic counts
                cursor.execute("SELECT COUNT(*) FROM equipment_memories")
                total_memories = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT equipment_id) FROM equipment_memories")
                unique_equipment = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM equipment_memories WHERE is_rare_case = 1")
                rare_cases = cursor.fetchone()[0]
                
                # Get age distribution
                cursor.execute("""
                SELECT 
                    MIN(timestamp) as oldest,
                    MAX(timestamp) as newest,
                    AVG(importance_score) as avg_importance
                FROM equipment_memories
                """)
                stats = cursor.fetchone()
                
                return {
                    "total_memories": total_memories,
                    "unique_equipment": unique_equipment,
                    "rare_cases": rare_cases,
                    "oldest_memory": datetime.fromtimestamp(stats[0]).isoformat() if stats[0] else None,
                    "newest_memory": datetime.fromtimestamp(stats[1]).isoformat() if stats[1] else None,
                    "average_importance": stats[2] if stats[2] is not None else 0.0
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {}

# Example usage
if __name__ == "__main__":
    try:
        # Initialize the memory system
        memory_system = IndustrialLongTermMemory()
        
        # Store a memory about a 20-year-old equipment issue
        memory_id = memory_system.store_memory(
            equipment_id="pump_1998_A",
            description="Excessive vibration in centrifugal pump causing bearing failure",
            solution="Replaced worn impeller and balanced rotor assembly",
            importance_score=0.7,
            is_rare_case=True,
            tags=["pump", "vibration", "bearing", "rare"],
            metadata={
                "equipment_age": "20 years",
                "manufacturer": "GenericPumps Inc.",
                "replacement_parts": ["impeller", "bearings"]
            }
        )
        print(f"Stored memory with ID: {memory_id}")
        
        # Retrieve memories for the equipment
        memories = memory_system.retrieve_memory(
            equipment_id="pump_1998_A",
            min_importance=0.5
        )
        print(f"Found {len(memories)} relevant memories")
        for mem in memories:
            print(f"- {mem.description} (importance: {mem.importance_score})")
        
        # Find similar issues
        similar = memory_system.find_similar_issues(
            description="centrifugal pump making unusual noise",
            limit=3
        )
        print(f"Found {len(similar)} similar issues")
        for mem, score in similar:
            print(f"- Similarity: {score:.2f} | {mem.description}")
        
        # Apply forgetting mechanism
        removed = memory_system.apply_forgetting_mechanism()
        print(f"Removed {removed} low-importance memories")
        
        # Get system statistics
        stats = memory_system.get_memory_statistics()
        print("Memory system statistics:")
        for k, v in stats.items():
            print(f"- {k}: {v}")
            
    except Exception as e:
        print(f"Error in example usage: {str(e)}")