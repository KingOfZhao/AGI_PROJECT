"""
跨域迁移中的技能重组模块

该模块实现了从源领域到目标领域的技能迁移，通过抽象底层逻辑并重新实例化的方式，
将异构领域的'真实节点'（SKILL）适配到新上下文中。

典型应用场景：
- 将游戏开发中的碰撞检测技能迁移到金融风控的异常相交检测
- 将图像处理中的边缘检测技能迁移到股票趋势分析

输入输出格式：
- 输入：源技能描述（JSON格式）、目标领域参数（字典）
- 输出：适配后的技能实例（包含重新实例化的函数和参数）

示例：
>>> source_skill = {
...     "domain": "game_dev",
...     "name": "collision_detection",
...     "math_model": "geometric_intersection",
...     "params": {"threshold": 0.5}
... }
>>> target_params = {"domain": "finance", "risk_level": "high"}
>>> migrated_skill = cross_domain_skill_reuse(source_skill, target_params)
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import numpy as np
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """技能节点数据结构"""
    domain: str
    name: str
    math_model: str
    params: Dict[str, Any]
    abstract_logic: Optional[str] = None

def validate_skill_structure(skill_data: Dict[str, Any]) -> bool:
    """
    验证技能数据结构是否符合要求
    
    Args:
        skill_data: 待验证的技能数据
        
    Returns:
        bool: 是否通过验证
        
    Raises:
        ValueError: 当数据结构不完整时抛出
    """
    required_fields = {'domain', 'name', 'math_model', 'params'}
    if not isinstance(skill_data, dict):
        logger.error("Invalid skill data type: expected dict")
        raise ValueError("Skill data must be a dictionary")
    
    missing_fields = required_fields - set(skill_data.keys())
    if missing_fields:
        logger.error(f"Missing required fields: {missing_fields}")
        raise ValueError(f"Missing required fields: {missing_fields}")
    
    if not isinstance(skill_data['params'], dict):
        logger.error("Invalid params type: expected dict")
        raise ValueError("Params must be a dictionary")
    
    logger.debug("Skill structure validation passed")
    return True

def extract_math_logic(skill: SkillNode) -> str:
    """
    提取技能的底层数学逻辑
    
    Args:
        skill: 抽象后的技能节点
        
    Returns:
        str: 抽象后的数学逻辑描述
    """
    # 这里使用模式匹配来提取数学逻辑
    # 实际应用中可以使用更复杂的NLP或代码分析技术
    math_patterns = {
        'collision': r'intersection|overlap|collide',
        'distance': r'distance|far|near',
        'threshold': r'threshold|limit|boundary'
    }
    
    abstract_logic = []
    for logic_type, pattern in math_patterns.items():
        if re.search(pattern, skill.name.lower()) or re.search(pattern, skill.math_model.lower()):
            abstract_logic.append(logic_type)
    
    if not abstract_logic:
        logger.warning(f"No recognized math logic found for skill: {skill.name}")
        return "generic_logic"
    
    logger.info(f"Extracted math logic: {abstract_logic} from skill: {skill.name}")
    return "_".join(sorted(abstract_logic))

def adapt_parameters(source_params: Dict[str, Any], target_domain: str) -> Dict[str, Any]:
    """
    将源参数适配到目标领域
    
    Args:
        source_params: 源领域参数
        target_domain: 目标领域名称
        
    Returns:
        Dict[str, Any]: 适配后的参数
    """
    # 定义领域间的参数映射规则
    param_mapping = {
        'game_dev': {
            'threshold': 'risk_threshold',
            'sensitivity': 'detection_sensitivity'
        },
        'finance': {
            'risk_threshold': 'collision_threshold',
            'detection_sensitivity': 'game_sensitivity'
        }
    }
    
    adapted_params = {}
    for param, value in source_params.items():
        if target_domain in param_mapping:
            # 查找参数映射
            mapped_param = param_mapping[target_domain].get(param, param)
            adapted_params[mapped_param] = value
            logger.debug(f"Mapped parameter {param} -> {mapped_param} for domain {target_domain}")
        else:
            # 没有映射规则则保持原样
            adapted_params[param] = value
    
    logger.info(f"Adapted parameters: {adapted_params} for domain: {target_domain}")
    return adapted_params

def create_skill_instance(abstract_logic: str, params: Dict[str, Any]) -> callable:
    """
    根据抽象逻辑和参数创建可执行的技能实例
    
    Args:
        abstract_logic: 抽象后的数学逻辑
        params: 适配后的参数
        
    Returns:
        callable: 可执行的技能函数
        
    Raises:
        NotImplementedError: 当逻辑类型不支持时抛出
    """
    def collision_intersection_detector(data: List[float], threshold: float = 0.5) -> bool:
        """碰撞/相交检测的通用实现"""
        if len(data) < 2:
            logger.warning("Insufficient data points for collision detection")
            return False
        
        # 简化的相交检测逻辑
        max_val = max(data)
        min_val = min(data)
        range_val = max_val - min_val
        
        if range_val <= 0:
            logger.debug("Zero range detected, no intersection possible")
            return False
            
        normalized_range = range_val / max(abs(max_val), abs(min_val), 1e-6)
        result = normalized_range > threshold
        logger.debug(f"Collision detection result: {result} (range={normalized_range}, threshold={threshold})")
        return result
    
    def distance_based_anomaly_detector(data: List[float], threshold: float = 0.3) -> bool:
        """基于距离的异常检测通用实现"""
        if len(data) < 2:
            logger.warning("Insufficient data points for distance detection")
            return False
            
        mean = np.mean(data)
        std_dev = np.std(data)
        
        if std_dev <= 0:
            logger.debug("Zero standard deviation detected, no anomaly possible")
            return False
            
        z_scores = [(x - mean) / std_dev for x in data]
        max_z = max(abs(z) for z in z_scores)
        result = max_z > threshold
        logger.debug(f"Anomaly detection result: {result} (max_z={max_z}, threshold={threshold})")
        return result
    
    # 根据抽象逻辑选择适当的实现
    logic_mapping = {
        'collision_intersection': collision_intersection_detector,
        'distance_threshold': distance_based_anomaly_detector,
        'collision_threshold': collision_intersection_detector,
        'distance_intersection': distance_based_anomaly_detector
    }
    
    if abstract_logic not in logic_mapping:
        logger.error(f"Unsupported abstract logic type: {abstract_logic}")
        raise NotImplementedError(f"No implementation available for logic: {abstract_logic}")
    
    # 使用装饰器添加参数验证
    @wraps(logic_mapping[abstract_logic])
    def wrapped_skill(*args, **kwargs):
        # 合并默认参数和用户参数
        final_params = {**params, **kwargs}
        
        # 参数边界检查
        if 'threshold' in final_params and not (0 <= final_params['threshold'] <= 1):
            logger.warning(f"Threshold {final_params['threshold']} out of [0,1] range, clipping")
            final_params['threshold'] = max(0, min(1, final_params['threshold']))
        
        return logic_mapping[abstract_logic](*args, **final_params)
    
    logger.info(f"Created skill instance for logic: {abstract_logic} with params: {params}")
    return wrapped_skill

def cross_domain_skill_reuse(
    source_skill: Dict[str, Any],
    target_params: Dict[str, Any],
    target_domain: Optional[str] = None
) -> Tuple[SkillNode, callable]:
    """
    跨域技能重组主函数
    
    Args:
        source_skill: 源技能数据
        target_params: 目标领域参数
        target_domain: 目标领域名称（可选，如果不提供则从参数中推断）
        
    Returns:
        Tuple[SkillNode, callable]: 包含抽象技能节点和可执行实例的元组
        
    Raises:
        ValueError: 当输入验证失败时抛出
    """
    # 1. 验证输入
    validate_skill_structure(source_skill)
    
    # 2. 创建抽象技能节点
    abstract_skill = SkillNode(
        domain=source_skill['domain'],
        name=source_skill['name'],
        math_model=source_skill['math_model'],
        params=source_skill['params']
    )
    logger.info(f"Created abstract skill node: {abstract_skill.name}")
    
    # 3. 提取数学逻辑
    abstract_logic = extract_math_logic(abstract_skill)
    abstract_skill.abstract_logic = abstract_logic
    
    # 4. 确定目标领域
    if target_domain is None:
        target_domain = target_params.get('domain', 'general')
    logger.info(f"Target domain set to: {target_domain}")
    
    # 5. 参数适配
    adapted_params = adapt_parameters(source_skill['params'], target_domain)
    
    # 6. 合并目标参数
    final_params = {**adapted_params, **target_params}
    logger.debug(f"Final parameters: {final_params}")
    
    # 7. 创建技能实例
    skill_instance = create_skill_instance(abstract_logic, final_params)
    
    return abstract_skill, skill_instance

# 示例用法
if __name__ == "__main__":
    # 游戏开发中的碰撞检测技能
    game_skill = {
        "domain": "game_dev",
        "name": "3D_collision_detection",
        "math_model": "geometric_intersection",
        "params": {"threshold": 0.7, "sensitivity": "high"}
    }
    
    # 金融风控参数
    finance_params = {
        "domain": "finance",
        "risk_level": "high",
        "detection_window": 30
    }
    
    try:
        # 执行跨域迁移
        abstract_skill, collision_detector = cross_domain_skill_reuse(
            game_skill, 
            finance_params
        )
        
        print(f"Abstract Skill: {abstract_skill}")
        
        # 测试迁移后的技能
        test_data = [1.2, 1.5, 3.8, 1.1, 0.9]
        result = collision_detector(test_data)
        print(f"Collision detection result: {result}")
        
    except ValueError as e:
        logger.error(f"Skill migration failed: {str(e)}")
    except NotImplementedError as e:
        logger.error(f"Skill implementation not available: {str(e)}")