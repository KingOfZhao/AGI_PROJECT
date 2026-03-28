"""
Module: human_machine_symbiosis_interface
Description: 实现‘人机共生’的代码化接口：构建双向API，AI生成设备调试清单给人类技工，
             技工执行后进行简单的‘通过/失败’打标，AI自动更新网络中2555个SKILL的概率权重。
Author: AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import json
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import random

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("symbiosis_interface.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FeedbackStatus(Enum):
    """技工反馈状态的枚举类"""
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"

@dataclass
class SkillNode:
    """
    技能节点数据结构
    代表网络中的一个具体技能或调试步骤
    """
    skill_id: str
    description: str
    weight: float = 1.0  # 权重范围 0.0 到 1.0
    confidence: float = 0.5  # 模型对该技能当前状态的置信度
    last_updated: str = "Never"

@dataclass
class DiagnosticChecklist:
    """
    设备调试清单数据结构
    AI生成并传递给人类的任务对象
    """
    task_id: str
    target_device: str
    steps: List[Dict[str, str]]  # 包含 step_id, instruction, expected_outcome
    generated_at: str
    status: FeedbackStatus = FeedbackStatus.PENDING

class SymbiosisInterface:
    """
    人机共生双向接口核心类。
    
    管理技能权重的存储、清单的生成以及基于反馈的权重更新。
    模拟了一个包含2555个技能节点的网络。
    
    Attributes:
        skill_network (Dict[str, SkillNode]): 存储所有技能节点的字典。
        learning_rate (float): 权重更新的学习率。
    """

    def __init__(self, initial_skill_count: int = 2555, learning_rate: float = 0.05):
        """
        初始化接口，预填充模拟数据。

        Args:
            initial_skill_count (int): 初始化的技能节点数量。
            learning_rate (float): 权重调整的步长。
        """
        if initial_skill_count <= 0:
            raise ValueError("Skill count must be positive.")
        
        self.skill_network: Dict[str, SkillNode] = {}
        self.learning_rate = learning_rate
        self._initialize_mock_network(initial_skill_count)
        logger.info(f"SymbiosisInterface initialized with {len(self.skill_network)} skills.")

    def _initialize_mock_network(self, count: int) -> None:
        """
        [辅助函数]
        初始化模拟的技能网络数据。
        
        Args:
            count (int): 要生成的节点数量。
        """
        logger.debug(f"Generating {count} mock skill nodes...")
        for i in range(count):
            node_id = f"SKILL_{i:04d}"
            # 模拟不同类型的调试技能
            desc = f"Diagnostic routine for subsystem {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} - Variation {i%100}"
            self.skill_network[node_id] = SkillNode(
                skill_id=node_id,
                description=desc,
                weight=random.uniform(0.3, 0.9),
                confidence=random.uniform(0.1, 0.9)
            )

    def generate_diagnostic_checklist(self, device_id: str, context_data: Dict) -> DiagnosticChecklist:
        """
        [核心函数 1]
        生成一份设备调试清单给人类技工。
        
        基于当前技能网络中权重最高（最相关/最需要验证）的节点生成任务。
        
        Args:
            device_id (str): 目标设备的ID。
            context_data (Dict): 当前设备的环境上下文数据。
            
        Returns:
            DiagnosticChecklist: 包含调试步骤的清单对象。
        
        Raises:
            ValueError: 如果技能网络为空。
        """
        if not self.skill_network:
            logger.error("Attempted to generate checklist with empty skill network.")
            raise ValueError("Skill network is empty.")

        logger.info(f"Generating checklist for device: {device_id}")
        
        # 简单的排序逻辑：优先选择置信度低但权重尚可的节点进行验证（探索与利用）
        # 或者选择权重最高的节点（最相关）。这里模拟选择权重最高的Top 5。
        sorted_skills = sorted(
            self.skill_network.values(), 
            key=lambda x: x.weight, 
            reverse=True
        )
        
        selected_steps = []
        # 选取前5个相关的技能步骤
        for skill in sorted_skills[:5]:
            step = {
                "step_id": skill.skill_id,
                "instruction": f"Check/Execute: {skill.description}",
                "expected_outcome": "System stabilizes or error code clears"
            }
            selected_steps.append(step)
            
        checklist = DiagnosticChecklist(
            task_id=f"TASK_{device_id}_{random.randint(1000, 9999)}",
            target_device=device_id,
            steps=selected_steps,
            generated_at="2023-10-27T10:00:00Z"
        )
        
        logger.debug(f"Checklist {checklist.task_id} generated with {len(checklist.steps)} steps.")
        return checklist

    def process_human_feedback(self, checklist: DiagnosticChecklist, feedback: Dict[str, str]) -> bool:
        """
        [核心函数 2]
        处理人类技工的反馈并更新网络中2555个SKILL的概率权重。
        
        技工只需对清单中的步骤进行简单的通过(PASS)/失败(FAIL)打标。
        系统将根据反馈调整相关Skill的权重。
        
        Args:
            checklist (DiagnosticChecklist): 之前生成的清单对象。
            feedback (Dict[str, str]): 键值对，Step ID -> "PASS" or "FAIL"。
            
        Returns:
            bool: 更新是否成功。
            
        Raises:
            KeyError: 如果反馈中的Step ID不在网络中。
        """
        logger.info(f"Processing feedback for Task: {checklist.task_id}")
        
        if not feedback:
            logger.warning("Empty feedback received.")
            return False

        try:
            for step_id, result_str in feedback.items():
                if step_id not in self.skill_network:
                    logger.error(f"Invalid Skill ID received in feedback: {step_id}")
                    continue

                # 数据验证
                try:
                    status = FeedbackStatus[result_str.upper()]
                except KeyError:
                    logger.error(f"Invalid feedback status '{result_str}' for step {step_id}. Must be PASS or FAIL.")
                    continue

                # 获取当前节点
                node = self.skill_network[step_id]
                old_weight = node.weight
                
                # 权重更新逻辑 (Hebbian-like learning rule simplified)
                # PASS: 增加权重 (加强连接)
                # FAIL: 减少权重 (减弱连接)
                delta = 0.0
                if status == FeedbackStatus.PASS:
                    delta = self.learning_rate * (1.0 - node.weight) # 越接近1增长越慢
                elif status == FeedbackStatus.FAIL:
                    delta = -self.learning_rate * (node.weight - 0.0) # 越接近0减少越慢
                
                new_weight = node.weight + delta
                
                # 边界检查
                node.weight = self._clamp(new_weight, 0.0, 1.0)
                
                # 更新置信度
                node.confidence = min(1.0, node.confidence + 0.01)
                
                logger.info(f"Updated Skill {step_id}: {old_weight:.4f} -> {node.weight:.4f} (Feedback: {status.name})")

            return True

        except Exception as e:
            logger.exception("Error during feedback processing.")
            return False

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """
        [辅助函数]
        将数值限制在指定范围内。
        """
        return max(min_val, min(value, max_val))

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 实例化接口 (初始化包含2555个技能的系统)
    interface = SymbiosisInterface(initial_skill_count=2555)
    
    # 2. AI 生成调试清单
    device_context = {"status": "degraded", "error_code": "0x804"}
    checklist = interface.generate_diagnostic_checklist(device_id="ROBO_ARM_01", context_data=device_context)
    
    print(f"\n--- Generated Checklist for {checklist.target_device} ---")
    for step in checklist.steps:
        print(f"Step {step['step_id']}: {step['instruction']}")

    # 3. 模拟人类技工执行任务并反馈 (简单的通过/失败)
    # 假设技工认为第一个步骤通过，第二个失败，其余随机
    human_feedback = {}
    for i, step in enumerate(checklist.steps):
        if i == 0:
            res = "PASS"
        elif i == 1:
            res = "FAIL"
        else:
            res = random.choice(["PASS", "FAIL"])
        human_feedback[step['step_id']] = res
    
    print(f"\n--- Submitting Human Feedback ---")
    print(json.dumps(human_feedback, indent=2))

    # 4. 更新网络权重
    success = interface.process_human_feedback(checklist, human_feedback)
    
    if success:
        print("\nFeedback processed. Skill network weights updated.")