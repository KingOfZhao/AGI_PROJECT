"""
风险隔离沙盒系统

本模块实现了一个低成本的'试错魔圈'，通过构建具有明确胜负条件、反馈机制和'虚拟后果'的沙盒环境，
让用户在模拟环境中进行决策和学习。系统支持多种场景模拟，特别适用于投资学习、决策训练等领域。

核心功能：
- 创建模拟环境（如反直觉市场波动）
- 管理用户决策和反馈机制
- 追踪学习进度和固化'真实节点'

数据格式：
- 输入：用户决策数据（JSON格式）
- 输出：模拟结果和反馈报告（JSON格式）
"""

import json
import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimulationType(Enum):
    """模拟环境类型枚举"""
    INVESTMENT = auto()
    DECISION_MAKING = auto()
    STRATEGY_TESTING = auto()


@dataclass
class SandboxEnvironment:
    """沙盒环境数据结构"""
    env_id: str
    env_type: SimulationType
    parameters: Dict[str, Any]
    state: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = False


@dataclass
class UserDecision:
    """用户决策数据结构"""
    decision_id: str
    env_id: str
    action: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feedback:
    """反馈结果数据结构"""
    feedback_id: str
    decision_id: str
    is_successful: bool
    message: str
    score_change: float
    new_state: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RiskIsolationSandbox:
    """
    风险隔离沙盒系统
    
    实现一个低成本的'试错魔圈'，通过模拟环境让用户进行决策训练，
    并提供即时反馈和虚拟后果，帮助固化'真实节点'。
    
    示例:
        >>> sandbox = RiskIsolationSandbox()
        >>> env = sandbox.create_environment(SimulationType.INVESTMENT, 
        ...                                {"volatility": 0.3, "initial_capital": 10000})
        >>> decision = sandbox.submit_decision(env.env_id, "buy", 5000)
        >>> feedback = sandbox.get_feedback(decision.decision_id)
    """
    
    def __init__(self) -> None:
        """初始化沙盒系统"""
        self.environments: Dict[str, SandboxEnvironment] = {}
        self.decisions: Dict[str, UserDecision] = {}
        self.feedback_history: Dict[str, Feedback] = {}
        self.user_scores: Dict[str, float] = {}
        logger.info("风险隔离沙盒系统初始化完成")
    
    def create_environment(self, 
                          env_type: SimulationType,
                          parameters: Dict[str, Any],
                          user_id: Optional[str] = None) -> SandboxEnvironment:
        """
        创建新的模拟环境
        
        参数:
            env_type: 模拟环境类型
            parameters: 环境参数
            user_id: 可选的用户ID
            
        返回:
            SandboxEnvironment: 创建的沙盒环境
            
        异常:
            ValueError: 如果参数验证失败
        """
        if not parameters:
            logger.error("创建环境失败: 参数为空")
            raise ValueError("环境参数不能为空")
            
        env_id = str(uuid.uuid4())
        
        # 验证参数边界
        if env_type == SimulationType.INVESTMENT:
            if "initial_capital" not in parameters or parameters["initial_capital"] <= 0:
                logger.error("投资环境参数无效: 初始资本必须为正数")
                raise ValueError("投资环境需要有效的初始资本参数")
        
        # 创建环境状态
        initial_state = self._generate_initial_state(env_type, parameters)
        
        environment = SandboxEnvironment(
            env_id=env_id,
            env_type=env_type,
            parameters=parameters,
            state=initial_state,
            is_active=True
        )
        
        self.environments[env_id] = environment
        if user_id:
            self.user_scores[user_id] = 0.0
        
        logger.info(f"创建新环境: ID={env_id}, 类型={env_type.name}")
        return environment
    
    def submit_decision(self,
                       env_id: str,
                       action: str,
                       value: float,
                       metadata: Optional[Dict[str, Any]] = None) -> UserDecision:
        """
        提交用户决策到沙盒环境
        
        参数:
            env_id: 环境ID
            action: 用户动作
            value: 动作值
            metadata: 可选的元数据
            
        返回:
            UserDecision: 用户决策记录
            
        异常:
            ValueError: 如果环境不存在或不活跃
        """
        if env_id not in self.environments:
            logger.error(f"提交决策失败: 环境不存在 ID={env_id}")
            raise ValueError("环境不存在")
            
        environment = self.environments[env_id]
        if not environment.is_active:
            logger.error(f"提交决策失败: 环境已关闭 ID={env_id}")
            raise ValueError("环境已关闭")
            
        decision_id = str(uuid.uuid4())
        decision = UserDecision(
            decision_id=decision_id,
            env_id=env_id,
            action=action,
            value=value,
            metadata=metadata or {}
        )
        
        self.decisions[decision_id] = decision
        logger.info(f"收到新决策: ID={decision_id}, 环境ID={env_id}, 动作={action}")
        return decision
    
    def get_feedback(self, decision_id: str) -> Feedback:
        """
        获取决策反馈
        
        参数:
            decision_id: 决策ID
            
        返回:
            Feedback: 决策反馈
            
        异常:
            ValueError: 如果决策不存在
        """
        if decision_id not in self.decisions:
            logger.error(f"获取反馈失败: 决策不存在 ID={decision_id}")
            raise ValueError("决策不存在")
            
        decision = self.decisions[decision_id]
        environment = self.environments[decision.env_id]
        
        # 根据环境类型生成反馈
        if environment.env_type == SimulationType.INVESTMENT:
            feedback = self._evaluate_investment_decision(decision, environment)
        else:
            feedback = self._evaluate_generic_decision(decision, environment)
        
        self.feedback_history[feedback.feedback_id] = feedback
        logger.info(f"生成反馈: ID={feedback.feedback_id}, 决策ID={decision_id}")
        return feedback
    
    def _generate_initial_state(self, 
                               env_type: SimulationType,
                               parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成环境的初始状态（辅助函数）
        
        参数:
            env_type: 环境类型
            parameters: 环境参数
            
        返回:
            Dict[str, Any]: 初始状态字典
        """
        if env_type == SimulationType.INVESTMENT:
            return {
                "capital": parameters["initial_capital"],
                "assets": 0,
                "market_price": 100.0,
                "volatility": parameters.get("volatility", 0.2),
                "steps": 0
            }
        elif env_type == SimulationType.DECISION_MAKING:
            return {
                "score": 0,
                "scenarios_completed": 0,
                "current_scenario": 1
            }
        else:
            return {"status": "initialized"}
    
    def _evaluate_investment_decision(self,
                                     decision: UserDecision,
                                     environment: SandboxEnvironment) -> Feedback:
        """
        评估投资决策（核心函数）
        
        参数:
            decision: 用户决策
            environment: 沙盒环境
            
        返回:
            Feedback: 评估结果反馈
        """
        state = environment.state.copy()
        action = decision.action.lower()
        value = decision.value
        success = False
        message = ""
        score_change = 0.0
        
        # 模拟市场波动（反直觉设计）
        market_change = random.uniform(-0.3, 0.3)  # 高波动性
        state["market_price"] *= (1 + market_change)
        state["steps"] += 1
        
        # 评估决策
        if action == "buy":
            if value <= state["capital"]:
                assets_bought = value / state["market_price"]
                state["capital"] -= value
                state["assets"] += assets_bought
                success = True
                message = f"购买成功: 买入{assets_bought:.2f}单位资产"
                score_change = 5.0  # 奖励理性决策
            else:
                message = "资金不足，购买失败"
                score_change = -2.0  # 惩罚冲动决策
                
        elif action == "sell":
            if value <= state["assets"]:
                revenue = value * state["market_price"]
                state["capital"] += revenue
                state["assets"] -= value
                success = True
                message = f"出售成功: 获得{revenue:.2f}资金"
                score_change = 3.0  # 奖励及时止损
            else:
                message = "资产不足，出售失败"
                score_change = -1.5
                
        elif action == "hold":
            success = True
            message = "持有观望"
            score_change = 1.0  # 奖励耐心
            
        else:
            message = "无效操作"
            score_change = -5.0  # 重罚错误操作
        
        # 更新环境状态
        environment.state = state
        
        feedback_id = str(uuid.uuid4())
        return Feedback(
            feedback_id=feedback_id,
            decision_id=decision.decision_id,
            is_successful=success,
            message=message,
            score_change=score_change,
            new_state=state
        )
    
    def _evaluate_generic_decision(self,
                                  decision: UserDecision,
                                  environment: SandboxEnvironment) -> Feedback:
        """
        评估通用决策（核心函数）
        
        参数:
            decision: 用户决策
            environment: 沙盒环境
            
        返回:
            Feedback: 评估结果反馈
        """
        state = environment.state.copy()
        action = decision.action.lower()
        value = decision.value
        success = False
        message = ""
        score_change = 0.0
        
        # 简单决策评估逻辑
        if action in ["accept", "approve", "confirm"]:
            success = True
            message = "决策接受"
            score_change = 2.0
        elif action in ["reject", "deny", "cancel"]:
            success = True
            message = "决策拒绝"
            score_change = 1.0
        else:
            message = "无效决策"
            score_change = -1.0
        
        state["score"] += score_change
        state["scenarios_completed"] += 1
        environment.state = state
        
        feedback_id = str(uuid.uuid4())
        return Feedback(
            feedback_id=feedback_id,
            decision_id=decision.decision_id,
            is_successful=success,
            message=message,
            score_change=score_change,
            new_state=state
        )
    
    def get_environment_status(self, env_id: str) -> Dict[str, Any]:
        """
        获取环境状态
        
        参数:
            env_id: 环境ID
            
        返回:
            Dict[str, Any]: 环境状态信息
            
        异常:
            ValueError: 如果环境不存在
        """
        if env_id not in self.environments:
            logger.error(f"获取状态失败: 环境不存在 ID={env_id}")
            raise ValueError("环境不存在")
            
        environment = self.environments[env_id]
        return {
            "env_id": environment.env_id,
            "type": environment.env_type.name,
            "is_active": environment.is_active,
            "current_state": environment.state,
            "parameters": environment.parameters
        }
    
    def close_environment(self, env_id: str) -> None:
        """
        关闭环境
        
        参数:
            env_id: 环境ID
            
        异常:
            ValueError: 如果环境不存在
        """
        if env_id not in self.environments:
            logger.error(f"关闭环境失败: 环境不存在 ID={env_id}")
            raise ValueError("环境不存在")
            
        environment = self.environments[env_id]
        environment.is_active = False
        logger.info(f"环境已关闭: ID={env_id}")


# 使用示例
if __name__ == "__main__":
    # 初始化沙盒系统
    sandbox = RiskIsolationSandbox()
    
    # 创建投资模拟环境
    investment_params = {
        "initial_capital": 10000,
        "volatility": 0.3
    }
    env = sandbox.create_environment(
        SimulationType.INVESTMENT, 
        investment_params,
        user_id="user_123"
    )
    
    # 提交一系列决策
    decisions = [
        ("buy", 5000),
        ("hold", 0),
        ("sell", 20),
        ("buy", 3000)
    ]
    
    for action, value in decisions:
        decision = sandbox.submit_decision(env.env_id, action, value)
        feedback = sandbox.get_feedback(decision.decision_id)
        print(f"决策: {action} {value} | 结果: {feedback.message} | 分数变化: {feedback.score_change}")
    
    # 获取最终状态
    final_status = sandbox.get_environment_status(env.env_id)
    print("\n最终环境状态:")
    print(json.dumps(final_status, indent=2))
    
    # 关闭环境
    sandbox.close_environment(env.env_id)