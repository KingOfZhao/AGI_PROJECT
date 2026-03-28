"""
隐喻驱动的高保真代码生成架构

结合代码验证与结构映射，构建能够解析复杂隐喻需求的智能体。
该模块将用户的模糊意图通过结构映射算法转化为中间表示层（IR），
再将其转化为可执行的Python代码，并自动生成测试用例以验证隐喻逻辑。

Copyright (c) 2023 AGI System. All rights reserved.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetaphorDomain(Enum):
    """隐喻领域枚举"""
    LIBRARY = auto()
    TRANSPORTATION = auto()
    BUILDING = auto()
    COOKING = auto()
    UNKNOWN = auto()

@dataclass
class MetaphorMapping:
    """隐喻映射数据结构"""
    source_concept: str
    target_concept: str
    mapping_rules: Dict[str, str]
    validation_rules: Dict[str, List[str]]

class MetaphorParser:
    """解析隐喻表达并提取关键结构映射"""
    
    DOMAIN_PATTERNS = {
        MetaphorDomain.LIBRARY: [
            r'像管理图书馆一样管理(\w+)',
            r'像借书一样(\w+)',
            r'图书(归档|借阅|归还|丢失)'
        ],
        MetaphorDomain.TRANSPORTATION: [
            r'像(驾驶|导航|规划路线)一样(\w+)',
            r'交通(拥堵|畅通|管制)'
        ]
    }
    
    @classmethod
    def identify_domain(cls, metaphor_text: str) -> MetaphorDomain:
        """识别隐喻所属领域"""
        for domain, patterns in cls.DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, metaphor_text):
                    logger.info(f"识别到隐喻领域: {domain.name}")
                    return domain
        return MetaphorDomain.UNKNOWN
    
    @classmethod
    def extract_mapping(cls, metaphor_text: str, domain: MetaphorDomain) -> MetaphorMapping:
        """从隐喻文本中提取结构映射"""
        if domain == MetaphorDomain.LIBRARY:
            return cls._extract_library_mapping(metaphor_text)
        elif domain == MetaphorDomain.TRANSPORTATION:
            return cls._extract_transport_mapping(metaphor_text)
        else:
            raise ValueError(f"不支持的隐喻领域: {domain}")
    
    @classmethod
    def _extract_library_mapping(cls, text: str) -> MetaphorMapping:
        """提取图书馆领域隐喻映射"""
        mapping_rules = {
            "借书": "申请内存",
            "归还书籍": "释放内存",
            "图书丢失": "内存泄漏",
            "图书归档": "内存分配",
            "借阅记录": "内存日志"
        }
        
        validation_rules = {
            "借书": ["必须归还", "借阅期限检查"],
            "图书丢失": ["资源释放检查"],
            "借阅记录": ["完整性检查"]
        }
        
        return MetaphorMapping(
            source_concept="图书馆管理",
            target_concept="内存管理",
            mapping_rules=mapping_rules,
            validation_rules=validation_rules
        )
    
    @classmethod
    def _extract_transport_mapping(cls, text: str) -> MetaphorMapping:
        """提取交通领域隐喻映射"""
        mapping_rules = {
            "驾驶": "程序控制",
            "导航": "路径规划",
            "交通拥堵": "资源竞争",
            "路线规划": "算法设计"
        }
        
        validation_rules = {
            "驾驶": ["安全检查", "方向验证"],
            "导航": ["目标可达性检查"],
            "交通拥堵": ["资源使用率监控"]
        }
        
        return MetaphorMapping(
            source_concept="交通系统",
            target_concept="程序流程",
            mapping_rules=mapping_rules,
            validation_rules=validation_rules
        )

class CodeGenerator:
    """基于隐喻映射生成代码和测试用例"""
    
    @staticmethod
    def generate_code(mapping: MetaphorMapping) -> str:
        """生成Python代码"""
        if mapping.target_concept == "内存管理":
            return CodeGenerator._generate_memory_management_code(mapping)
        elif mapping.target_concept == "程序流程":
            return CodeGenerator._generate_flow_control_code(mapping)
        else:
            raise ValueError(f"不支持的目标概念: {mapping.target_concept}")
    
    @staticmethod
    def _generate_memory_management_code(mapping: MetaphorMapping) -> str:
        """生成内存管理相关代码"""
        code = f'''"""
{mapping.target_concept}模块 - 基于'{mapping.source_concept}'隐喻
自动生成于隐喻驱动架构
"""

class {mapping.target_concept.replace(" ", "_")}:
    def __init__(self):
        """初始化{mapping.target_concept}"""
        self.allocated = {{}}  # 已分配资源
        self.logs = []         # 操作日志
    
    def {mapping.mapping_rules["借书"]}(self, size: int) -> str:
        """{mapping.mapping_rules["借书"]} - 对应隐喻中的'借书'"""
        if size <= 0:
            raise ValueError("分配大小必须为正数")
        
        resource_id = f"mem_{{len(self.allocated) + 1}}"
        self.allocated[resource_id] = size
        self._log_operation("{mapping.mapping_rules["借书"]}", resource_id, size)
        return resource_id
    
    def {mapping.mapping_rules["归还书籍"]}(self, resource_id: str) -> None:
        """{mapping.mapping_rules["归还书籍"]} - 对应隐喻中的'归还书籍'"""
        if resource_id not in self.allocated:
            raise ValueError(f"无效的资源ID: {{resource_id}}")
        
        del self.allocated[resource_id]
        self._log_operation("{mapping.mapping_rules["归还书籍"]}", resource_id)
    
    def check_{mapping.mapping_rules["图书丢失"].replace(" ", "_")}(self) -> List[str]:
        """检查{mapping.mapping_rules["图书丢失"]} - 对应隐喻中的'图书丢失'"""
        leaked = [rid for rid in self.allocated if rid not in self.logs]
        if leaked:
            logger.warning(f"检测到{mapping.mapping_rules["图书丢失"]}: {{leaked}}")
        return leaked
    
    def _log_operation(self, operation: str, resource_id: str, size: int = 0) -> None:
        """记录操作日志 - 对应隐喻中的'借阅记录'"""
        entry = {{
            "operation": operation,
            "resource_id": resource_id,
            "size": size,
            "status": "completed"
        }}
        self.logs.append(entry)
        logger.info(f"操作记录: {{entry}}")
'''
        return code
    
    @staticmethod
    def _generate_flow_control_code(mapping: MetaphorMapping) -> str:
        """生成流程控制相关代码"""
        code = f'''"""
{mapping.target_concept}模块 - 基于'{mapping.source_concept}'隐喻
自动生成于隐喻驱动架构
"""

class {mapping.target_concept.replace(" ", "_")}:
    def __init__(self):
        """初始化{mapping.target_concept}"""
        self.path = []  # 执行路径
    
    def {mapping.mapping_rules["驾驶"]}(self, direction: str) -> None:
        """{mapping.mapping_rules["驾驶"]} - 对应隐喻中的'驾驶'"""
        if not direction:
            raise ValueError("方向不能为空")
        
        self.path.append(direction)
        logger.info(f"当前方向: {{direction}}")
    
    def {mapping.mapping_rules["导航"]}(self, destination: str) -> bool:
        """{mapping.mapping_rules["导航"]} - 对应隐喻中的'导航'"""
        if not destination:
            raise ValueError("目标不能为空")
        
        # 简化的导航逻辑
        reachable = destination in ["success", "end"]
        logger.info(f"目标 {{destination}} 可达: {{reachable}}")
        return reachable
    
    def check_{mapping.mapping_rules["交通拥堵"].replace(" ", "_")}(self) -> bool:
        """检查{mapping.mapping_rules["交通拥堵"]} - 对应隐喻中的'交通拥堵'"""
        is_congested = len(self.path) > 10  # 简化的拥堵检测
        if is_congested:
            logger.warning(f"检测到{mapping.mapping_rules["交通拥堵"]}")
        return is_congested
'''
        return code
    
    @staticmethod
    def generate_test_cases(mapping: MetaphorMapping) -> str:
        """生成测试用例"""
        test_code = f'''"""
{mapping.target_concept}测试用例 - 验证隐喻逻辑
自动生成于隐喻驱动架构
"""

import unittest
from generated_code import {mapping.target_concept.replace(" ", "_")}

class Test{mapping.target_concept.replace(" ", "_")}(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.manager = {mapping.target_concept.replace(" ", "_")}()
    
    def test_{mapping.mapping_rules["借书"].replace(" ", "_")}(self):
        """测试{mapping.mapping_rules["借书"]} - 对应隐喻中的'借书'"""
        resource_id = self.manager.{mapping.mapping_rules["借书"]}(1024)
        self.assertIn(resource_id, self.manager.allocated)
        self.assertEqual(len(self.manager.logs), 1)
    
    def test_{mapping.mapping_rules["归还书籍"].replace(" ", "_")}(self):
        """测试{mapping.mapping_rules["归还书籍"]} - 对应隐喻中的'归还书籍'"""
        resource_id = self.manager.{mapping.mapping_rules["借书"]}(512)
        self.manager.{mapping.mapping_rules["归还书籍"]}(resource_id)
        self.assertNotIn(resource_id, self.manager.allocated)
        self.assertEqual(len(self.manager.logs), 2)
    
    def test_{mapping.mapping_rules["图书丢失"].replace(" ", "_")}(self):
        """测试{mapping.mapping_rules["图书丢失"]}检测 - 对应隐喻中的'图书丢失'"""
        self.manager.{mapping.mapping_rules["借书"]}(2048)
        leaked = self.manager.check_{mapping.mapping_rules["图书丢失"].replace(" ", "_")}()
        self.assertEqual(len(leaked), 1)
    
    def test_invalid_operations(self):
        """测试无效操作"""
        with self.assertRaises(ValueError):
            self.manager.{mapping.mapping_rules["借书"]}(-1)
        
        with self.assertRaises(ValueError):
            self.manager.{mapping.mapping_rules["归还书籍"]}("invalid_id")

if __name__ == "__main__":
    unittest.main()
'''
        return test_code

def process_metaphor_request(metaphor_text: str) -> Tuple[str, str]:
    """
    处理隐喻驱动的代码生成请求
    
    参数:
        metaphor_text: 包含隐喻的描述文本
        
    返回:
        Tuple[生成的代码, 生成的测试用例]
        
    示例:
        >>> code, tests = process_metaphor_request("像管理图书馆一样管理内存")
        >>> print(code)  # 输出生成的内存管理代码
    """
    try:
        # 1. 识别隐喻领域
        domain = MetaphorParser.identify_domain(metaphor_text)
        if domain == MetaphorDomain.UNKNOWN:
            raise ValueError("无法识别隐喻领域")
        
        # 2. 提取隐喻映射
        mapping = MetaphorParser.extract_mapping(metaphor_text, domain)
        
        # 3. 生成代码和测试用例
        generated_code = CodeGenerator.generate_code(mapping)
        test_cases = CodeGenerator.generate_test_cases(mapping)
        
        logger.info(f"成功生成基于'{metaphor_text}'隐喻的代码和测试用例")
        return generated_code, test_cases
    
    except Exception as e:
        logger.error(f"处理隐喻请求失败: {str(e)}")
        raise

# 示例用法
if __name__ == "__main__":
    try:
        # 示例1: 内存管理隐喻
        memory_code, memory_tests = process_metaphor_request(
            "像管理图书馆一样管理内存"
        )
        print("=== 生成的内存管理代码 ===")
        print(memory_code)
        print("\n=== 生成的测试用例 ===")
        print(memory_tests)
        
        # 示例2: 流程控制隐喻
        flow_code, flow_tests = process_metaphor_request(
            "像驾驶汽车一样控制程序流程"
        )
        print("\n=== 生成的流程控制代码 ===")
        print(flow_code)
        print("\n=== 生成的测试用例 ===")
        print(flow_tests)
        
    except Exception as e:
        print(f"示例运行失败: {str(e)}")