"""
Module: auto_cognitive_solidification.py
Description: Implements mechanisms to detect stable code patterns ('Real Nodes') within an AGI system
             and refactor them into reusable, parameterized functions or classes, thereby achieving
             'Cognitive Solidification' and autonomous knowledge base growth.
"""

import ast
import astor
import logging
import hashlib
from typing import List, Dict, Optional, Union, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveSolidification")

@dataclass
class CodeFragment:
    """Represents a raw code snippet generated or executed by the system."""
    id: str
    source_code: str
    execution_count: int = 0
    success_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    signature_hash: str = ""

    def __post_init__(self):
        """Calculates a structural hash to identify similar logic regardless of variable names."""
        try:
            tree = ast.parse(self.source_code)
            # Remove variable names and docstrings to normalize structure
            cleaner = VariableRenamer()
            cleaned_tree = cleaner.visit(tree)
            self.signature_hash = hashlib.sha256(ast.dump(cleaned_tree).encode('utf-8')).hexdigest()
        except SyntaxError:
            self.signature_hash = hashlib.sha256(self.source_code.encode('utf-8')).hexdigest()

@dataclass
class SkillNode:
    """Represents a solidified, reusable skill in the library."""
    function_name: str
    parameters: List[str]
    body: str
    created_at: datetime = field(default_factory=datetime.now)
    stability_score: float = 0.0

class VariableRenamer(ast.NodeTransformer):
    """
    Helper: AST Transformer to rename variables to generic placeholders (var_0, var_1...)
    to enable structural comparison of code snippets.
    """
    def __init__(self):
        super().__init__()
        self.var_map = {}
        self.var_counter = 0

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id not in self.var_map:
            self.var_map[node.id] = f"var_{self.var_counter}"
            self.var_counter += 1
        node.id = self.var_map[node.id]
        return node

class KnowledgeBase:
    """
    Mock database for storing raw code fragments and the Skill Library.
    """
    def __init__(self):
        self.raw_fragments: Dict[str, CodeFragment] = {}
        self.skill_library: Dict[str, SkillNode] = {}

    def add_fragment(self, code: str) -> CodeFragment:
        frag_id = hashlib.md5(code.encode()).hexdigest()
        if frag_id in self.raw_fragments:
            self.raw_fragments[frag_id].execution_count += 1
            self.raw_fragments[frag_id].success_count += 1 # Assuming success if added again
            self.raw_fragments[frag_id].last_used = datetime.now()
        else:
            fragment = CodeFragment(id=frag_id, source_code=code)
            self.raw_fragments[frag_id] = fragment
        return self.raw_fragments[frag_id]

    def get_stable_candidates(self, threshold: int) -> List[CodeFragment]:
        return [
            f for f in self.raw_fragments.values()
            if f.execution_count >= threshold and f.success_count == f.execution_count
        ]

class CognitiveSolidifier:
    """
    Core Engine: Analyzes raw code fragments to identify 'Real Nodes' (stable patterns)
    and refactors them into parameterized functions.
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.MIN_STABILITY_THRESHOLD = 3  # Config: Number of successful reuses required

    def _extract_variables(self, code: str) -> Set[str]:
        """
        Helper: Analyzes code to identify input dependencies (variables used but not defined).
        """
        try:
            tree = ast.parse(code)
            analyzer = DependencyAnalyzer()
            analyzer.visit(tree)
            return analyzer.inputs
        except Exception as e:
            logger.error(f"AST analysis failed for code extraction: {e}")
            return set()

    def monitor_and_solidify(self) -> Optional[SkillNode]:
        """
        Core: Scans the knowledge base for code fragments that meet stability criteria.
        If found, triggers the refactoring process.
        """
        candidates = self.kb.get_stable_candidates(self.MIN_STABILITY_THRESHOLD)
        if not candidates:
            logger.info("No stable code patterns detected yet.")
            return None

        # Group by structural hash to find duplicates
        hash_groups: Dict[str, List[CodeFragment]] = {}
        for c in candidates:
            if c.signature_hash not in hash_groups:
                hash_groups[c.signature_hash] = []
            hash_groups[c.signature_hash].append(c)

        # Check for repeated structural patterns
        for sig, group in hash_groups.items():
            if len(group) >= 1:  # Logic could be stricter (e.g. different contexts)
                logger.info(f"Detected stable pattern with signature {sig[:8]}...")
                return self._refactor_to_skill(group[0])
        
        return None

    def _refactor_to_skill(self, fragment: CodeFragment) -> Optional[SkillNode]:
        """
        Core: Transforms a raw code snippet into a parameterized SkillNode.
        """
        logger.info(f"Refactoring code ID {fragment.id} into Skill...")
        
        inputs = self._extract_variables(fragment.source_code)
        if not inputs:
            logger.warning("Code appears self-contained or static; skipping parameterization.")
            return None

        func_name = f"skill_{fragment.id[:6]}"
        params = sorted(list(inputs))
        
        # Simple wrapping logic (Real implementation might use AST manipulation for injection)
        function_body = f"def {func_name}({', '.join(params)}):\n"
        
        # Indent original code
        indented_body = "\n".join(["    " + line for line in fragment.source_code.split("\n") if line.strip()])
        function_body += indented_body
        
        new_skill = SkillNode(
            function_name=func_name,
            parameters=params,
            body=function_body,
            stability_score=fragment.success_count / (fragment.execution_count + 1e-9)
        )
        
        self.kb.skill_library[func_name] = new_skill
        logger.info(f"Successfully created Skill: {func_name}")
        return new_skill

class DependencyAnalyzer(ast.NodeVisitor):
    """
    Helper: AST Visitor to determine variable inputs.
    Tracks names that are loaded before being stored.
    """
    def __init__(self):
        self.inputs: Set[str] = set()
        self.scopes: List[Set[str]] = [set()]  # Stack of scopes

    def visit_Assign(self, node: ast.Assign):
        # Mark targets as defined in current scope
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.scopes[-1].add(target.id)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            # Check if defined in any scope
            is_defined = any(node.id in scope for scope in self.scopes)
            # Filter out built-ins (simplified list)
            built_ins = {'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict'}
            if not is_defined and node.id not in built_ins:
                self.inputs.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Enter new scope
        self.scopes.append(set(node.args.args))
        self.generic_visit(node)
        self.scopes.pop()

# -----------------------------
# Usage Example
# -----------------------------
if __name__ == "__main__":
    # Initialize System
    kb = KnowledgeBase()
    solidifier = CognitiveSolidifier(kb)

    # Simulate AGI generating and using code multiple times
    # This snippet calculates the area of a rectangle
    snippet = """
width = w
height = h
area = width * height
print(f"Area: {area}")
"""
    
    logger.info("Feeding system with repeated usage of a code pattern...")
    
    # Simulate multiple successful uses
    for _ in range(4):
        kb.add_fragment(snippet)

    # Run Monitor
    new_skill = solidifier.monitor_and_solidify()

    if new_skill:
        print("\n--- Generated Skill Code ---")
        print(new_skill.body)
        print("Parameters:", new_skill.parameters)
        print("----------------------------")