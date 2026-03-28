"""
Skill Quantization Compiler Module
==================================
An advanced intent-parameter alignment engine that translates ambiguous human expert
knowledge into precise machine-executable instructions using LLM capabilities.

Features:
- Intent parsing and parameter extraction
- Experience language quantization
- Real-time script generation
- Multi-domain adaptation

Author: AGI System
Version: 1.0.0
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstructionDomain(Enum):
    """Enumeration of supported instruction domains."""
    COOKING = "cooking"
    CRAFTSMANSHIP = "craftsmanship"
    MANUFACTURING = "manufacturing"
    MEDICAL = "medical"
    GENERAL = "general"


class InstructionComplexity(Enum):
    """Enumeration of instruction complexity levels."""
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    EXPERT = 4


@dataclass
class QuantizedInstruction:
    """Data class representing a compiled instruction."""
    code: str
    parameters: Dict[str, Union[float, str, int, bool]]
    confidence: float
    domain: InstructionDomain
    complexity: InstructionComplexity
    timestamp: str
    source_text: str


class BaseLLMAdapter(ABC):
    """Abstract base class for LLM adapters."""
    
    @abstractmethod
    def generate_completion(self, prompt: str) -> str:
        """Generate completion from LLM."""
        pass


class MockLLMAdapter(BaseLLMAdapter):
    """Mock LLM adapter for demonstration purposes."""
    
    def generate_completion(self, prompt: str) -> str:
        """Simulate LLM response generation."""
        logger.debug(f"Generating completion for prompt: {prompt[:100]}...")
        return json.dumps({
            "intent": "add_ingredient",
            "parameters": {
                "ingredient": "salt",
                "quantity": 5.0,
                "unit": "grams"
            },
            "confidence": 0.85
        })


class SkillQuantizationCompiler:
    """
    Main compiler class for translating human expert language into
    precise machine-executable instructions.
    """
    
    # Domain-specific parameter patterns
    PARAMETER_PATTERNS = {
        'quantity': r'(\d+(?:\.\d+)?)\s*(grams?|g|ml|milliliters?|teaspoons?|tablespoons?|cups?)',
        'temperature': r'(\d+(?:\.\d+)?)\s*(°[CF]|degrees?|celsius|fahrenheit)',
        'time': r'(\d+(?:\.\d+)?)\s*(seconds?|sec|minutes?|min|hours?|hr|h)',
        'speed': r'(low|medium|high|fast|slow)',
        'intensity': r'(gentle|moderate|strong|light|heavy)'
    }
    
    # Ambiguous term mappings
    AMBIGUOUS_TERMS = {
        'pinch': {'quantity': 0.5, 'unit': 'grams', 'confidence': 0.6},
        'dash': {'quantity': 1.0, 'unit': 'ml', 'confidence': 0.55},
        'handful': {'quantity': 30.0, 'unit': 'grams', 'confidence': 0.5},
        'splash': {'quantity': 15.0, 'unit': 'ml', 'confidence': 0.5},
        'drizzle': {'quantity': 10.0, 'unit': 'ml', 'confidence': 0.6},
        'touch': {'quantity': 0.2, 'unit': 'grams', 'confidence': 0.55},
        'bit': {'quantity': 2.0, 'unit': 'grams', 'confidence': 0.5},
        'some': {'quantity': 5.0, 'unit': 'grams', 'confidence': 0.45}
    }
    
    def __init__(
        self,
        llm_adapter: Optional[BaseLLMAdapter] = None,
        domain: InstructionDomain = InstructionDomain.GENERAL,
        strict_validation: bool = True
    ):
        """
        Initialize the SkillQuantizationCompiler.
        
        Args:
            llm_adapter: LLM adapter for intent parsing (uses MockLLMAdapter if None)
            domain: Primary domain for instruction compilation
            strict_validation: Enable strict parameter validation
        """
        self.llm_adapter = llm_adapter or MockLLMAdapter()
        self.domain = domain
        self.strict_validation = strict_validation
        self._instruction_history: List[QuantizedInstruction] = []
        
        logger.info(
            f"Initialized SkillQuantizationCompiler for domain: {domain.value}"
        )
    
    def _validate_parameters(
        self,
        parameters: Dict[str, Union[float, str, int, bool]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate extracted parameters against domain constraints.
        
        Args:
            parameters: Dictionary of parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not parameters:
            return False, "Empty parameters dictionary"
        
        # Check for required keys based on domain
        if self.domain == InstructionDomain.COOKING:
            if 'quantity' in parameters:
                try:
                    qty = float(parameters.get('quantity', 0))
                    if qty <= 0 or qty > 10000:
                        return False, f"Quantity {qty} out of valid range (0-10000)"
                except (ValueError, TypeError):
                    return False, "Invalid quantity format"
        
        # Check confidence bounds
        if 'confidence' in parameters:
            conf = parameters.get('confidence', 0)
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                return False, f"Invalid confidence value: {conf}"
        
        return True, None
    
    def _extract_numeric_parameters(
        self,
        text: str
    ) -> Dict[str, Union[float, str]]:
        """
        Extract numeric parameters from text using regex patterns.
        
        Args:
            text: Input text containing parameters
            
        Returns:
            Dictionary of extracted parameters
        """
        extracted = {}
        
        for param_type, pattern in self.PARAMETER_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        extracted[param_type] = float(groups[0])
                        extracted[f'{param_type}_unit'] = groups[1].lower()
                    except (ValueError, IndexError):
                        continue
                elif len(groups) == 1:
                    try:
                        extracted[param_type] = float(groups[0])
                    except ValueError:
                        continue
        
        return extracted
    
    def _resolve_ambiguous_terms(
        self,
        text: str
    ) -> Dict[str, Union[float, str, Dict]]:
        """
        Resolve ambiguous qualitative terms to quantitative values.
        
        Args:
            text: Input text containing ambiguous terms
            
        Returns:
            Dictionary of resolved terms with confidence scores
        """
        resolved = {}
        text_lower = text.lower()
        
        for term, mapping in self.AMBIGUOUS_TERMS.items():
            if term in text_lower:
                resolved[term] = {
                    'quantity': mapping['quantity'],
                    'unit': mapping['unit'],
                    'confidence': mapping['confidence']
                }
                logger.debug(f"Resolved ambiguous term '{term}': {resolved[term]}")
        
        return resolved
    
    def _calculate_complexity(
        self,
        parameters: Dict,
        ambiguous_count: int
    ) -> InstructionComplexity:
        """
        Calculate instruction complexity based on parameters and ambiguity.
        
        Args:
            parameters: Extracted parameters
            ambiguous_count: Number of ambiguous terms found
            
        Returns:
            InstructionComplexity level
        """
        score = 0
        
        # Factor in parameter count
        score += min(len(parameters) // 2, 3)
        
        # Factor in ambiguous terms
        score += min(ambiguous_count, 2)
        
        # Map score to complexity
        if score <= 1:
            return InstructionComplexity.SIMPLE
        elif score <= 3:
            return InstructionComplexity.MODERATE
        elif score <= 5:
            return InstructionComplexity.COMPLEX
        else:
            return InstructionComplexity.EXPERT
    
    def _generate_executable_code(
        self,
        intent: str,
        parameters: Dict[str, Union[float, str, int, bool]]
    ) -> str:
        """
        Generate executable code from intent and parameters.
        
        Args:
            intent: Parsed intent
            parameters: Quantized parameters
            
        Returns:
            Executable code string
        """
        # Generate Python-like executable code
        code_lines = [
            "# Auto-generated instruction script",
            f"# Generated at: {datetime.now().isoformat()}",
            f"# Domain: {self.domain.value}",
            "",
            f"def execute_instruction():",
            f'    """Execute {intent} operation."""',
        ]
        
        # Add parameter initialization
        for key, value in parameters.items():
            if isinstance(value, str):
                code_lines.append(f'    {key} = "{value}"')
            elif isinstance(value, bool):
                code_lines.append(f'    {key} = {value}')
            else:
                code_lines.append(f'    {key} = {value}')
        
        # Add operation logic based on domain
        if self.domain == InstructionDomain.COOKING:
            code_lines.extend([
                "",
                f"    # Execute {intent}",
                f"    print(f'Executing: {intent}')",
                f"    if 'quantity' in locals() and 'ingredient' in locals():",
                f"        print(f'Adding {{quantity}} {{unit}} of {{ingredient}}')",
                f"    return True"
            ])
        else:
            code_lines.extend([
                "",
                f"    # Execute {intent}",
                f"    print(f'Executing: {intent}')",
                f"    return True"
            ])
        
        return "\n".join(code_lines)
    
    def compile_instruction(
        self,
        natural_language: str,
        context: Optional[Dict] = None
    ) -> QuantizedInstruction:
        """
        Main method to compile natural language into executable instruction.
        
        This is the primary interface for converting human expert language
        into precise machine instructions.
        
        Args:
            natural_language: Input text from human expert
            context: Optional context dictionary for disambiguation
            
        Returns:
            QuantizedInstruction object with executable code
            
        Raises:
            ValueError: If input validation fails
            RuntimeError: If compilation fails
        """
        # Input validation
        if not natural_language or not isinstance(natural_language, str):
            raise ValueError("Input must be a non-empty string")
        
        if len(natural_language) > 10000:
            raise ValueError("Input exceeds maximum length of 10000 characters")
        
        logger.info(f"Compiling instruction: {natural_language[:50]}...")
        
        try:
            # Step 1: Extract numeric parameters
            numeric_params = self._extract_numeric_parameters(natural_language)
            
            # Step 2: Resolve ambiguous terms
            ambiguous_resolved = self._resolve_ambiguous_terms(natural_language)
            
            # Step 3: Merge parameters with preference to numeric values
            all_parameters: Dict[str, Union[float, str, int, bool]] = {}
            all_parameters.update(numeric_params)
            
            # Add resolved ambiguous terms with reduced confidence
            for term, values in ambiguous_resolved.items():
                if 'quantity' not in all_parameters:
                    all_parameters['quantity'] = values['quantity']
                    all_parameters['unit'] = values['unit']
                    all_parameters['confidence'] = values['confidence']
            
            # Step 4: Use LLM for intent parsing
            llm_response = self.llm_adapter.generate_completion(natural_language)
            try:
                llm_data = json.loads(llm_response)
                intent = llm_data.get('intent', 'unknown')
                if 'parameters' in llm_data:
                    all_parameters.update(llm_data['parameters'])
            except json.JSONDecodeError:
                intent = "generic_operation"
                logger.warning("Failed to parse LLM response as JSON")
            
            # Step 5: Validate parameters
            is_valid, error_msg = self._validate_parameters(all_parameters)
            if not is_valid and self.strict_validation:
                raise RuntimeError(f"Parameter validation failed: {error_msg}")
            elif not is_valid:
                logger.warning(f"Parameter validation warning: {error_msg}")
            
            # Step 6: Calculate complexity
            complexity = self._calculate_complexity(
                all_parameters,
                len(ambiguous_resolved)
            )
            
            # Step 7: Generate executable code
            code = self._generate_executable_code(intent, all_parameters)
            
            # Calculate overall confidence
            confidence = all_parameters.get('confidence', 0.75)
            if ambiguous_resolved:
                confidence *= 0.9  # Reduce confidence for ambiguous terms
            
            # Create instruction object
            instruction = QuantizedInstruction(
                code=code,
                parameters=all_parameters,
                confidence=min(confidence, 1.0),
                domain=self.domain,
                complexity=complexity,
                timestamp=datetime.now().isoformat(),
                source_text=natural_language
            )
            
            # Store in history
            self._instruction_history.append(instruction)
            
            logger.info(
                f"Successfully compiled instruction with confidence: {confidence:.2f}"
            )
            
            return instruction
            
        except Exception as e:
            logger.error(f"Compilation failed: {str(e)}")
            raise RuntimeError(f"Instruction compilation failed: {str(e)}")
    
    def batch_compile(
        self,
        instructions: List[str],
        stop_on_error: bool = False
    ) -> List[QuantizedInstruction]:
        """
        Compile multiple instructions in batch mode.
        
        Args:
            instructions: List of natural language instructions
            stop_on_error: Whether to stop on first error
            
        Returns:
            List of compiled QuantizedInstruction objects
        """
        results = []
        
        for idx, instruction in enumerate(instructions):
            try:
                compiled = self.compile_instruction(instruction)
                results.append(compiled)
            except Exception as e:
                logger.error(f"Batch compilation error at index {idx}: {e}")
                if stop_on_error:
                    break
        
        return results
    
    def get_compilation_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve compilation history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of instruction dictionaries
        """
        history = [
            {
                'code': inst.code,
                'parameters': inst.parameters,
                'confidence': inst.confidence,
                'domain': inst.domain.value,
                'complexity': inst.complexity.name,
                'timestamp': inst.timestamp,
                'source': inst.source_text[:100] + '...' if len(inst.source_text) > 100 else inst.source_text
            }
            for inst in self._instruction_history
        ]
        
        if limit:
            return history[-limit:]
        return history


# Usage Example
if __name__ == "__main__":
    # Example 1: Basic cooking instruction
    print("=" * 60)
    print("Example 1: Cooking Domain")
    print("=" * 60)
    
    compiler = SkillQuantizationCompiler(
        domain=InstructionDomain.COOKING,
        strict_validation=False
    )
    
    # Compile a vague cooking instruction
    instruction1 = compiler.compile_instruction(
        "Add a pinch of salt and drizzle some olive oil, "
        "then cook at medium heat for about 5 minutes"
    )
    
    print(f"\nSource: {instruction1.source_text}")
    print(f"Confidence: {instruction1.confidence:.2f}")
    print(f"Complexity: {instruction1.complexity.name}")
    print(f"Parameters: {json.dumps(instruction1.parameters, indent=2)}")
    print(f"\nGenerated Code:\n{instruction1.code}")
    
    # Example 2: Batch compilation
    print("\n" + "=" * 60)
    print("Example 2: Batch Compilation")
    print("=" * 60)
    
    instructions = [
        "Stir gently for 30 seconds",
        "Add 2 cups of flour",
        "Heat to 180 degrees celsius"
    ]
    
    batch_results = compiler.batch_compile(instructions)
    
    for i, result in enumerate(batch_results, 1):
        print(f"\nInstruction {i}: {result.source_text}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Parameters: {result.parameters}")
    
    # Example 3: View compilation history
    print("\n" + "=" * 60)
    print("Example 3: Compilation History")
    print("=" * 60)
    
    history = compiler.get_compilation_history(limit=3)
    print(f"Total compilations: {len(history)}")
    for record in history:
        print(f"  - [{record['domain']}] {record['source'][:40]}... "
              f"(confidence: {record['confidence']:.2f})")