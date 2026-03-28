"""
Module: auto_cognitive_impedance_matching.py

This module implements the 'auto_cognitive_impedance_matching' skill for AGI systems.
It focuses on dynamic regulation of AI output based on real-time monitoring of human
cognitive states (friction and load).

Core Philosophy:
    Instead of maximizing information density unidirectionally, this system performs
    'adaptive impedance matching'. It detects intent ambiguity or cognitive overload
    and responds by downgrading output complexity or generating clarifying questions.

Key Components:
    - CognitiveStateMonitor: Tracks interaction metrics (latency, error rate).
    - OutputGovernor: Adjusts the granularity and frequency of AI responses.
    - ImpedanceMatcher: Core logic bridging human state and system output.

Author: AGI System
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveImpedanceMatcher")


class CognitiveState(Enum):
    """Enumeration of possible human cognitive states during interaction."""
    OPTIMAL = "optimal"                 # Flow state, high bandwidth communication
    ENGAGED = "engaged"                 # Normal interaction
    CONFUSED = "confused"               # High friction, possible ambiguity
    OVERLOADED = "overloaded"           # High load, needs immediate reduction
    DISENGAGED = "disengaged"           # Low latency, no response (timeout)


class OutputStrategy(Enum):
    """Strategies for AI response generation."""
    FULL_DETAIL = "full_detail"         # Maximum information density
    SUMMARIZED = "summarized"           # Moderate reduction
    BULLETS = "key_points"              # High reduction, list format
    CLARIFICATION = "clarification"     # Stop output, ask questions
    EMERGENCY_STOP = "stop"             # Pause interaction


@dataclass
class InteractionMetrics:
    """
    Data container for real-time interaction telemetry.
    Used to calculate the current 'Cognitive Load'.
    """
    timestamp: float
    response_latency_ms: float          # Time taken for human to respond
    error_rate: float                   # Ratio of misunderstood commands (0.0-1.0)
    scroll_speed: float                 # Pixels per second (indicator of skimming)
    mouse_jitter: float                 # Pixels (indicator of frustration)
    idle_cycles: int                    # Number of cycles without input

    def validate(self) -> bool:
        """Validates the metric data bounds."""
        if not (0.0 <= self.error_rate <= 1.0):
            raise ValueError(f"Error rate {self.error_rate} out of bounds [0, 1]")
        if self.response_latency_ms < 0:
            raise ValueError("Latency cannot be negative")
        return True


@dataclass
class SystemOutput:
    """Structured output from the Impedance Matching system."""
    strategy: OutputStrategy
    content: str
    complexity_score: float             # 0.0 (simple) to 1.0 (complex)
    metadata: dict = field(default_factory=dict)


class CognitiveLoadAnalyzer:
    """
    Analyzes interaction metrics to determine the current cognitive state.
    Implements signal processing logic for state detection.
    """

    def __init__(self, latency_threshold_ms: float = 2000.0, error_threshold: float = 0.3):
        self.latency_threshold = latency_threshold_ms
        self.error_threshold = error_threshold
        self._history: List[InteractionMetrics] = []
        logger.info("CognitiveLoadAnalyzer initialized.")

    def update_history(self, metrics: InteractionMetrics) -> None:
        """Adds new metrics to history and maintains a sliding window."""
        metrics.validate()
        self._history.append(metrics)
        if len(self._history) > 10:
            self._history.pop(0)

    def assess_state(self, current_metrics: InteractionMetrics) -> CognitiveState:
        """
        Core heuristic function to assess human cognitive state.
        
        Args:
            current_metrics: The latest telemetry data points.
            
        Returns:
            CognitiveState: The determined state of the human user.
        """
        self.update_history(current_metrics)
        
        # Heuristic 1: Overload Detection (High latency + High errors)
        if (current_metrics.response_latency_ms > self.latency_threshold * 2 and
                current_metrics.error_rate > self.error_threshold):
            logger.warning("Cognitive OVERLOAD detected.")
            return CognitiveState.OVERLOADED

        # Heuristic 2: Confusion/Friction Detection (High jitter or specific error patterns)
        if current_metrics.mouse_jitter > 15.0 or current_metrics.error_rate > 0.1:
            logger.info("Confusion/Friction detected.")
            return CognitiveState.CONFUSED

        # Heuristic 3: Disengagement (Idle)
        if current_metrics.idle_cycles > 5:
            logger.info("User disengagement detected.")
            return CognitiveState.DISENGAGED

        # Heuristic 4: Optimal Flow (Fast response, low error)
        if (current_metrics.response_latency_ms < self.latency_threshold and
                current_metrics.error_rate < 0.05):
            logger.debug("Optimal cognitive flow.")
            return CognitiveState.OPTIMAL

        return CognitiveState.ENGAGED


class AdaptiveOutputController:
    """
    Controls the granularity and frequency of AI output based on cognitive state.
    Implements the 'Adaptive Impedance Matching' logic.
    """

    def __init__(self):
        self.current_complexity = 1.0
        logger.info("AdaptiveOutputController ready.")

    def _generate_clarification_question(self, context: str) -> SystemOutput:
        """Helper function to generate a question instead of an answer."""
        return SystemOutput(
            strategy=OutputStrategy.CLARIFICATION,
            content=f"I noticed some hesitation regarding '{context}'. Would you like me to explain the concept again or break it down into smaller steps?",
            complexity_score=0.1,
            metadata={"intent": "reduce_ambiguity"}
        )

    def regulate_output(self, 
                        target_state: CognitiveState, 
                        proposed_content: str, 
                        intent_confidence: float = 1.0) -> SystemOutput:
        """
        Adjusts the output based on the target cognitive state.
        
        Args:
            target_state: The current state of the user.
            proposed_content: The raw, high-density content the AI wants to output.
            intent_confidence: The AI's confidence in understanding user intent (0.0-1.0).
            
        Returns:
            SystemOutput: The adjusted, safe-to-display content package.
        """
        try:
            # Boundary check for confidence
            if not (0.0 <= intent_confidence <= 1.0):
                raise ValueError("Intent confidence must be between 0 and 1.")

            # Logic: If intent is ambiguous, force clarification regardless of load
            if intent_confidence < 0.6:
                logger.info(f"Low intent confidence ({intent_confidence}). Switching to Clarification.")
                return self._generate_clarification_question("current request")

            # Logic: Adaptive Impedance Matching based on Cognitive State
            if target_state == CognitiveState.OVERLOADED:
                # Severe downgrade: Stop complex output, provide simple summary
                self.current_complexity = 0.2
                return SystemOutput(
                    strategy=OutputStrategy.BULLETS,
                    content="I see you're busy. Here are the key takeaways:\n- Point A\n- Point B\n(Shall I pause?)",
                    complexity_score=0.2,
                    metadata={"downgrade_reason": "overload"}
                )

            elif target_state == CognitiveState.CONFUSED:
                # Moderate downgrade: Ask for guidance
                self.current_complexity = 0.5
                return self._generate_clarification_question("details")

            elif target_state == CognitiveState.OPTIMAL:
                # Increase bandwidth
                self.current_complexity = 1.0
                return SystemOutput(
                    strategy=OutputStrategy.FULL_DETAIL,
                    content=proposed_content,
                    complexity_score=1.0,
                    metadata={"bandwidth": "maximum"}
                )
                
            elif target_state == CognitiveState.DISENGAGED:
                return SystemOutput(
                    strategy=OutputStrategy.EMERGENCY_STOP,
                    content="",
                    complexity_score=0.0,
                    metadata={"status": "waiting_for_input"}
                )

            # Default (Engaged)
            self.current_complexity = 0.8
            return SystemOutput(
                strategy=OutputStrategy.SUMMARIZED,
                content=f"Summary: {proposed_content[:100]}...",
                complexity_score=0.7,
                metadata={"bandwidth": "standard"}
            )

        except Exception as e:
            logger.error(f"Error regulating output: {e}")
            # Fail-safe: Return a simple, safe message
            return SystemOutput(
                strategy=OutputStrategy.CLARIFICATION,
                content="An internal error occurred while adjusting to your state. How would you like to proceed?",
                complexity_score=0.1,
                metadata={"error": str(e)}
            )


# --- Integration / Usage Example ---

def run_interaction_cycle():
    """
    Simulates a full interaction cycle demonstrating the skill.
    """
    # Initialize components
    analyzer = CognitiveLoadAnalyzer(latency_threshold_ms=1500.0)
    controller = AdaptiveOutputController()

    # Simulate Input Data (Telemetry)
    raw_content = ("The optimization of the gradient descent algorithm requires "
                   "careful tuning of the learning rate and momentum to avoid local minima.")

    # Scenario 1: User is in Flow (Low Latency, Low Error)
    print("\n--- Scenario 1: Optimal Flow ---")
    metrics_optimal = InteractionMetrics(
        timestamp=time.time(),
        response_latency_ms=500.0,
        error_rate=0.01,
        scroll_speed=0.0,
        mouse_jitter=2.0,
        idle_cycles=0
    )
    state = analyzer.assess_state(metrics_optimal)
    output = controller.regulate_output(state, raw_content, intent_confidence=0.95)
    print(f"State: {state.value}")
    print(f"Output: {output.content}")
    print(f"Strategy: {output.strategy.value}")

    # Scenario 2: User is Overloaded (High Latency, High Errors)
    print("\n--- Scenario 2: Cognitive Overload ---")
    metrics_overload = InteractionMetrics(
        timestamp=time.time(),
        response_latency_ms=5000.0,  # Slow response
        error_rate=0.4,              # High errors
        scroll_speed=50.0,
        mouse_jitter=25.0,           # Frustrated movement
        idle_cycles=0
    )
    state = analyzer.assess_state(metrics_overload)
    output = controller.regulate_output(state, raw_content, intent_confidence=0.95)
    print(f"State: {state.value}")
    print(f"Output: {output.content}")
    print(f"Strategy: {output.strategy.value}")

    # Scenario 3: Intent Ambiguity (AI is unsure)
    print("\n--- Scenario 3: Intent Ambiguity ---")
    # Re-use optimal metrics, but low confidence
    state = analyzer.assess_state(metrics_optimal) 
    output = controller.regulate_output(state, raw_content, intent_confidence=0.4)
    print(f"State: {state.value}")
    print(f"Output: {output.content}")
    print(f"Strategy: {output.strategy.value}")

if __name__ == "__main__":
    run_interaction_cycle()