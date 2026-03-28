"""
实时响应式参数化CAD引擎

本模块实现了一个基于有向无环图(DAG)的参数化CAD核心引擎。它将CAD中的几何约束求解
过程封装为异步计算单元，并利用类似React/Flutter的Diffing算法实现局部重绘。

核心特性:
- 响应式状态管理: 修改参数触发最小必要的重计算
- 异步几何求解: 避免UI线程阻塞
- 局部重绘: 仅更新受影响的几何构件
- 60FPS工程设计: 优化Web端CAD交互体验

输入数据格式:
    parameters: Dict[str, float] - 参数键值对
    constraints: List[Dict] - 约束条件列表
    geometry_cache: Dict - 几何对象缓存

输出数据格式:
    {
        'updated_ids': List[str],  # 需要重绘的构件ID
        'geometry': Dict,          # 更新后的几何数据
        'render_ops': List[Dict]   # 渲染操作指令
    }

作者: AGI System
版本: 1.0.0
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ReactiveCADEngine")


class GeometryType(Enum):
    """几何构件类型枚举"""
    POINT = auto()
    LINE = auto()
    ARC = auto()
    CIRCLE = auto()
    POLYGON = auto()
    SPLINE = auto()
    DIMENSION = auto()


class ConstraintType(Enum):
    """约束类型枚举"""
    DISTANCE = auto()
    ANGLE = auto()
    COINCIDENT = auto()
    PARALLEL = auto()
    PERPENDICULAR = auto()
    TANGENT = auto()


@dataclass
class GeometryNode:
    """几何节点数据结构"""
    node_id: str
    geo_type: GeometryType
    parameters: Dict[str, float]
    dependencies: Set[str] = field(default_factory=set)
    hash_value: str = ""
    is_dirty: bool = True
    last_updated: float = 0.0

    def compute_hash(self) -> str:
        """计算节点参数哈希值用于变更检测"""
        content = f"{self.node_id}:{sorted(self.parameters.items())}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


@dataclass
class RenderOperation:
    """渲染操作指令"""
    operation: str  # 'create', 'update', 'delete'
    target_id: str
    geometry_data: Dict[str, Any]
    priority: int = 0  # 渲染优先级，数值越小越先渲染


class ReactiveCADEngine:
    """
    实时响应式参数化CAD引擎
    
    实现了基于DAG的响应式几何更新系统，支持异步求解和局部重绘。
    
    使用示例:
        >>> engine = ReactiveCADEngine()
        >>> engine.add_parameter("width", 100.0)
        >>> engine.add_parameter("height", 50.0)
        >>> 
        >>> # 定义几何构件
        >>> engine.add_geometry("line1", GeometryType.LINE, 
        ...                     {"x1": 0, "y1": 0, "x2": "@width", "y2": 0})
        >>> 
        >>> # 异步更新参数
        >>> result = await engine.update_parameter("width", 150.0)
        >>> print(f"Updated nodes: {result['updated_ids']}")
    """
    
    def __init__(self, fps_target: int = 60):
        """
        初始化CAD引擎
        
        Args:
            fps_target: 目标帧率，默认60FPS
        """
        self._parameters: Dict[str, float] = {}
        self._geometries: Dict[str, GeometryNode] = {}
        self._constraints: List[Dict[str, Any]] = []
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self._geometry_cache: Dict[str, Dict[str, Any]] = {}
        self._solver_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False
        self._frame_time = 1000.0 / fps_target  # 每帧时间
        
        # 性能统计
        self._stats = {
            'total_updates': 0,
            'avg_solve_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info(f"ReactiveCADEngine initialized with {fps_target} FPS target")

    def add_parameter(self, name: str, value: float) -> None:
        """
        添加或更新参数
        
        Args:
            name: 参数名称
            value: 参数值
            
        Raises:
            ValueError: 参数值无效时抛出
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"Parameter value must be numeric, got {type(value)}")
        
        if not name or not isinstance(name, str):
            raise ValueError("Parameter name must be a non-empty string")
        
        # 边界检查
        if abs(value) > 1e10:
            logger.warning(f"Parameter '{name}' has extreme value: {value}")
        
        self._parameters[name] = float(value)
        logger.debug(f"Parameter '{name}' set to {value}")

    def add_geometry(
        self, 
        node_id: str, 
        geo_type: GeometryType,
        parameters: Dict[str, Any],
        dependencies: Optional[Set[str]] = None
    ) -> None:
        """
        添加几何构件到场景
        
        Args:
            node_id: 节点唯一标识符
            geo_type: 几何类型
            parameters: 几何参数（可包含参数引用如"@width"）
            dependencies: 依赖的其他节点ID集合
        """
        if node_id in self._geometries:
            raise ValueError(f"Geometry node '{node_id}' already exists")
        
        # 解析参数中的引用依赖
        parsed_params = {}
        param_deps = set()
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('@'):
                # 参数引用
                ref_name = value[1:]
                if ref_name not in self._parameters:
                    raise ValueError(f"Unknown parameter reference: {ref_name}")
                parsed_params[key] = ('ref', ref_name)
                param_deps.add(f"param:{ref_name}")
            else:
                parsed_params[key] = ('value', float(value))
        
        # 合并显式依赖和参数依赖
        all_deps = (dependencies or set()) | param_deps
        
        node = GeometryNode(
            node_id=node_id,
            geo_type=geo_type,
            parameters=parsed_params,
            dependencies=all_deps,
            hash_value="",
            is_dirty=True
        )
        node.hash_value = node.compute_hash()
        
        self._geometries[node_id] = node
        self._update_dependency_graph(node_id, all_deps)
        
        logger.info(f"Added geometry '{node_id}' of type {geo_type.name}")

    def _update_dependency_graph(self, node_id: str, dependencies: Set[str]) -> None:
        """
        更新依赖图（辅助函数）
        
        维护正向和反向依赖索引，用于快速查找受影响的节点。
        
        Args:
            node_id: 节点ID
            dependencies: 依赖集合
        """
        # 清理旧的反向依赖
        for dep in self._dependency_graph.get(node_id, set()):
            self._reverse_deps[dep].discard(node_id)
        
        # 设置新依赖
        self._dependency_graph[node_id] = dependencies.copy()
        
        # 建立反向索引
        for dep in dependencies:
            self._reverse_deps[dep].add(node_id)

    async def update_parameter(
        self, 
        name: str, 
        value: float,
        propagate: bool = True
    ) -> Dict[str, Any]:
        """
        异步更新参数并传播变更
        
        这是引擎的核心函数之一，实现了响应式更新机制：
        1. 更新参数值
        2. 计算受影响的节点
        3. 异步求解几何
        4. 生成渲染指令
        
        Args:
            name: 参数名称
            value: 新值
            propagate: 是否传播变更到依赖节点
            
        Returns:
            包含更新结果的字典:
            - updated_ids: 更新的节点ID列表
            - geometry: 更新后的几何数据
            - render_ops: 渲染操作列表
            - solve_time: 求解耗时
            
        Raises:
            KeyError: 参数不存在时抛出
            ValueError: 值无效时抛出
        """
        start_time = time.perf_counter()
        
        # 验证参数存在
        if name not in self._parameters:
            raise KeyError(f"Parameter '{name}' not found")
        
        # 值验证
        if not isinstance(value, (int, float)):
            raise ValueError(f"Invalid value type: {type(value)}")
        
        old_value = self._parameters[name]
        
        # 值相同时跳过
        if abs(old_value - value) < 1e-9:
            logger.debug(f"Parameter '{name}' unchanged, skipping update")
            return {
                'updated_ids': [],
                'geometry': {},
                'render_ops': [],
                'solve_time': 0.0
            }
        
        # 更新参数
        self._parameters[name] = float(value)
        param_key = f"param:{name}"
        
        # 查找受影响的节点
        affected_nodes = set()
        if propagate and param_key in self._reverse_deps:
            affected_nodes = self._get_transitive_dependents(param_key)
        
        logger.info(
            f"Parameter '{name}' updated: {old_value} -> {value}, "
            f"affecting {len(affected_nodes)} nodes"
        )
        
        # 异步求解受影响的几何
        render_ops = []
        updated_geometry = {}
        
        if affected_nodes:
            updated_geometry, render_ops = await self._solve_geometries(
                affected_nodes
            )
        
        solve_time = (time.perf_counter() - start_time) * 1000
        
        # 更新统计
        self._stats['total_updates'] += 1
        self._stats['avg_solve_time'] = (
            (self._stats['avg_solve_time'] * (self._stats['total_updates'] - 1) + solve_time)
            / self._stats['total_updates']
        )
        
        # 检查是否满足帧率要求
        if solve_time > self._frame_time:
            logger.warning(
                f"Solve time {solve_time:.2f}ms exceeds frame budget "
                f"{self._frame_time:.2f}ms"
            )
        
        return {
            'updated_ids': list(affected_nodes),
            'geometry': updated_geometry,
            'render_ops': render_ops,
            'solve_time': solve_time
        }

    def _get_transitive_dependents(self, source: str) -> Set[str]:
        """
        获取传递依赖的所有节点（BFS遍历）
        
        Args:
            source: 源节点或参数键
            
        Returns:
            所有依赖源节点的几何节点ID集合
        """
        visited = set()
        queue = [source]
        
        while queue:
            current = queue.pop(0)
            for dependent in self._reverse_deps.get(current, set()):
                if dependent not in visited and dependent.startswith('param:'):
                    visited.add(dependent)
                    queue.append(dependent)
                elif dependent not in visited:
                    visited.add(dependent)
                    queue.append(dependent)
        
        # 只返回几何节点（非参数节点）
        return {n for n in visited if not n.startswith('param:')}

    async def _solve_geometries(
        self, 
        node_ids: Set[str]
    ) -> Tuple[Dict[str, Any], List[RenderOperation]]:
        """
        异步求解几何节点
        
        核心求解函数，实现：
        1. 拓扑排序确定求解顺序
        2. 增量计算（仅计算脏节点）
        3. 生成最小化渲染指令
        
        Args:
            node_ids: 需要求解的节点ID集合
            
        Returns:
            元组(更新后的几何数据, 渲染操作列表)
        """
        # 拓扑排序
        sorted_nodes = self._topological_sort(node_ids)
        
        geometry_data = {}
        render_ops = []
        
        # 分批处理以保持响应性
        batch_size = 10
        
        for i in range(0, len(sorted_nodes), batch_size):
            batch = sorted_nodes[i:i + batch_size]
            
            for node_id in batch:
                node = self._geometries.get(node_id)
                if not node:
                    continue
                
                # 解析参数
                resolved_params = self._resolve_parameters(node)
                
                # 检查哈希是否变化
                new_hash = hashlib.md5(
                    str(sorted(resolved_params.items())).encode()
                ).hexdigest()[:16]
                
                if new_hash == node.hash_value and not node.is_dirty:
                    self._stats['cache_hits'] += 1
                    continue
                
                self._stats['cache_misses'] += 1
                
                # 执行几何计算
                computed_geo = await self._compute_geometry(
                    node.geo_type, 
                    resolved_params
                )
                
                # 更新节点状态
                node.hash_value = new_hash
                node.is_dirty = False
                node.last_updated = time.time()
                
                # 缓存结果
                self._geometry_cache[node_id] = computed_geo
                geometry_data[node_id] = computed_geo
                
                # 生成渲染指令
                render_op = self._create_render_operation(node_id, computed_geo)
                render_ops.append(render_op)
            
            # 让出控制权保持响应性
            if i + batch_size < len(sorted_nodes):
                await asyncio.sleep(0)
        
        return geometry_data, render_ops

    def _resolve_parameters(self, node: GeometryNode) -> Dict[str, float]:
        """
        解析几何节点的参数引用
        
        Args:
            node: 几何节点
            
        Returns:
            解析后的参数字典（所有值都是float）
        """
        resolved = {}
        
        for key, (ptype, pvalue) in node.parameters.items():
            if ptype == 'ref':
                resolved[key] = self._parameters.get(pvalue, 0.0)
            else:
                resolved[key] = pvalue
        
        return resolved

    async def _compute_geometry(
        self, 
        geo_type: GeometryType,
        params: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        计算几何数据（异步）
        
        实际应用中这里会调用几何内核（如OpenCASCADE）
        
        Args:
            geo_type: 几何类型
            params: 解析后的参数
            
        Returns:
            几何数据字典
        """
        # 模拟异步计算延迟
        await asyncio.sleep(0.001)
        
        # 边界检查
        for key, value in params.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid parameter '{key}': {value}")
            if abs(value) > 1e8:
                logger.warning(f"Extreme value in {key}: {value}")
        
        result = {
            'type': geo_type.name,
            'params': params.copy(),
            'bounding_box': self._compute_bounding_box(geo_type, params)
        }
        
        # 根据类型计算特定属性
        if geo_type == GeometryType.LINE:
            result['length'] = self._compute_line_length(params)
            result['vertices'] = [
                (params.get('x1', 0), params.get('y1', 0)),
                (params.get('x2', 0), params.get('y2', 0))
            ]
        elif geo_type == GeometryType.CIRCLE:
            result['radius'] = params.get('radius', 10.0)
            result['center'] = (params.get('cx', 0), params.get('cy', 0))
            result['circumference'] = 2 * 3.14159 * result['radius']
        elif geo_type == GeometryType.ARC:
            result['radius'] = params.get('radius', 10.0)
            result['start_angle'] = params.get('start_angle', 0)
            result['end_angle'] = params.get('end_angle', 90)
        
        return result

    def _compute_bounding_box(
        self, 
        geo_type: GeometryType,
        params: Dict[str, float]
    ) -> Dict[str, float]:
        """计算几何包围盒"""
        if geo_type == GeometryType.POINT:
            x, y = params.get('x', 0), params.get('y', 0)
            return {'min_x': x, 'min_y': y, 'max_x': x, 'max_y': y}
        elif geo_type == GeometryType.LINE:
            x1, y1 = params.get('x1', 0), params.get('y1', 0)
            x2, y2 = params.get('x2', 0), params.get('y2', 0)
            return {
                'min_x': min(x1, x2),
                'min_y': min(y1, y2),
                'max_x': max(x1, x2),
                'max_y': max(y1, y2)
            }
        elif geo_type in (GeometryType.CIRCLE, GeometryType.ARC):
            cx, cy = params.get('cx', 0), params.get('cy', 0)
            r = params.get('radius', 10)
            return {
                'min_x': cx - r,
                'min_y': cy - r,
                'max_x': cx + r,
                'max_y': cy + r
            }
        return {'min_x': 0, 'min_y': 0, 'max_x': 0, 'max_y': 0}

    def _compute_line_length(self, params: Dict[str, float]) -> float:
        """计算线段长度"""
        x1, y1 = params.get('x1', 0), params.get('y1', 0)
        x2, y2 = params.get('x2', 0), params.get('y2', 0)
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def _create_render_operation(
        self, 
        node_id: str, 
        geometry_data: Dict[str, Any]
    ) -> RenderOperation:
        """
        创建渲染操作指令
        
        实现Diffing算法，决定是创建、更新还是删除几何
        """
        if node_id not in self._geometry_cache:
            return RenderOperation(
                operation='create',
                target_id=node_id,
                geometry_data=geometry_data,
                priority=self._get_render_priority(geometry_data['type'])
            )
        else:
            return RenderOperation(
                operation='update',
                target_id=node_id,
                geometry_data=geometry_data,
                priority=self._get_render_priority(geometry_data['type'])
            )

    def _get_render_priority(self, geo_type_name: str) -> int:
        """获取渲染优先级（数值越小越先渲染）"""
        priorities = {
            'POINT': 1,
            'LINE': 2,
            'ARC': 3,
            'CIRCLE': 3,
            'POLYGON': 4,
            'SPLINE': 5,
            'DIMENSION': 10
        }
        return priorities.get(geo_type_name, 5)

    def _topological_sort(self, node_ids: Set[str]) -> List[str]:
        """
        拓扑排序节点以确定正确的求解顺序
        
        Args:
            node_ids: 待排序的节点集合
            
        Returns:
            排序后的节点ID列表
        """
        in_degree = {nid: 0 for nid in node_ids}
        graph = {nid: [] for nid in node_ids}
        
        # 构建子图
        for nid in node_ids:
            node = self._geometries.get(nid)
            if node:
                for dep in node.dependencies:
                    if dep in node_ids:
                        graph[dep].append(nid)
                        in_degree[nid] += 1
        
        # Kahn算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检测循环依赖
        if len(result) != len(node_ids):
            logger.warning("Circular dependency detected in geometry nodes")
            # 返回已排序部分 + 未排序部分
            remaining = [n for n in node_ids if n not in result]
            result.extend(remaining)
        
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎性能统计"""
        return {
            **self._stats,
            'parameter_count': len(self._parameters),
            'geometry_count': len(self._geometries),
            'cache_size': len(self._geometry_cache)
        }

    def export_scene(self) -> Dict[str, Any]:
        """
        导出完整场景数据
        
        Returns:
            包含所有参数、几何和缓存的字典
        """
        return {
            'parameters': self._parameters.copy(),
            'geometries': {
                nid: {
                    'type': node.geo_type.name,
                    'parameters': node.parameters,
                    'hash': node.hash_value
                }
                for nid, node in self._geometries.items()
            },
            'cache': self._geometry_cache.copy()
        }


# 便捷函数
def create_rectangle(
    engine: ReactiveCADEngine,
    base_x: str,
    base_y: str,
    width_param: str,
    height_param: str
) -> List[str]:
    """
    辅助函数：创建参数化矩形
    
    Args:
        engine: CAD引擎实例
        base_x: 左下角X坐标参数名
        base_y: 左下角Y坐标参数名
        width_param: 宽度参数名
        height_param: 高度参数名
        
    Returns:
        创建的几何节点ID列表
        
    Example:
        >>> engine = ReactiveCADEngine()
        >>> engine.add_parameter("x", 0)
        >>> engine.add_parameter("y", 0)
        >>> engine.add_parameter("w", 100)
        >>> engine.add_parameter("h", 50)
        >>> rect_ids = create_rectangle(engine, "x", "y", "w", "h")
    """
    node_ids = []
    
    # 底边
    bottom_id = f"rect_bottom_{int(time.time()*1000)}"
    engine.add_geometry(
        bottom_id,
        GeometryType.LINE,
        {
            'x1': f'@{base_x}',
            'y1': f'@{base_y}',
            'x2': f'@{base_x}+@{width_param}',
            'y2': f'@{base_y}'
        }
    )
    node_ids.append(bottom_id)
    
    # 右边
    right_id = f"rect_right_{int(time.time()*1000)}"
    engine.add_geometry(
        right_id,
        GeometryType.LINE,
        {
            'x1': f'@{base_x}+@{width_param}',
            'y1': f'@{base_y}',
            'x2': f'@{base_x}+@{width_param}',
            'y2': f'@{base_y}+@{height_param}'
        },
        dependencies={bottom_id}
    )
    node_ids.append(right_id)
    
    # 顶边
    top_id = f"rect_top_{int(time.time()*1000)}"
    engine.add_geometry(
        top_id,
        GeometryType.LINE,
        {
            'x1': f'@{base_x}+@{width_param}',
            'y1': f'@{base_y}+@{height_param}',
            'x2': f'@{base_x}',
            'y2': f'@{base_y}+@{height_param}'
        },
        dependencies={right_id}
    )
    node_ids.append(top_id)
    
    # 左边
    left_id = f"rect_left_{int(time.time()*1000)}"
    engine.add_geometry(
        left_id,
        GeometryType.LINE,
        {
            'x1': f'@{base_x}',
            'y1': f'@{base_y}+@{height_param}',
            'x2': f'@{base_x}',
            'y2': f'@{base_y}'
        },
        dependencies={top_id}
    )
    node_ids.append(left_id)
    
    logger.info(f"Created rectangle with {len(node_ids)} edges")
    return node_ids


# 异步主函数示例
async def main():
    """使用示例"""
    # 初始化引擎
    engine = ReactiveCADEngine(fps_target=60)
    
    # 添加参数
    engine.add_parameter("origin_x", 0.0)
    engine.add_parameter("origin_y", 0.0)
    engine.add_parameter("width", 200.0)
    engine.add_parameter("height", 100.0)
    
    # 添加几何
    engine.add_geometry(
        "base_line",
        GeometryType.LINE,
        {
            'x1': '@origin_x',
            'y1': '@origin_y',
            'x2': '@origin_x+@width',
            'y2': '@origin_y'
        }
    )
    
    engine.add_geometry(
        "center_circle",
        GeometryType.CIRCLE,
        {
            'cx': '@origin_x+@width/2',
            'cy': '@origin_y+@height/2',
            'radius': 25.0
        },
        dependencies={'base_line'}
    )
    
    # 更新参数并观察变化
    print("=== Initial State ===")
    result1 = await engine.update_parameter("width", 300.0)
    print(f"Updated nodes: {result1['updated_ids']}")
    print(f"Solve time: {result1['solve_time']:.2f}ms")
    
    print("\n=== Second Update ===")
    result2 = await engine.update_parameter("height", 150.0)
    print(f"Updated nodes: {result2['updated_ids']}")
    print(f"Render operations: {len(result2['render_ops'])}")
    
    # 打印统计
    print("\n=== Statistics ===")
    stats = engine.get_statistics()
    print(f"Total updates: {stats['total_updates']}")
    print(f"Average solve time: {stats['avg_solve_time']:.2f}ms")
    print(f"Cache hit rate: {stats['cache_hits']/(stats['cache_hits']+stats['cache_misses'])*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())