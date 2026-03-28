"""
归纳引擎模块：自下而上构建宏技能

该模块实现了基于过程挖掘的自动化技能归纳系统。通过分析操作日志中的重复模式，
自动识别并封装高频操作序列为可复用的宏技能节点。

输入格式:
    操作日志格式为JSON数组，每个操作包含:
    - timestamp: ISO格式时间戳
    - action: 操作类型 (如 'open_browser', 'search')
    - parameters: 操作参数字典
    - context: 执行上下文信息

输出格式:
    宏技能节点包含:
    - skill_id: 唯一标识符
    - steps: 操作步骤列表
    - frequency: 出现频率
    - last_used: 最后使用时间
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Operation:
    """表示单个操作的数据类"""
    timestamp: str
    action: str
    parameters: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证操作数据"""
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise ValueError("Invalid timestamp format")
        if not isinstance(self.action, str) or not self.action:
            raise ValueError("Action must be a non-empty string")
        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")


@dataclass
class MacroSkill:
    """表示宏技能的数据类"""
    skill_id: str
    steps: List[Dict[str, Any]]
    frequency: int = 1
    last_used: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    parameters_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将宏技能转换为字典格式"""
        return {
            "skill_id": self.skill_id,
            "steps": self.steps,
            "frequency": self.frequency,
            "last_used": self.last_used,
            "description": self.description,
            "parameters_schema": self.parameters_schema
        }


class InductionEngine:
    """归纳引擎核心类，负责从操作日志中发现和构建宏技能"""

    def __init__(self, min_sequence_length: int = 3, min_frequency: int = 2):
        """
        初始化归纳引擎
        
        参数:
            min_sequence_length: 最小序列长度，低于此值的模式不会被考虑
            min_frequency: 最小出现频率，低于此值的模式不会被封装
        """
        self.min_sequence_length = max(2, min_sequence_length)
        self.min_frequency = max(1, min_frequency)
        self.macro_skills: Dict[str, MacroSkill] = {}
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """验证初始化参数"""
        if self.min_sequence_length < 2:
            raise ValueError("Minimum sequence length must be at least 2")
        if self.min_frequency < 1:
            raise ValueError("Minimum frequency must be at least 1")

    def _generate_skill_id(self, steps: List[Dict[str, Any]]) -> str:
        """为宏技能生成唯一ID"""
        steps_str = json.dumps(steps, sort_keys=True)
        return f"macro_{hashlib.md5(steps_str.encode()).hexdigest()[:8]}"

    def _validate_operation_sequence(self, operations: List[Operation]) -> bool:
        """验证操作序列是否有效"""
        if not operations:
            logger.warning("Empty operation sequence provided")
            return False
        
        for op in operations:
            try:
                Operation(**op)  # 验证每个操作的结构
            except (TypeError, ValueError) as e:
                logger.error(f"Invalid operation detected: {e}")
                return False
        return True

    def _find_common_sequences(self, actions: List[str]) -> List[Tuple[List[str], int]]:
        """
        在操作序列中查找重复出现的子序列
        
        参数:
            actions: 操作名称序列
            
        返回:
            包含子序列及其出现频率的列表，按频率降序排列
        """
        if len(actions) < self.min_sequence_length:
            return []

        sequences = {}
        max_len = min(len(actions), self.min_sequence_length * 3)  # 限制最大序列长度
        
        # 滑动窗口查找重复序列
        for length in range(self.min_sequence_length, max_len + 1):
            for i in range(len(actions) - length + 1):
                subsequence = tuple(actions[i:i+length])
                sequences[subsequence] = sequences.get(subsequence, 0) + 1

        # 过滤并排序结果
        common_sequences = [
            (list(seq), freq) for seq, freq in sequences.items() 
            if freq >= self.min_frequency
        ]
        return sorted(common_sequences, key=lambda x: (-x[1], -len(x[0])))

    def _extract_parameters_schema(self, operations: List[Operation]) -> Dict[str, Any]:
        """从操作序列中提取参数模式"""
        schema = {}
        for op in operations:
            for param, value in op.parameters.items():
                if param not in schema:
                    schema[param] = {"type": type(value).__name__, "examples": []}
                schema[param]["examples"].append(value)
        
        # 简化模式，只保留类型和少量示例
        for param in schema:
            schema[param]["examples"] = schema[param]["examples"][:3]
        return schema

    def analyze_operations(self, operations: List[Dict[str, Any]]) -> List[MacroSkill]:
        """
        分析操作日志并返回发现的宏技能
        
        参数:
            operations: 操作日志列表，每个操作为字典格式
            
        返回:
            发现的宏技能列表
            
        示例:
            >>> engine = InductionEngine()
            >>> logs = [{"timestamp": "2023-01-01T00:00:00", "action": "search", "parameters": {}}]
            >>> skills = engine.analyze_operations(logs)
        """
        if not self._validate_operation_sequence(operations):
            logger.error("Invalid operation sequence provided")
            return []

        try:
            # 将操作转换为内部表示
            ops = [Operation(**op) for op in operations]
            actions = [op.action for op in ops]
            
            # 查找重复序列
            common_sequences = self._find_common_sequences(actions)
            if not common_sequences:
                logger.info("No common sequences found meeting the criteria")
                return []

            new_skills = []
            
            # 创建宏技能
            for seq, freq in common_sequences:
                # 查找序列在操作中的起始位置
                start_idx = actions.index(seq[0])
                end_idx = start_idx + len(seq)
                
                # 提取完整操作步骤
                steps = []
                for op in ops[start_idx:end_idx]:
                    steps.append({
                        "action": op.action,
                        "parameters": op.parameters,
                        "context": op.context
                    })
                
                # 生成宏技能
                skill_id = self._generate_skill_id(steps)
                if skill_id not in self.macro_skills:
                    parameters_schema = self._extract_parameters_schema(ops[start_idx:end_idx])
                    
                    skill = MacroSkill(
                        skill_id=skill_id,
                        steps=steps,
                        frequency=freq,
                        description=f"Automatically generated skill for: {' -> '.join(seq)}",
                        parameters_schema=parameters_schema
                    )
                    self.macro_skills[skill_id] = skill
                    new_skills.append(skill)
                    logger.info(f"Created new macro skill: {skill_id} with frequency {freq}")
                else:
                    # 更新现有技能的频率和最后使用时间
                    self.macro_skills[skill_id].frequency += freq
                    self.macro_skills[skill_id].last_used = datetime.utcnow().isoformat()
            
            return new_skills

        except Exception as e:
            logger.error(f"Error analyzing operations: {str(e)}")
            return []

    def get_macro_skill(self, skill_id: str) -> Optional[MacroSkill]:
        """根据ID获取宏技能"""
        return self.macro_skills.get(skill_id)

    def execute_macro_skill(self, skill_id: str, parameters: Dict[str, Any] = None) -> bool:
        """
        执行指定的宏技能
        
        参数:
            skill_id: 要执行的宏技能ID
            parameters: 执行参数
            
        返回:
            执行是否成功
            
        示例:
            >>> engine = InductionEngine()
            >>> engine.execute_macro_skill("macro_12345678", {"query": "Python教程"})
        """
        skill = self.get_macro_skill(skill_id)
        if not skill:
            logger.error(f"Macro skill not found: {skill_id}")
            return False

        try:
            logger.info(f"Executing macro skill: {skill_id}")
            for step in skill.steps:
                # 这里应该是实际执行操作的逻辑
                # 示例中只是记录日志
                action = step["action"]
                params = {**step["parameters"], **(parameters or {})}
                logger.info(f"Executing step: {action} with params {params}")
            
            # 更新最后使用时间
            skill.last_used = datetime.utcnow().isoformat()
            return True

        except Exception as e:
            logger.error(f"Error executing macro skill {skill_id}: {str(e)}")
            return False

    def export_skills(self) -> List[Dict[str, Any]]:
        """导出所有宏技能为字典列表"""
        return [skill.to_dict() for skill in self.macro_skills.values()]

    def import_skills(self, skills_data: List[Dict[str, Any]]) -> int:
        """
        导入宏技能
        
        参数:
            skills_data: 要导入的宏技能数据
            
        返回:
            成功导入的技能数量
        """
        count = 0
        for skill_dict in skills_data:
            try:
                skill = MacroSkill(**skill_dict)
                self.macro_skills[skill.skill_id] = skill
                count += 1
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to import skill: {e}")
        return count


# 使用示例
if __name__ == "__main__":
    # 示例操作日志
    sample_operations = [
        {"timestamp": "2023-01-01T00:00:00", "action": "open_browser", "parameters": {"url": "https://example.com"}},
        {"timestamp": "2023-01-01T00:00:05", "action": "search", "parameters": {"query": "Python教程"}},
        {"timestamp": "2023-01-01T00:00:10", "action": "copy_text", "parameters": {"selector": "#result"}},
        {"timestamp": "2023-01-01T00:00:15", "action": "paste_text", "parameters": {"target": "editor"}},
        
        {"timestamp": "2023-01-01T00:01:00", "action": "open_browser", "parameters": {"url": "https://example.com"}},
        {"timestamp": "2023-01-01T00:01:05", "action": "search", "parameters": {"query": "Python示例"}},
        {"timestamp": "2023-01-01T00:01:10", "action": "copy_text", "parameters": {"selector": "#result"}},
        {"timestamp": "2023-01-01T00:01:15", "action": "paste_text", "parameters": {"target": "editor"}},
        
        {"timestamp": "2023-01-01T00:02:00", "action": "open_browser", "parameters": {"url": "https://example.com"}},
        {"timestamp": "2023-01-01T00:02:05", "action": "search", "parameters": {"query": "Python文档"}},
        {"timestamp": "2023-01-01T00:02:10", "action": "copy_text", "parameters": {"selector": "#result"}},
        {"timestamp": "2023-01-01T00:02:15", "action": "paste_text", "parameters": {"target": "editor"}},
    ]

    # 创建归纳引擎实例
    engine = InductionEngine(min_sequence_length=4, min_frequency=2)
    
    # 分析操作日志
    new_skills = engine.analyze_operations(sample_operations)
    print(f"发现 {len(new_skills)} 个新的宏技能")
    
    # 导出技能
    exported_skills = engine.export_skills()
    print("导出的宏技能:", json.dumps(exported_skills, indent=2))
    
    # 执行宏技能示例
    if new_skills:
        skill_id = new_skills[0].skill_id
        success = engine.execute_macro_skill(skill_id, {"query": "Python最佳实践"})
        print(f"执行宏技能 {skill_id}: {'成功' if success else '失败'}")