"""
SKILL: auto_自上而下拆解_公差配合_知识的微观粒_fd1034
Description: 自上而下拆解‘公差配合’知识的微观粒度拆解与成本函数映射。
             将静态的公差标准（如ISO 286）转化为动态的、可计算的成本-良率概率图模型。
Author: AGI System
Version: 1.0.0
"""

import logging
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProcessCapability(Enum):
    """加工能力等级枚举"""
    STANDARD = "standard"   # 常规加工 Cpk ~ 1.0
    PRECISION = "precision" # 精密加工 Cpk ~ 1.33
    ULTRA = "ultra"         # 超精密加工 Cpk ~ 2.0

@dataclass
class ManufacturingResource:
    """制造资源数据结构：定义加工能力的成本模型"""
    name: str
    cpk: float                      # 制程能力指数
    base_cost: float                # 基础设置成本
    tolerance_sensitivity: float    # 公差敏感度系数 (成本随精度提高的增长率)
    measurement_error: float = 0.0  # 测量系统误差

@dataclass
class ToleranceZone:
    """公差区间数据结构"""
    nominal: float          # 公称尺寸
    upper_deviation: float  # 上偏差
    lower_deviation: float  # 下偏差
    cost_weight: float = 1.0 # 该特征对总成本的权重

    @property
    def tolerance_value(self) -> float:
        """计算公差值"""
        return abs(self.upper_deviation - self.lower_deviation)

@dataclass
class OptimizationResult:
    """优化结果输出结构"""
    recommended_tolerance: float    # 推荐公差值
    estimated_yield_rate: float     # 预估良率 (0.0 - 1.0)
    estimated_unit_cost: float      # 预估单件成本
    selected_process: str           # 选定的加工工艺名称
    risk_score: float               # 风险评分 (0-100, 越低越好)

class ToleranceCostModel:
    """
    核心类：公差成本模型与概率图映射。
    
    将传统的静态公差知识（如H7/g6）拆解为微观的：
    1. 加工能力概率分布
    2. 测量误差传递
    3. 成本非线性映射
    
    Input:
        - resources: 制造资源列表
        - target_cost: 目标成本限制
        - min_yield: 最低良率要求
    
    Output:
        - OptimizationResult: 包含最优公差、工艺和成本的综合方案
    """

    def __init__(self, resources: List[ManufacturingResource]):
        """
        初始化模型，载入供应链加工能力数据。
        
        Args:
            resources (List[ManufacturingResource]): 可用的制造资源列表
        """
        if not resources:
            raise ValueError("资源列表不能为空")
        self.resources = resources
        logger.info(f"ToleranceCostModel 初始化完成，载入 {len(resources)} 种制造资源。")

    def _calculate_process_cost(self, resource: ManufacturingResource, tolerance: float) -> float:
        """
        辅助函数：计算特定公差下的加工成本。
        
        使用非线性模型：Cost = Base + k * (1/Tolerance^alpha)
        模拟精度越高，成本指数级上升的现象。
        
        Args:
            resource (ManufacturingResource): 制造资源
            tolerance (float): 目标公差值
            
        Returns:
            float: 计算出的成本
        """
        if tolerance <= 0:
            raise ValueError("公差必须为正数")
            
        # 防止除零错误和极小值导致的数值溢出
        safe_tolerance = max(tolerance, 1e-6)
        
        # 成本指数模型
        precision_cost = resource.tolerance_sensitivity * (1 / safe_tolerance ** 1.5)
        total_cost = resource.base_cost + precision_cost
        
        logger.debug(f"Resource: {resource.name}, Tolerance: {tolerance}, Cost: {total_cost}")
        return total_cost

    def _calculate_yield_probability(self, resource: ManufacturingResource, tolerance: float) -> float:
        """
        核心函数1：计算良率概率（知识微观粒度拆解）。
        
        基于正态分布假设和 Cpk (Process Capability Index) 计算合格率。
        考虑测量误差对实际良率的影响（测量不确定度导致误判）。
        
        P(defect) 不仅仅取决于加工方差，还取决于测量系统的分辨力。
        
        Args:
            resource (ManufacturingResource): 制造资源
            tolerance (float): 规格公差宽度
            
        Returns:
            float: 良率 (0.0 - 1.0)
        """
        if tolerance <= 0: return 0.0
        
        # 有效公差：需要扣除测量误差带来的不确定性区间
        # 简化模型：测量误差占用公差带的 6*Sigma_m
        effective_tolerance = tolerance - (6 * resource.measurement_error)
        
        if effective_tolerance <= 0:
            logger.warning(f"测量误差 ({resource.measurement_error}) 超过公差带 ({tolerance})，良率将极低。")
            return 0.0

        # 计算西格玛水平
        # 假设中心偏移为 1.5 Sigma (标准工业假设)
        # Cpk = Min(USL-Mean, Mean-LSL) / 3*Sigma => 这里反推 Yield
        # 简化计算：基于 Cpk 查表或正态分布积分
        
        sigma_level = (effective_tolerance / 2) / ((tolerance / 6) / resource.cpk)
        
        # 使用标准正态分布计算 P(Z < sigma_level)
        # 这里使用 erf 近似积分
        yield_rate = 0.5 * (1 + math.erf(sigma_level / math.sqrt(2)))
        
        return min(1.0, yield_rate)

    def optimize_tolerance_schema(
        self, 
        target_dimension: ToleranceZone, 
        max_cost: float, 
        min_yield_req: float = 0.95
    ) -> OptimizationResult:
        """
        核心函数2：寻优函数 - 给定成本目标，自动生成最优公差方案。
        
        遍历公差带宽和制造资源，寻找满足成本约束和良率约束的最大公差（最宽松公差）。
        这是一个典型的约束优化问题：
        Maximize Tolerance (降低加工难度)
        Subject to: Cost <= max_cost AND Yield >= min_yield_req
        
        Args:
            target_dimension (ToleranceZone): 目标尺寸特征
            max_cost (float): 允许的最大单件成本
            min_yield_req (float): 最低良率要求
            
        Returns:
            OptimizationResult: 最优方案
        """
        logger.info(f"开始寻优: 成本上限 {max_cost}, 良率下限 {min_yield_req}")
        
        best_solution: Optional[OptimizationResult] = None
        max_found_tolerance = 0.0
        
        # 定义搜索空间：从标称尺寸的 0.01% 到 5% 范围内搜索公差值
        search_range = [target_dimension.nomual * p / 100 for p in range(1, 500, 5)]
        
        # 边界检查：如果搜索范围为空（如 nominal 为 0），使用绝对值搜索
        if not search_range or target_dimension.nomual == 0:
            search_range = [i * 0.01 for i in range(1, 100)]

        for resource in self.resources:
            for trial_tolerance in search_range:
                try:
                    # 1. 计算成本
                    cost = self._calculate_process_cost(resource, trial_tolerance)
                    if cost > max_cost:
                        continue # 成本超限，跳过
                    
                    # 2. 计算良率
                    yield_rate = self._calculate_yield_probability(resource, trial_tolerance)
                    if yield_rate < min_yield_req:
                        continue # 良率不足，跳过
                    
                    # 3. 评估是否为更优解（寻找成本允许范围内最宽松的公差，以最大化可制造性）
                    # 或者是寻找良率与成本平衡点。这里策略为：在满足约束下，寻找 Cost/Yield 比率最优
                    # 但根据描述 "给定成本目标"，主要是在成本范围内最大化鲁棒性
                    
                    if trial_tolerance > max_found_tolerance:
                        max_found_tolerance = trial_tolerance
                        risk = (1.0 - yield_rate) * 100 + (cost / max_cost * 10) # 简单风险评分
                        
                        best_solution = OptimizationResult(
                            recommended_tolerance=trial_tolerance,
                            estimated_yield_rate=yield_rate,
                            estimated_unit_cost=cost,
                            selected_process=resource.name,
                            risk_score=risk
                        )
                        
                except Exception as e:
                    logger.error(f"计算过程中出错: {e}")
                    continue

        if not best_solution:
            logger.warning("未找到满足约束的公差方案。建议放宽成本或降低良率要求。")
            # 返回一个兜底方案（最便宜的工艺的最紧公差尝试）
            # 实际生产中这里应抛出异常或返回特定的状态码
            return OptimizationResult(0, 0, 0, "No Solution", 100)

        logger.info(f"寻优完成: 推荐公差 {best_solution.recommended_tolerance}, 工艺 {best_solution.selected_process}")
        return best_solution

# ==========================================
# 使用示例与数据流演示
# ==========================================

def run_demo():
    """
    演示如何使用 ToleranceCostModel 进行公差拆解与成本映射。
    """
    # 1. 定义供应链资源数据
    # 模拟三种不同的加工供应商
    shop_standard = ManufacturingResource(
        name="Standard_CNC_Shop",
        cpk=1.0,
        base_cost=10.0,
        tolerance_sensitivity=0.5,
        measurement_error=0.005
    )
    
    shop_precision = ManufacturingResource(
        name="Precision_Grinding_Center",
        cpk=1.67,
        base_cost=50.0,
        tolerance_sensitivity=2.5,
        measurement_error=0.001
    )
    
    shop_ultra = ManufacturingResource(
        name="Ultra_Precision_Lab",
        cpk=2.0,
        base_cost=200.0,
        tolerance_sensitivity=10.0,
        measurement_error=0.0001
    )

    resources = [shop_standard, shop_precision, shop_ultra]

    # 2. 初始化模型
    model = ToleranceCostModel(resources)

    # 3. 定义设计需求
    # 假设我们需要配合一个直径 50mm 的轴
    shaft_feature = ToleranceZone(
        nominal=50.0,
        upper_deviation=0.0,
        lower_deviation=-0.1, # 初始粗略公差
        cost_weight=1.0
    )

    # 4. 场景 A: 成本敏感型 (低成本，允许一定不良率)
    print("\n--- 场景 A: 成本敏感 (Budget: 30) ---")
    result_a = model.optimize_tolerance_schema(
        target_dimension=shaft_feature,
        max_cost=30.0,
        min_yield_req=0.90
    )
    print(f"推荐方案: 公差 {result_a.recommended_tolerance:.4f}mm, "
          f"工艺: {result_a.selected_process}, "
          f"成本: ${result_a.estimated_unit_cost:.2f}, "
          f"良率: {result_a.estimated_yield_rate:.2%}")

    # 5. 场景 B: 质量敏感型 (高预算，要求高良率)
    print("\n--- 场景 B: 质量敏感 (Budget: 150) ---")
    result_b = model.optimize_tolerance_schema(
        target_dimension=shaft_feature,
        max_cost=150.0,
        min_yield_req=0.999
    )
    print(f"推荐方案: 公差 {result_b.recommended_tolerance:.4f}mm, "
          f"工艺: {result_b.selected_process}, "
          f"成本: ${result_b.estimated_unit_cost:.2f}, "
          f"良率: {result_b.estimated_yield_rate:.2%}")

if __name__ == "__main__":
    run_demo()