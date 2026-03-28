"""
Module: auto_cognitive_kernel.py
Description: 实现自优化认知内核，通过分析人机交互历史，动态编译针对特定用户的专用Prompt语境，
             实现通用知识的内联与冗余推理的削减。
Author: Senior Python Engineer (AGI System Component)
Date: 2023-10-27
Version: 1.0.0
"""

import json
import logging
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveKernel")

class InteractionType(Enum):
    """交互类型枚举"""
    QUERY = "query"
    COMMAND = "command"
    FEEDBACK = "feedback"

@dataclass
class InteractionRecord:
    """单次人机交互记录的数据结构"""
    timestamp: float
    user_input: str
    system_response: str
    interaction_type: InteractionType
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将记录转换为字典"""
        return {
            "timestamp": self.timestamp,
            "user_input": self.user_input,
            "system_response": self.system_response,
            "type": self.interaction_type.value,
            "latency": self.latency_ms,
            "metadata": self.metadata
        }

@dataclass
class UserProfile:
    """用户画像数据结构，存储编译后的专用语境"""
    user_id: str
    preference_vector: Dict[str, float] = field(default_factory=dict)
    cached_knowledge: Dict[str, str] = field(default_factory=dict)
    optimized_prompt_template: str = "Default System Prompt"
    last_updated: float = field(default_factory=time.time)

    def update_timestamp(self):
        """更新最后修改时间"""
        self.last_updated = time.time()

class CognitiveKernelOptimizer:
    """
    自优化认知内核的核心类。
    
    负责监控交互、分析用户习惯、编译专用Prompt以及管理知识内联。
    """

    def __init__(self, base_prompt: str, optimization_threshold: int = 5):
        """
        初始化认知内核。
        
        Args:
            base_prompt (str): 系统的基础通用Prompt。
            optimization_threshold (int): 触发重新编译所需的最小交互次数。
        """
        self.base_prompt = base_prompt
        self.optimization_threshold = optimization_threshold
        self._interaction_buffer: List[InteractionRecord] = []
        self._user_profiles: Dict[str, UserProfile] = {}
        logger.info("Cognitive Kernel Initialized with threshold %d", optimization_threshold)

    def _get_user_hash(self, user_identifier: str) -> str:
        """
        辅助函数：生成用户ID的哈希值以保护隐私或统一格式。
        
        Args:
            user_identifier (str): 原始用户标识符。
            
        Returns:
            str: SHA256哈希后的字符串。
        """
        return hashlib.sha256(user_identifier.encode('utf-8')).hexdigest()[:16]

    def record_interaction(
        self, 
        user_id: str, 
        user_input: str, 
        response: str, 
        i_type: InteractionType,
        latency: float
    ) -> None:
        """
        核心函数1：记录并处理单次交互。
        
        将交互存入缓冲区，如果达到阈值则触发后台编译。
        
        Args:
            user_id (str): 用户唯一标识。
            user_input (str): 用户输入内容。
            response (str): 系统生成的回复。
            i_type (InteractionType): 交互类型。
            latency (float): 响应延迟（毫秒）。
        """
        if not user_input or not response:
            logger.warning("Empty input or response detected, skipping recording.")
            return
            
        record = InteractionRecord(
            timestamp=time.time(),
            user_input=user_input,
            system_response=response,
            interaction_type=i_type,
            latency_ms=latency
        )
        
        self._interaction_buffer.append(record)
        u_hash = self._get_user_hash(user_id)
        
        # 确保用户档案存在
        if u_hash not in self._user_profiles:
            self._user_profiles[u_hash] = UserProfile(user_id=u_hash)
            
        logger.debug(f"Recorded interaction for user {u_hash}. Buffer size: {len(self._interaction_buffer)}")
        
        # 检查是否需要触发优化
        if len(self._interaction_buffer) >= self.optimization_threshold:
            self.trigger_background_compilation(u_hash)

    def trigger_background_compilation(self, user_hash: str) -> None:
        """
        核心函数2：触发后台认知编译。
        
        分析缓冲区数据，更新用户画像，生成专用Prompt。
        这是一个模拟的"编译"过程，将通用知识针对特定语境进行内联。
        
        Args:
            user_hash (str): 目标用户的哈希ID。
        """
        logger.info(f"Starting cognitive compilation for user {user_hash}...")
        profile = self._user_profiles.get(user_hash)
        if not profile:
            logger.error("User profile not found during compilation.")
            return

        # 分析交互模式（模拟NLP分析过程）
        # 这里简单统计关键词偏好作为示例
        keyword_freq: Dict[str, int] = {}
        total_latency = 0.0
        
        relevant_records = [r for r in self._interaction_buffer] # 在实际场景中会根据user_id过滤
        
        for record in relevant_records:
            words = record.user_input.lower().split()
            for word in words:
                if len(word) > 4: # 过滤短词
                    keyword_freq[word] = keyword_freq.get(word, 0) + 1
            total_latency += record.latency_ms
            
        # 更新偏好向量
        profile.preference_vector = {
            k: v / len(relevant_records) for k, v in keyword_freq.items()
        }
        
        # 知识内联：将高频概念固化到Prompt中，减少未来的推理需求
        top_keywords = sorted(keyword_freq, key=keyword_freq.get, reverse=True)[:3]
        inline_knowledge = f"User focus areas: {', '.join(top_keywords)}. "
        
        # 构建专用Prompt
        # 实际场景中这里会涉及复杂的Prompt Engineering
        new_prompt_suffix = f"\n\n[Context Injection]: Based on history, prioritize efficiency for topics related to {', '.join(top_keywords)}."
        profile.optimized_prompt_template = self.base_prompt + new_prompt_suffix
        
        profile.update_timestamp()
        
        # 清空已处理的缓冲区（或标记为已处理）
        self._interaction_buffer.clear()
        
        logger.info(f"Compilation complete. New prompt generated with context: {inline_knowledge}")

    def get_optimized_context(self, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        获取针对该用户的优化后上下文。
        
        Args:
            user_id (str): 用户ID。
            
        Returns:
            Tuple[str, Dict]: 包含优化后的Prompt和当前元数据。
        """
        u_hash = self._get_user_hash(user_id)
        profile = self._user_profiles.get(u_hash)
        
        if profile:
            return profile.optimized_prompt_template, profile.preference_vector
        else:
            return self.base_prompt, {}

# 使用示例
if __name__ == "__main__":
    # 基础系统提示词
    BASE_SYSTEM_PROMPT = "You are a helpful AGI assistant."
    
    # 初始化内核
    kernel = CognitiveKernelOptimizer(base_prompt=BASE_SYSTEM_PROMPT, optimization_threshold=3)
    
    # 模拟用户交互
    user = "user_12345"
    
    # 交互 1
    kernel.record_interaction(
        user_id=user, 
        user_input="How do I optimize Python code performance?", 
        response="You can use profilers like cProfile...", 
        i_type=InteractionType.QUERY,
        latency=150.5
    )
    
    # 交互 2
    kernel.record_interaction(
        user_id=user, 
        user_input="Explain memory management in Python.", 
        response="Python uses reference counting...", 
        i_type=InteractionType.QUERY,
        latency=145.0
    )
    
    # 交互 3 (触发阈值)
    kernel.record_interaction(
        user_id=user, 
        user_input="What about Python generators?", 
        response="Generators allow you to declare a function...", 
        i_type=InteractionType.QUERY,
        latency=130.2
    )
    
    # 获取优化后的结果
    optimized_prompt, preferences = kernel.get_optimized_context(user)
    
    print("-" * 30)
    print("Optimized Prompt:")
    print(optimized_prompt)
    print("-" * 30)
    print("User Preferences (Vector):")
    print(json.dumps(preferences, indent=2))