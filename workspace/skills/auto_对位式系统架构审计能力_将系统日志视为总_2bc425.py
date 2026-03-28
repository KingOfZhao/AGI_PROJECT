"""
Module: auto_contrapuntal_architecture_audit.py
Description: 对位式系统架构审计能力。将系统日志视为总谱，AI作为指挥家，分析不同微服务或模块（声部）
             之间的互动。如果两个模块在短时间内频繁相互调用导致死锁或延迟，被视为'平行五度'（不良进行）。
             系统应具备自动识别'不协和'交互模式的能力，并提出'反向进行'的代码重构建议。
Author: AGI System
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InteractionType(Enum):
    """定义交互类型的枚举"""
    SYNC_CALL = "sync"       # 同步调用
    ASYNC_CALL = "async"     # 异步调用
    DB_QUERY = "db"          # 数据库查询
    EXTERNAL_API = "ext_api" # 外部API调用

@dataclass
class LogEntry:
    """
    单条系统日志的数据结构，代表总谱中的一个音符。
    
    Attributes:
        timestamp (float): 时间戳。
        source (str): 源模块（声部A）。
        target (str): 目标模块（声部B）。
        latency (float): 响应延迟（毫秒）。
        interaction_type (InteractionType): 交互类型。
    """
    timestamp: float
    source: str
    target: str
    latency: float
    interaction_type: InteractionType

@dataclass
class ContrapuntalIssue:
    """
    审计发现的问题，代表一段'不协和'的乐句。
    
    Attributes:
        module_pair (Tuple[str, str]): 涉及的模块对。
        issue_type (str): 问题类型（如 'Parallel_Fifths'）。
        severity (str): 严重程度。
        suggestion (str): '反向进行'的重构建议。
    """
    module_pair: Tuple[str, str]
    issue_type: str
    severity: str
    suggestion: str

@dataclass
class AuditReport:
    """
    最终的审计报告，类似乐曲的分析总结。
    """
    is_harmonious: bool = True
    issues: List[ContrapuntalIssue] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

def _validate_log_entry(entry: Dict) -> Optional[LogEntry]:
    """
    辅助函数：验证并转换原始日志字典为 LogEntry 对象。
    包含数据验证和边界检查。
    
    Args:
        entry (Dict): 原始日志数据。
        
    Returns:
        Optional[LogEntry]: 验证通过返回对象，否则返回 None。
    """
    try:
        required_keys = {"timestamp", "source", "target", "latency", "type"}
        if not required_keys.issubset(entry.keys()):
            logger.warning(f"Missing keys in log entry: {entry}")
            return None
            
        if entry['latency'] < 0:
            logger.warning(f"Negative latency detected: {entry['latency']}")
            return None
            
        # 映射字符串到枚举
        interaction_type = InteractionType(entry['type'])
        
        return LogEntry(
            timestamp=float(entry['timestamp']),
            source=str(entry['source']),
            target=str(entry['target']),
            latency=float(entry['latency']),
            interaction_type=interaction_type
        )
    except ValueError as e:
        logger.error(f"Data validation error: {e} in entry {entry}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return None

def analyze_interaction_concordance(
    logs: List[Dict], 
    time_window_seconds: float = 2.0, 
    latency_threshold_ms: float = 200.0,
    call_frequency_threshold: int = 5
) -> AuditReport:
    """
    核心函数：分析系统日志（总谱），识别不协和的交互模式（平行五度）。
    
    算法逻辑：
    1. 将日志按时间排序。
    2. 在滑动时间窗口内，统计模块对之间的调用频率和平均延迟。
    3. 如果高频且高延迟的同步调用，标记为'Parallel Fifths'。
    4. 生成重构建议。
    
    Args:
        logs (List[Dict]): 原始日志列表。
        time_window_seconds (float): 检测并发问题的时间窗口。
        latency_threshold_ms (float): 判定为高延迟的阈值。
        call_frequency_threshold (int): 判定为高频调用的阈值。
        
    Returns:
        AuditReport: 包含审计结果和重构建议的报告。
    """
    logger.info("Starting Contrapuntal System Architecture Audit...")
    
    # 数据预处理
    parsed_logs: List[LogEntry] = []
    for raw_entry in logs:
        parsed = _validate_log_entry(raw_entry)
        if parsed:
            parsed_logs.append(parsed)
            
    if not parsed_logs:
        logger.warning("No valid log entries to analyze.")
        return AuditReport(is_harmonious=True)

    # 按时间排序
    parsed_logs.sort(key=lambda x: x.timestamp)
    
    # 统计交互模式
    # Key: (source, target), Value: List of latencies within window
    interaction_windows: Dict[Tuple[str, str], List[LogEntry]] = defaultdict(list)
    issues: List[ContrapuntalIssue] = []
    
    # 滑动窗口检测 (简化版：这里使用统计聚合代替实时滑动窗口以演示逻辑)
    # 统计特定时间段内的总交互
    interaction_stats: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {"count": 0, "total_latency": 0.0, "types": set()})
    
    # 计算总时间跨度
    start_time = parsed_logs[0].timestamp
    end_time = parsed_logs[-1].timestamp
    duration = end_time - start_time if end_time > start_time else 1.0

    for entry in parsed_logs:
        key = (entry.source, entry.target)
        interaction_stats[key]["count"] += 1
        interaction_stats[key]["total_latency"] += entry.latency
        interaction_stats[key]["types"].add(entry.interaction_type)

    # 分析不协和音程
    for pair, stats in interaction_stats.items():
        avg_latency = stats["total_latency"] / stats["count"]
        calls_per_second = stats["count"] / duration
        
        # 检测 '平行五度'：高频、高延迟的同步耦合
        # 条件：调用频率高 且 平均延迟高 且 存在同步调用
        is_high_freq = calls_per_second > call_frequency_threshold / duration # 简易计算
        is_slow = avg_latency > latency_threshold_ms
        is_sync = InteractionType.SYNC_CALL in stats["types"]
        
        if is_high_freq and is_slow and is_sync:
            issue = ContrapuntalIssue(
                module_pair=pair,
                issue_type="Parallel_Fifths_Detected",
                severity="High",
                suggestion=(
                    f"Detected tight coupling between {pair[0]} and {pair[1]}. "
                    "Suggest 'Contrary Motion': Introduce Message Queue (e.g., Kafka/RabbitMQ) "
                    "or Async Processing to decouple modules and reduce latency blocking."
                )
            )
            issues.append(issue)
            logger.warning(f"Issue detected: {issue.issue_type} between {pair}")

    # 生成报告
    report = AuditReport(
        is_harmonious=len(issues) == 0,
        issues=issues,
        metrics={
            "total_logs_analyzed": len(parsed_logs),
            "unique_interactions": len(interaction_stats),
            "avg_system_latency": sum(s["total_latency"] for s in interaction_stats.values()) / len(parsed_logs)
        }
    )
    
    logger.info(f"Audit Complete. Harmonious: {report.is_harmonious}")
    return report

def suggest_refactoring(report: AuditReport) -> str:
    """
    核心函数：根据审计报告生成详细的重构策略文本（反向进行建议）。
    
    Args:
        report (AuditReport): 审计报告对象。
        
    Returns:
        str: 格式化的重构建议文本。
    """
    if report.is_harmonious:
        return "System Architecture is Harmonious. No major refactor needed."
    
    output_lines = ["=== System Architecture Refactoring Score ===\n"]
    
    for issue in report.issues:
        output_lines.append(f"Module Pair: {issue.module_pair[0]} -> {issue.module_pair[1]}")
        output_lines.append(f"  - Issue: {issue.issue_type} ({issue.severity})")
        output_lines.append(f"  - Strategy: {issue.suggestion}")
        output_lines.append("-" * 40)
        
    return "\n".join(output_lines)

# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 模拟系统日志数据
    mock_logs = [
        {"timestamp": 1000.0, "source": "UserService", "target": "Database", "latency": 50, "type": "db"},
        {"timestamp": 1000.1, "source": "OrderService", "target": "PaymentGateway", "latency": 300, "type": "sync"},
        {"timestamp": 1000.2, "source": "OrderService", "target": "PaymentGateway", "latency": 320, "type": "sync"},
        {"timestamp": 1000.3, "source": "OrderService", "target": "PaymentGateway", "latency": 310, "type": "sync"},
        {"timestamp": 1000.4, "source": "OrderService", "target": "PaymentGateway", "latency": 305, "type": "sync"},
        {"timestamp": 1000.5, "source": "OrderService", "target": "PaymentGateway", "latency": 315, "type": "sync"},
        {"timestamp": 1000.6, "source": "LogService", "target": "ElasticSearch", "latency": 10, "type": "async"},
        # 无效数据示例
        {"timestamp": 1000.7, "source": "BadModule", "target": "Nowhere", "latency": -5, "type": "sync"},
    ]

    # 1. 执行审计
    audit_report = analyze_interaction_concordance(
        logs=mock_logs,
        latency_threshold_ms=200.0
    )

    # 2. 生成建议
    refactoring_text = suggest_refactoring(audit_report)
    print(refactoring_text)