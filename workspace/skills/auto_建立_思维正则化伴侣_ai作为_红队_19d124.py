"""
高级技能模块: 思维正则化伴侣

该模块实现了AI作为'红队'角色的核心逻辑，旨在检测人类专家的'认知过拟合'现象，
并通过'认知Dropout'机制引入噪声或屏蔽特定假设，强迫思维跳出局部最优解，
从而保持认知网络的稀疏性与鲁棒性。
"""

import logging
import random
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveState(Enum):
    """认知状态枚举"""
    NORMAL = "normal"
    OVERFITTING_SUSPECTED = "overfitting_suspected"
    REGULARIZED = "regularized"

@dataclass
class ExpertDecision:
    """
    专家决策数据结构
    
    Attributes:
        context (str): 决策背景描述
        core_assumptions (List[str]): 决策所依赖的核心假设或经验
        reasoning_chain (str): 决策的推理过程文本
        confidence (float): 决策的信心度 (0.0 - 1.0)
    """
    context: str
    core_assumptions: List[str]
    reasoning_chain: str
    confidence: float

    def __post_init__(self):
        """数据验证"""
        if not self.core_assumptions:
            raise ValueError("核心假设列表不能为空")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("信心度必须在0.0到1.0之间")

@dataclass
class RedTeamReport:
    """
    红队检测报告
    
    Attributes:
        status (CognitiveState): 当前认知状态
        overfitting_score (float): 过拟合评分 (0-100)
        alerts (List[str]): 检测到的具体风险点
        regularized_scenario (Optional[str]): 经过Dropout处理后的新场景描述
    """
    status: CognitiveState
    overfitting_score: float
    alerts: List[str] = field(default_factory=list)
    regularized_scenario: Optional[str] = None

class CognitiveRegularizationCompanion:
    """
    思维正则化伴侣 AI
    
    作为红队角色，检测认知过拟合并应用认知Dropout机制。
    """
    
    def __init__(self, overfitting_threshold: float = 0.75, dropout_rate: float = 0.3):
        """
        初始化伴侣
        
        Args:
            overfitting_threshold (float): 判定为过拟合的阈值
            dropout_rate (float): 认知Dropout的概率 (0.0-1.0)
        """
        if not 0 <= dropout_rate <= 1:
            raise ValueError("Dropout rate 必须在 0 和 1 之间")
            
        self.overfitting_threshold = overfitting_threshold
        self.dropout_rate = dropout_rate
        logger.info(f"初始化思维正则化伴侣: Threshold={overfitting_threshold}, DropoutRate={dropout_rate}")

    def _calculate_specificity_score(self, text: str) -> float:
        """
        [辅助函数] 计算文本的特异性/复杂度得分
        
        模拟检测过度解释倾向。使用简单的启发式方法：
        检查文本长度、因果连接词密度等。
        
        Args:
            text (str): 输入的推理文本
            
        Returns:
            float: 特异性得分 (0.0-1.0)
        """
        if not text:
            return 0.0
            
        # 启发式规则：文本越长，使用越多解释性连接词，得分越高
        words = re.findall(r'\w+', text)
        word_count = len(words)
        
        # 惩罚过长且充满细节的描述（模拟过度拟合噪声）
        # 假设超过50个词且包含大量"因为"、"所以"等逻辑词为高风险
        connector_words = ['因为', '所以', '导致', '由于', 'result', 'because', 'therefore']
        connector_count = sum(1 for w in words if w.lower() in connector_words)
        
        # 简单的归一化评分逻辑
        length_score = min(word_count / 100.0, 1.0)
        density_score = min(connector_count / 5.0, 1.0)
        
        return (length_score * 0.5) + (density_score * 0.5)

    def detect_cognitive_overfitting(self, decision: ExpertDecision) -> RedTeamReport:
        """
        [核心函数 1] 检测专家决策中的认知过拟合迹象
        
        分析决策的逻辑链条和信心度，判断是否陷入了过度解释偶然事件的陷阱。
        
        Args:
            decision (ExpertDecision): 专家的决策输入
            
        Returns:
            RedTeamReport: 包含过拟合评分和风险警示的报告
        """
        logger.info(f"开始分析决策上下文: {decision.context[:30]}...")
        
        alerts = []
        score = 0.0
        
        # 1. 检查逻辑链条的特异性
        specificity = self._calculate_specificity_score(decision.reasoning_chain)
        if specificity > 0.7:
            alerts.append("检测到高特异性的推理链条，可能正在过度拟合噪声细节。")
            score += 40
            
        # 2. 检查信心度与假设数量的矛盾
        # 如果假设很少但信心极高，或者假设极多且逻辑极其复杂
        if len(decision.core_assumptions) <= 2 and decision.confidence > 0.9:
            alerts.append("在极少假设下表现出极端自信，可能忽略了潜在的黑天鹅事件。")
            score += 30
        elif len(decision.core_assumptions) > 5 and specificity > 0.8:
            alerts.append("依赖过多经验假设来支撑结论，模型复杂度过高（方差风险）。")
            score += 30
            
        # 3. 检查关键词（模拟模式匹配）
        if "历来如此" in decision.reasoning_chain or "绝对" in decision.reasoning_chain:
            alerts.append("发现绝对化表述，暗示思维僵化。")
            score += 20

        final_score = min(score, 100.0)
        state = (CognitiveState.OVERFITTING_SUSPECTED 
                 if final_score > (self.overfitting_threshold * 100) 
                 else CognitiveState.NORMAL)
        
        logger.info(f"分析完成: 状态={state}, 得分={final_score}")
        
        return RedTeamReport(
            status=state,
            overfitting_score=final_score,
            alerts=alerts
        )

    def apply_cognitive_dropout(self, decision: ExpertDecision) -> str:
        """
        [核心函数 2] 应用认知Dropout机制
        
        随机屏蔽用户的一部分核心经验假设，构建一个缺失信息的模拟场景，
        强迫大脑寻找新的特征路径，从而提升认知鲁棒性。
        
        Args:
            decision (ExpertDecision): 原始决策对象
            
        Returns:
            str: 经过Dropout处理后的新场景描述（对抗性提示）
        """
        logger.info("启动认知Dropout机制...")
        
        if not decision.core_assumptions:
            return "无法执行Dropout：缺乏核心假设数据。"

        # 随机选择要屏蔽的假设
        num_to_drop = max(1, int(len(decision.core_assumptions) * self.dropout_rate))
        assumptions_copy = decision.core_assumptions.copy()
        
        dropped = []
        for _ in range(num_to_drop):
            if assumptions_copy:
                idx = random.randrange(len(assumptions_copy))
                dropped.append(assumptions_copy.pop(idx))
        
        remaining_assumptions = assumptions_copy
        
        # 生成对抗性场景
        scenario = (
            f"[对抗性模拟推演]\n"
            f"原始背景: {decision.context}\n\n"
            f"假设突发事件：你引以为傲的以下经验假设突然失效：\n"
            f"- {', '.join(dropped)}\n\n"
            f"现在的限制条件是：你只能依赖以下剩余假设：\n"
            f"- {', '.join(remaining_assumptions) if remaining_assumptions else '无（必须从零开始）'}\n\n"
            f"请在此条件下重新构建推演路径。"
        )
        
        logger.debug(f"已屏蔽假设: {dropped}")
        return scenario

    def process_decision_pipeline(self, decision: ExpertDecision) -> Dict:
        """
        完整的处理流水线：检测 -> 如果高风险 -> 应用Dropout
        
        Args:
            decision (ExpertDecision): 输入决策
            
        Returns:
            Dict: 包含完整分析结果和建议的字典
        """
        try:
            report = self.detect_cognitive_overfitting(decision)
            
            result = {
                "input_context": decision.context,
                "diagnosis": report.alerts,
                "overfitting_score": report.overfitting_score,
                "status": report.status.value,
                "intervention": None
            }
            
            if report.status == CognitiveState.OVERFITTING_SUSPECTED:
                logger.warning("检测到认知过拟合，正在生成干预方案...")
                dropout_scenario = self.apply_cognitive_dropout(decision)
                result["intervention"] = dropout_scenario
                result["status"] = CognitiveState.REGULARIZED.value
            
            return result
            
        except Exception as e:
            logger.error(f"处理决策时发生错误: {str(e)}")
            raise RuntimeError("思维正则化处理管道崩溃") from e

# 使用示例
if __name__ == "__main__":
    # 模拟一个专家的过度自信决策
    expert_input = ExpertDecision(
        context="预测下一季度市场份额",
        core_assumptions=[
            "竞争对手A不会降价", 
            "原材料价格保持稳定", 
            "用户忠诚度维持在高点",
            "广告投放转化率恒定"
        ],
        reasoning_chain=(
            "根据过去5年的数据，每逢节假日销量必涨，因为用户习惯在此期间消费，"
            "且竞争对手A历来在Q4表现保守，绝对不会发起价格战。"
            "我们的模型极其复杂，考虑了30个变量，所以结果绝对准确。"
        ),
        confidence=0.98
    )

    # 初始化伴侣
    companion = CognitiveRegularizationCompanion(overfitting_threshold=0.6, dropout_rate=0.4)
    
    # 执行分析
    analysis_result = companion.process_decision_pipeline(expert_input)
    
    # 打印结果
    print(f"认知状态: {analysis_result['status']}")
    print(f"过拟合风险分: {analysis_result['overfitting_score']}")
    if analysis_result['intervention']:
        print("\n--- 认知Dropout干预 ---")
        print(analysis_result['intervention'])