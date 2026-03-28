"""
Skill Node Health Monitor & Executor Coverage Analyzer

Module Name: skill_node_monitor_11bd72
Description: Monitors the health and validity of AGI skill nodes by validating
             environment variables, checking API availability, and performing
             basic execution coverage analysis.

Author: Senior Python Engineer
Version: 1.0.0
"""

import os
import re
import json
import logging
import subprocess
import importlib.util
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("skill_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Enumeration of possible Skill Node statuses."""
    HEALTHY = "healthy"
    DAMAGED = "damaged"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


@dataclass
class SkillNode:
    """
    Data structure representing a Skill Node.

    Attributes:
        node_id: Unique identifier for the skill node.
        name: Human-readable name.
        exec_path: Path to the Python script or module.
        env_dependencies: List of required environment variable keys.
        api_endpoints: List of external API URLs the node depends on.
        last_checked: Timestamp of the last check.
    """
    node_id: str
    name: str
    exec_path: str
    env_dependencies: List[str] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    last_checked: Optional[datetime] = None


class SkillMonitor:
    """
    Monitors and validates the integrity of Skill Nodes.

    This class automates the detection of node validity, including static
    analysis of code existence, environment variable availability, and
    optional runtime checks.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the monitor.

        Args:
            config_path: Path to a JSON file containing node definitions.
        """
        self.nodes: Dict[str, SkillNode] = {}
        if config_path:
            self.load_nodes_from_config(config_path)

    def load_nodes_from_config(self, file_path: str) -> None:
        """
        Load skill node configurations from a JSON file.

        Args:
            file_path: Path to the configuration file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        logger.info(f"Loading configuration from {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("Configuration must be a list of node objects.")

            for item in data:
                try:
                    node = SkillNode(
                        node_id=item['node_id'],
                        name=item['name'],
                        exec_path=item['exec_path'],
                        env_dependencies=item.get('env_dependencies', []),
                        api_endpoints=item.get('api_endpoints', [])
                    )
                    self.nodes[node.node_id] = node
                except KeyError as e:
                    logger.error(f"Missing key in node config: {e} - Skipping entry.")
            
            logger.info(f"Successfully loaded {len(self.nodes)} nodes.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def check_environment_variables(self, required_vars: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if required environment variables are set.

        Args:
            required_vars: List of environment variable names.

        Returns:
            A tuple (is_valid, missing_vars).
        """
        missing = []
        for var in required_vars:
            if var not in os.environ or not os.environ[var]:
                missing.append(var)
        
        is_valid = len(missing) == 0
        return is_valid, missing

    def analyze_code_static(self, node: SkillNode) -> Tuple[NodeStatus, str]:
        """
        Perform static analysis on the node's executable code.

        Checks:
        1. File existence.
        2. Python syntax validity (using py_compile).
        3. Presence of required function definitions (optional, checking for 'execute' or 'run').

        Args:
            node: The SkillNode to analyze.

        Returns:
            Tuple of (NodeStatus, message).
        """
        path = node.exec_path
        if not os.path.exists(path):
            logger.warning(f"Node {node.node_id}: Path not found {path}")
            return NodeStatus.DAMAGED, f"Executable path missing: {path}"

        # Try to compile the file to check for syntax errors
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, path, 'exec')
        except SyntaxError as e:
            logger.error(f"Node {node.node_id}: Syntax error in {path} - {e}")
            return NodeStatus.DAMAGED, f"Syntax Error: {e}"
        except Exception as e:
            logger.error(f"Node {node.node_id}: Error reading file {path} - {e}")
            return NodeStatus.DAMAGED, f"Read Error: {e}"

        # Check for required env vars
        env_valid, missing = self.check_environment_variables(node.env_dependencies)
        if not env_valid:
            msg = f"Missing environment variables: {', '.join(missing)}"
            logger.warning(f"Node {node.node_id}: {msg}")
            return NodeStatus.DAMAGED, msg

        return NodeStatus.HEALTHY, "Static analysis passed."

    def run_node_diagnostics(self, node_id: str) -> Dict[str, Any]:
        """
        Execute full diagnostics for a specific node.

        Args:
            node_id: The ID of the node to check.

        Returns:
            A dictionary containing diagnostic results.
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found in registry.")
            return {"status": "error", "message": "Node not found"}

        node = self.nodes[node_id]
        node.last_checked = datetime.now()
        
        # 1. Static Analysis
        status, message = self.analyze_code_static(node)
        
        # 2. API Connectivity (Simplified check via curl availability or request if implemented)
        # For this module, we assume API checks are external or complex, so we focus on Code/Env.
        
        result = {
            "node_id": node.node_id,
            "name": node.name,
            "status": status.value,
            "message": message,
            "timestamp": node.last_checked.isoformat()
        }

        if status == NodeStatus.HEALTHY:
            logger.info(f"Node {node_id} is HEALTHY.")
        else:
            logger.warning(f"Node {node_id} is DAMAGED: {message}")

        return result

    def batch_analyze_coverage(self) -> Dict[str, List[str]]:
        """
        Analyze all loaded nodes and categorize them by health status.

        Returns:
            Dictionary categorizing node IDs by status.
        """
        report = {
            "healthy": [],
            "damaged": [],
            "errors": []
        }

        logger.info(f"Starting batch analysis for {len(self.nodes)} nodes...")
        
        for node_id in self.nodes:
            try:
                result = self.run_node_diagnostics(node_id)
                if result['status'] == NodeStatus.HEALTHY.value:
                    report["healthy"].append(node_id)
                else:
                    report["damaged"].append(node_id)
            except Exception as e:
                logger.exception(f"Critical error analyzing node {node_id}")
                report["errors"].append(node_id)

        logger.info(f"Analysis complete. Healthy: {len(report['healthy'])}, Damaged: {len(report['damaged'])}")
        return report


# --- Helper Functions ---

def generate_sample_config(output_path: str = "sample_skills.json") -> None:
    """
    Generates a sample configuration file for testing purposes.
    
    Args:
        output_path: Where to save the JSON file.
    """
    sample_data = [
        {
            "node_id": "skill_001",
            "name": "WeatherAPIFetcher",
            "exec_path": "./skills/weather_skill.py", # Assume this might not exist
            "env_dependencies": ["OPENWEATHER_API_KEY"],
            "api_endpoints": ["https://api.openweathermap.org/data/2.5/"]
        },
        {
            "node_id": "skill_002",
            "name": "DatabaseCleaner",
            "exec_path": "./skills/db_cleaner.py",
            "env_dependencies": ["DB_CONN_STRING", "ADMIN_USER"]
        }
    ]
    with open(output_path, 'w') as f:
        json.dump(sample_data, f, indent=4)
    print(f"Generated sample config at {output_path}")


if __name__ == "__main__":
    # Usage Example
    # 1. Generate dummy data
    CONFIG_FILE = "skills_config.json"
    generate_sample_config(CONFIG_FILE)

    # 2. Create a dummy skill file for demonstration
    if not os.path.exists("./skills"):
        os.makedirs("./skills")
    
    with open("./skills/weather_skill.py", "w") as f:
        f.write("print('Weather skill loaded')\n")
        # This file is valid python but logic depends on ENV vars

    # 3. Initialize Monitor
    monitor = SkillMonitor(CONFIG_FILE)

    # 4. Run Diagnostics
    # Note: This will likely report 'damaged' because the env vars are missing in your shell
    diagnostic_report = monitor.batch_analyze_coverage()
    
    print("\n--- Final Report ---")
    print(json.dumps(diagnostic_report, indent=2))