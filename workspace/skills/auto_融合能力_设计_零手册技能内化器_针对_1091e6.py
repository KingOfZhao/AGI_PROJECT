"""
高级Python模块：零手册技能内化器

该模块实现了一套"引导式沙盒"系统，用于复杂工具的学习。
通过解构专家操作路径，将其封装为新手引导关卡，
让用户在解决实际问题的过程中"不知不觉"地掌握高级技巧。

核心功能：
1. 专家路径分析器：分析并提取专家操作路径
2. 引导关卡生成器：将专家路径转化为渐进式学习关卡
3. 智能提示系统：根据用户行为提供高亮提示

数据流：
输入：专家操作日志/用户行为数据
处理：路径分析 → 关卡设计 → 交互引导
输出：学习进度/技能掌握度报告

作者：AGI系统
版本：1.0.0
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ZeroManualSkillInternalizer")


class ToolType(Enum):
    """支持的复杂工具类型"""
    PROGRAMMING_IDE = auto()
    DESIGN_SOFTWARE = auto()
    INDUSTRIAL_MACHINE = auto()
    DATA_ANALYSIS = auto()
    OTHER = auto()


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


@dataclass
class OperationStep:
    """操作步骤数据结构"""
    step_id: str
    description: str
    action_type: str
    parameters: Dict[str, Union[str, int, float, bool]]
    timestamp: str
    is_expert_action: bool = False


@dataclass
class GuidanceHint:
    """引导提示数据结构"""
    hint_id: str
    target_element: str
    hint_text: str
    highlight_style: str
    priority: int
    display_condition: Optional[Dict] = None


class ExpertPathAnalyzer:
    """专家路径分析器"""
    
    def __init__(self, tool_type: ToolType):
        """
        初始化分析器
        
        Args:
            tool_type: 要分析的工具类型
        """
        self.tool_type = tool_type
        self.logger = logging.getLogger(f"{__name__}.ExpertPathAnalyzer")
        
    def analyze_operation_log(self, log_path: Union[str, Path]) -> List[OperationStep]:
        """
        分析专家操作日志，提取关键操作路径
        
        Args:
            log_path: 操作日志文件路径
            
        Returns:
            操作步骤列表
            
        Raises:
            FileNotFoundError: 日志文件不存在
            ValueError: 日志格式无效
        """
        log_path = Path(log_path)
        if not log_path.exists():
            error_msg = f"操作日志文件不存在: {log_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
                
            if not isinstance(log_data, list):
                raise ValueError("日志数据应为操作步骤列表")
                
            operation_steps = []
            for idx, step_data in enumerate(log_data):
                try:
                    step = self._parse_step_data(step_data, idx)
                    operation_steps.append(step)
                except (KeyError, TypeError) as e:
                    self.logger.warning(f"跳过无效步骤 {idx}: {str(e)}")
                    continue
                    
            self.logger.info(f"成功分析 {len(operation_steps)} 个操作步骤")
            return operation_steps
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
    def _parse_step_data(self, step_data: Dict, index: int) -> OperationStep:
        """
        解析单个操作步骤数据
        
        Args:
            step_data: 步骤数据字典
            index: 步骤索引
            
        Returns:
            OperationStep 对象
        """
        required_fields = ['description', 'action_type', 'parameters']
        for field in required_fields:
            if field not in step_data:
                raise KeyError(f"缺少必要字段: {field}")
                
        step_id = step_data.get('step_id', f"step_{index:03d}")
        timestamp = step_data.get('timestamp', datetime.now().isoformat())
        is_expert = step_data.get('is_expert_action', False)
        
        return OperationStep(
            step_id=step_id,
            description=step_data['description'],
            action_type=step_data['action_type'],
            parameters=step_data['parameters'],
            timestamp=timestamp,
            is_expert_action=is_expert
        )
        
    def extract_expert_patterns(self, steps: List[OperationStep]) -> Dict[str, List[OperationStep]]:
        """
        从操作步骤中提取专家模式
        
        Args:
            steps: 操作步骤列表
            
        Returns:
            专家模式字典，键为模式名称，值为步骤列表
        """
        if not steps:
            self.logger.warning("操作步骤列表为空")
            return {}
            
        expert_steps = [step for step in steps if step.is_expert_action]
        if not expert_steps:
            self.logger.info("未找到专家操作步骤")
            return {}
            
        # 简单实现：按操作类型分组
        patterns = {}
        for step in expert_steps:
            pattern_name = f"expert_{step.action_type}_pattern"
            if pattern_name not in patterns:
                patterns[pattern_name] = []
            patterns[pattern_name].append(step)
            
        self.logger.info(f"识别到 {len(patterns)} 种专家模式")
        return patterns


class GuidanceLevelGenerator:
    """引导关卡生成器"""
    
    def __init__(self, min_steps_per_level: int = 3):
        """
        初始化关卡生成器
        
        Args:
            min_steps_per_level: 每个关卡最少包含的步骤数
        """
        if min_steps_per_level < 1:
            raise ValueError("每个关卡最少包含1个步骤")
            
        self.min_steps_per_level = min_steps_per_level
        self.logger = logging.getLogger(f"{__name__}.GuidanceLevelGenerator")
        
    def generate_levels_from_pattern(
        self,
        pattern: List[OperationStep],
        difficulty: SkillLevel = SkillLevel.NOVICE
    ) -> List[Dict]:
        """
        根据专家操作模式生成引导关卡
        
        Args:
            pattern: 专家操作模式步骤列表
            difficulty: 目标难度等级
            
        Returns:
            关卡列表，每个关卡包含引导提示和解锁条件
        """
        if not pattern:
            self.logger.warning("操作模式为空，无法生成关卡")
            return []
            
        levels = []
        total_steps = len(pattern)
        steps_per_level = max(self.min_steps_per_level, total_steps // 4)
        
        for i in range(0, total_steps, steps_per_level):
            level_steps = pattern[i:i + steps_per_level]
            level_num = i // steps_per_level + 1
            
            # 生成引导提示
            hints = []
            for step in level_steps:
                hint = self._generate_hint_for_step(step, difficulty)
                hints.append(hint)
                
            level = {
                "level_id": f"level_{level_num:02d}",
                "name": f"技能掌握阶段 {level_num}",
                "description": self._generate_level_description(level_steps),
                "steps": [step.__dict__ for step in level_steps],
                "hints": hints,
                "unlock_condition": {
                    "type": "step_completion",
                    "threshold": len(level_steps) * 0.7  # 完成70%即可解锁下一关
                },
                "difficulty": difficulty.name
            }
            levels.append(level)
            
        self.logger.info(f"生成了 {len(levels)} 个引导关卡")
        return levels
        
    def _generate_hint_for_step(
        self,
        step: OperationStep,
        difficulty: SkillLevel
    ) -> Dict:
        """
        为单个操作步骤生成引导提示
        
        Args:
            step: 操作步骤
            difficulty: 难度等级
            
        Returns:
            引导提示字典
        """
        # 根据难度调整提示详细程度
        detail_level = {
            SkillLevel.NOVICE: "详细",
            SkillLevel.INTERMEDIATE: "适中",
            SkillLevel.ADVANCED: "简略",
            SkillLevel.EXPERT: "极少"
        }
        
        return {
            "hint_id": f"hint_{step.step_id}",
            "target_element": step.parameters.get("target_element", "未知"),
            "hint_text": f"提示: {step.description} ({detail_level[difficulty]})",
            "highlight_style": "pulse" if difficulty == SkillLevel.NOVICE else "underline",
            "display_condition": {
                "type": "action_delay",
                "threshold_ms": 2000  # 2秒无操作后显示提示
            }
        }
        
    def _generate_level_description(self, steps: List[OperationStep]) -> str:
        """
        生成关卡描述
        
        Args:
            steps: 关卡步骤列表
            
        Returns:
            关卡描述字符串
        """
        if not steps:
            return "空关卡"
            
        actions = set(step.action_type for step in steps)
        action_desc = "、".join(actions)
        return f"本关卡将练习以下操作: {action_desc}"


def calculate_skill_progress(
    completed_levels: List[Dict],
    user_actions: List[Dict]
) -> Dict[str, Union[float, int, str]]:
    """
    计算用户技能掌握进度
    
    Args:
        completed_levels: 已完成的关卡列表
        user_actions: 用户操作记录
        
    Returns:
        包含进度信息的字典
    """
    if not completed_levels:
        return {
            "progress_percentage": 0.0,
            "mastered_skills": 0,
            "total_levels": 0,
            "skill_level": SkillLevel.NOVICE.name
        }
        
    total_levels = len(completed_levels)
    mastered_count = 0
    
    for level in completed_levels:
        # 简单实现：假设每个关卡都有一个完成状态
        if level.get("completed", False):
            mastered_count += 1
            
    progress_percentage = (mastered_count / total_levels) * 100
    
    # 根据进度确定技能等级
    if progress_percentage >= 90:
        skill_level = SkillLevel.EXPERT.name
    elif progress_percentage >= 70:
        skill_level = SkillLevel.ADVANCED.name
    elif progress_percentage >= 40:
        skill_level = SkillLevel.INTERMEDIATE.name
    else:
        skill_level = SkillLevel.NOVICE.name
        
    return {
        "progress_percentage": round(progress_percentage, 2),
        "mastered_skills": mastered_count,
        "total_levels": total_levels,
        "skill_level": skill_level,
        "last_updated": datetime.now().isoformat()
    }


def validate_operation_log(log_data: Union[str, Dict, List]) -> bool:
    """
    验证操作日志数据格式
    
    Args:
        log_data: 要验证的数据
        
    Returns:
        是否有效
    """
    if isinstance(log_data, str):
        try:
            log_data = json.loads(log_data)
        except json.JSONDecodeError:
            return False
            
    if not isinstance(log_data, list):
        return False
        
    for item in log_data:
        if not isinstance(item, dict):
            return False
        if 'action_type' not in item or 'description' not in item:
            return False
            
    return True


# 使用示例
if __name__ == "__main__":
    # 示例操作日志数据
    sample_log = [
        {
            "step_id": "step_001",
            "description": "打开IDE并创建新项目",
            "action_type": "project_creation",
            "parameters": {"target_element": "new_project_button", "click_count": 1},
            "timestamp": "2023-01-01T10:00:00",
            "is_expert_action": False
        },
        {
            "step_id": "step_002",
            "description": "配置Python虚拟环境",
            "action_type": "environment_setup",
            "parameters": {"target_element": "settings_panel", "options_selected": 3},
            "timestamp": "2023-01-01T10:05:00",
            "is_expert_action": True
        },
        {
            "step_id": "step_003",
            "description": "使用代码模板快速生成类结构",
            "action_type": "code_generation",
            "parameters": {"target_element": "code_menu", "template_used": "class_template"},
            "timestamp": "2023-01-01T10:10:00",
            "is_expert_action": True
        }
    ]
    
    # 保存示例日志到临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_log, f)
        temp_log_path = f.name
    
    try:
        # 初始化分析器
        analyzer = ExpertPathAnalyzer(ToolType.PROGRAMMING_IDE)
        
        # 分析操作日志
        operation_steps = analyzer.analyze_operation_log(temp_log_path)
        
        # 提取专家模式
        expert_patterns = analyzer.extract_expert_patterns(operation_steps)
        
        # 生成引导关卡
        level_generator = GuidanceLevelGenerator(min_steps_per_level=2)
        for pattern_name, steps in expert_patterns.items():
            levels = level_generator.generate_levels_from_pattern(steps, SkillLevel.NOVICE)
            print(f"为模式 '{pattern_name}' 生成了 {len(levels)} 个关卡")
            
        # 计算技能进度
        progress = calculate_skill_progress(levels, [])
        print(f"技能进度: {progress['progress_percentage']}%")
        
    finally:
        # 清理临时文件
        Path(temp_log_path).unlink()