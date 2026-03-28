"""
结构化语义适配器

该模块实现了一个能够跨领域迁移逻辑骨架的智能体。它结合了源域的设计模式
（如观察者模式）与目标域的结构约束（如API签名），通过结构映射理论生成
高可用的适配代码。

核心能力:
1. 源域结构提取
2. 目标域结构解析
3. 基于结构映射的代码生成
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Callable, Any
from functools import wraps
import time
from abc import ABC, abstractmethod

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== 数据结构定义 ==============
@dataclass
class StructuralNode:
    """结构节点基类"""
    id: str
    type: str
    attributes: Dict[str, Any]
    children: List['StructuralNode']
    
    def find_by_type(self, node_type: str) -> List['StructuralNode']:
        """递归查找特定类型的节点"""
        result = []
        if self.type == node_type:
            result.append(self)
        for child in self.children:
            result.extend(child.find_by_type(node_type))
        return result


@dataclass
class MappingRule:
    """映射规则"""
    source_pattern: str
    target_template: str
    priority: int = 1


# ============== 核心组件 ==============
class StructuralExtractor:
    """结构提取器 - 从源域提取逻辑骨架"""
    
    def __init__(self):
        self._parsers: Dict[str, Callable] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self) -> None:
        """注册默认解析器"""
        self._parsers['observer'] = self._parse_observer_pattern
        self._parsers['factory'] = self._parse_factory_pattern
        self._parsers['strategy'] = self._parse_strategy_pattern
    
    def extract(self, source_code: str, pattern_type: str) -> StructuralNode:
        """
        从源代码中提取特定模式的结构
        
        Args:
            source_code: 源代码字符串
            pattern_type: 设计模式类型
            
        Returns:
            StructuralNode: 提取的结构树
            
        Raises:
            ValueError: 不支持的模式类型或代码解析失败
        """
        if pattern_type not in self._parsers:
            raise ValueError(f"Unsupported pattern type: {pattern_type}")
        
        logger.info(f"Extracting {pattern_type} pattern structure...")
        
        try:
            return self._parsers[pattern_type](source_code)
        except Exception as e:
            logger.error(f"Failed to extract structure: {str(e)}")
            raise ValueError(f"Structure extraction failed: {str(e)}")
    
    def _parse_observer_pattern(self, code: str) -> StructuralNode:
        """解析观察者模式结构"""
        # 提取类定义
        classes = re.findall(r'class\s+(\w+)[\s(:]', code)
        methods = re.findall(r'def\s+(\w+)\s*\(', code)
        
        # 构建结构树
        root = StructuralNode(
            id="observer_root",
            type="pattern",
            attributes={"name": "Observer Pattern"},
            children=[]
        )
        
        # 添加Subject节点
        subject_node = StructuralNode(
            id="subject",
            type="class",
            attributes={"role": "subject"},
            children=[
                StructuralNode(
                    id=f"method_{m}",
                    type="method",
                    attributes={"name": m},
                    children=[]
                ) for m in methods if 'notify' in m or 'attach' in m or 'detach' in m
            ]
        )
        root.children.append(subject_node)
        
        # 添加Observer节点
        observer_node = StructuralNode(
            id="observer",
            type="class",
            attributes={"role": "observer"},
            children=[
                StructuralNode(
                    id=f"method_{m}",
                    type="method",
                    attributes={"name": m},
                    children=[]
                ) for m in methods if 'update' in m
            ]
        )
        root.children.append(observer_node)
        
        logger.debug(f"Extracted structure with {len(classes)} classes")
        return root
    
    def _parse_factory_pattern(self, code: str) -> StructuralNode:
        """解析工厂模式结构"""
        # 简化实现
        return StructuralNode(
            id="factory_root",
            type="pattern",
            attributes={"name": "Factory Pattern"},
            children=[
                StructuralNode(
                    id="creator",
                    type="class",
                    attributes={"role": "creator"},
                    children=[]
                ),
                StructuralNode(
                    id="product",
                    type="class",
                    attributes={"role": "product"},
                    children=[]
                )
            ]
        )
    
    def _parse_strategy_pattern(self, code: str) -> StructuralNode:
        """解析策略模式结构"""
        # 简化实现
        return StructuralNode(
            id="strategy_root",
            type="pattern",
            attributes={"name": "Strategy Pattern"},
            children=[
                StructuralNode(
                    id="context",
                    type="class",
                    attributes={"role": "context"},
                    children=[]
                ),
                StructuralNode(
                    id="strategy",
                    type="interface",
                    attributes={"role": "strategy"},
                    children=[]
                )
            ]
        )


class TargetDomainParser:
    """目标域解析器 - 解析目标域的结构约束"""
    
    def parse_api_signatures(self, api_docs: str) -> StructuralNode:
        """
        解析API文档中的函数签名
        
        Args:
            api_docs: API文档字符串
            
        Returns:
            StructuralNode: API结构树
        """
        logger.info("Parsing target domain API signatures...")
        
        # 提取函数签名
        signatures = re.findall(
            r'(?:def|function|func)\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\w+))?',
            api_docs
        )
        
        root = StructuralNode(
            id="api_root",
            type="api",
            attributes={"name": "Target API"},
            children=[]
        )
        
        for name, params, return_type in signatures:
            param_list = [p.strip() for p in params.split(',') if p.strip()]
            
            func_node = StructuralNode(
                id=f"func_{name}",
                type="function",
                attributes={
                    "name": name,
                    "params": param_list,
                    "return_type": return_type or "void"
                },
                children=[]
            )
            root.children.append(func_node)
        
        logger.debug(f"Parsed {len(signatures)} API functions")
        return root
    
    def infer_structure(self, signatures: StructuralNode) -> Dict[str, Any]:
        """
        从签名推断隐含结构
        
        Args:
            signatures: API签名结构
            
        Returns:
            Dict: 推断的结构特征
        """
        features = {
            "has_callbacks": False,
            "has_listeners": False,
            "has_factories": False,
            "naming_patterns": set()
        }
        
        for func in signatures.children:
            name = func.attributes.get("name", "")
            params = func.attributes.get("params", [])
            
            # 检测回调特征
            if any('callback' in p.lower() or 'handler' in p.lower() for p in params):
                features["has_callbacks"] = True
            
            # 检测监听器特征
            if 'listen' in name.lower() or 'subscribe' in name.lower():
                features["has_listeners"] = True
            
            # 检测工厂特征
            if 'create' in name.lower() or 'make' in name.lower():
                features["has_factories"] = True
            
            # 提取命名模式
            if '_' in name:
                features["naming_patterns"].add('snake_case')
            elif name[0].isupper():
                features["naming_patterns"].add('PascalCase')
        
        logger.info(f"Inferred features: {features}")
        return features


class StructuralMapper:
    """结构映射器 - 执行源域到目标域的结构映射"""
    
    def __init__(self):
        self.mapping_rules: List[MappingRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """加载默认映射规则"""
        self.mapping_rules = [
            MappingRule(
                source_pattern="observer.subject.notify",
                target_template="api.emit_event",
                priority=1
            ),
            MappingRule(
                source_pattern="observer.observer.update",
                target_template="api.handle_callback",
                priority=1
            ),
            MappingRule(
                source_pattern="factory.creator.create",
                target_template="api.build_instance",
                priority=2
            )
        ]
    
    def map_structures(
        self,
        source: StructuralNode,
        target: StructuralNode,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行结构映射
        
        Args:
            source: 源域结构
            target: 目标域结构
            features: 目标域特征
            
        Returns:
            Dict: 映射结果，包含生成的适配代码
        """
        logger.info("Performing structural mapping...")
        
        mapping_result = {
            "source_pattern": source.attributes.get("name", "Unknown"),
            "target_api": target.attributes.get("name", "Unknown"),
            "mappings": [],
            "generated_code": ""
        }
        
        # 根据特征选择最佳匹配规则
        applicable_rules = self._find_applicable_rules(source, features)
        
        if not applicable_rules:
            logger.warning("No applicable mapping rules found")
            return mapping_result
        
        # 执行映射
        for rule in applicable_rules:
            source_parts = rule.source_pattern.split('.')
            target_parts = rule.target_template.split('.')
            
            # 查找源节点
            source_nodes = self._find_nodes_by_path(source, source_parts)
            
            for node in source_nodes:
                mapping_result["mappings"].append({
                    "source_id": node.id,
                    "source_type": node.type,
                    "target_template": rule.target_template,
                    "priority": rule.priority
                })
        
        # 生成适配代码
        mapping_result["generated_code"] = self._generate_adapter_code(
            source, target, mapping_result["mappings"]
        )
        
        logger.info(f"Generated {len(mapping_result['mappings'])} mappings")
        return mapping_result
    
    def _find_applicable_rules(
        self,
        source: StructuralNode,
        features: Dict[str, Any]
    ) -> List[MappingRule]:
        """查找适用的映射规则"""
        applicable = []
        pattern_name = source.attributes.get("name", "").lower()
        
        for rule in self.mapping_rules:
            if 'observer' in pattern_name and 'observer' in rule.source_pattern:
                if features.get("has_callbacks") or features.get("has_listeners"):
                    applicable.append(rule)
            elif 'factory' in pattern_name and 'factory' in rule.source_pattern:
                if features.get("has_factories"):
                    applicable.append(rule)
        
        return sorted(applicable, key=lambda r: r.priority)
    
    def _find_nodes_by_path(
        self,
        root: StructuralNode,
        path: List[str]
    ) -> List[StructuralNode]:
        """根据路径查找节点"""
        if not path:
            return [root]
        
        current_type = path[0]
        remaining_path = path[1:]
        
        results = []
        if current_type in root.type or current_type in root.id:
            if remaining_path:
                for child in root.children:
                    results.extend(self._find_nodes_by_path(child, remaining_path))
            else:
                results.append(root)
        else:
            for child in root.children:
                results.extend(self._find_nodes_by_path(child, path))
        
        return results
    
    def _generate_adapter_code(
        self,
        source: StructuralNode,
        target: StructuralNode,
        mappings: List[Dict]
    ) -> str:
        """生成适配器代码"""
        code_lines = [
            '"""',
            f'Auto-generated Structural Adapter',
            f'Source Pattern: {source.attributes.get("name", "Unknown")}',
            f'Target API: {target.attributes.get("name", "Unknown")}',
            '"""',
            '',
            'from typing import Callable, Any, List, Dict',
            'import logging',
            '',
            'logger = logging.getLogger(__name__)',
            '',
            '',
            'class StructuralAdapter:',
            '    """结构适配器 - 将源域模式适配到目标域API"""',
            '    ',
            '    def __init__(self, api_client: Any):',
            '        self._api = api_client',
            '        self._callbacks: Dict[str, List[Callable]] = {}',
            '    ',
        ]
        
        # 根据映射生成方法
        for i, mapping in enumerate(mappings):
            method_name = mapping["target_template"].split('.')[-1]
            source_type = mapping["source_type"]
            
            code_lines.extend([
                f'    def {method_name}_{source_type}(self, *args, **kwargs) -> Any:',
                f'        """适配方法 - 源: {mapping["source_id"]}"""',
                '        try:',
                f'            logger.debug(f"Calling adapted method {method_name}")',
                f'            return self._api.{method_name}(*args, **kwargs)',
                '        except Exception as e:',
                '            logger.error(f"Adapter call failed: {{e}}")',
                '            raise',
                '    ',
            ])
        
        code_lines.extend([
            '    def register_callback(self, event: str, callback: Callable) -> None:',
            '        """注册回调函数"""',
            '        if event not in self._callbacks:',
            '            self._callbacks[event] = []',
            '        self._callbacks[event].append(callback)',
            '    ',
            '    def _notify_callbacks(self, event: str, data: Any) -> None:',
            '        """触发回调"""',
            '        for callback in self._callbacks.get(event, []):',
            '            try:',
            '                callback(data)',
            '            except Exception as e:',
            '                logger.error(f"Callback error: {{e}}")',
            ''
        ])
        
        return '\n'.join(code_lines)


class StructuralSemanticAdapter:
    """
    结构化语义适配器 - 主入口类
    
    结合领域A的代码生成能力与领域B的结构映射算法，
    构建能理解并迁移'逻辑骨架'的智能体。
    """
    
    def __init__(self):
        """初始化适配器组件"""
        self.extractor = StructuralExtractor()
        self.parser = TargetDomainParser()
        self.mapper = StructuralMapper()
        self._cache: Dict[str, Any] = {}
        
        logger.info("StructuralSemanticAdapter initialized")
    
    def adapt(
        self,
        source_code: str,
        pattern_type: str,
        api_docs: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整的结构适配流程
        
        Args:
            source_code: 源域代码
            pattern_type: 设计模式类型
            api_docs: 目标域API文档
            validate: 是否验证输入
            
        Returns:
            Dict: 适配结果，包含生成的代码和映射信息
            
        Raises:
            ValueError: 输入验证失败
            RuntimeError: 适配过程失败
        """
        start_time = time.time()
        
        # 输入验证
        if validate:
            self._validate_inputs(source_code, api_docs)
        
        try:
            # Step 1: 提取源域结构
            logger.info(f"Step 1/4: Extracting source structure ({pattern_type})")
            source_structure = self.extractor.extract(source_code, pattern_type)
            
            # Step 2: 解析目标域API
            logger.info("Step 2/4: Parsing target domain API")
            target_structure = self.parser.parse_api_signatures(api_docs)
            
            # Step 3: 推断目标域特征
            logger.info("Step 3/4: Inferring target domain features")
            features = self.parser.infer_structure(target_structure)
            
            # Step 4: 执行结构映射
            logger.info("Step 4/4: Performing structural mapping")
            result = self.mapper.map_structures(
                source_structure, target_structure, features
            )
            
            # 添加元数据
            result["metadata"] = {
                "processing_time": time.time() - start_time,
                "source_nodes": len(source_structure.children),
                "target_functions": len(target_structure.children),
                "pattern_type": pattern_type
            }
            
            logger.info(f"Adaptation completed in {result['metadata']['processing_time']:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Adaptation failed: {str(e)}")
            raise RuntimeError(f"Structural adaptation failed: {str(e)}")
    
    def _validate_inputs(self, source_code: str, api_docs: str) -> None:
        """验证输入数据"""
        if not source_code or len(source_code.strip()) < 10:
            raise ValueError("Source code is too short or empty")
        
        if not api_docs or len(api_docs.strip()) < 5:
            raise ValueError("API documentation is too short or empty")
        
        # 检查基本语法特征
        if 'def ' not in source_code and 'class ' not in source_code:
            raise ValueError("Source code doesn't appear to contain valid Python")
    
    def register_custom_pattern(
        self,
        pattern_name: str,
        parser_func: Callable[[str], StructuralNode]
    ) -> None:
        """
        注册自定义模式解析器
        
        Args:
            pattern_name: 模式名称
            parser_func: 解析函数
        """
        self.extractor._parsers[pattern_name] = parser_func
        logger.info(f"Registered custom pattern parser: {pattern_name}")
    
    def get_supported_patterns(self) -> List[str]:
        """获取支持的模式列表"""
        return list(self.extractor._parsers.keys())


# ============== 辅助函数 ==============
def create_quick_adapter(
    source_code: str,
    api_signatures: str,
    pattern_hint: Optional[str] = None
) -> str:
    """
    快速创建适配器的便捷函数
    
    Args:
        source_code: 源域代码
        api_signatures: API签名
        pattern_hint: 模式提示（可选）
        
    Returns:
        str: 生成的适配器代码
        
    Example:
        >>> source = "class Subject: ..."
        >>> api = "def emit_event(event_name, data): ..."
        >>> code = create_quick_adapter(source, api, "observer")
    """
    adapter = StructuralSemanticAdapter()
    
    # 自动检测模式
    if pattern_hint is None:
        if 'notify' in source_code or 'observer' in source_code.lower():
            pattern_hint = 'observer'
        elif 'create' in source_code or 'factory' in source_code.lower():
            pattern_hint = 'factory'
        elif 'strategy' in source_code.lower():
            pattern_hint = 'strategy'
        else:
            pattern_hint = 'observer'  # 默认
    
    result = adapter.adapt(source_code, pattern_hint, api_signatures)
    return result["generated_code"]


def analyze_structural_similarity(
    code1: str,
    code2: str
) -> Dict[str, Any]:
    """
    分析两段代码之间的结构相似性
    
    Args:
        code1: 第一段代码
        code2: 第二段代码
        
    Returns:
        Dict: 相似性分析结果
    """
    def extract_features(code: str) -> Dict[str, Any]:
        return {
            "classes": len(re.findall(r'class\s+\w+', code)),
            "functions": len(re.findall(r'def\s+\w+', code)),
            "imports": len(re.findall(r'import\s+\w+', code)),
            "decorators": len(re.findall(r'@\w+', code))
        }
    
    features1 = extract_features(code1)
    features2 = extract_features(code2)
    
    # 计算简单相似度
    total = 0
    matches = 0
    for key in features1:
        total += 1
        if features1[key] == features2[key]:
            matches += 1
    
    return {
        "code1_features": features1,
        "code2_features": features2,
        "similarity_score": matches / total if total > 0 else 0,
        "structural_difference": {
            k: features2[k] - features1[k] for k in features1
        }
    }


# ============== 使用示例 ==============
if __name__ == "__main__":
    # 示例源代码（观察者模式）
    EXAMPLE_SOURCE = """
class Subject:
    def __init__(self):
        self._observers = []
    
    def attach(self, observer):
        self._observers.append(observer)
    
    def detach(self, observer):
        self._observers.remove(observer)
    
    def notify(self, event):
        for obs in self._observers:
            obs.update(event)

class Observer:
    def update(self, event):
        print(f"Received: {event}")
"""
    
    # 示例目标API
    EXAMPLE_API = """
def emit_event(event_name: str, data: dict) -> bool:
    pass

def register_callback(callback: Callable[[dict], None]) -> str:
    pass

def unregister_callback(callback_id: str) -> bool:
    pass

def handle_event(event_type: str, handler: Callable) -> None:
    pass
"""
    
    # 执行适配
    print("=" * 60)
    print("Structural Semantic Adapter Demo")
    print("=" * 60)
    
    adapter = StructuralSemanticAdapter()
    
    # 显示支持的模式
    print(f"\nSupported patterns: {adapter.get_supported_patterns()}")
    
    # 执行适配
    result = adapter.adapt(
        source_code=EXAMPLE_SOURCE,
        pattern_type="observer",
        api_docs=EXAMPLE_API
    )
    
    # 输出结果
    print(f"\nSource Pattern: {result['source_pattern']}")
    print(f"Target API: {result['target_api']}")
    print(f"Mappings Found: {len(result['mappings'])}")
    print(f"Processing Time: {result['metadata']['processing_time']:.3f}s")
    
    print("\n" + "=" * 60)
    print("Generated Adapter Code:")
    print("=" * 60)
    print(result['generated_code'])
    
    # 测试快速适配函数
    print("\n" + "=" * 60)
    print("Quick Adapter Test:")
    print("=" * 60)
    quick_code = create_quick_adapter(EXAMPLE_SOURCE, EXAMPLE_API)
    print(quick_code[:500] + "..." if len(quick_code) > 500 else quick_code)