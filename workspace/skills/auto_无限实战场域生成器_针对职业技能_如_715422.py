"""
无限实战场域生成器

针对特定职业技能（如代码Debug、外科手术流程、硬件故障排查）的智能练习案例生成系统。
该模块能够根据用户的薄弱点（如：循环逻辑错误、变量命名规范等）实时构建特定的练习关卡，
解决了传统教育中"高质量练习素材匮乏"的痛点，实现"千人千面"的实战演练。

典型应用场景：
1. 代码Debug训练：生成包含特定类型错误的代码片段
2. 医疗技能训练：生成特定难度的手术流程场景
3. 故障排查训练：生成包含特定故障模式的系统日志

依赖：
- Python 3.7+
- typing
- logging
- json
- random
"""

import json
import logging
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillDomain(Enum):
    """技能领域枚举"""
    CODE_DEBUG = "code_debug"
    SURGICAL_SKILLS = "surgical_skills"
    TROUBLESHOOTING = "troubleshooting"

class DifficultyLevel(Enum):
    """难度等级枚举"""
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4

@dataclass
class UserProfile:
    """用户画像数据结构"""
    user_id: str
    skill_domain: SkillDomain
    weak_points: List[str]  # 薄弱点列表，如["循环逻辑", "变量命名"]
    current_level: DifficultyLevel
    learning_history: List[Dict[str, Any]]  # 历史练习记录
    last_active: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "skill_domain": self.skill_domain.value,
            "weak_points": self.weak_points,
            "current_level": self.current_level.value,
            "learning_history": self.learning_history,
            "last_active": self.last_active.isoformat()
        }

@dataclass
class TrainingScenario:
    """训练场景数据结构"""
    scenario_id: str
    skill_domain: SkillDomain
    difficulty: DifficultyLevel
    target_weakness: str
    content: Dict[str, Any]  # 具体的训练内容
    metadata: Dict[str, Any]  # 元数据，如创建时间、预计完成时间等
    hints: List[str]  # 提示信息

    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps({
            "scenario_id": self.scenario_id,
            "skill_domain": self.skill_domain.value,
            "difficulty": self.difficulty.value,
            "target_weakness": self.target_weakness,
            "content": self.content,
            "metadata": self.metadata,
            "hints": self.hints
        }, indent=2)

class ScenarioGenerator:
    """无限实战场域生成器核心类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化生成器
        
        Args:
            config: 配置字典，包含各种生成参数
        """
        self.config = config or {}
        self.scenario_counter = 0
        self.template_library = self._initialize_templates()
        logger.info("ScenarioGenerator initialized with config: %s", self.config)
    
    def _initialize_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        初始化场景模板库
        
        Returns:
            按技能领域分类的模板字典
        """
        return {
            SkillDomain.CODE_DEBUG.value: [
                {
                    "template_id": "code_loop_error",
                    "weakness": "循环逻辑",
                    "template": "for i in range({start}, {end}):\n    {body}",
                    "error_types": ["off_by_one", "infinite_loop", "incorrect_range"]
                },
                {
                    "template_id": "code_variable_naming",
                    "weakness": "变量命名",
                    "template": "{var1} = {value1}\n{var2} = {value2}\nprint({var1} + {var2})",
                    "error_types": ["naming_conflict", "case_sensitivity"]
                }
            ],
            SkillDomain.SURGICAL_SKILLS.value: [
                {
                    "template_id": "suture_technique",
                    "weakness": "缝合技术",
                    "template": "使用{instrument}在{tissue_type}上进行{technique}缝合",
                    "error_types": ["incorrect_instrument", "tissue_damage", "improper_tension"]
                }
            ],
            SkillDomain.TROUBLESHOOTING.value: [
                {
                    "template_id": "network_issue",
                    "weakness": "网络故障排查",
                    "template": "系统日志显示: {error_code} - {error_message}",
                    "error_types": ["timeout", "connection_refused", "dns_failure"]
                }
            ]
        }
    
    def _validate_user_profile(self, user_profile: Union[Dict[str, Any], UserProfile]) -> UserProfile:
        """
        验证并转换用户画像数据
        
        Args:
            user_profile: 用户画像数据，可以是字典或UserProfile对象
            
        Returns:
            验证后的UserProfile对象
            
        Raises:
            ValueError: 如果数据验证失败
        """
        try:
            if isinstance(user_profile, dict):
                # 转换字典为UserProfile对象
                user_profile = UserProfile(
                    user_id=user_profile["user_id"],
                    skill_domain=SkillDomain(user_profile["skill_domain"]),
                    weak_points=user_profile.get("weak_points", []),
                    current_level=DifficultyLevel(user_profile.get("current_level", 1)),
                    learning_history=user_profile.get("learning_history", []),
                    last_active=datetime.fromisoformat(user_profile["last_active"])
                    if "last_active" in user_profile else datetime.now()
                )
            
            # 边界检查
            if not user_profile.user_id:
                raise ValueError("用户ID不能为空")
            
            if not user_profile.weak_points:
                logger.warning("用户 %s 没有设置薄弱点，将使用默认场景", user_profile.user_id)
            
            return user_profile
        except (KeyError, ValueError) as e:
            logger.error("用户画像验证失败: %s", str(e))
            raise ValueError(f"无效的用户画像数据: {str(e)}")
    
    def _select_template(self, skill_domain: SkillDomain, weakness: str) -> Dict[str, Any]:
        """
        根据技能领域和薄弱点选择合适的模板
        
        Args:
            skill_domain: 技能领域
            weakness: 薄弱点描述
            
        Returns:
            选中的模板
            
        Raises:
            ValueError: 如果找不到合适的模板
        """
        domain_templates = self.template_library.get(skill_domain.value, [])
        
        # 尝试精确匹配
        for template in domain_templates:
            if template["weakness"] == weakness:
                return template
        
        # 如果没有精确匹配，尝试模糊匹配
        for template in domain_templates:
            if weakness in template["weakness"] or template["weakness"] in weakness:
                logger.info("使用模糊匹配模板: %s 代替 %s", template["weakness"], weakness)
                return template
        
        # 如果还是没有，随机选择一个
        if domain_templates:
            selected = random.choice(domain_templates)
            logger.warning("没有找到匹配的模板，随机选择: %s", selected["weakness"])
            return selected
        
        raise ValueError(f"找不到适合 {skill_domain.value} 领域的模板")
    
    def generate_scenario(
        self,
        user_profile: Union[Dict[str, Any], UserProfile],
        custom_weakness: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None
    ) -> TrainingScenario:
        """
        生成训练场景
        
        Args:
            user_profile: 用户画像数据
            custom_weakness: 自定义薄弱点（覆盖用户画像中的薄弱点）
            difficulty: 自定义难度（覆盖用户画像中的难度）
            
        Returns:
            生成的训练场景
            
        Raises:
            ValueError: 如果参数无效或生成失败
        """
        try:
            # 验证用户数据
            validated_user = self._validate_user_profile(user_profile)
            logger.info("为用户 %s 生成训练场景", validated_user.user_id)
            
            # 确定薄弱点和难度
            target_weakness = custom_weakness or (
                random.choice(validated_user.weak_points) 
                if validated_user.weak_points else "综合技能"
            )
            target_difficulty = difficulty or validated_user.current_level
            
            # 选择模板
            template = self._select_template(
                validated_user.skill_domain,
                target_weakness
            )
            
            # 生成场景内容
            scenario_content = self._generate_content_from_template(
                template,
                target_difficulty
            )
            
            # 创建场景对象
            self.scenario_counter += 1
            scenario = TrainingScenario(
                scenario_id=f"scenario_{validated_user.skill_domain.value}_{self.scenario_counter}",
                skill_domain=validated_user.skill_domain,
                difficulty=target_difficulty,
                target_weakness=target_weakness,
                content=scenario_content,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "estimated_time": f"{target_difficulty.value * 5}分钟",
                    "success_criteria": "正确识别并修复所有问题"
                },
                hints=self._generate_hints(template, target_difficulty)
            )
            
            logger.info("成功生成场景: %s", scenario.scenario_id)
            return scenario
            
        except Exception as e:
            logger.error("场景生成失败: %s", str(e))
            raise RuntimeError(f"场景生成失败: {str(e)}")
    
    def _generate_content_from_template(
        self,
        template: Dict[str, Any],
        difficulty: DifficultyLevel
    ) -> Dict[str, Any]:
        """
        根据模板生成具体内容
        
        Args:
            template: 场景模板
            difficulty: 难度等级
            
        Returns:
            生成的场景内容
        """
        content = {"template_id": template["template_id"]}
        
        # 这里根据不同的技能领域实现不同的内容生成逻辑
        if "code_loop_error" in template["template_id"]:
            # 代码Debug场景
            start = random.randint(0, 5)
            end = start + random.randint(3, 10)
            
            # 根据难度选择错误类型
            error_type = random.choice(template["error_types"])
            
            if error_type == "off_by_one":
                body = f"print(array[{end}])  # 故意制造索引越界"
            elif error_type == "infinite_loop":
                body = "pass  # 缺少循环终止条件"
            else:
                body = "print(i)"
            
            content.update({
                "code": template["template"].format(
                    start=start,
                    end=end if random.random() > 0.3 else end + 1,  # 有概率制造错误
                    body=body
                ),
                "error_type": error_type,
                "expected_fix": "检查循环边界或添加终止条件"
            })
        
        elif "suture_technique" in template["template_id"]:
            # 外科手术场景
            instruments = ["持针器", "镊子", "剪刀"]
            tissues = ["皮肤", "筋膜", "血管"]
            techniques = ["间断", "连续", "褥式"]
            
            content.update({
                "description": template["template"].format(
                    instrument=random.choice(instruments),
                    tissue_type=random.choice(tissues),
                    technique=random.choice(techniques)
                ),
                "evaluation_criteria": [
                    "进针角度正确",
                    "打结力度适中",
                    "组织对齐良好"
                ][:difficulty.value]  # 难度越高，评估标准越多
            })
        
        elif "network_issue" in template["template_id"]:
            # 故障排查场景
            error_codes = ["ETIMEDOUT", "ECONNREFUSED", "ENOTFOUND"]
            error_messages = [
                "Connection timed out",
                "Connection refused by server",
                "DNS resolution failed"
            ]
            
            idx = random.randint(0, len(error_codes) - 1)
            content.update({
                "log_entry": template["template"].format(
                    error_code=error_codes[idx],
                    error_message=error_messages[idx]
                ),
                "possible_causes": [
                    "网络连接中断",
                    "目标服务未运行",
                    "DNS配置错误"
                ],
                "resolution_steps": [
                    "检查网络连接",
                    "验证服务状态",
                    "测试DNS解析"
                ]
            })
        
        return content
    
    def _generate_hints(
        self,
        template: Dict[str, Any],
        difficulty: DifficultyLevel
    ) -> List[str]:
        """
        生成提示信息
        
        Args:
            template: 场景模板
            difficulty: 难度等级
            
        Returns:
            提示信息列表，难度越高提示越少
        """
        base_hints = [
            f"注意检查与{template['weakness']}相关的部分",
            "仔细阅读错误信息或症状",
            "尝试复现问题"
        ]
        
        # 根据难度调整提示数量
        hint_count = max(1, 4 - difficulty.value)
        return base_hints[:hint_count]
    
    def generate_batch_scenarios(
        self,
        user_profile: Union[Dict[str, Any], UserProfile],
        count: int = 3,
        diversity: bool = True
    ) -> List[TrainingScenario]:
        """
        批量生成训练场景
        
        Args:
            user_profile: 用户画像数据
            count: 要生成的场景数量
            diversity: 是否确保场景多样性
            
        Returns:
            生成的场景列表
            
        Raises:
            ValueError: 如果参数无效
        """
        if count < 1 or count > 10:
            raise ValueError("生成数量应在1-10之间")
        
        validated_user = self._validate_user_profile(user_profile)
        scenarios = []
        
        for i in range(count):
            # 如果需要多样性，每次循环选择不同的薄弱点
            custom_weakness = (
                validated_user.weak_points[i % len(validated_user.weak_points)]
                if diversity and validated_user.weak_points else None
            )
            
            # 轮换难度
            difficulty = DifficultyLevel((i % 4) + 1)
            
            try:
                scenario = self.generate_scenario(
                    user_profile=validated_user,
                    custom_weakness=custom_weakness,
                    difficulty=difficulty
                )
                scenarios.append(scenario)
            except Exception as e:
                logger.error("批量生成中第 %d 个场景失败: %s", i+1, str(e))
                continue
        
        if not scenarios:
            raise RuntimeError("批量生成失败，无法生成任何有效场景")
        
        logger.info("成功批量生成 %d 个场景", len(scenarios))
        return scenarios

# 使用示例
if __name__ == "__main__":
    # 示例用户数据
    example_user = {
        "user_id": "user_123",
        "skill_domain": "code_debug",
        "weak_points": ["循环逻辑", "变量命名"],
        "current_level": 2,
        "learning_history": []
    }
    
    # 初始化生成器
    generator = ScenarioGenerator({
        "max_scenarios_per_user": 5,
        "default_difficulty": 2
    })
    
    try:
        # 生成单个场景
        print("生成单个场景:")
        scenario = generator.generate_scenario(example_user)
        print(scenario.to_json())
        
        print("\n批量生成场景:")
        # 批量生成场景
        batch = generator.generate_batch_scenarios(example_user, count=3)
        for idx, s in enumerate(batch, 1):
            print(f"\n场景 {idx}:")
            print(s.to_json())
            
    except Exception as e:
        print(f"错误: {str(e)}")