"""
意图-代码参数闭环校验模块

本模块旨在解决AGI系统中自然语言意图与生成代码参数之间的双向约束问题。
它能够将用户的隐含约束（如“只处理前10行”、“不要覆盖原文件”）转化为结构化的策略，
并在代码执行前后进行严格的校验与监控。若检测到违规行为，系统将自动截停并回滚。

核心功能：
1. 意图解析：将自然语言意图转化为约束策略对象。
2. 参数校验：在执行前检查输入参数是否符合约束。
3. 监控执行：在执行后检查结果是否越界，并支持回滚操作。

输入格式说明：
- intent_text: str, 用户的自然语言指令。
- params: dict, 待执行函数的参数字典。
- target_func: Callable, 实际执行业务逻辑的函数。

输出格式说明：
- 执行成功返回函数的原始返回值。
- 抛出 ConstraintViolationError 当约束被违反。
"""

import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConstraintViolationError(RuntimeError):
    """当生成的代码或参数违反用户意图约束时抛出此异常。"""
    pass


@dataclass
class ConstraintPolicy:
    """
    从用户意图中提取的结构化约束策略。
    
    Attributes:
        max_rows: Optional[int]: 允许处理的最大行数，None表示无限制。
        allow_overwrite: bool: 是否允许覆盖已存在的文件。
        safe_mode: bool: 是否启用沙箱或临时文件模式。
        output_dir: Optional[str]: 限制的输出目录。
    """
    max_rows: Optional[int] = None
    allow_overwrite: bool = False
    safe_mode: bool = True
    output_dir: Optional[str] = None


def extract_constraints_from_intent(intent_text: str) -> ConstraintPolicy:
    """
    [辅助函数] 解析自然语言意图，生成约束策略对象。
    
    此处使用简单的正则匹配模拟NLP解析过程。在实际AGI系统中，
    这部分可能由LLM完成并输出结构化JSON。
    
    Args:
        intent_text: 用户的自然语言指令。
        
    Returns:
        ConstraintPolicy: 包含提取规则的策略对象。
        
    Examples:
        >>> extract_constraints_from_intent("只处理前10行，不要覆盖原文件")
        ConstraintPolicy(max_rows=10, allow_overwrite=False, ...)
    """
    logger.info(f"正在解析意图: '{intent_text}'")
    policy = ConstraintPolicy()
    
    # 提取行数限制 (例如: "前10行", "limit 5")
    row_match = re.search(r'前(\d+)行|limit\s*(\d+)', intent_text, re.IGNORECASE)
    if row_match:
        policy.max_rows = int(row_match.group(1) or row_match.group(2))
        logger.info(f"检测到行数约束: max_rows={policy.max_rows}")
        
    # 提取覆盖限制 (例如: "不要覆盖", "no overwrite")
    if any(keyword in intent_text for keyword in ['不要覆盖', '禁止覆盖', 'no overwrite']):
        policy.allow_overwrite = False
        logger.info("检测到禁止覆盖约束")
    else:
        policy.allow_overwrite = True
        
    return policy


def validate_execution_params(params: Dict[str, Any], policy: ConstraintPolicy) -> None:
    """
    [核心函数1] 执行前的参数双向校验。
    
    检查传入的参数是否显式或隐式地违反了从意图中提取的策略。
    
    Args:
        params: 待执行函数的参数字典。
        policy: 约束策略对象。
        
    Raises:
        ConstraintViolationError: 如果参数违反约束。
    """
    logger.info("开始执行前参数校验...")
    
    # 1. 检查行数参数
    if policy.max_rows is not None:
        # 检查常见的参数名，如 limit, nrows, head
        limit_keys = ['limit', 'nrows', 'max_rows', 'head']
        for key in limit_keys:
            if key in params:
                if params[key] > policy.max_rows:
                    msg = f"参数校验失败: 参数 '{key}={params[key]}' 超过了意图约束的最大值 {policy.max_rows}"
                    logger.error(msg)
                    raise ConstraintViolationError(msg)
                # 如果参数未设置但策略有要求，自动注入约束（双向约束的一部分）
                elif params[key] is None:
                    params[key] = policy.max_rows
                    logger.info(f"自动注入约束参数: {key}={policy.max_rows}")

    # 2. 检查文件覆盖风险
    if not policy.allow_overwrite:
        output_path = params.get('output_path') or params.get('filename')
        if output_path and os.path.exists(output_path):
            msg = f"参数校验失败: 意图禁止覆盖，但目标文件 '{output_path}' 已存在。"
            logger.error(msg)
            raise ConstraintViolationError(msg)
            
    logger.info("参数校验通过。")


def execute_with_monitoring(
    target_func: Callable,
    params: Dict[str, Any],
    policy: ConstraintPolicy
) -> Any:
    """
    [核心函数2] 带实时监控和回滚机制的执行器。
    
    执行目标函数，监控其行为（如实际处理的行数），并在违规时回滚。
    
    Args:
        target_func: 要执行的业务逻辑函数。
        params: 传递给业务函数的参数。
        policy: 约束策略对象。
        
    Returns:
        Any: target_func 的返回值。
        
    Raises:
        ConstraintViolationError: 如果执行结果违反约束。
    """
    # 1. 预校验
    validate_execution_params(params, policy)
    
    # 2. 准备执行环境（例如：使用临时文件以实现回滚）
    original_output_path = params.get('output_path')
    temp_output_path = None
    
    if original_output_path and policy.safe_mode:
        # 创建临时文件路径
        base_dir = os.path.dirname(original_output_path) or "."
        temp_output_path = os.path.join(base_dir, f".tmp_{os.path.basename(original_output_path)}")
        params['output_path'] = temp_output_path
        logger.info(f"安全模式已启用: 将先写入临时文件 {temp_output_path}")

    try:
        # 3. 执行函数
        logger.info(f"正在执行函数: {target_func.__name__}")
        result = target_func(**params)
        
        # 4. 执行后监控 (Post-Execution Validation)
        # 假设函数返回一个包含统计信息的字典，或者我们检查文件大小
        if policy.max_rows is not None and temp_output_path and os.path.exists(temp_output_path):
            with open(temp_output_path, 'r') as f:
                actual_rows = sum(1 for _ in f)
            
            if actual_rows > policy.max_rows:
                msg = f"执行监控拦截: 实际生成行数 {actual_rows} 超过约束 {policy.max_rows}。正在回滚..."
                logger.error(msg)
                # 回滚操作：删除临时文件
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                raise ConstraintViolationError(msg)
        
        # 5. 提交结果 (将临时文件移动到最终位置)
        if temp_output_path and original_output_path:
            shutil.move(temp_output_path, original_output_path)
            logger.info(f"操作成功，结果已保存至 {original_output_path}")
            
        return result

    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        # 清理临时文件
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
                logger.info("临时文件已清理。")
            except OSError:
                pass
        raise  # 重新抛出异常


# ==========================================
# 示例使用场景
# ==========================================

def mock_data_processing_task(output_path: str, nrows: int = None) -> Dict[str, Any]:
    """
    模拟一个数据处理任务。
    注意：这个函数故意设计得比较“笨”，如果不加监控，可能会写出超过预期的数据。
    """
    # 模拟生成数据：如果 nrows 为 None，默认生成 100 行
    count = nrows if nrows is not None else 100
    
    with open(output_path, 'w') as f:
        for i in range(count):
            f.write(f"Data Line {i+1}\n")
            
    return {"status": "success", "rows_generated": count}

if __name__ == "__main__":
    # 场景 1: 用户意图是“只处理前5行”，但代码参数试图传入 10
    print("--- 场景 1: 参数拦截 ---")
    user_intent = "请处理数据，只保留前5行"
    policy = extract_constraints_from_intent(user_intent)
    
    try:
        # 尝试传入 nrows=10，这应该被拦截或自动修正
        execute_with_monitoring(
            target_func=mock_data_processing_task,
            params={"output_path": "data_output.txt", "nrows": 10},
            policy=policy
        )
    except ConstraintViolationError as e:
        print(f"捕获到预期异常: {e}")

    # 场景 2: 用户意图是“不要覆盖”，且代码试图生成大量数据
    # 我们先创建一个空文件模拟已存在
    with open("protected_data.txt", "w") as f:
        f.write("Original Content\n")
        
    print("\n--- 场景 2: 文件覆盖拦截 ---")
    user_intent_2 = "生成报表，但绝对不要覆盖原文件"
    policy_2 = extract_constraints_from_intent(user_intent_2)
    
    try:
        execute_with_monitoring(
            target_func=mock_data_processing_task,
            params={"output_path": "protected_data.txt", "nrows": 5},
            policy=policy_2
        )
    except ConstraintViolationError as e:
        print(f"捕获到预期异常: {e}")

    # 场景 3: 正常执行与回滚
    # 代码试图生成100行，但意图限制为10行。系统应生成文件后发现行数不对并删除文件。
    print("\n--- 场景 3: 执行后监控与回滚 ---")
    user_intent_3 = "只生成10行测试数据"
    policy_3 = extract_constraints_from_intent(user_intent_3)
    
    try:
        # 故意不传 nrows，让 mock 函数默认生成 100 行
        execute_with_monitoring(
            target_func=mock_data_processing_task,
            params={"output_path": "test_rollback.txt"}, 
            policy=policy_3
        )
    except ConstraintViolationError as e:
        print(f"捕获到预期异常: {e}")
        if not os.path.exists("test_rollback.txt"):
            print("验证成功: 违规文件已被系统自动删除（回滚）。")