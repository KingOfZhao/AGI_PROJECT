"""
模块名称: atomic_cad_collaboration
描述: 实现操作原子化的协同设计系统核心逻辑。
      将CAD特征操作封装为Action对象，利用CRDT算法支持多人实时协同。
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ActionType(Enum):
    """定义CAD操作的类型"""
    EXTRUDE = "EXTRUDE"          # 拉伸
    CUT = "CUT"                  # 切除
    FILLET = "FILLET"            # 倒角
    CHAMFER = "CHAMFER"          # 倒圆角
    REVOLVE = "REVOLVE"          # 旋转
    SKETCH = "SKETCH"            # 草图

@dataclass
class Vector3D:
    """三维向量数据结构"""
    x: float
    y: float
    z: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

@dataclass(order=True)
class OperationAction:
    """
    原子化操作对象。
    类似于前端Riverpod/Bloc处理的Event，但在后端进行CRDT处理。
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = ActionType.EXTRUDE
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    user_id: str = "unknown"
    params: Dict[str, Any] = field(default_factory=dict)
    # 用于CRDT向量的计数器，结构为 [client_id, counter]
    operation_id: tuple = field(default_factory=lambda: (uuid.uuid4().hex, 0))

    def to_json(self) -> str:
        """将Action序列化为JSON字符串，用于网络传输"""
        data = asdict(self)
        data['action_type'] = self.action_type.value
        data['operation_id'] = list(self.operation_id) # Tuple不可JSON序列化
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'OperationAction':
        """从JSON字符串反序列化"""
        try:
            data = json.loads(json_str)
            data['action_type'] = ActionType(data['action_type'])
            data['operation_id'] = tuple(data['operation_id'])
            return cls(**data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"反序列化Action失败: {e}")
            raise ValueError("Invalid Action JSON format")

class CADStateVector:
    """
    CRDT状态向量。
    用于跟踪不同客户端的操作同步状态。
    """
    def __init__(self):
        self.vector: Dict[str, int] = {} # {user_id: counter}

    def increment(self, user_id: str) -> int:
        """增加特定用户的计数器，返回新值"""
        current = self.vector.get(user_id, 0)
        new_val = current + 1
        self.vector[user_id] = new_val
        return new_val

    def merge(self, other_vector: Dict[str, int]) -> bool:
        """
        合并外部状态向量 (CRDT Merge操作)。
        返回是否有更新。
        """
        updated = False
        for user, counter in other_vector.items():
            if counter > self.vector.get(user, 0):
                self.vector[user] = counter
                updated = True
        return updated

    def to_dict(self) -> Dict[str, int]:
        return self.vector.copy()

class AtomicCollaborativeCADSystem:
    """
    协同设计系统核心类。
    实现了基于Operation Transformation (OT) / CRDT 思想的合并逻辑。
    """

    def __init__(self):
        # 存储所有已应用的操作历史 (OpLog)
        self._operation_log: List[OperationAction] = []
        # 状态向量，用于解决冲突
        self._state_vector = CADStateVector()
        # 当前的模型状态 (简化的B-rep表示)
        self._model_state: Dict[str, Any] = {
            "geometry_tree": [],
            "metadata": {}
        }
        logger.info("Atomic Collaborative CAD System initialized.")

    def _validate_action_params(self, action: OperationAction) -> bool:
        """
        辅助函数：验证Action参数的有效性。
        """
        if not isinstance(action.params, dict):
            return False

        required_keys = {
            ActionType.EXTRUDE: ["sketch_id", "distance"],
            ActionType.CUT: ["sketch_id", "depth"],
            ActionType.FILLET: ["edge_id", "radius"]
        }

        keys = required_keys.get(action.action_type)
        if keys:
            return all(k in action.params for k in keys)
        return True

    def create_action(
        self,
        user_id: str,
        action_type: ActionType,
        params: Dict[str, Any]
    ) -> OperationAction:
        """
        核心函数1: 创建一个新的原子化操作。
        模拟客户端发起请求。
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")

        # 获取当前用户的状态计数并自增
        counter = self._state_vector.increment(user_id)
        
        new_action = OperationAction(
            action_type=action_type,
            user_id=user_id,
            params=params,
            operation_id=(user_id, counter) # Lamport Clock 风格的ID
        )

        if not self._validate_action_params(new_action):
            raise ValueError(f"Invalid parameters for action {action_type}")

        logger.info(f"Action created: {new_action.operation_id} by {user_id}")
        return new_action

    def apply_remote_action(self, action_json: str) -> Dict[str, Any]:
        """
        核心函数2: 接收并应用远程操作（通过网络传输）。
        实现CRDT的合并逻辑，确保最终一致性。
        
        输入格式: JSON字符串
        输出格式: 包含更新状态的字典
        """
        try:
            action = OperationAction.from_json(action_json)
            logger.debug(f"Received remote action: {action.action_id}")

            # 1. 幂等性检查：如果操作已存在，则忽略
            if any(op.action_id == action.action_id for op in self._operation_log):
                logger.warning(f"Duplicate action detected: {action.action_id}")
                return {"status": "duplicate", "model": self._model_state}

            # 2. 因果关系检查 (简化的CRDT逻辑)
            # 在真实的CRDT中，这里需要检查是否缺失前置操作
            # 这里简化为直接追加，因为3D CAD操作通常是严格顺序依赖的
            
            # 3. 应用操作到模型
            self._execute_feature_logic(action)
            
            # 4. 记录操作
            self._operation_log.append(action)
            # 更新状态向量以反映我们已看到此操作
            uid, count = action.operation_id
            if self._state_vector.vector.get(uid, 0) < count:
                 self._state_vector.vector[uid] = count

            logger.info(f"Action {action.action_id} applied successfully.")
            
            return {
                "status": "success",
                "model": self._model_state,
                "vector": self._state_vector.to_dict()
            }

        except Exception as e:
            logger.error(f"Failed to apply remote action: {e}")
            return {"status": "error", "message": str(e)}

    def _execute_feature_logic(self, action: OperationAction) -> None:
        """
        辅助函数：执行具体的CAD特征逻辑（此处为模拟）。
        """
        feature_name = action.action_type.value
        logger.info(f"Executing feature: {feature_name} with params {action.params}")
        
        # 模拟修改模型状态
        self._model_state["geometry_tree"].append({
            "id": action.action_id,
            "type": feature_name,
            "props": action.params
        })

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化系统
    cad_system = AtomicCollaborativeCADSystem()

    # 模拟用户A创建拉伸操作
    try:
        user_a = "user_123"
        # 创建Action对象 (通常在客户端生成)
        action_a = cad_system.create_action(
            user_id=user_a,
            action_type=ActionType.EXTRUDE,
            params={"sketch_id": "sketch_01", "distance": 50.0}
        )
        
        # 模拟通过网络传输 (序列化)
        json_payload = action_a.to_json()
        print(f"\n[Network] Transmitting Payload: {json_payload[:100]}...")

        # 服务端/其他客户端接收并应用
        result = cad_system.apply_remote_action(json_payload)
        print(f"[System] Apply Result: {result['status']}")
        print(f"[Model] Tree Depth: {len(result['model']['geometry_tree'])}")

    except ValueError as e:
        print(f"Error: {e}")

    # 模拟用户B并发进行倒角操作
    try:
        user_b = "user_456"
        # 注意：实际系统中需要先同步状态向量，这里简化演示
        action_b = cad_system.create_action(
            user_id=user_b,
            action_type=ActionType.FILLET,
            params={"edge_id": "edge_99", "radius": 5.0}
        )
        
        # 此时系统状态应包含两个操作
        cad_system.apply_remote_action(action_b.to_json())
        print(f"\nTotal operations in log: {len(cad_system._operation_log)}")
        
    except Exception as e:
        logging.error(f"System crash: {e}")