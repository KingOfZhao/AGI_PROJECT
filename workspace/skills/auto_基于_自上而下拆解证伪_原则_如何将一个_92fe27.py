"""
模块名称: industrial_sop_decomposer
描述: 基于自上而下拆解证伪原则，将复杂工业SOP动态拆解为DAG技能树。
      核心功能包括SOP文本解析、逻辑断层检测、技能节点补全及DAG构建。
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    属性:
        id: 技能唯一标识符
        name: 技能名称
        description: 技能描述
        inputs: 输入参数列表
        outputs: 输出参数列表
        dependencies: 依赖的技能ID列表
    """
    id: str
    name: str
    description: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.inputs, list):
            self.inputs = [self.inputs]
        if not isinstance(self.outputs, list):
            self.outputs = [self.outputs]

class SOPDecomposer:
    """
    工业SOP分解器，基于自上而下拆解证伪原则构建DAG技能树
    
    示例:
        >>> skill_library = {
        ...     "SK001": SkillNode(id="SK001", name="部件准备", outputs=["部件A", "部件B"]),
        ...     "SK002": SkillNode(id="SK002", name="部件组装", inputs=["部件A", "部件B"], outputs=["组装体"]),
        ...     "SK003": SkillNode(id="SK003", name="质量检测", inputs=["组装体"], outputs=["合格证"])
        ... }
        >>> decomposer = SOPDecomposer(skill_library)
        >>> sop_text = "1. 准备部件\\n2. 组装部件\\n3. 质量检测"
        >>> dag = decomposer.decompose_sop(sop_text)
    """
    
    def __init__(self, skill_library: Dict[str, SkillNode]):
        """
        初始化SOP分解器
        
        参数:
            skill_library: 可用的技能库，包含所有可调用的技能节点
        """
        self._validate_skill_library(skill_library)
        self.skill_library = skill_library
        self.skill_index = self._build_skill_index()
        logger.info(f"SOPDecomposer initialized with {len(skill_library)} skills")
    
    def _validate_skill_library(self, library: Dict[str, SkillNode]) -> None:
        """验证技能库的完整性和正确性"""
        if not library:
            raise ValueError("技能库不能为空")
        
        for skill_id, skill in library.items():
            if not isinstance(skill, SkillNode):
                raise TypeError(f"技能库值必须是SkillNode类型，发现 {type(skill)}")
            if skill.id != skill_id:
                raise ValueError(f"技能ID不匹配: {skill_id} != {skill.id}")
    
    def _build_skill_index(self) -> Dict[str, List[SkillNode]]:
        """
        构建技能索引，映射输入/输出到对应技能节点
        
        返回:
            字典，键为输入/输出名称，值为提供该输出的技能列表
        """
        index = defaultdict(list)
        for skill in self.skill_library.values():
            for output in skill.outputs:
                index[output].append(skill)
        return index
    
    def decompose_sop(self, sop_text: str) -> Dict[str, SkillNode]:
        """
        分解SOP文本为DAG技能树
        
        参数:
            sop_text: SOP文本描述，每行一个步骤
            
        返回:
            DAG技能树，包含所有必要的技能节点和依赖关系
            
        异常:
            ValueError: 如果SOP文本为空或无法分解
        """
        if not sop_text.strip():
            raise ValueError("SOP文本不能为空")
        
        steps = self._parse_sop_steps(sop_text)
        if not steps:
            raise ValueError("未能从SOP文本中解析出有效步骤")
        
        logger.info(f"开始分解SOP，共 {len(steps)} 个步骤")
        
        # 初始化DAG
        dag = {}
        # 跟踪当前可用的输出
        available_outputs: Set[str] = set()
        # 前一个步骤的技能ID，用于建立依赖关系
        prev_skill_ids: List[str] = []
        
        for step_desc in steps:
            try:
                skill = self._find_matching_skill(step_desc, available_outputs)
                
                # 建立与前序步骤的依赖关系
                if prev_skill_ids:
                    skill.dependencies.extend(prev_skill_ids)
                
                dag[skill.id] = skill
                available_outputs.update(skill.outputs)
                prev_skill_ids = [skill.id]
                
                logger.debug(f"步骤 '{step_desc}' 映射到技能 '{skill.name}'")
            except ValueError as e:
                logger.error(f"步骤 '{step_desc}' 分解失败: {str(e)}")
                raise
        
        self._validate_dag(dag)
        logger.info("SOP分解完成，DAG验证通过")
        return dag
    
    def _parse_sop_steps(self, sop_text: str) -> List[str]:
        """
        解析SOP文本为步骤列表
        
        参数:
            sop_text: 原始SOP文本
            
        返回:
            清理后的步骤描述列表
        """
        steps = []
        for line in sop_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # 处理常见的步骤编号格式
            if line[0].isdigit():
                # 去除数字编号
                line = line.split('.', 1)[-1].strip()
            elif line.startswith(('•', '-', '*')):
                # 去除项目符号
                line = line[1:].strip()
                
            if line:
                steps.append(line)
        
        return steps
    
    def _find_matching_skill(self, step_desc: str, available_outputs: Set[str]) -> SkillNode:
        """
        根据步骤描述和可用输出查找匹配的技能节点
        
        参数:
            step_desc: 步骤描述文本
            available_outputs: 当前可用的输出集合
            
        返回:
            匹配的技能节点
            
        异常:
            ValueError: 如果找不到匹配的技能或输入条件不满足
        """
        # 简化的匹配逻辑，实际应用中可能需要更复杂的NLP处理
        best_match = None
        best_score = -1
        
        for skill in self.skill_library.values():
            # 计算名称相似度分数 (简化版)
            name_words = set(skill.name.lower().split())
            desc_words = set(step_desc.lower().split())
            common_words = name_words & desc_words
            score = len(common_words) / max(len(name_words), 1)
            
            # 检查输入条件是否满足
            missing_inputs = [inp for inp in skill.inputs if inp not in available_outputs]
            
            if not missing_inputs and score > best_score:
                best_score = score
                best_match = skill
        
        if best_match is None:
            raise ValueError(f"无法找到匹配的技能或输入条件不满足: {step_desc}")
        
        # 创建技能节点的深拷贝以避免修改原始库
        return SkillNode(
            id=f"{best_match.id}_{step_desc[:8]}",
            name=best_match.name,
            description=step_desc,
            inputs=best_match.inputs.copy(),
            outputs=best_match.outputs.copy(),
            dependencies=best_match.dependencies.copy()
        )
    
    def _validate_dag(self, dag: Dict[str, SkillNode]) -> None:
        """
        验证DAG的完整性和无环性
        
        参数:
            dag: 待验证的DAG
            
        异常:
            ValueError: 如果DAG无效或包含环
        """
        if not dag:
            raise ValueError("DAG不能为空")
        
        # 检查所有依赖是否存在
        all_skill_ids = set(dag.keys())
        for skill in dag.values():
            for dep_id in skill.dependencies:
                if dep_id not in all_skill_ids:
                    raise ValueError(f"技能 '{skill.id}' 依赖不存在的技能 '{dep_id}'")
        
        # 检查DAG是否无环
        visited = set()
        recursion_stack = set()
        
        def has_cycle(skill_id: str) -> bool:
            visited.add(skill_id)
            recursion_stack.add(skill_id)
            
            for dep_id in dag[skill_id].dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in recursion_stack:
                    return True
            
            recursion_stack.remove(skill_id)
            return False
        
        for skill_id in dag:
            if skill_id not in visited:
                if has_cycle(skill_id):
                    raise ValueError("DAG包含环，不是有效的有向无环图")

def example_usage():
    """使用示例: 组装减速机的SOP分解"""
    # 创建模拟技能库
    skill_library = {
        "SK001": SkillNode(
            id="SK001",
            name="准备齿轮和轴",
            outputs=["齿轮", "轴"]
        ),
        "SK002": SkillNode(
            id="SK002",
            name="安装轴承",
            inputs=["轴"],
            outputs=["带轴承的轴"]
        ),
        "SK003": SkillNode(
            id="SK003",
            name="齿轮热套",
            inputs=["齿轮", "带轴承的轴"],
            outputs["齿轮轴组件"]
        ),
        "SK004": SkillNode(
            id="SK004",
            name="组装减速机壳体",
            outputs=["减速机壳体"]
        ),
        "SK005": SkillNode(
            id="SK005",
            name="最终装配",
            inputs=["齿轮轴组件", "减速机壳体"],
            outputs=["完整减速机"]
        )
    }
    
    # 初始化分解器
    decomposer = SOPDecomposer(skill_library)
    
    # 示例SOP文本
    sop_text = """
    1. 准备所有必要的齿轮和轴
    2. 在轴上安装轴承
    3. 将齿轮热套到轴上
    4. 组装减速机壳体
    5. 进行最终装配
    """
    
    try:
        # 分解SOP
        dag = decomposer.decompose_sop(sop_text)
        
        # 打印结果
        print("生成的DAG技能树:")
        for skill_id, skill in dag.items():
            print(f"{skill_id}: {skill.name}")
            print(f"  输入: {skill.inputs}")
            print(f"  输出: {skill.outputs}")
            print(f"  依赖: {skill.dependencies}\n")
            
    except ValueError as e:
        print(f"SOP分解失败: {str(e)}")

if __name__ == "__main__":
    example_usage()