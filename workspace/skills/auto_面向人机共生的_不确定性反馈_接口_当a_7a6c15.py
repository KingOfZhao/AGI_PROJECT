"""
Module: auto_面向人机共生的_不确定性反馈_接口_当a_7a6c15
Description: 面向人机共生的'不确定性反馈'接口。当AI系统面临认知僵局（即多个候选解释的权重相近，
             难以决策）时，计算各分支的'信息熵减潜力'，生成面向人类的'最小分辨问题'。
             旨在以最小的认知成本获取最关键的信息，实现人机智能共生。
Author: AGI System Core
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """反馈问题的类型枚举"""
    BINARY = "BINARY_CHOICE"          # 二选一 (是/否)
    MULTIPLE_CHOICE = "MULTI_CHOICE"  # 多选一
    SLIDER = "SLIDER"                 # 连续值输入

@dataclass
class CandidateExplanation:
    """候选解释的数据结构"""
    id: str
    description: str
    probability: float
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证：确保概率在有效范围内"""
        if not 0.0 <= self.probability <= 1.0:
            logger.error(f"Invalid probability value for {self.id}: {self.probability}")
            raise ValueError(f"Probability must be between 0.0 and 1.0, got {self.probability}")

@dataclass
class ClarificationQuestion:
    """生成的澄清问题结构"""
    question_id: str
    question_text: str
    feedback_type: FeedbackType
    options: List[str]
    expected_entropy_reduction: float
    target_candidates: List[str]  # 涉及的候选ID

class CognitiveDeadlockError(Exception):
    """自定义异常：认知僵局处理失败"""
    pass

def _calculate_entropy(probabilities: List[float]) -> float:
    """
    [辅助函数] 计算香农信息熵。
    
    Args:
        probabilities (List[float]): 归一化的概率分布列表。
        
    Returns:
        float: 系统当前的信息熵。
        
    Raises:
        ValueError: 如果概率和不为1（允许微小浮点误差）。
    """
    if not math.isclose(sum(probabilities), 1.0, abs_tol=1e-5):
        # 尝试归一化
        total = sum(probabilities)
        if total == 0: return 0.0
        probabilities = [p / total for p in probabilities]
        
    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def analyze_cognitive_state(candidates: List[CandidateExplanation]) -> Tuple[bool, float]:
    """
    [核心函数 1] 分析当前状态是否处于认知僵局。
    
    通过计算熵值和概率分布方差，判断系统是否需要人类介入。
    
    Args:
        candidates (List[CandidateExplanation]): 候选解释列表。
        
    Returns:
        Tuple[bool, float]: 
            - is_deadlock (bool): 是否处于僵局。
            - current_entropy (float): 当前系统熵值。
            
    Example:
        >>> cands = [CandidateExplanation("a", "desc", 0.5), CandidateExplanation("b", "desc2", 0.5)]
        >>> deadlock, entropy = analyze_cognitive_state(cands)
    """
    if not candidates:
        return False, 0.0

    probs = [c.probability for c in candidates]
    current_entropy = _calculate_entropy(probs)
    
    # 检查是否存在绝对优势候选（熵值极低）
    max_prob = max(probs)
    confidence_threshold = 0.85 # 阈值：如果最高概率超过85%，不视为僵局
    
    is_deadlock = False
    if max_prob < confidence_threshold and len(candidates) > 1:
        # 如果熵值较高，或者前两名差距过小
        sorted_probs = sorted(probs, reverse=True)
        if len(sorted_probs) > 1 and (sorted_probs[0] - sorted_probs[1]) < 0.2:
            is_deadlock = True
            logger.info(f"Cognitive deadlock detected. Entropy: {current_entropy:.4f}")
    
    return is_deadlock, current_entropy

def generate_minimal_feedback_request(
    candidates: List[CandidateExplanation],
    context: Optional[Dict[str, Any]] = None
) -> Optional[ClarificationQuestion]:
    """
    [核心函数 2] 生成最小分辨问题（MPQ）。
    
    算法逻辑：
    1. 识别概率最高的前N个候选。
    2. 分析它们属性（Attributes）中的差异点。
    3. 计算如果区分这些差异，能带来的预期熵减。
    4. 封装成对人类最友好的二选一或多选一问题。
    
    Args:
        candidates (List[CandidateExplanation]): 候选解释列表。
        context (Optional[Dict]): 上下文信息，包含用户偏好等。
        
    Returns:
        Optional[ClarificationQuestion]: 生成的澄清问题对象，如果无僵局则返回None。
        
    Data Format:
        Input candidates attributes example:
        [
            {'id': '1', 'prob': 0.45, 'attrs': {'color': 'red', 'shape': 'circle'}},
            {'id': '2', 'prob': 0.40, 'attrs': {'color': 'blue', 'shape': 'circle'}}
        ]
        Output Question: "Is the object more likely Red or Blue?"
    """
    if not candidates:
        return None

    is_deadlock, current_entropy = analyze_cognitive_state(candidates)
    
    if not is_deadlock:
        logger.info("System is confident enough. No feedback required.")
        return None

    # 简化逻辑：选取概率最高的两个候选进行对比
    # 实际AGI场景中，这里应包含复杂的语义分析和差异提取
    sorted_candidates = sorted(candidates, key=lambda x: x.probability, reverse=True)
    
    if len(sorted_candidates) < 2:
        return None
        
    cand_a, cand_b = sorted_candidates[0], sorted_candidates[1]
    
    # 寻找区分性属性（模拟）
    # 假设我们在属性中寻找不同的Key
    diff_key = None
    val_a, val_b = None, None
    
    # 寻找第一个值不同的属性
    common_keys = set(cand_a.attributes.keys()) & set(cand_b.attributes.keys())
    for key in common_keys:
        if cand_a.attributes[key] != cand_b.attributes[key]:
            diff_key = key
            val_a = cand_a.attributes[key]
            val_b = cand_b.attributes[key]
            break
    
    question_text = ""
    options = []

    if diff_key:
        # 生成二选一问题
        question_text = (
            f"为了更准确地理解，请确认：关于'{diff_key}'，"
            f"实际情况更接近于 '{val_a}' 还是 '{val_b}'？"
        )
        options = [f"选项A: {val_a} (支持: {cand_a.description})", 
                   f"选项B: {val_b} (支持: {cand_b.description})"]
        
        # 估算熵减潜力（简化：假设区分后胜者通吃）
        # 真实计算需要后验概率估计
        potential_reduction = current_entropy * 0.8 # 假设能消除80%的不确定性
    else:
        # 如果属性完全一致，需要更高级的抽象提问
        question_text = f"在这两种可能之间，您直觉上倾向于哪一个？\n1. {cand_a.description}\n2. {cand_b.description}"
        options = ["倾向于解释 1", "倾向于解释 2"]
        potential_reduction = current_entropy * 0.5

    logger.info(f"Generated MPQ. Expected Entropy Reduction: {potential_reduction:.4f} bits")
    
    return ClarificationQuestion(
        question_id=f"q_{cand_a.id}_{cand_b.id}",
        question_text=question_text,
        feedback_type=FeedbackType.BINARY,
        options=options,
        expected_entropy_reduction=potential_reduction,
        target_candidates=[cand_a.id, cand_b.id]
    )

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 构造模拟数据：AI面临两个权重相近的解释
        # 解释A：用户想要订票 (权重0.48)
        # 解释B：用户想要退票 (权重0.46)
        candidate_A = CandidateExplanation(
            id="intent_book",
            description="Book a flight ticket",
            probability=0.48,
            attributes={"action": "booking", "object": "ticket"}
        )
        
        candidate_B = CandidateExplanation(
            id="intent_refund",
            description="Refund an existing ticket",
            probability=0.46,
            attributes={"action": "refund", "object": "ticket"}
        )
        
        # 噪音数据
        candidate_C = CandidateExplanation(
            id="intent_info",
            description="Just checking info",
            probability=0.06,
            attributes={"action": "query", "object": "schedule"}
        )

        candidates_list = [candidate_A, candidate_B, candidate_C]

        print("--- 分析认知状态 ---")
        deadlock, entropy = analyze_cognitive_state(candidates_list)
        print(f"Is Deadlock: {deadlock}, System Entropy: {entropy:.4f} bits")

        print("\n--- 生成最小分辨问题 ---")
        question = generate_minimal_feedback_request(candidates_list)
        
        if question:
            print(f"Question ID: {question.question_id}")
            print(f"Type: {question.feedback_type.value}")
            print(f"Q: {question.question_text}")
            for opt in question.options:
                print(f"- {opt}")
            print(f"Expected Information Gain: {question.expected_entropy_reduction:.4f} bits")
        else:
            print("No question generated (System confident).")

    except ValueError as ve:
        logger.error(f"Data validation error: {ve}")
    except CognitiveDeadlockError as cde:
        logger.critical(f"Failed to resolve deadlock: {cde}")
    except Exception as e:
        logger.exception("Unexpected system error")