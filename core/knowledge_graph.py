"""
knowledge_graph.py — 刀模行业知识图谱
材料→工艺→设备→标准→误差 的关系图谱

基于已确认的30条已知(F)和11条待解决(V)构建
推演任务: dp_1774574718408_8c3ee3 (刀模行业知识图谱)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum


class NodeType(Enum):
    MATERIAL = "material"           # 材料(灰板/瓦楞/微瓦楞/塑料)
    FLUTE = "flute"                 # 楞型(A/B/C/E/F/N/AB/BC/EB/EF)
    MACHINE = "machine"             # 设备
    PROCESS = "process"             # 工序(模切/裱合/压痕/清废)
    STANDARD = "standard"           # 标准(FEFCO/GB/JIS/DIN/ECMA)
    TOLERANCE = "tolerance"         # 公差等级
    ERROR_SOURCE = "error_source"   # 误差源
    FORMULA = "formula"             # 公式/规则
    MARKET = "market"               # 市场(亚洲/欧洲)


class EdgeType(Enum):
    REQUIRES = "requires"           # 需要
    PRODUCES = "produces"           # 产生
    CONSTRAINED_BY = "constrained"  # 受限于
    COMPENSATED_BY = "compensated"  # 补偿
    AFFECTS = "affects"             # 影响
    DERIVED_FROM = "derived"        # 派生自
    CONFLICTS = "conflicts"         # 冲突


@dataclass
class KGNode:
    """知识图谱节点"""
    node_id: str
    node_type: NodeType
    label: str
    properties: Dict = field(default_factory=dict)
    confidence: float = 1.0  # 0-1, 来源确认度

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        return isinstance(other, KGNode) and self.node_id == other.node_id


@dataclass
class KGEdge:
    """知识图谱边"""
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: Dict = field(default_factory=dict)

    def __hash__(self):
        return hash((self.source_id, self.target_id, self.edge_type))


class KnowledgeGraph:
    """刀模行业知识图谱"""

    def __init__(self):
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []
        self._adjacency: Dict[str, List[KGEdge]] = {}
        self._built = False

    def add_node(self, node: KGNode):
        self.nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = []

    def add_edge(self, edge: KGEdge):
        self.edges.append(edge)
        if edge.source_id in self._adjacency:
            self._adjacency[edge.source_id].append(edge)

    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[KGNode]:
        """获取邻居节点"""
        result = []
        for edge in self._adjacency.get(node_id, []):
            if edge_type and edge.edge_type != edge_type:
                continue
            if edge.target_id in self.nodes:
                result.append(self.nodes[edge.target_id])
        return result

    def get_path(self, start: str, end: str) -> Optional[List[str]]:
        """BFS最短路径"""
        if start not in self.nodes or end not in self.nodes:
            return None
        from collections import deque
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            current, path = queue.popleft()
            if current == end:
                return path
            for edge in self._adjacency.get(current, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, path + [edge.target_id]))
        return None

    def get_error_chain(self, material_id: str) -> List[Dict]:
        """获取某材料的完整误差链"""
        chain = []
        visited = set()
        self._trace_errors(material_id, chain, visited)
        return chain

    def _trace_errors(self, node_id: str, chain: List[Dict], visited: Set):
        if node_id in visited:
            return
        visited.add(node_id)
        node = self.nodes.get(node_id)
        if not node:
            return
        for edge in self._adjacency.get(node_id, []):
            target = self.nodes.get(edge.target_id)
            if not target or target.node_type == NodeType.ERROR_SOURCE:
                chain.append({
                    "from": node.label,
                    "to": target.label if target else "?",
                    "type": edge.edge_type.value,
                    "weight": edge.weight,
                    "detail": edge.properties
                })
            self._trace_errors(edge.target_id, chain, visited)

    def query(self, node_type: NodeType, **props) -> List[KGNode]:
        """按类型和属性查询节点"""
        results = []
        for node in self.nodes.values():
            if node.node_type != node_type:
                continue
            match = True
            for k, v in props.items():
                if node.properties.get(k) != v:
                    match = False
                    break
            if match:
                results.append(node)
        return results

    def stats(self) -> Dict:
        """图谱统计"""
        type_counts = {}
        for node in self.nodes.values():
            t = node.node_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        edge_type_counts = {}
        for edge in self.edges:
            t = edge.edge_type.value
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "by_type": type_counts,
            "by_edge": edge_type_counts,
            "avg_confidence": sum(n.confidence for n in self.nodes.values()) / max(len(self.nodes), 1)
        }

    def build_diepre_graph(self):
        """构建DiePre完整知识图谱（基于30条已确认已知）"""
        if self._built:
            return

        # === 材料 ===
        materials = [
            ("mat_grayboard", "灰板", {"density_range": "0.8-1.2", "thickness": "0.5-3.0mm", "k_factor": 0.37}),
            ("mat_single_wall", "单瓦楞纸板", {"flute_options": "A/B/C/E/F", "thickness": "1.5-8mm"}),
            ("mat_double_wall", "双瓦楞纸板", {"flute_options": "AB/BC/EB", "thickness": "5-12mm", "k_factor": 0.40}),
            ("mat_micro_flute", "微瓦楞纸板", {"flute_options": "E/F/N/EF", "thickness": "0.8-2.0mm", "k_factor": 0.42}),
            ("mat_plastic", "塑料片材", {"types": "PET/PVC/PP", "k_factor": 0.50}),
        ]
        for mid, label, props in materials:
            self.add_node(KGNode(mid, NodeType.MATERIAL, label, props))

        # === 楞型 ===
        flutes = [
            ("fl_A", "A楞", {"thickness_mm": 4.8, "flutes_per_m": 110, "use": "缓冲包装"}),
            ("fl_B", "B楞", {"thickness_mm": 3.0, "flutes_per_m": 170, "use": "印刷纸箱"}),
            ("fl_C", "C楞", {"thickness_mm": 3.8, "flutes_per_m": 140, "use": "运输包装"}),
            ("fl_E", "E楞", {"thickness_mm": 1.8, "flutes_per_m": 290, "use": "展示盒"}),
            ("fl_F", "F楞", {"thickness_mm": 0.9, "flutes_per_m": 410, "use": "微型包装"}),
            ("fl_N", "N楞", {"thickness_mm": 0.6, "flutes_per_m": 550, "use": "精密电子"}),
            ("fl_AB", "AB双瓦", {"thickness_mm": 7.8, "flutes_per_m": 0, "use": "重型包装"}),
            ("fl_BC", "BC双瓦", {"thickness_mm": 6.8, "flutes_per_m": 0, "use": "电商包装"}),
            ("fl_EF", "EF微双", {"thickness_mm": 2.7, "flutes_per_m": 0, "use": "高端化妆品"}),
        ]
        for fid, label, props in flutes:
            self.add_node(KGNode(fid, NodeType.FLUTE, label, props))

        # === 设备 ===
        machines = [
            ("mach_bobst", "Bobst SPRINT", {"precision_mm": 0.15, "type": "flatbed", "thermal_drift": 0.065, "country": "瑞士"}),
            ("mach_heidelberg", "Heidelberg Dymatrix", {"precision_mm": 0.20, "type": "flatbed", "thermal_drift": 0.05, "country": "德国"}),
            ("mach_domestic", "国产标准模切机", {"precision_mm": 0.30, "type": "flatbed", "thermal_drift": 0.10, "country": "中国"}),
            ("mach_rotary_bobst", "Bobst Visioncut", {"precision_mm": 0.25, "type": "rotary", "thermal_drift": 0.08, "country": "瑞士"}),
        ]
        for mid, label, props in machines:
            self.add_node(KGNode(mid, NodeType.MACHINE, label, props))

        # === 工序 ===
        processes = [
            ("proc_diecut", "模切", {"type": "flatbed/rotary", "primary": True}),
            ("proc_laminate", "裱合", {"coupling_errors": 3, "description": "胶水收缩+面纸膨胀+张力差异"}),
            ("proc_crease", "压痕", {"depth_ratio": "0.45T-0.55T", "critical": True}),
            ("proc_stripping", "清废", {"critical_angle_deg": 15, "blade_angle_effect": True}),
            ("proc_print", "印刷", {"mc_change": "±2-4%", "registration": 0.15}),
        ]
        for pid, label, props in processes:
            self.add_node(KGNode(pid, NodeType.PROCESS, label, props))

        # === 标准 ===
        standards = [
            ("std_fefco", "FEFCO", {"region": "欧洲", "tolerance_mm": 0.5, "size_basis": "内尺寸"}),
            ("std_ecma", "ECMA", {"region": "欧洲", "tolerance_mm": 0.3, "size_basis": "内尺寸"}),
            ("std_gb", "GB/T 6543", {"region": "中国", "tolerance_mm": 1.5, "size_basis": "外尺寸", "blind_spots": 4}),
            ("std_jis", "JIS Z 1506", {"region": "日本", "tolerance_mm": 0.8, "size_basis": "外尺寸", "has_micro_flute": True}),
            ("std_din", "DIN 55445", {"region": "德国", "tolerance_mm": 0.5, "size_basis": "外尺寸"}),
        ]
        for sid, label, props in standards:
            self.add_node(KGNode(sid, NodeType.STANDARD, label, props))

        # === 误差源 ===
        errors = [
            ("err_mc", "含水量变化(MC)", {"impact": "最大", "sensitive_range": "10-16%", "correction": "MC兼容±2%"}),
            ("err_thermal", "热膨胀", {"bobst_30min_mm": 0.065, "heidelberg_30min_mm": 0.05}),
            ("err_moisture_absorb", "吸湿收缩", {"curve_type": "S型Logistic", "k_range": "40-60", "mc_mid": "12%"}),
            ("err_moisture_desorb", "脱湿收缩", {"asymmetry": True, "k_absorb_neq_k_desorb": True}),
            ("err_laminate_glue", "裱合胶水收缩", {"coupling": True, "direction": "拉力"}),
            ("err_laminate_face", "裱合面纸膨胀", {"coupling": True, "direction": "推力"}),
            ("err_laminate_tension", "裱合张力差异", {"coupling": True}),
            ("err_fan", "扇形误差", {"formula": "L²/(8R)+thermal", "centrifugal": "negligible"}),
            ("err_k_phase", "K因子相变", {"critical_ratio": 0.65, "mc_critical": 16, "type": "discontinuous"}),
            ("err_asian_collapse", "亚洲纸板塌陷", {"compensation_mm": 0.15, "europe_compensation": 0}),
        ]
        for eid, label, props in errors:
            self.add_node(KGNode(eid, NodeType.ERROR_SOURCE, label, props))

        # === 公式 ===
        formulas = [
            ("fm_rss", "RSS误差合成", {"formula": "sqrt(sum(σi²))", "correction": "k=1.15-1.25"}),
            ("fm_fefco_tuck", "FEFCO插舌公式", {"formula": "W=t+C_res", "tuck": "W-1.5t-0.5mm"}),
            ("fm_crease_depth", "压痕深度", {"formula": "0.45T-0.55T", "double_wall": "0.45T(浅10%)"}),
            ("fm_fan", "扇形误差", {"formula": "L²/(8R)", "thermal_add": True}),
            ("fm_rss_nonnormal", "非正态RSS修正", {"distributions": "正态/均匀/偏态/瑞利/线性趋势"}),
            ("fm_precision_limit", "精度极限", {"bobst_mm": 0.687, "domestic_mm": 1.155, "note": "±0.5mm不可达"}),
            ("fm_micro_flute", "微瓦楞修正", {"formula": "W=(t+C_res)×K_stru", "note": "不可套用FEFCO"}),
        ]
        for fid, label, props in formulas:
            self.add_node(KGNode(fid, NodeType.FORMULA, label, props))

        # === 市场 ===
        markets = [
            ("mkt_asia", "亚洲市场", {"collapse_compensation": 0.15, "mc_tolerance": "较宽松"}),
            ("mkt_europe", "欧洲市场", {"collapse_compensation": 0, "mc_tolerance": "严格", "primary_std": "FEFCO"}),
        ]
        for mid, label, props in markets:
            self.add_node(KGNode(mid, NodeType.MARKET, label, props))

        # === 关系（边）===
        # 材料→楞型
        self.add_edge(KGEdge("mat_single_wall", "fl_A", EdgeType.REQUIRES, 0.8))
        self.add_edge(KGEdge("mat_single_wall", "fl_B", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_single_wall", "fl_C", EdgeType.REQUIRES, 0.7))
        self.add_edge(KGEdge("mat_single_wall", "fl_E", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_micro_flute", "fl_E", EdgeType.REQUIRES, 0.6))
        self.add_edge(KGEdge("mat_micro_flute", "fl_F", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_micro_flute", "fl_N", EdgeType.REQUIRES, 0.8))
        self.add_edge(KGEdge("mat_double_wall", "fl_AB", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_double_wall", "fl_BC", EdgeType.REQUIRES, 0.8))

        # 工序→误差源
        self.add_edge(KGEdge("proc_laminate", "err_laminate_glue", EdgeType.PRODUCES, 0.8))
        self.add_edge(KGEdge("proc_laminate", "err_laminate_face", EdgeType.PRODUCES, 0.8))
        self.add_edge(KGEdge("proc_laminate", "err_laminate_tension", EdgeType.PRODUCES, 0.7))
        self.add_edge(KGEdge("proc_diecut", "err_thermal", EdgeType.PRODUCES, 0.9))
        self.add_edge(KGEdge("proc_crease", "err_k_phase", EdgeType.PRODUCES, 0.6))
        self.add_edge(KGEdge("proc_stripping", "err_k_phase", EdgeType.PRODUCES, 0.4))

        # 误差源→公式
        self.add_edge(KGEdge("err_laminate_glue", "fm_rss", EdgeType.DERIVED_FROM, 0.9))
        self.add_edge(KGEdge("err_laminate_face", "fm_rss", EdgeType.DERIVED_FROM, 0.9))
        self.add_edge(KGEdge("err_thermal", "fm_rss", EdgeType.DERIVED_FROM, 0.9))
        self.add_edge(KGEdge("err_fan", "fm_fan", EdgeType.DERIVED_FROM, 1.0))
        self.add_edge(KGEdge("err_k_phase", "fm_precision_limit", EdgeType.AFFECTS, 0.8))

        # MC→多个误差
        self.add_edge(KGEdge("err_mc", "err_moisture_absorb", EdgeType.PRODUCES, 0.95))
        self.add_edge(KGEdge("err_mc", "err_moisture_desorb", EdgeType.PRODUCES, 0.95))
        self.add_edge(KGEdge("err_mc", "err_asian_collapse", EdgeType.AFFECTS, 0.7))
        self.add_edge(KGEdge("err_mc", "err_k_phase", EdgeType.AFFECTS, 0.6))

        # 材料→工序
        self.add_edge(KGEdge("mat_grayboard", "proc_laminate", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_double_wall", "proc_diecut", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mat_micro_flute", "proc_diecut", EdgeType.REQUIRES, 0.9))

        # 设备→工序
        self.add_edge(KGEdge("mach_bobst", "proc_diecut", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mach_heidelberg", "proc_diecut", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("mach_rotary_bobst", "proc_diecut", EdgeType.REQUIRES, 0.9))

        # 设备→精度
        self.add_edge(KGEdge("mach_bobst", "fm_precision_limit", EdgeType.CONSTRAINED_BY, 0.95))
        self.add_edge(KGEdge("mach_domestic", "fm_precision_limit", EdgeType.CONSTRAINED_BY, 0.95))

        # 标准→公式
        self.add_edge(KGEdge("std_fefco", "fm_fefco_tuck", EdgeType.DERIVED_FROM, 1.0))
        self.add_edge(KGEdge("std_fefco", "fm_crease_depth", EdgeType.DERIVED_FROM, 0.9))

        # 微瓦楞特殊处理
        self.add_edge(KGEdge("fl_F", "fm_micro_flute", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("fl_N", "fm_micro_flute", EdgeType.REQUIRES, 0.9))
        self.add_edge(KGEdge("fm_micro_flute", "std_jis", EdgeType.CONSTRAINED_BY, 0.8))
        self.add_edge(KGEdge("fm_micro_flute", "std_fefco", EdgeType.CONFLICTS, 0.7))

        # 市场→补偿
        self.add_edge(KGEdge("mkt_asia", "err_asian_collapse", EdgeType.COMPENSATED_BY, 0.8))
        self.add_edge(KGEdge("mkt_europe", "std_fefco", EdgeType.CONSTRAINED_BY, 0.9))

        # 非正态修正
        self.add_edge(KGEdge("fm_rss", "fm_rss_nonnormal", EdgeType.DERIVED_FROM, 0.85))

        # 吸湿不对称
        self.add_edge(KGEdge("err_moisture_absorb", "err_moisture_desorb", EdgeType.CONFLICTS, 0.9, {"note": "吸湿≠脱湿路径"}))

        self._built = True

    def get_tolerance_for_combo(self, material_id: str, machine_id: str, market_id: str) -> Dict:
        """查询材料+设备+市场组合的总公差"""
        if not self._built:
            self.build_diepre_graph()

        result = {
            "material": self.nodes[material_id].label if material_id in self.nodes else material_id,
            "machine": self.nodes[machine_id].label if machine_id in self.nodes else machine_id,
            "market": self.nodes[market_id].label if market_id in self.nodes else market_id,
            "machine_precision_mm": self.nodes[machine_id].properties.get("precision_mm", 0.5) if machine_id in self.nodes else 0.5,
            "market_compensation_mm": 0.0,
            "error_sources": [],
            "total_budget_mm": 0.0,
            "achievable_grades": [],
        }

        # 市场补偿
        if market_id == "mkt_asia":
            result["market_compensation_mm"] = 0.15

        # 误差链
        chain = self.get_error_chain(material_id)
        result["error_sources"] = [e["to"] for e in chain if e.get("to")]

        # RSS合成
        machine_prec = result["machine_precision_mm"]
        import math
        sigma_sq = machine_prec ** 2
        # 加入典型误差源
        sigma_sq += 0.08 ** 2   # 热膨胀
        sigma_sq += 0.10 ** 2   # MC影响
        sigma_sq += 0.05 ** 2   # 材料变异
        rss_total = math.sqrt(sigma_sq) * 1.2  # k=1.2安全系数
        result["total_budget_mm"] = round(rss_total, 3)

        # 可达公差等级
        if rss_total <= 0.4:
            result["achievable_grades"] = ["precision"]
        elif rss_total <= 0.8:
            result["achievable_grades"] = ["standard", "precision"]
        elif rss_total <= 1.5:
            result["achievable_grades"] = ["commercial", "standard"]
        else:
            result["achievable_grades"] = ["industrial", "commercial"]

        return result

    def find_critical_path(self, target_tolerance_mm: float) -> Dict:
        """反查达到目标公差的关键约束"""
        if not self._built:
            self.build_diepre_graph()

        import math
        # 精度极限
        bobst_limit = self.nodes["mach_bobst"].properties["precision_mm"]
        domestic_limit = self.nodes["mach_domestic"].properties["precision_mm"]

        # RSS最小值(仅机器精度+热膨胀)
        rss_min_bobst = math.sqrt(bobst_limit**2 + 0.065**2 + 0.08**2 + 0.05**2) * 1.15
        rss_min_domestic = math.sqrt(domestic_limit**2 + 0.10**2 + 0.10**2 + 0.05**2) * 1.15

        achievable = target_tolerance_mm >= rss_min_bobst

        return {
            "target_tolerance_mm": target_tolerance_mm,
            "achievable": achievable,
            "bobst_rss_mm": round(rss_min_bobst, 3),
            "domestic_rss_mm": round(rss_min_domestic, 3),
            "recommendation": (
                f"Bobst最小可达{rss_min_bobst:.3f}mm, 国产{rss_min_domestic:.3f}mm. "
                f"目标{target_tolerance_mm}mm {'可达' if achievable else '不可达(需更高精度设备)'}"
            ),
            "tightest_constraints": [
                {"source": "设备精度", "bobst_mm": bobst_limit, "domestic_mm": domestic_limit},
                {"source": "热膨胀", "mm": 0.065},
                {"source": "MC影响", "mm": 0.08},
            ]
        }


# === 快速测试 ===
if __name__ == "__main__":
    kg = KnowledgeGraph()
    kg.build_diepre_graph()
    stats = kg.stats()
    print(f"知识图谱: {stats['total_nodes']}节点, {stats['total_edges']}条边")
    print(f"节点类型: {stats['by_type']}")
    print(f"平均置信度: {stats['avg_confidence']:.2f}")

    # 测试公差查询
    print("\n--- 公差查询 ---")
    result = kg.get_tolerance_for_combo("mat_double_wall", "mach_bobst", "mkt_europe")
    print(f"双瓦楞+Bobst+欧洲: 总公差={result['total_budget_mm']}mm, 等级={result['achievable_grades']}")

    result2 = kg.get_tolerance_for_combo("mat_single_wall", "mach_domestic", "mkt_asia")
    print(f"单瓦楞+国产+亚洲: 总公差={result2['total_budget_mm']}mm, 等级={result2['achievable_grades']}")

    # 精度反查
    print("\n--- 精度反查 ---")
    for tol in [0.3, 0.5, 1.0]:
        analysis = kg.find_critical_path(tol)
        print(f"目标±{tol}mm: {analysis['recommendation']}")

    # 路径查询
    print("\n--- 路径查询 ---")
    path = kg.get_path("mat_micro_flute", "std_jis")
    print(f"微瓦楞→JIS: {' → '.join(kg.nodes[nid].label for nid in path) if path else '无路径'}")

    # 误差链
    print("\n--- 误差链 ---")
    chain = kg.get_error_chain("mat_grayboard")
    for c in chain[:5]:
        print(f"  {c['from']} → {c['to']} ({c['type']})")
