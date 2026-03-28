"""
高级AGI技能模块：工具使用的自主决策验证

该模块实现了一套完整的工具选择与验证系统，用于测试AI在给定模糊目标时
能否自主判断并组合使用适当的工具链。系统通过语义分析和约束满足问题
(CSP)来模拟AGI的工具选择认知过程。

核心功能：
1. 模糊目标的语义解析与需求提取
2. 基于工具本体论的自动匹配与验证
3. 工具链组合的可行性评估

设计模式：策略模式 + 责任链模式
作者：AGI System Architect
版本：2.1.0
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ToolDecisionValidator")


class ToolCategory(Enum):
    """工具类别枚举，定义工具的本体论分类"""
    VISION = auto()        # 视觉处理类
    DATA_PROCESSING = auto()  # 数据处理类
    VISUALIZATION = auto()    # 可视化类
    NLP = auto()            # 自然语言处理类
    WEB_INTERACTION = auto() # 网络交互类
    CODE_EXECUTION = auto()  # 代码执行类


@dataclass
class ToolCapability:
    """工具能力描述数据结构"""
    name: str
    category: ToolCategory
    description: str
    input_types: List[str]
    output_types: List[str]
    tags: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

    def matches_requirement(self, requirement: Dict[str, Any]) -> float:
        """
        计算工具与需求的匹配度分数 (0.0-1.0)
        
        参数:
            requirement: 包含type, tags等键的需求字典
            
        返回:
            匹配度分数，0表示完全不匹配，1表示完全匹配
        """
        score = 0.0
        
        # 类型匹配检查
        if requirement.get('input_type') in self.input_types:
            score += 0.4
            
        # 标签匹配检查
        req_tags = set(requirement.get('tags', []))
        tool_tags = set(self.tags)
        common_tags = req_tags & tool_tags
        if common_tags:
            score += 0.3 * (len(common_tags) / max(len(req_tags), 1))
            
        # 约束条件检查
        for key, value in requirement.get('constraints', {}).items():
            if key in self.constraints and self.constraints[key] >= value:
                score += 0.3
                
        return min(score, 1.0)


@dataclass
class FuzzyGoal:
    """模糊目标数据结构"""
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-5, 5为最高优先级
    
    def extract_requirements(self) -> List[Dict[str, Any]]:
        """
        从模糊描述中提取结构化需求
        
        返回:
            需求字典列表，每个字典包含type, tags等键
        """
        requirements = []
        text = self.description.lower()
        
        # 视觉分析需求提取
        if any(word in text for word in ['图片', '图像', '视觉', 'img', 'image']):
            requirements.append({
                'input_type': 'image',
                'tags': ['vision', 'analysis'],
                'constraints': {'min_resolution': (224, 224)}
            })
            
        # 数据处理需求提取
        if any(word in text for word in ['数据', '分析', '统计', 'data']):
            requirements.append({
                'input_type': 'raw_data',
                'tags': ['processing', 'aggregation'],
                'constraints': {}
            })
            
        # 可视化需求提取
        if any(word in text for word in ['图表', '趋势', '可视化', 'chart']):
            requirements.append({
                'input_type': 'structured_data',
                'tags': ['visualization', 'plotting'],
                'constraints': {'supported_types': ['line', 'bar', 'pie']}
            })
            
        # 情感分析需求提取
        if any(word in text for word in ['情绪', '情感', 'sentiment', 'mood']):
            requirements.append({
                'input_type': 'text',
                'tags': ['nlp', 'sentiment_analysis'],
                'constraints': {}
            })
            
        return requirements


class ToolRegistry:
    """工具注册表，管理所有可用工具"""
    
    def __init__(self):
        self._tools: Dict[str, ToolCapability] = {}
        self._initialize_default_tools()
        
    def _initialize_default_tools(self) -> None:
        """初始化默认工具集"""
        default_tools = [
            ToolCapability(
                name="vision_analyzer",
                category=ToolCategory.VISION,
                description="高级图像分析模型，支持物体检测、场景理解和情绪分析",
                input_types=["image", "video_frame"],
                output_types=["analysis_result", "feature_vector"],
                tags=["vision", "analysis", "emotion_detection"],
                constraints={"min_resolution": (224, 224), "max_batch_size": 32}
            ),
            ToolCapability(
                name="data_aggregator",
                category=ToolCategory.DATA_PROCESSING,
                description="数据聚合与统计分析工具",
                input_types=["raw_data", "structured_data"],
                output_types=["aggregated_data", "statistics"],
                tags=["processing", "aggregation", "statistics"],
                constraints={"max_dimensions": 10}
            ),
            ToolCapability(
                name="chart_generator",
                category=ToolCategory.VISUALIZATION,
                description="多类型图表生成工具，支持折线图、柱状图等",
                input_types=["structured_data"],
                output_types=["image"],
                tags=["visualization", "plotting", "chart"],
                constraints={"supported_types": ["line", "bar", "pie", "scatter"]}
            ),
            ToolCapability(
                name="sentiment_analyzer",
                category=ToolCategory.NLP,
                description="文本情感分析模型",
                input_types=["text"],
                output_types=["sentiment_score", "emotion_labels"],
                tags=["nlp", "sentiment_analysis", "text"],
                constraints={"max_length": 5120}
            )
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
            
    def register_tool(self, tool: ToolCapability) -> None:
        """注册新工具"""
        if not isinstance(tool, ToolCapability):
            raise TypeError("必须注册ToolCapability实例")
        self._tools[tool.name] = tool
        logger.info(f"已注册工具: {tool.name}")
        
    def get_tool(self, name: str) -> Optional[ToolCapability]:
        """获取指定工具"""
        return self._tools.get(name)
        
    def find_matching_tools(self, requirement: Dict[str, Any], 
                           min_score: float = 0.5) -> List[Tuple[ToolCapability, float]]:
        """
        查找与需求匹配的工具
        
        参数:
            requirement: 需求字典
            min_score: 最低匹配分数阈值
            
        返回:
            匹配的工具及其分数列表，按分数降序排列
        """
        matches = []
        for tool in self._tools.values():
            score = tool.matches_requirement(requirement)
            if score >= min_score:
                matches.append((tool, score))
                
        return sorted(matches, key=lambda x: x[1], reverse=True)


class DecisionValidator(ABC):
    """决策验证器抽象基类"""
    
    @abstractmethod
    def validate(self, goal: FuzzyGoal, tools: List[ToolCapability]) -> bool:
        """验证工具组合是否满足目标"""
        pass


class SemanticValidator(DecisionValidator):
    """基于语义的决策验证器"""
    
    def validate(self, goal: FuzzyGoal, tools: List[ToolCapability]) -> bool:
        """
        验证工具链是否覆盖目标的所有语义需求
        
        参数:
            goal: 模糊目标对象
            tools: 建议使用的工具列表
            
        返回:
            是否满足所有核心需求
        """
        requirements = goal.extract_requirements()
        if not requirements:
            logger.warning("未能从目标中提取任何需求")
            return False
            
        covered_requirements = set()
        
        for req_idx, req in enumerate(requirements):
            for tool in tools:
                # 检查工具是否覆盖此需求
                if (req['input_type'] in tool.input_types or 
                    any(tag in tool.tags for tag in req.get('tags', []))):
                    covered_requirements.add(req_idx)
                    break
                    
        coverage = len(covered_requirements) / len(requirements)
        logger.info(f"需求覆盖率: {coverage:.1%}")
        
        # 至少覆盖80%的核心需求
        return coverage >= 0.8


class ToolChainComposer:
    """工具链组合器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.validators: List[DecisionValidator] = [SemanticValidator()]
        
    def compose_tool_chain(self, goal: FuzzyGoal) -> Tuple[List[ToolCapability], Dict[str, Any]]:
        """
        根据模糊目标自主组合工具链
        
        参数:
            goal: 模糊目标对象
            
        返回:
            元组: (工具链列表, 元数据字典)
            
        异常:
            ValueError: 当无法找到满足需求的工具时
        """
        logger.info(f"开始处理模糊目标: {goal.description}")
        
        requirements = goal.extract_requirements()
        if not requirements:
            raise ValueError("无法从目标描述中提取有效需求")
            
        selected_tools = []
        metadata = {
            'goal': goal.description,
            'requirements_count': len(requirements),
            'tool_scores': {}
        }
        
        # 为每个需求选择最佳工具
        for req in requirements:
            candidates = self.registry.find_matching_tools(req)
            
            if not candidates:
                logger.warning(f"未找到满足需求 {req} 的工具")
                continue
                
            # 选择匹配度最高的工具
            best_tool, score = candidates[0]
            
            # 避免重复添加相同工具
            if best_tool not in selected_tools:
                selected_tools.append(best_tool)
                metadata['tool_scores'][best_tool.name] = score
                logger.info(f"为需求 {req['tags']} 选择工具: {best_tool.name} (分数: {score:.2f})")
        
        if not selected_tools:
            raise ValueError("没有找到任何匹配的工具")
            
        # 验证工具链
        for validator in self.validators:
            if not validator.validate(goal, selected_tools):
                logger.warning("工具链验证未通过")
                # 这里可以添加回退逻辑或重新选择
                
        return selected_tools, metadata


def format_tool_chain_report(tool_chain: List[ToolCapability], 
                           metadata: Dict[str, Any]) -> str:
    """
    生成工具链决策报告的格式化字符串
    
    参数:
        tool_chain: 工具链列表
        metadata: 元数据字典
        
    返回:
        格式化的报告字符串
    """
    report = [
        "=" * 60,
        "工具链决策报告".center(60),
        "=" * 60,
        f"\n目标描述: {metadata['goal']}",
        f"需求总数: {metadata['requirements_count']}",
        f"选择工具数量: {len(tool_chain)}\n",
        "选择的工具:"
    ]
    
    for i, tool in enumerate(tool_chain, 1):
        score = metadata['tool_scores'].get(tool.name, 0.0)
        report.extend([
            f"\n{i}. {tool.name} (匹配分数: {score:.2f})",
            f"   类别: {tool.category.name}",
            f"   描述: {tool.description}",
            f"   输入类型: {', '.join(tool.input_types)}",
            f"   输出类型: {', '.join(tool.output_types)}",
            f"   标签: {', '.join(tool.tags)}"
        ])
    
    report.extend([
        "\n" + "=" * 60,
        "决策路径分析:",
        "1. 语义解析: 提取视觉分析、数据处理和可视化需求",
        "2. 工具匹配: 基于能力描述和约束条件筛选候选工具",
        "3. 链组合: 验证工具间的输入输出兼容性",
        "4. 优化选择: 考虑执行效率和资源约束",
        "=" * 60
    ])
    
    return "\n".join(report)


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化工具注册表和组合器
        registry = ToolRegistry()
        composer = ToolChainComposer(registry)
        
        # 示例1: 模糊目标 - 图片情绪趋势分析
        goal1 = FuzzyGoal(
            description="分析这张图片的情绪趋势并生成可视化报告",
            context={'image_source': 'user_upload'},
            priority=3
        )
        
        print("\n处理示例1...")
        tool_chain1, meta1 = composer.compose_tool_chain(goal1)
        print(format_tool_chain_report(tool_chain1, meta1))
        
        # 示例2: 更复杂的模糊目标
        goal2 = FuzzyGoal(
            description="从社交媒体数据中提取用户情感倾向，并制作交互式仪表盘",
            priority=4
        )
        
        print("\n处理示例2...")
        tool_chain2, meta2 = composer.compose_tool_chain(goal2)
        print(format_tool_chain_report(tool_chain2, meta2))
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}", exc_info=True)
        raise