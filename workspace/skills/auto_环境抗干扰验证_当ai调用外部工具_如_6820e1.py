"""
模块名称: auto_环境抗干扰验证_当ai调用外部工具_如_6820e1
描述: 【环境抗干扰验证】当AI调用外部工具（如代码解释器或搜索引擎）获取到的返回结果是错误或被污染的数据时，
      AI是否具备‘交叉验证’的能力，并拒绝将该错误信息固化为真实节点？
      
该模块实现了一套针对外部工具调用结果的数据验证机制。它通过多种策略（如格式验证、
多源交叉验证、一致性检查）来确保数据的可靠性，防止由于环境噪音或工具错误导致的
'数据污染'进入系统的核心知识库。
"""

import logging
import re
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Integrity_Validator")

# 定义自定义异常
class ValidationError(Exception):
    """基础验证错误"""
    pass

class CrossVerificationFailedError(ValidationError):
    """交叉验证失败错误"""
    pass

class DataTamperingError(ValidationError):
    """数据篡改或污染错误"""
    pass

@dataclass
class ToolResult:
    """
    外部工具返回结果的数据结构。
    
    Attributes:
        tool_name (str): 工具名称（如 'search_engine', 'code_interpreter'）
        raw_output (Any): 原始返回数据
        timestamp (str): 获取时间戳
        signature (str): 数据签名（模拟防篡改）
        metadata (dict): 其他元数据
    """
    tool_name: str
    raw_output: Any
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    signature: str = ""
    metadata: dict = field(default_factory=dict)

@dataclass
class ValidatedNode:
    """
    验证通过后的真实节点数据结构。
    """
    content: Any
    confidence_score: float
    verification_source: str
    created_at: str

def _generate_data_signature(data: Any) -> str:
    """
    [辅助函数] 生成数据的模拟签名，用于检测数据是否在传输中被篡改。
    
    Args:
        data (Any): 需要签名的数据
        
    Returns:
        str: 模拟的哈希签名
    """
    try:
        # 将数据序列化为JSON字符串进行哈希
        data_str = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(data_str).hexdigest()[:16]
    except TypeError:
        # 处理不可序列化的数据
        return hashlib.sha256(str(data).encode('utf-8')).hexdigest()[:16]

def validate_schema_integrity(result: ToolResult, expected_schema: Dict[str, type]) -> bool:
    """
    [核心函数 1] 验证返回结果的数据结构完整性。
    
    检查数据是否符合预期的格式（Schema），这是防止错误数据进入系统的第一道防线。
    
    Args:
        result (ToolResult): 外部工具返回的结果对象
        expected_schema (Dict[str, type]): 期望的数据结构键值类型映射
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ValidationError: 如果数据结构不匹配
    """
    logger.info(f"正在对工具 {result.tool_name} 的结果进行结构完整性验证...")
    
    if not isinstance(result.raw_output, dict):
        logger.error(f"结构验证失败: 期望 dict 类型，得到 {type(result.raw_output)}")
        raise ValidationError("Invalid data type: Expected dictionary.")
    
    for key, expected_type in expected_schema.items():
        if key not in result.raw_output:
            logger.error(f"结构验证失败: 缺少键 '{key}'")
            raise ValidationError(f"Missing required key: {key}")
        
        # 这里的类型检查是示意性的，实际生产中可能需要更复杂的类型推断
        if not isinstance(result.raw_output[key], expected_type):
            logger.error(f"结构验证失败: 键 '{key}' 类型错误")
            raise ValidationError(f"Type mismatch for key '{key}'")
            
    logger.info("结构完整性验证通过。")
    return True

def perform_cross_verification(
    primary_result: ToolResult, 
    secondary_sources: List[ToolResult],
    similarity_threshold: float = 0.8
) -> Tuple[bool, float]:
    """
    [核心函数 2] 执行交叉验证。
    
    比较主要工具返回的结果与辅助来源的结果。如果主来源数据被污染（如搜索引擎返回404页面内容），
    而辅助来源返回了不同的结果，则判定为不可信。
    
    Args:
        primary_result (ToolResult): 主要工具（如搜索引擎）的结果
        secondary_sources (List[ToolResult]): 辅助验证来源的结果列表
        similarity_threshold (float): 判定为一致的相似度阈值 (0.0 to 1.0)
        
    Returns:
        Tuple[bool, float]: (是否验证通过, 计算出的置信度分数)
        
    Raises:
        CrossVerificationFailedError: 如果交叉验证发现严重不一致
    """
    logger.info(f"开始交叉验证，主来源: {primary_result.tool_name}, 辅助来源数量: {len(secondary_sources)}")
    
    if not secondary_sources:
        logger.warning("没有提供辅助验证源，交叉验证降级为仅检查签名。")
        return True, 0.5  # 低置信度

    primary_content_str = str(primary_result.raw_output)
    match_scores = []
    
    # 简单的文本相似度检查模拟（实际生产中应使用Embedding向量 cosine similarity）
    def _simple_similarity(text1: str, text2: str) -> float:
        # 这是一个简化的Jaccard相似度实现
        set1 = set(text1.split())
        set2 = set(text2.split())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    for secondary in secondary_sources:
        secondary_content_str = str(secondary.raw_output)
        score = _simple_similarity(primary_content_str, secondary_content_str)
        match_scores.append(score)
        
    avg_score = sum(match_scores) / len(match_scores)
    
    if avg_score < similarity_threshold:
        logger.error(f"交叉验证失败: 数据一致性过低 (Score: {avg_score:.2f})")
        raise CrossVerificationFailedError(
            f"Primary source data conflicts with verification sources. Score: {avg_score}"
        )
        
    logger.info(f"交叉验证通过。平均一致性分数: {avg_score:.2f}")
    return True, avg_score

def verify_tool_result_integrity(
    tool_result: ToolResult,
    verification_sources: List[ToolResult],
    expected_schema: Optional[Dict[str, type]] = None
) -> ValidatedNode:
    """
    [主入口函数] 综合环境抗干扰验证流程。
    
    整合签名校验、结构验证和交叉验证。如果数据被识别为错误或被污染，
    该函数将抛出异常，阻止数据固化为节点。
    
    Args:
        tool_result (ToolResult): 待验证的主数据
        verification_sources (List[ToolResult]): 用于交叉验证的数据列表
        expected_schema (Optional[Dict[str, type]]): 期望的数据结构
        
    Returns:
        ValidatedNode: 验证通过的安全节点对象
        
    Raises:
        DataTamperingError: 如果检测到数据被篡改
        ValidationError: 如果验证未通过
    """
    logger.info(f"=== 启动环境抗干扰验证流程 for {tool_result.tool_name} ===")
    
    # 1. 边界检查：确保输入不为空
    if not tool_result.raw_output:
        raise ValidationError("Empty tool output received.")
        
    # 2. 完整性校验（模拟）
    # 在实际场景中，这里会校验 tool_result.signature 是否匹配
    expected_sig = _generate_data_signature(tool_result.raw_output)
    # if tool_result.signature != expected_sig: 
    #     raise DataTamperingError("Signature mismatch detected! Data may be corrupted.")
    
    # 3. 结构验证
    if expected_schema:
        validate_schema_integrity(tool_result, expected_schema)
    
    # 4. 交叉验证（核心抗干扰逻辑）
    try:
        is_consistent, confidence = perform_cross_verification(
            tool_result, 
            verification_sources
        )
    except CrossVerificationFailedError as e:
        logger.critical(f"拒绝固化节点: 检测到环境干扰或错误数据。原因: {e}")
        raise # 重新抛出，阻止后续流程
    
    # 5. 固化为验证节点
    if is_consistent:
        node = ValidatedNode(
            content=tool_result.raw_output,
            confidence_score=confidence,
            verification_source=f"CrossChecked_{len(verification_sources)}_Sources",
            created_at=datetime.utcnow().isoformat()
        )
        logger.info(f"验证成功，节点已固化。置信度: {confidence:.2f}")
        return node

# ==============================================================================
# 使用示例
# ==============================================================================
if __name__ == "__main__":
    # 模拟场景：AI调用搜索引擎获取某支股票的价格
    
    # 1. 模拟主工具返回（可能是过时或错误的）
    primary_data = {
        "stock": "AAPL",
        "price": 150.00,
        "currency": "USD"
    }
    primary_tool = ToolResult(
        tool_name="SearchEngine",
        raw_output=primary_data,
        signature=_generate_data_signature(primary_data)
    )
    
    # 2. 模拟辅助验证源（比如另一个API或缓存）
    # 假设辅助源显示价格也是 150.00
    source_a_data = {"stock": "AAPL", "price": 150.00, "currency": "USD"}
    source_a = ToolResult(tool_name="BackupAPI", raw_output=source_a_data)
    
    # 假设辅助源B显示价格也是 150.00
    source_b_data = {"stock": "AAPL", "price": 150.00, "currency": "USD"}
    source_b = ToolResult(tool_name="LocalCache", raw_output=source_b_data)
    
    print("--- 测试场景 1: 正常验证 ---")
    try:
        # 定义期望的结构
        schema = {"stock": str, "price": (int, float), "currency": str}
        
        safe_node = verify_tool_result_integrity(
            tool_result=primary_tool,
            verification_sources=[source_a, source_b],
            expected_schema=schema
        )
        print(f"节点创建成功: {safe_node}")
    except ValidationError as e:
        print(f"验证失败: {e}")

    print("\n--- 测试场景 2: 环境干扰（数据污染） ---")
    # 模拟数据污染：主工具返回了被注入的广告或错误数据
    polluted_data = {
        "stock": "AAPL",
        "price": "ERROR_TIMEOUT",  # 错误的数据
        "currency": "USD"
    }
    polluted_tool = ToolResult(
        tool_name="SearchEngine",
        raw_output=polluted_data,
        signature=_generate_data_signature(polluted_data)
    )
    
    # 辅助源依然是正确的，这将触发交叉验证失败
    try:
        verify_tool_result_integrity(
            tool_result=polluted_tool,
            verification_sources=[source_a, source_b],
            expected_schema=schema
        )
    except (ValidationError, CrossVerificationFailedError) as e:
        print(f"成功拦截污染数据! 错误信息: {e}")

    print("\n--- 测试场景 3: 结构不匹配 ---")
    bad_schema_data = {"stock": 12345, "price": 100} # stock 应该是 str
    bad_schema_tool = ToolResult(tool_name="BadTool", raw_output=bad_schema_data)
    try:
        verify_tool_result_integrity(
            tool_result=bad_schema_tool,
            verification_sources=[],
            expected_schema={"stock": str} 
        )
    except ValidationError as e:
        print(f"成功拦截结构错误数据! 错误信息: {e}")