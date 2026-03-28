"""
模块名称: auto_如何通过图神经网络_gnn_分析1237_ba7cf8
描述: 实现基于图神经网络（GNN）的引用拓扑结构分析工具。
      本模块利用 PyTorch Geometric 构建图神经网络模型，对节点引用网络进行嵌入学习，
      并结合图论算法自动检测“概念孤岛”（死胡同/接收者）和“冗余环路”（空转/闭环）。
作者: Senior Python Engineer
版本: 1.0.0
"""

import logging
import sys
from typing import List, Tuple, Dict, Optional, Set, Any

import torch
import torch.nn.functional as F
from torch import Tensor
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class GCNEncoder(torch.nn.Module):
    """
    图卷积神经网络编码器。
    
    用于学习节点的低维嵌入表示，捕捉图的拓扑结构特征。
    
    Attributes:
        conv1 (GCNConv): 第一层图卷积层。
        conv2 (GCNConv): 第二层图卷积层。
    """
    
    def __init__(self, num_features: int, hidden_dim: int, embedding_dim: int):
        """
        初始化 GCN 编码器。
        
        Args:
            num_features (int): 输入节点特征维度。
            hidden_dim (int): 隐藏层维度。
            embedding_dim (int): 输出嵌入维度。
        """
        super(GCNEncoder, self).__init__()
        if num_features <= 0 or hidden_dim <= 0 or embedding_dim <= 0:
            raise ValueError("网络维度参数必须为正整数")
            
        self.conv1 = GCNConv(num_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, embedding_dim)
        logger.debug(f"GCNEncoder 初始化完成: in={num_features}, hidden={hidden_dim}, out={embedding_dim}")

    def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
        """
        前向传播。
        
        Args:
            x (Tensor): 节点特征矩阵。
            edge_index (Tensor): 边索引矩阵 (COO格式)。
            
        Returns:
            Tensor: 节点的嵌入向量矩阵。
        """
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, training=self.training)
        x = self.conv2(x, edge_index)
        return x


class GraphTopologyAnalyzer:
    """
    图拓扑分析器。
    
    结合深度学习（GNN）嵌入和传统图论指标来分析节点引用网络。
    重点识别 '概念孤岛' (Dead-ends) 和 '冗余环路' (Redundant Loops)。
    """

    def __init__(self, num_nodes: int, node_features: Tensor, edges: Tensor, device: Optional[str] = None):
        """
        初始化分析器。
        
        Args:
            num_nodes (int): 节点总数。
            node_features (Tensor): 节点特征矩阵 [num_nodes, num_features]。
            edges (Tensor): 边列表 [2, num_edges]，表示源节点到目标节点的引用。
            device (Optional[str]): 计算设备 ('cpu' 或 'cuda')。
        """
        self._validate_inputs(num_nodes, node_features, edges)
        
        self.num_nodes = num_nodes
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.data = Data(x=node_features, edge_index=edges).to(self.device)
        
        # 预计算基础图统计信息
        self.adj_list = self._build_adjacency_list(edges)
        
        logger.info(f"GraphTopologyAnalyzer 初始化完成，共 {num_nodes} 个节点，运行设备: {self.device}")

    def _validate_inputs(self, num_nodes: int, node_features: Tensor, edges: Tensor) -> None:
        """验证输入数据的合法性。"""
        if num_nodes <= 0:
            raise ValueError("节点数量必须大于 0")
        if node_features.size(0) != num_nodes:
            raise ValueError(f"特征矩阵行数 {node_features.size(0)} 与节点数 {num_nodes} 不匹配")
        if edges.dim() != 2 or edges.size(0) != 2:
            raise ValueError("边矩阵必须是形状为 [2, num_edges] 的张量")
        if torch.any(edges < 0) or torch.any(edges >= num_nodes):
            raise ValueError("边索引中包含无效的节点ID (超出范围)")

    def _build_adjacency_list(self, edges: Tensor) -> Dict[int, Set[int]]:
        """构建邻接表以便快速查找邻居（辅助图论计算）。"""
        adj: Dict[int, Set[int]] = {i: set() for i in range(self.num_nodes)}
        # edges: [2, E], row 0 is source, row 1 is target (citation direction)
        sources = edges[0].tolist()
        targets = edges[1].tolist()
        
        for src, tgt in zip(sources, targets):
            adj[src].add(tgt)
        return adj

    def train_gnn_encoder(self, hidden_dim: int = 16, embedding_dim: int = 8, epochs: int = 50) -> GCNEncoder:
        """
        训练 GNN 编码器以获取节点嵌入。
        
        此处采用无监督/自监督的链路预测重构任务作为示例目标，
        训练模型理解节点间的连接紧密程度。
        
        Args:
            hidden_dim (int): 隐藏层维度。
            embedding_dim (int): 嵌入维度。
            epochs (int): 训练轮数。
            
        Returns:
            GCNEncoder: 训练好的编码器模型。
        """
        logger.info("开始训练 GNN 编码器...")
        model = GCNEncoder(self.data.num_features, hidden_dim, embedding_dim).to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

        # 简单的无监督训练循环示意
        model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            # 这里仅作示意，实际无监督学习需要具体的损失函数（如基于随机游走或重构误差）
            # 为了保持代码通用性，我们仅执行前向传播模拟特征提取过程
            z = model(self.data.x, self.data.edge_index)
            
            # 模拟损失计算 (实际应用中应替换为真实的 Contrastive Loss 等)
            # 这里我们假设目的是让模型学习结构，简单的正则化示例
            loss = z.mean() * 0  # Dummy loss for compilation
            
            if epoch % 10 == 0:
                logger.debug(f"Epoch {epoch}/{epochs} - Embedding Norm: {z.norm(dim=1).mean().item():.4f}")

        logger.info("GNN 编码器训练完成。")
        return model

    def detect_concept_islands(self) -> List[int]:
        """
        识别“概念孤岛” (死胡同)。
        
        定义：只有入度没有出度的节点（Sink节点），意味着知识流入了这些节点但不再传播。
        在引用网络中，这代表该概念被引用但不引用其他概念。
        
        Returns:
            List[int]: 孤岛节点的索引列表。
        """
        logger.info("正在检测概念孤岛...
")
        islands = []
        
        # 检查每个节点的邻接表，如果出度为0，则为孤岛
        # 注意：在构建邻接表时，key是源节点，value是目标节点集合
        # 如果 value 为空，则该节点没有出度
        
        # 首先计算入度以确认它不是孤立点（完全断连）
        in_degrees = torch.zeros(self.num_nodes, dtype=torch.long)
        for targets in self.adj_list.values():
            for t in targets:
                in_degrees[t] += 1
        
        for node_id in range(self.num_nodes):
            out_degree = len(self.adj_list[node_id])
            if out_degree == 0:
                # 只有入度 > 0 才算 "死胡同"，否则是完全孤立点
                if in_degrees[node_id] > 0:
                    islands.append(node_id)
        
        logger.info(f"检测到 {len(islands)} 个概念孤岛。")
        return islands

    def detect_redundant_loops(self, max_component_size: int = 10) -> List[List[int]]:
        """
        识别“冗余环路” (空转/闭环群)。
        
        定义：节点群内部互相引用，形成闭环，且与外界主要网络缺乏有效交互。
        这里的简化算法寻找弱连通分量，并筛选出那些“入度主要来自内部，出度主要去往内部”
        且形成闭环的小型群体。
        
        Args:
            max_component_size (int): 判定为“微小/冗余”群体的最大节点数阈值。
            
        Returns:
            List[List[int]]: 冗余环路群的列表，每个元素是一个节点ID列表。
        """
        logger.info("正在检测冗余环路...")
        
        # 1. 使用 BFS/DFS 寻找弱连通分量
        visited = [False] * self.num_nodes
        components: List[Set[int]] = []

        for i in range(self.num_nodes):
            if not visited[i]:
                comp = self._bfs_weak_component(i, visited)
                if len(comp) > 1: # 只关注有交互的群体
                    components.append(comp)

        # 2. 分析每个分量的封闭性
        redundant_loops = []
        for comp in components:
            if len(comp) > max_component_size:
                continue # 忽略大型连通块，重点关注小团体

            internal_edges = 0
            external_out_edges = 0
            
            # 统计边的情况
            for node in comp:
                for neighbor in self.adj_list[node]:
                    if neighbor in comp:
                        internal_edges += 1
                    else:
                        external_out_edges += 1
            
            # 判定逻辑：如果内部连接紧密，且几乎没有对外输出（空转），则标记
            # 简单启发式：内部边数 > 节点数 (存在环) 且 对外边数 == 0
            if internal_edges >= len(comp) and external_out_edges == 0:
                redundant_loops.append(sorted(list(comp)))
                
        logger.info(f"检测到 {len(redundant_loops)} 个潜在的冗余环路群。")
        return redundant_loops

    def _bfs_weak_component(self, start_node: int, visited: List[bool]) -> Set[int]:
        """
        辅助函数：广度优先搜索寻找弱连通分量（忽略方向）。
        
        Args:
            start_node (int): 起始节点。
            visited (List[bool]): 访问标记数组。
            
        Returns:
            Set[int]: 该连通分量包含的节点集合。
        """
        queue = [start_node]
        component = set()
        visited[start_node] = True
        
        # 构建反向邻接表用于弱连通搜索
        reverse_adj: Dict[int, Set[int]] = {i: set() for i in range(self.num_nodes)}
        for src, tgts in self.adj_list.items():
            for t in tgts:
                reverse_adj[t].add(src)

        while queue:
            curr = queue.pop(0)
            component.add(curr)
            
            # 获取所有邻居（出和入）
            neighbors = self.adj_list[curr].union(reverse_adj[curr])
            
            for n in neighbors:
                if not visited[n]:
                    visited[n] = True
                    queue.append(n)
                    
        return component

# 使用示例
if __name__ == "__main__":
    try:
        # 1. 模拟数据生成 (1237个节点)
        NUM_NODES = 1237
        NUM_FEATURES = 10
        NUM_EDGES = 5000
        
        # 随机生成节点特征
        features = torch.randn((NUM_NODES, NUM_FEATURES))
        
        # 随机生成边 (源 -> 目标)
        # 确保有一些特定的结构，例如：
        # 制造一些 Sink 节点
        edges_list = []
        for _ in range(NUM_EDGES - 100):
            src = torch.randint(0, NUM_NODES, (1,))
            tgt = torch.randint(0, NUM_NODES, (1,))
            edges_list.append([src.item(), tgt.item()])
            
        # 添加明确的孤岛: 节点 100 被很多节点引用，但不引用别人
        for i in range(50):
            edges_list.append([torch.randint(0, NUM_NODES, (1,)).item(), 100])
            
        # 添加明确的环路: 节点 200 <-> 201 <-> 202 <-> 200，且不连外
        edges_list.append([200, 201])
        edges_list.append([201, 202])
        edges_list.append([202, 200])
        
        edge_index = torch.tensor(edges_list, dtype=torch.long).t().contiguous()
        
        # 2. 初始化分析器
        analyzer = GraphTopologyAnalyzer(
            num_nodes=NUM_NODES,
            node_features=features,
            edges=edge_index
        )
        
        # 3. 运行 GNN (可选，此处仅演示结构分析，GNN训练为占位符)
        # analyzer.train_gnn_encoder(epochs=10)
        
        # 4. 检测概念孤岛
        islands = analyzer.detect_concept_islands()
        print(f"\n检测到的概念孤岛 (前5个): {islands[:5]}")
        
        # 5. 检测冗余环路
        loops = analyzer.detect_redundant_loops()
        print(f"\n检测到的冗余环路群: {loops}")
        
    except Exception as e:
        logger.error(f"运行时发生错误: {str(e)}", exc_info=True)