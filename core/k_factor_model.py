"""
K因子相变模型 — 刀模展开长度精确计算
=======================================
从1562个已确认知识节点中提取58个K因子数据点，建立分层模型。

核心发现: K因子不是连续函数，存在相变边界:
  - 正常区域: K随厚度/结构缓慢变化 (0.35-0.45)
  - 爆线临界: K骤降到0.25 (纤维断裂，不可逆)

已知(F): F25(分层表), F26(双瓦楞外实内虚), 推演#2
待解(V): V9(双瓦楞中性轴), V10(JIS原文)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MaterialType(Enum):
    """材料类型"""
    GRAYBOARD = "灰板"          # 灰板/白板
    CARDBOARD = "卡纸"          # 单层卡纸/铜版纸
    SINGLE_WALL = "单瓦楞"      # A/B/C/E/F 楞
    DOUBLE_WALL = "双瓦楞"      # AB/BC/EB 楞
    TRIPLE_WALL = "三瓦楞"      # AAA/ABB 等
    PLASTIC = "塑料"            # PVC/PP 片材
    LAMINATED = "裱合复合"      # 灰板+面纸/卡纸+瓦楞


class FluteType(Enum):
    """楞型"""
    A = "A"   # 4.5mm
    B = "B"   # 2.5mm
    C = "C"   # 3.5mm
    E = "E"   # 1.5mm
    F = "F"   # 0.8mm
    AB = "AB"  # ~7mm
    BC = "BC"  # ~6mm
    EB = "EB"  # ~4mm
    EF = "EF"  # ~2.3mm
    MICRO = "MICRO"  # <1mm特种


@dataclass
class KFactorResult:
    """K因子计算结果"""
    k: float              # K因子值
    phase: str            # 相区: "normal" | "critical" | "phase_transition"
    neutral_axis_offset: float  # 中性轴偏移量 (从中心算, 正=向内)
    confidence: float     # 置信度 0-1
    warning: Optional[str] = None  # 警告信息
    correction: Optional[str] = None  # 修正建议


class KFactorModel:
    """
    K因子分层模型
    
    数据来源: 58个已确认K因子数据点 (all_confirmed_knowledge.txt)
    模型类型: 分层经验模型 + 相变检测
    
    物理原理:
    - 折叠时外层拉伸、内层压缩
    - 中性层(Neutral Axis)不在几何中心，向内侧偏移
    - K因子 = 中性层位置 / 总厚度 (0=内侧, 0.5=中心, 1.0=外侧)
    - K < 0.5 意味着内层压缩 > 外层拉伸 → 展开长度需减小
    """
    
    # === 基准K值表 (从节点数据提取, 按材料+楞型分层) ===
    BASE_K = {
        # 灰板: K随厚度增大 (纤维断裂风险增加)
        (MaterialType.GRAYBOARD, None): {
            't_threshold': 1.5,  # mm
            'k_thin': 0.35,      # ≤1.5mm
            'k_thick': 0.40,     # >1.5mm
            'dk_dt': 0.02,       # K每增加1mm厚度变化量
        },
        # 卡纸: 接近各向同性
        (MaterialType.CARDBOARD, None): {
            'k_base': 0.50,      # 铜版纸中性层居中
            'k_offset': -0.08,   # 印刷面张力导致轻微偏移
        },
        # 单瓦楞: K≈0.35, 中空结构导致中性轴内移
        (MaterialType.SINGLE_WALL, FluteType.A): {'k': 0.35, 'offset_pct': 18},
        (MaterialType.SINGLE_WALL, FluteType.B): {'k': 0.35, 'offset_pct': 15},
        (MaterialType.SINGLE_WALL, FluteType.C): {'k': 0.35, 'offset_pct': 16},
        (MaterialType.SINGLE_WALL, FluteType.E): {'k': 0.42, 'offset_pct': 10},
        (MaterialType.SINGLE_WALL, FluteType.F): {'k': 0.45, 'offset_pct': 8},
        (MaterialType.SINGLE_WALL, FluteType.MICRO): {'k': 0.48, 'offset_pct': 5},
        # 双瓦楞: 芯纸层数增加, 中性轴进一步内移
        (MaterialType.DOUBLE_WALL, FluteType.AB): {'k': 0.38, 'offset_pct': 20},
        (MaterialType.DOUBLE_WALL, FluteType.BC): {'k': 0.40, 'offset_pct': 20},
        (MaterialType.DOUBLE_WALL, FluteType.EB): {'k': 0.40, 'offset_pct': 18},
        (MaterialType.DOUBLE_WALL, FluteType.EF): {'k': 0.42, 'offset_pct': 15},
        # 三瓦楞: 保守估计
        (MaterialType.TRIPLE_WALL, None): {'k': 0.42, 'offset_pct': 22},
        # 塑料: 各向同性, 中性层居中
        (MaterialType.PLASTIC, None): {'k': 0.50, 'offset_pct': 0},
    }
    
    # === 相变参数 ===
    # K从正常值骤降到0.25的临界条件
    PHASE_TRANSITION = {
        'k_critical': 0.25,         # 爆线临界K值
        'depth_ratio_normal': 0.50, # 正常压痕深度比 (d/T)
        'depth_ratio_critical': 0.65, # 爆线临界压痕深度比
        'mc_threshold': 14,          # 含水量阈值 %
        'transition_band': 0.05,     # 相变过渡带宽
    }
    
    # === MC(含水率)修正系数 ===
    # K因子随MC变化: MC越高, 纸越软, 中性轴越居中
    MC_CORRECTION = {
        'mc_ref': 8,          # 参考MC %
        'dk_dmc': -0.005,     # 每增加1%MC, K变化量 (负=趋向居中)
        'mc_max': 14,         # 超过此值进入危险区
    }
    
    def calculate(
        self,
        material: MaterialType,
        thickness: float,
        flute: Optional[FluteType] = None,
        mc: float = 8.0,
        crease_depth_ratio: float = 0.50,
        high_strength: bool = False,
    ) -> KFactorResult:
        """
        计算K因子
        
        Args:
            material: 材料类型
            thickness: 总厚度 (mm)
            flute: 楞型 (仅瓦楞纸板)
            mc: 含水率 (%)
            crease_depth_ratio: 压痕深度/厚度比 (d/T)
            high_strength: 是否高强瓦楞
            
        Returns:
            KFactorResult
        """
        # Step 1: 查基准K值
        k_base = self._lookup_base_k(material, flute, thickness)
        
        # Step 2: 高强瓦楞修正
        if high_strength and material in (MaterialType.SINGLE_WALL, MaterialType.DOUBLE_WALL):
            k_base += 0.03  # 高强瓦楞K值略大 (纤维更刚, 中性轴外移)
        
        # Step 3: MC修正
        k_mc = self._apply_mc_correction(k_base, mc)
        
        # Step 4: 相变检测
        phase, k_phase = self._detect_phase_transition(
            k_mc, crease_depth_ratio, mc, material
        )
        
        # Step 5: 计算中性轴偏移
        offset = 0.5 - k_phase  # 正值=向内偏移
        
        # Step 6: 置信度
        confidence = self._estimate_confidence(material, flute, thickness)
        
        # Step 7: 警告
        warning = None
        correction = None
        if phase == "critical":
            warning = f"⚠️ 爆线风险! K={k_phase:.2f}已进入相变临界区"
            correction = f"建议压痕深度比降至{self.PHASE_TRANSITION['depth_ratio_normal']:.2f}以下"
        elif phase == "phase_transition":
            warning = f"⚡ 接近相变边界, K={k_phase:.2f}, 建议降低压痕深度"
            correction = f"当前d/T={crease_depth_ratio:.2f}, 建议≤0.55"
        elif mc > self.PHASE_TRANSITION['mc_threshold']:
            warning = f"💧 MC={mc}%超过阈值{self.PHASE_TRANSITION['mc_threshold']}%, 精度下降"
            correction = "建议MC控制在8±2%再加工"
        
        return KFactorResult(
            k=round(k_phase, 3),
            phase=phase,
            neutral_axis_offset=round(offset, 3),
            confidence=confidence,
            warning=warning,
            correction=correction,
        )
    
    def _lookup_base_k(self, material, flute, thickness):
        """查表获取基准K值"""
        key = (material, flute)
        if key in self.BASE_K:
            val = self.BASE_K[key]
            if isinstance(val, dict) and 'k' in val:
                return val['k']
            # dict without 'k' handled below by material type fallback
        
        # 灰板厚度分档
        if material == MaterialType.GRAYBOARD:
            gb = self.BASE_K[(MaterialType.GRAYBOARD, None)]
            if thickness <= gb['t_threshold']:
                return gb['k_thin']
            else:
                return min(gb['k_thick'] + gb['dk_dt'] * (thickness - gb['t_threshold']), 0.50)
        
        # 卡纸
        if material == MaterialType.CARDBOARD:
            cb = self.BASE_K[(MaterialType.CARDBOARD, None)]
            return cb['k_base'] + cb['k_offset']
        
        # 三瓦楞
        if material == MaterialType.TRIPLE_WALL:
            return self.BASE_K[(MaterialType.TRIPLE_WALL, None)]['k']
        
        # 塑料
        if material == MaterialType.PLASTIC:
            return self.BASE_K[(MaterialType.PLASTIC, None)]['k']
        
        # 双瓦楞回退
        if material == MaterialType.DOUBLE_WALL:
            return self.BASE_K[(MaterialType.DOUBLE_WALL, FluteType.BC)]['k']
        
        # 单瓦楞回退
        if material == MaterialType.SINGLE_WALL:
            return self.BASE_K[(MaterialType.SINGLE_WALL, FluteType.B)]['k']
        
        return 0.35
    
    def _apply_mc_correction(self, k, mc):
        """MC含水率修正"""
        delta_mc = mc - self.MC_CORRECTION['mc_ref']
        k_corrected = k + self.MC_CORRECTION['dk_dmc'] * delta_mc
        return max(0.20, min(0.50, k_corrected))
    
    def _detect_phase_transition(self, k, crease_depth_ratio, mc, material):
        """相变检测"""
        k_crit = self.PHASE_TRANSITION['k_critical']
        d_crit = self.PHASE_TRANSITION['depth_ratio_critical']
        band = self.PHASE_TRANSITION['transition_band']
        
        # 压痕过深 → 爆线相变
        if crease_depth_ratio >= d_crit:
            # 超过临界深度, K骤降
            severity = (crease_depth_ratio - d_crit) / (1.0 - d_crit)
            k_collapsed = k_crit + (k - k_crit) * (1 - severity * 0.8)
            return "critical", max(k_crit, k_collapsed)
        
        # 过渡区
        if crease_depth_ratio >= d_crit - band * 2:
            transition_factor = (crease_depth_ratio - (d_crit - band * 2)) / (band * 2)
            k_transition = k - transition_factor * (k - k_crit) * 0.3
            return "phase_transition", k_transition
        
        # MC过高也可能触发
        if mc > self.PHASE_TRANSITION['mc_threshold']:
            mc_factor = (mc - self.PHASE_TRANSITION['mc_threshold']) / (20 - self.PHASE_TRANSITION['mc_threshold'])
            k_mc_degraded = k - mc_factor * 0.1
            return "phase_transition", k_mc_degraded
        
        return "normal", k
    
    def _estimate_confidence(self, material, flute, thickness):
        """估计置信度"""
        # 有直接数据的组合置信度高
        high_conf = [
            (MaterialType.GRAYBOARD, None),
            (MaterialType.SINGLE_WALL, FluteType.A),
            (MaterialType.SINGLE_WALL, FluteType.B),
            (MaterialType.SINGLE_WALL, FluteType.C),
            (MaterialType.PLASTIC, None),
        ]
        if (material, flute) in high_conf:
            return 0.85
        
        # 微瓦楞有推演数据但需验证
        if material == MaterialType.SINGLE_WALL and flute in (FluteType.E, FluteType.F):
            return 0.70
        
        # 双瓦楞是保守估计
        if material == MaterialType.DOUBLE_WALL:
            return 0.60
        
        # 裱合复合
        if material == MaterialType.LAMINATED:
            return 0.50
        
        return 0.65
    
    def unfold_length(self, panels: list, k_results: list) -> float:
        """
        计算展开长度 (复合结构展开公式 R7)
        
        L = Σ(A_i + B_i) + Σ(t_j × K_j)
        
        Args:
            panels: [(A_i, B_i, t_j), ...] 各面板外尺寸和折弯处厚度
            k_results: 各折弯处的KFactorResult
            
        Returns:
            展开总长度 (mm)
        """
        total = 0.0
        for i, (a, b, t) in enumerate(panels):
            total += a + b
            if i < len(k_results):
                total += t * k_results[i].k
        return total
    
    def get_lookup_table(self) -> str:
        """生成K因子速查表"""
        lines = ["=" * 70]
        lines.append("K因子速查表 (从58个数据点建模)")
        lines.append("=" * 70)
        lines.append(f"{'材料':<12} {'楞型':<6} {'K值':<8} {'偏移':<8} {'置信度':<8}")
        lines.append("-" * 70)
        
        for (mat, flute), val in sorted(self.BASE_K.items(), key=lambda x: (x[0][0].value, str(x[0][1]))):
            if isinstance(val, dict) and 'k' in val:
                k = val['k']
                off = val.get('offset_pct', int((0.5 - k) * 100))
                conf = self._estimate_confidence(mat, flute, 0)
                lines.append(f"{mat.value:<12} {flute.value if flute else '-':<6} {k:<8.2f} {off}%{'':<5} {conf:.0%}")
            elif isinstance(val, dict) and 'k_thin' in val:
                lines.append(f"{mat.value:<12} {'≤1.5mm':<6} {val['k_thin']:<8.2f} {'15%':<8} {'85%':<8}")
                lines.append(f"{mat.value:<12} {'>1.5mm':<6} {val['k_thick']:<8.2f} {'10%':<8} {'80%':<8}")
        
        lines.append("-" * 70)
        lines.append(f"{'爆线临界':<12} {'-':<6} {self.PHASE_TRANSITION['k_critical']:<8.2f} {'25%':<8} {'N/A':<8}")
        lines.append(f"{'塑料PVC':<12} {'-':<6} {'0.50':<8} {'0%':<8} {'90%':<8}")
        return "\n".join(lines)


# === 快捷函数 ===
_model = KFactorModel()

def calc_k(material: str, thickness: float, flute: str = None, mc: float = 8.0, crease_depth_ratio: float = 0.50) -> KFactorResult:
    """快捷K因子计算"""
    mat_map = {
        '灰板': MaterialType.GRAYBOARD, '卡纸': MaterialType.CARDBOARD,
        '单瓦楞': MaterialType.SINGLE_WALL, '双瓦楞': MaterialType.DOUBLE_WALL,
        '三瓦楞': MaterialType.TRIPLE_WALL, '塑料': MaterialType.PLASTIC,
    }
    flute_map = {f.value: f for f in FluteType}
    
    mat = mat_map.get(material, MaterialType.SINGLE_WALL)
    fl = flute_map.get(flute) if flute else None
    return _model.calculate(mat, thickness, fl, mc, crease_depth_ratio)


if __name__ == "__main__":
    # === 测试用例 ===
    print(_model.get_lookup_table())
    print("\n=== 场景测试 ===\n")
    
    scenarios = [
        ("灰板1.5mm", MaterialType.GRAYBOARD, 1.5, None),
        ("灰板3.0mm", MaterialType.GRAYBOARD, 3.0, None),
        ("B楞2.5mm", MaterialType.SINGLE_WALL, 2.5, FluteType.B),
        ("E楞1.5mm", MaterialType.SINGLE_WALL, 1.5, FluteType.E),
        ("BC双瓦楞6mm", MaterialType.DOUBLE_WALL, 6.0, FluteType.BC),
        ("B楞高强", MaterialType.SINGLE_WALL, 2.5, FluteType.B),
        ("塑料PVC", MaterialType.PLASTIC, 0.5, None),
    ]
    
    for name, mat, t, fl in scenarios:
        r = _model.calculate(mat, t, fl, mc=8.0, crease_depth_ratio=0.50)
        print(f"{name}: K={r.k:.3f} | 偏移={r.neutral_axis_offset:.3f} | 相区={r.phase} | 置信度={r.confidence:.0%}")
    
    # 爆线场景
    print("\n=== 爆线相变测试 ===\n")
    for d_ratio in [0.50, 0.55, 0.60, 0.65, 0.70, 0.80]:
        r = _model.calculate(MaterialType.SINGLE_WALL, 2.5, FluteType.B, crease_depth_ratio=d_ratio)
        print(f"B楞 d/T={d_ratio:.2f}: K={r.k:.3f} | {r.phase} | {r.warning or 'OK'}")
    
    # MC影响
    print("\n=== MC含水率影响 ===\n")
    for mc_val in [6, 8, 10, 12, 14, 16]:
        r = _model.calculate(MaterialType.SINGLE_WALL, 2.5, FluteType.B, mc=mc_val)
        print(f"B楞 MC={mc_val}%: K={r.k:.3f} | {r.phase} | {r.warning or 'OK'}")
    
    # 展开长度计算
    print("\n=== 展开长度计算 (R7公式) ===\n")
    panels = [(100, 100, 2.5), (50, 50, 2.5), (100, 100, 2.5)]  # 3个折弯
    k_results = [
        _model.calculate(MaterialType.SINGLE_WALL, 2.5, FluteType.B),
        _model.calculate(MaterialType.SINGLE_WALL, 2.5, FluteType.B),
        _model.calculate(MaterialType.SINGLE_WALL, 2.5, FluteType.B),
    ]
    L = _model.unfold_length(panels, k_results)
    print(f"3折弯箱体 (100×50×100, B楞2.5mm): 展开长度 = {L:.2f}mm")
    print(f"对比传统公式 L=A+A+B+B+3t = {100+100+50+50+3*2.5:.2f}mm")
    print(f"K因子修正节省: {100+100+50+50+3*2.5 - L:.2f}mm")
