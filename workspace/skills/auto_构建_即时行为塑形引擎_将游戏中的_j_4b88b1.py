"""
名称: auto_构建_即时行为塑形引擎_将游戏中的_j_4b88b1
描述: 构建‘即时行为塑形引擎’。将游戏中的‘Juice’（感官反馈强化）和‘奖励时间表’（Reward Schedules，
      如变比率强化）引入教育交互。不仅仅是‘答对加分’，而是通过视觉特效、连击音效、随机稀有掉落
      （如获得稀有的知识卡片）来多巴胺化学习过程。重点在于将宏大的教育目标拆解为微小的、高频的、
      成瘾性的反馈单元，利用强化学习算法优化每个个体的最佳奖励间隔，重塑学习的神经回路。
"""

import logging
import random
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BehaviorShapingEngine")


class RewardRarity(Enum):
    """奖励稀有度枚举"""
    COMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4


class FeedbackType(Enum):
    """反馈类型枚举"""
    VISUAL = "visual"
    AUDIO = "audio"
    HAPTIC = "haptic"
    POINTS = "points"
    ITEM = "item"


@dataclass
class UserProfile:
    """用户画像数据结构"""
    user_id: str
    engagement_score: float = 0.0  # 参与度评分 [0, 1]
    reward_sensitivity: float = 0.5  # 奖励敏感度 [0, 1]
    current_streak: int = 0  # 当前连击数
    last_interaction_time: datetime = field(default_factory=datetime.now)
    total_interactions: int = 0  # 总交互次数
    historical_rewards: List[Dict] = field(default_factory=list)


@dataclass
class RewardConfig:
    """奖励配置"""
    base_points: int = 10
    streak_multiplier: float = 1.5
    max_streak: int = 100
    vr_schedule_ratio: int = 5  # 变比率强化(VR)的平均比率
    legendary_drop_rate: float = 0.01  # 传说级物品掉落率


class ImmediateBehaviorShapingEngine:
    """
    即时行为塑形引擎
    
    将游戏化反馈机制应用于教育交互，通过多巴胺驱动的反馈循环增强学习动力。
    
    核心功能:
    1. 实时反馈生成 (视觉、听觉、触觉)
    2. 基于强化学习的奖励调度 (变比率强化)
    3. 动态奖励间隔优化
    4. 连击系统与稀有掉落机制
    
    使用示例:
    >>> engine = ImmediateBehaviorShapingEngine()
    >>> user = UserProfile(user_id="student_123")
    >>> feedback = engine.generate_immediate_feedback(user, is_correct=True)
    >>> print(feedback)
    """
    
    def __init__(self, config: Optional[RewardConfig] = None):
        """
        初始化引擎
        
        Args:
            config: 奖励配置对象，如果为None则使用默认配置
        """
        self.config = config or RewardConfig()
        self._initialize_reward_pool()
        logger.info("Behavior Shaping Engine initialized with config: %s", 
                   json.dumps(self.config.__dict__, indent=2))
    
    def _initialize_reward_pool(self) -> None:
        """初始化奖励池"""
        self.reward_pool = {
            RewardRarity.COMMON: [
                {"type": FeedbackType.POINTS, "value": self.config.base_points},
                {"type": FeedbackType.VISUAL, "value": "sparkle"},
                {"type": FeedbackType.AUDIO, "value": "ding"},
            ],
            RewardRarity.RARE: [
                {"type": FeedbackType.ITEM, "value": "knowledge_card_common"},
                {"type": FeedbackType.POINTS, "value": self.config.base_points * 2},
            ],
            RewardRarity.EPIC: [
                {"type": FeedbackType.ITEM, "value": "knowledge_card_rare"},
                {"type": FeedbackType.VISUAL, "value": "firework"},
            ],
            RewardRarity.LEGENDARY: [
                {"type": FeedbackType.ITEM, "value": "knowledge_card_legendary"},
                {"type": FeedbackType.VISUAL, "value": "golden_explosion"},
            ]
        }
    
    def _determine_reward_rarity(self, user: UserProfile) -> RewardRarity:
        """
        确定奖励稀有度 (辅助函数)
        
        基于变比率强化(VR)调度和用户历史数据确定当前奖励的稀有度
        
        Args:
            user: 用户画像
            
        Returns:
            RewardRarity: 确定的奖励稀有度
        """
        # 变比率强化逻辑
        if random.random() < self.config.legendary_drop_rate * (1 + user.reward_sensitivity):
            return RewardRarity.LEGENDARY
        
        # 基于参与度和连击数调整稀有度概率
        rarity_roll = random.random()
        engagement_factor = user.engagement_score * 0.3
        streak_factor = min(user.current_streak / self.config.max_streak, 1.0) * 0.2
        
        if rarity_roll < 0.6 - engagement_factor - streak_factor:
            return RewardRarity.COMMON
        elif rarity_roll < 0.85 - engagement_factor:
            return RewardRarity.RARE
        else:
            return RewardRarity.EPIC
    
    def generate_immediate_feedback(
        self,
        user: UserProfile,
        is_correct: bool,
        response_time_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成即时反馈 (核心函数1)
        
        基于用户行为和上下文生成多维度的即时反馈
        
        Args:
            user: 用户画像
            is_correct: 回答是否正确
            response_time_ms: 响应时间(毫秒)，用于调整反馈强度
            
        Returns:
            Dict: 包含各类反馈的字典
            
        Raises:
            ValueError: 如果用户数据无效
        """
        if not isinstance(user, UserProfile):
            raise ValueError("Invalid user profile type")
        
        if user.engagement_score < 0 or user.engagement_score > 1:
            logger.warning("Engagement score out of bounds, clamping to [0, 1]")
            user.engagement_score = max(0, min(1, user.engagement_score))
        
        feedback_package = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user.user_id,
            "feedback_events": [],
            "points_earned": 0,
            "streak_bonus": False,
            "rewards": []
        }
        
        if is_correct:
            # 更新连击
            user.current_streak += 1
            user.total_interactions += 1
            
            # 计算基础分数
            base_points = self.config.base_points
            streak_multiplier = 1 + (user.current_streak * 0.1 * self.config.streak_multiplier)
            streak_multiplier = min(streak_multiplier, 5.0)  # 上限5倍
            total_points = int(base_points * streak_multiplier)
            
            # 响应时间加成
            if response_time_ms and response_time_ms < 3000:  # 快速回答
                speed_bonus = 1 + (3000 - response_time_ms) / 10000
                total_points = int(total_points * speed_bonus)
                feedback_package["feedback_events"].append({
                    "type": FeedbackType.VISUAL.value,
                    "data": "speed_bonus_effect",
                    "intensity": speed_bonus
                })
            
            feedback_package["points_earned"] = total_points
            feedback_package["streak_bonus"] = user.current_streak > 1
            
            # 添加基础反馈
            feedback_package["feedback_events"].extend([
                {"type": FeedbackType.AUDIO.value, "data": "correct_ding"},
                {"type": FeedbackType.VISUAL.value, "data": "green_pulse"},
            ])
            
            # 连击特效
            if user.current_streak >= 3:
                feedback_package["feedback_events"].append({
                    "type": FeedbackType.VISUAL.value,
                    "data": f"streak_{min(user.current_streak, 10)}_effect",
                    "intensity": min(user.current_streak / 10, 1.0)
                })
                feedback_package["feedback_events"].append({
                    "type": FeedbackType.AUDIO.value,
                    "data": f"streak_{min(user.current_streak, 10)}_sound"
                })
            
            # 确定并添加稀有奖励
            rarity = self._determine_reward_rarity(user)
            reward = random.choice(self.reward_pool[rarity])
            reward_copy = reward.copy()
            reward_copy["rarity"] = rarity.name
            feedback_package["rewards"].append(reward_copy)
            
            # 记录到历史
            user.historical_rewards.append({
                "timestamp": datetime.now().isoformat(),
                "rarity": rarity.name,
                "reward": reward_copy
            })
            
            # 更新参与度评分 (指数移动平均)
            user.engagement_score = user.engagement_score * 0.9 + 0.1 * min(1.0, user.current_streak / 10)
            
        else:
            # 错误回答的反馈
            user.current_streak = 0
            user.total_interactions += 1
            
            feedback_package["feedback_events"] = [
                {"type": FeedbackType.AUDIO.value, "data": "gentle_buzz"},
                {"type": FeedbackType.VISUAL.value, "data": "shake_effect"},
                {"type": FeedbackType.HAPTIC.value, "data": "light_vibration"}
            ]
            
            # 降低参与度评分
            user.engagement_score = user.engagement_score * 0.95
        
        user.last_interaction_time = datetime.now()
        
        logger.debug("Generated feedback for user %s: %s", user.user_id, feedback_package)
        return feedback_package
    
    def optimize_reward_schedule(self, user: UserProfile) -> Dict[str, Any]:
        """
        优化奖励调度 (核心函数2)
        
        基于强化学习原理为个体用户计算最佳奖励间隔和强化策略
        
        Args:
            user: 用户画像
            
        Returns:
            Dict: 包含优化后的调度参数
        """
        if not isinstance(user, UserProfile):
            raise ValueError("Invalid user profile type")
        
        # 分析历史奖励模式
        recent_rewards = user.historical_rewards[-20:] if user.historical_rewards else []
        
        # 计算平均奖励间隔 (简化版强化学习优化)
        if len(recent_rewards) >= 2:
            intervals = []
            for i in range(1, len(recent_rewards)):
                t1 = datetime.fromisoformat(recent_rewards[i-1]["timestamp"])
                t2 = datetime.fromisoformat(recent_rewards[i]["timestamp"])
                intervals.append((t2 - t1).total_seconds())
            
            avg_interval = sum(intervals) / len(intervals) if intervals else 60.0
        else:
            avg_interval = 60.0  # 默认60秒
        
        # 基于用户敏感度调整变比率
        optimal_vr_ratio = max(3, min(10, int(
            self.config.vr_schedule_ratio * (1 + user.reward_sensitivity - 0.5)
        )))
        
        # 动态调整掉落率
        legendary_rate = self.config.legendary_drop_rate
        if user.engagement_score < 0.3:
            # 低参与度用户增加掉落率
            legendary_rate *= 2
        elif user.engagement_score > 0.7:
            # 高参与度用户维持标准掉落率
            pass
        
        schedule = {
            "user_id": user.user_id,
            "optimal_reward_interval_sec": avg_interval * (1 - user.engagement_score * 0.3),
            "vr_schedule_ratio": optimal_vr_ratio,
            "adjusted_legendary_rate": legendary_rate,
            "engagement_zone": "high" if user.engagement_score > 0.7 else 
                              "medium" if user.engagement_score > 0.3 else "low",
            "recommended_action": self._get_recommended_action(user),
            "next_big_reward_in": int(avg_interval * optimal_vr_ratio)
        }
        
        logger.info("Optimized reward schedule for user %s: %s", user.user_id, schedule)
        return schedule
    
    def _get_recommended_action(self, user: UserProfile) -> str:
        """
        获取推荐行动 (辅助函数)
        
        基于用户当前状态推荐干预策略
        """
        if user.current_streak == 0 and user.total_interactions > 5:
            return "offer_bonus_challenge"  # 提供额外挑战恢复信心
        elif user.engagement_score < 0.3:
            return "increase_reward_frequency"  # 增加奖励频率
        elif user.current_streak > 10:
            return "introduce_special_event"  # 引入特殊事件
        else:
            return "maintain_current_flow"  # 维持当前节奏
    
    def export_user_data(self, user: UserProfile) -> str:
        """
        导出用户数据为JSON格式
        
        Args:
            user: 用户画像
            
        Returns:
            str: JSON格式的用户数据
        """
        data = {
            "user_id": user.user_id,
            "engagement_score": user.engagement_score,
            "reward_sensitivity": user.reward_sensitivity,
            "current_streak": user.current_streak,
            "total_interactions": user.total_interactions,
            "last_interaction": user.last_interaction_time.isoformat(),
            "historical_rewards": user.historical_rewards
        }
        return json.dumps(data, indent=2)


# 使用示例
if __name__ == "__main__":
    # 初始化引擎
    engine = ImmediateBehaviorShapingEngine()
    
    # 创建用户
    student = UserProfile(user_id="student_001", reward_sensitivity=0.7)
    
    # 模拟学习交互
    print("=== 模拟学习交互 ===")
    for i in range(5):
        is_correct = random.random() > 0.3  # 70%正确率
        response_time = random.randint(1000, 5000)
        
        feedback = engine.generate_immediate_feedback(
            student, 
            is_correct=is_correct,
            response_time_ms=response_time
        )
        
        print(f"\n交互 {i+1}:")
        print(f"  正确: {is_correct}")
        print(f"  连击: {student.current_streak}")
        print(f"  获得分数: {feedback['points_earned']}")
        if feedback['rewards']:
            print(f"  获得奖励: {feedback['rewards'][0]['value']} ({feedback['rewards'][0]['rarity']})")
    
    # 优化奖励调度
    print("\n=== 优化奖励调度 ===")
    schedule = engine.optimize_reward_schedule(student)
    print(f"推荐奖励间隔: {schedule['optimal_reward_interval_sec']:.1f}秒")
    print(f"变比率: VR-{schedule['vr_schedule_ratio']}")
    print(f"参与度区域: {schedule['engagement_zone']}")
    print(f"推荐行动: {schedule['recommended_action']}")
    
    # 导出用户数据
    print("\n=== 用户数据导出 ===")
    print(engine.export_user_data(student))