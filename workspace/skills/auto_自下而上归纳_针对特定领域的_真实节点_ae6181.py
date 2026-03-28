"""
Module: auto_bottom_up_induction_real_nodes
Description: Implements a skill for an AGI system to demonstrate structured reproduction
             capabilities by constructing a cohesive business plan from scattered
             keywords using a simulated knowledge graph of "Real Nodes".
             
Domain: cognitive_modeling
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeCategory(Enum):
    """Categories for domain knowledge nodes."""
    SUPPLY_CHAIN = "supply_chain"
    MARKETING = "marketing"
    RISK_CONTROL = "risk_control"
    FINANCE = "finance"
    OPERATIONS = "operations"

@dataclass
class KnowledgeNode:
    """
    Represents a 'Real Node' in the AGI's knowledge graph.
    
    Attributes:
        id: Unique identifier for the node.
        content: The actual knowledge or strategy text.
        category: The functional category of the node.
        dependencies: List of prerequisite node IDs required to activate this node.
    """
    id: str
    content: str
    category: NodeCategory
    dependencies: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)

class KnowledgeGraph:
    """
    A simulated repository of 'Real Nodes' representing structured domain knowledge.
    In a real AGI system, this would interface with a vector database or neural memory.
    """
    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._initialize_domain_knowledge()

    def _initialize_domain_knowledge(self):
        """Populates the graph with specific, non-generic nodes for the 'Street Vendor' domain."""
        # Supply Chain Nodes
        self.add_node(KnowledgeNode(
            id="wholesale_market_168",
            content="Source inventory from local wholesale markets (e.g., 1688.com or physical markets) to maintain margins > 40%.",
            category=NodeCategory.SUPPLY_CHAIN,
            dependencies=[]
        ))
        self.add_node(KnowledgeNode(
            id="inventory_buffer",
            content="Maintain 20% safety stock for high-velocity SKUs to prevent stockouts during peak hours.",
            category=NodeCategory.SUPPLY_CHAIN,
            dependencies=["wholesale_market_168"]
        ))

        # Operations Nodes
        self.add_node(KnowledgeNode(
            id="foot_traffic_analysis",
            content="Select locations based on evening foot traffic density (>100 people/15min) and proximity to subway exits.",
            category=NodeCategory.OPERATIONS,
            dependencies=[]
        ))
        self.add_node(KnowledgeNode(
            id="mobile_payment_qr",
            content="Setup dual-platform mobile payment (WeChat/Alipay) with audio confirmation enabled.",
            category=NodeCategory.OPERATIONS,
            dependencies=[]
        ))

        # Finance Nodes
        self.add_node(KnowledgeNode(
            id="psychological_pricing",
            content="Implement '.99' pricing strategy or bundle pricing (e.g., 2 for 15 CNY) to increase perceived value.",
            category=NodeCategory.FINANCE,
            dependencies=["foot_traffic_analysis"]
        ))

        # Risk Control Nodes
        self.add_node(KnowledgeNode(
            id="urban_management_radar",
            content="Identify 'Chengguan' patrol patterns via local vendor chat groups; establish escape routes and code words.",
            category=NodeCategory.RISK_CONTROL,
            dependencies=[]
        ))
        self.add_node(KnowledgeNode(
            id="weather_contingency",
            content="Monitor hourly weather forecasts; prepare rain covers and waterproof inventory protection.",
            category=NodeCategory.RISK_CONTROL,
            dependencies=[]
        ))

    def add_node(self, node: KnowledgeNode):
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    def find_nodes_by_keywords(self, keywords: List[str]) -> List[KnowledgeNode]:
        """
        Simulates semantic search. 
        Returns nodes that semantically match the provided keywords.
        """
        matched_nodes = []
        # Simple keyword mapping for simulation purposes
        mapping = {
            "摆摊": ["wholesale_market_168", "mobile_payment_qr"],
            "选址": ["foot_traffic_analysis", "urban_management_radar"],
            "定价": ["psychological_pricing"],
            "进货": ["wholesale_market_168", "inventory_buffer"]
        }
        
        target_ids: Set[str] = set()
        for kw in keywords:
            if kw in mapping:
                target_ids.update(mapping[kw])
        
        for nid in target_ids:
            node = self.get_node(nid)
            if node:
                matched_nodes.append(node)
        
        logger.info(f"Semantic search found {len(matched_nodes)} nodes for keywords: {keywords}")
        return matched_nodes

    def resolve_dependencies(self, initial_nodes: List[KnowledgeNode]) -> List[KnowledgeNode]:
        """
        Bottom-up induction core: Finds missing logical dependencies to ensure structural integrity.
        """
        resolved_map: Dict[str, KnowledgeNode] = {n.id: n for n in initial_nodes}
        queue = list(initial_nodes)
        
        while queue:
            current_node = queue.pop(0)
            for dep_id in current_node.dependencies:
                if dep_id not in resolved_map:
                    dep_node = self.get_node(dep_id)
                    if dep_node:
                        resolved_map[dep_id] = dep_node
                        queue.append(dep_node)
                        logger.debug(f"Induced hidden node: {dep_id} required by {current_node.id}")
        
        return list(resolved_map.values())

class BusinessPlanner:
    """
    Core Logic: Constructs a structured business plan from scattered data points.
    """
    
    def __init__(self, knowledge_base: KnowledgeGraph):
        self.kb = knowledge_base

    def _validate_input(self, keywords: List[str]) -> bool:
        """Validates that keywords are not empty and contain valid strings."""
        if not keywords:
            logger.error("Input validation failed: Keywords list is empty.")
            raise ValueError("Keywords list cannot be empty.")
        if not all(isinstance(k, str) and k.strip() for k in keywords):
            logger.error("Input validation failed: Invalid keyword types.")
            raise TypeError("All keywords must be non-empty strings.")
        return True

    def generate_plan(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        Generates a structured business plan based on keywords.
        
        Args:
            keywords: A list of loose keywords (e.g., ['摆摊', '选址']).
            
        Returns:
            A dictionary categorized by NodeCategory containing the plan steps.
            
        Raises:
            ValueError: If input is invalid.
        """
        try:
            self._validate_input(keywords)
            
            # Step 1: Retrieve initial "Real Nodes" via semantic search
            initial_nodes = self.kb.find_nodes_by_keywords(keywords)
            
            if not initial_nodes:
                logger.warning("No relevant nodes found for the given keywords.")
                return {}

            # Step 2: Bottom-up Induction - Fill in the gaps
            # AI realizes that to "Select Location" (Ops), one must consider "Urban Management" (Risk)
            complete_nodes = self.kb.resolve_dependencies(initial_nodes)
            
            # Step 3: Structure the output
            structured_plan: Dict[str, List[str]] = {}
            
            for node in complete_nodes:
                cat_name = node.category.value
                if cat_name not in structured_plan:
                    structured_plan[cat_name] = []
                
                structured_plan[cat_name].append(f"[{node.id}] {node.content}")
            
            logger.info(f"Plan generation complete. Total nodes: {len(complete_nodes)}")
            return structured_plan

        except Exception as e:
            logger.exception("Failed to generate business plan.")
            raise

def format_plan_output(plan: Dict[str, List[str]]) -> str:
    """
    Helper function to format the dictionary plan into a readable report string.
    """
    if not plan:
        return "No viable business plan could be constructed."
    
    output_lines = ["="*40, "AGI Generated Business Execution Plan", "="*40, ""]
    
    # Define order of importance for the report
    category_order = [
        NodeCategory.SUPPLY_CHAIN.value,
        NodeCategory.OPERATIONS.value,
        NodeCategory.FINANCE.value,
        NodeCategory.MARKETING.value,
        NodeCategory.RISK_CONTROL.value
    ]
    
    for category in category_order:
        if category in plan:
            output_lines.append(f"## {category.upper().replace('_', ' ')}")
            for idx, item in enumerate(plan[category], 1):
                output_lines.append(f"  {idx}. {item}")
            output_lines.append("") # Empty line for spacing
            
    return "\n".join(output_lines)

# Main Execution Block
if __name__ == "__main__":
    # Initialize the Knowledge Graph
    kb = KnowledgeGraph()
    
    # Initialize the Planner Agent
    planner = BusinessPlanner(kb)
    
    # Input: Scattered Keywords (The "Prompt")
    input_keywords = ["摆摊", "选址"]
    
    print(f"Input Keywords: {input_keywords}\n")
    
    try:
        # Generate the structured logic
        raw_plan = planner.generate_plan(input_keywords)
        
        # Format for human reading
        readable_plan = format_plan_output(raw_plan)
        print(readable_plan)
        
    except ValueError as ve:
        print(f"Input Error: {ve}")
    except Exception as e:
        print(f"System Error: {e}")