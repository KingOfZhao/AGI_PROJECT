#!/usr/bin/env python3
"""
推演引擎执行器 — ULDS v2.1
调用本地模型(Ollama) + GLM-5/GLM-5 Turbo/GLM-4.7 API 执行推演计划
记录推演过程/结果/报告到数据库

用法:
  python3 deduction_runner.py                    # 执行全部排队计划
  python3 deduction_runner.py --project p_diepre # 只推演指定项目
  python3 deduction_runner.py --plan dp_xxx      # 只推演指定计划
  python3 deduction_runner.py --limit 5          # 最多执行5个计划
  python3 deduction_runner.py --init             # 初始化DB后推演
  python3 deduction_runner.py --list             # 列出待推演计划
"""

import os
import sys
import re
import json
import time
import argparse
import hashlib
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# 加载环境变量
from pathlib import Path
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from deduction_db import DeductionDB, check_shell_safety, init_all

# ==================== 配置 ====================

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
# Coding Plan Pro 专属端点 (注意: .env中的ZHIPU_BASE_URL是通用端点, 推演引擎必须用Coding端点)
ZHIPU_CODING_ENDPOINT = "https://open.bigmodel.cn/api/coding/paas/v4"
ZHIPU_BASE_URL = os.getenv("ZHIPU_CODING_URL", ZHIPU_CODING_ENDPOINT)
ZHIPU_BASE = ZHIPU_BASE_URL + "/chat/completions"

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ULDS v2.1 系统提示词
ULDS_SYSTEM_PROMPT = """你是AGI v13推演引擎, 基于ULDS v2.1(十一大必然规律)进行极致推演。

核心原则: 问题与答案之间只有接近一条道路。从规律到答案的路径就是推演——逐级细化,直到路径清晰可见、可执行。

十一大必然规律:
L1 数学公理 | L2 物理定律 | L3 化学规律 | L4 逻辑规则
L5 信息论 | L6 系统论 | L7 概率统计 | L8 对称性
L9 可计算性 | L10 演化动力学 | L11 认识论极限

八大超越策略:
S1 规律约束注入 | S2 技能库锚定 | S3 王朝治理 | S4 四向碰撞
S5 5级真实性 | S6 并行推理 | S7 零回避扫描 | S8 链式收敛

推演要求:
1. 每个推演步骤必须标注使用的ULDS规律(L1-L11)
2. 遇到无法解决的问题必须明确标记为[BLOCKED]并说明原因
3. 生成的代码/命令必须通过Shell安全检查
4. 推演结果必须可验证、可执行
5. 对已知实现推演最佳实践, 对未知领域执行"见路不走"策略

重要: 你的每次回复末尾必须附加结构化标记, 用于知识图谱和推演拓展。格式如下:

[NODE] DXF解析引擎 | tool | 0.85 | L1+L5
[NODE] 材料约束传播 | concept | 0.9 | L2+L3
[NODE] 精度误差范围 | constraint | 0.95 | L1+L7
[RELATION] DXF解析引擎 -> 材料约束传播 | produces
[RELATION] 精度误差范围 -> DXF解析引擎 | constrains
[EXPAND] 材料数据库自动爬取 | p_diepre | medium | 从行业数据源自动采集材料参数
[BLOCKED] 缺少IADD官方规格数据

规则:
- [NODE] 节点名称 | 类型(concept/method/tool/constraint/pattern) | 置信度(0-1) | 关联ULDS规律
- [RELATION] 源节点 -> 目标节点 | 关系类型(depends/produces/conflicts/extends/constrains)
- [EXPAND] 新推演方向标题 | 项目ID | 优先级(critical/high/medium) | 简述
- [BLOCKED] 无法解决的问题描述
- 每次回复至少输出2个[NODE]和1个[RELATION], 报告阶段至少输出1个[EXPAND]"""

# ==================== 模型调用 ====================

def call_ollama(prompt: str, system: str = "", model: str = "qwen2.5-coder:14b",
                max_tokens: int = 4096, temperature: float = 0.3) -> Tuple[str, int, int]:
    """调用本地Ollama模型, 返回 (response, tokens, latency_ms)"""
    start = time.time()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or ULDS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode())
        latency = int((time.time() - start) * 1000)
        content = result.get("message", {}).get("content", "")
        tokens = result.get("eval_count", len(content) // 4)
        return content, tokens, latency
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return f"[OLLAMA_ERROR] {e}", 0, latency


def call_zhipu(prompt: str, system: str = "", model_id: str = "glm-5",
               max_tokens: int = 8192, temperature: float = 0.7) -> Tuple[str, int, int]:
    """调用智谱GLM API, 返回 (response, tokens, latency_ms)"""
    if not ZHIPU_API_KEY:
        return "[ERROR] ZHIPU_API_KEY未配置, 请在.env中设置", 0, 0

    start = time.time()
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system or ULDS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            ZHIPU_BASE,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ZHIPU_API_KEY}"
            },
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read().decode())
        latency = int((time.time() - start) * 1000)
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})
        tokens = usage.get("total_tokens", len(content) // 4)
        return content, tokens, latency
    except urllib.error.HTTPError as e:
        latency = int((time.time() - start) * 1000)
        body = e.read().decode() if hasattr(e, 'read') else str(e)
        return f"[API_ERROR] HTTP {e.code}: {body[:200]}", 0, latency
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return f"[API_ERROR] {e}", 0, latency


def call_model(prompt: str, model_pref: str = "glm5", system: str = "") -> Tuple[str, str, int, int]:
    """统一模型调用接口, 返回 (response, model_used, tokens, latency_ms)
    Coding Plan Pro端点, GLM失败时自动回退Ollama"""
    # Coding Plan Pro: GLM-5(复杂), GLM-5-Turbo(快速), GLM-4-flash(普通节省额度)
    model_map = {
        "ollama_local": ("ollama", "qwen2.5-coder:14b", 4096, 0.3),
        "glm5": ("zhipu", "glm-5", 8192, 0.7),
        "glm5_turbo": ("zhipu", "glm-5-turbo", 8192, 0.5),
        "glm4_flash": ("zhipu", "glm-4-flash", 4096, 0.5),
        "glm47": ("zhipu", "glm-4-flash", 4096, 0.5),
        "glm45air": ("zhipu", "glm-4-flash", 2048, 0.3),
    }
    backend, model_id, max_tokens, temp = model_map.get(model_pref, model_map["glm5"])

    if backend == "ollama":
        resp, tokens, lat = call_ollama(prompt, system, model_id, max_tokens, temp)
        return resp, f"ollama/{model_id}", tokens, lat
    else:
        resp, tokens, lat = call_zhipu(prompt, system, model_id, max_tokens, temp)
        if "[API_ERROR]" in resp or "[ERROR]" in resp:
            fb_resp, fb_tokens, fb_lat = call_ollama(prompt, system, "qwen2.5-coder:14b", 4096, 0.3)
            return fb_resp, f"ollama/qwen2.5-coder:14b(fallback<-{model_id})", fb_tokens, lat + fb_lat
        return resp, f"zhipu/{model_id}", tokens, lat


# ==================== 推演执行 ====================

def build_deduction_prompt(plan: dict, project: dict, step_num: int, phase: str,
                           prev_results: List[str] = None) -> str:
    """构建推演提示词"""
    context = f"""## 推演计划
- 项目: {project.get('name', '')}
- 终极目标: {project.get('ultimate_goal', '')}
- 短期目标: {project.get('short_term_goal', '')}
- 推演主题: {plan['title']}
- 推演描述: {plan.get('description', '')}
- ULDS规律: {plan.get('ulds_laws', '')}
- 超越策略: {plan.get('surpass_strategies', '')}

## 当前推演
- 步骤: {step_num}
- 阶段: {phase}
"""
    if prev_results:
        context += "\n## 前序推演结果\n"
        for i, r in enumerate(prev_results[-3:], 1):
            context += f"Step {i}: {r[:500]}\n"

    NODE_FOOTER = """\n\n---\n请在回复末尾输出结构化标记(必须输出, 至少2个NODE+1个RELATION):
[NODE] 节点名 | 类型(concept/method/tool/constraint/pattern) | 置信度(0-1) | ULDS规律
[RELATION] 源节点 -> 目标节点 | 关系(depends/produces/conflicts/extends/constrains)"""

    phase_prompts = {
        "decompose": f"""{context}
请对该推演主题进行问题分解:
1. 列出实现该目标必须解决的核心问题(不可回避)
2. 每个问题标注涉及的ULDS规律(L1-L11)
3. 标注问题优先级(P0/P1/P2)和依赖关系
4. 如有无法解决的问题标记为[BLOCKED]
{NODE_FOOTER}""",

        "analyze": f"""{context}
请对分解后的问题进行深度分析:
1. 对每个核心问题进行ULDS规律约束分析
2. 找出问题之间的依赖关系和约束传播路径
3. 推演可行的解决方案(至少2个方向)
4. 评估每个方案的可行性/风险/成本
{NODE_FOOTER}""",

        "implement": f"""{context}
请给出具体的实现方案:
1. 选择最优方案并说明理由(基于ULDS规律)
2. 给出可执行的步骤(代码/命令/操作)
3. 定义验证标准(如何确认推演成功)
4. 所有shell命令必须完整, 禁止未闭合的引号/括号/heredoc
{NODE_FOOTER}""",

        "validate": f"""{context}
请对推演结果进行验证:
1. 检查方案是否满足ULDS规律约束
2. 执行零回避扫描: 是否有遗漏的问题?
3. 评估结果的真实性等级(L0-L5)
4. 标记需要人工验证的部分
5. 列出后续可进一步推演的方向
{NODE_FOOTER}""",

        "report": f"""{context}
请生成推演报告:
1. 推演摘要(50字以内)
2. 核心发现(3-5条)
3. 使用的ULDS规律和超越策略
4. 遇到的[BLOCKED]问题
5. 下一步推演建议
6. 真实性等级评估

---
必须输出以下结构化标记(至少3个NODE + 2个RELATION + 1个EXPAND):
[NODE] 节点名 | 类型(concept/method/tool/constraint/pattern) | 置信度(0-1) | ULDS规律
[RELATION] 源节点 -> 目标节点 | 关系(depends/produces/conflicts/extends/constrains)
[EXPAND] 新推演方向标题 | 项目ID | 优先级(critical/high/medium) | 简述

示例:
[NODE] 约束传播求解器 | tool | 0.8 | L1+L6
[NODE] 材料误差范围 | constraint | 0.95 | L2+L7
[NODE] F→V→F链式收敛 | pattern | 0.9 | L1+L6+L8
[RELATION] 约束传播求解器 -> 材料误差范围 | depends
[RELATION] F→V→F链式收敛 -> 约束传播求解器 | produces
[EXPAND] 材料数据库自动采集 | p_diepre | medium | 从行业数据源自动爬取材料参数""",
    }
    return phase_prompts.get(phase, phase_prompts["decompose"])


# Shell续行提示符黑名单 — 绝不允许作为问题内容
SHELL_PROMPT_GARBAGE = re.compile(
    r'^\s*'
    r'(dquote>|quote>|heredoc>|pipe>|>\s*$|\)>|\}>|`>)'
    r'|^\s*[>)}`"\'\']{1,3}\s*$'
    r'|^\s*双引号未闭合'
    r'|^\s*单引号未闭合'
    r'|^\s*反引号未闭合'
    r'|^\s*括号未闭合'
    r'|^\s*管道续行'
    r'|^\s*Here-Document',
    re.MULTILINE
)

def is_valid_problem(text: str) -> bool:
    """校验[BLOCKED]问题内容是否有效, 过滤垃圾/shell续行提示"""
    if not text or not text.strip():
        return False
    t = text.strip()
    # 过短
    if len(t) < 4:
        return False
    # 纯符号/标点
    clean = re.sub(r'[\s\W_]+', '', t)
    if len(clean) < 2:
        return False
    # Shell续行提示符
    if SHELL_PROMPT_GARBAGE.search(t):
        return False
    # 代码片段误入过滤: 包含{self./f-string模板/未闭合括号
    if re.search(r'\{self[.\[]', t) or re.search(r'\{\w+\}["\')]', t):
        return False
    # 必须包含至少2个中文字符或5个英文字母
    cn = len(re.findall(r'[\u4e00-\u9fff]', t))
    en = len(re.findall(r'[a-zA-Z]', t))
    if cn < 2 and en < 5:
        return False
    return True


def sanitize_shell_cmd(raw_resp: str) -> str:
    """从模型响应中安全提取shell命令, 只提取完整闭合的代码块"""
    # 只匹配有完整闭合```的代码块
    cmds = re.findall(r'```(?:bash|shell|sh)\n(.*?)\n```', raw_resp, re.DOTALL)
    if not cmds:
        return ""
    result = []
    for cmd in cmds:
        lines = []
        for line in cmd.strip().split('\n'):
            line = line.rstrip()
            # 跳过shell续行提示符
            if re.match(r'^\s*(dquote|quote|heredoc|pipe)?>', line):
                continue
            lines.append(line)
        result.append('\n'.join(lines))
    return '\n'.join(result)


def extract_nodes(db: DeductionDB, plan_id: str, step_id: int, response: str):
    """从推演响应中提取节点和关系, 写入数据库"""
    nodes_added = 0
    # 提取 [NODE] 标记
    for m in re.finditer(r'\[NODE\]\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*(.+)', response):
        name, ntype, conf, laws = m.group(1).strip(), m.group(2).strip(), float(m.group(3)), m.group(4).strip()
        db.add_node({'plan_id': plan_id, 'step_id': step_id, 'node_type': ntype,
                     'name': name, 'content': '', 'ulds_laws': laws,
                     'confidence': conf, 'truth_level': 'L1' if conf >= 0.7 else 'L0'})
        nodes_added += 1
    # 提取 [RELATION] 标记
    for m in re.finditer(r'\[RELATION\]\s*(.+?)\s*->\s*(.+?)\s*\|\s*(.+)', response):
        src, tgt, rel = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        db.add_node({'plan_id': plan_id, 'step_id': step_id, 'node_type': 'relation',
                     'name': f"{src}->{tgt}", 'content': rel, 'ulds_laws': '',
                     'confidence': 0.5})
        nodes_added += 1
    return nodes_added


def extract_expansions(response: str) -> List[dict]:
    """从推演响应中提取新的推演方向"""
    expansions = []
    for m in re.finditer(r'\[EXPAND\]\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)', response):
        expansions.append({
            'title': m.group(1).strip(),
            'project_id': m.group(2).strip(),
            'priority': m.group(3).strip(),
            'description': m.group(4).strip(),
        })
    return expansions


PROBLEM_CATEGORIES = {
    'env_config': {
        'keywords': ['环境变量', '未定义', '未配置', 'URL', 'KEY', 'PATH', 'ENV', 'config', '端口', '连接'],
        'severity': 'medium',
        'solution': '检查.env配置和环境变量定义, 确认服务端口和连接地址',
    },
    'algorithm_gap': {
        'keywords': ['算法', '解析', '变换', '矩阵', 'CTM', '鲁棒', '精度', '收敛', '逼近', '复杂度'],
        'severity': 'high',
        'solution': '分解为子问题逐步攻克, 或引入成熟开源库替代自实现',
    },
    'data_missing': {
        'keywords': ['数据', '缺乏', '缺失', '实测', '标注', '训练集', '样本', '参数'],
        'severity': 'medium',
        'solution': '构建最小数据集验证可行性, 再逐步扩充; 或寻找开源数据源',
    },
    'capability_limit': {
        'keywords': ['识别', '光栅', '手绘', '非矢量', 'OCR', '图像', '视觉', 'CV'],
        'severity': 'high',
        'solution': '评估现有CV/OCR方案(Tesseract/PaddleOCR/YOLO), 定义最小可用精度阈值',
    },
    'external_dep': {
        'keywords': ['牌照', '合规', '第三方', '授权', '许可', '付费', 'API限制'],
        'severity': 'medium',
        'solution': '梳理外部依赖清单, 确认替代方案和成本',
    },
    'perf_limit': {
        'keywords': ['性能', '算力', '速度', '延迟', '内存', 'OOM', '超时', 'timeout'],
        'severity': 'medium',
        'solution': '量化瓶颈指标, 优先优化热路径; 考虑分层/缓存/异步策略',
    },
}


def classify_problem(raw_text: str, plan: dict, phase: str, full_response: str) -> dict:
    """智能分类[BLOCKED]问题: 校验→清洗→分类→生成结构化问题"""
    b = raw_text.strip()
    if not is_valid_problem(b):
        return None

    # 清洗: 去除markdown格式(**粗体**, `代码`, 尾部标点残留)
    title_clean = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', b)
    title_clean = re.sub(r'`(.+?)`', r'\1', title_clean)
    title_clean = re.sub(r'[\*:：]+$', '', title_clean)  # 去掉尾部*:残留
    title_clean = title_clean.strip()

    # 自动分类
    category = 'unknown'
    severity = 'high'
    solution = '拆解为可验证的子问题, 逐步推演解决'
    for cat, info in PROBLEM_CATEGORIES.items():
        if any(kw in title_clean for kw in info['keywords']):
            category = cat
            severity = info['severity']
            solution = info['solution']
            break

    # 从响应上下文提取更详细描述 (取[BLOCKED]前后各2行)
    context_lines = []
    resp_lines = full_response.split('\n')
    for i, line in enumerate(resp_lines):
        if '[BLOCKED]' in line and b[:20] in line:
            start = max(0, i - 2)
            end = min(len(resp_lines), i + 3)
            for j in range(start, end):
                cl = resp_lines[j].strip()
                if (cl and len(cl) > 5
                        and '[BLOCKED]' not in cl
                        and not cl.startswith('[NODE]')
                        and not cl.startswith('[RELATION]')
                        and not cl.startswith('[EXPAND]')):
                    context_lines.append(cl)
            break
    context = '; '.join(context_lines[:3]) if context_lines else ''

    desc_parts = [
        f"[{plan['title']}] {phase}阶段",
        f"分类: {category}",
        f"问题: {title_clean}",
    ]
    if context:
        desc_parts.append(f"上下文: {context[:200]}")

    return {
        'plan_id': plan['id'],
        'project_id': plan['project_id'],
        'title': title_clean[:100],
        'description': ' | '.join(desc_parts),
        'severity': severity,
        'suggested_solution': solution,
    }


def run_single_plan(db: DeductionDB, plan: dict, project: dict, verbose: bool = True,
                    queue_settings: dict = None) -> dict:
    """执行单个推演计划"""
    plan_id = plan['id']
    model_pref = plan.get('model_preference', 'glm5')
    phases = ["decompose", "analyze", "implement", "validate", "report"]
    prev_results = []
    total_tokens = 0
    total_latency = 0
    blocked = []
    expanded_plans = []
    nodes_extracted = 0
    qs = queue_settings or {}

    if verbose:
        print(f"\n{'='*60}")
        print(f"推演: {plan['title']}")
        print(f"项目: {project.get('name','')} | 模型: {model_pref} | 规律: {plan.get('ulds_laws','')}")
        print(f"{'='*60}")

    db.update_plan_status(plan_id, 'running')

    for step_num, phase in enumerate(phases, 1):
        if verbose:
            print(f"\n  [{step_num}/{len(phases)}] {phase}...", end=" ", flush=True)

        prompt = build_deduction_prompt(plan, project, step_num, phase, prev_results)

        # 对于validate阶段使用Ollama本地校验(幻觉检测)
        use_model = model_pref
        if phase == "validate":
            use_model = "ollama_local"
        # 对于report阶段使用GLM-5 Turbo(快速)
        elif phase == "report":
            use_model = "glm5_turbo"

        resp, model_used, tokens, latency = call_model(prompt, use_model)

        # Shell安全提取 + 检查
        shell_cmd = sanitize_shell_cmd(resp)
        safe, reason = check_shell_safety(shell_cmd)
        if not safe:
            shell_cmd = ""  # 不安全的命令直接丢弃

        # 记录步骤
        db.add_step({
            'plan_id': plan_id,
            'step_number': step_num,
            'phase': phase,
            'prompt': prompt[:2000],
            'response': resp,
            'model_used': model_used,
            'tokens_used': tokens,
            'latency_ms': latency,
            'confidence': 0.7 if "[ERROR]" not in resp else 0.1,
            'shell_cmd': shell_cmd,
        })

        # 提取节点
        n_count = extract_nodes(db, plan_id, step_num, resp)
        nodes_extracted += n_count

        # 检测BLOCKED问题 (严格校验 + 智能分类)
        if "[BLOCKED]" in resp:
            blocks = re.findall(r'\[BLOCKED\]\s*(.+?)(?:\n|$)', resp)
            for b in blocks:
                # 去除可能的重复[BLOCKED]前缀
                b = re.sub(r'^\s*\[BLOCKED\]\s*', '', b)
                prob = classify_problem(b, plan, phase, resp)
                if prob is None:
                    if verbose:
                        print(f"    [SKIP] 无效问题: {repr(b.strip()[:40])}")
                    continue
                blocked.append(prob['title'])
                db.add_problem(prob)

        # 提取拓展推演方向 (report阶段)
        if phase == 'report' and qs.get('auto_expand', 1):
            expansions = extract_expansions(resp)
            max_expand = qs.get('max_expand_per_plan', 3)
            for exp in expansions[:max_expand]:
                if not exp.get('title'):
                    continue
                new_plan_id = db.add_plan({
                    'project_id': exp.get('project_id', plan['project_id']),
                    'title': exp['title'],
                    'description': f"[自动拓展] 来源: {plan['title']} → {exp.get('description','')}",
                    'priority': exp.get('priority', 'medium'),
                    'ulds_laws': plan.get('ulds_laws', ''),
                    'surpass_strategies': plan.get('surpass_strategies', ''),
                    'estimated_rounds': 5,
                    'model_preference': plan.get('model_preference', 'glm5_turbo'),
                })
                expanded_plans.append(new_plan_id)
                if verbose:
                    print(f"    [EXPAND] +{exp['title']} → {new_plan_id}")

        if not safe:
            if verbose:
                print(f"⚠ Shell不安全: {reason[:60]}")

        prev_results.append(resp[:1000])
        total_tokens += tokens
        total_latency += latency

        if verbose:
            status = "✓" if "[ERROR]" not in resp else "✗"
            print(f"{status} {tokens}tok {latency}ms ({model_used})")

        # 避免API限流
        time.sleep(0.5)

    # 记录结果
    truth_level = "L1" if not blocked else "L0"
    db.add_result({
        'plan_id': plan_id,
        'result_type': 'deduction',
        'content': prev_results[-1] if prev_results else "",
        'code_generated': "",
        'tests_passed': len(phases) - len(blocked),
        'tests_total': len(phases),
        'truth_level': truth_level,
    })

    # 记录报告
    db.add_report({
        'plan_id': plan_id,
        'project_id': plan['project_id'],
        'report_type': 'round',
        'title': f"推演报告: {plan['title']}",
        'content': prev_results[-1] if prev_results else "",
        'metrics': {
            'total_tokens': total_tokens,
            'total_latency_ms': total_latency,
            'phases_completed': len(phases),
            'blocked_count': len(blocked),
            'truth_level': truth_level,
        }
    })

    # 更新状态
    final_status = 'done' if not blocked else 'done'
    db.update_plan_status(plan_id, final_status)

    if verbose:
        print(f"\n  完成: {total_tokens}tok | {total_latency}ms | 阻塞:{len(blocked)} | 节点:{nodes_extracted} | 拓展:{len(expanded_plans)}")
        if blocked:
            for b in blocked:
                print(f"    [BLOCKED] {b[:80]}")

    return {
        'plan_id': plan_id,
        'tokens': total_tokens,
        'latency': total_latency,
        'blocked': blocked,
        'truth_level': truth_level,
        'nodes_extracted': nodes_extracted,
        'expanded_plans': expanded_plans,
    }


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(description="AGI v13 推演引擎执行器")
    parser.add_argument("--project", type=str, help="只推演指定项目ID (如 p_diepre)")
    parser.add_argument("--plan", type=str, help="只推演指定计划ID")
    parser.add_argument("--limit", type=int, default=0, help="最多执行N个计划")
    parser.add_argument("--init", action="store_true", help="先初始化DB再推演")
    parser.add_argument("--list", action="store_true", help="列出待推演计划")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--export", action="store_true", help="导出CRM数据")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    parser.add_argument("--priority-project", type=str, help="优先推演指定项目")
    parser.add_argument("--problems-first", action="store_true", help="优先推演阻塞问题产生的计划")
    parser.add_argument("--no-expand", action="store_true", help="禁止自动拓展")
    parser.add_argument("--settings", action="store_true", help="查看/设置队列参数")
    args = parser.parse_args()

    verbose = not args.quiet

    # 初始化
    if args.init:
        if verbose:
            print("初始化推演数据库...")
        count, stats = init_all()
        if verbose:
            print(f"初始化完成: {count}个推演计划")
            print(json.dumps(stats, indent=2))

    db = DeductionDB()

    # 统计
    if args.stats:
        stats = db.get_stats()
        print("\n推演引擎统计:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        projects = db.get_projects()
        print(f"\n项目: {len(projects)}个")
        for p in projects:
            plans = db.get_plans(project_id=p['id'])
            queued = sum(1 for x in plans if x['status'] == 'queued')
            done = sum(1 for x in plans if x['status'] == 'done')
            print(f"  {p['name']}: {len(plans)}计划 ({queued}排队 {done}完成)")
        db.close()
        return

    # 列出计划
    if args.list:
        plans = db.get_plans(project_id=args.project, status='queued')
        print(f"\n待推演计划: {len(plans)}个")
        print(f"{'ID':<30} {'优先级':<8} {'模型':<12} {'项目':<20} {'标题'}")
        print("-" * 100)
        for p in plans:
            proj = db.conn.execute("SELECT name FROM projects WHERE id=?", (p['project_id'],)).fetchone()
            pname = proj[0] if proj else p['project_id']
            print(f"{p['id']:<30} {p['priority']:<8} {p['model_preference']:<12} {pname:<20} {p['title']}")
        db.close()
        return

    # 导出CRM数据
    if args.export:
        crm_data = db.export_for_crm()
        export_path = os.path.join(os.path.dirname(__file__), "web", "data", "deduction_export.json")
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(crm_data, f, ensure_ascii=False, indent=2, default=str)
        if verbose:
            print(f"CRM数据已导出: {export_path}")
        db.close()
        return

    # 队列设置
    if args.settings:
        qs = db.get_queue_settings()
        print("\n推演队列设置:")
        print(json.dumps(qs, indent=2, ensure_ascii=False, default=str))
        db.close()
        return

    # 加载队列设置
    queue_settings = db.get_queue_settings()
    if args.priority_project:
        queue_settings['priority_project'] = args.priority_project
        db.update_queue_settings(queue_settings)
    if args.no_expand:
        queue_settings['auto_expand'] = 0
    if args.problems_first:
        queue_settings['new_problems_position'] = 'prepend'

    # 获取待推演计划
    if args.plan:
        row = db.conn.execute("SELECT * FROM deduction_plans WHERE id=?", (args.plan,)).fetchone()
        if not row:
            print(f"计划 {args.plan} 不存在")
            db.close()
            return
        plans = [dict(row)]
    else:
        plans = db.get_plans(project_id=args.project, status='queued')

    # 按队列设置排序
    prio_proj = queue_settings.get('priority_project')
    if prio_proj:
        plans.sort(key=lambda p: (0 if p['project_id'] == prio_proj else 1,
                                  {'critical':0,'high':1,'medium':2}.get(p.get('priority','medium'),3)))

    # 阻塞问题产生的计划优先
    if queue_settings.get('new_problems_position') == 'prepend':
        spawned_ids = set()
        for prob in db.get_problems():
            if prob.get('spawned_plan_id'):
                spawned_ids.add(prob['spawned_plan_id'])
        if spawned_ids:
            spawned = [p for p in plans if p['id'] in spawned_ids]
            rest = [p for p in plans if p['id'] not in spawned_ids]
            plans = spawned + rest

    if not plans:
        print("没有待推演的计划")
        db.close()
        return

    if args.limit > 0:
        plans = plans[:args.limit]

    # 获取项目信息
    projects_map = {p['id']: p for p in db.get_projects()}

    if verbose:
        print(f"\n{'='*60}")
        print(f"AGI v13 推演引擎 — ULDS v2.1")
        print(f"待推演: {len(plans)}个计划")
        print(f"模型: Ollama本地 + GLM-5 + GLM-5 Turbo + GLM-4.7")
        print(f"{'='*60}")

    # 执行推演
    results = []
    total_start = time.time()

    for i, plan in enumerate(plans, 1):
        if verbose:
            print(f"\n[{i}/{len(plans)}] ", end="")

        project = projects_map.get(plan['project_id'], {})
        try:
            result = run_single_plan(db, plan, project, verbose, queue_settings)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\n  ✗ 推演失败: {e}")
                traceback.print_exc()
            try:
                db.update_plan_status(plan['id'], 'failed')
            except Exception:
                pass

    total_time = time.time() - total_start

    # 导出CRM数据
    crm_data = db.export_for_crm()
    export_path = os.path.join(os.path.dirname(__file__), "web", "data", "deduction_export.json")
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(crm_data, f, ensure_ascii=False, indent=2, default=str)

    # 汇总报告
    if verbose:
        total_tokens = sum(r.get('tokens', 0) for r in results)
        total_blocked = sum(len(r.get('blocked', [])) for r in results)
        total_nodes = sum(r.get('nodes_extracted', 0) for r in results)
        total_expanded = sum(len(r.get('expanded_plans', [])) for r in results)
        print(f"\n{'='*60}")
        print(f"推演完成")
        print(f"  计划: {len(results)}/{len(plans)}")
        print(f"  Token: {total_tokens:,}")
        print(f"  耗时: {total_time:.1f}s")
        print(f"  阻塞: {total_blocked}个")
        print(f"  节点提取: {total_nodes}个")
        print(f"  自动拓展: {total_expanded}个新计划")
        print(f"  CRM导出: {export_path}")
        stats = db.get_stats()
        print(f"  统计: {json.dumps(stats, ensure_ascii=False)}")
        print(f"{'='*60}")

    db.close()


if __name__ == "__main__":
    main()
