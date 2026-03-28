"""
无限语境生成导师

该模块实现了一个基于LLM和PCG（过程内容生成）逻辑的交互式教学系统。
针对一个核心概念（如'复利效应'），根据用户的职业背景，实时生成无限个
定制化的、难度递进的交互式案例场景。

主要组件:
    - InfiniteContextMentor: 核心类，负责场景生成和交互逻辑
    - LLMInterface: 模拟与大语言模型的交互接口
    - PCGEngine: 过程内容生成引擎
"""

import logging
import json
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """难度等级枚举"""
    NOVICE = 1       # 新手
    INTERMEDIATE = 2 # 中级
    ADVANCED = 3     # 高级
    EXPERT = 4       # 专家
    MASTER = 5       # 大师


class Profession(Enum):
    """职业背景枚举"""
    PROGRAMMER = "程序员"
    CHEF = "厨师"
    PAINTER = "画家"
    TEACHER = "教师"
    DOCTOR = "医生"


@dataclass
class ScenarioContext:
    """场景上下文数据结构"""
    core_concept: str
    profession: Profession
    difficulty: DifficultyLevel
    scenario_id: str
    description: str
    variables: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)


class LLMInterface:
    """
    大语言模型接口（模拟实现）
    
    在实际应用中，这里会连接到真实的LLM API（如OpenAI, Anthropic等）
    当前实现使用模板和规则生成内容
    """
    
    def __init__(self, model_name: str = "gpt-4-simulation"):
        self.model_name = model_name
        self._template_cache: Dict[str, str] = {}
        
    def generate_scenario(
        self, 
        concept: str, 
        profession: Profession,
        difficulty: DifficultyLevel,
        seed: int
    ) -> Dict[str, Any]:
        """
        根据核心概念和职业背景生成场景
        
        Args:
            concept: 核心概念（如'复利效应'）
            profession: 用户职业背景
            difficulty: 难度等级
            seed: 随机种子，用于可重复生成
            
        Returns:
            包含场景信息的字典
        """
        logger.info(f"Generating scenario for {profession.value} about {concept}")
        
        # 基于职业和概念的模板映射
        templates = self._get_profession_templates(profession, concept)
        
        # 根据难度调整参数范围
        params = self._calculate_difficulty_params(difficulty, seed)
        
        # 模拟LLM生成过程
        scenario_data = {
            "description": self._generate_description(templates, params),
            "variables": self._generate_variables(params, seed),
            "constraints": self._generate_constraints(difficulty),
            "feedback_rules": self._generate_feedback_rules(profession)
        }
        
        logger.debug(f"Generated scenario data: {json.dumps(scenario_data, indent=2)}")
        return scenario_data
    
    def _get_profession_templates(
        self, 
        profession: Profession, 
        concept: str
    ) -> Dict[str, str]:
        """获取职业相关的场景模板"""
        templates = {
            Profession.PROGRAMMER: {
                "复利效应": (
                    "你正在开发一个代码重构项目。每次优化一个模块，"
                    "都会使后续模块的开发效率提升{efficiency}%。"
                    "当前有{modules}个模块需要处理，初始效率为{base_efficiency}%。"
                )
            },
            Profession.CHEF: {
                "复利效应": (
                    "你正在改进一道经典菜谱。每次尝试新配方，"
                    "都会积累{experience}点经验值，使下一次创新成功率提升{success_rate}%。"
                    "当前已尝试{attempts}次，基础成功率为{base_success}%。"
                )
            },
            Profession.PAINTER: {
                "复利效应": (
                    "你在创作系列画作。每完成一幅作品，"
                    "你的技法熟练度提升{skill}%，使后续作品价值增长{value_growth}%。"
                    "计划创作{total_paintings}幅，当前市场价值为{current_value}。"
                )
            }
        }
        
        if profession not in templates or concept not in templates[profession]:
            # 通用模板
            return {
                "default": (
                    f"你正在学习{concept}。每次实践都会带来{concept}的累积效果。"
                    f"初始状态为{10}，每次增长率为{5}%。"
                )
            }
        
        return templates[profession]
    
    def _calculate_difficulty_params(
        self, 
        difficulty: DifficultyLevel, 
        seed: int
    ) -> Dict[str, Any]:
        """根据难度计算参数范围"""
        random.seed(seed)
        
        base_ranges = {
            DifficultyLevel.NOVICE: {
                "complexity": (1, 3),
                "variables": 2,
                "time_limit": None,
                "hints_available": 5
            },
            DifficultyLevel.INTERMEDIATE: {
                "complexity": (3, 6),
                "variables": 4,
                "time_limit": 300,
                "hints_available": 3
            },
            DifficultyLevel.ADVANCED: {
                "complexity": (6, 10),
                "variables": 6,
                "time_limit": 180,
                "hints_available": 2
            },
            DifficultyLevel.EXPERT: {
                "complexity": (10, 15),
                "variables": 8,
                "time_limit": 120,
                "hints_available": 1
            },
            DifficultyLevel.MASTER: {
                "complexity": (15, 20),
                "variables": 10,
                "time_limit": 60,
                "hints_available": 0
            }
        }
        
        return base_ranges.get(difficulty, base_ranges[DifficultyLevel.NOVICE])
    
    def _generate_description(
        self, 
        templates: Dict[str, str], 
        params: Dict[str, Any]
    ) -> str:
        """生成场景描述"""
        template_key = list(templates.keys())[0]
        template = templates[template_key]
        
        # 提取模板中的变量并生成值
        import string
        formatter = string.Formatter()
        variable_names = [v[1] for v in formatter.parse(template) if v[1] is not None]
        
        values = {}
        for var in variable_names:
            if "efficiency" in var or "rate" in var or "growth" in var:
                values[var] = round(random.uniform(1, 10), 1)
            elif "modules" in var or "attempts" in var or "paintings" in var:
                values[var] = random.randint(5, 20)
            elif "base" in var:
                values[var] = random.randint(10, 50)
            elif "value" in var:
                values[var] = random.randint(100, 1000)
            else:
                values[var] = random.randint(1, 10)
        
        try:
            return template.format(**values)
        except KeyError as e:
            logger.warning(f"Missing variable in template: {e}")
            return template
    
    def _generate_variables(
        self, 
        params: Dict[str, Any], 
        seed: int
    ) -> Dict[str, Any]:
        """生成场景变量"""
        random.seed(seed)
        complexity = params.get("complexity", (1, 3))
        
        return {
            "iteration_count": random.randint(*complexity),
            "growth_rate": round(random.uniform(1.01, 1.2), 3),
            "initial_value": random.randint(10, 100),
            "noise_factor": round(random.uniform(0, 0.1), 2),
            "hidden_constraints": random.randint(0, params.get("variables", 2) // 2)
        }
    
    def _generate_constraints(self, difficulty: DifficultyLevel) -> List[str]:
        """生成场景约束条件"""
        all_constraints = [
            "时间资源有限",
            "资源不可再生",
            "存在竞争者",
            "市场波动性",
            "技术折旧",
            "机会成本",
            "边际递减效应",
            "外部干扰因素"
        ]
        
        num_constraints = difficulty.value
        return random.sample(all_constraints, min(num_constraints, len(all_constraints)))
    
    def _generate_feedback_rules(self, profession: Profession) -> Dict[str, str]:
        """生成反馈规则"""
        profession_feedback = {
            Profession.PROGRAMMER: {
                "correct": "代码优化路径正确！复利效应在技术债务减少中体现。",
                "partial": "部分模块优化有效，但整体架构还有改进空间。",
                "incorrect": "优化策略可能导致新的技术债务，请重新思考。"
            },
            Profession.CHEF: {
                "correct": "配方改进完美！风味层次随迭代更加丰富。",
                "partial": "口感有提升，但火候掌握还需精进。",
                "incorrect": "配料组合产生冲突，味道层次混乱。"
            },
            Profession.PAINTER: {
                "correct": "技法运用娴熟！作品价值呈现指数增长。",
                "partial": "构图有进步，但色彩运用还可以更深入。",
                "incorrect": "技法堆砌过度，作品失去焦点。"
            }
        }
        
        return profession_feedback.get(profession, {
            "correct": "理解正确！",
            "partial": "部分正确，继续探索。",
            "incorrect": "方向有误，请重新思考。"
        })


class PCGEngine:
    """
    过程内容生成引擎
    
    负责生成无限变化的游戏化场景，确保每次体验都有独特性
    """
    
    def __init__(self, llm_interface: LLMInterface):
        self.llm = llm_interface
        self.scenario_counter = 0
        
    def generate_unique_seed(self) -> int:
        """生成唯一种子"""
        self.scenario_counter += 1
        import time
        return int(time.time() * 1000) + self.scenario_counter
    
    def create_scenario(
        self,
        concept: str,
        profession: Profession,
        difficulty: DifficultyLevel
    ) -> ScenarioContext:
        """
        创建完整场景
        
        Args:
            concept: 核心概念
            profession: 职业背景
            difficulty: 难度等级
            
        Returns:
            ScenarioContext对象
        """
        if not concept or not isinstance(concept, str):
            raise ValueError("概念必须是非空字符串")
        
        if len(concept) > 100:
            raise ValueError("概念描述过长，请限制在100字符以内")
        
        seed = self.generate_unique_seed()
        scenario_id = f"SCN_{seed}_{profession.name}_{difficulty.name}"
        
        logger.info(f"Creating scenario {scenario_id}")
        
        try:
            llm_data = self.llm.generate_scenario(concept, profession, difficulty, seed)
            
            scenario = ScenarioContext(
                core_concept=concept,
                profession=profession,
                difficulty=difficulty,
                scenario_id=scenario_id,
                description=llm_data["description"],
                variables=llm_data["variables"],
                constraints=llm_data["constraints"],
                expected_outcomes=self._generate_expected_outcomes(difficulty)
            )
            
            logger.info(f"Scenario {scenario_id} created successfully")
            return scenario
            
        except Exception as e:
            logger.error(f"Failed to create scenario: {e}")
            raise RuntimeError(f"场景生成失败: {e}") from e
    
    def _generate_expected_outcomes(
        self, 
        difficulty: DifficultyLevel
    ) -> List[str]:
        """生成预期学习成果"""
        base_outcomes = [
            "理解复利效应的基本原理",
            "识别影响复利效果的关键变量",
            "预测长期趋势",
            "优化增长策略"
        ]
        
        advanced_outcomes = [
            "处理非线性增长中的干扰因素",
            "在约束条件下最大化复利效果",
            "设计可持续的增长系统",
            "识别复利效应的边界条件"
        ]
        
        if difficulty.value <= 2:
            return base_outcomes[:difficulty.value + 1]
        else:
            return base_outcomes + advanced_outcomes[:difficulty.value - 2]


class InfiniteContextMentor:
    """
    无限语境生成导师
    
    核心类，整合LLM和PCG能力，提供个性化的交互式学习体验
    """
    
    def __init__(self, llm_model: str = "gpt-4-simulation"):
        """
        初始化导师系统
        
        Args:
            llm_model: 使用的LLM模型名称
        """
        self.llm = LLMInterface(llm_model)
        self.pcg = PCGEngine(self.llm)
        self.user_progress: Dict[str, Any] = {}
        self.scenario_history: List[ScenarioContext] = []
        
        logger.info("InfiniteContextMentor initialized")
    
    def start_learning_session(
        self,
        user_id: str,
        concept: str,
        profession: Profession,
        initial_difficulty: Optional[DifficultyLevel] = None
    ) -> Tuple[ScenarioContext, Dict[str, Any]]:
        """
        开始学习会话
        
        Args:
            user_id: 用户唯一标识
            concept: 要学习的核心概念
            profession: 用户职业背景
            initial_difficulty: 初始难度（可选，根据历史记录自动调整）
            
        Returns:
            元组（场景上下文，会话信息）
            
        Raises:
            ValueError: 参数验证失败
        """
        # 数据验证
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        if len(user_id) > 50:
            raise ValueError("用户ID过长，请限制在50字符以内")
        
        # 初始化或获取用户进度
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "total_sessions": 0,
                "completed_scenarios": 0,
                "average_score": 0.0,
                "current_difficulty": DifficultyLevel.NOVICE.value,
                "concept_history": {}
            }
            logger.info(f"New user registered: {user_id}")
        
        progress = self.user_progress[user_id]
        
        # 确定难度
        if initial_difficulty is None:
            # 自适应难度调整
            difficulty = self._calculate_adaptive_difficulty(progress, concept)
        else:
            difficulty = initial_difficulty
        
        # 生成场景
        scenario = self.pcg.create_scenario(concept, profession, difficulty)
        self.scenario_history.append(scenario)
        
        # 更新进度
        progress["total_sessions"] += 1
        if concept not in progress["concept_history"]:
            progress["concept_history"][concept] = {
                "attempts": 0,
                "best_score": 0.0
            }
        progress["concept_history"][concept]["attempts"] += 1
        
        session_info = {
            "session_id": scenario.scenario_id,
            "user_id": user_id,
            "difficulty": difficulty.name,
            "hints_remaining": self._get_hints_for_difficulty(difficulty),
            "time_limit": self._get_time_limit(difficulty),
            "progress": progress
        }
        
        logger.info(f"Learning session started for user {user_id}")
        return scenario, session_info
    
    def evaluate_response(
        self,
        scenario: ScenarioContext,
        user_response: Dict[str, Any],
        time_taken: float
    ) -> Dict[str, Any]:
        """
        评估用户响应
        
        Args:
            scenario: 当前场景
            user_response: 用户的响应数据
            time_taken: 响应时间（秒）
            
        Returns:
            评估结果字典
            
        Raises:
            TypeError: 参数类型错误
        """
        if not isinstance(scenario, ScenarioContext):
            raise TypeError("scenario必须是ScenarioContext类型")
        
        if not isinstance(user_response, dict):
            raise TypeError("user_response必须是字典类型")
        
        if time_taken < 0:
            raise ValueError("响应时间不能为负数")
        
        logger.info(f"Evaluating response for scenario {scenario.scenario_id}")
        
        # 计算分数
        base_score = self._calculate_base_score(scenario, user_response)
        time_bonus = self._calculate_time_bonus(time_taken, scenario.difficulty)
        final_score = min(100, base_score + time_bonus)
        
        # 确定反馈类型
        if final_score >= 80:
            feedback_type = "correct"
        elif final_score >= 50:
            feedback_type = "partial"
        else:
            feedback_type = "incorrect"
        
        # 获取反馈
        feedback_rules = self.llm._generate_feedback_rules(scenario.profession)
        feedback = feedback_rules.get(feedback_type, "继续努力！")
        
        # 生成详细分析
        analysis = self._generate_detailed_analysis(
            scenario, 
            user_response, 
            final_score
        )
        
        result = {
            "score": final_score,
            "feedback_type": feedback_type,
            "feedback": feedback,
            "time_taken": time_taken,
            "time_bonus": time_bonus,
            "analysis": analysis,
            "next_difficulty": self._suggest_next_difficulty(
                final_score, 
                scenario.difficulty
            ).name
        }
        
        logger.info(f"Evaluation complete: score={final_score}")
        return result
    
    def _calculate_adaptive_difficulty(
        self, 
        progress: Dict[str, Any], 
        concept: str
    ) -> DifficultyLevel:
        """计算自适应难度"""
        avg_score = progress.get("average_score", 0.0)
        current_diff = progress.get("current_difficulty", 1)
        
        # 如果是新概念，从适中难度开始
        if concept not in progress.get("concept_history", {}):
            return DifficultyLevel.NOVICE
        
        # 根据平均分调整难度
        if avg_score >= 85 and current_diff < 5:
            return DifficultyLevel(current_diff + 1)
        elif avg_score < 50 and current_diff > 1:
            return DifficultyLevel(current_diff - 1)
        else:
            return DifficultyLevel(current_diff)
    
    def _calculate_base_score(
        self, 
        scenario: ScenarioContext, 
        response: Dict[str, Any]
    ) -> float:
        """计算基础分数"""
        # 简化的评分逻辑
        expected_keys = ["understanding", "application", "prediction"]
        score = 0.0
        
        for key in expected_keys:
            if key in response:
                value = response[key]
                if isinstance(value, (int, float)):
                    score += min(33.33, max(0, value))
                elif isinstance(value, bool) and value:
                    score += 33.33
        
        return round(score, 2)
    
    def _calculate_time_bonus(
        self, 
        time_taken: float, 
        difficulty: DifficultyLevel
    ) -> float:
        """计算时间奖励"""
        time_limits = {
            DifficultyLevel.NOVICE: float('inf'),
            DifficultyLevel.INTERMEDIATE: 300,
            DifficultyLevel.ADVANCED: 180,
            DifficultyLevel.EXPERT: 120,
            DifficultyLevel.MASTER: 60
        }
        
        limit = time_limits.get(difficulty, float('inf'))
        if limit == float('inf'):
            return 0
        
        if time_taken <= limit * 0.5:
            return 15
        elif time_taken <= limit * 0.75:
            return 10
        elif time_taken <= limit:
            return 5
        else:
            return -5
    
    def _generate_detailed_analysis(
        self,
        scenario: ScenarioContext,
        response: Dict[str, Any],
        score: float
    ) -> Dict[str, Any]:
        """生成详细分析"""
        return {
            "concept_mastery": f"{score}%",
            "strengths": [
                "识别关键变量" if score > 60 else None,
                "应用复利思维" if score > 70 else None,
                "长期预测能力" if score > 80 else None
            ],
            "areas_for_improvement": [
                "基础概念理解" if score < 60 else None,
                "实际应用能力" if score < 70 else None,
                "复杂场景分析" if score < 80 else None
            ],
            "recommended_practice": [
                "尝试更多基础场景" if score < 60 else None,
                "挑战中级难度" if 60 <= score < 80 else None,
                "探索专家级挑战" if score >= 80 else None
            ]
        }
    
    def _suggest_next_difficulty(
        self, 
        score: float, 
        current: DifficultyLevel
    ) -> DifficultyLevel:
        """建议下一个难度"""
        if score >= 85 and current.value < 5:
            return DifficultyLevel(current.value + 1)
        elif score < 50 and current.value > 1:
            return DifficultyLevel(current.value - 1)
        return current
    
    def _get_hints_for_difficulty(self, difficulty: DifficultyLevel) -> int:
        """获取可用提示数量"""
        hints_map = {
            DifficultyLevel.NOVICE: 5,
            DifficultyLevel.INTERMEDIATE: 3,
            DifficultyLevel.ADVANCED: 2,
            DifficultyLevel.EXPERT: 1,
            DifficultyLevel.MASTER: 0
        }
        return hints_map.get(difficulty, 0)
    
    def _get_time_limit(self, difficulty: DifficultyLevel) -> Optional[int]:
        """获取时间限制（秒）"""
        time_map = {
            DifficultyLevel.NOVICE: None,
            DifficultyLevel.INTERMEDIATE: 300,
            DifficultyLevel.ADVANCED: 180,
            DifficultyLevel.EXPERT: 120,
            DifficultyLevel.MASTER: 60
        }
        return time_map.get(difficulty)
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户学习统计
        
        Args:
            user_id: 用户唯一标识
            
        Returns:
            统计信息字典
        """
        if user_id not in self.user_progress:
            logger.warning(f"User {user_id} not found")
            return {"error": "用户不存在"}
        
        progress = self.user_progress[user_id]
        
        return {
            "user_id": user_id,
            "total_sessions": progress["total_sessions"],
            "completed_scenarios": progress["completed_scenarios"],
            "average_score": progress["average_score"],
            "current_difficulty": DifficultyLevel(
                progress["current_difficulty"]
            ).name,
            "concepts_learned": list(progress["concept_history"].keys()),
            "mastery_levels": {
                concept: data["best_score"] 
                for concept, data in progress["concept_history"].items()
            }
        }


# 使用示例
if __name__ == "__main__":
    """
    使用示例:
    
    >>> mentor = InfiniteContextMentor()
    >>> scenario, session = mentor.start_learning_session(
    ...     user_id="student_001",
    ...     concept="复利效应",
    ...     profession=Profession.PROGRAMMER
    ... )
    >>> print(f"场景描述: {scenario.description}")
    >>> 
    >>> # 用户响应
    >>> response = {
    ...     "understanding": 85,
    ...     "application": 80,
    ...     "prediction": 75
    ... }
    >>> result = mentor.evaluate_response(scenario, response, time_taken=120.5)
    >>> print(f"得分: {result['score']}")
    >>> print(f"反馈: {result['feedback']}")
    """
    
    # 演示代码
    print("=" * 60)
    print("无限语境生成导师 - 演示")
    print("=" * 60)
    
    try:
        # 初始化导师系统
        mentor = InfiniteContextMentor(llm_model="gpt-4-simulation")
        
        # 为程序员创建复利效应学习场景
        scenario, session = mentor.start_learning_session(
            user_id="demo_programmer",
            concept="复利效应",
            profession=Profession.PROGRAMMER,
            initial_difficulty=DifficultyLevel.INTERMEDIATE
        )
        
        print(f"\n[场景ID] {scenario.scenario_id}")
        print(f"[难度] {scenario.difficulty.name}")
        print(f"[描述] {scenario.description}")
        print(f"[约束条件] {', '.join(scenario.constraints)}")
        print(f"[预期成果] {scenario.expected_outcomes}")
        
        # 模拟用户响应
        user_response = {
            "understanding": 90,
            "application": 85,
            "prediction": 80
        }
        
        # 评估响应
        evaluation = mentor.evaluate_response(
            scenario, 
            user_response, 
            time_taken=150.0
        )
        
        print(f"\n[评估结果]")
        print(f"得分: {evaluation['score']}/100")
        print(f"反馈类型: {evaluation['feedback_type']}")
        print(f"反馈: {evaluation['feedback']}")
        print(f"建议下一难度: {evaluation['next_difficulty']}")
        
        # 获取用户统计
        stats = mentor.get_user_statistics("demo_programmer")
        print(f"\n[用户统计]")
        for key, value in stats.items():
            print(f"{key}: {value}")
            
    except ValueError as ve:
        logger.error(f"参数错误: {ve}")
        print(f"错误: {ve}")
    except RuntimeError as re:
        logger.error(f"运行时错误: {re}")
        print(f"错误: {re}")
    except Exception as e:
        logger.exception(f"未知错误: {e}")
        print(f"系统错误: {e}")
    
    print("\n" + "=" * 60)
    print("演示结束")
    print("=" * 60)