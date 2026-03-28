"""
人机共生反馈环的信任权重动态分配系统

该模块实现了一个基于贝叶斯更新的动态信任模型，用于评估和分配人机共生系统中
人类反馈的权重。系统根据反馈者的历史准确率和领域专长，动态调整其提交的
'证伪'或'证实'操作的权重。

核心功能:
1. 基于Beta分布的贝叶斯更新机制
2. 领域专长加权
3. 动态信任评分计算
4. 反馈权重分配

输入格式:
    - user_id: str, 用户唯一标识
    - feedback_type: str, 反馈类型 ('confirm'|'refute')
    - domain: str, 反馈所属领域
    - evidence: float, 支持证据强度 [0, 1]

输出格式:
    - weight: float, 分配的反馈权重 [0, 1]
    - trust_score: float, 用户信任评分 [0, 1]
    - is_expert: bool, 是否为专家级用户
"""

import math
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """用户信任档案数据结构"""
    user_id: str
    alpha: float = 1.0  # Beta分布的成功参数
    beta: float = 1.0   # Beta分布的失败参数
    domain_expertise: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    total_feedbacks: int = 0
    correct_feedbacks: int = 0


class TrustWeightAllocator:
    """
    基于贝叶斯更新的信任权重动态分配系统
    
    该系统使用Beta分布建模用户的信任度，并结合领域专长信息
    动态调整用户反馈的权重。
    
    示例:
        >>> allocator = TrustWeightAllocator()
        >>> # 添加用户初始专长信息
        >>> allocator.update_domain_expertise("user123", "nlp", 0.7)
        >>> # 处理用户反馈
        >>> weight, trust_score = allocator.process_feedback(
        ...     "user123", "refute", "nlp", 0.8
        ... )
        >>> # 更新用户信任度
        >>> allocator.update_user_trust("user123", True)
    """
    
    def __init__(self, min_weight: float = 0.01, max_weight: float = 1.0):
        """
        初始化信任权重分配器
        
        参数:
            min_weight: 最小分配权重
            max_weight: 最大分配权重
        """
        self.min_weight = max(0.0, min_weight)
        self.max_weight = min(1.0, max_weight)
        self.users: Dict[str, UserProfile] = {}
        self.domain_weights: Dict[str, float] = {}
        logger.info("TrustWeightAllocator initialized with min_weight=%.2f, max_weight=%.2f", 
                   self.min_weight, self.max_weight)
    
    def _validate_user_id(self, user_id: str) -> None:
        """验证用户ID的有效性"""
        if not isinstance(user_id, str) or not user_id.strip():
            error_msg = f"Invalid user_id: {user_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_feedback_type(self, feedback_type: str) -> None:
        """验证反馈类型的有效性"""
        valid_types = {'confirm', 'refute'}
        if feedback_type not in valid_types:
            error_msg = f"Invalid feedback_type: {feedback_type}. Must be one of {valid_types}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_domain(self, domain: str) -> None:
        """验证领域的有效性"""
        if not isinstance(domain, str) or not domain.strip():
            error_msg = f"Invalid domain: {domain}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_evidence(self, evidence: float) -> None:
        """验证证据强度的有效性"""
        if not isinstance(evidence, (int, float)) or not 0 <= evidence <= 1:
            error_msg = f"Invalid evidence value: {evidence}. Must be between 0 and 1"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _get_or_create_user(self, user_id: str) -> UserProfile:
        """获取或创建用户档案"""
        self._validate_user_id(user_id)
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
            logger.info("Created new user profile for user_id: %s", user_id)
        return self.users[user_id]
    
    def _calculate_trust_score(self, user_profile: UserProfile) -> float:
        """
        计算用户的信任评分
        
        使用Beta分布的期望值作为信任评分:
        trust_score = alpha / (alpha + beta)
        
        参数:
            user_profile: 用户档案
            
        返回:
            float: 信任评分 [0, 1]
        """
        if user_profile.alpha <= 0 or user_profile.beta <= 0:
            return 0.5  # 默认中性信任度
        
        trust_score = user_profile.alpha / (user_profile.alpha + user_profile.beta)
        return np.clip(trust_score, 0.0, 1.0)
    
    def update_domain_expertise(
        self, 
        user_id: str, 
        domain: str, 
        expertise_level: float
    ) -> None:
        """
        更新用户的领域专长信息
        
        参数:
            user_id: 用户ID
            domain: 领域名称
            expertise_level: 专长水平 [0, 1]
            
        示例:
            >>> allocator.update_domain_expertise("user123", "nlp", 0.8)
        """
        self._validate_user_id(user_id)
        self._validate_domain(domain)
        
        if not isinstance(expertise_level, (int, float)) or not 0 <= expertise_level <= 1:
            error_msg = f"Invalid expertise_level: {expertise_level}. Must be between 0 and 1"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user_profile = self._get_or_create_user(user_id)
        user_profile.domain_expertise[domain] = expertise_level
        user_profile.last_updated = datetime.now()
        logger.info("Updated domain expertise for user %s in %s: %.2f", 
                   user_id, domain, expertise_level)
    
    def update_user_trust(
        self, 
        user_id: str, 
        is_correct: bool, 
        learning_rate: float = 0.1
    ) -> float:
        """
        基于反馈正确性更新用户信任度
        
        使用贝叶斯更新规则:
        - 如果反馈正确: alpha += learning_rate * evidence
        - 如果反馈错误: beta += learning_rate * evidence
        
        参数:
            user_id: 用户ID
            is_correct: 反馈是否正确
            learning_rate: 学习率，控制更新速度
            
        返回:
            float: 更新后的信任评分
            
        示例:
            >>> # 当用户反馈被证实正确时
            >>> trust_score = allocator.update_user_trust("user123", True)
        """
        self._validate_user_id(user_id)
        
        if not isinstance(is_correct, bool):
            error_msg = f"Invalid is_correct type: {type(is_correct)}. Must be bool"
            logger.error(error_msg)
            raise TypeError(error_msg)
        
        if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
            error_msg = f"Invalid learning_rate: {learning_rate}. Must be positive"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user_profile = self._get_or_create_user(user_id)
        
        # 贝叶斯更新
        if is_correct:
            user_profile.alpha += learning_rate
            user_profile.correct_feedbacks += 1
        else:
            user_profile.beta += learning_rate
        
        user_profile.total_feedbacks += 1
        user_profile.last_updated = datetime.now()
        
        trust_score = self._calculate_trust_score(user_profile)
        logger.info("Updated trust for user %s: is_correct=%s, new_trust=%.4f", 
                   user_id, is_correct, trust_score)
        
        return trust_score
    
    def calculate_feedback_weight(
        self,
        user_id: str,
        feedback_type: str,
        domain: str,
        evidence: float = 0.5
    ) -> Tuple[float, float]:
        """
        计算用户反馈的权重
        
        权重计算考虑以下因素:
        1. 用户基础信任评分 (来自贝叶斯更新)
        2. 领域专长加权
        3. 反馈类型 (证伪通常需要更高信任度)
        4. 证据强度
        
        参数:
            user_id: 用户ID
            feedback_type: 反馈类型 ('confirm'|'refute')
            domain: 反馈所属领域
            evidence: 支持证据强度 [0, 1]
            
        返回:
            Tuple[float, float]: (权重, 信任评分)
            
        示例:
            >>> weight, trust = allocator.calculate_feedback_weight(
            ...     "expert1", "refute", "nlp", 0.9
            ... )
        """
        # 输入验证
        self._validate_user_id(user_id)
        self._validate_feedback_type(feedback_type)
        self._validate_domain(domain)
        self._validate_evidence(evidence)
        
        user_profile = self._get_or_create_user(user_id)
        base_trust = self._calculate_trust_score(user_profile)
        
        # 获取领域专长，如果没有则使用基础信任度
        domain_factor = user_profile.domain_expertise.get(domain, base_trust)
        
        # 反馈类型调整因子 (证伪需要更高信任度)
        type_factor = 1.2 if feedback_type == 'refute' else 1.0
        
        # 计算综合权重
        raw_weight = base_trust * domain_factor * type_factor * evidence
        
        # 应用非线性变换增强区分度
        weight = math.tanh(2.0 * raw_weight)
        
        # 应用边界限制
        weight = np.clip(weight, self.min_weight, self.max_weight)
        
        logger.debug(
            "Calculated weight for user %s: base_trust=%.4f, domain_factor=%.4f, "
            "type_factor=%.2f, evidence=%.2f, final_weight=%.4f",
            user_id, base_trust, domain_factor, type_factor, evidence, weight
        )
        
        return float(weight), base_trust
    
    def is_expert(self, user_id: str, domain: str, threshold: float = 0.7) -> bool:
        """
        判断用户是否为领域专家
        
        参数:
            user_id: 用户ID
            domain: 领域名称
            threshold: 专家判定阈值
            
        返回:
            bool: 是否为专家
            
        示例:
            >>> if allocator.is_expert("user123", "nlp"):
            ...     print("User is an expert in NLP")
        """
        self._validate_user_id(user_id)
        self._validate_domain(domain)
        
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            error_msg = f"Invalid threshold: {threshold}. Must be between 0 and 1"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user_profile = self._get_or_create_user(user_id)
        trust_score = self._calculate_trust_score(user_profile)
        domain_expertise = user_profile.domain_expertise.get(domain, 0.0)
        
        # 综合信任度和领域专长
        combined_score = 0.6 * trust_score + 0.4 * domain_expertise
        is_expert_user = combined_score >= threshold
        
        logger.debug(
            "Expert check for user %s in domain %s: trust=%.4f, expertise=%.4f, combined=%.4f, is_expert=%s",
            user_id, domain, trust_score, domain_expertise, combined_score, is_expert_user
        )
        
        return is_expert_user
    
    def get_user_stats(self, user_id: str) -> Dict[str, float]:
        """
        获取用户统计信息
        
        参数:
            user_id: 用户ID
            
        返回:
            Dict[str, float]: 用户统计信息
            
        示例:
            >>> stats = allocator.get_user_stats("user123")
            >>> print(f"Trust score: {stats['trust_score']:.2f}")
        """
        self._validate_user_id(user_id)
        
        if user_id not in self.users:
            logger.warning("User %s not found", user_id)
            return {
                'trust_score': 0.5,
                'total_feedbacks': 0,
                'correct_feedbacks': 0,
                'accuracy': 0.0
            }
        
        user_profile = self.users[user_id]
        trust_score = self._calculate_trust_score(user_profile)
        accuracy = (
            user_profile.correct_feedbacks / user_profile.total_feedbacks
            if user_profile.total_feedbacks > 0 else 0.0
        )
        
        return {
            'trust_score': trust_score,
            'total_feedbacks': user_profile.total_feedbacks,
            'correct_feedbacks': user_profile.correct_feedbacks,
            'accuracy': accuracy,
            'last_updated': user_profile.last_updated.isoformat()
        }


# 使用示例
if __name__ == "__main__":
    # 初始化信任权重分配器
    allocator = TrustWeightAllocator(min_weight=0.05, max_weight=1.0)
    
    # 示例1: 新手用户随机点击"证实"
    novice_user = "novice123"
    weight, trust = allocator.calculate_feedback_weight(
        novice_user, "confirm", "general", evidence=0.3
    )
    print(f"Novice user weight: {weight:.4f}, trust: {trust:.4f}")
    
    # 示例2: 设置专家用户
    expert_user = "expert456"
    allocator.update_domain_expertise(expert_user, "nlp", 0.9)
    allocator.update_user_trust(expert_user, True)  # 历史正确反馈
    allocator.update_user_trust(expert_user, True)
    
    # 专家用户的"证伪"操作
    weight, trust = allocator.calculate_feedback_weight(
        expert_user, "refute", "nlp", evidence=0.95
    )
    print(f"Expert user weight: {weight:.4f}, trust: {trust:.4f}")
    print(f"Is expert: {allocator.is_expert(expert_user, 'nlp')}")
    
    # 示例3: 查看用户统计
    stats = allocator.get_user_stats(expert_user)
    print(f"Expert stats: {stats}")