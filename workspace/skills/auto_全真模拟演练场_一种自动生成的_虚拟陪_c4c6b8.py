"""
Module: auto_全真模拟演练场_一种自动生成的_虚拟陪_c4c6b8
Description: 【全真模拟演练场】一种自动生成的'虚拟陪练'系统。
             针对人类用户的学习目标（如'处理客户投诉'），利用LLM生成极具攻击性、
             情绪化、逻辑陷阱的'虚拟客户'。系统根据用户的应对（输入），实时评估其
             技能水平，并动态调整虚拟环境的难度，形成'刻意练习'闭环。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DifficultyLevel(Enum):
    """模拟难度的枚举类"""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4

@dataclass
class UserProfile:
    """用户画像数据结构"""
    user_id: str
    target_skill: str  # 例如: "处理客户投诉"
    current_difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    history_scores: List[float] = field(default_factory=list)
    session_start_time: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class SimulationState:
    """模拟演练的当前状态"""
    turn_count: int = 0
    last_user_input: str = ""
    last_ai_response: str = ""
    current_score: float = 0.0
    is_active: bool = True

class VirtualSparringSystem:
    """
    虚拟陪练系统核心类。
    
    负责管理模拟环境、生成交互内容、评估用户反馈及动态调整难度。
    """

    def __init__(self, model_config: Optional[Dict] = None):
        """
        初始化系统。
        
        Args:
            model_config (Optional[Dict]): LLM模型配置，如果为None则使用模拟模式。
        """
        self.model_config = model_config if model_config else {"mode": "mock"}
        self.active_sessions: Dict[str, SimulationState] = {}
        logger.info("Virtual Sparring System initialized with config: %s", self.model_config)

    def _validate_user_input(self, user_input: str) -> bool:
        """
        辅助函数：验证用户输入的合法性和安全性。
        
        Args:
            user_input (str): 用户的原始输入文本。
            
        Returns:
            bool: 如果输入有效返回True，否则返回False。
        """
        if not user_input or not isinstance(user_input, str):
            logger.warning("Input validation failed: Empty or non-string input.")
            return False
        
        # 简单的长度边界检查
        if len(user_input) > 2000:
            logger.warning("Input validation failed: Input exceeds length limit.")
            return False
            
        # 这里可以添加注入攻击检测等安全逻辑
        # 例如检测SQL注入或Prompt注入的简单特征
        dangerous_patterns = ["--", "; DROP", "IGNORE PREVIOUS"]
        if any(pattern in user_input.upper() for pattern in dangerous_patterns):
            logger.warning("Input validation failed: Potentially malicious content detected.")
            return False
            
        return True

    def initialize_session(self, user_profile: UserProfile) -> str:
        """
        核心函数1: 初始化一个新的模拟演练会话。
        
        根据用户目标生成初始场景设定。
        
        Args:
            user_profile (UserProfile): 包含目标和难度设置的用户数据。
            
        Returns:
            str: 虚拟环境生成的开场白或场景描述。
            
        Raises:
            ValueError: 如果用户目标无效。
        """
        if not user_profile.target_skill:
            raise ValueError("Target skill cannot be empty.")
            
        session_id = f"session_{user_profile.user_id}_{datetime.now().timestamp()}"
        self.active_sessions[session_id] = SimulationState()
        
        logger.info(f"Session initialized for user {user_profile.user_id}. Target: {user_profile.target_skill}")
        
        # 根据难度生成开场白
        # 在实际应用中，这里会调用LLM生成
        opening_line = (
            f"[系统] 模拟开始。目标：{user_profile.target_skill}。"
            f"当前难度：{user_profile.current_difficulty.name}。\n"
            f"[客户] (语气急躁) 喂？是你们负责售后的吗？我要投诉！你们的产品简直太糟糕了！"
        )
        
        return opening_line

    def process_user_response(
        self, 
        session_id: str, 
        user_input: str, 
        user_profile: UserProfile
    ) -> Tuple[str, float, DifficultyLevel]:
        """
        核心函数2: 处理用户输入，进行评估并生成下一轮反馈。
        
        这是'刻意练习'闭环的核心。
        
        Args:
            session_id (str): 会话ID。
            user_input (str): 用户的回复内容。
            user_profile (UserProfile): 用户画像，用于难度调整逻辑。
            
        Returns:
            Tuple[str, float, DifficultyLevel]: 
                - 虚拟客户的下一句回复
                - 本轮得分 (0.0 - 100.0)
                - 建议的下一轮难度
        """
        if session_id not in self.active_sessions:
            logger.error(f"Session {session_id} not found.")
            return "[系统错误] 会话已过期。", 0.0, user_profile.current_difficulty

        if not self._validate_user_input(user_input):
            return "[系统] 输入包含无效内容，请重新输入。", 0.0, user_profile.current_difficulty

        state = self.active_sessions[session_id]
        state.turn_count += 1
        state.last_user_input = user_input
        
        # 1. 实时评估
        current_score = self._evaluate_response_quality(user_input, user_profile.target_skill)
        state.current_score = current_score
        user_profile.history_scores.append(current_score)
        
        # 2. 动态调整难度
        new_difficulty = self._adjust_difficulty(user_profile)
        user_profile.current_difficulty = new_difficulty
        
        # 3. 生成虚拟客户回复
        # 这里使用Mock逻辑，实际需接入LLM API
        next_response = self._generate_adversarial_response(
            user_input, 
            current_score, 
            new_difficulty
        )
        state.last_ai_response = next_response
        
        logger.info(f"Turn {state.turn_count}: Score {current_score}, Difficulty adjusted to {new_difficulty.name}")
        
        return next_response, current_score, new_difficulty

    def _evaluate_response_quality(self, user_input: str, target_skill: str) -> float:
        """
        辅助函数：评估用户回复的质量。
        
        逻辑：基于关键词匹配和长度（Mock逻辑）。
        实际生产中应使用LLM进行语义理解评分。
        
        Args:
            user_input (str): 用户输入
            target_skill (str): 目标技能
            
        Returns:
            float: 分数 (0-100)
        """
        score = 50.0  # 基础分
        
        # 模拟逻辑：检测是否包含专业词汇
        professional_keywords = ["理解", "抱歉", "解决方案", "核实", "马上"]
        positive_count = sum(1 for word in professional_keywords if word in user_input)
        score += positive_count * 10
        
        # 检测是否包含攻击性词汇（扣分）
        negative_keywords = ["笨蛋", "不对", "闭嘴", "不知道"]
        negative_count = sum(1 for word in negative_keywords if word in user_input)
        score -= negative_count * 20
        
        # 边界检查
        return max(0.0, min(100.0, score))

    def _adjust_difficulty(self, profile: UserProfile) -> DifficultyLevel:
        """
        辅助函数：根据历史表现动态调整难度。
        
        逻辑：
        - 如果最近3次平均分 > 80，提升难度
        - 如果最近3次平均分 < 50，降低难度
        """
        current = profile.current_difficulty.value
        history = profile.history_scores
        
        if len(history) < 3:
            return profile.current_difficulty
            
        recent_avg = sum(history[-3:]) / 3
        
        new_level = current
        if recent_avg > 80 and current < 4:
            new_level = current + 1
            logger.info(f"User performance high ({recent_avg}). Increasing difficulty.")
        elif recent_avg < 50 and current > 1:
            new_level = current - 1
            logger.info(f"User performance low ({recent_avg}). Decreasing difficulty.")
            
        return DifficultyLevel(new_level)

    def _generate_adversarial_response(
        self, 
        user_input: str, 
        score: float, 
        difficulty: DifficultyLevel
    ) -> str:
        """
        生成对抗性的虚拟客户回复（Mock实现）。
        
        根据用户得分和难度生成不同情绪强度的回复。
        """
        if difficulty == DifficultyLevel.EXPERT:
            return (
                "[客户] (情绪极度激动，语速极快) 你说的这些我都听过了！"
                "全是借口！如果今天不给我退款，我马上发推特曝光你们公司！"
                "别跟我提什么规定，那是你们的事！"
            )
        elif difficulty == DifficultyLevel.HARD:
            return "[客户] (不耐烦) 稍等，你刚才说的逻辑有问题。如果是那样，为什么说明书上没写？你是不是在忽悠我？"
        elif difficulty == DifficultyLevel.MEDIUM:
            return "[客户] (怀疑) 哎，你说的听起来是有道理，但我还是很担心。如果修不好怎么办？"
        else:
            return "[客户] (稍微平静) 嗯...好吧，听起来你好像确实想帮我。那你说第一步该怎么做？"

# Example Usage
if __name__ == "__main__":
    # 1. 初始化系统
    system = VirtualSparringSystem(model_config={"provider": "mock_llm"})
    
    # 2. 创建用户画像
    user = UserProfile(
        user_id="user_123",
        target_skill="处理愤怒客户的投诉",
        current_difficulty=DifficultyLevel.MEDIUM
    )
    
    try:
        # 3. 开始会话
        print("--- 初始化会话 ---")
        opening = system.initialize_session(user)
        print(opening)
        
        # 4. 模拟第一轮交互
        print("\n--- 第一轮交互 (用户尝试安抚) ---")
        response_1, score_1, diff_1 = system.process_user_response(
            f"session_{user.user_id}_", 
            "您好，非常抱歉听到您有这样的体验。我完全理解您的焦急。请问具体是什么问题呢？", 
            user
        )
        print(f"得分: {score_1}")
        print(f"新难度: {diff_1.name}")
        print(f"客户回复: {response_1}")
        
        # 5. 模拟第二轮交互 (表现不佳)
        print("\n--- 第二轮交互 (用户表现不耐烦) ---")
        response_2, score_2, diff_2 = system.process_user_response(
            f"session_{user.user_id}_", 
            "这个我也没办法，这是规定。你能不能冷静点说话？", 
            user
        )
        print(f"得分: {score_2}")
        print(f"新难度: {diff_2.name}")
        print(f"客户回复: {response_2}")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")