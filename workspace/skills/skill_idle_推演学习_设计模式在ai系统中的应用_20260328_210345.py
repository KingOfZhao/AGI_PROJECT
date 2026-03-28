#!/usr/bin/env python3
"""
自动推演生成的Skill: 推演学习: 设计模式在AI系统中的应用
生成时间: 2026-03-28T21:03:45.990050
"""

import abc
import time
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# ==========================================
# 1. 定义核心数据结构
# ==========================================

class ModelType(Enum):
    GPT_4 = "gpt-4-expensive"
    LOCAL_LLAMA = "llama-3-fast"
    CLAUDE_3 = "claude-3-sonnet"

@dataclass
class AIContext:
    """贯穿整个生命周期的上下文对象"""
    session_id: str
    user_input: str
    history: List[Dict] = field(default_factory=list)
    intent: Optional[str] = None
    contains_pii: bool = False
    selected_model: Optional[ModelType] = None
    tool_calls: List[Dict] = field(default_factory=list)
    final_response: Optional[str] = None
    metadata: Dict = field(default_factory=dict) # 用于存储额外状态

# ==========================================
# 2. 责任链模式 - 构建处理流水线
# ==========================================

class AbstractHandler(abc.ABC):
    """抽象处理者"""
    _next_handler: 'AbstractHandler' = None

    def set_next(self, handler: 'AbstractHandler') -> 'AbstractHandler':
        self._next_handler = handler
        return handler  # 允许链式调用

    def handle(self, ctx: AIContext) -> AIContext:
        # 执行当前逻辑
        result = self._process(ctx)
        if result is False:
            # 如果处理失败（如安全拦截），终止链路
            return ctx
        
        # 传递给下一个
        if self._next_handler:
            return self._next_handler.handle(ctx)
        return ctx

    @abc.abstractmethod
    def _process(self, ctx: AIContext) -> bool:
        pass

class SafetyFilterHandler(AbstractHandler):
    """安全过滤器：检测PII等敏感信息"""
    def _process(self, ctx: AIContext) -> bool:
        print(f"[SafetyCheck] Analyzing input for session {ctx.session_id}...")
        # 模拟 PII 检测逻辑
        if "password" in ctx.user_input or "credit card" in ctx.user_input:
            ctx.contains_pii = True
            ctx.final_response = "Error: Sensitive data detected. Request blocked."
            print("[SafetyCheck] Blocked due to PII.")
            return False # 终止传递
        print("[SafetyCheck] Input safe.")
        return True

class IntentClassifierHandler(AbstractHandler):
    """意图识别器：决定后续路由"""
    def _process(self, ctx: AIContext) -> bool:
        print("[Intent] Classifying intent...")
        if "code" in ctx.user_input or "debug" in ctx.user_input:
            ctx.intent = "coding"
            ctx.selected_model = ModelType.GPT_4 # 复杂任务选强模型
        elif "hello" in ctx.user_input:
            ctx.intent = "chitchat"
            ctx.selected_model = ModelType.LOCAL_LLAMA # 简单任务选快模型
        else:
            ctx.intent = "general"
            ctx.selected_model = ModelType.CLAUDE_3
        print(f"[Intent] Detected intent: {ctx.intent}, Selected Model: {ctx.selected_model}")
        return True

# ==========================================
# 3. 策略模式 - 动态模型执行
# ==========================================

class LLMStrategy(abc.ABC):
    @abc.abstractmethod
    def execute(self, prompt: str, history: List[Dict]) -> str:
        pass

class GPT4Strategy(LLMStrategy):
    def execute(self, prompt: str, history: List[Dict]) -> str:
        # 模拟 API 调用
        print("...Calling OpenAI GPT-4 API (High Cost)...")
        time.sleep(0.5)
        return f"Here is the complex code solution for: {prompt}"

class LocalLlamaStrategy(LLMStrategy):
    def execute(self, prompt: str, history: List[Dict]) -> str:
        # 模拟本地推理
        print("...Running Local Inference (Low Latency)...")
        time.sleep(0.1)
        return f"Hello! I am local bot. Response to: {prompt}"

class ModelRouter:
    """策略工厂，根据Context选择执行策略"""
    def __init__(self):
        self._strategies = {
            ModelType.GPT_4: GPT4Strategy(),
            ModelType.LOCAL_LLAMA: LocalLlamaStrategy(),
            ModelType.CLAUDE_3: GPT4Strategy() # 模拟复用
        }

    def run(self, ctx: AIContext) -> AIContext:
        if not ctx.selected_model:
            raise ValueError("Model not selected in context")
        
        strategy = self._strategies.get(ctx.selected_model)
        if not strategy:
            raise ValueError(f"No strategy for model {ctx.selected_model}")
        
        # 执行策略
        response = strategy.execute(ctx.user_input, ctx.history)
        ctx.final_response = response
        return ctx

# ==========================================
# 4. Skill 封装与编排
# ==========================================

class AICoreSkill:
    """
    可封装的AI核心技能
    封装了 Chain of Responsibility (流程控制) 和 Strategy (执行逻辑)
    """
    def __init__(self):
        # 构建责任链
        safety = SafetyFilterHandler()
        intent = IntentClassifierHandler()
        
        # 链条: 安全 -> 意图
        safety.set_next(intent)
        
        self.pipeline_head = safety
        self.model_router = ModelRouter()

    def invoke(self, session_id: str, user_input: str, history: List[Dict] = []) -> Dict:
        """
        统一调用入口
        """
        # 1. 初始化上下文
        ctx = AIContext(
            session_id=session_id,
            user_input=user_input,
            history=history
        )

        try:
            # 2. 执行前置处理链
            ctx = self.pipeline_head.handle(ctx)

            # 3. 如果未被拦截且无最终响应，执行模型调用
            if not ctx.final_response and ctx.selected_model:
                ctx = self.model_router.run(ctx)
            
            # 4. 后置处理 (如日志、计费)
            self._log_usage(ctx)

            return {
                "status": "success",
                "response": ctx.final_response,
                "model_used": ctx.selected_model.value if ctx.selected_model else None,
                "intent": ctx.intent
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "session_id": session_id
            }

    def _log_usage(self, ctx: AIContext):
        print(f"[Log] Session: {ctx.session_id} | Model: {ctx.selected_model} | Tokens: Simulated")

# ==========================================
# 5. 运行演示
# ==========================================

if __name__ == "__main__":
    # 实例化 Skill
    ai_skill = AICoreSkill()
    
    print("--- Test Case 1: Simple Chat (Local Model) ---")
    result_1 = ai_skill.invoke(
        session_id="user_123",
        user_input="hello there"
    )
    print(f"Output: {result_1}\n")

    print("--- Test Case 2: Complex Coding (Cloud Model) ---")
    result_2 = ai_skill.invoke(
        session_id="user_123",
        user_input="Please write a python script for web scraping"
    )
    print(f"Output: {result_2}\n")

    print("--- Test Case 3: Security Block (Chain Termination) ---")
    result_3 = ai_skill.invoke(
        session_id="user_456",
        user_input="Here is my password: 123456"
    )
    print(f"Output: {result_3}\n")


if __name__ == "__main__":
    print("Skill: 推演学习: 设计模式在AI系统中的应用")
