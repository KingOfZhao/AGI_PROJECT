"""
清废临界角精化模型 (Stripper Angle Refined Model)
===================================================
竞技场增强: 钱学森(系统分层+设备耦合) + 冯诺依曼(状态机+断裂韧性) + 海森堡(不确定性冗余)

精化公式:
  θ = θ_base(t) + Δθ_speed(v) + Δθ_modulus(E) + Δθ_moisture(MC) + Δθ_blade

其中:
  θ_base(t) = 15° + 5° × ln(t)    [基础几何项, t=纸板厚度mm]
  Δθ_speed(v) = k_v × (v/v_ref)²  [速度补偿, 钱学森]
  Δθ_modulus(E) = k_E × (E_ref/E - 1) [模量补偿, 冯诺依曼]
  Δθ_moisture(MC) = k_mc × (MC - MC_ref) [含水补偿]
  Δθ_blade = k_blade × (1 - sharpness) [刀具锋利度补偿]
"""

import math
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class StripAngleResult:
    theta_base: float       # 基础角 °
    delta_speed: float      # 速度补偿 °
    delta_modulus: float    # 模量补偿 °
    delta_moisture: float   # 含水补偿 °
    delta_blade: float      # 刀具补偿 °
    theta_optimal: float    # 最优角 °
    theta_safe_min: float   # 安全下限 °
    theta_safe_max: float   # 安全上限 °
    recommendation: str
    confidence: float


# 材料断裂参数
MATERIAL_FRACTURE = {
    "corrugated_A": {"name": "A楞瓦楞", "t_range": (4.0, 5.5), "E": 1200, "Gc": 250, "k_v": 2.5},
    "corrugated_B": {"name": "B楞瓦楞", "t_range": (2.5, 3.5), "E": 1500, "Gc": 200, "k_v": 2.0},
    "corrugated_C": {"name": "C楞瓦楞", "t_range": (3.5, 4.5), "E": 1350, "Gc": 220, "k_v": 2.3},
    "corrugated_AB": {"name": "AB双瓦", "t_range": (6.5, 8.5), "E": 1000, "Gc": 300, "k_v": 3.0},
    "corrugated_E": {"name": "E微瓦楞", "t_range": (1.5, 2.0), "E": 2000, "Gc": 150, "k_v": 1.5},
    "corrugated_F": {"name": "F微瓦楞", "t_range": (0.8, 1.2), "E": 2500, "Gc": 120, "k_v": 1.2},
    "folding_box": {"name": "白卡纸", "t_range": (0.3, 0.5), "E": 3500, "Gc": 100, "k_v": 1.0},
    "folding_box_thick": {"name": "厚卡纸", "t_range": (0.5, 1.0), "E": 3000, "Gc": 130, "k_v": 1.3},
    "greyboard": {"name": "灰板", "t_range": (1.0, 3.0), "E": 2200, "Gc": 180, "k_v": 1.8},
    "kraft_liner": {"name": "牛皮纸", "t_range": (0.2, 0.4), "E": 4000, "Gc": 80, "k_v": 0.8},
}


class StripAngleModel:
    """清废临界角精化模型"""
    
    def __init__(self):
        self.v_ref = 150  # 参考速度 张/分
        self.E_ref = 2000  # 参考模量 MPa
        self.MC_ref = 10.0  # 参考含水量 %
        self.safety_margin = 1.5  # 海森堡: ±1.5°冗余
    
    def compute(
        self,
        material: str = "corrugated_B",
        thickness: float = 3.0,       # mm
        speed: float = 150,           # 张/分
        MC: float = 10.0,             # 含水量 %
        blade_sharpness: float = 0.9, # 0-1, 1=全新
    ) -> StripAngleResult:
        """
        计算最优清废角
        
        Args:
            material: 材料key (MATERIAL_FRACTURE)
            thickness: 纸板厚度 mm
            speed: 清废速度 张/分
            MC: 含水量 %
            blade_sharpness: 刀具锋利度 0-1
        """
        mat = MATERIAL_FRACTURE.get(material, MATERIAL_FRACTURE["corrugated_B"])
        
        # === 1. 基础几何项 ===
        theta_base = 15.0 + 5.0 * math.log(max(thickness, 0.1))
        
        # === 2. 速度补偿 (钱学森: 惯性力 ∝ v²) ===
        k_v = mat["k_v"]
        delta_speed = k_v * (speed / self.v_ref) ** 2
        
        # === 3. 模量补偿 (冯诺依曼: 断裂韧性接口) ===
        E = mat["E"]
        # MC对模量的影响: 每升1%MC, E降8% (钱学森)
        E_effective = E * (1 - 0.08 * (MC - self.MC_ref))
        E_effective = max(E_effective, E * 0.3)  # 下限: 30%原始模量
        
        k_E = 3.0  # 模量影响系数
        delta_modulus = k_E * (self.E_ref / E_effective - 1)
        
        # === 4. 含水补偿 ===
        # MC高→韧性增加→需要更大角度(废料不掉)
        k_mc = 0.5  # 每偏离1%MC补偿0.5°
        delta_moisture = k_mc * (MC - self.MC_ref)
        
        # === 5. 刀具锋利度补偿 ===
        # 钝刀→撕裂阻力增加→需要更大角度
        k_blade = 3.0  # 完全钝刀补偿3°
        delta_blade = k_blade * (1 - blade_sharpness)
        
        # === 最优角 ===
        theta_optimal = theta_base + delta_speed + delta_modulus + delta_moisture + delta_blade
        
        # === 安全区间 (海森堡: 不确定性冗余) ===
        # 速度越高, 不确定性越大, 安全区间越宽
        uncertainty = self.safety_margin * (1 + 0.3 * speed / self.v_ref)
        theta_safe_min = theta_optimal - uncertainty
        theta_safe_max = theta_optimal + uncertainty
        
        # === 建议 ===
        if theta_optimal > 30:
            rec = (f"⚠️ 最优角{theta_optimal:.1f}°偏大, 清废可能不净。"
                   f"建议: 1)降低速度 2)更换锋利刀具 3)控制MC<{MC-2:.0f}%")
        elif theta_optimal < 10:
            rec = (f"⚠️ 最优角{theta_optimal:.1f}°偏小, 有产品带出风险。"
                   f"安全下限{theta_safe_min:.1f}°, 注意监控")
        else:
            rec = (f"最优清废角{theta_optimal:.1f}° (安全区间{theta_safe_min:.1f}°~{theta_safe_max:.1f}°)。"
                   f"材料: {mat['name']}, 速度: {speed:.0f}张/分")
        
        confidence = 0.80 if material.startswith("corrugated") else 0.65
        
        return StripAngleResult(
            theta_base=theta_base,
            delta_speed=delta_speed,
            delta_modulus=delta_modulus,
            delta_moisture=delta_moisture,
            delta_blade=delta_blade,
            theta_optimal=theta_optimal,
            theta_safe_min=theta_safe_min,
            theta_safe_max=theta_safe_max,
            recommendation=rec,
            confidence=confidence,
        )
    
    def lookup_table(self, speed: float = 150, MC: float = 10.0) -> List[Tuple[str, float, float, float]]:
        """生成速查表"""
        results = []
        for key, mat in sorted(MATERIAL_FRACTURE.items()):
            t_mid = (mat["t_range"][0] + mat["t_range"][1]) / 2
            r = self.compute(material=key, thickness=t_mid, speed=speed, MC=MC)
            results.append((mat["name"], t_mid, r.theta_optimal, r.theta_safe_min, r.theta_safe_max))
        return results


if __name__ == "__main__":
    model = StripAngleModel()
    
    print("=" * 70)
    print("  清废临界角精化模型 — 竞技场增强版")
    print("=" * 70)
    
    # 场景1: 速查表
    print("\n--- 清废角速查表 (150张/分, MC=10%, 刀具新) ---")
    print(f"  {'材料':15s} | {'厚度mm':>6s} | {'最优角°':>7s} | {'安全区间°':>12s}")
    print(f"  {'-'*15} | {'-'*6} | {'-'*7} | {'-'*12}")
    for name, t, opt, lo, hi in model.lookup_table(150, 10):
        print(f"  {name:15s} | {t:6.1f} | {opt:7.1f} | {lo:.1f} ~ {hi:.1f}")
    
    # 场景2: 速度影响 (钱学森)
    print("\n--- 速度影响 (B楞, t=3mm, MC=10%) ---")
    for v in [80, 120, 150, 200, 250, 300]:
        r = model.compute("corrugated_B", 3.0, v)
        print(f"  v={v:3d}张/分 | θ={r.theta_optimal:.1f}° (Δv={r.delta_speed:+.1f}°) | "
              f"区间{r.theta_safe_min:.1f}°~{r.theta_safe_max:.1f}°")
    
    # 场景3: MC影响
    print("\n--- 含水量影响 (B楞, t=3mm, 150张/分) ---")
    for mc in [6, 8, 10, 12, 14, 16]:
        r = model.compute("corrugated_B", 3.0, 150, MC=mc)
        print(f"  MC={mc:2d}% | θ={r.theta_optimal:.1f}° (ΔMC={r.delta_moisture:+.1f}°, "
              f"E_eff={MATERIAL_FRACTURE['corrugated_B']['E']*(1-0.08*(mc-10)):.0f}MPa)")
    
    # 场景4: 刀具磨损
    print("\n--- 刀具锋利度影响 (B楞, t=3mm, 150张/分) ---")
    for s in [1.0, 0.8, 0.6, 0.4, 0.2]:
        r = model.compute("corrugated_B", 3.0, 150, blade_sharpness=s)
        label = "新刀" if s > 0.8 else ("良好" if s > 0.6 else ("磨损" if s > 0.4 else "严重磨损"))
        print(f"  锋利度={s:.1f} ({label:4s}) | θ={r.theta_optimal:.1f}° (Δblade={r.delta_blade:+.1f}°)")
    
    # 场景5: 海森堡不确定性区间
    print("\n--- 海森堡不确定性冗余 (不同速度下安全区间宽度) ---")
    for v in [100, 150, 200, 300]:
        r = model.compute("corrugated_B", 3.0, v)
        width = r.theta_safe_max - r.theta_safe_min
        print(f"  v={v:3d}张/分 | 最优={r.theta_optimal:.1f}° | "
              f"安全区间宽度={width:.1f}° (冗余±{width/2:.1f}°)")
PYEOF
