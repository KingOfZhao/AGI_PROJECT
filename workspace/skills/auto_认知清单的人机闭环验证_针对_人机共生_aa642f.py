"""
模块名称: auto_认知清单的人机闭环验证_针对_人机共生_aa642f
描述: 本模块旨在实现AGI系统中的'认知清单人机闭环验证'功能。
      针对特定的物理任务（如操作老式胶片相机），验证AI生成的操作步骤在真实物理世界中的可执行性。
      核心逻辑是对比AI的理论知识与人类在盲测中发现的隐性物理约束，从而修补认知盲区。
作者: AGI System Core
版本: 1.0.0
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hci_verification_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """操作步骤执行状态的枚举类"""
    SUCCESS = "success"
    FAILED_PHYSICAL_CONSTRAINT = "failed_physical_constraint"  # 物理约束缺失
    FAILED_AMBIGUITY = "failed_ambiguity"                     # 指令模糊
    SKIPPED = "skipped"


@dataclass
class OperationStep:
    """操作步骤的数据结构"""
    step_id: int
    description: str
    expected_state: str
    actual_result: Optional[str] = None
    status: Optional[StepStatus] = None
    hidden_constraint_detected: Optional[str] = None  # 发现的隐性物理约束

    def to_dict(self) -> Dict[str, Any]:
        """将对象转换为字典"""
        data = asdict(self)
        if self.status:
            data['status'] = self.status.value
        return data


@dataclass
class VerificationReport:
    """验证报告的数据结构"""
    task_name: str
    timestamp: str
    total_steps: int
    success_rate: float
    physical_constraints_found: List[str]
    raw_data: List[Dict[str, Any]]

    def to_json(self) -> str:
        """将报告序列化为JSON"""
        return json.dumps(self, default=lambda o: o.__dict__, indent=2, ensure_ascii=False)


class HumanInTheLoopValidator:
    """
    人机闭环验证器。
    
    负责：
    1. 加载AI生成的任务清单。
    2. 模拟/接收人类在物理世界中的反馈。
    3. 识别AI遗漏的物理约束。
    4. 生成修补后的认知清单。
    """

    def __init__(self, task_name: str, ai_proposed_steps: List[Dict[str, str]]):
        """
        初始化验证器。
        
        Args:
            task_name (str): 任务名称，例如 'operate_vintage_camera'.
            ai_proposed_steps (List[Dict]): AI生成的步骤列表，每个字典包含 'description' 和 'expected_state'.
        """
        self.task_name = task_name
        self.steps: List[OperationStep] = []
        self._load_steps(ai_proposed_steps)
        logger.info(f"初始化验证器: 任务 '{task_name}', 共 {len(self.steps)} 个步骤.")

    def _load_steps(self, steps_data: List[Dict[str, str]]) -> None:
        """辅助函数：加载并验证步骤数据"""
        if not steps_data:
            raise ValueError("步骤数据不能为空")
        
        for idx, data in enumerate(steps_data):
            if 'description' not in data:
                raise ValueError(f"步骤 {idx} 缺少 'description' 字段")
            
            step = OperationStep(
                step_id=idx + 1,
                description=data.get('description', ''),
                expected_state=data.get('expected_state', 'Unknown')
            )
            self.steps.append(step)

    def validate_step_executability(self, step_index: int, human_feedback: Dict[str, Any]) -> bool:
        """
        核心函数：验证单个步骤的可执行性。
        
        基于人类反馈判断AI指令是否失败，并提取隐性物理约束。
        
        Args:
            step_index (int): 步骤索引。
            human_feedback (Dict): 包含 'is_executable', 'failure_reason', 'constraint_observed' 的字典。
        
        Returns:
            bool: 验证过程是否顺利完成。
        """
        if step_index < 0 or step_index >= len(self.steps):
            logger.error(f"索引越界: {step_index}")
            raise IndexError("步骤索引超出范围")

        target_step = self.steps[step_index]
        
        if not human_feedback.get('is_executable', True):
            # 人类反馈该步骤无法执行
            reason = human_feedback.get('failure_reason', 'Unknown failure')
            constraint = human_feedback.get('constraint_observed', 'No constraint recorded')
            
            # 判断失败类型，这里假设主要是物理约束问题
            target_step.status = StepStatus.FAILED_PHYSICAL_CONSTRAINT
            target_step.actual_result = f"执行失败: {reason}"
            target_step.hidden_constraint_detected = constraint
            
            logger.warning(
                f"步骤 {target_step.step_id} 验证失败 | "
                f"指令: '{target_step.description}' | "
                f"缺失约束: '{constraint}'"
            )
            return True
        
        target_step.status = StepStatus.SUCCESS
        target_step.actual_result = "Executed successfully"
        logger.info(f"步骤 {target_step.step_id}: '{target_step.description}' 验证通过。")
        return True

    def generate_closed_loop_report(self) -> VerificationReport:
        """
        核心函数：生成闭环验证报告。
        
        统计失败率，收集所有发现的隐性约束，生成最终报告。
        
        Returns:
            VerificationReport: 包含完整验证结果的对象。
        """
        total = len(self.steps)
        if total == 0:
            return VerificationReport(self.task_name, datetime.now().isoformat(), 0, 0.0, [], [])

        success_count = 0
        constraints_list = []
        raw_data_list = []

        for step in self.steps:
            if step.status == StepStatus.SUCCESS:
                success_count += 1
            elif step.status == StepStatus.FAILED_PHYSICAL_CONSTRAINT and step.hidden_constraint_detected:
                constraints_list.append(step.hidden_constraint_detected)
            
            raw_data_list.append(step.to_dict())

        success_rate = (success_count / total) * 100
        
        report = VerificationReport(
            task_name=self.task_name,
            timestamp=datetime.now().isoformat(),
            total_steps=total,
            success_rate=success_rate,
            physical_constraints_found=constraints_list,
            raw_data=raw_data_list
        )
        
        logger.info(f"报告生成完毕. 成功率: {success_rate:.2f}%, 发现隐性约束: {len(constraints_list)}条.")
        return report


# ================= 使用示例 =================
if __name__ == "__main__":
    # 模拟AI生成的关于“操作老式胶片相机”的初始认知清单
    # 注意：AI可能忽略了物理先决条件
    ai_task_steps = [
        {
            "description": "打开镜头盖并直接按下快门按钮进行拍摄。",
            "expected_state": "快门触发，照片拍摄完成。"
        },
        {
            "description": "拍摄后立即再次按下快门。",
            "expected_state": "连续拍摄第二张照片。"
        },
        {
            "description": "旋转过片扳手直到停止。",
            "expected_state": "胶卷前进一帧，快门上弦。"
        }
    ]

    # 初始化验证器
    validator = HumanInTheLoopValidator(
        task_name="Vintage_Camera_Operation_Test",
        ai_proposed_steps=ai_task_steps
    )

    print("\n--- 开始人机闭环验证测试 ---\n")

    # 模拟人类盲测反馈
    
    # 场景 1: 人类发现老式相机如果不过片，快门按不下去（机械互锁）
    # AI的第一步直接要求按快门，但此时快门是锁定的。
    feedback_step_0 = {
        "is_executable": False,
        "failure_reason": "快门按钮无法按下，感觉被机械锁死。",
        "constraint_observed": "隐含物理约束：机械快门需要先'上弦'（过片）才能释放。"
    }
    
    try:
        validator.validate_step_executability(0, feedback_step_0)
    except Exception as e:
        logger.error(f"验证过程异常: {e}")

    # 场景 2: 人类尝试执行AI的第二步（连续按快门）
    # 假设人类手动过了第一张片，拍了第一张，然后尝试拍第二张。
    feedback_step_1 = {
        "is_executable": False,
        "failure_reason": "第一次拍摄后，快门再次被锁死，无法拍摄。",
        "constraint_observed": "单次动作机制：每次释放快门后，必须再次过片才能进行下一次拍摄。"
    }
    
    validator.validate_step_executability(1, feedback_step_1)

    # 场景 3: 验证过片步骤
    feedback_step_2 = {
        "is_executable": True
    }
    validator.validate_step_executability(2, feedback_step_2)

    # 生成最终报告
    final_report = validator.generate_closed_loop_report()
    
    print("\n--- 最终验证报告 (JSON) ---\n")
    print(final_report.to_json())

    # 输出应当写入文件的路径提示
    # print(f"日志已写入: hci_verification_log.log")