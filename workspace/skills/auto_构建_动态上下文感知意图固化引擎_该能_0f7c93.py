"""
模块名称: dynamic_context_engine
功能描述: 构建'动态上下文感知意图固化引擎'。该能力不仅解析自然语言为JSON，
         还能结合当前任务状态（上下文），自动推断并补全用户省略的隐含参数，
         将模糊意图转化为可立即执行的、包含所有必要参数的'真实节点'操作指令。
版本: 1.0.0
作者: AGI System
创建日期: 2023-10-27
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentCategory(Enum):
    """意图类别枚举"""
    FILE_OPERATION = "file_operation"
    DATA_QUERY = "data_query"
    SYSTEM_CONFIG = "system_config"
    UNKNOWN = "unknown"

@dataclass
class ContextState:
    """
    当前任务的上下文状态。
    
    属性:
        last_visited_ids: 最近访问的对象ID列表，用于解析“那个”等指代词
        active_workflow: 当前激活的工作流名称
        environment_vars: 环境变量或全局配置
        history: 历史交互记录简表
    """
    last_visited_ids: List[str] = field(default_factory=list)
    active_workflow: str = "default_flow"
    environment_vars: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ActionableNode:
    """
    真实节点操作指令结构。
    
    属性:
        action: 具体的动作类型
        params: 完整的参数字典
        confidence: 解析置信度 (0.0 - 1.0)
        requires_confirmation: 是否需要用户二次确认（当置信度低时）
    """
    action: str
    params: Dict[str, Any]
    confidence: float = 1.0
    requires_confirmation: bool = False

class ContextAwareIntentEngine:
    """
    动态上下文感知意图固化引擎。
    
    负责将自然语言输入结合 ContextState 转化为结构化的 ActionableNode。
    """
    
    def __init__(self, initial_context: Optional[ContextState] = None):
        """
        初始化引擎。
        
        Args:
            initial_context: 初始上下文状态，如果为None则创建默认状态。
        """
        self.context = initial_context if initial_context else ContextState()
        logger.info("ContextAwareIntentEngine initialized with context: %s", self.context.active_workflow)

    def update_context(self, new_data: Dict[str, Any]) -> None:
        """
        更新当前上下文状态。
        
        Args:
            new_data: 包含更新字段的字典
        """
        if "last_visited_ids" in new_data:
            self.context.last_visited_ids = new_data["last_visited_ids"]
        if "active_workflow" in new_data:
            self.context.active_workflow = new_data["active_workflow"]
        logger.debug("Context updated.")

    def _infer_category(self, text: str) -> IntentCategory:
        """
        [辅助函数] 基于关键词推断意图类别。
        
        Args:
            text: 输入文本
            
        Returns:
            IntentCategory 枚举值
        """
        text = text.lower()
        if any(word in text for word in ["文件", "删除", "移动", "file", "delete"]):
            return IntentCategory.FILE_OPERATION
        if any(word in text for word in ["查询", "搜索", "检查", "query", "search"]):
            return IntentCategory.DATA_QUERY
        if any(word in text for word in ["配置", "设置", "config", "set"]):
            return IntentCategory.SYSTEM_CONFIG
        return IntentCategory.UNKNOWN

    def _resolve_deictic_references(self, text: str, extracted_params: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        [核心函数 1] 解析并补全模糊指代（如“那个”、“刚才的”）。
        
        结合 ContextState 中的 last_visited_ids 进行消歧。
        
        Args:
            text: 原始输入文本
            extracted_params: 初步提取的参数
            
        Returns:
            (补全后的参数字典, 置信度)
        """
        params = extracted_params.copy()
        confidence = 1.0
        
        # 检测模糊指代词
        vague_patterns = ["那个", "刚才的", "上一个", "it", "that", "the one"]
        has_vague_ref = any(re.search(rf"\b{p}\b", text.lower()) for p in vague_patterns)
        
        # 如果参数中缺少目标ID，且文本中包含指代词，尝试补全
        if "target_id" not in params and has_vague_ref:
            if self.context.last_visited_ids:
                # 默认取最近的一个ID (LIFO)
                inferred_id = self.context.last_visited_ids[0]
                params["target_id"] = inferred_id
                params["source_context"] = "inferred_from_history"
                
                # 简单的置信度计算：历史记录越少，指代越明确，置信度越高
                confidence = 0.9 if len(self.context.last_visited_ids) == 1 else 0.7
                logger.info(f"Inferred target_id '{inferred_id}' from context for vague reference.")
            else:
                confidence = 0.2
                logger.warning("Vague reference found but context is empty.")
        
        return params, confidence

    def solidify_intent(self, natural_language_input: str) -> ActionableNode:
        """
        [核心函数 2] 将自然语言转化为固化的可执行节点。
        
        流程:
        1. 初步意图分类
        2. 基础参数提取（模拟NLP解析）
        3. 上下文消歧与参数补全
        4. 数据验证与封装
        
        Args:
            natural_language_input: 用户的自然语言输入
            
        Returns:
            ActionableNode 对象
            
        Raises:
            ValueError: 如果输入为空或无法解析
        """
        if not natural_language_input or not natural_language_input.strip():
            raise ValueError("Input text cannot be empty")

        logger.info(f"Processing input: {natural_language_input}")
        
        # 1. 意图分类
        category = self._infer_category(natural_language_input)
        
        # 2. 基础参数提取 (模拟 NLP 解析结果)
        # 假设解析出了一些显式参数，但缺少隐式参数
        raw_params = {
            "raw_text": natural_language_input,
            "timestamp": "2023-10-27T10:00:00Z" # 模拟时间戳
        }
        
        # 简单的实体提取模拟
        if "删除" in natural_language_input or "delete" in natural_language_input:
            action = "delete_object"
        elif "查询" in natural_language_input or "query" in natural_language_input:
            action = "get_status"
        else:
            action = "generic_action"
            
        # 3. 上下文消歧 - 核心步骤
        resolved_params, confidence = self._resolve_deictic_references(natural_language_input, raw_params)
        
        # 4. 验证与边界检查
        # 如果是删除操作且置信度低于0.8，强制要求确认
        requires_confirmation = False
        if action == "delete_object" and confidence < 0.85:
            requires_confirmation = True
            logger.warning(f"Low confidence ({confidence}) for destructive action. Flagging for confirmation.")
            
        # 补充元数据
        resolved_params["domain"] = category.value
        resolved_params["triggering_workflow"] = self.context.active_workflow
        
        # 构建最终节点
        node = ActionableNode(
            action=action,
            params=resolved_params,
            confidence=confidence,
            requires_confirmation=requires_confirmation
        )
        
        logger.info(f"Intent solidified: Action={action}, Params={resolved_params}, Conf={confidence}")
        return node

# 使用示例
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = ContextAwareIntentEngine()
    
    # 2. 模拟上下文注入：假设用户刚刚浏览了 ID 为 "doc_1024" 的文件
    engine.update_context({"last_visited_ids": ["doc_1024", "img_2048"]})
    
    # 3. 输入模糊指令
    user_input = "把那个文件删掉"  # "那个" 具体指代不明，需要引擎推断
    
    try:
        # 4. 执行意图固化
        executable_node = engine.solidify_intent(user_input)
        
        # 5. 打印结果
        print("\n--- Execution Result ---")
        print(f"Action: {executable_node.action}")
        print(f"Target ID: {executable_node.params.get('target_id', 'N/A')}")
        print(f"Confidence: {executable_node.confidence}")
        print(f"Needs Confirmation: {executable_node.requires_confirmation}")
        print(f"Full JSON: {json.dumps(executable_node.params, indent=2)}")
        
    except ValueError as e:
        logger.error(f"Processing failed: {e}")