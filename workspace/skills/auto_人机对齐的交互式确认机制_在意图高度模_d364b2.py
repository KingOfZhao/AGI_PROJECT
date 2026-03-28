"""
高级Python工程师为AGI系统生成的SKILL代码模块。

名称: auto_人机对齐的交互式确认机制_在意图高度模_d364b2
描述: 实现一个用于处理高度模糊意图的交互式确认机制。
      该模块能够计算输入意图的模糊度分数，并据此生成
      结构化的问卷（二选一或填空式），以引导用户进行
      低成本但高价值的意图细化。
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AmbiguityDimension(Enum):
    """定义意图模糊性的维度"""
    SCOPE = "scope"           # 影响范围（文件、模块、系统）
    TARGET = "target"         # 目标对象（函数名、变量名）
    METRIC = "metric"         # 优化指标（速度、内存、可读性）
    STRATEGY = "strategy"     # 执行策略（重构、重写、微调）

@dataclass
class AmbiguityFactor:
    """模糊性因子的数据结构"""
    dimension: AmbiguityDimension
    score: float              # 0.0 (明确) 到 1.0 (极度模糊)
    context: str              # 导致模糊的上下文片段

@dataclass
class ClarificationOption:
    """澄清问题的选项"""
    key: str
    display_text: str
    value_mapping: str

@dataclass
class ClarificationQuestion:
    """结构化问卷中的单个问题"""
    dimension: AmbiguityDimension
    question_text: str
    options: List[ClarificationOption]
    input_type: str  # 'choice' or 'fill_blank'

@dataclass
class IntentAnalysisReport:
    """意图分析报告"""
    original_intent: str
    ambiguity_score: float
    factors: List[AmbiguityFactor] = field(default_factory=list)
    questions: List[ClarificationQuestion] = field(default_factory=list)

def _calculate_keyword_ambiguity(text: str, keywords: Dict[str, float]) -> Tuple[float, str]:
    """
    辅助函数：基于关键词权重计算模糊度。
    
    Args:
        text (str): 输入文本
        keywords (Dict[str, float]): 关键词及其默认模糊权重
        
    Returns:
        Tuple[float, str]: 计算出的模糊度分数和匹配到的上下文
    """
    text_lower = text.lower()
    max_score = 0.0
    matched_context = "generic"
    
    for keyword, score in keywords.items():
        if keyword in text_lower:
            if score > max_score:
                max_score = score
                matched_context = keyword
    
    # 简单的启发式规则：句子越短，模糊度通常越高（缺乏上下文）
    word_count = len(re.findall(r'\w+', text))
    length_penalty = max(0, 1.0 - (word_count / 15.0)) # 15个词以上视为无长度惩罚
    
    final_score = min(1.0, max_score + length_penalty * 0.2)
    return final_score, matched_context

def calculate_ambiguity_score(user_intent: str) -> IntentAnalysisReport:
    """
    核心函数1: 计算意图的模糊度分数并生成分析报告。
    
    该函数通过多个维度（范围、指标、策略等）分析用户输入，
    识别出模糊点。
    
    Args:
        user_intent (str): 用户的原始意图字符串。
        
    Returns:
        IntentAnalysisReport: 包含模糊度分数和详细因子的报告。
        
    Raises:
        ValueError: 如果输入为空或非字符串。
    """
    if not isinstance(user_intent, str) or not user_intent.strip():
        logger.error("输入意图无效: 必须是非空字符串")
        raise ValueError("Input intent must be a non-empty string.")
    
    logger.info(f"开始分析意图: {user_intent}")
    
    factors = []
    
    # 1. 分析 METRIC 维度 (如 "优化" - 意味着什么指标？)
    metric_keywords = {
        "优化": 0.8, "改进": 0.7, "快一点": 0.3, 
        "省内存": 0.2, "好看": 0.2
    }
    score, ctx = _calculate_keyword_ambiguity(user_intent, metric_keywords)
    if score > 0.3:
        factors.append(AmbiguityFactor(
            dimension=AmbiguityDimension.METRIC,
            score=score,
            context=f"检测到模糊动词: '{ctx}'"
        ))

    # 2. 分析 TARGET 维度 (如 "这个函数" - 指向不明)
    if "这个" in user_intent or "那个" in user_intent or "它" in user_intent:
        factors.append(AmbiguityFactor(
            dimension=AmbiguityDimension.TARGET,
            score=0.9,
            context="包含指示代词，缺乏具体上下文"
        ))
        
    # 3. 分析 SCOPE 维度
    if len(user_intent.split()) < 3 and "整个" not in user_intent:
         factors.append(AmbiguityFactor(
            dimension=AmbiguityDimension.SCOPE,
            score=0.6,
            context="描述过于简略，范围不清"
        ))

    # 计算总体分数 (取各维度最大值或加权平均，这里取最大值代表风险)
    total_score = max([f.score for f in factors]) if factors else 0.0
    
    report = IntentAnalysisReport(
        original_intent=user_intent,
        ambiguity_score=total_score,
        factors=factors
    )
    
    logger.info(f"分析完成。总体模糊度: {total_score:.2f}")
    return report

def generate_clarification_questions(report: IntentAnalysisReport) -> List[ClarificationQuestion]:
    """
    核心函数2: 根据模糊度分析报告生成交互式问卷。
    
    仅当模糊度超过阈值时生成问题，旨在用最少的交互获取最大信息量。
    
    Args:
        report (IntentAnalysisReport): calculate_ambiguity_score 的输出。
        
    Returns:
        List[ClarificationQuestion]: 结构化的问题列表。
    """
    questions = []
    threshold = 0.5  # 触发交互的阈值
    
    if report.ambiguity_score < threshold:
        logger.info("意图足够清晰，无需交互确认。")
        return questions

    logger.info("意图模糊，开始生成澄清问题...")
    
    for factor in report.factors:
        if factor.score < 0.4:
            continue
            
        if factor.dimension == AmbiguityDimension.METRIC:
            # 生成二选一或多选问题
            q = ClarificationQuestion(
                dimension=factor.dimension,
                question_text="您提到的'优化'主要侧重于以下哪个目标？",
                options=[
                    ClarificationOption("A", "执行速度 (Performance)", "optimize_for='speed'"),
                    ClarificationOption("B", "代码可读性 (Readability)", "optimize_for='readability'"),
                    ClarificationOption("C", "内存占用 (Memory)", "optimize_for='memory'")
                ],
                input_type="choice"
            )
            questions.append(q)
            
        elif factor.dimension == AmbiguityDimension.TARGET:
            # 生成填空式问题
            q = ClarificationQuestion(
                dimension=factor.dimension,
                question_text="请明确需要操作的具体对象名称：",
                options=[
                    ClarificationOption("INPUT", "输入目标函数/模块名", "target_name='{user_input}'")
                ],
                input_type="fill_blank"
            )
            questions.append(q)
            
    return questions

def interactive_alignment_session(user_intent: str) -> Dict[str, Union[str, float, List[str]]]:
    """
    辅助函数: 模拟完整的交互式对齐会话流程。
    
    整合分析、生成问卷，并模拟用户响应以返回最终结构化意图。
    实际生产中，此函数会调用UI接口等待用户输入。
    
    Args:
        user_intent (str): 原始用户意图
        
    Returns:
        Dict: 包含原始意图、最终确认的参数列表和修正后的置信度。
    """
    try:
        # 1. 分析
        report = calculate_ambiguity_score(user_intent)
        
        result_data = {
            "original_intent": user_intent,
            "clarified_params": {},
            "final_confidence": 1.0 - report.ambiguity_score
        }
        
        # 2. 生成问卷
        questions = generate_clarification_questions(report)
        
        if not questions:
            return result_data
            
        # 3. 模拟用户交互 (实际AGI系统中这里会阻塞等待API响应)
        logger.info(f"系统生成 {len(questions)} 个问题需要确认。")
        
        simulated_responses = {}
        for q in questions:
            print(f"\n[SYSTEM QUESTION]: {q.question_text}")
            for idx, opt in enumerate(q.options):
                print(f"  [{idx + 1}] {opt.display_text}")
            
            # 模拟用户选择（这里自动选择第一个选项仅用于演示代码逻辑）
            # 在真实场景中，这里会获取 input()
            simulated_choice = q.options[0].value_mapping
            logger.debug(f"模拟用户选择: {simulated_choice}")
            simulated_responses[q.dimension.value] = simulated_choice
            
        result_data["clarified_params"] = simulated_responses
        result_data["final_confidence"] = 1.0  # 确认后置信度重置为高
        
        return result_data
        
    except Exception as e:
        logger.error(f"交互对齐过程中发生错误: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    # 使用示例
    user_input = "帮我优化一下这个函数"
    
    print(f"--- 处理用户输入: '{user_input}' ---")
    alignment_result = interactive_alignment_session(user_input)
    
    print("\n--- 最终对齐结果 ---")
    print(f"原始意图: {alignment_result['original_intent']}")
    print(f"提取参数: {alignment_result['clarified_params']}")
    print(f"置信度: {alignment_result['final_confidence']}")