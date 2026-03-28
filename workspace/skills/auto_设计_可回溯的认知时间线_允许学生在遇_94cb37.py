"""
可回溯的认知时间线系统

该模块实现了一个允许学生在解题过程中"存档"和"读档"的认知时间线系统。
当学生遇到困难时，可以回到之前的认知节点尝试不同的解题路径，
系统会记录所有"死亡"（错误）并生成错误路径图谱。

核心功能：
- 认知节点存档/读档
- 错误路径追踪与分析
- 认知状态回溯
- 失败原因智能分析

Example:
    >>> timeline = CognitiveTimeline(student_id="stu_123")
    >>> timeline.create_checkpoint("开始解题", {"understood": True})
    >>> timeline.update_state("尝试方法A", {"approach": "induction"})
    >>> if not verify_solution():
    ...     timeline.mark_failure("方法A验证失败", "逻辑跳跃")
    ...     timeline.restore_checkpoint("开始解题")
"""

import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveTimeline")


class FailureSeverity(Enum):
    """失败严重程度枚举"""
    MINOR = "minor"          # 小错误，不影响主要思路
    MODERATE = "moderate"    # 中等错误，需要调整方向
    CRITICAL = "critical"    # 严重错误，需要完全重置


@dataclass
class CognitiveNode:
    """
    认知节点数据结构
    
    Attributes:
        node_id: 节点唯一标识
        timestamp: 创建时间戳
        label: 节点标签/描述
        cognitive_state: 当前认知状态字典
        parent_id: 父节点ID（用于构建路径树）
        children: 子节点ID列表
        is_failure: 是否为失败节点
        failure_reason: 失败原因描述
        failure_category: 失败类别
    """
    node_id: str
    timestamp: str
    label: str
    cognitive_state: Dict[str, Any]
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    is_failure: bool = False
    failure_reason: Optional[str] = None
    failure_category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class FailureRecord:
    """
    失败记录数据结构
    
    Attributes:
        record_id: 记录唯一ID
        node_id: 关联的认知节点ID
        timestamp: 记录时间
        reason: 失败原因
        category: 失败类别
        severity: 严重程度
        context: 上下文信息
        attempted_path: 尝试的路径
    """
    record_id: str
    node_id: str
    timestamp: str
    reason: str
    category: str
    severity: FailureSeverity
    context: Dict[str, Any]
    attempted_path: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['severity'] = self.severity.value
        return result


class CognitiveTimeline:
    """
    可回溯的认知时间线系统
    
    该类管理学生的认知过程，允许创建检查点、记录失败、
    回溯到之前的认知状态，并生成错误分析报告。
    
    Attributes:
        student_id: 学生唯一标识
        nodes: 认知节点字典 {node_id: CognitiveNode}
        current_node_id: 当前所在节点ID
        root_node_id: 根节点ID
        failure_records: 失败记录列表
        path_history: 路径历史记录
        
    Input Format:
        - cognitive_state: Dict[str, Any] - 认知状态字典
        - label: str - 节点标签
        - failure_reason: str - 失败原因描述
        - failure_category: str - 失败类别
        
    Output Format:
        - 节点数据: Dict (通过 to_dict() 方法)
        - 错误图谱: Dict (通过 generate_error_graph() 方法)
        - 分析报告: Dict (通过 analyze_failures() 方法)
    """
    
    MAX_NODES = 1000  # 最大节点数限制
    MAX_FAILURE_RECORDS = 500  # 最大失败记录数
    
    def __init__(self, student_id: str, session_id: Optional[str] = None):
        """
        初始化认知时间线
        
        Args:
            student_id: 学生唯一标识
            session_id: 会话ID（可选，用于区分不同学习会话）
            
        Raises:
            ValueError: 如果student_id为空
        """
        if not student_id or not student_id.strip():
            raise ValueError("学生ID不能为空")
        
        self.student_id = student_id.strip()
        self.session_id = session_id or self._generate_id("session")
        self.nodes: Dict[str, CognitiveNode] = {}
        self.current_node_id: Optional[str] = None
        self.root_node_id: Optional[str] = None
        self.failure_records: List[FailureRecord] = []
        self.path_history: List[str] = []
        self._checkpoint_stack: List[str] = []  # 检查点栈
        
        # 创建根节点
        self._create_root_node()
        
        logger.info(f"认知时间线已初始化 - 学生: {self.student_id}, 会话: {self.session_id}")
    
    def _generate_id(self, prefix: str = "node") -> str:
        """
        生成唯一标识符
        
        Args:
            prefix: ID前缀
            
        Returns:
            格式为 prefix_uuid 的唯一标识符
        """
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    def _create_root_node(self) -> None:
        """创建根节点"""
        root_id = self._generate_id("root")
        root_node = CognitiveNode(
            node_id=root_id,
            timestamp=datetime.now().isoformat(),
            label="起点",
            cognitive_state={"initialized": True},
            parent_id=None,
            metadata={"type": "root"}
        )
        self.nodes[root_id] = root_node
        self.root_node_id = root_id
        self.current_node_id = root_id
        self.path_history.append(root_id)
        
        logger.debug(f"根节点已创建: {root_id}")
    
    def _validate_state(self, cognitive_state: Dict[str, Any]) -> bool:
        """
        验证认知状态数据
        
        Args:
            cognitive_state: 待验证的认知状态字典
            
        Returns:
            验证是否通过
            
        Raises:
            TypeError: 如果cognitive_state不是字典
        """
        if not isinstance(cognitive_state, dict):
            raise TypeError("认知状态必须是字典类型")
        
        # 检查键名是否合法
        for key in cognitive_state.keys():
            if not isinstance(key, str):
                raise ValueError("认知状态的键必须是字符串类型")
        
        return True
    
    def _check_node_limit(self) -> None:
        """
        检查节点数量限制
        
        Raises:
            MemoryError: 如果超过最大节点数限制
        """
        if len(self.nodes) >= self.MAX_NODES:
            logger.warning(f"已达到最大节点数限制: {self.MAX_NODES}")
            raise MemoryError(f"认知节点数量超过限制 ({self.MAX_NODES})")
    
    def create_checkpoint(
        self, 
        label: str, 
        cognitive_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建认知检查点（存档点）
        
        在当前认知状态下创建一个可以回溯的节点。
        学生可以在遇到困难时回到此节点。
        
        Args:
            label: 检查点标签/描述
            cognitive_state: 当前认知状态字典
            metadata: 额外的元数据（可选）
            
        Returns:
            新创建的节点ID
            
        Raises:
            ValueError: 如果label为空或状态验证失败
            MemoryError: 如果超过节点数量限制
            
        Example:
            >>> timeline.create_checkpoint(
            ...     "理解题意",
            ...     {"problem_understood": True, "key_info": ["已知条件A", "求证B"]}
            ... )
            'node_abc123'
        """
        # 数据验证
        if not label or not label.strip():
            raise ValueError("检查点标签不能为空")
        
        self._validate_state(cognitive_state)
        self._check_node_limit()
        
        label = label.strip()
        
        # 创建新节点
        node_id = self._generate_id("checkpoint")
        new_node = CognitiveNode(
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            label=label,
            cognitive_state=cognitive_state.copy(),
            parent_id=self.current_node_id,
            metadata=metadata or {}
        )
        
        # 更新父节点的子节点列表
        if self.current_node_id and self.current_node_id in self.nodes:
            self.nodes[self.current_node_id].children.append(node_id)
        
        # 添加到节点字典
        self.nodes[node_id] = new_node
        self.current_node_id = node_id
        self.path_history.append(node_id)
        self._checkpoint_stack.append(node_id)
        
        logger.info(f"检查点已创建: [{label}] - {node_id}")
        
        return node_id
    
    def update_state(
        self, 
        label: str, 
        cognitive_state: Dict[str, Any],
        merge: bool = True
    ) -> str:
        """
        更新认知状态（创建普通节点）
        
        创建一个新的认知节点，记录思维过程的变化。
        与检查点不同，普通节点不会自动加入检查点栈。
        
        Args:
            label: 状态更新描述
            cognitive_state: 新的认知状态
            merge: 是否与当前状态合并（默认True）
            
        Returns:
            新创建的节点ID
        """
        if not label or not label.strip():
            raise ValueError("状态标签不能为空")
        
        self._validate_state(cognitive_state)
        self._check_node_limit()
        
        # 合并状态
        final_state = cognitive_state.copy()
        if merge and self.current_node_id:
            current_state = self.nodes[self.current_node_id].cognitive_state
            final_state = {**current_state, **cognitive_state}
        
        # 创建节点
        node_id = self._generate_id("state")
        new_node = CognitiveNode(
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            label=label.strip(),
            cognitive_state=final_state,
            parent_id=self.current_node_id,
            metadata={"type": "state_update"}
        )
        
        if self.current_node_id and self.current_node_id in self.nodes:
            self.nodes[self.current_node_id].children.append(node_id)
        
        self.nodes[node_id] = new_node
        self.current_node_id = node_id
        self.path_history.append(node_id)
        
        logger.debug(f"状态已更新: [{label}] - {node_id}")
        
        return node_id
    
    def mark_failure(
        self,
        reason: str,
        category: str,
        severity: FailureSeverity = FailureSeverity.MODERATE,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        标记当前节点为失败状态并记录失败原因
        
        当学生解题失败时，调用此方法记录失败信息。
        这些记录将用于生成错误路径图谱。
        
        Args:
            reason: 失败原因描述
            category: 失败类别（如"计算错误"、"逻辑错误"、"概念误解"等）
            severity: 失败严重程度
            context: 额外的上下文信息
            
        Returns:
            失败记录ID
            
        Example:
            >>> timeline.mark_failure(
            ...     reason="忽略了边界条件",
            ...     category="逻辑错误",
            ...     severity=FailureSeverity.MODERATE
            ... )
        """
        if not reason or not category:
            raise ValueError("失败原因和类别不能为空")
        
        if len(self.failure_records) >= self.MAX_FAILURE_RECORDS:
            logger.warning("失败记录已达上限，将清理最旧的记录")
            self.failure_records = self.failure_records[-self.MAX_FAILURE_RECORDS//2:]
        
        # 标记当前节点为失败
        if self.current_node_id and self.current_node_id in self.nodes:
            current_node = self.nodes[self.current_node_id]
            current_node.is_failure = True
            current_node.failure_reason = reason
            current_node.failure_category = category
        
        # 创建失败记录
        record_id = self._generate_id("fail")
        failure_record = FailureRecord(
            record_id=record_id,
            node_id=self.current_node_id or "",
            timestamp=datetime.now().isoformat(),
            reason=reason,
            category=category,
            severity=severity,
            context=context or {},
            attempted_path=self.get_current_path()
        )
        
        self.failure_records.append(failure_record)
        
        logger.warning(f"失败已记录: [{category}] {reason} - {record_id}")
        
        return record_id
    
    def restore_checkpoint(self, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """
        恢复到指定检查点（读档）
        
        将认知状态回溯到之前的检查点，允许学生从该点
        重新开始尝试不同的解题路径。
        
        Args:
            checkpoint_id: 要恢复的检查点ID。如果为None，则恢复到上一个检查点
            
        Returns:
            恢复后的认知状态字典
            
        Raises:
            ValueError: 如果检查点不存在或无效
            
        Example:
            >>> # 恢复到上一个检查点
            >>> state = timeline.restore_checkpoint()
            >>> # 恢复到指定检查点
            >>> state = timeline.restore_checkpoint("node_abc123")
        """
        target_id = checkpoint_id
        
        # 如果没有指定，使用栈顶的检查点
        if target_id is None:
            if not self._checkpoint_stack:
                raise ValueError("没有可用的检查点")
            # 弹出当前节点，获取上一个检查点
            if self._checkpoint_stack[-1] == self.current_node_id:
                self._checkpoint_stack.pop()
            if not self._checkpoint_stack:
                target_id = self.root_node_id
            else:
                target_id = self._checkpoint_stack[-1]
        
        # 验证检查点存在
        if target_id not in self.nodes:
            raise ValueError(f"检查点不存在: {target_id}")
        
        # 执行恢复
        old_node_id = self.current_node_id
        self.current_node_id = target_id
        restored_node = self.nodes[target_id]
        
        # 记录恢复操作
        restore_record = {
            "action": "restore",
            "from_node": old_node_id,
            "to_node": target_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if "restore_history" not in restored_node.metadata:
            restored_node.metadata["restore_history"] = []
        restored_node.metadata["restore_history"].append(restore_record)
        
        logger.info(f"已恢复到检查点: [{restored_node.label}] - {target_id}")
        
        return restored_node.cognitive_state.copy()
    
    def get_current_path(self) -> List[str]:
        """
        获取从根节点到当前节点的路径
        
        Returns:
            节点ID列表，表示当前认知路径
        """
        if not self.current_node_id:
            return []
        
        path = []
        current_id = self.current_node_id
        
        while current_id:
            if current_id in self.nodes:
                path.append(current_id)
                current_id = self.nodes[current_id].parent_id
            else:
                break
        
        return list(reversed(path))
    
    def get_available_checkpoints(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的检查点列表
        
        Returns:
            检查点信息列表，每个元素包含id、label、timestamp等
        """
        checkpoints = []
        
        for node_id in self._checkpoint_stack:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                checkpoints.append({
                    "id": node.node_id,
                    "label": node.label,
                    "timestamp": node.timestamp,
                    "is_failure": node.is_failure,
                    "state_keys": list(node.cognitive_state.keys())
                })
        
        # 添加根节点
        if self.root_node_id:
            root_node = self.nodes[self.root_node_id]
            checkpoints.insert(0, {
                "id": root_node.node_id,
                "label": root_node.label,
                "timestamp": root_node.timestamp,
                "is_failure": False,
                "state_keys": ["initialized"]
            })
        
        return checkpoints
    
    def generate_error_graph(self) -> Dict[str, Any]:
        """
        生成错误路径图谱
        
        分析所有失败记录，生成可视化的错误路径图谱，
        帮助学生和教师理解错误模式和关联。
        
        Returns:
            错误图谱字典，包含:
            - nodes: 所有相关节点
            - edges: 节点间的边
            - failure_clusters: 按类别分组的失败
            - statistics: 统计信息
        """
        # 收集失败节点
        failure_nodes = []
        edges = []
        categories: Dict[str, List[Dict]] = {}
        
        for record in self.failure_records:
            if record.node_id in self.nodes:
                node = self.nodes[record.node_id]
                node_info = {
                    "id": record.record_id,
                    "node_id": record.node_id,
                    "label": node.label,
                    "reason": record.reason,
                    "category": record.category,
                    "severity": record.severity.value,
                    "timestamp": record.timestamp
                }
                failure_nodes.append(node_info)
                
                # 按类别分组
                if record.category not in categories:
                    categories[record.category] = []
                categories[record.category].append(node_info)
                
                # 添加路径边
                path = record.attempted_path
                for i in range(len(path) - 1):
                    edge = {"from": path[i], "to": path[i+1], "type": "path"}
                    if edge not in edges:
                        edges.append(edge)
        
        # 统计信息
        statistics = {
            "total_failures": len(self.failure_records),
            "unique_categories": len(categories),
            "category_distribution": {k: len(v) for k, v in categories.items()},
            "severity_distribution": self._get_severity_distribution()
        }
        
        return {
            "nodes": failure_nodes,
            "edges": edges,
            "failure_clusters": categories,
            "statistics": statistics,
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_severity_distribution(self) -> Dict[str, int]:
        """获取严重程度分布"""
        distribution = {"minor": 0, "moderate": 0, "critical": 0}
        for record in self.failure_records:
            distribution[record.severity.value] += 1
        return distribution
    
    def analyze_failures(self) -> Dict[str, Any]:
        """
        智能分析失败模式
        
        基于失败记录，分析学生的常见错误模式，
        提供针对性的改进建议。
        
        Returns:
            分析报告字典，包含:
            - common_patterns: 常见错误模式
            - suggestions: 改进建议
            - progress_timeline: 进度时间线
            - strengths: 表现较好的方面
        """
        if not self.failure_records:
            return {
                "status": "no_failures",
                "message": "目前没有失败记录，继续保持！"
            }
        
        # 分析常见类别
        category_counts: Dict[str, int] = {}
        for record in self.failure_records:
            category_counts[record.category] = category_counts.get(record.category, 0) + 1
        
        # 找出最常见的错误类别
        sorted_categories = sorted(
            category_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 生成建议
        suggestions = self._generate_suggestions(sorted_categories)
        
        # 分析进度
        total_nodes = len(self.nodes)
        failure_rate = len(self.failure_records) / max(total_nodes, 1)
        
        # 计算探索效率
        checkpoints_used = len(self._checkpoint_stack)
        restore_count = sum(
            len(node.metadata.get("restore_history", []))
            for node in self.nodes.values()
        )
        
        return {
            "status": "analyzed",
            "summary": {
                "total_attempts": total_nodes,
                "total_failures": len(self.failure_records),
                "failure_rate": round(failure_rate, 3),
                "unique_error_types": len(category_counts)
            },
            "common_patterns": sorted_categories[:5],
            "suggestions": suggestions,
            "learning_metrics": {
                "exploration_depth": checkpoints_used,
                "persistence_score": round(restore_count / max(len(self.failure_records), 1), 2),
                "growth_mindset_indicator": "positive" if restore_count > len(self.failure_records) * 0.5 else "needs_encouragement"
            },
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _generate_suggestions(
        self, 
        sorted_categories: List[Tuple[str, int]]
    ) -> List[Dict[str, str]]:
        """
        基于错误模式生成改进建议
        
        Args:
            sorted_categories: 排序后的错误类别列表
            
        Returns:
            建议列表
        """
        suggestion_templates = {
            "计算错误": {
                "tip": "建议放慢计算速度，逐步验证每一步",
                "resource": "练习基础运算和检查技巧"
            },
            "逻辑错误": {
                "tip": "尝试用流程图或伪代码梳理逻辑",
                "resource": "学习逻辑推理和命题分析"
            },
            "概念误解": {
                "tip": "回顾相关概念的定义和示例",
                "resource": "查看概念讲解视频或教材"
            },
            "边界条件": {
                "tip": "养成检查边界情况的习惯",
                "resource": "练习边界条件分析方法"
            },
            "方法选择": {
                "tip": "在开始前先评估不同方法的适用性",
                "resource": "学习问题分类和方法匹配"
            }
        }
        
        suggestions = []
        for category, count in sorted_categories[:3]:
            template = suggestion_templates.get(category, {
                "tip": "针对此类错误进行专项练习",
                "resource": "咨询老师获取学习资源"
            })
            suggestions.append({
                "category": category,
                "occurrence": count,
                "tip": template["tip"],
                "resource": template["resource"]
            })
        
        return suggestions
    
    def export_timeline(self) -> str:
        """
        导出完整时间线数据为JSON格式
        
        Returns:
            JSON字符串
        """
        export_data = {
            "metadata": {
                "student_id": self.student_id,
                "session_id": self.session_id,
                "export_time": datetime.now().isoformat(),
                "total_nodes": len(self.nodes),
                "total_failures": len(self.failure_records)
            },
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "failure_records": [r.to_dict() for r in self.failure_records],
            "error_graph": self.generate_error_graph(),
            "analysis": self.analyze_failures()
        }
        
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    def get_state_hash(self) -> str:
        """
        获取当前认知状态的哈希值
        
        用于比较不同时刻的认知状态是否相同。
        
        Returns:
            SHA256哈希字符串
        """
        if not self.current_node_id:
            return ""
        
        current_node = self.nodes[self.current_node_id]
        state_str = json.dumps(current_node.cognitive_state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]


def create_demo_session() -> CognitiveTimeline:
    """
    创建演示会话，展示认知时间线的使用方法
    
    Returns:
        配置好的CognitiveTimeline实例
    """
    # 初始化时间线
    timeline = CognitiveTimeline(
        student_id="demo_student_001",
        session_id="math_problem_001"
    )
    
    # 创建第一个检查点：理解题目
    timeline.create_checkpoint(
        "理解题目要求",
        {
            "problem_type": "几何证明",
            "given": ["三角形ABC", "AB=AC", "D是BC中点"],
            "to_prove": "AD垂直于BC",
            "strategy": None
        }
    )
    
    # 更新状态：选择方法
    timeline.update_state(
        "分析解题思路",
        {
            "possible_methods": ["全等三角形", "等腰三角形性质", "坐标法"],
            "selected_method": "全等三角形"
        }
    )
    
    # 创建检查点：开始证明
    timeline.create_checkpoint(
        "开始全等三角形证明",
        {
            "method": "证明三角形ABD全等于三角形ACD",
            "need_conditions": ["AB=AC(已知)", "BD=CD(已知)", "AD=AD(公共边)"]
        }
    )
    
    # 模拟失败
    timeline.mark_failure(
        reason="SSA不能证明全等，缺少角度条件",
        category="概念误解",
        severity=FailureSeverity.MODERATE,
        context={"wrong_assumption": "SSA全等"}
    )
    
    # 回溯到选择方法的节点
    timeline.restore_checkpoint()
    
    # 尝试新方法
    timeline.update_state(
        "改用等腰三角形性质",
        {
            "selected_method": "等腰三角形性质",
            "property": "等腰三角形底边上的中线也是高"
        }
    )
    
    # 创建检查点
    timeline.create_checkpoint(
        "应用等腰三角形性质",
        {
            "applied_property": "三线合一",
            "proof_steps": ["AB=AC(等腰三角形)", "D是BC中点(已知)", "所以AD垂直BC"]
        }
    )
    
    # 标记成功（不是失败）
    timeline.update_state(
        "证明完成",
        {
            "status": "success",
            "method_used": "等腰三角形性质"
        }
    )
    
    return timeline


# 使用示例和测试
if __name__ == "__main__":
    print("=" * 60)
    print("认知时间线系统演示")
    print("=" * 60)
    
    # 创建演示会话
    timeline = create_demo_session()
    
    # 获取可用检查点
    print("\n可用的检查点:")
    checkpoints = timeline.get_available_checkpoints()
    for cp in checkpoints:
        print(f"  - [{cp['id'][:15]}...] {cp['label']}")
    
    # 生成错误图谱
    print("\n错误路径图谱:")
    error_graph = timeline.generate_error_graph()
    print(f"  总失败次数: {error_graph['statistics']['total_failures']}")
    print(f"  错误类别分布: {error_graph['statistics']['category_distribution']}")
    
    # 分析失败
    print("\n失败分析报告:")
    analysis = timeline.analyze_failures()
    if analysis["status"] == "analyzed":
        print(f"  总尝试次数: {analysis['summary']['total_attempts']}")
        print(f"  失败率: {analysis['summary']['failure_rate']}")
        print("  改进建议:")
        for suggestion in analysis["suggestions"]:
            print(f"    - {suggestion['category']}: {suggestion['tip']}")
    
    # 获取当前路径
    print("\n当前认知路径:")
    path = timeline.get_current_path()
    for i, node_id in enumerate(path):
        node = timeline.nodes[node_id]
        status = "❌" if node.is_failure else "✓"
        print(f"  {i+1}. {status} {node.label}")
    
    # 导出数据
    print("\n导出时间线数据...")
    exported = timeline.export_timeline()
    print(f"导出数据大小: {len(exported)} 字节")
    
    # 状态哈希
    print(f"\n当前状态哈希: {timeline.get_state_hash()}")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)