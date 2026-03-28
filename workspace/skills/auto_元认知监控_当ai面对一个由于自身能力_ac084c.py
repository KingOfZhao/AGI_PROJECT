"""
元认知监控模块

本模块实现了AGI系统的元认知监控功能，用于检测AI是否面临超出自身能力边界的问题，
并做出适当的响应（寻求外部工具或人类帮助，而非胡乱生成答案）。

核心功能：
1. 评估问题难度与自身能力边界
2. 监控回答置信度
3. 主动触发外部求助机制

典型使用场景：
- 超大质数计算
- 复杂数学证明
- 需要外部工具的任务（如精确计算、实时数据查询）
- 伦理敏感决策

数据流：
输入 -> 能力评估 -> 置信度计算 -> 决策生成 -> (内部解决/外部求助)
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("metacognitive_monitor.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class CapabilityLevel(Enum):
    """系统能力级别枚举"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    EXPERT = auto()


class ResponseType(Enum):
    """响应类型枚举"""
    INTERNAL_SOLUTION = auto()  # 系统内部解决
    TOOL_ASSISTED = auto()      # 需要工具辅助
    HUMAN_HELP = auto()         # 需要人类帮助
    UNKNOWN = auto()            # 无法确定


@dataclass
class MetacognitiveAssessment:
    """元认知评估结果数据结构"""
    problem_type: str
    difficulty_score: float  # 0.0-1.0
    capability_match: float  # 0.0-1.0
    confidence: float       # 0.0-1.0
    response_type: ResponseType
    recommended_action: str
    additional_resources: Optional[Dict[str, Any]] = None


class MetacognitiveMonitor:
    """
    元认知监控核心类
    
    实现了AI系统的自我评估和决策机制，用于判断问题是否超出能力边界，
    并决定适当的响应方式。
    """
    
    def __init__(self, 
                 capability_level: CapabilityLevel = CapabilityLevel.MEDIUM,
                 confidence_threshold: float = 0.7,
                 difficulty_threshold: float = 0.8):
        """
        初始化元认知监控器
        
        参数:
            capability_level: 系统当前能力级别
            confidence_threshold: 内部解决的最低置信度阈值
            difficulty_threshold: 超出能力边界的难度阈值
        """
        self.capability_level = capability_level
        self.confidence_threshold = confidence_threshold
        self.difficulty_threshold = difficulty_threshold
        self._external_tools = {}
        self._human_help_callback = None
        
        logger.info(f"MetacognitiveMonitor initialized with capability: {capability_level.name}")
    
    def register_external_tool(self, tool_name: str, tool_func: Callable) -> None:
        """
        注册外部工具函数
        
        参数:
            tool_name: 工具名称
            tool_func: 工具函数
        """
        if not callable(tool_func):
            raise ValueError("Tool function must be callable")
            
        self._external_tools[tool_name] = tool_func
        logger.debug(f"Registered external tool: {tool_name}")
    
    def set_human_help_callback(self, callback: Callable) -> None:
        """
        设置人类帮助回调函数
        
        参数:
            callback: 回调函数，接收问题描述并返回人类提供的解决方案
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")
            
        self._human_help_callback = callback
        logger.debug("Human help callback configured")
    
    def assess_problem(self, problem: str, context: Optional[Dict[str, Any]] = None) -> MetacognitiveAssessment:
        """
        评估问题难度和自身能力匹配度
        
        参数:
            problem: 问题描述
            context: 问题上下文信息
            
        返回:
            MetacognitiveAssessment: 元认知评估结果
        """
        if not problem or not isinstance(problem, str):
            raise ValueError("Problem description must be a non-empty string")
            
        context = context or {}
        
        try:
            # 1. 分析问题类型
            problem_type = self._classify_problem(problem, context)
            
            # 2. 评估问题难度
            difficulty = self._evaluate_difficulty(problem, problem_type, context)
            
            # 3. 评估能力匹配度
            capability_match = self._evaluate_capability_match(problem_type)
            
            # 4. 计算置信度
            confidence = self._calculate_confidence(difficulty, capability_match)
            
            # 5. 确定响应类型
            response_type, recommended_action = self._determine_response(
                difficulty, capability_match, confidence
            )
            
            # 6. 准备额外资源
            additional_resources = None
            if response_type == ResponseType.TOOL_ASSISTED:
                additional_resources = {"available_tools": list(self._external_tools.keys())}
            elif response_type == ResponseType.HUMAN_HELP:
                additional_resources = {"help_callback_available": self._human_help_callback is not None}
            
            assessment = MetacognitiveAssessment(
                problem_type=problem_type,
                difficulty_score=difficulty,
                capability_match=capability_match,
                confidence=confidence,
                response_type=response_type,
                recommended_action=recommended_action,
                additional_resources=additional_resources
            )
            
            logger.info(f"Problem assessment: {assessment}")
            return assessment
            
        except Exception as e:
            logger.error(f"Error assessing problem: {str(e)}", exc_info=True)
            return MetacognitiveAssessment(
                problem_type="unknown",
                difficulty_score=1.0,
                capability_match=0.0,
                confidence=0.0,
                response_type=ResponseType.UNKNOWN,
                recommended_action="Error occurred during assessment"
            )
    
    def execute_response(self, assessment: MetacognitiveAssessment, problem: str) -> Any:
        """
        根据评估结果执行响应
        
        参数:
            assessment: 元认知评估结果
            problem: 原始问题描述
            
        返回:
            Any: 解决方案或帮助请求结果
        """
        if not isinstance(assessment, MetacognitiveAssessment):
            raise TypeError("assessment must be a MetacognitiveAssessment instance")
            
        try:
            if assessment.response_type == ResponseType.INTERNAL_SOLUTION:
                logger.info("Attempting internal solution")
                return self._attempt_internal_solution(problem)
                
            elif assessment.response_type == ResponseType.TOOL_ASSISTED:
                logger.info("Seeking tool-assisted solution")
                return self._seek_tool_assistance(problem)
                
            elif assessment.response_type == ResponseType.HUMAN_HELP:
                logger.info("Requesting human help")
                return self._request_human_help(problem)
                
            else:
                logger.warning("Unknown response type, defaulting to human help")
                return self._request_human_help(problem)
                
        except Exception as e:
            logger.error(f"Error executing response: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "fallback_action": "human_help_required"
            }
    
    def _classify_problem(self, problem: str, context: Dict[str, Any]) -> str:
        """
        分类问题类型（内部辅助方法）
        
        参数:
            problem: 问题描述
            context: 问题上下文
            
        返回:
            str: 问题类型标识
        """
        # 这里实现简单的问题分类逻辑
        # 实际应用中可以使用更复杂的NLP或机器学习模型
        
        if any(keyword in problem.lower() for keyword in ["prime", "质数", "素数"]):
            return "math/prime_number"
        elif any(keyword in problem.lower() for keyword in ["prove", "证明", "theorem"]):
            return "math/proof"
        elif any(keyword in problem.lower() for keyword in ["calculate", "计算", "compute"]):
            return "math/calculation"
        elif any(keyword in problem.lower() for keyword in ["ethical", "伦理", "moral"]):
            return "ethics/decision"
        else:
            return "general/unknown"
    
    def _evaluate_difficulty(self, problem: str, problem_type: str, context: Dict[str, Any]) -> float:
        """
        评估问题难度（内部辅助方法）
        
        参数:
            problem: 问题描述
            problem_type: 问题类型
            context: 问题上下文
            
        返回:
            float: 难度分数 (0.0-1.0)
        """
        # 基于问题类型和长度简单评估难度
        # 实际应用中可以实现更复杂的评估逻辑
        
        base_difficulty = 0.5
        
        # 质数相关问题的特殊处理
        if problem_type == "math/prime_number":
            if any(str(x) in problem for x in range(10**6, 10**9)):
                return min(1.0, base_difficulty + 0.4)
            elif any(str(x) in problem for x in range(10**9, 10**12)):
                return min(1.0, base_difficulty + 0.8)
        
        # 问题长度作为难度指标
        if len(problem) > 200:
            base_difficulty += 0.2
        elif len(problem) > 500:
            base_difficulty += 0.4
            
        return min(1.0, max(0.0, base_difficulty))
    
    def _evaluate_capability_match(self, problem_type: str) -> float:
        """
        评估能力匹配度（内部辅助方法）
        
        参数:
            problem_type: 问题类型
            
        返回:
            float: 能力匹配分数 (0.0-1.0)
        """
        # 基于系统当前能力级别和问题类型评估匹配度
        capability_map = {
            CapabilityLevel.LOW: {
                "math/prime_number": 0.2,
                "math/proof": 0.1,
                "math/calculation": 0.3,
                "ethics/decision": 0.4,
                "general/unknown": 0.5
            },
            CapabilityLevel.MEDIUM: {
                "math/prime_number": 0.4,
                "math/proof": 0.3,
                "math/calculation": 0.6,
                "ethics/decision": 0.7,
                "general/unknown": 0.6
            },
            CapabilityLevel.HIGH: {
                "math/prime_number": 0.6,
                "math/proof": 0.5,
                "math/calculation": 0.8,
                "ethics/decision": 0.9,
                "general/unknown": 0.7
            },
            CapabilityLevel.EXPERT: {
                "math/prime_number": 0.8,
                "math/proof": 0.7,
                "math/calculation": 0.9,
                "ethics/decision": 0.95,
                "general/unknown": 0.8
            }
        }
        
        return capability_map.get(self.capability_level, {}).get(problem_type, 0.5)
    
    def _calculate_confidence(self, difficulty: float, capability_match: float) -> float:
        """
        计算置信度（内部辅助方法）
        
        参数:
            difficulty: 难度分数
            capability_match: 能力匹配分数
            
        返回:
            float: 置信度分数 (0.0-1.0)
        """
        # 简单置信度计算：能力匹配度减去难度分数的一部分
        confidence = capability_match - (difficulty * 0.5)
        return min(1.0, max(0.0, confidence))
    
    def _determine_response(self, difficulty: float, capability_match: float, confidence: float) -> Tuple[ResponseType, str]:
        """
        确定响应类型（内部辅助方法）
        
        参数:
            difficulty: 难度分数
            capability_match: 能力匹配分数
            confidence: 置信度分数
            
        返回:
            Tuple[ResponseType, str]: (响应类型, 推荐操作描述)
        """
        if confidence >= self.confidence_threshold:
            return ResponseType.INTERNAL_SOLUTION, "Attempt internal solution with high confidence"
        
        if difficulty > self.difficulty_threshold:
            if self._external_tools:
                return ResponseType.TOOL_ASSISTED, "Seek tool-assisted solution due to high difficulty"
            else:
                return ResponseType.HUMAN_HELP, "Request human help due to high difficulty and no available tools"
        
        if capability_match < 0.5:
            return ResponseType.HUMAN_HELP, "Request human help due to low capability match"
        
        return ResponseType.TOOL_ASSISTED, "Seek tool-assisted solution as fallback"
    
    def _attempt_internal_solution(self, problem: str) -> Any:
        """
        尝试内部解决方案（内部辅助方法）
        
        参数:
            problem: 问题描述
            
        返回:
            Any: 解决方案结果
        """
        # 这里实现简单的内部解决方案逻辑
        # 实际应用中可以调用内部模型或算法
        
        if "prime" in problem.lower() or "质数" in problem or "素数" in problem:
            # 示例：简单的质数检查（仅用于演示，不适用于大数）
            try:
                num = int(''.join(filter(str.isdigit, problem)))
                if num < 10**6:  # 仅对小数有效
                    is_prime = self._is_prime(num)
                    return {
                        "success": True,
                        "solution": f"{num} is {'a prime' if is_prime else 'not a prime'} number",
                        "method": "internal"
                    }
            except (ValueError, TypeError):
                pass
                
        return {
            "success": False,
            "error": "Internal solution not available",
            "fallback_action": "tool_or_human_help"
        }
    
    def _seek_tool_assistance(self, problem: str) -> Any:
        """
        寻求工具辅助解决方案（内部辅助方法）
        
        参数:
            problem: 问题描述
            
        返回:
            Any: 工具辅助解决方案结果
        """
        if not self._external_tools:
            return {
                "success": False,
                "error": "No external tools available",
                "fallback_action": "human_help"
            }
            
        # 选择合适的工具（这里简化处理，实际应用中可以实现更智能的工具选择）
        for tool_name, tool_func in self._external_tools.items():
            try:
                result = tool_func(problem)
                if result.get("success", False):
                    return {
                        "success": True,
                        "solution": result["solution"],
                        "tool_used": tool_name,
                        "method": "tool_assisted"
                    }
            except Exception as e:
                logger.warning(f"Tool {tool_name} failed: {str(e)}")
                continue
                
        return {
            "success": False,
            "error": "All available tools failed",
            "fallback_action": "human_help"
        }
    
    def _request_human_help(self, problem: str) -> Any:
        """
        请求人类帮助（内部辅助方法）
        
        参数:
            problem: 问题描述
            
        返回:
            Any: 人类帮助结果
        """
        if not self._human_help_callback:
            return {
                "success": False,
                "error": "No human help callback configured",
                "action_required": "Please seek human assistance manually"
            }
            
        try:
            solution = self._human_help_callback(problem)
            return {
                "success": True,
                "solution": solution,
                "method": "human_help"
            }
        except Exception as e:
            logger.error(f"Human help callback failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "action_required": "Human help callback failed, please seek assistance manually"
            }
    
    @staticmethod
    def _is_prime(n: int) -> bool:
        """
        简单的质数检查函数（仅用于演示，不适用于大数）
        
        参数:
            n: 要检查的数字
            
        返回:
            bool: 是否为质数
        """
        if n <= 1:
            return False
        if n <= 3:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        w = 2
        while i * i <= n:
            if n % i == 0:
                return False
            i += w
            w = 6 - w
        return True


# 示例使用
if __name__ == "__main__":
    # 初始化元认知监控器
    monitor = MetacognitiveMonitor(
        capability_level=CapabilityLevel.HIGH,
        confidence_threshold=0.6,
        difficulty_threshold=0.75
    )
    
    # 注册外部工具
    def mock_prime_tool(problem: str) -> Dict[str, Any]:
        """模拟质数检查工具"""
        try:
            num = int(''.join(filter(str.isdigit, problem)))
            # 这里只是模拟，实际工具应该实现真正的质数检查
            if num > 10**6:
                return {
                    "success": True,
                    "solution": f"{num} is too large to check with internal method, but tool indicates it's likely prime"
                }
            return {
                "success": True,
                "solution": f"{num} is a prime number (verified by tool)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    monitor.register_external_tool("prime_checker", mock_prime_tool)
    
    # 设置人类帮助回调
    def mock_human_help(problem: str) -> str:
        """模拟人类帮助回调"""
        return f"Human expert provided solution for: {problem}"
    
    monitor.set_human_help_callback(mock_human_help)
    
    # 测试用例
    test_problems = [
        "检查数字17是否是质数",
        "计算第1000000个质数",
        "证明费马大定理",
        "计算圆周率的前1000位",
        "做出一个伦理决策：自动驾驶汽车应该优先保护乘客还是行人？"
    ]
    
    for problem in test_problems:
        print(f"\n=== 测试问题: {problem} ===")
        assessment = monitor.assess_problem(problem)
        print(f"评估结果: 难度={assessment.difficulty_score:.2f}, 能力匹配={assessment.capability_match:.2f}, 置信度={assessment.confidence:.2f}")
        print(f"推荐操作: {assessment.recommended_action} ({assessment.response_type.name})")
        
        result = monitor.execute_response(assessment, problem)
        print("执行结果:", result)