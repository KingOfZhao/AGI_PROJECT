"""
模块名称: auto_构建_自适应心流导航系统_adapt_a42543
描述: 实现'自适应心流导航系统' (Adaptive Flow Navigation System)。
      该系统利用多模态数据实时评估学习者的认知负荷，动态调整任务难度，
      维持用户处于'心流'状态，实现认知螺旋上升。
"""

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptiveFlowNav")

class CognitiveState(Enum):
    """认知状态枚举"""
    ANXIETY = "anxiety"       # 焦虑（负荷过高）
    FLOW = "flow"             # 心流（平衡状态）
    BOREDOM = "boredom"       # 厌倦（负荷过低）
    UNKNOWN = "unknown"       # 未知状态

@dataclass
class UserInput:
    """用户多模态输入数据"""
    eye_movement_variance: float  # 眼动方差（0.0-1.0，值越高越焦虑）
    click_frequency: float        # 操作频率（次/分钟）
    answer_accuracy: float        # 答题正确率（0.0-1.0）
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.eye_movement_variance <= 1:
            raise ValueError("眼动方差必须在0-1之间")
        if self.click_frequency < 0:
            raise ValueError("操作频率不能为负")
        if not 0 <= self.answer_accuracy <= 1:
            raise ValueError("答题正确率必须在0-1之间")

@dataclass
class TaskDifficulty:
    """任务难度参数"""
    complexity: int        # 复杂度（1-10）
    hint_level: int        # 提示级别（0-3，0=无提示）
    randomness: float      # 随机性（0.0-1.0）

    def __post_init__(self):
        """边界检查"""
        self.complexity = max(1, min(10, self.complexity))
        self.hint_level = max(0, min(3, self.hint_level))
        self.randomness = max(0.0, min(1.0, self.randomness))

class AdaptiveFlowNavigationSystem:
    """
    自适应心流导航系统
    
    该系统通过实时分析用户的多模态数据（眼动、操作频率、答题正确率），
    动态调整任务难度，确保用户始终处于最佳认知负荷状态。
    
    使用示例:
    >>> system = AdaptiveFlowNavigationSystem()
    >>> user_input = UserInput(eye_movement_variance=0.8, click_frequency=15, answer_accuracy=0.4)
    >>> new_difficulty = system.adjust_difficulty(user_input)
    >>> print(new_difficulty)
    TaskDifficulty(complexity=4, hint_level=2, randomness=0.3)
    """
    
    def __init__(self, 
                 history_size: int = 5, 
                 anxiety_threshold: float = 0.7,
                 boredom_threshold: float = 0.3):
        """
        初始化系统
        
        参数:
            history_size: 历史数据窗口大小
            anxiety_threshold: 焦虑判定阈值
            boredom_threshold: 厌倦判定阈值
        """
        self.history: List[UserInput] = []
        self.current_difficulty = TaskDifficulty(5, 1, 0.5)
        self.history_size = history_size
        self.anxiety_threshold = anxiety_threshold
        self.boredom_threshold = boredom_threshold
        logger.info("初始化自适应心流导航系统")
    
    def _assess_cognitive_load(self, input_data: UserInput) -> float:
        """
        评估认知负荷（内部方法）
        
        基于多模态数据计算综合认知负荷指数（0-1，1表示最高负荷）
        
        参数:
            input_data: 用户输入数据
            
        返回:
            认知负荷指数
        """
        # 加权计算认知负荷
        load = (
            input_data.eye_movement_variance * 0.4 +  # 眼动贡献40%
            (1 - input_data.answer_accuracy) * 0.3 +  # 错误率贡献30%
            (max(0, min(1, input_data.click_frequency / 30))) * 0.3  # 点击频率归一化后贡献30%
        )
        
        # 考虑历史趋势
        if self.history:
            recent_loads = [self._assess_cognitive_load(h) for h in self.history[-3:]]
            trend = sum(recent_loads) / len(recent_loads) * 0.3
            load = load * 0.7 + trend * 0.3
        
        logger.debug(f"计算认知负荷: {load:.2f}")
        return max(0.0, min(1.0, load))
    
    def _determine_state(self, cognitive_load: float) -> CognitiveState:
        """
        确定认知状态（内部方法）
        
        参数:
            cognitive_load: 认知负荷指数
            
        返回:
            认知状态枚举值
        """
        if cognitive_load > self.anxiety_threshold:
            return CognitiveState.ANXIETY
        elif cognitive_load < self.boredom_threshold:
            return CognitiveState.BOREDOM
        else:
            return CognitiveState.FLOW
    
    def adjust_difficulty(self, input_data: UserInput) -> TaskDifficulty:
        """
        核心方法：根据用户输入调整任务难度
        
        参数:
            input_data: 用户输入数据
            
        返回:
            调整后的任务难度参数
            
        异常:
            ValueError: 如果输入数据无效
        """
        try:
            # 验证输入数据
            if not isinstance(input_data, UserInput):
                raise ValueError("无效的输入数据类型")
                
            # 记录历史数据
            self.history.append(input_data)
            if len(self.history) > self.history_size:
                self.history.pop(0)
            
            # 评估认知负荷
            cognitive_load = self._assess_cognitive_load(input_data)
            state = self._determine_state(cognitive_load)
            
            logger.info(f"当前认知状态: {state.value}, 负荷指数: {cognitive_load:.2f}")
            
            # 根据状态调整难度
            if state == CognitiveState.ANXIETY:
                # 焦虑状态：降维处理
                new_complexity = max(1, self.current_difficulty.complexity - 1)
                new_hint = min(3, self.current_difficulty.hint_level + 1)
                new_random = max(0.0, self.current_difficulty.randomness - 0.2)
                logger.info("检测到焦虑信号，执行降维策略")
                
            elif state == CognitiveState.BOREDOM:
                # 厌倦状态：引入挑战
                new_complexity = min(10, self.current_difficulty.complexity + 1)
                new_hint = max(0, self.current_difficulty.hint_level - 1)
                new_random = min(1.0, self.current_difficulty.randomness + 0.2)
                logger.info("检测到厌倦信号，引入挑战")
                
            else:
                # 心流状态：微调保持平衡
                new_complexity = self.current_difficulty.complexity
                new_hint = self.current_difficulty.hint_level
                new_random = self.current_difficulty.randomness
                logger.info("维持心流状态，微调参数")
            
            # 添加随机扰动（避免过于机械）
            if random.random() < 0.2:
                new_complexity = max(1, min(10, new_complexity + random.choice([-1, 1])))
            
            # 更新当前难度
            self.current_difficulty = TaskDifficulty(
                complexity=new_complexity,
                hint_level=new_hint,
                randomness=new_random
            )
            
            return self.current_difficulty
            
        except Exception as e:
            logger.error(f"难度调整失败: {str(e)}")
            raise RuntimeError(f"系统调整失败: {str(e)}") from e
    
    def get_cross_domain_analogy(self, domain: str = "math") -> Optional[str]:
        """
        辅助方法：生成跨域类比解释
        
        当用户处于焦虑状态时，提供跨领域类比帮助理解
        
        参数:
            domain: 当前知识领域
            
        返回:
            类比解释字符串或None
        """
        analogies = {
            "math": [
                "这就像学习骑自行车，开始需要辅助轮（提示），逐渐会找到平衡",
                "想象你在解谜，每个步骤都是通向宝藏的地图碎片"
            ],
            "programming": [
                "编程就像搭乐高积木，先从基础块开始，逐步构建复杂结构",
                "调试程序就像侦探破案，每个错误都是线索"
            ]
        }
        
        if domain in analogies:
            analogy = random.choice(analogies[domain])
            logger.info(f"生成跨域类比: {analogy}")
            return analogy
        return None
    
    def get_system_status(self) -> Dict:
        """
        获取系统状态信息
        
        返回:
            包含系统状态的字典
        """
        return {
            "current_difficulty": self.current_difficulty.__dict__,
            "history_size": len(self.history),
            "last_state": self._determine_state(
                self._assess_cognitive_load(self.history[-1])
            ).value if self.history else "no_data"
        }

# 示例用法
if __name__ == "__main__":
    # 初始化系统
    flow_system = AdaptiveFlowNavigationSystem()
    
    # 模拟用户交互
    test_inputs = [
        UserInput(0.2, 10, 0.9),  # 高性能 -> 可能厌倦
        UserInput(0.8, 25, 0.4),  # 低性能 -> 可能焦虑
        UserInput(0.4, 15, 0.7),  # 平衡状态
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n--- 交互 {i} ---")
        print(f"用户输入: 眼动={user_input.eye_movement_variance}, 频率={user_input.click_frequency}, 正确率={user_input.answer_accuracy}")
        
        try:
            new_diff = flow_system.adjust_difficulty(user_input)
            print(f"调整后难度: {new_diff}")
            
            if flow_system._determine_state(
                flow_system._assess_cognitive_load(user_input)
            ) == CognitiveState.ANXIETY:
                analogy = flow_system.get_cross_domain_analogy("programming")
                print(f"类比解释: {analogy}")
                
        except Exception as e:
            print(f"错误: {str(e)}")
    
    print("\n系统状态:", flow_system.get_system_status())