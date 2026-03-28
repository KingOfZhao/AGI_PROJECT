"""
模块名称: auto_融合_意图坍缩_bu_97_p3_74_7367fa
描述: 融合‘意图坍缩’、‘认知负载调节’与‘人格演变数仓’。
      本模块实现了一个自适应的人机交互接口，根据用户的历史偏好（人格数仓）和
      当前实时状态（认知负载），动态调整意图识别的概率分布（意图坍缩）。
      旨在实现从模糊意念到可执行代码/指令的“同频共振”。
"""

import logging
import random
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 常量与枚举定义 ---

class IntentType(Enum):
    """意图类型枚举"""
    CODE_GENERATION = "code_gen"
    DATA_QUERY = "data_query"
    SYSTEM_CONFIG = "sys_config"
    GENERAL_CHAT = "general_chat"
    FUZZY_EXPLORATION = "fuzzy_exploration"

class CognitiveState(Enum):
    """认知状态枚举，基于 td_97_Q6_3_9182 模块"""
    FOCUSED = "focused"       # 低负载，意图明确
    NORMAL = "normal"         # 常态
    OVERLOADED = "overloaded" # 高负载，思维模糊
    FATIGUED = "fatigued"     # 疲劳

# --- 数据结构 ---

@dataclass
class UserProfile:
    """
    用户画像数据结构 (ho_97_O3_1200)
    存储历史决策偏好，用于调整意图坍缩的先验概率。
    """
    user_id: str
    decision_history: Dict[str, int] = field(default_factory=dict)
    preference_vector: Dict[str, float] = field(default_factory=dict)
    
    def update_preference(self, intent: str, success: bool):
        """更新用户偏好向量"""
        weight = 1.0 if success else -0.5
        current = self.preference_vector.get(intent, 0.5)
        # 简单的指数移动平均模拟学习过程
        self.preference_vector[intent] = min(max(current + (weight * 0.1), 0.0), 1.0)

@dataclass
class IntentCandidate:
    """意图候选项"""
    intent_type: IntentType
    description: str
    base_prob: float
    adjusted_prob: float = 0.0
    action_code: str = "" # 模拟的可执行代码或指令

# --- 核心类 ---

class IntentCollapseEngine:
    """
    核心引擎：负责融合多维数据，执行意图坍缩。
    """

    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
        self.cognitive_load = 0.0  # 0.0 (低) -> 1.0 (高)

    def _adjust_for_cognitive_load(self, candidates: List[IntentCandidate]) -> None:
        """
        核心函数1: 认知负载调节
        基于 td_97_Q6_3_9182 逻辑。当负载高时，抑制复杂意图，提升简单/结构化意图的权重。
        """
        for candidate in candidates:
            # 如果是高负载，且意图是复杂的代码生成，降低概率
            if self.cognitive_load > 0.7:
                if candidate.intent_type == IntentType.CODE_GENERATION:
                    candidate.adjusted_prob *= (1.0 - self.cognitive_load * 0.5)
                elif candidate.intent_type == IntentType.FUZZY_EXPLORATION:
                    # 思维模糊时，增强探索性建议的权重
                    candidate.adjusted_prob *= (1.0 + self.cognitive_load * 0.3)
            
            # 边界检查
            candidate.adjusted_prob = max(0.0, min(1.0, candidate.adjusted_prob))
        
        logger.info(f"Adjusted candidates based on cognitive load: {self.cognitive_load}")

    def _collapse_wave_function(self, raw_input: str, candidates: List[IntentCandidate]) -> IntentCandidate:
        """
        核心函数2: 意图坍缩
        根据调整后的概率分布，将模糊的输入"坍缩"为一个确定的意图。
        模拟量子测量的随机性，但受限于概率幅。
        """
        total_prob = sum(c.adjusted_prob for c in candidates)
        if total_prob <= 0:
            raise ValueError("Total probability is zero, cannot collapse.")
        
        # 归一化
        rand_val = random.random() * total_prob
        cumulative = 0.0
        
        selected_candidate = candidates[0] # fallback
        
        for candidate in candidates:
            cumulative += candidate.adjusted_prob
            if rand_val <= cumulative:
                selected_candidate = candidate
                break
        
        logger.info(f"Intent collapsed to: {selected_candidate.intent_type.value}")
        return selected_candidate

    def analyze_and_execute(self, user_input: str, current_cognitive_load: float) -> Dict[str, Any]:
        """
        主流程：融合处理
        """
        self.cognitive_load = current_cognitive_load
        
        # 1. 生成初始意图波函数 (模拟NLP解析)
        initial_candidates = self._generate_hypotheses(user_input)
        
        # 2. 注入历史偏好
        self._apply_history_bias(initial_candidates)
        
        # 3. 认知负载调节
        self._adjust_for_cognitive_load(initial_candidates)
        
        # 4. 执行坍缩
        final_intent = self._collapse_wave_function(user_input, initial_candidates)
        
        # 5. 生成响应 (模拟代码结晶)
        result = self._crystallize_code(final_intent, user_input)
        
        # 更新用户历史
        self.user_profile.update_preference(final_intent.intent_type.value, True)
        
        return result

    # --- 辅助函数 ---

    def _generate_hypotheses(self, text: str) -> List[IntentCandidate]:
        """
        辅助函数: 根据输入文本生成初始意图假设列表。
        这里使用简单的关键词匹配模拟复杂的NLP过程。
        """
        candidates = []
        # 简单的规则模拟
        if "代码" in text or "函数" in text:
            candidates.append(IntentCandidate(IntentType.CODE_GENERATION, "生成Python代码", 0.6))
        if "查询" in text or "多少" in text:
            candidates.append(IntentCandidate(IntentType.DATA_QUERY, "查询数据库", 0.5))
        if "配置" in text:
            candidates.append(IntentCandidate(IntentType.SYSTEM_CONFIG, "修改系统设置", 0.4))
        
        # 默认总是保留一个模糊探索选项，以防万一
        candidates.append(IntentCandidate(IntentType.FUZZY_EXPLORATION, "探索性建议", 0.1))
        
        # 初始化 adjusted_prob
        for c in candidates:
            c.adjusted_prob = c.base_prob
            
        return candidates

    def _apply_history_bias(self, candidates: List[IntentCandidate]) -> None:
        """应用用户历史偏好偏置"""
        for c in candidates:
            bias = self.user_profile.preference_vector.get(c.intent_type.value, 1.0)
            c.adjusted_prob = c.base_prob * bias

    def _crystallize_code(self, intent: IntentCandidate, context: str) -> Dict[str, Any]:
        """
        将意图结晶为结构化输出。
        如果用户认知负载高，输出结构化的选项列表；
        如果负载低，直接输出执行逻辑。
        """
        response = {
            "status": "success",
            "intent": intent.intent_type.value,
            "action_taken": None,
            "message": ""
        }
        
        if self.cognitive_load > 0.8:
            # 高负载：提供结构化选项，不直接执行复杂操作
            response["action_taken"] = "STRUCTURED_OPTIONS"
            response["message"] = f"检测到您思维模糊，为您推荐结构化选项：{intent.description}"
            response["options"] = ["确认执行", "推迟操作", "修改参数"]
        else:
            # 低/中负载：直接执行
            response["action_taken"] = "DIRECT_EXECUTION"
            response["message"] = f"已将意念结晶为代码逻辑：{intent.description}"
            # 模拟生成的代码片段
            response["generated_code"] = f"def run_{intent.intent_type.value}(): print('Executing {context}')"
            
        return response

# --- 使用示例 ---
if __name__ == "__main__":
    # 初始化用户画像 (模拟从 ho_97_O3_1200 数仓加载)
    user = UserProfile(user_id="user_8848")
    user.preference_vector = {
        "code_gen": 0.8, # 用户非常喜欢生成代码
        "data_query": 0.2
    }

    # 初始化引擎
    engine = IntentCollapseEngine(user_profile=user)

    # 模拟场景 1: 用户思维清晰，意图明确
    print("--- 场景 1: 低认知负载 ---")
    result_clear = engine.analyze_and_execute("帮我写一个排序代码", current_cognitive_load=0.1)
    print(json.dumps(result_clear, indent=2, ensure_ascii=False))

    # 模拟场景 2: 用户思维模糊，高认知负载
    print("\n--- 场景 2: 高认知负载 ---")
    result_fuzzy = engine.analyze_and_execute("帮我... 那个... 搞一下数据", current_cognitive_load=0.9)
    print(json.dumps(result_fuzzy, indent=2, ensure_ascii=False))