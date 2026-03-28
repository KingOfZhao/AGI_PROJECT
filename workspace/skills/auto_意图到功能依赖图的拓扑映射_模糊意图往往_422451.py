"""
模块名称: auto_意图到功能依赖图的拓扑映射_模糊意图往往_422451
描述: 本模块实现了从模糊的自然语言意图到结构化功能依赖图的映射。
      它模拟了AGI系统中"结构化认知网络"的能力，能够识别意图背后的
      拓扑结构，解析模块间的依赖关系（如初始化顺序），并进行验证。
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from collections import deque

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DependencyGraphError(Exception):
    """自定义异常类，用于处理依赖图相关的错误（如循环依赖）。"""
    pass


class IntentParser:
    """
    负责将模糊的自然语言意图解析为结构化的功能节点和依赖关系。
    这是将非结构化信息转化为结构化拓扑的第一步。
    """

    def __init__(self):
        # 定义意图关键词到功能节点的映射规则
        self._keyword_map = {
            r"database|db|存储": "DatabaseModule",
            r"cache|缓存|redis": "CacheModule",
            r"auth|认证|登录": "AuthModule",
            r"api|接口|rest": "ApiGateway",
            r"log|日志|监控": "LoggingModule",
            r"config|配置": "ConfigModule"
        }

    def parse_intent(self, intent_text: str) -> Tuple[Set[str], List[Tuple[str, str]]]:
        """
        解析意图文本，提取功能节点和显式/隐式依赖关系。

        Args:
            intent_text (str): 用户的模糊意图描述，例如 "我需要一个带认证的API，它要连数据库".

        Returns:
            Tuple[Set[str], List[Tuple[str, str]]]: 
                - 功能节点集合
                - 依赖关系列表 (源节点, 目标节点)
        """
        if not isinstance(intent_text, str) or not intent_text.strip():
            logger.warning("输入意图为空或非字符串")
            return set(), []

        identified_nodes = set()
        
        # 1. 识别节点
        for pattern, node_name in self._keyword_map.items():
            if re.search(pattern, intent_text, re.IGNORECASE):
                identified_nodes.add(node_name)
        
        logger.info(f"从意图中识别出节点: {identified_nodes}")

        # 2. 推断依赖关系 (基于领域知识的隐式拓扑映射)
        # 这里模拟了AI对系统架构的理解：Config是基础，DB需要Config，Auth需要DB等
        relations = []
        
        # 规则：所有模块依赖于配置
        if "ConfigModule" in identified_nodes:
            for node in identified_nodes:
                if node != "ConfigModule":
                    relations.append((node, "ConfigModule"))

        # 规则：Auth 依赖 DB (通常用户数据在DB)
        if "AuthModule" in identified_nodes and "DatabaseModule" in identified_nodes:
            relations.append(("AuthModule", "DatabaseModule"))

        # 规则：API 依赖 Auth (通常API需要鉴权)
        if "ApiGateway" in identified_nodes and "AuthModule" in identified_nodes:
            relations.append(("ApiGateway", "AuthModule"))
        
        # 规则：Cache 依赖 Config
        if "CacheModule" in identified_nodes and "ConfigModule" in identified_nodes:
            relations.append(("CacheModule", "ConfigModule"))

        logger.info(f"推断出的依赖关系: {relations}")
        return identified_nodes, relations


class TopologyMapper:
    """
    负责构建功能依赖图并进行拓扑逻辑验证。
    核心能力是检测循环依赖并生成初始化顺序。
    """

    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}
        self.reverse_graph: Dict[str, Set[str]] = {}

    def _add_edge(self, u: str, v: str) -> None:
        """辅助函数：添加边到图中"""
        if u not in self.graph:
            self.graph[u] = set()
        if v not in self.graph:
            self.graph[v] = set() # 确保孤立节点也在图中
        self.graph[u].add(v)

    def build_graph(self, nodes: Set[str], dependencies: List[Tuple[str, str]]) -> None:
        """
        构建邻接表表示的有向图。

        Args:
            nodes (Set[str]): 所有功能节点的集合。
            dependencies (List[Tuple[str, str]]): 依赖列表，(A, B) 表示 A 依赖于 B。
        """
        self.graph = {node: set() for node in nodes}
        
        for u, v in dependencies:
            if u in nodes and v in nodes:
                self._add_edge(u, v)
            else:
                logger.warning(f"忽略无效的依赖边: ({u}, {v})，节点不在识别集合中。")
        
        logger.info("功能依赖图构建完成")

    def topological_sort(self) -> List[str]:
        """
        执行拓扑排序以确定初始化顺序。
        这是验证意图是否可执行的关键步骤。

        Returns:
            List[str]: 排序后的节点列表（初始化顺序）。

        Raises:
            DependencyGraphError: 如果存在循环依赖。
        """
        if not self.graph:
            return []

        in_degree = {node: 0 for node in self.graph}
        
        # 计算入度
        for u in self.graph:
            for v in self.graph[u]:
                in_degree[v] += 1

        # 使用队列处理入度为0的节点
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        sorted_order = []

        while queue:
            u = queue.popleft()
            sorted_order.append(u)

            for v in self.graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        # 验证是否存在环
        if len(sorted_order) != len(self.graph):
            logger.error("检测到循环依赖！意图结构存在逻辑冲突。")
            raise DependencyGraphError("意图拓扑映射失败：存在循环依赖，无法确定初始化顺序。")

        # 反转列表，因为我们要的是"被依赖者优先初始化"
        # (u, v) 表示 u 依赖 v，所以 v 应该在 u 前面。
        # 标准拓扑排序输出的是从源到汇，这里我们需要从汇到源（基础依赖先加载）
        # 实际上，根据入度算法，先出来的也是没有入度的点（即没有依赖别人的点，或者说是基础点）。
        # 让我们重新检查逻辑：
        # u -> v: u depends on v.
        # Adj list: u: [v]
        # In-degree: v has in-degree from u. u has 0.
        # Queue: [u]. Pop u. Result [u]. Dec v. 
        # Result [u, v].
        # 这意味着 u (依赖于别人) 先出来？不对。
        # 修正：如果 u -> v 表示 u 依赖 v，那么 v 必须先于 u 初始化。
        # 标准拓扑排序：u -> v 意味着 u 在 v 之前。
        # 所以我们的图定义和排序结果需要对应。
        # 如果定义 (u, v) 为 u 依赖 v，则在图中 u -> v。
        # 拓扑排序结果 [u, v] 意味着先处理 u 再处理 v。
        # 但初始化逻辑要求先处理 v 再处理 u。
        # 因此，我们需要返回 reversed(sorted_order)。
        
        initialization_order = list(reversed(sorted_order))
        logger.info(f"计算出的系统初始化顺序: {initialization_order}")
        return initialization_order

    def validate_structure(self) -> bool:
        """
        验证图的完整性。
        """
        if not self.graph:
            return False
        return True


def map_intent_to_topology(intent_text: str) -> Optional[Dict[str, List[str]]]:
    """
    核心功能函数：将模糊意图映射为结构化的拓扑数据。

    Args:
        intent_text (str): 输入的意图字符串。

    Returns:
        Optional[Dict[str, List[str]]]: 包含 'nodes' 和 'initialization_order' 的字典，
                                         如果验证失败则返回 None。
    
    Example:
        >>> intent = "构建一个使用数据库和缓存的API服务"
        >>> result = map_intent_to_topology(intent)
        >>> print(result['initialization_order'])
        # 预期输出应包含 Config, DB, Cache, API 等顺序
    """
    logger.info(f"开始处理意图: {intent_text}")
    
    try:
        # 阶段 1: 解析意图
        parser = IntentParser()
        nodes, deps = parser.parse_intent(intent_text)
        
        if not nodes:
            logger.warning("未能从意图中识别出有效功能节点。")
            return None

        # 阶段 2: 构建拓扑图
        mapper = TopologyMapper()
        mapper.build_graph(nodes, deps)
        
        # 阶段 3: 验证与排序
        if not mapper.validate_structure():
            return None
            
        init_order = mapper.topological_sort()
        
        return {
            "raw_nodes": list(nodes),
            "dependencies": [f"{u} -> {v}" for u, v in deps],
            "initialization_order": init_order
        }

    except DependencyGraphError as dge:
        logger.error(f"拓扑映射错误: {dge}")
        return None
    except Exception as e:
        logger.exception(f"处理过程中发生未预期错误: {e}")
        return None


# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    # 示例 1: 一个合理的系统架构意图
    user_intent_1 = "我需要开发一个高并发的API服务，它包含用户认证模块，并且必须连接到数据库和缓存系统。"
    
    print("-" * 30)
    print(f"输入意图: {user_intent_1}")
    result_1 = map_intent_to_topology(user_intent_1)
    
    if result_1:
        print("\n[系统识别结果]")
        print(f"识别节点: {result_1['raw_nodes']}")
        print(f"依赖关系: {result_1['dependencies']}")
        print(f"推荐初始化顺序: {result_1['initialization_order']}")
    
    # 示例 2: 模拟一个包含冲突的意图 (这里通过硬编码模拟，实际解析器可能识别不出)
    # 为了演示错误处理，我们直接构造一个循环依赖
    print("-" * 30)
    print("模拟循环依赖测试...")
    try:
        faulty_mapper = TopologyMapper()
        # 手动构建一个环 A->B, B->A
        # 注意：正常 IntentParser 很难产生这种矛盾，除非意图本身就是逻辑混乱的
        faulty_mapper.build_graph({"A", "B"}, [("A", "B"), ("B", "A")])
        print(f"尝试排序循环依赖图...")
        faulty_mapper.topological_sort()
    except DependencyGraphError as e:
        print(f"成功捕获预期错误: {e}")

    # 示例 3: 边界检查 - 空输入
    print("-" * 30)
    map_intent_to_topology("")