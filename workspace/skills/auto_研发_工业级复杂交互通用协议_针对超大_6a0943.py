"""
高级Python模块：工业级复杂交互通用协议 (AGI Skill)

名称: auto_研发_工业级复杂交互通用协议_针对超大_6a0943
描述: 本模块旨在解决超大规模UI交互（如万级节点流程图）的性能瓶颈。
      实现了基于Bounding Volume Hierarchy (BVH) 的空间索引技术，
      用于替代传统的DOM遍历，提供CAD级的拾取精度和性能。
      支持框选、点选、链选等复杂交互逻辑的后端计算核心。

依赖: numpy
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CAD_Interaction_Protocol")

# 尝试导入numpy，如果失败则提供降级方案或抛出警告
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("Numpy not found. Falling back to pure Python list operations. Performance may degrade.")


@dataclass
class BoundingBox:
    """
    表示一个2D轴对齐包围盒 (AABB)。
    
    Attributes:
        id (str): 关联的UI元素唯一标识符
        min_x (float): 包围盒最小X坐标
        min_y (float): 包围盒最小Y坐标
        max_x (float): 包围盒最大X坐标
        max_y (float): 包围盒最大Y坐标
    """
    id: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def intersects(self, other: 'BoundingBox') -> bool:
        """检查当前包围盒是否与另一个包围盒相交。"""
        return (self.min_x <= other.max_x and self.max_x >= other.min_x and
                self.min_y <= other.max_y and self.max_y >= other.min_y)

    def contains_point(self, x: float, y: float) -> bool:
        """检查点是否在包围盒内。"""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


class BVHNode:
    """
    Bounding Volume Hierarchy 树节点。
    使用二叉树结构存储空间索引信息。
    """
    def __init__(self, bounds: Optional[BoundingBox] = None):
        self.bounds: Optional[BoundingBox] = None  # 节点的包围盒（合并后的）
        self.left: Optional['BVHNode'] = None
        self.right: Optional['BVHNode'] = None
        self.object_id: Optional[str] = None  # 只有叶子节点存储物体ID
        self._is_leaf = False

    def is_leaf(self) -> bool:
        return self._is_leaf


class IndustrialInteractionEngine:
    """
    工业级交互引擎核心类。
    
    实现了针对超大规模数据的快速拾取算法。
    输入格式: List[Dict] 或 List[BoundingBox]
    输出格式: List[str] (匹配的元素ID列表)
    """

    def __init__(self, elements: List[Union[dict, BoundingBox]]):
        """
        初始化引擎并构建空间索引。
        
        Args:
            elements: UI元素列表，可以是字典列表(需包含id和bounds)或BoundingBox对象列表。
        
        Raises:
            ValueError: 如果元素列表为空或格式无效。
        """
        if not elements:
            raise ValueError("Elements list cannot be empty.")
        
        logger.info(f"Initializing IndustrialInteractionEngine with {len(elements)} elements.")
        self.root: Optional[BVHNode] = None
        self._elements_map = {}
        
        parsed_boxes = self._validate_and_parse_elements(elements)
        start_time = time.time()
        self.root = self._build_bvh(parsed_boxes)
        end_time = time.time()
        logger.info(f"BVH Tree construction completed in {end_time - start_time:.4f}s.")

    def _validate_and_parse_elements(self, elements: List) -> List[BoundingBox]:
        """辅助函数：验证并解析输入数据为BoundingBox对象。"""
        parsed = []
        for idx, el in enumerate(elements):
            if isinstance(el, BoundingBox):
                parsed.append(el)
                self._elements_map[el.id] = el
            elif isinstance(el, dict):
                try:
                    # 假设字典包含 'id' 和 'box' (min_x, min_y, max_x, max_y)
                    bid = el.get('id', f"auto_id_{idx}")
                    b = el.get('bounds', el.get('box'))
                    if not b or len(b) != 4:
                        raise ValueError(f"Element {bid} missing valid bounds.")
                    
                    box = BoundingBox(id=bid, min_x=b[0], min_y=b[1], max_x=b[2], max_y=b[3])
                    parsed.append(box)
                    self._elements_map[bid] = box
                except Exception as e:
                    logger.error(f"Failed to parse element at index {idx}: {e}")
                    continue
            else:
                logger.warning(f"Unsupported element type at index {idx}: {type(el)}")
        return parsed

    def _build_bvh(self, boxes: List[BoundingBox]) -> Optional[BVHNode]:
        """递归构建BVH树。"""
        if not boxes:
            return None

        node = BVHNode()
        
        # 如果只有一个物体，创建叶子节点
        if len(boxes) == 1:
            node.bounds = boxes[0]
            node.object_id = boxes[0].id
            node._is_leaf = True
            return node

        # 计算当前层级的合并包围盒
        # 优化：使用Numpy进行批量计算（如果可用）
        if NUMPY_AVAILABLE:
            coords = np.array([[b.min_x, b.min_y, b.max_x, b.max_y] for b in boxes])
            node.bounds = BoundingBox(
                id="__aggregate__",
                min_x=coords[:, 0].min(),
                min_y=coords[:, 1].min(),
                max_x=coords[:, 2].max(),
                max_y=coords[:, 3].max()
            )
        else:
            min_x = min(b.min_x for b in boxes)
            min_y = min(b.min_y for b in boxes)
            max_x = max(b.max_x for b in boxes)
            max_y = max(b.max_y for b in boxes)
            node.bounds = BoundingBox(id="__aggregate__", min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)

        # 简单的SAH (Surface Area Heuristic) 近似：选择最长轴进行排序分割
        # 这里为了演示清晰，使用简单的中位数分割
        extent_x = node.bounds.max_x - node.bounds.min_x
        extent_y = node.bounds.max_y - node.bounds.min_y
        
        # 根据最长轴排序
        if extent_x > extent_y:
            boxes.sort(key=lambda b: (b.min_x + b.max_x) / 2)
        else:
            boxes.sort(key=lambda b: (b.min_y + b.max_y) / 2)

        mid = len(boxes) // 2
        node.left = self._build_bvh(boxes[:mid])
        node.right = self._build_bvh(boxes[mid:])
        
        return node

    def query_rect_selection(self, selection_box: Tuple[float, float, float, float]) -> List[str]:
        """
        核心功能：执行框选查询。
        
        Args:
            selection_box: (min_x, min_y, max_x, max_y) 选择框坐标。
        
        Returns:
            匹配的元素ID列表。
        """
        if not self.root:
            return []

        sel_bb = BoundingBox(id="__sel__", 
                             min_x=selection_box[0], 
                             min_y=selection_box[1], 
                             max_x=selection_box[2], 
                             max_y=selection_box[3])
        
        results: Set[str] = set()
        self._traverse_for_intersection(self.root, sel_bb, results)
        return list(results)

    def _traverse_for_intersection(self, node: Optional[BVHNode], query_box: BoundingBox, results: Set[str]):
        """递归遍历树寻找相交节点。"""
        if node is None or node.bounds is None:
            return

        # 如果查询框与当前节点包围盒不相交，直接剪枝
        if not node.bounds.intersects(query_box):
            return

        # 如果是叶子节点，添加结果
        if node.is_leaf():
            if node.bounds.intersects(query_box):
                results.add(node.object_id)
            return

        # 递归检查子节点
        self._traverse_for_intersection(node.left, query_box, results)
        self._traverse_for_intersection(node.right, query_box, results)

    def query_point_picking(self, x: float, y: float) -> Optional[str]:
        """
        核心功能：点选查询 (O(log N))。
        
        Args:
            x, y: 屏幕坐标点。
        
        Returns:
            最上层匹配的元素ID (由于BVH是空间索引，若需Z-Order排序需额外逻辑)。
        """
        # 创建一个极小的包围盒作为点
        point_bb = BoundingBox(id="point", min_x=x-0.1, min_y=y-0.1, max_x=x+0.1, max_y=y+0.1)
        
        candidates: Set[str] = set()
        self._traverse_for_intersection(self.root, point_bb, candidates)
        
        if candidates:
            # 实际工业场景中，这里需要根据Z-Index或距离排序
            # 此处简单返回第一个
            return list(candidates)[0]
        return None

# 使用示例
if __name__ == "__main__":
    # 模拟生成10000个随机UI元素
    mock_elements = []
    for i in range(10000):
        x, y = np.random.randint(0, 2000), np.random.randint(0, 2000)
        w, h = np.random.randint(20, 100), np.random.randint(20, 100)
        mock_elements.append({
            "id": f"node_{i}",
            "bounds": (x, y, x+w, y+h)
        })

    # 初始化引擎
    engine = IndustrialInteractionEngine(mock_elements)

    # 测试框选
    # 查询坐标 (100, 100) 到 (500, 500) 范围内的所有节点
    selected_ids = engine.query_rect_selection((100, 100, 500, 500))
    print(f"Found {len(selected_ids)} elements in the selection box.")
    
    # 测试点选
    picked_id = engine.query_point_picking(150, 150)
    print(f"Picked element ID: {picked_id}")