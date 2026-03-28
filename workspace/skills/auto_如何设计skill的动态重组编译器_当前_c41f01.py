"""
Skill Dynamic Recombination Compiler Module

This module implements a Just-In-Time (JIT) compiler for an AGI system's Skill library.
It addresses the inefficiency of static skill invocation (currently 374 individual skills)
by enabling dynamic fusion of multiple granular skills into a temporary 'Macro Skill'
based on specific problem contexts.

Key Features:
- Dynamic dependency graph resolution.
- Runtime compilation of Python code objects.
- Context-aware input validation and injection.
- Comprehensive error handling and logging.

Author: Senior Python Engineer
Version: 1.0.0
"""

import ast
import inspect
import importlib
import logging
import time
import hashlib
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillJITCompiler")


@dataclass
class SkillMetadata:
    """Metadata container for a primitive Skill."""
    name: str
    description: str
    input_schema: Dict[str, str]  # e.g., {'text': 'str', 'data': 'List[int]'}
    output_type: str
    dependencies: List[str] = field(default_factory=list)
    func: Optional[Callable] = None  # The actual executable function

    def __hash__(self):
        return hash(self.name)


@dataclass
class ExecutionContext:
    """Context provided by the AGI system to determine skill selection."""
    user_query: str
    available_data: Dict[str, Any]
    required_capabilities: List[str]


class SkillRegistry:
    """
    Manages the repository of available primitive skills.
    Acts as the source of truth for the compiler.
    """
    def __init__(self):
        self._skills: Dict[str, SkillMetadata] = {}
        self._load_mock_skills()

    def _load_mock_skills(self):
        """Populates registry with mock skills for demonstration."""
        # Mock Skill 1
        def analyze_data(data: List[float]) -> Dict[str, float]:
            if not data: return {"mean": 0.0, "count": 0}
            return {"mean": sum(data) / len(data), "count": len(data)}

        # Mock Skill 2
        def sentiment_understanding(text: str) -> str:
            positive_words = {'good', 'great', 'excellent', 'happy'}
            words = set(text.lower().split())
            score = len(words.intersection(positive_words))
            return "positive" if score > 0 else "neutral"

        # Mock Skill 3
        def plot_chart(stats: Dict[str, float], sentiment: str) -> str:
            return f"Chart generated: Mean={stats['mean']:.2f}, Sentiment={sentiment}"

        self.register_skill(SkillMetadata(
            name="data_analysis", description="Calculates basic stats",
            input_schema={"data": "List[float]"}, output_type="Dict[str, float]",
            func=analyze_data
        ))
        self.register_skill(SkillMetadata(
            name="sentiment_understanding", description="Analyzes text sentiment",
            input_schema={"text": "str"}, output_type="str",
            func=sentiment_understanding
        ))
        self.register_skill(SkillMetadata(
            name="plotting", description="Visualizes data and context",
            input_schema={"stats": "Dict[str, float]", "sentiment": "str"}, output_type="str",
            func=plot_chart
        ))

    def register_skill(self, skill: SkillMetadata):
        self._skills[skill.name] = skill
        logger.debug(f"Registered skill: {skill.name}")

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        return self._skills.get(name)

    def find_skills_by_capabilities(self, capabilities: List[str]) -> List[str]:
        """
        Simple capability matcher.
        In a real AGI, this would use vector embeddings for semantic search.
        """
        matched = []
        for name, skill in self._skills.items():
            if any(cap.lower() in skill.description.lower() or cap.lower() == name.lower()
                   for cap in capabilities):
                matched.append(name)
        return matched


class DynamicRecombinationCompiler:
    """
    The core JIT compiler that fuses multiple skills into a Macro Skill.
    """

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._macro_cache: Dict[str, Callable] = {}
        logger.info("DynamicRecombinationCompiler initialized.")

    def _validate_inputs(self, skill: SkillMetadata, data_map: Dict[str, Any]) -> bool:
        """Validates input data against skill schema."""
        for param, p_type in skill.input_schema.items():
            if param not in data_map:
                logger.error(f"Missing input '{param}' for skill '{skill.name}'")
                return False
            # Basic runtime type checking (simplified)
            # In prod, use pydantic or similar
            actual_type = type(data_map[param]).__name__
            if actual_type != p_type and not (
                p_type == "List[float]" and isinstance(data_map[param], list)
                and all(isinstance(x, (int, float)) for x in data_map[param])
            ):
                logger.warning(
                    f"Type mismatch for {skill.name}.{param}: expected {p_type}, got {actual_type}"
                )
                # Allow continuation for demo purposes, but strict mode would fail here
        return True

    def _topological_sort(self, skill_names: List[str]) -> List[str]:
        """
        Resolves execution order based on data dependencies.
        This is a simplified heuristic sort. A real implementation requires
        analyzing input/output types of connected skills to build a DAG.
        """
        # For this demo, we assume the 'find_skills' returns them in roughly
        # discovery order, but we push 'plotting'/'output' skills to the end.
        # Heuristic: Skills with 'plot' or 'report' usually go last.
        prioritized = []
        sinks = []
        for name in skill_names:
            if 'plot' in name or 'report' in name or 'output' in name:
                sinks.append(name)
            else:
                prioritized.append(name)
        
        ordered = prioritized + sinks
        logger.info(f"Resolved execution order: {ordered}")
        return ordered

    def compile_macro_skill(self, context: ExecutionContext) -> Optional[Callable]:
        """
        Main Compilation Entry Point.
        Analyzes context, selects skills, orders them, and compiles a fused function.
        """
        cache_key = hashlib.md5(
            (context.user_query + str(context.required_capabilities)).encode()
        ).hexdigest()

        if cache_key in self._macro_cache:
            logger.info("Macro skill cache hit.")
            return self._macro_cache[cache_key]

        # 1. Skill Discovery
        target_skill_names = self.registry.find_skills_by_capabilities(
            context.required_capabilities
        )
        
        if len(target_skill_names) < 2:
            logger.warning("Insufficient skills found for recombination.")
            # Fallback or error handling logic
        
        # 2. Dependency Resolution & Ordering
        ordered_skills = self._topological_sort(target_skill_names)
        
        # 3. Code Generation / Fusion
        # We construct a wrapper function that chains the calls in memory
        def macro_skill_executor(**kwargs) -> Dict[str, Any]:
            """
            Dynamically generated Macro Skill.
            Handles data passing between sub-skills.
            """
            runtime_data = kwargs.copy()
            results_log = {}
            
            logger.info(f"Executing Macro Skill chain: {' -> '.join(ordered_skills)}")
            
            try:
                for skill_name in ordered_skills:
                    skill = self.registry.get_skill(skill_name)
                    if not skill:
                        raise RuntimeError(f"Skill {skill_name} not found during execution.")

                    # Prepare arguments for the current skill
                    # This logic maps available data (runtime_data) to skill inputs
                    call_args = {}
                    for param_name in skill.input_schema.keys():
                        if param_name in runtime_data:
                            call_args[param_name] = runtime_data[param_name]
                        else:
                            # Complex logic needed here to match outputs of prev skill to input of current
                            # For demo, we try to match by type or name heuristically
                            found = False
                            for k, v in runtime_data.items():
                                if k == param_name or param_name in k: # Fuzzy match
                                    call_args[param_name] = v
                                    found = True
                                    break
                            if not found:
                                raise ValueError(f"Cannot resolve parameter '{param_name}' for {skill_name}")

                    # Validate before execution
                    if not self._validate_inputs(skill, call_args):
                        raise ValueError(f"Validation failed for {skill_name}")

                    # Execute
                    start_t = time.perf_counter()
                    result = skill.func(**call_args)
                    duration = time.perf_counter() - start_t
                    
                    logger.debug(f"Skill {skill_name} executed in {duration:.4f}s")
                    
                    # Store result back to context for next skills
                    # We use the skill name or output type as key
                    result_key = f"{skill_name}_result"
                    runtime_data[result_key] = result
                    runtime_data[skill.output_type] = result # Type-based mapping
                    results_log[skill_name] = result

                return {
                    "status": "success",
                    "final_context": runtime_data,
                    "execution_trace": results_log
                }

            except Exception as e:
                logger.error(f"Error during Macro Skill execution: {str(e)}")
                return {"status": "error", "message": str(e)}

        # 4. Caching
        self._macro_cache[cache_key] = macro_skill_executor
        logger.info(f"Compiled new Macro Skill for context: {context.user_query[:30]}...")
        return macro_skill_executor


# --- Usage Example ---

if __name__ == "__main__":
    # 1. Setup System
    registry = SkillRegistry()
    compiler = DynamicRecombinationCompiler(registry)

    # 2. Define User Context
    # User wants to analyze numeric data and combine it with text sentiment to plot a chart
    context = ExecutionContext(
        user_query="Analyze this sales data and customer feedback, then plot a combined chart.",
        required_capabilities=["data analysis", "sentiment understanding", "plotting"],
        available_data={
            "data": [100.5, 200.0, 150.0, 300.5],
            "text": "The sales were good but the process was slow."
        }
    )

    # 3. Compile Macro Skill (JIT)
    macro_skill = compiler.compile_macro_skill(context)

    if macro_skill:
        print("\n--- Executing Dynamic Macro Skill ---")
        # 4. Execute with specific data
        result = macro_skill(
            data=context.available_data["data"],
            text=context.available_data["text"]
        )
        
        print("\n--- Execution Result ---")
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Failed to compile macro skill.")