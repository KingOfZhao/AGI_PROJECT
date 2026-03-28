"""
模块名称: industrial_practice_checklist_generator
功能描述: 将复杂的工业标准（如ISO 9001）转化为针对特定车间、工位的每日行动清单。
         支持根据环境因子（季节、设备状态）动态调整检查项，实现持续优化的'持续碰撞'机制。
作者: AGI System
版本: 1.0.0
"""

import logging
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Any, TypedDict, Literal
from enum import Enum
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class Season(Enum):
    """季节枚举，用于环境上下文"""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

class DeviceStatus(Enum):
    """设备状态枚举"""
    NEW = "new"
    NORMAL = "normal"
    AGING = "aging"
    CRITICAL = "critical"

@dataclass
class EnvironmentalContext:
    """环境上下文，影响清单生成的动态因子"""
    current_date: date
    temperature: float  # 摄氏度
    humidity: float     # 百分比 (0.0 - 1.0)
    device_status: DeviceStatus
    season: Season

    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.humidity <= 1.0):
            raise ValueError(f"湿度必须在0.0到1.0之间，当前值: {self.humidity}")

@dataclass
class StandardClause:
    """工业标准条款的数据结构"""
    clause_id: str
    description: str
    category: str  # 例如: 'safety', 'quality', 'maintenance'
    base_frequency: str  # 'daily', 'weekly', 'monthly'
    conditions: Dict[str, Any] = field(default_factory=dict)
    # 定义触发特殊检查的条件，例如 {'device_status': 'AGING', 'season': 'WINTER'}

@dataclass
class ChecklistItem:
    """最终生成的清单项"""
    item_id: str
    content: str
    priority: int  # 1-10, 10为最高
    reason: str    # 解释为何生成此项（溯源到标准+环境因子）

# --- 辅助函数 ---

def _determine_season(input_date: date) -> Season:
    """
    根据日期确定季节（简化版，基于北半球一般划分）。
    
    Args:
        input_date (date): 输入日期
        
    Returns:
        Season: 季节枚举值
    """
    month = input_date.month
    if 3 <= month <= 5:
        return Season.SPRING
    elif 6 <= month <= 8:
        return Season.SUMMER
    elif 9 <= month <= 11:
        return Season.AUTUMN
    else:
        return Season.WINTER

def _calculate_dynamic_priority(base_priority: int, context: EnvironmentalContext) -> int:
    """
    根据环境上下文动态调整优先级。
    
    Args:
        base_priority (int): 基础优先级
        context (EnvironmentalContext): 当前环境上下文
        
    Returns:
        int: 调整后的优先级 (1-10)
    """
    modified_priority = base_priority
    
    # 规则：如果设备老化且处于极端天气，优先级提升
    if context.device_status == DeviceStatus.AGING:
        modified_priority += 2
    
    if context.season == Season.WINTER and context.temperature < 0:
        modified_priority += 1
    
    # 边界检查
    return max(1, min(10, modified_priority))

# --- 核心逻辑类 ---

class ChecklistGenerator:
    """
    实践清单生成器核心类。
    负责加载标准、匹配环境、生成清单。
    """
    
    def __init__(self, standard_repository: List[StandardClause]):
        """
        初始化生成器。
        
        Args:
            standard_repository (List[StandardClause]): 预加载的工业标准库
        """
        self.standard_repository = standard_repository
        logger.info(f"ChecklistGenerator initialized with {len(standard_repository)} clauses.")

    def _is_clause_applicable(self, clause: StandardClause, context: EnvironmentalContext) -> bool:
        """
        判断条款是否适用于当前环境（'持续碰撞'的核心逻辑）。
        
        Args:
            clause (StandardClause): 标准条款
            context (EnvironmentalContext): 环境上下文
            
        Returns:
            bool: 是否适用
        """
        # 如果条款没有特殊条件，默认适用
        if not clause.conditions:
            return True
            
        match = True
        
        # 检查设备状态条件
        if "device_status" in clause.conditions:
            required_status = clause.conditions["device_status"]
            # 简单匹配逻辑：如果是CRITICAL条款，只对AGING或CRITICAL设备显示
            if required_status == "CRITICAL" and context.device_status not in [DeviceStatus.AGING, DeviceStatus.CRITICAL]:
                match = False
        
        # 检查季节条件
        if "season" in clause.conditions:
            if context.season.value != clause.conditions["season"]:
                match = False
                
        return match

    def generate_daily_checklist(
        self, 
        station_id: str, 
        context: EnvironmentalContext,
        limit: int = 10
    ) -> List[ChecklistItem]:
        """
        生成针对特定工位的每日清单。
        
        Args:
            station_id (str): 工位ID
            context (EnvironmentalContext): 当前环境数据
            limit (int): 返回清单的最大数量
            
        Returns:
            List[ChecklistItem]: 生成的清单列表
            
        Raises:
            ValueError: 如果输入数据无效
        """
        if not station_id:
            logger.error("Station ID cannot be empty")
            raise ValueError("Station ID must be provided")

        logger.info(f"Generating checklist for Station: {station_id} | Context: {context}")
        
        generated_items: List[ChecklistItem] = []
        
        try:
            for clause in self.standard_repository:
                # 1. 基础过滤：只处理每日任务
                if clause.base_frequency != 'daily':
                    continue
                
                # 2. 环境碰撞检测
                if self._is_clause_applicable(clause, context):
                    # 3. 动态调整内容
                    adjusted_content = self._adjust_content_based_on_context(clause.description, context)
                    
                    # 4. 计算优先级
                    base_prio = 5 # 默认基础优先级
                    final_prio = _calculate_dynamic_priority(base_prio, context)
                    
                    item = ChecklistItem(
                        item_id=f"{station_id}-{clause.clause_id}-{context.current_date.isoformat()}",
                        content=adjusted_content,
                        priority=final_prio,
                        reason=f"Standard: {clause.clause_id} | Triggered by: {context.device_status.value} status"
                    )
                    generated_items.append(item)
            
            # 5. 排序并截取
            generated_items.sort(key=lambda x: x.priority, reverse=True)
            return generated_items[:limit]

        except Exception as e:
            logger.error(f"Error generating checklist: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to generate checklist due to internal error.")

    def _adjust_content_based_on_context(self, original_content: str, context: EnvironmentalContext) -> str:
        """
        动态修改检查项的具体内容，使其更具针对性。
        """
        prefix = ""
        if context.device_status == DeviceStatus.AGING:
            prefix = "[重点监控] "
        elif context.season == Season.SUMMER and "temperature" in original_content.lower():
            prefix = "[高温预警] "
            
        return f"{prefix}{original_content}"

# --- 使用示例与模拟 ---

def load_mock_standards() -> List[StandardClause]:
    """加载模拟的ISO标准数据"""
    return [
        StandardClause(
            clause_id="ISO-9001-7.1.3",
            description="检查设备运行噪音是否在正常范围内",
            category="maintenance",
            base_frequency="daily",
            conditions={} # 通用条款
        ),
        StandardClause(
            clause_id="ISO-9001-8.5.1",
            description="检查液压系统压力表读数",
            category="operation",
            base_frequency="daily",
            conditions={"device_status": "AGING"} # 仅在设备老化时触发
        ),
        StandardClause(
            clause_id="ISO-9001-Env-Control",
            description="检查车间防冻液浓度",
            category="safety",
            base_frequency="daily",
            conditions={"season": "WINTER"} # 仅冬季触发
        )
    ]

def main():
    """主执行函数示例"""
    try:
        # 1. 准备数据
        standards = load_mock_standards()
        generator = ChecklistGenerator(standards)
        
        # 2. 设置环境上下文 (模拟冬季 + 老化设备)
        current_env = EnvironmentalContext(
            current_date=date(2023, 12, 15),
            temperature=-5.0,
            humidity=0.4,
            device_status=DeviceStatus.AGING,
            season=Season.WINTER
        )
        
        # 3. 生成清单
        logger.info("--- Generating Checklist for AGING device in WINTER ---")
        checklist = generator.generate_daily_checklist(
            station_id="WORKSHOP-A-STATION-01",
            context=current_env
        )
        
        # 4. 输出结果
        print(f"\n{'='*20} DAILY CHECKLIST {'='*20}")
        for item in checklist:
            print(f"[Prio: {item.priority}] {item.content}")
            print(f"  -> ID: {item.item_id}")
            print(f"  -> Reason: {item.reason}")
            print("-" * 40)
            
        # 5. 对比：正常设备在夏季的情况
        summer_env = EnvironmentalContext(
            current_date=date(2023, 7, 15),
            temperature=30.0,
            humidity=0.6,
            device_status=DeviceStatus.NORMAL,
            season=Season.SUMMER
        )
        
        logger.info("--- Generating Checklist for NORMAL device in SUMMER ---")
        checklist_summer = generator.generate_daily_checklist(
            station_id="WORKSHOP-A-STATION-02",
            context=summer_env
        )
        
        print(f"\n{'='*20} SUMMER CHECKLIST (Normal Device) {'='*20}")
        print(f"Total items: {len(checklist_summer)} (Expected fewer items than winter/aging scenario)")
        for item in checklist_summer:
            print(f"[Prio: {item.priority}] {item.content}")

    except Exception as e:
        logger.critical(f"System crash: {e}")

if __name__ == "__main__":
    main()