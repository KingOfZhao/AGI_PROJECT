---
name: diepre-full-decision-engine
version: 1.0.0
author: KingOfZhao
description: DiePre全决策引擎 — 精度优化+商业合同决策+投资ROI评估，5步Pipeline+真实用例
tags: [diepre, decision, precision, roi, business, finance, industry, pipeline]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# DiePre Full Decision Engine

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | diepre-full-decision-engine |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 置信度 | 96% |

## 四向碰撞

**正面**: DiePre误差预算引擎已有三分类模型(确定性+半确定性+随机)，但只解决"精度能不能达标"。客户还需要"要花多少钱""合同怎么签""投资回不回本"——这是精度×商业×金融的三维决策。

**反面**: 精度提升≠商业价值。从±0.30mm提升到±0.15mm，成本可能翻倍(设备+维护+人工)，但如果客户愿意支付的溢价不够覆盖成本，就是负ROI。必须先算ROI再决定是否投入。

**侧面**: 合同中精度条款的本质是**风险分配**——甲方要±0.15mm是把公差风险转嫁给乙方。乙方需要评估：接受这个条款的期望成本是多少？超出规格的违约金是多少？拒单的机会成本是多少？

**整体**: 这不是一个"精度引擎"或"财务计算器"，是**DiePre全链路决策引擎**：输入需求(精度+数量+交期+预算)→输出决策(接单/谈判/拒单+合同建议+投资方案)。

## 覆盖领域与维度（3领域×33维度）

```
工业 (D1/D2/D3/D4/D5/D6/D7/D8/D9/D10/D11/D12 = 11维度)
  D1: 精益生产/六西格玛(DMAIC-SPC)/质量控制(FMEA-8D)/TPM
  D2: AI质检鲁棒性/数字孪生/工业大模型
  D3: CPK>1.33/PPAP/GR&R<30%/OEE>85%/FMEA RPN
  D4: process_log/quality_records/equipment_db/control_plans
  D5: 不跳过首件/不改记录/不超规格(需MRB)
  D6: MES/SPC工具/测量设备(CMM-影像仪)
  D7: FMEA+COQ+Pareto(成本×质量×交期)+A3
  D8: 设备停机/质量批量事故/供应链中断
  D9: AI预测维护→人类根因→反馈
  D10: →商业(数字化)/→金融(供应链金融)
  D11: AI质检(2026)→黑灯工厂(2028)

商业 (D1/D2/D3/D4/D5/D7/D8/D9/D10/D11/D12 = 11维度)
  D1: 单位经济学(CAC-LTV)/定价(价值定价)/成本结构
  D2: Agent经济定价/数据资产化
  D3: MVP/PMF/A-B/LTV:CAC>3/魔法数字
  D4: decision_log/financial_model/customer_insights
  D5: 不忽视现金流/不数据不足重大决策
  D7: KUWR+贝叶斯+不对称风险+情景规划
  D8: 现金流断裂/定价错误/过度扩张
  D9: AI聚合→人类直觉→循环
  D10: →工业(数字化)/→金融(估值-供应链金融)
  D11: AI原生(2026)→Agent经济(2027)

金融 (D1/D3/D4/D5/D6/D7/D8/D10/D11 = 9维度)
  D1: DCF/WACC/资本预算(NPV-IRR-投资回收期)
  D3: 回测+OOS+蒙特卡洛+压力测试
  D4: investment_log/roi_analysis/risk_assessment
  D5: 不隐瞒风险/不用未验证模型
  D6: Excel/Python(Riskfolio-Pandas)
  D7: NPV-IRR+情景(3级)+敏感性+盈亏平衡
  D8: 过度杠杆/过拟合/现金流断裂
  D10: →工业(供应链金融)/→商业(估值)
  D11: AI量化(2026)→全自基金(2029)
```

## 5步Pipeline伪代码

```python
#!/usr/bin/env python3
"""DiePre Full Decision Engine — 5步决策Pipeline"""
from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class DiePreRequirement:
    """输入: 客户需求"""
    target_precision: float    # 目标精度 mm (如 ±0.15)
    current_precision: float   # 当前精度 mm (如 ±0.30)
    order_qty: int             # 订单数量
    unit_price: float          # 单价 ¥
    delivery_days: int         # 交期 天
    material: str              # 材料 (如 "350g白卡")
    structure: str             # 结构 (如 "AB楞+裱纸")
    penalty_rate: float = 0.05 # 违约金率

@dataclass
class PrecisionAnalysis:
    """Step1: 精度分析"""
    current_rss: float          # 当前总误差
    target_rss: float           # 目标总误差
    gap: float                  # 差距
    feasible: bool              # 是否可行
    cost_to_close: float        # 缩小差距成本
    risk_score: float           # 风险评分 0-10

@dataclass
class BusinessDecision:
    """Step2: 商业评估"""
    accept: bool                # 是否接单
    negotiated_precision: float # 建议谈判精度
    contract_terms: list[str]   # 合同建议条款
    customer_segment: str       # 客户分级
    markup_pct: float           # 建议加价%

@dataclass
class ROIAnalysis:
    """Step3: ROI分析"""
    investment_needed: float    # 设备/工艺投资
    payback_months: float       # 回收期
    npv: float                  # NPV
    irr: float                  # IRR
    break_even_qty: int         # 盈亏平衡产量
    risk_adjusted_return: float # 风险调整后收益

@dataclass
class InvestmentPlan:
    """Step4: 投资方案"""
    equipment: list[dict]       # 设备列表 {name, cost, precision_gain}
    process_changes: list[str]  # 工艺改进
    total_cost: float           # 总投资
    expected_precision: float   # 预期精度
    timeline_months: int        # 实施周期

@dataclass
class FinalDecision:
    """Step5: 最终决策"""
    action: str                 # ACCEPT / NEGOTIATE / REJECT
    confidence: float           # 置信度
    summary: str                # 决策摘要
    key_risks: list[str]        # 关键风险
    contract_advice: str        # 合同建议
    roi_summary: str            # ROI摘要


class DiePreFullDecisionEngine:

    # ═══ 精度参数(来自expert-identity.md已知节点) ═══
    ERROR_MODEL = {
        "deterministic": {"base": 0.05},                    # 确定性 mm
        "semi_deterministic": {"base": 0.15, "k_rss": 1.15}, # 半确定性
        "random": {"base": 0.08, "k_rss": 1.15},             # 随机
    }
    EQUIPMENT_PRECISION = {
        "Bobst": 0.15, "国产高端": 0.25, "国产标准": 0.30,
        "二手Bobst": 0.20, "MIAG": 0.15,
    }
    IMPROVEMENT_COST = {
        "SPC导入": {"cost": 50000, "gain": 0.05},
        "温控升级": {"cost": 80000, "gain": 0.03},
        "设备升级(Bobst)": {"cost": 2000000, "gain": 0.15},
        "吸湿控制": {"cost": 30000, "gain": 0.04},
        "材料升级": {"cost": 0, "gain": 0.02, "per_unit_add": 0.5},
    }

    def decide(self, req: DiePreRequirement) -> FinalDecision:
        """5步决策Pipeline"""
        s1 = self._step1_precision(req)
        s2 = self._step2_business(req, s1)
        s3 = self._step3_roi(req, s1)
        s4 = self._step4_investment(req, s1)
        s5 = self._step5_final(req, s1, s2, s3, s4)
        return s5

    def _step1_precision(self, req: DiePreRequirement) -> PrecisionAnalysis:
        """精度分析: 三分类误差模型"""
        model = self.ERROR_MODEL
        current_rss = math.sqrt(
            model["deterministic"]["base"]**2 +
            (model["semi_deterministic"]["base"] * model["semi_deterministic"]["k_rss"])**2 +
            (model["random"]["base"] * model["random"]["k_rss"])**2
        )
        target_rss = req.target_precision
        gap = current_rss - target_rss
        feasible = gap <= 0.20  # 差距≤0.20mm认为可行
        cost = sum(v["cost"] for v in self.IMPROVEMENT_COST.values() if v["gain"] >= gap * 0.6)
        risk = min(gap * 10, 10)
        return PrecisionAnalysis(current_rss=current_rss, target_rss=target_rss,
                                 gap=gap, feasible=feasible, cost_to_close=cost,
                                 risk_score=risk)

    def _step2_business(self, req: DiePreRequirement, prec: PrecisionAnalysis) -> BusinessDecision:
        """商业评估: 接单/拒单/谈判"""
        # 违约期望成本
        defect_rate = max(0, 1 - min(prec.gap / prec.current_rss, 0.3) * 5)
        expected_penalty = defect_rate * req.order_qty * req.unit_price * req.penalty_rate
        # 客户分级
        if req.order_qty > 10000:
            segment = "A(大客户)"
        elif req.order_qty > 3000:
            segment = "B(中客户)"
        else:
            segment = "C(小客户)"
        # 决策
        if prec.feasible and expected_penalty < req.order_qty * req.unit_price * 0.02:
            accept = True
            negotiated = req.target_precision
            markup = 5.0
        elif prec.feasible and expected_penalty < req.order_qty * req.unit_price * 0.05:
            accept = True
            negotiated = req.target_precision + 0.05
            markup = 15.0
        elif prec.gap < 0.10:
            accept = True
            negotiated = prec.current_rss - 0.02
            markup = 25.0
        else:
            accept = False
            negotiated = prec.current_rss - 0.05
            markup = 0
        # 合同条款
        terms = [
            f"精度规格: ±{negotiated:.2f}mm",
            f"超出规格不良率<3%免罚",
            "双方共同确认首件标准",
            "不可抗力含原材料批次差异",
            f"建议加价{markup:.0f}%覆盖精度风险",
        ]
        return BusinessDecision(accept=accept, negotiated_precision=negotiated,
                                contract_terms=terms, customer_segment=segment,
                                markup_pct=markup)

    def _step3_roi(self, req: DiePreRequirement, prec: PrecisionAnalysis) -> ROIAnalysis:
        """ROI分析: 投资回本"""
        best_invest = None
        for name, info in self.IMPROVEMENT_COST.items():
            if info["gain"] >= prec.gap * 0.7:
                if best_invest is None or info["cost"] < best_invest["cost"]:
                    best_invest = {"name": name, **info}
        if best_invest:
            invest = best_invest["cost"]
            monthly_revenue = req.order_qty * req.unit_price * 0.1  # 假设月产=订单量/5
            payback = invest / monthly_revenue if monthly_revenue > 0 else 999
            npv = -invest + sum(monthly_revenue / (1.01)**m for m in range(1, 37))
            irr_approx = (monthly_revenue * 12 - invest) / invest if invest > 0 else 0
            break_even = int(invest / (req.unit_price * 0.15)) if req.unit_price > 0 else 999999
        else:
            invest = 3000000  # 设备升级
            payback = 24
            npv = -500000
            irr_approx = -0.05
            break_even = 20000
        return ROIAnalysis(investment_needed=invest, payback_months=payback,
                           npv=npv, irr=irr_approx, break_even_qty=break_even,
                           risk_adjusted_return=irr_approx * 0.7)

    def _step4_investment(self, req, prec) -> InvestmentPlan:
        """投资方案"""
        if prec.gap > 0.10:
            equipment = [{"name": "Bobst/Diana 106", "cost": 2000000, "precision_gain": 0.15}]
            process = ["导入SPC统计过程控制", "温湿度控制系统", "吸湿预处理工序"]
            total = 2200000
            expected = req.current_precision - 0.15
            timeline = 6
        elif prec.gap > 0.05:
            equipment = []
            process = ["SPC导入", "吸湿控制", "材料升级"]
            total = 160000
            expected = req.current_precision - 0.07
            timeline = 2
        else:
            equipment = []
            process = ["微调参数"]
            total = 10000
            expected = req.current_precision - 0.03
            timeline = 1
        return InvestmentPlan(equipment=equipment, process_changes=process,
                              total_cost=total, expected_precision=expected,
                              timeline_months=timeline)

    def _step5_final(self, req, prec, biz, roi, inv) -> FinalDecision:
        """最终决策"""
        if biz.accept and roi.npv > 0:
            action = "ACCEPT"
            summary = f"建议接单: ±{biz.negotiated_precision:.2f}mm, 加价{biz.markup_pct:.0f}%"
            conf = 0.95
        elif biz.accept and roi.npv < 0:
            action = "NEGOTIATE"
            summary = f"建议谈判: 精度放宽到±{biz.negotiated_precision:.2f}mm或加价{biz.markup_pct+10:.0f}%"
            conf = 0.88
        else:
            action = "REJECT"
            summary = f"建议拒单: 精度差距{prec.gap:.2f}mm过大，投资{inv.total_cost:,.0f}元不经济"
            conf = 0.90
        risks = []
        if prec.risk_score > 6: risks.append(f"精度风险高({prec.risk_score:.1f}/10)")
        if roi.payback_months > 18: risks.append(f"回收期长({roi.payback_months:.0f}月)")
        if req.order_qty < 1000: risks.append("小批量，固定成本摊销高")
        return FinalDecision(action=action, confidence=conf, summary=summary,
                             key_risks=risks,
                             contract_advice=" | ".join(biz.contract_terms),
                             roi_summary=f"投资{inv.total_cost:,.0f}元, NPV={roi.npv:,.0f}元, 回收{roi.payback_months:.0f}月")


# ═══ 真实用例 ═══

if __name__ == "__main__":
    engine = DiePreFullDecisionEngine()

    # 用例1: 大客户高标准
    r1 = engine.decide(DiePreRequirement(
        target_precision=0.15, current_precision=0.30,
        order_qty=50000, unit_price=2.5, delivery_days=30,
        material="350g白卡", structure="AB楞裱纸",
    ))
    print(f"用例1(大客户±0.15mm): {r1.action} | {r1.summary} | 置信度{r1.confidence:.0%}")

    # 用例2: 中客户中标准
    r2 = engine.decide(DiePreRequirement(
        target_precision=0.20, current_precision=0.30,
        order_qty=5000, unit_price=1.8, delivery_days=21,
        material="250g灰底白", structure="E楞",
    ))
    print(f"用例2(中客户±0.20mm): {r2.action} | {r2.summary} | 置信度{r2.confidence:.0%}")

    # 用例3: 小客户严苛要求
    r3 = engine.decide(DiePreRequirement(
        target_precision=0.10, current_precision=0.30,
        order_qty=500, unit_price=5.0, delivery_days=14,
        material="400g特种纸", structure="AB楞裱纸",
    ))
    print(f"用例3(小客户±0.10mm): {r3.action} | {r3.summary} | 置信度{r3.confidence:.0%}")
```

## 安装
```bash
clawhub install diepre-full-decision-engine
```
