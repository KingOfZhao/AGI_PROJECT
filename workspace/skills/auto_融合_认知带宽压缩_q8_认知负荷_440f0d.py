"""
模块名称: auto_融合_认知带宽压缩_q8_认知负荷_440f0d
描述: 实现AGI系统中的认知带宽压缩与自适应接口功能。
      整合认知状态监测、信息密度动态调整及行动清单生成，
      确保输出内容与用户当前的人脑处理能力（认知负荷）完美匹配。
"""

import logging
import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveState(Enum):
    """用户认知状态枚举"""
    FATIGUED = "fatigued"       # 疲惫：需要极简信息
    CASUAL = "casual"           # 浅层浏览：需要适度摘要
    FOCUSED = "focused"         # 专注：可处理高保真细节
    UNKNOWN = "unknown"         # 未知：默认安全模式

@dataclass
class ContentPacket:
    """原始内容数据包结构"""
    raw_text: str
    technical_terms: List[str]
    key_insights: List[str]
    action_items: List[str]
    complexity_score: float  # 0.0 (简单) to 1.0 (极难)

class CognitiveLoadMonitor:
    """
    核心类：认知负荷监测器 (对应 Q2)
    模拟监测用户状态并决定输出策略
    """
    
    def __init__(self):
        self.current_state = CognitiveState.UNKNOWN
        self.interaction_history = []
        
    def detect_state(self, biometric_data: Optional[Dict] = None, 
                     interaction_speed: float = 0.5) -> CognitiveState:
        """
        根据模拟数据检测用户认知状态
        
        Args:
            biometric_data: 模拟的生物识别数据（如眨眼频率、心率变异性）
            interaction_speed: 用户交互速度 (0.0-1.0)
            
        Returns:
            CognitiveState: 当前推测的认知状态
        """
        try:
            # 边界检查
            interaction_speed = max(0.0, min(1.0, interaction_speed))
            
            # 简单的模拟逻辑：实际场景会使用传感器数据
            if interaction_speed < 0.3:
                self.current_state = CognitiveState.FATIGUED
            elif interaction_speed > 0.7:
                self.current_state = CognitiveState.FOCUSED
            else:
                self.current_state = CognitiveState.CASUAL
                
            logger.info(f"检测到认知状态变更: {self.current_state.value}")
            return self.current_state
            
        except Exception as e:
            logger.error(f"状态检测失败: {str(e)}")
            return CognitiveState.UNKNOWN

class InformationCompressor:
    """
    核心类：认知带宽压缩器 (对应 Q8)
    负责根据状态调整信息密度
    """
    
    @staticmethod
    def compress_content(content: ContentPacket, 
                         target_state: CognitiveState) -> Dict[str, Any]:
        """
        根据认知状态压缩或重构信息
        
        Args:
            content: 原始内容数据包
            target_state: 目标认知状态
            
        Returns:
            Dict: 调整后的输出格式
        """
        if not isinstance(content, ContentPacket):
            raise ValueError("无效的输入内容格式")
            
        logger.info(f"正在为状态 {target_state.value} 压缩内容...")
        
        if target_state == CognitiveState.FATIGUED:
            # 极简模式：仅保留核心行动清单
            return {
                "mode": "minimalist_checklist",
                "primary_action": content.action_items[0] if content.action_items else "休息",
                "mental_model": "使用 '3-3-3' 呼吸法恢复注意力",
                "detail_level": "5%"
            }
            
        elif target_state == CognitiveState.CASUAL:
            # 浅层模式：提供摘要和关键点
            return {
                "mode": "summary_bullets",
                "key_insights": content.key_insights[:3],  # 限制列表项
                "simplified_terms": content.technical_terms,
                "detail_level": "30%"
            }
            
        elif target_state == CognitiveState.FOCUSED:
            # 专注模式：完整细节与深度分析
            return {
                "mode": "high_fidelity_deep_dive",
                "full_content": content.raw_text,
                "technical_analysis": content.technical_terms,
                "deep_dive_actions": content.action_items,
                "complexity": content.complexity_score,
                "detail_level": "100%"
            }
            
        else:
            # 默认安全模式
            return {
                "mode": "safe_default",
                "message": "无法确定认知状态，显示标准摘要。",
                "summary": content.key_insights
            }

def generate_practical_checklist(actions: List[str], 
                                 complexity_threshold: float = 0.7) -> List[Dict]:
    """
    辅助函数：生成实践清单 (对应 Q5)
    将原始行动项转换为结构化执行步骤
    
    Args:
        actions: 原始行动项列表
        complexity_threshold: 复杂度阈值，超过则拆解任务
        
    Returns:
        List[Dict]: 结构化的清单项
    """
    if not actions:
        return []
        
    structured_list = []
    for idx, action in enumerate(actions):
        # 简单模拟：如果文本过长，视为复杂任务并添加拆解提示
        is_complex = len(action.split()) > 10
        
        item = {
            "id": f"task_{idx+1}",
            "description": action,
            "status": "pending",
            "cognitive_cost": "high" if is_complex else "low",
            "sub_steps": []
        }
        
        # 如果任务复杂，尝试拆解（这里仅作模拟）
        if is_complex:
            item["sub_steps"].append({"hint": "建议将此任务拆解为2-3个子步骤"})
            
        structured_list.append(item)
        
    return structured_list

# 使用示例
if __name__ == "__main__":
    # 1. 准备模拟数据
    raw_data = ContentPacket(
        raw_text="深度学习模型在处理非结构化数据时表现出色，但需要大量算力...",
        technical_terms=["Transformer", "Backpropagation", "GPU Utilization"],
        key_insights=["模型需要数据归一化", "批大小影响收敛速度"],
        action_items=["配置CUDA环境", "清洗数据集", "启动训练脚本", "监控损失函数"],
        complexity_score=0.85
    )

    # 2. 初始化监测器
    monitor = CognitiveLoadMonitor()
    
    # 3. 模拟场景 A：用户疲惫
    print("--- 场景 A: 用户疲惫 (交互速度慢) ---")
    state_a = monitor.detect_state(interaction_speed=0.1)
    output_a = InformationCompressor.compress_content(raw_data, state_a)
    print(json.dumps(output_a, indent=2, ensure_ascii=False))
    
    # 4. 模拟场景 B：用户专注
    print("\n--- 场景 B: 用户专注 (交互速度快) ---")
    state_b = monitor.detect_state(interaction_speed=0.9)
    output_b = InformationCompressor.compress_content(raw_data, state_b)
    print(json.dumps(output_b, indent=2, ensure_ascii=False))
    
    # 5. 生成辅助清单
    print("\n--- 生成结构化清单 ---")
    checklist = generate_practical_checklist(raw_data.action_items)
    print(json.dumps(checklist, indent=2, ensure_ascii=False))