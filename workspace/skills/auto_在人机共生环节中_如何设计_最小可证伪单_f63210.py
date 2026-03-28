"""
模块名称: mfu_protocol_generator
描述: 在人机共生环节中，实现'最小可证伪单元'的生成协议。
      本模块旨在将宏大的抽象目标（真实节点）转化为具体的、可执行的、
      具有明确二元反馈（真/伪）的微任务协议。

作者: AGI System Core Team
版本: 1.0.0
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    """任务复杂度枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class ValidationError(Exception):
    """自定义数据验证错误"""
    pass

@dataclass
class TruthNode:
    """
    真实节点数据结构 - 代表宏大的、未经验证的假设或目标。
    
    Attributes:
        node_id (str): 节点唯一标识符
        description (str): 节点的自然语言描述
        context (Dict[str, Any]): 相关的上下文元数据
        created_at (datetime): 创建时间
    """
    node_id: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class MFUTask:
    """
    最小可证伪单元 数据结构。
    
    Attributes:
        task_id (str): 任务唯一ID
        parent_node_id (str): 关联的父节点ID
        action_directive (str): 人类必须执行的具体物理或数字动作指令
        expected_evidence (str): 期望得到的证据描述
        verification_method (str): 验证方法
        estimated_duration (timedelta): 预计耗时
        is_falsifiable (bool): 是否满足可证伪性标准
    """
    task_id: str
    parent_node_id: str
    action_directive: str
    expected_evidence: str
    verification_method: str
    estimated_duration: timedelta
    is_falsifiable: bool = True
    created_at: datetime = field(default_factory=datetime.now)

class MFUProtocolGenerator:
    """
    负责将抽象的 TruthNode 分解为具体的 MFUTask 的协议生成器。
    
    核心逻辑是将自然语言描述转化为实验性步骤，确保每一步都能产生
    二元反馈（成功/失败），从而驱动AGI系统的下一轮迭代。
    """
    
    def __init__(self, max_duration_hours: float = 24.0):
        """
        初始化生成器。
        
        Args:
            max_duration_hours (float): 单个微任务的最大允许时长（小时）。
        """
        self.max_duration_hours = max_duration_hours
        self._task_counter = 0
        logger.info("MFUProtocolGenerator initialized with max duration: %s hours", max_duration_hours)

    def _validate_node(self, node: TruthNode) -> None:
        """
        辅助函数：验证输入节点的有效性。
        
        Args:
            node (TruthNode): 待验证的节点
            
        Raises:
            ValidationError: 如果节点数据无效
        """
        if not node.node_id or not isinstance(node.node_id, str):
            raise ValidationError("Invalid node_id: Must be a non-empty string.")
        if not node.description or len(node.description) < 10:
            raise ValidationError("Description too short or empty to generate MFU.")
        
        # 简单的启发式检查：确保描述中包含动词，暗示可执行性潜力
        if not re.search(r'\b(is|are|can|create|build|test|verify|run|execute)\b', node.description.lower()):
            logger.warning(f"Node {node.node_id} description lacks actionable verbs.")

    def _calculate_task_duration(self, complexity: TaskComplexity) -> timedelta:
        """
        辅助函数：根据复杂度估算任务时长。
        
        Args:
            complexity (TaskComplexity): 任务复杂度枚举值
            
        Returns:
            timedelta: 预估的时间增量
        """
        base_hours = {
            TaskComplexity.LOW: 0.5,
            TaskComplexity.MEDIUM: 2.0,
            TaskComplexity.HIGH: 8.0
        }
        return timedelta(hours=base_hours.get(complexity, 1.0))

    def _generate_actionable_directive(self, description: str) -> Tuple[str, str, str]:
        """
        [核心逻辑] 将描述性文本转化为行动指令和验证标准。
        这是一个简化的NLP逻辑模拟，实际AGI系统会使用LLM。
        
        Args:
            description (str): 原始目标描述
            
        Returns:
            Tuple[str, str, str]: (行动指令, 期望证据, 验证方法)
        """
        # 模拟NLP处理：提取关键词并生成指令
        # 在真实场景中，这里会调用LLM进行Few-Shot生成
        
        if "server" in description.lower() or "api" in description.lower():
            action = f"Send a GET request to the endpoint defined in context and record the HTTP status code."
            evidence = "A log entry showing the exact HTTP status code (e.g., 200, 404, 500)."
            verify = "Check if status code == 200"
        elif "document" in description.lower() or "read" in description.lower():
            action = f"Locate the specific section mentioned and extract the defined parameter value."
            evidence = "The specific string or integer value found in the document."
            verify = "Compare extracted value against expected regex pattern."
        else:
            # 通用物理世界交互
            action = f"Perform the physical operation described: '{description}' and take a photo."
            evidence = "A timestamped photo or log file of the operation result."
            verify = "Visual confirmation of the state change."
            
        return action, evidence, verify

    def decompose_node(self, node: TruthNode) -> List[MFUTask]:
        """
        [核心函数] 将宏大的真实节点分解为最小可证伪单元列表。
        
        Args:
            node (TruthNode): 输入的抽象目标节点
            
        Returns:
            List[MFUTask]: 生成的微任务列表
            
        Raises:
            ValidationError: 输入数据校验失败
            ValueError: 处理逻辑中的数值错误
        """
        try:
            self._validate_node(node)
            logger.info(f"Starting decomposition for Node: {node.node_id}")
            
            tasks: List[MFUTask] = []
            
            # 模拟分解逻辑：这里假设一个节点生成一个主要的MFU
            # 实际系统中这里会进行递归分解直到粒度满足要求
            action, evidence, verify = self._generate_actionable_directive(node.description)
            
            # 确定任务时长
            duration = self._calculate_task_duration(TaskComplexity.MEDIUM)
            
            if duration.total_seconds() / 3600 > self.max_duration_hours:
                logger.warning(f"Generated task exceeds max duration. Splitting required (not implemented in this demo).")
                # 在生产环境中，这里会触发进一步的分解递归
            
            self._task_counter += 1
            task_id = f"MFU-{node.node_id}-{self._task_counter}"
            
            new_task = MFUTask(
                task_id=task_id,
                parent_node_id=node.node_id,
                action_directive=action,
                expected_evidence=evidence,
                verification_method=verify,
                estimated_duration=duration,
                is_falsifiable=True # 协议保证生成的任务必须是可证伪的
            )
            
            tasks.append(new_task)
            logger.info(f"Successfully generated Task: {task_id}")
            return tasks

        except ValidationError as ve:
            logger.error(f"Validation failed for node {node.node_id}: {ve}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during decomposition: {e}", exc_info=True)
            raise RuntimeError("MFU Generation Protocol Failed") from e

    def export_protocol(self, tasks: List[MFUTask], format_type: str = "json") -> str:
        """
        导出生成的协议以供人类或机器读取。
        
        Args:
            tasks (List[MFUTask]): 任务列表
            format_type (str): 导出格式，默认为 'json'
            
        Returns:
            str: 格式化后的字符串
        """
        if format_type != "json":
            raise NotImplementedError("Only JSON export is currently supported.")
        
        output_data = []
        for task in tasks:
            task_dict = asdict(task)
            # 转换不可序列化的对象
            task_dict['estimated_duration'] = str(task.estimated_duration)
            task_dict['created_at'] = task.created_at.isoformat()
            output_data.append(task_dict)
            
        return json.dumps(output_data, indent=2)

# Example Usage
if __name__ == "__main__":
    # 1. 定义一个宏大的、模糊的“真实节点”
    vague_goal = TruthNode(
        node_id="NODE-2023-Alpha",
        description="Verify if the new database migration script handles UTF-8 characters correctly on the legacy server.",
        context={"server_ip": "192.168.1.50", "script_path": "/opt/migrate.sh"}
    )

    # 2. 初始化协议生成器
    generator = MFUProtocolGenerator(max_duration_hours=24.0)

    try:
        # 3. 执行分解协议
        mfu_tasks = generator.decompose_node(vague_goal)

        # 4. 导出并展示结果
        protocol_json = generator.export_protocol(mfu_tasks)
        print("Generated MFU Protocol:")
        print(protocol_json)

        print("\n--- Human Instruction ---")
        print(f"Task ID: {mfu_tasks[0].task_id}")
        print(f"Action: {mfu_tasks[0].action_directive}")
        print(f"Evidence Required: {mfu_tasks[0].expected_evidence}")
        print(f"Time Limit: {mfu_tasks[0].estimated_duration}")

    except Exception as e:
        print(f"Protocol execution failed: {e}")