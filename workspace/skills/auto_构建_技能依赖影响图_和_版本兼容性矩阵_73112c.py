"""
高级技能模块：技能依赖影响图与版本兼容性矩阵构建器

该模块为AGI系统提供核心基础设施支持。它负责维护系统内不同技能（Skills）之间的
复杂依赖关系，构建依赖影响图以评估变更传播范围，并维护版本兼容性矩阵。
在检测到技能更新时，模块将在隔离的沙箱环境中执行传播测试，以确保系统稳定性。

作者: AGI System Core Team
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import subprocess
import sys
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, TypedDict

# 配置模块级日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class CompatibilityLevel(Enum):
    """定义技能版本的兼容性等级枚举"""
    FULL = "full"               # 完全兼容
    PARTIAL = "partial"         # 部分兼容，可能有轻微警告
    BREAKING = "breaking"       # 破坏性变更，不兼容
    UNKNOWN = "unknown"         # 未经测试或数据缺失

class SkillMetadata(TypedDict):
    """技能元数据的类型定义"""
    skill_id: str
    version: str
    dependencies: List[str]     # 依赖的技能ID列表

class CompatibilityMatrix(TypedDict):
    """版本兼容性矩阵的类型定义"""
    source_skill: str
    target_skill: str
    source_version: str
    target_version: str
    level: CompatibilityLevel

class DependencyGraph:
    """
    技能依赖影响图管理类。
    
    使用邻接表构建有向图，支持依赖解析和受影响节点分析。
    """

    def __init__(self) -> None:
        """初始化依赖图"""
        self._graph: Dict[str, Set[str]] = {}  # 正向依赖: A -> {B, C} (A depends on B, C)
        self._reverse_graph: Dict[str, Set[str]] = {} # 反向依赖/影响图: A -> {B} (B depends on A)
        logger.info("DependencyGraph initialized.")

    def add_skill(self, skill: SkillMetadata) -> None:
        """
        向图中添加一个技能节点及其依赖关系。
        
        Args:
            skill (SkillMetadata): 包含ID、版本和依赖列表的技能字典。
        """
        skill_id = skill['skill_id']
        deps = skill['dependencies']

        if skill_id not in self._graph:
            self._graph[skill_id] = set()
            self._reverse_graph[skill_id] = set()
        
        # 建立正向和反向连接
        for dep_id in deps:
            if not dep_id:
                continue
            self._graph[skill_id].add(dep_id)
            
            if dep_id not in self._reverse_graph:
                self._reverse_graph[dep_id] = set()
            self._reverse_graph[dep_id].add(skill_id)
            
        logger.debug(f"Skill added/updated: {skill_id} with dependencies: {deps}")

    def get_impact_set(self, updated_skill_id: str) -> Set[str]:
        """
        [核心函数 1]
        根据更新的技能，递归查找所有受影响的下游技能（反向依赖）。
        
        Args:
            updated_skill_id (str): 发生变更的技能ID。
            
        Returns:
            Set[str]: 受影响的技能ID集合。
        """
        if updated_skill_id not in self._reverse_graph:
            logger.warning(f"Skill {updated_skill_id} not found in reverse graph.")
            return set()

        impacted_skills: Set[str] = set()
        queue: List[str] = [updated_skill_id]
        
        while queue:
            current_node = queue.pop(0)
            # 获取依赖于当前节点的所有技能
            dependents = self._reverse_graph.get(current_node, set())
            
            for dep_skill in dependents:
                if dep_skill not in impacted_skills:
                    impacted_skills.add(dep_skill)
                    queue.append(dep_skill)
                    
        logger.info(f"Impact analysis for {updated_skill_id}: {len(impacted_skills)} skills affected.")
        return impacted_skills

class VersionCompatibilityEngine:
    """
    版本兼容性矩阵引擎。
    
    负责存储、查询和验证技能间的版本兼容性。
    """

    def __init__(self) -> None:
        """初始化引擎和存储结构"""
        # Key: (source_id, target_id), Value: CompatibilityMatrix
        self._matrix_store: Dict[Tuple[str, str], List[CompatibilityMatrix]] = {}
        logger.info("VersionCompatibilityEngine initialized.")

    def update_compatibility_record(self, record: CompatibilityMatrix) -> None:
        """
        更新或插入一条兼容性记录。
        
        Args:
            record (CompatibilityMatrix): 包含源技能、目标技能和版本的兼容性数据。
        """
        key = (record['source_skill'], record['target_skill'])
        if key not in self._matrix_store:
            self._matrix_store[key] = []
        
        # 简单的去重逻辑：移除同版本的旧记录
        self._matrix_store[key] = [
            r for r in self._matrix_store[key] 
            if not (r['source_version'] == record['source_version'] and r['target_version'] == record['target_version'])
        ]
        self._matrix_store[key].append(record)
        logger.debug(f"Compatibility record updated for {key}")

    def check_compatibility(self, skill_a: str, ver_a: str, skill_b: str, ver_b: str) -> CompatibilityLevel:
        """
        [核心函数 2]
        检查两个特定版本的技能是否兼容。
        
        Args:
            skill_a (str): 技能A的ID
            ver_a (str): 技能A的版本
            skill_b (str): 技能B的ID
            ver_b (str): 技能B的版本
            
        Returns:
            CompatibilityLevel: 兼容性等级枚举值。
        """
        # 双向检查
        key_1 = (skill_a, skill_b)
        key_2 = (skill_b, skill_a)
        
        records = self._matrix_store.get(key_1, []) + self._matrix_store.get(key_2, [])
        
        for r in records:
            # 检查版本是否匹配（顺序无关）
            match_1 = (r['source_version'] == ver_a and r['target_version'] == ver_b)
            match_2 = (r['source_version'] == ver_b and r['target_version'] == ver_a)
            
            if match_1 or match_2:
                logger.info(f"Compatibility check hit cache: {skill_a}:{ver_a} <-> {skill_b}:{ver_b} = {r['level']}")
                return r['level']
                
        logger.warning(f"Compatibility data missing for {skill_a}:{ver_a} <-> {skill_b}:{ver_b}")
        return CompatibilityLevel.UNKNOWN

def run_sandbox_propagation_test(skill_id: str, impact_set: Set[str]) -> bool:
    """
    [辅助函数]
    在沙箱环境中运行传播测试。
    
    模拟更新 'skill_id' 并检查 'impact_set' 中的技能是否仍然正常工作。
    
    Args:
        skill_id (str): 待更新的技能ID。
        impact_set (Set[str]): 受影响的技能ID集合。
        
    Returns:
        bool: 如果所有受影响的技能在沙箱中测试通过则返回True，否则返回False。
    """
    logger.info(f"Starting SANDBOX propagation test for update on: {skill_id}")
    
    if not impact_set:
        logger.info("No dependent skills to test. Propagation test passed trivially.")
        return True

    try:
        # 模拟测试过程 - 在实际生产中这里会调用Docker容器或子进程
        # 这里我们使用简单的逻辑模拟测试结果
        simulated_test_command = ["echo", f"Running tests for dependents: {', '.join(impact_set)}"]
        
        # 使用 subprocess 进行安全的沙箱命令执行模拟
        # 注意：此处为了演示安全性，使用了 subprocess 但未实际执行危险操作
        result = subprocess.run(
            simulated_test_command, 
            capture_output=True, 
            text=True, 
            timeout=10  # 设置超时防止挂起
        )
        
        if result.returncode == 0:
            logger.info(f"Sandbox test successful for impact set of {skill_id}.")
            return True
        else:
            logger.error(f"Sandbox test failed. stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Sandbox test timed out.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during sandbox testing: {str(e)}")
        return False

def validate_skill_input(skill: SkillMetadata) -> bool:
    """
    数据验证辅助函数。
    """
    if not isinstance(skill, dict):
        raise ValueError("Input must be a dictionary.")
    if 'skill_id' not in skill or 'version' not in skill:
        raise ValueError("Missing required fields: 'skill_id' or 'version'.")
    return True

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 初始化系统组件
        dep_graph = DependencyGraph()
        compat_engine = VersionCompatibilityEngine()
        
        # 2. 定义测试数据
        # 假设我们有一个技能链: Core -> DataUtils -> ML_Model
        skill_core: SkillMetadata = {
            "skill_id": "core_py_lib", 
            "version": "2.0.0", 
            "dependencies": []
        }
        skill_utils: SkillMetadata = {
            "skill_id": "data_utils", 
            "version": "1.5.0", 
            "dependencies": ["core_py_lib"]
        }
        skill_ml: SkillMetadata = {
            "skill_id": "ml_model_inference", 
            "version": "3.1.0", 
            "dependencies": ["data_utils"]
        }
        
        # 3. 构建依赖图
        logger.info("--- Building Dependency Graph ---")
        dep_graph.add_skill(skill_core)
        dep_graph.add_skill(skill_utils)
        dep_graph.add_skill(skill_ml)
        
        # 4. 设置版本兼容性矩阵
        logger.info("--- Configuring Compatibility Matrix ---")
        # 假设 Core 2.0.0 和 DataUtils 1.5.0 是兼容的
        compat_record: CompatibilityMatrix = {
            "source_skill": "core_py_lib",
            "target_skill": "data_utils",
            "source_version": "2.0.0",
            "target_version": "1.5.0",
            "level": CompatibilityLevel.FULL
        }
        compat_engine.update_compatibility_record(compat_record)
        
        # 5. 模拟节点更新场景
        # 场景：我们要更新 "core_py_lib"
        update_target = "core_py_lib"
        
        # 6. 计算影响范围
        logger.info(f"--- Analyzing Impact for update: {update_target} ---")
        impacted_skills = dep_graph.get_impact_set(update_target)
        print(f"Impacted Skills: {impacted_skills}")
        
        # 7. 执行沙箱测试
        # 在实际应用中，这里会检查 impacted_skills 中的具体版本兼容性
        is_safe = run_sandbox_propagation_test(update_target, impacted_skills)
        
        if is_safe:
            logger.info("SYSTEM SAFE: Update can be propagated.")
        else:
            logger.warning("SYSTEM ALERT: Update blocked due to propagation failure.")
            
    except Exception as e:
        logger.critical(f"System crash during execution: {e}", exc_info=True)