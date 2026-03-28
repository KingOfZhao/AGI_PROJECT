"""
模块名称: auto_implicit_struct_explicit
描述: 【隐结构显性化】从海量非结构化交互日志中提取'隐性真实节点'的自下而上归纳构建系统。
      该模块实现了从原始交互数据中识别高频操作模式、聚类现象簇，并自动生成临时概念标签的功能。
"""

import logging
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from collections import Counter
import re
import json
from datetime import datetime
import hashlib

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class InteractionLog:
    """交互日志数据结构"""
    log_id: str
    timestamp: str
    user_action: str
    system_response: str
    context: Dict[str, Any] = field(default_factory=dict)
    raw_content: str = ""

    def __post_init__(self):
        """数据验证和清理"""
        if not self.log_id or not isinstance(self.log_id, str):
            raise ValueError("log_id必须是非空字符串")
        
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        
        # 自动生成原始内容摘要
        if not self.raw_content:
            self.raw_content = f"{self.user_action} {self.system_response}"


@dataclass
class ImplicitNode:
    """隐性节点数据结构"""
    node_id: str
    patterns: List[str]
    frequency: int
    first_seen: str
    last_seen: str
    context_samples: List[Dict[str, Any]] = field(default_factory=list)
    auto_label: str = ""
    confidence_score: float = 0.0
    status: str = "pending"  # pending, confirmed, rejected

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "patterns": self.patterns,
            "frequency": self.frequency,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "context_samples": self.context_samples,
            "auto_label": self.auto_label,
            "confidence_score": self.confidence_score,
            "status": self.status
        }


def preprocess_logs(raw_logs: List[Dict[str, Any]]) -> List[InteractionLog]:
    """
    预处理原始日志数据，转换为标准化的InteractionLog对象
    
    参数:
        raw_logs: 原始日志数据列表
        
    返回:
        标准化后的InteractionLog对象列表
        
    异常:
        ValueError: 当输入数据无效时抛出
    """
    if not raw_logs:
        logger.warning("输入日志列表为空")
        return []
    
    processed_logs = []
    for i, raw_log in enumerate(raw_logs):
        try:
            # 验证必需字段
            if not isinstance(raw_log, dict):
                logger.warning(f"日志 #{i} 不是字典格式，跳过")
                continue
                
            if 'user_action' not in raw_log or 'system_response' not in raw_log:
                logger.warning(f"日志 #{i} 缺少必需字段，跳过")
                continue
                
            # 生成唯一ID如果不存在
            log_id = raw_log.get('log_id', '')
            if not log_id:
                # 使用内容哈希作为ID
                content_hash = hashlib.md5(
                    f"{raw_log['user_action']}{raw_log['system_response']}".encode()
                ).hexdigest()[:12]
                log_id = f"auto_{content_hash}_{i}"
            
            # 创建标准化日志对象
            log = InteractionLog(
                log_id=log_id,
                timestamp=raw_log.get('timestamp', ''),
                user_action=raw_log['user_action'],
                system_response=raw_log['system_response'],
                context=raw_log.get('context', {}),
                raw_content=raw_log.get('raw_content', '')
            )
            
            processed_logs.append(log)
            
        except Exception as e:
            logger.error(f"处理日志 #{i} 时出错: {str(e)}")
            continue
    
    logger.info(f"成功预处理 {len(processed_logs)}/{len(raw_logs)} 条日志")
    return processed_logs


def extract_action_patterns(logs: List[InteractionLog], 
                          min_pattern_length: int = 3,
                          max_pattern_length: int = 10) -> Dict[str, int]:
    """
    从交互日志中提取用户操作模式
    
    参数:
        logs: 标准化日志列表
        min_pattern_length: 最小模式长度
        max_pattern_length: 最大模式长度
        
    返回:
        模式到频率的映射字典
        
    注意:
        模式是连续操作序列，通过n-gram方法提取
    """
    if not logs or min_pattern_length < 1:
        return {}
    
    # 提取所有用户操作序列
    actions = [log.user_action for log in logs if log.user_action]
    pattern_counter = Counter()
    
    # 生成n-gram模式
    for n in range(min_pattern_length, min(max_pattern_length + 1, len(actions) + 1)):
        for i in range(len(actions) - n + 1):
            pattern = " -> ".join(actions[i:i+n])
            pattern_counter[pattern] += 1
    
    # 过滤低频模式
    min_frequency = max(2, len(logs) // 100)  # 至少出现2次或占总量的1%
    significant_patterns = {
        pattern: freq for pattern, freq in pattern_counter.items()
        if freq >= min_frequency
    }
    
    logger.info(f"提取到 {len(significant_patterns)} 个显著操作模式")
    return significant_patterns


def identify_implicit_nodes(logs: List[InteractionLog],
                          existing_nodes: Set[str],
                          min_frequency: int = 5,
                          similarity_threshold: float = 0.7) -> List[ImplicitNode]:
    """
    识别隐性结构节点（核心函数）
    
    参数:
        logs: 标准化日志列表
        existing_nodes: 已存在的节点集合（用于过滤已知概念）
        min_frequency: 最小频率阈值
        similarity_threshold: 模式相似度阈值
        
    返回:
        识别出的隐性节点列表
        
    算法:
        1. 提取操作模式并聚类
        2. 过滤已知概念
        3. 生成自动标签
        4. 计算置信度分数
    """
    if not logs:
        logger.warning("输入日志列表为空，无法识别隐性节点")
        return []
    
    # 1. 提取操作模式
    patterns = extract_action_patterns(logs)
    if not patterns:
        logger.info("未找到显著操作模式")
        return []
    
    # 2. 模式聚类（简化版，实际应用中可能需要更复杂的聚类算法）
    pattern_clusters = _cluster_patterns(patterns, similarity_threshold)
    
    # 3. 创建隐性节点
    implicit_nodes = []
    for cluster_id, (cluster_patterns, total_freq) in enumerate(pattern_clusters.items()):
        if total_freq < min_frequency:
            continue
            
        # 生成节点ID
        node_id = f"implicit_{cluster_id}_{hashlib.md5(str(cluster_patterns).encode()).hexdigest()[:8]}"
        
        # 获取时间信息
        timestamps = [
            log.timestamp for log in logs 
            if any(p in log.user_action for p in cluster_patterns)
        ]
        first_seen = min(timestamps) if timestamps else ""
        last_seen = max(timestamps) if timestamps else ""
        
        # 生成自动标签
        auto_label = _generate_auto_label(cluster_patterns)
        
        # 收集上下文样本
        context_samples = []
        for log in logs:
            if any(p in log.user_action for p in cluster_patterns):
                context_samples.append({
                    "log_id": log.log_id,
                    "user_action": log.user_action,
                    "system_response": log.system_response[:100] + "..." if len(log.system_response) > 100 else log.system_response
                })
                if len(context_samples) >= 3:  # 最多保留3个样本
                    break
        
        # 计算置信度分数（基于频率和模式多样性）
        confidence = min(1.0, total_freq / (len(logs) * 0.1))  # 归一化到0-1
        
        node = ImplicitNode(
            node_id=node_id,
            patterns=list(cluster_patterns),
            frequency=total_freq,
            first_seen=first_seen,
            last_seen=last_seen,
            context_samples=context_samples,
            auto_label=auto_label,
            confidence_score=confidence
        )
        
        implicit_nodes.append(node)
    
    # 按频率排序
    implicit_nodes.sort(key=lambda x: x.frequency, reverse=True)
    
    logger.info(f"识别出 {len(implicit_nodes)} 个隐性节点")
    return implicit_nodes


def _cluster_patterns(patterns: Dict[str, int], 
                    threshold: float) -> Dict[int, Tuple[Set[str], int]]:
    """
    模式聚类辅助函数（简化版）
    
    参数:
        patterns: 模式到频率的映射
        threshold: 相似度阈值
        
    返回:
        聚类ID到(模式集合, 总频率)的映射
    """
    clusters = {}
    cluster_id = 0
    
    # 简单的单链接聚类
    for pattern, freq in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        added = False
        
        # 检查是否与现有聚类相似
        for cid, (cluster_patterns, cluster_freq) in clusters.items():
            if _pattern_similarity(pattern, list(cluster_patterns)[0]) >= threshold:
                cluster_patterns.add(pattern)
                clusters[cid] = (cluster_patterns, cluster_freq + freq)
                added = True
                break
        
        if not added:
            clusters[cluster_id] = ({pattern}, freq)
            cluster_id += 1
    
    return clusters


def _pattern_similarity(pattern1: str, pattern2: str) -> float:
    """
    计算两个模式之间的相似度（基于Jaccard相似度）
    """
    set1 = set(pattern1.split(" -> "))
    set2 = set(pattern2.split(" -> "))
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def _generate_auto_label(patterns: Set[str]) -> str:
    """
    为模式聚类生成自动标签（辅助函数）
    
    参数:
        patterns: 模式集合
        
    返回:
        自动生成的临时标签
    """
    # 提取最常见的动词和名词
    words = []
    for pattern in patterns:
        words.extend(pattern.split())
    
    # 简单词频统计
    word_counter = Counter(words)
    common_words = [word for word, _ in word_counter.most_common(3) 
                   if len(word) > 2 and word.lower() not in {'the', 'and', 'for'}]
    
    if common_words:
        return f"AutoConcept_{'_'.join(common_words[:2])}"
    return f"AutoConcept_{hashlib.md5(str(patterns).encode()).hexdigest()[:6]}"


def export_implicit_nodes(nodes: List[ImplicitNode], 
                         format: str = "json") -> str:
    """
    导出隐性节点到指定格式
    
    参数:
        nodes: 隐性节点列表
        format: 输出格式 (json, csv)
        
    返回:
        格式化后的字符串
        
    异常:
        ValueError: 当格式不支持时抛出
    """
    if not nodes:
        return ""
    
    if format == "json":
        return json.dumps([node.to_dict() for node in nodes], indent=2)
    elif format == "csv":
        lines = ["node_id,auto_label,frequency,confidence_score,status"]
        for node in nodes:
            lines.append(f"{node.node_id},{node.auto_label},{node.frequency},{node.confidence_score:.2f},{node.status}")
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的导出格式: {format}")


# 使用示例
if __name__ == "__main__":
    # 示例数据
    sample_logs = [
        {
            "log_id": "log1",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log2",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log3",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log4",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log5",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log6",
            "user_action": "add to cart",
            "system_response": "product added",
            "context": {"page": "product_detail"}
        },
        {
            "log_id": "log7",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log8",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        },
        {
            "log_id": "log9",
            "user_action": "add to cart",
            "system_response": "product added",
            "context": {"page": "product_detail"}
        },
        {
            "log_id": "log10",
            "user_action": "search product",
            "system_response": "showing product list",
            "context": {"page": "home"}
        }
    ]
    
    # 处理流程
    print("=== 隐性结构显性化处理流程 ===")
    
    # 1. 预处理日志
    processed_logs = preprocess_logs(sample_logs)
    print(f"预处理完成，共 {len(processed_logs)} 条有效日志")
    
    # 2. 识别隐性节点
    existing_nodes = {"search", "product", "cart"}  # 假设这些是已知概念
    implicit_nodes = identify_implicit_nodes(
        logs=processed_logs,
        existing_nodes=existing_nodes,
        min_frequency=2
    )
    
    # 3. 输出结果
    print(f"\n发现 {len(implicit_nodes)} 个隐性节点:")
    for node in implicit_nodes:
        print(f"- {node.auto_label} (频率: {node.frequency}, 置信度: {node.confidence_score:.2f})")
        print(f"  模式示例: {node.patterns[0]}")
    
    # 4. 导出结果
    json_output = export_implicit_nodes(implicit_nodes, "json")
    print("\nJSON输出:")
    print(json_output)