"""
Module: auto_concept_extractor_36b542
Description: Real-time extraction and solidification of nodes from unstructured text streams.
             Implements an online pipeline to identify emerging concepts and filter noise.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ConceptExtractor")


@dataclass
class ConceptCandidate:
    """
    Represents a candidate concept extracted from the stream.

    Attributes:
        term (str): The extracted noun phrase or entity.
        context (str): The surrounding text context.
        timestamp (float): Extraction time (Unix epoch).
        retention_score (float): A dynamic score indicating the likelihood of being a valid concept.
        frequency (int): Number of times encountered.
    """

    term: str
    context: str
    timestamp: float = field(default_factory=time.time)
    retention_score: float = 0.0
    frequency: int = 1


class ConceptRetentionCalculator:
    """
    Calculates the probability of a concept being a valid, persistent node
    rather than temporary noise (slang/typos).
    """

    def __init__(self, half_life_seconds: int = 3600):
        self.half_life = half_life_seconds

    def calculate_score(
        self, current_score: float, frequency: int, time_delta: float
    ) -> float:
        """
        Updates the retention score based on recency and frequency.
        Uses a simplified exponential decay model.

        Args:
            current_score (float): The previous score.
            frequency (int): Total occurrences so far.
            time_delta (float): Time since last appearance.

        Returns:
            float: Updated retention score (0.0 to 1.0).
        """
        # Decay factor
        decay = 0.5 ** (time_delta / self.half_life)
        
        # Reinforcement factor (logarithmic growth to prevent explosion)
        boost = 1.0 + (0.1 * (frequency ** 0.5))
        
        new_score = (current_score * decay * boost)
        return min(max(new_score, 0.0), 1.0)


class OnlineNodeExtractor:
    """
    Main pipeline class for monitoring text streams and extracting nodes.
    """

    def __init__(
        self,
        existing_nodes_count: int = 1507,
        retention_threshold: float = 0.75,
        db_path: str = ":memory:",
    ):
        """
        Initialize the extractor.

        Args:
            existing_nodes_count (int): Simulated size of current knowledge graph.
            retention_threshold (float): Threshold to trigger node solidification.
            db_path (str): Path to SQLite DB for persistence.
        """
        self.existing_nodes = self._load_mock_nodes(existing_nodes_count)
        self.candidates: Dict[str, ConceptCandidate] = {}
        self.calculator = ConceptRetentionCalculator()
        self.retention_threshold = retention_threshold
        self.db_path = db_path
        self._init_db()
        logger.info(
            f"Pipeline initialized with {existing_nodes_count} existing nodes. Threshold: {retention_threshold}"
        )

    def _load_mock_nodes(self, count: int) -> Set[str]:
        """Simulates loading existing graph nodes."""
        # In a real scenario, load from Vector DB or Graph DB
        return {f"concept_{i}" for i in range(count)}

    def _init_db(self):
        """Initialize SQLite for persisting solidified nodes."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS solidified_nodes
                             (term TEXT PRIMARY KEY, retention_score REAL, solidified_at TEXT)"""
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _preprocess_text(self, text: str) -> List[str]:
        """
        Cleans and tokenizes text into candidate noun phrases.
        
        Args:
            text (str): Raw input text.
            
        Returns:
            List[str]: List of potential terms.
        """
        if not text or not isinstance(text, str):
            return []
        
        # Remove special characters, keep alphanumeric and spaces
        clean_text = re.sub(r"[^a-zA-Z0-9\s\-]", "", text.lower())
        # Simple noun phrase extraction (regex for 2-3 word phrases)
        # In production, use spaCy or NLTK
        pattern = r"\b[a-z]{3,}(?:\s+[a-z]{3,}){0,2}\b"
        matches = re.findall(pattern, clean_text)
        return matches

    def process_chunk(self, text_chunk: str, source_id: str = "default"):
        """
        Processes a chunk of text to update candidate scores or identify new nodes.

        Args:
            text_chunk (str): The incoming text data.
            source_id (str): Identifier for the data source (e.g., 'arxiv', 'news').
        """
        try:
            terms = self._preprocess_text(text_chunk)
            current_time = time.time()

            for term in terms:
                # 1. Filter against existing knowledge
                if term in self.existing_nodes:
                    continue

                # 2. Update or Create Candidate
                if term in self.candidates:
                    candidate = self.candidates[term]
                    time_delta = current_time - candidate.timestamp
                    
                    # Update score using the calculator
                    candidate.retention_score = self.calculator.calculate_score(
                        candidate.retention_score, candidate.frequency, time_delta
                    )
                    candidate.timestamp = current_time
                    candidate.frequency += 1
                    
                    logger.debug(
                        f"Updated '{term}': Score {candidate.retention_score:.4f}, Freq {candidate.frequency}"
                    )
                else:
                    self.candidates[term] = ConceptCandidate(
                        term=term, context=text_chunk[:50]
                    )
                    # Initial boost for first occurrence
                    self.candidates[term].retention_score = 0.1

                # 3. Check for Solidification
                if self.candidates[term].retention_score >= self.retention_threshold:
                    self._solidify_node(self.candidates[term])
                    # Remove from volatile candidates
                    del self.candidates[term]

        except Exception as e:
            logger.error(f"Error processing chunk from {source_id}: {e}", exc_info=True)

    def _solidify_node(self, candidate: ConceptCandidate):
        """
        Mounts the candidate as a permanent node in the system.
        
        Args:
            candidate (ConceptCandidate): The validated concept.
        """
        try:
            logger.info(
                f"🚀 SOLIDIFYING NODE: '{candidate.term}' (Score: {candidate.retention_score:.2f})"
            )
            
            # Add to existing set
            self.existing_nodes.add(candidate.term)
            
            # Persist to Database
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO solidified_nodes VALUES (?, ?, ?)",
                    (candidate.term, candidate.retention_score, datetime.utcnow().isoformat()),
                )
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Failed to solidify node '{candidate.term}' to DB: {e}")


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # Instantiate the pipeline
    pipeline = OnlineNodeExtractor(
        existing_nodes_count=1507, retention_threshold=0.6
    )

    # Simulate a stream of data (Mix of existing, noise, and emerging concepts)
    data_stream = [
        "The new transformer architecture improves latency.",  # Existing concept
        "Everyone is talking about quantum_entanglement_22.",  # Noise/Slang
        "Researchers discover 'gravitational_waves' patterns.",  # Emerging
        "Check out this cool slang_term_xyz!",  # Noise
        "Slang_term_xyz is stupid.",  # Noise fades
        "New paper on 'gravitational_waves' confirms theory.",  # Emerging reinforcement
        "Deep learning enables 'neuromorphic_computing'.",  # Emerging
    ]

    # Simulate time passing and processing
    print("\n--- Starting Stream Processing ---")
    for i, text in enumerate(data_stream):
        # Simulate time progression
        time.sleep(0.1) 
        print(f"\n[Input {i+1}]: {text}")
        pipeline.process_chunk(text, source_id="sim_stream")

    print("\n--- Final State ---")
    print(f"Total Nodes: {len(pipeline.existing_nodes)}")
    
    # Verify DB
    conn = sqlite3.connect(pipeline.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solidified_nodes")
    rows = cursor.fetchall()
    print(f"Solidified Nodes in DB: {rows}")
    conn.close()