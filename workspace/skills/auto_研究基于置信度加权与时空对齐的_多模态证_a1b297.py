"""
Module: multimodal_evidence_fusion.py
Description: 实现基于置信度加权与时空对齐的多模态证据融合算法。
             该模块旨在为AGI系统提供跨模态（如视觉、文本、音频）的事实核查能力，
             通过对齐时空戳并根据信源置信度进行加权，得出最终的可信度评分。
Author: AGI System Core Engineer
Version: 1.0.0
License: MIT
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime, timedelta
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义常量
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
DEFAULT_TEMPORAL_TOLERANCE = 5.0  # 默认时间容差（秒）
DEFAULT_SPATIAL_TOLERANCE = 50.0  # 默认空间容差（米，视具体场景而定）

@dataclass
class ModalityEvidence:
    """
    单个模态的证据数据结构。
    
    Attributes:
        source (str): 数据来源（例如 'visual', 'text', 'audio'）
        timestamp (float): 时间戳（Unix时间戳或相对秒数）
        location (Optional[Tuple[float, float]]): 空间坐标 (纬度, 经度) 或，可选
        claim (str): 提取的事实声明
        confidence (float): 初始置信度 [0.0, 1.0]
        reliability (float): 信源本身的可靠性评分 [0.0, 1.0]
        raw_data (dict): 原始数据元信息
    """
    source: str
    timestamp: float
    claim: str
    confidence: float
    reliability: float
    location: Optional[Tuple[float, float]] = None
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self):
        """数据验证"""
        if not MIN_CONFIDENCE <= self.confidence <= MAX_CONFIDENCE:
            raise ValueError(f"Confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}")
        if not MIN_CONFIDENCE <= self.reliability <= MAX_CONFIDENCE:
            raise ValueError(f"Reliability must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}")

def calculate_spatial_distance(
    loc1: Optional[Tuple[float, float]], 
    loc2: Optional[Tuple[float, float]]
) -> float:
    """
    辅助函数：计算两个位置之间的欧几里得距离。
    
    注意：这是一个简化的计算，实际生产环境应使用 Haversine 公式处理经纬度。
    如果任一位置为None，则返回无穷大表示无法对齐。
    
    Args:
        loc1: 位置1坐标
        loc2: 位置2坐标
        
    Returns:
        float: 距离数值
    """
    if loc1 is None or loc2 is None:
        return float('inf')
    
    # 简单的欧几里得距离，仅用于演示
    return np.sqrt((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)

def align_evidence_temporally_and_spatially(
    evidences: List[ModalityEvidence],
    temporal_tolerance: float = DEFAULT_TEMPORAL_TOLERANCE,
    spatial_tolerance: float = DEFAULT_SPATIAL_TOLERANCE
) -> List[List[ModalityEvidence]]:
    """
    核心函数1：时空对齐。
    
    将输入的证据列表根据时间窗口和空间 proximity 分组。
    只有在时间和空间上都足够接近的证据才会被视为针对同一事件的观察。
    
    Args:
        evidences: 原始证据列表
        temporal_tolerance: 时间容差（秒）
        spatial_tolerance: 空间容差（单位取决于坐标系统）
        
    Returns:
        List[List[ModalityEvidence]]: 对齐后的证据组列表
    """
    if not evidences:
        return []

    # 按时间戳排序
    sorted_evidences = sorted(evidences, key=lambda x: x.timestamp)
    aligned_groups = []
    current_group = [sorted_evidences[0]]
    
    # 基准点：当前组的第一个证据
    base_time = sorted_evidences[0].timestamp
    base_loc = sorted_evidences[0].location

    logger.info(f"Starting alignment with {len(evidences)} evidences. Tolerance: {temporal_tolerance}s/{spatial_tolerance}m")

    for evidence in sorted_evidences[1:]:
        time_diff = abs(evidence.timestamp - base_time)
        space_diff = calculate_spatial_distance(evidence.location, base_loc)
        
        if time_diff <= temporal_tolerance and space_diff <= spatial_tolerance:
            # 符合对齐条件，加入当前组
            current_group.append(evidence)
        else:
            # 不符合，结束当前组，开启新组
            aligned_groups.append(current_group)
            current_group = [evidence]
            base_time = evidence.timestamp
            base_loc = evidence.location
            
    aligned_groups.append(current_group)
    logger.info(f"Alignment complete. Created {len(aligned_groups)} evidence groups.")
    return aligned_groups

def weighted_fusion_algorithm(aligned_group: List[ModalityEvidence]) -> float:
    """
    核心函数2：基于置信度的加权融合。
    
    算法逻辑：
    最终置信度 = Σ(信源可靠性 * 证据置信度) / Σ(信源可靠性)
    
    该算法给予高可靠性信源更高的权重。如果所有信源可靠性为0，则返回0。
    
    Args:
        aligned_group: 一组已经对齐的证据
        
    Returns:
        float: 融合后的最终置信度分数 [0.0, 1.0]
    """
    if not aligned_group:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for evidence in aligned_group:
        # 权重因子：这里简单地使用 reliability，也可以扩展为 reliability * (1 + importance)
        weight = evidence.reliability
        score = evidence.confidence
        
        weighted_sum += weight * score
        total_weight += weight

    if total_weight == 0:
        logger.warning("Total weight is zero in group, returning 0 confidence.")
        return 0.0

    fused_confidence = weighted_sum / total_weight
    
    # 边界检查
    return np.clip(fused_confidence, MIN_CONFIDENCE, MAX_CONFIDENCE)

def process_multimodal_facts(
    evidences: List[ModalityEvidence],
    claim_threshold: float = 0.7
) -> Dict[str, Union[float, str, List[str]]]:
    """
    主处理流程：整合对齐与融合逻辑，输出事实核查结果。
    
    Args:
        evidences: 输入的所有模态证据
        claim_threshold: 判定为 "True" 的置信度阈值
        
    Returns:
        Dict: 包含 'final_confidence', 'verdict', 'sources_used' 的结果字典
    """
    logger.info("Starting Multimodal Fact Checking Process...")
    
    # 1. 时空对齐
    groups = align_evidence_temporally_and_spatially(evidences)
    
    # 2. 对每一组进行融合（这里简化为处理最大的组或所有组的平均，这里取最大的组作为主事件）
    if not groups:
        return {"error": "No valid evidence groups formed."}
    
    # 寻找证据最多的组（假设这是当前最关注的事件）
    primary_group = max(groups, key=len)
    
    # 3. 加权融合
    final_score = weighted_fusion_algorithm(primary_group)
    
    # 4. 判定
    verdict = "UNVERIFIED"
    if final_score >= claim_threshold:
        verdict = "VERIFIED_TRUE"
    elif final_score <= (1 - claim_threshold):
        verdict = "VERIFIED_FALSE"
    
    sources = [e.source for e in primary_group]
    
    result = {
        "final_confidence": round(final_score, 4),
        "verdict": verdict,
        "sources_used": sources,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"Process completed. Verdict: {verdict}, Score: {final_score}")
    return result

# --- Usage Example ---
if __name__ == "__main__":
    # 模拟AGI系统接收到的多模态数据
    
    # 视觉证据：检测到火灾，置信度0.9，摄像机可靠性0.8
    vis_evidence = ModalityEvidence(
        source="visual_camera_01",
        timestamp=1672531200.0,
        location=(34.0522, -118.2437),
        claim="fire_detected",
        confidence=0.9,
        reliability=0.8
    )
    
    # 文本证据：社交媒体推文报告烟雾，置信度0.7，社交媒体可靠性0.5（较低）
    text_evidence = ModalityEvidence(
        source="twitter_stream",
        timestamp=1672531202.0, # 2秒后
        location=(34.0523, -118.2436), # 非常近
        claim="smoke_seen",
        confidence=0.7,
        reliability=0.5
    )
    
    # 音频证据：警报声，置信度0.95，传感器可靠性0.95
    audio_evidence = ModalityEvidence(
        source="audio_sensor_array",
        timestamp=1672531205.0, # 5秒后
        location=(34.0521, -118.2437), # 非常近
        claim="alarm_sound",
        confidence=0.95,
        reliability=0.95
    )
    
    # 无关证据：时间太早，不应融合
    old_evidence = ModalityEvidence(
        source="archive_log",
        timestamp=1672531100.0, # 100秒前
        location=(34.0522, -118.2437),
        claim="no_fire",
        confidence=1.0,
        reliability=1.0
    )

    all_evidences = [vis_evidence, text_evidence, audio_evidence, old_evidence]
    
    # 运行处理
    try:
        result = process_multimodal_facts(all_evidences, claim_threshold=0.75)
        print("\n--- Fact Check Result ---")
        print(f"Verdict: {result['verdict']}")
        print(f"Confidence: {result['final_confidence']}")
        print(f"Sources: {result['sources_used']}")
        print("-------------------------\n")
        
        # 预期结果：算法应该融合前三个证据（时空对齐），忽略第四个。
        # 计算: (0.8*0.9 + 0.5*0.7 + 0.95*0.95) / (0.8 + 0.5 + 0.95)
        # = (0.72 + 0.35 + 0.9025) / 2.25 = 1.9725 / 2.25 ≈ 0.876
        # Verdict: VERIFIED_TRUE (> 0.75)
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)