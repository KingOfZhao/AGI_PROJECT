"""
路径依赖型实践方案推荐引擎

该模块实现了一个基于图结构的推荐系统，用于解决复杂的实践问题。
它通过构建'情境-方案-后果'的立体网络，提供符合当前工具箱（节点）、
避开之前失败尝试（路径）、且不破坏后续步骤（拓扑结构）的定制化解决方案。

模块主要组件:
    - Action: 定义行动节点的数据结构
    - RecommendationEngine: 核心推荐引擎类
    - 辅助函数: 用于图分析和路径评估

典型用例:
    >>> engine = RecommendationEngine()
    >>> engine.load_knowledge_base("repair_db.json")
    >>> solution = engine.recommend(
            problem="network_failure",
            available_tools=["cli", "ping"],
            failed_attempts=["restart_router"]
        )
"""

import json
import logging
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass(order=True)
class Action:
    """
    表示解决方案网络中的一个行动节点。
    
    属性:
        id: 唯一标识符
        name: 行动名称
        requirements: 执行此行动所需的工具/资源
        provides: 执行后提供的资源/状态
        risk_level: 风险等级 (1-10)
        dependencies: 前置行动ID列表
    """
    id: str
    name: str
    requirements: Set[str] = field(default_factory=set)
    provides: Set[str] = field(default_factory=set)
    risk_level: int = 1
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """数据验证和边界检查"""
        if not self.id or not self.name:
            raise ValueError("Action ID and name cannot be empty")
        if not 1 <= self.risk_level <= 10:
            raise ValueError("Risk level must be between 1 and 10")


class RecommendationEngine:
    """
    路径依赖型推荐引擎核心类。
    
    该引擎维护一个行动图，并根据当前状态、可用工具和
    历史路径提供最佳行动建议。
    """
    
    def __init__(self):
        """初始化推荐引擎"""
        self.actions: Dict[str, Action] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        logger.info("RecommendationEngine initialized")
    
    def load_knowledge_base(self, file_path: str) -> None:
        """
        从JSON文件加载知识库。
        
        参数:
            file_path: JSON文件路径
            
        抛出:
            FileNotFoundError: 文件不存在
            ValueError: 数据格式无效
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Knowledge base file not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                raise ValueError("Invalid knowledge base format")
            
            self._build_graph(data)
            logger.info(f"Loaded {len(self.actions)} actions from knowledge base")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
    
    def _build_graph(self, data: Dict[str, Any]) -> None:
        """构建行动图和反向图"""
        for action_id, action_data in data.items():
            try:
                action = Action(
                    id=action_id,
                    name=action_data.get('name', action_id),
                    requirements=set(action_data.get('requirements', [])),
                    provides=set(action_data.get('provides', [])),
                    risk_level=action_data.get('risk_level', 1),
                    dependencies=action_data.get('dependencies', [])
                )
                self.actions[action_id] = action
                
                # 构建依赖图
                for dep in action.dependencies:
                    self.graph[dep].append(action_id)
                    self.reverse_graph[action_id].append(dep)
                    
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid action {action_id}: {e}")
                continue
    
    def recommend(
        self,
        problem: str,
        available_tools: List[str],
        failed_attempts: List[str],
        current_state: Optional[Set[str]] = None,
        max_depth: int = 5
    ) -> List[Tuple[Action, int]]:
        """
        基于当前状态和约束推荐行动序列。
        
        参数:
            problem: 要解决的问题标识符
            available_tools: 当前可用的工具/资源列表
            failed_attempts: 之前失败尝试的行动ID列表
            current_state: 当前状态标记集合
            max_depth: 最大搜索深度
            
        返回:
            排序后的行动列表及其得分，格式为 [(Action, score), ...]
            
        抛出:
            ValueError: 如果问题无效或没有可用工具
        """
        # 数据验证
        if not problem:
            raise ValueError("Problem cannot be empty")
        if not available_tools:
            raise ValueError("Available tools list cannot be empty")
        
        current_state = current_state or set()
        available_tools = set(available_tools)
        failed_set = set(failed_attempts)
        
        logger.info(f"Starting recommendation for problem: {problem}")
        logger.debug(f"Available tools: {available_tools}")
        logger.debug(f"Failed attempts: {failed_set}")
        
        # 寻找候选行动
        candidates = self._find_candidate_actions(
            available_tools, failed_set, current_state
        )
        
        if not candidates:
            logger.warning("No candidate actions found")
            return []
        
        # 评估和排序候选行动
        scored_actions = []
        for action in candidates:
            score = self._evaluate_action(
                action, problem, available_tools, failed_set, current_state
            )
            scored_actions.append((action, score))
        
        # 按分数降序排序
        scored_actions.sort(key=lambda x: (-x[1], x[0].risk_level))
        
        logger.info(f"Found {len(scored_actions)} candidate actions")
        return scored_actions[:max_depth]
    
    def _find_candidate_actions(
        self,
        available_tools: Set[str],
        failed_set: Set[str],
        current_state: Set[str]
    ) -> List[Action]:
        """寻找符合当前约束的候选行动"""
        candidates = []
        
        for action_id, action in self.actions.items():
            # 跳过已失败尝试
            if action_id in failed_set:
                logger.debug(f"Skipping failed action: {action_id}")
                continue
            
            # 检查工具要求
            if not action.requirements.issubset(available_tools):
                logger.debug(f"Action {action_id} requires missing tools")
                continue
            
            # 检查依赖是否满足
            dependencies_met = all(
                dep in current_state or dep in failed_set
                for dep in action.dependencies
            )
            
            if not dependencies_met:
                logger.debug(f"Action {action_id} has unmet dependencies")
                continue
            
            candidates.append(action)
        
        return candidates
    
    def _evaluate_action(
        self,
        action: Action,
        problem: str,
        available_tools: Set[str],
        failed_set: Set[str],
        current_state: Set[str]
    ) -> int:
        """
        评估行动的适用性得分。
        
        得分基于:
        1. 与问题的相关性 (最高40分)
        2. 工具利用率 (最高20分)
        3. 风险等级 (最高20分，风险越低分数越高)
        4. 拓扑安全性 (最高20分)
        """
        score = 0
        
        # 1. 问题相关性 (检查是否直接解决问题)
        if problem in action.provides:
            score += 40
        elif any(p.startswith(problem) for p in action.provides):
            score += 30
        
        # 2. 工具利用率
        used_tools = len(action.requirements & available_tools)
        total_tools = len(available_tools)
        if total_tools > 0:
            score += int((used_tools / total_tools) * 20)
        
        # 3. 风险评估 (风险越低分数越高)
        score += (11 - action.risk_level) * 2
        
        # 4. 拓扑安全性 (检查后续行动是否可行)
        safe_successors = 0
        for successor_id in self.graph[action.id]:
            if successor_id not in failed_set:
                successor = self.actions.get(successor_id)
                if successor and successor.requirements.issubset(
                    available_tools | action.provides
                ):
                    safe_successors += 1
        
        if safe_successors > 0:
            score += min(20, safe_successors * 4)
        
        return score


def visualize_path(
    engine: RecommendationEngine,
    actions: List[Tuple[Action, int]],
    output_format: str = "text"
) -> str:
    """
    可视化推荐路径。
    
    参数:
        engine: 推荐引擎实例
        actions: 推荐的行动列表
        output_format: 输出格式 ('text' 或 'mermaid')
        
    返回:
        格式化的路径表示字符串
        
    抛出:
        ValueError: 如果输出格式不支持
    """
    if not actions:
        return "No actions to visualize"
    
    if output_format == "text":
        lines = ["Recommended Path:"]
        for i, (action, score) in enumerate(actions, 1):
            deps = ", ".join(action.dependencies) if action.dependencies else "None"
            lines.append(
                f"{i}. {action.name} (Score: {score}, Risk: {action.risk_level})\n"
                f"   Requires: {', '.join(action.requirements)}\n"
                f"   Provides: {', '.join(action.provides)}\n"
                f"   Dependencies: {deps}"
            )
        return "\n".join(lines)
    
    elif output_format == "mermaid":
        lines = ["graph TD"]
        added_nodes = set()
        
        for action, _ in actions:
            if action.id not in added_nodes:
                lines.append(f"    {action.id}[\"{action.name}\"]")
                added_nodes.add(action.id)
            
            for dep in action.dependencies:
                if dep in engine.actions and dep not in added_nodes:
                    dep_action = engine.actions[dep]
                    lines.append(f"    {dep}[\"{dep_action.name}\"]")
                    added_nodes.add(dep)
                lines.append(f"    {dep} --> {action.id}")
        
        return "\n".join(lines)
    
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def validate_knowledge_base(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证知识库数据结构。
    
    参数:
        data: 要验证的知识库数据
        
    返回:
        元组 (是否有效, 错误消息列表)
    """
    errors = []
    
    if not isinstance(data, dict):
        return False, ["Knowledge base must be a dictionary"]
    
    for action_id, action_data in data.items():
        if not isinstance(action_data, dict):
            errors.append(f"Action {action_id} data must be a dictionary")
            continue
        
        if 'name' not in action_data:
            errors.append(f"Action {action_id} missing 'name' field")
        
        risk = action_data.get('risk_level', 1)
        if not isinstance(risk, int) or not 1 <= risk <= 10:
            errors.append(f"Action {action_id} has invalid risk level: {risk}")
        
        for field_name in ['requirements', 'provides', 'dependencies']:
            if field_name in action_data and not isinstance(action_data[field_name], list):
                errors.append(f"Action {action_id} '{field_name}' must be a list")
    
    return len(errors) == 0, errors


# 示例用法
if __name__ == "__main__":
    # 创建示例知识库
    sample_kb = {
        "restart_service": {
            "name": "Restart Network Service",
            "requirements": ["cli", "sudo"],
            "provides": ["service_restarted"],
            "risk_level": 3,
            "dependencies": []
        },
        "check_logs": {
            "name": "Check System Logs",
            "requirements": ["cli"],
            "provides": ["logs_analyzed"],
            "risk_level": 1,
            "dependencies": []
        },
        "update_config": {
            "name": "Update Network Configuration",
            "requirements": ["cli", "sudo", "editor"],
            "provides": ["config_updated"],
            "risk_level": 5,
            "dependencies": ["check_logs"]
        },
        "restart_router": {
            "name": "Restart Router Hardware",
            "requirements": ["physical_access", "power_control"],
            "provides": ["router_restarted"],
            "risk_level": 8,
            "dependencies": []
        },
        "verify_connectivity": {
            "name": "Verify Network Connectivity",
            "requirements": ["cli", "ping"],
            "provides": ["network_verified"],
            "risk_level": 1,
            "dependencies": ["restart_service"]
        }
    }
    
    # 保存示例知识库到文件
    kb_path = "sample_knowledge_base.json"
    with open(kb_path, 'w') as f:
        json.dump(sample_kb, f, indent=2)
    
    # 使用推荐引擎
    engine = RecommendationEngine()
    engine.load_knowledge_base(kb_path)
    
    # 场景1: 正常推荐
    print("\n=== Scenario 1: Standard Recommendation ===")
    recommendations = engine.recommend(
        problem="network_verified",
        available_tools=["cli", "ping", "sudo"],
        failed_attempts=[]
    )
    print(visualize_path(engine, recommendations))
    
    # 场景2: 路径依赖推荐 (有失败尝试)
    print("\n=== Scenario 2: Path-Dependent Recommendation ===")
    recommendations = engine.recommend(
        problem="network_verified",
        available_tools=["cli", "ping", "sudo"],
        failed_attempts=["restart_service"]
    )
    print(visualize_path(engine, recommendations))
    
    # 场景3: 工具受限情况
    print("\n=== Scenario 3: Limited Tools Available ===")
    recommendations = engine.recommend(
        problem="network_verified",
        available_tools=["cli"],
        failed_attempts=[]
    )
    print(visualize_path(engine, recommendations))
    
    # 验证知识库
    print("\n=== Knowledge Base Validation ===")
    is_valid, errors = validate_knowledge_base(sample_kb)
    print(f"Valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")