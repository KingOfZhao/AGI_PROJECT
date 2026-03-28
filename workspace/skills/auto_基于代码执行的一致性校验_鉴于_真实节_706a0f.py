"""
模块名称: auto_hypothesis_validator.py
描述: 这是一个用于AGI系统的高级技能模块，旨在解决自然语言假设的可证伪性问题。
      该模块实现了将自然语言描述的假设转化为可执行代码，并在沙箱环境中
      运行以验证其真伪的自动化流程。
      
      核心功能：
      1. 将结构化的假设对象转化为可执行脚本。
      2. 使用Subprocess沙箱机制执行代码并捕获结果。
      3. 基于执行结果和退出状态码判断假设的一致性与真伪。

作者: AGI System Core Team
版本: 1.0.0
日期: 2023-10-27
"""

import subprocess
import logging
import tempfile
import os
import json
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class HypothesisInput:
    """
    假设输入的数据结构。
    
    Attributes:
        hypothesis_id (str): 假设的唯一标识符。
        description (str): 自然语言描述的假设内容。
        executable_logic (str): 预设的可执行逻辑（Python代码字符串或Shell命令）。
        expected_output (Optional[str]): 期望的输出匹配模式（支持简单的字符串包含检查）。
        timeout (int): 执行超时时间（秒）。
    """
    hypothesis_id: str
    description: str
    executable_logic: str
    expected_output: Optional[str] = None
    timeout: int = 10

@dataclass
class ValidationResult:
    """
    验证结果的数据结构。
    
    Attributes:
        is_falsifiable (bool): 是否通过了可证伪性检查（即代码是否成功运行并符合预期）。
        is_verified (bool): 假设是否被验证为真。
        execution_stdout (str): 标准输出内容。
        execution_stderr (str): 标准错误内容。
        return_code (int): 进程返回码。
        analysis (str): 结果分析说明。
    """
    is_falsifiable: bool
    is_verified: bool
    execution_stdout: str
    execution_stderr: str
    return_code: int
    analysis: str

class HypothesisValidationError(Exception):
    """自定义异常：假设验证过程中发生的错误。"""
    pass

def _sanitize_environment() -> Dict[str, str]:
    """
    [辅助函数] 净化执行环境变量。
    
    移除可能影响沙箱安全性的环境变量，并设置必要的基础路径。
    
    Returns:
        Dict[str, str]: 安全的环境变量字典。
    """
    safe_env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "HOME": "/tmp/agi_sandbox",
        "PYTHONPATH": ""
    }
    logger.debug("Environment sanitized for sandbox execution.")
    return safe_env

def generate_executable_script(hypothesis: HypothesisInput) -> Tuple[str, str]:
    """
    [核心函数 1] 生成可执行脚本文件。
    
    将假设中的逻辑代码写入临时文件。这里模拟了从自然语言到代码的转化结果。
    在真实的AGI场景中，这里会调用LLM生成代码，当前版本直接使用输入的逻辑。
    
    Args:
        hypothesis (HypothesisInput): 包含逻辑代码的假设对象。
        
    Returns:
        Tuple[str, str]: (脚本文件路径, 脚本类型 python/shell)
        
    Raises:
        HypothesisValidationError: 如果代码生成或文件写入失败。
    """
    try:
        # 数据验证：检查逻辑代码是否为空
        if not hypothesis.executable_logic.strip():
            raise HypothesisValidationError("Executable logic cannot be empty.")
        
        # 创建临时目录作为沙箱
        sandbox_dir = Path(tempfile.mkdtemp(prefix="agi_sandbox_"))
        logger.info(f"Sandbox directory created at: {sandbox_dir}")
        
        # 判断代码类型并写入文件
        # 这里做了一个简单的启发式判断，实际应用中需更复杂的解析
        logic = hypothesis.executable_logic
        if "import " in logic or "def " in logic or "print(" in logic:
            script_path = sandbox_dir / "validate_script.py"
            script_type = "python"
            # 添加头部使其可运行
            content = f"#!/usr/bin/env python3\n# Auto-generated for: {hypothesis.hypothesis_id}\n\n{logic}"
        else:
            script_path = sandbox_dir / "validate_script.sh"
            script_type = "shell"
            content = f"#!/bin/bash\n# Auto-generated for: {hypothesis.hypothesis_id}\n\n{logic}"
            
        script_path.write_text(content, encoding='utf-8')
        script_path.chmod(0o755)  # 赋予执行权限
        
        logger.info(f"Script generated successfully: {script_path}")
        return str(script_path), script_type
        
    except IOError as e:
        logger.error(f"Failed to write script file: {e}")
        raise HypothesisValidationError(f"File system error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during script generation: {e}")
        raise

def execute_and_verify(
    script_path: str, 
    script_type: str, 
    hypothesis: HypothesisInput
) -> ValidationResult:
    """
    [核心函数 2] 执行脚本并验证结果。
    
    在隔离的子进程中执行生成的脚本，捕获输出，并根据结果验证假设。
    
    Args:
        script_path (str): 可执行脚本的路径。
        script_type (str): 脚本类型。
        hypothesis (HypothesisInput): 原始假设对象，包含期望输出等配置。
        
    Returns:
        ValidationResult: 包含详细验证结果的对象。
    """
    cmd = []
    if script_type == "python":
        cmd = ["python3", script_path]
    else:
        cmd = [script_path]
        
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    stdout_data, stderr_data, return_code = "", "", -1
    
    try:
        # 获取净化的环境
        env = _sanitize_environment()
        
        # 启动子进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=os.path.dirname(script_path)
        )
        
        # 带超时的等待
        stdout_data, stderr_data = process.communicate(timeout=hypothesis.timeout)
        return_code = process.returncode
        
        logger.info(f"Execution finished with return code: {return_code}")
        
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_data, stderr_data = process.communicate()
        logger.warning(f"Execution timed out after {hypothesis.timeout} seconds.")
        return ValidationResult(
            is_falsifiable=False,
            is_verified=False,
            execution_stdout=stdout_data,
            execution_stderr=f"Timeout expired ({hypothesis.timeout}s)",
            return_code=-1,
            analysis="Execution failed due to timeout."
        )
    except Exception as e:
        logger.error(f"Execution critical failure: {e}")
        return ValidationResult(
            is_falsifiable=False,
            is_verified=False,
            execution_stdout="",
            execution_stderr=str(e),
            return_code=-1,
            analysis="Failed to start subprocess."
        )

    # 结果分析逻辑
    is_verified = False
    is_falsifiable = (return_code == 0) # 能够成功运行即具备可证伪性基础
    
    if hypothesis.expected_output:
        # 如果定义了期望输出，则进行匹配
        if hypothesis.expected_output in stdout_data:
            is_verified = True
            analysis = "Output matched expected pattern."
        else:
            is_verified = False
            analysis = f"Output mismatch. Expected substring: '{hypothesis.expected_output}'"
    else:
        # 如果没有定义期望输出，通常认为只要代码跑通(Exit 0)即为验证通过
        # 或者根据业务逻辑解析stdout中的JSON断言
        if return_code == 0:
            is_verified = True
            analysis = "Execution successful (Exit 0)."
        else:
            is_verified = False
            analysis = "Execution returned non-zero exit code."

    return ValidationResult(
        is_falsifiable=is_falsifiable,
        is_verified=is_verified,
        execution_stdout=stdout_data.strip(),
        execution_stderr=stderr_data.strip(),
        return_code=return_code,
        analysis=analysis
    )

def validate_hypothesis_entry(hypothesis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    主入口函数：验证假设的完整流程。
    
    接收原始字典数据，进行解析、生成脚本、执行并返回结构化结果。
    
    Args:
        hypothesis_data (Dict[str, Any]): 原始输入数据。
        
    Returns:
        Dict[str, Any]: 包含验证结果的字典，适合API返回。
        
    Example Input:
    {
        "hypothesis_id": "test_706a0f",
        "description": "Check if 10 is greater than 5",
        "executable_logic": "print('10 > 5: True')",
        "expected_output": "True"
    }
    """
    try:
        # 1. 数据验证与解析
        logger.info(f"Starting validation for node: {hypothesis_data.get('hypothesis_id')}")
        validated_input = HypothesisInput(**hypothesis_data)
        
        # 2. 生成可执行脚本
        script_path, script_type = generate_executable_script(validated_input)
        
        # 3. 执行与验证
        result = execute_and_verify(script_path, script_type, validated_input)
        
        # 4. 清理临时文件 (简单实现，生产环境建议用finally块)
        if os.path.exists(script_path):
            os.remove(script_path)
            # 尝试删除父目录（如果为空）
            try:
                os.rmdir(os.path.dirname(script_path))
            except OSError:
                pass
                
        return result.__dict__
        
    except TypeError as e:
        logger.error(f"Input data validation failed: {e}")
        return {"error": f"Invalid input data format: {str(e)}", "is_verified": False}
    except HypothesisValidationError as e:
        logger.error(f"Validation process failed: {e}")
        return {"error": str(e), "is_verified": False}
    except Exception as e:
        logger.critical(f"Unhandled exception in validation entry: {e}")
        return {"error": "Internal System Error", "is_verified": False}

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例 1: 验证一个简单的数学逻辑假设
    sample_hypothesis_1 = {
        "hypothesis_id": "math_check_001",
        "description": "Verify that Python can correctly sum integers.",
        "executable_logic": """
x = 10
y = 20
assert x + y == 30
print("Result is correct")
""",
        "expected_output": "Result is correct",
        "timeout": 5
    }
    
    print("--- Running Sample 1 ---")
    res1 = validate_hypothesis_entry(sample_hypothesis_1)
    print(json.dumps(res1, indent=2))
    
    # 示例 2: 验证一个预期会失败的假设
    sample_hypothesis_2 = {
        "hypothesis_id": "file_check_002",
        "description": "Check if a non-existent file exists.",
        "executable_logic": "import os; os.path.exists('/non/existent/path/that/should/fail')",
        "expected_output": "True", # 逻辑上这会输出 False 或报错，所以验证会失败
        "timeout": 5
    }
    
    print("\n--- Running Sample 2 ---")
    res2 = validate_hypothesis_entry(sample_hypothesis_2)
    print(json.dumps(res2, indent=2))