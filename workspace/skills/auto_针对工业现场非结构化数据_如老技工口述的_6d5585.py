"""
SKILL: Industrial Unstructured Data Semantic Parser
这是一个针对工业现场非结构化数据（如老技工口述经验）的语义解析器。
该模块旨在将模糊的自然语言描述转化为结构化的、具有逻辑拓扑的“认知网络节点”，
而非简单的文本Embedding。
"""

import logging
import re
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialSemanticParser")


class NodeCategory(Enum):
    """认知网络节点的分类枚举"""
    ACOUSTIC_SIGNAL = "acoustic_signal"  # 声学信号特征
    OPERATIONAL_PARAM = "operational_param"  # 运行参数
    FAULT_PATTERN = "fault_pattern"  # 故障模式
    ACTION_DIRECTIVE = "action_directive"  # 操作指令
    CONTEXTUAL_CONDITION = "contextual_condition"  # 环境条件


@dataclass
class CognitiveNode:
    """
    认知网络节点数据结构
    代表了一个从非结构化文本中提取出的明确知识单元
    """
    node_id: str
    name: str
    category: NodeCategory
    logical_topology: Dict[str, Any]  # 存储逻辑拓扑，如阈值、判断条件
    original_text: str  # 原始文本溯源
    confidence: float  # 解析置信度
    connections: List[str]  # 关联的其他节点ID

    def to_json(self) -> str:
        """将节点转换为JSON字符串"""
        node_dict = asdict(self)
        node_dict['category'] = self.category.value
        return json.dumps(node_dict, ensure_ascii=False, indent=2)


class DataValidationError(Exception):
    """自定义数据验证错误"""
    pass


def _preprocess_text(raw_text: str) -> str:
    """
    [辅助函数] 文本预处理
    清洗工业现场常见的口语化表达，去除无意义停顿词，标准化标点。
    
    Args:
        raw_text (str): 原始输入文本
        
    Returns:
        str: 清洗后的标准化文本
    """
    if not raw_text:
        return ""
    
    # 去除常见口语填充词
    fillers = ['嗯', '啊', '那个', '然后', '就是', '大概', '可能']
    processed_text = raw_text
    for filler in fillers:
        processed_text = processed_text.replace(filler, '')
    
    # 标准化标点符号
    processed_text = re.sub(r'[，。；！？、]', ' ', processed_text)
    processed_text = re.sub(r'\s+', ' ', processed_text).strip()
    
    logger.debug(f"Preprocessed text: {processed_text}")
    return processed_text


def extract_fuzzy_parameters(text_segment: str) -> Dict[str, Any]:
    """
    [核心函数 1] 模糊参数提取与边界映射
    将模糊的语义（如"声音尖尖的"、"温度很高"）映射为可执行的数据结构。
    这里使用了基于规则的映射，在实际AGI场景中可接入LLM或小样本模型。
    
    Args:
        text_segment (str): 包含特定现象描述的文本片段
        
    Returns:
        Dict[str, Any]: 包含参数名、模糊集类型和推断边界的字典
        
    Raises:
        DataValidationError: 如果无法解析关键参数
    """
    logger.info(f"Extracting parameters from: {text_segment}")
    param_mapping = {
        "pattern": None,
        "fuzzy_set": None,
        "inferred_range": None
    }

    # 规则库：模拟专家系统的知识映射
    # 实际应用中这里应该是一个知识图谱查询或向量检索过程
    if "尖尖的" in text_segment or "刺耳" in text_segment:
        param_mapping["pattern"] = "high_frequency_peak"
        param_mapping["fuzzy_set"] = "HIGH"
        param_mapping["inferred_range"] = {"min_hz": 2000, "max_hz": 20000, "unit": "Hz"}
    elif "沉闷" in text_segment or "咚咚" in text_segment:
        param_mapping["pattern"] = "low_frequency_impact"
        param_mapping["fuzzy_set"] = "MEDIUM_LOW"
        param_mapping["inferred_range"] = {"min_hz": 20, "max_hz": 400, "unit": "Hz"}
    elif "温度高" in text_segment or "烫手" in text_segment:
        param_mapping["pattern"] = "overheat_warning"
        param_mapping["fuzzy_set"] = "CRITICAL"
        param_mapping["inferred_range"] = {"min_c": 60, "max_c": 150, "unit": "Celsius"}
    else:
        logger.warning(f"No specific fuzzy rule matched for: {text_segment}")
        param_mapping["pattern"] = "unknown_anomaly"
        param_mapping["fuzzy_set"] = "UNKNOWN"
        param_mapping["inferred_range"] = {}

    # 边界检查
    if not param_mapping["pattern"]:
        raise DataValidationError(f"Failed to extract valid pattern from: {text_segment}")

    return param_mapping


def build_cognitive_node(
    raw_input: str, 
    expert_id: str, 
    context_tags: List[str]
) -> Optional[CognitiveNode]:
    """
    [核心函数 2] 构建认知网络节点
    整合预处理和参数提取，生成一个包含逻辑拓扑的节点对象。
    
    输入格式说明:
        raw_input: 类似 "听到轴承那边有尖尖的声音，可能是缺油了"
    
    输出格式说明:
        CognitiveNode对象，包含可执行的逻辑结构。
    
    Args:
        raw_input (str): 原始的非结构化输入
        expert_id (str): 提供信息的专家ID，用于溯源
        context_tags (List[str]): 上下文标签，如 ["CNC", "Spindle", "Bearing"]
        
    Returns:
        Optional[CognitiveNode]: 构建完成的节点，如果失败则返回None
    """
    try:
        # 1. 数据清洗
        clean_text = _preprocess_text(raw_input)
        if len(clean_text) < 5:
            raise DataValidationError("Input text too short after preprocessing")

        # 2. 语义解析与参数提取
        # 这里简化了从整句中提取关键片段的过程
        extracted_params = extract_fuzzy_parameters(clean_text)
        
        # 3. 确定节点分类
        if "声音" in clean_text or "听" in clean_text:
            category = NodeCategory.ACOUSTIC_SIGNAL
        elif "缺油" in clean_text or "磨损" in clean_text:
            category = NodeCategory.FAULT_PATTERN
        else:
            category = NodeCategory.OPERATIONAL_PARAM

        # 4. 构建逻辑拓扑
        # 这是一个简化的拓扑结构，描述了 IF-THEN 逻辑
        logical_topology = {
            "trigger_condition": {
                "param": extracted_params["pattern"],
                "fuzzy_logic": extracted_params["fuzzy_set"],
                "value_boundary": extracted_params["inferred_range"]
            },
            "hypothesis": "Lack of lubrication" if "缺油" in clean_text else "Mechanical wear",
            "weight": 0.85  # 初始置信度权重
        }

        # 5. 生成节点ID
        import hashlib
        node_hash = hashlib.md5(f"{clean_text}{expert_id}".encode()).hexdigest()[:8]
        node_id = f"COG_{category.value.upper()}_{node_hash}"

        # 6. 数据封装
        node = CognitiveNode(
            node_id=node_id,
            name=f"Expert Knowledge: {clean_text[:20]}...",
            category=category,
            logical_topology=logical_topology,
            original_text=raw_input,
            confidence=0.75,  # 初始置信度，后续可根据反馈调整
            connections=context_tags  # 初始连接为上下文标签
        )

        logger.info(f"Successfully built cognitive node: {node_id}")
        return node

    except DataValidationError as e:
        logger.error(f"Validation Error: {e}")
        return None
    except Exception as e:
        logger.critical(f"Unexpected error building node: {e}", exc_info=True)
        return None

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟老技工的口述数据
    expert_transcript_1 = "嗯...在主轴那边，听到有尖尖的声音，滋滋的那种，大概是轴承缺油了。"
    expert_transcript_2 = "如果机器底部有咚咚的沉闷敲击声，可能是地脚螺栓松动了。"

    print(f"{'='*10} Industrial Cognitive Node Parser {'='*10}")

    # 示例 1: 处理高频噪声描述
    node_1 = build_cognitive_node(
        raw_input=expert_transcript_1,
        expert_id="TECH_MASTER_001",
        context_tags=["Machine_Tool", "Spindle", "Maintenance"]
    )

    if node_1:
        print("\nGenerated Node 1 (JSON):")
        print(node_1.to_json())
        
    # 示例 2: 处理低频冲击描述
    node_2 = build_cognitive_node(
        raw_input=expert_transcript_2,
        expert_id="TECH_MASTER_002",
        context_tags=["Foundation", "Vibration"]
    )
    
    if node_2:
        print("\nGenerated Node 2 (JSON):")
        print(node_2.to_json())
        
    # 示例 3: 边界测试 - 无效输入
    node_3 = build_cognitive_node(
        raw_input="啊，那个，嗯",
        expert_id="TEST",
        context_tags=[]
    )
    if node_3 is None:
        print("\nSuccessfully handled invalid input (Node creation skipped).")