"""
异构创新雷达 - 跨行业技能映射引擎

该模块实现了一个跨行业创新映射系统，当用户在特定行业遇到瓶颈时，
系统会检索结构相似但领域不同的案例，通过提取解构骨架并强制映射，
激发非线性的创新解决方案。

核心功能:
1. 分析用户瓶颈场景的结构特征
2. 在异构领域库中检索结构相似的案例
3. 提取解决方案骨架并映射到用户场景

使用示例:
>>> radar = HeterogeneousRadar()
>>> result = radar.innovate("餐饮", "高峰期出餐慢")
>>> print(result['mapped_solutions'][0])
{
    "source_domain": "F1赛车进站策略",
    "skeleton": ["流程优化", "并行处理"],
    "application": "建立标准化备餐流程，实现多工位并行作业..."
}
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import math
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HeterogeneousRadar")


class DomainCategory(Enum):
    """行业领域分类"""
    CATERING = "餐饮"
    MANUFACTURING = "制造业"
    SPORTS = "体育"
    LOGISTICS = "物流"
    HEALTHCARE = "医疗"
    TECHNOLOGY = "科技"
    MILITARY = "军事"


@dataclass
class ProblemScenario:
    """问题场景数据结构"""
    domain: str
    problem: str
    features: Dict[str, float]  # 特征向量: {"time_pressure": 0.8, "complexity": 0.6}
    constraints: List[str]


@dataclass
class SolutionSkeleton:
    """解决方案骨架"""
    source_domain: str
    source_case: str
    skeleton: List[str]  # 解构骨架元素
    effectiveness: float  # 历史有效性评分 (0-1)
    implementation_steps: List[str]


class HeterogeneousRadar:
    """
    异构创新雷达引擎
    
    通过跨领域结构相似性检索，将异构行业的解决方案映射到用户问题场景。
    """
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化异构创新雷达
        
        Args:
            knowledge_base_path: 知识库JSON文件路径，如未提供则使用内置示例数据
        """
        self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
        self.domain_similarity_matrix = self._build_domain_similarity_matrix()
        logger.info("HeterogeneousRadar initialized with %d cases", len(self.knowledge_base))
    
    def _load_knowledge_base(self, path: Optional[str]) -> List[Dict]:
        """
        加载跨行业知识库
        
        Args:
            path: 知识库文件路径
            
        Returns:
            知识库案例列表
            
        Raises:
            FileNotFoundError: 当文件路径无效时
            json.JSONDecodeError: 当JSON格式错误时
        """
        default_knowledge = [
            {
                "domain": "制造业",
                "case": "丰田精益生产",
                "problem": "生产瓶颈导致交付延迟",
                "features": {"time_pressure": 0.9, "complexity": 0.7, "resource_constraint": 0.8},
                "skeleton": ["流程优化", "并行处理", "标准化作业"],
                "effectiveness": 0.95,
                "steps": ["识别价值流", "消除浪费", "建立拉动系统"]
            },
            {
                "domain": "体育",
                "case": "F1赛车进站策略",
                "problem": "比赛时间损失",
                "features": {"time_pressure": 0.95, "complexity": 0.8, "resource_constraint": 0.6},
                "skeleton": ["精确分工", "并行处理", "预演训练"],
                "effectiveness": 0.9,
                "steps": ["角色明确化", "动作标准化", "同步协调训练"]
            },
            {
                "domain": "医疗",
                "case": "急诊室分流系统",
                "problem": "患者等待时间过长",
                "features": {"time_pressure": 0.85, "complexity": 0.9, "resource_constraint": 0.7},
                "skeleton": ["优先级分类", "资源动态分配", "流程简化"],
                "effectiveness": 0.88,
                "steps": ["实施检伤分类", "建立快速通道", "动态调整人员"]
            },
            {
                "domain": "物流",
                "case": "亚马逊仓储优化",
                "problem": "订单处理效率低",
                "features": {"time_pressure": 0.8, "complexity": 0.6, "resource_constraint": 0.75},
                "skeleton": ["算法优化", "路径规划", "自动化处理"],
                "effectiveness": 0.92,
                "steps": ["实施Kiva机器人", "优化拣货路径", "预测性库存放置"]
            }
        ]
        
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Loaded knowledge base from %s", path)
                    return data
            except FileNotFoundError:
                logger.error("Knowledge base file not found: %s", path)
                raise
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON format in knowledge base: %s", e)
                raise
        
        return default_knowledge
    
    def _build_domain_similarity_matrix(self) -> Dict[Tuple[str, str], float]:
        """
        构建领域相似度矩阵
        
        Returns:
            领域相似度字典，键为(domain1, domain2)元组，值为相似度(0-1)
        """
        domains = set(case["domain"] for case in self.knowledge_base)
        matrix = {}
        
        # 预定义领域相似度 (可以根据业务需求扩展)
        similarity_rules = {
            ("餐饮", "制造业"): 0.3,
            ("餐饮", "体育"): 0.2,
            ("餐饮", "医疗"): 0.4,
            ("餐饮", "物流"): 0.35,
            ("制造业", "体育"): 0.25,
            ("制造业", "医疗"): 0.45,
            ("制造业", "物流"): 0.6,
            ("体育", "医疗"): 0.3,
            ("体育", "物流"): 0.2,
            ("医疗", "物流"): 0.5
        }
        
        for d1 in domains:
            for d2 in domains:
                if d1 == d2:
                    matrix[(d1, d2)] = 1.0
                else:
                    key = tuple(sorted((d1, d2)))
                    matrix[(d1, d2)] = similarity_rules.get(key, 0.1)
        
        return matrix
    
    def analyze_problem(self, domain: str, problem: str) -> ProblemScenario:
        """
        分析用户问题场景并提取特征
        
        Args:
            domain: 问题所在行业领域
            problem: 问题描述
            
        Returns:
            ProblemScenario对象，包含提取的特征和约束
            
        Raises:
            ValueError: 当输入参数无效时
        """
        if not domain or not isinstance(domain, str):
            raise ValueError("Domain must be a non-empty string")
        if not problem or not isinstance(problem, str):
            raise ValueError("Problem must be a non-empty string")
        
        logger.info("Analyzing problem: %s in domain: %s", problem, domain)
        
        # 特征提取 (简化版，实际应用中可以使用NLP模型)
        features = {
            "time_pressure": self._estimate_time_pressure(problem),
            "complexity": self._estimate_complexity(problem),
            "resource_constraint": self._estimate_resource_constraint(problem)
        }
        
        # 约束提取 (简化版)
        constraints = []
        if "成本" in problem or "预算" in problem:
            constraints.append("成本敏感")
        if "质量" in problem:
            constraints.append("质量要求高")
        
        return ProblemScenario(
            domain=domain,
            problem=problem,
            features=features,
            constraints=constraints
        )
    
    def _estimate_time_pressure(self, problem: str) -> float:
        """估算时间压力特征"""
        time_keywords = ["慢", "延迟", "等待", "高峰", "紧急"]
        score = sum(0.2 for kw in time_keywords if kw in problem)
        return min(max(score, 0.1), 0.95)  # 确保在合理范围内
    
    def _estimate_complexity(self, problem: str) -> float:
        """估算复杂性特征"""
        complexity_keywords = ["复杂", "多步骤", "协调", "混乱"]
        score = sum(0.15 for kw in complexity_keywords if kw in problem)
        return min(max(score + 0.3, 0.2), 0.9)
    
    def _estimate_resource_constraint(self, problem: str) -> float:
        """估算资源约束特征"""
        resource_keywords = ["不足", "缺乏", "有限", "短缺"]
        score = sum(0.2 for kw in resource_keywords if kw in problem)
        return min(max(score + 0.3, 0.1), 0.85)
    
    def retrieve_heterogeneous_cases(
        self, 
        scenario: ProblemScenario, 
        top_k: int = 3
    ) -> List[Tuple[Dict, float]]:
        """
        检索异构领域案例
        
        Args:
            scenario: 用户问题场景
            top_k: 返回的最相似案例数量
            
        Returns:
            元组列表，每个元组包含案例字典和相似度分数
            
        Raises:
            ValueError: 当top_k小于1时
        """
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        
        logger.info("Retrieving heterogeneous cases for domain: %s", scenario.domain)
        
        similarities = []
        
        for case in self.knowledge_base:
            # 跳过同领域案例
            if case["domain"] == scenario.domain:
                continue
                
            # 计算特征相似度
            feature_sim = self._calculate_feature_similarity(
                scenario.features, case["features"]
            )
            
            # 计算领域距离 (使用1-相似度来表示距离)
            domain_distance = 1 - self.domain_similarity_matrix.get(
                (scenario.domain, case["domain"]), 0.1
            )
            
            # 综合分数: 平衡特征相似度和领域距离
            # 我们希望特征相似但领域不同
            combined_score = feature_sim * domain_distance
            
            similarities.append((case, combined_score))
        
        # 按综合分数降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def _calculate_feature_similarity(
        self, 
        features1: Dict[str, float], 
        features2: Dict[str, float]
    ) -> float:
        """
        计算两个特征向量之间的余弦相似度
        
        Args:
            features1: 第一个特征向量
            features2: 第二个特征向量
            
        Returns:
            余弦相似度分数 (0-1)
        """
        # 获取所有特征键
        all_keys = set(features1.keys()).union(set(features2.keys()))
        
        # 构建向量
        vec1 = [features1.get(k, 0.0) for k in all_keys]
        vec2 = [features2.get(k, 0.0) for k in all_keys]
        
        # 计算点积和模
        dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
        norm1 = math.sqrt(sum(v ** 2 for v in vec1))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def map_solution(
        self, 
        scenario: ProblemScenario, 
        source_case: Dict
    ) -> Dict[str, str]:
        """
        将解决方案骨架映射到用户场景
        
        Args:
            scenario: 用户问题场景
            source_case: 源案例字典
            
        Returns:
            包含映射解决方案的字典
        """
        logger.info(
            "Mapping solution from %s to %s", 
            source_case["domain"], 
            scenario.domain
        )
        
        # 提取骨架元素
        skeleton = source_case["skeleton"]
        
        # 生成应用建议 (简化版，实际应用中可以使用模板或生成模型)
        applications = []
        for element in skeleton:
            if element == "流程优化":
                applications.append(
                    f"在{scenario.domain}场景中，重新设计核心流程，消除非必要步骤"
                )
            elif element == "并行处理":
                applications.append(
                    f"在{scenario.domain}场景中，识别可并行的任务，实施同步作业"
                )
            elif element == "标准化作业":
                applications.append(
                    f"在{scenario.domain}场景中，制定标准操作程序(SOP)，减少变异"
                )
            elif element == "精确分工":
                applications.append(
                    f"在{scenario.domain}场景中，明确角色职责，专业化分工"
                )
            elif element == "预演训练":
                applications.append(
                    f"在{scenario.domain}场景中，进行场景模拟训练，提高熟练度"
                )
            else:
                applications.append(
                    f"在{scenario.domain}场景中，应用{element}原则"
                )
        
        return {
            "source_domain": source_case["domain"],
            "source_case": source_case["case"],
            "skeleton": skeleton,
            "application": "；".join(applications),
            "implementation_hints": source_case["steps"]
        }
    
    def innovate(
        self, 
        domain: str, 
        problem: str, 
        top_k: int = 3
    ) -> Dict[str, List]:
        """
        完整的创新流程：分析问题、检索异构案例、映射解决方案
        
        Args:
            domain: 问题所在行业领域
            problem: 问题描述
            top_k: 返回的解决方案数量
            
        Returns:
            包含异构创新解决方案的字典
            
        Example:
            >>> radar = HeterogeneousRadar()
            >>> result = radar.innovate("餐饮", "高峰期出餐慢")
            >>> print(result["mapped_solutions"][0]["source_domain"])
            "制造业"
        """
        logger.info("Starting innovation process for %s: %s", domain, problem)
        
        try:
            # 1. 分析问题场景
            scenario = self.analyze_problem(domain, problem)
            
            # 2. 检索异构案例
            heterogeneous_cases = self.retrieve_heterogeneous_cases(scenario, top_k)
            
            # 3. 映射解决方案
            mapped_solutions = []
            for case, score in heterogeneous_cases:
                solution = self.map_solution(scenario, case)
                solution["similarity_score"] = round(score, 3)
                mapped_solutions.append(solution)
            
            return {
                "original_problem": problem,
                "original_domain": domain,
                "analyzed_features": scenario.features,
                "mapped_solutions": mapped_solutions,
                "status": "success"
            }
            
        except Exception as e:
            logger.error("Error in innovation process: %s", str(e))
            return {
                "original_problem": problem,
                "original_domain": domain,
                "error": str(e),
                "status": "failed"
            }


# 使用示例
if __name__ == "__main__":
    # 初始化异构创新雷达
    radar = HeterogeneousRadar()
    
    # 示例1: 餐饮行业问题
    print("\n=== 餐饮行业创新方案 ===")
    result1 = radar.innovate("餐饮", "高峰期出餐慢，顾客等待时间长")
    for i, solution in enumerate(result1.get("mapped_solutions", []), 1):
        print(f"\n方案 {i}: 来自 {solution['source_domain']} - {solution['source_case']}")
        print(f"相似度分数: {solution['similarity_score']}")
        print(f"核心原则: {', '.join(solution['skeleton'])}")
        print(f"应用建议: {solution['application']}")
    
    # 示例2: 科技行业问题
    print("\n\n=== 科技行业创新方案 ===")
    result2 = radar.innovate("科技", "软件开发周期长，需求变更频繁")
    for i, solution in enumerate(result2.get("mapped_solutions", []), 1):
        print(f"\n方案 {i}: 来自 {solution['source_domain']} - {solution['source_case']}")
        print(f"相似度分数: {solution['similarity_score']}")
        print(f"核心原则: {', '.join(solution['skeleton'])}")
        print(f"应用建议: {solution['application']}")