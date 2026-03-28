"""
模块: smooth_state_gui_generator
描述: 实现AGI系统中的平滑态GUI/UX生成器，用于在人机共生界面中处理后台数据剧烈变化时的视觉过渡。
      通过"声部连接"逻辑计算最优过渡路径，确保认知连续性。
"""

import logging
import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmoothStateGenerator")

class TransitionType(Enum):
    """定义过渡动画类型"""
    LINEAR = "linear"
    EASE_IN_OUT = "ease_in_out"
    ELASTIC = "elastic"
    COGNITIVE_BRIDGE = "cognitive_bridge"  # 认知桥接：用于剧烈结构变化

@dataclass
class GUIState:
    """表示GUI状态的数据结构"""
    id: str
    position: Tuple[float, float]  # (x, y) 坐标
    opacity: float  # 透明度 [0.0, 1.0]
    scale: float  # 缩放比例
    metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> bool:
        """验证GUI状态数据的有效性"""
        if not (0.0 <= self.opacity <= 1.0):
            logger.error(f"Invalid opacity value: {self.opacity}")
            return False
        if self.scale <= 0:
            logger.error(f"Invalid scale value: {self.scale}")
            return False
        return True

@dataclass
class TransitionPath:
    """表示过渡路径的计算结果"""
    start_state: GUIState
    end_state: GUIState
    transition_type: TransitionType
    duration_ms: int  # 过渡持续时间(毫秒)
    keyframes: List[Tuple[float, GUIState]]  # 关键帧列表 (时间点, 状态)
    cognitive_load_score: float  # 预估的认知负荷分数 (0.0-1.0)

class SmoothStateGenerator:
    """
    平滑态GUI/UX生成器，用于计算AGI系统中的最优视觉过渡路径。
    
    核心功能：
    1. 分析前后状态差异，确定过渡策略
    2. 计算"声部连接"路径，确保视觉连续性
    3. 生成中间关键帧，实现平滑过渡
    
    示例:
        >>> generator = SmoothStateGenerator()
        >>> start = GUIState("elem1", (0, 0), 1.0, 1.0)
        >>> end = GUIState("elem1", (100, 100), 0.8, 1.2)
        >>> path = generator.calculate_transition(start, end)
        >>> print(path.duration_ms)
    """
    
    def __init__(self, max_cognitive_load: float = 0.7):
        """
        初始化生成器
        
        Args:
            max_cognitive_load: 允许的最大认知负荷阈值 (0.0-1.0)
        """
        self.max_cognitive_load = max_cognitive_load
        self._validate_parameters()
        
    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性"""
        if not (0.0 <= self.max_cognitive_load <= 1.0):
            raise ValueError("max_cognitive_load must be between 0.0 and 1.0")
    
    def calculate_transition(
        self,
        start_state: GUIState,
        end_state: GUIState,
        force_type: Optional[TransitionType] = None
    ) -> TransitionPath:
        """
        计算两个GUI状态之间的最优过渡路径
        
        Args:
            start_state: 起始状态
            end_state: 目标状态
            force_type: 强制指定过渡类型 (可选)
            
        Returns:
            TransitionPath: 计算出的过渡路径
            
        Raises:
            ValueError: 如果状态数据无效
        """
        logger.info(f"Calculating transition from {start_state.id} to {end_state.id}")
        
        # 验证输入数据
        if not (start_state.validate() and end_state.validate()):
            raise ValueError("Invalid GUI state data")
            
        # 确定过渡类型
        transition_type = force_type if force_type else self._determine_transition_type(start_state, end_state)
        
        # 计算过渡持续时间
        duration = self._calculate_duration(start_state, end_state, transition_type)
        
        # 生成关键帧
        keyframes = self._generate_keyframes(start_state, end_state, transition_type, duration)
        
        # 计算认知负荷分数
        cognitive_load = self._calculate_cognitive_load(start_state, end_state, transition_type)
        
        # 创建过渡路径对象
        path = TransitionPath(
            start_state=start_state,
            end_state=end_state,
            transition_type=transition_type,
            duration_ms=duration,
            keyframes=keyframes,
            cognitive_load_score=cognitive_load
        )
        
        logger.info(f"Transition calculated: {transition_type.value}, duration: {duration}ms, load: {cognitive_load:.2f}")
        return path
    
    def _determine_transition_type(self, start: GUIState, end: GUIState) -> TransitionType:
        """
        根据状态变化程度确定过渡类型
        
        Args:
            start: 起始状态
            end: 目标状态
            
        Returns:
            TransitionType: 确定的过渡类型
        """
        # 计算位置变化距离
        position_delta = math.sqrt((end.position[0]-start.position[0])**2 + 
                                  (end.position[1]-start.position[1])**2)
        
        # 计算其他属性变化
        opacity_delta = abs(end.opacity - start.opacity)
        scale_delta = abs(end.scale - start.scale)
        
        # 根据变化程度选择过渡类型
        if position_delta > 500 or opacity_delta > 0.5 or scale_delta > 0.5:
            logger.debug("Large state change detected, using cognitive bridge")
            return TransitionType.COGNITIVE_BRIDGE
        elif position_delta > 200 or opacity_delta > 0.3 or scale_delta > 0.3:
            return TransitionType.ELASTIC
        elif position_delta > 50 or opacity_delta > 0.1 or scale_delta > 0.1:
            return TransitionType.EASE_IN_OUT
        else:
            return TransitionType.LINEAR
    
    def _calculate_duration(self, start: GUIState, end: GUIState, transition_type: TransitionType) -> int:
        """
        计算过渡持续时间
        
        Args:
            start: 起始状态
            end: 目标状态
            transition_type: 过渡类型
            
        Returns:
            int: 持续时间(毫秒)
        """
        # 基础时间根据变化程度计算
        position_delta = math.sqrt((end.position[0]-start.position[0])**2 + 
                                  (end.position[1]-start.position[1])**2)
        
        base_duration = min(2000, max(200, position_delta * 2))
        
        # 根据过渡类型调整
        if transition_type == TransitionType.COGNITIVE_BRIDGE:
            return int(base_duration * 1.5)  # 认知桥接需要更长时间
        elif transition_type == TransitionType.ELASTIC:
            return int(base_duration * 1.2)
        elif transition_type == TransitionType.EASE_IN_OUT:
            return int(base_duration * 0.9)
        else:
            return int(base_duration * 0.7)
    
    def _generate_keyframes(
        self,
        start: GUIState,
        end: GUIState,
        transition_type: TransitionType,
        duration: int
    ) -> List[Tuple[float, GUIState]]:
        """
        生成过渡路径的关键帧
        
        Args:
            start: 起始状态
            end: 目标状态
            transition_type: 过渡类型
            duration: 持续时间
            
        Returns:
            List[Tuple[float, GUIState]]: 关键帧列表 (时间点, 状态)
        """
        keyframes = []
        steps = 10  # 关键帧数量
        
        for i in range(steps + 1):
            t = i / steps  # 归一化时间 [0, 1]
            
            # 根据过渡类型计算缓动因子
            if transition_type == TransitionType.LINEAR:
                ease_factor = t
            elif transition_type == TransitionType.EASE_IN_OUT:
                ease_factor = t * t * (3 - 2 * t)
            elif transition_type == TransitionType.ELASTIC:
                ease_factor = self._elastic_ease(t)
            else:  # COGNITIVE_BRIDGE
                ease_factor = self._cognitive_bridge_ease(t, start, end)
            
            # 插值计算当前状态
            current_pos = (
                start.position[0] + (end.position[0] - start.position[0]) * ease_factor,
                start.position[1] + (end.position[1] - start.position[1]) * ease_factor
            )
            
            current_opacity = start.opacity + (end.opacity - start.opacity) * ease_factor
            current_scale = start.scale + (end.scale - start.scale) * ease_factor
            
            # 创建关键帧状态
            state = GUIState(
                id=start.id,
                position=current_pos,
                opacity=current_opacity,
                scale=current_scale
            )
            
            keyframes.append((t * duration, state))
        
        return keyframes
    
    def _elastic_ease(self, t: float) -> float:
        """弹性缓动函数"""
        p = 0.3
        return math.pow(2, -10 * t) * math.sin((t - p / 4) * (2 * math.pi) / p) + 1
    
    def _cognitive_bridge_ease(self, t: float, start: GUIState, end: GUIState) -> float:
        """
        认知桥接缓动函数，用于剧烈结构变化
        
        特点：
        1. 前段加速展示变化
        2. 中段暂停让用户适应
        3. 后段平滑完成过渡
        """
        if t < 0.3:
            return t * 2.0  # 前段加速
        elif t < 0.6:
            return 0.6 + (t - 0.3) * 0.2  # 中段缓慢
        else:
            return 0.8 + (t - 0.6) * 2.0  # 后段加速
    
    def _calculate_cognitive_load(
        self,
        start: GUIState,
        end: GUIState,
        transition_type: TransitionType
    ) -> float:
        """
        计算过渡的认知负荷分数
        
        Args:
            start: 起始状态
            end: 目标状态
            transition_type: 过渡类型
            
        Returns:
            float: 认知负荷分数 (0.0-1.0)
        """
        # 基于变化量和类型计算负荷
        position_delta = math.sqrt((end.position[0]-start.position[0])**2 + 
                                  (end.position[1]-start.position[1])**2)
        opacity_delta = abs(end.opacity - start.opacity)
        scale_delta = abs(end.scale - start.scale)
        
        # 归一化各变化因素
        pos_factor = min(1.0, position_delta / 1000.0)
        opacity_factor = opacity_delta
        scale_factor = min(1.0, scale_delta / 2.0)
        
        # 综合计算
        base_load = (pos_factor * 0.5 + opacity_factor * 0.3 + scale_factor * 0.2)
        
        # 根据过渡类型调整
        if transition_type == TransitionType.COGNITIVE_BRIDGE:
            return min(1.0, base_load * 1.2)  # 认知桥接虽然更平滑但变化大
        elif transition_type == TransitionType.ELASTIC:
            return min(1.0, base_load * 1.1)
        else:
            return min(1.0, base_load)
    
    def batch_process_transitions(
        self,
        transitions: List[Tuple[GUIState, GUIState]]
    ) -> List[TransitionPath]:
        """
        批量处理多个过渡请求
        
        Args:
            transitions: 过渡请求列表，每个元素是 (start_state, end_state) 元组
            
        Returns:
            List[TransitionPath]: 计算出的过渡路径列表
            
        Raises:
            ValueError: 如果输入数据无效
        """
        logger.info(f"Processing batch of {len(transitions)} transitions")
        
        if not transitions:
            logger.warning("Empty transitions list provided")
            return []
            
        results = []
        for i, (start, end) in enumerate(transitions):
            try:
                path = self.calculate_transition(start, end)
                results.append(path)
            except Exception as e:
                logger.error(f"Failed to process transition {i}: {str(e)}")
                continue
                
        return results

# 示例用法
if __name__ == "__main__":
    # 创建生成器实例
    generator = SmoothStateGenerator(max_cognitive_load=0.8)
    
    # 定义起始和目标状态
    start_state = GUIState(
        id="element1",
        position=(100, 100),
        opacity=1.0,
        scale=1.0,
        metadata={"type": "card", "content": "旧数据"}
    )
    
    end_state = GUIState(
        id="element1",
        position=(400, 300),
        opacity=0.7,
        scale=1.2,
        metadata={"type": "card", "content": "新数据"}
    )
    
    # 计算过渡路径
    try:
        transition_path = generator.calculate_transition(start_state, end_state)
        print(f"Transition type: {transition_path.transition_type.value}")
        print(f"Duration: {transition_path.duration_ms}ms")
        print(f"Cognitive load: {transition_path.cognitive_load_score:.2f}")
        print(f"Keyframes generated: {len(transition_path.keyframes)}")
        
        # 输出第一个和最后一个关键帧
        first_frame = transition_path.keyframes[0]
        last_frame = transition_path.keyframes[-1]
        print(f"\nFirst keyframe at {first_frame[0]}ms: pos={first_frame[1].position}")
        print(f"Last keyframe at {last_frame[0]}ms: pos={last_frame[1].position}")
        
    except ValueError as e:
        print(f"Error: {str(e)}")