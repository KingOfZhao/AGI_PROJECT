"""
跨域工具链组装模块

本模块实现了一个基于有向无环图(DAG)的跨域工具链组装系统。当用户意图需要跨越多个领域
(如"分析股票数据并生成图表发邮件")时，系统能够根据可用技能节点动态规划出最优执行路径。

核心功能:
1. 基于技能依赖关系的DAG构建
2. 依赖冲突检测与解决
3. 最优执行路径规划
4. 执行计划验证与优化

典型使用示例:
    >>> from auto_cross_domain_toolchain import ToolChainAssembler
    >>> assembler = ToolChainAssembler(skill_nodes)
    >>> plan = assembler.assemble(
    ...     intent="分析AAPL股票数据并生成图表发邮件",
    ...     constraints={"max_execution_time": 60}
    ... )
    >>> plan.execute()

输入输出格式:
    输入: 自然语言意图描述 + 可选约束条件
    输出: 可执行的DAG工作流计划
"""

import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import networkx as nx
import numpy as np
from pydantic import BaseModel, validator, constr

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("CrossDomainToolchain")


class SkillCategory(Enum):
    """技能类别枚举"""
    DATA_RETRIEVAL = auto()
    DATA_PROCESSING = auto()
    VISUALIZATION = auto()
    COMMUNICATION = auto()
    ANALYSIS = auto()
    STORAGE = auto()


@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    Attributes:
        id: 唯一标识符
        name: 技能名称
        description: 技能描述
        category: 技能类别
        input_requirements: 输入数据要求
        output_capabilities: 输出数据能力
        dependencies: 依赖的其他技能ID
        estimated_time: 预估执行时间(秒)
        reliability: 可靠性评分(0-1)
    """
    id: str
    name: str
    description: str
    category: SkillCategory
    input_requirements: Set[str]
    output_capabilities: Set[str]
    dependencies: Set[str] = field(default_factory=set)
    estimated_time: float = 1.0
    reliability: float = 0.95


class ExecutionPlan(BaseModel):
    """
    执行计划模型，包含数据验证
    
    Attributes:
        plan_id: 计划唯一ID
        dag: 工作流有向无环图
        nodes: 执行节点列表
        estimated_duration: 预估总时间
        confidence: 计划置信度
        metadata: 其他元数据
    """
    plan_id: str
    dag: Dict[str, List[str]]
    nodes: List[Dict[str, Any]]
    estimated_duration: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @validator("confidence")
    def validate_confidence(cls, v):
        """验证置信度在0-1之间"""
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class ToolChainAssembler:
    """
    跨域工具链组装器
    
    根据用户意图和可用技能节点，动态规划出最优的DAG执行计划。
    处理技能间的依赖关系，解决潜在冲突，确保计划的可执行性。
    
    Attributes:
        skill_nodes: 可用的技能节点集合
        skill_index: 按输出能力索引的技能映射
        dependency_graph: 全局依赖关系图
    """
    
    def __init__(self, skill_nodes: List[SkillNode]):
        """
        初始化工具链组装器
        
        Args:
            skill_nodes: 可用的技能节点列表
        """
        self.skill_nodes = {node.id: node for node in skill_nodes}
        self.skill_index = self._build_skill_index(skill_nodes)
        self.dependency_graph = self._build_dependency_graph(skill_nodes)
        logger.info(f"Initialized ToolChainAssembler with {len(skill_nodes)} skill nodes")
    
    def _build_skill_index(self, skill_nodes: List[SkillNode]) -> Dict[str, Set[str]]:
        """
        构建技能索引，按输出能力组织技能
        
        Args:
            skill_nodes: 技能节点列表
            
        Returns:
            按输出能力索引的技能字典 {能力: 技能ID集合}
        """
        index = defaultdict(set)
        for node in skill_nodes:
            for capability in node.output_capabilities:
                index[capability].add(node.id)
        return dict(index)
    
    def _build_dependency_graph(self, skill_nodes: List[SkillNode]) -> nx.DiGraph:
        """
        构建全局依赖关系图
        
        Args:
            skill_nodes: 技能节点列表
            
        Returns:
            网络X有向图表示的依赖关系
        """
        graph = nx.DiGraph()
        
        # 添加所有节点
        for node in skill_nodes:
            graph.add_node(node.id, data=node)
        
        # 添加依赖边
        for node in skill_nodes:
            for dep_id in node.dependencies:
                if dep_id in self.skill_nodes:
                    graph.add_edge(dep_id, node.id)
        
        # 验证无环
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Dependency graph contains cycles")
            
        return graph
    
    def assemble(
        self,
        intent: constr(min_length=5, max_length=500),
        constraints: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        根据意图组装执行计划
        
        Args:
            intent: 用户意图描述
            constraints: 可选约束条件，如:
                - max_execution_time: 最大执行时间(秒)
                - required_capabilities: 必须包含的能力
                - excluded_skills: 排除的技能ID
                
        Returns:
            可执行的ExecutionPlan对象
            
        Raises:
            ValueError: 如果无法构建有效的执行计划
        """
        constraints = constraints or {}
        logger.info(f"Assembling plan for intent: {intent[:50]}...")
        
        try:
            # 1. 解析意图所需的能力
            required_caps = self._parse_intent_requirements(intent)
            if "required_capabilities" in constraints:
                required_caps.update(constraints["required_capabilities"])
            
            # 2. 选择候选技能
            candidate_skills = self._select_candidate_skills(required_caps)
            
            # 3. 构建初始DAG
            dag = self._build_initial_dag(candidate_skills, required_caps)
            
            # 4. 解决依赖冲突
            resolved_dag = self._resolve_dependency_conflicts(dag)
            
            # 5. 优化执行计划
            optimized_dag = self._optimize_execution_plan(
                resolved_dag,
                constraints.get("max_execution_time", float("inf"))
            )
            
            # 6. 生成最终执行计划
            plan = self._generate_execution_plan(optimized_dag)
            
            logger.info(f"Successfully assembled plan {plan.plan_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to assemble plan: {str(e)}")
            raise ValueError(f"Plan assembly failed: {str(e)}") from e
    
    def _parse_intent_requirements(self, intent: str) -> Set[str]:
        """
        解析意图所需的能力(简化版，实际应使用NLP模型)
        
        Args:
            intent: 用户意图
            
        Returns:
            所需的能力集合
        """
        # 这里使用简单关键词匹配，实际应使用NLP模型
        capabilities = set()
        
        keywords_map = {
            "分析": {"data_analysis", "statistical_analysis"},
            "股票": {"stock_data_retrieval"},
            "数据": {"data_processing"},
            "图表": {"chart_generation"},
            "发邮件": {"email_sending"},
            "报告": {"report_generation"},
            "预测": {"prediction_model"},
            "存储": {"data_storage"},
            "可视化": {"data_visualization"}
        }
        
        for keyword, caps in keywords_map.items():
            if keyword in intent:
                capabilities.update(caps)
                
        logger.debug(f"Parsed intent requirements: {capabilities}")
        return capabilities
    
    def _select_candidate_skills(
        self,
        required_capabilities: Set[str]
    ) -> List[SkillNode]:
        """
        选择满足能力需求的候选技能
        
        Args:
            required_capabilities: 所需的能力集合
            
        Returns:
            候选技能列表
            
        Raises:
            ValueError: 如果无法满足所有能力需求
        """
        candidates = []
        missing_caps = set()
        
        for cap in required_capabilities:
            if cap in self.skill_index:
                # 简单起见，选择每个能力的第一个技能
                # 实际应更复杂的选择逻辑
                skill_id = next(iter(self.skill_index[cap]))
                candidates.append(self.skill_nodes[skill_id])
            else:
                missing_caps.add(cap)
        
        if missing_caps:
            raise ValueError(f"No skills found for capabilities: {missing_caps}")
            
        return candidates
    
    def _build_initial_dag(
        self,
        skills: List[SkillNode],
        required_capabilities: Set[str]
    ) -> nx.DiGraph:
        """
        构建初始DAG图
        
        Args:
            skills: 候选技能列表
            required_capabilities: 所需能力
            
        Returns:
            初始DAG图
        """
        dag = nx.DiGraph()
        
        # 添加所有技能节点
        for skill in skills:
            dag.add_node(skill.id, data=skill)
        
        # 添加依赖边
        for skill in skills:
            for dep_id in skill.dependencies:
                if dep_id in self.skill_nodes:
                    dag.add_edge(dep_id, skill.id)
        
        # 添加数据流边(基于输入输出匹配)
        skill_outputs = defaultdict(set)
        for skill in skills:
            for output in skill.output_capabilities:
                skill_outputs[output].add(skill.id)
        
        for skill in skills:
            for input_req in skill.input_requirements:
                for provider_id in skill_outputs.get(input_req, set()):
                    if provider_id != skill.id:
                        dag.add_edge(provider_id, skill.id)
        
        if not nx.is_directed_acyclic_graph(dag):
            raise ValueError("Initial DAG contains cycles")
            
        return dag
    
    def _resolve_dependency_conflicts(self, dag: nx.DiGraph) -> nx.DiGraph:
        """
        解决依赖冲突
        
        Args:
            dag: 输入DAG图
            
        Returns:
            解决冲突后的DAG图
        """
        # 这里简化处理，实际应包含更复杂的冲突解决逻辑
        # 例如: 1. 检测并解决循环依赖 2. 处理版本冲突 3. 解决资源竞争
        
        # 检查是否有循环依赖
        if not nx.is_directed_acyclic_graph(dag):
            # 尝试解决循环依赖
            try:
                # 使用深度优先搜索找到循环
                cycles = list(nx.simple_cycles(dag))
                logger.warning(f"Detected {len(cycles)} dependency cycles")
                
                # 简单解决策略: 移除循环中的一条边
                for cycle in cycles:
                    if len(cycle) > 1:
                        dag.remove_edge(cycle[0], cycle[1])
                        logger.debug(f"Removed edge {cycle[0]}->{cycle[1]} to break cycle")
                
                if not nx.is_directed_acyclic_graph(dag):
                    raise ValueError("Unable to resolve all dependency cycles")
                    
            except Exception as e:
                raise ValueError(f"Failed to resolve dependency conflicts: {str(e)}") from e
        
        return dag
    
    def _optimize_execution_plan(
        self,
        dag: nx.DiGraph,
        max_execution_time: float
    ) -> nx.DiGraph:
        """
        优化执行计划
        
        Args:
            dag: 输入DAG图
            max_execution_time: 最大允许执行时间
            
        Returns:
            优化后的DAG图
        """
        # 计算当前预估执行时间
        total_time = sum(
            self.skill_nodes[node_id].estimated_time
            for node_id in dag.nodes()
        )
        
        if total_time > max_execution_time:
            logger.warning(
                f"Estimated time {total_time}s exceeds limit {max_execution_time}s"
            )
            
            # 简单优化策略: 移除非关键路径上的节点
            # 实际应使用更复杂的优化算法
            critical_path = nx.dag_longest_path(dag)
            non_critical_nodes = set(dag.nodes()) - set(critical_path)
            
            for node_id in non_critical_nodes:
                dag.remove_node(node_id)
                logger.debug(f"Removed non-critical node {node_id} to reduce execution time")
        
        return dag
    
    def _generate_execution_plan(self, dag: nx.DiGraph) -> ExecutionPlan:
        """
        生成最终执行计划
        
        Args:
            dag: 优化后的DAG图
            
        Returns:
            ExecutionPlan对象
        """
        # 生成DAG的邻接表表示
        dag_dict = defaultdict(list)
        for u, v in dag.edges():
            dag_dict[u].append(v)
        
        # 准备节点信息
        nodes = []
        for node_id in dag.nodes():
            skill = self.skill_nodes[node_id]
            nodes.append({
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "estimated_time": skill.estimated_time,
                "reliability": skill.reliability
            })
        
        # 计算计划属性
        estimated_duration = sum(
            self.skill_nodes[node_id].estimated_time
            for node_id in dag.nodes()
        )
        
        confidence = np.mean([
            self.skill_nodes[node_id].reliability
            for node_id in dag.nodes()
        ])
        
        return ExecutionPlan(
            plan_id=f"plan_{hash(frozenset(dag.nodes())) % 10000:04d}",
            dag=dict(dag_dict),
            nodes=nodes,
            estimated_duration=estimated_duration,
            confidence=confidence,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(dag.edges())
            }
        )


# 示例使用
if __name__ == "__main__":
    # 示例技能节点
    example_skills = [
        SkillNode(
            id="stock_data_retrieval",
            name="Stock Data Retriever",
            description="Retrieve stock market data from various sources",
            category=SkillCategory.DATA_RETRIEVAL,
            input_requirements={"stock_symbol"},
            output_capabilities={"stock_data_retrieval", "time_series_data"},
            estimated_time=2.5,
            reliability=0.98
        ),
        SkillNode(
            id="data_analysis",
            name="Data Analyzer",
            description="Perform statistical analysis on numeric data",
            category=SkillCategory.ANALYSIS,
            input_requirements={"time_series_data"},
            output_capabilities={"data_analysis", "statistical_analysis"},
            dependencies={"stock_data_retrieval"},
            estimated_time=3.0,
            reliability=0.95
        ),
        SkillNode(
            id="chart_generation",
            name="Chart Generator",
            description="Generate visual charts from analyzed data",
            category=SkillCategory.VISUALIZATION,
            input_requirements={"statistical_analysis"},
            output_capabilities={"chart_generation", "data_visualization"},
            dependencies={"data_analysis"},
            estimated_time=1.5,
            reliability=0.97
        ),
        SkillNode(
            id="email_sending",
            name="Email Sender",
            description="Send emails with attachments and content",
            category=SkillCategory.COMMUNICATION,
            input_requirements={"chart_generation"},
            output_capabilities={"email_sending"},
            dependencies={"chart_generation"},
            estimated_time=0.5,
            reliability=0.99
        )
    ]
    
    # 初始化组装器
    assembler = ToolChainAssembler(example_skills)
    
    # 示例意图
    intent = "分析AAPL股票数据，生成图表并发送邮件报告"
    
    # 组装执行计划
    try:
        plan = assembler.assemble(
            intent=intent,
            constraints={"max_execution_time": 10.0}
        )
        
        print(f"\nGenerated Execution Plan (ID: {plan.plan_id}):")
        print(f"- Estimated Duration: {plan.estimated_duration:.1f}s")
        print(f"- Confidence: {plan.confidence:.2%}")
        print("\nExecution Steps:")
        for i, node in enumerate(plan.nodes, 1):
            print(f"{i}. {node['name']} ({node['estimated_time']:.1f}s)")
        
        print("\nDAG Structure:")
        for node, deps in plan.dag.items():
            print(f"{node} -> {', '.join(deps) if deps else 'END'}")
            
    except Exception as e:
        print(f"Error: {str(e)}")