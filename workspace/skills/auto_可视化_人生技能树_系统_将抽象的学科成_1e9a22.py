"""
Module: auto_可视化_人生技能树_系统_将抽象的学科成_1e9a22
Description: 可视化'人生技能树'系统。将抽象的学科成绩转化为具象的'职业天赋树'。
             支持跨学科组合解锁隐藏路径，将线性学习变为网状探索。
Author: AGI System
Version: 1.0.0
"""

import logging
import json
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillStatus(Enum):
    """技能节点状态枚举"""
    LOCKED = "locked"           # 锁定（迷雾中）
    UNLOCKED = "unlocked"       # 已解锁（可见但未习得）
    MASTERED = "mastered"       # 已掌握（点亮）
    HIDDEN = "hidden"           # 隐藏职业路径

@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    Attributes:
        id: 唯一标识符
        name: 节点名称
        category: 所属分支 (如 '逻辑构筑', '艺术表达')
        difficulty: 难度系数 (1-10)
        prerequisites: 前置技能ID列表
        status: 当前状态
        mastery_level: 掌握度 (0-100)
        description: 节点描述
        unlocks: 该节点能解锁的其他节点或职业路径
    """
    id: str
    name: str
    category: str
    difficulty: int = 1
    prerequisites: List[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.LOCKED
    mastery_level: int = 0
    description: str = ""
    unlocks: List[str] = field(default_factory=list)

    def __post_init__(self):
        """数据验证"""
        if not 1 <= self.difficulty <= 10:
            raise ValueError(f"Difficulty must be between 1 and 10, got {self.difficulty}")
        if not 0 <= self.mastery_level <= 100:
            raise ValueError(f"Mastery level must be between 0 and 100, got {self.mastery_level}")

class LifeSkillTreeSystem:
    """
    人生技能树系统核心类
    
    将学科成绩转化为RPG风格的技能树系统，支持：
    1. 节点解锁与点亮机制
    2. 跨学科组合发现隐藏职业
    3. 地图迷雾探索机制
    4. 可视化数据导出
    
    Example:
        >>> system = LifeSkillTreeSystem()
        >>> system.load_skill_tree(default_skill_data())
        >>> system.update_skill_mastery("math_basic", 90)
        >>> system.check_synergy_unlocks()
        >>> print(system.generate_visualization_data())
    """
    
    def __init__(self):
        """初始化技能树系统"""
        self.nodes: Dict[str, SkillNode] = {}
        self.hidden_paths: Dict[str, Dict] = {}
        self.activated_synergies: Set[str] = set()
        logger.info("LifeSkillTreeSystem initialized")
    
    def load_skill_tree(self, skill_data: Dict[str, Dict]) -> None:
        """
        加载技能树数据
        
        Args:
            skill_data: 技能节点字典，格式为 {'node_id': {attributes}}
        
        Raises:
            ValueError: 如果数据格式无效
        """
        try:
            for node_id, attrs in skill_data.items():
                node = SkillNode(
                    id=node_id,
                    name=attrs.get('name', node_id),
                    category=attrs.get('category', 'General'),
                    difficulty=attrs.get('difficulty', 1),
                    prerequisites=attrs.get('prerequisites', []),
                    description=attrs.get('description', ''),
                    unlocks=attrs.get('unlocks', [])
                )
                self.nodes[node_id] = node
                logger.debug(f"Loaded node: {node_id} - {node.name}")
            
            # 加载隐藏路径配置
            if 'hidden_paths' in skill_data.get('__meta__', {}):
                self.hidden_paths = skill_data['__meta__']['hidden_paths']
            
            self._update_node_visibility()
            logger.info(f"Skill tree loaded with {len(self.nodes)} nodes")
            
        except Exception as e:
            logger.error(f"Failed to load skill tree: {str(e)}")
            raise ValueError(f"Invalid skill data format: {str(e)}")
    
    def update_skill_mastery(self, node_id: str, score: int) -> bool:
        """
        更新技能掌握度（基于成绩）
        
        Args:
            node_id: 技能节点ID
            score: 学科成绩 (0-100)
        
        Returns:
            bool: 是否成功更新并达到掌握阈值
        
        Raises:
            KeyError: 如果节点不存在
            ValueError: 如果成绩范围无效
        """
        # 边界检查
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")
        
        if node_id not in self.nodes:
            logger.error(f"Node not found: {node_id}")
            raise KeyError(f"Skill node '{node_id}' does not exist")
        
        node = self.nodes[node_id]
        old_level = node.mastery_level
        node.mastery_level = score
        
        # 判断是否掌握 (成绩>=85视为掌握)
        if score >= 85 and node.status != SkillStatus.MASTERED:
            node.status = SkillStatus.MASTERED
            self._handle_skill_mastery(node)
            logger.info(f"Skill MASTERED: {node.name} (Score: {score})")
            return True
        elif score >= 60 and node.status == SkillStatus.LOCKED:
            node.status = SkillStatus.UNLOCKED
            logger.info(f"Skill UNLOCKED: {node.name} (Score: {score})")
        
        logger.debug(f"Updated {node_id}: {old_level}% -> {score}%")
        return False
    
    def _handle_skill_mastery(self mastered_node: SkillNode) -> None:
        """
        处理技能掌握后的连锁反应（内部方法）
        
        Args:
            mastered_node: 刚被掌握的技能节点
        """
        # 解锁后续节点
        for unlock_id in mastered_node.unlocks:
            if unlock_id in self.nodes:
                target_node = self.nodes[unlock_id]
                if target_node.status == SkillStatus.LOCKED:
                    # 检查是否所有前置条件都已满足
                    if self._check_prerequisites(target_node):
                        target_node.status = SkillStatus.UNLOCKED
                        logger.info(f"Unlocked new skill: {target_node.name}")
        
        # 检查跨学科协同效应
        self.check_synergy_unlocks()
    
    def _check_prerequisites(self, node: SkillNode) -> bool:
        """
        检查节点前置条件是否满足（辅助函数）
        
        Args:
            node: 要检查的技能节点
        
        Returns:
            bool: 是否满足所有前置条件
        """
        for prereq_id in node.prerequisites:
            if prereq_id not in self.nodes:
                logger.warning(f"Missing prerequisite node: {prereq_id}")
                continue
            if self.nodes[prereq_id].status != SkillStatus.MASTERED:
                return False
        return True
    
    def check_synergy_unlocks(self) -> List[str]:
        """
        检查跨学科组合解锁的隐藏职业路径
        
        Returns:
            List[str]: 新激活的协同路径列表
        
        Example:
            >>> system.check_synergy_unlocks()
            ['Interaction Designer', 'Data Artist']
        """
        newly_activated = []
        
        for path_id, path_config in self.hidden_paths.items():
            if path_id in self.activated_synergies:
                continue
            
            required_skills = path_config.get('requires', [])
            min_mastery = path_config.get('min_mastery', 80)
            
            # 检查是否满足所有组合条件
            all_satisfied = True
            for skill_id in required_skills:
                if skill_id not in self.nodes:
                    all_satisfied = False
                    break
                if self.nodes[skill_id].mastery_level < min_mastery:
                    all_satisfied = False
                    break
            
            if all_satisfied:
                self.activated_synergies.add(path_id)
                newly_activated.append(path_config.get('name', path_id))
                logger.info(f"SYNERGY UNLOCKED: {path_config.get('name')} "
                           f"(Combination: {', '.join(required_skills)})")
        
        return newly_activated
    
    def generate_visualization_data(self) -> Dict:
        """
        生成可视化所需的数据结构
        
        Returns:
            Dict: 包含节点、边和元数据的可视化字典
        
        Output Format:
            {
                "nodes": [
                    {"id": str, "label": str, "category": str, 
                     "status": str, "mastery": int, "x": int, "y": int}
                ],
                "edges": [
                    {"from": str, "to": str, "type": str}
                ],
                "synergies": List[Dict],
                "meta": Dict
            }
        """
        nodes_data = []
        edges_data = []
        
        # 生成节点数据
        for node_id, node in self.nodes.items():
            # 简单的布局算法（实际应用中可替换为力导向布局）
            category_offset = hash(node.category) % 5
            x_pos = (len(nodes_data) % 10) * 120
            y_pos = (len(nodes_data) // 10) * 100 + category_offset * 50
            
            nodes_data.append({
                "id": node_id,
                "label": node.name,
                "category": node.category,
                "status": node.status.value,
                "mastery": node.mastery_level,
                "x": x_pos,
                "y": y_pos,
                "description": node.description
            })
            
            # 生成边数据
            for prereq in node.prerequisites:
                edges_data.append({
                    "from": prereq,
                    "to": node_id,
                    "type": "prerequisite"
                })
        
        # 生成协同路径数据
        synergies_data = []
        for path_id in self.activated_synergies:
            path_config = self.hidden_paths.get(path_id, {})
            synergies_data.append({
                "id": path_id,
                "name": path_config.get('name', path_id),
                "combination": path_config.get('requires', []),
                "description": path_config.get('description', '')
            })
        
        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "synergies": synergies_data,
            "meta": {
                "total_nodes": len(self.nodes),
                "mastered_count": sum(1 for n in self.nodes.values() 
                                     if n.status == SkillStatus.MASTERED),
                "synergies_activated": len(self.activated_synergies)
            }
        }
    
    def _update_node_visibility(self) -> None:
        """更新所有节点的可见性状态（内部方法）"""
        for node in self.nodes.values():
            if node.status == SkillStatus.LOCKED and not node.prerequisites:
                node.status = SkillStatus.UNLOCKED

def default_skill_data() -> Dict:
    """
    提供默认的技能树数据模板
    
    Returns:
        Dict: 包含基础技能节点和隐藏路径的配置字典
    """
    return {
        "__meta__": {
            "hidden_paths": {
                "interaction_designer": {
                    "name": "交互设计师",
                    "requires": ["programming_basic", "art_basic"],
                    "min_mastery": 80,
                    "description": "结合编程与艺术，创造用户体验"
                },
                "data_scientist": {
                    "name": "数据科学家",
                    "requires": ["math_advanced", "programming_intermediate"],
                    "min_mastery": 85,
                    "description": "用数学和编程解读数据宇宙"
                }
            }
        },
        "math_basic": {
            "name": "数学基础",
            "category": "逻辑构筑",
            "difficulty": 3,
            "description": "基础运算与代数概念",
            "unlocks": ["math_advanced", "physics_basic"]
        },
        "math_advanced": {
            "name": "微积分基础",
            "category": "逻辑构筑",
            "difficulty": 7,
            "prerequisites": ["math_basic"],
            "description": "变化与运动的数学描述",
            "unlocks": ["physics_advanced"]
        },
        "programming_basic": {
            "name": "编程入门",
            "category": "数字工艺",
            "difficulty": 4,
            "description": "与机器对话的第一步",
            "unlocks": ["programming_intermediate"]
        },
        "programming_intermediate": {
            "name": "算法与数据结构",
            "category": "数字工艺",
            "difficulty": 6,
            "prerequisites": ["programming_basic"],
            "description": "高效解决问题的艺术"
        },
        "art_basic": {
            "name": "艺术表达",
            "category": "创意构建",
            "difficulty": 3,
            "description": "色彩、构图与视觉语言"
        },
        "physics_basic": {
            "name": "物理学 I",
            "category": "自然科学",
            "difficulty": 5,
            "prerequisites": ["math_basic"],
            "description": "物质与能量的基本规律"
        },
        "physics_advanced": {
            "name": "物理学 II",
            "category": "自然科学",
            "difficulty": 8,
            "prerequisites": ["math_advanced", "physics_basic"],
            "description": "量子世界的奥秘"
        }
    }

# 使用示例
if __name__ == "__main__":
    try:
        # 初始化系统
        skill_system = LifeSkillTreeSystem()
        
        # 加载技能树
        skill_system.load_skill_tree(default_skill_data())
        
        # 模拟学生成绩更新
        print("\n=== 模拟学习进程 ===")
        skill_system.update_skill_mastery("math_basic", 92)    # 掌握数学基础
        skill_system.update_skill_mastery("programming_basic", 88)  # 掌握编程入门
        skill_system.update_skill_mastery("art_basic", 85)     # 掌握艺术基础
        
        # 检查跨学科解锁
        synergies = skill_system.check_synergy_unlocks()
        print(f"\n解锁的隐藏路径: {synergies}")
        
        # 生成可视化数据
        vis_data = skill_system.generate_visualization_data()
        print(f"\n可视化统计: {vis_data['meta']}")
        
        # 导出为JSON（实际应用中可接入前端可视化库）
        with open('skill_tree_visualization.json', 'w', encoding='utf-8') as f:
            json.dump(vis_data, f, ensure_ascii=False, indent=2)
            print("\n可视化数据已导出到 skill_tree_visualization.json")
            
    except Exception as e:
        logger.error(f"System error: {str(e)}", exc_info=True)
        raise