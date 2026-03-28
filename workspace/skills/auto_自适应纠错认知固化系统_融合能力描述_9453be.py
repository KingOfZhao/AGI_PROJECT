"""
自适应纠错认知固化系统

该模块实现了一个能够将运行时错误转化为认知层面知识的高级系统。
它不仅处理代码回滚，还分析错误根源，并将失败经验固化为知识节点，
使AI系统能够从错误中学习，避免重复犯错。

Author: AGI System Core Team
Version: 2.0.0
Domain: cross_domain
"""

import json
import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误类别枚举，定义认知层面的错误根源"""
    LOGIC_FLAW = "logic_flaw"           # 逻辑缺陷：算法或业务逻辑错误
    ENV_MISSING = "environment_missing"  # 环境缺失：依赖、库或资源不可用
    INTENT_MISMATCH = "intent_mismatch" # 意图误解：对任务目标的错误理解
    INPUT_INVALID = "input_invalid"     # 输入无效：边界检查失败或数据格式错误
    UNKNOWN = "unknown"                 # 未知错误


class CorrectionAction(Enum):
    """修正动作枚举"""
    ROLLBACK = "rollback"       # 回滚代码
    RETRY_MODIFIED = "retry"    # 修改参数重试
    ASK_HUMAN = "ask_human"     # 请求人工介入
    SKIP_TASK = "skip_task"     # 跳过当前任务


@dataclass
class FailureNode:
    """
    负向真实节点：代表一次失败的执行尝试及其认知分析结果。
    
    Attributes:
        node_id (str): 唯一标识符。
        task_signature (str): 任务特征签名，用于匹配相似任务。
        error_type (str): 原始错误类型。
        error_message (str): 原始错误信息。
        category (ErrorCategory): 归因类别。
        root_cause_analysis (str): AI生成的根本原因分析。
        timestamp (str): 创建时间。
        correction_strategy (Dict): 建议的修正策略。
    """
    node_id: str
    task_signature: str
    error_type: str
    error_message: str
    category: ErrorCategory
    root_cause_analysis: str
    timestamp: str
    correction_strategy: Dict[str, Any]


class KnowledgeBase:
    """
    模拟知识库接口，用于存储和检索认知节点。
    在生产环境中应替换为向量数据库（如Milvus, Pinecone）或图数据库。
    """
    def __init__(self):
        self._storage: Dict[str, FailureNode] = {}

    def store(self, node: FailureNode) -> bool:
        """存储节点"""
        try:
            self._storage[node.node_id] = node
            logger.info(f"Knowledge Node stored: {node.node_id}")
            return True
        except Exception as e:
            logger.error(f"Storage failed: {e}")
            return False

    def query_similar(self, task_signature: str, threshold: float = 0.8) -> Optional[FailureNode]:
        """
        查询相似的历史失败记录。
        这里简化为前缀匹配，实际应用应使用语义相似度搜索。
        """
        for key, node in self._storage.items():
            # 简单的相似度模拟：检查任务签名是否有重叠
            if node.task_signature in task_signature or task_signature in node.task_signature:
                return node
        return None


class AdaptiveErrorCognitiveSystem:
    """
    自适应纠错认知固化系统。
    
    负责协调错误捕获、认知分析、知识固化和未来决策建议。
    
    Input Format:
        - error_info: Dict (包含 'type', 'message', 'code_context', 'task_desc')
        - sandbox_state: Dict (沙箱环境状态)
    
    Output Format:
        - result: Dict (包含 'success', 'action', 'analysis', 'knowledge_id')
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        初始化系统。
        
        Args:
            knowledge_base (Optional[KnowledgeBase]): 注入的知识库实例。
        """
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.version = "9453be"

    def _generate_signature(self, task_desc: str, code_context: str) -> str:
        """
        辅助函数：生成任务特征签名。
        用于唯一标识一类任务，以便将来复用经验。
        
        Args:
            task_desc (str): 任务描述文本。
            code_context (str): 相关代码片段。
            
        Returns:
            str: SHA256哈希签名。
        """
        raw_data = f"{task_desc}::{code_context}"
        return hashlib.sha256(raw_data.encode('utf-8')).hexdigest()[:16]

    def _analyze_root_cause(self, error_type: str, error_msg: str, code_context: str) -> Tuple[ErrorCategory, str]:
        """
        核心函数：分析错误的根本原因。
        
        使用规则引擎模拟认知模型的分析过程。在AGI场景下，这里应调用LLM进行深度推理。
        
        Args:
            error_type (str): 异常类型。
            error_msg (str): 异常详细信息。
            code_context (str): 出错时的代码上下文。
            
        Returns:
            Tuple[ErrorCategory, str]: (错误类别, 详细分析文本)
        """
        analysis = ""
        category = ErrorCategory.UNKNOWN
        
        try:
            # 规则1：环境缺失检测
            if "ModuleNotFoundError" in error_type or "ImportError" in error_type:
                category = ErrorCategory.ENV_MISSING
                missing_lib = re.search(r"No module named '(\S+)'", error_msg)
                lib_name = missing_lib.group(1) if missing_lib else "unknown"
                analysis = (f"Detected missing dependency: {lib_name}. "
                            f"The current sandbox environment lacks this library.")
                return category, analysis

            # 规则2：逻辑缺陷检测 (例如：空指针，除以零)
            if "ZeroDivisionError" in error_type or "NullPointerException" in error_type:
                category = ErrorCategory.LOGIC_FLAW
                analysis = ("Logical edge case not handled. "
                            "Code attempted an invalid operation on data states.")
                return category, analysis

            # 规则3：意图误解检测 (例如：KeyError 往往意味着数据结构与预期不符)
            if "KeyError" in error_type or "AttributeError" in error_type:
                category = ErrorCategory.INTENT_MISMATCH
                analysis = ("Data structure mismatch. The code expects a specific structure "
                            "that differs from the actual runtime data.")
                return category, analysis

            # 默认情况
            analysis = f"Unclassified error encountered: {error_msg}"
            return category, analysis

        except Exception as e:
            logger.error(f"Error during root cause analysis: {e}")
            return ErrorCategory.UNKNOWN, "Analysis failed due to internal error."

    def consult_past_failures(self, current_task_desc: str) -> Optional[Dict]:
        """
        核心函数：在执行前咨询过去的失败经验。
        
        Args:
            current_task_desc (str): 当前任务描述。
            
        Returns:
            Optional[Dict]: 如果找到相关的失败记录，返回建议的修正策略；否则返回None。
        """
        logger.info("Consulting cognitive memory for past failures...")
        # 使用任务描述作为模糊查询键
        past_node = self.knowledge_base.query_similar(current_task_desc)
        
        if past_node:
            logger.warning(f"Recalled similar failure scenario: ID {past_node.node_id}")
            return {
                "warning": "Similar task failed previously.",
                "root_cause": past_node.root_cause_analysis,
                "suggested_strategy": past_node.correction_strategy,
                "memory_id": past_node.node_id
            }
        return None

    def process_execution_failure(
        self,
        error_info: Dict[str, str],
        task_desc: str,
        sandbox_state: Dict
    ) -> Dict[str, Any]:
        """
        处理执行失败：分析、固化并决策。
        
        这是系统的主要入口点，当沙箱捕获异常时调用。
        
        Args:
            error_info (Dict): 包含 'type', 'message', 'code' 的字典。
            task_desc (str): 任务的自然语言描述。
            sandbox_state (Dict): 沙箱环境的状态快照。
            
        Returns:
            Dict[str, Any]: 包含处理结果和建议动作的字典。
            
        Raises:
            ValueError: 如果输入数据缺少必要字段。
        """
        # 1. 数据验证
        if not all(k in error_info for k in ['type', 'message', 'code']):
            logger.error("Invalid input: error_info missing required fields.")
            raise ValueError("error_info must contain 'type', 'message', and 'code'")

        logger.info(f"Processing failure for task: {task_desc[:50]}...")
        
        error_type = error_info.get('type')
        error_msg = error_info.get('message')
        code_context = error_info.get('code')
        
        # 2. 认知分析
        category, analysis = self._analyze_root_cause(error_type, error_msg, code_context)
        logger.info(f"Root cause categorized as: {category.value}")
        
        # 3. 生成修正策略
        strategy = self._determine_correction_strategy(category, sandbox_state)
        
        # 4. 认知固化
        signature = self._generate_signature(task_desc, code_context)
        node_id = f"fail_{datetime.now().strftime('%Y%m%d%H%M%S')}_{signature[:8]}"
        
        failure_node = FailureNode(
            node_id=node_id,
            task_signature=signature,
            error_type=error_type,
            error_message=error_msg,
            category=category,
            root_cause_analysis=analysis,
            timestamp=datetime.now().isoformat(),
            correction_strategy=strategy
        )
        
        persist_success = self.knowledge_base.store(failure_node)
        
        # 5. 生成最终响应
        response = {
            "status": "analyzed_and_stored" if persist_success else "analysis_failed_storage",
            "knowledge_node_id": node_id,
            "category": category.value,
            "diagnosis": analysis,
            "recommended_action": strategy.get('action'),
            "details": strategy.get('details')
        }
        
        return response

    def _determine_correction_strategy(self, category: ErrorCategory, state: Dict) -> Dict:
        """
        辅助函数：根据错误类别生成具体的修正策略。
        
        Args:
            category (ErrorCategory): 错误类别。
            state (Dict): 当前环境状态。
            
        Returns:
            Dict: 包含 'action' 和 'details' 的策略字典。
        """
        if category == ErrorCategory.ENV_MISSING:
            return {
                "action": CorrectionAction.RETRY_MODIFIED.value,
                "details": "Attempt to install missing dependency or use fallback library."
            }
        elif category == ErrorCategory.INTENT_MISMATCH:
            return {
                "action": CorrectionAction.ASK_HUMAN.value,
                "details": "Data structure unexpected. Request clarification on data schema."
            }
        elif category == ErrorCategory.LOGIC_FLAW:
            return {
                "action": CorrectionAction.ROLLBACK.value,
                "details": "Critical logic error. Rollback to last stable commit and refactor logic."
            }
        else:
            return {
                "action": CorrectionAction.SKIP_TASK.value,
                "details": "Unrecoverable error detected."
            }

# Usage Example
if __name__ == "__main__":
    # 初始化系统
    kb = KnowledgeBase()
    cognitive_system = AdaptiveErrorCognitiveSystem(knowledge_base=kb)

    # 模拟沙箱运行失败的数据
    mock_error_data = {
        "type": "ModuleNotFoundError",
        "message": "No module named 'pandas'",
        "code": "import pandas as pd\ndf = pd.DataFrame()"
    }
    mock_task = "Process uploaded CSV file and generate statistics"
    mock_sandbox = {"os": "linux", "python_version": "3.9"}

    print("--- Test Case 1: Processing a new failure ---")
    result = cognitive_system.process_execution_failure(
        error_info=mock_error_data,
        task_desc=mock_task,
        sandbox_state=mock_sandbox
    )
    print(json.dumps(result, indent=2))

    print("\n--- Test Case 2: Consulting memory before next attempt ---")
    # 模拟下一次遇到类似任务
    memory_check = cognitive_system.consult_past_failures("Process uploaded Excel file")
    if memory_check:
        print("System found relevant memory:")
        print(json.dumps(memory_check, indent=2))
    else:
        print("No relevant past failures found.")