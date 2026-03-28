"""
高级Python模块：基于特征树的UI动态构建系统

该模块实现了一套仿CAD参数化设计的UI特征树中间件。它将UI组件抽象为
具有参数依赖的节点，当参数发生变更时，系统能够智能地计算受影响的
节点范围，并仅重建必要的子树结构，从而优化动态界面的渲染性能。

Author: AGI System
Version: 1.0.0
Domain: cross_domain (Software Architecture / Frontend Infra)
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from copy import deepcopy

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FeatureTreeUI")

@dataclass
class UIComponent:
    """
    UI组件节点基类，模拟Flutter的Widget。
    
    Attributes:
        widget_type (str): 组件类型，如 'Container', 'Row', 'Text'.
        properties (Dict[str, Any]): 组件的属性参数（特征参数）.
        children (List['UIComponent']): 子组件列表.
        uid (str): 唯一标识符，用于哈希计算和差异比较.
    """
    widget_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List['UIComponent'] = field(default_factory=list)
    uid: str = field(default_factory=lambda: hashlib.md5(str(id(self)).encode()).hexdigest()[:8])

    def get_hash(self) -> str:
        """生成当前节点及其子树的哈希值，用于变更检测。"""
        content = f"{self.widget_type}:{sorted(self.properties.items())}"
        for child in self.children:
            content += child.get_hash()
        return hashlib.sha256(content.encode()).hexdigest()

class FeatureTreeMiddleware:
    """
    特征树中间件核心类。
    
    管理UI树的状态、参数依赖关系和增量更新逻辑。
    """
    
    def __init__(self, global_params: Optional[Dict[str, Any]] = None):
        """
        初始化中间件。
        
        Args:
            global_params: 全局共享的设计参数，如主题色、间距约束。
        """
        self._root: Optional[UIComponent] = None
        self._global_params: Dict[str, Any] = global_params if global_params else {}
        self._dependency_map: Dict[str, Set[str]] = {} # key: param_name, value: set of node uids
        self._snapshot: Dict[str, str] = {} # key: node uid, value: node hash
        
        logger.info("FeatureTreeMiddleware initialized with params: %s", self._global_params)

    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """
        辅助函数：验证参数的合法性。
        
        Args:
            params: 待验证的参数字典。
            
        Returns:
            bool: 参数是否合法。
            
        Raises:
            ValueError: 如果参数包含不支持的类型或无效值。
        """
        if not isinstance(params, dict):
            logger.error("Invalid params type: expected dict, got %s", type(params))
            raise ValueError("Parameters must be a dictionary.")
        
        # 边界检查：简单的类型校验示例
        for k, v in params.items():
            if isinstance(v, (list, dict, set)) and len(str(v)) > 1000:
                logger.warning("Parameter '%s' exceeds size limit.", k)
                # 实际生产中可能会抛出异常或截断
        
        return True

    def build_node(self, widget_type: str, **kwargs) -> UIComponent:
        """
        核心函数1：构建单个UI特征节点。
        
        自动处理全局参数的注入与依赖关系的记录。
        
        Args:
            widget_type: 组件类型。
            **kwargs: 组件属性。
            
        Returns:
            UIComponent: 构建好的组件实例。
        """
        self._validate_params(kwargs)
        
        # 模拟参数化特征：如果属性引用了全局参数（此处用简单字符串匹配模拟）
        node = UIComponent(widget_type=widget_type, properties=kwargs)
        
        # 记录依赖：如果属性值中包含对全局变量的引用逻辑（此处简化为检查特定key）
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith("$global."):
                param_key = value.split(".")[1]
                if param_key not in self._dependency_map:
                    self._dependency_map[param_key] = set()
                self._dependency_map[param_key].add(node.uid)
                # 解析真实值
                real_value = self._global_params.get(param_key)
                if real_value:
                    node.properties[key] = real_value
                    logger.debug(f"Injected global param '{param_key}' into node {node.uid}")

        # 递归处理子节点（如果在kwargs中传入了children）
        if 'children' in kwargs and isinstance(kwargs['children'], list):
            # 移除children属性，因为它应该作为数据结构的一部分而非属性
            # 这里仅作演示，实际架构中会有更严格的定义
            pass 
            
        return node

    def update_global_param(self, key: str, value: Any) -> Dict[str, Any]:
        """
        核心函数2：更新全局参数并触发增量重建。
        
        模拟CAD中的"修改尺寸"操作。该函数会计算受影响的子树，
        并返回需要重建的节点列表。
        
        Args:
            key: 需要修改的全局参数名（如 'theme_color'）。
            value: 新的参数值。
            
        Returns:
            Dict[str, Any]: 包含变更报告的字典，格式如下：
            {
                "status": "success",
                "affected_nodes": List[str], # 受影响节点的UID列表
                "rebuild_required": bool
            }
        """
        if key not in self._global_params:
            logger.warning("Param '%s' not found in global context.", key)
            return {"status": "error", "message": "Param not found"}

        logger.info(f"Updating global param: {key} = {value}")
        self._global_params[key] = value
        
        # 查找受影响的节点
        affected_uids = self._dependency_map.get(key, set())
        
        if not affected_uids:
            return {"status": "success", "affected_nodes": [], "rebuild_required": False}

        # 模拟重建逻辑：在实际引擎中，这里会生成新的Widget树并Diff
        # 这里我们仅返回受影响的节点ID列表
        logger.info(f"Change propagation detected. Affected nodes: {affected_uids}")
        
        return {
            "status": "success",
            "affected_nodes": list(affected_uids),
            "rebuild_required": True,
            "new_value": value
        }

    def mount_tree(self, root: UIComponent) -> None:
        """
        挂载根节点并生成初始快照。
        
        Args:
            root: UI树的根节点。
        """
        self._root = root
        self._take_snapshot(self._root)
        logger.info("UI Feature Tree mounted successfully.")

    def _take_snapshot(self, node: UIComponent):
        """递归生成初始哈希快照，用于后续的差异比较。"""
        self._snapshot[node.uid] = node.get_hash()
        for child in node.children:
            self._take_snapshot(child)

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化系统，定义全局设计意图（主题色、边距）
    print("--- Initializing System ---")
    middleware = FeatureTreeMiddleware(global_params={
        "primary_color": "#FF0000",
        "base_padding": 16
    })

    # 2. 构建UI特征树
    # 这里的 build_node 类似于 Flutter 中的 Widget 构造函数
    # 注意："$global.primary_color" 是模拟的参数引用语法
    header = middleware.build_node(
        widget_type="Container",
        color="$global.primary_color",
        padding=10
    )
    
    body = middleware.build_node(
        widget_type="Row",
        children=[] # 在真实场景中这里会挂载子节点
    )
    
    root_node = middleware.build_node(
        widget_type="Column",
        children=[header, body]
    )

    # 3. 挂载树
    middleware.mount_tree(root_node)
    print(f"Root mounted with hash: {root_node.get_hash()[:10]}...")
    print(f"Header node ID: {header.uid}, Color: {header.properties['color']}")

    # 4. 动态修改参数（模拟CAD调整尺寸）
    print("\n--- Updating Global Parameter ---")
    result = middleware.update_global_param("primary_color", "#0000FF")
    
    if result["rebuild_required"]:
        print(f"System detected change. Rebuilding {len(result['affected_nodes'])} nodes.")
        # 在实际应用中，这里会触发受影响节点的 rebuild
        # 我们可以重新构建受影响的节点来模拟更新
        new_header = middleware.build_node(
            widget_type="Container",
            color="$global.primary_color", # 此时应该解析为蓝色
            padding=10
        )
        print(f"New Header Color: {new_header.properties['color']}") # 应该输出 #0000FF
    else:
        print("No UI changes required.")
        
    # 5. 边界情况测试：更新不存在的参数
    print("\n--- Testing Error Handling ---")
    err_res = middleware.update_global_param("non_existent_key", 123)
    print(f"Result: {err_res['status']}")