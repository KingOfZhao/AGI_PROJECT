"""
模块: auto_基于_人机交互动态接口_bu_24_p_769913
描述: 实现基于人机交互动态接口、不确定性盲区与认知阻力算法的AGI协作模块。
      系统主动监测认知状态，实现智能的'人机回环'决策。
"""

import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, List, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DecisionRiskLevel(Enum):
    """决策风险等级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class CognitiveResistanceLevel(Enum):
    """认知阻力等级枚举"""
    NONE = 0
    SLIGHT = 1
    MODERATE = 2
    SEVERE = 3

@dataclass
class CognitiveState:
    """人类认知状态数据结构"""
    comfort_score: float = 1.0  # 0.0-1.0, 舒适度分数
    uncertainty_blind_spot: float = 0.0  # 0.0-1.0, 不确定性盲区概率
    cognitive_load: float = 0.0  # 0.0-1.0, 当前认知负荷
    resistance_level: CognitiveResistanceLevel = CognitiveResistanceLevel.NONE
    
    def is_valid(self) -> bool:
        """验证认知状态数据是否有效"""
        return (0.0 <= self.comfort_score <= 1.0 and
                0.0 <= self.uncertainty_blind_spot <= 1.0 and
                0.0 <= self.cognitive_load <= 1.0)

@dataclass
class DecisionContext:
    """决策上下文数据结构"""
    task_id: str
    input_data: Dict[str, Any]
    risk_level: DecisionRiskLevel = DecisionRiskLevel.LOW
    metadata: Dict[str, Any] = field(default_factory=dict)

class HumanInTheLoopSystem:
    """人机回环协作系统核心类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化人机回环系统
        
        Args:
            config: 配置字典，包含系统参数
        """
        self.config = config or {
            'risk_threshold': DecisionRiskLevel.MEDIUM,
            'uncertainty_threshold': 0.7,
            'resistance_threshold': CognitiveResistanceLevel.MODERATE,
            'max_retries': 3
        }
        self._validate_config()
        logger.info("HumanInTheLoopSystem initialized with config: %s", self.config)
    
    def _validate_config(self) -> None:
        """验证配置参数有效性"""
        if not isinstance(self.config['risk_threshold'], DecisionRiskLevel):
            raise ValueError("risk_threshold must be DecisionRiskLevel enum")
        if not 0 <= self.config['uncertainty_threshold'] <= 1:
            raise ValueError("uncertainty_threshold must be between 0 and 1")
    
    def evaluate_cognitive_state(self, 
                               biometric_data: Dict[str, Any],
                               interaction_history: List[Dict[str, Any]]) -> CognitiveState:
        """
        评估当前人类认知状态
        
        Args:
            biometric_data: 生物特征数据(心率、瞳孔扩张等)
            interaction_history: 最近交互历史
            
        Returns:
            CognitiveState: 当前认知状态评估结果
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not biometric_data:
            logger.warning("Empty biometric data received")
            return CognitiveState()
        
        try:
            # 计算舒适度分数(基于心率变异性等指标)
            hrv = biometric_data.get('heart_rate_variability', 0.5)
            pupil_dilation = biometric_data.get('pupil_dilation', 0.5)
            comfort_score = max(0.0, min(1.0, (hrv * 0.7 + (1 - pupil_dilation) * 0.3)))
            
            # 计算不确定性盲区(基于交互错误率和响应时间)
            error_rate = biometric_data.get('error_rate', 0.0)
            response_time_deviation = biometric_data.get('response_time_deviation', 0.0)
            uncertainty_blind_spot = max(0.0, min(1.0, (error_rate * 0.6 + response_time_deviation * 0.4)))
            
            # 计算认知负荷(基于多任务处理能力和注意力分散度)
            multitasking_score = biometric_data.get('multitasking_score', 0.5)
            attention_dispersion = biometric_data.get('attention_dispersion', 0.5)
            cognitive_load = max(0.0, min(1.0, (1 - multitasking_score) * 0.7 + attention_dispersion * 0.3))
            
            # 确定认知阻力等级
            resistance_level = self._calculate_resistance_level(
                comfort_score, uncertainty_blind_spot, cognitive_load
            )
            
            state = CognitiveState(
                comfort_score=comfort_score,
                uncertainty_blind_spot=uncertainty_blind_spot,
                cognitive_load=cognitive_load,
                resistance_level=resistance_level
            )
            
            if not state.is_valid():
                raise ValueError("Invalid cognitive state calculated")
                
            logger.debug("Evaluated cognitive state: %s", state)
            return state
            
        except Exception as e:
            logger.error("Error evaluating cognitive state: %s", str(e))
            raise
    
    def _calculate_resistance_level(self, 
                                  comfort: float, 
                                  uncertainty: float,
                                  load: float) -> CognitiveResistanceLevel:
        """
        计算认知阻力等级(辅助函数)
        
        Args:
            comfort: 舒适度分数
            uncertainty: 不确定性概率
            load: 认知负荷
            
        Returns:
            CognitiveResistanceLevel: 计算出的认知阻力等级
        """
        # 加权计算认知阻力指数
        resistance_index = (1 - comfort) * 0.4 + uncertainty * 0.3 + load * 0.3
        
        if resistance_index < 0.2:
            return CognitiveResistanceLevel.NONE
        elif resistance_index < 0.4:
            return CognitiveResistanceLevel.SLIGHT
        elif resistance_index < 0.6:
            return CognitiveResistanceLevel.MODERATE
        else:
            return CognitiveResistanceLevel.SEVERE
    
    def make_decision(self,
                     context: DecisionContext,
                     cognitive_state: CognitiveState) -> Tuple[bool, Dict[str, Any]]:
        """
        核心决策函数，决定是否需要人类介入
        
        Args:
            context: 决策上下文
            cognitive_state: 当前认知状态
            
        Returns:
            Tuple[bool, Dict]: (是否需要人类介入, 决策结果)
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not isinstance(context, DecisionContext):
            raise TypeError("context must be DecisionContext instance")
        if not cognitive_state.is_valid():
            raise ValueError("Invalid cognitive state provided")
            
        try:
            decision_data = {
                'task_id': context.task_id,
                'original_risk': context.risk_level.name,
                'cognitive_state': {
                    'comfort': cognitive_state.comfort_score,
                    'uncertainty': cognitive_state.uncertainty_blind_spot,
                    'load': cognitive_state.cognitive_load,
                    'resistance': cognitive_state.resistance_level.name
                },
                'human_intervention_needed': False,
                'adjusted_strategy': None,
                'confidence': 0.0
            }
            
            # 检查高风险决策
            if context.risk_level.value >= self.config['risk_threshold'].value:
                decision_data['human_intervention_needed'] = True
                decision_data['adjusted_strategy'] = "request_expert_review"
                decision_data['confidence'] = 0.9
                logger.warning("High risk decision detected for task %s", context.task_id)
                return (True, decision_data)
            
            # 检查认知阻力过高
            if cognitive_state.resistance_level.value >= self.config['resistance_threshold'].value:
                decision_data['human_intervention_needed'] = True
                decision_data['adjusted_strategy'] = "simplify_interface"
                decision_data['confidence'] = 0.85
                logger.info("High cognitive resistance detected, simplifying interface")
                return (True, decision_data)
            
            # 检查不确定性盲区
            if cognitive_state.uncertainty_blind_spot >= self.config['uncertainty_threshold']:
                decision_data['human_intervention_needed'] = True
                decision_data['adjusted_strategy'] = "request_clarification"
                decision_data['confidence'] = 0.75
                logger.info("Uncertainty blind spot detected, requesting clarification")
                return (True, decision_data)
            
            # 正常决策路径
            decision_data['adjusted_strategy'] = "autonomous_execution"
            decision_data['confidence'] = 0.95
            logger.debug("Proceeding with autonomous execution for task %s", context.task_id)
            return (False, decision_data)
            
        except Exception as e:
            logger.error("Decision making failed: %s", str(e))
            raise

# 使用示例
if __name__ == "__main__":
    try:
        # 初始化系统
        hitl_system = HumanInTheLoopSystem({
            'risk_threshold': DecisionRiskLevel.MEDIUM,
            'uncertainty_threshold': 0.6,
            'resistance_threshold': CognitiveResistanceLevel.MODERATE
        })
        
        # 模拟输入数据
        biometric_data = {
            'heart_rate_variability': 0.65,
            'pupil_dilation': 0.3,
            'error_rate': 0.1,
            'response_time_deviation': 0.2,
            'multitasking_score': 0.7,
            'attention_dispersion': 0.4
        }
        
        # 评估认知状态
        cognitive_state = hitl_system.evaluate_cognitive_state(biometric_data, [])
        
        # 创建决策上下文
        decision_context = DecisionContext(
            task_id="task_12345",
            input_data={'param1': 'value1', 'param2': 42},
            risk_level=DecisionRiskLevel.HIGH,
            metadata={'source': 'user_input'}
        )
        
        # 做出决策
        needs_intervention, decision = hitl_system.make_decision(decision_context, cognitive_state)
        
        # 输出结果
        print("\nDecision Results:")
        print(f"Needs human intervention: {needs_intervention}")
        print(json.dumps(decision, indent=2))
        
    except Exception as e:
        logger.error("System error: %s", str(e))