"""
名称: auto_自下而下的归纳聚类_在海量工业日志数据_d78853
描述: 【自下而上的归纳聚类】在海量工业日志数据中，如何设计算法自动发现‘频繁共现的节点组合’并将其固化为新的‘复合技能节点’？
     例如，发现‘预热’、‘检查油压’、‘低速启动’总是连续发生，从而归纳出‘冷启动标准流程’这一高阶概念。
领域: pattern_recognition
"""

import logging
import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LogNode:
    """
    基础日志节点类，用于表示工业日志中的单个事件。
    """
    def __init__(self, node_id: str, action: str, timestamp: datetime.datetime):
        self.node_id = node_id
        self.action = action
        self.timestamp = timestamp

    def __repr__(self):
        return f"LogNode(action='{self.action}')"


class CompositeSkill:
    """
    复合技能类，表示归纳出的高阶概念。
    """
    def __init__(self, skill_id: str, sub_nodes: List[str], description: str):
        self.skill_id = skill_id
        self.sub_nodes = sub_nodes
        self.description = description
        self.frequency = 0  # 出现频率

    def __repr__(self):
        return f"CompositeSkill(id='{self.skill_id}', nodes={self.sub_nodes}, freq={self.frequency})"


def validate_log_data(log_sequence: List[LogNode]) -> bool:
    """
    辅助函数：验证输入的日志数据是否符合处理要求。
    
    参数:
        log_sequence: 日志节点列表
        
    返回:
        bool: 数据是否有效
        
    异常:
        ValueError: 如果数据无效
    """
    if not isinstance(log_sequence, list):
        raise ValueError("输入必须是列表类型")
    
    if len(log_sequence) < 2:
        raise ValueError("日志序列长度必须至少为2")
    
    # 检查时间戳是否有序
    for i in range(1, len(log_sequence)):
        if log_sequence[i].timestamp < log_sequence[i-1].timestamp:
            logger.warning("日志时间戳未按升序排列")
            return False
    
    return True


def extract_action_sequences(log_sequence: List[LogNode], window_size: int = 3) -> List[Tuple[str, ...]]:
    """
    核心函数1：从日志序列中提取动作序列。
    
    参数:
        log_sequence: 日志节点列表
        window_size: 滑动窗口大小
        
    返回:
        动作序列的元组列表
        
    异常:
        ValueError: 如果窗口大小无效
    """
    if window_size < 2 or window_size > 10:
        raise ValueError("窗口大小必须在2到10之间")
    
    sequences = []
    
    try:
        for i in range(len(log_sequence) - window_size + 1):
            window = log_sequence[i:i+window_size]
            actions = tuple(node.action for node in window)
            sequences.append(actions)
            
        logger.info(f"从{len(log_sequence)}个日志节点中提取了{len(sequences)}个序列窗口")
        return sequences
    
    except Exception as e:
        logger.error(f"提取序列时发生错误: {str(e)}")
        raise


def discover_frequent_patterns(
    sequences: List[Tuple[str, ...]], 
    min_support: int = 2,
    min_confidence: float = 0.7
) -> Dict[Tuple[str, ...], int]:
    """
    核心函数2：发现频繁共现的动作模式。
    
    参数:
        sequences: 动作序列列表
        min_support: 最小支持度（出现次数）
        min_confidence: 最小置信度（比例）
        
    返回:
        频繁模式及其出现次数的字典
        
    异常:
        ValueError: 如果参数无效
    """
    if min_support < 1:
        raise ValueError("最小支持度必须至少为1")
    
    if not 0 <= min_confidence <= 1:
        raise ValueError("最小置信度必须在0到1之间")
    
    try:
        # 统计模式出现频率
        pattern_counter = Counter(sequences)
        
        # 过滤低频模式
        frequent_patterns = {
            pattern: count 
            for pattern, count in pattern_counter.items() 
            if count >= min_support
        }
        
        # 计算置信度（这里简化为只考虑支持度）
        # 在实际应用中，可能需要更复杂的置信度计算
        
        logger.info(f"发现{len(frequent_patterns)}个频繁模式")
        return frequent_patterns
    
    except Exception as e:
        logger.error(f"发现频繁模式时发生错误: {str(e)}")
        raise


def create_composite_skills(
    frequent_patterns: Dict[Tuple[str, ...], int],
    skill_prefix: str = "AUTO_"
) -> List[CompositeSkill]:
    """
    辅助函数：将频繁模式转换为复合技能节点。
    
    参数:
        frequent_patterns: 频繁模式字典
        skill_prefix: 技能ID前缀
        
    返回:
        复合技能列表
    """
    skills = []
    
    try:
        for idx, (pattern, freq) in enumerate(frequent_patterns.items(), 1):
            skill_id = f"{skill_prefix}{idx}"
            description = f"自动归纳的复合技能: {' -> '.join(pattern)}"
            
            skill = CompositeSkill(
                skill_id=skill_id,
                sub_nodes=list(pattern),
                description=description
            )
            skill.frequency = freq
            skills.append(skill)
            
        logger.info(f"创建了{len(skills)}个复合技能")
        return skills
    
    except Exception as e:
        logger.error(f"创建复合技能时发生错误: {str(e)}")
        raise


def analyze_log_patterns(log_sequence: List[LogNode]) -> List[CompositeSkill]:
    """
    主函数：分析日志序列并发现复合技能。
    
    参数:
        log_sequence: 日志节点列表
        
    返回:
        发现的复合技能列表
        
    使用示例:
        >>> logs = [
        ...     LogNode("1", "预热", datetime(2023, 1, 1, 8, 0)),
        ...     LogNode("2", "检查油压", datetime(2023, 1, 1, 8, 5)),
        ...     LogNode("3", "低速启动", datetime(2023, 1, 1, 8, 10)),
        ...     LogNode("4", "预热", datetime(2023, 1, 1, 9, 0)),
        ...     LogNode("5", "检查油压", datetime(2023, 1, 1, 9, 5)),
        ...     LogNode("6", "低速启动", datetime(2023, 1, 1, 9, 10))
        ... ]
        >>> skills = analyze_log_patterns(logs)
    """
    try:
        # 验证输入数据
        if not validate_log_data(log_sequence):
            raise ValueError("无效的日志数据")
        
        # 提取动作序列
        sequences = extract_action_sequences(log_sequence, window_size=3)
        
        # 发现频繁模式
        patterns = discover_frequent_patterns(sequences, min_support=2)
        
        # 创建复合技能
        skills = create_composite_skills(patterns)
        
        return skills
    
    except Exception as e:
        logger.error(f"日志模式分析失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 示例使用
    example_logs = [
        LogNode("1", "预热", datetime.datetime(2023, 1, 1, 8, 0)),
        LogNode("2", "检查油压", datetime.datetime(2023, 1, 1, 8, 5)),
        LogNode("3", "低速启动", datetime.datetime(2023, 1, 1, 8, 10)),
        LogNode("4", "正常运行", datetime.datetime(2023, 1, 1, 8, 15)),
        LogNode("5", "预热", datetime.datetime(2023, 1, 1, 9, 0)),
        LogNode("6", "检查油压", datetime.datetime(2023, 1, 1, 9, 5)),
        LogNode("7", "低速启动", datetime.datetime(2023, 1, 1, 9, 10)),
        LogNode("8", "正常运行", datetime.datetime(2023, 1, 1, 9, 15)),
    ]
    
    try:
        discovered_skills = analyze_log_patterns(example_logs)
        print("\n发现的复合技能:")
        for skill in discovered_skills:
            print(f"- {skill.skill_id}: {skill.description} (出现{skill.frequency}次)")
    except Exception as e:
        print(f"示例运行失败: {str(e)}")