"""
意图粒度拆解模块

本模块实现了一个基于递归算法的意图拆解系统，用于将宏观复杂意图（如"开发贪吃蛇游戏"）
自上而下地拆解为最小可执行单元（MEU）。该系统通过多维度分析（包括复杂性评估、领域知识匹配
和上下文相关性）来确定何时终止递归，从而避免无限递归或粒度过粗的问题。

核心算法采用混合策略：
1. 结构化分析：识别意图中的逻辑连接词和子任务结构
2. 复杂性评估：基于任务特征评估是否达到最小粒度
3. 领域知识辅助：利用预定义规则加速特定领域任务的拆解

典型应用场景：
- 自动化任务规划系统
- 认知架构中的任务分解
- 复杂系统开发的需求分析

输入格式：
{
    "intent": "开发一个贪吃蛇游戏",
    "context": {
        "domain": "game_development",
        "complexity_threshold": 0.7,
        "max_depth": 5
    }
}

输出格式：
{
    "status": "success",
    "result": {
        "original_intent": "开发一个贪吃蛇游戏",
        "decomposition_tree": {...},
        "meu_list": [...],
        "statistics": {...}
    }
}
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, auto
import json
import re
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IntentDecomposer")


class IntentType(Enum):
    """意图类型枚举"""
    ATOMIC = auto()      # 最小可执行单元
    COMPOSITE = auto()   # 复合意图，需要进一步拆解
    UNKNOWN = auto()     # 未知类型


@dataclass
class IntentNode:
    """意图节点数据结构，表示拆解树中的一个节点"""
    content: str
    type: IntentType = IntentType.UNKNOWN
    depth: int = 0
    complexity: float = 0.0
    children: List['IntentNode'] = field(default_factory=list)
    parent: Optional['IntentNode'] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """将节点转换为字典表示"""
        return {
            "content": self.content,
            "type": self.type.name,
            "depth": self.depth,
            "complexity": self.complexity,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata
        }


@dataclass
class DecompositionResult:
    """拆解结果数据结构"""
    original_intent: str
    decomposition_tree: Dict
    meu_list: List[Dict]
    statistics: Dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """将结果转换为字典表示"""
        return {
            "original_intent": self.original_intent,
            "decomposition_tree": self.decomposition_tree,
            "meu_list": self.meu_list,
            "statistics": self.statistics,
            "timestamp": self.timestamp
        }


class IntentDecomposer:
    """意图拆解器主类"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化意图拆解器
        
        参数:
            config: 配置字典，包含以下可选项:
                - complexity_threshold: 复杂度阈值，默认0.7
                - max_depth: 最大递归深度，默认5
                - domain_rules: 领域特定规则字典
                - meu_criteria: 最小可执行单元标准
        """
        self.config = config or {}
        self.complexity_threshold = self.config.get('complexity_threshold', 0.7)
        self.max_depth = self.config.get('max_depth', 5)
        self.domain_rules = self.config.get('domain_rules', {})
        
        # 初始化领域规则（示例）
        self._init_domain_rules()
        
        logger.info("IntentDecomposer initialized with config: %s", json.dumps(self.config, indent=2))
    
    def _init_domain_rules(self):
        """初始化领域特定规则"""
        # 游戏开发领域规则
        self.domain_rules['game_development'] = {
            'split_patterns': [
                r'开发一个(.+?)游戏',
                r'实现(.+?)功能',
                r'设计(.+?)模块'
            ],
            'atomic_intents': [
                '绘制游戏界面',
                '处理用户输入',
                '实现游戏逻辑',
                '添加音效',
                '实现计分系统'
            ]
        }
        
        # Web开发领域规则
        self.domain_rules['web_development'] = {
            'split_patterns': [
                r'创建一个(.+?)网站',
                r'实现(.+?)功能',
                r'设计(.+?)页面'
            ],
            'atomic_intents': [
                '设计数据库模式',
                '创建前端界面',
                '实现后端API',
                '添加用户认证',
                '部署应用'
            ]
        }
    
    def decompose_intent(self, intent: str, context: Optional[Dict] = None) -> Dict:
        """
        拆解复杂意图为最小可执行单元
        
        参数:
            intent: 要拆解的意图字符串
            context: 上下文信息，包含领域等元数据
            
        返回:
            包含拆解结果的字典
            
        异常:
            ValueError: 当输入意图为空或无效时抛出
            RuntimeError: 当拆解过程中出现严重错误时抛出
        """
        if not intent or not isinstance(intent, str):
            logger.error("Invalid intent provided: %s", intent)
            raise ValueError("Intent must be a non-empty string")
            
        context = context or {}
        logger.info("Starting decomposition for intent: '%s'", intent)
        logger.debug("Context: %s", json.dumps(context, indent=2))
        
        try:
            # 创建根节点
            root_node = IntentNode(content=intent, depth=0)
            
            # 执行递归拆解
            self._recursive_decompose(root_node, context)
            
            # 收集最小可执行单元
            meu_list = self._collect_meu(root_node)
            
            # 生成统计信息
            statistics = {
                "total_nodes": self._count_nodes(root_node),
                "max_depth": self._calculate_max_depth(root_node),
                "meu_count": len(meu_list),
                "complexity_avg": self._calculate_avg_complexity(root_node)
            }
            
            # 构建结果对象
            result = DecompositionResult(
                original_intent=intent,
                decomposition_tree=root_node.to_dict(),
                meu_list=meu_list,
                statistics=statistics
            )
            
            logger.info("Decomposition completed successfully")
            logger.debug("Result: %s", json.dumps(result.to_dict(), indent=2))
            
            return {
                "status": "success",
                "result": result.to_dict()
            }
            
        except Exception as e:
            logger.error("Error during intent decomposition: %s", str(e), exc_info=True)
            raise RuntimeError(f"Failed to decompose intent: {str(e)}") from e
    
    def _recursive_decompose(self, node: IntentNode, context: Dict, current_depth: int = 0) -> None:
        """
        递归拆解意图节点的核心方法
        
        参数:
            node: 当前处理的意图节点
            context: 上下文信息
            current_depth: 当前递归深度
        """
        # 检查递归深度
        if current_depth > self.max_depth:
            logger.warning("Max recursion depth reached at node: %s", node.content)
            node.type = IntentType.ATOMIC
            return
            
        # 评估节点复杂度
        complexity = self._evaluate_complexity(node.content, context)
        node.complexity = complexity
        
        # 检查是否为最小可执行单元
        if complexity < self.complexity_threshold or self._is_meu(node.content, context):
            node.type = IntentType.ATOMIC
            logger.debug("Atomic intent found: %s (complexity: %.2f)", node.content, complexity)
            return
            
        # 尝试拆解节点
        sub_intents = self._split_intent(node.content, context)
        
        if not sub_intents:
            node.type = IntentType.ATOMIC
            logger.debug("No further decomposition possible for: %s", node.content)
            return
            
        # 创建子节点
        node.type = IntentType.COMPOSITE
        for sub_intent in sub_intents:
            child_node = IntentNode(
                content=sub_intent,
                depth=current_depth + 1,
                parent=node
            )
            node.children.append(child_node)
            
            # 递归处理子节点
            self._recursive_decompose(child_node, context, current_depth + 1)
    
    def _split_intent(self, intent: str, context: Dict) -> List[str]:
        """
        拆解意图为子意图列表
        
        参数:
            intent: 要拆解的意图
            context: 上下文信息
            
        返回:
            子意图列表
        """
        domain = context.get('domain', 'general')
        domain_rules = self.domain_rules.get(domain, {})
        
        # 尝试应用领域特定规则
        for pattern in domain_rules.get('split_patterns', []):
            match = re.search(pattern, intent)
            if match:
                # 这里可以根据匹配结果生成更具体的子意图
                # 简化示例：直接返回预定义的原子意图
                return domain_rules.get('atomic_intents', [])
        
        # 通用拆解逻辑（简化版）
        if "和" in intent:
            return [part.strip() for part in intent.split("和")]
        elif "然后" in intent:
            return [part.strip() for part in intent.split("然后")]
        elif "以及" in intent:
            return [part.strip() for part in intent.split("以及")]
        
        # 如果没有明显的拆分点，返回空列表表示无法进一步拆解
        return []
    
    def _evaluate_complexity(self, intent: str, context: Dict) -> float:
        """
        评估意图的复杂度
        
        参数:
            intent: 要评估的意图
            context: 上下文信息
            
        返回:
            复杂度评分 (0.0-1.0)
        """
        # 简化复杂度评估逻辑
        complexity = 0.0
        
        # 基于长度评估
        if len(intent) > 50:
            complexity += 0.3
        
        # 基于关键词评估
        complex_keywords = ['系统', '平台', '框架', '架构', '综合', '集成']
        for keyword in complex_keywords:
            if keyword in intent:
                complexity += 0.2
        
        # 基于连接词评估
        if any(word in intent for word in ['和', '以及', '然后', '同时']):
            complexity += 0.3
        
        # 确保复杂度在0-1范围内
        return min(max(complexity, 0.0), 1.0)
    
    def _is_meu(self, intent: str, context: Dict) -> bool:
        """
        判断意图是否为最小可执行单元
        
        参数:
            intent: 要判断的意图
            context: 上下文信息
            
        返回:
            布尔值，表示是否为最小可执行单元
        """
        domain = context.get('domain', 'general')
        domain_rules = self.domain_rules.get(domain, {})
        
        # 检查是否在预定义的原子意图列表中
        if intent in domain_rules.get('atomic_intents', []):
            return True
        
        # 基于特征的判断逻辑
        meu_indicators = [
            len(intent) < 20,  # 短意图更可能是原子性的
            not any(word in intent for word in ['和', '以及', '然后', '同时']),
            intent.startswith(('实现', '创建', '设计', '编写', '修复'))
        ]
        
        return all(meu_indicators)
    
    def _collect_meu(self, node: IntentNode) -> List[Dict]:
        """
        收集树中的所有最小可执行单元
        
        参数:
            node: 意图树的根节点
            
        返回:
            最小可执行单元列表
        """
        meu_list = []
        
        if node.type == IntentType.ATOMIC:
            meu_list.append({
                "content": node.content,
                "depth": node.depth,
                "complexity": node.complexity,
                "metadata": node.metadata
            })
        else:
            for child in node.children:
                meu_list.extend(self._collect_meu(child))
        
        return meu_list
    
    def _count_nodes(self, node: IntentNode) -> int:
        """计算树中的节点总数"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def _calculate_max_depth(self, node: IntentNode) -> int:
        """计算树的最大深度"""
        if not node.children:
            return node.depth
        return max(self._calculate_max_depth(child) for child in node.children)
    
    def _calculate_avg_complexity(self, node: IntentNode) -> float:
        """计算节点的平均复杂度"""
        total, count = self._calculate_complexity_sum(node)
        return total / count if count > 0 else 0.0
    
    def _calculate_complexity_sum(self, node: IntentNode) -> Tuple[float, int]:
        """辅助方法：计算复杂度总和和节点数"""
        total = node.complexity
        count = 1
        
        for child in node.children:
            child_total, child_count = self._calculate_complexity_sum(child)
            total += child_total
            count += child_count
            
        return total, count


# 使用示例
if __name__ == "__main__":
    # 示例配置
    config = {
        "complexity_threshold": 0.6,
        "max_depth": 4,
        "domain_rules": {
            "game_development": {
                "split_patterns": [
                    r'开发一个(.+?)游戏',
                    r'实现(.+?)功能'
                ],
                "atomic_intents": [
                    "绘制游戏界面",
                    "处理用户输入",
                    "实现游戏逻辑",
                    "添加音效",
                    "实现计分系统"
                ]
            }
        }
    }
    
    # 创建拆解器实例
    decomposer = IntentDecomposer(config)
    
    # 示例意图
    intent = "开发一个贪吃蛇游戏"
    context = {
        "domain": "game_development",
        "user_expertise": "intermediate"
    }
    
    # 执行拆解
    result = decomposer.decompose_intent(intent, context)
    
    # 打印结果
    print("\nDecomposition Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 另一个示例
    web_intent = "创建一个电商网站和移动应用"
    web_context = {
        "domain": "web_development",
        "complexity_threshold": 0.5
    }
    
    web_result = decomposer.decompose_intent(web_intent, web_context)
    print("\nWeb Development Example:")
    print(json.dumps(web_result, indent=2, ensure_ascii=False))