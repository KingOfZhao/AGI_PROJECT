"""
人机共生反馈闭环的延迟敏感性分析模块

本模块模拟在"AI建议 -> 人类实践 -> 反馈"的闭环中，时间延迟对AI模型
权重更新及归因准确性的影响。它量化了从"真实节点"生成到AI权重更新的
时间差与模型准确率下降之间的非线性关系。

主要功能:
1. 构建模拟的人机交互环境
2. 模拟不同时间延迟下的反馈闭环
3. 分析延迟对AI归因准确性的影响
4. 生成延迟敏感性分析报告

数据流:
输入 -> AI模型 -> 人类实践 -> 环境反馈 -> (延迟) -> AI模型更新
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SimulationConfig:
    """模拟配置参数"""
    num_iterations: int = 1000  # 每次实验的迭代次数
    num_trials: int = 10        # 每个延迟设置的实验次数
    base_accuracy: float = 0.85  # 初始模型准确率
    noise_level: float = 0.05    # 环境噪声水平
    learning_rate: float = 0.1   # AI模型学习率
    min_delay: int = 0           # 最小延迟(迭代步数)
    max_delay: int = 20          # 最大延迟(迭代步数)
    delay_step: int = 2          # 延迟增量

@dataclass
class ExperimentResult:
    """实验结果数据结构"""
    delay: int
    accuracy: float
    attribution_error: float
    stability: float
    sample_size: int

class DelaySensitivityAnalyzer:
    """人机共生反馈闭环延迟敏感性分析器"""
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        """初始化分析器
        
        Args:
            config: 模拟配置参数，如果为None则使用默认值
        """
        self.config = config or SimulationConfig()
        self._validate_config()
        logger.info("DelaySensitivityAnalyzer initialized with config: %s", 
                   json.dumps(self.config.__dict__, indent=2))
    
    def _validate_config(self) -> None:
        """验证配置参数的有效性"""
        if self.config.num_iterations <= 0:
            raise ValueError("num_iterations must be positive")
        if not 0 < self.config.base_accuracy <= 1:
            raise ValueError("base_accuracy must be between 0 and 1")
        if self.config.min_delay < 0:
            raise ValueError("min_delay cannot be negative")
        if self.config.max_delay < self.config.min_delay:
            raise ValueError("max_delay cannot be less than min_delay")
    
    def _simulate_human_practice(self, 
                                ai_suggestion: float, 
                                true_state: float) -> Tuple[bool, float]:
        """模拟人类实践过程
        
        Args:
            ai_suggestion: AI模型的建议值
            true_state: 环境真实状态
            
        Returns:
            Tuple[实践是否成功, 反馈值]
        """
        # 人类实践成功率受AI建议准确性和环境噪声影响
        error = abs(ai_suggestion - true_state)
        success_prob = max(0, 1 - error - self.config.noise_level)
        success = np.random.random() < success_prob
        
        # 反馈值包含噪声
        feedback = true_state + np.random.normal(0, self.config.noise_level)
        return success, feedback
    
    def run_single_experiment(self, 
                            delay: int, 
                            seed: Optional[int] = None) -> Dict[str, float]:
        """运行单次延迟敏感性实验
        
        Args:
            delay: 反馈延迟的迭代步数
            seed: 随机种子，用于结果复现
            
        Returns:
            包含实验结果的字典:
            {
                'final_accuracy': float,
                'attribution_error': float,
                'stability': float
            }
        """
        if seed is not None:
            np.random.seed(seed)
        
        # 初始化模型和环境
        model_accuracy = self.config.base_accuracy
        feedback_buffer = []
        accuracy_history = []
        attribution_errors = []
        
        for i in range(self.config.num_iterations):
            # 生成环境真实状态
            true_state = np.random.random()
            
            # AI生成建议
            if np.random.random() < model_accuracy:
                ai_suggestion = true_state  # 正确建议
            else:
                ai_suggestion = np.random.random()  # 错误建议
            
            # 人类实践
            success, feedback = self._simulate_human_practice(ai_suggestion, true_state)
            
            # 将反馈存入缓冲区
            feedback_buffer.append((i, feedback, success, true_state, ai_suggestion))
            
            # 处理延迟到达的反馈
            if i >= delay:
                _, delayed_feedback, delayed_success, delayed_state, delayed_suggestion = feedback_buffer[i - delay]
                
                # 模型更新
                attribution_error = abs(delayed_state - delayed_suggestion)
                attribution_errors.append(attribution_error)
                
                # 延迟越大，归因错误越大
                error_factor = min(1, delay / 10)  # 非线性因子
                effective_error = attribution_error * (1 + error_factor)
                
                # 更新模型准确率
                if delayed_success:
                    model_accuracy += self.config.learning_rate * (1 - effective_error)
                else:
                    model_accuracy -= self.config.learning_rate * effective_error
                
                # 确保准确率在合理范围内
                model_accuracy = np.clip(model_accuracy, 0.5, 1.0)
            
            accuracy_history.append(model_accuracy)
        
        # 计算结果指标
        final_accuracy = np.mean(accuracy_history[-100:])  # 最后100次迭代的平均准确率
        avg_attribution_error = np.mean(attribution_errors) if attribution_errors else 0
        stability = 1 - np.std(accuracy_history[-100:]) / 0.1  # 稳定性指标
        
        return {
            'final_accuracy': final_accuracy,
            'attribution_error': avg_attribution_error,
            'stability': stability
        }
    
    def run_comprehensive_analysis(self) -> List[ExperimentResult]:
        """运行全面的延迟敏感性分析
        
        Returns:
            包含不同延迟设置下实验结果的列表
        """
        results = []
        
        # 测试不同延迟设置
        for delay in range(self.config.min_delay, 
                          self.config.max_delay + 1, 
                          self.config.delay_step):
            trial_results = []
            
            # 每个延迟设置运行多次实验
            for trial in range(self.config.num_trials):
                result = self.run_single_experiment(delay, seed=trial)
                trial_results.append(result)
            
            # 计算平均结果
            avg_accuracy = np.mean([r['final_accuracy'] for r in trial_results])
            avg_error = np.mean([r['attribution_error'] for r in trial_results])
            avg_stability = np.mean([r['stability'] for r in trial_results])
            
            results.append(ExperimentResult(
                delay=delay,
                accuracy=avg_accuracy,
                attribution_error=avg_error,
                stability=avg_stability,
                sample_size=len(trial_results)
            ))
            
            logger.info("Delay %d: Accuracy=%.3f, Error=%.3f, Stability=%.3f",
                       delay, avg_accuracy, avg_error, avg_stability)
        
        return results
    
    def generate_report(self, results: List[ExperimentResult]) -> Dict:
        """生成延迟敏感性分析报告
        
        Args:
            results: 实验结果列表
            
        Returns:
            包含分析报告的字典
        """
        if not results:
            raise ValueError("No experiment results to generate report")
        
        # 计算关键指标
        delays = [r.delay for r in results]
        accuracies = [r.accuracy for r in results]
        errors = [r.attribution_error for r in results]
        stabilities = [r.stability for r in results]
        
        # 找出临界延迟点(准确率下降超过5%的点)
        baseline_accuracy = accuracies[0]
        critical_delay = None
        for delay, acc in zip(delays, accuracies):
            if baseline_accuracy - acc > 0.05:
                critical_delay = delay
                break
        
        # 计算非线性关系
        nonlinear_coef = np.polyfit(delays, accuracies, 2)  # 二次拟合
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.__dict__,
            'summary': {
                'baseline_accuracy': baseline_accuracy,
                'critical_delay': critical_delay,
                'max_accuracy_drop': baseline_accuracy - min(accuracies),
                'average_stability': np.mean(stabilities)
            },
            'trend_analysis': {
                'nonlinear_coefficients': nonlinear_coef.tolist(),
                'delay_accuracy_correlation': np.corrcoef(delays, accuracies)[0, 1]
            },
            'detailed_results': [r.__dict__ for r in results]
        }
        
        logger.info("Generated analysis report with critical delay: %s", critical_delay)
        return report

def plot_results(results: List[ExperimentResult], save_path: str = None) -> None:
    """绘制实验结果图表
    
    Args:
        results: 实验结果列表
        save_path: 图表保存路径，如果为None则显示图表
    """
    delays = [r.delay for r in results]
    accuracies = [r.accuracy for r in results]
    errors = [r.attribution_error for r in results]
    
    plt.figure(figsize=(12, 5))
    
    # 准确率与延迟关系
    plt.subplot(1, 2, 1)
    plt.plot(delays, accuracies, 'bo-')
    plt.xlabel('Feedback Delay (iterations)')
    plt.ylabel('Model Accuracy')
    plt.title('Accuracy vs Feedback Delay')
    plt.grid(True)
    
    # 归因误差与延迟关系
    plt.subplot(1, 2, 2)
    plt.plot(delays, errors, 'ro-')
    plt.xlabel('Feedback Delay (iterations)')
    plt.ylabel('Attribution Error')
    plt.title('Attribution Error vs Feedback Delay')
    plt.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        logger.info("Saved plot to %s", save_path)
    else:
        plt.show()

# 使用示例
if __name__ == "__main__":
    try:
        # 初始化分析器
        config = SimulationConfig(
            num_iterations=500,
            num_trials=5,
            max_delay=15,
            delay_step=3
        )
        analyzer = DelaySensitivityAnalyzer(config)
        
        # 运行分析
        results = analyzer.run_comprehensive_analysis()
        
        # 生成报告
        report = analyzer.generate_report(results)
        print(json.dumps(report, indent=2))
        
        # 绘制结果
        plot_results(results, "delay_sensitivity_analysis.png")
        
    except Exception as e:
        logger.error("Error in analysis: %s", str(e), exc_info=True)
        raise