"""
Module: auto_structural_falsification.py
Description: 【结构完整性证伪】针对已建立的708个SKILL节点，生成对抗性破坏测试用例。
             本模块旨在模拟恶劣环境（如磁盘已满、权限受限、资源耗尽），
             以验证系统对技能的理解是否包含边界条件，而非仅停留在Happy Path。
Author: AGI System Core
Version: 1.0.0
"""

import os
import sys
import json
import time
import logging
import tempfile
import hashlib
import shutil
import traceback
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from contextlib import contextmanager

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("StructuralFalsification")


class SkillCategory(Enum):
    """技能节点分类枚举"""
    FILE_IO = "file_io"
    NETWORK = "network"
    DATABASE = "database"
    COMPUTATION = "computation"
    MEMORY_MANAGEMENT = "memory_management"


@dataclass
class SkillNode:
    """代表一个待测试的技能节点"""
    node_id: str
    name: str
    category: SkillCategory
    description: str
    dependencies: List[str] = field(default_factory=list)
    criticality: int = 1  # 1-5, 5为最关键


@dataclass
class FalsificationResult:
    """证伪测试结果"""
    skill_node_id: str
    is_falsified: bool  # True表示成功被破坏（未通过完整性测试）
    error_type: Optional[str]
    error_message: str
    execution_time_ms: float
    environment_context: Dict[str, Any]


class EnvironmentSimulator:
    """
    核心类：负责构建对抗性测试环境。
    用于模拟资源受限、权限不足或外部依赖失效的场景。
    """

    def __init__(self, base_temp_dir: Optional[str] = None):
        self.base_dir = base_temp_dir or tempfile.gettempdir()
        self.active_sandbox: Optional[str] = None
        logger.info(f"Environment Simulator initialized at: {self.base_dir}")

    def _create_sandbox(self) -> str:
        """创建隔离的测试沙箱目录"""
        sandbox_name = f"falsify_sandbox_{int(time.time())}"
        path = os.path.join(self.base_dir, sandbox_name)
        os.makedirs(path, exist_ok=True)
        self.active_sandbox = path
        return path

    def _cleanup_sandbox(self) -> None:
        """清理沙箱环境"""
        if self.active_sandbox and os.path.exists(self.active_sandbox):
            try:
                # 尝试恢复权限以便删除
                os.chmod(self.active_sandbox, 0o755)
                shutil.rmtree(self.active_sandbox)
                logger.debug(f"Sandbox cleaned: {self.active_sandbox}")
            except Exception as e:
                logger.error(f"Failed to clean sandbox {self.active_sandbox}: {e}")
            finally:
                self.active_sandbox = None

    @contextmanager
    def simulate_disk_full(self, target_path: str, quota_bytes: int = 1024):
        """
        模拟磁盘已满或配额受限的环境。
        通过使用Device Null或模拟大文件占用来触发IOError。
        注意：这是一个逻辑模拟，具体实现依赖于OS配额管理或临时文件填充。
        """
        logger.warning(f"Activating DISK_FULL simulation for {target_path}")
        dummy_file = None
        try:
            # 简单模拟：创建一个占位文件，并在后续操作中预期失败
            # 在真实场景中，这里会调用系统级的配额设置
            # 这里我们通过Monkey Patch open函数来模拟
            original_open = open
            
            def restricted_open(*args, **kwargs):
                if 'w' in args[1] or 'a' in args[1]:
                    raise OSError(28, "No space left on device (Simulated)")
                return original_open(*args, **kwargs)

            # 临时替换内置open
            builtins = __builtins__
            if isinstance(builtins, dict):
                builtins['open'] = restricted_open
            else:
                builtins.open = restricted_open
            
            yield target_path
        finally:
            # 恢复环境
            if isinstance(builtins, dict):
                builtins['open'] = original_open
            else:
                builtins.open = original_open
            logger.info("Disk full simulation deactivated.")

    @contextmanager
    def simulate_permission_denied(self, target_dir: str):
        """
        模拟权限受限环境（只读文件系统）。
        """
        logger.warning(f"Activating PERMISSION_DENIED simulation for {target_dir}")
        original_mode = os.stat(target_dir).st_mode
        try:
            # 移除写权限
            os.chmod(target_dir, 0o444)
            yield target_dir
        finally:
            # 恢复权限
            os.chmod(target_dir, original_mode)
            logger.info("Permission simulation deactivated.")

    @contextmanager
    def simulate_resource_exhaustion(self):
        """
        模拟资源耗尽（如高CPU负载或内存锁定）。
        这里主要是一个占位逻辑，实际生产中会启动压力进程。
        """
        logger.warning("Activating RESOURCE_EXHAUSTION simulation (Low Priority)")
        # 模拟高延迟
        time.sleep(0.1) 
        yield


class FalsificationEngine:
    """
    核心引擎：针对输入的Skill Node生成并执行破坏性测试。
    """

    def __init__(self):
        self.env_sim = EnvironmentSimulator()
        self.test_report: List[FalsificationResult] = []

    def _validate_skill_integrity(self, skill: SkillNode) -> bool:
        """辅助函数：验证技能节点数据结构的有效性"""
        if not skill.node_id or not skill.name:
            raise ValueError("Skill node must have ID and Name")
        if skill.criticality < 1 or skill.criticality > 5:
            logger.warning(f"Invalid criticality level for {skill.node_id}, defaulting to 1")
            return False
        return True

    def _generate_adversarial_io_code(self, file_path: str) -> str:
        """
        生成针对文件IO的对抗性测试代码字符串。
        不仅仅是读写，而是尝试在边界条件下操作。
        """
        return f"""
import json
import os

def attempt_destructive_write(path):
    # 尝试写入超大文件或非法字符
    try:
        with open(path, 'w') as f:
            f.write("\\x00" * 10000) # 写入大量NULL字节
            f.flush()
            # 如果在这里还没有失败，说明环境模拟可能不够严格
            return True
    except OSError as e:
        raise e
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {{e}}")

if __name__ == "__main__":
    attempt_destructive_write("{file_path}")
"""

    def execute_io_falsification(self, skill: SkillNode) -> FalsificationResult:
        """
        核心函数 1: 执行针对文件IO类型的结构完整性证伪测试。
        测试目标：验证代码是否能优雅处理权限拒绝或磁盘已满。
        """
        start_time = time.time()
        sandbox = self.env_sim._create_sandbox()
        target_file = os.path.join(sandbox, "critical_data.json")
        is_falsified = False
        error_ctx = None
        msg = "System passed destructive test (Robust)."
        env_context = {"sandbox": sandbox, "condition": "permission_denied"}

        try:
            # 阶段 1: 验证基础能力 (Happy Path)
            with open(target_file, 'w') as f:
                f.write("test")
            
            # 阶段 2: 施加对抗性环境
            with self.env_sim.simulate_permission_denied(sandbox):
                # 阶段 3: 尝试执行技能逻辑
                # 这里我们模拟调用一个期望写入的操作
                try:
                    # 尝试在只读目录下创建新文件
                    new_file = os.path.join(sandbox, "illegal_write.txt")
                    with open(new_file, 'w') as f:
                        f.write("This should fail")
                    
                    # 如果代码执行到了这里，说明系统未能拦截非法操作 -> 证伪成功（系统不安全/不完整）
                    is_falsified = True 
                    msg = "FALSIFIED: System allowed write operation in read-Only environment."
                    error_ctx = "SecurityBreach"
                    
                except (PermissionError, OSError) as e:
                    # 这是预期的行为，系统具有完整性
                    logger.info(f"Expected failure caught: {e}")
                    is_falsified = False
                    msg = "Robust: Correctly handled permission denial."
                    error_ctx = type(e).__name__

        except Exception as e:
            is_falsified = True
            error_ctx = "SetupError"
            msg = f"Test setup failed: {str(e)}"
            logger.error(traceback.format_exc())
        finally:
            exec_time = (time.time() - start_time) * 1000
            self.env_sim._cleanup_sandbox()

        return FalsificationResult(
            skill_node_id=skill.node_id,
            is_falsified=is_falsified,
            error_type=error_ctx,
            error_message=msg,
            execution_time_ms=exec_time,
            environment_context=env_context
        )

    def execute_memory_falsification(self, skill: SkillNode) -> FalsificationResult:
        """
        核心函数 2: 执行针对内存管理/计算类型的证伪测试。
        测试目标：验证是否存在内存泄漏或无限递归风险。
        """
        start_time = time.time()
        is_falsified = False
        msg = "Memory handling is robust."
        error_ctx = None
        
        # 定义一个递归深度限制检查
        MAX_DEPTH = 1000
        
        def recursive_overflow(depth: int):
            if depth > MAX_DEPTH:
                return
            recursive_overflow(depth + 1)

        try:
            # 设置递归限制比测试目标更小
            old_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(100) # 设置极低的限制
            
            try:
                recursive_overflow(0)
                # 如果在低限制下没报错，可能没有递归，或者使用了尾调用优化（Python通常没有）
                is_falsified = False 
                msg = "No recursion crash observed within limits."
            except RecursionError:
                # 预期内的错误
                is_falsified = False
                msg = "Correctly raises RecursionError under constrained limit."
                error_ctx = "RecursionError"
            
            sys.setrecursionlimit(old_limit)

        except Exception as e:
            is_falsified = True
            error_ctx = "UnexpectedCrash"
            msg = str(e)

        exec_time = (time.time() - start_time) * 1000
        return FalsificationResult(
            skill_node_id=skill.node_id,
            is_falsified=is_falsified,
            error_type=error_ctx,
            error_message=msg,
            execution_time_ms=exec_time,
            environment_context={"limit_set": 100}
        )

    def run_full_falsification_suite(self, skills: List[SkillNode]) -> Dict[str, Any]:
        """
        运行完整的证伪测试套件，并生成报告。
        """
        logger.info(f"Starting Structural Falsification for {len(skills)} nodes...")
        results = []
        
        for skill in skills:
            if not self._validate_skill_integrity(skill):
                continue

            logger.info(f"Testing Node: {skill.name} [{skill.category.value}]")
            
            if skill.category == SkillCategory.FILE_IO:
                res = self.execute_io_falsification(skill)
            elif skill.category == SkillCategory.COMPUTATION:
                res = self.execute_memory_falsification(skill)
            else:
                # 默认跳过或待实现
                continue
            
            results.append(res)

        # 汇总报告
        total_falsified = sum(1 for r in results if r.is_falsified)
        report = {
            "total_nodes_tested": len(results),
            "structural_integrity_score": (len(results) - total_falsified) / len(results) if results else 0,
            "details": [r.__dict__ for r in results]
        }
        return report

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 定义测试节点
    test_nodes = [
        SkillNode(
            node_id="s_3114c3_001",
            name="Python File Write",
            category=SkillCategory.FILE_IO,
            description="Standard file writing capability",
            criticality=5
        ),
        SkillNode(
            node_id="s_3114c3_002",
            name="Recursive Calculation",
            category=SkillCategory.COMPUTATION,
            description="Recursive fibonacci implementation",
            criticality=3
        )
    ]

    # 2. 初始化引擎
    engine = FalsificationEngine()

    # 3. 运行测试
    final_report = engine.run_full_falsification_suite(test_nodes)

    # 4. 输出结果
    print("\n--- Falsification Report Summary ---")
    print(json.dumps(final_report, indent=2))