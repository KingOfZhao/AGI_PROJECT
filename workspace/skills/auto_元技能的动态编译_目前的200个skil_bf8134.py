"""
模块: auto_meta_skill_compiler
描述: 实现AGI系统中的元技能动态编译。负责将基础技能在运行时组合成复合技能，
     执行任务，并管理技能生命周期的创建与销毁。
"""

import logging
import inspect
from typing import Dict, List, Callable, Any, Optional, TypeVar, TypedDict
from dataclasses import dataclass, field
from functools import reduce
from datetime import datetime
import uuid

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型变量和类型结构
T = TypeVar('T')

class SkillMetadata(TypedDict):
    id: str
    description: str
    version: str
    dependencies: List[str]

@dataclass
class SkillContext:
    """技能执行的上下文环境"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    state: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    """执行结果的数据结构"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    composed_skills: List[str] = field(default_factory=list)

class MetaSkillCompiler:
    """
    元技能动态编译器。
    负责将基础技能注册、动态组合、执行及生命周期管理。
    """
    
    def __init__(self):
        self._registry: Dict[str, Callable] = {}
        self._metadata: Dict[str, SkillMetadata] = {}
        self._active_compositions: Dict[str, List[str]] = {}
        logger.info("MetaSkillCompiler 初始化完成。")

    def register_skill(self, 
                       func: Callable, 
                       metadata: Optional[SkillMetadata] = None) -> None:
        """
        注册基础技能到编译器。
        
        Args:
            func (Callable): 技能对应的函数。
            metadata (Optional[SkillMetadata]): 技能的元数据。
        
        Raises:
            ValueError: 如果函数签名无效或缺少必要元数据。
        """
        if not callable(func):
            raise ValueError("提供的技能必须是可调用对象。")
        
        skill_name = func.__name__
        
        # 默认元数据
        default_meta: SkillMetadata = {
            "id": skill_name,
            "description": inspect.getdoc(func) or "No description",
            "version": "1.0.0",
            "dependencies": []
        }
        
        # 更新元数据
        if metadata:
            default_meta.update(metadata)
            
        self._registry[skill_name] = func
        self._metadata[skill_name] = default_meta
        logger.info(f"技能 '{skill_name}' 已注册。")

    def validate_composition(self, skill_sequence: List[str]) -> bool:
        """
        辅助函数：验证技能组合的合法性和依赖关系。
        
        Args:
            skill_sequence (List[str]): 拟组合的技能名称列表。
            
        Returns:
            bool: 如果组合合法返回 True。
        
        Raises:
            KeyError: 如果技能未注册。
            ValueError: 如果依赖检查失败。
        """
        if not skill_sequence:
            raise ValueError("技能序列不能为空。")
            
        for skill_name in skill_sequence:
            if skill_name not in self._registry:
                logger.error(f"验证失败：技能 '{skill_name}' 未注册。")
                raise KeyError(f"Skill '{skill_name}' not found in registry.")
        
        # 简单的依赖检查逻辑示例（此处仅作演示，实际可包含DAG拓扑排序检查）
        # 假设某些技能需要特定的上下文状态，这里暂时略过复杂逻辑
        logger.debug(f"技能序列 {skill_sequence} 验证通过。")
        return True

    def compose_skills(self, 
                       skill_sequence: List[str], 
                       composition_name: str) -> Callable[[Any], ExecutionResult]:
        """
        核心函数：动态编译技能。
        将一组技能函数封装为一个复合函数（管道模式）。
        
        Args:
            skill_sequence (List[str]): 基础技能名称列表。
            composition_name (str): 复合技能的名称。
            
        Returns:
            Callable: 编译后的复合技能函数。
        """
        self.validate_composition(skill_sequence)
        
        # 记录组合关系
        comp_id = f"comp_{composition_name}_{uuid.uuid4().hex[:8]}"
        self._active_compositions[comp_id] = skill_sequence
        
        def composed_function(initial_input: Any, context: Optional[SkillContext] = None) -> ExecutionResult:
            """
            动态生成的复合技能执行体。
            """
            start_time = datetime.now()
            current_data = initial_input
            ctx = context or SkillContext()
            
            logger.info(f"开始执行复合技能 '{composition_name}' (ID: {comp_id})")
            
            try:
                # 管道式执行
                for skill_name in skill_sequence:
                    skill_func = self._registry[skill_name]
                    logger.debug(f"正在执行子技能: {skill_name}")
                    
                    # 简单的参数适配：如果函数接受上下文，则传入
                    sig = inspect.signature(skill_func)
                    if 'context' in sig.parameters:
                        current_data = skill_func(current_data, context=ctx)
                    else:
                        current_data = skill_func(current_data)
                        
                exec_time = (datetime.now() - start_time).total_seconds()
                
                return ExecutionResult(
                    success=True,
                    data=current_data,
                    execution_time=exec_time,
                    composed_skills=skill_sequence
                )
                
            except Exception as e:
                logger.error(f"复合技能 '{composition_name}' 执行失败: {str(e)}")
                return ExecutionResult(
                    success=False,
                    data=None,
                    error=str(e),
                    composed_skills=skill_sequence
                )
            finally:
                # 固化或解散逻辑：此处为自动清理活动组合记录（可配置）
                if comp_id in self._active_compositions:
                    del self._active_compositions[comp_id]
                    logger.info(f"复合技能实例 {comp_id} 已解散。")

        composed_function.__name__ = composition_name
        composed_function.__doc__ = f"Dynamic composition of: {', '.join(skill_sequence)}"
        return composed_function

    def execute_isolated(self, 
                         skill_name: str, 
                         data: Any, 
                         context: Optional[SkillContext] = None) -> ExecutionResult:
        """
        核心函数：执行单个技能并进行包装处理。
        
        Args:
            skill_name (str): 技能名称。
            data (Any): 输入数据。
            context (Optional[SkillContext]): 上下文对象。
            
        Returns:
            ExecutionResult: 标准化的执行结果。
        """
        if skill_name not in self._registry:
            raise KeyError(f"Skill {skill_name} not found.")
            
        func = self._registry[skill_name]
        start_time = datetime.now()
        
        try:
            # 边界检查：输入数据验证（这里简单检查是否为None，实际可用Pydantic）
            if data is None:
                logger.warning(f"技能 {skill_name} 接收到 None 输入。")

            result_data = func(data)
            
            return ExecutionResult(
                success=True,
                data=result_data,
                execution_time=(datetime.now() - start_time).total_seconds(),
                composed_skills=[skill_name]
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                data=None,
                error=str(e),
                composed_skills=[skill_name]
            )

# ==========================================
# 使用示例 (模拟基础技能)
# ==========================================

def skill_fetch_data(query: str) -> List[Dict]:
    """模拟搜索技能：获取原始数据"""
    return [
        {"id": 1, "value": 10, "type": "A", "desc": "item1"},
        {"id": 2, "value": 5, "type": "B", "desc": "item2"},
        {"id": 3, "value": 20, "type": "A", "desc": "item3"},
    ]

def skill_filter_data(data: List[Dict]) -> List[Dict]:
    """模拟筛选技能：只保留类型为A的数据"""
    return [d for d in data if d['type'] == 'A']

def skill_sort_data(data: List[Dict]) -> List[Dict]:
    """模拟排序技能：根据value降序排列"""
    return sorted(data, key=lambda x: x['value'], reverse=True)

def skill_format_report(data: List[Dict]) -> str:
    """模拟格式化技能：生成报告字符串"""
    header = "ID | Value | Type\n"
    rows = "\n".join([f"{d['id']} | {d['value']} | {d['type']}" for d in data])
    return header + rows

if __name__ == "__main__":
    # 初始化编译器
    compiler = MetaSkillCompiler()
    
    # 1. 注册基础技能
    compiler.register_skill(skill_fetch_data)
    compiler.register_skill(skill_filter_data)
    compiler.register_skill(skill_sort_data)
    compiler.register_skill(skill_format_report)
    
    # 2. 定义复合技能流程 (模拟 "市场调研" 技能)
    # 流程：搜索 -> 筛选 -> 排序 -> 格式化
    market_research_pipeline = [
        "skill_fetch_data", 
        "skill_filter_data", 
        "skill_sort_data", 
        "skill_format_report"
    ]
    
    # 3. 动态编译
    try:
        market_research_skill = compiler.compose_skills(
            market_research_pipeline, 
            "MarketResearchComposite"
        )
        
        # 4. 执行复合技能
        query_input = "market trends 2023"
        result = market_research_skill(query_input)
        
        # 5. 输出结果
        if result.success:
            print("\n=== 复合技能执行成功 ===")
            print(f"执行时间: {result.execution_time:.4f}s")
            print(f"涉及技能: {result.composed_skills}")
            print("\n生成报告:\n")
            print(result.data)
        else:
            print(f"\n执行失败: {result.error}")
            
        # 测试边界检查：空的技能序列
        # compiler.compose_skills([], "EmptySkill") # This should raise ValueError
        
    except Exception as e:
        logger.error(f"系统运行时错误: {e}")