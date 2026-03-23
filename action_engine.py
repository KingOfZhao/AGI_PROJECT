#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 动作引擎 (Action Engine) — 赋予 AGI 双手
让模型可以：
  1. 创建/读取/修改文件 (py, json, md, yaml, skill, pcm 等)
  2. 执行 Python 脚本并获取输出
  3. 自主构建技能模块 (skill)
  4. 将执行结果反馈回认知网络
"""

import os
import sys
import json
import uuid
import time
import subprocess
import traceback
import threading
import re
from pathlib import Path
from datetime import datetime

# ==================== 工作区配置 ====================
WORKSPACE_DIR = Path(__file__).parent / "workspace"
SKILLS_DIR = WORKSPACE_DIR / "skills"
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"
LOGS_DIR = WORKSPACE_DIR / "logs"

for d in [WORKSPACE_DIR, SKILLS_DIR, OUTPUTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 安全白名单路径 — 允许在这些目录下创建文件
SAFE_PATHS = [
    WORKSPACE_DIR.resolve(),
    Path.home() / "Desktop",
    Path.home() / "桌面",
    Path.home() / "Documents",
    Path.home() / "文档",
    Path.home() / "Downloads",
    Path(__file__).parent.resolve(),  # 项目根目录
]

# 允许创建的文件类型
ALLOWED_EXTENSIONS = {
    '.py', '.json', '.yaml', '.yml', '.md', '.txt', '.csv',
    '.html', '.css', '.js', '.ts', '.tsx', '.jsx', '.vue', '.sh', '.pcm', '.skill', '.toml',
    '.xml', '.sql', '.r', '.lua', '.conf', '.ini', '.env',
    '.rs', '.go', '.java', '.cs', '.kt', '.swift', '.dart',  # 编译型语言(GLM-5·臣)
    '.sol', '.vy',                                             # 区块链(GLM-5·臣)
    '.cpp', '.c', '.h', '.hpp',                                # C/C++
    '.rb', '.php', '.scala', '.ex', '.exs',                    # 其他语言
    '.wat', '.wasm',                                           # WebAssembly
    '.gd', '.gdscript',                                        # Godot游戏引擎
    '.proto', '.graphql', '.prisma',                           # Schema/接口定义
    '.dxf', '.step', '.stp', '.iges',                          # CAD工程文件
}

# Python 执行超时（秒）
EXEC_TIMEOUT = 30

# ==================== 执行日志（内存 + 持久化） ====================
_execution_log = []
_log_lock = threading.Lock()
_log_subscribers = []  # SSE 订阅者列表


def _emit_step(step_type, detail, status="running"):
    """发射一个执行步骤到日志和所有订阅者"""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "type": step_type,
        "detail": detail,
        "status": status,
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
    }
    with _log_lock:
        _execution_log.append(entry)
        if len(_execution_log) > 500:
            _execution_log.pop(0)
        # 通知所有 SSE 订阅者
        for q in _log_subscribers:
            try:
                q.append(entry)
            except:
                pass
    return entry


def subscribe_log():
    """订阅执行日志流（SSE 用）"""
    q = []
    with _log_lock:
        _log_subscribers.append(q)
    return q


def unsubscribe_log(q):
    with _log_lock:
        if q in _log_subscribers:
            _log_subscribers.remove(q)


def get_recent_log(n=50):
    with _log_lock:
        return list(_execution_log[-n:])


# ==================== 文件操作 ====================
class FileAction:
    """文件创建/读取/修改"""

    @staticmethod
    def create_file(filepath, content, description=""):
        """创建文件 — 支持工作区内相对路径和白名单内绝对路径"""
        _emit_step("file_create", f"准备创建文件: {filepath}")

        # 解析路径：绝对路径直接使用，相对路径放入workspace
        filepath_p = Path(filepath)
        if filepath_p.is_absolute():
            full_path = filepath_p
        elif filepath.startswith('~'):
            full_path = Path(filepath).expanduser()
        else:
            full_path = WORKSPACE_DIR / filepath

        # 安全检查：必须在白名单目录内
        resolved = full_path.resolve()
        is_safe = any(
            str(resolved).startswith(str(sp.resolve()))
            for sp in SAFE_PATHS
            if sp.exists() or sp == WORKSPACE_DIR.resolve()
        )
        if not is_safe:
            msg = f"安全限制：路径不在允许范围内 ({filepath})。允许: Desktop/Documents/Downloads/workspace"
            _emit_step("file_create", msg, "error")
            return {"success": False, "error": msg}

        # 扩展名检查
        ext = full_path.suffix.lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            msg = f"不支持的文件类型: {ext}"
            _emit_step("file_create", msg, "error")
            return {"success": False, "error": msg}

        # 创建目录
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        try:
            full_path.write_text(content, encoding='utf-8')
            size = full_path.stat().st_size
            _emit_step("file_create", f"✓ 文件已创建: {filepath} ({size} bytes)", "done")
            return {
                "success": True,
                "path": str(filepath),
                "full_path": str(full_path),
                "size": size,
                "description": description
            }
        except Exception as e:
            msg = f"创建文件失败: {e}"
            _emit_step("file_create", msg, "error")
            return {"success": False, "error": msg}

    @staticmethod
    def read_file(filepath):
        """读取工作区文件"""
        full_path = WORKSPACE_DIR / filepath
        try:
            full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
        except ValueError:
            return {"success": False, "error": "安全限制：不能读取工作区外文件"}

        if not full_path.exists():
            return {"success": False, "error": f"文件不存在: {filepath}"}

        try:
            content = full_path.read_text(encoding='utf-8')
            return {
                "success": True,
                "path": str(filepath),
                "content": content,
                "size": full_path.stat().st_size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_workspace():
        """列出工作区所有文件"""
        files = []
        for f in WORKSPACE_DIR.rglob("*"):
            if f.is_file():
                rel = f.relative_to(WORKSPACE_DIR)
                files.append({
                    "path": str(rel),
                    "size": f.stat().st_size,
                    "ext": f.suffix,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "dir": str(rel.parent) if str(rel.parent) != "." else ""
                })
        files.sort(key=lambda x: x['path'])
        return files


# ==================== Python 执行 ====================
class ExecuteAction:
    """安全执行 Python 脚本"""

    @staticmethod
    def run_python(filepath=None, code=None, description=""):
        """执行 Python 代码，返回输出结果"""
        exec_id = str(uuid.uuid4())[:8]

        if filepath:
            full_path = WORKSPACE_DIR / filepath
            try:
                full_path.resolve().relative_to(WORKSPACE_DIR.resolve())
            except ValueError:
                return {"success": False, "error": "安全限制"}
            if not full_path.exists():
                return {"success": False, "error": f"文件不存在: {filepath}"}
            code_to_run = full_path.read_text(encoding='utf-8')
            _emit_step("execute", f"执行文件: {filepath}", "running")
        elif code:
            # 将代码保存到临时文件执行
            temp_file = OUTPUTS_DIR / f"exec_{exec_id}.py"
            temp_file.write_text(code, encoding='utf-8')
            filepath = f"outputs/exec_{exec_id}.py"
            code_to_run = code
            _emit_step("execute", f"执行代码片段 ({len(code)} chars)", "running")
        else:
            return {"success": False, "error": "需要提供 filepath 或 code"}

        # 记录代码内容到日志
        preview = code_to_run[:200] + ('...' if len(code_to_run) > 200 else '')
        _emit_step("execute_code", f"```python\n{preview}\n```", "running")

        # 获取 venv python
        project_dir = Path(__file__).parent
        venv_python = project_dir / "venv" / "bin" / "python"
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        # 执行
        start_time = time.time()
        try:
            result = subprocess.run(
                [python_cmd, "-c", code_to_run],
                capture_output=True, text=True,
                timeout=EXEC_TIMEOUT,
                cwd=str(WORKSPACE_DIR),
                env={**os.environ, "PYTHONPATH": str(project_dir)}
            )
            elapsed = time.time() - start_time
            stdout = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            stderr = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr

            success = result.returncode == 0

            if success:
                _emit_step("execute_result", f"✓ 执行成功 ({elapsed:.2f}s)\n{stdout[:300]}", "done")
            else:
                _emit_step("execute_result", f"✗ 执行失败 (code={result.returncode})\n{stderr[:300]}", "error")

            # 保存输出
            output_file = OUTPUTS_DIR / f"output_{exec_id}.txt"
            output_file.write_text(
                f"=== 执行时间: {datetime.now().isoformat()} ===\n"
                f"=== 文件: {filepath} ===\n"
                f"=== 耗时: {elapsed:.2f}s ===\n"
                f"=== 返回码: {result.returncode} ===\n\n"
                f"--- STDOUT ---\n{result.stdout}\n\n"
                f"--- STDERR ---\n{result.stderr}\n",
                encoding='utf-8'
            )

            return {
                "success": success,
                "exec_id": exec_id,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": result.returncode,
                "elapsed": round(elapsed, 2),
                "output_file": f"outputs/output_{exec_id}.txt"
            }

        except subprocess.TimeoutExpired:
            _emit_step("execute_result", f"✗ 执行超时 ({EXEC_TIMEOUT}s)", "error")
            return {"success": False, "error": f"执行超时 ({EXEC_TIMEOUT}s)"}
        except Exception as e:
            _emit_step("execute_result", f"✗ 执行异常: {e}", "error")
            return {"success": False, "error": str(e)}


# ==================== 技能构建器 ====================
class SkillBuilder:
    """AGI 自主构建可复用的技能模块"""

    @staticmethod
    def build_skill(name, description, code, tags=None):
        """构建一个技能文件"""
        _emit_step("skill_build", f"构建技能: {name}", "running")

        # 规范化技能名
        safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', name)
        skill_file = SKILLS_DIR / f"{safe_name}.py"

        # 技能文件格式
        skill_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: {name}
描述: {description}
标签: {', '.join(tags or [])}
创建: {datetime.now().isoformat()}
由 AGI v13.3 Cognitive Lattice 自主构建
"""

{code}

# === 技能元数据 ===
SKILL_META = {{
    "name": {json.dumps(name, ensure_ascii=False)},
    "description": {json.dumps(description, ensure_ascii=False)},
    "tags": {json.dumps(tags or [], ensure_ascii=False)},
    "created_at": "{datetime.now().isoformat()}",
    "version": "1.0"
}}

if __name__ == "__main__":
    print(f"技能 [{name}] 执行中...")
    if 'main' in dir():
        main()
    elif 'run' in dir():
        run()
    else:
        print("此技能没有定义 main() 或 run() 入口")
'''
        result = FileAction.create_file(f"skills/{safe_name}.py", skill_content, description)

        if result["success"]:
            # 保存技能元数据
            meta_file = SKILLS_DIR / f"{safe_name}.meta.json"
            meta_file.write_text(json.dumps({
                "name": name,
                "description": description,
                "tags": tags or [],
                "file": f"skills/{safe_name}.py",
                "created_at": datetime.now().isoformat(),
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            _emit_step("skill_build", f"✓ 技能已构建: {safe_name}.py", "done")

        return result

    @staticmethod
    def list_skills():
        """列出所有已构建的技能"""
        skills = []
        for f in SKILLS_DIR.glob("*.meta.json"):
            try:
                meta = json.loads(f.read_text(encoding='utf-8'))
                skills.append(meta)
            except:
                pass
        return skills

    @staticmethod
    def run_skill(name):
        """执行一个技能"""
        safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', name)
        skill_file = f"skills/{safe_name}.py"
        _emit_step("skill_run", f"执行技能: {name}", "running")
        return ExecuteAction.run_python(filepath=skill_file)


# ==================== LLM 驱动的动作规划器 ====================

ACTION_PLAN_SYSTEM = """你是认知格 AGI 的动作规划器。你拥有以下核心能力：

## 基础能力
1. **create_file**: 创建文件（py/json/md/yaml/skill 等）
2. **execute_python**: 执行 Python 代码
3. **build_skill**: 构建可复用的技能模块
4. **read_file**: 读取已有文件

## 高级能力（超越静态 LLM）
5. **code_synthesize**: 迭代式代码合成 — 生成→执行→检错→自动修复→循环直到通过（最多5轮）
6. **web_research**: 搜索互联网 → 抓取页面 → 提取知识 → 注入认知网络
7. **reasoning_chain**: 基于认知网络已知节点构建可追溯的推理链
8. **verify_claim**: 通过编写并执行代码来验证或反驳一个声明
9. **forge_tool**: 当缺乏某种能力时，自主设计→生成→测试→注册新工具
10. **learn_topic**: 自主学习 — 识别知识空白 → Web研究/代码验证 → 填补
11. **analyze_network**: 分析认知网络拓扑（孤立节点/枢纽/跨域桥梁）
12. **mine_patterns**: 跨域模式挖掘 — 发现不同领域的深层结构相似性

## 软件工程能力（Cascade 级别）
13. **implement_requirement**: 完整软件工程管线 — 需求分析→架构设计→多文件代码生成→测试验证→调试修复（处理复杂多文件项目）
14. **edit_existing_code**: 增量编辑现有文件 — 读取代码→理解上下文→精准替换→验证
15. **analyze_codebase**: 分析代码库结构 — AST解析→依赖图→模式识别→架构理解

## 云端算力委托（智谱AI）
16. **zhipu_delegate**: 将复杂任务委托给智谱AI云端模型 — 自动选择最优模型(glm-4-flash快速/glm-4-plus强力/glm-4-long长文/glm-5旗舰)，结果经本地校验
   - 适用场景：本地14B模型能力不足的复杂推理、大规模代码生成、长文档分析、需要更强算力的任务
   - 本地模型负责决策和校验，智谱AI负责执行

## 超越引擎（多模型编排，超越单体大模型）
17. **surpass**: 超越引擎 — 自动分析任务复杂度，选择最优策略执行
   - strategy=iterative: 代码生成→执行验证→自动修复→循环(最多5轮)，确保代码可运行
   - strategy=ensemble: 多模型投票(本地+flash+plus)，交叉校验取共识
   - strategy=cot: 结构化思维链，分解复杂问题为子步骤逐一推理
   - strategy=cloud: 知识锚定生成，注入proven节点确保事实性
   - 不指定strategy则自动分析任务选择最优方案

## 云端代码产出（Claude级编码能力）
18. **cloud_code_generate**: 调用GLM-4.7生成高质量代码→自动写入文件→执行验证→失败自修复（最多3轮）
   - 用于需要实际创建文件并执行的任务（如"在桌面创建一个xx脚本"）
   - 生成的代码直接写入指定路径，不是给用户看的文本
   - params: {"task": "任务描述", "filepath": "文件保存路径(绝对或相对)", "execute": true/false}

输出严格 JSON 数组，每个动作：
[
  {
    "action": "动作名",
    "params": {
      // create_file: {"path": "相对路径", "content": "文件内容", "description": "描述"}
      // execute_python: {"code": "Python代码"} 或 {"filepath": "文件路径"}
      // build_skill: {"name": "技能名", "description": "描述", "code": "核心代码", "tags": ["标签"]}
      // read_file: {"path": "文件路径"}
      // code_synthesize: {"task": "任务描述", "save_path": "保存路径(可选)"}
      // web_research: {"topic": "研究主题", "depth": 1或2}
      // reasoning_chain: {"question": "要推理的问题"}
      // verify_claim: {"claim": "要验证的声明"}
      // forge_tool: {"need": "需要什么工具"}
      // learn_topic: {"domain": "要学习的领域(可选)"}
      // analyze_network: {}
      // mine_patterns: {}
      // implement_requirement: {"requirement": "自然语言需求描述", "project_dir": "项目目录(可选)"}
      // edit_existing_code: {"filepath": "要编辑的文件路径", "requirement": "修改需求"}
      // analyze_codebase: {"project_dir": "项目目录"}
      // zhipu_delegate: {"task": "委托任务描述", "task_type": "code_gen/reasoning/translate/summarize/analyze/chat(可选)", "model": "glm-4-flash/glm-4-plus/glm-4-long/glm-5(可选)", "verify": true}
      // surpass: {"task": "任务描述", "strategy": "iterative/ensemble/cot/cloud(可选,不填自动)", "model": "指定模型(可选)"}
      // cloud_code_generate: {"task": "任务描述", "filepath": "保存路径(绝对路径或相对路径)", "execute": true}
    },
    "reasoning": "为什么执行这个动作（一句话）"
  }
]

决策原则：
- 用户要求创建脚本/文件/程序 → 优先用 cloud_code_generate（云端高质量代码+自动写入+验证）
- 复杂多文件项目/完整软件开发 → 用 implement_requirement（最强代码能力）
- 修改现有文件 → 用 edit_existing_code（增量精准编辑）
- 理解项目结构 → 用 analyze_codebase
- 简单单文件脚本 → 也可用 code_synthesize（自动修复）
- 需要最新信息 → 用 web_research
- 需要验证一个说法 → 用 verify_claim
- 需要深度分析 → 用 reasoning_chain
- 发现缺乏某种工具 → 用 forge_tool
- 简单文件操作（已有内容）→ 用 create_file / read_file
- 本地模型能力不够的复杂任务 → 用 zhipu_delegate（借用云端算力，结果本地校验）
- 需要最高质量输出的关键任务 → 用 surpass（多模型编排+迭代精炼+知识锚定，超越单体大模型）
- 当用户指定路径(如桌面)时，在filepath中使用绝对路径
- 每个动作必须有明确目的
- 执行结果将反馈到认知网络成为新的已知节点
- 只输出 JSON，不要其他文字"""


def _detect_action_intent(message):
    """检测用户消息是否包含动作执行意图（创建文件、运行代码等）"""
    action_keywords = [
        '创建', '生成', '写入', '编写', '保存', '新建', '制作',
        '在桌面', '在Desktop', '在文件', '写一个', '写个', '做一个',
        '运行', '执行', '测试', '部署', '安装', '下载',
        'create', 'write', 'generate', 'build', 'make', 'save',
        '脚本', '程序', '文件', '项目', '应用',
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in action_keywords)


def plan_actions(question, context_nodes=None, lattice=None):
    """让云端LLM规划需要执行的动作（优先GLM-4.5-Air，回退本地）"""
    import cognitive_core

    context = ""
    if context_nodes:
        context = "\n\n相关已知节点：\n" + "\n".join(
            f"- [{n.get('domain', '?')}] {n.get('content', '')}" for n in context_nodes[:5]
        )

    skills = SkillBuilder.list_skills()
    skills_ctx = ""
    if skills:
        skills_ctx = "\n\n已有技能：\n" + "\n".join(
            f"- {s['name']}: {s['description']}" for s in skills[:10]
        )

    # 添加用户桌面路径提示，让LLM知道可以在桌面创建文件
    desktop_path = str(Path.home() / "Desktop")
    path_hint = f"\n\n可用路径：桌面={desktop_path}，工作区=workspace/，项目根=./"

    messages = [
        {
            "role": "system",
            "content": cognitive_core.COGNITIVE_LATTICE_IDENTITY + ACTION_PLAN_SYSTEM
        },
        {
            "role": "user",
            "content": f"请为以下任务规划执行动作：\n\n{question}{context}{skills_ctx}{path_hint}\n\n输出动作计划 JSON："
        }
    ]

    import agi_v13_cognitive_lattice as agi

    # 优先使用云端GLM-4.5-Air做动作规划（JSON生成质量远高于本地14B）
    result = None
    try:
        zhipu_b = agi.BACKENDS.get("zhipu")
        if zhipu_b and zhipu_b.get("api_key"):
            from openai import OpenAI
            client = OpenAI(api_key=zhipu_b["api_key"], base_url=zhipu_b["base_url"])
            resp = client.chat.completions.create(
                model="GLM-4.5-Air",
                max_tokens=4096,
                temperature=0.2,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages]
            )
            content = resp.choices[0].message.content.strip()
            _emit_step("action_plan", f"☁ GLM-4.5-Air 规划完成 ({len(content)}字符)", "running")
            result = agi._parse_llm_content(content)
    except Exception as e:
        _emit_step("action_plan", f"云端规划失败({e})，回退本地模型", "running")

    # 回退本地模型
    if result is None or (isinstance(result, dict) and 'error' in result):
        result = agi.llm_call(messages)

    return agi.extract_items(result)


def _dispatch_advanced_action(act_type, params, lattice=None):
    """调度高级技能动作"""
    try:
        if act_type == "code_synthesize":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.code_synthesizer import synthesize_and_verify
            task = params.get("task", params.get("description", ""))
            save = params.get("save_path")
            _emit_step("execute", f"🔄 迭代式代码合成: {task[:60]}...", "running")
            r = synthesize_and_verify(task, save_path=save)
            status = "done" if r.get("success") else "error"
            _emit_step("execute_result", f"迭代{r.get('iterations',0)}次 {'✓成功' if r.get('success') else '✗失败'}", status)
            return r

        elif act_type == "web_research":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.web_researcher import research_topic, research_and_ingest
            topic = params.get("topic", "")
            depth = params.get("depth", 1)
            _emit_step("execute", f"🌐 Web研究: {topic[:60]}", "running")
            if lattice:
                r = research_and_ingest(topic, lattice)
            else:
                r = research_topic(topic, depth=depth)
            _emit_step("execute_result", f"发现{r.get('total_points',0)}个知识点, 注入{r.get('ingested_nodes',0)}个", "done" if r.get("success") else "error")
            return r

        elif act_type == "reasoning_chain":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.knowledge_consolidator import build_reasoning_chain
            question = params.get("question", "")
            _emit_step("execute", f"🔗 构建推理链: {question[:60]}", "running")
            if lattice:
                r = build_reasoning_chain(lattice, question)
            else:
                r = {"success": False, "error": "需要认知网络实例"}
            _emit_step("execute_result", f"推理链 {r.get('steps',0)} 步", "done" if r.get("success") else "error")
            return r

        elif act_type == "verify_claim":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.self_evaluator import verify_by_execution
            claim = params.get("claim", "")
            _emit_step("execute", f"🔬 代码验证声明: {claim[:60]}", "running")
            r = verify_by_execution(claim, lattice)
            verdict = "已验证" if r.get("verified") else "已反驳"
            _emit_step("execute_result", f"{verdict}: {claim[:40]}", "done")
            return r

        elif act_type == "forge_tool":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.tool_forge import forge_from_need
            need = params.get("need", "")
            _emit_step("execute", f"🛠 锻造新工具: {need[:60]}", "running")
            r = forge_from_need(need)
            _emit_step("execute_result", f"工具{'✓锻造成功' if r.get('success') else '✗锻造失败'}: {r.get('name','?')}", "done" if r.get("success") else "error")
            return r

        elif act_type == "learn_topic":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.autonomous_learner import run_learning_cycle
            domain = params.get("domain")
            _emit_step("execute", f"📚 自主学习: {domain or '全领域'}", "running")
            if lattice:
                r = run_learning_cycle(lattice, domain=domain)
            else:
                r = {"success": False, "error": "需要认知网络实例"}
            _emit_step("execute_result", f"填补{r.get('gaps_filled',0)}个空白, +{r.get('new_nodes',0)}节点", "done" if r.get("success") else "error")
            return r

        elif act_type == "analyze_network":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.knowledge_consolidator import analyze_network_topology
            _emit_step("execute", "📊 分析认知网络拓扑", "running")
            if lattice:
                r = analyze_network_topology(lattice)
                r["success"] = True
            else:
                r = {"success": False, "error": "需要认知网络实例"}
            _emit_step("execute_result", f"健康度:{r.get('health_score','?')}, 枢纽:{len(r.get('hub_nodes',[]))}个", "done")
            return r

        elif act_type == "mine_patterns":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.knowledge_consolidator import mine_cross_domain_patterns
            _emit_step("execute", "🔍 跨域模式挖掘", "running")
            if lattice:
                r = mine_cross_domain_patterns(lattice)
            else:
                r = {"success": False, "error": "需要认知网络实例"}
            _emit_step("execute_result", f"发现{r.get('count',0)}个跨域模式", "done" if r.get("success") else "error")
            return r

        elif act_type == "implement_requirement":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.software_engineer import implement_requirement
            req = params.get("requirement", params.get("task", ""))
            proj = params.get("project_dir")
            _emit_step("execute", f"🏗️ 软件工程管线: {req[:60]}...", "running")
            r = implement_requirement(req, project_dir=proj, save=True, lattice=lattice)
            n_files = len(r.get('files', []))
            status = "done" if r.get("success") else "error"
            _emit_step("execute_result", f"{'✓' if r.get('success') else '✗'} {n_files}个文件, 调试{r.get('debug_iterations',0)}轮", status)
            return r

        elif act_type == "edit_existing_code":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.software_engineer import edit_existing_file
            fpath = params.get("filepath", params.get("path", ""))
            req = params.get("requirement", params.get("task", ""))
            _emit_step("execute", f"✏️ 增量编辑: {fpath}", "running")
            r = edit_existing_file(fpath, req)
            status = "done" if r.get("success") else "error"
            _emit_step("execute_result", f"{'✓编辑成功' if r.get('success') else '✗编辑失败'}: {fpath}", status)
            return r

        elif act_type == "analyze_codebase":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.codebase_analyzer import analyze_project
            proj = params.get("project_dir", str(WORKSPACE_DIR))
            _emit_step("execute", f"📂 分析代码库: {proj}", "running")
            r = analyze_project(proj)
            r["success"] = True
            _emit_step("execute_result", f"文件:{r.get('stats',{}).get('total_files',0)}, 行:{r.get('stats',{}).get('total_lines',0)}", "done")
            return r

        elif act_type == "surpass":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.surpass_engine import surpass, surpass_code, surpass_reason, surpass_critical
            task = params.get("task", params.get("prompt", ""))
            strategy = params.get("strategy")  # local/cloud/ensemble/iterative/cot
            model = params.get("model")
            _emit_step("execute", f"🚀 超越引擎({strategy or '自动'}): {task[:60]}", "running")
            r = surpass(task, lattice=lattice, force_strategy=strategy, force_model=model)
            status = "done" if r.get("success") else "error"
            strat = r.get("strategy", r.get("task_analysis", {}).get("strategy", "?"))
            dur = r.get("total_duration", r.get("duration", 0))
            _emit_step("execute_result", f"超越引擎({strat}) {'✓' if r.get('success') else '✗'} {dur:.1f}s", status)
            return r

        elif act_type == "zhipu_delegate":
            sys.path.insert(0, str(WORKSPACE_DIR))
            from skills.zhipu_ai_caller import smart_delegate, call_zhipu, generate_code
            task = params.get("task", params.get("prompt", ""))
            task_type = params.get("task_type", "")
            model = params.get("model")
            verify = params.get("verify", True)
            _emit_step("execute", f"🌐 智谱AI委托({task_type or '自动'}): {task[:60]}", "running")
            # 根据是否指定代码生成选择接口
            if task_type == "code_gen":
                language = params.get("language", "python")
                r = generate_code(task, language=language, model=model, verify=verify)
            elif task_type:
                r = call_zhipu(prompt=task, task_type=task_type, model=model, verify_locally=verify)
            else:
                # 收集相关节点作为上下文
                ctx = None
                if lattice:
                    try:
                        related = lattice.find_similar_nodes(task, threshold=0.4, limit=3)
                        if related:
                            ctx = [{"domain": n.get("domain",""), "content": n.get("content","")} for n in related]
                    except:
                        pass
                r = smart_delegate(task, local_context=ctx, force_model=model, verify=verify)
            status = "done" if r.get("success") else "error"
            model_used = r.get("model", "?")
            dur = r.get("duration", 0)
            _emit_step("execute_result", f"智谱AI({model_used}) {'✓' if r.get('success') else '✗'} {dur:.1f}s", status)
            return r

        elif act_type == "cloud_code_generate":
            # ★ 君臣佐使：复杂代码→GLM-5(臣), 简单代码→GLM-4.7(佐), 14B验证(君) ★
            task = params.get("task", params.get("prompt", ""))
            filepath = params.get("filepath", params.get("path", ""))
            do_execute = params.get("execute", True)

            import agi_v13_cognitive_lattice as agi
            zhipu_b = agi.BACKENDS.get("zhipu")
            if not zhipu_b or not zhipu_b.get("api_key"):
                return {"success": False, "error": "智谱API未配置"}

            from openai import OpenAI
            client = OpenAI(api_key=zhipu_b["api_key"], base_url=zhipu_b["base_url"])

            # 确定文件扩展名和语言
            fp = Path(filepath) if filepath else Path("output.py")
            lang = {"py": "Python", "js": "JavaScript", "ts": "TypeScript",
                    "dart": "Dart", "sh": "Shell", "html": "HTML",
                    "rs": "Rust", "go": "Go", "java": "Java", "cs": "C#",
                    "sol": "Solidity", "swift": "Swift", "kt": "Kotlin",
                    "cpp": "C++", "c": "C", "rb": "Ruby", "php": "PHP",
                    "wasm": "WebAssembly(WAT)"}.get(fp.suffix.lstrip('.'), "Python")

            # 君臣佐使路由: 检测代码复杂度决定用臣(GLM-5)还是佐(GLM-4.7)
            task_lower = task.lower()
            complex_kw = ['rust', 'go ', 'golang', 'c#', 'java', '.net', 'wasm',
                          'solidity', '智能合约', '架构', '微服务', '分布式',
                          'unity', 'unreal', 'electron', 'tauri', '跨平台',
                          '编译器', 'compiler', '操作系统', '系统设计', '全栈']
            is_complex = any(k in task_lower for k in complex_kw) or lang not in ("Python", "Shell")
            use_model = "GLM-5" if is_complex else "GLM-4.7"
            role_name = "臣" if is_complex else "佐"
            _emit_step("execute", f"☁ [{role_name}] 云端代码产出({use_model}): {task[:60]}", "running")

            code_prompt = f"""你是一位顶级软件工程师（超越Claude Opus 4.6级别）。请为以下任务生成完整的、可直接运行的{lang}代码。

任务：{task}

要求：
1. 代码必须是完整的、可直接运行的（不是片段）
2. 包含所有必要的import语句
3. 包含错误处理
4. 包含注释说明关键逻辑
5. 如果需要第三方库，在文件顶部注释中注明安装命令
6. 只输出代码，不要其他文字（不要```标记）
7. 如果是Rust/Go/Java/C#等编译型语言，确保代码可直接编译通过"""

            max_rounds = 3
            last_code = ""
            last_error = ""

            for round_i in range(max_rounds):
                _emit_step("execute", f"☁ [{role_name}] 第{round_i+1}轮代码生成({use_model})...", "running")

                if round_i == 0:
                    gen_messages = [
                        {"role": "system", "content": code_prompt},
                        {"role": "user", "content": f"请生成代码，保存到 {filepath}"}
                    ]
                else:
                    gen_messages = [
                        {"role": "system", "content": code_prompt},
                        {"role": "user", "content": f"上一版代码执行出错:\n{last_error}\n\n上一版代码:\n{last_code}\n\n请修复后重新输出完整代码（只输出代码）:"}
                    ]

                try:
                    resp = client.chat.completions.create(
                        model=use_model,
                        max_tokens=8192,
                        temperature=0.2,
                        messages=gen_messages
                    )
                    generated = resp.choices[0].message.content.strip()
                except Exception as e:
                    # 臣失败→佐回退
                    if use_model == "GLM-5":
                        _emit_step("execute", f"GLM-5调用失败，回退GLM-4.7(佐)...", "running")
                        try:
                            resp = client.chat.completions.create(
                                model="GLM-4.7", max_tokens=8192,
                                temperature=0.2, messages=gen_messages)
                            generated = resp.choices[0].message.content.strip()
                            use_model = "GLM-4.7"; role_name = "佐"
                        except Exception as e2:
                            _emit_step("execute_result", f"所有模型调用失败: {e2}", "error")
                            return {"success": False, "error": f"代码生成失败: {e}, {e2}"}
                    else:
                        _emit_step("execute_result", f"{use_model}调用失败: {e}", "error")
                        return {"success": False, "error": f"{use_model}调用失败: {e}"}

                # 清理代码（移除markdown标记）
                if generated.startswith("```"):
                    lines = generated.split("\n")
                    lines = lines[1:]  # 移除 ```python
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    generated = "\n".join(lines)

                last_code = generated

                # 写入文件
                write_result = FileAction.create_file(filepath, generated, f"云端生成: {task[:50]}")
                if not write_result.get("success"):
                    _emit_step("execute_result", f"写入失败: {write_result.get('error')}", "error")
                    return write_result

                actual_path = write_result.get("full_path", filepath)
                _emit_step("execute", f"✓ 代码已写入 {actual_path} ({len(generated)}字符)", "done")

                # 执行验证（仅Python）
                if do_execute and fp.suffix == '.py':
                    _emit_step("execute", f"🔄 执行验证(第{round_i+1}轮)...", "running")
                    exec_result = ExecuteAction.run_python(code=generated)
                    if exec_result.get("success"):
                        _emit_step("execute_result",
                                   f"✓ [{role_name}] 云端代码产出成功({use_model}, {round_i+1}轮) — {actual_path}",
                                   "done")
                        return {
                            "success": True,
                            "path": filepath,
                            "full_path": actual_path,
                            "size": len(generated),
                            "rounds": round_i + 1,
                            "model": use_model,
                            "role": role_name,
                            "stdout": exec_result.get("stdout", ""),
                            "description": f"[{role_name}] 云端代码产出: {task[:50]}"
                        }
                    else:
                        last_error = exec_result.get("stderr", exec_result.get("error", "未知错误"))
                        # 错误分类+智能修复策略
                        try:
                            from error_classifier import classify_error, pre_check_code, repair_history
                            err_info = classify_error(last_error)
                            err_cat = err_info.get("category", "unknown")
                            strategies = err_info.get("strategies", [])
                            repair_prompt = err_info.get("repair_prompt", "")
                            if repair_prompt:
                                last_error = repair_prompt
                            _emit_step("execute", f"✗ 第{round_i+1}轮失败[{err_cat}]，策略: {strategies[0]['name'] if strategies else '通用'}，自修复中...", "running")
                        except Exception:
                            _emit_step("execute", f"✗ 第{round_i+1}轮执行失败，自修复中...", "running")
                        continue
                else:
                    # 非Python或不需执行
                    _emit_step("execute_result",
                               f"✓ [{role_name}] 云端代码已生成并保存({use_model}) — {actual_path}",
                               "done")
                    return {
                        "success": True,
                        "path": filepath,
                        "full_path": actual_path,
                        "size": len(generated),
                        "rounds": 1,
                        "model": use_model,
                        "role": role_name,
                        "description": f"[{role_name}] 云端代码产出: {task[:50]}"
                    }

            # 所有轮次用完仍失败
            _emit_step("execute_result", f"✗ {max_rounds}轮自修复后仍失败", "error")
            return {
                "success": False,
                "path": filepath,
                "full_path": str(Path(filepath).resolve()),
                "error": f"代码生成{max_rounds}轮后仍有错误: {last_error[:200]}",
                "last_code_saved": True,
                "model": "GLM-4.7"
            }

        else:
            return {"success": False, "error": f"未知高级动作: {act_type}"}

    except ImportError as e:
        _emit_step("execute_result", f"技能加载失败: {e}", "error")
        return {"success": False, "error": f"技能加载失败: {e}"}
    except Exception as e:
        _emit_step("execute_result", f"执行异常: {e}", "error")
        return {"success": False, "error": str(e)}


# 高级动作列表
ADVANCED_ACTIONS = {
    "code_synthesize", "web_research", "reasoning_chain",
    "verify_claim", "forge_tool", "learn_topic",
    "analyze_network", "mine_patterns",
    "implement_requirement", "edit_existing_code", "analyze_codebase",
    "zhipu_delegate", "surpass", "cloud_code_generate"
}


def execute_action_plan(actions, lattice=None):
    """执行动作计划，返回每步结果"""
    results = []
    _emit_step("plan_start", f"开始执行动作计划: {len(actions)} 个步骤", "running")

    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            continue

        act_type = action.get("action", "")
        params = action.get("params", {})
        reasoning = action.get("reasoning", "")

        _emit_step("plan_step", f"[{i+1}/{len(actions)}] {act_type}: {reasoning}", "running")

        if act_type in ADVANCED_ACTIONS:
            r = _dispatch_advanced_action(act_type, params, lattice)
        elif act_type == "create_file":
            r = FileAction.create_file(
                params.get("path", "untitled.txt"),
                params.get("content", ""),
                params.get("description", "")
            )
        elif act_type == "execute_python":
            if "filepath" in params:
                r = ExecuteAction.run_python(filepath=params["filepath"])
            else:
                r = ExecuteAction.run_python(code=params.get("code", "print('hello')"))
        elif act_type == "build_skill":
            r = SkillBuilder.build_skill(
                params.get("name", "unnamed"),
                params.get("description", ""),
                params.get("code", ""),
                params.get("tags", [])
            )
        elif act_type == "read_file":
            r = FileAction.read_file(params.get("path", ""))
        else:
            r = {"success": False, "error": f"未知动作: {act_type}"}

        results.append({
            "step": i + 1,
            "action": act_type,
            "reasoning": reasoning,
            "result": r
        })

    _emit_step("plan_done", f"动作计划执行完成: {len(results)} 步", "done")
    return results


# ==================== F6: 能力缺口规则检测器 ====================
# 关键词+模式匹配检测能力缺口，比纯LLM判断更可靠

CAPABILITY_RULES = [
    # (规则名, 关键词列表, 所需能力, 当前状态, 建议动作)
    {
        "name": "web_search",
        "keywords": ["搜索", "最新", "新闻", "实时", "当前", "今天", "search", "latest", "current"],
        "capability": "Web搜索/实时信息获取",
        "status": "需API Key",
        "fix": "配置Google/Bing搜索API Key → H1",
        "fixable_by_code": False,
    },
    {
        "name": "image_generation",
        "keywords": ["画图", "生成图片", "图像", "image", "draw", "render", "渲染"],
        "capability": "图像生成",
        "status": "未实现",
        "fix": "集成DALL-E/Stable Diffusion API",
        "fixable_by_code": True,
    },
    {
        "name": "audio_processing",
        "keywords": ["语音", "音频", "音乐", "speech", "audio", "voice", "TTS", "ASR"],
        "capability": "语音/音频处理",
        "status": "未实现",
        "fix": "集成Whisper/TTS模型",
        "fixable_by_code": True,
    },
    {
        "name": "video_processing",
        "keywords": ["视频", "video", "播放", "剪辑"],
        "capability": "视频处理",
        "status": "未实现",
        "fix": "集成FFmpeg/视频模型",
        "fixable_by_code": True,
    },
    {
        "name": "database_query",
        "keywords": ["MySQL", "PostgreSQL", "MongoDB", "数据库查询", "SQL查询", "远程数据库"],
        "capability": "外部数据库连接",
        "status": "仅SQLite",
        "fix": "添加数据库连接器技能模块",
        "fixable_by_code": True,
    },
    {
        "name": "plc_control",
        "keywords": ["PLC", "DCS", "梯形图", "工控", "SCADA", "HMI", "工业控制"],
        "capability": "工业控制系统编程",
        "status": "未实现",
        "fix": "需工控编程专业人员 → H8",
        "fixable_by_code": False,
    },
    {
        "name": "real_hardware",
        "keywords": ["传感器", "热电偶", "采集卡", "GPIO", "Arduino", "树莓派", "硬件连接"],
        "capability": "硬件设备接口",
        "status": "未实现",
        "fix": "需硬件驱动集成",
        "fixable_by_code": False,
    },
    {
        "name": "3d_visualization",
        "keywords": ["3D可视化", "3D渲染", "WebGL", "三维显示", "CAD预览"],
        "capability": "3D在线可视化",
        "status": "仅文件生成",
        "fix": "集成Three.js/CadQuery Viewer前端",
        "fixable_by_code": True,
    },
    {
        "name": "multi_language_code",
        "keywords": ["Dart代码", "Kotlin代码", "Swift代码", "Java代码", "C++代码", "Rust代码"],
        "capability": "多语言代码生成+验证",
        "status": "仅Python验证",
        "fix": "扩展tool_controller支持多语言运行时 → F16",
        "fixable_by_code": True,
    },
    {
        "name": "email_send",
        "keywords": ["发邮件", "发送邮件", "email", "SMTP"],
        "capability": "邮件发送",
        "status": "未实现",
        "fix": "添加SMTP技能模块",
        "fixable_by_code": True,
    },
    {
        "name": "pdf_processing",
        "keywords": ["PDF", "pdf解析", "PDF生成", "pdf文件"],
        "capability": "PDF处理",
        "status": "未实现",
        "fix": "集成PyPDF2/reportlab",
        "fixable_by_code": True,
    },
    {
        "name": "deployment",
        "keywords": ["部署", "Docker", "K8s", "Kubernetes", "CI/CD", "上线", "发布"],
        "capability": "自动化部署",
        "status": "未实现",
        "fix": "添加Docker/K8s部署技能",
        "fixable_by_code": True,
    },
]


def detect_capability_gaps(question: str, action_results: list = None) -> list:
    """F6: 基于规则检测能力缺口
    
    Args:
        question: 用户问题/任务描述
        action_results: 动作执行结果(可选，用于检测执行失败)
    
    Returns:
        检测到的能力缺口列表
    """
    gaps = []
    q_lower = question.lower()
    
    # 规则1: 关键词匹配
    for rule in CAPABILITY_RULES:
        for kw in rule["keywords"]:
            if kw.lower() in q_lower:
                gaps.append({
                    "rule": rule["name"],
                    "capability": rule["capability"],
                    "status": rule["status"],
                    "fix": rule["fix"],
                    "fixable_by_code": rule["fixable_by_code"],
                    "matched_keyword": kw,
                    "source": "keyword_match",
                })
                break  # 每条规则只匹配一次
    
    # 规则2: 执行失败分析
    if action_results:
        for r in action_results:
            result = r.get("result", {})
            if not result.get("success"):
                error = result.get("error", "")
                # ImportError → 缺少依赖
                if "ImportError" in error or "ModuleNotFoundError" in error:
                    module = re.search(r"No module named '(\w+)'", error)
                    mod_name = module.group(1) if module else "unknown"
                    gaps.append({
                        "rule": "missing_module",
                        "capability": f"Python模块: {mod_name}",
                        "status": "未安装",
                        "fix": f"pip install {mod_name}",
                        "fixable_by_code": True,
                        "source": "execution_failure",
                    })
                # 超时 → 可能需要更强算力
                elif "超时" in error or "timeout" in error.lower():
                    gaps.append({
                        "rule": "compute_limit",
                        "capability": "更长执行时间/更强算力",
                        "status": "当前超时30s",
                        "fix": "增加超时时间或委托智谱API",
                        "fixable_by_code": True,
                        "source": "execution_failure",
                    })
    
    # 去重
    seen = set()
    unique_gaps = []
    for g in gaps:
        key = g["rule"]
        if key not in seen:
            seen.add(key)
            unique_gaps.append(g)
    
    if unique_gaps:
        _emit_step("capability_gap", 
                    f"🔍 检测到 {len(unique_gaps)} 个能力缺口: " + 
                    ", ".join(g["capability"] for g in unique_gaps), "warning")
    
    return unique_gaps


def action_to_nodes(results, lattice):
    """将动作执行结果转化为认知网络节点"""
    new_nodes = []
    for r in results:
        if not r["result"].get("success"):
            continue

        act = r["action"]
        if act == "create_file":
            content = f"已创建文件 {r['result'].get('path', '?')}: {r['reasoning']}"
            nid = lattice.add_node(content, "实践产出", "proven", source="action_engine", silent=True)
            if nid:
                new_nodes.append({"id": nid, "content": content})

        elif act == "execute_python":
            stdout = r["result"].get("stdout", "")[:200]
            content = f"执行验证: {r['reasoning']} → 结果: {stdout}"
            nid = lattice.add_node(content, "执行验证", "proven", source="action_engine", silent=True)
            if nid:
                new_nodes.append({"id": nid, "content": content})

        elif act == "build_skill":
            content = f"技能构建: {r['reasoning']}"
            nid = lattice.add_node(content, "技能", "proven", source="skill_builder", silent=True)
            if nid:
                new_nodes.append({"id": nid, "content": content})

    if new_nodes:
        _emit_step("nodes_feedback", f"动作结果已反馈为 {len(new_nodes)} 个新节点", "done")
    return new_nodes
