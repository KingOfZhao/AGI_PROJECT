"""
模块名称: auto_开发_贝叶斯情境仲裁器_根据当前环境压_967c93
描述: 开发'贝叶斯情境仲裁器'，根据当前环境压力（如是否处于DDoS攻击态）动态调整'本地直觉'与'全局共识'的权重比例。

此模块实现了一个基于贝叶斯推断的决策仲裁器。它实时监控环境指标（如CPU负载、错误率），
利用贝叶斯更新计算系统处于"高压状态"（如DDoS攻击或资源枯竭）的后验概率。
基于该概率，仲裁器动态调整决策权重：在高压状态下，倾向于信任"本地直觉"（响应快、
基于局部状态的自救策略）；在低压状态下，倾向于信任"全局共识"（更耗算力、全局最优的协同策略）。

数据流:
    Input: {
        "metrics": {"error_rate": 0.0-1.0, "latency_ms": float, "cpu_load": 0.0-1.0},
        "local_decision": {"action": str, "confidence": 0.0-1.0},
        "global_decision": {"action": str, "confidence": 0.0-1.0}
    }
    Output: {
        "final_action": str,
        "selected_source": str,
        "pressure_score": float,
        "weights": {"local": float, "global": float}
    }
"""

import logging
import math
from typing import Dict, Any, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BayesianContextArbitrator:
    """
    贝叶斯情境仲裁器类。
    
    负责根据环境压力动态平衡本地直觉与全局共识的权重。
    """

    def __init__(self, 
                 prior_pressure: float = 0.05, 
                 pressure_threshold: float = 0.75,
                 sensitivity: float = 1.5):
        """
        初始化仲裁器。

        Args:
            prior_pressure (float): 初始环境压力信念（先验概率），默认为0.05。
            pressure_threshold (float): 触发高压策略的阈值，默认为0.75。
            sensitivity (float): 似然函数的敏感度系数，控制对环境变化的反应速度。
        """
        self.pressure_belief = prior_pressure  # P(Pressure)
        self.pressure_threshold = pressure_threshold
        self.sensitivity = sensitivity
        logger.info(f"Arbitrator initialized with prior: {prior_pressure}, threshold: {pressure_threshold}")

    def _validate_inputs(self, metrics: Dict[str, float], 
                         local_decision: Dict[str, Any], 
                         global_decision: Dict[str, Any]) -> None:
        """
        辅助函数：验证输入数据的完整性和范围。
        
        Args:
            metrics (Dict): 环境指标字典。
            local_decision (Dict): 本地决策字典。
            global_decision (Dict): 全局决策字典。
            
        Raises:
            ValueError: 如果数据缺失或超出边界。
        """
        if not all(k in metrics for k in ['error_rate', 'cpu_load']):
            raise ValueError("Metrics must contain 'error_rate' and 'cpu_load'")
        
        if not (0 <= metrics['error_rate'] <= 1 and 0 <= metrics['cpu_load'] <= 1):
            raise ValueError("Error rate and CPU load must be between 0 and 1")

        if 'confidence' not in local_decision or 'confidence' not in global_decision:
            raise ValueError("Decisions must contain 'confidence' key")
            
        if not (0 <= local_decision['confidence'] <= 1 and 0 <= global_decision['confidence'] <= 1):
            raise ValueError("Confidence values must be between 0 and 1")

    def _calculate_likelihood(self, metrics: Dict[str, float]) -> float:
        """
        核心函数1: 计算似然概率 P(Data | Pressure)。
        
        基于环境指标计算当前处于高压状态的可能性。
        使用高斯分布模拟：指标越高，处于高压状态的概率越大。
        
        Args:
            metrics (Dict): 包含 'error_rate', 'latency_ms', 'cpu_load' 的字典。
            
        Returns:
            float: 似然概率值。
        """
        # 简单的加权综合指标
        # 假设 error_rate 权重较高，因为是攻击的直接体现
        composite_score = (
            metrics.get('error_rate', 0) * 0.5 + 
            metrics.get('cpu_load', 0) * 0.3 + 
            min(metrics.get('latency_ms', 0) / 1000, 1.0) * 0.2 # 归一化延迟
        )
        
        # 使用Sigmoid函数将综合得分映射为似然概率
        # x = composite_score, 中心点设为0.6 (感觉压力大)
        likelihood = 1 / (1 + math.exp(-self.sensitivity * (composite_score - 0.6)))
        
        logger.debug(f"Composite score: {composite_score:.4f}, Likelihood: {likelihood:.4f}")
        return likelihood

    def update_belief(self, metrics: Dict[str, float]) -> float:
        """
        核心函数2: 使用贝叶斯定理更新后验概率 P(Pressure | Data)。
        
        Posterior = (Likelihood * Prior) / Normalization_Constant
        为了简化，我们这里计算 P(Pressure) 的更新，并假设 P(Not Pressure) 的似然较低。
        
        Args:
            metrics (Dict): 最新的环境指标。
            
        Returns:
            float: 更新后的压力指数 (0.0 到 1.0)。
        """
        likelihood_high = self._calculate_likelihood(metrics)
        
        # 假设正常状态下的似然 (互补)
        likelihood_low = 1 - likelihood_high
        
        # 贝叶斯更新
        # P(Press|D) = [P(D|Press) * P(Press)] / [P(D|Press)*P(Press) + P(D|~Press)*P(~Press)]
        numerator = likelihood_high * self.pressure_belief
        denominator = numerator + (likelihood_low * (1 - self.pressure_belief))
        
        if denominator == 0:
            # 防止除零，虽然理论上不会发生
            posterior = 0.0
        else:
            posterior = numerator / denominator
            
        # 应用移动平均平滑，防止抖动 (简单的指数加权)
        # 这里直接赋值，但在生产环境建议使用 learning_rate
        self.pressure_belief = posterior
        
        logger.info(f"Bayesian update completed. New pressure belief: {self.pressure_belief:.4f}")
        return self.pressure_belief

    def arbitrate(self, 
                  metrics: Dict[str, float], 
                  local_decision: Dict[str, Any], 
                  global_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心函数3: 执行仲裁，决定最终采纳的决策。
        
        Args:
            metrics (Dict): 环境指标。
            local_decision (Dict): 本地系统的建议 (通常反应快，局部最优)。
            global_decision (Dict): 全局集群的建议 (通常耗资源，全局最优)。
            
        Returns:
            Dict: 包含最终动作、权重分配和元数据的字典。
        """
        try:
            self._validate_inputs(metrics, local_decision, global_decision)
        except ValueError as e:
            logger.error(f"Input validation failed: {e}")
            # 默认降级策略：选择置信度高的，或默认本地
            return {
                "final_action": local_decision.get("action", "fallback"),
                "selected_source": "fallback_error",
                "pressure_score": 0.0,
                "weights": {"local": 1.0, "global": 0.0}
            }

        # 1. 更新当前环境压力信念
        current_pressure = self.update_belief(metrics)
        
        # 2. 计算权重
        # 如果压力大 (current_pressure -> 1)，权重向 Local 倾斜 (Local: 1, Global: 0)
        # 如果压力小 (current_pressure -> 0)，权重向 Global 倾斜 (Local: 0, Global: 1)
        weight_local = current_pressure
        weight_global = 1.0 - current_pressure
        
        # 3. 计算加权得分
        # 结合决策自身的置信度
        score_local = weight_local * local_decision['confidence']
        score_global = weight_global * global_decision['confidence']
        
        logger.info(f"Scores -> Local: {score_local:.3f} (w={weight_local:.2f}), Global: {score_global:.3f} (w={weight_global:.2f})")
        
        # 4. 选择最终决策
        if score_local >= score_global:
            final_action = local_decision['action']
            source = "local_intuition"
        else:
            final_action = global_decision['action']
            source = "global_consensus"
            
        return {
            "final_action": final_action,
            "selected_source": source,
            "pressure_score": current_pressure,
            "weights": {
                "local": weight_local,
                "global": weight_global
            },
            "raw_scores": {
                "local": score_local,
                "global": score_global
            }
        }

# 使用示例
if __name__ == "__main__":
    # 初始化仲裁器
    arbitrator = BayesianContextArbitrator(prior_pressure=0.1)
    
    print("--- 场景 1: 正常流量 (低压) ---")
    normal_metrics = {"error_rate": 0.01, "cpu_load": 0.2, "latency_ms": 50}
    local_idea = {"action": "cache_refresh", "confidence": 0.6}
    global_idea = {"action": "deploy_new_model", "confidence": 0.9}
    
    result_normal = arbitrator.arbitrate(normal_metrics, local_idea, global_idea)
    print(f"Decision: {result_normal['final_action']} (Source: {result_normal['selected_source']})")
    print(f"Weights: Local {result_normal['weights']['local']:.2f} vs Global {result_normal['weights']['global']:.2f}")
    
    print("\n--- 场景 2: DDoS 攻击 (高压) ---")
    attack_metrics = {"error_rate": 0.95, "cpu_load": 0.99, "latency_ms": 5000}
    # 在攻击中，本地可能决定 "限流" (高置信度因为检测到了异常)
    # 全局可能决定 "扩展集群" (但在高压下，扩展可能来不及，且通信受阻)
    local_idea_attack = {"action": "enable_rate_limit", "confidence": 0.95}
    global_idea_attack = {"action": "scale_up_cluster", "confidence": 0.8}
    
    result_attack = arbitrator.arbitrate(attack_metrics, local_idea_attack, global_idea_attack)
    print(f"Decision: {result_attack['final_action']} (Source: {result_attack['selected_source']})")
    print(f"Weights: Local {result_attack['weights']['local']:.2f} vs Global {result_attack['weights']['global']:.2f}")