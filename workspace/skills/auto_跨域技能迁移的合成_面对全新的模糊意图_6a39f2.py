"""
高级AGI技能合成模块：跨域技能迁移与模糊意图解析

本模块实现了基于语义重叠区的复合技能合成算法，用于处理模糊意图场景下的技能迁移。
核心功能包括：
- 计算技能节点间的语义重叠度
- 基于图论的技能组合优化
- 动态技能链构建与验证

示例场景：
>>> synthesizer = SkillSynthesizer(skill_repository)
>>> intent = "监控竞品价格变动并发送邮件通知"
>>> new_skill = synthesizer.synthesize(intent)
>>> new_skill.execute()
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import numpy as np
from collections import defaultdict
from functools import lru_cache

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skill_synthesis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """技能节点数据结构，表示系统中的原子技能"""
    id: str
    name: str
    domain: str
    description: str
    input_schema: Dict
    output_schema: Dict
    dependencies: List[str]
    semantic_vector: Optional[np.ndarray] = None  # 技能的语义向量表示

    def __post_init__(self):
        """初始化后验证数据完整性"""
        if not all([self.id, self.name, self.domain]):
            raise ValueError("技能节点必须包含id, name和domain")
        if not isinstance(self.semantic_vector, (np.ndarray, type(None))):
            raise TypeError("semantic_vector必须是numpy数组或None")

class SkillSynthesizer:
    """跨域技能合成器，处理模糊意图并生成复合技能"""
    
    def __init__(self, skill_repository: Dict[str, SkillNode]):
        """
        初始化技能合成器
        
        参数:
            skill_repository: 技能仓库，包含所有可用技能节点
        """
        self.skill_repository = skill_repository
        self._build_overlap_matrix()
        logger.info(f"初始化技能合成器，加载 {len(skill_repository)} 个技能节点")
    
    def _build_overlap_matrix(self) -> None:
        """构建技能间的语义重叠矩阵"""
        self.overlap_matrix = defaultdict(dict)
        skill_ids = list(self.skill_repository.keys())
        
        for i in range(len(skill_ids)):
            for j in range(i+1, len(skill_ids)):
                skill_a = self.skill_repository[skill_ids[i]]
                skill_b = self.skill_repository[skill_ids[j]]
                overlap = self._calculate_semantic_overlap(skill_a, skill_b)
                self.overlap_matrix[skill_ids[i]][skill_ids[j]] = overlap
                self.overlap_matrix[skill_ids[j]][skill_ids[i]] = overlap
    
    @lru_cache(maxsize=1024)
    def _calculate_semantic_overlap(self, skill_a: SkillNode, skill_b: SkillNode) -> float:
        """
        计算两个技能间的语义重叠度
        
        参数:
            skill_a: 第一个技能节点
            skill_b: 第二个技能节点
            
        返回:
            float: 语义重叠度得分 (0.0-1.0)
            
        异常:
            ValueError: 如果技能向量未初始化
        """
        if skill_a.semantic_vector is None or skill_b.semantic_vector is None:
            raise ValueError("技能节点必须包含语义向量才能计算重叠度")
            
        # 计算余弦相似度
        similarity = np.dot(skill_a.semantic_vector, skill_b.semantic_vector) / (
            np.linalg.norm(skill_a.semantic_vector) * np.linalg.norm(skill_b.semantic_vector)
        )
        
        # 应用领域惩罚因子
        domain_penalty = 0.8 if skill_a.domain != skill_b.domain else 1.0
        final_score = similarity * domain_penalty
        
        logger.debug(f"计算 {skill_a.name} 和 {skill_b.name} 重叠度: {final_score:.3f}")
        return float(np.clip(final_score, 0.0, 1.0))
    
    def synthesize(self, intent: str, threshold: float = 0.7, max_depth: int = 3) -> Optional[SkillNode]:
        """
        合成新技能以处理模糊意图
        
        参数:
            intent: 用户意图描述
            threshold: 技能组合的最低重叠度阈值
            max_depth: 最大技能组合深度
            
        返回:
            SkillNode: 合成的新技能节点，如果失败返回None
            
        示例:
            >>> synthesizer = SkillSynthesizer(skill_repo)
            >>> new_skill = synthesizer.synthesize("每日自动爬取竞品数据并发送邮件报告")
        """
        if not intent or not isinstance(intent, str):
            logger.error("无效的意图输入")
            return None
            
        logger.info(f"开始合成技能处理意图: {intent}")
        
        try:
            # 1. 意图解析与向量化
            intent_vector = self._vectorize_intent(intent)
            
            # 2. 找到与意图最相关的初始技能
            candidate_skills = self._find_candidate_skills(intent_vector, threshold)
            if not candidate_skills:
                logger.warning("未找到与意图匹配的候选技能")
                return None
                
            # 3. 构建技能组合链
            skill_chain = self._build_skill_chain(candidate_skills, intent_vector, max_depth)
            if not skill_chain:
                logger.warning("无法构建有效的技能链")
                return None
                
            # 4. 合成新技能
            new_skill = self._compose_skill(skill_chain, intent)
            logger.info(f"成功合成新技能: {new_skill.name}")
            return new_skill
            
        except Exception as e:
            logger.error(f"技能合成过程中发生错误: {str(e)}", exc_info=True)
            return None
    
    def _vectorize_intent(self, intent: str) -> np.ndarray:
        """
        将意图文本转化为向量表示
        
        参数:
            intent: 意图文本
            
        返回:
            np.ndarray: 意图的向量表示
        """
        # 实际实现中会使用NLP模型进行向量化
        # 这里简化为随机向量作为示例
        logger.debug(f"向量化意图: {intent}")
        return np.random.rand(128)  # 假设我们的语义向量维度为128
    
    def _find_candidate_skills(self, intent_vector: np.ndarray, threshold: float) -> List[Tuple[SkillNode, float]]:
        """
        找到与意图向量最相关的候选技能
        
        参数:
            intent_vector: 意图的向量表示
            threshold: 最低相关性阈值
            
        返回:
            List[Tuple[SkillNode, float]]: 候选技能及其相关性得分列表
        """
        candidates = []
        
        for skill in self.skill_repository.values():
            if skill.semantic_vector is None:
                continue
                
            similarity = np.dot(skill.semantic_vector, intent_vector) / (
                np.linalg.norm(skill.semantic_vector) * np.linalg.norm(intent_vector)
            )
            
            if similarity >= threshold:
                candidates.append((skill, similarity))
                
        # 按相关性降序排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        logger.debug(f"找到 {len(candidates)} 个候选技能")
        return candidates
    
    def _build_skill_chain(self, candidates: List[Tuple[SkillNode, float]], 
                          intent_vector: np.ndarray, max_depth: int) -> List[SkillNode]:
        """
        构建技能组合链以最大化覆盖意图
        
        参数:
            candidates: 候选技能列表
            intent_vector: 意图向量
            max_depth: 最大链深度
            
        返回:
            List[SkillNode]: 构建的最佳技能链
        """
        if not candidates or max_depth <= 0:
            return []
            
        best_chain = []
        best_coverage = 0.0
        
        # 使用贪心算法构建技能链
        current_chain = [candidates[0][0]]
        remaining_intent = intent_vector - candidates[0][0].semantic_vector
        
        for _ in range(max_depth - 1):
            next_skill = self._find_best_overlap(current_chain[-1], remaining_intent)
            if not next_skill:
                break
                
            current_chain.append(next_skill)
            remaining_intent -= next_skill.semantic_vector
            
            # 计算当前链的意图覆盖率
            coverage = np.linalg.norm(intent_vector - remaining_intent) / np.linalg.norm(intent_vector)
            if coverage > best_coverage:
                best_coverage = coverage
                best_chain = current_chain.copy()
                
        return best_chain
    
    def _find_best_overlap(self, current_skill: SkillNode, remaining_intent: np.ndarray) -> Optional[SkillNode]:
        """
        找到与当前技能和剩余意图最佳重叠的下一个技能
        
        参数:
            current_skill: 当前技能节点
            remaining_intent: 剩余未覆盖的意图向量
            
        返回:
            SkillNode: 最佳下一个技能节点，如果找不到则返回None
        """
        best_skill = None
        best_score = -1.0
        
        for skill_id, overlap in self.overlap_matrix[current_skill.id].items():
            skill = self.skill_repository[skill_id]
            if skill.semantic_vector is None:
                continue
                
            # 计算与剩余意图的重叠度
            intent_overlap = np.dot(skill.semantic_vector, remaining_intent) / (
                np.linalg.norm(skill.semantic_vector) * np.linalg.norm(remaining_intent)
            )
            
            # 综合考虑技能间重叠和意图重叠
            combined_score = 0.6 * overlap + 0.4 * intent_overlap
            if combined_score > best_score:
                best_score = combined_score
                best_skill = skill
                
        return best_skill
    
    def _compose_skill(self, skill_chain: List[SkillNode], intent: str) -> SkillNode:
        """
        将技能链合成为新的复合技能
        
        参数:
            skill_chain: 技能链
            intent: 原始意图
            
        返回:
            SkillNode: 合成的新技能节点
        """
        # 生成新技能ID
        new_id = f"composite_{'_'.join(skill.id[:4] for skill in skill_chain)}"
        
        # 生成新技能名称
        name_parts = [skill.name for skill in skill_chain]
        new_name = " → ".join(name_parts)
        
        # 合并输入输出模式
        input_schema = {}
        output_schema = {}
        for i, skill in enumerate(skill_chain):
            input_schema.update({f"step_{i}_{k}": v for k, v in skill.input_schema.items()})
            if i == len(skill_chain) - 1:
                output_schema.update(skill.output_schema)
                
        # 创建复合技能
        composite_skill = SkillNode(
            id=new_id,
            name=new_name,
            domain="composite",
            description=f"自动合成的复合技能，用于处理: {intent}",
            input_schema=input_schema,
            output_schema=output_schema,
            dependencies=[skill.id for skill in skill_chain],
            semantic_vector=np.mean([skill.semantic_vector for skill in skill_chain], axis=0)
        )
        
        return composite_skill

# 示例用法
if __name__ == "__main__":
    # 创建示例技能仓库
    skill_repo = {
        "web_crawler": SkillNode(
            id="web_crawler",
            name="网页爬虫",
            domain="data_collection",
            description="从指定网站爬取数据",
            input_schema={"url": "string"},
            output_schema={"html": "string"},
            dependencies=[],
            semantic_vector=np.random.rand(128)
        ),
        "data_cleaner": SkillNode(
            id="data_cleaner",
            name="数据清洗",
            domain="data_processing",
            description="清洗和结构化原始数据",
            input_schema={"raw_data": "string"},
            output_schema={"clean_data": "dict"},
            dependencies=["web_crawler"],
            semantic_vector=np.random.rand(128)
        ),
        "email_sender": SkillNode(
            id="email_sender",
            name="邮件发送",
            domain="communication",
            description="发送电子邮件",
            input_schema={"to": "string", "subject": "string", "body": "string"},
            output_schema={"status": "bool"},
            dependencies=[],
            semantic_vector=np.random.rand(128)
        )
    }
    
    # 初始化技能合成器
    synthesizer = SkillSynthesizer(skill_repo)
    
    # 合成新技能处理模糊意图
    intent = "每日自动爬取竞品数据并发送邮件报告"
    new_skill = synthesizer.synthesize(intent)
    
    if new_skill:
        print(f"成功合成新技能: {new_skill.name}")
        print(f"描述: {new_skill.description}")
        print(f"依赖: {new_skill.dependencies}")
    else:
        print("技能合成失败")