"""
Module: capability_graph_builder
This module provides tools to transform unstructured legacy codebases into a structured
'Capability Graph' using static analysis. It allows mapping fuzzy user intents to specific
function call paths rather than just isolated code snippets.

Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import ast
import logging
import os
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Structures ---

@dataclass
class CodeNode:
    """
    Represents a node in the Capability Graph.
    
    Attributes:
        id: Unique identifier (usually the qualified function name).
        name: Short name of the function/class.
        docstring: Extracted documentation string (semantic meaning).
        args: List of argument names.
        calls: List of other node IDs this node calls (dependencies).
    """
    id: str
    name: str
    docstring: Optional[str] = None
    args: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)

@dataclass
class CapabilityGraph:
    """
    Represents the structured capability graph of the codebase.
    """
    nodes: Dict[str, CodeNode] = field(default_factory=dict)
    adjacency_list: Dict[str, List[str]] = field(default_factory=dict)

    def add_node(self, node: CodeNode) -> None:
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Overwriting.")
        self.nodes[node.id] = node
        self.adjacency_list[node.id] = node.calls

    def get_execution_path(self, start_node_id: str) -> List[str]:
        """Retrieves a linear execution path via DFS (simplified)."""
        if start_node_id not in self.nodes:
            raise ValueError(f"Node {start_node_id} not found in graph.")
        
        path = []
        visited = set()
        
        def _dfs(current_id: str):
            if current_id in visited or current_id not in self.nodes:
                return
            visited.add(current_id)
            path.append(current_id)
            for neighbor in self.adjacency_list.get(current_id, []):
                _dfs(neighbor)
        
        _dfs(start_node_id)
        return path

# --- Static Analysis Engine ---

class CodebaseParser(ast.NodeVisitor):
    """
    AST Visitor that traverses a Python codebase to extract semantic structures
    and build the Capability Graph.
    """

    def __init__(self, root_dir: str):
        """
        Initialize the parser.
        
        Args:
            root_dir: The root directory of the legacy codebase.
        """
        if not os.path.isdir(root_dir):
            raise ValueError(f"Directory does not exist: {root_dir}")
        
        self.root_dir = root_dir
        self.graph = CapabilityGraph()
        self.current_module: str = ""
        self.import_aliases: Dict[str, str] = {}
        logger.info(f"CodebaseParser initialized for directory: {root_dir}")

    def _resolve_name(self, node: ast.AST) -> str:
        """Helper to resolve attribute names (e.g., self.func -> ClassName.func)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parent = self._resolve_name(node.value)
            return f"{parent}.{node.attr}"
        return ""

    def _parse_file(self, filepath: str) -> None:
        """Parses a single Python file and updates the graph."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=filepath)
            # Update module context
            rel_path = os.path.relpath(filepath, self.root_dir)
            self.current_module = rel_path.replace(os.sep, ".").replace(".py", "")
            
            logger.debug(f"Parsing module: {self.current_module}")
            self.import_aliases = {} # Reset imports per file
            self.visit(tree)
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {filepath}: {e}")
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}", exc_info=True)

    def build_graph(self) -> CapabilityGraph:
        """
        Scans the directory recursively and builds the capability graph.
        
        Returns:
            CapabilityGraph: The fully constructed graph.
        """
        logger.info("Starting static analysis and graph construction...")
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    self._parse_file(full_path)
        
        self._link_external_calls()
        logger.info(f"Graph construction complete. Total nodes: {len(self.graph.nodes)}")
        return self.graph

    def visit_Import(self, node: ast.Import) -> None:
        """Track imports to resolve cross-module calls."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.import_aliases[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track 'from x import y' statements."""
        module = node.module if node.module else ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_qualname = f"{module}.{alias.name}" if module else alias.name
            self.import_aliases[name] = full_qualname
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function metadata and call relationships."""
        # Construct ID: module.function_name
        func_id = f"{self.current_module}.{node.name}"
        
        # Extract Docstring (Semantics)
        docstring = ast.get_docstring(node)
        
        # Extract Arguments
        args = [arg.arg for arg in node.args.args]
        
        # Extract Calls (Dependencies) - Simplified local scope analysis
        calls: Set[str] = set()
        
        # Analyze body for function calls
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._resolve_name(child.func)
                # Heuristic: If it's a local call or known import
                if call_name:
                    # Simple resolution: if it looks like a local call
                    if "." not in call_name:
                        calls.add(f"{self.current_module}.{call_name}")
                    else:
                        # Could be external or class method, store raw for now
                        calls.add(call_name)

        code_node = CodeNode(
            id=func_id,
            name=node.name,
            docstring=docstring,
            args=args,
            calls=list(calls)
        )
        self.graph.add_node(code_node)
        
        # Continue traversal (though we manually walked body, generic_visit ensures completeness)
        self.generic_visit(node)

    def _link_external_calls(self) -> None:
        """
        Post-processing step to link calls using import aliases.
        """
        logger.info("Resolving external dependencies...")
        for node_id, node in self.graph.nodes.items():
            resolved_calls = []
            for call in node.calls:
                # Check if the call matches an import alias
                base_name = call.split(".")[0]
                if base_name in self.import_aliases:
                    resolved = call.replace(base_name, self.import_aliases[base_name], 1)
                    resolved_calls.append(resolved)
                else:
                    resolved_calls.append(call)
            node.calls = list(set(resolved_calls))
            self.graph.adjacency_list[node_id] = node.calls

# --- Intent Matching Engine ---

def match_intent_to_path(
    graph: CapabilityGraph, 
    query: str, 
    threshold: int = 1
) -> List[Tuple[str, float]]:
    """
    Matches a fuzzy intent string against the capability graph's semantics.
    
    Args:
        graph: The structured capability graph.
        query: The fuzzy intent (e.g., "handle user login").
        threshold: Minimum score to include in results.
        
    Returns:
        List of Tuples (FunctionID, RelevanceScore).
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string.")
    
    query_tokens = set(query.lower().split())
    scores = []
    
    for node_id, node in graph.nodes.items():
        if not node.docstring:
            continue
            
        # Very simple semantic matching via token overlap (BM25 or Embeddings preferred in prod)
        doc_tokens = set(node.docstring.lower().split())
        common = query_tokens.intersection(doc_tokens)
        score = len(common) / (len(query_tokens) + 1e-6) # Simple Jaccard-like ratio
        
        # Boost if function name matches
        if any(q in node.name.lower() for q in query_tokens):
            score += 0.5
            
        if score * 10 >= threshold:
            scores.append((node_id, score))
            
    # Sort by score desc
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

# --- Main Execution / Example ---

def main():
    """
    Example usage of the Capability Graph Builder.
    """
    # Create a dummy legacy code structure for demonstration
    dummy_dir = "temp_legacy_code"
    os.makedirs(dummy_dir, exist_ok=True)
    
    # File 1: auth logic
    auth_code = """
def login_user(username, password):
    '''Authenticate a user and create a session. Validates credentials.'''
    if verify_password(username, password):
        return create_session(username)
    return None

def verify_password(user, pwd):
    '''Check if password matches database hash.'''
    # Mock logic
    return True
"""
    with open(os.path.join(dummy_dir, "auth.py"), "w") as f:
        f.write(auth_code)
        
    # File 2: session logic
    session_code = """
import time

def create_session(user_id):
    '''Generates a new session token for the user.'''
    token = generate_token()
    return {'user': user_id, 'token': token, 'time': time.time()}

def generate_token():
    '''Creates a secure random token.'''
    import secrets
    return secrets.token_hex(16)
"""
    with open(os.path.join(dummy_dir, "session_manager.py"), "w") as f:
        f.write(session_code)

    try:
        # 1. Build the graph
        parser = CodebaseParser(dummy_dir)
        capability_graph = parser.build_graph()
        
        # 2. Display Graph Structure
        print("\n--- Discovered Nodes (Capabilities) ---")
        for node_id, node in capability_graph.nodes.items():
            print(f"ID: {node_id}")
            print(f"   Doc: {node.docstring}")
            print(f"   Calls: {node.calls}")
            
        # 3. Match Intent
        print("\n--- Intent Matching ---")
        intent = "generate session for user"
        matches = match_intent_to_path(capability_graph, intent)
        
        if matches:
            best_match_id, score = matches[0]
            print(f"Intent: '{intent}'")
            print(f"Best Match: {best_match_id} (Score: {score:.2f})")
            
            # 4. Get Execution Path
            path = capability_graph.get_execution_path(best_match_id)
            print(f"Execution Path: {' -> '.join(path)}")
        else:
            print("No matching capabilities found.")
            
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")
    finally:
        # Cleanup dummy dir
        import shutil
        shutil.rmtree(dummy_dir)

if __name__ == "__main__":
    main()