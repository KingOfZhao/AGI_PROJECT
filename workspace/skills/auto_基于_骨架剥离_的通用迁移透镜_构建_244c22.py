"""
Module: auto_skeleton_transfer_lens.py
Description: 基于‘骨架剥离’的通用迁移透镜 - 用于提取抽象结构骨架并寻找跨域解决方案
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SkeletonTransferLens")


@dataclass
class Skeleton:
    """骨架结构数据类"""
    source_domain: str
    verbs: List[str]
    nouns: List[str]
    raw_text: str
    vector: Optional[np.ndarray] = None


@dataclass
class CrossDomainSolution:
    """跨域解决方案数据类"""
    source_skeleton: Skeleton
    target_skeleton: Skeleton
    similarity_score: float
    heuristic_mapping: Dict[str, str]


class SkeletonExtractor:
    """骨架提取器：从文本中提取动词-名词结构骨架"""
    
    def __init__(self, language: str = 'zh'):
        """
        初始化骨架提取器
        
        Args:
            language: 语言类型 ('zh' 或 'en')
        """
        self.language = language
        self._init_lexicon()
        logger.info(f"初始化骨架提取器，语言: {language}")
    
    def _init_lexicon(self) -> None:
        """初始化领域词汇表"""
        # 简化的动词/名词词典（实际应用中应使用NLP库）
        self.domain_verbs = {
            'zh': ['进化', '筛选', '迭代', '测试', '感染', '防御', '变异', 
                   '传播', '识别', '清除', '优化', '学习', '训练'],
            'en': ['evolve', 'select', 'iterate', 'test', 'infect', 'defend', 
                   'mutate', 'spread', 'identify', 'eliminate', 'optimize', 
                   'learn', 'train']
        }
        
        self.domain_nouns = {
            'zh': ['生物', '病毒', '代码', '系统', '抗体', '数据', '模型',
                   '网络', '种群', '环境', '单元', '特征'],
            'en': ['organism', 'virus', 'code', 'system', 'antibody', 'data', 
                   'model', 'network', 'population', 'environment', 'unit', 'feature']
        }
    
    def extract(self, text: str) -> Skeleton:
        """
        从文本中提取骨架结构
        
        Args:
            text: 输入文本
            
        Returns:
            Skeleton对象
            
        Raises:
            ValueError: 当输入文本为空或无效时
        """
        if not text or not isinstance(text, str):
            raise ValueError("输入文本必须是非空字符串")
            
        logger.debug(f"开始提取骨架，文本长度: {len(text)}")
        
        # 简单分词（实际应用中应使用jieba等分词工具）
        words = re.findall(r'[\w\u4e00-\u9fa5]+', text.lower())
        
        verbs = []
        nouns = []
        
        for word in words:
            if word in self.domain_verbs[self.language]:
                verbs.append(word)
            elif word in self.domain_nouns[self.language]:
                nouns.append(word)
        
        # 推断领域（简化版）
        domain = self._infer_domain(text)
        
        skeleton = Skeleton(
            source_domain=domain,
            verbs=list(set(verbs)),
            nouns=list(set(nouns)),
            raw_text=text
        )
        
        logger.info(f"提取骨架完成 - 动词: {verbs}, 名词: {nouns}, 领域: {domain}")
        return skeleton
    
    def _infer_domain(self, text: str) -> str:
        """推断文本所属领域"""
        if '生物' in text or '进化' in text:
            return 'biology'
        elif '计算机' in text or '代码' in text:
            return 'computer_science'
        elif '医学' in text or '病毒' in text:
            return 'medicine'
        return 'general'


class TransferLens:
    """通用迁移透镜：寻找跨域解决方案"""
    
    def __init__(self, knowledge_base: Optional[List[Skeleton]] = None):
        """
        初始化迁移透镜
        
        Args:
            knowledge_base: 预加载的骨架知识库
        """
        self.knowledge_base = knowledge_base or []
        self.vectorizer = TfidfVectorizer()
        self._build_vectors()
        logger.info(f"初始化迁移透镜，知识库大小: {len(self.knowledge_base)}")
    
    def _build_vectors(self) -> None:
        """构建骨架的向量表示"""
        if not self.knowledge_base:
            return
            
        corpus = []
        for skeleton in self.knowledge_base:
            text = " ".join(skeleton.verbs + skeleton.nouns)
            corpus.append(text)
        
        if corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
            logger.debug("TF-IDF向量矩阵构建完成")
    
    def add_to_knowledge_base(self, skeleton: Skeleton) -> None:
        """添加骨架到知识库"""
        if not isinstance(skeleton, Skeleton):
            raise TypeError("必须添加Skeleton类型的对象")
            
        self.knowledge_base.append(skeleton)
        self._build_vectors()
        logger.info(f"添加新骨架到知识库，当前大小: {len(self.knowledge_base)}")
    
    def find_analogous_solution(
        self, 
        problem_skeleton: Skeleton,
        top_k: int = 3,
        min_similarity: float = 0.3
    ) -> List[CrossDomainSolution]:
        """
        寻找跨域启发式解决方案
        
        Args:
            problem_skeleton: 问题骨架
            top_k: 返回的最相似解决方案数量
            min_similarity: 最小相似度阈值
            
        Returns:
            跨域解决方案列表
            
        Raises:
            ValueError: 当知识库为空或参数无效时
        """
        if not self.knowledge_base:
            raise ValueError("知识库为空，请先添加骨架")
            
        if top_k < 1:
            raise ValueError("top_k必须大于0")
            
        if not 0 <= min_similarity <= 1:
            raise ValueError("min_similarity必须在0到1之间")
            
        logger.info(f"开始寻找跨域解决方案，top_k={top_k}")
        
        # 构建查询向量
        query_text = " ".join(problem_skeleton.verbs + problem_skeleton.nouns)
        query_vec = self.vectorizer.transform([query_text])
        
        # 计算相似度
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # 获取top_k相似的骨架（排除同域）
        results = []
        for idx in similarities.argsort()[::-1]:
            candidate = self.knowledge_base[idx]
            score = similarities[idx]
            
            # 跳过同域和低相似度的
            if (candidate.source_domain == problem_skeleton.source_domain or 
                score < min_similarity):
                continue
                
            # 生成启发式映射
            mapping = self._generate_heuristic_mapping(
                problem_skeleton, candidate
            )
            
            solution = CrossDomainSolution(
                source_skeleton=candidate,
                target_skeleton=problem_skeleton,
                similarity_score=float(score),
                heuristic_mapping=mapping
            )
            
            results.append(solution)
            if len(results) >= top_k:
                break
        
        logger.info(f"找到 {len(results)} 个跨域解决方案")
        return results
    
    def _generate_heuristic_mapping(
        self,
        source: Skeleton,
        target: Skeleton
    ) -> Dict[str, str]:
        """生成启发式概念映射"""
        mapping = {}
        
        # 简单映射：基于顺序
        for i, verb in enumerate(source.verbs):
            if i < len(target.verbs):
                mapping[f"动作_{i+1}"] = f"{verb} -> {target.verbs[i]}"
        
        for i, noun in enumerate(source.nouns):
            if i < len(target.nouns):
                mapping[f"实体_{i+1}"] = f"{noun} -> {target.nouns[i]}"
        
        return mapping


def load_sample_knowledge_base() -> List[Skeleton]:
    """加载示例知识库"""
    return [
        Skeleton(
            source_domain="biology",
            verbs=["变异", "筛选", "进化"],
            nouns=["种群", "环境", "基因"],
            raw_text="生物进化是通过种群基因变异和环境筛选实现的"
        ),
        Skeleton(
            source_domain="computer_science",
            verbs=["修改", "测试", "迭代"],
            nouns=["代码", "用例", "版本"],
            raw_text="代码迭代是通过随机修改和单元测试实现的"
        ),
        Skeleton(
            source_domain="medicine",
            verbs=["识别", "防御", "清除"],
            nouns=["病毒", "抗体", "细胞"],
            raw_text="免疫系统通过识别病毒和产生抗体来防御和清除感染"
        ),
        Skeleton(
            source_domain="network_security",
            verbs=["检测", "隔离", "阻断"],
            nouns=["入侵", "防火墙", "流量"],
            raw_text="网络安全系统通过检测异常流量和隔离威胁来阻断入侵"
        )
    ]


def demonstrate_transfer_lens():
    """演示迁移透镜的使用"""
    print("\n=== 演示基于骨架剥离的通用迁移透镜 ===")
    
    # 初始化
    extractor = SkeletonExtractor(language='zh')
    knowledge_base = load_sample_knowledge_base()
    lens = TransferLens(knowledge_base)
    
    # 示例问题：计算机病毒防御
    problem_text = "计算机病毒不断变异，需要开发新的防御机制"
    problem_skeleton = extractor.extract(problem_text)
    
    print(f"\n问题骨架: {problem_skeleton.verbs} + {problem_skeleton.nouns}")
    
    # 寻找跨域解决方案
    solutions = lens.find_analogous_solution(
        problem_skeleton, 
        top_k=2,
        min_similarity=0.2
    )
    
    print("\n=== 跨域启发式解决方案 ===")
    for i, sol in enumerate(solutions, 1):
        print(f"\n方案 {i}:")
        print(f"源领域: {sol.source_skeleton.source_domain}")
        print(f"相似度: {sol.similarity_score:.2f}")
        print("启发式映射:")
        for key, value in sol.heuristic_mapping.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    demonstrate_transfer_lens()