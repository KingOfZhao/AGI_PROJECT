"""
标准体系差异矩阵 — FEFCO/JIS/GB/DIN 四国对比
==============================================
从1562节点中提取各国标准在刀模设计参数上的差异

核心发现:
1. 宽严阶梯: JIS最严 > DIN≈FEFCO > GB最宽
2. 焦点差异: JIS折痕美观 / FEFCO物流适配 / DIN机械加工 / GB生产可行性
3. 微瓦楞: GB完全缺失, JIS有具体参数
4. 公差定义: FEFCO正态分布 / GB分级公差 / JIS线性分段

数据来源: 106条标准对比节点
"""

from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class Standard(Enum):
    FEFCO = "FEFCO"
    JIS = "JIS"
    GB = "GB"
    DIN = "DIN"


@dataclass
class StandardParam:
    """标准参数"""
    name: str
    fei_value: Optional[str]  # FEFCO
    jis_value: Optional[str]  # JIS
    gb_value: Optional[str]   # GB
    din_value: Optional[str]  # DIN
    diepre_value: str         # DiePre推荐
    severity: str             # "critical" | "high" | "medium"
    note: str


class StandardMatrix:
    """
    四国标准差异矩阵
    
    使用方法:
    - 查询特定参数在不同标准下的值
    - 获取出口订单的标准切换建议
    - 识别标准盲区
    """
    
    # === 核心参数差异表 ===
    PARAMS = {
        # --- 压痕槽宽公式 ---
        "groove_width_coarse": StandardParam(
            name="槽宽公式(粗瓦楞A/B/C)",
            fei_value="W = 1.5t", jis_value="W = t + (0.8~1.0)", gb_value="W = 1.5t + C",
            din_value="W = 1.5t", diepre_value="W = 1.5t + Δ_f(machine)",
            severity="high",
            note="FEFCO/DIN一致; JIS偏窄注重美观; GB加修正系数C(产地差异大)"
        ),
        "groove_width_micro": StandardParam(
            name="槽宽公式(微瓦楞E/F)",
            fei_value="W = t + 1.0 (偏宽)", jis_value="W = t + 0.5 (最严)",
            gb_value="缺失, 参考行业经验", din_value="W = t + 0.8",
            diepre_value="W = (t + C_res) × K_stru",
            severity="critical",
            note="GB完全缺失; FEFCO vs JIS差异≥0.5mm, 显著"
        ),
        "groove_width_grayboard": StandardParam(
            name="槽宽公式(灰板)",
            fei_value="W = 1.5t + 1", jis_value="W = 1.2t + 0.6", gb_value="W = 1.5t + C",
            din_value="W = 1.5t", diepre_value="≤1.5mm: 1.5t+1; >1.5mm: 2t+1",
            severity="high",
            note="江浙沪修正版: >1.5mm灰板用2t+1"
        ),
        
        # --- 压痕深度 ---
        "crease_depth_coarse": StandardParam(
            name="压痕深度(粗瓦楞)",
            fei_value="d = 0.5T", jis_value="d = 0.45T (较浅)", gb_value="d = 0.5T",
            din_value="d = 0.48T", diepre_value="d = 0.50T (标准) / 0.45T (双瓦楞)",
            severity="high",
            note="JIS偏浅防止爆线; 双瓦楞建议0.45T防外实内虚"
        ),
        "crease_depth_micro": StandardParam(
            name="压痕深度(微瓦楞)",
            fei_value="d = 0.5T", jis_value="d = 0.40~0.45T",
            gb_value="缺失", din_value="d = 0.48T",
            diepre_value="E: 0.40T / F: 0.45T / EF: 0.38T",
            severity="critical",
            note="微瓦楞需更浅的压痕防塌陷"
        ),
        
        # --- 公差带 ---
        "tolerance_0201_under1000": StandardParam(
            name="0201箱型公差(L≤1000mm)",
            fei_value="±1.5mm", jis_value="±1.0mm (最严)", gb_value="±2.0mm (优等品) / ±3.0mm",
            din_value="±1.5mm", diepre_value="目标市场决定: 欧洲±1.5 / 日本±1.0 / 内销±2.0",
            severity="critical",
            note="GB允许偏差是JIS的3倍; 出口日本必须收紧"
        ),
        "tolerance_precision": StandardParam(
            name="精密模切公差",
            fei_value="±0.5mm", jis_value="±0.3mm", gb_value="±1.0mm",
            din_value="±0.5mm", diepre_value="±0.5mm (需RSS前置校验)",
            severity="critical",
            note="±0.5mm在修正RSS下数学不可达(实际0.687mm/Bobst)"
        ),
        
        # --- K因子 ---
        "k_factor_single_wall": StandardParam(
            name="K因子(单瓦楞)",
            fei_value="k ≈ 0.35 (经验值)", jis_value="有具体测试方法",
            gb_value="未定义K因子概念", din_value="k ≈ 0.35",
            diepre_value="分层表: A/B/C=0.35, E=0.42, F=0.45",
            severity="high",
            note="GB完全未引入K因子; JIS有测试方法可参考"
        ),
        
        # --- 插舌公式 ---
        "tongue_formula": StandardParam(
            name="FEFCO插舌公式",
            fei_value="插舌 = 插口 - 1.5×t - 0.5mm",
            jis_value="插舌 = 插口 - 1.5×t - 0.3mm (间隙更小)",
            gb_value="GB/T 6543无明确公式", din_value="同FEFCO",
            diepre_value="亚洲+0.1-0.2mm补偿 (塌陷修正)",
            severity="high",
            note="亚洲纸板回收浆比例高, 需额外补偿"
        ),
        
        # --- 咬口余量 ---
        "bite_margin": StandardParam(
            name="咬口(夹持)余量",
            fei_value="8-10mm", jis_value="6-8mm", gb_value="12-15mm",
            din_value="8-10mm", diepre_value="Bobst:8mm / Heidelberg:10mm / 国产:12mm",
            severity="high",
            note="国产机12-15mm远大于Bobst 8mm, 浪费材料"
        ),
        
        # --- 吸湿处理 ---
        "moisture_control": StandardParam(
            name="含水率控制要求",
            fei_value="MC 8±2%", jis_value="MC 7±1.5% (更严)",
            gb_value="MC 8±3% (较宽)", din_value="MC 8±2%",
            diepre_value="MC 8±2% (推荐), 精密品MC 8±1%",
            severity="high",
            note="JIS对MC控制最严; GB最宽"
        ),
    }
    
    # === 目标市场标准映射 ===
    MARKET_STANDARD = {
        '欧洲': Standard.FEFCO,
        '日本': Standard.JIS,
        '内销': Standard.GB,
        '德国': Standard.DIN,
        '东南亚': Standard.GB,  # 通常参考GB
        '美国': Standard.FEFCO,  # 无独立标准, 参考FEFCO
    }
    
    # === 标准切换建议 ===
    SWITCH_RULES = {
        ('内销', '日本'): "⚠️ GB→JIS: 公差收紧3倍, 咬口从12mm→8mm, MC从±3%→±1.5%, 必须设备升级",
        ('内销', '欧洲'): "⚠️ GB→FEFCO: 公差收紧1.3倍, 槽宽公式调整, 需验证纸张兼容性",
        ('内销', '德国'): "⚠️ GB→DIN: 压痕深度略调, 机械适配性检查",
        ('欧洲', '日本'): "⚠️ FEFCO→JIS: 槽宽收窄, 压痕略浅, MC控制加严",
    }
    
    def get_param(self, param_key: str) -> StandardParam:
        return self.PARAMS[param_key]
    
    def get_all_blind_spots(self) -> list:
        """识别标准盲区 (GB缺失的参数)"""
        blind = []
        for key, p in self.PARAMS.items():
            if p.gb_value and ('缺失' in p.gb_value or '未定义' in p.gb_value or '无' in p.gb_value):
                blind.append((key, p.name, p.gb_value))
        return blind
    
    def switch_advice(self, from_market: str, to_market: str) -> str:
        """获取标准切换建议"""
        rule = self.SWITCH_RULES.get((from_market, to_market))
        if rule:
            return rule
        from_std = self.MARKET_STANDARD.get(from_market, Standard.GB)
        to_std = self.MARKET_STANDARD.get(to_market, Standard.FEFCO)
        return f"ℹ️ {from_market}({from_std.value}) → {to_market}({to_std.value}): 需检查各参数差异"
    
    def print_matrix(self, filter_severity: str = None) -> str:
        """打印差异矩阵"""
        lines = [f"{'='*100}"]
        lines.append(f"  四国标准差异矩阵 (FEFCO/JIS/GB/DIN/DiePre)")
        lines.append(f"{'='*100}")
        lines.append(f"{'参数':<30} {'FEFCO':<18} {'JIS':<18} {'GB':<18} {'DiePre':<18}")
        lines.append(f"{'-'*100}")
        
        for key, p in self.PARAMS.items():
            if filter_severity and p.severity != filter_severity:
                continue
            fei = (p.fei_value or '-')[:16]
            jis = (p.jis_value or '-')[:16]
            gb = (p.gb_value or '-')[:16]
            dp = (p.diepre_value or '-')[:16]
            lines.append(f"{p.name:<30} {fei:<18} {jis:<18} {gb:<18} {dp:<18}")
        
        return "\n".join(lines)
    
    def print_blind_spots(self) -> str:
        """打印标准盲区"""
        spots = self.get_all_blind_spots()
        lines = [f"\n⚠️ GB标准盲区 ({len(spots)}个)"]
        lines.append("-" * 60)
        for key, name, val in spots:
            lines.append(f"  • {name}: {val}")
        return "\n".join(lines)


if __name__ == "__main__":
    matrix = StandardMatrix()
    
    print(matrix.print_matrix())
    print(matrix.print_blind_spots())
    
    print("\n=== 出口标准切换建议 ===\n")
    for (f, t), advice in sorted(matrix.SWITCH_RULES.items()):
        print(f"  {f} → {t}: {advice}")
    
    print("\n=== 目标市场标准映射 ===\n")
    for market, std in matrix.MARKET_STANDARD.items():
        print(f"  {market}: {std.value}")
    
    print("\n=== 关键参数详情 ===\n")
    for key in ['groove_width_micro', 'tolerance_precision', 'k_factor_single_wall']:
        p = matrix.get_param(key)
        print(f"\n📌 {p.name} [{p.severity.upper()}]")
        print(f"   FEFCO: {p.fei_value}")
        print(f"   JIS:   {p.jis_value}")
        print(f"   GB:    {p.gb_value}")
        print(f"   DIN:   {p.din_value}")
        print(f"   DiePre:{p.diepre_value}")
        print(f"   📝 {p.note}")
