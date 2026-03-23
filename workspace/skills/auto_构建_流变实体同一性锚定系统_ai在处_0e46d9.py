"""
流变实体同一性锚定系统

本模块构建了一个用于长期人机共生关系的动态用户模型系统。
通过混合使用SCD Type 2（历史版本记录）和Type 3（当前与初始状态记录）的建模方法，
使AI能够理解用户行为的演变轨迹，而非仅做切片分析。

系统核心功能:
- 追踪用户属性的演变历史（SCD Type 2）
- 维护用户初始状态锚点（SCD Type 3）
- 提供行为一致性与偏差的智能分析
- 支持多维度用户画像的动态更新

典型用例:
>>> system = IdentityAnchorSystem()
>>> system.initialize_user("user_123", {"personality": "calm", "patience": 0.9})
>>> system.update_state("user_123", {"patience": 0.3}, context="deadline_pressure")
>>> analysis = system.analyze_deviation("user_123", "patience")
>>> print(analysis)
"虽然你现在很急躁(当前属性)，但这不符合你原本冷静的性格(历史锚点)"

数据格式:
输入:
- user_id: str
- attributes: Dict[str, Any] (用户属性键值对)
- context: Optional[str] (状态变更上下文)

输出:
- 分析结果: Dict[str, Any] (包含偏差度、建议响应等)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
from collections import defaultdict
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class UserState:
    """用户状态数据结构"""
    attributes: Dict[str, Any]  # 当前属性
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Optional[str] = None  # 状态变更上下文


@dataclass
class UserProfile:
    """用户完整档案（混合SCD Type 2 + Type 3）"""
    user_id: str
    initial_state: UserState  # 初始状态锚点（Type 3）
    current_state: UserState  # 当前状态（Type 3）
    historical_states: List[UserState] = field(default_factory=list)  # 历史版本（Type 2）
    attribute_weights: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """将用户档案序列化为字典"""
        return {
            "user_id": self.user_id,
            "initial_state": self.initial_state.__dict__,
            "current_state": self.current_state.__dict__,
            "historical_states": [s.__dict__ for s in self.historical_states],
            "attribute_weights": dict(self.attribute_weights),
            "last_updated": self.last_updated
        }


class IdentityAnchorSystem:
    """
    流变实体同一性锚定系统
    
    实现SCD Type 2 + Type 3混合建模，用于长期人机关系中的用户行为理解。
    
    Attributes:
        users (Dict[str, UserProfile]): 用户档案字典
        attribute_schemas (Dict[str, type]): 属性类型模式
        deviation_threshold (float): 偏差阈值
    """
    
    def __init__(self, deviation_threshold: float = 0.4):
        """
        初始化系统
        
        Args:
            deviation_threshold: 判断行为偏差的阈值，默认0.4
        """
        self.users: Dict[str, UserProfile] = {}
        self.attribute_schemas: Dict[str, type] = {
            "personality": str,
            "patience": float,
            "mood": str,
            "stress_level": float,
            "engagement": float
        }
        self.deviation_threshold = deviation_threshold
        logger.info("IdentityAnchorSystem initialized with threshold %.2f", deviation_threshold)
    
    def initialize_user(self, user_id: str, initial_attributes: Dict[str, Any]) -> bool:
        """
        初始化用户档案
        
        Args:
            user_id: 用户唯一标识
            initial_attributes: 初始属性字典
            
        Returns:
            bool: 初始化是否成功
            
        Raises:
            ValueError: 如果用户已存在或属性无效
        """
        if user_id in self.users:
            logger.error("User %s already exists", user_id)
            raise ValueError(f"User {user_id} already exists")
        
        # 验证属性
        self._validate_attributes(initial_attributes)
        
        # 创建初始状态
        initial_state = UserState(attributes=initial_attributes.copy())
        
        # 创建用户档案
        profile = UserProfile(
            user_id=user_id,
            initial_state=initial_state,
            current_state=initial_state,
            historical_states=[],
            attribute_weights=self._calculate_initial_weights(initial_attributes)
        )
        
        self.users[user_id] = profile
        logger.info("Initialized user %s with attributes: %s", user_id, initial_attributes)
        return True
    
    def update_state(self, user_id: str, new_attributes: Dict[str, Any], 
                    context: Optional[str] = None) -> bool:
        """
        更新用户状态（SCD Type 2历史记录 + Type 3当前状态）
        
        Args:
            user_id: 用户唯一标识
            new_attributes: 要更新的属性字典
            context: 状态变更的上下文描述
            
        Returns:
            bool: 更新是否成功
            
        Raises:
            KeyError: 如果用户不存在
            ValueError: 如果属性无效
        """
        if user_id not in self.users:
            logger.error("User %s not found", user_id)
            raise KeyError(f"User {user_id} not found")
        
        # 验证属性
        self._validate_attributes(new_attributes, partial=True)
        
        profile = self.users[user_id]
        
        # 将当前状态添加到历史记录（SCD Type 2）
        profile.historical_states.append(profile.current_state)
        
        # 创建新状态
        merged_attributes = {**profile.current_state.attributes, **new_attributes}
        new_state = UserState(
            attributes=merged_attributes,
            context=context
        )
        
        # 更新当前状态（SCD Type 3）
        profile.current_state = new_state
        profile.last_updated = datetime.now().isoformat()
        
        # 更新属性权重
        self._update_weights(user_id, new_attributes)
        
        logger.info("Updated user %s state: %s (context: %s)", 
                   user_id, new_attributes, context)
        return True
    
    def analyze_deviation(self, user_id: str, attribute: str) -> Dict[str, Any]:
        """
        分析用户属性与初始锚点的偏差
        
        Args:
            user_id: 用户唯一标识
            attribute: 要分析的属性名
            
        Returns:
            Dict: 包含分析结果的字典，格式:
                {
                    "attribute": str,
                    "current_value": Any,
                    "initial_value": Any,
                    "deviation_score": float,
                    "is_significant": bool,
                    "trend": str,
                    "suggestion": str
                }
                
        Raises:
            KeyError: 如果用户或属性不存在
        """
        if user_id not in self.users:
            raise KeyError(f"User {user_id} not found")
        
        profile = self.users[user_id]
        
        if attribute not in profile.initial_state.attributes:
            raise KeyError(f"Attribute {attribute} not found for user {user_id}")
        
        initial_value = profile.initial_state.attributes[attribute]
        current_value = profile.current_state.attributes[attribute]
        
        # 计算偏差分数
        deviation_score = self._calculate_deviation_score(
            initial_value, current_value, attribute
        )
        
        # 分析趋势
        trend = self._analyze_trend(profile.historical_states, attribute)
        
        # 生成建议
        suggestion = self._generate_suggestion(
            attribute, initial_value, current_value, deviation_score, trend
        )
        
        result = {
            "attribute": attribute,
            "current_value": current_value,
            "initial_value": initial_value,
            "deviation_score": deviation_score,
            "is_significant": deviation_score > self.deviation_threshold,
            "trend": trend,
            "suggestion": suggestion
        }
        
        logger.info("Analyzed deviation for %s.%s: score=%.2f", 
                   user_id, attribute, deviation_score)
        return result
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户完整档案
        
        Args:
            user_id: 用户唯一标识
            
        Returns:
            Dict: 序列化的用户档案
            
        Raises:
            KeyError: 如果用户不存在
        """
        if user_id not in self.users:
            raise KeyError(f"User {user_id} not found")
        return self.users[user_id].to_dict()
    
    def _validate_attributes(self, attributes: Dict[str, Any], partial: bool = False) -> None:
        """
        验证属性字典（辅助函数）
        
        Args:
            attributes: 要验证的属性字典
            partial: 是否为部分更新
            
        Raises:
            ValueError: 如果属性无效
        """
        if not isinstance(attributes, dict):
            raise ValueError("Attributes must be a dictionary")
        
        for attr, value in attributes.items():
            if attr not in self.attribute_schemas:
                logger.warning("Unknown attribute: %s", attr)
                continue
            
            expected_type = self.attribute_schemas[attr]
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"Attribute {attr} must be {expected_type}, got {type(value)}"
                )
            
            # 数值范围检查
            if expected_type == float:
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"Attribute {attr} must be between 0 and 1")
    
    def _calculate_deviation_score(self, initial: Any, current: Any, 
                                  attribute: str) -> float:
        """
        计算偏差分数（辅助函数）
        
        Args:
            initial: 初始值
            current: 当前值
            attribute: 属性名
            
        Returns:
            float: 偏差分数 [0, 1]
        """
        if isinstance(initial, (int, float)) and isinstance(current, (int, float)):
            return abs(initial - current)
        elif isinstance(initial, str) and isinstance(current, str):
            # 简单的字符串相似度计算
            if initial == current:
                return 0.0
            return 0.5 if initial.lower() == current.lower() else 1.0
        else:
            return 1.0 if initial != current else 0.0
    
    def _analyze_trend(self, historical_states: List[UserState], attribute: str) -> str:
        """
        分析属性变化趋势（辅助函数）
        
        Args:
            historical_states: 历史状态列表
            attribute: 属性名
            
        Returns:
            str: 趋势描述 ('increasing', 'decreasing', 'stable', 'volatile')
        """
        if len(historical_states) < 2:
            return "insufficient_data"
        
        values = []
        for state in historical_states[-5:]:  # 取最近5个状态
            if attribute in state.attributes:
                values.append(state.attributes[attribute])
        
        if not values or not isinstance(values[0], (int, float)):
            return "non_numeric"
        
        if len(values) < 2:
            return "stable"
        
        # 简单的线性趋势分析
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_diff = sum(diffs) / len(diffs)
        
        if avg_diff > 0.05:
            return "increasing"
        elif avg_diff < -0.05:
            return "decreasing"
        elif max(diffs) - min(diffs) > 0.2:
            return "volatile"
        else:
            return "stable"
    
    def _generate_suggestion(self, attribute: str, initial: Any, current: Any,
                           deviation: float, trend: str) -> str:
        """
        生成交互建议（辅助函数）
        
        Args:
            attribute: 属性名
            initial: 初始值
            current: 当前值
            deviation: 偏差分数
            trend: 趋势描述
            
        Returns:
            str: 建议文本
        """
        if deviation <= self.deviation_threshold:
            return "行为符合常规模式"
        
        # 映射属性名到自然语言
        attr_display = {
            "patience": "耐心程度",
            "mood": "情绪状态",
            "stress_level": "压力水平",
            "engagement": "参与度",
            "personality": "性格特质"
        }
        
        attr_name = attr_display.get(attribute, attribute)
        
        # 生成动态建议
        suggestions = []
        
        if isinstance(initial, str):
            suggestions.append(f"虽然你现在{current}，但这不符合你原本{initial}的{attr_name}")
        else:
            if current < initial:
                suggestions.append(f"你的{attr_name}从{initial:.1f}下降到{current:.1f}")
            else:
                suggestions.append(f"你的{attr_name}从{initial:.1f}上升到{current:.1f}")
        
        if trend == "increasing":
            suggestions.append("这个趋势在持续上升")
        elif trend == "decreasing":
            suggestions.append("这个趋势在持续下降")
        elif trend == "volatile":
            suggestions.append("这个指标波动较大")
        
        return "，".join(suggestions) + "。"
    
    def _calculate_initial_weights(self, attributes: Dict[str, Any]) -> Dict[str, float]:
        """计算初始属性权重"""
        return {attr: 1.0 / len(attributes) for attr in attributes}
    
    def _update_weights(self, user_id: str, changed_attributes: Dict[str, Any]) -> None:
        """更新属性权重（基于变化频率）"""
        profile = self.users[user_id]
        for attr in changed_attributes:
            profile.attribute_weights[attr] += 0.1  # 增加变化属性的权重


# 使用示例
if __name__ == "__main__":
    # 初始化系统
    system = IdentityAnchorSystem(deviation_threshold=0.35)
    
    # 创建用户档案
    user_attrs = {
        "personality": "calm",
        "patience": 0.9,
        "mood": "neutral",
        "stress_level": 0.3,
        "engagement": 0.8
    }
    system.initialize_user("user_123", user_attrs)
    
    # 模拟状态变化
    system.update_state("user_123", {"patience": 0.6}, context="minor_delay")
    system.update_state("user_123", {"patience": 0.4, "stress_level": 0.6}, 
                       context="deadline_pressure")
    system.update_state("user_123", {"patience": 0.2, "mood": "frustrated"}, 
                       context="system_crash")
    
    # 分析偏差
    analysis = system.analyze_deviation("user_123", "patience")
    print("\nPatience Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # 获取完整档案
    profile = system.get_user_profile("user_123")
    print("\nUser Profile:")
    print(f"Initial state: {profile['initial_state']['attributes']}")
    print(f"Current state: {profile['current_state']['attributes']}")
    print(f"Historical updates: {len(profile['historical_states'])}")