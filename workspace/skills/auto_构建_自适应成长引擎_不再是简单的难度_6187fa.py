"""
Module: auto_构建_自适应成长引擎_不再是简单的难度_6187fa
Description: 构建自适应成长引擎。基于多模态数据实时解构用户认知负荷。
             包含认知状态管理、动态难度调整及信息呈现优化功能。
Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class CognitiveState(Enum):
    """用户认知状态枚举"""
    FLOW = auto()          # 心流状态：高效学习
    FATIGUE = auto()       # 疲劳：效率下降
    OVERLOAD = auto()      # 认知过载：需立即干预
    BORED = auto()         # 厌倦：需要提升挑战


class PresentationMode(Enum):
    """信息呈现模式"""
    ABSTRACT = "abstract"         # 抽象模式（纯文本/公式）
    CONCRETE = "concrete"         # 具体形象模式（可视化辅助）
    SCAFFOLDED = "scaffolded"     # 脚手架模式（分步引导）


@dataclass
class MultiModalData:
    """多模态输入数据结构"""
    eye_movement_stability: float  # 眼动稳定性 [0.0, 1.0]
    operation_delay: float         # 操作延迟 (秒)
    error_rate: float              # 错误率 [0.0, 1.0]
    timestamp: float = time.time() # 时间戳

    def validate(self) -> bool:
        """验证数据有效性"""
        return all([
            0.0 <= self.eye_movement_stability <= 1.0,
            0.0 <= self.error_rate <= 1.0,
            self.operation_delay >= 0
        ])


@dataclass
class CognitiveProfile:
    """用户认知画像"""
    current_state: CognitiveState
    cognitive_load: float          # 认知负荷指数 [0.0, 1.0]
    recommended_mode: PresentationMode
    scaffold_strength: float       # 脚手架强度 [0.0, 1.0]
    difficulty_adjustment: float   # 难度调整系数 [-1.0, 1.0]


class AdaptiveGrowthEngine:
    """自适应成长引擎
    
    功能：
    1. 实时分析多模态数据评估认知状态
    2. 动态调整难度和呈现方式
    3. 提供认知状态管理和干预建议
    
    示例：
        >>> engine = AdaptiveGrowthEngine()
        >>> data = MultiModalData(0.75, 2.5, 0.3)
        >>> profile = engine.analyze_cognitive_state(data)
        >>> print(f"当前状态: {profile.current_state.name}")
    """
    
    def __init__(self, sensitivity: float = 0.7):
        """
        初始化引擎
        
        Args:
            sensitivity: 敏感度参数 [0.0, 1.0]
        """
        self._validate_sensitivity(sensitivity)
        self.sensitivity = sensitivity
        self._history: List[MultiModalData] = []
        logger.info("AdaptiveGrowthEngine initialized with sensitivity %.2f", sensitivity)
    
    def _validate_sensitivity(self, sensitivity: float) -> None:
        """验证敏感度参数"""
        if not 0 <= sensitivity <= 1:
            raise ValueError("Sensitivity must be between 0 and 1")
    
    def analyze_cognitive_state(self, data: MultiModalData) -> CognitiveProfile:
        """
        分析用户认知状态
        
        Args:
            data: 多模态输入数据
            
        Returns:
            CognitiveProfile: 包含状态分析和调整建议
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not data.validate():
            error_msg = "Invalid multimodal data detected"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self._history.append(data)
        if len(self._history) > 10:
            self._history.pop(0)
        
        # 计算认知负荷指数
        cognitive_load = self._calculate_cognitive_load(data)
        
        # 确定认知状态
        state = self._determine_cognitive_state(cognitive_load)
        
        # 确定呈现模式和脚手架强度
        mode, scaffold = self._determine_presentation_strategy(state, cognitive_load)
        
        # 计算难度调整
        difficulty_adj = self._calculate_difficulty_adjustment(state, cognitive_load)
        
        profile = CognitiveProfile(
            current_state=state,
            cognitive_load=cognitive_load,
            recommended_mode=mode,
            scaffold_strength=scaffold,
            difficulty_adjustment=difficulty_adj
        )
        
        logger.info("Analyzed cognitive state: %s (load=%.2f)", state.name, cognitive_load)
        return profile
    
    def _calculate_cognitive_load(self, data: MultiModalData) -> float:
        """
        计算认知负荷指数
        
        综合考虑眼动稳定性、操作延迟和错误率
        使用加权平均模型
        """
        weights = {
            'eye': 0.4,
            'delay': 0.3,
            'error': 0.3
        }
        
        # 标准化操作延迟 (假设5秒以上为最高负荷)
        normalized_delay = min(data.operation_delay / 5.0, 1.0)
        
        load = (
            weights['eye'] * (1 - data.eye_movement_stability) +
            weights['delay'] * normalized_delay +
            weights['error'] * data.error_rate
        )
        
        # 应用敏感度调整
        load = load * (0.8 + 0.4 * self.sensitivity)
        return min(max(load, 0.0), 1.0)  # 确保在[0,1]范围内
    
    def _determine_cognitive_state(self, cognitive_load: float) -> CognitiveState:
        """根据认知负荷确定状态"""
        if cognitive_load < 0.3:
            return CognitiveState.BORED
        elif 0.3 <= cognitive_load < 0.6:
            return CognitiveState.FLOW
        elif 0.6 <= cognitive_load < 0.8:
            return CognitiveState.FATIGUE
        else:
            return CognitiveState.OVERLOAD
    
    def _determine_presentation_strategy(
        self, 
        state: CognitiveState, 
        load: float
    ) -> Tuple[PresentationMode, float]:
        """确定信息呈现策略"""
        if state == CognitiveState.OVERLOAD:
            return (PresentationMode.CONCRETE, 0.8)
        elif state == CognitiveState.FATIGUE:
            return (PresentationMode.SCAFFOLDED, 0.6)
        elif state == CognitiveState.FLOW:
            return (PresentationMode.ABSTRACT, 0.3)
        else:  # BORED
            return (PresentationMode.ABSTRACT, 0.1)
    
    def _calculate_difficulty_adjustment(
        self, 
        state: CognitiveState, 
        load: float
    ) -> float:
        """计算难度调整系数"""
        if state == CognitiveState.OVERLOAD:
            return -0.4  # 大幅降低难度
        elif state == CognitiveState.FATIGUE:
            return -0.2
        elif state == CognitiveState.BORED:
            return 0.3   # 增加挑战
        else:  # FLOW
            return 0.1   # 小幅增加
    
    def get_historical_trend(self) -> Dict[str, float]:
        """获取历史趋势分析"""
        if not self._history:
            return {}
            
        avg_eye = sum(d.eye_movement_stability for d in self._history) / len(self._history)
        avg_delay = sum(d.operation_delay for d in self._history) / len(self._history)
        avg_error = sum(d.error_rate for d in self._history) / len(self._history)
        
        return {
            'avg_eye_stability': avg_eye,
            'avg_operation_delay': avg_delay,
            'avg_error_rate': avg_error,
            'sample_size': len(self._history)
        }


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化引擎
        engine = AdaptiveGrowthEngine(sensitivity=0.75)
        
        # 模拟多模态数据输入
        test_data = [
            MultiModalData(0.85, 1.2, 0.1),  # 良好状态
            MultiModalData(0.65, 3.5, 0.4),  # 疲劳状态
            MultiModalData(0.40, 5.0, 0.7)   # 过载状态
        ]
        
        for data in test_data:
            profile = engine.analyze_cognitive_state(data)
            print(f"\n当前状态: {profile.current_state.name}")
            print(f"认知负荷: {profile.cognitive_load:.2f}")
            print(f"推荐模式: {profile.recommended_mode.value}")
            print(f"难度调整: {profile.difficulty_adjustment:+.2f}")
            
        # 获取历史趋势
        trend = engine.get_historical_trend()
        print("\n历史趋势分析:", trend)
        
    except Exception as e:
        logger.error("Engine error: %s", str(e), exc_info=True)
        raise