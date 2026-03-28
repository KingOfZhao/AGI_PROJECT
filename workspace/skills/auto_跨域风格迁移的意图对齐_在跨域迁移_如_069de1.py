"""
跨域风格迁移的意图对齐模块 (Cross-Domain Style Transfer Intent Alignment)

该模块实现了在跨系统迁移（例如从Web前端到命令行工具）时，
对用户意图进行结构化对齐的核心算法。它能自动剥离领域特定的
表现形式（如HTML按钮、DOM结构），提取核心认知逻辑（如验证流程、
状态反馈），并将其映射到目标领域的原生结构中。
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class IntentContext:
    """
    意图上下文数据类。
    
    Attributes:
        raw_intent (str): 原始意图描述。
        source_domain (str): 源领域 (例如 'web', 'mobile')。
        target_domain (str): 目标领域 (例如 'cli', 'api')。
        specific_bindings (Dict[str, Any]): 领域特定的绑定数据。
    """
    raw_intent: str
    source_domain: str
    target_domain: str
    specific_bindings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlignedIntent:
    """
    对齐后的意图数据类。
    
    Attributes:
        core_logic (str): 提取出的核心认知逻辑。
        target_actions (List[str]): 映射到目标领域的动作序列。
        payload (Dict[str, Any]): 处理后的数据负载。
        confidence (float): 对齐置信度 (0.0 to 1.0).
    """
    core_logic: str
    target_actions: List[str]
    payload: Dict[str, Any]
    confidence: float = 0.0

# --- 抽象基类与领域适配器 ---

class DomainAdapter(ABC):
    """领域适配器抽象基类"""
    
    @abstractmethod
    def extract_core_logic(self, context: IntentContext) -> str:
        pass

    @abstractmethod
    def map_to_target(self, core_logic: str, context: IntentContext) -> List[str]:
        pass

class WebToCLIAdapter(DomainAdapter):
    """Web到CLI的特定适配器"""
    
    def extract_core_logic(self, context: IntentContext) -> str:
        # 剥离 'button', 'click', 'popup' 等 UI 元素
        # 保留 'verify', 'submit', 'check' 等逻辑
        ui_noise = ['button', 'div', 'span', 'popup', 'modal', 'hover', 'click']
        cleaned_intent = context.raw_intent
        for noise in ui_noise:
            cleaned_intent = re.sub(rf'\b{noise}\b', '', cleaned_intent, flags=re.IGNORECASE)
        
        core = cleaned_intent.strip().replace('  ', ' ')
        logger.debug(f"Extracted core logic: '{core}' from '{context.raw_intent}'")
        return core

    def map_to_target(self, core_logic: str, context: IntentContext) -> List[str]:
        # 将逻辑映射为 CLI 指令
        # 这是一个简化的规则引擎示例
        actions = []
        if 'login' in core_logic.lower():
            actions.append('authenticate --user $USER --token $TOKEN')
        if 'verify' in core_logic.lower():
            actions.append('check_status --verbose')
        if 'submit' in core_logic.lower():
            actions.append('commit_changes --force')
        
        if not actions:
            actions.append(f'execute_generic --cmd "{core_logic}"')
            
        return actions

# --- 核心功能类 ---

class IntentAlignmentEngine:
    """
    意图对齐引擎。
    负责协调不同领域间的意图迁移，包含验证、提取和映射逻辑。
    """
    
    DOMAIN_MAPPING = {
        ('web', 'cli'): WebToCLIAdapter
    }

    def __init__(self):
        self._adapters: Dict[tuple, DomainAdapter] = {}
        self._initialize_adapters()

    def _initialize_adapters(self):
        """初始化内置适配器"""
        for key, adapter_cls in self.DOMAIN_MAPPING.items():
            self._adapters[key] = adapter_cls()
            logger.info(f"Loaded adapter for {key}")

    def _validate_context(self, context: IntentContext) -> bool:
        """
        验证输入上下文的有效性。
        
        Args:
            context (IntentContext): 输入的意图上下文。
            
        Returns:
            bool: 如果数据有效返回 True。
            
        Raises:
            ValueError: 如果数据缺失或格式错误。
        """
        if not context.raw_intent:
            raise ValueError("Raw intent cannot be empty.")
        if not context.source_domain or not context.target_domain:
            raise ValueError("Source and target domains must be specified.")
        
        # 边界检查：检查是否支持该领域转换
        key = (context.source_domain.lower(), context.target_domain.lower())
        if key not in self._adapters:
            raise ValueError(f"Unsupported domain transfer: {key}")
            
        return True

    def align(self, context: IntentContext) -> AlignedIntent:
        """
        执行意图对齐的主函数。
        
        Args:
            context (IntentContext): 包含原始意图和领域信息的上下文对象。
            
        Returns:
            AlignedIntent: 包含核心逻辑和目标动作的对齐结果。
        """
        try:
            logger.info(f"Starting alignment for intent: {context.raw_intent[:50]}...")
            self._validate_context(context)
            
            key = (context.source_domain.lower(), context.target_domain.lower())
            adapter = self._adapters[key]
            
            # 1. 剥离领域特定形式，提取核心逻辑
            core_logic = adapter.extract_core_logic(context)
            
            # 2. 映射到目标领域结构
            target_actions = adapter.map_to_target(core_logic, context)
            
            # 3. 构造结果
            result = AlignedIntent(
                core_logic=core_logic,
                target_actions=target_actions,
                payload=self._transform_payload(context.specific_bindings),
                confidence=0.85  # 模拟置信度计算
            )
            
            logger.info(f"Alignment successful. Actions generated: {len(target_actions)}")
            return result

        except ValueError as ve:
            logger.error(f"Validation Error: {ve}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during alignment: {e}", exc_info=True)
            raise RuntimeError("Intent alignment failed due to internal error.") from e

    def _transform_payload(self, bindings: Dict[str, Any]) -> Dict[str, Any]:
        """
        辅助函数：转换数据负载格式。
        将 Web 表单数据转换为 CLI 参数格式。
        """
        transformed = {}
        for k, v in bindings.items():
            # 简单的命名转换示例: webInput -> web_input
            new_key = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            transformed[new_key] = v
        return transformed

# --- 使用示例与执行入口 ---

def run_demonstration():
    """
    演示如何使用 IntentAlignmentEngine 进行跨域迁移。
    """
    print("--- AGI Skill: Cross-Domain Intent Alignment Demonstration ---")
    
    # 场景：将Web登录流程迁移到CLI工具
    web_intent = "User clicks the Submit button to trigger the popup for login verification."
    bindings = {
        "userName": "admin",
        "userToken": "xyz123",
        "retryCount": 3
    }
    
    context = IntentContext(
        raw_intent=web_intent,
        source_domain="web",
        target_domain="cli",
        specific_bindings=bindings
    )
    
    engine = IntentAlignmentEngine()
    
    try:
        aligned = engine.align(context)
        
        print(f"\n[Original Intent (Web)]: {context.raw_intent}")
        print(f"[Extracted Core Logic]: {aligned.core_logic}")
        print(f"[Target Actions (CLI)]:")
        for action in aligned.target_actions:
            print(f"  > {action}")
        print(f"[Transformed Payload]: {aligned.payload}")
        print(f"[Confidence Score]: {aligned.confidence}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_demonstration()