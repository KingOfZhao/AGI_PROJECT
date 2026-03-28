"""
Module: auto_如何实现_结构化认知网络_向低代码_无代_0fcd5f
Description: Translates structured cognitive causal chains (AGI knowledge) into 
             IEC 61131-3 compliant Structured Text (ST) for PLCs.
Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogicalOperator(Enum):
    """Enumeration for logical operators in causal chains."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NONE = "NONE"  # Single condition

@dataclass
class CausalNode:
    """Represents a single node in the cognitive network (a condition)."""
    id: str
    variable: str
    operator: str  # e.g., '>', '<', '==', 'IS_TRUE'
    value: Union[float, int, bool, str]

@dataclass
class CausalLink:
    """Represents the connection between conditions and an action."""
    conditions: List[CausalNode]
    logic: LogicalOperator = LogicalOperator.NONE
    action: str = ""
    action_params: Dict[str, Union[str, float, int]] = field(default_factory=dict)

class CognitiveToSTCompiler:
    """
    Compiles structured cognitive networks into IEC 61131-3 Structured Text (ST).
    
    This class transforms abstract causal relationships (e.g., "If Temp > 100 AND Pressure < 50, 
    then Open Valve") into executable PLC logic code.
    """

    def __init__(self, variable_mapping: Optional[Dict[str, str]] = None):
        """
        Initializes the compiler.
        
        Args:
            variable_mapping (dict, optional): Mapping from cognitive variable names to PLC tags.
                                               e.g., {'temperature': 'IO_Sensor_Temp'}.
        """
        self.variable_mapping = variable_mapping or {}
        self._validated = False
        logger.info("CognitiveToSTCompiler initialized.")

    def _validate_input_data(self, causal_chain: CausalLink) -> bool:
        """
        Validates the structure and integrity of the input causal chain.
        
        Args:
            causal_chain (CausalLink): The cognitive logic to validate.
            
        Returns:
            bool: True if validation passes.
            
        Raises:
            ValueError: If data is incomplete or malformed.
        """
        if not causal_chain.action:
            msg = "Validation Error: Causal chain must have an action."
            logger.error(msg)
            raise ValueError(msg)
        
        if not causal_chain.conditions:
            msg = "Validation Error: Causal chain must have at least one condition."
            logger.error(msg)
            raise ValueError(msg)
            
        if len(causal_chain.conditions) > 1 and causal_chain.logic == LogicalOperator.NONE:
            msg = "Validation Error: Multiple conditions require a logical operator (AND/OR)."
            logger.error(msg)
            raise ValueError(msg)

        # Check boundary conditions for values
        for cond in causal_chain.conditions:
            if isinstance(cond.value, (int, float)) and not (-1e9 < cond.value < 1e9):
                logger.warning(f"Boundary Check: Value {cond.value} in condition {cond.id} is extreme.")
        
        self._validated = True
        return True

    def _sanitize_variable_name(self, var_name: str) -> str:
        """
        Helper function to map and sanitize variable names to valid PLC identifiers.
        
        Args:
            var_name (str): The raw variable name from the cognitive network.
            
        Returns:
            str: The sanitized or mapped PLC tag name.
        """
        # If a mapping exists, use it; otherwise, fallback to sanitized name
        if var_name in self.variable_mapping:
            return self.variable_mapping[var_name]
        
        # Basic sanitization: Replace spaces with underscores, remove special chars
        safe_name = var_name.replace(" ", "_")
        return ''.join(e for e in safe_name if e.isalnum() or e == '_')

    def _format_condition(self, node: CausalNode) -> str:
        """
        Formats a single CausalNode into a ST boolean expression.
        
        Args:
            node (CausalNode): The condition node.
            
        Returns:
            str: ST formatted string (e.g., "Temp_Sensor > 100").
        """
        var = self._sanitize_variable_name(node.variable)
        op = node.operator
        val = node.value
        
        # Handle formatting for different data types
        if isinstance(val, str):
            val_str = f"'{val}'"  # String literals need quotes in ST
        elif isinstance(val, bool):
            val_str = "TRUE" if val else "FALSE"
        else:
            val_str = str(val)
            
        return f"({var} {op} {val_str})"

    def generate_structured_text(self, causal_chain: CausalLink) -> str:
        """
        Core function to generate IEC 61131-3 Structured Text from a Causal Link.
        
        Args:
            causal_chain (CausalLink): The input cognitive logic object.
            
        Returns:
            str: A snippet of Structured Text code ready for PLC import.
            
        Example:
            >>> compiler = CognitiveToSTCompiler()
            >>> node = CausalNode(id='c1', variable='Temp', operator='>', value=80)
            >>> link = CausalLink(conditions=[node], action='Set_Alarm', action_params={'Val': True})
            >>> print(compiler.generate_structured_text(link))
            IF (Temp > 80) THEN
                Set_Alarm := TRUE;
            END_IF;
        """
        try:
            self._validate_input_data(causal_chain)
        except ValueError as e:
            return f"// Compilation Failed: {str(e)}"

        # Build the logic condition string
        condition_strings = [self._format_condition(c) for c in causal_chain.conditions]
        
        if causal_chain.logic == LogicalOperator.NONE:
            logic_expression = condition_strings[0]
        else:
            op = f" {causal_chain.logic.value} "
            logic_expression = op.join(condition_strings)

        # Build the action statement
        action_var = self._sanitize_variable_name(causal_chain.action)
        
        # Determine assignment value (default to TRUE for actions without params)
        if 'value' in causal_chain.action_params:
            assignment_val = causal_chain.action_params['value']
            if isinstance(assignment_val, bool):
                action_value = "TRUE" if assignment_val else "FALSE"
            elif isinstance(assignment_val, str):
                action_value = f"'{assignment_val}'"
            else:
                action_value = str(assignment_val)
        else:
            action_value = "TRUE"  # Default digital set

        # Construct final ST block
        st_code = f"""
(* Auto-generated by Cognitive Compiler *)
(* Source Logic: {causal_chain.logic.value} combination of {len(causal_chain.conditions)} conditions *)

IF {logic_expression} THEN
    {action_var} := {action_value};
END_IF;
        """
        
        logger.info(f"Successfully compiled logic for action: {action_var}")
        return st_code.strip()

# Example Usage
if __name__ == "__main__":
    # 1. Setup mapping (Simulating AGI knowing the physical IO tags)
    tag_map = {
        "temperature": "AI_Reactor_Temp",
        "pressure": "AI_System_Press",
        "cooling_valve": "DO_Cooling_Relay"
    }

    compiler = CognitiveToSTCompiler(variable_mapping=tag_map)

    # 2. Define Cognitive Logic (Simulating extracted knowledge graph)
    # Logic: IF Temperature > 100.5 AND Pressure IS_TRUE THEN Open Cooling Valve
    cond_temp = CausalNode(
        id="cond_1", 
        variable="temperature", 
        operator=">", 
        value=100.5
    )
    cond_pressure = CausalNode(
        id="cond_2", 
        variable="pressure", 
        operator=">=", 
        value=50.0
    )

    causal_link = CausalLink(
        conditions=[cond_temp, cond_pressure],
        logic=LogicalOperator.AND,
        action="cooling_valve",
        action_params={"value": True}
    )

    # 3. Compile to IEC 61131-3 ST
    plc_code = compiler.generate_structured_text(causal_link)
    
    print("-" * 40)
    print("Generated PLC Code (IEC 61131-3 ST):")
    print("-" * 40)
    print(plc_code)