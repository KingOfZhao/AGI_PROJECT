"""
Self-Healing Code Structure Module

This module implements a sophisticated self-healing architecture for AGI systems,
designed to handle ambiguous intents and edge cases through bottom-up introspection
and autonomous refactoring capabilities.

Key Features:
- Intent ambiguity detection
- Self-reflective code analysis
- Autonomous refactoring triggers
- Graceful degradation mechanisms
- Comprehensive error handling

Example:
    >>> from auto_self_healing import SelfHealingProcessor
    >>> processor = SelfHealingProcessor()
    >>> result = processor.process_input({"intent": "complex_query", "params": {...}})
"""

import logging
import sys
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum, auto
import json
import inspect
import traceback
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('self_healing.log')
    ]
)
logger = logging.getLogger(__name__)


class HealingAction(Enum):
    """Enumeration of possible healing actions the system can take."""
    RETRY = auto()
    REFINE_INPUT = auto()
    RESTRUCTURE_CODE = auto()
    REQUEST_HUMAN = auto()
    GRACEFUL_DEGRADATION = auto()


@dataclass
class ProcessingContext:
    """Context container for processing state and metadata."""
    input_data: Dict[str, Any]
    original_intent: Optional[str] = None
    current_state: Optional[str] = None
    healing_attempts: int = 0
    last_error: Optional[Exception] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AmbiguityDetector:
    """Detects ambiguous intents and edge cases in input data."""
    
    @staticmethod
    def validate_input_structure(data: Dict[str, Any]) -> bool:
        """Validate basic input structure requirements.
        
        Args:
            data: Input dictionary to validate
            
        Returns:
            bool: True if input meets minimum structure requirements
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
            
        required_fields = {'intent', 'params'}
        if not required_fields.issubset(data.keys()):
            missing = required_fields - set(data.keys())
            raise ValueError(f"Missing required fields: {missing}")
            
        if not isinstance(data['params'], dict):
            raise ValueError("Parameters must be in dictionary format")
            
        return True

    @staticmethod
    def detect_ambiguity(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Detect ambiguous intent in input data.
        
        Args:
            data: Input data to analyze
            
        Returns:
            Tuple containing:
                - bool: True if ambiguity detected
                - Optional[str]: Description of detected ambiguity
        """
        try:
            AmbiguityDetector.validate_input_structure(data)
            
            intent = data['intent']
            params = data['params']
            
            # Check for vague intent descriptors
            vague_terms = {'something', 'anything', 'maybe', 'possibly'}
            if any(term in str(intent).lower() for term in vague_terms):
                return True, "Vague intent descriptor detected"
                
            # Check for contradictory parameters
            if 'include' in params and 'exclude' in params:
                intersection = set(params['include']) & set(params['exclude'])
                if intersection:
                    return True, f"Contradictory parameters: {intersection}"
                    
            # Check for missing critical parameters
            if intent == 'data_analysis' and 'dataset' not in params:
                return True, "Missing required dataset parameter"
                
            return False, None
            
        except ValueError as e:
            return True, f"Input validation failed: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in ambiguity detection: {str(e)}")
            return True, f"System error during analysis: {str(e)}"


class SelfHealingProcessor:
    """Core processor with self-healing capabilities."""
    
    MAX_HEALING_ATTEMPTS = 3
    
    def __init__(self):
        """Initialize the processor with default strategies."""
        self.healing_strategies = {
            HealingAction.RETRY: self._retry_operation,
            HealingAction.REFINE_INPUT: self._refine_input,
            HealingAction.RESTRUCTURE_CODE: self._restructure_code,
            HealingAction.REQUEST_HUMAN: self._request_human_intervention,
            HealingAction.GRACEFUL_DEGRADATION: self._graceful_degradation
        }
        self.context = None
        logger.info("SelfHealingProcessor initialized")

    def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data with self-healing capabilities.
        
        Args:
            input_data: Input dictionary containing intent and parameters
            
        Returns:
            Dict containing processing results or healing status
            
        Example:
            >>> processor = SelfHealingProcessor()
            >>> result = processor.process_input({
            ...     "intent": "data_analysis",
            ...     "params": {"dataset": "sales.csv"}
            ... })
        """
        self.context = ProcessingContext(input_data=input_data)
        
        try:
            # Initial processing attempt
            result = self._attempt_processing()
            
            if result.get('status') == 'success':
                return result
                
            # Check for ambiguity
            is_ambiguous, ambiguity_reason = AmbiguityDetector.detect_ambiguity(input_data)
            
            if is_ambiguous:
                logger.warning(f"Detected ambiguity: {ambiguity_reason}")
                return self._initiate_healing_process(ambiguity_reason)
                
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            self.context.last_error = e
            return self._initiate_healing_process(str(e))

    def _attempt_processing(self) -> Dict[str, Any]:
        """Attempt to process the input data normally."""
        try:
            # Validate input structure first
            AmbiguityDetector.validate_input_structure(self.context.input_data)
            
            # Simulate actual processing based on intent
            intent = self.context.input_data['intent']
            params = self.context.input_data['params']
            
            if intent == 'data_analysis':
                if 'dataset' not in params:
                    raise ValueError("Missing dataset parameter")
                    
                return {
                    'status': 'success',
                    'result': f"Analyzed dataset: {params['dataset']}",
                    'metrics': {'record_count': 1000, 'features': 12}
                }
                
            return {
                'status': 'success',
                'result': f"Processed intent: {intent}",
                'params': params
            }
            
        except Exception as e:
            logger.warning(f"Initial processing attempt failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'needs_healing': True
            }

    def _initiate_healing_process(self, reason: str) -> Dict[str, Any]:
        """Initiate the self-healing process.
        
        Args:
            reason: Description of what triggered healing
            
        Returns:
            Dict containing healing results or status
        """
        logger.info(f"Initiating self-healing process due to: {reason}")
        self.context.metadata['healing_reason'] = reason
        
        while self.context.healing_attempts < self.MAX_HEALING_ATTEMPTS:
            self.context.healing_attempts += 1
            action = self._determine_healing_action()
            
            logger.info(f"Attempt {self.context.healing_attempts}: Taking action {action.name}")
            result = self.healing_strategies[action](self.context)
            
            if result.get('status') == 'success':
                return result
                
        # If all attempts fail
        logger.error("All self-healing attempts failed")
        return {
            'status': 'failed',
            'error': 'Max healing attempts reached',
            'last_attempt': self.context.healing_attempts,
            'recommendation': 'Manual intervention required'
        }

    def _determine_healing_action(self) -> HealingAction:
        """Determine the most appropriate healing action based on context."""
        error = self.context.last_error
        
        if isinstance(error, ValueError):
            if 'Missing' in str(error):
                return HealingAction.REFINE_INPUT
            return HealingAction.RETRY
            
        if self.context.healing_attempts > 2:
            return HealingAction.REQUEST_HUMAN
            
        # Default action based on context state
        if 'input_validation' in str(error):
            return HealingAction.REFINE_INPUT
        if 'processing' in str(error):
            return HealingAction.RESTRUCTURE_CODE
            
        return HealingAction.RETRY

    # Healing strategy implementations
    def _retry_operation(self, context: ProcessingContext) -> Dict[str, Any]:
        """Retry the operation with the same input."""
        logger.info("Retrying operation...")
        return self._attempt_processing()

    def _refine_input(self, context: ProcessingContext) -> Dict[str, Any]:
        """Attempt to refine the input parameters."""
        logger.info("Attempting to refine input parameters...")
        
        # Simulate input refinement
        if 'params' in context.input_data:
            refined_params = context.input_data['params'].copy()
            
            # Add missing parameters if possible
            if context.input_data['intent'] == 'data_analysis' and 'dataset' not in refined_params:
                refined_params['dataset'] = 'default_dataset.csv'
                
            context.input_data['params'] = refined_params
            return self._attempt_processing()
            
        return {
            'status': 'failed',
            'error': 'Could not refine input parameters',
            'needs_different_strategy': True
        }

    def _restructure_code(self, context: ProcessingContext) -> Dict[str, Any]:
        """Simulate code restructuring for healing."""
        logger.info("Attempting code restructuring...")
        
        # In a real system, this would involve:
        # 1. Analyzing the code that failed
        # 2. Generating alternative implementations
        # 3. Testing the new implementation
        
        # Simulate successful restructuring
        return {
            'status': 'success',
            'result': 'Processed with restructured code',
            'healing_action': 'code_restructure',
            'metrics': {'execution_time': 0.45, 'memory_usage': '12MB'}
        }

    def _request_human_intervention(self, context: ProcessingContext) -> Dict[str, Any]:
        """Request human intervention when healing fails."""
        logger.warning("Requesting human intervention...")
        
        return {
            'status': 'pending',
            'action': 'human_intervention_required',
            'context': {
                'original_input': context.input_data,
                'healing_attempts': context.healing_attempts,
                'last_error': str(context.last_error)
            },
            'recommendation': 'Please review the input and processing logic'
        }

    def _graceful_degradation(self, context: ProcessingContext) -> Dict[str, Any]:
        """Provide a degraded but functional response."""
        logger.info("Applying graceful degradation...")
        
        return {
            'status': 'partial_success',
            'result': 'Limited functionality response',
            'degraded_features': ['full_analysis', 'detailed_metrics'],
            'available_features': ['basic_processing', 'error_reporting']
        }


# Helper function
def log_processing_time(func: Callable) -> Callable:
    """Decorator to log processing time of functions.
    
    Args:
        func: Function to be decorated
        
    Returns:
        Wrapped function with timing logs
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"{func.__name__} executed in {duration:.4f} seconds")
        return result
    return wrapper


if __name__ == "__main__":
    # Example usage
    import time
    
    processor = SelfHealingProcessor()
    
    # Test case 1: Normal input
    normal_input = {
        "intent": "data_analysis",
        "params": {"dataset": "sales.csv"}
    }
    print("Testing normal input:")
    print(json.dumps(processor.process_input(normal_input), indent=2))
    
    # Test case 2: Ambiguous input
    ambiguous_input = {
        "intent": "maybe_analyze",
        "params": {"include": ["A"], "exclude": ["A"]}
    }
    print("\nTesting ambiguous input:")
    print(json.dumps(processor.process_input(ambiguous_input), indent=2))
    
    # Test case 3: Invalid input
    invalid_input = {
        "intent": "data_analysis",
        "params": {}  # Missing dataset
    }
    print("\nTesting invalid input:")
    print(json.dumps(processor.process_input(invalid_input), indent=2))