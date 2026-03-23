#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Controller + Real Python Runtime
=====================================
架构核心 (参考: ChatGLM All Tools + CaveAgent + Tool-R1):
  - 智谱API = 大脑 (思考/决策/规划)
  - Python技能文件 = 四肢 (执行/状态/验证)
  - 零本地模型负担, 一个函数闭环解决代码问题

设计哲学:
  LLM只生成"做什么", Python运行时负责"真正做"
  持久化命名空间 = CaveAgent双流架构的流2
  execute_python = Tool-R1的统一工具链
  tool_choice=auto = ChatGLM All Tools的自主决策
"""

import json
import time
import sys
import io
import os
import re
import sqlite3
import threading
import traceback
import contextlib
import platform as _platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# 编码能力增强模块
try:
    import coding_enhancer
    _HAS_CODING_ENHANCER = True
except ImportError:
    _HAS_CODING_ENHANCER = False

# ==================== 路径 ====================
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "memory.db"
SKILLS_DIR = PROJECT_ROOT / "workspace" / "skills"

# 确保项目根目录在sys.path中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==================== 认知格引用(由api_server注入) ====================
_lattice = None

def set_lattice(lattice_instance):
    """注入认知格实例，启用语义搜索（由api_server.init_app调用）"""
    global _lattice
    _lattice = lattice_instance
    print("  [ToolController] 认知格已注入，query_knowledge升级为语义搜索")


# ==================== 配置 ====================

def _load_zhipu_config():
    """从已有BACKENDS配置读取智谱API信息"""
    try:
        import agi_v13_cognitive_lattice as agi
        zhipu_cfg = agi.BACKENDS.get("zhipu", {})
        return {
            "api_key": zhipu_cfg.get("api_key", ""),
            "base_url": zhipu_cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
            "default_model": "glm-4-plus",
            "fast_model": "glm-4-flash",
        }
    except Exception:
        return {
            "api_key": "8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4-plus",
            "fast_model": "glm-4-flash",
        }

# ==================== 系统提示 ====================

SYSTEM_PROMPT = """你是一个强大的代码问题解决器。你拥有真实Python运行时和多种工具，不猜测——执行代码来验证。

可用工具:
- execute_python: 持久化Python运行时(变量跨调用保持,可import任何已安装包和workspace/skills/下的模块)
- run_shell: 执行shell命令(有安全限制)
- read_file / write_file: 文件操作
- query_knowledge: 搜索已验证的proven知识节点
- list_skills: 查看可用Python技能模块

代码质量工具:
- run_linter: ruff代码检查(风格/命名/导入)，支持自动修复
- run_security_scan: Bandit安全扫描(SQL注入/XSS/OWASP漏洞)
- run_tests: pytest测试运行+覆盖率报告
- generate_test: 基于AST自动生成pytest测试用例
- analyze_code: AST代码结构分析(函数/类/复杂度/文档率)
- code_review: 自动代码审查(安全+风格+性能,输出A/B/C评级)
- run_profiler: CPU/内存性能分析(cProfile/tracemalloc)
- run_browser_test: Playwright浏览器自动化测试
- analyze_tech_debt: 技术债务分析(TODO/复杂度/bare-except)

工作流:
1. 分析问题 → 需要什么工具/知识?
2. 执行代码验证 → 检查输出
3. 有错误 → 分类错误 → 选择修复策略 → 重试(最多3轮)
4. 成功 → run_linter检查风格 → run_security_scan检查安全 → 返回答案
5. 如果是新功能 → generate_test生成测试 → run_tests验证

execute_python中可以:
- import workspace.skills.code_synthesizer 代码合成
- import workspace.skills.shell_executor 系统操作
- 使用标准库和numpy/requests等常用包
- 变量在多次调用间保持,支持增量开发

回答要求: 简洁准确,包含验证结果。如果写了代码,必须execute_python验证能运行。"""


# ==================== 持久化Python运行时 (CaveAgent双流·流2) ====================

class PersistentRuntime:
    """持久化Python内核 — 变量/import跨调用保持"""

    def __init__(self):
        self._namespace = {
            "__builtins__": __builtins__,
            "__name__": "__tool_runtime__",
        }
        self._history = []
        self._created_at = time.time()
        self._lock = threading.Lock()

    def execute(self, code: str, timeout: int = 30) -> Dict:
        """执行Python代码, 变量持久化, 带超时保护"""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        result = {"success": False}

        def _run():
            nonlocal result
            try:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    exec(code, self._namespace)
                result["success"] = True
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {e}"
                result["traceback"] = traceback.format_exc()[-1500:]

        with self._lock:
            t = threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout)

            if t.is_alive():
                result["error"] = f"执行超时 ({timeout}s)"
                result["success"] = False

        result["stdout"] = stdout_buf.getvalue()[:8000]
        result["stderr"] = stderr_buf.getvalue()[:2000]

        # 可用变量列表
        user_vars = [k for k in self._namespace
                     if not k.startswith('_') and k not in ('builtins',)]
        result["variables"] = user_vars[:50]

        self._history.append({
            "code": code[:300],
            "success": result["success"],
            "time": time.time(),
        })
        return result

    def reset(self):
        """重置运行时"""
        with self._lock:
            self._namespace = {
                "__builtins__": __builtins__,
                "__name__": "__tool_runtime__",
            }
            self._history = []
            self._created_at = time.time()

    @property
    def stats(self):
        return {
            "total_executions": len(self._history),
            "successful": sum(1 for h in self._history if h["success"]),
            "variables_count": len([k for k in self._namespace if not k.startswith('_')]),
            "uptime_s": round(time.time() - self._created_at, 1),
        }


# ==================== 工具定义 (OpenAI Function Calling格式) ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "在持久化Python运行时中执行代码。变量跨调用保持。可import已安装的包和workspace/skills/下的模块。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "执行shell命令。适合:安装包、git、文件管理、系统查询。危险命令会被阻止。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "shell命令"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容(绝对路径或相对于项目根目录)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入/创建文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "搜索认知格中已验证的proven知识节点。用于获取已有的技术知识。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "limit": {"type": "integer", "description": "返回数量(默认5)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "列出所有可用的Python技能模块及其能力描述",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_dxf",
            "description": "解析DXF图纸文件, 提取所有实体(线段/圆/弧/文字/尺寸标注等), 输出结构化文本描述。支持R12-R2018版本DXF。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "DXF文件路径"},
                    "detail_level": {"type": "string", "description": "summary(概要)/full(完整)/entities(仅实体)", "enum": ["summary", "full", "entities"]}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "concept_to_checklist",
            "description": "将工业概念/需求转化为可实践检查清单: 包含加工步骤/刀具/参数/热处理/检验等。输入零件描述, 输出JSON格式工艺规划。",
            "parameters": {
                "type": "object",
                "properties": {
                    "concept": {"type": "string", "description": "工业概念/零件需求描述"},
                    "context": {"type": "string", "description": "额外上下文(材料/公差/工艺要求等)"}
                },
                "required": ["concept"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dxf_drawing",
            "description": "生成DXF工艺图纸。支持: process_flow(工序流程图), flange(参数化法兰盘), heat_curve(热处理曲线), part_outline(零件轮廓)。输出DXF文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "drawing_type": {"type": "string", "description": "图纸类型", "enum": ["process_flow", "flange", "heat_curve", "part_outline"]},
                    "params_json": {"type": "string", "description": "JSON格式参数(process_flow需steps数组, flange需outer_d/inner_d等, heat_curve需steps数组, part_outline需width/height等)"}
                },
                "required": ["drawing_type", "params_json"]
            }
        }
    },
]


# ==================== 工具执行器 ====================

# 全局持久化运行时
_runtime = PersistentRuntime()

DANGEROUS_KEYWORDS = ['rm -rf /', 'mkfs', 'dd if=', '> /dev/', 'shutdown', 'reboot']


def _exec_python(code: str) -> Dict:
    return _runtime.execute(code)


# 平台感知命令模板 (dim13: 终端命令生成准确性)
_CURRENT_OS = _platform.system().lower()  # darwin/linux/windows

PLATFORM_COMMANDS = {
    "list_files":    {"darwin": "ls -la", "linux": "ls -la", "windows": "dir"},
    "find_file":     {"darwin": "find . -name '{}'", "linux": "find . -name '{}'", "windows": "dir /s /b *{}*"},
    "disk_usage":    {"darwin": "df -h", "linux": "df -h", "windows": "wmic logicaldisk get size,freespace,caption"},
    "process_list":  {"darwin": "ps aux", "linux": "ps aux", "windows": "tasklist"},
    "kill_process":  {"darwin": "kill -9 {}", "linux": "kill -9 {}", "windows": "taskkill /F /PID {}"},
    "network_info":  {"darwin": "ifconfig", "linux": "ip addr", "windows": "ipconfig /all"},
    "open_port":     {"darwin": "lsof -i :{}", "linux": "ss -tlnp | grep :{}", "windows": "netstat -ano | findstr :{}"},
    "install_pkg":   {"darwin": "pip3 install {}", "linux": "pip3 install {}", "windows": "pip install {}"},
    "python_run":    {"darwin": "python3 {}", "linux": "python3 {}", "windows": "python {}"},
    "git_status":    {"darwin": "git status", "linux": "git status", "windows": "git status"},
    "env_var":       {"darwin": "echo ${}", "linux": "echo ${}", "windows": "echo %{}%"},
    "create_dir":    {"darwin": "mkdir -p {}", "linux": "mkdir -p {}", "windows": "mkdir {}"},
    "remove_dir":    {"darwin": "rm -rf {}", "linux": "rm -rf {}", "windows": "rmdir /s /q {}"},
    "copy_file":     {"darwin": "cp {} {}", "linux": "cp {} {}", "windows": "copy {} {}"},
    "curl_get":      {"darwin": "curl -s {}", "linux": "curl -s {}", "windows": "curl -s {}"},
}

def get_platform_command(action: str, *args) -> str:
    """获取当前平台的正确命令"""
    tpl = PLATFORM_COMMANDS.get(action, {}).get(_CURRENT_OS, "")
    if tpl and args:
        tpl = tpl.format(*args)
    return tpl


def _exec_shell(command: str) -> Dict:
    for kw in DANGEROUS_KEYWORDS:
        if kw in command.lower():
            return {"success": False, "error": f"危险命令被阻止: {kw}"}
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=str(PROJECT_ROOT)
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
            "returncode": result.returncode,
            "platform": _CURRENT_OS,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "命令超时(30s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _read_file(path: str) -> Dict:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / path
    try:
        content = p.read_text(encoding='utf-8')
        if len(content) > 15000:
            content = content[:15000] + f"\n...(截断, 总长{len(content)}字符)"
        return {"success": True, "content": content, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _write_file(path: str, content: str) -> Dict:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / path
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return {"success": True, "path": str(p), "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _query_knowledge(query: str, limit: int = 5) -> Dict:
    """搜索proven知识节点 — 优先语义搜索，回退关键词匹配"""
    # === 优先：语义搜索（通过注入的认知格实例） ===
    if _lattice is not None:
        try:
            results = _lattice.find_similar_nodes(query, threshold=0.35, limit=limit)
            proven = [n for n in results if n.get('status') == 'proven']
            # 如果proven不够，补充其他状态的高相似度节点
            nodes = proven if len(proven) >= 2 else results[:limit]
            return {
                "success": True,
                "search_mode": "semantic",
                "count": len(nodes),
                "nodes": [
                    {
                        "id": n.get('id'),
                        "content": n.get('content', '')[:300],
                        "domain": n.get('domain', ''),
                        "status": n.get('status', ''),
                        "similarity": round(n.get('similarity', 0), 3),
                    }
                    for n in nodes
                ]
            }
        except Exception as e:
            print(f"  [ToolController] 语义搜索失败，回退关键词: {e}")

    # === 回退：SQL关键词匹配 ===
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("""
            SELECT id, content, domain, status FROM cognitive_nodes
            WHERE status='proven' AND content LIKE ?
            ORDER BY id DESC LIMIT ?
        """, (f"%{query}%", limit))
        rows = c.fetchall()

        if not rows:
            words = [w for w in query.split() if len(w) > 1][:4]
            if words:
                conditions = " OR ".join(["content LIKE ?" for _ in words])
                word_params = [f"%{w}%" for w in words]
                c.execute(f"""
                    SELECT id, content, domain, status FROM cognitive_nodes
                    WHERE status='proven' AND ({conditions})
                    ORDER BY id DESC LIMIT ?
                """, word_params + [limit])
                rows = c.fetchall()
        conn.close()

        return {
            "success": True,
            "search_mode": "keyword_fallback",
            "count": len(rows),
            "nodes": [{"id": r[0], "content": r[1][:300], "domain": r[2]} for r in rows]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _list_skills() -> Dict:
    """列出所有技能模块"""
    skills = []
    for meta_file in sorted(SKILLS_DIR.glob("*.meta.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            py_name = meta_file.name.replace('.meta.json', '.py')
            py_file = SKILLS_DIR / py_name
            skills.append({
                "name": meta.get("name", meta_file.stem),
                "description": meta.get("description", "")[:100],
                "file": f"workspace/skills/{py_name}" if py_file.exists() else None,
                "capabilities": meta.get("capabilities", [])[:5],
            })
        except Exception:
            pass
    return {"success": True, "count": len(skills), "skills": skills}


def _parse_dxf(file_path: str, detail_level: str = "summary") -> Dict:
    """解析DXF图纸"""
    try:
        from workspace.skills.cad_file_recognizer import dxf_to_text
        return dxf_to_text(file_path, detail_level)
    except Exception as e:
        return {"success": False, "error": f"DXF解析失败: {e}"}


def _concept_to_checklist(concept: str, context: str = "") -> Dict:
    """工业概念→检查清单"""
    try:
        from workspace.skills.cad_process_planner import concept_to_checklist
        return concept_to_checklist(concept, context)
    except Exception as e:
        return {"success": False, "error": f"工艺规划失败: {e}"}


def _generate_dxf_drawing(drawing_type: str, params_json: str) -> Dict:
    """生成DXF工艺图纸"""
    try:
        params = json.loads(params_json) if isinstance(params_json, str) else params_json
    except json.JSONDecodeError:
        return {"success": False, "error": f"参数JSON解析失败: {params_json[:200]}"}

    try:
        from workspace.skills import cad_drawing_generator as gen
        if drawing_type == "process_flow":
            return gen.generate_process_flow_dxf(
                steps=params.get("steps", []),
                title=params.get("title", "工艺流程图"),
            )
        elif drawing_type == "flange":
            return gen.generate_flange_dxf(**{k: v for k, v in params.items() if k in (
                'outer_d', 'inner_d', 'bolt_circle_d', 'bolt_count', 'bolt_hole_d', 'thickness', 'material'
            )})
        elif drawing_type == "heat_curve":
            return gen.generate_heat_treatment_curve(
                steps=params.get("steps", []),
                title=params.get("title", "热处理工艺曲线"),
            )
        elif drawing_type == "part_outline":
            return gen.generate_part_outline_dxf(
                width=params.get("width", 100),
                height=params.get("height", 50),
                holes=params.get("holes", []),
                title=params.get("title", "零件图"),
                material=params.get("material", ""),
            )
        else:
            return {"success": False, "error": f"未知图纸类型: {drawing_type}。支持: process_flow/flange/heat_curve/part_outline"}
    except Exception as e:
        return {"success": False, "error": f"图纸生成失败: {e}"}


# 工具分发表
TOOL_HANDLERS = {
    "execute_python": lambda args: _exec_python(args.get("code", "")),
    "run_shell":      lambda args: _exec_shell(args.get("command", "")),
    "read_file":      lambda args: _read_file(args.get("path", "")),
    "write_file":     lambda args: _write_file(args.get("path", ""), args.get("content", "")),
    "query_knowledge": lambda args: _query_knowledge(args.get("query", ""), args.get("limit", 5)),
    "list_skills":    lambda args: _list_skills(),
    "parse_dxf":      lambda args: _parse_dxf(args.get("file_path", ""), args.get("detail_level", "summary")),
    "concept_to_checklist": lambda args: _concept_to_checklist(args.get("concept", ""), args.get("context", "")),
    "generate_dxf_drawing": lambda args: _generate_dxf_drawing(args.get("drawing_type", ""), args.get("params_json", "{}")),
}

# ==================== 编码增强工具注册 ====================
if _HAS_CODING_ENHANCER:
    TOOLS.extend(coding_enhancer.CODING_TOOLS)
    TOOL_HANDLERS.update(coding_enhancer.CODING_HANDLERS)


def execute_tool(name: str, args: Dict) -> Dict:
    """安全执行工具"""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"success": False, "error": f"未知工具: {name}"}
    try:
        return handler(args)
    except Exception as e:
        return {"success": False, "error": f"工具执行异常: {type(e).__name__}: {e}"}


# ==================== LLM Controller 核心 ====================

_client = None
_stats = {
    "total_solves": 0,
    "total_tool_calls": 0,
    "total_tokens_est": 0,
    "total_rounds": 0,
    "errors": 0,
}


def _get_client():
    """懒加载OpenAI客户端(连接智谱API)"""
    global _client
    if _client is None:
        from openai import OpenAI
        cfg = _load_zhipu_config()
        _client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )
        print(f"  [ToolController] 已连接智谱API: {cfg['base_url']}")
    return _client


def solve(
    question: str,
    max_rounds: int = 15,
    model: str = None,
    system_prompt: str = None,
    context: List[Dict] = None,
    on_step: callable = None,
) -> Dict:
    """
    核心函数: 问题 → LLM思考 + 工具调用循环 → 真实验证的答案

    这一个函数替代整个旧pipeline:
      旧: local_ollama → decompose → collide → synthesize (复杂, 依赖本地模型)
      新: zhipu_api → tool_calls → python_runtime → done (简洁, 真实执行)

    Args:
        question: 用户问题
        max_rounds: 最大工具调用轮次
        model: 指定模型(默认glm-4-plus, 简单任务可用glm-4-flash)
        system_prompt: 自定义系统提示
        context: 额外上下文messages
        on_step: 步骤回调 (step_type, detail) -> None

    Returns:
        {answer, tool_calls, rounds, duration, runtime_stats}
    """
    t0 = time.time()
    cfg = _load_zhipu_config()
    model = model or cfg["default_model"]
    client = _get_client()

    messages = [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT}
    ]
    if context:
        messages.extend(context)
    messages.append({"role": "user", "content": question})

    tool_log = []
    _stats["total_solves"] += 1

    if on_step:
        on_step("start", {"question": question[:200], "model": model})

    # 消息自动压缩阈值（防止上下文过长导致幻觉漂移）
    MSG_TOKEN_LIMIT = 12000  # 估算token上限
    MSG_KEEP_LAST = 8        # 压缩时保留最近N条消息

    for round_num in range(max_rounds):
        # === 消息自动压缩（防幻觉累积） ===
        est_tokens = sum(len(m.get("content", "")) // 2 for m in messages)
        if est_tokens > MSG_TOKEN_LIMIT and len(messages) > MSG_KEEP_LAST + 1:
            system_msg = messages[0] if messages[0]["role"] == "system" else None
            kept = messages[-MSG_KEEP_LAST:]
            messages = ([system_msg] if system_msg else []) + kept
            print(f"  [ToolController] 消息压缩: {est_tokens}tok→保留{len(messages)}条(防幻觉)")

        # === LLM 思考 (流1) ===
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as e:
            _stats["errors"] += 1
            error_msg = str(e)
            print(f"  [ToolController] API错误: {error_msg[:200]}")
            return {
                "answer": f"API调用失败: {error_msg}",
                "tool_calls": tool_log,
                "rounds": round_num,
                "duration": round(time.time() - t0, 2),
                "error": error_msg,
            }

        msg = response.choices[0].message

        # Token统计
        if response.usage:
            _stats["total_tokens_est"] += response.usage.total_tokens

        # === 无工具调用 → LLM给出最终答案 ===
        if not msg.tool_calls:
            answer = msg.content or ""
            _stats["total_rounds"] += round_num + 1
            if on_step:
                on_step("done", {"answer": answer[:300], "rounds": round_num + 1})
            print(f"  [ToolController] 完成: {round_num+1}轮, {len(tool_log)}次工具调用, {time.time()-t0:.1f}s")
            return {
                "answer": answer,
                "tool_calls": tool_log,
                "rounds": round_num + 1,
                "duration": round(time.time() - t0, 2),
                "runtime_stats": _runtime.stats,
            }

        # === 有工具调用 → 执行工具 (流2) ===
        # 将assistant消息(含tool_calls)追加到messages
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        })

        # 执行每个工具调用
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                tool_args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            if on_step:
                on_step("tool_call", {
                    "name": tool_name,
                    "args_preview": str(tool_args)[:200],
                    "round": round_num + 1,
                })

            # 真实执行
            result = execute_tool(tool_name, tool_args)
            _stats["total_tool_calls"] += 1

            # 记录日志
            tool_log.append({
                "round": round_num + 1,
                "name": tool_name,
                "args": {k: str(v)[:150] for k, v in tool_args.items()},
                "success": result.get("success", False),
                "result_preview": _preview_result(result),
            })

            if on_step:
                on_step("tool_result", {
                    "name": tool_name,
                    "success": result.get("success"),
                    "preview": _preview_result(result)[:100],
                    "round": round_num + 1,
                })

            # 结果反馈给LLM
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "...(truncated)"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

            print(f"  [Tool] R{round_num+1} {tool_name} → {'✅' if result.get('success') else '❌'}")

    # 达到最大轮次
    _stats["total_rounds"] += max_rounds
    return {
        "answer": "达到最大工具调用轮次。部分结果:\n" + "\n".join(
            f"- {t['name']}: {'✅' if t['success'] else '❌'} {t['result_preview'][:100]}"
            for t in tool_log[-5:]
        ),
        "tool_calls": tool_log,
        "rounds": max_rounds,
        "duration": round(time.time() - t0, 2),
        "runtime_stats": _runtime.stats,
    }


def _preview_result(result: Dict) -> str:
    """提取结果摘要"""
    if result.get("stdout"):
        return result["stdout"][:200]
    if result.get("content"):
        return result["content"][:200]
    if result.get("nodes"):
        return f"{len(result['nodes'])}个知识节点"
    if result.get("skills"):
        return f"{len(result['skills'])}个技能模块"
    if result.get("error"):
        return f"错误: {result['error'][:150]}"
    return str(result)[:200]


# ==================== 公开API ====================

def get_stats() -> Dict:
    """获取控制器统计"""
    return {**_stats, "runtime": _runtime.stats}


def reset_runtime() -> Dict:
    """重置持久化运行时"""
    _runtime.reset()
    return {"success": True, "message": "运行时已重置"}


def get_tools_info() -> List[Dict]:
    """获取所有注册的工具信息"""
    return [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
        }
        for t in TOOLS
    ]


# ==================== 自测 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("LLM Controller 自测")
    print("=" * 60)

    # 测试1: 列出技能
    print("\n--- 测试1: list_skills ---")
    r = _list_skills()
    print(f"技能数: {r['count']}")
    for s in r['skills'][:3]:
        print(f"  - {s['name']}: {s['description'][:60]}")

    # 测试2: 持久化运行时
    print("\n--- 测试2: PersistentRuntime ---")
    r1 = _runtime.execute("x = 42\nprint(f'x = {x}')")
    print(f"  执行1: {r1}")
    r2 = _runtime.execute("print(f'x still = {x}')\ny = x * 2\nprint(f'y = {y}')")
    print(f"  执行2: {r2}")
    print(f"  运行时统计: {_runtime.stats}")

    # 测试3: 知识查询
    print("\n--- 测试3: query_knowledge ---")
    r = _query_knowledge("Python", 3)
    print(f"  找到 {r['count']} 个节点")
    for n in r.get('nodes', [])[:2]:
        print(f"  - [{n['domain']}] {n['content'][:60]}")

    # 测试4: 完整solve (需要网络)
    print("\n--- 测试4: solve ---")
    try:
        result = solve("用Python写一个函数计算斐波那契数列前10项并验证", max_rounds=5)
        print(f"  轮次: {result['rounds']}")
        print(f"  工具调用: {len(result['tool_calls'])}次")
        print(f"  耗时: {result['duration']}s")
        print(f"  答案前200字: {result['answer'][:200]}")
    except Exception as e:
        print(f"  solve测试跳过(需要网络): {e}")

    print("\n" + "=" * 60)
    print("自测完成")
