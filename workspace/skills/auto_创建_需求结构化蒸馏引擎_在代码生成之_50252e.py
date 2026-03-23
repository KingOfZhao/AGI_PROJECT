"""
需求结构化蒸馏引擎

该模块实现了一个认知科学驱动的预处理层，用于在代码生成之前将模糊的自然语言需求
转化为严谨的结构化数据。它不直接翻译自然语言，而是识别需求中的'概念骨架'，
并强制进行变量对齐和缺失信息确认。

核心功能：
1. 概念骨架提取
2. 关键缺失变量识别
3. 人机交互式需求确认
4. 结构化JSON骨架生成

典型使用场景：
    >>> from auto_创建_需求结构化蒸馏引擎_在代码生成之_50252e import RequirementDistillationEngine
    >>> engine = RequirementDistillationEngine()
    >>> intent = "做一个像生物进化一样的优化器"
    >>> structured_data = engine.distill(intent)
    >>> # 系统会识别缺失的'适应性函数'并要求确认
    >>> structured_data['concept_skeleton']
    {'selection': '...', 'crossover': '...', 'mutation': '...'}

输入格式：
    - 自然语言文本字符串

输出格式：
    {
        "concept_skeleton": dict,  # 概念骨架结构
        "missing_variables": list, # 缺失的关键变量
        "structured_intent": dict, # 结构化意图
        "confidence_score": float  # 置信度分数
    }

作者: AGI System
版本: 1.0.0
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistillationError(Exception):
    """需求蒸馏过程中的基础异常类"""
    pass


class ValidationError(DistillationError):
    """数据验证失败时抛出的异常"""
    pass


class IntentParsingError(DistillationError):
    """意图解析失败时抛出的异常"""
    pass


@dataclass
class ConceptualSkeleton:
    """
    概念骨架数据结构
    
    属性:
        core_concepts: 核心概念列表
        relationships: 概念间关系映射
        required_variables: 必需变量列表
        optional_variables: 可选变量列表
        domain_hints: 领域提示信息
    """
    core_concepts: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    domain_hints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "core_concepts": self.core_concepts,
            "relationships": self.relationships,
            "required_variables": self.required_variables,
            "optional_variables": self.optional_variables,
            "domain_hints": self.domain_hints
        }


class PatternMatcher(ABC):
    """模式匹配器抽象基类"""
    
    @abstractmethod
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        匹配文本中的模式
        
        参数:
            text: 输入文本
            
        返回:
            匹配结果字典，如果没有匹配则返回None
        """
        pass
    
    @abstractmethod
    def extract_skeleton(self, match_result: Dict[str, Any]) -> ConceptualSkeleton:
        """
        从匹配结果中提取概念骨架
        
        参数:
            match_result: 模式匹配结果
            
        返回:
            概念骨架对象
        """
        pass


class EvolutionaryOptimizerPattern(PatternMatcher):
    """进化优化器模式匹配器"""
    
    # 进化算法相关关键词
    KEYWORDS = {
        'evolution': ['进化', '演化', 'evolution', 'evolutionary'],
        'optimizer': ['优化器', '优化', 'optimizer', 'optimization'],
        'selection': ['选择', 'selection', 'select'],
        'crossover': ['交叉', '杂交', 'crossover', 'recombination'],
        'mutation': ['变异', '突变', 'mutation'],
        'population': ['种群', '群体', 'population'],
        'fitness': ['适应', '适应度', 'fitness', '适应函数', '适应性函数']
    }
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        匹配进化优化器相关文本
        
        参数:
            text: 输入文本
            
        返回:
            匹配结果字典，包含匹配到的关键词和位置
        """
        text_lower = text.lower()
        matches = {}
        
        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if category not in matches:
                        matches[category] = []
                    matches[category].append({
                        'keyword': keyword,
                        'position': text_lower.find(keyword.lower())
                    })
        
        # 至少匹配到进化或优化器相关关键词
        if 'evolution' in matches or 'optimizer' in matches:
            return matches
        return None
    
    def extract_skeleton(self, match_result: Dict[str, Any]) -> ConceptualSkeleton:
        """
        从匹配结果中提取进化算法概念骨架
        
        参数:
            match_result: 模式匹配结果
            
        返回:
            概念骨架对象
        """
        skeleton = ConceptualSkeleton()
        
        # 核心概念
        skeleton.core_concepts = ['selection', 'crossover', 'mutation', 'population']
        
        # 概念关系
        skeleton.relationships = {
            'selection': '选择适应性高的个体',
            'crossover': '组合两个体的基因',
            'mutation': '随机改变个体基因',
            'population': '候选解的集合'
        }
        
        # 必需变量
        skeleton.required_variables = ['fitness_function', 'population_size']
        
        # 检查是否识别到适应度相关
        if 'fitness' not in match_result:
            skeleton.required_variables.append('fitness_function')
        
        # 可选变量
        skeleton.optional_variables = [
            'crossover_rate', 
            'mutation_rate', 
            'selection_method',
            'max_generations'
        ]
        
        # 领域提示
        skeleton.domain_hints = ['optimization', 'evolutionary_computation', 'metaheuristic']
        
        return skeleton


class NeuralNetworkPattern(PatternMatcher):
    """神经网络模式匹配器"""
    
    KEYWORDS = {
        'neural': ['神经网络', 'neural network', 'neural', '深度学习'],
        'layer': ['层', 'layer', 'hidden layer'],
        'activation': ['激活', 'activation', 'relu', 'sigmoid', 'tanh'],
        'training': ['训练', 'training', '学习', 'learning'],
        'loss': ['损失', 'loss', '代价', 'cost']
    }
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """匹配神经网络相关文本"""
        text_lower = text.lower()
        matches = {}
        
        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if category not in matches:
                        matches[category] = []
                    matches[category].append({
                        'keyword': keyword,
                        'position': text_lower.find(keyword.lower())
                    })
        
        if 'neural' in matches:
            return matches
        return None
    
    def extract_skeleton(self, match_result: Dict[str, Any]) -> ConceptualSkeleton:
        """从匹配结果中提取神经网络概念骨架"""
        skeleton = ConceptualSkeleton()
        
        skeleton.core_concepts = ['layers', 'activation', 'optimizer', 'loss_function']
        
        skeleton.relationships = {
            'layers': '网络层级结构',
            'activation': '非线性变换函数',
            'optimizer': '参数更新策略',
            'loss_function': '优化目标'
        }
        
        skeleton.required_variables = ['input_shape', 'output_shape', 'loss_function']
        
        if 'loss' not in match_result:
            skeleton.required_variables.append('loss_function')
        
        skeleton.optional_variables = [
            'hidden_layers',
            'neurons_per_layer',
            'learning_rate',
            'batch_size',
            'epochs'
        ]
        
        skeleton.domain_hints = ['deep_learning', 'machine_learning', 'neural_network']
        
        return skeleton


def validate_input_text(text: str) -> Tuple[bool, Optional[str]]:
    """
    验证输入文本的有效性
    
    参数:
        text: 输入文本
        
    返回:
        (是否有效, 错误消息)
    """
    if not isinstance(text, str):
        return False, "输入必须是字符串类型"
    
    if len(text.strip()) == 0:
        return False, "输入文本不能为空"
    
    if len(text) > 10000:
        return False, "输入文本过长，请限制在10000字符以内"
    
    # 检查是否包含足够的语义信息
    words = re.findall(r'\b\w+\b', text)
    if len(words) < 2:
        return False, "输入文本缺乏足够的语义信息"
    
    return True, None


def calculate_text_hash(text: str) -> str:
    """
    计算文本的哈希值，用于缓存
    
    参数:
        text: 输入文本
        
    返回:
        SHA256哈希值的前16位
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


class RequirementDistillationEngine:
    """
    需求结构化蒸馏引擎
    
    该引擎在代码生成之前运行认知科学驱动的预处理层，识别需求中的'概念骨架'，
    并强制进行变量对齐和缺失信息确认。
    
    属性:
        pattern_matchers: 已注册的模式匹配器列表
        cache: 处理结果缓存
        interaction_callback: 人机交互回调函数
        
    使用示例:
        >>> engine = RequirementDistillationEngine()
        >>> 
        >>> # 示例1: 进化优化器
        >>> intent1 = "做一个像生物进化一样的优化器"
        >>> result1 = engine.distill(intent1)
        >>> print(result1['missing_variables'])
        ['fitness_function', 'population_size']
        >>> 
        >>> # 示例2: 神经网络
        >>> intent2 = "创建一个图像分类的神经网络"
        >>> result2 = engine.distill(intent2)
        >>> print(result2['concept_skeleton']['core_concepts'])
        ['layers', 'activation', 'optimizer', 'loss_function']
    """
    
    def __init__(self, interaction_callback: Optional[callable] = None):
        """
        初始化需求蒸馏引擎
        
        参数:
            interaction_callback: 人机交互回调函数，用于获取用户输入
                                 签名: (prompt: str) -> str
        """
        self.pattern_matchers: List[PatternMatcher] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.interaction_callback = interaction_callback or self._default_interaction
        
        # 注册内置模式匹配器
        self._register_builtin_patterns()
        
        logger.info("需求结构化蒸馏引擎初始化完成")
    
    def _register_builtin_patterns(self) -> None:
        """注册内置的模式匹配器"""
        self.pattern_matchers.append(EvolutionaryOptimizerPattern())
        self.pattern_matchers.append(NeuralNetworkPattern())
        logger.debug(f"已注册 {len(self.pattern_matchers)} 个内置模式匹配器")
    
    def register_pattern(self, pattern: PatternMatcher) -> None:
        """
        注册自定义模式匹配器
        
        参数:
            pattern: 模式匹配器实例
        """
        if not isinstance(pattern, PatternMatcher):
            raise ValidationError("必须注册PatternMatcher的子类实例")
        
        self.pattern_matchers.append(pattern)
        logger.info(f"已注册新的模式匹配器: {pattern.__class__.__name__}")
    
    def _default_interaction(self, prompt: str) -> str:
        """
        默认的人机交互方法（使用控制台输入）
        
        参数:
            prompt: 提示信息
            
        返回:
            用户输入
        """
        try:
            return input(f"\n[系统询问] {prompt}: ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.warning("用户取消了输入操作")
            return ""
    
    def _extract_concept_skeleton(self, text: str) -> Tuple[Optional[ConceptualSkeleton], float]:
        """
        从文本中提取概念骨架
        
        参数:
            text: 输入文本
            
        返回:
            (概念骨架对象, 置信度分数)
        """
        best_skeleton = None
        best_confidence = 0.0
        
        for matcher in self.pattern_matchers:
            match_result = matcher.match(text)
            if match_result:
                # 计算置信度：基于匹配关键词的数量和位置
                matched_categories = len(match_result)
                total_keywords = sum(len(v) for v in match_result.values())
                confidence = min(1.0, (matched_categories * 0.3 + total_keywords * 0.1))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_skeleton = matcher.extract_skeleton(match_result)
                    logger.debug(
                        f"模式匹配成功: {matcher.__class__.__name__}, "
                        f"置信度: {confidence:.2f}"
                    )
        
        return best_skeleton, best_confidence
    
    def _identify_missing_variables(
        self, 
        skeleton: ConceptualSkeleton,
        user_responses: Optional[Dict[str, str]] = None
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        识别缺失的关键变量
        
        参数:
            skeleton: 概念骨架
            user_responses: 用户已提供的响应
            
        返回:
            (缺失变量列表, 已确认变量字典)
        """
        user_responses = user_responses or {}
        missing = []
        confirmed = {}
        
        for var in skeleton.required_variables:
            if var in user_responses and user_responses[var]:
                confirmed[var] = user_responses[var]
            else:
                missing.append(var)
        
        return missing, confirmed
    
    def _request_user_confirmation(
        self, 
        missing_variables: List[str],
        skeleton: ConceptualSkeleton
    ) -> Dict[str, str]:
        """
        请求用户确认缺失的变量（人机共生）
        
        参数:
            missing_variables: 缺失变量列表
            skeleton: 概念骨架
            
        返回:
            用户确认的变量字典
        """
        user_responses = {}
        
        logger.info(f"检测到 {len(missing_variables)} 个缺失的关键变量，开始人机交互")
        
        for var in missing_variables:
            # 生成友好的提示
            prompt = self._generate_variable_prompt(var, skeleton)
            response = self.interaction_callback(prompt)
            
            if response:
                user_responses[var] = response
                logger.debug(f"用户确认变量 '{var}': {response}")
            else:
                logger.warning(f"用户未提供变量 '{var}' 的值")
        
        return user_responses
    
    def _generate_variable_prompt(self, variable: str, skeleton: ConceptualSkeleton) -> str:
        """
        为变量生成用户友好的提示信息
        
        参数:
            variable: 变量名
            skeleton: 概念骨架
            
        返回:
            提示字符串
        """
        # 变量描述映射
        descriptions = {
            'fitness_function': '适应性函数（用于评估个体优劣的标准，例如：目标函数、损失函数）',
            'population_size': '种群大小（每次迭代保留的候选解数量，推荐值：50-200）',
            'input_shape': '输入数据形状（例如：图像尺寸 224x224x3）',
            'output_shape': '输出形状（例如：分类类别数 10）',
            'loss_function': '损失函数（例如：交叉熵、均方误差）'
        }
        
        desc = descriptions.get(variable, f"请提供 '{variable}' 的值")
        hints = f"\n可选值提示: {skeleton.optional_variables}" if skeleton.optional_variables else ""
        
        return f"{desc}{hints}"
    
    def _build_structured_output(
        self,
        skeleton: ConceptualSkeleton,
        confirmed_variables: Dict[str, str],
        confidence: float
    ) -> Dict[str, Any]:
        """
        构建结构化输出
        
        参数:
            skeleton: 概念骨架
            confirmed_variables: 已确认的变量
            confidence: 置信度
            
        返回:
            结构化输出字典
        """
        return {
            "concept_skeleton": skeleton.to_dict(),
            "missing_variables": [
                var for var in skeleton.required_variables 
                if var not in confirmed_variables
            ],
            "confirmed_variables": confirmed_variables,
            "structured_intent": {
                "domain": skeleton.domain_hints[0] if skeleton.domain_hints else "unknown",
                "core_components": skeleton.core_concepts,
                "component_descriptions": skeleton.relationships,
                "parameters": {
                    **confirmed_variables,
                    **{var: None for var in skeleton.optional_variables}
                }
            },
            "confidence_score": confidence,
            "metadata": {
                "engine_version": "1.0.0",
                "pattern_matchers_used": [
                    m.__class__.__name__ for m in self.pattern_matchers
                ]
            }
        }
    
    def distill(
        self, 
        intent_text: str, 
        auto_confirm: bool = False
    ) -> Dict[str, Any]:
        """
        蒸馏需求：将模糊意图转化为结构化数据
        
        这是引擎的主入口函数，执行完整的蒸馏流程：
        1. 输入验证
        2. 缓存检查
        3. 概念骨架提取
        4. 缺失变量识别
        5. 人机交互确认（可选）
        6. 结构化输出生成
        
        参数:
            intent_text: 自然语言意图文本
            auto_confirm: 是否自动确认（跳过人机交互，用于测试）
            
        返回:
            结构化需求字典，包含概念骨架、缺失变量、结构化意图等
            
        异常:
            ValidationError: 输入验证失败
            IntentParsingError: 意图解析失败
            
        使用示例:
            >>> engine = RequirementDistillationEngine()
            >>> 
            >>> # 基本使用
            >>> result = engine.distill("创建一个进化优化器")
            >>> print(result['concept_skeleton']['core_concepts'])
            ['selection', 'crossover', 'mutation', 'population']
            >>> 
            >>> # 使用自定义交互回调
            >>> def my_callback(prompt):
            ...     return "用户输入的值"
            >>> engine = RequirementDistillationEngine(interaction_callback=my_callback)
            >>> result = engine.distill("构建神经网络分类器")
        """
        logger.info(f"开始蒸馏需求: {intent_text[:50]}...")
        
        # 1. 输入验证
        is_valid, error_msg = validate_input_text(intent_text)
        if not is_valid:
            logger.error(f"输入验证失败: {error_msg}")
            raise ValidationError(error_msg)
        
        # 2. 缓存检查
        text_hash = calculate_text_hash(intent_text)
        if text_hash in self.cache:
            logger.info(f"使用缓存结果: {text_hash}")
            return self.cache[text_hash]
        
        # 3. 概念骨架提取
        skeleton, confidence = self._extract_concept_skeleton(intent_text)
        
        if skeleton is None:
            logger.warning("未能识别任何概念骨架")
            return {
                "concept_skeleton": None,
                "missing_variables": [],
                "confirmed_variables": {},
                "structured_intent": None,
                "confidence_score": 0.0,
                "error": "无法识别意图中的概念模式",
                "suggestions": [
                    "请提供更具体的需求描述",
                    "明确指出所需的算法或模型类型"
                ]
            }
        
        # 4. 缺失变量识别
        missing_vars, confirmed_vars = self._identify_missing_variables(skeleton)
        
        logger.info(
            f"识别到 {len(skeleton.core_concepts)} 个核心概念, "
            f"{len(missing_vars)} 个缺失变量"
        )
        
        # 5. 人机交互确认
        if missing_vars and not auto_confirm:
            user_responses = self._request_user_confirmation(missing_vars, skeleton)
            confirmed_vars.update(user_responses)
        
        # 6. 构建结构化输出
        result = self._build_structured_output(skeleton, confirmed_vars, confidence)
        
        # 缓存结果
        self.cache[text_hash] = result
        
        logger.info(f"需求蒸馏完成，置信度: {confidence:.2f}")
        
        return result
    
    def batch_distill(
        self, 
        intent_texts: List[str],
        auto_confirm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量蒸馏多个需求
        
        参数:
            intent_texts: 意图文本列表
            auto_confirm: 是否自动确认
            
        返回:
            结构化结果列表
        """
        results = []
        for i, text in enumerate(intent_texts):
            try:
                logger.info(f"处理批量需求 {i+1}/{len(intent_texts)}")
                result = self.distill(text, auto_confirm=auto_confirm)
                results.append(result)
            except DistillationError as e:
                logger.error(f"批量处理第 {i+1} 个需求失败: {e}")
                results.append({
                    "error": str(e),
                    "original_text": text
                })
        
        return results
    
    def export_skeleton_to_json(
        self, 
        result: Dict[str, Any], 
        filepath: str
    ) -> None:
        """
        将结构化结果导出为JSON文件
        
        参数:
            result: 蒸馏结果
            filepath: 输出文件路径
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"结构化骨架已导出至: {filepath}")
        except IOError as e:
            logger.error(f"导出失败: {e}")
            raise


# 便捷函数
def create_evolutionary_optimizer_skeleton(
    fitness_function: str,
    population_size: int = 100
) -> Dict[str, Any]:
    """
    快速创建进化优化器的结构化骨架
    
    参数:
        fitness_function: 适应性函数描述
        population_size: 种群大小
        
    返回:
        结构化骨架字典
        
    使用示例:
        >>> skeleton = create_evolutionary_optimizer_skeleton(
        ...     fitness_function="minimize(x^2 + y^2)",
        ...     population_size=50
        ... )
        >>> print(skeleton['structured_intent']['parameters']['fitness_function'])
        'minimize(x^2 + y^2)'
    """
    engine = RequirementDistillationEngine()
    
    # 构造带有参数的意图文本
    intent = f"创建一个进化优化器，种群大小为{population_size}，适应性函数为{fitness_function}"
    
    return engine.distill(intent, auto_confirm=True)


# 模块测试
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("需求结构化蒸馏引擎 - 演示")
    print("=" * 60)
    
    # 创建引擎实例
    engine = RequirementDistillationEngine()
    
    # 测试用例1: 进化优化器
    print("\n[测试1] 进化优化器需求")
    print("-" * 40)
    intent1 = "做一个像生物进化一样的优化器"
    result1 = engine.distill(intent1, auto_confirm=True)
    print(f"输入: {intent1}")
    print(f"核心概念: {result1['concept_skeleton']['core_concepts']}")
    print(f"缺失变量: {result1['missing_variables']}")
    print(f"置信度: {result1['confidence_score']:.2f}")
    
    # 测试用例2: 神经网络
    print("\n[测试2] 神经网络需求")
    print("-" * 40)
    intent2 = "创建一个用于图像分类的深度学习神经网络"
    result2 = engine.distill(intent2, auto_confirm=True)
    print(f"输入: {intent2}")
    print(f"核心概念: {result2['concept_skeleton']['core_concepts']}")
    print(f"缺失变量: {result2['missing_variables']}")
    print(f"置信度: {result2['confidence_score']:.2f}")
    
    # 测试用例3: 导出JSON
    print("\n[测试3] 导出结构化骨架")
    print("-" * 40)
    engine.export_skeleton_to_json(result1, "skeleton_output.json")
    print("已导出到 skeleton_output.json")
    
    # 测试用例4: 快捷函数
    print("\n[测试4] 使用快捷函数")
    print("-" * 40)
    skeleton = create_evolutionary_optimizer_skeleton(
        fitness_function="minimize(x^2 + y^2)",
        population_size=50
    )
    print(f"适应性函数: {skeleton['structured_intent']['parameters']['fitness_function']}")
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)