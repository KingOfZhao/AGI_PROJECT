"""
模块名称: industrial_meta_skill_generator
版本: 1.0.0
描述: 面向工业场景的元技能生成器。该模块实现了一个自动化系统，能够通过阅读设备说明书（自上而下的语义分析）
      和试探性操作（自下而上的交互探索），为新设备生成操作技能树。同时，系统会将新生成的技能与现有的
      1630个基础技能节点进行向量相似度计算，评估重叠度，以实现技能复用和避免冗余。

核心功能:
    1. 说明书解析: 提取文本中的操作指令和状态转移。
    2. 设备试探: 模拟探索性交互，记录动作-反馈对。
    3. 技能合成: 将上述两种信息融合为结构化的技能树。
    4. 重叠度评估: 基于语义向量计算新技能与现有技能库的重合程度。

依赖库:
    - numpy: 数值计算和向量化操作
    - logging: 日志记录
    - dataclasses: 数据结构定义
    - typing: 类型注解
"""

import logging
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
SKILL_DATABASE_SIZE = 1630  # 现有技能节点数量
SIMILARITY_THRESHOLD = 0.85  # 判定为重复技能的相似度阈值

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 技能的唯一标识符 (基于内容哈希生成)
        name (str): 技能名称
        description (str): 详细描述
        action_vector (List[float]): 动作的语义向量表示 (简化为随机向量用于演示)
        pre_conditions (List[str]): 执行前置条件
        post_effects (List[str]): 执行后效果
        source (str): 技能来源
        """
    id: str = ""
    name: str = ""
    description: str = ""
    action_vector: List[float] = field(default_factory=list)
    pre_conditions: List[str] = field(default_factory=list)
    post_effects: List[str] = field(default_factory=list)
    source: str = "unknown"

    def __post_init__(self):
        if not self.id:
            # 基于内容生成唯一ID
            content_str = f"{self.name}{self.description}{self.action_vector}"
            self.id = hashlib.md5(content_str.encode('utf-8')).hexdigest()[:12]
        if not self.action_vector:
            # 如果没有向量，生成一个模拟向量 (实际应用中应使用Embedding模型)
            self.action_vector = self._generate_mock_vector()

    def _generate_mock_vector(self) -> List[float]:
        """生成模拟的语义向量 (实际工程中替换为BERT/Word2Vec)"""
        import random
        random.seed(hash(self.name))
        return [random.uniform(-1, 1) for _ in range(128)]

@dataclass
class DeviceSpec:
    """设备说明书数据结构"""
    raw_text: str
    commands: List[str] = field(default_factory=list)

class MetaSkillGenerator:
    """
    元技能生成器主类。
    
    负责协调自上而下的文本理解和自下而上的交互探索，
    生成标准化的技能树，并与现有技能库进行比对。
    """

    def __init__(self, existing_skills: Optional[List[SkillNode]] = None):
        """
        初始化生成器。
        
        Args:
            existing_skills (Optional[List[SkillNode]]): 现有的技能库。
                                                         如果为None，则模拟初始化一个标准库。
        """
        self.existing_skills = existing_skills if existing_skills else self._load_mock_skill_database()
        logger.info(f"Skill Generator initialized with {len(self.existing_skills)} existing skills.")

    def _load_mock_skill_database(self) -> List[SkillNode]:
        """模拟加载现有的1630个技能节点"""
        logger.info("Loading mock skill database...")
        mock_skills = []
        base_actions = ["rotate", "grasp", "move", "heat", "press", "scan", "inject"]
        
        # 生成模拟数据以匹配 SKILL_DATABASE_SIZE
        for i in range(SKILL_DATABASE_SIZE):
            action = base_actions[i % len(base_actions)]
            skill = SkillNode(
                name=f"{action}_v{i}",
                description=f"Standard industrial action: {action} variant {i}",
                source="legacy_db"
            )
            mock_skills.append(skill)
        return mock_skills

    def parse_manual_top_down(self, spec: DeviceSpec) -> List[SkillNode]:
        """
        [核心函数 1] 自上而下：解析说明书文本。
        
        使用正则表达式和关键词提取技术，从非结构化文本中识别潜在的操作指令。
        
        Args:
            spec (DeviceSpec): 包含原始文本的设备说明书对象。
            
        Returns:
            List[SkillNode]: 从文本中提取出的潜在技能节点列表。
            
        Raises:
            ValueError: 如果输入文本为空或无效。
        """
        if not spec.raw_text or len(spec.raw_text.strip()) < 10:
            logger.error("Invalid manual text provided.")
            raise ValueError("Manual text must not be empty or too short.")

        logger.info("Starting Top-Down analysis (Manual Parsing)...")
        extracted_skills = []
        
        # 模拟NLP解析逻辑：寻找 "Press ... to ..." 或 "Rotate ... for ..." 模式
        # 这里的正则仅作演示，实际AGI系统会使用LLM或专用NLP模型
        pattern = r"(?:Press|Rotate|Hold|Turn|Start)\s+([a-zA-Z0-9_]+)\s+(?:to|for)\s+([a-zA-Z0-9_\s]+)"
        matches = re.findall(pattern, spec.raw_text, re.IGNORECASE)

        for match in matches:
            trigger, outcome = match
            node = SkillNode(
                name=f"manual_op_{trigger.strip()}",
                description=f"Trigger {trigger.strip()} to achieve {outcome.strip()}",
                source="manual_extraction",
                pre_conditions=["manual_context_valid"],
                post_effects=[outcome.strip()]
            )
            extracted_skills.append(node)
            
        logger.info(f"Extracted {len(extracted_skills)} candidate skills from manual.")
        return extracted_skills

    def explore_device_bottom_up(self, device_id: str, trial_count: int = 5) -> List[SkillNode]:
        """
        [核心函数 2] 自下而上：试探性操作与交互学习。
        
        模拟对物理设备的黑盒测试。发送随机或结构化指令，
        观察状态变化，从而推导因果关系（技能）。
        
        Args:
            device_id (str): 目标设备ID。
            trial_count (int): 尝试操作的次数。
            
        Returns:
            List[SkillNode]: 通过交互发现的技能节点列表。
        """
        if trial_count <= 0:
            return []

        logger.info(f"Starting Bottom-Up exploration on device {device_id}...")
        discovered_skills = []
        
        # 模拟探索过程
        for i in range(trial_count):
            # 模拟发送指令
            action = f"test_action_{i}"
            # 模拟接收反馈 (这里简单模拟反馈逻辑)
            # 假设有50%概率成功触发状态变更
            success = (hash(f"{device_id}{i}") % 2) == 0
            
            if success:
                effect = f"state_changed_to_S{i}"
                node = SkillNode(
                    name=f"exploratory_{action}",
                    description=f"Discovered by trial: {action} leads to {effect}",
                    source="exploration",
                    post_effects=[effect]
                )
                discovered_skills.append(node)
                
        logger.info(f"Discovered {len(discovered_skills)} skills via exploration.")
        return discovered_skills

    def _calculate_cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        [辅助函数] 计算两个向量的余弦相似度。
        
        Args:
            vec_a (List[float]): 向量A
            vec_b (List[float]): 向量B
            
        Returns:
            float: 相似度得分 (0.0 到 1.0)
        """
        if len(vec_a) != len(vec_b):
            return 0.0
            
        # 手动实现点积和模长，避免引入额外依赖如scipy，保持环境纯净
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a**2 for a in vec_a) ** 0.5
        norm_b = sum(b**2 for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

    def verify_and_merge_skills(self, candidate_skills: List[SkillNode]) -> Tuple[List[SkillNode], Dict[str, float]]:
        """
        验证新技能是否与现有技能库重叠。
        
        Args:
            candidate_skills (List[SkillNode]): 待验证的新技能列表。
            
        Returns:
            Tuple[List[SkillNode], Dict[str, float]]: 
                - filtered_skills: 去重后需要添加的新技能列表。
                - overlap_report: 每个候选技能与现有库的最大重叠度报告。
        """
        logger.info("Verifying skill overlaps...")
        filtered_skills = []
        overlap_report = {}

        for candidate in candidate_skills:
            max_sim = 0.0
            # 在实际工程中，这里会使用向量数据库(如Faiss)进行ANN搜索，而不是遍历
            # 这里为了演示逻辑完整性进行线性搜索
            
            # 仅为了性能，随机抽样一部分现有技能进行比较，模拟大规模检索
            import random
            sample_existing = random.sample(self.existing_skills, min(100, len(self.existing_skills)))
            
            for existing in sample_existing:
                sim = self._calculate_cosine_similarity(candidate.action_vector, existing.action_vector)
                if sim > max_sim:
                    max_sim = sim
            
            overlap_report[candidate.name] = max_sim
            
            if max_sim < SIMILARITY_THRESHOLD:
                logger.debug(f"Skill '{candidate.name}' is unique (Max Sim: {max_sim:.2f}). Adding to tree.")
                filtered_skills.append(candidate)
            else:
                logger.info(f"Skill '{candidate.name}' duplicates existing skill (Sim: {max_sim:.2f}). Skipping.")

        return filtered_skills, overlap_report

def main():
    """
    使用示例：模拟对新设备 'X-100 Mechanic Arm' 的技能生成过程。
    """
    # 1. 准备模拟数据
    manual_text = """
    Device X-100 Operation Manual.
    1. Press red_button to activate emergency_stop.
    2. Rotate valve_counter_clockwise to release pressure.
    3. Hold safety_key for 3 seconds to unlock hatch.
    """
    
    device_spec = DeviceSpec(raw_text=manual_text)
    generator = MetaSkillGenerator()

    print("-" * 50)
    print("Starting Meta-Skill Generation Process...")
    print("-" * 50)

    try:
        # 2. 自上而下分析
        manual_skills = generator.parse_manual_top_down(device_spec)
        
        # 3. 自下而上探索
        explored_skills = generator.explore_device_bottom_up("X-100", trial_count=10)
        
        # 4. 合并候选技能
        all_candidates = manual_skills + explored_skills
        
        # 5. 去重与评估
        new_skills, report = generator.verify_and_merge_skills(all_candidates)
        
        # 6. 结果输出
        print(f"\nTotal Candidates Extracted: {len(all_candidates)}")
        print(f"New Unique Skills Generated: {len(new_skills)}")
        print("\nOverlap Report (Sample):")
        for name, score in list(report.items())[:5]:
            print(f" - {name}: {score:.2f} similarity")
            
        print("\nGenerated Skill Tree Structure (JSON Preview):")
        if new_skills:
            # 打印第一个技能的详细信息
            sample_skill = new_skills[0]
            print(json.dumps({
                "id": sample_skill.id,
                "name": sample_skill.name,
                "source": sample_skill.source,
                "effects": sample_skill.post_effects
            }, indent=2))
            
    except ValueError as e:
        logger.error(f"Process failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    main()