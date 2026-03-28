"""
Module: dynamic_ecosystem_equilibrium.py
Description: 构建动态生态系统均衡模型，将市场均衡视为动态波动区间而非静态点。
             融合生态学演替理论，实时监测市场拥挤效应与资源枯竭信号，
             预测市场红海爆发点，并提供生态位分化的转型路径。
Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from pydantic import BaseModel, Field, ValidationError, field_validator

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 数据模型定义 ---

class MarketState(BaseModel):
    """市场当前状态的数据模型"""
    timestamp: int = Field(..., description="Unix时间戳或时间步长")
    total_market_size: float = Field(..., gt=0, description="市场总容量/总流量")
    competitor_count: int = Field(..., ge=1, description="当前竞争对手数量")
    avg_profit_margin: float = Field(..., ge=-1, le=1, description="行业平均利润率")
    resource_utilization: float = Field(..., ge=0, le=1, description="资源利用率 (0-1)")

    @field_validator('avg_profit_margin')
    def check_margin(cls, v):
        if v < -0.5:
            logger.warning("Detected catastrophic negative profit margins.")
        return v


class EcosystemConfig(BaseModel):
    """模型超参数配置"""
    carrying_capacity_alpha: float = Field(1.5, description="拥挤效应的敏感度系数")
    collapse_threshold: float = Field(0.85, description="系统崩溃/红海预警的拥挤阈值")
    differentiation_threshold: float = Field(0.75, description="建议生态位分化的触发阈值")


# --- 核心功能类 ---

class DynamicEcosystemEquilibrium:
    """
    动态生态系统均衡模型核心类。
    
    该类不使用静态的供需曲线交点，而是使用逻辑斯谛增长模型和
    捕食者-猎物方程的变体来模拟市场竞争动态。
    """

    def __init__(self, config: Optional[EcosystemConfig] = None):
        """
        初始化模型。
        
        Args:
            config (EcosystemConfig, optional): 模型配置参数。如果为None，使用默认配置。
        """
        self.config = config if config else EcosystemConfig()
        self.history: List[MarketState] = []
        logger.info("Dynamic Ecosystem Equilibrium Model initialized with config: %s", self.config.model_dump_json())

    def _validate_input_data(self, data: Union[Dict, MarketState]) -> MarketState:
        """
        辅助函数：验证输入数据并将其转换为MarketState对象。
        
        Args:
            data (Union[Dict, MarketState]): 原始输入数据。
            
        Returns:
            MarketState: 验证后的状态对象。
            
        Raises:
            ValueError: 如果数据验证失败。
        """
        try:
            if isinstance(data, MarketState):
                return data
            return MarketState(**data)
        except ValidationError as e:
            logger.error(f"Input data validation failed: {e}")
            raise ValueError(f"Invalid market data provided: {e}")

    def calculate_crowding_index(self, current_state: MarketState) -> float:
        """
        核心函数1: 计算市场拥挤指数。
        
        基于生态学中的'拥挤效应'，当种群密度增加时，个体增长速率下降。
        这里结合资源利用率和竞争者数量来量化市场的'拥挤'程度。
        
        公式构思: CI = (N / K) * (R_util ^ alpha)
        其中 N: 竞争者, K: 隐含承载力, R_util: 资源利用率
        
        Args:
            current_state (MarketState): 当前市场快照。
            
        Returns:
            float: 拥挤指数 (0.0 到 1.0+).
        """
        logger.debug(f"Calculating crowding index for timestamp {current_state.timestamp}")
        
        # 简单的承载力估算：假设资源利用率达到100%时的竞争者数量为理想最大值
        # 这里引入一个非线性调整，避免除零错误
        implied_capacity = current_state.competitor_count / (current_state.resource_utilization + 1e-6)
        
        # 标准化拥挤度
        density = current_state.competitor_count / max(implied_capacity, current_state.competitor_count)
        
        # 引入资源枯竭的加速因子
        crowding = density * (current_state.resource_utilization ** self.config.carrying_capacity_alpha)
        
        # 边界检查
        crowding = np.clip(crowding, 0.0, 1.5) # 允许超过1.0以表示过载
        
        logger.info(f"Crowding Index calculated: {crowding:.4f}")
        return crowding

    def analyze_market_dynamics(self, data_stream: List[Union[Dict, MarketState]]) -> Dict[str, Union[float, str, List[float]]]:
        """
        核心函数2: 分析市场动态并生成均衡预测与策略。
        
        处理时间序列数据，计算波动率，预测红海临界点，并提供转型建议。
        
        Args:
            data_stream (List[Union[Dict, MarketState]]): 市场状态的时间序列列表。
            
        Returns:
            Dict: 包含以下键的字典:
                - 'trend': str ('stable', 'warning', 'critical')
                - 'avg_crowding': float
                - 'volatility': float (市场震荡程度)
                - 'suggestion': str (基于生态位分化的策略建议)
                - 'forecast': float (下一时刻拥挤度预测)
        """
        if not data_stream:
            logger.error("Input data stream is empty.")
            return {"error": "Empty data stream"}

        validated_states = []
        for item in data_stream:
            try:
                state = self._validate_input_data(item)
                validated_states.append(state)
            except ValueError:
                continue # 跳过无效数据，或者根据需求停止

        if len(validated_states) < 2:
            logger.warning("Insufficient data for trend analysis (need at least 2 points).")
            return {"error": "Insufficient data"}

        # 计算历史拥挤度序列
        crowding_indices = [self.calculate_crowding_index(s) for s in validated_states]
        avg_crowding = np.mean(crowding_indices)
        
        # 计算波动率 (模拟生态系统的稳定性)
        volatility = np.std(crowding_indices)
        
        # 简单的趋势预测 (使用线性外推)
        x = np.arange(len(crowding_indices))
        y = np.array(crowding_indices)
        try:
            slope, _ = np.polyfit(x, y, 1)
            forecast = crowding_indices[-1] + slope
        except Exception:
            forecast = crowding_indices[-1]

        # 状态判定与策略生成
        trend_status = "stable"
        suggestion = "维持现状，优化效率。"

        if avg_crowding > self.config.collapse_threshold:
            trend_status = "critical"
            suggestion = (
                "警报：生态系统接近崩溃点（红海）。"
                "立即停止在当前维度的投入。"
                "建议实施'生态位分化'策略：寻找未被利用的资源维度（细分市场）或开发新物种（新产品线）。"
            )
            logger.warning(f"CRITICAL: Market crowding {avg_crowding:.2f} exceeds threshold.")
        elif avg_crowding > self.config.differentiation_threshold:
            trend_status = "warning"
            suggestion = (
                "警告：市场趋于饱和，边际收益递减。"
                "建议准备转型，探索差异化竞争路径，避免同质化竞争。"
            )
            logger.info(f"WARNING: Market approaching saturation at {avg_crowding:.2f}.")
        
        return {
            "trend": trend_status,
            "avg_crowding": float(avg_crowding),
            "volatility": float(volatility),
            "suggestion": suggestion,
            "forecast": float(forecast)
        }

# --- 使用示例 ---

if __name__ == "__main__":
    # 模拟一个随着时间推移变得拥挤的市场数据
    mock_data = [
        {"timestamp": 1, "total_market_size": 1000, "competitor_count": 5, "avg_profit_margin": 0.5, "resource_utilization": 0.2},
        {"timestamp": 2, "total_market_size": 1200, "competitor_count": 10, "avg_profit_margin": 0.45, "resource_utilization": 0.3},
        {"timestamp": 3, "total_market_size": 1250, "competitor_count": 20, "avg_profit_margin": 0.30, "resource_utilization": 0.5},
        {"timestamp": 4, "total_market_size": 1300, "competitor_count": 40, "avg_profit_margin": 0.15, "resource_utilization": 0.8},
        {"timestamp": 5, "total_market_size": 1300, "competitor_count": 60, "avg_profit_margin": 0.05, "resource_utilization": 0.95}, # 接近崩溃
    ]

    # 初始化模型
    model = DynamicEcosystemEquilibrium()
    
    # 执行分析
    try:
        result = model.analyze_market_dynamics(mock_data)
        
        print("\n--- Analysis Report ---")
        print(f"Status: {result.get('trend')}")
        print(f"Avg Crowding: {result.get('avg_crowding'):.4f}")
        print(f"Forecast: {result.get('forecast'):.4f}")
        print(f"Strategy: {result.get('suggestion')}")
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")