"""
Module: cross_domain_binary_diagnostics.py

This module implements a high-level AGI skill: transferring the logical structure
of 'Binary Search' (commonly used in code debugging) into the domain of physical
craftsmanship troubleshooting (e.g., pottery making).

It provides a generalized diagnostic engine that maps logical 'search spaces'
to physical 'process sequences', enabling efficient fault isolation.
"""

import logging
from typing import List, Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiagnosticStatus(Enum):
    """Enumeration of possible diagnostic outcomes for a segment."""
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"

@dataclass
class ProcessSegment:
    """
    Represents a discrete segment of a manufacturing or logical process.
    
    Attributes:
        name: Identifier for the process segment (e.g., 'Drying', 'Firing').
        start_params: Dictionary of parameters defining the start state.
        end_params: Dictionary of parameters defining the end state.
        metadata: Additional contextual information.
    """
    name: str
    start_params: Dict[str, Any]
    end_params: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DiagnosticResult:
    """
    Container for the results of a binary diagnostic split.
    
    Attributes:
        split_point: The index where the split occurred.
        first_half_status: Status of the first half of the process.
        second_half_status: Status of the second half of the process.
        recommendation: Textual recommendation for the next step.
        remaining_range: The tuple of indices representing the new search range.
    """
    split_point: int
    first_half_status: DiagnosticStatus
    second_half_status: DiagnosticStatus
    recommendation: str
    remaining_range: Tuple[int, int]

class BinaryDiagnosticsEngine:
    """
    A generic engine for performing binary search-like diagnostics on sequential processes.
    
    This class abstracts the 'Binary Search' algorithm to work on physical or logical
    process chains. It requires a method to 'probe' the state of the process at a 
    specific point (The 'Midpoint').
    
    Usage Example:
        >>> # Mocking a pottery process
        >>> steps = [
        ...     ProcessSegment("Prep Clay", {}, {}),
        ...     ProcessSegment("Shape", {}, {}),
        ...     ProcessSegment("Dry", {}, {"humidity": "high"}), # Fault likely here or later
        ...     ProcessSegment("Fire", {}, {"temp": 1000}),
        ...     ProcessSegment("Glaze", {}, {})
        ... ]
        >>> 
        >>> # Fault detected in final product
        >>> def mock_probe(index):
        ...     # Simulate: Fault appears after index 2 (Drying)
        ...     return DiagnosticStatus.PASS if index < 2 else DiagnosticStatus.FAIL
        >>> 
        >>> engine = BinaryDiagnosticsEngine(steps, mock_probe)
        >>> # Perform one step of binary search
        >>> result = engine.diagnose_split((0, len(steps)))
        >>> print(result.recommendation)
    """

    def __init__(self, 
                 process_steps: List[ProcessSegment], 
                 probe_func: Callable[[int], DiagnosticStatus],
                 validation_mode: bool = True):
        """
        Initialize the Binary Diagnostics Engine.

        Args:
            process_steps: An ordered list of ProcessSegment objects representing the full workflow.
            probe_func: A callback function that accepts an index (int) and returns a DiagnosticStatus.
                        This simulates "checking" the state of the work-in-progress at that step.
            validation_mode: If True, performs input validation on initialization.
        
        Raises:
            ValueError: If process_steps is empty or probe_func is not callable.
        """
        if validation_mode:
            self._validate_inputs(process_steps, probe_func)
        
        self.process_steps = process_steps
        self.probe_func = probe_func
        self._step_count = len(process_steps)
        logger.info(f"BinaryDiagnosticsEngine initialized with {self._step_count} steps.")

    @staticmethod
    def _validate_inputs(steps: List[ProcessSegment], probe: Callable):
        """Helper function to validate initialization parameters."""
        if not steps:
            logger.error("Initialization failed: Process steps list cannot be empty.")
            raise ValueError("Process steps list cannot be empty.")
        if not callable(probe):
            logger.error("Initialization failed: Probe function must be callable.")
            raise TypeError("Probe function must be callable.")
        if not all(isinstance(s, ProcessSegment) for s in steps):
            logger.error("Initialization failed: All steps must be ProcessSegment instances.")
            raise TypeError("All items in process_steps must be ProcessSegment instances.")

    def _get_midpoint(self, start: int, end: int) -> int:
        """
        Calculate the midpoint between two indices.
        
        Args:
            start: Start index of the current search range.
            end: End index of the current search range.
            
        Returns:
            The integer index of the midpoint.
        """
        if start >= end:
            # Should be caught by boundaries, but safety check
            return start
        return start + (end - start) // 2

    def diagnose_split(self, current_range: Tuple[int, int]) -> DiagnosticResult:
        """
        Perform a single iteration of binary diagnostic logic on the process.
        
        This function identifies the midpoint of the provided range, simulates a check
        (via the probe_func), and determines which half of the process contains the fault.
        
        Logic Mapping (Code Debug -> Craft Debug):
        - Code: Check if bug exists at commit history midpoint.
        - Craft: Check if structural flaw exists after 'Drying' phase (midpoint).
        
        Args:
            current_range: A tuple (start_index, end_index) defining the current suspicion window.
                           Note: end_index is exclusive.
                           
        Returns:
            DiagnosticResult: An object containing the analysis results and next steps.
        
        Raises:
            IndexError: If the range is invalid.
        """
        start, end = current_range

        # Boundary Checks
        if start < 0 or end > self._step_count:
            logger.error(f"Range {current_range} out of bounds for process length {self._step_count}.")
            raise IndexError("Diagnostic range out of bounds.")
        if end - start <= 1:
            logger.info(f"Diagnostic converged to single step: Index {start}")
            step_name = self.process_steps[start].name
            return DiagnosticResult(
                split_point=start,
                first_half_status=DiagnosticStatus.INCONCLUSIVE,
                second_half_status=DiagnosticStatus.FAIL,
                recommendation=f"Fault isolated to final step: '{step_name}'. Please review this specific stage.",
                remaining_range=(start, start + 1)
            )

        mid = self._get_midpoint(start, end)
        segment_name = self.process_steps[mid].name
        
        logger.info(f"Probing process at midpoint index {mid} ('{segment_name}')...")

        try:
            # Execute the probe (Physical Domain: Inspect the pot at this stage)
            status = self.probe_func(mid)
        except Exception as e:
            logger.error(f"Probe function failed at index {mid}: {e}")
            raise RuntimeError(f"Probe function execution error: {e}") from e

        # Logic: 
        # If PASS at Midpoint -> Fault occurred AFTER Midpoint (Right Half)
        # If FAIL at Midpoint -> Fault occurred AT or BEFORE Midpoint (Left Half)
        
        if status == DiagnosticStatus.PASS:
            # Fault is in the second half
            new_range = (mid + 1, end)
            logger.info(f"Probe PASSED at '{segment_name}'. Isolating right half: {new_range}")
            return DiagnosticResult(
                split_point=mid,
                first_half_status=DiagnosticStatus.PASS,
                second_half_status=DiagnosticStatus.FAIL,
                recommendation=f"Process healthy up to '{segment_name}'. Focus search on later stages.",
                remaining_range=new_range
            )
        else:
            # Fault is in the first half (including midpoint)
            new_range = (start, mid + 1)
            logger.info(f"Probe FAILED at '{segment_name}'. Isolating left half: {new_range}")
            return DiagnosticResult(
                split_point=mid,
                first_half_status=DiagnosticStatus.FAIL,
                second_half_status=DiagnosticStatus.INCONCLUSIVE,
                recommendation=f"Defect detected by '{segment_name}'. Focus search on earlier stages.",
                remaining_range=new_range
            )

    def run_full_diagnosis(self) -> str:
        """
        Convenience method to run the binary search until the fault is isolated.
        
        Returns:
            A string summary of the diagnosed fault location.
        """
        low, high = 0, self._step_count
        steps_taken = 0
        max_steps = self._step_count + 2 # Safety break

        logger.info("--- Starting Full Binary Diagnosis ---")
        
        while low < high and steps_taken < max_steps:
            if high - low <= 1:
                step = self.process_steps[low]
                logger.info(f"Diagnosis Complete. Fault located at: {step.name}")
                return f"Fault isolated to process step: '{step.name}' (Index {low})"
            
            result = self.diagnose_split((low, high))
            low, high = result.remaining_range
            steps_taken += 1

        return "Diagnosis failed to converge."

# --- Helper Function for Demonstration ---

def create_pottery_process() -> List[ProcessSegment]:
    """
    Helper function to generate a mock pottery process chain.
    
    Returns:
        List[ProcessSegment]: A list of steps representing pottery creation.
    """
    return [
        ProcessSegment("Clay Preparation", {"moisture": 0.2}, {"moisture": 0.2}),
        ProcessSegment("Wedging", {"air_pockets": True}, {"air_pockets": False}),
        ProcessSegment("Shaping", {"form": "none"}, {"form": "vase"}),
        ProcessSegment("Drying", {"moisture": 0.2}, {"moisture": 0.05}), # Potential issue: uneven drying
        ProcessSegment("Bisque Firing", {"temp": 20}, {"temp": 1000}),
        ProcessSegment("Glazing", {"coating": 0}, {"coating": 1}),
        ProcessSegment("Glaze Firing", {"temp": 20}, {"temp": 1200})
    ]

def main():
    """
    Main execution block demonstrating the Cross-Domain Binary Search.
    """
    print("Initializing Cross-Domain Diagnostic System...")
    
    # 1. Setup the process chain
    process = create_pottery_process()
    
    # 2. Define the fault simulation
    # Scenario: The pot cracks. We suspect an issue in 'Drying' (Index 3).
    # The 'crack' becomes visible after step 3, but didn't exist before.
    # Logic: A probe before/at 3 might show latent issues or be healthy?
    # In Binary Search Debugging: We check if the bug (crack) exists at Midpoint.
    # Let's assume the physical flaw happens *during* Drying (Index 3).
    fault_index = 3 
    
    def physical_probe(index: int) -> DiagnosticStatus:
        """
        Simulates a master craftsman inspecting the pot at a specific stage.
        If index < fault_index: The process looks healthy (PASS).
        If index >= fault_index: The defect is present (FAIL).
        """
        if index < fault_index:
            print(f"  >> [Probe] Checking at step {index}: Structure intact.")
            return DiagnosticStatus.PASS
        else:
            print(f"  >> [Probe] Checking at step {index}: CRACK DETECTED!")
            return DiagnosticStatus.FAIL

    # 3. Initialize Engine
    try:
        engine = BinaryDiagnosticsEngine(process, physical_probe)
        
        # 4. Run automated diagnosis
        result = engine.run_full_diagnosis()
        print("-" * 30)
        print(f"FINAL RESULT: {result}")
        
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"Runtime Error: {e}")

if __name__ == "__main__":
    main()