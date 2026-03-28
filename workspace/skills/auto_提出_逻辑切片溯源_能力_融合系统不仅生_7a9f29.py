"""
逻辑切片溯源能力融合系统

该模块提供了一个用于生成可溯源答案的框架。系统不仅生成针对用户查询的回复，
还构建一个依赖图，将结论映射回源文档中的具体文本片段（逻辑切片）。
当结论无法在源文档中找到支持时，系统会将其标记为潜在幻觉。

主要功能：
1. generate_traceable_response: 生成答案并构建依赖图。
2. verify_conclusion_validity: 验证特定结论的溯源切片，检测幻觉。

输入格式:
- documents: List[Dict], 其中每个字典包含 'id' (str) 和 'content' (str)。
- query: str, 用户的查询。

输出格式:
- TraceableResponse: 包含答案文本和结论列表（每个结论包含文本和证据切片）。
- VerificationReport: 包含验证状态、证据列表和幻觉警告。

使用示例:
    >>> docs = [
    ...     {"id": "doc1", "content": "阿司匹林是一种抗血小板药物。"},
    ...     {"id": "doc2", "content": "阿司匹林可能导致胃出血。"}
    ... ]
    >>> response = generate_traceable_response(docs, "阿司匹林的作用和副作用是什么？")
    >>> print(response.answer)
    >>> report = verify_conclusion_validity(response.conclusions[0], docs)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SourceDocument:
    """表示输入的源文档。"""
    id: str
    content: str

    def __post_init__(self):
        if not self.content:
            logger.warning(f"文档 {self.id} 的内容为空。")


@dataclass
class EvidenceSlice:
    """表示源文档中支持结论的具体文本片段。"""
    doc_id: str
    start_index: int
    end_index: int
    text: str

    def __str__(self):
        return f"[Doc:{self.doc_id}][{self.start_index}:{self.end_index}] '{self.text}'"


@dataclass
class TraceableConclusion:
    """表示一个可溯源的结论节点。"""
    statement: str
    evidence_slices: List[EvidenceSlice] = field(default_factory=list)

    def is_hallucination(self) -> bool:
        """检查结论是否缺乏证据支持（潜在幻觉）。"""
        return len(self.evidence_slices) == 0


@dataclass
class TraceableResponse:
    """包含生成的答案和完整的依赖图结构。"""
    answer: str
    conclusions: List[TraceableConclusion]


@dataclass
class VerificationReport:
    """结论验证报告。"""
    conclusion_statement: str
    is_valid: bool
    found_evidence: List[EvidenceSlice]
    warning_message: Optional[str] = None


def _extract_text_slices(doc: SourceDocument, target_phrase: str) -> List[EvidenceSlice]:
    """
    辅助函数：在文档中查找目标短语并返回切片信息。

    Args:
        doc: 源文档对象。
        target_phrase: 要查找的文本片段。

    Returns:
        包含所有匹配切片的列表。
    """
    if not target_phrase or not doc.content:
        return []

    slices = []
    # 使用正则查找所有出现的位置，忽略大小写
    for match in re.finditer(re.escape(target_phrase), doc.content, re.IGNORECASE):
        start = match.start()
        end = match.end()
        slices.append(EvidenceSlice(
            doc_id=doc.id,
            start_index=start,
            end_index=end,
            text=doc.content[start:end]
        ))
    
    return slices


def generate_traceable_response(
    documents: List[Dict[str, str]], 
    query: str
) -> TraceableResponse:
    """
    核心函数1：生成答案并构建逻辑切片依赖图。
    
    注意：在实际AGI系统中，这里会调用LLM。本实现模拟了一个基于规则的
    检索增强生成（RAG）过程，以演示溯源逻辑。

    Args:
        documents: 文档字典列表，格式为 [{'id': str, 'content': str}, ...]。
        query: 用户的查询字符串。

    Returns:
        TraceableResponse: 包含答案和溯源结论的对象。

    Raises:
        ValueError: 如果输入文档格式无效或为空。
    """
    if not documents:
        raise ValueError("输入文档列表不能为空。")
    
    # 数据验证与转换
    source_docs = []
    for doc_data in documents:
        if 'id' not in doc_data or 'content' not in doc_data:
            raise ValueError(f"文档格式错误，必须包含 'id' 和 'content' 键: {doc_data}")
        source_docs.append(SourceDocument(id=doc_data['id'], content=doc_data['content']))

    logger.info(f"正在处理查询: '{query}' 基于 {len(source_docs)} 个文档。")

    # 模拟推理过程：提取包含查询关键词的句子作为“结论”
    conclusions = []
    answer_parts = []
    
    keywords = re.findall(r'\w+', query) # 简单分词
    
    for doc in source_docs:
        # 简单逻辑：如果文档包含关键词，则将其作为结论的一部分
        # 在真实场景中，这里是LLM生成文本，并输出引用的来源
        for keyword in keywords:
            if keyword.lower() in doc.content.lower():
                # 模拟生成一个基于文档内容的结论陈述
                statement = f"根据文档 {doc.id}，{keyword} 相关信息已被记录。"
                
                # 查找证据切片
                slices = _extract_text_slices(doc, keyword)
                
                conclusion = TraceableConclusion(statement=statement, evidence_slices=slices)
                conclusions.append(conclusion)
                answer_parts.append(statement)

    # 构建最终答案
    final_answer = " ".join(answer_parts) if answer_parts else "未在文档中找到相关信息。"
    
    # 如果没有找到信息，生成一个潜在的幻觉示例用于演示
    if not answer_parts:
        hallucination_stmt = "系统推测该信息可能存在于未收录的资料中。"
        conclusions.append(TraceableConclusion(statement=hallucination_stmt, evidence_slices=[]))
        final_answer = hallucination_stmt

    logger.info("答案生成完毕，依赖图构建完成。")
    return TraceableResponse(answer=final_answer, conclusions=conclusions)


def verify_conclusion_validity(
    conclusion: TraceableConclusion, 
    documents: List[SourceDocument]
) -> VerificationReport:
    """
    核心函数2：验证结论的溯源切片，检测幻觉。
    
    当用户质疑某个结论时，系统利用此函数高亮显示支持片段。
    如果切片为空或无效，则标记为潜在幻觉。

    Args:
        conclusion: 待验证的结论对象。
        documents: 原始文档列表，用于二次校验。

    Returns:
        VerificationReport: 详细的验证报告。
    """
    logger.info(f"正在验证结论: '{conclusion.statement}'")
    
    # 边界检查
    if not conclusion.evidence_slices:
        return VerificationReport(
            conclusion_statement=conclusion.statement,
            is_valid=False,
            found_evidence=[],
            warning_message="警告：未找到支持该结论的逻辑切片。这可能是潜在幻觉。"
        )
    
    valid_slices = []
    doc_map = {d.id: d for d in documents}
    
    # 二次校验：确保切片确实存在于文档中（防止数据篡改或索引错误）
    for slice_ref in conclusion.evidence_slices:
        if slice_ref.doc_id not in doc_map:
            logger.warning(f"切片引用的文档 ID {slice_ref.doc_id} 不存在。")
            continue
            
        doc = doc_map[slice_ref.doc_id]
        # 提取文档中的实际文本进行比对
        actual_text = doc.content[slice_ref.start_index:slice_ref.end_index]
        
        if actual_text == slice_ref.text:
            valid_slices.append(slice_ref)
        else:
            logger.warning(f"切片内容不匹配。预期: '{slice_ref.text}', 实际: '{actual_text}'")

    is_valid = len(valid_slices) > 0
    warning_msg = None if is_valid else "警告：所有引用的切片均无效或无法匹配。"
    
    return VerificationReport(
        conclusion_statement=conclusion.statement,
        is_valid=is_valid,
        found_evidence=valid_slices,
        warning_message=warning_msg
    )


if __name__ == "__main__":
    # 使用示例：医疗领域场景
    sample_docs = [
        {"id": "med_001", "content": "阿司匹林是一种常用的抗血小板药物，用于预防心脏病发作。"},
        {"id": "med_002", "content": "阿司匹林的主要副作用包括胃部不适和胃出血风险增加。"}
    ]
    
    user_query = "阿司匹林有什么副作用？"
    
    try:
        # 1. 生成答案和依赖图
        response = generate_traceable_response(sample_docs, user_query)
        print(f"=== 系统生成的答案 ===\n{response.answer}\n")
        
        # 2. 对每个结论进行溯源验证（模拟用户质疑）
        print("=== 逻辑切片溯源验证 ===")
        for i, concl in enumerate(response.conclusions):
            print(f"\n结论 {i+1}: {concl.statement}")
            
            # 将字典转换为SourceDocument对象以供验证函数使用
            src_docs = [SourceDocument(id=d['id'], content=d['content']) for d in sample_docs]
            report = verify_conclusion_validity(concl, src_docs)
            
            print(f"状态: {'可信' if report.is_valid else '潜在幻觉'}")
            if report.warning_message:
                print(f"警告: {report.warning_message}")
            
            print("支持片段:")
            for ev in report.found_evidence:
                print(f"  - {ev}")
                
    except ValueError as e:
        logger.error(f"系统运行错误: {e}")