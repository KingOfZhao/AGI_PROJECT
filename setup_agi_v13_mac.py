#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac 上部署 AGI v13.2 Cognitive Lattice 的前置条件安装脚本
运行方式：
    python3 setup_agi_v13_mac.py
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# ======================
# 颜色输出辅助函数
# ======================
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(msg):
    print(f"\n{Colors.OKCYAN}════ {msg} ════{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def run_cmd(cmd, cwd=None, check=True, capture_output=False):
    """执行 shell 命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, cwd=cwd,
            text=True, capture_output=capture_output
        )
        if capture_output:
            return result.stdout.strip()
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"命令执行失败：{cmd}")
        print_error(e.stderr if e.stderr else "无错误输出")
        sys.exit(1)

# ======================
# 主流程
# ======================

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════╗")
    print("║   Mac 上部署 AGI v13.2 Cognitive Lattice 前置脚本   ║")
    print("╚════════════════════════════════════════════════════╝")
    print(Colors.ENDC)

    home = Path.home()
    project_dir = Path.cwd()  # 当前目录即项目目录
    venv_dir = project_dir / "venv"

    # 1. 检查并安装 Homebrew
    print_step("1. 检查 Homebrew")
    if shutil.which("brew") is None:
        print("未找到 Homebrew，正在安装...")
        run_cmd('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        print_success("Homebrew 安装完成")
    else:
        print_success("Homebrew 已安装")

    # 2. 安装 Python（推荐 3.11 或 3.12）
    print_step("2. 安装/升级 Python 3.11 或 3.12")
    run_cmd("brew install python@3.12", check=False)  # 如果已安装会跳过
    python_bin = run_cmd("brew --prefix python@3.12", capture_output=True) + "/bin/python3.12"
    print_success(f"使用 Python: {python_bin}")

    # 3. 创建虚拟环境
    print_step("3. 创建虚拟环境")
    if venv_dir.exists():
        print_warning("虚拟环境已存在，跳过创建")
    else:
        run_cmd(f"{python_bin} -m venv venv")
        print_success("虚拟环境创建完成：./venv")

    # 4. 激活虚拟环境并安装依赖
    print_step("4. 安装依赖包")
    pip_cmd = f"{venv_dir}/bin/pip install --upgrade pip"
    run_cmd(pip_cmd)

    requirements = [
        "openai",                       # 统一 LLM 调用（兼容 Ollama/OpenAI/xAI/智谱/DeepSeek）
        "sentence-transformers",        # 本地 embedding（云端后端需要，Ollama 可用内置替代）
        "numpy",
        "torch",                        # sentence-transformers 需要
    ]

    for pkg in requirements:
        run_cmd(f"{venv_dir}/bin/pip install {pkg}")

    print_success("所有依赖安装完成")

    # 5. 安装 Ollama（本地部署推荐）
    print_step("5. 安装 Ollama 本地 LLM 运行器")
    if shutil.which("ollama") is None:
        print("未找到 Ollama，正在安装...")
        run_cmd("brew install ollama", check=False)
    print_success("Ollama 已安装")
    print("\n推荐拉取模型（选一个）：")
    print("  32GB 内存推荐：  ollama pull qwen2.5-coder:14b")
    print("  内存紧张推荐：  ollama pull qwen2.5-coder:7b")
    print("  Embedding 模型： ollama pull nomic-embed-text")
    print("\n也可以用云端 API，修改 Config.ACTIVE_BACKEND 即可切换：")
    print("  可选: ollama / openai / xai / deepseek / zhipu")
    input("\n按回车继续...")

    # 6. 数据库目录准备
    print_step("6. 准备数据库目录")
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    print_success("数据库目录准备完成：./data/memory.db 将自动创建")

    # 7. 最终运行指令
    print_step("7. 完成！运行方式")
    print(f"{Colors.OKGREEN}运行命令：{Colors.ENDC}")
    print("\n本地部署（推荐，需先启动 Ollama）：")
    print("    ollama serve                           # 终端1: 启动 Ollama 服务")
    print(f"    {venv_dir}/bin/python agi_v13_cognitive_lattice.py  # 终端2: 运行")
    print("\n切换后端：修改 agi_v13_cognitive_lattice.py 中的 Config.ACTIVE_BACKEND")
    print("\n支持的交互命令：")
    print("  • 直接输入问题   → 双向拆解 + 碰撞")
    print("  • 具现化节点     → 录入人类真实实践节点")
    print("  • 生成实践清单   → 为节点生成验证步骤")
    print("  • 自成长         → 触发一次自动成长循环")
    print("  • 认知状态       → 查看网络统计")
    print("  • 搜索 <关键词>  → 语义搜索")
    print("  • exit           → 退出")

    print(f"\n{Colors.BOLD}{Colors.OKCYAN}祝你探索愉快！{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        print_error(f"安装过程中发生错误：{e}")
        sys.exit(1)