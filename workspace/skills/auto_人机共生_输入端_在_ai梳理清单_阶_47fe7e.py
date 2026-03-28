"""
Module: auto_人机共生_输入端_在_ai梳理清单_阶_47fe7e
Description: 【人机共生-输入端】在'AI梳理清单'阶段，如何量化'清单的可执行颗粒度'？
             本模块提供'指令歧义性检测器'，用于预测人类执行AI生成指令时的理解偏差概率。
             旨在辅助AGI系统将复杂认知节点拆解为原子化指令，并评估节点描述语言的形式化约束程度。

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
import re
import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AmbiguityLevel(Enum):
    """指令清晰度等级枚举"""
    CLEAR = "clear"                 # 清晰，可直接执行
    POTENTIAL_RISK = "potential"    # 潜在风险，建议复核
    HIGH_AMBIGUITY = "high"         # 高歧义性，必须重构


@dataclass
class InstructionMetrics:
    """指令度量数据结构，存储各项量化指标"""
    word_count: int
    action_verb_ratio: float       # 动词密度
    abstract_noun_count: int       # 抽象名词数量
    context_dependency_score: float # 上下文依赖分数 (0-1)
    vagueness_score: float         # 模糊性分数 (0-1)


class InstructionValidationError(Exception):
    """自定义异常：指令数据验证错误"""
    pass


class AmbiguityDetector:
    """
    核心类：指令歧义性检测器
    
    功能：
    1. 解析自然语言指令。
    2. 基于语言学特征和启发式规则量化指令的'可执行颗粒度'。
    3. 预测人类的'理解偏差概率'。
    """

    # 定义模糊词汇集合 (实际生产中应使用NLP模型或更大的语料库)
    VAGUE_WORDS = {
        "一些", "很多", "稍微", "大概", "可能", "尽快", "优化", 
        "处理", "相关", "适当", "近期", "某些", "something", "some", "soon"
    }
    
    # 定义原子化动词白名单 (示例)
    ATOMIC_VERBS = {
        "点击", "输入", "复制", "粘贴", "移动", "删除", "创建", 
        "发送", "确认", "选择", "click", "type", "move", "delete"
    }

    def __init__(self, sensitivity: float = 0.7):
        """
        初始化检测器
        
        Args:
            sensitivity (float): 敏感度阈值 (0.0-1.0)，越高对歧义越严格
        """
        if not 0.0 <= sensitivity <= 1.0:
            logger.error("Sensitivity must be between 0.0 and 1.0")
            raise ValueError("Invalid sensitivity range")
        
        self.sensitivity = sensitivity
        logger.info(f"AmbiguityDetector initialized with sensitivity: {sensitivity}")

    def _preprocess_text(self, text: str) -> str:
        """
        辅助函数：文本预处理
        
        Args:
            text (str): 原始文本
            
        Returns:
            str: 清洗后的文本
        """
        # 移除多余空格和换行
        text = re.sub(r'\s+', ' ', text).strip()
        # 这里可以加入分词逻辑，简化起见使用基础正则
        return text

    def _calculate_metrics(self, instruction: str) -> InstructionMetrics:
        """
        核心函数1：计算指令的量化指标
        
        Args:
            instruction (str): 待分析的指令文本
            
        Returns:
            InstructionMetrics: 包含各项指标的度量对象
        """
        logger.debug(f"Calculating metrics for: {instruction[:20]}...")
        
        words = re.findall(r'\w+|[^\w\s]', instruction)
        word_count = len(words)
        
        if word_count == 0:
            return InstructionMetrics(0, 0.0, 0, 0.0, 1.0) # 空指令视为极度模糊

        # 1. 计算原子化动词比例
        verb_count = sum(1 for w in words if w.lower() in self.ATOMIC_VERBS)
        action_verb_ratio = verb_count / word_count

        # 2. 计算模糊词分数
        vague_count = sum(1 for w in words if w.lower() in self.VAGUE_WORDS)
        vagueness_score = vague_count / word_count

        # 3. 抽象名词检测 (简化版：检测没有具体指向的词汇)
        # 假设以"性"、"化"结尾的词或"情况"、"问题"为抽象词
        abstract_patterns = [r'性$', r'化$', r'度$', r'情况', r'问题', r'tion', r'ment']
        abstract_noun_count = 0
        for w in words:
            if any(re.search(p, w) for p in abstract_patterns):
                abstract_noun_count += 1

        # 4. 上下文依赖度 (简化版：检测代词"它"、"这个"、"that"、"it")
        context_words = {"它", "这个", "那个", "其", "it", "this", "that", "they"}
        context_count = sum(1 for w in words if w.lower() in context_words)
        context_dependency_score = context_count / max(word_count, 1)

        return InstructionMetrics(
            word_count=word_count,
            action_verb_ratio=action_verb_ratio,
            abstract_noun_count=abstract_noun_count,
            context_dependency_score=context_dependency_score,
            vagueness_score=vagueness_score
        )

    def predict_deviation_probability(self, metrics: InstructionMetrics) -> float:
        """
        核心函数2：预测理解偏差概率
        
        基于加权公式计算：
        P(deviation) = w1*(1-verb_ratio) + w2*vagueness + w3*context_dep + w4*log(word_count)
        
        Args:
            metrics (InstructionMetrics): 指令度量指标
            
        Returns:
            float: 偏差概率 (0.0-1.0)
        """
        # 权重超参数
        W_VERB = 0.4      # 动词越少，偏差越大
        W_VAGUE = 0.3     # 模糊词越多，偏差越大
        W_CTX = 0.2       # 上下文依赖越高，偏差越大
        W_ABSTRACT = 0.1  # 抽象名词影响

        # 归一化词汇长度影响 (太长或太短都容易产生歧义，这里主要惩罚过短)
        length_factor = 0.0
        if metrics.word_count < 5:
            length_factor = 0.2 # 信息量不足
        
        # 计算基础风险分
        score = (
            W_VERB * (1 - metrics.action_verb_ratio) +
            W_VAGUE * metrics.vagueness_score +
            W_CTX * metrics.context_dependency_score +
            W_ABSTRACT * (metrics.abstract_noun_count / max(metrics.word_count, 1)) +
            length_factor
        )
        
        # 应用敏感度调节
        adjusted_score = score * (1 + (self.sensitivity - 0.5))
        
        # 截断到 [0, 1]
        final_prob = max(0.0, min(1.0, adjusted_score))
        logger.debug(f"Calculated deviation probability: {final_prob:.4f}")
        return final_prob

    def analyze_instruction(self, instruction_text: str) -> Dict[str, Any]:
        """
        分析单条指令并生成完整报告
        
        Args:
            instruction_text (str): 输入指令
            
        Returns:
            Dict: 包含概率、等级和建议的报告
        """
        if not instruction_text or not isinstance(instruction_text, str):
            logger.error("Invalid input: empty or non-string instruction")
            raise InstructionValidationError("Input must be a non-empty string")

        clean_text = self._preprocess_text(instruction_text)
        metrics = self._calculate_metrics(clean_text)
        probability = self.predict_deviation_probability(metrics)

        # 判定等级
        if probability < 0.3:
            level = AmbiguityLevel.CLEAR
        elif probability < 0.7:
            level = AmbiguityLevel.POTENTIAL_RISK
        else:
            level = AmbiguityLevel.HIGH_AMBIGUITY

        # 生成建议
        suggestion = "No action needed."
        if level != AmbiguityLevel.CLEAR:
            if metrics.vagueness_score > 0.1:
                suggestion = "建议替换模糊词汇（如'尽快'、'一些'）为具体数值或对象。"
            elif metrics.action_verb_ratio < 0.1:
                suggestion = "建议使用明确的动作动词开头（如'复制'、'点击'）。"
            elif metrics.context_dependency_score > 0.2:
                suggestion = "建议消除代词指代，明确具体的操作对象。"

        return {
            "instruction": instruction_text,
            "deviation_probability": round(probability, 4),
            "ambiguity_level": level.value,
            "metrics": metrics.__dict__,
            "suggestion": suggestion
        }


# 辅助函数：批量处理
def batch_process_instructions(detector: AmbiguityDetector, instructions: List[str]) -> List[Dict]:
    """
    辅助函数：批量处理指令列表
    
    Args:
        detector (AmbiguityDetector): 检测器实例
        instructions (List[str]): 指令列表
        
    Returns:
        List[Dict]: 分析报告列表
    """
    results = []
    if not instructions:
        logger.warning("Empty instruction list received for batch processing")
        return results

    logger.info(f"Starting batch processing for {len(instructions)} instructions...")
    
    for idx, inst in enumerate(instructions):
        try:
            report = detector.analyze_instruction(inst)
            report['id'] = idx
            results.append(report)
        except InstructionValidationError as e:
            logger.warning(f"Skipping invalid instruction at index {idx}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing index {idx}: {e}", exc_info=True)
            
    return results


def main():
    """
    使用示例与模块测试
    """
    # 1. 初始化检测器
    detector = AmbiguityDetector(sensitivity=0.8)

    # 2. 定义测试用例 (模拟AI生成的清单)
    test_instructions = [
        "点击屏幕右上角的'提交'按钮",  # 清晰
        "处理一下那个文件",          # 极度模糊，高歧义
        "尽快优化相关代码的性能",     # 抽象，缺乏具体指标
        "将变量X的值设置为100",       # 清晰
        "它需要被移动到那里"          # 高上下文依赖
    ]

    print("-" * 60)
    print(f"{'Instruction':<30} | {'Prob':<6} | {'Level':<10}")
    print("-" * 60)

    # 3. 批量处理
    reports = batch_process_instructions(detector, test_instructions)

    # 4. 输出结果
    for report in reports:
        inst_preview = (report['instruction'][:25] + '..') if len(report['instruction']) > 25 else report['instruction']
        print(f"{inst_preview:<30} | {report['deviation_probability']:<6} | {report['ambiguity_level']:<10}")
        if report['ambiguity_level'] != 'clear':
            print(f"  -> Suggestion: {report['suggestion']}")
    
    print("-" * 60)

if __name__ == "__main__":
    main()