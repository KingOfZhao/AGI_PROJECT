"""
意图形式化的语义熵减机制

本模块实现了一个基于信息论的迭代询问算法，旨在将高熵的模糊人类意图
（如"做一个好用的后台"）转化为低熵的受限语义空间。通过结构化对话，
每次交互通过最大化信息增益来消除歧义，直到意图的语义熵低于特定阈值，
从而为代码生成提供确定性输入。

核心组件:
- SemanticEntropyReducer: 主要的熵减机制类
- InformationGainCalculator: 信息增益计算器
- EntropyEstimator: 语义熵估算器

数据流:
模糊意图 -> 结构化询问 -> 答案解析 -> 熵减迭代 -> 形式化意图

作者: AGI System
版本: 1.0.0
领域: cognitive_science
"""

import math
import random
import logging
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticEntropyReducer")


class IntentCategory(Enum):
    """意图类别枚举"""
    UI_DESIGN = auto()
    DATA_PROCESSING = auto()
    WORKFLOW_AUTOMATION = auto()
    API_INTEGRATION = auto()
    SECURITY = auto()
    PERFORMANCE = auto()
    UNKNOWN = auto()


@dataclass
class SemanticDimension:
    """语义维度数据结构
    
    属性:
        name: 维度名称
        description: 维度描述
        possible_values: 可能的取值列表
        current_entropy: 当前熵值
        resolved_value: 解析后的值
        is_resolved: 是否已解析
    """
    name: str
    description: str
    possible_values: List[str]
    current_entropy: float = 1.0
    resolved_value: Optional[str] = None
    is_resolved: bool = False
    
    def __post_init__(self):
        """初始化后验证数据"""
        if not self.possible_values:
            raise ValueError(f"维度 {self.name} 必须有至少一个可能值")
        if len(self.possible_values) < 2:
            logger.warning(f"维度 {self.name} 只有1个可能值，熵将始终为0")


@dataclass
class FormalizedIntent:
    """形式化意图数据结构
    
    属性:
        original_intent: 原始意图描述
        category: 意图类别
        dimensions: 解析后的语义维度字典
        total_entropy: 总语义熵
        confidence: 置信度
        timestamp: 时间戳
    """
    original_intent: str
    category: IntentCategory
    dimensions: Dict[str, SemanticDimension]
    total_entropy: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_deterministic_spec(self) -> Dict[str, Any]:
        """转换为确定性规格说明"""
        spec = {
            "original_intent": self.original_intent,
            "category": self.category.name,
            "resolved_dimensions": {},
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }
        
        for name, dim in self.dimensions.items():
            if dim.is_resolved:
                spec["resolved_dimensions"][name] = dim.resolved_value
            else:
                spec["resolved_dimensions"][name] = f"UNRESOLVED(entropy={dim.current_entropy:.3f})"
        
        return spec


class EntropyEstimator:
    """语义熵估算器
    
    使用信息论公式计算语义空间的熵值:
    H(X) = -Σ p(x) * log2(p(x))
    """
    
    @staticmethod
    def calculate_dimension_entropy(dimension: SemanticDimension) -> float:
        """计算单个维度的熵
        
        参数:
            dimension: 语义维度对象
            
        返回:
            float: 熵值 (0到1之间)
            
        异常:
            ValueError: 如果维度数据无效
        """
        if not dimension.possible_values:
            raise ValueError("维度必须有至少一个可能值")
        
        if dimension.is_resolved:
            return 0.0
        
        n = len(dimension.possible_values)
        if n == 1:
            return 0.0
        
        # 假设均匀分布
        probability = 1.0 / n
        entropy = -n * probability * math.log2(probability)
        
        # 归一化到0-1范围
        max_entropy = math.log2(n)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return normalized_entropy
    
    @staticmethod
    def calculate_total_entropy(dimensions: Dict[str, SemanticDimension]) -> float:
        """计算所有维度的总熵
        
        参数:
            dimensions: 维度字典
            
        返回:
            float: 总熵值
        """
        if not dimensions:
            return 0.0
        
        total = 0.0
        for dim in dimensions.values():
            total += EntropyEstimator.calculate_dimension_entropy(dim)
        
        # 归一化
        return total / len(dimensions)


class InformationGainCalculator:
    """信息增益计算器
    
    计算每个问题可能带来的信息增益:
    IG(Q) = H(before) - H(after|answer)
    """
    
    @staticmethod
    def calculate_expected_gain(
        dimension: SemanticDimension,
        answer_probability: float = 0.5
    ) -> float:
        """计算针对某维度提问的期望信息增益
        
        参数:
            dimension: 目标维度
            answer_probability: 回答特定值的概率
            
        返回:
            float: 期望信息增益
        """
        current_entropy = EntropyEstimator.calculate_dimension_entropy(dimension)
        
        if current_entropy == 0:
            return 0.0
        
        # 假设回答将熵减半
        expected_reduction = current_entropy * answer_probability
        
        return expected_reduction
    
    @staticmethod
    def select_best_question(
        dimensions: Dict[str, SemanticDimension]
    ) -> Optional[Tuple[str, SemanticDimension]]:
        """选择信息增益最大的问题
        
        参数:
            dimensions: 所有未解析的维度
            
        返回:
            Optional[Tuple[str, SemanticDimension]]: 最佳问题及其维度
        """
        best_gain = 0.0
        best_dimension = None
        best_name = None
        
        for name, dim in dimensions.items():
            if dim.is_resolved:
                continue
                
            gain = InformationGainCalculator.calculate_expected_gain(dim)
            
            if gain > best_gain:
                best_gain = gain
                best_dimension = dim
                best_name = name
        
        if best_dimension:
            logger.info(f"选择维度 '{best_name}' 提问，期望信息增益: {best_gain:.4f}")
            return (best_name, best_dimension)
        
        return None


class SemanticEntropyReducer:
    """语义熵减机制主类
    
    通过迭代询问将模糊意图转化为确定性规格。
    
    使用示例:
        >>> reducer = SemanticEntropyReducer(entropy_threshold=0.1)
        >>> initial_intent = "做一个好用的后台管理系统"
        >>> formalized = reducer.reduce_entropy(initial_intent)
        >>> print(formalized.to_deterministic_spec())
    
    属性:
        entropy_threshold: 熵阈值，低于此值停止迭代
        max_iterations: 最大迭代次数
        dimensions: 当前语义维度
        conversation_history: 对话历史
    """
    
    def __init__(
        self,
        entropy_threshold: float = 0.15,
        max_iterations: int = 10
    ):
        """初始化熵减机制
        
        参数:
            entropy_threshold: 目标熵阈值 (0.0-1.0)
            max_iterations: 最大迭代次数 (1-50)
            
        异常:
            ValueError: 参数超出有效范围
        """
        if not 0.0 <= entropy_threshold <= 1.0:
            raise ValueError("熵阈值必须在0.0到1.0之间")
        
        if not 1 <= max_iterations <= 50:
            raise ValueError("最大迭代次数必须在1到50之间")
        
        self.entropy_threshold = entropy_threshold
        self.max_iterations = max_iterations
        self.dimensions: Dict[str, SemanticDimension] = {}
        self.conversation_history: List[Dict[str, str]] = []
        self.original_intent: str = ""
        
        logger.info(f"初始化语义熵减器，阈值={entropy_threshold}, 最大迭代={max_iterations}")
    
    def _initialize_dimensions(self, intent: str) -> None:
        """根据意图初始化语义维度
        
        参数:
            intent: 原始意图描述
        """
        # 这里使用预定义维度，实际应用中可通过NLP分析动态生成
        self.dimensions = {
            "primary_function": SemanticDimension(
                name="primary_function",
                description="系统的主要功能",
                possible_values=[
                    "用户管理", "内容管理", "数据分析", 
                    "订单处理", "库存管理", "综合管理"
                ]
            ),
            "target_users": SemanticDimension(
                name="target_users",
                description="目标用户群体",
                possible_values=[
                    "内部员工", "外部客户", "管理员", 
                    "普通用户", "混合用户"
                ]
            ),
            "scale": SemanticDimension(
                name="scale",
                description="系统规模",
                possible_values=[
                    "小型(<100用户)", "中型(100-1000用户)", 
                    "大型(1000-10000用户)", "超大型(>10000用户)"
                ]
            ),
            "ui_style": SemanticDimension(
                name="ui_style",
                description="界面风格偏好",
                possible_values=[
                    "简约现代", "功能密集型", "数据可视化导向", 
                    "移动端优先", "传统企业风格"
                ]
            ),
            "integration_needs": SemanticDimension(
                name="integration_needs",
                description="集成需求",
                possible_values=[
                    "独立系统", "需要API对接", "需要SSO集成", 
                    "需要数据分析平台", "全面集成"
                ]
            )
        }
        
        logger.info(f"为意图 '{intent[:50]}...' 初始化了 {len(self.dimensions)} 个语义维度")
    
    def _generate_question(self, dimension: SemanticDimension) -> str:
        """生成针对特定维度的问题
        
        参数:
            dimension: 目标维度
            
        返回:
            str: 生成的问题文本
        """
        options = "\n".join(
            f"  {i+1}. {val}" for i, val in enumerate(dimension.possible_values)
        )
        
        question = f"""
关于您的意图 "{self.original_intent}"，我需要澄清一个方面：

【{dimension.description}】
请选择最符合您需求的选项：
{options}

请输入选项编号或直接描述您的需求："""
        
        return question.strip()
    
    def _parse_answer(
        self, 
        answer: str, 
        dimension: SemanticDimension
    ) -> Optional[str]:
        """解析用户回答
        
        参数:
            answer: 用户回答文本
            dimension: 目标维度
            
        返回:
            Optional[str]: 解析后的值，失败返回None
        """
        answer = answer.strip()
        
        # 尝试解析数字选项
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(dimension.possible_values):
                return dimension.possible_values[idx]
        except ValueError:
            pass
        
        # 尝试模糊匹配
        answer_lower = answer.lower()
        for value in dimension.possible_values:
            if answer_lower in value.lower() or value.lower() in answer_lower:
                return value
        
        # 无法解析，返回原始回答作为新值
        if len(answer) > 2:
            logger.warning(f"无法精确匹配回答，使用原始值: {answer}")
            return answer
        
        return None
    
    def _categorize_intent(self) -> IntentCategory:
        """根据解析结果对意图进行分类
        
        返回:
            IntentCategory: 意图类别
        """
        # 简单的启发式分类
        if "primary_function" in self.dimensions:
            func = self.dimensions["primary_function"].resolved_value
            if func:
                if "数据" in func:
                    return IntentCategory.DATA_PROCESSING
                elif "用户" in func:
                    return IntentCategory.SECURITY
                elif "订单" in func or "库存" in func:
                    return IntentCategory.WORKFLOW_AUTOMATION
        
        # 默认分类
        return IntentCategory.UI_DESIGN
    
    def reduce_entropy(
        self, 
        intent: str,
        answer_provider: Optional[callable] = None
    ) -> FormalizedIntent:
        """执行熵减过程
        
        这是核心函数，通过迭代询问降低意图的语义熵。
        
        参数:
            intent: 原始模糊意图
            answer_provider: 可选的答案提供函数（用于自动化测试）
            
        返回:
            FormalizedIntent: 形式化后的意图对象
            
        异常:
            RuntimeError: 如果迭代过程中出现严重错误
        """
        if not intent or len(intent.strip()) < 3:
            raise ValueError("意图描述太短，至少需要3个字符")
        
        self.original_intent = intent.strip()
        self._initialize_dimensions(self.original_intent)
        self.conversation_history = []
        
        iteration = 0
        current_entropy = 1.0
        
        logger.info(f"开始熵减过程，初始熵: {current_entropy:.4f}")
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # 选择信息增益最大的问题
            question_data = InformationGainCalculator.select_best_question(
                self.dimensions
            )
            
            if not question_data:
                logger.info("所有维度已解析，停止迭代")
                break
            
            dim_name, dimension = question_data
            
            # 生成问题
            question = self._generate_question(dimension)
            
            # 获取答案
            if answer_provider:
                answer = answer_provider(question, dim_name, iteration)
            else:
                # 模拟交互（实际应用中应替换为真实交互）
                answer = self._simulate_answer(dimension, iteration)
            
            # 记录对话历史
            self.conversation_history.append({
                "iteration": str(iteration),
                "dimension": dim_name,
                "question": question,
                "answer": answer
            })
            
            # 解析答案
            resolved_value = self._parse_answer(answer, dimension)
            
            if resolved_value:
                # 更新维度状态
                self.dimensions[dim_name].resolved_value = resolved_value
                self.dimensions[dim_name].is_resolved = True
                self.dimensions[dim_name].possible_values = [resolved_value]
                self.dimensions[dim_name].current_entropy = 0.0
                
                logger.info(f"维度 '{dim_name}' 已解析: {resolved_value}")
            else:
                logger.warning(f"无法解析维度 '{dim_name}' 的答案")
                # 熵减失败，略微降低熵值
                self.dimensions[dim_name].current_entropy *= 0.8
            
            # 重新计算总熵
            current_entropy = EntropyEstimator.calculate_total_entropy(self.dimensions)
            logger.info(f"迭代 {iteration}, 当前熵: {current_entropy:.4f}")
            
            # 检查是否达到阈值
            if current_entropy <= self.entropy_threshold:
                logger.info(f"熵值 {current_entropy:.4f} 低于阈值 {self.entropy_threshold}，停止迭代")
                break
        
        # 计算置信度
        resolved_count = sum(1 for d in self.dimensions.values() if d.is_resolved)
        confidence = resolved_count / len(self.dimensions) if self.dimensions else 0.0
        
        # 分类意图
        category = self._categorize_intent()
        
        # 构建形式化意图对象
        formalized = FormalizedIntent(
            original_intent=self.original_intent,
            category=category,
            dimensions=self.dimensions.copy(),
            total_entropy=current_entropy,
            confidence=confidence
        )
        
        logger.info(f"熵减完成，最终熵: {current_entropy:.4f}, 置信度: {confidence:.2%}")
        
        return formalized
    
    def _simulate_answer(self, dimension: SemanticDimension, iteration: int) -> str:
        """模拟用户回答（用于演示和测试）
        
        参数:
            dimension: 目标维度
            iteration: 当前迭代次数
            
        返回:
            str: 模拟的回答
        """
        # 模拟不同回答模式
        if iteration <= 2:
            # 前两次迭代返回数字选项
            return str(random.randint(1, len(dimension.possible_values)))
        elif random.random() < 0.7:
            # 70%概率返回模糊文本
            return dimension.possible_values[random.randint(0, len(dimension.possible_values)-1)]
        else:
            # 30%概率返回更详细的描述
            return f"我需要{dimension.possible_values[0]}，但要有一些定制化"


def validate_intent_input(intent: str) -> bool:
    """验证意图输入的有效性
    
    参数:
        intent: 待验证的意图字符串
        
    返回:
        bool: 是否有效
    """
    if not intent or not isinstance(intent, str):
        return False
    
    intent = intent.strip()
    
    # 最小长度检查
    if len(intent) < 3:
        return False
    
    # 最大长度检查
    if len(intent) > 1000:
        return False
    
    # 基本内容检查
    if intent.lower() in ["test", "测试", "null", "none"]:
        return False
    
    return True


def demo_entropy_reduction():
    """演示熵减机制的完整工作流程"""
    print("=" * 60)
    print("语义熵减机制演示")
    print("=" * 60)
    
    # 创建熵减器实例
    reducer = SemanticEntropyReducer(entropy_threshold=0.15, max_iterations=8)
    
    # 测试意图
    test_intents = [
        "做一个好用的后台管理系统",
        "开发一个数据分析平台",
        "构建用户权限控制系统"
    ]
    
    for intent in test_intents:
        if not validate_intent_input(intent):
            print(f"无效意图: {intent}")
            continue
        
        print(f"\n处理意图: {intent}")
        print("-" * 50)
        
        try:
            # 执行熵减
            formalized = reducer.reduce_entropy(intent)
            
            # 输出结果
            spec = formalized.to_deterministic_spec()
            print(f"\n形式化结果:")
            print(f"  类别: {spec['category']}")
            print(f"  置信度: {spec['confidence']:.2%}")
            print(f"  最终熵: {formalized.total_entropy:.4f}")
            print(f"  解析维度:")
            for dim, value in spec['resolved_dimensions'].items():
                print(f"    - {dim}: {value}")
            
            # 输出对话历史摘要
            print(f"\n对话历史 ({len(formalized.dimensions)} 轮):")
            for i, entry in enumerate(reducer.conversation_history[:3], 1):
                print(f"  {i}. [{entry['dimension']}] {entry['answer'][:30]}...")
            
        except Exception as e:
            logger.error(f"处理意图时出错: {e}")
            print(f"错误: {e}")


if __name__ == "__main__":
    # 运行演示
    demo_entropy_reduction()
    
    # 使用示例
    print("\n" + "=" * 60)
    print("使用示例")
    print("=" * 60)
    print("""
# 创建熵减器
reducer = SemanticEntropyReducer(entropy_threshold=0.2)

# 定义自定义答案提供函数
def my_answer_provider(question, dimension, iteration):
    print(question)
    return input("您的回答: ")

# 执行熵减
formalized = reducer.reduce_entropy(
    "开发一个电商后台",
    answer_provider=my_answer_provider
)

# 获取确定性规格
spec = formalized.to_deterministic_spec()
print(spec)
""")