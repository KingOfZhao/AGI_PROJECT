#!/usr/bin/env python3
"""
验证本地模型对 skill 库的关联调用能力
=============================================
三阶段验证:
  Phase 1 — 技能发现: SkillLibrary 能否加载 v1-v7 全部 7 个技能
  Phase 2 — 意图路由: SkillRouter 能否按意图精准匹配到对应技能
  Phase 3 — 本地模型调用: Ollama → v1 编码链 → 实际生成+精炼代码
"""

import sys
import os
import json
import time
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
SKILLS_DIR = PROJECT_ROOT / "workspace" / "skills"

# ── 颜色输出 ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0

def check(label: str, ok: bool, detail: str = ""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  {GREEN}✅ PASS{RESET}  {label}" + (f"  ({detail})" if detail else ""))
    else:
        failed += 1
        print(f"  {RED}❌ FAIL{RESET}  {label}" + (f"  ({detail})" if detail else ""))


# ═══════════════════════════════════════════════════════════════
#  Phase 1: 技能发现
# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
print(f"{BOLD}{CYAN}  Phase 1 — 技能发现 (Skill Discovery){RESET}")
print(f"{BOLD}{CYAN}{'═'*60}{RESET}\n")

EXPECTED_SKILLS = {
    "local_llm_coding_chain_v1":       ("自性编码链 v1", "coding"),
    "local_skill_orchestrator_v2":     ("自性技能协调器 v2", "orchestration"),
    "local_auto_skill_generator_v3":   ("自性自动新技能生成器 v3", "meta_evolution"),
    "local_code_validator_v4":         ("自性代码验证器 v4", "testing"),
    "local_project_scaffolder_v5":     ("自性项目脚手架生成器 v5", "scaffolding"),
    "local_knowledge_node_builder_v6": ("自性知识节点构建器 v6", "knowledge_graph"),
    "local_autonomous_evolver_v7":     ("自性自主进化器 v7", "meta_evolution"),
}

# 1a. 文件存在性
for stem, (display_name, _) in EXPECTED_SKILLS.items():
    py_file = SKILLS_DIR / f"{stem}.py"
    meta_file = SKILLS_DIR / f"{stem}.meta.json"
    check(f"{display_name} .py 文件存在", py_file.exists(), str(py_file.name))
    check(f"{display_name} .meta.json 存在", meta_file.exists(), str(meta_file.name))

# 1b. meta.json 结构完整性
print(f"\n  {YELLOW}── meta.json 结构验证 ──{RESET}")
for stem, (display_name, expected_cat) in EXPECTED_SKILLS.items():
    meta_file = SKILLS_DIR / f"{stem}.meta.json"
    if not meta_file.exists():
        check(f"{display_name} meta 结构", False, "文件不存在")
        continue
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    required_keys = {"name", "description", "tags", "category", "file", "source", "safety_level", "design_spec"}
    has_all = required_keys.issubset(set(meta.keys()))
    check(f"{display_name} meta 字段完整", has_all, f"缺少: {required_keys - set(meta.keys())}" if not has_all else f"category={meta['category']}")
    check(f"{display_name} chain_position 存在", "chain_position" in meta.get("design_spec", {}), f"pos={meta.get('design_spec',{}).get('chain_position')}")

# 1c. SkillLibrary 加载
print(f"\n  {YELLOW}── SkillLibrary 加载验证 ──{RESET}")
from pcm_skill_router import SkillLibrary
lib = SkillLibrary()
total = lib.load()
check(f"SkillLibrary 总加载数 > 0", total > 0, f"loaded {total} skills")

found_chain_skills = []
for stem, (display_name, _) in EXPECTED_SKILLS.items():
    found = display_name in lib.by_name
    if found:
        found_chain_skills.append(display_name)
    check(f"SkillLibrary 包含 {display_name}", found)

check(f"全部 7 个自性技能链均已加载", len(found_chain_skills) == 7, f"found {len(found_chain_skills)}/7")


# ═══════════════════════════════════════════════════════════════
#  Phase 2: 意图路由
# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
print(f"{BOLD}{CYAN}  Phase 2 — 意图路由 (Skill Routing){RESET}")
print(f"{BOLD}{CYAN}{'═'*60}{RESET}\n")

from pcm_skill_router import SkillRouter
router = SkillRouter(lib)

ROUTING_TESTS = [
    ("链式编码 本地模型 代码生成",    "自性编码链 v1"),
    ("技能协调 多链并行 节点注册",    "自性技能协调器 v2"),
    ("自动生成新技能 自进化",        "自性自动新技能生成器 v3"),
    ("代码验证 测试用例 自动修复",    "自性代码验证器 v4"),
    ("项目脚手架 一键生成 目录结构",  "自性项目脚手架生成器 v5"),
    ("知识图谱 节点关系 构建",       "自性知识节点构建器 v6"),
    ("自主进化 自我生成 无穷闭环",    "自性自主进化器 v7"),
]

for query, expected_name in ROUTING_TESTS:
    results = router.route(query, top_k=15)
    names = [r["name"] for r in results]
    found = expected_name in names
    rank = names.index(expected_name) + 1 if found else -1
    score = results[rank-1]["score"] if found else 0
    check(f"路由「{query[:15]}...」→ {expected_name}", found, f"rank={rank}, score={score}")

# 交叉路由: 一个泛化查询能否命中多个链节点
cross_results = router.route("本地模型 编码能力 链式调用 技能", top_k=20)
cross_names = [r["name"] for r in cross_results]
chain_hits = sum(1 for name in cross_names if name.startswith("自性"))
check(f"泛化查询命中多个链节点", chain_hits >= 3, f"hit {chain_hits}/7 chain skills")

print(f"\n  {YELLOW}── Top-5 泛化路由结果 ──{RESET}")
for i, r in enumerate(cross_results[:5], 1):
    print(f"    {i}. {r['name']}  score={r['score']}  reasons={r['match_reasons'][:3]}")


# ═══════════════════════════════════════════════════════════════
#  Phase 3: 本地模型实际调用
# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
print(f"{BOLD}{CYAN}  Phase 3 — 本地模型调用 (Ollama LLM Call){RESET}")
print(f"{BOLD}{CYAN}{'═'*60}{RESET}\n")

import requests

OLLAMA_URL = "http://localhost:11434"

# 3a. Ollama 连接检查
try:
    resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    models = [m["name"] for m in resp.json().get("models", [])]
    check("Ollama 服务连接", True, f"models: {models}")
except Exception as e:
    check("Ollama 服务连接", False, str(e))
    models = []

if not models:
    print(f"\n  {RED}⚠ Ollama 未运行，跳过 Phase 3 实际调用测试{RESET}")
else:
    # 选择可用模型 (优先 qwen2.5-coder)
    model = next((m for m in models if "coder" in m), models[0])
    print(f"  {YELLOW}使用模型: {model}{RESET}\n")

    # 3b. 动态加载 v1 编码链并调用
    print(f"  {YELLOW}── 动态加载 v1 编码链 ──{RESET}")
    v1_path = SKILLS_DIR / "local_llm_coding_chain_v1.py"
    spec = importlib.util.spec_from_file_location("skill_v1", v1_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    check("动态加载 LocalLLMCodingChain 类", hasattr(mod, "LocalLLMCodingChain"))

    chain = mod.LocalLLMCodingChain(base_url=OLLAMA_URL, model=model)
    check("实例化 v1 编码链", chain is not None, f"model={chain.model}")

    # 3c. 单节点调用 — 生成代码 (小任务，控制时间)
    print(f"\n  {YELLOW}── 节点1: generate_code (小任务) ──{RESET}")
    task = "写一个Python函数 fibonacci(n)，返回第n个斐波那契数，要求有类型提示和docstring"
    t0 = time.time()
    code = chain.generate_code(task)
    t1 = time.time()
    code_ok = len(code) > 50 and ("def " in code or "fibonacci" in code.lower())
    check(f"generate_code 返回有效代码", code_ok, f"{len(code)} chars, {t1-t0:.1f}s")
    if code_ok:
        # 打印前 8 行
        lines = code.strip().split("\n")[:8]
        for line in lines:
            print(f"    {CYAN}│{RESET} {line}")
        if len(code.strip().split("\n")) > 8:
            print(f"    {CYAN}│{RESET} ... ({len(code.strip().split(chr(10)))} lines total)")

    # 3d. 单节点调用 — 自批判精炼
    print(f"\n  {YELLOW}── 节点2: critique_and_refine ──{RESET}")
    t0 = time.time()
    refined = chain.critique_and_refine(code)
    t1 = time.time()
    refined_ok = len(refined) > 50
    check(f"critique_and_refine 返回优化代码", refined_ok, f"{len(refined)} chars, {t1-t0:.1f}s")
    check(f"chain_history 记录完整", len(chain.chain_history) >= 2, f"{len(chain.chain_history)} nodes recorded")

    # 3e. 端到端: 路由发现 → 加载技能 → 调用
    print(f"\n  {YELLOW}── 端到端: 路由 → 加载 → 调用 ──{RESET}")
    e2e_results = router.route("本地模型 编码链 链式调用", top_k=10)
    e2e_names = [r["name"] for r in e2e_results]
    v1_found = "自性编码链 v1" in e2e_names
    check("路由发现「自性编码链 v1」", v1_found)

    if v1_found:
        # 从 meta 获取文件路径
        v1_meta_path = SKILLS_DIR / "local_llm_coding_chain_v1.meta.json"
        v1_meta = json.loads(v1_meta_path.read_text(encoding="utf-8"))
        skill_file = PROJECT_ROOT / v1_meta["file"]
        check("meta.file 指向有效 .py 文件", skill_file.exists(), str(skill_file))

        # 动态加载并执行最小调用
        spec2 = importlib.util.spec_from_file_location("e2e_v1", skill_file)
        mod2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mod2)
        e2e_chain = mod2.LocalLLMCodingChain(base_url=OLLAMA_URL, model=model)
        e2e_code = e2e_chain._call_model("print('hello world')", temperature=0.1)
        check("端到端 LLM 调用成功", len(e2e_code) > 5 and "错误" not in e2e_code, f"{len(e2e_code)} chars")


# ═══════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════
total_tests = passed + failed
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  验证结果: {GREEN}{passed} passed{RESET} / {RED if failed else GREEN}{failed} failed{RESET} / {total_tests} total{RESET}")
if failed == 0:
    print(f"{BOLD}{GREEN}  ✅ 本地模型对 skill 库的关联调用能力验证全部通过{RESET}")
else:
    print(f"{BOLD}{YELLOW}  ⚠ 存在 {failed} 项未通过，请检查上方详情{RESET}")
print(f"{BOLD}{'═'*60}{RESET}\n")

sys.exit(0 if failed == 0 else 1)
