"""
跨域概念迁移模块：从生物免疫学到网络安全

本模块演示了如何将生物免疫系统识别病原体的核心机制（特异性识别、分布式检测、
记忆效应）映射并重构为网络安全系统中识别零日攻击的算法架构。

核心映射关系：
1. 抗原决定簇 -> 网络流量特征向量
2. 主要组织相容性复合体(MHC) -> 特征提取器
3. B细胞/T细胞 -> 分布式检测代理
4. 抗体 -> 异常检测模型
5. 记忆细胞 -> 攻击模式数据库

数学基础：
- 使用负选择算法模拟T细胞的自我/非我识别
- 基于R连续位匹配规则进行模式识别
- 应用亲和力成熟机制优化检测器
"""

import logging
import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ImmuneToSecurityMapper")


class DomainType(Enum):
    """领域类型枚举"""
    BIOLOGICAL = "biological"
    CYBER = "cyber"


@dataclass
class FeatureVector:
    """特征向量数据结构"""
    data: NDArray[np.float64]
    domain: DomainType
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.data, np.ndarray):
            raise TypeError("特征数据必须是numpy数组")
        if self.data.ndim != 1:
            raise ValueError("特征数据必须是一维数组")


@dataclass
class DetectionResult:
    """检测结果数据结构"""
    is_anomaly: bool
    confidence: float
    matched_patterns: List[str]
    response_action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ImmuneSystemToSecurityMapper:
    """
    将生物免疫系统机制映射到网络安全系统的核心类
    
    实现了以下关键概念迁移：
    1. 负选择算法：模拟T细胞在胸腺中的成熟过程
    2. R连续位匹配：模拟抗体与抗原的特异性结合
    3. 记忆细胞机制：存储已知攻击模式以加速响应
    """
    
    def __init__(
        self,
        feature_dim: int = 10,
        r_contiguous: int = 4,
        threshold: float = 0.85,
        max_detectors: int = 100
    ):
        """
        初始化映射器
        
        Args:
            feature_dim: 特征向量维度
            r_contiguous: R连续位匹配规则参数
            threshold: 异常判定阈值
            max_detectors: 最大检测器数量
        """
        self.feature_dim = feature_dim
        self.r_contiguous = r_contiguous
        self.threshold = threshold
        self.max_detectors = max_detectors
        
        # 模拟生物组件
        self.mhc_extractor = self._initialize_mhc()  # 特征提取器
        self.detector_cells = []  # 检测细胞集合
        self.memory_cells = {}  # 记忆细胞
        
        logger.info(
            f"初始化免疫系统映射器: 特征维度={feature_dim}, "
            f"R连续位={r_contiguous}, 阈值={threshold}"
        )
    
    def _initialize_mhc(self) -> NDArray[np.float64]:
        """
        初始化MHC（主要组织相容性复合体）模拟器
        
        在生物系统中，MHC负责将抗原肽呈递给T细胞。
        在网络安全中，这相当于特征提取和转换过程。
        
        Returns:
            特征转换矩阵
        """
        np.random.seed(42)  # 确保可重复性
        mhc_matrix = np.random.randn(self.feature_dim, self.feature_dim)
        logger.debug("MHC特征提取器初始化完成")
        return mhc_matrix
    
    def _negative_selection(
        self,
        self_patterns: List[FeatureVector],
        candidate_detector: NDArray[np.float64]
    ) -> bool:
        """
        负选择算法：模拟T细胞的成熟过程
        
        在生物系统中，T细胞在胸腺中经过负选择，确保不与自身抗原反应。
        在网络安全中，这相当于生成不匹配正常流量模式的检测器。
        
        Args:
            self_patterns: 自身模式集合（正常流量特征）
            candidate_detector: 候选检测器
            
        Returns:
            是否通过负选择（True表示成熟，可以成为检测器）
        """
        for self_pattern in self_patterns:
            similarity = self._calculate_affinity(
                candidate_detector,
                self_pattern.data
            )
            if similarity > self.threshold:
                logger.debug("检测器未通过负选择")
                return False
        
        logger.debug("检测器通过负选择")
        return True
    
    def _calculate_affinity(
        self,
        detector: NDArray[np.float64],
        pattern: NDArray[np.float64]
    ) -> float:
        """
        计算检测器与模式之间的亲和力
        
        在生物系统中，亲和力决定抗体与抗原的结合强度。
        这里使用R连续位匹配规则和余弦相似度的组合。
        
        Args:
            detector: 检测器向量
            pattern: 模式向量
            
        Returns:
            亲和力值 [0, 1]
        """
        # 边界检查
        if len(detector) != len(pattern):
            raise ValueError("检测器和模式维度不匹配")
        
        # 计算余弦相似度
        dot_product = np.dot(detector, pattern)
        norm = np.linalg.norm(detector) * np.linalg.norm(pattern)
        cosine_sim = dot_product / norm if norm != 0 else 0
        
        # R连续位匹配规则
        r_matches = 0
        for i in range(len(detector) - self.r_contiguous + 1):
            if np.allclose(
                detector[i:i+self.r_contiguous],
                pattern[i:i+self.r_contiguous],
                atol=0.1
            ):
                r_matches += 1
        
        r_score = r_matches / (len(detector) - self.r_contiguous + 1)
        
        # 综合亲和力
        affinity = 0.6 * cosine_sim + 0.4 * r_score
        return float(np.clip(affinity, 0, 1))
    
    def generate_detectors(
        self,
        self_patterns: List[FeatureVector],
        num_candidates: int = 1000
    ) -> int:
        """
        生成检测器集合
        
        模拟免疫系统中B细胞和T细胞的生成过程，
        通过负选择确保检测器不会对自身模式产生反应。
        
        Args:
            self_patterns: 自身模式集合（正常流量特征）
            num_candidates: 候选检测器数量
            
        Returns:
            成功生成的检测器数量
        """
        if not self_patterns:
            raise ValueError("自身模式集合不能为空")
        
        generated = 0
        attempts = 0
        max_attempts = num_candidates * 10
        
        while generated < self.max_detectors and attempts < max_attempts:
            attempts += 1
            
            # 生成随机候选检测器
            candidate = np.random.randn(self.feature_dim)
            
            # 应用负选择
            if self._negative_selection(self_patterns, candidate):
                self.detector_cells.append(candidate)
                generated += 1
        
        logger.info(
            f"检测器生成完成: 生成数量={generated}, "
            f"尝试次数={attempts}, 效率={generated/attempts:.2%}"
        )
        return generated
    
    def detect_anomaly(
        self,
        traffic_feature: FeatureVector,
        use_memory: bool = True
    ) -> DetectionResult:
        """
        检测网络流量中的异常
        
        模拟免疫系统中抗体识别抗原的过程，
        结合记忆细胞加速已知攻击的识别。
        
        Args:
            traffic_feature: 网络流量特征向量
            use_memory: 是否使用记忆细胞加速识别
            
        Returns:
            检测结果对象
        """
        # 数据验证
        if not isinstance(traffic_feature, FeatureVector):
            raise TypeError("输入必须是FeatureVector类型")
        
        if len(traffic_feature.data) != self.feature_dim:
            raise ValueError(
                f"特征维度不匹配: 期望{self.feature_dim}, "
                f"实际{len(traffic_feature.data)}"
            )
        
        # 特征转换（模拟MHC呈递）
        presented_feature = np.dot(self.mhc_extractor, traffic_feature.data)
        
        # 首先检查记忆细胞（快速响应）
        if use_memory:
            for pattern_id, memory_pattern in self.memory_cells.items():
                affinity = self._calculate_affinity(
                    presented_feature,
                    memory_pattern
                )
                if affinity > self.threshold:
                    logger.info(f"通过记忆细胞识别已知攻击: {pattern_id}")
                    return DetectionResult(
                        is_anomaly=True,
                        confidence=affinity,
                        matched_patterns=[pattern_id],
                        response_action="immediate_block",
                        details={"source": "memory_cell"}
                    )
        
        # 使用检测器集合进行识别
        max_affinity = 0
        matched_detectors = []
        
        for i, detector in enumerate(self.detector_cells):
            affinity = self._calculate_affinity(presented_feature, detector)
            if affinity > self.threshold:
                matched_detectors.append(f"detector_{i}")
                max_affinity = max(max_affinity, affinity)
        
        is_anomaly = len(matched_detectors) > 0
        
        if is_anomaly:
            # 更新记忆细胞（免疫记忆）
            pattern_id = f"pattern_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            self.memory_cells[pattern_id] = presented_feature
            logger.info(f"发现新攻击模式，已添加到记忆细胞: {pattern_id}")
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            confidence=max_affinity if is_anomaly else 0,
            matched_patterns=matched_detectors,
            response_action="quarantine" if is_anomaly else None,
            details={"detector_count": len(self.detector_cells)}
        )
    
    def affinity_maturation(
        self,
        attack_patterns: List[FeatureVector],
        iterations: int = 10
    ) -> None:
        """
        亲和力成熟：优化检测器集合
        
        模拟免疫系统中B细胞在生发中心经历体细胞高频突变
        和亲和力成熟的过程，提高检测器对特定攻击的识别能力。
        
        Args:
            attack_patterns: 已知攻击模式集合
            iterations: 优化迭代次数
        """
        if not self.detector_cells:
            logger.warning("没有可优化的检测器")
            return
        
        logger.info(f"开始亲和力成熟过程，迭代次数: {iterations}")
        
        for iteration in range(iterations):
            improved_count = 0
            
            for i, detector in enumerate(self.detector_cells):
                # 对每个攻击模式计算亲和力
                best_affinity = 0
                for pattern in attack_patterns:
                    affinity = self._calculate_affinity(
                        detector,
                        np.dot(self.mhc_extractor, pattern.data)
                    )
                    best_affinity = max(best_affinity, affinity)
                
                # 如果亲和力不足，进行变异（模拟体细胞高频突变）
                if best_affinity < self.threshold:
                    mutation = np.random.randn(self.feature_dim) * 0.1
                    new_detector = detector + mutation
                    new_detector = new_detector / np.linalg.norm(new_detector)
                    
                    # 评估变异后的检测器
                    new_affinity = 0
                    for pattern in attack_patterns:
                        affinity = self._calculate_affinity(
                            new_detector,
                            np.dot(self.mhc_extractor, pattern.data)
                        )
                        new_affinity = max(new_affinity, affinity)
                    
                    if new_affinity > best_affinity:
                        self.detector_cells[i] = new_detector
                        improved_count += 1
            
            logger.debug(
                f"迭代 {iteration + 1}/{iterations}: "
                f"改进检测器数量={improved_count}"
            )


def generate_sample_data(
    num_samples: int,
    feature_dim: int,
    is_normal: bool = True
) -> List[FeatureVector]:
    """
    生成示例数据
    
    Args:
        num_samples: 样本数量
        feature_dim: 特征维度
        is_normal: 是否生成正常流量数据
        
    Returns:
        FeatureVector列表
    """
    samples = []
    base_pattern = np.random.randn(feature_dim)
    
    for _ in range(num_samples):
        if is_normal:
            # 正常流量：围绕基础模式的小幅变化
            noise = np.random.randn(feature_dim) * 0.1
            data = base_pattern + noise
        else:
            # 攻击流量：随机模式或特定攻击签名
            data = np.random.randn(feature_dim) * 2
        
        samples.append(FeatureVector(
            data=data,
            domain=DomainType.CYBER,
            timestamp=datetime.now()
        ))
    
    return samples


# 使用示例
if __name__ == "__main__":
    # 初始化映射器
    mapper = ImmuneSystemToSecurityMapper(
        feature_dim=10,
        r_contiguous=3,
        threshold=0.8,
        max_detectors=50
    )
    
    # 生成正常流量样本（自身模式）
    normal_traffic = generate_sample_data(100, 10, is_normal=True)
    
    # 生成检测器（模拟免疫细胞成熟过程）
    detector_count = mapper.generate_detectors(normal_traffic)
    print(f"成功生成 {detector_count} 个检测器")
    
    # 生成测试数据
    test_normal = generate_sample_data(5, 10, is_normal=True)
    test_attack = generate_sample_data(5, 10, is_normal=False)
    
    # 测试正常流量
    print("\n测试正常流量:")
    for i, sample in enumerate(test_normal[:2]):
        result = mapper.detect_anomaly(sample)
        print(f"样本 {i+1}: 异常={result.is_anomaly}, 置信度={result.confidence:.2f}")
    
    # 测试攻击流量
    print("\n测试攻击流量:")
    for i, sample in enumerate(test_attack[:2]):
        result = mapper.detect_anomaly(sample)
        print(f"样本 {i+1}: 异常={result.is_anomaly}, 置信度={result.confidence:.2f}")
    
    # 亲和力成熟
    print("\n执行亲和力成熟优化...")
    mapper.affinity_maturation(test_attack, iterations=5)
    
    # 再次测试攻击流量
    print("\n优化后测试攻击流量:")
    for i, sample in enumerate(test_attack[:2]):
        result = mapper.detect_anomaly(sample)
        print(f"样本 {i+1}: 异常={result.is_anomaly}, 置信度={result.confidence:.2f}")