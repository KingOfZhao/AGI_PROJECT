"""
Module: cognitive_node_half_life
A robust mathematical model for implementing time-based decay of cognitive node weights
in AGI systems, featuring configurable decay rates, domain volatility factors, and
automated threshold-based triggering for re-validation or archival.

Author: Senior Python Engineer
Version: 1.0.0
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveNode:
    """
    Data structure representing a cognitive node in the knowledge graph.
    
    Attributes:
        node_id: Unique identifier for the node
        content: The actual knowledge content (e.g., IT solution)
        created_at: Timestamp when node was created
        last_verified: Timestamp when node was last verified
        last_accessed: Timestamp when node was last accessed
        initial_weight: Starting weight value (0.0 to 1.0)
        access_count: Number of times node has been accessed
        domain: Domain category (e.g., 'networking', 'security')
    """
    
    def __init__(
        self,
        node_id: str,
        content: str,
        created_at: datetime,
        last_verified: datetime,
        last_accessed: datetime,
        initial_weight: float = 1.0,
        access_count: int = 0,
        domain: str = "general"
    ):
        self.node_id = node_id
        self.content = content
        self.created_at = created_at
        self.last_verified = last_verified
        self.last_accessed = last_accessed
        self.initial_weight = initial_weight
        self.access_count = access_count
        self.domain = domain
        
    def to_dict(self) -> Dict:
        """Convert node to dictionary representation."""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "last_verified": self.last_verified.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "initial_weight": self.initial_weight,
            "access_count": self.access_count,
            "domain": self.domain
        }


class CognitiveHalfLifeCalculator:
    """
    Implements a mathematical model for calculating cognitive node decay based on:
    - Time since last verification
    - Historical access frequency
    - Domain-specific volatility rates
    
    The model uses exponential decay with configurable half-lives and domain factors.
    """
    
    # Default half-life in days for different domains
    DOMAIN_HALF_LIVES: Dict[str, float] = {
        "networking": 90.0,
        "security": 30.0,
        "software": 60.0,
        "hardware": 180.0,
        "general": 120.0
    }
    
    # Default decay factors (higher = faster decay)
    DOMAIN_VOLATILITY: Dict[str, float] = {
        "networking": 0.8,
        "security": 1.2,  # Security knowledge becomes obsolete faster
        "software": 1.0,
        "hardware": 0.6,
        "general": 0.9
    }
    
    # Minimum weight threshold before triggering re-validation
    DEFAULT_WEIGHT_THRESHOLD = 0.3
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the calculator with optional configuration overrides.
        
        Args:
            config: Dictionary with custom half-lives and volatility factors
        """
        self.config = config or {}
        self._merge_config()
        logger.info("CognitiveHalfLifeCalculator initialized with config: %s", self.config)
    
    def _merge_config(self) -> None:
        """Merge custom configuration with defaults."""
        if "half_lives" in self.config:
            self.DOMAIN_HALF_LIVES.update(self.config["half_lives"])
        if "volatility" in self.config:
            self.DOMAIN_VOLATILITY.update(self.config["volatility"])
        if "weight_threshold" in self.config:
            self.DEFAULT_WEIGHT_THRESHOLD = self.config["weight_threshold"]
    
    def _validate_node(self, node: CognitiveNode) -> bool:
        """
        Validate that a cognitive node has all required fields and valid values.
        
        Args:
            node: CognitiveNode instance to validate
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        if not isinstance(node, CognitiveNode):
            raise ValueError("Input must be a CognitiveNode instance")
            
        if not node.node_id:
            raise ValueError("Node ID cannot be empty")
            
        if not node.content:
            logger.warning("Node %s has empty content", node.node_id)
            
        if node.last_verified > datetime.now():
            raise ValueError("Last verified time cannot be in the future")
            
        if node.last_accessed > datetime.now():
            raise ValueError("Last accessed time cannot be in the future")
            
        if not 0 <= node.initial_weight <= 1:
            raise ValueError("Initial weight must be between 0 and 1")
            
        if node.access_count < 0:
            raise ValueError("Access count cannot be negative")
            
        return True
    
    def _get_domain_params(self, domain: str) -> Tuple[float, float]:
        """
        Get domain-specific half-life and volatility factor.
        
        Args:
            domain: Domain category
            
        Returns:
            Tuple of (half_life_days, volatility_factor)
        """
        half_life = self.DOMAIN_HALF_LIVES.get(
            domain, 
            self.DOMAIN_HALF_LIVES["general"]
        )
        volatility = self.DOMAIN_VOLATILITY.get(
            domain, 
            self.DOMAIN_VOLATILITY["general"]
        )
        return half_life, volatility
    
    def calculate_access_factor(self, node: CognitiveNode) -> float:
        """
        Calculate a factor based on historical access frequency.
        Nodes accessed more frequently decay slower.
        
        Args:
            node: CognitiveNode instance
            
        Returns:
            Access factor between 0.5 (rarely accessed) and 1.0 (frequently accessed)
        """
        # Normalize access count using logarithmic scale
        # This gives diminishing returns for very high access counts
        if node.access_count == 0:
            return 0.5
            
        log_access = math.log10(node.access_count + 1)
        max_log = 3.0  # Assumes 1000 accesses is "very frequent"
        
        # Scale between 0.5 and 1.0
        factor = 0.5 + 0.5 * min(log_access / max_log, 1.0)
        return round(factor, 4)
    
    def calculate_current_weight(
        self, 
        node: CognitiveNode, 
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate the current active weight of a cognitive node based on:
        - Time since last verification
        - Domain-specific half-life
        - Historical access frequency
        
        Implements exponential decay: W(t) = W0 * e^(-λt) * access_factor
        
        Args:
            node: CognitiveNode instance
            current_time: Override current time (for testing)
            
        Returns:
            Current weight between 0.0 and 1.0
        """
        try:
            self._validate_node(node)
        except ValueError as e:
            logger.error("Node validation failed: %s", e)
            raise
            
        current_time = current_time or datetime.now()
        
        # Get domain parameters
        half_life_days, volatility = self._get_domain_params(node.domain)
        
        # Calculate time since verification in days
        time_delta = current_time - node.last_verified
        days_elapsed = time_delta.total_seconds() / (24 * 3600)
        
        # Prevent negative time
        days_elapsed = max(0, days_elapsed)
        
        # Calculate decay constant (λ = ln(2) / half_life)
        decay_constant = math.log(2) / half_life_days
        
        # Calculate access factor
        access_factor = self.calculate_access_factor(node)
        
        # Calculate current weight with exponential decay
        # Adjusted by volatility factor and access frequency
        decay = math.exp(-decay_constant * days_elapsed * volatility)
        current_weight = node.initial_weight * decay * access_factor
        
        # Ensure weight stays within bounds
        current_weight = max(0.0, min(1.0, current_weight))
        
        logger.debug(
            "Node %s: days=%.2f, decay=%.4f, access_factor=%.4f, weight=%.4f",
            node.node_id, days_elapsed, decay, access_factor, current_weight
        )
        
        return round(current_weight, 6)
    
    def evaluate_node_status(
        self, 
        node: CognitiveNode, 
        threshold: Optional[float] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Union[str, float, bool]]:
        """
        Evaluate a node's status and determine if action is needed.
        
        Args:
            node: CognitiveNode instance
            threshold: Weight threshold for triggering actions
            current_time: Override current time (for testing)
            
        Returns:
            Dictionary with evaluation results including:
            - current_weight
            - action_needed (bool)
            - recommended_action (str)
            - days_since_verification (float)
        """
        threshold = threshold or self.DEFAULT_WEIGHT_THRESHOLD
        current_time = current_time or datetime.now()
        
        try:
            current_weight = self.calculate_current_weight(node, current_time)
        except ValueError as e:
            return {
                "node_id": node.node_id,
                "error": str(e),
                "action_needed": False,
                "recommended_action": "fix_invalid_data"
            }
        
        days_since_verification = (current_time - node.last_verified).days
        
        # Determine recommended action
        if current_weight < threshold * 0.5:
            recommended_action = "archive"
        elif current_weight < threshold:
            recommended_action = "revalidate"
        else:
            recommended_action = "none"
        
        action_needed = recommended_action != "none"
        
        result = {
            "node_id": node.node_id,
            "current_weight": current_weight,
            "threshold": threshold,
            "action_needed": action_needed,
            "recommended_action": recommended_action,
            "days_since_verification": days_since_verification,
            "domain": node.domain
        }
        
        if action_needed:
            logger.warning(
                "Node %s requires %s (weight: %.4f < threshold: %.4f)",
                node.node_id, recommended_action, current_weight, threshold
            )
        
        return result
    
    def batch_evaluate(
        self, 
        nodes: List[CognitiveNode], 
        threshold: Optional[float] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, List[Dict]]:
        """
        Evaluate multiple nodes and categorize them by recommended action.
        
        Args:
            nodes: List of CognitiveNode instances
            threshold: Weight threshold for triggering actions
            current_time: Override current time (for testing)
            
        Returns:
            Dictionary with categorized evaluation results
        """
        results = {
            "revalidate": [],
            "archive": [],
            "healthy": [],
            "errors": []
        }
        
        for node in nodes:
            try:
                eval_result = self.evaluate_node_status(
                    node, threshold, current_time
                )
                
                if "error" in eval_result:
                    results["errors"].append(eval_result)
                elif eval_result["recommended_action"] == "archive":
                    results["archive"].append(eval_result)
                elif eval_result["recommended_action"] == "revalidate":
                    results["revalidate"].append(eval_result)
                else:
                    results["healthy"].append(eval_result)
                    
            except Exception as e:
                logger.exception("Error evaluating node %s", node.node_id)
                results["errors"].append({
                    "node_id": node.node_id,
                    "error": str(e)
                })
        
        # Log summary
        logger.info(
            "Batch evaluation complete: %d healthy, %d revalidate, %d archive, %d errors",
            len(results["healthy"]), len(results["revalidate"]),
            len(results["archive"]), len(results["errors"])
        )
        
        return results


# Example usage
if __name__ == "__main__":
    # Create sample cognitive nodes
    now = datetime.now()
    
    nodes = [
        CognitiveNode(
            node_id="IT_SOL_001",
            content="Restart router to fix connectivity issues",
            created_at=now - timedelta(days=365),
            last_verified=now - timedelta(days=180),
            last_accessed=now - timedelta(days=30),
            initial_weight=0.95,
            access_count=50,
            domain="networking"
        ),
        CognitiveNode(
            node_id="IT_SEC_002",
            content="Use firewall rule X to block malware Y",
            created_at=now - timedelta(days=60),
            last_verified=now - timedelta(days=45),
            last_accessed=now - timedelta(days=5),
            initial_weight=1.0,
            access_count=5,
            domain="security"
        ),
        CognitiveNode(
            node_id="IT_HRD_003",
            content="Replace RAM module in server Z",
            created_at=now - timedelta(days=400),
            last_verified=now - timedelta(days=400),
            last_accessed=now - timedelta(days=200),
            initial_weight=0.9,
            access_count=2,
            domain="hardware"
        )
    ]
    
    # Initialize calculator with custom config
    config = {
        "weight_threshold": 0.4,
        "volatility": {
            "security": 1.5  # Even higher volatility for security
        }
    }
    
    calculator = CognitiveHalfLifeCalculator(config)
    
    # Evaluate individual nodes
    print("\nIndividual Node Evaluations:")
    for node in nodes:
        result = calculator.evaluate_node_status(node)
        print(f"Node {result['node_id']}: Weight={result['current_weight']:.4f}, "
              f"Action={result['recommended_action']}")
    
    # Batch evaluation
    print("\nBatch Evaluation Results:")
    batch_results = calculator.batch_evaluate(nodes)
    for category, items in batch_results.items():
        print(f"{category.upper()}: {len(items)} nodes")