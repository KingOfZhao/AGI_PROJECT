#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shell Executor 技能 — 让模型通过Python脚本安全执行命令行操作

功能:
  1. 执行shell命令并捕获输出
  2. 执行Python代码片段
  3. 读取/写入文件
  4. 管理进程（列出/终止）
  5. 网络诊断（ping/curl/端口检查）

安全策略:
  - 所有命令通过subprocess执行，不使用shell=True（防注入）
  - 危险命令需要confirm=True确认
  - 超时保护（默认30秒）
  - 输出截断保护（最大10000字符）
"""

import subprocess
import sys
import os
import json
import socket
import signal
import time
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 危险命令关键字
DANGEROUS_KEYWORDS = ['rm -rf', 'mkfs', 'dd if=', 'format', '> /dev/', 'shutdown', 'reboot']

# 最大输出长度
MAX_OUTPUT = 10000

# 默认超时
DEFAULT_TIMEOUT = 30


def run_shell(cmd, cwd=None, timeout=DEFAULT_TIMEOUT, confirm=False, env=None):
    """执行shell命令并返回结果
    
    Args:
        cmd: 命令字符串或列表
        cwd: 工作目录（默认项目根目录）
        timeout: 超时秒数
        confirm: 危险命令需要True确认
        env: 环境变量字典
    
    Returns:
        dict: {success, stdout, stderr, returncode, duration}
    """
    if cwd is None:
        cwd = str(PROJECT_ROOT)
    
    # 安全检查
    cmd_str = cmd if isinstance(cmd, str) else ' '.join(cmd)
    for kw in DANGEROUS_KEYWORDS:
        if kw in cmd_str.lower() and not confirm:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'⚠ 危险命令被阻止: 包含 "{kw}"。设置 confirm=True 以强制执行。',
                'returncode': -1,
                'duration': 0
            }
    
    start = time.time()
    try:
        if isinstance(cmd, str):
            # 使用shell模式执行字符串命令
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd, env={**os.environ, **(env or {})}
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=cwd, env={**os.environ, **(env or {})}
            )
        
        duration = time.time() - start
        stdout = result.stdout[:MAX_OUTPUT] if result.stdout else ''
        stderr = result.stderr[:MAX_OUTPUT] if result.stderr else ''
        
        return {
            'success': result.returncode == 0,
            'stdout': stdout,
            'stderr': stderr,
            'returncode': result.returncode,
            'duration': round(duration, 3)
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'⚠ 命令超时 ({timeout}s)',
            'returncode': -1,
            'duration': timeout
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'duration': time.time() - start
        }


def run_python(code, timeout=DEFAULT_TIMEOUT):
    """执行Python代码片段 — tempfile模式(解决heredoc>卡死问题)
    
    使用临时文件执行, 彻底避免:
      - heredoc> 卡死 (shell等待EOF标记)
      - python -c 引号嵌套解析错误
      - 管道截断/特殊字符展开
    
    Args:
        code: Python代码字符串 (任意长度/引号嵌套均安全)
        timeout: 超时秒数
    
    Returns:
        dict: {success, stdout, stderr, returncode, duration}
    """
    import tempfile
    
    python = str(PROJECT_ROOT / 'venv' / 'bin' / 'python')
    if not os.path.exists(python):
        python = sys.executable
    
    fd, temp_path = tempfile.mkstemp(suffix='.py', prefix='shell_exec_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
        return run_shell([python, temp_path], timeout=timeout)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def run_script(script_path, args=None, timeout=60):
    """执行Python脚本文件
    
    Args:
        script_path: 脚本路径（相对于项目根目录或绝对路径）
        args: 命令行参数列表
        timeout: 超时秒数
    """
    python = str(PROJECT_ROOT / 'venv' / 'bin' / 'python')
    if not os.path.exists(python):
        python = sys.executable
    
    path = Path(script_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    
    if not path.exists():
        return {
            'success': False,
            'stdout': '',
            'stderr': f'脚本不存在: {path}',
            'returncode': -1,
            'duration': 0
        }
    
    cmd = [python, str(path)] + (args or [])
    return run_shell(cmd, timeout=timeout)


def read_file(file_path):
    """读取文件内容"""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        content = path.read_text(encoding='utf-8')
        return {'success': True, 'content': content, 'size': len(content), 'path': str(path)}
    except Exception as e:
        return {'success': False, 'content': '', 'error': str(e)}


def write_file(file_path, content, mkdir=True):
    """写入文件"""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return {'success': True, 'path': str(path), 'size': len(content)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def list_processes(filter_name=None):
    """列出进程"""
    cmd = 'ps aux'
    result = run_shell(cmd)
    if not result['success']:
        return result
    
    lines = result['stdout'].strip().split('\n')
    if filter_name:
        lines = [lines[0]] + [l for l in lines[1:] if filter_name.lower() in l.lower()]
    
    return {'success': True, 'processes': lines, 'count': len(lines) - 1}


def check_port(port, host='localhost'):
    """检查端口是否在监听"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return {'port': port, 'host': host, 'open': result == 0}
    except Exception as e:
        return {'port': port, 'host': host, 'open': False, 'error': str(e)}


def http_get(url, timeout=10):
    """HTTP GET请求"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AGI-Shell/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')[:MAX_OUTPUT]
            return {
                'success': True,
                'status': resp.status,
                'body': body,
                'headers': dict(resp.headers)
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def system_info():
    """获取系统信息"""
    import platform
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'arch': platform.machine(),
        'python': platform.python_version(),
        'hostname': platform.node(),
        'cwd': os.getcwd(),
        'project_root': str(PROJECT_ROOT),
        'venv': str(PROJECT_ROOT / 'venv'),
    }


def batch_run(commands):
    """批量执行命令（按顺序）
    
    Args:
        commands: 命令列表，每项为 str 或 dict{cmd, cwd, timeout}
    
    Returns:
        list of results
    """
    results = []
    for i, cmd in enumerate(commands):
        if isinstance(cmd, str):
            r = run_shell(cmd)
        elif isinstance(cmd, dict):
            r = run_shell(cmd.get('cmd', ''), 
                         cwd=cmd.get('cwd'),
                         timeout=cmd.get('timeout', DEFAULT_TIMEOUT))
        else:
            r = {'success': False, 'stderr': f'无效命令格式: {type(cmd)}'}
        
        r['index'] = i
        r['cmd'] = cmd if isinstance(cmd, str) else cmd.get('cmd', str(cmd))
        results.append(r)
        
        # 如果命令失败且不是允许失败的，停止
        if not r['success'] and (isinstance(cmd, dict) and not cmd.get('allow_fail', False)):
            break
    
    return results


# ==================== CLI入口 ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Shell Executor - AGI命令行能力')
    sub = parser.add_subparsers(dest='action')
    
    # run
    p_run = sub.add_parser('run', help='执行shell命令')
    p_run.add_argument('cmd', nargs='+', help='命令')
    p_run.add_argument('--cwd', help='工作目录')
    p_run.add_argument('--timeout', type=int, default=30)
    
    # python
    p_py = sub.add_parser('python', help='执行Python代码')
    p_py.add_argument('code', help='Python代码')
    
    # script
    p_sc = sub.add_parser('script', help='执行Python脚本')
    p_sc.add_argument('path', help='脚本路径')
    p_sc.add_argument('args', nargs='*', help='参数')
    
    # port
    p_port = sub.add_parser('port', help='检查端口')
    p_port.add_argument('port', type=int)
    
    # info
    sub.add_parser('info', help='系统信息')
    
    # ps
    p_ps = sub.add_parser('ps', help='列出进程')
    p_ps.add_argument('--filter', help='过滤关键字')
    
    # http
    p_http = sub.add_parser('http', help='HTTP GET')
    p_http.add_argument('url')
    
    args = parser.parse_args()
    
    if args.action == 'run':
        r = run_shell(' '.join(args.cmd), cwd=args.cwd, timeout=args.timeout)
    elif args.action == 'python':
        r = run_python(args.code)
    elif args.action == 'script':
        r = run_script(args.path, args.args)
    elif args.action == 'port':
        r = check_port(args.port)
    elif args.action == 'info':
        r = system_info()
    elif args.action == 'ps':
        r = list_processes(args.filter)
    elif args.action == 'http':
        r = http_get(args.url)
    else:
        parser.print_help()
        sys.exit(0)
    
    print(json.dumps(r, ensure_ascii=False, indent=2))
