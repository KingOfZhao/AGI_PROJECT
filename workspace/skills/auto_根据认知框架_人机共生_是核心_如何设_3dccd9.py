"""
模块名称: human_in_the_loop_interface
描述: 根据认知框架，实现‘人机共生’的核心接口。
      本模块设计了一个‘人在回路’系统，当AI遇到‘置信度低谷’时，
      自动生成‘最小验证问题’向人类求助，并将二值反馈转化为强化学习的Reward信号。

核心功能:
1. 监控AI模型的置信度。
2. 生成自然语言形式的最小验证问题。
3. 处理人类反馈并映射为RL奖励。
"""

import logging
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """人类反馈的类型枚举"""
    POSITIVE = 1  # "是"
    NEGATIVE = 0  # "否"
    UNKNOWN = -1  # 未知/超时

@dataclass
class AIState:
    """AI当前状态的表示类"""
    state_id: str
    raw_data: Any
    predicted_label: str
    confidence: float  # 0.0 到 1.0

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"置信度必须在0.0和1.0之间，当前为: {self.confidence}")

class HumanInTheLoopInterface:
    """
    人机共生接口类。
    
    负责在AI置信度低于阈值时介入，请求人类验证，并生成训练信号。
    """
    
    def __init__(self, confidence_threshold: float = 0.75, reward_scale: float = 1.0):
        """
        初始化接口。
        
        Args:
            confidence_threshold (float): 触发人类介入的置信度阈值。
            reward_scale (float): 奖励信号的缩放因子。
        """
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("阈值必须在0.0和1.0之间")
            
        self.confidence_threshold = confidence_threshold
        self.reward_scale = reward_scale
        self.interaction_history: List[Dict[str, Any]] = []
        logger.info(f"HITL Interface initialized with threshold: {self.confidence_threshold}")

    def check_intervention_needed(self, ai_state: AIState) -> bool:
        """
        核心函数1: 检查当前状态是否需要人类介入。
        
        Args:
            ai_state (AIState): 当前AI的推理状态。
            
        Returns:
            bool: 如果置信度低于阈值返回True，否则False。
        """
        if ai_state.confidence < self.confidence_threshold:
            logger.warning(f"低置信度检测: {ai_state.confidence:.2f} < {self.confidence_threshold}. 触发介入。")
            return True
        return False

    def generate_minimal_question(self, ai_state: AIState, context: Optional[Dict] = None) -> str:
        """
        核心函数2: 根据低置信度状态生成最小验证问题。
        
        此处模拟根据预测标签生成特定的验证问题。
        
        Args:
            ai_state (AIState): 需要验证的AI状态。
            context (Optional[Dict]): 额外的上下文信息（如环境属性）。
            
        Returns:
            str: 生成的自然语言问题。
        """
        # 简单的模板匹配逻辑，实际场景中可接入LLM
        label = ai_state.predicted_label
        question = f"检测到不确定因素。系统预测倾向为 '{label}'。这个判断正确吗？"
        
        # 模拟生成针对特定属性的'最小'问题（例如颜色）
        if context and "attribute" in context:
            attr = context["attribute"]
            question = f"关于属性 '{attr}'，系统检测到异常。当前状态是否表现为 '{label}'？"
            
        logger.info(f"生成验证问题: {question}")
        return question

    def map_feedback_to_reward(self, feedback: FeedbackType, current_confidence: float) -> float:
        """
        核心函数3 (辅助/映射): 将人类反馈转化为RL Reward。
        
        策略:
        - 正向反馈 (是): 给予正奖励，奖励大小与(1 - confidence)成正比，鼓励探索未知。
        - 负向反馈 (否): 给予负奖励，惩罚错误的低置信度预测。
        - 未知: 给予小的负奖励或0，避免利用系统漏洞。
        
        Args:
            feedback (FeedbackType): 人类的反馈枚举。
            current_confidence (float): 决策时的置信度。
            
        Returns:
            float: 计算出的奖励值。
        """
        base_reward = 0.0
        if feedback == FeedbackType.POSITIVE:
            # 越是不确定时得到确认，奖励应越高（信息增益大）
            uncertainty = 1.0 - current_confidence
            base_reward = 1.0 + (uncertainty * self.reward_scale)
            logger.debug(f"正向反馈。不确定性: {uncertainty:.2f}, 奖励: {base_reward:.2f}")
        elif feedback == FeedbackType.NEGATIVE:
            base_reward = -1.0 * self.reward_scale
            logger.debug(f"负向反馈。惩罚: {base_reward:.2f}")
        else:
            base_reward = -0.1 # 轻微惩罚，表示浪费时间
            logger.debug("反馈未知或超时。")
            
        return base_reward

    def execute_interaction_cycle(self, ai_state: AIState, context: Optional[Dict] = None) -> Tuple[bool, float]:
        """
        执行完整的交互周期（模拟）。
        
        Args:
            ai_state (AIState): AI状态。
            context (Optional[Dict]): 上下文。
            
        Returns:
            Tuple[bool, float]: (是否发生了介入, 最终计算的奖励)
        """
        if not self.check_intervention_needed(ai_state):
            return False, 0.0
        
        question = self.generate_minimal_question(ai_state, context)
        
        # --- 模拟人类输入 ---
        # 在实际部署中，这里会连接前端API等待输入
        # 此处我们随机模拟一个人类响应
        print(f"\n[系统提问]: {question}")
        simulated_human_input = random.choice([FeedbackType.POSITIVE, FeedbackType.NEGATIVE])
        print(f"[模拟人类输入]: {'是' if simulated_human_input == FeedbackType.POSITIVE else '否'}")
        # -------------------
        
        reward = self.map_feedback_to_reward(simulated_human_input, ai_state.confidence)
        
        # 记录日志
        self.interaction_history.append({
            "state_id": ai_state.state_id,
            "question": question,
            "feedback": simulated_human_input,
            "reward": reward
        })
        
        return True, reward

# 数据验证辅助函数
def validate_state_input(state_dict: Dict) -> AIState:
    """
    验证输入数据并创建AIState对象。
    
    Args:
        state_dict (Dict): 包含状态信息的原始字典。
        
    Returns:
        AIState: 验证后的状态对象。
        
    Raises:
        KeyError: 缺少必要字段。
        ValueError: 数据类型错误。
    """
    required_keys = ["state_id", "predicted_label", "confidence"]
    for key in required_keys:
        if key not in state_dict:
            logger.error(f"缺少必要字段: {key}")
            raise KeyError(f"Missing required key: {key}")
            
    return AIState(
        state_id=str(state_dict["state_id"]),
        raw_data=state_dict.get("raw_data"),
        predicted_label=str(state_dict["predicted_label"]),
        confidence=float(state_dict["confidence"])
    )

if __name__ == "__main__":
    # 使用示例
    print("--- 启动人机共生接口测试 ---")
    
    # 1. 初始化接口
    hitl = HumanInTheLoopInterface(confidence_threshold=0.8, reward_scale=2.0)
    
    # 2. 模拟AI状态数据
    # 场景A: 高置信度，不应触发
    state_high_conf = {
        "state_id": "img_001",
        "predicted_label": "cat",
        "confidence": 0.95
    }
    
    # 场景B: 低置信度，触发介入 (例如: 颜色识别困难)
    state_low_conf = {
        "state_id": "img_002",
        "predicted_label": "red_tint",
        "confidence": 0.55,
        "raw_data": "<image_data>"
    }
    
    try:
        # 验证并创建对象
        valid_state_high = validate_state_input(state_high_conf)
        valid_state_low = validate_state_input(state_low_conf)
        
        # 运行高置信度场景
        intervened, reward = hitl.execute_interaction_cycle(valid_state_high)
        if not intervened:
            print(f"Test 1 Passed: 高置信度未触发介入。")
            
        # 运行低置信度场景
        intervened, reward = hitl.execute_interaction_cycle(valid_state_low, context={"attribute": "color"})
        if intervened:
            print(f"Test 2 Passed: 介入成功，生成奖励: {reward:.2f}")
            
    except (ValueError, KeyError) as e:
        logger.error(f"测试失败: {e}")
    
    print("--- 测试结束 ---")