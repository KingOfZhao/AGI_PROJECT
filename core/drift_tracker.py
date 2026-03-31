"""
drift_tracker.py — 刀模物理基准漂移追踪器

场景: 刀模在长时间运行中，刀具磨损、温度变化、纸张特性漂移等
导致实际精度偏离初始标定值。此模块通过时序数据自动检测和修正漂移。

核心算法:
  1. 滑动窗口MAE → 检测漂移趋势
  2. 相对漂移率 = |avg_error / baseline|
  3. 超过阈值时触发自动补偿
  4. 支持人机闭环确认

整合自 skill 节点 a2acd7 (物理基准漂移追踪器)
"""

import math
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class DriftResult:
    """单参数漂移检测结果"""
    parameter: str
    is_drifted: bool
    drift_score: float          # 相对漂移率 (0-1)
    abs_error_mm: float         # 绝对误差 (mm)
    suggested_correction: float # 建议补偿值 (mm)
    history_mean: float         # 滑动窗口均值
    history_std: float          # 滑动窗口标准差
    timestamp: float = 0.0


@dataclass
class DriftSummary:
    """整体漂移摘要"""
    total_params: int = 0
    drifted_params: int = 0
    max_drift_score: float = 0.0
    worst_param: str = ""
    corrections: Dict[str, float] = field(default_factory=dict)
    needs_human_review: bool = False


class DriftTracker:
    """
    刀模物理基准漂移追踪器
    
    追踪关键参数随时间的漂移:
    - 切割精度 (刀刃磨损)
    - 压痕深度 (钢线磨损/弹性疲劳)
    - 套印精度 (印刷机温漂)
    - 纸张MC变化 (环境湿度漂移)
    
    用法:
        tracker = DriftTracker({
            "cut_accuracy": 0.15,    # Bobst初始标定 ±0.15mm
            "crease_depth": 0.50,    # 压痕深度基准
            "register": 0.10,        # 套印精度
            "paper_mc": 8.0,         # 含水量基准 %
        })
        
        # 每次生产后输入实测值
        result = tracker.ingest({
            "cut_accuracy": 0.18,    # 实测偏差
            "crease_depth": 0.52,
            "register": 0.11,
            "paper_mc": 9.2,
        })
        
        if result.needs_human_review:
            print("需要人工确认补偿:", result.corrections)
    """
    
    def __init__(
        self,
        baseline_params: Dict[str, float],
        sensitivity_threshold: float = 0.05,
        window_size: int = 20,
        drift_confirm_count: int = 3,
    ):
        """
        Args:
            baseline_params: 参数基准值 {参数名: 基准值}
            sensitivity_threshold: 漂移报警阈值 (相对漂移率, 0.05=5%)
            window_size: 滑动窗口大小 (观测次数)
            drift_confirm_count: 连续N次漂移才确认 (避免噪声误报)
        """
        if not baseline_params:
            raise ValueError("baseline_params 不能为空")
        
        self.baselines = dict(baseline_params)
        self.threshold = sensitivity_threshold
        self.window_size = window_size
        self.confirm_count = drift_confirm_count
        
        self._windows: Dict[str, deque] = {
            k: deque(maxlen=window_size) for k in baseline_params
        }
        self._drift_counters: Dict[str, int] = {
            k: 0 for k in baseline_params
        }
        self._total_observations = 0
        self._correction_history: List[Dict] = []
    
    def ingest(
        self,
        observations: Dict[str, float],
        model_predictions: Optional[Dict[str, float]] = None,
    ) -> DriftSummary:
        """
        输入新观测值, 执行漂移分析
        
        Args:
            observations: 实测值 {参数名: 实测值}
            model_predictions: 理论预测值 (可选, 缺省用baseline)
        
        Returns:
            DriftSummary: 漂移摘要
        """
        self._total_observations += 1
        results: Dict[str, DriftResult] = {}
        
        for param, obs_val in observations.items():
            if param not in self.baselines:
                logger.warning(f"未知参数: {param}")
                continue
            
            # 计算误差
            expected = (model_predictions or {}).get(param, self.baselines[param])
            error = obs_val - expected
            self._windows[param].append(error)
            
            # 滑动窗口统计
            window = list(self._windows[param])
            n = len(window)
            mean_err = sum(window) / n
            variance = sum((x - mean_err) ** 2 for x in window) / n
            std_err = math.sqrt(variance)
            
            # 相对漂移率 (MC用绝对值+2%容差, 其他用相对值)
            baseline = self.baselines[param]
            if "mc" in param.lower():
                # 含水量: 绝对偏差 > 2% 才报警
                relative_drift = abs(mean_err) / 2.0
            else:
                norm_baseline = baseline if baseline != 0 else 1.0
                relative_drift = abs(mean_err / norm_baseline)
            
            is_drifted = relative_drift > self.threshold
            
            # 连续确认机制
            if is_drifted:
                self._drift_counters[param] += 1
                confirmed = self._drift_counters[param] >= self.confirm_count
            else:
                self._drift_counters[param] = 0
                confirmed = False
            
            results[param] = DriftResult(
                parameter=param,
                is_drifted=confirmed,
                drift_score=round(relative_drift, 4),
                abs_error_mm=round(mean_err, 4),
                suggested_correction=round(-mean_err, 4),  # 补偿 = -误差
                history_mean=round(mean_err, 4),
                history_std=round(std_err, 4),
                timestamp=time.time(),
            )
            
            if confirmed:
                logger.warning(f"⚠️ 漂移确认: {param} | 偏差={mean_err:.4f} | 漂移率={relative_drift:.2%}")
        
        # 汇总
        drifted = {k: v for k, v in results.items() if v.is_drifted}
        max_score = max((v.drift_score for v in results.values()), default=0)
        worst = max(results.items(), key=lambda x: x[1].drift_score, default=("", DriftResult("", False, 0, 0, 0, 0, 0)))
        
        corrections = {k: v.suggested_correction for k, v in drifted.items()}
        
        summary = DriftSummary(
            total_params=len(results),
            drifted_params=len(drifted),
            max_drift_score=max_score,
            worst_param=worst[0],
            corrections=corrections,
            needs_human_review=len(drifted) > 0,
        )
        
        if corrections:
            self._correction_history.append({
                "observation": self._total_observations,
                "corrections": corrections,
                "timestamp": time.time(),
            })
        
        return summary
    
    def get_trend(self, param: str) -> Dict[str, any]:
        """获取参数漂移趋势数据"""
        if param not in self._windows:
            return {"error": "unknown parameter"}
        
        window = list(self._windows[param])
        if not window:
            return {"error": "no data"}
        
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        
        # 趋势方向 (简单线性回归斜率)
        n = len(window)
        if n < 2:
            return {"values": window, "mean": mean, "trend": "insufficient_data"}
        
        x_mean = (n - 1) / 2
        slope = sum((i - x_mean) * (window[i] - mean) for i in range(n))
        slope /= sum((i - x_mean) ** 2 for i in range(n))
        
        trend = "increasing" if slope > 0.001 else ("decreasing" if slope < -0.001 else "stable")
        
        return {
            "parameter": param,
            "baseline": self.baselines[param],
            "values": window,
            "mean": round(mean, 4),
            "std": round(math.sqrt(variance), 4),
            "slope": round(slope, 6),
            "trend": trend,
            "observation_count": n,
        }
    
    def reset_param(self, param: str, new_baseline: Optional[float] = None):
        """重置参数 (人工校准后调用)"""
        if param in self._windows:
            self._windows[param].clear()
            self._drift_counters[param] = 0
            if new_baseline is not None:
                self.baselines[param] = new_baseline
                logger.info(f"参数 {param} 基准已更新为 {new_baseline}")


# ═══ 预置配置 ═══

BOBST_DRIFT_CONFIG = {
    "cut_accuracy": 0.15,     # 切割精度基准 (mm)
    "crease_depth": 0.50,     # 压痕深度 (mm)
    "crease_width": 1.20,     # 压痕宽度 (mm)
    "register_x": 0.10,       # X套印 (mm)
    "register_y": 0.10,       # Y套印 (mm)
    "paper_mc": 8.0,          # 含水量 (%)
    "blade_wear": 0.0,        # 刀刃磨损 (mm)
}

DOMESTIC_DRIFT_CONFIG = {
    "cut_accuracy": 0.30,
    "crease_depth": 0.55,
    "crease_width": 1.50,
    "register_x": 0.20,
    "register_y": 0.20,
    "paper_mc": 8.0,
    "blade_wear": 0.0,
}


if __name__ == "__main__":
    print("=== 刀模漂移追踪器演示 ===\n")
    
    tracker = DriftTracker(BOBST_DRIFT_CONFIG, sensitivity_threshold=0.08, drift_confirm_count=5)
    
    # 模拟100次生产, 刀具逐渐磨损
    print("模拟刀具磨损场景 (100次生产):\n")
    for i in range(100):
        wear = i * 0.002  # 每次生产磨损0.002mm
        noise = (i % 7 - 3) * 0.005  # 噪声
        
        obs = {
            "cut_accuracy": 0.15 + wear + noise,
            "crease_depth": 0.50 + wear * 0.3,
            "paper_mc": 8.0 + math.sin(i * 0.3) * 0.3,  # MC自然波动  # MC噪声更小
        }
        
        summary = tracker.ingest(obs)
        
        if summary.needs_human_review:
            print(f"  第{i+1:3d}次: ⚠️ 漂移! {summary.drifted_params}个参数 | "
                  f"最大漂移率: {summary.max_drift_score:.1%} | {summary.worst_param}")
            print(f"          建议补偿: {summary.corrections}")
            break
    
    # 趋势分析
    print(f"\n切割精度趋势:")
    trend = tracker.get_trend("cut_accuracy")
    print(f"  均值偏差: {trend['mean']:.4f}mm")
    print(f"  趋势方向: {trend['trend']}")
    print(f"  斜率: {trend['slope']:.6f} mm/次")
    
    print(f"\n含水量趋势:")
    mc_trend = tracker.get_trend("paper_mc")
    print(f"  均值偏差: {mc_trend['mean']:.4f}%")
    print(f"  趋势方向: {mc_trend['trend']}")
