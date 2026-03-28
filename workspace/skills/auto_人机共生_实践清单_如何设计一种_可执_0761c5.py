"""
模块名称: auto_人机共生_实践清单_如何设计一种_可执_0761c5
描述: 实现AGI系统中将抽象SKILL节点转化为可执行微实验的生成协议。
      核心目标是降低人类认知负荷，确保物理执行门槛低（目标5分钟内完成），
      并提供明确的通过/失败判定标准。
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillComplexity(Enum):
    """SKILL节点的复杂度枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class ExperimentStatus(Enum):
    """实验状态枚举"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"

@dataclass
class VerificationStep:
    """单个验证步骤的数据结构"""
    step_id: str
    instruction: str           # 人类可读的执行指令
    physical_action: bool      # 是否涉及物理动作
    estimated_time_sec: int    # 预估耗时（秒）
    pass_criteria: str         # 通过标准描述
    fail_criteria: str         # 失败标准描述
    required_tools: List[str]  # 所需工具列表

@dataclass
class MicroExperiment:
    """微实验完整数据结构"""
    experiment_id: str
    source_skill_id: str
    generated_time: str
    total_estimated_time_sec: int
    steps: List[VerificationStep] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.PENDING
    execution_log: List[Dict] = field(default_factory=list)

class MicroExperimentGenerator:
    """
    微实验生成器核心类。
    
    负责将抽象的Skill定义转化为具体的、可执行的、低认知负荷的操作清单。
    """
    
    def __init__(self, max_total_time_sec: int = 300):
        """
        初始化生成器。
        
        Args:
            max_total_time_sec (int): 实验最大允许总时长（默认300秒即5分钟）
        """
        self.max_total_time_sec = max_total_time_sec
        logger.info(f"MicroExperimentGenerator initialized with max time: {max_total_time_sec}s")

    def _validate_skill_node(self, skill_node: Dict[str, Any]) -> bool:
        """
        辅助函数：验证输入的Skill节点数据结构是否合法。
        
        Args:
            skill_node (Dict): 输入的技能节点数据
            
        Returns:
            bool: 验证通过返回True，否则抛出ValueError
            
        Raises:
            ValueError: 当数据缺失或格式错误时
        """
        if not isinstance(skill_node, dict):
            logger.error("Invalid skill node type: expected dict")
            raise ValueError("Skill node must be a dictionary")
            
        required_keys = ["skill_id", "description", "complexity", "goal_state"]
        for key in required_keys:
            if key not in skill_node:
                logger.error(f"Missing required key in skill node: {key}")
                raise ValueError(f"Missing required key: {key}")
                
        # 验证复杂度是否在枚举范围内
        try:
            SkillComplexity[skill_node["complexity"].upper()]
        except KeyError:
            logger.error(f"Invalid complexity level: {skill_node['complexity']}")
            raise ValueError(f"Complexity must be one of {[e.name for e in SkillComplexity]}")
            
        logger.debug("Skill node validation passed")
        return True

    def _decompose_goal(self, goal_description: str, complexity: SkillComplexity) -> List[str]:
        """
        核心函数1：目标分解逻辑（模拟）。
        
        将复杂的技能目标分解为原子化的操作指令。
        在真实AGI场景中，这里会调用LLM进行推理。
        
        Args:
            goal_description (str): 技能的最终目标描述
            complexity (SkillComplexity): 技能复杂度
            
        Returns:
            List[str]: 分解后的指令字符串列表
        """
        logger.info(f"Decomposing goal: {goal_description[:30]}...")
        
        # 模拟分解逻辑：根据复杂度生成不同数量的步骤
        # 这里使用简单的字符串分割模拟真实场景中的语义分析
        raw_steps = []
        if complexity == SkillComplexity.LOW:
            raw_steps = [f"Verify environment for '{goal_description}'", f"Execute basic check for '{goal_description}'"]
        elif complexity == SkillComplexity.MEDIUM:
            raw_steps = [
                "Prepare physical workspace",
                f"Locate target object related to '{goal_description}'",
                f"Perform interaction defined in '{goal_description}'",
                "Verify immediate feedback"
            ]
        else:
            # 高复杂度通常需要拆分为多个微实验，此处仅截断以适应5分钟原则
            raw_steps = [
                "Phase 1: Isolate variables",
                f"Phase 2: Test core function of '{goal_description}'",
                "Phase 3: Check safety constraints"
            ]
            
        return raw_steps

    def generate_protocol(self, skill_node: Dict[str, Any]) -> MicroExperiment:
        """
        核心函数2：生成可执行清单协议。
        
        将输入的Skill节点转换为包含具体步骤、时间预估和判定标准的MicroExperiment对象。
        
        Args:
            skill_node (Dict): 包含skill_id, description, complexity, goal_state的字典
            
        Returns:
            MicroExperiment: 生成好的微实验对象
            
        Raises:
            ValueError: 输入验证失败时抛出
            RuntimeError: 生成过程中时间预算超限时抛出
        """
        try:
            self._validate_skill_node(skill_node)
        except ValueError as e:
            logger.error(f"Validation failed: {e}")
            raise

        skill_id = skill_node["skill_id"]
        complexity = SkillComplexity[skill_node["complexity"].upper()]
        
        logger.info(f"Generating protocol for skill: {skill_id}")
        
        # 1. 分解目标
        raw_instructions = self._decompose_goal(skill_node["description"], complexity)
        
        steps: List[VerificationStep] = []
        current_total_time = 0
        
        # 2. 构建步骤详情
        for idx, instruction in enumerate(raw_instructions):
            step_id = f"{skill_id}_step_{idx+1}"
            
            # 模拟时间预估逻辑
            est_time = 60 if complexity == SkillComplexity.HIGH else 30
            current_total_time += est_time
            
            # 边界检查：确保不超过5分钟限制
            if current_total_time > self.max_total_time_sec:
                logger.warning(f"Time budget exceeded ({current_total_time}s), truncating steps.")
                break
                
            # 生成判定标准（模拟）
            pass_crit = f"Visual confirmation: '{instruction}' completed without error."
            fail_crit = f"System error or physical obstruction detected."
            
            step = VerificationStep(
                step_id=step_id,
                instruction=instruction,
                physical_action=True,  # 假设都需要物理交互
                estimated_time_sec=est_time,
                pass_criteria=pass_crit,
                fail_criteria=fail_crit,
                required_tools=["Human Hand", "Visual Sensor"] # 默认工具
            )
            steps.append(step)
            
        if not steps:
            raise RuntimeError("Failed to generate valid steps within time constraints.")

        # 3. 组装微实验对象
        experiment = MicroExperiment(
            experiment_id=f"exp_{skill_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            source_skill_id=skill_id,
            generated_time=datetime.now().isoformat(),
            total_estimated_time_sec=current_total_time,
            steps=steps
        )
        
        logger.info(f"Protocol generated successfully with {len(steps)} steps.")
        return experiment

def format_checklist_for_human(experiment: MicroExperiment) -> str:
    """
    辅助函数：将微实验对象格式化为人类易读的清单文本。
    
    Args:
        experiment (MicroExperiment): 生成的微实验对象
        
    Returns:
        str: 格式化后的Markdown文本
    """
    output = [
        f"# Micro-Experiment Checklist: {experiment.experiment_id}",
        f"**Source Skill:** {experiment.source_skill_id}",
        f"**Total Est. Time:** {experiment.total_estimated_time_sec} seconds\n",
        "---\n"
    ]
    
    for step in experiment.steps:
        output.append(f"## Step {step.step_id}")
        output.append(f"**Action:** {step.instruction}")
        output.append(f"**Time:** {step.estimated_time_sec}s")
        output.append(f"**Pass Condition:** [ ] {step.pass_criteria}")
        output.append(f"**Fail Condition:** [ ] {step.fail_criteria}\n")
        
    return "\n".join(output)

# 使用示例
if __name__ == "__main__":
    # 模拟一个来自AGI系统的抽象Skill节点
    abstract_skill = {
        "skill_id": "skill_grasp_cup_01",
        "description": "Identify and physically grasp a coffee cup on the desk without spillage.",
        "complexity": "MEDIUM",
        "goal_state": "cup_in_hand"
    }

    generator = MicroExperimentGenerator(max_total_time_sec=300)
    
    try:
        # 生成协议
        micro_exp = generator.generate_protocol(abstract_skill)
        
        # 转换为人类可读格式
        readable_checklist = format_checklist_for_human(micro_exp)
        print(readable_checklist)
        
        # 输出JSON数据结构（用于系统间传输）
        # print(json.dumps(asdict(micro_exp), indent=2, default=str))
        
    except (ValueError, RuntimeError) as e:
        logger.critical(f"Experiment generation aborted: {e}")