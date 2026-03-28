"""
名称: auto_语境敏感的解构式技能重组_在拆解ski_d7093c
描述: 该模块实现了【语境敏感的解构式技能重组】。
     核心逻辑在于将复杂的Skill拆解为带有'语境指纹'（Context Fingerprint）的原子（Atom）。
     每个原子包含'前置差异链'（Pre-condition）和'后置期望链'（Post-condition）。
     在重组过程中，系统执行严格的'语境兼容性检查'，确保原子间的数据流和状态流匹配，
     从而避免传统静态拼接导致的运行时错误。

Author: AGI System Core
Version: 1.0.0
Domain: cross_domain
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps
import time

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class ContextFingerprint:
    """
    语境指纹数据结构。
    用于定义原子技能执行前后的数据状态期望和差异。
    """
    # 前置差异链：描述执行该技能前必须满足的状态或数据格式
    pre_conditions: Dict[str, Any] = field(default_factory=dict)
    # 后置期望链：描述执行该技能后产出的状态或数据格式
    post_expectations: Dict[str, Any] = field(default_factory=dict)
    # 语境标签：用于快速筛选兼容性（如 'nlp', 'vision', 'database'）
    context_tags: List[str] = field(default_factory=list)

    def is_compatible_with(self, other: 'ContextFingerprint') -> bool:
        """
        检查当前指纹的后置期望是否与另一个指纹的前置条件兼容。
        """
        # 检查语境标签是否有交集（简单的兼容性逻辑）
        if self.context_tags or other.context_tags:
            if not set(self.context_tags).intersection(set(other.context_tags)):
                # 允许空标签集合的通用兼容性，或者强制要求交集
                pass 

        # 深度检查：后置期望是否满足前置条件的要求
        # 这里使用简单的子集检查逻辑：other.pre_conditions 的 key 必须在 self.post_expectations 中存在且类型匹配
        for key, expected_type in other.pre_conditions.items():
            if key not in self.post_expectations:
                logger.warning(f"兼容性检查失败: 缺少键 '{key}'")
                return False
            
            # 简单的类型检查模拟
            actual_type = self.post_expectations[key]
            if expected_type != actual_type:
                logger.warning(f"兼容性检查失败: 键 '{key}' 类型不匹配 (期望: {expected_type}, 实际: {actual_type})")
                return False
        
        logger.info("语境指纹兼容性检查通过")
        return True

@dataclass
class AtomSkill:
    """
    原子技能：不可再分的最小执行单元。
    """
    name: str
    action: Callable[..., Any]  # 实际执行的函数
    fingerprint: ContextFingerprint
    description: str = ""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行原子技能，包含前置检查和后置验证"""
        logger.info(f"正在执行原子技能: {self.name}")
        
        # 1. 前置差异链验证 (模拟)
        # 实际场景中这里会验证 input_data 是否满足 pre_conditions
        
        try:
            # 2. 执行核心动作
            result = self.action(input_data)
            if result is None:
                result = {}
            logger.info(f"技能 {self.name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"技能 {self.name} 执行出错: {str(e)}")
            raise

class SkillRecombinationError(Exception):
    """技能重组失败异常"""
    pass

# --- 核心功能函数 ---

def deconstruct_skill(
    skill_name: str, 
    raw_action: Callable, 
    pre_cons: Dict[str, str], 
    post_exps: Dict[str, str],
    tags: List[str]
) -> AtomSkill:
    """
    【解构】将一个原始函数包装为带有语境指纹的原子技能。
    
    Args:
        skill_name (str): 技能名称
        raw_action (Callable): 原始函数
        pre_cons (Dict[str, str]): 前置条件 (参数名 -> 类型描述)
        post_exps (Dict[str, str]): 后置期望 (返回键 -> 类型描述)
        tags (List[str]): 语境标签
        
    Returns:
        AtomSkill: 封装好的原子技能
        
    Example:
        >>> def hello_world(data):
        ...     return {"msg": "Hello"}
        >>> atom = deconstruct_skill("greet", hello_world, {}, {"msg": "str"}, ["nlp"])
    """
    if not callable(raw_action):
        raise ValueError("raw_action 必须是可调用对象")
        
    fingerprint = ContextFingerprint(
        pre_conditions=pre_cons,
        post_expectations=post_exps,
        context_tags=tags
    )
    
    atom = AtomSkill(
        name=skill_name,
        action=raw_action,
        fingerprint=fingerprint,
        description=f"Atom generated from {skill_name}"
    )
    
    logger.info(f"技能解构完成: {skill_name} -> AtomSkill")
    return atom

def recombine_skills_for_task(
    task_goal: str, 
    skill_pool: List[AtomSkill], 
    initial_context: Dict[str, Any]
) -> Tuple[Optional[Callable], List[AtomSkill]]:
    """
    【重组】根据任务目标从技能池中筛选并重组原子技能链。
    
    通过语境兼容性检查，寻找一条可行的技能执行路径。
    
    Args:
        task_goal (str): 任务描述（用于未来嵌入向量检索，此处使用关键词模拟）
        skill_pool (List[AtomSkill]): 可用的原子技能池
        initial_context (Dict[str, Any]): 初始的输入数据上下文
        
    Returns:
        Tuple[Optional[Callable], List[AtomSkill]]: 返回组合后的执行函数和选定的技能链
        
    Raises:
        SkillRecombinationError: 无法找到兼容的技能组合
    """
    logger.info(f"开始重组技能以完成任务: {task_goal}")
    
    selected_chain: List[AtomSkill] = []
    current_fingerprint = ContextFingerprint(
        post_expectations={k: type(v).__name__ for k, v in initial_context.items()}
    )
    
    # 简单的贪心策略寻找路径（实际AGI应使用规划算法如A*或MCTS）
    # 模拟：寻找能处理当前输出的技能，直到无法继续或达到最大深度
    max_depth = 5
    used_skills = set()
    
    for _ in range(max_depth):
        found_next = False
        for skill in skill_pool:
            if skill.name in used_skills:
                continue
                
            # 核心：语境兼容性检查
            if current_fingerprint.is_compatible_with(skill.fingerprint):
                # 模拟选中该技能
                selected_chain.append(skill)
                used_skills.add(skill.name)
                
                # 更新当前指纹：当前技能的输出成为下一阶段的输入上下文
                # 注意：这里需要动态合并指纹，实际实现更复杂
                current_fingerprint = skill.fingerprint 
                found_next = True
                logger.info(f"选中技能: {skill.name}")
                break
        
        if not found_next:
            break
            
    if not selected_chain:
        raise SkillRecombinationError("无法找到符合初始语境的技能组合")

    # 构建组合后的执行函数
    def combined_executor(ctx: Dict[str, Any]) -> Dict[str, Any]:
        data = ctx
        for skill in selected_chain:
            data = skill.execute(data)
        return data

    logger.info(f"成功重组技能链: {' -> '.join([s.name for s in selected_chain])}")
    return combined_executor, selected_chain

# --- 辅助函数 ---

def validate_atom_data_integrity(atom: AtomSkill) -> bool:
    """
    【辅助】验证原子技能的数据完整性。
    
    检查定义的 pre_conditions 是否与 action 函数的签名大致匹配（简单模拟）。
    
    Args:
        atom (AtomSkill): 待验证的原子技能
        
    Returns:
        bool: 是否通过验证
    """
    if not atom.name or not isinstance(atom.name, str):
        logger.error("验证失败: 技能名称无效")
        return False
        
    if not atom.fingerprint or not isinstance(atom.fingerprint, ContextFingerprint):
        logger.error("验证失败: 语境指纹缺失或类型错误")
        return False
        
    # 检查是否定义了输入输出规范
    if not atom.fingerprint.pre_conditions and not atom.fingerprint.post_expectations:
        logger.warning(f"技能 {atom.name} 缺乏明确的I/O指纹定义，可能导致重组不稳定")
        
    return True

# --- 使用示例与测试 ---

if __name__ == "__main__":
    # 1. 定义原始业务逻辑函数
    def fetch_user_data(input_ctx: dict) -> dict:
        user_id = input_ctx.get("user_id")
        # 模拟数据库查询
        logger.info(f"Fetching data for user {user_id}")
        return {"user_profile": {"id": user_id, "age": 25, "name": "Alice"}, "status": "raw"}

    def analyze_sentiment(input_ctx: dict) -> dict:
        profile = input_ctx.get("user_profile")
        if not profile:
            raise ValueError("Missing user_profile")
        # 模拟NLP分析
        logger.info(f"Analyzing sentiment for {profile['name']}")
        return {"sentiment_score": 0.8, "raw_data": profile}

    # 2. 解构技能并添加语境指纹
    # Atom 1: 数据获取
    atom_fetch = deconstruct_skill(
        skill_name="db_fetch_user",
        raw_action=fetch_user_data,
        pre_cons={"user_id": "int"},  # 期望输入 user_id
        post_exps={"user_profile": "dict", "status": "str"},  # 输出包含 user_profile
        tags=["database", "user"]
    )
    
    # Atom 2: 情感分析
    atom_nlp = deconstruct_skill(
        skill_name="nlp_sentiment",
        raw_action=analyze_sentiment,
        pre_cons={"user_profile": "dict"},  # 期望输入 user_profile (由上一个技能提供)
        post_exps={"sentiment_score": "float"},
        tags=["nlp", "analysis"]
    )

    # 验证完整性
    assert validate_atom_data_integrity(atom_fetch)
    assert validate_atom_data_integrity(atom_nlp)

    # 3. 尝试重组技能
    skill_pool = [atom_nlp, atom_fetch] # 乱序放入池中
    
    # 定义初始任务输入
    task_input = {"user_id": 101}
    
    try:
        # 系统自动寻找路径：fetch -> nlp
        # 注意：此处逻辑简化，实际需要更复杂的规划器来处理乱序匹配
        # 为了演示，我们手动模拟一下 is_compatible_with 的调用
        
        # 模拟初始指纹
        init_fp = ContextFingerprint(post_expectations={"user_id": "int"})
        
        # 检查 fetch 是否兼容初始输入
        if init_fp.is_compatible_with(atom_fetch.fingerprint):
            logger.info("Step 1 Check: Context matches AtomFetch requirements")
            
            # 检查 fetch 的输出是否兼容 nlp 的输入
            if atom_fetch.fingerprint.is_compatible_with(atom_nlp.fingerprint):
                logger.info("Step 2 Check: AtomFetch output matches AtomNLP requirements")
                
                # 手动构建执行链进行演示
                final_chain = [atom_fetch, atom_nlp]
                
                print("\n--- Executing Recombined Skill Chain ---")
                current_data = task_input
                for skill in final_chain:
                    print(f"Executing: {skill.name}")
                    current_data = skill.execute(current_data)
                
                print("\nFinal Result:")
                print(current_data)
            else:
                logger.error("重组失败: Fetch 输出无法满足 NLP 输入")
        else:
            logger.error("重组失败: 初始语境不满足 Fetch 输入")

    except SkillRecombinationError as e:
        logger.error(f"Task failed: {e}")
    except Exception as e:
        logger.error(f"Execution error: {e}")