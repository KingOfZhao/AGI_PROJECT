"""
长上下文状态流追踪引擎

该模块实现了一个基于编译器原理（数据流分析）的对话状态管理引擎。
它将对话历史视为基本块，将实体视为变量。通过模拟活跃变量分析，
精准判断哪些历史实体在当前上下文中是'活跃'的，哪些可以被视为'死代码'，
从而优化LLM的KV Cache管理，在有限窗口中维持超长对话的逻辑自洽性。

Author: AGI System Architect
Version: 1.0.0
"""

import logging
import hashlib
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EntityType(Enum):
    """实体类型枚举，定义不同类型的对话实体"""
    USER_INTENT = "user_intent"
    SYSTEM_ACTION = "system_action"
    TOPIC = "topic"
    ENTITY = "entity"
    CONTEXT_VAR = "context_var"

@dataclass
class ConversationEntity:
    """
    对话实体类
    
    表示对话中的一个关键信息单元，类似于编译器中的变量。
    
    Attributes:
        name (str): 实体名称（唯一标识符）
        entity_type (EntityType): 实体类型
        value (Any): 实体的值
        defined_at (int): 实体被定义（首次出现）的对话轮次索引
        last_used_at (int): 实体最后一次被引用的对话轮次索引
        is_active (bool): 当前是否处于活跃状态
        token_cost (int): 该实体在KV Cache中占用的估计token数
    """
    name: str
    entity_type: EntityType
    value: Any
    defined_at: int
    last_used_at: int = field(default=0)
    is_active: bool = field(default=True)
    token_cost: int = field(default=10) # 默认估算占用10个token

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, ConversationEntity):
            return self.name == other.name
        return False

@dataclass
class ConversationBlock:
    """
    对话基本块
    
    对应于编译器中的基本块概念，包含一组对话轮次。
    
    Attributes:
        block_id (str): 块的唯一ID
        start_index (int): 在完整历史中的起始索引
        end_index (int): 在完整历史中的结束索引
        gen_set (Set[str]): 在该块内生成（定义）的实体名称集合
        kill_set (Set[str]): 在该块内失效（被覆盖）的实体名称集合
        live_in (Set[str]): 进入该块时活跃的实体集合
        live_out (Set[str]): 离开该块时活跃的实体集合
    """
    block_id: str
    start_index: int
    end_index: int
    gen_set: Set[str] = field(default_factory=set)
    kill_set: Set[str] = field(default_factory=set)
    live_in: Set[str] = field(default_factory=set)
    live_out: Set[str] = field(default_factory=set)

class LongContextStateEngine:
    """
    长上下文状态流追踪引擎
    
    核心类，负责管理对话历史、执行数据流分析、并生成KV Cache优化建议。
    """

    def __init__(self, context_window_size: int = 4096, block_size: int = 5):
        """
        初始化引擎
        
        Args:
            context_window_size (int): LLM的最大上下文窗口大小
            block_size (int): 每个基本块包含的对话轮次数
        """
        if context_window_size <= 0 or block_size <= 0:
            raise ValueError("Window size and block size must be positive integers.")
            
        self.context_window_size = context_window_size
        self.block_size = block_size
        self.entity_registry: Dict[str, ConversationEntity] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.blocks: List[ConversationBlock] = []
        
        logger.info(f"Engine initialized with window size {context_window_size} and block size {block_size}")

    def _hash_content(self, content: str) -> str:
        """辅助函数：生成内容的哈希值"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def add_turn(self, role: str, content: str, extracted_entities: Optional[Dict[str, Any]] = None):
        """
        添加一轮对话
        
        Args:
            role (str): 角色
            content (str): 对话内容
            extracted_entities (Optional[Dict[str, Any]]): 从内容中提取的实体字典 {name: value}
        """
        if not content or not isinstance(content, str):
            logger.warning("Invalid content provided, skipping turn.")
            return

        turn_index = len(self.conversation_history)
        
        # 记录对话
        self.conversation_history.append({
            "role": role,
            "content": content,
            "index": turn_index
        })
        
        # 处理实体定义和引用
        # 这里模拟实体提取和定义过程
        if extracted_entities:
            for name, value in extracted_entities.items():
                self._define_entity(name, EntityType.CONTEXT_VAR, value, turn_index)
        
        # 检查是否需要创建新的基本块
        if turn_index > 0 and (turn_index + 1) % self.block_size == 0:
            self._create_block(turn_index - self.block_size + 1, turn_index)
            
        logger.debug(f"Added turn {turn_index}. Total entities: {len(self.entity_registry)}")

    def _define_entity(self, name: str, e_type: EntityType, value: Any, turn_idx: int):
        """定义或更新一个实体"""
        if name in self.entity_registry:
            # 如果实体已存在，更新其定义（类似于变量重新赋值）
            entity = self.entity_registry[name]
            entity.value = value
            entity.last_used_at = turn_idx
            entity.is_active = True
            logger.debug(f"Entity '{name}' updated at turn {turn_idx}")
        else:
            # 新实体
            entity = ConversationEntity(
                name=name,
                entity_type=e_type,
                value=value,
                defined_at=turn_idx,
                last_used_at=turn_idx
            )
            self.entity_registry[name] = entity
            logger.debug(f"Entity '{name}' defined at turn {turn_idx}")

    def _create_block(self, start_idx: int, end_idx: int):
        """创建并初始化一个基本块，计算Gen和Kill集合"""
        block_id = f"block_{len(self.blocks)}"
        new_block = ConversationBlock(block_id=block_id, start_index=start_idx, end_index=end_idx)
        
        # 简化的Gen/Kill分析：假设块内提到的实体都是生成的
        # 在实际场景中，这里会使用NLP模型提取引用和定义
        for i in range(start_idx, end_idx + 1):
            if i < len(self.conversation_history):
                # 模拟：如果实体在注册表中且定义时间在此块内，则加入Gen
                for entity in self.entity_registry.values():
                    if start_idx <= entity.defined_at <= end_idx:
                        new_block.gen_set.add(entity.name)
        
        self.blocks.append(new_block)
        logger.info(f"Created new conversation block {block_id} covering turns {start_idx}-{end_idx}")

    def perform_liveness_analysis(self) -> Dict[str, bool]:
        """
        核心函数：执行活跃变量分析
        
        通过后向数据流分析算法，计算每个基本块入口和出口的活跃实体集合。
        公式：
        out[B] = U (in[S]) for all successors S of B
        in[B] = use[B] U (out[B] - def[B])
        
        Returns:
            Dict[str, bool]: 实体名称到其活跃状态的映射
        """
        if not self.blocks:
            logger.warning("No blocks to analyze.")
            return {}

        # 初始化：所有块的LiveOut为空
        # 迭代直到不变点
        changed = True
        iterations = 0
        max_iterations = 100 # 防止无限循环

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            # 后向遍历基本块
            for block in reversed(self.blocks):
                # 计算LiveOut：后继块的LiveIn的并集
                # 这里简化为线性流，即当前块的LiveOut等于下一个块的LiveIn
                # 如果是CFG图结构，需要遍历所有后继
                current_live_out = set()
                
                # 寻找后继块（简化逻辑：链表结构）
                # 实际实现需要查找图结构
                block_idx = self.blocks.index(block)
                if block_idx + 1 < len(self.blocks):
                    successor = self.blocks[block_idx + 1]
                    current_live_out.update(successor.live_in)
                
                # 计算LiveIn
                current_live_in = block.gen_set.union(current_live_out.difference(block.kill_set))
                
                # 检查是否发生变化
                if current_live_in != block.live_in or current_live_out != block.live_out:
                    changed = True
                    block.live_in = current_live_in
                    block.live_out = current_live_out

        logger.info(f"Liveness analysis completed in {iterations} iterations.")
        
        # 更新全局实体注册表的活跃状态
        active_entities_map = {}
        final_live_set = self.blocks[0].live_in if self.blocks else set()
        
        for name, entity in self.entity_registry.items():
            is_alive = name in final_live_set
            entity.is_active = is_alive
            active_entities_map[name] = is_alive
            
        return active_entities_map

    def optimize_kv_cache(self) -> Tuple[Set[str], Set[str]]:
        """
        核心函数：基于活跃分析生成KV Cache优化策略
        
        识别哪些实体对应的KV对应该保留，哪些可以清除。
        
        Returns:
            Tuple[Set[str], Set[str]]: (保留实体集合, 清除实体集合)
        """
        if not self.perform_liveness_analysis():
            return set(), set()

        keep_entities = set()
        evict_entities = set()
        current_token_estimate = 0

        # 按照最后使用时间倒序排列，结合活跃状态
        sorted_entities = sorted(
            self.entity_registry.values(), 
            key=lambda e: e.last_used_at, 
            reverse=True
        )

        for entity in sorted_entities:
            # 模拟Token占用检查
            if current_token_estimate + entity.token_cost < self.context_window_size:
                if entity.is_active:
                    keep_entities.add(entity.name)
                    current_token_estimate += entity.token_cost
                else:
                    # 如果是不活跃实体，但在窗口内有空间，暂时保留（防止后续突然引用）
                    # 这里采用激进策略：不活跃即清除
                    evict_entities.add(entity.name)
                    logger.debug(f"Marking inactive entity '{entity.name}' for eviction.")
            else:
                # 窗口已满，即使活跃也需要进行裁剪（此处逻辑简化，实际需要更复杂的替换策略如LRU）
                # 标记为清除
                evict_entities.add(entity.name)
                logger.warning(f"Context window full. Entity '{entity.name}' marked for eviction to save space.")

        logger.info(f"KV Cache Optimization: Retain {len(keep_entities)}, Evict {len(evict_entities)}")
        return keep_entities, evict_entities

# 示例用法
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = LongContextStateEngine(context_window_size=1000, block_size=2)
    
    print("--- Starting Simulation ---")
    
    # 2. 模拟对话流
    # 第一轮
    engine.add_turn("user", "我想预订一张去北京的机票。", {"dest": "北京", "intent": "book_ticket"})
    
    # 第二轮
    engine.add_turn("system", "好的，请问您希望什么时间出发？", {"context": "waiting_for_time"})
    
    # 触发第一个Block的创建 (0-1)
    
    # 第三轮
    engine.add_turn("user", "明天下午三点。", {"time": "明天 15:00", "intent": "provide_time"})
    
    # 第四轮 - 'dest' (北京) 仍然被隐式引用，'intent' 变更为 confirm
    engine.add_turn("system", "已为您找到明天下午三点前往北京的航班CA123。", {"flight": "CA123"})
    
    # 触发第二个Block的创建 (2-3)
    
    # 3. 执行优化
    print("\nAnalyzing Context...")
    keep, evict = engine.optimize_kv_cache()
    
    print(f"\nActive Entities to Keep in KV Cache: {keep}")
    print(f"Dead Entities to Evict (Dead Code Elimination): {evict}")
    
    # 验证内部状态
    print("\nEntity Status:")
    for name, entity in engine.entity_registry.items():
        print(f" - {name}: Active={entity.is_active}, Defined@{entity.defined_at}, LastUsed@{entity.last_used_at}")