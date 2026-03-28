"""
Module: dynamic_context_manager.py
Description: Implements a 'Memory Stream' mechanism for dynamic context window management.
             This system prioritizes historical code snippets, conversation logs, and documentation
             to maintain intent consistency in long-range AGI programming tasks.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import time
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryItemType(Enum):
    """Enumeration for different types of context items."""
    CONVERSATION = 1
    CODE_SNIPPET = 2
    DOCUMENTATION = 3
    INTENT_CORE = 4  # Highest priority, the core goal

@dataclass
class MemoryItem:
    """
    Represents a single unit of memory in the stream.
    
    Attributes:
        id: Unique identifier for the item.
        content: The actual text content (code or dialogue).
        type: The category of the memory item.
        timestamp: Creation time (simulated).
        importance: A static score (0.0 to 1.0) assigned at creation.
        access_count: Number of times this item has been retrieved.
    """
    id: str
    content: str
    type: MemoryItemType
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    access_count: int = 0

    def update_access(self):
        """Increment access count when retrieved."""
        self.access_count += 1

@dataclass
class ContextWindow:
    """
    Represents the limited working memory (Context Window).
    """
    max_tokens: int
    current_tokens: int = 0
    items: List[MemoryItem] = field(default_factory=list)

    def fit_check(self, item: MemoryItem, token_estimator: callable) -> bool:
        """Check if item fits without exceeding limits."""
        item_tokens = token_estimator(item.content)
        return (self.current_tokens + item_tokens) <= self.max_tokens

class DynamicContextManager:
    """
    Manages the 'Memory Stream' and selects the most relevant context 
    for the current step of a long-range programming task.
    """

    def __init__(self, max_context_tokens: int = 4096):
        """
        Initialize the manager.
        
        Args:
            max_context_tokens: The maximum token limit for the LLM context window.
        """
        if max_context_tokens <= 0:
            raise ValueError("Context window size must be positive.")
        
        self.long_term_memory: List[MemoryItem] = []
        self.context_window = ContextWindow(max_tokens=max_context_tokens)
        self.recency_decay_factor = 0.95
        logger.info(f"DynamicContextManager initialized with limit {max_context_tokens} tokens.")

    def add_memory(self, item: MemoryItem):
        """
        Add a new item to the long-term memory stream.
        
        Args:
            item: The MemoryItem to add.
        """
        if not isinstance(item, MemoryItem):
            raise TypeError("Only MemoryItem objects can be added.")
        
        self.long_term_memory.append(item)
        logger.debug(f"Added item {item.id} (Type: {item.type.name}) to memory stream.")

    def estimate_tokens(self, text: str) -> int:
        """
        Helper: Estimate token count (approximate: 1 token ~= 4 chars).
        
        Args:
            text: Input string.
            
        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return math.ceil(len(text) / 4.0)

    def calculate_relevance_score(self, item: MemoryItem) -> float:
        """
        Core Algorithm: Calculate the relevance of a memory item based on
        recency, importance, and frequency of access.
        
        Formula: Score = (Importance * w1) + (Recency * w2) + (Frequency * w3)
        
        Args:
            item: The memory item to score.
            
        Returns:
            A float score representing priority.
        """
        # 1. Recency: Exponential decay based on time
        time_diff = time.time() - item.timestamp
        recency_score = math.exp(-time_diff / 3600)  # Decay over hours
        
        # 2. Importance: Static weight based on type
        type_weights = {
            MemoryItemType.INTENT_CORE: 1.0,
            MemoryItemType.CODE_SNIPPET: 0.8,
            MemoryItemType.DOCUMENTATION: 0.6,
            MemoryItemType.CONVERSATION: 0.4
        }
        importance_score = type_weights.get(item.type, 0.5) * item.importance
        
        # 3. Frequency: Logarithmic scaling of access
        frequency_score = math.log1p(item.access_count)
        
        # Weighted Sum (Tunable hyperparameters)
        w1, w2, w3 = 0.5, 0.3, 0.2
        final_score = (importance_score * w1) + (recency_score * w2) + (frequency_score * w3)
        
        return final_score

    def build_working_context(self, current_query: str) -> List[Dict[str, Any]]:
        """
        Selects and loads the most relevant memories into the context window
        based on the current query and history.
        
        Args:
            current_query: The current user input or task description.
            
        Returns:
            A list of dictionaries representing the context payload.
        """
        logger.info("Rebuilding context window...")
        
        # 1. Score all items
        scored_items = []
        for item in self.long_term_memory:
            score = self.calculate_relevance_score(item)
            scored_items.append((score, item))
        
        # 2. Sort by score (descending)
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # 3. Fill the window (Knapsack-style greedy approach)
        self.context_window.items = []
        self.context_window.current_tokens = self.estimate_tokens(current_query)
        
        selected_context = []
        
        for score, item in scored_items:
            if self.context_window.fit_check(item, self.estimate_tokens):
                self.context_window.items.append(item)
                item_tokens = self.estimate_tokens(item.content)
                self.context_window.current_tokens += item_tokens
                item.update_access() # Mark as retrieved
                
                selected_context.append({
                    "role": "system" if item.type == MemoryItemType.INTENT_CORE else "assistant",
                    "content": item.content,
                    "metadata": {
                        "id": item.id,
                        "score": round(score, 4),
                        "type": item.type.name
                    }
                })
            else:
                # If window is full, we stop (simple strategy)
                # Advanced strategy could look for smaller items to fill gaps
                continue
        
        logger.info(f"Context built. Items: {len(selected_context)}, Tokens used: {self.context_window.current_tokens}")
        return selected_context

# Example Usage
if __name__ == "__main__":
    # 1. Initialize Manager (Simulating a 200 token limit for demo)
    manager = DynamicContextManager(max_context_tokens=200)
    
    # 2. Create sample memories
    intent = MemoryItem(
        id="intent_001",
        content="Primary Goal: Refactor the authentication module to use OAuth2.",
        type=MemoryItemType.INTENT_CORE,
        importance=1.0
    )
    
    old_code = MemoryItem(
        id="code_old",
        content="def login(user, pass): return db.query(user, pass)", 
        type=MemoryItemType.CODE_SNIPPET,
        importance=0.6,
        timestamp=time.time() - 7200 # 2 hours ago
    )
    
    recent_chat = MemoryItem(
        id="chat_new",
        content="User: Please also add logging to the new login function.",
        type=MemoryItemType.CONVERSATION,
        importance=0.8
    )
    
    # 3. Add to stream
    manager.add_memory(intent)
    manager.add_memory(old_code)
    manager.add_memory(recent_chat)
    
    # 4. Build Context for the next step
    current_task = "Implement the OAuth2 client class."
    context_payload = manager.build_working_context(current_task)
    
    print("\n=== Selected Context for AGI ===")
    for ctx in context_payload:
        print(f"[{ctx['metadata']['type']} | Score: {ctx['metadata']['score']}]: {ctx['content'][:30]}...")