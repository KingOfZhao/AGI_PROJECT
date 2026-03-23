"""
模块名称: auto_context_persistence.py
描述: 实现AGI系统中的上下文持久化机制。通过维护'结构化认知网络'的快照，
      支持增量更新和快速定位，避免在长程任务执行中重新加载整个环境。
作者: Senior Python Engineer
版本: 1.0.0
"""

import hashlib
import json
import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CognitiveNode:
    """
    认知网络中的节点数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        content (Any): 节点存储的具体内容（代码、文本或数据）。
        context_hash (str): 节点内容的哈希值，用于检测变更。
        edges (Set[str]): 指向其他节点ID的连接，表示依赖或关联关系。
        timestamp (float): 节点最后更新的时间戳。
    """
    node_id: str
    content: Any
    context_hash: str = ""
    edges: Set[str] = field(default_factory=set)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.context_hash:
            self.context_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算内容的SHA256哈希值。"""
        data = pickle.dumps(self.content)
        return hashlib.sha256(data).hexdigest()

    def update_content(self, new_content: Any):
        """更新节点内容并刷新哈希值。"""
        self.content = new_content
        self.context_hash = self._compute_hash()
        self.timestamp = time.time()
        logger.debug(f"Node {self.node_id} content updated. New hash: {self.context_hash[:8]}...")


class ContextPersistenceManager:
    """
    上下文持久化管理器。
    
    负责维护结构化认知网络，实现快照存储、增量更新和基于依赖关系的上下文恢复。
    """

    def __init__(self, storage_path: str = "./cognitive_storage"):
        """
        初始化管理器。
        
        Args:
            storage_path (str): 快照存储的目录路径。
        """
        self.storage_path = storage_path
        self.network: Dict[str, CognitiveNode] = {}
        self.index_map: Dict[str, str] = {}  # 关键词/标签 -> 节点ID 的倒排索引
        
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
            logger.info(f"Created storage directory at: {self.storage_path}")

    def add_node(self, node: CognitiveNode, tags: Optional[List[str]] = None) -> None:
        """
        核心函数1: 添加或更新认知节点。
        
        Args:
            node (CognitiveNode): 要添加的节点对象。
            tags (Optional[List[str]]): 用于检索的标签列表。
        """
        if not isinstance(node, CognitiveNode):
            raise ValueError("Invalid node type. Expected CognitiveNode.")
        
        # 数据验证
        if not node.node_id:
            raise ValueError("Node ID cannot be empty.")

        # 检查是否需要增量更新（如果节点已存在且内容变化）
        if node.node_id in self.network:
            old_node = self.network[node.node_id]
            if old_node.context_hash == node.context_hash:
                logger.info(f"Node {node.node_id} unchanged. Skip update.")
                return
            logger.info(f"Performing incremental update for node {node.node_id}")
        
        self.network[node.node_id] = node
        
        # 更新倒排索引
        if tags:
            for tag in tags:
                if tag not in self.index_map:
                    self.index_map[tag] = set()
                self.index_map[tag].add(node.node_id)
        
        logger.info(f"Node {node.node_id} added/updated in memory.")

    def save_snapshot(self, snapshot_id: str) -> bool:
        """
        核心函数2: 将当前认知网络保存为持久化快照。
        
        使用JSON格式存储图结构和索引，确保人类可读性和跨平台兼容性。
        
        Args:
            snapshot_id (str): 快照的唯一标识符。
        
        Returns:
            bool: 保存是否成功。
        """
        try:
            file_path = os.path.join(self.storage_path, f"{snapshot_id}.json")
            
            # 准备序列化数据
            serializable_network = {
                node_id: {
                    'content': vars(node)['content'], # 注意：实际场景需处理复杂对象的序列化
                    'hash': node.context_hash,
                    'edges': list(node.edges),
                    'timestamp': node.timestamp
                }
                for node_id, node in self.network.items()
            }
            
            data_payload = {
                'meta': {'snapshot_id': snapshot_id, 'saved_at': time.time()},
                'network': serializable_network,
                'index': {k: list(v) for k, v in self.index_map.items()}
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_payload, f, indent=4, ensure_ascii=False, default=str)
            
            logger.info(f"Snapshot {snapshot_id} saved successfully to {file_path}")
            return True

        except IOError as e:
            logger.error(f"IOError while saving snapshot: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during snapshot save: {e}")
            return False

    def locate_and_retrieve(self, query_tags: List[str]) -> List[CognitiveNode]:
        """
        辅助函数: 基于标签定位相关上下文节点。
        
        Args:
            query_tags (List[str]): 查询标签列表。
        
        Returns:
            List[CognitiveNode]: 匹配到的节点列表。
        """
        matched_node_ids: Set[str] = set()
        
        for tag in query_tags:
            if tag in self.index_map:
                matched_node_ids.update(self.index_map[tag])
        
        results = [self.network[nid] for nid in matched_node_ids if nid in self.network]
        logger.info(f"Located {len(results)} nodes for tags: {query_tags}")
        return results

    def load_snapshot(self, snapshot_id: str) -> bool:
        """
        从磁盘加载快照到内存。
        
        Args:
            snapshot_id (str): 要加载的快照ID。
        """
        file_path = os.path.join(self.storage_path, f"{snapshot_id}.json")
        if not os.path.exists(file_path):
            logger.warning(f"Snapshot file not found: {file_path}")
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重建内存结构
            self.network.clear()
            self.index_map.clear()
            
            for node_id, node_data in data['network'].items():
                # 重建节点对象
                node = CognitiveNode(
                    node_id=node_id,
                    content=node_data['content'],
                    context_hash=node_data['hash'],
                    edges=set(node_data['edges']),
                    timestamp=node_data['timestamp']
                )
                self.network[node_id] = node
            
            for tag, ids in data['index'].items():
                self.index_map[tag] = set(ids)
                
            logger.info(f"Snapshot {snapshot_id} loaded. Total nodes: {len(self.network)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load snapshot {snapshot_id}: {e}")
            return False

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化管理器
    manager = ContextPersistenceManager(storage_path="./agi_memory")
    
    # 1. 模拟长程任务中的环境状态
    code_context_1 = {
        "function_name": "calc_gradient",
        "code": "def calc_gradient(x): return 2*x",
        "dependencies": ["numpy"]
    }
    
    node_1 = CognitiveNode(node_id="grad_func_v1", content=code_context_1)
    
    # 添加节点并打标签
    manager.add_node(node_1, tags=["backprop", "math", "layer1"])
    
    # 2. 模拟环境变化：代码更新
    updated_code = {
        "function_name": "calc_gradient",
        "code": "def calc_gradient(x): return 2*x + 0.01", # 增加了 bias
        "dependencies": ["numpy"]
    }
    
    # 创建新节点并关联旧节点 (模拟增量更新)
    node_2 = CognitiveNode(node_id="grad_func_v2", content=updated_code, edges={"grad_func_v1"})
    manager.add_node(node_2, tags=["backprop", "math", "layer2"])
    
    # 3. 持久化快照
    manager.save_snapshot("task_epoch_1")
    
    # 4. 模拟系统重启后的上下文恢复
    print("\n--- Simulating System Reboot ---")
    new_manager = ContextPersistenceManager(storage_path="./agi_memory")
    new_manager.load_snapshot("task_epoch_1")
    
    # 5. 快速定位相关上下文
    print("\n--- Retrieving Context ---")
    # AI 想要查找与 "backprop" 相关的代码
    relevant_nodes = new_manager.locate_and_retrieve(query_tags=["backprop"])
    
    for node in relevant_nodes:
        print(f"Found Node: {node.node_id}, Hash: {node.context_hash[:6]}")
        print(f"Is updated version? {'Yes' if 'v2' in node.node_id else 'No'}")