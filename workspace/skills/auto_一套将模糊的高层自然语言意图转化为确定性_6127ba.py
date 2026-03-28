"""
Safe Intent Compilation System for AGI
======================================
A robust compilation framework that transforms high-level natural language 
intents into deterministic physical execution sequences through quantum-inspired 
state collapse mechanisms.

Key Features:
- Intent-Code Isomorphism Verification (ho_96_O1_2685)
- Adaptive Granularity Decomposition (bu_97_P3_7461)
- Hybrid Verification System (bu_97_P3_9406)
- Compile-Execute-Feedback Loop (bu_96_P4_50)

Author: AGI Systems Engineering Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentComplexity(Enum):
    """Classification of intent complexity levels"""
    ATOMIC = auto()
    COMPOSITE = auto()
    AMBIGUOUS = auto()
    INVALID = auto()


class ExecutionStatus(Enum):
    """Execution status codes"""
    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()
    FAILURE = auto()
    REQUIRES_CLARIFICATION = auto()


@dataclass
class Intent:
    """Data structure representing a parsed intent"""
    raw_text: str
    action: str
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    complexity: IntentComplexity = IntentComplexity.ATOMIC


@dataclass
class AtomicOperation:
    """Represents a single executable atomic operation"""
    operation_id: str
    action_type: str
    parameters: Dict[str, Any]
    preconditions: List[Callable] = field(default_factory=list)
    postconditions: List[Callable] = field(default_factory=list)
    safety_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of intent execution"""
    status: ExecutionStatus
    operations_executed: List[str]
    feedback: Dict[str, Any]
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def validate_input(func: Callable) -> Callable:
    """
    Decorator for input validation (part of hybrid verification system bu_97_P3_9406)
    
    Ensures that inputs meet structural and semantic requirements before processing.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Validate all string inputs for safety
        for arg in args:
            if isinstance(arg, str):
                if len(arg) > 10000:
                    raise ValueError(f"Input exceeds maximum length: {len(arg)} > 10000")
                if re.search(r'[<>&\';"]', arg):
                    logger.warning(f"Potentially unsafe characters in input: {arg[:50]}...")
        
        result = func(*args, **kwargs)
        return result
    return wrapper


class IntentCompiler:
    """
    Core compiler class implementing the Safe Intent Compilation System.
    
    This class transforms fuzzy natural language intents into deterministic
    atomic operations through a multi-stage compilation process.
    """
    
    # Action vocabulary with associated parameter schemas
    ACTION_SCHEMAS = {
        'move': {
            'required': ['destination'],
            'optional': ['speed', 'path_type', 'avoid_obstacles'],
            'safety_bounds': {
                'speed': (0.0, 10.0),  # m/s
                'acceleration': (0.0, 5.0)  # m/s²
            }
        },
        'grasp': {
            'required': ['target_object'],
            'optional': ['force', 'approach_angle', 'gripper_type'],
            'safety_bounds': {
                'force': (0.5, 50.0),  # Newtons
                'approach_angle': (-90.0, 90.0)  # degrees
            }
        },
        'speak': {
            'required': ['message'],
            'optional': ['volume', 'language', 'tone'],
            'safety_bounds': {
                'volume': (0.0, 1.0),
                'duration': (0.0, 300.0)  # seconds
            }
        },
        'search': {
            'required': ['query'],
            'optional': ['scope', 'max_results', 'filters'],
            'safety_bounds': {
                'max_results': (1, 1000)
            }
        }
    }
    
    def __init__(self, safety_threshold: float = 0.85, max_decomposition_depth: int = 5):
        """
        Initialize the Intent Compiler.
        
        Args:
            safety_threshold: Minimum confidence threshold for execution (0.0-1.0)
            max_decomposition_depth: Maximum depth for intent decomposition
        """
        if not 0.0 <= safety_threshold <= 1.0:
            raise ValueError("Safety threshold must be between 0.0 and 1.0")
        if max_decomposition_depth < 1:
            raise ValueError("Max decomposition depth must be at least 1")
            
        self.safety_threshold = safety_threshold
        self.max_decomposition_depth = max_decomposition_depth
        self._operation_counter = 0
        self._execution_history: List[ExecutionResult] = []
        
        logger.info(f"IntentCompiler initialized with safety_threshold={safety_threshold}")
    
    @validate_input
    def parse_intent(self, natural_language_input: str, context: Optional[Dict] = None) -> Intent:
        """
        Parse natural language input into structured Intent object.
        
        This implements the first stage of the compilation pipeline,
        extracting action, entities, and constraints from fuzzy input.
        
        Args:
            natural_language_input: Raw natural language command
            context: Optional context dictionary with environmental info
            
        Returns:
            Intent: Structured intent object
            
        Raises:
            ValueError: If input cannot be parsed into valid intent
            
        Example:
            >>> compiler = IntentCompiler()
            >>> intent = compiler.parse_intent("Move to the kitchen quickly")
            >>> print(intent.action)
            'move'
        """
        if not natural_language_input or not natural_language_input.strip():
            raise ValueError("Input cannot be empty")
        
        context = context or {}
        normalized_input = natural_language_input.lower().strip()
        
        # Extract action (simplified NLP - in production use proper NLP pipeline)
        action = self._extract_action(normalized_input)
        if not action:
            return Intent(
                raw_text=natural_language_input,
                action='unknown',
                complexity=IntentComplexity.INVALID,
                confidence=0.0
            )
        
        # Extract entities and constraints
        entities = self._extract_entities(normalized_input, action)
        constraints = self._extract_constraints(normalized_input)
        
        # Determine complexity
        complexity = self._assess_complexity(normalized_input, action, entities)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(action, entities, constraints)
        
        intent = Intent(
            raw_text=natural_language_input,
            action=action,
            entities=entities,
            constraints=constraints,
            context=context,
            confidence=confidence,
            complexity=complexity
        )
        
        logger.debug(f"Parsed intent: {intent.action} with confidence {confidence:.2f}")
        return intent
    
    def decompose_intent(self, intent: Intent, depth: int = 0) -> List[AtomicOperation]:
        """
        Decompose complex intent into atomic operations.
        
        Implements Adaptive Granularity Decomposition (bu_97_P3_7461).
        Recursively breaks down composite intents until atomic level is reached.
        
        Args:
            intent: The intent to decompose
            depth: Current recursion depth
            
        Returns:
            List[AtomicOperation]: List of atomic operations
            
        Raises:
            RuntimeError: If max decomposition depth exceeded
        """
        if depth > self.max_decomposition_depth:
            raise RuntimeError(f"Max decomposition depth {self.max_decomposition_depth} exceeded")
        
        operations = []
        
        if intent.complexity == IntentComplexity.INVALID:
            raise ValueError(f"Cannot decompose invalid intent: {intent.raw_text}")
        
        if intent.complexity == IntentComplexity.ATOMIC:
            # Direct conversion to atomic operation
            op = self._create_atomic_operation(intent)
            operations.append(op)
            
        elif intent.complexity == IntentComplexity.COMPOSITE:
            # Decompose into sub-intents
            sub_intents = self._split_composite_intent(intent)
            for sub_intent in sub_intents:
                operations.extend(self.decompose_intent(sub_intent, depth + 1))
                
        elif intent.complexity == IntentComplexity.AMBIGUOUS:
            # Request clarification through feedback channel
            operations.append(self._create_clarification_request(intent))
        
        logger.info(f"Decomposed intent into {len(operations)} operations at depth {depth}")
        return operations
    
    def verify_isomorphism(self, intent: Intent, operations: List[AtomicOperation]) -> Tuple[bool, float]:
        """
        Verify intent-code isomorphism (ho_96_O1_2685).
        
        Ensures that the generated operations faithfully represent the original intent.
        This is critical for preventing goal drift during compilation.
        
        Args:
            intent: Original intent
            operations: Generated atomic operations
            
        Returns:
            Tuple[bool, float]: (is_isomorphic, alignment_score)
        """
        if not operations:
            return False, 0.0
        
        # Check action coverage
        expected_actions = {intent.action}
        actual_actions = {op.action_type for op in operations}
        
        action_coverage = len(expected_actions & actual_actions) / len(expected_actions)
        
        # Check entity preservation
        entity_score = self._verify_entity_preservation(intent, operations)
        
        # Check constraint satisfaction
        constraint_score = self._verify_constraint_satisfaction(intent, operations)
        
        # Combined alignment score
        alignment_score = (action_coverage * 0.4 + entity_score * 0.3 + constraint_score * 0.3)
        
        is_isomorphic = alignment_score >= self.safety_threshold
        
        if not is_isomorphic:
            logger.warning(
                f"Isomorphism check failed: score={alignment_score:.3f} < threshold={self.safety_threshold}"
            )
        
        return is_isomorphic, alignment_score
    
    def execute_operations(
        self, 
        operations: List[AtomicOperation],
        dry_run: bool = True
    ) -> ExecutionResult:
        """
        Execute compiled atomic operations with safety checks.
        
        Implements the Compile-Execute-Feedback Loop (bu_96_P4_50).
        
        Args:
            operations: List of atomic operations to execute
            dry_run: If True, simulate execution without actual effects
            
        Returns:
            ExecutionResult: Result of the execution attempt
        """
        executed_ops = []
        feedback = {}
        metrics = {'total_time': 0.0, 'success_rate': 0.0}
        successful_count = 0
        
        for op in operations:
            try:
                # Check preconditions
                preconditions_met = all(
                    check(op.parameters) for check in op.preconditions
                ) if op.preconditions else True
                
                if not preconditions_met:
                    feedback[op.operation_id] = "Preconditions not met"
                    continue
                
                # Check safety bounds
                bounds_ok = self._check_safety_bounds(op)
                if not bounds_ok:
                    feedback[op.operation_id] = "Safety bounds violation"
                    continue
                
                if not dry_run:
                    # Actual execution would happen here
                    # This is a simulation for demonstration
                    logger.info(f"Executing operation: {op.operation_id}")
                
                executed_ops.append(op.operation_id)
                successful_count += 1
                
                # Verify postconditions
                if op.postconditions and not dry_run:
                    postconditions_met = all(
                        check(op.parameters) for check in op.postconditions
                    )
                    if not postconditions_met:
                        feedback[op.operation_id] = "Postconditions not satisfied"
                
            except Exception as e:
                logger.error(f"Error executing {op.operation_id}: {str(e)}")
                feedback[op.operation_id] = str(e)
        
        metrics['success_rate'] = successful_count / len(operations) if operations else 0.0
        
        # Determine overall status
        if successful_count == len(operations):
            status = ExecutionStatus.SUCCESS
        elif successful_count > 0:
            status = ExecutionStatus.PARTIAL_SUCCESS
        else:
            status = ExecutionStatus.FAILURE
        
        result = ExecutionResult(
            status=status,
            operations_executed=executed_ops,
            feedback=feedback,
            metrics=metrics
        )
        
        self._execution_history.append(result)
        return result
    
    def compile_and_execute(
        self, 
        natural_language_input: str,
        context: Optional[Dict] = None,
        dry_run: bool = True
    ) -> ExecutionResult:
        """
        Full compilation and execution pipeline.
        
        This is the main entry point combining all stages:
        1. Parse intent
        2. Decompose into atomic operations
        3. Verify isomorphism
        4. Execute with feedback
        
        Args:
            natural_language_input: Raw command
            context: Optional execution context
            dry_run: Simulate execution if True
            
        Returns:
            ExecutionResult: Final execution result
        """
        try:
            # Stage 1: Parse
            intent = self.parse_intent(natural_language_input, context)
            
            if intent.complexity == IntentComplexity.INVALID:
                return ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    operations_executed=[],
                    feedback={'error': 'Invalid intent - could not parse'}
                )
            
            # Stage 2: Decompose
            operations = self.decompose_intent(intent)
            
            # Stage 3: Verify
            is_isomorphic, alignment = self.verify_isomorphism(intent, operations)
            
            if not is_isomorphic:
                return ExecutionResult(
                    status=ExecutionStatus.REQUIRES_CLARIFICATION,
                    operations_executed=[],
                    feedback={
                        'error': 'Intent-code isomorphism failed',
                        'alignment_score': alignment
                    }
                )
            
            # Stage 4: Execute
            result = self.execute_operations(operations, dry_run)
            
            logger.info(f"Pipeline completed: {result.status.name}")
            return result
            
        except Exception as e:
            logger.exception("Compilation pipeline failed")
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                operations_executed=[],
                feedback={'error': str(e)}
            )
    
    # ==================== Helper Methods ====================
    
    def _extract_action(self, text: str) -> Optional[str]:
        """Extract primary action from normalized text"""
        action_keywords = {
            'move': ['move', 'go', 'travel', 'navigate', 'walk', 'drive'],
            'grasp': ['grasp', 'grab', 'hold', 'pick', 'take', 'seize'],
            'speak': ['speak', 'say', 'tell', 'announce', 'communicate'],
            'search': ['search', 'find', 'look', 'locate', 'seek']
        }
        
        for action, keywords in action_keywords.items():
            for keyword in keywords:
                if keyword in text.split():
                    return action
        return None
    
    def _extract_entities(self, text: str, action: str) -> Dict[str, Any]:
        """Extract entities related to the action"""
        entities = {}
        
        if action == 'move':
            # Simple location extraction
            location_patterns = [
                r'to (?:the )?(\w+)',
                r'towards (?:the )?(\w+)',
                r'into (?:the )?(\w+)'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, text)
                if match:
                    entities['destination'] = match.group(1)
                    break
                    
        elif action == 'grasp':
            # Object extraction
            object_patterns = [
                r'(?:the )?(\w+)',
                r'grab (?:the )?(\w+)',
                r'pick up (?:the )?(\w+)'
            ]
            for pattern in object_patterns:
                match = re.search(pattern, text)
                if match:
                    entities['target_object'] = match.group(1)
                    break
        
        return entities
    
    def _extract_constraints(self, text: str) -> Dict[str, Any]:
        """Extract constraints and modifiers from text"""
        constraints = {}
        
        # Speed constraints
        if 'quickly' in text or 'fast' in text:
            constraints['speed'] = 'high'
        elif 'slowly' in text or 'carefully' in text:
            constraints['speed'] = 'low'
        
        # Safety constraints
        if 'carefully' in text or 'gently' in text:
            constraints['safety_mode'] = 'enhanced'
        
        return constraints
    
    def _assess_complexity(
        self, 
        text: str, 
        action: str, 
        entities: Dict[str, Any]
    ) -> IntentComplexity:
        """Assess the complexity level of the intent"""
        # Check for conjunctions indicating composite intent
        conjunctions = ['and', 'then', 'after', 'before', 'while']
        has_conjunction = any(c in text for c in conjunctions)
        
        # Check for ambiguity markers
        ambiguity_markers = ['maybe', 'perhaps', 'might', 'somewhere', 'somehow']
        has_ambiguity = any(a in text for a in ambiguity_markers)
        
        if has_ambiguity:
            return IntentComplexity.AMBIGUOUS
        elif has_conjunction or len(entities) > 2:
            return IntentComplexity.COMPOSITE
        else:
            return IntentComplexity.ATOMIC
    
    def _calculate_confidence(
        self, 
        action: str, 
        entities: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for parsed intent"""
        if action == 'unknown':
            return 0.0
        
        schema = self.ACTION_SCHEMAS.get(action, {})
        required = schema.get('required', [])
        
        # Check required entities
        entity_score = sum(1 for r in required if r in entities) / len(required) if required else 1.0
        
        # Base confidence
        base = 0.6
        
        return min(1.0, base + entity_score * 0.3 + (0.1 if constraints else 0))
    
    def _create_atomic_operation(self, intent: Intent) -> AtomicOperation:
        """Create atomic operation from atomic intent"""
        self._operation_counter += 1
        op_id = f"op_{self._operation_counter:04d}"
        
        schema = self.ACTION_SCHEMAS.get(intent.action, {})
        
        return AtomicOperation(
            operation_id=op_id,
            action_type=intent.action,
            parameters=intent.entities,
            safety_bounds=schema.get('safety_bounds', {})
        )
    
    def _split_composite_intent(self, intent: Intent) -> List[Intent]:
        """Split composite intent into sub-intents"""
        # Simplified splitting logic
        # In production, use proper dependency parsing
        sub_intents = []
        
        # Split by conjunctions
        parts = re.split(r'\s+(?:and|then)\s+', intent.raw_text)
        
        for part in parts:
            sub_intent = self.parse_intent(part, intent.context)
            sub_intents.append(sub_intent)
        
        return sub_intents
    
    def _create_clarification_request(self, intent: Intent) -> AtomicOperation:
        """Create operation to request clarification"""
        self._operation_counter += 1
        return AtomicOperation(
            operation_id=f"clarify_{self._operation_counter:04d}",
            action_type='request_clarification',
            parameters={
                'original_intent': intent.raw_text,
                'ambiguity_detected': True
            }
        )
    
    def _verify_entity_preservation(self, intent: Intent, operations: List[AtomicOperation]) -> float:
        """Verify that all entities from intent are preserved in operations"""
        if not intent.entities:
            return 1.0
        
        all_params = {}
        for op in operations:
            all_params.update(op.parameters)
        
        preserved = sum(1 for k in intent.entities if k in all_params)
        return preserved / len(intent.entities)
    
    def _verify_constraint_satisfaction(self, intent: Intent, operations: List[AtomicOperation]) -> float:
        """Verify that constraints are satisfied by operations"""
        if not intent.constraints:
            return 1.0
        
        # Simplified check - in production, use formal verification
        return 0.9  # Placeholder
    
    def _check_safety_bounds(self, operation: AtomicOperation) -> bool:
        """Check if operation parameters are within safety bounds"""
        for param, value in operation.parameters.items():
            if param in operation.safety_bounds:
                min_val, max_val = operation.safety_bounds[param]
                if isinstance(value, (int, float)):
                    if not min_val <= value <= max_val:
                        logger.warning(
                            f"Safety bound violation: {param}={value} "
                            f"not in [{min_val}, {max_val}]"
                        )
                        return False
        return True


# ==================== Usage Example ====================
if __name__ == "__main__":
    # Initialize compiler with safety threshold
    compiler = IntentCompiler(safety_threshold=0.75, max_decomposition_depth=3)
    
    # Example 1: Simple atomic intent
    print("\n=== Example 1: Atomic Intent ===")
    result1 = compiler.compile_and_execute(
        "Move to the kitchen quickly",
        dry_run=True
    )
    print(f"Status: {result1.status.name}")
    print(f"Operations: {result1.operations_executed}")
    print(f"Metrics: {result1.metrics}")
    
    # Example 2: Composite intent
    print("\n=== Example 2: Composite Intent ===")
    result2 = compiler.compile_and_execute(
        "Move to the kitchen and grab the apple carefully",
        dry_run=True
    )
    print(f"Status: {result2.status.name}")
    print(f"Operations: {result2.operations_executed}")
    
    # Example 3: Ambiguous intent
    print("\n=== Example 3: Ambiguous Intent ===")
    result3 = compiler.compile_and_execute(
        "Maybe go somewhere and do something",
        dry_run=True
    )
    print(f"Status: {result3.status.name}")
    print(f"Feedback: {result3.feedback}")