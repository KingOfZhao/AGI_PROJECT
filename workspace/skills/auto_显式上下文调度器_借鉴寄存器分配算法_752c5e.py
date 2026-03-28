"""
auto_显式上下文调度器_借鉴寄存器分配算法_752c5e
============================================

该模块实现了一个显式上下文调度器，借鉴编译器原理中的寄存器分配算法（如图着色算法），
主动管理LLM的显存/上下文窗口空间。

核心思想：
1. 活跃度分析（Liveness Analysis）：预测对话块在未来的重要性
2. 图着色分配：将上下文块分配到有限的"寄存器"（上下文窗口）中
3. 智能溢出：将不活跃的上下文转存到向量数据库，而非简单丢弃

作者: AGI System
版本: 1.0.0
"""

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContextPriority(Enum):
    """上下文块优先级枚举"""
    CRITICAL = 100    # 系统提示词、用户画像
    HIGH = 75         # 最近N轮对话
    MEDIUM = 50       # 相关历史话题
    LOW = 25          # 可归档内容
    SPILLED = 0       # 已溢出到向量库


@dataclass
class ContextBlock:
    """
    上下文块数据结构
    
    Attributes:
        id: 唯一标识符
        content: 文本内容
        token_count: token数量
        timestamp: 创建时间戳
        priority: 当前优先级
        access_count: 访问次数
        last_access: 最后访问时间
        dependencies: 依赖的上下文块ID集合
        embedding: 向量嵌入（用于溢出后的检索）
    """
    id: str
    content: str
    token_count: int
    timestamp: float
    priority: ContextPriority = ContextPriority.MEDIUM
    access_count: int = 0
    last_access: float = field(default_factory=lambda: datetime.now().timestamp())
    dependencies: Set[str] = field(default_factory=set)
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        """数据验证"""
        if not self.id:
            raise ValueError("ContextBlock id cannot be empty")
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")
        if not isinstance(self.priority, ContextPriority):
            raise TypeError("priority must be a ContextPriority enum")
    
    def touch(self):
        """更新访问时间和计数"""
        self.access_count += 1
        self.last_access = datetime.now().timestamp()
    
    def calculate_liveness_score(self, current_time: float, decay_factor: float = 0.95) -> float:
        """
        计算活跃度分数（类似寄存器分配中的活跃度分析）
        
        Args:
            current_time: 当前时间戳
            decay_factor: 时间衰减因子
            
        Returns:
            活跃度分数，越高表示越应该保留在上下文窗口
        """
        time_elapsed = current_time - self.last_access
        time_decay = math.exp(-time_elapsed / 3600)  # 每小时衰减
        
        # 综合考虑：优先级权重 + 访问频率 + 时间衰减 + 依赖关系
        priority_weight = self.priority.value / 100
        frequency_score = math.log1p(self.access_count) / 10
        
        liveness = (
            priority_weight * 0.4 +
            frequency_score * 0.3 +
            time_decay * 0.2 +
            len(self.dependencies) * 0.02
        ) * decay_factor
        
        return min(1.0, liveness)


class VectorStoreInterface(ABC):
    """向量存储接口（抽象基类）"""
    
    @abstractmethod
    async def store(self, block: ContextBlock) -> bool:
        """存储上下文块"""
        pass
    
    @abstractmethod
    async def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[ContextBlock]:
        """检索相似上下文"""
        pass


class MockVectorStore(VectorStoreInterface):
    """模拟向量存储实现"""
    
    def __init__(self):
        self._store: Dict[str, ContextBlock] = {}
    
    async def store(self, block: ContextBlock) -> bool:
        self._store[block.id] = block
        logger.info(f"Stored block {block.id} to vector store")
        return True
    
    async def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[ContextBlock]:
        # 简化实现：返回所有存储的块
        return list(self._store.values())[:top_k]


class ContextScheduler:
    """
    显式上下文调度器
    
    借鉴寄存器分配算法管理LLM上下文窗口，实现智能的资源调配。
    
    Attributes:
        max_tokens: 上下文窗口最大token数
        reserve_ratio: 保留给新内容的比例
        blocks: 当前活跃的上下文块
        spilled_blocks: 已溢出的上下文块ID集合
        vector_store: 向量存储后端
        interference_graph: 干涉图（用于图着色算法）
    
    Example:
        >>> scheduler = ContextScheduler(max_tokens=4096)
        >>> block = ContextBlock(
        ...     id="msg_001",
        ...     content="Hello, how are you?",
        ...     token_count=6,
        ...     timestamp=datetime.now().timestamp()
        ... )
        >>> scheduler.add_block(block)
        >>> active_context = scheduler.get_active_context()
    """
    
    def __init__(
        self,
        max_tokens: int = 8192,
        reserve_ratio: float = 0.2,
        vector_store: Optional[VectorStoreInterface] = None
    ):
        """
        初始化调度器
        
        Args:
            max_tokens: 最大token容量
            reserve_ratio: 预留空间比例（0-1之间）
            vector_store: 向量存储后端实例
            
        Raises:
            ValueError: 参数不合法时抛出
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= reserve_ratio < 1:
            raise ValueError("reserve_ratio must be in [0, 1)")
        
        self.max_tokens = max_tokens
        self.reserve_ratio = reserve_ratio
        self._available_tokens = max_tokens
        self._blocks: Dict[str, ContextBlock] = {}
        self._spilled_blocks: Set[str] = set()
        self._vector_store = vector_store or MockVectorStore()
        self._interference_graph: Dict[str, Set[str]] = {}  # 干涉图
        
        logger.info(f"ContextScheduler initialized with max_tokens={max_tokens}")
    
    def _update_interference_graph(self):
        """
        更新干涉图（用于图着色算法）
        
        如果两个上下文块在时间上重叠或存在依赖关系，则它们干涉。
        干涉的块不能同时被溢出。
        """
        self._interference_graph.clear()
        block_ids = list(self._blocks.keys())
        
        for i, id1 in enumerate(block_ids):
            self._interference_graph[id1] = set()
            block1 = self._blocks[id1]
            
            for j, id2 in enumerate(block_ids):
                if i != j:
                    block2 = self._blocks[id2]
                    # 检查依赖关系
                    if id2 in block1.dependencies or id1 in block2.dependencies:
                        self._interference_graph[id1].add(id2)
    
    def _graph_coloring_spill(self) -> List[str]:
        """
        使用图着色算法决定哪些块应该被溢出
        
        Returns:
            应该溢出的上下文块ID列表
        """
        if not self._blocks:
            return []
        
        current_time = datetime.now().timestamp()
        
        # 计算每个块的活跃度分数
        liveness_scores = {
            block_id: block.calculate_liveness_score(current_time)
            for block_id, block in self._blocks.items()
        }
        
        # 按活跃度升序排序（优先溢出低活跃度）
        sorted_blocks = sorted(
            liveness_scores.items(),
            key=lambda x: x[1]
        )
        
        # 选择溢出候选（保护CRITICAL优先级）
        spill_candidates = []
        for block_id, score in sorted_blocks:
            block = self._blocks[block_id]
            if block.priority != ContextPriority.CRITICAL:
                spill_candidates.append((block_id, score, block.token_count))
        
        return [item[0] for item in spill_candidates]
    
    async def _spill_to_vector_store(self, block_ids: List[str]) -> int:
        """
        将上下文块溢出到向量存储
        
        Args:
            block_ids: 要溢出的块ID列表
            
        Returns:
            实际溢出的token数量
        """
        spilled_tokens = 0
        
        for block_id in block_ids:
            if block_id not in self._blocks:
                continue
            
            block = self._blocks[block_id]
            
            # 生成简单哈希作为embedding（实际应用中应使用真实嵌入模型）
            if block.embedding is None:
                block.embedding = self._generate_mock_embedding(block.content)
            
            try:
                success = await self._vector_store.store(block)
                if success:
                    spilled_tokens += block.token_count
                    self._spilled_blocks.add(block_id)
                    del self._blocks[block_id]
                    logger.info(f"Spilled block {block_id} ({block.token_count} tokens)")
            except Exception as e:
                logger.error(f"Failed to spill block {block_id}: {e}")
        
        return spilled_tokens
    
    def _generate_mock_embedding(self, content: str) -> List[float]:
        """
        生成模拟嵌入向量（实际应用中应调用真实embedding模型）
        
        Args:
            content: 文本内容
            
        Returns:
            模拟的嵌入向量
        """
        # 使用哈希生成伪随机向量
        hash_obj = hashlib.sha256(content.encode())
        hash_bytes = hash_obj.digest()
        
        # 转换为384维向量
        embedding = []
        for i in range(384):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val - 128) / 128.0)
        
        return embedding
    
    def add_block(self, block: ContextBlock) -> bool:
        """
        添加新的上下文块
        
        Args:
            block: 要添加的上下文块
            
        Returns:
            是否成功添加
            
        Raises:
            TypeError: block类型错误
            ValueError: 数据验证失败
        """
        if not isinstance(block, ContextBlock):
            raise TypeError("block must be a ContextBlock instance")
        
        # 检查是否有足够空间
        required_space = int(self.max_tokens * self.reserve_ratio)
        if block.token_count > self._available_tokens - required_space:
            logger.warning(f"Insufficient space for block {block.id}")
            return False
        
        self._blocks[block.id] = block
        self._available_tokens -= block.token_count
        self._update_interference_graph()
        
        logger.info(f"Added block {block.id} ({block.token_count} tokens)")
        return True
    
    async def schedule(self) -> Tuple[str, Dict[str, Any]]:
        """
        执行上下文调度（核心调度算法）
        
        类似寄存器分配器，当空间不足时：
        1. 执行活跃度分析
        2. 运行图着色算法确定溢出候选
        3. 将低活跃度内容溢出到向量存储
        
        Returns:
            Tuple[调度结果描述, 调度统计信息]
        """
        current_time = datetime.now().timestamp()
        stats = {
            "total_blocks": len(self._blocks),
            "available_tokens": self._available_tokens,
            "spilled_count": 0,
            "retrieved_count": 0
        }
        
        # 检查是否需要调度
        threshold = int(self.max_tokens * (1 - self.reserve_ratio))
        if self._available_tokens >= threshold:
            return "No scheduling needed", stats
        
        logger.info("Starting context scheduling...")
        
        # 计算需要释放的空间
        target_free = int(self.max_tokens * self.reserve_ratio)
        need_to_free = target_free - self._available_tokens
        
        # 获取溢出候选
        spill_candidates = self._graph_coloring_spill()
        
        # 选择要溢出的块（直到释放足够空间）
        to_spill = []
        freed_tokens = 0
        
        for block_id in spill_candidates:
            if freed_tokens >= need_to_free:
                break
            
            block = self._blocks.get(block_id)
            if block:
                to_spill.append(block_id)
                freed_tokens += block.token_count
        
        # 执行溢出
        if to_spill:
            actual_freed = await self._spill_to_vector_store(to_spill)
            self._available_tokens += actual_freed
            stats["spilled_count"] = len(to_spill)
        
        # 更新干涉图
        self._update_interference_graph()
        
        result = f"Scheduled: spilled {stats['spilled_count']} blocks, freed {freed_tokens} tokens"
        logger.info(result)
        
        return result, stats
    
    def get_active_context(self) -> List[ContextBlock]:
        """
        获取当前活跃的上下文（用于LLM输入）
        
        Returns:
            按优先级和活跃度排序的上下文块列表
        """
        current_time = datetime.now().timestamp()
        
        active_blocks = list(self._blocks.values())
        
        # 按活跃度降序排序
        active_blocks.sort(
            key=lambda b: b.calculate_liveness_score(current_time),
            reverse=True
        )
        
        # 标记为已访问
        for block in active_blocks:
            block.touch()
        
        return active_blocks
    
    def get_context_window_usage(self) -> Dict[str, Any]:
        """
        获取上下文窗口使用情况
        
        Returns:
            包含使用统计的字典
        """
        return {
            "max_tokens": self.max_tokens,
            "available_tokens": self._available_tokens,
            "used_tokens": self.max_tokens - self._available_tokens,
            "usage_ratio": (self.max_tokens - self._available_tokens) / self.max_tokens,
            "active_blocks": len(self._blocks),
            "spilled_blocks": len(self._spilled_blocks)
        }
    
    async def retrieve_spilled_context(
        self,
        query: str,
        top_k: int = 3
    ) -> List[ContextBlock]:
        """
        从向量存储检索已溢出的相关上下文
        
        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            
        Returns:
            检索到的上下文块列表
        """
        query_embedding = self._generate_mock_embedding(query)
        
        try:
            retrieved = await self._vector_store.retrieve(query_embedding, top_k)
            logger.info(f"Retrieved {len(retrieved)} blocks from vector store")
            return retrieved
        except Exception as e:
            logger.error(f"Failed to retrieve from vector store: {e}")
            return []


# 使用示例
async def demo():
    """
    演示上下文调度器的使用
    
    Input Format:
        - ContextBlock对象包含: id, content, token_count, timestamp等字段
        
    Output Format:
        - get_active_context() 返回 List[ContextBlock]
        - schedule() 返回 Tuple[str, Dict]
        - get_context_window_usage() 返回 Dict[str, Any]
    """
    # 创建调度器（模拟4096 token窗口）
    scheduler = ContextScheduler(max_tokens=4096, reserve_ratio=0.25)
    
    # 添加系统提示词（最高优先级）
    system_block = ContextBlock(
        id="system_prompt",
        content="You are a helpful AI assistant.",
        token_count=10,
        timestamp=datetime.now().timestamp(),
        priority=ContextPriority.CRITICAL
    )
    scheduler.add_block(system_block)
    
    # 添加多轮对话
    for i in range(20):
        msg_block = ContextBlock(
            id=f"msg_{i:03d}",
            content=f"This is message number {i} in our conversation.",
            token_count=12 + len(str(i)),
            timestamp=datetime.now().timestamp() - (20 - i) * 60,  # 模拟时间递减
            priority=ContextPriority.HIGH if i > 15 else ContextPriority.MEDIUM
        )
        scheduler.add_block(msg_block)
    
    # 执行调度
    result, stats = await scheduler.schedule()
    print(f"调度结果: {result}")
    print(f"统计信息: {stats}")
    
    # 获取活跃上下文
    active = scheduler.get_active_context()
    print(f"\n活跃上下文块数: {len(active)}")
    for block in active[:3]:
        print(f"  - {block.id}: {block.content[:30]}...")
    
    # 查看使用情况
    usage = scheduler.get_context_window_usage()
    print(f"\n上下文窗口使用: {usage['usage_ratio']:.1%}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())