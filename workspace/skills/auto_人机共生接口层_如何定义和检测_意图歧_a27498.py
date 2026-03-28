"""
模块名称: auto_人机共生接口层_如何定义和检测_意图歧_a27498
描述: 【人机共生接口层】如何定义和检测'意图歧义点'并自动生成'澄清性提问'？
      系统不应盲目猜测，而应在不确定性超过阈值时，生成精确的A/B选项供人类确认。
      这是'人机共生'的关键，旨在用最小的人类交互成本消除最大的语义鸿沟。
领域: hci/dialog_systems
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AmbiguityType(Enum):
    """意图歧义类型的枚举定义"""
    SEMANTIC = "semantic"       # 语义歧义（同一词多义）
    SCOPE = "scope"             # 范围歧义（指代不清）
    INTENT_CONFIDENCE = "intent" # 意图置信度低

@dataclass
class IntentCandidate:
    """表示一个可能的意图候选项"""
    intent_id: str
    description: str
    confidence: float
    action_schema: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证：确保置信度在0.0到1.0之间"""
        if not (0.0 <= self.confidence <= 1.0):
            logger.error(f"无效的置信度值: {self.confidence}")
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

@dataclass
class ClarificationRequest:
    """生成的澄清请求对象"""
    query_text: str
    options: List[Dict[str, str]] # List of {'id': 'A', 'text': '...'}
    ambiguity_type: AmbiguityType
    original_candidates: List[IntentCandidate]

class AmbiguityDetector:
    """
    核心类：负责检测意图歧义并生成澄清提问。
    
    输入格式:
        - user_input: str, 用户的原始输入文本
        - nlu_result: Dict, 包含 'candidates' (List[IntentCandidate]) 和 'context' (Dict)
    输出格式:
        - ClarificationRequest 或 None (如果无歧义)
    """
    
    # 系统配置常量
    CONFIDENCE_THRESHOLD_HIGH = 0.75  # 高于此值认为意图明确
    CONFIDENCE_DELTA_THRESHOLD = 0.15 # 前两名候选项的分差小于此值视为混淆

    def __init__(self, config: Optional[Dict] = None):
        """初始化检测器"""
        self.config = config or {}
        logger.info("AmbiguityDetector 初始化完成。阈值设定: High>=%.2f, Delta<=%.2f",
                    self.CONFIDENCE_THRESHOLD_HIGH, self.CONFIDENCE_DELTA_THRESHOLD)

    def _validate_nlu_input(self, nlu_data: Dict) -> List[IntentCandidate]:
        """辅助函数：验证NLU解析数据并提取候选项"""
        if not nlu_data or 'candidates' not in nlu_data:
            logger.warning("输入数据无效或缺少 'candidates' 键")
            return []
        
        raw_candidates = nlu_data.get('candidates', [])
        candidates = []
        
        for item in raw_candidates:
            try:
                # 假设输入可能是字典，转换为强类型Dataclass
                if isinstance(item, dict):
                    cand = IntentCandidate(**item)
                elif isinstance(item, IntentCandidate):
                    cand = item
                else:
                    continue
                candidates.append(cand)
            except TypeError as e:
                logger.error(f"候选项数据结构不匹配: {e}")
            except ValueError as e:
                logger.error(f"候选项数据验证失败: {e}")
        
        return candidates

    def detect_ambiguity(self, user_input: str, nlu_result: Dict) -> Optional[ClarificationRequest]:
        """
        核心函数1: 检测是否存在需要人工干预的意图歧义。
        
        逻辑:
        1. 验证输入数据
        2. 排序意图候选项
        3. 应用规则判断是否歧义:
           - 规则A: Top 1 置信度不够高
           - 规则B: Top 1 和 Top 2 非常接近，系统难以区分
        """
        candidates = self._validate_nlu_input(nlu_result)
        
        if not candidates:
            logger.info("未检测到有效意图候选项。")
            return None

        # 按置信度降序排序
        sorted_candidates = sorted(candidates, key=lambda x: x.confidence, reverse=True)
        top_candidate = sorted_candidates[0]
        
        is_ambiguous = False
        ambiguity_reason = ""
        
        # 规则 A: 最高置信度仍然太低
        if top_candidate.confidence < self.CONFIDENCE_THRESHOLD_HIGH:
            is_ambiguous = True
            ambiguity_reason = f"Top confidence {top_candidate.confidence} is below threshold."
            logger.debug(f"检测到歧义(低置信度): {ambiguity_reason}")
        
        # 规则 B: 前两名势均力敌 (Confusion Matrix)
        if len(sorted_candidates) > 1:
            second_candidate = sorted_candidates[1]
            delta = top_candidate.confidence - second_candidate.confidence
            if delta < self.CONFIDENCE_DELTA_THRESHOLD:
                is_ambiguous = True
                ambiguity_reason = f"Top 2 candidates are too close (Delta: {delta:.2f})."
                logger.debug(f"检测到歧义(候选项混淆): {ambiguity_reason}")

        if is_ambiguous:
            # 截取前2-3个候选项用于生成澄清问题
            top_candidates = sorted_candidates[:3]
            return self.generate_clarification(user_input, top_candidates)
        
        logger.info("意图明确，无需澄清。Intent: %s", top_candidate.intent_id)
        return None

    def generate_clarification(self, user_input: str, candidates: List[IntentCandidate]) -> ClarificationRequest:
        """
        核心函数2: 基于歧义点生成结构化的澄清性提问。
        
        目标: 生成 A/B 选项，最小化人类认知负担。
        """
        # 生成提问文本
        query_text = f"关于 '{user_input}'，我检测到几种可能的意图，请确认您希望执行的操作："
        
        # 生成选项
        options = []
        for idx, cand in enumerate(candidates):
            # 将索引映射为 A, B, C...
            option_key = chr(65 + idx) 
            options.append({
                'id': option_key,
                'text': cand.description,
                'intent_key': cand.intent_id
            })
        
        logger.info("生成澄清问题，包含 %d 个选项。", len(options))
        
        return ClarificationRequest(
            query_text=query_text,
            options=options,
            ambiguity_type=AmbiguityType.INTENT_CONFIDENCE,
            original_candidates=candidates
        )

# ================= 使用示例 =================
if __name__ == "__main__":
    # 模拟输入数据
    mock_user_input = "帮我定个苹果"
    
    # 模拟 NLU 引擎的输出 (包含多个高相关性的候选项)
    # '苹果' 可能指 '水果' 也可能指 '手机'
    mock_nlu_data = {
        "candidates": [
            {
                "intent_id": "buy_fruit",
                "description": "购买水果（如苹果、香蕉）",
                "confidence": 0.65
            },
            {
                "intent_id": "buy_electronics",
                "description": "购买苹果电子产品（如iPhone）",
                "confidence": 0.60
            },
            {
                "intent_id": "schedule_task",
                "description": "设定一个提醒",
                "confidence": 0.10
            }
        ],
        "context": {}
    }

    # 初始化检测器
    detector = AmbiguityDetector()

    print(f"--- 处理用户输入: '{mock_user_input}' ---")
    
    # 执行检测
    clarification = detector.detect_ambiguity(mock_user_input, mock_nlu_data)

    # 输出结果
    if clarification:
        print("\n[系统] 检测到意图歧义！触发人机共生接口...")
        print(f"[系统提问] {clarification.query_text}")
        for opt in clarification.options:
            print(f"  [{opt['id']}]: {opt['text']}")
    else:
        print("\n[系统] 意图明确，直接执行。")