"""
Module: auto_cognitive_consistency_sandbox.py
Description: 针对'认知自洽'，为知识节点自动生成验证沙箱与测试用例的系统。
             旨在解决如何为'真实节点'（如Python爬虫技能）自动生成最小I/O数据集，
             以便定期运行体检，剔除过时或错误的'僵尸节点'。

Author: Senior Python Engineer (AGI System Component)
Date: 2023-10-27
Version: 1.0.0
"""

import json
import logging
import re
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from functools import wraps

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义异常类型
class NodeValidationError(Exception):
    """自定义异常：节点验证失败"""
    pass

class SandboxGenerationError(Exception):
    """自定义异常：沙箱环境生成失败"""
    pass

@dataclass
class KnowledgeNode:
    """
    知识节点的数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        description (str): 节点功能的文本描述。
        logic_body (Callable): 包含实际逻辑的可调用对象（如函数）。
        input_schema (Dict): 预期的输入数据结构定义。
        output_schema (Dict): 预期的输出数据结构定义。
        creation_time (float): 节点创建的时间戳。
    """
    node_id: str
    description: str
    logic_body: Callable
    input_schema: Dict[str, str]
    output_schema: Dict[str, str]
    creation_time: float = time.time()

@dataclass
class TestCase:
    """
    测试用例数据结构。
    
    Attributes:
        case_id (str): 测试用例ID。
        inputs (Dict): 输入参数。
        expected_outputs (Any): 预期的输出结果或校验规则。
        context (Dict): 测试上下文元数据。
    """
    case_id: str
    inputs: Dict[str, Any]
    expected_outputs: Any
    context: Dict[str, str]

def timeout_handler(func: Callable, timeout: int = 5) -> Any:
    """
    辅助函数：简易的执行超时控制（注意：这只是一个模拟，实际生产环境建议使用 multiprocessing/signals）。
    
    Args:
        func (Callable): 要执行的函数。
        timeout (int): 超时时间（秒）。
        
    Returns:
        Any: 函数执行结果。
        
    Raises:
        TimeoutError: 如果执行超时。
    """
    start_time = time.time()
    # 这里仅作演示，实际阻塞函数无法在纯单线程中通过时间检查中断
    # 在真实AGI系统中，应使用多进程或多线程实现真正的超时中断
    result = func()
    end_time = time.time()
    if end_time - start_time > timeout:
        raise TimeoutError(f"Execution timed out after {timeout} seconds.")
    return result

def generate_hash_id(data: Any) -> str:
    """
    辅助函数：根据数据生成唯一哈希ID。
    
    Args:
        data (Any): 任意可序列化的数据。
        
    Returns:
        str: 哈希字符串。
    """
    data_str = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.md5(data_str).hexdigest()[:8]

def generate_sandbox_test_cases(node: KnowledgeNode) -> List[TestCase]:
    """
    核心函数 1: 为给定的知识节点自动生成最小化的测试用例集。
    
    该函数尝试解析节点的输入输出模式，生成边界值和典型值作为输入，
    并建立预期输出的校验逻辑。
    
    Args:
        node (KnowledgeNode): 待验证的知识节点对象。
        
    Returns:
        List[TestCase]: 生成的测试用例列表。
        
    Raises:
        SandboxGenerationError: 如果无法解析模式或生成数据失败。
    """
    logger.info(f"Generating sandbox test cases for Node ID: {node.node_id}")
    test_cases = []
    
    try:
        # 这里模拟一个简单的策略：根据输入类型生成数据
        # 真实场景下，这里可能会接入LLM来生成更智能的测试数据
        mock_inputs = {}
        
        for key, type_hint in node.input_schema.items():
            if 'int' in type_hint:
                # 生成边界值：0, 1, -1
                mock_inputs[key] = [0, 1, -1]
            elif 'str' in type_hint:
                # 生成空字符串和普通字符串
                mock_inputs[key] = ["", "test_string"]
            elif 'list' in type_hint:
                mock_inputs[key] = [[], ["item"]]
            else:
                mock_inputs[key] = [None]
        
        # 为了演示，我们只取第一组组合生成一个测试用例
        # 实际应该使用笛卡尔积生成多组用例
        inputs_sample = {k: v[1] for k, v in mock_inputs.items()} # 取非空值
        
        case_id = generate_hash_id(inputs_sample)
        
        # 构建预期输出的校验规则（而不是硬编码输出值）
        validation_rules = {
            "type_check": node.output_schema,
            "not_null": True
        }
        
        case = TestCase(
            case_id=f"tc_{node.node_id}_{case_id}",
            inputs=inputs_sample,
            expected_outputs=validation_rules,
            context={"generated_by": "auto_sandbox_v1"}
        )
        test_cases.append(case)
        
        logger.debug(f"Generated test case: {case.case_id}")
        return test_cases
        
    except Exception as e:
        logger.error(f"Failed to generate sandbox for {node.node_id}: {str(e)}")
        raise SandboxGenerationError(f"Sandbox generation failed: {str(e)}")

def validate_node_consistency(node: KnowledgeNode, test_cases: List[TestCase]) -> Tuple[bool, Dict[str, Any]]:
    """
    核心函数 2: 在沙箱中运行测试用例，验证节点的认知自洽性。
    
    执行逻辑：
    1. 遍历所有测试用例。
    2. 在隔离环境（此处简化为try-except块）中运行节点逻辑。
    3. 比对实际输出与预期输出规则。
    4. 记录通过率，判断节点是否为'僵尸节点'。
    
    Args:
        node (KnowledgeNode): 待验证的节点。
        test_cases (List[TestCase]): 用于验证的测试用例列表。
        
    Returns:
        Tuple[bool, Dict[str, Any]]: 
            - bool: 总体是否通过验证。
            - Dict: 详细的验证报告。
    """
    logger.info(f"Starting consistency validation for Node: {node.node_id}")
    report = {
        "node_id": node.node_id,
        "total_cases": len(test_cases),
        "passed": 0,
        "failed": 0,
        "errors": [],
        "is_zombie": False
    }
    
    for case in test_cases:
        try:
            # 模拟沙箱执行
            logger.debug(f"Executing case {case.case_id} with inputs: {case.inputs}")
            
            # 实际调用节点逻辑
            actual_output = node.logic_body(**case.inputs)
            
            # 验证输出 (简化版：检查类型和非空)
            rules = case.expected_outputs
            is_valid = True
            
            if rules.get("not_null") and actual_output is None:
                is_valid = False
                raise NodeValidationError("Output is null but expected non-null")
            
            # 简单的类型检查模拟
            expected_type = list(rules.get("type_check").values())[0]
            # 实际需更严格的类型推断，这里仅做演示
            if expected_type not in str(type(actual_output)):
                 logger.warning(f"Type mismatch: expected {expected_type}, got {type(actual_output)}")
                 # 这里不强制失败，仅警告，视具体业务逻辑而定
            
            if is_valid:
                report["passed"] += 1
                
        except Exception as e:
            report["failed"] += 1
            error_info = {
                "case_id": case.case_id,
                "error_type": type(e).__name__,
                "message": str(e)
            }
            report["errors"].append(error_info)
            logger.warning(f"Case {case.case_id} failed: {str(e)}")
    
    # 判定逻辑：如果失败率超过阈值，标记为僵尸节点
    if report["total_cases"] > 0:
        fail_rate = report["failed"] / report["total_cases"]
        if fail_rate > 0.5:  # 阈值设定为 50%
            report["is_zombie"] = True
            logger.warning(f"Node {node.node_id} marked as ZOMBIE NODE due to high failure rate.")
    
    is_success = report["failed"] == 0
    logger.info(f"Validation finished. Success: {is_success}")
    return is_success, report

# ================= 使用示例 =================

if __name__ == "__main__":
    # 1. 定义一个模拟的'真实节点' (例如：一个简单的加法器或爬虫逻辑)
    def mock_spider_logic(url: str, depth: int) -> Dict[str, Any]:
        """模拟一个Python爬虫节点的逻辑"""
        if not url:
            raise ValueError("URL cannot be empty")
        if depth < 0:
            raise ValueError("Depth cannot be negative")
            
        # 模拟处理逻辑
        return {
            "title": f"Title of {url}",
            "links_found": depth * 2,
            "status": "success"
        }

    # 2. 构建知识节点对象
    node_metadata = {
        "node_id": "spider_001",
        "description": "Basic web scraper logic",
        "logic_body": mock_spider_logic,
        "input_schema": {
            "url": "str",
            "depth": "int"
        },
        "output_schema": {
            "result": "dict"
        }
    }
    
    crawler_node = KnowledgeNode(**node_metadata)

    try:
        # 3. 自动生成测试用例
        print("--- Generating Test Cases ---")
        test_suites = generate_sandbox_test_cases(crawler_node)
        print(f"Generated {len(test_suites)} test cases.")
        
        # 4. 执行一致性验证
        print("\n--- Validating Node Consistency ---")
        success, validation_report = validate_node_consistency(crawler_node, test_suites)
        
        # 5. 输出报告
        print("\n--- Validation Report ---")
        print(json.dumps(validation_report, indent=2))
        
        # 演示处理僵尸节点的情况
        print("\n--- Testing Failure Scenario (Bad Logic) ---")
        def bad_logic(url: str, depth: int):
            raise RuntimeError("I am a broken node (zombie)")
        
        zombie_node = KnowledgeNode(
            node_id="bad_node_002", 
            description="Broken", 
            logic_body=bad_logic, 
            input_schema={"url": "str", "depth": "int"}, 
            output_schema={"res": "dict"}
        )
        # 复用之前的测试用例逻辑
        # 注意：这里需要重新生成适合该节点的case，但为了演示错误处理，我们强行复用或简单生成
        z_test_cases = generate_sandbox_test_cases(zombie_node)
        _, z_report = validate_node_consistency(zombie_node, z_test_cases)
        print(f"Zombie node detected: {z_report['is_zombie']}")
        
    except Exception as main_e:
        logger.error(f"System Error: {main_e}")