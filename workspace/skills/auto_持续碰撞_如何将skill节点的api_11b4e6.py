"""
Module: auto_continuous_collision_skill_api.py

This module implements a standardized API wrapper framework for AGI SKILL nodes.
It addresses the 'Continuous Collision' problem in skill orchestration by
encapsulating static skill descriptions into dynamic, composable, and
executable components.

The framework enables automatic chaining of skills (e.g., 'Buy Vegetables'
automatically invoking 'Payment') by enforcing strict contracts regarding
Inputs, Outputs, Preconditions, and Post-conditions.

Author: Senior Python Engineer (AGI Systems)
Date: 2023-10-27
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Callable, List, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillAPISystem")

# Type variable for generic data handling
T = TypeVar('T')

class SkillExecutionStatus(Enum):
    """Enumeration of possible execution states for a SKILL node."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # Preconditions not met

@dataclass
class SkillContext:
    """
    The shared state passed between skills during an orchestration session.
    This acts as the 'short-term memory' for the execution chain.
    """
    session_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)

    def update_state(self, key: str, value: Any):
        """Thread-safe state update (simplified for demo)."""
        self.state[key] = value
        logger.debug(f"Context updated: {key}={value}")

    def get_state(self, key: str) -> Optional[Any]:
        """Retrieve data from context."""
        return self.state.get(key)

@dataclass
class SkillAPI:
    """
    Standardized API Wrapper for a SKILL node.
    
    This class transforms a static description into an executable, composable unit.
    """
    name: str
    description: str
    input_schema: Dict[str, type]
    output_schema: Dict[str, type]
    preconditions: Callable[[SkillContext], bool]
    postconditions: Callable[[SkillContext, Dict], bool]
    executor: Callable[[SkillContext, Dict], Dict]
    dependencies: List[str] = field(default_factory=list)

    def _validate_input(self, inputs: Dict[str, Any]) -> bool:
        """Validates input data against the defined schema."""
        if not inputs:
            return True # Allow empty inputs if schema is empty
        
        for key, expected_type in self.input_schema.items():
            if key not in inputs:
                logger.error(f"Validation Error: Missing input '{key}' for skill '{self.name}'")
                return False
            if not isinstance(inputs[key], expected_type):
                # Special handling for int/float polymorphism
                if expected_type == float and isinstance(inputs[key], int):
                    continue
                logger.error(
                    f"Validation Error: Input '{key}' expected type {expected_type}, "
                    f"got {type(inputs[key])} in skill '{self.name}'"
                )
                return False
        return True

    def _validate_output(self, outputs: Dict[str, Any]) -> bool:
        """Validates output data against the defined schema."""
        for key, expected_type in self.output_schema.items():
            if key not in outputs:
                logger.error(f"Validation Error: Missing output '{key}' in skill '{self.name}'")
                return False
            if not isinstance(outputs[key], expected_type):
                 if expected_type == float and isinstance(outputs[key], int):
                    continue
                 logger.error(
                    f"Validation Error: Output '{key}' expected type {expected_type}, "
                    f"got {type(outputs[key])} in skill '{self.name}'"
                )
                 return False
        return True

    def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Executes the skill logic with full lifecycle management:
        1. Check Preconditions (Collision detection)
        2. Validate Inputs
        3. Execute Logic
        4. Validate Outputs
        5. Verify Postconditions
        6. Update Context
        """
        logger.info(f"Attempting to execute SKILL: {self.name}")
        context.history.append(f"START:{self.name}")

        # 1. Collision Detection / Pre-check
        if not self.preconditions(context):
            logger.warning(f"SKILL {self.name} SKIPPED: Preconditions not met.")
            context.history.append(f"SKIP:{self.name}")
            return {"status": SkillExecutionStatus.SKIPPED, "message": "Preconditions failed"}

        # 2. Input Validation
        if not self._validate_input(kwargs):
            raise ValueError(f"Invalid input arguments for skill {self.name}")

        try:
            # 3. Execution
            start_time = time.time()
            result_data = self.executor(context, kwargs)
            duration = time.time() - start_time
            
            logger.info(f"SKILL {self.name} executed in {duration:.4f}s")

            # 4. Output Validation
            if not self._validate_output(result_data):
                raise RuntimeError(f"Skill {self.name} returned invalid output structure")

            # 5. Postcondition Verification
            if not self.postconditions(context, result_data):
                logger.error(f"Postcondition failed for {self.name}. Rolling back logic (simulation).")
                raise RuntimeError("Postcondition check failed")

            # 6. Update Context
            for k, v in result_data.items():
                context.update_state(k, v)
            
            context.history.append(f"END:{self.name}")
            return {"status": SkillExecutionStatus.SUCCESS, "data": result_data}

        except Exception as e:
            logger.exception(f"SKILL {self.name} FAILED: {str(e)}")
            context.history.append(f"FAIL:{self.name}")
            return {"status": SkillExecutionStatus.FAILED, "error": str(e)}

# --- Helper Functions for Skill Construction ---

def create_skill_node(
    name: str,
    desc: str,
    inputs: Dict[str, type],
    outputs: Dict[str, type],
    logic: Callable,
    pre_check: Optional[Callable] = None,
    post_check: Optional[Callable] = None
) -> SkillAPI:
    """
    Factory function to reduce boilerplate when creating SkillAPI instances.
    Provides default pass-all conditions if not specified.
    """
    default_pre = lambda ctx: True
    default_post = lambda ctx, res: True

    return SkillAPI(
        name=name,
        description=desc,
        input_schema=inputs,
        output_schema=outputs,
        preconditions=pre_check if pre_check else default_pre,
        postconditions=post_check if post_check else default_post,
        executor=logic
    )

def compose_skills(skills: List[SkillAPI], initial_context: SkillContext) -> SkillContext:
    """
    Orchestrates a sequence of skills. If a skill returns SKIPPED or FAILED,
    the chain behavior can be customized (here we continue but log).
    """
    logger.info(f"Starting composition chain for {len(skills)} skills.")
    for skill in skills:
        # In a real AGI system, inputs would be dynamically extracted from context
        # Here we pass empty kwargs assuming the skill reads from context directly
        skill.execute(initial_context)
    
    logger.info("Composition chain completed.")
    return initial_context

# --- Example Usage: "Buy Vegetables" -> "Payment" ---

if __name__ == "__main__":
    # 1. Define Logic for 'Buy Vegetables'
    def logic_buy_veggies(ctx: SkillContext, args: Dict) -> Dict:
        logger.info("Selecting items: Tomato, Potato")
        total_cost = 15.50
        return {"cart_items": ["Tomato", "Potato"], "total_cost": total_cost}

    # 2. Define Logic for 'Payment'
    def logic_payment(ctx: SkillContext, args: Dict) -> Dict:
        cost = ctx.get_state("total_cost")
        if not cost:
            raise ValueError("No cost found in context")
        
        logger.info(f"Processing payment of ${cost}...")
        # Simulate payment gateway interaction
        time.sleep(0.1) 
        return {"payment_status": "COMPLETED", "receipt_id": "REC-001"}

    # Precondition for Payment: Must have items in cart
    def pre_payment(ctx: SkillContext) -> bool:
        items = ctx.get_state("cart_items")
        cost = ctx.get_state("total_cost")
        return bool(items) and cost > 0

    # Postcondition for Payment: Receipt ID must exist
    def post_payment(ctx: SkillContext, result: Dict) -> bool:
        return "receipt_id" in result

    # 3. Construct Nodes
    skill_veggies = create_skill_node(
        name="purchase_vegetables",
        desc="Selects vegetables and calculates cost",
        inputs={}, # Reads from logic internal state
        outputs={"cart_items": list, "total_cost": float},
        logic=logic_buy_veggies
    )

    skill_payment = create_skill_node(
        name="process_payment",
        desc="Executes transaction for cart items",
        inputs={}, # Inputs come from Context state
        outputs={"payment_status": str, "receipt_id": str},
        logic=logic_payment,
        pre_check=pre_payment,
        post_check=post_payment
    )

    # 4. Run Orchestration
    session = SkillContext(session_id="sess_12345")
    
    # Try running just payment first (should skip due to precondition)
    print("\n--- Test 1: Payment without Cart ---")
    skill_payment.execute(session)
    
    # Run the full chain
    print("\n--- Test 2: Full Chain ---")
    compose_skills([skill_veggies, skill_payment], session)
    
    print("\nFinal Context State:")
    print(json.dumps(session.state, indent=2))
    print("\nExecution History:")
    print(json.dumps(session.history, indent=2))