"""
模块: auto_人机共生_设计一种_最小化反事实实践接口_efee8f
描述: 实现人机共生环境下的假设证伪接口，将模糊假设转化为可执行的验证行动清单。
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HypothesisCategory(Enum):
    """假设类别枚举"""
    SPATIAL = "spatial"          # 空间相关
    TEMPORAL = "temporal"        # 时间相关
    BEHAVIORAL = "behavioral"    # 行为相关
    CAUSAL = "causal"           # 因果相关
    UNKNOWN = "unknown"         # 未知类别

@dataclass
class Hypothesis:
    """假设数据结构"""
    content: str                          # 假设内容
    category: HypothesisCategory         # 假设类别
    confidence: float = 0.0              # 置信度 [0.0, 1.0]
    variables: List[str] = field(default_factory=list)  # 涉及的变量
    constraints: List[str] = field(default_factory=list) # 约束条件

@dataclass
class FalsificationAction:
    """证伪行动项"""
    action_id: str                       # 行动ID
    description: str                     # 行动描述
    expected_duration: str               # 预期持续时间
    required_resources: List[str]        # 所需资源
    success_criteria: str                # 成功标准
    risk_level: str = "low"              # 风险等级: low, medium, high
    priority: int = 1                    # 优先级 [1-5]

class HypothesisValidator:
    """假设验证器，处理输入验证和边界检查"""
    
    @staticmethod
    def validate_hypothesis(hypothesis: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        验证假设数据结构
        
        Args:
            hypothesis: 待验证的假设字典
            
        Returns:
            Tuple[验证结果, 错误信息]
        """
        if not isinstance(hypothesis, dict):
            return False, "Hypothesis must be a dictionary"
        
        required_fields = ['content', 'category']
        for field in required_fields:
            if field not in hypothesis:
                return False, f"Missing required field: {field}"
        
        if not isinstance(hypothesis['content'], str) or len(hypothesis['content']) < 5:
            return False, "Content must be a string with at least 5 characters"
        
        if hypothesis['category'] not in [cat.value for cat in HypothesisCategory]:
            return False, f"Invalid category. Must be one of: {[cat.value for cat in HypothesisCategory]}"
        
        if 'confidence' in hypothesis:
            conf = hypothesis['confidence']
            if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                return False, "Confidence must be a number between 0.0 and 1.0"
        
        return True, None

class FalsificationGenerator:
    """证伪清单生成器核心类"""
    
    def __init__(self):
        self.validator = HypothesisValidator()
        self._action_templates = self._initialize_templates()
        logger.info("FalsificationGenerator initialized with %d templates", 
                   len(self._action_templates))
    
    def _initialize_templates(self) -> Dict[HypothesisCategory, List[Dict]]:
        """初始化行动模板库"""
        return {
            HypothesisCategory.SPATIAL: [
                {
                    "description_template": "在不同位置{}进行对比实验",
                    "duration": "1-2小时",
                    "resources": ["测量工具", "记录表"],
                    "success_criteria": "观察到显著差异(p<0.05)"
                }
            ],
            HypothesisCategory.TEMPORAL: [
                {
                    "description_template": "在不同时间段{}进行对比测试",
                    "duration": "2-4小时",
                    "resources": ["计时器", "记录设备"],
                    "success_criteria": "时间序列分析显示显著变化"
                }
            ],
            HypothesisCategory.BEHAVIORAL: [
                {
                    "description_template": "执行两种不同行为模式{}并记录结果",
                    "duration": "30分钟-1小时",
                    "resources": ["行为记录表", "观察者"],
                    "success_criteria": "行为结果差异超过预期阈值"
                }
            ],
            HypothesisCategory.CAUSAL: [
                {
                    "description_template": "控制变量{}，观察因果链变化",
                    "duration": "3-5小时",
                    "resources": ["实验环境", "控制工具"],
                    "success_criteria": "因果链中断或强化明显"
                }
            ],
            HypothesisCategory.UNKNOWN: [
                {
                    "description_template": "探索性测试假设{}",
                    "duration": "不定",
                    "resources": ["基础工具"],
                    "success_criteria": "获得可观察的证据"
                }
            ]
        }
    
    def parse_hypothesis(self, raw_input: Dict[str, Any]) -> Optional[Hypothesis]:
        """
        解析原始输入为结构化假设对象
        
        Args:
            raw_input: 原始输入字典
            
        Returns:
            Hypothesis对象，解析失败返回None
        """
        is_valid, error = self.validator.validate_hypothesis(raw_input)
        if not is_valid:
            logger.error("Hypothesis validation failed: %s", error)
            return None
        
        try:
            category = HypothesisCategory(raw_input['category'])
            hypothesis = Hypothesis(
                content=raw_input['content'],
                category=category,
                confidence=raw_input.get('confidence', 0.5),
                variables=raw_input.get('variables', []),
                constraints=raw_input.get('constraints', [])
            )
            logger.info("Successfully parsed hypothesis: %s", hypothesis.content)
            return hypothesis
        except Exception as e:
            logger.error("Error parsing hypothesis: %s", str(e))
            return None
    
    def generate_falsification_checklist(
        self,
        hypothesis: Hypothesis,
        max_actions: int = 3,
        risk_tolerance: str = "low"
    ) -> List[FalsificationAction]:
        """
        生成证伪清单
        
        Args:
            hypothesis: 结构化假设对象
            max_actions: 最大行动数量 (1-5)
            risk_tolerance: 风险容忍度 (low, medium, high)
            
        Returns:
            FalsificationAction列表
            
        Example:
            >>> generator = FalsificationGenerator()
            >>> hyp = Hypothesis("地摊位置影响销量", HypothesisCategory.SPATIAL, 0.7)
            >>> checklist = generator.generate_falsification_checklist(hyp)
            >>> for action in checklist:
            ...     print(action.description)
        """
        # 参数边界检查
        max_actions = max(1, min(5, max_actions))
        if risk_tolerance not in ["low", "medium", "high"]:
            logger.warning("Invalid risk tolerance, defaulting to 'low'")
            risk_tolerance = "low"
        
        actions = []
        templates = self._action_templates.get(
            hypothesis.category,
            self._action_templates[HypothesisCategory.UNKNOWN]
        )
        
        for i in range(min(max_actions, len(templates))):
            template = templates[i % len(templates)]
            
            # 根据假设内容生成具体描述
            description = template["description_template"].format(
                f"验证'{hypothesis.content}'"
            )
            
            # 根据置信度调整优先级
            priority = self._calculate_priority(hypothesis.confidence, i)
            
            # 根据风险容忍度调整风险等级
            risk_level = self._adjust_risk_level(risk_tolerance, hypothesis.category)
            
            action = FalsificationAction(
                action_id=f"ACT-{hypothesis.category.value[:3].upper()}-{i+1:02d}",
                description=description,
                expected_duration=template["duration"],
                required_resources=template["resources"].copy(),
                success_criteria=template["success_criteria"],
                risk_level=risk_level,
                priority=priority
            )
            actions.append(action)
        
        logger.info("Generated %d falsification actions for hypothesis: %s",
                   len(actions), hypothesis.content)
        return actions
    
    def _calculate_priority(self, confidence: float, index: int) -> int:
        """
        计算行动优先级
        
        Args:
            confidence: 假设置信度
            index: 行动索引
            
        Returns:
            优先级 [1-5]
        """
        # 高置信度假设优先级更高
        base_priority = 3
        confidence_adjustment = int(confidence * 2)  # 0-2
        index_penalty = min(index, 2)  # 后续行动优先级略低
        
        priority = base_priority + confidence_adjustment - index_penalty
        return max(1, min(5, priority))
    
    def _adjust_risk_level(self, tolerance: str, category: HypothesisCategory) -> str:
        """
        根据容忍度和类别调整风险等级
        
        Args:
            tolerance: 风险容忍度
            category: 假设类别
            
        Returns:
            调整后的风险等级
        """
        base_risk = {
            HypothesisCategory.SPATIAL: "low",
            HypothesisCategory.TEMPORAL: "medium",
            HypothesisCategory.BEHAVIORAL: "medium",
            HypothesisCategory.CAUSAL: "high",
            HypothesisCategory.UNKNOWN: "high"
        }
        
        base = base_risk.get(category, "medium")
        
        # 根据容忍度调整
        if tolerance == "low":
            if base == "high":
                return "medium"
        elif tolerance == "high":
            if base == "low":
                return "medium"
        
        return base

def format_checklist_output(checklist: List[FalsificationAction]) -> str:
    """
    格式化证伪清单为可读字符串
    
    Args:
        checklist: 行动列表
        
    Returns:
        格式化的字符串
    """
    output = ["=" * 50]
    output.append("证伪行动清单 (Falsification Checklist)")
    output.append("=" * 50)
    
    for i, action in enumerate(checklist, 1):
        output.append(f"\n行动 #{i} [优先级: {action.priority}/5]")
        output.append(f"ID: {action.action_id}")
        output.append(f"描述: {action.description}")
        output.append(f"预期耗时: {action.expected_duration}")
        output.append(f"所需资源: {', '.join(action.required_resources)}")
        output.append(f"成功标准: {action.success_criteria}")
        output.append(f"风险等级: {action.risk_level}")
    
    output.append("\n" + "=" * 50)
    output.append(f"共 {len(checklist)} 项行动建议")
    output.append("=" * 50)
    
    return "\n".join(output)

# 使用示例
if __name__ == "__main__":
    # 示例1: 地摊位置假设
    example_hypothesis = {
        "content": "地摊位置靠近地铁口会提高销量",
        "category": "spatial",
        "confidence": 0.75,
        "variables": ["位置", "销量"],
        "constraints": ["晴天", "工作日"]
    }
    
    generator = FalsificationGenerator()
    
    # 解析假设
    parsed_hypothesis = generator.parse_hypothesis(example_hypothesis)
    
    if parsed_hypothesis:
        # 生成证伪清单
        checklist = generator.generate_falsification_checklist(
            parsed_hypothesis,
            max_actions=3,
            risk_tolerance="medium"
        )
        
        # 输出格式化结果
        print(format_checklist_output(checklist))
        
        # 也可以导出为JSON格式
        checklist_data = [
            {
                "id": action.action_id,
                "description": action.description,
                "duration": action.expected_duration,
                "resources": action.required_resources,
                "criteria": action.success_criteria,
                "risk": action.risk_level,
                "priority": action.priority
            }
            for action in checklist
        ]
        print("\nJSON格式输出:")
        print(json.dumps(checklist_data, indent=2, ensure_ascii=False))