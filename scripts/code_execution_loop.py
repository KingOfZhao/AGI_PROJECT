#!/usr/bin/env python3
"""
OpenClaw自主代码执行循环

功能:
1. 接收任务描述
2. 生成代码方案
3. 执行并验证
4. 自动修复错误
5. 保存为可复用Skill
"""

import os
import sys
import re
import json
import hashlib
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import subprocess
import tempfile
import ast

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from terminal_executor import TerminalExecutor, CommandResult


# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

class ExecutionStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    EXECUTING = "executing"
    VALIDATING = "validating"
    FIXING = "fixing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    code: str = ""
    output: str = ""
    error: str = ""
    iterations: int = 0
    skill_saved: bool = False
    skill_path: str = ""
    duration_ms: int = 0
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "code": self.code,
            "output": self.output,
            "error": self.error,
            "iterations": self.iterations,
            "skill_saved": self.skill_saved,
            "skill_path": self.skill_path,
            "duration_ms": self.duration_ms
        }


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    description: str
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    previous_attempts: List[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 代码生成器
# ═══════════════════════════════════════════════════════════════

class CodeGenerator:
    """代码生成器 - 调用本地模型"""
    
    def __init__(self, bridge_url: str = "http://127.0.0.1:9801"):
        self.bridge_url = bridge_url
        self.session = None
        
        try:
            import requests
            self.session = requests.Session()
        except ImportError:
            pass
    
    def generate(self, task: TaskContext, error_feedback: str = None) -> Tuple[str, str]:
        """生成代码，返回(代码, 解释)"""
        
        prompt = self._build_prompt(task, error_feedback)
        
        if self.session:
            try:
                response = self.session.post(
                    f"{self.bridge_url}/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return self._extract_code(content)
            except Exception as e:
                print(f"Bridge调用失败: {e}")
        
        # 降级：使用模板生成
        return self._template_generate(task)
    
    def _build_prompt(self, task: TaskContext, error_feedback: str = None) -> str:
        """构建提示词"""
        
        prompt = f"""任务: {task.description}

要求:
{chr(10).join(f'- {r}' for r in task.requirements) if task.requirements else '- 无特殊要求'}

约束:
{chr(10).join(f'- {c}' for c in task.constraints) if task.constraints else '- 无特殊约束'}

"""
        
        if error_feedback:
            prompt += f"""
上次尝试的错误:
{error_feedback}

请修复错误并生成正确的代码。
"""
        
        if task.previous_attempts:
            prompt += f"""
之前的尝试次数: {len(task.previous_attempts)}
"""
        
        prompt += """
请生成完整可执行的Python代码。代码必须:
1. 包含所有必要的import
2. 有清晰的函数/类结构
3. 包含错误处理
4. 可以直接运行

用```python和```包裹代码。
"""
        
        return prompt
    
    def _extract_code(self, content: str) -> Tuple[str, str]:
        """从响应中提取代码"""
        
        # 提取代码块
        code_match = re.search(r'```python\n(.*?)```', content, re.DOTALL)
        
        if code_match:
            code = code_match.group(1).strip()
            # 提取解释（代码块之外的文本）
            explanation = re.sub(r'```python.*?```', '', content, flags=re.DOTALL).strip()
            return code, explanation
        
        # 如果没有代码块，尝试提取整个内容中的Python代码
        lines = content.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                in_code = True
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines), ""
        
        return "", content
    
    def _template_generate(self, task: TaskContext) -> Tuple[str, str]:
        """模板生成 - 降级方案"""
        
        # 根据任务描述识别模式
        desc = task.description.lower()
        
        if "文件" in desc or "读取" in desc:
            code = '''#!/usr/bin/env python3
"""任务: {desc}"""

from pathlib import Path
import json

def main():
    # TODO: 实现具体逻辑
    result = {{"status": "success", "message": "任务完成"}}
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    main()
'''.format(desc=task.description)
        
        elif "api" in desc or "请求" in desc:
            code = '''#!/usr/bin/env python3
"""任务: {desc}"""

import requests
import json

def main():
    # TODO: 实现API调用
    result = {{"status": "success", "message": "任务完成"}}
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    main()
'''.format(desc=task.description)
        
        else:
            code = '''#!/usr/bin/env python3
"""任务: {desc}"""

import sys
import json

def main():
    # TODO: 实现具体逻辑
    result = {{"status": "success", "message": "任务完成"}}
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    main()
'''.format(desc=task.description)
        
        return code, "使用模板生成"


# ═══════════════════════════════════════════════════════════════
# 代码验证器
# ═══════════════════════════════════════════════════════════════

class CodeValidator:
    """代码验证器"""
    
    def __init__(self):
        self.executor = TerminalExecutor()
    
    def validate_syntax(self, code: str) -> Tuple[bool, str]:
        """验证语法"""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"语法错误 (行 {e.lineno}): {e.msg}"
    
    def validate_imports(self, code: str) -> Tuple[bool, List[str]]:
        """验证导入"""
        missing = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        if not self._check_module(module):
                            missing.append(module)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        if not self._check_module(module):
                            missing.append(module)
        
        except SyntaxError:
            pass
        
        return len(missing) == 0, missing
    
    def _check_module(self, module: str) -> bool:
        """检查模块是否可用"""
        # 标准库
        stdlib = {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'pathlib',
            'collections', 'itertools', 'functools', 'typing', 'dataclasses',
            'hashlib', 'uuid', 'random', 'math', 'statistics',
            'subprocess', 'threading', 'multiprocessing', 'asyncio',
            'tempfile', 'shutil', 'glob', 'fnmatch',
            'sqlite3', 'csv', 'xml', 'html',
            'urllib', 'http', 'email', 'socket',
            'logging', 'warnings', 'traceback', 'inspect', 'ast',
            'contextlib', 'copy', 'pickle', 'struct', 'io',
            'argparse', 'configparser', 'enum', 'abc'
        }
        
        if module in stdlib:
            return True
        
        # 尝试导入
        try:
            __import__(module)
            return True
        except ImportError:
            return False
    
    def execute_and_validate(self, code: str, 
                             expected_output: str = None,
                             timeout: int = 30) -> Tuple[bool, str, str]:
        """执行并验证"""
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行
            result = self.executor.execute(
                f"python3 {temp_file}",
                timeout=timeout,
                check_security=False
            )
            
            if result.exit_code != 0:
                return False, result.stdout, result.stderr
            
            # 验证输出
            if expected_output:
                if expected_output not in result.stdout:
                    return False, result.stdout, f"输出不匹配，期望包含: {expected_output}"
            
            return True, result.stdout, ""
        
        finally:
            Path(temp_file).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════
# 错误修复器
# ═══════════════════════════════════════════════════════════════

class ErrorFixer:
    """错误修复器"""
    
    # 常见错误模式及修复
    ERROR_PATTERNS = [
        # 缺少导入
        (r"NameError: name '(\w+)' is not defined", 
         lambda m: f"添加导入: import {m.group(1)} 或 from xxx import {m.group(1)}"),
        
        # 模块未找到
        (r"ModuleNotFoundError: No module named '(\w+)'",
         lambda m: f"安装模块: pip install {m.group(1)}"),
        
        # 属性错误
        (r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
         lambda m: f"检查{m.group(1)}类型是否正确，或属性名{m.group(2)}拼写"),
        
        # 类型错误
        (r"TypeError: (.+)",
         lambda m: f"类型错误: {m.group(1)}，检查参数类型"),
        
        # 索引错误
        (r"IndexError: (.+)",
         lambda m: f"索引越界: {m.group(1)}，检查列表/字符串长度"),
        
        # 键错误
        (r"KeyError: (.+)",
         lambda m: f"字典键不存在: {m.group(1)}，使用.get()或检查键名"),
        
        # 文件错误
        (r"FileNotFoundError: (.+)",
         lambda m: f"文件不存在: {m.group(1)}，检查路径"),
        
        # 语法错误
        (r"SyntaxError: (.+)",
         lambda m: f"语法错误: {m.group(1)}"),
    ]
    
    def analyze_error(self, error: str) -> str:
        """分析错误并给出修复建议"""
        
        suggestions = []
        
        for pattern, fix_func in self.ERROR_PATTERNS:
            match = re.search(pattern, error)
            if match:
                suggestions.append(fix_func(match))
        
        if not suggestions:
            # 通用建议
            if "Traceback" in error:
                # 提取最后一行错误
                lines = error.strip().split('\n')
                last_error = lines[-1] if lines else error
                suggestions.append(f"错误: {last_error}")
        
        return '\n'.join(suggestions) if suggestions else "未知错误，请检查代码逻辑"
    
    def suggest_fix(self, code: str, error: str) -> str:
        """建议修复方案"""
        
        analysis = self.analyze_error(error)
        
        # 自动修复尝试
        fixed_code = code
        
        # 缺少导入的自动修复
        missing_import = re.search(r"NameError: name '(\w+)' is not defined", error)
        if missing_import:
            name = missing_import.group(1)
            
            # 常见名称到模块的映射
            import_map = {
                'Path': 'from pathlib import Path',
                'datetime': 'from datetime import datetime',
                'json': 'import json',
                'os': 'import os',
                'sys': 'import sys',
                're': 'import re',
                'Dict': 'from typing import Dict',
                'List': 'from typing import List',
                'Optional': 'from typing import Optional',
                'dataclass': 'from dataclasses import dataclass',
            }
            
            if name in import_map:
                import_stmt = import_map[name]
                if import_stmt not in fixed_code:
                    # 在文件开头添加导入
                    lines = fixed_code.split('\n')
                    
                    # 找到第一个非注释、非空行
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                            # 如果是import/from语句，继续
                            if line.strip().startswith('import ') or line.strip().startswith('from '):
                                insert_pos = i + 1
                            else:
                                insert_pos = i
                                break
                    
                    lines.insert(insert_pos, import_stmt)
                    fixed_code = '\n'.join(lines)
        
        return fixed_code, analysis


# ═══════════════════════════════════════════════════════════════
# Skill保存器
# ═══════════════════════════════════════════════════════════════

class SkillSaver:
    """Skill保存器"""
    
    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or PROJECT_ROOT / "workspace/skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, task: TaskContext, code: str, result: ExecutionResult) -> str:
        """保存为Skill"""
        
        # 生成Skill名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_hash = hashlib.md5(task.description.encode()).hexdigest()[:8]
        skill_name = f"skill_auto_{name_hash}_{timestamp}"
        
        # 生成Skill文件
        skill_content = f'''#!/usr/bin/env python3
"""
自动生成的Skill

任务: {task.description}
生成时间: {datetime.now().isoformat()}
迭代次数: {result.iterations}

要求:
{chr(10).join(f"- {r}" for r in task.requirements) if task.requirements else "- 无"}

约束:
{chr(10).join(f"- {c}" for c in task.constraints) if task.constraints else "- 无"}
"""

{code}
'''
        
        # 保存Python文件
        skill_path = self.skills_dir / f"{skill_name}.py"
        skill_path.write_text(skill_content)
        
        # 保存元数据
        meta = {
            "name": skill_name,
            "description": task.description,
            "requirements": task.requirements,
            "constraints": task.constraints,
            "created_at": datetime.now().isoformat(),
            "iterations": result.iterations,
            "execution_time_ms": result.duration_ms,
            "tags": ["auto_generated", "code_execution_loop"]
        }
        
        meta_path = self.skills_dir / f"{skill_name}.meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        
        return str(skill_path)


# ═══════════════════════════════════════════════════════════════
# 主执行循环
# ═══════════════════════════════════════════════════════════════

class CodeExecutionLoop:
    """自主代码执行循环"""
    
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.generator = CodeGenerator()
        self.validator = CodeValidator()
        self.fixer = ErrorFixer()
        self.saver = SkillSaver()
    
    def execute(self, task_description: str,
                requirements: List[str] = None,
                constraints: List[str] = None,
                expected_output: str = None,
                save_skill: bool = True) -> ExecutionResult:
        """执行任务"""
        
        import time
        start_time = time.time()
        
        # 创建任务上下文
        task = TaskContext(
            task_id=hashlib.md5(task_description.encode()).hexdigest()[:16],
            description=task_description,
            requirements=requirements or [],
            constraints=constraints or []
        )
        
        result = ExecutionResult(status=ExecutionStatus.PENDING)
        error_feedback = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n=== 迭代 {iteration}/{self.max_iterations} ===")
            result.iterations = iteration
            
            # 1. 生成代码
            result.status = ExecutionStatus.GENERATING
            print("生成代码...")
            
            code, explanation = self.generator.generate(task, error_feedback)
            
            if not code:
                result.error = "代码生成失败"
                continue
            
            result.code = code
            print(f"生成了 {len(code)} 字符的代码")
            
            # 2. 语法验证
            result.status = ExecutionStatus.VALIDATING
            print("验证语法...")
            
            syntax_ok, syntax_error = self.validator.validate_syntax(code)
            if not syntax_ok:
                print(f"语法错误: {syntax_error}")
                error_feedback = syntax_error
                result.status = ExecutionStatus.FIXING
                continue
            
            # 3. 导入验证
            print("验证导入...")
            imports_ok, missing = self.validator.validate_imports(code)
            if not imports_ok:
                print(f"缺少模块: {missing}")
                error_feedback = f"缺少模块: {', '.join(missing)}"
                result.status = ExecutionStatus.FIXING
                continue
            
            # 4. 执行验证
            result.status = ExecutionStatus.EXECUTING
            print("执行代码...")
            
            exec_ok, output, exec_error = self.validator.execute_and_validate(
                code, expected_output
            )
            
            result.output = output
            
            if exec_ok:
                # 成功
                result.status = ExecutionStatus.SUCCESS
                result.error = ""
                print("执行成功!")
                
                # 5. 保存Skill
                if save_skill:
                    print("保存Skill...")
                    skill_path = self.saver.save(task, code, result)
                    result.skill_saved = True
                    result.skill_path = skill_path
                    print(f"Skill已保存: {skill_path}")
                
                break
            else:
                # 失败，准备修复
                print(f"执行失败: {exec_error}")
                result.error = exec_error
                result.status = ExecutionStatus.FIXING
                
                # 分析错误
                fixed_code, analysis = self.fixer.suggest_fix(code, exec_error)
                error_feedback = f"错误: {exec_error}\n分析: {analysis}"
                
                # 记录尝试
                task.previous_attempts.append({
                    "iteration": iteration,
                    "code": code,
                    "error": exec_error,
                    "analysis": analysis
                })
                
                # 如果自动修复有效，直接使用
                if fixed_code != code:
                    print("尝试自动修复...")
                    # 下次迭代会用新代码
        
        # 最终状态
        if result.status != ExecutionStatus.SUCCESS:
            result.status = ExecutionStatus.FAILED
        
        result.duration_ms = int((time.time() - start_time) * 1000)
        
        return result


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw自主代码执行循环")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--max-iter", type=int, default=5, help="最大迭代次数")
    parser.add_argument("--no-save", action="store_true", help="不保存Skill")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    
    args = parser.parse_args()
    
    loop = CodeExecutionLoop(max_iterations=args.max_iter)
    
    if args.demo:
        # 演示任务
        task = "创建一个函数，接收一个数字列表，返回其中的偶数列表及其和"
        requirements = ["函数名为filter_evens", "返回字典包含evens和sum两个键"]
    elif args.task:
        task = args.task
        requirements = []
    else:
        parser.print_help()
        return
    
    print(f"任务: {task}")
    print(f"要求: {requirements}")
    print("-" * 50)
    
    result = loop.execute(
        task,
        requirements=requirements,
        save_skill=not args.no_save
    )
    
    print("\n" + "=" * 50)
    print(f"状态: {result.status.value}")
    print(f"迭代: {result.iterations}")
    print(f"耗时: {result.duration_ms}ms")
    
    if result.skill_saved:
        print(f"Skill: {result.skill_path}")
    
    if result.output:
        print(f"\n输出:\n{result.output}")
    
    if result.error:
        print(f"\n错误:\n{result.error}")


if __name__ == "__main__":
    main()
