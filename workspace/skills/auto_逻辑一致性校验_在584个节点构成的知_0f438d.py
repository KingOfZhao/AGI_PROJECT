"""
逻辑一致性校验模块

该模块用于在知识图谱中检测逻辑一致性问题，特别是属性变更的传播验证。
通过构建依赖链并修改根节点属性，验证变更是否能正确传播至叶节点。

功能:
- 从知识图谱中随机抽取依赖链
- 修改根节点属性并验证传播效果
- 检测逻辑断层和不一致
- 生成详细的校验报告

使用示例:
>>> validator = LogicConsistencyValidator(graph_data)
>>> results = validator.validate_propagation(chain_length=3, modification="increase")
>>> print(results["is_consistent"])
False
"""

import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logic_consistency_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """知识图谱节点数据结构"""
    node_id: str
    node_type: str
    properties: Dict[str, Any]
    dependencies: List[str]  # 依赖的其他节点ID列表


@dataclass
class ValidationResult:
    """校验结果数据结构"""
    chain_id: str
    is_consistent: bool
    propagation_depth: int
    break_points: List[str]
    details: Dict[str, Any]


class LogicConsistencyValidator:
    """知识图谱逻辑一致性校验器"""
    
    def __init__(self, graph_data: Dict[str, GraphNode]):
        """
        初始化校验器
        
        Args:
            graph_data: 知识图谱数据，节点ID到节点的映射
        """
        self.graph_data = graph_data
        self._validate_graph()
        
    def _validate_graph(self) -> None:
        """验证知识图谱数据结构"""
        if not isinstance(self.graph_data, dict):
            raise ValueError("Graph data must be a dictionary")
            
        if len(self.graph_data) < 3:
            raise ValueError("Graph must contain at least 3 nodes for dependency chain")
            
        for node_id, node in self.graph_data.items():
            if not isinstance(node, GraphNode):
                raise ValueError(f"Node {node_id} must be a GraphNode instance")
                
            if node_id != node.node_id:
                raise ValueError(f"Node ID mismatch: {node_id} vs {node.node_id}")
    
    def _find_random_chain(self, chain_length: int = 3) -> Optional[List[str]]:
        """
        查找随机依赖链
        
        Args:
            chain_length: 期望的链条长度
            
        Returns:
            节点ID列表，表示从根到叶的依赖链，或None如果未找到
        """
        logger.info(f"Searching for random chain with length {chain_length}")
        
        # 找出所有可能的起始节点（没有依赖或依赖较少的节点）
        potential_roots = [
            node_id for node_id, node in self.graph_data.items()
            if len(node.dependencies) <= 1
        ]
        
        if not potential_roots:
            logger.warning("No potential root nodes found in the graph")
            return None
            
        # 随机选择起始节点
        start_node = random.choice(potential_roots)
        chain = [start_node]
        visited = set([start_node])
        
        # 递归查找依赖链
        def _build_chain(current_node: str, depth: int) -> bool:
            if depth >= chain_length:
                return True
                
            # 获取当前节点的依赖
            dependencies = self.graph_data[current_node].dependencies
            valid_deps = [d for d in dependencies if d not in visited]
            
            if not valid_deps:
                return False
                
            # 随机选择一个依赖继续构建链条
            next_node = random.choice(valid_deps)
            chain.append(next_node)
            visited.add(next_node)
            
            return _build_chain(next_node, depth + 1)
        
        if _build_chain(start_node, 1):
            logger.info(f"Found chain: {' -> '.join(chain)}")
            return chain
        else:
            logger.warning("Could not build a chain of requested length")
            return None
    
    def modify_root_property(
        self, 
        root_id: str, 
        property_name: str, 
        modification: Any
    ) -> bool:
        """
        修改根节点属性
        
        Args:
            root_id: 根节点ID
            property_name: 要修改的属性名
            modification: 修改值或修改函数
            
        Returns:
            修改是否成功
        """
        logger.info(f"Modifying root node {root_id} property {property_name}")
        
        if root_id not in self.graph_data:
            logger.error(f"Node {root_id} not found in graph")
            return False
            
        node = self.graph_data[root_id]
        
        if property_name not in node.properties:
            logger.error(f"Property {property_name} not found in node {root_id}")
            return False
            
        try:
            if callable(modification):
                # 如果是函数，应用于当前值
                node.properties[property_name] = modification(
                    node.properties[property_name]
                )
            else:
                # 直接设置新值
                node.properties[property_name] = modification
                
            logger.info(f"Successfully modified {property_name} in node {root_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify property: {str(e)}")
            return False
    
    def validate_propagation(
        self,
        chain_length: int = 3,
        property_name: str = "value",
        modification: Any = lambda x: x * 1.1  # 默认增加10%
    ) -> ValidationResult:
        """
        验证属性变更传播
        
        Args:
            chain_length: 要测试的链条长度
            property_name: 要修改的属性名
            modification: 修改值或修改函数
            
        Returns:
            ValidationResult 包含校验结果和详细信息
        """
        logger.info("Starting propagation validation")
        
        # 1. 查找随机链条
        chain = self._find_random_chain(chain_length)
        if not chain:
            return ValidationResult(
                chain_id="",
                is_consistent=False,
                propagation_depth=0,
                break_points=[],
                details={"error": "Could not find valid chain"}
            )
            
        chain_id = "->".join(chain)
        root_id = chain[0]
        
        # 2. 修改根节点属性
        if not self.modify_root_property(root_id, property_name, modification):
            return ValidationResult(
                chain_id=chain_id,
                is_consistent=False,
                propagation_depth=0,
                break_points=[],
                details={"error": "Failed to modify root property"}
            )
            
        # 3. 验证传播
        propagation_depth = 0
        break_points = []
        expected_value = self.graph_data[root_id].properties[property_name]
        
        for i in range(1, len(chain)):
            current_node = self.graph_data[chain[i]]
            current_value = current_node.properties.get(property_name)
            
            # 检查属性是否存在
            if property_name not in current_node.properties:
                break_points.append(chain[i])
                logger.warning(f"Property {property_name} missing in node {chain[i]}")
                continue
                
            # 检查值是否一致（这里简化了实际一致性检查）
            # 实际应用中应根据业务规则实现更复杂的检查
            if not self._check_consistency(expected_value, current_value):
                break_points.append(chain[i])
                logger.warning(
                    f"Consistency break at node {chain[i]}: "
                    f"expected {expected_value}, got {current_value}"
                )
            else:
                propagation_depth += 1
                
        # 4. 返回结果
        is_consistent = len(break_points) == 0
        result = ValidationResult(
            chain_id=chain_id,
            is_consistent=is_consistent,
            propagation_depth=propagation_depth,
            break_points=break_points,
            details={
                "root_modification": str(modification),
                "property_name": property_name,
                "expected_value": str(expected_value)
            }
        )
        
        logger.info(
            f"Validation completed. Consistent: {is_consistent}, "
            f"Propagation depth: {propagation_depth}, "
            f"Break points: {break_points}"
        )
        
        return result
    
    def _check_consistency(self, expected: Any, actual: Any) -> bool:
        """
        检查值一致性（简化版）
        
        实际应用中应根据业务规则实现更复杂的检查逻辑
        """
        # 简单比较或根据业务规则扩展
        return str(expected) == str(actual)


def generate_sample_graph(node_count: int = 584) -> Dict[str, GraphNode]:
    """
    生成示例知识图谱
    
    Args:
        node_count: 要生成的节点数量
        
    Returns:
        节点ID到节点的映射字典
    """
    logger.info(f"Generating sample graph with {node_count} nodes")
    
    graph = {}
    node_types = ["Concept", "Property", "Relation", "Entity"]
    
    # 生成节点
    for i in range(node_count):
        node_id = f"node_{i}"
        node_type = random.choice(node_types)
        
        # 随机生成一些属性
        properties = {
            "value": random.uniform(1, 100),
            "weight": random.uniform(0.1, 1.0),
            "description": f"Sample {node_type} node {i}",
            "created_at": datetime.now().isoformat()
        }
        
        # 随机生成依赖关系（确保DAG）
        dependencies = []
        if i > 0:
            # 每个节点随机依赖1-3个前面的节点
            dep_count = min(random.randint(1, 3), i)
            dependencies = random.sample(
                [f"node_{j}" for j in range(i)],
                dep_count
            )
        
        graph[node_id] = GraphNode(
            node_id=node_id,
            node_type=node_type,
            properties=properties,
            dependencies=dependencies
        )
    
    logger.info("Sample graph generation completed")
    return graph


if __name__ == "__main__":
    # 示例用法
    try:
        # 1. 生成示例知识图谱
        sample_graph = generate_sample_graph(584)
        
        # 2. 初始化校验器
        validator = LogicConsistencyValidator(sample_graph)
        
        # 3. 执行校验
        result = validator.validate_propagation(
            chain_length=3,
            property_name="value",
            modification=lambda x: x * 1.5  # 增加50%
        )
        
        # 4. 打印结果
        print("\nValidation Result:")
        print(f"Chain: {result.chain_id}")
        print(f"Is Consistent: {result.is_consistent}")
        print(f"Propagation Depth: {result.propagation_depth}")
        print(f"Break Points: {result.break_points}")
        print(f"Details: {result.details}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)