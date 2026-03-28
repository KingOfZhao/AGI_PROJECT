"""
高级Python模块：自动化反事实数据增强

该模块实现了针对AGI技能节点的自动化反事实数据增强功能。
通过生成带有虚假前提的样本，测试系统技能调用的鲁棒性。

核心功能：
1. 加载现有技能节点数据
2. 生成反事实样本
3. 执行压力测试并生成报告
"""

import json
import logging
import random
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('counterfactual_augmentation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 常量定义
MAX_SKILL_NODES = 1497
MIN_CONFIDENCE_THRESHOLD = 0.7
COUNTERFACTUAL_TEMPLATES = [
    "使用{material}作为{ingredient}的替代品",
    "在{condition}条件下执行{action}",
    "假设{premise}，如何{task}",
    "当{variable}为{value}时，{consequence}"
]

@dataclass
class SkillNode:
    """技能节点数据结构"""
    id: str
    name: str
    description: str
    category: str
    dependencies: List[str]
    metadata: Dict

    @classmethod
    def from_dict(cls, data: Dict) -> 'SkillNode':
        """从字典创建技能节点实例"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            dependencies=data.get('dependencies', []),
            metadata=data.get('metadata', {})
        )

class CounterfactualGenerator:
    """反事实样本生成器"""
    
    def __init__(self, template_file: Optional[str] = None):
        """
        初始化生成器
        
        Args:
            template_file: 自定义模板文件路径
        """
        self.templates = COUNTERFACTUAL_TEMPLATES
        if template_file:
            self._load_custom_templates(template_file)
        logger.info(f"CounterfactualGenerator initialized with {len(self.templates)} templates")
    
    def _load_custom_templates(self, file_path: str) -> None:
        """加载自定义模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                custom_templates = json.load(f)
                if isinstance(custom_templates, list):
                    self.templates.extend(custom_templates)
                    logger.info(f"Loaded {len(custom_templates)} custom templates")
        except Exception as e:
            logger.error(f"Failed to load custom templates: {e}")
    
    def generate_sample(self, skill: SkillNode) -> Dict:
        """
        为技能节点生成反事实样本
        
        Args:
            skill: 技能节点对象
            
        Returns:
            包含反事实样本的字典
        """
        if not self._validate_skill(skill):
            raise ValueError(f"Invalid skill node: {skill.id}")
        
        template = random.choice(self.templates)
        
        # 生成虚假前提的材料
        materials = ["生铁", "塑料", "云朵", "梦境", "时间碎片", "量子泡沫"]
        conditions = ["真空", "零重力", "极端高温", "绝对零度", "强磁场"]
        
        # 填充模板
        sample = {
            "skill_id": skill.id,
            "original_skill": skill.name,
            "counterfactual_text": template.format(
                material=random.choice(materials),
                ingredient=skill.name.split()[0] if ' ' in skill.name else skill.name,
                condition=random.choice(conditions),
                action=skill.name,
                premise=f"{skill.name}不需要任何工具",
                task=skill.name,
                variable="环境参数",
                value="异常值",
                consequence="系统崩溃"
            ),
            "timestamp": datetime.now().isoformat(),
            "hash": hashlib.md5((skill.id + template).encode()).hexdigest()
        }
        
        return sample
    
    def _validate_skill(self, skill: SkillNode) -> bool:
        """验证技能节点有效性"""
        if not skill.id or not skill.name:
            return False
        return True

class SkillNodeTester:
    """技能节点压力测试器"""
    
    def __init__(self, confidence_threshold: float = MIN_CONFIDENCE_THRESHOLD):
        """
        初始化测试器
        
        Args:
            confidence_threshold: 置信度阈值
        """
        self.confidence_threshold = confidence_threshold
        self.test_results = []
        logger.info(f"SkillNodeTester initialized with threshold {confidence_threshold}")
    
    def test_skill_invocation(self, skill: SkillNode, counterfactual: Dict) -> Dict:
        """
        测试技能调用
        
        Args:
            skill: 技能节点
            counterfactual: 反事实样本
            
        Returns:
            测试结果字典
        """
        # 模拟系统响应 - 在实际应用中这里会调用真实的技能系统
        mock_response = self._mock_system_response(skill, counterfactual)
        
        result = {
            "skill_id": skill.id,
            "counterfactual_hash": counterfactual["hash"],
            "passed": mock_response["confidence"] < self.confidence_threshold,
            "confidence": mock_response["confidence"],
            "invoked": mock_response["invoked"],
            "details": mock_response["details"],
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        return result
    
    def _mock_system_response(self, skill: SkillNode, counterfactual: Dict) -> Dict:
        """
        模拟系统响应 (实际应用中替换为真实系统调用)
        
        Args:
            skill: 技能节点
            counterfactual: 反事实样本
            
        Returns:
            模拟的系统响应
        """
        # 这里模拟一个简单的响应逻辑
        # 实际应用中应该调用真实的技能系统
        
        # 检查反事实文本中是否包含技能关键词
        invoked = any(keyword in counterfactual["counterfactual_text"] 
                     for keyword in skill.name.split())
        
        # 计算模拟的置信度
        base_confidence = random.uniform(0.4, 0.95)
        if invoked:
            confidence = min(1.0, base_confidence + 0.2)
        else:
            confidence = max(0.0, base_confidence - 0.3)
        
        return {
            "invoked": invoked,
            "confidence": confidence,
            "details": {
                "matched_keywords": [kw for kw in skill.name.split() 
                                    if kw in counterfactual["counterfactual_text"]],
                "response_time": random.uniform(0.01, 0.5)
            }
        }
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        if not self.test_results:
            logger.warning("No test results available for report generation")
            return {}
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "avg_confidence": sum(r["confidence"] for r in self.test_results) / total_tests
            },
            "details": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return report

def load_skill_nodes(file_path: str) -> List[SkillNode]:
    """
    加载技能节点数据
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        技能节点列表
        
    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON解析错误
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            raise ValueError("Invalid skill nodes data format, expected list")
            
        skill_nodes = [SkillNode.from_dict(item) for item in data]
        
        if len(skill_nodes) > MAX_SKILL_NODES:
            logger.warning(f"Loaded {len(skill_nodes)} nodes, but max allowed is {MAX_SKILL_NODES}")
            skill_nodes = skill_nodes[:MAX_SKILL_NODES]
            
        logger.info(f"Successfully loaded {len(skill_nodes)} skill nodes")
        return skill_nodes
        
    except FileNotFoundError as e:
        logger.error(f"Skill nodes file not found: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in skill nodes file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading skill nodes: {e}")
        raise

def save_report(report: Dict, output_path: str) -> None:
    """
    保存测试报告
    
    Args:
        report: 测试报告字典
        output_path: 输出文件路径
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        raise

def run_counterfactual_tests(
    skill_nodes: List[SkillNode],
    output_file: str = "counterfactual_report.json"
) -> Dict:
    """
    执行完整的反事实测试流程
    
    Args:
        skill_nodes: 技能节点列表
        output_file: 报告输出文件路径
        
    Returns:
        测试报告字典
        
    Example:
        >>> skills = load_skill_nodes("skills.json")
        >>> report = run_counterfactual_tests(skills, "test_report.json")
        >>> print(f"Pass rate: {report['summary']['pass_rate']:.2%}")
    """
    if not skill_nodes:
        logger.error("No skill nodes provided for testing")
        return {}
    
    generator = CounterfactualGenerator()
    tester = SkillNodeTester()
    
    logger.info(f"Starting counterfactual tests for {len(skill_nodes)} skills")
    
    for skill in skill_nodes:
        try:
            # 生成反事实样本
            counterfactual = generator.generate_sample(skill)
            
            # 执行测试
            tester.test_skill_invocation(skill, counterfactual)
            
        except Exception as e:
            logger.error(f"Failed to test skill {skill.id}: {e}")
            continue
    
    # 生成并保存报告
    report = tester.generate_report()
    save_report(report, output_file)
    
    return report

if __name__ == "__main__":
    # 示例用法
    try:
        # 1. 加载技能节点 (这里使用模拟数据)
        mock_skills = [
            {
                "id": "skill_001",
                "name": "番茄炒蛋",
                "description": "制作番茄炒蛋的技能",
                "category": "cooking",
                "dependencies": [],
                "metadata": {"difficulty": "easy"}
            },
            {
                "id": "skill_002",
                "name": "更换轮胎",
                "description": "汽车轮胎更换技能",
                "category": "automotive",
                "dependencies": ["jack", "wrench"],
                "metadata": {"difficulty": "medium"}
            }
        ]
        
        # 转换为SkillNode对象
        skill_nodes = [SkillNode.from_dict(s) for s in mock_skills]
        
        # 2. 执行反事实测试
        report = run_counterfactual_tests(skill_nodes, "example_report.json")
        
        # 3. 打印结果摘要
        print("\nTest Summary:")
        print(f"Total tests: {report['summary']['total_tests']}")
        print(f"Passed tests: {report['summary']['passed_tests']}")
        print(f"Pass rate: {report['summary']['pass_rate']:.1%}")
        print(f"Average confidence: {report['summary']['avg_confidence']:.2f}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")