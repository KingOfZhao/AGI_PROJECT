"""
模块名称: intent_formalization_mapper
描述: 【意图形式化层】构建'模糊语言到分层任务树(HTN)的概率映射器'。
      本模块实现了将含有隐喻和歧义的自然语言(NL)转化为带概率分布的中间表示(IR)，
      并利用现有SKILL节点作为约束条件进行语义对齐。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义异常类
class IntentMappingError(Exception):
    """自定义异常：意图映射过程中的错误"""
    pass

class SkillNodeNotFoundError(Exception):
    """自定义异常：未找到匹配的技能节点"""
    pass

@dataclass
class SkillNode:
    """
    报能节点数据结构
    """
    id: str
    name: str
    description: str
    keywords: List[str]
    embedding: Optional[np.ndarray] = None
    children: List['SkillNode'] = field(default_factory=list)

@dataclass
class MappedIntent:
    """
    映射后的意图中间表示
    """
    raw_input: str
    matched_skills: List[Tuple[str, float]]  # (Skill ID, Probability)
    resolved_semantics: Dict[str, str]       # 解析出的语义槽位
    confidence: float

class IntentFormalizationMapper:
    """
    意图形式化映射器核心类。
    
    将模糊的自然语言输入映射到结构化的分层任务网络节点。
    核心算法结合了语义相似度计算与基于约束的传播。
    """
    
    def __init__(self, skill_repository: List[SkillNode], embedding_dim: int = 128):
        """
        初始化映射器。
        
        Args:
            skill_repository (List[SkillNode]): 系统可用的技能节点库。
            embedding_dim (int): 语义向量的维度。
        """
        if not skill_repository:
            logger.warning("Skill repository is empty. Mapper will not produce results.")
        
        self.skill_repo = skill_repository
        self.embedding_dim = embedding_dim
        self._build_index()
        logger.info(f"Mapper initialized with {len(self.skill_repo)} skills.")

    def _build_index(self):
        """构建简单的内存索引，实际生产中应使用向量数据库"""
        self.skill_embeddings = np.array(
            [s.embedding for s in self.skill_repo if s.embedding is not None]
        )
        if self.skill_embeddings.size == 0:
            # 如果没有预置embedding，生成随机占位符用于演示
            logger.warning("No embeddings found in skills, using random placeholders.")
            self.skill_embeddings = np.random.randn(len(self.skill_repo), self.embedding_dim)
            
    def _text_to_vector(self, text: str) -> np.ndarray:
        """
        辅助函数：将文本转换为向量。
        [模拟] 实际生产中应调用BERT/GPT等模型API。
        
        Args:
            text (str): 输入文本
            
        Returns:
            np.ndarray: 文本的向量表示
        """
        # 简单的Hash模拟向量化，确保确定性用于演示
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self.embedding_dim)

    def _resolve_metaphors(self, text: str) -> Dict[str, str]:
        """
        辅助函数：解析隐喻和模糊词汇。
        
        Args:
            text (str): 原始输入文本
            
        Returns:
            Dict[str, str]: 解析出的属性键值对
        """
        semantics = {}
        # 定义简单的启发式规则（实际需要常识图谱支持）
        if "科技感" in text or "赛博朋克" in text:
            semantics["style"] = "futuristic"
            semantics["color_scheme"] = "neon_dark"
        
        if "简单" in text or "傻瓜式" in text:
            semantics["complexity"] = "low"
            semantics["ux_pattern"] = "wizard"
            
        if "专业" in text:
            semantics["complexity"] = "high"
            semantics["detail_level"] = "verbose"
            
        logger.debug(f"Resolved metaphors: {semantics}")
        return semantics

    def _calculate_semantic_alignment(self, input_vec: np.ndarray, skill_vec: np.ndarray) -> float:
        """
        计算语义对齐分数（余弦相似度）。
        
        Args:
            input_vec (np.ndarray): 输入向量
            skill_vec (np.ndarray): 技能向量
            
        Returns:
            float: 相似度分数 [0, 1]
        """
        norm_product = np.linalg.norm(input_vec) * np.linalg.norm(skill_vec)
        if norm_product == 0:
            return 0.0
        return np.dot(input_vec, skill_vec) / norm_product

    def map_to_htn_distribution(
        self, 
        natural_language_input: str, 
        top_k: int = 3,
        threshold: float = 0.2
    ) -> MappedIntent:
        """
        核心函数：将自然语言映射为带概率分布的HTN节点集合。
        
        流程:
        1. 隐喻解析
        2. 向量化
        3. 全局语义对齐
        4. 构建概率分布
        
        Args:
            natural_language_input (str): 用户的自然语言输入
            top_k (int): 返回的最匹配节点数量
            threshold (float): 置信度阈值，低于此值不返回
            
        Returns:
            MappedIntent: 包含匹配结果的数据对象
            
        Raises:
            IntentMappingError: 如果输入无效或映射失败
        """
        if not natural_language_input or not isinstance(natural_language_input, str):
            raise IntentMappingError("Input must be a non-empty string.")
            
        logger.info(f"Processing intent: {natural_language_input}")
        
        # 1. 隐喻解析
        resolved_semantics = self._resolve_metaphors(natural_language_input)
        
        # 2. 向量化输入
        input_vec = self._text_to_vector(natural_language_input)
        
        # 3. 计算与所有技能节点的对齐分数
        scores = []
        for idx, skill in enumerate(self.skill_repo):
            # 结合关键词匹配增强（简单的混合策略）
            keyword_boost = 0.0
            for kw in skill.keywords:
                if kw in natural_language_input:
                    keyword_boost += 0.1 # 每命中一个关键词增加权重
            
            # 计算语义相似度
            skill_vec = self.skill_embeddings[idx]
            semantic_score = self._calculate_semantic_alignment(input_vec, skill_vec)
            
            # 混合分数
            final_score = min((semantic_score + keyword_boost) / (1 + keyword_boost), 1.0)
            scores.append((skill.id, final_score, skill.name))
            
        # 4. 排序并选择 Top-K
        scores.sort(key=lambda x: x[1], reverse=True)
        filtered_scores = [(s[0], s[1]) for s in scores if s[1] >= threshold]
        
        if not filtered_scores:
            logger.warning("No skills matched the threshold.")
            return MappedIntent(
                raw_input=natural_language_input,
                matched_skills=[],
                resolved_semantics=resolved_semantics,
                confidence=0.0
            )
            
        top_matches = filtered_scores[:top_k]
        
        # 归一化概率分布
        total_score = sum(s[1] for s in top_matches)
        normalized_matches = [(s[0], s[1]/total_score) for s in top_matches]
        
        # 计算 overall confidence
        system_confidence = normalized_matches[0][1] if normalized_matches else 0.0
        
        return MappedIntent(
            raw_input=natural_language_input,
            matched_skills=normalized_matches,
            resolved_semantics=resolved_semantics,
            confidence=system_confidence
        )

    def validate_constraints(self, mapped_intent: MappedIntent) -> bool:
        """
        验证映射结果是否满足系统约束条件。
        
        Args:
            mapped_intent (MappedIntent): 映射后的意图对象
            
        Returns:
            bool: 是否通过验证
        """
        if not mapped_intent.matched_skills:
            return False
            
        # 检查置信度是否过低
        if mapped_intent.confidence < 0.1:
            logger.error("Validation failed: Confidence too low.")
            return False
            
        return True

# --- 使用示例与数据构建 ---

def setup_demo_environment():
    """构建演示环境"""
    # 模拟技能库
    skills = [
        SkillNode(
            id="ui_gen_dark",
            name="Dark UI Generator",
            description="Generates dark mode user interfaces",
            keywords=["界面", "UI", "暗色", "科技"],
            embedding=np.random.randn(128) * 0.5 + 0.2 # 模拟特定的向量分布
        ),
        SkillNode(
            id="data_viz",
            name="Data Visualizer",
            description="Creates charts and graphs",
            keywords=["图表", "分析", "数据", "展示"],
            embedding=np.random.randn(128) * 0.5 + 0.8
        ),
        SkillNode(
            id="code_refactor",
            name="Code Refactor Tool",
            description="Refactors and cleans code",
            keywords=["代码", "重构", "优化", "清理"],
            embedding=np.random.randn(128) - 0.5
        )
    ]
    return skills

if __name__ == "__main__":
    # 初始化
    demo_skills = setup_demo_environment()
    mapper = IntentFormalizationMapper(demo_skills)
    
    # 测试用例 1: 包含隐喻的模糊需求
    fuzzy_input = "我要一个有科技感的界面"
    
    try:
        print(f"\n--- Input: {fuzzy_input} ---")
        result = mapper.map_to_htn_distribution(fuzzy_input)
        
        print(f"Confidence: {result.confidence:.4f}")
        print("Matched Skills (ID: Probability):")
        for skill_id, prob in result.matched_skills:
            print(f"  - {skill_id}: {prob:.2%}")
        print(f"Resolved Semantics: {result.resolved_semantics}")
        
        if mapper.validate_constraints(result):
            print(">> Result validated successfully.")
        else:
            print(">> Result validation failed.")
            
    except IntentMappingError as e:
        logger.error(f"Mapping failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error occurred.")