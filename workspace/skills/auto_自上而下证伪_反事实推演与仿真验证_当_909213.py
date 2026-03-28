"""
SKILL: auto_自上而下证伪_反事实推演与仿真验证_当_909213
Description: 【自上而下证伪】反事实推演与仿真验证：当AI生成一个新的工艺优化方案时，
             如何在虚拟仿真环境中进行“压力测试”以证伪其有效性？
             即寻找导致该方案失败的边界条件。
Domain: digital_twin
"""

import logging
import random
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FalsificationEngine_909213")

class ProcessStatus(Enum):
    """工艺状态枚举"""
    SUCCESS = "success"
    FAILURE = "failure"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"

@dataclass
class ProcessParameter:
    """工艺参数定义"""
    name: str
    current_value: float
    min_limit: float
    max_limit: float
    unit: str
    tolerance: float = 0.05  # 默认5%的容差

    def is_within_limits(self, value: float) -> bool:
        """检查值是否在允许范围内"""
        return self.min_limit <= value <= self.max_limit

@dataclass
class OptimizationScheme:
    """AI生成的优化方案"""
    scheme_id: str
    parameters: Dict[str, float]  # 参数名: 设定值
    expected_improvement: float   # 预期提升百分比
    description: str

@dataclass
class SimulationResult:
    """仿真结果数据结构"""
    is_successful: bool
    metric_output: float
    error_code: Optional[str] = None
    message: str = ""

@dataclass
class FalsificationReport:
    """证伪报告"""
    original_scheme: OptimizationScheme
    is_falsified: bool
    failure_conditions: List[Dict[str, Any]]
    robustness_score: float  # 0.0 (脆弱) to 1.0 (鲁棒)
    simulation_steps: int
    details: str

class VirtualSimulator:
    """
    虚拟仿真环境模拟器 (Mock Class)
    模拟数字孪生环境中的物理反馈
    """
    
    def run_simulation(self, params: Dict[str, float]) -> SimulationResult:
        """
        根据输入参数运行单次仿真
        """
        # 模拟物理规则：这里假设是一个简单的化学反应釜
        # 关键参数: temperature, pressure, concentration
        
        temp = params.get('temperature', 300)
        pressure = params.get('pressure', 1.0)
        concentration = params.get('concentration', 0.5)
        
        # 模拟失败条件 1: 热失控
        if temp > 450 and pressure > 2.0:
            return SimulationResult(False, 0.0, "ERR_OVERHEAT", "Critical Failure: Thermal Runaway detected.")
            
        # 模拟失败条件 2: 产量低
        if concentration < 0.2 or temp < 280:
            return SimulationResult(False, 0.0, "LOW_YIELD", "Process inefficient.")
            
        # 模拟不稳定区域
        if temp > 420 and (pressure > 1.8 or pressure < 0.5):
            return SimulationResult(False, 0.0, "UNSTABLE", "Oscillation detected in control loop.")
            
        # 模拟成功情况下的产出
        # 简单的非线性模型
        base_output = 100.0
        efficiency = (temp / 350) * pressure * concentration
        noise = random.uniform(-0.05, 0.05)
        
        return SimulationResult(True, base_output * efficiency * (1 + noise))


def validate_scheme_parameters(
    scheme: OptimizationScheme, 
    param_limits: Dict[str, Tuple[float, float]]
) -> bool:
    """
    辅助函数：验证方案参数是否在物理可行域内（基础检查）
    
    Args:
        scheme: 优化方案对象
        param_limits: 参数的物理限制字典 {name: (min, max)}
        
    Returns:
        bool: 参数是否有效
        
    Raises:
        ValueError: 如果参数缺失
    """
    logger.info(f"Validating scheme: {scheme.scheme_id}")
    for param_name, value in scheme.parameters.items():
        if param_name not in param_limits:
            logger.warning(f"Unknown parameter encountered: {param_name}")
            continue
            
        min_val, max_val = param_limits[param_name]
        if not (min_val <= value <= max_val):
            logger.error(f"Parameter {param_name} value {value} out of bounds [{min_val}, {max_val}]")
            return False
            
    return True

def generate_counterfactuals(
    base_params: Dict[str, float], 
    limits: Dict[str, Tuple[float, float]], 
    num_samples: int = 10,
    perturbation_intensity: float = 0.1
) -> List[Dict[str, float]]:
    """
    核心函数 1: 生成反事实/对抗性样本
    在基础参数周围生成扰动，或探索边界值。
    
    Args:
        base_params: 原始优化参数
        limits: 参数边界
        num_samples: 生成样本数量
        perturbation_intensity: 扰动强度因子
        
    Returns:
        List of parameter dictionaries
    """
    counterfactuals = []
    param_names = list(base_params.keys())
    
    for _ in range(num_samples):
        new_params = {}
        for name in param_names:
            val = base_params[name]
            min_v, max_v = limits[name]
            range_v = max_v - min_v
            
            # 随机选择扰动策略：高斯扰动 或 边界探索
            strategy = random.choice(['gaussian', 'boundary'])
            
            if strategy == 'gaussian':
                # 添加高斯噪声
                noise = random.gauss(0, range_v * perturbation_intensity)
                new_val = val + noise
            else:
                # 探索边界（极值）
                new_val = random.choice([min_v, max_v, val * 1.1, val * 0.9])
            
            # 截断到合法范围
            new_params[name] = max(min_v, min(max_v, new_val))
            
        counterfactuals.append(new_params)
        
    return counterfactuals

def execute_falsification_process(
    scheme: OptimizationScheme,
    simulator: VirtualSimulator,
    param_limits: Dict[str, Tuple[float, float]],
    max_iterations: int = 50
) -> FalsificationReport:
    """
    核心函数 2: 执行自上而下的证伪过程
    
    通过迭代式的反事实推演，尝试找到导致方案失效的边界条件。
    
    Args:
        scheme: 待测试的优化方案
        simulator: 虚拟仿真环境实例
        param_limits: 参数物理限制
        max_iterations: 最大证伪尝试次数
        
    Returns:
        FalsificationReport: 包含证伪结果的详细报告
    """
    logger.info(f"Starting falsification for scheme: {scheme.scheme_id}")
    
    # 1. 基础验证
    if not validate_scheme_parameters(scheme, param_limits):
        return FalsificationReport(
            original_scheme=scheme,
            is_falsified=True,
            failure_conditions=[{"error": "Invalid base parameters"}],
            robustness_score=0.0,
            simulation_steps=0,
            details="Base scheme parameters violate physical limits."
        )

    # 2. 运行基准测试
    base_result = simulator.run_simulation(scheme.parameters)
    if not base_result.is_successful:
        return FalsificationReport(
            original_scheme=scheme,
            is_falsified=True,
            failure_conditions=[asdict(base_result)],
            robustness_score=0.0,
            simulation_steps=1,
            details="Base scheme failed immediately in simulation."
        )

    # 3. 压力测试循环
    failure_conditions = []
    successful_tests = 0
    total_tests = 0
    
    # 自适应扰动强度
    intensity = 0.05
    
    for i in range(max_iterations):
        total_tests += 1
        
        # 动态调整扰动强度，尝试触发失败
        # 如果一直成功，增加扰动；如果频繁失败，减少扰动以寻找边界
        intensity = min(0.5, intensity * 1.05) 
        
        # 生成反事实测试用例
        test_cases = generate_counterfactuals(
            scheme.parameters, 
            param_limits, 
            num_samples=5, 
            perturbation_intensity=intensity
        )
        
        found_failure_this_round = False
        
        for params in test_cases:
            result = simulator.run_simulation(params)
            
            if not result.is_successful:
                logger.warning(f"Falsification found! Condition: {params} -> {result.message}")
                failure_conditions.append({
                    "parameters": params,
                    "result": asdict(result)
                })
                found_failure_this_round = True
                # 稍微降低强度以精确定位边界
                intensity *= 0.8
                break 
            else:
                successful_tests += 1

    # 4. 生成报告
    robustness = successful_tests / total_tests if total_tests > 0 else 0.0
    
    # 如果我们找到了任何失败条件，则方案在该语境下被部分证伪
    is_falsified = len(failure_conditions) > 0
    
    report = FalsificationReport(
        original_scheme=scheme,
        is_falsified=is_falsified,
        failure_conditions=failure_conditions,
        robustness_score=robustness,
        simulation_steps=total_tests,
        details=f"Completed {total_tests} simulations. Found {len(failure_conditions)} failure modes."
    )
    
    logger.info(f"Falsification complete. Robustness: {robustness:.2f}")
    return report

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 定义参数边界
    LIMITS = {
        "temperature": (250.0, 500.0),  # 摄氏度
        "pressure": (0.1, 3.0),         # MPa
        "concentration": (0.1, 1.0)     # mol/L
    }

    # 2. AI生成的优化方案（看起来很美好，但可能对扰动敏感）
    ai_scheme = OptimizationScheme(
        scheme_id="OPT_9092_V1",
        parameters={
            "temperature": 440.0,  # 接近热失控边缘
            "pressure": 1.9,       # 高压
            "concentration": 0.8
        },
        expected_improvement=15.0,
        description="High-temp rapid synthesis"
    )

    # 3. 初始化仿真器
    sim_env = VirtualSimulator()

    # 4. 执行证伪
    report = execute_falsification_process(
        scheme=ai_scheme,
        simulator=sim_env,
        param_limits=LIMITS,
        max_iterations=20
    )

    # 5. 打印结果
    print("\n" + "="*30)
    print(f" REPORT FOR {report.original_scheme.scheme_id} ")
    print("="*30)
    print(f"Is Falsified: {report.is_falsified}")
    print(f"Robustness Score: {report.robustness_score:.4f}")
    print(f"Failure Modes Found: {len(report.failure_conditions)}")
    
    if report.is_falsified:
        print("\nSample Failure Condition:")
        fail_case = report.failure_conditions[0]
        print(f"Params: {fail_case['parameters']}")
        print(f"Error: {fail_case['result']['message']}")