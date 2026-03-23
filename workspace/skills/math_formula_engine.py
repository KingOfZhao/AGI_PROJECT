#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数学公式编码引擎 — 用数学公式定义、拆解、构建问题
=================================================
核心思想：
  任何可描述的问题 → 数学形式化表达 → 可执行Python代码 → 验证结果
  通过将问题转化为数学语言，消除自然语言歧义，强化本地模型推理能力。

架构：
  1. 问题形式化: 自然语言 → 数学符号表达(LaTeX + SymPy)
  2. 公式编码: 数学表达 → 可执行Python(numpy/sympy/scipy)
  3. 拆解器: 复杂公式 → 子公式树 → 逐步求解
  4. 构建器: 子结果 → 组合 → 完整解
  5. 验证器: 代码执行 → 数值验证 → proven节点注入
"""

import sys
import json
import math
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKILL_META = {
    "name": "math_formula_engine",
    "display_name": "数学公式编码引擎",
    "description": "用数学公式定义/拆解/构建问题，转化为可执行代码验证，强化本地模型",
    "tags": ["数学", "公式", "编码", "验证", "拆解", "构建"],
    "capabilities": [
        "formalize: 自然语言问题→数学形式化表达",
        "decompose: 复杂公式→子公式树",
        "codify: 数学表达→可执行Python代码",
        "verify: 执行代码并数值验证",
        "build: 从子结果组合完整解",
    ],
}


# ==================== 数据结构 ====================

@dataclass
class MathNode:
    """数学公式节点"""
    id: str
    name: str                          # 公式名/变量名
    formula_latex: str                 # LaTeX表达
    formula_python: str                # Python可执行表达
    domain: str = "general"            # 所属领域
    variables: List[str] = field(default_factory=list)   # 自由变量
    constraints: List[str] = field(default_factory=list)  # 约束条件
    unit: str = ""                     # 物理单位
    children: List[str] = field(default_factory=list)     # 子公式ID
    parent: str = ""                   # 父公式ID
    verified: bool = False
    result: Any = None
    error: str = ""


@dataclass
class FormulaTree:
    """公式拆解树"""
    root_id: str
    nodes: Dict[str, MathNode] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)  # 拓扑排序后的执行顺序
    context: Dict[str, Any] = field(default_factory=dict)      # 共享变量空间


# ==================== 基础数学公式库(proven) ====================
# 这些是经过验证的基础公式，作为拆解的原子单元

PROVEN_FORMULAS = {
    # 基础代数
    "quadratic": {
        "name": "一元二次方程求根公式",
        "latex": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "python": "lambda a,b,c: ((-b + (b**2 - 4*a*c)**0.5) / (2*a), (-b - (b**2 - 4*a*c)**0.5) / (2*a))",
        "domain": "代数",
        "variables": ["a", "b", "c"],
    },
    "linear_system_2x2": {
        "name": "二元一次方程组(Cramer)",
        "latex": r"x=\frac{e_1b_2-e_2b_1}{a_1b_2-a_2b_1}, y=\frac{a_1e_2-a_2e_1}{a_1b_2-a_2b_1}",
        "python": "lambda a1,b1,e1,a2,b2,e2: ((e1*b2-e2*b1)/(a1*b2-a2*b1), (a1*e2-a2*e1)/(a1*b2-a2*b1))",
        "domain": "代数",
    },

    # 微积分
    "derivative_power": {
        "name": "幂函数求导",
        "latex": r"\frac{d}{dx}x^n = nx^{n-1}",
        "python": "lambda n, x: n * x**(n-1)",
        "domain": "微积分",
    },
    "integral_power": {
        "name": "幂函数积分",
        "latex": r"\int x^n dx = \frac{x^{n+1}}{n+1} + C",
        "python": "lambda n, x, C=0: x**(n+1)/(n+1) + C",
        "domain": "微积分",
    },

    # 物理-热力学
    "heat_transfer": {
        "name": "傅里叶热传导定律",
        "latex": r"q = -k \nabla T = -k \frac{dT}{dx}",
        "python": "lambda k, dT, dx: -k * dT / dx",
        "domain": "热力学",
        "unit": "W/m²",
    },
    "newton_cooling": {
        "name": "牛顿冷却定律",
        "latex": r"\frac{dT}{dt} = -h(T - T_{env})",
        "python": "lambda h, T, T_env: -h * (T - T_env)",
        "domain": "热力学",
    },
    "stefan_boltzmann": {
        "name": "斯特藩-玻尔兹曼辐射定律",
        "latex": r"P = \epsilon \sigma A T^4",
        "python": "lambda epsilon, A, T: epsilon * 5.67e-8 * A * T**4",
        "domain": "热力学",
        "unit": "W",
    },
    "arrhenius": {
        "name": "阿伦尼乌斯方程(反应速率与温度)",
        "latex": r"k = A \exp\left(-\frac{E_a}{RT}\right)",
        "python": "lambda A, Ea, T: A * math.exp(-Ea / (8.314 * T))",
        "domain": "化学动力学",
    },
    "clausius_clapeyron": {
        "name": "克劳修斯-克拉伯龙方程(相变)",
        "latex": r"\frac{dP}{dT} = \frac{L}{T \Delta V}",
        "python": "lambda L, T, dV: L / (T * dV)",
        "domain": "热力学",
    },

    # 材料科学
    "fick_diffusion": {
        "name": "菲克第一扩散定律(碳扩散)",
        "latex": r"J = -D \frac{dC}{dx}",
        "python": "lambda D, dC, dx: -D * dC / dx",
        "domain": "材料科学",
        "unit": "mol/(m²·s)",
    },
    "fick_second": {
        "name": "菲克第二定律(浓度随时间变化)",
        "latex": r"\frac{\partial C}{\partial t} = D \frac{\partial^2 C}{\partial x^2}",
        "python": "lambda D, d2C_dx2: D * d2C_dx2",
        "domain": "材料科学",
    },
    "carbon_diffusion_coeff": {
        "name": "碳在γ-Fe中的扩散系数",
        "latex": r"D = D_0 \exp\left(-\frac{Q}{RT}\right), D_0=2.0\times10^{-5}, Q=142kJ/mol",
        "python": "lambda T: 2.0e-5 * math.exp(-142000 / (8.314 * (T + 273.15)))",
        "domain": "材料科学-铁碳",
        "unit": "m²/s",
    },
    "lever_rule": {
        "name": "杠杆定律(相比例计算)",
        "latex": r"f_\alpha = \frac{C_\beta - C_0}{C_\beta - C_\alpha}",
        "python": "lambda C0, C_alpha, C_beta: (C_beta - C0) / (C_beta - C_alpha) if C_beta != C_alpha else 0",
        "domain": "材料科学-铁碳",
    },

    # 控制理论
    "pid_control": {
        "name": "PID控制器输出",
        "latex": r"u(t) = K_p e(t) + K_i \int e(t)dt + K_d \frac{de(t)}{dt}",
        "python": "lambda Kp, Ki, Kd, e, e_integral, e_derivative: Kp*e + Ki*e_integral + Kd*e_derivative",
        "domain": "控制理论",
    },
    "thermal_time_constant": {
        "name": "热时间常数",
        "latex": r"\tau = \frac{mc_p}{hA}",
        "python": "lambda m, cp, h, A: m * cp / (h * A)",
        "domain": "热力学-控制",
        "unit": "s",
    },

    # 统计/误差
    "rmse": {
        "name": "均方根误差",
        "latex": r"RMSE = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(y_i - \hat{y}_i)^2}",
        "python": "lambda y_true, y_pred: (sum((a-b)**2 for a,b in zip(y_true,y_pred))/len(y_true))**0.5",
        "domain": "统计",
    },
    "normal_distribution": {
        "name": "正态分布概率密度",
        "latex": r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}",
        "python": "lambda x, mu, sigma: (1/(sigma*math.sqrt(2*math.pi))) * math.exp(-(x-mu)**2/(2*sigma**2))",
        "domain": "统计",
    },
}


# ==================== 铁碳相图数据(proven) ====================
# 基于Fe-C平衡相图的关键温度和碳含量数据

FE_C_PHASE_DIAGRAM = {
    "critical_points": {
        "A": {"T": 1538, "C": 0.0, "desc": "纯铁熔点"},
        "B": {"T": 1495, "C": 0.53, "desc": "包晶点-液相线"},
        "C": {"T": 1148, "C": 4.30, "desc": "共晶点(莱氏体)"},
        "D": {"T": 1227, "C": 6.69, "desc": "Fe3C分解温度(渗碳体)"},
        "E": {"T": 1148, "C": 2.11, "desc": "碳在γ-Fe中最大溶解度"},
        "F": {"T": 1148, "C": 6.69, "desc": "共晶渗碳体"},
        "G": {"T": 912, "C": 0.0, "desc": "纯铁α↔γ转变"},
        "H": {"T": 1495, "C": 0.09, "desc": "包晶点-δ相线"},
        "J": {"T": 1495, "C": 0.17, "desc": "包晶反应点"},
        "K": {"T": 727, "C": 6.69, "desc": "共析渗碳体"},
        "P": {"T": 727, "C": 0.0218, "desc": "碳在α-Fe中最大溶解度"},
        "S": {"T": 727, "C": 0.77, "desc": "共析点(珠光体)"},
    },
    "phase_boundaries": {
        # 主要相界线的分段线性近似: [(T, C%), ...]
        "liquidus_AC": [(1538, 0.0), (1495, 0.53), (1148, 4.30)],
        "solidus_AE": [(1538, 0.0), (1495, 0.09), (1148, 2.11)],
        "solvus_GP": [(912, 0.0), (727, 0.0218)],
        "solvus_ES": [(1148, 2.11), (727, 0.77)],
        "eutectoid_PSK": [(727, 0.0218), (727, 6.69)],  # 水平共析线
    },
    "phases": {
        "L": "液相(Liquid)",
        "δ": "δ铁素体(BCC, >1394°C)",
        "γ": "奥氏体(Austenite, FCC)",
        "α": "铁素体(Ferrite, BCC)",
        "Fe3C": "渗碳体(Cementite)",
        "P": "珠光体(Pearlite, α+Fe3C共析)",
        "Le": "莱氏体(Ledeburite, γ+Fe3C共晶)",
    },
    "heat_treatments": {
        "退火(Annealing)": {"T_range": (700, 900), "purpose": "消除应力/细化晶粒/降低硬度"},
        "正火(Normalizing)": {"T_range": (870, 930), "purpose": "细化晶粒/改善切削性"},
        "淬火(Quenching)": {"T_range": (780, 860), "purpose": "获得马氏体/提高硬度"},
        "回火(Tempering)": {"T_range": (150, 650), "purpose": "降低脆性/调整硬度韧性平衡"},
        "渗碳(Carburizing)": {"T_range": (900, 950), "purpose": "表面增碳/提高表面硬度"},
    },
}


# ==================== 核心引擎 ====================

class MathFormulaEngine:
    """数学公式编码引擎"""

    def __init__(self):
        self._namespace = {"math": math, "np": None}
        try:
            import numpy as np
            self._namespace["np"] = np
        except ImportError:
            pass

    # ---------- 1. 形式化 ----------
    def formalize(self, problem: str) -> Dict[str, Any]:
        """将自然语言问题形式化为数学表达"""
        # 匹配已知公式模式
        matches = self._match_known_formulas(problem)

        # 提取数值和变量
        variables = self._extract_variables(problem)
        numbers = self._extract_numbers(problem)

        return {
            "original": problem,
            "matched_formulas": matches,
            "variables": variables,
            "numbers": numbers,
            "formalization": self._build_formalization(problem, matches, variables),
        }

    def _match_known_formulas(self, text: str) -> List[Dict]:
        """匹配已知公式"""
        matches = []
        keywords_map = {
            "quadratic": ["二次方程", "求根", "ax²", "ax^2"],
            "heat_transfer": ["热传导", "傅里叶", "热流", "温度梯度"],
            "newton_cooling": ["冷却", "牛顿冷却", "散热"],
            "fick_diffusion": ["扩散", "菲克", "碳扩散", "浓度梯度"],
            "carbon_diffusion_coeff": ["碳扩散系数", "扩散系数", "γ-Fe"],
            "lever_rule": ["杠杆", "相比例", "相含量"],
            "arrhenius": ["阿伦尼乌斯", "反应速率", "活化能"],
            "pid_control": ["PID", "控制器", "温度控制"],
            "stefan_boltzmann": ["辐射", "黑体", "斯特藩"],
            "rmse": ["均方根误差", "RMSE", "误差"],
            "thermal_time_constant": ["时间常数", "热惯性"],
            "fick_second": ["浓度变化", "扩散方程"],
            "clausius_clapeyron": ["相变", "克拉伯龙"],
        }
        for formula_id, keywords in keywords_map.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    f = PROVEN_FORMULAS[formula_id]
                    matches.append({
                        "id": formula_id,
                        "name": f["name"],
                        "latex": f["latex"],
                        "python": f["python"],
                        "domain": f.get("domain", ""),
                    })
                    break
        return matches

    def _extract_variables(self, text: str) -> List[str]:
        """提取文本中的变量符号"""
        import re
        # 匹配温度、碳含量等常见变量
        patterns = {
            "T": r"温度[为是:：]?\s*(\d+\.?\d*)\s*[°℃]?",
            "C": r"碳含量[为是:：]?\s*(\d+\.?\d*)\s*%?",
            "t": r"时间[为是:：]?\s*(\d+\.?\d*)\s*(s|min|h)?",
            "ΔT": r"温差[为是:：]?\s*[±]?(\d+\.?\d*)\s*[°℃]?",
        }
        found = {}
        for var, pattern in patterns.items():
            m = re.search(pattern, text)
            if m:
                found[var] = float(m.group(1))
        return found

    def _extract_numbers(self, text: str) -> List[float]:
        """提取文本中的所有数值"""
        import re
        nums = re.findall(r'(?<![a-zA-Z])(\d+\.?\d*)(?![a-zA-Z])', text)
        return [float(n) for n in nums if n]

    def _build_formalization(self, problem, matches, variables) -> str:
        """构建形式化表达"""
        parts = [f"问题: {problem}"]
        if variables:
            parts.append(f"已知量: {variables}")
        if matches:
            for m in matches:
                parts.append(f"适用公式: {m['name']} → {m['latex']}")
        return "\n".join(parts)

    # ---------- 2. 编码 ----------
    def codify(self, formula_id: str = None, formula_python: str = None,
               variables: Dict = None) -> Dict[str, Any]:
        """将数学公式转为可执行Python代码"""
        if formula_id and formula_id in PROVEN_FORMULAS:
            f = PROVEN_FORMULAS[formula_id]
            code = f["python"]
            name = f["name"]
        elif formula_python:
            code = formula_python
            name = "custom"
        else:
            return {"error": "需要formula_id或formula_python"}

        # 生成可执行代码块
        exec_code = f"""
import math
func = {code}
variables = {variables or {}}
result = func(**variables) if variables else None
"""
        return {
            "name": name,
            "code": code,
            "exec_code": exec_code,
            "variables": variables,
        }

    # ---------- 3. 拆解 ----------
    def decompose(self, problem: str) -> FormulaTree:
        """将复杂问题拆解为公式树"""
        tree = FormulaTree(root_id="root")

        # 形式化
        formal = self.formalize(problem)

        # 创建根节点
        root = MathNode(
            id="root",
            name=problem[:50],
            formula_latex="",
            formula_python="",
            domain=self._detect_domain(problem),
            variables=list(formal.get("variables", {}).keys()),
        )
        tree.nodes["root"] = root

        # 为每个匹配的公式创建子节点
        for i, match in enumerate(formal["matched_formulas"]):
            child_id = f"formula_{i}"
            child = MathNode(
                id=child_id,
                name=match["name"],
                formula_latex=match["latex"],
                formula_python=match["python"],
                domain=match.get("domain", ""),
                parent="root",
            )
            tree.nodes[child_id] = child
            root.children.append(child_id)

        # 构建执行顺序(叶子节点优先)
        tree.execution_order = list(reversed(list(tree.nodes.keys())))

        return tree

    def _detect_domain(self, text: str) -> str:
        """检测问题所属领域"""
        domain_keywords = {
            "热力学": ["温度", "热", "冷却", "加热", "传导", "辐射"],
            "材料科学": ["碳", "铁", "钢", "合金", "晶", "相变", "渗碳", "淬火"],
            "控制理论": ["控制", "PID", "调节", "反馈", "温差"],
            "力学": ["力", "应力", "应变", "弹性", "塑性"],
            "化学": ["反应", "浓度", "速率", "活化能"],
            "代数": ["方程", "求解", "根", "极值"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in text for kw in keywords):
                return domain
        return "general"

    # ---------- 4. 执行与验证 ----------
    def execute(self, formula_id: str = None, formula_python: str = None,
                variables: Dict = None) -> Dict[str, Any]:
        """执行公式并返回结果"""
        if formula_id and formula_id in PROVEN_FORMULAS:
            code = PROVEN_FORMULAS[formula_id]["python"]
            name = PROVEN_FORMULAS[formula_id]["name"]
        elif formula_python:
            code = formula_python
            name = "custom"
        else:
            return {"error": "需要公式"}

        try:
            func = eval(code, {"math": math, "__builtins__": {"abs": abs, "sum": sum, "len": len, "zip": zip, "min": min, "max": max}})
            if variables:
                result = func(**variables)
            else:
                result = None

            return {
                "success": True,
                "name": name,
                "formula": code,
                "variables": variables,
                "result": result,
                "type": type(result).__name__,
            }
        except Exception as e:
            return {
                "success": False,
                "name": name,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ---------- 5. 批量执行公式树 ----------
    def execute_tree(self, tree: FormulaTree, context: Dict = None) -> Dict[str, Any]:
        """执行整棵公式树"""
        if context:
            tree.context.update(context)

        results = {}
        for node_id in tree.execution_order:
            node = tree.nodes[node_id]
            if not node.formula_python:
                continue

            result = self.execute(
                formula_python=node.formula_python,
                variables=tree.context,
            )
            node.verified = result.get("success", False)
            node.result = result.get("result")
            node.error = result.get("error", "")
            results[node_id] = result

            # 将结果写回上下文供后续节点使用
            if node.result is not None:
                tree.context[node.name] = node.result

        return {
            "tree_id": tree.root_id,
            "results": results,
            "context": tree.context,
            "all_verified": all(n.verified for n in tree.nodes.values() if n.formula_python),
        }

    # ---------- 6. 温差推演专用 ----------
    def temperature_differential_analysis(self, T_target: float, C_percent: float,
                                          delta_T: float = 10.0) -> Dict[str, Any]:
        """
        温差推演分析:
        给定目标温度T、碳含量C%、温差范围±delta_T
        分析该条件下的材料学行为
        """
        results = {}

        # 1. 碳扩散系数 at T
        D = self.execute("carbon_diffusion_coeff", variables={"T": T_target})
        results["carbon_diffusion_coeff"] = D

        # 2. 相区判定
        phase = self._determine_phase(T_target, C_percent)
        results["phase"] = phase

        # 3. 温差范围内的扩散系数变化
        T_low = T_target - delta_T
        T_high = T_target + delta_T
        D_low = self.execute("carbon_diffusion_coeff", variables={"T": T_low})
        D_high = self.execute("carbon_diffusion_coeff", variables={"T": T_high})
        results["D_range"] = {
            "T_low": T_low, "D_low": D_low.get("result"),
            "T_high": T_high, "D_high": D_high.get("result"),
            "D_ratio": D_high.get("result", 0) / D_low.get("result", 1e-30) if D_low.get("result") else None,
        }

        # 4. 温差对材料性能的影响评估
        if delta_T > 0:
            sensitivity = abs(
                (D_high.get("result", 0) - D_low.get("result", 0)) / (2 * delta_T)
            ) if D_high.get("result") and D_low.get("result") else 0
            results["temperature_sensitivity"] = {
                "dD/dT": sensitivity,
                "interpretation": self._interpret_sensitivity(sensitivity, T_target),
            }

        # 5. 热时间常数估算(典型钢件)
        # 假设: 10kg钢件, cp=500 J/(kg·K), h=100 W/(m²·K), A=0.1 m²
        tau = self.execute("thermal_time_constant",
                          variables={"m": 10, "cp": 500, "h": 100, "A": 0.1})
        results["thermal_time_constant"] = tau

        # 6. PID温差控制参数建议
        results["pid_suggestion"] = self._suggest_pid_params(delta_T, T_target)

        return {
            "T_target": T_target,
            "C_percent": C_percent,
            "delta_T": delta_T,
            "analysis": results,
        }

    def _determine_phase(self, T: float, C: float) -> Dict:
        """根据铁碳相图判定相区"""
        cp = FE_C_PHASE_DIAGRAM["critical_points"]

        if T > cp["A"]["T"]:
            return {"phase": "L", "desc": "全部液相", "T": T, "C": C}
        if T > cp["E"]["T"]:
            if C < 2.11:
                return {"phase": "L+γ", "desc": "液相+奥氏体两相区", "T": T, "C": C}
            elif C < 4.30:
                return {"phase": "L", "desc": "液相区", "T": T, "C": C}
            else:
                return {"phase": "L+Fe3C", "desc": "液相+渗碳体", "T": T, "C": C}
        if T > cp["S"]["T"]:  # 727-1148°C
            if C < self._interpolate_solvus_ES(T):
                return {"phase": "γ", "desc": "奥氏体单相区", "T": T, "C": C}
            else:
                return {"phase": "γ+Fe3C", "desc": "奥氏体+渗碳体", "T": T, "C": C}
        # < 727°C
        if C < 0.0218:
            return {"phase": "α", "desc": "铁素体单相区", "T": T, "C": C}
        elif C < 0.77:
            return {"phase": "α+P", "desc": "铁素体+珠光体(亚共析钢)", "T": T, "C": C}
        elif abs(C - 0.77) < 0.01:
            return {"phase": "P", "desc": "珠光体(共析钢)", "T": T, "C": C}
        elif C < 2.11:
            return {"phase": "P+Fe3CII", "desc": "珠光体+二次渗碳体(过共析钢)", "T": T, "C": C}
        else:
            return {"phase": "Le'+Fe3CI", "desc": "变态莱氏体+一次渗碳体(白口铸铁)", "T": T, "C": C}

    def _interpolate_solvus_ES(self, T: float) -> float:
        """ES线(碳在γ-Fe中的溶解度)线性插值"""
        # ES: (1148, 2.11) → (727, 0.77)
        if T >= 1148:
            return 2.11
        if T <= 727:
            return 0.77
        return 0.77 + (T - 727) / (1148 - 727) * (2.11 - 0.77)

    def _interpret_sensitivity(self, sensitivity: float, T: float) -> str:
        """解读温度敏感度"""
        if sensitivity < 1e-12:
            return f"在{T}°C附近扩散系数对温度极不敏感，温差控制要求低"
        elif sensitivity < 1e-10:
            return f"在{T}°C附近扩散系数对温度中等敏感，建议温差±5°C"
        else:
            return f"在{T}°C附近扩散系数对温度高度敏感，需精确温差控制±2°C以内"

    def _suggest_pid_params(self, target_delta: float, T: float) -> Dict:
        """根据目标温差和温度建议PID参数"""
        # 经验公式：高温段需要更保守的参数
        if T > 1000:
            Kp, Ki, Kd = 2.0, 0.1, 0.5
        elif T > 600:
            Kp, Ki, Kd = 4.0, 0.3, 1.0
        else:
            Kp, Ki, Kd = 8.0, 0.5, 2.0

        # 温差越小，需要更精细的调节
        if target_delta <= 2:
            Kp *= 0.5
            Ki *= 0.3
            Kd *= 2.0
        elif target_delta <= 5:
            Kp *= 0.7
            Ki *= 0.5
            Kd *= 1.5

        methods = []
        if target_delta >= 20:
            methods = ["开关控制(On/Off)", "时间比例控制", "简单PID"]
        elif target_delta >= 10:
            methods = ["PID控制", "模糊PID", "分段加热"]
        elif target_delta >= 5:
            methods = ["精密PID+热电偶多点测温", "模糊PID+前馈补偿", "多区独立控制"]
        elif target_delta >= 2:
            methods = ["自适应PID+多点温度反馈", "模型预测控制(MPC)", "多区独立PID+均热板"]
        else:
            methods = [
                "模型预测控制(MPC)+高精度传感器",
                "多区独立控制+均热板+辐射屏蔽",
                "材料包覆(隔热层)减小表面温差",
                "梯度加热+旋转工件",
                "等温淬火/分级冷却",
            ]

        return {
            "target_delta_T": target_delta,
            "suggested_Kp": round(Kp, 2),
            "suggested_Ki": round(Ki, 2),
            "suggested_Kd": round(Kd, 2),
            "control_methods": methods,
            "sensor_requirement": f"热电偶精度需≤±{max(0.5, target_delta/4):.1f}°C",
        }

    # ---------- 7. 碰撞推演 ----------
    def four_direction_collision(self, T_start: float, T_end: float, T_step: float,
                                 C_start: float, C_end: float, C_step: float) -> Dict:
        """
        四向碰撞推演：温度×碳含量网格
        在每个(T,C)点计算材料状态，寻找规律
        """
        import numpy as np

        T_range = np.arange(T_start, T_end + T_step, T_step)
        C_range = np.arange(C_start, C_end + C_step, C_step)

        grid = []
        phase_transitions = []  # 记录相变点

        prev_phase = None
        for T in T_range:
            row = []
            for C in C_range:
                phase = self._determine_phase(float(T), float(C))
                D_result = self.execute("carbon_diffusion_coeff", variables={"T": float(T)})
                D = D_result.get("result", 0)

                point = {
                    "T": float(T),
                    "C": float(C),
                    "phase": phase["phase"],
                    "D": D,
                    "desc": phase["desc"],
                }
                row.append(point)

                # 检测相变
                if prev_phase and prev_phase != phase["phase"]:
                    phase_transitions.append({
                        "T": float(T),
                        "C": float(C),
                        "from": prev_phase,
                        "to": phase["phase"],
                    })
                prev_phase = phase["phase"]

            grid.append(row)

        # 总结规律
        patterns = self._summarize_patterns(grid, phase_transitions)

        return {
            "T_range": [float(t) for t in T_range],
            "C_range": [float(c) for c in C_range],
            "grid_size": f"{len(T_range)}×{len(C_range)}",
            "total_points": len(T_range) * len(C_range),
            "phase_transitions": phase_transitions[:50],  # 限制输出
            "patterns": patterns,
        }

    def _summarize_patterns(self, grid, transitions) -> List[str]:
        """从碰撞网格中总结规律"""
        patterns = []

        # 统计各相区出现频次
        phase_counts = {}
        for row in grid:
            for point in row:
                p = point["phase"]
                phase_counts[p] = phase_counts.get(p, 0) + 1

        total = sum(phase_counts.values())
        for phase, count in sorted(phase_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            desc = FE_C_PHASE_DIAGRAM["phases"].get(phase, phase)
            patterns.append(f"{phase}({desc}): {count}点 ({pct:.1f}%)")

        # 相变频率
        if transitions:
            patterns.append(f"共检测到{len(transitions)}个相变边界点")

        # 温度敏感区间
        D_values = []
        for row in grid:
            for point in row:
                if point["D"] and point["D"] > 0:
                    D_values.append((point["T"], point["D"]))
        if D_values:
            D_values.sort(key=lambda x: x[1])
            patterns.append(f"扩散系数范围: {D_values[0][1]:.2e} ({D_values[0][0]}°C) ~ {D_values[-1][1]:.2e} ({D_values[-1][0]}°C)")

        return patterns

    # ---------- 8. 注入proven节点 ----------
    def inject_proven_formulas(self, lattice) -> Dict:
        """将所有proven公式注入认知晶格"""
        injected = 0
        for fid, f in PROVEN_FORMULAS.items():
            content = f"{f['name']}: {f['latex']} → Python: {f['python'][:80]}"
            nid = lattice.add_node(
                content,
                domain=f"数学公式-{f.get('domain', 'general')}",
                status="proven",
                source="math_formula_engine",
                silent=True,
            )
            if nid:
                injected += 1

        # 注入铁碳相图关键数据点
        for pid, p in FE_C_PHASE_DIAGRAM["critical_points"].items():
            content = f"铁碳相图{pid}点: T={p['T']}°C, C={p['C']}%, {p['desc']}"
            nid = lattice.add_node(
                content,
                domain="材料科学-铁碳相图",
                status="proven",
                source="math_formula_engine",
                silent=True,
            )
            if nid:
                injected += 1

        return {"injected": injected}


# ==================== 模块级便捷函数 ====================

_engine = MathFormulaEngine()

def formalize(problem: str) -> Dict:
    return _engine.formalize(problem)

def codify(formula_id: str = None, formula_python: str = None, variables: Dict = None) -> Dict:
    return _engine.codify(formula_id, formula_python, variables)

def execute(formula_id: str = None, formula_python: str = None, variables: Dict = None) -> Dict:
    return _engine.execute(formula_id, formula_python, variables)

def decompose(problem: str) -> Dict:
    tree = _engine.decompose(problem)
    return {"root": tree.root_id, "nodes": {k: asdict(v) for k, v in tree.nodes.items()}}

def temperature_analysis(T: float, C: float, delta_T: float = 10.0) -> Dict:
    return _engine.temperature_differential_analysis(T, C, delta_T)

def collision(T_start=25, T_end=1600, T_step=100, C_start=0, C_end=6.69, C_step=0.5) -> Dict:
    return _engine.four_direction_collision(T_start, T_end, T_step, C_start, C_end, C_step)

def inject_formulas(lattice) -> Dict:
    return _engine.inject_proven_formulas(lattice)

def list_formulas() -> List[Dict]:
    return [{"id": k, "name": v["name"], "latex": v["latex"], "domain": v.get("domain","")}
            for k, v in PROVEN_FORMULAS.items()]


# ==================== 自测 ====================

if __name__ == "__main__":
    engine = MathFormulaEngine()

    print("=" * 60)
    print("数学公式编码引擎 自测")
    print("=" * 60)

    # 1. 执行已知公式
    print("\n[1] 碳扩散系数 at 900°C:")
    r = engine.execute("carbon_diffusion_coeff", variables={"T": 900})
    print(f"  D = {r['result']:.4e} m²/s")

    # 2. 相区判定
    print("\n[2] 相区判定:")
    for T, C in [(25, 0.4), (727, 0.77), (900, 0.5), (1200, 3.0)]:
        p = engine._determine_phase(T, C)
        print(f"  T={T}°C, C={C}% → {p['phase']} ({p['desc']})")

    # 3. 温差推演
    print("\n[3] 温差推演 at 900°C, C=0.5%, ΔT=10°C:")
    r = engine.temperature_differential_analysis(900, 0.5, 10)
    a = r["analysis"]
    print(f"  相区: {a['phase']['desc']}")
    print(f"  D范围: {a['D_range']['D_low']:.4e} ~ {a['D_range']['D_high']:.4e}")
    print(f"  温度敏感度: {a['temperature_sensitivity']['interpretation']}")
    print(f"  PID建议: {a['pid_suggestion']['control_methods']}")

    # 4. 小规模碰撞
    print("\n[4] 碰撞推演 (室温~1600°C, C: 0~6.69%, 粗网格):")
    r = engine.four_direction_collision(25, 1600, 200, 0, 6.69, 1.0)
    print(f"  网格: {r['grid_size']}, {r['total_points']}点")
    for p in r["patterns"]:
        print(f"  {p}")

    print("\n✅ 自测完成")
