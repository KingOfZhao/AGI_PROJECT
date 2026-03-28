"""
Module: auto_context_state_memory_manager.py
Description: 动态上下文窗口与状态记忆管理器。

本模块实现了一个模拟人类工作记忆的动态上下文管理系统。
在AGI生成代码或处理长链条任务时，它通过注意力机制平衡
短期记忆（当前函数上下文）和长期记忆（项目全局结构）的权重，
确保在保持核心意图不变的前提下，根据任务进度动态调整上下文窗口。
"""

import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContextType(Enum):
    """上下文类型的枚举，区分短期和长期记忆。"""
    SHORT_TERM = "short_term"  # 当前工作上下文，如当前函数、变量
    LONG_TERM = "long_term"    # 全局上下文，如项目结构、核心意图

@dataclass
class MemoryItem:
    """单个记忆项的数据结构。"""
    content: Any
    timestamp: float = field(default_factory=time.time)
    relevance_score: float = 0.0
    type: ContextType = ContextType.SHORT_TERM

class DynamicContextManager:
    """
    动态上下文管理器。
    
    负责管理AGI编码过程中的上下文窗口，动态调整短期与长期记忆的权重。
    
    Attributes:
        core_intent (str): 任务的核心意图，通常不可变。
        memory_buffer (List[MemoryItem]): 记忆存储缓冲区。
        progress (float): 当前任务进度 (0.0 到 1.0)。
        decay_rate (float): 记忆衰减率。
        max_capacity (int): 上下文窗口的最大容量（Token数或条目数）。
    """

    def __init__(self, core_intent: str, max_capacity: int = 100, decay_rate: float = 0.05):
        """
        初始化管理器。
        
        Args:
            core_intent (str): 核心意图描述。
            max_capacity (int): 最大上下文容量。
            decay_rate (float): 时间衰减系数。
        """
        if not core_intent:
            raise ValueError("Core intent cannot be empty.")
        
        self.core_intent = core_intent
        self.memory_buffer: List[MemoryItem] = []
        self.progress: float = 0.0
        self.decay_rate = decay_rate
        self.max_capacity = max_capacity
        
        # 将核心意图作为最高优先级的长期记忆存入
        self.add_context("CORE_INTENT_DEFINITION", ContextType.LONG_TERM, relevance_score=1.0)
        logger.info(f"Context Manager initialized with intent: {core_intent}")

    def add_context(self, content: Any, context_type: ContextType, relevance_score: Optional[float] = None) -> None:
        """
        向管理器添加新的上下文信息。
        
        Args:
            content (Any): 上下文内容。
            context_type (ContextType): 上下文类型（短期/长期）。
            relevance_score (float, optional): 初始相关性分数，默认为0.5。
        """
        if content is None:
            logger.warning("Attempted to add None content to context, ignored.")
            return

        # 数据验证
        initial_score = relevance_score if relevance_score is not None else 0.5
        if not (0.0 <= initial_score <= 1.0):
            logger.error(f"Invalid relevance score: {initial_score}. Must be between 0 and 1.")
            initial_score = 0.5

        item = MemoryItem(
            content=content,
            type=context_type,
            relevance_score=initial_score
        )
        self.memory_buffer.append(item)
        logger.debug(f"Added {context_type.value} context: {str(content)[:30]}...")

    def update_progress(self, step: float) -> None:
        """
        更新当前任务进度，并触发上下文权重的动态调整。
        
        进度决定了短期记忆和长期记忆的权重分配策略。
        初期（0-30%）：短期记忆权重高，探索细节。
        中期（30-70%）：平衡。
        后期（70-100%）：长期记忆权重高，回归核心意图。
        
        Args:
            step (float): 当前进度值 (0.0 - 1.0)。
        """
        if not (0.0 <= step <= 1.0):
            logger.warning(f"Progress {step} out of bounds [0, 1]. Clamping.")
            self.progress = max(0.0, min(1.0, step))
        else:
            self.progress = step
        
        logger.info(f"Progress updated to: {self.progress * 100:.1f}%")
        self._adjust_window_weights()

    def _adjust_window_weights(self) -> None:
        """
        [辅助函数] 根据当前进度和时间衰减调整记忆权重。
        
        核心算法：
        1. 计算时间衰减因子。
        2. 根据进度计算动态权重因子。
        3. 更新每个记忆项的 relevance_score。
        """
        current_time = time.time()
        
        # 动态权重曲线：随着进度推进，长期记忆的重要性非线性增加
        # 示例：简单的线性插值或Sigmoid函数，这里使用简单的阈值策略演示
        long_term_boost = 0.0
        if self.progress > 0.7:
            long_term_boost = 0.5 * (self.progress - 0.7) / 0.3 # 后期增强

        for item in self.memory_buffer:
            # 1. 时间衰减
            time_delta = current_time - item.timestamp
            decay = 1.0 / (1.0 + self.decay_rate * time_delta)
            
            base_score = 0.5  # 基础分
            
            # 2. 类型权重调整
            if item.type == ContextType.LONG_TERM:
                type_weight = 0.8 + long_term_boost
            else:
                # 短期记忆在任务初期更重要
                type_weight = 0.9 - (self.progress * 0.4) 
            
            # 综合评分
            item.relevance_score = base_score * type_weight * decay
            
            # 确保分数在有效范围内
            item.relevance_score = max(0.0, min(1.0, item.relevance_score))

    def get_active_context(self) -> List[Dict[str, Any]]:
        """
        获取经过筛选和排序的当前活动上下文窗口。
        
        模拟人类工作记忆的“聚焦”功能，返回最相关的上下文片段。
        如果超出容量限制，将执行遗忘机制（移除低相关性项）。
        
        Returns:
            List[Dict[str, Any]]: 包含内容、类型和分数的字典列表。
        """
        # 按相关性降序排序
        sorted_memory = sorted(self.memory_buffer, key=lambda x: x.relevance_score, reverse=True)
        
        # 容量检查与遗忘机制
        if len(sorted_memory) > self.max_capacity:
            logger.info("Context capacity exceeded, pruning low-relevance memories.")
            # 保护核心意图（假设核心意图分数始终为1或最高）
            # 这里简单截断，实际应用中可能需要更复杂的遗忘策略
            pruned_memory = sorted_memory[:self.max_capacity]
            self.memory_buffer = pruned_memory
        
        # 格式化输出
        active_window = [
            {
                "content": item.content,
                "type": item.type.value,
                "relevance": round(item.relevance_score, 3)
            }
            for item in self.memory_buffer
        ]
        
        return active_window

def simulate_agi_coding_process(intent: str) -> None:
    """
    使用示例：模拟AGI系统使用此管理器生成代码的过程。
    
    Args:
        intent (str): 用户意图，例如 "Write a Python web scraper".
    """
    print(f"--- Starting AGI Task: {intent} ---")
    
    # 1. 初始化
    manager = DynamicContextManager(core_intent=intent, max_capacity=5)
    
    # 2. 阶段一：理解需求，加载短期细节
    manager.update_progress(0.1)
    manager.add_context("Import requests library", ContextType.SHORT_TERM)
    manager.add_context("Define target URL", ContextType.SHORT_TERM)
    
    # 3. 阶段二：编写代码，进入心流
    manager.update_progress(0.5)
    manager.add_context("Parse HTML structure", ContextType.SHORT_TERM)
    # 模拟一些全局信息的注入
    manager.add_context("Project Structure: src/utils/scraper.py", ContextType.LONG_TERM)
    
    # 4. 阶段三：收尾，检查是否符合核心意图
    manager.update_progress(0.9)
    # 此时，短期记忆（如具体变量名）权重下降，长期记忆（意图）权重上升
    manager.add_context("Handle exceptions", ContextType.SHORT_TERM)
    
    # 5. 获取最终上下文视图
    active_context = manager.get_active_context()
    
    print("\n--- Final Active Context Window ---")
    for item in active_context:
        print(f"[{item['type'].upper()}] Score: {item['relevance']} | Content: {item['content']}")
        
    print("-----------------------------------")

if __name__ == "__main__":
    # 运行示例
    try:
        simulate_agi_coding_process("Develop a REST API endpoint for user authentication")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")