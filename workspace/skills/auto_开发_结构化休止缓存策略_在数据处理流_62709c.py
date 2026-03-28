"""
Module: structured_rest_caching.py

Description:
    Implements a 'Structured Rest Caching Strategy' for AGI data processing pipelines.
    This system moves beyond simple data caching by explicitly caching 'Miss' or 'No Data'
    states with specific Time-To-Live (TTL) values. Much like a musical rest (休止符)
    anticipates the next melody, this strategy actively predicts when to retry or blocks
    redundant invalid requests within a time window, transforming system 'idling' into
    a rhythmic 'rest'.

    This prevents 'Cache Stampedes' on non-existent keys and reduces load on downstream
    services when they return empty results.

Key Features:
    - Structured caching of both Data and Anti-Data (Rest States).
    - Proactive retry scheduling based on Rest TTL.
    - Protection against repetitive invalid queries.

Author: AGI System Core Engineer
Version: 1.0.0
"""

import time
import hashlib
import logging
import json
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure Module Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StructuredRestCache")

class CacheState(Enum):
    """Enumeration of possible cache entry states."""
    DATA = "DATA"               # Valid data exists
    REST = "REST"               # Explicit 'No Data' / Failure state (The 'Rest')
    UNKNOWN = "UNKNOWN"         # Not in cache yet

@dataclass
class CacheEntry:
    """
    Represents a single entry in the cache structure.
    
    Attributes:
        state: Whether this entry holds Data or is a Rest (miss) marker.
        value: The data payload if state is DATA, else None.
        expires_at: Unix timestamp when this entry (or rest period) expires.
        metadata: Optional dictionary for debugging or audit trails.
    """
    state: CacheState
    value: Optional[Any]
    expires_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class StructuredRestCache:
    """
    A caching system that handles 'No Data' conditions as first-class citizens
    with their own expiration logic.
    """

    def __init__(self, default_data_ttl: int = 300, default_rest_ttl: int = 60):
        """
        Initialize the cache store.

        Args:
            default_data_ttl: Default seconds to keep valid data.
            default_rest_ttl: Default seconds to block/retry for missing data.
        """
        if not isinstance(default_data_ttl, int) or default_data_ttl <= 0:
            raise ValueError("default_data_ttl must be a positive integer")
        if not isinstance(default_rest_ttl, int) or default_rest_ttl <= 0:
            raise ValueError("default_rest_ttl must be a positive integer")

        self._store: Dict[str, CacheEntry] = {}
        self.default_data_ttl = default_data_ttl
        self.default_rest_ttl = default_rest_ttl
        logger.info(f"StructuredRestCache initialized (Data TTL: {default_data_ttl}s, Rest TTL: {default_rest_ttl}s)")

    def _generate_key(self, query_params: Dict[str, Any]) -> str:
        """
        Helper: Generates a deterministic hash key from query parameters.
        
        Args:
            query_params: Dictionary of input parameters.
            
        Returns:
            A SHA256 hex digest string.
        """
        # Sort keys to ensure dictionary order doesn't change the hash
        params_str = json.dumps(query_params, sort_keys=True)
        return hashlib.sha256(params_str.encode('utf-8')).hexdigest()

    def get(self, query_params: Dict[str, Any]) -> CacheEntry:
        """
        Core Function 1: Retrieve the state of a query from the cache.
        
        Checks if a key exists. If it exists as a 'Rest', checks if the rest period
        is over (signaling a retry is needed) or still active (signaling blocking).

        Args:
            query_params: The input query dictionary.

        Returns:
            CacheEntry: Contains state (DATA/REST/UNKNOWN) and value if applicable.
        """
        key = self._generate_key(query_params)
        current_time = time.time()
        
        entry = self._store.get(key)
        
        if entry is None:
            logger.debug(f"Key {key[:8]}... not found (State: UNKNOWN)")
            return CacheEntry(state=CacheState.UNKNOWN, value=None, expires_at=0)

        # Check Expiration
        if current_time > entry.expires_at:
            logger.info(f"Key {key[:8]}... expired (State was {entry.state}). Evicting.")
            del self._store[key]
            return CacheEntry(state=CacheState.UNKNOWN, value=None, expires_at=0)

        # Handle Rest State Logic
        if entry.state == CacheState.REST:
            # If we are here, the Rest is still active (not expired).
            # We return the REST state to tell the caller to wait/block.
            logger.info(f"Key {key[:8]}... is in REST state. Blocking request.")
            return entry
        
        # Handle Data State
        logger.info(f"Key {key[:8]}... HIT (Data).")
        return entry

    def set_data(self, query_params: Dict[str, Any], value: Any, ttl: Optional[int] = None) -> None:
        """
        Core Function 2: Store valid data in the cache.
        
        Args:
            query_params: The query parameters that generated this data.
            value: The data payload.
            ttl: Optional override for data TTL.
        """
        key = self._generate_key(query_params)
        _ttl = ttl if ttl is not None else self.default_data_ttl
        expires_at = time.time() + _ttl
        
        entry = CacheEntry(
            state=CacheState.DATA,
            value=value,
            expires_at=expires_at,
            metadata={"created_at": time.time()}
        )
        
        self._store[key] = entry
        logger.info(f"Key {key[:8]}... cached as DATA (TTL: {_ttl}s).")

    def set_rest(self, query_params: Dict[str, Any], ttl: Optional[int] = None, reason: str = "No Data") -> None:
        """
        Core Function 3: Store a 'Rest' state (Failure/Empty) in the cache.
        
        This prevents the system from hammering the downstream source for the
        duration of the Rest TTL.

        Args:
            query_params: The query parameters that resulted in failure/empty data.
            ttl: Optional override for rest TTL.
            reason: Description of why this is a rest (for logging).
        """
        key = self._generate_key(query_params)
        _ttl = ttl if ttl is not None else self.default_rest_ttl
        expires_at = time.time() + _ttl
        
        entry = CacheEntry(
            state=CacheState.REST,
            value=None,
            expires_at=expires_at,
            metadata={"reason": reason, "created_at": time.time()}
        )
        
        self._store[key] = entry
        logger.warning(f"Key {key[:8]}... cached as REST (Reason: '{reason}', TTL: {_ttl}s).")

    def process_request(self, query_params: Dict[str, Any], fetch_function: callable) -> Any:
        """
        Helper: Orchestrator function demonstrating the flow.
        
        This handles the logic of checking the cache, deciding whether to call
        the fetch function, and updating the cache based on results.

        Args:
            query_params: Input query.
            fetch_function: A callable that performs the actual expensive work.
        
        Returns:
            The data if found, or None if in a Rest state.
        
        Raises:
            ValueError: If fetch_function is not callable.
        """
        if not callable(fetch_function):
            raise ValueError("fetch_function must be callable")

        # 1. Check Cache State
        entry = self.get(query_params)

        if entry.state == CacheState.DATA:
            return entry.value
        
        if entry.state == CacheState.REST:
            # Logic: Since the entry exists and hasn't expired, we return None
            # (or raise a specific exception) to stop the flow.
            return None

        # 2. Cache Miss (UNKNOWN) -> Perform Expensive Operation
        logger.info(f"Cache Miss for query. Executing fetch function...")
        try:
            result = fetch_function(query_params)
            
            # 3. Analyze Result
            if result is None or result == [] or result == {}:
                # It returned nothing -> Cache as REST
                self.set_rest(query_params, reason="Empty Result")
                return None
            else:
                # It returned data -> Cache as DATA
                self.set_data(query_params, result)
                return result
                
        except Exception as e:
            logger.error(f"Fetch function failed: {e}")
            # Cache the error as a Rest to prevent retry storms
            self.set_rest(query_params, reason=f"Exception: {str(e)}")
            # Re-raise or return None depending on policy. Here we return None for safety.
            return None

# Example Usage (Commented out for module context, but kept for completeness)
# if __name__ == "__main__":
#     cache = StructuredRestCache(default_rest_ttl=10)
#     
#     def mock_db_fetch(query):
#         print("...Querying Database...")
#         if query.get("id") == 1:
#             return {"data": "valid"}
#         return None
# 
#     # First run: Miss, fetches, gets None, caches Rest
#     print("Run 1:", cache.process_request({"id": 99}, mock_db_fetch))
#     
#     # Second run: Hits Rest Cache, returns None immediately (No DB query)
#     print("Run 2:", cache.process_request({"id": 99}, mock_db_fetch))
#     
#     # Wait for Rest TTL to expire...
#     time.sleep(11)
#     
#     # Third run: Rest expired, retries query.
#     print("Run 3:", cache.process_request({"id": 99}, mock_db_fetch))