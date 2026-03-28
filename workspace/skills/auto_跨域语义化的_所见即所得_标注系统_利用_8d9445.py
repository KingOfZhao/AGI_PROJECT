"""
跨域语义化的'所见即所得'标注系统 (Auto-Semantic WYSIWYG Annotation System)

该模块实现了一个基于上下文树形索引的标注系统，用于在3D CAD模型与Flutter生成的UI信息层之间
建立动态、非破坏性的语义连接。当CAD模型结构发生重组时，UI标注会自动跟随其所属节点移动。

核心功能：
1. 维护CAD模型与UI标注的共享树形索引
2. 处理模型结构重组时的标注位置自动更新
3. 提供标注数据的验证和边界检查

依赖：
- Python 3.8+
- typing_extensions (用于类型注解)
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CADNode:
    """CAD模型树节点"""
    node_id: str
    node_type: str  # 如 "bolt_hole", "surface", "assembly"
    position: Tuple[float, float, float]  # 3D坐标 (x, y, z)
    parent_id: Optional[str] = None
    children: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UIAnnotation:
    """UI标注信息"""
    annotation_id: str
    target_node_id: str  # 关联的CAD节点ID
    content: str  # 标注内容
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 相对于节点的偏移量
    visible: bool = True
    style: Dict = None  # Flutter样式配置

    def __post_init__(self):
        if self.style is None:
            self.style = {
                'color': '#FFFFFF',
                'fontSize': 14,
                'background': 'rgba(0,0,0,0.5)'
            }


class ContextTree:
    """上下文树形索引结构"""

    def __init__(self):
        self.nodes: Dict[str, CADNode] = {}
        self.root_id: Optional[str] = None

    def add_node(self, node: CADNode) -> bool:
        """添加节点到树中"""
        if node.node_id in self.nodes:
            logger.warning(f"节点 {node.node_id} 已存在")
            return False

        self.nodes[node.node_id] = node

        # 如果指定了父节点，更新父节点的子节点列表
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.node_id not in parent.children:
                parent.children.append(node.node_id)
        elif node.parent_id is None:
            # 如果没有父节点，设为根节点
            if self.root_id is not None:
                logger.warning("树已有根节点，新节点未设置父节点")
            else:
                self.root_id = node.node_id

        logger.info(f"成功添加节点 {node.node_id} 到树中")
        return True

    def remove_node(self, node_id: str, force: bool = False) -> bool:
        """
        从树中移除节点
        
        Args:
            node_id: 要移除的节点ID
            force: 是否强制移除（包括子节点）
        
        Returns:
            bool: 是否成功移除
        """
        if node_id not in self.nodes:
            logger.warning(f"节点 {node_id} 不存在")
            return False

        node = self.nodes[node_id]

        # 检查是否有子节点
        if node.children and not force:
            logger.error(f"节点 {node_id} 有子节点，请使用 force=True 强制移除")
            return False

        # 从父节点中移除引用
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node_id in parent.children:
                parent.children.remove(node_id)

        # 递归移除子节点
        if force:
            for child_id in node.children[:]:  # 使用副本避免迭代时修改
                self.remove_node(child_id, force=True)

        # 移除节点
        del self.nodes[node_id]
        if node_id == self.root_id:
            self.root_id = None

        logger.info(f"成功移除节点 {node_id}")
        return True

    def get_node_path(self, node_id: str) -> List[str]:
        """获取从根节点到指定节点的路径"""
        if node_id not in self.nodes:
            return []

        path = []
        current_id = node_id
        while current_id is not None:
            path.insert(0, current_id)
            current_id = self.nodes[current_id].parent_id

        return path

    def find_nodes_by_type(self, node_type: str) -> List[str]:
        """根据类型查找节点"""
        return [nid for nid, node in self.nodes.items() if node.node_type == node_type]

    def to_json(self) -> str:
        """将树结构序列化为JSON"""
        return json.dumps({
            'root_id': self.root_id,
            'nodes': {nid: {
                'node_id': node.node_id,
                'node_type': node.node_type,
                'position': node.position,
                'parent_id': node.parent_id,
                'children': node.children,
                'metadata': node.metadata
            } for nid, node in self.nodes.items()}
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'ContextTree':
        """从JSON反序列化树结构"""
        tree = cls()
        data = json.loads(json_str)

        # 先添加所有节点
        for nid, node_data in data['nodes'].items():
            tree.add_node(CADNode(
                node_id=node_data['node_id'],
                node_type=node_data['node_type'],
                position=tuple(node_data['position']),
                parent_id=node_data['parent_id'],
                children=node_data['children'],
                metadata=node_data['metadata']
            ))

        tree.root_id = data['root_id']
        return tree


class AnnotationSystem:
    """跨域语义化标注系统"""

    def __init__(self):
        self.context_tree = ContextTree()
        self.annotations: Dict[str, UIAnnotation] = {}
        self._flutter_ui_state: Dict = {}  # 模拟Flutter UI状态

    def create_annotation(
        self,
        target_node_id: str,
        content: str,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        style: Optional[Dict] = None
    ) -> Optional[str]:
        """
        创建新的UI标注
        
        Args:
            target_node_id: 目标CAD节点ID
            content: 标注内容
            offset: 相对于节点的偏移量 (x, y, z)
            style: Flutter样式配置
        
        Returns:
            Optional[str]: 创建的标注ID，失败返回None
        """
        # 验证目标节点存在
        if target_node_id not in self.context_tree.nodes:
            logger.error(f"目标节点 {target_node_id} 不存在")
            return None

        # 数据验证
        if not content.strip():
            logger.error("标注内容不能为空")
            return None

        if len(content) > 500:
            logger.warning("标注内容过长，已截断到500字符")
            content = content[:500]

        # 创建标注
        annotation_id = f"annot_{uuid4().hex[:8]}"
        annotation = UIAnnotation(
            annotation_id=annotation_id,
            target_node_id=target_node_id,
            content=content,
            offset=offset,
            style=style or {}
        )

        self.annotations[annotation_id] = annotation
        logger.info(f"成功创建标注 {annotation_id} 关联到节点 {target_node_id}")
        return annotation_id

    def update_annotation(
        self,
        annotation_id: str,
        content: Optional[str] = None,
        offset: Optional[Tuple[float, float, float]] = None,
        style: Optional[Dict] = None
    ) -> bool:
        """
        更新现有标注
        
        Args:
            annotation_id: 要更新的标注ID
            content: 新的标注内容
            offset: 新的偏移量
            style: 新的样式配置
        
        Returns:
            bool: 是否更新成功
        """
        if annotation_id not in self.annotations:
            logger.error(f"标注 {annotation_id} 不存在")
            return False

        annotation = self.annotations[annotation_id]

        if content is not None:
            if not content.strip():
                logger.error("标注内容不能为空")
                return False
            if len(content) > 500:
                logger.warning("标注内容过长，已截断到500字符")
                content = content[:500]
            annotation.content = content

        if offset is not None:
            if len(offset) != 3 or not all(isinstance(v, (int, float)) for v in offset):
                logger.error("偏移量必须是包含3个数字的元组")
                return False
            annotation.offset = offset

        if style is not None:
            annotation.style.update(style)

        logger.info(f"成功更新标注 {annotation_id}")
        return True

    def remove_annotation(self, annotation_id: str) -> bool:
        """移除标注"""
        if annotation_id not in self.annotations:
            logger.warning(f"标注 {annotation_id} 不存在")
            return False

        del self.annotations[annotation_id]
        logger.info(f"成功移除标注 {annotation_id}")
        return True

    def handle_cad_restructure(self, old_node_id: str, new_node_id: str) -> int:
        """
        处理CAD模型结构重组
        
        当CAD节点被替换或重组时，自动更新相关标注的引用
        
        Args:
            old_node_id: 旧节点ID
            new_node_id: 新节点ID
        
        Returns:
            int: 更新的标注数量
        """
        if old_node_id not in self.context_tree.nodes:
            logger.warning(f"旧节点 {old_node_id} 不存在")
            return 0

        if new_node_id not in self.context_tree.nodes:
            logger.warning(f"新节点 {new_node_id} 不存在")
            return 0

        # 查找所有关联到旧节点的标注
        updated_count = 0
        for annotation in self.annotations.values():
            if annotation.target_node_id == old_node_id:
                annotation.target_node_id = new_node_id
                updated_count += 1
                logger.info(
                    f"更新标注 {annotation.annotation_id} 引用: "
                    f"{old_node_id} -> {new_node_id}"
                )

        return updated_count

    def get_annotations_for_node(self, node_id: str) -> List[UIAnnotation]:
        """获取特定节点的所有标注"""
        return [
            annot for annot in self.annotations.values()
            if annot.target_node_id == node_id
        ]

    def generate_flutter_ui_state(self) -> Dict:
        """
        生成Flutter UI状态
        
        Returns:
            Dict: 包含所有可见标注的UI状态
        """
        ui_state = {
            'annotations': [],
            'metadata': {
                'tree_version': '1.0',
                'last_updated': str(uuid4().int >> 64)  # 模拟时间戳
            }
        }

        for annotation in self.annotations.values():
            if not annotation.visible:
                continue

            node = self.context_tree.nodes.get(annotation.target_node_id)
            if not node:
                logger.warning(f"标注 {annotation.annotation_id} 引用不存在的节点 {annotation.target_node_id}")
                continue

            # 计算标注在3D空间中的实际位置
            position = (
                node.position[0] + annotation.offset[0],
                node.position[1] + annotation.offset[1],
                node.position[2] + annotation.offset[2]
            )

            ui_state['annotations'].append({
                'id': annotation.annotation_id,
                'position': position,
                'content': annotation.content,
                'style': annotation.style,
                'node_path': self.context_tree.get_node_path(annotation.target_node_id)
            })

        self._flutter_ui_state = ui_state
        return ui_state


def validate_coordinate(coord: Tuple[float, float, float]) -> bool:
    """
    验证3D坐标是否在合理范围内
    
    Args:
        coord: 3D坐标 (x, y, z)
    
    Returns:
        bool: 是否有效
    """
    if len(coord) != 3:
        return False

    for value in coord:
        if not isinstance(value, (int, float)):
            return False
        if abs(value) > 1e6:  # 假设坐标范围不超过1百万
            return False

    return True


def calculate_relative_offset(
    parent_pos: Tuple[float, float, float],
    child_pos: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """
    计算子节点相对于父节点的偏移量
    
    Args:
        parent_pos: 父节点坐标
        child_pos: 子节点坐标
    
    Returns:
        Tuple[float, float, float]: 相对偏移量
    """
    if not (validate_coordinate(parent_pos) and validate_coordinate(child_pos)):
        raise ValueError("无效的坐标输入")

    return (
        child_pos[0] - parent_pos[0],
        child_pos[1] - parent_pos[1],
        child_pos[2] - parent_pos[2]
    )


# 使用示例
if __name__ == "__main__":
    # 创建标注系统实例
    system = AnnotationSystem()

    # 构建CAD模型树结构
    root = CADNode(
        node_id="root_assembly",
        node_type="assembly",
        position=(0.0, 0.0, 0.0)
    )
    system.context_tree.add_node(root)

    bolt_hole = CADNode(
        node_id="bolt_hole_1",
        node_type="bolt_hole",
        position=(10.0, 5.0, 2.0),
        parent_id="root_assembly"
    )
    system.context_tree.add_node(bolt_hole)

    # 创建标注
    annot_id = system.create_annotation(
        target_node_id="bolt_hole_1",
        content="扭矩要求: 25Nm\n公差范围: ±0.1mm",
        offset=(0.0, 0.0, 0.5),
        style={'color': '#FF0000', 'fontSize': 12}
    )

    # 生成Flutter UI状态
    ui_state = system.generate_flutter_ui_state()
    print("Flutter UI状态:", json.dumps(ui_state, indent=2))

    # 模拟CAD模型重组（节点替换）
    new_bolt_hole = CADNode(
        node_id="bolt_hole_1_v2",
        node_type="bolt_hole",
        position=(10.0, 5.0, 2.0),
        parent_id="root_assembly"
    )
    system.context_tree.add_node(new_bolt_hole)

    # 处理重组并更新标注引用
    updated = system.handle_cad_restructure("bolt_hole_1", "bolt_hole_1_v2")
    print(f"更新了 {updated} 个标注引用")

    # 再次生成UI状态查看变化
    updated_ui_state = system.generate_flutter_ui_state()
    print("更新后的Flutter UI状态:", json.dumps(updated_ui_state, indent=2))