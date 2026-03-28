"""
人机共生闭环 - 教学型交互模块

该模块实现了一个教学型交互系统，当AI遇到模糊指令时，能引导工人进行二元选择，
并将交互过程转化为新的语义节点，避免下次重复询问。

核心功能：
1. 模糊指令检测与解析
2. 二元选择引导界面
3. 交互历史记录与语义节点生成
4. 知识库更新与持久化

数据格式：
- 输入: {"instruction": str, "context": dict}
- 输出: {"clarified_instruction": str, "new_nodes": list, "confidence": float}

作者: AGI系统
版本: 1.0.0
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teaching_interaction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class SemanticNode:
    """语义节点数据结构"""
    node_id: str
    original_instruction: str
    clarified_instruction: str
    choices: List[str]
    selected_choice: str
    context: Dict
    created_at: str
    usage_count: int = 0


@dataclass
class InteractionSession:
    """交互会话数据结构"""
    session_id: str
    start_time: str
    end_time: Optional[str]
    nodes_created: List[str]
    status: str


class FuzzyInstructionError(Exception):
    """模糊指令异常"""
    pass


class TeachingInteractionSystem:
    """
    教学型交互系统
    
    该系统通过引导式对话将模糊指令转化为明确指令，并自动生成语义节点，
    实现人机知识共生。
    
    示例:
        >>> system = TeachingInteractionSystem()
        >>> result = system.process_instruction(
        ...     "把这个表面处理得光一点",
        ...     {"task_type": "surface_finishing"}
        ... )
        >>> print(result['clarified_instruction'])
    """
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化教学型交互系统
        
        参数:
            knowledge_base_path: 知识库存储路径，默认为当前目录下的knowledge_base.json
        """
        self.knowledge_base_path = Path(knowledge_base_path or 'knowledge_base.json')
        self.current_session: Optional[InteractionSession] = None
        self.semantic_nodes: Dict[str, SemanticNode] = {}
        self._initialize_system()
        logger.info("教学型交互系统初始化完成")
    
    def _initialize_system(self) -> None:
        """初始化系统，加载已有知识库"""
        try:
            if self.knowledge_base_path.exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for node_data in data.get('semantic_nodes', []):
                        node = SemanticNode(**node_data)
                        self.semantic_nodes[node.node_id] = node
                logger.info(f"已加载 {len(self.semantic_nodes)} 个语义节点")
            else:
                self._save_knowledge_base()
                logger.info("创建新的知识库")
        except Exception as e:
            logger.error(f"初始化系统失败: {e}")
            raise
    
    def _save_knowledge_base(self) -> None:
        """保存知识库到文件"""
        try:
            data = {
                'semantic_nodes': [asdict(node) for node in self.semantic_nodes.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.knowledge_base_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("知识库已保存")
        except Exception as e:
            logger.error(f"保存知识库失败: {e}")
            raise
    
    def _generate_binary_choices(self, fuzzy_term: str, context: Dict) -> Tuple[str, str]:
        """
        根据模糊术语生成二元选择
        
        参数:
            fuzzy_term: 模糊术语（如"光一点"）
            context: 上下文信息
            
        返回:
            包含两个选择的元组
            
        示例:
            >>> choices = self._generate_binary_choices("光一点", {"task_type": "surface_finishing"})
            >>> print(choices)
            ('镜面光', '哑光光')
        """
        # 模糊术语映射表（实际应用中可以从配置文件加载）
        choice_mappings = {
            '光': ('镜面光', '哑光光'),
            '亮': ('高亮', '柔光'),
            '平': ('完全平整', '保持纹理'),
            '快': ('最快速', '最稳定'),
            '好': ('高质量', '高效率'),
            '干净': ('无残留', '低污染'),
            '紧': ('紧密配合', '适中配合')
        }
        
        # 尝试匹配模糊术语
        for key, choices in choice_mappings.items():
            if key in fuzzy_term:
                logger.info(f"为模糊术语 '{fuzzy_term}' 生成选择: {choices}")
                return choices
        
        # 默认通用选择
        default_choices = ('选项A（推荐）', '选项B')
        logger.warning(f"未找到 '{fuzzy_term}' 的特定映射，使用默认选择")
        return default_choices
    
    def detect_fuzzy_instruction(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """
        检测指令中的模糊术语
        
        参数:
            instruction: 输入指令
            
        返回:
            (是否模糊, 模糊术语)的元组
            
        示例:
            >>> is_fuzzy, term = self.detect_fuzzy_instruction("把这个表面处理得光一点")
            >>> print(is_fuzzy, term)
            True 光一点
        """
        # 模糊术语模式库
        fuzzy_patterns = [
            r'(.{1,2})一点',  # XX一点
            r'比较(.{1,2})',   # 比较XX
            r'稍微(.{1,2})',   # 稍微XX
            r'太(.{1,2})',     # 太XX
            r'不够(.{1,2})',   # 不够XX
            r'(.{1,2})些',     # XX些
        ]
        
        for pattern in fuzzy_patterns:
            match = re.search(pattern, instruction)
            if match:
                fuzzy_term = match.group(0)
                logger.info(f"检测到模糊指令: '{instruction}' -> 模糊术语: '{fuzzy_term}'")
                return True, fuzzy_term
        
        logger.info(f"指令明确: '{instruction}'")
        return False, None
    
    def start_interaction_session(self) -> str:
        """
        开始新的交互会话
        
        返回:
            会话ID
        """
        session_id = str(uuid.uuid4())
        self.current_session = InteractionSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            nodes_created=[],
            status='active'
        )
        logger.info(f"开始新会话: {session_id}")
        return session_id
    
    def end_interaction_session(self) -> None:
        """结束当前交互会话"""
        if self.current_session:
            self.current_session.end_time = datetime.now().isoformat()
            self.current_session.status = 'completed'
            logger.info(f"会话结束: {self.current_session.session_id}")
            self.current_session = None
    
    def process_instruction(
        self,
        instruction: str,
        context: Optional[Dict] = None,
        auto_mode: bool = False
    ) -> Dict[str, Union[str, List, float]]:
        """
        处理输入指令（核心函数1）
        
        参数:
            instruction: 输入指令文本
            context: 指令上下文信息
            auto_mode: 自动模式（使用历史选择，默认False）
            
        返回:
            包含澄清结果、新节点和置信度的字典
            
        异常:
            FuzzyInstructionError: 当模糊指令无法处理时
            
        示例:
            >>> result = system.process_instruction(
            ...     "把这个表面处理得光一点",
            ...     {"task_type": "surface_finishing"}
            ... )
            >>> print(result['clarified_instruction'])
        """
        if not instruction or not isinstance(instruction, str):
            raise ValueError("指令必须是非空字符串")
        
        context = context or {}
        result = {
            'original_instruction': instruction,
            'clarified_instruction': instruction,
            'new_nodes': [],
            'confidence': 1.0,
            'interaction_required': False
        }
        
        # 检测模糊性
        is_fuzzy, fuzzy_term = self.detect_fuzzy_instruction(instruction)
        
        if not is_fuzzy:
            return result
        
        # 检查是否有历史语义节点可复用
        for node in self.semantic_nodes.values():
            if fuzzy_term in node.original_instruction:
                # 找到匹配的历史节点
                clarified = instruction.replace(
                    fuzzy_term,
                    node.selected_choice
                )
                result.update({
                    'clarified_instruction': clarified,
                    'confidence': 0.9,
                    'reused_node': node.node_id,
                    'interaction_required': False
                })
                node.usage_count += 1
                self._save_knowledge_base()
                logger.info(f"复用语义节点 {node.node_id}: {fuzzy_term} -> {node.selected_choice}")
                return result
        
        # 需要新的交互
        if auto_mode:
            # 自动模式：使用默认选择
            choice_a, choice_b = self._generate_binary_choices(fuzzy_term, context)
            selected_choice = choice_a  # 默认选择第一个选项
            confidence = 0.7
            logger.warning(f"自动模式选择: {selected_choice} (置信度: {confidence})")
        else:
            # 引导用户交互
            interaction_result = self._guide_binary_selection(
                instruction,
                fuzzy_term,
                context
            )
            selected_choice = interaction_result['selected_choice']
            confidence = interaction_result['confidence']
        
        # 生成明确指令
        clarified_instruction = instruction.replace(fuzzy_term, selected_choice)
        
        # 创建新的语义节点
        new_node = self._create_semantic_node(
            instruction,
            clarified_instruction,
            fuzzy_term,
            selected_choice,
            context
        )
        
        result.update({
            'clarified_instruction': clarified_instruction,
            'new_nodes': [new_node.node_id],
            'confidence': confidence,
            'interaction_required': not auto_mode
        })
        
        return result
    
    def _guide_binary_selection(
        self,
        instruction: str,
        fuzzy_term: str,
        context: Dict
    ) -> Dict[str, Union[str, float]]:
        """
        引导用户进行二元选择（核心函数2）
        
        参数:
            instruction: 原始指令
            fuzzy_term: 模糊术语
            context: 上下文信息
            
        返回:
            包含选择结果和置信度的字典
            
        示例:
            >>> result = self._guide_binary_selection(
            ...     "把这个表面处理得光一点",
            ...     "光一点",
            ...     {"task_type": "surface_finishing"}
            ... )
        """
        choice_a, choice_b = self._generate_binary_choices(fuzzy_term, context)
        
        # 模拟用户交互界面（实际应用中可以是GUI或语音交互）
        print("\n" + "="*60)
        print(f"AI需要澄清指令: '{instruction}'")
        print(f"模糊术语: '{fuzzy_term}'")
        print("\n请选择您期望的效果:")
        print(f"  [1] {choice_a}")
        print(f"  [2] {choice_b}")
        print("="*60)
        
        # 获取用户输入（这里用模拟输入，实际应用中替换为真实交互）
        # 在自动化测试中可以使用mock
        while True:
            try:
                # 模拟用户输入 - 实际应用中替换为 input()
                # user_input = input("请输入选择 (1/2): ")
                user_input = "1"  # 演示用，默认选择1
                
                if user_input == '1':
                    selected_choice = choice_a
                    confidence = 0.95
                    break
                elif user_input == '2':
                    selected_choice = choice_b
                    confidence = 0.95
                    break
                else:
                    print("无效输入，请输入 1 或 2")
            except KeyboardInterrupt:
                logger.warning("用户取消交互")
                selected_choice = choice_a
                confidence = 0.5
                break
        
        logger.info(f"用户选择: {selected_choice} (置信度: {confidence})")
        
        return {
            'selected_choice': selected_choice,
            'confidence': confidence,
            'interaction_type': 'binary_selection'
        }
    
    def _create_semantic_node(
        self,
        original_instruction: str,
        clarified_instruction: str,
        fuzzy_term: str,
        selected_choice: str,
        context: Dict
    ) -> SemanticNode:
        """
        创建新的语义节点（辅助函数）
        
        参数:
            original_instruction: 原始模糊指令
            clarified_instruction: 澄清后的明确指令
            fuzzy_term: 模糊术语
            selected_choice: 用户选择的明确术语
            context: 上下文信息
            
        返回:
            新创建的SemanticNode对象
        """
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        # 提取二元选择
        choices = list(self._generate_binary_choices(fuzzy_term, context))
        
        new_node = SemanticNode(
            node_id=node_id,
            original_instruction=original_instruction,
            clarified_instruction=clarified_instruction,
            choices=choices,
            selected_choice=selected_choice,
            context=context,
            created_at=datetime.now().isoformat(),
            usage_count=1
        )
        
        self.semantic_nodes[node_id] = new_node
        
        # 更新当前会话
        if self.current_session:
            self.current_session.nodes_created.append(node_id)
        
        self._save_knowledge_base()
        logger.info(f"创建新语义节点: {node_id} - {fuzzy_term} -> {selected_choice}")
        
        return new_node
    
    def get_semantic_nodes(self, filter_term: Optional[str] = None) -> List[Dict]:
        """
        获取语义节点列表
        
        参数:
            filter_term: 过滤术语（可选）
            
        返回:
            语义节点字典列表
        """
        nodes = []
        for node in self.semantic_nodes.values():
            if filter_term is None or filter_term in node.original_instruction:
                nodes.append(asdict(node))
        return nodes
    
    def export_knowledge_base(self, export_path: str) -> None:
        """
        导出知识库到指定路径
        
        参数:
            export_path: 导出文件路径
        """
        try:
            export_file = Path(export_path)
            data = {
                'semantic_nodes': [asdict(node) for node in self.semantic_nodes.values()],
                'exported_at': datetime.now().isoformat(),
                'total_nodes': len(self.semantic_nodes)
            }
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"知识库已导出到: {export_path}")
        except Exception as e:
            logger.error(f"导出知识库失败: {e}")
            raise


def demonstrate_system():
    """演示系统使用方法"""
    print("\n" + "="*60)
    print("教学型交互系统演示")
    print("="*60)
    
    # 初始化系统
    system = TeachingInteractionSystem()
    
    # 开始会话
    session_id = system.start_interaction_session()
    print(f"会话ID: {session_id}")
    
    # 示例1: 处理模糊指令
    print("\n--- 示例1: 表面处理模糊指令 ---")
    result1 = system.process_instruction(
        "把这个表面处理得光一点",
        {"task_type": "surface_finishing", "material": "metal"}
    )
    print(f"原始指令: {result1['original_instruction']}")
    print(f"明确指令: {result1['clarified_instruction']}")
    print(f"置信度: {result1['confidence']}")
    print(f"创建节点: {result1['new_nodes']}")
    
    # 示例2: 处理相同类型的模糊指令（应复用节点）
    print("\n--- 示例2: 重复模糊指令（测试知识复用） ---")
    result2 = system.process_instruction(
        "那个零件也要光一点",
        {"task_type": "surface_finishing", "material": "plastic"}
    )
    print(f"原始指令: {result2['original_instruction']}")
    print(f"明确指令: {result2['clarified_instruction']}")
    print(f"置信度: {result2['confidence']}")
    print(f"复用节点: {result2.get('reused_node', 'None')}")
    
    # 示例3: 处理明确指令
    print("\n--- 示例3: 明确指令 ---")
    result3 = system.process_instruction(
        "将表面抛光至Ra0.4",
        {"task_type": "surface_finishing"}
    )
    print(f"原始指令: {result3['original_instruction']}")
    print(f"明确指令: {result3['clarified_instruction']}")
    print(f"需要交互: {result3['interaction_required']}")
    
    # 查看所有语义节点
    print("\n--- 语义节点列表 ---")
    nodes = system.get_semantic_nodes()
    for node in nodes:
        print(f"ID: {node['node_id']}")
        print(f"  映射: '{node['original_instruction']}' -> '{node['clarified_instruction']}'")
        print(f"  使用次数: {node['usage_count']}")
    
    # 结束会话
    system.end_interaction_session()
    print("\n演示完成！")


if __name__ == "__main__":
    demonstrate_system()