"""
Module: auto_左右跨域重叠_异质概念迁移的零样本结构_060ac6
Description: 【左右跨域重叠】异质概念迁移的零样本结构映射。
             本模块实现了在不同语义向量空间之间寻找深层结构同构性的算法，
             用于验证和生成跨域的零样本策略迁移（例如：生物免疫 -> 网络安全）。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError, field_validator
from scipy.spatial.distance import cosine
from scipy.linalg import orthogonal_procrustes

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class DomainConcept(BaseModel):
    """领域概念数据模型，包含概念名称及其高维向量表示。"""
    name: str = Field(..., description="概念的名称，如 'T-Cell' 或 'Firewall'")
    vector: List[float] = Field(..., description="概念的高维嵌入向量")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="概念的非结构性属性")

    @field_validator('vector')
    def check_vector_dimension(cls, v):
        if not v:
            raise ValueError("Vector cannot be empty")
        return v

class MappedPair(BaseModel):
    """映射结果模型，表示源域概念与目标域概念的对齐关系。"""
    source_concept: str
    target_concept: str
    similarity_score: float
    structural_role: str

# --- 核心类 ---

class CrossDomainMapper:
    """
    处理异质概念迁移和结构映射的核心类。
    
    使用Procrustes分析等方法，在向量空间中寻找源域和目标域之间的最佳旋转对齐，
    从而发现深层同构性，即使表面语义无关。
    """

    def __init__(self, dim_threshold: int = 10):
        """
        初始化映射器。
        
        Args:
            dim_threshold (int): 向量维度的最小阈值，低于此值将拒绝处理。
        """
        self.dim_threshold = dim_threshold
        self.alignment_matrix: Optional[np.ndarray] = None
        logger.info("CrossDomainMapper initialized with dim_threshold: %d", dim_threshold)

    def _validate_domains(self, source: List[DomainConcept], target: List[DomainConcept]) -> Tuple[np.ndarray, np.ndarray]:
        """
        辅助函数：验证数据并转换为矩阵格式。
        
        Args:
            source: 源域概念列表
            target: 目标域概念列表
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: 源矩阵和目标矩阵
            
        Raises:
            ValueError: 如果数据为空或维度不匹配
        """
        if not source or not target:
            raise ValueError("Source and Target domains cannot be empty.")
        
        src_vectors = [c.vector for c in source]
        tgt_vectors = [c.vector for c in target]
        
        src_dim = len(src_vectors[0])
        tgt_dim = len(tgt_vectors[0])
        
        if src_dim != tgt_dim:
            raise ValueError(f"Dimension mismatch: Source ({src_dim}) vs Target ({tgt_dim})")
            
        if src_dim < self.dim_threshold:
            logger.warning("Vector dimension is very low, structural mapping may be inaccurate.")
            
        logger.debug("Data validation passed. Matrix shapes: Source %s, Target %s", 
                     np.array(src_vectors).shape, np.array(tgt_vectors).shape)
        
        return np.array(src_vectors), np.array(tgt_vectors)

    def align_structural_topology(self, source: List[DomainConcept], target: List[DomainConcept]) -> np.ndarray:
        """
        核心函数1：计算跨域的结构拓扑对齐。
        
        使用正交Procrustes分析寻找一个旋转矩阵，使得源域向量空间在旋转后
        与目标域向量空间的重叠度（结构相似性）最大化。
        
        Args:
            source (List[DomainConcept]): 源域概念集合（如生物免疫系统）
            target (List[DomainConcept]): 目标域概念集合（如计算机网络防火墙）
            
        Returns:
            np.ndarray: 对齐矩阵（变换矩阵），用于将源域概念映射到目标域空间。
        """
        logger.info("Starting structural topology alignment...")
        try:
            src_matrix, tgt_matrix = self._validate_domains(source, target)
            
            # 为了进行Procrustes分析，我们需要配对的锚点。
            # 在零样本场景下，我们假设前N个概念是潜在的锚点（或随机采样），
            # 或者使用无监督的迭代对齐。这里简化为假设输入已按潜在结构排序或使用全量数据进行粗略对齐。
            # 注意：实际AGI场景中，这里应包含寻找锚点的启发式算法。
            min_len = min(len(src_matrix), len(tgt_matrix))
            
            # 计算正交Procrustes问题
            # 寻找矩阵R，使得 ||A @ R - B||_F 最小
            R, _ = orthogonal_procrustes(src_matrix[:min_len], tgt_matrix[:min_len])
            
            self.alignment_matrix = R
            logger.info("Alignment matrix computed successfully. Shape: %s", R.shape)
            return R
            
        except Exception as e:
            logger.error("Error during structural alignment: %s", str(e))
            raise

    def discover_isomorphic_mappings(self, source: List[DomainConcept], target: List[DomainConcept], top_k: int = 3) -> List[MappedPair]:
        """
        核心函数2：基于对齐的空间发现同构概念映射并生成策略。
        
        将源域概念变换到目标域空间后，计算最近邻，发现结构相似的概念。
        
        Args:
            source (List[DomainConcept]): 源域概念
            target (List[DomainConcept]): 目标域概念
            top_k (int): 返回的最匹配数量
            
        Returns:
            List[MappedPair]: 映射关系列表
        """
        if self.alignment_matrix is None:
            logger.warning("Alignment matrix not found. Running alignment first.")
            self.align_structural_topology(source, target)
            
        logger.info("Discovering isomorphic mappings...")
        
        src_matrix, tgt_matrix = self._validate_domains(source, target)
        tgt_names = [c.name for c in target]
        
        # 变换源域向量
        transformed_src = src_matrix @ self.alignment_matrix
        
        results = []
        
        # 对每个源概念寻找目标域中的最近邻
        for i, src_concept in enumerate(source):
            src_vec = transformed_src[i]
            
            # 计算与所有目标向量的余弦相似度
            similarities = []
            for j, tgt_vec in enumerate(tgt_matrix):
                # 余弦相似度 = 1 - 余弦距离
                sim = 1 - cosine(src_vec, tgt_vec)
                similarities.append((tgt_names[j], sim))
            
            # 排序获取 Top K
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 取最高分作为主要映射
            best_match_name, best_score = similarities[0]
            
            # 简单的策略生成逻辑（示例）
            role = "Unknown"
            if best_score > 0.8:
                role = "Functional Isomorph (High Confidence)"
            elif best_score > 0.6:
                role = "Structural Analog (Medium Confidence)"
            
            result = MappedPair(
                source_concept=src_concept.name,
                target_concept=best_match_name,
                similarity_score=round(best_score, 4),
                structural_role=role
            )
            results.append(result)
            logger.debug(f"Mapped {src_concept.name} -> {best_match_name} (Score: {best_score:.4f})")
            
        return results

# --- 使用示例 ---

def generate_mock_data(n_samples: int = 10, dim: int = 128) -> Tuple[List[DomainConcept], List[DomainConcept]]:
    """
    辅助函数：生成模拟的向量数据用于演示。
    在真实场景中，这些向量应来自Bert/GPT等Encoder。
    """
    # 模拟源域：免疫系统
    source_names = ["Antigen", "B-Cell", "T-Cell", "Antibody", "MemoryCell"]
    # 模拟目标域：网络安全 (结构上故意与源域对齐，但语义无关)
    target_names = ["Malware", "IDS_Scanner", "Firewall_Rule", "Block_Action", "Log_History"]
    
    # 生成随机向量，但为了演示"同构性"，我们让对应位置的向量有相似的分布特征
    source_data = []
    target_data = []
    
    base_vectors = np.random.randn(len(source_names), dim)
    
    for i, name in enumerate(source_names):
        # 源向量 = 基础向量 + 噪声
        vec = base_vectors[i] + np.random.normal(0, 0.1, dim)
        source_data.append(DomainConcept(name=name, vector=vec.tolist()))
        
    for i, name in enumerate(target_names):
        # 目标向量 = 基础向量 + 不同的噪声 (模拟结构相似但语义不同)
        vec = base_vectors[i] + np.random.normal(0, 0.1, dim)
        target_data.append(DomainConcept(name=name, vector=vec.tolist()))
        
    return source_data, target_data

if __name__ == "__main__":
    # 示例执行流程
    print("--- Generating Mock Data for Immune System & Cyber Security ---")
    src_domain, tgt_domain = generate_mock_data()
    
    mapper = CrossDomainMapper(dim_threshold=50)
    
    try:
        # 1. 对齐结构
        print("\n1. Aligning Structural Topology...")
        mapper.align_structural_topology(src_domain, tgt_domain)
        
        # 2. 发现映射
        print("\n2. Discovering Isomorphic Mappings...")
        mappings = mapper.discover_isomorphic_mappings(src_domain, tgt_domain)
        
        print("\n--- Results: Cross-Domain Mappings ---")
        for m in mappings:
            print(f"Source: {m.source_concept:<15} -> Target: {m.target_concept:<15} "
                  f"| Similarity: {m.similarity_score:.4f} | Role: {m.structural_role}")
                  
        print("\nInterpretation: AI has detected that 'T-Cell' structurally maps to 'Firewall_Rule' "
              "in the vector space, suggesting a potential strategy transfer.")
              
    except ValidationError as ve:
        logger.error(f"Data validation failed: {ve}")
    except ValueError as ve:
        logger.error(f"Processing error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")