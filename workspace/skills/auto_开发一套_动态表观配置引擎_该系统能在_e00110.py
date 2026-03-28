"""
Module: dynamic_epigenetic_engine
A dynamic epigenetic configuration engine that enables real-time module control 
through digital methylation markers, with adaptive evolution capabilities.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from copy import deepcopy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EpigeneticEngine")


class MethylMarkType(Enum):
    """Types of digital methylation markers"""
    ACTIVATOR = auto()  # Turns on module
    SUPPRESSOR = auto()  # Turns off module
    ADAPTIVE = auto()  # Environment-adaptive marker


@dataclass
class MicroserviceModule:
    """Represents a microservice module in the system"""
    name: str
    is_active: bool = True
    load_factor: float = 0.0
    adaptation_score: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert module to dictionary representation"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MicroserviceModule':
        """Create module from dictionary"""
        return cls(**data)


@dataclass
class MethylMark:
    """Digital methylation marker that controls module behavior"""
    target_module: str
    mark_type: MethylMarkType
    strength: float = 1.0
    duration: float = 0.0  # 0 for permanent
    created_at: float = field(default_factory=time.time)
    environment_trigger: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if marker has expired"""
        if self.duration == 0:
            return False
        return (time.time() - self.created_at) > self.duration

    def to_dict(self) -> Dict[str, Any]:
        """Convert marker to dictionary"""
        return {
            "target_module": self.target_module,
            "mark_type": self.mark_type.name,
            "strength": self.strength,
            "duration": self.duration,
            "created_at": self.created_at,
            "environment_trigger": self.environment_trigger
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MethylMark':
        """Create marker from dictionary"""
        data["mark_type"] = MethylMarkType[data["mark_type"]]
        return cls(**data)


class EpigeneticEngine:
    """
    Dynamic epigenetic configuration engine that manages microservice modules
    through digital methylation markers with adaptive evolution capabilities.
    """

    def __init__(self):
        """Initialize the epigenetic engine"""
        self.modules: Dict[str, MicroserviceModule] = {}
        self.marks: List[MethylMark] = []
        self.adaptation_history: List[Dict[str, Any]] = []
        self._initialize_core_modules()

    def _initialize_core_modules(self) -> None:
        """Initialize core system modules"""
        core_modules = [
            "auth", "database", "api_gateway", "cache", "logger",
            "scheduler", "messaging", "storage", "compute", "network"
        ]
        for name in core_modules:
            self.modules[name] = MicroserviceModule(name=name)
        logger.info("Initialized core system modules")

    def apply_methyl_mark(self, mark: MethylMark) -> bool:
        """
        Apply a digital methylation mark to control module behavior.
        
        Args:
            mark: The methylation marker to apply
            
        Returns:
            bool: True if mark was applied successfully
            
        Raises:
            ValueError: If target module doesn't exist
        """
        if mark.target_module not in self.modules:
            logger.error(f"Module {mark.target_module} not found")
            raise ValueError(f"Module {mark.target_module} does not exist")

        # Validate strength value
        if not 0 <= mark.strength <= 1:
            logger.error(f"Invalid mark strength: {mark.strength}")
            raise ValueError("Mark strength must be between 0 and 1")

        # Remove expired marks before applying new one
        self._cleanup_expired_marks()

        # Apply the mark
        self.marks.append(mark)
        self._update_module_state(mark.target_module)
        
        logger.info(f"Applied {mark.mark_type.name} mark to {mark.target_module}")
        return True

    def _update_module_state(self, module_name: str) -> None:
        """Update module state based on active methylation marks"""
        if module_name not in self.modules:
            return

        module = self.modules[module_name]
        active_marks = [m for m in self.marks 
                       if m.target_module == module_name and not m.is_expired()]

        if not active_marks:
            return

        # Calculate net activation effect
        net_effect = 0.0
        for mark in active_marks:
            if mark.mark_type == MethylMarkType.ACTIVATOR:
                net_effect += mark.strength
            elif mark.mark_type == MethylMarkType.SUPPRESSOR:
                net_effect -= mark.strength
            elif mark.mark_type == MethylMarkType.ADAPTIVE:
                # Adaptive marks respond to environment
                net_effect += mark.strength * self._get_environment_factor()

        # Update module state
        module.is_active = net_effect > 0
        module.last_updated = time.time()
        
        logger.debug(f"Updated {module_name} state: active={module.is_active}")

    def _get_environment_factor(self) -> float:
        """Calculate current environment factor (simulated)"""
        # In a real system, this would integrate with monitoring tools
        return 0.5  # Default neutral factor

    def _cleanup_expired_marks(self) -> None:
        """Remove expired methylation marks"""
        initial_count = len(self.marks)
        self.marks = [m for m in self.marks if not m.is_expired()]
        removed = initial_count - len(self.marks)
        
        if removed > 0:
            logger.debug(f"Removed {removed} expired marks")

    def add_adaptation_record(self, module_name: str, 
                            environment_factor: float,
                            performance_delta: float) -> None:
        """
        Record an adaptation event for evolutionary learning.
        
        Args:
            module_name: Name of the module being adapted
            environment_factor: Current environment factor
            performance_delta: Change in performance metrics
        """
        if module_name not in self.modules:
            logger.warning(f"Attempt to record adaptation for unknown module {module_name}")
            return

        record = {
            "module": module_name,
            "timestamp": time.time(),
            "environment_factor": environment_factor,
            "performance_delta": performance_delta,
            "state": self.modules[module_name].to_dict()
        }
        
        self.adaptation_history.append(record)
        
        # Update module adaptation score
        module = self.modules[module_name]
        module.adaptation_score += performance_delta * 0.1
        
        logger.info(f"Recorded adaptation for {module_name}: delta={performance_delta:.2f}")

    def get_epigenetic_state(self) -> Dict[str, Any]:
        """
        Get current epigenetic state of the system.
        
        Returns:
            Dict containing all modules, marks and adaptation history
        """
        return {
            "modules": {name: module.to_dict() for name, module in self.modules.items()},
            "marks": [mark.to_dict() for mark in self.marks],
            "adaptation_history": self.adaptation_history[-10:],  # Last 10 records
            "timestamp": time.time()
        }

    def inherit_state(self, parent_state: Dict[str, Any], 
                     inheritance_factor: float = 0.7) -> None:
        """
        Inherit epigenetic state from a parent system (evolutionary inheritance).
        
        Args:
            parent_state: State dictionary from parent system
            inheritance_factor: Fraction of state to inherit (0-1)
            
        Raises:
            ValueError: If inheritance factor is out of range
        """
        if not 0 <= inheritance_factor <= 1:
            raise ValueError("Inheritance factor must be between 0 and 1")

        # Inherit modules state
        for name, state in parent_state.get("modules", {}).items():
            if name in self.modules and inheritance_factor > 0.5:
                module = self.modules[name]
                # Inherit adaptation score
                module.adaptation_score = state.get("adaptation_score", 0) * inheritance_factor
                
                # Inherit active state with some randomness
                if inheritance_factor > 0.7:
                    module.is_active = state.get("is_active", True)

        # Inherit some methylation marks
        for mark_data in parent_state.get("marks", []):
            mark = MethylMark.from_dict(mark_data)
            # Only inherit non-expired marks with some probability
            if not mark.is_expired() and (inheritance_factor + 0.1) > 0.5:
                self.marks.append(mark)

        logger.info(f"Inherited epigenetic state with factor {inheritance_factor:.2f}")

    def adapt_to_environment(self, environment_data: Dict[str, float]) -> None:
        """
        Automatically adapt to environmental conditions by applying adaptive marks.
        
        Args:
            environment_data: Dictionary of environmental metrics (e.g., {"cpu_load": 0.9})
        """
        for module_name, module in self.modules.items():
            # Calculate environment pressure
            pressure = self._calculate_environment_pressure(environment_data, module_name)
            
            if pressure > 0.7:  # High pressure
                # Apply adaptive mark to optimize
                mark = MethylMark(
                    target_module=module_name,
                    mark_type=MethylMarkType.ADAPTIVE,
                    strength=pressure,
                    duration=300,  # 5 minutes
                    environment_trigger="high_load"
                )
                self.apply_methyl_mark(mark)
                
                # Record adaptation
                self.add_adaptation_record(
                    module_name=module_name,
                    environment_factor=pressure,
                    performance_delta=0.1  # Simulated improvement
                )

    def _calculate_environment_pressure(self, env_data: Dict[str, float], 
                                      module_name: str) -> float:
        """Calculate environment pressure for a specific module"""
        # Module-specific pressure calculation (simplified for example)
        if module_name == "compute":
            return env_data.get("cpu_load", 0.0)
        elif module_name == "database":
            return env_data.get("db_connections", 0.0) / 100
        elif module_name == "cache":
            return env_data.get("cache_miss_rate", 0.0)
        return 0.0

    def save_state(self, filepath: str) -> None:
        """Save current epigenetic state to file"""
        state = self.get_epigenetic_state()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved epigenetic state to {filepath}")

    def load_state(self, filepath: str) -> None:
        """Load epigenetic state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Clear current state
        self.modules.clear()
        self.marks.clear()
        
        # Load modules
        for name, data in state.get("modules", {}).items():
            self.modules[name] = MicroserviceModule.from_dict(data)
        
        # Load marks
        for mark_data in state.get("marks", []):
            self.marks.append(MethylMark.from_dict(mark_data))
        
        logger.info(f"Loaded epigenetic state from {filepath}")


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = EpigeneticEngine()
    
    # Apply some methylation marks
    try:
        # Activate the cache module
        engine.apply_methyl_mark(MethylMark(
            target_module="cache",
            mark_type=MethylMarkType.ACTIVATOR,
            strength=0.8
        ))
        
        # Suppress the logger module temporarily
        engine.apply_methyl_mark(MethylMark(
            target_module="logger",
            mark_type=MethylMarkType.SUPPRESSOR,
            strength=0.6,
            duration=60  # 1 minute
        ))
        
        # Simulate environment adaptation
        env_data = {
            "cpu_load": 0.85,
            "db_connections": 120,
            "cache_miss_rate": 0.15
        }
        engine.adapt_to_environment(env_data)
        
        # Print current state
        print("Current Epigenetic State:")
        print(json.dumps(engine.get_epigenetic_state(), indent=2))
        
    except ValueError as e:
        logger.error(f"Error: {e}")