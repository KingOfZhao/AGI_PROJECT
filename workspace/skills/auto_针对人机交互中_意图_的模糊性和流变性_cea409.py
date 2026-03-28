"""
模块名称: auto_针对人机交互中_意图_的模糊性和流变性_cea409
描述: 针对人机交互中“意图”的模糊性和流变性，提出的一种代码生成与状态管理协议。
      该概念不追求一次性完美解析，而是建立一套“上下文状态机”，在多轮对话中动态捕捉和修正意图。
      它要求系统显式标注“假设边界”和“不确定性”，将模糊的自然语言转化为结构化的DSL（领域特定语言）时，
      能够自动进行逻辑自洽性检验，并在最小可执行单元层面进行证伪，确保生成的代码或方案在逻辑闭环上是坚实的。
"""

import logging
import json
import re
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentFuzzinessManager")

class IntentState(Enum):
    """意图状态枚举，表示意图在交互过程中的不同阶段"""
    INIT = auto()           # 初始状态
    CLARIFYING = auto()     # 澄清中
    HYPOTHESIZED = auto()   # 已建立假设
    VALIDATED = auto()      # 已验证
    FALSIFIED = auto()      # 已证伪
    EXECUTED = auto()       # 已执行

class IntentValidationError(Exception):
    """意图验证错误，用于处理数据验证失败的情况"""
    pass

class DSLConversionError(Exception):
    """DSL转换错误，用于处理自然语言到DSL转换失败的情况"""
    pass

@dataclass
class Hypothesis:
    """假设数据结构，用于存储意图假设及其边界"""
    id: str
    description: str
    confidence: float
    assumptions: List[str] = field(default_factory=list)
    boundaries: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """将假设对象转换为字典"""
        return asdict(self)

@dataclass
class IntentContext:
    """意图上下文，存储整个交互过程中的状态和数据"""
    session_id: str
    current_state: IntentState = IntentState.INIT
    raw_input: str = ""
    dsl_representation: Dict[str, Any] = field(default_factory=dict)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    uncertainty_score: float = 1.0  # 0.0 表示完全确定，1.0 表示完全不确定
    
    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """添加新的假设到上下文"""
        self.hypotheses.append(hypothesis)
        self._update_uncertainty()
        
    def _update_uncertainty(self) -> None:
        """根据假设更新不确定性分数"""
        if not self.hypotheses:
            self.uncertainty_score = 1.0
            return
            
        # 使用最高置信度的假设来更新不确定性
        max_confidence = max(h.confidence for h in self.hypotheses)
        self.uncertainty_score = 1.0 - max_confidence
        
    def to_dict(self) -> Dict[str, Any]:
        """将上下文对象转换为字典"""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.name,
            "raw_input": self.raw_input,
            "dsl_representation": self.dsl_representation,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "validation_results": self.validation_results,
            "history": self.history,
            "uncertainty_score": self.uncertainty_score
        }

class IntentStateMachine:
    """意图状态机，管理意图的整个生命周期"""
    
    def __init__(self):
        """初始化状态机"""
        self.sessions: Dict[str, IntentContext] = {}
        self.dsl_patterns = {
            "query": r"what|how|when|where|why|who",
            "command": r"do|make|create|delete|update|remove",
            "preference": r"like|prefer|want|need|wish"
        }
        
    def create_session(self, session_id: str) -> IntentContext:
        """创建新的会话上下文
        
        参数:
            session_id: 会话唯一标识符
            
        返回:
            新创建的IntentContext对象
            
        异常:
            ValueError: 如果session_id已存在
        """
        if session_id in self.sessions:
            logger.warning(f"Session ID {session_id} already exists")
            raise ValueError(f"Session ID {session_id} already exists")
            
        context = IntentContext(session_id=session_id)
        self.sessions[session_id] = context
        logger.info(f"Created new session: {session_id}")
        return context
        
    def process_input(self, session_id: str, raw_input: str) -> IntentContext:
        """处理用户输入并更新意图状态
        
        参数:
            session_id: 会话唯一标识符
            raw_input: 用户原始输入文本
            
        返回:
            更新后的IntentContext对象
            
        异常:
            KeyError: 如果session_id不存在
            DSLConversionError: 如果无法将输入转换为DSL
        """
        if session_id not in self.sessions:
            logger.error(f"Session ID {session_id} not found")
            raise KeyError(f"Session ID {session_id} not found")
            
        context = self.sessions[session_id]
        context.raw_input = raw_input
        context.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "input_received",
            "data": raw_input
        })
        
        try:
            # 转换输入为DSL表示
            dsl = self._convert_to_dsl(raw_input)
            context.dsl_representation = dsl
            
            # 生成初始假设
            hypothesis = self._generate_initial_hypothesis(dsl)
            context.add_hypothesis(hypothesis)
            
            # 更新状态
            if context.current_state == IntentState.INIT:
                context.current_state = IntentState.HYPOTHESIZED
            elif context.current_state == IntentState.HYPOTHESIZED:
                context.current_state = IntentState.CLARIFYING
                
            logger.info(f"Processed input for session {session_id}: {raw_input[:50]}...")
            return context
            
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            raise DSLConversionError(f"Failed to convert input to DSL: {str(e)}")
            
    def _convert_to_dsl(self, raw_input: str) -> Dict[str, Any]:
        """将自然语言输入转换为结构化的DSL表示
        
        参数:
            raw_input: 用户原始输入文本
            
        返回:
            包含DSL表示的字典
            
        异常:
            DSLConversionError: 如果转换失败
        """
        if not raw_input or not isinstance(raw_input, str):
            raise DSLConversionError("Input must be a non-empty string")
            
        dsl: Dict[str, Any] = {
            "original_text": raw_input,
            "intent_type": "unknown",
            "entities": [],
            "actions": [],
            "constraints": [],
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        try:
            # 检测意图类型
            for intent_type, pattern in self.dsl_patterns.items():
                if re.search(pattern, raw_input.lower()):
                    dsl["intent_type"] = intent_type
                    break
                    
            # 提取实体 (简化示例，实际应用中可以使用NLP库)
            words = raw_input.split()
            entities = [word for word in words if len(word) > 3 and word.isalpha()]
            dsl["entities"] = list(set(entities))
            
            # 提取动作 (简化示例)
            action_verbs = ["create", "delete", "update", "get", "find", "make"]
            dsl["actions"] = [verb for verb in action_verbs if verb in raw_input.lower()]
            
            logger.debug(f"Generated DSL: {dsl}")
            return dsl
            
        except Exception as e:
            logger.error(f"DSL conversion error: {str(e)}")
            raise DSLConversionError(f"Failed to convert input to DSL: {str(e)}")
            
    def _generate_initial_hypothesis(self, dsl: Dict[str, Any]) -> Hypothesis:
        """基于DSL生成初始意图假设
        
        参数:
            dsl: 结构化的DSL表示
            
        返回:
            生成的Hypothesis对象
        """
        hypothesis_id = f"hyp_{datetime.now().timestamp()}"
        
        # 根据DSL内容生成假设描述
        description = f"User intent appears to be a {dsl['intent_type']}"
        if dsl['entities']:
            description += f" related to {', '.join(dsl['entities'][:3])}"
        if dsl['actions']:
            description += f" with actions: {', '.join(dsl['actions'])}"
            
        # 计算初始置信度 (简化示例)
        confidence = 0.7 if dsl['intent_type'] != "unknown" else 0.3
        if dsl['entities']:
            confidence += 0.1
        if dsl['actions']:
            confidence += 0.1
            
        confidence = min(max(confidence, 0.0), 1.0)  # 确保在0-1范围内
        
        # 定义假设边界
        boundaries = {
            "max_confidence": confidence,
            "min_confidence": 0.1,
            "valid_intent_types": ["query", "command", "preference"]
        }
        
        # 定义假设假设 (元假设!)
        assumptions = [
            "User input is in English",
            "User has a single primary intent",
            "Intent can be categorized into predefined types"
        ]
        
        return Hypothesis(
            id=hypothesis_id,
            description=description,
            confidence=confidence,
            assumptions=assumptions,
            boundaries=boundaries
        )
        
    def validate_hypothesis(self, session_id: str, hypothesis_id: str, 
                           validation_data: Dict[str, Any]) -> IntentContext:
        """验证特定的意图假设
        
        参数:
            session_id: 会话唯一标识符
            hypothesis_id: 要验证的假设ID
            validation_data: 用于验证的数据
            
        返回:
            更新后的IntentContext对象
            
        异常:
            KeyError: 如果session_id或hypothesis_id不存在
            IntentValidationError: 如果验证失败
        """
        if session_id not in self.sessions:
            logger.error(f"Session ID {session_id} not found")
            raise KeyError(f"Session ID {session_id} not found")
            
        context = self.sessions[session_id]
        hypothesis = next((h for h in context.hypotheses if h.id == hypothesis_id), None)
        
        if not hypothesis:
            logger.error(f"Hypothesis ID {hypothesis_id} not found in session {session_id}")
            raise KeyError(f"Hypothesis ID {hypothesis_id} not found")
            
        try:
            # 执行逻辑自洽性检验
            validation_result = {
                "hypothesis_id": hypothesis_id,
                "is_valid": True,
                "issues": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 检查1: 假设边界是否被违反
            if hypothesis.confidence > hypothesis.boundaries["max_confidence"]:
                validation_result["is_valid"] = False
                validation_result["issues"].append("Confidence exceeds maximum boundary")
                
            # 检查2: 意图类型是否有效
            if context.dsl_representation["intent_type"] not in hypothesis.boundaries["valid_intent_types"]:
                validation_result["is_valid"] = False
                validation_result["issues"].append("Invalid intent type for this hypothesis")
                
            # 检查3: 验证数据是否提供额外证据
            if "supporting_evidence" in validation_data:
                evidence = validation_data["supporting_evidence"]
                if isinstance(evidence, list) and len(evidence) > 0:
                    # 增加置信度
                    hypothesis.confidence = min(hypothesis.confidence + 0.1 * len(evidence), 
                                              hypothesis.boundaries["max_confidence"])
                    
            # 检查4: 验证数据是否提供反驳证据
            if "contradicting_evidence" in validation_data:
                evidence = validation_data["contradicting_evidence"]
                if isinstance(evidence, list) and len(evidence) > 0:
                    # 降低置信度
                    hypothesis.confidence = max(hypothesis.confidence - 0.2 * len(evidence), 
                                              hypothesis.boundaries["min_confidence"])
                    
                    if hypothesis.confidence < 0.3:
                        validation_result["is_valid"] = False
                        validation_result["issues"].append("Confidence too low after contradicting evidence")
            
            # 更新验证结果
            context.validation_results.append(validation_result)
            
            # 更新状态
            if validation_result["is_valid"]:
                context.current_state = IntentState.VALIDATED
            else:
                context.current_state = IntentState.FALSIFIED
                
            # 记录历史
            context.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "hypothesis_validated",
                "hypothesis_id": hypothesis_id,
                "result": validation_result["is_valid"]
            })
            
            # 更新不确定性分数
            context._update_uncertainty()
            
            logger.info(f"Validated hypothesis {hypothesis_id} for session {session_id}: {'Valid' if validation_result['is_valid'] else 'Invalid'}")
            return context
            
        except Exception as e:
            logger.error(f"Error validating hypothesis: {str(e)}")
            raise IntentValidationError(f"Failed to validate hypothesis: {str(e)}")
            
    def generate_response(self, session_id: str) -> Dict[str, Any]:
        """基于当前意图状态生成响应
        
        参数:
            session_id: 会话唯一标识符
            
        返回:
            包含响应数据和动作建议的字典
            
        异常:
            KeyError: 如果session_id不存在
        """
        if session_id not in self.sessions:
            logger.error(f"Session ID {session_id} not found")
            raise KeyError(f"Session ID {session_id} not found")
            
        context = self.sessions[session_id]
        response = {
            "session_id": session_id,
            "state": context.current_state.name,
            "uncertainty_score": context.uncertainty_score,
            "message": "",
            "suggested_actions": [],
            "hypotheses": [h.to_dict() for h in context.hypotheses]
        }
        
        # 根据状态生成不同的响应
        if context.current_state == IntentState.INIT:
            response["message"] = "I'm not sure what you mean. Could you please provide more details?"
            response["suggested_actions"] = ["clarify_intent"]
            
        elif context.current_state == IntentState.HYPOTHESIZED:
            if context.hypotheses:
                top_hypothesis = max(context.hypotheses, key=lambda h: h.confidence)
                response["message"] = f"I think you want to {top_hypothesis.description}. Am I correct?"
                response["suggested_actions"] = ["confirm_hypothesis", "reject_hypothesis", "provide_more_details"]
            else:
                response["message"] = "I'm still trying to understand your intent."
                response["suggested_actions"] = ["clarify_intent"]
                
        elif context.current_state == IntentState.CLARIFYING:
            response["message"] = "I need some more information to better understand your intent."
            response["suggested_actions"] = ["provide_examples", "narrow_down_intent"]
            
        elif context.current_state == IntentState.VALIDATED:
            response["message"] = "I'm confident I understand your intent. Ready to proceed."
            response["suggested_actions"] = ["execute_action", "refine_parameters"]
            
        elif context.current_state == IntentState.FALSIFIED:
            response["message"] = "My previous understanding was incorrect. Let's try again."
            response["suggested_actions"] = ["restart_intent_detection", "provide_different_perspective"]
            
        elif context.current_state == IntentState.EXECUTED:
            response["message"] = "Action has been executed based on your intent."
            response["suggested_actions"] = ["rate_result", "provide_feedback", "start_new_intent"]
            
        # 记录历史
        context.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "response_generated",
            "state": context.current_state.name
        })
        
        logger.info(f"Generated response for session {session_id} in state {context.current_state.name}")
        return response
        
    def execute_intent(self, session_id: str) -> IntentContext:
        """执行已验证的意图
        
        参数:
            session_id: 会话唯一标识符
            
        返回:
            更新后的IntentContext对象
            
        异常:
            KeyError: 如果session_id不存在
            ValueError: 如果意图尚未验证
        """
        if session_id not in self.sessions:
            logger.error(f"Session ID {session_id} not found")
            raise KeyError(f"Session ID {session_id} not found")
            
        context = self.sessions[session_id]
        
        if context.current_state != IntentState.VALIDATED:
            logger.error(f"Cannot execute intent in state {context.current_state.name}")
            raise ValueError(f"Intent must be in VALIDATED state before execution. Current state: {context.current_state.name}")
            
        try:
            # 模拟执行意图
            execution_result = {
                "status": "success",
                "executed_at": datetime.now().isoformat(),
                "details": f"Executed intent based on hypothesis {context.hypotheses[-1].id}"
            }
            
            # 更新状态
            context.current_state = IntentState.EXECUTED
            
            # 记录历史
            context.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "intent_executed",
                "result": execution_result
            })
            
            logger.info(f"Executed intent for session {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error executing intent: {str(e)}")
            context.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "execution_failed",
                "error": str(e)
            })
            raise

def format_uncertainty_score(score: float) -> str:
    """格式化不确定性分数为人类可读的字符串
    
    参数:
        score: 不确定性分数 (0.0-1.0)
        
    返回:
        人类可读的不确定性描述
        
    异常:
        ValueError: 如果分数不在0-1范围内
    """
    if not isinstance(score, (int, float)) or score < 0 or score > 1:
        logger.error(f"Invalid uncertainty score: {score}")
        raise ValueError("Uncertainty score must be between 0.0 and 1.0")
        
    if score < 0.2:
        return "Very certain"
    elif score < 0.4:
        return "Fairly certain"
    elif score < 0.6:
        return "Somewhat uncertain"
    elif score < 0.8:
        return "Very uncertain"
    else:
        return "Extremely uncertain"

# 示例使用
if __name__ == "__main__":
    try:
        # 创建状态机实例
        state_machine = IntentStateMachine()
        
        # 创建新会话
        session = state_machine.create_session("user123_session")
        print(f"Created session: {session.session_id}")
        
        # 处理用户输入
        session = state_machine.process_input("user123_session", 
                                            "I want to create a new report about monthly sales")
        print(f"Processed input. Current state: {session.current_state.name}")
        print(f"Generated DSL: {json.dumps(session.dsl_representation, indent=2)}")
        
        # 获取生成的响应
        response = state_machine.generate_response("user123_session")
        print(f"\nSystem response: {response['message']}")
        print(f"Suggested actions: {', '.join(response['suggested_actions'])}")
        print(f"Uncertainty: {format_uncertainty_score(session.uncertainty_score)}")
        
        # 验证假设
        if session.hypotheses:
            hypothesis_id = session.hypotheses[0].id
            validation_data = {
                "supporting_evidence": ["User mentioned 'report'", "User mentioned 'monthly sales'"],
                "contradicting_evidence": []
            }
            session = state_machine.validate_hypothesis("user123_session", hypothesis_id, validation_data)
            print(f"\nValidated hypothesis. New state: {session.current_state.name}")
            print(f"Updated uncertainty: {format_uncertainty_score(session.uncertainty_score)}")
            
        # 执行意图
        if session.current_state == IntentState.VALIDATED:
            session = state_machine.execute_intent("user123_session")
            print(f"\nExecuted intent. Final state: {session.current_state.name}")
            
    except Exception as e:
        logger.error(f"Error in example usage: {str(e)}")