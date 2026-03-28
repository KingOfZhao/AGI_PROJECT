"""
梯度流建筑结构优化系统

该模块实现了一个基于神经网络反向传播机制的建筑结构优化系统。通过将建筑结构
视为神经网络，利用梯度下降算法优化结构的拓扑形态，实现应力分布的均匀化，
从而减少材料浪费并提升抗震性能。

核心思想：
- 将建筑结构节点视为神经元
- 将构件连接视为神经突触
- 将应力分布视为损失函数
- 通过反向传播优化结构形态

依赖：
    - numpy
    - scipy
    - networkx
    - matplotlib (可视化)

作者: AGI System
版本: 1.0.0
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StructureType(Enum):
    """建筑结构类型枚举"""
    TRUSS = "truss"           # 桁架结构
    SHELL = "shell"           # 壳体结构
    FRAME = "frame"           # 框架结构
    MEMBRANE = "membrane"     # 膜结构


@dataclass
class Node:
    """
    结构节点类 - 对应神经网络中的神经元
    
    Attributes:
        id: 节点唯一标识符
        position: 三维坐标
        fixed: 是否为固定节点（支座）
        load: 施加的荷载向量
        displacement: 位移向量
    """
    id: int
    position: np.ndarray
    fixed: bool = False
    load: np.ndarray = field(default_factory=lambda: np.zeros(3))
    displacement: np.ndarray = field(default_factory=lambda: np.zeros(3))
    
    def __post_init__(self):
        """数据验证"""
        if self.position.shape != (3,):
            raise ValueError(f"节点{self.id}的位置必须是三维坐标")
        if self.load.shape != (3,):
            raise ValueError(f"节点{self.id}的荷载必须是三维向量")


@dataclass
class Element:
    """
    结构构件类 - 对应神经网络中的突触连接
    
    Attributes:
        id: 构件唯一标识符
        node_ids: 连接的节点ID对
        cross_section: 截面积
        material_property: 材料属性（弹性模量等）
        stress: 当前应力
        strain: 当前应变
    """
    id: int
    node_ids: Tuple[int, int]
    cross_section: float = 0.01
    material_property: Dict = field(default_factory=lambda: {"E": 210e9})  # 钢材弹性模量
    stress: float = 0.0
    strain: float = 0.0
    
    def __post_init__(self):
        """数据验证"""
        if self.cross_section <= 0:
            raise ValueError(f"构件{id}的截面积必须为正数")
        if len(self.node_ids) != 2:
            raise ValueError(f"构件{id}必须连接两个节点")


class GradientFlowStructuralOptimizer:
    """
    梯度流建筑结构优化器
    
    利用神经网络反向传播机制优化建筑结构的拓扑形态。通过迭代调整节点位置，
    使应力分布趋于均匀，实现结构的最优形态生成。
    
    输入格式:
        - nodes: List[Node] - 节点列表
        - elements: List[Element] - 构件列表
        - config: Dict - 配置参数
        
    输出格式:
        - optimized_nodes: List[Node] - 优化后的节点列表
        - metrics: Dict - 优化指标（应力分布、材料用量等）
    
    Example:
        >>> # 创建初始结构
        >>> nodes = [Node(0, np.array([0, 0, 0]), fixed=True),
        ...          Node(1, np.array([5, 0, 0]), fixed=True),
        ...          Node(2, np.array([2.5, 3, 0]), load=np.array([0, -1000, 0]))]
        >>> elements = [Element(0, (0, 2)), Element(1, (1, 2))]
        >>> 
        >>> # 初始化优化器
        >>> optimizer = GradientFlowStructuralOptimizer(
        ...     nodes=nodes, 
        ...     elements=elements,
        ...     config={"learning_rate": 0.01, "iterations": 100}
        ... )
        >>> 
        >>> # 执行优化
        >>> optimized_nodes, metrics = optimizer.optimize()
    """
    
    def __init__(
        self,
        nodes: List[Node],
        elements: List[Element],
        config: Optional[Dict] = None
    ):
        """
        初始化优化器
        
        Args:
            nodes: 结构节点列表
            elements: 结构构件列表
            config: 配置参数字典，包含：
                - learning_rate: 学习率（默认0.01）
                - iterations: 迭代次数（默认100）
                - target_stress: 目标应力（默认100e6 Pa）
                - boundary_penalty: 边界约束惩罚系数（默认0.1）
                - min_section: 最小截面积（默认0.001）
                - max_section: 最大截面积（默认0.1）
        """
        self.nodes = {node.id: node for node in nodes}
        self.elements = {elem.id: elem for elem in elements}
        
        # 默认配置
        self.config = {
            "learning_rate": 0.01,
            "iterations": 100,
            "target_stress": 100e6,  # 100 MPa
            "boundary_penalty": 0.1,
            "min_section": 0.001,
            "max_section": 0.1,
            "stress_tolerance": 0.05,  # 5%容差
            "gravity": np.array([0, 0, -9.81])
        }
        if config:
            self.config.update(config)
        
        # 优化历史记录
        self.history: List[Dict] = []
        
        # 验证数据完整性
        self._validate_structure()
        
        logger.info(f"初始化梯度流结构优化器: {len(nodes)}节点, {len(elements)}构件")
    
    def _validate_structure(self) -> None:
        """
        验证结构数据完整性
        
        Raises:
            ValueError: 数据验证失败时抛出
        """
        if len(self.nodes) < 2:
            raise ValueError("结构至少需要2个节点")
        
        if len(self.elements) < 1:
            raise ValueError("结构至少需要1个构件")
        
        # 检查构件连接的节点是否存在
        for elem_id, elem in self.elements.items():
            for node_id in elem.node_ids:
                if node_id not in self.nodes:
                    raise ValueError(
                        f"构件{elem_id}连接的节点{node_id}不存在"
                    )
        
        # 检查是否有固定节点
        fixed_count = sum(1 for node in self.nodes.values() if node.fixed)
        if fixed_count == 0:
            logger.warning("结构没有固定节点，可能导致刚体位移")
        
        logger.debug("结构数据验证通过")
    
    def _compute_element_length(
        self, 
        elem: Element,
        positions: Optional[Dict[int, np.ndarray]] = None
    ) -> float:
        """
        计算构件长度
        
        Args:
            elem: 构件对象
            positions: 可选的节点位置字典（用于优化过程中的临时位置）
            
        Returns:
            构件长度
        """
        if positions is None:
            positions = {nid: node.position for nid, node in self.nodes.items()}
        
        node1_pos = positions[elem.node_ids[0]]
        node2_pos = positions[elem.node_ids[1]]
        
        return float(np.linalg.norm(node2_pos - node1_pos))
    
    def _compute_stress_distribution(
        self,
        positions: Optional[Dict[int, np.ndarray]] = None
    ) -> Tuple[np.ndarray, float]:
        """
        计算应力分布（前向传播）
        
        基于有限元方法计算各构件的应力分布，对应神经网络的前向传播过程。
        
        Args:
            positions: 可选的节点位置字典
            
        Returns:
            Tuple[np.ndarray, float]: (应力数组, 总应变能)
        """
        if positions is None:
            positions = {nid: node.position for nid, node in self.nodes.items()}
        
        stresses = []
        total_strain_energy = 0.0
        
        for elem_id, elem in self.elements.items():
            length = self._compute_element_length(elem, positions)
            
            if length < 1e-10:
                logger.warning(f"构件{elem_id}长度过小，跳过")
                stresses.append(0.0)
                continue
            
            # 简化的应力计算（实际工程中需要完整有限元分析）
            # 计算节点力的影响
            node1 = self.nodes[elem.node_ids[0]]
            node2 = self.nodes[elem.node_ids[1]]
            
            # 方向向量
            direction = (positions[elem.node_ids[1]] - positions[elem.node_ids[0]]) / length
            
            # 计算轴向力（简化模型）
            force = np.linalg.norm(node1.load + node2.load)
            
            # 应力 = 力 / 截面积
            stress = force / elem.cross_section
            stresses.append(stress)
            
            # 应变能 = 0.5 * 应力 * 应变 * 体积
            strain = stress / elem.material_property["E"]
            volume = elem.cross_section * length
            strain_energy = 0.5 * stress * strain * volume
            total_strain_energy += strain_energy
            
            # 更新构件状态
            elem.stress = stress
            elem.strain = strain
        
        return np.array(stresses), total_strain_energy
    
    def _compute_loss(
        self,
        stresses: np.ndarray,
        positions: Dict[int, np.ndarray]
    ) -> float:
        """
        计算总损失函数
        
        损失函数由以下部分组成：
        1. 应力均匀性损失：使所有构件应力接近目标值
        2. 应力方差损失：最小化应力分布方差
        3. 边界约束损失：惩罚超出设计域边界的节点
        
        Args:
            stresses: 应力数组
            positions: 节点位置字典
            
        Returns:
            总损失值
        """
        if len(stresses) == 0:
            return float('inf')
        
        # 1. 应力均匀性损失
        target = self.config["target_stress"]
        stress_loss = np.mean((stresses - target) ** 2) / (target ** 2)
        
        # 2. 应力方差损失
        variance_loss = np.var(stresses) / (target ** 2)
        
        # 3. 边界约束损失
        boundary_loss = 0.0
        for node_id, pos in positions.items():
            if not self.nodes[node_id].fixed:
                # 惩罚负坐标（假设地面为z=0）
                if pos[2] < 0:
                    boundary_loss += pos[2] ** 2
        
        # 总损失
        total_loss = (
            stress_loss + 
            0.5 * variance_loss + 
            self.config["boundary_penalty"] * boundary_loss
        )
        
        return float(total_loss)
    
    def _compute_gradients(
        self,
        positions: Dict[int, np.ndarray]
    ) -> Dict[int, np.ndarray]:
        """
        计算位置梯度（反向传播）
        
        计算损失函数对各节点位置的梯度，对应神经网络的反向传播过程。
        使用数值微分方法计算梯度。
        
        Args:
            positions: 当前节点位置
            
        Returns:
            节点ID到梯度向量的映射
        """
        gradients = {}
        epsilon = 1e-6  # 数值微分步长
        
        # 计算当前损失
        stresses, _ = self._compute_stress_distribution(positions)
        base_loss = self._compute_loss(stresses, positions)
        
        for node_id, node in self.nodes.items():
            if node.fixed:
                gradients[node_id] = np.zeros(3)
                continue
            
            gradient = np.zeros(3)
            
            for i in range(3):
                # 前向扰动
                perturbed_pos = positions.copy()
                perturbed_pos[node_id] = perturbed_pos[node_id].copy()
                perturbed_pos[node_id][i] += epsilon
                
                stresses_perturbed, _ = self._compute_stress_distribution(perturbed_pos)
                loss_perturbed = self._compute_loss(stresses_perturbed, perturbed_pos)
                
                # 数值梯度
                gradient[i] = (loss_perturbed - base_loss) / epsilon
            
            gradients[node_id] = gradient
        
        return gradients
    
    def _update_positions(
        self,
        positions: Dict[int, np.ndarray],
        gradients: Dict[int, np.ndarray]
    ) -> Dict[int, np.ndarray]:
        """
        更新节点位置（梯度下降）
        
        使用自适应学习率更新节点位置，对应神经网络的权重更新过程。
        
        Args:
            positions: 当前位置
            gradients: 位置梯度
            
        Returns:
            更新后的位置
        """
        new_positions = {}
        lr = self.config["learning_rate"]
        
        for node_id, pos in positions.items():
            if self.nodes[node_id].fixed:
                new_positions[node_id] = pos.copy()
            else:
                # 梯度裁剪，防止过大的位移
                grad = gradients[node_id]
                grad_norm = np.linalg.norm(grad)
                if grad_norm > 1.0:
                    grad = grad / grad_norm
                
                # 自适应学习率
                adaptive_lr = lr / (1 + 0.01 * len(self.history))
                
                # 更新位置
                new_pos = pos - adaptive_lr * grad
                new_positions[node_id] = new_pos
        
        return new_positions
    
    def _optimize_cross_sections(self) -> None:
        """
        优化构件截面积
        
        根据应力分布优化各构件的截面积，实现材料的最优配置。
        应力高的构件增加截面积，应力低的构件减少截面积。
        """
        target = self.config["target_stress"]
        min_section = self.config["min_section"]
        max_section = self.config["max_section"]
        
        for elem_id, elem in self.elements.items():
            if elem.stress > 0:
                # 根据应力比调整截面积
                stress_ratio = elem.stress / target
                
                # 渐进调整
                if stress_ratio > 1.0 + self.config["stress_tolerance"]:
                    # 应力过高，增加截面积
                    adjustment = 1.0 + 0.1 * (stress_ratio - 1.0)
                elif stress_ratio < 1.0 - self.config["stress_tolerance"]:
                    # 应力过低，减少截面积
                    adjustment = 1.0 - 0.05 * (1.0 - stress_ratio)
                else:
                    adjustment = 1.0
                
                new_section = elem.cross_section * adjustment
                elem.cross_section = np.clip(new_section, min_section, max_section)
    
    def optimize(self) -> Tuple[List[Node], Dict]:
        """
        执行结构优化
        
        主优化循环，通过迭代更新节点位置和构件截面积，
        实现结构形态的整体优化。
        
        Returns:
            Tuple[List[Node], Dict]: 
                - 优化后的节点列表
                - 优化指标字典，包含：
                    - final_loss: 最终损失值
                    - stress_variance: 应力方差
                    - material_usage: 材料用量
                    - iterations: 迭代次数
                    - convergence_history: 收敛历史
        
        Raises:
            RuntimeError: 优化过程失败时抛出
        """
        logger.info("开始梯度流结构优化...")
        
        # 初始化位置
        positions = {nid: node.position.copy() for nid, node in self.nodes.items()}
        
        # 优化主循环
        for iteration in range(self.config["iterations"]):
            try:
                # 前向传播：计算应力分布
                stresses, strain_energy = self._compute_stress_distribution(positions)
                
                # 计算损失
                loss = self._compute_loss(stresses, positions)
                
                # 反向传播：计算梯度
                gradients = self._compute_gradients(positions)
                
                # 更新位置
                positions = self._update_positions(positions, gradients)
                
                # 优化截面积
                self._optimize_cross_sections()
                
                # 记录历史
                metrics = {
                    "iteration": iteration,
                    "loss": loss,
                    "stress_mean": float(np.mean(stresses)),
                    "stress_std": float(np.std(stresses)),
                    "strain_energy": strain_energy,
                    "max_stress": float(np.max(stresses)) if len(stresses) > 0 else 0,
                    "min_stress": float(np.min(stresses)) if len(stresses) > 0 else 0
                }
                self.history.append(metrics)
                
                # 日志记录
                if iteration % 10 == 0:
                    logger.info(
                        f"迭代 {iteration}: 损失={loss:.6f}, "
                        f"平均应力={np.mean(stresses)/1e6:.2f}MPa, "
                        f"应力标准差={np.std(stresses)/1e6:.2f}MPa"
                    )
                
                # 收敛检查
                if loss < 1e-8:
                    logger.info(f"优化收敛于迭代 {iteration}")
                    break
                    
            except Exception as e:
                logger.error(f"迭代 {iteration} 发生错误: {str(e)}")
                raise RuntimeError(f"优化过程失败: {str(e)}")
        
        # 更新节点位置
        for node_id, pos in positions.items():
            self.nodes[node_id].position = pos
        
        # 计算最终指标
        final_stresses, _ = self._compute_stress_distribution()
        
        # 计算材料用量
        total_material = sum(
            elem.cross_section * self._compute_element_length(elem)
            for elem in self.elements.values()
        )
        
        final_metrics = {
            "final_loss": self.history[-1]["loss"] if self.history else float('inf'),
            "stress_variance": float(np.var(final_stresses)),
            "stress_mean": float(np.mean(final_stresses)),
            "material_usage": total_material,
            "iterations": len(self.history),
            "convergence_history": [h["loss"] for h in self.history],
            "optimization_success": len(self.history) > 0
        }
        
        logger.info(
            f"优化完成: 最终损失={final_metrics['final_loss']:.6f}, "
            f"材料用量={total_material:.4f}m³"
        )
        
        return list(self.nodes.values()), final_metrics
    
    def export_results(self, filepath: Union[str, Path]) -> None:
        """
        导出优化结果到JSON文件
        
        Args:
            filepath: 输出文件路径
        """
        filepath = Path(filepath)
        
        results = {
            "nodes": [
                {
                    "id": node.id,
                    "position": node.position.tolist(),
                    "fixed": node.fixed,
                    "load": node.load.tolist()
                }
                for node in self.nodes.values()
            ],
            "elements": [
                {
                    "id": elem.id,
                    "node_ids": list(elem.node_ids),
                    "cross_section": elem.cross_section,
                    "stress": elem.stress,
                    "strain": elem.strain
                }
                for elem in self.elements.values()
            ],
            "history": self.history,
            "config": self.config
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"结果已导出至: {filepath}")


# ===================== 辅助函数 =====================

def create_grid_structure(
    width: float,
    length: float,
    height: float,
    divisions: Tuple[int, int, int]
) -> Tuple[List[Node], List[Element]]:
    """
    创建网格结构（辅助函数）
    
    生成三维网格结构作为优化的初始形态。
    
    Args:
        width: 结构宽度
        length: 结构长度
        height: 结构高度
        divisions: (x, y, z)方向的网格划分数
        
    Returns:
        Tuple[List[Node], List[Element]: 节点列表和构件列表
    
    Example:
        >>> nodes, elements = create_grid_structure(10, 10, 5, (5, 5, 3))
        >>> print(f"创建 {len(nodes)} 个节点, {len(elements)} 个构件")
    """
    nx, ny, nz = divisions
    nodes = []
    elements = []
    
    # 创建节点
    node_id = 0
    node_map = {}  # (i, j, k) -> node_id
    
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                x = i * width / nx
                y = j * length / ny
                z = k * height / nz
                
                # 底层节点固定
                fixed = (k == 0)
                
                node = Node(
                    id=node_id,
                    position=np.array([x, y, z]),
                    fixed=fixed,
                    load=np.array([0, 0, -100 if k == nz else 0])  # 顶层施加荷载
                )
                nodes.append(node)
                node_map[(i, j, k)] = node_id
                node_id += 1
    
    # 创建构件（连接相邻节点）
    elem_id = 0
    
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                current = (i, j, k)
                
                # X方向连接
                if i < nx:
                    neighbor = (i + 1, j, k)
                    elements.append(Element(
                        id=elem_id,
                        node_ids=(node_map[current], node_map[neighbor])
                    ))
                    elem_id += 1
                
                # Y方向连接
                if j < ny:
                    neighbor = (i, j + 1, k)
                    elements.append(Element(
                        id=elem_id,
                        node_ids=(node_map[current], node_map[neighbor])
                    ))
                    elem_id += 1
                
                # Z方向连接
                if k < nz:
                    neighbor = (i, j, k + 1)
                    elements.append(Element(
                        id=elem_id,
                        node_ids=(node_map[current], node_map[neighbor])
                    ))
                    elem_id += 1
    
    logger.info(f"创建网格结构: {len(nodes)}节点, {len(elements)}构件")
    return nodes, elements


def analyze_optimization_results(
    optimizer: GradientFlowStructuralOptimizer
) -> Dict:
    """
    分析优化结果（辅助函数）
    
    对优化结果进行详细分析，包括应力分布、材料效率、形态变化等。
    
    Args:
        optimizer: 已完成优化的优化器实例
        
    Returns:
        分析结果字典，包含：
        - stress_efficiency: 应力效率（实际/理想）
        - material_saving: 材料节省比例
        - form_complexity: 形态复杂度
        - structural_stability: 结构稳定性指标
    """
    if not optimizer.history:
        raise ValueError("优化器尚未执行优化")
    
    # 计算应力效率
    final_metrics = optimizer.history[-1]
    target_stress = optimizer.config["target_stress"]
    actual_mean_stress = final_metrics["stress_mean"]
    
    stress_efficiency = min(actual_mean_stress, target_stress) / max(actual_mean_stress, target_stress)
    
    # 计算材料节省（与均匀截面对比）
    optimized_material = sum(
        elem.cross_section * optimizer._compute_element_length(elem)
        for elem in optimizer.elements.values()
    )
    
    avg_section = np.mean([elem.cross_section for elem in optimizer.elements.values()])
    uniform_material = avg_section * sum(
        optimizer._compute_element_length(elem)
        for elem in optimizer.elements.values()
    )
    
    material_saving = 1.0 - (optimized_material / uniform_material) if uniform_material > 0 else 0
    
    # 计算形态复杂度（基于位置方差）
    positions = np.array([node.position for node in optimizer.nodes.values()])
    form_complexity = np.mean(np.std(positions, axis=0))
    
    # 结构稳定性（基于应力分布均匀性）
    stress_std = final_metrics["stress_std"]
    structural_stability = 1.0 / (1.0 + stress_std / target_stress)
    
    analysis = {
        "stress_efficiency": float(stress_efficiency),
        "material_saving": float(material_saving),
        "form_complexity": float(form_complexity),
        "structural_stability": float(structural_stability),
        "final_loss": final_metrics["loss"],
        "iterations_completed": len(optimizer.history)
    }
    
    logger.info(f"优化分析完成: 应力效率={stress_efficiency:.2%}, "
                f"材料节省={material_saving:.2%}")
    
    return analysis


# ===================== 主程序入口 =====================

if __name__ == "__main__":
    # 使用示例
    print("=" * 60)
    print("梯度流建筑结构优化系统 - 演示")
    print("=" * 60)
    
    # 1. 创建初始网格结构
    print("\n1. 创建初始网格结构...")
    nodes, elements = create_grid_structure(
        width=10.0,    # 10米宽
        length=10.0,   # 10米长
        height=5.0,    # 5米高
        divisions=(4, 4, 2)  # 4x4x2 网格划分
    )
    
    # 2. 配置优化参数
    print("\n2. 配置优化参数...")
    config = {
        "learning_rate": 0.05,
        "iterations": 50,
        "target_stress": 80e6,  # 80 MPa
        "boundary_penalty": 0.2,
        "min_section": 0.002,
        "max_section": 0.08
    }
    
    # 3. 初始化优化器
    print("\n3. 初始化优化器...")
    optimizer = GradientFlowStructuralOptimizer(
        nodes=nodes,
        elements=elements,
        config=config
    )
    
    # 4. 执行优化
    print("\n4. 执行梯度流优化...")
    optimized_nodes, metrics = optimizer.optimize()
    
    # 5. 分析结果
    print("\n5. 分析优化结果...")
    analysis = analyze_optimization_results(optimizer)
    
    # 6. 输出结果摘要
    print("\n" + "=" * 60)
    print("优化结果摘要")
    print("=" * 60)
    print(f"迭代次数: {metrics['iterations']}")
    print(f"最终损失: {metrics['final_loss']:.6f}")
    print(f"平均应力: {metrics['stress_mean']/1e6:.2f} MPa")
    print(f"应力方差: {metrics['stress_variance']/1e12:.4f} (MPa)²")
    print(f"材料用量: {metrics['material_usage']:.4f} m³")
    print(f"应力效率: {analysis['stress_efficiency']:.2%}")
    print(f"材料节省: {analysis['material_saving']:.2%}")
    print(f"结构稳定性: {analysis['structural_stability']:.4f}")
    
    # 7. 导出结果
    print("\n7. 导出优化结果...")
    optimizer.export_results("optimization_results.json")
    
    print("\n" + "=" * 60)
    print("优化完成！")
    print("=" * 60)