"""
模块名称: semantic_tactile_alignment_network
描述: 构建语义-触觉对齐网络(STAN)，解决手工艺中自然语言力度描述的歧义性。
      将模糊的自然语言形容词（如“轻揉”、“重按”）映射到具体的物理参数区间。

Author: Advanced Python Engineer for AGI System
Version: 1.0.0
License: MIT
"""

import logging
import numpy as np
from typing import Dict, Tuple, List, Optional, Union
from pydantic import BaseModel, Field, validator, ValidationError
from sklearn.preprocessing import MinMaxScaler

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === 数据模型与验证 ===

class TactileSample(BaseModel):
    """
    单次触觉样本的数据结构，用于验证输入数据的完整性。
    """
    adjective: str = Field(..., description="描述动作的自然语言形容词，如'轻柔'")
    force_newton: float = Field(..., ge=0.0, description="力传感器采集的力值，范围[0, 50.0]")
    pressure_pascal: float = Field(..., ge=0.0, description="压强值，范围[0, 100000.0]")

    @validator('force_newton', 'pressure_pascal')
    def check_physical_limits(cls, v, values, **kwargs):
        # 简单的物理边界检查，防止传感器异常数据
        if v > 1e6:
            raise ValueError(f"物理参数 {v} 超出合理范围，可能传感器故障")
        return v

class SemanticEmbeddingConfig(BaseModel):
    """
    网络配置参数
    """
    embedding_dim: int = Field(default=64, description="语义嵌入向量的维度")
    force_max_limit: float = Field(default=50.0, description="系统最大承受力")


# === 核心类定义 ===

class SemanticTactileAligner:
    """
    语义-触觉对齐网络核心类。
    
    负责将自然语言指令转化为物理执行参数。
    通过建立 'Adjective -> Physical Parameter Distribution' 的映射关系。
    
    输入格式:
        - 文本指令
    输出格式:
        - Dict: {"mean_force": float, "std_force": float, "action_vector": np.ndarray}
    """

    def __init__(self, config: Optional[SemanticEmbeddingConfig] = None):
        """
        初始化对齐网络。
        
        Args:
            config (SemanticEmbeddingConfig, optional): 网络配置. Defaults to None.
        """
        self.config = config if config else SemanticEmbeddingConfig()
        # 简单的词向量查找表，实际AGI场景中应接入LLM Embedding (e.g., OpenAI, BERT)
        self._vocabulary_map: Dict[str, np.ndarray] = {}
        # 物理参数统计映射表: word -> {'mean': float, 'std': float, 'scaler': MinMaxScaler}
        self._physical_profile_map: Dict[str, Dict] = {}
        # 模拟一个固定的随机种子以保证Embedding一致性
        self._rng = np.random.default_rng(seed=42)
        logger.info("SemanticTactileAligner initialized with embedding dim: %d", self.config.embedding_dim)

    def _get_text_embedding(self, text: str) -> np.ndarray:
        """
        [辅助函数] 获取文本的嵌入向量。
        在实际生产中，这将调用预训练模型。此处使用确定性哈希模拟。
        
        Args:
            text (str): 输入文本
            
        Returns:
            np.ndarray: 语义向量
        """
        if text not in self._vocabulary_map:
            # 模拟生成一个基于文本hash的伪随机向量
            base_vector = np.zeros(self.config.embedding_dim)
            digest = int.from_bytes(text.encode(), 'little')
            self._rng.seed(digest)
            self._vocabulary_map[text] = self._rng.random(self.config.embedding_dim)
        return self._vocabulary_map[text]

    def train_mapping(self, samples: List[Dict]) -> None:
        """
        [核心函数 1] 训练语义到物理参数的映射关系。
        输入一组带有形容词标签的传感器数据，计算每个形容词对应的物理参数分布。
        
        Args:
            samples (List[Dict]): 历史采集数据列表。
                                  格式: [{"adjective": "轻按", "force": 2.5, "pressure": 1000}, ...]
        
        Raises:
            ValueError: 如果数据格式无效或数据量不足
        """
        logger.info(f"Starting training with {len(samples)} samples...")
        if len(samples) < 2:
            raise ValueError("Insufficient data for statistical mapping (min 2 samples).")

        # 数据分组
        grouped_data: Dict[str, List[float]] = {}
        
        # 验证并分组数据
        for raw_sample in samples:
            try:
                sample = TactileSample(**raw_sample)
                if sample.adjective not in grouped_data:
                    grouped_data[sample.adjective] = []
                grouped_data[sample.adjective].append(sample.force_newton)
            except (ValidationError, TypeError) as e:
                logger.warning(f"Skipping invalid sample data: {raw_sample}. Error: {e}")
                continue

        # 建立映射
        for adj, forces in grouped_data.items():
            if len(forces) < 1:
                continue
            
            forces_np = np.array(forces).reshape(-1, 1)
            
            # 计算统计特征
            mean_force = np.mean(forces_np)
            std_force = np.std(forces_np)
            
            # 训练一个简单的缩放器，用于归一化
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaler.fit(forces_np)
            
            self._physical_profile_map[adj] = {
                "mean": mean_force,
                "std": std_force,
                "scaler": scaler,
                "raw_data_size": len(forces)
            }
            logger.info(f"Mapped '{adj}' -> Mean: {mean_force:.2f}N, Std: {std_force:.2f}N")

    def execute_command(self, command: str) -> Dict[str, Union[float, np.ndarray, str]]:
        """
        [核心函数 2] 执行从语言指令到物理参数的转化。
        
        Args:
            command (str): 自然语言指令，如 "请轻轻按压"
            
        Returns:
            Dict: 包含物理执行参数和语义向量的字典。
                  {
                      "target_force_N": float, 
                      "force_tolerance_N": float,
                      "semantic_vector": np.ndarray,
                      "status": str
                  }
        
        Raises:
            KeyError: 如果指令中的形容词未在训练集中
        """
        # 1. 简单的关键词提取 (实际应使用NLP分词或LLM)
        detected_adjective = self._extract_adjective(command)
        
        if detected_adjective not in self._physical_profile_map:
            logger.error(f"Unknown adjective '{detected_adjective}' in command '{command}'")
            raise KeyError(f"Semantic mapping for '{detected_adjective}' not found.")
            
        # 2. 获取物理参数
        profile = self._physical_profile_map[detected_adjective]
        target_force = profile["mean"]
        tolerance = profile["std"]
        
        # 3. 获取语义向量 (用于下游控制器)
        embedding = self._get_text_embedding(detected_adjective)
        
        # 4. 边界检查
        if target_force > self.config.force_max_limit:
            logger.warning(f"Calculated force {target_force} exceeds safety limit. Clamping.")
            target_force = self.config.force_max_limit

        logger.info(f"Executing '{command}': Target {target_force:.2f}N (+/- {tolerance:.2f})")
        
        return {
            "target_force_N": float(target_force),
            "force_tolerance_N": float(tolerance),
            "semantic_vector": embedding,
            "status": "CALCULATED_SUCCESS"
        }

    def _extract_adjective(self, text: str) -> str:
        """
        [辅助函数] 从句子中提取关键词。
        这是一个简化的实现，实际应用需要使用NLP库。
        """
        # 简单的启发式规则
        text = text.replace("请", "").strip()
        # 假设我们的训练词汇有 "轻按", "重压", "轻揉"
        known_words = self._physical_profile_map.keys()
        for word in known_words:
            if word in text:
                return word
        # 如果找不到，默认返回第一个词（演示用）
        return text.split()[0] if text.split() else "unknown"


# === 使用示例 ===
if __name__ == "__main__":
    # 1. 模拟采集的历史传感器数据
    training_data = [
        {"adjective": "轻按", "force_newton": 2.1, "pressure_pascal": 1000},
        {"adjective": "轻按", "force_newton": 1.9, "pressure_pascal": 950},
        {"adjective": "轻按", "force_newton": 2.5, "pressure_pascal": 1100},
        {"adjective": "重压", "force_newton": 15.0, "pressure_pascal": 8000},
        {"adjective": "重压", "force_newton": 18.5, "pressure_pascal": 8500},
        {"adjective": "重压", "force_newton": 16.2, "pressure_pascal": 8200},
        {"adjective": "轻揉", "force_newton": 3.5, "pressure_pascal": 1200},
        # 故意插入一个异常数据测试验证
        {"adjective": "轻揉", "force_newton": -1.0, "pressure_pascal": 0}, 
    ]

    # 2. 初始化系统
    config = SemanticEmbeddingConfig(embedding_dim=128)
    aligner = SemanticTactileAligner(config=config)

    try:
        # 3. 训练映射
        # 注意：pydantic validator 会过滤掉 force_newton < 0 的数据
        aligner.train_mapping(training_data)

        # 4. 执行指令
        user_command = "请重压这个零件"
        result = aligner.execute_command(user_command)

        print("-" * 30)
        print(f"指令: {user_command}")
        print(f"解析结果: {result['status']}")
        print(f"目标力度: {result['target_force_N']:.2f} N")
        print(f"允许公差: ±{result['force_tolerance_N']:.2f} N")
        print(f"向量维度: {len(result['semantic_vector'])}")
        print("-" * 30)

    except (ValueError, KeyError) as e:
        logger.error(f"System execution failed: {e}")