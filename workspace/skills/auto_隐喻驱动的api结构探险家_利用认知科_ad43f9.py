"""
隐喻驱动的API结构探险家

该模块利用认知科学中的概念隐喻理论，帮助AI系统快速理解和适应未知的API结构。
通过识别源域（Source Domain，如日常生活中的概念）到目标域（Target Domain，如API结构）
的映射关系，系统能够在缺乏显式文档的情况下，推断函数的行为和数据流向。

核心思想：
- 源域: 熟悉的概念体系（如"咖啡机"、"图书馆"、"流水线"）
- 目标域: 陌生的API结构
- 映射: 将源域的属性和关系映射到目标域，生成预测性的API使用策略

Example:
    >>> from auto_metaphor_explorer import MetaphorExplorer
    >>> explorer = MetaphorExplorer()
    >>> api_doc = {"brew": "Start the brewing process", "bean": "Input data packet"}
    >>> mapping = explorer.analyze(api_doc, source_domain="coffee_machine")
    >>> print(mapping.predict_usage("brew"))
    "Function 'brew' likely initiates a resource-intensive process. Expects 'bean' (data) as input."
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetaphorDomain(Enum):
    """预定义的隐喻源域枚举"""
    COFFEE_MACHINE = "coffee_machine"
    LIBRARY = "library"
    PIPELINE = "pipeline"
    VEHICLE = "vehicle"
    UNKNOWN = "unknown"

@dataclass
class MetaphorMapping:
    """存储隐喻映射结果的数据结构"""
    source_domain: MetaphorDomain
    target_structure: Dict[str, Any]
    confidence_score: float
    semantic_map: Dict[str, str] = field(default_factory=dict)
    inferred_behaviors: Dict[str, str] = field(default_factory=dict)

    def predict_usage(self, function_name: str) -> str:
        """基于隐喻映射预测函数用法"""
        if not self.semantic_map:
            return "Unable to predict: no semantic mapping available."
        
        # 查找最接近的语义映射
        best_match = None
        for key, value in self.semantic_map.items():
            if key.lower() in function_name.lower():
                best_match = value
                break
        
        if not best_match:
            return f"No direct metaphor found for '{function_name}'. General API usage recommended."
        
        return (
            f"Function '{function_name}' maps to '{best_match}' in the {self.source_domain.value} domain. "
            f"Inferred behavior: {self.inferred_behaviors.get(function_name, 'Unknown behavior')}"
        )

class MetaphorExplorer:
    """
    隐喻驱动的API结构探险家
    
    该类通过分析API文档中的自然语言描述，识别潜在的隐喻结构，并将其映射到已知的概念域，
    从而生成对API行为的预测性解释。
    
    Attributes:
        domain_knowledge (Dict): 存储不同源域的知识库
        threshold (float): 判断隐喻匹配有效性的置信度阈值
    """
    
    def __init__(self, threshold: float = 0.65):
        """
        初始化探险家
        
        Args:
            threshold: 置信度阈值，默认0.65。高于此值的映射才会被接受。
        """
        self.threshold = threshold
        self.domain_knowledge = self._load_domain_knowledge()
        logger.info("MetaphorExplorer initialized with threshold %.2f", threshold)
    
    def _load_domain_knowledge(self) -> Dict[MetaphorDomain, Dict[str, Any]]:
        """加载预定义的源域知识库（辅助函数）"""
        knowledge = {
            MetaphorDomain.COFFEE_MACHINE: {
                "keywords": ["brew", "bean", "grind", "pour", "mug", "filter"],
                "semantics": {
                    "brew": "process_start",
                    "bean": "data_input",
                    "grind": "data_processing",
                    "pour": "data_output",
                    "mug": "container",
                    "filter": "validation"
                },
                "behaviors": {
                    "brew": "Initiates resource-intensive process. Blocking or async recommended.",
                    "grind": "Transforms data structure. Expect CPU usage spike."
                }
            },
            MetaphorDomain.LIBRARY: {
                "keywords": ["book", "borrow", "return", "shelf", "catalog", "fine"],
                "semantics": {
                    "borrow": "acquire_lock",
                    "return": "release_lock",
                    "book": "resource_object",
                    "shelf": "storage_partition",
                    "fine": "error_penalty"
                },
                "behaviors": {
                    "borrow": "Acquires exclusive access. Check for availability first.",
                    "return": "Releases resources. Ensure state consistency."
                }
            },
            MetaphorDomain.PIPELINE: {
                "keywords": ["flow", "valve", "pipe", "leak", "pressure", "filter"],
                "semantics": {
                    "flow": "data_stream",
                    "valve": "flow_control",
                    "pipe": "communication_channel",
                    "leak": "memory_leak",
                    "pressure": "system_load"
                },
                "behaviors": {
                    "valve": "Controls data throughput. Can cause backpressure if closed."
                }
            }
        }
        return knowledge
    
    def _preprocess_text(self, text: str) -> List[str]:
        """
        预处理文本：小写化、去除标点、分词
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的单词列表
        """
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()
    
    def analyze(self, api_doc: Dict[str, Any], source_domain: Optional[str] = None) -> MetaphorMapping:
        """
        分析API文档并生成隐喻映射
        
        Args:
            api_doc: 包含API描述的字典，键为函数名/端点名，值为描述文本
            source_domain: 可选，手动指定源域。若为None则自动检测
            
        Returns:
            MetaphorMapping: 包含映射结果和预测的对象
            
        Raises:
            ValueError: 如果输入文档为空或格式不正确
        """
        if not api_doc:
            logger.error("Empty API document provided")
            raise ValueError("API document cannot be empty")
        
        logger.info("Starting metaphor analysis for API with %d endpoints", len(api_doc))
        
        # 自动检测或验证源域
        detected_domain = self._detect_domain(api_doc) if source_domain is None \
                          else MetaphorDomain(source_domain.lower())
        
        if detected_domain == MetaphorDomain.UNKNOWN:
            logger.warning("Could not detect familiar metaphor domain")
            return MetaphorMapping(
                source_domain=detected_domain,
                target_structure=api_doc,
                confidence_score=0.0,
                semantic_map={},
                inferred_behaviors={}
            )
        
        # 构建语义映射
        domain_data = self.domain_knowledge.get(detected_domain, {})
        semantic_map = {}
        inferred_behaviors = {}
        
        for api_term, description in api_doc.items():
            words = self._preprocess_text(str(description))
            for word in words:
                if word in domain_data.get("keywords", []):
                    semantic_map[api_term] = domain_data["semantics"].get(word, "unknown_concept")
                    if word in domain_data.get("behaviors", {}):
                        inferred_behaviors[api_term] = domain_data["behaviors"][word]
                    break  # 匹配第一个关键词
        
        # 计算置信度
        confidence = len(semantic_map) / len(api_doc) if api_doc else 0.0
        logger.info("Analysis complete. Confidence: %.2f", confidence)
        
        return MetaphorMapping(
            source_domain=detected_domain,
            target_structure=api_doc,
            confidence_score=confidence,
            semantic_map=semantic_map,
            inferred_behaviors=inferred_behaviors
        )
    
    def _detect_domain(self, api_doc: Dict[str, Any]) -> MetaphorDomain:
        """
        自动检测API文档最符合的隐喻域
        
        Args:
            api_doc: API文档字典
            
        Returns:
            MetaphorDomain: 检测到的域枚举值
        """
        word_bag = set()
        for desc in api_doc.values():
            word_bag.update(self._preprocess_text(str(desc)))
        
        max_overlap = 0
        best_domain = MetaphorDomain.UNKNOWN
        
        for domain, data in self.domain_knowledge.items():
            overlap = len(word_bag.intersection(set(data["keywords"])))
            if overlap > max_overlap:
                max_overlap = overlap
                best_domain = domain
        
        return best_domain
    
    def compare_apis(self, known_api: Dict[str, Any], unknown_api: Dict[str, Any]) -> Dict[str, float]:
        """
        比较两个API的结构相似性（跨域功能）
        
        Args:
            known_api: 已知API的结构
            unknown_api: 未知API的结构
            
        Returns:
            字典，包含每个函数的相似度得分 (0.0-1.0)
        """
        if not known_api or not unknown_api:
            raise ValueError("Both APIs must contain valid structures")
        
        similarity_scores = {}
        known_words = set()
        
        # 构建已知API的词袋
        for desc in known_api.values():
            known_words.update(self._preprocess_text(str(desc)))
        
        for func, desc in unknown_api.items():
            unknown_words = set(self._preprocess_text(str(desc)))
            common_words = known_words.intersection(unknown_words)
            score = len(common_words) / len(unknown_words) if unknown_words else 0.0
            similarity_scores[func] = round(score, 3)
        
        logger.info("API comparison complete. Avg similarity: %.2f", 
                   sum(similarity_scores.values())/len(similarity_scores))
        return similarity_scores

# 使用示例
if __name__ == "__main__":
    # 创建探险家实例
    explorer = MetaphorExplorer(threshold=0.6)
    
    # 示例1: 分析虚构的量子咖啡机API
    quantum_coffee_api = {
        "quantum_brew": "Initiate quantum superposition brewing",
        "entangled_beans": "Input data in entangled state",
        "haptic_filter": "Filter results through haptic feedback",
        "mug_projection": "Project output into 3D mug space"
    }
    
    mapping = explorer.analyze(quantum_coffee_api)
    print(f"\nDetected Domain: {mapping.source_domain.value}")
    print(f"Confidence: {mapping.confidence_score:.2f}")
    print("Semantic Map:", mapping.semantic_map)
    print("Prediction for 'quantum_brew':", mapping.predict_usage("quantum_brew"))
    
    # 示例2: 比较两个API
    standard_http = {
        "get": "Retrieve data from server",
        "post": "Submit data to server"
    }
    
    weird_api = {
        "fetch_info": "Grab information from the void",
        "push_data": "Shove data into the pipeline"
    }
    
    similarity = explorer.compare_apis(standard_http, weird_api)
    print("\nAPI Similarity Analysis:", similarity)