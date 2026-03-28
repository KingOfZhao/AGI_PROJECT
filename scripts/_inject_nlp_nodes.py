#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLP Proven Nodes 批量注入脚本
从 自然语言沟通的真实节点.md 读取 → 去重 → 分类 → 注入认知晶格DB
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)



import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import agi_v13_cognitive_lattice as agi

# ==================== 分类规则 ====================
# 关键词 → 领域映射（优先匹配靠前的规则）
CATEGORY_RULES = [
    # 幻觉/验证
    (["幻觉", "自验证", "事实核查", "可证伪", "锚定", "真实性"], "NLP-幻觉检测与验证"),
    # 意图/语义理解
    (["意图", "隐喻", "反讽", "讽刺", "歧义", "澄清", "语义", "语用", "隐含", "暗示",
      "前提", "推断", "理解", "含义", "蕴含"], "NLP-语义理解"),
    # 情感/语气
    (["情感", "语气", "情绪", "态度", "正负面", "褒贬", "讽刺检测"], "NLP-情感分析"),
    # 实体/关系抽取
    (["实体", "关系抽取", "命名实体", "共指", "指代", "消解"], "NLP-实体与关系"),
    # 逻辑/推理
    (["逻辑", "因果", "推理", "论证", "谬误", "矛盾", "一致性", "假设检验"], "NLP-逻辑推理"),
    # 生成/重写
    (["重写", "释义", "简化", "摘要", "生成", "扩写", "改写", "风格迁移", "润色"], "NLP-文本生成与重写"),
    # 对话/交互
    (["对话", "多轮", "会话", "上下文", "追问", "澄清", "话轮", "交互", "反馈"], "NLP-对话管理"),
    # 分类/主题
    (["分类", "主题", "标签", "归类", "聚类", "话题"], "NLP-文本分类"),
    # 翻译/多语言
    (["翻译", "多语言", "对齐", "跨语言", "双语", "语码转换"], "NLP-多语言处理"),
    # 知识/常识
    (["知识", "常识", "世界知识", "grounding", "百科", "知识图谱"], "NLP-知识与常识"),
    # 语法/拼写
    (["语法", "拼写", "纠错", "校对", "句法", "词法", "分词", "词性"], "NLP-语言基础"),
    # 代码/结构化
    (["代码", "SQL", "API", "结构化", "JSON", "XML", "正则", "模板"], "NLP-代码与结构化"),
    # 搜索/检索
    (["搜索", "检索", "相似度", "匹配", "关键词", "索引", "排序"], "NLP-搜索与检索"),
    # 工具调用/规划
    (["工具", "调用", "规划", "分解", "拆解", "步骤", "任务", "编排", "调度"], "NLP-任务规划"),
    # 安全/伦理
    (["安全", "伦理", "偏见", "公平", "有害", "毒性", "边界", "拒绝", "越狱"], "NLP-安全与伦理"),
    # 评估/度量
    (["评估", "度量", "评分", "打分", "指标", "质量", "基准", "benchmark"], "NLP-评估与度量"),
    # 视觉/多模态
    (["视觉", "图像", "多模态", "视频", "音频", "3D", "跨模态"], "NLP-多模态"),
    # 记忆/上下文
    (["记忆", "上下文", "长文本", "窗口", "注意力", "压缩", "摘要管理"], "NLP-上下文管理"),
]

def categorize(content: str) -> str:
    """根据关键词规则分类NLP节点"""
    for keywords, domain in CATEGORY_RULES:
        for kw in keywords:
            if kw in content:
                return domain
    return "NLP-通用能力"


# ==================== Claude补充的NLP proven节点 ====================
CLAUDE_NLP_NODES = [
    ("NLP-幻觉检测与验证", "幻觉检测的核心是将生成文本与已知事实锚点逐句比对，计算锚定率来量化可信度"),
    ("NLP-幻觉检测与验证", "自一致性检验：对同一问题多次采样生成，取共识部分作为可信输出，分歧部分标记为潜在幻觉"),
    ("NLP-幻觉检测与验证", "降低幻觉的关键手段：降低temperature、注入proven节点上下文、限制生成范围到已知事实"),
    ("NLP-语义理解", "隐喻理解需要检测源域与目标域的映射关系，如'时间是金钱'中时间(目标域)←金钱(源域)的属性迁移"),
    ("NLP-语义理解", "多义词消歧依赖上下文窗口内的共现词分布，而非孤立的词向量距离"),
    ("NLP-语义理解", "语用推理需要考虑Grice合作原则的四个准则：量、质、关系、方式"),
    ("NLP-情感分析", "细粒度情感分析需要区分持有者(holder)、目标(target)和极性(polarity)三要素"),
    ("NLP-情感分析", "反讽检测需要识别字面语义与说话者真实意图之间的不一致"),
    ("NLP-实体与关系", "嵌套实体识别：实体可以嵌套出现，如'[北京[大学]]'中'北京大学'和'大学'都是有效实体"),
    ("NLP-实体与关系", "零样本关系抽取通过将关系描述转化为自然语言假设，用文本蕴含模型判断是否成立"),
    ("NLP-逻辑推理", "自然语言推理(NLI)的三分类：蕴含(entailment)、矛盾(contradiction)、中性(neutral)"),
    ("NLP-逻辑推理", "链式推理(Chain-of-Thought)通过显式化中间步骤降低推理错误率，本质是将隐式推理外化为可验证步骤"),
    ("NLP-文本生成与重写", "受控生成的三种范式：前缀调优(prefix-tuning)、提示工程(prompting)、解码约束(constrained decoding)"),
    ("NLP-文本生成与重写", "低幻觉重写的核心策略：去除主观修饰、替换模糊量词为具体数据、将观点标记为观点而非事实"),
    ("NLP-对话管理", "对话状态追踪(DST)需要维护slot-value对的累积更新，处理用户修正和隐式确认"),
    ("NLP-对话管理", "多轮对话中的省略恢复：用户后续发言可能省略已建立的共同基础(common ground)，需要补全"),
    ("NLP-文本分类", "层次分类(hierarchical classification)利用标签间的父子关系约束预测，避免逻辑矛盾"),
    ("NLP-多语言处理", "跨语言迁移学习依赖多语言预训练模型中的共享表示空间，零样本跨语言效果与语言相似度正相关"),
    ("NLP-知识与常识", "知识图谱补全通过链接预测推断缺失关系，TransE将关系建模为头实体到尾实体的向量平移"),
    ("NLP-知识与常识", "常识推理需要的知识类型：物理直觉、因果关系、社会规范、时间顺序、空间关系"),
    ("NLP-语言基础", "中文分词的核心挑战：新词发现、歧义切分('结合成分子')、跨领域适应"),
    ("NLP-语言基础", "子词分词(BPE/WordPiece/Unigram)平衡了词表大小与未登录词(OOV)问题"),
    ("NLP-代码与结构化", "Text-to-SQL需要模式链接(schema linking)：将自然语言中的实体对齐到数据库表名和列名"),
    ("NLP-搜索与检索", "稠密检索(dense retrieval)用双编码器分别编码查询和文档，通过向量内积计算相关性"),
    ("NLP-搜索与检索", "检索增强生成(RAG)的关键是检索质量：召回率>准确率，因为生成模型可以过滤无关信息"),
    ("NLP-任务规划", "工具调用的关键是意图到API的映射：识别用户意图→选择合适工具→填充参数→执行→解释结果"),
    ("NLP-安全与伦理", "对抗性提示(prompt injection)防御：输入清洗+系统提示隔离+输出过滤的多层防线"),
    ("NLP-安全与伦理", "大模型偏见来源于训练数据中的统计偏差，缓解方法包括去偏训练、对抗去偏和后处理校准"),
    ("NLP-评估与度量", "BLEU/ROUGE等自动指标与人类评估相关性有限，开放式生成任务更需要人类或LLM-as-Judge评估"),
    ("NLP-上下文管理", "长文本处理的核心瓶颈是注意力机制的O(n²)复杂度，解决方案包括稀疏注意力、线性注意力和分块处理"),
]


def main():
    print("=" * 60)
    print("NLP Proven Nodes 批量注入")
    print("=" * 60)

    # 1. 读取并去重
    with open(os.path.join(os.path.dirname(__file__), "自然语言沟通的真实节点.md"), "r") as f:
        text = f.read()
    raw = [x.strip() for x in text.split("、") if x.strip()]
    unique = list(dict.fromkeys(raw))
    print(f"\n[1] 文件解析: {len(raw)} 原始项 → {len(unique)} 去重后")

    # 2. 分类
    categorized = {}
    for node in unique:
        domain = categorize(node)
        categorized.setdefault(domain, []).append(node)

    print(f"\n[2] 分类结果 ({len(categorized)} 个领域):")
    for domain, nodes in sorted(categorized.items(), key=lambda x: -len(x[1])):
        print(f"  {domain}: {len(nodes)} 个节点")

    # 3. 添加 Claude 补充节点
    for domain, content in CLAUDE_NLP_NODES:
        categorized.setdefault(domain, []).append(content)
    total_nodes = sum(len(v) for v in categorized.values())
    print(f"\n[3] 加入Claude补充节点 (+{len(CLAUDE_NLP_NODES)}) → 总计 {total_nodes} 个")

    # 4. 初始化认知晶格
    lattice = agi.CognitiveLattice()
    stats_before = lattice.stats()
    print(f"\n[4] 注入前状态: {stats_before['total_nodes']} 节点, {stats_before.get('proven', 0)} proven")

    # 5. 批量注入
    injected = 0
    skipped = 0
    for domain, nodes in categorized.items():
        for content in nodes:
            if len(content) < 3:
                skipped += 1
                continue
            nid = lattice.add_node(
                content, domain, "proven",
                source="nlp_proven_injection",
                silent=True
            )
            if nid:
                injected += 1
            else:
                skipped += 1

    print(f"\n[5] 注入完成: {injected} 新增, {skipped} 跳过(已存在或过短)")

    # 6. 注入后统计
    stats_after = lattice.stats()
    print(f"\n[6] 注入后状态: {stats_after['total_nodes']} 节点, {stats_after.get('proven', 0)} proven")
    print(f"    新增节点: +{stats_after['total_nodes'] - stats_before['total_nodes']}")

    # 7. 各领域统计
    print(f"\n[7] NLP领域分布:")
    with lattice._lock:
        c = lattice.conn.cursor()
        c.execute("""
            SELECT domain, COUNT(*) as cnt
            FROM cognitive_nodes
            WHERE domain LIKE 'NLP-%' AND status = 'proven'
            GROUP BY domain
            ORDER BY cnt DESC
        """)
        for row in c.fetchall():
            print(f"  {row['domain']}: {row['cnt']} proven")

    print("\n" + "=" * 60)
    print("NLP Proven Nodes 注入完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
