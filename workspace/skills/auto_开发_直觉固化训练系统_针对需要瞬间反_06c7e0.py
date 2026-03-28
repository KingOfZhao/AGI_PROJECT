"""
Intuition Solidification Training System (直觉固化训练系统)

A high-performance training module designed to convert complex logical decision-making
into 'muscle memory' through high-frequency simulation and reaction time monitoring.

Core Concept:
In high-pressure fields (Emergency Medicine, Combat, Negotiation), conscious reasoning
is too slow. This system forces the user to repeatedly execute specific decision paths.
Once the user's reaction speed hits a threshold, the logic is 'Materialized' (cached)
as intuition. The system schedules periodic 'Refreshes' to prevent skill decay.

Author: AGI System
Version: 1.0.0
"""

import logging
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime, timedelta

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IntuitionTrainer")


class SkillStatus(Enum):
    """Status of the skill logic in the user's cognitive library."""
    UNTRAINED = "untrained"
    TRAINING = "training"
    MATERIALIZED = "materialized"  # Intuition formed
    DECAYED = "decayed"            # Needs refresh


class TrainingIntensity(Enum):
    """Intensity levels for simulation."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4


@dataclass
class DecisionScenario:
    """Represents a single training scenario (input) and expected logic (output)."""
    scenario_id: str
    description: str
    context: Dict[str, Any]  # e.g., {"patient_bp": 80, "oxygen_sat": 90}
    expected_action: str     # The correct decision path ID
    complexity_score: float  # 0.0 to 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class UserPerformance:
    """Tracks a user's performance on a specific scenario."""
    scenario_id: str
    attempts: int = 0
    successful_attempts: int = 0
    avg_reaction_time_ms: float = 0.0
    last_attempt_time: Optional[datetime] = None
    current_status: SkillStatus = SkillStatus.UNTRAINED
    last_refresh_time: Optional[datetime] = None

    def update_stats(self, reaction_time_ms: float, success: bool):
        """Updates rolling average of reaction time."""
        self.attempts += 1
        self.last_attempt_time = datetime.now()
        if success:
            self.successful_attempts += 1
        
        # Rolling average calculation
        prev_total = self.avg_reaction_time_ms * (self.attempts - 1)
        self.avg_reaction_time_ms = (prev_total + reaction_time_ms) / self.attempts
        logger.debug(f"Updated stats for {self.scenario_id}: Avg Time {self.avg_reaction_time_ms:.2f}ms")


class IntuitionSolidificationSystem:
    """
    Main system for managing the lifecycle of intuitive skills.
    """

    def __init__(self, reaction_threshold_ms: float = 200.0, decay_period_days: int = 7):
        """
        Initialize the training system.

        Args:
            reaction_threshold_ms (float): The target reaction time in milliseconds 
                                           to qualify as 'Materialized'.
            decay_period_days (int): Days before a materialized skill is considered decayed.
        """
        if reaction_threshold_ms <= 0:
            raise ValueError("Reaction threshold must be positive.")
        
        self.scenarios: Dict[str, DecisionScenario] = {}
        self.user_profiles: Dict[str, UserPerformance] = {}
        self.reaction_threshold_ms = reaction_threshold_ms
        self.decay_period = timedelta(days=decay_period_days)
        self._simulation_hooks: Dict[str, Callable] = {}
        
        logger.info(f"System Initialized. Target Threshold: {reaction_threshold_ms}ms")

    def load_scenario(self, scenario: DecisionScenario) -> None:
        """Register a new scenario into the system."""
        if not scenario.scenario_id or not scenario.expected_action:
            raise ValueError("Scenario must have an ID and expected action.")
        
        self.scenarios[scenario.scenario_id] = scenario
        self.user_profiles[scenario.scenario_id] = UserPerformance(scenario_id=scenario.scenario_id)
        logger.info(f"Loaded Scenario: {scenario.scenario_id} - {scenario.description}")

    def run_simulation_cycle(self, intensity: TrainingIntensity = TrainingIntensity.HIGH) -> Dict[str, Any]:
        """
        Core Function 1: Executes a training simulation cycle.
        
        Selects scenarios based on intensity, monitors reaction, and updates state.
        In a real application, this would interface with a UI or VR environment.
        Here, we simulate the input/output logic.
        
        Returns:
            Dict containing session summary.
        """
        logger.info(f"Starting Simulation Cycle (Intensity: {intensity.name})...")
        
        # Filter scenarios that need training or refresh
        candidates = [
            s for s in self.scenarios.values() 
            if self.user_profiles[s.scenario_id].current_status != SkillStatus.MATERIALIZED
            or self._check_decay(s.scenario_id)
        ]

        if not candidates:
            logger.info("All skills are materialized and up to date.")
            return {"status": "complete", "trained_count": 0}

        session_log = []
        
        for scenario in candidates:
            # Simulate the user interaction (Mocked for backend demonstration)
            # In production, this triggers an event and waits for callback
            start_time = time.perf_counter()
            
            # --- MOCK USER RESPONSE ---
            # Simulate processing time (e.g., 150ms to 500ms depending on complexity)
            # Lower complexity + higher attempts = faster reaction
            perf = self.user_profiles[scenario.scenario_id]
            base_latency = 300 + (scenario.complexity_score * 500) - (perf.attempts * 10)
            simulated_reaction_time = max(50, base_latency) # Clamp min 50ms
            time.sleep(simulated_reaction_time / 1000.0) # Simulate wait
            
            user_decision = scenario.expected_action # Assume correct decision for demo
            # --------------------------

            end_time = time.perf_counter()
            reaction_time_ms = (end_time - start_time) * 1000
            
            # Validate and Update
            is_correct = (user_decision == scenario.expected_action)
            self.update_performance_metrics(scenario.scenario_id, reaction_time_ms, is_correct)
            
            session_log.append({
                "scenario": scenario.scenario_id,
                "time_ms": round(reaction_time_ms, 2),
                "status": self.user_profiles[scenario.scenario_id].current_status.value
            })

        return {"status": "success", "log": session_log}

    def update_performance_metrics(self, scenario_id: str, reaction_time_ms: float, is_correct: bool) -> None:
        """
        Core Function 2: Analyzes performance and updates the cognitive state.
        
        Checks if the user has reached the 'Materialized' threshold.
        """
        if scenario_id not in self.user_profiles:
            logger.error(f"Unknown Scenario ID: {scenario_id}")
            return

        profile = self.user_profiles[scenario_id]
        profile.update_stats(reaction_time_ms, is_correct)

        # Logic for State Transition
        if profile.current_status == SkillStatus.MATERIALIZED:
            # Just refresh the timestamp
            profile.last_refresh_time = datetime.now()
            logger.info(f"Refreshed materialized view: {scenario_id}")
            return

        # Check Threshold
        # Requirement: Fast reaction AND high success rate
        success_rate = profile.successful_attempts / profile.attempts if profile.attempts > 0 else 0
        
        if (profile.avg_reaction_time_ms <= self.reaction_threshold_ms and 
            success_rate > 0.95 and 
            profile.attempts >= 5):
            
            profile.current_status = SkillStatus.MATERIALIZED
            profile.last_refresh_time = datetime.now()
            logger.warning(f"SKILL MATERIALIZED: {scenario_id}! Intuition locked.")
        else:
            profile.current_status = SkillStatus.TRAINING

    def _check_decay(self, scenario_id: str) -> bool:
        """
        Helper Function: Checks if a materialized skill has expired (decayed).
        """
        profile = self.user_profiles.get(scenario_id)
        if not profile or profile.current_status != SkillStatus.MATERIALIZED:
            return False
        
        if profile.last_refresh_time is None:
            return True
            
        if datetime.now() - profile.last_refresh_time > self.decay_period:
            profile.current_status = SkillStatus.DECAYED
            logger.warning(f"Skill DECAYED: {scenario_id}. Needs refresh.")
            return True
        
        return False

    def export_progress(self) -> str:
        """Exports current user state as JSON for external monitoring."""
        data = [asdict(p) for p in self.user_profiles.values()]
        # Convert datetime/enum to string for JSON serialization
        for item in data:
            item['current_status'] = item['current_status'].value
            if item['last_attempt_time']:
                item['last_attempt_time'] = item['last_attempt_time'].isoformat()
            if item['last_refresh_time']:
                item['last_refresh_time'] = item['last_refresh_time'].isoformat()
        return json.dumps(data, indent=2)


# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup System
    trainer = IntuitionSolidificationSystem(reaction_threshold_ms=250.0, decay_period_days=30)
    
    # 2. Define Scenarios (e.g., Emergency Triage)
    s1 = DecisionScenario(
        scenario_id="triage_car_crash",
        description="Car crash victim, unresponsive, heavy bleeding.",
        context={"victim_status": "unresponsive", "bleeding": "heavy"},
        expected_action="apply_tourniquet",
        complexity_score=0.8,
        tags=["emergency", "trauma"]
    )
    
    s2 = DecisionScenario(
        scenario_id="negotiation_hostile",
        description="Subject holding weapon, shouting incoherently.",
        context={"subject_armed": True, "rational": False},
        expected_action="call_backup_negotiator",
        complexity_score=0.9,
        tags=["crisis", "negotiation"]
    )
    
    trainer.load_scenario(s1)
    trainer.load_scenario(s2)
    
    # 3. Run Training Loop
    print("\n--- Starting Training Session ---")
    # Running multiple times to simulate skill acquisition
    for i in range(6):
        print(f"\nCycle {i+1}...")
        result = trainer.run_simulation_cycle()
        # print(result) # Uncomment to see detailed logs
    
    # 4. Check Status
    print("\n--- Final Status ---")
    print(trainer.export_progress())