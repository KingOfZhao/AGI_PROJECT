"""
Module: context_firewall.py
Author: Senior Python Engineer
Description: Implements a Context Firewall for AGI systems to ensure safe cross-domain knowledge transfer.
             It isolates source domain noise and fuses valid abstract concepts into the target domain.
"""

import logging
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class ContextEntity(BaseModel):
    """Represents a single entity within a specific domain context."""
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    domain_specific_score: float = Field(
        ..., ge=0.0, le=1.0, 
        description="Score indicating how specific the entity is to the source domain (1.0 = highly specific noise)."
    )

class DomainPacket(BaseModel):
    """Represents a packet of information transferring between domains."""
    source_domain: str
    target_domain: str
    raw_entities: List[ContextEntity]

# --- Core Functions ---

def analyze_entity_specificity(
    entity: ContextEntity, 
    noise_keywords: Set[str]
) -> Tuple[ContextEntity, float]:
    """
    Analyzes an entity to determine its specificity to the source domain.
    
    Args:
        entity: The context entity to analyze.
        noise_keywords: A set of keywords that define 'noise' for the target domain.
        
    Returns:
        A tuple containing the original entity and a calculated noise impact score.
        
    Raises:
        ValueError: If entity content is empty.
    """
    if not entity.content:
        logger.error(f"Entity {entity.id} has empty content.")
        raise ValueError("Entity content cannot be empty.")

    # Calculate overlap with noise keywords
    words = set(re.findall(r'\w+', entity.content.lower()))
    overlap = words.intersection(noise_keywords)
    
    # Calculate dynamic noise score based on keyword density + inherent metadata score
    # Formula: (Overlap Count / Total Words) * 0.6 + Metadata Score * 0.4
    word_count = len(words)
    density_score = len(overlap) / word_count if word_count > 0 else 0.0
    
    final_noise_score = (density_score * 0.6) + (entity.domain_specific_score * 0.4)
    
    logger.debug(f"Entity {entity.id} analyzed. Noise Score: {final_noise_score:.2f}")
    return entity, final_noise_score

def context_isolation_engine(
    packet: DomainPacket, 
    noise_threshold: float = 0.35,
    custom_noise_lexicon: Optional[Set[str]] = None
) -> List[ContextEntity]:
    """
    The 'Context Firewall' core logic. Filters out high-specificity noise entities.
    
    Args:
        packet: The data packet containing raw entities from source domain.
        noise_threshold: The cutoff score. Entities above this are discarded.
        custom_noise_lexicon: Specific terms to filter (e.g., 'cavalry', 'scroll').
        
    Returns:
        A list of sanitized entities ready for fusion.
        
    Example:
        >>> entities = [ContextEntity(id="1", content="Deploy cavalry", domain_specific_score=0.9)]
        >>> packet = DomainPacket(source_domain="ancient_war", target_domain="modern_biz", raw_entities=entities)
        >>> clean = context_isolation_engine(packet, noise_threshold=0.5, custom_noise_lexicon={"cavalry"})
        >>> print(len(clean))
        0
    """
    logger.info(f"Initializing Firewall: {packet.source_domain} -> {packet.target_domain}")
    
    # Default lexicon if none provided
    noise_lexicon = custom_noise_lexicon or set()
    
    clean_entities = []
    
    for entity in packet.raw_entities:
        try:
            _, score = analyze_entity_specificity(entity, noise_lexicon)
            
            if score < noise_threshold:
                # Sanitize content by masking noise words
                sanitized_content = _sanitize_content(entity.content, noise_lexicon)
                entity.content = sanitized_content
                clean_entities.append(entity)
                logger.info(f"PASS: Entity {entity.id} admitted (Score: {score:.2f})")
            else:
                logger.warning(f"BLOCK: Entity {entity.id} quarantined (Score: {score:.2f} > {noise_threshold})")
                
        except ValueError as ve:
            logger.error(f"Skipping invalid entity: {ve}")
            continue
        except Exception as e:
            logger.critical(f"Unexpected error processing entity {entity.id}: {e}")
            continue
            
    return clean_entities

# --- Auxiliary Functions ---

def _sanitize_content(content: str, noise_words: Set[str]) -> str:
    """
    Replaces specific noise words in the text with generic placeholders 
    to preserve structure while removing specific semantics.
    
    Args:
        content: The raw text string.
        noise_words: Words to be redacted.
        
    Returns:
        Sanitized string.
    """
    def replace_match(match):
        word = match.group(0)
        if word.lower() in noise_words:
            return f"<GENERALIZED_{word.upper()}>"
        return word

    # Use regex to match whole words only
    pattern = r'\b(' + '|'.join(re.escape(w) for w in noise_words) + r')\b'
    return re.sub(pattern, replace_match, content, flags=re.IGNORECASE)

# --- Execution / Example Usage ---

def run_simulation():
    """
    Demonstrates the transfer of Ancient Military Strategy to Modern Management.
    """
    print("--- Starting Context Firewall Simulation ---")
    
    # 1. Define Data
    raw_data = [
        ContextEntity(
            id="strat_001", 
            content="Utilize light cavalry to flank the enemy phalanx.", 
            domain_specific_score=0.8, 
            metadata={"era": "ancient"}
        ),
        ContextEntity(
            id="strat_002", 
            content="Maintain a strong supply chain to ensure troop endurance.", 
            domain_specific_score=0.1, 
            metadata={"era": "universal"}
        ),
        ContextEntity(
            id="strat_003", 
            content="Send scouts to gather intelligence on enemy movements.", 
            domain_specific_score=0.4, 
            metadata={"era": "semi-modern"}
        ),
        ContextEntity(
            id="strat_004", 
            content="", # Invalid data test
            domain_specific_score=0.0
        )
    ]
    
    packet = DomainPacket(
        source_domain="ancient_warfare",
        target_domain="corporate_management",
        raw_entities=raw_data
    )
    
    # 2. Define Firewall Rules (Lexicon)
    noise_lexicon = {"cavalry", "phalanx", "chariot", "scroll", "legion"}
    
    # 3. Run Firewall
    try:
        filtered_entities = context_isolation_engine(
            packet, 
            noise_threshold=0.45, 
            custom_noise_lexicon=noise_lexicon
        )
        
        print("\n--- Transfer Results ---")
        for entity in filtered_entities:
            print(f"[VALID] ID: {entity.id} | Content: {entity.content}")
            
    except ValidationError as e:
        logger.error(f"Data validation failed: {e}")
    except Exception as e:
        logger.critical(f"System failure: {e}")

if __name__ == "__main__":
    run_simulation()