"""
仿生自愈存储网络

该模块实现了一种受DNA修复酶机制启发的分布式存储维护系统。
它定义了“数字酶”Agent，能够扫描存储节点（细胞），检测数据损坏（变异），
并利用同源参考（健康副本）执行原子级修复，从而实现动态的代谢式数据维护。

Classes:
    BionicStorageNode: 代表网络中的单个存储节点（细胞）。
    DigitalEnzyme: 负责扫描、诊断和修复数据的智能Agent。

Functions:
    calculate_genetic_hash: 辅助函数，计算数据的哈希值以验证完整性。
    detect_mutations: 核心函数，扫描网络并识别受损节点。
    repair_mutation: 核心函数，利用健康参考节点修复受损数据。

Example:
    >>> node_a = BionicStorageNode("node_1", b"healthy_data")
    >>> node_b = BionicStorageNode("node_2", b"healthy_data") # node_2 is node_1's homolog
    >>> # Simulate mutation
    >>> node_b.data = b"corrupted_data"
    >>> enzyme = DigitalEnzyme()
    >>> enzyme.register_homology_pair(node_a, node_b)
    >>> enzyme.run_metabolic_cycle()
    >>> print(node_b.data.decode())
    healthy_data
"""

import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BionicStorageNetwork")


@dataclass
class BionicStorageNode:
    """
    代表仿生存储网络中的一个节点（细胞）。

    Attributes:
        node_id (str): 节点的唯一标识符。
        data (bytes): 存储的数据载荷。
        checksum (str): 数据的SHA-256校验和，用于完整性验证。
        is_healthy (bool): 标记节点当前是否处于健康状态。
    """
    node_id: str
    data: bytes
    checksum: str = field(init=False)
    is_healthy: bool = field(init=False)

    def __post_init__(self):
        """初始化后计算校验和并标记为健康。"""
        self.checksum = calculate_genetic_hash(self.data)
        self.is_healthy = True

    def update_data(self, new_data: bytes) -> None:
        """
        更新节点数据并重新计算校验和。

        Args:
            new_data (bytes): 新的数据载荷。

        Raises:
            ValueError: 如果数据为空或非字节类型。
        """
        if not isinstance(new_data, bytes):
            raise ValueError("Data must be of type bytes.")
        if len(new_data) == 0:
            raise ValueError("Data payload cannot be empty.")
        
        self.data = new_data
        self.checksum = calculate_genetic_hash(new_data)
        self.is_healthy = True


class DigitalEnzyme:
    """
    数字酶Agent。负责监控存储网络，检测变异（数据损坏），
    并利用同源重组机制修复受损节点。
    """

    def __init__(self):
        """初始化数字酶，建立节点注册表和同源映射。"""
        self.nodes: Dict[str, BionicStorageNode] = {}
        self.homology_map: Dict[str, str] = {}  # Maps node_id -> reference_node_id

    def register_node(self, node: BionicStorageNode) -> None:
        """
        注册一个存储节点到网络中。

        Args:
            node (BionicStorageNode): 要注册的节点实例。
        """
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already registered. Overwriting.")
        self.nodes[node.node_id] = node
        logger.info(f"Node {node.node_id} registered successfully.")

    def register_homology_pair(self, node_a: BionicStorageNode, node_b: BionicStorageNode) -> None:
        """
        注册两个节点为同源对（互为备份参考）。

        Args:
            node_a (BionicStorageNode): 节点A。
            node_b (BionicStorageNode): 节点B。
        """
        self.homology_map[node_a.node_id] = node_b.node_id
        self.homology_map[node_b.node_id] = node_a.node_id
        logger.info(f"Homology pair established: {node_a.node_id} <-> {node_b.node_id}")

    def _validate_input(self, data: bytes) -> bool:
        """
        辅助函数：验证输入数据的有效性。

        Args:
            data (bytes): 待验证的数据。

        Returns:
            bool: 如果数据有效返回True，否则返回False。
        """
        return isinstance(data, bytes) and len(data) > 0

    def detect_mutations(self) -> List[str]:
        """
        核心函数：扫描网络，检测数据变异（完整性校验失败）。

        Returns:
            List[str]: 检测到的受损节点ID列表。
        """
        damaged_nodes = []
        logger.info("Starting metabolic scan for mutations...")

        for node_id, node in self.nodes.items():
            # 重新计算当前数据的哈希
            current_hash = calculate_genetic_hash(node.data)
            
            # 比较存储的校验和与实际校验和
            if current_hash != node.checksum:
                logger.warning(
                    f"Mutation detected in node {node_id}. "
                    f"Expected: {node.checksum}, Found: {current_hash}"
                )
                node.is_healthy = False
                damaged_nodes.append(node_id)
            else:
                node.is_healthy = True

        if not damaged_nodes:
            logger.info("Scan complete. No mutations found.")
        else:
            logger.error(f"Scan complete. Found {len(damaged_nodes)} damaged nodes.")
            
        return damaged_nodes

    def repair_mutation(self, damaged_node_id: str) -> bool:
        """
        核心函数：利用同源参考节点修复受损节点。

        Args:
            damaged_node_id (str): 需要修复的节点ID。

        Returns:
            bool: 修复成功返回True，失败返回False。
        """
        if damaged_node_id not in self.nodes:
            logger.error(f"Repair failed: Node {damaged_node_id} not found in network.")
            return False

        damaged_node = self.nodes[damaged_node_id]

        # 查找同源参考节点
        if damaged_node_id not in self.homology_map:
            logger.error(f"Repair failed: No homology reference found for {damaged_node_id}.")
            return False

        reference_node_id = self.homology_map[damaged_node_id]
        reference_node = self.nodes.get(reference_node_id)

        # 验证参考节点是否健康
        if not reference_node or not reference_node.is_healthy:
            logger.error(
                f"Repair failed: Reference node {reference_node_id} is missing or damaged. "
                "Cannot perform safe repair."
            )
            return False

        try:
            # 执行原子级修复（数据替换）
            logger.info(
                f"Initiating enzymatic repair on {damaged_node_id} "
                f"using template from {reference_node_id}..."
            )
            
            # 在实际应用中，这里可能涉及更复杂的差异修补算法
            # 这里实现完全覆盖修复
            damaged_node.update_data(reference_node.data)
            
            logger.info(
                f"Repair successful. Node {damaged_node_id} integrity restored. "
                f"New Checksum: {damaged_node.checksum}"
            )
            return True

        except Exception as e:
            logger.exception(f"Critical error during repair of {damaged_node_id}: {e}")
            return False

    def run_metabolic_cycle(self) -> Dict[str, bool]:
        """
        执行一个完整的代谢周期：扫描所有节点并尝试修复发现的变异。

        Returns:
            Dict[str, bool]: 修复结果报告，键为节点ID，值为是否修复成功。
        """
        results = {}
        damaged_ids = self.detect_mutations()

        for node_id in damaged_ids:
            success = self.repair_mutation(node_id)
            results[node_id] = success

        return results


def calculate_genetic_hash(data: bytes) -> str:
    """
    辅助函数：计算数据的数字“基因”指纹（SHA-256）。

    Args:
        data (bytes): 输入数据。

    Returns:
        str: 十六进制格式的哈希字符串。
    """
    if not isinstance(data, bytes):
        raise TypeError("Input data must be bytes.")
    return hashlib.sha256(data).hexdigest()


# 使用示例
if __name__ == "__main__":
    # 1. 初始化环境
    enzyme_agent = DigitalEnzyme()

    # 2. 创建节点（细胞）
    # 原始数据
    original_payload = b"Critical_Genome_Segment_Alpha_207e7d"
    
    node_cell_1 = BionicStorageNode("cell_01", original_payload)
    node_cell_2 = BionicStorageNode("cell_02", original_payload) # cell_02 是 cell_01 的同源副本

    # 3. 注册节点和同源关系
    enzyme_agent.register_node(node_cell_1)
    enzyme_agent.register_node(node_cell_2)
    enzyme_agent.register_homology_pair(node_cell_1, node_cell_2)

    print(f"Initial State Cell 1: {node_cell_1.data}")
    print(f"Initial State Cell 2: {node_cell_2.data}")
    print("-" * 40)

    # 4. 模拟变异（数据篡改/损坏）
    print("Simulating data corruption in Cell 2...")
    node_cell_2.data = b"Corrupted_Mutant_Data_XYZ"
    # 注意：此时 checksum 属性尚未更新，模拟了物理层面的比特翻转

    # 5. 运行代谢周期（自愈）
    print("Running metabolic cycle (Auto-Healing)...")
    repair_report = enzyme_agent.run_metabolic_cycle()

    # 6. 验证结果
    print("-" * 40)
    print(f"Final State Cell 1: {node_cell_1.data}")
    print(f"Final State Cell 2: {node_cell_2.data}")
    print(f"Repair Report: {repair_report}")
    
    if node_cell_2.data == original_payload:
        print("\n[SUCCESS] Bionic self-healing mechanism restored the data successfully.")
    else:
        print("\n[FAILURE] Data integrity compromised.")