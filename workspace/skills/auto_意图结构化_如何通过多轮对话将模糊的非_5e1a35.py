"""
模块名称: auto_意图结构化_如何通过多轮对话将模糊的非_5e1a35
描述: 实现基于多轮对话的意图结构化解析器。
      该模块演示了AGI系统如何通过主动提问，将用户的模糊自然语言意图
      转化为符合严格Schema定义的JSON中间表示(IR)。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentResolutionStatus(Enum):
    """意图解析状态枚举"""
    COMPLETE = "COMPLETE"
    NEED_INFO = "NEED_INFO"
    INVALID = "INVALID"

@dataclass
class IntentSchema:
    """
    意图Schema定义，描述目标IR的结构。
    
    Attributes:
        name (str): 意图名称
        required_slots (List[str]): 必须填写的槽位列表
        slot_types (Dict[str, str]): 槽位名称到数据类型的映射
        descriptions (Dict[str, str]): 槽位描述，用于生成提示语
    """
    name: str
    required_slots: List[str]
    slot_types: Dict[str, str]
    descriptions: Dict[str, str]

    def validate_structure(self) -> bool:
        """验证Schema内部一致性"""
        if not all(slot in self.slot_types for slot in self.required_slots):
            return False
        return True

@dataclass
class ConversationContext:
    """
    对话上下文，维护当前对话的状态。
    
    Attributes:
        user_id (str): 用户标识
        current_intent (Optional[IntentSchema]): 当前正在处理的意图Schema
        filled_slots (Dict[str, Any]): 已填充的槽位值
        history (List[Dict[str, str]]): 对话历史记录
    """
    user_id: str
    current_intent: Optional[IntentSchema] = None
    filled_slots: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)

class IntentStructuringEngine:
    """
    意图结构化引擎。
    
    负责管理多轮对话状态，生成澄清性问题，验证输入，
    并最终生成结构化的中间表示(IR)。
    """

    def __init__(self, schemas: List[IntentSchema]):
        """
        初始化引擎。
        
        Args:
            schemas (List[IntentSchema]): 系统支持的意图Schema列表
        """
        self.schemas = {s.name: s for s in schemas}
        logger.info(f"Engine initialized with {len(self.schemas)} schemas.")

    def _extract_simple_entity(self, text: str, entity_type: str) -> Optional[Any]:
        """
        辅助函数：简化的实体提取逻辑。
        
        在实际AGI场景中，这里会调用LLM或NER模型。
        这里仅作演示用途，使用正则和简单规则。
        
        Args:
            text (str): 输入文本
            entity_type (str): 期望的实体类型 (如 'date', 'city', 'number')
            
        Returns:
            Optional[Any]: 提取到的实体值或None
        """
        logger.debug(f"Attempting to extract {entity_type} from '{text}'")
        text = text.strip()
        
        if entity_type == "date":
            # 极简日期匹配
            match = re.search(r'\d{4}-\d{2}-\d{2}', text)
            if match:
                return match.group(0)
        elif entity_type == "city":
            # 假设城市是一个非纯数字的字符串
            if text and not text.isdigit():
                return text
        elif entity_type == "number":
            match = re.search(r'\d+', text)
            if match:
                return int(match.group(0))
        
        return None

    def _generate_clarification_question(self, schema: IntentSchema, missing_slot: str) -> str:
        """
        生成澄清性问题。
        
        Args:
            schema (IntentSchema): 当前意图
            missing_slot (str): 缺失的槽位名
            
        Returns:
            str: 生成的问题字符串
        """
        desc = schema.descriptions.get(missing_slot, missing_slot)
        return f"为了完成操作，请告诉我：{desc}？"

    def process_turn(self, context: ConversationContext, user_input: str) -> Tuple[ConversationContext, str, IntentResolutionStatus]:
        """
        核心函数：处理单轮对话。
        
        流程:
        1. 意图识别 (如果尚未确定)
        2. 槽位填充 (提取实体)
        3. 状态检查 (是否缺少必填项)
        4. 生成回复 (提问或结束)
        
        Args:
            context (ConversationContext): 当前对话上下文
            user_input (str): 用户输入
            
        Returns:
            Tuple[ConversationContext, str, IntentResolutionStatus]: 
            (更新后的上下文, 系统回复, 当前状态)
        """
        try:
            context.history.append({"role": "user", "content": user_input})
            
            # 阶段1: 意图识别
            if context.current_intent is None:
                # 演示用硬逻辑：根据关键词识别意图
                if "订票" in user_input or "飞" in user_input:
                    context.current_intent = self.schemas.get("BookFlight")
                elif "天气" in user_input:
                    context.current_intent = self.schemas.get("QueryWeather")
                else:
                    return context, "抱歉，我没理解您的意思。您是想订票还是查天气？", IntentResolutionStatus.INVALID
            
            if context.current_intent is None:
                return context, "系统内部错误：无法确定意图。", IntentResolutionStatus.INVALID

            schema = context.current_intent
            
            # 阶段2: 槽位填充
            # 尝试从当前输入中提取所有缺失的槽位
            for slot in schema.required_slots:
                if slot not in context.filled_slots:
                    entity_type = schema.slot_types.get(slot)
                    value = self._extract_simple_entity(user_input, entity_type)
                    if value:
                        context.filled_slots[slot] = value
                        logger.info(f"Filled slot '{slot}' with value '{value}'")

            # 阶段3: 检查完整性与生成回复
            for slot in schema.required_slots:
                if slot not in context.filled_slots:
                    question = self._generate_clarification_question(schema, slot)
                    context.history.append({"role": "system", "content": question})
                    return context, question, IntentResolutionStatus.NEED_INFO

            # 所有槽位已填充
            return context, "意图解析完成。", IntentResolutionStatus.COMPLETE

        except Exception as e:
            logger.error(f"Error processing turn: {str(e)}", exc_info=True)
            return context, "处理过程中发生错误。", IntentResolutionStatus.INVALID

    def generate_ir(self, context: ConversationContext) -> Optional[Dict[str, Any]]:
        """
        核心函数：生成中间表示(IR)。
        
        验证最终数据并构建JSON对象树。
        
        Args:
            context (ConversationContext): 已完成的对话上下文
            
        Returns:
            Optional[Dict[str, Any]]: 结构化的JSON对象 (字典形式)
        """
        if context.current_intent is None or context.filled_slots is None:
            logger.warning("Attempted to generate IR with incomplete context")
            return None

        ir = {
            "intent": context.current_intent.name,
            "slots": context.filled_slots,
            "metadata": {
                "user_id": context.user_id,
                "schema_version": "1.0"
            }
        }
        
        logger.info(f"Generated IR: {json.dumps(ir, ensure_ascii=False)}")
        return ir

# 使用示例
if __name__ == "__main__":
    # 定义Schema
    flight_schema = IntentSchema(
        name="BookFlight",
        required_slots=["departure_city", "arrival_city", "date"],
        slot_types={
            "departure_city": "city",
            "arrival_city": "city",
            "date": "date"
        },
        descriptions={
            "departure_city": "出发城市",
            "arrival_city": "目的城市",
            "date": "出发日期 (YYYY-MM-DD)"
        }
    )

    # 初始化引擎
    engine = IntentStructuringEngine(schemas=[flight_schema])
    
    # 模拟用户会话
    ctx = ConversationContext(user_id="user_123")
    
    print("=== Turn 1 ===")
    user_msg_1 = "我要订票去北京"
    ctx, reply_1, status_1 = engine.process_turn(ctx, user_msg_1)
    print(f"User: {user_msg_1}")
    print(f"System: {reply_1} [Status: {status_1.value}]")
    
    # 只有当状态为NEED_INFO时才继续
    if status_1 == IntentResolutionStatus.NEED_INFO:
        print("\n=== Turn 2 ===")
        # 假设用户回答了上一个问题 (目的城市已提取为北京，缺出发城市)
        user_msg_2 = "上海"
        ctx, reply_2, status_2 = engine.process_turn(ctx, user_msg_2)
        print(f"User: {user_msg_2}")
        print(f"System: {reply_2} [Status: {status_2.value}]")

        if status_2 == IntentResolutionStatus.NEED_INFO:
            print("\n=== Turn 3 ===")
            # 补全日期
            user_msg_3 = "2023-10-01"
            ctx, reply_3, status_3 = engine.process_turn(ctx, user_msg_3)
            print(f"User: {user_msg_3}")
            print(f"System: {reply_3} [Status: {status_3.value}]")

            if status_3 == IntentResolutionStatus.COMPLETE:
                ir_result = engine.generate_ir(ctx)
                print("\nFinal Structured IR:")
                print(json.dumps(ir_result, indent=2, ensure_ascii=False))