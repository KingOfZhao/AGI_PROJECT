import time
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanMachineSymbiosis")

class CognitiveState(Enum):
    """人类认知状态枚举"""
    RELAXED = "relaxed"
    FOCUSED = "focused"
    OVERLOADED = "overloaded"

@dataclass
class CognitiveDebt:
    """
    认知债务数据结构
    用于记录未被人类验证的假设性操作
    """
    hypothesis_id: str
    created_at: float
    decay_factor: float = 1.0
    verification_status: Optional[bool] = None
    confidence: float = 0.8
    metadata: Dict = field(default_factory=dict)

@dataclass
class BiometricSignal:
    """
    生物特征信号数据结构
    用于实时监测人类状态
    """
    timestamp: float
    correction_rate: float  # 修正频率 (0.0-1.0)
    response_delay: float  # 响应延迟 (秒)
    eye_tracking_variance: Optional[float] = None  # 眼动追踪方差
    stress_level: Optional[float] = None  # 压力水平 (0.0-1.0)

class AdaptiveBuffer:
    """
    人机协作时间差与认知差自适应缓冲系统
    
    功能特点：
    1. 时间弹性管理：通过认知暂存、概率衰减和认知债务账本处理验证延迟
    2. 认知弹性调整：根据人类生理指标动态调整信息密度
    3. 动态平衡维护：量化预测与实际偏差，保持交互闭环稳定
    
    使用示例：
    >>> buffer = AdaptiveBuffer()
    >>> # 添加认知债务
    >>> buffer.add_cognitive_debt("hyp_001", {"action": "predict_next_word", "context": "..."})
    >>> # 处理人类信号
    >>> signal = BiometricSignal(time.time(), 0.2, 1.5, 0.1, 0.3)
    >>> new_density = buffer.process_human_signal(signal)
    >>> print(f"调整后信息密度: {new_density}")
    """
    
    def __init__(self, max_debt_age: float = 30.0, base_decay_rate: float = 0.05):
        """
        初始化自适应缓冲系统
        
        Args:
            max_debt_age: 认知债务最大存活时间(秒)
            base_decay_rate: 基础衰减率
        """
        self.max_debt_age = max_debt_age
        self.base_decay_rate = base_decay_rate
        self.cognitive_debts: Dict[str, CognitiveDebt] = {}
        self.current_info_density = 1.0  # 1.0表示标准密度
        self.human_state = CognitiveState.RELAXED
        self._last_interaction_time = time.time()
        
        # 边界检查
        if max_debt_age <= 0:
            raise ValueError("max_debt_age必须大于0")
        if not 0 <= base_decay_rate <= 1:
            raise ValueError("base_decay_rate必须在0到1之间")
            
        logger.info("AdaptiveBuffer initialized with max_debt_age=%.1f, decay_rate=%.2f", 
                   max_debt_age, base_decay_rate)

    def add_cognitive_debt(self, hypothesis_id: str, metadata: Optional[Dict] = None) -> None:
        """
        添加新的认知债务
        
        Args:
            hypothesis_id: 假设ID
            metadata: 与假设相关的元数据
            
        Raises:
            ValueError: 如果hypothesis_id已存在
        """
        if hypothesis_id in self.cognitive_debts:
            raise ValueError(f"假设ID {hypothesis_id} 已存在")
            
        debt = CognitiveDebt(
            hypothesis_id=hypothesis_id,
            created_at=time.time(),
            metadata=metadata or {}
        )
        
        self.cognitive_debts[hypothesis_id] = debt
        logger.debug("添加认知债务: %s", hypothesis_id)
        self._cleanup_debts()

    def verify_debt(self, hypothesis_id: str, status: bool) -> None:
        """
        验证认知债务
        
        Args:
            hypothesis_id: 假设ID
            status: 验证结果(True=接受, False=拒绝)
            
        Raises:
            KeyError: 如果hypothesis_id不存在
        """
        if hypothesis_id not in self.cognitive_debts:
            raise KeyError(f"假设ID {hypothesis_id} 不存在")
            
        debt = self.cognitive_debts[hypothesis_id]
        debt.verification_status = status
        
        # 根据验证结果调整衰减因子
        if status:
            debt.decay_factor *= 0.9  # 接受后快速衰减
        else:
            debt.decay_factor *= 1.2  # 拒绝后缓慢衰减
            
        logger.info("验证债务 %s: %s, 新衰减因子: %.2f", 
                   hypothesis_id, "接受" if status else "拒绝", debt.decay_factor)

    def process_human_signal(self, signal: BiometricSignal) -> float:
        """
        处理人类生物信号并调整信息密度
        
        Args:
            signal: 生物特征信号
            
        Returns:
            调整后的信息密度值
        """
        # 数据验证
        if not 0 <= signal.correction_rate <= 1:
            raise ValueError("修正频率必须在0到1之间")
        if signal.response_delay < 0:
            raise ValueError("响应延迟不能为负")
            
        # 更新交互时间
        self._last_interaction_time = signal.timestamp
        
        # 计算认知负载
        load = self._calculate_cognitive_load(signal)
        
        # 动态调整信息密度
        self._adjust_info_density(load)
        
        logger.info("处理人类信号 - 认知负载: %.2f, 新信息密度: %.2f, 状态: %s", 
                   load, self.current_info_density, self.human_state.value)
        
        return self.current_info_density

    def get_debt_status(self) -> List[Dict]:
        """
        获取所有认知债务的状态
        
        Returns:
            包含所有债务状态的字典列表
        """
        self._cleanup_debts()
        return [{
            "id": debt.hypothesis_id,
            "age": time.time() - debt.created_at,
            "decay": debt.decay_factor,
            "status": debt.verification_status,
            "confidence": debt.confidence
        } for debt in self.cognitive_debts.values()]

    def _calculate_cognitive_load(self, signal: BiometricSignal) -> float:
        """
        计算当前认知负载 (辅助函数)
        
        Args:
            signal: 生物特征信号
            
        Returns:
            认知负载指数 (0.0-1.0)
        """
        # 基础负载计算
        correction_load = signal.correction_rate * 0.4
        delay_load = min(signal.response_delay / 5.0, 1.0) * 0.3
        
        # 可选信号处理
        stress_load = 0.0
        eye_load = 0.0
        
        if signal.stress_level is not None:
            if not 0 <= signal.stress_level <= 1:
                raise ValueError("压力水平必须在0到1之间")
            stress_load = signal.stress_level * 0.2
            
        if signal.eye_tracking_variance is not None:
            if signal.eye_tracking_variance < 0:
                raise ValueError("眼动方差不能为负")
            eye_load = min(signal.eye_tracking_variance / 0.5, 1.0) * 0.1
            
        total_load = correction_load + delay_load + stress_load + eye_load
        return min(max(total_load, 0.0), 1.0)

    def _adjust_info_density(self, cognitive_load: float) -> None:
        """
        根据认知负载调整信息密度 (核心函数)
        
        Args:
            cognitive_load: 认知负载指数
        """
        # 确定认知状态
        if cognitive_load < 0.3:
            self.human_state = CognitiveState.RELAXED
        elif cognitive_load < 0.7:
            self.human_state = CognitiveState.FOCUSED
        else:
            self.human_state = CognitiveState.OVERLOADED
            
        # 动态调整信息密度
        if self.human_state == CognitiveState.OVERLOADED:
            # 过载时大幅降低密度
            self.current_info_density = max(0.3, self.current_info_density - 0.2)
        elif self.human_state == CognitiveState.FOCUSED:
            # 专注时微调
            self.current_info_density = max(0.7, min(1.0, self.current_info_density - 0.05))
        else:
            # 放松时可以增加密度
            self.current_info_density = min(1.5, self.current_info_density + 0.1)

    def _cleanup_debts(self) -> None:
        """
        清理过期或已验证的认知债务 (内部方法)
        """
        now = time.time()
        expired = []
        
        for debt_id, debt in self.cognitive_debts.items():
            age = now - debt.created_at
            
            # 应用时间衰减
            debt.decay_factor *= math.exp(-self.base_decay_rate * age / self.max_debt_age)
            
            # 检查是否过期
            if age > self.max_debt_age or debt.decay_factor < 0.01:
                expired.append(debt_id)
                
        # 移除过期债务
        for debt_id in expired:
            debt = self.cognitive_debts.pop(debt_id)
            logger.debug("移除过期债务 %s (年龄: %.1fs, 衰减: %.2f)", 
                        debt_id, now - debt.created_at, debt.decay_factor)

if __name__ == "__main__":
    # 使用示例
    buffer = AdaptiveBuffer(max_debt_age=60.0)
    
    # 添加认知债务
    buffer.add_cognitive_debt("hyp_001", {"content": "预测用户下一个操作是保存文件"})
    buffer.add_cognitive_debt("hyp_002", {"content": "预测用户需要数据可视化建议"})
    
    # 模拟人类验证延迟
    time.sleep(2)
    
    # 验证第一个债务
    buffer.verify_debt("hyp_001", True)
    
    # 处理人类信号
    signal = BiometricSignal(
        timestamp=time.time(),
        correction_rate=0.15,
        response_delay=1.2,
        stress_level=0.3
    )
    new_density = buffer.process_human_signal(signal)
    
    # 检查状态
    print("\n认知债务状态:")
    for status in buffer.get_debt_status():
        print(f"- {status['id']}: 年龄={status['age']:.1f}s, 衰减={status['decay']:.2f}")
    
    print(f"\n当前信息密度: {new_density:.2f}")
    print(f"人类认知状态: {buffer.human_state.value}")