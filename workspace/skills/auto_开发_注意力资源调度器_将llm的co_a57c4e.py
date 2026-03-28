"""
高级注意力资源调度器

该模块实现了一个模拟编译器寄存器分配机制的上下文管理器。
将LLM的Context Window视为有限的寄存器堆，将外部向量数据库视为内存。
通过计算知识块的活跃度和冲突，决定信息的驻留、驱逐和加载。

版权所有 (C) 2023 AGI Systems. 保留所有权利。
"""

import heapq
import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BlockType(Enum):
    """知识块类型枚举"""
    TEMPORARY = auto()    # 临时数据，优先驱逐
    GENERAL = auto()      # 普通数据
    CALLEE_SAVED = auto() # 类似"被调用者保存"寄存器，核心上下文，尽量常驻
    VOLATILE = auto()     # 易失性数据，每次任务后可自动清理

@dataclass(order=True)
class KnowledgeBlock:
    """
    知识块数据结构
    
    属性:
        id: 块的唯一标识符
        content: 文本内容或数据载荷
        embedding: 向量嵌入表示
        block_type: 块的类型（决定保留优先级基础）
        token_count: 占用的token数量
        access_frequency: 被访问的频率
        last_access_time: 最后一次访问的逻辑时间戳
        scope_ids: 关联的作用域ID集合（用于冲突分析）
        priority_score: 计算出的优先级分数（越高越重要）
    """
    id: str
    content: str
    embedding: List[float]
    block_type: BlockType
    token_count: int
    access_frequency: int = 0
    last_access_time: int = 0
    scope_ids: Set[str] = field(default_factory=set)
    priority_score: float = field(default=0.0, compare=True)

    def __post_init__(self):
        if not isinstance(self.scope_ids, set):
            self.scope_ids = set(self.scope_ids)

class ContextWindowOverflowError(Exception):
    """上下文窗口溢出异常"""
    pass

class AttentionScheduler:
    """
    注意力资源调度器
    
    使用类似寄存器分配的图着色算法思想来管理LLM上下文。
    """
    
    def __init__(self, max_context_tokens: int = 4096, spill_threshold: float = 0.85):
        """
        初始化调度器
        
        Args:
            max_context_tokens: 上下文窗口最大token数
            spill_threshold: 触发Spilling机制的占用率阈值 (0.0-1.0)
        """
        if max_context_tokens <= 0:
            raise ValueError("Context window size must be positive")
        
        self.max_context_tokens = max_context_tokens
        self.spill_threshold = spill_threshold
        
        # 寄存器堆
        self.context_blocks: Dict[str, KnowledgeBlock] = {}
        # 外部存储
        self.vector_db_buffer: Dict[str, KnowledgeBlock] = {}
        # 冲突图: 记录ID之间的冲突权重
        self.conflict_graph: Dict[str, Dict[str, float]] = {}
        
        self.current_token_usage = 0
        self.logical_time = 0
        
        logger.info(f"Scheduler initialized with {max_context_tokens} token capacity.")

    def _calculate_liveness_score(self, block: KnowledgeBlock) -> float:
        """
        辅助函数：计算知识块的活跃度分数
        
        类似于编译器中的活跃变量分析。
        结合访问频率、时间衰减和类型权重。
        """
        # 时间衰减因子
        time_decay = 1.0 / (1.0 + math.log1p(self.logical_time - block.last_access_time))
        
        # 类型权重
        type_weights = {
            BlockType.CALLEE_SAVED: 10.0,
            BlockType.GENERAL: 1.0,
            BlockType.TEMPORARY: 0.5,
            BlockType.VOLATILE: 0.1
        }
        weight = type_weights.get(block.block_type, 1.0)
        
        # 综合分数
        score = (block.access_frequency * time_decay * weight)
        return score

    def _update_conflict_graph(self, active_blocks: List[KnowledgeBlock]):
        """
        更新冲突图
        
        如果两个块在同一次任务上下文中被一起使用，则增加它们之间的边权重。
        这有助于决定哪些块应该被分配在同一个"寄存器"中。
        """
        block_ids = [b.id for b in active_blocks]
        for i in range(len(block_ids)):
            for j in range(i + 1, len(block_ids)):
                id1, id2 = block_ids[i], block_ids[j]
                
                if id1 not in self.conflict_graph:
                    self.conflict_graph[id1] = {}
                if id2 not in self.conflict_graph:
                    self.conflict_graph[id2] = {}
                
                # 增加连接强度
                self.conflict_graph[id1][id2] = self.conflict_graph[id1].get(id2, 0) + 1.0
                self.conflict_graph[id2][id1] = self.conflict_graph[id2].get(id1, 0) + 1.0

    def allocate(self, blocks: List[KnowledgeBlock]) -> Tuple[List[KnowledgeBlock], List[str]]:
        """
        核心函数：将知识块分配到上下文窗口（寄存器分配）
        
        处理流程:
        1. 计算当前使用量
        2. 如果空间不足，根据活跃度分数进行 Spilling
        3. 加载新的块
        
        Returns:
            Tuple[List[KnowledgeBlock], List[str]]: 
                - 当前上下文中的所有块
                - 被踢出到Vector DB的块ID列表
        """
        self.logical_time += 1
        spilled_ids = []
        
        # 1. 更新冲突图
        self._update_conflict_graph(blocks)
        
        # 计算新块所需的容量
        incoming_tokens = sum(b.token_count for b in blocks)
        
        # 检查是否需要 Spilling
        current_usage_ratio = (self.current_token_usage + incoming_tokens) / self.max_context_tokens
        
        if current_usage_ratio > self.spill_threshold:
            logger.info(f"Threshold exceeded ({current_usage_ratio:.2f}), initiating spilling...")
            spilled_ids = self._spill_to_db(required_space=incoming_tokens)
        
        # 加载新块
        for block in blocks:
            if block.id not in self.context_blocks:
                self.context_blocks[block.id] = block
                self.current_token_usage += block.token_count
            
            # 更新访问统计
            self.context_blocks[block.id].last_access_time = self.logical_time
            self.context_blocks[block.id].access_frequency += 1
        
        # 边界检查
        if self.current_token_usage > self.max_context_tokens:
            raise ContextWindowOverflowError(
                f"Fatal: Context overflow even after spilling. "
                f"Usage: {self.current_token_usage}, Max: {self.max_context_tokens}"
            )
            
        return list(self.context_blocks.values()), spilled_ids

    def _spill_to_db(self, required_space: int) -> List[str]:
        """
        核心函数：将低优先级数据踢出到外部存储
        
        使用基于堆的选择算法，优先保留：
        1. Callee-saved 类型的块
        2. 活跃度高的块
        
        Args:
            required_space: 需要腾出的token空间
            
        Returns:
            被移除的块ID列表
        """
        candidates = []
        
        # 构建候选驱逐堆 (最小堆，优先驱逐分数低的)
        for block in self.context_blocks.values():
            # Callee-saved 类型的块很难被驱逐，给予巨大的负分（如果是最小堆，则需要反转逻辑）
            # 这里我们使用最大堆来保留好的，或者用最小堆来找最差的。
            # 为了简单，我们计算一个 'eviction_cost'，越低越容易被踢。
            
            if block.block_type == BlockType.CALLEE_SAVED:
                cost = float('inf') # 几乎不可被踢
            else:
                cost = self._calculate_liveness_score(block)
            
            # 使用最小堆，堆顶是代价最小的（最该被踢的）
            # Python heapq 是最小堆
            heapq.heappush(candidates, (cost, block.id, block))
            
        spilled_ids = []
        freed_tokens = 0
        
        while candidates and freed_tokens < required_space:
            cost, bid, block = heapq.heappop(candidates)
            
            # 双重检查，防止踢出关键数据导致错误
            if block.block_type == BlockType.CALLEE_SAVED:
                continue # 跳过核心数据，宁愿报错也不破坏核心逻辑
            
            # 执行 Spilling
            logger.debug(f"Spilling block {bid} with cost {cost}")
            
            # 移动到 Vector DB
            self.vector_db_buffer[bid] = block
            del self.context_blocks[bid]
            
            spilled_ids.append(bid)
            freed_tokens += block.token_count
            
        self.current_token_usage -= freed_tokens
        logger.info(f"Spilled {len(spilled_ids)} blocks, freed {freed_tokens} tokens.")
        return spilled_ids

    def retrieve_from_db(self, block_id: str) -> Optional[KnowledgeBlock]:
        """
        从外部存储加载数据回上下文
        
        类似于 Load from Memory.
        """
        if block_id in self.vector_db_buffer:
            logger.info(f"Loading block {block_id} from Vector DB to Context.")
            block = self.vector_db_buffer.pop(block_id)
            # 重新分配会自动处理空间检查
            self.allocate([block])
            return block
        return None

# 使用示例
if __name__ == "__main__":
    # 初始化调度器
    scheduler = AttentionScheduler(max_context_tokens=1000)
    
    # 模拟数据
    block_a = KnowledgeBlock(
        id="sys_prompt", 
        content="System Instructions...", 
        embedding=[0.1]*128, 
        block_type=BlockType.CALLEE_SAVED, 
        token_count=200
    )
    
    block_b = KnowledgeBlock(
        id="user_query", 
        content="What is AGI?", 
        embedding=[0.2]*128, 
        block_type=BlockType.TEMPORARY, 
        token_count=50
    )
    
    # 1. 分配系统提示词（常驻）
    current_ctx, _ = scheduler.allocate([block_a])
    print(f"Current Usage: {scheduler.current_token_usage}")
    
    # 2. 分配用户查询
    current_ctx, _ = scheduler.allocate([block_b])
    print(f"Current Usage: {scheduler.current_token_usage}")
    
    # 3. 模拟大量数据涌入导致 Spilling
    large_blocks = [
        KnowledgeBlock(f"doc_{i}", f"content {i}", [0.3]*128, BlockType.GENERAL, 300)
        for i in range(5)
    ]
    
    try:
        # 这里应该会触发 spilling，因为 200 + 50 + 300*5 > 1000
        # block_b (TEMPORARY) 应该会被优先踢出，block_a (CALLEE_SAVED) 应该保留
        _, spilled = scheduler.allocate(large_blocks)
        print(f"Spilled IDs: {spilled}")
        print(f"Block 'user_query' in context: {'user_query' in scheduler.context_blocks}")
        print(f"Block 'sys_prompt' in context: {'sys_prompt' in scheduler.context_blocks}")
    except ContextWindowOverflowError as e:
        print(f"Error: {e}")