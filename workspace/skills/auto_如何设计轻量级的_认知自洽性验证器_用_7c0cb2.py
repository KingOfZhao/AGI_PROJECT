"""
轻量级认知自洽性验证器

该模块实现了一个用于AGI系统的轻量级验证器，用于评估新生成的技能节点是否形成闭环。
验证器检查技能是否包含完整的"状态识别-操作动作-结果反馈"三元组。

输入格式:
    技能数据格式为字典，包含以下字段:
    - name: str, 技能名称
    - components: Dict[str, Any], 包含:
        - state_recognition: Dict[str, Any], 状态识别组件
        - operation_action: Dict[str, Any], 操作动作组件
        - result_feedback: Dict[str, Any], 结果反馈组件

输出格式:
    验证结果为字典，包含:
    - is_valid: bool, 是否通过验证
    - missing_components: List[str], 缺失的组件列表
    - suggestions: List[str], 改进建议
    - confidence_score: float, 自洽性置信度(0.0-1.0)

使用示例:
    >>> validator = CognitiveConsistencyValidator()
    >>> skill = {
    ...     "name": "repair_bike_chain",
    ...     "components": {
    ...         "state_recognition": {"type": "visual", "triggers": ["chain_slippage"]},
    ...         "operation_action": {"type": "physical", "steps": ["realign_chain"]},
    ...         "result_feedback": {"type": "auditory", "indicators": ["smooth_rotation"]}
    ...     }
    ... }
    >>> result = validator.validate_skill(skill)
    >>> print(result["is_valid"])
    True
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveConsistencyValidator")


@dataclass
class ValidationResult:
    """验证结果数据结构"""
    is_valid: bool
    missing_components: List[str]
    suggestions: List[str]
    confidence_score: float
    timestamp: str = datetime.now().isoformat()


class CognitiveConsistencyValidator:
    """
    轻量级认知自洽性验证器
    
    用于评估新生成的技能节点是否包含完整的认知闭环：
    状态识别 -> 操作动作 -> 结果反馈
    
    属性:
        min_confidence_threshold (float): 最小置信度阈值
        required_components (List[str]): 必需的组件列表
    """
    
    def __init__(self, min_confidence_threshold: float = 0.7):
        """
        初始化验证器
        
        参数:
            min_confidence_threshold: 最小置信度阈值，低于此值视为验证失败
        """
        self.min_confidence_threshold = min_confidence_threshold
        self.required_components = [
            "state_recognition",
            "operation_action",
            "result_feedback"
        ]
        logger.info(f"Initialized validator with threshold {min_confidence_threshold}")
    
    def _validate_structure(self, skill_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        辅助函数: 验证技能数据结构
        
        参数:
            skill_data: 待验证的技能数据
            
        返回:
            Tuple[验证是否通过, 错误消息列表]
        """
        errors = []
        
        if not isinstance(skill_data, dict):
            errors.append("Skill data must be a dictionary")
            return (False, errors)
        
        if "name" not in skill_data or not isinstance(skill_data["name"], str):
            errors.append("Skill must have a valid 'name' field")
        
        if "components" not in skill_data or not isinstance(skill_data["components"], dict):
            errors.append("Skill must have a 'components' dictionary")
        
        return (len(errors) == 0, errors)
    
    def _calculate_confidence(self, skill_data: Dict[str, Any]) -> float:
        """
        辅助函数: 计算技能的自洽性置信度
        
        参数:
            skill_data: 待评估的技能数据
            
        返回:
            置信度分数(0.0-1.0)
        """
        if "components" not in skill_data:
            return 0.0
        
        components = skill_data["components"]
        score = 0.0
        
        # 检查每个必需组件是否存在并包含必要内容
        for component in self.required_components:
            if component in components:
                comp_data = components[component]
                
                # 基础分: 组件存在
                score += 0.2
                
                # 内容分: 组件有类型定义
                if "type" in comp_data:
                    score += 0.1
                
                # 内容分: 组件有触发条件或指示器
                if component == "state_recognition" and "triggers" in comp_data:
                    score += 0.1
                elif component == "operation_action" and "steps" in comp_data:
                    score += 0.1
                elif component == "result_feedback" and "indicators" in comp_data:
                    score += 0.1
        
        # 归一化到0-1范围
        return min(max(score / 1.0, 0.0), 1.0)
    
    def validate_skill(self, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心函数: 验证技能的认知自洽性
        
        参数:
            skill_data: 待验证的技能数据
            
        返回:
            验证结果字典，包含:
            - is_valid: 是否通过验证
            - missing_components: 缺失的组件列表
            - suggestions: 改进建议
            - confidence_score: 自洽性置信度
            - timestamp: 验证时间戳
            
        异常:
            ValueError: 当输入数据无效时抛出
        """
        # 验证输入结构
        is_valid_structure, structure_errors = self._validate_structure(skill_data)
        if not is_valid_structure:
            logger.error(f"Invalid skill structure: {structure_errors}")
            raise ValueError(f"Invalid skill data: {', '.join(structure_errors)}")
        
        # 检查必需组件
        components = skill_data["components"]
        missing = [c for c in self.required_components if c not in components]
        
        # 生成建议
        suggestions = []
        if "state_recognition" in missing:
            suggestions.append("Add state recognition component with triggers")
        if "operation_action" in missing:
            suggestions.append("Add operation action component with steps")
        if "result_feedback" in missing:
            suggestions.append("Add result feedback component with indicators")
        
        # 计算置信度
        confidence = self._calculate_confidence(skill_data)
        
        # 确定验证结果
        is_valid = (
            len(missing) == 0 and 
            confidence >= self.min_confidence_threshold
        )
        
        result = ValidationResult(
            is_valid=is_valid,
            missing_components=missing,
            suggestions=suggestions,
            confidence_score=confidence
        )
        
        logger.info(
            f"Validated skill '{skill_data.get('name', 'unknown')}' - "
            f"Valid: {is_valid}, Confidence: {confidence:.2f}"
        )
        
        return result.__dict__
    
    def batch_validate(self, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        核心函数: 批量验证多个技能
        
        参数:
            skills: 待验证的技能列表
            
        返回:
            批量验证结果字典，包含:
            - total_skills: 总技能数
            - valid_skills: 有效技能数
            - invalid_skills: 无效技能数
            - average_confidence: 平均置信度
            - details: 每个技能的详细验证结果
        """
        if not skills or not isinstance(skills, list):
            logger.error("Invalid input: skills must be a non-empty list")
            raise ValueError("Input must be a non-empty list of skills")
        
        results = []
        valid_count = 0
        total_confidence = 0.0
        
        for skill in skills:
            try:
                result = self.validate_skill(skill)
                results.append({
                    "skill_name": skill.get("name", "unknown"),
                    "result": result
                })
                
                if result["is_valid"]:
                    valid_count += 1
                total_confidence += result["confidence_score"]
                
            except ValueError as e:
                logger.warning(f"Skipping invalid skill: {str(e)}")
                results.append({
                    "skill_name": skill.get("name", "unknown"),
                    "result": {
                        "is_valid": False,
                        "error": str(e)
                    }
                })
        
        batch_result = {
            "total_skills": len(skills),
            "valid_skills": valid_count,
            "invalid_skills": len(skills) - valid_count,
            "average_confidence": total_confidence / len(skills) if skills else 0.0,
            "details": results,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(
            f"Batch validation completed - "
            f"Valid: {valid_count}/{len(skills)}, "
            f"Avg Confidence: {batch_result['average_confidence']:.2f}"
        )
        
        return batch_result


if __name__ == "__main__":
    # 示例用法
    validator = CognitiveConsistencyValidator(min_confidence_threshold=0.7)
    
    # 示例1: 有效技能
    valid_skill = {
        "name": "repair_bike_chain",
        "components": {
            "state_recognition": {
                "type": "visual",
                "triggers": ["chain_slippage", "abnormal_sound"]
            },
            "operation_action": {
                "type": "physical",
                "steps": ["stop_bike", "realign_chain", "test_rotation"]
            },
            "result_feedback": {
                "type": "auditory",
                "indicators": ["smooth_rotation", "no_abnormal_sound"]
            }
        }
    }
    
    # 示例2: 无效技能(缺少结果反馈)
    invalid_skill = {
        "name": "adjust_bike_seat",
        "components": {
            "state_recognition": {
                "type": "tactile",
                "triggers": ["discomfort"]
            },
            "operation_action": {
                "type": "physical",
                "steps": ["loosen_bolt", "adjust_height", "tighten_bolt"]
            }
        }
    }
    
    # 验证单个技能
    print("Validating 'repair_bike_chain':")
    print(json.dumps(validator.validate_skill(valid_skill), indent=2))
    
    print("\nValidating 'adjust_bike_seat':")
    print(json.dumps(validator.validate_skill(invalid_skill), indent=2))
    
    # 批量验证
    print("\nBatch validation:")
    print(json.dumps(
        validator.batch_validate([valid_skill, invalid_skill]),
        indent=2
    ))