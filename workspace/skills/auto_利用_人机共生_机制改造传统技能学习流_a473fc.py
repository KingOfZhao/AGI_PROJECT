import networkx as nx
import random
from typing import Dict, List, Set, Tuple, Optional

class AdaptiveSkillLearning:
    """
    利用'人机共生'机制改造传统技能学习流的AI系统。
    
    该系统通过动态调整训练难度与维度，实现技能的适应性内化。
    核心机制包括：
    1. 实时反馈驱动：根据学习者表现动态调整
    2. 跨域重叠：在多个领域间建立知识连接
    3. 实践-反馈-概念重构闭环：持续优化学习路径
    
    Attributes:
        graph (nx.DiGraph): 技能知识图谱，节点表示技能概念，边表示依赖关系
        current_node (str): 当前学习的技能节点
        domains (Set[str]): 支持的领域集合
        difficulty_range (Tuple[int, int]): 难度范围(1-10)
    """
    
    def __init__(self):
        """初始化自适应技能学习系统"""
        self.graph = nx.DiGraph()
        self.current_node = None
        self.domains = {'math', 'physics', 'programming', 'biology'}
        self.difficulty_range = (1, 10)
        self._initialize_graph()
        
    def _initialize_graph(self) -> None:
        """初始化技能知识图谱"""
        # 添加技能节点 (节点名: 领域, 难度, 掌握程度)
        nodes = [
            ('addition', {'math'}, 1, 0.5),
            ('subtraction', {'math'}, 1, 0.5),
            ('vector', {'math', 'physics'}, 3, 0.3),
            ('force', {'physics'}, 2, 0.4),
            ('loop', {'programming'}, 2, 0.6),
            ('dna_replication', {'biology'}, 4, 0.2),
            ('algorithm', {'programming', 'math'}, 5, 0.3),
            ('energy', {'physics', 'biology'}, 4, 0.4)
        ]
        
        for name, domains, difficulty, mastery in nodes:
            self.graph.add_node(
                name,
                domains=set(domains),
                difficulty=difficulty,
                mastery=mastery,
                consecutive_success=0,
                consecutive_failure=0
            )
        
        # 添加技能依赖关系
        edges = [
            ('addition', 'subtraction'),
            ('addition', 'vector'),
            ('subtraction', 'vector'),
            ('vector', 'force'),
            ('loop', 'algorithm'),
            ('algorithm', 'energy'),
            ('vector', 'algorithm')
        ]
        
        for src, dst in edges:
            self.graph.add_edge(src, dst, type='dependency')
        
        # 设置起始节点
        self.current_node = 'addition'
    
    def generate_practice(self) -> Tuple[str, Dict]:
        """
        生成个性化练习内容
        
        Returns:
            Tuple[str, Dict]: (练习节点, 练习配置)
            
        Raises:
            ValueError: 当知识图谱为空时
        """
        if not self.graph.nodes:
            raise ValueError("知识图谱为空，无法生成练习")
            
        current_data = self.graph.nodes[self.current_node]
        candidates = self._get_candidate_nodes()
        
        # 根据掌握程度选择难度
        if current_data['mastery'] > 0.7:
            # 高掌握度：选择更高难度或跨域节点
            target_difficulty = min(10, current_data['difficulty'] + 1)
            domain_overlap = True
        elif current_data['mastery'] < 0.3:
            # 低掌握度：选择更低难度节点
            target_difficulty = max(1, current_data['difficulty'] - 1)
            domain_overlap = False
        else:
            # 中等掌握度：保持当前难度
            target_difficulty = current_data['difficulty']
            domain_overlap = random.choice([True, False])
        
        # 筛选候选节点
        filtered = []
        for node in candidates:
            node_data = self.graph.nodes[node]
            if (target_difficulty - 1 <= node_data['difficulty'] <= target_difficulty + 1 and
                (domain_overlap and node_data['domains'] & current_data['domains'] or
                 not domain_overlap)):
                filtered.append(node)
        
        if not filtered:
            filtered = candidates  # 回退到所有候选节点
        
        # 根据连续成功/失败次数调整选择倾向
        if current_data['consecutive_success'] >= 2:
            # 连续成功：优先选择高难度节点
            filtered.sort(key=lambda x: self.graph.nodes[x]['difficulty'], reverse=True)
        elif current_data['consecutive_failure'] >= 2:
            # 连续失败：优先选择低难度节点
            filtered.sort(key=lambda x: self.graph.nodes[x]['difficulty'])
        
        next_node = random.choice(filtered[:3])  # 从前3个中随机选择
        
        # 生成练习配置
        practice_config = {
            'node': next_node,
            'domains': list(self.graph.nodes[next_node]['domains']),
            'difficulty': self.graph.nodes[next_node]['difficulty'],
            'adaptive_hints': self._generate_hints(next_node),
            'cross_domain_tasks': self._generate_cross_domain_tasks(next_node)
        }
        
        return next_node, practice_config
    
    def _get_candidate_nodes(self) -> List[str]:
        """获取候选练习节点"""
        # 获取与当前节点直接或间接相关的节点
        related = set(self.graph.successors(self.current_node))
        related.update(self.graph.predecessors(self.current_node))
        related.add(self.current_node)  # 包含当前节点
        
        # 获取跨域节点（与当前节点无直接关系但有领域重叠）
        current_domains = self.graph.nodes[self.current_node]['domains']
        for node, data in self.graph.nodes(data=True):
            if node not in related and data['domains'] & current_domains:
                related.add(node)
        
        # 添加随机节点以增加探索性
        all_nodes = set(self.graph.nodes())
        unrelated = list(all_nodes - related)
        if unrelated:
            related.add(random.choice(unrelated))
        
        return list(related)
    
    def _generate_hints(self, node: str) -> List[str]:
        """生成自适应提示"""
        mastery = self.graph.nodes[node]['mastery']
        if mastery < 0.3:
            return ["基础概念回顾", "分步示例演示"]
        elif mastery < 0.7:
            return ["关键点提示", "常见错误分析"]
        else:
            return ["高级应用场景", "跨领域关联探索"]
    
    def _generate_cross_domain_tasks(self, node: str) -> List[str]:
        """生成跨领域任务"""
        node_domains = self.graph.nodes[node]['domains']
        tasks = []
        
        for domain in self.domains:
            if domain not in node_domains:
                # 为其他领域生成相关任务
                if domain == 'math' and 'physics' in node_domains:
                    tasks.append("将物理问题转化为数学方程")
                elif domain == 'programming' and 'math' in node_domains:
                    tasks.append("用编程实现数学算法")
                elif domain == 'biology' and 'physics' in node_domains:
                    tasks.append("分析生物系统中的物理原理")
        
        return tasks if tasks else ["综合应用练习"]
    
    def record_feedback(self, correct: bool, time_taken: Optional[float] = None) -> None:
        """
        记录学习反馈并更新知识图谱
        
        Args:
            correct: 练习是否正确
            time_taken: 完成练习耗时(秒)
            
        Raises:
            ValueError: 当当前节点不存在时
        """
        if self.current_node not in self.graph:
            raise ValueError(f"节点 {self.current_node} 不存在于知识图谱中")
            
        node_data = self.graph.nodes[self.current_node]
        
        # 更新连续成功/失败计数
        if correct:
            node_data['consecutive_success'] += 1
            node_data['consecutive_failure'] = 0
            # 增加掌握程度（难度越高增加越多）
            mastery_gain = 0.1 * (1 + node_data['difficulty'] / 10)
            node_data['mastery'] = min(1.0, node_data['mastery'] + mastery_gain)
        else:
            node_data['consecutive_failure'] += 1
            node_data['consecutive_success'] = 0
            # 减少掌握程度（难度越高减少越少）
            mastery_loss = 0.05 * (1 - node_data['difficulty'] / 10)
            node_data['mastery'] = max(0.0, node_data['mastery'] - mastery_loss)
        
        # 动态调整难度
        if node_data['consecutive_success'] >= 3:
            node_data['difficulty'] = min(10, node_data['difficulty'] + 1)
            node_data['consecutive_success'] = 0
        elif node_data['consecutive_failure'] >= 3:
            node_data['difficulty'] = max(1, node_data['difficulty'] - 1)
            node_data['consecutive_failure'] = 0
        
        # 更新当前节点
        self.current_node = self._select_next_node()
    
    def _select_next_node(self) -> str:
        """根据当前状态选择下一个学习节点"""
        current_data = self.graph.nodes[self.current_node]
        candidates = self._get_candidate_nodes()
        
        # 根据掌握程度选择倾向
        if current_data['mastery'] > 0.7:
            # 高掌握度：优先选择高难度或跨域节点
            candidates.sort(key=lambda x: (
                self.graph.nodes[x]['difficulty'],
                len(self.graph.nodes[x]['domains'])
            ), reverse=True)
        elif current_data['mastery'] < 0.3:
            # 低掌握度：优先选择低难度节点
            candidates.sort(key=lambda x: self.graph.nodes[x]['difficulty'])
        else:
            # 中等掌握度：随机选择
            random.shuffle(candidates)
        
        return candidates[0]
    
    def reconstruct_concept(self) -> None:
        """
        执行概念重构：根据学习历史优化知识图谱结构
        """
        # 1. 移除掌握程度过低的节点
        to_remove = [
            node for node, data in self.graph.nodes(data=True)
            if data['mastery'] < 0.1 and data['consecutive_failure'] >= 5
        ]
        for node in to_remove:
            self.graph.remove_node(node)
        
        # 2. 添加新的跨域连接
        nodes = list(self.graph.nodes())
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                node1, node2 = nodes[i], nodes[j]
                data1, data2 = self.graph.nodes[node1], self.graph.nodes[node2]
                
                # 如果有领域重叠且无连接，添加关联边
                if data1['domains'] & data2['domains'] and not self.graph.has_edge(node1, node2):
                    self.graph.add_edge(node1, node2, type='cross_domain')
        
        # 3. 调整节点难度分布
        for node, data in self.graph.nodes(data=True):
            if data['mastery'] > 0.8 and data['difficulty'] < 8:
                data['difficulty'] += 1
            elif data['mastery'] < 0.2 and data['difficulty'] > 2:
                data['difficulty'] -= 1


# 示例使用
if __name__ == "__main__":
    try:
        # 初始化学习系统
        learner = AdaptiveSkillLearning()
        
        # 模拟学习流程
        for _ in range(5):
            # 生成练习
            node, practice = learner.generate_practice()
            print(f"\n当前练习: {node} (难度: {practice['difficulty']}, 领域: {practice['domains']})")
            print(f"自适应提示: {practice['adaptive_hints']}")
            print(f"跨域任务: {practice['cross_domain_tasks']}")
            
            # 模拟练习结果 (随机正确/错误)
            correct = random.choice([True, False])
            print(f"练习结果: {'正确' if correct else '错误'}")
            
            # 记录反馈
            learner.record_feedback(correct)
            
            # 每3次反馈执行一次概念重构
            if _ % 3 == 2:
                learner.reconstruct_concept()
                print("执行概念重构...")
        
        print("\n最终知识图谱状态:")
        for node, data in learner.graph.nodes(data=True):
            print(f"{node}: 掌握程度={data['mastery']:.2f}, 难度={data['difficulty']}")
            
    except Exception as e:
        print(f"发生错误: {str(e)}")