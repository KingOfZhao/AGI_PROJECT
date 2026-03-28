"""
模块名称: auto_人机共生层_设计_人类意图的置信度加权_d03358
描述: 本模块实现了人机共生层中的核心组件——人类意图的置信度加权与收敛接口。
     旨在将人类模糊的自然语言输入转化为系统可执行的确定性参数。
     通过评估输入各部分的置信度，针对低置信度区域启动交互式追问，
     从而实现从不确定性到确定性的收敛。
作者: AGI System
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class IntentDomain(Enum):
    """意图领域的枚举，用于上下文推断"""
    GENERAL = "general"
    DATA_QUERY = "data_query"
    SYSTEM_CONFIG = "system_config"
    CREATIVE_WRITING = "creative_writing"

@dataclass
class IntentComponent:
    """
    意图组件数据结构。
    表示解析后的单个意图片段。
    """
    raw_text: str
    normalized_value: Any
    confidence: float  # 0.0 到 1.0
    entity_type: str   # e.g., 'date', 'target', 'action'
    is_resolved: bool = False

    def __post_init__(self):
        # 边界检查：确保置信度在合法范围内
        if not (0.0 <= self.confidence <= 1.0):
            logger.warning(f"Confidence {self.confidence} out of bounds for '{self.raw_text}'. Clamping.")
            self.confidence = max(0.0, min(1.0, self.confidence))

@dataclass
class UserIntent:
    """
    用户意图聚合对象。
    包含原始输入和解析后的组件列表。
    """
    original_input: str
    components: List[IntentComponent] = field(default_factory=list)
    domain: IntentDomain = IntentDomain.GENERAL
    resolved: bool = False

class IntentConfidenceWeighting:
    """
    人类意图的置信度加权接口。
    
    负责解析用户输入，识别低置信度片段，并生成追问策略。
    """
    
    def __init__(self, confidence_threshold: float = 0.75):
        """
        初始化接口。
        
        Args:
            confidence_threshold (float): 触发追问的置信度阈值。低于此值被视为“不确定”。
        """
        self.confidence_threshold = confidence_threshold
        logger.info(f"IntentConfidenceWeighting initialized with threshold: {confidence_threshold}")

    def _preprocess_text(self, text: str) -> str:
        """
        辅助函数：文本预处理。
        清理输入文本，去除多余空格和标点。
        
        Args:
            text (str): 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # 简单的清理逻辑
        cleaned = text.strip().lower()
        cleaned = re.sub(r'[?؟!。！，,]+$', '', cleaned)
        logger.debug(f"Preprocessed '{text}' to '{cleaned}'")
        return cleaned

    def parse_intent(self, user_input: str) -> UserIntent:
        """
        核心函数 1: 解析与加权。
        将自然语言输入分解为组件，并分配初始置信度权重。
        
        Args:
            user_input (str): 用户的原始输入字符串。
            
        Returns:
            UserIntent: 包含加权组件的意图对象。
            
        Example Input:
            "帮我查一下大概昨天下午的销售数据"
        """
        if not user_input:
            raise ValueError("Input cannot be empty")

        cleaned_input = self._preprocess_text(user_input)
        intent = UserIntent(original_input=user_input)
        
        # 模拟NLP解析过程 (在实际AGI中这里会连接LLM或NLU引擎)
        # 假设逻辑：识别关键实体
        # "查一下" -> Action (High confidence)
        # "销售数据" -> Target (High confidence)
        # "大概" -> Modifier indicating uncertainty (Lower confidence for the modified object)
        # "昨天下午" -> Time (Context dependent, might be ambiguous without timezone)

        components = []
        
        # 模拟解析逻辑
        if "查" in cleaned_input or "寻找" in cleaned_input:
            components.append(IntentComponent("查", "QUERY", 0.98, "action"))
        
        if "销售" in cleaned_input:
            components.append(IntentComponent("销售", "SALES_DATA", 0.95, "target"))
            
        # 处理时间模糊性
        if "昨天" in cleaned_input:
            # "昨天"是相对时间，置信度中等
            components.append(IntentComponent("昨天", "YESTERDAY", 0.6, "time"))
            
        # 处理程度副词降低置信度
        if "大概" in cleaned_input or "可能" in cleaned_input:
            # 如果包含模糊词，主动降低关联实体的置信度
            for comp in components:
                if comp.entity_type in ["time", "quantity"]:
                    comp.confidence *= 0.5 # 惩罚系数
                    logger.info(f"Detected uncertainty modifier '大概', lowering confidence for {comp.entity_type}")

        intent.components = components
        logger.info(f"Parsed intent with {len(components)} components.")
        return intent

    def resolve_uncertainty(self, intent: UserIntent) -> Tuple[UserIntent, Optional[str]]:
        """
        核心函数 2: 交互式追问与收敛。
        检查意图中的低置信度部分，生成追问文本。
        如果用户提供了反馈（此处模拟为立即修正），则更新意图。
        
        Args:
            intent (UserIntent): 待解决的意图对象。
            
        Returns:
            Tuple[UserIntent, Optional[str]]: 
                - 更新后的意图对象。
                - 追问字符串（如果需要），如果无需追问则返回None。
        """
        unresolved_components = [
            c for c in intent.components 
            if c.confidence < self.confidence_threshold and not c.is_resolved
        ]

        if not unresolved_components:
            intent.resolved = True
            logger.info("Intent fully resolved with high confidence.")
            return intent, None

        # 生成追问策略：针对最低置信度的组件提问
        target_component = min(unresolved_components, key=lambda x: x.confidence)
        
        question = self._generate_clarification_question(target_component)
        logger.info(f"Generated clarification question for: {target_component.raw_text}")
        
        # 注意：在实际交互循环中，这里会等待用户输入。
        # 为了模块演示，我们返回问题，由上层控制器处理用户输入并重新调用 parse 或 update。
        return intent, question

    def _generate_clarification_question(self, component: IntentComponent) -> str:
        """
        辅助函数：生成追问语句。
        根据组件类型生成自然语言追问。
        
        Args:
            component (IntentComponent): 需要澄清的组件。
            
        Returns:
            str: 生成的追问字符串。
        """
        entity = component.raw_text
        if component.entity_type == "time":
            return f"系统检测到您提到了'{entity}'，请问具体是指哪个时间段？例如：YYYY-MM-DD HH:MM"
        elif component.entity_type == "target":
            return f"关于'{entity}'，您是指具体的详细列表还是汇总数据？"
        else:
            return f"您提到的'{entity}'描述比较模糊，能否提供更具体的信息？"

    def update_intent_with_feedback(self, intent: UserIntent, component_text: str, new_value: str) -> None:
        """
        使用用户反馈更新意图组件。
        
        Args:
            intent (UserIntent): 意图对象。
            component_text (str): 原始组件文本。
            new_value (str): 用户提供的确切值。
        """
        for comp in intent.components:
            if comp.raw_text == component_text:
                comp.normalized_value = new_value
                comp.confidence = 1.0 # 确认为 1.0
                comp.is_resolved = True
                logger.info(f"Updated component '{component_text}' to '{new_value}' with full confidence.")
                return
        logger.warning(f"Component '{component_text}' not found for update.")

# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    # 1. 初始化接口
    weighting_system = IntentConfidenceWeighting(confidence_threshold=0.75)
    
    # 模拟用户输入 (包含确定的指令 "查销售" 和不确定的描述 "大概昨天")
    user_input = "帮我查一下大概昨天的销售数据"
    
    print(f"--- 处理用户输入: '{user_input}' ---")
    
    try:
        # 2. 解析意图
        current_intent = weighting_system.parse_intent(user_input)
        
        # 3. 检查不确定性并获取追问
        current_intent, question = weighting_system.resolve_uncertainty(current_intent)
        
        if question:
            print(f"系统追问: {question}")
            
            # 模拟用户回答了追问
            user_answer = "2023-10-26 14:00"
            print(f"用户回答: {user_answer}")
            
            # 4. 收敛：更新意图
            # 假设我们知道是针对 "昨天" 这个组件的追问
            weighting_system.update_intent_with_feedback(current_intent, "昨天", user_answer)
            
            # 5. 再次检查
            current_intent, final_question = weighting_system.resolve_uncertainty(current_intent)
            
            if not final_question:
                print("系统: 意图已完全收敛。正在执行任务...")
                print("最终参数:")
                for comp in current_intent.components:
                    print(f"  - {comp.entity_type}: {comp.normalized_value} (Conf: {comp.confidence})")
            else:
                print("系统: 仍有不确定因素。")
                
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)