"""
模块名称: dynamic_adaptive_tokenization
描述: 实现一个基于上下文感知的动态自适应分词系统。
      该系统模拟编译器词法分析中的‘前瞻’机制，根据输入文本的统计特征
      (如代码混合度、熵值)动态调整分词策略。在结构化代码或高密度信息区
      采用细粒度分词以保留语义，在普通文本区采用粗粒度分词以压缩序列长度。
作者: AGI System
版本: 1.0.0
"""

import logging
import re
import math
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Token:
    """
    基础Token数据结构。
    
    Attributes:
        text (str): Token的文本内容。
        token_id (int): 模拟的Token ID。
        granularity (str): 分词粒度类型 ('fine' 或 'coarse')。
        entropy (float): 生成该Token时的局部上下文熵。
    """
    text: str
    token_id: int
    granularity: str
    entropy: float

class DynamicAdaptiveTokenizer:
    """
    动态自适应分词器。
    
    结合编译原理的词法分析思想，通过滑动窗口和前瞻缓冲区分析文本特征，
    动态在 '粗粒度' (Coarse) 和 '细粒度' (Fine) 分词模式间切换。
    
    输入格式: 
        raw_text (str): 原始输入字符串，可包含代码、自然语言等。
    输出格式:
        List[Token]: 包含元数据的Token对象列表。
    """

    def __init__(self, 
                 window_size: int = 10, 
                 entropy_threshold: float = 4.0,
                 code_pattern_threshold: float = 0.3):
        """
        初始化分词器。
        
        Args:
            window_size (int): 计算局部熵的滑动窗口大小。
            entropy_threshold (float): 切换到细粒度模式的熵阈值。
            code_pattern_threshold (float): 判定为代码上下文的字符比例阈值。
        """
        if window_size < 1:
            raise ValueError("窗口大小必须大于0")
        self.window_size = window_size
        self.entropy_threshold = entropy_threshold
        self.code_pattern_threshold = code_pattern_threshold
        
        # 模拟词表 (简化版，实际应加载大规模词表)
        # 粗粒度词表倾向于长单词或常用短语
        self._coarse_vocab = {"the": 1, "user": 2, "system": 3, "variable": 4, "function": 5}
        # 细粒度词表包含字符级或子词级单位，用于代码/未知文本
        self._fine_vocab = {chr(i): i for i in range(97, 123)} # a-z
        self._next_id = 1000
        
        logger.info("DynamicAdaptiveTokenizer 初始化完成")

    def _calculate_local_entropy(self, text_chunk: str) -> float:
        """
        辅助函数: 计算文本块的香农熵。
        熵值高通常意味着字符分布更随机（如代码、密文），需要更精细的分词。
        
        Args:
            text_chunk (str): 文本片段。
            
        Returns:
            float: 计算出的熵值。
        """
        if not text_chunk:
            return 0.0
        
        freq = {}
        for char in text_chunk:
            freq[char] = freq.get(char, 0) + 1
            
        entropy = 0.0
        length = len(text_chunk)
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
            
        return entropy

    def _detect_code_patterns(self, text_chunk: str) -> bool:
        """
        辅助函数: 检测是否包含代码特征（简化的启发式规则）。
        模拟编译器的词法分析前瞻。
        
        Args:
            text_chunk (str): 待检测文本。
            
        Returns:
            bool: 如果检测到代码特征返回True。
        """
        # 简单规则：括号、运算符、驼峰命名、下划线
        code_indicators = r"[{}();=<>!&_]"
        matches = re.findall(code_indicators, text_chunk)
        
        if len(matches) / max(1, len(text_chunk)) > 0.15:
            return True
        return False

    def _get_fine_grained_tokens(self, text: str) -> List[Token]:
        """
        核心函数: 细粒度分词逻辑 (字符级/子词级)。
        适用于高熵区域或代码区域。
        """
        tokens = []
        for char in text:
            if char in self._fine_vocab:
                token_id = self._fine_vocab[char]
            else:
                # 动态分配ID (模拟OOV处理)
                self._fine_vocab[char] = self._next_id
                token_id = self._next_id
                self._next_id += 1
            
            tokens.append(Token(
                text=char, 
                token_id=token_id, 
                granularity='fine',
                entropy=self._calculate_local_entropy(char) # 单字符熵较低，主要是标记作用
            ))
        return tokens

    def _get_coarse_grained_tokens(self, text: str) -> List[Token]:
        """
        核心函数: 粗粒度分词逻辑 (单词/短语级)。
        适用于低熵的自然语言区域。
        """
        # 简单的空格分词模拟
        words = text.split(' ')
        tokens = []
        
        for word in words:
            if not word: continue
            
            # 查表或模拟
            if word in self._coarse_vocab:
                token_id = self._coarse_vocab[word]
            else:
                # 如果词表中没有，回退到细粒度处理该单词，或者分配新ID
                # 这里演示为了保持粗粒度连贯性，我们分配新ID，但在实际LLM中会使用BPE等
                self._coarse_vocab[word] = self._next_id
                token_id = self._next_id
                self._next_id += 1
            
            tokens.append(Token(
                text=word,
                token_id=token_id,
                granularity='coarse',
                entropy=self._calculate_local_entropy(word)
            ))
        return tokens

    def tokenize(self, raw_text: str) -> List[Token]:
        """
        主入口: 执行动态自适应分词。
        
        算法流程:
        1. 滑动窗口遍历文本。
        2. 计算窗口内的熵和代码特征密度。
        3. 根据指标决定当前窗口的分词策略 (前瞻决策)。
        4. 执行分词并合并结果。
        
        Args:
            raw_text (str): 输入文本。
            
        Returns:
            List[Token]: 分词结果列表。
            
        Raises:
            ValueError: 如果输入不是字符串。
        """
        if not isinstance(raw_text, str):
            logger.error("输入类型错误: 必须是字符串")
            raise ValueError("Input must be a string")
        
        if not raw_text:
            return []

        logger.info(f"开始处理文本，长度: {len(raw_text)}")
        
        all_tokens = []
        buffer = ""
        current_mode = "coarse" # 默认粗粒度
        n = len(raw_text)
        
        # 模拟前瞻指针
        i = 0
        while i < n:
            # 获取前瞻窗口
            lookahead_window = raw_text[i : i + self.window_size]
            
            # 计算上下文特征
            local_entropy = self._calculate_local_entropy(lookahead_window)
            is_code = self._detect_code_patterns(lookahead_window)
            
            # 动态决策逻辑
            desired_mode = "coarse"
            if local_entropy > self.entropy_threshold or is_code:
                desired_mode = "fine"
            
            # 如果模式发生变化，处理缓冲区并切换
            if desired_mode != current_mode:
                logger.debug(f"模式切换 @ index {i}: {current_mode} -> {desired_mode} (Entropy: {local_entropy:.2f})")
                
                # 处理之前缓冲区里的内容
                if buffer:
                    if current_mode == "coarse":
                        all_tokens.extend(self._get_coarse_grained_tokens(buffer))
                    else:
                        all_tokens.extend(self._get_fine_grained_tokens(buffer))
                    buffer = ""
                
                current_mode = desired_mode
            
            # 将当前字符加入缓冲区
            # 注意：为了简化演示，我们按窗口步长或字符处理
            # 这里采用逐字符累积，实际系统中可能按块处理
            buffer += raw_text[i]
            i += 1
            
        # 处理剩余缓冲区
        if buffer:
            if current_mode == "coarse":
                all_tokens.extend(self._get_coarse_grained_tokens(buffer))
            else:
                all_tokens.extend(self._get_fine_grained_tokens(buffer))
                
        logger.info(f"分词完成，生成 {len(all_tokens)} 个Tokens")
        return all_tokens

# 使用示例
if __name__ == "__main__":
    # 模拟AGI系统中的混合文本场景
    sample_text = (
        "The user requested to execute the following SQL query: "
        "SELECT * FROM users WHERE id = 1; "
        "This operation requires high security clearance."
    )
    
    try:
        tokenizer = DynamicAdaptiveTokenizer(window_size=8, entropy_threshold=3.5)
        result_tokens = tokenizer.tokenize(sample_text)
        
        print(f"{'ID':<6} | {'Granularity':<10} | {'Text':<10} | {'Entropy':<5}")
        print("-" * 40)
        for token in result_tokens[:15]: # 仅展示前15个
            print(f"{token.token_id:<6} | {token.granularity:<10} | {repr(token.text):<10} | {token.entropy:.2f}")
            
    except Exception as e:
        logger.error(f"运行时发生错误: {e}")