"""
高级上下文感知的动态意图补全引擎
基于实践权重和环境约束实现动态参数填充
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentType(Enum):
    """意图类型枚举"""
    DEBUG = "debug"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    DEPLOY = "deploy"
    TEST = "test"

class ContextType(Enum):
    """上下文类型枚举"""
    CURSOR_POSITION = "cursor_position"
    RECENT_LOGS = "recent_logs"
    RECENT_FILES = "recent_files"
    DEVELOPER_PROFILE = "developer_profile"
    SYSTEM_STATUS = "system_status"

@dataclass
class ContextData:
    """上下文数据结构"""
    type: ContextType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    weight: float = 1.0  # 实践权重 (0.0-1.0)

@dataclass
class IntentParameter:
    """意图参数结构"""
    name: str
    value: Optional[Any] = None
    confidence: float = 0.0
    source: str = "unknown"  # 参数来源: explicit, inferred, default

@dataclass
class ParsedIntent:
    """解析后的意图结构"""
    intent_type: IntentType
    parameters: Dict[str, IntentParameter]
    confidence: float = 0.0
    context_used: List[ContextType] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class ContextAwareIntentEngine:
    """
    上下文感知的动态意图补全引擎
    
    功能特点:
    1. 基于实践权重的动态参数填充
    2. 多维度上下文感知 (代码位置、日志、开发者习惯等)
    3. 自动冲突解决和参数合并
    4. 支持渐进式意图解析
    
    使用示例:
    >>> engine = ContextAwareIntentEngine()
    >>> context = {
    ...     "cursor_position": {"file": "app.py", "line": 42},
    ...     "recent_logs": [{"level": "ERROR", "message": "NullPointerException"}]
    ... }
    >>> intent = engine.parse_intent("fix this bug", context)
    >>> print(intent.to_dict())
    """
    
    def __init__(self, max_context_age: int = 3600):
        """
        初始化引擎
        
        Args:
            max_context_age: 上下文最大有效期(秒)
        """
        self.max_context_age = max_context_age
        self._context_cache: Dict[ContextType, ContextData] = {}
        self._practice_weights: Dict[str, float] = {}
        self._intent_history: List[ParsedIntent] = []
        
        # 初始化默认实践权重
        self._init_default_weights()
        logger.info("ContextAwareIntentEngine initialized with max_context_age=%d", max_context_age)
    
    def _init_default_weights(self) -> None:
        """初始化默认实践权重"""
        self._practice_weights = {
            "cursor_position": 0.9,  # 光标位置权重最高
            "recent_logs": 0.8,
            "recent_files": 0.7,
            "developer_profile": 0.6,
            "system_status": 0.5
        }
    
    def update_context(self, context_type: ContextType, data: Dict[str, Any], weight: float = None) -> None:
        """
        更新上下文数据
        
        Args:
            context_type: 上下文类型
            data: 上下文数据
            weight: 可选的自定义权重
        """
        if not isinstance(context_type, ContextType):
            raise ValueError(f"Invalid context type: {context_type}")
            
        if weight is not None:
            if not 0.0 <= weight <= 1.0:
                raise ValueError("Weight must be between 0.0 and 1.0")
        
        effective_weight = weight if weight is not None else self._practice_weights.get(context_type.value, 0.5)
        
        self._context_cache[context_type] = ContextData(
            type=context_type,
            data=data,
            weight=effective_weight
        )
        logger.debug("Context updated: %s with weight %.2f", context_type.value, effective_weight)
    
    def parse_intent(self, command: str, additional_context: Dict[ContextType, Dict] = None) -> ParsedIntent:
        """
        解析用户意图
        
        Args:
            command: 用户输入的命令
            additional_context: 额外的上下文数据
            
        Returns:
            ParsedIntent: 解析后的意图对象
        """
        if not command or not isinstance(command, str):
            raise ValueError("Command must be a non-empty string")
        
        logger.info("Parsing intent for command: '%s'", command)
        
        # 合并临时上下文
        if additional_context:
            for ctx_type, data in additional_context.items():
                self.update_context(ctx_type, data)
        
        # 识别意图类型
        intent_type = self._detect_intent_type(command)
        if not intent_type:
            raise ValueError("Unable to determine intent type from command")
        
        # 收集相关上下文
        relevant_contexts = self._get_relevant_contexts(intent_type)
        
        # 解析参数
        parameters = self._extract_parameters(command, intent_type, relevant_contexts)
        
        # 创建意图对象
        intent = ParsedIntent(
            intent_type=intent_type,
            parameters=parameters,
            confidence=self._calculate_confidence(parameters, relevant_contexts),
            context_used=[ctx.type for ctx in relevant_contexts]
        )
        
        # 记录到历史
        self._intent_history.append(intent)
        if len(self._intent_history) > 100:  # 限制历史记录大小
            self._intent_history.pop(0)
        
        logger.info("Intent parsed: %s with confidence %.2f", intent_type.value, intent.confidence)
        return intent
    
    def _detect_intent_type(self, command: str) -> Optional[IntentType]:
        """检测意图类型"""
        command = command.lower()
        
        patterns = {
            IntentType.DEBUG: r'\b(fix|debug|solve|bug|error|issue)\b',
            IntentType.REFACTOR: r'\b(refactor|improve|optimize|clean)\b',
            IntentType.DOCUMENT: r'\b(document|comment|explain|doc)\b',
            IntentType.DEPLOY: r'\b(deploy|release|ship|publish)\b',
            IntentType.TEST: r'\b(test|spec|verify|check)\b'
        }
        
        for intent_type, pattern in patterns.items():
            if re.search(pattern, command):
                return intent_type
        
        return None
    
    def _get_relevant_contexts(self, intent_type: IntentType) -> List[ContextData]:
        """获取与意图类型相关的上下文"""
        now = datetime.now()
        relevant = []
        
        # 根据意图类型确定需要哪些上下文
        context_priority = {
            IntentType.DEBUG: [
                ContextType.CURSOR_POSITION,
                ContextType.RECENT_LOGS,
                ContextType.RECENT_FILES
            ],
            IntentType.REFACTOR: [
                ContextType.CURSOR_POSITION,
                ContextType.RECENT_FILES,
                ContextType.DEVELOPER_PROFILE
            ],
            # 其他意图类型的优先级...
        }
        
        priority = context_priority.get(intent_type, list(ContextType))
        
        for ctx_type in priority:
            if ctx_type in self._context_cache:
                ctx = self._context_cache[ctx_type]
                age = (now - ctx.timestamp).total_seconds()
                if age <= self.max_context_age:
                    relevant.append(ctx)
        
        return relevant
    
    def _extract_parameters(
        self,
        command: str,
        intent_type: IntentType,
        contexts: List[ContextData]
    ) -> Dict[str, IntentParameter]:
        """从命令和上下文中提取参数"""
        parameters = {}
        
        # 基础参数提取
        if intent_type == IntentType.DEBUG:
            parameters.update(self._extract_debug_params(command, contexts))
        elif intent_type == IntentType.REFACTOR:
            parameters.update(self._extract_refactor_params(command, contexts))
        # 其他意图类型的参数提取...
        
        # 填充默认参数
        self._fill_default_parameters(parameters, intent_type, contexts)
        
        return parameters
    
    def _extract_debug_params(
        self,
        command: str,
        contexts: List[ContextData]
    ) -> Dict[str, IntentParameter]:
        """提取调试相关参数"""
        params = {}
        
        # 从光标位置获取文件和行号
        cursor_ctx = next((ctx for ctx in contexts if ctx.type == ContextType.CURSOR_POSITION), None)
        if cursor_ctx:
            file_data = cursor_ctx.data
            params["file_path"] = IntentParameter(
                name="file_path",
                value=file_data.get("file"),
                confidence=cursor_ctx.weight,
                source="cursor_position"
            )
            params["line_number"] = IntentParameter(
                name="line_number",
                value=file_data.get("line"),
                confidence=cursor_ctx.weight,
                source="cursor_position"
            )
        
        # 从日志中提取错误信息
        logs_ctx = next((ctx for ctx in contexts if ctx.type == ContextType.RECENT_LOGS), None)
        if logs_ctx and logs_ctx.data.get("errors"):
            error_data = logs_ctx.data["errors"][0]  # 取最近的错误
            params["error_type"] = IntentParameter(
                name="error_type",
                value=error_data.get("type"),
                confidence=logs_ctx.weight,
                source="recent_logs"
            )
            params["error_message"] = IntentParameter(
                name="error_message",
                value=error_data.get("message"),
                confidence=logs_ctx.weight,
                source="recent_logs"
            )
        
        return params
    
    def _extract_refactor_params(
        self,
        command: str,
        contexts: List[ContextData]
    ) -> Dict[str, IntentParameter]:
        """提取重构相关参数"""
        params = {}
        
        # 从光标位置获取文件和行号
        cursor_ctx = next((ctx for ctx in contexts if ctx.type == ContextType.CURSOR_POSITION), None)
        if cursor_ctx:
            file_data = cursor_ctx.data
            params["file_path"] = IntentParameter(
                name="file_path",
                value=file_data.get("file"),
                confidence=cursor_ctx.weight,
                source="cursor_position"
            )
            
            # 提取方法名或类名
            if "method" in file_data:
                params["method_name"] = IntentParameter(
                    name="method_name",
                    value=file_data["method"],
                    confidence=cursor_ctx.weight * 0.9,
                    source="cursor_position"
                )
        
        return params
    
    def _fill_default_parameters(
        self,
        parameters: Dict[str, IntentParameter],
        intent_type: IntentType,
        contexts: List[ContextData]
    ) -> None:
        """填充默认参数"""
        # 为调试意图添加默认参数
        if intent_type == IntentType.DEBUG:
            if "file_path" not in parameters:
                # 尝试从最近文件中获取
                recent_files_ctx = next(
                    (ctx for ctx in contexts if ctx.type == ContextType.RECENT_FILES),
                    None
                )
                if recent_files_ctx and recent_files_ctx.data.get("files"):
                    parameters["file_path"] = IntentParameter(
                        name="file_path",
                        value=recent_files_ctx.data["files"][0],
                        confidence=recent_files_ctx.weight * 0.7,
                        source="recent_files"
                    )
        
        # 为重构意图添加默认参数
        elif intent_type == IntentType.REFACTOR:
            if "scope" not in parameters:
                parameters["scope"] = IntentParameter(
                    name="scope",
                    value="method",  # 默认重构方法级别
                    confidence=0.5,
                    source="default"
                )
    
    def _calculate_confidence(
        self,
        parameters: Dict[str, IntentParameter],
        contexts: List[ContextData]
    ) -> float:
        """计算意图置信度"""
        if not parameters:
            return 0.0
        
        # 参数置信度的加权平均
        total_confidence = 0.0
        total_weight = 0.0
        
        for param in parameters.values():
            total_confidence += param.confidence
            total_weight += 1.0
        
        avg_param_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        
        # 上下文完整度
        context_score = len(contexts) / len(ContextType)
        
        # 综合置信度 (参数70% + 上下文30%)
        final_confidence = avg_param_confidence * 0.7 + context_score * 0.3
        return min(max(final_confidence, 0.0), 1.0)  # 确保在0-1之间
    
    def get_intent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取意图历史记录"""
        return [intent.to_dict() for intent in self._intent_history[-limit:]]
    
    def clear_context_cache(self) -> None:
        """清空上下文缓存"""
        self._context_cache.clear()
        logger.info("Context cache cleared")

def to_dict(self) -> Dict[str, Any]:
    """将ParsedIntent转换为字典"""
    return {
    "intent_type": self.intent_type.value,
    "parameters": {
        name: {
            "value": param.value,
            "confidence": param.confidence,
            "source": param.source
        } for name, param in self.parameters.items()
    },
    "confidence": self.confidence,
    "context_used": [ctx.value for ctx in self.context_used],
    "timestamp": self.timestamp.isoformat()
}

# 添加到ParsedIntent类中
ParsedIntent.to_dict = to_dict

# 使用示例
if __name__ == "__main__":
    try:
        # 创建引擎实例
        engine = ContextAwareIntentEngine(max_context_age=1800)
        
        # 更新上下文数据
        engine.update_context(
            ContextType.CURSOR_POSITION,
            {"file": "src/main.py", "line": 42, "method": "process_data"},
            weight=0.95
        )
        
        engine.update_context(
            ContextType.RECENT_LOGS,
            {
                "errors": [
                    {
                        "type": "NullPointerException",
                        "message": "Object reference not set to an instance",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            },
            weight=0.85
        )
        
        engine.update_context(
            ContextType.DEVELOPER_PROFILE,
            {"preferred_scope": "method", "experience_level": "senior"},
            weight=0.7
        )
        
        # 解析意图
        intent = engine.parse_intent("fix this bug")
        print("\nParsed Intent:")
        print(json.dumps(intent.to_dict(), indent=2))
        
        # 解析另一个意图
        refactor_intent = engine.parse_intent("refactor this code")
        print("\nParsed Refactor Intent:")
        print(json.dumps(refactor_intent.to_dict(), indent=2))
        
        # 查看意图历史
        print("\nIntent History:")
        print(json.dumps(engine.get_intent_history(2), indent=2))
        
    except Exception as e:
        logger.error("Error in example execution: %s", str(e), exc_info=True)