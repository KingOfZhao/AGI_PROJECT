"""
模块名称: auto_如何实现_最小可执行单元_的代码化封装与_760ab8
领域: software_engineering
描述: 本模块实现了将抽象知识（如“摆摊技巧”）转化为最小可执行单元（MEU）的代码化封装，
      并通过多进程沙箱机制隔离执行环境，确保主系统的安全性与稳定性。
"""

import logging
import multiprocessing
import time
import traceback
from typing import Any, Dict, List, Optional, Callable

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_TIMEOUT = 5  # 默认执行超时时间（秒）
ALLOWED_BUILTINS = {
    'abs': abs, 'min': min, 'max': max, 'len': len, 'str': str, 'int': int,
    'float': float, 'round': round, 'sum': sum, 'pow': pow, 'range': range,
    'print': print  # 允许打印以便调试，但在生产环境中可移除
}


class SkillExecutionError(Exception):
    """自定义异常：用于封装沙箱执行过程中的错误"""
    pass


def validate_io_schema(data: Dict[str, Any], schema: Dict[str, type]) -> bool:
    """
    辅助函数：验证输入/输出数据是否符合预定义的Schema。
    
    参数:
        data: 待验证的数据字典。
        schema: 定义了键名和预期类型的字典。
        
    返回:
        bool: 如果验证通过返回True，否则返回False。
        
    示例:
        >>> validate_io_schema({'price': 10.5}, {'price': (int, float)})
        True
    """
    if not isinstance(data, dict):
        logger.error("数据验证失败：输入不是字典类型")
        return False

    for key, expected_type in schema.items():
        if key not in data:
            logger.error(f"数据验证失败：缺少必需的键 '{key}'")
            return False
        if not isinstance(data[key], expected_type):
            logger.error(
                f"数据验证失败：键 '{key}' 的类型应为 {expected_type}，实际为 {type(data[key])}"
            )
            return False
    return True


def generate_meu_code(skill_name: str, logic_template: str, input_params: List[str]) -> str:
    """
    核心函数1：代码生成器。将非结构化的逻辑字符串封装为标准的Python函数。
    
    参数:
        skill_name: 生成的函数名称。
        logic_template: 包含业务逻辑的代码片段（例如："return cost * 1.2"）。
        input_params: 函数的参数名列表。
        
    返回:
        str: 完整的Python函数代码字符串。
        
    异常:
        ValueError: 如果逻辑模板包含潜在的不安全语法（简单检查）。
    """
    # 简单的安全检查：禁止导入语句，防止在沙箱外绕过限制
    dangerous_keywords = ['import', 'exec', 'eval', 'open', 'os.', 'sys.']
    template_lower = logic_template.lower()
    for kw in dangerous_keywords:
        if kw in template_lower:
            raise ValueError(f"安全警告：逻辑模板中包含禁止的关键词 '{kw}'")

    params_str = ", ".join(input_params)
    code_wrapper = f"""
def {skill_name}({params_str}):
    \"\"\"Auto-generated skill function: {skill_name}\"\"\"
    try:
        # 业务逻辑开始
        result = {logic_template}
        # 业务逻辑结束
        return result
    except Exception as e:
        # 捕获内部逻辑错误并返回错误信息字符串
        return str(e)
"""
    return code_wrapper.strip()


def _run_isolated_process(code_str: str, inputs: Dict[str, Any], result_queue: multiprocessing.Queue):
    """
    核心函数2（内部）：沙箱执行目标函数。运行在独立的进程中。
    
    参数:
        code_str: 包含函数定义的Python代码字符串。
        inputs: 传递给函数的参数字典。
        result_queue: 用于将执行结果或异常传回主进程的队列。
    """
    # 构建受限的全局命名空间
    restricted_globals = {
        '__builtins__': {},  # 移除所有默认内置函数
        **ALLOWED_BUILTINS  # 仅添加白名单内的内置函数
    }
    
    local_vars = {}
    
    try:
        # 1. 动态编译并执行代码字符串，定义函数
        exec(code_str, restricted_globals, local_vars)
        
        # 2. 从局部变量中获取生成的函数（假设函数名为 'dynamic_skill' 或通过解析获取）
        # 这里为了简化，我们约定生成的函数名为 'dynamic_skill'
        # 在实际应用中，可以通过 ast 解析 code_str 获取函数名
        func_name = [k for k in local_vars.keys() if callable(local_vars[k])][0]
        skill_func = local_vars[func_name]
        
        # 3. 准备参数
        args = inputs.get('args', [])
        kwargs = inputs.get('kwargs', {})
        
        # 4. 执行函数
        output = skill_func(*args, **kwargs)
        
        # 5. 将结果放入队列
        result_queue.put({'status': 'success', 'data': output})
        
    except Exception as e:
        # 捕获执行过程中的任何异常
        error_msg = f"Sandbox Execution Error: {str(e)}\n{traceback.format_exc()}"
        result_queue.put({'status': 'error', 'message': error_msg})


class SkillSandbox:
    """
    最小可执行单元（MEU）沙箱管理器。
    负责代码生成、进程隔离执行及结果回收。
    """
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        初始化沙箱。
        
        参数:
            timeout: 单个技能执行的最大允许时间（秒）。
        """
        self.timeout = timeout

    def execute_skill(
        self, 
        skill_logic: str, 
        input_args: List[Any], 
        input_kwargs: Dict[str, Any],
        input_schema: Optional[Dict[str, type]] = None
    ) -> Any:
        """
        执行封装后的技能。
        
        参数:
            skill_logic: 技能的逻辑代码字符串（例如："cost * 1.5"）。
            input_args: 位置参数列表。
            input_kwargs: 关键字参数字典。
            input_schema: 输入参数的验证Schema（可选）。
            
        返回:
            Any: 技能执行的结果。
            
        异常:
            SkillExecutionError: 如果执行超时、验证失败或发生运行时错误。
        """
        # 1. 输入验证
        if input_schema:
            # 合并 args 和 kwargs 进行验证（简化处理，仅验证 kwargs）
            if not validate_io_schema(input_kwargs, input_schema):
                raise SkillExecutionError("Input validation failed.")
        
        # 2. 生成可执行代码
        # 提取参数名
        param_names = list(input_kwargs.keys())
        code_str = generate_meu_code("dynamic_skill", skill_logic, param_names)
        
        logger.info(f"Generated Code:\n{code_str}")
        
        # 3. 准备进程间通信
        result_queue = multiprocessing.Queue()
        
        # 4. 启动隔离进程
        process = multiprocessing.Process(
            target=_run_isolated_process,
            args=(code_str, {'args': input_args, 'kwargs': input_kwargs}, result_queue)
        )
        
        process.start()
        process.join(timeout=self.timeout)
        
        # 5. 处理结果
        if process.is_alive():
            process.terminate()
            process.join()
            raise SkillExecutionError(f"Skill execution timed out after {self.timeout} seconds")
        
        if not result_queue.empty():
            result = result_queue.get()
            if result['status'] == 'success':
                return result['data']
            else:
                raise SkillExecutionError(f"Skill runtime error: {result['message']}")
        else:
            raise SkillExecutionError("Skill execution failed with no return message (possible crash)")


# 使用示例
if __name__ == "__main__":
    # 示例场景：封装一个“摆摊定价”技巧
    # 技能逻辑：成本加价50%，并根据数量给予折扣
    pricing_logic = """
    base_price = cost * 1.5
    if quantity > 10:
        final_price = base_price * 0.9
    else:
        final_price = base_price
    return {'unit_price': round(final_price, 2), 'total': round(final_price * quantity, 2)}
    """
    
    sandbox = SkillSandbox(timeout=3)
    
    try:
        # 定义输入验证规则
        schema = {
            'cost': (int, float),
            'quantity': int
        }
        
        # 执行技能
        result = sandbox.execute_skill(
            skill_logic=pricing_logic,
            input_args=[],
            input_kwargs={'cost': 100, 'quantity': 12},
            input_schema=schema
        )
        
        logger.info(f"Execution Result: {result}")
        
    except SkillExecutionError as e:
        logger.error(f"Failed to execute skill: {e}")