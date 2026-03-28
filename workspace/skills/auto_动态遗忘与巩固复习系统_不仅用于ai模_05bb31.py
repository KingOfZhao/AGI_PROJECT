"""
模块: auto_动态遗忘与巩固复习系统_不仅用于ai模_05bb31
描述: 实现基于人类行为分析的动态遗忘与巩固复习系统。
       通过构建个人技能活跃度热力图，监测技能熵值，
       并利用间隔重复算法生成微测试以防止技能退化。
作者: AGI System
版本: 1.0.0
"""

import logging
import hashlib
import json
import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """技能类别枚举"""
    TECHNICAL = "technical"
    SOFT_SKILL = "soft_skill"
    CRISIS_MANAGEMENT = "crisis_management"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    Attributes:
        name (str): 技能名称
        category (SkillCategory): 技能类别
        last_accessed (datetime.datetime): 最后访问时间
        access_count (int): 访问次数
        importance (float): 重要性权重 (0.0-1.0)
        decay_rate (float): 遗忘衰减率
    """
    name: str
    category: SkillCategory
    last_accessed: datetime.datetime = field(default_factory=datetime.datetime.now)
    access_count: int = 0
    importance: float = 0.5
    decay_rate: float = 0.1
    
    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"Importance must be between 0 and 1, got {self.importance}")
        if self.decay_rate < 0:
            raise ValueError(f"Decay rate cannot be negative, got {self.decay_rate}")


class DynamicForgettingSystem:
    """
    动态遗忘与巩固复习系统
    
    该系统监测用户的操作行为，构建个人技能活跃度热力图。
    当检测到某项关键技能节点长期未被调用（熵值升高）时，
    系统会主动生成微测试或情景模拟，帮助用户刷新认知路径。
    
    Example:
        >>> system = DynamicForgettingSystem()
        >>> system.register_skill("危机公关", SkillCategory.CRISIS_MANAGEMENT, 0.9)
        >>> system.record_usage("危机公关")
        >>> system.check_and_generate_review()
    """
    
    def __init__(self, entropy_threshold: float = 0.7, time_window_days: int = 30):
        """
        初始化系统
        
        Args:
            entropy_threshold (float): 触发复习的熵值阈值 (0.0-1.0)
            time_window_days (int): 时间窗口（天数）
        """
        if not 0.0 <= entropy_threshold <= 1.0:
            raise ValueError("Entropy threshold must be between 0 and 1")
        if time_window_days <= 0:
            raise ValueError("Time window must be positive")
            
        self.entropy_threshold = entropy_threshold
        self.time_window_days = time_window_days
        self.skill_database: Dict[str, SkillNode] = {}
        self.interaction_log: List[Dict[str, Any]] = []
        
        logger.info(f"System initialized with threshold={entropy_threshold}, window={time_window_days}d")

    def register_skill(self, 
                       name: str, 
                       category: SkillCategory, 
                       importance: float = 0.5,
                       decay_rate: float = 0.1) -> bool:
        """
        注册一个新的技能节点到系统中
        
        Args:
            name (str): 技能名称
            category (SkillCategory): 技能类别
            importance (float): 重要性权重
            decay_rate (float): 遗忘衰减率
            
        Returns:
            bool: 注册是否成功
            
        Raises:
            ValueError: 如果参数验证失败
        """
        try:
            if name in self.skill_database:
                logger.warning(f"Skill '{name}' already exists, updating...")
                
            skill = SkillNode(
                name=name,
                category=category,
                importance=importance,
                decay_rate=decay_rate
            )
            self.skill_database[name] = skill
            logger.info(f"Skill registered: {name} [{category.value}]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register skill '{name}': {str(e)}")
            return False

    def record_usage(self, skill_name: str, context: Optional[Dict] = None) -> bool:
        """
        记录用户对某项技能的使用行为
        
        该方法更新技能的最后访问时间和访问次数，用于计算活跃度。
        
        Args:
            skill_name (str): 技能名称
            context (Optional[Dict]): 使用上下文信息
            
        Returns:
            bool: 记录是否成功
        """
        if skill_name not in self.skill_database:
            logger.warning(f"Skill '{skill_name}' not found in database")
            return False
            
        try:
            skill = self.skill_database[skill_name]
            skill.last_accessed = datetime.datetime.now()
            skill.access_count += 1
            
            # 记录交互日志
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "skill": skill_name,
                "context": context or {},
                "action": "usage_recorded"
            }
            self.interaction_log.append(log_entry)
            
            logger.debug(f"Usage recorded for '{skill_name}', total count: {skill.access_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording usage for '{skill_name}': {str(e)}")
            return False

    def _calculate_entropy(self, skill: SkillNode) -> float:
        """
        辅助函数：计算技能的认知熵值
        
        熵值反映技能的退化程度。时间越长未使用，熵值越高。
        公式: entropy = 1 - exp(-decay_rate * days_since_last_access)
        
        Args:
            skill (SkillNode): 技能节点对象
            
        Returns:
            float: 熵值 (0.0-1.0)
        """
        now = datetime.datetime.now()
        days_inactive = (now - skill.last_accessed).days
        
        # 基于指数衰减模型计算熵值
        raw_entropy = 1 - (1 / (1 + (days_inactive * skill.decay_rate)))
        
        # 重要性权重调整（重要技能的熵值增长更快，需要更频繁复习）
        weighted_entropy = raw_entropy * (1 + skill.importance)
        
        # 边界检查
        return min(max(weighted_entropy, 0.0), 1.0)

    def generate_heatmap(self) -> Dict[str, float]:
        """
        生成个人技能活跃度热力图
        
        Returns:
            Dict[str, float]: 技能名称到活跃度分数的映射 (活跃度 = 1 - 熵值)
        """
        heatmap = {}
        for name, skill in self.skill_database.items():
            entropy = self._calculate_entropy(skill)
            activity_score = 1.0 - entropy
            heatmap[name] = round(activity_score, 3)
            
        logger.info(f"Heatmap generated for {len(heatmap)} skills")
        return heatmap

    def check_and_generate_review(self) -> List[Dict[str, Any]]:
        """
        核心功能：检查所有技能状态并生成复习任务
        
        遍历技能库，当发现高熵值（低活跃度）技能时，
        根据间隔重复算法生成相应的微测试或情景模拟。
        
        Returns:
            List[Dict[str, Any]]: 需要复习的技能列表及其复习任务
        """
        review_tasks = []
        current_time = datetime.datetime.now()
        
        for name, skill in self.skill_database.items():
            entropy = self._calculate_entropy(skill)
            
            if entropy >= self.entropy_threshold:
                days_since_last = (current_time - skill.last_accessed).days
                
                # 生成复习任务
                task = {
                    "skill_name": name,
                    "category": skill.category.value,
                    "current_entropy": round(entropy, 3),
                    "days_inactive": days_since_last,
                    "importance": skill.importance,
                    "review_type": self._determine_review_type(skill, entropy),
                    "generated_at": current_time.isoformat(),
                    "task_id": self._generate_task_id(name, current_time)
                }
                review_tasks.append(task)
                
                logger.warning(
                    f"Skill decay detected: '{name}' (Entropy: {entropy:.2f}, "
                    f"Inactive: {days_since_last} days)"
                )
        
        if review_tasks:
            logger.info(f"Generated {len(review_tasks)} review tasks")
        else:
            logger.info("All skills are within healthy activity levels")
            
        return review_tasks

    def _determine_review_type(self, skill: SkillNode, entropy: float) -> str:
        """
        辅助函数：根据技能属性和熵值决定复习类型
        
        Args:
            skill (SkillNode): 技能节点
            entropy (float): 当前熵值
            
        Returns:
            str: 复习类型
        """
        if skill.category == SkillCategory.CRISIS_MANAGEMENT:
            return "CRISIS_SIMULATION"
        elif entropy > 0.9:
            return "INTENSIVE_RETEST"
        elif skill.category == SkillCategory.SOFT_SKILL:
            return "SCENARIO_ROLEPLAY"
        else:
            return "MICRO_QUIZ"

    def _generate_task_id(self, skill_name: str, timestamp: datetime.datetime) -> str:
        """
        生成唯一的任务ID
        
        Args:
            skill_name (str): 技能名称
            timestamp (datetime.datetime): 时间戳
            
        Returns:
            str: 唯一任务ID
        """
        raw_string = f"{skill_name}_{timestamp.isoformat()}"
        return hashlib.md5(raw_string.encode()).hexdigest()[:12]

    def export_data(self) -> str:
        """
        导出系统数据为JSON格式
        
        Returns:
            str: JSON格式的数据快照
        """
        data = {
            "metadata": {
                "export_time": datetime.datetime.now().isoformat(),
                "total_skills": len(self.skill_database),
                "threshold": self.entropy_threshold
            },
            "skills": {
                name: {
                    "category": skill.category.value,
                    "last_accessed": skill.last_accessed.isoformat(),
                    "access_count": skill.access_count,
                    "importance": skill.importance,
                    "entropy": self._calculate_entropy(skill)
                }
                for name, skill in self.skill_database.items()
            },
            "heatmap": self.generate_heatmap()
        }
        return json.dumps(data, indent=2)


# ================= 使用示例 =================
if __name__ == "__main__":
    print("=" * 60)
    print("动态遗忘与巩固复习系统 - 演示")
    print("=" * 60)
    
    try:
        # 1. 初始化系统
        system = DynamicForgettingSystem(entropy_threshold=0.65)
        
        # 2. 注册技能
        system.register_skill("Python编程", SkillCategory.TECHNICAL, importance=0.8)
        system.register_skill("危机公关", SkillCategory.CRISIS_MANAGEMENT, importance=0.95)
        system.register_skill("团队协作", SkillCategory.SOFT_SKILL, importance=0.7)
        system.register_skill("机器学习原理", SkillCategory.DOMAIN_KNOWLEDGE, importance=0.6)
        
        # 3. 模拟技能使用 (模拟Python技能经常使用，危机公关长期未用)
        system.record_usage("Python编程")
        system.record_usage("Python编程", context={"project": "AGI_Core"})
        system.record_usage("团队协作")
        
        # 模拟危机公关技能在60天前被访问过
        crisis_skill = system.skill_database["危机公关"]
        crisis_skill.last_accessed = datetime.datetime.now() - datetime.timedelta(days=60)
        
        # 模拟机器学习技能在20天前被访问过
        ml_skill = system.skill_database["机器学习原理"]
        ml_skill.last_accessed = datetime.datetime.now() - datetime.timedelta(days=20)
        
        # 4. 生成热力图
        print("\n[当前技能活跃度热力图]")
        heatmap = system.generate_heatmap()
        for skill, score in sorted(heatmap.items(), key=lambda x: x[1]):
            status = "✅ 活跃" if score > 0.5 else "⚠️ 警告" if score > 0.3 else "🔥 危险"
            print(f"  - {skill}: {score:.2f} {status}")
        
        # 5. 检查并生成复习任务
        print("\n[系统监测结果]")
        tasks = system.check_and_generate_review()
        
        if tasks:
            print(f"检测到 {len(tasks)} 项技能需要复习:\n")
            for task in tasks:
                print(f"  📌 技能: {task['skill_name']}")
                print(f"     类型: {task['review_type']}")
                print(f"     熵值: {task['current_entropy']}")
                print(f"     未动用: {task['days_inactive']} 天")
                print(f"     任务ID: {task['task_id']}")
                print("-" * 40)
        else:
            print("所有技能状态良好，无需复习。")
            
        # 6. 导出数据示例
        print("\n[数据导出片段]")
        print(system.export_data()[:300] + "...")
        
    except Exception as e:
        logger.error(f"System error: {str(e)}", exc_info=True)