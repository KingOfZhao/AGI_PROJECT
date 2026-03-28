"""
Module: auto_构建_语义边界防御机制_当进行跨域_5ca199
Description: Implements a Semantic Boundary Defense Mechanism to detect and resolve
             'vocabulary traps' (homonyms with contradictory meanings) during
             cross-domain knowledge transfer (e.g., Biology to Computer Science).
Author: AGI System
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConflictSeverity(Enum):
    """Enumeration for conflict severity levels."""
    CRITICAL = "CRITICAL"  # Logic inversion (e.g., True vs False)
    HIGH = "HIGH"          # Opposite operations (e.g., Create vs Delete)
    MEDIUM = "MEDIUM"      # Contextual shift
    LOW = "LOW"            # Nuance difference


@dataclass
class Definition:
    """Represents a term definition within a specific domain."""
    domain: str
    description: str
    operational_logic: str  # e.g., "APPEND", "DELETE", "BOOLEAN_TRUE"
    synonyms: List[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    """Data structure for a detected semantic conflict."""
    term: str
    source_domain: str
    target_domain: str
    source_logic: str
    target_logic: str
    severity: ConflictSeverity
    resolution_strategy: str


class SemanticBoundaryDefense:
    """
    Core class for Semantic Boundary Defense.
    
    Prevents logical pollution during cross-domain operations by identifying
    and flagging terms that have conflicting definitions in different domains.
    
    Usage Example:
        >>> defender = SemanticBoundaryDefense()
        >>> defender.register_domain_definition("client", "Biology", 
        ...     "An organism that consumes resources", "CONSUME")
        >>> defender.register_domain_definition("client", "CS_Network", 
        ...     "A device requesting services", "REQUEST")
        >>> conflicts = defender.scan_for_conflicts("Biology", "CS_Network")
        >>> print(len(conflicts) > 0)
        True
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the defense mechanism.
        
        Args:
            strict_mode (bool): If True, raises exceptions on validation errors.
                               If False, logs warnings.
        """
        self._knowledge_base: Dict[str, Dict[str, Definition]] = {}
        self.strict_mode = strict_mode
        logger.info("SemanticBoundaryDefense initialized with strict_mode=%s", strict_mode)

    def register_domain_definition(self, 
                                   term: str, 
                                   domain: str, 
                                   description: str, 
                                   operational_logic: str,
                                   synonyms: Optional[List[str]] = None) -> None:
        """
        Registers a definition for a term within a specific domain.
        
        Args:
            term (str): The vocabulary term.
            domain (str): The domain context (e.g., 'Biology').
            description (str): Explanation of the term.
            operational_logic (str): Abstract representation of the logic 
                                     (e.g., 'INCREASE', 'DECREASE').
            synonyms (List[str], optional): List of synonyms.
        
        Raises:
            ValueError: If term or domain is empty.
        """
        if not term or not domain:
            msg = "Term and Domain cannot be empty."
            logger.error(msg)
            if self.strict_mode:
                raise ValueError(msg)
            return

        term = term.lower().strip()
        domain = domain.strip()
        
        definition = Definition(
            domain=domain,
            description=description,
            operational_logic=operational_logic.upper().strip(),
            synonyms=synonyms or []
        )

        if term not in self._knowledge_base:
            self._knowledge_base[term] = {}
        
        self._knowledge_base[term][domain] = definition
        logger.debug("Registered definition for '%s' in domain '%s'", term, domain)

    def _determine_severity(self, logic_a: str, logic_b: str) -> ConflictSeverity:
        """
        Helper function to determine severity based on logic opposition.
        
        Args:
            logic_a (str): Logic from source domain.
            logic_b (str): Logic from target domain.
            
        Returns:
            ConflictSeverity: The calculated severity level.
        """
        # Define antonym pairs (Logic A, Logic B) -> Severity
        opposition_map = {
            frozenset({"INCREASE", "DECREASE"}): ConflictSeverity.HIGH,
            frozenset({"TRUE", "FALSE"}): ConflictSeverity.CRITICAL,
            frozenset({"CREATE", "DELETE"}): ConflictSeverity.CRITICAL,
            frozenset({"START", "STOP"}): ConflictSeverity.HIGH,
            frozenset({"POSITIVE", "NEGATIVE"}): ConflictSeverity.HIGH,
        }

        pair = frozenset({logic_a, logic_b})
        return opposition_map.get(pair, ConflictSeverity.MEDIUM)

    def scan_for_conflicts(self, 
                           source_domain: str, 
                           target_domain: str) -> List[ConflictReport]:
        """
        Scans for vocabulary traps between two domains.
        
        Args:
            source_domain (str): The domain where the concept originates.
            target_domain (str): The domain to which the concept is being applied.
            
        Returns:
            List[ConflictReport]: A list of detected semantic conflicts.
        """
        if source_domain == target_domain:
            logger.warning("Source and Target domains are identical. No cross-domain check needed.")
            return []

        conflicts: List[ConflictReport] = []
        
        logger.info("Initiating semantic boundary scan: %s -> %s", source_domain, target_domain)

        for term, definitions in self._knowledge_base.items():
            source_def = definitions.get(source_domain)
            target_def = definitions.get(target_domain)

            # Only check if term exists in BOTH domains
            if source_def and target_def:
                if source_def.operational_logic != target_def.operational_logic:
                    severity = self._determine_severity(
                        source_def.operational_logic, 
                        target_def.operational_logic
                    )
                    
                    # Construct Resolution Strategy
                    strategy = (
                        f"ALERT: Term '{term}' implies '{source_def.operational_logic}' "
                        f"in {source_domain} but '{target_def.operational_logic}' in {target_domain}. "
                        f"Map explicitly to avoid logic pollution."
                    )

                    report = ConflictReport(
                        term=term,
                        source_domain=source_domain,
                        target_domain=target_domain,
                        source_logic=source_def.operational_logic,
                        target_logic=target_def.operational_logic,
                        severity=severity,
                        resolution_strategy=strategy
                    )
                    conflicts.append(report)
                    
                    logger.warning("Vocabulary Trap Detected: '%s' (%s)", term, severity.value)

        return conflicts

    def generate_bilingual_dictionary(self, 
                                      source_domain: str, 
                                      target_domain: str,
                                      output_format: str = "dict") -> Any:
        """
        Generates a mapping dictionary to resolve conflicts.
        
        Args:
            source_domain (str): Origin domain.
            target_domain (str): Target domain.
            output_format (str): 'dict' for Python dict, 'json' for JSON string.
            
        Returns:
            Dict or JSON string containing the mapping table.
        """
        conflicts = self.scan_for_conflicts(source_domain, target_domain)
        
        dictionary = {
            "metadata": {
                "source": source_domain,
                "target": target_domain,
                "generated_at": "timestamp_placeholder",
                "conflict_count": len(conflicts)
            },
            "mappings": []
        }

        for c in conflicts:
            entry = {
                "term": c.term,
                "source_meaning": c.source_logic,
                "target_meaning": c.target_logic,
                "warning_level": c.severity.value,
                "action": "REMAP_REQUIRED" if c.severity == ConflictSeverity.CRITICAL else "VERIFY_CONTEXT"
            }
            dictionary["mappings"].append(entry)
        
        if output_format == "json":
            return json.dumps(dictionary, indent=4)
        return dictionary


def run_defense_demonstration():
    """
    Standalone function to demonstrate the module capabilities.
    Simulates a scenario involving Biology concepts applied to Computer Science.
    """
    print("\n--- Initializing Semantic Boundary Defense System ---\n")
    
    # 1. Initialize System
    defender = SemanticBoundaryDefense(strict_mode=True)
    
    # 2. Populate Knowledge Base (Simulating Left-Right Brain / Cross-Domain concepts)
    
    # Domain 1: Biology (Left Domain)
    defender.register_domain_definition(
        term="virus",
        domain="Biology",
        description="An infectious agent that replicates only inside living cells.",
        operational_logic="REPLICATE_PARASITIC"
    )
    
    # Domain 2: Computer Science (Right Domain)
    defender.register_domain_definition(
        term="virus",
        domain="CS_Security",
        description="A type of malicious software that attaches itself to legitimate programs.",
        operational_logic="EXECUTE_MALICIOUS"
    )
    
    # Example of Logical Contradiction: "Host"
    # In Biology: Host provides resources (PASSIVE/GIVER)
    # In Networking: Host is a computational node (ACTIVE/PROCESSOR)
    defender.register_domain_definition(
        term="host",
        domain="Biology",
        description="An organism that harbors a parasitic organism.",
        operational_logic="RESOURCE_PROVIDER"
    )
    defender.register_domain_definition(
        term="host",
        domain="CS_Network",
        description="A computer or other device providing data or services.",
        operational_logic="SERVICE_PROVIDER"
    )

    # Example of Direct Logical Inversion: "Session"
    # In Parliment/Law: Session is a gathering (AGGREGATION)
    # In HTTP: Session is transient state storage (PERSISTENCE)
    defender.register_domain_definition(
        term="session",
        domain="Formal_Meetings",
        description="A meeting or period devoted to a particular activity.",
        operational_logic="INTERACTION_EVENT"
    )
    defender.register_domain_definition(
        term="session",
        domain="CS_Web",
        description="A semi-permanent interactive information interchange.",
        operational_logic="STATE_STORAGE"
    )

    print("\n--- Scanning for Semantic Traps (Biology -> CS_Security) ---\n")
    
    # 3. Execute Scan
    conflict_reports = defender.scan_for_conflicts("Biology", "CS_Security")
    
    # 4. Display Reports
    if not conflict_reports:
        print("No conflicts detected.")
    else:
        for report in conflict_reports:
            print(f"[{report.severity.value}] Term: '{report.term}'")
            print(f"  Bio Logic: {report.source_logic}")
            print(f"  CS Logic:  {report.target_logic}")
            print(f"  Strategy:  {report.resolution_strategy}")
            print("-" * 60)

    print("\n--- Generating Bilingual Dictionary (JSON Output) ---\n")
    
    # 5. Generate Dictionary
    dictionary_json = defender.generate_bilingual_dictionary("Biology", "CS_Security", output_format="json")
    print(dictionary_json)


if __name__ == "__main__":
    run_defense_demonstration()