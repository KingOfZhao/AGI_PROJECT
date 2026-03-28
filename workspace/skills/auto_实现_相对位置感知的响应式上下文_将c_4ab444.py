"""
名称: auto_实现_相对位置感知的响应式上下文_将c_4ab444
描述: 实现'相对位置感知的响应式上下文'。将CAD的UCS概念抽象化，用于Flutter的深层次Widget树。
当前Widget只继承逻辑数据，新能力让它继承'计算环境'（如当前处于哪个步骤、相对父节点的逻辑位置）。
这使得开发'位置敏感'的业务逻辑成为可能（例如：表格中某一行的删除按钮，自动获知自己在'第N行'这个坐标系信息，无需显式传参）。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from functools import wraps
import json

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PositionalContext:
    """
    位置感知上下文数据结构。
    模拟Flutter中的InheritedWidget携带的数据负载。
    
    Attributes:
        path (List[str]): 从根节点到当前节点的路径ID列表 (类比CAD中的坐标轴)
        depth (int): 当前节点在树中的深度
        metadata (Dict[str, Any]): 随位置流动的计算环境变量 (类比UCS中的参数)
        parent_context (Optional['PositionalContext']): 父节点的上下文引用
    """
    path: List[str] = field(default_factory=list)
    depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_context: Optional['PositionalContext'] = field(default=None, repr=False)

    def get_ancestor_metadata(self, key: str) -> Optional[Any]:
        """向上遍历查找特定的元数据（类似CAD中的追踪参考线）"""
        current: Optional[PositionalContext] = self
        while current:
            if key in current.metadata:
                return current.metadata[key]
            current = current.parent_context
        return None

class ContextualTreeBuilder:
    """
    核心类：构建和管理响应式上下文树。
    实现了将CAD的UCS(用户坐标系)概念映射到Widget树的逻辑。
    """
    
    def __init__(self, root_id: str = "root"):
        self._root = PositionalContext(path=[root_id], depth=0)
        self._registry: Dict[str, PositionalContext] = {root_id: self._root}
        logger.info(f"Initialized Contextual Tree with root: {root_id}")

    def create_child_context(
        self, 
        parent_id: str, 
        child_id: str, 
        logic_data: Optional[Dict[str, Any]] = None
    ) -> PositionalContext:
        """
        核心函数1: 创建具有相对位置感知的子上下文。
        
        Args:
            parent_id (str): 父节点ID
            child_id (str): 当前节点ID
            logic_data (Optional[Dict]): 该层级特定的逻辑数据
            
        Returns:
            PositionalContext: 新创建的上下文对象
            
        Raises:
            ValueError: 如果父节点不存在
        """
        if parent_id not in self._registry:
            msg = f"Parent node {parent_id} not found in context tree."
            logger.error(msg)
            raise ValueError(msg)
            
        parent = self._registry[parent_id]
        
        # 计算新节点的相对位置信息
        new_path = parent.path + [child_id]
        new_depth = parent.depth + 1
        
        # 合并逻辑数据（这里模拟Flutter的BuildContext继承机制）
        new_context = PositionalContext(
            path=new_path,
            depth=new_depth,
            metadata=logic_data or {},
            parent_context=parent
        )
        
        self._registry[child_id] = new_context
        logger.debug(f"Created child context: {child_id} at depth {new_depth}")
        return new_context

    def get_context_by_id(self, node_id: str) -> Optional[PositionalContext]:
        """
        辅助函数: 根据ID获取上下文。
        """
        return self._registry.get(node_id)

    def execute_position_sensitive_logic(
        self, 
        node_id: str, 
        action_func: Callable[[PositionalContext, Dict], Any],
        extra_args: Optional[Dict] = None
    ) -> Any:
        """
        核心函数2: 执行位置敏感的业务逻辑。
        
        这模拟了Flutter中子Widget通过BuildContext获取祖先信息的机制。
        例如：表格行中的删除按钮自动获知自己在"第N行"。
        
        Args:
            node_id (str): 执行逻辑的节点ID
            action_func (Callable): 业务逻辑函数，接收context和extra_args
            extra_args (Optional[Dict]): 额外的参数
            
        Returns:
            Any: 业务逻辑的执行结果
            
        Raises:
            RuntimeError: 如果节点不存在或执行失败
        """
        if node_id not in self._registry:
            raise RuntimeError(f"Node {node_id} not found for execution.")
            
        context = self._registry[node_id]
        
        try:
            logger.info(f"Executing logic at node: {node_id}, Path: {' -> '.join(context.path)}")
            return action_func(context, extra_args or {})
        except Exception as e:
            logger.error(f"Failed to execute logic at {node_id}: {str(e)}")
            raise RuntimeError(f"Execution failed: {str(e)}") from e

def validate_tree_integrity(builder: ContextualTreeBuilder) -> bool:
    """
    数据验证与边界检查函数。
    检查树结构的完整性和路径一致性。
    """
    logger.info("Starting tree integrity validation...")
    for node_id, ctx in builder._registry.items():
        # 边界检查1: 路径末端必须与ID匹配
        if not ctx.path or ctx.path[-1] != node_id:
            logger.error(f"Integrity check failed: Path mismatch for {node_id}")
            return False
            
        # 边界检查2: 深度必须等于路径长度-1
        if ctx.depth != len(ctx.path) - 1:
            logger.error(f"Integrity check failed: Depth mismatch for {node_id}")
            return False
            
    logger.info("Tree integrity validation passed.")
    return True

# 使用示例
if __name__ == "__main__":
    # 模拟Flutter中的Widget树构建与上下文传递
    tree = ContextualTreeBuilder(root_id="AppRoot")
    
    # 构建层级结构：App -> Table -> Row -> DeleteButton
    table_ctx = tree.create_child_context("AppRoot", "DataTable", {"source": "users.db"})
    row1_ctx = tree.create_child_context("DataTable", "Row_1", {"index": 0, "id": "user_001"})
    row2_ctx = tree.create_child_context("DataTable", "Row_2", {"index": 1, "id": "user_002"})
    
    # 深层节点：删除按钮
    btn_ctx = tree.create_child_context("Row_1", "DeleteBtn_1", {"action": "delete"})
    
    # 验证数据
    is_valid = validate_tree_integrity(tree)
    print(f"Tree Valid: {is_valid}")
    
    # 定义位置敏感的业务逻辑（模拟Flutter中的事件处理）
    def handle_delete_button_click(context: PositionalContext, args: Dict) -> Dict:
        """
        业务逻辑：删除按钮不需要显式传入 'RowIndex'，
        而是直接从上下文环境中查询。
        """
        # 获取当前行的索引（向上查找父节点元数据）
        row_index = context.get_ancestor_metadata("index")
        table_source = context.get_ancestor_metadata("source")
        
        # 获取自身的路径信息
        logical_path = "/".join(context.path)
        
        return {
            "status": "success",
            "message": f"Deleting item from {table_source} at row {row_index}",
            "trigger_path": logical_path,
            "depth": context.depth
        }
    
    # 执行逻辑
    try:
        result = tree.execute_position_sensitive_logic(
            node_id="DeleteBtn_1",
            action_func=handle_delete_button_click
        )
        print("\n--- Execution Result ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")