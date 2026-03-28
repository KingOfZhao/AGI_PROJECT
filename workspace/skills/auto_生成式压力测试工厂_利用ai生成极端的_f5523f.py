"""
生成式压力测试工厂

该模块利用AI生成极端的环境参数组合（虚拟魔鬼代言人），在数字孪生环境中
对传统工艺流程进行'虚拟攻击'。通过生成前所未有的参数曲线来攻击工艺流程，
预测可能的变质点，从而在无需大量物理浪费的情况下，归纳出更优的工艺边界，
实现'零成本试错'。

示例:
    >>> from auto_generative_stress_test_factory import GenerativeStressTestFactory
    >>> factory = GenerativeStressTestFactory()
    >>> stress_scenarios = factory.generate_stress_scenarios(
    ...     base_params={'temperature': 25, 'humidity': 60},
    ...     num_scenarios=5,
    ...     intensity=0.8
    ... )
    >>> test_results = factory.run_virtual_attack(
    ...     process_model="traditional_brewing",
    ...     scenarios=stress_scenarios
    ... )
"""

import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class StressScenario:
    """压力测试场景数据结构"""
    scenario_id: str
    parameters: Dict[str, Union[float, int]]
    intensity: float
    generation_method: str
    timestamp: str


@dataclass
class TestResult:
    """测试结果数据结构"""
    scenario_id: str
    passed: bool
    failure_point: Optional[Dict[str, Any]]
    metrics: Dict[str, float]
    recommendations: List[str]


class GenerativeStressTestFactory:
    """生成式压力测试工厂类
    
    该类利用AI生成极端的环境参数组合，在数字孪生环境中对传统工艺流程进行
    虚拟攻击，以发现工艺边界和潜在风险点。
    
    属性:
        process_models (Dict[str, Any]): 存储工艺模型的数据结构
        stress_history (List[StressScenario]): 历史压力测试场景记录
    """
    
    def __init__(self) -> None:
        """初始化生成式压力测试工厂"""
        self.process_models = {}
        self.stress_history = []
        logger.info("Generative Stress Test Factory initialized")
    
    def generate_stress_scenarios(
        self,
        base_params: Dict[str, Union[float, int]],
        num_scenarios: int = 5,
        intensity: float = 0.8,
        generation_method: str = "random"
    ) -> List[StressScenario]:
        """生成压力测试场景
        
        根据基础参数和指定的强度生成多个压力测试场景。
        
        参数:
            base_params: 基础工艺参数字典，如温度、湿度等
            num_scenarios: 要生成的场景数量
            intensity: 压力强度(0.0-1.0)，越高表示生成的参数越极端
            generation_method: 生成方法，可选"random"或"gradient"
            
        返回:
            包含StressScenario对象的列表
            
        异常:
            ValueError: 如果输入参数无效
        """
        # 输入验证
        if not base_params:
            raise ValueError("Base parameters cannot be empty")
        if not 0 <= intensity <= 1:
            raise ValueError("Intensity must be between 0 and 1")
        if num_scenarios <= 0:
            raise ValueError("Number of scenarios must be positive")
        
        logger.info(f"Generating {num_scenarios} stress scenarios with intensity {intensity}")
        
        scenarios = []
        for i in range(num_scenarios):
            # 生成场景ID
            scenario_id = f"stress_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
            
            # 根据生成方法创建极端参数
            if generation_method == "random":
                stressed_params = self._generate_random_stress(base_params, intensity)
            elif generation_method == "gradient":
                stressed_params = self._generate_gradient_stress(base_params, intensity, i)
            else:
                raise ValueError(f"Unknown generation method: {generation_method}")
            
            # 创建场景对象
            scenario = StressScenario(
                scenario_id=scenario_id,
                parameters=stressed_params,
                intensity=intensity,
                generation_method=generation_method,
                timestamp=datetime.now().isoformat()
            )
            
            scenarios.append(scenario)
            self.stress_history.append(scenario)
        
        logger.info(f"Successfully generated {len(scenarios)} stress scenarios")
        return scenarios
    
    def run_virtual_attack(
        self,
        process_model: str,
        scenarios: List[StressScenario],
        safety_threshold: float = 0.9
    ) -> List[TestResult]:
        """运行虚拟攻击测试
        
        在数字孪生环境中运行生成的压力场景，测试工艺流程的鲁棒性。
        
        参数:
            process_model: 工艺模型名称
            scenarios: 要测试的压力场景列表
            safety_threshold: 安全阈值(0.0-1.0)
            
        返回:
            包含TestResult对象的列表
            
        异常:
            ValueError: 如果工艺模型不存在或场景为空
        """
        if not scenarios:
            raise ValueError("No scenarios provided for testing")
        
        # 检查工艺模型是否存在
        if process_model not in self.process_models:
            logger.warning(f"Process model {process_model} not found, creating default model")
            self.process_models[process_model] = self._create_default_process_model(process_model)
        
        model = self.process_models[process_model]
        results = []
        
        logger.info(f"Running virtual attack on {process_model} with {len(scenarios)} scenarios")
        
        for scenario in scenarios:
            try:
                # 模拟测试过程
                test_metrics = self._simulate_process(model, scenario.parameters)
                
                # 分析结果
                failure_point = None
                passed = True
                recommendations = []
                
                # 检查关键指标是否超过安全阈值
                for param, value in test_metrics.items():
                    if param in model['critical_params'] and value > safety_threshold:
                        passed = False
                        failure_point = {
                            'parameter': param,
                            'value': value,
                            'threshold': safety_threshold
                        }
                        recommendations.append(
                            f"Adjust {param} control to handle values above {value:.2f}"
                        )
                
                # 如果没有失败，添加优化建议
                if passed:
                    recommendations = self._generate_optimization_recommendations(
                        scenario.parameters, test_metrics
                    )
                
                # 创建测试结果
                result = TestResult(
                    scenario_id=scenario.scenario_id,
                    passed=passed,
                    failure_point=failure_point,
                    metrics=test_metrics,
                    recommendations=recommendations
                )
                
                results.append(result)
                logger.info(f"Test completed for scenario {scenario.scenario_id}: {'PASSED' if passed else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"Error testing scenario {scenario.scenario_id}: {str(e)}")
                continue
        
        return results
    
    def _generate_random_stress(
        self,
        base_params: Dict[str, Union[float, int]],
        intensity: float
    ) -> Dict[str, Union[float, int]]:
        """生成随机压力参数
        
        辅助函数，根据基础参数和强度生成随机压力参数。
        
        参数:
            base_params: 基础工艺参数
            intensity: 压力强度
            
        返回:
            包含压力参数的字典
        """
        stressed_params = {}
        for param, value in base_params.items():
            # 根据参数类型生成不同的压力值
            if isinstance(value, float):
                # 浮点数参数，添加随机波动
                variation = (random.random() - 0.5) * 2 * intensity * abs(value)
                stressed_value = value + variation
            elif isinstance(value, int):
                # 整数参数，添加整数波动
                variation = int((random.random() - 0.5) * 2 * intensity * abs(value))
                stressed_value = value + variation
            else:
                # 其他类型参数保持不变
                stressed_value = value
            
            stressed_params[param] = stressed_value
        
        return stressed_params
    
    def _generate_gradient_stress(
        self,
        base_params: Dict[str, Union[float, int]],
        intensity: float,
        gradient_step: int
    ) -> Dict[str, Union[float, int]]:
        """生成梯度压力参数
        
        辅助函数，根据基础参数、强度和梯度步数生成梯度压力参数。
        
        参数:
            base_params: 基础工艺参数
            intensity: 压力强度
            gradient_step: 梯度步数
            
        返回:
            包含压力参数的字典
        """
        stressed_params = {}
        step_factor = gradient_step * intensity / 10
        
        for param, value in base_params.items():
            if isinstance(value, (float, int)):
                # 按梯度方向增加压力
                direction = 1 if random.random() > 0.5 else -1
                variation = direction * step_factor * abs(value)
                stressed_value = value + variation
            else:
                stressed_value = value
            
            stressed_params[param] = stressed_value
        
        return stressed_params
    
    def _create_default_process_model(self, model_name: str) -> Dict[str, Any]:
        """创建默认工艺模型
        
        辅助函数，为指定的工艺名称创建默认模型。
        
        参数:
            model_name: 工艺模型名称
            
        返回:
            包含工艺模型定义的字典
        """
        # 这里可以根据不同的工艺名称返回不同的默认模型
        # 示例中使用简化的模型结构
        default_model = {
            'name': model_name,
            'critical_params': {
                'temperature': {'min': 10, 'max': 40},
                'humidity': {'min': 30, 'max': 90},
                'pressure': {'min': 0.9, 'max': 1.1}
            },
            'optimal_ranges': {
                'temperature': {'min': 20, 'max': 30},
                'humidity': {'min': 50, 'max': 70}
            },
            'response_time': 60  # 响应时间(秒)
        }
        
        return default_model
    
    def _simulate_process(
        self,
        model: Dict[str, Any],
        parameters: Dict[str, Union[float, int]]
    ) -> Dict[str, float]:
        """模拟工艺过程
        
        辅助函数，模拟给定参数下的工艺过程。
        
        参数:
            model: 工艺模型
            parameters: 输入参数
            
        返回:
            包含模拟结果的字典
        """
        # 这里是一个简化的模拟过程
        # 实际应用中应该连接到数字孪生系统或物理模型
        
        results = {}
        critical_params = model.get('critical_params', {})
        
        for param, value in parameters.items():
            if param in critical_params:
                limits = critical_params[param]
                # 计算参数偏离程度 (0-1)
                if value < limits['min']:
                    deviation = (limits['min'] - value) / abs(limits['min'])
                elif value > limits['max']:
                    deviation = (value - limits['max']) / abs(limits['max'])
                else:
                    deviation = 0
                
                results[f"{param}_deviation"] = deviation
        
        # 添加一些随机噪声模拟真实环境
        for key in results:
            results[key] = min(1.0, max(0.0, results[key] + random.uniform(-0.1, 0.1)))
        
        return results
    
    def _generate_optimization_recommendations(
        self,
        parameters: Dict[str, Union[float, int]],
        metrics: Dict[str, float]
    ) -> List[str]:
        """生成优化建议
        
        辅助函数，根据测试结果生成工艺优化建议。
        
        参数:
            parameters: 测试参数
            metrics: 测试指标
            
        返回:
            包含优化建议的字符串列表
        """
        recommendations = []
        
        # 根据参数偏离程度生成建议
        for param, value in parameters.items():
            deviation_key = f"{param}_deviation"
            if deviation_key in metrics and metrics[deviation_key] > 0.5:
                recommendations.append(
                    f"Consider tightening control for {param} to reduce deviation"
                )
        
        # 如果没有具体建议，添加一般性建议
        if not recommendations:
            recommendations.append("Process parameters are within optimal range")
            recommendations.append("Consider stress testing with higher intensity")
        
        return recommendations
    
    def save_stress_history(self, file_path: str) -> None:
        """保存压力测试历史到文件
        
        参数:
            file_path: 要保存的文件路径
        """
        try:
            with open(file_path, 'w') as f:
                history_data = [
                    {
                        'scenario_id': s.scenario_id,
                        'parameters': s.parameters,
                        'intensity': s.intensity,
                        'generation_method': s.generation_method,
                        'timestamp': s.timestamp
                    }
                    for s in self.stress_history
                ]
                json.dump(history_data, f, indent=2)
            logger.info(f"Stress history saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save stress history: {str(e)}")
            raise