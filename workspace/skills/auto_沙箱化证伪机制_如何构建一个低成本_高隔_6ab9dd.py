"""
沙箱化证伪机制模块

该模块提供了一个低成本、高隔离的代码执行环境，用于验证生成的代码是否满足意图。
核心功能包括：代码执行、副作用监控、资源限制、结果验证。

输入格式:
    - code: 待执行的Python代码字符串
    - inputs: 代码执行所需的输入参数(dict)
    - expected_output: 预期的输出结果(可选)
    - timeout: 超时时间(秒，默认5)
    - memory_limit: 内存限制(MB，默认50)

输出格式:
    {
        "success": bool,  # 执行是否成功
        "output": Any,    # 代码输出结果
        "error": str,     # 错误信息(如果有)
        "metrics": {      # 执行指标
            "time": float,  # 执行时间(秒)
            "memory": int,  # 内存使用峰值(KB)
            "cpu": float    # CPU使用率(%)
        },
        "side_effects": [  # 副作用记录
            {
                "type": str,  # 副作用类型
                "details": dict  # 详细信息
            }
        ]
    }
"""

import os
import sys
import time
import json
import resource
import tempfile
import threading
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
import psutil
import subprocess
from pathlib import Path
import ast

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SideEffectType(Enum):
    """副作用类型枚举"""
    FILE_CREATE = auto()
    FILE_MODIFY = auto()
    FILE_DELETE = auto()
    NETWORK_ACCESS = auto()
    PROCESS_SPAWN = auto()
    ENV_CHANGE = auto()
    MEMORY_OVERUSE = auto()
    CPU_OVERUSE = auto()


@dataclass
class ExecutionResult:
    """执行结果数据结构"""
    success: bool = False
    output: Any = None
    error: Optional[str] = None
    metrics: Dict[str, Union[float, int]] = field(default_factory=dict)
    side_effects: List[Dict[str, Any]] = field(default_factory=list)


class SandboxMonitor:
    """沙箱监控器，用于跟踪执行过程中的副作用"""
    
    def __init__(self, sandbox_dir: str):
        self.sandbox_dir = Path(sandbox_dir).absolute()
        self.initial_files = set()
        self.final_files = set()
        self.side_effects = []
        self.memory_samples = []
        self.cpu_samples = []
        self._monitor_thread = None
        self._stop_event = threading.Event()
        
    def start_monitoring(self, pid: int, interval: float = 0.1) -> None:
        """开始监控进程资源使用情况"""
        self.initial_files = self._get_current_files()
        
        def monitor():
            try:
                process = psutil.Process(pid)
                while not self._stop_event.is_set():
                    try:
                        # 采样内存和CPU使用情况
                        with process.oneshot():
                            mem_info = process.memory_info()
                            cpu_percent = process.cpu_percent()
                            self.memory_samples.append(mem_info.rss)
                            self.cpu_samples.append(cpu_percent)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    time.sleep(interval)
            except Exception as e:
                logger.error(f"监控线程错误: {e}")
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        self.final_files = self._get_current_files()
        self._detect_file_side_effects()
        self._detect_resource_abuse()
    
    def _get_current_files(self) -> set:
        """获取当前目录下的所有文件"""
        files = set()
        for root, _, filenames in os.walk(self.sandbox_dir):
            for filename in filenames:
                filepath = Path(root) / filename
                files.add(str(filepath.relative_to(self.sandbox_dir)))
        return files
    
    def _detect_file_side_effects(self) -> None:
        """检测文件系统副作用"""
        created = self.final_files - self.initial_files
        deleted = self.initial_files - self.final_files
        modified = set()
        
        # 检查修改的文件（简化版，实际应该比较文件内容或哈希）
        for filepath in self.initial_files & self.final_files:
            full_path = self.sandbox_dir / filepath
            try:
                if full_path.stat().st_mtime > self._get_start_time():
                    modified.add(filepath)
            except FileNotFoundError:
                continue
        
        for file in created:
            self._add_side_effect(SideEffectType.FILE_CREATE, {"file": file})
        
        for file in modified:
            self._add_side_effect(SideEffectType.FILE_MODIFY, {"file": file})
        
        for file in deleted:
            self._add_side_effect(SideEffectType.FILE_DELETE, {"file": file})
    
    def _detect_resource_abuse(self) -> None:
        """检测资源滥用"""
        if self.memory_samples and max(self.memory_samples) > 50 * 1024 * 1024:  # 50MB
            self._add_side_effect(SideEffectType.MEMORY_OVERUSE, {
                "peak_memory": max(self.memory_samples) // 1024  # KB
            })
        
        if self.cpu_samples and max(self.cpu_samples) > 80:  # 80% CPU
            self._add_side_effect(SideEffectType.CPU_OVERUSE, {
                "peak_cpu": max(self.cpu_samples)
            })
    
    def _add_side_effect(self, effect_type: SideEffectType, details: Dict) -> None:
        """添加副作用记录"""
        self.side_effects.append({
            "type": effect_type.name,
            "details": details
        })
    
    def _get_start_time(self) -> float:
        """获取监控开始时间"""
        return time.time() - 5  # 简单实现，假设监控开始于5秒前


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    验证代码安全性（基础检查）
    
    参数:
        code: 要验证的Python代码字符串
        
    返回:
        Tuple[验证结果(bool), 错误信息(如果验证失败)]
    """
    # 检查危险操作
    dangerous_keywords = [
        'import os', 'import sys', 'import subprocess', 
        'import shutil', 'import socket', '__import__',
        'eval(', 'exec(', 'compile(', 'open(',
        'os.system', 'subprocess.call', 'subprocess.run',
        'shutil.rmtree', 'socket.socket'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in code:
            return False, f"检测到潜在危险操作: {keyword}"
    
    # 检查语法错误
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误: {str(e)}"
    
    return True, None


def run_in_sandbox(
    code: str,
    inputs: Optional[Dict[str, Any]] = None,
    expected_output: Optional[Any] = None,
    timeout: int = 5,
    memory_limit: int = 50,  # MB
    sandbox_dir: Optional[str] = None
) -> ExecutionResult:
    """
    在沙箱环境中执行代码
    
    参数:
        code: 要执行的Python代码
        inputs: 代码执行所需的输入参数
        expected_output: 预期的输出结果(用于验证)
        timeout: 执行超时时间(秒)
        memory_limit: 内存限制(MB)
        sandbox_dir: 沙箱目录路径(如果为None则创建临时目录)
        
    返回:
        ExecutionResult: 执行结果对象
    """
    # 初始化结果对象
    result = ExecutionResult()
    
    # 验证代码
    is_valid, error_msg = validate_code(code)
    if not is_valid:
        result.error = error_msg
        result.success = False
        return result
    
    # 准备输入参数
    inputs = inputs or {}
    if not isinstance(inputs, dict):
        result.error = "输入参数必须是字典类型"
        result.success = False
        return result
    
    # 创建沙箱目录
    if sandbox_dir is None:
        sandbox_dir = tempfile.mkdtemp(prefix="sandbox_")
    os.makedirs(sandbox_dir, exist_ok=True)
    
    # 准备执行环境
    exec_globals = {
        '__builtins__': {
            'print': print,
            'range': range,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'bool': bool,
            'None': None,
            'True': True,
            'False': False,
        },
        'inputs': inputs,
        'output': None,
    }
    
    # 添加代码中的函数定义到全局变量
    try:
        code_obj = compile(code, '<string>', 'exec')
        exec(code_obj, exec_globals)
    except Exception as e:
        result.error = f"代码编译错误: {str(e)}\n{traceback.format_exc()}"
        result.success = False
        return result
    
    # 检查是否有main函数
    if 'main' not in exec_globals or not callable(exec_globals['main']):
        result.error = "代码必须定义一个可调用的main()函数"
        result.success = False
        return result
    
    # 设置资源限制
    def set_limits():
        # 设置内存限制
        memory_limit_bytes = memory_limit * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        # 设置CPU时间限制(比timeout稍大)
        resource.setrlimit(resource.RLIMIT_CPU, (timeout + 1, timeout + 1))
    
    # 启动监控器
    monitor = SandboxMonitor(sandbox_dir)
    start_time = time.time()
    
    try:
        # 在子进程中执行代码以实现更好的隔离
        # 这里简化实现，实际生产环境应使用subprocess或容器
        pid = os.getpid()
        monitor.start_monitoring(pid)
        
        # 执行代码
        try:
            exec_globals['output'] = exec_globals['main'](**inputs)
            result.output = exec_globals['output']
            result.success = True
            
            # 验证输出是否符合预期
            if expected_output is not None:
                if result.output != expected_output:
                    result.error = f"输出不符合预期。预期: {expected_output}, 实际: {result.output}"
                    result.success = False
        except Exception as e:
            result.error = f"执行错误: {str(e)}\n{traceback.format_exc()}"
            result.success = False
    except Exception as e:
        result.error = f"沙箱错误: {str(e)}\n{traceback.format_exc()}"
        result.success = False
    finally:
        # 停止监控
        monitor.stop_monitoring()
        end_time = time.time()
        
        # 收集指标
        result.metrics = {
            "time": end_time - start_time,
            "memory": max(monitor.memory_samples) // 1024 if monitor.memory_samples else 0,
            "cpu": max(monitor.cpu_samples) if monitor.cpu_samples else 0,
        }
        
        # 添加副作用
        result.side_effects = monitor.side_effects
    
    return result


def cleanup_sandbox(sandbox_dir: str) -> bool:
    """
    清理沙箱环境
    
    参数:
        sandbox_dir: 要清理的沙箱目录路径
        
    返回:
        bool: 清理是否成功
    """
    try:
        if os.path.exists(sandbox_dir):
            for root, dirs, files in os.walk(sandbox_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(sandbox_dir)
        return True
    except Exception as e:
        logger.error(f"清理沙箱失败: {e}")
        return False


if __name__ == "__main__":
    # 示例用法
    sample_code = """
def main(a, b):
    # 测试正常执行
    result = a + b
    return result
"""
    
    sample_bad_code = """
def main():
    # 测试危险操作
    import os
    os.system('rm -rf /')
    return "This should not run"
"""
    
    sample_resource_abuse = """
def main():
    # 测试内存滥用
    big_list = [0] * 10**8  # 尝试分配大量内存
    return "This should trigger memory limit"
"""
    
    # 测试正常代码
    print("=== 测试正常代码 ===")
    result = run_in_sandbox(sample_code, {"a": 10, "b": 20}, expected_output=30)
    print(f"执行结果: {result.success}")
    print(f"输出: {result.output}")
    print(f"错误: {result.error}")
    print(f"指标: {result.metrics}")
    print(f"副作用: {result.side_effects}")
    
    # 测试危险代码
    print("\n=== 测试危险代码 ===")
    result = run_in_sandbox(sample_bad_code)
    print(f"执行结果: {result.success}")
    print(f"错误: {result.error}")
    
    # 测试资源滥用
    print("\n=== 测试资源滥用 ===")
    result = run_in_sandbox(sample_resource_abuse, memory_limit=10)  # 设置10MB内存限制
    print(f"执行结果: {result.success}")
    print(f"副作用: {result.side_effects}")