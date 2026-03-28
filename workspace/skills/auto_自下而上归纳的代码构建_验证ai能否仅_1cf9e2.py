"""
Module: auto_自下而上归纳的代码构建_验证ai能否仅_1cf9e2
Domain: machine_learning

Description:
    该模块实现了一个自下而上的程序归纳系统。它通过观察一组输入/输出（I/O）对，
    在没有自然语言描述的情况下，尝试反向推导底层的数学算法（主要针对多项式关系），
    并将其动态生成为一个可复用的Python函数节点。这模拟了人类通过观察数据总结规律
    并将其固化为技能的过程。

Features:
    - 自动验证输入数据的完整性和有效性。
    - 基于多项式回归的算法归纳引擎。
    - 动态代码生成与函数节点固化。
    - 详细的日志记录与错误处理。
"""

import logging
import sys
from typing import List, Tuple, Callable, Optional, Union
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InductionError(Exception):
    """自定义异常，用于在算法归纳失败时抛出。"""
    pass


def validate_io_pairs(io_pairs: List[Tuple[Union[int, float], Union[int, float]]]) -> List[Tuple[float, float]]:
    """
    辅助函数：验证输入/输出对的数据格式和有效性。

    Args:
        io_pairs: 包含 (输入, 输出) 元组的列表。

    Returns:
        转换为 float 类型的清洗后的 I/O 对列表。

    Raises:
        ValueError: 如果数据为空、格式不正确或包含非数值类型。
    """
    if not io_pairs:
        logger.error("输入数据为空。")
        raise ValueError("I/O pairs list cannot be empty.")

    cleaned_pairs = []
    for i, pair in enumerate(io_pairs):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            logger.error(f"第 {i} 个元素不是有效的元组: {pair}")
            raise ValueError(f"Element at index {i} is not a valid tuple.")

        x, y = pair
        try:
            x_val = float(x)
            y_val = float(y)
        except (TypeError, ValueError) as e:
            logger.error(f"第 {i} 个元素包含非数值数据: {pair}")
            raise ValueError(f"Non-numeric data found at index {i}.") from e

        cleaned_pairs.append((x_val, y_val))

    logger.info(f"成功验证 {len(cleaned_pairs)} 组 I/O 对。")
    return cleaned_pairs


def induce_algorithm(io_pairs: List[Tuple[float, float]], max_degree: int = 5, tolerance: float = 1e-6) -> np.poly1d:
    """
    核心函数 1：通过观察 I/O 对归纳底层算法。

    该函数尝试将数据拟合为多项式函数。它从低阶（线性）开始尝试，
    逐步增加复杂度，直到找到符合误差容忍度的最简单模型（奥卡姆剃刀原则）。

    Args:
        io_pairs: 经过验证的 (输入, 输出) 列表。
        max_degree: 尝试拟合的最高多项式阶数。
        tolerance: 拟合误差的容忍阈值（均方误差 MSE）。

    Returns:
        np.poly1d: 拟合得到的多项式模型对象。

    Raises:
        InductionError: 如果在 max_degree 范围内无法找到符合误差要求的模型。
    """
    x_values = np.array([p[0] for p in io_pairs])
    y_values = np.array([p[1] for p in io_pairs])

    logger.info("开始自下而上归纳算法...")

    for degree in range(1, max_degree + 1):
        try:
            # 使用最小二乘法拟合多项式
            coefficients = np.polyfit(x_values, y_values, degree)
            model = np.poly1d(coefficients)
            
            # 计算拟合误差 (MSE)
            predictions = model(x_values)
            mse = np.mean((predictions - y_values) ** 2)
            
            logger.debug(f"尝试阶数 {degree}: MSE = {mse:.6f}")

            if mse < tolerance:
                logger.info(f"成功归纳算法: 阶数={degree}, MSE={mse:.6f}")
                return model
        except np.linalg.LinAlgError:
            logger.warning(f"阶数 {degree} 拟合失败（可能是奇异矩阵），跳过。")
            continue

    logger.error(f"无法在阶数 {max_degree} 内归纳出符合误差要求的算法。")
    raise InductionError("Failed to induce a valid algorithm within the specified degree limit.")


def solidify_function_node(model: np.poly1d) -> Callable[[float], float]:
    """
    核心函数 2：将归纳出的数学模型固化为可复用的Python函数节点。

    该函数提取模型参数，动态生成Python代码字符串，并编译为可调用对象。
    这模拟了将“隐性知识”转化为“显性代码”的过程。

    Args:
        model: 归纳得到的多项式模型。

    Returns:
        Callable[[float], float]: 生成的Python函数，接收输入并返回预测输出。
    """
    # 获取多项式系数
    coeffs = model.coefficients.tolist()
    degree = len(coeffs) - 1
    
    # 构建函数体的字符串表达式
    # 例如: 2x^2 + 3x + 1 -> "return 2.0 * x**2 + 3.0 * x**1 + 1.0"
    expr_parts = []
    for power, coeff in enumerate(reversed(coeffs)):
        if power == 0:
            expr_parts.append(f"{coeff}")
        else:
            expr_parts.append(f"{coeff} * x**{power}")
    
    expression_str = " + ".join(expr_parts)
    
    # 动态生成函数代码
    func_code = f"""
def induced_function(x):
    \"\"\"Auto-generated function from I/O induction.\"\"\"
    return {expression_str}
"""
    
    logger.info(f"生成函数代码: {expression_str}")
    
    # 在局部作用域中执行代码以获取函数对象
    local_scope = {}
    try:
        exec(func_code, {}, local_scope)
    except Exception as e:
        logger.error("动态代码生成失败。")
        raise RuntimeError("Failed to generate function node.") from e
        
    return local_scope['induced_function']


def main():
    """
    使用示例：
    演示如何通过观察一组数据，让系统自动发现 y = x^2 + 2x + 1 的规律。
    """
    # 1. 准备观察数据 (I/O 对)
    # 假设底层规律是 y = x^2 + 2x + 1
    raw_data = [
        (0, 1),
        (1, 4),
        (2, 9),
        (3, 16),
        (4, 25),
        (5, 36),
        (-1, 0)
    ]
    
    print("-" * 60)
    print("【自下而上归纳构建系统】启动")
    print("-" * 60)

    try:
        # 2. 数据验证
        valid_data = validate_io_pairs(raw_data)
        
        # 3. 归纳算法
        model = induce_algorithm(valid_data, max_degree=3)
        
        # 4. 固化为函数节点
        skill_function = solidify_function_node(model)
        
        # 5. 验证生成的函数
        test_input = 10
        predicted_output = skill_function(test_input)
        expected_output = test_input**2 + 2*test_input + 1
        
        print(f"\n验证结果:")
        print(f"输入: {test_input}")
        print(f"生成函数预测: {predicted_output}")
        print(f"理论真实值: {expected_output}")
        print(f"验证状态: {'通过' if abs(predicted_output - expected_output) < 1e-5 else '失败'}")
        
        # 打印生成的函数源码信息
        print(f"\n生成的函数对象: {skill_function}")
        print(f"函数文档: {skill_function.__doc__}")

    except (ValueError, InductionError, RuntimeError) as e:
        logger.critical(f"系统运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()