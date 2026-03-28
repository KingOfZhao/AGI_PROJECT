"""
Module: inverse_prompt_engineering.py
Description: 实现'反向提示词工程'模块，用于自动生成攻击性测试用例以验证新概念的边界和鲁棒性。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inverse_prompt_engineering.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """测试用例数据结构"""
    test_id: str
    category: str
    description: str
    expected_impact: str
    created_at: str


@dataclass
class ConceptAnalysis:
    """概念分析结果数据结构"""
    concept_name: str
    definition: str
    core_attributes: List[str]
    edge_cases: List[str]
    test_cases: List[TestCase]


class InversePromptEngineer:
    """
    反向提示词工程核心类
    
    该类负责接收新概念，并自动生成攻击性测试用例来验证概念的边界和鲁棒性。
    
    Example:
        >>> engineer = InversePromptEngineer()
        >>> concept = "元宇宙中的地缘政治"
        >>> analysis = engineer.analyze_concept(concept)
        >>> print(analysis.test_cases)
    """
    
    def __init__(self, max_test_cases: int = 10):
        """
        初始化反向提示词工程器
        
        Args:
            max_test_cases: 生成的最大测试用例数量，默认为10
        """
        self.max_test_cases = max_test_cases
        self._validate_init_params()
        logger.info(f"InversePromptEngineer initialized with max_test_cases={max_test_cases}")
    
    def _validate_init_params(self) -> None:
        """验证初始化参数"""
        if not isinstance(self.max_test_cases, int) or self.max_test_cases <= 0:
            raise ValueError("max_test_cases must be a positive integer")
    
    def analyze_concept(self, concept: str) -> ConceptAnalysis:
        """
        分析概念并生成测试用例
        
        Args:
            concept: 待分析的新概念字符串
            
        Returns:
            ConceptAnalysis: 包含定义、核心属性和测试用例的分析结果
            
        Raises:
            ValueError: 如果概念为空或格式无效
        """
        try:
            # 输入验证
            if not concept or not isinstance(concept, str):
                raise ValueError("Concept must be a non-empty string")
            
            cleaned_concept = self._sanitize_input(concept)
            logger.info(f"Analyzing concept: {cleaned_concept}")
            
            # 模拟概念分析过程
            definition = self._generate_definition(cleaned_concept)
            core_attributes = self._extract_core_attributes(cleaned_concept)
            edge_cases = self._identify_edge_cases(cleaned_concept, core_attributes)
            test_cases = self._generate_test_cases(cleaned_concept, edge_cases)
            
            analysis = ConceptAnalysis(
                concept_name=cleaned_concept,
                definition=definition,
                core_attributes=core_attributes,
                edge_cases=edge_cases,
                test_cases=test_cases[:self.max_test_cases]
            )
            
            logger.info(f"Successfully generated {len(analysis.test_cases)} test cases for concept: {cleaned_concept}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing concept '{concept}': {str(e)}")
            raise
    
    def _sanitize_input(self, input_string: str) -> str:
        """
        清理和规范化输入字符串
        
        Args:
            input_string: 原始输入字符串
            
        Returns:
            str: 清理后的字符串
        """
        # 移除多余空格和特殊字符
        sanitized = re.sub(r'[^\w\s\u4e00-\u9fff]', '', input_string.strip())
        if not sanitized:
            raise ValueError("Input contains no valid characters after sanitization")
        return sanitized
    
    def _generate_definition(self, concept: str) -> str:
        """
        生成概念定义（模拟）
        
        Args:
            concept: 概念名称
            
        Returns:
            str: 生成的定义
        """
        # 这里应该是调用LLM或其他服务的实际实现
        # 模拟实现
        definitions = {
            "元宇宙中的地缘政治": "在虚拟世界元宇宙中，国家、组织或个人之间因虚拟领土、资源、数据主权等引发的权力关系和政治互动。",
            "数字货币监管": "针对加密货币、稳定币等数字资产制定的法律框架和监管政策。"
        }
        return definitions.get(concept, f"关于'{concept}'的综合性定义，涉及其核心特征和作用机制。")
    
    def _extract_core_attributes(self, concept: str) -> List[str]:
        """
        提取概念的核心属性（模拟）
        
        Args:
            concept: 概念名称
            
        Returns:
            List[str]: 核心属性列表
        """
        # 模拟属性提取逻辑
        if "地缘政治" in concept:
            return ["虚拟领土", "数据主权", "数字国界", "虚拟资源", "数字身份"]
        elif "货币" in concept:
            return ["去中心化", "匿名性", "跨境流动", "价值存储", "智能合约"]
        else:
            return ["基本属性1", "基本属性2", "基本属性3", "基本属性4", "基本属性5"]
    
    def _identify_edge_cases(self, concept: str, attributes: List[str]) -> List[str]:
        """
        识别概念的边界情况（模拟）
        
        Args:
            concept: 概念名称
            attributes: 核心属性列表
            
        Returns:
            List[str]: 边界情况列表
        """
        # 模拟边界情况识别
        edge_cases = []
        
        for attr in attributes:
            if "领土" in attr or "国界" in attr:
                edge_cases.extend([
                    "服务器宕机时的领土连续性",
                    "跨平台虚拟领土争端",
                    "数字国界的物理实现"
                ])
            elif "主权" in attr:
                edge_cases.extend([
                    "多平台间的主权冲突",
                    "用户数据所有权争议",
                    "平台政策变更的主权影响"
                ])
            elif "资源" in attr:
                edge_cases.extend([
                    "虚拟资源稀缺性的人为控制",
                    "资源分配算法的公平性",
                    "跨平台资源转移机制"
                ])
        
        # 添加一些通用边界情况
        edge_cases.extend([
            "极端网络条件下的概念实现",
            "大规模用户行为异常的影响",
            "技术标准不统一的兼容性问题"
        ])
        
        return edge_cases
    
    def _generate_test_cases(self, concept: str, edge_cases: List[str]) -> List[TestCase]:
        """
        生成攻击性测试用例（模拟）
        
        Args:
            concept: 概念名称
            edge_cases: 边界情况列表
            
        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        test_cases = []
        timestamp = datetime.now().isoformat()
        
        # 为每个边界情况生成测试用例
        for i, edge_case in enumerate(edge_cases[:self.max_test_cases], start=1):
            # 模拟测试用例生成逻辑
            if "服务器" in edge_case or "宕机" in edge_case:
                test_case = TestCase(
                    test_id=f"TC-{concept[:3].upper()}-{i:03d}",
                    category="技术依赖性",
                    description=f"当{edge_case}时，{concept}的基本假设是否仍然成立？",
                    expected_impact="概念的核心机制可能完全失效",
                    created_at=timestamp
                )
            elif "主权" in edge_case or "所有权" in edge_case:
                test_case = TestCase(
                    test_id=f"TC-{concept[:3].upper()}-{i:03d}",
                    category="法律与伦理",
                    description=f"在{edge_case}的情况下，现行法律框架如何适用？",
                    expected_impact="可能需要全新的法律解释或国际协定",
                    created_at=timestamp
                )
            else:
                test_case = TestCase(
                    test_id=f"TC-{concept[:3].upper()}-{i:03d}",
                    category="边界条件",
                    description=f"测试{edge_case}对{concept}的影响程度",
                    expected_impact="可能导致概念部分失效或需要重新定义",
                    created_at=timestamp
                )
            
            test_cases.append(test_case)
        
        # 添加一些特定的攻击性测试用例
        if "地缘政治" in concept:
            test_cases.append(TestCase(
                test_id=f"TC-{concept[:3].upper()}-ATK",
                category="极端攻击",
                description="若主要元宇宙平台被单一国家控制，'数字国界'是否等同于物理国界？",
                expected_impact="概念可能被政治化，失去技术中立性",
                created_at=timestamp
            ))
        
        return test_cases
    
    def export_results(self, analysis: ConceptAnalysis, format: str = "json") -> str:
        """
        导出分析结果
        
        Args:
            analysis: 分析结果对象
            format: 导出格式，支持'json'或'csv'
            
        Returns:
            str: 格式化后的结果字符串
            
        Raises:
            ValueError: 如果格式不支持
        """
        try:
            if format.lower() == "json":
                return json.dumps(asdict(analysis), indent=2, ensure_ascii=False)
            elif format.lower() == "csv":
                # 简化的CSV导出
                lines = ["test_id,category,description,expected_impact"]
                for tc in analysis.test_cases:
                    lines.append(f"{tc.test_id},{tc.category},{tc.description},{tc.expected_impact}")
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Error exporting results: {str(e)}")
            raise


def example_usage():
    """使用示例函数"""
    try:
        # 创建反向提示词工程器实例
        engineer = InversePromptEngineer(max_test_cases=8)
        
        # 分析一个概念
        concept = "元宇宙中的地缘政治"
        analysis = engineer.analyze_concept(concept)
        
        # 打印结果
        print(f"\n概念分析报告: {analysis.concept_name}")
        print(f"定义: {analysis.definition}")
        print("\n核心属性:")
        for attr in analysis.core_attributes:
            print(f"- {attr}")
        
        print("\n生成的攻击性测试用例:")
        for tc in analysis.test_cases:
            print(f"[{tc.test_id}] {tc.category}: {tc.description}")
            print(f"   预期影响: {tc.expected_impact}\n")
        
        # 导出为JSON
        json_output = engineer.export_results(analysis, "json")
        print("\nJSON输出:")
        print(json_output[:500] + "...")  # 只打印前500字符
        
    except Exception as e:
        print(f"示例运行出错: {str(e)}")


if __name__ == "__main__":
    # 运行示例
    example_usage()