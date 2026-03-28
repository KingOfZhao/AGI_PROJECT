"""
产业代谢与价值循环引擎 (Industrial Metabolism and Value Cycle Engine)

该模块基于生态系统能量流动原理，模拟和分析经济系统的代谢过程。
它将企业视为生态有机体，分析其“价值营养级”，识别“呼吸消耗”（无效损耗）
与“次级生产”（有效产出）。通过引入“分解者”机制，旨在将废料转化为资源，
推动经济系统从线性增长向螺旋上升的循环经济范式转移。

核心概念：
- 呼吸消耗: 企业运营过程中的非生产性成本和损耗。
- 次级生产: 扣除消耗后的净价值增值。
- 分解者: 能够回收系统废料并将其转化为可用资源的经济实体。
- 螺旋指数: 衡量系统通过循环利用实现价值增值倍数的指标。

输入格式说明:
    输入为 EconomicEntity 对象的列表，每个对象代表一个企业或部门。
    - input_resources: 输入资源总量 (float, >= 0)
    - output_value: 总产出价值 (float, >= 0)
    - respiration_cost: 运营/呼吸消耗 (float, >= 0)
    - waste_output: 产生的废料/未利用资源 (float, >= 0)

输出格式说明:
    字典结构，包含系统级指标和各实体的详细分析数据。
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Literal
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialMetabolismEngine")


@dataclass
class EconomicEntity:
    """代表经济系统中的一个实体（如企业、部门）。"""
    id: str
    name: str
    input_resources: float
    output_value: float
    respiration_cost: float  # 呼吸消耗
    waste_output: float      # 待处理的废料

    def __post_init__(self):
        """初始化后的基本验证。"""
        if self.input_resources < 0 or self.output_value < 0 or \
           self.respiration_cost < 0 or self.waste_output < 0:
            raise ValueError("所有数值字段必须为非负数。")


class IndustrialMetabolismEngine:
    """
    产业代谢与价值循环引擎。
    
    融合生态系统能量流动模型，分析经济代谢效率，并模拟通过引入
    分解者机制实现价值循环的过程。
    """

    def __init__(self, decomposition_efficiency: float = 0.6):
        """
        初始化引擎。
        
        Args:
            decomposition_efficiency: 分解者将废料转化为新资源的效率系数 (0.0 - 1.0)。
        """
        self._validate_efficiency(decomposition_efficiency)
        self.decomposition_efficiency = decomposition_efficiency

    @staticmethod
    def _validate_efficiency(value: float) -> None:
        """验证效率系数是否在有效范围内。"""
        if not 0.0 <= value <= 1.0:
            raise ValueError("分解效率必须在 0.0 到 1.0 之间")

    def _calculate_entity_metrics(self, entity: EconomicEntity) -> Dict[str, float]:
        """
        辅助函数：计算单个实体的生态学指标。
        
        Args:
            entity: 经济实体对象
            
        Returns:
            包含次级生产、生态效率等指标的字典
        """
        # 次级生产 = 总产出 - 呼吸消耗
        secondary_production = entity.output_value - entity.respiration_cost
        
        # 生态效率 = 次级生产 / 输入资源
        # 避免除以零
        efficiency = 0.0
        if entity.input_resources > 0:
            efficiency = secondary_production / entity.input_resources
            
        # 废料率
        waste_ratio = 0.0
        if entity.output_value > 0:
            waste_ratio = entity.waste_output / entity.output_value

        return {
            "secondary_production": secondary_production,
            "ecological_efficiency": efficiency,
            "waste_ratio": waste_ratio
        }

    def analyze_trophic_levels(self, entities: List[EconomicEntity]) -> List[Dict]:
        """
        核心函数 1：分析经济实体的价值营养级。
        
        根据生态效率和废料产生量，将实体分类为：
        - 'Producer' (生产者): 高效率，低废料
        - 'Consumer' (消费者): 中等效率
        - 'Potential_Decomposer' (潜在分解者): 低效率，高废料（尾部企业）
        
        Args:
            entities: 经济实体列表
            
        Returns:
            包含每个实体分析结果的字典列表
        """
        logger.info(f"开始分析 {len(entities)} 个实体的价值营养级...")
        analysis_results = []

        for entity in entities:
            try:
                metrics = self._calculate_entity_metrics(entity)
                
                # 营养级分类逻辑
                role: Literal['Producer', 'Consumer', 'Potential_Decomposer']
                if metrics['ecological_efficiency'] > 0.5 and metrics['waste_ratio'] < 0.2:
                    role = 'Producer'
                elif metrics['ecological_efficiency'] < 0.1 or metrics['waste_ratio'] > 0.5:
                    role = 'Potential_Decomposer'
                else:
                    role = 'Consumer'

                result = {
                    "id": entity.id,
                    "name": entity.name,
                    "role": role,
                    "metrics": metrics
                }
                analysis_results.append(result)
                
            except Exception as e:
                logger.error(f"分析实体 {entity.id} 时出错: {e}")
                continue

        return analysis_results

    def optimize_value_cycle(self, entities: List[EconomicEntity]) -> Dict:
        """
        核心函数 2：模拟价值循环优化与范式转移。
        
        识别系统中的废料，利用“潜在分解者”将其转化为新资源，
        计算系统从线性模式转向螺旋模式后的价值增益。
        
        Args:
            entities: 经济实体列表
            
        Returns:
            包含系统总价值、循环增益、螺旋指数的字典
        """
        logger.info("启动价值循环优化模拟...")
        
        total_system_waste = 0.0
        total_system_value = 0.0
        decomposer_capacity = 0.0

        # 1. 扫描系统状态
        for entity in entities:
            total_system_value += entity.output_value
            total_system_waste += entity.waste_output
            
            # 简单假设：潜在分解者的处理能力与其输入规模成正比
            # 在实际应用中，这里可以更复杂
            metrics = self._calculate_entity_metrics(entity)
            if metrics['ecological_efficiency'] < 0.2: # 识别为低效/尾部企业
                decomposer_capacity += entity.input_resources * 0.5 

        # 2. 模拟分解过程
        # 实际可处理的废料量受限于分解者容量和总废料量
        processable_waste = min(total_system_waste, decomposer_capacity)
        
        # 转化出的新资源价值
        recycled_value = processable_waste * self.decomposition_efficiency
        
        # 3. 计算螺旋上升指标
        # 螺旋指数 = (原始价值 + 循环增值) / 原始价值
        # 如果指数 > 1，说明实现了螺旋上升（价值增长）
        spiral_index = 1.0
        if total_system_value > 0:
            spiral_index = (total_system_value + recycled_value) / total_system_value
        
        # 4. 范式转移评估
        paradigm_shift = "Linear (Stagnant)"
        if spiral_index > 1.05:
            paradigm_shift = "Spiral (Growth)"
        elif spiral_index > 1.01:
            paradigm_shift = "Transitioning"

        return {
            "total_system_output": total_system_value,
            "total_system_waste": total_system_waste,
            "recycled_value_potential": recycled_value,
            "spiral_index": spiral_index,
            "paradigm_status": paradigm_shift,
            "waste_recovery_rate": (processable_waste / total_system_waste) if total_system_waste > 0 else 0
        }


# 使用示例
if __name__ == "__main__":
    # 创建模拟经济实体
    # 实体A: 高效生产者 (类似植物)
    entity_a = EconomicEntity(
        id="E001", name="GreenTech Manufacturer",
        input_resources=1000.0, output_value=2500.0,
        respiration_cost=800.0, waste_output=100.0
    )
    
    # 实体B: 普通消费者 (类似食草动物)
    entity_b = EconomicEntity(
        id="E002", name="Standard Assembly",
        input_resources=1500.0, output_value=2000.0,
        respiration_cost=1200.0, waste_output=300.0
    )
    
    # 实体C: 尾部企业/潜在分解者 (高废料，低效)
    entity_c = EconomicEntity(
        id="E003", name="Heavy Industry Legacy",
        input_resources=2000.0, output_value=2200.0,
        respiration_cost=1800.0, waste_output=800.0
    )

    ecosystem = [entity_a, entity_b, entity_c]

    # 初始化引擎
    engine = IndustrialMetabolismEngine(decomposition_efficiency=0.75)

    # 1. 分析营养级
    trophic_analysis = engine.analyze_trophic_levels(ecosystem)
    print("\n--- 价值营养级分析 ---")
    for item in trophic_analysis:
        print(f"ID: {item['id']} ({item['name']})")
        print(f"  角色: {item['role']}")
        print(f"  生态效率: {item['metrics']['ecological_efficiency']:.2f}")
        print(f"  废料率: {item['metrics']['waste_ratio']:.2f}")

    # 2. 优化价值循环
    cycle_metrics = engine.optimize_value_cycle(ecosystem)
    print("\n--- 价值循环优化结果 ---")
    print(f"系统总产出: {cycle_metrics['total_system_output']:.2f}")
    print(f"系统总废料: {cycle_metrics['total_system_waste']:.2f}")
    print(f"潜在循环价值: {cycle_metrics['recycled_value_potential']:.2f}")
    print(f"螺旋指数: {cycle_metrics['spiral_index']:.4f}")
    print(f"范式状态: {cycle_metrics['paradigm_status']}")