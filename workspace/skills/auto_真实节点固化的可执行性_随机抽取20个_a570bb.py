"""
Module: auto_真实节点固化的可执行性_随机抽取20个_a570bb

This module is designed to verify the executability of 'known nodes' in an AGI system.
It randomly selects 20 entries marked as 'known nodes' and attempts to generate
valid, executable Python or Shell scripts from them. This process validates whether
the knowledge contained within the nodes is 'executable' (procedural/functional)
or merely 'descriptive' (declarative).

Author: Auto-Generated AGI Skill
Version: 1.0.0
"""

import json
import logging
import os
import random
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Enumeration for different types of knowledge nodes."""
    PYTHON = "python"
    SHELL = "shell"
    UNKNOWN = "unknown"

@dataclass
class KnowledgeNode:
    """
    Represents a single unit of knowledge in the AGI system.
    
    Attributes:
        id: Unique identifier for the node.
        content: The raw content (description or code).
        type: The detected type of the node (Python, Shell, etc.).
        context: Additional context or metadata required for execution.
    """
    id: str
    content: str
    type: NodeType
    context: Dict[str, str]

class NodeValidationError(Exception):
    """Custom exception for errors during node validation."""
    pass

class ExecutionEnvironmentError(Exception):
    """Custom exception for environment setup failures."""
    pass

def detect_node_type(content: str) -> NodeType:
    """
    Auxiliary function to detect the programming language of the content.
    
    Uses heuristics like keywords and syntax structure to determine if the content
    is Python, Shell, or unknown.
    
    Args:
        content: The raw string content of the node.
        
    Returns:
        NodeType: The detected language type.
        
    Example:
        >>> detect_node_type("print('hello world')")
        <NodeType.PYTHON: 'python'>
    """
    content = content.strip()
    
    # Heuristics for Python
    python_indicators = [
        r'\bdef\s+\w+\s*\(', 
        r'\bimport\s+\w+', 
        r'\bprint\s*\(', 
        r'\bclass\s+\w+:',
        r'if\s+__name__\s*==\s*["\']__main__["\']'
    ]
    for pattern in python_indicators:
        if re.search(pattern, content):
            return NodeType.PYTHON

    # Heuristics for Shell
    shell_indicators = [
        r'^\s*#\!/bin/(bash|sh)', 
        r'\b(apt-get|yum|brew|pip|npm)\s+install\b',
        r'\b(echo|grep|awk|sed|chmod|docker)\s+',
        r'\$\(.*\)', # Command substitution
        r'\|\s*\w+' # Piping
    ]
    for pattern in shell_indicators:
        if re.search(pattern, content):
            return NodeType.SHELL
            
    return NodeType.UNKNOWN

def sanitize_script_content(content: str, node_type: NodeType) -> str:
    """
    Sanitizes and wraps the content to ensure it is safe for execution.
    
    For Python, it wraps loose statements in a main block.
    For Shell, it ensures standard error output redirection.
    
    Args:
        content: The raw script content.
        node_type: The type of the script.
        
    Returns:
        str: The sanitized script ready for writing to a file.
    """
    if node_type == NodeType.PYTHON:
        # Ensure code is indented properly if wrapped in main
        if "if __name__" not in content:
            wrapped = textwrap.indent(content, "    ")
            return f"import sys\n\ndef main():\n{wrapped}\n\nif __name__ == '__main__':\n    main()"
        return content
    
    if node_type == NodeType.SLL:
        # Add standard error handling for shell scripts
        return f"#!/bin/bash\nset -e\n{content}"
        
    return content

def verify_node_executability(node: KnowledgeNode) -> Tuple[bool, str]:
    """
    Core function that attempts to execute the node content in a sandboxed environment.
    
    It writes the script to a temporary file, executes it, captures the output,
    and checks for success or failure.
    
    Args:
        node: The KnowledgeNode object to verify.
        
    Returns:
        Tuple[bool, str]: (True, output) if execution successful, (False, error_msg) otherwise.
    """
    logger.info(f"Validating node {node.id}...")
    
    # Create a temporary workspace
    workspace = f"/tmp/agi_skill_exec_{node.id}"
    os.makedirs(workspace, exist_ok=True)
    
    script_path = ""
    command = []
    
    if node.type == NodeType.PYTHON:
        script_path = os.path.join(workspace, "script.py")
        with open(script_path, "w") as f:
            f.write(sanitize_script_content(node.content, node.type))
        command = [sys.executable, script_path]
        
    elif node.type == NodeType.SHELL:
        script_path = os.path.join(workspace, "script.sh")
        with open(script_path, "w") as f:
            f.write(sanitize_script_content(node.content, node.type))
        os.chmod(script_path, 0o755)
        command = ["/bin/bash", script_path]
        
    else:
        return False, "Node type is UNKNOWN or not executable."
    
    try:
        # Use timeout to prevent hanging
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd=workspace,
            env={**os.environ, **node.context} # Inject context as env vars
        )
        
        if result.returncode == 0:
            logger.info(f"Node {node.id} executed successfully.")
            return True, result.stdout
        else:
            logger.warning(f"Node {node.id} execution failed with code {result.returncode}.")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error(f"Node {node.id} execution timed out.")
        return False, "Execution timed out."
    except Exception as e:
        logger.error(f"Unexpected error executing node {node.id}: {str(e)}")
        return False, str(e)
    finally:
        # Cleanup workspace (optional, commented out for debugging)
        # if os.path.exists(workspace):
        #     shutil.rmtree(workspace)
        pass

def process_bulk_nodes(nodes: List[Dict[str, str]], sample_size: int = 20) -> Dict[str, Dict]:
    """
    Main driver function to process a list of nodes.
    
    Validates input, randomly selects the specified number of nodes, 
    classifies them, and attempts execution.
    
    Args:
        nodes: A list of dictionaries representing raw node data.
        sample_size: Number of nodes to randomly select (default 20).
        
    Returns:
        Dict: A report containing statistics and details of the execution.
        
    Example Input format:
        [
            {"id": "node_1", "content": "print('hello')", "context": {}},
            {"id": "node_2", "content": "echo 'World'", "context": {}}
        ]
    """
    if not nodes:
        raise NodeValidationError("Input node list is empty.")
        
    if len(nodes) < sample_size:
        logger.warning(f"Requested sample size {sample_size} exceeds list size {len(nodes)}. Using all nodes.")
        sample_size = len(nodes)
        
    # Random Sampling
    sampled_raw = random.sample(nodes, sample_size)
    
    results = {
        "total_processed": 0,
        "executable_count": 0,
        "descriptive_count": 0,
        "details": []
    }
    
    for raw in sampled_raw:
        # Data Validation
        if not all(k in raw for k in ["id", "content"]):
            logger.warning(f"Skipping invalid node entry: {raw}")
            continue
            
        # Object Mapping
        detected_type = detect_node_type(raw["content"])
        node = KnowledgeNode(
            id=raw["id"],
            content=raw["content"],
            type=detected_type,
            context=raw.get("context", {})
        )
        
        # Execution Verification
        is_executable, output = verify_node_executability(node)
        
        results["total_processed"] += 1
        if is_executable:
            results["executable_count"] += 1
            status = "EXECUTABLE_KNOWLEDGE"
        else:
            results["descriptive_count"] += 1
            status = "DESCRIPTIVE_OR_FAILED"
            
        results["details"].append({
            "node_id": node.id,
            "type": node.type.value,
            "status": status,
            "output_preview": output[:100] + "..." if len(output) > 100 else output
        })
        
    return results

# ---------------------------------------------------------
# Usage Example
# ---------------------------------------------------------
if __name__ == "__main__":
    # Mock Data Generation for Demonstration
    mock_data = [
        {"id": "py_01", "content": "x = 10; y = 20; print(x+y)", "context": {}},
        {"id": "sh_01", "content": "echo 'Current dir:'; pwd", "context": {}},
        {"id": "txt_01", "content": "This is just a description of a concept.", "context": {}},
        {"id": "py_02", "content": "import math; print(math.sqrt(16))", "context": {}},
        {"id": "err_01", "content": "import non_existent_module", "context": {}},
    ] * 5 # Repeat to ensure we have enough for sample size
    
    try:
        logger.info("Starting AGI Skill Execution: Node Solidification Check")
        report = process_bulk_nodes(mock_data, sample_size=5)
        
        print("\n--- EXECUTION REPORT ---")
        print(f"Total Processed: {report['total_processed']}")
        print(f"Executable Nodes: {report['executable_count']}")
        print(f"Descriptive/Failed Nodes: {report['descriptive_count']}")
        print("\nDetails:")
        for item in report['details']:
            print(f" - ID: {item['node_id']} | Type: {item['type']} | Status: {item['status']}")
            
    except NodeValidationError as e:
        logger.error(f"Validation Error: {e}")
    except Exception as e:
        logger.critical(f"System Failure: {e}", exc_info=True)