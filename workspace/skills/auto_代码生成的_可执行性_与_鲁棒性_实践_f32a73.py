"""
模块名称: robust_code_generator
描述: 本模块演示了在AGI系统中生成高质量、高鲁棒性Python代码的最佳实践。
      它专注于代码生成的‘可执行性’与‘鲁棒性’，确保代码在边缘条件、
      异常输入或资源受限的情况下依然能够优雅处理。
"""

import logging
import hashlib
import json
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

# 配置全局日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 定义类型别名，提高代码可读性
JsonDict = Dict[str, Any]
ExecutionResult = Tuple[bool, Union[str, None], Union[JsonDict, None]]

@dataclass
class CodeArtifact:
    """
    用于存储生成的代码元数据的数据类。
    
    属性:
        code_str: 生成的代码字符串。
        language: 编程语言类型。
        dependencies: 依赖库列表。
        signature: 函数签名哈希，用于唯一标识。
    """
    code_str: str
    language: str
    dependencies: List[str]
    signature: str

def _validate_input_schema(payload: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    [辅助函数] 验证输入数据是否包含必需的键，并且类型有效。
    
    参数:
        payload: 输入的数据字典。
        required_keys: 必须存在的键列表。
        
    返回:
        bool: 如果验证通过返回True，否则抛出ValueError。
        
    异常:
        ValueError: 当缺少键或键值为空时抛出。
    """
    if not isinstance(payload, dict):
        logger.error(f"输入验证失败: 期望dict，得到 {type(payload)}")
        raise ValueError("Invalid payload type: Expected a dictionary.")
    
    missing_keys = [key for key in required_keys if key not in payload or payload[key] is None]
    if missing_keys:
        logger.warning(f"输入验证失败: 缺少键或值为None -> {missing_keys}")
        raise ValueError(f"Missing required keys: {missing_keys}")
    
    return True

def generate_robust_signature(func_name: str, description: str, timestamp: float) -> str:
    """
    [核心函数 1] 生成唯一的技能签名，用于追踪代码版本和确保一致性。
    包含边界检查和输入清洗。
    
    参数:
        func_name: 目标函数名称。
        description: 功能描述文本。
        timestamp: 生成时的时间戳。
        
    返回:
        str: 唯一的哈希签名。
        
    示例:
        >>> sig = generate_robust_signature("data_sort", "sorts data", time.time())
        >>> isinstance(sig, str)
        True
    """
    logger.info(f"开始生成签名: {func_name}")
    
    # 边界检查：确保字符串非空且为安全字符
    if not func_name or not isinstance(func_name, str):
        logger.error("无效的函数名输入")
        raise ValueError("Function name must be a non-empty string.")
    
    if not description:
        description = "default_description"  # 优雅降级处理空描述
    
    # 防止注入或过长字符串导致处理时间过长 (DoS防护)
    safe_func_name = func_name[:50] 
    safe_description = description[:100]
    
    try:
        raw_data = f"{safe_func_name}:{safe_description}:{timestamp}"
        # 使用SHA256确保唯一性
        hash_obj = hashlib.sha256(raw_data.encode('utf-8'))
        signature = hash_obj.hexdigest()[:16] # 截取前16位作为简短签名
        logger.debug(f"生成签名成功: {signature}")
        return signature
    except Exception as e:
        logger.critical(f"签名生成过程中发生未知错误: {e}", exc_info=True)
        raise RuntimeError("Signature generation failed.") from e

def execute_skill_with_sandbox(
    code_snippet: str, 
    input_data: JsonDict, 
    timeout_seconds: int = 5
) -> ExecutionResult:
    """
    [核心函数 2] 模拟执行生成的代码片段，并包含严格的异常捕获和资源限制。
    
    此函数旨在演示AGI生成的代码如何安全地处理外部输入。
    注意：实际生产环境中应使用Docker或Subprocess隔离，此处为演示逻辑。
    
    参数:
        code_snippet: 要执行的Python代码字符串。
        input_data: 传递给代码的输入数据字典。
        timeout_seconds: 模拟的超时时间（秒）。
        
    返回:
        ExecutionResult: 元组 (success: bool, error_msg: Optional[str], output: Optional[JsonDict])
        
    示例:
        >>> code = "def run(x): return {'res': x['val'] + 1}"
        >>> data = {'val': 10}
        >>> success, err, out = execute_skill_with_sandbox(code, data)
        >>> success
        True
    """
    logger.info("准备在沙箱环境中执行代码...")
    
    # 1. 数据验证
    try:
        _validate_input_schema(input_data, [])
    except ValueError as ve:
        return False, str(ve), None

    # 2. 静态代码检查 (模拟 - 简单检查危险操作)
    forbidden_keywords = ["import os", "import sys", "eval(", "exec("]
    for keyword in forbidden_keywords:
        if keyword in code_snippet:
            logger.warning(f"检测到危险操作: {keyword}")
            return False, f"SecurityViolation: Use of forbidden keyword '{keyword}'", None

    # 3. 执行逻辑 (模拟执行过程)
    start_time = time.time()
    try:
        # 模拟资源耗尽保护
        if len(code_snippet) > 10000:
            raise MemoryError("Code snippet size exceeds memory limit.")
            
        # 模拟执行延迟
        time.sleep(0.1) 
        
        # 模拟业务逻辑处理
        if "error_trigger" in input_data:
            raise ValueError("Input triggered a simulated logic error.")
            
        result_data = {
            "status": "executed",
            "processed_values": input_data,
            "timestamp": start_time
        }
        
        # 模拟超时检查
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Execution timed out.")

        logger.info("代码执行成功")
        return True, None, result_data

    except MemoryError as me:
        logger.error(f"资源耗尽异常: {me}")
        return False, "SystemResourceExhausted", None
    except TimeoutError as te:
        logger.error(f"执行超时: {te}")
        return False, "ExecutionTimeout", None
    except Exception as e:
        logger.error(f"运行时异常捕获: {e}", exc_info=True)
        return False, f"RuntimeError: {str(e)}", None

if __name__ == "__main__":
    # 使用示例
    
    # 1. 生成签名
    try:
        sig = generate_robust_signature("process_data", "处理大数据集", time.time())
        print(f"生成的唯一签名: {sig}")
    except Exception as e:
        print(f"签名生成失败: {e}")

    # 2. 准备代码和数据
    mock_code = """
def process(input):
    return {'result': input['value'] * 2}
    """
    
    valid_input = {"value": 100}
    malicious_input = {"value": 100, "error_trigger": True}
    
    # 3. 执行代码
    print("\n--- 测试正常执行 ---")
    success, error, result = execute_skill_with_sandbox(mock_code, valid_input)
    print(f"成功: {success}, 结果: {result}")

    print("\n--- 测试异常处理 ---")
    success, error, result = execute_skill_with_sandbox(mock_code, malicious_input)
    print(f"成功: {success}, 错误: {error}")

    print("\n--- 测试危险代码 ---")
    dangerous_code = "import os; os.system('rm -rf /')"
    success, error, result = execute_skill_with_sandbox(dangerous_code, valid_input)
    print(f"成功: {success}, 错误: {error}")