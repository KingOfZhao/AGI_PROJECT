"""
直觉-逻辑双向编译器

本模块提供了一个将人类模糊的直觉意图转化为结构化、可执行逻辑的AGI工具。
通过模拟多轮对话的状态机循环，引导用户将隐性技能（如"我想摆个摊"）解析为
严格的"行动JSON"（包含选址、选品、定价等节点的结构化数据）。

核心功能：
1. 模糊指令解析：将自然语言转化为中间状态结构
2. 逻辑节点补全：通过状态机引导用户填补缺失的逻辑节点
3. 双向编译：支持直觉到逻辑的转化和逻辑到直觉的反馈

作者: AGI System
版本: 1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("IntuitionLogicCompiler")


class NodeType(Enum):
    """定义逻辑节点的类型枚举"""

    LOCATION = auto()  # 选址节点
    PRODUCT = auto()  # 选品节点
    PRICING = auto()  # 定价节点
    TIMING = auto()  # 时间节点
    RESOURCE = auto()  # 资源节点
    EXECUTION = auto()  # 执行节点
    FEEDBACK = auto()  # 反馈节点


class ConversationState(Enum):
    """定义对话状态枚举"""

    INITIAL = auto()  # 初始状态
    CLARIFYING = auto()  # 澄清中
    CONFIRMING = auto()  # 确认中
    COMPLETED = auto()  # 已完成
    ERROR = auto()  # 错误状态


@dataclass
class LogicNode:
    """逻辑节点数据结构"""

    node_type: NodeType
    description: str
    value: Optional[Union[str, int, float, Dict]] = None
    is_confirmed: bool = False
    dependencies: List["LogicNode"] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """将节点转换为字典格式"""
        return {
            "node_type": self.node_type.name,
            "description": self.description,
            "value": self.value,
            "is_confirmed": self.is_confirmed,
            "dependencies": [dep.node_type.name for dep in self.dependencies],
        }


@dataclass
class UserIntent:
    """用户意图数据结构"""

    raw_input: str
    parsed_intent: Optional[Dict] = None
    required_nodes: List[NodeType] = field(default_factory=list)
    current_state: ConversationState = ConversationState.INITIAL
    conversation_history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """将意图转换为字典格式"""
        return {
            "raw_input": self.raw_input,
            "parsed_intent": self.parsed_intent,
            "required_nodes": [node.name for node in self.required_nodes],
            "current_state": self.current_state.name,
            "conversation_history": self.conversation_history,
        }


class IntuitionLogicCompiler:
    """
    直觉-逻辑双向编译器

    将模糊的直觉意图转化为结构化逻辑，通过多轮对话引导用户完善逻辑节点。

    示例用法：
    >>> compiler = IntuitionLogicCompiler()
    >>> user_input = "我想摆个摊"
    >>> result = compiler.process_user_input(user_input)
    >>> while not result["is_complete"]:
    ...     user_response = input(result["next_prompt"])
    ...     result = compiler.continue_conversation(user_response)
    """

    def __init__(self):
        """初始化编译器"""
        self._initialize_node_templates()
        self.active_intents: Dict[str, UserIntent] = {}
        self.session_counter = 0
        logger.info("IntuitionLogicCompiler initialized successfully")

    def _initialize_node_templates(self) -> None:
        """初始化节点模板库"""
        self.node_templates = {
            NodeType.LOCATION: {
                "question": "请问您计划在哪里{action}？",
                "examples": ["商业区", "居民区", "学校附近", "线上平台"],
            },
            NodeType.PRODUCT: {
                "question": "您打算提供什么样的产品或服务？",
                "examples": ["食品", "手工艺品", "咨询服务", "数字产品"],
            },
            NodeType.PRICING: {
                "question": "您预期的价格范围是多少？",
                "examples": ["低价走量", "中端市场", "高端定制"],
            },
            NodeType.TIMING: {
                "question": "您计划什么时间开始？运营时间如何安排？",
                "examples": ["立即开始", "下个月", "周末", "全天"],
            },
            NodeType.RESOURCE: {
                "question": "您目前有哪些资源？还需要哪些资源？",
                "examples": ["资金", "人力", "技能", "设备"],
            },
        }

    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        self.session_counter += 1
        return f"session_{self.session_counter:04d}"

    def _extract_action_type(self, text: str) -> Tuple[str, float]:
        """
        从文本中提取动作类型和置信度

        Args:
            text: 用户输入的文本

        Returns:
            Tuple[str, float]: (动作类型, 置信度)
        """
        text = text.lower().strip()

        # 使用简单的关键词匹配（实际应用中可使用NLP模型）
        action_patterns = {
            r"摆摊|摊位|卖东西": "retail_operation",
            r"写报告|做汇报|整理数据": "report_creation",
            r"开发|编程|写代码": "software_development",
            r"设计|创作|构思": "creative_design",
        }

        for pattern, action_type in action_patterns.items():
            if re.search(pattern, text):
                return action_type, 0.8

        return "general_activity", 0.5

    def _determine_required_nodes(self, action_type: str) -> List[NodeType]:
        """
        根据动作类型确定所需的逻辑节点

        Args:
            action_type: 动作类型

        Returns:
            List[NodeType]: 所需节点类型列表
        """
        node_mapping = {
            "retail_operation": [
                NodeType.LOCATION,
                NodeType.PRODUCT,
                NodeType.PRICING,
                NodeType.TIMING,
                NodeType.RESOURCE,
            ],
            "report_creation": [
                NodeType.TIMING,
                NodeType.RESOURCE,
                NodeType.EXECUTION,
            ],
            "software_development": [
                NodeType.PRODUCT,
                NodeType.TIMING,
                NodeType.RESOURCE,
                NodeType.EXECUTION,
            ],
            "creative_design": [
                NodeType.PRODUCT,
                NodeType.TIMING,
                NodeType.RESOURCE,
            ],
        }

        return node_mapping.get(action_type, [NodeType.TIMING, NodeType.RESOURCE])

    def process_user_input(self, user_input: str) -> Dict:
        """
        处理用户输入，初始化意图解析流程

        Args:
            user_input: 用户的原始输入文本

        Returns:
            Dict: 包含解析状态和下一步提示的字典

        示例:
            >>> compiler = IntuitionLogicCompiler()
            >>> result = compiler.process_user_input("我想摆个摊")
            >>> print(result["next_prompt"])
        """
        if not user_input or not isinstance(user_input, str):
            error_msg = "无效的输入：输入必须是非空字符串"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        session_id = self._generate_session_id()
        action_type, confidence = self._extract_action_type(user_input)
        required_nodes = self._determine_required_nodes(action_type)

        # 创建用户意图对象
        intent = UserIntent(
            raw_input=user_input,
            parsed_intent={"action_type": action_type, "confidence": confidence},
            required_nodes=required_nodes,
            current_state=ConversationState.CLARIFYING,
        )

        self.active_intents[session_id] = intent
        logger.info(f"Created new session {session_id} for action type: {action_type}")

        # 生成第一个节点的提问
        first_node = required_nodes[0]
        next_prompt = self._generate_node_question(first_node, action_type)

        return {
            "session_id": session_id,
            "status": "clarifying",
            "is_complete": False,
            "current_node": first_node.name,
            "next_prompt": next_prompt,
            "progress": f"1/{len(required_nodes)}",
        }

    def _generate_node_question(self, node_type: NodeType, action_type: str) -> str:
        """
        生成针对特定节点的提问

        Args:
            node_type: 节点类型
            action_type: 动作类型

        Returns:
            str: 生成的提问字符串
        """
        template = self.node_templates.get(node_type, {})
        question = template.get("question", "请提供更多关于{node}的信息")
        examples = template.get("examples", [])

        # 根据动作类型调整问题
        action_map = {
            "retail_operation": "经营",
            "report_creation": "完成任务",
            "software_development": "开发",
            "creative_design": "设计",
        }
        action = action_map.get(action_type, "操作")

        formatted_question = question.format(action=action, node=node_type.name)

        if examples:
            example_str = "、".join(examples[:3])
            formatted_question += f"\n参考示例：{example_str}"

        return formatted_question

    def continue_conversation(
        self, session_id: str, user_response: str
    ) -> Dict:
        """
        继续对话，处理用户对当前节点的回复

        Args:
            session_id: 会话ID
            user_response: 用户对当前问题的回复

        Returns:
            Dict: 包含下一状态和提示的字典

        Raises:
            ValueError: 当会话ID无效或会话不存在时
        """
        if session_id not in self.active_intents:
            error_msg = f"无效的会话ID: {session_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        intent = self.active_intents[session_id]

        if intent.current_state == ConversationState.COMPLETED:
            return {
                "session_id": session_id,
                "status": "already_completed",
                "is_complete": True,
                "message": "该会话已完成，请开始新的会话",
            }

        # 记录对话历史
        current_node = intent.required_nodes[len(intent.conversation_history)]
        intent.conversation_history.append(
            {
                "node_type": current_node.name,
                "question": self._generate_node_question(
                    current_node, intent.parsed_intent["action_type"]
                ),
                "response": user_response,
            }
        )

        # 解析用户回复并更新节点值
        self._update_node_value(intent, current_node, user_response)
        logger.info(f"Session {session_id}: Updated node {current_node.name}")

        # 检查是否所有节点都已完成
        if len(intent.conversation_history) >= len(intent.required_nodes):
            intent.current_state = ConversationState.CONFIRMING
            return self._generate_confirmation(intent, session_id)

        # 生成下一个节点的提问
        next_node = intent.required_nodes[len(intent.conversation_history)]
        next_prompt = self._generate_node_question(
            next_node, intent.parsed_intent["action_type"]
        )

        return {
            "session_id": session_id,
            "status": "clarifying",
            "is_complete": False,
            "current_node": next_node.name,
            "next_prompt": next_prompt,
            "progress": f"{len(intent.conversation_history)+1}/{len(intent.required_nodes)}",
        }

    def _update_node_value(
        self, intent: UserIntent, node_type: NodeType, user_response: str
    ) -> None:
        """
        更新节点值并验证

        Args:
            intent: 用户意图对象
            node_type: 节点类型
            user_response: 用户回复

        Raises:
            ValueError: 当用户回复无效时
        """
        # 简单的验证逻辑（实际应用中可扩展）
        if not user_response or len(user_response.strip()) < 2:
            raise ValueError("回复内容过短，请提供更详细的信息")

        # 根据节点类型进行不同的解析和验证
        if node_type == NodeType.PRICING:
            # 尝试提取价格信息
            price_pattern = r"(\d+)-(\d+)"
            match = re.search(price_pattern, user_response)
            if match:
                min_price, max_price = map(int, match.groups())
                if min_price <= 0 or max_price <= 0:
                    raise ValueError("价格必须为正数")
                if min_price > max_price:
                    raise ValueError("最低价不能高于最高价")
                value = {"min": min_price, "max": max_price, "raw": user_response}
            else:
                value = {"raw": user_response, "parsed": False}
        else:
            value = user_response

        # 更新parsed_intent
        if "nodes" not in intent.parsed_intent:
            intent.parsed_intent["nodes"] = {}

        intent.parsed_intent["nodes"][node_type.name] = {
            "value": value,
            "is_confirmed": False,
        }

    def _generate_confirmation(self, intent: UserIntent, session_id: str) -> Dict:
        """
        生成最终确认提示

        Args:
            intent: 用户意图对象
            session_id: 会话ID

        Returns:
            Dict: 包含确认信息的字典
        """
        # 构建摘要
        summary = self._build_intent_summary(intent)

        return {
            "session_id": session_id,
            "status": "confirming",
            "is_complete": False,
            "next_prompt": f"请确认您的计划摘要：\n{summary}\n\n确认无误请回复'确认'，需要修改请指出需要修改的部分。",
            "summary": summary,
        }

    def _build_intent_summary(self, intent: UserIntent) -> str:
        """
        构建意图摘要

        Args:
            intent: 用户意图对象

        Returns:
            str: 格式化的摘要字符串
        """
        summary_lines = [f"核心意图: {intent.parsed_intent['action_type']}"]

        nodes = intent.parsed_intent.get("nodes", {})
        for node_type, node_data in nodes.items():
            value = node_data.get("value", "未指定")
            if isinstance(value, dict):
                value = value.get("raw", str(value))
            summary_lines.append(f"- {node_type}: {value}")

        return "\n".join(summary_lines)

    def confirm_intent(self, session_id: str, confirmation: str) -> Dict:
        """
        确认最终意图并生成结构化JSON

        Args:
            session_id: 会话ID
            confirmation: 用户确认信息

        Returns:
            Dict: 最终的结构化JSON输出

        Raises:
            ValueError: 当会话不存在或状态不正确时
        """
        if session_id not in self.active_intents:
            raise ValueError(f"无效的会话ID: {session_id}")

        intent = self.active_intents[session_id]

        if intent.current_state != ConversationState.CONFIRMING:
            raise ValueError("当前会话状态不允许确认操作")

        if confirmation.lower() not in ["确认", "是的", "没问题", "确认无误"]:
            # 用户要求修改
            return {
                "session_id": session_id,
                "status": "modification_required",
                "is_complete": False,
                "message": "请指出需要修改的部分，我们将重新处理相关节点。",
            }

        # 标记所有节点为已确认
        for node_data in intent.parsed_intent.get("nodes", {}).values():
            node_data["is_confirmed"] = True

        intent.current_state = ConversationState.COMPLETED

        # 生成最终的结构化JSON
        result_json = {
            "session_id": session_id,
            "status": "completed",
            "is_complete": True,
            "action_plan": intent.parsed_intent,
            "conversation_history": intent.conversation_history,
            "metadata": {
                "compiler_version": "1.0.0",
                "completion_timestamp": self._get_current_timestamp(),
            },
        }

        logger.info(f"Session {session_id} completed successfully")
        return result_json

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳（ISO格式）"""
        from datetime import datetime

        return datetime.now().isoformat()

    def export_to_json(self, session_id: str, file_path: str) -> None:
        """
        将完成的意图导出为JSON文件

        Args:
            session_id: 会话ID
            file_path: 输出文件路径

        Raises:
            ValueError: 当会话不存在或未完成时
            IOError: 当文件写入失败时
        """
        if session_id not in self.active_intents:
            raise ValueError(f"无效的会话ID: {session_id}")

        intent = self.active_intents[session_id]

        if intent.current_state != ConversationState.COMPLETED:
            raise ValueError("只能导出已完成的会话")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(intent.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Session {session_id} exported to {file_path}")
        except IOError as e:
            logger.error(f"Failed to export session {session_id}: {str(e)}")
            raise


# 使用示例
if __name__ == "__main__":
    # 创建编译器实例
    compiler = IntuitionLogicCompiler()

    # 模拟用户交互流程
    print("=== 直觉-逻辑双向编译器演示 ===")
    user_input = "我想摆个摊"
    print(f"用户输入: {user_input}")

    # 初始处理
    result = compiler.process_user_input(user_input)
    session_id = result["session_id"]
    print(f"系统: {result['next_prompt']}")

    # 模拟多轮对话
    responses = [
        "我想在大学城附近摆摊",  # 选址
        "主要卖手工艺品和创意小礼品",  # 选品
        "价格在20-50元之间",  # 定价
        "下个月开始，周末和晚上",  # 时间
        "我有制作手工艺品的技能，还需要购买一些材料",  # 资源
    ]

    for response in responses:
        print(f"用户: {response}")
        result = compiler.continue_conversation(session_id, response)

        if result["status"] == "confirming":
            print(f"系统: {result['next_prompt']}")
            break
        else:
            print(f"系统: {result['next_prompt']}")

    # 最终确认
    print("用户: 确认")
    final_result = compiler.confirm_intent(session_id, "确认")
    print("\n最终结构化输出:")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))