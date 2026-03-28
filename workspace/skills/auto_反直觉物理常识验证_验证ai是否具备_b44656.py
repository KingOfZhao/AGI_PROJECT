"""
模块名称: auto_反直觉物理常识验证_验证ai是否具备_b44656
描述: 【反直觉物理常识验证】验证AI是否具备‘真实节点’中的物理体感。
      本模块用于评估AI在零重力环境下的物理常识理解能力。
作者: 高级Python工程师
版本: 1.0.0
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhysicsResponseType(Enum):
    """物理响应类型枚举"""
    CORRECT_INTUITION = "correct_intuition"  # 正确理解反直觉物理
    NAIVE_TEXT = "naive_text"  # 仅基于文本统计的错误理解
    PARTIAL_SOLUTION = "partial_solution"  # 部分正确的解决方案
    INVALID_RESPONSE = "invalid_response"  # 无效响应


@dataclass
class PhysicsValidationResult:
    """物理验证结果数据类"""
    response_type: PhysicsResponseType
    score: float  # 0.0到1.0之间的评分
    explanation: str
    detected_keywords: List[str]
    missing_keywords: List[str]
    has_physical_intuition: bool


class ZeroGravityPhysicsValidator:
    """
    零重力物理常识验证器
    
    用于验证AI对零重力环境下物理行为的理解是否具备真实物理体感，
    而非仅基于文本统计的模式匹配。
    """
    
    # 关键物理概念关键词
    CORE_PHYSICS_KEYWORDS = {
        "反作用力": ["反作用力", "牛顿第三定律", "反冲", "反弹"],
        "动量守恒": ["动量守恒", "动量", "动量交换"],
        "参考系": ["参考系", "惯性系", "非惯性"],
        "力偶": ["力偶", "旋转", "扭矩"]
    }
    
    # 解决方案关键词
    SOLUTION_KEYWORDS = {
        "固定装置": ["磁力靴", "固定", "吸附", "束缚", "夹具", "固定装置"],
        "替代工具": ["爆炸钉", "射钉枪", "气动工具", "电动工具"],
        "环境改造": ["真空吸附", "负压", "粘合剂"]
    }
    
    # 错误响应模式
    ERROR_PATTERNS = [
        r"挥动\s*锤子",
        r"敲击\s*钉子",
        r"像\s*在\s*地球\s*上\s*一样",
        r"正常\s*使用",
        r"直接\s*敲打"
    ]

    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器
        
        参数:
            strict_mode: 是否启用严格模式（默认True）
        """
        self.strict_mode = strict_mode
        self._validate_parameters()
        logger.info("ZeroGravityPhysicsValidator 初始化完成，严格模式: %s", strict_mode)

    def _validate_parameters(self) -> None:
        """验证初始化参数"""
        if not isinstance(self.strict_mode, bool):
            raise ValueError("strict_mode 必须是布尔值")

    def validate_response(self, response: str) -> PhysicsValidationResult:
        """
        验证AI响应的物理正确性
        
        参数:
            response: AI生成的响应文本
            
        返回:
            PhysicsValidationResult: 包含验证结果的详细数据
            
        示例:
            >>> validator = ZeroGravityPhysicsValidator()
            >>> result = validator.validate_response(
            ...     "在零重力环境下，直接挥动锤子会导致人反方向旋转，..."
            ... )
        """
        if not response or not isinstance(response, str):
            logger.error("无效输入: 响应为空或非字符串")
            return PhysicsValidationResult(
                response_type=PhysicsResponseType.INVALID_RESPONSE,
                score=0.0,
                explanation="输入响应无效",
                detected_keywords=[],
                missing_keywords=list(self.CORE_PHYSICS_KEYWORDS.keys()),
                has_physical_intuition=False
            )
        
        # 清理输入文本
        cleaned_response = self._preprocess_text(response)
        
        # 检测关键词
        detected_core = self._detect_keywords(cleaned_response, self.CORE_PHYSICS_KEYWORDS)
        detected_solution = self._detect_keywords(cleaned_response, self.SOLUTION_KEYWORDS)
        
        # 检查错误模式
        error_detected = self._check_error_patterns(cleaned_response)
        
        # 计算评分和结果类型
        score, response_type, explanation = self._calculate_score(
            detected_core, detected_solution, error_detected
        )
        
        # 确定缺失的关键词
        missing_core = [k for k in self.CORE_PHYSICS_KEYWORDS if k not in detected_core]
        missing_solution = [k for k in self.SOLUTION_KEYWORDS if k not in detected_solution]
        
        result = PhysicsValidationResult(
            response_type=response_type,
            score=score,
            explanation=explanation,
            detected_keywords=list(detected_core.keys()) + list(detected_solution.keys()),
            missing_keywords=missing_core + missing_solution,
            has_physical_intuition=score > 0.6
        )
        
        logger.info("验证完成 - 类型: %s, 得分: %.2f", response_type.value, score)
        return result

    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本：标准化格式、去除多余空格等
        
        参数:
            text: 原始文本
            
        返回:
            清理后的文本
        """
        # 去除首尾空格，合并多个空格
        cleaned = ' '.join(text.split())
        # 统一标点符号
        cleaned = cleaned.replace('，', ',').replace('。', '.').replace('！', '!')
        return cleaned.lower()

    def _detect_keywords(
        self, 
        text: str, 
        keyword_dict: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        检测文本中的关键词
        
        参数:
            text: 要分析的文本
            keyword_dict: 关键词字典 {类别: [关键词列表]}
            
        返回:
            检测到的关键词字典 {类别: [匹配的关键词]}
        """
        detected = {}
        for category, keywords in keyword_dict.items():
            matched = []
            for keyword in keywords:
                if keyword.lower() in text:
                    matched.append(keyword)
            if matched:
                detected[category] = matched
        return detected

    def _check_error_patterns(self, text: str) -> bool:
        """
        检查文本中的错误模式
        
        参数:
            text: 要检查的文本
            
        返回:
            是否检测到错误模式
        """
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, text):
                logger.warning("检测到错误模式: %s", pattern)
                return True
        return False

    def _calculate_score(
        self,
        detected_core: Dict[str, List[str]],
        detected_solution: Dict[str, List[str]],
        error_detected: bool
    ) -> Tuple[float, PhysicsResponseType, str]:
        """
        计算物理理解评分
        
        参数:
            detected_core: 检测到的核心物理概念
            detected_solution: 检测到的解决方案
            error_detected: 是否检测到错误模式
            
        返回:
            (评分, 响应类型, 解释)
        """
        if error_detected:
            return (
                0.2,
                PhysicsResponseType.NAIVE_TEXT,
                "响应中包含错误物理理解，显示缺乏真实物理体感"
            )
        
        core_score = len(detected_core) / len(self.CORE_PHYSICS_KEYWORDS)
        solution_score = len(detected_solution) / len(self.SOLUTION_KEYWORDS)
        
        # 综合评分 (核心物理概念权重更高)
        total_score = 0.6 * core_score + 0.4 * solution_score
        
        if self.strict_mode:
            total_score = min(total_score * 1.2, 1.0)  # 严格模式下调整评分
        
        # 确定响应类型
        if total_score >= 0.8:
            response_type = PhysicsResponseType.CORRECT_INTUITION
            explanation = "响应显示对零重力物理有深刻理解，具备真实物理体感"
        elif total_score >= 0.5:
            response_type = PhysicsResponseType.PARTIAL_SOLUTION
            explanation = "响应包含部分正确理解，但物理体感不够完整"
        else:
            response_type = PhysicsResponseType.NAIVE_TEXT
            explanation = "响应基于文本统计，缺乏真实物理理解"
        
        return (total_score, response_type, explanation)

    def generate_report(self, result: PhysicsValidationResult) -> str:
        """
        生成详细的验证报告
        
        参数:
            result: 验证结果
            
        返回:
            格式化的报告字符串
        """
        report = f"""
=== 零重力物理常识验证报告 ===
响应类型: {result.response_type.value}
物理体感评分: {result.score:.2f}/1.0
具备真实物理体感: {'是' if result.has_physical_intuition else '否'}

检测到的物理概念: {', '.join(result.detected_keywords) or '无'}
缺失的关键概念: {', '.join(result.missing_keywords) or '无'}

解释: {result.explanation}
"""
        return report.strip()


# 使用示例
if __name__ == "__main__":
    # 示例1: 正确理解物理体感的响应
    good_response = """
    在零重力环境下，直接挥动锤子会导致根据牛顿第三定律产生反作用力，
    使人向相反方向旋转。解决方案包括：1) 使用磁力靴将自己固定在表面，
    2) 使用爆炸钉或气动工具代替传统锤击，3) 将锤子临时吸附在墙壁上
    作为固定支点。
    """
    
    # 示例2: 基于文本统计的错误响应
    bad_response = """
    在零重力环境下，你可以像在地球上一样挥动锤子把钉子敲进木头，
    只需要小心控制力度即可。
    """
    
    validator = ZeroGravityPhysicsValidator(strict_mode=True)
    
    print("=== 测试1: 正确物理理解 ===")
    result1 = validator.validate_response(good_response)
    print(validator.generate_report(result1))
    
    print("\n=== 测试2: 错误物理理解 ===")
    result2 = validator.validate_response(bad_response)
    print(validator.generate_report(result2))
    
    print("\n=== 测试3: 边界情况测试 ===")
    try:
        # 测试空输入
        empty_result = validator.validate_response("")
        print(f"空输入处理: {empty_result.response_type.value}")
        
        # 测试非字符串输入
        validator.validate_response(123)  # type: ignore
    except Exception as e:
        print(f"正确捕获异常: {str(e)}")