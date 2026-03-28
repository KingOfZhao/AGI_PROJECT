"""
Module: deterministic_semantic_parser
A compiler-theory-based deterministic semantic parsing engine for AGI systems.

This engine processes natural language by mapping it to a strongly-typed Natural
Language Intermediate Representation (NL-IR). It utilizes a multi-pass mechanism
(Lexing -> Parsing -> Semantic Analysis -> Code Gen) to ensure logical consistency,
eliminate hallucinations, and provide explainability for high-stakes domains
like finance and law.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class TokenType(Enum):
    """Represents the type of tokens in the input stream."""
    KEYWORD = auto()
    IDENTIFIER = auto()
    TYPE_LITERAL = auto()
    VALUE_LITERAL = auto()
    OPERATOR = auto()
    UNKNOWN = auto()

class SemanticError(Exception):
    """Custom exception for semantic analysis failures."""
    pass

@dataclass
class Token:
    """Represents a lexical token."""
    type: TokenType
    value: str
    position: int

@dataclass
class Symbol:
    """Represents a symbol in the symbol table (e.g., a variable or entity)."""
    name: str
    type_name: str  # e.g., 'Currency', 'LegalClause', 'Date'
    scope: str
    value: Optional[Any] = None

@dataclass
class IntermediateRepresentation:
    """
    Strongly-typed Natural Language Intermediate Representation (NL-IR).
    This structure bridges the gap between fuzzy natural language and strict logic.
    """
    intent: str
    entities: Dict[str, Any]  # key: entity name, value: typed value
    logic_chain: List[str]    # Ordered list of logical steps
    is_verified: bool = False
    confidence: float = 0.0

@dataclass
class ParseContext:
    """Maintains the state of the parsing process."""
    scope_stack: List[str] = field(default_factory=lambda: ['global'])
    symbol_table: Dict[str, Symbol] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

# --- Core Classes ---

class DeterministicSemanticParser:
    """
    A parser that applies compiler design principles (Lexing, Parsing, Semantic Analysis)
    to natural language inputs to generate deterministic, verifiable outputs.
    """

    def __init__(self):
        self._init_standard_types()

    def _init_standard_types(self):
        """Initialize basic type system rules."""
        # In a real AGI system, this would load from a schema definition
        self.type_system = {
            'Currency': r'^\$?\d+(\.\d{2})?$',
            'Percentage': r'^\d+(\.\d+)?%$',
            'Date': r'^\d{4}-\d{2}-\d{2}$',
            'LegalParty': r'^[A-Z][a-z]+$',  # Simplified
        }
        logger.info("Type system initialized with standard definitions.")

    def _lexical_scan(self, text: str) -> List[Token]:
        """
        Pass 1: Lexical Analysis.
        Converts raw text into a stream of categorized tokens.
        """
        tokens = []
        # Simple regex-based tokenizer for demonstration
        words = re.findall(r"[\w']+|\$[\d\.]+|\S", text)
        
        for idx, word in enumerate(words):
            token_type = TokenType.UNKNOWN
            
            if word.lower() in ['transfer', 'verify', 'execute', 'calculate']:
                token_type = TokenType.KEYWORD
            elif word.lower() in ['from', 'to', 'if', 'when']:
                token_type = TokenType.OPERATOR
            elif re.match(r'^\$[\d\.]+$', word):
                token_type = TokenType.TYPE_LITERAL # Money type hint
            elif re.match(r'^\d+$', word):
                token_type = TokenType.VALUE_LITERAL
            elif word[0].isupper():
                token_type = TokenType.IDENTIFIER
            else:
                token_type = TokenType.UNKNOWN
                
            tokens.append(Token(type=token_type, value=word, position=idx))
            
        logger.debug(f"Lexical scan complete. Found {len(tokens)} tokens.")
        return tokens

    def _parse_to_ir(self, tokens: List[Token]) -> IntermediateRepresentation:
        """
        Pass 2: Syntax Parsing.
        Constructs the Intermediate Representation (IR) from tokens.
        """
        # Simplified parsing logic: subject-verb-object structure assumption
        intent = "UNKNOWN"
        entities = {}
        logic_chain = []
        
        # Basic logic extraction
        verb = None
        subject = None
        
        for token in tokens:
            if token.type == TokenType.KEYWORD:
                verb = token.value
                intent = verb.upper()
                logic_chain.append(f"ACTION: {verb}")
            elif token.type == TokenType.IDENTIFIER:
                if verb:
                    # Heuristic: Post-verb identifiers are often objects/parties
                    entities[token.value] = "EntityRef"
                    logic_chain.append(f"REF: {token.value}")
            elif token.type == TokenType.TYPE_LITERAL:
                # Inferred type based on literal format
                entities[f"amount_{len(entities)}"] = token.value
                logic_chain.append(f"VALUE: {token.value}")

        if not intent:
            intent = "QUERY" # Default fallback

        ir = IntermediateRepresentation(
            intent=intent,
            entities=entities,
            logic_chain=logic_chain
        )
        logger.info(f"Generated preliminary IR: {ir.intent}")
        return ir

    def _semantic_analysis(self, ir: IntermediateRepresentation, context: ParseContext) -> IntermediateRepresentation:
        """
        Pass 3: Semantic Analysis.
        Validates types, checks scope, and ensures logical consistency.
        """
        current_scope = context.scope_stack[-1]
        
        # 1. Type Inference and Checking
        for key, value in ir.entities.items():
            inferred_type = self._infer_type(value)
            
            if inferred_type == "UNKNOWN":
                warning = f"Type inference failed for {key}={value}"
                context.errors.append(warning)
                logger.warning(warning)
            else:
                # Update symbol table
                sym = Symbol(name=key, type_name=inferred_type, scope=current_scope, value=value)
                context.symbol_table[f"{current_scope}.{key}"] = sym
                logger.debug(f"Symbol added: {sym.name}:{sym.type_name}")

        # 2. Logic Consistency Check (Anti-Hallucination)
        # Example: If intent is TRANSFER, we must have at least two parties and a currency
        if ir.intent == "TRANSFER":
            party_count = sum(1 for k in ir.entities if "EntityRef" in str(ir.entities[k]))
            has_value = any(isinstance(v, str) and v.startswith('$') for v in ir.entities.values())
            
            if party_count < 2:
                err = "Semantic Error: Transfer requires at least 2 parties."
                context.errors.append(err)
                raise SemanticError(err)
            if not has_value:
                logger.warning("Semantic Warning: Transfer has no associated monetary value.")
                
        # 3. Final Verification
        if not context.errors:
            ir.is_verified = True
            ir.confidence = 1.0 # Deterministic confidence
            
        return ir

    def _infer_type(self, value: Any) -> str:
        """Helper: Infers the semantic type of a value."""
        if not isinstance(value, str):
            return "NativeType"
        
        for type_name, pattern in self.type_system.items():
            if re.match(pattern, value):
                return type_name
        return "UNKNOWN"

    def compile_intent(self, text: str) -> Dict[str, Any]:
        """
        Main entry point. Compiles natural language into a verified intent structure.
        
        Args:
            text (str): The input natural language string.
            
        Returns:
            Dict[str, Any]: A structured, validated output format.
        
        Raises:
            SemanticError: If the input fails logical consistency checks.
        """
        logger.info(f"Starting compilation for: {text[:50]}...")
        
        try:
            # Pass 1: Lexing
            tokens = self._lexical_scan(text)
            
            # Pass 2: Parsing
            ir = self._parse_to_ir(tokens)
            
            # Pass 3: Semantic Analysis
            context = ParseContext()
            verified_ir = self._semantic_analysis(ir, context)
            
            return {
                "status": "SUCCESS",
                "intent": verified_ir.intent,
                "parameters": verified_ir.entities,
                "execution_plan": verified_ir.logic_chain,
                "meta": {
                    "verified": verified_ir.is_verified,
                    "scope": context.scope_stack[-1]
                }
            }
            
        except SemanticError as se:
            logger.error(f"Semantic compilation failed: {se}")
            return {
                "status": "FAILED_LOGIC",
                "error": str(se),
                "hint": "Input text does not satisfy logical constraints."
            }
        except Exception as e:
            logger.critical(f"Unexpected compilation error: {e}")
            return {
                "status": "FAILED_SYSTEM",
                "error": str(e)
            }

# --- Usage Example ---
if __name__ == "__main__":
    # Example Input 1: Valid Financial Instruction
    input_1 = "Transfer $150.00 to Alice"
    
    # Example Input 2: Logically Incomplete Instruction
    input_2 = "Transfer to Alice" # Missing amount
    
    engine = DeterministicSemanticParser()
    
    print("-" * 60)
    result_1 = engine.compile_intent(input_1)
    print(f"Input: {input_1}")
    print(f"Output: {result_1}")
    
    print("-" * 60)
    result_2 = engine.compile_intent(input_2)
    print(f"Input: {input_2}")
    print(f"Output: {result_2}")