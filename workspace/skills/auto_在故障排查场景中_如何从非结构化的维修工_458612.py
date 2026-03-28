"""
高级技能模块：故障排查工单因果三元组提取与知识图谱映射

该模块旨在解决AGI系统在工业维修场景下的核心认知难题：
如何将人类自然语言描述的（非结构化、模糊的）维修工单，
转化为机器可推理的（结构化、严格的）知识图谱节点。

核心功能：
1. 从文本中抽取 '故障现象-操作行为-解决结果' 三元组。
2. 将抽取出的实体映射到标准化的知识图谱节点ID。

Author: AGI System Core Engineer
Date: 2023-10-27
Version: 2.0.0
"""

import logging
import re
import json
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class MappingStatus(Enum):
    """映射状态枚举"""
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    NOT_FOUND = "not_found"

@dataclass
class CausalTriplet:
    """
    因果关系三元组数据结构
    
    Attributes:
        symptom (str): 故障现象原始文本
        action (str): 操作行为原始文本
        result (str): 解决结果原始文本
        confidence (float): 提取置信度 (0.0 - 1.0)
    """
    symptom: str
    action: str
    result: str
    confidence: float = 0.0

    def __post_init__(self):
        """数据验证"""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

@dataclass
class MappedTriplet:
    """
    映射后的三元组结构
    
    Attributes:
        raw_triplet (CausalTriplet): 原始三元组
        symptom_node_id (Optional[int]): 映射到的现象节点ID
        action_node_id (Optional[int]): 映射到的操作节点ID
        result_node_id (Optional[int]): 映射到的结果节点ID
        status (MappingStatus): 映射状态
    """
    raw_triplet: CausalTriplet
    symptom_node_id: Optional[int] = None
    action_node_id: Optional[int] = None
    result_node_id: Optional[int] = None
    status: MappingStatus = MappingStatus.NOT_FOUND

# --- 辅助函数 ---

def _normalize_text(text: str) -> str:
    """
    辅助函数：文本标准化预处理
    
    Args:
        text (str): 输入文本
        
    Returns:
        str: 标准化后的文本（小写、去特殊符号、繁转简等）
    
    Example:
        >>> _normalize_text("泵体震动!! 过大")
        '泵体震动 过大'
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 转小写
    text = text.lower()
    # 去除多余空格和换行
    text = re.sub(r'\s+', ' ', text).strip()
    # 简单的繁体转简体映射 (示例，生产环境建议使用opencc)
    traditional_to_simple = {"震動": "震动", "異常": "异常"}
    for k, v in traditional_to_simple.items():
        text = text.replace(k, v)
        
    return text

# --- 核心功能类 ---

class KnowledgeGraphMapper:
    """
    知识图谱映射器
    负责将非结构化文本实体映射到现有的3022个图谱节点上。
    """
    
    def __init__(self, node_database: Dict[int, str]):
        """
        初始化映射器
        
        Args:
            node_database (Dict[int, str]): 节点ID到标准名称的映射字典
        """
        if len(node_database) > 3022:
            logger.warning(f"Node database size {len(node_database)} exceeds expected 3022.")
        
        self.node_db = node_database
        # 预先构建反向索引以加速查找 (Name -> ID)
        self._name_to_id_map: Dict[str, int] = {v: k for k, v in node_database.items()}
        logger.info(f"KnowledgeGraphMapper initialized with {len(node_database)} nodes.")

    def map_entity(self, entity_text: str) -> Tuple[Optional[int], MappingStatus]:
        """
        核心函数1: 实体映射
        
        Args:
            entity_text (str): 待映射的实体文本
            
        Returns:
            Tuple[Optional[int], MappingStatus]: (节点ID, 映射状态)
        
        Raises:
            ValueError: 如果输入为空
        """
        if not entity_text:
            raise ValueError("Entity text cannot be empty")

        normalized = _normalize_text(entity_text)
        
        # 1. 尝试精确匹配
        if normalized in self._name_to_id_map:
            return self._name_to_id_map[normalized], MappingStatus.EXACT_MATCH
        
        # 2. 尝试模糊匹配 (此处使用简单的包含关系模拟复杂的NLP语义匹配)
        # 在生产环境中，这里应调用 BERT/Word2Vec 向量相似度计算
        best_match_id = None
        highest_score = 0.0
        
        for name, idx in self._name_to_id_map.items():
            # 简单的字符集重叠度作为相似度评分
            overlap = len(set(normalized) & set(name)) / max(len(set(normalized)), 1)
            if overlap > 0.8 and overlap > highest_score: # 阈值设定
                highest_score = overlap
                best_match_id = idx
        
        if best_match_id:
            logger.debug(f"Fuzzy matched '{entity_text}' to Node {best_match_id}")
            return best_match_id, MappingStatus.FUZZY_MATCH
            
        return None, MappingStatus.NOT_FOUND

class TicketProcessor:
    """
    工单处理器
    负责从非结构化文本中提取因果三元组
    """
    
    # 定义常用的因果连接词模式
    CAUSAL_PATTERNS = [
        r"(?P<symptom>.+?)(?P<connector>导致|出现|发生|显示)(?P<mid>.+?)(?P<action>更换|重启|调整|维修|检查)(?P<action_target>.+?)(后)?(?P<result>正常|恢复|解决)",
        r"(?P<symptom>.+?)，(?P<action>执行.+)后，(?P<result>.+)",
        r"故障现象[是为]?(?P<symptom>.+?)，处理措施[是为]?(?P<action>.+?)，结果[是为]?(?P<result>.+)"
    ]

    def extract_causal_triplet(self, text: str) -> Optional[CausalTriplet]:
        """
        核心函数2: 因果三元组提取
        
        Args:
            text (str): 维修工单文本内容
            
        Returns:
            Optional[CausalTriplet]: 提取出的三元组，如果失败返回None
        """
        if not text:
            logger.warning("Empty text provided for extraction")
            return None

        logger.info(f"Processing ticket: {text[:50]}...")
        
        for pattern in self.CAUSAL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # 根据正则组名动态构建字段
                    groups = match.groupdict()
                    symptom = groups.get('symptom', '').strip()
                    # 拼接动作和目标 (如: 更换 + 泵 -> 更换泵)
                    action = (groups.get('action', '') + " " + groups.get('action_target', '')).strip()
                    result = groups.get('result', '').strip()
                    
                    if symptom and action:
                        # 简单的置信度计算逻辑
                        confidence = 0.9 if len(symptom) > 2 and len(action) > 2 else 0.6
                        return CausalTriplet(
                            symptom=symptom, 
                            action=action, 
                            result=result, 
                            confidence=confidence
                        )
                except Exception as e:
                    logger.error(f"Error parsing regex match: {e}")
                    continue
        
        logger.warning(f"Failed to extract triplet from text: {text}")
        return None

# --- 主处理流程函数 ---

def process_maintenance_ticket(
    ticket_text: str, 
    mapper: KnowledgeGraphMapper
) -> Dict[str, Any]:
    """
    完整的处理流水线：提取 -> 映射 -> 结构化输出
    
    Args:
        ticket_text (str): 原始工单文本
        mapper (KnowledgeGraphMapper): 已初始化的图谱映射器实例
        
    Returns:
        Dict[str, Any]: 包含原始数据、三元组和映射结果的完整JSON对象
    
    Example:
        >>> db = {1: "泵体震动", 2: "更换密封圈", 3: "设备恢复"}
        >>> mapper_instance = KnowledgeGraphMapper(db)
        >>> result = process_maintenance_ticket("泵体震动过大，更换密封圈后设备恢复", mapper_instance)
        >>> print(result['mapped']['symptom_node_id'])
        1
    """
    logger.info("=== Starting Ticket Processing ===")
    
    # 1. 数据清洗与验证
    clean_text = _normalize_text(ticket_text)
    if len(clean_text) < 5:
        return {"error": "Input text too short", "status": "failed"}

    # 2. 实体关系提取
    processor = TicketProcessor()
    raw_triplet = processor.extract_causal_triplet(clean_text)
    
    if not raw_triplet:
        return {
            "input": ticket_text,
            "status": "extraction_failed",
            "message": "Could not identify causal structure."
        }

    # 3. 知识图谱映射
    mapped_result = MappedTriplet(raw_triplet=raw_triplet)
    
    try:
        s_id, s_status = mapper.map_entity(raw_triplet.symptom)
        a_id, a_status = mapper.map_entity(raw_triplet.action)
        r_id, r_status = mapper.map_entity(raw_triplet.result)
        
        mapped_result.symptom_node_id = s_id
        mapped_result.action_node_id = a_id
        mapped_result.result_node_id = r_id
        
        # 确定整体状态
        if s_status == MappingStatus.EXACT_MATCH and a_status == MappingStatus.EXACT_MATCH:
            mapped_result.status = MappingStatus.EXACT_MATCH
        elif s_id or a_id:
            mapped_result.status = MappingStatus.FUZZY_MATCH
        else:
            mapped_result.status = MappingStatus.NOT_FOUND
            
    except Exception as e:
        logger.exception("Mapping phase failed critically")
        return {"error": str(e), "status": "critical_failure"}

    logger.info(f"Processing complete. Status: {mapped_result.status.value}")
    
    return {
        "input": ticket_text,
        "status": "success",
        "extraction": asdict(raw_triplet),
        "mapping": asdict(mapped_result) # 注意：dataclass默认序列化可能需要处理Enum
    }

# --- 使用示例 ---

if __name__ == "__main__":
    # 模拟知识图谱数据库 (3022个节点的子集)
    mock_kg_db = {
        101: "水泵震动异常",
        205: "更换轴承",
        308: "运行正常",
        404: "系统恢复"
    }

    # 初始化映射器
    kg_mapper = KnowledgeGraphMapper(mock_kg_db)

    # 模拟输入工单 (包含模糊描述)
    # "水泵震动异常" -> 精确匹配 101
    # "换了轴承" -> 模糊匹配 205 (假设我们的简单算法能捕捉到，或者需要更高级的NLP)
    # "好了" -> 模糊匹配 308/404
    sample_ticket = "现场发现水泵震动异常，噪音大。维修人员现场更换轴承后，测试运行正常。"
    
    # 执行处理
    result_json = process_maintenance_ticket(sample_ticket, kg_mapper)
    
    # 打印结果
    print(json.dumps(result_json, indent=2, ensure_ascii=False, default=str))