"""
上下文感知型记忆垃圾回收器

该模块实现了一个智能的上下文管理器，专为AGI系统、长程对话模型或长文本生成任务设计。
它摒弃了传统的FIFO（先进先出）策略，转而采用类似JVM的“分代收集”算法。

核心逻辑：
1. 将对话历史分为年轻代和中年老代。
2. 热点数据（被频繁引用或包含关键实体的数据）会被提升至老年代，获得更高的“存活”优先级。
3. 垃圾数据（早期、低引用、非热点）会被压缩成摘要或直接丢弃。
4. 在保持上下文窗口不溢出的同时，最大化保留关键信息的密度。

作者: AGI Systems Architect
版本: 1.0.0
"""

import logging
import hashlib
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContextualMemoryGC")

@dataclass
class InteractionUnit:
    """
    对话交互单元。
    
    Attributes:
        role (str): 说话者角色 (e.g., 'user', 'assistant').
        content (str): 文本内容。
        timestamp (float): 创建时间戳。
        uid (str): 唯一标识符。
        access_count (int): 被引用/检索的次数。
        generation (int): 当前所处的代 (0=Young, 1=Old).
        entities (List[str]): 包含的关键实体/关键词。
    """
    role: str
    content: str
    timestamp: float = field(default_factory=datetime.now().timestamp)
    uid: str = field(default="", init=False)
    access_count: int = field(default=0, init=False)
    generation: int = field(default=0, init=False) # 0: Young, 1: Tenured
    entities: List[str] = field(default_factory=list, init=False)

    def __post_init__(self):
        # 生成基于内容的哈希UID
        hash_base = f"{self.role}:{self.content}:{self.timestamp}"
        self.uid = hashlib.md5(hash_base.encode()).hexdigest()[:8]
        
    def count_tokens(self) -> int:
        """简单的Token估算逻辑 (Char/4)。"""
        return max(1, len(self.content) // 4)

class ContextualMemoryGC:
    """
    上下文感知型记忆垃圾回收器。
    
    管理对话历史，执行分代GC策略以优化长程记忆。
    """

    def __init__(
        self, 
        max_tokens: int = 4096, 
        young_gen_threshold: int = 5,
        promotion_threshold: int = 3,
        compression_ratio: float = 0.3
    ):
        """
        初始化垃圾回收器。
        
        Args:
            max_tokens (int): 上下文窗口的最大Token限制。
            young_gen_threshold (int): 触发Minor GC的年轻代轮次阈值。
            promotion_threshold (int): 晋升到老年代所需的最小引用次数。
            compression_ratio (float): 压缩摘要时的目标长度比例。
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
            
        self.max_tokens = max_tokens
        self.young_gen_threshold = young_gen_threshold
        self.promotion_threshold = promotion_threshold
        self.compression_ratio = compression_ratio
        
        # 存储结构
        self.young_generation: List[InteractionUnit] = []
        self.old_generation: List[InteractionUnit] = []
        self.summary_pool: List[str] = [] # 存储被压缩的历史摘要
        
        # 统计信息
        self.gc_cycles = 0
        self.current_tokens = 0

    def _extract_entities(self, text: str) -> List[str]:
        """
        辅助函数：从文本中提取关键实体（模拟NER）。
        在实际AGI应用中，这里应接入NLP模型。
        """
        # 模拟：提取全大写单词或特定长度的单词作为关键实体
        words = text.split()
        # 简单规则：长度大于6的词视为潜在关键实体，或包含特定标记
        entities = [w for w in words if len(w) > 6 or w.isupper()]
        return list(set(entities))

    def add_interaction(self, role: str, content: str) -> None:
        """
        添加新的交互到年轻代。
        
        Args:
            role (str): 角色。
            content (str): 内容。
        """
        if not content or not isinstance(content, str):
            logger.warning("Invalid content provided, skipping.")
            return

        unit = InteractionUnit(role=role, content=content)
        unit.entities = self._extract_entities(content)
        
        self.young_generation.append(unit)
        self.current_tokens += unit.count_tokens()
        
        logger.debug(f"Added interaction {unit.uid}. Current tokens: {self.current_tokens}")
        
        # 触发GC检查
        if len(self.young_generation) >= self.young_gen_threshold:
            self.run_gc_cycle()

    def get_context_window(self) -> List[Dict[str, Any]]:
        """
        获取经过GC管理后的、可直接用于LLM输入的上下文窗口。
        
        Returns:
            List[Dict]: 包含 'role' 和 'content' 的字典列表。
        """
        context = []
        
        # 1. 如果存在摘要池，优先加入（作为长程记忆的压缩表示）
        if self.summary_pool:
            summary_text = f"[Historical Summary]: {' '.join(self.summary_pool[-3:])}" # 保留最近几个摘要
            context.append({"role": "system", "content": summary_text})
            
        # 2. 加入老年代（高价值历史）
        for unit in self.old_generation:
            context.append({"role": unit.role, "content": unit.content})
            
        # 3. 加入年轻代（近期交互）
        for unit in self.young_generation:
            context.append({"role": unit.role, "content": unit.content})
            
        return context

    def _compress_units(self, units: List[InteractionUnit]) -> str:
        """
        核心函数：将多个交互单元压缩为一个摘要文本。
        模拟LLM摘要过程。
        """
        combined_text = " ".join([u.content for u in units])
        # 模拟压缩：只取前N%和关键实体
        keep_len = int(len(combined_text) * self.compression_ratio)
        entities_flat = " ".join(list(set([e for u in units for e in u.entities])))[:100]
        
        simulated_summary = f"Summary of {len(units)} turns: {combined_text[:keep_len]}... [Keywords: {entities_flat}]"
        logger.info(f"Compressed {len(units)} units into summary.")
        return simulated_summary

    def run_gc_cycle(self) -> Tuple[int, int]:
        """
        核心函数：执行分代垃圾回收周期。
        
        策略：
        1. Minor GC: 扫描年轻代。
           - 引用次数高的 -> 晋升到老年代。
           - 引用次数低的 -> 标记为垃圾。
        2. Major GC (Conditional): 如果Token依然超限，清理老年代或进行压缩。
        
        Returns:
            Tuple[int, int]: (释放的Token数, 压缩的交互数)
        """
        self.gc_cycles += 1
        logger.info(f"Starting GC Cycle #{self.gc_cycles}. Current Tokens: {self.current_tokens}")
        
        survivors: List[InteractionUnit] = []
        garbage: List[InteractionUnit] = []
        promoted_count = 0
        
        # --- Minor GC Phase ---
        for unit in self.young_generation:
            # 模拟引用更新：如果老年代中有关联实体，增加访问计数
            # 这里使用简单的启发式：如果内容包含之前的实体，视为引用
            for old_unit in self.old_generation:
                if set(unit.entities) & set(old_unit.entities):
                    unit.access_count += 1
            
            # 晋升判断
            if unit.access_count >= self.promotion_threshold:
                unit.generation = 1
                self.old_generation.append(unit)
                promoted_count += 1
                logger.debug(f"Promoted unit {unit.uid} to Old Generation.")
            else:
                # 保留在年轻代还是回收？
                # 这里为了演示，将早期且低引用的直接视为垃圾
                # 实际上这里应该更复杂（如滑动窗口）
                garbage.append(unit)

        # 年轻代现在只保留最近的、未被晋升但还没到GC时间的，或者清空
        # 本策略：Minor GC 清除非热点早期数据
        # 假设年轻代超过阈值的部分全是垃圾（简化FIFO+标记清除的结合）
        if len(self.young_generation) > self.young_gen_threshold // 2:
             # 将最旧的一部分低引用数据移入garbage
             pass # 上面的循环已经分类完毕，这里我们用survivors替换
            
        # 此处简化逻辑：没有被晋升的，且是旧数据的，进入压缩流程
        # 清空年轻代，未晋升的视作待处理
        self.young_generation = [] 
        
        # 处理垃圾：压缩并放入Summary Pool
        if garbage:
            summary = self._compress_units(garbage)
            self.summary_pool.append(summary)
            # 释放Token计数 (简化计算)
            freed_tokens = sum(u.count_tokens() for u in garbage)
            self.current_tokens -= freed_tokens
            # 摘要本身也占Token
            self.current_tokens += len(summary) // 4 
            
        logger.info(f"GC Finished. Promoted: {promoted_count}, Compressed: {len(garbage)}")
        
        # --- Major GC Phase (如果超限) ---
        if self.current_tokens > self.max_tokens:
            self._handle_overflow()
            
        return freed_tokens, len(garbage)

    def _handle_overflow(self) -> None:
        """
        辅助函数：处理严重的内存溢出。
        策略：丢弃最老的老年代数据，或者重新压缩摘要。
        """
        logger.warning("Context overflow detected! Running aggressive cleanup.")
        if self.old_generation:
            # 移除最老的一个单元
            removed = self.old_generation.pop(0)
            self.current_tokens -= removed.count_tokens()
            logger.info(f"Dropped oldest unit from Old Gen: {removed.uid}")
        
        # 如果摘要池太大，合并摘要
        if len(self.summary_pool) > 5:
            combined = " | ".join(self.summary_pool)
            self.summary_pool = [f"Consolidated History: {combined[:500]}..."]
            self.current_tokens = self._recalculate_tokens()

    def _recalculate_tokens(self) -> int:
        """重新计算当前总Token数，防止漂移。"""
        total = 0
        for u in self.young_generation:
            total += u.count_tokens()
        for u in self.old_generation:
            total += u.count_tokens()
        for s in self.summary_pool:
            total += len(s) // 4
        return total

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 初始化GC管理器
    gc_manager = ContextualMemoryGC(
        max_tokens=1000, 
        young_gen_threshold=5,
        promotion_threshold=2
    )
    
    print("=== 模拟长程对话 ===")
    
    # 1. 添加一些关于"Python"的对话（应该成为热点）
    gc_manager.add_interaction("user", "我想学习Python编程。")
    gc_manager.add_interaction("assistant", "当然，建议从Python官方文档开始。")
    # 模拟再次引用，触发晋升逻辑（在实际流中，这需要跨轮次引用检测，这里简化模拟）
    # 在run_gc_cycle中，如果后续对话包含"Python"，之前的对话会被标记引用
    
    # 2. 添加一些无关紧要的闲聊（垃圾候选）
    gc_manager.add_interaction("user", "今天天气真好啊。")
    gc_manager.add_interaction("assistant", "是的，阳光明媚。")
    gc_manager.add_interaction("user", "午饭吃了什么？") # 触发GC阈值 (5条)
    
    # 3. 手动触发引用模拟（正常情况下由检索机制完成）
    # 假设我们通过检索再次访问了第一条数据
    if gc_manager.young_generation:
        gc_manager.young_generation[0].access_count += 2 # 人为提升热度

    # 4. 添加更多对话，包含热点关键词 "Python"
    gc_manager.add_interaction("user", "Python有什么好的Web框架？") # 包含Python关键词
    gc_manager.add_interaction("assistant", "Django和Flask是流行的Python框架。")
    
    # 此时运行GC
    print("\n>>> 运行GC周期...")
    gc_manager.run_gc_cycle()
    
    # 5. 查看结果
    print("\n=== 当前上下文窗口内容 ===")
    context = gc_manager.get_context_window()
    for item in context:
        print(f"[{item['role']}]: {item['content'][:50]}...")
        
    print(f"\n剩余Token估计: {gc_manager.current_tokens}")
    print(f"老年代数据量: {len(gc_manager.old_generation)}")
    print(f"摘要池数量: {len(gc_manager.summary_pool)}")
