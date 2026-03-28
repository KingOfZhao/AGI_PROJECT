"""
高级技能模块：基于过程-结果对比的微观反馈机制

该模块实现了一套基于时间差分算法的回溯分析系统，用于在缺乏显式标签的情况下，
通过最终成品的良品/次品状态自动识别导致失败的关键动作片段（错误节点）。

核心思想：
1. 将生产过程建模为马尔可夫决策过程(MDP)
2. 使用TD(λ)算法计算每个状态的价值
3. 通过反向传播计算TD误差，识别关键决策点
4. 自动生成避坑指南，无需人工标注

输入格式：
- process_data: 包含时间步、状态、动作的序列数据
- outcome_data: 最终结果（良品/次品）及奖励值

输出格式：
- FeedbackReport: 包含错误节点、风险等级、改进建议的报告
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OutcomeStatus(Enum):
    """成品状态枚举"""
    GOOD = 1       # 良品
    DEFECTIVE = 0  # 次品


@dataclass
class ProcessStep:
    """生产过程步骤数据结构"""
    timestamp: int          # 时间步
    state_vector: np.ndarray  # 状态向量
    action_id: int          # 执行的动作ID
    metadata: Dict[str, Any] = None  # 附加元数据


@dataclass
class OutcomeData:
    """成品结果数据结构"""
    status: OutcomeStatus   # 良品/次品状态
    reward: float           # 最终奖励值
    process_id: str         # 关联的过程ID


@dataclass
class ErrorNode:
    """错误节点数据结构"""
    step_index: int         # 步骤索引
    timestamp: int          # 时间步
    td_error: float         # TD误差值
    risk_level: str         # 风险等级
    state_vector: np.ndarray  # 状态快照
    suggestion: str         # 改进建议


@dataclass
class FeedbackReport:
    """反馈报告数据结构"""
    process_id: str
    is_defective: bool
    error_nodes: List[ErrorNode]
    critical_steps: List[int]
    summary: str


class TDlambdaLearner:
    """TD(λ)学习器核心类"""
    
    def __init__(self, lambda_param: float = 0.8, gamma: float = 0.99, 
                 alpha: float = 0.1, threshold: float = 0.3):
        """
        初始化TD(λ)学习器
        
        Args:
            lambda_param: 资格迹衰减参数 (0-1)
            gamma: 折扣因子
            alpha: 学习率
            threshold: 错误节点识别阈值
        """
        if not 0 <= lambda_param <= 1:
            raise ValueError(f"lambda_param must be in [0, 1], got {lambda_param}")
        if not 0 <= gamma <= 1:
            raise ValueError(f"gamma must be in [0, 1], got {gamma}")
        if not 0 < alpha <= 1:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        if threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}")
            
        self.lambda_param = lambda_param
        self.gamma = gamma
        self.alpha = alpha
        self.threshold = threshold
        self.value_function: Dict[int, float] = {}  # 状态价值函数
        
        logger.info(f"TDlambdaLearner initialized with λ={lambda_param}, "
                   f"γ={gamma}, α={alpha}, threshold={threshold}")
    
    def _hash_state(self, state_vector: np.ndarray) -> int:
        """将状态向量哈希为唯一标识符"""
        return hash(state_vector.tobytes())
    
    def compute_td_error(self, current_value: float, reward: float, 
                         next_value: float) -> float:
        """
        计算TD误差: δ = r + γV(s') - V(s)
        
        Args:
            current_value: 当前状态价值
            reward: 即时奖励
            next_value: 下一状态价值
            
        Returns:
            TD误差值
        """
        td_error = reward + self.gamma * next_value - current_value
        logger.debug(f"TD error computed: {td_error:.4f}")
        return td_error
    
    def backward_analysis(self, process_steps: List[ProcessStep], 
                          final_reward: float) -> List[Tuple[int, float, float]]:
        """
        反向传播分析，计算每个时间步的TD误差
        
        Args:
            process_steps: 过程步骤序列
            final_reward: 最终奖励值
            
        Returns:
            包含(步骤索引, 状态价值, TD误差)的列表
        """
        if not process_steps:
            raise ValueError("process_steps cannot be empty")
            
        n_steps = len(process_steps)
        td_errors = []
        eligibility_traces = {}
        
        # 反向遍历计算TD误差
        for t in reversed(range(n_steps)):
            step = process_steps[t]
            state_hash = self._hash_state(step.state_vector)
            
            # 获取或初始化状态价值
            if state_hash not in self.value_function:
                self.value_function[state_hash] = 0.0
            
            current_value = self.value_function[state_hash]
            
            # 计算下一状态价值（最后一步使用最终奖励）
            if t == n_steps - 1:
                next_value = final_reward
                reward = 0.0  # 最终步骤无中间奖励
            else:
                next_step = process_steps[t + 1]
                next_hash = self._hash_state(next_step.state_vector)
                next_value = self.value_function.get(next_hash, 0.0)
                reward = 0.0  # 稀疏奖励设置
            
            # 计算TD误差
            td_error = self.compute_td_error(current_value, reward, next_value)
            
            # 更新资格迹
            for s in list(eligibility_traces.keys()):
                eligibility_traces[s] *= self.gamma * self.lambda_param
            eligibility_traces[state_hash] = eligibility_traces.get(state_hash, 0) + 1
            
            # 更新价值函数
            self.value_function[state_hash] += self.alpha * td_error * eligibility_traces.get(state_hash, 1)
            
            td_errors.append((t, current_value, td_error))
            logger.debug(f"Step {t}: V(s)={current_value:.4f}, TD error={td_error:.4f}")
        
        logger.info(f"Backward analysis completed for {n_steps} steps")
        return td_errors[::-1]  # 返回正序结果


class MicroFeedbackGenerator:
    """微观反馈生成器"""
    
    def __init__(self, td_learner: TDlambdaLearner):
        """
        初始化反馈生成器
        
        Args:
            td_learner: TD学习器实例
        """
        self.td_learner = td_learner
        self.risk_levels = {
            'critical': (1.0, float('inf')),
            'high': (0.5, 1.0),
            'medium': (0.3, 0.5),
            'low': (0.0, 0.3)
        }
        logger.info("MicroFeedbackGenerator initialized")
    
    def _determine_risk_level(self, td_error: float) -> str:
        """根据TD误差绝对值确定风险等级"""
        abs_error = abs(td_error)
        for level, (low, high) in self.risk_levels.items():
            if low <= abs_error < high:
                return level
        return 'critical'
    
    def _generate_suggestion(self, td_error: float, step_index: int, 
                            total_steps: int) -> str:
        """生成改进建议"""
        if td_error > 0:
            return (f"步骤{step_index}: 正向偏差{td_error:.2f}，"
                   f"建议保持或优化此动作模式")
        else:
            position = "早期" if step_index < total_steps * 0.3 else \
                      "中期" if step_index < total_steps * 0.7 else "后期"
            return (f"步骤{step_index}: 检测到{position}负向偏差{abs(td_error):.2f}，"
                   f"建议审查此处的动作选择")
    
    def identify_error_nodes(self, process_steps: List[ProcessStep], 
                            td_errors: List[Tuple[int, float, float]]) -> List[ErrorNode]:
        """
        识别错误节点（关键动作片段）
        
        Args:
            process_steps: 过程步骤序列
            td_errors: TD误差列表
            
        Returns:
            错误节点列表
        """
        if len(process_steps) != len(td_errors):
            raise ValueError("process_steps and td_errors must have the same length")
        
        error_nodes = []
        threshold = self.td_learner.threshold
        total_steps = len(process_steps)
        
        for i, (step_idx, value, td_error) in enumerate(td_errors):
            # 识别显著负向TD误差（导致失败的节点）
            if td_error < -threshold:
                step = process_steps[step_idx]
                risk_level = self._determine_risk_level(td_error)
                suggestion = self._generate_suggestion(td_error, step_idx, total_steps)
                
                error_node = ErrorNode(
                    step_index=step_idx,
                    timestamp=step.timestamp,
                    td_error=td_error,
                    risk_level=risk_level,
                    state_vector=step.state_vector.copy(),
                    suggestion=suggestion
                )
                error_nodes.append(error_node)
                logger.debug(f"Error node identified at step {step_idx}: "
                           f"TD error={td_error:.4f}, risk={risk_level}")
        
        logger.info(f"Identified {len(error_nodes)} error nodes")
        return error_nodes
    
    def generate_report(self, process_id: str, process_steps: List[ProcessStep],
                       outcome: OutcomeData) -> FeedbackReport:
        """
        生成完整的反馈报告
        
        Args:
            process_id: 过程ID
            process_steps: 过程步骤序列
            outcome: 成品结果数据
            
        Returns:
            反馈报告
        """
        if not process_steps:
            raise ValueError("process_steps cannot be empty")
        if not isinstance(outcome, OutcomeData):
            raise TypeError("outcome must be an instance of OutcomeData")
        
        # 执行TD学习反向分析
        td_errors = self.td_learner.backward_analysis(process_steps, outcome.reward)
        
        # 识别错误节点
        error_nodes = self.identify_error_nodes(process_steps, td_errors)
        
        # 提取关键步骤
        critical_steps = [node.step_index for node in error_nodes 
                         if node.risk_level in ['critical', 'high']]
        
        # 生成摘要
        is_defective = outcome.status == OutcomeStatus.DEFECTIVE
        if is_defective:
            summary = (f"过程{process_id}产生次品。识别到{len(error_nodes)}个潜在错误节点，"
                      f"其中{len(critical_steps)}个为高/关键风险。建议重点审查这些步骤。")
        else:
            summary = (f"过程{process_id}产生良品。识别到{len(error_nodes)}个改进点，"
                      f"可用于进一步优化生产流程。")
        
        report = FeedbackReport(
            process_id=process_id,
            is_defective=is_defective,
            error_nodes=error_nodes,
            critical_steps=critical_steps,
            summary=summary
        )
        
        logger.info(f"Feedback report generated for process {process_id}")
        return report


def create_sample_data(n_steps: int = 20) -> Tuple[List[ProcessStep], OutcomeData]:
    """
    创建示例数据用于演示
    
    Args:
        n_steps: 步骤数量
        
    Returns:
        (过程步骤列表, 结果数据)
    """
    np.random.seed(42)
    process_steps = []
    
    for i in range(n_steps):
        # 模拟状态向量（4维）
        state = np.random.randn(4) * 0.5
        # 在第8-12步引入潜在问题
        if 8 <= i <= 12:
            state[0] -= 1.5  # 引入异常偏移
        
        step = ProcessStep(
            timestamp=i * 10,
            state_vector=state,
            action_id=np.random.randint(0, 5),
            metadata={'temperature': 20 + np.random.randn()}
        )
        process_steps.append(step)
    
    # 创建次品结果
    outcome = OutcomeData(
        status=OutcomeStatus.DEFECTIVE,
        reward=-1.0,
        process_id="SAMPLE_PROC_001"
    )
    
    return process_steps, outcome


# 使用示例
if __name__ == "__main__":
    """
    完整使用示例：
    1. 创建TD学习器
    2. 创建反馈生成器
    3. 生成示例数据
    4. 执行分析并生成报告
    5. 输出结果
    """
    print("=" * 60)
    print("基于过程-结果对比的微观反馈机制演示")
    print("=" * 60)
    
    # 1. 初始化TD学习器
    td_learner = TDlambdaLearner(
        lambda_param=0.8,
        gamma=0.99,
        alpha=0.1,
        threshold=0.3
    )
    
    # 2. 初始化反馈生成器
    feedback_gen = MicroFeedbackGenerator(td_learner)
    
    # 3. 创建示例数据
    steps, outcome = create_sample_data(25)
    print(f"\n创建了{len(steps)}个步骤的示例过程数据")
    print(f"最终结果: {'良品' if outcome.status == OutcomeStatus.GOOD else '次品'}")
    
    # 4. 生成反馈报告
    report = feedback_gen.generate_report(
        process_id="DEMO_001",
        process_steps=steps,
        outcome=outcome
    )
    
    # 5. 输出报告
    print("\n" + "=" * 60)
    print("反馈报告")
    print("=" * 60)
    print(f"过程ID: {report.process_id}")
    print(f"是否次品: {report.is_defective}")
    print(f"识别的错误节点数: {len(report.error_nodes)}")
    print(f"关键步骤索引: {report.critical_steps}")
    print(f"\n摘要: {report.summary}")
    
    print("\n详细错误节点:")
    for node in report.error_nodes[:5]:  # 只显示前5个
        print(f"  - 步骤{node.step_index}: TD误差={node.td_error:.4f}, "
              f"风险={node.risk_level}")
        print(f"    建议: {node.suggestion}")
    
    print("\n" + "=" * 60)
    print("演示完成")