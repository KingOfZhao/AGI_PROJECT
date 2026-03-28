"""
模块名称: adaptive_cognitive_engine
功能描述: 实现自适应认知分层引擎，模拟人类注意力机制进行数据处理与决策。

该系统实现了双过程理论：
1. 快思考 (Bronze层): 低认知负荷场景下的直觉响应
2. 慢思考 (Silver层): 高价值/异常场景下的深度分析

典型用例:
    >>> engine = AdaptiveCognitiveEngine()
    >>> engine.process_data({"sensor_reading": 25.4, "priority": "low"})
    >>> engine.process_data({"sensor_reading": 150.0, "priority": "high"})

数据流说明:
    输入格式: Dict[str, Union[float, str, int]]
    输出格式: Dict[str, Union[float, str, Dict]]
"""

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CognitiveMode(Enum):
    """认知处理模式枚举"""
    FAST_THINKING = auto()  # Bronze层直觉处理
    DEEP_THINKING = auto()  # Silver层深度处理


@dataclass
class DataPayload:
    """数据载荷结构"""
    raw_data: Dict[str, Union[float, str, int]]
    timestamp: float
    priority: str = "normal"
    anomaly_score: float = 0.0


class AdaptiveCognitiveEngine:
    """
    自适应认知分层引擎核心类
    
    特性:
    - 动态认知负荷检测
    - 自动数据分层存储
    - 资源使用优化
    - 异常检测与处理
    """
    
    def __init__(self, 
                 bronze_capacity: int = 100,
                 silver_capacity: int = 50,
                 anomaly_threshold: float = 3.0):
        """
        初始化认知引擎
        
        参数:
            bronze_capacity: Bronze层最大容量
            silver_capacity: Silver层最大容量
            anomaly_threshold: 异常检测阈值(标准差倍数)
        """
        self.bronze_layer: List[DataPayload] = []
        self.silver_layer: List[DataPayload] = []
        self.bronze_capacity = bronze_capacity
        self.silver_capacity = silver_capacity
        self.anomaly_threshold = anomaly_threshold
        self._cognitive_load = 0.0
        self._last_cleanup = time.time()
        
        logger.info("Adaptive Cognitive Engine initialized with Bronze=%d, Silver=%d",
                   bronze_capacity, silver_capacity)

    def _calculate_anomaly_score(self, data: Dict[str, Union[float, str, int]]) -> float:
        """
        计算数据异常分数
        
        参数:
            data: 输入数据字典
            
        返回:
            float: 异常分数(基于Z-score)
            
        异常:
            ValueError: 当数据缺少数值字段时
        """
        numeric_fields = {k: v for k, v in data.items() 
                         if isinstance(v, (int, float))}
        
        if not numeric_fields:
            raise ValueError("No numeric fields found for anomaly detection")
            
        if len(self.bronze_layer) < 10:  # 不足样本时返回0
            return 0.0
            
        # 计算历史均值和标准差
        historical_values = []
        for payload in self.bronze_layer[-100:]:
            historical_values.extend(
                v for v in payload.raw_data.values() 
                if isinstance(v, (int, float))
            )
            
        if not historical_values:
            return 0.0
            
        mean = sum(historical_values) / len(historical_values)
        std_dev = math.sqrt(sum((x - mean)**2 for x in historical_values) / len(historical_values))
        
        # 计算当前数据的平均Z-score
        current_values = list(numeric_fields.values())
        avg_z_score = sum(abs(x - mean) for x in current_values) / (len(current_values) * std_dev) if std_dev > 0 else 0.0
        
        return avg_z_score

    def _manage_memory(self) -> None:
        """
        内存管理辅助函数
        
        实现类似记忆遗忘的机制:
        - 当Bronze层超过容量时，删除最旧的数据
        - 定期将高价值数据从Bronze提升到Silver
        """
        # Bronze层清理
        if len(self.bronze_layer) > self.bronze_capacity:
            removed_count = len(self.bronze_layer) - self.bronze_capacity
            self.bronze_layer = self.bronze_layer[-self.bronze_capacity:]
            logger.debug("Removed %d old entries from Bronze layer", removed_count)
            
        # Silver层清理
        if len(self.silver_layer) > self.silver_capacity:
            removed_count = len(self.silver_layer) - self.silver_capacity
            self.silver_layer = self.silver_layer[-self.silver_capacity:]
            logger.debug("Removed %d old entries from Silver layer", removed_count)
            
        # 定期数据提升 (每60秒)
        if time.time() - self._last_cleanup > 60:
            high_value_data = [
                payload for payload in self.bronze_layer 
                if payload.anomaly_score > self.anomaly_threshold * 0.5
            ]
            
            self.silver_layer.extend(high_value_data)
            self.bronze_layer = [
                payload for payload in self.bronze_layer 
                if payload.anomaly_score <= self.anomaly_threshold * 0.5
            ]
            
            logger.info("Promoted %d high-value items to Silver layer", len(high_value_data))
            self._last_cleanup = time.time()

    def process_data(self, raw_data: Dict[str, Union[float, str, int]]) -> Dict[str, Union[float, str, Dict]]:
        """
        主数据处理函数 - 核心认知分层逻辑
        
        参数:
            raw_data: 原始输入数据
            
        返回:
            Dict: 包含处理结果和元数据的字典
            
        异常:
            ValueError: 当输入数据无效时
            RuntimeError: 当处理过程中发生严重错误时
        """
        if not raw_data:
            raise ValueError("Empty input data is not allowed")
            
        try:
            # 数据验证
            if not isinstance(raw_data, dict):
                raise ValueError("Input must be a dictionary")
                
            # 创建数据载荷
            anomaly_score = self._calculate_anomaly_score(raw_data)
            priority = str(raw_data.get("priority", "normal")).lower()
            
            payload = DataPayload(
                raw_data=raw_data,
                timestamp=time.time(),
                priority=priority,
                anomaly_score=anomaly_score
            )
            
            # 认知模式选择
            mode = self._determine_cognitive_mode(payload)
            
            if mode == CognitiveMode.FAST_THINKING:
                # Bronze层处理 (快思考)
                self.bronze_layer.append(payload)
                result = self._fast_process(payload)
                logger.debug("Fast processed data with anomaly score %.2f", anomaly_score)
            else:
                # Silver层处理 (慢思考)
                self.silver_layer.append(payload)
                result = self._deep_process(payload)
                logger.info("Deep processed high-value data (score %.2f)", anomaly_score)
                
            # 内存管理
            self._manage_memory()
            
            return {
                "status": "processed",
                "mode": mode.name,
                "result": result,
                "metadata": {
                    "anomaly_score": anomaly_score,
                    "timestamp": payload.timestamp,
                    "layer": "bronze" if mode == CognitiveMode.FAST_THINKING else "silver"
                }
            }
            
        except Exception as e:
            logger.error("Data processing failed: %s", str(e), exc_info=True)
            raise RuntimeError(f"Processing error: {str(e)}") from e

    def _determine_cognitive_mode(self, payload: DataPayload) -> CognitiveMode:
        """
        确定认知处理模式
        
        参数:
            payload: 数据载荷
            
        返回:
            CognitiveMode: 选择的处理模式
        """
        # 高优先级或异常数据触发深度处理
        if (payload.priority in ("high", "critical") or 
            payload.anomaly_score > self.anomaly_threshold or
            self._cognitive_load > 0.7):  # 高认知负荷也触发深度思考
            return CognitiveMode.DEEP_THINKING
            
        return CognitiveMode.FAST_THINKING

    def _fast_process(self, payload: DataPayload) -> Dict[str, Union[float, str]]:
        """
        快思考处理逻辑
        
        参数:
            payload: 数据载荷
            
        返回:
            Dict: 快速处理结果
        """
        # 模拟直觉性模式匹配
        result = {
            "processing": "fast",
            "confidence": 0.7 + 0.3 * (1 - min(payload.anomaly_score, 10) / 10),
            "action": "normal_operation"
        }
        
        # 更新认知负荷
        self._cognitive_load = min(1.0, self._cognitive_load + 0.05)
        
        return result

    def _deep_process(self, payload: DataPayload) -> Dict[str, Union[float, str, Dict]]:
        """
        慢思考处理逻辑
        
        参数:
            payload: 数据载荷
            
        返回:
            Dict: 深度处理结果
        """
        # 模拟深度分析
        analysis = {
            "data_quality": "high" if payload.anomaly_score > self.anomaly_threshold else "medium",
            "recommended_action": "investigate" if payload.anomaly_score > self.anomaly_threshold * 1.5 else "monitor",
            "correlation": self._find_correlations(payload)
        }
        
        # 更新认知负荷 (深度处理消耗更多资源)
        self._cognitive_load = min(1.0, self._cognitive_load + 0.15)
        
        return {
            "processing": "deep",
            "confidence": 0.9,
            "analysis": analysis,
            "action": "special_attention"
        }

    def _find_correlations(self, current_payload: DataPayload) -> Dict[str, float]:
        """
        辅助函数: 在Silver层查找相关数据
        
        参数:
            current_payload: 当前数据载荷
            
        返回:
            Dict: 相似数据项及其相关度分数
        """
        correlations = {}
        current_numeric = {
            k: v for k, v in current_payload.raw_data.items() 
            if isinstance(v, (int, float))
        }
        
        for payload in self.silver_layer[-20:]:  # 检查最近的Silver层数据
            similarity = 0.0
            count = 0
            
            for k, v in payload.raw_data.items():
                if k in current_numeric and isinstance(v, (int, float)):
                    # 简单的相似度计算
                    max_val = max(abs(v), abs(current_numeric[k]), 1e-6)
                    similarity += 1 - abs(v - current_numeric[k]) / max_val
                    count += 1
                    
            if count > 0:
                avg_similarity = similarity / count
                if avg_similarity > 0.7:  # 只记录高相似度
                    correlations[f"entry_{id(payload)}"] = avg_similarity
                    
        return correlations


# 使用示例
if __name__ == "__main__":
    engine = AdaptiveCognitiveEngine(anomaly_threshold=2.5)
    
    # 模拟正常数据流 (快思考)
    for i in range(5):
        data = {"sensor_reading": 25.0 + i*0.1, "priority": "low"}
        result = engine.process_data(data)
        print(f"Result {i+1}: Mode={result['mode']}, Confidence={result['result']['confidence']:.2f}")
    
    # 模拟异常数据 (慢思考)
    anomaly_data = {"sensor_reading": 150.0, "priority": "high", "error_code": "E102"}
    result = engine.process_data(anomaly_data)
    print("\nAnomaly processing:")
    print(f"Mode: {result['mode']}")
    print(f"Action: {result['result']['action']}")
    print(f"Analysis: {result['result']['analysis']}")