"""
流式响应式设计内核

该模块将Flutter的响应式编程范式深度植入CAD内核，实现几何特征的自动级联重算。
通过定义几何特征的'依赖关系图'，当基础参数(State)改变时，自动触发受影响特征的
级联重算，并在UI层实现毫秒级的几何预览更新。

核心功能：
1. 响应式状态管理：类似Flutter的StatefulWidget
2. 依赖图构建：几何特征间的依赖关系
3. 级联更新：自动传播状态变更
4. 高性能预览：毫秒级几何更新

依赖：
- Python 3.7+
- networkx (用于依赖图管理)
- numpy (用于几何计算)
- logging (内置)

示例:
    >>> kernel = StreamReactiveKernel()
    >>> 
    >>> # 定义基础参数(类似Flutter的State)
    >>> length = kernel.add_state("length", 100.0)
    >>> width = kernel.add_state("width", 50.0)
    >>> 
    >>> # 定义依赖特征(类似Widget的build方法)
    >>> area = kernel.add_feature(
    ...     "area", 
    ...     lambda l, w: l * w, 
    ...     dependencies=["length", "width"]
    ... )
    >>> 
    >>> # 修改参数会自动触发级联更新
    >>> kernel.update_state("length", 120.0)
    >>> print(kernel.get_value("area"))  # 6000.0
"""

import logging
from typing import Dict, List, Callable, Any, Optional, Set, Tuple
import networkx as nx
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
import time
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StreamReactiveKernel")

class FeatureType(Enum):
    """几何特征类型枚举"""
    STATE = auto()      # 基础状态参数
    FEATURE = auto()    # 派生几何特征
    CONSTRAINT = auto() # 几何约束

@dataclass
class GeometricFeature:
    """几何特征数据结构"""
    name: str
    feature_type: FeatureType
    value: Any
    compute_func: Optional[Callable] = None
    dependencies: Optional[List[str]] = None
    last_updated: float = 0.0
    dirty: bool = True
    meta: Optional[Dict[str, Any]] = None

class StreamReactiveKernel:
    """
    流式响应式设计内核
    
    实现类似Flutter的响应式编程模型，但用于CAD几何特征管理。
    当基础参数改变时，自动触发依赖特征的级联重算。
    
    属性:
        features (Dict[str, GeometricFeature]): 所有几何特征的字典
        dependency_graph (nx.DiGraph): 特征依赖关系图
        update_queue (List[str]): 待更新特征队列
        update_callbacks (Dict[str, List[Callable]]): 更新回调函数
    """
    
    def __init__(self):
        """初始化响应式内核"""
        self.features: Dict[str, GeometricFeature] = {}
        self.dependency_graph = nx.DiGraph()
        self.update_queue: List[str] = []
        self.update_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._batch_mode = False
        self._pending_updates: Set[str] = set()
        
        logger.info("StreamReactiveKernel initialized")
    
    def add_state(
        self, 
        name: str, 
        initial_value: Any,
        meta: Optional[Dict[str, Any]] = None
    ) -> GeometricFeature:
        """
        添加基础状态参数(类似Flutter的State)
        
        参数:
            name: 状态名称(必须唯一)
            initial_value: 初始值
            meta: 元数据(如单位、范围等)
            
        返回:
            GeometricFeature: 创建的状态特征
            
        异常:
            ValueError: 如果名称已存在或值无效
        """
        if name in self.features:
            raise ValueError(f"Feature '{name}' already exists")
            
        if initial_value is None:
            raise ValueError("State value cannot be None")
            
        self._validate_value(initial_value)
        
        feature = GeometricFeature(
            name=name,
            feature_type=FeatureType.STATE,
            value=initial_value,
            last_updated=time.time(),
            meta=meta or {}
        )
        
        self.features[name] = feature
        self.dependency_graph.add_node(name)
        
        logger.debug(f"Added state '{name}' with value {initial_value}")
        return feature
    
    def add_feature(
        self,
        name: str,
        compute_func: Callable,
        dependencies: List[str],
        meta: Optional[Dict[str, Any]] = None
    ) -> GeometricFeature:
        """
        添加派生几何特征(类似Flutter的Widget build方法)
        
        参数:
            name: 特征名称(必须唯一)
            compute_func: 计算函数，参数为依赖特征的值
            dependencies: 依赖的特征名称列表
            meta: 元数据(如几何类型、颜色等)
            
        返回:
            GeometricFeature: 创建的特征
            
        异常:
            ValueError: 如果名称已存在或依赖无效
            TypeError: 如果compute_func不可调用
        """
        if name in self.features:
            raise ValueError(f"Feature '{name}' already exists")
            
        if not callable(compute_func):
            raise TypeError("compute_func must be callable")
            
        if not dependencies:
            raise ValueError("Feature must have at least one dependency")
            
        for dep in dependencies:
            if dep not in self.features:
                raise ValueError(f"Dependency '{dep}' not found")
                
        feature = GeometricFeature(
            name=name,
            feature_type=FeatureType.FEATURE,
            value=None,
            compute_func=compute_func,
            dependencies=dependencies,
            meta=meta or {}
        )
        
        self.features[name] = feature
        self.dependency_graph.add_node(name)
        
        # 添加依赖边
        for dep in dependencies:
            self.dependency_graph.add_edge(dep, name)
            
        logger.debug(f"Added feature '{name}' depending on {dependencies}")
        return feature
    
    def update_state(self, name: str, new_value: Any) -> None:
        """
        更新状态参数并触发级联更新(类似Flutter的setState)
        
        参数:
            name: 状态名称
            new_value: 新值
            
        异常:
            ValueError: 如果状态不存在或值无效
        """
        if name not in self.features:
            raise ValueError(f"State '{name}' not found")
            
        if self.features[name].feature_type != FeatureType.STATE:
            raise ValueError(f"'{name}' is not a state")
            
        self._validate_value(new_value)
        
        # 批量模式下暂存更新
        if self._batch_mode:
            self._pending_updates.add(name)
            self.features[name].value = new_value
            self.features[name].dirty = True
            logger.debug(f"Batch update queued for state '{name}'")
            return
            
        # 立即更新模式
        old_value = self.features[name].value
        self.features[name].value = new_value
        self.features[name].last_updated = time.time()
        self.features[name].dirty = True
        
        logger.debug(f"Updated state '{name}' from {old_value} to {new_value}")
        
        # 触发级联更新
        self._cascade_update(name)
    
    def get_value(self, name: str) -> Any:
        """
        获取特征的当前值，如果脏则先重算
        
        参数:
            name: 特征名称
            
        返回:
            Any: 特征的当前值
            
        异常:
            ValueError: 如果特征不存在
        """
        if name not in self.features:
            raise ValueError(f"Feature '{name}' not found")
            
        feature = self.features[name]
        
        # 如果是脏特征，先重算
        if feature.dirty:
            self._recompute_feature(name)
            
        return feature.value
    
    def batch_update(self) -> 'BatchUpdateContext':
        """
        进入批量更新模式(类似Flutter的batchUpdates)
        
        返回:
            BatchUpdateContext: 批量更新上下文管理器
            
        示例:
            with kernel.batch_update():
                kernel.update_state("length", 120)
                kernel.update_state("width", 80)
        """
        return BatchUpdateContext(self)
    
    def on_update(self, name: str, callback: Callable[[Any], None]) -> None:
        """
        注册特征更新回调(类似Flutter的addListener)
        
        参数:
            name: 特征名称
            callback: 回调函数，接收新值作为参数
        """
        if name not in self.features:
            raise ValueError(f"Feature '{name}' not found")
            
        self.update_callbacks[name].append(callback)
        logger.debug(f"Added update callback for '{name}'")
    
    def _validate_value(self, value: Any) -> None:
        """验证值的有效性"""
        if isinstance(value, (int, float)):
            if not np.isfinite(value):
                raise ValueError("Numeric value must be finite")
                
    def _recompute_feature(self, name: str) -> None:
        """重新计算特征值"""
        feature = self.features[name]
        
        if feature.feature_type == FeatureType.STATE:
            feature.dirty = False
            return
            
        # 收集依赖的值
        dep_values = []
        for dep in feature.dependencies:
            dep_feature = self.features[dep]
            
            # 如果依赖也是脏的，先重算
            if dep_feature.dirty:
                self._recompute_feature(dep)
                
            dep_values.append(dep_feature.value)
        
        # 计算新值
        try:
            start_time = time.perf_counter()
            new_value = feature.compute_func(*dep_values)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            feature.value = new_value
            feature.last_updated = time.time()
            feature.dirty = False
            
            logger.debug(
                f"Recomputed feature '{name}' in {elapsed:.2f}ms, new value: {new_value}"
            )
            
            # 触发回调
            for callback in self.update_callbacks.get(name, []):
                try:
                    callback(new_value)
                except Exception as e:
                    logger.error(f"Error in update callback for '{name}': {e}")
                    
        except Exception as e:
            logger.error(f"Failed to recompute feature '{name}': {e}")
            raise RuntimeError(f"Feature computation failed: {e}") from e
    
    def _cascade_update(self, start_node: str) -> None:
        """执行级联更新"""
        # 获取受影响的所有节点(拓扑排序)
        try:
            affected_nodes = nx.descendants(self.dependency_graph, start_node)
            sorted_nodes = nx.topological_sort(
                self.dependency_graph.subgraph({start_node} | affected_nodes)
            )
        except nx.NetworkXError as e:
            logger.error(f"Dependency graph error: {e}")
            return
            
        # 跳过起始节点(已经更新)
        next(sorted_nodes)
        
        # 标记所有受影响节点为脏
        for node in sorted_nodes:
            self.features[node].dirty = True
            logger.debug(f"Marked feature '{node}' as dirty")
            
        # 执行重算
        for node in sorted_nodes:
            if self.features[node].dirty:
                self._recompute_feature(node)

class BatchUpdateContext:
    """批量更新上下文管理器"""
    
    def __init__(self, kernel: StreamReactiveKernel):
        self.kernel = kernel
        
    def __enter__(self):
        self.kernel._batch_mode = True
        self.kernel._pending_updates = set()
        logger.debug("Entered batch update mode")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.kernel._batch_mode = False
        
        # 处理所有暂存的更新
        for name in self.kernel._pending_updates:
            self.kernel.features[name].last_updated = time.time()
            self.kernel._cascade_update(name)
            
        self.kernel._pending_updates.clear()
        logger.debug("Exited batch update mode")
        
        if exc_type is not None:
            logger.error(f"Error during batch update: {exc_val}")
            return False  # 重新抛出异常
            
        return True

# 辅助函数
def create_reactive_kernel() -> StreamReactiveKernel:
    """
    创建并返回一个配置好的响应式内核实例
    
    返回:
        StreamReactiveKernel: 配置好的内核实例
    """
    kernel = StreamReactiveKernel()
    
    # 添加默认的几何特征计算函数
    def rectangle_points(length: float, width: float) -> List[Tuple[float, float]]:
        """计算矩形顶点坐标"""
        return [
            (0.0, 0.0),
            (length, 0.0),
            (length, width),
            (0.0, width)
        ]
    
    kernel.add_state("length", 100.0, {"unit": "mm", "min": 1.0})
    kernel.add_state("width", 50.0, {"unit": "mm", "min": 1.0})
    kernel.add_feature(
        "rectangle_points",
        rectangle_points,
        ["length", "width"],
        {"type": "polygon"}
    )
    
    return kernel

if __name__ == "__main__":
    # 使用示例
    kernel = create_reactive_kernel()
    
    # 添加更新监听器
    def on_points_update(new_points):
        print(f"Rectangle points updated: {new_points}")
        
    kernel.on_update("rectangle_points", on_points_update)
    
    # 测试单个更新
    print("\nSingle update:")
    kernel.update_state("length", 120.0)
    
    # 测试批量更新
    print("\nBatch update:")
    with kernel.batch_update():
        kernel.update_state("length", 150.0)
        kernel.update_state("width", 75.0)
    
    # 获取最终值
    print("\nFinal values:")
    print(f"Length: {kernel.get_value('length')}")
    print(f"Width: {kernel.get_value('width')}")
    print(f"Points: {kernel.get_value('rectangle_points')}")