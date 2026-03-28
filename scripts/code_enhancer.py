#!/usr/bin/env python3
"""
代码增强系统 - OpenClaw 代码实现能力强化模块

包含:
1. ProjectIndexer - AST解析、符号索引、依赖图
2. DiffEngine - 精确代码编辑、冲突检测
3. ExecutionLoop - 编译/测试/自动重试
4. AutoFixer - 根据错误自动修复

用法:
    from code_enhancer import CodeEnhancer
    enhancer = CodeEnhancer(workspace="/path/to/project")
    result = enhancer.analyze_and_fix("main.py")
"""

import os
import re
import ast
import sys
import json
import difflib
import subprocess
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("code_enhancer")


# ==================== 数据结构 ====================

@dataclass
class Symbol:
    """代码符号"""
    name: str
    kind: str  # function, class, variable, import, method
    file: str
    line: int
    end_line: int = 0
    signature: str = ""
    docstring: str = ""
    references: List[Tuple[str, int]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EditOperation:
    """编辑操作"""
    filepath: str
    operation: str  # replace, insert, delete
    start_line: int
    end_line: int
    old_content: str = ""
    new_content: str = ""
    description: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    return_code: int
    stdout: str
    stderr: str
    duration: float
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def parse_errors(self):
        """解析错误信息"""
        # Python错误
        py_pattern = r'File "([^"]+)", line (\d+).*?\n\s*(\w+Error): (.+)'
        for match in re.finditer(py_pattern, self.stderr, re.MULTILINE):
            self.errors.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "type": match.group(3),
                "message": match.group(4)
            })
        
        # TypeScript/JavaScript错误
        ts_pattern = r'(\S+\.(?:ts|js|tsx|jsx)):(\d+):(\d+) - error (TS\d+): (.+)'
        for match in re.finditer(ts_pattern, self.stderr):
            self.errors.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "code": match.group(4),
                "message": match.group(5)
            })


# ==================== ProjectIndexer ====================

class ProjectIndexer:
    """项目索引器 - AST解析、符号提取、依赖分析"""
    
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.symbols: Dict[str, Symbol] = {}
        self.file_symbols: Dict[str, List[str]] = defaultdict(list)
        self.imports: Dict[str, Set[str]] = defaultdict(set)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.file_hashes: Dict[str, str] = {}
    
    def index_project(self, extensions: List[str] = None) -> Dict[str, Any]:
        """索引整个项目"""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]
        
        stats = {"files": 0, "symbols": 0, "errors": 0}
        
        for ext in extensions:
            for filepath in self.workspace.rglob(f"*{ext}"):
                # 跳过常见忽略目录
                if any(p in str(filepath) for p in [".git", "__pycache__", "node_modules", ".venv", "venv"]):
                    continue
                
                try:
                    self._index_file(filepath)
                    stats["files"] += 1
                except Exception as e:
                    logger.warning(f"索引失败 {filepath}: {e}")
                    stats["errors"] += 1
        
        stats["symbols"] = len(self.symbols)
        logger.info(f"索引完成: {stats['files']} 文件, {stats['symbols']} 符号")
        return stats
    
    def _index_file(self, filepath: Path):
        """索引单个文件"""
        content = filepath.read_text(encoding="utf-8", errors="replace")
        file_hash = hashlib.md5(content.encode()).hexdigest()
        
        rel_path = str(filepath.relative_to(self.workspace))
        
        # 检查是否需要重新索引
        if rel_path in self.file_hashes and self.file_hashes[rel_path] == file_hash:
            return
        
        self.file_hashes[rel_path] = file_hash
        
        # 清除旧符号
        if rel_path in self.file_symbols:
            for sym_name in self.file_symbols[rel_path]:
                self.symbols.pop(sym_name, None)
            self.file_symbols[rel_path] = []
        
        # Python文件
        if filepath.suffix == ".py":
            self._index_python(filepath, content, rel_path)
        # JavaScript/TypeScript
        elif filepath.suffix in [".js", ".ts", ".jsx", ".tsx"]:
            self._index_javascript(filepath, content, rel_path)
    
    def _index_python(self, filepath: Path, content: str, rel_path: str):
        """索引Python文件"""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"语法错误 {filepath}:{e.lineno}: {e.msg}")
            return
        
        for node in ast.walk(tree):
            symbol = None
            
            if isinstance(node, ast.FunctionDef):
                args = ", ".join(a.arg for a in node.args.args)
                symbol = Symbol(
                    name=node.name,
                    kind="function",
                    file=rel_path,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    signature=f"def {node.name}({args})",
                    docstring=ast.get_docstring(node) or ""
                )
            
            elif isinstance(node, ast.AsyncFunctionDef):
                args = ", ".join(a.arg for a in node.args.args)
                symbol = Symbol(
                    name=node.name,
                    kind="async_function",
                    file=rel_path,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    signature=f"async def {node.name}({args})",
                    docstring=ast.get_docstring(node) or ""
                )
            
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(
                    b.id if isinstance(b, ast.Name) else str(b) 
                    for b in node.bases
                )
                symbol = Symbol(
                    name=node.name,
                    kind="class",
                    file=rel_path,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    signature=f"class {node.name}({bases})" if bases else f"class {node.name}",
                    docstring=ast.get_docstring(node) or ""
                )
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[rel_path].add(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports[rel_path].add(node.module)
            
            if symbol:
                key = f"{rel_path}:{symbol.name}"
                self.symbols[key] = symbol
                self.file_symbols[rel_path].append(key)
    
    def _index_javascript(self, filepath: Path, content: str, rel_path: str):
        """索引JavaScript/TypeScript文件（简化版）"""
        # 函数定义
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, content):
            line = content[:match.start()].count('\n') + 1
            symbol = Symbol(
                name=match.group(1),
                kind="function",
                file=rel_path,
                line=line,
                signature=f"function {match.group(1)}({match.group(2)})"
            )
            key = f"{rel_path}:{symbol.name}"
            self.symbols[key] = symbol
            self.file_symbols[rel_path].append(key)
        
        # 箭头函数
        arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
        for match in re.finditer(arrow_pattern, content):
            line = content[:match.start()].count('\n') + 1
            symbol = Symbol(
                name=match.group(1),
                kind="arrow_function",
                file=rel_path,
                line=line,
                signature=f"const {match.group(1)} = () =>"
            )
            key = f"{rel_path}:{symbol.name}"
            self.symbols[key] = symbol
            self.file_symbols[rel_path].append(key)
        
        # 类定义
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            line = content[:match.start()].count('\n') + 1
            extends = f" extends {match.group(2)}" if match.group(2) else ""
            symbol = Symbol(
                name=match.group(1),
                kind="class",
                file=rel_path,
                line=line,
                signature=f"class {match.group(1)}{extends}"
            )
            key = f"{rel_path}:{symbol.name}"
            self.symbols[key] = symbol
            self.file_symbols[rel_path].append(key)
    
    def search_symbols(self, query: str, kind: str = None) -> List[Symbol]:
        """搜索符号"""
        results = []
        query_lower = query.lower()
        
        for key, symbol in self.symbols.items():
            if kind and symbol.kind != kind:
                continue
            
            if query_lower in symbol.name.lower():
                results.append(symbol)
        
        return sorted(results, key=lambda s: (
            0 if s.name.lower() == query_lower else 1,
            len(s.name)
        ))
    
    def get_file_symbols(self, filepath: str) -> List[Symbol]:
        """获取文件的所有符号"""
        return [self.symbols[key] for key in self.file_symbols.get(filepath, [])]
    
    def get_dependencies(self, filepath: str) -> Set[str]:
        """获取文件的依赖"""
        return self.imports.get(filepath, set())
    
    def find_references(self, symbol_name: str) -> List[Tuple[str, int]]:
        """查找符号引用"""
        references = []
        pattern = re.compile(r'\b' + re.escape(symbol_name) + r'\b')
        
        for filepath in self.file_symbols.keys():
            try:
                content = (self.workspace / filepath).read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split('\n'), 1):
                    if pattern.search(line):
                        references.append((filepath, i))
            except Exception:
                pass
        
        return references


# ==================== DiffEngine ====================

class DiffEngine:
    """差异引擎 - 精确代码编辑"""
    
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.edit_history: List[EditOperation] = []
        self.backup_dir = workspace / ".code_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_edit(self, filepath: str, old_text: str, new_text: str, 
                    description: str = "") -> Optional[EditOperation]:
        """创建编辑操作"""
        full_path = self.workspace / filepath
        if not full_path.exists():
            return None
        
        content = full_path.read_text(encoding="utf-8")
        
        if old_text not in content:
            logger.warning(f"未找到要替换的内容: {old_text[:50]}...")
            return None
        
        # 计算行号
        before_match = content.split(old_text)[0]
        start_line = before_match.count('\n') + 1
        end_line = start_line + old_text.count('\n')
        
        return EditOperation(
            filepath=filepath,
            operation="replace",
            start_line=start_line,
            end_line=end_line,
            old_content=old_text,
            new_content=new_text,
            description=description
        )
    
    def apply_edit(self, edit: EditOperation) -> bool:
        """应用编辑"""
        full_path = self.workspace / edit.filepath
        
        try:
            content = full_path.read_text(encoding="utf-8")
            
            # 备份
            self._backup_file(edit.filepath, content)
            
            # 应用编辑
            if edit.operation == "replace":
                if edit.old_content not in content:
                    logger.error(f"内容不匹配，无法应用编辑")
                    return False
                new_content = content.replace(edit.old_content, edit.new_content, 1)
            
            elif edit.operation == "insert":
                lines = content.split('\n')
                lines.insert(edit.start_line - 1, edit.new_content)
                new_content = '\n'.join(lines)
            
            elif edit.operation == "delete":
                lines = content.split('\n')
                del lines[edit.start_line - 1:edit.end_line]
                new_content = '\n'.join(lines)
            
            else:
                logger.error(f"未知操作类型: {edit.operation}")
                return False
            
            full_path.write_text(new_content, encoding="utf-8")
            self.edit_history.append(edit)
            logger.info(f"✓ 编辑已应用: {edit.filepath}:{edit.start_line}-{edit.end_line}")
            return True
            
        except Exception as e:
            logger.error(f"应用编辑失败: {e}")
            return False
    
    def apply_edits(self, edits: List[EditOperation]) -> int:
        """批量应用编辑"""
        success_count = 0
        for edit in edits:
            if self.apply_edit(edit):
                success_count += 1
        return success_count
    
    def _backup_file(self, filepath: str, content: str):
        """备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.replace('/', '_')}_{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        backup_path.write_text(content, encoding="utf-8")
    
    def generate_diff(self, filepath: str, old_content: str, new_content: str) -> str:
        """生成diff"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}"
        )
        return ''.join(diff)
    
    def rollback_last(self) -> bool:
        """回滚最后一次编辑"""
        if not self.edit_history:
            logger.warning("没有可回滚的编辑")
            return False
        
        edit = self.edit_history.pop()
        full_path = self.workspace / edit.filepath
        
        try:
            content = full_path.read_text(encoding="utf-8")
            new_content = content.replace(edit.new_content, edit.old_content, 1)
            full_path.write_text(new_content, encoding="utf-8")
            logger.info(f"✓ 已回滚: {edit.filepath}")
            return True
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False


# ==================== ExecutionLoop ====================

class ExecutionLoop:
    """执行循环 - 编译/测试/自动重试"""
    
    def __init__(self, workspace: Path, diff_engine: DiffEngine = None):
        self.workspace = Path(workspace)
        self.diff_engine = diff_engine or DiffEngine(workspace)
        self.max_retries = 3
        self.timeout = 60
        self.history: List[ExecutionResult] = []
    
    def execute(self, command: Union[str, List[str]], cwd: str = None,
                env: Dict[str, str] = None) -> ExecutionResult:
        """执行命令"""
        import time
        start_time = time.time()
        
        work_dir = Path(cwd) if cwd else self.workspace
        
        try:
            exec_env = os.environ.copy()
            exec_env["PAGER"] = "cat"
            if env:
                exec_env.update(env)
            
            result = subprocess.run(
                command,
                shell=isinstance(command, str),
                capture_output=True,
                text=True,
                cwd=str(work_dir),
                env=exec_env,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            exec_result = ExecutionResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            exec_result = ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"命令超时 (>{self.timeout}s)",
                duration=time.time() - start_time
            )
        except Exception as e:
            exec_result = ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time
            )
        
        exec_result.parse_errors()
        self.history.append(exec_result)
        return exec_result
    
    def run_with_fix(self, command: str, auto_fixer: 'AutoFixer' = None,
                     cwd: str = None) -> ExecutionResult:
        """执行命令并自动修复错误"""
        for attempt in range(self.max_retries + 1):
            logger.info(f"执行 [{attempt + 1}/{self.max_retries + 1}]: {command[:50]}...")
            
            result = self.execute(command, cwd)
            
            if result.success:
                logger.info("✓ 执行成功")
                return result
            
            logger.warning(f"✗ 执行失败 (退出码: {result.return_code})")
            
            if result.errors:
                for err in result.errors[:3]:
                    logger.warning(f"  {err.get('file')}:{err.get('line')} - {err.get('message', '')[:60]}")
            
            # 尝试自动修复
            if auto_fixer and attempt < self.max_retries:
                logger.info("尝试自动修复...")
                fixes = auto_fixer.analyze_errors(result.errors)
                
                if fixes:
                    logger.info(f"应用 {len(fixes)} 个修复...")
                    self.diff_engine.apply_edits(fixes)
                else:
                    logger.warning("无法生成修复方案")
                    break
        
        return result
    
    def run_tests(self, test_command: str = None) -> ExecutionResult:
        """运行测试"""
        if test_command is None:
            # 自动检测测试命令
            if (self.workspace / "pytest.ini").exists() or (self.workspace / "tests").exists():
                test_command = "python -m pytest -v"
            elif (self.workspace / "package.json").exists():
                test_command = "npm test"
            else:
                test_command = "python -m pytest"
        
        logger.info(f"运行测试: {test_command}")
        return self.execute(test_command)
    
    def run_linter(self, filepath: str) -> ExecutionResult:
        """运行代码检查"""
        ext = Path(filepath).suffix.lower()
        
        if ext == ".py":
            cmd = f"python -m pylint --output-format=text {filepath}"
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            cmd = f"npx eslint {filepath}"
        else:
            return ExecutionResult(True, 0, "", "", 0)
        
        return self.execute(cmd)


# ==================== AutoFixer ====================

class AutoFixer:
    """自动修复器 - 根据错误生成修复方案"""
    
    def __init__(self, indexer: ProjectIndexer, workspace: Path):
        self.indexer = indexer
        self.workspace = Path(workspace)
        self.fix_patterns = self._init_patterns()
    
    def _init_patterns(self) -> List[Dict[str, Any]]:
        """初始化修复模式"""
        return [
            {
                "pattern": r"name '(\w+)' is not defined",
                "type": "NameError",
                "handler": self._fix_undefined_name
            },
            {
                "pattern": r"expected '([^']+)'",
                "type": "SyntaxError",
                "handler": self._fix_missing_syntax
            },
            {
                "pattern": r"IndentationError",
                "type": "IndentationError",
                "handler": self._fix_indentation
            },
            {
                "pattern": r"No module named '(\w+)'",
                "type": "ModuleNotFoundError",
                "handler": self._fix_missing_module
            },
            {
                "pattern": r"unexpected indent",
                "type": "IndentationError",
                "handler": self._fix_indentation
            },
        ]
    
    def analyze_errors(self, errors: List[Dict[str, Any]]) -> List[EditOperation]:
        """分析错误并生成修复"""
        fixes = []
        
        for error in errors:
            fix = self._generate_fix(error)
            if fix:
                fixes.append(fix)
        
        return fixes
    
    def _generate_fix(self, error: Dict[str, Any]) -> Optional[EditOperation]:
        """为单个错误生成修复"""
        error_type = error.get("type", "")
        message = error.get("message", "")
        
        for pattern_info in self.fix_patterns:
            if pattern_info["type"] in error_type:
                match = re.search(pattern_info["pattern"], message)
                if match:
                    return pattern_info["handler"](error, match)
        
        return None
    
    def _fix_undefined_name(self, error: Dict, match: re.Match) -> Optional[EditOperation]:
        """修复未定义的名称"""
        name = match.group(1)
        filepath = error.get("file", "")
        
        if not filepath or not (self.workspace / filepath).exists():
            return None
        
        # 搜索项目中是否有此符号
        symbols = self.indexer.search_symbols(name)
        
        if symbols:
            # 找到符号，添加import
            symbol = symbols[0]
            module = symbol.file.replace("/", ".").replace(".py", "")
            
            import_line = f"from {module} import {name}\n"
            
            content = (self.workspace / filepath).read_text(encoding="utf-8")
            lines = content.split('\n')
            
            # 找到合适的插入位置（在其他import之后）
            insert_line = 1
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_line = i + 2
            
            return EditOperation(
                filepath=filepath,
                operation="insert",
                start_line=insert_line,
                end_line=insert_line,
                new_content=import_line,
                description=f"添加缺失的import: {name}"
            )
        
        return None
    
    def _fix_missing_syntax(self, error: Dict, match: re.Match) -> Optional[EditOperation]:
        """修复缺失的语法元素"""
        missing = match.group(1)
        filepath = error.get("file", "")
        line_num = error.get("line", 0)
        
        if not filepath or not line_num:
            return None
        
        try:
            content = (self.workspace / filepath).read_text(encoding="utf-8")
            lines = content.split('\n')
            
            if line_num <= len(lines):
                line_content = lines[line_num - 1]
                
                # 缺少冒号
                if missing == ":":
                    keywords = ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 'try', 'except', 'finally', 'with']
                    for kw in keywords:
                        if line_content.strip().startswith(kw) and not line_content.rstrip().endswith(':'):
                            return EditOperation(
                                filepath=filepath,
                                operation="replace",
                                start_line=line_num,
                                end_line=line_num,
                                old_content=line_content,
                                new_content=line_content.rstrip() + ':',
                                description="添加缺失的冒号"
                            )
                
                # 缺少括号
                elif missing == ")":
                    open_count = line_content.count('(') - line_content.count(')')
                    if open_count > 0:
                        return EditOperation(
                            filepath=filepath,
                            operation="replace",
                            start_line=line_num,
                            end_line=line_num,
                            old_content=line_content,
                            new_content=line_content.rstrip() + ')' * open_count,
                            description="添加缺失的右括号"
                        )
        except Exception:
            pass
        
        return None
    
    def _fix_indentation(self, error: Dict, match: re.Match) -> Optional[EditOperation]:
        """修复缩进问题"""
        filepath = error.get("file", "")
        line_num = error.get("line", 0)
        
        if not filepath or not line_num:
            return None
        
        try:
            content = (self.workspace / filepath).read_text(encoding="utf-8")
            lines = content.split('\n')
            
            if line_num <= len(lines):
                current_line = lines[line_num - 1]
                
                # 获取上一行的缩进
                if line_num > 1:
                    prev_line = lines[line_num - 2]
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    
                    # 如果上一行以冒号结尾，增加缩进
                    if prev_line.rstrip().endswith(':'):
                        expected_indent = prev_indent + 4
                    else:
                        expected_indent = prev_indent
                    
                    new_line = ' ' * expected_indent + current_line.lstrip()
                    
                    return EditOperation(
                        filepath=filepath,
                        operation="replace",
                        start_line=line_num,
                        end_line=line_num,
                        old_content=current_line,
                        new_content=new_line,
                        description="修复缩进"
                    )
        except Exception:
            pass
        
        return None
    
    def _fix_missing_module(self, error: Dict, match: re.Match) -> Optional[EditOperation]:
        """修复缺失的模块（生成安装建议）"""
        module_name = match.group(1)
        
        # 常见模块映射
        pip_packages = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "sklearn": "scikit-learn",
            "yaml": "PyYAML",
        }
        
        package = pip_packages.get(module_name, module_name)
        logger.info(f"💡 建议安装: pip install {package}")
        
        return None  # 不自动安装，只提供建议


# ==================== CodeEnhancer 主类 ====================

class CodeEnhancer:
    """代码增强器 - 统一接口"""
    
    def __init__(self, workspace: str = None):
        self.workspace = Path(workspace) if workspace else PROJECT_ROOT
        self.indexer = ProjectIndexer(self.workspace)
        self.diff_engine = DiffEngine(self.workspace)
        self.executor = ExecutionLoop(self.workspace, self.diff_engine)
        self.fixer = AutoFixer(self.indexer, self.workspace)
        
        # 初始化索引
        self.indexer.index_project()
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """分析单个文件"""
        full_path = self.workspace / filepath
        if not full_path.exists():
            return {"error": f"文件不存在: {filepath}"}
        
        # 重新索引该文件
        self.indexer._index_file(full_path)
        
        symbols = self.indexer.get_file_symbols(filepath)
        dependencies = self.indexer.get_dependencies(filepath)
        
        return {
            "filepath": filepath,
            "symbols": [s.to_dict() for s in symbols],
            "dependencies": list(dependencies),
            "symbol_count": len(symbols)
        }
    
    def run_and_fix(self, command: str) -> Dict[str, Any]:
        """执行命令并自动修复"""
        result = self.executor.run_with_fix(command, self.fixer)
        
        return {
            "success": result.success,
            "return_code": result.return_code,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "duration": result.duration,
            "errors": result.errors,
            "attempts": len(self.executor.history)
        }
    
    def edit_file(self, filepath: str, old_text: str, new_text: str,
                  description: str = "") -> Dict[str, Any]:
        """编辑文件"""
        edit = self.diff_engine.create_edit(filepath, old_text, new_text, description)
        
        if not edit:
            return {"success": False, "error": "无法创建编辑操作"}
        
        success = self.diff_engine.apply_edit(edit)
        
        return {
            "success": success,
            "edit": edit.to_dict(),
            "diff": self.diff_engine.generate_diff(filepath, old_text, new_text)
        }
    
    def search(self, query: str, kind: str = None) -> List[Dict[str, Any]]:
        """搜索符号"""
        symbols = self.indexer.search_symbols(query, kind)
        return [s.to_dict() for s in symbols[:20]]
    
    def find_references(self, symbol_name: str) -> List[Tuple[str, int]]:
        """查找引用"""
        return self.indexer.find_references(symbol_name)
    
    def run_tests(self) -> Dict[str, Any]:
        """运行测试"""
        result = self.executor.run_tests()
        return {
            "success": result.success,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000],
            "duration": result.duration
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "workspace": str(self.workspace),
            "indexed_files": len(self.indexer.file_symbols),
            "total_symbols": len(self.indexer.symbols),
            "edit_history": len(self.diff_engine.edit_history),
            "execution_history": len(self.executor.history)
        }


# ==================== CLI ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="代码增强系统")
    parser.add_argument("--workspace", "-w", default=".", help="工作区路径")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # index
    index_parser = subparsers.add_parser("index", help="索引项目")
    
    # search
    search_parser = subparsers.add_parser("search", help="搜索符号")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--kind", help="符号类型")
    
    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="分析文件")
    analyze_parser.add_argument("filepath", help="文件路径")
    
    # run
    run_parser = subparsers.add_parser("run", help="执行命令")
    run_parser.add_argument("cmd", help="命令")
    run_parser.add_argument("--fix", action="store_true", help="自动修复")
    
    # test
    test_parser = subparsers.add_parser("test", help="运行测试")
    
    # stats
    stats_parser = subparsers.add_parser("stats", help="显示统计")
    
    args = parser.parse_args()
    
    enhancer = CodeEnhancer(args.workspace)
    
    if args.command == "index":
        stats = enhancer.indexer.index_project()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "search":
        results = enhancer.search(args.query, args.kind)
        for r in results:
            print(f"{r['file']}:{r['line']} - {r['kind']} {r['name']}")
    
    elif args.command == "analyze":
        result = enhancer.analyze_file(args.filepath)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "run":
        if args.fix:
            result = enhancer.run_and_fix(args.cmd)
        else:
            result = enhancer.executor.execute(args.cmd)
            result = {"success": result.success, "stdout": result.stdout, "stderr": result.stderr}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "test":
        result = enhancer.run_tests()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stats":
        stats = enhancer.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
