"""
多模态感官冲突的仲裁机制模块

该模块实现了一个基于可证伪性原则的多模态融合系统，用于解决文本与视觉信息冲突时的仲裁问题。
核心思想：视觉信息通常比文本信息更难伪造，因此在冲突时应给予更高权重。

典型使用场景：
>>> arbitrator = MultimodalArbitrator()
>>> text_input = {"content": "红色的苹果", "confidence": 0.8}
>>> visual_input = {"content": "青色", "confidence": 0.9, "source": "high_res_camera"}
>>> result = arbitrator.resolve_conflict(text_input, visual_input)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModalityData:
    """多模态数据容器"""
    modality_type: str
    content: Any
    confidence: float
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("置信度必须在0到1之间")
        if not self.modality_type or not isinstance(self.modality_type, str):
            raise ValueError("模态类型必须是非空字符串")


class MultimodalArbitrator:
    """
    多模态冲突仲裁器
    
    基于可证伪性原则动态调整不同模态的权重，当检测到冲突时优先信任更难伪造的模态。
    
    属性:
        modality_weights (Dict[str, float]): 各模态的基础权重
        falsifiability_scores (Dict[str, float]): 各模态的可证伪性得分
        conflict_threshold (float): 判定为冲突的阈值
    """
    
    def __init__(self, conflict_threshold: float = 0.3):
        """
        初始化仲裁器
        
        参数:
            conflict_threshold: 判定为冲突的阈值(0-1)
        """
        self.modality_weights = {
            'text': 0.4,      # 文本模态基础权重
            'visual': 0.6     # 视觉模态基础权重
        }
        self.falsifiability_scores = {
            'text': 0.3,      # 文本相对容易伪造
            'visual': 0.9     # 视觉证据更难伪造
        }
        self.conflict_threshold = conflict_threshold
        logger.info("多模态仲裁器初始化完成，冲突阈值: %.2f", conflict_threshold)
    
    def _calculate_conflict_score(self, text_data: ModalityData, visual_data: ModalityData) -> float:
        """
        计算文本与视觉数据之间的冲突分数
        
        参数:
            text_data: 文本模态数据
            visual_data: 视觉模态数据
            
        返回:
            冲突分数(0-1)，越高表示冲突越严重
        """
        # 这里使用简单的余弦相似度作为冲突度量示例
        # 实际应用中应该使用更复杂的语义相似度计算
        text_vec = self._content_to_vector(text_data.content)
        visual_vec = self._content_to_vector(visual_data.content)
        
        similarity = np.dot(text_vec, visual_vec) / (np.linalg.norm(text_vec) * np.linalg.norm(visual_vec))
        conflict_score = 1 - (similarity + 1) / 2  # 转换为0-1范围
        
        logger.debug("计算冲突分数: %.2f (相似度: %.2f)", conflict_score, similarity)
        return conflict_score
    
    def _content_to_vector(self, content: Any) -> np.ndarray:
        """
        将内容转换为向量表示(辅助函数)
        
        这是一个简化的实现，实际应用中应使用预训练的嵌入模型
        
        参数:
            content: 要转换的内容
            
        返回:
            内容的向量表示
        """
        # 简化的哈希向量生成
        if isinstance(content, str):
            vec = np.zeros(100)
            for i, char in enumerate(content[:20]):
                vec[i] = ord(char) / 255.0
            return vec
        else:
            return np.random.rand(100)
    
    def _adjust_weights(self, conflict_score: float) -> Dict[str, float]:
        """
        根据冲突分数动态调整模态权重
        
        参数:
            conflict_score: 冲突分数
            
        返回:
            调整后的权重字典
        """
        if conflict_score <= self.conflict_threshold:
            return self.modality_weights.copy()
        
        # 冲突时增强视觉模态权重
        adjusted_weights = self.modality_weights.copy()
        adjustment_factor = min(1.0, conflict_score / self.conflict_threshold)
        
        adjusted_weights['visual'] += self.falsifiability_scores['visual'] * adjustment_factor * 0.5
        adjusted_weights['text'] -= self.falsifiability_scores['text'] * adjustment_factor * 0.3
        
        # 归一化权重
        total = sum(adjusted_weights.values())
        adjusted_weights = {k: v/total for k, v in adjusted_weights.items()}
        
        logger.info("调整权重: %s (冲突分数: %.2f)", adjusted_weights, conflict_score)
        return adjusted_weights
    
    def resolve_conflict(
        self,
        text_data: Dict[str, Any],
        visual_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解决文本与视觉模态之间的冲突
        
        参数:
            text_data: 文本数据字典，包含content, confidence等字段
            visual_data: 视觉数据字典，包含content, confidence, source等字段
            
        返回:
            包含仲裁结果的字典，包括:
            - final_decision: 最终决策内容
            - confidence: 最终置信度
            - used_modality: 主要使用的模态
            - conflict_score: 冲突分数
            - weights: 使用的权重
            
        示例:
            >>> arbitrator = MultimodalArbitrator()
            >>> text = {"content": "红色的苹果", "confidence": 0.8}
            >>> visual = {"content": "青色", "confidence": 0.9, "source": "camera"}
            >>> result = arbitrator.resolve_conflict(text, visual)
        """
        try:
            # 数据验证和转换
            text_modality = ModalityData(
                modality_type='text',
                content=text_data.get('content'),
                confidence=text_data.get('confidence', 0.5),
                metadata=text_data.get('metadata')
            )
            
            visual_modality = ModalityData(
                modality_type='visual',
                content=visual_data.get('content'),
                confidence=visual_data.get('confidence', 0.5),
                source=visual_data.get('source'),
                metadata=visual_data.get('metadata')
            )
            
            # 计算冲突分数
            conflict_score = self._calculate_conflict_score(text_modality, visual_modality)
            
            # 调整权重
            adjusted_weights = self._adjust_weights(conflict_score)
            
            # 决策过程
            if conflict_score > self.conflict_threshold:
                # 有冲突，根据可证伪性原则决策
                if adjusted_weights['visual'] > adjusted_weights['text']:
                    final_decision = visual_modality.content
                    used_modality = 'visual'
                    confidence = visual_modality.confidence * adjusted_weights['visual']
                else:
                    final_decision = text_modality.content
                    used_modality = 'text'
                    confidence = text_modality.confidence * adjusted_weights['text']
                
                logger.warning(
                    "检测到冲突(%.2f): 文本='%s' vs 视觉='%s'，选择: %s",
                    conflict_score, text_modality.content, visual_modality.content, used_modality
                )
            else:
                # 无冲突，融合决策
                final_decision = f"{text_modality.content} (视觉验证: {visual_modality.content})"
                used_modality = 'fused'
                confidence = (text_modality.confidence * adjusted_weights['text'] + 
                              visual_modality.confidence * adjusted_weights['visual'])
                logger.info("无严重冲突，进行融合决策")
            
            return {
                'final_decision': final_decision,
                'confidence': confidence,
                'used_modality': used_modality,
                'conflict_score': conflict_score,
                'weights': adjusted_weights
            }
            
        except Exception as e:
            logger.error("冲突解决过程中发生错误: %s", str(e))
            raise RuntimeError(f"冲突解决失败: {str(e)}") from e


def evaluate_arbitration_performance(test_cases: list) -> Dict[str, float]:
    """
    评估仲裁机制在测试案例上的性能
    
    参数:
        test_cases: 测试案例列表，每个案例是包含text_data和visual_data的字典
        
    返回:
        包含性能指标的字典:
        - accuracy: 准确率
        - conflict_detection_rate: 冲突检测率
        - avg_confidence: 平均置信度
    """
    arbitrator = MultimodalArbitrator()
    results = []
    
    for case in test_cases:
        try:
            result = arbitrator.resolve_conflict(
                case['text_data'],
                case['visual_data']
            )
            results.append(result)
        except Exception as e:
            logger.error("测试案例失败: %s", str(e))
            continue
    
    if not results:
        return {'accuracy': 0.0, 'conflict_detection_rate': 0.0, 'avg_confidence': 0.0}
    
    # 计算指标
    conflict_cases = [r for r in results if r['conflict_score'] > arbitrator.conflict_threshold]
    conflict_detection_rate = len(conflict_cases) / len(results)
    
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    
    # 这里简化了准确率计算，实际应用中应有ground truth
    accuracy = sum(1 for r in results if r['confidence'] > 0.7) / len(results)
    
    logger.info(
        "性能评估完成 - 准确率: %.2f, 冲突检测率: %.2f, 平均置信度: %.2f",
        accuracy, conflict_detection_rate, avg_confidence
    )
    
    return {
        'accuracy': accuracy,
        'conflict_detection_rate': conflict_detection_rate,
        'avg_confidence': avg_confidence
    }


# 使用示例
if __name__ == "__main__":
    # 初始化仲裁器
    arbitrator = MultimodalArbitrator(conflict_threshold=0.4)
    
    # 测试案例1: 有冲突的情况
    text_data1 = {"content": "红色的苹果", "confidence": 0.85}
    visual_data1 = {"content": "青色", "confidence": 0.95, "source": "high_res_camera"}
    result1 = arbitrator.resolve_conflict(text_data1, visual_data1)
    print(f"案例1结果: {result1}")
    
    # 测试案例2: 无冲突的情况
    text_data2 = {"content": "一只猫坐在沙发上", "confidence": 0.9}
    visual_data2 = {"content": "猫科动物", "confidence": 0.88, "source": "webcam"}
    result2 = arbitrator.resolve_conflict(text_data2, visual_data2)
    print(f"案例2结果: {result2}")
    
    # 性能评估
    test_cases = [
        {"text_data": {"content": "大型犬", "confidence": 0.7}, 
         "visual_data": {"content": "小型犬", "confidence": 0.6}},
        {"text_data": {"content": "晴朗的天气", "confidence": 0.8}, 
         "visual_data": {"content": "晴朗", "confidence": 0.9}}
    ]
    performance = evaluate_arbitration_performance(test_cases)
    print(f"性能指标: {performance}")