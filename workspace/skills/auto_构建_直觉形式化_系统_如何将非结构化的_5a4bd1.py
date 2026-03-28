"""
直觉形式化系统

该模块提供了一个将非结构化的、潜意识的专家直觉转化为显性的、可执行的结构化代码的框架。
重点在于捕捉'非典型成功案例'中的隐性特征。

典型应用场景：
1. 老中医把脉诊断
2. 资深司机的预判驾驶
3. 艺术鉴赏家的真伪辨别
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeatureType(Enum):
    """特征类型枚举"""
    EXPLICIT = auto()    # 显性特征（如体温、血压）
    IMPLICIT = auto()    # 隐性特征（如把脉时的细微波动）
    CONTEXTUAL = auto()  # 环境特征（如天气、时间）

@dataclass
class Feature:
    """特征数据结构"""
    name: str
    value: Any
    type: FeatureType
    weight: float = 1.0  # 特征权重（0.0-1.0）
    description: str = ""

@dataclass
class ExpertCase:
    """专家案例数据结构"""
    case_id: str
    features: Dict[str, Feature]
    outcome: Any
    is_typical: bool = False  # 是否为典型成功案例
    metadata: Dict[str, Any] = field(default_factory=dict)

class IntuitionFormalizationSystem:
    """直觉形式化系统主类"""
    
    def __init__(self, feature_names: List[str], threshold: float = 0.7):
        """
        初始化直觉形式化系统
        
        参数:
            feature_names: 特征名称列表
            threshold: 决策阈值(0.0-1.0)
        """
        if not feature_names:
            raise ValueError("特征名称列表不能为空")
        
        if not 0 <= threshold <= 1:
            raise ValueError("阈值必须在0.0到1.0之间")
            
        self.feature_names = feature_names
        self.threshold = threshold
        self.knowledge_base: List[ExpertCase] = []
        self.feature_weights: Dict[str, float] = {name: 1.0 for name in feature_names}
        
        logger.info("初始化直觉形式化系统，特征数量: %d, 阈值: %.2f", 
                   len(feature_names), threshold)
    
    def add_expert_case(self, case: ExpertCase) -> None:
        """
        添加专家案例到知识库
        
        参数:
            case: 专家案例对象
            
        异常:
            ValueError: 如果案例特征与系统不匹配
        """
        # 验证案例特征是否匹配系统定义
        missing_features = set(self.feature_names) - set(case.features.keys())
        if missing_features:
            raise ValueError(f"案例缺少必需的特征: {missing_features}")
            
        self.knowledge_base.append(case)
        logger.debug("添加案例 %s 到知识库，当前案例数: %d", 
                    case.case_id, len(self.knowledge_base))
        
        # 如果是非典型成功案例，更新特征权重
        if not case.is_typical and case.outcome == "success":
            self._update_feature_weights(case)
    
    def formalize_intuition(self, input_features: Dict[str, Any]) -> Tuple[bool, float]:
        """
        将输入特征形式化为决策结果
        
        参数:
            input_features: 输入特征字典
            
        返回:
            Tuple[决策结果(bool), 置信度(float)]
            
        异常:
            ValueError: 如果输入特征不完整
        """
        # 验证输入特征完整性
        self._validate_input_features(input_features)
        
        # 转换为特征对象
        features = {
            name: Feature(
                name=name,
                value=value,
                type=self._determine_feature_type(name),
                weight=self.feature_weights[name]
            )
            for name, value in input_features.items()
        }
        
        # 计算与知识库中案例的相似度
        similarities = []
        for case in self.knowledge_base:
            similarity = self._calculate_case_similarity(features, case.features)
            similarities.append((similarity, case))
        
        if not similarities:
            logger.warning("知识库为空，无法做出决策")
            return False, 0.0
        
        # 加权平均决策
        weighted_sum = 0.0
        total_weight = 0.0
        for sim, case in similarities:
            outcome_value = 1.0 if case.outcome == "success" else 0.0
            weighted_sum += sim * outcome_value * (2.0 if not case.is_typical else 1.0)
            total_weight += sim
        
        confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
        decision = confidence >= self.threshold
        
        logger.info("形式化决策结果: %s, 置信度: %.2f", decision, confidence)
        return decision, confidence
    
    def _update_feature_weights(self, case: ExpertCase) -> None:
        """
        更新特征权重（基于非典型成功案例）
        
        参数:
            case: 非典型成功案例
        """
        for name, feature in case.features.items():
            # 对于非典型案例，增加其特征的权重
            if feature.type == FeatureType.IMPLICIT:
                increment = 0.1 * feature.weight
                self.feature_weights[name] = min(1.0, self.feature_weights[name] + increment)
                logger.debug("更新特征 %s 权重: %.2f (+%.2f)", 
                            name, self.feature_weights[name], increment)
    
    def _validate_input_features(self, features: Dict[str, Any]) -> None:
        """验证输入特征的完整性"""
        missing = set(self.feature_names) - set(features.keys())
        if missing:
            raise ValueError(f"输入缺少特征: {missing}")
    
    def _determine_feature_type(self, feature_name: str) -> FeatureType:
        """
        确定特征类型（辅助函数）
        
        参数:
            feature_name: 特征名称
            
        返回:
            特征类型枚举
        """
        # 简单规则：根据名称判断类型
        if any(keyword in feature_name.lower() for keyword in ["隐性", "implicit", "微妙"]):
            return FeatureType.IMPLICIT
        elif any(keyword in feature_name.lower() for keyword in ["环境", "context", "时间"]):
            return FeatureType.CONTEXTUAL
        return FeatureType.EXPLICIT
    
    def _calculate_case_similarity(self, 
                                 features1: Dict[str, Feature], 
                                 features2: Dict[str, Feature]) -> float:
        """
        计算两个案例之间的相似度
        
        参数:
            features1: 第一个案例的特征
            features2: 第二个案例的特征
            
        返回:
            相似度分数(0.0-1.0)
        """
        total_sim = 0.0
        total_weight = 0.0
        
        for name in self.feature_names:
            f1 = features1[name]
            f2 = features2[name]
            
            # 计算单个特征的相似度
            if isinstance(f1.value, (int, float)) and isinstance(f2.value, (int, float)):
                # 数值特征：使用高斯相似度
                diff = abs(f1.value - f2.value)
                range_ = max(abs(f1.value), abs(f2.value), 1.0)  # 避免除零
                sim = np.exp(-diff**2 / (2 * (range_/2)**2))
            else:
                # 分类特征：精确匹配
                sim = 1.0 if f1.value == f2.value else 0.0
            
            # 加权相似度
            weight = (f1.weight + f2.weight) / 2
            total_sim += sim * weight
            total_weight += weight
        
        return total_sim / total_weight if total_weight > 0 else 0.0

    def get_feature_importance_report(self) -> Dict[str, float]:
        """
        生成特征重要性报告
        
        返回:
            特征权重字典
        """
        return {
            "feature_importance": self.feature_weights,
            "total_cases": len(self.knowledge_base),
            "atypical_cases": sum(1 for case in self.knowledge_base if not case.is_typical)
        }

# 使用示例
if __name__ == "__main__":
    # 1. 定义系统特征（老中医诊断系统）
    features = [
        "脉搏频率", "脉搏力度", "脉搏节律",  # 显性特征
        "脉象微妙变化", "脉管弹性",         # 隐性特征
        "诊断时间", "患者体位"              # 环境特征
    ]
    
    # 2. 初始化系统
    system = IntuitionFormalizationSystem(features, threshold=0.75)
    
    # 3. 添加专家案例
    typical_case = ExpertCase(
        case_id="typical_001",
        features={
            "脉搏频率": Feature("脉搏频率", 72, FeatureType.EXPLICIT),
            "脉搏力度": Feature("脉搏力度", "中等", FeatureType.EXPLICIT),
            "脉搏节律": Feature("脉搏节律", "规律", FeatureType.EXPLICIT),
            "脉象微妙变化": Feature("脉象微妙变化", "滑脉", FeatureType.IMPLICIT, weight=1.2),
            "脉管弹性": Feature("脉管弹性", "良好", FeatureType.IMPLICIT),
            "诊断时间": Feature("诊断时间", "上午", FeatureType.CONTEXTUAL),
            "患者体位": Feature("患者体位", "坐姿", FeatureType.CONTEXTUAL)
        },
        outcome="success",
        is_typical=True,
        metadata={"doctor": "王医生", "patient_age": 45}
    )
    
    # 非典型成功案例（隐性特征更重要）
    atypical_case = ExpertCase(
        case_id="atypical_001",
        features={
            "脉搏频率": Feature("脉搏频率", 68, FeatureType.EXPLICIT),
            "脉搏力度": Feature("脉搏力度", "偏弱", FeatureType.EXPLICIT),
            "脉搏节律": Feature("脉搏节律", "轻微不规律", FeatureType.EXPLICIT),
            "脉象微妙变化": Feature("脉象微妙变化", "细脉", FeatureType.IMPLICIT, weight=1.5),
            "脉管弹性": Feature("脉管弹性", "较差", FeatureType.IMPLICIT, weight=1.3),
            "诊断时间": Feature("诊断时间", "下午", FeatureType.CONTEXTUAL),
            "患者体位": Feature("患者体位", "卧姿", FeatureType.CONTEXTUAL)
        },
        outcome="success",
        is_typical=False,
        metadata={"doctor": "李医生", "patient_age": 72, "notes": "复杂病例"}
    )
    
    system.add_expert_case(typical_case)
    system.add_expert_case(atypical_case)
    
    # 4. 形式化新案例
    new_case_features = {
        "脉搏频率": 70,
        "脉搏力度": "中等偏弱",
        "脉搏节律": "轻微不规律",
        "脉象微妙变化": "细脉",
        "脉管弹性": "较差",
        "诊断时间": "下午",
        "患者体位": "坐姿"
    }
    
    decision, confidence = system.formalize_intuition(new_case_features)
    print(f"决策结果: {'成功' if decision else '失败'}, 置信度: {confidence:.2f}")
    
    # 5. 查看特征重要性
    report = system.get_feature_importance_report()
    print("\n特征重要性报告:")
    for feature, weight in report["feature_importance"].items():
        print(f"{feature}: {weight:.2f}")