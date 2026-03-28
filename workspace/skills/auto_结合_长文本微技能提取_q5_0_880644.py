"""
高级技能模块: auto_结合_长文本微技能提取_q5_0_880644
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from uuid import uuid4

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class KnowledgeCrystal:
    """
    知识晶体数据结构。
    代表经过提取、标准化和压缩后的高密度知识节点。
    """
    node_id: str
    skill_name: str
    counter_intuitive_facts: List[str]
    standardized_steps: List[str]
    source_metadata: Dict[str, str]
    creation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    density_score: float = 0.0  # 知识密度评分 (0.0 - 1.0)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

@dataclass
class RawInput:
    """
    原始输入数据结构。
    """
    content: str
    source_type: str  # e.g., 'audio_transcript', 'legacy_code', 'manual_log'
    context_tags: List[str]

# --- 辅助函数 ---

def _validate_input_data(raw_data: RawInput) -> bool:
    """
    辅助函数：验证输入数据的完整性和合法性。
    
    Args:
        raw_data (RawInput): 原始输入数据对象。
        
    Returns:
        bool: 如果数据有效返回True，否则抛出ValueError。
        
    Raises:
        ValueError: 当内容为空或类型不支持时。
    """
    if not raw_data.content or not raw_data.content.strip():
        logger.error("输入内容为空，无法提取技能。")
        raise ValueError("Content cannot be empty.")
    
    supported_types = ['audio_transcript', 'legacy_code', 'manual_log', 'unstructured_text']
    if raw_data.source_type not in supported_types:
        logger.warning(f"非标准来源类型: {raw_data.source_type}，尝试通用处理模式。")
    
    logger.debug(f"输入数据验证通过: {raw_data.source_type}, 长度: {len(raw_data.content)}")
    return True

def _calculate_density_score(facts_count: int, steps_count: int) -> float:
    """
    辅助函数：计算知识晶体的密度分值。
    密度基于有效信息的数量和结构化程度。
    
    Args:
        facts_count (int): 提取出的反直觉事实数量。
        steps_count (int): 标准化步骤数量。
        
    Returns:
        float: 0.0到1.0之间的密度评分。
    """
    score = 0.0
    # 基础分值计算
    score += min(facts_count * 0.1, 0.4)  # 反直觉事实权重
    score += min(steps_count * 0.1, 0.4)  # 标准化步骤权重
    if facts_count > 0 and steps_count > 0:
        score += 0.2  # 完整性奖励
    return round(min(score, 1.0), 2)

# --- 核心函数 ---

def extract_micro_skills_q5(raw_text: str, source_type: str) -> Dict[str, Any]:
    """
    核心函数 Q5_0: 长文本微技能提取。
    从混乱的非结构化文本中识别关键模式和隐性知识。
    
    Args:
        raw_text (str): 原始长文本。
        source_type (str): 数据来源类型，用于调整提取策略。
        
    Returns:
        Dict[str, Any]: 包含提取出的原始微技能列表和上下文关键词。
        
    Example:
        >>> text = "老李说这机器要是停了，千万别马上重启，得等三分钟让电容放电，不然容易烧板子..."
        >>> result = extract_micro_skills_q5(text, "audio_transcript")
    """
    logger.info(f"开始执行微技能提取 (Q5_0)，源类型: {source_type}")
    
    # 模拟NLP处理逻辑：关键词提取和模式匹配
    # 在实际AGI系统中，这里会调用LLM或NLP模型
    extracted_skills = []
    
    # 1. 识别因果链条 (模拟)
    # 规则：寻找 "如果...那么...", "千万别...", "必须..." 等模式
    causal_patterns = [
        r"如果(.*?)就(.*?)。",
        r"千万别(.*?)，不然(.*?)。",
        r"必须(.*?)才能(.*?)。"
    ]
    
    temp_skills = []
    for pattern in causal_patterns:
        matches = re.findall(pattern, raw_text)
        for match in matches:
            temp_skills.append(f"条件: {match[0].strip()} -> 动作/结果: {match[1].strip()}")

    # 2. 识别反直觉结论 (模拟)
    # 通常包含否定词或与常识相反的陈述
    counter_intuitive = []
    if "不要" in raw_text or "别" in raw_text:
        # 简单的模拟逻辑：提取包含否定词的句子
        sentences = raw_text.replace('!', '.').replace('!', '.').split('.')
        for sent in sentences:
            if "别" in sent or "不要" in sent:
                counter_intuitive.append(sent.strip())

    logger.info(f"提取完成，发现 {len(temp_skills)} 个潜在微技能，{len(counter_intuitive)} 个反直觉点。")
    
    return {
        "raw_micro_skills": temp_skills,
        "counter_intuitive_hints": counter_intuitive,
        "keywords": list(set(re.findall(r'[\u4e00-\u9fa5]{2,4}', raw_text))) # 简单提取中文关键词
    }

def standardize_and_crystallize(extracted_data: Dict, source_meta: Dict) -> KnowledgeCrystal:
    """
    核心函数 E1_9115 & Q6_2: 工业经验标准化与认知图谱压缩。
    将提取的原始技能转换为标准格式，并压缩为知识晶体。
    
    Args:
        extracted_data (Dict): extract_micro_skills_q5 的输出结果。
        source_meta (Dict): 来源元数据。
        
    Returns:
        KnowledgeCrystal: 固化后的知识晶体对象。
    """
    logger.info("开始执行标准化 (E1_9115) 与压缩 (Q6_2)...")
    
    raw_skills = extracted_data.get("raw_micro_skills", [])
    raw_hints = extracted_data.get("counter_intuitive_hints", [])
    
    # 1. 标准化处理 (E1_9115)
    # 将自然语言转换为 If-Then 规则或步骤流
    standardized_steps = []
    for skill in raw_skills:
        # 模拟标准化清洗
        std_step = skill.replace("条件:", "IF").replace("动作/结果:", "THEN")
        standardized_steps.append(std_step)
    
    # 2. 认知图谱压缩 (Q6_2)
    # 合并相似项，去除冗余，生成高密度摘要
    # 这里模拟生成一个唯一的晶体ID
    crystal_id = f"CRYSTAL-{uuid4().hex[:8].upper()}"
    
    # 提取晶体名称 (简单的启发式方法)
    skill_name = f"Skill_{extracted_data.get('keywords', ['Unknown'])[0]}"
    
    # 计算密度
    density = _calculate_density_score(len(raw_hints), len(standardized_steps))
    
    crystal = KnowledgeCrystal(
        node_id=crystal_id,
        skill_name=skill_name,
        counter_intuitive_facts=raw_hints,
        standardized_steps=standardized_steps,
        source_metadata=source_meta,
        density_score=density
    )
    
    logger.info(f"知识晶体生成成功: ID {crystal_id}, 密度 {density}")
    return crystal

# --- 主类封装 ---

class SkillExtractorOrchestrator:
    """
    AGI技能提取编排器。
    整合长文本微技能提取、标准化与图谱压缩流程。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config if config else {}
        logger.info("SkillExtractorOrchestrator 初始化完成。")

    def process_unstructured_data(self, raw_data: RawInput) -> Optional[KnowledgeCrystal]:
        """
        执行完整的提取与固化流程。
        
        Args:
            raw_data (RawInput): 包含内容和元数据的输入对象。
            
        Returns:
            Optional[KnowledgeCrystal]: 处理成功返回知识晶体，失败返回None。
        """
        try:
            # 1. 数据验证
            _validate_input_data(raw_data)
            
            # 2. Q5_0: 提取
            extracted_info = extract_micro_skills_q5(
                raw_data.content, 
                raw_data.source_type
            )
            
            if not extracted_info["raw_micro_skills"] and not extracted_info["counter_intuitive_hints"]:
                logger.warning("未能提取到有效技能，流程终止。")
                return None
                
            # 3. E1_9115 & Q6_2: 标准化与压缩
            source_meta = {
                "type": raw_data.source_type,
                "tags": raw_data.context_tags,
                "timestamp": datetime.now().isoformat()
            }
            
            crystal = standardize_and_crystallize(extracted_info, source_meta)
            
            # 4. 模拟插入图谱 (实际应用中会调用图数据库API)
            self._insert_into_graph(crystal)
            
            return crystal

        except ValueError as ve:
            logger.error(f"数据验证失败: {ve}")
            return None
        except Exception as e:
            logger.critical(f"处理过程中发生未预期错误: {e}", exc_info=True)
            return None

    def _insert_into_graph(self, crystal: KnowledgeCrystal):
        """
        [Mock] 将知识晶体插入AGI认知图谱。
        """
        logger.info(f"[GraphDB Mock] 插入节点: {crystal.node_id} - {crystal.skill_name}")
        # 实际代码此处可能是 Neo4j 或 NetworkX 的操作
        pass

# --- 使用示例 ---

if __name__ == "__main__":
    # 模拟老师傅的录音转录文本 (非结构化数据)
    sample_transcript = """
    这台液压机操作有个窍门。每天早上开机的时候，千万别直接按启动钮。
    如果你直接启动，油路里的气排不干净，一会儿压力就稳不住。
    正确的做法是，先把阀门拧松两圈，听不到嘶嘶声了，再拧紧。
    还有，要是听见响声特别大，赶紧停机，那是缺油了，千万别硬撑。
    """
    
    # 准备输入数据
    input_data = RawInput(
        content=sample_transcript,
        source_type="audio_transcript",
        context_tags=["manufacturing", "hydraulics", "safety"]
    )
    
    # 初始化编排器
    orchestrator = SkillExtractorOrchestrator()
    
    # 执行处理
    result_crystal = orchestrator.process_unstructured_data(input_data)
    
    # 输出结果
    if result_crystal:
        print("\n=== 知识晶体生成结果 ===")
        print(result_crystal.to_json())
    else:
        print("\n处理失败，未生成知识晶体。")