```python
"""
高级上下文感知代码检索模块

该模块实现了一个基于语义向量的代码切片机制，用于在大型代码库中快速定位相关代码片段。
通过结合符号索引和语义相似度搜索，能够高效地将最小必要代码上下文加载到LLM窗口中。

核心功能：
1. 代码符号解析与切片
2. 语义向量索引构建
3. 混合检索策略（符号+语义）
4. 智能上下文窗口管理

输入输出格式说明：
输入：
- project_path: 项目根目录路径 (str)
- query: 自然语言查询 (str)
- max_tokens: 最大token限制 (int)
- min_score: 最小相似度阈值 (float)

输出：
- Dict结构，包含：
  * 'context': 合并后的代码上下文 (str)
  * 'slices': 匹配的代码片段列表 (List[CodeSlice])
  * 'stats': 检索统计信息 (Dict)
"""

import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import re
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CodeSlice:
    """代码片段数据结构"""
    file_path: str
    start_line: int
    end_line: int
    code: str
    symbols: List[str]
    score: float = 0.0
    token_count: int = 0


class CodeContextRetriever:
    """
    基于语义向量的代码上下文检索器
    
    该类实现了一个混合检索策略，结合符号索引和语义相似度搜索，
    能够根据模糊意图动态加载最小必要代码段。
    """
    
    def __init__(self, project_path: str, model_name: str = 'all-MiniLM-L6-v2'):
        """
        初始化检索器
        
        Args:
            project_path: 项目根目录路径
            model_name: 用于语义编码的模型名称
            
        Raises:
            ValueError: 如果项目路径不存在
        """
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
            
        self.model_name = model_name
        self.index: Dict[str, List[CodeSlice]] = defaultdict(list)
        self.symbol_index: Dict[str, Set[str]] = defaultdict(set)
        self._initialized = False
        
        logger.info(f"Initialized CodeContextRetriever for project: {self.project_path}")

    def initialize(self) -> None:
        """
        初始化代码索引，解析项目结构并构建语义向量
        
        该方法会扫描项目目录，解析所有Python文件，提取符号信息，
        并为每个代码片段生成语义向量。
        """
        if self._initialized:
            logger.warning("Index already initialized, skipping...")
            return
            
        logger.info("Starting index initialization...")
        python_files = list(self.project_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                self._process_file(file_path)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
                
        self._initialized = True
        logger.info(f"Index initialization complete. Processed {len(python_files)} files.")

    def _process_file(self, file_path: Path) -> None:
        """
        处理单个Python文件，提取符号和代码片段
        
        Args:
            file_path: Python文件路径
        """
        rel_path = file_path.relative_to(self.project_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 简单的符号提取（实际应用中可以使用更复杂的解析器）
        symbols = self._extract_symbols(content)
        
        # 创建文件级别的代码片段
        file_slice = CodeSlice(
            file_path=str(rel_path),
            start_line=1,
            end_line=content.count('\n') + 1,
            code=content,
            symbols=symbols
        )
        
        # 添加到索引
        for symbol in symbols:
            self.index[symbol].append(file_slice)
            self.symbol_index[str(rel_path)].add(symbol)
            
        logger.debug(f"Processed file: {rel_path}, found symbols: {symbols}")

    def _extract_symbols(self, code: str) -> List[str]:
        """
        从代码中提取符号（函数、类、变量等）
        
        Args:
            code: Python代码字符串
            
        Returns:
            提取的符号列表
        """
        # 简单的正则匹配（实际应用中可以使用AST解析）
        patterns = [
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # 函数定义
            r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # 类定义
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=',  # 变量赋值
        ]
        
        symbols = set()
        for pattern in patterns:
            matches = re.findall(pattern, code)
            symbols.update(matches)
            
        return list(symbols)

    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 2000,
        min_score: float = 0.6
    ) -> Dict:
        """
        根据查询检索相关代码上下文
        
        Args:
            query: 自然语言查询
            max_tokens: 返回上下文的最大token数
            min_score: 最小相似度阈值
            
        Returns:
            包含上下文和元数据的字典
            
        Raises:
            ValueError: 如果索引未初始化
        """
        if not self._initialized:
            raise ValueError("Index not initialized. Call initialize() first.")
            
        # 1. 查询预处理
        processed_query = self._preprocess_query(query)
        
        # 2. 符号匹配（简化版，实际应用中会使用语义相似度）
        matched_symbols = self._find_matching_symbols(processed_query)
        
        # 3. 检索相关代码片段
        slices = []
        for symbol in matched_symbols:
            for code_slice in self.index[symbol]:
                # 计算相似度分数（简化版）
                score = self._calculate_similarity(processed_query, code_slice)
                if score >= min_score:
                    code_slice.score = score
                    code_slice.token_count = len(code_slice.code.split())  # 简单的token估算
                    slices.append(code_slice)
        
        # 4. 去重和排序
        unique_slices = self._deduplicate_slices(slices)
        sorted_slices = sorted(unique_slices, key=lambda x: x.score, reverse=True)
        
        # 5. 构建上下文窗口
        context, selected_slices, token_count = self._build_context_window(
            sorted_slices, max_tokens
        )
        
        # 6. 准备返回结果
        return {
            'context': context,
            'slices': selected_slices,
            'stats': {
                'total_candidates': len(slices),
                'selected_slices': len(selected_slices),
                'token_count': token_count,
                'coverage': len(set(s.file_path for s in selected_slices)) / len(self.index) if self.index else 0
            }
        }

    def _preprocess_query(self, query: str) -> str:
        """
        预处理查询文本
        
        Args:
            query: 原始查询字符串
            
        Returns:
            处理后的查询字符串
        """
        # 简单的预处理：小写化，移除特殊字符
        processed = re.sub(r'[^a-zA-Z0-9\s]', '', query.lower())
        return processed.strip()

    def _find_matching_symbols(self, query: str) -> Set[str]:
        """
        根据查询查找匹配的符号
        
        Args:
            query: 预处理后的查询字符串
            
        Returns:
            匹配的符号集合
        """
        query_terms = query.split()
        matched_symbols = set()
        
        for symbol in self.index.keys():
            symbol_lower = symbol.lower()
            for term in query_terms:
                if term in symbol_lower:
                    matched_symbols.add(symbol)
                    break
                    
        return matched_symbols

    def _calculate_similarity(self, query: str, code_slice: CodeSlice) -> float:
        """
        计算查询与代码片段的相似度（简化版）
        
        在实际应用中，这里应该使用真正的语义相似度计算，
        可能基于预训练的句子编码器。
        
        Args:
            query: 查询字符串
            code_slice: 代码片段对象
            
        Returns:
            相似度分数 [0, 1]
        """
        # 简化的相似度计算：查询词在代码中出现的频率
        query_terms = set(query.split())
        code_lower = code_slice.code.lower()
        
        if not query_terms:
            return 0.0
            
        matches = sum(1 for term in query_terms if term in code_lower)
        return matches / len(query_terms)

    def _deduplicate_slices(self, slices: List[CodeSlice]) -> List[CodeSlice]:
        """
        去重代码片段，保留分数最高的版本
        
        Args:
            slices: 原始代码片段列表
            
        Returns:
            去重后的代码片段列表
        """
        seen = {}
        for slice_ in slices:
            key = (slice_.file_path, slice_.start_line, slice_.end_line)
            if key not in seen or slice_.score > seen[key].score:
                seen[key] = slice_
                
        return list(seen.values())

    def _build_context_window(
        self,
        slices: List[CodeSlice],
        max_tokens: int
    ) -> Tuple[str, List[CodeSlice], int]:
        """
        构建上下文窗口，确保不超过token限制
        
        Args:
            slices: 排序后的代码片段列表
            max_tokens: 最大token数
            
        Returns:
            元组包含：合并的上下文字符串，选择的代码片段，实际token数
        """
        selected = []
        total_tokens = 0
        context_parts = []
        
        for slice_ in slices:
            if total_tokens + slice_.token_count > max_tokens:
                break
                
            selected.append(slice_)
            total_tokens += slice_.token_count
            
            # 添加文件头和代码片段
            context_parts.append(f"\n# File: {slice_.file_path} (lines {slice_.start_line}-{slice_.end_line})\n")
            context_parts.append(slice_.code)
            
        context = ''.join(context_parts)
        return context, selected, total_tokens

    def get_index_stats(self) -> Dict:
        """
        获取索引统计信息
        
        Returns:
            包含索引统计信息的字典
        """
        return {
            'total_files': len(set(s.file_path for slices in self.index.values() for s in slices)),
            'total_symbols': len(self.index),
            'total_slices': sum(len(slices) for slices in self.index.values()),
            'symbol_frequency': {k: len(v) for k, v in sorted(self.index.items(), key=lambda x: -len(x[1]))[:10]}
        }


# 使用示例
if __name__ == "__main__":
    # 初始化检索器
    retriever = CodeContextRetriever(project_path=".")
    retriever.initialize()
    
    # 获取索引统计信息
    stats = retriever.get_index_stats()
    print("Index Statistics:")
    print(f"Total files: {stats['total_files']}")
    print(f"Total symbols: {stats['total_symbols']}")
    print(f"Total slices: {stats['total_slices']}")
    print("Top symbols by frequency:")
    for symbol, count in stats['symbol_frequency'].items():
        print(f"  {symbol}: {count}")
    
    # 执行查询
    print("\nExecuting query: 'find all database connections'")
    result = retriever.retrieve_context(
        query="find all database connections",
        max_tokens=1000
    )
    
    # 打印结果
    print(f"\nFound {len(result['slices'])} relevant code slices:")
    for slice_ in result['slices']:
        print(f"- {slice_.file_path} (lines {slice_.start_line}-{slice_.end_line}), score: {slice_.score:.2f}")
    
    print("\nContext Preview (first 500 chars):")
    print(result['context'][:500] + "...")