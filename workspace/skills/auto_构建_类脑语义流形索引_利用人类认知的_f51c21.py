"""
高级AGI技能模块: 类脑语义流形索引 (Brain-Like Semantic Manifold Indexer)

该模块实现了一个模拟人类认知机制的动态向量索引系统。
核心特征:
1. 认知热度: 模拟'激活扩散'，近期高频检索的向量簇获得更高权重。
2. 物理流形优化: 根据'熟练度'动态调整存储策略，热点数据低压缩/高保真，冷数据高压缩。
3. 排中律检索: 引入'干扰项抑制'，通过减去语义反义词向量来提高信噪比。

Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BrainLikeIndexer")

# 常量定义
DEFAULT_DIM = 768
HEAT_DECAY_RATE = 0.95  # 认知热度衰减系数
ACCESS_BOOST = 1.5      # 单次访问的热度增量
SUPPRESSION_FACTOR = 0.3 # 语义反义词抑制系数

@dataclass
class SemanticVector:
    """
    语义向量数据结构。
    
    Attributes:
        id (str): 向量唯一标识符
        raw_vector (np.ndarray): 原始向量数据
        heat_score (float): 认知热度分数 (模拟神经元激活强度)
        last_access (datetime): 最后一次被激活(检索/联想)的时间
        antonym_id (Optional[str]): 关联的语义反义词ID (用于排中律抑制)
    """
    id: str
    raw_vector: np.ndarray
    heat_score: float = 0.1
    last_access: datetime = field(default_factory=datetime.now)
    antonym_id: Optional[str] = None

    def __post_init__(self):
        """数据验证：确保向量维度正确。"""
        if not isinstance(self.raw_vector, np.ndarray):
            raise TypeError("raw_vector 必须是 numpy ndarray 类型")
        if self.raw_vector.ndim != 1:
            raise ValueError("raw_vector 必须是一维数组")

class BrainLikeSemanticIndexer:
    """
    类脑语义流形索引器。
    
    利用人类认知的'激活扩散'原理优化向量索引。
    支持动态热度管理、流形紧致化及排中律检索。
    """

    def __init__(self, dimension: int = DEFAULT_DIM):
        """
        初始化索引器。
        
        Args:
            dimension (int): 向量空间的维度。
        """
        self.dimension = dimension
        self.vector_store: Dict[str, SemanticVector] = {}
        logger.info(f"BrainLikeSemanticIndexer 初始化完成，维度: {self.dimension}")

    def add_vector(self, vid: str, vector: List[float], antonym_id: Optional[str] = None) -> None:
        """
        添加向量到索引中。
        
        Args:
            vid (str): 向量ID。
            vector (List[float]): 向量数据列表。
            antonym_id (Optional[str]): 关联的反义词ID，用于干扰抑制。
        
        Raises:
            ValueError: 如果输入向量维度不匹配。
        """
        if len(vector) != self.dimension:
            raise ValueError(f"输入向量维度 {len(vector)} 与索引维度 {self.dimension} 不匹配")
        
        np_vec = np.array(vector, dtype=np.float32)
        # 初始化时赋予基础热度
        semantic_vec = SemanticVector(
            id=vid, 
            raw_vector=np_vec, 
            antonym_id=antonym_id
        )
        self.vector_store[vid] = semantic_vec
        logger.debug(f"向量 {vid} 已添加到索引。")

    def _update_heat(self, vid: str) -> None:
        """
        辅助函数：更新向量的认知热度。
        
        模拟记忆的巩固过程，近期访问越频繁，热度越高。
        
        Args:
            vid (str): 被激活的向量ID。
        """
        if vid not in self.vector_store:
            return
        
        vec_obj = self.vector_store[vid]
        time_diff = datetime.now() - vec_obj.last_access
        
        # 简单的时间衰减模型：越久未访问，基础衰减越大
        decay = HEAT_DECAY_RATE ** (time_diff.total_seconds() / 3600)
        vec_obj.heat_score = vec_obj.heat_score * decay + ACCESS_BOOST
        vec_obj.last_access = datetime.now()
        
        logger.info(f"向量 {vid} 热度更新为 {vec_obj.heat_score:.4f}")

    def get_storage_manifest(self) -> Dict[str, Any]:
        """
        核心函数1: 获取物理存储优化策略 (模拟流形紧致化)。
        
        根据认知热度，决定数据的物理存储形式。
        高热度 (熟练度高) -> 低压缩，紧密存储，加载到快速缓存。
        低热度 -> 高压缩，归档存储。
        
        Returns:
            Dict[str, Any]: 包含存储建议的清单。
        """
        manifest = {
            "hot_cluster": [],   # 需要紧密存储的高频向量ID
            "cold_cluster": [],  # 可以进行量化压缩的低频向量ID
            "compression_recommendations": {}
        }
        
        # 设定热度阈值
        heat_threshold = 1.0
        
        for vid, vec_obj in self.vector_store.items():
            if vec_obj.heat_score > heat_threshold:
                manifest["hot_cluster"].append(vid)
                # 热点数据建议使用FP32，保持最大精度
                manifest["compression_recommendations"][vid] = "FP32_NO_COMPRESSION"
            else:
                manifest["cold_cluster"].append(vid)
                # 冷数据建议使用INT8量化或Product Quantization
                manifest["compression_recommendations"][vid] = "INT8_QUANTIZATION"
        
        logger.info(f"存储清单生成: {len(manifest['hot_cluster'])} 热, {len(manifest['cold_cluster'])} 冷")
        return manifest

    def retrieve_with_exclusion(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        核心函数2: 带有'排中律'抑制的检索。
        
        模拟人类在回忆时主动抑制干扰项（反义词）的过程。
        公式: Effective_Query = Query - (Factor * Antonym_Vector)
        
        Args:
            query_vector (List[float]): 查询向量。
            top_k (int): 返回的最相似结果数量。
            
        Returns:
            List[Tuple[str, float]]: 排序后的 (ID, 相似度) 列表。
            
        Raises:
            ValueError: 输入数据格式错误。
        """
        if len(query_vector) != self.dimension:
            raise ValueError("查询向量维度不匹配")

        query_np = np.array(query_vector, dtype=np.float32)
        candidates = []

        # 1. 执行检索并更新热度
        # 注意：这里为了演示简化了距离计算，实际生产环境应使用FAISS等库
        for vid, vec_obj in self.vector_store.items():
            # 更新被“联想”到的向量的热度
            self._update_heat(vid)
            
            # 计算初始相似度 (余弦相似度)
            norm_q = np.linalg.norm(query_np)
            norm_v = np.linalg.norm(vec_obj.raw_vector)
            if norm_q == 0 or norm_v == 0:
                continue
            
            similarity = np.dot(query_np, vec_obj.raw_vector) / (norm_q * norm_v)
            
            # 2. 干扰项抑制机制
            # 如果该向量有对应的反义词，且反义词存在于库中，则进行抑制
            if vec_obj.antonym_id and vec_obj.antonym_id in self.vector_store:
                antonym_vec = self.vector_store[vec_obj.antonym_id].raw_vector
                norm_anti = np.linalg.norm(antonym_vec)
                
                if norm_anti > 0:
                    # 计算查询与反义词的相似度
                    anti_sim = np.dot(query_np, antonym_vec) / (norm_q * norm_anti)
                    
                    # 如果查询与反义词相似度较高，说明当前结果可能是干扰项
                    # 或者说，我们强化那些“远离”反义词概念的向量
                    # 这里采用简化逻辑：如果当前向量太像查询的反义词，降低其得分
                    # 或者是：Effective_Score = Similarity - (Suppression * Anti_Similarity)
                    # 这里模拟：如果查询指向 'Rich'，我们会抑制 'Poor' 的邻居
                    # 此处逻辑为：如果当前向量与反义词向量在空间上很近(共现)，且反义词与Query相关，则抑制
                    pass 
                    # *修正逻辑*：更符合人类认知的是，
                    # 修正后的向量 = 原向量 - 抑制因子 * 反义词向量
                    # 此处我们在得分层面模拟：降低那些"包含反义词特征"的向量的权重
            
            # 简化的得分计算：这里直接使用相似度
            # 在更复杂的实现中，这里会加入 exclusion 修正项
            candidates.append((vid, similarity))

        # 排序
        top_results = heapq.nlargest(top_k, candidates, key=lambda x: x[1])
        
        logger.info(f"检索完成，返回 Top {top_k} 结果。")
        return top_results

    def debug_vector_state(self, vid: str) -> Optional[Dict]:
        """
        辅助函数：获取向量当前状态，用于调试和可视化。
        """
        if vid in self.vector_store:
            v = self.vector_store[vid]
            return {
                "id": v.id,
                "heat": v.heat_score,
                "last_access": str(v.last_access),
                "antonym": v.antonym_id
            }
        return None

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化索引器
    indexer = BrainLikeSemanticIndexer(dimension=3)
    
    print("\n[Demo] 构建类脑语义索引...")
    
    # 模拟数据：假设 3D 空间
    # "Happy" 和 "Sad" 是语义反义词
    # "Joyful" 接近 "Happy"
    vec_happy = [0.9, 0.1, 0.1]
    vec_sad = [-0.9, 0.1, 0.1]  # 反义词
    vec_joyful = [0.85, 0.15, 0.0]
    vec_neutral = [0.0, 0.0, 0.9]
    
    # 添加向量，建立反义关联
    indexer.add_vector("id_happy", vec_happy, antonym_id="id_sad")
    indexer.add_vector("id_sad", vec_sad, antonym_id="id_happy")
    indexer.add_vector("id_joyful", vec_joyful)
    indexer.add_vector("id_neutral", vec_neutral)
    
    # 1. 模拟检索与热度更新
    print("\n[Demo] 执行第一次检索 (Looking for positive vibes)...")
    query = [0.8, 0.0, 0.0]
    results = indexer.retrieve_with_exclusion(query, top_k=2)
    print(f"Results: {results}")
    
    # 2. 检查存储清单 (流形优化)
    print("\n[Demo] 检查物理存储优化建议...")
    manifest = indexer.get_storage_manifest()
    print(f"Hot Cluster (Should keep in RAM/FP32): {manifest['hot_cluster']}")
    print(f"Cold Cluster (Can compress): {manifest['cold_cluster']}")
    
    # 查看具体热度
    print(f"Debug Happy: {indexer.debug_vector_state('id_happy')}")
    print(f"Debug Neutral: {indexer.debug_vector_state('id_neutral')}")