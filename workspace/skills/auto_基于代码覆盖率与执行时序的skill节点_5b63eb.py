"""
模块名称: auto_robustness_evaluator
描述: 基于代码覆盖率与执行时序的Skill节点鲁棒性评估框架。
      本模块实现了一套自动化测试流程，通过注入边界值和异常参数，
      监控目标Skill节点的执行成功率、资源消耗及输出稳定性，
      最终生成标准化的'鲁棒性评分'。
"""

import time
import json
import logging
import random
import tracemalloc
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 异常类定义
class SkillExecutionError(Exception):
    """自定义Skill执行异常"""
    pass

class DataValidationError(Exception):
    """数据验证异常"""
    pass

# 数据结构定义
@dataclass
class RobustnessMetrics:
    """存储单个Skill的鲁棒性指标"""
    skill_id: str
    success_rate: float          # 执行成功率 (0.0 - 1.0)
    avg_execution_time_ms: float # 平均执行时间 (毫秒)
    peak_memory_kb: float        # 峰值内存消耗 (KB)
    output_stability_score: float # 输出稳定性 (0.0 - 1.0)
    final_robustness_score: float # 最终综合评分 (0 - 100)

@dataclass
class TestCase:
    """测试用例结构"""
    inputs: Dict[str, Any]
    is_edge_case: bool
    description: str

def measure_performance(func: Callable) -> Callable:
    """
    辅助函数: 装饰器，用于测量函数的执行时间和内存峰值。
    返回扩充后的结果字典，包含原始结果、时间和内存数据。
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        # 启动内存追踪
        tracemalloc.start()
        start_time = time.perf_counter()
        
        result = None
        status = "success"
        error_msg = ""
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            status = "fail"
            error_msg = str(e)
            logger.error(f"Error in {func.__name__}: {e}")
        
        end_time = time.perf_counter()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "result": result,
            "status": status,
            "error": error_msg,
            "execution_time_ms": (end_time - start_time) * 1000,
            "peak_memory_kb": peak_memory / 1024
        }
    return wrapper

class RobustnessEvaluator:
    """
    核心评估类：负责生成测试向量、执行Skill节点、计算评分。
    """
    
    def __init__(self, target_skills: List[Dict[str, Any]]):
        """
        初始化评估器。
        
        Args:
            target_skills: 待评估的Skill节点列表，每个节点包含 'id' 和 'handler' (可调用对象)。
        """
        if not target_skills:
            raise ValueError("Target skills list cannot be empty.")
        
        self.skills = target_skills
        self.results: List[RobustnessMetrics] = []
        logger.info(f"Initialized evaluator with {len(self.skills)} skills.")

    def _generate_test_vectors(self, input_schema: Dict) -> List[TestCase]:
        """
        核心函数1: 生成测试向量。
        根据简单的输入模式生成正常值、边界值（空值、极值）和异常类型数据。
        
        Args:
            input_schema: 描述输入参数的字典 (简化版)。
        
        Returns:
            测试用例列表。
        """
        test_cases = []
        
        # 简单的边界/异常生成逻辑
        # 1. 正常随机值
        normal_inputs = {k: random.randint(0, 100) for k in input_schema.keys()}
        test_cases.append(TestCase(inputs=normal_inputs, is_edge_case=False, description="Normal input"))
        
        # 2. 边界值: 空值/None
        edge_inputs = {k: None for k in input_schema.keys()}
        test_cases.append(TestCase(inputs=edge_inputs, is_edge_case=True, description="Null inputs"))
        
        # 3. 边界值: 极端数值
        extreme_inputs = {k: 1e9 for k in input_schema.keys()}
        test_cases.append(TestCase(inputs=extreme_inputs, is_edge_case=True, description="Extreme large numbers"))
        
        # 4. 异常类型
        type_error_inputs = {k: "invalid_string" for k in input_schema.keys()}
        test_cases.append(TestCase(inputs=type_error_inputs, is_edge_case=True, description="Type mismatch"))
        
        return test_cases

    def _calculate_stability(self, outputs: List[Any]) -> float:
        """
        辅助函数: 计算输出稳定性。
        检查输出结构的一致性。如果所有输出结构相同，得分为1.0，
        如果出现异常或结构剧烈变化，分数降低。
        """
        if not outputs:
            return 0.0
        
        # 简单检查：比较返回值的类型一致性
        first_type = type(outputs[0])
        consistent_count = sum(1 for out in outputs if isinstance(out, first_type))
        
        return consistent_count / len(outputs)

    def evaluate_single_skill(self, skill_handler: Callable, schema: Dict) -> Tuple[float, float, float, float]:
        """
        核心函数2: 执行单个Skill的鲁棒性测试。
        
        Args:
            skill_handler: Skill的可调用函数。
            schema: 输入参数模式。
            
        Returns:
            元组: (成功率, 平均时间, 峰值内存, 稳定性分数)
        """
        test_vectors = self._generate_test_vectors(schema)
        
        success_count = 0
        total_time = 0.0
        max_memory = 0.0
        outputs = []
        
        # 包装Handler以测量性能
        wrapped_handler = measure_performance(skill_handler)
        
        for case in test_vectors:
            # 执行测试
            metrics = wrapped_handler(case.inputs)
            
            total_time += metrics["execution_time_ms"]
            max_memory = max(max_memory, metrics["peak_memory_kb"])
            
            if metrics["status"] == "success":
                success_count += 1
                outputs.append(metrics["result"])
            else:
                outputs.append(None) # 失败视为输出不稳定因素
            
            # 边界检查：防止内存泄漏 (设置阈值 100MB)
            if max_memory > 100 * 1024:
                logger.warning("Memory threshold exceeded during test.")

        success_rate = success_count / len(test_vectors)
        avg_time = total_time / len(test_vectors)
        stability = self._calculate_stability(outputs)
        
        return success_rate, avg_time, max_memory, stability

    def run_evaluation(self) -> List[RobustnessMetrics]:
        """
        运行所有Skill的评估流程。
        
        Returns:
            包含所有Skill鲁棒性指标的结果列表。
        """
        logger.info("Starting full robustness evaluation...")
        
        for skill in self.skills:
            try:
                sid = skill.get('id', 'unknown')
                handler = skill.get('handler')
                schema = skill.get('input_schema', {'data': 'int'}) # 默认schema
                
                if not callable(handler):
                    raise DataValidationError(f"Skill {sid} handler is not callable.")

                logger.info(f"Evaluating Skill: {sid}")
                
                # 执行核心评估
                s_rate, a_time, p_mem, s_score = self.evaluate_single_skill(handler, schema)
                
                # 计算最终鲁棒性评分 (加权算法)
                # 公式: 40%成功率 + 20%稳定性 + 20%性能 + 20%内存
                # 性能和内存进行归一化反向处理 (假设阈值: 200ms, 10MB)
                perf_score = max(0, 100 - (a_time / 2)) # 200ms扣完
                mem_score = max(0, 100 - (p_mem / 10240)) # 10MB扣完
                
                final_score = (
                    (s_rate * 40) + 
                    (s_score * 20) + 
                    (perf_score * 0.2) + 
                    (mem_score * 0.2)
                )
                
                metric = RobustnessMetrics(
                    skill_id=sid,
                    success_rate=s_rate,
                    avg_execution_time_ms=a_time,
                    peak_memory_kb=p_mem,
                    output_stability_score=s_score,
                    final_robustness_score=round(final_score, 2)
                )
                
                self.results.append(metric)
                
            except Exception as e:
                logger.error(f"Failed to evaluate skill {skill.get('id')}: {e}")
                continue
                
        return self.results

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟一个简单的Skill节点
    def mock_skill_handler(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """模拟的Skill处理函数"""
        # 模拟处理逻辑
        time.sleep(0.01) # 模拟耗时
        
        # 模拟针对异常输入的处理
        if inputs.get("data") is None:
            raise ValueError("Input cannot be None")
        if isinstance(inputs.get("data"), str):
            return {"status": "handled_error", "message": "Invalid type"}
            
        # 正常逻辑
        val = inputs.get("data", 0)
        return {"result": val * 2, "status": "ok"}

    # 准备模拟数据
    skills_to_test = [
        {
            "id": "skill_001_process_data",
            "handler": mock_skill_handler,
            "input_schema": {"data": "int"}
        },
        {
            "id": "skill_002_unstable",
            "handler": lambda x: None, # 一个简单的总是返回None的Skill
            "input_schema": {"param": "str"}
        }
    ]

    # 实例化并运行评估器
    try:
        evaluator = RobustnessEvaluator(skills_to_test)
        final_results = evaluator.run_evaluation()
        
        print("\n--- Evaluation Report ---")
        for res in final_results:
            print(json.dumps(res.__dict__, indent=2))
            
    except Exception as e:
        print(f"Critical Error: {e}")