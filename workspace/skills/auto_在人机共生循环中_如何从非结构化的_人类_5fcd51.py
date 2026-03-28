"""
模块名称: adaptive_feedback_processor
版本: 1.0.0
描述: 在人机共生循环中，从非结构化人类实践日志中提取负反馈信号，
      并将其固化为准新的'反直觉节点' (Counter-Intuitive Nodes)。

核心功能:
    1. 多模态输入解析
    2. 负反馈信号提取
    3. 反直觉节点生成与参数修正

依赖:
    - Python 3.9+
    - pydantic (用于数据验证)
    - loguru (用于日志记录，需安装)
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

# 尝试导入 pydantic，如果失败则使用基础类型模拟
try:
    from pydantic import BaseModel, Field, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # 简单的模拟基类，用于在没有pydantic时保持代码结构
    class BaseModel:
        def __init__(__pydantic_self__, **data):
            __pydantic_self__.__dict__.update(data)
        class Config:
            arbitrary_types_allowed = True

    def Field(*args, **kwargs):
        return None

    def ValidationError(*args):
        return ValueError(*args)

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Cognitive_Loop")


# --- 数据模型定义 ---

class ModalityType(str, Enum):
    """输入数据的模态类型"""
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    BIO_SIGNAL = "bio_signal"  # 如心率、皮电反应


class RawPracticeLog(BaseModel):
    """人类实践日志的非结构化输入"""
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    modality: ModalityType
    content: Union[str, bytes]  # 文本为str，音视频可以是base64或bytes
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackSignal(BaseModel):
    """提取出的反馈信号"""
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    source_log_id: str
    sentiment_score: float  # -1.0 (极度负面) 到 1.0 (极度正面)
    error_attribution: str  # 归因描述，如 "视觉遮挡"、"认知过载"
    intensity: float  # 信号强度 0.0 到 1.0
    context_snapshot: Dict[str, Any]  # 上下文快照


class CounterIntuitiveNode(BaseModel):
    """反直觉节点：存储修正后的认知模型参数"""
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    related_skill_node: str  # 关联的原有技能节点ID
    correction_vector: Dict[str, float]  # 参数修正向量
    heuristic_rule: str  # 提炼出的反直觉规则 (如: "在X情况下，Y不仅无用反而有害")
    creation_time: datetime = Field(default_factory=datetime.now)
    confidence: float = 0.0  # 节点的置信度


# --- 辅助函数 ---

def _validate_input_boundary(log: RawPracticeLog) -> bool:
    """
    辅助函数: 验证输入数据的边界和合法性。
    
    Args:
        log (RawPracticeLog): 原始日志对象。
        
    Returns:
        bool: 如果数据有效返回True，否则抛出ValueError。
        
    Raises:
        ValueError: 如果内容为空或模态不匹配。
    """
    if not log.content:
        logger.error(f"Log {log.log_id}: Content is empty.")
        raise ValueError("Content cannot be empty.")
    
    if isinstance(log.content, str) and len(log.content) < 5:
        logger.warning(f"Log {log.log_id}: Text content suspiciously short.")
        # 这里不抛出异常，仅警告，但在严格模式下可能需要处理
        
    # 模拟检查：如果是视频但内容是短字符串，视为无效
    if log.modality == ModalityType.VIDEO and isinstance(log.content, str) and len(log.content) < 100:
         logger.error(f"Log {log.log_id}: Video content implies binary data or long string, got short string.")
         raise ValueError("Invalid content for VIDEO modality.")
         
    return True


# --- 核心函数 ---

def extract_negative_signal(log: RawPracticeLog) -> Optional[FeedbackSignal]:
    """
    核心函数 1: 从原始日志中提取负反馈信号。
    
    此函数模拟了 NLP 和情感分析的过程。在生产环境中，这里会调用
    BERT/Electra 模型或语音情感识别 API。
    
    Args:
        log (RawPracticeLog): 非结构化的输入日志。
        
    Returns:
        Optional[FeedbackSignal]: 如果检测到显著负反馈，返回信号对象；否则返回None。
        
    Example:
        >>> log = RawPracticeLog(modality=ModalityType.TEXT, content="该死，我又忘了关门！")
        >>> signal = extract_negative_signal(log)
        >>> signal.sentiment_score < 0
        True
    """
    try:
        _validate_input_boundary(log)
    except ValueError as e:
        logger.warning(f"Validation failed for log {log.log_id}: {e}")
        return None

    logger.info(f"Processing log {log.log_id} for negative signals...")
    
    # 模拟：情感分析逻辑
    sentiment = 0.0
    attribution = "unknown"
    
    if log.modality == ModalityType.TEXT:
        # 简单的关键词匹配模拟复杂模型
        negative_keywords = ["失败", "错误", "该死", "不行", "糟糕", "忘了"]
        positive_keywords = ["成功", "很好", "顺利"]
        
        content_lower = str(log.content).lower()
        
        neg_count = sum(1 for k in negative_keywords if k in content_lower)
        pos_count = sum(1 for k in positive_keywords if k in content_lower)
        
        sentiment = (pos_count - neg_count) / (max(len(content_lower.split()), 1))
        
        # 归因提取 (模拟实体抽取)
        if "忘了" in content_lower:
            attribution = "memory_lapse"
        elif "遮挡" in content_lower:
            attribution = "visual_occlusion"
        elif "太快" in content_lower:
            attribution = "timing_constraint"
            
    elif log.modality == ModalityType.VIDEO:
        # 模拟：调用计算机视觉接口分析面部微表情
        # 假设 metadata 中包含预处理的关键帧分析结果
        if log.metadata.get("face_frown_detected"):
            sentiment = -0.8
            attribution = "emotional_distress"
    
    # 边界检查：情感得分必须在 [-1, 1]
    sentiment = max(-1.0, min(1.0, sentiment))
    
    # 只有当情感得分为负且显著时才返回信号
    if sentiment < -0.1:
        intensity = abs(sentiment)
        logger.info(f"Negative signal detected! Score: {sentiment}, Attribution: {attribution}")
        return FeedbackSignal(
            source_log_id=log.log_id,
            sentiment_score=sentiment,
            error_attribution=attribution,
            intensity=intensity,
            context_snapshot=log.metadata
        )
    
    return None


def solidify_to_counter_intuitive_node(
    signal: FeedbackSignal, 
    target_skill_id: str,
    existing_graph: Optional[Dict[str, Any]] = None
) -> CounterIntuitiveNode:
    """
    核心函数 2: 将负反馈信号固化为反直觉节点。
    
    该函数不仅仅记录错误，而是试图修改底层参数。它将“失败”转化为“修正向量”。
    
    Args:
        signal (FeedbackSignal): 提取出的负反馈信号。
        target_skill_id (str): 需要修正的目标技能节点ID。
        existing_graph (Optional[Dict]): 当前的知识图谱上下文，用于上下文感知修正。
        
    Returns:
        CounterIntuitiveNode: 包含修正参数的新节点。
        
    Raises:
        ValueError: 如果信号强度不足以支持固化。
    """
    if signal.intensity < 0.2:
        logger.warning(f"Signal intensity too low ({signal.intensity}), not solidifying.")
        raise ValueError("Signal too weak for solidification.")

    logger.info(f"Solidifying signal {signal.signal_id} into CIN for skill {target_skill_id}...")
    
    # 初始化修正向量
    correction_vector = {
        "weight_penalty": 0.0,
        "bias_adjustment": 0.0,
        "constraint_added": False
    }
    
    # 核心逻辑：根据归因生成修正参数
    # 这部分是 AGI 的“学习”过程，将自然语言/信号归因映射到数学参数
    if signal.error_attribution == "memory_lapse":
        correction_vector["weight_penalty"] = -0.5  # 降低依赖该路径的权重
        correction_vector["bias_adjustment"] = 0.2  # 增加随机检查的偏置
        heuristic = "在执行关键步骤前，必须增加显式确认环节，防止记忆缺失。"
        
    elif signal.error_attribution == "timing_constraint":
        correction_vector["weight_penalty"] = -0.3
        correction_vector["constraint_added"] = True
        heuristic = "该技能节点在高频操作下不可靠，需引入缓冲时间。"
        
    elif signal.error_attribution == "visual_occlusion":
        correction_vector["weight_penalty"] = -0.8  # 视觉受阻时，该节点几乎无效
        heuristic = "当视觉输入置信度低时，禁止执行此动作，切换为触觉反馈模式。"
        
    else:
        correction_vector["weight_penalty"] = -0.1 * signal.intensity
        heuristic = f"通用降权规则。原始归因: {signal.error_attribution}"

    # 生成反直觉节点
    node = CounterIntuitiveNode(
        related_skill_node=target_skill_id,
        correction_vector=correction_vector,
        heuristic_rule=heuristic,
        confidence=signal.intensity * 0.8  # 初始置信度基于信号强度
    )
    
    logger.success(f"Created CIN Node {node.node_id} with heuristic: {heuristic}")
    return node


# --- 使用示例与主逻辑 ---

def run_symbiosis_cycle(raw_data: Dict[str, Any], skill_id: str):
    """
    运行一次完整的人机共生循环处理。
    """
    try:
        # 1. 数据封装
        log_entry = RawPracticeLog(**raw_data)
        
        # 2. 提取信号
        feedback_signal = extract_negative_signal(log_entry)
        
        if feedback_signal:
            # 3. 固化节点
            new_node = solidify_to_counter_intuitive_node(feedback_signal, skill_id)
            
            # 打印结果 (模拟存入数据库)
            print("-" * 30)
            print(f"NEW CIN GENERATED: {new_node.node_id}")
            print(f"Heuristic: {new_node.heuristic_rule}")
            print(f"Corrections: {json.dumps(new_node.correction_vector, indent=2)}")
            print("-" * 30)
            return new_node
        else:
            print("No significant negative feedback detected.")
            return None
            
    except ValidationError as e:
        logger.error(f"Data validation error: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error in symbiosis cycle: {e}", exc_info=True)

if __name__ == "__main__":
    # 模拟输入数据：人类在执行任务时的挫败感语音转文字
    sample_input = {
        "modality": ModalityType.TEXT,
        "content": "哎呀，我又忘了检查安全阀！这太糟糕了，每次匆忙的时候都会出错。",
        "metadata": {
            "speaker_id": "human_01",
            "task_context": "maintenance_routine_v2"
        }
    }
    
    # 运行循环
    run_symbiosis_cycle(sample_input, skill_id="safety_check_protocol_v1")