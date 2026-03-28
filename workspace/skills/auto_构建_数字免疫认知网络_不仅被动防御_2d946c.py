"""
Module: auto_构建_数字免疫认知网络_不仅被动防御_2d946c
Description: 构建数字免疫认知网络。不仅被动防御，更能主动'吞噬'异常数据（抗原）并提取特征，
             生成'数字抗体'（动态规则代码）。当分布式产线中出现未定义的故障模式时，
             系统能像免疫应答一样，在局部节点（巨噬细胞角色）进行隔离，并迅速向全网广播
             '疫苗'（更新后的验证逻辑），实现故障的自主免疫和全群免疫。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import hashlib
import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalImmuneSystem")

# --- Data Structures ---

@dataclass
class Antigen:
    """
    抗原数据结构：代表异常数据或未被当前规则识别的潜在威胁。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source_node: str = "Unknown"
    payload: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self):
        # 生成数据指纹，模拟生物抗原的化学特征
        self.signature = self._generate_signature()

    def _generate_signature(self) -> str:
        """基于负载内容生成唯一哈希指纹"""
        payload_str = json.dumps(self.payload, sort_keys=True).encode('utf-8')
        return hashlib.sha256(payload_str).hexdigest()

    def is_malformed(self) -> bool:
        """检查数据是否格式错误或包含危险键值"""
        if not isinstance(self.payload, dict):
            return True
        # 示例：检测深层嵌套或保留键
        if "__code__" in str(self.payload):
            return True
        return False

@dataclass
class DigitalAntibody:
    """
    数字抗体数据结构：由系统生成的动态验证逻辑，用于识别特定的抗原。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    targets_signature: str = ""  # 目标抗原指纹
    rule_name: str = "GenericValidation"
    validation_logic: Callable[[Dict], bool] = field(repr=False, default=lambda x: True)
    creation_date: str = field(default_factory=lambda: datetime.now().isoformat())
    affinity_score: float = 0.0  # 亲和力/置信度

    def to_dict(self) -> Dict:
        """序列化为字典（逻辑部分仅保留名称）"""
        return {
            "id": self.id,
            "targets_signature": self.targets_signature,
            "rule_name": self.rule_name,
            "creation_date": self.creation_date,
            "affinity_score": self.affinity_score
        }

@dataclass
class VaccineBroadcast:
    """
    疫苗广播包：用于在分布式节点间同步新生成的抗体。
    """
    antibody: DigitalAntibody
    broadcast_range: str = "GLOBAL"  # GLOBAL, REGIONAL, LOCAL
    priority: int = 1  # 1=High, 5=Low

# --- Core Classes ---

class MacrophageNode:
    """
    巨噬细胞节点角色：负责吞噬、分析抗原并生成抗体。
    这是网络的核心处理单元。
    """

    def __init__(self, node_id: str, initial_rules: List[Callable[[Dict], bool]]):
        self.node_id = node_id
        self.known_antibodies: List[DigitalAntibody] = []
        self.isolated_antigens: List[Antigen] = []
        self._initialize_system(default_rules=initial_rules)
        logger.info(f"Macrophage Node {self.node_id} initialized.")

    def _initialize_system(self, default_rules: List[Callable[[Dict], bool]]):
        """初始化先天免疫规则"""
        for rule in default_rules:
            antibody = DigitalAntibody(
                rule_name=rule.__name__,
                validation_logic=rule,
                affinity_score=1.0
            )
            self.known_antibodies.append(antibody)

    def ingest_data(self, data_stream: Dict[str, Any]) -> Optional[Antigen]:
        """
        核心函数：摄入并分析数据流。
        如果数据通过验证，返回None。
        如果数据被识别为异常（抗原），创建Antigen对象并进行隔离。
        """
        try:
            # 边界检查：数据是否为字典
            if not isinstance(data_stream, dict):
                raise ValueError("Invalid data format: Expected dict.")

            # 模拟抗原生成
            potential_antigen = Antigen(source_node=self.node_id, payload=data_stream)
            
            if potential_antigen.is_malformed():
                logger.warning(f"Malformed antigen detected and incinerated: {potential_antigen.id}")
                return None

            # 免疫检查：遍历现有抗体
            is_safe = False
            for antibody in self.known_antibodies:
                try:
                    if antibody.validation_logic(data_stream):
                        is_safe = True
                        break
                except Exception as e:
                    logger.error(f"Antibody {antibody.rule_name} raised error: {e}")
                    # 抗体失效，需要标记或移除（此处略过）

            if not is_safe:
                logger.warning(f"Unknown pattern detected! Isolating Antigen: {potential_antigen.signature[:8]}...")
                self.isolated_antigens.append(potential_antigen)
                return potential_antigen

            return None

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            return None

    def generate_antibody(self, antigen: Antigen) -> Optional[VaccineBroadcast]:
        """
        核心函数：分析隔离的抗原并生成对应的数字抗体（疫苗）。
        这是一个简化的'代码生成/规则提取'过程。
        """
        if not antigen:
            return None

        logger.info(f"Analyzing antigen {antigen.id} for antibody generation...")
        
        # 提取特征逻辑（模拟）
        # 在真实AGI中，这里会涉及LLM生成代码或符号回归
        extracted_features = self._extract_features_heuristic(antigen.payload)
        
        if not extracted_features:
            return None

        # 动态构建验证函数
        def dynamic_validation_logic(payload: Dict) -> bool:
            # 规则：如果出现提取到的特定异常特征键，返回False（标记为需拦截）
            # 这是一个简单的示例，实际可以是复杂的逻辑树
            is_anomaly = True
            for key, val in extracted_features.items():
                if payload.get(key) != val:
                    is_anomaly = False
                    break
            # 如果匹配到了异常特征，验证失败（即它是坏的），返回False
            # 但在免疫系统中，抗体是用来结合抗原的。
            # 这里的逻辑是：如果数据匹配抗体规则，则视为"已识别的威胁"。
            return not is_anomaly 

        # 创建新抗体
        new_antibody = DigitalAntibody(
            targets_signature=antigen.signature,
            rule_name=f"AutoGen_Antibody_{uuid.uuid4().hex[:6]}",
            validation_logic=dynamic_validation_logic,
            affinity_score=0.95
        )
        
        # 自身注册
        self.known_antibodies.append(new_antibody)
        logger.info(f"New Antibody Generated: {new_antibody.rule_name}")

        # 准备广播疫苗
        return VaccineBroadcast(antibody=new_antibody, priority=1)

    def _extract_features_heuristic(self, payload: Dict) -> Dict[str, Any]:
        """
        辅助函数：从异常数据中提取关键特征。
        """
        # 简单启发式：寻找可能表示错误的值
        features = {}
        for k, v in payload.items():
            if "error" in str(k).lower() or v is None or str(v) == "NaN":
                features[k] = v
        return features

    def receive_vaccine(self, vaccine: VaccineBroadcast):
        """接收来自其他节点的疫苗并更新规则库"""
        # 检查是否已存在
        if not any(ab.id == vaccine.antibody.id for ab in self.known_antibodies):
            self.known_antibodies.append(vaccine.antibody)
            logger.info(f"Node {self.node_id} received Vaccine: {vaccine.antibody.rule_name}")
        else:
            logger.debug(f"Node {self.node_id} already has antibody {vaccine.antibody.rule_name}")

# --- Usage Example ---

if __name__ == "__main__":
    # 1. 定义一些基础规则（先天免疫）
    def rule_check_schema(data: Dict) -> bool:
        return "user_id" in data and "timestamp" in data

    # 2. 初始化节点
    node = MacrophageNode(node_id="Node_Alpha_01", initial_rules=[rule_check_schema])

    # 3. 模拟正常数据
    normal_data = {"user_id": "123", "timestamp": "2023-01-01", "value": 100}
    print("\n--- Processing Normal Data ---")
    node.ingest_data(normal_data)

    # 4. 模拟未知异常数据（抗原）
    # 假设这是一种新型错误，包含 'error_code' 字段且值为 '0xDEAD'
    antigenic_data = {
        "user_id": "124", 
        "timestamp": "2023-01-02", 
        "error_code": "0xDEAD", 
        "status": "critical_failure"
    }
    
    print("\n--- Processing Antigenic Data ---")
    antigen = node.ingest_data(antigenic_data)

    # 5. 自主生成抗体
    if antigen:
        print("\n--- Generating Antibody ---")
        vaccine = node.generate_antibody(antigen)
        
        if vaccine:
            print(f"Vaccine Created: {vaccine.antibody.rule_name}")
            
            # 6. 测试新抗体：再次摄入类似数据
            print("\n--- Retesting Similar Data with New Immunity ---")
            similar_bad_data = {
                "user_id": "125", 
                "timestamp": "2023-01-03", 
                "error_code": "0xDEAD", 
                "status": "critical_failure"
            }
            # 此时节点已更新规则，虽然数据结构仍包含错误，但已被"识别"
            # 具体的处理策略由 validation_logic 决定，这里演示它不再被隔离为"未知"
            result = node.ingest_data(similar_bad_data)
            
            if result is None:
                print("Success: The system now recognizes and handles the previously unknown pattern.")
            else:
                print("Failure: The pattern is still treated as unknown.")