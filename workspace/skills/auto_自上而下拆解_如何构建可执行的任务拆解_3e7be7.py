"""
Module: auto_top_down_decomposition
Description: Implements an executable task decomposition engine for AGI systems.
             It transforms high-level 'Real Nodes' (goals) into directed acyclic
             graphs of atomic SKILLs, verifying I/O compatibility.

Author: Senior Python Engineer
Domain: Software Engineering / AGI Planning
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel, Field, ValidationError
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Data Models ---

class SkillType(str, Enum):
    """Enumeration defining the type of the node."""
    ATOMIC = "ATOMIC"   # Cannot be decomposed further
    ABSTRACT = "ABSTRACT" # High-level goal needing decomposition

class DataSchema(BaseModel):
    """Represents the data format for inputs and outputs."""
    type: str = Field(..., description="The semantic type of the data, e.g., 'RawIngredients', 'CutVegetables'")
    format: str = Field("json", description="Technical format, e.g., json, binary, stream")

class Skill(BaseModel):
    """Represents an atomic or abstract capability in the AGI system."""
    id: str
    name: str
    type: SkillType
    input_schema: List[DataSchema] = Field(default_factory=list)
    output_schema: List[DataSchema] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list, description="List of prerequisite Skill IDs")

class DecompositionRule(BaseModel):
    """Mapping from an abstract node to a sequence of sub-skills."""
    target_node_id: str
    sub_skill_sequence: List[str]

class TaskGraph(BaseModel):
    """Represents the execution plan."""
    root_goal: str
    nodes: Dict[str, Skill] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)

# --- Decomposition Engine ---

class DecompositionEngine:
    """
    Core engine responsible for decomposing high-level goals into executable skill graphs.
    It ensures semantic validity and I/O compatibility between connected skills.
    """

    def __init__(self, skill_registry: Dict[str, Skill], rule_set: Dict[str, List[str]]):
        """
        Initialize the engine with a registry of available skills and decomposition rules.
        
        Args:
            skill_registry (Dict[str, Skill]): A dictionary containing all atomic and abstract skills.
            rule_set (Dict[str, List[str]]): Rules mapping abstract skill IDs to lists of sub-skill IDs.
        """
        self.skill_registry = skill_registry
        self.rule_set = rule_set
        logger.info("DecompositionEngine initialized with %d skills.", len(skill_registry))

    def _verify_io_compatibility(self, producer: Skill, consumer: Skill) -> bool:
        """
        Helper function: Validates if the output of the producer skill satisfies the input of the consumer.
        
        Args:
            producer (Skill): The skill producing data.
            consumer (Skill): The skill consuming data.
            
        Returns:
            bool: True if compatible, False otherwise.
        """
        if not consumer.input_schema:
            return True # No input required

        # Simple matching logic: Check if consumer input types exist in producer output types
        # In a real AGI system, this would involve ontological reasoning or vector similarity
        producer_outputs = {out.type for out in producer.output_schema}
        consumer_inputs = {inp.type for inp in consumer.input_schema}
        
        is_compatible = consumer_inputs.issubset(producer_outputs)
        
        if not is_compatible:
            logger.warning(
                f"I/O Mismatch: {producer.name} outputs {producer_outputs}, "
                f"but {consumer.name} requires {consumer_inputs}"
            )
        return is_compatible

    def _decompose_node(self, node: Skill) -> List[Skill]:
        """
        Attempts to decompose a single Abstract node into a sequence of skills.
        Validates the I/O chain of the resulting sequence.
        
        Args:
            node (Skill): The abstract node to decompose.
            
        Returns:
            List[Skill]: A list of executable/semi-executable skills.
        
        Raises:
            ValueError: If no rule exists or I/O validation fails.
        """
        if node.type == SkillType.ATOMIC:
            return [node]

        if node.id not in self.rule_set:
            raise ValueError(f"No decomposition rule found for abstract node: {node.id} ({node.name})")

        sub_skill_ids = self.rule_set[node.id]
        sub_skills = []
        
        # Fetch skills
        for skill_id in sub_skill_ids:
            if skill_id not in self.skill_registry:
                raise ValueError(f"Missing Skill in registry: {skill_id} required by rule for {node.id}")
            sub_skills.append(self.skill_registry[skill_id])

        # Validate Pipeline Integrity
        for i in range(len(sub_skills) - 1):
            current_skill = sub_skills[i]
            next_skill = sub_skills[i+1]
            
            if not self._verify_io_compatibility(current_skill, next_skill):
                raise ValueError(
                    f"Pipeline broken between {current_skill.id} and {next_skill.id} "
                    f"for target {node.id}"
                )
        
        logger.info(f"Successfully decomposed {node.name} into {[s.name for s in sub_skills]}")
        return sub_skills

    def build_execution_graph(self, root_goal_id: str) -> TaskGraph:
        """
        Main Entry Point: Builds a complete execution graph from a root goal using BFS.
        
        Args:
            root_goal_id (str): The ID of the high-level goal skill.
            
        Returns:
            TaskGraph: The fully resolved graph with execution order.
        """
        if root_goal_id not in self.skill_registry:
            raise ValueError(f"Root goal {root_goal_id} not found in registry.")

        graph = TaskGraph(root_goal=root_goal_id)
        queue = deque([self.skill_registry[root_goal_id]])
        
        # We need to handle expansion carefully to maintain order
        # This simplified example flattens the structure into a linear execution flow 
        # for the 'execution_order', while 'nodes' holds the unique definitions.
        
        processed_nodes: Set[str] = set()
        
        while queue:
            current_node = queue.popleft()
            
            if current_node.id in processed_nodes:
                continue
                
            try:
                # Try to decompose
                decomposed_parts = self._decompose_node(current_node)
                
                if len(decomposed_parts) > 1 or decomposed_parts[0].id != current_node.id:
                    # It was decomposed. Add new parts to queue to check if they need further decomposition.
                    # Remove the abstract node from final execution, replace with parts.
                    for part in decomposed_parts:
                        if part.id not in processed_nodes:
                            queue.append(part)
                            graph.nodes[part.id] = part
                else:
                    # It is atomic
                    graph.nodes[current_node.id] = current_node
                    processed_nodes.add(current_node.id)
                    
            except ValueError as e:
                logger.error(f"Decomposition failed for {current_node.id}: {e}")
                raise

        # Calculate execution order (Topological Sort logic simplified for this context)
        # Here we just list them in valid dependency order assuming the decomposition rules provide a sequence
        graph.execution_order = self._topological_sort(graph.nodes)
        
        logger.info(f"Task Graph built successfully with {len(graph.execution_order)} steps.")
        return graph

    def _topological_sort(self, nodes: Dict[str, Skill]) -> List[str]:
        """
        Helper: Performs a topological sort on the graph nodes based on dependencies.
        """
        # Simplified implementation for this context
        # Assuming a linear dependency chain derived from the decomposition for this snippet
        # In a full system, this would use Kahn's algorithm on a DAG structure
        
        visited = []
        # This is a placeholder logic for a complex graph sort
        # We just return keys assuming they were added in a semi-ordered fashion or independent
        return list(nodes.keys())

# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup Data
    skills_db = {
        "GOAL_DINNER": Skill(
            id="GOAL_DINNER", name="Cook Dinner", type=SkillType.ABSTRACT,
            input_schema=[DataSchema(type="Hunger")], output_schema=[DataSchema(type="Meal")]
        ),
        "SKILL_SHOP": Skill(
            id="SKILL_SHOP", name="Buy Groceries", type=SkillType.ATOMIC,
            input_schema=[DataSchema(type="Hunger")], output_schema=[DataSchema(type="RawIngredients")]
        ),
        "SKILL_PREP": Skill(
            id="SKILL_PREP", name="Prepare Ingredients", type=SkillType.ATOMIC,
            input_schema=[DataSchema(type="RawIngredients")], output_schema=[DataSchema(type="CutIngredients")]
        ),
        "SKILL_COOK": Skill(
            id="SKILL_COOK", name="Cook Food", type=SkillType.ATOMIC,
            input_schema=[DataSchema(type="CutIngredients")], output_schema=[DataSchema(type="Meal")]
        )
    }

    # Rules: GOAL_DINNER -> SHOP -> PREP -> COOK
    rules_db = {
        "GOAL_DINNER": ["SKILL_SHOP", "SKILL_PREP", "SKILL_COOK"]
    }

    # 2. Initialize Engine
    engine = DecompositionEngine(skill_registry=skills_db, rule_set=rules_db)

    try:
        # 3. Execute Decomposition
        plan = engine.build_execution_graph("GOAL_DINNER")
        
        print("\n--- Execution Plan Generated ---")
        print(f"Root Goal: {plan.root_goal}")
        print("Steps:")
        for step_id in plan.execution_order:
            skill = plan.nodes[step_id]
            print(f" - [{skill.type}] {skill.name} (ID: {skill.id})")
            print(f"    Input: {[s.type for s in skill.input_schema]}")
            print(f"    Output: {[s.type for s in skill.output_schema]}")
            
    except Exception as e:
        print(f"Critical Failure: {e}")