"""
高级认知记忆固化与衰变系统

该模块实现了基于艾宾浩斯遗忘曲线的记忆管理机制，模拟人类记忆的自然衰变与固化过程。
主要功能包括：
1. 记忆权重的指数衰变
2. 成功调用时的记忆固化
3. 衰变时间常数的动态调整
4. 记忆状态的持久化存储

典型使用场景：
>>> memory_system = MemorySystem()
>>> memory_system.store_memory("python_basics", "Core Python concepts")
>>> memory_system.access_memory("python_basics")  # 成功访问触发固化
>>> memory_system.apply_decay()  # 应用自然衰变
"""

import math
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import os

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 类型别名定义
MemoryID = str
MemoryContent = Union[str, Dict, List]
TimeStamp = float
Weight = float

@dataclass
class MemoryNode:
    """记忆节点数据结构"""
    id: MemoryID
    content: MemoryContent
    weight: Weight = 1.0  # 初始权重
    decay_rate: float = 0.5  # 初始衰变率(0-1)
    last_accessed: TimeStamp = None
    creation_time: TimeStamp = None
    access_count: int = 0
    consolidation_level: int = 0  # 固化等级(0-5)
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = datetime.now().timestamp()
        if self.creation_time is None:
            self.creation_time = datetime.now().timestamp()

class MemorySystem:
    """基于遗忘曲线的记忆管理系统"""
    
    # 系统常量
    MIN_DECAY_RATE = 0.05  # 最小衰变率(高度固化的记忆)
    MAX_DECAY_RATE = 0.8   # 最大衰变率(新记忆)
    DECAY_TIME_CONSTANT = 7 * 24 * 3600  # 默认衰变时间常数(7天)
    CONSOLIDATION_FACTOR = 0.7  # 每次固化衰变率降低因子
    MAX_WEIGHT = 2.0  # 最大权重上限
    MIN_WEIGHT = 0.01  # 最小权重下限(低于此值视为遗忘)
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化记忆系统
        
        Args:
            storage_path: 可选的记忆存储文件路径
        """
        self.memories: Dict[MemoryID, MemoryNode] = {}
        self.storage_path = storage_path
        self._load_memories()
        logger.info("Memory system initialized with %d memories", len(self.memories))
    
    def store_memory(
        self,
        memory_id: MemoryID,
        content: MemoryContent,
        initial_weight: Weight = 1.0,
        decay_rate: float = 0.5
    ) -> bool:
        """
        存储新记忆或更新现有记忆
        
        Args:
            memory_id: 记忆的唯一标识符
            content: 记忆内容
            initial_weight: 初始权重(0.01-2.0)
            decay_rate: 初始衰变率(0.05-0.8)
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            ValueError: 如果参数超出有效范围
        """
        try:
            # 数据验证
            if not memory_id:
                raise ValueError("Memory ID cannot be empty")
                
            if not (self.MIN_WEIGHT <= initial_weight <= self.MAX_WEIGHT):
                raise ValueError(f"Initial weight must be between {self.MIN_WEIGHT} and {self.MAX_WEIGHT}")
                
            if not (self.MIN_DECAY_RATE <= decay_rate <= self.MAX_DECAY_RATE):
                raise ValueError(f"Decay rate must be between {self.MIN_DECAY_RATE} and {self.MAX_DECAY_RATE}")
            
            # 创建或更新记忆节点
            current_time = datetime.now().timestamp()
            if memory_id in self.memories:
                # 更新现有记忆
                node = self.memories[memory_id]
                node.content = content
                node.last_accessed = current_time
                node.access_count += 1
                logger.debug("Updated existing memory: %s", memory_id)
            else:
                # 创建新记忆
                self.memories[memory_id] = MemoryNode(
                    id=memory_id,
                    content=content,
                    weight=initial_weight,
                    decay_rate=decay_rate,
                    last_accessed=current_time,
                    creation_time=current_time
                )
                logger.debug("Created new memory: %s", memory_id)
            
            self._save_memories()
            return True
            
        except Exception as e:
            logger.error("Failed to store memory %s: %s", memory_id, str(e))
            return False
    
    def access_memory(
        self,
        memory_id: MemoryID,
        validate_content: Optional[bool] = None
    ) -> Tuple[Optional[MemoryContent], Weight]:
        """
        访问记忆并应用固化机制
        
        Args:
            memory_id: 要访问的记忆ID
            validate_content: 可选的内容验证标志(如果为False则视为遗忘)
            
        Returns:
            Tuple[Optional[MemoryContent], Weight]: 返回记忆内容和当前权重
            如果记忆不存在或已遗忘则返回(None, 0)
        """
        try:
            if memory_id not in self.memories:
                logger.warning("Attempted to access non-existent memory: %s", memory_id)
                return (None, 0)
                
            node = self.memories[memory_id]
            current_time = datetime.now().timestamp()
            
            # 应用衰变前的即时访问
            if validate_content is False:
                # 内容验证失败，视为遗忘
                node.weight *= 0.5  # 权重减半
                node.access_count += 1
                node.last_accessed = current_time
                logger.info("Memory access failed (validation): %s", memory_id)
                self._save_memories()
                return (None, node.weight)
            
            # 应用固化机制
            self._consolidate_memory(node)
            
            # 更新访问记录
            node.access_count += 1
            node.last_accessed = current_time
            
            logger.info(
                "Memory accessed: %s (weight: %.2f, consolidation: %d)",
                memory_id, node.weight, node.consolidation_level
            )
            self._save_memories()
            return (node.content, node.weight)
            
        except Exception as e:
            logger.error("Failed to access memory %s: %s", memory_id, str(e))
            return (None, 0)
    
    def apply_decay(self, time_passed: Optional[float] = None) -> Dict[MemoryID, Weight]:
        """
        应用自然衰变到所有记忆
        
        Args:
            time_passed: 可选的时间间隔(秒)，如果为None则使用实际时间差
            
        Returns:
            Dict[MemoryID, Weight]: 更新后的记忆权重字典
        """
        try:
            current_time = datetime.now().timestamp()
            updated_weights = {}
            
            for memory_id, node in self.memories.items():
                # 计算时间差(秒)
                if time_passed is not None:
                    delta_seconds = time_passed
                else:
                    delta_seconds = current_time - node.last_accessed
                
                # 计算衰变因子
                decay_factor = math.exp(-delta_seconds / (self.DECAY_TIME_CONSTANT * (1 + node.consolidation_level)))
                
                # 应用衰变
                node.weight *= decay_factor
                
                # 确保权重在有效范围内
                node.weight = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, node.weight))
                
                updated_weights[memory_id] = node.weight
                
                # 记录衰变日志
                if delta_seconds > 3600:  # 只记录超过1小时的衰变
                    logger.debug(
                        "Applied decay to %s: delta=%.2f hours, new weight=%.2f",
                        memory_id, delta_seconds/3600, node.weight
                    )
            
            self._save_memories()
            return updated_weights
            
        except Exception as e:
            logger.error("Failed to apply decay: %s", str(e))
            return {}
    
    def _consolidate_memory(self, node: MemoryNode) -> None:
        """
        记忆固化辅助函数(核心固化逻辑)
        
        Args:
            node: 要固化的记忆节点
        """
        try:
            # 固化等级上限检查
            if node.consolidation_level >= 5:
                return
                
            # 增加固化等级
            node.consolidation_level += 1
            
            # 降低衰变率(但不超过最小值)
            node.decay_rate = max(
                self.MIN_DECAY_RATE,
                node.decay_rate * self.CONSOLIDATION_FACTOR
            )
            
            # 增加权重(但不超过最大值)
            node.weight = min(
                self.MAX_WEIGHT,
                node.weight * (1 + 0.2 * node.consolidation_level)  # 每级增加20%
            )
            
            logger.debug(
                "Consolidated memory %s to level %d (decay_rate: %.2f)",
                node.id, node.consolidation_level, node.decay_rate
            )
            
        except Exception as e:
            logger.error("Memory consolidation failed: %s", str(e))
    
    def _save_memories(self) -> bool:
        """将记忆状态保存到存储"""
        if not self.storage_path:
            return True
            
        try:
            # 转换为可序列化格式
            data = {
                "meta": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "memories": {mid: asdict(node) for mid, node in self.memories.items()}
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # 原子写入
            temp_path = self.storage_path + ".tmp"
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, self.storage_path)
            
            return True
            
        except Exception as e:
            logger.error("Failed to save memories: %s", str(e))
            return False
    
    def _load_memories(self) -> bool:
        """从存储加载记忆状态"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return True
            
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # 验证数据格式
            if not isinstance(data.get("memories"), dict):
                raise ValueError("Invalid memory data format")
                
            # 重建记忆节点
            self.memories = {
                mid: MemoryNode(**node_data)
                for mid, node_data in data["memories"].items()
            }
            
            return True
            
        except Exception as e:
            logger.error("Failed to load memories: %s", str(e))
            return False
    
    def get_memory_stats(self) -> Dict[str, Union[int, float]]:
        """
        获取记忆系统统计信息
        
        Returns:
            包含以下键的字典:
            - total_memories: 总记忆数
            - avg_weight: 平均权重
            - avg_decay_rate: 平均衰变率
            - avg_consolidation: 平均固化等级
            - forgotten_count: 已遗忘记忆数(权重<MIN_WEIGHT)
        """
        if not self.memories:
            return {
                "total_memories": 0,
                "avg_weight": 0,
                "avg_decay_rate": 0,
                "avg_consolidation": 0,
                "forgotten_count": 0
            }
            
        try:
            total = len(self.memories)
            weights = [node.weight for node in self.memories.values()]
            decay_rates = [node.decay_rate for node in self.memories.values()]
            consolidations = [node.consolidation_level for node in self.memories.values()]
            
            forgotten = sum(1 for w in weights if w < self.MIN_WEIGHT)
            
            return {
                "total_memories": total,
                "avg_weight": sum(weights) / total,
                "avg_decay_rate": sum(decay_rates) / total,
                "avg_consolidation": sum(consolidations) / total,
                "forgotten_count": forgotten
            }
            
        except Exception as e:
            logger.error("Failed to get memory stats: %s", str(e))
            return {
                "total_memories": 0,
                "avg_weight": 0,
                "avg_decay_rate": 0,
                "avg_consolidation": 0,
                "forgotten_count": 0
            }

# 使用示例
if __name__ == "__main__":
    # 初始化记忆系统(带持久化存储)
    memory_system = MemorySystem(storage_path="data/memory_store.json")
    
    # 存储一些示例记忆
    memory_system.store_memory(
        "python_basics",
        "Core Python concepts: variables, loops, functions",
        initial_weight=1.2,
        decay_rate=0.6
    )
    
    memory_system.store_memory(
        "design_patterns",
        ["Singleton", "Factory", "Observer"],
        initial_weight=0.9
    )
    
    # 访问记忆(触发固化)
    content, weight = memory_system.access_memory("python_basics")
    print(f"Accessed memory (weight: {weight:.2f}): {content}")
    
    # 模拟时间流逝(3天)
    memory_system.apply_decay(time_passed=3 * 24 * 3600)
    
    # 再次访问检查衰变效果
    content, weight = memory_system.access_memory("python_basics")
    print(f"After decay (weight: {weight:.2f}): {content}")
    
    # 获取系统统计
    stats = memory_system.get_memory_stats()
    print("\nMemory System Stats:")
    for k, v in stats.items():
        print(f"{k:>15}: {v}")