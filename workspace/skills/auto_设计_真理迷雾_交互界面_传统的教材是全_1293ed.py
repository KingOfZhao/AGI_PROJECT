"""
真理迷雾交互界面

该模块实现了一个交互式知识地图系统，其中知识点被包裹在“迷雾”中。
用户必须通过提出正确的问题或执行特定的操作（实验）来驱散迷雾，
从而将传统的被动阅读转化为主动的知识狩猎过程。

核心概念:
    - KnowledgeNode: 代表地图上的一个知识点，包含内容、解锁条件和当前状态。
    - FogStatus: 知识点的可见性状态（隐藏、部分可见、已揭示）。
    - TruthFogInterface: 管理知识地图和用户交互的核心类。

输入输出格式:
    - 输入: 用户操作通常为字符串形式的问题或实验描述。
    - 输出: JSON格式的地图状态或包含反馈的字典。

示例:
    >>> system = TruthFogInterface(initial_data)
    >>> result = system.attempt_reveal(node_id="physics_101", user_action="观察苹果下落")
    >>> print(result["message"])
    "迷雾已驱散！你发现了万有引力定律。"
"""

import logging
import json
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FogStatus(Enum):
    """定义知识点在迷雾中的状态"""
    HIDDEN = auto()      # 完全被迷雾覆盖，仅显示提示
    PARTIAL = auto()     # 迷雾变薄，显示部分线索
    REVEALED = auto()    # 迷雾驱散，显示完整知识


@dataclass
class KnowledgeNode:
    """
    知识节点数据类
    
    属性:
        node_id (str): 节点的唯一标识符
        content (str): 知识点的完整内容（仅在REVEALED状态下可见）
        hint (str): 迷雾状态下的提示文本
        unlock_actions (List[str]): 可以驱散迷雾的操作或问题列表
        status (FogStatus): 当前节点的可见状态
        metadata (Dict[str, Any]): 额外的元数据（如难度、分类等）
    """
    node_id: str
    content: str
    hint: str
    unlock_actions: List[str] = field(default_factory=list)
    status: FogStatus = FogStatus.HIDDEN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将节点序列化为字典，根据状态过滤敏感信息"""
        data = asdict(self)
        if self.status != FogStatus.REVEALED:
            data['content'] = "[迷雾笼罩] 内容不可见"
        data['status'] = self.status.name
        return data


class TruthFogInterface:
    """
    真理迷雾交互系统核心类
    
    负责管理知识地图的状态，处理用户交互，验证操作有效性，
    并根据用户行为更新迷雾状态。
    """

    def __init__(self, knowledge_map: Dict[str, Dict[str, Any]]):
        """
        初始化真理迷雾系统
        
        参数:
            knowledge_map: 包含节点数据的字典，键为node_id
            
        异常:
            ValueError: 如果输入数据格式无效
        """
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._load_map(knowledge_map)
        logger.info("TruthFogInterface initialized with %d nodes.", len(self._nodes))

    def _load_map(self, raw_map: Dict[str, Dict[str, Any]]) -> None:
        """加载并验证初始知识地图数据"""
        for nid, data in raw_map.items():
            if not isinstance(data, dict):
                logger.error("Invalid data format for node %s", nid)
                raise ValueError(f"Node data must be a dictionary, got {type(data)}")
            
            # 数据验证与默认值填充
            content = data.get('content', '')
            hint = data.get('hint', '这里有一团浓雾，看不清任何东西。')
            actions = data.get('unlock_actions', [])
            metadata = data.get('metadata', {})
            
            if not isinstance(actions, list):
                logger.warning("unlock_actions for %s is not a list, converting.", nid)
                actions = [str(actions)]

            self._nodes[nid] = KnowledgeNode(
                node_id=nid,
                content=content,
                hint=hint,
                unlock_actions=actions,
                metadata=metadata
            )

    def _validate_input(self, node_id: str, user_action: str) -> bool:
        """
        辅助函数：验证输入参数的有效性
        
        参数:
            node_id: 目标节点ID
            user_action: 用户输入的操作或问题
            
        返回:
            bool: 输入是否有效
        """
        if not node_id or not isinstance(node_id, str):
            logger.warning("Invalid node_id provided: %s", node_id)
            return False
        if not user_action or not isinstance(user_action, str):
            logger.warning("Invalid user_action provided: %s", user_action)
            return False
        if node_id not in self._nodes:
            logger.warning("Node %s does not exist in the map.", node_id)
            return False
        return True

    def attempt_reveal(self, node_id: str, user_action: str) -> Dict[str, Any]:
        """
        核心函数1：尝试驱散迷雾
        
        用户针对特定节点执行操作或提问。系统检查该操作是否匹配
        节点的解锁条件。如果匹配且节点未完全揭示，则更新状态。
        
        参数:
            node_id: 目标知识节点ID
            user_action: 用户提出的具体问题或执行的实验描述
            
        返回:
            Dict[str, Any]: 包含操作结果、新状态和反馈消息的字典
            {
                "success": bool,
                "node_id": str,
                "previous_status": str,
                "current_status": str,
                "message": str,
                "revealed_content": Optional[str]
            }
        """
        if not self._validate_input(node_id, user_action):
            return {
                "success": False,
                "message": "无效的输入参数或目标不存在。",
                "node_id": node_id
            }

        node = self._nodes[node_id]
        previous_status = node.status.name
        response = {
            "success": False,
            "node_id": node_id,
            "previous_status": previous_status,
            "current_status": previous_status,
            "message": "",
            "revealed_content": None
        }

        # 如果已经揭示，无需重复操作
        if node.status == FogStatus.REVEALED:
            response["message"] = "这里的迷雾早已散去，真理已显现。"
            logger.info("User attempted to reveal already revealed node %s", node_id)
            return response

        # 检查操作是否匹配解锁条件
        # 这里使用简单的包含匹配，实际应用中可使用更复杂的NLP或逻辑判断
        action_clean = user_action.strip().lower()
        is_match = any(
            action_clean in act.lower() or act.lower() in action_clean
            for act in node.unlock_actions
        )

        if is_match:
            # 操作正确，驱散迷雾
            node.status = FogStatus.REVEALED
            response["success"] = True
            response["current_status"] = node.status.name
            response["message"] = f"操作成功！迷雾消散，你发现了：{node.content}"
            response["revealed_content"] = node.content
            logger.info("Node %s revealed by action: '%s'", node_id, user_action)
        else:
            # 操作错误，迷雾依旧
            response["message"] = f"你的操作 '{user_action}' 似乎没有引起反应。迷雾依旧浓重。\n提示: {node.hint}"
            logger.debug("Failed reveal attempt on %s with action: '%s'", node_id, user_action)

        return response

    def get_visible_landscape(self) -> Dict[str, Any]:
        """
        核心函数2：获取当前可见的知识地图
        
        根据所有节点的当前状态，生成用户可见的地图视图。
        隐藏的节点只显示ID和提示，揭示的节点显示完整内容。
        
        返回:
            Dict[str, Any]: 包含地图统计和节点列表的字典
        """
        visible_nodes = []
        stats = {
            "total": len(self._nodes),
            "revealed": 0,
            "hidden": 0,
            "partial": 0
        }

        for node in self._nodes.values():
            visible_nodes.append(node.to_dict())
            # 更新统计信息
            if node.status == FogStatus.REVEALED:
                stats["revealed"] += 1
            elif node.status == FogStatus.HIDDEN:
                stats["hidden"] += 1
            else:
                stats["partial"] += 1

        landscape = {
            "stats": stats,
            "nodes": visible_nodes
        }
        
        logger.debug("Landscape requested. Stats: %s", stats)
        return landscape


# 示例用法
if __name__ == "__main__":
    # 定义初始知识地图数据
    initial_data = {
        "gravity_01": {
            "content": "万有引力定律：任意两个质点通过连心线方向上的力相互吸引。",
            "hint": "尝试观察物体从高处落下的现象。",
            "unlock_actions": ["扔苹果", "观察下落", "释放物体", "重力实验"],
            "metadata": {"category": "physics", "difficulty": 1}
        },
        "fire_01": {
            "content": "燃烧的三要素：可燃物、助燃物（氧气）、达到着火点。",
            "hint": "尝试点燃一根木头，并思考为什么它燃烧了。",
            "unlock_actions": ["点火", "燃烧木头", "生火"],
            "metadata": {"category": "chemistry", "difficulty": 1}
        }
    }

    # 初始化系统
    fog_system = TruthFogInterface(initial_data)

    # 模拟用户交互
    print("--- 初始状态 ---")
    print(json.dumps(fog_system.get_visible_landscape(), indent=2, ensure_ascii=False))

    print("\n--- 尝试错误的操作 ---")
    result = fog_system.attempt_reveal("gravity_01", "对着石头大喊")
    print(result["message"])

    print("\n--- 尝试正确的操作 ---")
    result = fog_system.attempt_reveal("gravity_01", "扔苹果")
    print(result["message"])

    print("\n--- 最终状态 ---")
    print(json.dumps(fog_system.get_visible_landscape(), indent=2, ensure_ascii=False))