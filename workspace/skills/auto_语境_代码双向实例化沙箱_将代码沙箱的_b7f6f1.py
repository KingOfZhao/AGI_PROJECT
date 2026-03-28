"""
高级Python模块：语境-代码双向实例化沙箱

该模块实现了一个创新的执行环境，旨在消除“自然语言对话”与“编程代码运行时”之间的鸿沟。
核心机制包括：
1. 实体固化：将代码执行结果（如变量、对象句柄）转化为对话语境中的可指代实体。
2. 语境锚定：解析用户意图，定位到沙箱内存中的具体变量，并执行修改操作。

模块名: auto_语境_代码双向实例化沙箱_将代码沙箱的_b7f6f1
"""

import logging
import inspect
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from uuid import uuid4
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ContextNode:
    """
    语境节点类。
    代表对话中的一个实体，它映射到沙箱内存中的一个具体对象。
    """
    node_id: str
    variable_name: str
    object_type: str
    description: str
    memory_ref: Any  # 实际对象的引用
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """将节点信息序列化为字典（不含不可序列化的对象引用）"""
        return {
            "node_id": self.node_id,
            "variable_name": self.variable_name,
            "object_type": self.object_type,
            "description": self.description,
            "metadata": self.metadata
        }

class BiDirectionalSandbox:
    """
    双向实例化沙箱类。
    提供代码执行环境，并维护“变量名 -> 语境节点”的映射关系。
    """
    
    def __init__(self):
        # 沙箱的全局命名空间，用于 exec 执行
        self._global_namespace: Dict[str, Any] = {}
        # 语境映射表：node_id -> ContextNode
        self._context_graph: Dict[str, ContextNode] = {}
        # 反向索引：variable_name -> node_id (用于快速查找变量对应的节点)
        self._var_to_node_map: Dict[str, str] = {}
        
        logger.info("双向实例化沙箱已初始化。")

    def _validate_code(self, code: str) -> bool:
        """
        辅助函数：简单的代码安全静态检查。
        防止导入危险模块或直接破坏沙箱结构。
        """
        forbidden_patterns = [
            r"import\s+os", 
            r"import\s+subprocess", 
            r"import\s+sys",
            r"__import__",
            r"eval\s*\(",
            r"exec\s*\("
        ]
        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                logger.error(f"代码包含禁止的模式: {pattern}")
                raise ValueError(f"安全违规：代码包含禁止的模式 {pattern}")
        return True

    def execute_and_solidify(self, code: str, intent_description: str = "") -> Dict[str, Any]:
        """
        核心函数1：执行代码并将结果固化为语境节点。
        
        Args:
            code (str): 要执行的Python代码片段。
            intent_description (str): 代码意图的自然语言描述，用于生成节点描述。
            
        Returns:
            Dict[str, Any]: 包含执行状态、文本输出和生成的语境节点信息的字典。
        """
        try:
            self._validate_code(code)
            logger.info(f"正在执行代码: {code[:50]}...")
            
            # 使用 exec 在隔离的命名空间中执行
            # 注意：实际生产环境应使用 Docker 或 RestrictedPython 进行更强隔离
            local_namespace = {}
            exec(code, self._global_namespace, local_namespace)
            
            # 更新持久化的全局命名空间
            self._global_namespace.update(local_namespace)
            
            created_nodes = []
            
            # 遍历新创建的变量，将其转化为 ContextNode
            for var_name, obj in local_namespace.items():
                if var_name.startswith("_"):
                    continue
                
                # 只有当变量不是已存在的节点时才创建新节点，或者更新它
                node_id = self._var_to_node_map.get(var_name)
                
                if not node_id:
                    node_id = f"node_{uuid4().hex[:8]}"
                
                # 获取对象类型和简要描述
                obj_type = type(obj).__name__
                # 尝试生成对象的简短描述
                obj_desc = f"{obj_type} object: {str(obj)[:50]}..."
                
                node = ContextNode(
                    node_id=node_id,
                    variable_name=var_name,
                    object_type=obj_type,
                    description=intent_description or f"Created via code execution",
                    memory_ref=obj,
                    metadata={"created_at": str(uuid4().time)}
                )
                
                self._context_graph[node_id] = node
                self._var_to_node_map[var_name] = node_id
                created_nodes.append(node.to_dict())
                logger.info(f"固化实体: 变量 '{var_name}' 映射为节点 '{node_id}'")

            return {
                "status": "success",
                "message": "代码执行成功，实体已固化。",
                "nodes_created": created_nodes,
                "stdout": str(local_namespace) # 简化的输出
            }
            
        except Exception as e:
            logger.error(f"代码执行失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "nodes_created": []
            }

    def anchor_and_modify(self, target_reference: str, modification_code_template: str) -> Dict[str, Any]:
        """
        核心函数2：语境锚定与修改。
        根据对话中的引用（如变量名或节点ID），定位内存对象并执行修改。
        
        Args:
            target_reference (str): 目标引用，可以是变量名或节点ID。
            modification_code_template (str): 包含修改逻辑的代码字符串。
                                              使用 {target} 作为占位符代表目标对象。
                                              
        Returns:
            Dict[str, Any]: 修改操作的结果。
        """
        target_node: Optional[ContextNode] = None
        
        # 1. 锚定过程：尝试通过 Node ID 或 变量名 查找对象
        if target_reference in self._context_graph:
            target_node = self._context_graph[target_reference]
        elif target_reference in self._var_to_node_map:
            node_id = self._var_to_node_map[target_reference]
            target_node = self._context_graph[node_id]
        
        if not target_node:
            logger.warning(f"语境锚定失败：无法找到引用 '{target_reference}'")
            return {
                "status": "anchor_failed",
                "message": f"在当前语境中找不到实体: {target_reference}"
            }
            
        logger.info(f"语境锚定成功：定位到节点 {target_node.node_id} ({target_node.variable_name})")
        
        try:
            # 2. 实例化过程：生成具体的操作指令
            # 将代码模板中的占位符替换为实际的变量名
            var_name = target_node.variable_name
            
            # 安全检查：确保变量名是有效的标识符
            if not var_name.isidentifier():
                 raise ValueError(f"Invalid variable name: {var_name}")

            # 构建可执行代码
            # 注意：这里假设 modification_code_template 类似于 "{target}.update({'color': 'red'})"
            # 或者是 "del {target}"
            executable_code = modification_code_template.replace("{target}", var_name)
            
            logger.info(f"生成操作指令: {executable_code}")
            
            # 执行修改
            # 修改操作是在同一个全局命名空间中进行的，因此会直接改变对象状态
            exec(executable_code, self._global_namespace, {})
            
            # 更新节点元数据以反映修改
            target_node.metadata['last_modified'] = str(uuid4().time)
            
            return {
                "status": "success",
                "message": f"实体 {var_name} 已成功修改。",
                "node_id": target_node.node_id,
                "executed_code": executable_code
            }
            
        except Exception as e:
            logger.error(f"修改实体失败: {str(e)}")
            return {
                "status": "execution_error",
                "message": str(e)
            }

    def get_context_snapshot(self) -> List[Dict]:
        """辅助函数：获取当前语境中所有实体的快照"""
        return [node.to_dict() for node in self._context_graph.values()]

# 演示与使用示例
if __name__ == "__main__":
    # 初始化沙箱
    sandbox = BiDirectionalSandbox()
    
    print("-" * 50)
    print("步骤 1: AI 生成代码创建数据结构")
    # 模拟：AI生成了一段代码，创建了一个包含颜色的配置字典
    code_part1 = """
config = {
    "theme": "dark",
    "color": "blue",
    "user": "admin"
}
"""
    result1 = sandbox.execute_and_solidify(code_part1, "创建初始配置")
    print(f"执行结果: {result1['status']}")
    print(f"创建的节点: {result1['nodes_created']}")
    
    # 获取生成的变量名（模拟语境识别）
    created_var_name = result1['nodes_created'][0]['variable_name']
    
    print("-" * 50)
    print("步骤 2: 用户对话指令 '把它变红'")
    # 模拟：系统解析用户意图，生成针对该对象的修改代码模板
    # 意图解析：Target=config, Action=change color to red
    modification_template = "{target}['color'] = 'red'"
    
    result2 = sandbox.anchor_and_modify(created_var_name, modification_template)
    print(f"修改结果: {result2['status']}")
    
    print("-" * 50)
    print("步骤 3: 验证沙箱内存中的对象状态")
    # 访问沙箱内部命名空间验证更改
    current_config = sandbox._global_namespace.get('config')
    print(f"当前内存中的配置对象: {current_config}")
    assert current_config['color'] == 'red', "测试失败：对象未更新"
    print("验证通过：对话成功修改了代码内存对象。")