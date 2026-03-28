"""
Module: auto_融合_物理沙箱_极端工况生成_与_双_6a1334
Description: 融合物理沙箱、极端工况生成与双向转译引擎。
             实现意图到物理现实的零距离验证，支持抗震建筑等场景的自动化仿真分析。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import random
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('physics_sandbox.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class StructureType(Enum):
    """建筑结构类型枚举"""
    REINFORCED_CONCRETE = "reinforced_concrete"
    STEEL_FRAME = "steel_frame"
    WOOD_FRAME = "wood_frame"
    MASONRY = "masonry"


class FailureMode(Enum):
    """失效模式枚举"""
    SHEAR_FAILURE = "shear_failure"
    BENDING_FAILURE = "bending_failure"
    FOUNDATION_SETTLEMENT = "foundation_settlement"
    RESONANCE_COLLAPSE = "resonance_collapse"
    NONE = "none"


@dataclass
class StructureSpec:
    """建筑结构规格数据模型"""
    name: str
    structure_type: StructureType
    height_meters: float
    width_meters: float
    floors: int
    damping_ratio: float = 0.05
    natural_frequency_hz: float = 1.0
    
    def __post_init__(self):
        """数据验证"""
        if self.height_meters <= 0 or self.width_meters <= 0:
            raise ValueError("建筑尺寸必须为正数")
        if self.floors <= 0:
            raise ValueError("楼层数必须为正整数")
        if not 0 < self.damping_ratio < 1:
            raise ValueError("阻尼比必须在0和1之间")


@dataclass
class EarthquakeScenario:
    """地震工况数据模型"""
    magnitude: float  # 里氏震级
    peak_ground_acceleration: float  # 峰值地面加速度 (g)
    dominant_frequency: float  # 主频 (Hz)
    duration_seconds: float  # 持续时间
    probability: float  # 发生概率
    
    def to_simulation_params(self) -> Dict[str, float]:
        """转换为仿真参数"""
        return {
            "pga": self.peak_ground_acceleration,
            "freq": self.dominant_frequency,
            "duration": self.duration_seconds
        }


@dataclass
class SimulationResult:
    """仿真结果数据模型"""
    scenario: EarthquakeScenario
    max_drift_ratio: float  # 最大层间位移角
    max_stress_mpa: float  # 最大应力
    is_collapsed: bool
    failure_mode: FailureMode
    damage_description: str
    confidence_score: float = 0.95


class PhysicsSandbox:
    """虚拟物理沙箱引擎"""
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化物理沙箱
        
        Args:
            config: 配置参数字典
        """
        self.config = config or {
            "gravity": 9.81,
            "time_step": 0.01,
            "solver_iterations": 100
        }
        self.simulation_cache: Dict[str, Any] = {}
        logger.info("物理沙箱引擎初始化完成")
    
    def _calculate_response_spectrum(
        self, 
        structure: StructureSpec, 
        earthquake: EarthquakeScenario
    ) -> Tuple[float, float]:
        """计算结构响应谱（核心仿真逻辑）
        
        Args:
            structure: 结构规格
            earthquake: 地震工况
            
        Returns:
            Tuple[最大位移角, 最大应力]
        """
        # 简化的结构动力学模型
        freq_ratio = earthquake.dominant_frequency / structure.natural_frequency_hz
        
        # 动力放大系数 (基于简化的反应谱理论)
        if 0.8 < freq_ratio < 1.2:
            # 共振区域
            amplification = 5.0 / (2 * structure.damping_ratio)
        else:
            amplification = 1.0 / abs(1 - freq_ratio**2)
        
        # 计算最大位移
        max_displacement = (
            earthquake.peak_ground_acceleration * 9.81 * 
            amplification * structure.height_meters / 100
        )
        
        # 计算层间位移角 (%)
        drift_ratio = (max_displacement / structure.height_meters) * 100
        
        # 估算最大应力 (简化模型)
        base_shear = (
            earthquake.peak_ground_acceleration * 
            structure.floors * 1000  # 假设每层质量1000吨
        )
        max_stress = base_shear / (structure.width_meters * 0.5)  # 简化截面
        
        return drift_ratio, max_stress
    
    def run_simulation(
        self, 
        structure: StructureSpec, 
        scenario: EarthquakeScenario
    ) -> SimulationResult:
        """运行单次物理仿真
        
        Args:
            structure: 建筑结构规格
            scenario: 地震工况
            
        Returns:
            SimulationResult: 仿真结果对象
        """
        logger.info(f"开始仿真: 结构={structure.name}, 震级={scenario.magnitude}")
        
        try:
            drift_ratio, max_stress = self._calculate_response_spectrum(
                structure, scenario
            )
            
            # 判断失效模式
            is_collapsed = False
            failure_mode = FailureMode.NONE
            damage_desc = "结构保持完好"
            
            # 基于阈值的失效判断
            if drift_ratio > 4.0:
                is_collapsed = True
                failure_mode = FailureMode.SHEAR_FAILURE
                damage_desc = f"层间位移角{drift_ratio:.2f}%超过极限值，承重墙发生剪切破坏"
            elif drift_ratio > 2.0:
                failure_mode = FailureMode.BENDING_FAILURE
                damage_desc = f"层间位移角{drift_ratio:.2f}%，部分梁柱出现塑性铰"
            elif max_stress > 300:  # MPa
                failure_mode = FailureMode.BENDING_FAILURE
                damage_desc = f"最大应力{max_stress:.1f}MPa超过材料屈服强度"
            
            result = SimulationResult(
                scenario=scenario,
                max_drift_ratio=round(drift_ratio, 3),
                max_stress=round(max_stress, 2),
                is_collapsed=is_collapsed,
                failure_mode=failure_mode,
                damage_description=damage_desc
            )
            
            logger.info(f"仿真完成: 失效模式={failure_mode.value}")
            return result
            
        except Exception as e:
            logger.error(f"仿真过程出错: {str(e)}")
            raise


class ExtremeConditionGenerator:
    """极端工况生成器"""
    
    def __init__(self, seed: Optional[int] = None):
        """初始化生成器
        
        Args:
            seed: 随机种子，用于可重复性
        """
        if seed:
            random.seed(seed)
        logger.info("极端工况生成器初始化完成")
    
    def generate_earthquake_scenarios(
        self,
        design_intensity: float = 7.0,
        num_scenarios: int = 5,
        include_extreme: bool = True
    ) -> List[EarthquakeScenario]:
        """生成地震工况集合（基于概率分布）
        
        Args:
            design_intensity: 设计烈度
            num_scenarios: 生成工况数量
            include_extreme: 是否包含极端工况
            
        Returns:
            List[EarthquakeScenario]: 地震工况列表
        """
        scenarios = []
        
        # 基于泊松分布的地震发生概率模型
        for i in range(num_scenarios):
            # 震级服从Gutenberg-Richter定律
            magnitude = design_intensity + random.gauss(0, 0.5) * (i + 1) / 2
            
            if include_extreme and i == num_scenarios - 1:
                # 极端工况：罕遇地震
                magnitude = min(design_intensity + 2.5, 9.0)
            
            # PGA与震级的经验关系
            pga = 0.1 * (10 ** (0.3 * magnitude - 1.5))
            pga = min(pga, 2.0)  # 物理上限
            
            # 主频随震级变化
            dominant_freq = max(0.5, 5.0 - 0.5 * magnitude)
            
            # 持续时间
            duration = 10 + 5 * (magnitude - 5)
            
            # 发生概率（指数衰减）
            probability = math.exp(-0.5 * abs(magnitude - design_intensity))
            
            scenario = EarthquakeScenario(
                magnitude=round(magnitude, 1),
                peak_ground_acceleration=round(pga, 3),
                dominant_frequency=round(dominant_freq, 2),
                duration_seconds=round(duration, 1),
                probability=round(probability, 3)
            )
            scenarios.append(scenario)
        
        logger.info(f"生成了{len(scenarios)}个地震工况")
        return scenarios


class BidirectionalTranslator:
    """双向转译引擎"""
    
    @staticmethod
    def intent_to_structure(intent: str) -> StructureSpec:
        """将自然语言意图转译为结构规格
        
        Args:
            intent: 用户意图描述
            
        Returns:
            StructureSpec: 结构规格对象
        """
        logger.info(f"解析意图: {intent}")
        
        # 简化的意图解析（实际AGI系统会使用NLP模型）
        intent_lower = intent.lower()
        
        if "医院" in intent or "hospital" in intent_lower:
            return StructureSpec(
                name="医疗中心",
                structure_type=StructureType.REINFORCED_CONCRETE,
                height_meters=45,
                width_meters=30,
                floors=12,
                damping_ratio=0.04,
                natural_frequency_hz=1.2
            )
        elif "学校" in intent or "school" in intent_lower:
            return StructureSpec(
                name="教学楼",
                structure_type=StructureType.REINFORCED_CONCRETE,
                height_meters=20,
                width_meters=50,
                floors=5,
                damping_ratio=0.05,
                natural_frequency_hz=1.8
            )
        else:  # 默认住宅
            return StructureSpec(
                name="住宅楼",
                structure_type=StructureType.REINFORCED_CONCRETE,
                height_meters=30,
                width_meters=25,
                floors=10,
                damping_ratio=0.05,
                natural_frequency_hz=1.5
            )
    
    @staticmethod
    def result_to_report(
        structure: StructureSpec,
        results: List[SimulationResult]
    ) -> str:
        """将仿真结果转译为自然语言报告
        
        Args:
            structure: 结构规格
            results: 仿真结果列表
            
        Returns:
            str: 自然语言报告
        """
        logger.info("生成自然语言报告")
        
        report_lines = [
            f"【{structure.name}抗震性能评估报告】",
            f"结构类型: {structure.structure_type.value}",
            f"建筑高度: {structure.height_meters}米 ({structure.floors}层)",
            f"自然频率: {structure.natural_frequency_hz}Hz\n",
            "─" * 40,
            "【极端工况测试结果】\n"
        ]
        
        critical_failures = []
        
        for i, result in enumerate(results, 1):
            scenario_desc = (
                f"工况{i}: {result.scenario.magnitude}级地震 "
                f"(PGA={result.scenario.peak_ground_acceleration}g, "
                f"概率={result.scenario.probability*100:.1f}%)"
            )
            report_lines.append(scenario_desc)
            
            if result.is_collapsed:
                critical_failures.append((i, result))
                report_lines.append(f"  ⚠️ 警告: {result.damage_description}")
            elif result.failure_mode != FailureMode.NONE:
                report_lines.append(f"  ⚡ 注意: {result.damage_description}")
            else:
                report_lines.append(f"  ✓ 安全: {result.damage_description}")
            
            report_lines.append(f"  最大位移角: {result.max_drift_ratio}%\n")
        
        # 综合评估结论
        report_lines.extend([
            "─" * 40,
            "【综合评估结论】"
        ])
        
        if critical_failures:
            worst = max(critical_failures, key=lambda x: x[1].scenario.magnitude)
            report_lines.append(
                f"❌ 结构存在重大安全隐患: {worst[1].damage_description}。"
                f"建议增加阻尼器或加固承重墙。"
            )
        else:
            report_lines.append(
                f"✓ 结构满足抗震要求，在所有测试工况下保持稳定。"
            )
        
        return "\n".join(report_lines)


def validate_structure_spec(data: Dict[str, Any]) -> StructureSpec:
    """验证并创建结构规格（辅助函数）
    
    Args:
        data: 原始数据字典
        
    Returns:
        StructureSpec: 验证后的结构规格
        
    Raises:
        ValueError: 数据验证失败
    """
    required_fields = [
        "name", "structure_type", "height_meters", 
        "width_meters", "floors"
    ]
    
    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"缺少必需字段: {field_name}")
    
    # 类型转换和边界检查
    try:
        structure_type = StructureType(data["structure_type"])
    except ValueError:
        raise ValueError(f"无效的结构类型: {data['structure_type']}")
    
    if data["height_meters"] > 1000:
        logger.warning("建筑高度超过1000米，可能需要特殊分析")
    
    return StructureSpec(
        name=str(data["name"])[:100],  # 限制名称长度
        structure_type=structure_type,
        height_meters=float(data["height_meters"]),
        width_meters=float(data["width_meters"]),
        floors=int(data["floors"]),
        damping_ratio=float(data.get("damping_ratio", 0.05)),
        natural_frequency_hz=float(data.get("natural_frequency_hz", 1.0))
    )


def run_intent_verification_pipeline(
    user_intent: str,
    design_intensity: float = 7.0,
    num_scenarios: int = 5
) -> Tuple[StructureSpec, List[SimulationResult], str]:
    """执行完整的意图验证流程
    
    Args:
        user_intent: 用户意图描述
        design_intensity: 设计烈度
        num_scenarios: 工况数量
        
    Returns:
        Tuple[结构规格, 仿真结果列表, 自然语言报告]
    """
    logger.info(f"启动意图验证流程: {user_intent}")
    
    # 1. 意图转译为结构规格
    structure = BidirectionalTranslator.intent_to_structure(user_intent)
    
    # 2. 生成极端工况
    generator = ExtremeConditionGenerator(seed=42)
    scenarios = generator.generate_earthquake_scenarios(
        design_intensity=design_intensity,
        num_scenarios=num_scenarios,
        include_extreme=True
    )
    
    # 3. 在物理沙箱中运行仿真
    sandbox = PhysicsSandbox()
    results = []
    
    for scenario in scenarios:
        result = sandbox.run_simulation(structure, scenario)
        results.append(result)
    
    # 4. 结果转译为自然语言报告
    report = BidirectionalTranslator.result_to_report(structure, results)
    
    logger.info("意图验证流程完成")
    return structure, results, report


# ==================== 使用示例 ====================
if __name__ == "__main__":
    """
    使用示例:
    
    1. 基本使用:
        >>> _, _, report = run_intent_verification_pipeline(
        ...     "设计一座抗震医院",
        ...     design_intensity=8.0
        ... )
        >>> print(report)
    
    2. 高级使用:
        >>> structure = validate_structure_spec({
        ...     "name": "摩天大楼",
        ...     "structure_type": "steel_frame",
        ...     "height_meters": 300,
        ...     "width_meters": 50,
        ...     "floors": 80
        ... })
        >>> generator = ExtremeConditionGenerator()
        >>> scenarios = generator.generate_earthquake_scenarios(7.0, 3)
        >>> sandbox = PhysicsSandbox()
        >>> result = sandbox.run_simulation(structure, scenarios[0])
    
    输入格式:
        - user_intent: 自然语言字符串
        - design_intensity: 浮点数 (5.0-9.0)
        - num_scenarios: 整数 (1-20)
    
    输出格式:
        - report: UTF-8编码的中文报告字符串
    """
    
    # 示例运行
    print("="*50)
    print("AGI 物理沙箱系统 - 极端工况验证演示")
    print("="*50 + "\n")
    
    structure, results, report = run_intent_verification_pipeline(
        user_intent="设计一座位于地震带的学校建筑",
        design_intensity=7.5,
        num_scenarios=4
    )
    
    print(report)
    print("\n" + "="*50)
    print(f"仿真完成，共测试{len(results)}个工况")
    
    # 导出JSON格式数据
    export_data = {
        "structure": asdict(structure),
        "results": [
            {
                "magnitude": r.scenario.magnitude,
                "is_safe": not r.is_collapsed,
                "failure_mode": r.failure_mode.value
            }
            for r in results
        ]
    }
    print("\nJSON数据导出:")
    print(json.dumps(export_data, indent=2, ensure_ascii=False))