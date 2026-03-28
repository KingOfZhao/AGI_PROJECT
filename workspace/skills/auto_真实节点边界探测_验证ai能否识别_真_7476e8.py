"""
名称: auto_真实节点边界探测_验证ai能否识别_真_7476e8
描述: 【真实节点边界探测】验证AI能否识别'真实节点'的适用边界。当赋予AI一个在特定Context下成立的技能（如'均摊复杂度优化'），将其置于一个完全不同的Context（如实时嵌入式系统，对最大延迟有严格要求）时，AI是否能主动拒绝应用该技能，并解释原因（'虽然平均快，但有抖动风险'）。
领域: system_engineering
"""

import logging
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BoundaryProbe")


class SystemContext(Enum):
    """系统运行环境的枚举定义"""
    GENERAL_PURPOSE = "general_purpose"  # 通用环境，关注吞吐量
    REAL_TIME_EMBEDDED = "real_time_embedded"  # 实时嵌入式环境，关注最大延迟
    BATCH_PROCESSING = "batch_processing"  # 批处理环境，关注总时间


class SkillType(Enum):
    """技能类型枚举"""
    AMORTIZED_OPTIMIZATION = "amortized_optimization"  # 如：动态数组扩容、Smart指针
    DETERMINISTIC_LOOP = "deterministic_loop"  # 如：固定步长循环
    DYNAMIC_MEMORY_ALLOCATION = "dynamic_memory_allocation"  # 动态内存分配


@dataclass
class SystemConstraints:
    """系统约束条件的数据结构"""
    max_latency_ms: float = 100.0  # 最大允许延迟（毫秒）
    allow_dynamic_memory: bool = True  # 是否允许动态内存分配
    avg_throughput_rps: int = 1000  # 平均吞吐量要求
    
    def is_real_time(self) -> bool:
        """辅助方法：判断是否为严苛的实时系统"""
        return self.max_latency_ms < 10.0


@dataclass
class Skill:
    """技能定义数据结构"""
    name: str
    category: SkillType
    description: str
    avg_benefit: float  # 平均收益系数 (>1.0表示有收益)
    worst_case_penalty: float  # 最坏情况惩罚系数
    requires_dynamic_memory: bool = False
    execution_logic: Optional[Callable[[], float]] = None  # 模拟执行逻辑，返回耗时


@dataclass
class ProbeResult:
    """边界探测结果"""
    success: bool
    applied_skill_name: str
    context_type: SystemContext
    message: str
    execution_time_ms: float = 0.0
    violation_detected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


def _validate_environment(context: SystemContext, constraints: SystemConstraints) -> bool:
    """
    辅助函数：验证环境参数的有效性
    
    Args:
        context: 系统上下文
        constraints: 系统约束
        
    Returns:
        bool: 参数是否有效
        
    Raises:
        ValueError: 如果参数不合法
    """
    if constraints.max_latency_ms <= 0:
        logger.error("最大延迟必须大于0")
        raise ValueError("max_latency_ms must be positive")
    
    if context == SystemContext.REAL_TIME_EMBEDDED and constraints.max_latency_ms > 1000:
        logger.warning("实时系统配置了较宽松的延迟限制，这可能不符合常规定义")
    
    return True


def simulate_amortized_optimization() -> float:
    """
    模拟均摊复杂度算法的执行时间
    大部分时候很快，偶尔会有扩容/重组导致的尖峰延迟
    """
    base_time = 0.5  # 基础耗时 ms
    # 10% 的概率触发昂贵的重组操作
    if random.random() < 0.1:
        logger.debug("触发均摊复杂度的最坏情况 (如 Hash 扩容)")
        return base_time * 20.0  # 抖动
    return base_time


def check_skill_boundary_validity(
    skill: Skill,
    context: SystemContext,
    constraints: SystemConstraints
) -> Tuple[bool, str]:
    """
    核心函数1：检测技能是否适用于当前上下文边界
    
    此函数模拟 AGI 的 "自我认知" 或 "边界感知" 能力。
    它不仅仅看技能的平均效果，而是根据系统约束（特别是实时性）进行判断。
    
    Args:
        skill: 待检测的技能对象
        context: 当前系统上下文
        constraints: 系统约束条件
        
    Returns:
        Tuple[bool, str]: (是否允许应用, 判定原因)
    """
    logger.info(f"正在探测技能边界: Skill='{skill.name}', Context='{context.value}'")
    
    # 边界检查 1: 动态内存限制 (针对嵌入式系统)
    if context == SystemContext.REAL_TIME_EMBEDDED:
        if skill.requires_dynamic_memory and not constraints.allow_dynamic_memory:
            reason = (f"拒绝应用技能 '{skill.name}': 实时上下文禁止动态内存分配，"
                      f"但该技能依赖动态内存。")
            logger.warning(reason)
            return False, reason

    # 边界检查 2: 延迟抖动限制 (针对均摊复杂度类技能)
    if context == SystemContext.REAL_TIME_EMBEDDED and constraints.is_real_time():
        # 计算最坏情况下的预估延迟
        # 这里简化模型：假设基础延迟是1ms，惩罚系数直接作用于最大延迟
        estimated_worst_latency = 1.0 * skill.worst_case_penalty
        
        if estimated_worst_latency > constraints.max_latency_ms:
            reason = (f"拒绝应用技能 '{skill.name}': 虽然平均收益高 ({skill.avg_benefit}x)，"
                      f"但最坏情况延迟 ({estimated_worst_latency:.2f}ms) 超过系统容忍度 "
                      f"({constraints.max_latency_ms}ms)。存在抖动风险。")
            logger.warning(reason)
            return False, reason
            
    # 边界检查 3: 批处理环境适用性
    if context == SystemContext.BATCH_PROCESSING:
        # 批处理通常不在乎单次抖动，只在乎总时间
        if skill.avg_benefit > 1.0:
            return True, f"批准应用: 批处理环境优先考虑平均收益 ({skill.avg_benefit}x)。"

    # 默认批准逻辑 (通用环境)
    return True, "技能符合当前上下文约束。"


def execute_with_boundary_probe(
    skill: Skill,
    context: SystemContext,
    constraints: SystemConstraints
) -> ProbeResult:
    """
    核心函数2：执行带有边界探测的技能应用流程
    
    该函数封装了完整的 "检查-执行-验证" 流程。
    它是 AGI 系统调用技能的安全网。
    
    Args:
        skill: 要尝试执行的技能
        context: 运行上下文
        constraints: 运行约束
        
    Returns:
        ProbeResult: 包含执行结果、是否违规、原因等信息的详细对象
        
    Example:
        >>> constraints = SystemConstraints(max_latency_ms=5.0)
        >>> skill = Skill("HashMap", SkillType.AMORTIZED_OPTIMIZATION, worst_case_penalty=50)
        >>> result = execute_with_boundary_probe(skill, SystemContext.REAL_TIME_EMBEDDED, constraints)
        >>> assert result.success is False
    """
    _validate_environment(context, constraints)
    
    start_time = time.perf_counter()
    
    # 1. 边界探测
    is_valid, reason = check_skill_boundary_validity(skill, context, constraints)
    
    if not is_valid:
        return ProbeResult(
            success=False,
            applied_skill_name=skill.name,
            context_type=context,
            message=f"边界探测拦截: {reason}",
            violation_detected=True
        )
    
    # 2. 模拟执行
    logger.info(f"开始执行技能: {skill.name}")
    exec_time = 0.0
    error = None
    
    try:
        if skill.execution_logic:
            # 多次采样以模拟真实运行
            times = [skill.execution_logic() for _ in range(100)]
            exec_time = sum(times) / len(times) # 平均值仅用于日志
            max_time = max(times)
            
            # 3. 运行时验证 - 即使静态检查通过，运行时也要监控
            if context == SystemContext.REAL_TIME_EMBEDDED:
                if max_time > constraints.max_latency_ms:
                    msg = (f"运行时违规: 技能 {skill.name} 实测最大延迟 {max_time:.2f}ms "
                           f"超过限制 {constraints.max_latency_ms}ms")
                    logger.error(msg)
                    return ProbeResult(
                        success=False,
                        applied_skill_name=skill.name,
                        context_type=context,
                        message=msg,
                        execution_time=max_time,
                        violation_detected=True
                    )
        else:
            exec_time = 0.1 # 默认模拟耗时
            
    except Exception as e:
        error = str(e)
        logger.exception(f"技能执行期间发生异常: {e}")
        return ProbeResult(
            success=False,
            applied_skill_name=skill.name,
            context_type=context,
            message=f"执行异常: {error}",
            violation_detected=False
        )

    end_time = time.perf_counter()
    total_duration = (end_time - start_time) * 1000
    
    return ProbeResult(
        success=True,
        applied_skill_name=skill.name,
        context_type=context,
        message=f"技能成功应用。平均耗时: {exec_time:.4f}ms。",
        execution_time=total_duration,
        violation_detected=False,
        metadata={"avg_latency": exec_time}
    )


# ==========================================
# 使用示例与测试代码
# ==========================================
if __name__ == "__main__":
    # 1. 定义技能：动态扩容数组 (均摊复杂度优化)
    dynamic_array_skill = Skill(
        name="DynamicArrayList_Opt",
        category=SkillType.AMORTIZED_OPTIMIZATION,
        description="使用动态数组替代链表以优化缓存命中率",
        avg_benefit=2.5,  # 平均快2.5倍
        worst_case_penalty=50.0,  # 扩容时可能比普通操作慢50倍
        requires_dynamic_memory=True,
        execution_logic=simulate_amortized_optimization
    )

    # 场景 A: 通用服务器环境 (关注吞吐量)
    server_constraints = SystemConstraints(
        max_latency_ms=500.0, 
        allow_dynamic_memory=True
    )
    print("\n--- 场景 A: 通用服务器 ---")
    result_server = execute_with_boundary_probe(
        skill=dynamic_array_skill,
        context=SystemContext.GENERAL_PURPOSE,
        constraints=server_constraints
    )
    print(f"结果: {result_server.message}")

    # 场景 B: 实时嵌入式系统 (硬实时，最大延迟 2ms)
    rtos_constraints = SystemConstraints(
        max_latency_ms=2.0, # 非常严格
        allow_dynamic_memory=False # 甚至可能禁止 malloc
    )
    print("\n--- 场景 B: 实时嵌入式 (RTOS) ---")
    result_rtos = execute_with_boundary_probe(
        skill=dynamic_array_skill,
        context=SystemContext.REAL_TIME_EMBEDDED,
        constraints=rtos_constraints
    )
    print(f"结果: {result_rtos.message}")
    print(f"是否发生违规: {result_rtos.violation_detected}")
    
    # 验证 AGI 是否正确识别了边界
    assert result_rtos.violation_detected is True
    assert result_rtos.success is False