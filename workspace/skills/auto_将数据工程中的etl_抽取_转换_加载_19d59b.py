import networkx as nx
import re
from typing import Dict, List, Tuple, Optional
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

class CognitiveETL:
    """
    实现数据工程中的ETL过程与认知清洗机制，将非结构化自然语言转换为DAG逻辑流。
    
    该类通过模拟人类认知过程，实现以下功能：
    1. 抽取(Extract)：从自然语言中提取关键实体和关系
    2. 转换(Transform)：应用认知清洗逻辑（归一化、去噪）
    3. 加载(Load)：构建有向无环图(DAG)逻辑流
    
    Attributes:
        stop_words (set): 停用词集合
        lemmatizer (WordNetLemmatizer): 词形还原器
        emotion_noise (set): 已知的情绪噪声词汇
    """
    
    def __init__(self):
        """
        初始化认知ETL处理器，下载必要的NLTK资源并设置清洗参数。
        """
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        except Exception as e:
            raise RuntimeError(f"NLTK资源下载失败: {str(e)}")
            
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.emotion_noise = {
            'hate', 'love', 'angry', 'sad', 'happy', 
            'disappointed', 'excited', 'frustrated'
        }
    
    def extract(self, text: str) -> List[Tuple[str, str]]:
        """
        从非结构化文本中抽取关键实体和关系。
        
        Args:
            text (str): 输入的自然语言文本
            
        Returns:
            List[Tuple[str, str]]: 实体-关系对列表
            
        Raises:
            ValueError: 当输入文本为空时
        """
        if not text.strip():
            raise ValueError("输入文本不能为空")
            
        try:
            tokens = word_tokenize(text.lower())
            tagged = nltk.pos_tag(tokens)
            
            # 提取名词短语作为实体
            entities = []
            current_entity = []
            
            for word, pos in tagged:
                if pos in ['NN', 'NNS', 'NNP', 'NNPS']:
                    current_entity.append(word)
                elif current_entity:
                    entities.append(' '.join(current_entity))
                    current_entity = []
            
            if current_entity:
                entities.append(' '.join(current_entity))
                
            # 提取动词短语作为关系
            relations = []
            for word, pos in tagged:
                if pos.startswith('VB'):
                    relations.append(self.lemmatizer.lemmatize(word, 'v'))
                    
            return [(entity, relation) for entity in entities for relation in relations]
            
        except Exception as e:
            raise RuntimeError(f"抽取过程失败: {str(e)}")
    
    def transform(self, extracted_data: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        应用认知清洗逻辑：归一化和去噪处理。
        
        Args:
            extracted_data (List[Tuple[str, str]]): 原始抽取的实体-关系对
            
        Returns:
            List[Tuple[str, str]]: 清洗后的实体-关系对
            
        Raises:
            TypeError: 当输入数据格式不正确时
        """
        if not isinstance(extracted_data, list):
            raise TypeError("输入数据必须是列表类型")
            
        cleaned_data = []
        
        for entity, relation in extracted_data:
            # 去噪：移除包含情绪噪声的实体
            if any(noise in entity.split() for noise in self.emotion_noise):
                continue
                
            # 归一化处理
            entity = re.sub(r'[^a-z0-9\s]', '', entity)
            relation = self.lemmatizer.lemmatize(relation, 'v')
            
            # 过滤停用词和空值
            if (entity not in self.stop_words and 
                relation not in self.stop_words and
                entity.strip() and relation.strip()):
                cleaned_data.append((entity, relation))
                
        return cleaned_data
    
    def load(self, transformed_data: List[Tuple[str, str]]) -> nx.DiGraph:
        """
        将清洗后的数据构建为有向无环图(DAG)逻辑流。
        
        Args:
            transformed_data (List[Tuple[str, str]]): 清洗后的实体-关系对
            
        Returns:
            nx.DiGraph: 表示逻辑流的有向无环图
            
        Raises:
            ValueError: 当无法构建有效DAG时
        """
        try:
            dag = nx.DiGraph()
            
            # 添加节点和边
            for entity, relation in transformed_data:
                dag.add_node(entity)
                dag.add_edge(entity, f"{entity}_{relation}")
                
            # 验证DAG有效性
            if not nx.is_directed_acyclic_graph(dag):
                raise ValueError("检测到循环依赖，无法构建有效DAG")
                
            return dag
            
        except Exception as e:
            raise RuntimeError(f"DAG构建失败: {str(e)}")
    
    def run(self, text: str) -> nx.DiGraph:
        """
        执行完整的认知ETL流程：抽取→转换→加载
        
        Args:
            text (str): 输入的自然语言文本
            
        Returns:
            nx.DiGraph: 最终构建的DAG逻辑流
            
        Raises:
            ValueError: 当输入无效时
            RuntimeError: 当处理流程失败时
        """
        if not text or not isinstance(text, str):
            raise ValueError("输入必须是有效的非空字符串")
            
        try:
            # 抽取阶段
            extracted = self.extract(text)
            
            # 转换阶段
            transformed = self.transform(extracted)
            
            # 加载阶段
            dag = self.load(transformed)
            
            return dag
            
        except Exception as e:
            raise RuntimeError(f"ETL流程执行失败: {str(e)}")


# 示例用法
if __name__ == "__main__":
    try:
        # 初始化认知ETL处理器
        etl_processor = CognitiveETL()
        
        # 示例输入文本（包含情绪噪声和模糊表达）
        input_text = """
        我讨厌处理这些混乱的客户数据，但必须提取用户信息并验证身份。
        系统应该自动清洗异常值并标准化格式，最后加载到数据仓库。
        """
        
        # 执行完整ETL流程
        result_dag = etl_processor.run(input_text)
        
        # 输出结果
        print("构建的DAG节点:", list(result_dag.nodes()))
        print("构建的DAG边:", list(result_dag.edges()))
        print("DAG是否为有向无环图:", nx.is_directed_acyclic_graph(result_dag))
        
    except Exception as e:
        print(f"错误: {str(e)}")