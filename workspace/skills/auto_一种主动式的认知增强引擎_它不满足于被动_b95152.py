"""
主动式认知增强引擎

一种主动式的认知增强引擎。它不满足于被动回答问题，而是利用算法在现有的数千个节点中
寻找'结构洞'（Structural Holes）——即那些在逻辑上应该存在但在知识库中缺失的节点。
通过小样本抽象归纳和跨域类比（如将生物进化论映射到代码迭代），系统能够主动生成'假设性节点'
并请求人类验证，从而实现认知网络的自生长。

数据输入格式:
    - 知识节点: Dict[str, Any]，必须包含 'id', 'type', 'content', 'connections' 字段
    - 连接关系: List[Dict]，每个包含 'source', 'target', 'relation_type'

数据输出格式:
    - 假设节点: Dict[str, Any]，包含 'hypothesis_id', 'description', 'confidence', 'source_analogy'
    - 结构洞报告: Dict[str, Any]，包含 'hole_id', 'related_nodes', 'suggested_fill'
"""

import logging
import uuid
import json
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cognitive_engine.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class CognitiveEngineError(Exception):
    """认知引擎基础异常类"""
    pass


class NodeValidationError(CognitiveEngineError):
    """节点验证错误"""
    pass


class StructuralHoleDetectionError(CognitiveEngineError):
    """结构洞检测错误"""
    pass


@dataclass
class KnowledgeNode:
    """知识节点数据类"""
    id: str
    type: str
    content: str
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HypotheticalNode:
    """假设性节点数据类"""
    hypothesis_id: str
    description: str
    confidence: float
    source_analogy: str
    related_nodes: List[str]
    suggested_connections: List[str]
    creation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProactiveCognitiveEngine:
    """
    主动式认知增强引擎
    
    通过检测知识网络中的结构洞，利用跨域类比生成假设性节点，
    实现认知网络的主动生长。
    
    使用示例:
        >>> engine = ProactiveCognitiveEngine()
        >>> engine.load_knowledge_base("knowledge_nodes.json")
        >>> holes = engine.detect_structural_holes()
        >>> hypotheses = engine.generate_hypotheses(holes)
        >>> for h in hypotheses[:3]:
        ...     print(f"假设: {h.description} (置信度: {h.confidence:.2f})")
    """
    
    # 跨域类比映射模板
    ANALOGY_TEMPLATES = {
        ('biology', 'software'): {
            'pattern': '进化 -> 迭代',
            'mapping': {
                'natural_selection': 'code_review',
                'mutation': 'feature_branch',
                'adaptation': 'refactoring',
                'species': 'module'
            }
        },
        ('physics', 'economics'): {
            'pattern': '力学定律 -> 市场规律',
            'mapping': {
                'force': 'market_pressure',
                'momentum': 'market_trend',
                'friction': 'transaction_cost',
                'equilibrium': 'market_balance'
            }
        },
        ('chemistry', 'social'): {
            'pattern': '化学反应 -> 社会互动',
            'mapping': {
                'catalyst': 'influencer',
                'bond': 'relationship',
                'reaction': 'event',
                'solution': 'community'
            }
        }
    }
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化认知引擎
        
        Args:
            knowledge_base_path: 知识库文件路径（可选）
        """
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.connection_graph: Dict[str, Set[str]] = defaultdict(set)
        self.node_types: Dict[str, List[str]] = defaultdict(list)
        self.hypotheses: List[HypotheticalNode] = []
        
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        
        logger.info("主动式认知引擎初始化完成")
    
    def load_knowledge_base(self, file_path: str) -> None:
        """
        从JSON文件加载知识库
        
        Args:
            file_path: 知识库JSON文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            NodeValidationError: 节点数据验证失败
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'nodes' not in data:
                raise NodeValidationError("无效的知识库格式：需要包含'nodes'字段")
            
            for node_data in data['nodes']:
                self._validate_node_data(node_data)
                node = KnowledgeNode(**node_data)
                self._add_node_to_graph(node)
            
            logger.info(f"成功加载 {len(self.nodes)} 个知识节点")
            
        except FileNotFoundError:
            logger.error(f"知识库文件不存在: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            raise NodeValidationError(f"JSON格式错误: {e}")
    
    def _validate_node_data(self, node_data: Dict[str, Any]) -> None:
        """
        验证节点数据的完整性和有效性
        
        Args:
            node_data: 待验证的节点数据
            
        Raises:
            NodeValidationError: 数据验证失败
        """
        required_fields = ['id', 'type', 'content', 'connections']
        
        if not isinstance(node_data, dict):
            raise NodeValidationError("节点数据必须是字典类型")
        
        for field in required_fields:
            if field not in node_data:
                raise NodeValidationError(f"缺少必需字段: {field}")
        
        if not isinstance(node_data['id'], str) or not node_data['id'].strip():
            raise NodeValidationError("节点ID必须是非空字符串")
        
        if not isinstance(node_data['connections'], list):
            raise NodeValidationError("connections必须是列表类型")
        
        # 边界检查
        if len(node_data['content']) > 10000:
            logger.warning(f"节点 {node_data['id']} 内容过长，可能影响处理效率")
    
    def _add_node_to_graph(self, node: KnowledgeNode) -> None:
        """
        将节点添加到知识图谱
        
        Args:
            node: 知识节点对象
        """
        self.nodes[node.id] = node
        self.node_types[node.type].append(node.id)
        
        for connected_id in node.connections:
            if connected_id in self.nodes:
                self.connection_graph[node.id].add(connected_id)
                self.connection_graph[connected_id].add(node.id)
    
    def detect_structural_holes(self, min_connection_threshold: int = 2) -> List[Dict[str, Any]]:
        """
        检测知识网络中的结构洞
        
        结构洞是指那些在逻辑上应该存在连接但实际上没有连接的节点对，
        或者是应该存在但缺失的中间概念节点。
        
        Args:
            min_connection_threshold: 最小连接阈值，用于识别潜在的桥接节点
            
        Returns:
            List[Dict]: 检测到的结构洞列表
            
        Raises:
            StructuralHoleDetectionError: 检测过程出错
        """
        if len(self.nodes) < 3:
            logger.warning("节点数量过少，无法进行有效的结构洞检测")
            return []
        
        structural_holes = []
        
        try:
            # 方法1: 检测缺失的桥接节点
            holes = self._find_missing_bridges(min_connection_threshold)
            structural_holes.extend(holes)
            
            # 方法2: 检测同类型节点间的连接缺失
            type_holes = self._find_intra_type_gaps()
            structural_holes.extend(type_holes)
            
            # 方法3: 检测跨域连接缺失
            cross_domain_holes = self._find_cross_domain_gaps()
            structural_holes.extend(cross_domain_holes)
            
            logger.info(f"检测到 {len(structural_holes)} 个潜在结构洞")
            return structural_holes
            
        except Exception as e:
            logger.error(f"结构洞检测失败: {e}")
            raise StructuralHoleDetectionError(f"检测过程出错: {e}")
    
    def _find_missing_bridges(self, threshold: int) -> List[Dict[str, Any]]:
        """
        寻找缺失的桥接节点
        
        当两个节点有多个共同邻居但没有直接连接时，
        可能存在一个缺失的中间概念。
        """
        holes = []
        checked_pairs: Set[Tuple[str, str]] = set()
        
        for node_id, connections in self.connection_graph.items():
            for neighbor_id in connections:
                pair = tuple(sorted([node_id, neighbor_id]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
                
                # 寻找共同邻居
                common_neighbors = self.connection_graph[node_id] & self.connection_graph[neighbor_id]
                
                if len(common_neighbors) >= threshold:
                    # 检查是否直接连接
                    if neighbor_id not in self.connection_graph[node_id]:
                        holes.append({
                            'hole_id': f"bridge_{uuid.uuid4().hex[:8]}",
                            'type': 'missing_bridge',
                            'related_nodes': [node_id, neighbor_id],
                            'common_neighbors': list(common_neighbors),
                            'significance': len(common_neighbors) / len(self.nodes)
                        })
        
        return holes
    
    def _find_intra_type_gaps(self) -> List[Dict[str, Any]]:
        """
        寻找同类型节点间的连接缺失
        """
        holes = []
        
        for node_type, node_ids in self.node_types.items():
            if len(node_ids) < 3:
                continue
            
            # 计算该类型节点的连接密度
            possible_connections = len(node_ids) * (len(node_ids) - 1) / 2
            actual_connections = 0
            
            for node_id in node_ids:
                type_connections = [n for n in self.connection_graph[node_id] if n in node_ids]
                actual_connections += len(type_connections)
            
            actual_connections /= 2  # 每条连接被计算了两次
            density = actual_connections / possible_connections if possible_connections > 0 else 0
            
            # 如果密度低于阈值，标记为结构洞
            if density < 0.3:
                holes.append({
                    'hole_id': f"intra_type_{node_type}_{uuid.uuid4().hex[:8]}",
                    'type': 'intra_type_gap',
                    'node_type': node_type,
                    'related_nodes': node_ids[:5],  # 只取前5个作为示例
                    'density': density,
                    'significance': 1 - density
                })
        
        return holes
    
    def _find_cross_domain_gaps(self) -> List[Dict[str, Any]]:
        """
        寻找跨域连接缺失
        """
        holes = []
        types = list(self.node_types.keys())
        
        for i, type1 in enumerate(types):
            for type2 in types[i+1:]:
                # 检查是否有类比模板
                analogy_key = (type1, type2)
                reverse_key = (type2, type1)
                
                has_analogy = analogy_key in self.ANALOGY_TEMPLATES or reverse_key in self.ANALOGY_TEMPLATES
                
                # 计算跨域连接数
                cross_connections = 0
                for node_id in self.node_types[type1]:
                    cross_conns = [n for n in self.connection_graph[node_id] 
                                   if n in self.node_types.get(type2, [])]
                    cross_connections += len(cross_conns)
                
                # 如果存在类比模板但连接稀疏，标记为结构洞
                if has_analogy and cross_connections < 2:
                    holes.append({
                        'hole_id': f"cross_domain_{type1}_{type2}_{uuid.uuid4().hex[:8]}",
                        'type': 'cross_domain_gap',
                        'domains': [type1, type2],
                        'cross_connections': cross_connections,
                        'has_analogy_template': has_analogy,
                        'significance': 0.8 if has_analogy else 0.4
                    })
        
        return holes
    
    def generate_hypotheses(self, structural_holes: List[Dict[str, Any]], 
                           max_hypotheses: int = 10) -> List[HypotheticalNode]:
        """
        基于结构洞生成假设性节点
        
        利用跨域类比和小样本抽象归纳，生成可能填补结构洞的假设性概念。
        
        Args:
            structural_holes: 检测到的结构洞列表
            max_hypotheses: 最大假设数量
            
        Returns:
            List[HypotheticalNode]: 生成的假设性节点列表
        """
        if not structural_holes:
            logger.warning("没有结构洞可供生成假设")
            return []
        
        hypotheses = []
        
        # 按重要性排序
        sorted_holes = sorted(structural_holes, key=lambda x: x.get('significance', 0), reverse=True)
        
        for hole in sorted_holes[:max_hypotheses]:
            try:
                hypothesis = self._generate_single_hypothesis(hole)
                if hypothesis:
                    hypotheses.append(hypothesis)
            except Exception as e:
                logger.error(f"生成假设失败 (hole: {hole['hole_id']}): {e}")
                continue
        
        self.hypotheses.extend(hypotheses)
        logger.info(f"成功生成 {len(hypotheses)} 个假设性节点")
        return hypotheses
    
    def _generate_single_hypothesis(self, hole: Dict[str, Any]) -> Optional[HypotheticalNode]:
        """
        为单个结构洞生成假设
        """
        hole_type = hole.get('type', '')
        
        if hole_type == 'missing_bridge':
            return self._generate_bridge_hypothesis(hole)
        elif hole_type == 'intra_type_gap':
            return self._generate_intra_type_hypothesis(hole)
        elif hole_type == 'cross_domain_gap':
            return self._generate_cross_domain_hypothesis(hole)
        
        return None
    
    def _generate_bridge_hypothesis(self, hole: Dict[str, Any]) -> HypotheticalNode:
        """
        为桥接型结构洞生成假设
        """
        related_nodes = hole['related_nodes']
        node1 = self.nodes.get(related_nodes[0])
        node2 = self.nodes.get(related_nodes[1])
        
        if not node1 or not node2:
            raise ValueError("无法找到相关节点")
        
        # 提取共同主题
        common_themes = self._extract_common_themes(node1.content, node2.content)
        
        # 生成假设描述
        description = (
            f"假设存在一个桥接概念，连接 '{node1.type}' 和 '{node2.type}' 领域，"
            f"可能涉及以下共同主题: {', '.join(common_themes[:3])}"
        )
        
        return HypotheticalNode(
            hypothesis_id=f"hyp_bridge_{uuid.uuid4().hex[:8]}",
            description=description,
            confidence=0.6 + hole['significance'] * 0.3,
            source_analogy="桥接归纳",
            related_nodes=related_nodes,
            suggested_connections=hole.get('common_neighbors', [])[:3]
        )
    
    def _generate_intra_type_hypothesis(self, hole: Dict[str, Any]) -> HypotheticalNode:
        """
        为同类型缺口生成假设
        """
        node_type = hole['node_type']
        density = hole['density']
        
        description = (
            f"在 '{node_type}' 类型节点中存在连接稀疏区域 (密度: {density:.2f})，"
            f"假设存在一个整合性概念可以增强该领域的内部连贯性"
        )
        
        return HypotheticalNode(
            hypothesis_id=f"hyp_intra_{uuid.uuid4().hex[:8]}",
            description=description,
            confidence=0.5 + (1 - density) * 0.4,
            source_analogy="领域内整合",
            related_nodes=hole['related_nodes'],
            suggested_connections=hole['related_nodes'][:3]
        )
    
    def _generate_cross_domain_hypothesis(self, hole: Dict[str, Any]) -> HypotheticalNode:
        """
        为跨域缺口生成假设（使用类比推理）
        """
        domains = hole['domains']
        domain1, domain2 = domains
        
        # 查找类比模板
        analogy_key = (domain1, domain2)
        reverse_key = (domain2, domain1)
        
        template = self.ANALOGY_TEMPLATES.get(analogy_key) or self.ANALOGY_TEMPLATES.get(reverse_key)
        
        if template:
            # 使用类比模板生成假设
            pattern = template['pattern']
            mapping = template['mapping']
            
            sample_mappings = list(mapping.items())[:2]
            mapping_desc = ", ".join([f"'{k}' -> '{v}'" for k, v in sample_mappings])
            
            description = (
                f"基于跨域类比 ({pattern})，假设 '{domain1}' 和 '{domain2}' 之间存在"
                f"可映射的概念关系。示例映射: {mapping_desc}"
            )
            
            confidence = 0.7 + hole['significance'] * 0.2
            source = f"跨域类比: {pattern}"
        else:
            description = (
                f"在 '{domain1}' 和 '{domain2}' 之间存在概念连接缺失，"
                f"建议探索两个领域间的潜在映射关系"
            )
            confidence = 0.4
            source = "跨域探索"
        
        return HypotheticalNode(
            hypothesis_id=f"hyp_cross_{uuid.uuid4().hex[:8]}",
            description=description,
            confidence=confidence,
            source_analogy=source,
            related_nodes=self.node_types.get(domain1, [])[:2] + self.node_types.get(domain2, [])[:2],
            suggested_connections=[]
        )
    
    def _extract_common_themes(self, content1: str, content2: str) -> List[str]:
        """
        从两段内容中提取共同主题（简化版本）
        """
        # 简单的关键词提取（实际应用中可使用NLP技术）
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        common = words1 & words2
        # 过滤掉常见词
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                     'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                     'from', 'as', 'into', 'through', 'during', 'before', 'after',
                     'above', 'below', 'between', 'under', 'again', 'further', 'then',
                     'once', 'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                     'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very'}
        
        themes = [w for w in common if w not in stopwords and len(w) > 3]
        return sorted(themes)[:5]
    
    def export_hypotheses(self, output_path: str) -> None:
        """
        导出假设性节点到JSON文件
        
        Args:
            output_path: 输出文件路径
        """
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'total_hypotheses': len(self.hypotheses),
                'hypotheses': [h.to_dict() for h in self.hypotheses]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出 {len(self.hypotheses)} 个假设到 {output_path}")
            
        except Exception as e:
            logger.error(f"导出假设失败: {e}")
            raise


def create_sample_knowledge_base(output_path: str = "sample_knowledge.json") -> str:
    """
    创建示例知识库用于测试
    
    Args:
        output_path: 输出文件路径
        
    Returns:
        str: 创建的文件路径
    """
    nodes = [
        {
            "id": "bio_001",
            "type": "biology",
            "content": "自然选择是进化的核心机制，通过适应环境的个体生存和繁殖来推动物种演变",
            "connections": ["bio_002", "bio_003"],
            "metadata": {"domain": "evolution"}
        },
        {
            "id": "bio_002",
            "type": "biology",
            "content": "基因突变提供了遗传变异的原始材料，是进化的基础",
            "connections": ["bio_001"],
            "metadata": {"domain": "genetics"}
        },
        {
            "id": "bio_003",
            "type": "biology",
            "content": "物种形成是通过生殖隔离产生新物种的过程",
            "connections": ["bio_001"],
            "metadata": {"domain": "speciation"}
        },
        {
            "id": "sw_001",
            "type": "software",
            "content": "代码审查是保证软件质量的重要实践，通过同行评审发现潜在问题",
            "connections": ["sw_002"],
            "metadata": {"domain": "quality"}
        },
        {
            "id": "sw_002",
            "type": "software",
            "content": "功能分支允许开发者在不影响主干的情况下进行功能开发和实验",
            "connections": ["sw_001"],
            "metadata": {"domain": "version_control"}
        },
        {
            "id": "sw_003",
            "type": "software",
            "content": "重构是改善代码结构而不改变其外部行为的过程",
            "connections": [],
            "metadata": {"domain": "maintenance"}
        },
        {
            "id": "phys_001",
            "type": "physics",
            "content": "牛顿运动定律描述了力与运动之间的关系",
            "connections": ["phys_002"],
            "metadata": {"domain": "mechanics"}
        },
        {
            "id": "phys_002",
            "type": "physics",
            "content": "动量守恒定律说明在没有外力作用下系统总动量保持不变",
            "connections": ["phys_001"],
            "metadata": {"domain": "mechanics"}
        },
        {
            "id": "econ_001",
            "type": "economics",
            "content": "市场均衡是供给与需求相等时的稳定状态",
            "connections": [],
            "metadata": {"domain": "market"}
        },
        {
            "id": "econ_002",
            "type": "economics",
            "content": "交易成本包括搜索、谈判和监督合同执行的所有费用",
            "connections": [],
            "metadata": {"domain": "transaction"}
        }
    ]
    
    data = {"nodes": nodes}
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path


# 主程序示例
if __name__ == "__main__":
    print("=" * 60)
    print("主动式认知增强引擎演示")
    print("=" * 60)
    
    # 创建示例知识库
    kb_path = create_sample_knowledge_base()
    print(f"\n[1] 创建示例知识库: {kb_path}")
    
    # 初始化引擎
    engine = ProactiveCognitiveEngine(kb_path)
    print(f"\n[2] 加载知识节点: {len(engine.nodes)} 个")
    
    # 检测结构洞
    print("\n[3] 检测结构洞...")
    holes = engine.detect_structural_holes()
    print(f"    发现 {len(holes)} 个潜在结构洞")
    
    # 显示部分结构洞
    for i, hole in enumerate(holes[:3]):
        print(f"\n    结构洞 #{i+1}:")
        print(f"      类型: {hole['type']}")
        print(f"      重要性: {hole['significance']:.2f}")
    
    # 生成假设
    print("\n[4] 生成假设性节点...")
    hypotheses = engine.generate_hypotheses(holes, max_hypotheses=5)
    
    # 显示假设
    print(f"\n    生成 {len(hypotheses)} 个假设性概念:\n")
    for i, hyp in enumerate(hypotheses):
        print(f"    假设 #{i+1}:")
        print(f"      ID: {hyp.hypothesis_id}")
        print(f"      描述: {hyp.description[:80]}...")
        print(f"      置信度: {hyp.confidence:.2f}")
        print(f"      来源: {hyp.source_analogy}")
        print()
    
    # 导出结果
    output_path = "hypotheses_export.json"
    engine.export_hypotheses(output_path)
    print(f"[5] 假设已导出到: {output_path}")
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)