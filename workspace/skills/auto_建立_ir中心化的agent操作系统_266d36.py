"""
Module: ir_centric_agent_os.py

This module implements an IR (Intermediate Representation) Centric Agent Operating System.
Unlike traditional linear chain-based agents, this system treats the agent's workflow
as an iterative compilation process acting upon an 'IntentIR' object.

Core Concepts:
- IntentIR: A centralized state object representing the user's intent, current plan, and history.
- Pass: An atomic operation (e.g., planning, tool use, critique) that transforms the IR.
- Rollback: Capability to revert IR to a previous state upon failure, enabling robustness.

Author: Senior Python Engineer (AGI System)
"""

import logging
import copy
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IR_Agent_OS")


class PassStatus(Enum):
    """Status of a compilation pass."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


@dataclass
class IntentIR:
    """
    The Centralized Intermediate Representation object.
    This holds the complete state of the task resolution process.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str = ""
    current_plan: List[str] = field(default_factory=list)
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_context: Dict[str, Any] = field(default_factory=dict)
    final_response: Optional[str] = None
    
    # Internal state for version control (Memento pattern)
    _state_stack: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    def save_state(self) -> None:
        """Saves the current state to the history stack for potential rollback."""
        # Deep copy to ensure immutability of the snapshot
        snapshot = {
            'current_plan': copy.deepcopy(self.current_plan),
            'action_history': copy.deepcopy(self.action_history),
            'knowledge_context': copy.deepcopy(self.knowledge_context),
            'final_response': self.final_response
        }
        self._state_stack.append(snapshot)
        logger.debug(f"State saved. Stack depth: {len(self._state_stack)}")

    def rollback(self) -> bool:
        """Reverts the IR to the previous state."""
        if not self._state_stack:
            logger.warning("Rollback failed: No history available.")
            return False
        
        previous_state = self._state_stack.pop()
        self.current_plan = previous_state['current_plan']
        self.action_history = previous_state['action_history']
        self.knowledge_context = previous_state['knowledge_context']
        self.final_response = previous_state['final_response']
        logger.info(f"IR Rolled back to previous state. Stack depth: {len(self._state_stack)}")
        return True


class BasePass:
    """
    Abstract base class for an Agent Pass.
    Each Pass acts as an independent compiler/transformation step on the IR.
    """
    
    pass_name: str = "BasePass"

    def execute(self, ir: IntentIR) -> PassStatus:
        """
        Executes the transformation logic on the IR.
        
        Args:
            ir (IntentIR): The centralized IR object.
            
        Returns:
            PassStatus: SUCCESS or FAILURE.
        """
        raise NotImplementedError("Execute method must be implemented by subclass.")


class PlannerPass(BasePass):
    """
    A Pass responsible for analyzing the query and generating a step-by-step plan.
    """
    pass_name = "PlannerPass"

    def execute(self, ir: IntentIR) -> PassStatus:
        logger.info(f"Executing {self.pass_name}...")
        if not ir.original_query:
            logger.error("PlannerPass failed: Empty query.")
            return PassStatus.FAILURE
        
        # Simulate Planning Logic
        ir.save_state()
        ir.current_plan = [
            "1. Analyze user request",
            "2. Search for relevant data",
            "3. Synthesize answer"
        ]
        ir.action_history.append({
            "step": "Planning",
            "status": "Completed",
            "timestamp": datetime.now().isoformat()
        })
        logger.info("Plan generated successfully.")
        return PassStatus.SUCCESS


class ToolPass(BasePass):
    """
    A Pass that simulates using an external tool (e.g., Search or Code Execution).
    Includes potential failure simulation for robustness testing.
    """
    pass_name = "ToolPass"

    def __init__(self, tool_name: str = "GenericTool", fail_mode: bool = False):
        self.tool_name = tool_name
        self.fail_mode = fail_mode

    def execute(self, ir: IntentIR) -> PassStatus:
        logger.info(f"Executing {self.pass_name} with tool {self.tool_name}...")
        
        # Validate Preconditions
        if not ir.current_plan:
            logger.error("ToolPass failed: No plan to execute.")
            return PassStatus.FAILURE

        if self.fail_mode:
            logger.error(f"Tool {self.tool_name} execution failed (Simulated).")
            return PassStatus.FAILURE

        # Simulate successful tool use
        ir.save_state()
        ir.knowledge_context['tool_result'] = f"Data retrieved by {self.tool_name}"
        ir.action_history.append({
            "step": "ToolExecution",
            "tool": self.tool_name,
            "status": "Success"
        })
        return PassStatus.SUCCESS


class CritiquePass(BasePass):
    """
    A Pass that verifies the results. If results are invalid, it returns FAILURE.
    """
    pass_name = "CritiquePass"

    def execute(self, ir: IntentIR) -> PassStatus:
        logger.info(f"Executing {self.pass_name}...")
        
        if 'tool_result' not in ir.knowledge_context:
            logger.warning("Critique failed: No tool result found.")
            return PassStatus.FAILURE
            
        # Simulate validation logic
        ir.final_response = f"Final Answer based on: {ir.knowledge_context['tool_result']}"
        return PassStatus.SUCCESS


class AgentOrchestrator:
    """
    The OS Kernel that manages the Pass sequence, handles errors, 
    and manages parallel execution or rollback logic.
    """

    def __init__(self):
        self.pass_registry: Dict[str, BasePass] = {}

    def register_pass(self, key: str, pass_instance: BasePass):
        """Registers a pass instance to the OS."""
        self.pass_registry[key] = pass_instance

    def run_workflow(self, ir: IntentIR, workflow_config: List[str]) -> IntentIR:
        """
        Executes a sequence of passes based on configuration.
        
        Args:
            ir (IntentIR): The initial IR.
            workflow_config (List[str]): List of keys identifying registered passes.
            
        Returns:
            IntentIR: The processed IR.
        """
        logger.info(f"Starting Workflow for Session: {ir.session_id}")
        
        for pass_key in workflow_config:
            if pass_key not in self.pass_registry:
                logger.error(f"Unknown Pass key: {pass_key}")
                continue
            
            current_pass = self.pass_registry[pass_key]
            
            # Execute Pass
            status = current_pass.execute(ir)
            
            if status == PassStatus.FAILURE:
                logger.warning(f"Pass {pass_key} failed. Initiating recovery...")
                
                # Example of Robustness: Rollback and try alternative path
                recovered = self._handle_failure(ir, pass_key)
                if not recovered:
                    logger.error("Workflow halted due to unrecoverable error.")
                    break
            else:
                logger.info(f"Pass {pass_key} completed successfully.")

        return ir

    def _handle_failure(self, ir: IntentIR, failed_pass_key: str) -> bool:
        """
        Internal helper to handle failures. 
        Attempts to rollback and try an alternative strategy.
        """
        # Rollback to state before the failed pass
        if ir.rollback():
            logger.info(f"System recovered state before {failed_pass_key}.")
            
            # Try a fallback pass if available (e.g., a backup tool)
            fallback_key = f"{failed_pass_key}_fallback"
            if fallback_key in self.pass_registry:
                logger.info(f"Attempting fallback strategy: {fallback_key}")
                fallback_pass = self.pass_registry[fallback_key]
                status = fallback_pass.execute(ir)
                return status == PassStatus.SUCCESS
            
        return False

# --- Utility Functions ---

def validate_ir_input(query: str) -> bool:
    """
    Validates the input query before creating an IR.
    
    Args:
        query (str): The user input string.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not query or not isinstance(query, str):
        return False
    if len(query) < 5: # Arbitrary boundary check
        logger.warning("Query too short.")
        return False
    return True

def pretty_print_ir(ir: IntentIR) -> str:
    """
    Formats the IR for display.
    """
    if not isinstance(ir, IntentIR):
        return "Invalid IR object"
    
    history = "\n".join([f"- {h}" for h in ir.action_history])
    return f"""
    === IR State ===
    ID: {ir.session_id}
    Plan: {ir.current_plan}
    Context: {ir.knowledge_context}
    Response: {ir.final_response}
    History:
    {history}
    ================
    """

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Input
    user_query = "Tell me about the latest AI trends."
    if not validate_ir_input(user_query):
        print("Invalid input.")
    else:
        # 2. Initialize IR and OS
        initial_ir = IntentIR(original_query=user_query)
        os_kernel = AgentOrchestrator()

        # 3. Register Passes (including fallbacks)
        # Primary tool that will fail
        os_kernel.register_pass("tool_step", ToolPass(tool_name="PrimarySearch", fail_mode=True))
        # Fallback tool that will succeed
        os_kernel.register_pass("tool_step_fallback", ToolPass(tool_name="BackupSearch", fail_mode=False))
        
        os_kernel.register_pass("planning", PlannerPass())
        os_kernel.register_pass("critique", CritiquePass())

        # 4. Define Workflow (Linear sequence)
        workflow = ["planning", "tool_step", "critique"]

        # 5. Execute
        final_ir = os_kernel.run_workflow(initial_ir, workflow)

        # 6. Output
        print(pretty_print_ir(final_ir))