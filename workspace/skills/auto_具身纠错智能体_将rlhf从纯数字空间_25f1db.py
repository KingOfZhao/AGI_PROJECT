"""
名称: auto_具身纠错智能体_将rlhf从纯数字空间_25f1db
描述: 【具身纠错智能体】将RLHF从纯数字空间拓展至物理实践空间。
      本模块实现了基于人类反馈的物理操作奖励模型，通过解析语音情感、
      视觉动作捕捉及传感器数据，将工匠的隐性知识（"手感"）转化为
      可优化的控制参数，实现人机共生的技能传递。
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmbodiedRLHF")


class FeedbackType(Enum):
    """反馈类型枚举"""
    SPEECH = "speech"
    GESTURE = "gesture"
    SENSOR = "sensor"


@dataclass
class PhysicalState:
    """物理操作状态数据结构"""
    timestamp: float
    arm_position: Tuple[float, float, float]  # (x, y, z) 坐标
    force_applied: float  # 施加的力 (牛顿)
    vibration_level: float  # 振动幅度
    temperature: float  # 操作点温度 (摄氏度)
    speed: float  # 移动速度 (m/s)


@dataclass
class HumanFeedback:
    """人类专家反馈数据结构"""
    timestamp: float
    feedback_type: FeedbackType
    content: Union[str, Dict, float]  # 语音文本/手势数据/传感器数值
    sentiment_score: float  # 情感评分 [-1.0, 1.0]


class EmbodiedRewardModel:
    """
    具身纠错奖励模型核心类
    
    该模型将人类专家的实时反馈（语音、手势、传感器数据）映射为
    物理操作的奖励信号，用于强化学习优化。
    
    属性:
        model_weights (Dict): 奖励模型的权重参数
        feedback_history (List): 历史反馈记录
        calibration_params (Dict): 传感器校准参数
    """
    
    def __init__(self, initial_weights: Optional[Dict] = None):
        """
        初始化奖励模型
        
        参数:
            initial_weights: 初始模型权重，若为None则使用默认值
        """
        self.model_weights = initial_weights or {
            'speech_weight': 0.4,
            'gesture_weight': 0.3,
            'sensor_weight': 0.3,
            'stability_penalty': -0.2,
            'precision_bonus': 0.5
        }
        self.feedback_history: List[HumanFeedback] = []
        self.calibration_params = {
            'force_threshold': 10.0,
            'vibration_limit': 0.05,
            'optimal_temperature': (200, 250)  # 焊接最佳温度范围
        }
        logger.info("Embodied Reward Model initialized with weights: %s", self.model_weights)

    def process_feedback(self, feedback: HumanFeedback, state: PhysicalState) -> float:
        """
        处理人类反馈并计算即时奖励
        
        参数:
            feedback: 人类专家的反馈数据
            state: 当前物理操作状态
            
        返回:
            float: 计算得到的奖励值 [-1.0, 1.0]
            
        异常:
            ValueError: 如果反馈数据无效
        """
        if not isinstance(feedback, HumanFeedback) or not isinstance(state, PhysicalState):
            logger.error("Invalid input types for feedback or state")
            raise ValueError("feedback must be HumanFeedback, state must be PhysicalState")
            
        # 数据验证
        if not -1.0 <= feedback.sentiment_score <= 1.0:
            logger.warning("Sentiment score %f out of bounds, clamping to [-1, 1]", 
                         feedback.sentiment_score)
            feedback.sentiment_score = max(-1.0, min(1.0, feedback.sentiment_score))
            
        # 记录反馈历史
        self.feedback_history.append(feedback)
        
        # 根据反馈类型计算奖励分量
        reward_components = {
            'speech': 0.0,
            'gesture': 0.0,
            'sensor': 0.0,
            'state_quality': 0.0
        }
        
        try:
            # 处理语音反馈
            if feedback.feedback_type == FeedbackType.SPEECH:
                reward_components['speech'] = self._process_speech_feedback(
                    feedback.content, feedback.sentiment_score
                )
                
            # 处理手势反馈
            elif feedback.feedback_type == FeedbackType.GESTURE:
                reward_components['gesture'] = self._process_gesture_feedback(
                    feedback.content, state
                )
                
            # 处理传感器反馈
            elif feedback.feedback_type == FeedbackType.SENSOR:
                reward_components['sensor'] = self._process_sensor_feedback(
                    feedback.content, state
                )
                
            # 计算状态质量奖励
            reward_components['state_quality'] = self._evaluate_state_quality(state)
            
            # 加权求和计算总奖励
            total_reward = (
                self.model_weights['speech_weight'] * reward_components['speech'] +
                self.model_weights['gesture_weight'] * reward_components['gesture'] +
                self.model_weights['sensor_weight'] * reward_components['sensor'] +
                reward_components['state_quality']  # 状态质量直接作为奖励项
            )
            
            logger.debug("Processed feedback - Components: %s, Total: %.3f", 
                        reward_components, total_reward)
            return max(-1.0, min(1.0, total_reward))
            
        except Exception as e:
            logger.error("Error processing feedback: %s", str(e))
            return 0.0  # 出错时返回中性奖励

    def update_model_weights(self, performance_score: float, learning_rate: float = 0.01) -> None:
        """
        根据整体性能评分更新模型权重（模拟RLHF过程）
        
        参数:
            performance_score: 最近操作周期的性能评分 [-1.0, 1.0]
            learning_rate: 学习率
        """
        if not -1.0 <= performance_score <= 1.0:
            raise ValueError("Performance score must be in [-1.0, 1.0]")
            
        # 简单的权重调整策略（实际中可使用更复杂的优化算法）
        if performance_score > 0.5:  # 表现良好，增强当前权重
            for key in self.model_weights:
                if key != 'stability_penalty':
                    self.model_weights[key] *= (1 + learning_rate)
        else:  # 表现不佳，减弱某些权重
            for key in self.model_weights:
                if key != 'precision_bonus':
                    self.model_weights[key] *= (1 - learning_rate)
                    
        # 归一化权重
        total = sum(v for k, v in self.model_weights.items() 
                   if k not in ['stability_penalty', 'precision_bonus'])
        for key in ['speech_weight', 'gesture_weight', 'sensor_weight']:
            self.model_weights[key] /= total
            
        logger.info("Updated model weights based on performance %.2f: %s", 
                   performance_score, self.model_weights)

    def _process_speech_feedback(self, content: str, sentiment: float) -> float:
        """
        处理语音反馈内容（辅助函数）
        
        参数:
            content: 语音识别的文本内容
            sentiment: 情感评分
            
        返回:
            float: 语音反馈奖励分量
        """
        # 关键词匹配增强反馈效果
        keywords = {
            '稳': 0.2,
            '轻': 0.15,
            '准': 0.25,
            '快': -0.1,  # 快在精细操作中通常是负面
            '慢': 0.1,
            '停': -0.5,
            '好': 0.3,
            '差': -0.3
        }
        
        keyword_bonus = 0.0
        for word, bonus in keywords.items():
            if word in str(content):
                keyword_bonus += bonus
                
        # 情感评分与关键词奖励的加权和
        reward = sentiment * 0.6 + keyword_bonus * 0.4
        logger.debug("Speech feedback processed: '%s' -> reward %.3f", content, reward)
        return reward

    def _process_gesture_feedback(self, gesture_data: Dict, state: PhysicalState) -> float:
        """
        处理手势反馈（辅助函数）
        
        参数:
            gesture_data: 手势识别数据 (包含手势类型、强度等)
            state: 当前物理状态
            
        返回:
            float: 手势反馈奖励分量
        """
        if not isinstance(gesture_data, dict):
            logger.warning("Invalid gesture data format")
            return 0.0
            
        gesture_type = gesture_data.get('type', '')
        intensity = gesture_data.get('intensity', 0.5)
        
        # 手势类型到奖励的映射
        gesture_rewards = {
            'nod': 0.3,          # 点头-认可
            'shake': -0.4,       # 摇头-否定
            'point': 0.2,        # 指引-注意
            'wave_off': -0.5,    # 挥手停止
            'thumb_up': 0.4,     # 竖大拇指
            'thumb_down': -0.3   # 大拇指朝下
        }
        
        base_reward = gesture_rewards.get(gesture_type, 0.0)
        reward = base_reward * intensity
        
        # 如果是纠正性手势，增加奖励幅度
        if gesture_type in ['point', 'wave_off']:
            reward *= 1.5
            
        logger.debug("Gesture feedback processed: %s (intensity %.2f) -> reward %.3f",
                    gesture_type, intensity, reward)
        return reward

    def _process_sensor_feedback(self, sensor_value: float, state: PhysicalState) -> float:
        """
        处理传感器直接反馈（辅助函数）
        
        参数:
            sensor_value: 传感器数值
            state: 当前物理状态
            
        返回:
            float: 传感器反馈奖励分量
        """
        try:
            # 检查力是否在合理范围
            force_diff = abs(state.force_applied - self.calibration_params['force_threshold'])
            force_reward = -0.1 * min(force_diff / 10.0, 1.0)  # 偏离越大惩罚越重
            
            # 检查振动水平
            vibration_penalty = 0.0
            if state.vibration_level > self.calibration_params['vibration_limit']:
                vibration_penalty = -0.2 * (state.vibration_level / self.calibration_params['vibration_limit'])
                
            # 检查温度是否在最佳范围
            temp_min, temp_max = self.calibration_params['optimal_temperature']
            if temp_min <= state.temperature <= temp_max:
                temp_reward = 0.15
            else:
                temp_diff = min(abs(state.temperature - temp_min), abs(state.temperature - temp_max))
                temp_reward = -0.1 * (temp_diff / 20.0)
                
            reward = force_reward + vibration_penalty + temp_reward
            logger.debug("Sensor feedback processed: force=%.2f, vib=%.3f, temp=%.1f -> reward %.3f",
                        state.force_applied, state.vibration_level, state.temperature, reward)
            return reward
            
        except Exception as e:
            logger.error("Error processing sensor feedback: %s", str(e))
            return 0.0

    def _evaluate_state_quality(self, state: PhysicalState) -> float:
        """
        评估物理状态质量（辅助函数）
        
        参数:
            state: 当前物理状态
            
        返回:
            float: 状态质量奖励 [-1.0, 1.0]
        """
        quality = 0.0
        
        # 稳定性奖励
        if state.vibration_level < 0.02:
            quality += self.model_weights['precision_bonus']
        elif state.vibration_level > 0.1:
            quality += self.model_weights['stability_penalty']
            
        # 速度合理性检查
        if 0.01 <= state.speed <= 0.05:  # 精细操作理想速度范围
            quality += 0.1
        elif state.speed > 0.1:
            quality -= 0.15  # 过快惩罚
            
        return quality


# 使用示例
if __name__ == "__main__":
    # 初始化奖励模型
    reward_model = EmbodiedRewardModel()
    
    # 模拟物理状态
    current_state = PhysicalState(
        timestamp=time.time(),
        arm_position=(0.5, 0.2, 0.1),
        force_applied=12.5,
        vibration_level=0.03,
        temperature=235.0,
        speed=0.03
    )
    
    # 模拟语音反馈
    speech_feedback = HumanFeedback(
        timestamp=time.time(),
        feedback_type=FeedbackType.SPEECH,
        content="这里手要稳，对准一点",
        sentiment_score=0.6
    )
    
    # 处理反馈并获取奖励
    reward = reward_model.process_feedback(speech_feedback, current_state)
    print(f"Calculated reward: {reward:.3f}")
    
    # 模拟手势反馈
    gesture_feedback = HumanFeedback(
        timestamp=time.time(),
        feedback_type=FeedbackType.GESTURE,
        content={'type': 'point', 'intensity': 0.8},
        sentiment_score=0.4
    )
    
    reward = reward_model.process_feedback(gesture_feedback, current_state)
    print(f"Gesture feedback reward: {reward:.3f}")
    
    # 模拟性能更新
    reward_model.update_model_weights(performance_score=0.7)