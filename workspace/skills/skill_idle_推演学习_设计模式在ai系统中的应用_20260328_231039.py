#!/usr/bin/env python3
"""
自动推演生成的Skill: 推演学习: 设计模式在AI系统中的应用
生成时间: 2026-03-28T23:10:39.602937
"""

import asyncio
import time
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. 基础数据结构与配置 (工厂模式的原料)
# ==========================================

class ModelTier(Enum):
    """模型层级定义"""
    CHEAP = "cheap"       # 快速、低成本 (e.g., GPT-3.5, Local)
    SMART = "smart"       # 高智商、高成本
    VISION = "vision"     # 多模态

@dataclass
class LLMConfig:
    """LLM调用配置"""
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 500
    system_prompt: str = "You are a helpful assistant."
    retry_count: int = 2

@dataclass
class LLMResponse:
    """LLM响应标准结构"""
    content: str
    model_used: str
    latency_ms: float
    success: bool
    error_msg: Optional[str] = None

# ==========================================
# 2. 策略模式 - 核心模型调用逻辑
# ==========================================

class LLMStrategy(ABC):
    """抽象策略：定义LLM调用接口"""
    
    @abstractmethod
    async def invoke(self, prompt: str, config: LLMConfig) -> LLMResponse:
        pass

class CheapModelStrategy(LLMStrategy):
    """具体策略：模拟低成本模型"""
    
    async def invoke(self, prompt: str, config: LLMConfig) -> LLMResponse:
        start_time = time.time()
        
        # 模拟网络延迟
        await asyncio.sleep(0.2) 
        
        # 模拟偶尔的失败 (20%概率)
        if random.random() < 0.2:
            raise ConnectionError("Cheap Model API Timeout")
            
        response_text = f"[Cheap Model Response]: Processed '{prompt[:20]}...'"
        latency = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=response_text,
            model_used=config.model_name,
            latency_ms=latency,
            success=True
        )

class SmartModelStrategy(LLMStrategy):
    """具体策略：模拟高智商模型"""
    
    async def invoke(self, prompt: str, config: LLMConfig) -> LLMResponse:
        start_time = time.time()
        
        # 模拟较长的思考延迟
        await asyncio.sleep(1.5)
        
        # 模拟高成本模型极其稳定，但可能超时
        if random.random() < 0.05:
            raise ConnectionError("Smart Model Rate Limit")

        response_text = f"[Smart Model Analysis]: Deep insight regarding '{prompt[:20]}...'"
        latency = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=response_text,
            model_used=config.model_name,
            latency_ms=latency,
            success=True
        )

# ==========================================
# 3. 工厂模式 - 动态配置构建
# ==========================================

class PromptFactory:
    """工厂：根据场景构建不同的Prompt配置"""
    
    @staticmethod
    def create_config(tier: ModelTier, context: Optional[Dict] = None) -> LLMConfig:
        context = context or {}
        
        if tier == ModelTier.CHEAP:
            return LLMConfig(
                model_name="gpt-3.5-turbo-local",
                temperature=0.5,
                max_tokens=200,
                system_prompt="You are a fast and concise assistant."
            )
        elif tier == ModelTier.SMART:
            return LLMConfig(
                model_name="gpt-4-turbo",
                temperature=0.8,
                max_tokens=2000,
                system_prompt="You are an expert reasoning engine. Think step by step."
            )
        else:
            return LLMConfig(model_name="default-model")

# ==========================================
# 4. Skill 封装 - 路由与容错核心
# ==========================================

class AIRouterSkill:
    """
    AI路由技能：
    1. 自动路由
    2. 熔断降级
    3. 自动重试
    """
    
    def __init__(self):
        self._strategies: Dict[ModelTier, LLMStrategy] = {
            ModelTier.CHEAP: CheapModelStrategy(),
            ModelTier.SMART: SmartModelStrategy()
        }
        self._failure_counts: Dict[str, int] = {}
        self._circuit_breaker_threshold = 3
        
    def _analyze_complexity(self, prompt: str) -> ModelTier:
        """简单的启发式路由逻辑"""
        complex_keywords = ["分析", "推演", "代码", "深度", "为什么"]
        if len(prompt) > 100 or any(kw in prompt for kw in complex_keywords):
            return ModelTier.SMART
        return ModelTier.CHEAP

    async def run(self, user_input: str, force_tier: Optional[ModelTier] = None) -> LLMResponse:
        """
        执行入口
        :param user_input: 用户输入
        :param force_tier: 强制指定模型层级，若为None则自动路由
        """
        target_tier = force_tier if force_tier else self._analyze_complexity(user_input)
        config = PromptFactory.create_config(target_tier)
        strategy = self._strategies.get(target_tier)
        
        if not strategy:
            return LLMResponse(content="", model_used="None", latency_ms=0, success=False, error_msg="Invalid Strategy")

        # 检查熔断状态
        if self._failure_counts.get(config.model_name, 0) >= self._circuit_breaker_threshold:
            logger.warning(f"Circuit Breaker OPEN for {config.model_name}. Fallback to CHEAP.")
            target_tier = ModelTier.CHEAP
            config = PromptFactory.create_config(target_tier)
            strategy = self._strategies[target_tier]

        # 执行重试逻辑
        last_error = None
        for attempt in range(config.retry_count):
            try:
                logger.info(f"Attempt {attempt+1}: Calling {config.model_name} (Tier: {target_tier.value})")
                response = await strategy.invoke(user_input, config)
                
                # 成功则重置失败计数
                self._failure_counts[config.model_name] = 0
                return response
                
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                last_error = e
                self._failure_counts[config.model_name] = self._failure_counts.get(config.model_name, 0) + 1
                
                # 如果是主模型失败，且不是最后一次尝试，准备降级
                if attempt < config.retry_count - 1:
                    await asyncio.sleep(1) # Wait before retry
                else:
                    # 最终失败，尝试降级到便宜模型
                    if target_tier != ModelTier.CHEAP:
                        logger.warning("Primary model failed. Fallback to CHEAP model.")
                        fallback_config = PromptFactory.create_config(ModelTier.CHEAP)
                        fallback_strategy = self._strategies[ModelTier.CHEAP]
                        try:
                            return await fallback_strategy.invoke(user_input, fallback_config)
                        except Exception as fallback_e:
                            return LLMResponse(
                                content="", model_used="fallback", latency_ms=0, 
                                success=False, error_msg=str(fallback_e)
                            )

        return LLMResponse(
            content="", model_used=config.model_name, latency_ms=0,
            success=False, error_msg=str(last_error)
        )

# ==========================================
# 5. 运行时测试
# ==========================================

async def main():
    skill = AIRouterSkill()
    
    print("--- Test Case 1: Simple Query (Auto Routing) ---")
    res1 = await skill.run("你好吗？")
    print(f"Response: {res1.content}\nSuccess: {res1.success}\nModel: {res1.model_used}\n")
    
    print("--- Test Case 2: Complex Query (Auto Routing) ---")
    res2 = await skill.run("请详细分析一下当前AI代码生成领域的技术瓶颈与未来推演。")
    print(f"Response: {res2.content}\nSuccess: {res2.success}\nModel: {res2.model_used}\n")

    print("--- Test Case 3: Forcing Cheap Model ---")
    res3 = await skill.run("这是一个很长的复杂问题，但我强制使用便宜模型。", force_tier=ModelTier.CHEAP)
    print(f"Response: {res3.content}\nSuccess: {res3.success}\nModel: {res3.model_used}\n")

if __name__ == "__main__":
    asyncio.run(main())


if __name__ == "__main__":
    print("Skill: 推演学习: 设计模式在AI系统中的应用")
