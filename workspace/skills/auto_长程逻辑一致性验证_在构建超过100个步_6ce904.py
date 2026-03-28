"""
长程逻辑一致性验证模块

该模块实现了AGI系统中的长程任务链条验证功能，用于检测超过100个步骤的
复杂任务执行过程中是否发生目标漂移。通过构建结构化认知网络作为全局导航图，
确保AI在执行长程任务时维持顶层目标的约束。

核心功能：
1. 构建结构化认知网络表示任务链条
2. 计算每个步骤与顶层目标的语义一致性
3. 检测并预警目标漂移现象
4. 生成一致性分析报告

数据格式：
输入: JSON格式的任务链条，包含步骤列表和目标描述
输出: 一致性验证报告，包含漂移检测结果和一致性得分

使用示例:
>>> validator = LongRangeConsistencyValidator()
>>> task_chain = load_task_chain("game_dev_steps.json")
>>> report = validator.validate(task_chain)
>>> print(report.summary)
"""

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LongRangeConsistencyValidator")


class DriftSeverity(Enum):
    """目标漂移严重程度枚举"""
    NONE = 0       # 无漂移
    MINOR = 1      # 轻微漂移
    MODERATE = 2   # 中度漂移
    SEVERE = 3     # 严重漂移
    CRITICAL = 4   # 关键漂移


@dataclass
class TaskStep:
    """任务步骤数据结构"""
    step_id: str
    description: str
    timestamp: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Union[str, int, float]] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not self.step_id or not isinstance(self.step_id, str):
            raise ValueError("step_id必须是非空字符串")
        if not self.description or not isinstance(self.description, str):
            raise ValueError("description必须是非空字符串")
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TaskChain:
    """任务链条数据结构"""
    chain_id: str
    top_level_goal: str
    steps: List[TaskStep]
    creation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """数据验证"""
        if len(self.steps) < 1:
            raise ValueError("任务链条必须包含至少一个步骤")
        if not self.top_level_goal:
            raise ValueError("必须定义顶层目标")


@dataclass
class ConsistencyReport:
    """一致性验证报告"""
    chain_id: str
    is_consistent: bool
    consistency_score: float
    drift_detected: bool
    drift_severity: DriftSeverity
    drift_steps: List[Tuple[str, float, str]]  # (step_id, drift_score, reason)
    step_scores: Dict[str, float]
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def summary(self) -> str:
        """生成报告摘要"""
        status = "一致" if self.is_consistent else "不一致"
        severity_str = self.drift_severity.name if self.drift_detected else "NONE"
        return (f"任务链 {self.chain_id} 验证结果: {status}\n"
                f"一致性得分: {self.consistency_score:.3f}\n"
                f"漂移检测: {'是' if self.drift_detected else '否'}\n"
                f"漂移严重程度: {severity_str}\n"
                f"问题步骤数: {len(self.drift_steps)}")


class CognitiveNode:
    """认知网络节点"""
    def __init__(self, node_id: str, content: str, node_type: str):
        self.node_id = node_id
        self.content = content
        self.node_type = node_type  # 'goal', 'step', 'context'
        self.connections: List[Tuple['CognitiveNode', float]] = []
    
    def add_connection(self, other: 'CognitiveNode', weight: float):
        """添加连接"""
        if weight < 0 or weight > 1:
            raise ValueError("连接权重必须在0-1之间")
        self.connections.append((other, weight))
    
    def get_activation_score(self, target_content: str) -> float:
        """计算激活得分（简化版语义相似度）"""
        # 简化的语义相似度计算（实际应用中应使用embedding模型）
        common_words = set(self.content.lower().split()) & set(target_content.lower().split())
        union_words = set(self.content.lower().split()) | set(target_content.lower().split())
        if not union_words:
            return 0.0
        return len(common_words) / len(union_words)


class StructuredCognitiveNetwork:
    """结构化认知网络"""
    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}
        self.goal_node: Optional[CognitiveNode] = None
    
    def build_from_task_chain(self, task_chain: TaskChain) -> None:
        """从任务链条构建认知网络"""
        # 创建目标节点
        self.goal_node = CognitiveNode(
            node_id="goal_0",
            content=task_chain.top_level_goal,
            node_type="goal"
        )
        self.nodes["goal_0"] = self.goal_node
        
        # 创建步骤节点并建立连接
        for i, step in enumerate(task_chain.steps):
            node = CognitiveNode(
                node_id=f"step_{i}",
                content=step.description,
                node_type="step"
            )
            
            # 与目标节点建立连接
            goal_similarity = node.get_activation_score(task_chain.top_level_goal)
            node.add_connection(self.goal_node, goal_similarity)
            
            # 处理依赖关系
            for dep_id in step.dependencies:
                if f"step_{dep_id}" in self.nodes:
                    dep_node = self.nodes[f"step_{dep_id}"]
                    dep_similarity = node.get_activation_score(dep_node.content)
                    node.add_connection(dep_node, dep_similarity)
            
            self.nodes[node.node_id] = node
        
        logger.info(f"认知网络构建完成，共{len(self.nodes)}个节点")
    
    def calculate_consistency(self) -> Dict[str, float]:
        """计算每个步骤与目标的一致性得分"""
        if not self.goal_node:
            raise ValueError("认知网络未初始化目标节点")
        
        scores = {}
        for node_id, node in self.nodes.items():
            if node.node_type == "step":
                # 计算与目标节点的直接连接权重
                goal_connection = next(
                    (w for n, w in node.connections if n.node_id == "goal_0"),
                    0.0
                )
                
                # 考虑通过中间节点的间接连接
                indirect_score = 0.0
                for connected_node, weight in node.connections:
                    if connected_node.node_type == "step":
                        indirect_goal_conn = next(
                            (w for n, w in connected_node.connections 
                             if n.node_id == "goal_0"),
                            0.0
                        )
                        indirect_score += weight * indirect_goal_conn * 0.5
                
                total_score = min(1.0, goal_connection + indirect_score)
                scores[node_id] = total_score
        
        return scores


def calculate_drift_severity(
    consistency_scores: Dict[str, float],
    threshold_minor: float = 0.7,
    threshold_moderate: float = 0.5,
    threshold_severe: float = 0.3,
    threshold_critical: float = 0.1
) -> Tuple[DriftSeverity, List[Tuple[str, float, str]]]:
    """
    辅助函数：计算漂移严重程度
    
    参数:
        consistency_scores: 步骤一致性得分字典
        threshold_minor: 轻微漂移阈值
        threshold_moderate: 中度漂移阈值
        threshold_severe: 严重漂移阈值
        threshold_critical: 关键漂移阈值
    
    返回:
        Tuple[漂移严重程度, 问题步骤列表]
    """
    drift_steps = []
    min_score = 1.0
    
    for step_id, score in consistency_scores.items():
        min_score = min(min_score, score)
        
        if score < threshold_critical:
            drift_steps.append((step_id, score, "关键漂移：严重偏离目标"))
        elif score < threshold_severe:
            drift_steps.append((step_id, score, "严重漂移：明显偏离目标"))
        elif score < threshold_moderate:
            drift_steps.append((step_id, score, "中度漂移：部分偏离目标"))
        elif score < threshold_minor:
            drift_steps.append((step_id, score, "轻微漂移：可能偏离目标"))
    
    # 确定整体严重程度
    if not drift_steps:
        severity = DriftSeverity.NONE
    elif min_score < threshold_critical:
        severity = DriftSeverity.CRITICAL
    elif min_score < threshold_severe:
        severity = DriftSeverity.SEVERE
    elif min_score < threshold_moderate:
        severity = DriftSeverity.MODERATE
    else:
        severity = DriftSeverity.MINOR
    
    return severity, drift_steps


class LongRangeConsistencyValidator:
    """长程逻辑一致性验证器"""
    
    def __init__(
        self,
        consistency_threshold: float = 0.6,
        window_size: int = 10,
        enable_detailed_logging: bool = True
    ):
        """
        初始化验证器
        
        参数:
            consistency_threshold: 一致性阈值
            window_size: 滑动窗口大小
            enable_detailed_logging: 是否启用详细日志
        """
        if consistency_threshold < 0 or consistency_threshold > 1:
            raise ValueError("一致性阈值必须在0-1之间")
        if window_size < 1:
            raise ValueError("窗口大小必须大于0")
        
        self.consistency_threshold = consistency_threshold
        self.window_size = window_size
        self.enable_detailed_logging = enable_detailed_logging
        self.cognitive_network = StructuredCognitiveNetwork()
        
        logger.info(f"验证器初始化完成，阈值={consistency_threshold}, 窗口={window_size}")
    
    def validate(self, task_chain: TaskChain) -> ConsistencyReport:
        """
        验证任务链条的逻辑一致性
        
        参数:
            task_chain: 待验证的任务链条
        
        返回:
            ConsistencyReport: 一致性验证报告
        """
        if not isinstance(task_chain, TaskChain):
            raise TypeError("输入必须是TaskChain类型")
        
        logger.info(f"开始验证任务链: {task_chain.chain_id}, 步骤数: {len(task_chain.steps)}")
        
        # 构建认知网络
        self.cognitive_network.build_from_task_chain(task_chain)
        
        # 计算一致性得分
        step_scores = self.cognitive_network.calculate_consistency()
        
        if not step_scores:
            raise ValueError("未能计算任何步骤的一致性得分")
        
        # 计算整体一致性得分
        overall_score = sum(step_scores.values()) / len(step_scores)
        
        # 检测漂移
        drift_severity, drift_steps = calculate_drift_severity(step_scores)
        
        # 使用滑动窗口检测局部漂移
        window_drifts = self._detect_local_drifts(step_scores, task_chain.steps)
        drift_steps.extend(window_drifts)
        
        # 生成报告
        is_consistent = (
            overall_score >= self.consistency_threshold 
            and drift_severity in [DriftSeverity.NONE, DriftSeverity.MINOR]
        )
        
        report = ConsistencyReport(
            chain_id=task_chain.chain_id,
            is_consistent=is_consistent,
            consistency_score=overall_score,
            drift_detected=len(drift_steps) > 0,
            drift_severity=drift_severity,
            drift_steps=drift_steps,
            step_scores=step_scores
        )
        
        if self.enable_detailed_logging:
            self._log_detailed_results(report)
        
        logger.info(f"验证完成，一致性得分: {overall_score:.3f}, 漂移: {drift_severity.name}")
        
        return report
    
    def _detect_local_drifts(
        self,
        step_scores: Dict[str, float],
        steps: List[TaskStep]
    ) -> List[Tuple[str, float, str]]:
        """
        使用滑动窗口检测局部漂移
        
        参数:
            step_scores: 步骤得分字典
            steps: 任务步骤列表
        
        返回:
            局部漂移列表
        """
        local_drifts = []
        
        if len(steps) < self.window_size:
            return local_drifts
        
        step_ids = [f"step_{i}" for i in range(len(steps))]
        scores = [step_scores.get(sid, 0.0) for sid in step_ids]
        
        for i in range(len(scores) - self.window_size + 1):
            window_scores = scores[i:i + self.window_size]
            window_avg = sum(window_scores) / len(window_scores)
            window_variance = sum(
                (s - window_avg) ** 2 for s in window_scores
            ) / len(window_scores)
            
            # 检测窗口内的突然下降
            if window_variance > 0.1:
                min_idx = i + window_scores.index(min(window_scores))
                step_id = step_ids[min_idx]
                local_drifts.append((
                    step_id,
                    scores[min_idx],
                    f"局部漂移：在窗口[{i}-{i+self.window_size-1}]内检测到不一致"
                ))
        
        return local_drifts
    
    def _log_detailed_results(self, report: ConsistencyReport) -> None:
        """记录详细结果"""
        logger.info("=" * 60)
        logger.info("详细验证报告:")
        logger.info(f"任务链ID: {report.chain_id}")
        logger.info(f"整体一致性: {report.consistency_score:.3f}")
        logger.info(f"漂移检测: {report.drift_severity.name}")
        
        if report.drift_steps:
            logger.info("问题步骤:")
            for step_id, score, reason in report.drift_steps:
                logger.info(f"  - {step_id}: 得分={score:.3f}, 原因={reason}")
        
        logger.info("步骤得分分布:")
        scores = list(report.step_scores.values())
        logger.info(f"  最小值: {min(scores):.3f}")
        logger.info(f"  最大值: {max(scores):.3f}")
        logger.info(f"  平均值: {sum(scores)/len(scores):.3f}")
        logger.info("=" * 60)
    
    def export_report(self, report: ConsistencyReport, filepath: str) -> None:
        """
        导出报告到JSON文件
        
        参数:
            report: 验证报告
            filepath: 输出文件路径
        """
        report_dict = {
            "chain_id": report.chain_id,
            "is_consistent": report.is_consistent,
            "consistency_score": report.consistency_score,
            "drift_detected": report.drift_detected,
            "drift_severity": report.drift_severity.name,
            "drift_steps": [
                {"step_id": sid, "score": sc, "reason": r}
                for sid, sc, r in report.drift_steps
            ],
            "step_scores": report.step_scores,
            "analysis_timestamp": report.analysis_timestamp
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"报告已导出到: {filepath}")


def create_sample_task_chain() -> TaskChain:
    """创建示例任务链条用于测试"""
    steps = []
    
    # 模拟游戏开发任务链
    game_dev_tasks = [
        ("定义游戏核心玩法机制", []),
        ("设计游戏角色和敌人属性", [0]),
        ("实现玩家移动控制系统", [0]),
        ("创建基础游戏场景", [0]),
        ("实现碰撞检测系统", [2, 3]),
        ("添加敌人AI行为", [1, 4]),
        ("设计游戏UI界面", [0]),
        ("实现计分系统", [1, 4]),
        ("添加音效和背景音乐", [3]),
        ("进行游戏平衡性测试", [1, 5, 7]),
        ("修复发现的bug", [4, 5, 7]),
        ("优化游戏性能", [4, 5]),
        ("添加游戏教程关卡", [2, 3, 6]),
        ("实现存档功能", [7]),
        ("添加多人游戏模式", [2, 4, 5]),  # 可能的漂移点
        ("设计游戏内购系统", [14]),  # 明显的漂移点
        ("添加社交分享功能", [14]),  # 明显的漂移点
        ("进行最终测试", [10, 11, 12, 13, 14, 15, 16]),
        ("准备发布材料", [6]),
        ("提交应用商店审核", [18])
    ]
    
    for i, (desc, deps) in enumerate(game_dev_tasks):
        steps.append(TaskStep(
            step_id=str(i),
            description=desc,
            timestamp=datetime.now().isoformat(),
            dependencies=[str(d) for d in deps]
        ))
    
    return TaskChain(
        chain_id="game_dev_001",
        top_level_goal="开发一个简单但完整的2D平台跳跃游戏",
        steps=steps
    )


if __name__ == "__main__":
    # 使用示例
    print("=" * 60)
    print("长程逻辑一致性验证示例")
    print("=" * 60)
    
    # 创建验证器
    validator = LongRangeConsistencyValidator(
        consistency_threshold=0.6,
        window_size=5,
        enable_detailed_logging=True
    )
    
    # 创建测试任务链
    task_chain = create_sample_task_chain()
    print(f"\n任务链: {task_chain.chain_id}")
    print(f"顶层目标: {task_chain.top_level_goal}")
    print(f"步骤数量: {len(task_chain.steps)}")
    
    # 执行验证
    report = validator.validate(task_chain)
    
    # 打印摘要
    print("\n" + report.summary)
    
    # 导出报告
    validator.export_report(report, "consistency_report.json")