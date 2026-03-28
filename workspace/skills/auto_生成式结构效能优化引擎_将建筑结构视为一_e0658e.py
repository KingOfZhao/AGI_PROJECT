"""
生成式结构效能优化引擎

该模块将建筑结构视为一个计算图（类似于神经网络），通过模拟深度学习中的
'反向传播'算法，对结构构件的截面属性进行微分求解。
旨在自动生成具备'最优传力路径'的仿生结构形态，并诊断结构中的薄弱环节。

主要功能:
1. 定义拓扑结构图
2. 模拟物理受力与梯度反向传播
3. 生成优化迭代报告

Author: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Node:
    """
    结构节点类
    
    Attributes:
        id (int): 节点唯一标识
        position (np.ndarray): 节点三维坐标
        is_fixed (bool): 是否为固定支座
        external_force (np.ndarray): 施加的外部荷载向量
    """
    id: int
    position: np.ndarray
    is_fixed: bool = False
    external_force: np.ndarray = np.zeros(3)


@dataclass
class Element:
    """
    结构构件类 (模拟神经网络中的权重连接)
    
    Attributes:
        id (int): 构件唯一标识
        node_a (int): 起始节点ID
        node_b (int): 终止节点ID
        cross_section (float): 截面尺寸 (模拟权重 Weight)
        current_stress (float): 当前计算出的应力 (模拟激活值)
    """
    id: int
    node_a: int
    node_b: int
    cross_section: float = 1.0
    current_stress: float = 0.0


class StructuralNeuralNetwork:
    """
    结构-神经网络映射模型
    
    将建筑结构映射为可微分的计算图。
    """
    
    def __init__(self, nodes: List[Node], elements: List[Element], learning_rate: float = 0.01):
        """
        初始化结构神经网络
        
        Args:
            nodes (List[Node]): 节点列表
            elements (List[Element]): 构件列表
            learning_rate (float): 优化学习率 (类似结构优化中的灵敏度)
        """
        self.nodes = {n.id: n for n in nodes}
        self.elements = {e.id: e for e in elements}
        self.learning_rate = learning_rate
        self.adjacency: Dict[int, List[int]] = {}
        self._build_adjacency()
        logger.info("Structural Neural Network initialized with %d nodes and %d elements.", 
                    len(self.nodes), len(self.elements))

    def _build_adjacency(self):
        """构建邻接表以加速查找"""
        for el in self.elements.values():
            if el.node_a not in self.adjacency:
                self.adjacency[el.node_a] = []
            if el.node_b not in self.adjacency:
                self.adjacency[el.node_b] = []
            self.adjacency[el.node_a].append(el.id)
            self.adjacency[el.node_b].append(el.id)

    def _calculate_element_stiffness(self, element_id: int) -> float:
        """
        辅助函数：计算构件的简化刚度
        
        Args:
            element_id (int): 构件ID
            
        Returns:
            float: 刚度值
            
        Note:
            简化公式: Stiffness ∝ Area / Length
        """
        el = self.elements[element_id]
        node_a = self.nodes[el.node_a]
        node_b = self.nodes[el.node_b]
        
        length = np.linalg.norm(node_a.position - node_b.position)
        if length < 1e-6:
            return 0.0
            
        # 简化的轴向刚度
        stiffness = el.cross_section / length
        return stiffness

    def forward_pass(self) -> float:
        """
        核心函数：前向传播 (模拟结构受力分析)
        
        计算力如何在结构中传递，并评估当前的'损失'（总重量或应变能）。
        
        Returns:
            float: 总体效能指标 (Total Compliance/Loss)
        """
        total_compliance = 0.0
        
        # 重置应力
        for el in self.elements.values():
            el.current_stress = 0.0

        # 简化的力流模拟：基于图论的力分配
        # 这里不进行完整的有限元矩阵求解，而是模拟力的"流动"
        # 假设力从加载点流向支座，应力与截面面积成反比（简单类比）
        
        for node in self.nodes.values():
            if np.linalg.norm(node.external_force) > 0:
                # 简单路径跟踪 (BFS-like propagation for demo)
                # 将力分配给连接的构件
                connected_elements = self.adjacency.get(node.id, [])
                if not connected_elements:
                    continue
                
                # 根据刚度分配力
                stiffnesses = np.array([self._calculate_element_stiffness(eid) for eid in connected_elements])
                total_stiff = np.sum(stiffnesses)
                
                if total_stiff == 0:
                    continue
                    
                for i, eid in enumerate(connected_elements):
                    el = self.elements[eid]
                    # 模拟应力计算
                    # 应力 ∝ 力 / 面积 (概念上)
                    # 这里我们模拟应力集中：截面越小，如果力大，应力越大
                    force_share = node.external_force * (stiffnesses[i] / total_stiff)
                    stress_magnitude = np.linalg.norm(force_share) / (el.cross_section + 1e-5)
                    el.current_stress = stress_magnitude
                    
                    # 损失函数：应变能 (Force * Deformation) + 惩罚项
                    # 简化为 Compliance = Stress^2 * Volume
                    length = np.linalg.norm(
                        self.nodes[el.node_a].position - self.nodes[el.node_b].position
                    )
                    volume = el.cross_section * length
                    total_compliance += (stress_magnitude ** 2) * volume

        logger.debug(f"Forward pass complete. Total Compliance: {total_compliance:.4f}")
        return total_compliance

    def backward_propagation(self, target_stress: float = 100.0):
        """
        核心函数：反向传播 (优化截面尺寸)
        
        根据应力分布调整截面（权重）。类似梯度下降。
        如果应力高于目标，增加截面；如果远低于目标，减少截面。
        
        Args:
            target_stress (float): 目标应力水平 (满应力设计准则 FSD)
        """
        logger.info("Starting backward propagation (Geometry Optimization)...")
        
        for el in self.elements.values():
            if el.current_stress < 1e-6:
                continue
                
            # 模拟梯度: d(Loss)/d(Weight) ∝ Stress - Target
            # 这里使用简单的比例控制作为梯度的近似
            gradient = el.current_stress - target_stress
            
            # 更新权重 (截面尺寸)
            # weight_new = weight_old - lr * gradient
            delta = self.learning_rate * gradient
            
            # 应用更新
            new_section = el.cross_section - delta # 负号因为我们要降低应力（损失）
            
            # 边界检查与数据验证
            min_section = 0.01 # 最小截面限制
            max_section = 10.0 # 最大截面限制
            
            if new_section < min_section:
                logger.warning(f"Element {el.id} hit minimum section boundary.")
                new_section = min_section
            elif new_section > max_section:
                logger.warning(f"Element {el.id} hit maximum section boundary.")
                new_section = max_section
                
            el.cross_section = new_section

    def diagnose_weak_points(self, threshold_ratio: float = 1.5) -> List[Dict[str, Any]]:
        """
        辅助函数：诊断薄弱环节 (类似于检测梯度消失/爆炸)
        
        找出应力集中或材料利用率极低的区域。
        
        Args:
            threshold_ratio (float): 判断应力集中的倍率 (相对于平均应力)
            
        Returns:
            List[Dict]: 包含薄弱点信息的列表
        """
        weak_points = []
        stresses = [el.current_stress for el in self.elements.values() if el.current_stress > 0]
        
        if not stresses:
            return []
            
        avg_stress = np.mean(stresses)
        
        for el in self.elements.values():
            if el.current_stress > avg_stress * threshold_ratio:
                weak_points.append({
                    "element_id": el.id,
                    "stress": el.current_stress,
                    "avg_stress": avg_stress,
                    "type": "Stress Concentration (High Risk)",
                    "suggestion": "Increase section or add bracing"
                })
            elif el.current_stress < avg_stress * (1 / threshold_ratio) and el.cross_section > 0.02:
                weak_points.append({
                    "element_id": el.id,
                    "stress": el.current_stress,
                    "avg_stress": avg_stress,
                    "type": "Material Inefficiency (Low Utilization)",
                    "suggestion": "Reduce section to save material"
                })
        
        return weak_points


def run_optimization_engine():
    """
    使用示例函数
    """
    try:
        logger.info("Initializing Generative Structural Optimization Engine...")
        
        # 1. 定义几何拓扑 (例如一个简单的桁架桥切片)
        # Nodes
        n1 = Node(1, np.array([0.0, 0.0, 0.0]), is_fixed=True)  # 支座
        n2 = Node(2, np.array([5.0, 0.0, 0.0]), is_fixed=True)  # 支座
        n3 = Node(3, np.array([2.5, 2.5, 0.0]), external_force=np.array([0.0, -100.0, 0.0])) # 荷载点
        n4 = Node(4, np.array([1.5, 1.0, 0.0])) # 中间节点
        n5 = Node(5, np.array([3.5, 1.0, 0.0])) # 中间节点
        
        # Elements
        # 初始截面都设为 1.0
        e1 = Element(1, 1, 3, 1.0)
        e2 = Element(2, 2, 3, 1.0)
        e3 = Element(3, 1, 4, 1.0)
        e4 = Element(4, 4, 3, 1.0)
        e5 = Element(5, 3, 5, 1.0)
        e6 = Element(6, 5, 2, 1.0)
        e7 = Element(7, 4, 5, 1.0)
        
        # 2. 实例化引擎
        engine = StructuralNeuralNetwork(
            nodes=[n1, n2, n3, n4, n5], 
            elements=[e1, e2, e3, e4, e5, e6, e7],
            learning_rate=0.005
        )
        
        # 3. 优化循环
        epochs = 50
        for i in range(epochs):
            loss = engine.forward_pass()
            engine.backward_propagation(target_stress=50.0) # 设定目标应力
            
            if i % 10 == 0:
                logger.info(f"Epoch {i}: Current Compliance Loss = {loss:.2f}")
        
        # 4. 最终诊断
        logger.info("Optimization finished. Diagnosing structure...")
        weak_spots = engine.diagnose_weak_points()
        
        print("\n=== Final Structural Report ===")
        print(f"{'Element ID':<12} {'Section Size':<15} {'Final Stress':<15}")
        print("-" * 45)
        for el in engine.elements.values():
            print(f"{el.id:<12} {el.cross_section:<15.4f} {el.current_stress:<15.4f}")
            
        print("\n=== Diagnostic Alerts ===")
        if not weak_spots:
            print("Structure is well optimized.")
        else:
            for alert in weak_spots:
                print(f"[Alert] Element {alert['element_id']}: {alert['type']}")
                print(f"        Stress: {alert['stress']:.2f} (Avg: {alert['avg_stress']:.2f})")
                print(f"        Action: {alert['suggestion']}")

    except Exception as e:
        logger.error(f"Critical error in optimization engine: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    run_optimization_engine()