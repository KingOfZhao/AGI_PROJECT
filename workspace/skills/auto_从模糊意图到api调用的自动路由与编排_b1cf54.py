"""
高级技能模块：从模糊意图到API调用的自动路由与编排

该模块实现了一个轻量级的执行引擎，能够将用户的模糊意图（如"给团队发送警报"）
解析为具体的API调用步骤。它包含以下核心功能：
1. 动态规划：基于当前上下文选择最优的API执行路径。
2. 错误处理：支持自动重试机制和执行链的回滚。
3. 技能树构建：将静态配置转化为可执行的图结构。

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class APIStep:
    """
    定义API调用的单个步骤（技能树的节点）。
    
    Attributes:
        name (str): 步骤名称
        action (Callable): 具体执行的函数
        compensation (Callable): 失败时的回滚函数
        retries (int): 重试次数
        inputs (Dict): 输入参数映射（从上下文中获取）
    """
    name: str
    action: Callable[..., Any]
    compensation: Optional[Callable[..., Any]] = None
    retries: int = 1
    inputs: Dict[str, str] = field(default_factory=dict)

@dataclass
class ExecutionContext:
    """
    执行上下文，维护运行时状态和数据。
    
    Attributes:
        intent (str): 用户的原始意图
        current_data (Dict): 当前步骤产生的数据
        execution_path (List): 已执行的步骤历史
        status (ExecutionStatus): 当前整体状态
    """
    intent: str
    current_data: Dict[str, Any] = field(default_factory=dict)
    execution_path: List[Tuple[str, ExecutionStatus]] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING

def _validate_payload(payload: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    [Helper] 验证输入数据是否包含必须的字段。
    
    Args:
        payload (Dict): 待验证的数据
        required_keys (List): 必须存在的键列表
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ValueError: 如果缺少必须字段
    """
    if not isinstance(payload, dict):
        logger.error("输入数据格式错误，期望Dict")
        raise ValueError("Payload must be a dictionary")
        
    missing = [key for key in required_keys if key not in payload]
    if missing:
        logger.warning(f"数据验证失败，缺少字段: {missing}")
        return False
    return True

def build_skill_tree(config: Dict[str, Any]) -> List[APIStep]:
    """
    根据配置构建执行链（技能树）。
    在真实场景中，这里会包含复杂的图构建逻辑。
    
    Args:
        config (Dict): 包含步骤定义的配置字典
        
    Returns:
        List[APIStep]: 排序后的执行步骤列表
        
    Example:
        >>> cfg = {
        ...     "steps": [
        ...         {"name": "auth", "type": "http", "endpoint": "/login"},
        ...         {"name": "send", "type": "http", "endpoint": "/msg"}
        ...     ]
        ... }
        >>> tree = build_skill_tree(cfg)
    """
    logger.info("正在构建API技能树...")
    steps = []
    
    # 模拟将配置转化为可执行对象
    # 这里使用模拟的函数代替真实的API调用
    
    def mock_auth_action(user: str) -> Dict:
        logger.info(f"模拟认证用户: {user}")
        return {"token": f"mock-token-{random.randint(1000, 9999)}"}

    def mock_send_action(token: str, message: str) -> Dict:
        logger.info(f"使用 {token} 发送消息: {message}")
        # 模拟偶尔失败以测试重试
        if random.random() < 0.2:
            raise ConnectionError("Network unstable")
        return {"msg_id": "msg_5566"}

    def mock_send_compensation(token: str, msg_id: str) -> None:
        logger.warning(f"回滚操作: 撤回消息 {msg_id}")

    # 硬编码一个简单的链式逻辑用于演示
    if config.get("intent") == "send_message":
        steps.append(APIStep(
            name="authenticate",
            action=mock_auth_action,
            inputs={"user": "context.user"}
        ))
        steps.append(APIStep(
            name="send_message",
            action=mock_send_action,
            compensation=mock_send_compensation,
            retries=3,
            inputs={"token": "prev_step.token", "message": "context.message"}
        ))
        
    return steps

def execute_orchestration(
    intent: str, 
    user_context: Dict[str, Any], 
    skill_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    核心执行引擎：处理意图，编排API调用，处理重试与回滚。
    
    Args:
        intent (str): 目标意图，如 'send_message'
        user_context (Dict): 用户的输入数据，如 {'user': 'admin', 'message': 'Hello'}
        skill_config (Dict): 系统配置
        
    Returns:
        Dict[str, Any]: 包含执行结果和状态的字典
        
    Example:
        >>> result = execute_orchestration(
        ...     "send_message", 
        ...     {"user": "alice", "message": "Test"}, 
        ...     {"intent": "send_message"}
        ... )
        >>> print(result['status'])
        success
    """
    # 初始化上下文
    ctx = ExecutionContext(intent=intent, current_data={"context": user_context})
    ctx.status = ExecutionStatus.RUNNING
    
    # 1. 构建技能树
    pipeline = build_skill_tree(skill_config)
    if not pipeline:
        logger.error("无法为意图构建执行路径")
        return {"status": "error", "message": "No valid path found"}

    logger.info(f"开始执行编排链，共 {len(pipeline)} 个步骤")

    try:
        # 2. 顺序执行步骤（可扩展为DAG拓扑排序执行）
        for step in pipeline:
            logger.info(f"执行步骤: {step.name}")
            
            # 准备参数：从上下文中解析输入
            # 简化的参数解析逻辑：prev_step.token -> ctx.current_data['authenticate']['token']
            try:
                step_args = {}
                for target_key, source_path in step.inputs.items():
                    # 极简路径解析
                    if source_path.startswith("context."):
                        key = source_path.split(".")[1]
                        step_args[target_key] = ctx.current_data["context"][key]
                    elif source_path.startswith("prev_step."):
                        # 获取上一步的结果
                        prev_step_name = ctx.execution_path[-1][0]
                        key = source_path.split(".")[1]
                        step_args[target_key] = ctx.current_data[prev_step_name][key]
            except KeyError as e:
                logger.error(f"参数解析失败: {e}")
                raise ValueError(f"Missing data for step {step.name}: {e}")

            # 3. 执行与重试机制
            attempt = 0
            last_exception = None
            while attempt < step.retries:
                try:
                    result = step.action(**step_args)
                    ctx.current_data[step.name] = result
                    ctx.execution_path.append((step.name, ExecutionStatus.SUCCESS))
                    logger.info(f"步骤 {step.name} 成功")
                    break
                except Exception as e:
                    attempt += 1
                    last_exception = e
                    logger.warning(f"步骤 {step.name} 失败 (尝试 {attempt}/{step.retries}): {str(e)}")
                    time.sleep(0.5) # 简单的退避策略
            
            # 如果重试耗尽仍然失败
            if attempt == step.retries:
                ctx.status = ExecutionStatus.FAILED
                raise RuntimeError(f"Step {step.name} failed after retries.") from last_exception

        ctx.status = ExecutionStatus.SUCCESS
        return {
            "status": ctx.status.value,
            "data": ctx.current_data,
            "trace": ctx.execution_path
        }

    except Exception as global_e:
        logger.error(f"执行过程中断，触发回滚机制: {global_e}")
        
        # 4. 回滚逻辑 (补偿事务)
        # 从后向前执行补偿
        for step_name, status in reversed(ctx.execution_path):
            if status == ExecutionStatus.SUCCESS:
                # 找到对应的步骤定义以获取补偿函数
                step_def = next((s for s in pipeline if s.name == step_name), None)
                if step_def and step_def.compensation:
                    try:
                        logger.info(f"正在回滚步骤: {step_name}")
                        # 注意：实际回滚需要传入之前的执行结果
                        step_def.compensation(None, None) # 此处参数简化
                    except Exception as comp_e:
                        logger.error(f"回滚失败 {step_name}: {comp_e}")
        
        return {
            "status": ExecutionStatus.FAILED.value,
            "error": str(global_e),
            "trace": ctx.execution_path
        }

if __name__ == "__main__":
    # 使用示例
    mock_config = {"intent": "send_message"}
    user_input = {"user": "engineer_01", "message": "System Alert: CPU High"}
    
    print("--- 开始运行自动编排引擎 ---")
    result = execute_orchestration(
        intent="send_message",
        user_context=user_input,
        skill_config=mock_config
    )
    
    print("\n--- 最终结果 ---")
    print(f"状态: {result['status']}")
    print(f"数据: {result.get('data', {})}")
    print(f"轨迹: {result.get('trace', [])}")