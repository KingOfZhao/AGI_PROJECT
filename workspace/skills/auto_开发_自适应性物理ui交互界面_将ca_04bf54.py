"""
Module: adaptive_physical_ui_layout.py
Description: Implements a CAD-inspired tolerance analysis engine for Flutter UI layouts.
             This module translates mechanical engineering tolerance principles (GD&T)
             into UI rendering logic to ensure critical features remain functional
             across varying screen dimensions (Mobile, Foldable, Automotive).
"""

import logging
import json
from typing import Dict, List, TypedDict, Optional, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AdaptivePhysicsUI")

class ComponentPriority(Enum):
    """Defines the priority level of UI components, similar to assembly criticality."""
    CRITICAL = 100  # 核心特征：不可压缩，不可隐藏 (e.g., Login button, Speedometer)
    FUNCTIONAL = 50 # 功能特征：可在公差下限进行降级渲染
    DECORATIVE = 10 # 装饰特征：空间不足时优先隐藏

class UIComponent(TypedDict):
    """Data structure for a UI component definition."""
    id: str
    base_width: int          # 基准宽度
    min_width: int           # 公差下限
    priority: int            # 优先级分数 (映射到 ComponentPriority)
    flexible: bool           # 是否允许弹性伸缩
    render_mode: str         # 当前渲染模式

class ToleranceAnalysisError(Exception):
    """Custom exception for tolerance calculation failures."""
    pass

def validate_component_data(component: Dict) -> UIComponent:
    """
    辅助函数: 验证并标准化UI组件数据。
    
    Args:
        component (Dict): 原始组件数据字典。
        
    Returns:
        UIComponent: 验证后的组件对象。
        
    Raises:
        ValueError: 如果缺少必要字段或数值逻辑错误。
    """
    required_fields = ['id', 'base_width', 'min_width', 'priority']
    for field in required_fields:
        if field not in component:
            raise ValueError(f"Missing required field: {field}")
    
    if component['min_width'] > component['base_width']:
        raise ValueError(f"Component {component['id']}: Min width cannot exceed base width.")
    
    if component['priority'] < 0:
        raise ValueError("Priority must be positive.")

    # 设置默认值
    component.setdefault('flexible', True)
    component.setdefault('render_mode', 'full')
    
    logger.debug(f"Component {component['id']} validated successfully.")
    return component

def calculate_interference(
    components: List[UIComponent], 
    container_width: int
) -> Dict[str, Union[float, bool]]:
    """
    核心函数 1: 计算布局干涉量。
    类比机械装配中的干涉检查，计算当前容器宽度与UI组件理想布局总宽度的差异。
    
    Args:
        components (List[UIComponent]): 组件列表。
        container_width (int): 容器当前宽度。
        
    Returns:
        Dict: 包含干涉分析结果:
            - 'total_ideal_width': 理想总宽度
            - 'clearance': 剩余间隙 (正数) 或 干涉量 (负数)
            - 'is_under_tolerance': 是否触碰到公差下限
    
    Example:
        >>> comps = [{'id': 'btn', 'base_width': 100, 'min_width': 50, 'priority': 100}]
        >>> result = calculate_interference(comps, 80)
    """
    try:
        total_base = sum(c['base_width'] for c in components)
        total_min = sum(c['min_width'] for c in components)
        
        clearance = container_width - total_base
        min_clearance = container_width - total_min
        
        result = {
            "total_ideal_width": total_base,
            "total_min_width": total_min,
            "clearance": clearance,
            "is_critical_state": min_clearance < 0
        }
        
        logger.info(f"Tolerance Analysis: Ideal={total_base}, Container={container_width}, Clearance={clearance}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating interference: {e}")
        raise ToleranceAnalysisError("Failed to analyze layout interference.")

def apply_adaptive_rendering_strategy(
    components: List[Dict], 
    container_width: int
) -> List[UIComponent]:
    """
    核心函数 2: 应用自适应性渲染策略。
    基于公差分析结果，决定每个组件的渲染状态。
    
    策略逻辑:
    1. 如果空间充足: 保持 BASE 状态。
    2. 如果空间压缩: 按优先级(Priority)低到高进行压缩，直到达到公差下限。
    3. 如果空间极度不足 (低于所有组件min_width之和): 隐藏 Decorative 组件，保活 Critical 组件。
    
    Args:
        components (List[Dict]): 原始组件数据列表。
        container_width (int): 目标容器宽度。
        
    Returns:
        List[UIComponent]: 更新了渲染指令的组件列表。
        
    Usage:
        可以将输出直接序列化为JSON，传递给Flutter Engine解析执行。
    """
    validated_components = [validate_component_data(c) for c in components]
    
    # 1. 初始干涉分析
    analysis = calculate_interference(validated_components, container_width)
    
    if analysis['is_critical_state']:
        logger.warning("CRITICAL: Container width below cumulative minimum tolerance. Engaging failsafe mode.")
        # 故障安全模式：仅保留 CRITICAL 组件，且强制使用最小宽度
        final_plan = []
        for comp in validated_components:
            if comp['priority'] >= ComponentPriority.CRITICAL.value:
                comp['width'] = comp['min_width']
                comp['render_mode'] = 'compressed_critical'
                final_plan.append(comp)
            else:
                comp['render_mode'] = 'hidden'
                # 即使隐藏也保留在返回列表中以便前端卸载
                final_plan.append(comp)
        return final_plan

    # 2. 常规公差调整
    # 按优先级排序 (低优先级先被处理/压缩)
    sorted_components = sorted(validated_components, key=lambda x: x['priority'])
    
    current_width_usage = analysis['total_ideal_width']
    output_plan = []
    
    # 深拷贝以避免修改原引用
    import copy
    working_comps = copy.deepcopy(sorted_components)
    
    for comp in working_comps:
        if current_width_usage <= container_width:
            # 空间已足够，保持当前状态
            comp['width'] = comp['base_width']
            output_plan.append(comp)
            continue
            
        available_space = container_width - (current_width_usage - comp['base_width'])
        
        if available_space < comp['min_width']:
            # 空间不足以维持最小公差，必须隐藏或降级
            if comp['priority'] < ComponentPriority.FUNCTIONAL.value:
                comp['render_mode'] = 'hidden'
                comp['width'] = 0
                current_width_usage -= comp['base_width']
                logger.info(f"Hiding decorative component: {comp['id']}")
            else:
                # 对于功能性组件，如果必须隐藏，标记为 'collapsed_icon'
                comp['render_mode'] = 'collapsed_icon'
                comp['width'] = 24  # 假设图标最小宽度
                current_width_usage -= (comp['base_width'] - 24)
        else:
            # 压缩到可用空间或最小宽度
            new_width = max(comp['min_width'], available_space)
            reduction = comp['base_width'] - new_width
            comp['width'] = new_width
            comp['render_mode'] = 'scaled_down'
            current_width_usage -= reduction
            logger.debug(f"Scaling component {comp['id']} to {new_width}px")
            
        output_plan.append(comp)

    # 恢复原始顺序 (可选，取决于UI框架需求)
    output_plan.sort(key=lambda x: components.index(next(c for c in components if c['id'] == x['id'])))
    
    return output_plan

# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    # 模拟一个车载屏幕切换场景：从中控大屏切换到仪表盘小屏
    # 定义一组UI组件
    dashboard_ui_components = [
        {"id": "nav_map", "base_width": 400, "min_width": 200, "priority": 100, "type": "view"},
        {"id": "media_control", "base_width": 150, "min_width": 50, "priority": 60, "type": "widget"},
        {"id": "climate_info", "base_width": 100, "min_width": 80, "priority": 80, "type": "info"},
        {"id": "album_art", "base_width": 120, "min_width": 0, "priority": 20, "type": "decorative"},
    ]
    
    # 场景 A: 宽屏模式 - 800px
    print("--- Scenario A: Wide Screen (800px) ---")
    layout_wide = apply_adaptive_rendering_strategy(dashboard_ui_components, 800)
    print(json.dumps(layout_wide, indent=2))
    
    # 场景 B: 紧凑模式 - 450px (触发压缩)
    print("\n--- Scenario B: Compact Screen (450px) ---")
    layout_compact = apply_adaptive_rendering_strategy(dashboard_ui_components, 450)
    print(json.dumps(layout_compact, indent=2))
    
    # 场景 C: 极限模式 - 250px (触发故障安全/隐藏策略)
    print("\n--- Scenario C: Critical Screen (250px) ---")
    layout_critical = apply_adaptive_rendering_strategy(dashboard_ui_components, 250)
    print(json.dumps(layout_critical, indent=2))