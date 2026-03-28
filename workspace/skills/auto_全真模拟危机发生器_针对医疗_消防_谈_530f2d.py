"""
全真模拟危机发生器

该模块提供了一个针对医疗、消防、谈判等高风险技能的AI陪练系统。
它利用大语言模型(LLM)根据用户的弱点生成极具迷惑性的'对抗性场景'，
并根据用户的实时反馈（如微表情、语调）动态调整攻击策略。

版本: 1.0.0
作者: AGI System Core Engineer
"""

import logging
import json
import random
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DomainType(Enum):
    """支持的领域类型枚举"""
    MEDICAL = "medical"
    FIREFIGHTING = "firefighting"
    NEGOTIATION = "negotiation"
    PUBLIC_SAFETY = "public_safety"

class EmotionalState(Enum):
    """用户情绪状态枚举"""
    CALM = "calm"
    ANXIOUS = "anxious"
    AGGRESSIVE = "aggressive"
    CONFUSED = "confused"
    PANICKED = "panicked"

@dataclass
class UserProfile:
    """用户画像数据结构"""
    user_id: str
    domain: DomainType
    historical_weaknesses: List[str] = field(default_factory=list)
    stress_threshold: float = 0.7  # 压力阈值 (0.0 - 1.0)
    current_stress_level: float = 0.0

@dataclass
class BiometricInput:
    """模拟的生物特征输入（如微表情、语调）"""
    voice_tremble_frequency: float = 0.0  # Hz
    heart_rate: int = 75  # BPM
    eye_contact_duration: float = 1.0  # seconds
    speech_pace: float = 1.0  # relative speed (1.0 is normal)

    def calculate_stress_indicator(self) -> float:
        """计算综合压力指标"""
        score = 0.0
        # 简单的启发式压力计算
        if self.heart_rate > 100:
            score += (self.heart_rate - 100) / 50
        if self.voice_tremble_frequency > 5.0:
            score += 0.3
        if self.speech_pace > 1.5 or self.speech_pace < 0.7:
            score += 0.2
        
        return min(max(score, 0.0), 1.0) # Normalize to [0, 1]

class CrisisSimulator:
    """
    全真模拟危机发生器核心类。
    
    负责管理模拟会话、生成对抗性场景以及动态调整难度。
    """

    def __init__(self, llm_config: Optional[Dict[str, str]] = None):
        """
        初始化模拟器。
        
        Args:
            llm_config (Optional[Dict[str, str]]): 大模型配置，包含API keys等。
        """
        self.llm_config = llm_config or {"model": "default_agi_core_v1"}
        self.active_sessions: Dict[str, Dict] = {}
        logger.info("CrisisSimulator initialized with config: %s", self.llm_config)

    def _validate_user_input(self, user_input: str) -> bool:
        """
        辅助函数：验证用户输入的安全性，防止提示词注入。
        
        Args:
            user_input (str): 用户的原始文本输入。
            
        Returns:
            bool: 如果输入安全则返回True。
        """
        if not user_input or len(user_input) > 2000:
            logger.warning("Input validation failed: Empty or too long.")
            return False
        
        forbidden_patterns = ["ignore previous", "system override", "hack"]
        if any(pattern in user_input.lower() for pattern in forbidden_patterns):
            logger.warning("Potential injection detected.")
            return False
            
        return True

    def initialize_session(self, user_profile: UserProfile) -> str:
        """
        初始化一个新的模拟训练会话。
        
        Args:
            user_profile (UserProfile): 用户画像对象。
            
        Returns:
            str: 会话ID。
        """
        session_id = f"sess_{random.randint(10000, 99999)}"
        
        # 根据领域加载基础场景
        base_scenario = self._generate_base_scenario(user_profile.domain)
        
        self.active_sessions[session_id] = {
            "profile": user_profile,
            "history": [],
            "current_state": base_scenario,
            "intensity": 0.5
        }
        
        logger.info(f"Session {session_id} initialized for user {user_profile.user_id} in domain {user_profile.domain.value}")
        return session_id

    def _generate_base_scenario(self, domain: DomainType) -> str:
        """辅助函数：生成基础场景描述"""
        scenarios = {
            DomainType.MEDICAL: "你在急诊室接收一名多重创伤患者，生命体征不稳定。",
            DomainType.FIREFIGHTING: "商场二楼发生火灾，能见度极低，有被困儿童哭声。",
            DomainType.NEGOTIATION: "一名绑匪挟持人质在屋顶，情绪极其不稳定。"
        }
        return scenarios.get(domain, "通用危机场景")

    def generate_adversarial_response(
        self, 
        session_id: str, 
        user_action: str, 
        biometrics: BiometricInput
    ) -> Tuple[str, EmotionalState, float]:
        """
        核心函数：生成对抗性的AI回复。
        
        根据用户的操作和生物特征反馈，利用LLM生成针对用户弱点的回复。
        
        Args:
            session_id (str): 活动会话ID。
            user_action (str): 用户采取的行动或说的话。
            biometrics (BiometricInput): 实时生物特征数据。
            
        Returns:
            Tuple[str, EmotionalState, float]: 
                - AI的对抗性回复/场景描述
                - 推断的用户情绪状态
                - 当前的危机强度等级 (0.0-1.0)
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found.")
        
        if not self._validate_user_input(user_action):
            return "系统错误：无效输入。", EmotionalState.CALM, 0.0

        session = self.active_sessions[session_id]
        profile = session["profile"]
        
        # 1. 分析生物特征，计算压力
        stress_indicator = biometrics.calculate_stress_indicator()
        profile.current_stress_level = (profile.current_stress_level + stress_indicator) / 2
        inferred_emotion = self._infer_emotion(biometrics, profile.current_stress_level)
        
        logger.debug(f"User stress: {profile.current_stress_level}, Emotion: {inferred_emotion}")

        # 2. 动态调整策略 (对抗性逻辑)
        # 如果用户表现出弱点（压力过大），AI针对性地增加难度或攻击软肋
        # 如果用户处理得当，AI引入突发变量
        
        response = ""
        new_intensity = session["intensity"]
        
        # 模拟LLM生成的对抗性逻辑 (这里用规则模拟AGI的决策过程)
        if profile.current_stress_level > profile.stress_threshold:
            # 针对弱点攻击
            new_intensity = min(1.0, session["intensity"] + 0.2)
            weakness = random.choice(profile.historical_weaknesses) if profile.historical_weaknesses else "决策犹豫"
            response = self._generate_attack_vector(profile.domain, user_action, weakness, inferred_emotion)
            logger.info(f"Adversarial attack triggered on weakness: {weakness}")
        else:
            # 常规推进或突发变量
            response = self._generate_standard_progression(profile.domain, user_action)
            
        session["history"].append({"user": user_action, "ai": response})
        session["intensity"] = new_intensity
        
        return response, inferred_emotion, new_intensity

    def _infer_emotion(self, biometrics: BiometricInput, stress_level: float) -> EmotionalState:
        """
        辅助函数：推断用户情绪状态。
        """
        if stress_level > 0.8 or biometrics.heart_rate > 130:
            return EmotionalState.PANICKED
        elif biometrics.voice_tremble_frequency > 6.0:
            return EmotionalState.ANXIOUS
        elif biometrics.speech_pace > 1.4:
            return EmotionalState.AGGRESSIVE
        elif stress_level < 0.3:
            return EmotionalState.CALM
        else:
            return EmotionalState.CONFUSED

    def _generate_attack_vector(
        self, 
        domain: DomainType, 
        user_action: str, 
        weakness: str, 
        emotion: EmotionalState
    ) -> str:
        """
        核心函数：构建针对弱点的攻击向量（生成对抗性文本）。
        
        在真实AGI场景中，这里会调用LLM生成。
        """
        templates = {
            DomainType.NEGOTIATION: {
                EmotionalState.PANICKED: f"对手注意到了你的颤抖，大声吼道：‘你根本不知道自己在做什么！看着你的眼睛我就知道你怕了！’ (针对: {weakness})",
                EmotionalState.ANXIOUS: f"对手突然改变了语调，冷笑着逼近一步：‘你在发抖吗？如果你的手抖得这么厉害，怎么保证我的安全？’ (针对: {weakness})",
            },
            DomainType.MEDICAL: {
                EmotionalState.CONFUSED: f"监护仪突然报警，患者血压骤降！护士惊慌地喊道：‘医生，血库没有血了！现在怎么办？’ (针对: {weakness})",
            }
        }
        # 默认返回
        return templates.get(domain, {}).get(emotion, f"情况突然恶化，针对你的'{weakness}'，环境变得更加恶劣。")

    def _generate_standard_progression(self, domain: DomainType, user_action: str) -> str:
        """常规剧情推进"""
        return f"你的行动 '{user_action[:20]}...' 产生了一定效果，但危机尚未解除，对方正在重新评估局势。"

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化系统
    simulator = CrisisSimulator()
    
    # 2. 创建用户画像
    # 假设该用户在谈判中容易受到时间压力的影响
    user = UserProfile(
        user_id="agent_007",
        domain=DomainType.NEGOTIATION,
        historical_weaknesses=["时间压力下的决断力", "面对攻击性语言的情绪控制"],
        stress_threshold=0.6
    )
    
    # 3. 开始会话
    session_id = simulator.initialize_session(user)
    print(f"--- Session Started: {session_id} ---")
    
    # 4. 模拟第一轮交互 (用户状态较好)
    bio_input_1 = BiometricInput(heart_rate=80, speech_pace=1.0)
    response_1, emotion_1, intensity_1 = simulator.generate_adversarial_response(
        session_id, 
        "我们是来帮助你的，请先冷静下来。", 
        bio_input_1
    )
    print(f"AI Response: {response_1}")
    print(f"Detected Emotion: {emotion_1.value}, Intensity: {intensity_1}\n")
    
    # 5. 模拟第二轮交互 (用户表现出现焦虑，触发了对抗性生成)
    # 模拟生物特征：心率升高，声音颤抖
    bio_input_2 = BiometricInput(heart_rate=115, voice_tremble_frequency=6.5, speech_pace=0.8)
    response_2, emotion_2, intensity_2 = simulator.generate_adversarial_response(
        session_id, 
        "呃...请不要冲动，我们需要...需要时间...", 
        bio_input_2
    )
    print(f"AI Response (Adversarial): {response_2}")
    print(f"Detected Emotion: {emotion_2.value}, Intensity: {intensity_2}")