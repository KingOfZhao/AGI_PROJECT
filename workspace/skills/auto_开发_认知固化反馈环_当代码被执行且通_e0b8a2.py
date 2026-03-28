"""
模块: cognitive_solidification_feedback_loop
描述: 实现AGI架构中的认知固化机制。当代码通过测试后，该模块负责将其抽象为
      通用技能节点，提取特征标签，并将其融合进现有的知识图谱中，实现系统能力的持续积累。
作者: AGI System Architect
版本: 1.0.0
"""

import logging
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, TypedDict, Union
from dataclasses import dataclass, field, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveSolidification")

# --- 数据结构定义 ---

class ExecutionReport(TypedDict):
    """代码执行报告的数据结构"""
    code_snippet: str
    test_passed: bool
    execution_time_ms: float
    input_examples: List[Dict[str, Any]]
    output_examples: List[Dict[str, Any]]
    context_tags: List[str]

@dataclass
class SkillNode:
    """
    技能节点数据结构
    代表知识图谱中的一个固化技能或知识点
    """
    node_id: str
    name: str
    description: str
    abstracted_logic: str  # 抽象后的逻辑描述或伪代码
    source_code_hash: str  # 原始代码的哈希，用于去重
    tags: Set[str]
    integration_score: float = 0.0  # 与现有网络的融合度
    creation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为可序列化的字典"""
        return {
            **asdict(self),
            'tags': list(self.tags)
        }

# --- 核心类 ---

class KnowledgeGraphManager:
    """
    知识图谱管理器（模拟）
    负责存储和检索技能节点，计算节点间的关联
    """
    def __init__(self):
        self._nodes: Dict[str, SkillNode] = {}
        self._edges: Dict[str, List[str]] = {} # node_id -> [related_node_ids]

    def find_similar_node(self, tags: Set[str], logic_signature: str) -> Optional[SkillNode]:
        """
        在图谱中查找是否存在相似逻辑的节点
        """
        for node in self._nodes.values():
            # 简单的相似度检查：标签交集或逻辑签名匹配
            if node.source_code_hash == logic_signature:
                return node
            if len(node.tags.intersection(tags)) > 2: # 至少有3个共同标签
                return node
        return None

    def merge_node(self, node: SkillNode) -> bool:
        """
        将新节点合并入图谱
        """
        if node.node_id in self._nodes:
            logger.warning(f"Node {node.node_id} already exists. Updating edges only.")
            return False
        
        self._nodes[node.node_id] = node
        self._edges[node.node_id] = []
        
        # 简化的融合逻辑：基于标签连接相关节点
        for existing_id, existing_node in self._nodes.items():
            if existing_id != node.node_id:
                common_tags = existing_node.tags.intersection(node.tags)
                if common_tags:
                    self._edges[node.node_id].append(existing_id)
                    self._edges[existing_id].append(node.node_id)
                    logger.info(f"Created edge between {node.node_id} and {existing_id} based on tags: {common_tags}")
        
        return True

class CognitiveSolidificationLoop:
    """
    认知固化反馈环主类
    处理从执行成功的代码到知识图谱节点的转化过程
    """

    def __init__(self, graph_manager: KnowledgeGraphManager):
        self.graph = graph_manager
        logger.info("Cognitive Solidification Loop Initialized")

    def _extract_abstraction(self, code: str, execution_data: ExecutionReport) -> str:
        """
        辅助函数：从具体代码中提取抽象逻辑模式
        实际AGI场景中会使用LLM或静态分析
        """
        # 模拟抽象过程：移除特定变量名，提取函数结构
        # 这里仅作演示，返回一个简化的结构描述
        func_defs = re.findall(r"def (\w+)\(", code)
        imports = re.findall(r"import (\w+)", code)
        
        abstraction = f"Functionality involves modules: {', '.join(imports)}. "
        abstraction += f"Key operations defined in: {', '.join(func_defs)}. "
        abstraction += f"Input-Output pattern detected: {type(execution_data['input_examples'][0]).__name__} -> {type(execution_data['output_examples'][0]).__name__}"
        
        return abstraction

    def _generate_tags(self, code: str, context: List[str]) -> Set[str]:
        """
        辅助函数：生成用于检索和分类的标签
        """
        base_tags = set(context)
        # 简单的关键词提取作为标签
        keywords = re.findall(r'\b(python|data|process|api|calculate|file|network)\b', code, re.IGNORECASE)
        base_tags.update(k.lower() for k in keywords)
        return base_tags

    def process_execution_feedback(self, report: ExecutionReport) -> Optional[SkillNode]:
        """
        核心函数：处理执行反馈，生成并融合技能节点
        
        Args:
            report (ExecutionReport): 包含代码、测试结果和上下文的报告
            
        Returns:
            Optional[SkillNode]: 如果固化成功，返回新的技能节点，否则返回None
        """
        # 1. 数据验证
        if not report.get('test_passed'):
            logger.error("Solidification rejected: Tests did not pass.")
            return None
        
        if not report.get('code_snippet'):
            logger.error("Solidification rejected: Empty code snippet.")
            return None

        try:
            code = report['code_snippet']
            code_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()
            
            # 2. 抽象化
            logger.info("Step 1: Abstracting logic from code...")
            abstract_logic = self._extract_abstraction(code, report)
            
            # 3. 标签化
            logger.info("Step 2: Generating semantic tags...")
            tags = self._generate_tags(code, report.get('context_tags', []))
            
            # 4. 节点生成
            node_name = f"Skill_{code_hash[:8]}"
            new_node = SkillNode(
                node_id=f"node_{datetime.now().timestamp()}",
                name=node_name,
                description=f"Auto-generated skill from execution context: {report.get('context_tags', ['general'])}",
                abstracted_logic=abstract_logic,
                source_code_hash=code_hash,
                tags=tags
            )
            
            # 5. 去重检查与融合
            logger.info("Step 3: Checking knowledge graph for duplicates...")
            existing_node = self.graph.find_similar_node(tags, code_hash)
            
            if existing_node:
                logger.info(f"Similar node found: {existing_node.node_id}. Reinforcing existing connection instead of creating new.")
                # 这里可以增加现有节点的权重，略过创建
                return existing_node
            
            # 6. 合并入图谱
            logger.info("Step 4: Merging new node into knowledge graph...")
            success = self.graph.merge_node(new_node)
            
            if success:
                logger.info(f"SUCCESS: New skill node {new_node.node_id} solidified.")
                return new_node
            else:
                return None

        except KeyError as e:
            logger.error(f"Invalid report format: missing key {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during solidification: {e}")
            return None

# --- 使用示例与测试 ---

def run_demo():
    """
    运行认知固化反馈环的演示
    """
    # 初始化系统
    kg_manager = KnowledgeGraphManager()
    solidifier = CognitiveSolidificationLoop(kg_manager)

    # 模拟输入数据：一段处理JSON数据的代码
    sample_code = """
import json

def process_user_data(data):
    '''处理用户数据并计算年龄'''
    if not data:
        return None
    user = json.loads(data)
    age = user.get('age', 0)
    return age * 2
"""

    execution_report_success: ExecutionReport = {
        "code_snippet": sample_code,
        "test_passed": True,
        "execution_time_ms": 45.2,
        "input_examples": [{'data': '{"age": 10}'}],
        "output_examples": [20],
        "context_tags": ["data_processing", "json", "user_module"]
    }

    # 执行固化
    print("--- Processing Successful Execution ---")
    new_skill = solidifier.process_execution_feedback(execution_report_success)

    if new_skill:
        print(f"New Skill Created: {new_skill.name}")
        print(f"Tags: {new_skill.tags}")
        print(f"Abstraction: {new_skill.abstracted_logic}")
    
    # 尝试再次提交相同代码（去重测试）
    print("\n--- Processing Duplicate Execution ---")
    duplicate_skill = solidifier.process_execution_feedback(execution_report_success)
    if duplicate_skill:
        print(f"Returned existing node: {duplicate_skill.node_id}")

    # 模拟失败的执行
    print("\n--- Processing Failed Execution ---")
    fail_report = execution_report_success.copy()
    fail_report['test_passed'] = False
    result = solidifier.process_execution_feedback(fail_report)
    print(f"Result of failed execution processing: {result}")

if __name__ == "__main__":
    run_demo()