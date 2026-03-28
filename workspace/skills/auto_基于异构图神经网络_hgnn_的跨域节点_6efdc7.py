"""
模块: auto_基于异构图神经网络_hgnn_的跨域节点_6efdc7
描述: 基于异构图神经网络（HGNN）的跨域节点注意力机制实现。
      该模块实现了动态权重算法，用于计算跨认知域节点间的语义与结构相似度，
      并通过注意力机制发现潜在的异构映射关系。
"""

import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeConfig:
    """节点配置数据类，用于存储图节点的元信息"""
    node_id: str
    domain: str
    feature_vector: torch.Tensor
    structural_index: int

class SemanticEncoder(nn.Module):
    """
    语义编码器：将原始节点特征映射到统一的语义空间
    """
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)

class StructuralEncoder(nn.Module):
    """
    结构编码器：提取节点的结构特征
    """
    def __init__(self, num_nodes: int, embed_dim: int):
        super().__init__()
        self.embedding = nn.Embedding(num_nodes, embed_dim)
        
    def forward(self, node_indices: torch.Tensor) -> torch.Tensor:
        return self.embedding(node_indices)

class CrossDomainAttention(nn.Module):
    """
    核心跨域注意力机制实现
    """
    def __init__(self, semantic_dim: int, structural_dim: int, attention_heads: int = 4):
        super().__init__()
        self.attention_heads = attention_heads
        self.head_dim = semantic_dim // attention_heads
        
        # 确保语义维度能被注意力头数整除
        assert semantic_dim % attention_heads == 0, "Semantic dimension must be divisible by attention heads"
        
        # 查询、键、值投影层
        self.q_proj = nn.Linear(semantic_dim, semantic_dim)
        self.k_proj = nn.Linear(semantic_dim, semantic_dim)
        self.v_proj = nn.Linear(semantic_dim, semantic_dim)
        
        # 结构融合层
        self.struct_fusion = nn.Linear(structural_dim, semantic_dim)
        
        # 输出层
        self.out_proj = nn.Linear(semantic_dim, semantic_dim)
        
    def forward(
        self, 
        query: torch.Tensor, 
        key: torch.Tensor, 
        value: torch.Tensor,
        struct_features: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        参数:
            query: 查询节点特征 [batch_size, seq_len, semantic_dim]
            key: 键节点特征 [batch_size, seq_len, semantic_dim]
            value: 值节点特征 [batch_size, seq_len, semantic_dim]
            struct_features: 结构特征 [batch_size, seq_len, structural_dim]
            
        返回:
            Tuple[输出特征, 注意力权重]
        """
        batch_size = query.size(0)
        
        # 融合结构特征
        struct_fused = self.struct_fusion(struct_features)
        query = query + struct_fused
        
        # 投影到多头注意力空间
        Q = self.q_proj(query).view(batch_size, -1, self.attention_heads, self.head_dim).transpose(1, 2)
        K = self.k_proj(key).view(batch_size, -1, self.attention_heads, self.head_dim).transpose(1, 2)
        V = self.v_proj(value).view(batch_size, -1, self.attention_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim ** 0.5)
        attn_weights = F.softmax(scores, dim=-1)
        
        # 应用注意力权重
        context = torch.matmul(attn_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.attention_heads * self.head_dim)
        
        output = self.out_proj(context)
        return output, attn_weights

class HGNNCrossDomainMapper(nn.Module):
    """
    完整的跨域节点映射系统
    """
    def __init__(
        self,
        num_nodes: int,
        input_dim: int,
        semantic_dim: int,
        structural_dim: int,
        domain_map: Dict[str, int],
        attention_heads: int = 4
    ):
        super().__init__()
        self.semantic_encoder = SemanticEncoder(input_dim, semantic_dim, semantic_dim)
        self.structural_encoder = StructuralEncoder(num_nodes, structural_dim)
        self.cross_attention = CrossDomainAttention(semantic_dim, structural_dim, attention_heads)
        self.domain_classifier = nn.Linear(semantic_dim, len(domain_map))
        self.domain_map = domain_map
        
    def forward(
        self, 
        node_features: torch.Tensor,
        node_indices: torch.Tensor,
        adj_matrix: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        参数:
            node_features: 节点特征 [batch_size, num_nodes, input_dim]
            node_indices: 节点索引 [batch_size, num_nodes]
            adj_matrix: 邻接矩阵 [batch_size, num_nodes, num_nodes] (可选)
            
        返回:
            Tuple[映射特征, 注意力权重, 域预测]
        """
        # 编码语义和结构特征
        semantic_feats = self.semantic_encoder(node_features)
        structural_feats = self.structural_encoder(node_indices)
        
        # 应用跨域注意力
        mapped_feats, attn_weights = self.cross_attention(
            semantic_feats, semantic_feats, semantic_feats, structural_feats
        )
        
        # 域分类
        domain_preds = self.domain_classifier(mapped_feats)
        
        return mapped_feats, attn_weights, domain_preds
    
    def discover_mappings(
        self, 
        node_configs: List[NodeConfig],
        threshold: float = 0.7
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        发现跨域映射关系
        
        参数:
            node_configs: 节点配置列表
            threshold: 映射关系阈值
            
        返回:
            映射关系字典 {source_node: [(target_node, score), ...]}
        """
        # 验证输入
        if not node_configs:
            raise ValueError("Node configs cannot be empty")
            
        # 准备批量数据
        features = torch.stack([nc.feature_vector for nc in node_configs])
        indices = torch.tensor([nc.structural_index for nc in node_configs])
        
        # 获取映射特征
        with torch.no_grad():
            mapped_feats, attn_weights, _ = self.forward(features.unsqueeze(0), indices.unsqueeze(0))
        
        # 计算相似度矩阵
        similarity_matrix = F.cosine_similarity(
            mapped_feats.unsqueeze(2), 
            mapped_feats.unsqueeze(1), 
            dim=-1
        ).squeeze(0)
        
        # 发现跨域映射
        mappings = {}
        for i, source in enumerate(node_configs):
            source_mappings = []
            for j, target in enumerate(node_configs):
                if source.domain != target.domain:  # 只考虑跨域映射
                    score = similarity_matrix[i, j].item()
                    if score >= threshold:
                        source_mappings.append((target.node_id, score))
            
            if source_mappings:
                mappings[source.node_id] = sorted(source_mappings, key=lambda x: x[1], reverse=True)
                
        return mappings

def validate_node_config(config: NodeConfig) -> bool:
    """
    验证节点配置的有效性
    
    参数:
        config: 节点配置对象
        
    返回:
        bool: 是否有效
    """
    if not isinstance(config, NodeConfig):
        logger.error(f"Invalid config type: {type(config)}")
        return False
        
    if not isinstance(config.node_id, str) or not config.node_id.strip():
        logger.error("Invalid node_id")
        return False
        
    if not isinstance(config.domain, str) or not config.domain.strip():
        logger.error("Invalid domain")
        return False
        
    if not isinstance(config.feature_vector, torch.Tensor):
        logger.error("Feature vector must be a torch.Tensor")
        return False
        
    if config.feature_vector.dim() != 1:
        logger.error("Feature vector must be 1-dimensional")
        return False
        
    if not isinstance(config.structural_index, int) or config.structural_index < 0:
        logger.error("Structural index must be a non-negative integer")
        return False
        
    return True

# 使用示例
"""
# 初始化参数
num_nodes = 3613
input_dim = 128
semantic_dim = 64
structural_dim = 32
domain_map = {'cooking': 0, 'programming': 1, 'sales': 2, 'emotion': 3}

# 创建模型实例
model = HGNNCrossDomainMapper(
    num_nodes=num_nodes,
    input_dim=input_dim,
    semantic_dim=semantic_dim,
    structural_dim=structural_dim,
    domain_map=domain_map
)

# 创建测试节点配置
node_configs = [
    NodeConfig(
        node_id="fire_control",
        domain="cooking",
        feature_vector=torch.randn(input_dim),
        structural_index=0
    ),
    NodeConfig(
        node_id="emotion_management",
        domain="emotion",
        feature_vector=torch.randn(input_dim),
        structural_index=1
    ),
    NodeConfig(
        node_id="code_optimization",
        domain="programming",
        feature_vector=torch.randn(input_dim),
        structural_index=2
    )
]

# 发现跨域映射
try:
    mappings = model.discover_mappings(node_configs, threshold=0.6)
    for source, targets in mappings.items():
        print(f"Source: {source}")
        for target, score in targets:
            print(f"  -> {target}: {score:.4f}")
except ValueError as e:
    print(f"Error: {e}")
"""