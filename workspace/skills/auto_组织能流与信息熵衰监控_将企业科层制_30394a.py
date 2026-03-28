"""
模块: auto_组织能流与信息熵衰监控_将企业科层制_30394a
描述: 将企业科层制视为生态食物链，利用林德曼效率模型计算信息传递损耗，
     识别组织架构中的能量泄露点，并生成优化建议。
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OrgLayer:
    """
    组织层级数据结构。
    
    Attributes:
        name (str): 层级名称 (e.g., '董事会', '高管', '经理', '员工')
        level (int): 层级深度，0为最高层 (太阳能/决策源)
        efficiency (float): 该层级的平均执行力/转化率 (0.0到1.0)
        noise_factor (float): 信息熵增因子/噪音干扰 (0.0到1.0)
    """
    name: str
    level: int
    efficiency: float = 0.8
    noise_factor: float = 0.1

    def __post_init__(self):
        if not 0 <= self.efficiency <= 1:
            raise ValueError(f"效率必须介于0和1之间，得到: {self.efficiency}")
        if not 0 <= self.noise_factor <= 1:
            raise ValueError(f"噪音因子必须介于0和1之间，得到: {self.noise_factor}")

def validate_org_structure(layers: List[OrgLayer]) -> bool:
    """
    辅助函数：验证组织架构的完整性和逻辑性。
    
    Args:
        layers (List[OrgLayer]): 组织层级列表。
        
    Returns:
        bool: 验证通过返回True。
        
    Raises:
        ValueError: 如果层级断裂或数据缺失。
    """
    if not layers:
        raise ValueError("组织架构不能为空")
    
    levels = [layer.level for layer in layers]
    expected_levels = list(range(len(layers)))
    
    if sorted(levels) != expected_levels:
        raise ValueError(f"层级必须连续且从0开始，当前层级: {levels}")
    
    logger.debug(f"组织结构验证通过，共 {len(layers)} 层")
    return True

def calculate_lindeman_transfer(
    current_layer: OrgLayer, 
    incoming_energy: float
) -> Tuple[float, float]:
    """
    核心函数：计算单个层级的林德曼效率转化与熵增。
    
    模拟生态学中的能量传递：N_t = N_{t-1} * Efficiency - Entropy。
    在企业中，这代表决策意图的保留程度。
    
    Args:
        current_layer (OrgLayer): 当前层级对象。
        incoming_energy (float): 上一层传递下来的决策能量/信息完整度。
        
    Returns:
        Tuple[float, float]: (传递给下一层的能量, 当前层级的能量损耗/熵增)
    """
    if incoming_energy < 0:
        logger.warning("检测到负能量输入，重置为0")
        incoming_energy = 0
        
    # 基础损耗：基于效率
    retained_energy = incoming_energy * current_layer.efficiency
    
    # 熵增损耗：噪音导致的额外执行偏差
    entropy_loss = retained_energy * current_layer.noise_factor
    
    final_output = max(0, retained_energy - entropy_loss)
    total_loss = incoming_energy - final_output
    
    logger.debug(
        f"层级 '{current_layer.name}' 处理: 输入={incoming_energy:.2f}, "
        f"输出={final_output:.2f}, 损耗={total_loss:.2f}"
    )
    
    return final_output, total_loss

def analyze_organization_energy_flow(
    hierarchy: List[OrgLayer], 
    initial_decision_power: float = 100.0
) -> Dict:
    """
    核心函数：分析整个组织的能流并定位泄露点。
    
    Args:
        hierarchy (List[OrgLayer]): 排序好的组织层级列表 (从高到低)。
        initial_decision_power (float): 初始决策能量值 (默认100)。
        
    Returns:
        Dict: 包含分析报告的字典。
            - 'total_efficiency': 总体系统效率
            - 'bottleneck_layer': 损耗最严重的层级名称
            - 'loss_log': 各层级损耗记录
            - 'recommendation': 优化建议
            
    Raises:
        ValueError: 输入数据校验失败时抛出。
    """
    try:
        validate_org_structure(hierarchy)
    except ValueError as e:
        logger.error(f"输入数据验证失败: {e}")
        raise

    current_energy = initial_decision_power
    total_loss = 0.0
    loss_log: Dict[str, float] = {}
    max_loss_layer = ""
    max_loss_value = -1.0

    logger.info(f"开始分析组织能流，初始能量: {initial_decision_power}")

    for i, layer in enumerate(hierarchy):
        # 顶层只有输出没有输入转化（或者说就是源头），这里简化处理，从向下一层传递开始计算
        # 或者我们将顶层视为 T0，它接收初始能量，并开始第一次转化
        
        output_energy, layer_loss = calculate_lindeman_transfer(layer, current_energy)
        
        loss_log[layer.name] = layer_loss
        total_loss += layer_loss
        
        if layer_loss > max_loss_value:
            max_loss_value = layer_loss
            max_loss_layer = layer.name
            
        current_energy = output_energy

    final_efficiency = (current_energy / initial_decision_power) * 100
    
    # 生成建议
    recommendation = generate_optimization_recommendation(
        max_loss_layer, 
        final_efficiency,
        hierarchy
    )

    report = {
        "total_system_efficiency_percent": round(final_efficiency, 2),
        "bottleneck_layer": max_loss_layer,
        "max_single_loss": round(max_loss_value, 2),
        "energy_flow_log": loss_log,
        "final_executable_energy": round(current_energy, 2),
        "recommendation": recommendation
    }

    logger.info(f"分析完成。总体效率: {final_efficiency:.2f}%, 瓶颈层级: {max_loss_layer}")
    return report

def generate_optimization_recommendation(
    bottleneck: str, 
    efficiency: float,
    layers: List[OrgLayer]
) -> str:
    """
    辅助函数：根据分析结果生成组织架构优化建议。
    
    Args:
        bottleneck (str): 瓶颈层级名称。
        efficiency (float): 总体效率。
        layers (List[OrgLayer]): 层级列表。
        
    Returns:
        str: 优化建议文本。
    """
    if efficiency > 80:
        return "组织能流极其健康，维持现状即可。"
    elif efficiency > 50:
        return f"组织运作一般。建议关注 '{bottleneck}' 层级的信息传导机制，减少冗余流程。"
    else:
        # 模拟向"食物网"（扁平化/网络化）转型的建议
        return (f"警告：严重能量泄露于 '{bottleneck}'。"
                f"建议削减该层级或推行扁平化，将线性链条转变为网状结构，"
                f"使基层直接获取高层'太阳能'（决策信息）。")

# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    # 构建一个模拟的科层制企业
    # 0: 董事会 (决策源, 效率高)
    # 1: 高管 (VP, 效率中上, 噪音低)
    # 2: 中层管理 (Director/Manager, 效率中, 噪音高 - 典型的熵增点)
    # 3: 基层主管 (Supervisor, 效率中下)
    # 4: 一线员工 (Execution, 效率波动)
    
    company_structure = [
        OrgLayer(name="董事会", level=0, efficiency=0.95, noise_factor=0.02),
        OrgLayer(name="高管团队", level=1, efficiency=0.85, noise_factor=0.05),
        OrgLayer(name="中层管理", level=2, efficiency=0.60, noise_factor=0.25), # 瓶颈点
        OrgLayer(name="基层主管", level=3, efficiency=0.75, noise_factor=0.10),
        OrgLayer(name="一线员工", level=4, efficiency=0.80, noise_factor=0.05),
    ]

    print("--- 启动组织能流监控 ---")
    try:
        report = analyze_organization_energy_flow(company_structure)
        
        print("\n[监控报告]")
        print(f"总体执行力留存率: {report['total_system_efficiency_percent']}%")
        print(f"能量泄露瓶颈层级: {report['bottleneck_layer']}")
        print("各层级损耗详情:")
        for layer, loss in report['energy_flow_log'].items():
            print(f"  - {layer}: {loss:.2f} 单位损耗")
        print(f"\n[系统建议]: {report['recommendation']}")
        
    except Exception as e:
        logger.error(f"运行时发生错误: {e}")