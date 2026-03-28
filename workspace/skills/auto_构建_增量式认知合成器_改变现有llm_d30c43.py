"""
增量式认知合成器

该模块实现了增量式认知合成器，改变了传统LLM的“一次性生成”黑盒模式。
通过引入语法制导的增量生成机制，系统在生成长文本或代码时，每生成一个
结构块（如函数、段落），立即进行局部语法/逻辑校验。若发现偏差，立即
回溯并尝试修复，模拟编译器的错误恢复机制，确保最终输出的结构完整性。

作者: AGI System Core Team
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("IncrementalCognitiveSynthesizer")


class BlockType(Enum):
    """定义生成的结构块类型。"""

    CODE_FUNCTION = auto()
    CODE_CLASS = auto()
    TEXT_PARAGRAPH = auto()
    UNKNOWN = auto()


@dataclass
class SyntaxBlock:
    """表示一个生成的语法结构块。"""

    id: int
    content: str
    block_type: BlockType
    is_valid: bool = False
    error_msg: str = ""


@dataclass
class SynthesisConfig:
    """合成器的配置参数。"""

    max_retries_per_block: int = 3
    max_total_tokens: int = 4096
    supported_languages: List[str] = field(default_factory=lambda: ["python", "text"])


class IncrementalCognitiveSynthesizer:
    """
    增量式认知合成器主类。

    该类封装了增量生成、校验和回溯的核心逻辑。它不直接调用LLM API，
    而是依赖于外部提供的生成器函数，从而保持模块的通用性。

    属性:
        config (SynthesisConfig): 合成器配置。
        blocks (List[SyntaxBlock]): 已成功生成的语法块列表。
        _current_buffer (str): 当前正在处理的临时缓冲区。
    """

    def __init__(self, config: Optional[SynthesisConfig] = None) -> None:
        """初始化合成器。"""
        self.config = config if config else SynthesisConfig()
        self.blocks: List[SyntaxBlock] = []
        self._current_buffer: str = ""
        logger.info("IncrementalCognitiveSynthesizer initialized.")

    def _validate_python_syntax(self, code_snippet: str) -> Tuple[bool, str]:
        """
        辅助函数：校验Python代码片段的语法。

        使用compile内置函数进行静态语法检查，不执行代码。

        Args:
            code_snippet (str): 代码片段字符串。

        Returns:
            Tuple[bool, str]: (是否通过校验, 错误信息)。
        """
        try:
            compile(code_snippet, "<string>", "exec")
            return True, "Syntax OK"
        except SyntaxError as e:
            error_msg = f"SyntaxError: {e.msg} (line {e.lineno})"
            logger.warning(f"Syntax validation failed: {error_msg}")
            return False, error_msg
        except Exception as e:
            return False, str(e)

    def _validate_text_structure(self, text_snippet: str) -> Tuple[bool, str]:
        """
        辅助函数：校验文本段落的逻辑完整性（简单规则示例）。

        规则：
        1. 必须以大写字母或数字开头。
        2. 必须以标点符号结束。

        Args:
            text_snippet (str): 文本片段。

        Returns:
            Tuple[bool, str]: (是否通过校验, 错误信息)。
        """
        stripped = text_snippet.strip()
        if not stripped:
            return False, "Empty block"

        # 规则1: 开头检查
        if not re.match(r"^[A-Z0-9]", stripped):
            return False, "Paragraph must start with Capital letter or Number"

        # 规则2: 结尾检查
        if not re.match(r".*[.!?。！？]$", stripped):
            return False, "Paragraph must end with punctuation"

        return True, "Structure OK"

    def _validate_block(self, block: SyntaxBlock) -> bool:
        """
        核心函数：根据块类型调度相应的校验器。

        Args:
            block (SyntaxBlock): 待校验的语法块。

        Returns:
            bool: 校验是否通过。
        """
        if block.block_type == BlockType.CODE_FUNCTION:
            is_ok, msg = self._validate_python_syntax(block.content)
        elif block.block_type == BlockType.TEXT_PARAGRAPH:
            is_ok, msg = self._validate_text_structure(block.content)
        else:
            # 对于未知类型，默认通过或实现特定逻辑
            is_ok, msg = True, "Skipped validation"

        block.is_valid = is_ok
        block.error_msg = msg
        return is_ok

    def synthesize(
        self,
        generator_func: Callable[[str, Optional[str]], str],
        prompt: str,
        mode: str = "code",
    ) -> str:
        """
        核心函数：执行增量式生成与校验循环。

        模拟增量生成过程：调用外部生成器 -> 获取块 -> 校验 -> 
        如果失败则回溯请求重新生成该块 -> 组装最终结果。

        Args:
            generator_func (Callable): 一个模拟LLM的回调函数。
                                       参数为(上下文, 错误提示)，返回生成的字符串。
            prompt (str): 原始用户提示词。
            mode (str): 生成模式 ('code' 或 'text')。

        Returns:
            str: 最终合成且通过校验的完整内容。

        Raises:
            ValueError: 如果达到最大重试次数仍未生成有效内容。
        """
        logger.info(f"Starting synthesis for mode: {mode}")
        self.blocks = []
        context = prompt
        block_id = 0

        # 模拟流式生成过程，这里假设generator_func每次返回一个“块”
        # 在真实场景中，这可能是一个while循环直到收到EOS标记
        # 这里为了演示逻辑，我们假设模拟器会生成3个块
        simulated_steps = 3
        
        for _ in range(simulated_steps):
            block_id += 1
            retry_count = 0
            success = False
            
            # 当前块的上下文包含了之前所有成功的内容
            current_full_context = "\n".join([b.content for b in self.blocks])
            
            while retry_count < self.config.max_retries_per_block:
                # 请求生成器生成下一个块
                # 如果是重试，传入错误信息作为提示（模拟Compiler Error Recovery）
                error_hint = None
                if retry_count > 0:
                    error_hint = f"Previous error: {last_error_msg}. Please fix."
                
                raw_chunk = generator_func(current_full_context, error_hint)
                
                # 确定块类型
                b_type = (
                    BlockType.CODE_FUNCTION
                    if mode == "code"
                    else BlockType.TEXT_PARAGRAPH
                )
                
                current_block = SyntaxBlock(
                    id=block_id, content=raw_chunk, block_type=b_type
                )

                # 校验
                if self._validate_block(current_block):
                    self.blocks.append(current_block)
                    success = True
                    logger.info(f"Block {block_id} validated successfully.")
                    break
                else:
                    retry_count += 1
                    last_error_msg = current_block.error_msg
                    logger.warning(
                        f"Block {block_id} validation failed. "
                        f"Retry {retry_count}/{self.config.max_retries_per_block}"
                    )

            if not success:
                logger.error(
                    f"Failed to generate valid block {block_id} "
                    f"after {self.config.max_retries_per_block} retries."
                )
                # 实际系统中可能选择跳过或抛出异常
                raise ValueError(f"Generation failed at block {block_id}: {last_error_msg}")

        # 组装最终结果
        final_output = "\n\n".join([b.content for b in self.blocks])
        logger.info("Synthesis completed successfully.")
        return final_output


# ============================================================
# 使用示例 (模拟外部LLM行为)
# ============================================================

def mock_llm_generator(context: str, error_hint: Optional[str]) -> str:
    """
    模拟一个LLM生成函数，演示错误恢复机制。
    
    Args:
        context: 已有的上下文。
        error_hint: 如果这是重试，包含错误提示。
    """
    if "python" in context.lower() or "code" in context.lower():
        # 模拟代码生成
        if error_hint:
            # 修正错误：补全缺失的冒号或缩进
            return "def calculate_sum(a, b):\n    return a + b"
        else:
            # 第一次生成一个带有语法错误的代码块（故意为之）
            # 缺少冒号
            return "def broken_func(a, b)\n    return a - b"
    else:
        # 模拟文本生成
        if error_hint:
            # 修正错误：添加标点
            return "This is a corrected sentence with proper structure."
        else:
            # 第一次生成缺少标点
            return "This is a sentence without ending"

if __name__ == "__main__":
    # 初始化合成器
    config = SynthesisConfig(max_retries_per_block=2)
    synthesizer = IncrementalCognitiveSynthesizer(config=config)

    # 示例 1: Python 代码生成 (将自动触发语法错误恢复)
    try:
        print("--- Starting Code Synthesis ---")
        # 注意：mock_llm_generator 会先生成错误代码，合成器检测到错误后，
        # 再次调用 generator_func 并传入 error_hint，从而获得正确代码。
        result_code = synthesizer.synthesize(
            generator_func=mock_llm_generator, 
            prompt="Write a Python function", 
            mode="code"
        )
        print("\nFinal Generated Code:\n", result_code)
    except ValueError as e:
        print(f"Synthesis Error: {e}")

    # 示例 2: 文本生成 (将自动触发结构校验恢复)
    try:
        print("\n--- Starting Text Synthesis ---")
        result_text = synthesizer.synthesize(
            generator_func=mock_llm_generator, 
            prompt="Write a paragraph", 
            mode="text"
        )
        print("\nFinal Generated Text:\n", result_text)
    except ValueError as e:
        print(f"Synthesis Error: {e}")