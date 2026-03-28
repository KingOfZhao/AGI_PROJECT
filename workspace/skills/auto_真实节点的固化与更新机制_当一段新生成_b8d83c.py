"""
名称: auto_真实节点的固化与更新机制_当一段新生成_b8d83c
描述: 真实节点的固化与更新机制: 当一段新生成的代码经过运行验证成功后，系统如何判断其具备'通用性'，
       从而将其抽象为新的SKILL或NODE并入知识库，避免知识库被一次性脚本污染？
领域: knowledge_engineering
"""

import hashlib
import logging
import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkillConsolidator")

@dataclass
class ExecutionTrace:
    """记录代码块的运行轨迹与元数据"""
    code_snippet: str
    success: bool
    execution_time: float  # seconds
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context_tags: List[str] = field(default_factory=list)

@dataclass
class SkillCandidate:
    """潜在的通用技能节点"""
    function_name: str
    code_body: str
    description: str
    signature: str
    usage_count: int = 1
    stability_score: float = 0.0
    input_schema: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class KnowledgeBase:
    """
    模拟知识库接口
    """
    def __init__(self):
        self._skills: Dict[str, SkillCandidate] = {}
    
    def exists(self, identifier: str) -> bool:
        return identifier in self._skills
    
    def add_skill(self, skill: SkillCandidate) -> bool:
        if self.exists(skill.function_name):
            logger.warning(f"Skill {skill.function_name} already exists.")
            return False
        self._skills[skill.function_name] = skill
        logger.info(f"Successfully consolidated new skill: {skill.function_name}")
        return True
    
    def update_skill(self, skill: SkillCandidate) -> bool:
        if not self.exists(skill.function_name):
            return False
        self._skills[skill.function_name] = skill
        logger.info(f"Updated skill: {skill.function_name}")
        return True

    def get_skill(self, identifier: str) -> Optional[SkillCandidate]:
        return self._skills.get(identifier)

def _extract_metadata(code: str) -> Tuple[str, List[str]]:
    """
    [辅助函数] 从代码字符串中提取函数名和参数列表。
    
    Args:
        code (str): 源代码字符串。
        
    Returns:
        Tuple[str, List[str]]: (函数名, 参数列表)。
        
    Raises:
        ValueError: 如果无法解析出函数定义。
    """
    # 简单的正则匹配，寻找 def function_name(...):
    pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\):"
    match = re.search(pattern, code)
    
    if not match:
        logger.error("Metadata extraction failed: No function definition found.")
        raise ValueError("Code snippet must contain a valid function definition.")
    
    func_name = match.group(1)
    params_str = match.group(2)
    # 简单清理参数
    params = [p.strip().split(":")[0].split("=")[0].strip() for p in params_str.split(",") if p.strip()]
    
    return func_name, params

def calculate_generalization_score(trace: ExecutionTrace, candidate_code: str) -> float:
    """
    [核心函数] 计算代码片段的通用性得分。
    
    评估维度：
    1. 输入输出结构的规范性 (是否使用了标准JSON可序列化结构)
    2. 代码复杂度 (太简单可能不值得固化，太复杂可能由于上下文依赖过强而不稳定)
    3. 上下文无关性 (检查是否依赖过多的全局变量或特定路径)
    
    Args:
        trace (ExecutionTrace): 运行记录。
        candidate_code (str): 候选代码。
        
    Returns:
        float: 0.0 到 1.0 之间的通用性得分。
    """
    score = 0.0
    
    # 1. 检查输入输出是否可序列化
    try:
        json.dumps(trace.inputs)
        json.dumps(trace.outputs)
        score += 0.4
        logger.debug("IO Serialization check passed.")
    except TypeError:
        logger.warning("IO contains non-serializable objects, lower generalization score.")
        score += 0.1

    # 2. 检查代码是否包含"硬编码"路径或临时值
    # 检查是否包含 '/tmp', 'C:\\Users', 具体的IP等
    hardcode_patterns = [
        r"(/tmp/|/var/|C:\\Users)",
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", # IP地址
        r"password\s*=\s*['\"]" # 硬编码密码
    ]
    
    is_clean = True
    for pattern in hardcode_patterns:
        if re.search(pattern, candidate_code):
            is_clean = False
            break
            
    if is_clean:
        score += 0.3
    else:
        score -= 0.5 # 惩罚项
        
    # 3. 检查是否有文档字符串
    if '"""' in candidate_code or "'''" in candidate_code:
        score += 0.1
        
    # 4. 基础分：运行成功
    if trace.success:
        score += 0.2
        
    # 边界限制
    final_score = max(0.0, min(1.0, score))
    logger.info(f"Calculated generalization score: {final_score}")
    return final_score

def consolidate_skill(trace: ExecutionTrace, kb: KnowledgeBase, threshold: float = 0.75) -> Optional[str]:
    """
    [核心函数] 判断是否将运行过的代码固化入库。
    
    逻辑流程：
    1. 验证运行记录的有效性。
    2. 提取代码元数据（函数名、签名）。
    3. 计算通用性得分。
    4. 如果得分超过阈值，生成SkillCandidate并入库。
    5. 如果知识库中已存在相似功能节点，更新其稳定性得分而非创建新节点。
    
    Args:
        trace (ExecutionTrace): 包含代码和运行结果的追踪对象。
        kb (KnowledgeBase): 知识库实例。
        threshold (float): 固化为SKILL的通用性得分阈值。
        
    Returns:
        Optional[str]: 成功固化的Skill ID，失败返回None。
    """
    logger.info(f"Processing trace for consolidation: {trace.timestamp}")
    
    # 1. 基础验证
    if not trace.success:
        logger.warning("Trace indicates failure. Skipping consolidation.")
        return None
        
    if not trace.code_snippet or len(trace.code_snippet) < 20:
        logger.warning("Code snippet too short or empty.")
        return None
        
    # 2. 元数据提取
    try:
        func_name, params = _extract_metadata(trace.code_snippet)
    except ValueError as e:
        logger.error(f"Invalid code structure: {e}")
        return None

    # 3. 计算通用性
    score = calculate_generalization_score(trace, trace.code_snippet)
    
    if score < threshold:
        logger.info(f"Score {score} below threshold {threshold}. Treated as disposable script.")
        return None
        
    # 4. 准备入库数据
    # 简单的Schema推断：只记录key和type
    input_schema = {k: type(v).__name__ for k, v in trace.inputs.items()}
    output_schema = {k: type(v).__name__ for k, v in trace.outputs.items()}
    
    new_skill = SkillCandidate(
        function_name=func_name,
        code_body=trace.code_snippet,
        description=f"Auto-generated skill from trace {trace.timestamp}",
        signature=", ".join(params),
        stability_score=score,
        input_schema=input_schema,
        output_schema=output_schema,
        usage_count=1
    )
    
    # 5. 冲突处理与更新
    # 这里使用简单的名称冲突检测，实际AGI系统可能需要语义向量相似度检测
    existing_skill = kb.get_skill(func_name)
    
    if existing_skill:
        logger.info(f"Skill '{func_name}' exists. Performing update and boosting stability.")
        existing_skill.usage_count += 1
        # 更新稳定性得分为加权平均
        existing_skill.stability_score = (existing_skill.stability_score + score) / 2
        existing_skill.last_updated = datetime.utcnow().isoformat()
        
        # 如果新代码更优（例如覆盖了更多边界情况），可以选择替换代码体
        # 此处策略为：保留高分代码
        if score > existing_skill.stability_score + 0.1:
            logger.info("New implementation shows higher stability, updating code body.")
            existing_skill.code_body = new_skill.code_body
            existing_skill.input_schema = new_skill.input_schema
            
        kb.update_skill(existing_skill)
        return existing_skill.function_name
    else:
        if kb.add_skill(new_skill):
            return new_skill.function_name
        return None

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化知识库
    kb_simulator = KnowledgeBase()
    
    # 场景 1: 一个高质量的通用代码片段 (计算直角三角形斜边)
    valid_code = '''
def calculate_hypotenuse(a: float, b: float) -> float:
    """计算直角三角形的斜边长度"""
    import math
    return math.sqrt(a**2 + b**2)
'''
    
    trace_1 = ExecutionTrace(
        code_snippet=valid_code,
        success=True,
        execution_time=0.0001,
        inputs={"a": 3, "b": 4},
        outputs={"result": 5.0},
        context_tags=["math", "geometry"]
    )
    
    print("--- Attempting to consolidate high-quality trace ---")
    skill_id_1 = consolidate_skill(trace_1, kb_simulator, threshold=0.7)
    if skill_id_1:
        print(f"Consolidated Skill ID: {skill_id_1}")
        
    # 场景 2: 一个包含硬编码路径的一次性脚本
    bad_code = '''
def process_temp_file():
    with open("/tmp/data_123.txt", "r") as f:
        return f.read()
'''
    trace_2 = ExecutionTrace(
        code_snippet=bad_code,
        success=True,
        execution_time=0.002,
        inputs={},
        outputs={"content": "some data"},
        context_tags=["io", "temp"]
    )
    
    print("\n--- Attempting to consolidate low-quality/hardcoded trace ---")
    skill_id_2 = consolidate_skill(trace_2, kb_simulator, threshold=0.7)
    print(f"Result for bad code: {'Rejected' if not skill_id_2 else 'Accepted'}")

    # 场景 3: 重复调用更新现有Skill
    trace_3 = ExecutionTrace(
        code_snippet=valid_code, # 相同代码
        success=True,
        execution_time=0.00009,
        inputs={"a": 5, "b": 12},
        outputs={"result": 13.0},
        context_tags=["math", "geometry"]
    )
    
    print("\n--- Attempting to update existing skill ---")
    consolidate_skill(trace_3, kb_simulator, threshold=0.7)
    stored_skill = kb_simulator.get_skill("calculate_hypotenuse")
    if stored_skill:
        print(f"Current Usage Count: {stored_skill.usage_count}")
        print(f"Current Stability: {stored_skill.stability_score:.2f}")