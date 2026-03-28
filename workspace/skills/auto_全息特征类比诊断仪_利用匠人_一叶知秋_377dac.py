"""
全息特征类比诊断仪

【全息特征类比诊断仪】利用匠人‘一叶知秋’的类比思维解决AI小样本问题。
当遇到罕见故障（样本<5），系统不再依赖统计学习，而是将故障信号（日志/堆栈）
映射为‘感官特征’（如波形尖锐度、频率异常），并在已有Skill库中寻找‘同构’的
已知故障（如将网络丢包类比为木材内部的暗裂），利用已知解决方案进行试探性修复。

领域: cross_domain
作者: AGI System Core
版本: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HolographicDiagnostician")


class SignalDomain(Enum):
    """信号域枚举，定义不同的工业/数字领域"""
    NETWORK = "network_traffic"
    MECHANICAL = "mechanical_vibration"
    SOFTWARE = "software_runtime"
    ELECTRONIC = "circuit_signal"


@dataclass
class SensoryFeature:
    """
    感官特征数据结构
    将原始信号转换为类似人类工匠感知的多维特征向量
    """
    sharpness: float  # 尖锐度（波形的突变程度，类比触觉的刺痛感）
    entropy: float    # 熵值（无序程度，类比视觉的模糊/浑浊度）
    rhythm: float     # 节奏异常（频率的规律性，类比听觉的律动）
    domain: SignalDomain
    raw_signature: str  # 原始信号的关键哈希或摘要

    def to_vector(self) -> np.ndarray:
        """将特征转换为用于计算的向量"""
        return np.array([self.sharpness, self.entropy, self.rhythm])


@dataclass
class KnownPattern:
    """
    已知故障模式
    存储在Skill库中的已知解决方案
    """
    name: str
    feature: SensoryFeature
    solution_code: str
    success_rate: float
    analogies: List[str] = field(default_factory=list)  # 类比描述，如"木材暗裂"


class HolographicDiagnostician:
    """
    全息特征类比诊断仪核心类
    
    利用小样本数据进行特征提取，并通过类比匹配寻找已知解决方案。
    实现了 '一叶知秋' 的推理逻辑。
    """

    def __init__(self, knowledge_base: List[KnownPattern]):
        """
        初始化诊断仪
        
        Args:
            knowledge_base (List[KnownPattern]): 预加载的已知故障模式库
        """
        self.knowledge_base = knowledge_base
        self._validate_knowledge_base()
        logger.info(f"诊断仪已初始化，加载了 {len(self.knowledge_base)} 个已知模式。")

    def _validate_knowledge_base(self) -> None:
        """验证知识库数据的有效性"""
        if not self.knowledge_base:
            logger.warning("知识库为空，将无法进行类比诊断。")

    def _extract_sensory_features(self, signal_data: Dict[str, Any]) -> SensoryFeature:
        """
        [辅助函数] 将原始信号映射为感官特征
        
        这是一个简化的模拟实现，实际场景中会使用FFT、小波分析或NLP Embedding。
        这里模拟了匠人通过“看、听、摸”将数据转化为直觉特征的过程。
        
        Args:
            signal_data (Dict[str, Any]): 包含 'log', 'metrics', 'domain' 的字典
            
        Returns:
            SensoryFeature: 提取出的特征对象
            
        Raises:
            ValueError: 如果输入数据缺少必要字段
        """
        if not all(k in signal_data for k in ['log', 'metrics', 'domain']):
            raise ValueError("输入数据必须包含 'log', 'metrics', 'domain' 字段")

        log_text = signal_data.get('log', '')
        metrics = signal_data.get('metrics', [])
        domain = SignalDomain(signal_data['domain'])

        # 模拟特征提取逻辑
        # 1. 尖锐度：基于日志中ERROR关键字的出现密度或指标的突变
        sharpness = min(1.0, log_text.upper().count('ERROR') * 0.2 + (max(metrics) - np.mean(metrics)) if metrics else 0)
        
        # 2. 熵：基于日志字符的混乱度或指标的方差
        entropy = min(1.0, np.var(metrics) * 10 if metrics else 0.5)
        
        # 3. 节奏：基于日志的时间间隔规律（此处简化为模拟值）
        rhythm = 0.6  # 默认值
        
        # 提取原始签名（简单的正则匹配模拟）
        signature_match = re.search(r'(0x[0-9a-fA-F]+|Exception: \w+)', log_text)
        raw_sig = signature_match.group(0) if signature_match else "unknown_signature"

        logger.debug(f"提取特征 -> 尖锐度:{sharpness:.2f}, 熵:{entropy:.2f}, 域:{domain.value}")
        
        return SensoryFeature(
            sharpness=round(sharpness, 2),
            entropy=round(entropy, 2),
            rhythm=round(rhythm, 2),
            domain=domain,
            raw_signature=raw_sig
        )

    def _calculate_isomorphism(self, f1: SensoryFeature, f2: SensoryFeature) -> float:
        """
        [辅助函数] 计算两个特征之间的同构度
        
        利用余弦相似度和域权重计算'同构性'。
        类比思维核心：不要求完全相同，只要结构（向量方向）相似。
        
        Args:
            f1 (SensoryFeature): 待诊断特征
            f2 (SensoryFeature): 已知特征
            
        Returns:
            float: 0.0 到 1.0 之间的相似度分数
        """
        v1 = f1.to_vector()
        v2 = f2.to_vector()
        
        # 余弦相似度
        dot_product = np.dot(v1, v2)
        norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
        cosine_sim = dot_product / norm_product if norm_product != 0 else 0.0
        
        # 域加权：如果领域不同，稍微降低分数，但允许跨域类比（全息原理）
        domain_penalty = 0.0 if f1.domain == f2.domain else 0.15
        
        score = max(0.0, (cosine_sim - domain_penalty))
        return score

    def diagnose(self, rare_fault_signal: Dict[str, Any], sample_count: int = 1) -> Optional[Tuple[KnownPattern, float, str]]:
        """
        [核心函数] 执行类比诊断
        
        当样本量极少时 (<5)，不使用统计学习，而是调用此方法。
        
        Args:
            rare_fault_signal (Dict): 故障信号数据
            sample_count (int): 当前拥有的样本数量（用于日志记录）
            
        Returns:
            Optional[Tuple[KnownPattern, float, str]]: 
                返回 (最佳匹配模式, 置信度, 类比解释)，如果没有匹配则返回None
        """
        if sample_count >= 5:
            logger.warning("样本充足，建议使用统计学习模型而非类比诊断。")
        
        try:
            # 1. 感官映射
            current_feature = self._extract_sensory_features(rare_fault_signal)
            logger.info(f"开始全息诊断：信号签名 {current_feature.raw_signature}")

            best_match: Optional[KnownPattern] = None
            highest_score = 0.0

            # 2. 全息扫描（在知识库中寻找同构结构）
            for pattern in self.knowledge_base:
                score = self._calculate_isomorphism(current_feature, pattern.feature)
                
                if score > highest_score:
                    highest_score = score
                    best_match = pattern
            
            # 3. 阈值判定
            if best_match and highest_score > 0.7:
                explanation = (
                    f"检测到同构特征 (Score: {highest_score:.2f})。"
                    f"虽然领域不同，但特征波形类似于 '{best_match.name}'。"
                    f"类比解释：正如 '{best_match.analogies[0] if best_match.analogies else '未知现象'}'。"
                )
                logger.info(f"诊断成功：匹配到已知模式 '{best_match.name}'")
                return best_match, highest_score, explanation
            else:
                logger.warning("未找到高置信度的同构匹配，建议人工介入。")
                return None

        except Exception as e:
            logger.error(f"诊断过程中发生异常: {str(e)}")
            return None

    def execute_trial_repair(self, solution_code: str) -> bool:
        """
        [核心函数] 执行试探性修复
        
        基于类比结果执行修复脚本。
        
        Args:
            solution_code (str): 从已知模式中提取的修复指令代码或标识符
            
        Returns:
            bool: 是否执行成功
        """
        logger.info(f"正在执行试探性修复方案: {solution_code}")
        # 模拟执行过程
        # 在真实场景中，这里会调用具体的执行器
        print(f"--- EXECUTING PATCH: {solution_code} ---")
        return True


# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 构建模拟知识库
    # 已知模式：网络丢包 - 类比为 "木材内部暗裂" (不易察觉但有结构性风险)
    known_network_glitch = KnownPattern(
        name="Network_Spike_Packet_Loss",
        feature=SensoryFeature(
            sharpness=0.8, entropy=0.3, rhythm=0.1, 
            domain=SignalDomain.NETWORK, 
            raw_signature="0xABCD"
        ),
        solution_code="sudo iptables -flush",
        success_rate=0.95,
        analogies=["木材内部的暗裂"]
    )

    # 初始化诊断仪
    diagnostician = HolographicDiagnostician(knowledge_base=[known_network_glitch])

    # 2. 模拟罕见故障信号 (样本<5)
    # 这是一个软件堆栈溢出的错误，但在波形特征上可能与网络丢包相似（突然的高尖锐度）
    rare_software_crash_log = """
    System Runtime Error [CRITICAL]
    Exception: SegFault (0x00000000)
    Stack overflow detected at 0xFFAABBCC
    """
    rare_software_metrics = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.9]  # 最后时刻突增

    input_signal = {
        'log': rare_software_crash_log,
        'metrics': rare_software_metrics,
        'domain': 'software_runtime'  # 注意：这是软件域，与知识库中的网络域不同
    }

    # 3. 执行诊断
    result = diagnostician.diagnose(input_signal, sample_count=1)

    if result:
        match, confidence, explanation = result
        print(f"\n>>> 诊断结果: {match.name}")
        print(f">>> 置信度: {confidence:.2f}")
        print(f">>> 解释: {explanation}")
        
        # 4. 试探性修复
        diagnostician.execute_trial_repair(match.solution_code)
    else:
        print("\n>>> 无法通过类比诊断确定故障原因。")