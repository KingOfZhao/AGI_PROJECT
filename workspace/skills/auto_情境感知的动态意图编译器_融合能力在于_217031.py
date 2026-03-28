"""
名称: auto_情境感知的动态意图编译器_融合能力在于_217031
描述: 【情境感知的动态意图编译器】融合能力在于利用实践技能中的'情境依赖性'（如环境噪音、用户习惯）
      作为解析模糊意图的隐式特征。不仅是解析语法，而是构建一个'情境状态机'，当输入模糊时，
      自动调用历史高频行为模式（类似肌肉记忆）填充缺失参数，生成高鲁棒性的执行代码或指令，
      大幅降低人机交互中的确认成本。
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContextAwareIntentCompiler")

# 定义数据结构
@dataclass
class UserContext:
    """
    用户情境上下文数据类。
    
    Attributes:
        user_id (str): 用户唯一标识。
        noise_level (float): 环境噪音等级 (0.0-1.0)，影响交互模式选择。
        history_frequency (Dict[str, int]): 历史指令频率统计，用于“肌肉记忆”填充。
        preferences (Dict[str, Any]): 用户偏好设置。
        last_interaction (datetime): 上次交互时间。
    """
    user_id: str
    noise_level: float = 0.0
    history_frequency: Dict[str, int] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    last_interaction: datetime = field(default_factory=datetime.now)

    def update_history(self, intent: str) -> None:
        """更新历史频率"""
        self.history_frequency[intent] = self.history_frequency.get(intent, 0) + 1


@dataclass
class CompiledInstruction:
    """
    编译后的指令数据类。
    
    Attributes:
        action (str): 核心动作名称。
        parameters (Dict[str, Any]): 解析后的参数。
        confidence (float): 解析置信度。
        is_implicit_fill (bool): 是否使用了隐式填充（肌肉记忆）。
    """
    action: str
    parameters: Dict[str, Any]
    confidence: float
    is_implicit_fill: bool = False


class ContextAwareIntentCompiler:
    """
    情境感知的动态意图编译器核心类。
    
    利用环境噪音、用户历史习惯等情境特征，将模糊的自然语言意图
    转化为确定性的可执行指令。
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化编译器。
        
        Args:
            config (Optional[Dict]): 配置字典，包含默认参数等。
        """
        self.config = config or {}
        self._context_cache: Dict[str, UserContext] = {}
        logger.info("ContextAwareIntentCompiler initialized.")

    def _validate_context(self, user_id: str) -> UserContext:
        """
        辅助函数：获取或初始化用户上下文。
        
        Args:
            user_id (str): 用户ID。
            
        Returns:
            UserContext: 用户上下文对象。
        """
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Invalid user_id provided.")
        
        if user_id not in self._context_cache:
            # 模拟从数据库加载用户画像
            logger.debug(f"Creating new context for user: {user_id}")
            self._context_cache[user_id] = UserContext(user_id=user_id)
        
        return self._context_cache[user_id]

    def _resolve_ambiguity_by_muscle_memory(self, 
                                            partial_intent: str, 
                                            context: UserContext) -> Optional[Tuple[str, float]]:
        """
        核心函数：利用历史高频行为（肌肉记忆）解决歧义。
        
        当检测到模糊指令（如"打开它"）时，查找该用户在该情境下
        最频繁执行的操作。
        
        Args:
            partial_intent (str): 提取出的模糊意图关键词。
            context (UserContext): 当前用户情境。
            
        Returns:
            Optional[Tuple[str, float]]: 返回 (最可能的完整意图, 概率权重)，
                                         如果没有历史数据则返回 None。
        """
        # 简单的模糊匹配逻辑：检查历史记录中包含该关键词的意图
        candidates = []
        for intent, count in context.history_frequency.items():
            if partial_intent.lower() in intent.lower():
                candidates.append((intent, count))
        
        if not candidates:
            return None
            
        # 按频率排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_intent, top_count = candidates[0]
        
        # 计算简单的置信度权重
        total_counts = sum(context.history_frequency.values())
        confidence = top_count / total_counts if total_counts > 0 else 0.0
        
        logger.info(f"Muscle memory triggered: '{top_intent}' with confidence {confidence:.2f}")
        return top_intent, confidence

    def parse_intent(self, raw_input: str, user_id: str, env_noise: float = 0.0) -> CompiledInstruction:
        """
        核心函数：解析原始输入并编译为指令。
        
        流程：
        1. 获取用户情境。
        2. 基础NLP解析（模拟）。
        3. 检查噪音等级，高噪音时倾向于简短确认或依赖默认值。
        4. 如果参数缺失，调用肌肉记忆填充。
        5. 生成最终指令。
        
        Args:
            raw_input (str): 用户的原始输入文本。
            user_id (str): 用户唯一标识。
            env_noise (float): 当前环境噪音等级 (0.0-1.0)。
            
        Returns:
            CompiledInstruction: 编译后的指令对象。
            
        Raises:
            ValueError: 输入数据无效时抛出。
        """
        if not raw_input or not isinstance(raw_input, str):
            raise ValueError("Input must be a non-empty string.")
        
        if not (0.0 <= env_noise <= 1.0):
            logger.warning("Noise level out of bounds, clamping to [0.0, 1.0]")
            env_noise = max(0.0, min(1.0, env_noise))

        context = self._validate_context(user_id)
        context.noise_level = env_noise
        
        # 1. 模拟基础NLP解析
        # 假设输入可能是 "打开灯光" 或 模糊的 "打开"
        parsed_action = self._extract_action(raw_input)
        parsed_params = self._extract_params(raw_input)
        
        confidence = 0.5
        is_implicit = False

        # 2. 处理模糊性：参数缺失检测
        # 假设 "turn_on" 动作通常需要 "device" 参数
        required_params = self._get_required_params(parsed_action)
        missing_params = [p for p in required_params if p not in parsed_params]

        if missing_params:
            logger.info(f"Missing parameters detected: {missing_params}. Attempting context fill.")
            
            # 3. 调用肌肉记忆填充
            # 这里简化处理，假设我们知道是在寻找 'device' 参数
            memory_hit = self._resolve_ambiguity_by_muscle_memory(parsed_action, context)
            
            if memory_hit:
                # 模拟从历史意图中提取缺失参数
                # 例如历史意图是 "turn_on living_room_light"
                # 这里我们简化逻辑，直接填充一个高频值
                most_common_device = context.preferences.get("default_device", "main_light")
                
                # 如果噪音大，直接使用默认值；如果噪音小，可能需要确认（此处省略确认逻辑，直接填充以降低交互成本）
                if env_noise > 0.7 or memory_hit[1] > 0.8:
                    parsed_params["device"] = most_common_device
                    parsed_params["source"] = "muscle_memory"
                    confidence = memory_hit[1]
                    is_implicit = True
                    logger.info("Context fill successful.")
                else:
                    confidence = 0.4 # 依然模糊，置信度低
            else:
                logger.warning("Ambiguity resolution failed.")

        # 4. 更新用户历史
        full_intent_key = f"{parsed_action}:{json.dumps(parsed_params)}"
        context.update_history(full_intent_key)

        return CompiledInstruction(
            action=parsed_action,
            parameters=parsed_params,
            confidence=confidence,
            is_implicit_fill=is_implicit
        )

    # --- 以下是模拟辅助方法 ---

    def _extract_action(self, text: str) -> str:
        """辅助：从文本提取动作"""
        if "打开" in text or "开启" in text:
            return "turn_on"
        elif "关闭" in text:
            return "turn_off"
        elif "查询" in text:
            return "query"
        return "unknown"

    def _extract_params(self, text: str) -> Dict[str, Any]:
        """辅助：从文本提取参数"""
        params = {}
        if "空调" in text:
            params["device"] = "air_conditioner"
        elif "灯" in text:
            params["device"] = "light"
        elif "音乐" in text:
            params["device"] = "speaker"
        
        # 提取温度等数值
        temp_match = re.search(r'(\d+)度', text)
        if temp_match:
            params["temperature"] = int(temp_match.group(1))
            
        return params

    def _get_required_params(self, action: str) -> List[str]:
        """辅助：获取动作所需的参数定义"""
        schema = {
            "turn_on": ["device"],
            "turn_off": ["device"],
            "query": ["target"],
            "unknown": []
        }
        return schema.get(action, [])


# --- 使用示例 ---
if __name__ == "__main__":
    # 初始化编译器
    compiler = ContextAwareIntentCompiler()
    
    # 模拟用户场景
    user = "user_123"
    
    # 1. 第一次明确的交互，建立历史记录
    print("--- Interaction 1: Explicit ---")
    instruction_1 = compiler.parse_intent("打开空调", user, env_noise=0.1)
    print(f"Action: {instruction_1.action}, Params: {instruction_1.parameters}, Implicit: {instruction_1.is_implicit_fill}")
    
    # 模拟用户多次操作空调，建立 '肌肉记忆'
    compiler._context_cache[user].preferences["default_device"] = "air_conditioner"
    for _ in range(5):
        compiler._context_cache[user].update_history("turn_on:air_conditioner")

    # 2. 模糊交互：高噪音环境，输入 "打开" (缺失对象)
    print("\n--- Interaction 2: Ambiguous (High Noise) ---")
    # 此时系统检测到缺失参数，且环境噪音大(0.8)，自动使用高频对象 'air_conditioner'
    instruction_2 = compiler.parse_intent("打开", user, env_noise=0.8)
    print(f"Action: {instruction_2.action}, Params: {instruction_2.parameters}")
    print(f"Implicit Fill Used: {instruction_2.is_implicit_fill}") # 应该为 True

    # 3. 边界检查示例
    print("\n--- Interaction 3: Error Handling ---")
    try:
        compiler.parse_intent("", user)
    except ValueError as e:
        print(f"Caught expected error: {e}")