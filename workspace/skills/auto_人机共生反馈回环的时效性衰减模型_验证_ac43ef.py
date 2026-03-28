"""
人机共生反馈回环的时效性衰减模型验证模块

本模块实现了一个用于验证人机共生系统中反馈时效性衰减的模型。
核心思想是验证'人类反馈的纠错权重'是否应随时间指数级衰减，
以及节点在无人干预下保持稳定时是否可以提升其'置信度'层级。

模型假设：
1. 初始状态：每个节点都有一个人工复核的依赖度
2. 衰减机制：每次成功的AI自动化调用都会降低对人工复核的依赖
3. 置信度提升：节点在无人干预下保持稳定时，可以提升其置信度层级
4. 指数衰减：人工复核的必要性随时间指数级衰减

输入数据格式：
{
    "node_id": "unique_node_identifier",
    "initial_human_dependency": 0.8,  # 0-1之间，表示初始对人工的依赖度
    "confidence_level": 3,  # 1-5之间的整数，表示初始置信度层级
    "last_human_check": "2023-01-01T00:00:00",  # ISO格式时间戳
    "automated_checks": 0,  # 自动化检查次数
    "error_count": 0  # 错误计数
}

输出数据格式：
{
    "node_id": "unique_node_identifier",
    "current_human_dependency": 0.25,  # 当前对人工的依赖度
    "confidence_level": 4,  # 当前置信度层级
    "decay_rate": 0.1,  # 衰减率
    "next_check_due": "2023-01-15T00:00:00",  # 下次检查时间
    "status": "stable"  # 节点状态: stable, needs_review, error
}
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import json
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DecayModelValidator:
    """人机共生反馈回环的时效性衰减模型验证器"""
    
    # 置信度层级定义 (1-5)
    CONFIDENCE_LEVELS = {
        1: "critical",    # 关键节点，需要频繁人工检查
        2: "high",        # 高风险节点
        3: "medium",      # 中等风险
        4: "low",         # 低风险
        5: "automated"    # 完全自动化
    }
    
    # 状态定义
    STATUS_OPTIONS = ["stable", "needs_review", "error"]
    
    def __init__(self, base_decay_rate: float = 0.1, max_automated_checks: int = 50):
        """
        初始化衰减模型验证器
        
        参数:
            base_decay_rate: 基础衰减率，控制依赖度下降的速度 (默认0.1)
            max_automated_checks: 最大自动化检查次数上限 (默认50)
        """
        self.base_decay_rate = base_decay_rate
        self.max_automated_checks = max_automated_checks
        self._validate_parameters()
        logger.info(f"DecayModelValidator initialized with decay_rate={base_decay_rate}, max_checks={max_automated_checks}")
    
    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性"""
        if not 0 < self.base_decay_rate < 1:
            raise ValueError("base_decay_rate must be between 0 and 1 (exclusive)")
        if self.max_automated_checks <= 0:
            raise ValueError("max_automated_checks must be positive")
    
    def validate_node_data(self, node_data: Dict[str, Any]) -> bool:
        """
        验证节点数据的完整性和有效性
        
        参数:
            node_data: 包含节点数据的字典
            
        返回:
            bool: 数据是否有效
            
        异常:
            ValueError: 当数据无效时抛出
        """
        required_fields = [
            'node_id', 'initial_human_dependency', 'confidence_level',
            'last_human_check', 'automated_checks', 'error_count'
        ]
        
        # 检查必需字段
        for field in required_fields:
            if field not in node_data:
                logger.error(f"Missing required field: {field}")
                raise ValueError(f"Missing required field: {field}")
        
        # 检查数据类型和范围
        if not isinstance(node_data['node_id'], str):
            raise ValueError("node_id must be a string")
        
        if not 0 <= node_data['initial_human_dependency'] <= 1:
            raise ValueError("initial_human_dependency must be between 0 and 1")
        
        if node_data['confidence_level'] not in self.CONFIDENCE_LEVELS:
            raise ValueError(f"confidence_level must be one of {list(self.CONFIDENCE_LEVELS.keys())}")
        
        try:
            datetime.fromisoformat(node_data['last_human_check'])
        except ValueError:
            raise ValueError("last_human_check must be a valid ISO format timestamp")
        
        if node_data['automated_checks'] < 0:
            raise ValueError("automated_checks cannot be negative")
        
        if node_data['error_count'] < 0:
            raise ValueError("error_count cannot be negative")
        
        logger.debug(f"Node data validation passed for node {node_data['node_id']}")
        return True
    
    def calculate_decay_rate(self, confidence_level: int, error_count: int) -> float:
        """
        根据置信度层级和错误计数计算动态衰减率
        
        参数:
            confidence_level: 当前置信度层级 (1-5)
            error_count: 错误计数
            
        返回:
            float: 计算出的衰减率
        """
        # 基础衰减率根据置信度层级调整
        level_factor = 1 + (confidence_level - 3) * 0.2  # 中等置信度为基准
        
        # 错误计数会降低衰减率（增加对人工的依赖）
        error_penalty = error_count * 0.05
        
        adjusted_rate = self.base_decay_rate * level_factor - error_penalty
        return max(0.01, min(adjusted_rate, 0.9))  # 限制在0.01-0.9之间
    
    def calculate_human_dependency(
        self, 
        initial_dependency: float, 
        automated_checks: int, 
        decay_rate: float
    ) -> float:
        """
        计算当前对人工复核的依赖度（指数衰减模型）
        
        参数:
            initial_dependency: 初始依赖度 (0-1)
            automated_checks: 成功的自动化检查次数
            decay_rate: 衰减率
            
        返回:
            float: 当前依赖度
        """
        if automated_checks <= 0:
            return initial_dependency
        
        # 指数衰减公式: dependency = initial * e^(-decay_rate * checks)
        current_dependency = initial_dependency * math.exp(-decay_rate * automated_checks)
        
        # 确保不低于最小值（完全自动化仍需保留最低限度的人工监督）
        return max(0.05, min(current_dependency, 1.0))
    
    def update_confidence_level(
        self, 
        current_level: int, 
        automated_checks: int, 
        error_count: int
    ) -> int:
        """
        根据自动化检查次数和错误计数更新置信度层级
        
        参数:
            current_level: 当前置信度层级 (1-5)
            automated_checks: 自动化检查次数
            error_count: 错误计数
            
        返回:
            int: 新的置信度层级
        """
        # 错误计数会降低置信度
        if error_count > 0:
            penalty = min(error_count, 2)  # 每个错误最多降2级
            new_level = max(1, current_level - penalty)
            logger.debug(f"Confidence level reduced from {current_level} to {new_level} due to {error_count} errors")
            return new_level
        
        # 无错误情况下，根据自动化检查次数提升置信度
        if automated_checks >= 20 and current_level < 5:
            logger.debug(f"Confidence level increased from {current_level} to {current_level + 1}")
            return current_level + 1
        elif automated_checks >= 10 and current_level < 4:
            logger.debug(f"Confidence level increased from {current_level} to {current_level + 1}")
            return current_level + 1
        
        return current_level
    
    def process_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个节点，应用衰减模型并返回更新后的状态
        
        参数:
            node_data: 包含节点数据的字典
            
        返回:
            Dict[str, Any]: 包含更新后节点状态的字典
            
        异常:
            ValueError: 当输入数据无效时
        """
        try:
            # 验证输入数据
            self.validate_node_data(node_data)
            
            # 提取数据
            node_id = node_data['node_id']
            initial_dependency = node_data['initial_human_dependency']
            confidence_level = node_data['confidence_level']
            last_human_check = datetime.fromisoformat(node_data['last_human_check'])
            automated_checks = min(node_data['automated_checks'], self.max_automated_checks)
            error_count = node_data['error_count']
            
            # 计算动态衰减率
            decay_rate = self.calculate_decay_rate(confidence_level, error_count)
            
            # 计算当前人工依赖度
            current_dependency = self.calculate_human_dependency(
                initial_dependency, automated_checks, decay_rate
            )
            
            # 更新置信度层级
            new_confidence_level = self.update_confidence_level(
                confidence_level, automated_checks, error_count
            )
            
            # 计算下次检查时间（基于当前依赖度）
            days_until_next_check = max(1, int(30 * (1 - current_dependency)))
            next_check = datetime.now() + timedelta(days=days_until_next_check)
            
            # 确定节点状态
            status = "stable"
            if error_count > 0:
                status = "error"
            elif current_dependency > 0.5:
                status = "needs_review"
            
            # 构建结果
            result = {
                "node_id": node_id,
                "current_human_dependency": round(current_dependency, 4),
                "confidence_level": new_confidence_level,
                "confidence_description": self.CONFIDENCE_LEVELS[new_confidence_level],
                "decay_rate": round(decay_rate, 4),
                "next_check_due": next_check.isoformat(),
                "status": status,
                "automated_checks": automated_checks,
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Processed node {node_id}: dependency={current_dependency:.2f}, level={new_confidence_level}, status={status}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing node {node_data.get('node_id', 'unknown')}: {str(e)}")
            raise
    
    def simulate_decay_over_time(
        self, 
        initial_node: Dict[str, Any], 
        time_steps: int = 30
    ) -> List[Dict[str, Any]]:
        """
        模拟节点随时间变化的衰减过程
        
        参数:
            initial_node: 初始节点数据
            time_steps: 模拟的时间步数（天）
            
        返回:
            List[Dict[str, Any]]: 模拟结果序列
        """
        results = []
        current_node = initial_node.copy()
        
        for day in range(time_steps):
            try:
                # 模拟每日自动化检查
                current_node['automated_checks'] += 1
                
                # 随机模拟错误（5%概率）
                import random
                if random.random() < 0.05:
                    current_node['error_count'] += 1
                
                # 处理节点
                result = self.process_node(current_node)
                results.append(result)
                
                # 更新节点状态用于下一步
                current_node['confidence_level'] = result['confidence_level']
                current_node['error_count'] = result.get('error_count', 0)
                
                logger.debug(f"Simulation day {day}: dependency={result['current_human_dependency']:.2f}")
                
            except Exception as e:
                logger.error(f"Simulation failed on day {day}: {str(e)}")
                break
        
        return results

# 使用示例
if __name__ == "__main__":
    # 示例节点数据
    example_node = {
        "node_id": "node_12345",
        "initial_human_dependency": 0.8,
        "confidence_level": 2,
        "last_human_check": "2023-01-01T00:00:00",
        "automated_checks": 5,
        "error_count": 0
    }
    
    # 创建验证器实例
    validator = DecayModelValidator(base_decay_rate=0.15, max_automated_checks=100)
    
    # 处理单个节点
    print("Processing single node:")
    result = validator.process_node(example_node)
    print(json.dumps(result, indent=2))
    
    # 模拟节点随时间变化
    print("\nSimulating decay over 30 days:")
    simulation_results = validator.simulate_decay_over_time(example_node, time_steps=30)
    
    # 打印部分结果
    for i, res in enumerate(simulation_results[::5]):  # 每5天打印一次
        print(f"Day {i*5}: Dependency={res['current_human_dependency']:.3f}, "
              f"Level={res['confidence_level']}, Status={res['status']}")