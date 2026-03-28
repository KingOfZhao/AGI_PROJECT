"""
Embodied Context Toolchain Engine (ECTE)

This module implements a context-aware engine designed for AGI systems.
It bridges natural language instructions with executable API calls by
maintaining a 'Context Stack' and mapping linguistic primitives (pronouns, verbs)
to data objects and API methods respectively.

Key Concepts:
1. Data Flow Ports: Pronouns (e.g., 'it', 'this') are resolved to objects in the context stack.
2. API Probes: Verbs (e.g., 'brighten', 'rotate') are mapped to available API methods.
3. Just-In-Time Learning: The system ingests API documentation to understand capabilities.

Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ECT_Engine")

@dataclass
class ContextEntry:
    """Represents an entry in the context stack."""
    identifier: str
    object_type: str
    data: Any
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class APICapability:
    """Represents an available API method."""
    method_name: str
    description: str
    target_type: str
    keywords: List[str]
    executor: Callable

class EmbodiedContextEngine:
    """
    The core engine managing the context stack and API mapping.
    
    Attributes:
        context_stack (List[ContextEntry]): A LIFO stack storing recent objects/references.
        api_library (Dict[str, APICapability]): A library of available skills/APIs.
    """

    def __init__(self):
        self.context_stack: List[ContextEntry] = []
        self.api_library: Dict[str, APICapability] = {}
        logger.info("Embodied Context Toolchain Engine initialized.")

    def ingest_api_documentation(self, api_docs: List[Dict[str, Any]]) -> None:
        """
        Ingests API definitions to update the capability library.
        This represents the 'Just-In-Time' learning of capabilities.
        
        Args:
            api_docs (List[Dict]): List of API definitions containing name, 
                                   target type, keywords, and function reference.
        """
        if not isinstance(api_docs, list):
            logger.error("Invalid API documentation format.")
            raise ValueError("API documentation must be a list of dictionaries.")

        count = 0
        for doc in api_docs:
            try:
                capability = APICapability(
                    method_name=doc['name'],
                    description=doc.get('description', ''),
                    target_type=doc['target_type'],
                    keywords=doc.get('keywords', []),
                    executor=doc['executor']
                )
                self.api_library[doc['name']] = capability
                count += 1
            except KeyError as e:
                logger.warning(f"Skipping invalid API doc entry: missing key {e}")
            except Exception as e:
                logger.error(f"Error processing API doc: {e}")
        
        logger.info(f"Successfully ingested {count} new API capabilities.")

    def push_context(self, identifier: str, obj: Any, obj_type: str) -> None:
        """
        Pushes a new object onto the context stack.
        
        Args:
            identifier: Name or ID of the object (e.g., 'image_1').
            obj: The actual data object.
            obj_type: The type class of the object (e.g., 'Image').
        """
        if not identifier or not obj_type:
            raise ValueError("Identifier and object type cannot be empty.")
        
        entry = ContextEntry(identifier=identifier, object_type=obj_type, data=obj)
        self.context_stack.append(entry)
        # Maintain stack limit (e.g., keep last 10 contexts)
        if len(self.context_stack) > 10:
            self.context_stack.pop(0)
        
        logger.debug(f"Context pushed: {identifier} ({obj_type})")

    def _resolve_pronoun(self, pronoun: str) -> Optional[ContextEntry]:
        """
        Helper function to resolve pronouns to the most recent matching context.
        (Simulates 'Data Flow Port' connection)
        
        Args:
            pronoun: The pronoun used (e.g., '它', 'this', 'it').
            
        Returns:
            The most recent ContextEntry or None.
        """
        # Simple logic: Return the top of the stack for generic pronouns
        # In advanced version, this would check gender/number agreement
        if not self.context_stack:
            logger.warning("Context stack is empty, cannot resolve pronoun.")
            return None
            
        logger.info(f"Resolved pronoun '{pronoun}' to recent context.")
        return self.context_stack[-1]

    def _find_api_probe(self, verb: str, target_type: str) -> Optional[APICapability]:
        """
        Helper function to find an API method based on a verb and target type.
        (Simulates 'API Probe' matching)
        
        Args:
            verb: The action verb (e.g., 'brighten', 'change').
            target_type: The type of the target object.
            
        Returns:
            Matching APICapability or None.
        """
        candidates = []
        
        for cap in self.api_library.values():
            if cap.target_type == target_type:
                # Check if verb matches keywords or method name
                if verb.lower() in [k.lower() for k in cap.keywords] or \
                   verb.lower() in cap.method_name.lower():
                    candidates.append(cap)
        
        if not candidates:
            return None
            
        # Return the first match (simple heuristic)
        return candidates[0]

    def execute_natural_command(self, text: str, params: Optional[Dict] = None) -> Any:
        """
        Core Function: Parses natural language, resolves context, and executes API.
        
        Args:
            text: Natural language command (e.g., "Make it brighter").
            params: Optional parameters for the execution.
            
        Returns:
            The result of the executed function.
            
        Raises:
            ValueError: If context or API cannot be resolved.
        """
        logger.info(f"Processing command: '{text}'")
        
        # 1. Linguistic Parsing (Simulated)
        # In a real AGI, this uses NLP models. Here we use regex/heuristics.
        pronoun_match = re.search(r"\b(it|this|它|这个)\b", text, re.IGNORECASE)
        # Extract verb (very naive extraction for demo)
        # Assuming the verb is the first word or specific action word
        words = text.replace("it", "").replace("this", "").strip().split()
        verb = words[0] if words else "unknown"

        # 2. Context Resolution (Anchor 'Data Flow Port')
        if not pronoun_match:
            raise ValueError("No pronoun found to anchor context.")
            
        context_entry = self._resolve_pronoun(pronoun_match.group(0))
        if not context_entry:
            raise ValueError("Context lost. No object found for reference.")
            
        target_obj = context_entry.data
        target_type = context_entry.object_type

        # 3. API Resolution (Anchor 'API Probe')
        capability = self._find_api_probe(verb, target_type)
        if not capability:
            raise ValueError(f"No capability found for action '{verb}' on type '{target_type}'")

        # 4. Execution
        logger.info(f"Executing: {capability.method_name} on {context_entry.identifier}")
        try:
            if params:
                result = capability.executor(target_obj, **params)
            else:
                result = capability.executor(target_obj)
            
            # Update context with result if it returns a modified object
            if result is not None:
                self.push_context(f"{context_entry.identifier}_modified", result, target_type)
                
            return result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            raise RuntimeError(f"API Execution Error: {e}")

# --- Mock Objects for Demonstration ---

class MockImage:
    def __init__(self, name, brightness=50):
        self.name = name
        self.brightness = brightness
        self.state = "original"

    def __repr__(self):
        return f"<Image '{self.name}' | Brightness: {self.brightness}>"

# --- API Definitions (Simulated External Knowledge) ---

def api_adjust_brightness(image_obj: MockImage, value: int = 10) -> MockImage:
    """Simulates an external API function."""
    image_obj.brightness += value
    image_obj.state = "modified"
    print(f"[System Call] Adjusted brightness of {image_obj.name} by {value}")
    return image_obj

def api_rotate_image(image_obj: MockImage) -> MockImage:
    """Simulates rotation."""
    print(f"[System Call] Rotating {image_obj.name}")
    return image_obj

def setup_engine() -> EmbodiedContextEngine:
    """Helper function to setup the engine with mock data."""
    engine = EmbodiedContextEngine()
    
    # Define capabilities
    docs = [
        {
            "name": "adjust_brightness",
            "target_type": "Image",
            "keywords": ["brighten", "lighten", "bright", "变亮"],
            "executor": api_adjust_brightness,
            "description": "Adjusts image brightness."
        },
        {
            "name": "rotate",
            "target_type": "Image",
            "keywords": ["rotate", "turn", "spin", "旋转"],
            "executor": api_rotate_image,
            "description": "Rotates the image."
        }
    ]
    
    engine.ingest_api_documentation(docs)
    return engine

if __name__ == "__main__":
    # 1. Initialize Engine
    engine = setup_engine()
    
    # 2. User provides an object (Simulated perception)
    current_image = MockImage("sunset.jpg")
    engine.push_context("current_image", current_image, "Image")
    
    print(f"\nInitial State: {current_image}")
    
    # 3. User issues natural language command
    # "把它变亮" (Make it brighter) -> '它' maps to current_image, '变亮' maps to adjust_brightness
    try:
        print("\nUser says: 'Make it brighter'")
        # We pass 'brighten' as verb extracted from sentence
        result = engine.execute_natural_command("brighten it", params={"value": 20})
        print(f"Result State: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. Test unknown action
    try:
        print("\nUser says: 'Delete it'")
        engine.execute_natural_command("delete it")
    except ValueError as e:
        print(f"Caught expected error: {e}")