"""
高级技能模块：基于语义依存关系的动态提示词工程

该模块实现了一个动态提示词工程系统，旨在通过分析中间表示的语义依存关系，
动态构建上下文窗口。系统利用本地向量数据库从2368个已有技能节点中检索
最相关的Few-shot示例，以优化AGI系统的代码生成质量。

核心功能：
1. 基于语义依存关系的上下文分析。
2. 动态检索相关技能示例。
3. 上下文敏感度影响的量化验证。

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === 数据结构定义 ===

class DependencyType(Enum):
    """语义依存关系类型枚举"""
    CONTROL_FLOW = "control_flow"
    DATA_TRANSFORMATION = "data_transformation"
    API_CALL = "api_call"
    ERROR_HANDLING = "error_handling"

@dataclass
class IRNode:
    """中间表示(IR)节点结构"""
    id: str
    content: str
    dependencies: List[str]  # 依赖的其他节点ID
    dep_type: DependencyType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SkillExample:
    """技能节点示例结构"""
    id: str
    code_snippet: str
    description: str
    embedding: List[float] = field(default_factory=list)

@dataclass
class PromptContext:
    """生成的提示词上下文"""
    system_instruction: str
    few_shot_blocks: List[str]
    current_task: str
    total_tokens: int = 0

# === 核心类定义 ===

class SemanticDependencyAnalyzer:
    """
    语义依存分析器
    负责解析IR结构并确定上下文构建的策略。
    """
    
    def __init__(self, sensitivity_threshold: float = 0.75):
        """
        初始化分析器
        
        Args:
            sensitivity_threshold (float): 上下文敏感度阈值，用于过滤低相关性的依赖
        """
        self.sensitivity_threshold = sensitivity_threshold
        logger.info(f"SemanticDependencyAnalyzer initialized with threshold {sensitivity_threshold}")

    def extract_context_seeds(self, ir_nodes: List[IRNode]) -> List[Dict[str, Any]]:
        """
        从IR节点列表中提取上下文种子。
        
        Args:
            ir_nodes (List[IRNode]): 输入的中间表示节点列表
            
        Returns:
            List[Dict[str, Any]]: 提取的上下文种子，包含文本和权重
            
        Raises:
            ValueError: 如果输入节点列表为空
        """
        if not ir_nodes:
            logger.error("Input IR nodes list is empty")
            raise ValueError("IR nodes list cannot be empty")

        seeds = []
        for node in ir_nodes:
            # 简化的敏感度计算逻辑：基于依赖数量和类型
            # 实际场景中应接入图神经网络或复杂启发式算法
            base_weight = 1.0
            if node.dep_type == DependencyType.CONTROL_FLOW:
                base_weight = 1.5  # 控制流通常对代码结构影响更大
            
            sensitivity_score = min(1.0, base_weight * (1 + len(node.dependencies) * 0.1))
            
            if sensitivity_score >= self.sensitivity_threshold:
                seed = {
                    "text": node.content,
                    "weight": sensitivity_score,
                    "type": node.dep_type.value,
                    "node_id": node.id
                }
                seeds.append(seed)
                logger.debug(f"Extracted seed from node {node.id} with score {sensitivity_score}")
        
        logger.info(f"Extracted {len(seeds)} high-sensitivity context seeds")
        return seeds

class DynamicPromptEngineer:
    """
    动态提示词工程核心引擎
    负责检索Few-shot示例并组装最终的Prompt。
    """
    
    def __init__(self, vector_db_client: Any):
        """
        初始化引擎
        
        Args:
            vector_db_client (Any): 模拟的向量数据库客户端
        """
        self.db = vector_db_client

    def construct_dynamic_prompt(
        self, 
        ir_nodes: List[IRNode], 
        analyzer: SemanticDependencyAnalyzer,
        max_context_tokens: int = 4000
    ) -> PromptContext:
        """
        构建基于语义依存关系的动态提示词。
        
        Args:
            ir_nodes (List[IRNode]): 当前的IR节点
            analyzer (SemanticDependencyAnalyzer): 分析器实例
            max_context_tokens (int): 最大上下文窗口限制
            
        Returns:
            PromptContext: 构建好的提示词上下文对象
        """
        logger.info("Starting dynamic prompt construction...")
        
        # 1. 分析语义依存关系，提取关键上下文种子
        try:
            context_seeds = analyzer.extract_context_seeds(ir_nodes)
        except ValueError as e:
            logger.warning(f"Failed to extract seeds: {e}. Using fallback strategy.")
            context_seeds = [{"text": "generic coding task", "weight": 0.5, "type": "generic"}]

        # 2. 基于种子检索Few-shot示例
        # 将所有种子文本合并为查询向量（此处简化为字符串拼接，实际需Embedding）
        combined_query = " ".join([s['text'] for s in context_seeds])
        relevant_skills = self._retrieve_relevant_skills(combined_query)
        
        # 3. 动态组装Prompt
        few_shot_blocks = []
        current_tokens = 0
        
        # 系统指令部分
        system_instruction = (
            "You are an expert Python Code Generation Agent. "
            "Generate code that strictly adheres to the semantic dependencies provided."
        )
        current_tokens += len(system_instruction.split())

        # 动态注入Few-shot示例，直到达到Token限制
        for skill in relevant_skills:
            skill_content = f"### Example: {skill.description}\n