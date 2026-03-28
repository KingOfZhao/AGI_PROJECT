"""
模块: auto_双向动态意图解析器_利用agi的_意_76e095
描述: 本模块实现了一个基于AGI状态机逻辑的双向动态意图解析器。
      它旨在将模糊的人类自然语言需求转化为严格的JSON规范文档。
      核心特性包括认知阻力机制，用于检测逻辑不自洽并强制中断澄清。
"""

import json
import logging
import re
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BidirectionalIntentParser")

# 定义常量
MAX_INPUT_LENGTH = 2048
MIN_CONFIDENCE_SCORE = 0.6

class ParserState(Enum):
    """解析器状态机的状态枚举。"""
    IDLE = auto()                # 空闲，等待输入
    ANALYZING = auto()           # 正在分析语义
    VALIDATING = auto()          # 正在验证逻辑自洽性
    CLARIFYING = auto()          # 需求澄清中（触发认知阻力）
    FINALIZING = auto()          # 生成最终规范
    COMPLETED = auto()           # 完成

class IntentParserError(Exception):
    """自定义异常类，用于处理解析过程中的特定错误。"""
    pass

class CognitiveResistanceError(IntentParserError):
    """当检测到逻辑冲突且无法自动解决时抛出。"""
    def __init__(self, message: str, conflicts: List[str]):
        super().__init__(message)
        self.conflicts = conflicts

class BidirectionalIntentParser:
    """
    双向动态意图解析器类。
    
    利用AGI的状态机逻辑，将模糊输入映射为结构化JSON。
    支持双向交互：不仅解析输入，还能生成反馈（询问）以细化需求。
    
    属性:
        state (ParserState): 当前解析器状态。
        raw_input (str): 原始用户输入。
        context_buffer (Dict): 存储解析过程中的中间上下文。
        final_spec (Dict): 最终生成的规范文档。
    """

    def __init__(self) -> None:
        """初始化解析器实例。"""
        self.state = ParserState.IDLE
        self.raw_input: str = ""
        self.context_buffer: Dict[str, Any] = {
            "keywords": [],
            "entities": {},
            "constraints": []
        }
        self.final_spec: Dict[str, Any] = {}
        logger.info("BidirectionalIntentParser initialized.")

    def _preprocess_input(self, user_input: str) -> str:
        """
        辅助函数：输入预处理与边界检查。
        
        Args:
            user_input (str): 原始用户输入字符串。
            
        Returns:
            str: 清洗后的字符串。
            
        Raises:
            ValueError: 如果输入为空或超过长度限制。
        """
        if not user_input or not isinstance(user_input, str):
            raise ValueError("Input must be a non-empty string.")
        
        stripped_input = user_input.strip()
        if len(stripped_input) > MAX_INPUT_LENGTH:
            logger.warning(f"Input truncated from {len(stripped_input)} to {MAX_INPUT_LENGTH}.")
            return stripped_input[:MAX_INPUT_LENGTH]
        
        # 简单的文本清洗，去除多余空格
        return re.sub(r'\s+', ' ', stripped_input)

    def _extract_semantic_components(self, text: str) -> Dict[str, Any]:
        """
        核心函数：语义组件提取（模拟NLP解析）。
        
        将自然语言分解为关键词、实体和约束条件。
        这是一个简化的模拟实现，实际AGI系统会调用LLM或NLP引擎。
        
        Args:
            text (str): 预处理后的文本。
            
        Returns:
            Dict[str, Any]: 包含keywords, entities, constraints的字典。
        """
        # 模拟提取逻辑
        # 在实际场景中，这里会使用Transformer模型进行NER和关系抽取
        components = {
            "keywords": [],
            "entities": {},
            "constraints": []
        }
        
        # 模拟关键词匹配
        keywords_map = {
            "装修": "renovation",
            "极简": "minimalist",
            "繁复": "complex",
            "策划": "planning",
            "活动": "event"
        }
        
        for cn, en in keywords_map.items():
            if cn in text:
                components["keywords"].append(en)
        
        # 模拟实体识别
        if "预算" in text:
            # 尝试提取数字（简化正则）
            budget_match = re.search(r'(\d+)', text)
            if budget_match:
                components["entities"]["budget"] = int(budget_match.group(1))
        
        logger.debug(f"Extracted components: {components}")
        return components

    def _check_cognitive_resistance(self, components: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        核心函数：认知阻力检查。
        
        分析需求内部的逻辑自洽性。如果发现矛盾（如风格冲突），
        返回需要澄清的冲突列表。
        
        Args:
            components (Dict): 提取出的语义组件。
            
        Returns:
            Tuple[bool, List[str]]: (是否存在冲突, 冲突描述列表)
        """
        conflicts = []
        keywords = components.get("keywords", [])
        
        # 规则1：风格冲突检测
        if "minimalist" in keywords and "complex" in keywords:
            conflict_msg = "Logical Contradiction: Requesting 'minimalist' style while simultaneously requiring 'complex' elements."
            conflicts.append(conflict_msg)
            logger.warning(f"Cognitive resistance triggered: {conflict_msg}")
        
        # 规则2：预算与范围冲突（模拟）
        budget = components.get("entities", {}).get("budget", 0)
        if budget > 0 and budget < 5000 and "renovation" in keywords:
            conflicts.append("Budget Constraints: Renovation budget appears unrealistic for full scope.")
            
        return len(conflicts) > 0, conflicts

    def process_intent(self, user_input: str) -> Dict[str, Any]:
        """
        主入口函数：处理用户意图。
        
        执行完整的状态机循环：输入 -> 解析 -> 验证 -> 输出/异常。
        
        Args:
            user_input (str): 用户的自然语言需求。
            
        Returns:
            Dict[str, Any]: 如果成功，返回结构化的JSON规范。
            
        Raises:
            CognitiveResistanceError: 如果需求逻辑不自洽，强制中断并询问。
            IntentParserError: 其他解析错误。
        """
        try:
            self.state = ParserState.ANALYZING
            logger.info(f"Processing intent: '{user_input}'")
            
            # 1. 预处理
            clean_text = self._preprocess_input(user_input)
            self.raw_input = clean_text
            
            # 2. 语义提取
            components = self._extract_semantic_components(clean_text)
            self.context_buffer.update(components)
            
            # 3. 认知阻力检查 (状态转移至 VALIDATING)
            self.state = ParserState.VALIDATING
            has_conflicts, conflict_list = self._check_cognitive_resistance(self.context_buffer)
            
            if has_conflicts:
                self.state = ParserState.CLARIFYING
                # 这里模拟AGI的“强制询问”特性
                raise CognitiveResistanceError(
                    "Requirements are logically inconsistent. Clarification required.",
                    conflict_list
                )
            
            # 4. 生成规范 (状态转移至 FINALIZING)
            self.state = ParserState.FINALIZING
            self.final_spec = self._generate_spec_json()
            
            self.state = ParserState.COMPLETED
            return self.final_spec

        except ValueError as ve:
            logger.error(f"Input validation error: {ve}")
            raise IntentParserError(f"Invalid Input: {ve}")
        except Exception as e:
            logger.critical(f"Unexpected error during intent processing: {e}")
            raise IntentParserError("System encountered an internal error.")

    def _generate_spec_json(self) -> Dict[str, Any]:
        """
        辅助函数：生成最终的JSON规范。
        
        基于解析后的上下文构建严格的JSON结构。
        """
        spec = {
            "meta": {
                "parser_version": "1.0.0",
                "status": "RESOLVED"
            },
            "intent": {
                "domain": self._detect_domain(),
                "attributes": self.context_buffer.get("entities", {}),
                "style_keywords": self.context_buffer.get("keywords", [])
            }
        }
        return spec

    def _detect_domain(self) -> str:
        """简单的域检测逻辑。"""
        kws = self.context_buffer.get("keywords", [])
        if "renovation" in kws:
            return "INTERIOR_DESIGN"
        if "event" in kws or "planning" in kws:
            return "EVENT_MANAGEMENT"
        return "GENERAL"

# 示例用法
if __name__ == "__main__":
    parser = BidirectionalIntentParser()
    
    # 示例 1: 正常流程
    try:
        print("--- Test Case 1: Valid Request ---")
        result = parser.process_intent("我想要一个极简风格的装修，预算在50000左右")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except CognitiveResistanceError as e:
        print(f"Clarification needed: {e.conflicts}")

    print("\n" + "="*30 + "\n")

    # 示例 2: 触发认知阻力 (逻辑冲突)
    try:
        print("--- Test Case 2: Contradictory Request ---")
        # 这里既有"极简"又有"繁复"，将触发异常
        result = parser.process_intent("帮我策划一个活动，风格既要极简又要繁复华丽")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except CognitiveResistanceError as e:
        print(f"Cognitive Resistance Triggered!")
        print(f"System Question: {e}")
        print(f"Detected Conflicts: {e.conflicts}")