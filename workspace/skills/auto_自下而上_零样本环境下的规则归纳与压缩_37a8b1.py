"""
名称: auto_自下而上_零样本环境下的规则归纳与压缩_37a8b1
描述: 【自下而上】零样本环境下的规则归纳与压缩。
     该模块实现了一个能够从少量样本中自动推导字符串变换规则的引擎。
     它模拟了AGI系统中的'归纳编程'能力，通过观察输入输出对，
     自下而上地构建可执行的变换函数，而非依赖预定义的模板。
领域: inductive_programming
"""

import logging
import re
from typing import List, Tuple, Dict, Optional, Callable, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class TransformationRule:
    """
    存储归纳出的变换规则。
    
    Attributes:
        pattern (str): 用于匹配输入的正则表达式模式。
        replacement (str): 用于生成输出的替换模式。
        confidence (float): 规则的可信度 (0.0 - 1.0)。
        source (str): 规则的来源描述（如 'regex_induction'）。
    """
    pattern: str
    replacement: str
    confidence: float
    source: str = "regex_induction"

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

# --- 辅助函数 ---

def _validate_samples(samples: List[Tuple[str, str]]) -> bool:
    """
    辅助函数：验证输入样本数据的合法性。
    
    Args:
        samples (List[Tuple[str, str]]): 输入输出字符串对的列表。
        
    Returns:
        bool: 如果数据有效返回 True，否则抛出 ValueError。
        
    Raises:
        ValueError: 如果样本为空或格式不正确。
    """
    if not samples:
        logger.error("Sample list is empty.")
        raise ValueError("Input samples cannot be empty.")
    
    for i, (inp, out) in enumerate(samples):
        if not isinstance(inp, str) or not isinstance(out, str):
            logger.error(f"Invalid type at index {i}: Expected Tuple[str, str].")
            raise ValueError(f"Sample at index {i} must be a tuple of strings.")
            
    logger.info(f"Validated {len(samples)} samples successfully.")
    return True

def _calculate_similarity(s1: str, s2: str) -> float:
    """
    辅助函数：计算两个字符串的简单结构相似度（基于Levenshtein距离的近似）。
    这里使用简单的序列匹配器逻辑来评估规则假设的拟合程度。
    
    Args:
        s1 (str): 字符串1
        s2 (str): 字符串2
        
    Returns:
        float: 相似度得分 (0.0 - 1.0)。
    """
    if s1 == s2: return 1.0
    if not s1 or not s2: return 0.0
    
    # 简化的Jaccard相似度或包含关系检查用于快速过滤
    # 这里我们使用集合重叠度作为一个简单的启发式指标
    set1, set2 = set(s1), set(s2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

# --- 核心逻辑函数 ---

def analyze_differences(samples: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    核心函数1：自下而上分析样本对，提取差异特征。
    
    该函数尝试识别输入到输出的变换是'恒等变换'、'前缀添加'、'后缀添加'
    还是'模式替换'。这是构建通用规则的基础。
    
    Args:
        samples (List[Tuple[str, str]]): 经过验证的样本列表。
        
    Returns:
        Dict[str, Any]: 包含提取特征和假设规则的字典。
        
    Example:
        >>> data = [("abc", "XabcY"), ("de", "XdeY")]
        >>> features = analyze_differences(data)
        >>> print(features['hypothesis_type'])
        'wrap_around'
    """
    logger.info("Starting bottom-up difference analysis...")
    hypotheses = []
    
    # 提取所有样本的共同特征
    for inp, out in samples:
        # 假设1：完全匹配
        if inp == out:
            hypotheses.append("identity")
            continue
            
        # 假设2：前缀/后缀包裹 (Wrap around)
        # 检查输入是否是输出的子串
        if inp in out:
            try:
                idx = out.index(inp)
                prefix = out[:idx]
                suffix = out[idx + len(inp):]
                
                # 验证是否所有样本都共享相同的前后缀
                # 注意：这里简化处理，仅记录当前样本的特征，实际生产中需聚合验证
                hypotheses.append({
                    "type": "wrap_around",
                    "prefix": prefix,
                    "suffix": suffix,
                    "input": inp
                })
            except ValueError:
                pass

    # 简单的聚合逻辑：如果所有样本都指示相同的包裹类型
    # 这里为了演示，我们只检查第一个非平凡假设
    # 在真实的AGI系统中，这里需要一个概率图模型来投票
    
    # 检测包裹一致性
    wrap_hypotheses = [h for h in hypotheses if isinstance(h, dict) and h['type'] == 'wrap_around']
    if wrap_hypotheses and len(wrap_hypotheses) == len(samples):
        # 检查前缀后缀是否一致
        prefixes = {h['prefix'] for h in wrap_hypotheses}
        suffixes = {h['suffix'] for h in wrap_hypotheses}
        
        if len(prefixes) == 1 and len(suffixes) == 1:
            p = prefixes.pop()
            s = suffixes.pop()
            logger.info(f"Strong pattern found: Prefix='{p}', Suffix='{s}'")
            return {
                "hypothesis_type": "wrap_around",
                "prefix": p,
                "suffix": s,
                "confidence": 0.95
            }

    # 默认返回：未找到明确规则
    logger.warning("No clear deterministic pattern found in samples.")
    return {"hypothesis_type": "unknown", "confidence": 0.0}

def compile_rule_node(analysis_result: Dict[str, Any]) -> Optional[Callable[[str], str]]:
    """
    核心函数2：将分析结果固化为一个可执行的Python函数（真实节点）。
    
    这个函数体现了"代码生成"的能力，它不仅仅是返回一个字符串描述，
    而是动态构建并返回一个能够执行变换的逻辑闭包。
    
    Args:
        analysis_result (Dict[str, Any]): analyze_differences 的输出结果。
        
    Returns:
        Optional[Callable[[str], str]]: 一个接受字符串输入并返回变换结果的函数，
                                        如果无法生成则返回 None。
                                        
    Example:
        >>> rule_func = compile_rule_node({"hypothesis_type": "wrap_around", "prefix": "A", "suffix": "Z"})
        >>> print(rule_func("test"))
        "AtestZ"
    """
    h_type = analysis_result.get("hypothesis_type")
    confidence = analysis_result.get("confidence", 0.0)
    
    if confidence < 0.8:
        logger.warning(f"Confidence too low ({confidence}) to compile solid node.")
        return None

    logger.info(f"Compiling executable node for type: {h_type}")

    if h_type == "wrap_around":
        prefix = analysis_result.get("prefix", "")
        suffix = analysis_result.get("suffix", "")
        
        # 定义并返回一个闭包
        def dynamic_transform(text: str) -> str:
            """
            自动生成的变换函数：包裹模式。
            """
            # 边界检查：如果输入已经被包裹，是否需要重复包裹？
            # 这里假设是无条件变换
            return f"{prefix}{text}{suffix}"
            
        # 将元数据附加到函数上，模拟真实节点的自描述能力
        dynamic_transform.__doc__ = f"Auto-generated wrapper: prefix='{prefix}', suffix='{suffix}'"
        dynamic_transform.metadata = analysis_result # type: ignore
        return dynamic_transform

    elif h_type == "identity":
        def identity_transform(text: str) -> str:
            return text
        return identity_transform
        
    else:
        logger.error("Unknown hypothesis type, cannot compile node.")
        return None

# --- 主执行类 ---

class RuleInductor:
    """
    规则归纳器：封装从观察到生成的完整流程。
    """
    
    def __init__(self, samples: List[Tuple[str, str]]):
        """
        初始化归纳器。
        
        Args:
            samples (List[Tuple[str, str]]): 观测样本。
        """
        _validate_samples(samples)
        self.samples = samples
        self.generated_node: Optional[Callable] = None
        self.analysis: Optional[Dict] = None

    def induce(self) -> bool:
        """
        执行归纳过程。
        
        Returns:
            bool: 是否成功生成规则。
        """
        try:
            # 1. 分析
            self.analysis = analyze_differences(self.samples)
            # 2. 压缩与生成
            self.generated_node = compile_rule_node(self.analysis)
            
            return self.generated_node is not None
        except Exception as e:
            logger.exception(f"Induction failed: {e}")
            return False

    def predict(self, new_input: str) -> str:
        """
        使用生成的规则节点进行预测。
        
        Args:
            new_input (str): 新的输入字符串。
            
        Returns:
            str: 预测结果。
            
        Raises:
            RuntimeError: 如果规则尚未生成。
        """
        if not self.generated_node:
            raise RuntimeError("Rule node has not been generated yet. Call induce() first.")
        
        logger.info(f"Predicting output for: {new_input}")
        return self.generated_node(new_input)

# --- 模块演示与测试 ---

if __name__ == "__main__":
    # 场景设定：观察到一个未知的字符串变换游戏
    # 输入 -> 输出
    # "apple" -> "[apple]"
    # "banana" -> "[banana]"
    # "1024" -> "[1024]"
    
    game_samples = [
        ("apple", "[apple]"),
        ("banana", "[banana]"),
        ("1024", "[1024]"),
        ("test_data", "[test_data]")
    ]

    print(f"{'='*10} AGI Rule Induction System {'='*10}")
    print(f"Observing {len(game_samples)} samples...")
    
    # 初始化归纳器
    inductor = RuleInductor(game_samples)
    
    # 执行归纳
    success = inductor.induce()
    
    if success:
        print("\n[SUCCESS] Rule Node Compiled.")
        print(f"Rule Metadata: {inductor.analysis}")
        
        # 测试零样本泛化
        test_case = "AGI_Future"
        predicted = inductor.predict(test_case)
        print(f"\nZero-Shot Test:")
        print(f"Input:    {test_case}")
        print(f"Predicted: {predicted}")
        
        # 验证结果
        assert predicted == "[AGI_Future]", "Induction logic error"
        print("\nAssertion passed. The system has correctly learned the rule.")
    else:
        print("\n[FAILED] Could not induce a confident rule from the given samples.")