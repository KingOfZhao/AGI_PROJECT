"""
Module: auto_dynamic_sop_balancer
Description: [Dynamic SOP Balancer] Creates a system capable of understanding 'violation rationality'.
             When operational data (bottom-up) deviates from SOPs (top-down) long-term without
             negative consequences or with increased efficiency, the system marks the node as a
             'Theoretical Conflict Zone'. AI assists in analyzing whether the deviation is due to
             environmental changes or new method discovery, automatically generating 'SOP Amendments'
             or 'Temporary Variance Permits' to achieve a dynamic closed-loop in process management.

Author: Senior Python Engineer (AGI System Core)
Version: 1.0.0
"""

import logging
import datetime
from typing import Dict, List, Optional, TypedDict, Union
from enum import Enum
from dataclasses import dataclass, field

# --- Configuration & Constants ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DynamicSOPBalancer")

class DeviationType(Enum):
    """Enumeration for the type of deviation detected."""
    ENVIRONMENTAL_DRIFT = "Environmental Drift (e.g., Equipment Aging)"
    NEW_METHOD_DISCOVERY = "New Method Discovery (Efficiency Optimization)"
    RANDOM_NOISE = "Random Noise / Anomaly"
    CRITICAL_FAILURE = "Critical Failure Risk"

class ActionType(Enum):
    """Enumeration for the system's decision action."""
    UPDATE_SOP = "Issue SOP Amendment"
    GRANT_VARIANCE = "Issue Temporary Variance Permit"
    IGNORE = "Maintain Current SOP"
    ALERT_SUPERVISOR = "Alert Human Supervisor"

# --- Data Structures ---

@dataclass
class OperationalRecord:
    """Represents a single record of operational data from a worker."""
    worker_id: str
    step_id: str
    timestamp: datetime.datetime
    execution_time: float  # in seconds
    outcome_quality: float # 0.0 (Failure) to 1.0 (Perfect)
    followed_sop: bool
    context_data: Dict[str, Union[str, float, int]] = field(default_factory=dict)

class ConflictZone(TypedDict):
    """Structure representing a detected theoretical conflict zone."""
    step_id: str
    frequency: int
    success_rate: float
    avg_efficiency_gain: float
    recommended_action: ActionType
    deviation_type: DeviationType

# --- Core Logic ---

class SOPComparator:
    """
    Compares real-time operational data against standard SOPs.
    Detects deviations and aggregates data for analysis.
    """

    def __init__(self, sop_baselines: Dict[str, Dict[str, float]]):
        """
        Initialize with SOP baselines.
        
        Args:
            sop_baselines (Dict): Dictionary mapping step_id to standard metrics 
                                  (e.g., standard_time, required_quality).
        """
        self.sop_baselines = sop_baselines
        self.deviation_buffer: Dict[str, List[OperationalRecord]] = {}
        logger.info("SOPComparator initialized with %d SOP steps.", len(sop_baselines))

    def ingest_operational_data(self, record: OperationalRecord) -> bool:
        """
        Ingests a single operational record and validates it against bounds.
        
        Args:
            record (OperationalRecord): The data record to ingest.
            
        Returns:
            bool: True if a deviation is detected, False otherwise.
            
        Raises:
            ValueError: If data validation fails.
        """
        # Data Validation
        if not 0.0 <= record.outcome_quality <= 1.0:
            logger.error("Invalid quality score for record by worker %s", record.worker_id)
            raise ValueError("Quality score must be between 0.0 and 1.0")
        
        if record.execution_time <= 0:
            logger.error("Invalid execution time for record by worker %s", record.worker_id)
            raise ValueError("Execution time must be positive")

        baseline = self.sop_baselines.get(record.step_id)
        if not baseline:
            logger.warning("Unknown Step ID encountered: %s", record.step_id)
            return False

        # Check for deviation (Bottom-up vs Top-down)
        # Logic: Not following SOP OR significantly faster with good quality
        is_deviating = False
        if not record.followed_sop:
            is_deviating = True
        elif record.execution_time < baseline['standard_time'] * 0.8: # 20% faster
            is_deviating = True

        if is_deviating:
            if record.step_id not in self.deviation_buffer:
                self.deviation_buffer[record.step_id] = []
            self.deviation_buffer[record.step_id].append(record)
            logger.info("Deviation detected at step %s by worker %s", record.step_id, record.worker_id)
            return True
        
        return False

    def get_deviation_clusters(self, min_samples: int = 5) -> Dict[str, List[OperationalRecord]]:
        """
        Returns clusters of deviations that meet the minimum frequency threshold.
        
        Args:
            min_samples (int): Minimum number of occurrences to consider it a pattern.
            
        Returns:
            Dict: A dictionary of step_ids to lists of records.
        """
        clusters = {
            step_id: records 
            for step_id, records in self.deviation_buffer.items() 
            if len(records) >= min_samples
        }
        return clusters


class DynamicSOPAnalyzer:
    """
    Analyzes conflict zones using AI logic to determine root causes 
    and generate corrective actions.
    """

    def __init__(self):
        self.conflict_zones: List[ConflictZone] = []
        logger.info("DynamicSOPAnalyzer initialized.")

    def _classify_deviation(self, records: List[OperationalRecord]) -> DeviationType:
        """
        Helper function to classify the type of deviation based on context.
        
        Args:
            records (List[OperationalRecord]): Historical records of the deviation.
            
        Returns:
            DeviationType: The classified type.
        """
        # Extract context features
        avg_age = sum(r.context_data.get('equipment_age_years', 0) for r in records) / len(records)
        
        # Heuristic Analysis
        if avg_age > 5.0:
            return DeviationType.ENVIRONMENTAL_DRIFT
        else:
            # Check if quality is maintained or improved
            avg_quality = sum(r.outcome_quality for r in records) / len(records)
            if avg_quality > 0.95:
                return DeviationType.NEW_METHOD_DISCOVERY
            
        return DeviationType.RANDOM_NOISE

    def analyze_and_recommend(self, step_id: str, records: List[OperationalRecord]) -> Optional[ConflictZone]:
        """
        Core function to analyze a specific conflict node and generate a recommendation.
        
        Args:
            step_id (str): The ID of the process step.
            records (List[OperationalRecord]): The list of deviating records.
            
        Returns:
            Optional[ConflictZone]: The analyzed result or None if invalid.
        """
        if not records:
            return None

        logger.info("Analyzing theoretical conflict zone for Step ID: %s", step_id)
        
        # Calculate Metrics
        total_cases = len(records)
        success_cases = sum(1 for r in records if r.outcome_quality > 0.9)
        success_rate = success_cases / total_cases
        
        avg_time = sum(r.execution_time for r in records) / total_cases
        # Assuming baseline is fetched or hardcoded for simplicity in logic
        # Here we assume a theoretical baseline of 100s for calculation demonstration
        efficiency_gain = (100.0 - avg_time) / 100.0 

        # Classify Deviation
        dev_type = self._classify_deviation(records)
        
        # Determine Action
        action = ActionType.IGNORE
        if success_rate > 0.95 and dev_type == DeviationType.NEW_METHOD_DISCOVERY:
            action = ActionType.UPDATE_SOP
            logger.warning("SYSTEM ALERT: New Method Detected. Recommending SOP Update for %s", step_id)
        elif success_rate > 0.85 and dev_type == DeviationType.ENVIRONMENTAL_DRIFT:
            action = ActionType.GRANT_VARIANCE
            logger.info("Context Change Detected. Recommending Temporary Variance for %s", step_id)
        elif success_rate < 0.5:
            action = ActionType.ALERT_SUPERVISOR
            logger.error("High Failure Rate in Deviation. Alerting Supervisor for %s", step_id)

        zone: ConflictZone = {
            "step_id": step_id,
            "frequency": total_cases,
            "success_rate": round(success_rate, 2),
            "avg_efficiency_gain": round(efficiency_gain, 2),
            "recommended_action": action,
            "deviation_type": dev_type
        }
        
        self.conflict_zones.append(zone)
        return zone

# --- Main Execution / Example ---

def run_sop_balancer_simulation():
    """
    Main function to demonstrate the Dynamic SOP Balancer workflow.
    """
    # 1. Define SOP Baselines
    sops = {
        "STEP_101_ASSEMBLY": {"standard_time": 50.0, "quality_threshold": 0.9},
        "STEP_102_WELD": {"standard_time": 120.0, "quality_threshold": 0.95}
    }

    # 2. Initialize Modules
    comparator = SOPComparator(sops)
    analyzer = DynamicSOPAnalyzer()

    # 3. Simulate Data Ingestion (Bottom-up data)
    # Scenario A: Workers found a faster way to assemble without quality loss (New Method)
    for i in range(10):
        rec = OperationalRecord(
            worker_id=f"W_{i%3}",
            step_id="STEP_101_ASSEMBLY",
            timestamp=datetime.datetime.now(),
            execution_time=35.0 + (i * 0.5), # Faster than standard 50.0
            outcome_quality=0.98,
            followed_sop=False, # Explicitly deviated
            context_data={"equipment_age_years": 1.0}
        )
        comparator.ingest_operational_data(rec)

    # Scenario B: Welding takes longer because machine is old (Environmental Drift)
    for i in range(8):
        rec = OperationalRecord(
            worker_id=f"W_{i%2}",
            step_id="STEP_102_WELD",
            timestamp=datetime.datetime.now(),
            execution_time=140.0, # Slower than standard 120.0
            outcome_quality=0.96, # Quality still good
            followed_sop=False, 
            context_data={"equipment_age_years": 7.5} # Old machine
        )
        comparator.ingest_operational_data(rec)

    # 4. Process Deviations (The 'Conflict' Analysis)
    clusters = comparator.get_deviation_clusters(min_samples=5)
    
    results = []
    for step_id, records in clusters.items():
        result = analyzer.analyze_and_recommend(step_id, records)
        if result:
            results.append(result)

    # 5. Output Results
    print("\n--- Dynamic SOP Balancer Report ---")
    for res in results:
        print(f"Node: {res['step_id']}")
        print(f"  Type: {res['deviation_type'].value}")
        print(f"  Success Rate: {res['success_rate']*100}%")
        print(f"  Action: {res['recommended_action'].value}")
        print("-" * 30)

if __name__ == "__main__":
    run_sop_balancer_simulation()