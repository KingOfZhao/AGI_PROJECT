"""
模块: auto_基于内部拓扑一致性的自证伪机制_如何在大_58ed8c
描述: 基于内部拓扑一致性的自证伪机制：如何在大规模知识网络（节点数>1000）中，
      利用图神经网络（GNN）检测语义向量空间中的逻辑冲突？例如，节点A蕴含非B，
      但网络中存在A到B的强连接。系统需自动生成'证伪向量'，对冲突区域进行定向干扰，
      测试网络鲁棒性。
领域: cognitive_science
"""

import logging
import random
import sys
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_EMBEDDING_DIM = 128
DEFAULT_HIDDEN_DIM = 256
DEFAULT_CONFLICT_THRESHOLD = 0.7
MIN_NODES_FOR_VALIDATION = 10


class SimpleGNNLayer(nn.Module):
    """
    简单的图神经网络层，用于聚合邻居信息。
    这是一个极简实现，用于演示核心逻辑，生产环境建议使用PyG或DGL。
    """
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, h: Tensor, adj_matrix: Tensor) -> Tensor:
        """
        前向传播。
        
        Args:
            h: 节点特征矩阵 shape (N, in_features)
            adj_matrix: 邻接矩阵 shape (N, N)
        
        Returns:
            更新后的特征 shape (N, out_features)
        """
        # 简单的聚合：邻居特征的加权和
        agg = torch.matmul(adj_matrix, h)
        return F.relu(self.linear(agg))


class TopologyConsistencyValidator:
    """
    基于内部拓扑一致性的自证伪系统。
    
    该系统旨在检测大规模语义知识网络中的逻辑冲突，并通过生成对抗性向量来测试系统的鲁棒性。
    
    核心逻辑：
    1. 使用GNN编码器将节点特征和拓扑结构映射到统一的语义向量空间。
    2. 计算拓扑一致性得分：如果节点A和B在图中强连接，它们的语义向量应高度相似/相关；
       如果A蕴含非B，则应低相关。
    3. 冲突检测：寻找高连接强度但低语义相似度（或相反逻辑）的节点对。
    4. 自证伪：生成'证伪向量'，通过反向传播扰动原始输入，试图放大或修复冲突，
       以观察系统的稳定性。
    """

    def __init__(self, node_count: int, embedding_dim: int = DEFAULT_EMBEDDING_DIM, 
                 hidden_dim: int = DEFAULT_HIDDEN_DIM, device: str = 'cpu'):
        """
        初始化验证器。
        
        Args:
            node_count: 知识网络中的节点总数。
            embedding_dim: 节点初始嵌入维度。
            hidden_dim: GNN隐藏层维度。
            device: 计算设备。
        """
        if node_count < MIN_NODES_FOR_VALIDATION:
            raise ValueError(f"节点数量必须大于 {MIN_NODES_FOR_VALIDATION} 以进行有效的拓扑分析。")
        
        self.node_count = node_count
        self.embedding_dim = embedding_dim
        self.device = torch.device(device)
        
        # 定义简单的GNN编码器 (2层)
        self.encoder = nn.Sequential(
            SimpleGNNLayer(embedding_dim, hidden_dim),
            SimpleGNNLayer(hidden_dim, hidden_dim)
        ).to(self.device)
        
        logger.info(f"TopologyConsistencyValidator initialized with {node_count} nodes on {self.device}.")

    def _validate_inputs(self, node_features: Tensor, adj_matrix: Tensor):
        """验证输入数据的维度和类型。"""
        if node_features.shape[0] != self.node_count or adj_matrix.shape[0] != self.node_count:
            raise ValueError(f"输入数据形状不匹配。期望节点数: {self.node_count}, "
                             f"得到特征: {node_features.shape[0]}, 邻接: {adj_matrix.shape[0]}")
        if node_features.shape[1] != self.embedding_dim:
            raise ValueError(f"特征维度不匹配。期望: {self.embedding_dim}, 得到: {node_features.shape[1]}")
        if not torch.is_floating_point(adj_matrix):
             raise TypeError("邻接矩阵必须是浮点类型.")

    def detect_conflicts(self, node_features: Tensor, adj_matrix: Tensor, 
                         threshold: float = DEFAULT_CONFLICT_THRESHOLD) -> List[Dict[str, Union[int, float]]]:
        """
        核心函数1：检测语义空间与拓扑结构之间的逻辑冲突。
        
        逻辑：
        1. 获取节点的GNN嵌入。
        2. 计算邻接矩阵中非零边（连接）的语义相似度（余弦相似度）。
        3. 如果存在边但相似度极低，或者无边但相似度极高，标记为潜在冲突。
        
        Args:
            node_features: 初始节点特征 (N, D).
            adj_matrix: 邻接矩阵 (N, N)，值代表连接强度.
            threshold: 判定冲突的阈值.
            
        Returns:
            冲突列表，每个元素包含 {'node_u': int, 'node_v': int, 'score': float, 'type': str}
        """
        try:
            self._validate_inputs(node_features, adj_matrix)
        except (ValueError, TypeError) as e:
            logger.error(f"输入验证失败: {e}")
            return []

        self.encoder.eval()
        with torch.no_grad():
            # 获取拓扑感知的嵌入
            # 注意：这里简化了多层GNN的调用，实际需要循环或Sequential支持多输入
            # 为演示方便，假设encoder只包含一层或者我们已经处理好了forward
            # 修正：上面的Sequential不能直接处理adj_matrix，这里手动调用
            h = node_features.to(self.device)
            adj = adj_matrix.to(self.device)
            
            # 手动前向传播模拟
            for layer in self.encoder:
                if isinstance(layer, SimpleGNNLayer):
                    h = layer(h, adj)
            
            # 归一化用于余弦相似度
            h_norm = F.normalize(h, p=2, dim=1)
            
            # 计算相似度矩阵 (N, N)
            similarity_matrix = torch.matmul(h_norm, h_norm.T)
            
            conflicts = []
            
            # 只检查上三角部分以避免重复 (忽略自环)
            rows, cols = torch.triu_indices(self.node_count, self.node_count, offset=1)
            
            # 提取对应位置的拓扑连接强度和语义相似度
            topo_strength = adj[rows, cols]
            sem_sim = similarity_matrix[rows, cols]
            
            # 冲突条件1: 强拓扑连接 (A->B) 但 语义冲突 (A ~ !B, 即相似度低)
            # 假设 adj > 0.5 为强连接, sim < 0.3 为语义背离
            conflict_mask_type1 = (topo_strength > 0.8) & (sem_sim < 0.3)
            
            # 冲突条件2: 拓扑无连接 (A !-> B) 但 语义极度相似 (A ~ B)
            # 假设 adj < 0.1 视为无连接, sim > 0.9 为语义雷同
            conflict_mask_type2 = (topo_strength < 0.1) & (sem_sim > 0.9)
            
            # 提取冲突索引
            conflict_indices_t1 = torch.nonzero(conflict_mask_type1).flatten()
            conflict_indices_t2 = torch.nonzero(conflict_mask_type2).flatten()
            
            # 格式化输出
            for idx in conflict_indices_t1[:10]: # 限制返回数量防止内存溢出
                u, v = rows[idx].item(), cols[idx].item()
                conflicts.append({
                    "node_u": u, "node_v": v, 
                    "topo_w": topo_strength[idx].item(),
                    "sem_sim": sem_sim[idx].item(),
                    "type": "StrongLink_LowSim"
                })
                
            for idx in conflict_indices_t2[:10]:
                u, v = rows[idx].item(), cols[idx].item()
                conflicts.append({
                    "node_u": u, "node_v": v, 
                    "topo_w": topo_strength[idx].item(),
                    "sem_sim": sem_sim[idx].item(),
                    "type": "NoLink_HighSim"
                })
                
        logger.info(f"检测完成。发现 {len(conflicts)} 个潜在逻辑冲突。")
        return conflicts

    def generate_falsification_vector(self, node_features: Tensor, adj_matrix: Tensor, 
                                      conflict_target: Dict[str, int], 
                                      epsilon: float = 0.05) -> Tuple[Tensor, float]:
        """
        核心函数2：生成自证伪向量（对抗性扰动）。
        
        针对特定的冲突节点对，计算一个梯度方向的扰动，试图改变当前的拓扑一致性得分，
        从而测试网络是否能通过微调来"修复"或"加剧"该冲突。
        
        Args:
            node_features: 原始节点特征.
            adj_matrix: 邻接矩阵.
            conflict_target: 包含 'node_u' 和 'node_v' 的字典.
            epsilon: 扰动系数.
            
        Returns:
            (perturbed_features, impact_score): 扰动后的特征和影响得分。
        """
        u, v = conflict_target['node_u'], conflict_target['node_v']
        
        # 确保梯度追踪开启
        feats = node_features.clone().detach().requires_grad_(True).to(self.device)
        adj = adj_matrix.to(self.device)
        
        self.encoder.train()
        
        # 前向传播
        h = feats
        for layer in self.encoder:
            if isinstance(layer, SimpleGNNLayer):
                h = layer(h, adj)
        
        # 计算目标损失：我们想要最大化或最小化 u 和 v 的距离，取决于冲突类型
        # 这里简单定义为：让 u 和 v 的嵌入在梯度方向上产生最大变化
        vec_u = h[u]
        vec_v = h[v]
        
        # 目标函数：余弦距离
        # Loss = 1 - CosineSimilarity(u, v)
        loss = 1 - F.cosine_similarity(vec_u.unsqueeze(0), vec_v.unsqueeze(0))
        
        # 反向传播
        loss.backward()
        
        # 获取梯度
        gradients = feats.grad.data
        
        # 生成扰动 (符号梯度攻击)
        perturbation = epsilon * gradients.sign()
        
        # 应用扰动
        perturbed_features = feats + perturbation
        perturbed_features = torch.clamp(perturbed_features, 0, 1) # 假设特征归一化在[0,1]
        
        # 计算影响得分
        with torch.no_grad():
            new_h = perturbed_features
            for layer in self.encoder:
                if isinstance(layer, SimpleGNNLayer):
                    new_h = layer(new_h, adj)
            
            new_sim = F.cosine_similarity(new_h[u].unsqueeze(0), new_h[v].unsqueeze(0)).item()
            impact_score = abs(loss.item() - (1 - new_sim))
            
        logger.info(f"生成证伪向量: Nodes ({u}, {v}), 扰动影响得分: {impact_score:.4f}")
        
        return perturbed_features.cpu().detach(), impact_score


# 辅助函数
def create_synthetic_knowledge_graph(num_nodes: int, dim: int, sparsity: float = 0.01) -> Tuple[Tensor, Tensor]:
    """
    辅助函数：生成用于测试的合成知识图谱数据。
    
    Args:
        num_nodes: 节点数量。
        dim: 特征维度。
        sparsity: 邻接矩阵稀疏度 (0-1)。
        
    Returns:
        (node_features, adj_matrix)
    """
    if not (0 < sparsity < 1):
        raise ValueError("Sparsity must be between 0 and 1")
        
    logger.info(f"生成合成数据: Nodes={num_nodes}, Dim={dim}, Sparsity={sparsity}")
    
    # 1. 生成随机特征
    features = torch.rand(num_nodes, dim)
    
    # 2. 生成随机邻接矩阵 (模拟随机知识网络)
    adj = torch.rand(num_nodes, num_nodes)
    
    # 3. 应用稀疏性掩码
    mask = torch.rand(num_nodes, num_nodes) > (1 - sparsity)
    adj = adj * mask.float()
    
    # 4. 对称化 (无向图) 并设置对角线为0
    adj = (adj + adj.T) / 2
    adj.fill_diagonal_(0)
    
    # 5. 人工注入一些冲突 (强连接，低特征相似度)
    # 随机选择几对节点，强制连接，但让特征正交
    for _ in range(5):
        u, v = random.randint(0, num_nodes-1), random.randint(0, num_nodes-1)
        if u == v: continue
        adj[u, v] = 1.0
        adj[v, u] = 1.0
        # 让特征正交 (简单的反转)
        features[v] = -features[u] + torch.randn(dim) * 0.1
        
    return features, adj

# 使用示例
if __name__ == "__main__":
    # 1. 初始化参数
    N = 1500  # 大规模网络节点数
    D = 128
    
    # 2. 生成测试数据
    try:
        feats, adj = create_synthetic_knowledge_graph(N, D)
        
        # 3. 初始化验证系统
        validator = TopologyConsistencyValidator(node_count=N, embedding_dim=D)
        
        # 4. 检测冲突
        conflicts = validator.detect_conflicts(feats, adj)
        
        # 5. 如果发现冲突，生成证伪向量
        if conflicts:
            target_conflict = conflicts[0]
            print(f"\n--- 开始证伪测试: 目标节点 {target_conflict['node_u']} - {target_conflict['node_v']} ---")
            print(f"原始状态: 拓扑权重 {target_conflict['topo_w']:.2f}, 语义相似度 {target_conflict['sem_sim']:.2f}")
            
            perturbed_feats, impact = validator.generate_falsification_vector(
                feats, adj, target_conflict
            )
            print(f"证伪向量已生成，对语义空间造成的扰动影响: {impact:.4f}")
        else:
            print("未检测到显著的逻辑冲突。")
            
    except Exception as e:
        logger.exception(f"运行时发生错误: {e}")