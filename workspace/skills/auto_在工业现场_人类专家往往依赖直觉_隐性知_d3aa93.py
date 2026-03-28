"""
工业现场人机共生故障诊断接口模块

该模块实现了一个将人类专家的直觉性隐性知识转化为机器可执行参数的
人机共生接口系统。核心功能包括：
1. 自然语言模糊输入的语义解析
2. 隐性知识到频谱分析参数的映射
3. 实时假设树修正与证伪

典型应用场景：
当专家说"这台泵声音不对"时，系统自动：
- 识别关键域（泵、声音）
- 提取特征指标（振动、噪音）
- 转化为频谱分析参数（FFT窗口大小、频率范围等）
- 生成修正后的假设树分支

数据格式：
输入：
{
    "text": "这台泵声音不对",
    "context": {"device_id": "PUMP_001", "location": "车间A"},
    "timestamp": "2023-11-15T14:30:00Z"
}

输出：
{
    "params": {
        "fft_window": 2048,
        "freq_range": [20, 2000],
        "window_type": "hann"
    },
    "hypothesis_adjustments": [
        {
            "node_id": "bearing_wear",
            "probability_delta": +0.15,
            "evidence": "声音异常通常与轴承磨损相关"
        }
    ]
}
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HumanMachineSymbiosis")


@dataclass
class AnalysisParameters:
    """频谱分析参数配置
    
    Attributes:
        fft_window: FFT窗口大小（必须是2的幂次）
        freq_range: 频率范围（最小频率，最大频率）
        window_type: 窗函数类型
        overlap: 窗口重叠比例（0-1）
        sensitivity: 异常检测灵敏度
    """
    fft_window: int = 1024
    freq_range: Tuple[float, float] = (20.0, 2000.0)
    window_type: str = "hann"
    overlap: float = 0.5
    sensitivity: float = 1.0
    
    def validate(self) -> bool:
        """验证参数合法性"""
        if not (self.fft_window & (self.fft_window - 1) == 0):
            raise ValueError(f"FFT窗口大小必须是2的幂次: {self.fft_window}")
        if not (0 <= self.overlap <= 1):
            raise ValueError(f"重叠比例必须在0-1之间: {self.overlap}")
        if self.freq_range[0] >= self.freq_range[1]:
            raise ValueError(f"无效的频率范围: {self.freq_range}")
        return True


@dataclass
class HypothesisNode:
    """假设树节点"""
    node_id: str
    description: str
    probability: float
    evidence: List[str] = field(default_factory=list)
    children: List['HypothesisNode'] = field(default_factory=list)


class NaturalLanguageParser:
    """自然语言解析器：将模糊描述转化为结构化特征"""
    
    # 领域关键词词典
    DOMAIN_KEYWORDS = {
        "设备": ["泵", "电机", "阀门", "压缩机", "风机"],
        "特征": ["声音", "振动", "温度", "压力", "流量"],
        "程度": ["轻微", "明显", "严重", "不对", "异常"],
        "时间": ["突然", "逐渐", "间歇"]
    }
    
    # 隐性知识映射规则
    KNOWLEDGE_MAPPING = {
        "声音": {
            "params": {"window_type": "hann", "sensitivity": 1.2},
            "hypotheses": ["bearing_wear", "imbalance", "misalignment"]
        },
        "振动": {
            "params": {"window_type": "hamming", "sensitivity": 1.5},
            "hypotheses": ["looseness", "resonance", "bearing_defect"]
        },
        "温度": {
            "params": {"window_type": "blackman", "sensitivity": 1.0},
            "hypotheses": ["overload", "cooling_issue", "friction"]
        }
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """预编译正则表达式提高性能"""
        self.device_pattern = re.compile(
            '|'.join(self.DOMAIN_KEYWORDS["设备"])
        )
        self.feature_pattern = re.compile(
            '|'.join(self.DOMAIN_KEYWORDS["特征"])
        )
    
    def parse_input(self, text: str) -> Dict[str, Union[str, List[str]]]:
        """解析自然语言输入
        
        Args:
            text: 输入文本（如"这台泵声音不对"）
            
        Returns:
            解析结果字典，包含：
            - devices: 识别的设备列表
            - features: 识别的特征列表
            - severity: 严重程度描述
            
        Example:
            >>> parser = NaturalLanguageParser()
            >>> parser.parse_input("泵的声音有点怪")
            {'devices': ['泵'], 'features': ['声音'], 'severity': '异常'}
        """
        try:
            devices = self.device_pattern.findall(text)
            features = self.feature_pattern.findall(text)
            
            # 分析严重程度
            severity = "normal"
            if any(word in text for word in ["不对", "异常", "严重"]):
                severity = "abnormal"
            elif any(word in text for word in ["轻微", "有点"]):
                severity = "minor"
            
            return {
                "devices": devices,
                "features": features,
                "severity": severity
            }
        except Exception as e:
            logger.error(f"自然语言解析失败: {str(e)}")
            raise


class ParameterGenerator:
    """参数生成器：将语义特征转化为分析参数"""
    
    def __init__(self):
        self.nl_parser = NaturalLanguageParser()
        self.default_params = AnalysisParameters()
    
    def _map_feature_to_params(
        self, 
        feature: str, 
        severity: str
    ) -> Tuple[Dict, float]:
        """将特征映射到参数调整
        
        Args:
            feature: 特征关键词（如"声音"）
            severity: 严重程度（normal/minor/abnormal）
            
        Returns:
            (参数调整字典, 假设概率增量)
        """
        if feature not in self.nl_parser.KNOWLEDGE_MAPPING:
            return {}, 0.0
        
        mapping = self.nl_parser.KNOWLEDGE_MAPPING[feature]
        param_adjustments = mapping["params"].copy()
        
        # 根据严重程度调整灵敏度
        if severity == "abnormal":
            param_adjustments["sensitivity"] *= 1.5
        elif severity == "minor":
            param_adjustments["sensitivity"] *= 0.8
        
        # 计算假设概率增量
        prob_delta = 0.1 if severity == "minor" else 0.2
        
        return param_adjustments, prob_delta
    
    def generate_parameters(
        self, 
        text: str, 
        current_params: Optional[AnalysisParameters] = None
    ) -> Tuple[AnalysisParameters, Dict[str, float]]:
        """生成修正后的分析参数
        
        Args:
            text: 专家输入的自然语言描述
            current_params: 当前使用的参数（可选）
            
        Returns:
            (新参数对象, 假设概率调整字典)
            
        Example:
            >>> generator = ParameterGenerator()
            >>> params, adjustments = generator.generate_parameters("泵振动严重异常")
        """
        try:
            # 解析自然语言
            parsed = self.nl_parser.parse_input(text)
            
            # 初始化参数
            if current_params is None:
                params = AnalysisParameters()
            else:
                params = current_params
            
            # 应用特征映射
            hypothesis_deltas = {}
            for feature in parsed["features"]:
                param_adj, prob_delta = self._map_feature_to_params(
                    feature, parsed["severity"]
                )
                
                # 更新参数
                for key, value in param_adj.items():
                    if hasattr(params, key):
                        setattr(params, key, value)
                
                # 记录假设调整
                if feature in self.nl_parser.KNOWLEDGE_MAPPING:
                    for hyp in self.nl_parser.KNOWLEDGE_MAPPING[feature]["hypotheses"]:
                        hypothesis_deltas[hyp] = hypothesis_deltas.get(hyp, 0) + prob_delta
            
            # 验证参数
            params.validate()
            
            return params, hypothesis_deltas
        
        except Exception as e:
            logger.error(f"参数生成失败: {str(e)}")
            raise


class HypothesisTreeManager:
    """假设树管理器：处理自上而下的证伪过程"""
    
    def __init__(self):
        self.root = HypothesisNode(
            node_id="root",
            description="设备异常",
            probability=0.5
        )
        self._initialize_tree()
    
    def _initialize_tree(self) -> None:
        """初始化标准假设树结构"""
        # 一级假设
        mechanical = HypothesisNode("mechanical", "机械故障", 0.3)
        electrical = HypothesisNode("electrical", "电气故障", 0.2)
        
        # 二级假设
        bearing = HypothesisNode("bearing_wear", "轴承磨损", 0.15, ["声音异常通常与轴承相关"])
        imbalance = HypothesisNode("imbalance", "不平衡", 0.1, ["振动特征明显"])
        
        mechanical.children.extend([bearing, imbalance])
        self.root.children.extend([mechanical, electrical])
    
    def adjust_hypotheses(
        self, 
        adjustments: Dict[str, float]
    ) -> List[Dict[str, Union[str, float]]]:
        """调整假设树概率
        
        Args:
            adjustments: {节点ID: 概率增量}字典
            
        Returns:
            修改后的节点列表
            
        Example:
            >>> manager = HypothesisTreeManager()
            >>> manager.adjust_hypotheses({"bearing_wear": 0.2})
        """
        modified_nodes = []
        
        def _adjust_node(node: HypothesisNode) -> None:
            if node.node_id in adjustments:
                delta = adjustments[node.node_id]
                node.probability = min(1.0, max(0.0, node.probability + delta))
                modified_nodes.append({
                    "node_id": node.node_id,
                    "description": node.description,
                    "new_probability": node.probability,
                    "delta": delta
                })
            
            for child in node.children:
                _adjust_node(child)
        
        _adjust_node(self.root)
        logger.info(f"已调整假设树: {len(modified_nodes)}个节点")
        
        return modified_nodes
    
    def get_most_probable(self, top_n: int = 3) -> List[Dict]:
        """获取概率最高的假设
        
        Args:
            top_n: 返回的最大假设数量
            
        Returns:
            按概率排序的假设列表
        """
        nodes = []
        
        def _collect_nodes(node: HypothesisNode) -> None:
            if node.node_id != "root":
                nodes.append({
                    "id": node.node_id,
                    "desc": node.description,
                    "prob": node.probability
                })
            for child in node.children:
                _collect_nodes(child)
        
        _collect_nodes(self.root)
        
        # 按概率降序排序
        nodes.sort(key=lambda x: x["prob"], reverse=True)
        return nodes[:top_n]


class HumanMachineSymbiosisInterface:
    """人机共生接口主类"""
    
    def __init__(self):
        self.param_generator = ParameterGenerator()
        self.hypothesis_manager = HypothesisTreeManager()
    
    def process_expert_input(
        self, 
        input_data: Dict
    ) -> Dict[str, Union[Dict, List]]:
        """处理专家输入并生成修正方案
        
        Args:
            input_data: 标准化输入数据（见模块文档）
            
        Returns:
            包含参数调整和假设修正的字典
            
        Example:
            >>> interface = HumanMachineSymbiosisInterface()
            >>> result = interface.process_expert_input({
            ...     "text": "泵的声音听起来不对劲",
            ...     "context": {"device_id": "PUMP_001"}
            ... })
        """
        try:
            # 输入验证
            if not input_data.get("text"):
                raise ValueError("输入文本不能为空")
            
            # 生成参数调整
            new_params, hyp_adjustments = self.param_generator.generate_parameters(
                input_data["text"]
            )
            
            # 修正假设树
            modified_nodes = self.hypothesis_manager.adjust_hypotheses(
                hyp_adjustments
            )
            
            # 生成输出
            output = {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "params": {
                    "fft_window": new_params.fft_window,
                    "freq_range": new_params.freq_range,
                    "window_type": new_params.window_type,
                    "sensitivity": new_params.sensitivity
                },
                "hypothesis_adjustments": modified_nodes,
                "top_hypotheses": self.hypothesis_manager.get_most_probable(),
                "context": input_data.get("context", {})
            }
            
            logger.info(f"成功处理专家输入: {input_data['text']}")
            return output
        
        except Exception as e:
            logger.error(f"处理专家输入失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# 使用示例
if __name__ == "__main__":
    # 初始化接口
    interface = HumanMachineSymbiosisInterface()
    
    # 示例1: 处理声音异常描述
    input1 = {
        "text": "这台泵的声音听起来不对劲",
        "context": {"device_id": "PUMP_001", "location": "车间A"}
    }
    result1 = interface.process_expert_input(input1)
    print("处理结果1:")
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    
    # 示例2: 处理振动异常描述
    input2 = {
        "text": "电机振动明显异常",
        "context": {"device_id": "MOTOR_102"}
    }
    result2 = interface.process_expert_input(input2)
    print("\n处理结果2:")
    print(json.dumps(result2, indent=2, ensure_ascii=False))