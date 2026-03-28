#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiePre AI 框架精髓提取 — 优化AGI自成长能力
从 DiePreAI 项目提炼6大核心模式，映射到代码领域自成长引擎

核心模式:
  1. 固定/可变双轨分类 (Dual-Track Classification)
  2. 参数收敛追踪器 (Convergence Tracker)
  3. 零回避风险扫描 (Zero-Avoidance Scanner)
  4. 6阶段管线门控 (Pipeline Stage Gate)
  5. RSS置信度合成 (RSS Confidence Composition)
  6. 成长会话记录 (Growth Session Recorder)

来源: /Users/administruter/Desktop/DiePre AI/DiePreAI/
  - DiePre_AI_Skill.md: 触发协议 + 推演管线 + 成长性设计
  - 融合任务清单_零回避版.md: 120项任务 / 12大阶段
  - Claude_需求理解.md: 82固定+46可变+35灾难
"""

import json
import math
import time
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# ==================== 模式1: 固定/可变双轨分类 ====================
# DiePre核心: 82项固定规则(物理定律/行业标准) + 46项可变参数(经验值)
# AGI映射: proven_node高置信度=固定, 低置信度=可变, 可变可升级为固定

class DualTrackClassifier:
    """固定/可变双轨节点分类器
    
    DiePre原理:
      - 固定框架: 物理定律/数学约束/行业标准 → 不可违反, 只增不减
      - 可变参数: 经验系数/校准值 → 持续收敛, 收敛后可升级为固定
    
    AGI映射:
      - fixed_rule: confidence ≥ 0.9 且经过3次以上验证 → 永久保留
      - variable_param: confidence < 0.9 → 需要更多验证数据
      - 升级路径: variable → fixed (当σ_sliding < threshold)
    """
    
    FIXED_THRESHOLD = 0.90      # 置信度 ≥ 此值 → 固定规则候选
    PROMOTION_COUNT = 3          # 验证次数 ≥ 此值 → 可升级
    DEMOTION_THRESHOLD = 0.50    # 置信度 < 此值 → 降级或淘汰
    
    @staticmethod
    def classify(node: dict) -> str:
        """分类节点为 fixed_rule / variable_param / hypothesis / deprecated"""
        conf = node.get("confidence", 0.5)
        verify_count = node.get("verify_count", 0)
        node_type = node.get("type", "hypothesis")
        
        if conf >= DualTrackClassifier.FIXED_THRESHOLD and verify_count >= DualTrackClassifier.PROMOTION_COUNT:
            return "fixed_rule"
        elif conf >= 0.6:
            return "variable_param"
        elif conf >= DualTrackClassifier.DEMOTION_THRESHOLD:
            return "hypothesis"
        else:
            return "deprecated"
    
    @staticmethod
    def can_promote(node: dict, convergence_sigma: float) -> bool:
        """判断可变参数是否可升级为固定规则
        DiePre原理: σ_sliding < 0.01 → 已收敛 → 考虑升级"""
        conf = node.get("confidence", 0.5)
        verify_count = node.get("verify_count", 0)
        return (conf >= DualTrackClassifier.FIXED_THRESHOLD 
                and verify_count >= DualTrackClassifier.PROMOTION_COUNT
                and convergence_sigma < 0.05)
    
    @staticmethod
    def batch_classify(nodes: List[dict]) -> Dict[str, List[dict]]:
        """批量分类节点"""
        result = {"fixed_rule": [], "variable_param": [], "hypothesis": [], "deprecated": []}
        for nd in nodes:
            track = DualTrackClassifier.classify(nd)
            result[track].append(nd)
        return result


# ==================== 模式2: 参数收敛追踪器 ====================
# DiePre原理: 每个可变参数维护历史值列表, 计算滑动σ
# σ < threshold → 已收敛 → 升级为固定; σ > threshold → 高波动 → 需更多数据

class ConvergenceTracker:
    """参数收敛追踪器
    
    DiePre原理 (DiePre_AI_Skill.md §5.1):
      对于每个可变参数P:
      - 维护历史值列表 [v₁, v₂, ..., vₙ]
      - 计算滑动标准差 σ_sliding(last 10)
      - σ < 0.01 → 已收敛 → 考虑升级为固定规则
      - σ > 0.1  → 高波动 → 需更多数据或拆分为子参数
    """
    
    CONVERGED_SIGMA = 0.05       # σ < 此值 → 已收敛
    HIGH_VOLATILITY_SIGMA = 0.30 # σ > 此值 → 高波动
    WINDOW_SIZE = 10             # 滑动窗口大小
    
    def __init__(self):
        self._history: Dict[str, List[float]] = {}  # domain/param → [confidence_values]
        self._lock = threading.Lock()
    
    def record(self, key: str, value: float):
        """记录一个参数值"""
        with self._lock:
            if key not in self._history:
                self._history[key] = []
            self._history[key].append(value)
            # 只保留最近 WINDOW_SIZE*3 个值
            if len(self._history[key]) > self.WINDOW_SIZE * 3:
                self._history[key] = self._history[key][-self.WINDOW_SIZE * 3:]
    
    def sigma(self, key: str) -> float:
        """计算滑动标准差"""
        with self._lock:
            values = self._history.get(key, [])
        if len(values) < 2:
            return 1.0  # 数据不足, 视为高波动
        window = values[-self.WINDOW_SIZE:]
        mean = sum(window) / len(window)
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        return math.sqrt(variance)
    
    def status(self, key: str) -> str:
        """获取参数收敛状态"""
        s = self.sigma(key)
        if s < self.CONVERGED_SIGMA:
            return "converged"
        elif s > self.HIGH_VOLATILITY_SIGMA:
            return "high_volatility"
        else:
            return "converging"
    
    def convergence_report(self) -> Dict[str, Any]:
        """生成收敛报告 (DiePre §5.1: 每10次验证自动生成成长报告)"""
        with self._lock:
            keys = list(self._history.keys())
        
        report = {"converged": [], "converging": [], "high_volatility": [], "insufficient_data": []}
        for key in keys:
            values = self._history.get(key, [])
            if len(values) < 3:
                report["insufficient_data"].append({"key": key, "count": len(values)})
                continue
            s = self.sigma(key)
            entry = {"key": key, "sigma": round(s, 4), "count": len(values),
                     "latest": round(values[-1], 3) if values else 0,
                     "mean": round(sum(values[-self.WINDOW_SIZE:]) / min(len(values), self.WINDOW_SIZE), 3)}
            status = self.status(key)
            report[status].append(entry)
        
        report["summary"] = {
            "total_params": len(keys),
            "converged_count": len(report["converged"]),
            "converging_count": len(report["converging"]),
            "volatile_count": len(report["high_volatility"]),
            "convergence_rate": len(report["converged"]) / max(len(keys), 1)
        }
        return report


# ==================== 模式3: 零回避风险扫描 ====================
# DiePre核心: 35类灾难, 每类 = 触发条件→量化后果→风险等级→检测方法→预防
# AGI映射: 代码SKILL必须扫描失败模式, 不可说"一般不会出问题"

class ZeroAvoidanceScanner:
    """零回避风险扫描器
    
    DiePre原理 (融合任务清单 §E):
      - 推演时不可隐藏风险, 即使概率低也必须列出
      - 不可说"一般不会出问题"
      - 每类灾难格式: 触发条件→量化后果→风险等级→检测方法→预防措施
    
    AGI映射:
      - 每个代码SKILL必须附带failure_modes列表
      - 每个proven_node必须标注已知局限性
      - 灾难知识进化: 1次=疑似, 2次=确认, 5次=完全量化
    """
    
    # 代码领域通用灾难库 (从DiePre的35类灾难模式提炼)
    CODE_DISASTER_TEMPLATES = [
        {"id": "CD01", "name": "边界条件遗漏", "trigger": "未处理空输入/极大输入/负数/None",
         "consequence": "运行时崩溃, 数据损坏", "level": "🔴致命", "detection": "边界测试"},
        {"id": "CD02", "name": "并发竞态", "trigger": "多线程共享可变状态无锁",
         "consequence": "数据不一致, 死锁, 结果随机", "level": "🔴致命", "detection": "压力测试+TSan"},
        {"id": "CD03", "name": "内存泄漏", "trigger": "循环引用/未释放资源/无限增长缓存",
         "consequence": "OOM崩溃, 性能退化", "level": "🟡严重", "detection": "profiler+长时运行"},
        {"id": "CD04", "name": "类型不匹配", "trigger": "动态类型语言中隐式转换",
         "consequence": "静默错误, 计算结果偏差", "level": "🟡严重", "detection": "类型检查+mypy"},
        {"id": "CD05", "name": "依赖版本冲突", "trigger": "未锁定依赖版本",
         "consequence": "构建失败, 行为变化", "level": "🟠中等", "detection": "lock文件+CI"},
        {"id": "CD06", "name": "异常吞没", "trigger": "bare except / pass",
         "consequence": "错误被隐藏, 调试困难", "level": "🟡严重", "detection": "代码审查"},
        {"id": "CD07", "name": "SQL注入/命令注入", "trigger": "字符串拼接构建查询/命令",
         "consequence": "数据泄露, 系统被入侵", "level": "🔴致命", "detection": "SAST扫描"},
        {"id": "CD08", "name": "API超时无处理", "trigger": "外部调用无timeout/retry",
         "consequence": "线程阻塞, 级联故障", "level": "🟡严重", "detection": "混沌测试"},
        {"id": "CD09", "name": "硬编码配置", "trigger": "密钥/路径/URL写入代码",
         "consequence": "安全风险, 环境切换困难", "level": "🟠中等", "detection": "secret扫描"},
        {"id": "CD10", "name": "算法复杂度爆炸", "trigger": "O(n²)或更差在大数据集上",
         "consequence": "超时, 资源耗尽", "level": "🟡严重", "detection": "性能基准测试"},
        {"id": "CD11", "name": "状态一致性破坏", "trigger": "中途失败无回滚/事务",
         "consequence": "数据库/文件系统处于不一致状态", "level": "🔴致命", "detection": "事务测试"},
        {"id": "CD12", "name": "精度丢失", "trigger": "浮点运算累积/整数溢出",
         "consequence": "结果偏差>容忍范围", "level": "🟠中等", "detection": "数值验证"},
    ]
    
    @classmethod
    def scan_skill(cls, skill_code: str, skill_meta: dict) -> List[dict]:
        """扫描SKILL代码的潜在灾难
        返回: [{disaster_id, name, trigger, risk_level, matched_pattern}]"""
        risks = []
        code_lower = skill_code.lower()
        
        # 规则扫描
        patterns = [
            ("CD01", ["def execute", "**kwargs"], lambda c: "if not" not in c and "is none" not in c),
            ("CD02", ["thread", "lock"], lambda c: "threading" in c and "lock" not in c),
            ("CD03", ["cache", "dict", "list"], lambda c: "max_size" not in c and ".clear()" not in c and len(c) > 200),
            ("CD06", ["except:", "except Exception"], lambda c: "pass" in c.split("except")[-1][:50] if "except" in c else False),
            ("CD07", ["cursor.execute", "f\"", "format("], lambda c: "?" not in c and "%s" not in c and "paramstyle" not in c),
            ("CD08", ["requests.", "urlopen", "http"], lambda c: "timeout" not in c),
            ("CD09", ["api_key", "password", "secret"], lambda c: "os.environ" not in c and "getenv" not in c),
            ("CD10", ["for ", "for "], lambda c: c.count("for ") >= 3),
        ]
        
        for disaster_id, keywords, check_fn in patterns:
            if any(kw in code_lower for kw in keywords):
                try:
                    if check_fn(code_lower):
                        template = next((d for d in cls.CODE_DISASTER_TEMPLATES if d["id"] == disaster_id), None)
                        if template:
                            risks.append({
                                "disaster_id": template["id"],
                                "name": template["name"],
                                "trigger": template["trigger"],
                                "consequence": template["consequence"],
                                "level": template["level"],
                                "detection": template["detection"],
                                "matched_in": skill_meta.get("name", "unknown"),
                            })
                except Exception:
                    pass
        
        return risks
    
    @classmethod
    def generate_failure_modes(cls, skill_name: str, description: str) -> List[dict]:
        """基于SKILL描述生成潜在失败模式列表 (用于GLM-5推演prompt)"""
        modes = []
        desc_lower = description.lower()
        
        keyword_disaster_map = {
            "并发": ["CD02"], "多线程": ["CD02"], "concurrent": ["CD02"],
            "数据库": ["CD07", "CD11"], "sql": ["CD07", "CD11"],
            "api": ["CD08", "CD09"], "http": ["CD08"],
            "缓存": ["CD03"], "cache": ["CD03"],
            "计算": ["CD10", "CD12"], "算法": ["CD10"],
            "文件": ["CD01", "CD11"], "读写": ["CD01", "CD11"],
        }
        
        for keyword, disaster_ids in keyword_disaster_map.items():
            if keyword in desc_lower:
                for did in disaster_ids:
                    template = next((d for d in cls.CODE_DISASTER_TEMPLATES if d["id"] == did), None)
                    if template and template not in modes:
                        modes.append(template)
        
        return modes


# ==================== 模式4: 6阶段管线门控 ====================
# DiePre原理: Stage1输入解析→Stage2上下文加载→Stage3推演→Stage4输出→Stage5验证→Stage6记录
# 每个Stage有入口条件和出口质量门, 不达标则阻断

class PipelineStageGate:
    """6阶段管线门控系统
    
    DiePre原理 (DiePre_AI_Skill.md §三):
      Stage 1: 输入解析 → 结构化元素(点/线/角/面)
      Stage 2: 材料+工序链加载 → 固定规则+可变参数
      Stage 3: 2D→3D推演 → 几何+补偿+误差+风险
      Stage 4: 输出与可视化映射
      Stage 5: 用户验证 → 修正/诊断
      Stage 6: 成长记录 → 参数校准
    
    AGI映射:
      Stage 1: 问题分解 → 结构化子问题 (top_down)
      Stage 2: 知识加载 → proven_nodes + skills (context)
      Stage 3: 多Phase推演 → 碰撞/证伪/生成 (inference)
      Stage 4: SKILL输出 + 可视化 (output)
      Stage 5: 执行验证 → 错误归因 (validation)
      Stage 6: 成长记录 → 收敛分析 (recording)
    """
    
    STAGES = [
        {"id": 1, "name": "decompose",   "display": "问题分解",     "gate_metric": "sub_questions_count", "gate_min": 1},
        {"id": 2, "name": "context",     "display": "知识加载",     "gate_metric": "context_nodes_count", "gate_min": 0},
        {"id": 3, "name": "inference",   "display": "多Phase推演",  "gate_metric": "raw_nodes_count",     "gate_min": 1},
        {"id": 4, "name": "output",      "display": "SKILL生成",    "gate_metric": "skills_generated",    "gate_min": 0},
        {"id": 5, "name": "validation",  "display": "验证校验",     "gate_metric": "validation_rate",     "gate_min": 0.3},
        {"id": 6, "name": "recording",   "display": "成长记录",     "gate_metric": "recorded",            "gate_min": 1},
    ]
    
    def __init__(self):
        self.stage_results: Dict[int, dict] = {}
        self.blocked_at: Optional[int] = None
    
    def check_gate(self, stage_id: int, metrics: dict) -> Tuple[bool, str]:
        """检查阶段门控是否通过
        返回: (通过, 原因)"""
        stage = next((s for s in self.STAGES if s["id"] == stage_id), None)
        if not stage:
            return True, "unknown_stage"
        
        metric_key = stage["gate_metric"]
        metric_value = metrics.get(metric_key, 0)
        gate_min = stage["gate_min"]
        
        passed = metric_value >= gate_min
        self.stage_results[stage_id] = {
            "stage": stage["name"], "display": stage["display"],
            "metric": metric_key, "value": metric_value,
            "threshold": gate_min, "passed": passed,
            "timestamp": datetime.now().isoformat()
        }
        
        if not passed:
            self.blocked_at = stage_id
            return False, f"{stage['display']}门控未通过: {metric_key}={metric_value} < {gate_min}"
        
        return True, "passed"
    
    def pipeline_report(self) -> dict:
        """生成管线执行报告"""
        return {
            "stages": self.stage_results,
            "blocked_at": self.blocked_at,
            "completed": self.blocked_at is None and len(self.stage_results) == len(self.STAGES),
            "pass_rate": sum(1 for s in self.stage_results.values() if s.get("passed")) / max(len(self.stage_results), 1),
        }


# ==================== 模式5: RSS置信度合成 ====================
# DiePre核心: e_total = √(Σeᵢ²) — 多源误差的RSS堆叠
# AGI映射: 多源置信度合成, 多Phase结果的综合质量评估

class RSSConfidenceComposer:
    """RSS置信度合成器
    
    DiePre原理 (Claude_需求理解.md §三):
      e_total = √(e_MC² + e_batch² + e_die² + e_machine² + e_aging²)
      各源贡献排序, 最大源优先改善
    
    AGI映射:
      - 多个Phase产生的节点, 每个Phase有不同的可靠度
      - 最终节点置信度 = RSS合成(各Phase置信度 × 权重)
      - 贡献最大的Phase = 最需要强化的方向
    """
    
    # Phase权重 (来自DiePre的误差源权重概念)
    PHASE_WEIGHTS = {
        "top_down": 0.8,        # 自上而下: 方向对但可能过于抽象
        "bottom_up": 0.9,       # 自下而上: 基于已有节点, 较可靠
        "horizontal": 0.7,      # 左右碰撞: 创新性高但风险也高
        "deep_reasoning": 0.85, # 深度推演: GLM-5主力, 质量较高
        "code_domain": 0.95,    # 代码维度: 可执行验证, 最高可靠度
        "falsify": 1.0,         # 证伪: 通过证伪的最可靠
    }
    
    @classmethod
    def compose(cls, confidences: List[Tuple[str, float]]) -> float:
        """RSS合成多源置信度
        confidences: [(phase_name, confidence_value), ...]
        返回: 合成后的总置信度 [0, 1]"""
        if not confidences:
            return 0.0
        
        weighted_sum_sq = 0.0
        total_weight = 0.0
        
        for phase, conf in confidences:
            weight = cls.PHASE_WEIGHTS.get(phase, 0.75)
            weighted_sum_sq += (conf * weight) ** 2
            total_weight += weight ** 2
        
        if total_weight == 0:
            return 0.0
        
        # RSS合成: 类似误差传播
        rss = math.sqrt(weighted_sum_sq / total_weight)
        return min(rss, 1.0)
    
    @classmethod
    def contribution_analysis(cls, confidences: List[Tuple[str, float]]) -> List[dict]:
        """贡献度分析: 哪个Phase对最终置信度贡献最大
        DiePre原理: 敏感度排序, 贡献最大源优先改善"""
        if not confidences:
            return []
        
        total = cls.compose(confidences)
        contributions = []
        for phase, conf in confidences:
            weight = cls.PHASE_WEIGHTS.get(phase, 0.75)
            contribution = (conf * weight) ** 2
            contributions.append({
                "phase": phase, "confidence": conf, "weight": weight,
                "contribution_pct": round(contribution / max(sum((c * cls.PHASE_WEIGHTS.get(p, 0.75)) ** 2 
                                                                  for p, c in confidences), 0.001) * 100, 1)
            })
        
        contributions.sort(key=lambda x: x["contribution_pct"], reverse=True)
        return contributions


# ==================== 模式6: 成长会话记录器 ====================
# DiePre原理: 每次验证后自动记录, 每10次生成成长报告
# 固定规则只增不减, 可变参数持续收敛, 新发现经历3阶段确认

class GrowthSessionRecorder:
    """成长会话记录器
    
    DiePre原理 (DiePre_AI_Skill.md §三 Stage 6):
      每次验证后自动记录:
        - session_id, input_type, material_combo
        - ai_output, user_corrections
        - new_discoveries, fixed_rules_reinforced, variable_params_updated
      
      每10次验证自动生成成长报告:
        - 收敛参数: 哪些已趋于稳定
        - 波动参数: 哪些还在持续被修正
        - 新增知识: 本轮发现的新规则/新灾难
        - 推荐动作: 是否需要更多实测数据
    
    灾难知识进化 (§5.3):
      1次发现 → 疑似灾难
      2次复现 → 确认灾难 → 入库
      5次数据 → 完全量化触发条件和后果
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.sessions: List[dict] = []
        self.convergence_tracker = ConvergenceTracker()
        self.discovery_counts: Dict[str, int] = {}  # discovery_key → occurrence count
        self._init_tables()
    
    def _init_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS growth_sessions(
                id TEXT PRIMARY KEY,
                round_number INTEGER,
                mode TEXT,
                fixed_nodes_count INTEGER DEFAULT 0,
                variable_nodes_count INTEGER DEFAULT 0,
                skills_generated INTEGER DEFAULT 0,
                skills_validated INTEGER DEFAULT 0,
                risks_scanned INTEGER DEFAULT 0,
                risks_found INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                elapsed_seconds REAL DEFAULT 0,
                pipeline_report TEXT,
                convergence_snapshot TEXT,
                discoveries TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS disaster_knowledge(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trigger_condition TEXT,
                consequence TEXT,
                risk_level TEXT,
                detection_method TEXT,
                occurrence_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'suspected',
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            );
            CREATE TABLE IF NOT EXISTS convergence_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                sigma REAL,
                status TEXT,
                value_count INTEGER,
                latest_value REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
    
    def record_session(self, round_num: int, mode: str, results: dict,
                       pipeline: PipelineStageGate, classified_nodes: dict,
                       risks: List[dict], discoveries: List[dict] = None):
        """记录一轮成长会话"""
        session_id = f"gs_{round_num}_{int(time.time()*1000)%99999}"
        
        # 记录各域置信度到收敛追踪器
        for track_name, nodes in classified_nodes.items():
            for nd in nodes:
                domain = nd.get("domain", "general")
                self.convergence_tracker.record(
                    f"{domain}.{track_name}", 
                    nd.get("confidence", 0.5)
                )
        
        # 记录灾难发现
        for risk in risks:
            key = risk.get("disaster_id", risk.get("name", "unknown"))
            self._record_disaster(key, risk)
        
        session = {
            "id": session_id,
            "round_number": round_num,
            "mode": mode,
            "fixed_nodes_count": len(classified_nodes.get("fixed_rule", [])),
            "variable_nodes_count": len(classified_nodes.get("variable_param", [])),
            "skills_generated": results.get("skills_gen", 0),
            "skills_validated": results.get("skills_valid", 0),
            "risks_scanned": len(risks),
            "risks_found": sum(1 for r in risks if r.get("level", "").startswith("🔴")),
            "tokens_used": results.get("tokens_used", 0),
            "elapsed_seconds": results.get("elapsed_seconds", 0),
            "pipeline_report": json.dumps(pipeline.pipeline_report(), ensure_ascii=False),
            "convergence_snapshot": json.dumps(self.convergence_tracker.convergence_report(), ensure_ascii=False),
            "discoveries": json.dumps(discoveries or [], ensure_ascii=False),
        }
        self.sessions.append(session)
        self._save_session(session)
        
        return session_id
    
    def _record_disaster(self, key: str, risk: dict):
        """记录灾难发现, 遵循DiePre灾难知识进化规则"""
        self.discovery_counts[key] = self.discovery_counts.get(key, 0) + 1
        count = self.discovery_counts[key]
        
        if count == 1:
            status = "suspected"
        elif count >= 5:
            status = "fully_quantified"
        elif count >= 2:
            status = "confirmed"
        else:
            status = "suspected"
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO disaster_knowledge(id, name, trigger_condition, consequence, 
                    risk_level, detection_method, occurrence_count, status)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    occurrence_count = occurrence_count + 1,
                    status = ?,
                    last_seen = CURRENT_TIMESTAMP
            """, (key, risk.get("name", key), risk.get("trigger", ""),
                  risk.get("consequence", ""), risk.get("level", "🟠"),
                  risk.get("detection", ""), count, status, status))
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def _save_session(self, session: dict):
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT OR REPLACE INTO growth_sessions(
                    id, round_number, mode, fixed_nodes_count, variable_nodes_count,
                    skills_generated, skills_validated, risks_scanned, risks_found,
                    tokens_used, elapsed_seconds, pipeline_report, convergence_snapshot, discoveries)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (session["id"], session["round_number"], session["mode"],
                  session["fixed_nodes_count"], session["variable_nodes_count"],
                  session["skills_generated"], session["skills_validated"],
                  session["risks_scanned"], session["risks_found"],
                  session["tokens_used"], session["elapsed_seconds"],
                  session["pipeline_report"], session["convergence_snapshot"],
                  session["discoveries"]))
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def growth_report(self) -> str:
        """生成成长报告 (DiePre §5: 每10次验证自动生成)"""
        conv = self.convergence_tracker.convergence_report()
        
        report = f"""# AGI 自成长报告 (DiePre框架增强版)
生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总会话: {len(self.sessions)}

## 收敛分析 (DiePre §5.1 参数收敛机制)
- 已收敛域: {conv['summary']['converged_count']} ({conv['summary']['convergence_rate']*100:.0f}%)
- 收敛中: {conv['summary']['converging_count']}
- 高波动: {conv['summary']['volatile_count']}

### 已收敛参数 (σ < {ConvergenceTracker.CONVERGED_SIGMA})
"""
        for item in conv.get("converged", []):
            report += f"  - {item['key']}: σ={item['sigma']:.4f}, mean={item['mean']:.3f}, N={item['count']}\n"
        
        report += f"\n### 高波动参数 (σ > {ConvergenceTracker.HIGH_VOLATILITY_SIGMA}) — 需更多数据\n"
        for item in conv.get("high_volatility", []):
            report += f"  - {item['key']}: σ={item['sigma']:.4f}, N={item['count']} ⚠️\n"
        
        report += f"\n## 灾难知识进化 (DiePre §5.3)\n"
        for key, count in sorted(self.discovery_counts.items(), key=lambda x: -x[1]):
            status = "疑似" if count == 1 else "确认" if count < 5 else "完全量化"
            report += f"  - {key}: {count}次 → {status}\n"
        
        return report


# ==================== 模式7: 节点真实性分级器 ====================
# 核心理念: 得到社会广泛认可和实际应用的就是真实节点
# 5级体系: L1本体真实 → L2关系真实 → L3能力真实 → L4共识真实 → L5进化真实

class NodeTruthClassifier:
    """节点真实性5级分类器
    
    真实性分级:
      L1 本体真实 (Intrinsic): 标准/定律/规范/广泛应用算法/机器参数/材料常数/开源API
      L2 关系真实 (Relational): 链式依赖验证/跨域碰撞/标准映射/模式实例化/组件组合/因果链/层级继承
      L3 能力真实 (Capability): 代码可执行/链式调用/工程部署/性能达标/人类反馈/竞赛通过/解决问题
      L4 共识真实 (Consensus): 开源广泛使用/行业最佳实践/学术引用/专利认证/教育收录/多平台验证
      L5 进化真实 (Evolutionary): 收敛稳定/证伪幸存/版本迭代/灾难完全量化/跨代验证
    
    所有节点都应存入数据库, 包括假设和已证伪节点
    节点真实性是动态的, 可升可降
    """
    
    # L1 本体真实关键词 (匹配即可判定)
    L1_KEYWORDS = {
        "standard": ["ISO", "ECMA", "FEFCO", "GB/T", "JIS", "DIN", "IEEE", "RFC", "PEP", "W3C",
                      "ANSI", "ASTM", "OSHA", "NIST"],
        "law": ["定律", "定理", "公理", "公式", "方程", "law", "theorem", "axiom"],
        "spec": ["规范", "specification", "标准", "standard", "protocol"],
        "algorithm": ["Dijkstra", "quicksort", "mergesort", "RSA", "AES", "SHA", "FFT",
                       "PageRank", "backpropagation", "gradient descent"],
        "api": ["React", "Vue", "Angular", "Spring Boot", "Django", "Flask", "Express",
                "PyTorch", "TensorFlow", "Kubernetes", "Docker"],
    }
    
    # L4 共识真实指标阈值
    L4_THRESHOLDS = {
        "npm_weekly_downloads": 1_000_000,
        "github_stars": 10_000,
        "paper_citations": 1000,
        "independent_implementations": 3,
    }
    
    TRUTH_LEVELS = {
        0: {"name": "hypothesis", "label": "假设", "color": "⬜"},
        1: {"name": "intrinsic", "label": "本体真实", "color": "🟦"},
        2: {"name": "relational", "label": "关系真实", "color": "🟩"},
        3: {"name": "capability", "label": "能力真实", "color": "🟨"},
        4: {"name": "consensus", "label": "共识真实", "color": "🟧"},
        5: {"name": "evolutionary", "label": "进化真实", "color": "🟥"},
        -1: {"name": "deprecated", "label": "已证伪", "color": "⬛"},
    }
    
    @classmethod
    def classify(cls, node: dict, context: dict = None) -> dict:
        """对节点进行真实性分级
        
        Args:
            node: 节点字典, 需包含 content, type, confidence, domain 等
            context: 上下文信息, 可包含:
                - chain_links: 该节点的链式依赖列表
                - cross_domain_count: 跨域验证次数
                - test_passed: 是否通过测试
                - deploy_verified: 是否部署验证
                - usage_count: 使用/引用次数
                - falsify_survived: 证伪幸存次数
                - convergence_sigma: 收敛σ值
                - version_count: 版本迭代次数
        
        Returns:
            {"truth_level": int, "truth_name": str, "truth_source": str, "reasons": [str]}
        """
        ctx = context or {}
        content = node.get("content", "")
        confidence = node.get("confidence", 0.0)
        node_type = node.get("type", "hypothesis")
        verify_count = node.get("verify_count", 0)
        
        # 已证伪检查
        if node_type == "deprecated" or confidence < 0.1:
            return cls._result(-1, "falsified", ["节点已被证伪或置信度极低"])
        
        reasons = []
        level = 0
        source = "unclassified"
        
        # === L1: 本体真实检查 ===
        l1_score = cls._check_intrinsic(content, node)
        if l1_score > 0:
            level = max(level, 1)
            source = f"intrinsic_{l1_score}"
            reasons.append(f"L1本体真实: 匹配{l1_score}个标准/定律/规范关键词")
        
        # === L2: 关系真实检查 ===
        chain_links = ctx.get("chain_links", [])
        cross_domain = ctx.get("cross_domain_count", 0)
        parent_truth = ctx.get("parent_truth_level", 0)
        
        if chain_links and all(l.get("truth_level", 0) >= 1 for l in chain_links):
            level = max(level, 2)
            source = "chain_dependency"
            reasons.append(f"L2关系真实: {len(chain_links)}个依赖节点均为真实")
        
        if cross_domain >= 2:
            level = max(level, 2)
            source = "cross_domain_overlap"
            reasons.append(f"L2关系真实: {cross_domain}个独立领域交叉验证")
        
        if parent_truth >= 1 and node.get("collision_type") == "top_down":
            level = max(level, 2)
            source = "hierarchy_inheritance"
            reasons.append(f"L2关系真实: 从L{parent_truth}父节点推导")
        
        if node.get("collision_type") == "horizontal" and confidence >= 0.7:
            level = max(level, 2)
            source = "pattern_instantiation"
            reasons.append("L2关系真实: 跨域碰撞模式实例化")
        
        # === L3: 能力真实检查 ===
        if ctx.get("test_passed"):
            level = max(level, 3)
            source = "code_executable"
            reasons.append("L3能力真实: 代码测试通过")
        
        if ctx.get("chain_call_verified"):
            level = max(level, 3)
            source = "chain_call"
            reasons.append("L3能力真实: 链式调用端到端验证通过")
        
        if ctx.get("deploy_verified"):
            level = max(level, 3)
            source = "deployment"
            reasons.append("L3能力真实: 工程部署验证通过")
        
        if ctx.get("benchmark_passed"):
            level = max(level, 3)
            source = "performance"
            reasons.append("L3能力真实: 性能基准达标")
        
        if ctx.get("human_verified"):
            level = max(level, 3)
            source = "human_practice"
            reasons.append("L3能力真实: 人类实践反馈验证")
        
        if ctx.get("competition_passed"):
            level = max(level, 3)
            source = "competition"
            reasons.append("L3能力真实: 竞赛/评测通过")
        
        if ctx.get("problem_solved"):
            level = max(level, 3)
            source = "problem_solved"
            reasons.append("L3能力真实: 实际解决了具体问题")
        
        # === L4: 共识真实检查 ===
        usage = ctx.get("usage_count", 0)
        if usage >= cls.L4_THRESHOLDS.get("github_stars", 10000):
            level = max(level, 4)
            source = "widespread_use"
            reasons.append(f"L4共识真实: 使用量{usage}达到广泛使用阈值")
        
        if ctx.get("in_textbook"):
            level = max(level, 4)
            source = "education"
            reasons.append("L4共识真实: 被教育体系收录")
        
        if ctx.get("multi_platform_count", 0) >= 3:
            level = max(level, 4)
            source = "multi_platform"
            reasons.append(f"L4共识真实: {ctx['multi_platform_count']}个独立平台验证")
        
        # === L5: 进化真实检查 ===
        sigma = ctx.get("convergence_sigma", 1.0)
        falsify_count = ctx.get("falsify_survived", 0)
        version_count = ctx.get("version_count", 0)
        
        if sigma < 0.01 and verify_count >= 10:
            level = max(level, 5)
            source = "convergence_stable"
            reasons.append(f"L5进化真实: σ={sigma:.4f}<0.01, 验证{verify_count}次")
        
        if falsify_count >= 5:
            level = max(level, 5)
            source = "falsify_survived"
            reasons.append(f"L5进化真实: 经{falsify_count}轮证伪仍成立")
        
        if version_count >= 3 and confidence >= 0.9:
            level = max(level, 5)
            source = "version_iterated"
            reasons.append(f"L5进化真实: v{version_count}迭代核心保留")
        
        # 如果没有任何真实性证据但置信度较高,至少保持hypothesis
        if level == 0 and confidence >= 0.6:
            reasons.append(f"暂为假设: 置信度{confidence:.2f}但缺少真实性证据")
        
        return cls._result(level, source, reasons)
    
    @classmethod
    def _check_intrinsic(cls, content: str, node: dict) -> int:
        """检查L1本体真实性: 匹配标准/定律/规范关键词"""
        score = 0
        content_upper = content.upper()
        for category, keywords in cls.L1_KEYWORDS.items():
            for kw in keywords:
                if kw.upper() in content_upper:
                    score += 1
        # 领域特化检查
        domain = node.get("domain", "")
        if domain in ("mathematics", "physics", "chemistry"):
            if any(k in content for k in ["证明", "推导", "公式", "proof", "derive"]):
                score += 1
        return score
    
    @classmethod
    def _result(cls, level: int, source: str, reasons: list) -> dict:
        info = cls.TRUTH_LEVELS.get(level, cls.TRUTH_LEVELS[0])
        return {
            "truth_level": level,
            "truth_name": info["name"],
            "truth_label": info["label"],
            "truth_color": info["color"],
            "truth_source": source,
            "reasons": reasons,
        }
    
    @classmethod
    def batch_classify(cls, nodes: list, contexts: dict = None) -> dict:
        """批量分类并按级别分组
        Args:
            nodes: 节点列表
            contexts: {node_id: context_dict} 映射
        Returns:
            {"L0": [...], "L1": [...], ..., "L5": [...], "deprecated": [...], "stats": {...}}
        """
        ctxs = contexts or {}
        result = {f"L{i}": [] for i in range(6)}
        result["deprecated"] = []
        
        for nd in nodes:
            ctx = ctxs.get(nd.get("id", ""), {})
            classification = cls.classify(nd, ctx)
            nd["truth_level"] = classification["truth_level"]
            nd["truth_name"] = classification["truth_name"]
            nd["truth_source"] = classification["truth_source"]
            nd["truth_reasons"] = classification["reasons"]
            
            lvl = classification["truth_level"]
            if lvl == -1:
                result["deprecated"].append(nd)
            else:
                result[f"L{lvl}"].append(nd)
        
        result["stats"] = {
            "total": len(nodes),
            **{f"L{i}": len(result[f"L{i}"]) for i in range(6)},
            "deprecated": len(result["deprecated"]),
            "avg_level": sum(nd.get("truth_level", 0) for nd in nodes) / max(len(nodes), 1),
        }
        return result


# ==================== 模式8: 链式调用追踪器 ====================
# 核心理念: 一个组件的形成就是代码功能的链式调用
# 节点在对应的链式调用中形成真实的能力

class ChainLinkTracker:
    """链式调用追踪器
    
    记录节点间的链式调用关系, 用于:
    1. 判定L2关系真实: 链中所有前置节点均为真实
    2. 判定L3能力真实: 链式调用端到端测试通过
    3. 组件发现: 从调用链中自动识别可复用组件
    4. 关系网络构建: 形成节点间的有向图
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS node_chains(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id TEXT NOT NULL,
                chain_name TEXT,
                from_node_id TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                call_type TEXT DEFAULT 'function_call',
                call_order INTEGER DEFAULT 0,
                verified BOOLEAN DEFAULT 0,
                truth_level_from INTEGER DEFAULT 0,
                truth_level_to INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_chain_from ON node_chains(from_node_id);
            CREATE INDEX IF NOT EXISTS idx_chain_to ON node_chains(to_node_id);
            CREATE INDEX IF NOT EXISTS idx_chain_id ON node_chains(chain_id);
        """)
        # Safely add columns to proven_nodes if they don't exist
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(proven_nodes)")
            existing_cols = {row[1] for row in c.fetchall()}
            new_cols = [
                ("truth_level", "INTEGER DEFAULT 0"),
                ("truth_source", "TEXT DEFAULT 'unclassified'"),
                ("truth_reasons", "TEXT DEFAULT '[]'"),
                ("verify_count", "INTEGER DEFAULT 0"),
                ("falsify_survived", "INTEGER DEFAULT 0"),
                ("chain_count", "INTEGER DEFAULT 0"),
                ("version_num", "INTEGER DEFAULT 1"),
            ]
            for col_name, col_def in new_cols:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE proven_nodes ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass
        conn.commit()
        conn.close()
    
    def add_chain(self, chain_id: str, chain_name: str, links: List[dict]):
        """添加一条链式调用关系
        links: [{"from": node_id, "to": node_id, "call_type": "function_call", "order": 0}]
        """
        conn = sqlite3.connect(str(self.db_path))
        for link in links:
            conn.execute(
                "INSERT INTO node_chains(chain_id, chain_name, from_node_id, to_node_id, call_type, call_order) VALUES(?,?,?,?,?,?)",
                (chain_id, chain_name, link["from"], link["to"],
                 link.get("call_type", "function_call"), link.get("order", 0)))
        conn.commit()
        conn.close()
    
    def verify_chain(self, chain_id: str, verified: bool = True):
        """标记链式调用已验证(端到端测试通过)"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE node_chains SET verified=? WHERE chain_id=?", (verified, chain_id))
        conn.commit()
        conn.close()
    
    def get_node_chains(self, node_id: str) -> List[dict]:
        """获取节点参与的所有链式调用"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            SELECT chain_id, chain_name, from_node_id, to_node_id, call_type, call_order, verified
            FROM node_chains WHERE from_node_id=? OR to_node_id=?
            ORDER BY chain_id, call_order
        """, (node_id, node_id))
        chains = [{"chain_id": r[0], "chain_name": r[1], "from": r[2], "to": r[3],
                    "call_type": r[4], "order": r[5], "verified": bool(r[6])} for r in c.fetchall()]
        conn.close()
        return chains
    
    def get_chain_context(self, node_id: str) -> dict:
        """获取节点的链式调用上下文(用于真实性分类)"""
        chains = self.get_node_chains(node_id)
        if not chains:
            return {"chain_links": [], "chain_call_verified": False}
        
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        related_ids = set()
        for ch in chains:
            related_ids.add(ch["from"])
            related_ids.add(ch["to"])
        related_ids.discard(node_id)
        
        chain_links = []
        for rid in related_ids:
            c.execute("SELECT id, truth_level, confidence FROM proven_nodes WHERE id=?", (rid,))
            row = c.fetchone()
            if row:
                chain_links.append({"id": row[0], "truth_level": row[1] or 0, "confidence": row[2] or 0})
        conn.close()
        
        any_verified = any(ch.get("verified") for ch in chains)
        return {"chain_links": chain_links, "chain_call_verified": any_verified}
    
    def discover_components(self, min_chain_length: int = 3) -> List[dict]:
        """从链式调用中自动发现可复用组件
        组件 = 在多条链中出现的节点子图"""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            SELECT from_node_id, COUNT(DISTINCT chain_id) as chain_count
            FROM node_chains GROUP BY from_node_id HAVING chain_count >= 2
            ORDER BY chain_count DESC
        """)
        hubs = [{"node_id": r[0], "chain_count": r[1]} for r in c.fetchall()]
        
        components = []
        for hub in hubs[:20]:
            c.execute("SELECT DISTINCT to_node_id FROM node_chains WHERE from_node_id=?",
                      (hub["node_id"],))
            downstream = [r[0] for r in c.fetchall()]
            
            if len(downstream) >= min_chain_length - 1:
                components.append({
                    "hub_node": hub["node_id"],
                    "chain_count": hub["chain_count"],
                    "downstream_nodes": downstream,
                    "component_size": len(downstream) + 1,
                })
        
        conn.close()
        return components


# ==================== 模式9: 算力智能调优器 ====================
# 核心: 根据节点真实性级别和Phase贡献度动态分配算力

class ComputeOptimizer:
    """算力智能调优器
    
    功能:
    1. 根据节点真实性级别分配token预算
    2. 根据RSS贡献度动态调整Phase权重
    3. 自适应并发度调整
    4. 高价值Phase优先执行
    5. 低质量节点跳过SKILL生成
    """
    
    # 各真实性级别的token预算倍率
    LEVEL_TOKEN_MULTIPLIER = {
        0: 0.5,   # hypothesis: 半量探索
        1: 0.8,   # L1 intrinsic: 验证性质疑
        2: 1.0,   # L2 relational: 标准推演
        3: 1.2,   # L3 capability: 代码生成需要更多token
        4: 0.6,   # L4 consensus: 已有共识,少量验证
        5: 0.3,   # L5 evolutionary: 极少维护性验证
        -1: 0.0,  # deprecated: 不分配
    }
    
    BASE_TOKENS = 8192
    
    def __init__(self):
        self._phase_weights = dict(RSSConfidenceComposer.PHASE_WEIGHTS)
        self._phase_history: Dict[str, List[float]] = {}
        self._concurrent_workers = 8
        self._lock = threading.Lock()
    
    def get_token_budget(self, truth_level: int) -> int:
        """根据节点真实性级别获取token预算"""
        mult = self.LEVEL_TOKEN_MULTIPLIER.get(truth_level, 1.0)
        return int(self.BASE_TOKENS * mult)
    
    def should_generate_skill(self, node: dict) -> bool:
        """判断是否值得为该节点生成SKILL
        低真实性+低置信度的节点不值得消耗算力生成代码"""
        truth_level = node.get("truth_level", 0)
        confidence = node.get("confidence", 0.5)
        
        if truth_level <= 0 and confidence < 0.6:
            return False
        if truth_level >= 3:
            return True
        if truth_level >= 1 and confidence >= 0.7:
            return True
        return confidence >= 0.75
    
    def update_phase_weights(self, contributions: List[dict]):
        """根据RSS贡献度分析更新Phase权重
        高贡献Phase权重上调, 低贡献Phase权重下调"""
        with self._lock:
            for contrib in contributions:
                phase = contrib["phase"]
                pct = contrib["contribution_pct"]
                
                if phase not in self._phase_history:
                    self._phase_history[phase] = []
                self._phase_history[phase].append(pct)
                
                if len(self._phase_history[phase]) > 10:
                    self._phase_history[phase] = self._phase_history[phase][-10:]
            
            sample_counts = [len(v) for v in self._phase_history.values()]
            if sample_counts and min(sample_counts) >= 5:
                for phase, pcts in self._phase_history.items():
                    avg_pct = sum(pcts) / len(pcts)
                    base = self._phase_weights.get(phase, 0.75)
                    adjusted = base * (0.7 + 0.6 * avg_pct / 100.0)
                    self._phase_weights[phase] = max(0.5, min(1.0, adjusted))
    
    def get_phase_weights(self) -> dict:
        with self._lock:
            return dict(self._phase_weights)
    
    def get_phase_frequency(self) -> dict:
        """获取各Phase建议执行频率"""
        weights = self.get_phase_weights()
        freq = {}
        for phase, weight in weights.items():
            if weight >= 0.9:
                freq[phase] = "every_round"
            elif weight >= 0.7:
                freq[phase] = "every_2_rounds"
            else:
                freq[phase] = "every_3_rounds"
        return freq
    
    def adjust_concurrency(self, avg_latency: float, error_rate: float):
        """根据API延迟和错误率调整并发度"""
        with self._lock:
            if error_rate > 0.2:
                self._concurrent_workers = max(2, self._concurrent_workers - 2)
            elif error_rate > 0.1:
                self._concurrent_workers = max(2, self._concurrent_workers - 1)
            elif avg_latency < 3.0 and error_rate < 0.05:
                self._concurrent_workers = min(16, self._concurrent_workers + 1)
    
    def get_concurrency(self) -> int:
        with self._lock:
            return self._concurrent_workers
    
    def optimization_report(self) -> dict:
        weights = self.get_phase_weights()
        freq = self.get_phase_frequency()
        return {
            "concurrent_workers": self._concurrent_workers,
            "phase_weights": weights,
            "phase_frequency": freq,
            "token_budget_by_level": {
                f"L{k}" if k >= 0 else "deprecated": int(self.BASE_TOKENS * v)
                for k, v in self.LEVEL_TOKEN_MULTIPLIER.items()
            },
        }
