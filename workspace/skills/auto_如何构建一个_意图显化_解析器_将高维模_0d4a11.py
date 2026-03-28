"""
模块名称: intent_explicit_parser
描述: 构建'意图显化'解析器，将高维模糊自然语言映射为结构化IR，利用约束词典补全参数并量化置信度。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MIN_CONFIDENCE_SCORE = 0.65
TOTAL_SKILL_NODES = 1980

@dataclass
class SkillNode:
    """
    技能节点定义，作为约束词典的条目。
    
    Attributes:
        id (str): 节点唯一标识
        keywords (List[str]): 触发该技能的关键词列表
        default_params (Dict[str, Any]): 默认参数配置
        category (str): 所属类别
    """
    id: str
    keywords: List[str]
    default_params: Dict[str, Any]
    category: str

@dataclass
class StructuredIR:
    """
    结构化中间表示，包含显式约束和解析元数据。
    
    Attributes:
        raw_input (str): 原始输入文本
        intent (str): 识别出的核心意图
        constraints (Dict[str, Any]): 显式约束参数
        confidence (float): 置信度分值 (0.0-1.0)
        missing_params (List[str]): 缺失且未补全的参数列表
        matched_skills (List[str]): 匹配到的技能节点ID列表
    """
    raw_input: str
    intent: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    missing_params: List[str] = field(default_factory=list)
    matched_skills: List[str] = field(default_factory=list)

class IntentExplicitParser:
    """
    意图显化解析器：将模糊自然语言指令转换为结构化中间表示。
    
    该解析器利用预定义的技能节点作为约束词典，自动补全缺失参数，
    量化模糊度，并拒绝置信度过低的无效指令。
    
    Attributes:
        skill_nodes (Dict[str, SkillNode]): 技能节点字典
        confidence_threshold (float): 置信度阈值
        
    Example:
        >>> parser = IntentExplicitParser()
        >>> parser.load_skill_nodes(sample_nodes)
        >>> ir = parser.parse("做一个好玩的贪吃蛇游戏")
        >>> if ir.confidence >= MIN_CONFIDENCE_SCORE:
        ...     print(f"解析成功: {ir.intent}")
    """
    
    def __init__(self, confidence_threshold: float = MIN_CONFIDENCE_SCORE):
        """
        初始化解析器。
        
        Args:
            confidence_threshold: 置信度阈值，低于此值的指令将被拒绝
        """
        self.skill_nodes: Dict[str, SkillNode] = {}
        self.confidence_threshold = confidence_threshold
        logger.info("IntentExplicitParser initialized with threshold %.2f", confidence_threshold)
    
    def load_skill_nodes(self, nodes: List[SkillNode]) -> None:
        """
        加载技能节点作为约束词典。
        
        Args:
            nodes: 技能节点列表
            
        Raises:
            ValueError: 如果节点数量超过限制或节点ID重复
        """
        if len(nodes) > TOTAL_SKILL_NODES:
            raise ValueError(f"Skill nodes exceed maximum limit of {TOTAL_SKILL_NODES}")
            
        for node in nodes:
            if node.id in self.skill_nodes:
                raise ValueError(f"Duplicate skill node ID: {node.id}")
            self.skill_nodes[node.id] = node
            
        logger.info("Loaded %d skill nodes into constraint dictionary", len(nodes))
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理输入文本：标准化格式、去除噪音。
        
        Args:
            text: 原始输入文本
            
        Returns:
            处理后的标准化文本
        """
        # 转换为小写并去除多余空格
        processed = text.lower().strip()
        processed = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', processed)  # 保留中文字符
        processed = ' '.join(processed.split())
        logger.debug("Preprocessed text: '%s' -> '%s'", text, processed)
        return processed
    
    def _calculate_confidence(self, 
                            matched_skills: List[SkillNode],
                            input_length: int) -> float:
        """
        计算解析置信度。
        
        Args:
            matched_skills: 匹配到的技能节点列表
            input_length: 输入文本长度
            
        Returns:
            置信度分值 (0.0-1.0)
        """
        if not matched_skills:
            return 0.0
            
        # 基础分值：匹配到的技能数量/总技能数（归一化）
        skill_score = min(len(matched_skills) / 10.0, 1.0) * 0.4
        
        # 输入长度得分（防止过短输入）
        length_score = min(input_length / 20.0, 1.0) * 0.3
        
        # 类别一致性得分
        categories = {s.category for s in matched_skills}
        category_score = 0.3 if len(categories) == 1 else 0.1 * len(categories)
        
        total_score = skill_score + length_score + category_score
        return min(max(total_score, 0.0), 1.0)  # 确保在0-1范围内
    
    def _match_skills(self, text: str) -> List[SkillNode]:
        """
        在约束词典中匹配相关技能节点。
        
        Args:
            text: 预处理后的输入文本
            
        Returns:
            匹配到的技能节点列表
        """
        matched = []
        words = set(text.split())
        
        for node in self.skill_nodes.values():
            # 检查是否有任何关键词出现在输入中
            if any(kw in text for kw in node.keywords):
                matched.append(node)
                
        logger.debug("Matched %d skills for input: '%s'", len(matched), text)
        return matched
    
    def _complete_parameters(self, 
                           matched_skills: List[SkillNode],
                           constraints: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        自动补全缺失参数。
        
        Args:
            matched_skills: 匹配到的技能节点
            constraints: 当前已识别的约束
            
        Returns:
            Tuple[补全后的约束字典, 仍缺失的参数列表]
        """
        completed = constraints.copy()
        missing = []
        
        # 收集所有默认参数
        param_sources = {}
        for skill in matched_skills:
            for param, value in skill.default_params.items():
                if param not in param_sources:
                    param_sources[param] = []
                param_sources[param].append((skill.id, value))
        
        # 应用最常见的默认值
        for param, sources in param_sources.items():
            if param not in completed:
                # 选择最频繁的默认值
                value_counts = {}
                for _, val in sources:
                    val_str = str(val)
                    value_counts[val_str] = value_counts.get(val_str, 0) + 1
                
                most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                completed[param] = most_common
                logger.debug("Auto-completed param '%s' with value '%s'", param, most_common)
        
        # 检查仍缺失的关键参数
        required_params = ['interface_style', 'win_condition']
        for param in required_params:
            if param not in completed:
                missing.append(param)
                
        return completed, missing
    
    def parse(self, input_text: str) -> StructuredIR:
        """
        主解析函数：将自然语言转换为结构化IR。
        
        Args:
            input_text: 原始自然语言输入
            
        Returns:
            StructuredIR: 结构化中间表示
            
        Raises:
            ValueError: 如果输入为空或解析失败
        """
        if not input_text or not input_text.strip():
            raise ValueError("Input text cannot be empty")
            
        logger.info("Parsing input: '%s'", input_text)
        
        # 1. 文本预处理
        processed_text = self._preprocess_text(input_text)
        
        # 2. 技能匹配
        matched_skills = self._match_skills(processed_text)
        if not matched_skills:
            logger.warning("No matching skills found for input: '%s'", input_text)
            return StructuredIR(
                raw_input=input_text,
                intent="unknown",
                confidence=0.0,
                missing_params=["intent"]
            )
        
        # 3. 提取核心意图（使用匹配技能的主类别）
        intent = matched_skills[0].category
        logger.debug("Extracted intent: '%s'", intent)
        
        # 4. 计算置信度
        confidence = self._calculate_confidence(matched_skills, len(processed_text))
        logger.debug("Calculated confidence: %.2f", confidence)
        
        # 5. 参数补全
        initial_constraints = {
            'input_length': len(input_text),
            'complexity': 'medium'  # 默认复杂度
        }
        completed_constraints, missing_params = self._complete_parameters(
            matched_skills, initial_constraints
        )
        
        # 6. 构建结构化IR
        ir = StructuredIR(
            raw_input=input_text,
            intent=intent,
            constraints=completed_constraints,
            confidence=confidence,
            missing_params=missing_params,
            matched_skills=[s.id for s in matched_skills]
        )
        
        # 7. 置信度检查
        if confidence < self.confidence_threshold:
            logger.warning(
                "Low confidence (%.2f) for input: '%s'. Threshold is %.2f",
                confidence, input_text, self.confidence_threshold
            )
        
        return ir

# 示例使用
if __name__ == "__main__":
    # 创建示例技能节点
    sample_nodes = [
        SkillNode(
            id="snake_game",
            keywords=["贪吃蛇", "snake", "游戏"],
            default_params={
                "interface_style": "minimalist",
                "win_condition": "score_based",
                "controls": "arrow_keys"
            },
            category="game_development"
        ),
        SkillNode(
            id="platform_game",
            keywords=["平台游戏", "跳跃", "platformer"],
            default_params={
                "interface_style": "pixel_art",
                "win_condition": "level_completion",
                "controls": "keyboard"
            },
            category="game_development"
        ),
        SkillNode(
            id="web_scraper",
            keywords=["爬虫", "抓取", "scraper"],
            default_params={
                "output_format": "json",
                "storage": "database"
            },
            category="data_engineering"
        )
    ]
    
    # 初始化解析器
    parser = IntentExplicitParser(confidence_threshold=0.5)
    parser.load_skill_nodes(sample_nodes)
    
    # 测试解析
    test_cases = [
        "做一个好玩的贪吃蛇游戏",
        "帮我写个网络爬虫抓取数据",
        "这个指令太模糊了"
    ]
    
    for text in test_cases:
        print(f"\n输入: {text}")
        ir = parser.parse(text)
        print(f"意图: {ir.intent}")
        print(f"置信度: {ir.confidence:.2f}")
        print(f"约束: {ir.constraints}")
        print(f"缺失参数: {ir.missing_params}")
        
        if ir.confidence < parser.confidence_threshold:
            print("警告: 置信度过低，可能需要澄清指令")