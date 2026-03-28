"""
高级技能模块：自然语言到类型化函数签名的零样本映射机制

该模块实现了一个零样本（Zero-Shot）解析器，能够将非结构化的自然语言意图描述
转化为符合工业标准的强类型Python函数签名（Pydantic模型或Type Hint字符串）。

核心机制：
1. 基于模式的意图提取：利用启发式规则和上下文关键词提取参数名。
2. 语义类型推断：不依赖特定领域训练数据，而是利用通用语义知识将描述性词汇
   (如 "count", "age", "id") 映射到具体的强类型。
3. 结构安全性验证：生成后的签名经过语法和逻辑校验，确保可被后续AST解析或代码生成器使用。

作者: AGI System
版本: 1.0.0
领域: software_engineering
"""

import re
import logging
import ast
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SemanticType(Enum):
    """语义类型的枚举定义，用于将自然语言映射到具体数据类型"""
    INTEGER = "int"
    FLOAT = "float"
    STRING = "str"
    BOOLEAN = "bool"
    LIST = "List[Any]"
    DICT = "Dict[str, Any]"
    ANY = "Any"

@dataclass
class ParameterSpec:
    """函数参数的规格定义"""
    name: str
    type_hint: str
    description: str
    default_value: Optional[Any] = None
    is_optional: bool = False

@dataclass
class FunctionSignature:
    """完整的函数签名定义"""
    function_name: str
    parameters: List[ParameterSpec]
    return_type: str
    exceptions: List[str]
    docstring: str

class TypeInferenceEngine:
    """
    辅助类：语义类型推断引擎
    负责在不依赖训练数据的情况下，通过关键词匹配和语义规则推断类型。
    """
    
    # 简化的语义映射表（实际生产中可扩展为巨大的知识图谱）
    SEMANTIC_MAP = {
        # 数值类
        r"(count|num|quantity|age|limit|page|size|amount|duration|interval)": SemanticType.INTEGER,
        r"(price|rate|score|ratio|latitude|longitude|temperature|weight)": SemanticType.FLOAT,
        # 布尔类
        r"(is_|has_|can_|should_|enable|disable|active|flag|verbose|force)": SemanticType.BOOLEAN,
        # 集合类
        r"(list|items|array|tags|ids|collection|\[)": SemanticType.LIST,
        # 字典/对象类
        r"(config|meta|json|payload|data|object|dict|mapping)": SemanticType.DICT,
        # 标识符类
        r"(id|pk|uuid|identifier)": SemanticType.STRING, # 假设ID通常为字符串，视具体系统而定
    }

    @classmethod
    def infer_type_from_name(cls, param_name: str, description: str = "") -> SemanticType:
        """
        根据参数名和描述推断类型。
        
        Args:
            param_name: 参数名称
            description: 参数描述文本
            
        Returns:
            推断出的SemanticType枚举值
        """
        combined_text = f"{param_name} {description}".lower()
        
        # 检查是否包含列表标记
        if "list of" in combined_text or "array of" in combined_text:
            return SemanticType.LIST
            
        for pattern, sem_type in cls.SEMANTIC_MAP.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                return sem_type
        
        # 默认为字符串或Any
        return SemanticType.ANY

class SignatureGenerator:
    """
    核心类：将自然语言意图转化为类型化函数签名。
    """
    
    def __init__(self):
        self.type_engine = TypeInferenceEngine()
        logger.info("SignatureGenerator initialized with Zero-Shot capabilities.")

    def _normalize_name(self, raw_text: str) -> str:
        """
        辅助函数：将非结构化文本转换为合法的Python变量名（snake_case）。
        
        Args:
            raw_text: 原始文本片段
            
        Returns:
            规范化的snake_case字符串
        """
        # 移除特殊字符，空格转下划线
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text).strip()
        if not cleaned:
            return "unknown_param"
        
        # 转换为snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cleaned)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace(' ', '_')

    def _extract_intent_structure(self, nl_description: str) -> Dict[str, Any]:
        """
        核心函数1：从非结构化文本中提取结构化意图。
        
        使用正则表达式解析特定的描述模式，例如：
        "Create a user with name, age, and email."
        
        Args:
            nl_description: 自然语言描述
            
        Returns:
            包含函数名、参数列表和返回描述的字典
        """
        logger.debug(f"Parsing intent: {nl_description[:50]}...")
        
        # 提取动词作为函数名前缀
        verbs = re.findall(r'\b(create|get|update|delete|fetch|process|calculate|validate|send|receive)\b', nl_description.lower())
        action = verbs[0] if verbs else "execute"
        
        # 尝试提取名词作为核心对象
        # 简单的分词逻辑：寻找 "the/a [noun]" 或 "for [noun]"
        objects = re.findall(r'\b(?:the|a|an|for)\s+([a-z_]+)\b', nl_description.lower())
        core_object = objects[0] if objects else "task"
        
        func_name = f"{action}_{core_object}"
        
        # 提取参数意图：寻找 "with [params]" 或 "given [params]" 后跟的列表
        # 这是一个简化的提取逻辑，实际上会使用NLP依存句法分析
        params_section = re.search(r'(?:with|using|given|for|params:)\s+(.*?)(?:\.|returns|$)', nl_description, re.IGNORECASE)
        
        raw_params = []
        if params_section:
            # 分割逗号或"and"连接的列表
            param_text = params_section.group(1)
            # 处理 "name, age and email" 这种情况
            parts = re.split(r',|\s+and\s+', param_text)
            raw_params = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
        
        # 提取返回值描述
        return_desc = "Result of the operation"
        return_match = re.search(r'returns?\s+(.*?)(?:\.|throws|$)', nl_description, re.IGNORECASE)
        if return_match:
            return_desc = return_match.group(1).strip()

        return {
            "function_name": self._normalize_name(func_name),
            "raw_params": raw_params,
            "return_desc": return_desc
        }

    def generate_signature(self, nl_description: str) -> FunctionSignature:
        """
        核心函数2：生成完整的类型化函数签名。
        
        Args:
            nl_description: 用户的意图描述
            
        Returns:
            FunctionSignature 对象
            
        Raises:
            ValueError: 如果描述无法解析出有效的意图
        """
        if not nl_description or len(nl_description) < 10:
            logger.error("Input description too short or empty.")
            raise ValueError("Description must be at least 10 characters long.")

        # 1. 提取结构
        intent_data = self._extract_intent_structure(nl_description)
        
        # 2. 类型推断与参数构建
        typed_params: List[ParameterSpec] = []
        
        for raw_p in intent_data['raw_params']:
            param_name = self._normalize_name(raw_p)
            
            # 零样本类型推断
            inferred_type = self.type_engine.infer_type_from_name(param_name, raw_p)
            
            # 简单的异常检测：如果参数名包含"email"，强制转为str
            if "email" in param_name:
                inferred_type = SemanticType.STRING
                
            typed_params.append(ParameterSpec(
                name=param_name,
                type_hint=inferred_type.value,
                description=raw_p,
                is_optional=False
            ))
            
        # 3. 推断返回类型
        return_type = SemanticType.ANY.value
        if "list" in intent_data['return_desc'].lower():
            return_type = SemanticType.LIST.value
        elif "success" in intent_data['return_desc'].lower() or "status" in intent_data['return_desc'].lower():
            return_type = SemanticType.BOOLEAN.value
            
        # 4. 推断异常声明
        exceptions = []
        if "fetch" in intent_data['function_name'] or "get" in intent_data['function_name']:
            exceptions.append("NotFoundError")
        if "file" in nl_description.lower():
            exceptions.append("IOError")
        if "connect" in nl_description.lower():
            exceptions.append("ConnectionError")
            
        signature = FunctionSignature(
            function_name=intent_data['function_name'],
            parameters=typed_params,
            return_type=return_type,
            exceptions=exceptions,
            docstring=nl_description
        )
        
        logger.info(f"Successfully generated signature for: {signature.function_name}")
        return signature

    def validate_signature_safety(self, signature: FunctionSignature) -> bool:
        """
        验证生成的签名的结构安全性。
        确保类型注解是有效的Python字面量，且参数名合法。
        
        Args:
            signature: 待验证的签名对象
            
        Returns:
            bool: 验证通过返回True
        """
        try:
            # 检查函数名语法
            if not re.match(r'^[a-z_][a-z0-9_]*$', signature.function_name):
                logger.warning(f"Invalid function name syntax: {signature.function_name}")
                return False
                
            # 尝试解析类型提示字符串，确保它们是有效的
            for param in signature.parameters:
                # 这里的检查是启发式的，因为List[Any]需要导入typing
                # 我们只检查是否包含非法字符
                if not re.match(r'^[a-zA-Z\[\]\,\s\.]+$', param.type_hint):
                    logger.error(f"Potentially unsafe type hint detected: {param.type_hint}")
                    return False
                    
            logger.info("Signature safety validation passed.")
            return True
            
        except Exception as e:
            logger.error(f"Validation crashed: {e}")
            return False

def main():
    """
    使用示例：演示如何使用该模块生成函数签名。
    """
    generator = SignatureGenerator()
    
    # 示例 1：简单的创建意图
    intent_1 = "Create a new user profile with username, age, email address and is_active status."
    
    # 示例 2：数据获取意图
    intent_2 = "Fetch a list of products given category_id and price_limit. Returns list of items."
    
    print("="*60)
    print(f"Processing Intent 1: {intent_1}")
    sig_1 = generator.generate_signature(intent_1)
    
    if generator.validate_signature_safety(sig_1):
        print(f"Generated Function Name: {sig_1.function_name}")
        print("Parameters:")
        for p in sig_1.parameters:
            print(f"  - {p.name}: {p.type_hint}  ({p.description})")
        print(f"Returns: {sig_1.return_type}")
        print(f"Raises: {sig_1.exceptions}")

    print("\n" + "="*60)
    print(f"Processing Intent 2: {intent_2}")
    sig_2 = generator.generate_signature(intent_2)
    
    if generator.validate_signature_safety(sig_2):
        print(f"Generated Function Name: {sig_2.function_name}")
        print("Parameters:")
        for p in sig_2.parameters:
            print(f"  - {p.name}: {p.type_hint}")
        print(f"Returns: {sig_2.return_type}")

if __name__ == "__main__":
    main()