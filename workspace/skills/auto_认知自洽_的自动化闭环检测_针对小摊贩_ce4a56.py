"""
模块: auto_cognitive_closure_detector.py
名称: auto_认知自洽_的自动化闭环检测_针对小摊贩_ce4a56
描述:
    针对“小摊贩”等非结构化商业场景的“认知自洽”闭环检测系统。
    本模块旨在建立“策略输出 -> 现实反馈 -> 认知更新”的自动化闭环。
    
    核心挑战:
    现实反馈往往是非结构化的自然语言（如：“今天没人买”、“天气太热”等）。
    本系统通过NLP特征提取，将这些反馈映射为结构化数据，进而更新策略节点的
    成功率参数，实现AI认知与物理世界的同步。

Core Components:
    - StrategyNode: 定义策略节点的数据结构。
    - FeedbackInterpreter: 基于关键词的情感/特征提取器。
    - CognitiveLoopMonitor: 闭环检测与参数更新引擎。

Author: AGI System Architect
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class StrategyNode:
    """
    策略节点类，代表AI生成的一个具体策略。
    
    Attributes:
        node_id (str): 策略唯一标识符。
        content (str): 策略内容描述 (e.g., "将摊位移至地铁口")。
        success_rate (float): 当前策略的成功率 (0.0 到 1.0)。
        sample_count (int): 累计反馈样本数。
        last_updated (str): 最后更新时间戳。
    """
    node_id: str
    content: str
    success_rate: float = 0.5  # 默认先验概率
    sample_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_metrics(self, is_success: bool, weight: float = 1.0):
        """根据新反馈更新成功率和样本数（使用贝叶斯平滑思想）。"""
        old_rate = self.success_rate
        n = self.sample_count
        
        # 简单的加权移动平均更新
        new_val = 1.0 if is_success else 0.0
        updated_rate = ((old_rate * n) + (new_val * weight)) / (n + weight)
        
        self.success_rate = round(updated_rate, 4)
        self.sample_count += 1
        self.last_updated = datetime.now().isoformat()
        logger.info(f"Node {self.node_id} updated: Rate {old_rate:.2f} -> {self.success_rate:.2f}")

# --- 辅助函数 ---

def preprocess_text(text: str) -> str:
    """
    辅助函数：清洗非结构化文本。
    去除多余空格、标点，转小写。
    
    Args:
        text (str): 原始输入文本。
    
    Returns:
        str: 清洗后的文本。
    """
    if not isinstance(text, str):
        logger.warning(f"Invalid input type for preprocessing: {type(text)}")
        return ""
    
    # 简单的清洗：转小写，去除首尾空格
    cleaned = text.strip().lower()
    # 去除特殊控制字符
    cleaned = re.sub(r'[\n\r\t]', ' ', cleaned)
    return cleaned

# --- 核心类 ---

class FeedbackInterpreter:
    """
    核心功能1：反馈解释器。
    负责从非结构化文本中提取情感特征和业务特征。
    """
    
    def __init__(self):
        # 模拟一个简单的基于关键词的情感词典
        # 在生产环境中，这里会加载模型或调用LLM API
        self.positive_keywords = {'赚钱', '卖光', '人多', '排队', '生意好', '盈利', '成功'}
        self.negative_keywords = {'亏本', '没人', '生意差', '滞销', '不好', '失败', '赔钱'}
        
    def extract_sentiment(self, feedback_text: str) -> Tuple[bool, float]:
        """
        分析文本情感，判断策略是否成功。
        
        Args:
            feedback_text (str): 用户的自然语言反馈。
            
        Returns:
            Tuple[bool, float]: (是否成功, 置信度/权重)
        """
        cleaned_text = preprocess_text(feedback_text)
        if not cleaned_text:
            return False, 0.0

        pos_count = sum(1 for word in self.positive_keywords if word in cleaned_text)
        neg_count = sum(1 for word in self.negative_keywords if word in cleaned_text)
        
        total_signals = pos_count + neg_count
        
        if total_signals == 0:
            logger.warning("No clear sentiment signals found in feedback.")
            return False, 0.1  # 默认弱反馈

        # 简单的逻辑判定
        is_success = pos_count > neg_count
        # 置信度基于信号强度
        confidence = (max(pos_count, neg_count) - min(pos_count, neg_count)) / (total_signals + 1)
        
        return is_success, confidence

class CognitiveLoopMonitor:
    """
    核心功能2：认知闭环监控器。
    管理‘实践-反馈’回路，更新认知状态。
    """
    
    def __init__(self):
        self.strategy_nodes: Dict[str, StrategyNode] = {}
        self.interpreter = FeedbackInterpreter()
        
    def register_strategy(self, node_id: str, content: str) -> None:
        """注册一个新的策略节点到监控系统中。"""
        if node_id in self.strategy_nodes:
            logger.error(f"Duplicate node ID detected: {node_id}")
            return
            
        new_node = StrategyNode(node_id=node_id, content=content)
        self.strategy_nodes[node_id] = new_node
        logger.info(f"New Strategy Registered: {node_id} - '{content}'")
        
    def process_feedback(self, node_id: str, feedback: str) -> Dict:
        """
        处理反馈并闭合回路。
        
        流程:
        1. 验证节点存在。
        2. 解释反馈文本。
        3. 更新节点参数。
        
        Args:
            node_id (str): 目标策略节点ID。
            feedback (str): 现实世界的非结构化反馈。
            
        Returns:
            Dict: 包含更新状态的报告。
        """
        if node_id not in self.strategy_nodes:
            logger.error(f"Node {node_id} not found for feedback processing.")
            return {"status": "error", "message": "Node not found"}
            
        logger.info(f"Processing feedback for {node_id}: '{feedback}'")
        
        try:
            # 1. 提取特征
            is_success, confidence = self.interpreter.extract_sentiment(feedback)
            
            # 2. 映射回节点并更新
            node = self.strategy_nodes[node_id]
            node.update_metrics(is_success, weight=confidence)
            
            # 3. 检查认知自洽性 (例如：成功率极低时发出警告)
            warning = None
            if node.sample_count > 5 and node.success_rate < 0.2:
                warning = "Cognitive Dissonance Detected: Strategy consistently failing."
                logger.warning(f"{warning} Node: {node_id}")
                
            return {
                "status": "success",
                "node_id": node_id,
                "interpreted_result": "success" if is_success else "failure",
                "updated_success_rate": node.success_rate,
                "warning": warning
            }
            
        except Exception as e:
            logger.exception(f"Critical error during loop closure for {node_id}")
            return {"status": "error", "message": str(e)}

    def get_system_state(self) -> List[Dict]:
        """获取当前所有节点的认知状态快照。"""
        return [node.__dict__ for node in self.strategy_nodes.values()]

# --- 使用示例 ---

if __name__ == "__main__":
    # 示例场景：小摊贩经营策略系统
    
    # 1. 初始化监控系统
    monitor = CognitiveLoopMonitor()
    
    # 2. AI生成并注册策略 (实践)
    monitor.register_strategy("strat_001", "在地铁口卖雨伞")
    
    # 3. 模拟现实反馈 (反馈)
    # 场景A: 下雨了，生意很好
    feedback_a = "今天运气真好，虽然下雨但是卖光了，赚了不少！"
    result_a = monitor.process_feedback("strat_001", feedback_a)
    print(f"Result A: {result_a}")
    
    # 场景B: 大晴天，没人买
    feedback_b = "天气太热了，根本没人买伞，滞销了，生意不好。"
    result_b = monitor.process_feedback("strat_001", feedback_b)
    print(f"Result B: {result_b}")
    
    # 4. 查看最终认知状态
    print("\nCurrent System State:")
    print(json.dumps(monitor.get_system_state(), indent=2))