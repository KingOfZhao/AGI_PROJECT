"""
高级自动反例生成器

该模块实现了一个针对Python函数（逻辑单元）的自动化反例生成系统。
通过静态类型检查和启发式策略，自动构建边界测试用例（如空值、超大数值、
类型错误、深层嵌套结构等），试图触发目标函数的未处理异常。
"""

import inspect
import logging
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, get_type_hints

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoAdversarialGenerator")

class ValidationError(Exception):
    """自定义异常：用于数据验证失败时的错误处理"""
    pass

class TargetExecutionError(Exception):
    """自定义异常：用于捕获目标函数运行时的崩溃"""
    pass

def _validate_target_function(target_func: Callable) -> None:
    """
    辅助函数：验证目标函数是否可调用并具备类型注解。
    
    参数:
        target_func (Callable): 待测试的目标函数
        
    异常:
        ValidationError: 如果目标函数无效或缺少必要的类型注解
    """
    if not callable(target_func):
        raise ValidationError("提供的输入不是一个可调用的函数。")
    
    # 检查是否有类型提示，这是生成高质量反例的关键
    hints = get_type_hints(target_func)
    if not hints:
        logger.warning(f"函数 {target_func.__name__} 缺少类型注解，将回退到通用启发式生成策略。")
    
    logger.info(f"目标函数 '{target_func.__name__}' 验证通过。")

def _generate_adversarial_value(target_type: Type) -> List[Any]:
    """
    核心函数：根据目标类型生成对抗性数值。
    
    参数:
        target_type (Type): 期望的参数类型（如 int, str, List 等）
        
    返回:
        List[Any]: 包含多个边界值的列表
    """
    adversarial_cases = []
    
    # 通用边界值（无论类型如何，尝试打破逻辑）
    adversarial_cases.extend([
        None,  # NoneType 攻击
        "",    # 空字符串（如果期望数值可能引发转换错误）
        " "    # 空白字符
    ])

    if target_type in (int, float):
        # 数值边界：极值、负数、零、特殊浮点数
        adversarial_cases.extend([
            0, -1, 1,
            sys.maxsize,  # 最大整数
            -sys.maxsize - 1,  # 最小整数
            float('inf'), float('-inf'), float('nan'),  # 特殊浮点
            1e308, -1e308  # 超大浮点
        ])
    elif target_type == str:
        # 字符串边界：超长串、特殊字符、代码注入尝试
        adversarial_cases.extend([
            "A" * 100000,  # 超长字符串（DoS攻击模拟）
            "𠮷",  # 多字节字符
            "'; DROP TABLE users; --",  # SQL注入模式
            "<script>alert('xss')</script>",  # XSS模式
            "\x00",  # 空字节
            "True", "False", "123"  # 布尔/数值的字面量伪装
        ])
    elif target_type in (list, List):
        # 列表边界：空列表、超长列表、混合类型列表
        adversarial_cases.extend([
            [],  # 空列表
            [None] * 1000,  # 大量None
            list(range(100000)),  # 大量整数
            [1, "string", None, b"bytes"],  # 非同构类型（针对排序函数等）
            [[[[[]]]]],  # 深层嵌套
            [float('nan'), float('inf')]  # 列表内包含特殊数值
        ])
    elif target_type == bool:
        # 布尔边界
        adversarial_cases.extend([True, False])
    
    return adversarial_cases

def generate_attack_matrix(func_signature: inspect.Signature) -> List[Dict[str, Any]]:
    """
    核心函数：解析函数签名并构建攻击矩阵。
    
    参数:
        func_signature (inspect.Signature): 目标函数的签名对象
        
    返回:
        List[Dict[str, Any]]: 参数字典列表，每个字典代表一次攻击的输入配置
    """
    attack_matrix = []
    hints = get_type_hints(func_signature)
    
    logger.info("正在构建攻击矩阵...")
    
    # 简化处理：针对每个参数生成独立的各种边界情况
    # 在实际AGI系统中，这里可能会使用笛卡尔积组合参数，但为了演示单参数攻击：
    for param_name, param in func_signature.parameters.items():
        param_type = hints.get(param_name, Any)
        
        # 生成该参数的对抗值
        attack_values = _generate_adversarial_value(param_type)
        
        for value in attack_values:
            attack_matrix.append({param_name: value})
            
    return attack_matrix

def execute_adversarial_attack(
    target_func: Callable, 
    max_execution_time: float = 2.0
) -> Dict[str, Any]:
    """
    主功能函数：对目标函数执行自动化对抗攻击测试。
    
    此函数会自动提取目标函数的参数类型，生成边界反例，
    并逐个执行以检测是否引发异常（崩溃）。
    
    参数:
        target_func (Callable): 待测试的Python函数。
        max_execution_time (float): 单个测试用例的超时时间（秒）。
        
    返回:
        Dict[str, Any]: 测试报告，包含总测试数、失败数、成功数及详细错误日志。
        
    示例:
        >>> def my_sort(data: list) -> list:
        ...     return sorted(data)
        >>> report = execute_adversarial_attack(my_sort)
        >>> print(f"测试完成，发现崩溃数: {report['crashes_found']}")
    """
    # 数据验证
    try:
        _validate_target_function(target_func)
    except ValidationError as e:
        logger.error(f"输入验证失败: {e}")
        return {"status": "error", "message": str(e)}

    sig = inspect.signature(target_func)
    attack_cases = generate_attack_matrix(sig)
    
    results = {
        "total_cases": len(attack_cases),
        "crashes_found": 0,
        "successful_runs": 0,
        "errors": []
    }

    logger.info(f"开始执行对抗性测试，共 {len(attack_cases)} 个用例...")

    for case in attack_cases:
        try:
            # 填充默认参数（如果有）
            bound_args = sig.bind_partial(**case)
            bound_args.apply_defaults()
            
            logger.debug(f"正在测试输入: {case}")
            
            # 简单的超时控制模拟（注意：在生产环境中应使用多进程/线程实现真正的超时）
            start_time = time.time()
            
            # 执行目标函数
            result = target_func(**bound_args.arguments)
            
            duration = time.time() - start_time
            
            # 检查结果是否合理（可选，此处仅检查是否崩溃）
            if duration > max_execution_time:
                raise TimeoutError(f"执行超时: {duration:.2f}s")
            
            results["successful_runs"] += 1
            
        except Exception as e:
            results["crashes_found"] += 1
            error_info = {
                "input": str(case),
                "exception_type": type(e).__name__,
                "message": str(e)
            }
            results["errors"].append(error_info)
            logger.warning(f"发现崩溃! 输入: {case} -> 异常: {type(e).__name__}")

    logger.info(f"测试完成。成功: {results['successful_runs']}, 崩溃: {results['crashes_found']}")
    return results

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例目标函数：一个简单的除法逻辑单元
    def calculate_ratio(numerator: int, denominator: int) -> float:
        """
        计算比率，简单的逻辑单元示例。
        """
        # 假设开发者忘记了处理 denominator=0 的情况
        return numerator / denominator

    print("--- 开始对抗性测试演示 ---")
    # 执行攻击
    test_report = execute_adversarial_attack(calculate_ratio)
    
    # 打印报告摘要
    print("\n测试报告摘要:")
    print(f"总用例: {test_report['total_cases']}")
    print(f"发现崩溃: {test_report['crashes_found']}")
    
    if test_report['crashes_found'] > 0:
        print("\n发现的错误详情:")
        for error in test_report['errors']:
            print(f"  输入: {error['input']}")
            print(f"  错误: {error['exception_type']} - {error['message']}")