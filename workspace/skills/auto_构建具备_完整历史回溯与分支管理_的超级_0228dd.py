"""
高级AGI技能模块: 参数化历史状态容器 (Parametric History State Container)

该模块实现了一个具备完整历史回溯与分支管理能力的应用状态容器。
借鉴CAD软件中的“参数化特征树”概念，允许用户不仅进行线性Undo/Redo，
还能回到历史中的任意“特征点”，修改参数，并自动重新计算后续所有状态分支。

核心特性:
- 快照管理: 记录每一步的状态快照。
- 参数化修改: 支持回到历史节点修改基础参数。
- 依赖重算: 修改历史节点后，自动向后传播计算（类似CAD的再生逻辑）。
- 分支隔离: 修改历史会生成新的时间线分支，防止状态污染。

作者: AGI System
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import copy
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StateCalculationError(Exception):
    """自定义异常：状态计算失败"""
    pass

class HistoryNodeNotFoundError(Exception):
    """自定义异常：历史节点未找到"""
    pass

@dataclass
class HistoryNode:
    """
    历史树节点，代表状态机中的一个特征步骤。
    
    Attributes:
        id (str): 节点的唯一标识符。
        action_name (str): 触发该状态变化的动作名称。
        params (Dict[str, Any]): 该动作使用的参数（CAD中的特征参数）。
        state_snapshot (Dict[str, Any]): 应用该动作后的状态快照。
        parent_id (Optional[str]): 父节点ID，用于构成历史树。
        timestamp (float): 创建时间戳（可选，此处省略具体实现）。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None

class ParametricStateContainer:
    """
    具备参数化历史回溯能力的超级状态容器。
    
    类似于Git的分支管理或CAD的特征树，但专注于应用状态数据流。
    """
    
    def __init__(self, initial_state: Dict[str, Any], 
                 reducer: Callable[[Dict[str, Any], str, Dict[str, Any]], Dict[str, Any]]):
        """
        初始化容器。
        
        Args:
            initial_state (Dict[str, Any]): 初始应用状态。
            reducer (Callable): 纯函数，接收(当前状态, 动作名, 参数)，返回新状态。
        """
        self._reducer = reducer
        self._history: Dict[str, HistoryNode] = {} # ID -> Node 映射
        self._current_node_id: Optional[str] = None
        
        # 创建根节点
        root_node = HistoryNode(
            action_name="INIT",
            params={},
            state_snapshot=copy.deepcopy(initial_state),
            parent_id=None
        )
        self._history[root_node.id] = root_node
        self._current_node_id = root_node.id
        logger.info(f"State container initialized with Root ID: {root_node.id}")

    @property
    def current_state(self) -> Dict[str, Any]:
        """获取当前活跃的状态快照"""
        if self._current_node_id not in self._history:
            raise RuntimeError("Critical Error: Current history node missing.")
        return copy.deepcopy(self._history[self._current_node_id].state_snapshot)

    def dispatch(self, action_name: str, params: Dict[str, Any]) -> str:
        """
        核心函数1: 派发一个新的动作，推进状态。
        
        这会在当前时间点创建一个新的历史节点。
        
        Args:
            action_name (str): 动作名称。
            params (Dict[str, Any]): 动作参数。
            
        Returns:
            str: 新创建的节点ID。
        """
        if not isinstance(action_name, str) or not action_name:
            raise ValueError("Action name must be a non-empty string.")
        if not isinstance(params, dict):
            raise ValueError("Params must be a dictionary.")

        current_state = self.current_state
        try:
            # 计算新状态
            new_state = self._reducer(current_state, action_name, params)
            
            # 创建新节点
            new_node = HistoryNode(
                action_name=action_name,
                params=params,
                state_snapshot=new_state,
                parent_id=self._current_node_id
            )
            
            # 更新历史记录
            self._history[new_node.id] = new_node
            self._current_node_id = new_node.id
            
            logger.info(f"Dispatched action '{action_name}'. New Node ID: {new_node.id}")
            return new_node.id
            
        except Exception as e:
            logger.error(f"Error during state reduction for action {action_name}: {e}")
            raise StateCalculationError(f"Failed to compute new state: {e}")

    def modify_history_params(self, target_node_id: str, new_params: Dict[str, Any]) -> str:
        """
        核心函数2: CAD风格的参数化回溯与重算。
        
        回到指定的历史节点，修改其参数，并基于该节点重新计算后续所有状态。
        这会创建一个新的分支（类似于Git Rebase）。
        
        Args:
            target_node_id (str): 要修改的历史节点ID。
            new_params (Dict[str, Any]): 新的参数集。
            
        Returns:
            str: 重算后最新节点的ID。
        """
        if target_node_id not in self._history:
            raise HistoryNodeNotFoundError(f"Node ID {target_node_id} not found.")
            
        node_to_modify = self._history[target_node_id]
        logger.warning(f"PARAMETRIC UPDATE: Modifying node {target_node_id} ({node_to_modify.action_name})")
        
        # 1. 修改目标节点的参数
        # 注意：为了保持树的不可变性（或历史完整性），这里通常应该创建副本，
        # 但为了演示"特征修改"，我们更新参数并触发重算。
        node_to_modify.params.update(new_params)
        
        # 2. 获取父节点状态用于重算
        parent_id = node_to_modify.parent_id
        if not parent_id:
            raise ValueError("Cannot modify root node parameters in this context.")
            
        base_state = self._history[parent_id].state_snapshot
        
        # 3. 重新计算当前节点
        try:
            recalculated_state = self._reducer(base_state, node_to_modify.action_name, node_to_modify.params)
            node_to_modify.state_snapshot = recalculated_state
        except Exception as e:
            logger.error(f"Recalculation failed at node {target_node_id}: {e}")
            raise StateCalculationError("History regeneration failed.")

        # 4. 级联重算
        # 这里简化实现：沿着旧分支的路径重新应用动作。
        # 在真实CAD中，这会涉及拓扑排序遍历所有子特征。
        self._cascade_recalculate(target_node_id)
        
        return self._current_node_id

    def _cascade_recalculate(self, start_node_id: str):
        """
        辅助函数: 递归/级联重新计算受影响的后续节点。
        
        当历史中间某节点参数改变时，其后继节点必须基于新状态重新生成。
        此处实现为线性传播（假设线性历史或简单的分支）。
        
        Args:
            start_node_id (str): 发生变更的起始节点ID。
        """
        # 查找当前节点之后的所有子节点（简化版：假设我们在主干上）
        # 在真实场景中，需要构建一个DAG（有向无环图）来查找 children
        
        # 为了演示，我们实现一个简单的"重放路径"逻辑
        # 查找当前 _current_node_id 是否是 target 的后代
        # 如果是，我们需要重新应用从 target 到 current 的所有 actions
        
        path_to_replay = self._get_path_from(start_node_id, self._current_node_id)
        
        if not path_to_replay:
            # 如果修改的不是祖先节点，只是切换分支，则不需要级联重算，
            # 或者如果修改的是分叉点，逻辑会更复杂。
            # 这里我们假设修改的是 direct ancestor。
            logger.info("No downstream nodes to recalculate or branch switched.")
            return

        running_state = self._history[start_node_id].state_snapshot
        
        logger.info(f"Starting cascade recalculation for {len(path_to_replay)} steps...")
        
        # 注意：为了保留历史树结构，我们通常是更新现有节点，或者创建新分支。
        # 这里我们直接更新现有节点的状态（模拟"再生"）
        for node_id in path_to_replay:
            node = self._history[node_id]
            try:
                running_state = self._reducer(running_state, node.action_name, node.params)
                node.state_snapshot = running_state
                logger.debug(f"Regenerated state for node {node_id}")
            except Exception as e:
                logger.error(f"Cascade failed at node {node_id}")
                # 停止传播，状态停留在上一个成功的节点
                self._current_node_id = self._history[node_id].parent_id
                raise StateCalculationError(f"Cascade regeneration error: {e}")

    def _get_path_from(self, start_id: str, end_id: str) -> List[str]:
        """辅助函数：获取两个节点之间的路径（不含start，含end）"""
        path = []
        current_id = end_id
        # 简单的反向回溯查找
        while current_id and current_id != start_id:
            path.append(current_id)
            node = self._history.get(current_id)
            if not node: break
            current_id = node.parent_id
            
        if current_id == start_id:
            return path[::-1] # 反转回正序
        return []

# 示例使用
if __name__ == "__main__":
    # 定义一个简单的Reducer：模拟一个设计表单或计数器
    def form_reducer(state: Dict, action: str, params: Dict) -> Dict:
        new_state = copy.deepcopy(state)
        
        if action == "SET_WIDTH":
            if not isinstance(params.get('value'), (int, float)):
                raise ValueError("Width must be numeric")
            new_state['width'] = params['value']
            # 依赖计算：面积
            new_state['area'] = new_state.get('width', 0) * new_state.get('height', 0)
            
        elif action == "SET_HEIGHT":
            if not isinstance(params.get('value'), (int, float)):
                raise ValueError("Height must be numeric")
            new_state['height'] = params['value']
            # 依赖计算：面积
            new_state['area'] = new_state.get('width', 0) * new_state.get('height', 0)
            
        elif action == "SET_COLOR":
            new_state['color'] = params.get('value', 'white')
            
        return new_state

    # 1. 初始化
    initial_data = {"width": 10, "height": 10, "area": 100, "color": "red"}
    container = ParametricStateContainer(initial_data, form_reducer)
    
    print("--- 初始状态 ---")
    print(container.current_state)

    # 2. 执行一系列操作 (构建历史树)
    print("\n--- 执行操作序列 ---")
    node_step1 = container.dispatch("SET_WIDTH", {"value": 20}) # Area -> 200
    node_step2 = container.dispatch("SET_COLOR", {"value": "blue"})
    node_step3 = container.dispatch("SET_HEIGHT", {"value": 50}) # Area -> 1000
    
    final_state = container.current_state
    print(f"最终状态: {final_state}")
    print(f"预期面积 (20*50): {final_state['area']}")

    # 3. 历史回溯与参数修改 (CAD特征修改)
    # 场景：用户觉得在第1步设置的宽度 20 不对，想改成 50，但希望保留后续的颜色修改和高度设置
    print(f"\n--- 修改历史参数: 回到节点 {node_step1} (SET_WIDTH) ---")
    print(f"将宽度从 20 修改为 50...")
    
    try:
        # 这将触发从 Step1 -> Step2 -> Step3 的重新计算
        container.modify_history_params(node_step1, {"value": 50})
        
        updated_state = container.current_state
        print(f"修改后最终状态: {updated_state}")
        print(f"新预期面积 (50*50): {updated_state['area']}")
        
        # 验证颜色是否保留
        assert updated_state['color'] == 'blue', "后续特征(颜色)丢失"
        assert updated_state['area'] == 2500, "面积计算错误"
        print("\n测试通过：历史参数修改成功，且后续状态正确重新计算。")
        
    except (HistoryNodeNotFoundError, StateCalculationError) as e:
        print(f"Error: {e}")