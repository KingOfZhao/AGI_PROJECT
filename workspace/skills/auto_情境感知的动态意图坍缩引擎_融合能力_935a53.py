"""
情境感知的动态意图坍缩引擎

该模块实现了一个跨领域的意图解析系统，融合了硬性的业务逻辑（领域A）
与软性的社会交互规则（领域B），旨在通过上下文感知和历史行为分析，
将极度简略或模糊的用户指令转化为高置信度的、完整的结构化参数。

核心能力：
1. 习惯性填充：基于用户历史行为模式自动补全默认参数。
2. 环境状态感知：根据当前上下文（如地理位置、时间段）调整意图权重。
3. 模糊逻辑推理：处理非结构化、省略式的自然语言指令。
4. 置信度评估：为生成的参数提供可靠性评分，模拟人类直觉。

Author: AGI System Core
Version: 1.0.0
Date: 2023-10-27
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentCollapseEngine")


class DomainType(Enum):
    """领域类型枚举"""
    BUSINESS_LOGIC = "A"  # 领域A：死板的业务逻辑/JSON映射
    SOCIAL_PROTOCOL = "B"  # 领域B：人情世故/潜规则


class IntentConfidence(Enum):
    """意图置信度等级"""
    EXPLICIT = 1.0      # 明确指定
    HIGH = 0.85         # 高度确信（基于强习惯）
    MEDIUM = 0.6        # 中度确信（基于环境推断）
    LOW = 0.3           # 低度确信（猜测）
    INVALID = 0.0       # 无效


@dataclass
class UserProfile:
    """用户画像档案，存储历史行为习惯"""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    frequent_actions: List[str] = field(default_factory=list)
    default_contacts: Dict[str, str] = field(default_factory=dict)
    role: str = "guest"


@dataclass
class ContextState:
    """当前环境状态上下文"""
    timestamp: datetime = field(default_factory=datetime.now)
    location: Optional[str] = None
    device_type: str = "unknown"
    active_session_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollapsedIntent:
    """坍缩后的意图结果"""
    raw_command: str
    structured_params: Dict[str, Any]
    confidence: float
    inference_path: List[str]  # 推理路径说明（解释性AI）
    requires_confirmation: bool


class ContextAwareIntentEngine:
    """
    情境感知的动态意图坍缩引擎。
    
    融合了业务规则与社会工程学逻辑，将模糊指令转化为具体参数。
    """

    def __init__(self):
        # 模拟数据库：用户档案
        self._user_db: Dict[str, UserProfile] = {}
        # 模拟规则库：业务逻辑（领域A）
        self._business_rules: Dict[str, Dict] = {}
        # 模拟潜规则库：社会常识（领域B）
        self._social_heuristics: List[Dict] = []
        
        self._initialize_mock_data()
        logger.info("Intent Collapse Engine initialized with Cross-Domain fusion.")

    def _initialize_mock_data(self):
        """初始化模拟数据"""
        # 模拟用户：老王，是一个经常需要处理采购的项目经理
        self._user_db["laowang_001"] = UserProfile(
            user_id="laowang_001",
            preferences={"budget_code": "B-2023-Alpha", "payment_method": "corporate_card"},
            frequent_actions=["procurement", "reimbursement"],
            default_contacts={"supplier": "Acme_Corp", "approver": "boss_li"},
            role="project_manager"
        )
        
        # 领域B潜规则：如果是周五下午且提到了"搞定"，通常指周报或团建安排
        self._social_heuristics.append({
            "condition": {"time": "friday_afternoon", "keyword": "搞定"},
            "implies": {"action": "submit_weekly_report", "target": "boss_li"}
        })

    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """加载用户档案"""
        return self._user_db.get(user_id)

    def _infer_from_social_context(
        self, 
        command: str, 
        user: UserProfile, 
        context: ContextState
    ) -> Tuple[Dict[str, Any], List[str], float]:
        """
        辅助函数：应用领域B（人情世故/潜规则）进行推理。
        
        Args:
            command: 原始指令
            user: 用户画像
            context: 环境上下文
            
        Returns:
            (推断出的参数, 推理路径, 置信度加分)
        """
        inferred_params = {}
        path = []
        confidence_boost = 0.0
        
        # 规则1：环境时间推断
        hour = context.timestamp.hour
        is_friday = context.timestamp.weekday() == 4
        
        if is_friday and 14 <= hour < 18:
            path.append("Context: Friday Afternoon (Social Rule: Wrap up week)")
            confidence_boost += 0.1
            
        # 规则2：模糊指代解析 ("那个事", "搞定它")
        vague_patterns = [r"搞定.*", r"那个事", r"老样子"]
        for pattern in vague_patterns:
            if re.match(pattern, command):
                # 查找用户最频繁的操作
                if user.frequent_actions:
                    top_action = user.frequent_actions[0]
                    inferred_params['action'] = top_action
                    path.append(f"Vague Term Detected -> Mapped to Frequent Action: '{top_action}'")
                    confidence_boost += 0.2
                    
                # 填充默认联系人
                if 'approver' in user.default_contacts:
                    inferred_params['target'] = user.default_contacts['approver']
                    path.append(f"Auto-filled Target: '{inferred_params['target']}' (Default Contact)")

        return inferred_params, path, confidence_boost

    def _apply_business_rules(
        self, 
        base_params: Dict[str, Any], 
        user: UserProfile
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        辅助函数：应用领域A（死板业务规则）完善参数。
        
        Args:
            base_params: 当前已有参数
            user: 用户画像
            
        Returns:
            (完善后的参数, 变更日志)
        """
        changes = []
        final_params = base_params.copy()
        
        # 强制填充：如果存在action但缺少必要参数，从用户画像补充
        if 'action' in final_params:
            # 检查预算代码
            if 'budget_code' not in final_params and 'budget_code' in user.preferences:
                final_params['budget_code'] = user.preferences['budget_code']
                changes.append(f"Filled missing 'budget_code' from user preferences")
                
            # 数据格式标准化
            if 'target' in final_params:
                # 确保target是小写加下划线（模拟格式清洗）
                clean_target = str(final_params['target']).lower().replace(" ", "_")
                if clean_target != final_params['target']:
                    final_params['target'] = clean_target
                    changes.append("Normalized 'target' format to snake_case")

        return final_params, changes

    def dynamic_intent_collapse(
        self, 
        raw_command: str, 
        user_id: str, 
        context: Optional[ContextState] = None
    ) -> CollapsedIntent:
        """
        核心函数：执行动态意图坍缩。
        
        将简略指令转换为完整JSON参数。
        
        Args:
            raw_command: 用户的原始输入，如 "搞定那个事"
            user_id: 用户ID，用于加载画像
            context: 当前环境状态，如果为None则自动生成
            
        Returns:
            CollapsedIntent 对象，包含结构化参数和元数据。
            
        Raises:
            ValueError: 如果用户ID不存在
        """
        if context is None:
            context = ContextState()
            
        logger.info(f"Processing command for {user_id}: '{raw_command}'")
        
        # 1. 验证用户存在性
        user_profile = self.load_user_profile(user_id)
        if not user_profile:
            logger.error(f"User {user_id} not found.")
            raise ValueError(f"User ID {user_id} invalid.")
            
        # 2. 初始化基础参数
        structured_params: Dict[str, Any] = {"raw_input": raw_command}
        inference_path = ["Start Collapse Sequence"]
        total_confidence = 0.5  # 基础置信度

        try:
            # 3. 阶段一：领域B (社会/习惯) 推理
            social_params, social_path, conf_boost = self._infer_from_social_context(
                raw_command, user_profile, context
            )
            structured_params.update(social_params)
            inference_path.extend(social_path)
            total_confidence += conf_boost
            
            # 4. 阶段二：领域A (业务逻辑) 填充
            business_params, business_path = self._apply_business_rules(
                structured_params, user_profile
            )
            structured_params.update(business_params)
            inference_path.extend(business_path)
            
            # 5. 阶段三：最终验证与置信度修正
            # 如果关键参数缺失，大幅降低置信度
            if 'action' not in structured_params:
                total_confidence *= 0.5
                inference_path.append("Warning: Core 'action' parameter inferred with low certainty")
            
            # 边界检查：置信度截断
            final_confidence = min(max(total_confidence, 0.0), 1.0)
            
            # 决定是否需要人工确认
            needs_confirm = final_confidence < 0.8 or "警告" in " ".join(inference_path)

            logger.info(f"Collapse complete. Confidence: {final_confidence:.2f}")
            
            return CollapsedIntent(
                raw_command=raw_command,
                structured_params=structured_params,
                confidence=final_confidence,
                inference_path=inference_path,
                requires_confirmation=needs_confirm
            )

        except Exception as e:
            logger.exception("Error during intent collapse")
            return CollapsedIntent(
                raw_command=raw_command,
                structured_params={},
                confidence=0.0,
                inference_path=[f"System Error: {str(e)}"],
                requires_confirmation=True
            )

    def export_to_json(self, intent: CollapsedIntent) -> str:
        """
        将坍缩结果导出为标准JSON字符串。
        
        Args:
            intent: 坍缩后的意图对象
            
        Returns:
            JSON字符串
        """
        output = {
            "params": intent.structured_params,
            "meta": {
                "confidence": intent.confidence,
                "needs_review": intent.requires_confirmation,
                "logic_trace": intent.inference_path
            }
        }
        return json.dumps(output, indent=2, ensure_ascii=False)


# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 初始化引擎
    engine = ContextAwareIntentEngine()
    
    # 2. 模拟环境：周五下午
    mock_context = ContextState(
        timestamp=datetime(2023, 10, 27, 16, 30), # 周五下午4点半
        location="Office"
    )
    
    # 3. 模拟用户输入：极度省略的指令
    user_input = "搞定那个事"
    user_id = "laowang_001"
    
    print(f"--- User Input: '{user_input}' ---")
    
    # 4. 执行坍缩
    result = engine.dynamic_intent_collapse(
        raw_command=user_input,
        user_id=user_id,
        context=mock_context
    )
    
    # 5. 输出结果
    print("\n--- Collapsed Result (JSON) ---")
    print(engine.export_to_json(result))
    
    if result.requires_confirmation:
        print("\n[System Notice] Confidence is not high enough, asking user for confirmation...")
        # 模拟确认交互
        print(f"Did you mean: Perform '{result.structured_params.get('action')}' "
              f"targeting '{result.structured_params.get('target')}'? (Y/n)")