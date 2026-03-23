import numpy as np
from scipy.linalg import orthogonal_procrustes
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional

class CrossDomainAlignment:
    """
    通过跨域向量对齐发现领域间隐性结构同构性并生成映射图谱
    
    该类实现以下功能:
    1. 加载两个不同领域的词向量表示
    2. 使用正交对齐技术对齐向量空间
    3. 发现领域间结构同构性
    4. 生成可视化映射图谱
    
    示例用法:
    >>> bio_vectors = {'cell': np.array([0.1, 0.2]), 'tissue': np.array([0.3, 0.4])}
    >>> city_vectors = {'building': np.array([0.5, 0.6]), 'district': np.array([0.7, 0.8])}
    >>> seed_alignments = {'cell': 'building', 'tissue': 'district'}
    >>> aligner = CrossDomainAlignment(bio_vectors, city_vectors, seed_alignments)
    >>> aligner.align_vectors()
    >>> isomorphisms = aligner.find_isomorphisms(threshold=0.7)
    >>> aligner.visualize_mapping(isomorphisms)
    """
    
    def __init__(self, domain1_vectors: Dict[str, np.ndarray], 
                 domain2_vectors: Dict[str, np.ndarray], 
                 seed_alignments: Dict[str, str]):
        """
        初始化跨域对齐器
        
        参数:
            domain1_vectors: 第一个领域的词向量字典 {词: 向量}
            domain2_vectors: 第二个领域的词向量字典 {词: 向量}
            seed_alignments: 已知对齐关系的种子词对 {领域1词: 领域2词}
            
        异常:
            ValueError: 当输入向量维度不一致或种子词不存在时抛出
        """
        self.domain1_vectors = domain1_vectors
        self.domain2_vectors = domain2_vectors
        self.seed_alignments = seed_alignments
        self.aligned_domain2 = None
        self.isomorphisms = None
        
        # 验证输入
        self._validate_inputs()
        
    def _validate_inputs(self):
        """验证输入数据的有效性"""
        # 检查向量维度一致性
        vec_dim = None
        for vec in self.domain1_vectors.values():
            if vec_dim is None:
                vec_dim = len(vec)
            elif len(vec) != vec_dim:
                raise ValueError("领域1向量维度不一致")
                
        for vec in self.domain2_vectors.values():
            if len(vec) != vec_dim:
                raise ValueError("领域2向量维度不一致")
                
        # 检查种子词是否存在
        for d1_word, d2_word in self.seed_alignments.items():
            if d1_word not in self.domain1_vectors:
                raise ValueError(f"种子词 '{d1_word}' 不在领域1中")
            if d2_word not in self.domain2_vectors:
                raise ValueError(f"种子词 '{d2_word}' 不在领域2中")
    
    def align_vectors(self):
        """
        使用正交对齐技术对齐两个领域的向量空间
        
        方法:
        1. 提取种子词向量构建对齐矩阵
        2. 应用正交Procrustes变换
        3. 对齐整个领域2的向量空间
        """
        # 提取种子词向量
        domain1_seeds = np.array([self.domain1_vectors[word] 
                                  for word in self.seed_alignments.keys()])
        domain2_seeds = np.array([self.domain2_vectors[word] 
                                  for word in self.seed_alignments.values()])
        
        # 应用正交Procrustes变换
        R, _ = orthogonal_procrustes(domain1_seeds, domain2_seeds)
        
        # 对齐整个领域2的向量
        self.aligned_domain2 = {
            word: np.dot(vec, R) 
            for word, vec in self.domain2_vectors.items()
        }
    
    def find_isomorphisms(self, threshold: float = 0.7) -> Dict[str, List[Tuple[str, float]]]:
        """
        发现领域间的结构同构性
        
        参数:
            threshold: 相似度阈值，仅返回高于此值的映射
            
        返回:
            字典 {领域1词: [(领域2词, 相似度), ...]}
            
        异常:
            ValueError: 当向量未对齐时抛出
        """
        if self.aligned_domain2 is None:
            raise ValueError("请先调用 align_vectors() 方法")
            
        # 计算所有词对的余弦相似度
        d1_words = list(self.domain1_vectors.keys())
        d2_words = list(self.aligned_domain2.keys())
        
        # 构建向量矩阵
        d1_matrix = np.array([self.domain1_vectors[word] for word in d1_words])
        d2_matrix = np.array([self.aligned_domain2[word] for word in d2_words])
        
        # 计算相似度矩阵
        sim_matrix = cosine_similarity(d1_matrix, d2_matrix)
        
        # 构建同构映射
        self.isomorphisms = {}
        for i, d1_word in enumerate(d1_words):
            # 排除种子词
            if d1_word in self.seed_alignments:
                continue
                
            # 获取相似度排序
            sim_scores = sorted(
                [(d2_words[j], sim_matrix[i, j]) for j in range(len(d2_words))],
                key=lambda x: x[1],
                reverse=True
            )
            
            # 过滤高于阈值的映射
            filtered = [(word, score) for word, score in sim_scores if score >= threshold]
            if filtered:
                self.isomorphisms[d1_word] = filtered
                
        return self.isomorphisms
    
    def visualize_mapping(self, isomorphisms: Dict[str, List[Tuple[str, float]]], 
                         output_file: Optional[str] = None):
        """
        生成领域间映射图谱可视化
        
        参数:
            isomorphisms: 同构映射字典
            output_file: 可选输出文件路径
        """
        # 创建有向图
        G = nx.DiGraph()
        
        # 添加节点和边
        for d1_word, mappings in isomorphisms.items():
            G.add_node(d1_word, domain='Domain1')
            for d2_word, score in mappings:
                G.add_node(d2_word, domain='Domain2')
                G.add_edge(d1_word, d2_word, weight=score)
        
        # 设置布局
        pos = nx.spring_layout(G)
        
        # 绘制节点
        domain1_nodes = [n for n, d in G.nodes(data=True) if d['domain'] == 'Domain1']
        domain2_nodes = [n for n, d in G.nodes(data=True) if d['domain'] == 'Domain2']
        
        nx.draw_networkx_nodes(G, pos, nodelist=domain1_nodes, node_color='skyblue', node_size=800)
        nx.draw_networkx_nodes(G, pos, nodelist=domain2_nodes, node_color='lightgreen', node_size=800)
        
        # 绘制边
        edges = G.edges(data=True)
        nx.draw_networkx_edges(G, pos, edgelist=edges, width=[d['weight']*3 for _, _, d in edges])
        
        # 添加标签
        nx.draw_networkx_labels(G, pos, font_size=10)
        
        # 添加标题
        plt.title("Cross-Domain Isomorphism Mapping", fontsize=14)
        
        # 保存或显示
        if output_file:
            plt.savefig(output_file)
            print(f"映射图谱已保存至 {output_file}")
        else:
            plt.show()
            
        plt.close()

# 示例用法
if __name__ == "__main__":
    # 示例数据 - 生物学与城市规划领域
    biology_vectors = {
        'cell': np.array([0.1, 0.2, 0.3]),
        'tissue': np.array([0.4, 0.5, 0.6]),
        'organ': np.array([0.7, 0.8, 0.9]),
        'organism': np.array([1.0, 1.1, 1.2]),
        'membrane': np.array([0.2, 0.3, 0.4]),
        'nucleus': np.array([0.5, 0.6, 0.7])
    }
    
    city_vectors = {
        'building': np.array([0.8, 0.9, 1.0]),
        'district': np.array([1.1, 1.2, 1.3]),
        'metropolis': np.array([1.4, 1.5, 1.6]),
        'infrastructure': np.array([0.9, 1.0, 1.1]),
        'zone': np.array([0.3, 0.4, 0.5]),
        'hub': np.array([0.6, 0.7, 0.8])
    }
    
    # 种子对齐关系
    seed_alignments = {
        'cell': 'building',
        'tissue': 'district',
        'organ': 'metropolis'
    }
    
    try:
        # 创建对齐器实例
        aligner = CrossDomainAlignment(biology_vectors, city_vectors, seed_alignments)
        
        # 向量对齐
        aligner.align_vectors()
        
        # 发现同构性
        isomorphisms = aligner.find_isomorphisms(threshold=0.8)
        print("发现的同构映射:")
        for word, mappings in isomorphisms.items():
            print(f"{word} -> {mappings}")
        
        # 可视化映射
        aligner.visualize_mapping(isomorphisms, "cross_domain_mapping.png")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")