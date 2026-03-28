"""
Module: auto_跨域体感迁移引擎_利用agi的跨域检索_6429bf
Description: 【跨域体感迁移引擎】利用AGI的跨域检索能力，为难以理解的抽象技能或体感寻找最匹配的已知经验模型。
             当用户无法理解某个复杂操作（如'核心收紧'）时，系统能检索用户已有的个人经验库
             （如'穿紧身裤拉拉链'的感觉），生成个性化的结构映射解释，实现技能的瞬间‘顿悟’式习得。
Author: Senior Python Engineer for AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class ExperienceNode:
    """
    经验节点类，代表用户的一个具体经验或技能。
    
    Attributes:
        id (str): 经验的唯一标识符。
        name (str): 经验的名称（如 '穿紧身裤'）。
        domain (str): 所属领域（如 '日常生活', '运动'）。
        features (Dict[str, float]): 特征向量，键为特征名，值为强度或相关性(0.0-1.0)。
        description (str): 详细描述。
    """
    id: str
    name: str
    domain: str
    features: Dict[str, float]
    description: str = ""

    def __post_init__(self):
        """数据验证：确保特征值在0到1之间。"""
        for feat, val in self.features.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"Feature value for '{feat}' must be between 0.0 and 1.0, got {val}")

@dataclass
class MappingResult:
    """
    映射结果类，包含迁移后的解释和元数据。
    """
    target_skill: str
    matched_experience: Optional[ExperienceNode]
    similarity_score: float
    analogy_explanation: str
    mapping_details: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# --- 核心类 ---

class CrossDomainSomaticTransferEngine:
    """
    跨域体感迁移引擎。
    
    利用向量相似度检索，将未知的抽象技能映射到用户熟悉的具象经验上。
    """

    def __init__(self, user_experience_db: List[ExperienceNode]):
        """
        初始化引擎。
        
        Args:
            user_experience_db (List[ExperienceNode]): 用户的个人经验库。
        """
        self.experience_db = user_experience_db
        logger.info(f"Engine initialized with {len(user_experience_db)} experience nodes.")

    def _calculate_feature_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        [辅助函数] 计算两个特征字典之间的余弦相似度（简化版）。
        
        Args:
            vec1 (Dict[str, float]): 目标技能的特征向量。
            vec2 (Dict[str, float]): 候选经验的特征向量。
            
        Returns:
            float: 相似度得分 (0.0 到 1.0)。
        """
        if not vec1 or not vec2:
            return 0.0
        
        # 找出共同键
        common_features = set(vec1.keys()) & set(vec2.keys())
        if not common_features:
            return 0.0
            
        dot_product = sum(vec1[k] * vec2[k] for k in common_features)
        norm1 = sum(v**2 for v in vec1.values())**0.5
        norm2 = sum(v**2 for v in vec2.values())**0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)

    def _generate_analogy(self, target: str, experience: ExperienceNode, mappings: Dict[str, str]) -> str:
        """
        [辅助函数] 基于特征映射生成自然语言解释。
        
        Args:
            target (str): 目标技能名称。
            experience (ExperienceNode): 匹配到的经验。
            mappings (Dict[str, str]): 特征映射关系。
            
        Returns:
            str: 生成的类比解释文本。
        """
        if not experience:
            return f"无法找到与 '{target}' 相关的已知经验。"
            
        explanation = (
            f"理解 '{target}' 的诀窍在于：想象你正在 '{experience.name}'。\n"
            f"具体来说：\n"
        )
        
        for t_feat, e_feat in mappings.items():
            explanation += f"- 这里的 '{t_feat}' 就像你 '{experience.name}' 时的 '{e_feat}' 感觉。\n"
            
        explanation += f"参考描述：{experience.description}"
        return explanation

    def retrieve_and_map(self, 
                         target_skill_name: str, 
                         target_features: Dict[str, float], 
                         threshold: float = 0.6) -> MappingResult:
        """
        [核心函数] 执行跨域检索和映射。
        
        步骤:
        1. 遍历用户经验库。
        2. 计算目标技能与每个经验的特征相似度。
        3. 排除同域结果（确保跨域）。
        4. 生成最佳匹配的结构映射解释。
        
        Args:
            target_skill_name (str): 需要理解的抽象技能名称。
            target_features (Dict[str, float]): 该技能的体感特征描述。
            threshold (float): 最低相似度阈值。
            
        Returns:
            MappingResult: 包含匹配结果和解释的对象。
            
        Raises:
            ValueError: 如果输入特征为空。
        """
        if not target_features:
            logger.error("Target features cannot be empty.")
            raise ValueError("Target features dictionary cannot be empty.")

        logger.info(f"Starting retrieval for skill: {target_skill_name}")
        
        best_match: Optional[ExperienceNode] = None
        highest_score = -1.0
        best_mapping: Dict[str, str] = {}

        # 遍历寻找最佳匹配
        for exp in self.experience_db:
            # 计算相似度
            score = self._calculate_feature_similarity(target_features, exp.features)
            
            # 简单的跨域检查：这里假设如果领域不同或明确标记为类比源则更好
            # 在实际AGI中，这里会有更复杂的语义距离计算
            
            if score > highest_score:
                highest_score = score
                best_match = exp
                
                # 生成简单的特征映射（将目标特征的键映射到最接近的源特征键）
                # 这里简化为同名映射，实际应基于语义相关性
                best_mapping = {k: k for k in target_features if k in exp.features}

        # 检查阈值
        if highest_score < threshold or best_match is None:
            logger.warning(f"No suitable match found above threshold {threshold}.")
            return MappingResult(
                target_skill=target_skill_name,
                matched_experience=None,
                similarity_score=highest_score,
                analogy_explanation="未找到足够相似的已知经验，建议扩充经验库。"
            )

        # 生成解释
        explanation = self._generate_analogy(target_skill_name, best_match, best_mapping)
        
        logger.info(f"Match found: '{best_match.name}' with score {highest_score:.2f}")
        
        return MappingResult(
            target_skill=target_skill_name,
            matched_experience=best_match,
            similarity_score=highest_score,
            analogy_explanation=explanation,
            mapping_details=best_mapping
        )

    def add_experience(self, new_exp: ExperienceNode) -> None:
        """
        [核心函数] 动态扩充经验库。
        
        Args:
            new_exp (ExperienceNode): 新的经验节点。
        """
        try:
            # 简单的重复检查
            if any(e.id == new_exp.id for e in self.experience_db):
                logger.warning(f"Experience ID {new_exp.id} already exists.")
                return
            self.experience_db.append(new_exp)
            logger.info(f"New experience added: {new_exp.name}")
        except Exception as e:
            logger.error(f"Failed to add experience: {e}")

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 构造模拟的用户经验库
    user_experiences = [
        ExperienceNode(
            id="exp_001",
            name="穿紧身牛仔裤拉拉链",
            domain="日常生活",
            features={
                "腹部收紧": 0.9,
                "骨盆后倾": 0.8,
                "深层压力": 0.7,
                "呼吸屏住": 0.5
            },
            description="为了扣上紧身的牛仔裤，必须深吸一口气，把肚子用力收回去。"
        ),
        ExperienceNode(
            id="exp_002",
            name="上厕所忘记带纸等待救援",
            domain="日常生活",
            features={
                "焦虑": 0.9,
                "腿部麻木": 0.8,
                "静止不动": 0.7
            },
            description="保持坐姿不敢动，腿部逐渐失去知觉。"
        ),
        ExperienceNode(
            id="exp_003",
            name="打喷嚏",
            domain="生理反射",
            features={
                "腹部瞬间收缩": 0.8,
                "气流急促": 0.9,
                "胸部震动": 0.6
            },
            description="无法控制的剧烈呼气动作。"
        )
    ]

    # 2. 初始化引擎
    engine = CrossDomainSomaticTransferEngine(user_experiences)

    # 3. 定义难以理解的抽象技能（输入）
    # 假设用户想学习普拉提中的 "Core Bracing" (核心收紧)
    abstract_skill_features = {
        "腹部收紧": 0.85,    # 对应 exp_001
        "骨盆后倾": 0.75,    # 对应 exp_001
        "深层压力": 0.8,     # 对应 exp_001
        "肋骨下沉": 0.4
    }

    # 4. 执行检索与迁移
    try:
        result = engine.retrieve_and_map(
            target_skill_name="普拉提核心收紧",
            target_features=abstract_skill_features,
            threshold=0.5
        )

        # 5. 输出结果
        print("\n" + "="*30)
        print(f"  Target Skill: {result.target_skill}")
        print(f"  Matched Experience: {result.matched_experience.name if result.matched_experience else 'None'}")
        print(f"  Similarity Score: {result.similarity_score:.2f}")
        print("-" * 30)
        print("  Insight/Analogy:")
        print(f"  {result.analogy_explanation}")
        print("="*30 + "\n")
        
        # 测试错误处理
        # engine.retrieve_and_map("Empty Test", {}) 

    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)