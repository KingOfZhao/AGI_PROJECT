"""
认知债务账本模块

本模块实现了一个用于AGI系统的认知债务管理系统。它跟踪记录所有被挂起的验证流程，
并提供了定期清算机制来处理这些债务。认知债务代表系统中未完成的验证任务，
需要定期检查和清理以确保系统的一致性和可靠性。

核心功能:
- 记录和跟踪认知债务（挂起的验证流程）
- 设计和执行定期清算机制
- 提供债务状态查询和统计功能
- 支持债务优先级和过期处理

数据格式:
输入:
- debt_record: Dict包含以下字段:
    - id: str, 唯一标识符
    - validation_type: str, 验证类型
    - data_reference: str, 数据引用路径
    - created_at: datetime, 创建时间
    - priority: int (1-10), 优先级
    - metadata: Dict, 附加元数据

输出:
- ledger_summary: Dict包含:
    - total_debts: int, 总债务数
    - pending_count: int, 待处理数
    - cleared_count: int, 已清算数
    - expired_count: int, 已过期数
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DebtStatus(Enum):
    """认知债务状态枚举"""
    PENDING = "pending"       # 待处理
    PROCESSING = "processing" # 处理中
    CLEARED = "cleared"       # 已清算
    EXPIRED = "expired"       # 已过期
    FAILED = "failed"         # 处理失败


class ValidationType(Enum):
    """验证类型枚举"""
    DATA_INTEGRITY = "data_integrity"   # 数据完整性
    LOGICAL_CONSISTENCY = "logical_consistency"  # 逻辑一致性
    FACTUAL_ACCURACY = "factual_accuracy"  # 事实准确性
    CAUSAL_REASONING = "causal_reasoning"  # 因果推理
    GOAL_ALIGNMENT = "goal_alignment"  # 目标对齐


@dataclass
class CognitiveDebt:
    """认知债务数据类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    validation_type: str = ""
    data_reference: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 默认中等优先级 (1-10)
    status: DebtStatus = DebtStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_processed: Optional[datetime] = None
    process_count: int = 0
    expiry_duration: timedelta = field(default_factory=lambda: timedelta(hours=24))
    
    def is_expired(self) -> bool:
        """检查债务是否已过期"""
        return datetime.now() - self.created_at > self.expiry_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['status'] = self.status.value
        data['expiry_duration'] = str(self.expiry_duration)
        if self.last_processed:
            data['last_processed'] = self.last_processed.isoformat()
        return data


class CognitiveDebtLedger:
    """
    认知债务账本类
    
    管理所有被挂起的验证流程，提供记录、查询、清算等功能。
    支持优先级排序、自动过期检测和定期清算机制。
    
    使用示例:
    >>> ledger = CognitiveDebtLedger()
    >>> debt_id = ledger.record_debt(
    ...     validation_type="data_integrity",
    ...     data_reference="/knowledge/graph/entity/123",
    ...     priority=7
    ... )
    >>> summary = ledger.get_ledger_summary()
    >>> ledger.perform_clearance()
    """
    
    def __init__(self, max_debts: int = 1000, auto_clear_interval: int = 3600):
        """
        初始化认知债务账本
        
        Args:
            max_debts: 最大债务记录数，默认1000
            auto_clear_interval: 自动清算间隔（秒），默认3600秒（1小时）
        """
        self._debts: Dict[str, CognitiveDebt] = {}
        self._max_debts = max_debts
        self._auto_clear_interval = auto_clear_interval
        self._last_clearance: datetime = datetime.now()
        self._clearance_count: int = 0
        logger.info(f"认知债务账本已初始化，最大容量: {max_debts}, 自动清算间隔: {auto_clear_interval}秒")
    
    def record_debt(
        self,
        validation_type: str,
        data_reference: str,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
        expiry_hours: int = 24
    ) -> str:
        """
        记录新的认知债务
        
        Args:
            validation_type: 验证类型，必须是ValidationType枚举值之一
            data_reference: 数据引用路径
            priority: 优先级 (1-10)，数字越大优先级越高
            metadata: 附加元数据
            expiry_hours: 过期时间（小时）
        
        Returns:
            str: 债务ID
        
        Raises:
            ValueError: 当参数无效时抛出
            RuntimeError: 当账本已满时抛出
        
        Example:
        >>> ledger = CognitiveDebtLedger()
        >>> debt_id = ledger.record_debt(
        ...     validation_type="logical_consistency",
        ...     data_reference="/inference/chain/456",
        ...     priority=8,
        ...     metadata={"source": "reasoning_engine"}
        ... )
        """
        # 参数验证
        if not validation_type:
            raise ValueError("验证类型不能为空")
        
        try:
            ValidationType(validation_type)
        except ValueError:
            valid_types = [vt.value for vt in ValidationType]
            raise ValueError(f"无效的验证类型: {validation_type}。有效类型: {valid_types}")
        
        if not data_reference:
            raise ValueError("数据引用不能为空")
        
        if not 1 <= priority <= 10:
            raise ValueError(f"优先级必须在1-10之间，当前值: {priority}")
        
        if len(self._debts) >= self._max_debts:
            raise RuntimeError(f"认知债务账本已满，最大容量: {self._max_debts}")
        
        # 创建债务记录
        debt = CognitiveDebt(
            validation_type=validation_type,
            data_reference=data_reference,
            priority=priority,
            metadata=metadata or {},
            expiry_duration=timedelta(hours=expiry_hours)
        )
        
        self._debts[debt.id] = debt
        logger.info(f"记录新认知债务: ID={debt.id}, 类型={validation_type}, 优先级={priority}")
        
        return debt.id
    
    def get_debt(self, debt_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定债务的详细信息
        
        Args:
            debt_id: 债务ID
        
        Returns:
            Optional[Dict]: 债务信息字典，如不存在返回None
        """
        if debt_id not in self._debts:
            logger.warning(f"未找到债务记录: {debt_id}")
            return None
        return self._debts[debt_id].to_dict()
    
    def get_pending_debts(
        self,
        limit: int = 100,
        min_priority: int = 1,
        validation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取待处理的债务列表
        
        Args:
            limit: 返回的最大记录数
            min_priority: 最小优先级过滤
            validation_type: 按验证类型过滤（可选）
        
        Returns:
            List[Dict]: 待处理债务列表，按优先级降序排列
        """
        if limit < 1:
            raise ValueError("limit必须大于0")
        
        pending = []
        for debt in self._debts.values():
            if debt.status != DebtStatus.PENDING:
                continue
            if debt.priority < min_priority:
                continue
            if validation_type and debt.validation_type != validation_type:
                continue
            pending.append(debt)
        
        # 按优先级降序排序
        pending.sort(key=lambda x: x.priority, reverse=True)
        
        return [d.to_dict() for d in pending[:limit]]
    
    def perform_clearance(
        self,
        max_items: int = 50,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        执行认知债务清算
        
        处理待处理的债务和过期债务。清算包括：
        1. 标记过期债务
        2. 尝试处理高优先级待处理债务
        3. 更新清算统计信息
        
        Args:
            max_items: 单次清算处理的最大项目数
            force: 是否强制清算（忽略时间间隔限制）
        
        Returns:
            Dict: 清算结果摘要
        
        Example:
        >>> result = ledger.perform_clearance(max_items=100)
        >>> print(f"清算完成: {result['processed']}项已处理")
        """
        current_time = datetime.now()
        
        # 检查是否到达清算时间
        if not force:
            time_since_last = (current_time - self._last_clearance).total_seconds()
            if time_since_last < self._auto_clear_interval:
                logger.debug(f"未到清算时间，距下次清算: {self._auto_clear_interval - time_since_last:.0f}秒")
                return {
                    "status": "skipped",
                    "reason": "interval_not_reached",
                    "next_clearance_in": self._auto_clear_interval - time_since_last
                }
        
        logger.info(f"开始认知债务清算，最大处理数: {max_items}")
        
        clearance_result = {
            "status": "completed",
            "start_time": current_time.isoformat(),
            "processed": 0,
            "cleared": 0,
            "expired": 0,
            "failed": 0,
            "details": []
        }
        
        processed_count = 0
        
        # 第一步：处理过期债务
        for debt_id, debt in list(self._debts.items()):
            if processed_count >= max_items:
                break
            
            if debt.status == DebtStatus.PENDING and debt.is_expired():
                debt.status = DebtStatus.EXPIRED
                debt.last_processed = current_time
                clearance_result["expired"] += 1
                clearance_result["details"].append({
                    "id": debt_id,
                    "action": "expired",
                    "validation_type": debt.validation_type
                })
                logger.info(f"债务已过期: ID={debt_id}, 类型={debt.validation_type}")
                processed_count += 1
        
        # 第二步：处理高优先级待处理债务
        pending_debts = [
            d for d in self._debts.values()
            if d.status == DebtStatus.PENDING
        ]
        pending_debts.sort(key=lambda x: x.priority, reverse=True)
        
        for debt in pending_debts:
            if processed_count >= max_items:
                break
            
            # 模拟验证处理（实际应用中这里会调用验证器）
            success = self._process_single_debt(debt)
            
            debt.last_processed = current_time
            debt.process_count += 1
            
            if success:
                debt.status = DebtStatus.CLEARED
                clearance_result["cleared"] += 1
                action = "cleared"
            else:
                debt.status = DebtStatus.FAILED
                clearance_result["failed"] += 1
                action = "failed"
            
            clearance_result["details"].append({
                "id": debt.id,
                "action": action,
                "validation_type": debt.validation_type,
                "process_count": debt.process_count
            })
            
            processed_count += 1
            clearance_result["processed"] += 1
        
        # 更新清算状态
        self._last_clearance = current_time
        self._clearance_count += 1
        clearance_result["clearance_number"] = self._clearance_count
        
        logger.info(
            f"清算完成: 处理={clearance_result['processed']}, "
            f"清算={clearance_result['cleared']}, "
            f"过期={clearance_result['expired']}, "
            f"失败={clearance_result['failed']}"
        )
        
        return clearance_result
    
    def _process_single_debt(self, debt: CognitiveDebt) -> bool:
        """
        处理单个认知债务（内部辅助方法）
        
        这是实际验证处理的占位符。在实际AGI系统中，
        这里会调用相应的验证器来执行具体的验证逻辑。
        
        Args:
            debt: 要处理的债务对象
        
        Returns:
            bool: 处理是否成功
        """
        logger.debug(f"处理债务: ID={debt.id}, 类型={debt.validation_type}")
        
        # 模拟验证逻辑 - 实际应用中替换为真实验证代码
        # 这里我们模拟80%的成功率
        import random
        success = random.random() < 0.8
        
        if success:
            logger.debug(f"债务验证通过: ID={debt.id}")
        else:
            logger.warning(f"债务验证失败: ID={debt.id}")
        
        return success
    
    def get_ledger_summary(self) -> Dict[str, Any]:
        """
        获取账本摘要统计
        
        Returns:
            Dict: 包含各种统计信息的字典
        
        Example:
        >>> summary = ledger.get_ledger_summary()
        >>> print(f"总债务: {summary['total_debts']}, 待处理: {summary['pending_count']}")
        """
        status_counts = {status.value: 0 for status in DebtStatus}
        priority_sum = 0
        type_counts: Dict[str, int] = {}
        oldest_pending: Optional[datetime] = None
        
        for debt in self._debts.values():
            status_counts[debt.status.value] += 1
            priority_sum += debt.priority
            
            if debt.validation_type not in type_counts:
                type_counts[debt.validation_type] = 0
            type_counts[debt.validation_type] += 1
            
            if debt.status == DebtStatus.PENDING:
                if oldest_pending is None or debt.created_at < oldest_pending:
                    oldest_pending = debt.created_at
        
        avg_priority = priority_sum / len(self._debts) if self._debts else 0
        
        return {
            "total_debts": len(self._debts),
            "pending_count": status_counts[DebtStatus.PENDING.value],
            "cleared_count": status_counts[DebtStatus.CLEARED.value],
            "expired_count": status_counts[DebtStatus.EXPIRED.value],
            "failed_count": status_counts[DebtStatus.FAILED.value],
            "processing_count": status_counts[DebtStatus.PROCESSING.value],
            "average_priority": round(avg_priority, 2),
            "type_distribution": type_counts,
            "oldest_pending_age_hours": (
                (datetime.now() - oldest_pending).total_seconds() / 3600
                if oldest_pending else 0
            ),
            "last_clearance": self._last_clearance.isoformat(),
            "total_clearances": self._clearance_count,
            "capacity_used_percent": round(len(self._debts) / self._max_debts * 100, 2)
        }
    
    def remove_debt(self, debt_id: str) -> bool:
        """
        从账本中移除债务
        
        Args:
            debt_id: 债务ID
        
        Returns:
            bool: 是否成功移除
        """
        if debt_id in self._debts:
            del self._debts[debt_id]
            logger.info(f"已移除债务: {debt_id}")
            return True
        logger.warning(f"移除失败，债务不存在: {debt_id}")
        return False
    
    def export_ledger(self, file_path: str) -> bool:
        """
        导出账本数据到JSON文件
        
        Args:
            file_path: 导出文件路径
        
        Returns:
            bool: 是否成功导出
        """
        try:
            export_data = {
                "export_time": datetime.now().isoformat(),
                "summary": self.get_ledger_summary(),
                "debts": [debt.to_dict() for debt in self._debts.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"账本已导出到: {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出账本失败: {str(e)}")
            return False


# 模块级辅助函数
def validate_debt_priority(priority: int) -> bool:
    """
    验证债务优先级是否有效
    
    Args:
        priority: 优先级值
    
    Returns:
        bool: 是否有效
    
    Example:
    >>> validate_debt_priority(5)
    True
    >>> validate_debt_priority(11)
    False
    """
    return 1 <= priority <= 10


def calculate_debt_urgency(debt: CognitiveDebt) -> float:
    """
    计算债务的紧急程度分数
    
    综合考虑优先级和已存在时间，计算出一个紧急程度分数。
    分数越高表示越紧急。
    
    Args:
        debt: 认知债务对象
    
    Returns:
        float: 紧急程度分数 (0-100)
    
    Example:
    >>> debt = CognitiveDebt(priority=8)
    >>> urgency = calculate_debt_urgency(debt)
    >>> print(f"紧急程度: {urgency}")
    """
    # 优先级权重: 60%
    priority_score = (debt.priority / 10) * 60
    
    # 时间紧迫性权重: 40%
    age_hours = (datetime.now() - debt.created_at).total_seconds() / 3600
    expiry_hours = debt.expiry_duration.total_seconds() / 3600
    time_score = min((age_hours / expiry_hours) * 40, 40)
    
    return round(priority_score + time_score, 2)


# 主程序示例
if __name__ == "__main__":
    # 创建认知债务账本实例
    ledger = CognitiveDebtLedger(max_debts=100, auto_clear_interval=60)
    
    # 记录一些认知债务
    print("=" * 60)
    print("认知债务账本演示")
    print("=" * 60)
    
    debt_ids = []
    
    # 记录不同类型的债务
    debt_ids.append(ledger.record_debt(
        validation_type="data_integrity",
        data_reference="/knowledge/entities/concept_456",
        priority=8,
        metadata={"source": "data_processor", "confidence": 0.75}
    ))
    
    debt_ids.append(ledger.record_debt(
        validation_type="logical_consistency",
        data_reference="/inference/results/chain_789",
        priority=9,
        metadata={"reasoning_path": "deductive"}
    ))
    
    debt_ids.append(ledger.record_debt(
        validation_type="factual_accuracy",
        data_reference="/knowledge/facts/assertion_123",
        priority=6,
        expiry_hours=12
    ))
    
    # 获取账本摘要
    print("\n账本摘要:")
    summary = ledger.get_ledger_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 获取待处理债务
    print("\n待处理债务列表:")
    pending = ledger.get_pending_debts(limit=5)
    for debt in pending:
        urgency = calculate_debt_urgency(CognitiveDebt(
            id=debt['id'],
            priority=debt['priority'],
            created_at=datetime.fromisoformat(debt['created_at']),
            expiry_duration=timedelta(
                hours=float(debt['expiry_duration'].replace('timedelta(seconds=', '').replace(')', ''))
            )
        ))
        print(f"  ID: {debt['id'][:8]}... | 类型: {debt['validation_type']} | "
              f"优先级: {debt['priority']} | 紧急度: {urgency}")
    
    # 执行清算
    print("\n执行清算...")
    result = ledger.perform_clearance(max_items=10, force=True)
    print(f"清算结果: {result['status']}")
    print(f"  处理: {result['processed']}")
    print(f"  清算: {result['cleared']}")
    print(f"  过期: {result['expired']}")
    print(f"  失败: {result['failed']}")
    
    # 最终摘要
    print("\n最终账本状态:")
    final_summary = ledger.get_ledger_summary()
    print(f"  总债务: {final_summary['total_debts']}")
    print(f"  待处理: {final_summary['pending_count']}")
    print(f"  已清算: {final_summary['cleared_count']}")
    print(f"  已过期: {final_summary['expired_count']}")
    
    print("\n" + "=" * 60)
    print("演示完成")