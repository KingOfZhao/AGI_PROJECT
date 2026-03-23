import ast
import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

class SemanticASTIndexer:
    """
    通过AST与语义向量的混合索引实现代码片段动态检索
    
    该类实现了从模糊语义到精确API调用或代码片段的动态检索与匹配，
    结合AST结构分析和语义向量相似度计算，提供混合检索能力。
    
    Attributes:
        ast_index (Dict): 存储AST节点序列的倒排索引
        semantic_vectors (Dict): 存储代码片段的语义向量
        code_snippets (Dict): 存储原始代码片段
    """
    
    def __init__(self):
        """初始化索引器"""
        self.ast_index = defaultdict(list)
        self.semantic_vectors = {}
        self.code_snippets = {}
        
    def _extract_ast_sequence(self, code: str) -> List[str]:
        """
        提取AST节点序列
        
        Args:
            code (str): 要解析的代码字符串
            
        Returns:
            List[str]: AST节点类型序列
            
        Raises:
            SyntaxError: 当代码语法错误时抛出
        """
        try:
            tree = ast.parse(code)
            return [node.__class__.__name__ for node in ast.walk(tree)]
        except SyntaxError as e:
            raise SyntaxError(f"代码语法错误: {e}")
            
    def _generate_semantic_vector(self, code: str) -> np.ndarray:
        """
        生成语义向量（模拟实现）
        
        实际应用中应使用预训练模型（如CodeBERT）生成真实语义向量
        此处使用随机向量作为示例
        
        Args:
            code (str): 代码字符串
            
        Returns:
            np.ndarray: 语义向量
        """
        # 在实际应用中替换为真实的语义向量生成
        return np.random.rand(128)
        
    def add_code_snippet(self, snippet_id: str, code: str) -> None:
        """
        添加代码片段到索引
        
        Args:
            snippet_id (str): 代码片段唯一标识
            code (str): 代码字符串
            
        Raises:
            ValueError: 当片段ID已存在时抛出
        """
        if snippet_id in self.code_snippets:
            raise ValueError(f"片段ID {snippet_id} 已存在")
            
        try:
            # 提取AST序列
            ast_sequence = self._extract_ast_sequence(code)
            
            # 生成语义向量
            semantic_vector = self._generate_semantic_vector(code)
            
            # 存储数据
            self.code_snippets[snippet_id] = code
            self.semantic_vectors[snippet_id] = semantic_vector
            
            # 构建AST倒排索引
            for node_type in ast_sequence:
                self.ast_index[node_type].append(snippet_id)
                
        except Exception as e:
            raise RuntimeError(f"添加代码片段失败: {e}")
            
    def _calculate_ast_similarity(self, query_seq: List[str], candidate_id: str) -> float:
        """
        计算AST结构相似度
        
        使用Jaccard相似度计算AST节点序列的重叠程度
        
        Args:
            query_seq (List[str]): 查询代码的AST节点序列
            candidate_id (str): 候选代码片段ID
            
        Returns:
            float: 相似度分数 (0-1)
        """
        candidate_seq = self._extract_ast_sequence(self.code_snippets[candidate_id])
        set_query = set(query_seq)
        set_candidate = set(candidate_seq)
        return len(set_query & set_candidate) / len(set_query | set_candidate)
        
    def _calculate_semantic_similarity(self, query_vector: np.ndarray, candidate_id: str) -> float:
        """
        计算语义相似度
        
        使用余弦相似度计算语义向量的相似程度
        
        Args:
            query_vector (np.ndarray): 查询代码的语义向量
            candidate_id (str): 候选代码片段ID
            
        Returns:
            float: 相似度分数 (0-1)
        """
        candidate_vector = self.semantic_vectors[candidate_id]
        dot_product = np.dot(query_vector, candidate_vector)
        norm_query = np.linalg.norm(query_vector)
        norm_candidate = np.linalg.norm(candidate_vector)
        return dot_product / (norm_query * norm_candidate + 1e-8)
        
    def search(self, query_code: str, top_k: int = 5, 
               ast_weight: float = 0.5) -> List[Tuple[str, float]]:
        """
        混合检索：结合AST结构和语义向量的相似度搜索
        
        Args:
            query_code (str): 查询代码字符串
            top_k (int): 返回结果数量
            ast_weight (float): AST结构相似度权重 (0-1)
            
        Returns:
            List[Tuple[str, float]]: 包含(片段ID, 综合相似度分数)的列表
            
        Raises:
            ValueError: 当查询代码语法错误时抛出
        """
        try:
            # 提取查询代码的AST序列和语义向量
            query_ast_seq = self._extract_ast_sequence(query_code)
            query_semantic_vector = self._generate_semantic_vector(query_code)
            
            # 获取候选片段ID（基于AST节点类型交集）
            candidate_ids = set()
            for node_type in query_ast_seq:
                candidate_ids.update(self.ast_index[node_type])
                
            if not candidate_ids:
                return []
                
            # 计算每个候选片段的综合相似度
            results = []
            for candidate_id in candidate_ids:
                ast_sim = self._calculate_ast_similarity(query_ast_seq, candidate_id)
                semantic_sim = self._calculate_semantic_similarity(query_semantic_vector, candidate_id)
                # 加权综合相似度
                combined_sim = ast_weight * ast_sim + (1 - ast_weight) * semantic_sim
                results.append((candidate_id, combined_sim))
                
            # 按相似度降序排序并返回top_k结果
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except SyntaxError as e:
            raise ValueError(f"查询代码语法错误: {e}")
        except Exception as e:
            raise RuntimeError(f"搜索过程中发生错误: {e}")
            
    def get_code_snippet(self, snippet_id: str) -> Optional[str]:
        """
        获取指定ID的代码片段
        
        Args:
            snippet_id (str): 代码片段ID
            
        Returns:
            Optional[str]: 代码片段字符串，如果不存在则返回None
        """
        return self.code_snippets.get(snippet_id)


# 示例用法
if __name__ == "__main__":
    # 初始化索引器
    indexer = SemanticASTIndexer()
    
    # 添加代码片段
    code1 = """
    def calculate_sum(numbers):
        total = 0
        for num in numbers:
            total += num
        return total
    """
    
    code2 = """
    def compute_average(values):
        if not values:
            return 0
        total = sum(values)
        return total / len(values)
    """
    
    code3 = """
    def find_max(items):
        max_val = items[0]
        for item in items[1:]:
            if item > max_val:
                max_val = item
        return max_val
    """
    
    try:
        indexer.add_code_snippet("sum_func", code1)
        indexer.add_code_snippet("avg_func", code2)
        indexer.add_code_snippet("max_func", code3)
        
        # 执行搜索查询
        query = """
        def find_largest_value(data):
            largest = data[0]
            for value in data[1:]:
                if value > largest:
                    largest = value
            return largest
        """
        
        results = indexer.search(query, top_k=2, ast_weight=0.6)
        
        # 输出结果
        print("搜索结果:")
        for snippet_id, score in results:
            print(f"片段ID: {snippet_id}, 相似度: {score:.4f}")
            print("代码内容:")
            print(indexer.get_code_snippet(snippet_id))
            print("-" * 50)
            
    except Exception as e:
        print(f"发生错误: {e}")