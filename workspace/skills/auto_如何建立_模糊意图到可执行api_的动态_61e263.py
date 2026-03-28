"""
Module: semantic_grounding_mapper.py

This module implements a dynamic mapping mechanism to translate fuzzy, abstract
user intents (expressed as adjectives or natural language concepts) into
concrete, executable API calls with specific numerical parameters.

It serves as a "Semantic Grounding" layer for AGI systems, bridging the gap
between high-level human instructions (e.g., "make the UI atmospheric") and
low-level code execution (e.g., `set_padding(20)`).

Key Features:
- Context-aware parameter interpretation.
- Multi-objective optimization using weighted scoring.
- Heuristic mapping from semantic descriptors to numerical ranges.
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class OptimizationStrategy(Enum):
    """Strategy for resolving conflicts in multi-objective optimization."""
    WEIGHTED_SUM = "weighted_sum"
    PRIORITY_BASED = "priority_based"

@dataclass
class SemanticVariable:
    """Represents a resolved concrete variable derived from fuzzy intent."""
    name: str
    value: Any
    confidence: float
    source_intent: str

@dataclass
class APIEndpoint:
    """Represents an executable API endpoint."""
    name: str
    func: Callable
    required_params: List[str]
    description: str = ""

@dataclass
class IntentContext:
    """Contextual information used to disambiguate intents."""
    user_role: str = "default"
    device_type: str = "desktop"  # e.g., mobile, desktop, vr
    current_state: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Tuple[Union[int, float], Union[int, float]]] = field(default_factory=dict)

# --- Helper Functions ---

def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """
    Constrains a value to be within a specified range [min_val, max_val].
    
    Args:
        value: The input value.
        min_val: The lower bound.
        max_val: The upper bound.
        
    Returns:
        The clamped value.
    """
    if not isinstance(value, (int, float)):
        logger.warning(f"Invalid value type for clamping: {type(value)}. Returning min_val.")
        return min_val
    return max(min_val, min(value, max_val))

# --- Core Logic ---

class SemanticMapper:
    """
    Translates fuzzy semantic intents into concrete parameters and API calls.
    """

    def __init__(self):
        # Registry of available APIs
        self._api_registry: Dict[str, APIEndpoint] = {}
        # Semantic mapping rules: Intent -> (Param -> Value_Resolver)
        self._semantic_rules: Dict[str, Dict[str, Callable]] = {}
        logger.info("SemanticMapper initialized.")

    def register_api(self, endpoint: APIEndpoint) -> None:
        """Registers an executable API endpoint."""
        if not callable(endpoint.func):
            raise ValueError(f"API {endpoint.name} must have a callable function.")
        self._api_registry[endpoint.name] = endpoint
        logger.debug(f"API registered: {endpoint.name}")

    def define_semantic_rule(self, intent_keyword: str, param_name: str, 
                             resolver: Callable[[IntentContext], Any]) -> None:
        """
        Defines how a specific intent keyword affects a specific parameter.
        
        Args:
            intent_keyword: e.g., "atmospheric", "fast", "compact"
            param_name: e.g., "padding", "timeout", "font_size"
            resolver: A function taking IntentContext and returning a concrete value.
        """
        if intent_keyword not in self._semantic_rules:
            self._semantic_rules[intent_keyword] = {}
        self._semantic_rules[intent_keyword][param_name] = resolver

    def resolve_fuzzy_value(self, intent: str, context: IntentContext) -> Dict[str, SemanticVariable]:
        """
        Core Function 1: Resolves a fuzzy intent string into a set of concrete variables.
        
        It looks for keywords within the intent string and applies defined rules
        to generate parameter values, handling conflicts via weighted averaging.
        
        Args:
            intent: The fuzzy user intent (e.g., "make it atmospheric and minimal").
            context: The current context providing constraints and state.
            
        Returns:
            A dictionary of parameter names to SemanticVariable objects.
        """
        if not intent or not isinstance(intent, str):
            raise ValueError("Intent must be a non-empty string.")

        resolved_params: Dict[str, List[Tuple[float, Any]]] = {} # param -> [(weight, value), ...]
        tokens = intent.lower().split()
        
        # 1. Identify applicable rules
        for token in tokens:
            if token in self._semantic_rules:
                rules = self._semantic_rules[token]
                # Default weight based on token presence (could be enhanced by NLP salience)
                weight = 1.0 
                
                for param_name, resolver in rules.items():
                    try:
                        value = resolver(context)
                        if param_name not in resolved_params:
                            resolved_params[param_name] = []
                        resolved_params[param_name].append((weight, value, token))
                        logger.info(f"Resolved param '{param_name}' -> {value} (Source: '{token}')")
                    except Exception as e:
                        logger.error(f"Error resolving param {param_name} for token {token}: {e}")

        # 2. Multi-objective optimization / Conflict resolution
        final_vars: Dict[str, SemanticVariable] = {}
        for param_name, values in resolved_params.items():
            if not values:
                continue

            # Strategy: Weighted Average for numerical values
            total_weight = sum(v[0] for v in values)
            if total_weight == 0: total_weight = 1.0
            
            # Check type of first value to determine aggregation method
            sample_val = values[0][1]
            
            if isinstance(sample_val, (int, float)):
                # Numerical optimization: Weighted Average
                agg_value = sum(w * v for w, v, _ in values) / total_weight
                if isinstance(sample_val, int):
                    agg_value = round(agg_value)
            else:
                # Categorical optimization: Highest weight wins (Priority)
                values.sort(key=lambda x: x[0], reverse=True)
                agg_value = values[0][1]

            # 3. Apply Boundary Checks
            min_b, max_b = context.constraints.get(param_name, (None, None))
            if min_b is not None and max_b is not None:
                agg_value = clamp(agg_value, min_b, max_b)

            final_vars[param_name] = SemanticVariable(
                name=param_name,
                value=agg_value,
                confidence=min(1.0, total_weight / 2.0), # Simple confidence heuristic
                source_intent=intent
            )

        return final_vars

    def execute_intent(self, target_api: str, intent: str, context: IntentContext) -> Dict[str, Any]:
        """
        Core Function 2: Maps the intent to a specific API and executes it.
        
        Args:
            target_api: The name of the API to call.
            intent: The fuzzy intent string.
            context: Execution context.
            
        Returns:
            The execution result or error dictionary.
        """
        if target_api not in self._api_registry:
            logger.error(f"API '{target_api}' not found.")
            return {"status": "error", "message": f"API {target_api} not registered"}

        api = self._api_registry[target_api]
        
        # 1. Resolve parameters
        resolved_vars = self.resolve_fuzzy_value(intent, context)
        
        # 2. Prepare arguments
        kwargs = {}
        missing_params = []
        for p in api.required_params:
            if p in resolved_vars:
                kwargs[p] = resolved_vars[p].value
            elif p in context.current_state:
                # Fallback to current state if intent didn't override
                kwargs[p] = context.current_state[p]
            else:
                missing_params.append(p)

        if missing_params:
            logger.warning(f"Missing required parameters for {target_api}: {missing_params}")
            # In a real AGI system, we might query the user or a knowledge base here.
            # For this skill, we return an error.
            return {"status": "error", "message": f"Missing params: {missing_params}"}

        # 3. Execute
        logger.info(f"Executing API: {target_api} with args: {kwargs}")
        try:
            result = api.func(**kwargs)
            return {
                "status": "success", 
                "api": target_api, 
                "args_used": kwargs, 
                "result": result
            }
        except Exception as e:
            logger.exception(f"API Execution failed: {e}")
            return {"status": "exception", "message": str(e)}

# --- Mock API Functions ---

def mock_ui_set_style(padding: int, margin: int, opacity: float) -> str:
    """Simulates a UI API call."""
    return f"Style applied: padding={padding}px, margin={margin}px, opacity={opacity:.2f}"

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup the Mapper
    mapper = SemanticMapper()
    
    # 2. Register APIs
    ui_api = APIEndpoint(
        name="ui_set_style",
        func=mock_ui_set_style,
        required_params=["padding", "margin", "opacity"],
        description="Updates the UI styling"
    )
    mapper.register_api(ui_api)

    # 3. Define Semantic Rules (The "Brain" of the mapping)
    
    # Rule for "Atmospheric": Large padding, low opacity (breathing room)
    def resolve_atmospheric_padding(ctx: IntentContext) -> int:
        base = 30
        # Context awareness: mobile needs less padding
        if ctx.device_type == "mobile":
            return 15
        return base

    def resolve_atmospheric_opacity(ctx: IntentContext) -> float:
        return 0.85

    # Rule for "Compact": Small padding, high density
    def resolve_compact_padding(ctx: IntentContext) -> int:
        return 5
    
    def resolve_compact_margin(ctx: IntentContext) -> int:
        return 2

    mapper.define_semantic_rule("atmospheric", "padding", resolve_atmospheric_padding)
    mapper.define_semantic_rule("atmospheric", "opacity", resolve_atmospheric_opacity)
    mapper.define_semantic_rule("compact", "padding", resolve_compact_padding)
    mapper.define_semantic_rule("compact", "margin", resolve_compact_margin)

    # 4. Define Context
    # Constraint: Padding must be between 0 and 50
    ctx = IntentContext(
        device_type="desktop",
        constraints={
            "padding": (0, 50),
            "margin": (0, 20),
            "opacity": (0.0, 1.0)
        },
        current_state={"margin": 10, "opacity": 1.0} # Default state
    )

    # 5. Execute Fuzzy Intent
    print("-" * 50)
    print("Scenario 1: User says 'Make it atmospheric'")
    res1 = mapper.execute_intent("ui_set_style", "atmospheric", ctx)
    print(f"Result: {res1}")

    print("\n" + "-" * 50)
    print("Scenario 2: User says 'Make it atmospheric but compact' (Conflict)")
    # This tests multi-objective optimization. 
    # 'Atmospheric' wants padding=30, 'Compact' wants padding=5.
    # Weighted average should result in approx 17.5.
    res2 = mapper.execute_intent("ui_set_style", "atmospheric compact", ctx)
    print(f"Result: {res2}")

    print("\n" + "-" * 50)
    print("Scenario 3: Boundary Check")
    # Rule for "huge" not defined, but let's pretend we had one that returned 100
    # We can test boundary by manually injecting a variable for the demo or trusting the clamp logic.
    # Here we demonstrate valid usage.
    ctx_mobile = IntentContext(device_type="mobile", constraints={"padding": (0, 50)})
    res3 = mapper.execute_intent("ui_set_style", "atmospheric", ctx_mobile)
    # On mobile, atmospheric padding resolver returns 15
    print(f"Result (Mobile Atmospheric): {res3}")