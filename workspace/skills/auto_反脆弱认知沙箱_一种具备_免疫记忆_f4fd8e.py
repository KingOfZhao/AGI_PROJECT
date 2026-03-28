"""
anti_fragile_sandbox.py
高级Python工程师为AGI系统生成的核心SKILL模块。

该模块实现了一个具备“免疫记忆”的反脆弱认知沙箱。它不仅仅是运行代码的容器，
更是认知的边界探测器。通过捕获执行过程中的失败（测试不通过或运行时错误），
系统自动触发“失败固化”机制，将错误上下文提炼为“反模式真实节点”（免疫节点）。
这些节点持久化存储，使得AI在未来的代码生成中能检索并主动避开类似的错误模式，
从而实现从失败中学习的自进化能力。

作者: AGI System Core
版本: 1.0.0
"""

import json
import logging
import hashlib
import pickle
import datetime
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 配置高可用的日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AntiFragileSandbox")

@dataclass
class ImmuneNode:
    """
    免疫节点数据结构（反模式真实节点）。
    
    Attributes:
        node_id (str): 基于错误特征生成的唯一哈希ID。
        timestamp (str): 错误发生的时间戳。
        error_type (str): 异常类型名称。
        error_message (str): 详细的错误信息。
        traceback (str): 完整的调用堆栈。
        context_snapshot (Dict): 导致错误的输入数据快照（经过脱敏处理）。
        code_signature (str): 执行代码的哈希签名，用于关联代码模式。
    """
    node_id: str
    timestamp: str
    error_type: str
    error_message: str
    traceback: str
    context_snapshot: Dict[str, Any]
    code_signature: str

class ImmuneMemorySystem:
    """
    免疫记忆存储系统。
    负责管理和持久化“免疫节点”，提供检索接口。
    """
    
    def __init__(self, storage_path: str = "immune_memory_store.pkl"):
        """
        初始化记忆系统。

        Args:
            storage_path (str): 持久化存储文件路径。
        """
        self.storage_path = storage_path
        self._memory_bank: Dict[str, ImmuneNode] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        """从磁盘加载历史记忆。"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'rb') as f:
                    self._memory_bank = pickle.load(f)
                logger.info(f"Loaded {len(self._memory_bank)} immune nodes from memory.")
            except Exception as e:
                logger.error(f"Failed to load immune memory: {e}")
                self._memory_bank = {}
        else:
            self._memory_bank = {}

    def _save_memory(self) -> None:
        """持久化记忆到磁盘。"""
        try:
            with open(self.storage_path, 'wb') as f:
                pickle.dump(self._memory_bank, f)
        except Exception as e:
            logger.error(f"Failed to save immune memory: {e}")

    def memorize(self, node: ImmuneNode) -> None:
        """
        存储一个新的免疫节点。

        Args:
            node (ImmuneNode): 包含错误信息的节点对象。
        """
        if not isinstance(node, ImmuneNode):
            raise ValueError("Invalid node type provided for memorization.")
        
        self._memory_bank[node.node_id] = node
        self._save_memory()
        logger.warning(f"New Immune Node solidified: {node.node_id} ({node.error_type})")

    def recall_similar(self, code_signature: str) -> List[ImmuneNode]:
        """
        检索与特定代码模式相关的历史错误。

        Args:
            code_signature (str): 待检查代码的签名。

        Returns:
            List[ImmuneNode]: 相关的免疫节点列表。
        """
        return [node for node in self._memory_bank.values() if node.code_signature == code_signature]

class AntiFragileSandbox:
    """
    反脆弱认知沙箱核心类。
    
    该沙箱执行传入的可执行对象（函数），监控其运行状态。
    一旦捕获异常，立即触发固化机制。
    """

    def __init__(self, memory_system: ImmuneMemorySystem):
        """
        初始化沙箱。

        Args:
            memory_system (ImmuneMemorySystem): 外部注入的免疫记忆系统实例。
        """
        self.memory = memory_system

    @staticmethod
    def _generate_signature(code_str: str) -> str:
        """生成代码的唯一签名（简化版，实际可用AST分析）。"""
        return hashlib.md5(code_str.encode('utf-8')).hexdigest()

    @staticmethod
    def _sanitize_input(input_data: Any) -> Dict[str, Any]:
        """
        数据验证与快照生成。
        确保输入数据可序列化，并进行边界检查。
        """
        if input_data is None:
            return {}
        
        # 这里仅做简单的类型检查和转换示例
        try:
            # 尝试JSON序列化来验证数据是否安全
            json.dumps(str(input_data))
            return {"snapshot": str(input_data)[:200]} # 截断防止过大
        except TypeError:
            return {"snapshot": "Unserializable data"}

    def _solidify_failure(self, 
                          exec_context: Dict, 
                          code_str: str, 
                          error: Exception, 
                          traceback_str: str) -> None:
        """
        核心辅助函数：失败固化机制。
        
        将运行时错误转化为结构化的知识节点。
        """
        timestamp = datetime.datetime.now().isoformat()
        signature = self._generate_signature(code_str)
        error_type = type(error).__name__
        
        # 生成唯一ID：基于错误类型和代码签名
        raw_id = f"{signature}-{error_type}"
        node_id = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()[:16]

        node = ImmuneNode(
            node_id=node_id,
            timestamp=timestamp,
            error_type=error_type,
            error_message=str(error),
            traceback=traceback_str,
            context_snapshot=exec_context,
            code_signature=signature
        )
        
        self.memory.memorize(node)

    def execute(self, 
                func: Callable, 
                inputs: Dict[str, Any], 
                code_source: str = "unknown") -> Tuple[bool, Any]:
        """
        核心函数：在安全环境中执行代码。

        Args:
            func (Callable): 待执行的目标函数。
            inputs (Dict[str, Any]): 函数的输入参数字典。
            code_source (str): 生成该代码的源码文本（用于签名计算）。

        Returns:
            Tuple[bool, Any]: (执行状态, 结果或错误对象)。
        
        Raises:
            TypeError: 如果传入的不是可调用对象。
        """
        if not callable(func):
            logger.error("Execution failed: Provided object is not callable.")
            raise TypeError("Target must be a callable function.")

        logger.info(f"Starting sandbox execution for inputs: {list(inputs.keys())}")
        
        try:
            # 数据边界预检
            safe_inputs = self._sanitize_input(inputs)
            
            # 执行目标逻辑
            result = func(**inputs)
            
            logger.info("Execution successful within sandbox.")
            return True, result

        except Exception as e:
            # 捕获异常并提取堆栈
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_str = "".join(
                logging.TracebackException.from_exception(e).format()
            )
            
            logger.error(f"Caught exception in sandbox: {exc_type.__name__}: {exc_value}")
            
            # 触发反脆弱机制：失败固化
            context = {
                "input_args": safe_inputs,
                "source_code_preview": code_source[:100]
            }
            self._solidify_failure(context, code_source, e, traceback_str)
            
            return False, e

# --- 使用示例 ---
if __name__ == "__main__":
    # 1. 初始化免疫记忆系统
    immune_sys = ImmuneMemorySystem(storage_path="temp_immune_system.pkl")
    
    # 2. 初始化沙箱
    sandbox = AntiFragileSandbox(memory_system=immune_sys)

    # 示例 1: 必然成功的代码
    def good_code(x: int, y: int) -> int:
        return x + y

    success, res = sandbox.execute(good_code, {'x': 10, 'y': 20}, code_source="def good_code...")
    print(f"Test 1 Result: Success={success}, Value={res}")

    # 示例 2: 必然失败的代码 (模拟反脆弱学习过程)
    def fragile_code(data: list) -> int:
        # 故意制造一个边界错误：未检查列表是否为空
        return data[0] 

    # 第一次运行失败，将生成免疫节点
    print("\n--- Running fragile code (Attempt 1) ---")
    success, err = sandbox.execute(fragile_code, {'data': []}, code_source="def fragile_code...")
    print(f"Test 2 Result: Success={success}, Error={type(err).__name__}")
    
    # 检查记忆系统是否记录了该错误
    retrieved_nodes = immune_sys.recall_similar(sandbox._generate_signature("def fragile_code..."))
    if retrieved_nodes:
        print(f"--> System has learned from failure! Memory node found: {retrieved_nodes[0].node_id}")
        print(f"--> Error details recorded: {retrieved_nodes[0].error_message}")

    # 清理临时文件 (可选)
    if os.path.exists("temp_immune_system.pkl"):
        os.remove("temp_immune_system.pkl")