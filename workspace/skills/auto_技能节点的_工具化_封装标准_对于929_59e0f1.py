"""
高级技能节点工具化封装标准模块

本模块提供了将自然语言描述的Skill节点转化为结构化JSON Schema的工具，
用于判断节点是否具备API化潜质，并生成可供其他节点调用的标准化接口定义。

核心功能：
1. 自动解析自然语言描述的Skill节点
2. 判断API化潜质（基于输入输出明确性、副作用可控性等）
3. 生成符合OpenAPI规范的JSON Schema
4. 提供验证和测试机制

使用示例：
    >>> from skill_tooling import SkillParser
    >>> parser = SkillParser()
    >>> skill_desc = "将摄氏度转换为华氏度，输入温度值(数字)，输出转换后的温度值"
    >>> schema = parser.generate_schema(skill_desc)
    >>> print(schema)
    {
        "input": {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"}
            },
            "required": ["temperature"]
        },
        "output": {
            "type": "number",
            "description": "转换后的华氏度温度值"
        },
        "side_effects": false
    }
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillType(Enum):
    """技能节点类型枚举"""
    COMPUTATION = "computation"  # 纯计算型，无副作用
    IO_BOUND = "io_bound"       # I/O密集型，可能有副作用
    STATEFUL = "stateful"       # 有状态型，明显副作用
    UNKNOWN = "unknown"         # 无法确定类型

@dataclass
class SchemaValidationResult:
    """Schema验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    api_potential: float  # 0.0-1.0之间的API化潜质评分

class SkillParser:
    """
    技能节点解析器，将自然语言描述转化为结构化JSON Schema
    
    属性:
        keywords (Dict[str, List[str]]): 用于识别输入输出的关键词
        api_potential_threshold (float): API化潜质阈值，默认0.7
    """
    
    def __init__(self):
        """初始化解析器，设置默认关键词和阈值"""
        self.keywords = {
            "input": ["输入", "参数", "变量", "接收", "需要"],
            "output": ["输出", "返回", "结果", "生成", "返回值"],
            "side_effects": ["写入", "修改", "删除", "更新", "状态"]
        }
        self.api_potential_threshold = 0.7
        logger.info("SkillParser初始化完成")
    
    def _extract_parameters(self, text: str, keyword_type: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取参数信息
        
        参数:
            text: 输入文本
            keyword_type: 关键词类型（input/output/side_effects）
            
        返回:
            参数字典或None
        """
        if keyword_type not in self.keywords:
            raise ValueError(f"无效的keyword_type: {keyword_type}")
            
        for keyword in self.keywords[keyword_type]:
            if keyword in text:
                # 简单的参数提取逻辑（实际应用中可使用NLP技术）
                param_part = text.split(keyword)[1].split("，")[0].strip()
                params = [p.strip() for p in param_part.split("、") if p.strip()]
                
                if params:
                    properties = {}
                    for param in params:
                        # 尝试推断参数类型
                        param_type = self._infer_param_type(param)
                        properties[param] = {"type": param_type}
                    
                    return {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties.keys())
                    }
        return None
    
    def _infer_param_type(self, param_name: str) -> str:
        """
        推断参数类型
        
        参数:
            param_name: 参数名称
            
        返回:
            推断的JSON Schema类型
        """
        param_lower = param_name.lower()
        
        if any(kw in param_lower for kw in ["数", "量", "值", "温度", "时间"]):
            return "number"
        elif any(kw in param_lower for kw in ["列表", "数组", "集合"]):
            return "array"
        elif any(kw in param_lower for kw in ["布尔", "是否", "标志"]):
            return "boolean"
        else:
            return "string"
    
    def _detect_side_effects(self, text: str) -> Tuple[bool, float]:
        """
        检测技能是否有副作用
        
        参数:
            text: 输入文本
            
        返回:
            (是否有副作用, 副作用严重程度评分)
        """
        side_effect_keywords = self.keywords["side_effects"]
        has_side_effects = any(kw in text for kw in side_effect_keywords)
        severity = 0.0
        
        if has_side_effects:
            # 简单的严重程度评分逻辑
            severity = sum(1 for kw in side_effect_keywords if kw in text) / len(side_effect_keywords)
            
        return has_side_effects, severity
    
    def _calculate_api_potential(self, input_schema: Optional[Dict], 
                               output_schema: Optional[Dict], 
                               has_side_effects: bool,
                               side_effect_severity: float) -> float:
        """
        计算API化潜质评分
        
        参数:
            input_schema: 输入Schema
            output_schema: 输出Schema
            has_side_effects: 是否有副作用
            side_effect_severity: 副作用严重程度
            
        返回:
            0.0-1.0之间的API化潜质评分
        """
        score = 0.0
        
        # 输入输出明确性评分
        if input_schema and output_schema:
            score += 0.4
            if len(input_schema.get("properties", {})) > 0:
                score += 0.2
            if output_schema.get("type") != "unknown":
                score += 0.2
        elif input_schema or output_schema:
            score += 0.3
        
        # 副作用影响评分
        if has_side_effects:
            score -= 0.3 * side_effect_severity
        else:
            score += 0.2
            
        # 确保评分在0-1范围内
        return max(0.0, min(1.0, score))
    
    def generate_schema(self, skill_description: str) -> Dict[str, Any]:
        """
        从自然语言描述生成JSON Schema
        
        参数:
            skill_description: 技能节点的自然语言描述
            
        返回:
            符合OpenAPI规范的JSON Schema字典
            
        异常:
            ValueError: 如果输入描述为空或不是字符串
        """
        if not skill_description or not isinstance(skill_description, str):
            logger.error("无效的技能描述")
            raise ValueError("技能描述必须是非空字符串")
            
        logger.info(f"开始解析技能描述: {skill_description[:50]}...")
        
        # 提取输入输出参数
        input_schema = self._extract_parameters(skill_description, "input")
        output_schema = self._extract_parameters(skill_description, "output")
        
        # 检测副作用
        has_side_effects, severity = self._detect_side_effects(skill_description)
        
        # 计算API化潜质
        api_potential = self._calculate_api_potential(
            input_schema, output_schema, has_side_effects, severity
        )
        
        # 构建完整Schema
        schema = {
            "input": input_schema or {"type": "null", "description": "未识别到输入参数"},
            "output": output_schema or {"type": "null", "description": "未识别到输出参数"},
            "side_effects": {
                "has_side_effects": has_side_effects,
                "severity": severity
            },
            "metadata": {
                "api_potential": api_potential,
                "is_api_ready": api_potential >= self.api_potential_threshold,
                "skill_type": self._determine_skill_type(
                    input_schema, output_schema, has_side_effects
                ).value
            }
        }
        
        logger.info(f"生成Schema完成，API潜质评分: {api_potential:.2f}")
        return schema
    
    def _determine_skill_type(self, input_schema: Optional[Dict], 
                            output_schema: Optional[Dict], 
                            has_side_effects: bool) -> SkillType:
        """
        确定技能类型
        
        参数:
            input_schema: 输入Schema
            output_schema: 输出Schema
            has_side_effects: 是否有副作用
            
        返回:
            SkillType枚举值
        """
        if not input_schema and not output_schema:
            return SkillType.UNKNOWN
            
        if has_side_effects:
            return SkillType.STATEFUL
            
        if input_schema and output_schema:
            return SkillType.COMPUTATION
            
        return SkillType.IO_BOUND
    
    def validate_schema(self, schema: Dict[str, Any]) -> SchemaValidationResult:
        """
        验证生成的Schema是否符合标准
        
        参数:
            schema: 要验证的Schema字典
            
        返回:
            SchemaValidationResult对象
        """
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = ["input", "output", "side_effects", "metadata"]
        for field in required_fields:
            if field not in schema:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查输入输出结构
        if "input" in schema:
            if not isinstance(schema["input"], dict):
                errors.append("input字段必须是字典")
            elif "properties" not in schema["input"] and schema["input"].get("type") != "null":
                warnings.append("input缺少properties字段")
        
        if "output" in schema:
            if not isinstance(schema["output"], dict):
                errors.append("output字段必须是字典")
            elif "type" not in schema["output"]:
                warnings.append("output缺少type字段")
        
        # 检查API潜质评分
        api_potential = schema.get("metadata", {}).get("api_potential", 0.0)
        if not (0.0 <= api_potential <= 1.0):
            errors.append("api_potential必须在0.0-1.0之间")
        
        is_valid = len(errors) == 0
        result = SchemaValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            api_potential=api_potential
        )
        
        logger.info(f"Schema验证完成，有效: {is_valid}, 错误: {len(errors)}, 警告: {len(warnings)}")
        return result
    
    def batch_process(self, skill_descriptions: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理技能描述
        
        参数:
            skill_descriptions: 技能描述列表
            
        返回:
            生成的Schema列表
            
        异常:
            ValueError: 如果输入不是列表或为空
        """
        if not skill_descriptions or not isinstance(skill_descriptions, list):
            raise ValueError("输入必须是非空列表")
            
        logger.info(f"开始批量处理{len(skill_descriptions)}个技能描述")
        results = []
        
        for desc in skill_descriptions:
            try:
                schema = self.generate_schema(desc)
                validation = self.validate_schema(schema)
                
                if validation.is_valid:
                    results.append(schema)
                else:
                    logger.warning(f"无效Schema，跳过: {validation.errors}")
                    results.append(None)
            except Exception as e:
                logger.error(f"处理技能描述时出错: {str(e)}")
                results.append(None)
        
        logger.info(f"批量处理完成，成功{len([r for r in results if r])}个，失败{len([r for r in results if not r])}个")
        return results

if __name__ == "__main__":
    # 示例用法
    parser = SkillParser()
    
    # 示例1: 温度转换技能
    temp_skill = "将摄氏度转换为华氏度，输入温度值(数字)，输出转换后的温度值"
    schema1 = parser.generate_schema(temp_skill)
    print("\n温度转换技能Schema:")
    print(json.dumps(schema1, indent=2, ensure_ascii=False))
    
    # 示例2: 数据库更新技能
    db_skill = "更新数据库中的用户信息，输入用户ID和更新字段，返回更新状态，会修改数据库"
    schema2 = parser.generate_schema(db_skill)
    print("\n数据库更新技能Schema:")
    print(json.dumps(schema2, indent=2, ensure_ascii=False))
    
    # 验证Schema
    validation1 = parser.validate_schema(schema1)
    print(f"\n温度转换技能验证结果: 有效={validation1.is_valid}, API潜质={validation1.api_potential:.2f}")
    
    validation2 = parser.validate_schema(schema2)
    print(f"数据库更新技能验证结果: 有效={validation2.is_valid}, API潜质={validation2.api_potential:.2f}")