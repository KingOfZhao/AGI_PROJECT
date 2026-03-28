"""
对抗性物理环境生成器

本模块实现了一个用于强化学习的对抗性环境生成器。它通过分析智能体的
当前弱点，主动生成极端的物理参数配置（如光照突变、地面摩擦系数骤变、
传感器高斯噪声等），从而克服“模拟-现实”差距，训练出高鲁棒性的AGI Agent。

典型用例:
    >>> generator = AdversarialPhysicsGenerator(param_space=example_space)
    >>> current_perf = {'stability': 0.6, 'vision_accuracy': 0.2}
    >>> scenario = generator.generate_scenario(current_perf)
    >>> print(scenario)

作者: AGI System Core Engineer
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple
import random

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名，提高代码可读性
PerformanceDict = Dict[str, float]
PhysicsParameters = Dict[str, Any]

class AdversarialPhysicsGenerator:
    """
    对抗性物理环境生成器类。
    
    根据输入的Agent性能指标，动态调整模拟环境参数，针对性地生成
    Agent难以处理的物理场景。
    """

    def __init__(self, 
                 param_space: Dict[str, Tuple[float, float]], 
                 intensity_factor: float = 1.0,
                 random_seed: Optional[int] = None):
        """
        初始化生成器。

        Args:
            param_space (Dict[str, Tuple[float, float]]): 物理参数的定义域。
                键为参数名，值为(最小值, 最大值)的元组。
                例如: {'friction': (0.1, 1.5), 'light_intensity': (0.0, 100.0)}
            intensity_factor (float): 对抗强度系数，默认1.0。数值越大生成的
                场景越极端。
            random_seed (Optional[int]): 随机种子，用于复现测试。
        
        Raises:
            ValueError: 如果参数空间为空或强度系数为负。
        """
        if not param_space:
            raise ValueError("Parameter space cannot be empty.")
        if intensity_factor < 0:
            raise ValueError("Intensity factor must be non-negative.")

        self.param_space = param_space
        self.intensity_factor = intensity_factor
        self._rng = np.random.default_rng(random_seed)
        
        # 初始化内部状态，记录历史弱点
        self._weakness_history: list = []
        
        logger.info(f"AdversarialPhysicsGenerator initialized with {len(param_space)} parameters.")

    def _validate_performance_metrics(self, metrics: PerformanceDict) -> bool:
        """
        辅助函数：验证性能指标字典的有效性。
        
        Args:
            metrics (PerformanceDict): 包含性能指标的字典。
        
        Returns:
            bool: 如果指标有效返回True。
        
        Raises:
            TypeError: 如果输入不是字典。
            ValueError: 如果指标值不在[0, 1]范围内。
        """
        if not isinstance(metrics, dict):
            raise TypeError("Performance metrics must be a dictionary.")
        
        for key, value in metrics.items():
            if not isinstance(value, (int, float)):
                logger.error(f"Invalid metric type for '{key}': {type(value)}")
                raise TypeError(f"Metric value for '{key}' must be numeric.")
            if not (0.0 <= value <= 1.0):
                logger.error(f"Metric value out of bounds for '{key}': {value}")
                raise ValueError(f"Metric value for '{key}' must be between 0.0 and 1.0.")
        
        return True

    def _get_adversarial_bias(self, performance_score: float) -> float:
        """
        辅助函数：计算对抗性偏置量。
        
        根据性能得分（0-1，越小表示越弱），计算一个偏置值。
        如果性能差（接近0），则偏置趋向于极端值（0或1）。
        如果性能好（接近1），则偏置趋向于中间值。
        
        Args:
            performance_score (float): 某一特定维度的性能得分。
        
        Returns:
            float: 用于插值的偏置系数。
        """
        # 使用反函数特性：性能越低，生成的偏离中心越大
        # 这里的逻辑是：如果性能是0.1（很差），我们想要极端值（0或1）
        # 如果性能是0.9（很好），我们保持在舒适区（0.5附近）
        weakness = 1.0 - performance_score
        # 加上一点随机扰动，防止过拟合特定的对抗模式
        noise = self._rng.normal(0, 0.05)
        return np.clip(weakness * self.intensity_factor + noise, 0, 1)

    def generate_scenario(self, 
                          current_performance: PerformanceDict, 
                          specific_target: Optional[str] = None) -> PhysicsParameters:
        """
        核心函数：生成对抗性物理场景参数。
        
        根据提供的性能指标，选择最薄弱的环节进行针对性参数生成。
        
        Args:
            current_performance (PerformanceDict): Agent当前的各项性能指标。
                键应对应物理环境的关键特征（如 'traction', 'vision'），
                值应在0.0（完全失败）到1.0（完美表现）之间。
            specific_target (Optional[str]): 指定要针对的特定参数名。
                如果为None，则自动选择表现最差的参数对应的物理维度。
        
        Returns:
            PhysicsParameters: 生成的物理参数字典。
        
        Example:
            >>> space = {'friction': (0.1, 1.0), 'lighting': (10.0, 1000.0)}
            >>> gen = AdversarialPhysicsGenerator(space)
            >>> perf = {'traction': 0.9, 'vision': 0.2} # Vision is poor
            >>> # Generator will likely generate extreme 'lighting' values
            >>> params = gen.generate_scenario(perf)
        """
        try:
            self._validate_performance_metrics(current_performance)
        except (TypeError, ValueError) as e:
            logger.error(f"Input validation failed: {e}")
            # 返回默认安全参数以防崩溃
            return self._get_default_params()

        # 1. 确定最薄弱的环节
        # 将性能指标映射到物理参数。
        # 这里假设性能键名与物理参数键名有对应关系，或者直接使用物理参数名
        # 为了演示，我们寻找performance中值最低的键
        
        if not current_performance:
            return self._get_default_params()

        # 找到表现最差的指标
        worst_metric_key = min(current_performance, key=current_performance.get)
        lowest_score = current_performance[worst_metric_key]
        
        # 确定要修改的物理参数
        # 如果没有特定目标，尝试在param_space中寻找相关键
        # 这里简化逻辑：如果worst_metric_key在param_space中，则针对它
        # 否则，随机选择一个param_space中的参数进行扰动
        
        target_param = None
        if specific_target and specific_target in self.param_space:
            target_param = specific_target
        elif worst_metric_key in self.param_space:
            target_param = worst_metric_key
        else:
            # 随机选择一个参数进行对抗性修改
            target_param = random.choice(list(self.param_space.keys()))
            logger.warning(f"Performance metric '{worst_metric_key}' not found in param space. "
                           f"Randomly targeting '{target_param}'.")

        # 2. 生成对抗性参数
        generated_params = {}
        min_val, max_val = self.param_space[target_param]
        
        # 计算对抗性偏差
        bias = self._get_adversarial_bias(lowest_score)
        
        # 决定是取最小值还是最大值（二值化极值偏好）
        # 如果bias > 0.5，倾向于max_val，否则倾向于min_val
        # 这里使用线性插值结合极值偏好
        if bias > 0.5:
            # 倾向于最大值
            # 将 bias 映射到 [mid, max]
            val = min_val + (max_val - min_val) * (0.5 + (bias - 0.5))
        else:
            # 倾向于最小值
            val = min_val + (max_val - min_val) * bias
            
        # 边界检查
        val = np.clip(val, min_val, max_val)
        generated_params[target_param] = val
        
        # 3. 对其他参数生成随机或 nominal 值
        for k, (v_min, v_max) in self.param_space.items():
            if k != target_param:
                # 其他参数保持正态分布，维持环境的基本真实性
                mean = (v_min + v_max) / 2
                std = (v_max - v_min) / 6 # 3-sigma rule
                rand_val = self._rng.normal(mean, std)
                generated_params[k] = np.clip(rand_val, v_min, v_max)

        logger.info(f"Generated adversarial scenario targeting '{target_param}' "
                    f"based on score {lowest_score:.2f}. Value set to {val:.4f}.")
        
        # 记录历史
        self._weakness_history.append({
            'target': target_param,
            'score': lowest_score,
            'generated_val': val
        })

        return generated_params

    def _get_default_params(self) -> PhysicsParameters:
        """生成默认的中心参数，用于错误回退。"""
        return {k: (v[0] + v[1]) / 2 for k, v in self.param_space.items()}

    def inject_noise(self, params: PhysicsParameters, noise_level: float = 0.1) -> PhysicsParameters:
        """
        核心函数：在生成的参数基础上注入高斯噪声。
        
        模拟真实世界中的工艺'残次品'或不稳定性。即使是对抗性参数，
        也不应该是一成不变的，需要模拟混沌。
        
        Args:
            params (PhysicsParameters): 基础物理参数。
            noise_level (float): 噪声标准差相对于参数范围的比率 (0.0-1.0)。
        
        Returns:
            PhysicsParameters: 注入噪声后的参数。
        """
        if not (0.0 <= noise_level <= 1.0):
            raise ValueError("Noise level must be between 0.0 and 1.0.")
            
        noisy_params = {}
        for key, value in params.items():
            if key in self.param_space:
                min_val, max_val = self.param_space[key]
                range_val = max_val - min_val
                # 计算绝对噪声标准差
                std_dev = range_val * noise_level
                # 注入噪声
                noise = self._rng.normal(0, std_dev)
                new_val = value + noise
                # 边界钳制
                noisy_params[key] = np.clip(new_val, min_val, max_val)
            else:
                noisy_params[key] = value # 保持原样如果未定义范围
                
        logger.debug(f"Injected noise with level {noise_level}")
        return noisy_params

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 定义物理参数空间 (模拟自动驾驶场景)
    # 摩擦系数 (0.0 极滑, 1.5 极高抓地力)
    # 光照强度 (0.0 漆黑, 2000.0 强光/眩光)
    # 传感器延迟 (0.01s 极快, 0.5s 严重卡顿)
    PARAM_SPACE = {
        'ground_friction': (0.05, 1.2),
        'ambient_light': (10.0, 2000.0),
        'sensor_latency': (0.01, 0.5)
    }

    # 2. 初始化生成器
    try:
        adv_generator = AdversarialPhysicsGenerator(
            param_space=PARAM_SPACE,
            intensity_factor=1.2, # 稍微激进的强度
            random_seed=42
        )

        # 3. 模拟 Agent 当前的性能反馈
        # 假设 Agent 在低光照下表现很差 (vision_score = 0.1)，但在抓地力方面表现尚可
        agent_performance_metrics = {
            'ambient_light': 0.1,  # 视觉得分低 -> 系统应生成极端光照
            'ground_friction': 0.8, # 表现良好 -> 系统可能不会针对此进行太多干扰
            'sensor_latency': 0.5   # 表现一般
        }

        print("--- Generating Adversarial Scenario ---")
        # 4. 生成场景
        scenario = adv_generator.generate_scenario(agent_performance_metrics)
        
        # 5. 注入工艺噪声 (模拟现实的不完美)
        final_env_params = adv_generator.inject_noise(scenario, noise_level=0.05)

        print(f"Agent Performance: {agent_performance_metrics}")
        print(f"Generated Base Scenario: {scenario}")
        print(f"Final Noisy Environment: {final_env_params}")

        # 预期结果：'ambient_light' 应该非常接近 10.0 或 2000.0
        # 因为 agent_performance_metrics['ambient_light'] 很低 (0.1)
        # 对抗网络会试图让环境变得更恶劣。

    except Exception as e:
        logger.critical(f"System crashed: {e}", exc_info=True)