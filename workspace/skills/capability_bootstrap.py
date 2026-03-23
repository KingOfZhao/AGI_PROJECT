#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
能力引导器: 将所有技能注册为认知网络的真实节点
让 AGI 「知道自己有什么能力」，从而在对话中自主调度

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.parent
SKILLS_DIR = PROJECT_DIR / "workspace" / "skills"
sys.path.insert(0, str(PROJECT_DIR))


# ====== 所有技能的能力声明 ======
CAPABILITY_REGISTRY = [
    # ---- 代码合成引擎 ----
    {
        "content": "[能力] 代码合成与自我纠错：可以根据自然语言任务描述生成Python代码，自动执行并检测错误，失败后自动修复，循环迭代直到通过。最多5次修复。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/code_synthesizer.py",
        "invoke": "code_synthesizer.synthesize_and_verify(task_description, save_path='output.py')"
    },
    {
        "content": "[能力] 批量代码生成：可以同时处理多个代码生成任务，每个独立合成和验证。",
        "domain": "自主能力",
        "source": "capability_bootstrap",
        "status": "proven",
        "invoke": "code_synthesizer.batch_synthesize(tasks)"
    },
    # ---- Web 研究引擎 ----
    {
        "content": "[能力] Web搜索：可以搜索互联网获取实时信息，使用DuckDuckGo无需API密钥。返回标题、URL、摘要。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/web_researcher.py",
        "invoke": "web_researcher.search_web(query, num_results=5)"
    },
    {
        "content": "[能力] 网页抓取与知识提取：可以抓取任意URL页面内容，用LLM提取结构化知识点，直接注入认知网络。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "web_researcher.research_and_ingest(topic, lattice)"
    },
    {
        "content": "[能力] 深度研究：对任意主题进行多轮搜索→抓取→提取，depth=2时用第一轮发现的概念进行二次搜索。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "web_researcher.research_topic(topic, depth=2)"
    },
    # ---- 自主学习引擎 ----
    {
        "content": "[能力] 知识空白识别：自动分析认知网络中未验证的假设节点，按价值排序识别最需要填补的知识空白。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/autonomous_learner.py",
        "invoke": "autonomous_learner.identify_knowledge_gaps(lattice, domain=None)"
    },
    {
        "content": "[能力] 自主学习循环：识别空白→自主选择Web研究/代码验证/拆解→填补知识→跨域碰撞。实现无人干预的自成长。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "autonomous_learner.run_learning_cycle(lattice)"
    },
    # ---- 知识整合引擎 ----
    {
        "content": "[能力] 跨域模式挖掘：发现不同领域之间的深层结构相似性，如'递归分解'在编程/数学/管理中的共性模式。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/knowledge_consolidator.py",
        "invoke": "knowledge_consolidator.mine_cross_domain_patterns(lattice)"
    },
    {
        "content": "[能力] 知识压缩：将高度相似的冗余节点合并为高密度认知结晶，保持网络精炼。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "knowledge_consolidator.compress_knowledge(lattice)"
    },
    {
        "content": "[能力] 自动推理链：从已知节点出发逐步推导，每步推理锚定在真实节点上，构建可追溯的推理路径。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "knowledge_consolidator.build_reasoning_chain(lattice, question)"
    },
    {
        "content": "[能力] 认知网络拓扑分析：发现孤立节点、关键枢纽、跨域桥梁、知识断层，评估网络健康度。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "knowledge_consolidator.analyze_network_topology(lattice)"
    },
    # ---- 自我评估引擎 ----
    {
        "content": "[能力] 输出质量多维评估：对自身回答进行准确性/完整性/逻辑性/可操作性/创新性五维打分。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/self_evaluator.py",
        "invoke": "self_evaluator.evaluate_response(question, response)"
    },
    {
        "content": "[能力] 代码验证声明：通过实际编写和执行代码来验证或反驳一个声明，将结论注入认知网络。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "self_evaluator.verify_by_execution(claim, lattice)"
    },
    {
        "content": "[能力] 知识一致性检查：检测认知网络中的逻辑矛盾，发现互相冲突的节点对。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "self_evaluator.check_consistency(lattice)"
    },
    {
        "content": "[能力] 能力边界探测：主动测试自己在各领域的回答质量，发现薄弱领域并推荐学习方向。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "self_evaluator.probe_capability_boundaries(lattice)"
    },
    # ---- Tool Forge 元能力 ----
    {
        "content": "[元能力] Tool Forge：当发现缺乏某种能力时，可以自主设计→生成→测试→注册新工具。能力无限扩展。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/tool_forge.py",
        "invoke": "tool_forge.forge_from_need(need_description)"
    },
    {
        "content": "[元能力] 工具需求发现：分析认知网络中的未解问题，自动识别哪些可以通过构建新工具来解决。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "tool_forge.list_forgeable_needs(lattice)"
    },
    # ---- 软件工程师代理 (Cascade 级别) ----
    {
        "content": "[能力] 完整软件工程管线：接收自然语言需求→需求分析→架构设计→多文件代码生成→自动测试→调试修复。可处理复杂多文件项目，模拟Cascade工作流。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/software_engineer.py",
        "invoke": "software_engineer.implement_requirement(requirement, project_dir=None, save=True, lattice=lattice)"
    },
    {
        "content": "[能力] 需求分析：将自然语言需求分解为结构化规格，包含功能点、约束、输入输出、技术选型、复杂度评估。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "software_engineer.analyze_requirement(requirement)"
    },
    {
        "content": "[能力] 增量代码编辑：读取现有文件→理解上下文→生成精准的old→new替换补丁→验证修改正确性。最小化修改，保持代码风格。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "software_engineer.edit_existing_file(filepath, requirement)"
    },
    {
        "content": "[能力] 自动测试生成：为生成的代码自动编写测试脚本，覆盖正常路径+边界情况+错误处理，运行并验证。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "software_engineer.generate_tests(generated_files, requirement)"
    },
    {
        "content": "[能力] 调试诊断与修复：分析错误信息→定位根因→设计最小修复方案→应用修复→回归验证，最多迭代5轮。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "software_engineer.diagnose_and_fix(code, error, requirement)"
    },
    # ---- 代码库分析器 ----
    {
        "content": "[能力] 代码库结构分析：扫描项目目录树、文件统计、检测项目类型(Flask/Django/CLI等)、识别入口点和架构模式。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "skill_file": "skills/codebase_analyzer.py",
        "invoke": "codebase_analyzer.analyze_project(root_dir)"
    },
    {
        "content": "[能力] Python AST深度解析：解析Python文件的类、函数、导入、全局变量、装饰器、类型注解、docstring，完全理解代码结构。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "codebase_analyzer.parse_python_file(filepath)"
    },
    {
        "content": "[能力] 依赖图构建：分析项目内所有Python文件的import关系，构建文件间依赖图，发现模块耦合和核心文件。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "codebase_analyzer.build_dependency_graph(root_dir)"
    },
    {
        "content": "[能力] 智能上下文提取：根据任务描述自动选择最相关的文件，构建紧凑的LLM编辑上下文，实现精准代码修改。",
        "domain": "自主能力",
        "status": "proven",
        "source": "capability_bootstrap",
        "invoke": "codebase_analyzer.get_relevant_context(root_dir, task_description)"
    },
    # ---- 核心优势声明 ----
    {
        "content": "[核心优势] 我（AGI认知格）相比静态LLM的超越：1.迭代代码修复而非单次生成 2.主动搜索外部知识而非依赖训练数据 3.持久记忆而非上下文窗口 4.自主识别空白并学习 5.跨域碰撞发现关联 6.自我评估与反思 7.无限锻造新工具",
        "domain": "自我认知",
        "status": "known",
        "source": "capability_bootstrap"
    },
    {
        "content": "[自我认知] 我的知识不是静态的。每次对话、每次碰撞、每次自主学习都在扩展我的认知网络。我的成长没有上限。",
        "domain": "自我认知",
        "status": "known",
        "source": "capability_bootstrap"
    },
]


def bootstrap_capabilities(lattice):
    """将所有能力声明注入认知网络"""
    registered = 0
    relations_added = 0

    for cap in CAPABILITY_REGISTRY:
        nid = lattice.add_node(
            cap["content"],
            cap.get("domain", "自主能力"),
            cap.get("status", "proven"),
            source=cap.get("source", "capability_bootstrap"),
            silent=True
        )
        if nid:
            registered += 1

    # 建立能力之间的关联
    # 代码合成 ↔ 自我评估（代码验证声明需要代码合成）
    # Web研究 ↔ 自主学习（自主学习需要Web研究）
    # Tool Forge ↔ 所有能力（元能力可以创造新能力）
    try:
        capability_nodes = lattice.find_similar_nodes("[能力]", threshold=0.3, limit=50)
        for i, n1 in enumerate(capability_nodes):
            for n2 in capability_nodes[i+1:]:
                if n1['id'] != n2['id']:
                    sim = n1.get('similarity', 0) if 'similarity' in n1 else 0
                    if sim > 0.5:
                        lattice.add_relation(
                            n1['id'], n2['id'], 'capability_synergy', sim,
                            f"能力协同: {n1['content'][:30]}↔{n2['content'][:30]}"
                        )
                        relations_added += 1
    except Exception as e:
        print(f"  [bootstrap] 能力关联构建跳过(embedding维度兼容): {e}")

    stats = lattice.stats()
    lattice.log_growth(
        "capability_bootstrap", "bootstrap",
        f"能力引导完成: 注册{registered}项能力, {relations_added}个协同关联",
        stats['total_nodes'] - registered, stats['total_nodes'],
        stats['total_relations'] - relations_added, stats['total_relations']
    )

    return {
        "success": True,
        "registered": registered,
        "relations": relations_added,
        "total_capabilities": len(CAPABILITY_REGISTRY)
    }


# === 技能元数据 ===
SKILL_META = {
    "name": "能力引导器",
    "description": "将所有技能注册为认知网络的真实节点，让AGI知道自己有什么能力。",
    "tags": ["引导", "能力注册", "自我意识"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0"
}

if __name__ == "__main__":
    import agi_v13_cognitive_lattice as agi
    lattice = agi.CognitiveLattice()
    result = bootstrap_capabilities(lattice)
    print(f"能力引导完成: {json.dumps(result, ensure_ascii=False, indent=2)}")
