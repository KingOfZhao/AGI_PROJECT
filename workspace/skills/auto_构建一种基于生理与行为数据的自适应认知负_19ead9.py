"""
自适应认知负荷调节系统

基于生理与行为数据的智能教学调节模块。结合眼动追踪、交互延迟等
生理指标与ZPD(最近发展区)理论，实时调整学习内容的难度与呈现方式。

核心功能:
- 多模态数据融合(生理+行为)
- ZPD动态边界计算
- 认知状态实时评估
- 自适应难度调节
- 脚手架智能生成

数据输入格式:
{
    "eye_tracking": {
        "fixation_duration": 250.5,  # 注视持续时间
        "saccade_amplitude": 3.2,    # 眼跳幅度(度)
        "blink_rate": 15.2,          # 眨眼率(次/分钟)
        "pupil_diameter": 4.2        # 瞳孔直径
    },
    "interaction": {
        "response_time": 3500,       # 响应时间
        "mouse_hesitation": 850,     # 鼠标犹豫时间
        "scroll_patterns": [0.8, 0.6, 0.9]  # 滚动模式
    },
    "performance": {
        "correct_rate": 0.72,        # 正确率(0-1)
        "completion_rate": 0.85      # 完成率(0-1)
    }
}

输出格式:
{
    "action": "reduce_complexity",  # 调节动作
    "intensity": 0.6,               # 调节强度(0-1)
    "scaffolding": ["hint_1", "hint_2"],  # 脚手架内容
    "zpd_status": "optimal",        # ZPD状态
    "confidence": 0.89              # 决策置信度
}

作者: AGI System
版本: 1.0.0
"""

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveState(Enum):
    """认知状态枚举"""
    OVERLOAD = auto()      # 认知过载
    OPTIMAL = auto()       # 最佳状态
    UNDERLOAD = auto()     # 认知不足/厌倦
    TRANSITION = auto()    # 过渡状态


class ActionType(Enum):
    """调节动作类型枚举"""
    REDUCE_COMPLEXITY = "reduce_complexity"
    INCREASE_CHALLENGE = "increase_challenge"
    PROVIDE_SCAFFOLD = "provide_scaffold"
    MAINTAIN_CURRENT = "maintain_current"
    BREAK_TIME = "suggest_break"


@dataclass
class ZPDZone:
    """最近发展区(ZPD)边界数据结构"""
    lower_bound: float  # 下界(能力下限)
    upper_bound: float  # 上界(能力上限)
    optimal_point: float  # 最佳挑战点


@dataclass
class CognitiveProfile:
    """认知档案数据结构"""
    working_memory_capacity: float  # 工作记忆容量(0-1)
    processing_speed: float         # 信息处理速度(0-1)
    attention_span: float           # 注意力持续时间(秒)
    learning_style: str             # 学习风格(visual/auditory/kinesthetic)


class AdaptiveCognitiveLoadSystem:
    """
    自适应认知负荷调节系统
    
    结合多模态生理数据和行为数据，基于ZPD理论实时调节学习体验。
    
    属性:
        zpd_history (List[ZPDZone]): 历史ZPD记录
        state_history (List[CognitiveState]): 历史认知状态
        current_difficulty (float): 当前难度级别(0-1)
        adaptation_threshold (float): 调节触发阈值
        decay_rate (float): 历史数据衰减率
        
    使用示例:
        >>> system = AdaptiveCognitiveLoadSystem()
        >>> learner_data = {
        ...     "eye_tracking": {"fixation_duration": 280, "pupil_diameter": 4.5},
        ...     "interaction": {"response_time": 4200, "mouse_hesitation": 1200},
        ...     "performance": {"correct_rate": 0.65}
        ... }
        >>> result = system.process_learner_state(learner_data)
        >>> print(result["action"])
    """
    
    def __init__(
        self,
        initial_difficulty: float = 0.5,
        adaptation_threshold: float = 0.15,
        decay_rate: float = 0.85
    ):
        """
        初始化自适应认知负荷调节系统
        
        参数:
            initial_difficulty: 初始难度级别(0-1)
            adaptation_threshold: 调节触发阈值(0-1)
            decay_rate: 历史数据衰减率(0-1)
        """
        # 参数验证
        if not 0 <= initial_difficulty <= 1:
            raise ValueError("初始难度必须在0-1范围内")
        if not 0 <= adaptation_threshold <= 1:
            raise ValueError("调节阈值必须在0-1范围内")
        if not 0 <= decay_rate <= 1:
            raise ValueError("衰减率必须在0-1范围内")
            
        self.current_difficulty = initial_difficulty
        self.adaptation_threshold = adaptation_threshold
        self.decay_rate = decay_rate
        
        # 历史数据存储
        self.zpd_history: List[ZPDZone] = []
        self.state_history: List[CognitiveState] = []
        self.performance_history: List[float] = []
        
        # 认知档案(默认值)
        self.cognitive_profile = CognitiveProfile(
            working_memory_capacity=0.7,
            processing_speed=0.65,
            attention_span=1800,  # 30分钟
            learning_style="visual"
        )
        
        # 脚手架知识库
        self._scaffold_knowledge_base = self._initialize_scaffolds()
        
        logger.info("自适应认知负荷系统初始化完成 | 初始难度: %.2f", initial_difficulty)

    def process_learner_state(
        self,
        learner_data: Dict[str, Dict[str, Union[float, List[float]]]],
        timestamp: Optional[float] = None
    ) -> Dict[str, Union[str, float, List[str]]]:
        """
        处理学习者状态并生成调节决策
        
        核心函数: 分析多模态数据，评估认知状态，生成自适应调节策略
        
        参数:
            learner_data: 学习者多模态数据字典
            timestamp: 数据时间戳(可选)
            
        返回:
            包含调节动作、强度、脚手架和置信度的决策字典
            
        异常:
            ValueError: 当输入数据格式不正确时
        """
        start_time = time.time()
        
        try:
            # 数据验证
            self._validate_input_data(learner_data)
            
            # 1. 计算认知负荷指标
            cognitive_load = self._calculate_cognitive_load(learner_data)
            logger.debug(f"认知负荷指数: {cognitive_load:.3f}")
            
            # 2. 评估认知状态
            cognitive_state = self._assess_cognitive_state(
                cognitive_load,
                learner_data.get("performance", {})
            )
            self.state_history.append(cognitive_state)
            
            # 3. 更新ZPD边界
            current_zpd = self._update_zpd_boundaries(
                cognitive_load,
                learner_data.get("performance", {}).get("correct_rate", 0.5)
            )
            
            # 4. 生成调节策略
            action, intensity = self._generate_adaptation_strategy(
                cognitive_state,
                cognitive_load,
                current_zpd
            )
            
            # 5. 生成脚手架(如果需要)
            scaffolding = []
            if action in [ActionType.PROVIDE_SCAFFOLD, ActionType.REDUCE_COMPLEXITY]:
                scaffolding = self._generate_scaffolding(
                    cognitive_state,
                    learner_data,
                    intensity
                )
            
            # 6. 计算决策置信度
            confidence = self._calculate_decision_confidence(
                cognitive_state,
                len(self.state_history)
            )
            
            # 构建结果
            result = {
                "action": action.value if isinstance(action, ActionType) else action,
                "intensity": round(intensity, 3),
                "scaffolding": scaffolding,
                "zpd_status": self._get_zpd_status(cognitive_state),
                "confidence": round(confidence, 3),
                "current_difficulty": round(self.current_difficulty, 3),
                "cognitive_load_index": round(cognitive_load, 3),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
            
            logger.info(
                f"决策完成 | 状态: {cognitive_state.name} | "
                f"动作: {result['action']} | 置信度: {result['confidence']:.2%}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理学习者状态时发生错误: {str(e)}", exc_info=True)
            # 返回安全默认值
            return {
                "action": ActionType.MAINTAIN_CURRENT.value,
                "intensity": 0.0,
                "scaffolding": [],
                "zpd_status": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }

    def _calculate_cognitive_load(
        self,
        learner_data: Dict[str, Dict[str, Union[float, List[float]]]]
    ) -> float:
        """
        计算综合认知负荷指数
        
        辅助函数: 融合眼动、交互、生理等多维数据
        
        参数:
            learner_data: 多模态学习者数据
            
        返回:
            标准化认知负荷指数(0-1)
        """
        load_components = []
        
        # 1. 眼动指标分析
        eye_data = learner_data.get("eye_tracking", {})
        if eye_data:
            # 瞳孔直径变化(认知负荷的可靠指标)
            pupil_load = self._normalize_value(
                eye_data.get("pupil_diameter", 4.0),
                min_val=2.0, max_val=8.0, inverse=False
            )
            
            # 注视持续时间(过长表示困难)
            fixation_load = self._normalize_value(
                eye_data.get("fixation_duration", 250),
                min_val=100, max_val=500, inverse=False
            )
            
            # 眨眼率(过低表示高负荷)
            blink_load = self._normalize_value(
                eye_data.get("blink_rate", 15),
                min_val=5, max_val=25, inverse=True
            )
            
            eye_load = (pupil_load * 0.4 + fixation_load * 0.35 + blink_load * 0.25)
            load_components.append(("eye_tracking", eye_load, 0.35))
        
        # 2. 交互行为分析
        interaction_data = learner_data.get("interaction", {})
        if interaction_data:
            # 响应时间
            response_load = self._normalize_value(
                interaction_data.get("response_time", 3000),
                min_val=1000, max_val=10000, inverse=False
            )
            
            # 鼠标犹豫时间
            hesitation_load = self._normalize_value(
                interaction_data.get("mouse_hesitation", 500),
                min_val=100, max_val=2000, inverse=False
            )
            
            # 滚动模式不规则度
            scroll_patterns = interaction_data.get("scroll_patterns", [])
            scroll_irregularity = self._calculate_pattern_irregularity(scroll_patterns)
            
            interaction_load = (
                response_load * 0.4 + 
                hesitation_load * 0.35 + 
                scroll_irregularity * 0.25
            )
            load_components.append(("interaction", interaction_load, 0.40))
        
        # 3. 性能数据分析
        performance_data = learner_data.get("performance", {})
        if performance_data:
            # 正确率转换为负荷(低正确率=高负荷)
            correct_rate = performance_data.get("correct_rate", 0.7)
            performance_load = 1.0 - correct_rate
            load_components.append(("performance", performance_load, 0.25))
        
        # 加权融合
        if not load_components:
            return 0.5  # 默认中等负荷
            
        total_weight = sum(w for _, _, w in load_components)
        weighted_load = sum(load * weight for _, load, weight in load_components) / total_weight
        
        # 应用历史平滑
        if self.performance_history:
            historical_factor = 0.3
            previous_load = self.performance_history[-1]
            weighted_load = (
                weighted_load * (1 - historical_factor) + 
                previous_load * historical_factor
            )
        
        self.performance_history.append(weighted_load)
        
        # 限制历史长度
        max_history = 50
        if len(self.performance_history) > max_history:
            self.performance_history = self.performance_history[-max_history:]
        
        return max(0.0, min(1.0, weighted_load))

    def _assess_cognitive_state(
        self,
        cognitive_load: float,
        performance_data: Dict[str, float]
    ) -> CognitiveState:
        """
        评估当前认知状态
        
        核心函数: 基于认知负荷和性能数据判断学习者状态
        
        参数:
            cognitive_load: 认知负荷指数
            performance_data: 性能数据字典
            
        返回:
            CognitiveState枚举值
        """
        correct_rate = performance_data.get("correct_rate", 0.7)
        
        # 定义ZPD边界(动态调整)
        optimal_load_lower = 0.35
        optimal_load_upper = 0.65
        
        # 基于认知档案调整边界
        memory_capacity = self.cognitive_profile.working_memory_capacity
        optimal_load_upper += (memory_capacity - 0.5) * 0.2
        
        # 状态判断逻辑
        if cognitive_load > optimal_load_upper:
            # 高负荷 + 低正确率 = 过载
            if correct_rate < 0.6:
                return CognitiveState.OVERLOAD
            # 高负荷 + 高正确率 = 挑战区(仍在ZPD内)
            else:
                return CognitiveState.TRANSITION
                
        elif cognitive_load < optimal_load_lower:
            # 低负荷 + 高正确率 = 厌倦
            if correct_rate > 0.85:
                return CognitiveState.UNDERLOAD
            # 低负荷 + 低正确率 = 可能是动力不足
            else:
                return CognitiveState.TRANSITION
                
        else:
            # 负荷在最佳区间
            return CognitiveState.OPTIMAL

    def _update_zpd_boundaries(
        self,
        cognitive_load: float,
        performance: float
    ) -> ZPDZone:
        """
        更新ZPD边界
        
        辅助函数: 根据实时表现动态调整最近发展区边界
        
        参数:
            cognitive_load: 当前认知负荷
            performance: 当前性能水平(正确率)
            
        返回:
            更新后的ZPD边界对象
        """
        # 基础ZPD计算
        base_lower = max(0.1, performance - 0.15)
        base_upper = min(1.0, performance + 0.20)
        
        # 根据认知档案调整
        processing_speed = self.cognitive_profile.processing_speed
        adjustment = (processing_speed - 0.5) * 0.1
        
        base_upper += adjustment
        base_lower += adjustment * 0.5
        
        # 历史平滑
        if self.zpd_history:
            prev_zpd = self.zpd_history[-1]
            smooth_factor = 0.3
            base_lower = base_lower * (1 - smooth_factor) + prev_zpd.lower_bound * smooth_factor
            base_upper = base_upper * (1 - smooth_factor) + prev_zpd.upper_bound * smooth_factor
        
        # 计算最佳点(略高于当前能力)
        optimal_point = (base_lower + base_upper) / 2 + 0.05
        
        zpd = ZPDZone(
            lower_bound=max(0.0, min(1.0, base_lower)),
            upper_bound=max(0.0, min(1.0, base_upper)),
            optimal_point=max(0.0, min(1.0, optimal_point))
        )
        
        self.zpd_history.append(zpd)
        
        # 限制历史长度
        max_history = 30
        if len(self.zpd_history) > max_history:
            self.zpd_history = self.zpd_history[-max_history:]
        
        return zpd

    def _generate_adaptation_strategy(
        self,
        cognitive_state: CognitiveState,
        cognitive_load: float,
        current_zpd: ZPDZone
    ) -> Tuple[ActionType, float]:
        """
        生成自适应调节策略
        
        核心函数: 根据认知状态决定调节动作和强度
        
        参数:
            cognitive_state: 当前认知状态
            cognitive_load: 认知负荷指数
            current_zpd: 当前ZPD边界
            
        返回:
            (动作类型, 调节强度)元组
        """
        action = ActionType.MAINTAIN_CURRENT
        intensity = 0.0
        
        if cognitive_state == CognitiveState.OVERLOAD:
            # 计算过载程度
            overload_magnitude = cognitive_load - current_zpd.upper_bound
            intensity = min(1.0, overload_magnitude * 2.5)
            
            if intensity > 0.6:
                action = ActionType.REDUCE_COMPLEXITY
                self.current_difficulty = max(
                    0.1,
                    self.current_difficulty - intensity * 0.15
                )
            else:
                action = ActionType.PROVIDE_SCAFFOLD
                
        elif cognitive_state == CognitiveState.UNDERLOAD:
            # 计算厌倦程度
            underload_magnitude = current_zpd.lower_bound - cognitive_load
            intensity = min(1.0, underload_magnitude * 2.0)
            
            action = ActionType.INCREASE_CHALLENGE
            self.current_difficulty = min(
                1.0,
                self.current_difficulty + intensity * 0.1
            )
            
        elif cognitive_state == CognitiveState.OPTIMAL:
            # 在最佳区间，微调
            action = ActionType.MAINTAIN_CURRENT
            intensity = 0.0
            
        elif cognitive_state == CognitiveState.TRANSITION:
            # 过渡状态，提供支持
            action = ActionType.PROVIDE_SCAFFOLD
            intensity = 0.3
        
        return action, intensity

    def _generate_scaffolding(
        self,
        cognitive_state: CognitiveState,
        learner_data: Dict,
        intensity: float
    ) -> List[str]:
        """
        生成个性化脚手架
        
        辅助函数: 根据认知状态和学习风格生成支持内容
        
        参数:
            cognitive_state: 认知状态
            learner_data: 学习者数据
            intensity: 调节强度
            
        返回:
            脚手架内容列表
        """
        scaffolds = []
        learning_style = self.cognitive_profile.learning_style
        
        if cognitive_state == CognitiveState.OVERLOAD:
            # 过载时的脚手架
            scaffolds.extend(self._scaffold_knowledge_base["overload"].get(
                learning_style,
                self._scaffold_knowledge_base["overload"]["default"]
            )[:int(intensity * 3) + 1])
            
        elif cognitive_state == CognitiveState.UNDERLOAD:
            # 厌倦时的挑战变体
            scaffolds.extend(self._scaffold_knowledge_base["challenge"].get(
                learning_style,
                self._scaffold_knowledge_base["challenge"]["default"]
            )[:int(intensity * 2) + 1])
            
        elif cognitive_state == CognitiveState.TRANSITION:
            # 过渡时的提示
            scaffolds.extend(self._scaffold_knowledge_base["transition"].get(
                learning_style,
                self._scaffold_knowledge_base["transition"]["default"]
            )[:1])
        
        return scaffolds

    # ==================== 工具函数 ====================
    
    def _validate_input_data(self, data: Dict) -> None:
        """验证输入数据格式"""
        if not isinstance(data, dict):
            raise ValueError("输入数据必须是字典类型")
        
        required_sections = ["eye_tracking", "interaction", "performance"]
        for section in required_sections:
            if section not in data:
                logger.warning(f"缺少数据部分: {section}, 将使用默认值")
    
    def _normalize_value(
        self,
        value: float,
        min_val: float,
        max_val: float,
        inverse: bool = False
    ) -> float:
        """将值归一化到0-1范围"""
        if max_val == min_val:
            return 0.5
        
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))
        
        return 1.0 - normalized if inverse else normalized
    
    def _calculate_pattern_irregularity(self, patterns: List[float]) -> float:
        """计算模式不规则度"""
        if len(patterns) < 2:
            return 0.0
        
        # 计算标准差作为不规则度指标
        mean = sum(patterns) / len(patterns)
        variance = sum((x - mean) ** 2 for x in patterns) / len(patterns)
        std_dev = math.sqrt(variance)
        
        return min(1.0, std_dev * 2)
    
    def _calculate_decision_confidence(
        self,
        state: CognitiveState,
        history_length: int
    ) -> float:
        """计算决策置信度"""
        base_confidence = 0.7
        
        # 历史数据越多，置信度越高
        history_boost = min(0.2, history_length * 0.01)
        
        # 过渡状态置信度较低
        if state == CognitiveState.TRANSITION:
            state_penalty = 0.15
        else:
            state_penalty = 0.0
        
        return max(0.0, min(1.0, base_confidence + history_boost - state_penalty))
    
    def _get_zpd_status(self, state: CognitiveState) -> str:
        """获取ZPD状态描述"""
        status_map = {
            CognitiveState.OVERLOAD: "frustration",
            CognitiveState.OPTIMAL: "optimal",
            CognitiveState.UNDERLOAD: "boredom",
            CognitiveState.TRANSITION: "transition"
        }
        return status_map.get(state, "unknown")
    
    def _initialize_scaffolds(self) -> Dict:
        """初始化脚手架知识库"""
        return {
            "overload": {
                "visual": [
                    "💡 尝试将问题分解为更小的步骤",
                    "📊 这里有一个可视化图解帮助理解",
                    "🎯 专注于当前这一个概念"
                ],
                "auditory": [
                    "🎧 让我们用语音解释这个概念",
                    "🗣️ 试着大声说出你的思考过程",
                    "❓ 回答这个简化版问题"
                ],
                "default": [
                    "📝 这里有一些提示",
                    "🔄 让我们回顾一下基础概念",
                    "⏸️ 建议短暂休息一下"
                ]
            },
            "challenge": {
                "visual": [
                    "🌟 尝试这个进阶挑战题",
                    "🏆 解锁隐藏成就",
                    "🔥 挑战时间模式"
                ],
                "auditory": [
                    "🎙️ 尝试用你自己的话解释",
                    "🎧 听听这个进阶案例",
                    "💡 设计一个新问题"
                ],
                "default": [
                    "🚀 准备好迎接挑战了吗?",
                    "⚡ 开启困难模式",
                    "🎯 尝试创新解法"
                ]
            },
            "transition": {
                "visual": ["📍 你正在进步中"],
                "auditory": ["🎵 保持专注"],
                "default": ["✨ 继续保持"]
            }
        }


# ==================== 使用示例 ====================

def demo_simulation():
    """
    演示系统运行模拟
    
    模拟不同认知状态下的系统响应
    """
    print("=" * 60)
    print("自适应认知负荷调节系统 - 演示")
    print("=" * 60)
    
    # 初始化系统
    system = AdaptiveCognitiveLoadSystem(
        initial_difficulty=0.5,
        adaptation_threshold=0.15
    )
    
    # 场景1: 认知过载的学生
    print("\n【场景1】认知过载的学生 - 眼动显示高负荷")
    overload_data = {
        "eye_tracking": {
            "fixation_duration": 450,      # 长注视
            "saccade_amplitude": 1.5,      # 小幅度眼跳
            "blink_rate": 8,               # 低眨眼率
            "pupil_diameter": 5.8          # 瞳孔放大
        },
        "interaction": {
            "response_time": 8500,         # 响应慢
            "mouse_hesitation": 1800,      # 长时间犹豫
            "scroll_patterns": [0.9, 0.95, 0.92]
        },
        "performance": {
            "correct_rate": 0.45,          # 正确率低
            "completion_rate": 0.60
        }
    }
    
    result1 = system.process_learner_state(overload_data)
    print(f"  → 认知负荷: {result1['cognitive_load_index']:.2%}")
    print(f"  → 状态: {result1['zpd_status']}")
    print(f"  → 动作: {result1['action']}")
    print(f"  → 强度: {result1['intensity']:.2%}")
    print(f"  → 脚手架: {result1['scaffolding']}")
    
    # 场景2: 厌倦的学生
    print("\n【场景2】认知不足的学生 - 表现出色但负荷低")
    underload_data = {
        "eye_tracking": {
            "fixation_duration": 150,      # 快速浏览
            "saccade_amplitude": 5.5,      # 大幅度眼跳
            "blink_rate": 22,              # 高眨眼率
            "pupil_diameter": 3.2          # 正常瞳孔
        },
        "interaction": {
            "response_time": 1200,         # 快速响应
            "mouse_hesitation": 150,       # 毫不犹豫
            "scroll_patterns": [0.3, 0.4, 0.35]
        },
        "performance": {
            "correct_rate": 0.95,          # 正确率极高
            "completion_rate": 1.0
        }
    }
    
    result2 = system.process_learner_state(underload_data)
    print(f"  → 认知负荷: {result2['cognitive_load_index']:.2%}")
    print(f"  → 状态: {result2['zpd_status']}")
    print(f"  → 动作: {result2['action']}")
    print(f"  → 强度: {result2['intensity']:.2%}")
    print(f"  → 脚手架: {result2['scaffolding']}")
    
    # 场景3: 最佳学习状态
    print("\n【场景3】处于ZPD最佳区的学生")
    optimal_data = {
        "eye_tracking": {
            "fixation_duration": 280,
            "saccade_amplitude": 3.2,
            "blink_rate": 16,
            "pupil_diameter": 4.2
        },
        "interaction": {
            "response_time": 3200,
            "mouse_hesitation": 450,
            "scroll_patterns": [0.6, 0.7, 0.65]
        },
        "performance": {
            "correct_rate": 0.75,
            "completion_rate": 0.85
        }
    }
    
    result3 = system.process_learner_state(optimal_data)
    print(f"  → 认知负荷: {result3['cognitive负荷_index']:.2%}")
    print(f"  → 状态: {result3['zpd_status']}")
    print(f"  → 动作: {result3['action']}")
    print(f"  → 置信度: {result3['confidence']:.2%}")
    
    print("\n" + "=" * 60)
    print(f"系统状态 | 当前难度: {system.current_difficulty:.2f}")
    print(f"         | 历史记录: {len(system.state_history)} 条")
    print("=" * 60)


if __name__ == "__main__":
    demo_simulation()