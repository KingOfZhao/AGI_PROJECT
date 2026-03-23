"""
模块: dynamic_user_style_mapper
描述: 建立用户画像与代码风格的动态映射机制，支持跨域特征重叠分析。
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from pydantic import BaseModel, validator, confloat

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PriorityType(Enum):
    """代码风格优先级枚举"""
    PERFORMANCE = "performance"
    READABILITY = "readability"
    CONCISENESS = "conciseness"
    MAINTAINABILITY = "maintainability"

class ParadigmType(Enum):
    """编程范式枚举"""
    FUNCTIONAL = "functional"
    OOP = "object_oriented"
    PROCEDURAL = "procedural"

class UserInteractionData(BaseModel):
    """用户交互数据模型，包含隐式偏好特征"""
    user_id: str
    interaction_count: int
    avg_response_time: float  # 平均响应时间
    code_complexity_score: confloat(ge=0, le=1)  # 代码复杂度评分
    error_rate: confloat(ge=0, le=1)  # 错误率
    feature_usage: Dict[str, float]  # 功能使用频率
    paradigm_preference: Dict[str, float]  # 编程范式偏好分布

    @validator('interaction_count')
    def validate_interaction_count(cls, v):
        if v < 0:
            raise ValueError("Interaction count must be positive")
        return v

@dataclass
class CodeStyleProfile:
    """代码风格配置，包含生成参数约束"""
    priority_weights: Dict[PriorityType, float] = field(default_factory=dict)
    paradigm_weights: Dict[ParadigmType, float] = field(default_factory=dict)
    max_nesting_depth: int = 3
    max_line_length: int = 88
    type_hints_required: bool = True
    docstring_style: str = "google"
    complexity_threshold: float = 0.7

    def to_generation_params(self) -> Dict[str, Any]:
        """转换为代码生成参数"""
        return {
            "priority": max(self.priority_weights.items(), key=lambda x: x[1])[0].value,
            "paradigm": max(self.paradigm_weights.items(), key=lambda x: x[1])[0].value,
            "formatting": {
                "max_line_length": self.max_line_length,
                "max_nesting_depth": self.max_nesting_depth
            },
            "quality": {
                "type_hints": self.type_hints_required,
                "docstring_style": self.docstring_style,
                "complexity_threshold": self.complexity_threshold
            }
        }

class StyleMapper:
    """用户画像到代码风格的动态映射器"""
    
    def __init__(self):
        self.user_profiles: Dict[str, CodeStyleProfile] = {}
        self.style_vectors: Dict[str, np.ndarray] = {}
        self._initialize_default_styles()
        
    def _initialize_default_styles(self) -> None:
        """初始化默认风格模板"""
        default_profiles = {
            "performance_oriented": CodeStyleProfile(
                priority_weights={PriorityType.PERFORMANCE: 0.7, PriorityType.READABILITY: 0.3},
                paradigm_weights={ParadigmType.FUNCTIONAL: 0.6, ParadigmType.OOP: 0.4},
                complexity_threshold=0.8,
                type_hints_required=True
            ),
            "readability_oriented": CodeStyleProfile(
                priority_weights={PriorityType.READABILITY: 0.6, PriorityType.MAINTAINABILITY: 0.4},
                paradigm_weights={ParadigmType.OOP: 0.7, ParadigmType.FUNCTIONAL: 0.3},
                max_nesting_depth=2,
                docstring_style="numpy"
            ),
            "balanced": CodeStyleProfile(
                priority_weights={PriorityType.READABILITY: 0.4, PriorityType.PERFORMANCE: 0.3, PriorityType.MAINTAINABILITY: 0.3},
                paradigm_weights={ParadigmType.OOP: 0.5, ParadigmType.FUNCTIONAL: 0.5}
            )
        }
        
        for name, profile in default_profiles.items():
            self.style_vectors[name] = self._profile_to_vector(profile)
            self.user_profiles[name] = profile
            
    def _profile_to_vector(self, profile: CodeStyleProfile) -> np.ndarray:
        """将风格配置转换为特征向量"""
        priority_vec = np.array([profile.priority_weights.get(p, 0) for p in PriorityType])
        paradigm_vec = np.array([profile.paradigm_weights.get(p, 0) for p in ParadigmType])
        quality_vec = np.array([
            profile.max_nesting_depth / 5,  # 归一化
            profile.max_line_length / 120,
            float(profile.type_hints_required),
            profile.complexity_threshold
        ])
        return np.concatenate([priority_vec, paradigm_vec, quality_vec])
    
    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _extract_implicit_features(self, interaction_data: UserInteractionData) -> np.ndarray:
        """从交互数据中提取隐式特征向量"""
        # 优先级特征推断
        priority_features = np.array([
            1 - interaction_data.error_rate,  # 性能优先 (低错误率)
            1 - interaction_data.code_complexity_score,  # 可读性优先
            1 / (1 + interaction_data.avg_response_time),  # 简洁性优先
            1 - interaction_data.code_complexity_score  # 可维护性
        ])
        
        # 范式特征提取
        paradigm_features = np.array([
            interaction_data.paradigm_preference.get("functional", 0),
            interaction_data.paradigm_preference.get("oop", 0),
            interaction_data.paradigm_preference.get("procedural", 0)
        ])
        
        # 质量特征提取
        quality_features = np.array([
            min(interaction_data.code_complexity_score * 5, 1),  # 嵌套深度
            0.7,  # 默认行长度
            interaction_data.feature_usage.get("type_hints", 0.5),
            interaction_data.code_complexity_score
        ])
        
        return np.concatenate([priority_features, paradigm_features, quality_features])
    
    def map_user_to_style(self, interaction_data: UserInteractionData) -> Tuple[CodeStyleProfile, float]:
        """
        将用户交互数据映射到代码风格配置
        
        参数:
            interaction_data: 用户交互数据模型
            
        返回:
            Tuple[CodeStyleProfile, float]: 最匹配的风格配置和相似度得分
            
        异常:
            ValueError: 如果输入数据无效
        """
        try:
            if interaction_data.interaction_count < 5:
                logger.warning("Insufficient interaction data, using default profile")
                return self.user_profiles["balanced"], 0.0
            
            user_vec = self._extract_implicit_features(interaction_data)
            max_sim = -1
            best_match = "balanced"
            
            # 计算与预定义风格的相似度
            for style_name, style_vec in self.style_vectors.items():
                sim = self._calculate_similarity(user_vec, style_vec)
                if sim > max_sim:
                    max_sim = sim
                    best_match = style_name
            
            # 创建个性化配置
            base_profile = self.user_profiles[best_match]
            personalized = self._create_personalized_profile(base_profile, user_vec)
            
            logger.info(f"User {interaction_data.user_id} mapped to {best_match} style (similarity: {max_sim:.2f})")
            return personalized, max_sim
            
        except Exception as e:
            logger.error(f"Error mapping user style: {str(e)}")
            raise ValueError(f"Style mapping failed: {str(e)}")
    
    def _create_personalized_profile(self, base: CodeStyleProfile, user_vec: np.ndarray) -> CodeStyleProfile:
        """创建个性化风格配置"""
        # 从向量中提取特征
        priority_weights = {
            PriorityType.PERFORMANCE: user_vec[0],
            PriorityType.READABILITY: user_vec[1],
            PriorityType.CONCISENESS: user_vec[2],
            PriorityType.MAINTAINABILITY: user_vec[3]
        }
        
        paradigm_weights = {
            ParadigmType.FUNCTIONAL: user_vec[4],
            ParadigmType.OOP: user_vec[5],
            ParadigmType.PROCEDURAL: user_vec[6]
        }
        
        # 创建混合配置
        return CodeStyleProfile(
            priority_weights=priority_weights,
            paradigm_weights=paradigm_weights,
            max_nesting_depth=min(int(user_vec[7] * 5), 5),
            max_line_length=int(user_vec[8] * 120),
            type_hints_required=user_vec[9] > 0.5,
            complexity_threshold=user_vec[10]
        )

    def update_style_vectors(self, feedback_data: Dict[str, Any]) -> None:
        """
        根据用户反馈更新风格向量
        
        参数:
            feedback_data: 包含用户反馈的字典，包括user_id, rating和comments
        """
        try:
            user_id = feedback_data.get("user_id")
            if not user_id or user_id not in self.user_profiles:
                logger.warning(f"Unknown user ID: {user_id}")
                return
            
            # 简单反馈处理：根据评分调整相似度权重
            rating = feedback_data.get("rating", 3)  # 1-5分
            adjustment = (rating - 3) * 0.1  # 标准化调整因子
            
            # 更新用户特征向量 (简化示例)
            if user_id in self.style_vectors:
                self.style_vectors[user_id] *= (1 + adjustment)
                logger.info(f"Updated style vector for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error updating style vectors: {str(e)}")

# 使用示例
if __name__ == "__main__":
    # 示例用户交互数据
    sample_interaction = UserInteractionData(
        user_id="dev_123",
        interaction_count=42,
        avg_response_time=0.8,
        code_complexity_score=0.4,
        error_rate=0.1,
        feature_usage={"type_hints": 0.8, "logging": 0.6},
        paradigm_preference={"functional": 0.7, "oop": 0.3}
    )
    
    # 创建映射器并映射用户风格
    mapper = StyleMapper()
    style_profile, similarity = mapper.map_user_to_style(sample_interaction)
    
    print(f"Matched style with similarity: {similarity:.2f}")
    print("Generation params:", style_profile.to_generation_params())
    
    # 模拟用户反馈
    feedback = {
        "user_id": "dev_123",
        "rating": 4,
        "comments": "Good performance but could be more readable"
    }
    mapper.update_style_vectors(feedback)