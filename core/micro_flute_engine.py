"""
微瓦楞(E/F/EF)刀模参数引擎
============================
从1562个已确认节点中提取106条微瓦楞数据，建立精确参数模型。

核心发现:
1. FEFCO公式 W=1.5t 对微瓦楞无效(槽宽过宽)
2. 需采用修正公式 W = (t + C_res) × K_stru
3. GB标准在微瓦楞领域完全缺失
4. JIS标准最严(注重折痕美观), 差异≥0.2mm vs FEFCO
5. Bobst/Heidelberg微瓦楞专用: 咬口8mm, 精度±0.10-0.15mm

已知(F): F27(不可套FEFCO), F28(JIS优势)
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class Standard(Enum):
    """标准体系"""
    FEFCO = "FEFCO"    # 欧洲, 侧重物流适配
    JIS = "JIS"        # 日本, 侧重精细外观
    GB = "GB"          # 中国, 侧重生产可行性
    DIN = "DIN"        # 德国, 侧重机械加工适配
    DIEPRE = "DIEPRE"  # DiePre综合修正版


class MicroFluteType(Enum):
    """微瓦楞楞型"""
    E = "E"   # 厚度 1.1-1.6mm, 楞高 ~1.8mm
    F = "F"   # 厚度 0.6-1.0mm, 楞高 ~1.2mm
    N = "N"   # 超微瓦楞, 厚度 ~0.5mm
    EF = "EF" # 双微瓦楞, 厚度 1.8-2.3mm


@dataclass
class MicroFluteParams:
    """微瓦楞完整参数集"""
    flute: MicroFluteType
    thickness: float          # 标称厚度 mm
    thickness_range: Tuple[float, float]  # 实际范围 mm
    groove_width: float       # 槽宽 W mm
    crease_depth: float       # 压痕深度 d mm
    crease_depth_ratio: float # d/T 比
    k_factor: float           # 中性轴系数
    mc_standard: float        # 标准含水率 %
    mc_tolerance: float       # MC兼容范围 %
    cd_expansion: float       # CD方向膨胀系数 %/1%RH
    md_expansion: float       # MD方向膨胀系数 %/1%RH
    folding_tolerance: float  # 折叠精度 mm
    bite_margin: float        # 咬口余量 mm
    standard: Standard        # 适用标准
    warnings: list            # 警告列表


class MicroFluteEngine:
    """
    微瓦楞参数引擎
    
    数据来源: 106条微瓦楞节点 (all_confirmed_knowledge.txt)
    覆盖: E/F/N/EF 四种楞型 × 5种标准体系
    
    关键公式:
    - FEFCO(粗瓦楞): W = 1.5t → 对微瓦楞无效
    - FEFCO(微瓦楞): W = t + 1.0 (偏宽)
    - JIS(微瓦楞): W = t + 0.5 (偏窄, 最严)
    - DiePre修正:   W = (t + C_res) × K_stru
    """
    
    # === E楞参数 ===
    E_PARAMS = {
        'thickness': 1.5,
        'thickness_range': (1.1, 1.6),
        'k_factor': 0.42,
        'mc_standard': 8.0,
        'cd_expansion': 0.10,     # %/1%RH
        'md_expansion': 0.02,     # %/1%RH (极小)
        'folding_tolerance': 0.30,
    }
    
    # === F楞参数 ===
    F_PARAMS = {
        'thickness': 0.8,
        'thickness_range': (0.6, 1.0),
        'k_factor': 0.45,
        'mc_standard': 8.0,
        'cd_expansion': 0.08,
        'md_expansion': 0.015,
        'folding_tolerance': 0.20,
    }
    
    # === N楞参数(超微) ===
    N_PARAMS = {
        'thickness': 0.5,
        'thickness_range': (0.4, 0.6),
        'k_factor': 0.48,
        'mc_standard': 7.5,
        'cd_expansion': 0.06,
        'md_expansion': 0.01,
        'folding_tolerance': 0.15,
    }
    
    # === EF双微瓦楞 ===
    EF_PARAMS = {
        'thickness': 2.0,
        'thickness_range': (1.8, 2.3),
        'k_factor': 0.40,
        'mc_standard': 8.0,
        'cd_expansion': 0.12,
        'md_expansion': 0.025,
        'folding_tolerance': 0.35,
    }
    
    # === 标准修正系数 ===
    STANDARD_CORRECTION = {
        Standard.FEFCO: {'C_res': 1.0, 'K_stru': 1.0, 'depth_ratio': 0.50},   # W = (t+1.0)×1.0
        Standard.JIS:   {'C_res': 0.5, 'K_stru': 1.0, 'depth_ratio': 0.45},   # W = (t+0.5)×1.0 (最严)
        Standard.GB:    {'C_res': 1.2, 'K_stru': 1.05, 'depth_ratio': 0.55},  # W = (t+1.2)×1.05 (最宽)
        Standard.DIN:   {'C_res': 0.8, 'K_stru': 1.0, 'depth_ratio': 0.48},   # W = (t+0.8)×1.0
        Standard.DIEPRE: {'C_res': 0.8, 'K_stru': 1.2, 'depth_ratio': 0.40},  # DiePre修正: 偏保守
    }
    
    # === 设备咬口余量 ===
    BITE_MARGIN = {
        'bobst': 8.0,        # Bobst SP系列: 8mm (物理极限)
        'heidelberg': 10.0,   # Heidelberg Dymatrix: 10mm
        'domestic_standard': 12.0,  # 国产标准机
        'domestic_old': 15.0,      # 国产老式机
    }
    
    def calculate(
        self,
        flute: MicroFluteType,
        standard: Standard = Standard.DIEPRE,
        machine: str = 'domestic_standard',
        mc: float = 8.0,
        custom_thickness: Optional[float] = None,
    ) -> MicroFluteParams:
        """
        计算微瓦楞完整参数
        
        Args:
            flute: 楞型
            standard: 标准体系
            machine: 设备类型
            mc: 含水率
            custom_thickness: 自定义厚度 (覆盖标准值)
        """
        # 基础参数
        base = {
            MicroFluteType.E: self.E_PARAMS,
            MicroFluteType.F: self.F_PARAMS,
            MicroFluteType.N: self.N_PARAMS,
            MicroFluteType.EF: self.EF_PARAMS,
        }[flute]
        
        t = custom_thickness or base['thickness']
        
        # 标准修正
        sc = self.STANDARD_CORRECTION[standard]
        
        # 槽宽计算 (核心公式)
        W = (t + sc['C_res']) * sc['K_stru']
        
        # 压痕深度
        d = t * sc['depth_ratio']
        
        # MC修正
        warnings = []
        mc_delta = abs(mc - base['mc_standard'])
        if mc_delta > 2:
            warnings.append(f"💧 MC={mc}%偏离标准{base['mc_standard']}%达{mc_delta:.1f}%, 精度下降")
            # MC影响槽宽: MC高→纸软→槽宽需略收
            if mc > base['mc_standard']:
                W *= (1 - 0.02 * mc_delta)  # 每超1%收窄2%
        
        # CD方向膨胀补偿
        cd_expand = base['cd_expansion'] * mc_delta
        
        # 咬口余量
        bite = self.BITE_MARGIN.get(machine, 12.0)
        
        # 精度标注
        precision_map = {
            'bobst': '±0.10-0.15mm (精密)',
            'heidelberg': '±0.10-0.20mm (精密)',
            'domestic_standard': '±0.25-0.30mm (标准)',
            'domestic_old': '±0.30-0.50mm (宽松)',
        }
        
        # 标准间差异警告
        if standard == Standard.FEFCO:
            warnings.append("⚠️ FEFCO公式W=1.5t对微瓦楞偏宽, 建议使用DIEPRE修正")
        if standard == Standard.GB:
            warnings.append("⚠️ GB标准在微瓦楞领域定义缺失, 参数为推演估算值")
        
        return MicroFluteParams(
            flute=flute,
            thickness=t,
            thickness_range=base['thickness_range'],
            groove_width=round(W, 2),
            crease_depth=round(d, 2),
            crease_depth_ratio=sc['depth_ratio'],
            k_factor=base['k_factor'],
            mc_standard=base['mc_standard'],
            mc_tolerance=2.0,
            cd_expansion=base['cd_expansion'],
            md_expansion=base['md_expansion'],
            folding_tolerance=base['folding_tolerance'],
            bite_margin=bite,
            standard=standard,
            warnings=warnings,
        )
    
    def compare_standards(self, flute: MicroFluteType, thickness: Optional[float] = None) -> str:
        """对比不同标准下的参数差异"""
        lines = [f"{'='*65}"]
        lines.append(f"  微瓦楞 {flute.value}楞 — 标准对比")
        lines.append(f"{'='*65}")
        lines.append(f"{'标准':<10} {'槽宽W(mm)':<12} {'压痕深度d':<12} {'d/T比':<8} {'咬口(mm)':<10}")
        lines.append(f"{'-'*65}")
        
        for std in Standard:
            p = self.calculate(flute, std, custom_thickness=thickness)
            bite = self.BITE_MARGIN.get('domestic_standard', 12.0)
            lines.append(
                f"{std.value:<10} {p.groove_width:<12.2f} {p.crease_depth:<12.2f} "
                f"{p.crease_depth_ratio:<8.2f} {bite:<10.1f}"
            )
        
        # 差异分析
        fefco = self.calculate(flute, Standard.FEFCO, custom_thickness=thickness)
        jis = self.calculate(flute, Standard.JIS, custom_thickness=thickness)
        diff = abs(fefco.groove_width - jis.groove_width)
        lines.append(f"{'-'*65}")
        lines.append(f"FEFCO vs JIS 槽宽差异: {diff:.2f}mm {'⚠️ ≥0.2mm, 显著' if diff >= 0.2 else '✅ <0.2mm'}")
        return "\n".join(lines)
    
    def unfold_length(
        self,
        flute: MicroFluteType,
        panels: list,  # [(A, B), ...] 面板尺寸
        standard: Standard = Standard.DIEPRE,
        mc: float = 8.0,
    ) -> Tuple[float, dict]:
        """
        微瓦楞展开长度计算
        
        L = Σ(A_i + B_i) + (n-1) × t × K
        
        Returns: (展开长度, 详细信息)
        """
        params = self.calculate(flute, standard, mc=mc)
        t = params.thickness
        k = params.k_factor
        
        n_bends = len(panels) - 1
        panel_sum = sum(a + b for a, b in panels)
        bend_correction = n_bends * t * k
        L = panel_sum + bend_correction
        
        # MC膨胀补偿
        mc_delta = mc - params.mc_standard
        cd_expand_mm = panel_sum * params.cd_expansion * mc_delta / 100
        L_adjusted = L - cd_expand_mm  # 膨胀则展开需缩短
        
        detail = {
            'panels': panels,
            'n_bends': n_bends,
            'panel_sum': panel_sum,
            'bend_correction': bend_correction,
            'k_factor': k,
            'mc_expand': cd_expand_mm,
            'L_raw': L,
            'L_adjusted': L_adjusted,
        }
        
        return round(L_adjusted, 2), detail


# === 快捷函数 ===
_engine = MicroFluteEngine()

def calc_micro(flute: str, standard: str = 'DIEPRE', machine: str = 'domestic_standard', mc: float = 8.0):
    """快捷微瓦楞参数计算"""
    flute_map = {f.value: f for f in MicroFluteType}
    std_map = {s.value: s for s in Standard}
    return _engine.calculate(flute_map[flute], std_map[standard], machine, mc)


if __name__ == "__main__":
    # 标准对比
    for ft in MicroFluteType:
        print(_engine.compare_standards(ft))
        print()
    
    # 展开长度测试
    print("=== 展开长度测试 ===\n")
    panels = [(100, 80), (50, 50), (100, 80)]  # 3面板, 2折弯
    for ft in [MicroFluteType.E, MicroFluteType.F, MicroFluteType.EF]:
        L, detail = _engine.unfold_length(ft, panels)
        print(f"{ft.value}楞: L={L:.2f}mm | 面板={detail['panel_sum']} | 折弯修正={detail['bend_correction']:.2f} | MC膨胀={detail['mc_expand']:.3f}mm")
    
    # Bobst精密场景
    print("\n=== Bobst SP106 + E楞精密场景 ===\n")
    p = _engine.calculate(MicroFluteType.E, Standard.DIEPRE, machine='bobst')
    print(f"槽宽: {p.groove_width}mm")
    print(f"压痕深度: {p.crease_depth}mm")
    print(f"K因子: {p.k_factor}")
    print(f"咬口: {p.bite_margin}mm")
    print(f"折叠精度: ±{p.folding_tolerance}mm")
    if p.warnings:
        for w in p.warnings:
            print(f"  {w}")
    
    # GB缺失警告
    print("\n=== GB标准缺失验证 ===\n")
    p_gb = _engine.calculate(MicroFluteType.F, Standard.GB)
    for w in p_gb.warnings:
        print(w)
