import logging
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BioImmuneSystemAdapter")

@dataclass
class Antigen:
    """
    抗原数据结构（代表异常或攻击）。
    
    Attributes:
        id (str): 唯一标识符。
        features (np.ndarray): 特征向量（多模态数据融合后的向量）。
        timestamp (datetime): 发生时间。
        source (str): 来源（如 'device_A', 'network_node_B'）。
        metadata (Dict[str, Any]): 额外元数据。
    """
    id: str
    features: np.ndarray
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Antibody:
    """
    抗体数据结构（代表解决方案或防御策略）。
    
    Attributes:
        id (str): 唯一标识符。
        pattern_signature (str): 能够识别的模式签名（哈希值）。
        action_code (Dict[str, Any]): 执行的动作或脚本。
        affinity_threshold (float): 激活阈值（相似度高于此值才触发）。
        creation_time (datetime): 创建时间。
        durability (int): 耐久度/权重，随成功次数增加。
    """
    id: str
    pattern_signature: str
    action_code: Dict[str, Any]
    affinity_threshold: float = 0.85
    creation_time: datetime = field(default_factory=datetime.now)
    durability: int = 1

class BioImmuneSystemAdapter:
    """
    将生物免疫系统机制迁移至工业与数字领域的核心类。
    
    该系统将设备异常或网络攻击视为“抗原”，将历史解决方案视为“抗体”。
    核心功能包括因果律提取（模式识别）、多模态加权（冲突处理）和重叠固化（记忆生成）。
    
    Attributes:
        memory_b_cells (Dict[str, Antibody]): 记忆B细胞库（长期记忆，存储成功的抗体）。
        sensitivity (float): 系统敏感度，影响抗原匹配的严格程度。
    """

    def __init__(self, sensitivity: float = 0.8):
        """
        初始化免疫系统适配器。
        
        Args:
            sensitivity (float): 系统敏感度 (0.0 to 1.0)。
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")
        
        self.memory_b_cells: Dict[str, Antibody] = {}
        self.sensitivity = sensitivity
        logger.info("BioImmuneSystemAdapter initialized with sensitivity: %.2f", sensitivity)

    def _calculate_causal_hash(self, features: np.ndarray) -> str:
        """
        [辅助函数] 因果律提取 - 生成特征指纹。
        
        通过对特征向量进行哈希化，提取关键的异常模式指纹。
        
        Args:
            features (np.ndarray): 输入的特征向量。
            
        Returns:
            str: SHA256哈希字符串，代表该模式的因果指纹。
        """
        # 简单的量化处理以增强鲁棒性，避免微小噪声导致哈希剧变
        quantized_features = np.round(features, decimals=3)
        feature_bytes = quantized_features.tobytes()
        return hashlib.sha256(feature_bytes).hexdigest()

    def _multimodal_weighted_distance(self, vec_a: np.ndarray, vec_b: np.ndarray, weights: Optional[np.ndarray] = None) -> float:
        """
        [辅助函数] 多模态加权距离计算。
        
        计算两个向量之间的加权余弦相似度。如果在冲突场景下（例如历史数据与实时数据特征分布不同），
        权重可用于强调关键特征（如电压、频率等关键工业参数）。
        
        Args:
            vec_a (np.ndarray): 向量A（抗体模式）。
            vec_b (np.ndarray): 向量B（抗原特征）。
            weights (Optional[np.ndarray]): 特征权重向量。
            
        Returns:
            float: 相似度得分 (0.0 to 1.0)。
        """
        if vec_a.shape != vec_b.shape:
            logger.error("Shape mismatch in distance calculation: %s vs %s", vec_a.shape, vec_b.shape)
            return 0.0
            
        if weights is None:
            weights = np.ones_like(vec_a)
        
        # 归一化权重
        norm_weights = weights / np.sum(weights)
        
        # 加权内积
        dot_product = np.dot(vec_a * norm_weights, vec_b)
        norm_a = np.linalg.norm(vec_a * norm_weights)
        norm_b = np.linalg.norm(vec_b * norm_weights)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def detect_and_respond(self, incoming_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        [核心函数 1] 检测抗原并触发免疫响应。
        
        流程：
        1. 数据验证与抗原构造。
        2. 因果律提取（生成指纹）。
        3. 在记忆库中匹配抗体。
        4. 返回防御策略或默认响应。
        
        Args:
            incoming_data (Dict): 包含 'features' (List[float]), 'source', 'metadata' 的字典。
            
        Returns:
            Dict: 包含 'status', 'matched_antibody', 'action' 的响应字典。
            
        Example Input:
            {
                "features": [0.12, 0.98, 0.05, 0.33],
                "source": "sensor_01",
                "metadata": {"type": "voltage_spike"}
            }
        """
        try:
            # 1. 数据验证
            if 'features' not in incoming_data:
                raise ValueError("Input data must contain 'features' key")
                
            features = np.array(incoming_data['features'])
            if features.size == 0:
                raise ValueError("Features cannot be empty")

            # 构造抗原
            antigen = Antigen(
                id=hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
                features=features,
                source=incoming_data.get('source', 'unknown'),
                metadata=incoming_data.get('metadata', {})
            )
            
            logger.info(f"Detecting antigen {antigen.id} from {antigen.source}")
            
            # 2. 因果律提取（提取指纹用于快速查找，这里暂未直接使用，主要靠向量匹配）
            current_hash = self._calculate_causal_hash(features)
            
            # 3. 匹配抗体（免疫识别）
            best_match: Optional[Antibody] = None
            highest_affinity = 0.0
            
            for ab_id, antibody in self.memory_b_cells.items():
                # 假设抗体的pattern_signature对应一种预存的向量模式，这里为了演示，我们需要还原
                # 在实际应用中，抗体应存储向量或可比较的模式
                # 此处假设我们有一个方法从action_code中获取模式向量（模拟）
                # 这里简化为：直接比较当前特征与存储的“原型特征”（假设存在metadata中）
                if "prototype_vector" in antibody.metadata:
                    stored_vec = np.array(antibody.metadata["prototype_vector"])
                    affinity = self._multimodal_weighted_distance(features, stored_vec)
                    
                    if affinity > self.sensitivity and affinity > highest_affinity:
                        highest_affinity = affinity
                        best_match = antibody

            # 4. 响应
            if best_match:
                logger.info(f"Antigen {antigen.id} matched Antibody {best_match.id} (Affinity: {highest_affinity:.4f})")
                # 增加耐久度（强化连接）
                best_match.durability += 1
                return {
                    "status": "defended",
                    "antibody_id": best_match.id,
                    "action": best_match.action_code,
                    "confidence": highest_affinity
                }
            else:
                logger.warning(f"Unknown antigen pattern detected: {antigen.id}")
                return {
                    "status": "unrecognized",
                    "action": {"type": "isolation", "target": antigen.source},
                    "confidence": 0.0
                }

        except Exception as e:
            logger.error(f"Error during immune response: {str(e)}")
            return {"status": "error", "message": str(e)}

    def reinforce_and_solidify(self, solution_data: Dict[str, Any]) -> bool:
        """
        [核心函数 2] 重叠固化 - 学习与进化。
        
        当一个新的防御策略被证明有效（人工反馈或自动验证），将其转化为永久的记忆B细胞。
        如果相似的模式已存在，则增强旧模式（重叠固化）；否则创建新的抗体。
        
        Args:
            solution_data (Dict): 包含 'features' (异常特征), 'action' (解决方案), 'success_score' (成功评分).
            
        Returns:
            bool: 操作是否成功。
        """
        try:
            if 'features' not in solution_data or 'action' not in solution_data:
                raise ValueError("Solution data must contain 'features' and 'action'")
                
            features = np.array(solution_data['features'])
            action = solution_data['action']
            score = solution_data.get('success_score', 1.0)
            
            if score < 0.8:
                logger.info("Solution score too low for solidification.")
                return False

            # 检查是否已存在非常相似的模式（重叠检测）
            for ab in self.memory_b_cells.values():
                if "prototype_vector" in ab.metadata:
                    sim = self._multimodal_weighted_distance(features, np.array(ab.metadata["prototype_vector"]))
                    # 如果重叠度极高，更新现有抗体而非创建新的
                    if sim > 0.95:
                        logger.info(f"Solidifying existing antibody {ab.id} (Overlap detected).")
                        ab.durability += int(score * 10)
                        ab.action_code.update(action) # 更新策略
                        return True

            # 创建新抗体（初次免疫应答 -> 记忆细胞转化）
            new_id = hashlib.sha256(features.tobytes()).hexdigest()[:12]
            new_antibody = Antibody(
                id=new_id,
                pattern_signature=self._calculate_causal_hash(features),
                action_code=action,
                metadata={"prototype_vector": features.tolist()}
            )
            
            self.memory_b_cells[new_id] = new_antibody
            logger.info(f"New Antibody generated and solidified: {new_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to solidify immune memory: {str(e)}")
            return False

# 使用示例
if __name__ == "__main__":
    # 初始化系统
    immune_sys = BioImmuneSystemAdapter(sensitivity=0.75)
    
    # 模拟一次未知攻击（抗原）
    attack_vector_1 = {
        "features": [0.1, 0.9, 0.2, 0.5], # 模拟异常数据
        "source": "turbine_01",
        "metadata": {"type": "vibration_anomaly"}
    }
    
    print("--- Processing First Attack (Unknown) ---")
    response = immune_sys.detect_and_respond(attack_vector_1)
    print(f"Response: {response['status']}")  # 应该是 unrecognized
    
    # 模拟人工介入并提交解决方案（固化/学习）
    print("\n--- Learning from Solution ---")
    solution = {
        "features": [0.1, 0.9, 0.2, 0.5],
        "action": {"command": "reduce_rpm", "value": 10},
        "success_score": 0.95
    }
    immune_sys.reinforce_and_solidify(solution)
    
    # 模拟再次遭遇相同攻击
    print("\n--- Processing Second Attack (Known) ---")
    response = immune_sys.detect_and_respond(attack_vector_1)
    print(f"Response: {response['status']}") # 应该是 defended
    print(f"Action taken: {response['action']}")