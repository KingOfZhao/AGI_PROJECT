"""
名称: auto_可视化代码_模型演变时间轴_将cad的_46611f
描述: 
    实现“代码/模型演变时间轴”系统。将CAD的“特征历史树”交互范式引入IDE。
    开发者可以像CAD软件回滚模型一样，拖动“构建进度条”查看每一步代码变更
    对虚拟UI树产生的具体Delta影响，快速定位问题源头。
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CodeTimelineSystem")


class ChangeType(Enum):
    """变更类型枚举"""
    ADD = "ADD"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
    MOVE = "MOVE"


@dataclass
class UITreeNode:
    """UI树节点结构"""
    id: str
    tag: str
    props: Dict[str, Any] = field(default_factory=dict)
    children: List['UITreeNode'] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class CodeStep:
    """代码执行步骤快照"""
    step_id: int
    source_code: str
    description: str
    timestamp: str
    state_snapshot: Dict[str, Any]  # 当前时刻的完整UI状态
    is_error_state: bool = False
    error_msg: Optional[str] = None


class CodeHistoryManager:
    """
    核心类：管理代码执行的历史记录与状态快照。
    模拟IDE中的代码执行过程，每一步操作生成一个快照。
    """

    def __init__(self, initial_state: Optional[Dict] = None):
        """
        初始化历史管理器
        
        Args:
            initial_state: 初始状态字典
        """
        self._history: List[CodeStep] = []
        self._current_step_index: int = -1
        self._initial_state = initial_state if initial_state else {}
        logger.info("CodeHistoryManager initialized.")

    def commit_change(
        self, 
        code: str, 
        desc: str, 
        new_state: Dict[str, Any],
        is_error: bool = False, 
        error_msg: Optional[str] = None
    ) -> int:
        """
        提交一个新的代码变更步骤（类似Git Commit，但是针对运行时状态）。
        
        Args:
            code: 变更的代码片段
            desc: 变更描述
            new_state: 变更后的完整UI树状态
            is_error: 是否包含错误
            error_msg: 错误信息
            
        Returns:
            新步骤的索引ID
        """
        if not isinstance(new_state, dict):
            logger.error("State snapshot must be a dictionary.")
            raise ValueError("State snapshot must be a dictionary.")

        step_id = len(self._history)
        step = CodeStep(
            step_id=step_id,
            source_code=code,
            description=desc,
            timestamp=datetime.now().isoformat(),
            state_snapshot=deepcopy(new_state),
            is_error_state=is_error,
            error_msg=error_msg
        )
        
        self._history.append(step)
        self._current_step_index = step_id
        logger.info(f"Committed step {step_id}: {desc}")
        return step_id

    def get_step_data(self, step_index: int) -> Optional[CodeStep]:
        """
        获取指定步骤的详细数据。
        
        Args:
            step_index: 步骤索引
            
        Returns:
            CodeStep对象或None
        """
        self._validate_index(step_index)
        return self._history[step_index]

    def _validate_index(self, index: int) -> None:
        """验证索引边界"""
        if not (0 <= index < len(self._history)):
            logger.error(f"Index {index} out of bounds.")
            raise IndexError(f"Step index {index} does not exist.")


class TimelineController:
    """
    控制器：处理时间轴的回滚、差异计算和可视化数据生成。
    实现类似CAD特征树的回滚逻辑。
    """

    def __init__(self, manager: CodeHistoryManager):
        self.manager = manager
        self._head_step: int = manager._current_step_index

    def calculate_ui_delta(
        self, 
        old_state: Dict[str, Any], 
        new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        辅助函数：计算两个UI状态之间的差异。
        简化版的Diff算法，用于展示具体Delta影响。
        
        Args:
            old_state: 旧状态
            new_state: 新状态
            
        Returns:
            包含变更详情的字典
        """
        delta_report = {
            "added_keys": [],
            "removed_keys": [],
            "changed_values": []
        }

        old_keys = set(old_state.keys())
        new_keys = set(new_state.keys())

        # 计算新增
        for key in new_keys - old_keys:
            delta_report["added_keys"].append({
                "key": key, 
                "value": new_state[key]
            })

        # 计算删除
        for key in old_keys - new_keys:
            delta_report["removed_keys"].append(key)

        # 计算变更
        for key in old_keys & new_keys:
            if old_state[key] != new_state[key]:
                delta_report["changed_values"].append({
                    "key": key,
                    "old": old_state[key],
                    "new": new_state[key]
                })

        return delta_report

    def rollback_to_step(self, target_step_id: int) -> Dict[str, Any]:
        """
        核心功能：将UI状态回滚到指定的历史步骤。
        类似于CAD中的"拖动构建进度条"。
        
        Args:
            target_step_id: 目标步骤ID
            
        Returns:
            包含目标状态、差异信息和代码的上下文字典
        """
        logger.info(f"Rolling back timeline to step {target_step_id}...")
        
        # 边界检查
        if not (0 <= target_step_id < len(self.manager._history)):
            raise ValueError("Invalid target step ID")

        current_step = self.manager._history[self._head_step]
        target_step = self.manager._history[target_step_id]

        # 计算回滚产生的Delta
        delta = self.calculate_ui_delta(
            current_step.state_snapshot, 
            target_step.state_snapshot
        )

        # 更新头指针（模拟IDE中的HEAD detached状态）
        self._head_step = target_step_id

        return {
            "status": "success",
            "current_head": self._head_step,
            "total_steps": len(self.manager._history),
            "target_state": target_step.state_snapshot,
            "delta_from_actual": delta,
            "code_context": target_step.source_code,
            "is_error_state": target_step.is_error_state
        }

    def visualize_timeline(self) -> str:
        """
        生成ASCII格式的时间轴可视化，用于CLI或日志展示。
        """
        vis_str = ["[TIMELINE VISUALIZER]"]
        vis_str.append(f"Total Steps: {len(self.manager._history)}")
        vis_str.append("-" * 40)
        
        for step in self.manager._history:
            prefix = "(HEAD)" if step.step_id == self._head_step else "     "
            status_icon = "❌" if step.is_error_state else "✅"
            vis_str.append(
                f"{prefix} [{step.step_id}] {status_icon} {step.description} @ {step.timestamp}"
            )
        
        return "\n".join(vis_str)


# 使用示例
if __name__ == "__main__":
    # 1. 初始化系统
    history_mgr = CodeHistoryManager(initial_state={"root": True})
    controller = TimelineController(history_mgr)

    # 2. 模拟代码执行过程（模拟开发者的操作历史）
    # 步骤0: 初始化
    history_mgr.commit_change(
        code="const App = () => <div></div>",
        desc="Initialize UI Tree",
        new_state={"root": True, "type": "div", "children": []}
    )

    # 步骤1: 添加按钮
    history_mgr.commit_change(
        code="setState({count: 0})",
        desc="Add State Counter",
        new_state={"root": True, "type": "div", "children": ["Button"], "count": 0}
    )

    # 步骤2: 修改状态（正常）
    history_mgr.commit_change(
        code="setCount(prev => prev + 1)",
        desc="Increment Counter",
        new_state={"root": True, "type": "div", "children": ["Button"], "count": 1}
    )

    # 步骤3: 引入Bug（界面崩溃，数据结构异常）
    history_mgr.commit_change(
        code="setCount(undefined)", # 模拟错误
        desc="Bad State Update",
        new_state={"root": True, "type": "div", "children": ["Button"], "count": None},
        is_error=True,
        error_msg="TypeError: Cannot read properties of undefined"
    )

    # 3. 可视化当前时间轴
    print(controller.visualize_timeline())

    # 4. 执行回滚操作：开发者发现错误，拖动进度条回到步骤2
    print("\n--- Executing Rollback to Step 2 ---")
    rollback_info = controller.rollback_to_step(2)
    
    print(f"Rollback Target: Step {rollback_info['current_head']}")
    print(f"Code at this step: {rollback_info['code_context']}")
    print("Delta (Difference from error state):")
    print(json.dumps(rollback_info['delta_from_actual'], indent=2))

    # 5. 再次查看时间轴状态，观察HEAD指针变化
    print("\n--- Timeline After Rollback ---")
    print(controller.visualize_timeline())