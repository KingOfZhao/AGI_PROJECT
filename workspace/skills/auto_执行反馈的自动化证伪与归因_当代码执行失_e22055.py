"""
模块名称: auto_执行反馈的自动化证伪与归因_当代码执行失_e22055
描述: 本模块实现了AGI认知架构中的核心元认知功能——执行反馈的自动化证伪与归因。
      当代码执行失败时，通过分析堆栈跟踪和环境上下文，将错误映射回认知图谱中的
      具体节点（如API参数、逻辑门控），并判断错误的根源是意图理解错误
      还是技能节点过时，从而实现自下而上的认知更新。
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Meta_Falsification")


class ErrorCategory(Enum):
    """错误类型枚举，用于区分归因类别"""
    INTENT_MISMATCH = "Intent_Mismatch"      # 意图理解错误：代码逻辑符合预期但不符合用户真实需求
    SKILL_OBSOLETE = "Skill_Obsolete"         # 技能节点过时：API接口变更、库版本不兼容
    LOGIC_ERROR = "Logic_Error"               # 逻辑/语法错误：变量未定义、类型错误
    ENV_CONTEXT_ERROR = "Environment_Error"   # 环境上下文错误：文件缺失、权限不足
    UNKNOWN = "Unknown"


@dataclass
class CognitiveNode:
    """认知网络中的节点数据结构"""
    node_id: str
    node_type: str  # e.g., 'API_CALL', 'INTENT', 'DATA_TRANSFORMATION'
    content: str    # 节点具体内容，如代码片段或描述
    version: str = "v1.0"
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ExecutionTrace:
    """执行轨迹数据结构，包含报错信息"""
    trace_id: str
    error_message: str
    stack_trace: str
    failed_code_snippet: str
    context_variables: Dict[str, Any]


@dataclass
class AttributionResult:
    """归因结果数据结构"""
    success: bool
    category: ErrorCategory
    suspected_node_id: Optional[str] = None
    confidence_score: float = 0.0
    reason: str = ""
    suggested_action: str = ""


class AutoFalsificationAttribution:
    """
    执行反馈的自动化证伪与归因核心类。
    
    负责将运行时错误映射回认知节点，确定是意图错误还是技能过时。
    
    输入格式:
        - cognitive_map: Dict[str, CognitiveNode] 认知图谱
        - execution_trace: ExecutionTrace 执行轨迹
        
    输出格式:
        - AttributionResult: 包含归因结果和建议动作的对象
    """

    def __init__(self, cognitive_map: Dict[str, CognitiveNode]):
        """
        初始化归因引擎。
        
        Args:
            cognitive_map (Dict[str, CognitiveNode]): 当前上下文的认知节点映射表。
        """
        self.cognitive_map = cognitive_map
        self._error_patterns = self._load_error_patterns()
        logger.info("AutoFalsificationAttribution Engine Initialized.")

    def _load_error_patterns(self) -> Dict[str, Any]:
        """加载预定义的错误模式匹配规则（模拟）"""
        return {
            "deprecated_api": {
                "pattern": r"AttributeError:.*object has no attribute '(\w+)'",
                "type": ErrorCategory.SKILL_OBSOLETE
            },
            "type_mismatch": {
                "pattern": r"TypeError:.*",
                "type": ErrorCategory.LOGIC_ERROR
            },
            "file_not_found": {
                "pattern": r"FileNotFoundError:.*",
                "type": ErrorCategory.ENV_CONTEXT_ERROR
            }
        }

    def _extract_semantic_signature(self, code_snippet: str) -> set:
        """
        辅助函数：从代码片段中提取语义签名（关键词）。
        
        Args:
            code_snippet (str): 失败的代码片段。
            
        Returns:
            set: 关键词集合。
        """
        # 简单模拟：提取函数调用和变量名
        tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code_snippet)
        stop_words = {"the", "a", "in", "is", "if", "else", "for", "return"}
        return {t for t in tokens if t not in stop_words and len(t) > 2}

    def _map_trace_to_node(self, trace: ExecutionTrace) -> Tuple[Optional[CognitiveNode], float]:
        """
        核心函数1: 将执行轨迹映射到具体的认知节点。
        
        通过词法分析和相似度匹配，找到认知网络中与错误代码最相关的节点。
        
        Args:
            trace (ExecutionTrace): 包含报错信息的执行轨迹。
            
        Returns:
            Tuple[Optional[CognitiveNode], float]: 返回最匹配的节点和匹配置信度。
        """
        error_tokens = self._extract_semantic_signature(trace.failed_code_snippet)
        best_match_node = None
        max_score = 0.0
        
        if not error_tokens:
            logger.warning("Empty semantic signature extracted from trace.")
            return None, 0.0

        for node_id, node in self.cognitive_map.items():
            node_tokens = self._extract_semantic_signature(node.content)
            
            # 计算Jaccard相似度作为基础分
            intersection = len(error_tokens.intersection(node_tokens))
            union = len(error_tokens.union(node_tokens))
            score = intersection / union if union > 0 else 0.0
            
            # 堆栈跟踪中包含节点ID则大幅加权
            if node.node_id in trace.stack_trace:
                score += 0.5  # Boost score
                
            if score > max_score:
                max_score = score
                best_match_node = node
                
        logger.info(f"Mapped trace to node {best_match_node.node_id if best_match_node else 'None'} with score {max_score:.2f}")
        return best_match_node, min(max_score, 1.0)

    def _determine_error_category(self, trace: ExecutionTrace, node: Optional[CognitiveNode]) -> ErrorCategory:
        """
        核心函数2: 判断错误类别（意图错误 vs 技能过时）。
        
        逻辑：
        1. 检查报错信息是否匹配已知的API废弃模式 -> SKILL_OBSOLETE
        2. 如果代码运行成功但结果非预期（此处假设传入的是Exception），则检查逻辑一致性。
        3. 如果是环境配置问题 -> ENV_CONTEXT_ERROR
        
        Args:
            trace (ExecutionTrace): 执行轨迹。
            node (Optional[CognitiveNode]): 关联的认知节点。
            
        Returns:
            ErrorCategory: 错误分类枚举值。
        """
        err_msg = trace.error_message
        
        # 模式匹配检查
        for key, rule in self._error_patterns.items():
            if re.search(rule["pattern"], err_msg):
                logger.info(f"Error pattern matched: {key}")
                return rule["type"]
        
        # 模拟深层语义检查：如果节点类型是API但报错是参数类型，可能是库更新导致的接口变更
        if node and node.node_type == "API_CALL":
            if "unexpected keyword argument" in err_msg or "missing 1 required positional argument" in err_msg:
                logger.info("API signature mismatch detected, categorizing as Skill Obsolete.")
                return ErrorCategory.SKILL_OBSOLETE

        # 如果节点是意图层，但执行层报逻辑错误，通常是意图落地偏差
        if node and node.node_type == "INTENT":
             return ErrorCategory.INTENT_MISMATCH
             
        return ErrorCategory.LOGIC_ERROR

    def analyze_and_attribute(self, trace: ExecutionTrace) -> AttributionResult:
        """
        执行完整的归因分析流程。
        
        Args:
            trace (ExecutionTrace): 输入的执行轨迹数据。
            
        Returns:
            AttributionResult: 分析结果。
        """
        if not trace or not trace.error_message:
            return AttributionResult(False, ErrorCategory.UNKNOWN, reason="Invalid trace input")
            
        try:
            # Step 1: 映射节点
            suspected_node, confidence = self._map_trace_to_node(trace)
            
            # Step 2: 归因分类
            category = self._determine_error_category(trace, suspected_node)
            
            # Step 3: 生成建议
            action = ""
            if category == ErrorCategory.SKILL_OBSOLETE:
                action = f"Trigger 'Skill_Update' agent for node {suspected_node.node_id if suspected_node else 'Unknown'}. Check library docs."
            elif category == ErrorCategory.INTENT_MISMATCH:
                action = "Re-evaluate user prompt alignment. Consider generating clarification question."
            elif category == ErrorCategory.LOGIC_ERROR:
                action = "Retry code generation with modified temperature or additional constraints."
            
            return AttributionResult(
                success=True,
                category=category,
                suspected_node_id=suspected_node.node_id if suspected_node else None,
                confidence_score=confidence,
                reason=f"Error classified as {category.value} based on pattern matching.",
                suggested_action=action
            )
            
        except Exception as e:
            logger.error(f"Critical error during attribution: {str(e)}")
            return AttributionResult(False, ErrorCategory.UNKNOWN, reason=str(e))

# 使用示例
if __name__ == "__main__":
    # 1. 构造模拟的认知网络
    mock_cognitive_map = {
        "node_001": CognitiveNode(
            node_id="node_001", 
            node_type="API_CALL", 
            content="requests.get(url, params=data)", 
            version="v2.0"
        ),
        "node_002": CognitiveNode(
            node_id="node_002", 
            node_type="INTENT", 
            content="Fetch user details from API", 
            version="v1.0"
        )
    }

    # 2. 构造模拟的失败执行轨迹
    # 假设 requests 库更新，get 方法不再接受 params 参数（模拟场景）
    failed_trace = ExecutionTrace(
        trace_id="exec_987",
        error_message="TypeError: requests.get() got an unexpected keyword argument 'params'",
        stack_trace="Traceback (most recent call last):\n  File \"agent.py\", line 45, in run\n    requests.get(url, params=data)\nTypeError: ...",
        failed_code_snippet="requests.get(api_url, params=query_data)",
        context_variables={"api_url": "http://example.com"}
    )

    # 3. 初始化引擎并执行分析
    engine = AutoFalsificationAttribution(mock_cognitive_map)
    result = engine.analyze_and_attribute(failed_trace)

    # 4. 输出结果
    print(f"--- Attribution Report ---")
    print(f"Success: {result.success}")
    print(f"Category: {result.category.value}")
    print(f"Suspected Node: {result.suspected_node_id}")
    print(f"Confidence: {result.confidence_score}")
    print(f"Action: {result.suggested_action}")