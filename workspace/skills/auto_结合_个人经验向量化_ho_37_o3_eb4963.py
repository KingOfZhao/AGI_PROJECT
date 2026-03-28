"""
高级AGI技能模块：结合个人经验向量化与双系统认知模拟
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any
from enum import Enum
import time

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveSystemType(Enum):
    """认知系统类型枚举"""
    SYSTEM_1_INTUITION = "intuition"
    SYSTEM_2_REASONING = "reasoning"

@dataclass
class ExperienceVector:
    """个人经验向量化数据结构"""
    vector_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    confidence: float = 1.0
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.embedding, np.ndarray):
            raise TypeError("embedding必须是numpy数组")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("confidence必须在0到1之间")

@dataclass
class LogicalSlice:
    """逻辑切片数据结构"""
    slice_id: str
    premise: str
    evidence: List[str]
    conclusion: str
    confidence: float = 1.0
    source: str = "unknown"

class CognitiveRegularizer:
    """思维正则化伴侣，监管System 1的直觉响应"""
    
    def __init__(self, regularization_strength: float = 0.7):
        """
        初始化正则化伴侣
        
        Args:
            regularization_strength: 正则化强度(0-1)，值越高逻辑监管越严格
        """
        self.strength = regularization_strength
        self._validate_strength()
        
    def _validate_strength(self) -> None:
        """验证正则化强度参数"""
        if not 0 <= self.strength <= 1:
            raise ValueError("正则化强度必须在0到1之间")
    
    def regularize(self, intuition_response: Dict, reasoning_response: Dict) -> Dict:
        """
        对比并正则化System 1和System 2的响应
        
        Args:
            intuition_response: System 1的直觉响应
            reasoning_response: System 2的推理响应
            
        Returns:
            正则化后的综合响应
        """
        try:
            # 计算直觉与推理的冲突度
            conflict_score = self._calculate_conflict(
                intuition_response, 
                reasoning_response
            )
            
            # 根据冲突度和正则化强度调整最终响应
            final_response = {
                "action": self._resolve_conflict(
                    intuition_response["action"],
                    reasoning_response["action"],
                    conflict_score
                ),
                "confidence": self._calculate_final_confidence(
                    intuition_response["confidence"],
                    reasoning_response["confidence"],
                    conflict_score
                ),
                "source": "hybrid",
                "conflict_score": conflict_score,
                "reasoning_trace": reasoning_response.get("reasoning_trace", [])
            }
            
            logger.info(f"正则化完成，冲突分数: {conflict_score:.2f}")
            return final_response
            
        except Exception as e:
            logger.error(f"正则化过程中出错: {str(e)}")
            raise RuntimeError(f"正则化失败: {str(e)}")
    
    def _calculate_conflict(self, resp1: Dict, resp2: Dict) -> float:
        """计算两个响应之间的冲突度"""
        # 这里简化实现，实际应用中可以使用更复杂的语义相似度计算
        if resp1["action"] == resp2["action"]:
            return 0.0
        return 1.0 - (resp1["confidence"] * resp2["confidence"])
    
    def _resolve_conflict(self, action1: str, action2: str, conflict: float) -> str:
        """解决行动冲突"""
        if conflict < 0.3:  # 低冲突时倾向直觉
            return action1
        elif conflict > 0.7:  # 高冲突时倾向推理
            return action2
        else:  # 中等冲突时需要更复杂的解决策略
            return action2  # 这里简化处理，实际可能需要人类介入
    
    def _calculate_final_confidence(self, conf1: float, conf2: float, conflict: float) -> float:
        """计算最终置信度"""
        weighted = (conf1 * (1 - self.strength) + conf2 * self.strength)
        return weighted * (1 - conflict * 0.5)  # 冲突会降低整体置信度

class VectorExperienceStore:
    """个人经验向量存储与检索系统"""
    
    def __init__(self, embedding_dim: int = 128):
        """
        初始化向量存储
        
        Args:
            embedding_dim: 向量维度
        """
        self.embedding_dim = embedding_dim
        self.experiences: Dict[str, ExperienceVector] = {}
        self._initialize_store()
        
    def _initialize_store(self) -> None:
        """初始化存储"""
        logger.info(f"初始化向量存储，维度: {self.embedding_dim}")
        
    def add_experience(self, exp: ExperienceVector) -> None:
        """添加经验向量"""
        if exp.embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"向量维度不匹配，预期{self.embedding_dim}，得到{exp.embedding.shape[0]}")
        self.experiences[exp.vector_id] = exp
        logger.debug(f"添加经验向量: {exp.vector_id}")
        
    def retrieve_nearest(
        self, 
        query_vec: np.ndarray, 
        k: int = 5,
        min_confidence: float = 0.0
    ) -> List[Tuple[ExperienceVector, float]]:
        """
        检索最近邻经验
        
        Args:
            query_vec: 查询向量
            k: 返回的最近邻数量
            min_confidence: 最小置信度阈值
            
        Returns:
            包含(经验向量, 相似度分数)的元组列表
        """
        if query_vec.shape[0] != self.embedding_dim:
            raise ValueError(f"查询向量维度不匹配，预期{self.embedding_dim}，得到{query_vec.shape[0]}")
            
        if k <= 0:
            raise ValueError("k必须大于0")
            
        if not self.experiences:
            logger.warning("经验存储为空，返回空结果")
            return []
            
        # 计算余弦相似度
        query_norm = query_vec / np.linalg.norm(query_vec)
        similarities = []
        
        for exp_id, exp in self.experiences.items():
            if exp.confidence < min_confidence:
                continue
                
            exp_norm = exp.embedding / np.linalg.norm(exp.embedding)
            similarity = np.dot(query_norm, exp_norm)
            similarities.append((exp, similarity))
            
        # 按相似度排序并返回top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

class LogicalSlicer:
    """逻辑切片与溯源系统"""
    
    def __init__(self):
        """初始化逻辑切片器"""
        self.slices: Dict[str, LogicalSlice] = {}
        self._initialize_slices()
        
    def _initialize_slices(self) -> None:
        """初始化基础逻辑切片"""
        # 这里添加一些基础逻辑切片
        self.add_slice(LogicalSlice(
            slice_id="basic_logic_1",
            premise="If A implies B and A is true, then B is true",
            evidence=["A is true", "A implies B"],
            conclusion="B is true",
            confidence=1.0
        ))
        
        self.add_slice(LogicalSlice(
            slice_id="basic_logic_2",
            premise="If not B and A implies B, then not A",
            evidence=["not B", "A implies B"],
            conclusion="not A",
            confidence=1.0
        ))
        
    def add_slice(self, slice_obj: LogicalSlice) -> None:
        """添加逻辑切片"""
        self.slices[slice_obj.slice_id] = slice_obj
        logger.debug(f"添加逻辑切片: {slice_obj.slice_id}")
        
    def validate_reasoning(self, reasoning_chain: List[str]) -> Tuple[bool, float, List[str]]:
        """
        验证推理链的逻辑有效性
        
        Args:
            reasoning_chain: 推理步骤列表
            
        Returns:
            (是否有效, 置信度, 使用的切片ID列表)
        """
        if not reasoning_chain:
            return False, 0.0, []
            
        used_slices = []
        total_confidence = 0.0
        is_valid = True
        
        for step in reasoning_chain:
            matched = False
            for slice_id, slice_obj in self.slices.items():
                if self._step_matches_slice(step, slice_obj):
                    used_slices.append(slice_id)
                    total_confidence += slice_obj.confidence
                    matched = True
                    break
                    
            if not matched:
                is_valid = False
                logger.warning(f"推理步骤无匹配逻辑切片: {step}")
                
        avg_confidence = total_confidence / len(reasoning_chain) if reasoning_chain else 0.0
        return is_valid, avg_confidence, used_slices
        
    def _step_matches_slice(self, step: str, slice_obj: LogicalSlice) -> bool:
        """检查推理步骤是否匹配逻辑切片"""
        # 简化实现，实际应用中需要更复杂的语义匹配
        return step.lower() in slice_obj.premise.lower() or \
               step.lower() in slice_obj.conclusion.lower()

class DualSystemCognition:
    """
    结合个人经验向量化和逻辑切片的双系统认知模型
    
    模拟人类快思考(System 1)和慢思考(System 2)的认知过程
    """
    
    def __init__(
        self,
        embedding_dim: int = 128,
        regularization_strength: float = 0.7
    ):
        """
        初始化双系统认知模型
        
        Args:
            embedding_dim: 向量维度
            regularization_strength: 正则化强度(0-1)
        """
        self.vector_store = VectorExperienceStore(embedding_dim)
        self.logical_slicer = LogicalSlicer()
        self.regularizer = CognitiveRegularizer(regularization_strength)
        
        logger.info("初始化双系统认知模型")
        
    def process_input(
        self, 
        input_vector: np.ndarray,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        处理输入，结合直觉和推理生成响应
        
        Args:
            input_vector: 输入向量
            context: 上下文信息
            
        Returns:
            处理结果字典
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # System 1: 基于直觉的快速响应
            intuition_response = self._system1_intuition(input_vector)
            
            # System 2: 基于推理的慢速响应
            reasoning_response = self._system2_reasoning(input_vector, context)
            
            # 使用正则化伴侣整合两个系统的响应
            final_response = self.regularizer.regularize(
                intuition_response,
                reasoning_response
            )
            
            processing_time = time.time() - start_time
            final_response["processing_time"] = processing_time
            
            logger.info(f"输入处理完成，耗时: {processing_time:.4f}秒")
            return final_response
            
        except Exception as e:
            logger.error(f"处理输入时出错: {str(e)}")
            raise RuntimeError(f"处理失败: {str(e)}")
    
    def _system1_intuition(self, input_vector: np.ndarray) -> Dict:
        """System 1: 基于直觉的快速响应"""
        try:
            # 检索最近邻经验
            nearest_exps = self.vector_store.retrieve_nearest(input_vector, k=3)
            
            if not nearest_exps:
                return {
                    "action": "no_action",
                    "confidence": 0.0,
                    "source": "intuition",
                    "explanation": "无相关经验"
                }
                
            # 选择最相似的经验作为直觉响应
            best_exp, similarity = nearest_exps[0]
            
            return {
                "action": best_exp.metadata.get("action", "unknown"),
                "confidence": similarity * best_exp.confidence,
                "source": "intuition",
                "explanation": f"基于经验{best_exp.vector_id}的直觉响应",
                "experience_id": best_exp.vector_id,
                "similarity": similarity
            }
            
        except Exception as e:
            logger.error(f"System 1处理出错: {str(e)}")
            return {
                "action": "error",
                "confidence": 0.0,
                "source": "intuition",
                "error": str(e)
            }
    
    def _system2_reasoning(
        self, 
        input_vector: np.ndarray, 
        context: Dict
    ) -> Dict:
        """System 2: 基于推理的慢速响应"""
        try:
            # 1. 从上下文中提取关键信息
            key_info = self._extract_key_information(input_vector, context)
            
            # 2. 构建推理链
            reasoning_chain = self._build_reasoning_chain(key_info)
            
            # 3. 验证推理链
            is_valid, confidence, used_slices = self.logical_slicer.validate_reasoning(
                reasoning_chain
            )
            
            if not is_valid:
                logger.warning("推理链验证失败")
                confidence *= 0.5  # 降低无效推理的置信度
                
            # 4. 生成推理响应
            action = self._determine_action_from_reasoning(reasoning_chain)
            
            return {
                "action": action,
                "confidence": confidence,
                "source": "reasoning",
                "explanation": "基于逻辑推理的响应",
                "reasoning_trace": reasoning_chain,
                "used_slices": used_slices,
                "is_valid": is_valid
            }
            
        except Exception as e:
            logger.error(f"System 2处理出错: {str(e)}")
            return {
                "action": "error",
                "confidence": 0.0,
                "source": "reasoning",
                "error": str(e)
            }
    
    def _extract_key_information(self, input_vector: np.ndarray, context: Dict) -> Dict:
        """从输入和上下文中提取关键信息"""
        # 这里简化实现，实际应用中可以使用更复杂的信息提取方法
        return {
            "vector_mean": float(np.mean(input_vector)),
            "vector_std": float(np.std(input_vector)),
            "context_keys": list(context.keys()),
            "context_values": list(context.values())
        }
    
    def _build_reasoning_chain(self, key_info: Dict) -> List[str]:
        """构建推理链"""
        # 这里简化实现，实际应用中可以使用更复杂的推理引擎
        chain = []
        
        if "user_intent" in key_info.get("context_keys", []):
            chain.append("识别用户意图")
            chain.append("匹配相关规则")
            
        if "risk_level" in key_info.get("context_keys", []):
            chain.append("评估风险等级")
            chain.append("检查安全约束")
            
        if not chain:
            chain.append("默认推理路径")
            
        return chain
    
    def _determine_action_from_reasoning(self, reasoning_chain: List[str]) -> str:
        """从推理链确定行动"""
        # 这里简化实现，实际应用中可以使用更复杂的决策逻辑
        if "安全约束" in reasoning_chain:
            return "conservative_action"
        elif "用户意图" in reasoning_chain:
            return "user_oriented_action"
        else:
            return "neutral_action"

# 使用示例
if __name__ == "__main__":
    try:
        # 初始化双系统认知模型
        cognition = DualSystemCognition(embedding_dim=128, regularization_strength=0.7)
        
        # 添加一些经验向量
        exp1 = ExperienceVector(
            vector_id="exp_1",
            embedding=np.random.rand(128),
            metadata={"action": "help_user", "tags": ["assistance"]},
            confidence=0.9
        )
        
        exp2 = ExperienceVector(
            vector_id="exp_2",
            embedding=np.random.rand(128),
            metadata={"action": "provide_info", "tags": ["information"]},
            confidence=0.8
        )
        
        cognition.vector_store.add_experience(exp1)
        cognition.vector_store.add_experience(exp2)
        
        # 处理一个输入
        input_vec = np.random.rand(128)
        context = {
            "user_intent": "get_help",
            "risk_level": "low"
        }
        
        result = cognition.process_input(input_vec, context)
        
        print("\n处理结果:")
        print(f"行动: {result['action']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"来源: {result['source']}")
        print(f"冲突分数: {result['conflict_score']:.2f}")
        print(f"处理时间: {result['processing_time']:.4f}秒")
        
    except Exception as e:
        logger.error(f"示例运行出错: {str(e)}")