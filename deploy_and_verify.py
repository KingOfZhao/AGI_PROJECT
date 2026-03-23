#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.2 Cognitive Lattice — 一键部署、运行、验证、修复脚本
运行方式：
    python3 deploy_and_verify.py

此脚本自动完成：
    1. 检查/安装 Ollama
    2. 拉取所需模型 (qwen2.5-coder:14b + nomic-embed-text)
    3. 启动 Ollama 服务
    4. 安装 Python 依赖
    5. 验证数据库初始化 + 种子节点 + 碰撞引擎
    6. 验证 LLM 调用 + Embedding 调用
    7. 自动修复常见问题
    8. 启动 AGI 主程序
"""

import os
import sys
import subprocess
import shutil
import time
import sqlite3
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_DIR / "venv"
PYTHON_BIN = VENV_DIR / "bin" / "python"
PIP_BIN = VENV_DIR / "bin" / "pip"
DB_PATH = PROJECT_DIR / "memory.db"
MAIN_SCRIPT = PROJECT_DIR / "agi_v13_cognitive_lattice.py"

# ==================== 颜色输出 ====================
class C:
    OK = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    INFO = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg):   print(f"{C.OK}✓ {msg}{C.END}")
def warn(msg): print(f"{C.WARN}⚠ {msg}{C.END}")
def fail(msg): print(f"{C.FAIL}✗ {msg}{C.END}")
def info(msg): print(f"{C.INFO}  {msg}{C.END}")
def step(msg): print(f"\n{C.BOLD}{C.INFO}{'='*50}{C.END}\n{C.BOLD}{C.INFO}  {msg}{C.END}\n{C.BOLD}{C.INFO}{'='*50}{C.END}")

def run(cmd, check=True, capture=False, timeout=None):
    """执行命令，返回 (成功, 输出)"""
    try:
        r = subprocess.run(
            cmd, shell=True, check=check, text=True,
            capture_output=capture, timeout=timeout,
            cwd=str(PROJECT_DIR)
        )
        return True, (r.stdout.strip() if capture else "")
    except subprocess.CalledProcessError as e:
        return False, (e.stderr or str(e))
    except subprocess.TimeoutExpired:
        return False, "命令超时"

def wait_for_url(url, timeout=15):
    """等待 URL 可访问"""
    import urllib.request
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except:
            time.sleep(1)
    return False


# ==================== 步骤1: 检查/安装 Ollama ====================
def step1_install_ollama():
    step("步骤1: 检查/安装 Ollama")

    if shutil.which("ollama"):
        success, ver = run("ollama --version", capture=True, check=False)
        ok(f"Ollama 已安装: {ver}")
        return True

    info("未找到 Ollama，正在通过 brew 安装...")
    success, out = run("brew install ollama", check=False)
    if success and shutil.which("ollama"):
        ok("Ollama 安装成功")
        return True

    # brew 不可用时尝试官方安装脚本
    info("尝试官方安装方式...")
    success, _ = run("curl -fsSL https://ollama.com/install.sh | sh", check=False)
    if shutil.which("ollama"):
        ok("Ollama 安装成功（官方脚本）")
        return True

    fail("Ollama 安装失败，请手动安装: https://ollama.com/download")
    return False


# ==================== 步骤2: 拉取模型 ====================
def step2_pull_models():
    step("步骤2: 拉取 Ollama 模型")

    models = [
        ("nomic-embed-text", "Embedding 模型 (~274MB)"),
        ("qwen2.5-coder:14b", "编码模型 14B (~9GB)"),
    ]

    # 检查已有模型
    success, out = run("ollama list", capture=True, check=False)
    existing = out if success else ""

    for model, desc in models:
        # 简单检查模型名是否在已有列表中
        model_base = model.split(":")[0]
        if model_base in existing and (model.split(":")[-1] if ":" in model else "") in existing:
            ok(f"{desc} 已存在: {model}")
            continue

        info(f"拉取 {desc}: {model} ...")
        success, out = run(f"ollama pull {model}", check=False, timeout=1200)
        if success:
            ok(f"{desc} 拉取成功")
        else:
            # 14B 太大时自动降级到 7B
            if "14b" in model:
                warn(f"14B 拉取失败，尝试降级到 7B...")
                success, _ = run("ollama pull qwen2.5-coder:7b", check=False, timeout=600)
                if success:
                    ok("7B 模型拉取成功，需修改 Config.ACTIVE_BACKEND = 'ollama_7b'")
                    fix_backend_to_7b()
                else:
                    fail(f"模型拉取失败: {model}")
                    return False
            else:
                fail(f"模型拉取失败: {model}")
                return False
    return True


def fix_backend_to_7b():
    """自动将配置切换到 7b"""
    try:
        content = MAIN_SCRIPT.read_text()
        content = content.replace(
            'ACTIVE_BACKEND = "ollama"',
            'ACTIVE_BACKEND = "ollama_7b"'
        )
        MAIN_SCRIPT.write_text(content)
        ok("已自动切换 ACTIVE_BACKEND → ollama_7b")
    except Exception as e:
        warn(f"自动切换失败，请手动修改: {e}")


# ==================== 步骤3: 启动 Ollama 服务 ====================
def step3_start_ollama():
    step("步骤3: 确保 Ollama 服务运行")

    if wait_for_url("http://localhost:11434", timeout=3):
        ok("Ollama 服务已在运行")
        return True

    info("启动 Ollama 服务...")
    # 后台启动
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if wait_for_url("http://localhost:11434", timeout=15):
        ok("Ollama 服务启动成功 (localhost:11434)")
        return True

    # 尝试 brew services
    info("尝试 brew services 启动...")
    run("brew services start ollama", check=False)
    if wait_for_url("http://localhost:11434", timeout=10):
        ok("Ollama 服务通过 brew services 启动成功")
        return True

    fail("Ollama 服务启动失败，请手动运行: ollama serve")
    return False


# ==================== 步骤4: Python 依赖 ====================
def step4_python_deps():
    step("步骤4: 检查 Python 依赖")

    if not VENV_DIR.exists():
        fail(f"虚拟环境不存在: {VENV_DIR}")
        info("请先运行: python3 -m venv venv")
        return False

    required = ["openai", "numpy"]
    missing = []
    for pkg in required:
        success, _ = run(f"{PYTHON_BIN} -c 'import {pkg}'", check=False, capture=True)
        if success:
            ok(f"  {pkg} ✓")
        else:
            missing.append(pkg)
            warn(f"  {pkg} 缺失")

    if missing:
        info(f"安装缺失依赖: {', '.join(missing)}")
        for pkg in missing:
            run(f"{PIP_BIN} install {pkg}", check=False)

    # sentence-transformers 可选（Ollama 有内置 embedding）
    success, _ = run(f"{PYTHON_BIN} -c 'import sentence_transformers'", check=False, capture=True)
    if success:
        ok("  sentence-transformers ✓ (备用 embedding)")
    else:
        info("  sentence-transformers 未安装（Ollama embedding 可用，不影响运行）")

    ok("Python 依赖检查完成")
    return True


# ==================== 步骤5: 数据库验证 ====================
def step5_verify_database():
    step("步骤5: 验证数据库")

    # 测试用临时导入
    sys.path.insert(0, str(PROJECT_DIR))

    try:
        # 导入但不触发模型加载（懒加载）
        import importlib
        spec = importlib.util.spec_from_file_location("agi", str(MAIN_SCRIPT))
        # 直接测试数据库操作
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 检查表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r['name'] for r in c.fetchall()]
        required_tables = ['cognitive_nodes', 'node_relations', 'growth_log', 'practice_records']

        for t in required_tables:
            if t in tables:
                ok(f"  表 {t} ✓")
            else:
                warn(f"  表 {t} 不存在（首次运行时自动创建）")

        # 检查节点数
        if 'cognitive_nodes' in tables:
            c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
            cnt = c.fetchone()['cnt']
            if cnt > 0:
                ok(f"  认知节点: {cnt} 个")
                c.execute("SELECT COUNT(DISTINCT domain) as cnt FROM cognitive_nodes")
                domains = c.fetchone()['cnt']
                ok(f"  覆盖领域: {domains} 个")
            else:
                info("  数据库为空（首次运行时自动录入 42 个种子节点）")

        if 'node_relations' in tables:
            c.execute("SELECT COUNT(*) as cnt FROM node_relations")
            rel_cnt = c.fetchone()['cnt']
            ok(f"  节点关联: {rel_cnt} 条")

        conn.close()
        ok("数据库验证通过")
        return True

    except Exception as e:
        if "no such table" in str(e):
            info("数据库尚未初始化（首次运行时自动创建）")
            return True
        fail(f"数据库验证失败: {e}")
        return False


# ==================== 步骤6: LLM + Embedding 调用验证 ====================
def step6_verify_llm():
    step("步骤6: 验证 LLM 和 Embedding 调用")

    # 6a: Embedding 验证
    info("测试 Ollama Embedding...")
    test_embed = f'''
import sys
sys.path.insert(0, "{PROJECT_DIR}")
from openai import OpenAI
import numpy as np
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
resp = client.embeddings.create(model="nomic-embed-text", input="测试文本")
vec = resp.data[0].embedding
print(f"embedding维度: {{len(vec)}}")
'''
    success, out = run(f'{PYTHON_BIN} -c \'{test_embed}\'', check=False, capture=True, timeout=30)
    if success and "embedding维度" in out:
        ok(f"Embedding 验证通过 ({out.strip()})")
    else:
        warn(f"Embedding 测试失败: {out}")
        info("将回退到本地 sentence-transformers（需要首次下载模型）")

    # 6b: LLM 验证
    info("测试 Ollama LLM 推理...")

    # 检查当前配置的模型
    success, model_list = run("ollama list", capture=True, check=False)
    using_14b = "qwen2.5-coder:14b" in (model_list or "")
    using_7b = "qwen2.5-coder:7b" in (model_list or "")
    model_name = "qwen2.5-coder:14b" if using_14b else ("qwen2.5-coder:7b" if using_7b else "qwen2.5-coder:14b")

    test_llm = f'''
from openai import OpenAI
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
resp = client.chat.completions.create(
    model="{model_name}",
    max_tokens=100,
    temperature=0.3,
    messages=[{{"role":"user","content":"输出JSON数组: [{{\\"test\\": true}}]\\n只输出JSON。"}}]
)
print(resp.choices[0].message.content.strip()[:200])
'''
    success, out = run(f'{PYTHON_BIN} -c \'{test_llm}\'', check=False, capture=True, timeout=120)
    if success and out.strip():
        ok(f"LLM 验证通过: {out.strip()[:80]}")
        return True
    else:
        warn(f"LLM 调用失败: {out}")
        info("可能原因: 模型尚未加载完成，首次调用需要等待模型载入内存")
        info(f"请确认模型已拉取: ollama list")
        return False


# ==================== 步骤7: 常见问题自动修复 ====================
def step7_auto_fix():
    step("步骤7: 自动修复检查")

    fixes_applied = 0

    # 7a: 检查主脚本是否存在
    if not MAIN_SCRIPT.exists():
        fail(f"主脚本不存在: {MAIN_SCRIPT}")
        return False
    ok("主脚本存在")

    # 7b: 检查是否还在用 anthropic 导入
    content = MAIN_SCRIPT.read_text()
    if "from anthropic import" in content:
        warn("检测到旧版 anthropic 导入，需要更新")
        fail("请重新从最新版本同步代码")
        return False
    ok("代码已使用 openai SDK（兼容 Ollama）")

    # 7c: 检查 ACTIVE_BACKEND 配置
    if 'ACTIVE_BACKEND = "ollama"' in content or 'ACTIVE_BACKEND = "ollama_7b"' in content:
        ok("ACTIVE_BACKEND 已配置为本地 Ollama")
    else:
        warn("ACTIVE_BACKEND 未配置为 Ollama，可能使用云端 API")
        info("如需本地运行，请设置 ACTIVE_BACKEND = \"ollama\"")

    # 7d: 检查旧数据库 schema 兼容性
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        try:
            c.execute("PRAGMA table_info(cognitive_nodes)")
            columns = [r[1] for r in c.fetchall()]
            new_cols = ['depth', 'parent_id', 'access_count']
            for col in new_cols:
                if col not in columns:
                    warn(f"数据库缺少列: {col}（程序启动时自动迁移）")
                    fixes_applied += 1
        except:
            pass
        conn.close()

    if fixes_applied > 0:
        info(f"发现 {fixes_applied} 个待修复项（程序启动时自动处理）")
    else:
        ok("无需修复")

    return True


# ==================== 步骤8: 启动主程序 ====================
def step8_launch():
    step("步骤8: 启动 AGI v13.2")

    print(f"""
{C.BOLD}{C.OK}所有验证通过！{C.END}

{C.BOLD}启动命令：{C.END}
    {PYTHON_BIN} {MAIN_SCRIPT}

{C.BOLD}支持的交互命令：{C.END}
    直接输入问题     → 双向拆解 + 碰撞
    具现化节点       → 录入人类真实实践节点
    生成实践清单     → 为未知节点生成验证步骤
    认知状态         → 查看认知网络统计
    成长日志         → 查看成长历史
    自成长           → 手动触发一次自成长循环
    自动成长         → 启动后台自动成长
    搜索 <关键词>    → 语义搜索认知网络
    exit             → 退出
""")

    answer = input(f"{C.INFO}是否立即启动 AGI? (y/n): {C.END}").strip().lower()
    if answer in ('y', 'yes', ''):
        os.execv(str(PYTHON_BIN), [str(PYTHON_BIN), str(MAIN_SCRIPT)])
    else:
        print(f"\n手动启动: {PYTHON_BIN} {MAIN_SCRIPT}")


# ==================== 主流程 ====================
def main():
    print(f"""
{C.BOLD}{C.INFO}╔══════════════════════════════════════════════════════╗
║  AGI v13.2 Cognitive Lattice — 部署·运行·验证·修复   ║
╚══════════════════════════════════════════════════════╝{C.END}
""")

    results = {}

    # 按顺序执行每个步骤
    steps = [
        ("安装 Ollama",         step1_install_ollama),
        ("拉取模型",             step2_pull_models),
        ("启动 Ollama 服务",     step3_start_ollama),
        ("Python 依赖",         step4_python_deps),
        ("数据库验证",           step5_verify_database),
        ("LLM + Embedding 验证", step6_verify_llm),
        ("自动修复",             step7_auto_fix),
    ]

    all_ok = True
    for name, func in steps:
        try:
            result = func()
            results[name] = result
            if not result:
                all_ok = False
                warn(f"步骤「{name}」未完全通过，继续检查后续步骤...")
        except KeyboardInterrupt:
            print("\n已取消")
            sys.exit(1)
        except Exception as e:
            fail(f"步骤「{name}」异常: {e}")
            results[name] = False
            all_ok = False

    # 汇总报告
    step("验证报告")
    for name, result in results.items():
        status = f"{C.OK}通过{C.END}" if result else f"{C.FAIL}未通过{C.END}"
        print(f"  {status}  {name}")

    if all_ok:
        ok("所有步骤验证通过！")
        step8_launch()
    else:
        warn("部分步骤未通过，请检查上方日志")
        info("修复后重新运行: python3 deploy_and_verify.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        fail(f"脚本执行异常: {e}")
        sys.exit(1)
