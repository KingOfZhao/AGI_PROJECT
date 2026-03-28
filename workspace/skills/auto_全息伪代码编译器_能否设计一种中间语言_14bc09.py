"""
全息伪代码编译器

该模块实现了一种将模糊的自然语言指令（如“力道柔和一点”）转换为机器人可执行精确参数代码
（如 {'pressure': -0.15, 'smoothness': 0.8}）的中间语言编译器。
它旨在解决人类隐性概念到机器显性指令的“最后一公里”转换问题。

主要组件:
- HolographicPseudoCompiler: 核心编译器类
- SemanticAligner: 语义-参数对齐处理器
- validate_parameters: 参数边界与安全性检查

作者: AGI System Core
版本: 1.0.0
"""

import logging
import re
import json
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExecutionDomain(Enum):
    """定义机器人执行的领域范围"""
    MANIPULATION = "manipulation"
    LOCOMOTION = "locomotion"
    SENSOR = "sensor"

@dataclass
class RobotParameter:
    """机器人参数的数据结构"""
    name: str
    value: float
    unit: str
    min_val: float
    max_val: float
    description: str = ""

@dataclass
class CompiledInstruction:
    """编译后的指令结构"""
    raw_text: str
    intent: str
    parameters: Dict[str, Any]
    confidence: float
    execution_domain: ExecutionDomain

class SemanticAligner:
    """
    语义对齐器：建立‘模糊语义-精确参数’的对齐库。
    负责解析自然语言中的修饰词并将其映射到具体的参数变化率或数值。
    """

    def __init__(self):
        # 模糊词到修饰因子的映射表
        # 例如："柔和" -> 减少力度，增加平滑度
        self._semantic_map = {
            "柔和": {"pressure": -0.15, "smoothness": 0.2, "velocity": -0.1},
            "猛烈": {"pressure": 0.30, "smoothness": -0.5, "velocity": 0.2},
            "快速": {"velocity": 0.5, "smoothness": -0.2, "pressure": 0.0},
            "慢速": {"velocity": -0.4, "smoothness": 0.3},
            "精准": {"tolerance": -0.8, "velocity": -0.2},
            "一点": {"intensity": 0.3},  # 程度修饰词
            "非常": {"intensity": 0.8},  # 程度修饰词
        }
        
        # 关键意图词到目标参数的映射
        self._intent_map = {
            "力道": "pressure",
            "压力": "pressure",
            "速度": "velocity",
            "轨迹": "smoothness",
            "加减速": "smoothness",
            "精度": "tolerance"
        }
        
        logger.info("SemanticAligner initialized with mapping tables.")

    def lookup_modifier(self, keyword: str) -> Optional[Dict[str, float]]:
        """
        辅助函数：查找关键词对应的参数修饰因子
        
        Args:
            keyword (str): 自然语言中的形容词或副词
            
        Returns:
            Optional[Dict[str, float]]: 参数调整字典，如果未找到则返回None
        """
        return self._semantic_map.get(keyword)

    def analyze_intent(self, text: str) -> Tuple[Optional[str], List[str]]:
        """
        分析文本中的意图和修饰词
        
        Args:
            text: 输入的自然语言文本
            
        Returns:
            (主要意图参数, 修饰词列表)
        """
        found_intent_key = None
        modifiers = []
        
        # 简单的分词匹配（实际场景应使用NLP模型）
        # 检查意图
        for key, param in self._intent_map.items():
            if key in text:
                found_intent_key = param
                break
                
        # 检查修饰词
        for key in self._semantic_map:
            if key in text:
                modifiers.append(key)
                
        return found_intent_key, modifiers


def validate_parameters(params: Dict[str, float], constraints: Dict[str, Tuple[float, float]]) -> bool:
    """
    辅助函数：验证生成的参数是否在安全边界内。
    
    Args:
        params: 待验证的参数字典 {param_name: value}
        constraints: 约束字典 {param_name: (min_val, max_val)}
        
    Returns:
        bool: 参数是否合法
        
    Raises:
        ValueError: 如果参数超出边界
    """
    for key, value in params.items():
        if key in constraints:
            min_val, max_val = constraints[key]
            if not (min_val <= value <= max_val):
                logger.error(f"Parameter validation failed: {key}={value} is out of bounds [{min_val}, {max_val}]")
                raise ValueError(f"Parameter {key} value {value} out of bounds.")
    logger.debug("Parameters validated successfully.")
    return True


class HolographicPseudoCompiler:
    """
    全息伪代码编译器主类。
    
    将模糊的自然语言教学转换为机器人可执行的参数代码。
    """
    
    # 机器人默认参数约束 (归一化值 -1.0 到 1.0 或具体单位)
    DEFAULT_CONSTRAINTS = {
        "pressure": (-1.0, 1.0),    # 相对压力变化
        "velocity": (-1.0, 1.0),    # 相对速度变化
        "smoothness": (0.0, 1.0),   # 平滑度 S (0: 线性, 1: 最平滑)
        "tolerance": (0.0, 0.1)     # 误差容忍度 (m)
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化编译器。
        
        Args:
            config: 可选的配置字典，可覆盖默认约束或添加自定义映射。
        """
        self.aligner = SemanticAligner()
        self.constraints = self.DEFAULT_CONSTRAINTS.copy()
        self.current_state = {
            "pressure": 0.5, 
            "velocity": 0.5, 
            "smoothness": 0.5, 
            "tolerance": 0.01
        } # 模拟当前机器人状态
        
        if config and 'constraints' in config:
            self.constraints.update(config['constraints'])
            
        logger.info("HolographicPseudoCompiler initialized.")

    def _calculate_new_state(self, modifiers: List[str], target_intent: Optional[str]) -> Dict[str, float]:
        """
        内部核心函数：根据修饰词计算新的参数状态。
        
        Args:
            modifiers: 提取出的修饰词列表
            target_intent: 主要目标的参数名
            
        Returns:
            计算后的新参数字典
        """
        delta_params: Dict[str, float] = {}
        
        # 聚合所有修饰词的影响
        for mod in modifiers:
            effect = self.aligner.lookup_modifier(mod)
            if effect:
                for param, val in effect.items():
                    if param not in delta_params:
                        delta_params[param] = 0.0
                    
                    # 如果是程度副词（如'一点'），它通常修饰前一个词，这里简化处理为乘数
                    # 实际实现需要更复杂的依存句法分析
                    if param == "intensity":
                        # 将强度应用到最近识别的参数上
                        if target_intent and target_intent in delta_params:
                            delta_params[target_intent] *= val
                    else:
                        delta_params[param] += val

        # 应用变化到当前状态
        new_state = self.current_state.copy()
        for param, delta in delta_params.items():
            if param in new_state:
                new_state[param] += delta
                
        return new_state

    def compile_instruction(self, natural_language_text: str) -> CompiledInstruction:
        """
        核心函数：编译自然语言指令。
        
        Args:
            natural_language_text: 输入的模糊指令，例如 "力道要柔和一点"
            
        Returns:
            CompiledInstruction: 包含可执行参数的对象
            
        Example:
            >>> compiler = HolographicPseudoCompiler()
            >>> instruction = compiler.compile_instruction("末端执行器力道柔和一点")
            >>> print(instruction.parameters['pressure'])
        """
        logger.info(f"Received compilation request: {natural_language_text}")
        
        try:
            # 1. 语义分析与对齐
            target_intent, modifiers = self.aligner.analyze_intent(natural_language_text)
            
            if not modifiers:
                logger.warning("No recognizable semantic modifiers found.")
                # 返回默认状态或抛出错误
                return CompiledInstruction(
                    raw_text=natural_language_text,
                    intent="unknown",
                    parameters={},
                    confidence=0.0,
                    execution_domain=ExecutionDomain.MANIPULATION
                )

            # 2. 参数计算
            calculated_params = self._calculate_new_state(modifiers, target_intent)
            
            # 3. 数据验证与边界检查
            validate_parameters(calculated_params, self.constraints)
            
            # 4. 生成可执行代码结构
            # 这里将归一化的参数转换为具体的指令描述（模拟）
            executable_params = self._generate_executable_dict(calculated_params)
            
            result = CompiledInstruction(
                raw_text=natural_language_text,
                intent=target_intent if target_intent else "general_adjustment",
                parameters=executable_params,
                confidence=0.85, # 模拟置信度
                execution_domain=ExecutionDomain.MANIPULATION
            )
            
            logger.info(f"Compilation successful. Intent: {result.intent}")
            return result

        except ValueError as ve:
            logger.error(f"Validation Error during compilation: {ve}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during compilation: {e}", exc_info=True)
            raise RuntimeError("Compilation failed due to internal error.") from e

    def _generate_executable_dict(self, norm_params: Dict[str, float]) -> Dict[str, Any]:
        """
        辅助函数：将归一化参数转换为具体的机器人指令格式。
        """
        # 这里的逻辑连接了'中间语言'到'底层代码'
        # 例如 smoothness S=0.8 对应具体的轨迹规划算法参数
        return {
            "timestamp": "now",
            "control_mode": "admittance",
            "setpoints": {
                "effector_pressure": f"{norm_params['pressure']:.2f} N",
                "trajectory_smoothing_factor": round(norm_params['smoothness'], 2),
                "max_velocity_scale": round(norm_params['velocity'], 2)
            },
            "safety_checks": "enabled"
        }

# 使用示例
if __name__ == "__main__":
    # 初始化编译器
    compiler = HolographicPseudoCompiler()
    
    test_cases = [
        "抓取鸡蛋时力道要柔和一点",
        "快速移动到目标点，但是要非常精准",
        "加减速曲线平滑度设为高"
    ]
    
    print("-" * 50)
    print("全息伪代码编译器测试")
    print("-" * 50)
    
    for text in test_cases:
        try:
            print(f"\n输入指令: {text}")
            result = compiler.compile_instruction(text)
            print(f"识别意图: {result.intent}")
            print(f"编译结果: {json.dumps(result.parameters, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"编译失败: {e}")
    
    # 边界检查测试
    print("\n测试边界检查...")
    try:
        # 假设输入了一个会导致参数溢出的指令（这里通过手动修改状态模拟，或构造极端词汇）
        # 构造一个极端的例子：假设 '猛烈' 修饰 '压力' 且超过了限制
        # 这里为了演示，我们直接调用验证函数
        validate_parameters({"pressure": 1.5}, HolographicPseudoCompiler.DEFAULT_CONSTRAINTS)
    except ValueError as e:
        print(f"成功捕获边界错误: {e}")
