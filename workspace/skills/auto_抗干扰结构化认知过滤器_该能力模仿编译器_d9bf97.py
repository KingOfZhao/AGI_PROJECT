"""
Module: anti_jamming_cognitive_filter
A robust cognitive filter designed to parse noisy, fragmented, or deceptive human language
by mimicking a compiler's error recovery and parsing mechanisms.
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AntiJammingFilter")

class IntentType(Enum):
    """Enumeration of possible intent types derived from the text."""
    REQUEST = "REQUEST"
    COMMITMENT = "COMMITMENT"
    INFORMATION = "INFORMATION"
    DECEPTION = "DECEPTION"
    UNKNOWN = "UNKNOWN"

@dataclass
class Token:
    """Represents a semantic token extracted from raw text."""
    type: str
    value: str
    confidence: float = 1.0

@dataclass
class IntentNode:
    """Represents a node in the Intent Tree."""
    intent_type: IntentType
    content: str
    confidence: float
    children: List['IntentNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class PragmaticLexer:
    """
    A lexer that converts raw, noisy text into semantic tokens.
    It focuses on identifying key linguistic markers (operators, delimiters).
    """
    
    # Patterns for "Pragmatic Brackets" - logical openers and closers
    PATTERNS = {
        'OPENER': re.compile(r'\b(but|however|although|if|when|suppose|imagine)\b', re.I),
        'CLOSER': re.compile(r'\b(so|therefore|thus|hence|agreed|done|deal)\b', re.I),
        'NEGATION': re.compile(r'\b(not|never|no|neither|nobody|nothing|fake|lie)\b', re.I),
        'COMMITMENT': re.compile(r'\b(will|promise|guarantee|must|shall|ensure)\b', re.I),
        'REQUEST': re.compile(r'\b(need|want|give|show|tell|help|please)\b', re.I),
        'NOISE': re.compile(r'[\*\#\@\!\?\.\,\;\:\(\)\[\]]+'), # Punctuation/Emojis as noise
        'FILLER': re.compile(r'\b(uh|um|like|you know|basically|literally)\b', re.I),
    }

    def tokenize(self, text: str) -> List[Token]:
        """
        Converts text to a stream of semantic tokens, skipping noise.
        
        Args:
            text (str): Raw input text.
            
        Returns:
            List[Token]: List of semantic tokens.
        """
        tokens = []
        if not text or not isinstance(text, str):
            logger.warning("Invalid input text received by lexer.")
            return []

        # Pre-processing: Normalize whitespace
        clean_text = ' '.join(text.split())
        
        # Scan for keywords
        processed_indices = set()
        
        for token_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(clean_text):
                start, end = match.span()
                # Simple collision handling (first match wins or overrides)
                if token_type in ['NOISE', 'FILLER']:
                    # Mark noise but don't add to token stream (filtering)
                    processed_indices.update(range(start, end))
                else:
                    tokens.append(Token(type=token_type, value=match.group()))
                    processed_indices.update(range(start, end))

        # Sort tokens by appearance order
        tokens.sort(key=lambda t: clean_text.find(t.value))
        
        logger.debug(f"Lexed {len(tokens)} semantic tokens from text.")
        return tokens

class ErrorRecoveryParser:
    """
    Parses semantic tokens into an Intent Tree, similar to how a compiler
    parses code with syntax errors. It detects unclosed logical loops (lies)
    and fragmented commitments.
    """

    def __init__(self):
        self._open_brackets = [] # Stack to track logical openers

    def parse(self, tokens: List[Token], context: Optional[Dict] = None) -> IntentNode:
        """
        Constructs the core intent tree from tokens.
        
        Args:
            tokens (List[Token]): Semantic tokens from the lexer.
            context (Optional[Dict]): Additional context (e.g., speaker history).
            
        Returns:
            IntentNode: The root of the intent tree.
        """
        if not tokens:
            return IntentNode(IntentType.UNKNOWN, "Empty or pure noise input", 0.0)

        root = IntentNode(IntentType.INFORMATION, "Root Analysis", 1.0)
        current_phrase = []
        
        for token in tokens:
            if token.type == 'OPENER':
                # Start a new logical branch
                node = IntentNode(
                    IntentType.UNKNOWN, 
                    f"Conditional context: {token.value}", 
                    0.8
                )
                root.children.append(node)
                self._open_brackets.append(node)
                
            elif token.type == 'CLOSER':
                # Close a logical branch
                if self._open_brackets:
                    closed_node = self._open_brackets.pop()
                    closed_node.intent_type = IntentType.COMMITMENT # A closed loop implies resolution
                else:
                    # Unmatched closer (e.g., "So..." without a premise)
                    root.children.append(IntentNode(IntentType.INFORMATION, "Conclusion without premise", 0.5))

            elif token.type == 'NEGATION':
                # Negation flips the value of the next or previous node
                node = IntentNode(IntentType.DECEPTION, f"Negation detected: {token.value}", 0.9)
                root.children.append(node)
                
            elif token.type == 'REQUEST':
                node = IntentNode(IntentType.REQUEST, f"Demand: {token.value}", 0.85)
                root.children.append(node)
                
            elif token.type == 'COMMITMENT':
                node = IntentNode(IntentType.COMMITMENT, f"Promise: {token.value}", 0.85)
                root.children.append(node)

        # Error Recovery: Handle unclosed logical brackets
        if self._open_brackets:
            for unclosed in self._open_brackets:
                unclosed.metadata['error'] = 'UNCLOSED_LOGIC'
                unclosed.content += " [WARNING: Logic incomplete or deflected]"
                unclosed.confidence *= 0.5 # Reduce confidence in incomplete logic
                logger.info(f"Detected unclosed logical structure: {unclosed.content}")
        
        return root

class StructuredCognitiveFilter:
    """
    Main interface for the Anti-Jamming Cognitive Filter.
    Input: Noisy text (str)
    Output: Structured Intent Tree (IntentNode)
    """
    
    def __init__(self):
        self.lexer = PragmaticLexer()
        self.parser = ErrorRecoveryParser()
        logger.info("StructuredCognitiveFilter initialized.")

    def process(self, raw_text: str) -> Dict[str, Any]:
        """
        Processes raw text to extract structured intent.
        
        Args:
            raw_text (str): Input text, potentially noisy or deceptive.
            
        Returns:
            Dict: A dictionary containing the structured analysis results.
        
        Example:
            >>> filter = StructuredCognitiveFilter()
            >>> result = filter.process("Look, um, I promise to pay, but... [static] ...never did.")
            >>> print(result['summary'])
        """
        if not isinstance(raw_text, str):
            raise ValueError("Input must be a string.")
        
        if len(raw_text) > 10000:
            logger.warning("Input text exceeds recommended length, processing might be slow.")

        # 1. Lexical Analysis (Tokenization & Noise Filtering)
        tokens = self.lexer.tokenize(raw_text)
        
        # 2. Syntactic/Semantic Parsing (Intent Tree Construction)
        intent_tree = self.parser.parse(tokens)
        
        # 3. Generate Output
        return self._format_output(intent_tree, raw_text)

    def _format_output(self, root: IntentNode, original: str) -> Dict[str, Any]:
        """Helper to format the tree into a serializable dictionary."""
        
        def tree_to_dict(node: IntentNode) -> Dict:
            return {
                "type": node.intent_type.value,
                "content": node.content,
                "confidence": node.confidence,
                "metadata": node.metadata,
                "sub_intents": [tree_to_dict(child) for child in node.children]
            }

        analysis = {
            "original_length": len(original),
            "structured_intent": tree_to_dict(root),
            "warnings": []
        }
        
        # Extract warnings from the tree recursively
        def extract_warnings(node: IntentNode):
            if "error" in node.metadata:
                analysis["warnings"].append(node.content)
            for child in node.children:
                extract_warnings(child)
                
        extract_warnings(root)
        
        return analysis

# --- Usage Example ---
if __name__ == "__main__":
    # Example of a fragmented, deceptive, or noisy input
    sample_input = (
        "I swear, #trustme, I will complete the task by tomorrow. "
        "But, you know, there are variables... [unintelligible] ... "
        "So basically, I need the resources. "
        "However, if the timeline shifts... I never actually promised."
    )

    print(f"--- Processing Input ---\n{sample_input}\n")
    
    try:
        cognitive_filter = StructuredCognitiveFilter()
        result = cognitive_filter.process(sample_input)
        
        import json
        print("--- Structured Output ---")
        print(json.dumps(result, indent=2))
        
        if result['warnings']:
            print("\n[!] Alerts:")
            for w in result['warnings']:
                print(f"- {w}")
                
    except Exception as e:
        logger.error(f"Critical failure in cognitive filter: {e}")