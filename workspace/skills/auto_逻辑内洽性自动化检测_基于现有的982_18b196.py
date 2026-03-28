"""
逻辑内洽性自动化检测模块

基于现有的认知节点网络，构建形式化逻辑验证器。
扫描节点间的依赖关系图，检测循环悖论或相互矛盾的规则。

输入格式:
    nodes (List[Dict]): 节点列表，每个节点包含:
        - id (str): 唯一标识符
        - content (str): 节点内容
        - is_absolute_truth (bool): 是否为绝对真理
        - dependencies (List[str]): 依赖的节点ID列表

输出格式:
    Dict: 包含检测结果:
        - is_valid (bool): 系统是否逻辑内洽
        - circular_paradoxes (List[List[str]]): 检测到的循环悖论
        - contradictions (List[Tuple[str, str]]): 检测到的矛盾对
        - warnings (List[str]): 警告信息
"""

import logging
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型枚举"""
    FACT = "fact"
    RULE = "rule"
    CONSTRAINT = "constraint"


@dataclass
class LogicNode:
    """逻辑节点数据类"""
    id: str
    content: str
    is_absolute_truth: bool = False
    dependencies: List[str] = None
    node_type: NodeType = NodeType.FACT
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class LogicConsistencyValidator:
    """逻辑内洽性验证器"""
    
    def __init__(self, nodes: List[Dict]):
        """
        初始化验证器
        
        Args:
            nodes: 节点列表，每个节点为字典格式
        """
        self.nodes = self._validate_and_convert_nodes(nodes)
        self.adjacency_graph = self._build_adjacency_graph()
        self.contradiction_pairs: List[Tuple[str, str]] = []
        self.circular_paradoxes: List[List[str]] = []
        
    def _validate_and_convert_nodes(self, raw_nodes: List[Dict]) -> List[LogicNode]:
        """
        验证并转换节点数据
        
        Args:
            raw_nodes: 原始节点数据
            
        Returns:
            转换后的LogicNode列表
            
        Raises:
            ValueError: 如果节点数据无效
        """
        validated_nodes = []
        seen_ids = set()
        
        for idx, node in enumerate(raw_nodes):
            try:
                # 检查必需字段
                if 'id' not in node or 'content' not in node:
                    raise ValueError(f"节点 {idx} 缺少必需字段 'id' 或 'content'")
                
                # 检查ID唯一性
                node_id = str(node['id'])
                if node_id in seen_ids:
                    raise ValueError(f"检测到重复的节点ID: {node_id}")
                seen_ids.add(node_id)
                
                # 创建LogicNode对象
                logic_node = LogicNode(
                    id=node_id,
                    content=str(node['content']),
                    is_absolute_truth=bool(node.get('is_absolute_truth', False)),
                    dependencies=list(node.get('dependencies', [])),
                    node_type=NodeType(node.get('node_type', 'fact'))
                )
                
                validated_nodes.append(logic_node)
                
            except Exception as e:
                logger.error(f"节点 {idx} 验证失败: {str(e)}")
                raise
        
        logger.info(f"成功验证 {len(validated_nodes)} 个节点")
        return validated_nodes
    
    def _build_adjacency_graph(self) -> Dict[str, List[str]]:
        """
        构建邻接图表示依赖关系
        
        Returns:
            邻接字典 {节点ID: [依赖节点ID列表]}
        """
        graph = {node.id: [] for node in self.nodes}
        node_ids = {node.id for node in self.nodes}
        
        for node in self.nodes:
            for dep_id in node.dependencies:
                if dep_id not in node_ids:
                    logger.warning(f"节点 {node.id} 引用了不存在的依赖 {dep_id}")
                    continue
                graph[node.id].append(dep_id)
        
        logger.debug(f"构建邻接图完成，包含 {len(graph)} 个节点")
        return graph
    
    def _detect_cycles_dfs(
        self,
        node: str,
        visited: Set[str],
        rec_stack: Set[str],
        path: List[str]
    ) -> Optional[List[str]]:
        """
        使用DFS检测循环依赖
        
        Args:
            node: 当前节点ID
            visited: 已访问节点集合
            rec_stack: 递归栈中的节点集合
            path: 当前路径
            
        Returns:
            如果检测到循环，返回循环路径；否则返回None
        """
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in self.adjacency_graph.get(node, []):
            if neighbor not in visited:
                cycle = self._detect_cycles_dfs(neighbor, visited, rec_stack, path)
                if cycle:
                    return cycle
            elif neighbor in rec_stack:
                # 找到循环
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
        
        path.pop()
        rec_stack.remove(node)
        return None
    
    def detect_circular_paradoxes(self) -> List[List[str]]:
        """
        检测循环悖论
        
        Returns:
            检测到的循环路径列表
        """
        logger.info("开始检测循环悖论...")
        
        visited = set()
        cycles = []
        
        for node_id in self.adjacency_graph:
            if node_id not in visited:
                cycle = self._detect_cycles_dfs(node_id, visited, set(), [])
                if cycle:
                    # 标准化循环表示（从最小ID开始）
                    min_idx = cycle.index(min(cycle))
                    normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                    
                    if normalized not in cycles:
                        cycles.append(normalized)
                        logger.warning(f"检测到循环悖论: {' -> '.join(normalized)}")
        
        self.circular_paradoxes = cycles
        logger.info(f"循环悖论检测完成，发现 {len(cycles)} 个循环")
        return cycles
    
    def detect_contradictions(self) -> List[Tuple[str, str]]:
        """
        检测相互矛盾的绝对真理
        
        Returns:
            检测到的矛盾节点对列表
        """
        logger.info("开始检测矛盾规则...")
        
        # 提取所有绝对真理节点
        absolute_nodes = [node for node in self.nodes if node.is_absolute_truth]
        
        # 定义矛盾关键词对
        contradiction_keywords = [
            ('必须吃素', '必须吃肉'),
            ('永远不', '必须'),
            ('禁止', '要求'),
            ('不可能', '必然'),
            ('错误', '正确')
        ]
        
        contradictions = []
        
        # 检查所有绝对真理对
        for i, node_a in enumerate(absolute_nodes):
            for node_b in absolute_nodes[i+1:]:
                # 检查是否包含矛盾关键词
                for keyword_a, keyword_b in contradiction_keywords:
                    if (keyword_a in node_a.content and keyword_b in node_b.content):
                        contradictions.append((node_a.id, node_b.id))
                        logger.warning(
                            f"检测到矛盾: 节点 {node_a.id} ({keyword_a}) "
                            f"vs 节点 {node_b.id} ({keyword_b})"
                        )
                        break
        
        self.contradiction_pairs = contradictions
        logger.info(f"矛盾检测完成，发现 {len(contradictions)} 对矛盾")
        return contradictions
    
    def validate_system(self) -> Dict:
        """
        执行完整的逻辑内洽性验证
        
        Returns:
            包含所有检测结果的字典
        """
        logger.info("开始系统逻辑内洽性验证...")
        
        # 执行检测
        circular_paradoxes = self.detect_circular_paradoxes()
        contradictions = self.detect_contradictions()
        
        # 生成警告
        warnings = []
        if circular_paradoxes:
            warnings.append(f"系统包含 {len(circular_paradoxes)} 个循环依赖")
        if contradictions:
            warnings.append(f"系统包含 {len(contradictions)} 对矛盾规则")
        
        # 判断系统是否有效
        is_valid = not bool(circular_paradoxes or contradictions)
        
        result = {
            'is_valid': is_valid,
            'circular_paradoxes': circular_paradoxes,
            'contradictions': contradictions,
            'warnings': warnings,
            'statistics': {
                'total_nodes': len(self.nodes),
                'absolute_truth_nodes': sum(1 for n in self.nodes if n.is_absolute_truth),
                'dependency_edges': sum(len(deps) for deps in self.adjacency_graph.values())
            }
        }
        
        if is_valid:
            logger.info("系统逻辑内洽性验证通过")
        else:
            logger.error("系统逻辑内洽性验证失败")
        
        return result


def generate_sample_nodes(count: int = 10) -> List[Dict]:
    """
    生成示例节点数据
    
    Args:
        count: 要生成的节点数量
        
    Returns:
        示例节点列表
    """
    base_nodes = [
        {'id': 'A', 'content': '为了健康必须吃素', 'is_absolute_truth': True, 'dependencies': []},
        {'id': 'B', 'content': '为了力量必须吃肉', 'is_absolute_truth': True, 'dependencies': []},
        {'id': 'C', 'content': '健康是力量的基础', 'is_absolute_truth': False, 'dependencies': ['A', 'B']},
        {'id': 'D', 'content': '运动增强体质', 'is_absolute_truth': False, 'dependencies': ['C']},
        {'id': 'E', 'content': '体质决定健康', 'is_absolute_truth': False, 'dependencies': ['D', 'A']},
        {'id': 'F', 'content': '睡眠促进恢复', 'is_absolute_truth': True, 'dependencies': []},
        {'id': 'G', 'content': '恢复需要营养', 'is_absolute_truth': False, 'dependencies': ['F', 'B']},
        {'id': 'H', 'content': '营养来自食物', 'is_absolute_truth': True, 'dependencies': []},
        {'id': 'I', 'content': '食物分为植物性和动物性', 'is_absolute_truth': True, 'dependencies': []},
        {'id': 'J', 'content': '平衡饮食最重要', 'is_absolute_truth': False, 'dependencies': ['H', 'I']},
    ]
    
    return base_nodes[:min(count, len(base_nodes))]


if __name__ == "__main__":
    # 示例用法
    print("=== 逻辑内洽性自动化检测示例 ===")
    
    # 生成测试数据
    sample_nodes = generate_sample_nodes()
    
    # 创建验证器实例
    validator = LogicConsistencyValidator(sample_nodes)
    
    # 执行验证
    result = validator.validate_system()
    
    # 打印结果
    print(f"\n系统有效性: {'通过' if result['is_valid'] else '失败'}")
    print(f"总节点数: {result['statistics']['total_nodes']}")
    print(f"绝对真理节点数: {result['statistics']['absolute_truth_nodes']}")
    
    if result['circular_paradoxes']:
        print("\n检测到的循环悖论:")
        for cycle in result['circular_paradoxes']:
            print(f"  - {' -> '.join(cycle)}")
    
    if result['contradictions']:
        print("\n检测到的矛盾规则:")
        for pair in result['contradictions']:
            print(f"  - 节点 {pair[0]} 与 节点 {pair[1]} 矛盾")
    
    if result['warnings']:
        print("\n警告:")
        for warning in result['warnings']:
            print(f"  - {warning}")