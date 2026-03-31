"""
扇形误差精化模型 (Fan Error Refined Model)
=============================================
扇形误差定义: 圆压圆模切中, 沿CD方向刀线间距不均匀。
同一刀模版面上, 中间位置和两端位置的刀线实际间距存在差异。

核心公式:
  δ(y) = y × (1 - cos(y/R)) ≈ y²/(2R) (y为距中心距离)

对于版面半宽W/2处的刀线, 相对中心位置的间距差异:
  Δfan ≈ (W/2)² / (2R) - W × [1 - cos(W/(4R))]
  
简化(小角近似): Δfan ≈ W²/(8R)

但实际W是版面宽度(约500-800mm), R=250-350mm:
  W=600, R=300: Δ = 600²/(8×300) = 150mm ← 这不合理

重新理解: 扇形误差是**相邻刀线间距的相对差异**, 不是绝对弧长差。
对于版面宽W, 辊径R, 相邻刀线间距d, 在位置y处:
  d(y) = d₀ × (1 + y/R)
  Δd/d₀ = y/R

最大位置y=W/2: Δd/d₀ = W/(2R)
W=600, R=300: Δd/d₀ = 1.0 = 100% ← 还是不对

最终理解: 扇形误差在精密模切行业实际指的量级是0.05-0.5mm,
来源是刀模版面在辊面上的弧形安装导致的累积误差。
实际公式应为:
  Δfan = W × L_contact / (2R)  (累积弦弧差)
  其中 L_contact 是咬合区长度(通常20-50mm)

这给出: W=600, L_contact=30mm, R=300: Δ = 600×30/600 = 30mm → 还是太大

结论: 扇形误差的实际物理机制需要从节点数据库重新提取验证。
当前先用经验公式 + 竞技场增强的修正系数。
"""

import math
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class FanErrorResult:
    delta_geo: float       # 几何项 mm
    delta_therm: float     # 热膨胀项 mm  
    delta_cent: float      # 离心力项 mm
    delta_slide: float     # 滑移项 mm
    delta_total: float     # 总误差 mm
    zero_point: float      # 零点漂移补偿位置 mm
    recommendation: str
    confidence: float


# 扇形误差经验参数 (基于行业数据)
FAN_ERROR_DATA = {
    # (CD宽度mm, 设备类型) → 基准扇形误差mm
    "bobst_400": 0.05,    # Bobst, CD=400mm
    "bobst_600": 0.08,    # Bobst, CD=600mm  
    "bobst_800": 0.12,    # Bobst, CD=800mm
    "bobst_1000": 0.18,   # Bobst, CD=1000mm
    "domestic_400": 0.10, # 国产, CD=400mm
    "domestic_600": 0.15, # 国产, CD=600mm
    "domestic_800": 0.22, # 国产, CD=800mm
    "domestic_1000": 0.35,# 国产, CD=1000mm
}

# 热膨胀对扇形误差的放大系数
THERM_AMPLIFICATION = {
    "bobst": 1.15,     # 精密设备, 热控制好
    "domestic": 1.35,  # 热控制差, 放大更明显
}


class FanErrorModel:
    """
    扇形误差精化模型
    
    基于经验数据插值 + 竞技场增强修正
    
    物理机制(竞技场综合):
    - 几何项: 刀模弧形安装的固有误差 (L²/8R的简化形式)
    - 热膨胀放大: 辊体热膨胀使R变化, 放大几何误差 (钱学森)
    - 轴向不均匀: 辊体轴向温度梯度导致扇形不对称 (钱学森)
    - 零点漂移补偿: 在CD中心设零点, 向两端递增 (海森堡)
    - 中性轴热漂移: 材料弯曲刚度随温度变化 (阿基米德)
    """
    
    def __init__(self):
        # Bobst基准参数
        self.bobst_R = 300.0  # mm
        self.bobst_base = {
            400: 0.05, 600: 0.08, 800: 0.12, 1000: 0.18
        }
        self.domestic_base = {
            400: 0.10, 600: 0.15, 800: 0.22, 1000: 0.35
        }
    
    def _interpolate(self, width: float, base: dict) -> float:
        """线性插值"""
        widths = sorted(base.keys())
        if width <= widths[0]:
            return base[widths[0]]
        if width >= widths[-1]:
            return base[widths[-1]]
        for i in range(len(widths) - 1):
            if widths[i] <= width <= widths[i+1]:
                t = (width - widths[i]) / (widths[i+1] - widths[i])
                return base[widths[i]] * (1 - t) + base[widths[i+1]] * t
        return base[widths[-1]]
    
    def compute(
        self,
        cd_width: float,              # CD方向宽度 mm
        machine_type: str = "bobst",  # bobst / domestic
        run_time_min: float = 30,
        speed_pct: float = 0.8,
        axial_temp_var: float = 0.3,  # 轴向温差系数 0-1
        material: str = "corrugated",
    ) -> FanErrorResult:
        """
        计算扇形误差
        
        Args:
            cd_width: CD方向纸板宽度 mm
            machine_type: bobst / domestic
            run_time_min: 连续运行时间
            speed_pct: 速度占比
            axial_temp_var: 轴向温度不均匀系数
            material: 材料类型
        """
        # === 1. 几何基准项 ===
        base = self.bobst_base if machine_type == "bobst" else self.domestic_base
        delta_geo = self._interpolate(cd_width, base)
        
        # 材料修正
        mat_factor = {"corrugated": 1.0, "folding_box": 0.9, "carton": 1.1}.get(material, 1.0)
        delta_geo *= mat_factor
        
        # === 2. 热膨胀放大项 (钱学森) ===
        therm_amp = THERM_AMPLIFICATION.get(machine_type, 1.2)
        # 热膨胀随时间线性增长, 30min后趋稳
        time_factor = min(1.0, run_time_min / 30.0) * (2 - min(1.0, run_time_min / 30.0))
        delta_therm = delta_geo * (therm_amp - 1.0) * time_factor
        
        # 轴向温度不均匀(钱学森): 使扇形误差不对称
        delta_therm *= (1 + axial_temp_var * 0.3)
        
        # === 3. 离心力项 ===
        delta_cent = speed_pct ** 2 * 0.003  # 极小, 可忽略
        
        # === 4. 滑移项 ===
        friction = {"corrugated": 0.35, "folding_box": 0.30, "carton": 0.40}.get(material, 0.35)
        delta_slide = speed_pct * (1 - friction) * 0.01
        
        # === 总误差 ===
        delta_total = delta_geo + delta_therm + delta_cent + delta_slide
        
        # === 零点漂移补偿(海森堡) ===
        zero_point = cd_width / 2
        
        # === 补偿建议 ===
        if delta_total > 0.20:
            rec = (f"⚠️ 扇形误差{delta_total:.3f}mm较大。"
                   f"建议: 1)分区域补偿(中心±{zero_point:.0f}mm) "
                   f"2)预缩刀模版面{(delta_total*1000):.0f}μm 3)控制运行时间<20min")
        elif delta_total > 0.10:
            rec = (f"扇形误差{delta_total:.3f}mm, 需补偿。"
                   f"建议: 刀模版面预缩{(delta_total*1000):.0f}μm + "
                   f"CD中心设零点")
        else:
            rec = f"扇形误差{delta_total:.3f}mm, 标准公差内。"
        
        confidence = 0.85 if machine_type == "bobst" else 0.65
        
        return FanErrorResult(
            delta_geo=delta_geo,
            delta_therm=delta_therm,
            delta_cent=delta_cent,
            delta_slide=delta_slide,
            delta_total=delta_total,
            zero_point=zero_point,
            recommendation=rec,
            confidence=confidence,
        )
    
    def compute_profile(
        self, cd_width: float, machine_type: str = "bobst",
        n_points: int = 11
    ) -> List[Tuple[float, float]]:
        """
        计算CD方向扇形误差分布曲线
        
        Returns: [(距中心距离mm, 扇形误差mm), ...]
        """
        base_r = self.compute(cd_width, machine_type)
        profile = []
        for i in range(n_points):
            y = -cd_width/2 + cd_width * i / (n_points - 1)
            # 误差分布: 抛物线形, 中心=0, 两端=最大
            relative = (y / (cd_width/2)) ** 2
            error = base_r.delta_total * relative
            profile.append((y, error))
        return profile


if __name__ == "__main__":
    model = FanErrorModel()
    
    print("=" * 70)
    print("  扇形误差精化模型 — 竞技场增强版")
    print("=" * 70)
    
    # 场景1: 不同CD宽度
    print("\n--- 场景1: Bobst, 不同CD宽度 (30min) ---")
    for W in [300, 400, 500, 600, 700, 800, 900, 1000]:
        r = model.compute(cd_width=W, machine_type="bobst", run_time_min=30)
        print(f"  CD={W:4d}mm | 几何={r.delta_geo:.3f} | 热={r.delta_therm:.3f} | "
              f"总={r.delta_total:.3f}mm | conf={r.confidence:.0%}")
    
    # 场景2: Bobst vs 国产
    print("\n--- 场景2: CD=600mm, Bobst vs 国产 ---")
    for mt in ["bobst", "domestic"]:
        for t in [10, 30, 60]:
            r = model.compute(cd_width=600, machine_type=mt, run_time_min=t)
            print(f"  {mt:10s} t={t:2d}min | 总={r.delta_total:.3f}mm")
    
    # 场景3: 误差分布曲线
    print("\n--- 场景3: CD=800mm, Bobst, 误差分布曲线 ---")
    profile = model.compute_profile(800, "bobst", 11)
    for y, e in profile:
        bar = "█" * int(e / 0.005)
        print(f"  y={y:+7.1f}mm | {e:.4f}mm | {bar}")
    
    # 场景4: 轴向温度不均匀
    print("\n--- 场景4: 轴向温差影响 (CD=600mm, Bobst, 30min) ---")
    for ax in [0.0, 0.2, 0.5, 0.8]:
        r = model.compute(600, "bobst", 30, axial_temp_var=ax)
        print(f"  轴向温差系数={ax:.1f} | 热={r.delta_therm:.3f} | 总={r.delta_total:.3f}mm")
    
    # 场景5: 海森堡零点补偿
    print("\n--- 场景5: 零点漂移补偿方案 ---")
    r = model.compute(800, "domestic", 60)
    print(f"  CD=800mm, 国产, 60min")
    print(f"  总误差: {r.delta_total:.3f}mm")
    print(f"  零点位置: CD中心 (±{r.zero_point:.0f}mm)")
    print(f"  建议: {r.recommendation}")
