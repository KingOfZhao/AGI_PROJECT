"""
模块名称: auto_一种具有批判性思维的抗干扰数据处理范式_70753f
描述: 一种具有批判性思维的抗干扰数据处理范式。传统系统追求‘去噪’，而该概念视‘异常’（脏数据、反直觉结论、执行报错）为高价值的‘负样本’。系统在处理信息时，会主动启动‘自上而下拆解证伪’流程，模拟‘魔鬼代言人’生成对抗性攻击，或利用‘反事实’逻辑进行压力测试。只有通过这一辩证过程的数据才能被接纳，从而消除‘表象偏差’，挖掘出隐藏在混乱之下的真实逻辑。
领域: cross_domain
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataStatus(Enum):
    """数据状态枚举"""
    RAW = "raw"  # 原始数据
    CLEAN = "clean"  # 清洗后的数据
    SUSPICIOUS = "suspicious"  # 可疑数据
    VALIDATED = "validated"  # 已验证数据
    REJECTED = "rejected"  # 拒绝的数据

@dataclass
class DataPoint:
    """数据点结构"""
    id: str
    content: Any
    status: DataStatus = DataStatus.RAW
    metadata: Optional[Dict[str, Any]] = None
    validation_score: float = 0.0
    counter_arguments: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.counter_arguments is None:
            self.counter_arguments = []

class CriticalDataProcessor:
    """
    具有批判性思维的抗干扰数据处理系统
    
    该系统不简单地去噪，而是通过辩证过程验证数据，将异常视为潜在的高价值负样本。
    
    输入格式:
        - 支持字典格式的原始数据，必须包含'id'和'content'字段
        - 示例: {'id': 'data_001', 'content': 'The sky is green', 'metadata': {'source': 'user_input'}}
    
    输出格式:
        - 返回DataPoint对象，包含处理状态和验证分数
        - 示例: DataPoint(id='data_001', content='The sky is green', status=DataStatus.REJECTED, validation_score=0.2)
    """
    
    def __init__(self, validation_threshold: float = 0.7, max_counter_args: int = 3):
        """
        初始化处理器
        
        Args:
            validation_threshold: 验证阈值，高于此值的数据被认为是有效的
            max_counter_args: 最大生成对抗性参数数量
        """
        self.validation_threshold = validation_threshold
        self.max_counter_args = max_counter_args
        self._validation_rules = []
        self._counter_argument_generators = []
        
        # 默认验证规则
        self._register_default_validation_rules()
        # 默认对抗性参数生成器
        self._register_default_counter_generators()
        
        logger.info("CriticalDataProcessor initialized with threshold %.2f", validation_threshold)
    
    def _register_default_validation_rules(self) -> None:
        """注册默认的数据验证规则"""
        # 规则1: 检查空值或None
        self._validation_rules.append(
            lambda data: 0.0 if data.content is None or data.content == "" else 1.0
        )
        
        # 规则2: 检查数据一致性 (简单示例)
        self._validation_rules.append(
            lambda data: 0.5 if isinstance(data.content, str) and len(data.content) > 1000 else 1.0
        )
        
        # 规则3: 检查数值合理性
        self._validation_rules.append(
            lambda data: 0.0 if isinstance(data.content, (int, float)) and (data.content > 1e6 or data.content < -1e6) else 1.0
        )
        
        logger.debug("Registered %d default validation rules", len(self._validation_rules))
    
    def _register_default_counter_generators(self) -> None:
        """注册默认的对抗性参数生成器"""
        # 生成器1: 反事实测试
        self._counter_argument_generators.append(
            lambda data: f"What if the opposite of '{data.content}' is true?"
        )
        
        # 生成器2: 边界情况测试
        self._counter_argument_generators.append(
            lambda data: f"Does '{data.content}' hold true in extreme conditions?"
        )
        
        # 生成器3: 上下文依赖性测试
        self._counter_argument_generators.append(
            lambda data: f"Is '{data.content}' dependent on unstated assumptions?"
        )
        
        logger.debug("Registered %d default counter-argument generators", len(self._counter_argument_generators))
    
    def add_validation_rule(self, rule: Callable[[DataPoint], float]) -> None:
        """
        添加自定义验证规则
        
        Args:
            rule: 接受DataPoint并返回0.0-1.0之间分数的函数
        """
        if not callable(rule):
            raise ValueError("Validation rule must be callable")
        
        self._validation_rules.append(rule)
        logger.info("Added custom validation rule")
    
    def add_counter_generator(self, generator: Callable[[DataPoint], str]) -> None:
        """
        添加自定义对抗性参数生成器
        
        Args:
            generator: 接受DataPoint并返回对抗性字符串的函数
        """
        if not callable(generator):
            raise ValueError("Counter-argument generator must be callable")
        
        self._counter_argument_generators.append(generator)
        logger.info("Added custom counter-argument generator")
    
    def _apply_validation_rules(self, data: DataPoint) -> float:
        """
        应用所有验证规则并计算平均分数
        
        Args:
            data: 要验证的数据点
            
        Returns:
            0.0到1.0之间的验证分数
        """
        if not self._validation_rules:
            logger.warning("No validation rules registered")
            return 1.0
        
        scores = []
        for rule in self._validation_rules:
            try:
                score = rule(data)
                if not 0.0 <= score <= 1.0:
                    logger.warning("Rule returned invalid score %.2f, clamping to [0,1]", score)
                    score = max(0.0, min(1.0, score))
                scores.append(score)
            except Exception as e:
                logger.error("Validation rule failed: %s", str(e))
                scores.append(0.0)  # 失败的规则给予0分
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_counter_arguments(self, data: DataPoint) -> List[str]:
        """
        为数据生成对抗性参数
        
        Args:
            data: 要测试的数据点
            
        Returns:
            对抗性参数列表
        """
        counter_args = []
        for generator in self._counter_argument_generators[:self.max_counter_args]:
            try:
                arg = generator(data)
                if arg:
                    counter_args.append(arg)
            except Exception as e:
                logger.error("Counter-argument generator failed: %s", str(e))
        
        return counter_args
    
    def _apply_counter_arguments(self, data: DataPoint, counter_args: List[str]) -> float:
        """
        应用对抗性参数并计算数据点的抗性分数
        
        Args:
            data: 要测试的数据点
            counter_args: 对抗性参数列表
            
        Returns:
            0.0到1.0之间的抗性分数
        """
        if not counter_args:
            return 1.0
        
        resistance_scores = []
        for arg in counter_args:
            # 简化的抗性计算 - 实际应用中可能需要更复杂的逻辑
            if "opposite" in arg.lower():
                # 反事实测试 - 数据点需要能自我证明
                score = 0.7 if self._has_self_evidence(data) else 0.3
            elif "extreme" in arg.lower():
                # 边界情况测试 - 检查数据是否有边界约束
                score = 0.8 if self._has_boundary_conditions(data) else 0.4
            else:
                # 默认抗性分数
                score = 0.5
            
            resistance_scores.append(score)
        
        return sum(resistance_scores) / len(resistance_scores) if resistance_scores else 0.0
    
    def _has_self_evidence(self, data: DataPoint) -> bool:
        """检查数据点是否包含自证逻辑"""
        if isinstance(data.content, str):
            return any(word in data.content.lower() for word in ["because", "since", "therefore", "proved"])
        return False
    
    def _has_boundary_conditions(self, data: DataPoint) -> bool:
        """检查数据点是否有明确的边界条件"""
        if isinstance(data.content, str):
            return any(word in data.content.lower() for word in ["only", "except", "when", "if"])
        return False
    
    def process_data_point(self, raw_data: Dict[str, Any]) -> DataPoint:
        """
        处理单个数据点，应用批判性思维验证
        
        Args:
            raw_data: 原始数据字典
            
        Returns:
            处理后的DataPoint对象
        """
        # 数据验证
        if not isinstance(raw_data, dict):
            raise ValueError("Input must be a dictionary")
        
        if "id" not in raw_data or "content" not in raw_data:
            raise ValueError("Input must contain 'id' and 'content' fields")
        
        # 创建数据点
        data_point = DataPoint(
            id=raw_data["id"],
            content=raw_data["content"],
            metadata=raw_data.get("metadata", {})
        )
        
        logger.info("Processing data point: %s", data_point.id)
        
        # 1. 应用验证规则
        validation_score = self._apply_validation_rules(data_point)
        data_point.validation_score = validation_score
        
        # 2. 生成对抗性参数
        counter_args = self._generate_counter_arguments(data_point)
        data_point.counter_arguments = counter_args
        
        # 3. 应用对抗性参数测试
        resistance_score = self._apply_counter_arguments(data_point, counter_args)
        
        # 4. 综合评估
        final_score = (validation_score * 0.6) + (resistance_score * 0.4)
        
        # 5. 确定状态
        if final_score >= self.validation_threshold:
            data_point.status = DataStatus.VALIDATED
            logger.info("Data point %s validated with score %.2f", data_point.id, final_score)
        else:
            data_point.status = DataStatus.REJECTED
            logger.warning("Data point %s rejected with score %.2f", data_point.id, final_score)
        
        return data_point
    
    def process_batch(self, raw_data_list: List[Dict[str, Any]]) -> List[DataPoint]:
        """
        批量处理数据点
        
        Args:
            raw_data_list: 原始数据字典列表
            
        Returns:
            处理后的DataPoint对象列表
        """
        if not isinstance(raw_data_list, list):
            raise ValueError("Input must be a list of dictionaries")
        
        processed_data = []
        for i, raw_data in enumerate(raw_data_list):
            try:
                processed = self.process_data_point(raw_data)
                processed_data.append(processed)
            except Exception as e:
                logger.error("Failed to process data point at index %d: %s", i, str(e))
                # 创建一个失败的数据点
                failed_data = DataPoint(
                    id=raw_data.get("id", f"failed_{i}"),
                    content=raw_data.get("content", None),
                    status=DataStatus.REJECTED,
                    metadata={"error": str(e)}
                )
                processed_data.append(failed_data)
        
        return processed_data
    
    def get_statistics(self, processed_data: List[DataPoint]) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Args:
            processed_data: 处理后的数据点列表
            
        Returns:
            包含统计信息的字典
        """
        if not processed_data:
            return {"total": 0, "validated": 0, "rejected": 0, "validation_rate": 0.0}
        
        validated = sum(1 for d in processed_data if d.status == DataStatus.VALIDATED)
        rejected = len(processed_data) - validated
        
        return {
            "total": len(processed_data),
            "validated": validated,
            "rejected": rejected,
            "validation_rate": validated / len(processed_data) if processed_data else 0.0,
            "average_score": sum(d.validation_score for d in processed_data) / len(processed_data)
        }

# 使用示例
if __name__ == "__main__":
    # 示例数据
    test_data = [
        {
            "id": "data_001",
            "content": "The sky is blue because of Rayleigh scattering",
            "metadata": {"source": "science_book"}
        },
        {
            "id": "data_002",
            "content": "The Earth is flat",
            "metadata": {"source": "conspiracy_theory"}
        },
        {
            "id": "data_003",
            "content": 123456789,
            "metadata": {"source": "sensor_reading"}
        },
        {
            "id": "data_004",
            "content": "This statement is false",
            "metadata": {"source": "paradox"}
        }
    ]
    
    # 初始化处理器
    processor = CriticalDataProcessor(validation_threshold=0.65)
    
    # 添加自定义验证规则
    def custom_length_rule(data: DataPoint) -> float:
        """检查内容长度是否合理"""
        if isinstance(data.content, str):
            return 1.0 if 10 < len(data.content) < 500 else 0.5
        return 0.8  # 非字符串数据
    
    processor.add_validation_rule(custom_length_rule)
    
    # 处理数据
    processed_results = processor.process_batch(test_data)
    
    # 输出结果
    print("\nProcessing Results:")
    for result in processed_results:
        print(f"ID: {result.id}")
        print(f"Content: {result.content}")
        print(f"Status: {result.status.value}")
        print(f"Score: {result.validation_score:.2f}")
        print("Counter Arguments:")
        for arg in result.counter_arguments:
            print(f"  - {arg}")
        print("-" * 50)
    
    # 获取统计信息
    stats = processor.get_statistics(processed_results)
    print("\nStatistics:")
    print(f"Total processed: {stats['total']}")
    print(f"Validated: {stats['validated']}")
    print(f"Rejected: {stats['rejected']}")
    print(f"Validation rate: {stats['validation_rate']:.1%}")
    print(f"Average score: {stats['average_score']:.2f}")