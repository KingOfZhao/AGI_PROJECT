#!/usr/bin/env python3
"""
OpenClaw 代码代理 - 赋予 OpenClaw 类似 Windsurf 的代码执行能力

功能:
1. 文件读写/编辑 - 读取、创建、修改代码文件
2. 终端命令执行 - 安全执行 shell 命令
3. 项目结构分析 - 分析项目目录结构
4. 代码搜索 - grep/find 搜索代码
5. 代码重构 - 批量修改代码

用法:
  from code_agent import CodeAgent
  agent = CodeAgent(workspace="/path/to/project")
  result = agent.execute_action(action_dict)
"""

import os
import re
import sys
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_ROOT = PROJECT_ROOT

# 安全配置
SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "pwd", "echo",
    "python3", "python", "pip", "pip3", "node", "npm", "npx",
    "git", "curl", "wget", "jq", "sed", "awk", "sort", "uniq",
    "mkdir", "touch", "cp", "mv", "rm",  # 文件操作需要确认
}

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",       # rm -rf /
    r">\s*/dev/",          # 写入设备
    r"mkfs",               # 格式化
    r"dd\s+if=",           # dd 命令
    r"chmod\s+777",        # 危险权限
    r"curl.*\|\s*sh",      # 管道执行
    r"wget.*\|\s*sh",
]


@dataclass
class ActionResult:
    """操作结果"""
    success: bool
    action: str
    output: str = ""
    error: str = ""
    files_changed: List[str] = None
    
    def __post_init__(self):
        if self.files_changed is None:
            self.files_changed = []
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        if self.success:
            icon = "✅"
            status = "成功"
        else:
            icon = "❌"
            status = "失败"
        
        parts = [f"{icon} **{self.action}** - {status}"]
        
        if self.output:
            # 限制输出长度
            output = self.output[:2000]
            if len(self.output) > 2000:
                output += f"\n... (截断，共 {len(self.output)} 字符)"
            parts.append(f"```\n{output}\n```")
        
        if self.error:
            parts.append(f"**错误:** {self.error}")
        
        if self.files_changed:
            parts.append(f"**修改文件:** {', '.join(self.files_changed)}")
        
        return "\n".join(parts)


class CodeAgent:
    """代码代理 - 执行代码相关操作"""
    
    def __init__(self, workspace: Optional[str] = None):
        self.workspace = Path(workspace) if workspace else WORKSPACE_ROOT
        self.history: List[ActionResult] = []
        self.dry_run = False  # 试运行模式
    
    # ==================== 文件操作 ====================
    
    def read_file(self, path: str, start_line: int = 1, end_line: int = None) -> ActionResult:
        """读取文件内容"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return ActionResult(False, "read_file", error=f"文件不存在: {path}")
            
            if not file_path.is_file():
                return ActionResult(False, "read_file", error=f"不是文件: {path}")
            
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            # 行号范围
            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = end_line if end_line else total_lines
            
            selected = lines[start_idx:end_idx]
            
            # 添加行号
            numbered = []
            for i, line in enumerate(selected, start=start_idx + 1):
                numbered.append(f"{i:4d}│ {line.rstrip()}")
            
            output = "\n".join(numbered)
            header = f"# {file_path.name} (行 {start_idx+1}-{min(end_idx, total_lines)}/{total_lines})\n"
            
            return ActionResult(True, "read_file", output=header + output)
            
        except Exception as e:
            return ActionResult(False, "read_file", error=str(e))
    
    def write_file(self, path: str, content: str, create_dirs: bool = True) -> ActionResult:
        """写入文件（创建或覆盖）"""
        try:
            file_path = self._resolve_path(path)
            
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.dry_run:
                return ActionResult(True, "write_file", 
                    output=f"[DRY RUN] 将写入 {len(content)} 字符到 {path}",
                    files_changed=[str(file_path)])
            
            # 备份原文件
            if file_path.exists():
                backup = file_path.with_suffix(file_path.suffix + ".bak")
                shutil.copy2(file_path, backup)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return ActionResult(True, "write_file", 
                output=f"已写入 {len(content)} 字符到 {path}",
                files_changed=[str(file_path)])
            
        except Exception as e:
            return ActionResult(False, "write_file", error=str(e))
    
    def edit_file(self, path: str, old_string: str, new_string: str, 
                  replace_all: bool = False) -> ActionResult:
        """编辑文件 - 查找并替换"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return ActionResult(False, "edit_file", error=f"文件不存在: {path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 检查 old_string 是否存在
            count = content.count(old_string)
            if count == 0:
                return ActionResult(False, "edit_file", 
                    error=f"未找到要替换的内容: {old_string[:100]}...")
            
            if count > 1 and not replace_all:
                return ActionResult(False, "edit_file",
                    error=f"找到 {count} 处匹配，请使用 replace_all=True 或提供更精确的内容")
            
            # 执行替换
            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
            
            if self.dry_run:
                return ActionResult(True, "edit_file",
                    output=f"[DRY RUN] 将替换 {count} 处",
                    files_changed=[str(file_path)])
            
            # 备份并写入
            backup = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            replaced = count if replace_all else 1
            return ActionResult(True, "edit_file",
                output=f"已替换 {replaced} 处",
                files_changed=[str(file_path)])
            
        except Exception as e:
            return ActionResult(False, "edit_file", error=str(e))
    
    def multi_edit(self, path: str, edits: List[Dict[str, str]]) -> ActionResult:
        """批量编辑文件"""
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return ActionResult(False, "multi_edit", error=f"文件不存在: {path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 依次应用编辑
            for i, edit in enumerate(edits):
                old_str = edit.get("old_string", "")
                new_str = edit.get("new_string", "")
                replace_all = edit.get("replace_all", False)
                
                if old_str not in content:
                    return ActionResult(False, "multi_edit",
                        error=f"编辑 {i+1} 失败: 未找到 '{old_str[:50]}...'")
                
                if replace_all:
                    content = content.replace(old_str, new_str)
                else:
                    content = content.replace(old_str, new_str, 1)
            
            if self.dry_run:
                return ActionResult(True, "multi_edit",
                    output=f"[DRY RUN] 将应用 {len(edits)} 处编辑",
                    files_changed=[str(file_path)])
            
            # 备份并写入
            backup = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return ActionResult(True, "multi_edit",
                output=f"已应用 {len(edits)} 处编辑",
                files_changed=[str(file_path)])
            
        except Exception as e:
            return ActionResult(False, "multi_edit", error=str(e))
    
    # ==================== 终端命令 ====================
    
    def run_command(self, command: str, cwd: str = None, 
                    timeout: int = 60, safe_check: bool = True) -> ActionResult:
        """执行终端命令"""
        try:
            # 安全检查
            if safe_check:
                safety = self._check_command_safety(command)
                if not safety["safe"]:
                    return ActionResult(False, "run_command",
                        error=f"命令被拒绝: {safety['reason']}")
            
            work_dir = self._resolve_path(cwd) if cwd else self.workspace
            
            if self.dry_run:
                return ActionResult(True, "run_command",
                    output=f"[DRY RUN] 将在 {work_dir} 执行: {command}")
            
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PAGER": "cat"},
            )
            
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"[stderr]\n{result.stderr}")
            
            output = "\n".join(output_parts)
            
            if result.returncode == 0:
                return ActionResult(True, "run_command", output=output)
            else:
                return ActionResult(False, "run_command",
                    output=output,
                    error=f"退出码: {result.returncode}")
            
        except subprocess.TimeoutExpired:
            return ActionResult(False, "run_command", error=f"命令超时 ({timeout}s)")
        except Exception as e:
            return ActionResult(False, "run_command", error=str(e))
    
    def _check_command_safety(self, command: str) -> Dict[str, Any]:
        """检查命令安全性"""
        # 检查危险模式
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return {"safe": False, "reason": f"匹配危险模式: {pattern}"}
        
        # 提取主命令
        parts = command.strip().split()
        if not parts:
            return {"safe": False, "reason": "空命令"}
        
        main_cmd = parts[0]
        
        # 处理管道和重定向前的命令
        for sep in ["|", "&&", "||", ";"]:
            if sep in main_cmd:
                main_cmd = main_cmd.split(sep)[0].strip()
        
        # 允许路径形式的命令
        if "/" in main_cmd:
            main_cmd = os.path.basename(main_cmd)
        
        return {"safe": True, "reason": ""}
    
    # ==================== 项目分析 ====================
    
    def list_dir(self, path: str = ".", max_depth: int = 3) -> ActionResult:
        """列出目录结构"""
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return ActionResult(False, "list_dir", error=f"目录不存在: {path}")
            
            if not dir_path.is_dir():
                return ActionResult(False, "list_dir", error=f"不是目录: {path}")
            
            lines = []
            self._tree(dir_path, lines, "", max_depth, 0)
            
            output = f"# {dir_path.name}/\n" + "\n".join(lines)
            return ActionResult(True, "list_dir", output=output)
            
        except Exception as e:
            return ActionResult(False, "list_dir", error=str(e))
    
    def _tree(self, path: Path, lines: list, prefix: str, max_depth: int, depth: int):
        """递归生成目录树"""
        if depth >= max_depth:
            return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        
        # 过滤隐藏文件和常见忽略目录
        ignored = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
        items = [i for i in items if i.name not in ignored and not i.name.startswith(".")]
        
        for i, item in enumerate(items[:50]):  # 限制数量
            is_last = (i == len(items) - 1) or (i == 49)
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._tree(item, lines, new_prefix, max_depth, depth + 1)
            else:
                size = item.stat().st_size
                size_str = self._format_size(size)
                lines.append(f"{prefix}{connector}{item.name} ({size_str})")
        
        if len(items) > 50:
            lines.append(f"{prefix}... 还有 {len(items) - 50} 个项目")
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}" if unit != "B" else f"{size}B"
            size /= 1024
        return f"{size:.1f}TB"
    
    def grep_search(self, query: str, path: str = ".", 
                    includes: List[str] = None, case_sensitive: bool = False) -> ActionResult:
        """搜索代码"""
        try:
            search_path = self._resolve_path(path)
            
            cmd = ["grep", "-rn"]
            if not case_sensitive:
                cmd.append("-i")
            
            if includes:
                for pattern in includes:
                    cmd.extend(["--include", pattern])
            
            cmd.extend([query, str(search_path)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            output = result.stdout if result.stdout else "未找到匹配"
            # 限制输出
            lines = output.split("\n")
            if len(lines) > 100:
                output = "\n".join(lines[:100]) + f"\n... 还有 {len(lines) - 100} 行"
            
            return ActionResult(True, "grep_search", output=output)
            
        except Exception as e:
            return ActionResult(False, "grep_search", error=str(e))
    
    def find_files(self, pattern: str, path: str = ".", 
                   file_type: str = "f") -> ActionResult:
        """查找文件"""
        try:
            search_path = self._resolve_path(path)
            
            cmd = ["find", str(search_path), "-type", file_type, "-name", pattern]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            output = result.stdout if result.stdout else "未找到文件"
            return ActionResult(True, "find_files", output=output)
            
        except Exception as e:
            return ActionResult(False, "find_files", error=str(e))
    
    def analyze_project(self, path: str = ".") -> ActionResult:
        """分析项目结构"""
        try:
            project_path = self._resolve_path(path)
            
            analysis = {
                "name": project_path.name,
                "path": str(project_path),
                "type": "unknown",
                "languages": [],
                "frameworks": [],
                "entry_points": [],
                "config_files": [],
            }
            
            # 检测项目类型
            indicators = {
                "package.json": ("node", "JavaScript/TypeScript"),
                "requirements.txt": ("python", "Python"),
                "setup.py": ("python", "Python"),
                "pyproject.toml": ("python", "Python"),
                "Cargo.toml": ("rust", "Rust"),
                "go.mod": ("go", "Go"),
                "pom.xml": ("java", "Java"),
                "build.gradle": ("java", "Java/Kotlin"),
                "pubspec.yaml": ("flutter", "Dart/Flutter"),
            }
            
            for file, (proj_type, lang) in indicators.items():
                if (project_path / file).exists():
                    analysis["type"] = proj_type
                    if lang not in analysis["languages"]:
                        analysis["languages"].append(lang)
                    analysis["config_files"].append(file)
            
            # 检测框架
            framework_indicators = {
                "next.config.js": "Next.js",
                "nuxt.config.js": "Nuxt.js",
                "vite.config.js": "Vite",
                "webpack.config.js": "Webpack",
                "manage.py": "Django",
                "app.py": "Flask",
                "fastapi": "FastAPI",
            }
            
            for file, framework in framework_indicators.items():
                if (project_path / file).exists():
                    analysis["frameworks"].append(framework)
            
            # 查找入口文件
            entry_candidates = ["main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs"]
            for entry in entry_candidates:
                if (project_path / entry).exists():
                    analysis["entry_points"].append(entry)
                if (project_path / "src" / entry).exists():
                    analysis["entry_points"].append(f"src/{entry}")
            
            # 统计文件
            stats = {"files": 0, "dirs": 0, "lines": 0}
            for item in project_path.rglob("*"):
                if item.is_file() and not any(p in str(item) for p in [".git", "__pycache__", "node_modules"]):
                    stats["files"] += 1
                    if item.suffix in [".py", ".js", ".ts", ".go", ".rs", ".java"]:
                        try:
                            stats["lines"] += len(item.read_text().split("\n"))
                        except:
                            pass
                elif item.is_dir():
                    stats["dirs"] += 1
            
            analysis["stats"] = stats
            
            output = json.dumps(analysis, ensure_ascii=False, indent=2)
            return ActionResult(True, "analyze_project", output=output)
            
        except Exception as e:
            return ActionResult(False, "analyze_project", error=str(e))
    
    # ==================== 辅助方法 ====================
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径（相对于工作区）"""
        if path is None:
            return self.workspace
        
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace / path
    
    # ==================== 代码增强器集成 ====================
    
    def _get_enhancer(self):
        """懒加载代码增强器"""
        if not hasattr(self, '_enhancer'):
            try:
                from code_enhancer import CodeEnhancer
                self._enhancer = CodeEnhancer(str(self.workspace))
            except ImportError:
                self._enhancer = None
        return self._enhancer
    
    def _search_symbols(self, query: str, kind: str = None) -> ActionResult:
        """搜索代码符号"""
        enhancer = self._get_enhancer()
        if not enhancer:
            return ActionResult(False, "search_symbols", error="代码增强器未加载")
        
        try:
            results = enhancer.search(query, kind)
            output = f"找到 {len(results)} 个符号:\n"
            for r in results[:20]:
                output += f"  {r['file']}:{r['line']} - {r['kind']} {r['name']}\n"
            return ActionResult(True, "search_symbols", output=output)
        except Exception as e:
            return ActionResult(False, "search_symbols", error=str(e))
    
    def _run_and_fix(self, command: str) -> ActionResult:
        """执行命令并自动修复错误"""
        enhancer = self._get_enhancer()
        if not enhancer:
            return ActionResult(False, "run_and_fix", error="代码增强器未加载")
        
        try:
            result = enhancer.run_and_fix(command)
            output = f"执行结果: {'成功' if result['success'] else '失败'}\n"
            output += f"尝试次数: {result.get('attempts', 1)}\n"
            if result.get('stdout'):
                output += f"输出:\n{result['stdout'][:1000]}\n"
            if result.get('errors'):
                output += f"错误:\n{json.dumps(result['errors'], ensure_ascii=False, indent=2)}\n"
            return ActionResult(result['success'], "run_and_fix", output=output)
        except Exception as e:
            return ActionResult(False, "run_and_fix", error=str(e))
    
    def _index_project(self, extensions: str = None) -> ActionResult:
        """索引项目"""
        enhancer = self._get_enhancer()
        if not enhancer:
            return ActionResult(False, "index_project", error="代码增强器未加载")
        
        try:
            ext_list = extensions.split(",") if extensions else None
            stats = enhancer.indexer.index_project(ext_list)
            output = f"索引完成:\n"
            output += f"  文件数: {stats['files']}\n"
            output += f"  符号数: {stats['symbols']}\n"
            output += f"  错误数: {stats['errors']}\n"
            return ActionResult(True, "index_project", output=output)
        except Exception as e:
            return ActionResult(False, "index_project", error=str(e))
    
    # ==================== 统一执行接口 ====================
    
    def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        """
        统一执行接口 - 解析并执行动作
        
        action 格式:
        {
            "type": "read_file|write_file|edit_file|run_command|list_dir|grep_search|...",
            "params": { ... }
        }
        """
        action_type = action.get("type", "")
        params = action.get("params", {})
        
        handlers = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "edit_file": self.edit_file,
            "multi_edit": self.multi_edit,
            "run_command": self.run_command,
            "list_dir": self.list_dir,
            "grep_search": self.grep_search,
            "find_files": self.find_files,
            "analyze_project": self.analyze_project,
            # 代码增强器集成
            "search_symbols": self._search_symbols,
            "run_and_fix": self._run_and_fix,
            "index_project": self._index_project,
        }
        
        handler = handlers.get(action_type)
        if not handler:
            return ActionResult(False, action_type, error=f"未知操作类型: {action_type}")
        
        try:
            result = handler(**params)
            self.history.append(result)
            return result
        except TypeError as e:
            return ActionResult(False, action_type, error=f"参数错误: {e}")
        except Exception as e:
            return ActionResult(False, action_type, error=str(e))
    
    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """批量执行多个动作"""
        results = []
        for action in actions:
            result = self.execute_action(action)
            results.append(result)
            if not result.success:
                break  # 遇到错误停止
        return results


# ==================== OpenClaw 集成 ====================

def parse_code_actions(ai_response: str) -> List[Dict[str, Any]]:
    """
    从 AI 响应中解析代码操作指令
    
    支持格式:
    ```action
    {"type": "read_file", "params": {"path": "main.py"}}
    ```
    
    或多个操作:
    ```actions
    [
        {"type": "read_file", "params": {"path": "main.py"}},
        {"type": "run_command", "params": {"command": "python main.py"}}
    ]
    ```
    """
    actions = []
    
    # 匹配 ```action 或 ```actions 代码块
    pattern = r"```(?:action|actions)\s*\n(.*?)\n```"
    matches = re.findall(pattern, ai_response, re.DOTALL)
    
    for match in matches:
        try:
            parsed = json.loads(match.strip())
            if isinstance(parsed, list):
                actions.extend(parsed)
            else:
                actions.append(parsed)
        except json.JSONDecodeError:
            continue
    
    return actions


def execute_ai_actions(ai_response: str, workspace: str = None) -> str:
    """
    执行 AI 响应中的所有代码操作，返回结果
    
    供 OpenClaw Bridge 调用
    """
    actions = parse_code_actions(ai_response)
    
    if not actions:
        return ""
    
    agent = CodeAgent(workspace=workspace)
    results = agent.execute_actions(actions)
    
    # 格式化结果
    output_parts = ["## 代码执行结果\n"]
    for result in results:
        output_parts.append(result.to_markdown())
        output_parts.append("")
    
    return "\n".join(output_parts)


# ==================== CLI ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw 代码代理")
    parser.add_argument("--workspace", "-w", default=".", help="工作区路径")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # read
    read_parser = subparsers.add_parser("read", help="读取文件")
    read_parser.add_argument("path", help="文件路径")
    read_parser.add_argument("--start", type=int, default=1, help="起始行")
    read_parser.add_argument("--end", type=int, help="结束行")
    
    # write
    write_parser = subparsers.add_parser("write", help="写入文件")
    write_parser.add_argument("path", help="文件路径")
    write_parser.add_argument("content", help="内容")
    
    # run
    run_parser = subparsers.add_parser("run", help="执行命令")
    run_parser.add_argument("cmd", help="命令")
    
    # list
    list_parser = subparsers.add_parser("list", help="列出目录")
    list_parser.add_argument("path", nargs="?", default=".", help="目录路径")
    
    # grep
    grep_parser = subparsers.add_parser("grep", help="搜索代码")
    grep_parser.add_argument("query", help="搜索内容")
    grep_parser.add_argument("--path", default=".", help="搜索路径")
    
    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="分析项目")
    analyze_parser.add_argument("path", nargs="?", default=".", help="项目路径")
    
    args = parser.parse_args()
    
    agent = CodeAgent(workspace=args.workspace)
    agent.dry_run = args.dry_run
    
    if args.command == "read":
        result = agent.read_file(args.path, args.start, args.end)
    elif args.command == "write":
        result = agent.write_file(args.path, args.content)
    elif args.command == "run":
        result = agent.run_command(args.cmd)
    elif args.command == "list":
        result = agent.list_dir(args.path)
    elif args.command == "grep":
        result = agent.grep_search(args.query, args.path)
    elif args.command == "analyze":
        result = agent.analyze_project(args.path)
    else:
        parser.print_help()
        return
    
    print(result.to_markdown())


if __name__ == "__main__":
    main()
