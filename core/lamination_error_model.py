"""
裱合工序误差模型 — 胶水收缩×纸张膨胀耦合
============================================
已知(F22): 裱合工序三耦合误差源
  1. 胶水固化收缩 (拉力, ~0.02-0.05%/干燥周期)
  2. 面纸吸湿膨胀 (推力, CD方向0.015-0.028%/1%RH)
  3. 张力控制差异 (裱合机进出纸速度差, ~0.02-0.05mm)

核心问题: RSS假设独立, 但胶水收缩与纸张膨胀方向可能叠加/抵消

物理模型:
  胶水固化 → 面纸局部MC升高 → 纸张膨胀
  干燥过程 → MC降低 → 纸张收缩
  两者方向相同(都导致收缩) → 叠加效应
  但时间尺度不同: 胶水固化(min级) vs MC平衡(h级)

结论: 不是简单相消, 是时序耦合
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class GlueType(Enum):
    """胶水类型"""
    STARCH = "淀粉胶"       # 最常用, 收缩率大
    PVA = "白乳胶"          # 收缩率中等
    HOTMELT = "热熔胶"      # 收缩率小, 快速固化
    POLYURETHANE = "聚氨酯"  # 收缩率最小, 高端


class CouplingDirection(Enum):
    """耦合方向"""
    ADDITIVE = "叠加"       # 同向, 误差放大
    PARTIAL_CANCEL = "部分抵消"  # 反向, 部分抵消
    INDEPENDENT = "独立"    # 正交方向, RSS适用


@dataclass
class LaminationResult:
    """裱合误差计算结果"""
    delta_glue: float        # 胶水收缩误差 mm
    delta_moisture: float    # MC膨胀误差 mm
    delta_tension: float     # 张力误差 mm
    delta_total: float       # 总误差 mm
    coupling_type: CouplingDirection
    coupling_factor: float   # 耦合系数 (1.0=完全叠加, 0.0=完全抵消)
    direction: str           # 主导方向: "MD" or "CD"
    confidence: float
    time_to_stable: float    # 稳定时间 hours


class LaminationErrorModel:
    """
    裱合误差模型
    
    三阶段时间模型:
    T0: 涂胶裱合 → 胶水湿润, 面纸MC急升
    T1: 固化期(0-4h) → 胶水收缩, MC开始下降
    T2: 稳定期(4-24h) → MC平衡, 尺寸稳定
    """
    
    # === 胶水收缩率 (%/干燥周期) ===
    GLUE_SHRINKAGE = {
        GlueType.STARCH:       {'rate': 0.05, 'time_h': 4, 'conf': 0.80},
        GlueType.PVA:          {'rate': 0.03, 'time_h': 6, 'conf': 0.85},
        GlueType.HOTMELT:      {'rate': 0.01, 'time_h': 0.5, 'conf': 0.90},
        GlueType.POLYURETHANE: {'rate': 0.015, 'time_h': 8, 'conf': 0.75},
    }
    
    # === 面纸膨胀系数 (%/1%RH) ===
    PAPER_EXPANSION = {
        'coated': {'cd': 0.028, 'md': 0.004, 'conf': 0.85},     # 铜版纸/涂布白板
        'kraft':  {'cd': 0.020, 'md': 0.003, 'conf': 0.80},     # 牛皮纸
        ' Ivory': {'cd': 0.015, 'md': 0.003, 'conf': 0.70},     # 白卡纸
    }
    
    # === 裱合纹理方向匹配规则 (R8) ===
    GRAIN_RULES = {
        'parallel': {
            'coupling': CouplingDirection.ADDITIVE,
            'factor': 1.0,
            'desc': '面纸∥灰板纹理 → 收缩方向一致 → 完全叠加',
        },
        'perpendicular': {
            'coupling': CouplingDirection.PARTIAL_CANCEL,
            'factor': 0.3,  # 喇叭口变形主导, 尺寸收缩被扭曲吸收
            'desc': '面纸⊥灰板纹理 → 喇叭口变形 → 尺寸误差部分转化为形变',
        },
        'unknown': {
            'coupling': CouplingDirection.ADDITIVE,
            'factor': 0.8,
            'desc': '纹理方向未知 → 保守假设叠加',
        },
    }
    
    def calculate(
        self,
        length_mm: float,
        direction: str = "CD",  # MD or CD
        face_paper: str = "coated",
        glue_type: GlueType = GlueType.STARCH,
        grain_match: str = "unknown",
        mc_start: float = 6.0,
        mc_target: float = 10.0,  # 裱合后面纸MC (胶水水分)
        mc_final: float = 8.0,     # 最终平衡MC
        machine_tension: float = 0.03,  # mm
        hours_after: float = 24.0,
    ) -> LaminationResult:
        """
        计算裱合误差
        
        Args:
            length_mm: 零件尺寸 mm
            direction: MD or CD
            face_paper: 面纸类型
            glue_type: 胶水类型
            grain_match: 纹理匹配 parallel/perpendicular/unknown
            mc_start: 裱合前面纸MC
            mc_target: 裱合后MC (胶水湿润后)
            mc_final: 最终平衡MC
            machine_tension: 张力误差 mm
            hours_after: 裱合后经过时间
        """
        # 1. 胶水收缩误差
        glue_info = self.GLUE_SHRINKAGE[glue_type]
        # 胶水收缩发生在固化期, 时间因子
        time_factor = min(1.0, hours_after / glue_info['time_h'])
        delta_glue = length_mm * glue_info['rate'] / 100 * time_factor
        
        # 2. MC膨胀误差 (两阶段)
        paper_info = self.PAPER_EXPANSION.get(face_paper, self.PAPER_EXPANSION['coated'])
        exp_coeff = paper_info['cd'] if direction == "CD" else paper_info['md']
        
        # 阶段1: MC急升 (涂胶时, 瞬时)
        mc_rise = mc_target - mc_start
        delta_expand = length_mm * exp_coeff * mc_rise / 100
        
        # 阶段2: MC回落 (干燥, 渐进)
        mc_drop = mc_target - mc_final
        stable_factor = min(1.0, hours_after / 24.0)  # 24h达到平衡
        delta_contract = length_mm * exp_coeff * mc_drop / 100 * stable_factor
        
        # 净MC误差 = 膨胀 - 收缩 (如果最终MC > 起始MC, 则净膨胀)
        delta_moisture = delta_expand - delta_contract
        
        # 3. 张力误差
        delta_tension = machine_tension
        
        # 4. 耦合分析
        grain_info = self.GRAIN_RULES.get(grain_match, self.GRAIN_RULES['unknown'])
        
        # 胶水收缩方向: 沿面纸CD方向 (面纸收缩)
        # MC膨胀方向: 沿面纸CD方向 (MC高时膨胀)
        # 净方向: 如果delta_moisture > 0(净膨胀) vs delta_glue > 0(收缩) → 部分抵消
        if delta_moisture > 0 and delta_glue > 0:
            # 膨胀 vs 收缩 → 部分抵消
            net = abs(delta_moisture - delta_glue)
            coupling_type = CouplingDirection.PARTIAL_CANCEL
            coupling_factor = 0.5 if grain_match == 'perpendicular' else 0.7
        else:
            # 同向 → 叠加
            net = abs(delta_moisture) + abs(delta_glue)
            coupling_type = grain_info['coupling']
            coupling_factor = grain_info['factor']
        
        delta_total = net * coupling_factor + delta_tension
        
        # 5. 稳定时间
        time_to_stable = max(glue_info['time_h'], 24.0)  # 取胶水固化时间和MC平衡时间的较大值
        
        # 6. 置信度
        conf = min(paper_info['conf'], glue_info['conf'])
        if grain_match == 'unknown':
            conf *= 0.8
        
        return LaminationResult(
            delta_glue=round(delta_glue, 3),
            delta_moisture=round(delta_moisture, 3),
            delta_tension=round(delta_tension, 3),
            delta_total=round(delta_total, 3),
            coupling_type=coupling_type,
            coupling_factor=round(coupling_factor, 2),
            direction=direction,
            confidence=round(conf, 2),
            time_to_stable=round(time_to_stable, 1),
        )
    
    def rss_integrate(self, lamination_result: LaminationResult, other_errors: list) -> float:
        """
        将裱合误差集成到RSS总误差中
        
        注意: 裱合误差不是简单RSS项, 需要乘以耦合系数
        """
        lam_sq = (lamination_result.delta_total * lamination_result.coupling_factor) ** 2
        other_sq = sum(e ** 2 for e in other_errors)
        return (lam_sq + other_sq) ** 0.5


# === 快捷函数 ===
_model = LaminationErrorModel()

def calc_lamination(length_mm, direction="CD", **kwargs) -> LaminationResult:
    return _model.calculate(length_mm, direction, **kwargs)


if __name__ == "__main__":
    print("=" * 65)
    print("  裱合误差模型 — 场景测试")
    print("=" * 65)
    
    scenarios = [
        ("标准场景: 300mm CD, 淀粉胶, 24h后", {
            'length_mm': 300, 'direction': 'CD', 'glue_type': GlueType.STARCH,
            'face_paper': 'coated', 'hours_after': 24,
        }),
        ("精密场景: 200mm CD, 聚氨酯, 48h后", {
            'length_mm': 200, 'direction': 'CD', 'glue_type': GlueType.POLYURETHANE,
            'face_paper': 'coated', 'hours_after': 48,
        }),
        ("灰板裱面纸: 500mm, 纹理垂直", {
            'length_mm': 500, 'direction': 'CD', 'glue_type': GlueType.STARCH,
            'face_paper': 'coated', 'grain_match': 'perpendicular', 'hours_after': 24,
        }),
        ("短时间: 100mm, 刚裱完1h", {
            'length_mm': 100, 'direction': 'CD', 'glue_type': GlueType.STARCH,
            'face_paper': 'coated', 'hours_after': 1,
        }),
        ("MD方向: 300mm MD", {
            'length_mm': 300, 'direction': 'MD', 'glue_type': GlueType.STARCH,
            'face_paper': 'coated', 'hours_after': 24,
        }),
    ]
    
    for name, kwargs in scenarios:
        r = _model.calculate(**kwargs)
        print(f"\n{name}")
        print(f"  胶水收缩: {r.delta_glue:.3f}mm | MC净膨胀: {r.delta_moisture:.3f}mm | 张力: {r.delta_tension:.3f}mm")
        print(f"  总误差: {r.delta_total:.3f}mm | 耦合: {r.coupling_type.value}(系数{r.coupling_factor}) | 置信度: {r.confidence:.0%}")
        print(f"  稳定时间: {r.time_to_stable:.0f}h")
    
    # RSS集成测试
    print(f"\n{'='*65}")
    print("  RSS集成测试")
    print(f"{'='*65}")
    r = _model.calculate(300, "CD")
    other = [0.15, 0.10, 0.08]  # 其他误差源
    rss_total = _model.rss_integrate(r, other)
    rss_naive = (sum(e**2 for e in other) + r.delta_total**2) ** 0.5
    print(f"  含裱合误差RSS: {rss_total:.3f}mm (耦合系数修正)")
    print(f"  天真RSS: {rss_naive:.3f}mm (假设独立)")
    print(f"  差异: {abs(rss_total - rss_naive):.3f}mm")
