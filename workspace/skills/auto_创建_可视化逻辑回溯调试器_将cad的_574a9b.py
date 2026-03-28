"""
可视化逻辑回溯调试器

受CAD软件特征历史树的启发，本模块实现了一个将应用程序状态流可视化为3D特征树的调试器。
开发者可以像在CAD软件中调整特征顺序一样，在UI界面上拖动事件（如网络请求、用户点击）的
执行顺序，实时观察App状态的分叉与演变。这为复现并发Bug（例如“先渲染后数据到达”）
提供了直观的手段。

核心概念:
- EventNode: 类似于CAD的特征，代表一个原子操作。
- StateSnapshot: 操作执行后的状态快照。
- TimelineTree: 状态演变的树状结构，支持分支（回溯/分叉）。

依赖:
- numpy
- networkx
"""

import json
import logging
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import copy

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CAD_Logic_Debugger")

# 尝试导入高级库，如果失败则提供基础实现
try:
    import networkx as nx
except ImportError:
    logger.warning("NetworkX library not found. Graph visualization features will be limited.")
    nx = None


class EventType(Enum):
    """事件类型枚举，定义应用生命周期中的各种动作"""
    USER_INPUT = "USER_INPUT"
    API_REQUEST = "API_REQUEST"
    API_RESPONSE = "API_RESPONSE"
    RENDER = "RENDER"
    COMPUTATION = "COMPUTATION"


@dataclass
class StateSnapshot:
    """
    应用状态快照。
    
    Attributes:
        store (Dict[str, Any]): 当时的应用状态数据（如Redux store或Context）。
        checksum (str): 状态内容的哈希值，用于快速比对。
    """
    store: Dict[str, Any]
    checksum: str = field(init=False)

    def __post_init__(self):
        # 简单的校验和生成，实际生产中应使用更健壮的hash算法
        self.checksum = str(hash(json.dumps(self.store, sort_keys=True, default=str)))

    def diff(self, other: 'StateSnapshot') -> Dict[str, Any]:
        """比较两个快照的差异"""
        if not isinstance(other, StateSnapshot):
            raise ValueError("Can only diff with another StateSnapshot")
        
        diffs = {}
        all_keys = set(self.store.keys()) | set(other.store.keys())
        for key in all_keys:
            val_self = self.store.get(key)
            val_other = other.store.get(key)
            if val_self != val_other:
                diffs[key] = {"from": val_self, "to": val_other}
        return diffs


@dataclass
class EventNode:
    """
    逻辑事件节点，类似于CAD中的'特征'。
    
    Attributes:
        event_id (str): 唯一标识符。
        event_type (EventType): 事件类型。
        payload (Dict[str, Any]): 事件携带的数据（如API返回的JSON）。
        timestamp (float): 事件发生的时间戳。
        description (str): 事件描述。
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.COMPUTATION
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def __hash__(self):
        return hash(self.event_id)

    def __eq__(self, other):
        if isinstance(other, EventNode):
            return self.event_id == other.event_id
        return False


class TimelineTree:
    """
    时间线树结构。
    
    管理状态快照和事件节点的DAG（有向无环图）。
    支持添加事件、回滚到特定历史点、以及分支模拟。
    """
    
    def __init__(self, initial_state: Dict[str, Any]):
        """
        初始化时间线树。
        
        Args:
            initial_state (Dict[str, Any]): 应用的初始状态。
        """
        self.graph = nx.DiGraph() if nx else {}
        self.root_snapshot = StateSnapshot(store=copy.deepcopy(initial_state))
        self.current_snapshot = self.root_snapshot
        self.head_node_id: Optional[str] = None # 当前HEAD指针
        self.nodes_map: Dict[str, EventNode] = {} # 节点ID到节点的映射
        
        # 初始化图
        if nx:
            self.graph.add_node("ROOT", data=self.root_snapshot)
        else:
            self.graph["ROOT"] = {"data": self.root_snapshot, "children": []}
            
        logger.info("TimelineTree initialized with root state.")

    def add_event(self, event: EventNode, reducer_func: callable) -> StateSnapshot:
        """
        核心函数1: 添加新事件并更新状态。
        
        模拟Redux reducer或类似的状态处理逻辑。
        
        Args:
            event (EventNode): 新发生的事件。
            reducer_func (callable): 纯函数 -> Dict，处理状态变更。
            
        Returns:
            StateSnapshot: 新生成的状态快照。
        """
        if not callable(reducer_func):
            raise TypeError("reducer_func must be callable")
            
        logger.info(f"Adding event: {event.event_type.name} - {event.description}")
        
        # 计算新状态
        try:
            new_store = reducer_func(self.current_snapshot.store, event)
            if not isinstance(new_store, dict):
                raise ValueError("Reducer must return a dictionary state")
        except Exception as e:
            logger.error(f"Error in reducer function for event {event.event_id}: {e}")
            raise

        new_snapshot = StateSnapshot(store=new_store)
        
        # 更新图结构
        if nx:
            self.graph.add_node(event.event_id, data=event)
            self.graph.add_node(f"state_{event.event_id}", data=new_snapshot)
            
            # 连接: 当前状态 -> Event -> 新状态
            parent_state_node = "ROOT" if not self.head_node_id else f"state_{self.head_node_id}"
            self.graph.add_edge(parent_state_node, event.event_id)
            self.graph.add_edge(event.event_id, f"state_{event.event_id}")
        else:
            # 简单字典实现略
            pass

        self.nodes_map[event.event_id] = event
        self.head_node_id = event.event_id
        self.current_snapshot = new_snapshot
        
        return new_snapshot

    def simulate_reorder(
        self, 
        target_event_id: str, 
        new_parent_event_id: str, 
        reducer_func: callable
    ) -> Tuple[StateSnapshot, Dict[str, Any]]:
        """
        核心函数2: 模拟重排序（CAD特征重排）。
        
        将 target_event 移动到 new_parent_event 之后，重新计算状态流。
        这用于检测"如果API响应在渲染之前到达会怎样？"这类场景。
        
        Args:
            target_event_id (str): 要移动的事件ID。
            new_parent_event_id (str): 新的父事件ID（在此事件之后插入）。
            reducer_func (callable): 状态归约函数。
            
        Returns:
            Tuple[StateSnapshot, Dict[str, Any]]: 
                (模拟后的最终状态, 与原始当前状态的差异)。
        """
        if target_event_id not in self.nodes_map or new_parent_event_id not in self.nodes_map:
            raise ValueError("Invalid event IDs for reordering")
            
        logger.warning(f"SIMULATING REORDER: Moving {target_event_id} after {new_parent_event_id}")
        
        # 获取原始快照以便稍后恢复
        original_snapshot = self.current_snapshot
        
        # 1. 收集需要重放的路径
        # 这里简化处理：在真实CAD系统中，这需要遍历DAG拓扑排序
        # 我们模拟一个简单的线性重放逻辑来演示概念
        
        # 获取从Root到NewParent的路径上的所有事件
        # 以及Target事件
        target_event = self.nodes_map[target_event_id]
        
        # 构建模拟状态
        # 假设我们从 new_parent 的状态开始，应用 target 事件
        # 真实实现需要克隆图并修改拓扑结构
        
        # 查找 new_parent 的状态快照
        if nx:
            try:
                # 这里的逻辑简化为：找到 new_parent 产生的状态
                # 实际上需要图遍历查找前置状态
                parent_state_node = f"state_{new_parent_event_id}"
                if not self.graph.has_node(parent_state_node):
                     # 如果是根节点附近的移动，可能需要回溯到ROOT
                     parent_state_node = "ROOT"
                     
                start_state_data = self.graph.nodes[parent_state_node]['data'].store
                simulated_state = copy.deepcopy(start_state_data)
                
                # 应用被移动的事件
                simulated_state = reducer_func(simulated_state, target_event)
                
                # 生成差异报告
                diff = self._generate_diff_report(original_snapshot.store, simulated_state)
                
                return StateSnapshot(store=simulated_state), diff

            except Exception as e:
                logger.error(f"Simulation failed: {e}")
                raise
        else:
            return original_snapshot, {}

    def _generate_diff_report(self, original: Dict, simulated: Dict) -> Dict[str, Any]:
        """
        辅助函数: 生成状态差异报告。
        
        比较原始时间线和模拟时间线的最终状态。
        """
        report = {"conflicts": [], "changes": {}}
        all_keys = set(original.keys()) | set(simulated.keys())
        
        for key in all_keys:
            orig_val = original.get(key)
            sim_val = simulated.get(key)
            if orig_val != sim_val:
                report["changes"][key] = {
                    "original": orig_val,
                    "simulated": sim_val,
                    "type": "MUTATION"
                }
                # 如果是关键数据（如isLoading, data），标记为潜在Bug
                if key in ["data", "isLoading", "user"]:
                    report["conflicts"].append(f"Key '{key}' diverged due to reorder")
                    
        return report

    def visualize(self):
        """
        辅助函数: 简单的可视化输出（文本模式）。
        """
        print(f"\n--- Timeline Tree Structure ({self.__class__.__name__}) ---")
        print(f"Current HEAD: {self.head_node_id}")
        print(f"State Checksum: {self.current_snapshot.checksum}")
        if nx:
            print("Nodes:", self.graph.nodes())
        print("--------------------------------------------------")


# --- 使用示例与模拟逻辑 ---

def example_reducer(state: Dict[str, Any], event: EventNode) -> Dict[str, Any]:
    """
    示例 Reducer: 处理应用状态变更。
    """
    new_state = copy.deepcopy(state)
    
    if event.event_type == EventType.USER_INPUT:
        new_state['last_input'] = event.payload.get('value')
        
    elif event.event_type == EventType.API_REQUEST:
        new_state['isLoading'] = True
        new_state['error'] = None
        
    elif event.event_type == EventType.API_RESPONSE:
        new_state['isLoading'] = False
        # 模拟并发Bug：如果数据先于渲染到达，或者渲染在数据到达时未正确处理
        if new_state.get('render_version') == 'v1':
            # 这里的逻辑可能会因为顺序不同而产生不同结果
            new_state['data'] = event.payload.get('data')
            new_state['needs_re_render'] = True
        else:
            new_state['data'] = event.payload.get('data')
            
    elif event.event_type == EventType.RENDER:
        new_state['render_version'] = event.payload.get('version')
        
    return new_state

def main():
    """主函数：演示调试器使用流程"""
    
    # 1. 初始化调试器和应用状态
    initial_app_state = {
        "user": "guest",
        "isLoading": False,
        "data": None,
        "last_input": None,
        "render_version": None
    }
    
    debugger = TimelineTree(initial_app_state)
    
    # 2. 模拟一系列事件（正常流程）
    # 用户点击按钮触发请求
    click_event = EventNode(
        event_type=EventType.USER_INPUT, 
        payload={"value": "submit_click"},
        description="User clicked submit"
    )
    debugger.add_event(click_event, example_reducer)
    
    # 请求发出
    req_event = EventNode(
        event_type=EventType.API_REQUEST,
        description="Fetching data..."
    )
    debugger.add_event(req_event, example_reducer)
    
    # 渲染开始（此时 isLoading=True，显示加载动画）
    render_event = EventNode(
        event_type=EventType.RENDER,
        payload={"version": "v1"},
        description="Rendered loading skeleton"
    )
    debugger.add_event(render_event, example_reducer)
    
    # 数据返回
    response_event = EventNode(
        event_type=EventType.API_RESPONSE,
        payload={"data": {"id": 1, "content": "Hello World"}},
        description="Data received"
    )
    debugger.add_event(response_event, example_reducer)
    
    print("\n[INFO] Normal Timeline Execution Complete")
    debugger.visualize()
    print(f"Final State: {debugger.current_snapshot.store}")
    
    # 3. 模拟Bug复现：如果我们重排事件？
    # 假设数据在渲染（Render v1）之前就到达了
    print("\n[INFO] Simulating Logic Reorder: API Response arrives BEFORE Render")
    
    # 我们将 response_event 移动到 render_event 之前（也就是 req_event 之后）
    # 注意：为了演示，我们假设移动 response 到 req 之后
    try:
        sim_state, diff = debugger.simulate_reorder(
            target_event_id=response_event.event_id,
            new_parent_event_id=req_event.event_id, 
            reducer_func=example_reducer
        )
        
        print("\n--- Simulation Result ---")
        print(f"Simulated State Checksum: {sim_state.checksum}")
        print(f"Original State Checksum: {debugger.current_snapshot.checksum}")
        print(f"Differences detected: {json.dumps(diff, indent=2)}")
        
        if diff.get("conflicts"):
            print("\n>>> BUG DETECTED: State flow diverges significantly with event reordering!")
        
    except ValueError as ve:
        print(f"Simulation error: {ve}")

if __name__ == "__main__":
    main()