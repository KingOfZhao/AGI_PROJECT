"""
模块: semantic_alignment_evaluator
描述: 构建基于特征指纹的代码意境对齐评估器。

该模块实现了'意境对齐评估器'，用于在AGI或辅助编程系统中评估生成的代码
是否符合业务意图。不同于传统的单元测试（检查具体数值），本评估器通过
Embedding技术计算'代码行为序列'与'业务意图描述'在潜在空间的重叠度。

核心哲学：
- 形可异，意必同 (Form varies, Intent aligns)。
- 允许非关键路径（如变量命名、循环结构）随性发挥。
- 核心业务逻辑（器型）必须在语义空间严丝合缝。

依赖:
    - numpy: 数值计算
    - sklearn: 余弦相似度计算
    - (模拟) langchain/embeddings: 用于将文本/代码转换为向量
"""

import logging
import re
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticEvaluator")


class AlignmentLevel(Enum):
    """对齐等级枚举"""
    PERFECT = "perfect"         # 完美契合
    ACCEPTABLE = "acceptable"   # 可接受的偏差
    DIVERGENT = "divergent"     # 意境发散（不合格）


@dataclass
class EvaluationResult:
    """评估结果数据结构"""
    score: float                    # 综合得分 [0.0, 1.0]
    level: AlignmentLevel           # 评级
    semantic_overlap: float         # 语义重叠度
    structural_fingerprint: float   # 结构指纹匹配度
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息

    def to_json(self) -> str:
        return json.dumps({
            "score": self.score,
            "level": self.level.value,
            "semantic_overlap": self.semantic_overlap,
            "details": self.details
        }, indent=2)


class MockEmbeddingModel:
    """
    模拟的Embedding模型 (实际生产中应替换为 OpenAI, HuggingFace 等真实实现)
    用于将文本或代码片段转换为向量。
    """
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 模拟逻辑：生成随机向量，但在确定性种子下保持一致性
        # 在真实场景中，这里会调用 Transformer 模型
        return [self._get_mock_embedding(t) for t in texts]

    def _get_mock_embedding(self, text: str) -> List[float]:
        # 简单的模拟：基于字符生成伪向量，确保相同文本向量相同
        np.random.seed(sum(ord(c) for c in text))
        return np.random.rand(768).tolist()


class SemanticAlignmentEvaluator:
    """
    意境对齐评估器核心类。
    
    通过计算代码指纹向量和意图描述向量的余弦相似度，判断代码是否满足了
    业务的核心需求，同时允许非关键实现的多样性。
    """

    def __init__(self, threshold_acceptable: float = 0.75, threshold_perfect: float = 0.92):
        """
        初始化评估器。

        Args:
            threshold_acceptable (float): 合格阈值，默认0.75
            threshold_perfect (float): 完美阈值，默认0.92
        """
        if not (0.0 <= threshold_acceptable <= 1.0 and 0.0 <= threshold_perfect <= 1.0):
            raise ValueError("Thresholds must be between 0.0 and 1.0")
            
        self.model = MockEmbeddingModel()
        self.threshold_acceptable = threshold_acceptable
        self.threshold_perfect = threshold_perfect
        logger.info("SemanticAlignmentEvaluator initialized with thresholds: acc=%s, perf=%s",
                    threshold_acceptable, threshold_perfect)

    def _extract_behavior_fingerprint(self, code_snippet: str) -> str:
        """
        [辅助函数] 提取代码的行为指纹。
        
        通过移除变量名、注释和特定格式，只保留关键字和结构，
        生成类似于'器型'的抽象描述文本，用于后续向量化。

        Args:
            code_snippet (str): 源代码字符串
            
        Returns:
            str: 抽象化后的代码结构描述
        """
        if not code_snippet or not isinstance(code_snippet, str):
            return ""
        
        # 1. 移除注释
        code = re.sub(r'#.*$', '', code_snippet, flags=re.MULTILINE)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        
        # 2. 归一化关键字和结构 (简化版，实际可使用AST)
        # 将代码视为一串行为动词和名词的组合
        tokens = re.findall(r'\b(def|class|return|if|for|while|import|try|except|with|async|await)\b', code)
        
        # 构建指纹字符串：包含结构关键字和函数调用模式
        # 这里的逻辑是：我们关注代码做了什么(结构)，而不是变量叫什么
        fingerprint = " ".join(tokens)
        
        # 3. 简单的语义增强 (将代码符号映射为自然语言描述，辅助Embedding理解)
        # 例如：看到 "def" -> "function definition", "return" -> "output value"
        semantic_map = {
            "def": "subroutine definition",
            "return": "output result",
            "if": "conditional check",
            "for": "iteration loop",
            "try": "error handling"
        }
        enhanced_desc = " ".join([semantic_map.get(t, t) for t in tokens])
        
        logger.debug(f"Extracted fingerprint: {enhanced_desc[:50]}...")
        return enhanced_desc

    def evaluate_alignment(self, 
                           generated_code: str, 
                           intent_description: str, 
                           context: Optional[Dict] = None) -> EvaluationResult:
        """
        [核心函数] 评估生成的代码与业务意图的对齐程度。

        Args:
            generated_code (str): AI生成的代码
            intent_description (str): 自然语言描述的业务意图
            context (Optional[Dict]): 上下文信息，如相关API文档

        Returns:
            EvaluationResult: 包含分数和详细信息的评估结果对象
        """
        logger.info("Starting evaluation for intent: '%s...'", intent_description[:30])
        
        # 1. 数据清洗与边界检查
        if not generated_code.strip():
            return EvaluationResult(0.0, AlignmentLevel.DIVERGENT, 0.0, 0.0, 
                                    {"error": "Empty code snippet"})
        
        # 2. 提取代码的'行为指纹'
        # 将代码转换为一种描述其行为结构的文本
        code_fingerprint_text = self._extract_behavior_fingerprint(generated_code)
        
        # 如果代码太简单可能提取不出指纹，回退到原始代码
        if not code_fingerprint_text:
            code_fingerprint_text = generated_code

        # 3. 构建对比文本
        # 结合上下文（如果有）增强意图描述
        full_intent = intent_description
        if context and "api_docs" in context:
            full_intent += f" Context: {context['api_docs']}"

        # 4. 向量化
        # 实际场景中这里会调用真正的LLM Embedding接口
        try:
            vectors = self.model.embed_documents([code_fingerprint_text, full_intent])
            vec_code = np.array(vectors[0]).reshape(1, -1)
            vec_intent = np.array(vectors[1]).reshape(1, -1)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return EvaluationResult(0.0, AlignmentLevel.DIVERGENT, 0.0, 0.0, 
                                    {"error": str(e)})

        # 5. 计算余弦相似度
        similarity_matrix = cosine_similarity(vec_code, vec_intent)
        semantic_overlap = float(similarity_matrix[0][0])
        
        # 6. 计算结构完整性权重
        # 检查代码是否包含基本的语法结构，防止只有注释
        structural_integrity = self._check_structural_integrity(generated_code)
        
        # 7. 综合评分
        # 评分 = 语义重叠度 * 结构完整性权重
        final_score = semantic_overlap * (0.5 + 0.5 * structural_integrity)
        
        # 8. 确定评级
        level = AlignmentLevel.DIVERGENT
        if final_score >= self.threshold_perfect:
            level = AlignmentLevel.PERFECT
        elif final_score >= self.threshold_acceptable:
            level = AlignmentLevel.ACCEPTABLE
            
        logger.info(f"Evaluation complete. Score: {final_score:.4f}, Level: {level.value}")

        return EvaluationResult(
            score=round(final_score, 4),
            level=level,
            semantic_overlap=round(semantic_overlap, 4),
            structural_fingerprint=round(structural_integrity, 4),
            details={
                "code_fingerprint_preview": code_fingerprint_text[:100],
                "intent_preview": intent_description[:100]
            }
        )

    def _check_structural_integrity(self, code: str) -> float:
        """
        [辅助函数] 检查代码的结构完整性。
        
        确保代码不仅仅是文本，而是包含定义、逻辑块等可执行结构。
        返回一个 0.0 到 1.0 的系数。
        """
        score = 0.0
        if "def " in code: score += 0.3
        if "return " in code: score += 0.3
        if "class " in code: score += 0.2
        if any(kw in code for kw in ["if ", "for ", "while "]): score += 0.2
        return min(score, 1.0)

    def batch_evaluate(self, 
                       code_samples: List[str], 
                       intent: str) -> List[EvaluationResult]:
        """
        [核心函数] 批量评估多个代码样本，寻找最符合'意境'的实现。
        
        适用场景：AGI系统生成多个候选代码方案，从中挑选最优解。

        Args:
            code_samples (List[str]): 代码样本列表
            intent (str): 统一的业务意图
            
        Returns:
            List[EvaluationResult]: 评估结果列表
        """
        results = []
        for i, code in enumerate(code_samples):
            logger.info(f"Evaluating sample {i+1}/{len(code_samples)}")
            res = self.evaluate_alignment(code, intent)
            results.append(res)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化评估器
    evaluator = SemanticAlignmentEvaluator(threshold_acceptable=0.7)
    
    # 定义业务意图 (意境)
    business_intent = "实现一个函数，接收用户ID，从数据库查询该用户的订单列表，并计算总金额。"
    
    # 样本1: 传统的、标准的实现 (期望: Acceptable/Perfect)
    code_sample_1 = """
def get_user_orders(user_id):
    # Connect to DB
    session = db.connect()
    orders = session.query(Order).filter_by(user_id=user_id).all()
    
    total_amount = 0
    for order in orders:
        total_amount += order.price
    
    return total_amount
"""

    # 样本2: 更加Pythonic的实现 (生成器表达式) (期望: Perfect - 意图一致，形式不同)
    code_sample_2 = """
def calculate_total_spending(uid):
    # Fetch data
    records = db.get_connection().fetch_all('orders', uid)
    return sum(r['price'] for r in records)
"""

    # 样本3: 意图偏离的实现 (发邮件而不是算钱) (期望: Divergent)
    code_sample_3 = """
def process_user(uid):
    email = User.get_email(uid)
    send_mail(email, "Welcome")
    return True
"""

    # 样本4: 非代码内容 (期望: Divergent)
    code_sample_4 = "这段代码用于计算订单总额，但我没有写代码。"

    print(f"--- Evaluating against intent: '{business_intent}' ---\n")

    samples = [code_sample_1, code_sample_2, code_sample_3, code_sample_4]
    results = evaluator.batch_evaluate(samples, business_intent)

    for i, res in enumerate(results):
        print(f"Rank {i+1}:")
        print(f"  Score: {res.score}")
        print(f"  Level: {res.level.value}")
        print(f"  Overlap: {res.semantic_overlap}")
        print("-" * 20)