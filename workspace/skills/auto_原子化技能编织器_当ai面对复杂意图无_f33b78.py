"""
原子化技能编织器

本模块实现了AGI系统中的'学徒模式'，用于处理复杂意图。它将复杂的编程意图
拆解为最小的原子操作（如'定义变量'、'读取文件'），逐个验证这些原子节点，
确认无误后再像编织竹篮一样组合成复杂功能，从而降低幻觉的发生率。

核心 metaphor:
    选材 -> 切割 -> 编织 -> 验收
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AtomicSkillWeaver")

class AtomState(Enum):
    """原子节点状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    VALIDATED = "validated"
    FAILED = "failed"

@dataclass
class AtomNode:
    """
    原子节点数据结构。
    
    Attributes:
        name (str): 节点名称
        action_type (str): 动作类型（如 'variable', 'read', 'compute'）
        parameters (Dict[str, Any]): 执行参数
        dependencies (List[str]): 依赖的节点ID列表
        state (AtomState): 当前状态
        result (Optional[Any]): 执行结果
    """
    name: str
    action_type: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    state: AtomState = AtomState.PENDING
    result: Optional[Any] = None

class AtomicWeaver:
    """
    原子化技能编织器核心类。
    
    负责管理原子节点的生命周期，验证依赖关系，并按拓扑顺序执行验证。
    
    Usage Example:
        >>> weaver = AtomicWeaver()
        >>> intent = "读取包含用户数据的JSON文件并计算平均年龄"
        >>> weaver.decompose_intent(intent)
        >>> result = weaver.weave()
        >>> print(f"Final Result: {result}")
    """
    
    def __init__(self):
        self.atoms: Dict[str, AtomNode] = {}
        self.context: Dict[str, Any] = {}  # 用于存储编织过程中的中间变量
        self._action_handlers: Dict[str, Callable] = {
            'define_var': self._handle_define_var,
            'read_file': self._handle_read_file,
            'compute': self._handle_compute,
            'transform': self._handle_transform
        }
        logger.info("AtomicWeaver initialized in Apprentice Mode.")

    def decompose_intent(self, complex_intent: str) -> None:
        """
        【选材与切割】
        将复杂意图拆解为原子节点序列。
        
        注意：此处使用模拟逻辑演示。在真实AGI场景中，这里会接入LLM进行规划。
        
        Args:
            complex_intent (str): 用户的复杂自然语言意图
        """
        logger.info(f"Received complex intent: '{complex_intent}'")
        # 模拟意图拆解过程
        # 假设意图是："读取data.json，计算所有用户的平均年龄"
        
        # 原子1: 定义数据源路径
        atom1 = AtomNode(
            name="DefineDataSource",
            action_type="define_var",
            parameters={"var_name": "file_path", "value": "data.json"}
        )
        
        # 原子2: 读取文件内容
        atom2 = AtomNode(
            name="ReadUserData",
            action_type="read_file",
            parameters={"path_var": "file_path"},
            dependencies=["DefineDataSource"]
        )
        
        # 原子3: 数据转换与计算
        atom3 = AtomNode(
            name="CalculateAverage",
            action_type="compute",
            parameters={"operation": "average", "field": "age"},
            dependencies=["ReadUserData"]
        )
        
        self.add_atom(atom1)
        self.add_atom(atom2)
        self.add_atom(atom3)
        
        logger.info(f"Decomposed intent into {len(self.atoms)} atomic nodes.")

    def add_atom(self, atom: AtomNode) -> None:
        """
        添加原子节点到编织器，并进行基础数据验证。
        
        Args:
            atom (AtomNode): 待添加的原子节点
        """
        if not atom.name or not atom.action_type:
            raise ValueError("Atom must have a name and action_type")
        
        if atom.name in self.atoms:
            logger.warning(f"Overwriting existing atom: {atom.name}")
            
        self.atoms[atom.name] = atom
        logger.debug(f"Atom added: {atom.name}")

    def validate_dependencies(self) -> bool:
        """
        【编织前检查】
        验证所有原子节点的依赖关系是否满足（无环且依赖存在）。
        
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        visited = set()
        recursion_stack = set()
        
        def has_cycle(node_name: str) -> bool:
            visited.add(node_name)
            recursion_stack.add(node_name)
            
            node = self.atoms.get(node_name)
            if not node:
                logger.error(f"Dependency validation failed: Missing node {node_name}")
                return True

            for dep in node.dependencies:
                if dep not in self.atoms:
                    logger.error(f"Dependency '{dep}' for node '{node_name}' does not exist.")
                    return True
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in recursion_stack:
                    logger.error("Circular dependency detected!")
                    return True
            
            recursion_stack.remove(node_name)
            return False

        for name in self.atoms:
            if name not in visited:
                if has_cycle(name):
                    return False
        
        logger.info("Dependency graph validated successfully (DAG confirmed).")
        return True

    def weave(self) -> Dict[str, Any]:
        """
        【编织与验收】
        按拓扑顺序执行原子节点，模拟编织过程。
        
        Returns:
            Dict[str, Any]: 包含最终执行结果的字典
        """
        if not self.validate_dependencies():
            return {"status": "error", "message": "Invalid dependencies"}

        execution_order = self._get_execution_order()
        logger.info(f"Starting weave sequence: {' -> '.join(execution_order)}")

        for node_name in execution_order:
            node = self.atoms[node_name]
            node.state = AtomState.RUNNING
            
            try:
                handler = self._action_handlers.get(node.action_type)
                if not handler:
                    raise ValueError(f"No handler for action type: {node.action_type}")
                
                # 执行原子操作
                logger.info(f"Executing atom: {node_name} ({node.action_type})")
                result = handler(node.parameters)
                
                node.result = result
                node.state = AtomState.VALIDATED
                logger.info(f"Atom {node_name} validated. Result stored.")
                
            except Exception as e:
                node.state = AtomState.FAILED
                logger.error(f"Atom {node_name} failed: {str(e)}")
                return {"status": "failed", "failed_at": node_name, "error": str(e)}

        return {
            "status": "success",
            "context": self.context,
            "final_result": list(self.atoms.values())[-1].result
        }

    def _get_execution_order(self) -> List[str]:
        """辅助函数：拓扑排序"""
        in_degree = {name: 0 for name in self.atoms}
        graph = {name: [] for name in self.atoms}
        
        for name, node in self.atoms.items():
            for dep in node.dependencies:
                graph[dep].append(name)
                in_degree[name] += 1
                
        queue = [n for n, d in in_degree.items() if d == 0]
        sorted_order = []
        
        while queue:
            u = queue.pop(0)
            sorted_order.append(u)
            for v in graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        return sorted_order

    # --- 原子操作处理器 ---
    
    def _handle_define_var(self, params: Dict[str, Any]) -> Any:
        """原子操作：定义变量"""
        var_name = params.get("var_name")
        value = params.get("value")
        if not var_name:
            raise ValueError("Missing 'var_name' in define_var")
        
        # 边界检查：防止覆盖系统关键变量
        if var_name.startswith("__"):
            raise PermissionError("Cannot overwrite system variables")
            
        self.context[var_name] = value
        return value

    def _handle_read_file(self, params: Dict[str, Any]) -> Any:
        """原子操作：读取文件（模拟）"""
        path_var = params.get("path_var")
        file_path = self.context.get(path_var)
        
        if not file_path:
            raise ValueError(f"Context variable '{path_var}' not found")
        
        logger.info(f"Simulating reading file: {file_path}")
        # 模拟数据返回，实际场景会使用 open()
        mock_data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 24},
            {"name": "Charlie", "age": 29}
        ]
        return mock_data

    def _handle_compute(self, params: Dict[str, Any]) -> Any:
        """原子操作：计算"""
        operation = params.get("operation")
        field_name = params.get("field")
        
        # 获取上一个节点的数据（这里简化处理，实际应从context或特定依赖获取）
        # 假设上一个节点的结果存储在 context['ReadUserData_result'] (逻辑简化)
        data = self.atoms["ReadUserData"].result
        
        if not data or operation != "average":
            raise NotImplementedError("Only average operation is implemented in this demo")
            
        values = [item[field_name] for item in data if field_name in item]
        if not values:
            raise ValueError(f"No valid data for field {field_name}")
            
        return sum(values) / len(values)

    def _handle_transform(self, params: Dict[str, Any]) -> Any:
        """原子操作：数据转换（占位符）"""
        pass

# 主程序入口示例
if __name__ == "__main__":
    # 创建编织器实例
    weaver = AtomicWeaver()
    
    # 定义复杂意图
    intent = "读取data.json并计算平均年龄"
    
    try:
        # 1. 拆解
        weaver.decompose_intent(intent)
        
        # 2. 编织执行
        result = weaver.weave()
        
        # 3. 输出结果
        print("\n=== Weaver Execution Report ===")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        logger.critical(f"System failure during weaving: {e}")