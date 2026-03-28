"""
高级技能模块：人机共生感官接口与语义-力觉闭环控制

名称: auto_通过连接_人机共生感官接口_td_5_0f48f
描述: 本模块实现了一个基于异构反馈的人机技能融合系统。它连接了高层语义理解
      （如"稍微紧一点"）与底层力觉控制接口，通过实时传感器数据反向修正
      语义与物理参数的映射关系，实现动态的人机共生控制。

核心组件:
- HapticSemanticAligner: 核心对齐类，处理语义到力觉参数的转换。
- GapVectorProcessor: 处理异构反馈（力觉、位置、时间）的向量化。
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Optional, List
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class SemanticToken(Enum):
    """定义支持的语义指令枚举"""
    TIGHTEN_SLIGHTLY = "稍微紧一点"
    TIGHTEN_MUCH = "紧很多"
    LOOSEN_SLIGHTLY = "稍微松一点"
    STOP = "停止"

@dataclass
class ForceFeedback:
    """力觉传感器反馈数据结构 (td_5_Q2_3)"""
    timestamp: float
    force_value: float  # 单位: 牛顿
    torque_value: float # 单位: 牛顿米
    is_valid: bool

@dataclass
class ControlParameters:
    """控制参数输出结构"""
    target_torque: float
    velocity_limit: float
    stiffness: float
    semantic_confidence: float

class SystemError(Exception):
    """自定义系统异常"""
    pass

# --- 核心类与函数 ---

class GapVectorProcessor:
    """
    异构反馈向量化处理器 (gap_5_G1)
    
    负责将不同源头的传感器数据（力觉、位置、语义历史）映射到同一特征空间，
    用于计算语义修正量。
    """
    
    def __init__(self, feature_dim: int = 64):
        self.feature_dim = feature_dim
        # 初始化简单的映射矩阵 (模拟神经网络权重)
        self._force_proj = np.random.randn(3, feature_dim // 2)
        self._history_proj = np.random.randn(5, feature_dim // 2)
        logger.info("GapVectorProcessor 初始化完成，特征维度: %d", feature_dim)

    def vectorize_feedback(self, feedback: ForceFeedback, history: List[float]) -> np.ndarray:
        """
        将原始反馈和历史记录转换为特征向量
        
        Args:
            feedback (ForceFeedback): 当前时刻的力觉反馈
            history (List[float]): 过去N次的力矩历史记录
            
        Returns:
            np.ndarray: 归一化的特征向量
        """
        if not feedback.is_valid:
            return np.zeros(self.feature_dim)
            
        # 简单的特征拼接与投影
        force_vec = np.array([feedback.force_value, feedback.torque_value, feedback.timestamp % 1.0])
        f_features = np.dot(force_vec, self._force_proj)
        
        # 填充或截断历史记录以保持维度一致
        hist_arr = np.array(history[-5:])
        if len(hist_arr) < 5:
            hist_arr = np.pad(hist_arr, (0, 5 - len(hist_arr)), 'constant')
        h_features = np.dot(hist_arr, self._history_proj)
        
        combined = np.concatenate([f_features, h_features])
        return combined / (np.linalg.norm(combined) + 1e-6)


class HapticSemanticAligner:
    """
    力觉-语义对齐器 (td_5_Q3_0)
    
    核心功能：建立自然语言与物理控制参数之间的映射，
    并根据实时反馈动态调整映射函数。
    """
    
    def __init__(self):
        # 初始语义-数值映射基准 (均值, 标准差)
        self._semantic_map: Dict[SemanticToken, Tuple[float, float]] = {
            SemanticToken.TIGHTEN_SLIGHTLY: (0.5, 0.1), # 初始假设：0.5 Nm
            SemanticToken.TIGHTEN_MUCH: (2.0, 0.2),
            SemanticToken.LOOSEN_SLIGHTLY: (-0.5, 0.1),
            SemanticToken.STOP: (0.0, 0.0)
        }
        self._gap_processor = GapVectorProcessor()
        self._history_buffer: List[float] = []
        logger.info("HapticSemanticAligner 初始化完成，连接人机共生感官接口")

    def _validate_token(self, token: SemanticToken) -> bool:
        """验证语义Token是否在映射表中"""
        if token not in self._semantic_map:
            logger.error("未知的语义指令: %s", token)
            raise ValueError(f"Unsupported semantic token: {token}")
        return True

    def _calculate_dynamic_offset(self, current_feedback: ForceFeedback) -> float:
        """
        辅助函数：基于异构反馈计算动态偏移量
        
        核心逻辑：如果当前感知的力矩与历史趋势不符，则生成修正值。
        """
        gap_vector = self._gap_processor.vectorize_feedback(current_feedback, self._history_buffer)
        
        # 模拟计算：使用特征向量的L2范数作为扰动因子
        # 在实际AGI系统中，这会是一个复杂的反向传播更新
        perturbation = np.linalg.norm(gap_vector) * 0.05
        
        # 根据当前力矩与预期的偏差决定修正方向
        if len(self._history_buffer) > 0:
            avg_history = np.mean(self._history_buffer)
            error = current_feedback.torque_value - avg_history
            return perturbation * np.sign(error)
        return 0.0

    def semantic_to_torque(self, 
                           instruction: SemanticToken, 
                           current_feedback: ForceFeedback) -> ControlParameters:
        """
        核心函数 1: 将语义指令转换为具体的控制参数
        
        Args:
            instruction (SemanticToken): 人类的自然语言指令枚举
            current_feedback (ForceFeedback): 当前的传感器反馈
            
        Returns:
            ControlParameters: 包含目标力矩和其他控制参数的结构体
            
        Raises:
            SystemError: 如果传感器数据无效或计算过程出错
        """
        try:
            self._validate_token(instruction)
            
            if not current_feedback.is_valid:
                logger.warning("传感器数据无效，回退到默认参数")
                return ControlParameters(0.0, 0.1, 0.5, 0.0)

            # 1. 获取基础参数
            base_mu, base_sigma = self._semantic_map[instruction]
            
            # 2. 计算基于反馈的动态修正 (实现 '稍微' 的数值分布修正)
            dynamic_offset = self._calculate_dynamic_offset(current_feedback)
            
            # 3. 生成最终目标力矩 (添加高斯噪声模拟不确定性)
            adjusted_mu = base_mu + dynamic_offset
            target_torque = np.random.normal(adjusted_mu, base_sigma)
            
            # 边界检查 (防止过载)
            target_torque = np.clip(target_torque, -10.0, 10.0)
            
            # 更新历史缓冲
            self._history_buffer.append(current_feedback.torque_value)
            if len(self._history_buffer) > 100:
                self._history_buffer.pop(0)

            logger.info(f"指令 '{instruction.value}' 转换: 基础{base_mu} + 修正{dynamic_offset:.4f} -> 目标 {target_torque:.4f}")

            return ControlParameters(
                target_torque=target_torque,
                velocity_limit=0.5,
                stiffness=0.8,
                semantic_confidence=1.0 - base_sigma
            )

        except Exception as e:
            logger.exception("语义转力矩过程中发生错误")
            raise SystemError(f"Alignment failed: {e}")

    def update_semantic_model(self, 
                              instruction: SemanticToken, 
                              actual_result: float, 
                              satisfaction_score: float):
        """
        核心函数 2: 反向修正模型
        
        根据操作结果和人类满意度反馈，调整语义映射的参数分布。
        例如：老工人觉得0.5Nm太紧了，系统下次会将'稍微'调整为0.4Nm。
        
        Args:
            instruction (SemanticToken): 执行的指令
            actual_result (float): 实际达到的物理力矩
            satisfaction_score (float): 人类反馈的满意度 (0.0-1.0)
        """
        if not (0.0 <= satisfaction_score <= 1.0):
            logger.error("满意度分数必须在0到1之间")
            return

        current_mu, current_sigma = self._semantic_map[instruction]
        
        # 简单的学习率调整逻辑
        learning_rate = 0.1 * (1.0 - satisfaction_score)
        
        # 如果不满意，调整均值向实际结果移动（或者远离，取决于具体逻辑）
        # 这里假设 actual_result 是理想的物理状态，如果满意度低，
        # 说明当前的语义映射和理想物理状态不匹配
        new_mu = current_mu + learning_rate * (actual_result - current_mu)
        
        # 更新映射
        self._semantic_map[instruction] = (new_mu, current_sigma)
        logger.info(f"模型更新: 指令 '{instruction.value}' 的均值从 {current_mu:.3f} 调整为 {new_mu:.3f}")

# --- 使用示例 ---

def run_demo():
    """
    演示如何使用 HapticSemanticAligner 进行人机交互。
    """
    print("--- 启动人机共生感官接口演示 ---")
    
    # 1. 初始化系统
    aligner = HapticSemanticAligner()
    
    # 2. 模拟第一次交互：老工人说"稍微紧一点"
    # 模拟传感器初始状态 (空载)
    initial_feedback = ForceFeedback(timestamp=0.0, force_value=0.0, torque_value=0.0, is_valid=True)
    
    # 转换指令
    params = aligner.semantic_to_torque(SemanticToken.TIGHTEN_SLIGHTLY, initial_feedback)
    print(f"生成目标力矩: {params.target_torque:.3f} Nm")
    
    # 3. 模拟执行后的反馈
    # 假设实际执行结果略高于目标，且工人满意度一般
    actual_torque = params.target_torque + 0.1
    aligner.update_semantic_model(SemanticToken.TIGHTEN_SLIGHTLY, actual_torque, 0.6)
    
    # 4. 模拟第二次交互：工人再次说"稍微紧一点"
    # 此时系统应该已经根据上次的反馈调整了理解
    new_feedback = ForceFeedback(timestamp=1.0, force_value=0.1, torque_value=actual_torque, is_valid=True)
    new_params = aligner.semantic_to_torque(SemanticToken.TIGHTEN_SLIGHTLY, new_feedback)
    
    print(f"修正后的目标力矩: {new_params.target_torque:.3f} Nm")
    print("--- 演示结束 ---")

if __name__ == "__main__":
    run_demo()