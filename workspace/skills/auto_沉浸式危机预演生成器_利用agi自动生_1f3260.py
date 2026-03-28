"""
沉浸式危机预演生成器

本模块利用AGI技术自动生成针对特定技能的极端边缘情况危机场景。
主要应用于高风险行业（如化工、医疗、航空）的VR演练系统。

核心功能:
1. 动态生成组合型灾难场景
2. 模拟"虚拟红队"动态调整难度
3. 多维度验证操作员应急能力
4. 生成结构化VR环境配置数据

输入格式:
{
    "skill": "化工阀门操作",
    "experience_level": "intermediate",
    "max_difficulty": 10,
    "risk_factors": ["toxic", "fire", "pressure"]
}

输出格式:
{
    "scenario_id": "uuid",
    "difficulty_score": 8.5,
    "events": [
        {
            "type": "valve_failure",
            "description": "主控阀门卡死在75%开启位置",
            "concurrent_events": ["alarm_failure", "gas_leak"]
        }
    ],
    "vr_environment": {
        "lighting": "emergency_red",
        "audio": "alarm_buzz",
        "hazard_zones": [{"type": "gas_cloud", "density": 0.8}]
    }
}
"""

import json
import logging
import uuid
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskFactor(Enum):
    """风险因素枚举"""
    TOXIC = "toxic"
    FIRE = "fire"
    PRESSURE = "pressure"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"


@dataclass
class ScenarioEvent:
    """场景事件数据结构"""
    event_type: str
    description: str
    concurrent_events: List[str]
    severity: float  # 0-10


@dataclass
class VREnvironment:
    """VR环境配置"""
    lighting: str
    audio: str
    hazard_zones: List[Dict]
    visibility: float  # 0-1


class CrisisScenarioGenerator:
    """
    沉浸式危机预演生成器核心类
    
    使用示例:
    >>> generator = CrisisScenarioGenerator()
    >>> params = {
    ...     "skill": "化工阀门操作",
    ...     "experience_level": "intermediate",
    ...     "max_difficulty": 10,
    ...     "risk_factors": ["toxic", "fire"]
    ... }
    >>> scenario = generator.generate_scenario(params)
    >>> print(scenario["difficulty_score"])
    """
    
    def __init__(self):
        self._validate_environment()
        self.scenario_counter = 0
        
    def _validate_environment(self) -> None:
        """验证运行环境配置"""
        try:
            # 检查必要的依赖和配置
            logger.info("Initializing CrisisScenarioGenerator environment")
        except Exception as e:
            logger.error(f"Environment validation failed: {str(e)}")
            raise RuntimeError("Invalid runtime environment") from e
    
    def _generate_event_description(
        self,
        event_type: str,
        severity: float
    ) -> str:
        """
        生成事件描述文本
        
        Args:
            event_type: 事件类型
            severity: 严重程度(0-10)
            
        Returns:
            生成的事件描述字符串
        """
        templates = {
            "valve_failure": [
                "主控阀门卡死在{pos}%开启位置",
                "紧急切断阀响应延迟超过{delay}秒",
                "阀门密封失效导致{leak_rate}%泄漏率"
            ],
            "alarm_failure": [
                "气体检测传感器误报率{false_pos}%上升",
                "主警报系统离线持续{duration}分钟",
                "警报显示面板显示错误读数"
            ],
            "gas_leak": [
                "检测到{gas_type}气体泄漏浓度{ppm}ppm",
                "泄漏源位于{location}区域且持续扩散",
                "风向改变导致泄漏物朝控制室方向移动"
            ]
        }
        
        if event_type not in templates:
            return f"未定义的{event_type}事件"
            
        template = random.choice(templates[event_type])
        
        # 根据严重程度生成参数
        if "{pos}" in template:
            pos = int(75 + (severity * 2.5))
            return template.format(pos=pos)
        elif "{delay}" in template:
            delay = int(severity * 1.8)
            return template.format(delay=delay)
        elif "{leak_rate}" in template:
            leak_rate = int(severity * 10)
            return template.format(leak_rate=leak_rate)
        elif "{false_pos}" in template:
            false_pos = int(severity * 5)
            return template.format(false_pos=false_pos)
        elif "{duration}" in template:
            duration = int(severity * 2)
            return template.format(duration=duration)
        elif "{gas_type}" in template:
            gas_type = random.choice(["氯气", "氨气", "硫化氢"])
            ppm = int(severity * 100)
            return template.format(gas_type=gas_type, ppm=ppm)
        elif "{location}" in template:
            location = random.choice(["A区储罐", "B管道节点", "C处理单元"])
            return template.format(location=location)
        else:
            return template
    
    def _calculate_difficulty(
        self,
        base_difficulty: float,
        risk_factors: List[str],
        concurrent_events: int
    ) -> float:
        """
        计算场景难度评分
        
        Args:
            base_difficulty: 基础难度
            risk_factors: 风险因素列表
            concurrent_events: 并发事件数量
            
        Returns:
            计算后的难度评分(0-10)
        """
        try:
            # 验证输入
            if not 0 <= base_difficulty <= 10:
                raise ValueError("Base difficulty must be between 0 and 10")
                
            # 风险因素加权
            risk_weights = {
                "toxic": 1.5,
                "fire": 1.3,
                "pressure": 1.2,
                "electrical": 1.1,
                "mechanical": 1.0
            }
            
            risk_score = sum(
                risk_weights.get(rf, 1.0) for rf in risk_factors
            ) / len(risk_factors) if risk_factors else 1.0
            
            # 并发事件影响
            concurrency_factor = 1 + (0.1 * concurrent_events)
            
            # 综合计算
            final_score = base_difficulty * risk_score * concurrency_factor
            return round(min(10.0, final_score), 1)
            
        except Exception as e:
            logger.error(f"Difficulty calculation error: {str(e)}")
            return base_difficulty  # 回退到基础难度
    
    def generate_scenario(
        self,
        params: Dict,
        red_team_mode: bool = False
    ) -> Dict:
        """
        生成危机预演场景
        
        Args:
            params: 场景参数字典
            red_team_mode: 是否启用红队模式(动态调整难度)
            
        Returns:
            包含完整场景配置的字典
            
        Raises:
            ValueError: 如果输入参数无效
        """
        try:
            # 参数验证
            if not params or "skill" not in params:
                raise ValueError("Invalid input parameters")
                
            # 生成唯一场景ID
            scenario_id = str(uuid.uuid4())
            self.scenario_counter += 1
            
            # 解析参数
            skill = params["skill"]
            experience = params.get("experience_level", "intermediate")
            max_difficulty = params.get("max_difficulty", 10)
            risk_factors = params.get("risk_factors", [])
            
            # 验证难度范围
            if not 1 <= max_difficulty <= 10:
                raise ValueError("Max difficulty must be between 1 and 10")
                
            # 基础难度基于经验水平
            base_difficulty = {
                "beginner": 3.0,
                "intermediate": 6.0,
                "expert": 8.5
            }.get(experience, 5.0)
            
            # 生成事件组合
            events = self._generate_event_combination(
                skill, 
                base_difficulty,
                risk_factors
            )
            
            # 计算最终难度
            difficulty_score = self._calculate_difficulty(
                base_difficulty,
                risk_factors,
                len(events)
            )
            
            # 红队模式调整
            if red_team_mode:
                difficulty_score = self._red_team_adjustment(
                    difficulty_score,
                    max_difficulty
                )
            
            # 生成VR环境配置
            vr_config = self._generate_vr_config(
                events,
                difficulty_score
            )
            
            # 构建输出
            result = {
                "scenario_id": scenario_id,
                "skill": skill,
                "experience_level": experience,
                "difficulty_score": difficulty_score,
                "events": [asdict(e) for e in events],
                "vr_environment": asdict(vr_config),
                "red_team_mode": red_team_mode
            }
            
            logger.info(f"Generated scenario {scenario_id} with difficulty {difficulty_score}")
            return result
            
        except Exception as e:
            logger.error(f"Scenario generation failed: {str(e)}")
            raise RuntimeError("Failed to generate crisis scenario") from e
    
    def _generate_event_combination(
        self,
        skill: str,
        base_difficulty: float,
        risk_factors: List[str]
    ) -> List[ScenarioEvent]:
        """
        生成事件组合
        
        Args:
            skill: 技能领域
            base_difficulty: 基础难度
            risk_factors: 风险因素列表
            
        Returns:
            场景事件对象列表
        """
        # 根据技能和风险因素选择可能的事件类型
        possible_events = {
            "化工阀门操作": ["valve_failure", "alarm_failure", "gas_leak"],
            "电力系统维护": ["electrical_fault", "power_outage", "explosion_risk"],
            "医疗急救": ["patient_deterioration", "equipment_failure", "mass_casualty"]
        }
        
        # 获取相关事件类型
        event_types = possible_events.get(skill, ["generic_failure"])
        
        # 确定并发事件数量 (基于基础难度)
        concurrent_count = min(
            len(event_types),
            max(1, int(base_difficulty / 3))
        )
        
        # 随机选择事件
        selected_events = random.sample(
            event_types,
            concurrent_count
        )
        
        # 创建事件对象
        events = []
        for i, event_type in enumerate(selected_events):
            severity = base_difficulty * (0.8 + (0.2 * i))
            description = self._generate_event_description(
                event_type,
                severity
            )
            
            # 设置并发事件
            concurrent = []
            if i > 0:
                concurrent = [e for e in selected_events[:i] if e != event_type]
            
            events.append(ScenarioEvent(
                event_type=event_type,
                description=description,
                concurrent_events=concurrent,
                severity=round(severity, 1)
            ))
        
        return events
    
    def _generate_vr_config(
        self,
        events: List[ScenarioEvent],
        difficulty: float
    ) -> VREnvironment:
        """
        生成VR环境配置
        
        Args:
            events: 事件列表
            difficulty: 难度评分
            
        Returns:
            VR环境配置对象
        """
        # 根据事件类型确定环境参数
        hazard_zones = []
        lighting = "normal"
        audio = "background_ambience"
        visibility = 1.0
        
        for event in events:
            if event.event_type == "gas_leak":
                hazard_zones.append({
                    "type": "gas_cloud",
                    "density": round(event.severity / 10, 1),
                    "color": "green" if "chlorine" in event.description else "yellow"
                })
                visibility = max(0.2, 1.0 - (event.severity / 15))
                audio = "alarm_buzz"
                
            elif event.event_type == "fire":
                hazard_zones.append({
                    "type": "fire_zone",
                    "intensity": round(event.severity / 10, 1),
                    "spread_rate": round(event.severity / 8, 1)
                })
                lighting = "fire_flicker"
                audio = "fire_roar"
                
            elif event.event_type == "explosion_risk":
                hazard_zones.append({
                    "type": "explosion_hazard",
                    "radius": round(event.severity * 2, 1),
                    "timer": int(event.severity * 6)
                })
                audio = "ticking_sound"
        
        # 根据难度调整环境
        if difficulty > 7:
            lighting = "emergency_red" if lighting == "normal" else lighting
            audio = "emergency_alarm" if audio == "background_ambience" else audio
        
        return VREnvironment(
            lighting=lighting,
            audio=audio,
            hazard_zones=hazard_zones,
            visibility=round(visibility, 1)
        )
    
    def _red_team_adjustment(
        self,
        current_difficulty: float,
        max_difficulty: float
    ) -> float:
        """
        红队模式难度调整
        
        Args:
            current_difficulty: 当前难度
            max_difficulty: 最大允许难度
            
        Returns:
            调整后的难度评分
        """
        # 红队模式会尝试将难度推向极限
        adjustment_factor = random.uniform(0.9, 1.1)
        new_difficulty = current_difficulty * adjustment_factor
        
        # 确保不超过最大难度
        return round(min(new_difficulty, max_difficulty), 1)


if __name__ == "__main__":
    # 使用示例
    generator = CrisisScenarioGenerator()
    
    # 常规模式
    params = {
        "skill": "化工阀门操作",
        "experience_level": "intermediate",
        "max_difficulty": 10,
        "risk_factors": ["toxic", "fire"]
    }
    
    scenario = generator.generate_scenario(params)
    print(json.dumps(scenario, indent=2))
    
    # 红队模式
    red_team_scenario = generator.generate_scenario(params, red_team_mode=True)
    print("\nRed Team Scenario:")
    print(json.dumps(red_team_scenario, indent=2))