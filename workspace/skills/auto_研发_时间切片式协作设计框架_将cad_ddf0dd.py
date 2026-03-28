"""
Module: time_sliced_collab_design.py
Description: 研发'时间切片式协作设计框架'。
             将CAD的每一个特征操作封装为Flutter可识别的Action/Event，
             利用状态管理逻辑实现工程图纸的毫秒级版本回溯和协同冲突解决。
"""

import logging
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TimeSlicedCADCollab")

class OperationType(Enum):
    """CAD操作类型枚举，映射为Flutter Event Types"""
    SKETCH = "SKETCH"
    EXTRUDE = "EXTRUDE"
    CUT = "CUT"
    FILLET = "FILLET"
    CHAMFER = "CHAMFER"

@dataclass(order=True)
class TimeSlice:
    """
    时间切片数据结构。
    表示在特定时间点的一个CAD特征操作。
    """
    # 排序索引，优先按时间戳排序
    timestamp: float
    # 操作ID
    action_id: str = field(compare=False)
    # 用户ID
    user_id: str = field(compare=False)
    # 操作类型
    op_type: OperationType = field(compare=False)
    # 操作负载数据 (e.g., {"depth": 10, "sketch_id": "..."})
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    # 父切片ID，用于分支回溯
    parent_id: Optional[str] = field(compare=False, default=None)

class CollaborativeDesignFramework:
    """
    时间切片式协作设计框架核心类。
    
    负责管理CAD特征的时间序列，解决协同冲突，并生成供前端Flutter消费的状态快照。
    
    Usage Example:
        >>> framework = CollaborativeDesignFramework()
        >>> op_id = framework.commit_local_action("user_01", "EXTRUDE", {"depth": 20})
        >>> print(framework.get_current_state())
    """

    def __init__(self, max_history_size: int = 1000):
        """
        初始化框架。
        
        Args:
            max_history_size (int): 撤销历史栈的最大深度。
        """
        self.time_slices: deque[TimeSlice] = deque(maxlen=max_history_size)
        self.branch_pointers: Dict[str, str] = {} # 记录分支头节点
        self.current_branch_id: str = "main"
        self._lock = False # 简单的锁模拟，防止并发写入冲突

    def _validate_payload(self, op_type: OperationType, payload: Dict[str, Any]) -> bool:
        """
        辅助函数：验证操作负载是否合法。
        
        Args:
            op_type (OperationType): 操作类型
            payload (Dict[str, Any]): 参数负载
            
        Returns:
            bool: 验证是否通过
        """
        if not isinstance(payload, dict):
            logger.error(f"Payload validation failed: Expected dict, got {type(payload)}")
            return False
        
        # 简单的规则校验示例
        if op_type == OperationType.EXTRUDE:
            if "depth" not in payload or not isinstance(payload['depth'], (int, float)):
                logger.error("Extrude operation requires numeric 'depth' in payload.")
                return False
            if payload['depth'] <= 0:
                logger.warning("Depth should be positive, but accepted.")
        
        return True

    def _generate_action_id(self) -> str:
        """生成唯一的Action ID"""
        return f"act_{uuid.uuid4().hex[:8]}"

    def resolve_conflict(self, local_slice: TimeSlice, remote_slice: TimeSlice) -> TimeSlice:
        """
        核心函数：解决协同冲突。
        
        采用"最后写入胜出"(Last-Write-Wins)策略，如果时间戳相同，则比较User ID字典序。
        类似Figma的冲突解决机制，但基于特征操作。
        
        Args:
            local_slice (TimeSlice): 本地产生的操作
            remote_slice (TimeSlice): 远程同步来的操作
            
        Returns:
            TimeSlice: 胜出的操作切片
        """
        logger.info(f"Resolving conflict between {local_slice.action_id} and {remote_slice.action_id}")
        
        # 边界检查：必须针对同一个父节点（即同一个设计状态）的修改才叫冲突
        if local_slice.parent_id != remote_slice.parent_id:
            # 如果不是基于同一个父节点，通常需要变基，这里简化为追加
            return remote_slice 

        if local_slice.timestamp > remote_slice.timestamp:
            return local_slice
        elif local_slice.timestamp < remote_slice.timestamp:
            return remote_slice
        else:
            # 时间戳相同，根据用户ID决定优先级
            return local_slice if local_slice.user_id > remote_slice.user_id else remote_slice

    def commit_local_action(
        self, 
        user_id: str, 
        op_type_str: str, 
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        核心函数：提交一个新的CAD特征操作。
        
        这相当于Flutter中的一个Event触发，生成一个新的时间切片。
        
        Args:
            user_id (str): 操作用户ID
            op_type_str (str): 操作类型字符串 (e.g., "EXTRUDE")
            payload (Dict[str, Any]): 操作参数
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, Action ID)
        """
        try:
            # 转换并验证
            op_type = OperationType[op_type_str.upper()]
            if not self._validate_payload(op_type, payload):
                return False, None

            # 确定父节点
            parent_id = self.branch_pointers.get(self.current_branch_id)
            
            # 创建时间切片
            new_slice = TimeSlice(
                timestamp=time.time() * 1000, # 毫秒级时间戳
                action_id=self._generate_action_id(),
                user_id=user_id,
                op_type=op_type,
                payload=payload,
                parent_id=parent_id
            )
            
            # 提交到历史栈
            self.time_slices.append(new_slice)
            self.branch_pointers[self.current_branch_id] = new_slice.action_id
            
            logger.info(f"Committed action {new_slice.action_id} by {user_id}")
            return True, new_slice.action_id

        except KeyError:
            logger.error(f"Invalid operation type: {op_type_str}")
            return False, None
        except Exception as e:
            logger.exception(f"Error committing action: {e}")
            return False, None

    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前设计状态。
        
        模拟遍历时间链表，生成当前分支的特征树摘要。
        在Flutter端，这相当于Riverpod/Bloc中的State对象。
        """
        features = [asdict(s) for s in self.time_slices if s.parent_id is not None or s == self.time_slices[0]]
        return {
            "branch": self.current_branch_id,
            "head_action_id": self.branch_pointers.get(self.current_branch_id),
            "feature_count": len(features),
            "last_updated": time.time()
        }

    def revert_to_version(self, target_action_id: str) -> bool:
        """
        版本回溯功能。
        
        将当前HEAD指针移动到指定的历史切片。
        """
        # 在实际实现中，需要重建历史树，这里仅做简单演示
        found = any(s.action_id == target_action_id for s in self.time_slices)
        if found:
            self.branch_pointers[self.current_branch_id] = target_action_id
            logger.info(f"Reverted state to action {target_action_id}")
            return True
        logger.warning(f"Target action {target_action_id} not found in history.")
        return False

# 数据输入输出格式说明
"""
Input Payload Format (JSON):
{
    "depth": 20.0,
    "sketch_profile": "closed_loop_01",
    "direction": "normal"
}

Output State Format (JSON):
{
    "branch": "main",
    "head_action_id": "act_a1b2c3d4",
    "feature_count": 5,
    "last_updated": 1678900000.123
}
"""

if __name__ == "__main__":
    # 演示代码
    framework = CollaborativeDesignFramework()
    
    # 模拟用户A进行拉伸操作
    success, action_id_1 = framework.commit_local_action("user_A", "EXTRUDE", {"depth": 10.5})
    print(f"Action 1 Committed: {success}, ID: {action_id_1}")
    
    # 模拟用户B进行倒角操作
    success, action_id_2 = framework.commit_local_action("user_B", "FILLET", {"radius": 2.0})
    print(f"Action 2 Committed: {success}, ID: {action_id_2}")
    
    # 获取当前状态
    current_state = framework.get_current_state()
    print(f"Current State: {json.dumps(current_state, indent=2)}")
    
    # 模拟回溯
    framework.revert_to_version(action_id_1)
    print(f"State after revert: {framework.get_current_state()}")