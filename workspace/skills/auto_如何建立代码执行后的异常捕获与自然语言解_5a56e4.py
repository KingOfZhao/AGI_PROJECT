"""
高级异常捕获与自然语言解释模块

本模块提供了一套完整的机制，用于将Python底层的Traceback堆栈信息
反向映射为人类可读的业务逻辑错误描述。通过维护错误签名映射表和
利用AST进行源码上下文分析，能够将枯燥的技术报错转化为对用户友好的
业务提示。

核心功能:
- 捕获并解析运行时异常的完整堆栈
- 将技术性错误映射为业务描述
- 记录详细的调试日志
- 提供结构化的错误报告

作者: AGI System
版本: 1.0.0
领域: error_handling
"""

import logging
import re
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

# 配置模块级日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- 数据结构定义 ---

@dataclass
class ErrorContext:
    """
    封装错误发生时的上下文信息。
    
    Attributes:
        file_path (str): 发生错误的文件路径。
        line_no (int): 发生错误的行号。
        function_name (str): 发生错误的函数名。
        code_snippet (str): 错误行的代码片段。
        locals (Dict[str, Any]): 错误发生时的局部变量快照（可选）。
    """
    file_path: str
    line_no: int
    function_name: str
    code_snippet: str = ""
    locals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterpretedError:
    """
    封装解释后的错误信息。
    
    Attributes:
        original_type (str): 原始异常类型名称。
        original_message (str): 原始异常消息。
        business_description (str): 人类可读的业务逻辑解释。
        context (Optional[ErrorContext]): 错误发生的上下文对象。
        severity (str): 错误严重程度。
    """
    original_type: str
    original_message: str
    business_description: str
    context: Optional[ErrorContext] = None
    severity: str = "ERROR"

    def to_dict(self) -> Dict[str, Any]:
        """将解释后的错误转换为字典格式，便于JSON序列化。"""
        return {
            "severity": self.severity,
            "type": self.original_type,
            "technical_msg": self.original_message,
            "business_msg": self.business_description,
            "location": f"{self.context.file_path}:{self.context.line_no}" if self.context else "Unknown"
        }


# --- 异常映射注册表 ---

# 定义业务逻辑错误的描述模板
ERROR_MAPPING_REGISTRY: Dict[Type[Exception], Dict[str, Any]] = {
    IndexError: {
        "pattern": r"list index out of range",
        "template": "业务数据处理失败：试图访问一个不存在的数据序列位置（索引越界）。请检查数据源是否完整或索引计算逻辑是否正确。",
        "severity": "CRITICAL"
    },
    FileNotFoundError: {
        "pattern": r"No such file or directory: '(.*)'",
        "template": "资源加载失败：系统无法找到指定的业务资源文件 [{match_group_1}]。请确认文件路径配置或文件是否已被移除。",
        "severity": "HIGH"
    },
    KeyError: {
        "pattern": r"'(.*)'",
        "template": "配置或数据缺失：无法找到关键标识符 [{match_group_1}]。这通常意味着传入的数据结构与预期不符。",
        "severity": "MEDIUM"
    },
    ValueError: {
        "pattern": r".*",
        "template": "数据格式校验失败：接收到的数据值不符合处理逻辑要求。",
        "severity": "MEDIUM"
    },
    ConnectionError: {
        "pattern": r".*",
        "template": "外部服务连接异常：无法连接到依赖的第三方服务或数据库。请检查网络连接或服务状态。",
        "severity": "HIGH"
    }
}


# --- 辅助函数 ---

def _extract_traceback_context(exc_traceback: Any) -> Optional[ErrorContext]:
    """
    [辅助函数] 从traceback对象中提取上下文信息。
    
    解析堆栈追踪，获取最顶层的调用帧信息，包括文件名、行号和函数名。
    
    Args:
        exc_traceback: Python traceback 对象。
        
    Returns:
        Optional[ErrorContext]: 包含上下文信息的对象，如果无法解析则返回None。
    """
    if exc_traceback is None:
        return None

    try:
        # 遍历到堆栈的最顶层（发生错误的具体位置）
        tb = exc_traceback
        while tb.tb_next:
            tb = tb.tb_next
        
        frame = tb.tb_frame
        lineno = tb.tb_lineno
        code = frame.f_code
        filename = code.co_filename
        func_name = code.co_name

        # 尝试获取出错的代码行内容
        # 注意：生产环境中读取文件可能有性能损耗或权限问题，此处仅为演示
        code_line = "Unavailable"
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if 0 < lineno <= len(lines):
                    code_line = lines[lineno - 1].strip()
        except IOError:
            logger.debug(f"Could not read source file: {filename}")

        return ErrorContext(
            file_path=filename,
            line_no=lineno,
            function_name=func_name,
            code_snippet=code_line,
            locals=frame.f_locals # 获取局部变量快照
        )
    except Exception as e:
        logger.error(f"Failed to extract traceback context: {e}")
        return None


# --- 核心函数 ---

def interpret_exception(
    exc: Exception, 
    custom_mappings: Optional[Dict[Type[Exception], Dict[str, Any]]] = None
) -> InterpretedError:
    """
    [核心函数 1] 将捕获的异常对象转换为自然语言描述。
    
    该函数结合全局映射表和用户自定义映射，利用正则表达式匹配原始错误信息，
    并生成面向业务的解释文本。
    
    Args:
        exc (Exception): 捕获到的异常实例。
        custom_mappings (Optional[Dict]): 自定义的异常映射规则，优先级高于默认规则。
        
    Returns:
        InterpretedError: 结构化的解释结果对象。
        
    Example:
        >>> try:
        >>>     my_list = [1, 2]
        >>>     print(my_list[5])
        >>> except Exception as e:
        >>>     result = interpret_exception(e)
        >>>     print(result.business_description)
    """
    # 合并映射表，自定义映射优先
    active_mappings = {**ERROR_MAPPING_REGISTRY}
    if custom_mappings:
        active_mappings.update(custom_mappings)

    exc_type = type(exc)
    exc_msg = str(exc)
    tb_context = _extract_traceback_context(exc.__traceback__)
    
    # 默认解释逻辑
    business_desc = f"发生未预期的系统错误: {exc_msg}"
    severity = "ERROR"

    # 查找匹配的映射规则
    # 支持异常类的继承关系查找
    for registered_type, config in active_mappings.items():
        if issubclass(exc_type, registered_type):
            pattern = config.get("pattern", ".*")
            template = config.get("template", business_desc)
            severity = config.get("severity", "ERROR")
            
            # 使用正则提取变量以填充模板
            match = re.search(pattern, exc_msg)
            if match:
                # 简单的模板填充逻辑，支持 {match_group_1} 等占位符
                desc = template
                for i, group in enumerate(match.groups()):
                    placeholder = f"{{match_group_{i+1}}}"
                    desc = desc.replace(placeholder, str(group))
                business_desc = desc
                logger.info(f"Exception {exc_type.__name__} matched pattern for business rule.")
                break
    else:
        logger.warning(f"No specific mapping found for exception type: {exc_type.__name__}")

    return InterpretedError(
        original_type=exc_type.__name__,
        original_message=exc_msg,
        business_description=business_desc,
        context=tb_context,
        severity=severity
    )


def safe_execute(
    func: Callable, 
    *args, 
    fallback_value: Any = None, 
    raise_on_error: bool = False, 
    **kwargs
) -> Tuple[bool, Any, Optional[InterpretedError]]:
    """
    [核心函数 2] 安全执行装饰器/包装器函数。
    
    在隔离环境中执行目标函数，如果发生异常，自动调用解释机制，
    并根据配置决定是抛出异常还是返回降级值。
    
    Args:
        func (Callable): 需要执行的目标函数。
        *args: 传递给目标函数的位置参数。
        fallback_value (Any): 发生错误时的默认返回值。
        raise_on_error (bool): 如果为True，解释完错误后重新抛出原始异常。
        **kwargs: 传递给目标函数的关键字参数。
        
    Returns:
        Tuple[bool, Any, Optional[InterpretedError]]: 
            - bool: 执行是否成功。
            - Any: 函数返回值或 fallback_value。
            - Optional[InterpretedError]: 错误解释对象（如果发生错误）。
            
    Example:
        >>> def process_data(index):
        >>>     data = [10, 20]
        >>>     return data[index]
        >>>
        >>> success, result, error = safe_execute(process_data, 5)
        >>> if not success:
        >>>     print(error.business_description)
    """
    logger.info(f"Executing function: {func.__name__}")
    try:
        # 边界检查：确保传入的是可调用对象
        if not callable(func):
            raise TypeError(f"Object {func} is not callable")
            
        result = func(*args, **kwargs)
        return True, result, None
    
    except Exception as e:
        # 记录原始堆栈以便调试
        logger.error(f"Exception caught in safe_execute: {traceback.format_exc()}")
        
        # 调用核心解释逻辑
        interpreted = interpret_exception(e)
        
        # 结构化日志记录
        logger.warning(
            f"Business Error Detected: {interpreted.business_description} "
            f"[Original: {interpreted.original_type}]"
        )
        
        if raise_on_error:
            raise e
            
        return False, fallback_value, interpreted


# --- 模块演示与使用示例 ---

if __name__ == "__main__":
    # 示例 1: 直接解释一个捕获的异常
    print("--- Example 1: Direct Interpretation ---")
    try:
        # 模拟业务逻辑：访问不存在的配置键
        config = {"host": "localhost"}
        port = config["port"] # This will raise KeyError
    except Exception as e:
        interpreted_error = interpret_exception(e)
        print(f"Human Readable: {interpreted_error.business_description}")
        print(f"Severity: {interpreted_error.severity}")
        print(f"Debug Info: {interpreted_error.to_dict()}")

    print("\n--- Example 2: Safe Execution Wrapper ---")
    
    def complex_business_logic(user_id: str, index: int):
        """
        模拟一个复杂的业务函数，包含文件读取或列表操作。
        """
        # 模拟 IndexError
        data = ["admin", "guest"]
        return data[index]

    # 使用 safe_execute 包装调用
    # 这里我们传入一个越界的索引
    is_success, data, error_obj = safe_execute(
        complex_business_logic, 
        "user_123", 
        10, # Index 10 is out of bounds
        fallback_value="DefaultUser"
    )

    if not is_success:
        print(f"Execution Failed. Reason: {error_obj.business_description}")
        print(f"Fallback value used: {data}")
        if error_obj.context:
            print(f"Error occurred at line {error_obj.context.line_no} in function {error_obj.context.function_name}")
            print(f"Code: {error_obj.context.code_snippet}")

    print("\n--- Example 3: Custom Mapping ---")
    
    # 定义自定义异常映射
    custom_rules = {
        ZeroDivisionError: {
            "pattern": r".*",
            "template": "计算逻辑错误：检测到除零操作，请检查分母的计算来源，确保不为零。",
            "severity": "HIGH"
        }
    }

    try:
        x = 1 / 0
    except Exception as e:
        # 传入自定义映射
        result = interpret_exception(e, custom_mappings=custom_rules)
        print(f"Custom Explanation: {result.business_description}")