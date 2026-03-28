#!/usr/bin/env python3
"""
终端执行器 - OpenClaw终端调用能力强化

功能:
1. 安全命令白名单
2. 命令链式执行
3. 输出解析和错误处理
4. 与项目模块集成
"""

import os
import sys
import re
import json
import shlex
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time

PROJECT_ROOT = Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════════
# 安全配置
# ═══════════════════════════════════════════════════════════════

class SecurityLevel(Enum):
    """安全等级"""
    SAFE = "safe"           # 完全安全，可自动执行
    MODERATE = "moderate"   # 中等风险，需确认
    DANGEROUS = "dangerous" # 危险，禁止执行


# 命令白名单
COMMAND_WHITELIST = {
    # 文件查看类 - SAFE
    "cat": SecurityLevel.SAFE,
    "head": SecurityLevel.SAFE,
    "tail": SecurityLevel.SAFE,
    "less": SecurityLevel.SAFE,
    "wc": SecurityLevel.SAFE,
    "ls": SecurityLevel.SAFE,
    "find": SecurityLevel.SAFE,
    "grep": SecurityLevel.SAFE,
    "rg": SecurityLevel.SAFE,
    "fd": SecurityLevel.SAFE,
    "tree": SecurityLevel.SAFE,
    "file": SecurityLevel.SAFE,
    "stat": SecurityLevel.SAFE,
    "du": SecurityLevel.SAFE,
    "df": SecurityLevel.SAFE,
    
    # 文本处理类 - SAFE
    "echo": SecurityLevel.SAFE,
    "printf": SecurityLevel.SAFE,
    "awk": SecurityLevel.SAFE,
    "sed": SecurityLevel.SAFE,
    "cut": SecurityLevel.SAFE,
    "sort": SecurityLevel.SAFE,
    "uniq": SecurityLevel.SAFE,
    "tr": SecurityLevel.SAFE,
    "jq": SecurityLevel.SAFE,
    "xargs": SecurityLevel.SAFE,
    
    # 开发工具 - SAFE
    "python3": SecurityLevel.SAFE,
    "python": SecurityLevel.SAFE,
    "node": SecurityLevel.SAFE,
    "npm": SecurityLevel.MODERATE,
    "pip": SecurityLevel.MODERATE,
    "pip3": SecurityLevel.MODERATE,
    "git": SecurityLevel.SAFE,
    "which": SecurityLevel.SAFE,
    "whereis": SecurityLevel.SAFE,
    "type": SecurityLevel.SAFE,
    
    # 网络类 - MODERATE
    "curl": SecurityLevel.MODERATE,
    "wget": SecurityLevel.MODERATE,
    "ping": SecurityLevel.SAFE,
    "dig": SecurityLevel.SAFE,
    "nslookup": SecurityLevel.SAFE,
    
    # 系统信息 - SAFE
    "uname": SecurityLevel.SAFE,
    "hostname": SecurityLevel.SAFE,
    "whoami": SecurityLevel.SAFE,
    "date": SecurityLevel.SAFE,
    "uptime": SecurityLevel.SAFE,
    "ps": SecurityLevel.SAFE,
    "top": SecurityLevel.SAFE,
    "env": SecurityLevel.SAFE,
    "printenv": SecurityLevel.SAFE,
    
    # 文件操作 - MODERATE/DANGEROUS
    "mkdir": SecurityLevel.MODERATE,
    "touch": SecurityLevel.MODERATE,
    "cp": SecurityLevel.MODERATE,
    "mv": SecurityLevel.DANGEROUS,
    "rm": SecurityLevel.DANGEROUS,
    "chmod": SecurityLevel.DANGEROUS,
    "chown": SecurityLevel.DANGEROUS,
}

# 危险参数模式
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+~",           # rm -rf ~
    r">\s*/dev/",              # 重定向到设备
    r";\s*rm\s+",              # 命令注入 rm
    r"\|\s*sh",                # 管道到 sh
    r"\|\s*bash",              # 管道到 bash
    r"`.*`",                   # 命令替换
    r"\$\(.*\)",               # 命令替换
    r"&&\s*rm\s+",             # && rm
    r"\|\|\s*rm\s+",           # || rm
    r"sudo\s+",                # sudo
    r"eval\s+",                # eval
    r"exec\s+",                # exec
    r"mkfs",                   # 格式化
    r"dd\s+if=",               # dd
    r":(){",                   # fork bomb
]


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class CommandResult:
    """命令执行结果"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    security_level: SecurityLevel = SecurityLevel.SAFE
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0
    
    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "success": self.success
        }


@dataclass
class ChainStep:
    """链式执行步骤"""
    command: str
    condition: str = "always"  # always, on_success, on_failure
    transform: Optional[Callable[[str], str]] = None
    timeout: int = 30


@dataclass
class ChainResult:
    """链式执行结果"""
    steps: List[CommandResult]
    total_duration_ms: int
    success: bool
    final_output: str


# ═══════════════════════════════════════════════════════════════
# 终端执行器
# ═══════════════════════════════════════════════════════════════

class TerminalExecutor:
    """安全终端执行器"""
    
    def __init__(self, 
                 working_dir: Path = None,
                 allowed_dirs: List[Path] = None,
                 max_output_size: int = 1024 * 1024,  # 1MB
                 default_timeout: int = 30):
        
        self.working_dir = working_dir or PROJECT_ROOT
        self.allowed_dirs = allowed_dirs or [PROJECT_ROOT, Path.home()]
        self.max_output_size = max_output_size
        self.default_timeout = default_timeout
        
        self.history: List[CommandResult] = []
        self.env = os.environ.copy()
        self.env["PAGER"] = "cat"  # 禁用分页
    
    # ==================== 安全检查 ====================
    
    def check_security(self, command: str) -> Tuple[SecurityLevel, str]:
        """检查命令安全性"""
        # 检查危险模式
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return SecurityLevel.DANGEROUS, f"匹配危险模式: {pattern}"
        
        # 解析命令
        try:
            parts = shlex.split(command)
            if not parts:
                return SecurityLevel.DANGEROUS, "空命令"
            
            base_cmd = parts[0].split("/")[-1]  # 处理绝对路径
        except ValueError as e:
            return SecurityLevel.DANGEROUS, f"命令解析失败: {e}"
        
        # 检查白名单
        if base_cmd in COMMAND_WHITELIST:
            level = COMMAND_WHITELIST[base_cmd]
            
            # 特殊检查
            if base_cmd in ["rm", "mv"] and any(p.startswith("-r") for p in parts):
                return SecurityLevel.DANGEROUS, "递归删除/移动操作"
            
            if base_cmd == "curl" and any(p in parts for p in ["-X", "--request"]):
                method = None
                for i, p in enumerate(parts):
                    if p in ["-X", "--request"] and i + 1 < len(parts):
                        method = parts[i + 1].upper()
                if method and method != "GET":
                    return SecurityLevel.MODERATE, f"非GET请求: {method}"
            
            return level, "白名单命令"
        
        return SecurityLevel.DANGEROUS, f"未知命令: {base_cmd}"
    
    def is_path_allowed(self, path: str) -> bool:
        """检查路径是否允许"""
        try:
            resolved = Path(path).resolve()
            return any(
                resolved == allowed or resolved.is_relative_to(allowed)
                for allowed in self.allowed_dirs
            )
        except Exception:
            return False
    
    # ==================== 命令执行 ====================
    
    def execute(self, 
                command: str,
                timeout: int = None,
                check_security: bool = True,
                capture_output: bool = True,
                cwd: Path = None) -> CommandResult:
        """执行单个命令"""
        
        timeout = timeout or self.default_timeout
        cwd = cwd or self.working_dir
        
        # 安全检查
        if check_security:
            level, reason = self.check_security(command)
            if level == SecurityLevel.DANGEROUS:
                return CommandResult(
                    command=command,
                    exit_code=-1,
                    stdout="",
                    stderr=f"安全检查失败: {reason}",
                    duration_ms=0,
                    security_level=level
                )
        else:
            level = SecurityLevel.SAFE
        
        # 执行命令
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=capture_output,
                timeout=timeout,
                env=self.env,
                text=True
            )
            
            stdout = result.stdout[:self.max_output_size] if result.stdout else ""
            stderr = result.stderr[:self.max_output_size] if result.stderr else ""
            
            cmd_result = CommandResult(
                command=command,
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=int((time.time() - start_time) * 1000),
                security_level=level
            )
            
        except subprocess.TimeoutExpired:
            cmd_result = CommandResult(
                command=command,
                exit_code=-2,
                stdout="",
                stderr=f"命令超时 ({timeout}秒)",
                duration_ms=timeout * 1000,
                security_level=level
            )
        except Exception as e:
            cmd_result = CommandResult(
                command=command,
                exit_code=-3,
                stdout="",
                stderr=f"执行异常: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000),
                security_level=level
            )
        
        self.history.append(cmd_result)
        return cmd_result
    
    def execute_chain(self, steps: List[ChainStep]) -> ChainResult:
        """链式执行命令"""
        results: List[CommandResult] = []
        total_start = time.time()
        last_output = ""
        
        for step in steps:
            # 检查条件
            if results:
                last_success = results[-1].success
                if step.condition == "on_success" and not last_success:
                    continue
                if step.condition == "on_failure" and last_success:
                    continue
            
            # 替换占位符
            command = step.command
            if "{output}" in command:
                command = command.replace("{output}", shlex.quote(last_output.strip()))
            if "{last_exit}" in command and results:
                command = command.replace("{last_exit}", str(results[-1].exit_code))
            
            # 执行
            result = self.execute(command, timeout=step.timeout)
            results.append(result)
            
            # 转换输出
            if step.transform and result.success:
                last_output = step.transform(result.stdout)
            else:
                last_output = result.stdout
            
            # 失败且非 on_failure 条件时停止
            if not result.success and step.condition != "on_failure":
                break
        
        total_duration = int((time.time() - total_start) * 1000)
        
        return ChainResult(
            steps=results,
            total_duration_ms=total_duration,
            success=all(r.success for r in results),
            final_output=last_output
        )
    
    # ==================== 输出解析 ====================
    
    def parse_json(self, output: str) -> Optional[Any]:
        """解析JSON输出"""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            match = re.search(r'\{.*\}|\[.*\]', output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None
    
    def parse_table(self, output: str, delimiter: str = None) -> List[List[str]]:
        """解析表格输出"""
        lines = output.strip().split('\n')
        if not lines:
            return []
        
        result = []
        for line in lines:
            if delimiter:
                result.append(line.split(delimiter))
            else:
                result.append(line.split())
        
        return result
    
    def parse_key_value(self, output: str, separator: str = "=") -> Dict[str, str]:
        """解析键值对输出"""
        result = {}
        for line in output.strip().split('\n'):
            if separator in line:
                key, _, value = line.partition(separator)
                result[key.strip()] = value.strip()
        return result
    
    def extract_numbers(self, output: str) -> List[float]:
        """提取数字"""
        numbers = re.findall(r'-?\d+\.?\d*', output)
        return [float(n) for n in numbers]
    
    def extract_paths(self, output: str) -> List[Path]:
        """提取路径"""
        paths = []
        for line in output.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('/') or line.startswith('.') or Path(line).exists()):
                paths.append(Path(line))
        return paths
    
    # ==================== 项目集成 ====================
    
    def run_python(self, script: str, args: List[str] = None) -> CommandResult:
        """运行Python脚本"""
        args_str = ' '.join(shlex.quote(a) for a in (args or []))
        command = f"python3 {shlex.quote(script)} {args_str}"
        return self.execute(command)
    
    def run_rose_crm(self, action: str, *args) -> CommandResult:
        """运行予人玫瑰CRM命令"""
        script = PROJECT_ROOT / "项目清单/予人玫瑰/rose_crm.py"
        return self.run_python(str(script), [action] + list(args))
    
    def run_diecut_3d(self, cad_file: str = None, demo: bool = False) -> CommandResult:
        """运行刀模3D生成"""
        script = PROJECT_ROOT / "项目清单/刀模活字印刷3D项目/cad_to_3d.py"
        args = []
        if demo:
            args.append("--demo")
        elif cad_file:
            args.append(cad_file)
        return self.run_python(str(script), args)
    
    def run_code_enhancer(self, action: str, *args) -> CommandResult:
        """运行代码增强器"""
        script = PROJECT_ROOT / "scripts/code_enhancer.py"
        return self.run_python(str(script), [action] + list(args))
    
    # ==================== 工作流 ====================
    
    def workflow_customer_order(self, 
                                customer_name: str,
                                company: str,
                                cad_file: str = None) -> Dict[str, Any]:
        """客户下单工作流：创建客户 → 生成刀模 → 自动报价"""
        
        results = {
            "customer": None,
            "diecut": None,
            "quote": None,
            "success": False,
            "errors": []
        }
        
        # 1. 创建客户
        customer_result = self.run_rose_crm(
            "customer", "add", customer_name, 
            f"--company={company}"
        )
        
        if not customer_result.success:
            results["errors"].append(f"创建客户失败: {customer_result.stderr}")
            return results
        
        # 解析客户ID
        match = re.search(r'ID:\s*(\d+)', customer_result.stdout)
        customer_id = match.group(1) if match else None
        results["customer"] = {"id": customer_id, "name": customer_name}
        
        # 2. 生成刀模模块
        if cad_file:
            diecut_result = self.run_diecut_3d(cad_file)
        else:
            diecut_result = self.run_diecut_3d(demo=True)
        
        if not diecut_result.success:
            results["errors"].append(f"刀模生成失败: {diecut_result.stderr}")
            return results
        
        # 解析模块信息
        match = re.search(r'总模块数:\s*(\d+)', diecut_result.stdout)
        module_count = int(match.group(1)) if match else 0
        
        match = re.search(r'预估成本:\s*¥([\d.]+)', diecut_result.stdout)
        estimated_cost = float(match.group(1)) if match else 0
        
        results["diecut"] = {
            "module_count": module_count,
            "estimated_cost": estimated_cost
        }
        
        # 3. 生成报价
        markup = 1.5  # 50% 利润
        quote_price = estimated_cost * markup
        
        # 创建任务
        task_result = self.run_rose_crm(
            "task", "add", 
            f"刀模订单-{customer_name}",
            f"--customer_id={customer_id}",
            "--priority=high"
        )
        
        results["quote"] = {
            "cost": estimated_cost,
            "price": quote_price,
            "markup": markup,
            "task_created": task_result.success
        }
        
        results["success"] = True
        return results


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw终端执行器")
    parser.add_argument("command", nargs="*", help="要执行的命令")
    parser.add_argument("--check", action="store_true", help="仅检查安全性")
    parser.add_argument("--chain", action="store_true", help="链式执行模式")
    parser.add_argument("--workflow", choices=["order"], help="执行工作流")
    parser.add_argument("--customer", help="客户名称")
    parser.add_argument("--company", help="公司名称")
    parser.add_argument("--cad", help="CAD文件")
    
    args = parser.parse_args()
    
    executor = TerminalExecutor()
    
    if args.workflow == "order":
        if not args.customer or not args.company:
            print("工作流需要 --customer 和 --company 参数")
            return
        
        print(f"执行客户下单工作流: {args.customer} @ {args.company}")
        result = executor.workflow_customer_order(
            args.customer, 
            args.company,
            args.cad
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    if not args.command:
        parser.print_help()
        return
    
    command = ' '.join(args.command)
    
    if args.check:
        level, reason = executor.check_security(command)
        print(f"安全等级: {level.value}")
        print(f"原因: {reason}")
        return
    
    result = executor.execute(command)
    
    print(f"命令: {result.command}")
    print(f"退出码: {result.exit_code}")
    print(f"耗时: {result.duration_ms}ms")
    print(f"安全等级: {result.security_level.value}")
    
    if result.stdout:
        print(f"\n=== 输出 ===\n{result.stdout}")
    if result.stderr:
        print(f"\n=== 错误 ===\n{result.stderr}")


if __name__ == "__main__":
    main()
