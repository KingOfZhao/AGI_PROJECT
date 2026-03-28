"""
Module: intent_grammar_aligner
Description: Implements an 'Intent-Grammar' aligner to convert unstructured natural language
             intents into Abstract Syntax Tree (AST) prefixes constrained by a Domain Specific
             Language (DSL). It identifies structural skeletons and validates them against
             a grammar schema.

Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
License: MIT
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

class TokenType(Enum):
    """Enumeration of recognized token types in the DSL."""
    KEYWORD = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    OPERATOR = auto()
    UNKNOWN = auto()

@dataclass
class Token:
    """Represents a lexical token."""
    type: TokenType
    value: str
    position: int

@dataclass
class ASTNode:
    """Represents a node in the Abstract Syntax Tree."""
    name: str
    children: List['ASTNode']
    value: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serializes the AST node to a dictionary format."""
        return {
            "name": self.name,
            "value": self.value,
            "children": [child.to_dict() for child in self.children]
        }

# --- Exception Handling ---

class GrammarValidationError(Exception):
    """Raised when the generated AST violates DSL constraints."""
    pass

class IntentParsingError(Exception):
    """Raised when the intent cannot be parsed into valid tokens."""
    pass

# --- Grammar Definition (Simulated DSL Schema) ---

# A simple DSL schema definition:
# Structure: COMMAND -> SUBJECT -> [PARAMETER]
DSL_GRAMMAR = {
    "ROOT": ["COMMAND"],
    "COMMAND": ["CREATE", "DELETE", "UPDATE", "QUERY"],
    "SUBJECT": ["USER", "FILE", "RECORD", "CONFIG"],
    "PARAMETER": ["STRING", "NUMBER"]
}

# Mapping Natural Language keywords to DSL Grammar Terminals
NL_TO_DSL_MAP = {
    "create": "CREATE", "make": "CREATE", "generate": "CREATE",
    "delete": "DELETE", "remove": "DELETE",
    "update": "UPDATE", "modify": "UPDATE", "change": "UPDATE",
    "query": "QUERY", "find": "QUERY", "search": "QUERY", "get": "QUERY",
    "user": "USER", "person": "USER",
    "file": "FILE", "document": "FILE",
    "record": "RECORD", "entry": "RECORD",
    "config": "CONFIG", "settings": "CONFIG"
}

# --- Core Functions ---

def tokenize_intent(intent: str) -> List[Token]:
    """
    Lexical analysis: Breaks down the natural language intent into tokens.
    
    Args:
        intent (str): The raw natural language input string.
        
    Returns:
        List[Token]: A list of Token objects.
        
    Raises:
        IntentParsingError: If the input is empty or invalid.
    """
    if not intent or not intent.strip():
        raise IntentParsingError("Input intent cannot be empty.")
    
    logger.info(f"Tokenizing intent: {intent}")
    tokens = []
    # Simple regex pattern to split by whitespace while keeping quoted strings
    # This is a heuristic alignment for the 'structure' identification.
    words = re.findall(r'[\w\.]+|"[^"]*"|\S', intent)
    
    for idx, word in enumerate(words):
        # Clean punctuation for better matching
        clean_word = word.strip(".,!?;").lower()
        
        token_type = TokenType.UNKNOWN
        mapped_value = None
        
        if clean_word in NL_TO_DSL_MAP:
            token_type = TokenType.KEYWORD
            mapped_value = NL_TO_DSL_MAP[clean_word]
        elif word.isdigit():
            token_type = TokenType.NUMBER
            mapped_value = word
        elif word.startswith('"') and word.endswith('"'):
            token_type = TokenType.STRING
            mapped_value = word
        else:
            # Treat as identifier if not keyword
            token_type = TokenType.IDENTIFIER
            mapped_value = word
            
        tokens.append(Token(type=token_type, value=mapped_value, position=idx))
        
    logger.debug(f"Generated {len(tokens)} tokens.")
    return tokens

def build_ast_from_tokens(tokens: List[Token]) -> ASTNode:
    """
    Syntactic analysis: Constructs an AST based on the DSL grammar constraints.
    
    This function attempts to fit the sequence of tokens into a valid 'Skeleton'
    defined by DSL_GRAMMAR.
    
    Args:
        tokens (List[Token]): List of tokens from the lexer.
        
    Returns:
        ASTNode: The root of the generated Abstract Syntax Tree.
        
    Raises:
        GrammarValidationError: If tokens cannot form a valid DSL structure.
    """
    logger.info("Building AST from tokens...")
    
    root = ASTNode(name="ROOT", children=[])
    
    # We expect a sequence: COMMAND -> SUBJECT -> [PARAMETERS]
    # We use a simple state machine to enforce this constraint.
    
    expected_category = "COMMAND"
    current_node = None
    
    for token in tokens:
        if token.type == TokenType.UNKNOWN:
            continue # Skip noise
            
        if expected_category == "COMMAND":
            if token.type == TokenType.KEYWORD and token.value in DSL_GRAMMAR["COMMAND"]:
                cmd_node = ASTNode(name="COMMAND", value=token.value, children=[])
                root.children.append(cmd_node)
                current_node = cmd_node
                expected_category = "SUBJECT"
                logger.debug(f"Recognized COMMAND: {token.value}")
            else:
                # Try to recover or skip if structure is not found immediately
                continue

        elif expected_category == "SUBJECT":
            if token.type == TokenType.KEYWORD and token.value in DSL_GRAMMAR["SUBJECT"]:
                subj_node = ASTNode(name="SUBJECT", value=token.value, children=[])
                if current_node:
                    current_node.children.append(subj_node)
                expected_category = "PARAMETER" # Transition to optional params
                logger.debug(f"Recognized SUBJECT: {token.value}")
                
        elif expected_category == "PARAMETER":
            if token.type in [TokenType.STRING, TokenType.NUMBER, TokenType.IDENTIFIER]:
                param_node = ASTNode(name="PARAMETER", value=token.value, children=[])
                if current_node:
                    # Find the subject node to attach params, or attach to command
                    # For simplicity, attaching to the current command context
                    current_node.children.append(param_node)
                logger.debug(f"Recognized PARAMETER: {token.value}")
    
    # Validation: Check if the skeleton is complete
    if not root.children:
        raise GrammarValidationError("Failed to identify any valid command structure.")
        
    # Check if we found a subject for the command
    command_node = root.children[0]
    has_subject = any(child.name == "SUBJECT" for child in command_node.children)
    if not has_subject:
        logger.warning("Command identified, but no valid subject found. AST may be incomplete.")
        # Depending on strictness, we might raise an error here.
        # For this skill, we allow partial matching.

    return root

# --- Helper Functions ---

def validate_and_transform(intent: str) -> Dict[str, Union[str, Dict]]:
    """
    High-level pipeline function that tokenizes intent, builds AST,
    and validates the final structure.
    
    Args:
        intent (str): Input natural language string.
        
    Returns:
        Dict: A dictionary containing the status and the serialized AST.
    """
    try:
        tokens = tokenize_intent(intent)
        ast_root = build_ast_from_tokens(tokens)
        
        # Boundary Check: Ensure AST is not empty
        if not ast_root.children:
            raise GrammarValidationError("AST generation resulted in empty tree.")
            
        return {
            "status": "SUCCESS",
            "intent": intent,
            "ast_prefix": ast_root.to_dict()
        }
    except (IntentParsingError, GrammarValidationError) as e:
        logger.error(f"Processing failed: {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "intent": intent
        }
    except Exception as e:
        logger.critical(f"Unexpected system error: {e}", exc_info=True)
        return {
            "status": "SYSTEM_ERROR",
            "error": "Internal processing error"
        }

# --- Usage Example ---

if __name__ == "__main__":
    # Example inputs
    user_intents = [
        "Create a new user named 'Admin'",
        "Delete the file 'temp.txt'",
        "Query record 12345",
        "This sentence has no valid command structure."
    ]
    
    print(f"{'='*10} Intent-Grammar Alignment System {'='*10}")
    
    for text in user_intents:
        print(f"\nInput: {text}")
        result = validate_and_transform(text)
        
        if result["status"] == "SUCCESS":
            print("-> Aligned AST:")
            import json
            print(json.dumps(result["ast_prefix"], indent=2))
        else:
            print(f"-> Error: {result['error']}")