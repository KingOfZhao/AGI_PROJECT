"""
模块名称: auto_执行环境沙箱_如何构建一个_可观测的代_9fcbd3
描述: 本模块实现了一个可观测的代码执行沙箱。它旨在为AGI系统或自动化任务提供一个安全、隔离的代码执行环境。
      核心功能包括：限制资源的代码执行、实时捕获执行状态（stdout, stderr, 变量快照）、
      以及文件系统变更监控。这使得AI系统能够基于反馈更新其世界模型，而非将代码执行视为黑盒。

依赖:
    - psutil (用于资源监控和进程管理)
    - RestrictedPython (可选，用于基础语法限制，本实现侧重于子进程隔离)

设计哲学:
    - 隔离性: 代码在子进程中运行，避免主崩溃。
    - 可观测性: 通过队列和管道实时回传状态。
    - 安全性: 限制CPU时间和内存使用。
"""

import subprocess
import threading
import json
import time
import logging
import os
import tempfile
import shutil
import signal
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import traceback

# 尝试导入 psutil，如果不存在则降级处理
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil library not found. Memory and CPU monitoring will be disabled.")

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ObservableSandbox")


@dataclass
class ExecutionResult:
    """
    执行结果的数据结构，用于映射回认知框架。
    """
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    start_time: str
    end_time: str
    duration_seconds: float
    memory_peak_mb: float
    variables_snapshot: Dict[str, Any]
    file_changes: List[Dict[str, str]]
    error_message: Optional[str] = None

    def to_json(self) -> str:
        """将结果序列化为JSON，便于传输给认知核心。"""
        return json.dumps(asdict(self), indent=2, default=str)


class ResourceMonitor:
    """
    辅助类：在子进程中运行，用于监控资源使用情况和捕获变量。
    通过将此类的逻辑注入到执行代码中实现部分可观测性。
    """
    def __init__(self, pid: int):
        self.pid = pid
        self.memory_peak = 0.0
        self.is_monitoring = True

    def monitor_loop(self, interval: float = 0.1):
        """持续监控进程资源占用的循环"""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            process = psutil.Process(self.pid)
            while self.is_monitoring:
                try:
                    mem_info = process.memory_info()
                    current_mem = mem_info.rss / (1024 * 1024)  # Convert to MB
                    if current_mem > self.memory_peak:
                        self.memory_peak = current_mem
                    time.sleep(interval)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")


def setup_temporary_workspace(base_dir: Optional[str] = None) -> str:
    """
    辅助函数：创建一个临时的文件系统工作空间。
    
    Args:
        base_dir (Optional[str]): 基础目录，如果为None则使用系统默认临时目录。
    
    Returns:
        str: 创建的临时工作目录路径。
    """
    prefix = "sandbox_workspace_"
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix, dir=base_dir)
        logger.info(f"Created temporary workspace: {temp_dir}")
        return temp_dir
    except OSError as e:
        logger.error(f"Failed to create workspace: {e}")
        raise


def scan_filesystem(path: str) -> Dict[str, float]:
    """扫描目录获取文件及其修改时间的快照。"""
    snapshot = {}
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                snapshot[full_path] = os.path.getmtime(full_path)
            except OSError:
                continue
    return snapshot


def detect_file_changes(before: Dict[str, float], after: Dict[str, float], workdir: str) -> List[Dict[str, str]]:
    """
    对比前后快照，检测文件变更。
    
    Returns:
        List of changes with 'type', 'path', and 'status'.
    """
    changes = []
    all_paths = set(before.keys()) | set(after.keys())
    
    for p in all_paths:
        rel_path = os.path.relpath(p, workdir)
        if p not in before:
            changes.append({"type": "CREATE", "path": rel_path, "full_path": p})
        elif p not in after:
            changes.append({"type": "DELETE", "path": rel_path, "full_path": p})
        elif before[p] != after[p]:
            changes.append({"type": "MODIFY", "path": rel_path, "full_path": p})
            
    return changes


class ObservableSandbox:
    """
    核心类：可观测的代码沙箱。
    
    负责构建执行环境、注入监控探针、运行代码并聚合结果。
    """

    def __init__(self, 
                 timeout_seconds: int = 30, 
                 max_memory_mb: int = 512, 
                 workdir: Optional[str] = None):
        """
        初始化沙箱配置。
        
        Args:
            timeout_seconds: 最大执行时间（秒）。
            max_memory_mb: 最大允许内存（MB），需要psutil支持严格限制。
            workdir: 指定工作目录，如果为None则自动创建临时目录。
        """
        self.timeout = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.owns_workdir = workdir is None
        self.workdir = workdir if workdir else setup_temporary_workspace()
        self.logger = logging.getLogger("SandboxInstance")

    def _construct_execution_script(self, user_code: str) -> str:
        """
        构造包装后的Python代码字符串。
        这段代码会捕获stdout/stderr，记录变量，并输出JSON格式的结果。
        """
        # 这是一个模板，将用户代码包裹在try-except中，并捕获上下文
        wrapper_code = f"""
import sys
import json
import traceback
from io import StringIO
import types

# 用于存储结果的字典
_run_result = {{
    "stdout": "",
    "stderr": "",
    "variables": {{}},
    "error": None
}}

# 重定向标准输出
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = StringIO()
sys.stderr = StringIO()

try:
    # --- 用户代码开始 ---
{self._indent_code(user_code, 4)}
    # --- 用户代码结束 ---

except Exception as e:
    _run_result["error"] = str(e)
    _run_result["stderr"] += traceback.format_exc()

finally:
    # 恢复标准输出
    _run_result["stdout"] = sys.stdout.getvalue()
    _run_result["stderr"] += sys.stderr.getvalue()
    sys.stdout = _old_stdout
    sys.stderr = _old_stderr

    # 捕获变量快照 (排除私有和模块属性)
    # 注意：这是一个简单的实现，实际AGI场景可能需要更复杂的过滤器
    _filtered_vars = {{}}
    _source_globals = globals()
    for k, v in _source_globals.items():
        if k.startswith('_') or k in ['sys', 'json', 'traceback', 'StringIO', 'types']:
            continue
        try:
            # 尝试序列化以验证是否可观察
            json.dumps({{"k": v}})
            _filtered_vars[k] = v
        except TypeError:
            _filtered_vars[k] = f"<Non-serializable: {{type(v).__name__}}>"

    _run_result["variables"] = _filtered_vars

    # 输出最终的JSON信号，以便父进程解析
    print("---SANDBOX_RESULT_START---")
    print(json.dumps(_run_result))
    print("---SANDBOX_RESULT_END---")
"""
        return wrapper_code

    def _indent_code(self, code: str, spaces: int) -> str:
        """辅助函数：缩进代码块"""
        prefix = " " * spaces
        return "\n".join(prefix + line for line in code.splitlines())

    def execute(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        核心函数：执行代码并返回可观测结果。
        
        Args:
            code (str): 要执行的Python代码字符串。
            input_data (Optional[Dict]): 可选的输入数据，可以作为环境变量或文件注入。
        
        Returns:
            ExecutionResult: 包含执行状态、资源消耗和输出结果的对象。
        """
        start_time = datetime.now()
        start_ts = time.time()
        
        # 1. 文件系统快照 (Before)
        fs_before = scan_filesystem(self.workdir)
        
        # 2. 准备执行脚本
        script_content = self._construct_execution_script(code)
        script_path = os.path.join(self.workdir, "exec_script.py")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # 3. 进程执行与资源监控
        # 使用 subprocess 隔离运行
        cmd = [sys.executable, script_path]
        
        # 设置环境变量
        env = os.environ.copy()
        if input_data:
            # 简单注入JSON字符串作为环境变量，防止命令行参数过长
            env["SANDBOX_INPUT_JSON"] = json.dumps(input_data)
        
        process = None
        stdout_data = ""
        stderr_data = ""
        exit_code = -1
        peak_memory = 0.0
        captured_vars = {}
        
        try:
            self.logger.info(f"Starting process with timeout {self.timeout}s...")
            
            # 启动监控线程（如果psutil可用）
            monitor_thread = None
            if PSUTIL_AVAILABLE:
                # 为了监控，我们需要先启动进程，获取PID
                process = subprocess.Popen(
                    cmd, cwd=self.workdir, env=env, 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True
                )
                
                # 启动资源监控
                def monitor_target():
                    nonlocal peak_memory
                    try:
                        p = psutil.Process(process.pid)
                        while process.poll() is None:
                            try:
                                mem = p.memory_info().rss / (1024 * 1024)
                                if mem > peak_memory:
                                    peak_memory = mem
                                # 检查内存限制
                                if mem > self.max_memory_mb:
                                    self.logger.warning(f"Memory limit exceeded: {mem:.2f}MB > {self.max_memory_mb}MB")
                                    process.kill()
                                time.sleep(0.05)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                break
                    except Exception as e:
                        pass

                monitor_thread = threading.Thread(target=monitor_target, daemon=True)
                monitor_thread.start()
                
                # 等待进程结束或超时
                try:
                    stdout_data, stderr_data = process.communicate(timeout=self.timeout)
                    exit_code = process.returncode
                except subprocess.TimeoutExpired:
                    self.logger.error("Process timed out.")
                    process.kill()
                    stdout_data, stderr_data = process.communicate()
                    exit_code = -1  # 自定义超时退出码
                    stderr_data += "\n[SANDBOX_ERROR] Execution timed out."

            else:
                # 无psutil降级模式
                process = subprocess.run(
                    cmd, cwd=self.workdir, env=env, 
                    capture_output=True, text=True, timeout=self.timeout
                )
                stdout_data = process.stdout
                stderr_data = process.stderr
                exit_code = process.returncode

        except Exception as e:
            self.logger.error(f"Sandbox execution failed: {traceback.format_exc()}")
            stderr_data += f"\n[SANDBOX_CRIT] {str(e)}"
            exit_code = -2

        # 4. 解析内部结果
        # 从stdout中提取JSON部分
        try:
            if "---SANDBOX_RESULT_START---" in stdout_data:
                json_str_start = stdout_data.find("---SANDBOX_RESULT_START---") + len("---SANDBOX_RESULT_START---")
                json_str_end = stdout_data.find("---SANDBOX_RESULT_END---")
                json_payload = stdout_data[json_str_start:json_str_end].strip()
                
                internal_result = json.loads(json_payload)
                
                # 优先使用内部捕获的stdout/stderr，因为它们更纯净（不包含JSON标记）
                # 但这里我们需要的是用户看到的输出，所以保留原始stdout
                # 这里我们选择更新变量快照
                captured_vars = internal_result.get("variables", {})
                if internal_result.get("error"):
                    # 如果内部有错误，补充到stderr
                    stderr_data = internal_result["stderr"] + "\n" + stderr_data
            else:
                # 如果没有找到标记，说明脚本可能在标记前就崩溃了
                pass
                
        except json.JSONDecodeError:
            self.logger.warning("Failed to decode internal sandbox JSON result.")

        # 5. 文件系统快照
        time.sleep(0.1) # 稍微等待确保文件系统刷新
        fs_after = scan_filesystem(self.workdir)
        file_changes = detect_file_changes(fs_before, fs_after, self.workdir)

        end_time = datetime.now()
        duration = time.time() - start_ts

        # 6. 构建最终结果
        result = ExecutionResult(
            success=(exit_code == 0 and "Error" not in stderr_data),
            exit_code=exit_code,
            stdout=stdout_data,
            stderr=stderr_data,
            start_time=str(start_time),
            end_time=str(end_time),
            duration_seconds=round(duration, 4),
            memory_peak_mb=round(peak_memory, 2),
            variables_snapshot=captured_vars,
            file_changes=file_changes
        )
        
        return result

    def cleanup(self):
        """清理工作空间"""
        if self.owns_workdir and os.path.exists(self.workdir):
            try:
                shutil.rmtree(self.workdir)
                logger.info(f"Cleaned up workspace: {self.workdir}")
            except Exception as e:
                logger.error(f"Failed to cleanup workspace: {e}")


if __name__ == "__main__":
    # 示例用法
    
    # 示例代码：包含计算、打印、文件写入和错误处理
    sample_code = """
import os
import time

# 1. 简单计算与变量
x = 100
y = 200
z = x + y
print(f"Calculation result: {z}")

# 2. 读取环境变量输入
input_json = os.getenv('SANDBOX_INPUT_JSON')
if input_json:
    import json
    data = json.loads(input_json)
    print(f"Received user: {data.get('user')}")

# 3. 文件操作
with open('output.txt', 'w') as f:
    f.write(f"Result is {z}")

# 4. 制造一个警告
# import nonexistent_module # 取消注释以测试错误处理

status = "completed"
large_list = [i for i in range(1000)] # 观察内存
"""

    # 初始化沙箱
    sandbox = ObservableSandbox(timeout_seconds=5, max_memory_mb=100)
    
    # 准备输入数据
    inputs = {
        "user": "AGI_System",
        "task_id": "9fcbd3"
    }

    print(f"--- Starting Execution in {sandbox.workdir} ---")
    
    try:
        # 执行
        result = sandbox.execute(sample_code, input_data=inputs)
        
        # 打印结果
        print("\n--- Execution Result JSON ---")
        print(result.to_json())
        
        print("\n--- Human Readable Summary ---")
        print(f"Success: {result.success}")
        print(f"Peak Memory: {result.memory_peak_mb} MB")
        print(f"Variables Captured: {list(result.variables_snapshot.keys())}")
        print(f"File Changes: {result.file_changes}")
        
    finally:
        # 清理
        sandbox.cleanup()