"""
意图-代码对齐的语义损失函数模块

该模块提供了一个基于嵌入模型的评估机制，用于计算自然语言意图与生成的代码片段
之间的语义距离。它不依赖于精确的字符串匹配或单元测试通过率，而是通过将两者
映射到高维语义空间，利用余弦相似度来衡量代码是否在语义上符合意图。

主要功能:
    - 计算意图与代码的语义损失 (Loss = 1 - Similarity)
    - 计算意图与代码的语义相似度
    - 输入数据的严格验证与清洗

依赖库:
    - sentence-transformers: 用于生成文本和代码的嵌入向量。
    - numpy: 用于向量运算。
    - logging: 用于日志记录。

输入格式:
    - intent (str): 自然语言描述的意图，例如 "计算列表中所有偶数的和"。
    - code (str): 生成的代码字符串，例如 "def sum_evens(lst): return sum(x for x in lst if x % 2 == 0)"。

输出格式:
    - float: 归一化的损失值 [0.0, 1.0]，其中 0.0 表示完全对齐，1.0 表示完全不相关。
"""

import logging
import numpy as np
from typing import Optional, Tuple
from sentence_transformers import SentenceTransformer

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentCodeSemanticLoss:
    """
    意图-代码对齐的语义损失计算器。

    该类利用预训练的Transformer模型将自然语言意图和代码片段映射到共享的向量空间，
    并计算它们之间的语义距离作为损失函数。这种方法解决了传统单元测试无法覆盖
    主观意图或非功能性需求的问题。

    Attributes:
        model (SentenceTransformer): 用于生成嵌入的预训练模型。
        model_name (str): 当前使用的模型名称。
    """

    def __init__(self, model_name: str = "microsoft/codebert-base"):
        """
        初始化语义损失计算器。

        Args:
            model_name (str): 使用的嵌入模型名称。默认为 'microsoft/codebert-base'，
                              该模型在代码和自然语言上进行了联合训练。
                              也可以使用 'sentence-transformers/all-MiniLM-L6-v2' 等通用模型。

        Raises:
            ImportError: 如果 sentence_transformers 库未安装。
            RuntimeError: 如果模型加载失败。
        """
        try:
            logger.info(f"正在加载嵌入模型: {model_name}...")
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info("模型加载成功。")
        except ImportError as e:
            logger.error("缺少必要的依赖库 'sentence-transformers'。请先安装: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError(f"无法加载模型 {model_name}") from e

    def _validate_input(self, text: str, field_name: str) -> str:
        """
        辅助函数：验证输入的文本数据。

        检查输入是否为字符串，是否为空或仅包含空白字符，并进行基本的清洗。

        Args:
            text (str): 待验证的文本。
            field_name (str): 字段名称，用于错误日志提示。

        Returns:
            str: 清洗后的文本（去除首尾空格）。

        Raises:
            TypeError: 如果输入不是字符串。
            ValueError: 如果输入为空或无效。
        """
        if not isinstance(text, str):
            logger.error(f"字段 '{field_name}' 必须是字符串类型，实际收到: {type(text)}")
            raise TypeError(f"{field_name} must be a string")

        stripped_text = text.strip()
        if not stripped_text:
            logger.error(f"字段 '{field_name}' 不能为空。")
            raise ValueError(f"{field_name} cannot be empty")

        return stripped_text

    def _get_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        核心辅助函数：计算文本列表的嵌入向量。

        Args:
            texts (list[str]): 包含意图或代码的字符串列表。

        Returns:
            np.ndarray: 形状为 (len(texts), embedding_dim) 的numpy数组。

        Raises:
            RuntimeError: 如果嵌入计算过程中发生错误。
        """
        try:
            # 编码文本，返回numpy数组
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings
        except Exception as e:
            logger.error(f"计算嵌入向量时发生错误: {e}")
            raise RuntimeError("Embedding computation failed") from e

    def calculate_similarity(self, intent: str, code: str) -> float:
        """
        核心函数：计算意图与代码之间的语义相似度。

        使用余弦相似度衡量两个向量在语义空间中的接近程度。
        结果范围在 [-1, 1] 之间，通常在 [0, 1] 之间。

        Args:
            intent (str): 自然语言意图描述。
            code (str): 生成的代码片段。

        Returns:
            float: 余弦相似度得分。

        Example:
            >>> calculator = IntentCodeSemanticLoss()
            >>> score = calculator.calculate_similarity("Add two numbers", "def add(a, b): return a + b")
            >>> print(f"Similarity: {score:.4f}")
        """
        # 1. 数据验证
        clean_intent = self._validate_input(intent, "intent")
        clean_code = self._validate_input(code, "code")

        # 2. 获取嵌入向量
        # 批量处理以提高效率
        embeddings = self._get_embeddings([clean_intent, clean_code])
        intent_emb, code_emb = embeddings[0], embeddings[1]

        # 3. 计算余弦相似度
        # dot(A, B) / (||A|| * ||B||)
        dot_product = np.dot(intent_emb, code_emb)
        norm_intent = np.linalg.norm(intent_emb)
        norm_code = np.linalg.norm(code_emb)

        # 边界检查：防止除以零（虽然嵌入向量通常不为零向量）
        if norm_intent == 0 or norm_code == 0:
            logger.warning("检测到零向量嵌入，返回相似度为 0.0")
            return 0.0

        similarity = dot_product / (norm_intent * norm_code)
        
        # 确保数值稳定性，防止浮点误差导致超出 [-1, 1]
        similarity = max(min(similarity, 1.0), -1.0)
        
        logger.debug(f"计算相似度: Intent='{clean_intent[:30]}...', Code='{clean_code[:30]}...' -> {similarity:.4f}")
        return similarity

    def compute_loss(self, intent: str, code: str) -> float:
        """
        核心函数：计算意图与代码对齐的语义损失。

        损失函数定义为 Loss = 1 - Similarity。
        当代码完全符合意图时，Similarity 接近 1，Loss 接近 0。
        当代码与意图无关时，Similarity 接近 0，Loss 接近 1。

        Args:
            intent (str): 自然语言意图描述。
            code (str): 生成的代码片段。

        Returns:
            float: 语义损失值，范围 [0.0, 2.0]（考虑到相似度可能为负）。
                   通常优化目标是使该值最小化（接近 0）。

        Example:
            >>> calculator = IntentCodeSemanticLoss()
            >>> loss = calculator.compute_loss("Sort a list", "print('hello')")
            >>> print(f"Semantic Loss: {loss:.4f}")
        """
        similarity = self.calculate_similarity(intent, code)
        loss = 1.0 - similarity
        logger.info(f"语义损失计算完成: {loss:.4f}")
        return loss


# 使用示例
if __name__ == "__main__":
    # 注意：运行此示例需要安装 sentence-transformers
    # pip install sentence-transformers
    
    print("--- 初始化语义损失计算器 ---")
    # 为了演示速度，这里使用一个较小的通用模型。
    # 在生产环境中，建议使用 'microsoft/codebert-base' 或 'huggingface/CodeBERTa-small-v1'
    try:
        loss_calculator = IntentCodeSemanticLoss(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print(f"初始化失败，请检查依赖: {e}")
        exit(1)

    # 示例 1: 高度对齐
    intent_1 = "Calculate the factorial of a number"
    code_1 = """
    def factorial(n):
        if n == 0: return 1
        return n * factorial(n-1)
    """
    loss_1 = loss_calculator.compute_loss(intent_1, code_1)
    print(f"\n示例 1 (高度对齐):")
    print(f"Intent: {intent_1}")
    print(f"Loss: {loss_1:.4f} (越低越好)")

    # 示例 2: 低度对齐 (代码功能错误)
    intent_2 = "Calculate the factorial of a number"
    code_2 = """
    def add_numbers(a, b):
        return a + b
    """
    loss_2 = loss_calculator.compute_loss(intent_2, code_2)
    print(f"\n示例 2 (低度对齐):")
    print(f"Intent: {intent_2}")
    print(f"Loss: {loss_2:.4f} (越高越差)")

    # 示例 3: 边界检查测试
    print("\n--- 边界检查测试 ---")
    try:
        loss_calculator.compute_loss("", "some code")
    except ValueError as ve:
        print(f"成功捕获空意图错误: {ve}")

    try:
        loss_calculator.compute_loss("valid intent", 123)
    except TypeError as te:
        print(f"成功捕获类型错误: {te}")