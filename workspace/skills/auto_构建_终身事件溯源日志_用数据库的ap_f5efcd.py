"""
终身事件溯源日志系统

本模块实现了一个基于Append-Only日志模型的终身事件溯源系统，
用于重构人类的自我评价体系。核心思想是不将失败视为对能力的
'Update（覆盖/否定）'，而是视为一个'Error Event（异常事件）'
追加到日志中。

数据模型:
    输入:
        - event_type: str (事件类型，如 'SUCCESS', 'ERROR', 'MILESTONE')
        - description: str (事件描述)
        - metadata: dict (可选的元数据)
        - timestamp: datetime (可选，默认当前时间)
    
    输出:
        - Event对象: 包含所有事件信息的不可变对象
        - 状态快照: dict (包含能力评估、成长轨迹等分析结果)

使用示例:
    >>> logger = LifelongEventLogger("my_life_log.json")
    >>> logger.append_event("SUCCESS", "完成Python项目", {"skill": "coding"})
    >>> logger.append_event("ERROR", "面试失败", {"reason": "紧张"})
    >>> snapshot = logger.analyze_current_state()
    >>> print(snapshot['growth_mindset_score'])
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    MILESTONE = "MILESTONE"
    LEARNING = "LEARNING"
    REFLECTION = "REFLECTION"


@dataclass(frozen=True)
class Event:
    """
    不可变事件对象
    
    属性:
        event_id: str - 事件唯一标识符
        event_type: EventType - 事件类型
        description: str - 事件描述
        timestamp: datetime - 事件发生时间
        metadata: dict - 附加元数据
    """
    event_id: str
    event_type: EventType
    description: str
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """将事件转换为字典格式"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """从字典创建事件对象"""
        return cls(
            event_id=data['event_id'],
            event_type=EventType(data['event_type']),
            description=data['description'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class LifelongEventLogger:
    """
    终身事件溯源日志系统
    
    核心理念:
        1. 事件不可变 - 所有事件一旦创建就不可修改或删除
        2. 失败即数据 - 错误事件是宝贵的学习数据，不是能力否定
        3. 状态快照 - 通过重放所有事件计算当前状态
        4. 成长型思维 - 强调过程和可修复性
    """
    
    def __init__(self, storage_path: str = "lifelong_events.json"):
        """
        初始化日志系统
        
        参数:
            storage_path: str - 日志存储路径
        """
        self.storage_path = Path(storage_path)
        self._events: List[Event] = []
        self._load_events()
        logger.info(f"初始化终身事件日志系统，当前事件数: {len(self._events)}")
    
    def _load_events(self) -> None:
        """从存储加载事件"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._events = [Event.from_dict(e) for e in data]
                logger.info(f"成功加载 {len(self._events)} 个历史事件")
        except Exception as e:
            logger.error(f"加载事件失败: {e}")
            self._events = []
    
    def _save_events(self) -> None:
        """保存事件到存储"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([e.to_dict() for e in self._events], f, 
                         ensure_ascii=False, indent=2)
            logger.info(f"成功保存 {len(self._events)} 个事件")
        except Exception as e:
            logger.error(f"保存事件失败: {e}")
            raise
    
    @staticmethod
    def _generate_event_id(event_type: EventType, timestamp: datetime, 
                          description: str) -> str:
        """
        生成唯一事件ID
        
        参数:
            event_type: 事件类型
            timestamp: 时间戳
            description: 事件描述
            
        返回:
            str: 基于内容哈希的唯一ID
        """
        content = f"{event_type.value}_{timestamp.isoformat()}_{description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def append_event(self, event_type: Union[str, EventType], 
                    description: str, 
                    metadata: Optional[Dict[str, Any]] = None,
                    timestamp: Optional[datetime] = None) -> Event:
        """
        追加新事件到日志
        
        参数:
            event_type: 事件类型（字符串或EventType枚举）
            description: 事件描述
            metadata: 可选的元数据字典
            timestamp: 可选的时间戳（默认当前时间）
            
        返回:
            Event: 新创建的事件对象
            
        异常:
            ValueError: 当参数验证失败时
        """
        # 数据验证
        if not description or not description.strip():
            raise ValueError("事件描述不能为空")
        
        if len(description) > 1000:
            raise ValueError("事件描述过长（最大1000字符）")
        
        # 类型转换
        if isinstance(event_type, str):
            try:
                event_type = EventType(event_type.upper())
            except ValueError:
                raise ValueError(f"无效的事件类型: {event_type}")
        
        # 设置默认值
        if timestamp is None:
            timestamp = datetime.now()
        
        if metadata is None:
            metadata = {}
        
        # 生成事件ID
        event_id = self._generate_event_id(event_type, timestamp, description)
        
        # 检查重复事件
        if any(e.event_id == event_id for e in self._events):
            logger.warning(f"检测到重复事件ID: {event_id}")
            raise ValueError("重复的事件")
        
        # 创建并追加事件
        event = Event(
            event_id=event_id,
            event_type=event_type,
            description=description.strip(),
            timestamp=timestamp,
            metadata=metadata
        )
        
        self._events.append(event)
        self._save_events()
        
        logger.info(f"成功追加事件: [{event_type.value}] {description[:50]}...")
        return event
    
    def analyze_current_state(self) -> Dict[str, Any]:
        """
        分析由所有历史事件累积而成的当前状态快照
        
        返回:
            dict: 包含以下字段的状态快照
                - total_events: 总事件数
                - event_distribution: 各类型事件分布
                - growth_mindset_score: 成长型思维评分(0-100)
                - learning_velocity: 学习速度指标
                - resilience_index: 韧性指数
                - capability_snapshot: 能力快照
                - recent_trends: 最近趋势分析
                - recommendations: AI建议
        """
        if not self._events:
            return {
                'total_events': 0,
                'message': '暂无事件数据，开始记录你的成长旅程吧！'
            }
        
        # 事件分布统计
        event_distribution = {}
        for event in self._events:
            et = event.event_type.value
            event_distribution[et] = event_distribution.get(et, 0) + 1
        
        # 计算成长型思维评分
        success_count = event_distribution.get('SUCCESS', 0)
        error_count = event_distribution.get('ERROR', 0)
        learning_count = event_distribution.get('LEARNING', 0)
        reflection_count = event_distribution.get('REFLECTION', 0)
        
        total = len(self._events)
        
        # 成长型思维评分算法
        # 关键指标：从错误中学习、持续反思、不畏惧失败
        resilience_score = min(100, (reflection_count * 15 + learning_count * 10) / max(1, error_count) * 10)
        growth_score = min(100, 
            (success_count * 5 + learning_count * 8 + reflection_count * 10 + 
             error_count * 3)  # 错误也贡献分数，因为它是数据
        )
        growth_mindset_score = int((resilience_score + growth_score) / 2)
        
        # 学习速度指标（事件频率）
        if len(self._events) >= 2:
            first_event = min(self._events, key=lambda e: e.timestamp)
            last_event = max(self._events, key=lambda e: e.timestamp)
            days_span = (last_event.timestamp - first_event.timestamp).days or 1
            learning_velocity = round(total / days_span, 2)
        else:
            learning_velocity = 0
        
        # 能力快照（从元数据中提取技能标签）
        capability_snapshot = {}
        for event in self._events:
            if 'skill' in event.metadata:
                skill = event.metadata['skill']
                capability_snapshot[skill] = capability_snapshot.get(skill, 0) + 1
        
        # 最近趋势（最近10个事件）
        recent_events = sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:10]
        recent_trends = {
            'recent_success_rate': sum(1 for e in recent_events if e.event_type == EventType.SUCCESS) / len(recent_events) * 100,
            'recent_learning_focus': [e.description for e in recent_events if e.event_type == EventType.LEARNING][:3]
        }
        
        # AI建议生成
        recommendations = self._generate_recommendations(
            event_distribution, growth_mindset_score, resilience_score
        )
        
        return {
            'total_events': total,
            'event_distribution': event_distribution,
            'growth_mindset_score': growth_mindset_score,
            'learning_velocity': learning_velocity,
            'resilience_index': int(resilience_score),
            'capability_snapshot': capability_snapshot,
            'recent_trends': recent_trends,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, event_dist: Dict[str, int], 
                                 growth_score: float, 
                                 resilience_score: float) -> List[str]:
        """
        根据事件分布生成个性化建议
        
        参数:
            event_dist: 事件分布字典
            growth_score: 成长型思维评分
            resilience_score: 韧性指数
            
        返回:
            List[str]: 建议列表
        """
        recommendations = []
        
        error_count = event_dist.get('ERROR', 0)
        reflection_count = event_dist.get('REFLECTION', 0)
        learning_count = event_dist.get('LEARNING', 0)
        
        # 基于规则的智能建议
        if error_count > 0 and reflection_count < error_count:
            recommendations.append(
                "💡 建议：你记录了多次错误事件，但反思记录较少。"
                "尝试对每个错误进行深度反思，这会显著提升你的成长速度。"
            )
        
        if resilience_score < 50:
            recommendations.append(
                "🌱 提示：你的韧性指数有提升空间。记住，失败不是能力的否定，"
                "而是成长的数据点。尝试将'ERROR'事件重新定义为'LEARNING'机会。"
            )
        
        if learning_count < 3:
            recommendations.append(
                "📚 观察：主动学习事件较少。建议记录更多学习过程，"
                "包括阅读、课程、实践等，这有助于构建完整的能力图谱。"
            )
        
        if growth_score > 80:
            recommendations.append(
                "🎉 太棒了！你展现了很强的成长型思维。继续保持记录习惯，"
                "并考虑分享你的经验帮助他人成长。"
            )
        
        if not recommendations:
            recommendations.append(
                "✨ 继续记录你的成长旅程！每一个事件都是宝贵的经验积累。"
            )
        
        return recommendations
    
    def get_event_history(self, limit: int = 50, 
                         event_type: Optional[EventType] = None) -> List[Dict[str, Any]]:
        """
        获取事件历史记录
        
        参数:
            limit: 返回的最大事件数
            event_type: 可选的事件类型过滤
            
        返回:
            List[Dict]: 事件列表（按时间倒序）
        """
        if event_type:
            filtered = [e for e in self._events if e.event_type == event_type]
        else:
            filtered = self._events
        
        sorted_events = sorted(filtered, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in sorted_events[:limit]]
    
    def export_analysis_report(self, output_path: str) -> None:
        """
        导出完整的分析报告
        
        参数:
            output_path: 输出文件路径
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'state_snapshot': self.analyze_current_state(),
            'event_history': self.get_event_history(limit=1000)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析报告已导出到: {output_path}")


# 使用示例
if __name__ == "__main__":
    # 创建日志系统实例
    logger_system = LifelongEventLogger("my_lifelong_log.json")
    
    # 追加各种类型的事件
    print("=== 终身事件溯源日志系统演示 ===\n")
    
    # 成功事件
    logger_system.append_event(
        "SUCCESS", 
        "完成Python自动化项目开发",
        {"skill": "Python", "project": "automation"}
    )
    
    # 错误事件（重要：不是否定能力，而是数据点）
    logger_system.append_event(
        "ERROR",
        "技术面试未能通过，算法部分表现不佳",
        {"skill": "Algorithm", "reason": "准备不足"}
    )
    
    # 学习事件
    logger_system.append_event(
        "LEARNING",
        "开始系统学习数据结构与算法",
        {"resource": "LeetCode", "daily_goal": "2题"}
    )
    
    # 反思事件
    logger_system.append_event(
        "REFLECTION",
        "面试失败后意识到基础的重要性，决定系统复习",
        {"insight": "基础不牢，地动山摇"}
    )
    
    # 里程碑事件
    logger_system.append_event(
        "MILESTONE",
        "完成100道算法题",
        {"platform": "LeetCode", "count": 100}
    )
    
    # 分析当前状态
    print("\n=== 当前状态快照分析 ===\n")
    snapshot = logger_system.analyze_current_state()
    
    print(f"总事件数: {snapshot['total_events']}")
    print(f"事件分布: {snapshot['event_distribution']}")
    print(f"成长型思维评分: {snapshot['growth_mindset_score']}/100")
    print(f"韧性指数: {snapshot['resilience_index']}/100")
    print(f"学习速度: {snapshot['learning_velocity']} 事件/天")
    print(f"\n能力快照: {snapshot['capability_snapshot']}")
    
    print("\n=== AI 建议 ===")
    for rec in snapshot['recommendations']:
        print(rec)
    
    # 导出报告
    logger_system.export_analysis_report("my_growth_report.json")
    print("\n报告已导出到 my_growth_report.json")