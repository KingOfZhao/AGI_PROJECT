"""
模块名称: human_ai_symbiosis_loop.py
描述: 实现人机共生验证闭环系统，用于优化AI生成的参数调整建议（如CNC进给速度），
     并通过人类反馈自动更新知识节点的置信度。

核心功能:
1. 生成可解释的参数调整建议
2. 构建快速验证界面
3. 反馈结果自动处理
4. 知识节点置信度动态更新

作者: AGI Systems
版本: 1.0.0
"""

import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('symbiosis_loop.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """知识节点数据结构，存储参数建议及其置信度"""
    node_id: str
    parameter_type: str
    current_value: float
    suggested_value: float
    confidence: float = 0.5
    history: List[Dict[str, float]] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_confidence(self, delta: float) -> None:
        """更新置信度，范围限制在[0.0, 1.0]"""
        self.confidence = max(0.0, min(1.0, self.confidence + delta))
        self.last_updated = datetime.now().isoformat()
        self.history.append({
            "timestamp": self.last_updated,
            "confidence": self.confidence,
            "delta": delta
        })


class HumanAISymbiosisLoop:
    """
    人机共生验证闭环系统
    
    实现AI建议生成、人类验证反馈和知识节点更新的完整闭环
    
    属性:
        knowledge_base (Dict[str, KnowledgeNode]): 知识节点存储
        feedback_threshold (float): 反馈生效的阈值
        learning_rate (float): 置信度调整的学习率
    """
    
    def __init__(self, feedback_threshold: float = 0.7, learning_rate: float = 0.1):
        """
        初始化人机共生系统
        
        参数:
            feedback_threshold: 反馈可信度阈值(0-1)
            learning_rate: 置信度调整的学习率(0-1)
        """
        self.knowledge_base: Dict[str, KnowledgeNode] = {}
        self.feedback_threshold = feedback_threshold
        self.learning_rate = learning_rate
        logger.info("HumanAISymbiosisLoop initialized with threshold=%.2f, lr=%.2f",
                    feedback_threshold, learning_rate)

    def generate_parameter_suggestion(
        self,
        node_id: str,
        current_value: float,
        context: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        生成参数调整建议并创建知识节点
        
        参数:
            node_id: 唯一节点标识符
            current_value: 当前参数值
            context: 参数上下文环境(如机器负载、材料硬度等)
            
        返回:
            Tuple[float, float]: (建议值, 初始置信度)
            
        异常:
            ValueError: 如果输入参数无效
        """
        # 输入验证
        if not node_id or not isinstance(current_value, (int, float)):
            logger.error("Invalid input parameters: node_id=%s, current_value=%s",
                         node_id, current_value)
            raise ValueError("Invalid node_id or current_value")
            
        if not context:
            logger.warning("Empty context provided for node %s", node_id)
            
        # 生成建议值 (示例: 进给速度优化算法)
        try:
            # 基于上下文的简单启发式规则
            if context.get("load", 0) > 0.8:
                suggested_value = current_value * 0.9  # 高负载时减速
            elif context.get("load", 0) < 0.3:
                suggested_value = current_value * 1.1  # 低负载时加速
            else:
                suggested_value = current_value  # 保持当前值
                
            # 限制在合理范围内
            suggested_value = max(
                context.get("min_value", current_value * 0.5),
                min(suggested_value, context.get("max_value", current_value * 1.5))
            )
            
            # 计算初始置信度
            confidence = 0.5 + 0.3 * (1 - abs(current_value - suggested_value) / current_value)
            
            # 创建知识节点
            self.knowledge_base[node_id] = KnowledgeNode(
                node_id=node_id,
                parameter_type="feed_rate",
                current_value=current_value,
                suggested_value=suggested_value,
                confidence=confidence
            )
            
            logger.info("Generated suggestion for %s: %.2f (confidence %.2f)",
                        node_id, suggested_value, confidence)
            return suggested_value, confidence
            
        except Exception as e:
            logger.error("Failed to generate suggestion for %s: %s", node_id, str(e))
            raise RuntimeError(f"Suggestion generation failed: {str(e)}")

    def process_human_feedback(
        self,
        node_id: str,
        feedback: bool,
        actual_value: Optional[float] = None,
        notes: str = ""
    ) -> float:
        """
        处理人类反馈并更新知识节点
        
        参数:
            node_id: 反馈对应的节点ID
            feedback: 反馈结果(True=成功, False=失败)
            actual_value: 实际采用值(如果不同于建议值)
            notes: 反馈备注
            
        返回:
            float: 更新后的置信度
            
        异常:
            KeyError: 如果节点ID不存在
            ValueError: 如果反馈数据无效
        """
        if node_id not in self.knowledge_base:
            logger.error("Unknown node ID: %s", node_id)
            raise KeyError(f"Node {node_id} not found in knowledge base")
            
        node = self.knowledge_base[node_id]
        
        # 计算置信度调整量
        delta = self.learning_rate * (1 if feedback else -1)
        
        # 如果提供了实际值且不同于建议值，调整学习率
        if actual_value is not None and actual_value != node.suggested_value:
            adjustment = abs(node.suggested_value - actual_value) / node.current_value
            delta *= (1 - adjustment)  # 差异越大，影响越小
            
        # 更新节点置信度
        old_confidence = node.confidence
        node.update_confidence(delta)
        
        # 记录详细反馈
        feedback_record = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "actual_value": actual_value,
            "notes": notes,
            "confidence_change": node.confidence - old_confidence
        }
        node.history.append(feedback_record)
        
        logger.info("Processed feedback for %s: %s (new confidence %.2f)",
                    node_id, "SUCCESS" if feedback else "FAILURE", node.confidence)
        return node.confidence

    def _validate_input_parameters(
        self,
        params: Dict[str, float],
        required_keys: List[str]
    ) -> bool:
        """
        验证输入参数的有效性(辅助函数)
        
        参数:
            params: 参数字典
            required_keys: 必需的键列表
            
        返回:
            bool: 参数是否有效
            
        异常:
            ValueError: 如果缺少必需键或值无效
        """
        missing_keys = [k for k in required_keys if k not in params]
        if missing_keys:
            raise ValueError(f"Missing required keys: {missing_keys}")
            
        for key, value in params.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid value type for {key}: {type(value)}")
                
        return True

    def export_knowledge_base(self, file_path: str) -> None:
        """
        导出知识库到JSON文件
        
        参数:
            file_path: 输出文件路径
            
        异常:
            IOError: 如果文件写入失败
        """
        try:
            data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "node_count": len(self.knowledge_base)
                },
                "nodes": {
                    node_id: {
                        "parameter_type": node.parameter_type,
                        "current_value": node.current_value,
                        "suggested_value": node.suggested_value,
                        "confidence": node.confidence,
                        "history_count": len(node.history)
                    }
                    for node_id, node in self.knowledge_base.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("Exported knowledge base to %s", file_path)
            
        except Exception as e:
            logger.error("Failed to export knowledge base: %s", str(e))
            raise IOError(f"Knowledge base export failed: {str(e)}")


# 使用示例
if __name__ == "__main__":
    # 初始化系统
    symbiosis_system = HumanAISymbiosisLoop(feedback_threshold=0.8, learning_rate=0.15)
    
    try:
        # 示例1: 生成参数建议
        context = {
            "load": 0.85,
            "material_hardness": 45.0,
            "min_value": 100.0,
            "max_value": 500.0
        }
        suggested_value, confidence = symbiosis_system.generate_parameter_suggestion(
            "cnc_machine_01", 200.0, context
        )
        print(f"Suggested value: {suggested_value:.2f}, Confidence: {confidence:.2f}")
        
        # 示例2: 处理成功反馈
        new_confidence = symbiosis_system.process_human_feedback(
            "cnc_machine_01", True, actual_value=190.0, notes="Operator approved with slight adjustment"
        )
        print(f"Updated confidence: {new_confidence:.2f}")
        
        # 导出知识库
        symbiosis_system.export_knowledge_base("knowledge_base.json")
        
    except Exception as e:
        logger.error("Symbiosis loop error: %s", str(e))