"""
monte_carlo_tolerance.py — 蒙特卡洛公差链累积分析

基于多工序误差传播的统计模拟，用于刀模多步骤加工的累积误差评估。

核心场景:
  原纸裁切 → 印刷 → 模切 → 糊盒
  每个工序贡献误差，通过MCS计算最终累积误差分布

整合自 skill 节点 3736b2 (公差链概率传播)
"""

import math
import random
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ProcessStep:
    """单工序误差定义"""
    name: str
    tolerance_mm: float          # 该工序的公差带 (±mm)
    distribution: str = "normal" # normal / uniform / triangular
    cpk: float = 1.0             # 过程能力指数
    bias_mm: float = 0.0         # 系统偏差 (mm)


@dataclass
class MCSResult:
    """蒙特卡洛模拟结果"""
    total_samples: int = 0
    mean_mm: float = 0.0         # 累积误差均值
    std_mm: float = 0.0          # 标准差
    min_mm: float = 0.0          # 最小值
    max_mm: float = 0.0          # 最大值
    p99_mm: float = 0.0          # 99th percentile
    p95_mm: float = 0.0          # 95th percentile
    rss_mm: float = 0.0          # RSS理论值 (对比用)
    rss_corrected_mm: float = 0.0  # RSS修正值 (k=1.15)
    pass_rate_015: float = 0.0   # ±0.15mm 合格率
    pass_rate_030: float = 0.0   # ±0.30mm 合格率
    pass_rate_custom: float = 0.0
    custom_tolerance: float = 0.0
    distribution_data: List[float] = field(default_factory=list)
    step_contributions: List[Dict[str, float]] = field(default_factory=list)


def run_tolerance_mcs(
    steps: List[ProcessStep],
    n_samples: int = 10000,
    target_tolerance: Optional[float] = None,
) -> MCSResult:
    """
    蒙特卡洛公差链累积模拟
    
    Args:
        steps: 工序列表 (每步的公差和分布)
        n_samples: 模拟次数 (默认50000)
        target_tolerance: 目标公差带 (mm), 用于计算合格率
    
    Returns:
        MCSResult: 模拟统计结果
    
    用法:
        steps = [
            ProcessStep("原纸裁切", 0.10, cpk=1.2),
            ProcessStep("印刷套印", 0.15, cpk=1.0),
            ProcessStep("模切", 0.20, cpk=1.0, bias_mm=0.02),
            ProcessStep("糊盒", 0.25, cpk=0.83),
        ]
        result = run_tolerance_mcs(steps, target_tolerance=0.5)
        print(f"累积误差 95%: ±{result.p95_mm:.3f}mm")
    """
    if not steps:
        return MCSResult()
    
    n = len(steps)
    total_errors = []
    step_errors = [[] for _ in range(n)]
    
    for _ in range(n_samples):
        cumulative = 0.0
        for i, step in enumerate(steps):
            # 生成单工序误差
            if step.distribution == "normal":
                # 基于 Cpk: sigma = tolerance / (3 * Cpk)
                sigma = step.tolerance_mm / (3 * max(step.cpk, 0.1))
                err = random.gauss(step.bias_mm, sigma)
            elif step.distribution == "triangular":
                # 三角分布
                a, b, c = -step.tolerance_mm, step.tolerance_mm, step.bias_mm
                err = random.triangular(a, b, c)
            else:  # uniform
                err = random.uniform(-step.tolerance_mm, step.tolerance_mm) + step.bias_mm
            
            step_errors[i].append(err)
            cumulative += err
        
        total_errors.append(cumulative)
    
    # 统计
    total_errors.sort()
    mean = sum(total_errors) / len(total_errors)
    variance = sum((x - mean) ** 2 for x in total_errors) / len(total_errors)
    std = math.sqrt(variance)
    
    # RSS 理论值 (假设独立正态)
    rss = math.sqrt(sum(s.tolerance_mm ** 2 for s in steps))
    rss_corrected = rss * 1.15  # DiePre 安全系数
    
    # Percentiles
    def percentile(data, p):
        idx = int(len(data) * p / 100)
        idx = min(idx, len(data) - 1)
        return data[idx]
    
    result = MCSResult(
        total_samples=n_samples,
        mean_mm=round(mean, 4),
        std_mm=round(std, 4),
        min_mm=round(total_errors[0], 4),
        max_mm=round(total_errors[-1], 4),
        p99_mm=round(abs(percentile(total_errors, 99.5)), 4),
        p95_mm=round(abs(percentile(total_errors, 97.5)), 4),
        rss_mm=round(rss, 4),
        rss_corrected_mm=round(rss_corrected, 4),
        custom_tolerance=target_tolerance or 0,
    )
    
    # 合格率计算
    for tol, attr in [(0.15, "pass_rate_015"), (0.30, "pass_rate_030")]:
        passed = sum(1 for x in total_errors if abs(x) <= tol)
        setattr(result, attr, round(passed / len(total_errors), 4))
    
    if target_tolerance:
        passed = sum(1 for x in total_errors if abs(x) <= target_tolerance)
        result.pass_rate_custom = round(passed / len(total_errors), 4)
    
    # 每步贡献度
    for i, step in enumerate(steps):
        step_std = math.sqrt(sum((x - sum(step_errors[i]) / len(step_errors[i])) ** 2 
                                  for x in step_errors[i]) / len(step_errors[i]))
        contribution_pct = (step_std ** 2 / max(variance, 1e-10)) * 100
        result.step_contributions.append({
            "name": step.name,
            "std_mm": round(step_std, 4),
            "contribution_pct": round(contribution_pct, 1),
            "bias_mm": step.bias_mm,
        })
    
    # 保留分布数据 (采样1000点用于绘图)
    if len(total_errors) > 1000:
        result.distribution_data = [round(total_errors[i], 4) 
                                     for i in range(0, len(total_errors), len(total_errors) // 1000)]
    
    return result


def compare_processes(
    nominal_mm: float,
    target_tolerance: float = 0.5,
) -> Dict[str, MCSResult]:
    """
    对比不同加工链路的累积误差
    
    Args:
        nominal_mm: 标称尺寸
        target_tolerance: 目标公差
    
    Returns:
        各工艺链路的MCS结果
    """
    # 尺寸越大, 误差越大 (线性缩放)
    scale = nominal_mm / 300.0
    
    chains = {
        "Bobst精密链": [
            ProcessStep("原纸裁切", 0.05 * scale, "normal", 1.33),
            ProcessStep("印刷套印", 0.08 * scale, "normal", 1.50),
            ProcessStep("Bobst模切", 0.15 * scale, "normal", 1.67),
            ProcessStep("自动糊盒", 0.10 * scale, "normal", 1.33),
        ],
        "国产标准链": [
            ProcessStep("原纸裁切", 0.10 * scale, "normal", 1.00),
            ProcessStep("印刷套印", 0.15 * scale, "normal", 1.00),
            ProcessStep("国产模切", 0.30 * scale, "normal", 1.00),
            ProcessStep("手工糊盒", 0.25 * scale, "uniform", 0.83),
        ],
        "混合链(Bobst模切+国产糊盒)": [
            ProcessStep("原纸裁切", 0.08 * scale, "normal", 1.17),
            ProcessStep("印刷套印", 0.12 * scale, "normal", 1.17),
            ProcessStep("Bobst模切", 0.15 * scale, "normal", 1.67),
            ProcessStep("手工糊盒", 0.25 * scale, "uniform", 0.83),
        ],
    }
    
    results = {}
    for name, steps in chains.items():
        results[name] = run_tolerance_mcs(steps, n_samples=5000, target_tolerance=target_tolerance)
    
    return results


if __name__ == "__main__":
    # 演示
    print("=== 刀模加工链蒙特卡洛模拟 ===\n")
    
    steps = [
        ProcessStep("原纸裁切", 0.10, "normal", 1.17, bias_mm=0.01),
        ProcessStep("印刷套印", 0.15, "normal", 1.00, bias_mm=0.02),
        ProcessStep("模切", 0.20, "normal", 1.00, bias_mm=-0.01),
        ProcessStep("糊盒", 0.25, "uniform", 0.83),
    ]
    
    result = run_tolerance_mcs(steps, n_samples=10000, target_tolerance=0.5)
    print(f"模拟次数: {result.total_samples}")
    print(f"累积误差均值: {result.mean_mm:.4f}mm")
    print(f"标准差: {result.std_mm:.4f}mm")
    print(f"95%分位: ±{result.p95_mm:.3f}mm")
    print(f"99%分位: ±{result.p99_mm:.3f}mm")
    print(f"RSS理论值: {result.rss_mm:.3f}mm")
    print(f"RSS修正(k=1.15): {result.rss_corrected_mm:.3f}mm")
    print(f"±0.15mm合格率: {result.pass_rate_015*100:.1f}%")
    print(f"±0.30mm合格率: {result.pass_rate_030*100:.1f}%")
    print(f"±0.50mm合格率: {result.pass_rate_custom*100:.1f}%")
    print(f"\n各工序贡献度:")
    for c in result.step_contributions:
        print(f"  {c['name']:12s} | σ={c['std_mm']:.4f}mm | 贡献={c['contribution_pct']:.1f}%")
    
    print("\n=== 工艺链对比 (300mm) ===")
    comparisons = compare_processes(300, target_tolerance=0.5)
    for name, r in comparisons.items():
        print(f"{name:35s} | 95%: ±{r.p95_mm:.3f}mm | RSS: {r.rss_mm:.3f}mm | ±0.3mm: {r.pass_rate_030*100:.1f}% | ±0.5mm: {r.pass_rate_custom*100:.1f}%")
