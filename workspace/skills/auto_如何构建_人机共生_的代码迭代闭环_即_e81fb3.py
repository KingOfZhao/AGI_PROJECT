"""
Module: human_machine_symbiosis_loop
Description: Implements an AGI-level skill for building a 'Human-Machine Symbiosis' code iteration loop.

This system facilitates a cycle where AI generates code, humans modify it, and the system
analyzes the differences to extract abstract concepts, distinguish intent changes from
environment adaptations, and update a dynamic knowledge base.

Core Logic:
1.  Context Awareness: Analyzes execution environment variables.
2.  Differentiation: Uses heuristics to separate 'Environment Adapters' (e.g., path changes)
    from 'Intent Modifications' (e.g., logic changes).
3.  Abstraction: Converts specific code diffs into generalized, parameterized concepts.
4.  Consolidation: Updates the node library with new concepts or anti-patterns.

Author: Senior Python Engineer (AGI Systems)
"""

import difflib
import logging
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanMachineSymbiosis")

class ModificationType(Enum):
    """Classification of code modification types."""
    INTENT_CHANGE = "intent_change"         # Logic correction or feature addition
    ENV_ADAPTER = "environment_adapter"     # Path, API key, or OS-specific change
    NOISE = "noise"                         # Formatting or insignificant changes

@dataclass
class CodeArtifact:
    """Represents a version of the code artifact."""
    id: str
    content: str
    source: str  # 'ai', 'human', 'system'
    timestamp: float

@dataclass
class ConceptNode:
    """Represents an abstracted concept in the knowledge base."""
    id: str
    pattern: str               # Generalized regex or code snippet
    description: str
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0

class NodeLibrary:
    """
    Storage and retrieval for ConceptNodes.
    In a real AGI system, this would interface with a Vector Database.
    """
    def __init__(self):
        self._nodes: Dict[str, ConceptNode] = {}
        logger.info("NodeLibrary initialized.")

    def add_node(self, node: ConceptNode) -> None:
        """Adds or updates a concept node."""
        if node.id in self._nodes:
            self._nodes[node.id].usage_count += 1
            logger.debug(f"Updated existing node: {node.id}")
        else:
            self._nodes[node.id] = node
            logger.info(f"New concept solidified: {node.id} - {node.description}")

    def find_similar(self, pattern: str) -> Optional[ConceptNode]:
        """Finds a node matching the pattern (dummy implementation)."""
        return None

class SymbiosisEngine:
    """
    Core engine for the Human-Machine Symbiosis Loop.
    """

    def __init__(self):
        self.library = NodeLibrary()
        self._environment_tokens = [
            r'\/home\/user', r'C:\\Users', r'os\.getenv', 
            r'API_KEY', r'localhost', r'127\.0\.0\.1'
        ]
        logger.info("SymbiosisEngine ready.")

    def _validate_code(self, code: str) -> bool:
        """Basic validation to ensure code is not empty or malicious."""
        if not code or not isinstance(code, str):
            raise ValueError("Invalid code input: Must be a non-empty string.")
        # naive check for potentially harmful operations (demo purposes)
        if "rm -rf /" in code or "format c:" in code.lower():
            logger.error("Malicious code pattern detected.")
            raise ValueError("Code contains prohibited commands.")
        return True

    def _extract_diff_blocks(self, original: str, modified: str) -> List[Tuple[str, str]]:
        """
        Helper function to extract changed blocks of code.
        Returns a list of (operation, content) tuples.
        """
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            lineterm=""
        )
        blocks = []
        current_block = []
        
        for line in diff:
            if line.startswith('@@'):
                if current_block:
                    blocks.append("".join(current_block))
                    current_block = []
            elif line.startswith('+') and not line.startswith('+++'):
                current_block.append(line)
        
        if current_block:
            blocks.append("".join(current_block))
            
        return blocks

    def classify_modification(self, diff_block: str) -> ModificationType:
        """
        Core Logic: Distinguishes between Intent Modifications and Environment Adapters.
        
        Heuristics:
        1. Environment Adapter: Matches known environment regex patterns.
        2. Intent Change: Contains logic keywords (if, for, def, class) or algorithmic changes.
        3. Noise: Whitespace or comments only.
        """
        # Check for Environment Tokens
        for token in self._environment_tokens:
            if re.search(token, diff_block):
                logger.debug(f"Detected environment token: {token}")
                return ModificationType.ENV_ADAPTER

        # Check for Logic/Intent changes
        logic_keywords = ['def ', 'class ', 'if ', 'for ', 'while ', 'return ', 'import ']
        clean_diff = diff_block.strip('+').strip()
        
        if any(kw in clean_diff for kw in logic_keywords):
            return ModificationType.INTENT_CHANGE
            
        if not clean_diff.replace('\n', '').replace(' ', '').replace('#', ''):
            return ModificationType.NOISE

        # Default to Intent Change if it's significant but unclassified
        return ModificationType.INTENT_CHANGE

    def abstract_to_concept(self, diff_block: str, mod_type: ModificationType) -> Optional[ConceptNode]:
        """
        Analyzes a specific code change and attempts to create a generalized ConceptNode.
        
        Strategy:
        - Replace specific variable names/literals with placeholders.
        - Extract structural pattern.
        """
        if mod_type == ModificationType.NOISE or mod_type == ModificationType.ENV_ADAPTER:
            return None

        logger.info("Abstracting code change into new concept...")
        
        # Naive Abstraction Logic: Replace specific strings with generic placeholders
        # In production, this would use AST parsing.
        abstracted_pattern = diff_block
        # Replace specific string literals
        abstracted_pattern = re.sub(r'".*?"', '"<VALUE>"', abstracted_pattern)
        abstracted_pattern = re.sub(r"'.*?'", "'<VALUE>'", abstracted_pattern)
        # Replace specific numbers
        abstracted_pattern = re.sub(r'\b\d+\b', '<INT>', abstracted_pattern)
        
        # Create a hash ID for the pattern
        node_id = f"concept_{hash(abstracted_pattern) % 10000}"
        
        return ConceptNode(
            id=node_id,
            pattern=abstracted_pattern,
            description=f"Auto-extracted pattern: {mod_type.value}",
            tags=["auto-learned", mod_type.value]
        )

    def run_iteration_cycle(
        self, 
        ai_draft: CodeArtifact, 
        human_modified: CodeArtifact
    ) -> Dict[str, Any]:
        """
        Main entry point. Runs the full analysis cycle.
        
        Args:
            ai_draft: The original code generated by the AI.
            human_modified: The code after human intervention.
            
        Returns:
            A report dictionary containing classification results and new nodes.
        """
        try:
            self._validate_code(ai_draft.content)
            self._validate_code(human_modified.content)
            
            logger.info(f"Starting analysis cycle for Draft ID: {ai_draft.id}")
            
            diffs = self._extract_diff_blocks(ai_draft.content, human_modified.content)
            report = {
                "total_changes": len(diffs),
                "classifications": [],
                "new_concepts": []
            }
            
            for diff in diffs:
                mod_type = self.classify_modification(diff)
                
                concept = self.abstract_to_concept(diff, mod_type)
                if concept:
                    self.library.add_node(concept)
                    report["new_concepts"].append(concept.id)
                
                report["classifications"].append({
                    "type": mod_type.value,
                    "preview": diff[:50] + "..."
                })
                
            logger.info(f"Cycle complete. Solidified {len(report['new_concepts'])} new concepts.")
            return report

        except Exception as e:
            logger.error(f"Error in iteration cycle: {str(e)}")
            return {"error": str(e)}

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Initialize Engine
    engine = SymbiosisEngine()

    # 2. Define Inputs
    ai_code = """
def process_data(path):
    # Load data
    with open(path, 'r') as f:
        data = f.read()
    return data
"""

    human_code = """
import os

def process_data(path):
    # Load data safely
    if not os.path.exists(path):
        return None
    
    # Fix: Use utf-8 encoding explicitly
    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()
    
    # Add processing
    return data.strip()
"""

    draft = CodeArtifact(id="draft_001", content=ai_code, source="ai", timestamp=0.0)
    human_fix = CodeArtifact(id="draft_001_mod", content=human_code, source="human", timestamp=1.0)

    # 3. Run Symbiosis Loop
    analysis_report = engine.run_iteration_cycle(draft, human_fix)

    # 4. Output Results
    print("\n--- Analysis Report ---")
    print(json.dumps(analysis_report, indent=2))